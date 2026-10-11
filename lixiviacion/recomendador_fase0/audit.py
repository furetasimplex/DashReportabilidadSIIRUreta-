"""Fase 0: SELECT DEV y estadística descriptiva local; no motor de recomendaciones."""
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import time
from sqlalchemy import text
from lixiviacion import db, map_db

P=Path(__file__).parent
STATES='APILADO CONFORMADO_PRE_RIEGO RIEGO RIEGO_DRENAJE DRENAJE_RESIDUAL DRENAJE_CON_RIEGO_PAUSADO PAUSA_HIDRAULICA REPOSO_PRE_RECLAMO RECLAMO RECLAMADO MIXTO SIN_COBERTURA_HIDRAULICA SIN_CLASIFICAR SIN_INFORMACION'.split()


def save(name,x):
    (P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')


def csvsave(name,rows):
    with (P/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def run():
    files=list(Path('lixiviacion').glob('*.py'))+[Path('layout.py')]+list(Path('assets').glob('*.css'))
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    save('runtime_before.json',hashes)
    allrows=[];times=[]
    with db._connection() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
        definition=conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:obj))'),{'obj':db.OP_SOURCE}).scalar_one()
        previous=Path('lixiviacion/diagnostico_performance/funcion_instalada_snapshot.sql').read_text(encoding='utf-8')
        assert definition.replace('\r\n','\n').strip()==previous.replace('\r\n','\n').strip(), 'Definición oficial cambió: detener reutilización del timeline validado'
        definitions={}
        for obj in (db.OP_SOURCE, db.SOURCE,'inventar_SpcHidr.fn_estado_operacional_modulo_diario'):
            value=conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:obj))'),{'obj':obj}).scalar_one()
            definitions[obj]=hashlib.sha256(value.encode()).hexdigest()
            (P/(obj.split('.')[-1]+'.snapshot.sql')).write_text(value,encoding='utf-8')
        day=[dict(r) for r in conn.execute(text(map_db.DAILY_SQL),{'fecha':date(2026,9,10)}).mappings()]
        assert len(day)==60
        save('estado_20260910.json',day)
        for item in day:
            params={'desde':'2026-01-01','hasta':'2026-09-10','pad_id':item['pad_id'],'parcela_id':item['parcela_id']}
            start=time.perf_counter()
            for attempt in range(3):
                try:
                    with db._connection() as parcel_conn:
                        rows=[dict(r) for r in parcel_conn.execute(text(db.OP_TIMELINE_SQL),params).mappings()]
                    break
                except Exception:
                    if attempt==2: raise
            save(f"parcel_{item['pad_id']}_{item['parcela_id']}.json",rows)
            assert len(rows)==253 and len({r['fecha'] for r in rows})==253
            assert all((r['pad_id'],r['parcela_id'])==(item['pad_id'],item['parcela_id']) for r in rows)
            times.append({'pad':item['pad_id'],'parcela':item['numero_parcela'],'seconds':time.perf_counter()-start})
            allrows.extend(rows)
            save('timings.json',times)
            print(item['pad_id'],item['numero_parcela'],round(times[-1]['seconds'],2),flush=True)
        save('operacional_snapshot.json',allrows)
        sql=f'''SELECT fecha,pad_id,parcela_id,nro_parcela_pad,campana_id,estado_asignacion,
        flujo_m3_d,cu_drenaje_gl,cu_refino_gl,delta_cu_gl,transferencia_cu_t_d
        FROM {db.SOURCE} WHERE fecha BETWEEN :desde AND :hasta ORDER BY pad_id,parcela_id,fecha'''
        with db._connection() as fresh:
            v2=[dict(r) for r in fresh.execute(text(sql),{'desde':'2026-01-01','hasta':'2026-09-10'}).mappings()]
        assert len(v2)==len({(r['fecha'],r['pad_id'],r['parcela_id']) for r in v2})
        save('v2_snapshot.json',v2)
        for obj,digest in definitions.items():
            with db._connection() as fresh:
                current=fresh.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:obj))'),{'obj':obj}).scalar_one()
            assert hashlib.sha256(current.encode()).hexdigest()==digest
    queries='-- Solo SELECT DEV. Timeline exacto runtime: ejecutar por cada par PAD/parcela, desde 2026-01-01 hasta 2026-09-10.\n'+db.OP_TIMELINE_SQL+';\n\n'+map_db.DAILY_SQL+';\n\n'+sql+';\nSELECT DB_NAME();\nSELECT OBJECT_DEFINITION(OBJECT_ID(:obj));\n'
    (P/'queries_readonly.sql').write_text(queries,encoding='utf-8')
    save('resultados.json',{'executed_utc':datetime.now(timezone.utc).isoformat(),'operational_rows':len(allrows),'v2_rows':len(v2),
        'definitions':definitions,'timeline_hash':hashlib.sha256(db.OP_TIMELINE_SQL.encode()).hexdigest(),
        'runtime_unchanged':all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items()),
        'seconds_total_timeline':sum(x['seconds'] for x in times),'scope':'descriptivo, sin prioridad, acciones ni umbrales nuevos'})
    analyze()


