CREATE PROCEDURE [inventar_SpcHidr].[sp_reporte_turno_emision_test]
    @fecha_inicio date,
    @fecha_fin    date
AS
BEGIN
    SET NOCOUNT ON;

    /* ============================================================
       LIMPIEZA TEMPORALES
       ============================================================ */

    DROP TABLE IF EXISTS #fechas;
    DROP TABLE IF EXISTS #hum;
    DROP TABLE IF EXISTS #hum_rep;
    DROP TABLE IF EXISTS #hum_torre_dia;
    DROP TABLE IF EXISTS #hum_torre_dia_final;
    DROP TABLE IF EXISTS #candidatos;
    DROP TABLE IF EXISTS #humedad_resuelta;
    DROP TABLE IF EXISTS #fes_candidatos_dia;
    DROP TABLE IF EXISTS #fes_dia_resuelta;

 /* ============================================================
   BLOQUE 1: TMH BASE DESDE APILADO
   Depuración anti-spike por correa/turno
   ============================================================ */

DECLARE @umbral_tmh_spike_turno decimal(18,6) = 150000.0;

WITH tmh_raw AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        CAST(ISNULL(TMH_CV008_A, 0) AS decimal(18,6)) AS TMH_CV008_A_Raw,
        CAST(ISNULL(TMH_CV008_B, 0) AS decimal(18,6)) AS TMH_CV008_B_Raw,
        CAST(ISNULL(TMH_CV108_A, 0) AS decimal(18,6)) AS TMH_CV108_A_Raw,
        CAST(ISNULL(TMH_CV108_B, 0) AS decimal(18,6)) AS TMH_CV108_B_Raw
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2
    WHERE Fecha >= @fecha_inicio
      AND Fecha <  @fecha_fin
),
tmh_limpia AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        CASE
            WHEN ABS(TMH_CV008_A_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV008_A_Raw
        END AS TMH_CV008_A,

        CASE
            WHEN ABS(TMH_CV008_B_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV008_B_Raw
        END AS TMH_CV008_B,

        CASE
            WHEN ABS(TMH_CV108_A_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV108_A_Raw
        END AS TMH_CV108_A,

        CASE
            WHEN ABS(TMH_CV108_B_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV108_B_Raw
        END AS TMH_CV108_B
    FROM tmh_raw
)
SELECT
    Fecha,
    Flag_Apilado_Valido,

    TMH_CV008_A,
    TMH_CV008_B,
    TMH_CV108_A,
    TMH_CV108_B,

    TMH_CV008_A + TMH_CV108_A AS TMH_Apilado_Total_A,
    TMH_CV008_B + TMH_CV108_B AS TMH_Apilado_Total_B,
    TMH_CV008_A + TMH_CV108_A + TMH_CV008_B + TMH_CV108_B AS TMH_Apilado_Total_Dia

INTO #fechas
FROM tmh_limpia;

/* ============================================================
   BLOQUE 2: HUMEDAD LABORATORIO
   Optimizado con ventana histórica razonable
   ============================================================ */

DECLARE @fecha_inicio_humedad date = DATEADD(DAY, -90, @fecha_inicio);

SELECT
    CAST(Fecha AS date) AS Fecha,
    Torre,
    Turno,
    AVG(CAST(Humedad_Prom_Pct AS float)) AS Humedad_Prom_Pct
INTO #hum
FROM inventar_SpcHidr.Informe_TM_lab
WHERE Humedad_Prom_Pct IS NOT NULL
  AND Fecha >= @fecha_inicio_humedad
  AND Fecha <  @fecha_fin
GROUP BY
    CAST(Fecha AS date),
    Torre,
    Turno;

CREATE CLUSTERED INDEX IX_hum
ON #hum (Fecha, Torre, Turno);

/* ============================================================
   BLOQUE 3: HUMEDAD + REPRESENTATIVIDAD FÍSICA
   Optimizado: usa resultado materializado
   ============================================================ */

SELECT
    h.Fecha,
    h.Torre,
    h.Turno,
    h.Humedad_Prom_Pct,
    CASE
        WHEN h.Torre = 'T1' AND h.Turno = 'A' THEN r.TM1_TurnoA_Fisico
        WHEN h.Torre = 'T1' AND h.Turno = 'B' THEN r.TM1_TurnoB_Fisico
        WHEN h.Torre = 'T2' AND h.Turno = 'A' THEN r.TM2_TurnoA_Fisico
        WHEN h.Torre = 'T2' AND h.Turno = 'B' THEN r.TM2_TurnoB_Fisico
    END AS Representatividad_Fisica
INTO #hum_rep
FROM #hum h
LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado r
    ON r.Dia = h.Fecha;

CREATE CLUSTERED INDEX IX_hum_rep
ON #hum_rep (Fecha, Torre, Turno);

  /* ============================================================
   BLOQUE 4: HUMEDADES REPRESENTATIVAS POR FECHA + TURNO

   Corrección:
   - No se reduce A/B a una sola humedad diaria.
   - Se conserva el orden cronológico A -> B.
   - Cada TM prioriza su humedad propia.
   - Cuando no existe humedad propia más reciente, utiliza
     la humedad representativa vigente de la otra torre.
   ============================================================ */

SELECT
    Fecha,
    Torre,
    Turno AS Turno_Humedad,
    Humedad_Prom_Pct AS Humedad_Torre_Dia,
    Representatividad_Fisica,

    DATEADD
    (
        HOUR,
        CASE
            WHEN Turno = 'A' THEN 8
            ELSE 20
        END,
        CAST(Fecha AS datetime2(0))
    ) AS FechaTurno_Origen

INTO #candidatos

FROM #hum_rep

WHERE Humedad_Prom_Pct IS NOT NULL
  AND Representatividad_Fisica >= 0.75;


CREATE CLUSTERED INDEX IX_candidatos
ON #candidatos
(
    FechaTurno_Origen DESC,
    Torre
);


/* ============================================================
   BLOQUE 5: RESOLUCIÓN CRONOLÓGICA POR FECHA + TURNO
   ============================================================ */

;WITH periodos AS
(
    SELECT
        f.Fecha,
        t.Turno_Objetivo,

        DATEADD
        (
            HOUR,
            CASE
                WHEN t.Turno_Objetivo = 'A' THEN 8
                ELSE 20
            END,
            CAST(f.Fecha AS datetime2(0))
        ) AS FechaTurno_Objetivo

    FROM #fechas AS f

    CROSS JOIN
    (
        VALUES
            ('A'),
            ('B')
    ) AS t(Turno_Objetivo)
),

resuelta_turno AS
(
    SELECT
        p.Fecha,
        p.Turno_Objetivo,

        /* ====================================================
           TM1
           ==================================================== */

        tm1.Humedad_Torre_Dia
            AS Humedad_TM1,

        tm1.Fecha
            AS Fecha_Origen_TM1,

        tm1.Torre
            AS Torre_Origen_TM1,

        tm1.Turno_Humedad
            AS Turno_Origen_TM1,

        tm1.Fuente_Humedad
            AS Fuente_Humedad_TM1,

        /* ====================================================
           TM2
           ==================================================== */

        tm2.Humedad_Torre_Dia
            AS Humedad_TM2,

        tm2.Fecha
            AS Fecha_Origen_TM2,

        tm2.Torre
            AS Torre_Origen_TM2,

        tm2.Turno_Humedad
            AS Turno_Origen_TM2,

        tm2.Fuente_Humedad
            AS Fuente_Humedad_TM2

    FROM periodos AS p

    /* --------------------------------------------------------
       Resolución TM1
       -------------------------------------------------------- */

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno_Humedad,
            c.Humedad_Torre_Dia,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno_Humedad,
                h.Humedad_Torre_Dia,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T1'
                            THEN 'PROPIA_TM1'
                        ELSE 'COMPARTIDA_DESDE_TM2'
                    END
                    AS varchar(23)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T1' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM #candidatos AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(10)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'HUMEDAD_INICIAL_PERIODO'
                    AS varchar(23)
                ),

                3

            FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s

            WHERE s.tm = 'TM1'
              AND CAST(s.fecha_origen AS datetime2(0))
                    <= p.FechaTurno_Objetivo
        ) AS c

        ORDER BY
            c.FechaTurno_Origen DESC,
            c.Prioridad ASC

    ) AS tm1

    /* --------------------------------------------------------
       Resolución TM2
       -------------------------------------------------------- */

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno_Humedad,
            c.Humedad_Torre_Dia,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno_Humedad,
                h.Humedad_Torre_Dia,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T2'
                            THEN 'PROPIA_TM2'
                        ELSE 'COMPARTIDA_DESDE_TM1'
                    END
                    AS varchar(23)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T2' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM #candidatos AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(10)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'HUMEDAD_INICIAL_PERIODO'
                    AS varchar(23)
                ),

                3

            FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s

            WHERE s.tm = 'TM2'
              AND CAST(s.fecha_origen AS datetime2(0))
                    <= p.FechaTurno_Objetivo
        ) AS c

        ORDER BY
            c.FechaTurno_Origen DESC,
            c.Prioridad ASC

    ) AS tm2
),

/* ============================================================
   BLOQUE 6: PIVOT A/B Y HUMEDAD RESUELTA POR FECHA

   Las columnas Humedad_TM1 y Humedad_TM2 se mantienen para
   compatibilidad y representan el valor vigente al cierre del día.
   ============================================================ */

humedad_resuelta_cte AS
(
    SELECT
        f.*,

        /* Humedades efectivas por turno */

        a.Humedad_TM1 AS Humedad_TM1_A,
        b.Humedad_TM1 AS Humedad_TM1_B,

        a.Humedad_TM2 AS Humedad_TM2_A,
        b.Humedad_TM2 AS Humedad_TM2_B,

        /* Humedad vigente al cierre diario */

        COALESCE
        (
            b.Humedad_TM1,
            a.Humedad_TM1
        ) AS Humedad_TM1,

        COALESCE
        (
            b.Humedad_TM2,
            a.Humedad_TM2
        ) AS Humedad_TM2,

        /* Trazabilidad TM1 */

        COALESCE
        (
            b.Fecha_Origen_TM1,
            a.Fecha_Origen_TM1
        ) AS Fecha_Humedad_TM1,

        COALESCE
        (
            b.Torre_Origen_TM1,
            a.Torre_Origen_TM1
        ) AS Torre_Humedad_TM1,

        COALESCE
        (
            b.Turno_Origen_TM1,
            a.Turno_Origen_TM1
        ) AS Turno_Humedad_TM1,

        COALESCE
        (
            b.Fuente_Humedad_TM1,
            a.Fuente_Humedad_TM1
        ) AS Fuente_Humedad_TM1,

        /* Trazabilidad TM2 */

        COALESCE
        (
            b.Fecha_Origen_TM2,
            a.Fecha_Origen_TM2
        ) AS Fecha_Humedad_TM2,

        COALESCE
        (
            b.Torre_Origen_TM2,
            a.Torre_Origen_TM2
        ) AS Torre_Humedad_TM2,

        COALESCE
        (
            b.Turno_Origen_TM2,
            a.Turno_Origen_TM2
        ) AS Turno_Humedad_TM2,

        COALESCE
        (
            b.Fuente_Humedad_TM2,
            a.Fuente_Humedad_TM2
        ) AS Fuente_Humedad_TM2

    FROM #fechas AS f

    LEFT JOIN resuelta_turno AS a
        ON a.Fecha = f.Fecha
       AND a.Turno_Objetivo = 'A'

    LEFT JOIN resuelta_turno AS b
        ON b.Fecha = f.Fecha
       AND b.Turno_Objetivo = 'B'
)

