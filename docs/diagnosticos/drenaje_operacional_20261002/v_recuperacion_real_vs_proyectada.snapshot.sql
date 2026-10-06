-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/* ---------------------------------------------------------------------
   4. VISTA DE MERGE: REAL vs PROYECTADO
   FULL JOIN para no perder ni los días que solo tienen real ni los que
   solo tienen proyección. 'fuente' dice de dónde salió cada punto.
   --------------------------------------------------------------------- */
CREATE   VIEW inventar_SpcHidr.v_recuperacion_real_vs_proyectada
AS
SELECT
    COALESCE(p.id_version, -1)                       AS id_version,
    COALESCE(r.campaña_id, p.campaña_id)             AS campaña_id,
    COALESCE(r.parcela_id, p.parcela_id)             AS parcela_id,
    COALESCE(r.pad_id,     p.pad_id)                 AS pad_id,
    COALESCE(r.Fecha_drenaje, CAST(p.fecha AS DATETIME)) AS fecha,
    r.Recuperacion_parcela                           AS recuperacion_real,
    p.recuperacion_proyectada                        AS recuperacion_proyectada,
    CASE
        WHEN r.Recuperacion_parcela IS NOT NULL
         AND p.recuperacion_proyectada IS NOT NULL THEN 'ambos'
        WHEN r.Recuperacion_parcela IS NOT NULL     THEN 'real'
        ELSE 'proyectado'
    END                                              AS fuente,
    CASE
        WHEN r.Recuperacion_parcela IS NOT NULL
         AND p.recuperacion_proyectada IS NOT NULL
        THEN r.Recuperacion_parcela - p.recuperacion_proyectada
    END                                              AS desviacion
FROM inventar_SpcHidr.Recuperaciones_pad r
FULL JOIN inventar_SpcHidr.proyeccion_serie p
       ON  p.campaña_id = r.campaña_id
       AND p.parcela_id = r.parcela_id
       AND p.fecha      = CAST(r.Fecha_drenaje AS DATE);
