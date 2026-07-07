USE [inventar_SpcHidr]
GO
/****** Objeto: StoredProcedure [inventar_SpcHidr].[sp_reporte_turno_test] Fecha de script: 07-07-2026 8:50:08 REPORTE OFICIAL DE TORRES DIA 07-07-2026******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER   PROCEDURE [inventar_SpcHidr].[sp_reporte_turno_test]
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
       ============================================================ */

    SELECT
        Fecha,
        Flag_Apilado_Valido,
        TMH_CV008_A,
        TMH_CV008_B,
        TMH_CV108_A,
        TMH_CV108_B,
        TMH_Apilado_Total_A,
        TMH_Apilado_Total_B,
        TMH_Apilado_Total_Dia
    INTO #fechas
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2
    WHERE Fecha >= @fecha_inicio
      AND Fecha <  @fecha_fin;

    CREATE CLUSTERED INDEX IX_fechas
    ON #fechas (Fecha);

    /* ============================================================
       BLOQUE 2: HUMEDAD LABORATORIO
       ============================================================ */

    SELECT
        CAST(Fecha AS date) AS Fecha,
        Torre,
        Turno,
        AVG(CAST(Humedad_Prom_Pct AS float)) AS Humedad_Prom_Pct
    INTO #hum
    FROM inventar_SpcHidr.Informe_TM_lab
    WHERE Humedad_Prom_Pct IS NOT NULL
      AND CAST(Fecha AS date) <= @fecha_fin
    GROUP BY
        CAST(Fecha AS date),
        Torre,
        Turno;

    CREATE CLUSTERED INDEX IX_hum
    ON #hum (Fecha, Torre, Turno);

    /* ============================================================
       BLOQUE 3: HUMEDAD + REPRESENTATIVIDAD FÍSICA
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
    LEFT JOIN inventar_SpcHidr.v_representatividad_diaria_calculada r
        ON r.Dia = h.Fecha;

    CREATE CLUSTERED INDEX IX_hum_rep
    ON #hum_rep (Fecha, Torre, Turno);

    /* ============================================================
       BLOQUE 4: ÚLTIMA HUMEDAD REPRESENTATIVA POR TORRE/DÍA
       ============================================================ */

    SELECT
        Fecha,
        Torre,
        Turno AS Turno_Humedad,
        Humedad_Prom_Pct AS Humedad_Torre_Dia,
        Representatividad_Fisica,
        ROW_NUMBER() OVER (
            PARTITION BY Fecha, Torre
            ORDER BY CASE WHEN Turno = 'B' THEN 2 ELSE 1 END DESC
        ) AS rn
    INTO #hum_torre_dia
    FROM #hum_rep
    WHERE Humedad_Prom_Pct IS NOT NULL
      AND Representatividad_Fisica >= 0.75;

    CREATE CLUSTERED INDEX IX_hum_torre_dia
    ON #hum_torre_dia (Fecha, Torre, rn);

    SELECT
        Fecha,
        Torre,
        Turno_Humedad,
        Humedad_Torre_Dia,
        Representatividad_Fisica
    INTO #hum_torre_dia_final
    FROM #hum_torre_dia
    WHERE rn = 1;

    CREATE CLUSTERED INDEX IX_hum_torre_dia_final
    ON #hum_torre_dia_final (Fecha, Torre);

    /* ============================================================
       BLOQUE 5: CANDIDATOS DE HUMEDAD
       ============================================================ */

    SELECT
        Fecha,
        'TM1' AS TM,
        Torre,
        Turno_Humedad,
        Humedad_Torre_Dia,
        Representatividad_Fisica,
        'PROPIA_TM1' AS Fuente_Humedad,
        1 AS Prioridad_Misma_Fecha
    INTO #candidatos
    FROM #hum_torre_dia_final
    WHERE Torre = 'T1'

    UNION ALL

    SELECT
        Fecha,
        'TM2' AS TM,
        Torre,
        Turno_Humedad,
        Humedad_Torre_Dia,
        Representatividad_Fisica,
        'PROPIA_TM2' AS Fuente_Humedad,
        2 AS Prioridad_Misma_Fecha
    FROM #hum_torre_dia_final
    WHERE Torre = 'T2'

    UNION ALL

    SELECT
        Fecha,
        'TM2' AS TM,
        Torre,
        Turno_Humedad,
        Humedad_Torre_Dia,
        Representatividad_Fisica,
        'ALINEADA_DESDE_TM1' AS Fuente_Humedad,
        1 AS Prioridad_Misma_Fecha
    FROM #hum_torre_dia_final
    WHERE Torre = 'T1'

    UNION ALL

    SELECT
        fecha_origen AS Fecha,
        tm AS TM,
        torre AS Torre,
        CAST(NULL AS varchar(10)) AS Turno_Humedad,
        humedad_pct AS Humedad_Torre_Dia,
        1.0 AS Representatividad_Fisica,
        'HUMEDAD_INICIAL_PERIODO' AS Fuente_Humedad,
        0 AS Prioridad_Misma_Fecha
    FROM inventar_SpcHidr.humedad_inicial_tm_periodo;

    CREATE CLUSTERED INDEX IX_candidatos
    ON #candidatos (TM, Fecha DESC, Prioridad_Misma_Fecha DESC);

    /* ============================================================
       BLOQUE 6: HUMEDAD RESUELTA POR FECHA
       ============================================================ */

    SELECT
        f.*,

        tm1.Humedad_Torre_Dia AS Humedad_TM1,
        tm1.Fecha AS Fecha_Humedad_TM1,
        tm1.Torre AS Torre_Humedad_TM1,
        tm1.Turno_Humedad AS Turno_Humedad_TM1,
        tm1.Fuente_Humedad AS Fuente_Humedad_TM1,

        tm2.Humedad_Torre_Dia AS Humedad_TM2,
        tm2.Fecha AS Fecha_Humedad_TM2,
        tm2.Torre AS Torre_Humedad_TM2,
        tm2.Turno_Humedad AS Turno_Humedad_TM2,
        tm2.Fuente_Humedad AS Fuente_Humedad_TM2

    INTO #humedad_resuelta
    FROM #fechas f

    OUTER APPLY (
        SELECT TOP (1) c.*
        FROM #candidatos c
        WHERE c.TM = 'TM1'
          AND c.Fecha <= f.Fecha
        ORDER BY
            c.Fecha DESC,
            c.Prioridad_Misma_Fecha DESC
    ) tm1

    OUTER APPLY (
        SELECT TOP (1) c.*
        FROM #candidatos c
        WHERE c.TM = 'TM2'
          AND c.Fecha <= f.Fecha
        ORDER BY
            c.Fecha DESC,
            c.Prioridad_Misma_Fecha DESC
    ) tm2;

    CREATE CLUSTERED INDEX IX_humedad_resuelta
    ON #humedad_resuelta (Fecha);

    /* ============================================================
   BLOQUE 7: FACTOR DE AJUSTE CAMIONES + CÁLCULO TMS CON SAL/SRR
   ============================================================ */

