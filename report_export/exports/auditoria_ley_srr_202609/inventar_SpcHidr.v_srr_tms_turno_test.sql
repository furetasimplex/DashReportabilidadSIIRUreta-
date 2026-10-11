CREATE VIEW
    [inventar_SpcHidr].[v_srr_tms_turno_test]
AS

WITH Base AS
(
    SELECT
        s.Fecha,
        s.Turno,
        s.Inicio_Turno,
        s.Fin_Turno,

        /* Totalizadores */
        s.TMH_CV001,
        s.TMH_CV002,
        s.TMH_CV003,
        s.TMH_CV002_003,
        s.Diferencia_TMH,
        s.Diferencia_Porcentaje,

        /* SRR oficial provisional */
        s.SRR_TMH_Oficial,
        s.Fuente_SRR,
        s.Flag_Totalizadores,
        s.Flag_Comparacion,

        /* Humedad diaria resuelta por torre */
        h.Humedad_TM1,
        h.Humedad_TM2,

        h.Fecha_Humedad_TM1,
        h.Torre_Humedad_TM1,
        h.Turno_Humedad_TM1,
        h.Fuente_Humedad_TM1,

        h.Fecha_Humedad_TM2,
        h.Torre_Humedad_TM2,
        h.Turno_Humedad_TM2,
        h.Fuente_Humedad_TM2

    FROM [inventar_SpcHidr].[v_srr_totalizadores_turno_test] s

    LEFT JOIN
        [inventar_SpcHidr].[v_apilado_tms_con_sal_srr_reporte_test] h
        ON h.Fecha = s.Fecha
),

Distribucion AS
(
    SELECT
        *,

        CASE
            WHEN SRR_TMH_Oficial IS NULL THEN NULL
            ELSE SRR_TMH_Oficial / 2.0
        END AS SRR_TMH_TM1,

        CASE
            WHEN SRR_TMH_Oficial IS NULL THEN NULL
            ELSE SRR_TMH_Oficial / 2.0
        END AS SRR_TMH_TM2

    FROM Base
),

Calculo AS
(
    SELECT
        *,

        CASE
            WHEN SRR_TMH_Oficial IS NULL
                THEN NULL

            WHEN SRR_TMH_Oficial = 0
                THEN 0

            WHEN Humedad_TM1 IS NULL
                THEN NULL

            WHEN Humedad_TM1 < 0
              OR Humedad_TM1 >= 100
                THEN NULL

            ELSE
                SRR_TMH_TM1
                * (1.0 - Humedad_TM1 / 100.0)
        END AS SRR_TMS_TM1,

        CASE
            WHEN SRR_TMH_Oficial IS NULL
                THEN NULL

            WHEN SRR_TMH_Oficial = 0
                THEN 0

            WHEN Humedad_TM2 IS NULL
                THEN NULL

            WHEN Humedad_TM2 < 0
              OR Humedad_TM2 >= 100
                THEN NULL

            ELSE
                SRR_TMH_TM2
                * (1.0 - Humedad_TM2 / 100.0)
        END AS SRR_TMS_TM2

    FROM Distribucion
)

SELECT
    Fecha,
    Turno,
    Inicio_Turno,
    Fin_Turno,

    /* Comparación de correas */
    TMH_CV001,
    TMH_CV002,
    TMH_CV003,
    TMH_CV002_003,
    Diferencia_TMH,
    Diferencia_Porcentaje,

    /* Distribución 50/50 del SRR oficial */
    SRR_TMH_Oficial,
    SRR_TMH_TM1,
    SRR_TMH_TM2,

    CASE
        WHEN SRR_TMH_TM1 IS NULL
          OR SRR_TMH_TM2 IS NULL
            THEN NULL
        ELSE
            SRR_TMH_TM1
            + SRR_TMH_TM2
            - SRR_TMH_Oficial
    END AS Check_Distribucion_TMH,

    /* Humedades utilizadas */
    Humedad_TM1,
    Humedad_TM2,

    CASE
        WHEN Humedad_TM1 IS NULL
          OR Humedad_TM2 IS NULL
            THEN NULL
        ELSE
            (Humedad_TM1 + Humedad_TM2) / 2.0
    END AS Humedad_Equivalente_SRR,

    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,

    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2,

    /* SRR seco */
    SRR_TMS_TM1,
    SRR_TMS_TM2,

    CASE
        WHEN SRR_TMS_TM1 IS NULL
          OR SRR_TMS_TM2 IS NULL
            THEN NULL
        ELSE
            SRR_TMS_TM1 + SRR_TMS_TM2
    END AS SRR_TMS_Oficial,

    Fuente_SRR,

    CAST
    (
        'CV001_CORREGIDO_50_50_HUMEDAD_DIARIA_POR_TORRE'
        AS varchar(60)
    ) AS Metodo_Calculo_SRR,

    Flag_Totalizadores,
    Flag_Comparacion,

    CASE
        WHEN Flag_Totalizadores <> 'OK'
            THEN 'REVISAR_TOTALIZADORES'

        WHEN SRR_TMH_Oficial IS NULL
            THEN 'SIN_SRR_TMH'

        WHEN SRR_TMH_Oficial = 0
            THEN 'OK_SIN_SRR'

        WHEN Humedad_TM1 IS NULL
            THEN 'SIN_HUMEDAD_TM1'

        WHEN Humedad_TM2 IS NULL
            THEN 'SIN_HUMEDAD_TM2'

        WHEN Humedad_TM1 < 0
          OR Humedad_TM1 >= 100
            THEN 'HUMEDAD_TM1_INVALIDA'

        WHEN Humedad_TM2 < 0
          OR Humedad_TM2 >= 100
            THEN 'HUMEDAD_TM2_INVALIDA'

        ELSE 'OK'
    END AS Flag_SRR_TMS

FROM Calculo;
