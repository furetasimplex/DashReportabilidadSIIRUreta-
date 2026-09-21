CREATE   PROCEDURE inventar_SpcHidr.sp_refrescar_historico_apilado_diario
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @FechaFin    date = DATEADD(DAY, -1, CAST(SYSUTCDATETIME() AS date));
    DECLARE @FechaInicio date = @FechaFin;

    EXEC inventar_SpcHidr.sp_refrescar_historico_apilado_test
         @FechaInicio   = @FechaInicio,
         @FechaFin      = @FechaFin,
         @DiasReproceso = 7;
END;