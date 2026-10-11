"""Read-only DEV audit of campaign 10 truck baseline and its chronology."""
import csv
import json
import os
import sys
from pathlib import Path
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from db_connection import get_engine
BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('DEV database required')

queries={
 'config': 'SELECT * FROM reclamo.configuracion ORDER BY clave',
 'modules': 'SELECT * FROM reclamo.modulo_congelado WHERE campaña_id=10 AND pad_id=2 ORDER BY modulo_id',
 'source': "SELECT fecha,campaña,campaña_id,modulo,modulo_id,volumen_diario_m3,volumen_final_reclamado,avance_porcentaje FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario WHERE campaña_id=10 ORDER BY modulo_id,fecha",
 'system': 'SELECT fecha,campaña_id,modulo_id,m3_camiones_dia,m3_camiones_acum,tms_camiones_dia,tms_camiones_acum FROM reclamo.v_camiones_acumulado WHERE campaña_id=10 ORDER BY modulo_id,fecha',
 'definitions': "SELECT o.name,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE SCHEMA_NAME(o.schema_id)='reclamo' AND o.name IN ('sp_establecer_linea_base','sp_auto_congelar_modulos_nuevos') ORDER BY o.name",
 'log_columns': "SELECT o.name object_name,c.name column_name,c.column_id FROM sys.objects o JOIN sys.columns c ON c.object_id=o.object_id WHERE SCHEMA_NAME(o.schema_id)='reclamo' AND o.name IN ('log_automatizacion','log_ejecucion') ORDER BY o.name,c.column_id",
 'source_columns': "SELECT c.name,c.column_id FROM sys.columns c WHERE c.object_id=OBJECT_ID('inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario') ORDER BY c.column_id",
 'automation_logs': 'SELECT * FROM reclamo.log_automatizacion WHERE campaña_id=10 AND modulo_id IN (81,87)',
 'execution_logs': "SELECT * FROM reclamo.log_ejecucion WHERE procedimiento IN ('reclamo.sp_auto_congelar_modulos_nuevos','reclamo.sp_establecer_linea_base','reclamo.sp_auto_mantener_secuencia')",
}
with get_engine().connect() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at')).mappings().one())
    if ident['database_name'].lower()!='inventar_spchidr': raise RuntimeError('Wrong database')
    results={k:[dict(r) for r in conn.execute(text(q)).mappings()] for k,q in queries.items()}
(BASE/'snapshot.json').write_text(json.dumps({'identity':ident,'results':results},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
for name in ('sp_establecer_linea_base','sp_auto_congelar_modulos_nuevos'):
    definition=next(r['definition'] for r in results['definitions'] if r['name']==name)
    (BASE/f'def_{name}.sql').write_text(definition.rstrip()+'\n',encoding='utf-8')
print(ident,{k:len(v) for k,v in results.items()})
print('log_columns',[(r['object_name'],r['column_name']) for r in results['log_columns']])
