CREATE   VIEW inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_leyes_dia AS

SELECT
    Fecha,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR ELSE 0 END)
        AS TMS_Sin_Sal_Con_SRR_Dia,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN Fino_CuT ELSE 0 END)
        AS Fino_CuT_Dia,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN Fino_CuS ELSE 0 END)
        AS Fino_CuS_Dia,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN Fino_FeT ELSE 0 END)
        AS Fino_FeT_Dia,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN Fino_FeS ELSE 0 END)
        AS Fino_FeS_Dia,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR * CuT ELSE 0 END)
        / NULLIF(SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR ELSE 0 END), 0)
        AS CuT_Pond,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR * CuS ELSE 0 END)
        / NULLIF(SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR ELSE 0 END), 0)
        AS CuS_Pond,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR * FeT ELSE 0 END)
        / NULLIF(SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR ELSE 0 END), 0)
        AS FeT_Pond,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR * FeS ELSE 0 END)
        / NULLIF(SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR ELSE 0 END), 0)
        AS FeS_Pond,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR * CO3 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR ELSE 0 END), 0)
        AS CO3_Pond,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR * ConsH ELSE 0 END)
        / NULLIF(SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR ELSE 0 END), 0)
        AS ConsH_Pond,

    SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR * Malla_Menos_100 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN Flag_TMS_Valido = 1 THEN TMS_Sin_Sal_Con_SRR ELSE 0 END), 0)
        AS Malla_Menos_100_Pond,

    CASE
        WHEN SUM(CASE WHEN Flag_TMS_Valido = 1 THEN Fino_CuT ELSE 0 END) = 0 THEN NULL
        ELSE
            SUM(CASE WHEN Flag_TMS_Valido = 1 THEN Fino_CuS ELSE 0 END)
            / NULLIF(SUM(CASE WHEN Flag_TMS_Valido = 1 THEN Fino_CuT ELSE 0 END), 0)
    END AS RS_CuS_CuT_Pond

FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_leyes_tm

GROUP BY Fecha;