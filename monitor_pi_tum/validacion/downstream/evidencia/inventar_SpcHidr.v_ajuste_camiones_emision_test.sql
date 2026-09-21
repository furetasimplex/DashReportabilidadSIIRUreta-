
CREATE   VIEW
    [inventar_SpcHidr].[v_ajuste_camiones_emision_test]
AS
SELECT
    f.Fecha,

    /* ============================================================
       Factor real calculado
       ============================================================ */
    f.Factor_Ajuste
        AS Factor_Ajuste_Calculado,

    f.Flag_Factor_Ajuste_Valido,
    f.Estado_Calculo,

    /* ============================================================
       Control de aplicación
       Solo vale 1 cuando existe un cálculo completo y utilizable.
       ============================================================ */
    CAST
    (
        CASE
            WHEN f.Flag_Factor_Ajuste_Valido = 1
             AND f.Factor_Ajuste IS NOT NULL
             AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
             AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
             AND f.Chancado_TMS_Ajustado IS NOT NULL
                THEN 1
            ELSE 0
        END
        AS bit
    ) AS Flag_Usa_Ajuste,

    /* ============================================================
       Factor operativo para aplicar en los reportes

       Importante:
       - No reemplaza al factor real.
       - Cuando el cálculo no es evaluable, usa 1 solo para mantener
         el valor basal en la salida diaria.
       ============================================================ */
    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Factor_Ajuste IS NOT NULL
            THEN f.Factor_Ajuste
        ELSE 1.0
    END AS Factor_Aplicacion_Reportes,

    /* ============================================================
       Valores originales
       ============================================================ */
    f.Apilado_TMH_Bruto_Original,
    f.Apilado_TMH_Neto_Original,

    f.Apilado_TMS_Bruto_Sin_Ajuste,
    f.Apilado_TMS_Neto_Sin_Ajuste,

    f.Chancado_TMS_Sin_Ajuste,
    f.Chancado_TMH_Sin_Ajuste,

    /* ============================================================
       Valores ajustados calculados
       ============================================================ */
    f.Apilado_TMH_Bruto_Ajustado,
    f.Apilado_TMH_Neto_Ajustado,

    f.Apilado_TMS_Bruto_Ajustado,
    f.Apilado_TMS_Neto_Ajustado,

    f.Chancado_TMS_Ajustado,

    /* ============================================================
       Valores efectivos para Datos Conciliados y Análisis TM
       ============================================================ */
    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
            THEN f.Apilado_TMH_Neto_Ajustado
        ELSE f.Apilado_TMH_Neto_Original
    END AS Apilado_TMH_Reporte,

    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
            THEN f.Apilado_TMS_Neto_Ajustado
        ELSE f.Apilado_TMS_Neto_Sin_Ajuste
    END AS Apilado_TMS_Reporte,

    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Chancado_TMS_Ajustado IS NOT NULL
            THEN f.Chancado_TMS_Ajustado
        ELSE f.Chancado_TMS_Sin_Ajuste
    END AS Chancado_TMS_Reporte,

    /* ============================================================
       Diferencias introducidas por el ajuste
       ============================================================ */
    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
            THEN
                f.Apilado_TMH_Neto_Ajustado
                - f.Apilado_TMH_Neto_Original
        ELSE 0.0
    END AS Diferencia_Apilado_TMH_Ajuste,

    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
            THEN
                f.Apilado_TMS_Neto_Ajustado
                - f.Apilado_TMS_Neto_Sin_Ajuste
        ELSE 0.0
    END AS Diferencia_Apilado_TMS_Ajuste,

    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Chancado_TMS_Ajustado IS NOT NULL
            THEN
                f.Chancado_TMS_Ajustado
                - f.Chancado_TMS_Sin_Ajuste
        ELSE 0.0
    END AS Diferencia_Chancado_TMS_Ajuste,

    /* ============================================================
       Descripción de la regla aplicada
       ============================================================ */
    CAST
    (
        CASE
            WHEN f.Flag_Factor_Ajuste_Valido = 1
             AND f.Factor_Ajuste IS NOT NULL
             AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
             AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
             AND f.Chancado_TMS_Ajustado IS NOT NULL
                THEN 'APLICA_AJUSTE_VALIDADO'

            WHEN f.Estado_Calculo = 'SIN_DATOS_CAMIONES'
                THEN 'FALLBACK_SIN_DATOS_CAMIONES'

            WHEN f.Flag_Factor_Ajuste_Valido = 0
                THEN CONCAT(
                    'FALLBACK_',
                    COALESCE(f.Estado_Calculo, 'NO_EVALUABLE')
                )

            ELSE 'FALLBACK_INCONSISTENCIA_CALCULO'
        END
        AS varchar(80)
    ) AS Regla_Aplicacion,

    /* ============================================================
       Trazabilidad complementaria
       ============================================================ */
    f.Sal_TMH_Dia,
    f.Humedad_Pct,

    f.Inventario_Chancado_TMS_Actual,
    f.Inventario_Chancado_TMS_Anterior,
    f.Delta_Inventario_Chancado_TMS,

    f.SRR_TMS_Turno_A,
    f.SRR_TMS_Turno_B,
    f.SRR_TMS_Dia,

    f.Produccion_KOM_TMH,
    f.Produccion_CAT_TMH,

    f.Vueltas_KOM,
    f.Vueltas_CAT,

    f.Carga_KOM_TMH_Viaje_Sin_Ajuste,
    f.Carga_CAT_TMH_Viaje_Sin_Ajuste,

    f.KOM_TMH_Corregido,
    f.CAT_TMH_Corregido,

    f.Cantidad_Registros_Originales,
    f.Cantidad_Registros_Validos,
    f.Cantidad_Duplicados_Eliminados,

    f.Metodo,
    f.Fuente_Camiones,
    f.Fecha_Calculo

FROM
    [inventar_SpcHidr].[Control_Factor_Ajuste_Camiones_v2_test] AS f;
