
CREATE   VIEW
    [inventar_SpcHidr].[v_humedad_inventario_test]
AS

WITH Base AS
(
    SELECT
        CAST(Fecha AS date) AS Fecha,

        TRY_CONVERT(float, Humedad_Turno_A)
            AS Humedad_Turno_A,

        TRY_CONVERT(float, Humedad_Turno_B)
            AS Humedad_Turno_B,

        TRY_CONVERT(float, Humedad_promedio_dia)
            AS Humedad_Promedio_Dia,

        TRY_CONVERT(float, Humedad_TM1)
            AS Humedad_TM1,

        Fecha_Humedad_TM1,
        Torre_Humedad_TM1,
        Turno_Humedad_TM1,
        Fuente_Humedad_TM1,

        TRY_CONVERT(float, Humedad_TM2)
            AS Humedad_TM2,

        Fecha_Humedad_TM2,
        Torre_Humedad_TM2,
        Turno_Humedad_TM2,
        Fuente_Humedad_TM2

    FROM [inventar_SpcHidr].[v_reporte_diario_humedad_test]
),

Resolucion AS
(
    SELECT
        b.*,

        CASE
            /*
              Caso normal:
              existe apilado y la vista ya calculó una humedad
              diaria ponderada por el tonelaje de los turnos.
            */
            WHEN b.Humedad_Promedio_Dia > 0
                THEN b.Humedad_Promedio_Dia

            /*
              Sin apilado:
              ambos turnos mantienen la misma humedad vigente.
            */
            WHEN b.Humedad_Turno_A > 0
             AND b.Humedad_Turno_B > 0
             AND ABS(
                    b.Humedad_Turno_A
                    - b.Humedad_Turno_B
                 ) <= 0.000001
                THEN
                    (
                        b.Humedad_Turno_A
                        + b.Humedad_Turno_B
                    ) / 2.0

            /*
              Solo existe humedad vigente en el turno A.
            */
            WHEN b.Humedad_Turno_A > 0
             AND
             (
                    b.Humedad_Turno_B IS NULL
                 OR b.Humedad_Turno_B <= 0
             )
                THEN b.Humedad_Turno_A

            /*
              Solo existe humedad vigente en el turno B.
            */
            WHEN b.Humedad_Turno_B > 0
             AND
             (
                    b.Humedad_Turno_A IS NULL
                 OR b.Humedad_Turno_A <= 0
             )
                THEN b.Humedad_Turno_B

            /*
              Respaldo: ambas torres mantienen la misma humedad
              ya resuelta mediante representatividad y arrastre.
            */
            WHEN b.Humedad_TM1 > 0
             AND b.Humedad_TM2 > 0
             AND ABS(
                    b.Humedad_TM1
                    - b.Humedad_TM2
                 ) <= 0.000001
                THEN
                    (
                        b.Humedad_TM1
                        + b.Humedad_TM2
                    ) / 2.0

            /*
              Solo TM1 tiene una humedad operacional resuelta.
            */
            WHEN b.Humedad_TM1 > 0
             AND
             (
                    b.Humedad_TM2 IS NULL
                 OR b.Humedad_TM2 <= 0
             )
                THEN b.Humedad_TM1

            /*
              Solo TM2 tiene una humedad operacional resuelta.
            */
            WHEN b.Humedad_TM2 > 0
             AND
             (
                    b.Humedad_TM1 IS NULL
                 OR b.Humedad_TM1 <= 0
             )
                THEN b.Humedad_TM2

            /*
              Si existen valores diferentes sin una humedad
              diaria ponderada, no se inventa un promedio.
            */
            ELSE NULL
        END AS Humedad_Inventario,

        CASE
            WHEN b.Humedad_Promedio_Dia > 0
                THEN 'HUMEDAD_DIARIA_PONDERADA'

            WHEN b.Humedad_Turno_A > 0
             AND b.Humedad_Turno_B > 0
             AND ABS(
                    b.Humedad_Turno_A
                    - b.Humedad_Turno_B
                 ) <= 0.000001
                THEN 'HUMEDAD_RESUELTA_SIN_APILADO'

            WHEN b.Humedad_Turno_A > 0
             AND
             (
                    b.Humedad_Turno_B IS NULL
                 OR b.Humedad_Turno_B <= 0
             )
                THEN 'HUMEDAD_RESUELTA_TURNO_A'

            WHEN b.Humedad_Turno_B > 0
             AND
             (
                    b.Humedad_Turno_A IS NULL
                 OR b.Humedad_Turno_A <= 0
             )
                THEN 'HUMEDAD_RESUELTA_TURNO_B'

            WHEN b.Humedad_TM1 > 0
             AND b.Humedad_TM2 > 0
             AND ABS(
                    b.Humedad_TM1
                    - b.Humedad_TM2
                 ) <= 0.000001
                THEN 'HUMEDAD_RESUELTA_TORRES'

            WHEN b.Humedad_TM1 > 0
             AND
             (
                    b.Humedad_TM2 IS NULL
                 OR b.Humedad_TM2 <= 0
             )
                THEN 'HUMEDAD_RESUELTA_TM1'

            WHEN b.Humedad_TM2 > 0
             AND
             (
                    b.Humedad_TM1 IS NULL
                 OR b.Humedad_TM1 <= 0
             )
                THEN 'HUMEDAD_RESUELTA_TM2'

            ELSE 'PENDIENTE_REGLA_CONFLICTO_HUMEDAD'
        END AS Regla_Humedad_Inventario

    FROM Base AS b
)

SELECT
    Fecha,

    Humedad_Inventario,
    Regla_Humedad_Inventario,

    CASE
        WHEN Humedad_Inventario IS NOT NULL
         AND Humedad_Inventario > 0
            THEN 1
        ELSE 0
    END AS Flag_Humedad_Inventario_Valida,

    /* Valores utilizados para auditoría */
    Humedad_Turno_A,
    Humedad_Turno_B,
    Humedad_Promedio_Dia,

    Humedad_TM1,
    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,

    Humedad_TM2,
    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2

FROM Resolucion;
