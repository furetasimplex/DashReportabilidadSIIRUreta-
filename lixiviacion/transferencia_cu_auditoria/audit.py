"""Auditoría DEV: únicamente SELECT; no cambia baseline ni runtime."""
import csv
import difflib
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from sqlalchemy import text
from lixiviacion import db

P = Path(__file__).parent
FIELDS = 'fecha,pad_id,parcela_id,nro_parcela_pad,campana_id,estado_asignacion,flujo_m3_d,cu_drenaje_gl,cu_refino_gl,delta_cu_gl,transferencia_cu_t_d'
BASE = ' FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta'
PARAMS = dict(desde='2026-06-01', hasta='2026-09-10')
AGG = 'COUNT_BIG(*) AS filas,SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,COUNT(transferencia_cu_t_d) AS transferencia_no_null'


def save(name, value):
    (P/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')


def csvsave(name, rows):
    if not rows:
        return
    with (P/name).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def run():
    protected = [p for p in Path('lixiviacion').rglob('*') if p.is_file() and P not in p.parents and '__pycache__' not in str(p)]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    queries = []
    with db._connection() as conn:
        def q(sql, params=None):
            assert sql.lstrip().upper().startswith('SELECT')
            queries.append(sql)
            return [dict(r) for r in conn.execute(text(sql), params or PARAMS).mappings()]
        assert q('SELECT DB_NAME() AS db')[0]['db'].lower() == 'inventar_spchidr'
        total = q('SELECT '+AGG+BASE)[0]
        rows = q('SELECT '+FIELDS+BASE+' ORDER BY fecha,pad_id,parcela_id')
        save('live_snapshot.json', rows)
        keys = Counter((str(r['fecha']),r['pad_id'],r['parcela_id']) for r in rows)
        result = {'captured_utc': datetime.now(timezone.utc).isoformat(), 'total': total, 'rows': len(rows),
                  'distinct_keys': len(keys), 'duplicate_keys': sum(v>1 for v in keys.values()),
                  'null_counts': {c:sum(r[c] is None for r in rows) for c in FIELDS.split(',')},
                  'zero_counts': {c:sum(r[c]==0 for r in rows) for c in FIELDS.split(',') if c.endswith('_gl') or c in ('flujo_m3_d','transferencia_cu_t_d')}}
        if total['transferencia'] != Decimal('30395.260628596'):
            result['STOP'] = 'LIVE volvió a cambiar; no continuar comparación'
            save('resultados.json',result); return
        for filename, group in [('date','fecha'),('pad','pad_id'),('parcel','pad_id,parcela_id,nro_parcela_pad'),('date_pad','fecha,pad_id'),('state','estado_asignacion')]:
            data=q('SELECT '+group+','+AGG+BASE+' GROUP BY '+group+' ORDER BY '+group)
            csvsave('summary_by_'+filename+'.csv',data)
            if filename=='pad': result['pads']=data
            if filename=='state': result['states']=data
        result['positive_outside']=q("SELECT COUNT_BIG(*) AS filas,SUM(transferencia_cu_t_d) AS transferencia"+BASE+" AND estado_asignacion='FUERA_VENTANA_RIEGO' AND flujo_m3_d>0")
        old=json.loads(Path('lixiviacion/SMOKE_DEV.json').read_text(encoding='utf-8'))
        result['pad_comparison']=[]
        for r in result['pads']:
            b=old[str(r['pad_id'])]['actual']
            result['pad_comparison'].append({'pad_id':r['pad_id'],'baseline':b,'live':r,
                'delta_transferencia':r['transferencia']-Decimal(b['transferencia']),
                'delta_flujo':r['flujo']-Decimal(b['flujo'])})
        result['delta_global']=total['transferencia']-Decimal(old['None']['actual']['transferencia'])
        assert sum(r['delta_transferencia'] for r in result['pad_comparison'])==result['delta_global']
        historical=Path('lixiviacion/diagnostico_auditoria')
        objects=json.loads((historical/'resultados.json').read_text(encoding='utf-8'))['objects']
        hashes=[]
        (P/'definitions_diff').mkdir(exist_ok=True)
        for obj in objects:
            if not any(x in obj for x in ('vw_tablero_lixiviacion_final_v2','vw_flujos_reales_','vw_drena_concentrados_','vw_riego_')): continue
            live=q('SELECT OBJECT_DEFINITION(OBJECT_ID(:name)) AS definition',{'name':obj})[0]['definition']
            if live is None: continue
            name=obj.replace('.','__')+'.sql'
            (P/'definitions_diff'/('live_'+name)).write_text(live,encoding='utf-8')
            prev=historical/name
            item={'object':obj,'live_sha256':hashlib.sha256(live.encode()).hexdigest(),'historical_file':str(prev),'baseline_association':'snapshot 05-10; no demuestra DDL instalado al producir SMOKE_DEV.json'}
            if prev.exists():
                past=prev.read_text(encoding='utf-8')
                item.update(historical_sha256=hashlib.sha256(past.encode()).hexdigest(),identical=past==live,
                            identical_normalized_newlines=past.replace('\r\n','\n').strip()==live.replace('\r\n','\n').strip())
                (P/'definitions_diff'/('diff_'+name+'.diff')).write_text(''.join(difflib.unified_diff(past.splitlines(True),live.splitlines(True),fromfile=str(prev),tofile=obj+' LIVE')),encoding='utf-8')
            hashes.append(item)
        save('definitions_hashes.json',hashes)
        result['formula_check']=q('SELECT COUNT_BIG(*) AS diferencias'+BASE+''' AND transferencia_cu_t_d <> CAST(CAST(flujo_m3_d*(cu_drenaje_gl-cu_refino_gl) AS decimal(31,6))/CAST(1000.0 AS decimal(5,1)) AS decimal(38,9))''')[0]
        with localcontext() as ctx:
            ctx.prec=70
            residuals=[r['transferencia_cu_t_d']-r['flujo_m3_d']*(r['cu_drenaje_gl']-r['cu_refino_gl'])/Decimal(1000) for r in rows if all(r[c] is not None for c in ('transferencia_cu_t_d','flujo_m3_d','cu_drenaje_gl','cu_refino_gl'))]
            result['rounding_live_only']={'sum_residual_t':sum(residuals),'sum_absolute_residual_t':sum(map(abs,residuals)), 'max_absolute_residual_t':max(map(abs,residuals)), 'note':'Referencia decimal alta precisión solo para cuantificar residual vigente; no sustituye fórmula SQL ni demuestra redondeo histórico.'}
        repeat=q('SELECT '+AGG+BASE)[0]
        assert repeat==total,'LIVE cambió durante captura'
        with localcontext() as ctx:
            ctx.prec=70
            assert sum(r['transferencia_cu_t_d'] for r in rows if r['transferencia_cu_t_d'] is not None)==total['transferencia']
            assert sum(r['flujo_m3_d'] for r in rows if r['flujo_m3_d'] is not None)==total['flujo']
        result['snapshot_sums_equal_sql']=True
    result['runtime_and_existing_evidence_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    save('protected_hashes.json',before)
    save('resultados.json',result)
    (P/'queries_readonly.sql').write_text('-- Ejecutadas mediante SQLAlchemy con :desde=2026-06-01, :hasta=2026-09-10; :name identifica cada objeto en definitions_hashes.json. Solo SELECT.\n\n'+';\n\n'.join(dict.fromkeys(queries))+';\n',encoding='utf-8')
    print(json.dumps(result,default=str,ensure_ascii=False))


if __name__=='__main__': run()
