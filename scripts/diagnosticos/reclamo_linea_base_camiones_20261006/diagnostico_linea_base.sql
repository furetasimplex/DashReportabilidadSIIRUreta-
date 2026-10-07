-- DEV / solo lectura. Corte y línea base de camiones de PAD2 campaña 10.
SELECT * FROM reclamo.configuracion ORDER BY clave;

SELECT campaña_id,pad_id,modulo_id,modulo_numero,fecha_congelamiento,
       fecha_linea_base,m3_camiones_previo,m3_rotopala_previo,estado,
       fuente,metodo,fecha_registro
FROM reclamo.modulo_congelado
WHERE campaña_id=10 AND pad_id=2 AND modulo_id IN (81,87)
ORDER BY modulo_id;

SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.sp_establecer_linea_base'))
       AS def_sp_establecer_linea_base;
SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.sp_auto_congelar_modulos_nuevos'))
       AS def_sp_auto_congelar_modulos_nuevos;

DECLARE @Corte date=(SELECT TRY_CAST(valor AS date)
                    FROM reclamo.configuracion WHERE clave='FECHA_CORTE_SISTEMA');

SELECT campaña_id,modulo_id,SUM(COALESCE(volumen_diario_m3,0)) AS m3_previo_esperado,
       MIN(fecha) AS primera_fecha,MAX(fecha) AS ultima_fecha_pre_corte,
       COUNT(*) AS filas
FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario
WHERE campaña_id=10 AND modulo_id IN (81,87) AND CAST(fecha AS date)<@Corte
GROUP BY campaña_id,modulo_id;

SELECT fecha,campaña,campaña_id,modulo,modulo_id,volumen_diario_m3,
       volumen_final_reclamado,avance_porcentaje
FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario
WHERE campaña_id=10 AND modulo_id IN (81,87)
ORDER BY modulo_id,fecha;

SELECT fecha,campaña_id,modulo_id,m3_camiones_dia,m3_camiones_acum,
       tms_camiones_dia,tms_camiones_acum
FROM reclamo.v_camiones_acumulado
WHERE campaña_id=10 AND modulo_id IN (81,87)
ORDER BY modulo_id,fecha;

SELECT * FROM reclamo.log_automatizacion
WHERE campaña_id=10 AND modulo_id IN (81,87)
ORDER BY fecha_evento,log_id;

SELECT * FROM reclamo.log_ejecucion
WHERE procedimiento IN ('reclamo.sp_auto_congelar_modulos_nuevos',
                        'reclamo.sp_establecer_linea_base',
                        'reclamo.sp_auto_mantener_secuencia')
ORDER BY ejecucion_id;

-- Auditoría ampliada: filas con diferencia de línea base > 0,001 m³.
WITH previo AS (
    SELECT campaña_id,modulo_id,
           SUM(COALESCE(volumen_diario_m3,0)) AS m3_previo_esperado,
           COUNT(*) AS filas_pre_corte
    FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario
    WHERE CAST(fecha AS date)<@Corte
    GROUP BY campaña_id,modulo_id
)
SELECT mc.campaña_id,mc.pad_id,mc.modulo_id,mc.modulo_numero,
       mc.fecha_congelamiento,mc.fecha_linea_base,
       mc.m3_camiones_previo AS m3_previo_actual,
       COALESCE(p.m3_previo_esperado,0) AS m3_previo_esperado,
       COALESCE(p.m3_previo_esperado,0)-mc.m3_camiones_previo AS diferencia_linea_base,
       COALESCE(p.filas_pre_corte,0) AS filas_pre_corte
FROM reclamo.modulo_congelado mc
LEFT JOIN previo p ON p.campaña_id=mc.campaña_id AND p.modulo_id=mc.modulo_id
WHERE mc.campaña_id=10 AND mc.pad_id=2
  AND ABS(COALESCE(p.m3_previo_esperado,0)-mc.m3_camiones_previo)>0.001
ORDER BY mc.modulo_numero;