def analyze():
    op=json.loads((P/'operacional_snapshot.json').read_text(encoding='utf-8'))
    v2=json.loads((P/'v2_snapshot.json').read_text(encoding='utf-8'))
    from decimal import Decimal
    facts=[]
    for state in STATES: facts.append((state,'operacional',op,lambda r,s=state:r['estado_operacional']==s))
    for quality in ('EVALUABLE','PARCIAL','NO_EVALUABLE','SIN_INFORMACION'):
        facts.append(('CALIDAD_'+quality,'operacional',op,lambda r,s=quality:r['calidad_estado']==s))
    for channel in ('riego','drenaje'):
        facts.extend([(channel+'_activo','operacional',op,lambda r,c=channel:r[c+'_activo']==1),
                      (channel+'_inactivo_con_dato','operacional',op,lambda r,c=channel:r['tiene_dato_'+c]==1 and r[c+'_activo']==0),
                      (channel+'_sin_registro','operacional',op,lambda r,c=channel:r['tiene_dato_'+c]!=1),
                      (channel+'_actividad_no_evaluable','operacional',op,lambda r,c=channel:r[c+'_activo'] is None)])
    for name,col,test in [('DELTA_NEGATIVO','delta_cu_gl',lambda v:v<0),('TRANSFERENCIA_NEGATIVA','transferencia_cu_t_d',lambda v:v<0),('FLUJO_CERO','flujo_m3_d',lambda v:v==0)]:
        facts.append((name,'V2',v2,lambda r,c=col,t=test:r[c] is not None and t(Decimal(r[c]))))
    facts.append(('FLUJO_POSITIVO_FUERA','V2',v2,lambda r:r['flujo_m3_d'] is not None and Decimal(r['flujo_m3_d'])>0 and r['estado_asignacion']=='FUERA_VENTANA_RIEGO'))
    facts.extend([
        ('FUERA_VENTANA_RIEGO','V2',v2,lambda r:r['estado_asignacion']=='FUERA_VENTANA_RIEGO'),
        ('RIEGO_SIN_SENAL_DRENAJE','operacional',op,lambda r:r['riego_activo']==1 and r['tiene_dato_drenaje']==1 and r['drenaje_activo']==0),
        ('DRENAJE_SIN_RIEGO_ACTUAL','operacional',op,lambda r:r['drenaje_activo']==1 and r['tiene_dato_riego']==1 and r['riego_activo']==0),
        ('SIN_INFORMACION_HIDRAULICA','operacional',op,lambda r:r['estado_operacional']=='SIN_COBERTURA_HIDRAULICA' or r['riego_activo'] is None or r['drenaje_activo'] is None)])
    counts=[];durations=[];runs=[]
    def pct(values,q):
        pos=(len(values)-1)*q; lo=int(pos);hi=min(lo+1,len(values)-1)
        return round(values[lo]+(values[hi]-values[lo])*(pos-lo),10)
    for name,source,rows,predicate in facts:
        for pad in (1,2):
            subset=[r for r in rows if r['pad_id']==pad]
            counts.append({'hecho':name,'fuente':source,'pad_id':pad,'parcelas_dia':sum(bool(predicate(r)) for r in subset),'filas_fuente':len(subset)})
            grouped=defaultdict(list)
            for r in subset: grouped[r['parcela_id']].append(r)
            lengths=[]
            for parcel,rs in grouped.items():
                rs.sort(key=lambda r:r['fecha']); streak=[]
                def emit():
                    if streak:
                        lengths.append(len(streak));runs.append({'hecho':name,'fuente':source,'pad_id':pad,'parcela_id':parcel,'campana_id':streak[0]['campana_id'],
                            'inicio':streak[0]['fecha'],'fin':streak[-1]['fecha'],'dias':len(streak),
                            'censura_inicio_rango':streak[0]['fecha']=='2026-01-01','censura_fin_rango':streak[-1]['fecha']=='2026-09-10'})
                for r in rs:
                    if streak and (r['campana_id']!=streak[-1]['campana_id'] or (date.fromisoformat(r['fecha'])-date.fromisoformat(streak[-1]['fecha'])).days!=1 or not predicate(r)):
                        emit();streak=[]
                    if predicate(r):streak.append(r)
                emit()
            lengths.sort()
            durations.append({'hecho':name,'fuente':source,'pad_id':pad,'rachas':len(lengths),'min':min(lengths) if lengths else None,
                              'mediana':pct(lengths,.5) if lengths else None,'p75':pct(lengths,.75) if lengths else None,
                              'p90':pct(lengths,.9) if lengths else None,'p95':pct(lengths,.95) if lengths else None,'max':max(lengths) if lengths else None})
    csvsave('hechos_historicos.csv',counts);csvsave('duraciones_descriptivas.csv',durations);csvsave('rachas_observadas.csv',runs)
    print('ANALISIS PASS',len(op),len(v2))


if __name__=='__main__':run()
