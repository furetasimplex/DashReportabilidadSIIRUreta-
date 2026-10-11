
CREATE VIEW [inventar_SpcHidr].[v_srr_tms_diario_test]
AS

WITH Turnos AS
(
SELECT
Fecha,

    MAX
    (
        CASE
            WHEN Turno = 'A'
                THEN SRR_TMH_Oficial
        END
    ) AS SRR_TMH_Turno_A,

    MAX
    (
        CASE
            WHEN Turno = 'B'
                THEN SRR_TMH_Oficial
        END
    ) AS SRR_TMH_Turno_B,

    MAX
    (
        CASE
            WHEN Turno = 'A'
                THEN SRR_TMS_TM1
        END
    ) AS SRR_TMS_TM1_Turno_A,

    MAX
    (
        CASE
            WHEN Turno = 'A'
                THEN SRR_TMS_TM2
        END
    ) AS SRR_TMS_TM2_Turno_A,

    MAX
    (
        CASE
            WHEN Turno = 'B'
                THEN SRR_TMS_TM1
        END
    ) AS SRR_TMS_TM1_Turno_B,

    MAX
    (
        CASE
            WHEN Turno = 'B'
                THEN SRR_TMS_TM2
        END
    ) AS SRR_TMS_TM2_Turno_B,

    MAX
    (
        CASE
            WHEN Turno = 'A'
                THEN SRR_TMS_Oficial
        END
    ) AS SRR_TMS_Turno_A,

    MAX
    (
        CASE
            WHEN Turno = 'B'
                THEN SRR_TMS_Oficial
        END
    ) AS SRR_TMS_Turno_B,

    MAX(Humedad_TM1) AS Humedad_TM1_Usada,
    MAX(Humedad_TM2) AS Humedad_TM2_Usada,

    MAX(Fecha_Humedad_TM1) AS Fecha_Humedad_TM1,
    MAX(Fuente_Humedad_TM1) AS Fuente_Humedad_TM1,

    MAX(Fecha_Humedad_TM2) AS Fecha_Humedad_TM2,
    MAX(Fuente_Humedad_TM2) AS Fuente_Humedad_TM2,

    MAX(Fuente_SRR) AS Fuente_SRR,

    MAX
    (
        CASE
            WHEN Turno = 'A'
                THEN Flag_SRR_TMS
        END
    ) AS Flag_SRR_TMS_A,

    MAX
    (
        CASE
            WHEN Turno = 'B'
                THEN Flag_SRR_TMS
        END
    ) AS Flag_SRR_TMS_B

FROM [inventar_SpcHidr].[v_srr_tms_turno_test]

GROUP BY Fecha

)

SELECT
t.Fecha,

t.SRR_TMH_Turno_A,
t.SRR_TMH_Turno_B,

CASE
    WHEN t.SRR_TMH_Turno_A IS NULL
      OR t.SRR_TMH_Turno_B IS NULL
        THEN NULL

    ELSE
        t.SRR_TMH_Turno_A
        + t.SRR_TMH_Turno_B
END AS SRR_TMH_Dia,

t.SRR_TMS_TM1_Turno_A,
t.SRR_TMS_TM2_Turno_A,
t.SRR_TMS_TM1_Turno_B,
t.SRR_TMS_TM2_Turno_B,

t.SRR_TMS_Turno_A,
t.SRR_TMS_Turno_B,

CASE
    WHEN t.SRR_TMS_Turno_A IS NULL
      OR t.SRR_TMS_Turno_B IS NULL
        THEN NULL

    ELSE
        t.SRR_TMS_Turno_A
        + t.SRR_TMS_Turno_B
END AS SRR_TMS_Dia,

t.Humedad_TM1_Usada,
t.Humedad_TM2_Usada,

t.Fecha_Humedad_TM1,
t.Fuente_Humedad_TM1,

t.Fecha_Humedad_TM2,
t.Fuente_Humedad_TM2,

d.TMH_CV001_Dia,
d.TMH_CV002_Dia,
d.TMH_CV003_Dia,
d.TMH_CV002_003_Dia,

d.Diferencia_TMH_Dia,
d.Diferencia_Porcentaje_Dia,

t.Fuente_SRR,

t.Flag_SRR_TMS_A,
t.Flag_SRR_TMS_B,

CASE
    WHEN t.Flag_SRR_TMS_A IN
         (
             'OK',
             'OK_SIN_SRR'
         )
     AND t.Flag_SRR_TMS_B IN
         (
             'OK',
             'OK_SIN_SRR'
         )
        THEN 'OK'

    ELSE 'REVISAR'
END AS Flag_SRR_TMS_Dia,

d.Flag_Totalizadores_Dia,
d.Flag_Comparacion_Dia

FROM Turnos t

LEFT JOIN
[inventar_SpcHidr].[v_srr_totalizadores_diario_test] d
ON d.Fecha = t.Fecha;
