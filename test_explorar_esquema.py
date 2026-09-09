#!/usr/bin/env python3
"""
test_explorar_esquema.py
=========================
Explora el esquema real de la BD para encontrar donde viven los datos de
detalle de reconciliacion (por solver_run_id) y los datos medidos diarios.
No adivina nombres de tabla: los busca.

Ejecutar: .venv/bin/python test_explorar_esquema.py
"""
from db_connection import get_engine
import pandas as pd

engine = get_engine()
print("Engine:", engine)
print("=" * 90)

def q(sql, label):
    print(f"\n--- {label} ---")
    try:
        df = pd.read_sql(sql, engine)
        print(df.to_string() if not df.empty else "(sin resultados)")
        return df
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return pd.DataFrame()

# 1) Bases de datos visibles para este login
q("SELECT name FROM sys.databases ORDER BY name", "Bases de datos visibles")

# 2) Esquemas dentro de la BD default (inventar_SpcHidr, segun .env SQLSERVER_DB)
q("SELECT DISTINCT TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES ORDER BY TABLE_SCHEMA",
  "Esquemas en la BD DEFAULT (donde conecta el engine, ej. inventar_SpcHidr)")

# 3) Todas las tablas de la BD default
df_tablas_default = q(
    "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_SCHEMA, TABLE_NAME",
    "Tablas en la BD DEFAULT"
)

# 4) Tablas en DEV_SIIR.hidro (cross-db, ya sabemos que aqui viven recon_caso / recon_caso_oficial)
df_tablas_devsiir = q(
    "SELECT TABLE_SCHEMA, TABLE_NAME FROM [DEV_SIIR].INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_TYPE='BASE TABLE' AND TABLE_SCHEMA='hidro' ORDER BY TABLE_NAME",
    "Tablas en DEV_SIIR.hidro"
)

# 5) Buscar por nombre de tabla candidatos en AMBAS bases (detalle, medid, solver, resultado, balance, flujo)
candidatos = ['detalle', 'medid', 'solver', 'resultado', 'balance', 'flujo', 'recon', 'ripio', 'run']

if not df_tablas_default.empty:
    print("\n--- Tablas candidatas en BD DEFAULT (por nombre) ---")
    mask = df_tablas_default['TABLE_NAME'].str.lower().str.contains('|'.join(candidatos))
    print(df_tablas_default[mask].to_string())

if not df_tablas_devsiir.empty:
    print("\n--- Tablas candidatas en DEV_SIIR.hidro (por nombre) ---")
    mask = df_tablas_devsiir['TABLE_NAME'].str.lower().str.contains('|'.join(candidatos))
    print(df_tablas_devsiir[mask].to_string())

# 6) Buscar la columna solver_run_id en TODAS las bases visibles (para saber donde mas se usa)
q(
    "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE COLUMN_NAME = 'solver_run_id'",
    "Tablas en BD DEFAULT que tienen columna 'solver_run_id'"
)
q(
    "SELECT TABLE_SCHEMA, TABLE_NAME FROM [DEV_SIIR].INFORMATION_SCHEMA.COLUMNS "
    "WHERE COLUMN_NAME = 'solver_run_id'",
    "Tablas en DEV_SIIR que tienen columna 'solver_run_id'"
)

print("\n" + "=" * 90)
print("Copia y pega TODA esta salida.")
