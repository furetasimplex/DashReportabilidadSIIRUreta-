CREATE   VIEW inventar_SpcHidr.v_contingencia_diagnostico_turno
AS

SELECT
    pi.fecha_operacional,
    pi.turno,
    pi.equipo_codigo,

    /* =========================
       Estado técnico PI
       ========================= */
    pi.estado_tecnico_pi,
    pi.registros,
    pi.registros_esperados,
    pi.cobertura_pct,
    pi.valores_distintos,

    pi.lectura_inicial_pi,
    pi.lectura_final_pi,
    pi.delta_observado_pi,

    pi.ultima_fecha_con_cambio,
    pi.segundos_sin_cambio_al_cierre,
    pi.cantidad_gaps_anormales,

    /* =========================
       Apoyo operacional MINA / IMP
       ========================= */
    apoyo.tonelaje_apoyo,
    apoyo.fuente_apoyo,

    COALESCE
    (
        apoyo.estado_apoyo,
        'SIN_INFORMACION'
    ) AS estado_apoyo,

    /* =========================
       Diagnóstico combinado
       SIN decidir PI vs TUM todavía
       ========================= */
    CAST
    (
        CASE

            /* PI varía y existe movimiento operacional */
            WHEN pi.estado_tecnico_pi = 'CON_VARIACION'
             AND apoyo.estado_apoyo = 'MOVIMIENTO_CONFIRMADO'
                THEN 'PI_COHERENTE_CON_OPERACION'

            /* PI tuvo gap, pero sigue mostrando movimiento */
            WHEN pi.estado_tecnico_pi = 'CON_VARIACION_COBERTURA_PARCIAL'
             AND apoyo.estado_apoyo = 'MOVIMIENTO_CONFIRMADO'
                THEN 'PI_CON_GAP_REQUIERE_VALIDACION'

            /* PI está plano todo el turno, pero sabemos que hubo alimentación */
            WHEN pi.estado_tecnico_pi = 'SIN_CAMBIO_TURNO_COMPLETO'
             AND apoyo.estado_apoyo = 'MOVIMIENTO_CONFIRMADO'
                THEN 'PI_INCONSISTENTE_CON_OPERACION'

            /* PI está plano y la fuente de apoyo reporta cero */
            WHEN pi.estado_tecnico_pi = 'SIN_CAMBIO_TURNO_COMPLETO'
             AND apoyo.estado_apoyo = 'SIN_MOVIMIENTO_REPORTADO'
                THEN 'PI_COHERENTE_CON_POSIBLE_PARADA'

            /* PI está plano pero no tenemos apoyo */
            WHEN pi.estado_tecnico_pi = 'SIN_CAMBIO_TURNO_COMPLETO'
             AND apoyo.estado_apoyo IS NULL
                THEN 'SIN_APOYO_PARA_DECIDIR'

            WHEN pi.estado_tecnico_pi = 'SIN_CAMBIO_TURNO_COMPLETO'
             AND apoyo.estado_apoyo = 'SIN_INFORMACION'
                THEN 'SIN_APOYO_PARA_DECIDIR'

            /* PI varía pero no tenemos apoyo */
            WHEN pi.estado_tecnico_pi IN
                 ('CON_VARIACION',
                  'CON_VARIACION_COBERTURA_PARCIAL')
             AND
             (
                 apoyo.estado_apoyo IS NULL
                 OR apoyo.estado_apoyo = 'SIN_INFORMACION'
             )
                THEN 'PI_CON_VARIACION_SIN_APOYO'

            ELSE 'REQUIERE_REVISION'

        END
        AS varchar(50)
    ) AS diagnostico_operacional

FROM inventar_SpcHidr.v_contingencia_pi_totalizador_turno pi

LEFT JOIN inventar_SpcHidr.v_contingencia_apoyo_operacional_turno apoyo
    ON  apoyo.fecha_operacional = pi.fecha_operacional
    AND apoyo.turno             = pi.turno;
