#!/usr/bin/env python3
"""
test_explorar_tablas_detalle.py
=================================
Inspecciona columnas y datos de muestra de las tablas candidatas a contener
el detalle de resultados de reconciliacion (por solver_run_id) en DEV_SIIR.hidro.

Ejecutar: .venv/bin/python test_explorar_tablas_detalle.py [solver_run_id] [caso_id]
"""
import sys
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

engine = get_engine()

solver_run_id = int(sys.argv[1]) if len(sys.argv) > 1 else 149
caso_id = int(sys.argv[2]) if len(sys.argv) > 2 else 21

tablas = [
    'recon_solver_run',
    'recon_resultado_flujo',
    'recon_caso_flujo_input',
    'recon_precontrol_nodo',
    'recon_nodo',
    'recon_flujo_modelo',
    'recon_modelo',
]

def q(sql, label):
    print(f"\n--- {label} ---")
    try:
        df = pd.read_sql(sql, engine)
        print(df.to_string() if not df.empty else "(sin resultados)")
        return df
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return pd.DataFrame()

# 1) Columnas de cada tabla candidata
for t in tablas:
    q(
        f"SELECT COLUMN_NAME, DATA_TYPE FROM [DEV_SIIR].INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA='hidro' AND TABLE_NAME='{t}' ORDER BY ORDINAL_POSITION",
        f"Columnas de hidro.{t}"
    )

# 2) recon_solver_run: ver la fila del run que estamos probando
q(
    f"SELECT TOP 5 * FROM [DEV_SIIR].[hidro].[recon_solver_run] WHERE id = {solver_run_id}",
    f"recon_solver_run donde id = {solver_run_id}"
)
q(
    f"SELECT TOP 5 * FROM [DEV_SIIR].[hidro].[recon_solver_run] ORDER BY id DESC",
    "recon_solver_run (ultimos 5, para ver estructura real de PK/FK)"
)

# 3) recon_resultado_flujo: ver si tiene solver_run_id directo o via otra FK
q(
    f"SELECT TOP 10 * FROM [DEV_SIIR].[hidro].[recon_resultado_flujo] WHERE solver_run_id = {solver_run_id}",
    f"recon_resultado_flujo con solver_run_id = {solver_run_id} (directo)"
)
q(
    "SELECT TOP 10 * FROM [DEV_SIIR].[hidro].[recon_resultado_flujo]",
    "recon_resultado_flujo (muestra general, para ver columnas reales con datos)"
)

# 4) recon_caso_flujo_input: muestra general
q(
    f"SELECT TOP 10 * FROM [DEV_SIIR].[hidro].[recon_caso_flujo_input] WHERE caso_id = {caso_id}",
    f"recon_caso_flujo_input con caso_id = {caso_id}"
)

print("\n" + "=" * 90)
print("Copia y pega TODA esta salida.")
