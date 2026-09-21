CREATE   VIEW inventar_SpcHidr.v_reporte_diario_humedad_test
AS

WITH base AS
(
    SELECT
        v.Fecha,

        v.Humedad_TM1,
        v.Humedad_TM2,

        v.Fecha_Humedad_TM1,
        v.Torre_Humedad_TM1,
        v.Turno_Humedad_TM1,
        v.Fuente_Humedad_TM1,

        v.Fecha_Humedad_TM2,
        v.Torre_Humedad_TM2,
        v.Turno_Humedad_TM2,
        v.Fuente_Humedad_TM2,

        v.TMH_TM1_Con_Sal_SRR_A AS TMH_TM1_A,
        v.TMH_TM2_Con_Sal_SRR_A AS TMH_TM2_A,

        v.TMH_TM1_Con_Sal_SRR_B AS TMH_TM1_B,
        v.TMH_TM2_Con_Sal_SRR_B AS TMH_TM2_B,

        v.Humedad_Equivalente_Dia,

        v.TMS_TM1_Con_Sal_SRR_A AS TMS_TM1_A,
        v.TMS_TM2_Con_Sal_SRR_A AS TMS_TM2_A,

        v.TMS_TM1_Con_Sal_SRR_B AS TMS_TM1_B,
        v.TMS_TM2_Con_Sal_SRR_B AS TMS_TM2_B,

        v.TMS_Total_Con_Sal_SRR_A,
        v.TMS_Total_Con_Sal_SRR_B,
        v.TMS_Total_Con_Sal_SRR_Dia,

        v.Flag_Apilado_Valido,
        v.Flag_TMS_Valido,
        v.Observacion_TMS

    FROM inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test AS v
),

/* ============================================================
   HUMEDADES DE LABORATORIO
   ============================================================ */
hum AS
(
    SELECT
        CAST(l.Fecha AS date) AS Fecha,
        l.Torre,
        l.Turno,

        AVG(
            CAST(
                l.Humedad_Prom_Pct
                AS float
            )
        ) AS Humedad_Prom_Pct

    FROM inventar_SpcHidr.Informe_TM_lab AS l

    WHERE l.Humedad_Prom_Pct IS NOT NULL
      AND l.Fecha >=
          DATEADD(
              DAY,
              -400,
              CAST(GETDATE() AS date)
          )

    GROUP BY
        CAST(l.Fecha AS date),
        l.Torre,
        l.Turno
),

/* ============================================================
   REPRESENTATIVIDAD FISICA

   CAMBIO DE PERFORMANCE:
   antes:
       v_representatividad_diaria_calculada

   ahora:
       representatividad_torres_resultado

   Misma información utilizada por esta vista:
       TM1 A/B físico
       TM2 A/B físico

   Esto evita expandir nuevamente toda la cadena PI/TUM.
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

    LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado AS r
        ON r.Dia = h.Fecha
),

/* ============================================================
   CANDIDATOS DE HUMEDAD VIGENTE
   ============================================================ */
candidatos AS
(
    SELECT
        h.Fecha,
        h.Torre,
        h.Turno,
        h.Humedad_Prom_Pct,
        h.Representatividad_Fisica,

        DATEADD(
            HOUR,
            CASE
                WHEN h.Turno = 'A' THEN 8
                ELSE 20
            END,
            CAST(h.Fecha AS datetime2(0))
        ) AS FechaTurno_Origen,

        CAST(
            'HUMEDAD_REPRESENTATIVA'
            AS varchar(30)
        ) AS Fuente

    FROM hum_rep AS h

    WHERE h.Humedad_Prom_Pct IS NOT NULL
      AND h.Representatividad_Fisica >= 0.75


    UNION ALL


    SELECT
        CAST(s.fecha_origen AS date),

        CAST(
            s.torre
            AS varchar(20)
        ),

        CAST(
            NULL
            AS varchar(10)
        ),

        CAST(
            s.humedad_pct
            AS float
        ),

        CAST(
            1.0
            AS float
        ),

        CAST(
            s.fecha_origen
            AS datetime2(0)
        ),

        CAST(
            'HUMEDAD_INICIAL_PERIODO'
            AS varchar(30)
        )

    FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s
),

/* ============================================================
   EXPANSION FECHA + TURNO
   ============================================================ */
periodos AS
(
    SELECT
        b.Fecha,

        CAST(
            'A'
            AS varchar(1)
        ) AS Turno,

        DATEADD(
            HOUR,
            8,
            CAST(b.Fecha AS datetime2(0))
        ) AS FechaTurno_Objetivo,

        b.TMH_TM1_A,
        b.TMH_TM2_A,

        COALESCE(b.TMH_TM1_A, 0)
        +
        COALESCE(b.TMH_TM2_A, 0)
            AS TMH_Total_Turno,

        b.TMS_Total_Con_Sal_SRR_A
            AS TMS_Total_Turno

    FROM base AS b


    UNION ALL


    SELECT
        b.Fecha,

        CAST(
            'B'
            AS varchar(1)
        ),

        DATEADD(
            HOUR,
            20,
            CAST(b.Fecha AS datetime2(0))
        ),

        b.TMH_TM1_B,
        b.TMH_TM2_B,

        COALESCE(b.TMH_TM1_B, 0)
        +
        COALESCE(b.TMH_TM2_B, 0),

        b.TMS_Total_Con_Sal_SRR_B

    FROM base AS b
),

