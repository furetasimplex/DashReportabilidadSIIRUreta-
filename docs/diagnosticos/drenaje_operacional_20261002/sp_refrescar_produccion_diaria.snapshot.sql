-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/* =====================================================================
   PROCEDIMIENTO DE REFRESCO DE LA PRODUCCION CONGELADA
   Ejecutar este archivo COMPLETO y SOLO: un CREATE PROCEDURE debe ser
   la primera sentencia de su lote.
   Requiere que 03_grupos_y_produccion.sql ya haya creado las tablas.
   ===================================================================== */

CREATE   PROCEDURE inventar_SpcHidr.sp_refrescar_produccion_diaria
    @campaña_id INT = NULL,      -- NULL = todas
    @desde      DATE = NULL      -- NULL = desde el principio
AS
BEGIN
    SET NOCOUNT ON;

    DELETE FROM inventar_SpcHidr.produccion_diaria_parcela
    WHERE (@campaña_id IS NULL OR campaña_id = @campaña_id)
      AND (@desde      IS NULL OR fecha     >= @desde);

    ;WITH base AS (
        SELECT r.[campaña_id], r.parcela_id, r.pad_id, r.PAD, r.Campana,
               CAST(r.Fecha_drenaje AS DATE)  AS fecha,
               r.Recuperacion_parcela         AS recuperacion,
               a.fino_apilado_cu
        FROM inventar_SpcHidr.Recuperaciones_pad r
        LEFT JOIN inventar_SpcHidr.res_parcelas_apilado a
               ON  a.Parcela = r.Parcela
              AND  a.Campana = r.Campana
              AND  a.PAD     = r.PAD
        WHERE (@campaña_id IS NULL OR r.[campaña_id] = @campaña_id)
          AND (@desde      IS NULL OR r.Fecha_drenaje >= @desde)
    ),
    calc AS (
        SELECT *,
               fino_apilado_cu * recuperacion / 100.0 AS cu_recuperado,
               DATEDIFF(DAY, MIN(fecha) OVER (
                   PARTITION BY [campaña_id], parcela_id), fecha) AS dia_drenaje
        FROM base
    ),
    dif AS (
        SELECT *,
               cu_recuperado - LAG(cu_recuperado) OVER (
                   PARTITION BY [campaña_id], parcela_id
                   ORDER BY fecha) AS delta
        FROM calc
    )
    INSERT INTO inventar_SpcHidr.produccion_diaria_parcela
        ([campaña_id], parcela_id, pad_id, PAD, Campana, fecha, dia_drenaje,
         recuperacion, fino_apilado_cu, cu_recuperado, cu_remanente, produccion)
    SELECT [campaña_id], parcela_id, pad_id, PAD, Campana, fecha, dia_drenaje,
           recuperacion, fino_apilado_cu, cu_recuperado,
           fino_apilado_cu - cu_recuperado,
           ISNULL(delta, cu_recuperado)     -- el primer día es el acumulado
    FROM dif;

    SELECT @@ROWCOUNT AS filas_congeladas;
END;

/* Uso:
   EXEC inventar_SpcHidr.sp_refrescar_produccion_diaria;
   EXEC inventar_SpcHidr.sp_refrescar_produccion_diaria @campaña_id = 11;
   EXEC inventar_SpcHidr.sp_refrescar_produccion_diaria @desde = '2026-01-01';
*/
