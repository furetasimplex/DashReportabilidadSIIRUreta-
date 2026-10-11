#!/usr/bin/env python3
"""
test_explorar_sps.py
======================
Busca y vuelca la definicion de los stored procedures sp_rep_% / sp_DatosConciliados_%
para encontrar el mapeo real entre codigo_flujo y columnas de Datos_conciliados_of.

Ejecutar: .venv/bin/python test_explorar_sps.py
"""
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 220)

engine = get_engine()

def q(sql, label):
    print(f"\n{'='*100}\n{label}\n{'='*100}")
    try:
        df = pd.read_sql(sql, engine)
        if df.empty:
            print("(sin resultados)")
        return df
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return pd.DataFrame()

# 1) Listar todos los SPs candidatos (sp_rep%, sp_DatosConciliados%, %flujo%) en la BD default
df_sps = q(
    "SELECT s.name AS esquema, p.name AS procedimiento "
    "FROM sys.procedures p JOIN sys.schemas s ON p.schema_id = s.schema_id "
    "WHERE p.name LIKE 'sp_rep%' OR p.name LIKE 'sp_DatosConciliados%' OR p.name LIKE '%flujo%' "
    "ORDER BY s.name, p.name",
    "Stored procedures candidatos en BD default (inventar_SpcHidr)"
)
if not df_sps.empty:
    print(df_sps.to_string())

# 2) Volcar definicion completa de cada uno encontrado
if not df_sps.empty:
    for _, row in df_sps.iterrows():
        esquema, proc = row['esquema'], row['procedimiento']
        df_def = q(
            f"SELECT OBJECT_DEFINITION(OBJECT_ID('[{esquema}].[{proc}]')) AS definicion",
            f"Definicion de [{esquema}].[{proc}]"
        )
        if not df_def.empty and df_def.iloc[0]['definicion']:
            print(df_def.iloc[0]['definicion'])
        else:
            print("(sin definicion / posiblemente encriptado o no accesible)")

# 3) Por si el mapeo vive tambien en DEV_SIIR
df_sps_dev = q(
    "SELECT s.name AS esquema, p.name AS procedimiento "
    "FROM [DEV_SIIR].sys.procedures p JOIN [DEV_SIIR].sys.schemas s ON p.schema_id = s.schema_id "
    "WHERE p.name LIKE 'sp_rep%' OR p.name LIKE '%flujo%' "
    "ORDER BY s.name, p.name",
    "Stored procedures candidatos en DEV_SIIR"
)
if not df_sps_dev.empty:
    print(df_sps_dev.to_string())
    for _, row in df_sps_dev.iterrows():
        esquema, proc = row['esquema'], row['procedimiento']
        df_def = q(
            f"SELECT OBJECT_DEFINITION(OBJECT_ID('[{esquema}].[{proc}]')) AS definicion",
            f"Definicion de DEV_SIIR.[{esquema}].[{proc}]"
        )
        if not df_def.empty and df_def.iloc[0]['definicion']:
            print(df_def.iloc[0]['definicion'])

print("\n" + "=" * 100)
print("Copia y pega TODA esta salida (aunque sea larga).")
