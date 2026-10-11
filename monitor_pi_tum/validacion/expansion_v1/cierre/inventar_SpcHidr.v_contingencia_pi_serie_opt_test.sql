CREATE   VIEW inventar_SpcHidr.v_contingencia_pi_serie_opt_test
AS

/* ============================================================
   CV008 - PRINCIPAL
   ÚNICO CAMBIO TÉCNICO:
   usar fecha_turno / codigo_turno ya calculados.
   ============================================================ */
SELECT
    CAST(t.fecha AS datetime2) AS fecha_hora,
    CAST(t.fecha_turno AS date) AS fecha_operacional,
    CAST(t.codigo_turno AS varchar(1)) AS turno,
    CAST('PRINCIPAL_CV008' AS varchar(40)) AS equipo_codigo,
    CAST(t.tot_008 AS decimal(28,6)) AS valor_pi,
    CAST('tot_TM.tot_008' AS varchar(100)) AS fuente_pi,
    CAST(10 AS int) AS cadencia_esperada_seg
FROM inventar_SpcHidr.tot_TM AS t
WHERE t.tot_008 IS NOT NULL

UNION ALL

/* ============================================================
   CV108 - PRINCIPAL
   ============================================================ */
SELECT
    CAST(t.fecha AS datetime2),
    CAST(t.fecha_turno AS date),
    CAST(t.codigo_turno AS varchar(1)),
    CAST('PRINCIPAL_CV108' AS varchar(40)),
    CAST(t.tot_108 AS decimal(28,6)),
    CAST('tot_TM.tot_108' AS varchar(100)),
    CAST(10 AS int)
FROM inventar_SpcHidr.tot_TM AS t
WHERE t.tot_108 IS NOT NULL

UNION ALL

/* ============================================================
   CV006 - CHANCADOR
   SIN CAMBIOS
   ============================================================ */
SELECT
    CAST(d.fecha_inicial AS datetime2),

    CASE
        WHEN CAST(d.fecha_inicial AS time) < '08:00:00'
            THEN DATEADD(DAY, -1, CAST(d.fecha_inicial AS date))
        ELSE CAST(d.fecha_inicial AS date)
    END,

    CASE
        WHEN CAST(d.fecha_inicial AS time) >= '08:00:00'
         AND CAST(d.fecha_inicial AS time) <  '20:00:00'
            THEN 'A'
        ELSE 'B'
    END,

    CAST('CHANCADOR_CV006' AS varchar(40)),
    CAST(d.cv006_tot AS decimal(28,6)),
    CAST('datos_filtrados.cv006_tot' AS varchar(100)),
    CAST(3600 AS int)

FROM inventar_SpcHidr.datos_filtrados AS d
WHERE d.cv006_tot IS NOT NULL

UNION ALL

/* ============================================================
   SRR CV002
   SIN CAMBIOS
   ============================================================ */
SELECT
    CAST(d.fecha_inicial AS datetime2),

    CASE
        WHEN CAST(d.fecha_inicial AS time) < '08:00:00'
            THEN DATEADD(DAY, -1, CAST(d.fecha_inicial AS date))
        ELSE CAST(d.fecha_inicial AS date)
    END,

    CASE
        WHEN CAST(d.fecha_inicial AS time) >= '08:00:00'
         AND CAST(d.fecha_inicial AS time) <  '20:00:00'
            THEN 'A'
        ELSE 'B'
    END,

    CAST('SRR_CV002' AS varchar(40)),
    CAST(d.cv002_tot AS decimal(28,6)),
    CAST('datos_filtrados.cv002_tot' AS varchar(100)),
    CAST(3600 AS int)

FROM inventar_SpcHidr.datos_filtrados AS d
WHERE d.cv002_tot IS NOT NULL

UNION ALL

/* ============================================================
   SRR CV003
   SIN CAMBIOS
   ============================================================ */
SELECT
    CAST(d.fecha_inicial AS datetime2),

    CASE
        WHEN CAST(d.fecha_inicial AS time) < '08:00:00'
            THEN DATEADD(DAY, -1, CAST(d.fecha_inicial AS date))
        ELSE CAST(d.fecha_inicial AS date)
    END,

    CASE
        WHEN CAST(d.fecha_inicial AS time) >= '08:00:00'
         AND CAST(d.fecha_inicial AS time) <  '20:00:00'
            THEN 'A'
        ELSE 'B'
    END,

    CAST('SRR_CV003' AS varchar(40)),
    CAST(d.cv003_tot AS decimal(28,6)),
    CAST('datos_filtrados.cv003_tot' AS varchar(100)),
    CAST(3600 AS int)

FROM inventar_SpcHidr.datos_filtrados AS d
WHERE d.cv003_tot IS NOT NULL

UNION ALL

/* ============================================================
   SRR CV001 - PROCESS VALUE
   MISMA matemática.
   Sólo cambia la derivación fecha_operacional / turno.
   ============================================================ */
SELECT
    CAST(t.fecha AS datetime2),
    CAST(t.fecha_turno AS date),
    CAST(t.codigo_turno AS varchar(1)),
    CAST('SRR_CV001' AS varchar(40)),
    CAST(t.tot_001 AS decimal(28,6)),
    CAST(
        'tot_TM.tot_001_PROCESS_VALUE'
        AS varchar(100)
    ),
    CAST(10 AS int)

FROM inventar_SpcHidr.tot_TM AS t

WHERE t.fecha >= '2026-07-01T08:00:00'
  AND t.tot_001 IS NOT NULL
  AND TRY_CONVERT(float, t.tot_001) >= 0

UNION ALL

/* ============================================================
   CV025 - RIPIOS
   SIN CAMBIOS
   ============================================================ */
SELECT
    CAST(d.fecha_inicial AS datetime2),

    CASE
        WHEN CAST(d.fecha_inicial AS time) < '08:00:00'
            THEN DATEADD(DAY, -1, CAST(d.fecha_inicial AS date))
        ELSE CAST(d.fecha_inicial AS date)
    END,

    CASE
        WHEN CAST(d.fecha_inicial AS time) >= '08:00:00'
         AND CAST(d.fecha_inicial AS time) <  '20:00:00'
            THEN 'A'
        ELSE 'B'
    END,

    CAST('RIPIOS_CV025' AS varchar(40)),
    CAST(d.cv025_tot AS decimal(28,6)),
    CAST('datos_filtrados.cv025_tot' AS varchar(100)),
    CAST(3600 AS int)

FROM inventar_SpcHidr.datos_filtrados AS d
WHERE d.cv025_tot IS NOT NULL;
