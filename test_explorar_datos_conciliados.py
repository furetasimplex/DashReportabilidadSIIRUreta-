#!/usr/bin/env python3
"""
test_explorar_datos_conciliados.py
====================================
Inspecciona inventar_SpcHidr.Datos_conciliados_of (fuente de datos diarios
medidos, segun contexto.md) para el caso/periodo de prueba.

Ejecutar: .venv/bin/python test_explorar_datos_conciliados.py [caso_id] [fecha_inicio] [fecha_fin]
"""
import sys
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 220)

engine = get_engine()

caso_id = int(sys.argv[1]) if len(sys.argv) > 1 else 21
fecha_inicio = sys.argv[2] if len(sys.argv) > 2 else '2026-08-01'
fecha_fin = sys.argv[3] if len(sys.argv) > 3 else '2026-08-08'

def q(sql, label):
    print(f"\n--- {label} ---")
    try:
        df = pd.read_sql(sql, engine)
        print(df.to_string() if not df.empty else "(sin resultados)")
        return df
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return pd.DataFrame()

# 1) Columnas de Datos_conciliados_of (y su tabla _ver hermana)
for t in ['Datos_conciliados_of', 'Datos_conciliados_of_ver']:
    q(
        f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_SCHEMA='inventar_SpcHidr' AND TABLE_NAME='{t}' ORDER BY ORDINAL_POSITION",
        f"Columnas de inventar_SpcHidr.{t}"
    )

# 2) Muestra general (para ver que forma tienen los datos reales)
df_muestra = q(
    "SELECT TOP 15 * FROM [inventar_SpcHidr].[Datos_conciliados_of] ORDER BY 1 DESC",
    "Muestra general de Datos_conciliados_of (15 filas mas recientes)"
)

# 3) Intento de filtro por caso_id / fecha si las columnas existen (ajustar tras ver la muestra)
if not df_muestra.empty:
    cols = [c.lower() for c in df_muestra.columns]
    print(f"\nColumnas detectadas: {list(df_muestra.columns)}")

    posibles_caso = [c for c in df_muestra.columns if 'caso' in c.lower()]
    posibles_fecha = [c for c in df_muestra.columns if 'fecha' in c.lower()]
    posibles_flujo = [c for c in df_muestra.columns if 'flujo' in c.lower() or 'codigo' in c.lower()]
    print(f"Candidatas a columna de caso: {posibles_caso}")
    print(f"Candidatas a columna de fecha: {posibles_fecha}")
    print(f"Candidatas a columna de flujo: {posibles_flujo}")

    if posibles_caso and posibles_fecha:
        col_caso = posibles_caso[0]
        col_fecha = posibles_fecha[0]
        q(
            f"SELECT TOP 20 * FROM [inventar_SpcHidr].[Datos_conciliados_of] "
            f"WHERE [{col_caso}] = {caso_id} "
            f"AND CAST([{col_fecha}] AS DATE) BETWEEN '{fecha_inicio}' AND '{fecha_fin}' "
            f"ORDER BY [{col_fecha}]",
            f"Filtrado por {col_caso}={caso_id} y {col_fecha} entre {fecha_inicio} y {fecha_fin}"
        )

print("\n" + "=" * 90)
print("Copia y pega TODA esta salida.")
