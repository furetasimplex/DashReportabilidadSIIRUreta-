"""Capture only DEV definitions and 04-06 October Reclamo rows."""
import json, os, sys
from pathlib import Path
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from db_connection import get_engine
BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('DEV only')
names=['v_cv25_diario','v_preliminar_cv25','v_preliminar_cv25_con_acumulado','v_reclamo_diario','v_modulo_base','cv25_diario','rotopala_horas_turno','calculo_diario']
queries={
 'cv25':'SELECT * FROM reclamo.cv25_diario WHERE fecha BETWEEN :start AND :end ORDER BY fecha',
 'cv_view':'SELECT * FROM reclamo.v_cv25_diario WHERE fecha BETWEEN :start AND :end ORDER BY fecha',
 'horas':'SELECT * FROM reclamo.rotopala_horas_turno WHERE fecha_turno BETWEEN :start AND :end ORDER BY fecha_turno,rotopala_id,turno',
 'prelim':'SELECT * FROM reclamo.v_preliminar_cv25 WHERE fecha_operacion BETWEEN :start AND :end ORDER BY fecha_operacion,rotopala_id,modulo_id',
 'reclamo_view':'SELECT * FROM reclamo.v_reclamo_diario WHERE fecha_operacion BETWEEN :start AND :end ORDER BY fecha_operacion,modulo_id',
 'calculo':'SELECT fecha_operacion,pad_id,[campaña_id],modulo_id,rotopala_id,tms_rotopala_dia,m3_rotopala_dia,fuente_reclamo,flag_calculo FROM reclamo.calculo_diario WHERE fecha_operacion BETWEEN :start AND :end ORDER BY fecha_operacion,pad_id,modulo_id',
 'open_modules':"SELECT [campaña_id],pad_id,modulo_id,modulo_numero,rotopala_id,fecha_apertura,fecha_cierre,estado_secuencia,densidad_oficial FROM reclamo.v_modulo_base WHERE estado_secuencia='ABIERTO' ORDER BY pad_id,rotopala_id,modulo_id",
 'last_topo':"SELECT [campaña_id],modulo_id,MAX(fecha_medicion) ultima_medicion FROM reclamo.topografia_avance WHERE estado='VIGENTE' GROUP BY [campaña_id],modulo_id",
 'prelim_acum':'SELECT * FROM reclamo.v_preliminar_cv25_con_acumulado WHERE fecha_operacion BETWEEN :start AND :end ORDER BY fecha_operacion,modulo_id',
}
with get_engine().connect() as c:
    ident=dict(c.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at')).mappings().one())
    if ident['database_name'].lower()!='inventar_spchidr': raise RuntimeError('wrong DB')
    objects={}
    for n in names:
        obj='reclamo.'+n
        meta=c.execute(text('SELECT o.type_desc,o.modify_date,OBJECT_DEFINITION(o.object_id) definition FROM sys.objects o WHERE o.object_id=OBJECT_ID(:obj)'),{'obj':obj}).mappings().first()
        cols=[dict(x) for x in c.execute(text('SELECT name,column_id FROM sys.columns WHERE object_id=OBJECT_ID(:obj) ORDER BY column_id'),{'obj':obj}).mappings()]
        objects[n]={'metadata':dict(meta) if meta else None,'columns':cols}
    rows={k:[dict(x) for x in c.execute(text(q),{'start':'2026-10-04','end':'2026-10-06'}).mappings()] for k,q in queries.items()}
(BASE/'snapshot_before.json').write_text(json.dumps({'identity':ident,'objects':objects,'rows':rows},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(ident,{k:len(v) for k,v in rows.items()})
