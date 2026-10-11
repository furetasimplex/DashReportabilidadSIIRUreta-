/* DEV, solo SELECT posterior al ALTER VIEW. No recalcula ni publica. */
SELECT DB_NAME() AS base, SYSDATETIME() AS observado;

SELECT cv.fecha,cv.tmh_dia,cv.tms_dia,cv.horas_con_dato_r1,
       cv.horas_con_dato_r2,cv.tag_utilizado,cv.flag
FROM reclamo.cv25_diario cv
WHERE cv.fecha BETWEEN '2026-10-04' AND '2026-10-06'
ORDER BY cv.fecha;

SELECT fecha,horas_r1,horas_r2,horas_total,
       tms_estimado_r1,tms_estimado_r2,flag_preliminar
FROM reclamo.v_cv25_diario
WHERE fecha BETWEEN '2026-10-04' AND '2026-10-06'
ORDER BY fecha;

SELECT fecha_operacion,[campaña_id],pad_id,modulo_id,modulo_numero,
       rotopala_id,tms_preliminar_dia,m3_preliminar_dia,
       fuente_reclamo,flag_preliminar
FROM reclamo.v_preliminar_cv25
WHERE fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06'
ORDER BY fecha_operacion,modulo_id;

SELECT fecha_operacion,[campaña_id],pad_id,modulo_id,
       tms_preliminar_dia,m3_preliminar_dia,fuente_reclamo
FROM reclamo.v_preliminar_cv25_con_acumulado
WHERE fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06'
ORDER BY fecha_operacion,modulo_id;

SELECT fecha_operacion,[campaña_id],pad_id,modulo_id,modulo_numero,
       rotopala_id,tms_rotopala_dia,m3_rotopala_dia,fuente_reclamo,flag_calculo
FROM reclamo.v_reclamo_diario
WHERE fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06'
ORDER BY fecha_operacion,modulo_id;

/* Control de la fuente que consume el mensaje del panel. La tabla calculada
   puede requerir reproceso independiente; no se actualiza en esta tarea. */
SELECT fecha_operacion,pad_id,fuente_reclamo,COUNT(*) AS filas
FROM reclamo.calculo_diario
WHERE fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06'
GROUP BY fecha_operacion,pad_id,fuente_reclamo
ORDER BY fecha_operacion,pad_id,fuente_reclamo;
