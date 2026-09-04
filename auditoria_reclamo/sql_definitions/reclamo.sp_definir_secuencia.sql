/* ============================================================================
   SP 2. reclamo.sp_definir_secuencia

   Regla R5 y R6. Asigna a cada modulo congelado de un PAD su posicion en la
   secuencia de la rotopala correspondiente, ordenando por numero de modulo
   creciente.

   No borra secuencias existentes: solo agrega los modulos que faltan, para no
   alterar el orden ya en uso.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_definir_secuencia]
(
    @CampañaId int,
    @PadId     int
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @RotopalaId tinyint =
    (
        SELECT TOP (1) r.rotopala_id
        FROM [reclamo].[rotopala] r
        WHERE r.pad_id = @PadId AND r.activa = 1
    );

    IF @RotopalaId IS NULL
        THROW 60101, 'No hay rotopala activa asociada a ese PAD. Revise reclamo.rotopala.', 1;

    DECLARE @OrdenBase int =
    (
        SELECT COALESCE(MAX(s.orden_secuencia), 0)
        FROM [reclamo].[secuencia_rotopala] s
        WHERE s.rotopala_id = @RotopalaId AND s.[campaña_id] = @CampañaId
    );

    INSERT INTO [reclamo].[secuencia_rotopala]
    (
        rotopala_id, [campaña_id], pad_id, modulo_id, modulo_numero,
        orden_secuencia, estado
    )
    SELECT
        @RotopalaId,
        mc.[campaña_id],
        mc.pad_id,
        mc.modulo_id,
        mc.modulo_numero,
        @OrdenBase + ROW_NUMBER() OVER (ORDER BY mc.modulo_numero, mc.modulo_id),
        'PENDIENTE'
    FROM [reclamo].[modulo_congelado] mc
    WHERE mc.[campaña_id] = @CampañaId
      AND mc.pad_id       = @PadId
      AND mc.estado       = 'CONGELADO'
      AND NOT EXISTS
      (
          SELECT 1
          FROM [reclamo].[secuencia_rotopala] s
          WHERE s.[campaña_id] = mc.[campaña_id]
            AND s.modulo_id    = mc.modulo_id
      );

    PRINT 'Modulos agregados a la secuencia: ' + CAST(@@ROWCOUNT AS varchar);

    SELECT
        s.orden_secuencia,
        s.modulo_id,
        s.modulo_numero,
        s.estado,
        s.fecha_apertura,
        s.fecha_cierre
    FROM [reclamo].[secuencia_rotopala] s
    WHERE s.rotopala_id = @RotopalaId AND s.[campaña_id] = @CampañaId
    ORDER BY s.orden_secuencia;
END;