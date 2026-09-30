CREATE OR ALTER PROCEDURE inventar_SpcHidr.sp_registrar_parametro_factor_camiones_vigencia_test
    @Parametro varchar(40),
    @Flota varchar(20),
    @Valor decimal(18,6),
    @VigenciaDesde date,
    @Motivo nvarchar(1000),
    @Usuario nvarchar(128)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF DB_NAME()<>N'inventar_SpcHidr' THROW 51000, 'Solo DEV.', 1;
    IF @Parametro IS NULL OR @Parametro NOT IN ('LIMITE_CARGA_AJUSTE','CARGA_NOMINAL_TMH_VIAJE')
        THROW 51018, 'Categoria de parametro no permitida.', 1;
    IF @Flota IS NULL OR @Flota NOT IN ('KOM','CAT') THROW 51010, 'Flota debe ser KOM o CAT.', 1;
    IF @Valor IS NULL OR @Valor<=0 THROW 51011, 'El limite debe ser mayor que cero.', 1;
    IF @VigenciaDesde IS NULL THROW 51012, 'Vigente desde es obligatorio.', 1;
    IF NULLIF(LTRIM(RTRIM(@Motivo)),N'') IS NULL OR NULLIF(LTRIM(RTRIM(@Usuario)),N'') IS NULL
        THROW 51013, 'Usuario y motivo son obligatorios.', 1;
    DECLARE @Propia bit=CASE WHEN @@TRANCOUNT=0 THEN 1 ELSE 0 END;
    IF @Propia=1 BEGIN TRANSACTION;
    BEGIN TRY
        DECLARE @Lock int, @N bigint;
        EXEC @Lock=sys.sp_getapplock @Resource='SIIR_FACTOR_CAMIONES_PARAMETROS_DEV',
            @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=15000;
        IF @Lock<0 THROW 51014, 'No fue posible bloquear los parametros; reintente.', 1;
        SELECT @N=COUNT_BIG(*) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (TABLOCKX,HOLDLOCK);
        DECLARE @Mensaje nvarchar(2048);
        IF EXISTS (SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
                   WHERE flota=@Flota AND parametro=@Parametro AND vigencia_desde=@VigenciaDesde)
        BEGIN
            SET @Mensaje=CONCAT('Ya existe una vigencia ',@Flota,' iniciada el ',CONVERT(varchar(10),@VigenciaDesde,105),'.');
            THROW 51015, @Mensaje, 1;
        END;
        DECLARE @Id bigint, @Anterior decimal(18,6), @Hasta date, @Siguiente date;
        IF (SELECT COUNT(*) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
            WHERE flota=@Flota AND parametro=@Parametro AND activo=1
              AND vigencia_desde<=@VigenciaDesde AND (vigencia_hasta IS NULL OR @VigenciaDesde<vigencia_hasta))<>1
            THROW 51016, 'La fecha debe estar cubierta por exactamente una vigencia existente.', 1;
        SELECT @Id=id,@Anterior=valor,@Hasta=vigencia_hasta
        FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
        WHERE flota=@Flota AND parametro=@Parametro AND activo=1
          AND vigencia_desde<=@VigenciaDesde AND (vigencia_hasta IS NULL OR @VigenciaDesde<vigencia_hasta);
        SELECT @Siguiente=MIN(vigencia_desde) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
        WHERE flota=@Flota AND parametro=@Parametro AND activo=1 AND vigencia_desde>@VigenciaDesde;
        IF @Hasta<>@Siguiente OR (@Hasta IS NULL AND @Siguiente IS NOT NULL) OR (@Hasta IS NOT NULL AND @Siguiente IS NULL)
            THROW 51017, 'Historia temporal inconsistente; revisar vigencias.', 1;
        DECLARE @Registro datetime2(7)=SYSDATETIME(), @Retro bit, @Fin date;
        SET @Retro=CASE WHEN @VigenciaDesde<CONVERT(date,@Registro) THEN 1 ELSE 0 END;
        UPDATE inventar_SpcHidr.factor_camiones_parametro_vigencia_test SET vigencia_hasta=@VigenciaDesde WHERE id=@Id;
        INSERT inventar_SpcHidr.factor_camiones_parametro_vigencia_test
            (flota,parametro,valor,vigencia_desde,vigencia_hasta,motivo,usuario_registro,fecha_registro)
        VALUES (@Flota,@Parametro,@Valor,@VigenciaDesde,@Siguiente,@Motivo,@Usuario,@Registro);
        -- Verifica continuidad del historial completo de esta flota.
        IF EXISTS (SELECT 1 FROM (
            SELECT vigencia_hasta, LEAD(vigencia_desde) OVER (ORDER BY vigencia_desde) siguiente
            FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
            WHERE flota=@Flota AND parametro=@Parametro AND activo=1
        ) h WHERE vigencia_hasta<>siguiente OR (vigencia_hasta IS NULL AND siguiente IS NOT NULL)
                   OR (vigencia_hasta IS NOT NULL AND siguiente IS NULL))
            THROW 51017, 'Historia temporal inconsistente; revisar vigencias.', 1;
        INSERT inventar_SpcHidr.factor_camiones_parametro_auditoria_test
            (flota,parametro,accion,valor_anterior,valor_nuevo,vigencia_desde,usuario,motivo,fecha_registro,es_retroactivo)
        VALUES (@Flota,@Parametro,'NUEVA_VIGENCIA',@Anterior,@Valor,@VigenciaDesde,@Usuario,@Motivo,@Registro,@Retro);
        SELECT @Fin=MAX(Fecha) FROM inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test;
        IF @Propia=1 COMMIT;
        SELECT @Retro AS Es_Retroactivo, @VigenciaDesde AS Fecha_Inicio_Afectada,
               @Fin AS Fecha_Fin_Afectada, @Anterior AS Valor_Anterior, @Valor AS Valor_Nuevo;
    END TRY
    BEGIN CATCH
        IF @Propia=1 AND XACT_STATE()<>0 ROLLBACK;
        THROW;
    END CATCH;
END;
