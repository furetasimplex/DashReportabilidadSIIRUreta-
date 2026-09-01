/*
Auditoría de solo lectura. Ejecutar conectado primero a inventar_SpcHidr y
luego a inventar_SpcHidr_PROD. No modifica objetos ni datos.
*/

SELECT
    @@SERVERNAME AS servidor,
    DB_NAME() AS base_actual,
    SYSDATETIMEOFFSET() AS fecha_auditoria;

-- Dependencias cross-database resueltas por SQL Server.
SELECT DISTINCT
    QUOTENAME(OBJECT_SCHEMA_NAME(d.referencing_id)) + N'.' +
        QUOTENAME(OBJECT_NAME(d.referencing_id)) AS modulo,
    o.type_desc,
    d.referenced_server_name,
    d.referenced_database_name,
    d.referenced_schema_name,
    d.referenced_entity_name
FROM sys.sql_expression_dependencies AS d
JOIN sys.objects AS o
  ON o.object_id = d.referencing_id
WHERE d.referenced_database_name IS NOT NULL
ORDER BY modulo, d.referenced_database_name,
         d.referenced_schema_name, d.referenced_entity_name;

-- Foco: módulos que fijan la base inventar de DEV o una variante PROD.
SELECT
    QUOTENAME(s.name) + N'.' + QUOTENAME(o.name) AS modulo,
    o.type_desc,
    d.referenced_server_name,
    d.referenced_database_name,
    d.referenced_schema_name,
    d.referenced_entity_name
FROM sys.sql_expression_dependencies AS d
JOIN sys.objects AS o
  ON o.object_id = d.referencing_id
JOIN sys.schemas AS s
  ON s.schema_id = o.schema_id
WHERE d.referenced_database_name IN
      (N'inventar_SpcHidr', N'inventar_SpcHidr_PROD')
ORDER BY modulo, d.referenced_entity_name;

-- Foco: módulos que todavía fijan DEV_SIIR.
SELECT
    QUOTENAME(s.name) + N'.' + QUOTENAME(o.name) AS modulo,
    o.type_desc,
    d.referenced_server_name,
    d.referenced_database_name,
    d.referenced_schema_name,
    d.referenced_entity_name
FROM sys.sql_expression_dependencies AS d
JOIN sys.objects AS o
  ON o.object_id = d.referencing_id
JOIN sys.schemas AS s
  ON s.schema_id = o.schema_id
WHERE d.referenced_database_name = N'DEV_SIIR'
ORDER BY modulo, d.referenced_entity_name;

-- Barrido textual complementario: detecta comentarios y SQL dinámico que el
-- catálogo de dependencias puede no resolver. Revisar manualmente los hits.
SELECT
    QUOTENAME(s.name) + N'.' + QUOTENAME(o.name) AS modulo,
    o.type_desc,
    m.definition
FROM sys.sql_modules AS m
JOIN sys.objects AS o
  ON o.object_id = m.object_id
JOIN sys.schemas AS s
  ON s.schema_id = o.schema_id
WHERE m.definition LIKE N'%inventar[_]SpcHidr.inventar[_]SpcHidr.%'
   OR m.definition LIKE N'%[[]inventar[_]SpcHidr[]].[[]inventar[_]SpcHidr[]].%'
   OR m.definition LIKE N'%DEV[_]SIIR.%'
   OR m.definition LIKE N'%[[]DEV[_]SIIR[]].%'
ORDER BY modulo;

