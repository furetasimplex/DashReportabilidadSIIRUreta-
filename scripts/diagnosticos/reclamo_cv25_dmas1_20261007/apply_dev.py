"""Capture and apply the single D+1 predicate change in DEV."""
import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

BASE = Path(__file__).resolve().parent
if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV only")

old_predicate = """        AND
        (
            a.ultima_medicion_topografica IS NULL
            OR cv.fecha > a.ultima_medicion_topografica
        )"""
new_predicate = """        AND cv.fecha = DATEADD(DAY, 1, a.ultima_medicion_topografica)"""

with get_engine().begin() as connection:
    database = connection.scalar(text("SELECT DB_NAME()"))
    if database.lower() != "inventar_spchidr":
        raise RuntimeError(f"Wrong database: {database}")
    names = ("v_cv25_diario", "v_preliminar_cv25", "v_reclamo_diario")
    definitions = {
        name: connection.scalar(text(f"SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.{name}'))")).replace("\r\n", "\n")
        for name in names
    }
    if any(not definition for definition in definitions.values()):
        raise RuntimeError("Missing view definition")
    before = definitions["v_preliminar_cv25"]
    if before.count(old_predicate) != 1 or new_predicate in before:
        raise RuntimeError("Live preliminary view differs from expected definition")
    if "CERO_OPERACION_CONFIRMADO" not in definitions["v_cv25_diario"]:
        raise RuntimeError("Confirmed zero-operation CV25 rule is missing")
    if not before.startswith("CREATE VIEW [reclamo].[v_preliminar_cv25]"):
        raise RuntimeError("Unexpected view header")
    rollback = before.replace("CREATE VIEW", "ALTER VIEW", 1)
    altered = rollback.replace(old_predicate, new_predicate, 1)
    (BASE / "definiciones_before.sql").write_text(
        "\nGO\n\n".join(f"-- reclamo.{name}\n{definitions[name]}" for name in names),
        encoding="utf-8",
    )
    (BASE / "alter_v_cv25_diario.sql").write_text(
        "-- Already deployed in DEV before this D+1 task; retained without another ALTER.\n"
        + definitions["v_cv25_diario"].replace("CREATE VIEW", "ALTER VIEW", 1),
        encoding="utf-8",
    )
    (BASE / "alter_v_preliminar_cv25.sql").write_text(altered, encoding="utf-8")
    (BASE / "rollback.sql").write_text(rollback, encoding="utf-8")
    connection.exec_driver_sql(altered)
    after = connection.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_preliminar_cv25'))"))
    if new_predicate not in after or old_predicate in after:
        raise RuntimeError("Post-DDL definition mismatch")

print(f"Applied D+1 predicate in DEV database {database}")
