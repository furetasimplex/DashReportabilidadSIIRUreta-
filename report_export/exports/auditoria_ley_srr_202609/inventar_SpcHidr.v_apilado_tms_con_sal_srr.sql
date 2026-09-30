
CREATE   VIEW
    [inventar_SpcHidr].[v_apilado_tms_con_sal_srr]
AS

WITH fechas AS
(
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

    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2
),

/* ============================================================
   HUMEDAD INFORMADA POR LABORATORIO
   ============================================================ */
hum AS
(
    SELECT
        CAST(Fecha AS date) AS Fecha,
        Torre,
        Turno,

        AVG
        (
            CAST(Humedad_Prom_Pct AS float)
        ) AS Humedad_Prom_Pct

    FROM inventar_SpcHidr.Informe_TM_lab

    WHERE Humedad_Prom_Pct IS NOT NULL

    GROUP BY
        CAST(Fecha AS date),
        Torre,
        Turno
),

/* ============================================================
   HUMEDAD + REPRESENTATIVIDAD FÍSICA
   ============================================================ */
hum_rep AS
(
    SELECT
        h.Fecha,
        h.Torre,
        h.Turno,
        h.Humedad_Prom_Pct,

        CASE
            WHEN h.Torre = 'T1'
             AND h.Turno = 'A'
                THEN r.TM1_TurnoA_Fisico

            WHEN h.Torre = 'T1'
             AND h.Turno = 'B'
                THEN r.TM1_TurnoB_Fisico

            WHEN h.Torre = 'T2'
             AND h.Turno = 'A'
                THEN r.TM2_TurnoA_Fisico

            WHEN h.Torre = 'T2'
             AND h.Turno = 'B'
                THEN r.TM2_TurnoB_Fisico
        END AS Representatividad_Fisica

    FROM hum AS h

    LEFT JOIN inventar_SpcHidr.v_representatividad_diaria_calculada AS r
        ON r.Dia = h.Fecha
),

/* ============================================================
   HUMEDADES REPRESENTATIVAS POR FECHA + TURNO
   ============================================================ */
hum_validas AS
(
    SELECT
        Fecha,
        Torre,
        Turno,
        Humedad_Prom_Pct,
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

    FROM hum_rep

    WHERE Humedad_Prom_Pct IS NOT NULL
      AND Representatividad_Fisica >= 0.75
),

/* ============================================================
   PERIODOS A/B QUE DEBEN RESOLVERSE
   ============================================================ */
periodos AS
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

    FROM fechas AS f

    CROSS JOIN
    (
        VALUES
            ('A'),
            ('B')
    ) AS t(Turno_Objetivo)
),

/* ============================================================
   RESOLUCIÓN CRONOLÓGICA POR FECHA + TURNO
   ============================================================ */
