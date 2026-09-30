
CREATE   VIEW
    [inventar_SpcHidr].[v_srr_tag_tmh_turno_test]
AS

/* ============================================================
   SRR TMH DESDE TAG INSTANTÁNEO

   Fuente:
       inventar_SpcHidr.tot_TM.tot_001

   Unidad fuente:
       TMH/h instantáneo

   Salida:
       TMH integrado por Fecha operacional + Turno

   Turnos:
       Ya vienen resueltos en fecha_turno y codigo_turno.

   Regla de integración:
       Toneladas = TPH × segundos / 3600

   La vista no utiliza:
       - Reporte por Turno
       - Caché
       - IMP
       - Factor de ajuste
   ============================================================ */

WITH deduplicado AS
(
    SELECT
        t.id_dato,
        CAST(t.fecha_turno AS date) AS Fecha,
        UPPER(LTRIM(RTRIM(t.codigo_turno))) AS Turno,
        CAST(t.fecha AS datetime2(0)) AS FechaHora,
        TRY_CONVERT(float, t.tot_001) AS SRR_TPH,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                t.fecha_turno,
                UPPER(LTRIM(RTRIM(t.codigo_turno))),
                t.fecha
            ORDER BY
                t.id_dato DESC
        ) AS rn

    FROM [inventar_SpcHidr].[tot_TM] AS t

    WHERE t.fecha_turno IS NOT NULL
      AND UPPER(LTRIM(RTRIM(t.codigo_turno))) IN ('A', 'B')
),
datos AS
(
    SELECT
        Fecha,
        Turno,
        FechaHora,
        SRR_TPH,

        LEAD(FechaHora) OVER
        (
            PARTITION BY Fecha, Turno
            ORDER BY FechaHora
        ) AS FechaHora_Siguiente

    FROM deduplicado
    WHERE rn = 1
),
intervalos AS
(
    SELECT
        Fecha,
        Turno,
        FechaHora,
        SRR_TPH,

        CASE
            /* El último registro representa los últimos 10 segundos */
            WHEN FechaHora_Siguiente IS NULL
                THEN 10

            ELSE DATEDIFF
            (
                SECOND,
                FechaHora,
                FechaHora_Siguiente
            )
        END AS Segundos_Intervalo

    FROM datos
),
resumen AS
(
    SELECT
        Fecha,
        Turno,

        COUNT(*) AS Cantidad_Registros,
        CAST(4320 AS int) AS Cantidad_Registros_Esperados,

        MIN(FechaHora) AS Primera_FechaHora,
        MAX(FechaHora) AS Ultima_FechaHora,

        MIN(SRR_TPH) AS SRR_TPH_Minimo,
        MAX(SRR_TPH) AS SRR_TPH_Maximo,
        AVG(SRR_TPH) AS SRR_TPH_Promedio,

        SUM
        (
            CASE
                WHEN SRR_TPH = 0 THEN 1
                ELSE 0
            END
        ) AS Registros_En_Cero,

        SUM
        (
            CASE
                WHEN SRR_TPH < 0 THEN 1
                ELSE 0
            END
        ) AS Registros_Negativos,

        SUM
        (
            CASE
                WHEN Segundos_Intervalo BETWEEN 1 AND 30
                    THEN Segundos_Intervalo
                ELSE 0
            END
        ) AS Segundos_Integrados,

        MAX(Segundos_Intervalo) AS Brecha_Maxima_Segundos,

        SUM
        (
            CASE
                WHEN Segundos_Intervalo > 30 THEN 1
                ELSE 0
            END
        ) AS Cantidad_Brechas_Mayores_30s,

        /* Resultado diagnóstico, aunque el turno esté incompleto */
        SUM
        (
            CASE
                WHEN SRR_TPH >= 0
                 AND Segundos_Intervalo BETWEEN 1 AND 30
                    THEN SRR_TPH * Segundos_Intervalo / 3600.0
                ELSE 0
            END
        ) AS SRR_TMH_Tag

    FROM intervalos

    GROUP BY
        Fecha,
        Turno
),
evaluacion AS
(
    SELECT
        r.*,

        CAST
        (
            100.0
            * r.Segundos_Integrados
            / 43200.0
            AS decimal(18,2)
        ) AS Cobertura_Pct

    FROM resumen AS r
)

SELECT
    Fecha,
    Turno,

    Cantidad_Registros,
    Cantidad_Registros_Esperados,

    Primera_FechaHora,
    Ultima_FechaHora,

    SRR_TPH_Minimo,
    SRR_TPH_Maximo,
    SRR_TPH_Promedio,

    Registros_En_Cero,
    Registros_Negativos,

    Segundos_Integrados,
    Cobertura_Pct,

    Brecha_Maxima_Segundos,
    Cantidad_Brechas_Mayores_30s,

    CAST(SRR_TMH_Tag AS decimal(18,6))
        AS SRR_TMH_Tag,

    CAST
    (
        CASE
            WHEN Registros_Negativos > 0
                THEN 0

            WHEN Cobertura_Pct < 99.00
                THEN 0

            WHEN Brecha_Maxima_Segundos > 30
                THEN 0

            ELSE 1
        END
        AS bit
    ) AS Flag_SRR_Tag_Valido,

    CAST
    (
        CASE
            WHEN Registros_Negativos > 0
                THEN 'TAG_CON_VALORES_NEGATIVOS'

            WHEN Cobertura_Pct < 99.00
                THEN 'TAG_INCOMPLETO'

            WHEN Brecha_Maxima_Segundos > 30
                THEN 'TAG_CON_BRECHAS'

            ELSE 'OK'
        END
        AS varchar(40)
    ) AS Estado_SRR_Tag

FROM evaluacion;
