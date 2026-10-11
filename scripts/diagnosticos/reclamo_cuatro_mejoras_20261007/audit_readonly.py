"""Capture the current DEV CV25 difference view and selected read-only rows."""
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
with get_engine().connect() as c:
    database = c.scalar(text("SELECT DB_NAME()"))
    if database.lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    definition = c.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_diferencia_cv25'))"))
    (BASE / "v_diferencia_cv25_before.sql").write_text(definition, encoding="utf-8")
    print("database", database)
    print("view definition\n", definition)
    for name, query in {
        "difference": "SELECT * FROM reclamo.v_diferencia_cv25 WHERE fecha BETWEEN '2026-10-04' AND '2026-10-06' ORDER BY fecha",
        "preview": "SELECT fecha_operacion,[campaña_id],pad_id,modulo_id,modulo_numero,rotopala_id,tms_rotopala_dia,tms_camiones_dia,avance_roto_pct,fuente_reclamo FROM reclamo.calculo_diario WHERE fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06' AND pad_id=2 ORDER BY fecha_operacion,modulo_numero",
    }.items():
        print(name)
        for row in c.execute(text(query)).mappings():
            print(dict(row))