SELECT *
INTO #humedad_resuelta
FROM humedad_resuelta_cte;


CREATE CLUSTERED INDEX IX_humedad_resuelta
ON #humedad_resuelta (Fecha);
    /* ============================================================
   BLOQUE 7: FACTOR DE AJUSTE CAMIONES V2 + CÁLCULO TMS

   Fuente única de emisión:
       inventar_SpcHidr.v_ajuste_camiones_emision_test

   Regla:
   - Factor válido: aplica el factor diario a CV008/CV108 por turno.
   - Factor no evaluable: Factor_Aplicacion_Reportes = 1 (fallback),
     conservando por separado el estado real del cálculo.
   - El TMS se calcula DESDE LOS TMH AJUSTADOS.
   - Los bloques posteriores de sal, leyes, ponderaciones, IMP y
     clasificación permanecen sin cambios.
   ============================================================ */
DROP TABLE IF EXISTS #base_tms;
DROP TABLE IF EXISTS #tms_con_sal;

SELECT
    h.*,

    fac.Factor_Ajuste_Calculado,
    fac.Flag_Factor_Ajuste_Valido,
    fac.Flag_Usa_Ajuste,
    fac.Estado_Calculo AS Estado_Factor_Ajuste_Camiones,
    fac.Regla_Aplicacion AS Regla_Factor_Ajuste_Camiones,

    COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS Factor_Ajuste_Camiones_Usado,

    /* TMH ajustado por torre y turno */
    h.TMH_CV008_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV008_A_Factor,

    h.TMH_CV008_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV008_B_Factor,

    h.TMH_CV108_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV108_A_Factor,

    h.TMH_CV108_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV108_B_Factor,

    /* Totales ajustados */
    h.TMH_Apilado_Total_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_A_Factor,

    h.TMH_Apilado_Total_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_B_Factor,

    h.TMH_Apilado_Total_Dia
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_Dia_Factor

INTO #base_tms
FROM #humedad_resuelta AS h
LEFT JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test AS fac
    ON fac.Fecha = h.Fecha;

CREATE CLUSTERED INDEX IX_base_tms
    ON #base_tms (Fecha);

SELECT
    x.*,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A
           + x.TMS_TM2_Con_Sal_SRR_A
    END AS TMS_Total_Con_Sal_SRR_A,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_B
           + x.TMS_TM2_Con_Sal_SRR_B
    END AS TMS_Total_Con_Sal_SRR_B,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A
           + x.TMS_TM1_Con_Sal_SRR_B
           + x.TMS_TM2_Con_Sal_SRR_A
           + x.TMS_TM2_Con_Sal_SRR_B
    END AS TMS_Total_Con_Sal_SRR_Dia

INTO #tms_con_sal
FROM
(
    SELECT
        b.*,

        CASE
            WHEN b.TMH_CV008_A_Factor = 0 THEN 0
            WHEN b.Humedad_TM1_A IS NULL THEN NULL
            ELSE b.TMH_CV008_A_Factor
                 * (1.0 - b.Humedad_TM1_A / 100.0)
        END AS TMS_TM1_Con_Sal_SRR_A,

        CASE
            WHEN b.TMH_CV008_B_Factor = 0 THEN 0
            WHEN b.Humedad_TM1_B IS NULL THEN NULL
            ELSE b.TMH_CV008_B_Factor
                 * (1.0 - b.Humedad_TM1_B / 100.0)
        END AS TMS_TM1_Con_Sal_SRR_B,

        CASE
            WHEN b.TMH_CV108_A_Factor = 0 THEN 0
            WHEN b.Humedad_TM2_A IS NULL THEN NULL
            ELSE b.TMH_CV108_A_Factor
                 * (1.0 - b.Humedad_TM2_A / 100.0)
        END AS TMS_TM2_Con_Sal_SRR_A,

        CASE
            WHEN b.TMH_CV108_B_Factor = 0 THEN 0
            WHEN b.Humedad_TM2_B IS NULL THEN NULL
            ELSE b.TMH_CV108_B_Factor
                 * (1.0 - b.Humedad_TM2_B / 100.0)
        END AS TMS_TM2_Con_Sal_SRR_B,

        CASE
            WHEN b.TMH_Apilado_Total_Dia_Factor = 0
                THEN 0

            WHEN b.TMH_CV008_A_Factor > 0
             AND b.Humedad_TM1_A IS NULL
                THEN NULL

            WHEN b.TMH_CV008_B_Factor > 0
             AND b.Humedad_TM1_B IS NULL
                THEN NULL

            WHEN b.TMH_CV108_A_Factor > 0
             AND b.Humedad_TM2_A IS NULL
                THEN NULL

            WHEN b.TMH_CV108_B_Factor > 0
             AND b.Humedad_TM2_B IS NULL
                THEN NULL

            ELSE
                (
                    b.TMH_CV008_A_Factor * b.Humedad_TM1_A
                  + b.TMH_CV008_B_Factor * b.Humedad_TM1_B
                  + b.TMH_CV108_A_Factor * b.Humedad_TM2_A
                  + b.TMH_CV108_B_Factor * b.Humedad_TM2_B
                )
                /
                NULLIF(b.TMH_Apilado_Total_Dia_Factor, 0)
        END AS Humedad_Equivalente_Dia

    FROM #base_tms AS b
) AS x;

CREATE CLUSTERED INDEX IX_tms_con_sal
    ON #tms_con_sal (Fecha);

/* ============================================================
   BLOQUE 8: SAL AJUSTADA + DESCUENTO DE SAL
   ============================================================ */

DROP TABLE IF EXISTS #sal_ajustada;
DROP TABLE IF EXISTS #tms_sin_sal;

SELECT
    v.Fecha,
    v.Sal_Pesometros_TA,
    v.Sal_Pesometros_TB,
    v.Sal_Pesometros_Dia,
    v.Sal_Topografia_Dia,
    v.Flag_Sal_Basica_Valida,
    v.Flag_Sal_Ajuste_Valido,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia
               * ISNULL(v.Sal_Pesometros_TA, 0)
               / NULLIF(v.Sal_Pesometros_Dia, 0)

        ELSE ISNULL(v.Sal_Ajustada_TA, 0)
    END AS Sal_Ajustada_TA,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia
               * ISNULL(v.Sal_Pesometros_TB, 0)
               / NULLIF(v.Sal_Pesometros_Dia, 0)

        ELSE ISNULL(v.Sal_Ajustada_TB, 0)
    END AS Sal_Ajustada_TB,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia

        ELSE ISNULL(v.Sal_Ajustada_Dia, 0)
    END AS Sal_Ajustada_Dia

INTO #sal_ajustada
FROM inventar_SpcHidr.v_sal_ajustada v
WHERE v.Fecha >= @fecha_inicio
  AND v.Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_sal_ajustada
ON #sal_ajustada (Fecha);


SELECT
    t.*,

    s.Sal_Pesometros_TA,
    s.Sal_Pesometros_TB,
    s.Sal_Pesometros_Dia,
    s.Sal_Topografia_Dia,

    s.Flag_Sal_Basica_Valida,
    s.Flag_Sal_Ajuste_Valido,

    s.Sal_Ajustada_TA,
    s.Sal_Ajustada_TB,
    s.Sal_Ajustada_Dia,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_A = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TA, 0)
             * t.TMS_TM1_Con_Sal_SRR_A
             / NULLIF(t.TMS_Total_Con_Sal_SRR_A, 0)
    END AS Sal_Asignada_TM1_A,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_A = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TA, 0)
             * t.TMS_TM2_Con_Sal_SRR_A
             / NULLIF(t.TMS_Total_Con_Sal_SRR_A, 0)
    END AS Sal_Asignada_TM2_A,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_B = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TB, 0)
             * t.TMS_TM1_Con_Sal_SRR_B
             / NULLIF(t.TMS_Total_Con_Sal_SRR_B, 0)
    END AS Sal_Asignada_TM1_B,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_B = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TB, 0)
             * t.TMS_TM2_Con_Sal_SRR_B
             / NULLIF(t.TMS_Total_Con_Sal_SRR_B, 0)
    END AS Sal_Asignada_TM2_B

INTO #tms_sin_sal
FROM #tms_con_sal t
LEFT JOIN #sal_ajustada s
    ON s.Fecha = t.Fecha;

CREATE CLUSTERED INDEX IX_tms_sin_sal
ON #tms_sin_sal (Fecha);
/* ============================================================
   BLOQUE 9: TMS SIN SAL EN FORMATO FECHA / TURNO / TM
   ============================================================ */

DROP TABLE IF EXISTS #tms_tm;

SELECT
    Fecha,
    Turno,
    TM,
    TMS
