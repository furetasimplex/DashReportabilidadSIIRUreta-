CREATE   VIEW [reclamo].[v_reclamo_diario]
AS
WITH universo AS
(
    SELECT fecha_medicion AS fecha_operacion, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_topografia_resuelta]
    UNION
    SELECT fecha_operacion, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_preliminar_cv25]
    UNION
    SELECT fecha, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_camiones_acumulado]
    UNION
    SELECT fecha_operacion, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_ajustes_aplicables]
),
corte AS
(
    SELECT [reclamo].[fn_fecha_corte]() AS fecha_corte
),
cam AS
(
    SELECT
        u.fecha_operacion,
        u.[campaña_id],
        u.modulo_id,
        (
            SELECT TOP (1) c.m3_camiones_acum
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = u.[campaña_id]
              AND c.modulo_id    = u.modulo_id
              AND c.fecha       <= u.fecha_operacion
            ORDER BY c.fecha DESC
        ) AS m3_camiones_acum,
        (
            SELECT TOP (1) c.tms_camiones_acum
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = u.[campaña_id]
              AND c.modulo_id    = u.modulo_id
              AND c.fecha       <= u.fecha_operacion
            ORDER BY c.fecha DESC
        ) AS tms_camiones_acum,
        (
            SELECT TOP (1) c.m3_camiones_dia
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = u.[campaña_id]
              AND c.modulo_id    = u.modulo_id
              AND c.fecha        = u.fecha_operacion
        ) AS m3_camiones_dia,
        (
            SELECT TOP (1) c.tms_camiones_dia
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = u.[campaña_id]
              AND c.modulo_id    = u.modulo_id
              AND c.fecha        = u.fecha_operacion
        ) AS tms_camiones_dia
    FROM universo u
),
aju AS
(
    SELECT
        a.fecha_operacion,
        a.[campaña_id],
        a.modulo_id,
        SUM(COALESCE(a.delta_m3, 0))  AS ajuste_m3,
        SUM(COALESCE(a.delta_tms, 0)) AS ajuste_tms,
        COUNT(*)                      AS ajustes_aplicados
    FROM [reclamo].[v_ajustes_aplicables] a
    GROUP BY a.fecha_operacion, a.[campaña_id], a.modulo_id
)
SELECT
    u.fecha_operacion,
    u.[campaña_id],
    u.pad_id,
    u.modulo_id,
    mb.modulo_numero,
    mb.rotopala_id,
    mb.orden_secuencia,

    /* base congelada */
    mb.tms_conformado,
    mb.m3_totales,
    mb.densidad_oficial,

    /* camiones */
    COALESCE(cam.m3_camiones_dia, 0)        AS m3_camiones_dia,
    COALESCE(cam.tms_camiones_dia, 0)       AS tms_camiones_dia,
    COALESCE(cam.m3_camiones_acum, 0)       AS m3_camiones_acum,
    COALESCE(cam.tms_camiones_acum, 0)      AS tms_camiones_acum,

    /* base disponible para la rotopala, neta de camiones. Piso en cero. */
    CASE
        WHEN mb.m3_totales - COALESCE(cam.m3_camiones_acum,0) < 0 THEN 0
        ELSE mb.m3_totales - COALESCE(cam.m3_camiones_acum,0)
    END                                     AS m3_disponible_roto,
    CASE
        WHEN mb.tms_conformado - COALESCE(cam.tms_camiones_acum,0) < 0 THEN 0
        ELSE mb.tms_conformado - COALESCE(cam.tms_camiones_acum,0)
    END                                     AS tms_disponible_roto,

    /* reclamo de rotopala del dia: topografia manda, preliminar rellena */
    COALESCE(tr.m3_incremento, pc.m3_preliminar_dia, 0)
        + COALESCE(aju.ajuste_m3, 0)        AS m3_rotopala_dia,

    CASE
        WHEN tr.m3_incremento IS NOT NULL
            THEN tr.m3_incremento * mb.densidad_oficial
        ELSE COALESCE(pc.tms_preliminar_dia, 0)
    END + COALESCE(aju.ajuste_tms, 0)       AS tms_rotopala_dia,

    tr.m3_reclamado_acum                    AS m3_rotopala_acum_topografia,
    tr.avance_total_pct,

    /* ajustes */
    COALESCE(aju.ajuste_m3, 0)              AS ajuste_m3,
    COALESCE(aju.ajuste_tms, 0)             AS ajuste_tms,
    COALESCE(aju.ajustes_aplicados, 0)      AS ajustes_aplicados,

    /* porcentajes */
    CASE
        WHEN COALESCE(mb.m3_totales,0) = 0 THEN NULL
        ELSE COALESCE(cam.m3_camiones_acum,0) / mb.m3_totales
    END                                     AS avance_camiones_pct,

    CASE
        WHEN COALESCE(mb.m3_totales,0) = 0 THEN NULL
        ELSE (COALESCE(cam.m3_camiones_acum,0) + COALESCE(tr.m3_reclamado_acum,0))
             / mb.m3_totales
    END                                     AS avance_total_pct_calculado,

    /* MODIFICADO: EL PORCENTAJE DE AVANCE POST-CAMIONES
       Prioridad: TOPOGRAFIA REAL → PRELIMINAR_ACUM → NULL */
    CASE
        WHEN mb.m3_totales - COALESCE(cam.m3_camiones_acum,0) <= 0 THEN NULL
        WHEN tr.m3_reclamado_acum IS NOT NULL
            THEN CAST(
                    tr.m3_reclamado_acum
                    / (mb.m3_totales - COALESCE(cam.m3_camiones_acum,0))
                 AS decimal(9,4))
        WHEN pc.m3_preliminar_acum IS NOT NULL
            THEN CAST(
                    pc.m3_preliminar_acum
                    / (mb.m3_totales - COALESCE(cam.m3_camiones_acum,0))
                 AS decimal(9,4))
        ELSE NULL
    END                                     AS avance_roto_pct,

    /* trazabilidad */
    CASE
        WHEN tr.m3_incremento IS NOT NULL AND COALESCE(aju.ajustes_aplicados,0) > 0
            THEN 'TOPOGRAFIA'
        WHEN tr.m3_incremento IS NOT NULL
            THEN 'TOPOGRAFIA'
        WHEN pc.tms_preliminar_dia IS NOT NULL
            THEN 'PRELIMINAR_CV25'
        WHEN COALESCE(aju.ajustes_aplicados,0) > 0
            THEN 'AJUSTE_MANUAL'
        ELSE 'SIN_DATO'
    END                                     AS fuente_reclamo,

    COALESCE(tr.metodo, pc.metodo_calculo, 'SIN_METODO')
                                            AS metodo_calculo,

    CASE
        WHEN mb.modulo_id IS NULL
            THEN 'MODULO_NO_CONGELADO'
        WHEN tr.flag_topografia IS NOT NULL
            THEN tr.flag_topografia
        WHEN pc.flag_preliminar IS NOT NULL
            THEN pc.flag_preliminar
        WHEN COALESCE(aju.ajustes_aplicados,0) > 0
            THEN 'SOLO_AJUSTE_MANUAL'
        ELSE 'SIN_DATO'
    END                                     AS flag_calculo,

    COALESCE(aju.ajustes_aplicados,0)       AS n_ajustes
FROM universo u
CROSS JOIN corte
LEFT JOIN [reclamo].[v_modulo_base] mb
    ON  mb.[campaña_id] = u.[campaña_id]
    AND mb.modulo_id    = u.modulo_id
LEFT JOIN [reclamo].[v_topografia_resuelta] tr
    ON  tr.[campaña_id]    = u.[campaña_id]
    AND tr.modulo_id       = u.modulo_id
    AND tr.fecha_medicion  = u.fecha_operacion
LEFT JOIN [reclamo].[v_preliminar_cv25] pc
    ON  pc.[campaña_id]     = u.[campaña_id]
    AND pc.modulo_id        = u.modulo_id
    AND pc.fecha_operacion  = u.fecha_operacion
LEFT JOIN cam
    ON  cam.[campaña_id]     = u.[campaña_id]
    AND cam.modulo_id        = u.modulo_id
    AND cam.fecha_operacion  = u.fecha_operacion
LEFT JOIN aju
    ON  aju.[campaña_id]     = u.[campaña_id]
    AND aju.modulo_id        = u.modulo_id
    AND aju.fecha_operacion  = u.fecha_operacion
WHERE u.fecha_operacion >= corte.fecha_corte;