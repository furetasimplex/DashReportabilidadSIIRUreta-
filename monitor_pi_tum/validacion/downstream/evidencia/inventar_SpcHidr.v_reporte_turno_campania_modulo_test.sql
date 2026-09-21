CREATE   VIEW inventar_SpcHidr.v_reporte_turno_campania_modulo_test
AS
WITH fechas_reporte AS
(
    SELECT DISTINCT
        Fecha
    FROM inventar_SpcHidr.v_reporte_turno_reales_test
    WHERE Fecha IS NOT NULL
),

base_topografia AS
(
    SELECT
        CAST(fecha AS date) AS Fecha,
        CAST(fecha AS date) AS Fecha_Topografia,
        [campaña],
        modulo,
        pad_id,
        volumen_diario_m3,
        avance_porcentaje,
        CASE
            WHEN pad_id = 1 THEN 'OXIDOS'
            WHEN pad_id = 2 THEN 'SULFUROS'
            ELSE 'SIN_PAD'
        END AS Material
    FROM inventar_SpcHidr.control_apilado_diario
    WHERE fecha IS NOT NULL
      AND volumen_diario_m3 > 0
),

rankeado AS
(
    SELECT
        *,
        ROW_NUMBER() OVER
        (
            PARTITION BY Fecha
            ORDER BY
                avance_porcentaje ASC,
                volumen_diario_m3 DESC,
                modulo ASC
        ) AS rn
    FROM base_topografia
),

modulo_dia AS
(
    SELECT
        Fecha,
        Fecha_Topografia AS Fecha_Topografia_Usada,
        CAST([campaña] AS varchar(100)) AS Campania,
        Material,
        CAST(modulo AS varchar(100)) AS Modulo,
        avance_porcentaje AS Avance,
        volumen_diario_m3 AS Volumen_Diario_Modulo_m3
    FROM rankeado
    WHERE rn = 1
),

base_reporte AS
(
    SELECT
        f.Fecha,
        md.Fecha_Topografia_Usada,
        md.Campania,
        md.Material,
        md.Modulo,
        md.Avance,
        md.Volumen_Diario_Modulo_m3
    FROM fechas_reporte f
    LEFT JOIN modulo_dia md
        ON md.Fecha = f.Fecha
),

relleno AS
(
    SELECT
        br.Fecha,

        ult.Fecha AS Fecha_Origen_Relleno,
        ult.Fecha_Topografia_Usada,
        ult.Campania,
        ult.Material,
        ult.Modulo,
        ult.Avance,
        ult.Volumen_Diario_Modulo_m3,

        CASE
            WHEN br.Campania IS NOT NULL
                THEN 'VALOR_DIA'

            WHEN ult.Campania IS NOT NULL
                THEN 'ARRASTRE_ULTIMO_VALIDO'

            ELSE 'SIN_DATO'
        END AS Fuente_Campania_Modulo

    FROM base_reporte br

    OUTER APPLY
    (
        SELECT TOP 1
            md.Fecha,
            md.Fecha_Topografia_Usada,
            md.Campania,
            md.Material,
            md.Modulo,
            md.Avance,
            md.Volumen_Diario_Modulo_m3
        FROM modulo_dia md
        WHERE md.Fecha <= br.Fecha
        ORDER BY md.Fecha DESC
    ) ult
)

SELECT
    Fecha,
    Fecha_Origen_Relleno,
    Fecha_Topografia_Usada,
    Campania,
    Material,
    Modulo,
    Avance,
    Volumen_Diario_Modulo_m3,
    Fuente_Campania_Modulo
FROM relleno;