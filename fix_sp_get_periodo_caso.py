"""
fix_sp_get_periodo_caso.py
===========================
Corrige inventar_SpcHidr.sp_rep_get_periodo_caso para que también reconozca
casos del sistema nuevo del solver (DEV_SIIR.hidro.recon_caso), no sólo
inventar_SpcHidr.casos_balance.

Sin este fix, "Marcar como Oficial" (sp_rep_publish_oficial_validado) falla
silenciosamente en el sentido de que aborta con
"No se pudo obtener el período del caso." ANTES de escribir nada en
Datos_conciliados_of_ver, para cualquier caso proveniente de recon_caso
(todos los casos nuevos que aparecen hoy en el dropdown "Caso Balance").

Ejecutar:
    .venv/bin/python fix_sp_get_periodo_caso.py
"""
from db_connection import get_engine
from sqlalchemy import text

engine = get_engine()
if engine is None:
    raise SystemExit("ERROR: engine es None, revisa .env")

BACKUP_PATH = "backup_sp_rep_get_periodo_caso_ORIGINAL.sql"

with engine.connect() as conn:
    row = conn.execute(
        text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_rep_get_periodo_caso')) AS def")
    ).fetchone()
    definicion_original = row[0]

if not definicion_original:
    raise SystemExit("No se pudo leer la definición original, aborto sin tocar nada.")

with open(BACKUP_PATH, "w", encoding="utf-8") as f:
    f.write(definicion_original)
print(f"✓ Backup de la definición original guardado en {BACKUP_PATH}")

ALTER_SQL = """
ALTER PROCEDURE inventar_SpcHidr.sp_rep_get_periodo_caso
    @caso_id INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        c.caso_id,
        CAST(c.fecha_ini AS DATE) AS fecha_inicio,
        CAST(c.fecha AS DATE) AS fecha_fin
    FROM inventar_SpcHidr.casos_balance c
    WHERE c.caso_id = @caso_id;

    IF @@ROWCOUNT = 0
    BEGIN
        -- Fallback (2026-09-09): el caso puede venir del sistema nuevo del
        -- solver (DEV_SIIR.hidro.recon_caso), que reutiliza el MISMO
        -- caso_id pero no tiene fila correspondiente en
        -- inventar_SpcHidr.casos_balance. Ver el bridge Python
        -- get_periodo_y_run_solver / _get_periodo_caso_con_fallback en
        -- ajuste_reporte/rep_prod_adjuster.py (misma idea, del lado SQL).
        SELECT
            rc.id AS caso_id,
            CAST(rc.fecha_inicio AS DATE) AS fecha_inicio,
            CAST(rc.fecha_fin AS DATE) AS fecha_fin
        FROM [DEV_SIIR].[hidro].[recon_caso] rc
        WHERE rc.id = @caso_id;
    END
END
"""

with engine.begin() as conn:
    conn.exec_driver_sql(ALTER_SQL)

print("✓ sp_rep_get_periodo_caso actualizado.")

# Verificación: debe devolver ahora el período correcto para caso_id=22 (Agosto 2, recon_caso)
with engine.connect() as conn:
    raw = conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id=22")
    rows = raw.fetchall()
    print(f"✓ Verificado: EXEC sp_rep_get_periodo_caso @caso_id=22 -> {rows}")

# Verificación 2: casos viejos (casos_balance) deben seguir funcionando igual.
# Ajusta este id si 70 ya no existe / cambia según tus pruebas anteriores.
with engine.connect() as conn:
    raw = conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id=70")
    rows = raw.fetchall()
    print(f"✓ Verificado (caso viejo 70, casos_balance): {rows}")
