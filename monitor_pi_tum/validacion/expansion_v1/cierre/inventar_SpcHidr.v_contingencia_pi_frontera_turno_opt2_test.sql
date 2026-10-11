CREATE   VIEW
inventar_SpcHidr.v_contingencia_pi_frontera_turno_opt2_test
AS

WITH fronteras AS
(
    SELECT
        pi.fecha_operacional,
        pi.turno,
        pi.equipo_codigo,

        /* Ya traemos directamente el resultado del totalizador.
           Evitamos volver a expandir la misma vista. */
        pi.delta_observado_pi,

        CASE
            WHEN pi.turno = 'A'
                THEN DATEADD
                (
                    HOUR,
                    8,
                    CAST(pi.fecha_operacional AS datetime2)
                )

            WHEN pi.turno = 'B'
                THEN DATEADD
                (
                    HOUR,
                    20,
                    CAST(pi.fecha_operacional AS datetime2)
                )
        END AS fecha_hora_inicio,

        CASE
            WHEN pi.turno = 'A'
                THEN DATEADD
                (
                    HOUR,
                    20,
                    CAST(pi.fecha_operacional AS datetime2)
                )

            WHEN pi.turno = 'B'
                THEN DATEADD
                (
                    HOUR,
                    8,
                    CAST
                    (
                        DATEADD(DAY, 1, pi.fecha_operacional)
                        AS datetime2
                    )
                )
        END AS fecha_hora_fin

    FROM inventar_SpcHidr.v_contingencia_pi_totalizador_turno_opt_test
         AS pi
)

SELECT
    f.fecha_operacional,
    f.turno,
    f.equipo_codigo,

    f.fecha_hora_inicio,
    f.fecha_hora_fin,

    ini.valor_pi AS lectura_inicio_pi,
    fin.valor_pi AS lectura_fin_pi,

    CAST
    (
        CASE
            /* SRR CV001 mantiene EXACTAMENTE su integración temporal */
            WHEN f.equipo_codigo = 'SRR_CV001'
                THEN f.delta_observado_pi

            /* Resto: frontera final - inicial */
            WHEN ini.valor_pi IS NOT NULL
             AND fin.valor_pi IS NOT NULL
                THEN fin.valor_pi - ini.valor_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS delta_frontera_pi,

    CAST
    (
        CASE
            WHEN ini.valor_pi IS NULL
             AND fin.valor_pi IS NULL
                THEN 'SIN_AMBAS_FRONTERAS'

            WHEN ini.valor_pi IS NULL
                THEN 'SIN_FRONTERA_INICIAL'

            WHEN fin.valor_pi IS NULL
                THEN 'SIN_FRONTERA_FINAL'

            ELSE 'FRONTERAS_COMPLETAS'
        END
        AS varchar(40)
    ) AS estado_fronteras

FROM fronteras AS f

LEFT JOIN inventar_SpcHidr.v_contingencia_pi_serie_opt_test AS ini
    ON  ini.equipo_codigo     = f.equipo_codigo
    AND ini.fecha_operacional = f.fecha_operacional
    AND ini.turno             = f.turno
    AND ini.fecha_hora        = f.fecha_hora_inicio

/* Deliberadamente se conserva EXACTO el JOIN productivo */
LEFT JOIN inventar_SpcHidr.v_contingencia_pi_serie_opt_test AS fin
    ON  fin.equipo_codigo = f.equipo_codigo
    AND fin.fecha_hora    = f.fecha_hora_fin;
