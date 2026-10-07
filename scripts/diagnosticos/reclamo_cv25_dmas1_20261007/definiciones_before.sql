-- reclamo.v_cv25_diario
CREATE VIEW [reclamo].[v_cv25_diario]
AS

WITH hr AS
(
    SELECT
        fecha_turno AS fecha,

        SUM
        (
            CASE
                WHEN h.rotopala_id = 1
                THEN h.horas_operacion
                ELSE 0
            END
        ) AS horas_r1,

        SUM
        (
            CASE
                WHEN h.rotopala_id = 2
                THEN h.horas_operacion
                ELSE 0
            END
        ) AS horas_r2,

        SUM(h.horas_operacion) AS horas_total,

        COUNT(DISTINCT h.turno) AS turnos_con_dato

    FROM [reclamo].[rotopala_horas_turno] h

    GROUP BY
        fecha_turno
)

SELECT
    COALESCE(cv.fecha, hr.fecha) AS fecha,

    cv.tmh_dia,
    cv.tms_dia,

    cv.tmh_cv025tot,
    cv.tmh_cv025_tot,

    cv.tag_utilizado,

    cv.flag AS flag_cv25,

    cv.tmh_cv025tot - cv.tmh_cv025_tot
        AS diferencia_entre_tags,

    ------------------------------------------------------------
    -- Contraste de tags CV025
    ------------------------------------------------------------
    CASE
        WHEN cv.tmh_cv025tot IS NULL
          OR cv.tmh_cv025_tot IS NULL
            THEN 'SIN_CONTRASTE'

        WHEN cv.tmh_cv025_tot = 0
            THEN 'TAG_SECUNDARIO_CERO'

        WHEN
            ABS(cv.tmh_cv025tot - cv.tmh_cv025_tot)
            * 100.0 / cv.tmh_cv025_tot > 1
            THEN 'TAGS_DIFIEREN_SOBRE_1_PCT'

        ELSE 'OK'
    END AS flag_tags,

    hr.horas_r1,
    hr.horas_r2,
    hr.horas_total,
    hr.turnos_con_dato,

    ------------------------------------------------------------
    -- TMS estimado R1
    --
    -- Si CV025 = 0, no hubo operación:
    -- corresponde explícitamente 0 TMS.
    --
    -- Con cobertura de corriente y cero horas: cero confirmado.
    -- Sin cobertura y cero horas: no inferir cero.
    ------------------------------------------------------------
    CASE
        WHEN cv.tms_dia IS NULL THEN NULL
        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 0

        WHEN COALESCE(hr.horas_r1, 0) = 0
         AND COALESCE(cv.horas_con_dato_r1, 0) > 0
            THEN 0

        WHEN COALESCE(hr.horas_r1, 0) = 0
         AND COALESCE(cv.horas_con_dato_r1, 0) = 0
            THEN NULL

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN NULL

        ELSE
            cv.tms_dia
            * hr.horas_r1
            / hr.horas_total
    END AS tms_estimado_r1,

    ------------------------------------------------------------
    -- TMS estimado R2
    ------------------------------------------------------------
    CASE
        WHEN cv.tms_dia IS NULL THEN NULL
        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 0

        WHEN COALESCE(hr.horas_r2, 0) = 0
         AND COALESCE(cv.horas_con_dato_r2, 0) > 0
            THEN 0

        WHEN COALESCE(hr.horas_r2, 0) = 0
         AND COALESCE(cv.horas_con_dato_r2, 0) = 0
            THEN NULL

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN NULL

        ELSE
            cv.tms_dia
            * hr.horas_r2
            / hr.horas_total
    END AS tms_estimado_r2,

    ------------------------------------------------------------
    -- Estado del preliminar
    ------------------------------------------------------------
    CASE
        WHEN cv.fecha IS NULL
            THEN 'SIN_CV25'

        WHEN cv.tms_dia IS NULL THEN 'SIN_RESOLVER_CV25'
        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 'CV25_CERO_SIN_OPERACION'

        WHEN COALESCE(hr.horas_total, 0) = 0
         AND (
             (COALESCE(hr.horas_r1, 0) = 0 AND COALESCE(cv.horas_con_dato_r1, 0) > 0)
             OR (COALESCE(hr.horas_r2, 0) = 0 AND COALESCE(cv.horas_con_dato_r2, 0) > 0)
         )
            THEN 'CERO_OPERACION_CONFIRMADO'

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN 'SIN_HORAS_NO_REPARTIBLE'

        ELSE 'OK'
    END AS flag_preliminar