INTO #tms_tm
FROM (
    SELECT
        Fecha,
        'A' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Con_Sal_SRR_A - COALESCE(Sal_Asignada_TM1_A, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'A' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Con_Sal_SRR_A - COALESCE(Sal_Asignada_TM2_A, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Con_Sal_SRR_B - COALESCE(Sal_Asignada_TM1_B, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Con_Sal_SRR_B - COALESCE(Sal_Asignada_TM2_B, 0) AS TMS
    FROM #tms_sin_sal
) x;

CREATE CLUSTERED INDEX IX_tms_tm
ON #tms_tm (Fecha, Turno, TM);
/* ============================================================
   BLOQUE 10: LEYES BASE RESUELTAS POR FECHA / TURNO / TM
   ============================================================ */

DROP TABLE IF EXISTS #leyes_base;

DECLARE @fecha_inicio_leyes_arrastre date =
    DATEADD(DAY, -90, @fecha_inicio);

SELECT *
INTO #leyes_base
FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
WHERE Fecha >= @fecha_inicio_leyes_arrastre
  AND Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_leyes_base_fecha_turno_tm
ON #leyes_base (Fecha, Turno, TM);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_fes
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (FeS, Fuente_FeS);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_consh
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (ConsH, Fuente_ConsH);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_malla12
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (Malla_Menos_1_2, Fuente_Malla_Menos_1_2);
/* ============================================================
   BLOQUE 10A: RESOLUCIÓN CRONOLÓGICA DE FeS

   RN-067:
   - El orden operacional es Fecha + Turno A + Turno B.
   - El turno A puede completar el turno B.
   - El turno B no puede modificar retroactivamente el turno A.
   - El valor nuevo del turno B rige desde B hacia adelante.
   - TM2 puede completar TM1.
   - TM1 no puede completar TM2.
   ============================================================ */

DROP TABLE IF EXISTS #fes_candidatos_dia;
DROP TABLE IF EXISTS #fes_dia_resuelta;

/* ------------------------------------------------------------
   Eventos originales válidos de FeS.

   TORRE_OTRO_TURNO_MISMO_DIA no se considera evento original,
   porque puede contener una compartición bidireccional previa.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,
    b.FeS,
    b.Fuente_FeS AS Fuente_Origen

INTO #fes_candidatos_dia

FROM #leyes_base AS b

WHERE b.FeS IS NOT NULL
  AND b.Fuente_FeS IN
  (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );

CREATE CLUSTERED INDEX IX_fes_candidatos_dia
ON #fes_candidatos_dia
(
    Fecha,
    Turno_Origen,
    TM_Origen
);

/* ------------------------------------------------------------
   Resolver cada Fecha + Turno + TM utilizando únicamente
   información cronológicamente disponible.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    c.FeS AS FeS_Nuevo_Dia,
    c.TM_Origen,
    c.Turno_Origen,

    CASE
        WHEN c.FeS IS NULL
            THEN NULL

        WHEN c.Fecha_Origen < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        /* Misma TM y mismo turno */
        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA'

        /* A completa B en la misma TM */
        WHEN c.TM_Origen = b.TM
         AND b.Turno = 'B'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_QUIMICA_OTRO_TURNO'

        /* TM2 completa TM1 en el mismo turno */
        WHEN b.TM = 'TM1'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1'

        /* TM2-A completa TM1-B */
        WHEN b.TM = 'TM1'
         AND b.Turno = 'B'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = 'A'
            THEN
                'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1_OTRO_TURNO'

        ELSE NULL
    END AS Fuente_Nuevo_Dia

INTO #fes_dia_resuelta

FROM #leyes_base AS b

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha AS Fecha_Origen,
        x.Turno_Origen,
        x.TM_Origen,
        x.FeS,
        x.Fuente_Origen

    FROM #fes_candidatos_dia AS x

    WHERE
        /* Misma TM o compartición permitida TM2 → TM1 */
        (
            x.TM_Origen = b.TM

            OR
            (
                b.TM = 'TM1'
                AND x.TM_Origen = 'TM2'
            )
        )

        /* Restricción cronológica */
        AND
        (
            x.Fecha < b.Fecha

            OR
            (
                x.Fecha = b.Fecha

                AND
                CASE
                    WHEN x.Turno_Origen = 'A' THEN 1
                    WHEN x.Turno_Origen = 'B' THEN 2
                    ELSE 9
                END
                <=
                CASE
                    WHEN b.Turno = 'A' THEN 1
                    WHEN b.Turno = 'B' THEN 2
                    ELSE 9
                END
            )
        )

    ORDER BY
        x.Fecha DESC,

        /* B es posterior a A */
        CASE
            WHEN x.Turno_Origen = 'B' THEN 2
            WHEN x.Turno_Origen = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igualdad temporal, priorizar la propia TM */
        CASE
            WHEN x.TM_Origen = b.TM THEN 1

            WHEN b.TM = 'TM1'
             AND x.TM_Origen = 'TM2' THEN 2

            ELSE 9
        END,

        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 9
        END

) AS c;

CREATE CLUSTERED INDEX IX_fes_dia_resuelta
ON #fes_dia_resuelta
(
    TM,
    Turno,
    Fecha
);
/* ============================================================
   BLOQUE 11A: RESOLUCIÓN CRONOLÓGICA MALLA -1/2

   Regla:
   - El orden operacional es Fecha + turno A + turno B.
   - Una medición válida del turno A puede completar B.
   - Una medición del turno B no puede modificar A.
   - El valor nuevo del turno B rige desde B hacia adelante.
   - TM2 puede completar TM1.
   - TM1 no completa TM2.
   - Se excluyen comparticiones bidireccionales previamente
     generadas por TORRE_OTRO_TURNO_MISMO_DIA.
   ============================================================ */

DROP TABLE IF EXISTS #malla12_candidata_dia_tm;
DROP TABLE IF EXISTS #malla12_dia_resuelta;

/* ------------------------------------------------------------
   Eventos originales válidos
   ------------------------------------------------------------ */

SELECT
    b.Fecha AS Fecha_Origen,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,

    b.Malla_Menos_1_2,
    b.Fuente_Malla_Menos_1_2 AS Fuente_Origen

INTO #malla12_candidata_dia_tm

FROM #leyes_base AS b

WHERE b.Malla_Menos_1_2 IS NOT NULL
  AND b.Malla_Menos_1_2 <> 0
  AND b.Fuente_Malla_Menos_1_2 IN
  (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );


CREATE CLUSTERED INDEX IX_malla12_candidata_fecha_turno_tm
ON #malla12_candidata_dia_tm
(
    Fecha_Origen,
    Turno_Origen,
    TM_Origen
);


/* ------------------------------------------------------------
   Resolver cada Fecha + Turno + TM utilizando solamente
   información disponible hasta ese instante.
   ------------------------------------------------------------ */

;WITH base AS
(
    SELECT DISTINCT
        Fecha,
        Turno,
        TM
    FROM #leyes_base
)

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    c.Fecha_Origen,
    c.Turno_Origen,
    c.TM_Origen,

    c.Malla_Menos_1_2,
    c.Fuente_Origen,

    CASE
        WHEN c.Malla_Menos_1_2 IS NULL
            THEN NULL

        /* El dato proviene de una fecha anterior */
        WHEN c.Fecha_Origen < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        /* Misma TM y mismo turno */
        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_FISICA'

        /* El turno A completa B en la misma TM */
        WHEN c.TM_Origen = b.TM
         AND b.Turno = 'B'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_FISICA_OTRO_TURNO'

        /* TM2 completa TM1 en el mismo turno */
        WHEN b.TM = 'TM1'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_FISICA_COMPARTIDA'

        /* TM2-A completa TM1-B */
        WHEN b.TM = 'TM1'
         AND b.Turno = 'B'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_FISICA_COMPARTIDA_OTRO_TURNO'

        ELSE NULL
    END AS Fuente_Malla_Resuelta

INTO #malla12_dia_resuelta

FROM base AS b

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha_Origen,
        x.Turno_Origen,
        x.TM_Origen,
        x.Malla_Menos_1_2,
        x.Fuente_Origen

    FROM #malla12_candidata_dia_tm AS x

    WHERE
        /* Misma TM o completitud permitida TM2 → TM1 */
        (
            x.TM_Origen = b.TM

            OR
            (
                b.TM = 'TM1'
                AND x.TM_Origen = 'TM2'
            )
        )

        /* El evento no puede ocurrir después del turno objetivo */
        AND
        (
            x.Fecha_Origen < b.Fecha

            OR
            (
                x.Fecha_Origen = b.Fecha

                AND
                CASE
                    WHEN x.Turno_Origen = 'A' THEN 1
                    WHEN x.Turno_Origen = 'B' THEN 2
                    ELSE 9
                END
                <=
                CASE
                    WHEN b.Turno = 'A' THEN 1
                    WHEN b.Turno = 'B' THEN 2
                    ELSE 9
                END
            )
        )

    ORDER BY
        /* Evento cronológico más reciente */
        x.Fecha_Origen DESC,

        CASE
            WHEN x.Turno_Origen = 'B' THEN 2
            WHEN x.Turno_Origen = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igualdad temporal, priorizar la propia TM */
        CASE
            WHEN x.TM_Origen = b.TM
                THEN 1

            WHEN b.TM = 'TM1'
             AND x.TM_Origen = 'TM2'
                THEN 2

            ELSE 9
        END,

        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO'
                THEN 1

            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
                THEN 2

            ELSE 9
        END

) AS c;


CREATE CLUSTERED INDEX
    IX_malla12_dia_resuelta_fecha_turno_tm

ON #malla12_dia_resuelta
(
    Fecha,
    Turno,
    TM
);
/* ============================================================
   BLOQUE 11B: ARRASTRE ÚLTIMO VALOR VÁLIDO
   FeS, ConsH y Malla -1/2
   ============================================================ */

DROP TABLE IF EXISTS #leyes_v2;

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    b.CuT,
    b.Fuente_CuT,

    b.CuS,
    b.Fuente_CuS,

    b.CO3,
    b.Fuente_CO3,

    b.CuFe,
    b.Fuente_CuFe,

    b.FeT,
    b.Fuente_FeT,

   ult_fes.FeS_Nuevo_Dia AS FeS,

CASE
    WHEN ult_fes.FeS_Nuevo_Dia IS NULL
        THEN b.Fuente_FeS

    WHEN ult_fes.Fecha = b.Fecha
        THEN ult_fes.Fuente_Nuevo_Dia

    WHEN ult_fes.Fecha < b.Fecha
        THEN 'ARRASTRE_ULTIMO_VALIDO'

    ELSE b.Fuente_FeS
END AS Fuente_FeS,

    ult_fes.Fecha AS Fecha_Origen_FeS,
    b.Turno AS Turno_Origen_FeS,
    b.TM AS TM_Origen_FeS,
/* ============================================================
   ConsH con resolución cronológica

   - A puede completar B.
   - B no puede modificar retroactivamente A.
   - TM2 puede completar TM1.
   - TM1 no completa TM2.
   ============================================================ */

CASE
    WHEN b.ConsH IS NOT NULL
     AND b.ConsH <> 0
     AND b.Fuente_ConsH <> 'NO_APLICA_MINA'

     /* Para A, TORRE_OTRO_TURNO significa que tomó el dato de B */
     AND NOT
     (
         b.Turno = 'A'
         AND b.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
     )
        THEN b.ConsH

    ELSE ult_consh.ConsH
END AS ConsH,

CASE
    /* Valor propio o completitud cronológicamente válida */
    WHEN b.ConsH IS NOT NULL
     AND b.ConsH <> 0
     AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
     AND NOT
     (
         b.Turno = 'A'
         AND b.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
     )
        THEN b.Fuente_ConsH

    WHEN ult_consh.ConsH IS NULL
        THEN b.Fuente_ConsH

    /* Valor de una fecha anterior */
    WHEN ult_consh.Fecha < b.Fecha
        THEN 'ARRASTRE_ULTIMO_VALIDO'

    /* Misma TM y mismo turno */
    WHEN ult_consh.Fecha = b.Fecha
     AND ult_consh.TM_Origen = b.TM
     AND ult_consh.Turno_Origen = b.Turno
        THEN ult_consh.Fuente_ConsH

    /* A completa B dentro de la misma TM */
    WHEN ult_consh.Fecha = b.Fecha
     AND ult_consh.TM_Origen = b.TM
     AND b.Turno = 'B'
     AND ult_consh.Turno_Origen = 'A'
        THEN 'TORRE_OTRO_TURNO_MISMO_DIA'

    /* TM2 completa TM1 */
    WHEN ult_consh.Fecha = b.Fecha
     AND b.TM = 'TM1'
     AND ult_consh.TM_Origen = 'TM2'
        THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1'

    ELSE 'ARRASTRE_ULTIMO_VALIDO'
END AS Fuente_ConsH,

    ult_consh.Fecha AS Fecha_Origen_ConsH,
    ult_consh.Turno_Origen AS Turno_Origen_ConsH,
    ult_consh.TM_Origen AS TM_Origen_ConsH,

   ult_malla.Malla_Menos_1_2
    AS Malla_Menos_1_2,

CASE
    WHEN ult_malla.Malla_Menos_1_2 IS NULL
        THEN b.Fuente_Malla_Menos_1_2

    ELSE ult_malla.Fuente_Malla_Resuelta

END AS Fuente_Malla_Menos_1_2,

    ult_malla.Fecha_Origen AS Fecha_Origen_Malla_Menos_1_2,
    ult_malla.Turno_Origen AS Turno_Origen_Malla_Menos_1_2,
    ult_malla.TM_Origen AS TM_Origen_Malla_Menos_1_2,

    b.Malla_Menos_100,
    b.Fuente_Malla_Menos_100,

    b.CaolBeta,
    b.Fuente_CaolBeta

INTO #leyes_v2
FROM #leyes_base b

OUTER APPLY (
    SELECT TOP (1)
        x.Fecha,
        x.FeS_Nuevo_Dia,
        x.Fuente_Nuevo_Dia
    FROM #fes_dia_resuelta x
    WHERE x.TM = b.TM
      AND x.Turno = b.Turno
      AND x.Fecha <= b.Fecha
      AND x.FeS_Nuevo_Dia IS NOT NULL
    ORDER BY
        x.Fecha DESC
) ult_fes

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha,
        x.Turno AS Turno_Origen,
        x.TM AS TM_Origen,
        x.ConsH,
        x.Fuente_ConsH

    FROM #leyes_base AS x

    WHERE x.ConsH IS NOT NULL
      AND x.ConsH <> 0
      AND x.Fuente_ConsH <> 'NO_APLICA_MINA'

      /* Excluir los A que fueron poblados desde el B futuro */
      AND NOT
      (
          x.Turno = 'A'
          AND x.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
      )

      /* Misma TM o compartición permitida TM2 → TM1 */
      AND
      (
          x.TM = b.TM
          OR
          (
              b.TM = 'TM1'
              AND x.TM = 'TM2'
          )
      )

      /* Restricción cronológica:
         - Para objetivo A: solo A del mismo día.
         - Para objetivo B: A o B del mismo día.
         - Siempre se permiten fechas anteriores.
      */
      AND
      (
          x.Fecha < b.Fecha

          OR
          (
              x.Fecha = b.Fecha
              AND
              (
                  (b.Turno = 'A' AND x.Turno = 'A')
                  OR
                  (b.Turno = 'B' AND x.Turno IN ('A', 'B'))
              )
          )
      )

    ORDER BY
        x.Fecha DESC,

        /* B es posterior a A */
        CASE
            WHEN x.Turno = 'B' THEN 2
            WHEN x.Turno = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igual instante, priorizar la propia TM */
        CASE
            WHEN x.TM = b.TM THEN 1
            WHEN b.TM = 'TM1' AND x.TM = 'TM2' THEN 2
            ELSE 9
        END,

        /* Priorizar medición original */
        CASE
            WHEN x.Fuente_ConsH = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_ConsH = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 3
        END

) AS ult_consh
OUTER APPLY
(
    SELECT TOP (1)
        d.Fecha,
        d.Turno,
        d.TM,

        d.Fecha_Origen,
        d.Turno_Origen,
        d.TM_Origen,

        d.Malla_Menos_1_2,
        d.Fuente_Origen,
        d.Fuente_Malla_Resuelta

    FROM #malla12_dia_resuelta AS d

    WHERE d.TM = b.TM
      AND d.Turno = b.Turno
      AND d.Fecha <= b.Fecha
      AND d.Malla_Menos_1_2 IS NOT NULL

    ORDER BY
        d.Fecha DESC

) AS ult_malla;

