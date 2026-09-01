/*
Corrige exclusivamente las 12 dependencias detectadas por el startup check.
PATCH_VERSION: 2026-09-01.4

Uso seguro:
  1. Ejecutar con @Aplicar = 0 para preflight (no modifica nada).
  2. Revisar el resultset de cambios.
  3. Cambiar @Aplicar = 1 y ejecutar nuevamente.
  4. Ejecutar: python scripts/smoke_test_production_db.py

El cambio se ejecuta dentro de una transacción y hace rollback ante cualquier
error. No modifica tablas ni datos de negocio.
*/

USE [inventar_SpcHidr_PROD];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Aplicar bit = 0; -- CAMBIAR A 1 SOLO DESPUES DE REVISAR EL PREFLIGHT

IF DB_NAME() <> N'inventar_SpcHidr_PROD'
    THROW 51000, 'Base incorrecta: este parche solo corre en inventar_SpcHidr_PROD.', 1;

IF DB_ID(N'PROD_SIIR') IS NULL
    THROW 51001, 'No existe PROD_SIIR en este servidor.', 1;

DECLARE @Objetivos table (
    deployment_order int NOT NULL UNIQUE,
    schema_name sysname NOT NULL,
    object_name sysname NOT NULL,
    cambio varchar(20) NOT NULL,
    PRIMARY KEY (schema_name, object_name)
);

INSERT @Objetivos (deployment_order, schema_name, object_name, cambio)
VALUES
    (1, N'dbo', N'v_imp_conciliacion_chancado', 'SIIR'),
    (2, N'inventar_SpcHidr', N'v_conciliacion_chancado_v2', 'SIIR'),
    (3, N'inventar_SpcHidr', N'v_srr_tms_origen_turno_emision_test', 'SIIR'),
    (4, N'inventar_SpcHidr', N'vw_drena_quimica_ingest', 'INVENTAR'),
    (5, N'inventar_SpcHidr', N'vw_riego_diario_ingest', 'INVENTAR'),
    (6, N'inventar_SpcHidr', N'sp_mantiene_datos_conciliados_emision_test', 'SIIR'),
    (7, N'inventar_SpcHidr', N'sp_mantiene_datos_conciliados_of', 'SIIR'),
    (8, N'inventar_SpcHidr', N'sp_reporte_turno_emision_srr_origen_sim_test', 'SIIR'),
    (9, N'inventar_SpcHidr', N'sp_reporte_turno_emision_test', 'SIIR'),
    (10, N'inventar_SpcHidr', N'sp_reporte_turno_test', 'SIIR'),
    (11, N'inventar_SpcHidr', N'sp_calcular_balance_flujos', 'SIIR'),
    (12, N'inventar_SpcHidr', N'sp_calcular_balance_flujos_copy1', 'SIIR');

IF EXISTS (
    SELECT 1
    FROM @Objetivos AS t
    WHERE OBJECT_ID(QUOTENAME(t.schema_name) + N'.' + QUOTENAME(t.object_name)) IS NULL
)
BEGIN
    SELECT t.schema_name, t.object_name
    FROM @Objetivos AS t
    WHERE OBJECT_ID(QUOTENAME(t.schema_name) + N'.' + QUOTENAME(t.object_name)) IS NULL;
    THROW 51002, 'Faltan modulos objetivo; no se aplico ningun cambio.', 1;
END;

DECLARE @Cambios table (
    row_id int PRIMARY KEY,
    modulo nvarchar(517) NOT NULL,
    cambio varchar(20) NOT NULL,
    definition_before nvarchar(max) NOT NULL,
    definition_after nvarchar(max) NOT NULL
);

INSERT @Cambios (row_id, modulo, cambio, definition_before, definition_after)
SELECT
    t.deployment_order,
    QUOTENAME(t.schema_name) + N'.' + QUOTENAME(t.object_name),
    t.cambio,
    m.definition,
    CASE t.cambio
        WHEN 'SIIR' THEN
            CASE
                -- El objeto fue renombrado históricamente con sp_rename, pero
                -- sys.sql_modules conservó CREATE VIEW dbo.test_imp. Si no se
                -- normaliza, el ALTER intenta modificar un objeto inexistente.
                WHEN t.schema_name = N'dbo'
                 AND t.object_name = N'v_imp_conciliacion_chancado'
                THEN REPLACE(
                    REPLACE(m.definition, N'DEV_SIIR', N'PROD_SIIR'),
                    N'CREATE VIEW dbo.test_imp',
                    N'CREATE VIEW dbo.v_imp_conciliacion_chancado'
                )
                ELSE REPLACE(m.definition, N'DEV_SIIR', N'PROD_SIIR')
            END
        WHEN 'INVENTAR' THEN REPLACE(
            REPLACE(
                m.definition,
                N'[inventar_SpcHidr].[inventar_SpcHidr].',
                N'[inventar_SpcHidr].'
            ),
            N'inventar_SpcHidr.inventar_SpcHidr.',
            N'inventar_SpcHidr.'
        )
    END
