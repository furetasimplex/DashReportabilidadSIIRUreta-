
CREATE VIEW [inventar_SpcHidr].[v_srr_totalizadores_turno_test]
AS

WITH DatosHora AS
(
SELECT
fecha_inicial,
fecha_final,
fecha_turno,

    TRY_CONVERT(decimal(20,6), cv001_tot) AS cv001_tot,
    TRY_CONVERT(decimal(20,6), cv002_tot) AS cv002_tot,
    TRY_CONVERT(decimal(20,6), cv003_tot) AS cv003_tot,

    ROW_NUMBER() OVER
    (
        PARTITION BY fecha_inicial
        ORDER BY fecha_final DESC
    ) AS rn

FROM [inventar_SpcHidr].[datos_filtrados]

WHERE fecha_turno IS NOT NULL

),

FechasOperacion AS
(
SELECT DISTINCT
fecha_turno AS Fecha

FROM DatosHora

WHERE rn = 1

),

Periodos AS
(
SELECT
Fecha,
CAST('A' AS varchar(1)) AS Turno,

    DATEADD
    (
        HOUR,
        8,
        CAST(Fecha AS datetime2)
    ) AS Inicio_Turno,

    DATEADD
    (
        HOUR,
        20,
        CAST(Fecha AS datetime2)
    ) AS Fin_Turno

FROM FechasOperacion

UNION ALL

SELECT
    Fecha,
    CAST('B' AS varchar(1)) AS Turno,

    DATEADD
    (
        HOUR,
        20,
        CAST(Fecha AS datetime2)
    ) AS Inicio_Turno,

    DATEADD
    (
        HOUR,
        32,
        CAST(Fecha AS datetime2)
    ) AS Fin_Turno

FROM FechasOperacion

),

Lecturas AS
(
SELECT
p.Fecha,
p.Turno,
p.Inicio_Turno,
p.Fin_Turno,

    ini.cv001_tot AS CV001_Inicio,
    fin.cv001_tot AS CV001_Fin,

    ini.cv002_tot AS CV002_Inicio,
    fin.cv002_tot AS CV002_Fin,

    ini.cv003_tot AS CV003_Inicio,
    fin.cv003_tot AS CV003_Fin

FROM Periodos p

LEFT JOIN DatosHora ini
    ON ini.fecha_inicial = p.Inicio_Turno
   AND ini.rn = 1

LEFT JOIN DatosHora fin
    ON fin.fecha_inicial = p.Fin_Turno
   AND fin.rn = 1

),

Incrementos AS
(
SELECT
*,

    CASE
        WHEN CV001_Inicio IS NULL
          OR CV001_Fin IS NULL
            THEN NULL

        WHEN CV001_Fin < CV001_Inicio
            THEN NULL

        ELSE CV001_Fin - CV001_Inicio
    END AS TMH_CV001,

    CASE
        WHEN CV002_Inicio IS NULL
          OR CV002_Fin IS NULL
            THEN NULL

        WHEN CV002_Fin < CV002_Inicio
            THEN NULL

        ELSE CV002_Fin - CV002_Inicio
    END AS TMH_CV002,

    CASE
        WHEN CV003_Inicio IS NULL
          OR CV003_Fin IS NULL
            THEN NULL

        WHEN CV003_Fin < CV003_Inicio
            THEN NULL

        ELSE CV003_Fin - CV003_Inicio
    END AS TMH_CV003

FROM Lecturas

),

Comparacion AS
(
SELECT
*,

    TMH_CV002 + TMH_CV003
        AS TMH_CV002_003,

    TMH_CV001
    - (TMH_CV002 + TMH_CV003)
        AS Diferencia_TMH,

    CASE
        WHEN TMH_CV001 IS NULL
          OR TMH_CV002 IS NULL
          OR TMH_CV003 IS NULL
            THEN NULL

        WHEN TMH_CV001 = 0
            THEN NULL

        ELSE
            (
                TMH_CV001
                - (TMH_CV002 + TMH_CV003)
            )
            / TMH_CV001
            * 100.0
    END AS Diferencia_Porcentaje,

    CASE
        WHEN TMH_CV001 IS NULL
          OR TMH_CV002 IS NULL
          OR TMH_CV003 IS NULL
            THEN NULL

        WHEN TMH_CV001 = 0
            THEN NULL

        ELSE
            (
                TMH_CV002
                + TMH_CV003
            )
            / TMH_CV001
            * 100.0
    END AS Cierre_CV002_003_Sobre_CV001

FROM Incrementos

)

SELECT
Fecha,
Turno,
Inicio_Turno,
Fin_Turno,

CV001_Inicio,
CV001_Fin,

CV002_Inicio,
CV002_Fin,

CV003_Inicio,
CV003_Fin,

TMH_CV001,
TMH_CV002,
TMH_CV003,
TMH_CV002_003,

Diferencia_TMH,
Diferencia_Porcentaje,
Cierre_CV002_003_Sobre_CV001,

TMH_CV001 AS SRR_TMH_Oficial,

CAST
(
    'CV001_TOTALIZADOR_CORREGIDO'
    AS varchar(40)
) AS Fuente_SRR,

CASE
    WHEN CV001_Inicio IS NULL
      OR CV001_Fin IS NULL
      OR CV002_Inicio IS NULL
      OR CV002_Fin IS NULL
      OR CV003_Inicio IS NULL
      OR CV003_Fin IS NULL
        THEN 'SIN_LECTURA_LIMITE'

    WHEN CV001_Fin < CV001_Inicio
        THEN 'RESETEO_CV001'

    WHEN CV002_Fin < CV002_Inicio
        THEN 'RESETEO_CV002'

    WHEN CV003_Fin < CV003_Inicio
        THEN 'RESETEO_CV003'

    ELSE 'OK'
END AS Flag_Totalizadores,

CASE
    WHEN TMH_CV001 IS NULL
      OR TMH_CV002 IS NULL
      OR TMH_CV003 IS NULL
        THEN 'SIN_DATOS'

    WHEN ABS
    (
        TMH_CV001
        - (TMH_CV002 + TMH_CV003)
    ) <= 0.01
        THEN 'COINCIDE'

    ELSE 'DIFIERE'
END AS Flag_Comparacion

FROM Comparacion;
