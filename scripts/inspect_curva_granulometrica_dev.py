import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_connection import get_engine


load_dotenv()
if os.getenv("SQLSERVER_HOST") != "149.50.136.234":
    raise RuntimeError("Inspeccion bloqueada fuera de DEV")

engine = get_engine()
with engine.connect() as conn:
    columnas = conn.execute(text("""
        SELECT c.column_id, c.name, t.name AS type_name
        FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(
            'inventar_SpcHidr.v_curva_granulometrica_torres_test'
        )
        ORDER BY c.column_id;
    """)).mappings().all()
    muestra = conn.execute(text("""
        SELECT TOP (8) *
        FROM inventar_SpcHidr.v_curva_granulometrica_torres_test
        WHERE Fecha >= '2026-08-01'
          AND Fecha < '2026-09-01'
          AND Torres_Utilizadas <> 'SIN_DATO'
        ORDER BY Fecha, Turno;
    """)).mappings().all()

print("COLUMNAS")
for fila in columnas:
    print(dict(fila))
print("MUESTRA")
for fila in muestra:
    print(dict(fila))
