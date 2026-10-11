CREATE VIEW
inventar_SpcHidr.v_bd_ton_t12_contingencia_test
AS

WITH ton_intervalo AS
(
    SELECT
        Fecha = CAST(r.Fecha AS date),

        Ton_Intervalo_TM1_TA =
            NULLIF
            (
                MAX
                (
                    CASE
                        WHEN r.Torre = 'T1'
                         AND r.Turno = 'A'
                            THEN r.Ton_Real
                    END
                ),
                0
            ),

        Ton_Intervalo_TM1_TB =
            NULLIF
            (
                MAX
                (
                    CASE
                        WHEN r.Torre = 'T1'
                         AND r.Turno = 'B'
                            THEN r.Ton_Real
                    END
                ),
                0
            ),

        Ton_Intervalo_TM2_TA =
            NULLIF
            (
                MAX
                (
                    CASE
                        WHEN r.Torre = 'T2'
                         AND r.Turno = 'A'
                            THEN r.Ton_Real
                    END
                ),
                0
            ),

        Ton_Intervalo_TM2_TB =
            NULLIF
            (
                MAX
                (
                    CASE
                        WHEN r.Torre = 'T2'
                         AND r.Turno = 'B'
                            THEN r.Ton_Real
                    END
                ),
                0
            )

    FROM inventar_SpcHidr.v_reporte_diario_emulado_excel AS r
    WHERE r.Torre IN ('T1','T2')

    GROUP BY
        CAST(r.Fecha AS date)
),

/* ============================================================
   RESOLVER T1/T2

   La vista de resolver se referencia UNA sola vez.

   Luego se transforma:
       CV008 A -> TM1 TA
       CV008 B -> TM1 TB
       CV108 A -> TM2 TA
       CV108 B -> TM2 TB

   No cambia ninguna decisión PI/TUM.
   ============================================================ */
resolver_t12 AS
(
    SELECT
        r.fecha_operacional,

        /* FUENTE */
        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV008'
                 AND r.turno = 'A'
                    THEN r.fuente_resuelta
            END
        ) AS Fuente_Resolver_TM1_TA,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV008'
                 AND r.turno = 'B'
                    THEN r.fuente_resuelta
            END
        ) AS Fuente_Resolver_TM1_TB,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV108'
                 AND r.turno = 'A'
                    THEN r.fuente_resuelta
            END
        ) AS Fuente_Resolver_TM2_TA,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV108'
                 AND r.turno = 'B'
                    THEN r.fuente_resuelta
            END
        ) AS Fuente_Resolver_TM2_TB,

        /* TIPO TUM */
        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV008'
                 AND r.turno = 'A'
                    THEN r.tipo_tum
            END
        ) AS Tipo_TUM_TM1_TA,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV008'
                 AND r.turno = 'B'
                    THEN r.tipo_tum
            END
        ) AS Tipo_TUM_TM1_TB,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV108'
                 AND r.turno = 'A'
                    THEN r.tipo_tum
            END
        ) AS Tipo_TUM_TM2_TA,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV108'
                 AND r.turno = 'B'
                    THEN r.tipo_tum
            END
        ) AS Tipo_TUM_TM2_TB,

        /* VALOR FINAL DEL RESOLVER */
        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV008'
                 AND r.turno = 'A'
                    THEN r.valor_final_resuelto
            END
        ) AS Valor_Resolver_TM1_TA,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV008'
                 AND r.turno = 'B'
                    THEN r.valor_final_resuelto
            END
        ) AS Valor_Resolver_TM1_TB,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV108'
                 AND r.turno = 'A'
                    THEN r.valor_final_resuelto
            END
        ) AS Valor_Resolver_TM2_TA,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV108'
                 AND r.turno = 'B'
                    THEN r.valor_final_resuelto
            END
        ) AS Valor_Resolver_TM2_TB,

        /* MOTIVO */
        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV008'
                 AND r.turno = 'A'
                    THEN r.motivo_decision
            END
        ) AS Motivo_TM1_TA,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV008'
                 AND r.turno = 'B'
                    THEN r.motivo_decision
            END
        ) AS Motivo_TM1_TB,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV108'
                 AND r.turno = 'A'
                    THEN r.motivo_decision
            END
        ) AS Motivo_TM2_TA,

        MAX
        (
            CASE
                WHEN r.equipo_codigo = 'PRINCIPAL_CV108'
                 AND r.turno = 'B'
                    THEN r.motivo_decision
            END
        ) AS Motivo_TM2_TB

    FROM (
    SELECT fecha_operacional,turno,equipo_codigo,fuente_resuelta,
           valor_final_resuelto,tipo_tum,motivo_decision
    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno WHERE fecha_operacional < '2026-09-01'
    UNION ALL
    SELECT fecha_operacional,turno,equipo_codigo,fuente_resuelta,
           valor_final_resuelto,tipo_tum,motivo_decision
    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test WHERE fecha_operacional >= '2026-09-01'
) AS r

    WHERE r.equipo_codigo IN
    (
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108'
    )

    GROUP BY
        r.fecha_operacional
)

