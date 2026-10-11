-- Ejecutadas mediante SQLAlchemy con :desde=2026-06-01, :hasta=2026-09-10; :name identifica cada objeto en definitions_hashes.json. Solo SELECT.

SELECT DB_NAME() AS db;

SELECT COUNT_BIG(*) AS filas,SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,COUNT(transferencia_cu_t_d) AS transferencia_no_null FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta;

SELECT fecha,pad_id,parcela_id,nro_parcela_pad,campana_id,estado_asignacion,flujo_m3_d,cu_drenaje_gl,cu_refino_gl,delta_cu_gl,transferencia_cu_t_d FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta ORDER BY fecha,pad_id,parcela_id;

SELECT fecha,COUNT_BIG(*) AS filas,SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,COUNT(transferencia_cu_t_d) AS transferencia_no_null FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY fecha ORDER BY fecha;

SELECT pad_id,COUNT_BIG(*) AS filas,SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,COUNT(transferencia_cu_t_d) AS transferencia_no_null FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY pad_id ORDER BY pad_id;

SELECT pad_id,parcela_id,nro_parcela_pad,COUNT_BIG(*) AS filas,SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,COUNT(transferencia_cu_t_d) AS transferencia_no_null FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY pad_id,parcela_id,nro_parcela_pad ORDER BY pad_id,parcela_id,nro_parcela_pad;

SELECT fecha,pad_id,COUNT_BIG(*) AS filas,SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,COUNT(transferencia_cu_t_d) AS transferencia_no_null FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY fecha,pad_id ORDER BY fecha,pad_id;

SELECT estado_asignacion,COUNT_BIG(*) AS filas,SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,COUNT(transferencia_cu_t_d) AS transferencia_no_null FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta GROUP BY estado_asignacion ORDER BY estado_asignacion;

SELECT COUNT_BIG(*) AS filas,SUM(transferencia_cu_t_d) AS transferencia FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta AND estado_asignacion='FUERA_VENTANA_RIEGO' AND flujo_m3_d>0;

SELECT OBJECT_DEFINITION(OBJECT_ID(:name)) AS definition;

SELECT COUNT_BIG(*) AS diferencias FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE fecha BETWEEN :desde AND :hasta AND transferencia_cu_t_d <> CAST(CAST(flujo_m3_d*(cu_drenaje_gl-cu_refino_gl) AS decimal(31,6))/CAST(1000.0 AS decimal(5,1)) AS decimal(38,9));
