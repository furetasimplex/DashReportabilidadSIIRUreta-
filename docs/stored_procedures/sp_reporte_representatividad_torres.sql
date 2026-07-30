USE [inventar_SpcHidr]
GO
/****** Objeto: StoredProcedure [inventar_SpcHidr].[sp_reporte_representatividad_torres] Fecha de script: 22-07-2026 17:25:15 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
ALTER   PROCEDURE
    [inventar_SpcHidr].[sp_reporte_representatividad_torres]
    @fecha_inicio date,
    @fecha_fin date
AS
BEGIN
    SET NOCOUNT ON;

    IF @fecha_inicio IS NULL
       OR @fecha_fin IS NULL
       OR @fecha_inicio > @fecha_fin
    BEGIN
        THROW 50002,
              'Rango de fechas inválido para reporte de representatividad.',
              1;
    END;

    SELECT
        Dia,

        TM1_TurnoA_Quimico,
        TM1_TurnoA_Fisico,
        TM1_TurnoB_Quimico,
        TM1_TurnoB_Fisico,

        TM2_TurnoA_Quimico,
        TM2_TurnoA_Fisico,
        TM2_TurnoB_Quimico,
        TM2_TurnoB_Fisico,

        SRR_TurnoA_Quimico,
        SRR_TurnoA_Fisico,
        SRR_TurnoB_Quimico,
        SRR_TurnoB_Fisico,

        fecha_calculo

    FROM inventar_SpcHidr.representatividad_torres_resultado

    WHERE Dia >= @fecha_inicio
      AND Dia <= @fecha_fin

    ORDER BY Dia;
END;
