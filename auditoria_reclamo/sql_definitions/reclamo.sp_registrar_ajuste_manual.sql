/* ============================================================================
   SP 4. reclamo.sp_registrar_ajuste_manual

   Regla R10. El ajuste nace en estado PROPUESTO y no afecta ninguna cifra
   hasta que se apruebe. Exige motivo y antecedente: la restriccion no es
   opcional y esta ademas en el modelo.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_registrar_ajuste_manual]
(
    @FechaOperacion   date,
    @CampañaId        int,
    @PadId            int,
    @ModuloId         int,
    @TipoAjuste       varchar(30),
    @Motivo           nvarchar(500),
    @AntecedenteTipo  varchar(40),
    @AntecedenteRef   nvarchar(500),
    @DeltaM3          decimal(30,12) = NULL,
    @DeltaTms         decimal(30,12) = NULL,
    @ModuloDestinoId  int            = NULL,
    @Observacion      nvarchar(1000) = NULL
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @Motivo IS NULL OR LTRIM(RTRIM(@Motivo)) = ''
        THROW 60301, 'Todo ajuste manual exige un motivo.', 1;

    IF @AntecedenteRef IS NULL OR LTRIM(RTRIM(@AntecedenteRef)) = ''
        THROW 60302,
              'Todo ajuste manual exige la referencia del antecedente que lo respalda.', 1;

    IF @DeltaM3 IS NULL AND @DeltaTms IS NULL
        THROW 60303, 'Debe informar al menos delta en m3 o en TMS.', 1;

    IF @TipoAjuste = 'TRASPASO_MODULO' AND @ModuloDestinoId IS NULL
        THROW 60304, 'Un traspaso exige el modulo destino.', 1;

    /* Si viene solo uno de los dos deltas, se deriva el otro con la densidad
       oficial del modulo. Deja constancia en la observacion. */
    DECLARE @Densidad decimal(30,12) =
    (
        SELECT TOP (1) mc.densidad_oficial
        FROM [reclamo].[modulo_congelado] mc
        WHERE mc.[campaña_id] = @CampañaId AND mc.modulo_id = @ModuloId
    );

    DECLARE @Derivado nvarchar(200) = NULL;

    IF @DeltaM3 IS NULL AND @DeltaTms IS NOT NULL AND COALESCE(@Densidad,0) > 0
    BEGIN
        SET @DeltaM3 = @DeltaTms / @Densidad;
        SET @Derivado = N'delta_m3 derivado de delta_tms con densidad oficial '
                      + CAST(@Densidad AS nvarchar(40));
    END;

    IF @DeltaTms IS NULL AND @DeltaM3 IS NOT NULL AND COALESCE(@Densidad,0) > 0
    BEGIN
        SET @DeltaTms = @DeltaM3 * @Densidad;
        SET @Derivado = N'delta_tms derivado de delta_m3 con densidad oficial '
                      + CAST(@Densidad AS nvarchar(40));
    END;

    INSERT INTO [reclamo].[ajuste_manual]
    (
        fecha_operacion, [campaña_id], pad_id, modulo_id, modulo_destino_id,
        tipo_ajuste, delta_m3, delta_tms,
        motivo, antecedente_tipo, antecedente_ref,
        estado, observacion
    )
    VALUES
    (
        @FechaOperacion, @CampañaId, @PadId, @ModuloId, @ModuloDestinoId,
        @TipoAjuste, @DeltaM3, @DeltaTms,
        @Motivo, @AntecedenteTipo, @AntecedenteRef,
        'PROPUESTO',
        LTRIM(RTRIM(COALESCE(@Observacion, N'') + N' ' + COALESCE(@Derivado, N'')))
    );

    DECLARE @Id int = SCOPE_IDENTITY();

    PRINT 'Ajuste registrado en estado PROPUESTO. ajuste_id = ' + CAST(@Id AS varchar);
    PRINT 'No afecta ninguna cifra hasta que se apruebe con sp_aprobar_ajuste_manual.';

    SELECT * FROM [reclamo].[ajuste_manual] WHERE ajuste_id = @Id;
END;