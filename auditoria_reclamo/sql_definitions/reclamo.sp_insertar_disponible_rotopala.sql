CREATE   PROCEDURE [reclamo].[sp_insertar_disponible_rotopala]
(
    @PadId           bigint,
    @ModuloId        bigint,
    @CampañaId       bigint,
    @Campaña         int            = NULL,
    @Tms             decimal(30,12) = NULL,
    @M3Totales       decimal(30,12) = NULL,
    @Densidad        decimal(30,12) = NULL,
    @M3Apilado       decimal(30,12) = NULL,
    @TmhApilado      decimal(30,12) = NULL,
    @RemanenteM3     decimal(30,12) = NULL,
    @RemanenteTms    decimal(30,12) = NULL,
    @Observacion     nvarchar(500) = NULL
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @ModuloNumero int =
        (SELECT numero FROM [inventar_SpcHidr].[modulo] WHERE id_modulo = @ModuloId);

    IF @ModuloNumero IS NULL
        THROW 61011, 'modulo_id no existe en inventar_SpcHidr.modulo.', 1;

    IF EXISTS
    (
        SELECT 1 FROM [inventar_SpcHidr].[disponible_rotopalas]
        WHERE pad_id = @PadId AND modulo_id = @ModuloId AND [campaña_id] = @CampañaId
    )
        THROW 61012,
              'Ya existe un registro para ese pad_id, modulo_id y campaña_id. Use sp_actualizar_disponible_rotopala.', 1;

    IF @Campaña IS NULL
        SELECT TOP (1) @Campaña = dr.[campaña]
        FROM [inventar_SpcHidr].[disponible_rotopalas] dr
        WHERE dr.[campaña_id] = @CampañaId;

    IF @Campaña IS NULL
        THROW 61013,
              'No se pudo determinar el numero de campaña visible (@Campaña). Informelo explicitamente.', 1;

    IF @Densidad IS NOT NULL AND @Densidad <= 0
        THROW 61014, 'La densidad debe ser mayor a 0.', 1;

    IF @Tms IS NOT NULL AND @Tms < 0
        THROW 61015, 'El TMS no puede ser negativo.', 1;

    IF @M3Totales IS NOT NULL AND @M3Totales < 0
        THROW 61016, 'El m3_totales no puede ser negativo.', 1;

    /* Densidad automatica, igual criterio que en la actualizacion. */
    IF @Densidad IS NULL AND @Tms IS NOT NULL AND COALESCE(@M3Totales, 0) > 0
        SET @Densidad = @Tms / @M3Totales;

    BEGIN TRANSACTION;

    INSERT INTO [inventar_SpcHidr].[disponible_rotopalas]
    (
        pad_id, modulo, modulo_id, [campaña], [campaña_id],
        tms, m3_totales, densidad, m3_apilado, tmh_apilado,
        remanente_m3, remanente_tms
    )
    VALUES
    (
        @PadId, @ModuloNumero, @ModuloId, @Campaña, @CampañaId,
        @Tms, @M3Totales, @Densidad, @M3Apilado, @TmhApilado,
        @RemanenteM3, @RemanenteTms
    );

    /* Caso borde: si por alguna razon ya existia una linea base congelada
       para este modulo/campaña (por ejemplo, se recreo una fila borrada),
       se propaga y se deja registro igual que en la actualizacion. */
    IF EXISTS
    (
        SELECT 1 FROM [reclamo].[modulo_congelado]
        WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId AND estado = 'CONGELADO'
    )
    BEGIN
        DECLARE @TmsCongPrevio2 decimal(30,12), @M3CongPrevio2 decimal(30,12), @DensCongPrevia2 decimal(30,12);

        SELECT @TmsCongPrevio2 = tms_conformado, @M3CongPrevio2 = m3_totales, @DensCongPrevia2 = densidad_oficial
        FROM [reclamo].[modulo_congelado]
        WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId AND estado = 'CONGELADO';

        UPDATE [reclamo].[modulo_congelado]
        SET tms_conformado   = COALESCE(@Tms, tms_conformado),
            m3_totales       = COALESCE(@M3Totales, m3_totales),
            densidad_oficial = COALESCE(@Densidad, densidad_oficial)
        WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId AND estado = 'CONGELADO';

        INSERT INTO [reclamo].[log_sincronizacion]
            (tabla_destino, tabla_origen, accion, fecha_dato,
             [campaña_id], modulo_id, campo, valor_anterior, valor_nuevo, observacion)
        SELECT
            'modulo_congelado', 'disponible_rotopalas (dashboard)', 'ACTUALIZADO',
            CAST(SYSDATETIME() AS date),
            @CampañaId, @ModuloId, cambios.campo, cambios.valor_anterior, cambios.valor_nuevo,
            COALESCE(@Observacion, N'Insertado en disponible_rotopalas; el modulo ya estaba congelado.')
        FROM
        (
            VALUES
                ('tms_conformado',   @TmsCongPrevio2,  COALESCE(@Tms, @TmsCongPrevio2)),
                ('m3_totales',       @M3CongPrevio2,   COALESCE(@M3Totales, @M3CongPrevio2)),
                ('densidad_oficial', @DensCongPrevia2, COALESCE(@Densidad, @DensCongPrevia2))
        ) AS cambios(campo, valor_anterior, valor_nuevo)
        WHERE NOT
        (
            (cambios.valor_anterior IS NULL AND cambios.valor_nuevo IS NULL)
            OR (cambios.valor_anterior IS NOT NULL AND cambios.valor_nuevo IS NOT NULL
                AND cambios.valor_anterior = cambios.valor_nuevo)
        );
    END;

    COMMIT TRANSACTION;

    SELECT dr.*,
           CASE WHEN EXISTS
           (
               SELECT 1 FROM [reclamo].[modulo_congelado] mc
               WHERE mc.[campaña_id] = @CampañaId AND mc.modulo_id = @ModuloId AND mc.estado = 'CONGELADO'
           ) THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS propagado_a_modulo_congelado
    FROM [inventar_SpcHidr].[disponible_rotopalas] dr
    WHERE dr.pad_id = @PadId AND dr.modulo_id = @ModuloId AND dr.[campaña_id] = @CampañaId;
END;