FROM [reclamo].[cv25_diario] cv

FULL OUTER JOIN hr
    ON hr.fecha = cv.fecha;

GO

-- reclamo.v_preliminar_cv25
CREATE VIEW [reclamo].[v_preliminar_cv25]
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
              AND ta.modulo_id = mb.modulo_id
              AND ta.estado = 'VIGENTE'
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

    -- Solo días operacionales ya cerrados.
    -- El día actual no se publica como preliminar.
    WHERE d.fecha < CAST(SYSDATETIME() AS date)
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

        CASE
            WHEN a.rotopala_id = 1
                THEN cv.tms_estimado_r1
            ELSE cv.tms_estimado_r2
        END AS tms_rotopala_dia_total,

        CASE
            WHEN a.rotopala_id = 1
                THEN cv.horas_r1
            ELSE cv.horas_r2
        END AS horas_rotopala,

        cv.flag_preliminar,

        COUNT(*) OVER
        (
            PARTITION BY cv.fecha, a.rotopala_id
        ) AS modulos_abiertos

    FROM cv

    CROSS JOIN abiertos a

    WHERE
        (
            a.fecha_apertura IS NULL
            OR cv.fecha >= a.fecha_apertura
        )

        AND
        (
            a.fecha_cierre IS NULL
            OR cv.fecha <= a.fecha_cierre
        )

        AND
        (
            a.ultima_medicion_topografica IS NULL
            OR cv.fecha > a.ultima_medicion_topografica
        )
),

