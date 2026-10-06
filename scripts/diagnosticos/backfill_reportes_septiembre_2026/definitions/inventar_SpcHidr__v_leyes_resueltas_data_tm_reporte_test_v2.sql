CREATE   VIEW [inventar_SpcHidr].[v_leyes_resueltas_data_tm_reporte_test_v2] AS

WITH base AS (
    SELECT *
    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
),

/* ============================================================
   Candidatos diarios de Malla -1/2 ya validados físicamente
   desde la vista base.

   Nota:
   - La vista base debe entregar TORRE_* solo cuando la medición
     de Informe Torre cumple representatividad física >= 0,75.
   - Si existe A y B válidos para una misma TM/fecha, se prioriza
     TORRE_MISMO_TURNO y luego turno B por ser posterior.
   ============================================================ */
malla12_candidata_dia_tm AS (
    SELECT
        Fecha,
        TM,
        TM AS TM_Origen,
        Turno AS Turno_Fuente,
        Malla_Menos_1_2,
        Fuente_Malla_Menos_1_2 AS Fuente_Origen
    FROM (
        SELECT
            b.*,
            ROW_NUMBER() OVER (
                PARTITION BY b.Fecha, b.TM
                ORDER BY
                    CASE
                        WHEN b.Fuente_Malla_Menos_1_2 = 'TORRE_MISMO_TURNO' THEN 3
                        WHEN b.Fuente_Malla_Menos_1_2 = 'TORRE_OTRO_TURNO_MISMO_DIA' THEN 2
                        WHEN b.Fuente_Malla_Menos_1_2 = 'SEMILLA_INICIO_PERIODO' THEN 1
                        ELSE 0
                    END DESC,
                    CASE WHEN b.Turno = 'B' THEN 2 ELSE 1 END DESC
            ) AS rn
        FROM base b
        WHERE b.Malla_Menos_1_2 IS NOT NULL
          AND b.Malla_Menos_1_2 <> 0
          AND b.Fuente_Malla_Menos_1_2 <> 'NO_APLICA_MINA'
    ) x
    WHERE rn = 1
),

fechas AS (
    SELECT DISTINCT Fecha
    FROM base
),

/* ============================================================
   Regla compartible RN-027:
   - Si TM1 y TM2 tienen valor válido en la fecha, cada TM usa el suyo.
   - Si solo una TM tiene valor válido, se comparte hacia ambas TM.
   ============================================================ */
malla12_dia_resuelta AS (
    SELECT
        f.Fecha,
        'TM1' AS TM,
        COALESCE(tm1.Malla_Menos_1_2, tm2.Malla_Menos_1_2) AS Malla_Menos_1_2,
        CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN 'TM1'
             WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN 'TM2'
        END AS TM_Origen,
        CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Turno_Fuente
             WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Turno_Fuente
        END AS Turno_Fuente,
        CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Fuente_Origen
             WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Fuente_Origen
        END AS Fuente_Origen
    FROM fechas f
    LEFT JOIN malla12_candidata_dia_tm tm1
        ON tm1.Fecha = f.Fecha
       AND tm1.TM = 'TM1'
    LEFT JOIN malla12_candidata_dia_tm tm2
        ON tm2.Fecha = f.Fecha
       AND tm2.TM = 'TM2'

    UNION ALL

    SELECT
        f.Fecha,
        'TM2' AS TM,
        COALESCE(tm2.Malla_Menos_1_2, tm1.Malla_Menos_1_2) AS Malla_Menos_1_2,
        CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN 'TM2'
             WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN 'TM1'
        END AS TM_Origen,
        CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Turno_Fuente
             WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Turno_Fuente
        END AS Turno_Fuente,
        CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Fuente_Origen
             WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Fuente_Origen
        END AS Fuente_Origen
    FROM fechas f
    LEFT JOIN malla12_candidata_dia_tm tm1
        ON tm1.Fecha = f.Fecha
       AND tm1.TM = 'TM1'
    LEFT JOIN malla12_candidata_dia_tm tm2
        ON tm2.Fecha = f.Fecha
       AND tm2.TM = 'TM2'
),

