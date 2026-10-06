/* -----------------------------------------------------------
   SECCION B: sp_refrescar_historico_apilado_test sin el PASO 0
   (resumen/purga ahora son pasos independientes 1 y 2)
----------------------------------------------------------- */
CREATE   PROCEDURE [inventar_SpcHidr].[sp_refrescar_historico_apilado_test]
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
    DECLARE @FechaInicioBorrado date =
        CASE WHEN @FechaLimiteReproceso < @FechaInicio THEN @FechaLimiteReproceso ELSE @FechaInicio END;

    DELETE FROM [inventar_SpcHidr].[Historico_Apilado_Diario]
    WHERE Fecha BETWEEN @FechaInicioBorrado AND @FechaFin;

    INSERT INTO [inventar_SpcHidr].[Historico_Apilado_Diario]
    (
        Fecha, Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia,
        Sal_turno_A, Sal_Turno_B, Sal_promedio_dia,
        Apilado_TMH_turno_A, Apilado_TMH_turno_B, Apilado_TMH_promedio_dia,
        Apilado_TMS_Real, Apilado_TMS_turno_A_Recalculado, Apilado_TMS_turno_B_Recalculado,
        Factor_Ajuste_Camiones,
        TMH_Bruto_A, TMH_Bruto_B, TMH_Bruto_Dia,
        Sal_Pesometros_TA, Sal_Pesometros_TB, Sal_Pesometros_Dia, Sal_Topografia_Dia,
        Sal_Ajustada_Dia,
        Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido,
        Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS,
        Check_Sal_Dia, Check_TMH_Dia, Check_TMS_Dia,
        Check_TMS_A_Fuente, Check_TMS_B_Fuente, Check_TMS_Dia_Fuente,
        Fecha_Calculo
    )
    SELECT
        v.Fecha, v.Humedad_Turno_A, v.Humedad_Turno_B, v.Humedad_promedio_dia,
        v.Sal_turno_A, v.Sal_Turno_B, v.Sal_promedio_dia,
        v.Apilado_TMH_turno_A, v.Apilado_TMH_turno_B, v.Apilado_TMH_promedio_dia,
        v.Apilado_TMS_Real, v.Apilado_TMS_turno_A_Recalculado, v.Apilado_TMS_turno_B_Recalculado,
        v.Factor_Ajuste_Camiones,
        v.TMH_Bruto_A, v.TMH_Bruto_B, v.TMH_Bruto_Dia,
        v.Sal_Pesometros_TA, v.Sal_Pesometros_TB, v.Sal_Pesometros_Dia, v.Sal_Topografia_Dia,
        v.Sal_Ajustada_Dia,
        v.Flag_Sal_Basica_Valida, v.Flag_Sal_Ajuste_Valido,
        v.Flag_Apilado_Valido, v.Flag_TMS_Valido, v.Observacion_TMS,
        v.Check_Sal_Dia, v.Check_TMH_Dia, v.Check_TMS_Dia,
        v.Check_TMS_A_Fuente, v.Check_TMS_B_Fuente, v.Check_TMS_Dia_Fuente,
        SYSDATETIME()
    FROM [inventar_SpcHidr].[v_reporte_diario_apilado_test] v
    WHERE v.Fecha BETWEEN @FechaInicioBorrado AND @FechaFin
      AND NOT EXISTS
      (
          SELECT 1
          FROM [inventar_SpcHidr].[Historico_Apilado_Diario] h
          WHERE h.Fecha = v.Fecha
      );

    PRINT '-- Historico_Apilado_Diario refrescado: '
        + CONVERT(varchar, @FechaInicioBorrado) + ' a ' + CONVERT(varchar, @FechaFin)
        + ' (ventana de reproceso desde ' + CONVERT(varchar, @FechaLimiteReproceso) + ')';
END;