CREATE CLUSTERED INDEX IX_leyes_v2_fecha_turno_tm
ON #leyes_v2 (Fecha, Turno, TM);

/* ============================================================
   TRAZABILIDAD: estado inicial de #leyes_v2
   Los bloques posteriores actualizan esta metadata junto con el valor.
   ============================================================ */
DROP TABLE IF EXISTS #trazabilidad_analitos;

SELECT
    l.Fecha,
    l.Turno,
    l.TM AS TM_Destino,
    a.Analito,
    a.Valor_Final,
    CASE
        WHEN a.Valor_Final IS NULL THEN NULL
        WHEN a.Fuente_Tecnica = 'MINA' THEN 'MB'
        WHEN a.Fuente_Tecnica = 'IMP' THEN 'IMP'
        WHEN a.TM_Origen IN ('TM1', 'TM2')
         AND a.Fuente_Tecnica IN
             ('ARRASTRE_ULTIMO_VALIDO', 'SEMILLA_INICIO_PERIODO')
            THEN a.TM_Origen
        WHEN a.Fuente_Tecnica LIKE '%TORRE%' AND a.TM_Origen = 'TM1' THEN 'TM1'
        WHEN a.Fuente_Tecnica LIKE '%TORRE%' AND a.TM_Origen = 'TM2' THEN 'TM2'
        WHEN a.Fuente_Tecnica = 'SEMILLA_INICIO_PERIODO'
             AND a.TM_Origen IN ('TM1', 'TM2') THEN a.TM_Origen
    END AS Fuente_Base,
    a.Fuente_Tecnica,
    a.Fecha_Origen,
    a.Turno_Origen,
    a.TM_Origen,
    CASE
        WHEN a.Valor_Final IS NULL THEN 'SIN_DATO'
        WHEN a.Fuente_Tecnica = 'MINA' THEN 'FALLBACK_MB'
        WHEN a.Fuente_Tecnica = 'IMP' THEN 'PROVISIONAL_IMP'
        WHEN a.Fuente_Tecnica = 'ARRASTRE_ULTIMO_VALIDO' THEN 'ARRASTRE'
        WHEN a.Fuente_Tecnica = 'SEMILLA_INICIO_PERIODO' THEN 'SEMILLA'
        WHEN a.Fuente_Tecnica LIKE '%OTRO_TURNO%' THEN 'OTRO_TURNO'
        WHEN a.Fuente_Tecnica LIKE '%COMPARTIDA%' THEN 'COMPARTIDO_TM2_A_TM1'
        WHEN a.Fuente_Tecnica LIKE '%TORRE%' THEN 'PROPIO'
        ELSE 'SIN_DATO'
    END AS Resolucion
INTO #trazabilidad_analitos
FROM #leyes_v2 AS l
CROSS APPLY
(
    VALUES
      ('CuT', l.CuT, l.Fuente_CuT, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CuT LIKE '%TORRE%' THEN l.TM END),
      ('CuS', l.CuS, l.Fuente_CuS, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CuS LIKE '%TORRE%' THEN l.TM END),
      ('FeT', l.FeT, l.Fuente_FeT, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_FeT LIKE '%TORRE%' THEN l.TM END),
      ('FeS', l.FeS, l.Fuente_FeS, l.Fecha_Origen_FeS,
          l.Turno_Origen_FeS, l.TM_Origen_FeS),
      ('CO3', l.CO3, l.Fuente_CO3, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CO3 LIKE '%TORRE%' THEN l.TM END),
      ('ConsH', l.ConsH, l.Fuente_ConsH, l.Fecha_Origen_ConsH,
          l.Turno_Origen_ConsH, l.TM_Origen_ConsH),
      ('CuFe', l.CuFe, l.Fuente_CuFe, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CuFe LIKE '%TORRE%' THEN l.TM END),
      ('CaolBeta', l.CaolBeta, l.Fuente_CaolBeta, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CaolBeta LIKE '%TORRE%' THEN l.TM END),
      ('Malla_Menos_1_2', l.Malla_Menos_1_2, l.Fuente_Malla_Menos_1_2,
          l.Fecha_Origen_Malla_Menos_1_2, l.Turno_Origen_Malla_Menos_1_2,
          l.TM_Origen_Malla_Menos_1_2),
      ('Malla_Menos_100', l.Malla_Menos_100, l.Fuente_Malla_Menos_100,
          l.Fecha, l.Turno,
          CASE WHEN l.Fuente_Malla_Menos_100 LIKE '%TORRE%' THEN l.TM END)
) AS a(Analito, Valor_Final, Fuente_Tecnica, Fecha_Origen, Turno_Origen, TM_Origen);

/* La etiqueta técnica conserva explícitamente la compartición TM2 -> TM1. */
UPDATE #trazabilidad_analitos
SET Fuente_Base = 'TM2',
    TM_Origen = 'TM2',
    Resolucion = 'COMPARTIDO_TM2_A_TM1'
WHERE Fuente_Tecnica LIKE '%COMPARTIDA%TM2%TM1%';

CREATE UNIQUE CLUSTERED INDEX IX_trazabilidad_analitos_clave
ON #trazabilidad_analitos (Fecha, Turno, TM_Destino, Analito);

/* ============================================================
   BLOQUE 11C - Ajuste CuFe según regla oficial
   Si representatividad química > 0.75, usar Clays_CuFe.
   Si no cumple, mantener CuFe ya resuelto desde MINA/Conciliación.
   ============================================================ */

