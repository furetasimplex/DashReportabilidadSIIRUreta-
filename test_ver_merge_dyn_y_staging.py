from db_connection import get_engine
from sqlalchemy import text
import pandas as pd

engine = get_engine()

with engine.connect() as conn:
    df = pd.read_sql(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_rep_merge_ajustado_dyn')) AS def"), conn)
    print(df.iloc[0]["def"])

print()
print("="*80)
print("Runs en rep_prod_ajustado_stg (distinct run_id/caso_id, conteo, fechas)")
print("="*80)
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT CAST(run_id AS VARCHAR(36)) AS run_id, caso_id, COUNT(*) AS filas,
               MIN(Fecha) AS min_fecha, MAX(Fecha) AS max_fecha, MAX(ts_ajuste) AS ts_ajuste
        FROM inventar_SpcHidr.rep_prod_ajustado_stg
        GROUP BY run_id, caso_id
        ORDER BY ts_ajuste DESC
    """), conn)
    print(df.to_string(index=False))

print()
print("="*80)
print("Ese run especifico (26838653-F61F-4A42-AA0F-054FBA60BC79) en rep_prod_ajustado (tabla final)")
print("="*80)
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT COUNT(*) AS filas, MIN(Fecha) AS min_fecha, MAX(Fecha) AS max_fecha
        FROM inventar_SpcHidr.rep_prod_ajustado
        WHERE CAST(run_id AS VARCHAR(36)) = '26838653-F61F-4A42-AA0F-054FBA60BC79' AND caso_id = 29
    """), conn)
    print(df.to_string(index=False))

print()
print("="*80)
print("rep_prod_ajuste_log para caso_id=29 (para ver el historial de corridas)")
print("="*80)
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT CAST(run_id AS VARCHAR(36)) AS run_id, caso_id, fecha_ini, fecha_fin, ts_inicio, ts_fin, ok, mensaje
        FROM inventar_SpcHidr.rep_prod_ajuste_log
        WHERE caso_id = 29
        ORDER BY ts_inicio DESC
    """), conn)
    print(df.to_string(index=False))
