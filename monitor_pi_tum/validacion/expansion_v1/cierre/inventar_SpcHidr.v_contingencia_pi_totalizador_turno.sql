CREATE   VIEW
inventar_SpcHidr.v_contingencia_pi_totalizador_turno
AS

WITH serie AS
(
    SELECT
        fecha_operacional,
        turno,
        equipo_codigo,
        fecha_hora,
        valor_pi,
        fuente_pi,
        cadencia_esperada_seg,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                fecha_operacional,
                turno,
                equipo_codigo
            ORDER BY fecha_hora
        ) AS rn_inicio,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                fecha_operacional,
                turno,
                equipo_codigo
            ORDER BY fecha_hora DESC
        ) AS rn_fin,

        LAG(fecha_hora) OVER
        (
            PARTITION BY
                fecha_operacional,
                turno,
                equipo_codigo
            ORDER BY fecha_hora
        ) AS fecha_anterior,

        LAG(valor_pi) OVER
        (
            PARTITION BY
                fecha_operacional,
                turno,
                equipo_codigo
            ORDER BY fecha_hora
        ) AS valor_anterior

    FROM inventar_SpcHidr.v_contingencia_pi_serie
),

calc AS
(
    SELECT
        *,

        DATEDIFF
        (
            SECOND,
            fecha_anterior,
            fecha_hora
        ) AS gap_seg,

        CASE
            WHEN valor_anterior IS NOT NULL
             AND valor_pi <> valor_anterior
                THEN 1
            ELSE 0
        END AS cambio

    FROM serie
),

resumen AS
(
    SELECT
        fecha_operacional,
        turno,
        equipo_codigo,

        MAX(fuente_pi)
            AS fuente_pi,

        MAX(cadencia_esperada_seg)
            AS cadencia_esperada_seg,

        COUNT(*)
            AS registros,

        COUNT(DISTINCT valor_pi)
            AS valores_distintos,

        MIN(fecha_hora)
            AS primera_fecha_registro,

        MAX(fecha_hora)
            AS ultima_fecha_registro,

        MAX
        (
            CASE
                WHEN rn_inicio = 1
                    THEN valor_pi
            END
        ) AS lectura_inicial_pi,

        MAX
        (
            CASE
                WHEN rn_fin = 1
                    THEN valor_pi
            END
        ) AS lectura_final_pi,

        MAX
        (
            CASE
                WHEN cambio = 1
                    THEN fecha_hora
            END
        ) AS ultima_fecha_con_cambio,

        MAX(gap_seg)
            AS max_gap_seg,

        SUM
        (
            CASE
                WHEN gap_seg >= cadencia_esperada_seg * 2
                    THEN 1
                ELSE 0
            END
        ) AS cantidad_gaps_anormales,

        /* SRR CV001 PROCESS VALUE:
           metodología exactamente igual a la oficial */
        SUM
        (
            CASE
                WHEN equipo_codigo = 'SRR_CV001'
                 AND valor_pi IS NOT NULL
                 AND valor_pi >= 0
                    THEN
                        TRY_CONVERT(float, valor_pi)
                        * cadencia_esperada_seg
                        / 3600.0
                ELSE 0
            END
        ) AS process_value_integrado_tmh

    FROM calc

    GROUP BY
        fecha_operacional,
        turno,
        equipo_codigo
),

diagnostico AS
(
    SELECT
        *,

        CAST
        (
            43200.0 / cadencia_esperada_seg
            AS int
        ) AS registros_esperados,

        CAST
        (
            registros * 100.0
            /
            NULLIF
            (
                43200.0 / cadencia_esperada_seg,
                0
            )
            AS decimal(10,2)
        ) AS cobertura_pct,

        CASE
            WHEN valores_distintos = 1
                THEN 43200

            WHEN ultima_fecha_con_cambio IS NOT NULL
                THEN DATEDIFF
                (
                    SECOND,
                    ultima_fecha_con_cambio,
                    ultima_fecha_registro
                )

            ELSE NULL
        END AS segundos_sin_cambio_al_cierre

    FROM resumen
)

SELECT
    fecha_operacional,
    turno,
    equipo_codigo,

    fuente_pi,
    cadencia_esperada_seg,

    registros_esperados,
    registros,
    cobertura_pct,

    valores_distintos,

    primera_fecha_registro,
    ultima_fecha_registro,

    lectura_inicial_pi,
    lectura_final_pi,

    CAST
    (
        CASE
            WHEN equipo_codigo = 'SRR_CV001'
                THEN process_value_integrado_tmh

            ELSE
                lectura_final_pi - lectura_inicial_pi
        END
        AS decimal(28,6)
    ) AS delta_observado_pi,

    ultima_fecha_con_cambio,
    segundos_sin_cambio_al_cierre,

    max_gap_seg,
    cantidad_gaps_anormales,

    CASE
        WHEN valores_distintos = 1
         AND registros = registros_esperados
         AND cantidad_gaps_anormales = 0
            THEN 'SIN_CAMBIO_TURNO_COMPLETO'

        WHEN valores_distintos = 1
            THEN 'SIN_CAMBIO_CON_COBERTURA_PARCIAL'

        WHEN registros < registros_esperados
          OR cantidad_gaps_anormales > 0
            THEN 'CON_VARIACION_COBERTURA_PARCIAL'

        ELSE 'CON_VARIACION'
    END AS estado_tecnico_pi

FROM diagnostico;
