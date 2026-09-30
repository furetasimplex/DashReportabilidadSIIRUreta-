CREATE   VIEW inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_leyes_tm AS

WITH base_tms AS (
    SELECT
        Fecha,
        'A' AS Turno,
        'TM1' AS TM,

        Flag_Apilado_Valido,
        Flag_TMS_Valido,
        Observacion_TMS,
        Factor_Ajuste_Camiones_Usado,

        TMH_TM1_Con_Sal_SRR_A AS TMH_Con_Sal_SRR,
        TMS_TM1_Con_Sal_SRR_A AS TMS_Con_Sal_SRR,
        TMS_TM1_Sin_Sal_Con_SRR_A AS TMS_Sin_Sal_Con_SRR

    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM1' AS TM,

        Flag_Apilado_Valido,
        Flag_TMS_Valido,
        Observacion_TMS,
        Factor_Ajuste_Camiones_Usado,

        TMH_TM1_Con_Sal_SRR_B AS TMH_Con_Sal_SRR,
        TMS_TM1_Con_Sal_SRR_B AS TMS_Con_Sal_SRR,
        TMS_TM1_Sin_Sal_Con_SRR_B AS TMS_Sin_Sal_Con_SRR

    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr

    UNION ALL

    SELECT
        Fecha,
        'A' AS Turno,
        'TM2' AS TM,

        Flag_Apilado_Valido,
        Flag_TMS_Valido,
        Observacion_TMS,
        Factor_Ajuste_Camiones_Usado,

        TMH_TM2_Con_Sal_SRR_A AS TMH_Con_Sal_SRR,
        TMS_TM2_Con_Sal_SRR_A AS TMS_Con_Sal_SRR,
        TMS_TM2_Sin_Sal_Con_SRR_A AS TMS_Sin_Sal_Con_SRR

    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM2' AS TM,

        Flag_Apilado_Valido,
        Flag_TMS_Valido,
        Observacion_TMS,
        Factor_Ajuste_Camiones_Usado,

        TMH_TM2_Con_Sal_SRR_B AS TMH_Con_Sal_SRR,
        TMS_TM2_Con_Sal_SRR_B AS TMS_Con_Sal_SRR,
        TMS_TM2_Sin_Sal_Con_SRR_B AS TMS_Sin_Sal_Con_SRR

    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr
)

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    b.Flag_Apilado_Valido,
    b.Flag_TMS_Valido,
    b.Observacion_TMS,
    b.Factor_Ajuste_Camiones_Usado,

    b.TMH_Con_Sal_SRR,
    b.TMS_Con_Sal_SRR,
    b.TMS_Sin_Sal_Con_SRR,

    l.Representatividad_TM,

    l.CuT,
    l.Fuente_CuT,

    l.CuS,
    l.Fuente_CuS,

    l.FeT,
    l.Fuente_FeT,

    l.FeS,
    l.Fuente_FeS,

    l.CO3,
    l.Fuente_CO3,

    l.ConsH,
    l.Fuente_ConsH,

    l.Malla_Menos_1_2,
    l.Fuente_Malla_Menos_1_2,

    l.Malla_Menos_100,
    l.Fuente_Malla_Menos_100,

    l.CuFe,
    l.Fuente_CuFe,

    l.Caolinita,
    l.Fuente_Caolinita,

    l.CaolBeta,
    l.Fuente_CaolBeta,

    l.Cuarzo,
    l.Fuente_Cuarzo,

    CASE
        WHEN b.TMS_Sin_Sal_Con_SRR IS NULL
          OR l.CuT IS NULL
            THEN NULL
        ELSE b.TMS_Sin_Sal_Con_SRR * l.CuT / 100.0
    END AS Fino_CuT,

    CASE
        WHEN b.TMS_Sin_Sal_Con_SRR IS NULL
          OR l.CuS IS NULL
            THEN NULL
        ELSE b.TMS_Sin_Sal_Con_SRR * l.CuS / 100.0
    END AS Fino_CuS,

    CASE
        WHEN b.TMS_Sin_Sal_Con_SRR IS NULL
          OR l.FeT IS NULL
            THEN NULL
        ELSE b.TMS_Sin_Sal_Con_SRR * l.FeT / 100.0
    END AS Fino_FeT,

    CASE
        WHEN b.TMS_Sin_Sal_Con_SRR IS NULL
          OR l.FeS IS NULL
            THEN NULL
        ELSE b.TMS_Sin_Sal_Con_SRR * l.FeS / 100.0
    END AS Fino_FeS,

    CASE
        WHEN l.CuT IS NULL
          OR l.CuT = 0
          OR l.CuS IS NULL
            THEN NULL
        ELSE l.CuS / NULLIF(l.CuT, 0)
    END AS RS_CuS_CuT

FROM base_tms b

LEFT JOIN inventar_SpcHidr.v_leyes_validadas_tm_turno l
    ON l.Fecha = b.Fecha
   AND l.Turno = b.Turno
   AND l.TM = b.TM;