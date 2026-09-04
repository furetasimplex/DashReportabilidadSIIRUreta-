/* ============================================================================
   SP 1. reclamo.sp_congelar_modulo

   Regla R1. Toma el tonelaje conformado desde modulos_turnos y el volumen y
   densidad desde disponible_rotopalas, y los congela.

   Un modulo ya congelado NO se puede volver a congelar sin @Forzar = 1, y esa
   accion queda registrada en la observacion.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_congelar_modulo]
(
    @CampañaId          int,
    @ModuloId           int,
    @PadId              int,
    @ParcelaId          int          = NULL,
    @FechaConformacion  date         = NULL,
    @Forzar             bit          = 0,
    @Observacion        nvarchar(1000) = NULL
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @CampañaId IS NULL OR @ModuloId IS NULL OR @PadId IS NULL
        THROW 60001, 'Debe informar campana, modulo y PAD.', 1;

    DECLARE @Existe int =
    (
        SELECT COUNT(*)
        FROM [reclamo].[modulo_congelado]
        WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId
    );

    IF @Existe > 0 AND @Forzar = 0
        THROW 60002,
              'El modulo ya esta congelado. Use @Forzar = 1 y explique el motivo en @Observacion.', 1;

    IF @Existe > 0 AND @Forzar = 1 AND @Observacion IS NULL
        THROW 60003,
              'Recongelar un modulo exige @Observacion con el motivo.', 1;

    /* ---- Base oficial: disponible_rotopalas -------------------------------
       CORRECCION 30-07-2026. El diseno original tomaba el TMS de la suma de
       modulos_turnos. El script 00 mostro que esa suma esta un orden por
       encima del valor de disponible_rotopalas, que es ademas el que usa la
       hoja "Disponible para rotopalas" del libro de ripios.
       disponible_rotopalas manda; modulos_turnos queda como contraste. */
    DECLARE @Tms      decimal(30,12);
    DECLARE @M3       decimal(30,12);
    DECLARE @Densidad decimal(30,12);

    SELECT TOP (1)
        @Tms      = CAST(dr.[tms]        AS decimal(30,12)),
        @M3       = CAST(dr.[m3_totales] AS decimal(30,12)),
        @Densidad = CAST(dr.[densidad]   AS decimal(30,12))
    FROM [inventar_SpcHidr].[disponible_rotopalas] dr
    WHERE dr.[campaña_id] = @CampañaId
      AND dr.[modulo_id]  = @ModuloId;

    IF @Tms IS NULL OR @Tms <= 0
        THROW 60004,
              'disponible_rotopalas no tiene tms para esa campana y modulo.', 1;

    IF @M3 IS NULL OR @M3 <= 0
        THROW 60005,
              'disponible_rotopalas no tiene m3_totales para esa campana y modulo.', 1;

    /* Si la densidad declarada no viene o es cero, se deriva del cociente. */
    IF COALESCE(@Densidad, 0) <= 0
        SET @Densidad = @Tms / @M3;

    /* Contraste con modulos_turnos, solo informativo. */
    DECLARE @TmsTurnos decimal(30,12) =
    (
        SELECT SUM(COALESCE(mt.[TMS], 0))
        FROM [inventar_SpcHidr].[modulos_turnos] mt
        WHERE mt.[campaña_id] = @CampañaId
          AND mt.[modulo_id]  = @ModuloId
    );

    IF @TmsTurnos IS NOT NULL AND @Tms > 0
       AND ABS(@TmsTurnos - @Tms) * 100.0 / @Tms > 10
        PRINT '        AVISO: modulos_turnos suma ' + CAST(@TmsTurnos AS varchar(40))
            + ' TMS y disponible_rotopalas informa ' + CAST(@Tms AS varchar(40))
            + '. Se congela con disponible_rotopalas.';

    /* Parcela y PAD se derivan de la jerarquia real pad > parcela > modulo,
       confirmada en el script 00 seccion 4. */
    IF @ParcelaId IS NULL
        SELECT @ParcelaId = md.id_parcela
        FROM [inventar_SpcHidr].[modulo] md
        WHERE md.id_modulo = @ModuloId;

    DECLARE @ModuloNumero int =
    (
        SELECT TOP (1) md.numero
        FROM [inventar_SpcHidr].[modulo] md
        WHERE md.id_modulo = @ModuloId
    );

    /* El numero de modulo debe caer dentro del rango fisico del PAD.
       Oxido: 32 parcelas x 2 modulos = 1 a 64.
       Sulfuro: 28 parcelas x 5 modulos = 1 a 140. */
    DECLARE @Min int, @Max int, @PadNombre varchar(40);
    SELECT @Min = tp.modulo_numero_min,
           @Max = tp.modulo_numero_max,
           @PadNombre = tp.nombre
    FROM [reclamo].[topologia_pad] tp
    WHERE tp.pad_id = @PadId;

    IF @Min IS NULL
        THROW 60006,
              'No hay topologia definida para ese PAD. Revise reclamo.topologia_pad.', 1;

    IF @ModuloNumero IS NOT NULL AND @ModuloNumero NOT BETWEEN @Min AND @Max
    BEGIN
        DECLARE @Msg nvarchar(300) =
            N'El modulo ' + CAST(@ModuloNumero AS nvarchar(10))
            + N' esta fuera del rango del ' + @PadNombre
            + N' (' + CAST(@Min AS nvarchar(10)) + N' a ' + CAST(@Max AS nvarchar(10)) + N').';
        THROW 60007, @Msg, 1;
    END;

    IF @Existe > 0
    BEGIN
        UPDATE [reclamo].[modulo_congelado]
        SET pad_id              = @PadId,
            parcela_id          = @ParcelaId,
            modulo_numero       = @ModuloNumero,
            fecha_conformacion  = COALESCE(@FechaConformacion, fecha_conformacion),
            fecha_congelamiento = CAST(SYSDATETIME() AS date),
            tms_conformado      = @Tms,
            m3_totales          = @M3,
            densidad_oficial    = @Densidad,
            fuente              = 'DISPONIBLE_ROTOPALAS',
            metodo              = 'RECONGELADO_FORZADO',
            usuario_registro    = SUSER_SNAME(),
            fecha_registro      = SYSDATETIME(),
            observacion         = @Observacion
        WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId;

        PRINT 'Modulo RECONGELADO. Campana ' + CAST(@CampañaId AS varchar)
            + ' modulo ' + CAST(@ModuloId AS varchar);
    END
    ELSE
    BEGIN
        INSERT INTO [reclamo].[modulo_congelado]
        (
            [campaña_id], pad_id, parcela_id, modulo_id, modulo_numero,
            fecha_conformacion, fecha_congelamiento,
            tms_conformado, m3_totales, densidad_oficial,
            fuente, metodo, estado, observacion
        )
        VALUES
        (
            @CampañaId, @PadId, @ParcelaId, @ModuloId, @ModuloNumero,
            COALESCE(@FechaConformacion, CAST(SYSDATETIME() AS date)),
            CAST(SYSDATETIME() AS date),
            @Tms, @M3, @Densidad,
            'DISPONIBLE_ROTOPALAS',
            'TMS_Y_VOLUMEN_DE_DISPONIBLE_ROTOPALAS',
            'CONGELADO', @Observacion
        );

        PRINT 'Modulo CONGELADO. Campana ' + CAST(@CampañaId AS varchar)
            + ' modulo ' + CAST(@ModuloId AS varchar)
            + ' TMS ' + CAST(@Tms AS varchar(40))
            + ' m3 '  + CAST(@M3 AS varchar(40));
    END;

    SELECT *
    FROM [reclamo].[modulo_congelado]
    WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId;
END;