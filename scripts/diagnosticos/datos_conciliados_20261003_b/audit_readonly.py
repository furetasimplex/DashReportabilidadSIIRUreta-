"""Read-only snapshot for the 2026-10-03 shift B emission trace."""
import json
import os
import sys
from pathlib import Path
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV database required")

queries = {
    "conciliados": "SELECT * FROM inventar_SpcHidr.Datos_conciliados_of WHERE Fecha = '2026-10-03'",
    "historico_apilado": "SELECT * FROM inventar_SpcHidr.Historico_Apilado_Diario WHERE CAST(Fecha AS date) = '2026-10-03'",
    "apilado_view": "SELECT * FROM inventar_SpcHidr.v_reporte_diario_apilado_test WHERE CAST(Fecha AS date) = '2026-10-03'",
    "humedad_view": "SELECT * FROM inventar_SpcHidr.v_reporte_diario_humedad_test WHERE CAST(Fecha AS date) = '2026-10-03'",
    "lab_turno_b": "SELECT * FROM inventar_SpcHidr.Informe_TM_lab WHERE CAST(Fecha AS date) = '2026-10-03' AND Turno = 'B' AND Torre IN ('T1','T2')",
    "lab_prior_candidate": "SELECT * FROM inventar_SpcHidr.Informe_TM_lab WHERE CAST(Fecha AS date) = '2026-09-28' AND Turno = 'B' AND Torre = 'T2'",
    "representatividad": "SELECT * FROM inventar_SpcHidr.representatividad_torres_resultado WHERE CAST(Dia AS date) = '2026-10-03'",
    "representatividad_prior_candidate": "SELECT * FROM inventar_SpcHidr.representatividad_torres_resultado WHERE CAST(Dia AS date) = '2026-09-28'",
    "apilado_tms_fuente": "SELECT * FROM inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test WHERE CAST(Fecha AS date) = '2026-10-03'",
    "humedad_inicial": "SELECT * FROM inventar_SpcHidr.humedad_inicial_tm_periodo WHERE CAST(fecha_origen AS date) <= '2026-10-03' AND torre IN ('T1','T2')",
    "conciliados_columns": "SELECT c.name,t.name AS data_type,c.column_id FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE c.object_id=OBJECT_ID('inventar_SpcHidr.Datos_conciliados_of') ORDER BY c.column_id",
    "definitions": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name,o.type_desc,o.modify_date,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.name IN ('sp_reporte_turno_emision_test','sp_mantiene_datos_conciliados_emision_test','v_ajuste_camiones_emision_test','v_datos_apilado_tmh_v2','v_contingencia_totalizador_resuelto_turno','v_reporte_diario_apilado_test','v_reporte_diario_humedad_test') ORDER BY schema_name,o.name",
    "historico_references": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name,o.type_desc,o.modify_date,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE m.definition LIKE '%Historico_Apilado_Diario%' ORDER BY schema_name,o.name",
}
with get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name,DB_NAME() AS database_name,SYSDATETIME() AS observed_at")).mappings().one())
    if identity["database_name"].lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    results = {name:[dict(r) for r in conn.execute(text(sql)).mappings()] for name,sql in queries.items()}
out = {"identity": identity, "results": results}
Path(__file__).with_name("snapshot.json").write_text(json.dumps(out, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print(identity, {key: len(value) for key,value in results.items()})
for row in results["conciliados"]:
    print("possible_3_42", [(key,str(value)) for key,value in row.items()
                            if isinstance(value,(float,int)) and 3.40 <= value <= 3.44])
