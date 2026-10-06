"""Read-only DEV trace of tower weights, sampling windows and 2026-10-03 B representativity."""
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

NAMES = (
    "v_representatividad_diaria_calculada",
    "sp_refrescar_representatividad_torres",
    "v_peso_real_torre_turno_excel",
    "v_peso_teorico_turno_torre_excel",
    "v_peso_teorico_turno_torre_representatividad_resuelto",
    "v_reporte_diario_emulado_excel",
    "v_bitacora_rangos",
    "v_bitacora_rangos_norm",
)
queries = {
    "objects": "SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,o.type_desc,o.modify_date,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.name IN (" + ",".join("'" + n + "'" for n in NAMES) + ") ORDER BY o.name",
    "related_objects": "SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,o.type_desc,o.modify_date,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE SCHEMA_NAME(o.schema_id)='inventar_SpcHidr' AND (m.definition LIKE '%TOMA DE MUESTRA%' OR m.definition LIKE '%horario_muestreo%' OR m.definition LIKE '%v_peso_real_torre_turno_excel%') ORDER BY o.name",
    "columns": "SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name object_name,c.name column_name,t.name type_name FROM sys.objects o JOIN sys.columns c ON c.object_id=o.object_id JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE SCHEMA_NAME(o.schema_id)='inventar_SpcHidr' AND (o.name LIKE '%peso%torre%' OR o.name LIKE '%muestra%' OR o.name LIKE '%representatividad%' OR o.name LIKE '%bitacora%') ORDER BY o.name,c.column_id",
    "real": "SELECT * FROM inventar_SpcHidr.v_peso_real_torre_turno_excel WHERE Fecha BETWEEN '2026-09-25' AND '2026-10-03' AND Turno='B' AND Torre IN ('T1','T2') ORDER BY Fecha,Torre",
    "teo": "SELECT * FROM inventar_SpcHidr.v_peso_teorico_turno_torre_representatividad_resuelto WHERE Fecha BETWEEN '2026-09-25' AND '2026-10-03' AND Turno='B' AND Torre IN ('T1','T2') ORDER BY Fecha,Torre",
    "rep_calc": "SELECT * FROM inventar_SpcHidr.v_representatividad_diaria_calculada WHERE Dia BETWEEN '2026-09-25' AND '2026-10-03' ORDER BY Dia",
    "rep_stored": "SELECT * FROM inventar_SpcHidr.representatividad_torres_resultado WHERE Dia BETWEEN '2026-09-25' AND '2026-10-03' ORDER BY Dia",
    "emulado": "SELECT * FROM inventar_SpcHidr.v_reporte_diario_emulado_excel WHERE Fecha BETWEEN '2026-09-25' AND '2026-10-03' AND Turno='B' AND Torre IN ('T1','T2') ORDER BY Fecha,Torre",
    "bitacora_raw": "SELECT * FROM inventar_SpcHidr.bitacora_turnos_consolidada WHERE fecha_calendario BETWEEN '2026-09-25' AND '2026-10-04' AND torre IN (1,2) ORDER BY torre,fecha_calendario,ts_toma_muestra",
    "bitacora_ranges": "SELECT * FROM inventar_SpcHidr.v_bitacora_rangos WHERE fecha_turno BETWEEN '2026-09-25' AND '2026-10-03' AND torre IN (1,2) ORDER BY torre,fecha_turno,turno",
    "peso_base": "SELECT * FROM inventar_SpcHidr.param_peso_teorico_base WHERE Torre IN ('T1','T2')",
}
with get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at")).mappings().one())
    if identity["database_name"].lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    results = {name: [dict(r) for r in conn.execute(text(sql)).mappings()] for name, sql in queries.items()}
out = {"identity": identity, "results": results}
Path(__file__).with_name("representatividad_snapshot.json").write_text(json.dumps(out, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print(identity, {key: len(value) for key, value in results.items()})
print("related_names", [r["name"] for r in results["related_objects"]])
