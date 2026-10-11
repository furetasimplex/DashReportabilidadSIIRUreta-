/* ================================================================
   v2 de reclamo.sp_actualizar_disponible_rotopala y
   reclamo.sp_insertar_disponible_rotopala, con dos cambios pedidos:

   1) DENSIDAD AUTOMATICA. Si no se informa @Densidad explicita, y
      cambia TMS o m3_totales, la densidad se recalcula sola como
      TMS/m3_totales. Si se informa @Densidad, esa manda (override
      manual). Si no cambia ni TMS ni m3_totales, la densidad
      existente se conserva tal cual.

   2) PROPAGACION A MODULO YA CONGELADO. Si el (campaña_id, modulo_id)
      editado ya tiene una fila CONGELADO en reclamo.modulo_congelado,
      el cambio de tms_conformado/m3_totales/densidad_oficial se
      aplica TAMBIEN ahi (ya no queda desincronizado de disponible_
      rotopalas), y cada campo que cambio queda registrado en
      reclamo.log_sincronizacion (tabla_destino='modulo_congelado',
      tabla_origen='disponible_rotopalas (dashboard)', con valor
      anterior y nuevo). Nada de esto pasa si el modulo no esta
      congelado -- ahi disponible_rotopalas sigue siendo la unica
      fuente y modulo_congelado ni se toca.

   Ambas procedimientos devuelven, en su SELECT final, la columna
   propagado_a_modulo_congelado (bit) para que el dashboard pueda
   avisar explicitamente cuando esto ocurrio.
================================================================ */

CREATE   PROCEDURE [reclamo].[sp_actualizar_disponible_rotopala]
(
    @IdDisponibleRotopalas int,
    @Tms             decimal(30,12) = NULL,
    @M3Totales       decimal(30,12) = NULL,
    @Densidad        decimal(30,12) = NULL,
    @M3Apilado       decimal(30,12) = NULL,
    @TmhApilado      decimal(30,12) = NULL,
    @RemanenteM3     decimal(30,12) = NULL,
    @RemanenteTms    decimal(30,12) = NULL,
    @SoloInformados  bit = 1,
    @Observacion     nvarchar(500) = NULL
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF NOT EXISTS
    (
        SELECT 1 FROM [inventar_SpcHidr].[disponible_rotopalas]
        WHERE id_disponible_rotopalas = @IdDisponibleRotopalas
    )
        THROW 61001, 'No existe ese id_disponible_rotopalas.', 1;

    IF @Densidad IS NOT NULL AND @Densidad <= 0
        THROW 61002, 'La densidad debe ser mayor a 0.', 1;

    IF @Tms IS NOT NULL AND @Tms < 0
        THROW 61003, 'El TMS no puede ser negativo.', 1;

    IF @M3Totales IS NOT NULL AND @M3Totales < 0
        THROW 61004, 'El m3_totales no puede ser negativo.', 1;

    DECLARE @PadId bigint, @ModuloId bigint, @CampañaId bigint;
    DECLARE @TmsPrevio decimal(30,12), @M3Previo decimal(30,12), @DensidadPrevia decimal(30,12);

    SELECT @PadId = pad_id, @ModuloId = modulo_id, @CampañaId = [campaña_id],
           @TmsPrevio = tms, @M3Previo = m3_totales, @DensidadPrevia = densidad
    FROM [inventar_SpcHidr].[disponible_rotopalas]
    WHERE id_disponible_rotopalas = @IdDisponibleRotopalas;

    DECLARE @TmsNuevo decimal(30,12) =
        CASE WHEN @SoloInformados = 1 THEN COALESCE(@Tms, @TmsPrevio) ELSE @Tms END;
    DECLARE @M3Nuevo decimal(30,12) =
        CASE WHEN @SoloInformados = 1 THEN COALESCE(@M3Totales, @M3Previo) ELSE @M3Totales END;

    /* Densidad automatica: manual explicita manda; si no, se recalcula
       solo cuando cambio TMS o m3_totales; si no cambio nada de eso, se
       conserva la que ya tenia (o NULL si @SoloInformados=0 y no se
       informo densidad). */
    DECLARE @DensidadNueva decimal(30,12);
    IF @Densidad IS NOT NULL
        SET @DensidadNueva = @Densidad;
    ELSE IF (@Tms IS NOT NULL OR @M3Totales IS NOT NULL) AND COALESCE(@M3Nuevo, 0) > 0
        SET @DensidadNueva = @TmsNuevo / @M3Nuevo;
    ELSE IF @SoloInformados = 1
        SET @DensidadNueva = @DensidadPrevia;
    ELSE
        SET @DensidadNueva = NULL;

    BEGIN TRANSACTION;

    UPDATE [inventar_SpcHidr].[disponible_rotopalas]
    SET tms           = @TmsNuevo,
        m3_totales    = @M3Nuevo,
        densidad      = @DensidadNueva,
        m3_apilado    = CASE WHEN @SoloInformados = 1 THEN COALESCE(@M3Apilado, m3_apilado) ELSE @M3Apilado END,
        tmh_apilado   = CASE WHEN @SoloInformados = 1 THEN COALESCE(@TmhApilado, tmh_apilado) ELSE @TmhApilado END,
        remanente_m3  = CASE WHEN @SoloInformados = 1 THEN COALESCE(@RemanenteM3, remanente_m3) ELSE @RemanenteM3 END,
        remanente_tms = CASE WHEN @SoloInformados = 1 THEN COALESCE(@RemanenteTms, remanente_tms) ELSE @RemanenteTms END
    WHERE id_disponible_rotopalas = @IdDisponibleRotopalas;

    /* Propagacion: solo si el modulo ya esta CONGELADO. */
    IF EXISTS
    (
        SELECT 1 FROM [reclamo].[modulo_congelado]
        WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId AND estado = 'CONGELADO'
    )
    BEGIN
        DECLARE @TmsCongPrevio decimal(30,12), @M3CongPrevio decimal(30,12), @DensCongPrevia decimal(30,12);

        SELECT @TmsCongPrevio = tms_conformado, @M3CongPrevio = m3_totales, @DensCongPrevia = densidad_oficial
        FROM [reclamo].[modulo_congelado]
        WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId AND estado = 'CONGELADO';

        UPDATE [reclamo].[modulo_congelado]
        SET tms_conformado   = @TmsNuevo,
            m3_totales       = @M3Nuevo,
            densidad_oficial = @DensidadNueva
        WHERE [campaña_id] = @CampañaId AND modulo_id = @ModuloId AND estado = 'CONGELADO';

        INSERT INTO [reclamo].[log_sincronizacion]
            (tabla_destino, tabla_origen, accion, fecha_dato,
             [campaña_id], modulo_id, campo, valor_anterior, valor_nuevo, observacion)
        SELECT
            'modulo_congelado', 'disponible_rotopalas (dashboard)', 'ACTUALIZADO',
            CAST(SYSDATETIME() AS date),
            @CampañaId, @ModuloId, cambios.campo, cambios.valor_anterior, cambios.valor_nuevo,
            COALESCE(@Observacion, N'Editado desde disponible_rotopalas; modulo ya estaba congelado.')
        FROM
        (
            VALUES
                ('tms_conformado',   @TmsCongPrevio,  @TmsNuevo),
                ('m3_totales',       @M3CongPrevio,   @M3Nuevo),
                ('densidad_oficial', @DensCongPrevia, @DensidadNueva)
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
    WHERE dr.id_disponible_rotopalas = @IdDisponibleRotopalas;
END;