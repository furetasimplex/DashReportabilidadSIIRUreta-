>>> inventar_SpcHidr.sp_rep_merge_ajustado_dyn <<<
====================================================================================================
CREATE   PROCEDURE inventar_SpcHidr.sp_rep_merge_ajustado_dyn
    @run_id UNIQUEIDENTIFIER
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @schema SYSNAME = 'inventar_SpcHidr';
    DECLARE @tgt SYSNAME = 'rep_prod_ajustado';
    DECLARE @stg SYSNAME = 'rep_prod
_ajustado_stg';

    -- columnas a excluir del UPDATE/INSERT dinámico (metadata/control)
    DECLARE @exclude TABLE (col SYSNAME);
    INSERT INTO @exclude(col) VALUES
        ('run_id'),
        ('ts_ajuste'),
        ('factor_chancado'),
        ('facto
r_sal'),
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

        INTERSE
CT

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
             +
 QUOTENAME(col_name),
        @ins_vals = @ins_vals + CASE WHEN @ins_vals = N'' THEN N'' ELSE N',' END
             + N'src.' + QUOTENAME(col_name)
    FROM common_cols
    WHERE col_name NOT IN (SELECT col FROM @exclude)
      AND col_name <> 'Fecha';   
-- Fecha es clave, no se actualiza

    -- Forzar estado=1 (una sola vez)
    IF @set = N'' 
        SET @set = N'    tgt.[estado] = 1';
    ELSE
        SET @set = @set + N',' + CHAR(10) + N'    tgt.[estado] = 1';

    -- En INSERT, agregamos estado expl
ícito (una sola vez)
    SET @ins_cols = @ins_cols + CASE WHEN @ins_cols = N'' THEN N'' ELSE N',' END + N'[estado]';
    SET @ins_vals = @ins_vals + CASE WHEN @ins_vals = N'' THEN N'' ELSE N',' END + N'1';

    DECLARE @sql NVARCHAR(MAX) = N'
MERGE ' + QU
OTENAME(@schema) + N'.' + QUOTENAME(@tgt) + N' AS tgt
USING (
    SELECT *
    FROM ' + QUOTENAME(@schema) + N'.' + QUOTENAME(@stg) + N'
    WHERE run_id = @run_id
) AS src
ON tgt.[Fecha] = src.[Fecha]
WHEN MATCHED THEN
    UPDATE SET
