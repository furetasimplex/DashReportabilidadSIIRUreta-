CREATE   VIEW
    inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test
AS

WITH Equipos AS
(
    SELECT CAST('CHANCADOR_CV006' AS varchar(40)) AS equipo_codigo

    UNION ALL
    SELECT 'PRINCIPAL_CV008'

    UNION ALL
    SELECT 'PRINCIPAL_CV108'

    UNION ALL
    SELECT 'RIPIOS_CV025'

    UNION ALL
    SELECT 'SRR_CV001'

    UNION ALL
    SELECT 'SRR_CV002'

    UNION ALL
    SELECT 'SRR_CV003'
),

Legacy AS
(
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
        valor_bruto_resuelto,
        valor_final_resuelto,
        motivo_decision,
        tum_batch_id,
        archivo_batch

    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno

    WHERE fecha_operacional >= '2026-09-01'
),

Estados AS
(
    SELECT
        fecha_operacional,
        turno,
        contingencia_pi_activa,
        estado_fuente,
        accion_vigente_id,
        accion_vigente,
        motivo_contingencia,
        comentario_ultima_accion,
        usuario_ultima_accion,
        fecha_registro_ultima_accion,
        fecha_accion_vigente,
        turno_accion_vigente

    FROM inventar_SpcHidr.v_contingencia_pi_estado_turno_test
),

Claves AS
(
    SELECT
        fecha_operacional,
        turno,
        equipo_codigo

    FROM Legacy AS l

    UNION

    SELECT
        a.fecha_operacional,
        a.turno,
        e.equipo_codigo

    FROM inventar_SpcHidr.contingencia_pi_accion_test AS a

    CROSS JOIN Equipos AS e

    WHERE a.fecha_operacional >= '2026-09-01'
),