DROP TABLE IF EXISTS #base_tms;
DROP TABLE IF EXISTS #tms_con_sal;

SELECT
    h.*,
    COALESCE(fac.factor_ajuste, 1.0) AS Factor_Ajuste_Camiones_Usado,

    h.TMH_Apilado_Total_A   * COALESCE(fac.factor_ajuste, 1.0) AS TMH_Apilado_Total_A_Factor,
    h.TMH_Apilado_Total_B   * COALESCE(fac.factor_ajuste, 1.0) AS TMH_Apilado_Total_B_Factor,
    h.TMH_Apilado_Total_Dia * COALESCE(fac.factor_ajuste, 1.0) AS TMH_Apilado_Total_Dia_Factor

INTO #base_tms
FROM #humedad_resuelta h
OUTER APPLY (
    SELECT TOP (1)
        f.factor_ajuste
    FROM inventar_SpcHidr.factor_ajuste_camiones f
    WHERE f.activo = 1
      AND h.Fecha >= f.fecha_inicio
      AND (f.fecha_fin IS NULL OR h.Fecha <= f.fecha_fin)
    ORDER BY
        f.fecha_inicio DESC,
        f.id_factor DESC
) fac;

CREATE CLUSTERED INDEX IX_base_tms
ON #base_tms (Fecha);

