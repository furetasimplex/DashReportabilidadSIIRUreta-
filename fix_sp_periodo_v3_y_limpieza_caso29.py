"""
fix_sp_periodo_v3_y_limpieza_caso29.py
========================================
1) Invierte la prioridad en sp_rep_get_periodo_caso: recon_caso PRIMERO,
   casos_balance como respaldo (mismo motivo que el fix Python en
   ajuste_reporte/rep_prod_adjuster.py: casos_balance tiene IDs bajos y
   densos que colisionan con IDs nuevos de recon_caso).
2) Verifica que no haya foreign keys apuntando a casos_balance que bloqueen
   borrar la fila.
3) Borra la fila vieja de casos_balance para caso_id=29 (confirmado sin
   ningun historial real en rep_prod_ajuste_log/rep_prod_ajustado/
   rep_prod_ajustado_stg/Datos_conciliados_of_ver - Luis confirmo que son
   bases de desarrollo y se pueden eliminar los antiguos que colisionan).
4) Re-verifica todo: sp_rep_get_periodo_caso(29) y el flujo completo de
   Marcar Oficial para el run que fallo.

Ejecutar:
    .venv/bin/python fix_sp_periodo_v3_y_limpieza_caso29.py
"""
from db_connection import get_engine
from sqlalchemy import text
import pandas as pd

engine = get_engine()
if engine is None:
    raise SystemExit("ERROR: engine es None, revisa .env")

print("=" * 80)
print("1) Foreign keys que referencian inventar_SpcHidr.casos_balance")
print("=" * 80)
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT fk.name AS fk_name, tp.name AS tabla_padre, tr.name AS tabla_referenciada
        FROM sys.foreign_keys fk
        INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
        INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
        WHERE tr.name = 'casos_balance'
    """), conn)
    print(f"FKs encontradas: {len(df)}")
    print(df.to_string(index=False))

print()
print("=" * 80)
print("2) Guardando respaldo de la fila caso_id=29 antes de borrar")
print("=" * 80)
with engine.connect() as conn:
    df_backup = pd.read_sql(text("SELECT * FROM inventar_SpcHidr.casos_balance WHERE caso_id = 29"), conn)
df_backup.to_csv("backup_casos_balance_caso29_ORIGINAL.csv", index=False)
print(df_backup.to_string(index=False))
print("✓ Respaldo guardado en backup_casos_balance_caso29_ORIGINAL.csv")

print()
print("=" * 80)
print("3) ALTER sp_rep_get_periodo_caso: recon_caso primero, casos_balance de respaldo")
print("=" * 80)

ALTER_SQL = """
ALTER PROCEDURE inventar_SpcHidr.sp_rep_get_periodo_caso
    @caso_id INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @caso_id_out INT = NULL;
    DECLARE @fecha_inicio DATE = NULL;
    DECLARE @fecha_fin DATE = NULL;

    -- 2026-09-09 (v3): recon_caso PRIMERO. Es la UNICA fuente del dropdown
    -- "Caso Balance" de la UI; casos_balance queda solo como respaldo para
    -- corridas viejas ya no seleccionables. Invertido tras detectar
    -- colision real de IDs (caso 29 existe en ambos sistemas con periodos
    -- distintos: marzo 2025 en casos_balance vs. agosto 2026 en recon_caso).
    SELECT
        @caso_id_out = rc.id,
        @fecha_inicio = CAST(rc.fecha_inicio AS DATE),
        @fecha_fin = CAST(rc.fecha_fin AS DATE)
    FROM [DEV_SIIR].[hidro].[recon_caso] rc
    WHERE rc.id = @caso_id;

    IF @fecha_inicio IS NULL
    BEGIN
        SELECT
            @caso_id_out = c.caso_id,
            @fecha_inicio = CAST(c.fecha_ini AS DATE),
            @fecha_fin = CAST(c.fecha AS DATE)
        FROM inventar_SpcHidr.casos_balance c
        WHERE c.caso_id = @caso_id;
    END

    -- Un solo result set final (0 o 1 fila), critico para
    -- "INSERT INTO @tabla(...) EXEC sp_rep_get_periodo_caso" usado dentro
    -- de sp_rep_publish_oficial_validado.
    SELECT
        @caso_id_out AS caso_id,
        @fecha_inicio AS fecha_inicio,
        @fecha_fin AS fecha_fin
    WHERE @fecha_inicio IS NOT NULL;
END
"""
with engine.begin() as conn:
    conn.exec_driver_sql(ALTER_SQL)
print("✓ sp_rep_get_periodo_caso actualizado (recon_caso primero)")

print()
print("=" * 80)
print("4) Borrando la fila vieja de casos_balance para caso_id=29")
print("=" * 80)
with engine.begin() as conn:
    result = conn.exec_driver_sql("DELETE FROM inventar_SpcHidr.casos_balance WHERE caso_id = 29")
    print(f"✓ Filas borradas: {result.rowcount}")

print()
print("=" * 80)
print("5) Verificacion: sp_rep_get_periodo_caso ahora para caso_id=29, 70, 999999")
print("=" * 80)
with engine.connect() as conn:
    for cid in (29, 70, 999999):
        raw = conn.exec_driver_sql(f"EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id={cid}")
        print(f"  caso_id={cid} -> {raw.fetchall()}")

print()
print("=" * 80)
print("6) Reintentando Marcar Oficial para el run que fallo (caso 29, run 26838653-...)")
print("=" * 80)
from modules.data_loader import get_data_loader
data_loader = get_data_loader()
try:
    resultado = data_loader.marcar_run_oficial(
        caso_id=29,
        run_id="26838653-F61F-4A42-AA0F-054FBA60BC79",
        usuario="lcortes_test",
        resumen=None,
    )
    print(f"✓ OK: {resultado}")
except Exception as e:
    print(f"✗ ERROR: {e}")

print()
with engine.connect() as conn:
    df = pd.read_sql(text("""
        SELECT Fecha, Chancado_TMS_Real, caso_id, estado_validacion, validation_id
        FROM inventar_SpcHidr.Datos_conciliados_of_ver
        WHERE caso_id = 29
        ORDER BY Fecha
    """), conn)
print(f"filas en Datos_conciliados_of_ver para caso_id=29: {len(df)}")
print(df.to_string(index=False))
