"""Guarded DEV-only ALTER of the CV25/topography comparison view."""
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

before = (BASE / "v_diferencia_cv25_before.sql").read_text(encoding="utf-8").replace("\r\n", "\n")
old = """        SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA'
                 THEN rd.tms_rotopala_dia ELSE 0 END) AS tms_topografia,"""
new = """        CASE WHEN SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA'
                           THEN 1 ELSE 0 END) = 0
             THEN NULL
             ELSE SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA'
                           THEN rd.tms_rotopala_dia ELSE 0 END)
        END AS tms_topografia,"""
if before.count(old) != 1 or not before.count("CREATE VIEW [reclamo].[v_diferencia_cv25]") == 1:
    raise RuntimeError("Unexpected captured view definition")
rollback = before.replace("CREATE VIEW", "ALTER VIEW", 1)
altered = rollback.replace(old, new, 1)
(BASE / "alter_v_diferencia_cv25.sql").write_text(altered, encoding="utf-8")
(BASE / "rollback.sql").write_text(rollback, encoding="utf-8")

with get_engine().begin() as c:
    database = c.scalar(text("SELECT DB_NAME()"))
    if database.lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    current = c.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_diferencia_cv25'))"))
    if current.replace("\r\n", "\n") != before:
        raise RuntimeError("Live view changed after audit; no DDL applied")
    c.exec_driver_sql(altered)
    after = c.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_diferencia_cv25'))"))
    if new not in after.replace("\r\n", "\n"):
        raise RuntimeError("Post-DDL definition mismatch")
print("DEV view updated:", database)
