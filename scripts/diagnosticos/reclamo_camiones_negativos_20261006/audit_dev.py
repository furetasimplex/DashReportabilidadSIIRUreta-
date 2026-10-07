"""Read-only DEV snapshot for reclamo.v_cuadratura_modulo."""
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
    "definitions": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name,o.type_desc,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE SCHEMA_NAME(o.schema_id)='reclamo' AND o.name IN ('v_cuadratura_modulo','v_camiones_acumulado')",
    "max_references": "SELECT SCHEMA_NAME(o.schema_id) AS schema_name,o.name,o.type_desc,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE SCHEMA_NAME(o.schema_id)='reclamo' AND (LOWER(m.definition) LIKE '%max(%m3_camiones_acum%' OR LOWER(m.definition) LIKE '%max(%tms_camiones_acum%' OR LOWER(m.definition) LIKE '%max(%camiones%acum%')",
    "camiones": "SELECT fecha,campaña_id,modulo_id,m3_camiones_dia,m3_camiones_acum,tms_camiones_dia,tms_camiones_acum FROM reclamo.v_camiones_acumulado WHERE campaña_id=10 AND modulo_id IN (81,87) ORDER BY modulo_id,fecha",
    "cuadratura": "SELECT * FROM reclamo.v_cuadratura_modulo ORDER BY campaña_id,modulo_id",
    "columns": "SELECT c.name,c.column_id FROM sys.columns c WHERE c.object_id=OBJECT_ID('reclamo.v_cuadratura_modulo') ORDER BY c.column_id",
    "base_camiones": "SELECT * FROM reclamo.camiones_reclamo WHERE campaña_id=10 AND modulo_id IN (81,87) ORDER BY modulo_id,fecha",
    "negative_camiones": "SELECT * FROM reclamo.camiones_reclamo WHERE m3_thm<0 OR tms_thm<0 ORDER BY fecha,modulo_id",
    "camiones_range": "SELECT campaña_id,modulo_id,MAX(fecha) AS ultima_fecha,MIN(m3_camiones_dia) AS minimo_diario,COUNT(*) AS filas FROM reclamo.v_camiones_acumulado GROUP BY campaña_id,modulo_id HAVING MIN(m3_camiones_dia)<0 ORDER BY campaña_id,modulo_id",
}
with get_engine().connect() as conn:
    identity=dict(conn.execute(text("SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at")).mappings().one())
    if identity["database_name"].lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    results={name:[dict(r) for r in conn.execute(text(sql)).mappings()] for name,sql in queries.items()}
out={"identity":identity,"results":results}
Path(__file__).with_name("before.json").write_text(json.dumps(out,ensure_ascii=False,default=str,indent=2),encoding="utf-8")
print(identity,{k:len(v) for k,v in results.items()})
