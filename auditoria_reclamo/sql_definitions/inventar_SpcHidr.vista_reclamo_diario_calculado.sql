CREATE   VIEW
[inventar_SpcHidr].[vista_reclamo_diario_calculado]
AS

/* ========================================================================
   PAD 1 — CONTRATO PRODUCTIVO ACTUAL
========================================================================= */
SELECT
    p.fecha_reporte,
    p.pad_id,
    p.[campaña_id],
    p.modulo_id,
    p.volumen_diario_m3,
    p.avance_porcentaje,
    p.avance_incremental,
    p.tms_total_apilado,
    p.finos_totales_apilados,
    p.tonelaje_reclamado_diario,
    p.fecha_operacion,
    p.modulo_numero,
    p.avance_acumulado_pad,
    p.cantidad_modulos_fuente,
    p.tms_base_modulo,
    p.m3_totales,
    p.densidad_exacta,
    p.volumen_camiones_aprobado_m3,
    p.tms_camiones_aprobado,
    p.periodo_reporte,
    p.fecha_corte_camiones,
    p.estado_configuracion_corte,
    p.fuente_configuracion_corte,
    p.regla_corte_camiones,
    p.medicion_valida,
    p.motivo_medicion,
    p.fuente_control_medicion,
    p.fecha_estado_utilizado,
    p.regla_estado_topografico,
    p.campaña_anterior_pad,
    p.modulo_anterior_pad,
    p.modulo_numero_anterior_pad,
    p.avance_anterior_pad,
    p.tms_anterior_pad,
    p.metodo_calculo

FROM [inventar_SpcHidr].[vista_reclamo_diario_calculado_oxidos_of] p

WHERE p.pad_id = 1


UNION ALL


/* ========================================================================
   PAD 2 — V4.9 TOPOGRAFÍA, MAPEADA AL CONTRATO OFICIAL
========================================================================= */
SELECT
    CAST(s.fecha_reporte AS date)
        AS fecha_reporte,

    CAST(s.pad_id AS int)
        AS pad_id,

    CAST(s.[campaña_id] AS int)
        AS [campaña_id],

    CAST(s.modulo_id AS int)
        AS modulo_id,

    CAST(COALESCE(b.volumen_diario_m3, 0.0) AS float)
        AS volumen_diario_m3,

    CAST(s.avance_porcentaje AS float)
        AS avance_porcentaje,

    CAST(s.avance_incremental AS float)
        AS avance_incremental,

    CAST(s.tms_disponible_roto AS float)
        AS tms_total_apilado,

    CAST(COALESCE(b.finos_totales_apilados, 0.0) AS float)
        AS finos_totales_apilados,

    CAST(s.tonelaje_reclamado_diario AS float)
        AS tonelaje_reclamado_diario,

    CAST(s.fecha_operacion AS date)
        AS fecha_operacion,

    CAST(s.modulo_numero AS int)
        AS modulo_numero,

    CAST(b.avance_acumulado_pad AS float)
        AS avance_acumulado_pad,

    CAST(b.cantidad_modulos_fuente AS int)
        AS cantidad_modulos_fuente,

    CAST(b.tms_base_modulo AS float)
        AS tms_base_modulo,

    CAST(b.m3_totales AS float)
        AS m3_totales,

    CAST(b.densidad_exacta AS float)
        AS densidad_exacta,

    CAST(b.volumen_camiones_aprobado_m3 AS float)
        AS volumen_camiones_aprobado_m3,

    CAST(b.tms_camiones_aprobado AS float)
        AS tms_camiones_aprobado,

    CAST(b.periodo_reporte AS date)
        AS periodo_reporte,

    CAST(b.fecha_corte_camiones AS date)
        AS fecha_corte_camiones,

    CAST(
        CASE
            WHEN b.fecha_corte_sesion IS NOT NULL
                THEN 'CORTE_EXPLICITO_SP'
            WHEN b.estado_configuracion_corte = 'PERIODO_CERRADO'
                THEN 'PERIODO_CERRADO'
            ELSE 'PERIODO_ABIERTO'
        END
        AS varchar(20)
    ) AS estado_configuracion_corte,

    CAST(b.fuente_configuracion_corte AS varchar(150))
        AS fuente_configuracion_corte,

    CAST(
        CASE
            WHEN b.fecha_corte_sesion IS NOT NULL
                THEN 'CORTE_EXPLICITO_SP'
            WHEN b.estado_configuracion_corte = 'PERIODO_CERRADO'
                THEN 'CORTE_PERIODO_CERRADO'
            WHEN b.fecha_ultima_carga_periodo IS NOT NULL
                THEN 'CORTE_ULTIMA_CARGA'
            WHEN b.fecha_corte_camiones IS NOT NULL
                THEN 'CORTE_CONFIG_RESPALDO'
            ELSE 'SIN_CORTE_CAMIONES'
        END
        AS varchar(27)
    ) AS regla_corte_camiones,

    CAST(s.medicion_valida AS bit)
        AS medicion_valida,

    CAST(s.motivo_medicion AS varchar(250))
        AS motivo_medicion,

    CAST(b.fuente_control_medicion AS varchar(250))
        AS fuente_control_medicion,

    CAST(b.fecha_estado_utilizado AS date)
        AS fecha_estado_utilizado,

    CAST(b.regla_estado_topografico AS varchar(29))
        AS regla_estado_topografico,

    CAST(s.campaña_anterior AS int)
        AS campaña_anterior_pad,

    CAST(s.modulo_id_anterior AS int)
        AS modulo_anterior_pad,

    CAST(s.modulo_numero_anterior AS int)
        AS modulo_numero_anterior_pad,

    CAST(s.avance_topografia_anterior AS float)
        AS avance_anterior_pad,

    CAST(s.tms_disponible_anterior AS float)
        AS tms_anterior_pad,

    CAST(s.metodo_calculo AS varchar(34))
        AS metodo_calculo

FROM [inventar_SpcHidr].
     [vista_reclamo_diario_calculado_sulfuros_of] s

INNER JOIN [inventar_SpcHidr].
           [vista_reclamo_diario_calculado_sulfuros_base_of] b
    ON  b.fecha_operacion = s.fecha_operacion
    AND b.pad_id          = s.pad_id
    AND b.[campaña_id]    = s.[campaña_id]
    AND b.modulo_id       = s.modulo_id

WHERE s.pad_id = 2;