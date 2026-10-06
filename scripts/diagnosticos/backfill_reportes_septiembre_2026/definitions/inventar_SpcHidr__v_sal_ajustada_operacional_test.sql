
CREATE   VIEW
[inventar_SpcHidr].[v_sal_ajustada_operacional_test]
AS

WITH base AS
(
    SELECT
        s.Fecha,

        s.CV201_TA,
        s.CV201_TB,
        s.CV202_TA,
        s.CV202_TB,

        s.Sal_Pesometros_TA,
        s.Sal_Pesometros_TB,
        s.Sal_Pesometros_Dia,

        s.Sal_Topografia_Dia,

        s.Flag_Sal_Basica_Valida,

        s.Flag_Sal_Ajuste_Valido
            AS Flag_Sal_Ajuste_Valido_Origen,

        s.Sal_Ajustada_TA
            AS Sal_Ajustada_TA_Origen,

        s.Sal_Ajustada_TB
            AS Sal_Ajustada_TB_Origen,

        s.Sal_Ajustada_Dia
            AS Sal_Ajustada_Dia_Origen,

        t.TMH_Total_Con_Sal_SRR_A
            AS TMH_Bruto_A,

        t.TMH_Total_Con_Sal_SRR_B
            AS TMH_Bruto_B

    FROM [inventar_SpcHidr].[v_sal_ajustada] s

    LEFT JOIN
        [inventar_SpcHidr].
        [v_apilado_tms_con_sal_srr_reporte_test] t
        ON t.Fecha = s.Fecha
),

calculo AS
(
    SELECT
        b.*,

        CASE
            WHEN COALESCE(b.Sal_Topografia_Dia, 0) <= 0
                THEN 0

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 0

            /* Solo A tuvo apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN b.Sal_Topografia_Dia

            /* Solo B tuvo apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN 0

            /* Ambos turnos tuvieron apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
             AND
                 COALESCE(b.Sal_Pesometros_TA, 0)
               + COALESCE(b.Sal_Pesometros_TB, 0) > 0
                THEN
                    b.Sal_Topografia_Dia
                    * COALESCE(b.Sal_Pesometros_TA, 0)
                    /
                    NULLIF
                    (
                        COALESCE(b.Sal_Pesometros_TA, 0)
                      + COALESCE(b.Sal_Pesometros_TB, 0),
                        0
                    )

            ELSE 0
        END AS Sal_Ajustada_TA_Candidata,

        CASE
            WHEN COALESCE(b.Sal_Topografia_Dia, 0) <= 0
                THEN 0

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 0

            /* Solo A tuvo apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 0

            /* Solo B tuvo apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN b.Sal_Topografia_Dia

            /* Ambos turnos tuvieron apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
             AND
                 COALESCE(b.Sal_Pesometros_TA, 0)
               + COALESCE(b.Sal_Pesometros_TB, 0) > 0
                THEN
                    b.Sal_Topografia_Dia
                    * COALESCE(b.Sal_Pesometros_TB, 0)
                    /
                    NULLIF
                    (
                        COALESCE(b.Sal_Pesometros_TA, 0)
                      + COALESCE(b.Sal_Pesometros_TB, 0),
                        0
                    )

            ELSE 0
        END AS Sal_Ajustada_TB_Candidata,

        CASE
            WHEN COALESCE(b.Sal_Topografia_Dia, 0) <= 0
                THEN 0

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 0

            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 1

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN 1

            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
             AND b.Flag_Sal_Basica_Valida = 1
             AND
                 COALESCE(b.Sal_Pesometros_TA, 0)
               + COALESCE(b.Sal_Pesometros_TB, 0) > 0
                THEN 1

            ELSE 0
        END AS Flag_Sal_Ajuste_Valido_Candidato,

        CASE
            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 'SIN_APILADO'

            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 'TODA_SAL_TURNO_A'

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN 'TODA_SAL_TURNO_B'

            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN 'AMBOS_TURNOS_PROPORCIONAL'

            ELSE 'NO_EVALUABLE'
        END AS Regla_Distribucion

    FROM base b
)

SELECT
    Fecha,

    CV201_TA,
    CV201_TB,
    CV202_TA,
    CV202_TB,

    Sal_Pesometros_TA,
    Sal_Pesometros_TB,
    Sal_Pesometros_Dia,

    Sal_Topografia_Dia,

    TMH_Bruto_A,
    TMH_Bruto_B,

    Flag_Sal_Basica_Valida,
    Flag_Sal_Ajuste_Valido_Origen,

    Sal_Ajustada_TA_Origen,
    Sal_Ajustada_TB_Origen,
    Sal_Ajustada_Dia_Origen,

    Flag_Sal_Ajuste_Valido_Candidato
        AS Flag_Sal_Ajuste_Valido,

    Sal_Ajustada_TA_Candidata
        AS Sal_Ajustada_TA,

    Sal_Ajustada_TB_Candidata
        AS Sal_Ajustada_TB,

    Sal_Ajustada_TA_Candidata
    + Sal_Ajustada_TB_Candidata
        AS Sal_Ajustada_Dia,

    TMH_Bruto_A
    - Sal_Ajustada_TA_Candidata
        AS Apilado_TMH_A_Candidato,

    TMH_Bruto_B
    - Sal_Ajustada_TB_Candidata
        AS Apilado_TMH_B_Candidato,

    Regla_Distribucion

FROM calculo;