UPDATE tr
SET
    tr.Fuente_Base = CASE
        WHEN v.Fuente_CuFe LIKE 'LAB_TM2_%' THEN 'TM2'
        WHEN v.Fuente_CuFe LIKE 'LAB_PROPIO_%' THEN l.TM
        WHEN v.Fuente_CuFe LIKE 'MB_%' THEN 'MB'
        WHEN v.Fuente_CuFe LIKE 'IMP%' THEN 'IMP'
    END,
    tr.Fuente_Tecnica = v.Fuente_CuFe,
    tr.Fecha_Origen = l.Fecha,
    tr.Turno_Origen = l.Turno,
    tr.TM_Origen = CASE
        WHEN v.Fuente_CuFe LIKE 'LAB_TM2_%' THEN 'TM2'
        WHEN v.Fuente_CuFe LIKE 'LAB_PROPIO_%' THEN l.TM
    END,
    tr.Resolucion = CASE
        WHEN v.Fuente_CuFe LIKE 'LAB_TM2_%' THEN 'COMPARTIDO_TM2_A_TM1'
        WHEN v.Fuente_CuFe LIKE 'LAB_PROPIO_%' THEN 'PROPIO'
        WHEN v.Fuente_CuFe LIKE 'MB_%' THEN 'FALLBACK_MB'
        WHEN v.Fuente_CuFe LIKE 'IMP%' THEN 'PROVISIONAL_IMP'
        ELSE 'SIN_DATO'
    END
FROM #trazabilidad_analitos AS tr
INNER JOIN #leyes_v2 AS l
    ON l.Fecha = tr.Fecha AND l.Turno = tr.Turno AND l.TM = tr.TM_Destino
INNER JOIN inventar_SpcHidr.representatividad_torres_resultado AS r
    ON r.Dia = l.Fecha
INNER JOIN inventar_SpcHidr.v_clays_cufe_calculado_v2_test AS v
    ON v.Fecha = l.Fecha AND v.Turno = l.Turno AND v.Torre = l.TM
CROSS APPLY (VALUES (CASE
    WHEN l.TM = 'TM1' AND l.Turno = 'A' THEN r.TM1_TurnoA_Quimico
    WHEN l.TM = 'TM1' AND l.Turno = 'B' THEN r.TM1_TurnoB_Quimico
    WHEN l.TM = 'TM2' AND l.Turno = 'A' THEN r.TM2_TurnoA_Quimico
    WHEN l.TM = 'TM2' AND l.Turno = 'B' THEN r.TM2_TurnoB_Quimico
END)) AS rep(Rep_Raw)
CROSS APPLY (VALUES
    (CASE WHEN rep.Rep_Raw > 1 THEN rep.Rep_Raw / 100.0 ELSE rep.Rep_Raw END)
) AS rn(Rep_Normalizada)
WHERE tr.Analito = 'CuFe'
  AND v.CuFe_Final_2D IS NOT NULL
  AND ISNULL(rn.Rep_Normalizada, 0) > 0.75;

UPDATE l
SET
    l.CuFe = TRY_CAST(c.CuFe AS float),
    l.Fuente_CuFe = 'TORRE'
FROM #leyes_v2 l
INNER JOIN inventar_SpcHidr.representatividad_torres_resultado r
    ON r.Dia = l.Fecha
INNER JOIN inventar_SpcHidr.Clays_CuFe c
    ON c.Fecha = l.Fecha
   AND c.Turno = CASE
                    WHEN l.Turno = 'A' THEN 'TA'
                    WHEN l.Turno = 'B' THEN 'TB'
                 END
   AND c.Torre = CASE
                    WHEN l.TM = 'TM1' THEN 'TM-1'
                    WHEN l.TM = 'TM2' THEN 'TM-2'
                 END
CROSS APPLY (
    SELECT
        CASE
            WHEN l.TM = 'TM1' AND l.Turno = 'A' THEN r.TM1_TurnoA_Quimico
            WHEN l.TM = 'TM1' AND l.Turno = 'B' THEN r.TM1_TurnoB_Quimico
            WHEN l.TM = 'TM2' AND l.Turno = 'A' THEN r.TM2_TurnoA_Quimico
            WHEN l.TM = 'TM2' AND l.Turno = 'B' THEN r.TM2_TurnoB_Quimico
        END AS Rep_Quimica_Raw
) rep
CROSS APPLY (
    SELECT
        CASE
            WHEN rep.Rep_Quimica_Raw > 1
                THEN rep.Rep_Quimica_Raw / 100.0
            ELSE rep.Rep_Quimica_Raw
        END AS Rep_Quimica_Normalizada
) rep_norm
WHERE TRY_CAST(c.CuFe AS float) IS NOT NULL
  AND ISNULL(rep_norm.Rep_Quimica_Normalizada, 0) > 0.75;

  /* ============================================================
   BLOQUE 11C.1 - Completitud CuFe TM2 -> TM1

   Si TM2 tiene CuFe representativo de torre para la misma Fecha + Turno,
   puede completar TM2 cuando TM1 no tiene dato representativo propio.

   Esta regla alinea CuFe con la completitud asimétrica ya aplicada
   para CuT, CuS, CO3 y FeT.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'LAB_TM2_COMPARTIDO',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos AS tr
INNER JOIN #leyes_v2 AS tm1
    ON tm1.Fecha = tr.Fecha AND tm1.Turno = tr.Turno AND tm1.TM = tr.TM_Destino
INNER JOIN #leyes_v2 AS tm2
    ON tm2.Fecha = tm1.Fecha AND tm2.Turno = tm1.Turno AND tm2.TM = 'TM2'
WHERE tr.Analito = 'CuFe' AND tm1.TM = 'TM1'
  AND tm2.CuFe IS NOT NULL AND tm2.Fuente_CuFe LIKE '%TORRE%'
  AND (tm1.CuFe IS NULL OR ISNULL(tm1.Fuente_CuFe, '') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.CuFe = tm2.CuFe,
    tm1.Fuente_CuFe = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuFe IS NOT NULL
  AND tm2.Fuente_CuFe LIKE '%TORRE%'
  AND (
        tm1.CuFe IS NULL
     OR ISNULL(tm1.Fuente_CuFe, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11D - Ajuste FeT según regla oficial

   Si TM2 tiene FeT representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.

   Esto evita ponderar TM1 MINA + TM2 TORRE cuando el oficial clasifica
   el turno como TM2 y usa el valor representativo de TM2.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 tm1 ON tm1.Fecha=tr.Fecha AND tm1.Turno=tr.Turno AND tm1.TM=tr.TM_Destino
JOIN #leyes_v2 tm2 ON tm2.Fecha=tm1.Fecha AND tm2.Turno=tm1.Turno AND tm2.TM='TM2'
WHERE tr.Analito='FeT' AND tm1.TM='TM1' AND tm2.FeT IS NOT NULL
  AND tm2.Fuente_FeT LIKE '%TORRE%'
  AND (tm1.FeT IS NULL OR ISNULL(tm1.Fuente_FeT,'') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.FeT = tm2.FeT,
    tm1.Fuente_FeT = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.FeT IS NOT NULL
  AND tm2.Fuente_FeT LIKE '%TORRE%'
  AND (
        tm1.FeT IS NULL
     OR ISNULL(tm1.Fuente_FeT, '') NOT LIKE '%TORRE%'
  );

  /* ============================================================
   BLOQUE 11E - Ajuste CO3 según regla oficial

   Si TM2 tiene CO3 representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 tm1 ON tm1.Fecha=tr.Fecha AND tm1.Turno=tr.Turno AND tm1.TM=tr.TM_Destino
JOIN #leyes_v2 tm2 ON tm2.Fecha=tm1.Fecha AND tm2.Turno=tm1.Turno AND tm2.TM='TM2'
WHERE tr.Analito='CO3' AND tm1.TM='TM1' AND tm2.CO3 IS NOT NULL
  AND tm2.Fuente_CO3 LIKE '%TORRE%'
  AND (tm1.CO3 IS NULL OR ISNULL(tm1.Fuente_CO3,'') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.CO3 = tm2.CO3,
    tm1.Fuente_CO3 = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CO3 IS NOT NULL
  AND tm2.Fuente_CO3 LIKE '%TORRE%'
  AND (
        tm1.CO3 IS NULL
     OR ISNULL(tm1.Fuente_CO3, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11F - Ajuste CaolBeta según reporte oficial

   CaolBeta se toma desde Clays_CuFe cuando existe dato para
   Fecha + Turno + TM. No depende de Conciliación Chancado
   cuando existe dato NIR/Clays disponible.
   ============================================================ */

UPDATE tr
SET
    tr.Fuente_Base = CASE
        WHEN v.Fuente_CaolBeta LIKE 'NIR_TM2_%' THEN 'TM2'
        WHEN v.Fuente_CaolBeta LIKE 'NIR_PROPIO_%' THEN l.TM
        WHEN v.Fuente_CaolBeta LIKE 'MB_%' THEN 'MB'
        WHEN v.Fuente_CaolBeta LIKE 'IMP%' THEN 'IMP'
    END,
    tr.Fuente_Tecnica = v.Fuente_CaolBeta,
    tr.Fecha_Origen = l.Fecha,
    tr.Turno_Origen = l.Turno,
    tr.TM_Origen = CASE
        WHEN v.Fuente_CaolBeta LIKE 'NIR_TM2_%' THEN 'TM2'
        WHEN v.Fuente_CaolBeta LIKE 'NIR_PROPIO_%' THEN l.TM
    END,
    tr.Resolucion = CASE
        WHEN v.Fuente_CaolBeta LIKE 'NIR_TM2_%' THEN 'COMPARTIDO_TM2_A_TM1'
        WHEN v.Fuente_CaolBeta LIKE 'NIR_PROPIO_%' THEN 'PROPIO'
        WHEN v.Fuente_CaolBeta LIKE 'MB_%' THEN 'FALLBACK_MB'
        WHEN v.Fuente_CaolBeta LIKE 'IMP%' THEN 'PROVISIONAL_IMP'
        ELSE 'SIN_DATO'
    END
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 l
  ON l.Fecha=tr.Fecha AND l.Turno=tr.Turno AND l.TM=tr.TM_Destino
JOIN inventar_SpcHidr.v_clays_cufe_calculado_v2_test v
  ON v.Fecha=l.Fecha AND v.Turno=l.Turno AND v.Torre=l.TM
WHERE tr.Analito='CaolBeta' AND v.CaolBeta_Final_2D IS NOT NULL;

UPDATE l
SET
    l.CaolBeta = clay.CaolBeta_Clays,
    l.Fuente_CaolBeta = 'CLAYS'
FROM #leyes_v2 l
INNER JOIN inventar_SpcHidr.Clays_CuFe c
    ON c.Fecha = l.Fecha
   AND c.Turno = CASE
                    WHEN l.Turno = 'A' THEN 'TA'
                    WHEN l.Turno = 'B' THEN 'TB'
                 END
   AND c.Torre = CASE
                    WHEN l.TM = 'TM1' THEN 'TM-1'
                    WHEN l.TM = 'TM2' THEN 'TM-2'
                 END
