CREATE   VIEW
inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno_opt_test
AS

WITH pi_productivo AS
(
    /* CV008 A */
    SELECT
        Fecha AS fecha_operacional,
        CAST('A' AS char(1)) AS turno,
        CAST('PRINCIPAL_CV008' AS varchar(40)) AS equipo_codigo,
        CAST(TMH_CV008_A_Bruto AS decimal(28,6)) AS valor_pi_bruto,
        CAST(TMH_CV008_A AS decimal(28,6))       AS valor_pi_final
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2

    UNION ALL

    /* CV008 B */
    SELECT
        Fecha,
        CAST('B' AS char(1)),
        CAST('PRINCIPAL_CV008' AS varchar(40)),
        CAST(TMH_CV008_B_Bruto AS decimal(28,6)),
        CAST(TMH_CV008_B AS decimal(28,6))
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2

    UNION ALL

    /* CV108 A */
    SELECT
        Fecha,
        CAST('A' AS char(1)),
        CAST('PRINCIPAL_CV108' AS varchar(40)),
        CAST(TMH_CV108_A_Bruto AS decimal(28,6)),
        CAST(TMH_CV108_A AS decimal(28,6))
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2

    UNION ALL

    /* CV108 B */
    SELECT
        Fecha,
        CAST('B' AS char(1)),
        CAST('PRINCIPAL_CV108' AS varchar(40)),
        CAST(TMH_CV108_B_Bruto AS decimal(28,6)),
        CAST(TMH_CV108_B AS decimal(28,6))
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2

    UNION ALL

    /* ============================================================
       CV006 + CV025 + SRR001/002/003
       UNA sola expansión de frontera.
       ============================================================ */
    SELECT
        f.fecha_operacional,
        f.turno,
        CAST(f.equipo_codigo AS varchar(40)),
        CAST(f.delta_frontera_pi AS decimal(28,6)),
        CAST(f.delta_frontera_pi AS decimal(28,6))
    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno_opt2_test AS f
    WHERE f.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'RIPIOS_CV025',
        'SRR_CV001',
        'SRR_CV002',
        'SRR_CV003'
    )
),

base AS
(
    SELECT
        d.fecha_operacional,
        d.turno,
        d.equipo_codigo,

        d.estado_tecnico_pi,
        d.cobertura_pct,

        d.ultima_fecha_con_cambio,
        d.segundos_sin_cambio_al_cierre,

        d.lectura_inicio_pi,
        d.lectura_fin_pi,
        d.delta_frontera_pi,
        d.estado_fronteras,

        p.valor_pi_bruto,
        p.valor_pi_final,

        d.tonelaje_apoyo,
        d.fuente_apoyo,
        d.estado_apoyo,

        d.tum_id,
        d.tum_disponible,

        d.lectura_inicio_tum,
        d.lectura_fin_tum,

        d.valor_turno_tum,
        d.total_excel_tum,

        d.lectura_inicial_calculada,
        d.lectura_final_calculada,

        d.diferencia_inicio_pi_tum,
        d.diferencia_fin_pi_tum,
        d.diferencia_tonelaje_pi_tum,

        d.archivo_batch,
        d.tum_batch_id,

        CAST
        (
            CASE
                WHEN d.tum_disponible = 0
                    THEN 'SIN_TUM'

                WHEN ISNULL(d.lectura_inicial_calculada,0) = 0
                 AND ISNULL(d.lectura_final_calculada,0) = 0
                    THEN 'TUM_DIRECTO'

                WHEN ISNULL(d.lectura_inicial_calculada,0) = 1
                 AND ISNULL(d.lectura_final_calculada,0) = 1
                    THEN 'TUM_CALCULADO'

                ELSE 'TUM_MIXTO'
            END
            AS varchar(30)
        ) AS tipo_tum

    FROM
        inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno_opt_test
        AS d

    LEFT JOIN pi_productivo AS p
      ON  p.fecha_operacional = d.fecha_operacional
      AND p.turno             = d.turno
      AND p.equipo_codigo     = d.equipo_codigo

    WHERE d.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108',
        'RIPIOS_CV025',
        'SRR_CV001',
        'SRR_CV002',
        'SRR_CV003'
    )
),

decision AS
(
    SELECT
        *,

        CAST
        (
            CASE
                WHEN estado_tecnico_pi = 'SIN_PI'
                 AND tum_disponible = 1
                 AND valor_turno_tum IS NOT NULL
                 AND valor_turno_tum >= 0
                    THEN 'TUM'

                WHEN equipo_codigo = 'SRR_CV001'
                 AND estado_tecnico_pi IN
                 (
                     'CON_VARIACION',
                     'CON_VARIACION_COBERTURA_PARCIAL'
                 )
                 AND valor_pi_final IS NOT NULL
                 AND valor_pi_final >= 0
                    THEN 'PI'

                WHEN equipo_codigo <> 'SRR_CV001'
                 AND estado_fronteras = 'FRONTERAS_COMPLETAS'
                 AND delta_frontera_pi IS NOT NULL
                 AND delta_frontera_pi >= 0
                 AND estado_tecnico_pi IN
                 (
                     'CON_VARIACION',
                     'CON_VARIACION_COBERTURA_PARCIAL'
                 )
                    THEN 'PI'

                WHEN tum_disponible = 1
                 AND valor_turno_tum IS NOT NULL
                 AND valor_turno_tum >= 0
                    THEN 'TUM'

                ELSE 'SIN_RESOLVER'
            END
            AS varchar(30)
        ) AS fuente_resuelta

    FROM base
)