SELECT
    x.*,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
        THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A + x.TMS_TM2_Con_Sal_SRR_A
    END AS TMS_Total_Con_Sal_SRR_A,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
        THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_B + x.TMS_TM2_Con_Sal_SRR_B
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
FROM (
    SELECT
        b.*,

        CASE
            WHEN b.TMH_CV008_A = 0 THEN 0
            WHEN b.Humedad_TM1 IS NULL THEN NULL
            ELSE b.TMH_CV008_A * (1 - b.Humedad_TM1 / 100.0)
        END AS TMS_TM1_Con_Sal_SRR_A,

        CASE
            WHEN b.TMH_CV008_B = 0 THEN 0
            WHEN b.Humedad_TM1 IS NULL THEN NULL
            ELSE b.TMH_CV008_B * (1 - b.Humedad_TM1 / 100.0)
        END AS TMS_TM1_Con_Sal_SRR_B,

        CASE
            WHEN b.TMH_CV108_A = 0 THEN 0
            WHEN b.Humedad_TM2 IS NULL THEN NULL
            ELSE b.TMH_CV108_A * (1 - b.Humedad_TM2 / 100.0)
        END AS TMS_TM2_Con_Sal_SRR_A,

        CASE
            WHEN b.TMH_CV108_B = 0 THEN 0
            WHEN b.Humedad_TM2 IS NULL THEN NULL
            ELSE b.TMH_CV108_B * (1 - b.Humedad_TM2 / 100.0)
        END AS TMS_TM2_Con_Sal_SRR_B,

        CASE
            WHEN b.TMH_Apilado_Total_Dia = 0 THEN 0
            WHEN b.Humedad_TM1 IS NULL OR b.Humedad_TM2 IS NULL THEN NULL
            ELSE (
                b.TMH_CV008_A * b.Humedad_TM1 +
                b.TMH_CV008_B * b.Humedad_TM1 +
                b.TMH_CV108_A * b.Humedad_TM2 +
                b.TMH_CV108_B * b.Humedad_TM2
            ) / NULLIF(b.TMH_Apilado_Total_Dia, 0)
        END AS Humedad_Equivalente_Dia

    FROM #base_tms b
) x;

CREATE CLUSTERED INDEX IX_tms_con_sal
ON #tms_con_sal (Fecha);
/* ============================================================
   BLOQUE 8: SAL AJUSTADA + DESCUENTO DE SAL
   ============================================================ */

DROP TABLE IF EXISTS #sal_ajustada;
DROP TABLE IF EXISTS #tms_sin_sal;

SELECT
    Fecha,
    Sal_Pesometros_TA,
    Sal_Pesometros_TB,
    Sal_Pesometros_Dia,
    Sal_Topografia_Dia,
    Flag_Sal_Basica_Valida,
    Flag_Sal_Ajuste_Valido,
    Sal_Ajustada_TA,
    Sal_Ajustada_TB,
    Sal_Ajustada_Dia
INTO #sal_ajustada
FROM inventar_SpcHidr.v_sal_ajustada
WHERE Fecha >= @fecha_inicio
  AND Fecha <  @fecha_fin;

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

SELECT *
INTO #leyes_base
FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
WHERE Fecha >= @fecha_inicio
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
   BLOQUE 10A: RESOLUCIÓN DIARIA DE FeS

   Regla:
   1. Toda medición con representatividad química >= 75 %
      es válida y reemplaza cualquier arrastre anterior.
   2. Si una TM tiene dato en un turno, se comparte al otro
      turno de la misma TM.
   3. Si solo una TM tiene dato representativo durante el día,
      se comparte también a la otra TM.
   4. Si ambas TM tienen valores representativos, cada TM
      conserva su propio valor.
   5. El arrastre se aplica después de resolver el día.
   ============================================================ */

DROP TABLE IF EXISTS #fes_candidatos_dia;
DROP TABLE IF EXISTS #fes_dia_resuelta;


