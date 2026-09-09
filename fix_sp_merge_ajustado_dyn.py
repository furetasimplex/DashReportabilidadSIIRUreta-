#!/usr/bin/env python3
"""
fix_sp_merge_ajustado_dyn.py
===============================
Corrige el bug en inventar_SpcHidr.sp_rep_merge_ajustado_dyn: la columna
Fecha se excluia tanto del UPDATE (correcto) como del INSERT dinamico
(incorrecto - Fecha es NOT NULL y es la clave del INSERT tambien). Por eso
fallaba con "Cannot insert the value NULL into column 'Fecha'" cada vez que
el ajuste procesaba una fecha que nunca antes se habia insertado en
rep_prod_ajustado (que es siempre el caso para un caso_id/periodo nuevo).

Fix: agrega [Fecha] / src.[Fecha] explicitamente a @ins_cols/@ins_vals,
igual que ya se hacia con [estado].

Ejecutar: .venv/bin/python fix_sp_merge_ajustado_dyn.py
"""
from db_connection import get_engine
from sqlalchemy import text

engine = get_engine()

NUEVA_DEFINICION = """
ALTER PROCEDURE inventar_SpcHidr.sp_rep_merge_ajustado_dyn
    @run_id UNIQUEIDENTIFIER
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @schema SYSNAME = 'inventar_SpcHidr';
    DECLARE @tgt SYSNAME = 'rep_prod_ajustado';
    DECLARE @stg SYSNAME = 'rep_prod_ajustado_stg';

    -- columnas a excluir del UPDATE/INSERT dinámico (metadata/control)
    DECLARE @exclude TABLE (col SYSNAME);
    INSERT INTO @exclude(col) VALUES
        ('run_id'),
        ('ts_ajuste'),
        ('factor_chancado'),
        ('factor_sal'),
        ('factor_finos'),
        ('estado');  -- <- CLAVE: excluir estado del dinámico

    DECLARE @set NVARCHAR(MAX) = N'';
    DECLARE @ins_cols NVARCHAR(MAX) = N'';
    DECLARE @ins_vals NVARCHAR(MAX) = N'';

    ;WITH common_cols AS (
        SELECT c1.name AS col_name
        FROM sys.columns c1
        INNER JOIN sys.objects o1 ON o1.object_id = c1.object_id
        INNER JOIN sys.schemas s1 ON s1.schema_id = o1.schema_id
        WHERE s1.name = @schema AND o1.name = @tgt

        INTERSECT

        SELECT c2.name
        FROM sys.columns c2
        INNER JOIN sys.objects o2 ON o2.object_id = c2.object_id
        INNER JOIN sys.schemas s2 ON s2.schema_id = o2.schema_id
        WHERE s2.name = @schema AND o2.name = @stg
    )
    SELECT
        @set = @set + CASE WHEN @set = N'' THEN N'' ELSE N',' + CHAR(10) END
             + N'    tgt.' + QUOTENAME(col_name) + N' = src.' + QUOTENAME(col_name),
        @ins_cols = @ins_cols + CASE WHEN @ins_cols = N'' THEN N'' ELSE N',' END
             + QUOTENAME(col_name),
        @ins_vals = @ins_vals + CASE WHEN @ins_vals = N'' THEN N'' ELSE N',' END
             + N'src.' + QUOTENAME(col_name)
    FROM common_cols
    WHERE col_name NOT IN (SELECT col FROM @exclude)
      AND col_name <> 'Fecha';   -- Fecha es clave, no se actualiza en el UPDATE

    -- Forzar estado=1 (una sola vez)
    IF @set = N''
        SET @set = N'    tgt.[estado] = 1';
    ELSE
        SET @set = @set + N',' + CHAR(10) + N'    tgt.[estado] = 1';

    -- FIX 2026-09-09: Fecha SI debe ir en el INSERT (es NOT NULL y es la
    -- clave del MERGE) - antes se excluia tambien del INSERT por el mismo
    -- filtro "col_name <> 'Fecha'" de arriba, lo que rompia el INSERT para
    -- cualquier fecha nunca antes insertada (siempre, en un caso/periodo
    -- nuevo) con "Cannot insert the value NULL into column 'Fecha'".
    SET @ins_cols = N'[Fecha],' + @ins_cols;
    SET @ins_vals = N'src.[Fecha],' + @ins_vals;

    -- En INSERT, agregamos estado explícito (una sola vez)
    SET @ins_cols = @ins_cols + CASE WHEN @ins_cols = N'' THEN N'' ELSE N',' END + N'[estado]';
    SET @ins_vals = @ins_vals + CASE WHEN @ins_vals = N'' THEN N'' ELSE N',' END + N'1';

    DECLARE @sql NVARCHAR(MAX) = N'
MERGE ' + QUOTENAME(@schema) + N'.' + QUOTENAME(@tgt) + N' AS tgt
USING (
    SELECT *
    FROM ' + QUOTENAME(@schema) + N'.' + QUOTENAME(@stg) + N'
    WHERE run_id = @run_id
) AS src
ON tgt.[Fecha] = src.[Fecha]
WHEN MATCHED THEN
    UPDATE SET
' + @set + N'
WHEN NOT MATCHED THEN
    INSERT (' + @ins_cols + N')
    VALUES (' + @ins_vals + N');
';

    EXEC sp_executesql @sql, N'@run_id UNIQUEIDENTIFIER', @run_id=@run_id;
END
"""

with engine.begin() as conn:
    conn.execute(text(NUEVA_DEFINICION))

print("✓ sp_rep_merge_ajustado_dyn actualizado (fix: Fecha ahora se incluye en el INSERT dinamico)")

# Verificacion: vuelve a traer la definicion y confirma que incluye el fix
with engine.connect() as conn:
    result = conn.exec_driver_sql("USE inventar_SpcHidr")
    result = conn.exec_driver_sql("EXEC sp_helptext 'inventar_SpcHidr.sp_rep_merge_ajustado_dyn'")
    texto = "\n".join(r[0] for r in result.fetchall() if r[0] is not None)
    if "[Fecha],'" in texto.replace(" ", "").replace("\n", "") or "N'[Fecha]," in texto:
        print("✓ Verificado: la nueva definicion incluye el fix de Fecha")
    else:
        print("⚠ No se pudo verificar automaticamente el fix, pero el ALTER se ejecuto sin error")
