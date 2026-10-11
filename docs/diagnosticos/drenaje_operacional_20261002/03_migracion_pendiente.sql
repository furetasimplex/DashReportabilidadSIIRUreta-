-- PLANTILLA BLOQUEADA. NO EJECUTADA. NO ES UN DESPLIEGUE LISTO.
-- Falta incorporar la definicion AUTORITATIVA test_v3 validada y su diff.
-- No usar el snapshot historico como candidato ni ejecutar este archivo en PROD.
-- Preparar backup 02, comparar firma/parametros/salida y completar los campos.
SET NOCOUNT ON;
SET XACT_ABORT ON;
DECLARE @aprobado bit=0, @persistir bit=0;
DECLARE @servidor_dev sysname=N'COMPLETAR_DEV', @base_dev sysname=N'COMPLETAR_DEV';
DECLARE @hash_previo varchar(64)='COMPLETAR_HASH_BACKUP';
DECLARE @ansi bit=NULL, @quoted bit=NULL;
DECLARE @alter_revisado nvarchar(max)=NULL;
-- @alter_revisado: ALTER PROCEDURE [inventar_SpcHidr].[sp_flujo_riego_drenaje]
-- + firma y cuerpo EXACTOS revisados de test_v3; sin GO, sin otras sentencias externas.
-- Conservar EXISTS de test_v2, fechas de riego, filtros, agregaciones y NULLs.
IF @aprobado<>1 OR @alter_revisado IS NULL OR @ansi IS NULL OR @quoted IS NULL
 THROW 51000, 'Plantilla incompleta o promocion no aprobada.',1;
IF @@SERVERNAME<>@servidor_dev OR DB_NAME()<>@base_dev
 THROW 51001, 'Conexion distinta del DEV aprobado.',1;
IF @@TRANCOUNT<>0 THROW 51002, 'Usar una sesion sin transaccion externa.',1;
DECLARE @id int=OBJECT_ID('inventar_SpcHidr.sp_flujo_riego_drenaje','P');
IF @id IS NULL THROW 51003, 'No existe el procedimiento destino.',1;
IF EXISTS(SELECT 1 FROM sys.crypt_properties WHERE major_id=@id)
 THROW 51004, 'Objeto firmado: falta plan explicito de refirma.',1;
IF OBJECT_ID('inventar_SpcHidr.v_drena_oxido_operacional','V') IS NULL
 OR OBJECT_ID('inventar_SpcHidr.v_drena_sulfuro_operacional','V') IS NULL
 THROW 51005, 'Faltan vistas operacionales.',1;
BEGIN TRY
 BEGIN TRANSACTION;
 DECLARE @lock int;
 EXEC @lock=sys.sp_getapplock @Resource=N'promocion_sp_flujo_riego_drenaje',
  @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=0;
 IF @lock<0 THROW 51006, 'Otra promocion esta en curso.',1;
 IF OBJECT_DEFINITION(@id) IS NULL
  OR CONVERT(varchar(64),HASHBYTES('SHA2_256',OBJECT_DEFINITION(@id)),2)<>@hash_previo
  THROW 51007, 'Definicion destino difiere del backup revisado.',1;
 IF @ansi=1 SET ANSI_NULLS ON; ELSE SET ANSI_NULLS OFF;
 IF @quoted=1 SET QUOTED_IDENTIFIER ON; ELSE SET QUOTED_IDENTIFIER OFF;
 EXEC sys.sp_executesql @alter_revisado;
 SELECT OBJECT_DEFINITION(@id) AS definicion_instalada_en_transaccion;
 -- Ejecutar pruebas acordadas en ensayo separado; NO invocar SPs de negocio aqui.
 IF @persistir=1 COMMIT TRANSACTION; ELSE ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
 IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
