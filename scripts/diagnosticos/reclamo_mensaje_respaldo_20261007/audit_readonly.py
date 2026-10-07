"""Inspect DEV sequence semantics and module/day source classification."""
import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV only")

with get_engine().connect() as c:
    print("database", c.scalar(text("SELECT DB_NAME()")))
    definition = c.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_modulo_base'))"))
    print("v_modulo_base definition:\n", definition)
    cols = c.execute(text("""
        SELECT c.name FROM sys.columns c
        WHERE c.object_id = OBJECT_ID('reclamo.secuencia_rotopala')
        ORDER BY c.column_id
    """)).scalars().all()
    print("secuencia_rotopala columns", cols)
    rows = c.execute(text("""
        SELECT q.fecha_operacion, q.pad_id, q.modulo_id, q.modulo_numero,
               q.rotopala_id, q.fuente_reclamo,
               mb.estado_secuencia, mb.fecha_apertura, mb.fecha_cierre,
               mb.rotopala_id AS mb_rotopala_id
        FROM reclamo.calculo_diario q
        LEFT JOIN reclamo.v_modulo_base mb
          ON mb.[campaña_id] = q.[campaña_id] AND mb.modulo_id = q.modulo_id
        WHERE q.fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06'
        ORDER BY q.pad_id, q.fecha_operacion, q.modulo_numero
    """)).mappings().all()
    for row in rows:
        print(dict(row))
