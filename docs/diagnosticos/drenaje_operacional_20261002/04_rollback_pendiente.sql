-- PLANTILLA BLOQUEADA. PREPARADA, NO EJECUTADA. SOLO DEV AUTORIZADO.
-- Restaurar mediante ALTER, sin DROP/CREATE para conservar identidad/permisos.
SET NOCOUNT ON;
SET XACT_ABORT ON;
DECLARE @aprobado bit=0, @persistir bit=0;
DECLARE @servidor_dev sysname=N'COMPLETAR_DEV', @base_dev sysname=N'COMPLETAR_DEV';
DECLARE @hash_instalado varchar(64)='COMPLETAR_HASH_POST_MIGRACION';
DECLARE @ansi_original bit=NULL, @quoted_original bit=NULL;
DECLARE @alter_original nvarchar(max)=NULL;
-- Completar desde backup 02: cambiar SOLO CREATE/CREATE OR ALTER por ALTER
-- en el encabezado, manteniendo nombre, firma, cuerpo y EXECUTE AS originales.
IF @aprobado<>1 OR @alter_original IS NULL OR @ansi_original IS NULL OR @quoted_original IS NULL
 THROW 51100, 'Rollback incompleto o no aprobado.',1;
IF @@SERVERNAME<>@servidor_dev OR DB_NAME()<>@base_dev
 THROW 51101, 'Conexion distinta del DEV aprobado.',1;
IF @@TRANCOUNT<>0 THROW 51102, 'Usar una sesion sin transaccion externa.',1;
DECLARE @id int=OBJECT_ID('inventar_SpcHidr.sp_flujo_riego_drenaje','P');
IF @id IS NULL THROW 51103, 'No existe procedimiento destino.',1;
IF EXISTS(SELECT 1 FROM sys.crypt_properties WHERE major_id=@id)
 THROW 51104, 'Objeto firmado: revisar restauracion de firma.',1;
BEGIN TRY
 BEGIN TRANSACTION;
 DECLARE @lock int;
 EXEC @lock=sys.sp_getapplock @Resource=N'promocion_sp_flujo_riego_drenaje',
  @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=0;
 IF @lock<0 THROW 51105, 'Otra promocion esta en curso.',1;
 IF OBJECT_DEFINITION(@id) IS NULL
  OR CONVERT(varchar(64),HASHBYTES('SHA2_256',OBJECT_DEFINITION(@id)),2)<>@hash_instalado
  THROW 51106, 'Destino cambio desde la migracion: no sobrescribir.',1;
 IF @ansi_original=1 SET ANSI_NULLS ON; ELSE SET ANSI_NULLS OFF;
 IF @quoted_original=1 SET QUOTED_IDENTIFIER ON; ELSE SET QUOTED_IDENTIFIER OFF;
 EXEC sys.sp_executesql @alter_original;
 SELECT OBJECT_DEFINITION(@id) AS definicion_restaurada_en_transaccion;
 IF @persistir=1 COMMIT TRANSACTION; ELSE ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
 IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
