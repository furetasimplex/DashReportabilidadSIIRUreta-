CREATE   VIEW
[inventar_SpcHidr].[v_reporte_diario_apilado_test]
AS


WITH base AS (SELECT v.Fecha, CAST(1.0 AS float) AS Factor_Ajuste_Camiones, h.Humedad_Turno_A, h.Humedad_Turno_B, h.Humedad_promedio_dia, v.TMH_Total_Con_Sal_SRR_A AS TMH_Bruto_A, v.TMH_Total_Con_Sal_SRR_B AS TMH_Bruto_B, 
                                     v.TMH_Total_Con_Sal_SRR_Dia AS TMH_Bruto_Dia, v.Sal_Ajustada_TA AS Sal_Ajustada_A, v.Sal_Ajustada_TB AS Sal_Ajustada_B, v.Sal_Ajustada_Dia, v.TMS_Total_Sin_Sal_Con_SRR_A AS TMS_Sin_Sal_A, v.TMS_Total_Sin_Sal_Con_SRR_B AS TMS_Sin_Sal_B, 
                                     v.TMS_Total_Sin_Sal_Con_SRR_Dia AS TMS_Sin_Sal_Dia, v.Sal_Pesometros_TA, v.Sal_Pesometros_TB, v.Sal_Pesometros_Dia, v.Sal_Topografia_Dia, v.Flag_Sal_Basica_Valida, v.Flag_Sal_Ajuste_Valido, v.Flag_Apilado_Valido, v.Flag_TMS_Valido, 
                                     v.Observacion_TMS
                        FROM    inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test AS v LEFT OUTER JOIN
                                     inventar_SpcHidr.v_reporte_diario_humedad_test AS h ON h.Fecha = v.Fecha), calculo AS
    (SELECT Fecha, Factor_Ajuste_Camiones, Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia, TMH_Bruto_A, TMH_Bruto_B, TMH_Bruto_Dia, Sal_Ajustada_A, Sal_Ajustada_B, Sal_Ajustada_Dia, TMS_Sin_Sal_A, TMS_Sin_Sal_B, TMS_Sin_Sal_Dia, Sal_Pesometros_TA, 
                 Sal_Pesometros_TB, Sal_Pesometros_Dia, Sal_Topografia_Dia, Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido, Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS, COALESCE (Sal_Ajustada_A, 0) AS Sal_turno_A, COALESCE (Sal_Ajustada_B, 0) AS Sal_turno_B, 
                 COALESCE (Sal_Ajustada_A, 0) + COALESCE (Sal_Ajustada_B, 0) AS Sal_Dia, TMH_Bruto_A * Factor_Ajuste_Camiones - COALESCE (Sal_Ajustada_A, 0) AS Apilado_TMH_turno_A, TMH_Bruto_B * Factor_Ajuste_Camiones - COALESCE (Sal_Ajustada_B, 0) 
                 AS Apilado_TMH_turno_B, CASE WHEN COALESCE (b.TMH_Bruto_A, 0) = 0 THEN 0 WHEN b.Humedad_Turno_A IS NULL THEN NULL ELSE b.TMH_Bruto_A * b.Factor_Ajuste_Camiones * (1 - b.Humedad_Turno_A / 100.0) - COALESCE (b.Sal_Ajustada_A, 0) 
                 END AS Apilado_TMS_turno_A_Recalculado, CASE WHEN COALESCE (b.TMH_Bruto_B, 0) = 0 THEN 0 WHEN b.Humedad_Turno_B IS NULL THEN NULL ELSE b.TMH_Bruto_B * b.Factor_Ajuste_Camiones * (1 - b.Humedad_Turno_B / 100.0) - COALESCE (b.Sal_Ajustada_B, 0) 
                 END AS Apilado_TMS_turno_B_Recalculado
    FROM    base AS b), resultado AS
    (SELECT Fecha, Factor_Ajuste_Camiones, Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia, TMH_Bruto_A, TMH_Bruto_B, TMH_Bruto_Dia, Sal_Ajustada_A, Sal_Ajustada_B, Sal_Ajustada_Dia, TMS_Sin_Sal_A, TMS_Sin_Sal_B, TMS_Sin_Sal_Dia, Sal_Pesometros_TA, 
                 Sal_Pesometros_TB, Sal_Pesometros_Dia, Sal_Topografia_Dia, Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido, Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS, Sal_turno_A, Sal_turno_B, Sal_Dia, Apilado_TMH_turno_A, Apilado_TMH_turno_B, 
                 Apilado_TMS_turno_A_Recalculado, Apilado_TMS_turno_B_Recalculado, Apilado_TMH_turno_A + Apilado_TMH_turno_B AS Apilado_TMH_Dia, Apilado_TMS_turno_A_Recalculado + Apilado_TMS_turno_B_Recalculado AS Apilado_TMS_Dia_Recalculado
    FROM    calculo AS c)
   
   SELECT
    r.Fecha,

    /* =========================================================
       HUMEDAD OPERACIONAL PUBLICABLE
       ========================================================= */
    CASE
        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) <= 0
            THEN 0.0
        ELSE r.Humedad_Turno_A
    END AS Humedad_Turno_A,

    CASE
        WHEN COALESCE(r.Apilado_TMH_turno_B, 0) <= 0
            THEN 0.0
        ELSE r.Humedad_Turno_B
    END AS Humedad_Turno_B,

    CASE
        /* No hubo apilado durante el día */
        WHEN COALESCE(r.Apilado_TMH_Dia, 0) <= 0
            THEN 0.0

        /* Solo tuvo apilado el turno A */
        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) <= 0
            THEN r.Humedad_Turno_A

        /* Solo tuvo apilado el turno B */
        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) <= 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) > 0
            THEN r.Humedad_Turno_B

        /* Ambos turnos tuvieron apilado */
        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) > 0
            THEN
                (
                    r.Apilado_TMH_turno_A * r.Humedad_Turno_A
                    +
                    r.Apilado_TMH_turno_B * r.Humedad_Turno_B
                )
                / NULLIF(r.Apilado_TMH_Dia, 0)

        ELSE 0.0
    END AS Humedad_promedio_dia,

    /* =========================================================
       SAL
       ========================================================= */
    r.Sal_turno_A,
    r.Sal_turno_B,
    r.Sal_Dia AS Sal_promedio_dia,

    /* =========================================================
       APILADO TMH
       ========================================================= */
    r.Apilado_TMH_turno_A,
    r.Apilado_TMH_turno_B,
    r.Apilado_TMH_Dia AS Apilado_TMH_promedio_dia,

    /* =========================================================
       APILADO TMS
       ========================================================= */
    r.Apilado_TMS_Dia_Recalculado AS Apilado_TMS_Real,
    r.Apilado_TMS_turno_A_Recalculado,
    r.Apilado_TMS_turno_B_Recalculado,

    /* =========================================================
       TRAZABILIDAD
       ========================================================= */
    r.Factor_Ajuste_Camiones,
    r.TMH_Bruto_A,
    r.TMH_Bruto_B,
    r.TMH_Bruto_Dia,

    r.Sal_Pesometros_TA,
    r.Sal_Pesometros_TB,
    r.Sal_Pesometros_Dia,
    r.Sal_Topografia_Dia,
    r.Sal_Ajustada_Dia,

    r.Flag_Sal_Basica_Valida,
    r.Flag_Sal_Ajuste_Valido,

    /* =========================================================
       FLAG DE APILADO RECALCULADO CON EL TMH NETO
       ========================================================= */
    CASE
        WHEN COALESCE(r.Apilado_TMH_Dia, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_A, 0) >= 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) >= 0
            THEN 1
        ELSE 0
    END AS Flag_Apilado_Valido,

    /* =========================================================
       FLAG DE TMS RECALCULADO
       ========================================================= */
    CASE
        WHEN r.Apilado_TMS_Dia_Recalculado IS NOT NULL
         AND r.Apilado_TMS_Dia_Recalculado > 0
         AND COALESCE(
                 r.Apilado_TMS_turno_A_Recalculado,
                 0
             ) >= 0
         AND COALESCE(
                 r.Apilado_TMS_turno_B_Recalculado,
                 0
             ) >= 0
            THEN 1
        ELSE 0
    END AS Flag_TMS_Valido,

    /* =========================================================
       OBSERVACIÓN OPERACIONAL RECALCULADA
       ========================================================= */
    CASE
        WHEN COALESCE(r.Apilado_TMH_Dia, 0) <= 0
            THEN 'SIN_APILADO_DIA'

        WHEN r.Apilado_TMS_Dia_Recalculado IS NULL
            THEN 'HUMEDAD_NO_DISPONIBLE'

        WHEN COALESCE(
                 r.Apilado_TMS_turno_A_Recalculado,
                 0
             ) < 0
          OR COALESCE(
                 r.Apilado_TMS_turno_B_Recalculado,
                 0
             ) < 0
            THEN 'TMS_NEGATIVO'

        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) <= 0
            THEN 'APILADO_VALIDO_SOLO_TURNO_A'

        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) <= 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) > 0
            THEN 'APILADO_VALIDO_SOLO_TURNO_B'

        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) > 0
            THEN 'APILADO_VALIDO_AMBOS_TURNOS'

        ELSE 'APILADO_NO_EVALUABLE'
    END AS Observacion_TMS,

    /* =========================================================
       CHECKS EXISTENTES
       ========================================================= */
    r.Sal_Dia
      - COALESCE(r.Sal_Ajustada_Dia, 0)
        AS Check_Sal_Dia,

    r.Apilado_TMH_Dia
      - (
            r.Apilado_TMH_turno_A
          + r.Apilado_TMH_turno_B
        )
        AS Check_TMH_Dia,

    r.Apilado_TMS_Dia_Recalculado
      - (
            r.Apilado_TMS_turno_A_Recalculado
          + r.Apilado_TMS_turno_B_Recalculado
        )
        AS Check_TMS_Dia,

    r.Apilado_TMS_turno_A_Recalculado
      - r.TMS_Sin_Sal_A
        AS Check_TMS_A_Fuente,

    r.Apilado_TMS_turno_B_Recalculado
      - r.TMS_Sin_Sal_B
        AS Check_TMS_B_Fuente,

    r.Apilado_TMS_Dia_Recalculado
      - r.TMS_Sin_Sal_Dia
        AS Check_TMS_Dia_Fuente

FROM resultado AS r;