
CREATE   PROCEDURE
    [inventar_SpcHidr].[sp_generador_reporte_diario_emision_test]
(
    @fecha_inicio date,
    @fecha_fin    date
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    /* ============================================================
       GENERADOR REPORTE DIARIO — LÍNEA DE EMISIÓN

       La fecha final es exclusiva.

       La lógica Turno → Día se encuentra centralizada en:
       inventar_SpcHidr.fn_generador_reporte_diario_emision_test

       Este procedimiento actúa únicamente como interfaz de consulta.

       No modifica:
       - sp_generador_reporte_diario
       - fn_generador_reporte_diario
       - reporte_turno_cache
       ============================================================ */

    IF @fecha_inicio IS NULL
       OR @fecha_fin IS NULL
    BEGIN
        THROW 50001,
              'Las fechas de inicio y fin son obligatorias.',
              1;
    END;

    IF @fecha_inicio >= @fecha_fin
    BEGIN
        THROW 50002,
              'La fecha de inicio debe ser menor que la fecha de fin.',
              1;
    END;

    SELECT *
    FROM
        [inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]
        (
            @fecha_inicio,
            @fecha_fin
        )
    ORDER BY Fecha;
END;
