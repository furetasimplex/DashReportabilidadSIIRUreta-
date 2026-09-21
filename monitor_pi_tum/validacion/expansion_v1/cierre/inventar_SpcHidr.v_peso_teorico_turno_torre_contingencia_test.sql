CREATE VIEW inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test
AS

WITH base AS
(
    SELECT
        pt.Fecha,
        pt.Turno,
        pt.Torre,

        pt.Horas_Reales,
        pt.Factor_Masa AS Factor_Masa_PI,

        pt.ts_ini,
        pt.ts_fin,

        pt.PesoBase_Quimico_12h,
        pt.PesoBase_Fisico_12h,

        pt.Fraccion_Muestreo AS Fraccion_Muestreo_PI,

        pt.PesoTeo_Quimico AS PesoTeo_Quimico_Actual,
        pt.PesoTeo_Fisico  AS PesoTeo_Fisico_Actual,

        Equipo =
            CASE pt.Torre
                WHEN 'T1' THEN 'PRINCIPAL_CV008'
                WHEN 'T2' THEN 'PRINCIPAL_CV108'
                ELSE NULL
            END

    FROM inventar_SpcHidr.v_peso_teorico_turno_torre_excel AS pt
),

resuelto AS
(
    SELECT
        b.*,

        r.fuente_resuelta,
        r.valor_final_resuelto,
        r.tipo_tum,
        r.motivo_decision,

        Turno_TUM_Ini =
            CASE
                WHEN b.Turno = 'A'
                    THEN DATEADD(
                            HOUR,
                            8,
                            CAST(b.Fecha AS datetime2)
                         )

                WHEN b.Turno = 'B'
                    THEN DATEADD(
                            HOUR,
                            20,
                            CAST(b.Fecha AS datetime2)
                         )
            END,

        Turno_TUM_Fin =
            CASE
                WHEN b.Turno = 'A'
                    THEN DATEADD(
                            HOUR,
                            20,
                            CAST(b.Fecha AS datetime2)
                         )

                WHEN b.Turno = 'B'
                    THEN DATEADD(
                            HOUR,
                            8,
                            DATEADD(
                                DAY,
                                1,
                                CAST(b.Fecha AS datetime2)
                            )
                         )
            END

    FROM base AS b

    LEFT JOIN (
    SELECT fecha_operacional,turno,equipo_codigo,fuente_resuelta,
           valor_final_resuelto,tipo_tum,motivo_decision
    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno WHERE fecha_operacional < '2026-09-01'
    UNION ALL
    SELECT fecha_operacional,turno,equipo_codigo,fuente_resuelta,
           valor_final_resuelto,tipo_tum,motivo_decision
    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test WHERE fecha_operacional >= '2026-09-01'
) AS r
        ON r.fecha_operacional = b.Fecha
       AND r.turno = b.Turno
       AND r.equipo_codigo = b.Equipo
),

ventanas AS
(
    SELECT
        r.*,

        Overlap_Ini =
            CASE
                WHEN r.ts_ini > r.Turno_TUM_Ini
                    THEN r.ts_ini
                ELSE r.Turno_TUM_Ini
            END,

        Overlap_Fin =
            CASE
                WHEN r.ts_fin < r.Turno_TUM_Fin
                    THEN r.ts_fin
                ELSE r.Turno_TUM_Fin
            END

    FROM resuelto AS r
),

calculo AS
(
    SELECT
        v.*,

        Minutos_Overlap =
            CASE
                WHEN v.Overlap_Fin > v.Overlap_Ini
                    THEN DATEDIFF(
                            MINUTE,
                            v.Overlap_Ini,
                            v.Overlap_Fin
                         )
                ELSE 0
            END,

        Fraccion_Overlap_TUM =
            CASE
                WHEN v.Overlap_Fin > v.Overlap_Ini
                    THEN
                        DATEDIFF(
                            MINUTE,
                            v.Overlap_Ini,
                            v.Overlap_Fin
                        ) / 720.0
                ELSE NULL
            END,

        Factor_Masa_TUM =
            CASE
                WHEN v.valor_final_resuelto IS NULL
                    THEN NULL

                WHEN v.valor_final_resuelto < 0
                    THEN NULL

                WHEN v.valor_final_resuelto >= 22500.0
                    THEN 1.0

                ELSE
                    v.valor_final_resuelto / 22500.0
            END

    FROM ventanas AS v
)

