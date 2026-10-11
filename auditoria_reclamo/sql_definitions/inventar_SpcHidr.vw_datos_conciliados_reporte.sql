CREATE   VIEW inventar_SpcHidr.vw_datos_conciliados_reporte
AS
WITH oficial_ranked AS
(
    SELECT
        v.[Fecha],
        v.[Chancado_TMS_Real],
        v.[Humedad_Turno_A],
        v.[Humedad_Turno_B],
        v.[Humedad_promedio_dia],
        v.[Sal_turno_A],
        v.[Sal_Turno_B],
        v.[Sal_promedio_dia],
        v.[Apilado_TMH_turno_A],
        v.[Apilado_TMH_turno_B],
        v.[Apilado_TMH_promedio_dia],
        v.[Apilado_TMS_Real],
        v.[Apilado_TMS_Plan],
        v.[Campana_apilado],
        v.[Modulo_apilado],
        v.[Avance_apilado],
        v.[Ley_CuT_Real],
        v.[Ley_CuT_Plan],
        v.[Cobre_fino_Apilado_Real],
        v.[Cobre_fino_Apilado_Plan],
        v.[TMS_Rotopala_1_Real],
        v.[TMS_Rotopala_1_Plan],
        v.[Campana_reclamo_oxidos],
        v.[Modulo_reclamo_oxidos],
        v.[Avance_reclamo_oxidos],
        v.[TMS_Rotopala_2_Real],
        v.[TMS_Rotopala_2_Plan],
        v.[Campana_reclamo_sulfuros],
        v.[modulo_reclamo_sulfuros],
        v.[Avance_reclamo_sulfuros],
        v.[Camiones_TMS_Reclamo_Oxidos],
        v.[Camiones_TMS_Reclamo_Sulfuros],
        v.[Movido],
        v.[Extraido],
        v.[Camiones_TMS_total],
        v.[Camiones_TMS_plan],
        v.[Campana_reclamo_camiones],
        v.[Modulo_reclamo_camiones],
        v.[Total_Ripios_Incluye_Camiones_Real],
        v.[Total_Ripios_Incluye_Camiones_Plan],
        v.[Produccion_Catodos_Real],
        v.[Produccion_Catodos_Plan],
        CAST(1 AS INT) AS [Estado],
        CAST(0 AS BIT) AS [es_preliminar],
        CAST(1 AS BIT) AS [es_oficial],
        CAST('OFICIAL' AS VARCHAR(20)) AS [fuente_reporte],
        ROW_NUMBER() OVER
        (
            PARTITION BY v.[Fecha]
            ORDER BY
                ISNULL(v.[fecha_validacion], '19000101') DESC,
                ISNULL(v.[validation_id], 0) DESC
        ) AS rn
    FROM inventar_SpcHidr.Datos_conciliados_of_ver v
    WHERE ISNULL(v.[estado_validacion], 'VALIDADO') = 'VALIDADO'
),
oficial AS
(
    SELECT
        [Fecha],
        [Chancado_TMS_Real],
        [Humedad_Turno_A],
        [Humedad_Turno_B],
        [Humedad_promedio_dia],
        [Sal_turno_A],
        [Sal_Turno_B],
        [Sal_promedio_dia],
        [Apilado_TMH_turno_A],
        [Apilado_TMH_turno_B],
        [Apilado_TMH_promedio_dia],
        [Apilado_TMS_Real],
        [Apilado_TMS_Plan],
        [Campana_apilado],
        [Modulo_apilado],
        [Avance_apilado],
        [Ley_CuT_Real],
        [Ley_CuT_Plan],
        [Cobre_fino_Apilado_Real],
        [Cobre_fino_Apilado_Plan],
        [TMS_Rotopala_1_Real],
        [TMS_Rotopala_1_Plan],
        [Campana_reclamo_oxidos],
        [Modulo_reclamo_oxidos],
        [Avance_reclamo_oxidos],
        [TMS_Rotopala_2_Real],
        [TMS_Rotopala_2_Plan],
        [Campana_reclamo_sulfuros],
        [modulo_reclamo_sulfuros],
        [Avance_reclamo_sulfuros],
        [Camiones_TMS_Reclamo_Oxidos],
        [Camiones_TMS_Reclamo_Sulfuros],
        [Movido],
        [Extraido],
        [Camiones_TMS_total],
        [Camiones_TMS_plan],
        [Campana_reclamo_camiones],
        [Modulo_reclamo_camiones],
        [Total_Ripios_Incluye_Camiones_Real],
        [Total_Ripios_Incluye_Camiones_Plan],
        [Produccion_Catodos_Real],
        [Produccion_Catodos_Plan],
        [Estado],
        [es_preliminar],
        [es_oficial],
        [fuente_reporte]
    FROM oficial_ranked
    WHERE rn = 1
),
provisorio AS
(
    SELECT
        b.[Fecha],
        b.[Chancado_TMS_Real],
        b.[Humedad_Turno_A],
        b.[Humedad_Turno_B],
        b.[Humedad_promedio_dia],
        b.[Sal_turno_A],
        b.[Sal_Turno_B],
        b.[Sal_promedio_dia],
        b.[Apilado_TMH_turno_A],
        b.[Apilado_TMH_turno_B],
        b.[Apilado_TMH_promedio_dia],
        b.[Apilado_TMS_Real],
        b.[Apilado_TMS_Plan],
        b.[Campana_apilado],
        b.[Modulo_apilado],
        b.[Avance_apilado],
        b.[Ley_CuT_Real],
        b.[Ley_CuT_Plan],
        b.[Cobre_fino_Apilado_Real],
        b.[Cobre_fino_Apilado_Plan],
        b.[TMS_Rotopala_1_Real],
        b.[TMS_Rotopala_1_Plan],
        b.[Campana_reclamo_oxidos],
        b.[Modulo_reclamo_oxidos],
        b.[Avance_reclamo_oxidos],
        b.[TMS_Rotopala_2_Real],
        b.[TMS_Rotopala_2_Plan],
        b.[Campana_reclamo_sulfuros],
        b.[modulo_reclamo_sulfuros],
        b.[Avance_reclamo_sulfuros],
        b.[Camiones_TMS_Reclamo_Oxidos],
        b.[Camiones_TMS_Reclamo_Sulfuros],
        b.[Movido],
        b.[Extraido],
        b.[Camiones_TMS_total],
        b.[Camiones_TMS_plan],
        b.[Campana_reclamo_camiones],
        b.[Modulo_reclamo_camiones],
        b.[Total_Ripios_Incluye_Camiones_Real],
        b.[Total_Ripios_Incluye_Camiones_Plan],
        b.[Produccion_Catodos_Real],
        b.[Produccion_Catodos_Plan],
        CAST(0 AS INT) AS [Estado],
        CAST(1 AS BIT) AS [es_preliminar],
        CAST(0 AS BIT) AS [es_oficial],
        CAST('PROVISORIO' AS VARCHAR(20)) AS [fuente_reporte]
    FROM inventar_SpcHidr.Datos_conciliados_of b
    LEFT JOIN oficial o
        ON b.[Fecha] = o.[Fecha]
    WHERE o.[Fecha] IS NULL
)
SELECT *
FROM oficial

UNION ALL

SELECT *
FROM provisorio;