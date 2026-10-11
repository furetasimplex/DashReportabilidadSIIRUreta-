"""Read-only DEV inventory of THM Reclamo lineage, constraints and ingestion jobs."""
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
names = ["control_reclamo_sulfuro_camiones_thm_diario", "camiones_reclamo", "calculo_diario"]
objects = ["sp_sincronizar_desde_etl", "v_camiones_acumulado", "v_reclamo_diario",
           "sp_calcular_reclamo_diario", "v_reclamo_para_conciliados",
           "sp_mantiene_datos_conciliados_emision_test", "v_cuadratura_modulo"]
queries = {
    "columns": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name AS object_name,c.name AS column_name,t.name AS data_type,c.is_nullable FROM sys.objects o JOIN sys.columns c ON c.object_id=o.object_id JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE o.name IN ('control_reclamo_sulfuro_camiones_thm_diario','camiones_reclamo','calculo_diario') ORDER BY schema_name,object_name,c.column_id",
    "checks": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name AS table_name,cc.name AS constraint_name,cc.definition,cc.is_disabled,cc.is_not_trusted FROM sys.check_constraints cc JOIN sys.objects o ON o.object_id=cc.parent_object_id WHERE o.name IN ('control_reclamo_sulfuro_camiones_thm_diario','camiones_reclamo','calculo_diario')",
    "triggers": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name AS table_name,tr.name AS trigger_name,tr.is_disabled,m.definition FROM sys.triggers tr JOIN sys.objects o ON o.object_id=tr.parent_id LEFT JOIN sys.sql_modules m ON m.object_id=tr.object_id WHERE o.name IN ('control_reclamo_sulfuro_camiones_thm_diario','camiones_reclamo','calculo_diario')",
    "definitions": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name,m.definition,o.modify_date FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.name IN ('sp_sincronizar_desde_etl','v_camiones_acumulado','v_reclamo_diario','sp_calcular_reclamo_diario','v_reclamo_para_conciliados','sp_mantiene_datos_conciliados_emision_test','v_cuadratura_modulo')",
    "writers": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name,o.type_desc,o.modify_date,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE m.definition LIKE '%control_reclamo_sulfuro_camiones_thm_diario%' ORDER BY schema_name,o.name",
    "jobs": "SELECT j.name AS job_name,s.step_id,s.step_name,s.subsystem,s.command FROM msdb.dbo.sysjobs j JOIN msdb.dbo.sysjobsteps s ON s.job_id=j.job_id WHERE s.command LIKE '%reclamo_sulfuro_camiones%' OR s.command LIKE '%Volumen Pilas%' OR s.command LIKE '%THM%' ORDER BY j.name,s.step_id",
    "source_sample": "SELECT TOP (1000) * FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario WHERE CAST(fecha AS date) BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY fecha",
}
with get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name,DB_NAME() AS database_name,SYSDATETIME() AS observed_at")).mappings().one())
    if identity["database_name"].lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    results = {}
    for key, sql in queries.items():
        try:
            results[key] = [dict(r) for r in conn.execute(text(sql)).mappings()]
        except Exception as exc:
            results[key] = {"error": f"{type(exc).__name__}: {exc}"}
out = {"identity": identity, "results": results}
Path(__file__).with_name("metadata.json").write_text(json.dumps(out, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print(identity)
print({k: len(v) if isinstance(v, list) else v for k,v in results.items()})