/* ------------------------------------------------------------
   Candidatos originales válidos

   TORRE_MISMO_TURNO:
   dato que realmente cumplió representatividad química.

   SEMILLA_INICIO_PERIODO:
   valor inicial para mantener continuidad del periodo.

   No se usa TORRE_OTRO_TURNO_MISMO_DIA como candidato original,
   porque la compartición entre turnos se reconstruye aquí.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,
    b.FeS,
    b.Fuente_FeS AS Fuente_Origen
INTO #fes_candidatos_dia
FROM #leyes_base b
WHERE b.FeS IS NOT NULL
  AND b.Fuente_FeS IN (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );

CREATE CLUSTERED INDEX IX_fes_candidatos_dia
ON #fes_candidatos_dia
(
    Fecha,
    TM_Origen,
    Turno_Origen
);


/* ------------------------------------------------------------
   Resolver cada posición Fecha + Turno + TM

   Prioridad:
   1. Misma TM y mismo turno.
   2. Misma TM y otro turno.
   3. Otra TM y mismo turno.
   4. Otra TM y otro turno.

   Una medición representativa siempre tiene prioridad
   sobre una semilla.
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

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA'

        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen <> b.Turno
            THEN 'TORRE_REP_QUIMICA_OTRO_TURNO'

        WHEN c.TM_Origen <> b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM'

        ELSE
            'TORRE_REP_QUIMICA_COMPARTIDA_TM_TURNO'
    END AS Fuente_Nuevo_Dia

INTO #fes_dia_resuelta
FROM #leyes_base b

OUTER APPLY (
    SELECT TOP (1)
        x.FeS,
        x.TM_Origen,
        x.Turno_Origen,
        x.Fuente_Origen
    FROM #fes_candidatos_dia x
    WHERE x.Fecha = b.Fecha
    ORDER BY
        /* Una medición representativa reemplaza la semilla */
        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 9
        END,

        /* Prioridad de ubicación */
        CASE
            WHEN x.TM_Origen = b.TM
             AND x.Turno_Origen = b.Turno
                THEN 1

            WHEN x.TM_Origen = b.TM
             AND x.Turno_Origen <> b.Turno
                THEN 2

            WHEN x.TM_Origen <> b.TM
             AND x.Turno_Origen = b.Turno
                THEN 3

            ELSE 4
        END
) c;

CREATE CLUSTERED INDEX IX_fes_dia_resuelta
ON #fes_dia_resuelta
(
    TM,
    Turno,
    Fecha
);

/* ============================================================
   BLOQUE 11A: MALLA -1/2 CANDIDATA Y COMPARTIBLE RN-027

   Criterio:
   - Malla -1/2 no cae a Conciliación Chancado.
   - Solo entra como dato nuevo si viene desde torre ya validada
     físicamente en la vista base.
   - Si una sola TM tiene valor válido el día, se comparte a ambas TM.
   - Si ambas TM tienen valor válido el día, cada TM conserva el suyo.
   - Si no hay nuevo valor válido, se arrastra el último valor válido.
   ============================================================ */

DROP TABLE IF EXISTS #malla12_candidata_dia_tm;

WITH candidatos AS (
    SELECT
        b.Fecha,
        b.Turno,
        b.TM,
        b.Malla_Menos_1_2,
        b.Fuente_Malla_Menos_1_2,
        ROW_NUMBER() OVER (
            PARTITION BY b.Fecha, b.TM
            ORDER BY
                CASE
                    WHEN b.Fuente_Malla_Menos_1_2 = 'TORRE_MISMO_TURNO' THEN 3
                    WHEN b.Fuente_Malla_Menos_1_2 = 'TORRE_OTRO_TURNO_MISMO_DIA' THEN 2
                    WHEN b.Fuente_Malla_Menos_1_2 = 'SEMILLA_INICIO_PERIODO' THEN 1
                    ELSE 0
                END DESC,
                CASE WHEN b.Turno = 'B' THEN 2 ELSE 1 END DESC
        ) AS rn
    FROM #leyes_base b
    WHERE b.Malla_Menos_1_2 IS NOT NULL
      AND b.Malla_Menos_1_2 <> 0
      AND b.Fuente_Malla_Menos_1_2 <> 'NO_APLICA_MINA'
)
SELECT
    Fecha,
    TM,
    TM AS TM_Origen,
    Turno AS Turno_Fuente,
    Malla_Menos_1_2,
    Fuente_Malla_Menos_1_2 AS Fuente_Origen
