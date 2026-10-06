-- PREPARADO, NO EJECUTADO. Ejecutar solo en la conexion DEV autorizada.
-- Sin USE, DDL, DML ni ejecucion de procedimientos de negocio.
SET NOCOUNT ON;
SELECT @@SERVERNAME AS servidor, DB_NAME() AS base_actual,
       HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION') AS puede_ver_definiciones;

-- Aristas completas: conservar referencias cross-database y no resueltas.
SELECT OBJECT_SCHEMA_NAME(d.referencing_id) AS esquema_consumidor,
       OBJECT_NAME(d.referencing_id) AS consumidor,
       d.referencing_minor_id, d.referenced_server_name, d.referenced_database_name,
       d.referenced_schema_name, d.referenced_entity_name, d.referenced_id,
       d.referenced_minor_id, d.is_caller_dependent, d.is_ambiguous
FROM sys.sql_expression_dependencies d
WHERE d.referenced_entity_name IN (
 N'v_drena_oxido_unpivot', N'v_drena_sulfuro_unpivot',
 N'drena_concentrados_oxido', N'drena_concentrados_sulfuro',
 N'v_drena_oxido_operacional', N'v_drena_sulfuro_operacional',
 N'campana_parcela_control', N'sp_flujo_riego_drenaje',
 N'sp_flujo_riego_drenaje_test_v2', N'sp_flujo_riego_drenaje_test_v3')
ORDER BY esquema_consumidor, consumidor;

-- Consumidores indirectos locales. Los objetos cross-db/no resueltos quedan arriba.
;WITH raices AS (
 SELECT object_id FROM sys.objects WHERE name IN (
 N'v_drena_oxido_unpivot', N'v_drena_sulfuro_unpivot',
 N'drena_concentrados_oxido', N'drena_concentrados_sulfuro',
 N'v_drena_oxido_operacional', N'v_drena_sulfuro_operacional',
 N'campana_parcela_control', N'sp_flujo_riego_drenaje')
), recorrido AS (
 SELECT object_id AS raiz, object_id AS objeto, 0 AS nivel,
        CAST('/' + CAST(object_id AS varchar(20)) + '/' AS varchar(max)) AS camino
 FROM raices
 UNION ALL
 SELECT r.raiz, d.referencing_id, r.nivel + 1,
        CAST(r.camino + CAST(d.referencing_id AS varchar(20)) + '/' AS varchar(max))
 FROM recorrido r JOIN sys.sql_expression_dependencies d ON d.referenced_id = r.objeto
 WHERE r.nivel < 30
 AND r.camino NOT LIKE '%/' + CAST(d.referencing_id AS varchar(20)) + '/%'
)
SELECT DISTINCT OBJECT_SCHEMA_NAME(raiz) AS esquema_raiz, OBJECT_NAME(raiz) AS raiz,
 OBJECT_SCHEMA_NAME(objeto) AS esquema_consumidor, OBJECT_NAME(objeto) AS consumidor,
 nivel, camino
FROM recorrido ORDER BY raiz, nivel, consumidor OPTION (MAXRECURSION 100);

-- Complemento textual: incluye SQL dinamico literal y nombres de columnas.
-- Una coincidencia en comentario no prueba una dependencia ejecutable.
SELECT SCHEMA_NAME(o.schema_id) AS esquema, o.name, o.type_desc,
       o.modify_date, m.definition
FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
WHERE m.definition LIKE '%drena%'
   OR o.name IN ('sp_resumen_campana', 'sp_calcular_balance_flujos_modelo6_v2',
                 'vw_tablero_lixiviacion_final');
SELECT SCHEMA_NAME(schema_id) AS esquema, name, base_object_name
FROM sys.synonyms;
SELECT OBJECT_SCHEMA_NAME(c.object_id) AS esquema, OBJECT_NAME(c.object_id) AS objeto,
 c.name, TYPE_NAME(c.user_type_id) AS tipo
FROM sys.columns c
WHERE c.name IN ('fecha_ini_drenaje','fecha_fin_drenaje','fecha_operacional','fecha_registro_raw');
-- SQL dinamico construido, jobs/SSIS, otras bases y consumidores externos no quedan
-- exhaustivamente cubiertos por sys.sql_expression_dependencies.
