"""Read-only snapshot of current DEV SQL definitions for the Reclamo runbook."""
import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("Expected DEV database inventar_SpcHidr")

NAMES = [
    "sp_actualizar_disponible_rotopala", "sp_insertar_disponible_rotopala",
    "sp_auto_congelar_modulos_nuevos", "sp_auto_mantener_secuencia",
    "sp_sincronizar_desde_etl", "sp_cargar_cv25_horas",
    "sp_calcular_reclamo_diario", "sp_registrar_ajuste_manual",
    "sp_mantiene_datos_conciliados_emision_test", "sp_mantiene_factor_ajuste_camiones_v2_test",
    "v_modulo_base", "v_reclamo_diario", "v_reclamo_para_conciliados",
    "v_diferencia_cv25", "v_cuadratura_modulo", "v_preliminar_cv25",
]
params = {f"n{i}": name for i, name in enumerate(NAMES)}
placeholders = ",".join(f":n{i}" for i in range(len(NAMES)))
query = text(f"""SELECT SCHEMA_NAME(o.schema_id) AS schema_name, o.name,
    o.type_desc, o.modify_date, m.definition
    FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
    WHERE o.name IN ({placeholders}) ORDER BY schema_name,o.name""")
with get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SYSDATETIME() AS observed_at")).mappings().one())
    if identity["database_name"].lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    rows = [dict(r) for r in conn.execute(query, params).mappings()]
for row in rows:
    row["sha256"] = hashlib.sha256((row["definition"] or "").encode()).hexdigest()
path = Path(__file__).with_name("live_definitions.json")
path.write_text(json.dumps({"identity": identity, "definitions": rows}, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print(identity)
print([(r["schema_name"],r["name"],r["modify_date"]) for r in rows])