INTO #malla12_candidata_dia_tm
FROM candidatos
WHERE rn = 1;

CREATE CLUSTERED INDEX IX_malla12_candidata_fecha_tm
ON #malla12_candidata_dia_tm (Fecha, TM);

DROP TABLE IF EXISTS #malla12_dia_resuelta;

WITH fechas AS (
    SELECT DISTINCT Fecha
    FROM #leyes_base
)
SELECT
    f.Fecha,
    'TM1' AS TM,
    COALESCE(tm1.Malla_Menos_1_2, tm2.Malla_Menos_1_2) AS Malla_Menos_1_2,
    CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN 'TM1'
         WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN 'TM2'
    END AS TM_Origen,
    CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Turno_Fuente
         WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Turno_Fuente
    END AS Turno_Fuente,
    CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Fuente_Origen
         WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Fuente_Origen
    END AS Fuente_Origen
INTO #malla12_dia_resuelta
FROM fechas f
LEFT JOIN #malla12_candidata_dia_tm tm1
    ON tm1.Fecha = f.Fecha
   AND tm1.TM = 'TM1'
LEFT JOIN #malla12_candidata_dia_tm tm2
    ON tm2.Fecha = f.Fecha
   AND tm2.TM = 'TM2'

UNION ALL

SELECT
    f.Fecha,
    'TM2' AS TM,
    COALESCE(tm2.Malla_Menos_1_2, tm1.Malla_Menos_1_2) AS Malla_Menos_1_2,
    CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN 'TM2'
         WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN 'TM1'
    END AS TM_Origen,
    CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Turno_Fuente
         WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Turno_Fuente
    END AS Turno_Fuente,
    CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Fuente_Origen
         WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Fuente_Origen
    END AS Fuente_Origen
FROM fechas f
LEFT JOIN #malla12_candidata_dia_tm tm1
    ON tm1.Fecha = f.Fecha
   AND tm1.TM = 'TM1'
LEFT JOIN #malla12_candidata_dia_tm tm2
    ON tm2.Fecha = f.Fecha
   AND tm2.TM = 'TM2';

CREATE CLUSTERED INDEX IX_malla12_dia_resuelta_fecha_tm
ON #malla12_dia_resuelta (Fecha, TM);

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

    CASE
        WHEN b.ConsH IS NOT NULL
         AND b.ConsH <> 0
         AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
        THEN b.ConsH
        ELSE ult_consh.ConsH
    END AS ConsH,

    CASE
        WHEN b.ConsH IS NOT NULL
         AND b.ConsH <> 0
         AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
        THEN b.Fuente_ConsH
        WHEN ult_consh.ConsH IS NOT NULL
        THEN 'ARRASTRE_ULTIMO_VALIDO'
        ELSE b.Fuente_ConsH
    END AS Fuente_ConsH,

    ult_malla.Malla_Menos_1_2 AS Malla_Menos_1_2,

    CASE
        WHEN ult_malla.Malla_Menos_1_2 IS NULL
            THEN b.Fuente_Malla_Menos_1_2

        WHEN ult_malla.Fecha = b.Fecha
         AND ult_malla.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        WHEN ult_malla.Fecha = b.Fecha
         AND ult_malla.TM_Origen = b.TM
            THEN 'TORRE_REP_FISICA'

        WHEN ult_malla.Fecha = b.Fecha
         AND ult_malla.TM_Origen <> b.TM
            THEN 'TORRE_REP_FISICA_COMPARTIDA'

        WHEN ult_malla.Fecha < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        ELSE b.Fuente_Malla_Menos_1_2
    END AS Fuente_Malla_Menos_1_2,

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

OUTER APPLY (
    SELECT TOP 1
        x.ConsH
    FROM #leyes_base x
    WHERE x.TM = b.TM
      AND x.Fecha <= b.Fecha
      AND x.ConsH IS NOT NULL
      AND x.ConsH <> 0
      AND x.Fuente_ConsH <> 'NO_APLICA_MINA'
    ORDER BY
        x.Fecha DESC,
        CASE WHEN x.Turno = b.Turno THEN 0 ELSE 1 END
) ult_consh