OUTER APPLY (
    SELECT
        TRY_CONVERT(float, REPLACE(CONVERT(varchar(50), c.CaolBeta), ',', '.')) AS CaolBeta_Clays
) clay
WHERE clay.CaolBeta_Clays IS NOT NULL;

/* ============================================================
   BLOQUE 11G - Ajuste CuT según regla oficial

   Si TM2 tiene CuT representativo de torre para la misma Fecha + Turno,
   puede completar TM2 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 tm1 ON tm1.Fecha=tr.Fecha AND tm1.Turno=tr.Turno AND tm1.TM=tr.TM_Destino
JOIN #leyes_v2 tm2 ON tm2.Fecha=tm1.Fecha AND tm2.Turno=tm1.Turno AND tm2.TM='TM2'
WHERE tr.Analito='CuT' AND tm1.TM='TM1' AND tm2.CuT IS NOT NULL
  AND tm2.Fuente_CuT LIKE '%TORRE%'
  AND (tm1.CuT IS NULL OR ISNULL(tm1.Fuente_CuT,'') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.CuT = tm2.CuT,
    tm1.Fuente_CuT = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuT IS NOT NULL
  AND tm2.Fuente_CuT LIKE '%TORRE%'
  AND (
        tm1.CuT IS NULL
     OR ISNULL(tm1.Fuente_CuT, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11H - Ajuste CuS según regla oficial

   Si TM2 tiene CuS representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 tm1 ON tm1.Fecha=tr.Fecha AND tm1.Turno=tr.Turno AND tm1.TM=tr.TM_Destino
JOIN #leyes_v2 tm2 ON tm2.Fecha=tm1.Fecha AND tm2.Turno=tm1.Turno AND tm2.TM='TM2'
WHERE tr.Analito='CuS' AND tm1.TM='TM1' AND tm2.CuS IS NOT NULL
  AND tm2.Fuente_CuS LIKE '%TORRE%'
  AND (tm1.CuS IS NULL OR ISNULL(tm1.Fuente_CuS,'') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.CuS = tm2.CuS,
    tm1.Fuente_CuS = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuS IS NOT NULL
  AND tm2.Fuente_CuS LIKE '%TORRE%'
  AND (
        tm1.CuS IS NULL
     OR ISNULL(tm1.Fuente_CuS, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11H.1 - Completitud Malla -100 TM2 -> TM1

   Regla:
   - TM2 puede completar TM1.
   - TM1 NO puede completar TM2.
   - La compartición es exclusivamente dentro de la misma
     Fecha + Turno.
   - TM2-A solo puede completar TM1-A.
   - TM2-B solo puede completar TM1-B.
   - Solo se comparte cuando TM2 posee dato válido de TORRE.
   - Si TM1 ya posee dato de TORRE, se conserva su dato propio.
   ============================================================ */

/* ------------------------------------------------------------
   Trazabilidad antes de modificar el valor
   ------------------------------------------------------------ */
UPDATE tr
SET
    tr.Fuente_Base     = 'TM2',
    tr.Fuente_Tecnica  = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen    = tm2.Fecha,
    tr.Turno_Origen    = tm2.Turno,
    tr.TM_Origen       = 'TM2',
    tr.Resolucion      = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
INNER JOIN #leyes_v2 tm1
    ON  tm1.Fecha = tr.Fecha
    AND tm1.Turno = tr.Turno
    AND tm1.TM    = tr.TM_Destino
INNER JOIN #leyes_v2 tm2
    ON  tm2.Fecha = tm1.Fecha
    AND tm2.Turno = tm1.Turno
    AND tm2.TM    = 'TM2'
WHERE tr.Analito = 'Malla_Menos_100'
  AND tm1.TM = 'TM1'
  AND tm2.Malla_Menos_100 IS NOT NULL
  AND tm2.Fuente_Malla_Menos_100 LIKE '%TORRE%'
  AND (
        tm1.Malla_Menos_100 IS NULL
        OR ISNULL(tm1.Fuente_Malla_Menos_100, '') NOT LIKE '%TORRE%'
      );


/* ------------------------------------------------------------
   Compartición efectiva TM2 -> TM1
   ------------------------------------------------------------ */
UPDATE tm1
SET
    tm1.Malla_Menos_100        = tm2.Malla_Menos_100,
    tm1.Fuente_Malla_Menos_100 = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON  tm2.Fecha = tm1.Fecha
    AND tm2.Turno = tm1.Turno
    AND tm2.TM    = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.Malla_Menos_100 IS NOT NULL
  AND tm2.Fuente_Malla_Menos_100 LIKE '%TORRE%'
  AND (
        tm1.Malla_Menos_100 IS NULL
        OR ISNULL(tm1.Fuente_Malla_Menos_100, '') NOT LIKE '%TORRE%'
      );
/* ============================================================
   BLOQUE 11I - Guarda de evaluabilidad por origen operacional

   RN-064 ampliada:
   - El TMS siempre proviene de CV008/CV108.
   - STOCK, MINA y SRR constituyen evidencia oficial.
   - IMP positivo constituye evidencia operacional provisional.
   - IMP no reemplaza ni distribuye el TMS.
   - Si CV008/CV108 entregan TMS cero, IMP no habilita tonelaje.
   ============================================================ */

UPDATE t
SET
    t.TMS = 0
FROM #tms_tm AS t

LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr AS o
    ON o.Fecha = t.Fecha
   AND o.Turno = t.Turno

LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS c
    ON c.Fecha = t.Fecha
   AND c.Turno = t.Turno

WHERE ISNULL(t.TMS, 0) > 0

  /* No existe evidencia operacional oficial */
  AND ISNULL(o.Ton_Stock_Camiones, 0) = 0
  AND ISNULL(o.Ton_Mina_Camiones, 0) = 0
  AND ISNULL(o.Ton_SRR, 0) = 0

  /* Tampoco existe evidencia provisional IMP */
  AND NOT
  (
      UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato, '')))) = 'IMP'
      AND ISNULL(c.Ton, 0) > 0
  );

/* ============================================================
   BLOQUE 12: PONDERACIÓN DE LEYES REALES POR TMS
   ============================================================ */

/* TRAZABILIDAD FINAL: despues de resoluciones y antes de ponderacion. */
UPDATE tr
SET tr.Valor_Final = CASE tr.Analito
    WHEN 'CuT' THEN l.CuT WHEN 'CuS' THEN l.CuS WHEN 'FeT' THEN l.FeT
    WHEN 'FeS' THEN l.FeS WHEN 'CO3' THEN l.CO3 WHEN 'ConsH' THEN l.ConsH
    WHEN 'CuFe' THEN l.CuFe WHEN 'CaolBeta' THEN l.CaolBeta
    WHEN 'Malla_Menos_1_2' THEN l.Malla_Menos_1_2
    WHEN 'Malla_Menos_100' THEN l.Malla_Menos_100 END
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 l
  ON l.Fecha=tr.Fecha AND l.Turno=tr.Turno AND l.TM=tr.TM_Destino;

DELETE FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
WHERE Fecha >= @fecha_inicio AND Fecha < @fecha_fin;

INSERT INTO inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
(
    Fecha, Turno, TM_Destino, Analito, Valor_Final,
    Fuente_Base, Fuente_Tecnica, Fecha_Origen, Turno_Origen, TM_Origen,
    Resolucion, Representatividad_Quimica, Representatividad_Fisica,
    Fecha_Proceso
)
SELECT
    tr.Fecha, tr.Turno, tr.TM_Destino, tr.Analito, tr.Valor_Final,
    CASE WHEN tr.Valor_Final IS NULL THEN NULL ELSE tr.Fuente_Base END,
    tr.Fuente_Tecnica, tr.Fecha_Origen, tr.Turno_Origen, tr.TM_Origen,
    CASE WHEN tr.Valor_Final IS NULL THEN 'SIN_DATO' ELSE tr.Resolucion END,
    TRY_CONVERT(decimal(18,10), rep.Rep_Quimica),
    TRY_CONVERT(decimal(18,10), rep.Rep_Fisica), SYSDATETIME()
FROM #trazabilidad_analitos tr
LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado r
  ON r.Dia=tr.Fecha
CROSS APPLY (VALUES
(
    CASE
      WHEN tr.TM_Destino='TM1' AND tr.Turno='A' THEN r.TM1_TurnoA_Quimico
      WHEN tr.TM_Destino='TM1' AND tr.Turno='B' THEN r.TM1_TurnoB_Quimico
      WHEN tr.TM_Destino='TM2' AND tr.Turno='A' THEN r.TM2_TurnoA_Quimico
      WHEN tr.TM_Destino='TM2' AND tr.Turno='B' THEN r.TM2_TurnoB_Quimico END,
    CASE
      WHEN tr.TM_Destino='TM1' AND tr.Turno='A' THEN r.TM1_TurnoA_Fisico
      WHEN tr.TM_Destino='TM1' AND tr.Turno='B' THEN r.TM1_TurnoB_Fisico
      WHEN tr.TM_Destino='TM2' AND tr.Turno='A' THEN r.TM2_TurnoA_Fisico
      WHEN tr.TM_Destino='TM2' AND tr.Turno='B' THEN r.TM2_TurnoB_Fisico END
)) rep(Rep_Quimica, Rep_Fisica)
WHERE tr.Fecha >= @fecha_inicio AND tr.Fecha < @fecha_fin;

DROP TABLE IF EXISTS #reales;