con_acumulado AS
(
    SELECT
        b.fecha AS fecha_operacion,
        b.[campaña_id],
        b.pad_id,
        b.modulo_id,
        b.modulo_numero,
        b.rotopala_id,
        b.horas_rotopala,
        b.modulos_abiertos,
        b.m3_totales,
        b.densidad_oficial,

        --------------------------------------------------------
        -- DIARIO
        --------------------------------------------------------
        CAST
        (
            b.tms_rotopala_dia_total / b.modulos_abiertos
            AS decimal(30,12)
        ) AS tms_preliminar_dia,

        CAST
        (
            CASE
                WHEN b.densidad_oficial = 0
                    THEN NULL
                ELSE
                    (
                        b.tms_rotopala_dia_total
                        / b.modulos_abiertos
                    )
                    / b.densidad_oficial
            END
            AS decimal(30,12)
        ) AS m3_preliminar_dia,

        --------------------------------------------------------
        -- ACUMULADO TMS
        --------------------------------------------------------
        SUM
        (
            CAST
            (
                b.tms_rotopala_dia_total / b.modulos_abiertos
                AS decimal(30,12)
            )
        )
        OVER
        (
            PARTITION BY
                b.[campaña_id],
                b.modulo_id

            ORDER BY b.fecha

            ROWS UNBOUNDED PRECEDING
        ) AS tms_preliminar_acum,

        --------------------------------------------------------
        -- ACUMULADO M3
        --------------------------------------------------------
        SUM
        (
            CAST
            (
                CASE
                    WHEN b.densidad_oficial = 0
                        THEN 0
                    ELSE
                        (
                            b.tms_rotopala_dia_total
                            / b.modulos_abiertos
                        )
                        / b.densidad_oficial
                END
                AS decimal(30,12)
            )
        )
        OVER
        (
            PARTITION BY
                b.[campaña_id],
                b.modulo_id

            ORDER BY b.fecha

            ROWS UNBOUNDED PRECEDING
        ) AS m3_preliminar_acum,

        CAST(
            'PRELIMINAR_CV25'
            AS varchar(40)
        ) AS fuente_reclamo,

        CAST(
            'CV25_REPARTIDO_POR_HORAS_ROTOPALA'
            AS varchar(80)
        ) AS metodo_calculo,

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

    ca.tms_preliminar_dia,
    ca.m3_preliminar_dia,

    ca.tms_preliminar_acum,
    ca.m3_preliminar_acum,

    CASE
        WHEN ca.m3_totales = 0
            THEN NULL
        ELSE CAST
        (
            ca.m3_preliminar_acum / ca.m3_totales
            AS float
        )
    END AS avance_preliminar_pct_total,

    ca.fuente_reclamo,
    ca.metodo_calculo,
    ca.flag_preliminar

FROM con_acumulado ca;

GO

-- reclamo.v_reclamo_diario
/* ============================================================================
   V2. ALTER VIEW v_reclamo_diario para usar acumulado combinado
   
   Cambios clave:
   - LEFT JOIN con v_preliminar_cv25_con_acumulado (en lugar de v_preliminar_cv25)
   - Calcular: m3_acum_total = topografia_acum + preliminar_acum (nunca retrocede)
   - Usar m3_acum_total para calcular avance_roto_pct
   ============================================================================ */

CREATE   VIEW [reclamo].[v_reclamo_diario]
AS
WITH universo AS
(
    SELECT fecha_medicion AS fecha_operacion, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_topografia_resuelta]
    UNION
    SELECT fecha_operacion, [campaña_id], 
           (SELECT pad_id FROM [reclamo].[v_modulo_base] mb WHERE mb.[campaña_id]=pca.[campaña_id] AND mb.modulo_id=pca.modulo_id),
           modulo_id
    FROM [reclamo].[v_preliminar_cv25_con_acumulado] pca
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
    COALESCE(tr.m3_incremento, pc_acum.m3_preliminar_dia, 0)
        + COALESCE(aju.ajuste_m3, 0)        AS m3_rotopala_dia,

    CASE
        WHEN tr.m3_incremento IS NOT NULL
            THEN tr.m3_incremento * mb.densidad_oficial
        ELSE COALESCE(pc_acum.tms_preliminar_dia, 0)
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
        ELSE (COALESCE(cam.m3_camiones_acum,0) + COALESCE(tr.m3_reclamado_acum,0) + COALESCE(pc_acum.m3_preliminar_acum,0))
             / mb.m3_totales
    END                                     AS avance_total_pct_calculado,

    /* EL PORCENTAJE QUE VA AL REPORTE: referido al remanente post camiones
       CAMBIO CLAVE: usar acumulado combinado (topografia + preliminar)
       que NUNCA RETROCEDE */
    CASE
        WHEN mb.m3_totales - COALESCE(cam.m3_camiones_acum,0) <= 0 THEN NULL
        ELSE (COALESCE(tr.m3_reclamado_acum,0) + COALESCE(pc_acum.m3_preliminar_acum,0))
             / (mb.m3_totales - COALESCE(cam.m3_camiones_acum,0))
    END                                     AS avance_roto_pct,

    /* trazabilidad */
    CASE
        WHEN tr.m3_incremento IS NOT NULL AND COALESCE(aju.ajustes_aplicados,0) > 0
            THEN 'TOPOGRAFIA'
        WHEN tr.m3_incremento IS NOT NULL
            THEN 'TOPOGRAFIA'
        WHEN pc_acum.tms_preliminar_dia IS NOT NULL
            THEN 'PRELIMINAR_CV25'
        WHEN COALESCE(aju.ajustes_aplicados,0) > 0
            THEN 'AJUSTE_MANUAL'
        ELSE 'SIN_DATO'
    END                                     AS fuente_reclamo,

    COALESCE(tr.metodo, pc_acum.metodo_calculo, 'SIN_METODO')
                                            AS metodo_calculo,

    CASE
        WHEN mb.modulo_id IS NULL
            THEN 'MODULO_NO_CONGELADO'
        WHEN tr.flag_topografia IS NOT NULL
            THEN tr.flag_topografia
        WHEN pc_acum.fuente_reclamo IS NOT NULL
            THEN 'PRELIMINAR_CV25'
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
LEFT JOIN [reclamo].[v_preliminar_cv25_con_acumulado] pc_acum
    ON  pc_acum.[campaña_id]     = u.[campaña_id]
    AND pc_acum.modulo_id        = u.modulo_id
    AND pc_acum.fecha_operacion  = u.fecha_operacion
LEFT JOIN cam
    ON  cam.[campaña_id]     = u.[campaña_id]
    AND cam.modulo_id        = u.modulo_id
    AND cam.fecha_operacion  = u.fecha_operacion
LEFT JOIN aju
    ON  aju.[campaña_id]     = u.[campaña_id]
    AND aju.modulo_id        = u.modulo_id
    AND aju.fecha_operacion  = u.fecha_operacion
WHERE u.fecha_operacion >= corte.fecha_corte;