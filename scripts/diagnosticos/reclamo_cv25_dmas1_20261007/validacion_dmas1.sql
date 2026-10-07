-- SELECT only, DEV. The 06-10 counterfactual changes the date gate only.
SELECT mb.modulo_id, mb.pad_id, mb.rotopala_id,
       MAX(t.fecha_medicion) AS ultima_topografia
FROM reclamo.v_modulo_base mb
LEFT JOIN reclamo.topografia_avance t
  ON t.[campaña_id] = mb.[campaña_id] AND t.modulo_id = mb.modulo_id
 AND t.estado = 'VIGENTE'
WHERE mb.estado_secuencia = 'ABIERTO'
GROUP BY mb.modulo_id, mb.pad_id, mb.rotopala_id;

SELECT fecha, tms_estimado_r1, tms_estimado_r2, horas_r1, horas_r2,
       flag_preliminar
FROM reclamo.v_cv25_diario
WHERE fecha BETWEEN '2026-10-04' AND '2026-10-07'
ORDER BY fecha;

SELECT fecha_operacion, modulo_id, rotopala_id, tms_preliminar_dia,
       fuente_reclamo
FROM reclamo.v_preliminar_cv25
WHERE fecha_operacion BETWEEN '2026-10-04' AND '2026-10-07'
ORDER BY fecha_operacion, modulo_id;

SELECT fecha_operacion, modulo_id, fuente_reclamo, tms_rotopala_dia
FROM reclamo.v_reclamo_diario
WHERE modulo_id = 80
  AND fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06'
ORDER BY fecha_operacion;

-- Simulated topography date for the date gate only; no INSERT/UPDATE.
SELECT fecha AS fecha_elegible_con_topografia_05,
       tms_estimado_r2 AS valor_cv25_disponible
FROM reclamo.v_cv25_diario
WHERE fecha BETWEEN '2026-10-05' AND '2026-10-07'
  AND fecha = DATEADD(DAY, 1, CAST('2026-10-05' AS date));
