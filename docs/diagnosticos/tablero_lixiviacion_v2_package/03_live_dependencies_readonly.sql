-- PREPARADO, NO EJECUTADO. Consulta manual futura en base autorizada.
-- Seccion A: metadatos locales. VIEW DEFINITION puede ser necesario para cobertura.
SELECT @@SERVERNAME AS servidor,DB_NAME() AS base_actual,
 HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION') AS view_definition;
SELECT s.name AS esquema,o.name,o.type_desc,o.create_date,o.modify_date,m.definition
FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
WHERE o.name IN ('vw_tablero_lixiviacion_final','vw_tablero_lixiviacion_final_v2',
 'vw_drena_concentrados_oxido_long','vw_drena_concentrados_sulfuro_long',
 'vw_riego_oxido_refino_base','vw_riego_sulfuro_refino_base');

-- Vistas/SP/funciones consumidores directos, columnas cuando SQL las registra.
SELECT OBJECT_SCHEMA_NAME(d.referencing_id) AS esquema_consumidor,
 OBJECT_NAME(d.referencing_id) AS consumidor,o.type_desc,
 d.referenced_server_name,d.referenced_database_name,d.referenced_schema_name,
 d.referenced_entity_name,d.referenced_id,d.referenced_minor_id,
 c.name AS columna_referenciada,d.is_caller_dependent,d.is_ambiguous
FROM sys.sql_expression_dependencies d
JOIN sys.objects o ON o.object_id=d.referencing_id
LEFT JOIN sys.columns c ON c.object_id=d.referenced_id AND c.column_id=d.referenced_minor_id
WHERE d.referenced_entity_name IN ('vw_tablero_lixiviacion_final','vw_tablero_lixiviacion_final_v2',
 'vw_drena_concentrados_oxido_long','vw_drena_concentrados_sulfuro_long',
 'vw_riego_oxido_refino_base','vw_riego_sulfuro_refino_base');

-- Transitivos locales; no confundir raiz como consumidor de si misma.
;WITH raices AS (
 SELECT object_id FROM sys.objects WHERE name IN
 ('vw_tablero_lixiviacion_final','vw_tablero_lixiviacion_final_v2')
), camino AS (
 SELECT object_id AS raiz,object_id AS nodo,0 AS nivel,
 CAST('/'+CAST(object_id AS varchar(20))+'/' AS varchar(max)) AS recorrido FROM raices
 UNION ALL
 SELECT c.raiz,d.referencing_id,c.nivel+1,
 CAST(c.recorrido+CAST(d.referencing_id AS varchar(20))+'/' AS varchar(max))
 FROM camino c JOIN sys.sql_expression_dependencies d ON d.referenced_id=c.nodo
 WHERE c.nivel<30 AND c.recorrido NOT LIKE '%/'+CAST(d.referencing_id AS varchar(20))+'/%'
)
SELECT DISTINCT OBJECT_SCHEMA_NAME(raiz) AS esquema_raiz,OBJECT_NAME(raiz) AS raiz,
 OBJECT_SCHEMA_NAME(nodo) AS esquema_consumidor,OBJECT_NAME(nodo) AS consumidor,nivel,recorrido
FROM camino WHERE nivel>0 OPTION(MAXRECURSION 100);

-- Complemento textual para SQL dinamico literal, SELECT * y aliases.
SELECT OBJECT_SCHEMA_NAME(m.object_id) AS esquema,o.name,o.type_desc,m.definition
FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id
WHERE m.definition LIKE '%vw_tablero_lixiviacion_final%'
 OR m.definition LIKE '%cu_drenaje_ppm%'
 OR m.definition LIKE '%cu_refino_ppm%'
 OR m.definition LIKE '%delta_cu_ppm%'
 OR m.definition LIKE '%transferencia_cu_kg_d%';
SELECT SCHEMA_NAME(schema_id) AS esquema,name,base_object_name FROM sys.synonyms;
-- referenced_minor_id=0 NO significa que ninguna columna se use.
-- No descubre consultas externas, SQL dinamico ensamblado, SSIS ni Power BI remoto.

-- Seccion B (OPCIONAL, SEPARADA): ejecutar individualmente si hay permisos.
-- Complementa detalle de columnas/is_select_all; puede fallar con dependencias
-- irresueltas o falta de permisos. No ejecuta el cuerpo del modulo inspeccionado.
-- Sustituir ESQUEMA.CONSUMIDOR por cada consumidor REAL hallado en seccion A.
-- SELECT * FROM sys.dm_sql_referenced_entities(N'ESQUEMA.CONSUMIDOR', N'OBJECT');

-- Seccion C (OPCIONAL, SEPARADA): SQL Agent. Dejar comentado hasta contar con
-- acceso autorizado a msdb (visibilidad depende de roles/permisos de Agent).
-- Ejecutar manualmente este SELECT solo, no solicitar privilegios automaticamente.
-- SELECT j.name AS job,j.enabled,s.step_id,s.step_name,s.subsystem,
--        s.database_name,s.command
-- FROM msdb.dbo.sysjobs j JOIN msdb.dbo.sysjobsteps s ON s.job_id=j.job_id
-- WHERE s.command LIKE '%vw_tablero_lixiviacion_final%'
--    OR s.command LIKE '%vw_drena_concentrados_oxido_long%'
--    OR s.command LIKE '%vw_drena_concentrados_sulfuro_long%'
--    OR s.command LIKE '%vw_riego_oxido_refino_base%'
--    OR s.command LIKE '%vw_riego_sulfuro_refino_base%';
-- Repetir busqueda por los consumidores indirectos hallados: un job puede llamar
-- un SP sin nombrar la vista. Revisar paquetes SSIS/PowerShell externos aparte.
