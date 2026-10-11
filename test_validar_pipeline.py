#!/usr/bin/env python3
"""
test_validar_pipeline.py
==========================
Verifica:
1) Si inventar_SpcHidr.casos_balance existe y tiene datos, y si su caso_id
   coincide con DEV_SIIR.hidro.recon_caso.id (cruce por caso_id=70 y por
   fecha_inicio/fecha_fin)
2) Historial real de corridas en rep_prod_ajuste_log (exitosas o no)
3) Muestra de Data_balance_rec (calificado con schema) para caso_id=70
4) Muestra de rep_prod_ajustado (calificado con schema) para caso_id=70

Escribe a validar_pipeline.txt

Ejecutar: .venv/bin/python test_validar_pipeline.py
"""
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_colwidth', 200)
pd.set_option('display.width', 250)
pd.set_option('display.max_columns', None)

engine = get_engine()
out_lines = []

def w(s=""):
    print(s)
    out_lines.append(str(s))

w("=" * 100)
w("1) inventar_SpcHidr.casos_balance -- existe? cuantas filas? caso_id=70?")
w("=" * 100)
try:
    df = pd.read_sql("SELECT * FROM inventar_SpcHidr.casos_balance", engine)
    w(f"Total filas: {len(df)}")
    w(df.to_string(index=False))
except Exception as e:
    w(f"ERROR: {e}")

w("\n" + "=" * 100)
w("2) DEV_SIIR.hidro.recon_caso -- para comparar caso_id=70 (existe alli?)")
w("=" * 100)
try:
    df = pd.read_sql("SELECT * FROM [DEV_SIIR].[hidro].[recon_caso] WHERE id = 70", engine)
    w(df.to_string(index=False) if not df.empty else "(no existe id=70 en recon_caso)")
except Exception as e:
    w(f"ERROR: {e}")

w("\n" + "=" * 100)
w("3) inventar_SpcHidr.rep_prod_ajuste_log -- historial de corridas")
w("=" * 100)
try:
    df = pd.read_sql("SELECT * FROM inventar_SpcHidr.rep_prod_ajuste_log ORDER BY ts_inicio DESC", engine)
    w(f"Total filas: {len(df)}")
    w(df.to_string(index=False))
except Exception as e:
    w(f"ERROR (probando sin ts_inicio): {e}")
    try:
        df = pd.read_sql("SELECT * FROM inventar_SpcHidr.rep_prod_ajuste_log", engine)
        w(f"Total filas: {len(df)}")
        w(df.to_string(index=False))
    except Exception as e2:
        w(f"ERROR: {e2}")

w("\n" + "=" * 100)
w("4) inventar_SpcHidr.Data_balance_rec para caso_id=70")
w("=" * 100)
try:
    df = pd.read_sql("SELECT * FROM inventar_SpcHidr.Data_balance_rec WHERE caso_id = 70 ORDER BY Flujo", engine)
    w(df.to_string(index=False))
except Exception as e:
    w(f"ERROR: {e}")

w("\n" + "=" * 100)
w("5) inventar_SpcHidr.rep_prod_ajustado para caso_id=70 (TOP 5 mas reciente)")
w("=" * 100)
try:
    df = pd.read_sql("SELECT TOP 5 * FROM inventar_SpcHidr.rep_prod_ajustado WHERE caso_id = 70 ORDER BY Fecha DESC", engine)
    w(df.to_string(index=False) if not df.empty else "(vacio - nunca se ha corrido exitosamente para este caso)")
except Exception as e:
    w(f"ERROR: {e}")

with open('validar_pipeline.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(out_lines))

print("\n\n>>> Guardado en validar_pipeline.txt <<<")
