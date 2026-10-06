"""Integración DEV: equivalencia, benchmark12, invariancia V2 y perfil; solo SELECT."""
import argparse
from contextlib import contextmanager
from datetime import date,timedelta
import hashlib
import json
import os
from pathlib import Path
import time
from unittest.mock import patch
from sqlalchemy import text
from lixiviacion import db,callbacks
from lixiviacion.diagnostico_performance import audit
from lixiviacion.diagnostico_performance_candidate.run import compare,reversals,stable,CASES
from lixiviacion.diagnostico_performance_candidate.build import SOURCE

P=Path(__file__).parent
END=date(2026,9,10)


def save(name,value):
    (P/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')


def v2_snapshot(name,lookup):
    cases=[]
    for pad,num in [(None,None)]+[(p,n) for p,n,_ in CASES]:
        f=dict(desde='2026-06-01',hasta='2026-09-10',pad=pad,parcela=lookup[(pad,num)] if pad else None,campana=None,estado=None)
        physical=callbacks.load(1,f['desde'],f['hasta'],pad,None,f['parcela'],None)
        assert physical[7]==f
        w,params=db.where(f)
        sql=f"SELECT {','.join(expr+' AS '+col for col,expr in db.DETAIL.items())} FROM {db.SOURCE} WHERE {w} ORDER BY fecha,pad_id,parcela_id"
        with db._connection() as conn: rows=[dict(r) for r in conn.execute(text(sql),params).mappings()]
        cases.append({'pad':pad,'parcela_id':f['parcela'],'kpis':list(physical[:4]),
                      'figures_sha256':[hashlib.sha256(fig.to_json().encode()).hexdigest() for fig in physical[4:7]],
                      'datatable_rows':len(rows),'datatable_sha256':stable(rows)})
    save(name,cases)
    return cases


def profile():
    original=db._connection;profiles=[]
    for pad,parcel in ((1,1),(2,39)):
        calls=[]
        class Proxy:
            def __init__(self,conn): self.conn=conn
            def execute(self,sql,params):
                start=time.perf_counter();result=self.conn.execute(sql,params);executed=time.perf_counter()
                class Result:
                    def mappings(self):
                        rows=list(result.mappings());end=time.perf_counter()
                        calls.append({'query':'header' if str(sql)==db.OP_HEADER_SQL else 'timeline',
                                      'params':params,'execute_seconds':executed-start,'fetch_seconds':end-executed,
                                      'total_seconds':end-start,'rows':len(rows)})
                        return rows
                return Result()
        @contextmanager
        def observed():
            with original() as conn: yield Proxy(conn)
        f=dict(desde='2026-06-01',hasta='2026-09-10',pad=pad,parcela=parcel,campana=None,estado=None)
        start=time.perf_counter()
        with patch.object(db,'_connection',observed): component=callbacks.load_operational(f)
        end=time.perf_counter()
        assert len(calls)==2 and calls[-1]['rows']==102
        profiles.append({'pad':pad,'parcela_id':parcel,'calls':calls,'total_seconds':end-start,
                         'rest_seconds':end-start-sum(c['total_seconds'] for c in calls)})
    save('callback_profile.json',profiles)


def run(stage):
    assert os.getenv('SQLSERVER_DB','').lower()=='inventar_spchidr'
    for d in ('statistics_io_time','plans'): (P/d).mkdir(exist_ok=True)
    engine=db.get_engine();raw=engine.raw_connection()
    before=audit.hashes();save(f'hashes_{stage}_before.json',before)
    previous_out=audit.OUT;audit.OUT=P
    old=(P/'OP_TIMELINE_SQL_before.sql').read_text(encoding='utf-8')
    new=(P/'candidate_runtime_12.sql').read_text(encoding='utf-8')
    timings=[]
    try:
        assert audit.execute(raw,engine,'SELECT DB_NAME() AS name',{})[0][0][0]['name'].lower()=='inventar_spchidr'
        definition=audit.execute(raw,engine,'SELECT OBJECT_DEFINITION(OBJECT_ID(:name)) AS definition',{'name':db.OP_SOURCE})[0][0][0]['definition']
        assert definition.replace('\r\n','\n')==SOURCE.read_text(encoding='utf-8').replace('\r\n','\n')
        ids=audit.execute(raw,engine,f'SELECT pad_id,parcela_id,numero_parcela FROM {db.OP_SOURCE}(:fecha)',{'fecha':END})[0][0]
        lookup={(r['pad_id'],r['numero_parcela']):r['parcela_id'] for r in ids};save('identities.json',ids)
        if stage=='functional': v2_snapshot('v2_before.json',lookup)
        raw.cursor().execute('SET STATISTICS IO ON; SET STATISTICS TIME ON').close()
        def take(label,sql,params,rep=1,plan=False):
            t,rows=audit.measure(raw,engine,label,sql,params,rep,plan)
            timings.append(t);save(f'{stage}_timings.json',timings)
            return rows
        if stage=='functional':
            assert db.OP_TIMELINE_SQL==old
            cases=[(p,n,s,days) for p,n,s in CASES for days in (1,7,31,62,102)]
            cases += [(1,1,'RIEGO_DRENAJE',253),(2,7,'RIEGO_DRENAJE',253)]
            checks=[]
            for pad,num,state,days in cases:
                params={'desde':END-timedelta(days=days-1),'hasta':END,'pad_id':pad,'parcela_id':lookup[(pad,num)]}
                label=f'p{pad}_{num}_{days}d'
                base=take(label+'_before',old,params);candidate=take(label+'_runtime12',new,params)
                check=compare(base,candidate)
                check['SOLO_ANTERIOR']=check.pop('SOLO_BASELINE');check['SOLO_NUEVO']=check.pop('SOLO_CANDIDATO')
                check.update(case=label,params=params,baseline_reversals=reversals(base),new_reversals=reversals(candidate),
                             campaigns=sorted({r['campana_id'] for r in base if r['campana_id'] is not None}),
                             canonical_state=candidate[-1]['estado_operacional'],expected_state=state)
                check['pass']=check['pass'] and len(candidate)==days and list(candidate[0])==list(db.OP_FIELDS) and check['canonical_state']==state and not check['baseline_reversals'] and not check['new_reversals']
                checks.append(check);save('comparacion.json',checks)
                if not check['pass']: raise RuntimeError('Diferencia: '+label+'; no integrar')
            print('FUNCTIONAL PASS',len(checks),flush=True)
        elif stage=='benchmark':
            assert db.OP_TIMELINE_SQL==new,'Medir exactamente el SQL integrado'
            for pad,num in ((1,1),(2,7)):
                for days in (1,7,31,62,102):
                    params={'desde':END-timedelta(days=days-1),'hasta':END,'pad_id':pad,'parcela_id':lookup[(pad,num)]}
                    for rep in (1,2,3): take(f'runtime12_p{pad}_{num}_{days}d',db.OP_TIMELINE_SQL,params,rep)
                take(f'runtime12_p{pad}_{num}_102d',db.OP_TIMELINE_SQL,params,4,True)
            save('benchmark.json',timings)
        elif stage=='post':
            assert db.OP_TIMELINE_SQL==new
            raw.cursor().execute('SET STATISTICS IO OFF; SET STATISTICS TIME OFF').close()
            after=v2_snapshot('v2_after.json',lookup)
            assert after==json.loads((P/'v2_before.json').read_text(encoding='utf-8')),'V2 difiere: investigar'
            profile()
            save('invariance.json',{'four_kpis':True,'three_figures':True,'datatable':True,'cases':8})
    finally:
        audit.OUT=previous_out
        raw.cursor().execute('SET STATISTICS XML OFF; SET STATISTICS IO OFF; SET STATISTICS TIME OFF').close()
        raw.rollback();raw.close()
        save(f'hashes_{stage}_after.json',{'unchanged_during_stage':before==audit.hashes(),'hashes':audit.hashes()})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['functional','benchmark','post']);run(p.parse_args().stage)
