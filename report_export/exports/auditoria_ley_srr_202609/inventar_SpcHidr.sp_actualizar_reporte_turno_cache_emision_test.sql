
/* ============================================================================
   ACTUALIZADOR DE LA CACHÉ GEMELA
   ============================================================================ */
CREATE   PROCEDURE
    [inventar_SpcHidr].[sp_actualizar_reporte_turno_cache_emision_test]
    @fecha_inicio date,
    @fecha_fin    date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @fecha_inicio IS NULL OR @fecha_fin IS NULL
        THROW 51010, 'Debe informar @fecha_inicio y @fecha_fin.', 1;

    IF @fecha_inicio >= @fecha_fin
        THROW 51011, '@fecha_fin debe ser posterior a @fecha_inicio.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        DELETE FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test]
        WHERE Fecha >= @fecha_inicio
          AND Fecha <  @fecha_fin;

        INSERT INTO [inventar_SpcHidr].[reporte_turno_cache_emision_test]
        (
            Fecha,
            Campania,
            Material,
            Modulo,
            Avance,
            Turno,
            Apilado_TMS_Real,
            Apilado_TMS_Plan_Mensual,
            STOCK,
            MINA,
            SRR,
            CuT_Real,
            CuT_Plan_Mensual,
            CuT_Plan_Semanal,
            CuS_Real,
            CuS_Plan_Mensual,
            CuS_Plan_Semanal,
            Solubilidad_Real,
            Solubilidad_Plan_Mensual,
            Solubilidad_Plan_Semanal,
            CO3_Real,
            CO3_Plan_Mensual,
            CO3_Plan_Semanal,
            CuFe_Real,
            CuFe_Plan_Mensual,
            CuFe_Plan_Semanal,
            FeT_Real,
            FeS_Real,
            ConsH_Real,
            Malla_Menos_1_2_Real,
            Malla_Menos_1_2_Plan_Semanal,
            Malla_Menos_100_Real,
            Malla_Menos_100_Plan_Mensual,
            Malla_Menos_100_Plan_Semanal,
            CaolBeta_Real,
            CaolBeta_Plan_Mensual,
            CaolBeta_Plan_Semanal,
            Dosis_Acido_Ideal_TM,
            Dosis_Acido_Programa_Semanal,
            Fuente_Info_Quimica,
            Fuente_Info_Fisica,
            Muestra_Quimica,
            Muestra_Fisica
        )
        EXEC [inventar_SpcHidr].[sp_reporte_turno_emision_test]
            @fecha_inicio = @fecha_inicio,
            @fecha_fin    = @fecha_fin;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        THROW;
    END CATCH;
END;
