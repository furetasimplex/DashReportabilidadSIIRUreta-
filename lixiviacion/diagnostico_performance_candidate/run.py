"""Candidatos SELECT en DEV. Equivalencia exacta antes de benchmark; sin DDL/DML."""
import argparse
from collections import Counter
from datetime import date,timedelta
import hashlib
import json
import os
from pathlib import Path
import time
from sqlalchemy import text
from lixiviacion import db
from lixiviacion.diagnostico_performance import audit
from .build import FIELDS,SOURCE

OUT=Path(__file__).parent
END=date(2026,9,10)
CASES=[(1,1,'RIEGO_DRENAJE'),(1,17,'MIXTO'),(1,29,'REPOSO_PRE_RECLAMO'),
       (2,1,'MIXTO'),(2,7,'RIEGO_DRENAJE'),(2,9,'REPOSO_PRE_RECLAMO'),(2,28,'APILADO')]


def save(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')


def stable(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':')).encode()).hexdigest()


def compare(base,candidate):
    key=lambda r:(r['fecha'],r['pad_id'],r['parcela_id'])
    b={key(r):r for r in base};c={key(r):r for r in candidate}
    fields=list(base[0]) if base else FIELDS
    def packed(rows): return Counter(tuple(r.get(f) for f in fields) for r in rows)
    pb,pc=packed(base),packed(candidate)
    diffs=[{'key':k,'columns':{f:{'baseline':b[k].get(f),'candidate':c[k].get(f)} for f in fields if b[k].get(f)!=c[k].get(f)}}
           for k in b.keys() & c.keys() if b[k]!=c[k]]
    result={'baseline_count':len(base),'candidate_count':len(candidate),
        'baseline_hash':stable(base),'candidate_hash':stable(candidate),
        'SOLO_BASELINE':sum((pb-pc).values()),'SOLO_CANDIDATO':sum((pc-pb).values()),
        'DIFERENCIAS_COLUMNAS':sum(len(x['columns']) for x in diffs),
        'duplicate_baseline_keys':len(base)-len(b),'duplicate_candidate_keys':len(candidate)-len(c),
        'columns_equal':all(list(r)==fields for r in candidate),'differences':diffs[:30]}
    result['pass']=not any(result[k] for k in ('SOLO_BASELINE','SOLO_CANDIDATO','DIFERENCIAS_COLUMNAS','duplicate_baseline_keys','duplicate_candidate_keys')) and result['columns_equal']
    return result


def reversals(rows):
    events=[];prior={}
    forbidden={'DRENAJE_RESIDUAL':{'RIEGO','RIEGO_DRENAJE'},
               'REPOSO_PRE_RECLAMO':{'RIEGO','RIEGO_DRENAJE','DRENAJE_RESIDUAL'}}
    for r in rows:
        k=(r['pad_id'],r['parcela_id'],r['campana_id'])
        seen=prior.setdefault(k,{})
        for terminal,targets in forbidden.items():
            if terminal in seen and r['estado_operacional'] in targets:
                events.append({'campaign':k,'from_date':seen[terminal],'to_date':r['fecha'],
                               'from':terminal,'to':r['estado_operacional']})
        if r['estado_operacional'] in forbidden: seen[r['estado_operacional']]=r['fecha']
    return events


