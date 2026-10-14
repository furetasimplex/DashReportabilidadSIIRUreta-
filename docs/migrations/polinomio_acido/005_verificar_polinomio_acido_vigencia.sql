USE [inventar_SpcHidr_PROD];
GO

SELECT
    DB_NAME() AS base_datos,
    OBJECT_ID(N'[inventar_SpcHidr].[dosis_acido_configuracion]', N'U') AS tabla_configuracion_id,
    OBJECT_ID(N'[inventar_SpcHidr].[fn_calcular_dosis_acido_fecha]', N'FN') AS funcion_fecha_id,
    OBJECT_ID(N'[inventar_SpcHidr].[fn_calcular_dosis_acido]', N'FN') AS funcion_compatibilidad_id,
    OBJECT_ID(N'[inventar_SpcHidr].[sp_registrar_dosis_acido_configuracion]', N'P') AS registro_id,
    OBJECT_ID(N'[inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]', N'IF') AS funcion_reporte_id,
    OBJECT_ID(N'[inventar_SpcHidr].[sp_reporte_turno_emision_test]', N'P') AS procedimiento_reporte_id;

;WITH periodos AS
(
    SELECT
        configuracion_id,
        vigencia_desde,
        DATEADD(DAY, -1, LEAD(vigencia_desde) OVER
        (
            ORDER BY vigencia_desde, configuracion_id
        )) AS vigencia_hasta,
        usuario_submit,
        fecha_submit
    FROM [inventar_SpcHidr].[dosis_acido_configuracion]
)
SELECT
    configuracion_id,
    vigencia_desde,
    vigencia_hasta,
    CASE
        WHEN CAST(GETDATE() AS date) < vigencia_desde THEN 'PROGRAMADA'
        WHEN vigencia_hasta IS NULL OR CAST(GETDATE() AS date) <= vigencia_hasta THEN 'VIGENTE'
        ELSE 'HISTORICA'
    END AS estado,
    usuario_submit,
    fecha_submit
FROM periodos
ORDER BY vigencia_desde;

IF EXISTS
(
    SELECT vigencia_desde
    FROM [inventar_SpcHidr].[dosis_acido_configuracion]
    GROUP BY vigencia_desde
    HAVING COUNT_BIG(*) > 1
)
    THROW 51020, 'Existen fechas de vigencia duplicadas.', 1;

SELECT
    o.[name] AS objeto,
    CASE
        WHEN sm.[definition] LIKE N'%[[]inventar_SpcHidr[]].[[]fn_calcular_dosis_acido_fecha[]]%'
            THEN CAST(1 AS bit)
        ELSE CAST(0 AS bit)
    END AS conectado_funcion_temporal
FROM sys.sql_modules AS sm
INNER JOIN sys.objects AS o ON o.[object_id] = sm.[object_id]
WHERE sm.[object_id] IN
(
    OBJECT_ID(N'[inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]'),
    OBJECT_ID(N'[inventar_SpcHidr].[sp_reporte_turno_emision_test]')
)
ORDER BY o.[name];

SELECT
    [inventar_SpcHidr].[fn_calcular_dosis_acido_fecha]
    (
        CONVERT(date, '19000101', 112), 0.10, 0.20, 1.00
    ) AS prueba_configuracion_historica;
GO