OUTER APPLY (
    SELECT TOP 1
        d.Fecha,
        d.TM_Origen,
        d.Turno_Fuente,
        d.Malla_Menos_1_2,
        d.Fuente_Origen
    FROM #malla12_dia_resuelta d
    WHERE d.TM = b.TM
      AND d.Fecha <= b.Fecha
      AND d.Malla_Menos_1_2 IS NOT NULL
    ORDER BY d.Fecha DESC
) ult_malla;

CREATE CLUSTERED INDEX IX_leyes_v2_fecha_turno_tm
ON #leyes_v2 (Fecha, Turno, TM);
/* ============================================================
   BLOQUE 12: PONDERACIÓN DE LEYES REALES POR TMS
   ============================================================ */

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
   ============================================================ */

DROP TABLE IF EXISTS #muestras;

WITH fuentes AS (
    SELECT
        Fecha,
        Turno,

        MAX(CASE WHEN Fuente_CuT LIKE '%TORRE%' 
                   OR Fuente_CuS LIKE '%TORRE%'
                   OR Fuente_CO3 LIKE '%TORRE%'
                   OR Fuente_CuFe LIKE '%TORRE%'
                   OR Fuente_FeT LIKE '%TORRE%'
                 THEN 1 ELSE 0 END) AS Quimica_Torre,

        MAX(CASE WHEN Fuente_CuT = 'MINA'
                   OR Fuente_CuS = 'MINA'
                   OR Fuente_CO3 = 'MINA'
                   OR Fuente_CuFe = 'MINA'
                   OR Fuente_FeT = 'MINA'
                 THEN 1 ELSE 0 END) AS Quimica_Mina,

        MAX(CASE WHEN Fuente_FeS = 'ARRASTRE_ULTIMO_VALIDO'
                   OR Fuente_ConsH = 'ARRASTRE_ULTIMO_VALIDO'
                 THEN 1 ELSE 0 END) AS Quimica_Arrastre,

        MAX(CASE WHEN Fuente_CuT = 'SEMILLA_INICIO_PERIODO'
                   OR Fuente_CuS = 'SEMILLA_INICIO_PERIODO'
                   OR Fuente_CO3 = 'SEMILLA_INICIO_PERIODO'
                   OR Fuente_CuFe = 'SEMILLA_INICIO_PERIODO'
                   OR Fuente_FeT = 'SEMILLA_INICIO_PERIODO'
                   OR Fuente_FeS = 'SEMILLA_INICIO_PERIODO'
                   OR Fuente_ConsH = 'SEMILLA_INICIO_PERIODO'
                 THEN 1 ELSE 0 END) AS Quimica_Semilla,

        MAX(CASE WHEN Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                   OR Fuente_Malla_Menos_100 LIKE '%TORRE%'
                 THEN 1 ELSE 0 END) AS Fisica_Torre,

        MAX(CASE WHEN Fuente_Malla_Menos_1_2 = 'MINA'
                   OR Fuente_Malla_Menos_100 = 'MINA'
                 THEN 1 ELSE 0 END) AS Fisica_Mina,

        MAX(CASE WHEN Fuente_Malla_Menos_1_2 = 'ARRASTRE_ULTIMO_VALIDO'
                 THEN 1 ELSE 0 END) AS Fisica_Arrastre,

        MAX(CASE WHEN Fuente_Malla_Menos_1_2 = 'SEMILLA_INICIO_PERIODO'
                   OR Fuente_Malla_Menos_100 = 'SEMILLA_INICIO_PERIODO'
                 THEN 1 ELSE 0 END) AS Fisica_Semilla

    FROM #leyes_v2
    GROUP BY Fecha, Turno
)

