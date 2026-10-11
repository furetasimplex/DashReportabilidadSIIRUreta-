
    CREATE OR ALTER VIEW
        [inventar_SpcHidr].[v_ajuste_camiones_emision_test]
    AS

    SELECT
        f.Fecha,

        /* --------------------------------------------------------
           FACTOR REAL CALCULADO
           -------------------------------------------------------- */

        f.Factor_Ajuste
            AS Factor_Ajuste_Calculado,

        f.Flag_Factor_Ajuste_Valido,
        f.Estado_Calculo,


        /* --------------------------------------------------------
           APLICACIÓN EFECTIVA
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN ov.modo = 'FORZADO_1'
                    THEN 0
                ELSE auto.Flag_Usa_Ajuste_Automatico
            END
            AS bit
        ) AS Flag_Usa_Ajuste,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN 1.0
            ELSE auto.Factor_Aplicacion_Automatica
        END AS Factor_Aplicacion_Reportes,


        /* --------------------------------------------------------
           VALORES ORIGINALES
           -------------------------------------------------------- */

        f.Apilado_TMH_Bruto_Original,
        f.Apilado_TMH_Neto_Original,

        f.Apilado_TMS_Bruto_Sin_Ajuste,
        f.Apilado_TMS_Neto_Sin_Ajuste,

        f.Chancado_TMS_Sin_Ajuste,
        f.Chancado_TMH_Sin_Ajuste,


        /* --------------------------------------------------------
           VALORES AJUSTADOS CALCULADOS
           NO se alteran por override.
           -------------------------------------------------------- */

        f.Apilado_TMH_Bruto_Ajustado,
        f.Apilado_TMH_Neto_Ajustado,

        f.Apilado_TMS_Bruto_Ajustado,
        f.Apilado_TMS_Neto_Ajustado,

        f.Chancado_TMS_Ajustado,


        /* --------------------------------------------------------
           VALORES EFECTIVOS PARA REPORTE
           -------------------------------------------------------- */

        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN f.Apilado_TMH_Neto_Original
            ELSE auto.Apilado_TMH_Reporte_Automatico
        END AS Apilado_TMH_Reporte,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN f.Apilado_TMS_Neto_Sin_Ajuste
            ELSE auto.Apilado_TMS_Reporte_Automatico
        END AS Apilado_TMS_Reporte,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN f.Chancado_TMS_Sin_Ajuste
            ELSE auto.Chancado_TMS_Reporte_Automatico
        END AS Chancado_TMS_Reporte,


        /* --------------------------------------------------------
           DIFERENCIAS EFECTIVAMENTE APLICADAS
           -------------------------------------------------------- */

        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN 0.0
            ELSE auto.Diferencia_Apilado_TMH_Automatica
        END AS Diferencia_Apilado_TMH_Ajuste,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN 0.0
            ELSE auto.Diferencia_Apilado_TMS_Automatica
        END AS Diferencia_Apilado_TMS_Ajuste,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN 0.0
            ELSE auto.Diferencia_Chancado_TMS_Automatica
        END AS Diferencia_Chancado_TMS_Ajuste,


        CAST
        (
            CASE
                WHEN ov.modo = 'FORZADO_1'
                    THEN 'FORZADO_1_USUARIO'
                ELSE auto.Regla_Aplicacion_Automatica
            END
            AS varchar(80)
        ) AS Regla_Aplicacion,


        /* --------------------------------------------------------
           TRAZABILIDAD EXISTENTE
           -------------------------------------------------------- */

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
        f.Fecha_Calculo,

        f.Carga_Nominal_KOM_TMH_Viaje,
        f.Carga_Nominal_CAT_TMH_Viaje,
        f.Estado_Fuente_MOV_CAM,
        f.Estado_Fuente_POWERBI,
        f.Limite_KOM_TMH_Viaje,
        f.Limite_CAT_TMH_Viaje,


        /* --------------------------------------------------------
           NUEVA TRAZABILIDAD 2B
           -------------------------------------------------------- */

        auto.Factor_Aplicacion_Automatica,

        auto.Flag_Usa_Ajuste_Automatico,

        auto.Regla_Aplicacion_Automatica,

        CAST
        (
            CASE
                WHEN ov.modo = 'FORZADO_1'
                    THEN 'FORZADO_1'
                ELSE 'AUTOMATICO'
            END
            AS varchar(20)
        ) AS Modo_Aplicacion,

        CAST
        (
            CASE
                WHEN ov.modo = 'FORZADO_1'
                    THEN 1
                ELSE 0
            END
            AS bit
        ) AS Flag_Override_1,

        ov.id_override
            AS Id_Control_Aplicacion,

        ov.motivo
            AS Control_Aplicacion_Motivo,

        ov.usuario
            AS Control_Aplicacion_Usuario,

        ov.fecha_registro
            AS Control_Aplicacion_Fecha_Registro


    FROM
        inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test AS f


    OUTER APPLY
    (
        SELECT TOP (1)
            o.id_override,
            o.modo,
            o.motivo,
            o.usuario,
            o.fecha_registro

        FROM
            inventar_SpcHidr.factor_camiones_override_aplicacion_test AS o

        WHERE
            f.Fecha >= o.fecha_desde
            AND f.Fecha <= o.fecha_hasta

        ORDER BY
            o.fecha_registro DESC,
            o.id_override DESC

    ) AS ov


    CROSS APPLY
    (
        SELECT

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
            ) AS Flag_Usa_Ajuste_Automatico,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Factor_Ajuste IS NOT NULL
                    THEN f.Factor_Ajuste
                ELSE 1.0
            END AS Factor_Aplicacion_Automatica,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
                    THEN f.Apilado_TMH_Neto_Ajustado
                ELSE f.Apilado_TMH_Neto_Original
            END AS Apilado_TMH_Reporte_Automatico,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
                    THEN f.Apilado_TMS_Neto_Ajustado
                ELSE f.Apilado_TMS_Neto_Sin_Ajuste
            END AS Apilado_TMS_Reporte_Automatico,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Chancado_TMS_Ajustado IS NOT NULL
                    THEN f.Chancado_TMS_Ajustado
                ELSE f.Chancado_TMS_Sin_Ajuste
            END AS Chancado_TMS_Reporte_Automatico,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
                    THEN
                        f.Apilado_TMH_Neto_Ajustado
                        - f.Apilado_TMH_Neto_Original
                ELSE 0.0
            END AS Diferencia_Apilado_TMH_Automatica,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
                    THEN
                        f.Apilado_TMS_Neto_Ajustado
                        - f.Apilado_TMS_Neto_Sin_Ajuste
                ELSE 0.0
            END AS Diferencia_Apilado_TMS_Automatica,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Chancado_TMS_Ajustado IS NOT NULL
                    THEN
                        f.Chancado_TMS_Ajustado
                        - f.Chancado_TMS_Sin_Ajuste
                ELSE 0.0
            END AS Diferencia_Chancado_TMS_Automatica,


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
                        THEN CONCAT
                        (
                            'FALLBACK_',
                            COALESCE(
                                f.Estado_Calculo,
                                'NO_EVALUABLE'
                            )
                        )

                    ELSE 'FALLBACK_INCONSISTENCIA_CALCULO'
                END
                AS varchar(80)
            ) AS Regla_Aplicacion_Automatica

        ) AS auto;
    