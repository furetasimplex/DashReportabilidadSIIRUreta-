#!/usr/bin/env python3
"""
test_cruce_casos.py
======================
Verifica si inventar_SpcHidr.casos_balance.caso_id coincide (mismo espacio
de IDs) con DEV_SIIR.hidro.recon_caso.id, y si existe una tabla
casos_balance (u homologa) directamente en DEV_SIIR.hidro.

Ejecutar: .venv/bin/python test_cruce_casos.py
"""
from db_connection import get_engine
import pandas as pd
pd.set_option('display.width', 200)
pd.set_option('display.max_columns', None)

engine = get_engine()

print("=" * 90)
print("1) Existe DEV_SIIR.hidro.casos_balance (u homologa)?")
print("=" * 90)
try:
    q = """
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM [DEV_SIIR].INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME LIKE '%caso%' OR TABLE_NAME LIKE '%balance%'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    df = pd.read_sql(q, engine)
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 90)
print("2) Cuantos caso_id de inventar_SpcHidr.casos_balance EXISTEN tambien como id en DEV_SIIR.hidro.recon_caso?")
print("=" * 90)
try:
    q = """
    SELECT cb.caso_id, cb.nombre_caso, cb.fecha_ini, cb.fecha,
           CASE WHEN rc.id IS NOT NULL THEN 'SI' ELSE 'NO' END AS existe_en_recon_caso
    FROM inventar_SpcHidr.casos_balance cb
    LEFT JOIN [DEV_SIIR].[hidro].[recon_caso] rc ON rc.id = cb.caso_id
    ORDER BY cb.caso_id
    """
    df = pd.read_sql(q, engine)
    print(f"Total casos_balance: {len(df)}")
    print(f"Coinciden con recon_caso.id: {(df['existe_en_recon_caso']=='SI').sum()}")
    print(f"NO coinciden: {(df['existe_en_recon_caso']=='NO').sum()}")
    print("\nMuestra (primeros 15 y ultimos 15):")
    print(df.head(15).to_string(index=False))
    print("...")
    print(df.tail(15).to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 90)
print("3) Cuantos id de DEV_SIIR.hidro.recon_caso EXISTEN tambien como caso_id en inventar_SpcHidr.casos_balance?")
print("=" * 90)
try:
    q = """
    SELECT rc.id, rc.nombre_caso, rc.fecha_inicio, rc.fecha_fin,
           CASE WHEN cb.caso_id IS NOT NULL THEN 'SI' ELSE 'NO' END AS existe_en_casos_balance
    FROM [DEV_SIIR].[hidro].[recon_caso] rc
    LEFT JOIN inventar_SpcHidr.casos_balance cb ON cb.caso_id = rc.id
    ORDER BY rc.id
    """
    df = pd.read_sql(q, engine)
    print(f"Total recon_caso: {len(df)}")
    print(f"Coinciden con casos_balance.caso_id: {(df['existe_en_casos_balance']=='SI').sum()}")
    print(f"NO coinciden: {(df['existe_en_casos_balance']=='NO').sum()}")
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 90)
print("4) recon_caso_oficial: tiene alguna columna que apunte a inventar_SpcHidr (caso_id_reportabilidad, etc)?")
print("=" * 90)
try:
    q = """
    SELECT COLUMN_NAME, DATA_TYPE
    FROM [DEV_SIIR].INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'recon_caso_oficial'
    ORDER BY ORDINAL_POSITION
    """
    df = pd.read_sql(q, engine)
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")