resuelta_turno AS
(
    SELECT
        p.Fecha,
        p.Turno_Objetivo,

        /* TM1 */
        tm1.Humedad_Prom_Pct
            AS Humedad_TM1,

        tm1.Fecha
            AS Fecha_Origen_TM1,

        tm1.Torre
            AS Torre_Origen_TM1,

        tm1.Turno
            AS Turno_Origen_TM1,

        tm1.Fuente_Humedad
            AS Fuente_Humedad_TM1,

        /* TM2 */
        tm2.Humedad_Prom_Pct
            AS Humedad_TM2,

        tm2.Fecha
            AS Fecha_Origen_TM2,

        tm2.Torre
            AS Torre_Origen_TM2,

        tm2.Turno
            AS Turno_Origen_TM2,

        tm2.Fuente_Humedad
            AS Fuente_Humedad_TM2

    FROM periodos AS p

    /* ========================================================
       HUMEDAD RESUELTA PARA TM1
       ======================================================== */
    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno,
            c.Humedad_Prom_Pct,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno,
                h.Humedad_Prom_Pct,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T1'
                            THEN 'PROPIA_TM1'
                        ELSE 'ALINEADA_DESDE_TM2'
                    END
                    AS varchar(18)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T1' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM hum_validas AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(5)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'SEMILLA_PERIODO'
                    AS varchar(18)
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

    /* ========================================================
       HUMEDAD RESUELTA PARA TM2
       ======================================================== */
    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno,
            c.Humedad_Prom_Pct,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno,
                h.Humedad_Prom_Pct,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T2'
                            THEN 'PROPIA_TM2'
                        ELSE 'ALINEADA_DESDE_TM1'
                    END
                    AS varchar(18)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T2' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM hum_validas AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(5)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'SEMILLA_PERIODO'
                    AS varchar(18)
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
   PIVOT A/B A UNA FILA DIARIA

   Las cuatro humedades por turno quedan disponibles internamente.
   Humedad_TM1 y Humedad_TM2 representan el valor vigente al
   cierre del día para mantener compatibilidad.
   ============================================================ */
humedad_resuelta AS
(
    SELECT
        f.*,

        /* Humedades TM1 por turno */
        a.Humedad_TM1 AS Humedad_TM1_A,
        b.Humedad_TM1 AS Humedad_TM1_B,

        /* Humedades TM2 por turno */
        a.Humedad_TM2 AS Humedad_TM2_A,
        b.Humedad_TM2 AS Humedad_TM2_B,

        /* Valor vigente al cierre del día */
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

    FROM fechas AS f

    LEFT JOIN resuelta_turno AS a
        ON a.Fecha = f.Fecha
       AND a.Turno_Objetivo = 'A'

    LEFT JOIN resuelta_turno AS b
        ON b.Fecha = f.Fecha
       AND b.Turno_Objetivo = 'B'
),

/* ============================================================
   FACTOR DE AJUSTE DE CAMIONES
   ============================================================ */
base AS
(
    SELECT
        h.*,

        COALESCE
        (
            fac.factor_ajuste,
            1.0
        ) AS Factor_Ajuste_Camiones_Usado,

        h.TMH_Apilado_Total_A
        * COALESCE(fac.factor_ajuste, 1.0)
            AS TMH_Apilado_Total_A_Factor,

        h.TMH_Apilado_Total_B
        * COALESCE(fac.factor_ajuste, 1.0)
            AS TMH_Apilado_Total_B_Factor,

        h.TMH_Apilado_Total_Dia
        * COALESCE(fac.factor_ajuste, 1.0)
            AS TMH_Apilado_Total_Dia_Factor

    FROM humedad_resuelta AS h

    OUTER APPLY
    (
        SELECT TOP (1)
            f.factor_ajuste

        FROM inventar_SpcHidr.factor_ajuste_camiones AS f

        WHERE f.activo = 1
          AND h.Fecha >= f.fecha_inicio
          AND
          (
              f.fecha_fin IS NULL
              OR h.Fecha <= f.fecha_fin
          )

        ORDER BY
            f.fecha_inicio DESC,
            f.id_factor DESC

    ) AS fac
),

/* ============================================================
   CÁLCULO DE TMS POR TORRE Y TURNO
   ============================================================ */
tms AS
(
    SELECT
        b.*,

        CASE
            WHEN b.TMH_CV008_A = 0
                THEN 0

            WHEN b.Humedad_TM1_A IS NULL
                THEN NULL

            ELSE
                b.TMH_CV008_A
                * (1 - b.Humedad_TM1_A / 100.0)
        END AS TMS_CV008_A,

        CASE
            WHEN b.TMH_CV008_B = 0
                THEN 0

            WHEN b.Humedad_TM1_B IS NULL
                THEN NULL

            ELSE
                b.TMH_CV008_B
                * (1 - b.Humedad_TM1_B / 100.0)
        END AS TMS_CV008_B,

        CASE
            WHEN b.TMH_CV108_A = 0
                THEN 0

            WHEN b.Humedad_TM2_A IS NULL
                THEN NULL

            ELSE
                b.TMH_CV108_A
                * (1 - b.Humedad_TM2_A / 100.0)
        END AS TMS_CV108_A,

        CASE
            WHEN b.TMH_CV108_B = 0
                THEN 0

            WHEN b.Humedad_TM2_B IS NULL
                THEN NULL

            ELSE
                b.TMH_CV108_B
                * (1 - b.Humedad_TM2_B / 100.0)
        END AS TMS_CV108_B

    FROM base AS b
)

SELECT
    Fecha,

    Flag_Apilado_Valido,

    Factor_Ajuste_Camiones_Usado,

    /* Humedad vigente al cierre del día */
    Humedad_TM1,
    Humedad_TM2,

    /* Humedad equivalente ponderada usando A/B */
    CASE
        WHEN TMH_Apilado_Total_Dia = 0
            THEN 0

        WHEN TMH_CV008_A > 0
         AND Humedad_TM1_A IS NULL
            THEN NULL

        WHEN TMH_CV008_B > 0
         AND Humedad_TM1_B IS NULL
            THEN NULL

        WHEN TMH_CV108_A > 0
         AND Humedad_TM2_A IS NULL
            THEN NULL

        WHEN TMH_CV108_B > 0
         AND Humedad_TM2_B IS NULL
            THEN NULL

        ELSE
            (
                  TMH_CV008_A * Humedad_TM1_A
                + TMH_CV008_B * Humedad_TM1_B
                + TMH_CV108_A * Humedad_TM2_A
                + TMH_CV108_B * Humedad_TM2_B
            )
            /
            NULLIF
            (
                TMH_Apilado_Total_Dia,
                0
            )
    END AS Humedad_Equivalente_Dia,

    /* Trazabilidad TM1 */
    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,

    /* Trazabilidad TM2 */
    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2,

    /* TMH por torre */
    TMH_CV008_A AS TMH_TM1_Con_Sal_SRR_A,
    TMH_CV008_B AS TMH_TM1_Con_Sal_SRR_B,
    TMH_CV108_A AS TMH_TM2_Con_Sal_SRR_A,
    TMH_CV108_B AS TMH_TM2_Con_Sal_SRR_B,

    /* TMH total */
    TMH_Apilado_Total_A
        AS TMH_Total_Con_Sal_SRR_A,

    TMH_Apilado_Total_B
        AS TMH_Total_Con_Sal_SRR_B,

    TMH_Apilado_Total_Dia
        AS TMH_Total_Con_Sal_SRR_Dia,

    /* TMH con factor */
    TMH_Apilado_Total_A_Factor
        AS TMH_Total_Con_Factor_A,

    TMH_Apilado_Total_B_Factor
        AS TMH_Total_Con_Factor_B,

    TMH_Apilado_Total_Dia_Factor
        AS TMH_Total_Con_Factor_Dia,

    /* Controles del factor */
    TMH_Apilado_Total_A_Factor
      - TMH_Apilado_Total_A
        AS Check_Factor_TMH_A,

    TMH_Apilado_Total_B_Factor
      - TMH_Apilado_Total_B
        AS Check_Factor_TMH_B,

    TMH_Apilado_Total_Dia_Factor
      - TMH_Apilado_Total_Dia
        AS Check_Factor_TMH_Dia,

    /* TMS por torre */
    TMS_CV008_A AS TMS_TM1_Con_Sal_SRR_A,
    TMS_CV008_B AS TMS_TM1_Con_Sal_SRR_B,
    TMS_CV108_A AS TMS_TM2_Con_Sal_SRR_A,
    TMS_CV108_B AS TMS_TM2_Con_Sal_SRR_B,

    /* TMS turno A */
    CASE
        WHEN TMS_CV008_A IS NULL
          OR TMS_CV108_A IS NULL
            THEN NULL

        ELSE
            TMS_CV008_A
          + TMS_CV108_A
    END AS TMS_Total_Con_Sal_SRR_A,

    /* TMS turno B */
    CASE
        WHEN TMS_CV008_B IS NULL
          OR TMS_CV108_B IS NULL
            THEN NULL

        ELSE
            TMS_CV008_B
          + TMS_CV108_B
    END AS TMS_Total_Con_Sal_SRR_B,

    /* TMS día */
    CASE
        WHEN TMS_CV008_A IS NULL
          OR TMS_CV008_B IS NULL
          OR TMS_CV108_A IS NULL
          OR TMS_CV108_B IS NULL
            THEN NULL

        ELSE
              TMS_CV008_A
            + TMS_CV008_B
            + TMS_CV108_A
            + TMS_CV108_B
    END AS TMS_Total_Con_Sal_SRR_Dia,

    /* Flag de validez */
    CASE
        WHEN Flag_Apilado_Valido = 0
            THEN 0

        WHEN TMH_CV008_A > 0
         AND Humedad_TM1_A IS NULL
            THEN 0

        WHEN TMH_CV008_B > 0
         AND Humedad_TM1_B IS NULL
            THEN 0

        WHEN TMH_CV108_A > 0
         AND Humedad_TM2_A IS NULL
            THEN 0

        WHEN TMH_CV108_B > 0
         AND Humedad_TM2_B IS NULL
            THEN 0

        ELSE 1
    END AS Flag_TMS_Valido,

    /* Observación */
    CASE
        WHEN Flag_Apilado_Valido = 0
            THEN 'APILADO_TMH_INVALIDO_O_CERO'

        WHEN TMH_CV008_A > 0
         AND Humedad_TM1_A IS NULL
            THEN 'SIN_HUMEDAD_REPRESENTATIVA_TM1'

        WHEN TMH_CV008_B > 0
         AND Humedad_TM1_B IS NULL
            THEN 'SIN_HUMEDAD_REPRESENTATIVA_TM1'

        WHEN TMH_CV108_A > 0
         AND Humedad_TM2_A IS NULL
            THEN 'SIN_HUMEDAD_REPRESENTATIVA_TM2'

        WHEN TMH_CV108_B > 0
         AND Humedad_TM2_B IS NULL
            THEN 'SIN_HUMEDAD_REPRESENTATIVA_TM2'

        ELSE 'TMS_VALIDO_SEGUN_REGLA_PROVISIONAL'
    END AS Observacion_TMS

FROM tms;
