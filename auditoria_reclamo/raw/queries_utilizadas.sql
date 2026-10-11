-- 00_conexion.csv
SELECT DB_NAME() AS database_actual, SUSER_SNAME() AS usuario, @@SERVERNAME AS servidor;
GO

-- 01_objetos_bd.csv
SELECT s.name AS esquema, o.name AS objeto, o.type_desc, o.create_date, o.modify_date
FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
WHERE s.name='reclamo' OR o.name LIKE '%reclamo%' OR o.name LIKE '%rotopala%'
   OR o.name LIKE '%cv25%' OR o.name LIKE '%camion%' OR o.name LIKE '%topografia%'
ORDER BY s.name,o.type_desc,o.name;
GO

-- 02_columnas_bd.csv
SELECT s.name AS esquema,t.name AS tabla,c.column_id,c.name AS columna,ty.name AS tipo,
       c.max_length,c.precision,c.scale,c.is_nullable,dc.definition AS valor_default
FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
JOIN sys.columns c ON c.object_id=t.object_id
JOIN sys.types ty ON ty.user_type_id=c.user_type_id
LEFT JOIN sys.default_constraints dc ON dc.parent_object_id=c.object_id AND dc.parent_column_id=c.column_id
WHERE s.name='reclamo' ORDER BY t.name,c.column_id;
GO

-- 03_indices.csv
SELECT s.name AS esquema,t.name AS tabla,i.name AS indice,i.is_primary_key,i.is_unique,
       i.type_desc,c.name AS columna,ic.key_ordinal,ic.is_included_column
FROM sys.indexes i JOIN sys.tables t ON t.object_id=i.object_id
JOIN sys.schemas s ON s.schema_id=t.schema_id
JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
WHERE s.name='reclamo' ORDER BY t.name,i.name,ic.key_ordinal,c.column_id;
GO

-- 04_foreign_keys.csv
SELECT fk.name AS FK,OBJECT_SCHEMA_NAME(fk.parent_object_id) AS esquema_hijo,
       OBJECT_NAME(fk.parent_object_id) AS tabla_hijo,cp.name AS columna_hijo,
       OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS esquema_padre,
       OBJECT_NAME(fk.referenced_object_id) AS tabla_padre,cr.name AS columna_padre
FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id=fk.object_id
JOIN sys.columns cp ON cp.object_id=fkc.parent_object_id AND cp.column_id=fkc.parent_column_id
JOIN sys.columns cr ON cr.object_id=fkc.referenced_object_id AND cr.column_id=fkc.referenced_column_id
WHERE OBJECT_SCHEMA_NAME(fk.parent_object_id)='reclamo'
   OR OBJECT_SCHEMA_NAME(fk.referenced_object_id)='reclamo'
ORDER BY esquema_hijo,tabla_hijo,FK;
GO

-- 05_constraints.csv
SELECT OBJECT_SCHEMA_NAME(cc.parent_object_id) AS esquema,
       OBJECT_NAME(cc.parent_object_id) AS tabla,cc.name AS constraint_name,cc.definition
FROM sys.check_constraints cc WHERE OBJECT_SCHEMA_NAME(cc.parent_object_id)='reclamo'
ORDER BY tabla,constraint_name;
GO

-- 06_dependencias.csv
SELECT OBJECT_SCHEMA_NAME(d.referencing_id) AS esquema_origen,
       OBJECT_NAME(d.referencing_id) AS objeto_origen,d.referenced_server_name,
       d.referenced_database_name,d.referenced_schema_name AS esquema_destino,
       d.referenced_entity_name AS objeto_destino,o.type_desc AS tipo_origen
FROM sys.sql_expression_dependencies d LEFT JOIN sys.objects o ON o.object_id=d.referencing_id
WHERE OBJECT_SCHEMA_NAME(d.referencing_id)='reclamo' OR d.referenced_schema_name='reclamo'
ORDER BY esquema_origen,objeto_origen,esquema_destino,objeto_destino;
GO

