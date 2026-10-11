USE [inventar_SpcHidr]
GO
/****** Objeto: StoredProcedure [inventar_SpcHidr].[sp_actualizar_reporte_turno_cache] Fecha de script: 22-07-2026 17:27:00 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER   PROCEDURE [inventar_SpcHidr].[sp_actualizar_reporte_turno_cache]
    @fecha_inicio date,
    @fecha_fin date
AS
BEGIN
    SET NOCOUNT ON;

    DELETE FROM inventar_SpcHidr.reporte_turno_cache
    WHERE Fecha >= @fecha_inicio
      AND Fecha <  @fecha_fin;

    INSERT INTO inventar_SpcHidr.reporte_turno_cache (
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
-- NUEVAS COLUMNAS
        Fuente_Info_Quimica,
        Fuente_Info_Fisica,
  -- COLUMNAS EXISTENTES
        Muestra_Quimica,
        Muestra_Fisica
    )
    EXEC inventar_SpcHidr.sp_reporte_turno_test
        @fecha_inicio = @fecha_inicio,
        @fecha_fin = @fecha_fin;
END;