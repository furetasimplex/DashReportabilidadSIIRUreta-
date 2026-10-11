
CREATE   VIEW inventar_SpcHidr.v_apilado_proporcion_final_reporte_test AS

WITH tms_turno AS (
    SELECT
        Fecha,
        'A' AS Turno,
        TMS_Total_Sin_Sal_Con_SRR_A AS Apilado_TMS_Con_SRR
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        TMS_Total_Sin_Sal_Con_SRR_B AS Apilado_TMS_Con_SRR
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test
),

base AS (
    SELECT
        t.Fecha,
        t.Turno,

        p.Ton_Stock_Camiones,
        p.Ton_Mina_Camiones,
        p.Ton_Stock_Mina_Camiones,

        p.Prop_Stock_Camiones,
        p.Prop_Mina_Camiones,

        p.Ton_SRR AS TMS_SRR,

        t.Apilado_TMS_Con_SRR,

        t.Apilado_TMS_Con_SRR - COALESCE(p.Ton_SRR, 0) AS Apilado_Menos_SRR

    FROM tms_turno t
    LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr p
        ON p.Fecha = t.Fecha
       AND p.Turno = t.Turno
)

SELECT
    Fecha,
    Turno,

    Ton_Stock_Camiones,
    Ton_Mina_Camiones,
    Ton_Stock_Mina_Camiones,

    Prop_Stock_Camiones,
    Prop_Mina_Camiones,

    TMS_SRR,
    Apilado_TMS_Con_SRR,
    Apilado_Menos_SRR,

    Apilado_Menos_SRR * Prop_Stock_Camiones AS TMS_Stock,
    Apilado_Menos_SRR * Prop_Mina_Camiones AS TMS_Mina,

    CASE
        WHEN Apilado_TMS_Con_SRR = 0 THEN NULL
        ELSE (Apilado_Menos_SRR * Prop_Stock_Camiones)
             / NULLIF(Apilado_TMS_Con_SRR, 0)
    END AS Prop_Final_Stock,

    CASE
        WHEN Apilado_TMS_Con_SRR = 0 THEN NULL
        ELSE (Apilado_Menos_SRR * Prop_Mina_Camiones)
             / NULLIF(Apilado_TMS_Con_SRR, 0)
    END AS Prop_Final_Mina,

    CASE
        WHEN Apilado_TMS_Con_SRR = 0 THEN NULL
        ELSE TMS_SRR / NULLIF(Apilado_TMS_Con_SRR, 0)
    END AS Prop_Final_SRR,

    CASE
        WHEN Apilado_TMS_Con_SRR = 0 THEN NULL
        ELSE (
            (Apilado_Menos_SRR * Prop_Stock_Camiones)
            + (Apilado_Menos_SRR * Prop_Mina_Camiones)
            + TMS_SRR
        ) / NULLIF(Apilado_TMS_Con_SRR, 0)
    END AS Prop_Final_Total,

    COALESCE(Apilado_Menos_SRR * Prop_Stock_Camiones, 0)
    + COALESCE(Apilado_Menos_SRR * Prop_Mina_Camiones, 0)
    + COALESCE(TMS_SRR, 0)
    - COALESCE(Apilado_TMS_Con_SRR, 0) AS Check_Distribucion_Apilado

FROM base;