/* ============================================================
   HUMEDAD UTILIZADA POR TURNO
   ============================================================ */
humedad_periodo AS
(
    SELECT
        p.Fecha,
        p.Turno,

        p.TMH_TM1_A,
        p.TMH_TM2_A,

        p.TMH_Total_Turno,
        p.TMS_Total_Turno,

        CASE
            WHEN p.TMH_Total_Turno = 0
                THEN vigente.Humedad_Prom_Pct

            WHEN p.TMS_Total_Turno IS NULL
                THEN NULL

            ELSE
                100.0
                *
                (
                    1.0
                    -
                    p.TMS_Total_Turno
                    /
                    NULLIF(
                        p.TMH_Total_Turno,
                        0
                    )
                )
        END AS Humedad_Turno

    FROM periodos AS p

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Humedad_Prom_Pct

        FROM candidatos AS c

        WHERE c.FechaTurno_Origen
              <= p.FechaTurno_Objetivo

        ORDER BY
            c.FechaTurno_Origen DESC,

            CASE
                WHEN c.Torre = 'T2' THEN 1
                WHEN c.Torre = 'T1' THEN 2
                ELSE 3
            END
    ) AS vigente
),

/* ============================================================
   PIVOT DIARIO
   ============================================================ */
humedad_turnos AS
(
    SELECT
        Fecha,

        MAX(
            CASE
                WHEN Turno = 'A'
                    THEN Humedad_Turno
            END
        ) AS Humedad_Turno_A,

        MAX(
            CASE
                WHEN Turno = 'B'
                    THEN Humedad_Turno
            END
        ) AS Humedad_Turno_B

    FROM humedad_periodo

    GROUP BY Fecha
),

calculos AS
(
    SELECT
        b.*,

        h.Humedad_Turno_A,
        h.Humedad_Turno_B,

        COALESCE(b.TMH_TM1_A, 0)
        +
        COALESCE(b.TMH_TM2_A, 0)
            AS TMH_Total_A,

        COALESCE(b.TMH_TM1_B, 0)
        +
        COALESCE(b.TMH_TM2_B, 0)
            AS TMH_Total_B,

        COALESCE(b.TMH_TM1_A, 0)
        +
        COALESCE(b.TMH_TM2_A, 0)
        +
        COALESCE(b.TMH_TM1_B, 0)
        +
        COALESCE(b.TMH_TM2_B, 0)
            AS TMH_Total_Dia

    FROM base AS b

    LEFT JOIN humedad_turnos AS h
        ON h.Fecha = b.Fecha
),

controles AS
(
    SELECT
        c.*,

        CASE
            WHEN c.TMH_Total_Dia = 0
                THEN 0

            WHEN c.Humedad_Turno_A IS NULL
              OR c.Humedad_Turno_B IS NULL
                THEN NULL

            ELSE
                (
                    c.TMH_Total_A
                    *
                    c.Humedad_Turno_A
                    +
                    c.TMH_Total_B
                    *
                    c.Humedad_Turno_B
                )
                /
                NULLIF(
                    c.TMH_Total_Dia,
                    0
                )
        END AS Humedad_Dia_Recalculada,

        CASE
            WHEN c.Humedad_Turno_A IS NULL
                THEN NULL

            ELSE
                c.TMH_Total_A
                *
                (
                    1.0
                    -
                    c.Humedad_Turno_A
                    /
                    100.0
                )
        END AS TMS_Recalculado_A,

        CASE
            WHEN c.Humedad_Turno_B IS NULL
                THEN NULL

            ELSE
                c.TMH_Total_B
                *
                (
                    1.0
                    -
                    c.Humedad_Turno_B
                    /
                    100.0
                )
        END AS TMS_Recalculado_B

    FROM calculos AS c
)

SELECT
    Fecha,

    Humedad_Turno_A,
    Humedad_Turno_B,

    Humedad_Equivalente_Dia
        AS Humedad_promedio_dia,

    Humedad_TM1,
    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,

    Humedad_TM2,
    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2,

    TMH_TM1_A,
    TMH_TM2_A,
    TMH_Total_A,

    TMH_TM1_B,
    TMH_TM2_B,
    TMH_Total_B,

    TMH_Total_Dia,

    Humedad_Dia_Recalculada,

    Humedad_Dia_Recalculada
    -
    Humedad_Equivalente_Dia
        AS Check_Humedad_Dia,

    TMS_Recalculado_A,

    TMS_Total_Con_Sal_SRR_A
        AS TMS_Fuente_A,

    TMS_Recalculado_A
    -
    TMS_Total_Con_Sal_SRR_A
        AS Check_TMS_A,

    TMS_Recalculado_B,

    TMS_Total_Con_Sal_SRR_B
        AS TMS_Fuente_B,

    TMS_Recalculado_B
    -
    TMS_Total_Con_Sal_SRR_B
        AS Check_TMS_B,

    TMS_Total_Con_Sal_SRR_Dia
        AS TMS_Fuente_Dia,

    Flag_Apilado_Valido,
    Flag_TMS_Valido,
    Observacion_TMS

FROM controles;