Base AS
(
SELECT k.fecha_operacional, k.turno, k.equipo_codigo, COALESCE (l.estado_tecnico_pi, 'SIN_PI') AS estado_tecnico_pi, COALESCE (l.estado_fronteras, 'SIN_PI') AS estado_fronteras, l.valor_pi_bruto, l.valor_pi_final, l.lectura_inicio_pi, l.lectura_fin_pi, l.delta_frontera_pi, 
                 l.ultima_fecha_con_cambio, l.segundos_sin_cambio_al_cierre, l.tonelaje_apoyo, l.fuente_apoyo, l.estado_apoyo, CAST(COALESCE (l.tum_disponible, 0) AS bit) AS tum_disponible, COALESCE (l.tipo_tum, 'SIN_TUM') AS tipo_tum, l.lectura_inicio_tum, l.lectura_fin_tum, 
                 l.valor_turno_tum, l.total_excel_tum, l.diferencia_inicio_pi_tum, l.diferencia_fin_pi_tum, l.diferencia_tonelaje_pi_tum, l.fuente_resuelta AS fuente_resuelta_legacy, l.valor_bruto_resuelto AS valor_bruto_resuelto_legacy, l.valor_final_resuelto AS valor_final_resuelto_legacy, 
                 l.motivo_decision AS motivo_decision_legacy, CAST(COALESCE (e.contingencia_pi_activa, 0) AS bit) AS contingencia_pi_activa, COALESCE (e.estado_fuente, 'NORMAL_PI') AS estado_fuente, e.accion_vigente_id, e.accion_vigente, e.motivo_contingencia, 
                 e.comentario_ultima_accion, e.usuario_ultima_accion, e.fecha_registro_ultima_accion, e.fecha_accion_vigente, e.turno_accion_vigente, l.tum_batch_id, l.archivo_batch
    FROM    Claves AS k LEFT OUTER JOIN
                 Legacy AS l ON l.fecha_operacional = k.fecha_operacional AND l.turno = k.turno AND l.equipo_codigo = k.equipo_codigo LEFT OUTER JOIN
                 Estados AS e ON e.fecha_operacional = k.fecha_operacional AND e.turno = k.turno), Disponibilidad AS
    (SELECT fecha_operacional, turno, equipo_codigo, estado_tecnico_pi, estado_fronteras, valor_pi_bruto, valor_pi_final, lectura_inicio_pi, lectura_fin_pi, delta_frontera_pi, ultima_fecha_con_cambio, segundos_sin_cambio_al_cierre, tonelaje_apoyo, fuente_apoyo, estado_apoyo, 
                 tum_disponible, tipo_tum, lectura_inicio_tum, lectura_fin_tum, valor_turno_tum, total_excel_tum, diferencia_inicio_pi_tum, diferencia_fin_pi_tum, diferencia_tonelaje_pi_tum, fuente_resuelta_legacy, valor_bruto_resuelto_legacy, valor_final_resuelto_legacy, 
                 motivo_decision_legacy, contingencia_pi_activa, estado_fuente, accion_vigente_id, accion_vigente, motivo_contingencia, comentario_ultima_accion, usuario_ultima_accion, fecha_registro_ultima_accion, fecha_accion_vigente, turno_accion_vigente, tum_batch_id, archivo_batch, 
                 CAST(CASE WHEN b.valor_pi_final IS NOT NULL AND b.valor_pi_final >= 0 THEN 1 ELSE 0 END AS bit) AS pi_disponible_operacional, CAST(CASE WHEN b.tum_disponible = 1 AND b.valor_turno_tum IS NOT NULL AND b.valor_turno_tum >= 0 THEN 1 ELSE 0 END AS bit) 
                 AS tum_disponible_operacional
    FROM    Base AS b), Decision AS
    (SELECT fecha_operacional, turno, equipo_codigo, estado_tecnico_pi, estado_fronteras, valor_pi_bruto, valor_pi_final, lectura_inicio_pi, lectura_fin_pi, delta_frontera_pi, ultima_fecha_con_cambio, segundos_sin_cambio_al_cierre, tonelaje_apoyo, fuente_apoyo, estado_apoyo, 
                 tum_disponible, tipo_tum, lectura_inicio_tum, lectura_fin_tum, valor_turno_tum, total_excel_tum, diferencia_inicio_pi_tum, diferencia_fin_pi_tum, diferencia_tonelaje_pi_tum, fuente_resuelta_legacy, valor_bruto_resuelto_legacy, valor_final_resuelto_legacy, 
                 motivo_decision_legacy, contingencia_pi_activa, estado_fuente, accion_vigente_id, accion_vigente, motivo_contingencia, comentario_ultima_accion, usuario_ultima_accion, fecha_registro_ultima_accion, fecha_accion_vigente, turno_accion_vigente, tum_batch_id, archivo_batch, 
                 pi_disponible_operacional, tum_disponible_operacional, CAST(CASE WHEN d .contingencia_pi_activa = 0 AND d .pi_disponible_operacional = 1 THEN 'PI' WHEN d .contingencia_pi_activa = 0 THEN 'PENDIENTE_PI' WHEN d .contingencia_pi_activa = 1 AND 
                 d .tum_disponible_operacional = 1 THEN 'TUM' WHEN d .contingencia_pi_activa = 1 THEN 'PENDIENTE_TUM' ELSE 'PENDIENTE_PI' END AS varchar(30)) AS fuente_resuelta_operacional
    FROM    Disponibilidad AS d)
    SELECT fecha_operacional, turno, equipo_codigo, estado_tecnico_pi, estado_fronteras, valor_pi_bruto, valor_pi_final, lectura_inicio_pi, lectura_fin_pi, delta_frontera_pi, ultima_fecha_con_cambio, segundos_sin_cambio_al_cierre, tonelaje_apoyo, fuente_apoyo, estado_apoyo, 
                tum_disponible, tipo_tum, lectura_inicio_tum, lectura_fin_tum, valor_turno_tum, total_excel_tum, diferencia_inicio_pi_tum, diferencia_fin_pi_tum, diferencia_tonelaje_pi_tum, contingencia_pi_activa, estado_fuente AS estado_operacional, accion_vigente_id, accion_vigente, 
                motivo_contingencia, comentario_ultima_accion AS comentario_estado_operacional, usuario_ultima_accion AS usuario_estado_operacional, fecha_registro_ultima_accion AS fecha_registro_estado_operacional, fecha_accion_vigente, turno_accion_vigente, 
                CASE WHEN contingencia_pi_activa = 1 THEN 'CONTINGENCIA_ESPECIALISTA' ELSE 'DEFAULT_PI' END AS modo_resolucion, pi_disponible_operacional, tum_disponible_operacional, fuente_resuelta_legacy, valor_bruto_resuelto_legacy, valor_final_resuelto_legacy, 
                motivo_decision_legacy, fuente_resuelta_operacional AS fuente_resuelta, CAST(CASE WHEN fuente_resuelta_operacional = 'PI' THEN valor_pi_bruto WHEN fuente_resuelta_operacional = 'TUM' THEN valor_turno_tum ELSE NULL END AS decimal(28, 6)) AS valor_bruto_resuelto, 
                CAST(CASE WHEN fuente_resuelta_operacional = 'PI' THEN valor_pi_final WHEN fuente_resuelta_operacional = 'TUM' AND equipo_codigo IN ('PRINCIPAL_CV008', 'PRINCIPAL_CV108') AND valor_turno_tum <= 100 THEN 0 WHEN fuente_resuelta_operacional = 'TUM' AND 
                equipo_codigo IN ('PRINCIPAL_CV008', 'PRINCIPAL_CV108') AND valor_turno_tum > 100 THEN valor_turno_tum WHEN fuente_resuelta_operacional = 'TUM' AND equipo_codigo IN ('CHANCADOR_CV006', 'RIPIOS_CV025', 'SRR_CV001', 'SRR_CV002', 'SRR_CV003') 
                THEN valor_turno_tum ELSE NULL END AS decimal(28, 6)) AS valor_final_resuelto, CAST(CASE WHEN contingencia_pi_activa = 0 AND fuente_resuelta_operacional = 'PI' THEN 'DEFAULT_PI_USA_PI' WHEN contingencia_pi_activa = 0 AND 
                fuente_resuelta_operacional = 'PENDIENTE_PI' THEN 'DEFAULT_PI_PENDIENTE_PI' WHEN contingencia_pi_activa = 1 AND fuente_resuelta_operacional = 'TUM' THEN 'CONTINGENCIA_PI_USA_TUM' WHEN contingencia_pi_activa = 1 AND 
                fuente_resuelta_operacional = 'PENDIENTE_TUM' THEN 'CONTINGENCIA_PI_PENDIENTE_TUM' ELSE 'RESOLUCION_NO_DETERMINADA' END AS varchar(80)) AS motivo_decision, tum_batch_id, archivo_batch
   FROM    Decision