-- PREPARADO, NO EJECUTADO. Guardar TODOS los resultsets en archivos sin truncar.
-- Esta consulta no crea una tabla de backup ni cambia objetos.
SET NOCOUNT ON;
SELECT @@SERVERNAME AS servidor, DB_NAME() AS base_actual, SYSDATETIMEOFFSET() AS extraido_en;
SELECT SCHEMA_NAME(o.schema_id) AS esquema, o.name, o.object_id, o.modify_date,
 m.uses_ansi_nulls, m.uses_quoted_identifier, m.is_schema_bound, m.execute_as_principal_id,
 o.principal_id AS propietario_objeto,
 CONVERT(varchar(64), HASHBYTES('SHA2_256',m.definition),2) AS sha256_utf16le,
 m.definition
FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
WHERE o.schema_id=SCHEMA_ID('inventar_SpcHidr')
 AND o.name IN ('sp_flujo_riego_drenaje','sp_flujo_riego_drenaje_test_v2',
               'sp_flujo_riego_drenaje_test_v3','v_drena_oxido_operacional','v_drena_sulfuro_operacional');
SELECT p.* FROM sys.parameters p
WHERE p.object_id IN (OBJECT_ID('inventar_SpcHidr.sp_flujo_riego_drenaje'),
                     OBJECT_ID('inventar_SpcHidr.sp_flujo_riego_drenaje_test_v3'));
SELECT dp.*, USER_NAME(dp.grantee_principal_id) AS destinatario,
 USER_NAME(dp.grantor_principal_id) AS otorgante
FROM sys.database_permissions dp
WHERE dp.class=1 AND dp.major_id=OBJECT_ID('inventar_SpcHidr.sp_flujo_riego_drenaje');
SELECT * FROM sys.crypt_properties
WHERE major_id=OBJECT_ID('inventar_SpcHidr.sp_flujo_riego_drenaje');
-- Verificar definiciones no NULL (permisos/cifrado), hash, opciones SET, firma,
-- parametros y contrato de salida antes de preparar ALTER y su inverso.
