CREATE   VIEW [reclamo].[v_preliminar_cv25]
AS
WITH abiertos AS
(
    SELECT
        mb.[campaña_id],
        mb.pad_id,
        mb.modulo_id,
        mb.modulo_numero,
        mb.rotopala_id,
        mb.orden_secuencia,
        mb.m3_totales,
        mb.densidad_oficial,
        mb.fecha_apertura,
        mb.fecha_cierre,
        (
            SELECT MAX(ta.fecha_medicion)
            FROM [reclamo].[topografia_avance] ta
            WHERE ta.[campaña_id] = mb.[campaña_id]
              AND ta.modulo_id    = mb.modulo_id
              AND ta.estado       = 'VIGENTE'
        ) AS ultima_medicion_topografica
    FROM [reclamo].[v_modulo_base] mb
    WHERE mb.estado_secuencia = 'ABIERTO'
      AND mb.rotopala_id IS NOT NULL
),
cv AS
(
    SELECT
        d.fecha,
        d.tms_estimado_r1,
        d.tms_estimado_r2,
        d.horas_r1,
        d.horas_r2,
        d.flag_preliminar
    FROM [reclamo].[v_cv25_diario] d
),
base AS
(
    SELECT
        cv.fecha,
        a.[campaña_id],
        a.pad_id,
        a.modulo_id,
        a.modulo_numero,
        a.rotopala_id,
        a.m3_totales,
        a.densidad_oficial,
        a.ultima_medicion_topografica,
        CASE WHEN a.rotopala_id = 1 THEN cv.tms_estimado_r1 ELSE cv.tms_estimado_r2 END
            AS tms_rotopala_dia_total,
        CASE WHEN a.rotopala_id = 1 THEN cv.horas_r1 ELSE cv.horas_r2 END
            AS horas_rotopala,
        cv.flag_preliminar,
        COUNT(*) OVER (PARTITION BY cv.fecha, a.rotopala_id) AS modulos_abiertos
    FROM cv
    CROSS JOIN abiertos a
    WHERE (a.fecha_apertura IS NULL OR cv.fecha >= a.fecha_apertura)
      AND (a.fecha_cierre   IS NULL OR cv.fecha <= a.fecha_cierre)
      AND (a.ultima_medicion_topografica IS NULL
           OR cv.fecha > a.ultima_medicion_topografica)
),
con_acumulado AS
(
    SELECT
        b.fecha                                 AS fecha_operacion,
        b.[campaña_id],
        b.pad_id,
        b.modulo_id,
        b.modulo_numero,
        b.rotopala_id,
        b.horas_rotopala,
        b.modulos_abiertos,
        b.m3_totales,
        b.densidad_oficial,

        /* DIARIO */
        CAST(b.tms_rotopala_dia_total / b.modulos_abiertos AS decimal(30,12))
                                            AS tms_preliminar_dia,
        CAST
        (
            CASE
                WHEN b.densidad_oficial = 0 THEN NULL
                ELSE (b.tms_rotopala_dia_total / b.modulos_abiertos) / b.densidad_oficial
            END AS decimal(30,12)
        )                                       AS m3_preliminar_dia,

        /* NUEVO: ACUMULADO */
        SUM
        (
            CAST(b.tms_rotopala_dia_total / b.modulos_abiertos AS decimal(30,12))
        ) OVER
        (
            PARTITION BY b.[campaña_id], b.modulo_id
            ORDER BY b.fecha
            ROWS UNBOUNDED PRECEDING
        )                                       AS tms_preliminar_acum,

        SUM
        (
            CAST
            (
                CASE
                    WHEN b.densidad_oficial = 0 THEN 0
                    ELSE (b.tms_rotopala_dia_total / b.modulos_abiertos) / b.densidad_oficial
                END AS decimal(30,12)
            )
        ) OVER
        (
            PARTITION BY b.[campaña_id], b.modulo_id
            ORDER BY b.fecha
            ROWS UNBOUNDED PRECEDING
        )                                       AS m3_preliminar_acum,

        CAST('PRELIMINAR_CV25' AS varchar(40))  AS fuente_reclamo,
        CAST('CV25_REPARTIDO_POR_HORAS_ROTOPALA' AS varchar(80)) AS metodo_calculo,
        b.flag_preliminar
    FROM base b
    WHERE b.tms_rotopala_dia_total IS NOT NULL
)
SELECT
    ca.fecha_operacion,
    ca.[campaña_id],
    ca.pad_id,
    ca.modulo_id,
    ca.modulo_numero,
    ca.rotopala_id,
    ca.horas_rotopala,
    ca.modulos_abiertos,

    /* DIARIO (compatible con versión anterior) */
    ca.tms_preliminar_dia,
    ca.m3_preliminar_dia,

    /* NUEVO: ACUMULADO */
    ca.tms_preliminar_acum,
    ca.m3_preliminar_acum,

    /* NUEVO: Porcentaje respecto del volumen total del módulo */
    CASE
        WHEN ca.m3_totales = 0 THEN NULL
        ELSE CAST(ca.m3_preliminar_acum / ca.m3_totales AS float)
    END                                     AS avance_preliminar_pct_total,

    ca.fuente_reclamo,
    ca.metodo_calculo,
    ca.flag_preliminar
FROM con_acumulado ca;