SELECT
    fecha_operacional,
    turno,
    equipo_codigo,

    estado_tecnico_pi,
    estado_fronteras,

    valor_pi_bruto,
    valor_pi_final,

    lectura_inicio_pi,
    lectura_fin_pi,
    delta_frontera_pi,

    ultima_fecha_con_cambio,
    segundos_sin_cambio_al_cierre,

    tonelaje_apoyo,
    fuente_apoyo,
    estado_apoyo,

    tum_disponible,
    tipo_tum,

    lectura_inicio_tum,
    lectura_fin_tum,

    valor_turno_tum,
    total_excel_tum,

    diferencia_inicio_pi_tum,
    diferencia_fin_pi_tum,
    diferencia_tonelaje_pi_tum,

    fuente_resuelta,

    CAST
    (
        CASE
            WHEN fuente_resuelta = 'PI'
                THEN valor_pi_bruto

            WHEN fuente_resuelta = 'TUM'
                THEN valor_turno_tum

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS valor_bruto_resuelto,

    CAST
    (
        CASE
            WHEN fuente_resuelta = 'PI'
                THEN valor_pi_final

            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo = 'CHANCADOR_CV006'
             AND valor_turno_tum >= 0
                THEN valor_turno_tum

            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo = 'RIPIOS_CV025'
             AND valor_turno_tum >= 0
                THEN valor_turno_tum

            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo IN
             (
                 'SRR_CV001',
                 'SRR_CV002',
                 'SRR_CV003'
             )
             AND valor_turno_tum >= 0
                THEN valor_turno_tum

            /* Regla productiva CV008 / CV108 */
            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo IN
             (
                 'PRINCIPAL_CV008',
                 'PRINCIPAL_CV108'
             )
             AND valor_turno_tum > 100
                THEN valor_turno_tum

            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo IN
             (
                 'PRINCIPAL_CV008',
                 'PRINCIPAL_CV108'
             )
             AND valor_turno_tum <= 100
                THEN 0

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS valor_final_resuelto,

    CAST
    (
        CASE
            WHEN fuente_resuelta = 'TUM'
             AND estado_tecnico_pi = 'SIN_PI'
             AND tipo_tum = 'TUM_DIRECTO'
                THEN 'SIN_PI_USA_TUM_DIRECTO'

            WHEN fuente_resuelta = 'TUM'
             AND estado_tecnico_pi = 'SIN_PI'
             AND tipo_tum = 'TUM_MIXTO'
                THEN 'SIN_PI_USA_TUM_MIXTO'

            WHEN fuente_resuelta = 'TUM'
             AND estado_tecnico_pi = 'SIN_PI'
             AND tipo_tum = 'TUM_CALCULADO'
                THEN 'SIN_PI_USA_TUM_CALCULADO'

            WHEN fuente_resuelta = 'PI'
             AND tum_disponible = 0
                THEN 'PI_DISPONIBLE'

            WHEN fuente_resuelta = 'PI'
             AND tum_disponible = 1
                THEN 'PI_PRIORITARIO_TUM_SOLO_CONTROL'

            WHEN fuente_resuelta = 'TUM'
             AND tipo_tum = 'TUM_DIRECTO'
                THEN 'PI_EN_CONTINGENCIA_USA_TUM_DIRECTO'

            WHEN fuente_resuelta = 'TUM'
             AND tipo_tum = 'TUM_MIXTO'
                THEN 'PI_EN_CONTINGENCIA_USA_TUM_MIXTO'

            WHEN fuente_resuelta = 'TUM'
             AND tipo_tum = 'TUM_CALCULADO'
                THEN 'PI_EN_CONTINGENCIA_USA_TUM_CALCULADO'

            WHEN fuente_resuelta = 'SIN_RESOLVER'
             AND estado_apoyo = 'MOVIMIENTO_CONFIRMADO'
                THEN 'MOVIMIENTO_CONFIRMADO_ESPERANDO_TUM'

            WHEN fuente_resuelta = 'SIN_RESOLVER'
             AND equipo_codigo IN
             (
                 'SRR_CV001',
                 'SRR_CV002',
                 'SRR_CV003'
             )
                THEN 'SRR_SIN_TUM'

            WHEN fuente_resuelta = 'SIN_RESOLVER'
             AND equipo_codigo = 'RIPIOS_CV025'
                THEN 'CV025_SIN_TUM'

            ELSE 'SIN_EVIDENCIA_SUFICIENTE'
        END
        AS varchar(80)
    ) AS motivo_decision,

    tum_batch_id,
    archivo_batch

FROM decision;
