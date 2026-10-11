
CREATE   VIEW
    [inventar_SpcHidr].[v_srr_totalizadores_diario_test]
AS

WITH Turnos AS
(
    SELECT
        Fecha,

        MAX
        (
            CASE WHEN Turno = 'A'
                 THEN TMH_CV001
            END
        ) AS TMH_CV001_Turno_A,

        MAX
        (
            CASE WHEN Turno = 'B'
                 THEN TMH_CV001
            END
        ) AS TMH_CV001_Turno_B,

        MAX
        (
            CASE WHEN Turno = 'A'
                 THEN TMH_CV002
            END
        ) AS TMH_CV002_Turno_A,

        MAX
        (
            CASE WHEN Turno = 'B'
                 THEN TMH_CV002
            END
        ) AS TMH_CV002_Turno_B,

        MAX
        (
            CASE WHEN Turno = 'A'
                 THEN TMH_CV003
            END
        ) AS TMH_CV003_Turno_A,

        MAX
        (
            CASE WHEN Turno = 'B'
                 THEN TMH_CV003
            END
        ) AS TMH_CV003_Turno_B,

        MAX
        (
            CASE WHEN Turno = 'A'
                 THEN Flag_Totalizadores
            END
        ) AS Flag_Totalizadores_A,

        MAX
        (
            CASE WHEN Turno = 'B'
                 THEN Flag_Totalizadores
            END
        ) AS Flag_Totalizadores_B,

        MAX
        (
            CASE WHEN Turno = 'A'
                 THEN Flag_Comparacion
            END
        ) AS Flag_Comparacion_A,

        MAX
        (
            CASE WHEN Turno = 'B'
                 THEN Flag_Comparacion
            END
        ) AS Flag_Comparacion_B

    FROM [inventar_SpcHidr].[v_srr_totalizadores_turno_test]

    GROUP BY Fecha
),

Diario AS
(
    SELECT
        *,

        CASE
            WHEN TMH_CV001_Turno_A IS NULL
              OR TMH_CV001_Turno_B IS NULL
                THEN NULL
            ELSE
                TMH_CV001_Turno_A
                + TMH_CV001_Turno_B
        END AS TMH_CV001_Dia,

        CASE
            WHEN TMH_CV002_Turno_A IS NULL
              OR TMH_CV002_Turno_B IS NULL
                THEN NULL
            ELSE
                TMH_CV002_Turno_A
                + TMH_CV002_Turno_B
        END AS TMH_CV002_Dia,

        CASE
            WHEN TMH_CV003_Turno_A IS NULL
              OR TMH_CV003_Turno_B IS NULL
                THEN NULL
            ELSE
                TMH_CV003_Turno_A
                + TMH_CV003_Turno_B
        END AS TMH_CV003_Dia

    FROM Turnos
),

Comparacion AS
(
    SELECT
        *,

        TMH_CV002_Dia
        + TMH_CV003_Dia
            AS TMH_CV002_003_Dia,

        TMH_CV001_Dia
        -
        (
            TMH_CV002_Dia
            + TMH_CV003_Dia
        ) AS Diferencia_TMH_Dia

    FROM Diario
)

SELECT
    Fecha,

    /* CV001: fuente oficial del parche */
    TMH_CV001_Turno_A,
    TMH_CV001_Turno_B,
    TMH_CV001_Dia,

    /* CV002 */
    TMH_CV002_Turno_A,
    TMH_CV002_Turno_B,
    TMH_CV002_Dia,

    /* CV003 */
    TMH_CV003_Turno_A,
    TMH_CV003_Turno_B,
    TMH_CV003_Dia,

    /* Comparación CV002 + CV003 */
    TMH_CV002_003_Dia,
    Diferencia_TMH_Dia,

    CASE
        WHEN TMH_CV001_Dia IS NULL
          OR TMH_CV002_003_Dia IS NULL
            THEN NULL

        WHEN TMH_CV001_Dia = 0
            THEN NULL

        ELSE
            Diferencia_TMH_Dia
            / TMH_CV001_Dia
            * 100.0
    END AS Diferencia_Porcentaje_Dia,

    CASE
        WHEN TMH_CV001_Dia IS NULL
          OR TMH_CV002_003_Dia IS NULL
            THEN NULL

        WHEN TMH_CV001_Dia = 0
            THEN NULL

        ELSE
            TMH_CV002_003_Dia
            / TMH_CV001_Dia
            * 100.0
    END AS Cierre_CV002_003_Sobre_CV001_Dia,

    /* Valores oficiales para SRR */
    TMH_CV001_Turno_A AS SRR_TMH_Turno_A,
    TMH_CV001_Turno_B AS SRR_TMH_Turno_B,
    TMH_CV001_Dia     AS SRR_TMH_Dia,

    CAST('PARCHE_CV001' AS varchar(30))
        AS Fuente_SRR,

    Flag_Totalizadores_A,
    Flag_Totalizadores_B,

    CASE
        WHEN Flag_Totalizadores_A = 'OK'
         AND Flag_Totalizadores_B = 'OK'
            THEN 'OK'
        ELSE 'REVISAR'
    END AS Flag_Totalizadores_Dia,

    Flag_Comparacion_A,
    Flag_Comparacion_B,

    CASE
        WHEN TMH_CV001_Dia IS NULL
          OR TMH_CV002_003_Dia IS NULL
            THEN 'SIN_DATOS'

        WHEN ABS(Diferencia_TMH_Dia) <= 0.01
            THEN 'COINCIDE'

        ELSE 'DIFIERE'
    END AS Flag_Comparacion_Dia

FROM Comparacion;
