from db_connection import get_engine
from sqlalchemy import text
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

engine = get_engine()

print("=" * 80)
print("1) Fila de casos_balance para caso_id=29 (la version VIEJA/original)")
print("=" * 80)
with engine.connect() as conn:
    df = pd.read_sql(text("SELECT * FROM inventar_SpcHidr.casos_balance WHERE caso_id = 29"), conn)
    print(df.to_string(index=False))

print()
print("=" * 80)
print("2) rep_prod_ajuste_log para caso_id=29 con fecha_ini ANTES de 2026 (historial real del caso VIEJO)")
print("=" * 80)
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT CAST(run_id AS VARCHAR(36)) AS run_id, caso_id, fecha_ini, fecha_fin, ts_inicio, ts_fin, ok, mensaje
        FROM inventar_SpcHidr.rep_prod_ajuste_log
        WHERE caso_id = 29 AND fecha_ini < '2026-01-01'
        ORDER BY ts_inicio DESC
    """), conn)
    print(f"filas encontradas: {len(df)}")
    print(df.to_string(index=False))

print()
print("=" * 80)
print("3) rep_prod_ajustado / rep_prod_ajustado_stg para caso_id=29 con Fecha ANTES de 2026")
print("=" * 80)
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT 'rep_prod_ajustado' AS tabla, COUNT(*) AS filas, MIN(Fecha) AS min_fecha, MAX(Fecha) AS max_fecha
        FROM inventar_SpcHidr.rep_prod_ajustado
        WHERE caso_id = 29 AND Fecha < '2026-01-01'
        UNION ALL
        SELECT 'rep_prod_ajustado_stg', COUNT(*), MIN(Fecha), MAX(Fecha)
        FROM inventar_SpcHidr.rep_prod_ajustado_stg
        WHERE caso_id = 29 AND Fecha < '2026-01-01'
        UNION ALL
        SELECT 'Datos_conciliados_of_ver', COUNT(*), MIN(Fecha), MAX(Fecha)
        FROM inventar_SpcHidr.Datos_conciliados_of_ver
        WHERE caso_id = 29 AND Fecha < '2026-01-01'
    """), conn)
    print(df.to_string(index=False))

print()
print("=" * 80)
print("4) rep_prod_targets para caso_id=29 (targets viejos calculados con Data_balance_rec)")
print("=" * 80)
with engine.connect() as conn:
    df = pd.read_sql(text("SELECT * FROM inventar_SpcHidr.rep_prod_targets WHERE caso_id = 29"), conn)
    print(f"filas encontradas: {len(df)}")
    print(df.to_string(index=False))

print()
print("=" * 80)
print("5) Riesgo de colision futura: cuantos de los proximos 30 ids (29..58) ya existen en casos_balance")
print("=" * 80)
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT caso_id, nombre_caso, fecha_ini, fecha
        FROM inventar_SpcHidr.casos_balance
        WHERE caso_id BETWEEN 27 AND 60
        ORDER BY caso_id
    """), conn)
    print(f"colisionan (existen en casos_balance) de 27 a 60: {len(df)} ids -> {df['caso_id'].tolist()}")
    print(df.to_string(index=False))

print()
print("=" * 80)
print("6) Lista completa de caso_id en casos_balance (para saber si es denso o disperso)")
print("=" * 80)
with engine.connect() as conn:
    df = pd.read_sql(text("SELECT caso_id FROM inventar_SpcHidr.casos_balance ORDER BY caso_id"), conn)
    ids = df["caso_id"].tolist()
    print(f"total: {len(ids)}, primeros 20: {ids[:20]}, ultimos 10: {ids[-10:]}")
