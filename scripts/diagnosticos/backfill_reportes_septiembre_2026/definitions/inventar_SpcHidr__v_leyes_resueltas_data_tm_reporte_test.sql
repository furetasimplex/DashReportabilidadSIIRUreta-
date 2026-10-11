CREATE   VIEW inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS

WITH base AS (
    SELECT
        Fecha,
        Turno,
        CASE 
            WHEN Turno = 'A' THEN 'B'
            WHEN Turno = 'B' THEN 'A'
        END AS Otro_Turno,
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

        FeS,
        Fuente_FeS,

        ConsH,
        Fuente_ConsH,

        Malla_Menos_1_2,
        Fuente_Malla_Menos_1_2,

        Malla_Menos_100,
        Fuente_Malla_Menos_100,

        CaolBeta,
        Fuente_CaolBeta

    FROM inventar_SpcHidr.v_leyes_validadas_tm_turno
),

unpivot_especial AS (
    SELECT
        Fecha,
        Turno,
        Otro_Turno,
        TM,
        Analito,
        Valor_Base,
        Fuente_Base
    FROM base
    CROSS APPLY (
        VALUES
            ('FeS', FeS, Fuente_FeS),
            ('ConsH', ConsH, Fuente_ConsH),
            ('Malla_Menos_1_2', Malla_Menos_1_2, Fuente_Malla_Menos_1_2)
    ) v(Analito, Valor_Base, Fuente_Base)
),

otro_turno AS (
    SELECT
        Fecha,
        Turno,
        TM,
        Analito,
        Valor_Base AS Valor_Otro_Turno,
        Fuente_Base AS Fuente_Otro_Turno
    FROM unpivot_especial
),

semillas AS (
    SELECT
        fecha AS Fecha,
        turno AS Turno,
        tm AS TM,
        analito AS Analito,
        valor AS Valor_Semilla,
        fuente_semilla AS Fuente_Semilla
    FROM inventar_SpcHidr.analitos_semilla_reporte_turno
),

resueltos AS (
    SELECT
        b.Fecha,
        b.Turno,
        b.TM,
        b.Analito,

        CASE
            WHEN s.Valor_Semilla IS NOT NULL
                THEN s.Valor_Semilla

            WHEN b.Fuente_Base = 'TORRE'
                THEN b.Valor_Base

            WHEN ot.Fuente_Otro_Turno = 'TORRE'
                THEN ot.Valor_Otro_Turno

            ELSE b.Valor_Base
        END AS Valor_Resuelto,

        CASE
            WHEN s.Valor_Semilla IS NOT NULL
                THEN 'SEMILLA_INICIO_PERIODO'

            WHEN b.Fuente_Base = 'TORRE'
                THEN 'TORRE_MISMO_TURNO'

            WHEN ot.Fuente_Otro_Turno = 'TORRE'
                THEN 'TORRE_OTRO_TURNO_MISMO_DIA'

            ELSE b.Fuente_Base
        END AS Fuente_Resuelta

    FROM unpivot_especial b
    LEFT JOIN otro_turno ot
        ON ot.Fecha = b.Fecha
       AND ot.Turno = b.Otro_Turno
       AND ot.TM = b.TM
       AND ot.Analito = b.Analito
    LEFT JOIN semillas s
        ON s.Fecha = b.Fecha
       AND s.Turno = b.Turno
       AND s.TM = b.TM
       AND s.Analito = b.Analito
),

resueltos_pivot AS (
    SELECT
        Fecha,
        Turno,
        TM,

        MAX(CASE WHEN Analito = 'FeS' THEN Valor_Resuelto END) AS FeS_Resuelto,
        MAX(CASE WHEN Analito = 'FeS' THEN Fuente_Resuelta END) AS Fuente_FeS_Resuelto,

        MAX(CASE WHEN Analito = 'ConsH' THEN Valor_Resuelto END) AS ConsH_Resuelto,
        MAX(CASE WHEN Analito = 'ConsH' THEN Fuente_Resuelta END) AS Fuente_ConsH_Resuelto,

        MAX(CASE WHEN Analito = 'Malla_Menos_1_2' THEN Valor_Resuelto END) AS Malla_Menos_1_2_Resuelto,
        MAX(CASE WHEN Analito = 'Malla_Menos_1_2' THEN Fuente_Resuelta END) AS Fuente_Malla_Menos_1_2_Resuelto

    FROM resueltos
    GROUP BY
        Fecha,
        Turno,
        TM
)

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    b.CuT,
    b.Fuente_CuT,

    b.CuS,
    b.Fuente_CuS,

    b.CO3,
    b.Fuente_CO3,

    b.CuFe,
    b.Fuente_CuFe,

    b.FeT,
    b.Fuente_FeT,

    r.FeS_Resuelto AS FeS,
    r.Fuente_FeS_Resuelto AS Fuente_FeS,

    r.ConsH_Resuelto AS ConsH,
    r.Fuente_ConsH_Resuelto AS Fuente_ConsH,

    r.Malla_Menos_1_2_Resuelto AS Malla_Menos_1_2,
    r.Fuente_Malla_Menos_1_2_Resuelto AS Fuente_Malla_Menos_1_2,

    b.Malla_Menos_100,
    b.Fuente_Malla_Menos_100,

    b.CaolBeta,
    b.Fuente_CaolBeta

FROM base b
LEFT JOIN resueltos_pivot r
    ON r.Fecha = b.Fecha
   AND r.Turno = b.Turno
   AND r.TM = b.TM;