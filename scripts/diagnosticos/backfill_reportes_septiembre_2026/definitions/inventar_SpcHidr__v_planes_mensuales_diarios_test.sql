
CREATE   VIEW
    [inventar_SpcHidr].[v_planes_mensuales_diarios_test]
AS

WITH PlanesRankeados AS
(
    SELECT
        pm.id,
        pm.fecha,

        pm.cut,
        pm.cu_fino,

        pm.rotopala1,
        pm.rotopala2,
        pm.camiones,

        pm.produccion_catodos,

        pm.srr,
        pm.cut_srr,

        ROW_NUMBER() OVER
        (
            PARTITION BY pm.fecha
            ORDER BY pm.id DESC
        ) AS rn

    FROM [inventar_SpcHidr].[planes_mensuales] pm

    WHERE pm.fecha IS NOT NULL
)

SELECT
    id,
    fecha AS Fecha,

    /* ========================================================
       CAMPOS DE APILADO
       Solo se conservan para diagnóstico.
       No reemplazan la fuente ya validada del reporte.
       ======================================================== */

    cut
        AS Ley_CuT_Plan_Fuente,

    cu_fino
        AS Cobre_Fino_Apilado_Plan_Fuente,

    /* ========================================================
       ROTOPALAS
       ======================================================== */

    rotopala1
        AS TMS_Rotopala_1_Plan,

    rotopala2
        AS TMS_Rotopala_2_Plan,

    /* ========================================================
       CAMIONES
       ======================================================== */

    camiones
        AS Camiones_TMS_Plan,

    /* ========================================================
       PRODUCCIÓN CATÓDICA
       ======================================================== */

    produccion_catodos
        AS Produccion_Catodos_Plan,

    /* ========================================================
       SRR

       En enero, los NULL de SRR y CuT SRR corresponden
       a valores históricos iguales a cero.
       ======================================================== */

    COALESCE(srr, 0)
        AS SRR_TMS_Plan,

    COALESCE(cut_srr, 0)
        AS Ley_CuT_Plan_SRR,

    /* ========================================================
       BANDERAS DE CONTROL
       ======================================================== */

    CASE
        WHEN rotopala1 IS NULL
            THEN 'SIN_PLAN'
        WHEN rotopala1 < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Rotopala_1_Plan,

    CASE
        WHEN rotopala2 IS NULL
            THEN 'SIN_PLAN'
        WHEN rotopala2 < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Rotopala_2_Plan,

    CASE
        WHEN camiones IS NULL
            THEN 'SIN_PLAN'
        WHEN camiones < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Camiones_Plan,

    CASE
        WHEN produccion_catodos IS NULL
            THEN 'SIN_PLAN'
        WHEN produccion_catodos < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Produccion_Catodos_Plan,

    CASE
        WHEN srr IS NULL
            THEN 'OK_CERO_DESDE_NULL'
        WHEN srr < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_SRR_TMS_Plan,

    CASE
        WHEN cut_srr IS NULL
            THEN 'OK_CERO_DESDE_NULL'
        WHEN cut_srr < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Ley_CuT_SRR_Plan,

    CASE
        WHEN cut IS NULL
            THEN 'SIN_PLAN'

        WHEN cut < 0
            THEN 'PLAN_NEGATIVO'

        WHEN cut > 2
            THEN 'REVISAR_VALOR_ALTO'

        ELSE 'OK'
    END AS Flag_Ley_CuT_Apilado_Fuente,

    CASE
        WHEN cu_fino IS NULL
            THEN 'SIN_PLAN'

        WHEN cu_fino < 0
            THEN 'PLAN_NEGATIVO'

        WHEN cu_fino > 1000
            THEN 'REVISAR_VALOR_ALTO'

        ELSE 'OK'
    END AS Flag_Cobre_Fino_Apilado_Fuente

FROM PlanesRankeados

WHERE rn = 1;
