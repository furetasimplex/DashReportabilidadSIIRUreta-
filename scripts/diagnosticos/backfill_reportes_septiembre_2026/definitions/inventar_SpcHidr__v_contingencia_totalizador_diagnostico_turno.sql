CREATE   VIEW
inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno
AS

WITH claves AS
(
    /* PI */
    SELECT
        p.fecha_operacional,
        p.turno,
        p.equipo_codigo
    FROM inventar_SpcHidr.v_contingencia_pi_totalizador_turno AS p
    WHERE p.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108',
        'RIPIOS_CV025',
        'SRR_CV001',
        'SRR_CV002',
        'SRR_CV003'
    )

    UNION

    /* TUM */
    SELECT
        t.fecha_operacional,
        t.turno,
        t.equipo_codigo
    FROM inventar_SpcHidr.v_contingencia_totalizador_turno AS t
    WHERE t.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108',
        'RIPIOS_CV025',
        'SRR_CV001',
        'SRR_CV002',
        'SRR_CV003'
    )
)

SELECT
    c.fecha_operacional,
    c.turno,
    c.equipo_codigo,

    CAST
    (
        CASE
            WHEN pi.equipo_codigo IS NULL
                THEN 'SIN_PI'
            ELSE pi.estado_tecnico_pi
        END
        AS varchar(50)
    ) AS estado_tecnico_pi,

    pi.cobertura_pct,
    pi.valores_distintos,
    pi.ultima_fecha_con_cambio,
    pi.segundos_sin_cambio_al_cierre,
    pi.cantidad_gaps_anormales,

    f.fecha_hora_inicio,
    f.fecha_hora_fin,
    f.lectura_inicio_pi,
    f.lectura_fin_pi,
    f.delta_frontera_pi,

    CAST
    (
        CASE
            WHEN pi.equipo_codigo IS NULL
                THEN 'SIN_PI'
            ELSE f.estado_fronteras
        END
        AS varchar(40)
    ) AS estado_fronteras,

    apoyo.tonelaje_apoyo,
    apoyo.fuente_apoyo,

    CAST
    (
        COALESCE(apoyo.estado_apoyo, 'SIN_INFORMACION')
        AS varchar(30)
    ) AS estado_apoyo,

    tum.id AS tum_id,

    tum.lectura_inicial AS lectura_inicio_tum,
    tum.lectura_final   AS lectura_fin_tum,

    tum.valor_turno AS valor_turno_tum,
    tum.total_excel AS total_excel_tum,

    tum.lectura_inicial_calculada,
    tum.lectura_final_calculada,

    tum.informe_tipo,
    tum.circuito,
    tum.equipo_nombre,

    tum.batch_id AS tum_batch_id,
    tum.archivo_batch,
    tum.quality_json,

    CAST
    (
        CASE
            WHEN tum.id IS NULL THEN 0
            ELSE 1
        END
        AS bit
    ) AS tum_disponible,

    CAST
    (
        CASE
            WHEN c.equipo_codigo = 'SRR_CV001'
                THEN NULL

            WHEN pi.equipo_codigo IS NULL
                THEN NULL

            WHEN tum.lectura_inicial IS NOT NULL
             AND f.lectura_inicio_pi IS NOT NULL
                THEN tum.lectura_inicial - f.lectura_inicio_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS diferencia_inicio_pi_tum,

    CAST
    (
        CASE
            WHEN c.equipo_codigo = 'SRR_CV001'
                THEN NULL

            WHEN pi.equipo_codigo IS NULL
                THEN NULL

            WHEN tum.lectura_final IS NOT NULL
             AND f.lectura_fin_pi IS NOT NULL
                THEN tum.lectura_final - f.lectura_fin_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS diferencia_fin_pi_tum,

    CAST
    (
        CASE
            WHEN tum.valor_turno IS NOT NULL
             AND f.delta_frontera_pi IS NOT NULL
                THEN tum.valor_turno - f.delta_frontera_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS diferencia_tonelaje_pi_tum,

    CAST
    (
        CASE
            WHEN pi.equipo_codigo IS NULL
             AND tum.id IS NOT NULL
                THEN 'SIN_PI_CON_TUM'

            WHEN pi.estado_tecnico_pi IN
            (
                'SIN_CAMBIO_TURNO_COMPLETO',
                'SIN_CAMBIO_CON_COBERTURA_PARCIAL'
            )
             AND tum.id IS NOT NULL
                THEN 'EVALUAR_CON_TUM'

            WHEN pi.estado_tecnico_pi IN
            (
                'SIN_CAMBIO_TURNO_COMPLETO',
                'SIN_CAMBIO_CON_COBERTURA_PARCIAL'
            )
             AND apoyo.estado_apoyo = 'MOVIMIENTO_CONFIRMADO'
             AND tum.id IS NULL
                THEN 'ESPERA_TUM_PI_INCONSISTENTE'

            WHEN pi.estado_tecnico_pi IN
            (
                'SIN_CAMBIO_TURNO_COMPLETO',
                'SIN_CAMBIO_CON_COBERTURA_PARCIAL'
            )
             AND tum.id IS NULL
                THEN 'SIN_EVIDENCIA_SUFICIENTE'

            WHEN pi.estado_tecnico_pi =
                 'CON_VARIACION_COBERTURA_PARCIAL'
             AND tum.id IS NOT NULL
                THEN 'PI_Y_TUM_DISPONIBLES'

            WHEN pi.estado_tecnico_pi =
                 'CON_VARIACION_COBERTURA_PARCIAL'
             AND tum.id IS NULL
                THEN 'PI_CON_GAP_SIN_TUM'

            WHEN pi.estado_tecnico_pi = 'CON_VARIACION'
             AND tum.id IS NOT NULL
                THEN 'PI_Y_TUM_DISPONIBLES'

            WHEN pi.estado_tecnico_pi = 'CON_VARIACION'
             AND tum.id IS NULL
                THEN 'PI_DISPONIBLE_SIN_TUM'

            ELSE 'REQUIERE_REVISION'
        END
        AS varchar(50)
    ) AS estado_diagnostico

FROM claves AS c

LEFT JOIN
    inventar_SpcHidr.v_contingencia_pi_totalizador_turno AS pi
    ON  pi.fecha_operacional = c.fecha_operacional
    AND pi.turno             = c.turno
    AND pi.equipo_codigo     = c.equipo_codigo

LEFT JOIN
    inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f
    ON  f.fecha_operacional = c.fecha_operacional
    AND f.turno             = c.turno
    AND f.equipo_codigo     = c.equipo_codigo

LEFT JOIN
    inventar_SpcHidr.v_contingencia_apoyo_operacional_turno AS apoyo
    ON  apoyo.fecha_operacional = c.fecha_operacional
    AND apoyo.turno             = c.turno
    AND c.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108'
    )

OUTER APPLY
(
    SELECT TOP (1)
        t.*
    FROM inventar_SpcHidr.v_contingencia_totalizador_turno AS t
    WHERE t.fecha_operacional = c.fecha_operacional
      AND t.turno             = c.turno
      AND t.equipo_codigo     = c.equipo_codigo
    ORDER BY
        t.source_revision_at DESC,
        t.updated_at DESC,
        t.batch_id DESC
) AS tum;
