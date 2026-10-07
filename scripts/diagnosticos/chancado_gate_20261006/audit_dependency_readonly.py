"""Read-only DEV audit of Chancado's downstream SRR dependency."""
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
with get_engine().connect() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at')).mappings().one())
    definition=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    rows=[dict(r) for r in conn.execute(text("""SELECT aj.Fecha,aj.Apilado_TMS_Reporte,aj.Sal_TMH_Dia,
        aj.SRR_TMS_Dia,aj.Delta_Inventario_Chancado_TMS,aj.Chancado_TMS_Reporte,
        dc.Chancado_TMS_Real,dc.Ley_CuT_Real_srr
        FROM inventar_SpcHidr.v_ajuste_camiones_emision_test aj
        JOIN inventar_SpcHidr.Datos_conciliados_of dc ON dc.Fecha=aj.Fecha
        WHERE aj.Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY aj.Fecha""")).mappings()]
if ident['database_name'].lower()!='inventar_spchidr': raise RuntimeError('Wrong DB')
(BASE/'dependency_before.sql').write_text(definition.rstrip()+'\n',encoding='utf-8')
(BASE/'dependency_before.json').write_text(json.dumps({'identity':ident,'rows':rows},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(ident,'rows',len(rows),'raw_chancado_refs',definition.count('aj.Chancado_TMS_Reporte'))