ajustada AS (
    SELECT
        b.*,

        CASE
            WHEN b.FeS IS NOT NULL
             AND b.FeS <> 0
             AND b.Fuente_FeS <> 'NO_APLICA_MINA'
            THEN b.FeS
            ELSE ult_fes.FeS
        END AS FeS_Ajustado,

        CASE
            WHEN b.FeS IS NOT NULL
             AND b.FeS <> 0
             AND b.Fuente_FeS <> 'NO_APLICA_MINA'
            THEN b.Fuente_FeS
            WHEN ult_fes.FeS IS NOT NULL
            THEN 'ARRASTRE_ULTIMO_VALIDO'
            ELSE b.Fuente_FeS
        END AS Fuente_FeS_Ajustada,

        CASE
            WHEN b.ConsH IS NOT NULL
             AND b.ConsH <> 0
             AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
            THEN b.ConsH
            ELSE ult_consh.ConsH
        END AS ConsH_Ajustado,

        CASE
            WHEN b.ConsH IS NOT NULL
             AND b.ConsH <> 0
             AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
            THEN b.Fuente_ConsH
            WHEN ult_consh.ConsH IS NOT NULL
            THEN 'ARRASTRE_ULTIMO_VALIDO'
            ELSE b.Fuente_ConsH
        END AS Fuente_ConsH_Ajustada,

        ult_malla.Malla_Menos_1_2 AS Malla_Menos_1_2_Ajustado,

        CASE
            WHEN ult_malla.Malla_Menos_1_2 IS NULL
                THEN b.Fuente_Malla_Menos_1_2

            WHEN ult_malla.Fecha = b.Fecha
             AND ult_malla.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
                THEN 'SEMILLA_INICIO_PERIODO'

            WHEN ult_malla.Fecha = b.Fecha
             AND ult_malla.TM_Origen = b.TM
                THEN 'TORRE_REP_FISICA'

            WHEN ult_malla.Fecha = b.Fecha
             AND ult_malla.TM_Origen <> b.TM
                THEN 'TORRE_REP_FISICA_COMPARTIDA'

            WHEN ult_malla.Fecha < b.Fecha
                THEN 'ARRASTRE_ULTIMO_VALIDO'

            ELSE b.Fuente_Malla_Menos_1_2
        END AS Fuente_Malla_Menos_1_2_Ajustada

    FROM base b

    OUTER APPLY (
        SELECT TOP 1
            x.FeS
        FROM base x
        WHERE x.TM = b.TM
          AND x.Fecha <= b.Fecha
          AND x.FeS IS NOT NULL
          AND x.FeS <> 0
          AND x.Fuente_FeS <> 'NO_APLICA_MINA'
        ORDER BY
            x.Fecha DESC,
            CASE WHEN x.Turno = b.Turno THEN 0 ELSE 1 END
    ) ult_fes

    OUTER APPLY (
        SELECT TOP 1
            x.ConsH
        FROM base x
        WHERE x.TM = b.TM
          AND x.Fecha <= b.Fecha
          AND x.ConsH IS NOT NULL
          AND x.ConsH <> 0
          AND x.Fuente_ConsH <> 'NO_APLICA_MINA'
        ORDER BY
            x.Fecha DESC,
            CASE WHEN x.Turno = b.Turno THEN 0 ELSE 1 END
    ) ult_consh

    OUTER APPLY (
        SELECT TOP 1
            d.Fecha,
            d.TM_Origen,
            d.Turno_Fuente,
            d.Malla_Menos_1_2,
            d.Fuente_Origen
        FROM malla12_dia_resuelta d
        WHERE d.TM = b.TM
          AND d.Fecha <= b.Fecha
          AND d.Malla_Menos_1_2 IS NOT NULL
        ORDER BY d.Fecha DESC
    ) ult_malla
)

SELECT
    Fecha,
    Turno,
    TM,
    CuT,
    Fuente_CuT,
    CuS,
    Fuente_CuS,
    CO3,
    Fuente_CO3,
    CuFe,
    Fuente_CuFe,
    FeT,
    Fuente_FeT,
    FeS_Ajustado AS FeS,
    Fuente_FeS_Ajustada AS Fuente_FeS,
    ConsH_Ajustado AS ConsH,
    Fuente_ConsH_Ajustada AS Fuente_ConsH,
    Malla_Menos_1_2_Ajustado AS Malla_Menos_1_2,
    Fuente_Malla_Menos_1_2_Ajustada AS Fuente_Malla_Menos_1_2,
    Malla_Menos_100,
    Fuente_Malla_Menos_100,
    CaolBeta,
    Fuente_CaolBeta
FROM ajustada;
