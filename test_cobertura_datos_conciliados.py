#!/usr/bin/env python3
"""
Verifica si inventar_SpcHidr.Datos_conciliados_of tiene datos diarios para
el rango de fechas de los casos NUEVOS (recon_caso, jul-ago 2026) - si no
los tiene, el motor de ajuste no podra correr para esos casos aunque
resolvamos el puente de targets.
"""
from db_connection import get_engine
import pandas as pd

engine = get_engine()

print("Rango total de fechas en Datos_conciliados_of:")
df = pd.read_sql("SELECT MIN(Fecha) AS min_fecha, MAX(Fecha) AS max_fecha, COUNT(*) AS n FROM inventar_SpcHidr.Datos_conciliados_of", engine)
print(df.to_string(index=False))

print("\nFilas para 2026-07-01 a 2026-08-23 (rango de los casos recon_caso):")
df2 = pd.read_sql("SELECT Fecha, Chancado_TMS_Real, Apilado_TMS_Real FROM inventar_SpcHidr.Datos_conciliados_of WHERE Fecha BETWEEN '2026-07-01' AND '2026-08-23' ORDER BY Fecha", engine)
print(f"Filas encontradas: {len(df2)}")
print(df2.to_string(index=False))
