CREATE OR ALTER PROCEDURE inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test
    @Flota varchar(20), @Valor decimal(18,6), @VigenciaDesde date,
    @Motivo nvarchar(1000), @Usuario nvarchar(128)
AS
BEGIN
    SET NOCOUNT ON;
    EXEC inventar_SpcHidr.sp_registrar_parametro_factor_camiones_vigencia_test
        @Parametro='LIMITE_CARGA_AJUSTE', @Flota=@Flota, @Valor=@Valor,
        @VigenciaDesde=@VigenciaDesde, @Motivo=@Motivo, @Usuario=@Usuario;
END;
