
CREATE   VIEW inventar_SpcHidr.v_representatividad_diaria_calculada_contingencia_test
AS

WITH representatividad_t12 AS
(
    SELECT
        pt.Fecha AS Dia,

        /* =========================================================
           TM1 - TURNO A - QUIMICO
        ========================================================= */
        MAX(
            CASE
                WHEN pt.Torre = 'T1'
                 AND pt.Turno = 'A'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Quimico_Candidato IS NULL
                          OR pt.PesoTeo_Quimico_Candidato <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico IS NULL
                          OR pr.PesoReal_Quimico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico_Candidato >= 1
                            THEN 1.0

                        ELSE
                            pr.PesoReal_Quimico
                            / pt.PesoTeo_Quimico_Candidato
                    END
            END
        ) AS TM1_TurnoA_Quimico,

        /* TM1 - TURNO A - FISICO */
        MAX(
            CASE
                WHEN pt.Torre = 'T1'
                 AND pt.Turno = 'A'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Fisico_Candidato IS NULL
                          OR pt.PesoTeo_Fisico_Candidato <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico IS NULL
                          OR pr.PesoReal_Fisico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico_Candidato >= 1
                            THEN 1.0

                        ELSE
                            pr.PesoReal_Fisico
                            / pt.PesoTeo_Fisico_Candidato
                    END
            END
        ) AS TM1_TurnoA_Fisico,

        /* =========================================================
           TM1 - TURNO B
        ========================================================= */
        MAX(
            CASE
                WHEN pt.Torre = 'T1'
                 AND pt.Turno = 'B'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Quimico_Candidato IS NULL
                          OR pt.PesoTeo_Quimico_Candidato <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico IS NULL
                          OR pr.PesoReal_Quimico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico_Candidato >= 1
                            THEN 1.0

                        ELSE
                            pr.PesoReal_Quimico
                            / pt.PesoTeo_Quimico_Candidato
                    END
            END
        ) AS TM1_TurnoB_Quimico,

        MAX(
            CASE
                WHEN pt.Torre = 'T1'
                 AND pt.Turno = 'B'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Fisico_Candidato IS NULL
                          OR pt.PesoTeo_Fisico_Candidato <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico IS NULL
                          OR pr.PesoReal_Fisico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico_Candidato >= 1
                            THEN 1.0

                        ELSE
                            pr.PesoReal_Fisico
                            / pt.PesoTeo_Fisico_Candidato
                    END
            END
        ) AS TM1_TurnoB_Fisico,

        /* =========================================================
           TM2 - TURNO A
        ========================================================= */
        MAX(
            CASE
                WHEN pt.Torre = 'T2'
                 AND pt.Turno = 'A'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Quimico_Candidato IS NULL
                          OR pt.PesoTeo_Quimico_Candidato <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico IS NULL
                          OR pr.PesoReal_Quimico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico_Candidato >= 1
                            THEN 1.0

                        ELSE
                            pr.PesoReal_Quimico
                            / pt.PesoTeo_Quimico_Candidato
                    END
            END
        ) AS TM2_TurnoA_Quimico,

        MAX(
            CASE
                WHEN pt.Torre = 'T2'
                 AND pt.Turno = 'A'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Fisico_Candidato IS NULL
                          OR pt.PesoTeo_Fisico_Candidato <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico IS NULL
                          OR pr.PesoReal_Fisico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico_Candidato >= 1
                            THEN 1.0

                        ELSE
                            pr.PesoReal_Fisico
                            / pt.PesoTeo_Fisico_Candidato
                    END
            END
        ) AS TM2_TurnoA_Fisico,

        /* =========================================================
           TM2 - TURNO B
        ========================================================= */
        MAX(
            CASE
                WHEN pt.Torre = 'T2'
                 AND pt.Turno = 'B'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Quimico_Candidato IS NULL
                          OR pt.PesoTeo_Quimico_Candidato <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico IS NULL
                          OR pr.PesoReal_Quimico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico_Candidato >= 1
                            THEN 1.0

                        ELSE
                            pr.PesoReal_Quimico
                            / pt.PesoTeo_Quimico_Candidato
                    END
            END
        ) AS TM2_TurnoB_Quimico,

        MAX(
            CASE
                WHEN pt.Torre = 'T2'
                 AND pt.Turno = 'B'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Fisico_Candidato IS NULL
                          OR pt.PesoTeo_Fisico_Candidato <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico IS NULL
                          OR pr.PesoReal_Fisico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico_Candidato >= 1
                            THEN 1.0

                        ELSE
                            pr.PesoReal_Fisico
                            / pt.PesoTeo_Fisico_Candidato
                    END
            END
        ) AS TM2_TurnoB_Fisico

    FROM inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test AS pt

    LEFT JOIN inventar_SpcHidr.v_peso_real_torre_turno_excel AS pr
        ON pr.Torre = pt.Torre
       AND pr.Fecha = pt.Fecha
       AND pr.Turno = pt.Turno

    WHERE pt.Torre IN ('T1', 'T2')

    GROUP BY
        pt.Fecha
),

representatividad_srr AS
(
    /*
        SRR queda EXACTAMENTE con su metodología vigente.
        No forma parte del cambio T1/T2.
    */
    SELECT
        Fecha AS Dia,

        CAST(
            MAX(
                CASE
                    WHEN Turno = 'A'
                        THEN Representatividad_Quimica
                END
            ) AS float
        ) AS SRR_TurnoA_Quimico,

        CAST(
            MAX(
                CASE
                    WHEN Turno = 'A'
                        THEN Representatividad_Fisica
                END
            ) AS float
        ) AS SRR_TurnoA_Fisico,

        CAST(
            MAX(
                CASE
                    WHEN Turno = 'B'
                        THEN Representatividad_Quimica
                END
            ) AS float
        ) AS SRR_TurnoB_Quimico,

        CAST(
            MAX(
                CASE
                    WHEN Turno = 'B'
                        THEN Representatividad_Fisica
                END
            ) AS float
        ) AS SRR_TurnoB_Fisico

    FROM inventar_SpcHidr.v_representatividad_srr_turno_calculada

    GROUP BY
        Fecha
)

SELECT
    t12.Dia,

    t12.TM1_TurnoA_Quimico,
    t12.TM1_TurnoA_Fisico,
    t12.TM1_TurnoB_Quimico,
    t12.TM1_TurnoB_Fisico,

    t12.TM2_TurnoA_Quimico,
    t12.TM2_TurnoA_Fisico,
    t12.TM2_TurnoB_Quimico,
    t12.TM2_TurnoB_Fisico,

    srr.SRR_TurnoA_Quimico,
    srr.SRR_TurnoA_Fisico,
    srr.SRR_TurnoB_Quimico,
    srr.SRR_TurnoB_Fisico

FROM representatividad_t12 AS t12

LEFT JOIN representatividad_srr AS srr
    ON srr.Dia = t12.Dia;

