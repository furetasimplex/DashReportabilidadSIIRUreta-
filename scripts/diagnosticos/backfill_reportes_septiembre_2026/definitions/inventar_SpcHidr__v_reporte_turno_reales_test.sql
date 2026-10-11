    CREATE   VIEW inventar_SpcHidr.v_reporte_turno_reales_test AS

WITH tms_tm AS (
    SELECT
        Fecha,
        'A' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Sin_Sal_Con_SRR_A AS TMS
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test

    UNION ALL

    SELECT
        Fecha,
        'A' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Sin_Sal_Con_SRR_A AS TMS
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Sin_Sal_Con_SRR_B AS TMS
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Sin_Sal_Con_SRR_B AS TMS
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test
),

base AS (
    SELECT
        t.Fecha,
        t.Turno,
        t.TM,
        t.TMS,

        l.CuT,
        l.CuS,
        l.CO3,
        l.CuFe,
        l.FeT,
        l.FeS,
        l.ConsH,
        l.Malla_Menos_1_2,
        l.Malla_Menos_100,
        l.CaolBeta

    FROM tms_tm t

    LEFT JOIN inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test_v2 l
        ON l.Fecha = t.Fecha
       AND l.Turno = t.Turno
       AND l.TM = t.TM
),

ponderado AS (
    SELECT
        Fecha,
        Turno,

        SUM(TMS) AS Apilado_TMS_Real,

        SUM(TMS * CuT) / NULLIF(SUM(CASE WHEN CuT IS NOT NULL THEN TMS ELSE 0 END), 0) AS CuT_Real,
        SUM(TMS * CuS) / NULLIF(SUM(CASE WHEN CuS IS NOT NULL THEN TMS ELSE 0 END), 0) AS CuS_Real,
        SUM(TMS * CO3) / NULLIF(SUM(CASE WHEN CO3 IS NOT NULL THEN TMS ELSE 0 END), 0) AS CO3_Real,
        SUM(TMS * CuFe) / NULLIF(SUM(CASE WHEN CuFe IS NOT NULL THEN TMS ELSE 0 END), 0) AS CuFe_Real,
        SUM(TMS * FeT) / NULLIF(SUM(CASE WHEN FeT IS NOT NULL THEN TMS ELSE 0 END), 0) AS FeT_Real,
        SUM(TMS * FeS) / NULLIF(SUM(CASE WHEN FeS IS NOT NULL THEN TMS ELSE 0 END), 0) AS FeS_Real,
        SUM(TMS * ConsH) / NULLIF(SUM(CASE WHEN ConsH IS NOT NULL THEN TMS ELSE 0 END), 0) AS ConsH_Real,
        SUM(TMS * Malla_Menos_1_2) / NULLIF(SUM(CASE WHEN Malla_Menos_1_2 IS NOT NULL THEN TMS ELSE 0 END), 0) AS Malla_Menos_1_2_Real,
        SUM(TMS * Malla_Menos_100) / NULLIF(SUM(CASE WHEN Malla_Menos_100 IS NOT NULL THEN TMS ELSE 0 END), 0) AS Malla_Menos_100_Real,
        SUM(TMS * CaolBeta) / NULLIF(SUM(CASE WHEN CaolBeta IS NOT NULL THEN TMS ELSE 0 END), 0) AS CaolBeta_Real

    FROM base
    GROUP BY
        Fecha,
        Turno
)

SELECT
    Fecha,
    Turno,
    Apilado_TMS_Real,

    CuT_Real,
    CuS_Real,

    CASE
        WHEN CuT_Real IS NULL OR CuT_Real = 0 THEN NULL
        ELSE CuS_Real / CuT_Real
    END AS Solubilidad_Real,

    CO3_Real,
    CuFe_Real,
    FeT_Real,
    FeS_Real,
    ConsH_Real,
    Malla_Menos_1_2_Real,
    Malla_Menos_100_Real,
    CaolBeta_Real

FROM ponderado;