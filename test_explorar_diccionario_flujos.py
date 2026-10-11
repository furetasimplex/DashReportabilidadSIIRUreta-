#!/usr/bin/env python3
"""
test_explorar_diccionario_flujos.py
=====================================
Inspecciona Diccionario_Flujos (en dbo y en inventar_SpcHidr) para ver si
mapea codigo_flujo (F1..F120) a columnas de Datos_conciliados_of, y tambien
recon_flujo_modelo / recon_nodo en DEV_SIIR.hidro por si el mapeo vive ahi.

Ejecutar: .venv/bin/python test_explorar_diccionario_flujos.py
"""
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 220)
pd.set_option('display.max_rows', 200)

engine = get_engine()

def q(sql, label):
    print(f"\n--- {label} ---")
    try:
        df = pd.read_sql(sql, engine)
        print(df.to_string() if not df.empty else "(sin resultados)")
        return df
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return pd.DataFrame()

# Columnas de Diccionario_Flujos en ambos esquemas de la BD default
q(
    "SELECT TABLE_SCHEMA, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_NAME='Diccionario_Flujos' ORDER BY TABLE_SCHEMA, ORDINAL_POSITION",
    "Columnas de Diccionario_Flujos (todas las instancias en BD default)"
)

# Contenido completo (es una tabla de dominio, deberia ser chica)
q("SELECT TOP 200 * FROM [dbo].[Diccionario_Flujos]", "Contenido dbo.Diccionario_Flujos")
q("SELECT TOP 200 * FROM [inventar_SpcHidr].[Diccionario_Flujos]", "Contenido inventar_SpcHidr.Diccionario_Flujos")

# Tambien revisar recon_flujo_modelo y recon_nodo en DEV_SIIR.hidro (definicion de flujos/nodos del modelo)
q(
    "SELECT COLUMN_NAME, DATA_TYPE FROM [DEV_SIIR].INFORMATION_SCHEMA.COLUMNS "
    "WHERE TABLE_SCHEMA='hidro' AND TABLE_NAME='recon_flujo_modelo' ORDER BY ORDINAL_POSITION",
    "Columnas de DEV_SIIR.hidro.recon_flujo_modelo"
)
q(
    "SELECT TOP 200 * FROM [DEV_SIIR].[hidro].[recon_flujo_modelo]",
    "Contenido DEV_SIIR.hidro.recon_flujo_modelo (definicion de cada codigo_flujo)"
)

print("\n" + "=" * 90)
print("Copia y pega TODA esta salida.")
