"""Install shared upstream Chancado gate in DEV without reprocessing data."""
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
before=(BASE/'dependency_before.sql').read_text(encoding='utf-8').rstrip()
alter=(BASE/'alter_dependency_srr.sql').read_text(encoding='utf-8')
select_rows=text("SELECT * FROM inventar_SpcHidr.Datos_conciliados_of WHERE Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY Fecha")
with get_engine().begin() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name')).mappings().one())
    if ident['database_name'].lower()!='inventar_spchidr' or ident['server_name']!='VPS-5347319-X':
        raise RuntimeError('Wrong DEV target')
    current=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    if current.rstrip()!=before: raise RuntimeError('SP definition drifted')
    rows_before=[dict(r) for r in conn.execute(select_rows).mappings()]
    conn.exec_driver_sql(alter)
    new=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    rows_after=[dict(r) for r in conn.execute(select_rows).mappings()]
    if rows_before!=rows_after: raise RuntimeError('ALTER changed materialized rows')
    if new.count('aj.Chancado_TMS_Reporte')!=1 or new.count('ch.Chancado_TMS_Real')!=3:
        raise RuntimeError('Shared gate references incorrect')
    if 'WHEN aj.Apilado_TMS_Reporte = 0' not in new or 'AND aj.SRR_TMS_Dia = 0' not in new:
        raise RuntimeError('Gate does not use input flow')
(BASE/'dependency_after.json').write_text(json.dumps({'identity':ident,'definition':new,
    'rows_before':rows_before,'rows_after':rows_after},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(ident,'shared_gate_refs',new.count('ch.Chancado_TMS_Real'),'unchanged_rows',len(rows_after))
