"""Read-only DEV snapshot for the official Chancado emission path."""
import json
import os
import sys
from pathlib import Path
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from db_connection import get_engine

if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr':
    raise RuntimeError('DEV database required')

queries={
 'definitions': "SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,o.type_desc,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.name IN ('v_ajuste_camiones_emision_test','sp_mantiene_datos_conciliados_emision_test','v_factor_ajuste_camiones_test','v_inventario_chancado_test') ORDER BY o.name",
 'ajuste_oct': "SELECT * FROM inventar_SpcHidr.v_ajuste_camiones_emision_test WHERE Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY Fecha",
 'dc_oct': "SELECT * FROM inventar_SpcHidr.Datos_conciliados_of WHERE Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY Fecha",
 'ajuste_hist': "SELECT Fecha,Apilado_TMS_Reporte,Sal_TMH_Dia,SRR_TMS_Dia,Delta_Inventario_Chancado_TMS,Chancado_TMS_Reporte,Chancado_TMS_Sin_Ajuste FROM inventar_SpcHidr.v_ajuste_camiones_emision_test WHERE Fecha BETWEEN '2026-01-01' AND '2026-10-04' ORDER BY Fecha",
 'columns_ajuste': "SELECT c.name FROM sys.columns c WHERE c.object_id=OBJECT_ID('inventar_SpcHidr.v_ajuste_camiones_emision_test') ORDER BY c.column_id",
}
with get_engine().connect() as conn:
    identity=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at')).mappings().one())
    if identity['database_name'].lower()!='inventar_spchidr': raise RuntimeError('Wrong database')
    results={k:[dict(r) for r in conn.execute(text(q)).mappings()] for k,q in queries.items()}
out={'identity':identity,'results':results}
Path(__file__).with_name('before.json').write_text(json.dumps(out,ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(identity,{k:len(v) for k,v in results.items()})