SELECT
    Fecha,
    Turno,

    CASE
        WHEN Quimica_Semilla = 1 THEN 'SEMILLA'
        WHEN Quimica_Arrastre = 1 AND (Quimica_Torre = 1 OR Quimica_Mina = 1) THEN 'MIXTA'
        WHEN Quimica_Torre = 1 AND Quimica_Mina = 1 THEN 'MIXTA'
        WHEN Quimica_Arrastre = 1 THEN 'ARRASTRE'
        WHEN Quimica_Torre = 1 THEN 'TORRE'
        WHEN Quimica_Mina = 1 THEN 'MINA'
        ELSE NULL
    END AS Muestra_Quimica,

    CASE
        WHEN Fisica_Semilla = 1 THEN 'SEMILLA'
        WHEN Fisica_Arrastre = 1 AND (Fisica_Torre = 1 OR Fisica_Mina = 1) THEN 'MIXTA'
        WHEN Fisica_Torre = 1 AND Fisica_Mina = 1 THEN 'MIXTA'
        WHEN Fisica_Arrastre = 1 THEN 'ARRASTRE'
        WHEN Fisica_Torre = 1 THEN 'TORRE'
        WHEN Fisica_Mina = 1 THEN 'MINA'
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
   ============================================================ */

/*
    IMPORTANTE:
    Aquí debes pegar la consulta que ya generaste y que entrega estas columnas:

    Fecha
    Turno
    Prop_Final_Stock
    Prop_Final_Mina
    Prop_Final_SRR
    Prop_Final_Total
    Check_Distribucion_Apilado

    Esa es la consulta que te dio el resultado con:
    Ton_Stock_Camiones, Ton_Mina_Camiones, TMS_SRR,
    Apilado_TMS_Con_SRR, Prop_Final_Stock, Prop_Final_Mina y Prop_Final_SRR.
*/

SELECT
    CAST(q.Fecha AS date) AS Fecha,
    q.Turno,

    CAST(COALESCE(q.Prop_Final_Stock, 0) AS decimal(18, 8)) AS Prop_Final_Stock,
    CAST(COALESCE(q.Prop_Final_Mina, 0) AS decimal(18, 8)) AS Prop_Final_Mina,
    CAST(COALESCE(q.Prop_Final_SRR, 0) AS decimal(18, 8)) AS Prop_Final_SRR,

    CAST(COALESCE(q.Prop_Final_Total, 0) AS decimal(18, 8)) AS Prop_Final_Total,
    CAST(COALESCE(q.Check_Distribucion_Apilado, 0) AS decimal(18, 8)) AS Check_Distribucion_Apilado

INTO #origen_apilado
FROM (
    SELECT
        Fecha,
        Turno,
        Prop_Final_Stock,
        Prop_Final_Mina,
        Prop_Final_SRR,
        Prop_Final_Total,
        Check_Distribucion_Apilado
    FROM inventar_SpcHidr.v_apilado_proporcion_final_reporte_test
) q
WHERE CAST(q.Fecha AS date) >= @fecha_inicio
  AND CAST(q.Fecha AS date) <  @fecha_fin;

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
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
          OR r.Solubilidad_Real IS NULL
          OR r.CO3_Real IS NULL
            THEN NULL

        WHEN r.Solubilidad_Real <= 0.25
            THEN 9 + 16.33 * r.CO3_Real * 0.95

        WHEN r.Solubilidad_Real > 0.25
          AND r.CuS_Real > 0
            THEN 8.182 * LOG(r.CuS_Real)
               + 18.997
               + 16.33 * r.CO3_Real * 0.95
               + 2

        ELSE NULL
    END
AS decimal(18, 2)) AS Dosis_Acido_Ideal_TM,

CAST(
    COALESCE(
        CASE
            WHEN COALESCE(ps.Solubilidad_Plan_Semanal, 0) <= 0.25
                THEN 9 + 16.33 * COALESCE(ps.CO3_Plan_Semanal, 0) * 0.95

            WHEN ps.Solubilidad_Plan_Semanal > 0.25
                AND ps.CuS_Plan_Semanal > 0
                    THEN 8.182 * LOG(ps.CuS_Plan_Semanal)
                   + 18.997
                   + 16.33 * COALESCE(ps.CO3_Plan_Semanal, 0) * 0.95
                   + 2

            ELSE 0
        END,
        0
    )
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
    m.Muestra_Quimica,
    m.Muestra_Fisica

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

