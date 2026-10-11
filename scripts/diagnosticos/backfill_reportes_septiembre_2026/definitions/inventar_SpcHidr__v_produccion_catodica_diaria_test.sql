
CREATE   VIEW
    [inventar_SpcHidr].[v_produccion_catodica_diaria_test]
AS

WITH Registros AS
(
    SELECT
        CAST(fecha_registro AS date) AS Fecha,

        id_registro,
        fecha_registro,

        turno_a,
        turno_b,
        real_produccion_ton,
        acumulado_real_ton,
        plan_produccion,

        ROW_NUMBER() OVER
        (
            PARTITION BY CAST(fecha_registro AS date)
            ORDER BY
                fecha_registro DESC,
                id_registro DESC
        ) AS rn

    FROM [inventar_SpcHidr].[produccion_catodica]

    WHERE fecha_registro IS NOT NULL
)

SELECT
    Fecha,

    id_registro,
    fecha_registro AS Fecha_Carga,

    turno_a,
    turno_b,

    real_produccion_ton
        AS Produccion_Catodos_Real,

    acumulado_real_ton,
    plan_produccion,

    CASE
        WHEN real_produccion_ton IS NULL
            THEN 'SIN_PRODUCCION_REAL'

        WHEN real_produccion_ton < 0
            THEN 'PRODUCCION_NEGATIVA'

        ELSE 'OK'
    END AS Flag_Produccion_Catodica

FROM Registros

WHERE rn = 1;
