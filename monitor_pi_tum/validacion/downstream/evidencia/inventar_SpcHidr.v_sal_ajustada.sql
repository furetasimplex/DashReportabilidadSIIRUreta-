CREATE   VIEW inventar_SpcHidr.v_sal_ajustada AS

WITH sal_marcas AS (
    SELECT DISTINCT
        CAST(fecha_turno AS date) AS Fecha,

        CAST(DATEADD(HOUR, 8, CAST(CAST(fecha_turno AS date) AS datetime2)) AS datetime2)
            AS ts_08_dia,

        CAST(DATEADD(HOUR, 20, CAST(CAST(fecha_turno AS date) AS datetime2)) AS datetime2)
            AS ts_20_dia,

        CAST(DATEADD(HOUR, 8, DATEADD(DAY, 1, CAST(CAST(fecha_turno AS date) AS datetime2))) AS datetime2)
            AS ts_08_dia_siguiente

    FROM inventar_SpcHidr.datos_filtrados
),

sal_base AS (
    SELECT
        m.Fecha,

        CAST(t08.cv201_tot AS float)  AS CV201_08,
        CAST(t20.cv201_tot AS float)  AS CV201_20,
        CAST(t08s.cv201_tot AS float) AS CV201_08_sig,

        CAST(t08.cv202_tot AS float)  AS CV202_08,
        CAST(t20.cv202_tot AS float)  AS CV202_20,
        CAST(t08s.cv202_tot AS float) AS CV202_08_sig

    FROM sal_marcas m

    LEFT JOIN inventar_SpcHidr.datos_filtrados t08
        ON t08.fecha_final = m.ts_08_dia

    LEFT JOIN inventar_SpcHidr.datos_filtrados t20
        ON t20.fecha_final = m.ts_20_dia

    LEFT JOIN inventar_SpcHidr.datos_filtrados t08s
        ON t08s.fecha_final = m.ts_08_dia_siguiente
),

sal_calc AS (
    SELECT
        Fecha,

        (CV201_20 - CV201_08) / 1000.0 AS CV201_TA_Bruto,
        (CV201_08_sig - CV201_20) / 1000.0 AS CV201_TB_Bruto,

        (CV202_20 - CV202_08) / 1000.0 AS CV202_TA_Bruto,
        (CV202_08_sig - CV202_20) / 1000.0 AS CV202_TB_Bruto

    FROM sal_base
),

sal_validacion AS (
    SELECT
        c.*,

        CASE
            WHEN CV201_TA_Bruto IS NULL THEN 0
            WHEN CV201_TB_Bruto IS NULL THEN 0
            WHEN CV202_TA_Bruto IS NULL THEN 0
            WHEN CV202_TB_Bruto IS NULL THEN 0

            WHEN CV201_TA_Bruto < 0 THEN 0
            WHEN CV201_TB_Bruto < 0 THEN 0
            WHEN CV202_TA_Bruto < 0 THEN 0
            WHEN CV202_TB_Bruto < 0 THEN 0

            ELSE 1
        END AS Flag_Sal_Basica_Valida

    FROM sal_calc c
),

sal_total AS (
    SELECT
        Fecha,

        CASE WHEN Flag_Sal_Basica_Valida = 1 THEN CV201_TA_Bruto ELSE 0 END AS CV201_TA,
        CASE WHEN Flag_Sal_Basica_Valida = 1 THEN CV201_TB_Bruto ELSE 0 END AS CV201_TB,
        CASE WHEN Flag_Sal_Basica_Valida = 1 THEN CV202_TA_Bruto ELSE 0 END AS CV202_TA,
        CASE WHEN Flag_Sal_Basica_Valida = 1 THEN CV202_TB_Bruto ELSE 0 END AS CV202_TB,

        Flag_Sal_Basica_Valida

    FROM sal_validacion
),

sal_ajuste_base AS (
    SELECT
        s.Fecha,

        s.CV201_TA,
        s.CV201_TB,
        s.CV202_TA,
        s.CV202_TB,

        s.CV201_TA + s.CV202_TA AS Sal_Pesometros_TA,
        s.CV201_TB + s.CV202_TB AS Sal_Pesometros_TB,

        s.CV201_TA
      + s.CV201_TB
      + s.CV202_TA
      + s.CV202_TB AS Sal_Pesometros_Dia,

        CAST(topo.tonelaje_topografia AS float) AS Sal_Topografia_Dia,

        s.Flag_Sal_Basica_Valida,

        CASE
            WHEN s.Flag_Sal_Basica_Valida = 0 THEN 0
            WHEN topo.tonelaje_topografia IS NULL THEN 0
            WHEN topo.tonelaje_topografia <= 0 THEN 0

            WHEN s.CV201_TA + s.CV202_TA <= 0 THEN 0
            WHEN s.CV201_TB + s.CV202_TB <= 0 THEN 0

            WHEN s.CV201_TA
               + s.CV201_TB
               + s.CV202_TA
               + s.CV202_TB <= 0 THEN 0

            ELSE 1
        END AS Flag_Sal_Ajuste_Valido

    FROM sal_total s

    LEFT JOIN inventar_SpcHidr.topografia_sal topo
        ON topo.fecha = s.Fecha
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

    Flag_Sal_Basica_Valida,
    Flag_Sal_Ajuste_Valido,

    CASE
        WHEN Flag_Sal_Ajuste_Valido = 1 THEN
            Sal_Pesometros_TA
            * Sal_Topografia_Dia
            / NULLIF(Sal_Pesometros_Dia, 0)
        ELSE 0
    END AS Sal_Ajustada_TA,

    CASE
        WHEN Flag_Sal_Ajuste_Valido = 1 THEN
            Sal_Pesometros_TB
            * Sal_Topografia_Dia
            / NULLIF(Sal_Pesometros_Dia, 0)
        ELSE 0
    END AS Sal_Ajustada_TB,

    CASE
        WHEN Flag_Sal_Ajuste_Valido = 1 THEN
            Sal_Topografia_Dia
        ELSE 0
    END AS Sal_Ajustada_Dia

FROM sal_ajuste_base;
