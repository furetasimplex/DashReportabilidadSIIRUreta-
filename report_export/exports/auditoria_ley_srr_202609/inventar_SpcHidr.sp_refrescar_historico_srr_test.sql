/* ============================================================
   PASO B - Procedimiento de refresco por ventana
   Mismo patron de @FechaInicio/@FechaFin/@DiasReproceso que
   sp_mantiene_datos_conciliados_of y sp_refrescar_historico_apilado_test.
============================================================ */
CREATE   PROCEDURE [inventar_SpcHidr].[sp_refrescar_historico_srr_test]
(
    @FechaInicio    date,
    @FechaFin       date,
    @DiasReproceso  int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;

    DECLARE @FechaLimiteReproceso date = DATEADD(DAY, -@DiasReproceso, @FechaFin);

    /* Borra solo la ventana de reproceso dentro del rango pedido */
    DELETE FROM [inventar_SpcHidr].[Historico_SRR_Diario]
    WHERE Fecha > @FechaLimiteReproceso
      AND Fecha BETWEEN @FechaInicio AND @FechaFin;

    /* Reinserta lo borrado + rellena fechas nuevas que aun no existan */
    INSERT INTO [inventar_SpcHidr].[Historico_SRR_Diario]
    (
        Fecha, SRR_TMH_Turno_A, SRR_TMH_Turno_B, SRR_TMH_Dia,
        SRR_TMS_TM1_Turno_A, SRR_TMS_TM2_Turno_A,
        SRR_TMS_TM1_Turno_B, SRR_TMS_TM2_Turno_B,
        SRR_TMS_Turno_A, SRR_TMS_Turno_B, SRR_TMS_Dia,
        Humedad_TM1_Usada, Humedad_TM2_Usada,
        Fecha_Humedad_TM1, Fuente_Humedad_TM1,
        Fecha_Humedad_TM2, Fuente_Humedad_TM2,
        TMH_CV001_Dia, TMH_CV002_Dia, TMH_CV003_Dia, TMH_CV002_003_Dia,
        Diferencia_TMH_Dia, Diferencia_Porcentaje_Dia,
        Fuente_SRR, Flag_SRR_TMS_A, Flag_SRR_TMS_B, Flag_SRR_TMS_Dia,
        Flag_Totalizadores_Dia, Flag_Comparacion_Dia,
        Fecha_Calculo
    )
    SELECT
        v.Fecha, v.SRR_TMH_Turno_A, v.SRR_TMH_Turno_B, v.SRR_TMH_Dia,
        v.SRR_TMS_TM1_Turno_A, v.SRR_TMS_TM2_Turno_A,
        v.SRR_TMS_TM1_Turno_B, v.SRR_TMS_TM2_Turno_B,
        v.SRR_TMS_Turno_A, v.SRR_TMS_Turno_B, v.SRR_TMS_Dia,
        v.Humedad_TM1_Usada, v.Humedad_TM2_Usada,
        v.Fecha_Humedad_TM1, v.Fuente_Humedad_TM1,
        v.Fecha_Humedad_TM2, v.Fuente_Humedad_TM2,
        v.TMH_CV001_Dia, v.TMH_CV002_Dia, v.TMH_CV003_Dia, v.TMH_CV002_003_Dia,
        v.Diferencia_TMH_Dia, v.Diferencia_Porcentaje_Dia,
        v.Fuente_SRR, v.Flag_SRR_TMS_A, v.Flag_SRR_TMS_B, v.Flag_SRR_TMS_Dia,
        v.Flag_Totalizadores_Dia, v.Flag_Comparacion_Dia,
        SYSDATETIME()
    FROM [inventar_SpcHidr].[v_srr_tms_diario_test] v
    WHERE v.Fecha BETWEEN @FechaInicio AND @FechaFin
      AND NOT EXISTS
      (
          SELECT 1
          FROM [inventar_SpcHidr].[Historico_SRR_Diario] h
          WHERE h.Fecha = v.Fecha
      );

    PRINT '-- Historico_SRR_Diario refrescado: '
        + CONVERT(varchar, @FechaInicio) + ' a ' + CONVERT(varchar, @FechaFin)
        + ' (ventana de reproceso desde ' + CONVERT(varchar, @FechaLimiteReproceso) + ')';
END;