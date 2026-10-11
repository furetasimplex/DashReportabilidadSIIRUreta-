CREATE PROCEDURE [reclamo].[sp_definir_secuencia]
(
    @CampañaId int,
    @PadId     int,
    @Siguientes int = 5
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    ------------------------------------------------------------
    -- 1. Rotopala activa correspondiente al PAD
    ------------------------------------------------------------
    DECLARE @RotopalaId tinyint =
    (
        SELECT TOP (1)
            r.rotopala_id
        FROM [reclamo].[rotopala] r
        WHERE r.pad_id = @PadId
          AND r.activa = 1
    );

    IF @RotopalaId IS NULL
        THROW 60101,
              'No hay rotopala activa asociada a ese PAD. Revise reclamo.rotopala.',
              1;


    ------------------------------------------------------------
    -- 2. Frente físico real alcanzado por ROTOPALA
    --
    -- Se determina EXCLUSIVAMENTE desde control_reclamo_diario.
    -- Los camiones NO participan en este cálculo.
    ------------------------------------------------------------
    DECLARE @ModuloMaxTopo int;

    SELECT
        @ModuloMaxTopo = MAX(md.numero)
    FROM [inventar_SpcHidr].[control_reclamo_diario] cr
    INNER JOIN [inventar_SpcHidr].[modulo] md
        ON md.id_modulo = cr.modulo_id
    WHERE cr.pad_id = @PadId
      AND cr.[campaña_id] = @CampañaId
      AND COALESCE(cr.volumen_diario_m3, 0) > 0;


    ------------------------------------------------------------
    -- 3. Último orden existente
    --
    -- Por ahora NO reordenamos automáticamente históricos.
    -- La reparación de R2/campaña 10 se hará en forma controlada.
    ------------------------------------------------------------
    DECLARE @OrdenBase int =
    (
        SELECT COALESCE(MAX(s.orden_secuencia), 0)
        FROM [reclamo].[secuencia_rotopala] s
        WHERE s.rotopala_id = @RotopalaId
          AND s.[campaña_id] = @CampañaId
    );


    ------------------------------------------------------------
    -- 4. Agregar únicamente módulos válidos para la secuencia
    --    física de la ROTOPALA.
    --
    -- Entran:
    --
    -- A) módulos con movimiento real de Rotopala/topografía
    --
    -- O
    --
    -- B) módulos que forman parte de la cola física inmediata:
    --    ModuloMaxTopo + 1 ... ModuloMaxTopo + @Siguientes
    --
    -- Un módulo que tenga solamente movimiento de camiones,
    -- fuera de esa cola física, NO entra a secuencia_rotopala.
    ------------------------------------------------------------
    ;WITH Candidatos AS
    (
        SELECT
            mc.[campaña_id],
            mc.pad_id,
            mc.modulo_id,
            mc.modulo_numero
        FROM [reclamo].[modulo_congelado] mc
        WHERE mc.[campaña_id] = @CampañaId
          AND mc.pad_id = @PadId
          AND mc.estado = 'CONGELADO'

          AND NOT EXISTS
          (
              SELECT 1
              FROM [reclamo].[secuencia_rotopala] s
              WHERE s.[campaña_id] = mc.[campaña_id]
                AND s.modulo_id = mc.modulo_id
          )

          AND
          (
              --------------------------------------------------
              -- A. Evidencia real de Rotopala
              --------------------------------------------------
              EXISTS
              (
                  SELECT 1
                  FROM [inventar_SpcHidr].[control_reclamo_diario] cr
                  WHERE cr.pad_id = mc.pad_id
                    AND cr.[campaña_id] = mc.[campaña_id]
                    AND cr.modulo_id = mc.modulo_id
                    AND COALESCE(cr.volumen_diario_m3, 0) > 0
              )

              OR

              --------------------------------------------------
              -- B. Cola física inmediata
              --------------------------------------------------
              (
                  @ModuloMaxTopo IS NOT NULL
                  AND mc.modulo_numero > @ModuloMaxTopo
                  AND mc.modulo_numero
                        <= @ModuloMaxTopo + @Siguientes
              )
          )
    )
    INSERT INTO [reclamo].[secuencia_rotopala]
    (
        rotopala_id,
        [campaña_id],
        pad_id,
        modulo_id,
        modulo_numero,
        orden_secuencia,
        estado
    )
    SELECT
        @RotopalaId,
        c.[campaña_id],
        c.pad_id,
        c.modulo_id,
        c.modulo_numero,
        @OrdenBase
        + ROW_NUMBER() OVER
          (
              ORDER BY
                  c.modulo_numero,
                  c.modulo_id
          ),
        'PENDIENTE'
    FROM Candidatos c;

    DECLARE @Agregados int = @@ROWCOUNT;


    ------------------------------------------------------------
    -- 5. Trazabilidad
    ------------------------------------------------------------
    PRINT 'Modulos agregados a la secuencia: '
        + CAST(@Agregados AS varchar);

    PRINT 'Frente maximo de Rotopala por topografia: '
        + COALESCE(
            CAST(@ModuloMaxTopo AS varchar),
            'SIN_TOPOGRAFIA'
          );


    ------------------------------------------------------------
    -- 6. Resultado
    ------------------------------------------------------------
    SELECT
        s.orden_secuencia,
        s.modulo_id,
        s.modulo_numero,
        s.estado,
        s.fecha_apertura,
        s.fecha_cierre
    FROM [reclamo].[secuencia_rotopala] s
    WHERE s.rotopala_id = @RotopalaId
      AND s.[campaña_id] = @CampañaId
    ORDER BY s.orden_secuencia;
END;
