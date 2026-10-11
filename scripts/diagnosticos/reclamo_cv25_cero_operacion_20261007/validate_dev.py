"""Read-only DEV regression and before/after evidence for 04-06 October."""
import csv, json, os, sys
from decimal import Decimal
from pathlib import Path
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from db_connection import get_engine
BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('DEV only')
before=json.loads((BASE/'snapshot_before.json').read_text(encoding='utf-8'))
queries={
 'cv25':'SELECT * FROM reclamo.cv25_diario WHERE fecha BETWEEN :a AND :b ORDER BY fecha',
 'cv_view':'SELECT * FROM reclamo.v_cv25_diario WHERE fecha BETWEEN :a AND :b ORDER BY fecha',
 'prelim':'SELECT * FROM reclamo.v_preliminar_cv25 WHERE fecha_operacion BETWEEN :a AND :b ORDER BY fecha_operacion,modulo_id',
 'prelim_acum':'SELECT * FROM reclamo.v_preliminar_cv25_con_acumulado WHERE fecha_operacion BETWEEN :a AND :b ORDER BY fecha_operacion,modulo_id',
 'reclamo_view':'SELECT fecha_operacion,[campaña_id],pad_id,modulo_id,rotopala_id,tms_rotopala_dia,m3_rotopala_dia,fuente_reclamo,flag_calculo FROM reclamo.v_reclamo_diario WHERE fecha_operacion BETWEEN :a AND :b ORDER BY fecha_operacion,modulo_id',
 'calculo':'SELECT fecha_operacion,pad_id,fuente_reclamo,COUNT(*) filas FROM reclamo.calculo_diario WHERE fecha_operacion BETWEEN :a AND :b GROUP BY fecha_operacion,pad_id,fuente_reclamo ORDER BY fecha_operacion,pad_id,fuente_reclamo',
}
with get_engine().connect() as c:
    ident=dict(c.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at')).mappings().one())
    if ident['database_name'].lower()!='inventar_spchidr': raise RuntimeError('wrong DB')
    definition=c.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_cv25_diario'))"))
    if 'CERO_OPERACION_CONFIRMADO' not in definition: raise RuntimeError('view not deployed')
    after={k:json.loads(json.dumps([dict(x) for x in c.execute(text(q),{'a':'2026-10-04','b':'2026-10-06'}).mappings()],default=str)) for k,q in queries.items()}

def date_map(rows,col): return {r[col]:r for r in rows}
b=date_map(before['rows']['cv_view'],'fecha'); a=date_map(after['cv_view'],'fecha')
raw_b=date_map(before['rows']['cv25'],'fecha'); raw_a=date_map(after['cv25'],'fecha')
if set(raw_b)!=set(raw_a): raise RuntimeError(f'CV25 dates changed: before={sorted(raw_b)}, after={sorted(raw_a)}')
raw_fields=('tmh_dia','tms_dia','horas_con_dato_r1','horas_con_dato_r2','tag_utilizado','flag')
raw_diffs={day:{field:(raw_b[day].get(field),raw_a[day].get(field)) for field in raw_fields
                if raw_b[day].get(field)!=raw_a[day].get(field)} for day in raw_b}
assert not any(raw_diffs.values()), f'raw CV25 business fields changed: {raw_diffs}'
assert Decimal(a['2026-10-04']['tms_estimado_r2'])==Decimal(b['2026-10-04']['tms_estimado_r2'])==Decimal('40157.437500')
assert b['2026-10-05']['tms_estimado_r2'] is None
assert Decimal(a['2026-10-05']['tms_estimado_r2'])==0
assert a['2026-10-05']['flag_preliminar']=='CERO_OPERACION_CONFIRMADO'
assert a['2026-10-06']['tms_estimado_r2'] is None
assert a['2026-10-06']['flag_preliminar']=='SIN_RESOLVER_CV25'
assert a['2026-10-04']['tms_estimado_r1'] is None, 'no R1 coverage must not imply zero'
zero=[r for r in after['prelim'] if r['fecha_operacion']=='2026-10-05' and r['rotopala_id']==2]
assert len(zero)==1 and Decimal(zero[0]['tms_preliminar_dia'])==0 and Decimal(zero[0]['m3_preliminar_dia'])==0
assert zero[0]['fuente_reclamo']=='PRELIMINAR_CV25'
assert not [r for r in after['prelim'] if r['fecha_operacion']=='2026-10-06' and r['rotopala_id']==2]
vzero=[r for r in after['reclamo_view'] if r['fecha_operacion']=='2026-10-05' and r['modulo_id']==zero[0]['modulo_id']]
assert len(vzero)==1 and vzero[0]['fuente_reclamo']=='PRELIMINAR_CV25'
assert Decimal(vzero[0]['tms_rotopala_dia'])==0
fields=['fecha','tmh_crudo_before','tmh_crudo_after','tms_crudo_before','tms_crudo_after','cobertura_r1','cobertura_r2','horas_r1','horas_r2','tms_estimado_r1_before','tms_estimado_r1_after','tms_estimado_r2_before','tms_estimado_r2_after','flag_before','flag_after','prelim_r2_modulo_id','prelim_r2_tms','prelim_r2_m3','v_reclamo_fuente_r2']
with (BASE/'before_after.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for day in ('2026-10-04','2026-10-05','2026-10-06'):
        p=next((r for r in after['prelim'] if r['fecha_operacion']==day and r['rotopala_id']==2),None)
        rv=next((r for r in after['reclamo_view'] if p and r['fecha_operacion']==day and r['modulo_id']==p['modulo_id']),None)
        w.writerow({'fecha':day,'tmh_crudo_before':raw_b[day]['tmh_dia'],'tmh_crudo_after':raw_a[day]['tmh_dia'],
            'tms_crudo_before':raw_b[day]['tms_dia'],'tms_crudo_after':raw_a[day]['tms_dia'],
            'cobertura_r1':raw_a[day]['horas_con_dato_r1'],'cobertura_r2':raw_a[day]['horas_con_dato_r2'],
            'horas_r1':a[day]['horas_r1'],'horas_r2':a[day]['horas_r2'],
            'tms_estimado_r1_before':b[day]['tms_estimado_r1'],'tms_estimado_r1_after':a[day]['tms_estimado_r1'],
            'tms_estimado_r2_before':b[day]['tms_estimado_r2'],'tms_estimado_r2_after':a[day]['tms_estimado_r2'],
            'flag_before':b[day]['flag_preliminar'],'flag_after':a[day]['flag_preliminar'],
            'prelim_r2_modulo_id':p['modulo_id'] if p else None,
            'prelim_r2_tms':p['tms_preliminar_dia'] if p else None,
            'prelim_r2_m3':p['m3_preliminar_dia'] if p else None,
            'v_reclamo_fuente_r2':rv['fuente_reclamo'] if rv else None})
(BASE/'snapshot_after.json').write_text(json.dumps({'identity':ident,'rows':after},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print('PASS',ident,{k:len(v) for k,v in after.items()},'zero_modulo',zero[0]['modulo_id'])
