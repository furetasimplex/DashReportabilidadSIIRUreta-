
CREATE   VIEW
[inventar_SpcHidr].[v_apilado_tms_sin_sal_con_srr_reporte_test]
AS
WITH base AS (SELECT t.Fecha, t.Flag_Apilado_Valido, t.Flag_TMS_Valido, t.Observacion_TMS, t.Factor_Ajuste_Camiones_Usado, t.Humedad_TM1, t.Humedad_TM2, t.Humedad_Equivalente_Dia, t.Fecha_Humedad_TM1, t.Torre_Humedad_TM1, t.Turno_Humedad_TM1, 
                                     t.Fuente_Humedad_TM1, t.Fecha_Humedad_TM2, t.Torre_Humedad_TM2, t.Turno_Humedad_TM2, t.Fuente_Humedad_TM2, t.TMH_TM1_Con_Sal_SRR_A, t.TMH_TM1_Con_Sal_SRR_B, t.TMH_TM2_Con_Sal_SRR_A, t.TMH_TM2_Con_Sal_SRR_B, 
                                     t.TMH_Total_Con_Sal_SRR_A, t.TMH_Total_Con_Sal_SRR_B, t.TMH_Total_Con_Sal_SRR_Dia, t.TMS_TM1_Con_Sal_SRR_A, t.TMS_TM1_Con_Sal_SRR_B, t.TMS_TM2_Con_Sal_SRR_A, t.TMS_TM2_Con_Sal_SRR_B, t.TMS_Total_Con_Sal_SRR_A, 
                                     t.TMS_Total_Con_Sal_SRR_B, t.TMS_Total_Con_Sal_SRR_Dia, s.Sal_Pesometros_TA, s.Sal_Pesometros_TB, s.Sal_Pesometros_Dia, s.Sal_Topografia_Dia, s.Flag_Sal_Basica_Valida, s.Flag_Sal_Ajuste_Valido, s.Sal_Ajustada_TA, s.Sal_Ajustada_TB, 
                                     s.Sal_Ajustada_Dia, CASE WHEN t .TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL WHEN t .TMS_Total_Con_Sal_SRR_A = 0 THEN 0 ELSE COALESCE (s.Sal_Ajustada_TA, 0) * t .TMS_TM1_Con_Sal_SRR_A / NULLIF (t .TMS_Total_Con_Sal_SRR_A, 0) 
                                     END AS Sal_Asignada_TM1_A, CASE WHEN t .TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL WHEN t .TMS_Total_Con_Sal_SRR_A = 0 THEN 0 ELSE COALESCE (s.Sal_Ajustada_TA, 0) * t .TMS_TM2_Con_Sal_SRR_A / NULLIF (t .TMS_Total_Con_Sal_SRR_A, 0) 
                                     END AS Sal_Asignada_TM2_A, CASE WHEN t .TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL WHEN t .TMS_Total_Con_Sal_SRR_B = 0 THEN 0 ELSE COALESCE (s.Sal_Ajustada_TB, 0) * t .TMS_TM1_Con_Sal_SRR_B / NULLIF (t .TMS_Total_Con_Sal_SRR_B, 0) 
                                     END AS Sal_Asignada_TM1_B, CASE WHEN t .TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL WHEN t .TMS_Total_Con_Sal_SRR_B = 0 THEN 0 ELSE COALESCE (s.Sal_Ajustada_TB, 0) * t .TMS_TM2_Con_Sal_SRR_B / NULLIF (t .TMS_Total_Con_Sal_SRR_B, 0) 
                                     END AS Sal_Asignada_TM2_B
                        FROM    inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test AS t LEFT OUTER JOIN
                                     inventar_SpcHidr.v_sal_ajustada_operacional_test AS s ON s.Fecha = t.Fecha), tms_sin_sal AS
    (SELECT Fecha, Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS, Factor_Ajuste_Camiones_Usado, Humedad_TM1, Humedad_TM2, Humedad_Equivalente_Dia, Fecha_Humedad_TM1, Torre_Humedad_TM1, Turno_Humedad_TM1, Fuente_Humedad_TM1, Fecha_Humedad_TM2, 
                 Torre_Humedad_TM2, Turno_Humedad_TM2, Fuente_Humedad_TM2, TMH_TM1_Con_Sal_SRR_A, TMH_TM1_Con_Sal_SRR_B, TMH_TM2_Con_Sal_SRR_A, TMH_TM2_Con_Sal_SRR_B, TMH_Total_Con_Sal_SRR_A, TMH_Total_Con_Sal_SRR_B, TMH_Total_Con_Sal_SRR_Dia, 
                 TMS_TM1_Con_Sal_SRR_A, TMS_TM1_Con_Sal_SRR_B, TMS_TM2_Con_Sal_SRR_A, TMS_TM2_Con_Sal_SRR_B, TMS_Total_Con_Sal_SRR_A, TMS_Total_Con_Sal_SRR_B, TMS_Total_Con_Sal_SRR_Dia, Sal_Pesometros_TA, Sal_Pesometros_TB, Sal_Pesometros_Dia, 
                 Sal_Topografia_Dia, Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido, Sal_Ajustada_TA, Sal_Ajustada_TB, Sal_Ajustada_Dia, Sal_Asignada_TM1_A, Sal_Asignada_TM2_A, Sal_Asignada_TM1_B, Sal_Asignada_TM2_B, CASE WHEN b.TMS_TM1_Con_Sal_SRR_A IS NULL THEN NULL 
                 ELSE b.TMS_TM1_Con_Sal_SRR_A - COALESCE (b.Sal_Asignada_TM1_A, 0) END AS TMS_TM1_Sin_Sal_Con_SRR_A, CASE WHEN b.TMS_TM1_Con_Sal_SRR_B IS NULL THEN NULL ELSE b.TMS_TM1_Con_Sal_SRR_B - COALESCE (b.Sal_Asignada_TM1_B, 0) 
                 END AS TMS_TM1_Sin_Sal_Con_SRR_B, CASE WHEN b.TMS_TM2_Con_Sal_SRR_A IS NULL THEN NULL ELSE b.TMS_TM2_Con_Sal_SRR_A - COALESCE (b.Sal_Asignada_TM2_A, 0) END AS TMS_TM2_Sin_Sal_Con_SRR_A, CASE WHEN b.TMS_TM2_Con_Sal_SRR_B IS NULL 
                 THEN NULL ELSE b.TMS_TM2_Con_Sal_SRR_B - COALESCE (b.Sal_Asignada_TM2_B, 0) END AS TMS_TM2_Sin_Sal_Con_SRR_B
    FROM    base AS b)
    SELECT Fecha, Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS, Factor_Ajuste_Camiones_Usado, Humedad_TM1, Humedad_TM2, Humedad_Equivalente_Dia, Fecha_Humedad_TM1, Torre_Humedad_TM1, Turno_Humedad_TM1, Fuente_Humedad_TM1, Fecha_Humedad_TM2, 
                Torre_Humedad_TM2, Turno_Humedad_TM2, Fuente_Humedad_TM2, TMH_TM1_Con_Sal_SRR_A, TMH_TM1_Con_Sal_SRR_B, TMH_TM2_Con_Sal_SRR_A, TMH_TM2_Con_Sal_SRR_B, TMH_Total_Con_Sal_SRR_A, TMH_Total_Con_Sal_SRR_B, TMH_Total_Con_Sal_SRR_Dia, 
                TMS_TM1_Con_Sal_SRR_A, TMS_TM1_Con_Sal_SRR_B, TMS_TM2_Con_Sal_SRR_A, TMS_TM2_Con_Sal_SRR_B, TMS_Total_Con_Sal_SRR_A, TMS_Total_Con_Sal_SRR_B, TMS_Total_Con_Sal_SRR_Dia, Sal_Pesometros_TA, Sal_Pesometros_TB, Sal_Pesometros_Dia, 
                Sal_Topografia_Dia, Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido, Sal_Ajustada_TA, Sal_Ajustada_TB, Sal_Ajustada_Dia, Sal_Asignada_TM1_A, Sal_Asignada_TM2_A, Sal_Asignada_TM1_B, Sal_Asignada_TM2_B, 
                Sal_Asignada_TM1_A + Sal_Asignada_TM2_A AS Sal_Distribuida_A, Sal_Asignada_TM1_B + Sal_Asignada_TM2_B AS Sal_Distribuida_B, TMS_TM1_Sin_Sal_Con_SRR_A, TMS_TM1_Sin_Sal_Con_SRR_B, TMS_TM2_Sin_Sal_Con_SRR_A, TMS_TM2_Sin_Sal_Con_SRR_B, 
                TMS_TM1_Sin_Sal_Con_SRR_A + TMS_TM2_Sin_Sal_Con_SRR_A AS TMS_Total_Sin_Sal_Con_SRR_A, TMS_TM1_Sin_Sal_Con_SRR_B + TMS_TM2_Sin_Sal_Con_SRR_B AS TMS_Total_Sin_Sal_Con_SRR_B, 
                TMS_TM1_Sin_Sal_Con_SRR_A + TMS_TM1_Sin_Sal_Con_SRR_B + TMS_TM2_Sin_Sal_Con_SRR_A + TMS_TM2_Sin_Sal_Con_SRR_B AS TMS_Total_Sin_Sal_Con_SRR_Dia, TMS_Total_Con_Sal_SRR_Dia - COALESCE (Sal_Ajustada_Dia, 0) 
                AS TMS_Total_Sin_Sal_Con_SRR_Dia_Check, Sal_Asignada_TM1_A + Sal_Asignada_TM2_A - COALESCE (Sal_Ajustada_TA, 0) AS Check_Sal_A, Sal_Asignada_TM1_B + Sal_Asignada_TM2_B - COALESCE (Sal_Ajustada_TB, 0) AS Check_Sal_B
   FROM    tms_sin_sal