-- 07_configuracion.csv
SELECT * FROM reclamo.configuracion ORDER BY clave;
GO

-- 08_topologia_pad.csv
SELECT * FROM reclamo.topologia_pad ORDER BY pad_id;
GO

-- 09_rotopala.csv
SELECT * FROM reclamo.rotopala ORDER BY rotopala_id;
GO

-- 10_camiones_completitud.csv
SELECT COUNT(*) AS total,
 SUM(CASE WHEN m3_thm IS NOT NULL THEN 1 ELSE 0 END) AS con_m3_thm,
 SUM(CASE WHEN m3_oficial IS NOT NULL THEN 1 ELSE 0 END) AS con_m3_oficial,
 SUM(CASE WHEN tms_thm IS NOT NULL THEN 1 ELSE 0 END) AS con_tms_thm,
 SUM(CASE WHEN tms_oficial IS NOT NULL THEN 1 ELSE 0 END) AS con_tms_oficial
FROM reclamo.camiones_reclamo;
GO

-- 11_camiones_ultimos_200.csv
SELECT TOP (200) fecha,[campaña_id] AS campana_id,pad_id,modulo_id,m3_geomensura,
 tms_geomensura,m3_thm,tms_thm,fuente_oficial,m3_oficial,tms_oficial,estado
FROM reclamo.camiones_reclamo ORDER BY fecha DESC,modulo_id;
GO

-- 12_triggers_camiones.csv
SELECT OBJECT_SCHEMA_NAME(tr.parent_id) AS esquema,OBJECT_NAME(tr.parent_id) AS tabla,
 tr.name AS trigger_name,OBJECT_DEFINITION(tr.object_id) AS definicion
FROM sys.triggers tr WHERE tr.parent_id=OBJECT_ID('reclamo.camiones_reclamo');
GO

-- 13_escritores_camiones_oficial.csv
SELECT OBJECT_SCHEMA_NAME(o.object_id) AS esquema,o.name,o.type_desc,sm.definition
FROM sys.objects o JOIN sys.sql_modules sm ON sm.object_id=o.object_id
WHERE sm.definition LIKE '%m3_oficial%' OR sm.definition LIKE '%tms_oficial%'
ORDER BY esquema,o.name;
GO

-- 14_referencias_publicacion.csv
SELECT OBJECT_SCHEMA_NAME(o.object_id) AS esquema,o.name,o.type_desc
FROM sys.objects o JOIN sys.sql_modules sm ON sm.object_id=o.object_id
WHERE sm.definition LIKE '%v_reclamo_para_conciliados%'
   OR sm.definition LIKE '%TMS_Rotopala_1_Real%'
   OR sm.definition LIKE '%TMS_Rotopala_2_Real%'
   OR sm.definition LIKE '%Camiones_TMS_Reclamo_Oxidos%'
   OR sm.definition LIKE '%Camiones_TMS_Reclamo_Sulfuros%'
ORDER BY esquema,o.name;
GO

-- 15_objetos_reclamo_antiguos.csv
SELECT s.name AS esquema,o.name AS objeto,o.type_desc,o.create_date,o.modify_date,
 CASE WHEN EXISTS(SELECT 1 FROM sys.sql_expression_dependencies d WHERE d.referenced_id=o.object_id)
      THEN 'REFERENCIADA' ELSE 'NO_REFERENCIADA' END AS clasificacion_dependencia
FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
WHERE o.name LIKE '%reclamo%' AND s.name<>'reclamo'
ORDER BY s.name,o.name;
GO

-- data_samples/topografia_fuente_julio.csv
SELECT * FROM inventar_SpcHidr.control_reclamo_diario
WHERE CAST(fecha AS date) BETWEEN '2026-07-01' AND '2026-07-31'
ORDER BY fecha,pad_id,[campaña_id],modulo_id;
GO

-- data_samples/topografia_sincronizada_julio.csv
SELECT * FROM reclamo.topografia_avance
WHERE fecha_medicion BETWEEN '2026-07-01' AND '2026-07-31'
ORDER BY fecha_medicion,pad_id,[campaña_id],modulo_id;
GO