SELECT
    Fecha,
    Turno,
    Torre,

    Horas_Reales,

    Factor_Masa_PI,

    ts_ini,
    ts_fin,

    PesoBase_Quimico_12h,
    PesoBase_Fisico_12h,

    Fraccion_Muestreo_PI,

    PesoTeo_Quimico_Actual,
    PesoTeo_Fisico_Actual,

    Fuente_Calculo =
        CASE
            /* Histórico previo al inicio de contingencia */
            WHEN Fecha < '2026-09-01'
                THEN 'PI_INTERVALO_HISTORICO'

            /* SRR mantiene su metodología propia */
            WHEN Torre = 'SRR'
                THEN 'PI_INTERVALO_SRR'

            WHEN fuente_resuelta = 'PI'
                THEN 'PI_INTERVALO'

            WHEN fuente_resuelta = 'TUM'
                THEN 'TUM_TURNO'

            ELSE 'SIN_RESOLVER'
        END,

    Fuente_Resolver = fuente_resuelta,

    tipo_tum,
    motivo_decision,

    Ton_TUM_Turno = valor_final_resuelto,

    Turno_TUM_Ini,
    Turno_TUM_Fin,

    Overlap_Ini,
    Overlap_Fin,
    Minutos_Overlap,
    Fraccion_Overlap_TUM,

    Factor_Masa_TUM,

    Factor_Masa_Calculo =
        CASE
            WHEN Fecha < '2026-09-01'
                THEN Factor_Masa_PI

            WHEN Torre = 'SRR'
                THEN Factor_Masa_PI

            WHEN fuente_resuelta = 'PI'
                THEN Factor_Masa_PI

            WHEN fuente_resuelta = 'TUM'
                THEN Factor_Masa_TUM

            ELSE NULL
        END,

    Fraccion_Calculo =
        CASE
            WHEN Fecha < '2026-09-01'
                THEN Fraccion_Muestreo_PI

            WHEN Torre = 'SRR'
                THEN Fraccion_Muestreo_PI

            WHEN fuente_resuelta = 'PI'
                THEN Fraccion_Muestreo_PI

            WHEN fuente_resuelta = 'TUM'
                THEN Fraccion_Overlap_TUM

            ELSE NULL
        END,

    PesoTeo_Quimico_Candidato =
        CASE
            WHEN Fecha < '2026-09-01'
                THEN PesoTeo_Quimico_Actual

            WHEN Torre = 'SRR'
                THEN PesoTeo_Quimico_Actual

            WHEN fuente_resuelta = 'PI'
                THEN PesoTeo_Quimico_Actual

            WHEN fuente_resuelta = 'TUM'
             AND Minutos_Overlap > 0
             AND Factor_Masa_TUM IS NOT NULL
                THEN
                    PesoBase_Quimico_12h
                    * Factor_Masa_TUM
                    * Fraccion_Overlap_TUM

            ELSE NULL
        END,

    PesoTeo_Fisico_Candidato =
        CASE
            WHEN Fecha < '2026-09-01'
                THEN PesoTeo_Fisico_Actual

            WHEN Torre = 'SRR'
                THEN PesoTeo_Fisico_Actual

            WHEN fuente_resuelta = 'PI'
                THEN PesoTeo_Fisico_Actual

            WHEN fuente_resuelta = 'TUM'
             AND Minutos_Overlap > 0
             AND Factor_Masa_TUM IS NOT NULL
                THEN
                    PesoBase_Fisico_12h
                    * Factor_Masa_TUM
                    * Fraccion_Overlap_TUM

            ELSE NULL
        END

FROM calculo;