FROM @Objetivos AS t
JOIN sys.objects AS o
  ON o.object_id = OBJECT_ID(QUOTENAME(t.schema_name) + N'.' + QUOTENAME(t.object_name))
JOIN sys.sql_modules AS m
  ON m.object_id = o.object_id;

-- Un módulo SIIR sin cambio es válido si ya apunta a PROD_SIIR. Esto vuelve
-- idempotente el runbook: puede ejecutarse cada vez que se despliega la app.
IF EXISTS (
    SELECT 1
    FROM @Cambios
    WHERE definition_before = definition_after
      AND cambio = 'SIIR'
      AND definition_after NOT LIKE N'%PROD[_]SIIR%'
)
BEGIN
    SELECT modulo, cambio
    FROM @Cambios
    WHERE definition_before = definition_after
      AND cambio = 'SIIR'
      AND definition_after NOT LIKE N'%PROD[_]SIIR%';
    THROW 51003, 'Modulo SIIR sin referencia DEV ni PROD; revisar manualmente.', 1;
END;

-- Los módulos cuyo before/after es idéntico ya están sincronizados.
DELETE FROM @Cambios WHERE definition_before = definition_after;

SELECT
    modulo,
    cambio,
    LEN(definition_before) AS largo_antes,
    LEN(definition_after) AS largo_despues,
    (LEN(definition_before) - LEN(REPLACE(definition_before, N'DEV_SIIR', N'')))
        / LEN(N'DEV_SIIR') AS ocurrencias_dev_siir,
    (LEN(definition_before) - LEN(REPLACE(
        definition_before, N'inventar_SpcHidr.inventar_SpcHidr.', N''
    ))) / LEN(N'inventar_SpcHidr.inventar_SpcHidr.') AS ocurrencias_inventar_dev
FROM @Cambios
ORDER BY row_id;

IF @Aplicar = 0
BEGIN
    IF NOT EXISTS (SELECT 1 FROM @Cambios)
        PRINT 'PREFLIGHT OK. Produccion ya esta sincronizada; cero cambios pendientes.';
    ELSE
        PRINT 'PREFLIGHT OK. No se modifico la base. Cambie @Aplicar a 1 para aplicar.';
    RETURN;
END;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @i int = 1;
    DECLARE @max int = (SELECT MAX(row_id) FROM @Cambios);
    DECLARE @sql nvarchar(max);
    DECLARE @create_pos int;

    WHILE @i <= @max
    BEGIN
        SELECT @sql = definition_after FROM @Cambios WHERE row_id = @i;

        -- Las definiciones de sys.sql_modules empiezan con CREATE (posiblemente
        -- tras espacios). ALTER conserva permisos y propiedades del objeto.
        SET @create_pos = CHARINDEX(N'CREATE OR ALTER', UPPER(@sql));
        IF @create_pos > 0
            SET @sql = STUFF(
                @sql, @create_pos, LEN(N'CREATE OR ALTER'), N'ALTER'
            );
        ELSE
        BEGIN
            SET @create_pos = CHARINDEX(N'CREATE', UPPER(@sql));
            IF @create_pos = 0
                THROW 51004, 'Definicion sin CREATE; transaccion revertida.', 1;
            SET @sql = STUFF(@sql, @create_pos, LEN(N'CREATE'), N'ALTER');
        END;

        EXEC sys.sp_executesql @sql;
        SET @i += 1;
    END;

    -- Smoke estructural dentro de la misma transacción.
    IF EXISTS (
        SELECT 1
        FROM sys.sql_expression_dependencies
        WHERE referenced_database_name IN (N'DEV_SIIR', N'inventar_SpcHidr')
    )
        THROW 51005, 'Persisten referencias a DEV; transaccion revertida.', 1;

    IF EXISTS (
        SELECT 1
        FROM sys.sql_modules
        WHERE definition LIKE N'%DEV[_]SIIR%'
    )
        THROW 51006, 'Persiste DEV_SIIR en texto SQL; transaccion revertida.', 1;

    COMMIT TRANSACTION;
    PRINT 'APLICACION OK: 12 modulos corregidos y smoke estructural aprobado.';
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

-- Resultado esperado: cero filas en ambos resultsets.
SELECT DISTINCT
    OBJECT_SCHEMA_NAME(d.referencing_id) + N'.' + OBJECT_NAME(d.referencing_id) AS modulo,
    d.referenced_database_name,
    d.referenced_schema_name,
    d.referenced_entity_name
FROM sys.sql_expression_dependencies AS d
WHERE d.referenced_database_name IN (N'DEV_SIIR', N'inventar_SpcHidr');

SELECT
    OBJECT_SCHEMA_NAME(m.object_id) + N'.' + OBJECT_NAME(m.object_id) AS modulo
FROM sys.sql_modules AS m
WHERE m.definition LIKE N'%DEV[_]SIIR%';
GO
