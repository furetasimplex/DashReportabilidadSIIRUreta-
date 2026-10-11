
CREATE   VIEW
    [inventar_SpcHidr].[v_srr_tag_tms_turno_test]
AS

/* ============================================================
   SRR TMS POR FECHA OPERACIONAL + TURNO

   Fuente de flujo:
       v_srr_tag_tmh_turno_test

   Fuente de humedad:
       v_apilado_tms_sin_sal_con_srr_reporte_test

   Metodología oficial:
       - El SRR húmedo se distribuye 50 % a TM1 y 50 % a TM2.
       - Cada mitad se convierte a seco con la humedad resuelta
         de su respectiva torre.
       - No utiliza IMP.
       - No utiliza el caché del Reporte por Turno.
   ============================================================ */

WITH humedad_dia AS
(
    SELECT
        CAST(v.Fecha AS date) AS Fecha,

        MAX(
            TRY_CONVERT(float, v.Humedad_TM1)
        ) AS Humedad_TM1,

        MAX(
            TRY_CONVERT(float, v.Humedad_TM2)
        ) AS Humedad_TM2,

        MAX(v.Fecha_Humedad_TM1)
            AS Fecha_Humedad_TM1,

        MAX(v.Torre_Humedad_TM1)
            AS Torre_Humedad_TM1,

        MAX(v.Turno_Humedad_TM1)
            AS Turno_Humedad_TM1,

        MAX(v.Fuente_Humedad_TM1)
            AS Fuente_Humedad_TM1,

        MAX(v.Fecha_Humedad_TM2)
            AS Fecha_Humedad_TM2,

        MAX(v.Torre_Humedad_TM2)
            AS Torre_Humedad_TM2,

        MAX(v.Turno_Humedad_TM2)
            AS Turno_Humedad_TM2,

        MAX(v.Fuente_Humedad_TM2)
            AS Fuente_Humedad_TM2

    FROM
        [inventar_SpcHidr].[v_apilado_tms_sin_sal_con_srr_reporte_test]
        AS v

    GROUP BY
        CAST(v.Fecha AS date)
)

SELECT
    s.Fecha,
    s.Turno,

    /* --------------------------------------------------------
       Trazabilidad del tag
       -------------------------------------------------------- */
    s.Cantidad_Registros,
    s.Cantidad_Registros_Esperados,

    s.Primera_FechaHora,
    s.Ultima_FechaHora,

    s.SRR_TPH_Minimo,
    s.SRR_TPH_Maximo,
    s.SRR_TPH_Promedio,

    s.Registros_En_Cero,
    s.Registros_Negativos,

    s.Segundos_Integrados,
    s.Cobertura_Pct,

    s.Brecha_Maxima_Segundos,
    s.Cantidad_Brechas_Mayores_30s,

    s.SRR_TMH_Tag,

    /* --------------------------------------------------------
       Humedades resueltas
       -------------------------------------------------------- */
    h.Humedad_TM1,
    h.Humedad_TM2,

    h.Fecha_Humedad_TM1,
    h.Torre_Humedad_TM1,
    h.Turno_Humedad_TM1,
    h.Fuente_Humedad_TM1,

    h.Fecha_Humedad_TM2,
    h.Torre_Humedad_TM2,
    h.Turno_Humedad_TM2,
    h.Fuente_Humedad_TM2,

    /* --------------------------------------------------------
       Distribución 50/50 y conversión a TMS
       -------------------------------------------------------- */
    CAST
    (
        CASE
            WHEN s.Flag_SRR_Tag_Valido <> 1
                THEN NULL

            WHEN h.Humedad_TM1 IS NULL
              OR h.Humedad_TM2 IS NULL
                THEN NULL

            WHEN h.Humedad_TM1 < 0
              OR h.Humedad_TM1 >= 100
              OR h.Humedad_TM2 < 0
              OR h.Humedad_TM2 >= 100
                THEN NULL

            ELSE
                s.SRR_TMH_Tag
                * 0.5
                * (1.0 - h.Humedad_TM1 / 100.0)
        END

        AS decimal(18,6)
    ) AS SRR_TMS_TM1_Tag,

    CAST
    (
        CASE
            WHEN s.Flag_SRR_Tag_Valido <> 1
                THEN NULL

            WHEN h.Humedad_TM1 IS NULL
              OR h.Humedad_TM2 IS NULL
                THEN NULL

            WHEN h.Humedad_TM1 < 0
              OR h.Humedad_TM1 >= 100
              OR h.Humedad_TM2 < 0
              OR h.Humedad_TM2 >= 100
                THEN NULL

            ELSE
                s.SRR_TMH_Tag
                * 0.5
                * (1.0 - h.Humedad_TM2 / 100.0)
        END

        AS decimal(18,6)
    ) AS SRR_TMS_TM2_Tag,

    CAST
    (
        CASE
            WHEN s.Flag_SRR_Tag_Valido <> 1
                THEN NULL

            WHEN h.Humedad_TM1 IS NULL
              OR h.Humedad_TM2 IS NULL
                THEN NULL

            WHEN h.Humedad_TM1 < 0
              OR h.Humedad_TM1 >= 100
              OR h.Humedad_TM2 < 0
              OR h.Humedad_TM2 >= 100
                THEN NULL

            ELSE
                s.SRR_TMH_Tag
                *
                (
                    0.5
                    * (1.0 - h.Humedad_TM1 / 100.0)

                    +

                    0.5
                    * (1.0 - h.Humedad_TM2 / 100.0)
                )
        END

        AS decimal(18,6)
    ) AS SRR_TMS_Tag,

    /* --------------------------------------------------------
       Evaluación final
       -------------------------------------------------------- */
    CAST
    (
        CASE
            WHEN s.Flag_SRR_Tag_Valido <> 1
                THEN 0

            WHEN h.Humedad_TM1 IS NULL
              OR h.Humedad_TM2 IS NULL
                THEN 0

            WHEN h.Humedad_TM1 < 0
              OR h.Humedad_TM1 >= 100
              OR h.Humedad_TM2 < 0
              OR h.Humedad_TM2 >= 100
                THEN 0

            ELSE 1
        END

        AS bit
    ) AS Flag_SRR_TMS_Valido,

    CAST
    (
        CASE
            WHEN s.Flag_SRR_Tag_Valido <> 1
                THEN s.Estado_SRR_Tag

            WHEN h.Humedad_TM1 IS NULL
              OR h.Humedad_TM2 IS NULL
                THEN 'SIN_HUMEDAD_RESUELTA'

            WHEN h.Humedad_TM1 < 0
              OR h.Humedad_TM1 >= 100
              OR h.Humedad_TM2 < 0
              OR h.Humedad_TM2 >= 100
                THEN 'HUMEDAD_INVALIDA'

            ELSE 'OK'
        END

        AS varchar(40)
    ) AS Estado_SRR_TMS,

    CAST('TOT_TM_TOT001' AS varchar(40))
        AS Fuente_SRR

FROM
    [inventar_SpcHidr].[v_srr_tag_tmh_turno_test]
    AS s

LEFT JOIN humedad_dia AS h
    ON h.Fecha = s.Fecha;
