"""
fix_sp_get_periodo_caso_v2.py
==============================
Corrige el fix anterior: la versión previa de sp_rep_get_periodo_caso hacia
un SELECT en la rama casos_balance y, si no encontraba nada, OTRO SELECT en
la rama recon_caso -> eso produce DOS result sets posibles cuando la primera
rama esta vacia, y tanto "INSERT INTO @periodo(...) EXEC sp_rep_get_periodo_caso"
(usado dentro de sp_rep_publish_oficial_validado) como un EXEC + fetchall()
comun SOLO leen el PRIMER result set. Para un caso que no esta en
casos_balance, ese primer result set queda vacio y el fallback nunca se ve.

Esta version arma el resultado en variables locales y hace UN SOLO SELECT
final, para que siempre haya exactamente un result set (0 o 1 filas), igual
que el SP original.

No vuelve a sobreescribir el backup (ya se guardo en
backup_sp_rep_get_periodo_caso_ORIGINAL.sql con la version pre-fix).

Ejecutar:
    .venv/bin/python fix_sp_get_periodo_caso_v2.py
"""
from db_connection import get_engine

engine = get_engine()
if engine is None:
    raise SystemExit("ERROR: engine es None, revisa .env")

ALTER_SQL = """
ALTER PROCEDURE inventar_SpcHidr.sp_rep_get_periodo_caso
    @caso_id INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @caso_id_out INT = NULL;
    DECLARE @fecha_inicio DATE = NULL;
    DECLARE @fecha_fin DATE = NULL;

    SELECT
        @caso_id_out = c.caso_id,
        @fecha_inicio = CAST(c.fecha_ini AS DATE),
        @fecha_fin = CAST(c.fecha AS DATE)
    FROM inventar_SpcHidr.casos_balance c
    WHERE c.caso_id = @caso_id;

    IF @fecha_inicio IS NULL
    BEGIN
        -- Fallback (2026-09-09): caso del sistema nuevo del solver
        -- (DEV_SIIR.hidro.recon_caso), que reutiliza el MISMO caso_id pero
        -- no tiene fila en inventar_SpcHidr.casos_balance.
        SELECT
            @caso_id_out = rc.id,
            @fecha_inicio = CAST(rc.fecha_inicio AS DATE),
            @fecha_fin = CAST(rc.fecha_fin AS DATE)
        FROM [DEV_SIIR].[hidro].[recon_caso] rc
        WHERE rc.id = @caso_id;
    END

    -- UN SOLO result set final, siempre (0 o 1 filas) - critico para que
    -- "INSERT INTO @periodo(...) EXEC sp_rep_get_periodo_caso" (usado en
    -- sp_rep_publish_oficial_validado) capture el valor correcto.
    SELECT
        @caso_id_out AS caso_id,
        @fecha_inicio AS fecha_inicio,
        @fecha_fin AS fecha_fin
    WHERE @fecha_inicio IS NOT NULL;
END
"""

with engine.begin() as conn:
    conn.exec_driver_sql(ALTER_SQL)

print("✓ sp_rep_get_periodo_caso corregido (un solo result set).")

with engine.connect() as conn:
    raw = conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id=22")
    print(f"✓ caso_id=22 (Agosto 2, recon_caso) -> {raw.fetchall()}")

with engine.connect() as conn:
    raw = conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id=70")
    print(f"✓ caso_id=70 (casos_balance) -> {raw.fetchall()}")

with engine.connect() as conn:
    raw = conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id=999999")
    print(f"✓ caso_id=999999 (no existe en ningun lado) -> {raw.fetchall()}")