def run(stage):
    assert os.getenv('SQLSERVER_DB','').lower()=='inventar_spchidr','Solo DEV'
    for d in ('statistics','plans'): (OUT/d).mkdir(exist_ok=True)
    before=audit.hashes();save(f'runtime_before_{stage}.json',before)
    engine=db.get_engine();raw=engine.raw_connection()
    timings=[]
    queries={name:(OUT/(name+'.sql')).read_text(encoding='utf-8') for name in
             ('baseline_runtime','baseline_full_contract','candidate_generic','candidate_ox','candidate_sulf')}
    # Reutiliza exclusivamente el capturador de mensajes; cambia su destino en memoria.
    original_out=audit.OUT;audit.OUT=OUT
    original_measure=audit.measure
    def take(label,name,params,rep=1,plan=False):
        # El capturador original usa statistics_io_time. Se guarda luego en statistics.
        (OUT/'statistics_io_time').mkdir(exist_ok=True)
        timing,rows=original_measure(raw,engine,label,queries[name],params,rep,plan)
        file=OUT/'statistics_io_time'/f'{label}_r{rep}.txt'
        file.replace(OUT/'statistics'/file.name)
        timings.append(timing);save(f'{stage}_timings.json',timings)
        return rows
    try:
        assert audit.execute(raw,engine,'SELECT DB_NAME() AS name',{})[0][0][0]['name'].lower()=='inventar_spchidr'
        live=audit.execute(raw,engine,'SELECT OBJECT_DEFINITION(OBJECT_ID(:name)) AS definition',{'name':db.OP_SOURCE})[0][0][0]['definition']
        assert live.replace('\r\n','\n')==SOURCE.read_text(encoding='utf-8').replace('\r\n','\n'),'Definición cambió; revisar antes de comparar'
        save(f'function_hash_{stage}.json',{'sha256':hashlib.sha256(live.encode()).hexdigest(),'matches_audited_snapshot':True})
        identities=audit.execute(raw,engine,f'SELECT pad_id,parcela_id,numero_parcela FROM {db.OP_SOURCE}(:fecha)',{'fecha':END})[0][0]
        lookup={(r['pad_id'],r['numero_parcela']):r['parcela_id'] for r in identities}
        save('identities.json',identities)
        raw.cursor().execute('SET STATISTICS IO ON; SET STATISTICS TIME ON').close()
        if stage in ('probe','functional'):
            comparisons=[]
            cases=[(pad,num,state,days) for pad,num,state in CASES for days in ([1] if stage=='probe' else [1,7,31,62,102])]
            if stage=='functional': cases += [(1,1,'RIEGO_DRENAJE',253),(2,7,'RIEGO_DRENAJE',253)]
            for pad,num,state,days in cases:
                params={'desde':END-timedelta(days=days-1),'hasta':END,'pad_id':pad,'parcela_id':lookup[(pad,num)]}
                label=f'p{pad}_{num}_{days}d'
                base=take(label+'_baseline_full','baseline_full_contract',params)
                runtime=take(label+'_baseline_runtime','baseline_runtime',params)
                runtime_check=compare(runtime,[{f:r[f] for f in db.OP_FIELDS} for r in base])
                assert runtime_check['pass'],runtime_check
                for name in ('candidate_generic','candidate_ox' if pad==1 else 'candidate_sulf'):
                    rows=take(label+'_'+name,name,params)
                    check=compare(base,rows)
                    check.update({'case':label,'candidate':name,'params':params,'runtime_projection_check':runtime_check,
                                  'baseline_reversals':reversals(base),'candidate_reversals':reversals(rows),
                                  'canonical_state':rows[-1]['estado_operacional'] if rows else None,'expected_canonical_state':state,
                                  'campaigns':sorted({r['campana_id'] for r in base if r['campana_id'] is not None}),
                                  'null_counts':{f:sum(r[f] is None for r in base) for f in FIELDS}})
                    check['pass']=check['pass'] and check['canonical_state']==state and check['candidate_reversals']==check['baseline_reversals']
                    comparisons.append(check);save('comparacion_funcional.json' if stage=='functional' else 'probe.json',comparisons)
                    if not check['pass']: raise RuntimeError('Diferencia funcional: '+label+' '+name+'; evidencia guardada, benchmark bloqueado')
            print('EQUIVALENCIA PASS',len(comparisons),flush=True)
        elif stage=='benchmark':
            checks=json.loads((OUT/'comparacion_funcional.json').read_text(encoding='utf-8'))
            assert len(checks)==74 and all(c['pass'] for c in checks),'Benchmark requiere equivalencia completa'
            for pad,num in ((1,1),(2,7)):
                for days in (1,7,31,62,102):
                    params={'desde':END-timedelta(days=days-1),'hasta':END,'pad_id':pad,'parcela_id':lookup[(pad,num)]}
                    for name in ('candidate_generic','candidate_ox' if pad==1 else 'candidate_sulf'):
                        for rep in (1,2,3): take(f'{name}_p{pad}_{num}_{days}d',name,params,rep)
                for name in ('candidate_generic','candidate_ox' if pad==1 else 'candidate_sulf'):
                    take(f'{name}_p{pad}_{num}_102d',name,params,4,True)
            save('benchmark.json',timings)
            raw.cursor().execute('SET STATISTICS IO OFF; SET STATISTICS TIME OFF').close()
            profiles=[]
            with engine.connect() as conn:
                for pad,num in ((1,1),(2,7)):
                    for name in ('candidate_generic','candidate_ox' if pad==1 else 'candidate_sulf'):
                        params={'desde':date(2026,6,1),'hasta':END,'pad_id':pad,'parcela_id':lookup[(pad,num)]}
                        start=time.perf_counter();result=conn.execute(text(queries[name]),params);executed=time.perf_counter()
                        rows=[dict(r) for r in result.mappings()];fetched=time.perf_counter()
                        checks_case=next(c for c in checks if c['case']==f'p{pad}_{num}_102d' and c['candidate']==name)
                        assert stable(rows)==checks_case['baseline_hash']
                        profiles.append({'candidate':name,'params':params,'rows':len(rows),'execute_seconds':executed-start,
                                         'fetch_seconds':fetched-executed,'total_seconds':fetched-start})
            save('sqlalchemy_profile.json',profiles)
    finally:
        audit.OUT=original_out
        raw.cursor().execute('SET STATISTICS XML OFF; SET STATISTICS IO OFF; SET STATISTICS TIME OFF').close()
        raw.rollback();raw.close()
        save(f'runtime_after_{stage}.json',{'unchanged':before==audit.hashes(),'hashes':audit.hashes()})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['probe','functional','benchmark']);run(p.parse_args().stage)
