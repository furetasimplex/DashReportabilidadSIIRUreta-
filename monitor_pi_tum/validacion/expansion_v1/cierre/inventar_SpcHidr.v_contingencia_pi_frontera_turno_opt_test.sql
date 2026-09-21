CREATE   VIEW
inventar_SpcHidr.v_contingencia_pi_frontera_turno_opt_test
AS

WITH turnos AS
(
    SELECT DISTINCT
        fecha_operacional,
        turno,
        equipo_codigo
    FROM inventar_SpcHidr.v_contingencia_pi_totalizador_turno_opt_test
),

fronteras AS
(
    SELECT
        fecha_operacional,
        turno,
        equipo_codigo,

        /* Inicio operacional del turno */
        CASE
            WHEN turno = 'A'
                THEN DATEADD
                     (
                         HOUR,
                         8,
                         CAST(fecha_operacional AS datetime2)
                     )

            WHEN turno = 'B'
                THEN DATEADD
                     (
                         HOUR,
                         20,
                         CAST(fecha_operacional AS datetime2)
                     )
        END AS fecha_hora_inicio,

        /* Fin operacional del turno */
        CASE
            WHEN turno = 'A'
                THEN DATEADD
                     (
                         HOUR,
                         20,
                         CAST(fecha_operacional AS datetime2)
                     )

            WHEN turno = 'B'
                THEN DATEADD
                     (
                         HOUR,
                         8,
                         CAST
                         (
                             DATEADD(DAY, 1, fecha_operacional)
                             AS datetime2
                         )
                     )
        END AS fecha_hora_fin

    FROM turnos
)

SELECT
    f.fecha_operacional,
    f.turno,
    f.equipo_codigo,

    f.fecha_hora_inicio,
    f.fecha_hora_fin,

    /* ============================================================
       Lecturas PI de frontera
       MISMA METODOLOGÍA
       ============================================================ */
    ini.valor_pi AS lectura_inicio_pi,
    fin.valor_pi AS lectura_fin_pi,

    /* ============================================================
       Valor del turno

       SRR_CV001:
           integración temporal proveniente del totalizador.

       Resto:
           frontera final - frontera inicial.
       ============================================================ */
    CAST
    (
        CASE
            WHEN f.equipo_codigo = 'SRR_CV001'
                THEN pi.delta_observado_pi

            WHEN ini.valor_pi IS NOT NULL
             AND fin.valor_pi IS NOT NULL
                THEN fin.valor_pi - ini.valor_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS delta_frontera_pi,

    /* ============================================================
       Estado fronteras
       MISMA LÓGICA
       ============================================================ */
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

INNER JOIN
    inventar_SpcHidr.v_contingencia_pi_totalizador_turno_opt_test AS pi
    ON  pi.fecha_operacional = f.fecha_operacional
    AND pi.turno             = f.turno
    AND pi.equipo_codigo     = f.equipo_codigo

LEFT JOIN
    inventar_SpcHidr.v_contingencia_pi_serie_opt_test AS ini
    ON  ini.equipo_codigo     = f.equipo_codigo
    AND ini.fecha_operacional = f.fecha_operacional
    AND ini.turno             = f.turno
    AND ini.fecha_hora        = f.fecha_hora_inicio

LEFT JOIN
    inventar_SpcHidr.v_contingencia_pi_serie_opt_test AS fin
    ON  fin.equipo_codigo = f.equipo_codigo
    AND fin.fecha_hora    = f.fecha_hora_fin;