SELECT
    t.Fecha,
    t.Turno,

    SUM(t.TMS) AS Apilado_TMS_Real,

    SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuT_Real,

    SUM(t.TMS * l.CuS) / NULLIF(SUM(CASE WHEN l.CuS IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuS_Real,

    CASE
        WHEN SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) IS NULL
          OR SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) = 0
        THEN NULL
        ELSE
            (
                SUM(t.TMS * l.CuS) / NULLIF(SUM(CASE WHEN l.CuS IS NOT NULL THEN t.TMS ELSE 0 END), 0)
            )
            /
            (
                SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0)
            )
    END AS Solubilidad_Real,

    SUM(t.TMS * l.CO3) / NULLIF(SUM(CASE WHEN l.CO3 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CO3_Real,

    SUM(t.TMS * l.CuFe) / NULLIF(SUM(CASE WHEN l.CuFe IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuFe_Real,

    SUM(t.TMS * l.FeT) / NULLIF(SUM(CASE WHEN l.FeT IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS FeT_Real,

    SUM(t.TMS * l.FeS) / NULLIF(SUM(CASE WHEN l.FeS IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS FeS_Real,

    SUM(t.TMS * l.ConsH) / NULLIF(SUM(CASE WHEN l.ConsH IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS ConsH_Real,

    SUM(t.TMS * l.Malla_Menos_1_2) / NULLIF(SUM(CASE WHEN l.Malla_Menos_1_2 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS Malla_Menos_1_2_Real,

    SUM(t.TMS * l.Malla_Menos_100) / NULLIF(SUM(CASE WHEN l.Malla_Menos_100 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS Malla_Menos_100_Real,

    SUM(t.TMS * l.CaolBeta) / NULLIF(SUM(CASE WHEN l.CaolBeta IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CaolBeta_Real

INTO #reales
FROM #tms_tm t
LEFT JOIN #leyes_v2 l
    ON l.Fecha = t.Fecha
   AND l.Turno = t.Turno
   AND l.TM = t.TM
GROUP BY
    t.Fecha,
    t.Turno;

CREATE CLUSTERED INDEX IX_reales_fecha_turno
ON #reales (Fecha, Turno);

/* ============================================================
   BLOQUE 13: CLASIFICACIÓN DE MUESTRA QUÍMICA Y FÍSICA

   Ajuste:
   - Se incorpora IMP como fuente válida de conciliación.
   - No se modifica la prioridad de TORRE, MINA, ARRASTRE
     ni SEMILLA.
   ============================================================ */

DROP TABLE IF EXISTS #muestras;

WITH fuentes AS
(
    SELECT
        Fecha,
        Turno,

        /* ----------------------------------------------------
           Fuentes químicas
           ---------------------------------------------------- */

        MAX
        (
            CASE
                WHEN Fuente_CuT  LIKE '%TORRE%'
                  OR Fuente_CuS  LIKE '%TORRE%'
                  OR Fuente_CO3  LIKE '%TORRE%'
                  OR Fuente_CuFe LIKE '%TORRE%'
                  OR Fuente_FeT  LIKE '%TORRE%'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Torre,

        MAX
        (
            CASE
                WHEN Fuente_CuT  = 'MINA'
                  OR Fuente_CuS  = 'MINA'
                  OR Fuente_CO3  = 'MINA'
                  OR Fuente_CuFe = 'MINA'
                  OR Fuente_FeT  = 'MINA'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Mina,

        /* Nueva clasificación IMP */
        MAX
        (
            CASE
                WHEN Fuente_CuT  = 'IMP'
                  OR Fuente_CuS  = 'IMP'
                  OR Fuente_CO3  = 'IMP'
                  OR Fuente_CuFe = 'IMP'
                  OR Fuente_FeT  = 'IMP'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_IMP,

        MAX
        (
            CASE
                WHEN Fuente_FeS  = 'ARRASTRE_ULTIMO_VALIDO'
                  OR Fuente_ConsH = 'ARRASTRE_ULTIMO_VALIDO'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Arrastre,

        MAX
        (
            CASE
                WHEN Fuente_CuT   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CuS   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CO3   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CuFe  = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_FeT   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_FeS   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_ConsH = 'SEMILLA_INICIO_PERIODO'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Semilla,

        /* ----------------------------------------------------
           Fuentes físicas
           ---------------------------------------------------- */

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                  OR Fuente_Malla_Menos_100 LIKE '%TORRE%'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Torre,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'MINA'
                  OR Fuente_Malla_Menos_100 = 'MINA'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Mina,

        /* Nueva clasificación IMP */
        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'IMP'
                  OR Fuente_Malla_Menos_100 = 'IMP'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_IMP,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'ARRASTRE_ULTIMO_VALIDO'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Arrastre,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_Malla_Menos_100 = 'SEMILLA_INICIO_PERIODO'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Semilla

    FROM #leyes_v2

    GROUP BY
        Fecha,
        Turno
)

SELECT
    Fecha,
    Turno,

    CASE
        WHEN Quimica_Semilla = 1
            THEN 'SEMILLA'

        WHEN Quimica_Arrastre = 1
         AND
         (
             Quimica_Torre = 1
             OR Quimica_Mina = 1
             OR Quimica_IMP = 1
         )
            THEN 'MIXTA'

        WHEN Quimica_Torre + Quimica_Mina + Quimica_IMP >= 2
            THEN 'MIXTA'

        WHEN Quimica_Arrastre = 1
            THEN 'ARRASTRE'

        WHEN Quimica_Torre = 1
            THEN 'TORRE'

        WHEN Quimica_IMP = 1
            THEN 'IMP'

        WHEN Quimica_Mina = 1
            THEN 'MINA'

        ELSE NULL
    END AS Muestra_Quimica,

    CASE
        WHEN Fisica_Semilla = 1
            THEN 'SEMILLA'

        WHEN Fisica_Arrastre = 1
         AND
         (
             Fisica_Torre = 1
             OR Fisica_Mina = 1
             OR Fisica_IMP = 1
         )
            THEN 'MIXTA'

        WHEN Fisica_Torre + Fisica_Mina + Fisica_IMP >= 2
            THEN 'MIXTA'

        WHEN Fisica_Arrastre = 1
            THEN 'ARRASTRE'

        WHEN Fisica_Torre = 1
            THEN 'TORRE'

        WHEN Fisica_IMP = 1
            THEN 'IMP'

        WHEN Fisica_Mina = 1
            THEN 'MINA'

        ELSE NULL
    END AS Muestra_Fisica

INTO #muestras

FROM fuentes;

CREATE CLUSTERED INDEX IX_muestras_fecha_turno
ON #muestras (Fecha, Turno);
/* ============================================================
   BLOQUE 14: CAMPAÑA, MÓDULO, AVANCE Y PLAN
   ============================================================ */

DROP TABLE IF EXISTS #campania_modulo;
DROP TABLE IF EXISTS #plan_mensual;
DROP TABLE IF EXISTS #plan_semanal;
DROP TABLE IF EXISTS #origen_apilado;

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
INTO #campania_modulo
FROM inventar_SpcHidr.v_reporte_turno_campania_modulo_test
WHERE Fecha >= @fecha_inicio
  AND Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_campania_modulo
ON #campania_modulo (Fecha);


/* ============================================================
   PLAN MENSUAL
   ============================================================ */

SELECT
    fecha AS Fecha,
    apilamiento AS Apilado_TMS_Plan_Mensual,
    cut AS CuT_Plan_Mensual,
    cus AS CuS_Plan_Mensual,
    CAST(
    CASE
        WHEN cut IS NULL OR cut = 0 OR cus IS NULL THEN NULL
        ELSE cus / cut
    END
    AS decimal(18, 6)) AS Solubilidad_Plan_Mensual,
    co3 AS CO3_Plan_Mensual,
    cl_acido AS ConsH_Plan_Mensual,
    cufe AS CuFe_Plan_Mensual,
    malla_100 AS Malla_Menos_100_Plan_Mensual,
    caol_beta AS CaolBeta_Plan_Mensual
INTO #plan_mensual
FROM inventar_SpcHidr.plan_mensual_reporte_turno
WHERE fecha >= @fecha_inicio
  AND fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_plan_mensual
ON #plan_mensual (Fecha);


/* ============================================================
   PLAN SEMANAL
   ============================================================ */

SELECT
    fecha AS Fecha,
    ton AS Apilado_TMS_Plan_Semanal,
    cut AS CuT_Plan_Semanal,
    cus AS CuS_Plan_Semanal,
    CAST(
    CASE
        WHEN cut IS NULL OR cut = 0 OR cus IS NULL THEN NULL
        ELSE cus / cut
    END
    AS decimal(18, 6)) AS Solubilidad_Plan_Semanal,
    co3 AS CO3_Plan_Semanal,
    cl_acido AS ConsH_Plan_Semanal,
    cufe AS CuFe_Plan_Semanal,
    malla_100 AS Malla_Menos_100_Plan_Semanal,
    betaclay AS CaolBeta_Plan_Semanal,
    porc_1_2 AS Malla_Menos_1_2_Plan_Semanal,
    arcillas AS Arcillas_Plan_Semanal,
    cuarzo AS Cuarzo_Plan_Semanal
INTO #plan_semanal
FROM inventar_SpcHidr.plan_semanal_reporte_turno
WHERE fecha >= @fecha_inicio
  AND fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_plan_semanal
ON #plan_semanal (Fecha);


 /* ============================================================
   BLOQUE 15: DISTRIBUCIÓN FINAL STOCK / MINA / SRR

   Prioridad:
   1. Origen oficial desde mov_cam.
   2. IMP provisional:
      - SRR = Es_SRR = 1
      - Camiones = STOCK
      - MINA = 0
   3. Sin origen: proporciones en cero.

   IMPORTANTE:
   IMP no reemplaza Apilado_TMS_Real.
   Solo determina las proporciones de origen.
   ============================================================ */

DROP TABLE IF EXISTS #imp_origen_turno;
DROP TABLE IF EXISTS #origen_apilado;


/* ------------------------------------------------------------
   15A. Consolidación IMP por Fecha + Turno
   ------------------------------------------------------------ */

SELECT
    CAST(i.Fecha AS date) AS Fecha,

    CASE
        WHEN i.Turno IN ('TA', 'A') THEN 'A'
        WHEN i.Turno IN ('TB', 'B') THEN 'B'
        ELSE i.Turno
    END COLLATE DATABASE_DEFAULT AS Turno,

    CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 1
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_SRR,

    CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 0
                 AND UPPER(LTRIM(RTRIM(ISNULL(i.Tipo_Registro, ''))))
                     = 'CAMION'
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_Camiones,

		  CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 0
                 AND UPPER(LTRIM(RTRIM(ISNULL(i.Tipo_Registro, ''))))
                     = 'MINA'
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_mina,

    CAST
    (
        SUM(ISNULL(i.Ton, 0))
        AS decimal(38,10)
    ) AS Ton_IMP_Total

INTO #imp_origen_turno

FROM DEV_SIIR.hidro.v_imp_chancado_normalizado AS i

WHERE i.Fecha >= @fecha_inicio
  AND i.Fecha <  @fecha_fin
  AND ISNULL(i.Ton, 0) > 0

GROUP BY
    CAST(i.Fecha AS date),

    CASE
        WHEN i.Turno IN ('TA', 'A') THEN 'A'
        WHEN i.Turno IN ('TB', 'B') THEN 'B'
        ELSE i.Turno
    END COLLATE DATABASE_DEFAULT;


CREATE CLUSTERED INDEX IX_imp_origen_turno
ON #imp_origen_turno (Fecha, Turno);


/* ------------------------------------------------------------
   15B. Determinación de la fuente de origen
   ------------------------------------------------------------ */

;WITH origen_base AS
(
    SELECT
        r.Fecha,
        r.Turno,

        CAST
        (
            ISNULL(r.Apilado_TMS_Real, 0)
            AS decimal(38,10)
        ) AS Apilado_TMS_Real,

        /* Fuente oficial */

        CAST
        (
            ISNULL(p.Ton_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Stock_Oficial,

        CAST
        (
            ISNULL(p.Ton_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Mina_Oficial,

        CAST
        (
            ISNULL(p.Ton_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_SRR_Oficial,

        CAST
        (
            ISNULL(p.Prop_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Prop_Stock_Oficial,

        CAST
        (
            ISNULL(p.Prop_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Prop_Mina_Oficial,

        /* Fuente IMP */

        CAST
        (
            ISNULL(i.Ton_IMP_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_SRR,

        CAST
        (
            ISNULL(i.Ton_IMP_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Camiones,

				CAST
        (
            ISNULL(i.Ton_IMP_mina, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_mina,

        CAST
        (
            ISNULL(i.Ton_IMP_Total, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Total,

        c.Fuente_Dato,

        CASE
            /* Prioridad 1: origen oficial positivo */

            WHEN ISNULL(p.Ton_Stock_Camiones, 0) > 0
              OR ISNULL(p.Ton_Mina_Camiones, 0) > 0
              OR ISNULL(p.Ton_SRR, 0) > 0
                THEN 'OFICIAL'

            /* Prioridad 2: respaldo provisional IMP */

            WHEN UPPER
                 (
                     LTRIM
                     (
                         RTRIM
                         (
                             ISNULL(c.Fuente_Dato, '')
                         )
                     )
                 ) = 'IMP'
             AND ISNULL(i.Ton_IMP_Total, 0) > 0
                THEN 'IMP'

            ELSE 'SIN_ORIGEN'
        END AS Fuente_Origen

    FROM #reales AS r

    LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr AS p
        ON p.Fecha = r.Fecha
       AND p.Turno = r.Turno

    LEFT JOIN #imp_origen_turno AS i
        ON i.Fecha = r.Fecha
       AND i.Turno = r.Turno

    LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS c
        ON c.Fecha = r.Fecha
       AND c.Turno = r.Turno
),

origen_srr AS
(
    SELECT
        b.*,

        /* SRR limitado al Apilado_TMS_Real */

        CAST
        (
            CASE
                WHEN b.Apilado_TMS_Real <= 0
                    THEN 0

                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN
                        CASE
                            WHEN b.Ton_SRR_Oficial <= 0
                                THEN 0

                            WHEN b.Ton_SRR_Oficial
                               > b.Apilado_TMS_Real
                                THEN b.Apilado_TMS_Real

                            ELSE b.Ton_SRR_Oficial
                        END

                WHEN b.Fuente_Origen = 'IMP'
                    THEN
                        CASE
                            WHEN b.Ton_IMP_SRR <= 0
                                THEN 0

                            WHEN b.Ton_IMP_SRR
                               > b.Apilado_TMS_Real
                                THEN b.Apilado_TMS_Real

                            ELSE b.Ton_IMP_SRR
                        END

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Ton_SRR_Usado,

        /* Proporción de camiones STOCK */

        CAST
        (
            CASE
                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN b.Prop_Stock_Oficial

                WHEN b.Fuente_Origen = 'IMP'
                 AND b.Ton_IMP_Camiones > 0
                    THEN (b.Ton_IMP_Camiones/(b.Ton_IMP_Total-b.Ton_IMP_SRR))

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Prop_Stock_Camiones_Usada,

        /* Proporción de camiones MINA */

        CAST
        (
            CASE
                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN b.Prop_Mina_Oficial

                WHEN b.Fuente_Origen = 'IMP'
                    AND b.Ton_IMP_mina > 0
                    THEN (b.Ton_IMP_mina/(b.Ton_IMP_Total-b.Ton_IMP_SRR))

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Prop_Mina_Camiones_Usada

    FROM origen_base AS b
),

origen_calculado AS
(
    SELECT
        s.*,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE

									((s.Apilado_TMS_Real- s.Ton_SRR_Usado)*
										s.Prop_Stock_Camiones_Usada)/s.Apilado_TMS_Real

            END
            AS decimal(18,8)
        ) AS Prop_Final_Stock,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
								((s.Apilado_TMS_Real- s.Ton_SRR_Usado)*
										s.Prop_Mina_Camiones_Usada)/s.Apilado_TMS_Real


            END
            AS decimal(18,8)
        ) AS Prop_Final_Mina,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
                    s.Ton_SRR_Usado
                    / NULLIF(s.Apilado_TMS_Real, 0)
            END
            AS decimal(18,8)
        ) AS Prop_Final_SRR

    FROM origen_srr AS s
)

SELECT
    o.Fecha,
    o.Turno,

    o.Prop_Final_Stock,
    o.Prop_Final_Mina,
    o.Prop_Final_SRR,

    CAST
    (
        o.Prop_Final_Stock
      + o.Prop_Final_Mina
      + o.Prop_Final_SRR
        AS decimal(18,8)
    ) AS Prop_Final_Total,

    /* Diferencia de tonelaje contra TMS real */

    CAST
    (
        (
            (
                o.Apilado_TMS_Real
              - o.Ton_SRR_Usado
            )
            * o.Prop_Stock_Camiones_Usada
        )
      + (
            (
                o.Apilado_TMS_Real
              - o.Ton_SRR_Usado
            )
            * o.Prop_Mina_Camiones_Usada
        )
      + o.Ton_SRR_Usado
      - o.Apilado_TMS_Real

        AS decimal(18,8)
    ) AS Check_Distribucion_Apilado,

    /* Columnas de auditoría */

    o.Fuente_Origen,
    o.Ton_SRR_Usado,
    o.Ton_IMP_SRR,
    o.Ton_IMP_Camiones,
    o.Ton_Stock_Oficial,
    o.Ton_Mina_Oficial,
    o.Ton_SRR_Oficial

INTO #origen_apilado

FROM origen_calculado AS o;


CREATE CLUSTERED INDEX IX_origen_apilado
ON #origen_apilado (Fecha, Turno);

/* ============================================================
   SELECT FINAL - ORDEN FORMATO BHP
   ============================================================ */

SELECT
    r.Fecha,
    cm.Campania,
    cm.Material,
    cm.Modulo,
    cm.Avance,
    r.Turno,

    /* Apilado */
    r.Apilado_TMS_Real,
    pm.Apilado_TMS_Plan_Mensual,

    /* Distribución de origen */
    CAST(100.0 * COALESCE(oa.Prop_Final_Stock, 0) AS decimal(18, 2)) AS STOCK,
    CAST(100.0 * COALESCE(oa.Prop_Final_Mina, 0) AS decimal(18, 2)) AS MINA,
    CAST(100.0 * COALESCE(oa.Prop_Final_SRR, 0) AS decimal(18, 2)) AS SRR,

    /* Análisis químicos */
    r.CuT_Real,
    pm.CuT_Plan_Mensual,
    ps.CuT_Plan_Semanal,

    r.CuS_Real,
    pm.CuS_Plan_Mensual,
    ps.CuS_Plan_Semanal,

    r.Solubilidad_Real,
    pm.Solubilidad_Plan_Mensual,
    ps.Solubilidad_Plan_Semanal,

    r.CO3_Real,
    pm.CO3_Plan_Mensual,
    ps.CO3_Plan_Semanal,

    r.CuFe_Real,
    pm.CuFe_Plan_Mensual,
    ps.CuFe_Plan_Semanal,

    r.FeT_Real,
    r.FeS_Real,

    /* Dosis / consumo ácido */
    r.ConsH_Real,

    /* Granulometrías */
    r.Malla_Menos_1_2_Real,
    ps.Malla_Menos_1_2_Plan_Semanal,

    r.Malla_Menos_100_Real,
    pm.Malla_Menos_100_Plan_Mensual,
    ps.Malla_Menos_100_Plan_Semanal,

 /* NIR */
r.CaolBeta_Real,
pm.CaolBeta_Plan_Mensual,
ps.CaolBeta_Plan_Semanal,

/* Dosis de ácido */
CAST(
    ROUND(
        CASE
            WHEN ISNULL(r.Solubilidad_Real, 0) < 0.25 THEN
                CASE
                    WHEN ISNULL(r.CO3_Real, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(r.CO3_Real, 0))
                END

            ELSE
                CASE
                    WHEN r.CuS_Real IS NULL OR r.CuS_Real <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(r.CuS_Real))
                               + 18.99
                               + (15.51 * ISNULL(r.CO3_Real, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(r.CuS_Real))
                               + 18.99
                               + (15.51 * ISNULL(r.CO3_Real, 0))
                        END
                END
        END
    , 2)
AS decimal(18, 2)) AS Dosis_Acido_Ideal_TM,

CAST(
    ROUND(
        CASE
            WHEN ISNULL(ps.Solubilidad_Plan_Semanal, 0) < 0.25 THEN
                CASE
                    WHEN ISNULL(ps.CO3_Plan_Semanal, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0))
                END

            ELSE
                CASE
                    WHEN ps.CuS_Plan_Semanal IS NULL OR ps.CuS_Plan_Semanal <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(ps.CuS_Plan_Semanal))
                               + 18.99
                               + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(ps.CuS_Plan_Semanal))
                               + 18.99
                               + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0))
                        END
                END
        END
    , 2)
AS decimal(18, 2)) AS Dosis_Acido_Programa_Semanal,

        /* Fuentes de información explícitas */
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN '-'
        ELSE COALESCE(fi.Fuente_Info_Quimica, '-')
    END AS Fuente_Info_Quimica,

    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN '-'
        ELSE COALESCE(fi.Fuente_Info_Fisica, '-')
    END AS Fuente_Info_Fisica,

    /* Clasificación técnica original */
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN NULL
        ELSE m.Muestra_Quimica
    END AS Muestra_Quimica,

    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN NULL
        ELSE m.Muestra_Fisica
    END AS Muestra_Fisica

FROM #reales r

LEFT JOIN #muestras m
    ON m.Fecha = r.Fecha
   AND m.Turno = r.Turno

LEFT JOIN inventar_SpcHidr.v_reporte_turno_fuentes_info_test fi
    ON fi.Fecha = r.Fecha
   AND fi.Turno = r.Turno

LEFT JOIN #campania_modulo cm
    ON cm.Fecha = r.Fecha

LEFT JOIN #origen_apilado oa
    ON oa.Fecha = r.Fecha
   AND oa.Turno = r.Turno

LEFT JOIN #plan_mensual pm
    ON pm.Fecha = r.Fecha

LEFT JOIN #plan_semanal ps
    ON ps.Fecha = r.Fecha

ORDER BY
    r.Fecha,
    r.Turno;
END