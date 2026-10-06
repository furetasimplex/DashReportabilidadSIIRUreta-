CREATE VIEW inventar_SpcHidr.v_bd_ton_oficial
AS

WITH ton_t12 AS
(
    SELECT
        Fecha,

        NULLIF(
            MAX(
                CASE
                    WHEN Torre = 'T1' AND Turno = 'A'
                        THEN Ton_Real
                END
            ),
            0
        ) AS [Apilado TMH CV-08 TA],

        NULLIF(
            MAX(
                CASE
                    WHEN Torre = 'T1' AND Turno = 'B'
                        THEN Ton_Real
                END
            ),
            0
        ) AS [Apilado TMH CV-08 TB],

        NULLIF(
            MAX(
                CASE
                    WHEN Torre = 'T2' AND Turno = 'A'
                        THEN Ton_Real
                END
            ),
            0
        ) AS [Apilado TMH CV-108 TA],

        NULLIF(
            MAX(
                CASE
                    WHEN Torre = 'T2' AND Turno = 'B'
                        THEN Ton_Real
                END
            ),
            0
        ) AS [Apilado TMH CV-108 TB]

    FROM inventar_SpcHidr.v_reporte_diario_emulado_excel

    WHERE Torre IN ('T1', 'T2')

    GROUP BY
        Fecha
),

ton_srr AS
(
    SELECT
        Fecha,

        NULLIF(
            MAX(
                CASE
                    WHEN Torre = 'SRR' AND Turno = 'A'
                        THEN Ton_Real
                END
            ),
            0
        ) AS [Apilado TMH CV-01 TA],

        NULLIF(
            MAX(
                CASE
                    WHEN Torre = 'SRR' AND Turno = 'B'
                        THEN Ton_Real
                END
            ),
            0
        ) AS [Apilado TMH CV-01 TB]

    FROM inventar_SpcHidr.v_reporte_diario_emulado_excel

    WHERE Torre = 'SRR'

    GROUP BY
        Fecha
)

SELECT
    t.Fecha,

    /* =========================================================
       Tonelajes Torres 1 y 2
       ========================================================= */

    t.[Apilado TMH CV-08 TA],
    t.[Apilado TMH CV-08 TB],
    t.[Apilado TMH CV-108 TA],
    t.[Apilado TMH CV-108 TB],

    /* =========================================================
       Representatividad Torres 1 y 2
       Se mantiene la lógica histórica sin cambios.
       ========================================================= */

    COALESCE(r.TM1_TurnoA_Quimico, 0)
        AS [Rep. TM1 TA Qui.],

    COALESCE(r.TM1_TurnoA_Fisico, 0)
        AS [Rep. TM1 TA Fis.],

    COALESCE(r.TM1_TurnoB_Quimico, 0)
        AS [Rep. TM1 TB Qui.],

    COALESCE(r.TM1_TurnoB_Fisico, 0)
        AS [Rep. TM1 TB Fis.],

    COALESCE(r.TM2_TurnoA_Quimico, 0)
        AS [Rep. TM2 TA Qui.],

    COALESCE(r.TM2_TurnoA_Fisico, 0)
        AS [Rep. TM2 TA Fis.],

    COALESCE(r.TM2_TurnoB_Quimico, 0)
        AS [Rep. TM2 TB Qui.],

    COALESCE(r.TM2_TurnoB_Fisico, 0)
        AS [Rep. TM2 TB Fis.],

    /* =========================================================
       Flags químicos Torres 1 y 2
       ========================================================= */

    CASE
        WHEN COALESCE(r.TM1_TurnoA_Quimico, 0) >= 0.75
            THEN 1
        ELSE 0
    END AS [Muestra representativa TM1 TA],

    CASE
        WHEN COALESCE(r.TM1_TurnoB_Quimico, 0) >= 0.75
            THEN 1
        ELSE 0
    END AS [Muestra representativa TM1 TB],

    CASE
        WHEN COALESCE(r.TM2_TurnoA_Quimico, 0) >= 0.75
            THEN 1
        ELSE 0
    END AS [Muestra representativa TM2 TA],

    CASE
        WHEN COALESCE(r.TM2_TurnoB_Quimico, 0) >= 0.75
            THEN 1
        ELSE 0
    END AS [Muestra representativa TM2 TB],

    /* =========================================================
       Flags físicos Torres 1 y 2
       ========================================================= */

    CASE
        WHEN COALESCE(r.TM1_TurnoA_Fisico, 0) >= 0.75
            THEN 1
        ELSE 0
    END AS [FISICO TM1 TA],

    CASE
        WHEN COALESCE(r.TM1_TurnoB_Fisico, 0) >= 0.75
            THEN 1
        ELSE 0
    END AS [FISICO TM1 TB],

    CASE
        WHEN COALESCE(r.TM2_TurnoA_Fisico, 0) >= 0.75
            THEN 1
        ELSE 0
    END AS [FISICO TM2 TA],

    CASE
        WHEN COALESCE(r.TM2_TurnoB_Fisico, 0) >= 0.75
            THEN 1
        ELSE 0
    END AS [FISICO TM2 TB],

    /* =========================================================
       Torre 3 / SRR
       ========================================================= */

    s.[Apilado TMH CV-01 TA],
    s.[Apilado TMH CV-01 TB],

    r.SRR_TurnoA_Quimico
        AS [Rep. SRR TA Qui.],

    r.SRR_TurnoA_Fisico
        AS [Rep. SRR TA Fis.],

    r.SRR_TurnoB_Quimico
        AS [Rep. SRR TB Qui.],

    r.SRR_TurnoB_Fisico
        AS [Rep. SRR TB Fis.],

    /* =========================================================
       Flags químicos SRR

       NULL = turno no evaluable o sin flujo SRR.
       0    = evaluable, pero no representativo.
       1    = representatividad >= 0,75.
       ========================================================= */

    CASE
        WHEN r.SRR_TurnoA_Quimico IS NULL
            THEN NULL

        WHEN r.SRR_TurnoA_Quimico >= 0.75
            THEN 1

        ELSE 0
    END AS [Muestra representativa TM3 TA],

    CASE
        WHEN r.SRR_TurnoB_Quimico IS NULL
            THEN NULL

        WHEN r.SRR_TurnoB_Quimico >= 0.75
            THEN 1

        ELSE 0
    END AS [Muestra representativa TM3 TB],

    /* =========================================================
       Flags físicos SRR
       ========================================================= */

    CASE
        WHEN r.SRR_TurnoA_Fisico IS NULL
            THEN NULL

        WHEN r.SRR_TurnoA_Fisico >= 0.75
            THEN 1

        ELSE 0
    END AS [FISICO TM3 TA],

    CASE
        WHEN r.SRR_TurnoB_Fisico IS NULL
            THEN NULL

        WHEN r.SRR_TurnoB_Fisico >= 0.75
            THEN 1

        ELSE 0
    END AS [FISICO TM3 TB]

FROM ton_t12 AS t

LEFT JOIN ton_srr AS s
    ON s.Fecha = t.Fecha

LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado AS r
    ON r.Dia = t.Fecha;
