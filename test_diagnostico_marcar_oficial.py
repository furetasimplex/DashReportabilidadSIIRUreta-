"""
test_diagnostico_marcar_oficial.py
===================================
Diagnostica por qué "Marcar como Oficial" no deja rastro visible en
inventar_SpcHidr.Datos_conciliados_of_ver.

Ejecutar desde la carpeta del proyecto (mismo venv de siempre):
    python3 test_diagnostico_marcar_oficial.py
"""
import sys
from db_connection import get_engine
from sqlalchemy import text
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

engine = get_engine()
if engine is None:
    print("ERROR: engine es None, revisa .env")
    sys.exit(1)


def q(sql, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


print("=" * 80)
print("1) Definición de sp_rep_publish_oficial_validado")
print("=" * 80)
try:
    df = q("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_rep_publish_oficial_validado')) AS def")
    definicion = df.iloc[0]["def"]
    if definicion:
        print(definicion)
    else:
        print("OBJECT_DEFINITION devolvió NULL, probando sp_helptext...")
        with engine.connect() as conn:
            raw = conn.exec_driver_sql("EXEC sp_helptext 'inventar_SpcHidr.sp_rep_publish_oficial_validado'")
            for row in raw.fetchall():
                print(row[0], end="")
except Exception as e:
    print(f"ERROR obteniendo definición: {e}")

print()
print("=" * 80)
print("2) Definición de sp_rep_log_validacion_decision")
print("=" * 80)
try:
    df = q("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_rep_log_validacion_decision')) AS def")
    definicion = df.iloc[0]["def"]
    if definicion:
        print(definicion)
    else:
        print("OBJECT_DEFINITION devolvió NULL, probando sp_helptext...")
        with engine.connect() as conn:
            raw = conn.exec_driver_sql("EXEC sp_helptext 'inventar_SpcHidr.sp_rep_log_validacion_decision'")
            for row in raw.fetchall():
                print(row[0], end="")
except Exception as e:
    print(f"ERROR obteniendo definición: {e}")

print()
print("=" * 80)
print("3) Tablas del schema inventar_SpcHidr que mencionen 'valid' u 'oficial'")
print("=" * 80)
try:
    df = q("""
        SELECT s.name AS schema_name, t.name AS table_name
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id = t.schema_id
        WHERE (t.name LIKE '%valid%' OR t.name LIKE '%oficial%')
        ORDER BY s.name, t.name
    """)
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 80)
print("4) Caso 'Agosto 2' en recon_caso (para ubicar el caso_id usado)")
print("=" * 80)
try:
    df = q("""
        SELECT id, nombre_caso, fecha_inicio, fecha_fin, estado
        FROM [DEV_SIIR].[hidro].[recon_caso]
        WHERE nombre_caso LIKE '%Agosto 2%'
        ORDER BY id DESC
    """)
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")

caso_id = None
if 'df' in dir() and not df.empty:
    caso_id = int(df.iloc[0]["id"])

run_id = "dfb7743e-8d03-4da0-afff-5a625e128a42"

print()
print("=" * 80)
print(f"5) rep_prod_ajuste_log para caso_id={caso_id}")
print("=" * 80)
if caso_id is not None:
    try:
        df = q("""
            SELECT CAST(run_id AS VARCHAR(36)) AS run_id, caso_id, fecha_ini, fecha_fin,
                   ts_inicio, ts_fin, ok, mensaje
            FROM inventar_SpcHidr.rep_prod_ajuste_log
            WHERE caso_id = :caso_id
            ORDER BY ts_inicio DESC
        """, {"caso_id": caso_id})
        print(df.to_string(index=False))
    except Exception as e:
        print(f"ERROR: {e}")

print()
print("=" * 80)
print(f"6) rep_prod_ajustado_stg para caso_id={caso_id} / run_id={run_id}")
print("=" * 80)
if caso_id is not None:
    try:
        df = q("""
            SELECT TOP 20 *
            FROM inventar_SpcHidr.rep_prod_ajustado_stg
            WHERE caso_id = :caso_id AND CAST(run_id AS VARCHAR(36)) = :run_id
            ORDER BY Fecha
        """, {"caso_id": caso_id, "run_id": run_id})
        print(f"filas encontradas: {len(df)}")
        print(df.head(10).to_string(index=False))
    except Exception as e:
        print(f"ERROR: {e}")

print()
print("=" * 80)
print("7) Columnas de Datos_conciliados_of_ver")
print("=" * 80)
try:
    df = q("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'inventar_SpcHidr' AND TABLE_NAME = 'Datos_conciliados_of_ver'
        ORDER BY ORDINAL_POSITION
    """)
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 80)
print("8) Filas de Datos_conciliados_of_ver en el rango 2026-08-08 a 2026-08-15")
print("=" * 80)
try:
    df = q("""
        SELECT *
        FROM inventar_SpcHidr.Datos_conciliados_of_ver
        WHERE Fecha BETWEEN '2026-08-08' AND '2026-08-15'
        ORDER BY Fecha
    """)
    print(f"filas encontradas: {len(df)}")
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 80)
print("9) MAX(Fecha) y conteo total de Datos_conciliados_of_ver (para ver si la tabla se actualiza en absoluto)")
print("=" * 80)
try:
    df = q("""
        SELECT COUNT(*) AS total_filas, MIN(Fecha) AS min_fecha, MAX(Fecha) AS max_fecha
        FROM inventar_SpcHidr.Datos_conciliados_of_ver
    """)
    print(df.to_string(index=False))
except Exception as e:
    print(f"ERROR: {e}")

print()
print("FIN DIAGNOSTICO")