SELECT
    t.Fecha,

    /* ============================================================
       BASE ORIGINAL: intervalo real de muestreo
       ============================================================ */
    CAST(t.Ton_Intervalo_TM1_TA AS decimal(18,3))
        AS Ton_Intervalo_TM1_TA,

    CAST(t.Ton_Intervalo_TM1_TB AS decimal(18,3))
        AS Ton_Intervalo_TM1_TB,

    CAST(t.Ton_Intervalo_TM2_TA AS decimal(18,3))
        AS Ton_Intervalo_TM2_TA,

    CAST(t.Ton_Intervalo_TM2_TB AS decimal(18,3))
        AS Ton_Intervalo_TM2_TB,

    /* ============================================================
       PI OPERACIONAL
       ============================================================ */
    CAST(a.TMH_CV008_A AS decimal(18,3))
        AS TMH_PI_Operacional_TM1_TA,

    CAST(a.TMH_CV008_B AS decimal(18,3))
        AS TMH_PI_Operacional_TM1_TB,

    CAST(a.TMH_CV108_A AS decimal(18,3))
        AS TMH_PI_Operacional_TM2_TA,

    CAST(a.TMH_CV108_B AS decimal(18,3))
        AS TMH_PI_Operacional_TM2_TB,

    /* ============================================================
       RESOLVER
       ============================================================ */
    r.Fuente_Resolver_TM1_TA,
    r.Fuente_Resolver_TM1_TB,
    r.Fuente_Resolver_TM2_TA,
    r.Fuente_Resolver_TM2_TB,

    r.Tipo_TUM_TM1_TA,
    r.Tipo_TUM_TM1_TB,
    r.Tipo_TUM_TM2_TA,
    r.Tipo_TUM_TM2_TB,

    CAST(r.Valor_Resolver_TM1_TA AS decimal(18,3))
        AS Valor_Resolver_TM1_TA,

    CAST(r.Valor_Resolver_TM1_TB AS decimal(18,3))
        AS Valor_Resolver_TM1_TB,

    CAST(r.Valor_Resolver_TM2_TA AS decimal(18,3))
        AS Valor_Resolver_TM2_TA,

    CAST(r.Valor_Resolver_TM2_TB AS decimal(18,3))
        AS Valor_Resolver_TM2_TB,

    /* ============================================================
       TONELAJE FINAL BD TON

       HISTÓRICO:
           intervalo real

       >= 01-09:
           PI           -> intervalo real
           TUM > 0      -> turno TUM completo
           TUM = 0      -> NULL
           SIN_RESOLVER -> NULL
       ============================================================ */

    CAST
    (
        CASE
            WHEN t.Fecha < '2026-09-01'
                THEN t.Ton_Intervalo_TM1_TA

            WHEN r.Fuente_Resolver_TM1_TA = 'PI'
                THEN t.Ton_Intervalo_TM1_TA

            WHEN r.Fuente_Resolver_TM1_TA = 'TUM'
             AND r.Valor_Resolver_TM1_TA > 0
                THEN r.Valor_Resolver_TM1_TA

            ELSE NULL
        END
        AS decimal(18,3)
    ) AS TMH_TM1_TA_Resuelto,

    CAST
    (
        CASE
            WHEN t.Fecha < '2026-09-01'
                THEN t.Ton_Intervalo_TM1_TB

            WHEN r.Fuente_Resolver_TM1_TB = 'PI'
                THEN t.Ton_Intervalo_TM1_TB

            WHEN r.Fuente_Resolver_TM1_TB = 'TUM'
             AND r.Valor_Resolver_TM1_TB > 0
                THEN r.Valor_Resolver_TM1_TB

            ELSE NULL
        END
        AS decimal(18,3)
    ) AS TMH_TM1_TB_Resuelto,

    CAST
    (
        CASE
            WHEN t.Fecha < '2026-09-01'
                THEN t.Ton_Intervalo_TM2_TA

            WHEN r.Fuente_Resolver_TM2_TA = 'PI'
                THEN t.Ton_Intervalo_TM2_TA

            WHEN r.Fuente_Resolver_TM2_TA = 'TUM'
             AND r.Valor_Resolver_TM2_TA > 0
                THEN r.Valor_Resolver_TM2_TA

            ELSE NULL
        END
        AS decimal(18,3)
    ) AS TMH_TM2_TA_Resuelto,

    CAST
    (
        CASE
            WHEN t.Fecha < '2026-09-01'
                THEN t.Ton_Intervalo_TM2_TB

            WHEN r.Fuente_Resolver_TM2_TB = 'PI'
                THEN t.Ton_Intervalo_TM2_TB

            WHEN r.Fuente_Resolver_TM2_TB = 'TUM'
             AND r.Valor_Resolver_TM2_TB > 0
                THEN r.Valor_Resolver_TM2_TB

            ELSE NULL
        END
        AS decimal(18,3)
    ) AS TMH_TM2_TB_Resuelto,

    /* ============================================================
       EVALUABILIDAD INDIVIDUAL
       ============================================================ */

    CAST
    (
        CASE
            WHEN t.Fecha < '2026-09-01'
                THEN CASE
                    WHEN COALESCE(a.TMH_CV008_A,0) > 0 THEN 1
                    ELSE 0
                END

            WHEN r.Fuente_Resolver_TM1_TA = 'PI'
                THEN CASE
                    WHEN COALESCE(a.TMH_CV008_A,0) > 0 THEN 1
                    ELSE 0
                END

            WHEN r.Fuente_Resolver_TM1_TA = 'TUM'
                THEN CASE
                    WHEN r.Valor_Resolver_TM1_TA > 0 THEN 1
                    ELSE 0
                END

            ELSE 0
        END
        AS tinyint
    ) AS Evaluable_TM1_TA_Resuelto,

    CAST
    (
        CASE
            WHEN t.Fecha < '2026-09-01'
                THEN CASE
                    WHEN COALESCE(a.TMH_CV008_B,0) > 0 THEN 1
                    ELSE 0
                END

            WHEN r.Fuente_Resolver_TM1_TB = 'PI'
                THEN CASE
                    WHEN COALESCE(a.TMH_CV008_B,0) > 0 THEN 1
                    ELSE 0
                END

            WHEN r.Fuente_Resolver_TM1_TB = 'TUM'
                THEN CASE
                    WHEN r.Valor_Resolver_TM1_TB > 0 THEN 1
                    ELSE 0
                END

            ELSE 0
        END
        AS tinyint
    ) AS Evaluable_TM1_TB_Resuelto,

    CAST
    (
        CASE
            WHEN t.Fecha < '2026-09-01'
                THEN CASE
                    WHEN COALESCE(a.TMH_CV108_A,0) > 0 THEN 1
                    ELSE 0
                END

            WHEN r.Fuente_Resolver_TM2_TA = 'PI'
                THEN CASE
                    WHEN COALESCE(a.TMH_CV108_A,0) > 0 THEN 1
                    ELSE 0
                END

            WHEN r.Fuente_Resolver_TM2_TA = 'TUM'
                THEN CASE
                    WHEN r.Valor_Resolver_TM2_TA > 0 THEN 1
                    ELSE 0
                END

            ELSE 0
        END
        AS tinyint
    ) AS Evaluable_TM2_TA_Resuelto,

    CAST
    (
        CASE
            WHEN t.Fecha < '2026-09-01'
                THEN CASE
                    WHEN COALESCE(a.TMH_CV108_B,0) > 0 THEN 1
                    ELSE 0
                END

            WHEN r.Fuente_Resolver_TM2_TB = 'PI'
                THEN CASE
                    WHEN COALESCE(a.TMH_CV108_B,0) > 0 THEN 1
                    ELSE 0
                END

            WHEN r.Fuente_Resolver_TM2_TB = 'TUM'
                THEN CASE
                    WHEN r.Valor_Resolver_TM2_TB > 0 THEN 1
                    ELSE 0
                END

            ELSE 0
        END
        AS tinyint
    ) AS Evaluable_TM2_TB_Resuelto,

    /* ============================================================
       TRAZABILIDAD
       ============================================================ */
    r.Motivo_TM1_TA,
    r.Motivo_TM1_TB,
    r.Motivo_TM2_TA,
    r.Motivo_TM2_TB

FROM ton_intervalo AS t

LEFT JOIN inventar_SpcHidr.v_datos_apilado_tmh_v2 AS a
    ON a.Fecha = t.Fecha

LEFT JOIN resolver_t12 AS r
    ON r.fecha_operacional = t.Fecha;