-- data_samples/topografia_resuelta_julio.csv
SELECT * FROM reclamo.v_topografia_resuelta
WHERE fecha_medicion BETWEEN '2026-07-01' AND '2026-07-31'
ORDER BY fecha_medicion,pad_id,[campaña_id],modulo_id;
GO

-- data_samples/camiones_julio.csv
SELECT * FROM reclamo.camiones_reclamo WHERE fecha BETWEEN '2026-07-01' AND '2026-07-31'
ORDER BY fecha,[campaña_id],modulo_id;
GO

-- data_samples/cv25_julio.csv
SELECT * FROM reclamo.cv25_diario WHERE fecha BETWEEN '2026-07-01' AND '2026-07-31' ORDER BY fecha;
GO

-- data_samples/horas_rotopala_julio.csv
SELECT * FROM reclamo.rotopala_horas_turno
WHERE fecha_turno BETWEEN '2026-07-01' AND '2026-07-31'
ORDER BY fecha_turno,turno,rotopala_id;
GO

-- data_samples/calculo_diario_julio.csv
SELECT * FROM reclamo.calculo_diario
WHERE fecha_operacion BETWEEN '2026-07-01' AND '2026-07-31'
ORDER BY fecha_operacion,pad_id,modulo_numero;
GO

-- data_samples/calculo_pad2_camp8_julio.csv
SELECT * FROM reclamo.calculo_diario
WHERE fecha_operacion BETWEEN '2026-07-01' AND '2026-07-31' AND pad_id=2 AND [campaña_id]=8
ORDER BY fecha_operacion,modulo_numero;
GO

-- data_samples/cuadratura_modulos.csv
SELECT * FROM reclamo.v_cuadratura_modulo ORDER BY pad_id,[campaña_id],modulo_numero;
GO

-- data_samples/cuadratura_pad2_camp8.csv
SELECT * FROM reclamo.v_cuadratura_modulo WHERE pad_id=2 AND [campaña_id]=8 ORDER BY modulo_numero;
GO

-- data_samples/conciliados_preview_julio.csv
SELECT * FROM reclamo.v_reclamo_para_conciliados
WHERE fecha_operacion BETWEEN '2026-07-01' AND '2026-07-31'
ORDER BY fecha_operacion,pad_id,modulo_numero;
GO

-- data_samples/datos_conciliados_julio.csv
SELECT * FROM inventar_SpcHidr.Datos_conciliados_of
WHERE CAST(Fecha AS date) BETWEEN '2026-07-01' AND '2026-07-31' ORDER BY Fecha;
GO

-- data_samples/secuencia_pad2_camp8.csv
SELECT * FROM reclamo.secuencia_rotopala WHERE [campaña_id]=8 AND pad_id=2
ORDER BY orden_secuencia,modulo_id;
GO

-- data_samples/modulos_congelados_pad2_camp8.csv
SELECT * FROM reclamo.modulo_congelado WHERE pad_id=2 AND [campaña_id]=8
ORDER BY modulo_numero,modulo_id;
GO

-- data_samples/vista_resumen_cv25_julio.csv
SELECT * FROM inventar_SpcHidr.vista_resumen_datos_filtrados
WHERE CAST(fecha_turno AS date) BETWEEN '2026-07-01' AND '2026-07-31' ORDER BY fecha_turno;
GO

-- data_samples/datos_filtrados_frecuencia_julio.csv
SELECT CAST(fecha_turno AS date) AS fecha,COUNT(*) AS filas,
 MIN(fecha_turno) AS primera_marca,MAX(fecha_turno) AS ultima_marca,
 COUNT(DISTINCT turno) AS turnos
FROM inventar_SpcHidr.datos_filtrados
WHERE CAST(fecha_turno AS date) BETWEEN '2026-07-01' AND '2026-07-31'
GROUP BY CAST(fecha_turno AS date) ORDER BY fecha;
GO

-- data_samples/comparacion_calculo_preview_publicado_julio.csv
WITH calc AS (
 SELECT fecha_operacion AS fecha,
  SUM(CASE WHEN pad_id=1 THEN tms_rotopala_dia ELSE 0 END) AS calc_r1,
  SUM(CASE WHEN pad_id=2 THEN tms_rotopala_dia ELSE 0 END) AS calc_r2,
  SUM(CASE WHEN pad_id=1 THEN tms_camiones_dia ELSE 0 END) AS calc_cam_ox,
  SUM(CASE WHEN pad_id=2 THEN tms_camiones_dia ELSE 0 END) AS calc_cam_su
 FROM reclamo.calculo_diario
 WHERE fecha_operacion BETWEEN '2026-07-01' AND '2026-07-31' GROUP BY fecha_operacion
), prev AS (
 SELECT fecha_operacion AS fecha,
  SUM(CASE WHEN pad_id=1 THEN tonelaje_reclamado_diario ELSE 0 END) AS prev_r1,
  SUM(CASE WHEN pad_id=2 THEN tonelaje_reclamado_diario ELSE 0 END) AS prev_r2,
  SUM(CASE WHEN pad_id=1 THEN tonelaje_camiones_diario ELSE 0 END) AS prev_cam_ox,
  SUM(CASE WHEN pad_id=2 THEN tonelaje_camiones_diario ELSE 0 END) AS prev_cam_su
 FROM reclamo.v_reclamo_para_conciliados
 WHERE fecha_operacion BETWEEN '2026-07-01' AND '2026-07-31' GROUP BY fecha_operacion
)
SELECT d.Fecha,c.calc_r1,p.prev_r1,d.TMS_Rotopala_1_Real,
 c.calc_r2,p.prev_r2,d.TMS_Rotopala_2_Real,c.calc_cam_ox,p.prev_cam_ox,
 d.Camiones_TMS_Reclamo_Oxidos,c.calc_cam_su,p.prev_cam_su,d.Camiones_TMS_Reclamo_Sulfuros,
 COALESCE(c.calc_r1,0)-COALESCE(d.TMS_Rotopala_1_Real,0) AS dif_calc_pub_r1,
 COALESCE(c.calc_r2,0)-COALESCE(d.TMS_Rotopala_2_Real,0) AS dif_calc_pub_r2,
 COALESCE(c.calc_cam_ox,0)-COALESCE(d.Camiones_TMS_Reclamo_Oxidos,0) AS dif_calc_pub_cam_ox,
 COALESCE(c.calc_cam_su,0)-COALESCE(d.Camiones_TMS_Reclamo_Sulfuros,0) AS dif_calc_pub_cam_su
FROM inventar_SpcHidr.Datos_conciliados_of d
LEFT JOIN calc c ON c.fecha=CAST(d.Fecha AS date) LEFT JOIN prev p ON p.fecha=CAST(d.Fecha AS date)
WHERE CAST(d.Fecha AS date) BETWEEN '2026-07-01' AND '2026-07-31' ORDER BY d.Fecha;
GO

-- raw/definiciones_reclamo_completas.csv
SELECT s.name AS esquema,o.name AS objeto,o.type_desc,sm.definition
FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.sql_modules sm ON sm.object_id=o.object_id
WHERE s.name='reclamo' ORDER BY o.type_desc,o.name;
GO

-- raw/definiciones_externas_relevantes.csv
SELECT s.name AS esquema,o.name AS objeto,o.type_desc,sm.definition
FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.sql_modules sm ON sm.object_id=o.object_id
WHERE (s.name='inventar_SpcHidr' AND o.name IN
 ('sp_mantiene_datos_conciliados_emision_test','sp_mantiene_datos_conciliados_of',
  'vista_reclamo_diario_calculado','v_reclamo_camiones_por_modulo'))
 OR sm.definition LIKE '%v_reclamo_para_conciliados%'
 OR sm.definition LIKE '%TMS_Rotopala_1_Real%'
 OR sm.definition LIKE '%Camiones_TMS_Reclamo_Oxidos%';
GO
