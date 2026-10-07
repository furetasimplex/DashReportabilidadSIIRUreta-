-- Current Python semaforo control 2
SELECT 2, 'Modulos congelados sin secuencia', 'BLOQUEANTE',
                   (SELECT COUNT(*) FROM reclamo.modulo_congelado mc
                    WHERE mc.estado = 'CONGELADO'
                      AND NOT EXISTS (SELECT 1 FROM reclamo.secuencia_rotopala s
                                      WHERE s.[campaña_id] = mc.[campaña_id]
                                        AND s.modulo_id = mc.modulo_id))

GO

-- Live maintenance SP
/* ============================================================================
   SP 3.e reclamo.sp_auto_mantener_secuencia

   Orquestador. Es lo que llama el boton del dashboard: el usuario no corre
   EXEC en la base de datos. Primero rellena secuencias huerfanas (modulos
   CONGELADOS de antes de esta automatizacion que nunca llegaron a tener
   fila en secuencia_rotopala), despues cierra y avanza (libera cupo),
   despues congela lo nuevo y precongela lo que viene (y abre lo que ya
   tiene movimiento si quedo cupo). Deja todo en reclamo.log_automatizacion
   y devuelve esa bitacora, ordenada con las alertas primero.

   Backfill de secuencia (agregado 2026-07-30): reclamo.sp_definir_secuencia
   ya se llamaba automaticamente para cada modulo recien congelado (dentro
   de sp_auto_congelar_modulos_nuevos), pero eso no alcanza a los modulos
   que quedaron CONGELADOS antes de que existiera esta automatizacion --
   confirmado en los modulos 125 a 140 de rotopala 2 / campaña 8, todos
   congelados en bloque el 2026-07-29 sin pasar por el flujo automatico, y
   por lo tanto sin fila en secuencia_rotopala. Sin este backfill, cuando el
   modulo 124 se cerraba por avance de secuencia, sp_auto_cerrar_y_avanzar_
   secuencia no encontraba un modulo 125 al cual abrir (porque no existia
   como PENDIENTE) y quedaba en ALERTA_FIN_DE_CAMPANA con un mensaje
   enganoso ("no hay mas modulos congelados"), cuando en realidad si los
   habia, solo que nunca se habian secuenciado. sp_definir_secuencia es
   idempotente: solo agrega los modulos que faltan, nunca reordena ni borra
   los que ya estan.
   ============================================================================ */
CREATE PROCEDURE [reclamo].[sp_auto_mantener_secuencia]
(
    @VentanaDias int = 90,
    @Siguientes  int = 5
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    INSERT INTO [reclamo].[log_ejecucion] (procedimiento, estado)
    VALUES ('reclamo.sp_auto_mantener_secuencia', 'EN_CURSO');
    DECLARE @EjecucionId int = SCOPE_IDENTITY();

    BEGIN TRY
/* ============================================================

   BACKFILL DE SECUENCIA ROTOPALA



   Solo considera módulos congelados que realmente pertenecen

   a la secuencia física de la rotopala:



   A) tienen movimiento/topografía real de rotopala

      O

   B) están dentro de los @Siguientes módulos posteriores

      al frente máximo alcanzado por topografía.



   Los módulos congelados únicamente por camiones y fuera de

   esa cola física NO generan backfill de secuencia.

   ============================================================ */



IF EXISTS

(

    SELECT 1

    FROM [reclamo].[modulo_congelado] mc

    WHERE mc.estado = 'CONGELADO'



      AND NOT EXISTS

      (

          SELECT 1

          FROM [reclamo].[secuencia_rotopala] s

          WHERE s.[campaña_id] = mc.[campaña_id]

            AND s.modulo_id = mc.modulo_id

      )



      AND

      (

          ------------------------------------------------------

          -- A. Evidencia real de Rotopala

          ------------------------------------------------------

          EXISTS

          (

              SELECT 1

              FROM [inventar_SpcHidr].[control_reclamo_diario] cr

              WHERE cr.pad_id = mc.pad_id

                AND cr.[campaña_id] = mc.[campaña_id]

                AND cr.modulo_id = mc.modulo_id

                AND COALESCE(cr.volumen_diario_m3,0) > 0

          )



          OR



          ------------------------------------------------------

          -- B. Cola física posterior al frente real

          ------------------------------------------------------

          (

              mc.modulo_numero >

              (

                  SELECT MAX(md.numero)

                  FROM [inventar_SpcHidr].[control_reclamo_diario] cr

                  INNER JOIN [inventar_SpcHidr].[modulo] md

                      ON md.id_modulo = cr.modulo_id

                  WHERE cr.pad_id = mc.pad_id

                    AND cr.[campaña_id] = mc.[campaña_id]

                    AND COALESCE(cr.volumen_diario_m3,0) > 0

              )



              AND mc.modulo_numero <=

              (

                  SELECT MAX(md.numero) + @Siguientes

                  FROM [inventar_SpcHidr].[control_reclamo_diario] cr

                  INNER JOIN [inventar_SpcHidr].[modulo] md

                      ON md.id_modulo = cr.modulo_id

                  WHERE cr.pad_id = mc.pad_id

                    AND cr.[campaña_id] = mc.[campaña_id]

                    AND COALESCE(cr.volumen_diario_m3,0) > 0

              )

          )

      )

)

BEGIN

    DECLARE @CampDef int, @PadDef int;



    DECLARE campañas_def CURSOR LOCAL FAST_FORWARD FOR

        SELECT DISTINCT

            mc.[campaña_id],

            mc.pad_id

        FROM [reclamo].[modulo_congelado] mc

        WHERE mc.estado = 'CONGELADO'



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

                    AND COALESCE(cr.volumen_diario_m3,0) > 0

              )



              OR



              --------------------------------------------------

              -- B. Cola física inmediata

              --------------------------------------------------

              (

                  mc.modulo_numero >

                  (

                      SELECT MAX(md.numero)

                      FROM [inventar_SpcHidr].[control_reclamo_diario] cr

                      INNER JOIN [inventar_SpcHidr].[modulo] md

                          ON md.id_modulo = cr.modulo_id

                      WHERE cr.pad_id = mc.pad_id

                        AND cr.[campaña_id] = mc.[campaña_id]

                        AND COALESCE(cr.volumen_diario_m3,0) > 0

                  )



                  AND mc.modulo_numero <=

                  (

                      SELECT MAX(md.numero) + @Siguientes

                      FROM [inventar_SpcHidr].[control_reclamo_diario] cr

                      INNER JOIN [inventar_SpcHidr].[modulo] md

                          ON md.id_modulo = cr.modulo_id

                      WHERE cr.pad_id = mc.pad_id

                        AND cr.[campaña_id] = mc.[campaña_id]

                        AND COALESCE(cr.volumen_diario_m3,0) > 0

                  )

              )

          );



    OPEN campañas_def;



    FETCH NEXT FROM campañas_def

    INTO @CampDef, @PadDef;



    WHILE @@FETCH_STATUS = 0

    BEGIN

        BEGIN TRY



            EXEC [reclamo].[sp_definir_secuencia]

                 @CampañaId = @CampDef,

                 @PadId = @PadDef,

                 @Siguientes = @Siguientes;



            INSERT INTO [reclamo].[log_automatizacion]

            (

                ejecucion_id,

                accion,

                pad_id,

                [campaña_id],

                detalle

            )

            VALUES

            (

                @EjecucionId,

                'SECUENCIADO_AUTOMATICO',

                @PadDef,

                @CampDef,

                N'Backfill: se agregaron a secuencia_rotopala únicamente '

                + N'los módulos congelados elegibles por topografía de rotopala '

                + N'o por pertenecer a la cola física siguiente.'

            );



        END TRY

        BEGIN CATCH



            INSERT INTO [reclamo].[log_automatizacion]

            (

                ejecucion_id,

                accion,

                pad_id,

                [campaña_id],

                detalle

            )

            VALUES

            (

                @EjecucionId,

                'ALERTA_SIN_BASE',

                @PadDef,

                @CampDef,

                N'Error en backfill de secuencia: '

                + ERROR_MESSAGE()

            );



        END CATCH;



        FETCH NEXT FROM campañas_def

        INTO @CampDef, @PadDef;

    END;



    CLOSE campañas_def;

    DEALLOCATE campañas_def;

END;

        EXEC [reclamo].[sp_auto_cerrar_y_avanzar_secuencia] @EjecucionId = @EjecucionId;

        EXEC [reclamo].[sp_auto_congelar_modulos_nuevos]
             @VentanaDias = @VentanaDias, @Siguientes = @Siguientes, @EjecucionId = @EjecucionId;

        /* -------------------------------------------------------------
           Relleno de cupo huerfano (agregado 2026-07-30, corregido el
           mismo dia): si una rotopala/campaña queda con CERO modulos
           ABIERTO pero SI tiene al menos un CERRADO (caso del modulo 124:
           se cerro en una corrida anterior a que existiera el backfill de
           secuencia de mas arriba, asi que su sucesor nunca se abrio
           porque el paso "abrir el siguiente" solo se dispara como efecto
           inmediato de cerrar dentro de la MISMA corrida), abre el
           siguiente PENDIENTE por orden_secuencia.

           Version anterior (incorrecta, descartada): exigia solo que
           existiera ALGUNA medicion VIGENTE en topografia_avance, sin
           mirar la fecha. Se comprobo en la rotopala 2 / campaña 8 que
           eso abre el modulo equivocado: los modulos 103 a 123 llevaban
           meses (abril a julio) ya extraidos casi al 100 % por camiones,
           congelados en bloque el 2026-07-29 sin nunca pasar por
           secuencia, y el 123 en particular tenia 4 mediciones VIGENTE
           pero todas de 2026-07-01 a 2026-07-04 -- anteriores incluso al
           124 (que midio hasta el 07-08). Al ordenar por orden_secuencia,
           que sp_definir_secuencia asigna por modulo_numero ascendente,
           123 quedaba antes que 125 y se abria primero aunque su ultima
           actividad real fuera mas vieja que la del propio modulo que se
           acababa de cerrar.

           Fix: la evidencia ahora exige que la medicion VIGENTE sea
           POSTERIOR a la ultima medicion real de los modulos ya CERRADOS
           de esa misma rotopala/campaña (mismo principio de "solo cola"
           que v_preliminar_cv25 y AVANCE_DE_SECUENCIA). Con esto, 123
           queda descartado (su ultima medicion, 07-04, es anterior al
           07-08 del 124) y el candidato correcto pasa a ser 125 (mide
           desde el 07-09, despues del 124).
        ------------------------------------------------------------- */
        DECLARE @RotRell tinyint, @CampRell int;
        DECLARE @SecRell int, @ModRell int, @PadRell int, @ModNumRell int;
        DECLARE @UltimaMedicionCerrado date;

        DECLARE grupos_relleno CURSOR LOCAL FAST_FORWARD FOR
            SELECT DISTINCT s.rotopala_id, s.[campaña_id]
            FROM [reclamo].[secuencia_rotopala] s
            WHERE NOT EXISTS
            (
                SELECT 1 FROM [reclamo].[secuencia_rotopala] s2
                WHERE s2.rotopala_id = s.rotopala_id AND s2.[campaña_id] = s.[campaña_id]
                  AND s2.estado = 'ABIERTO'
            )
            AND EXISTS
            (
                SELECT 1 FROM [reclamo].[secuencia_rotopala] s3
                WHERE s3.rotopala_id = s.rotopala_id AND s3.[campaña_id] = s.[campaña_id]
                  AND s3.estado = 'CERRADO'
            );
        OPEN grupos_relleno;
        FETCH NEXT FROM grupos_relleno INTO @RotRell, @CampRell;
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @SecRell = NULL;

            SET @UltimaMedicionCerrado =
            (
                SELECT MAX(t.fecha_medicion)
                FROM [reclamo].[secuencia_rotopala] s4
                INNER JOIN [reclamo].[topografia_avance] t
                        ON t.modulo_id = s4.modulo_id AND t.estado = 'VIGENTE'
                WHERE s4.rotopala_id = @RotRell AND s4.[campaña_id] = @CampRell
                  AND s4.estado = 'CERRADO'
            );

            SELECT TOP (1)
                @SecRell = s.secuencia_id, @ModRell = s.modulo_id,
                @PadRell = s.pad_id, @ModNumRell = s.modulo_numero
            FROM [reclamo].[secuencia_rotopala] s
            WHERE s.rotopala_id = @RotRell AND s.[campaña_id] = @CampRell
              AND s.estado = 'PENDIENTE'
              AND EXISTS
              (
                  SELECT 1 FROM [reclamo].[topografia_avance] t
                  WHERE t.modulo_id = s.modulo_id AND t.estado = 'VIGENTE'
                    AND
                    (
                        @UltimaMedicionCerrado IS NULL
                        OR t.fecha_medicion > @UltimaMedicionCerrado
                    )
              )
            ORDER BY s.orden_secuencia ASC;

            IF @SecRell IS NOT NULL
            BEGIN
                UPDATE [reclamo].[secuencia_rotopala]
                SET estado = 'ABIERTO', fecha_apertura =
                (SELECT MIN(CAST(t.fecha_medicion AS date))
                 FROM [reclamo].[topografia_avance] t
                 WHERE t.[campaña_id] = @CampRell AND t.pad_id = @PadRell
                   AND t.modulo_id = @ModRell AND t.estado = 'VIGENTE'
                   AND (@UltimaMedicionCerrado IS NULL OR t.fecha_medicion > @UltimaMedicionCerrado))
                WHERE secuencia_id = @SecRell;

                INSERT INTO [reclamo].[log_automatizacion]
                    (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
                VALUES
                    (@EjecucionId, 'ABIERTO_AUTOMATICO', @PadRell, @CampRell, @ModRell, @ModNumRell,
                     N'Rotopala sin modulo ABIERTO tras el backfill de secuencia. Se abre el '
                        + N'siguiente PENDIENTE con medicion real de topografia POSTERIOR a la '
                        + N'ultima medicion de los modulos ya cerrados (evidencia fisica de '
                        + N'actividad reciente, no se abre solo por haber cupo ni por tener '
                        + N'cualquier medicion historica).');
            END;

            FETCH NEXT FROM grupos_relleno INTO @RotRell, @CampRell;
        END;
        CLOSE grupos_relleno;
        DEALLOCATE grupos_relleno;

        DECLARE @Congelados int, @Abiertos int, @Cerrados int, @Alertas int;
        SELECT
            @Congelados = SUM(CASE WHEN accion = 'CONGELADO_AUTOMATICO' THEN 1 ELSE 0 END),
            @Abiertos   = SUM(CASE WHEN accion = 'ABIERTO_AUTOMATICO'   THEN 1 ELSE 0 END),
            @Cerrados   = SUM(CASE WHEN accion = 'CERRADO_AUTOMATICO'   THEN 1 ELSE 0 END),
            @Alertas    = SUM(CASE WHEN accion LIKE 'ALERTA%'           THEN 1 ELSE 0 END)
        FROM [reclamo].[log_automatizacion]
        WHERE ejecucion_id = @EjecucionId;

        PRINT 'Congelados automaticamente : ' + CAST(COALESCE(@Congelados,0) AS varchar);
        PRINT 'Abiertos automaticamente   : ' + CAST(COALESCE(@Abiertos,0) AS varchar);
        PRINT 'Cerrados automaticamente   : ' + CAST(COALESCE(@Cerrados,0) AS varchar);
        PRINT 'Alertas para revisar       : ' + CAST(COALESCE(@Alertas,0) AS varchar);

        UPDATE [reclamo].[log_ejecucion]
        SET fecha_fin       = SYSDATETIME(),
            filas_afectadas = COALESCE(@Congelados,0) + COALESCE(@Abiertos,0) + COALESCE(@Cerrados,0),
            estado          = 'OK'
        WHERE ejecucion_id = @EjecucionId;

        SELECT
            l.log_id, l.accion, l.pad_id, l.[campaña_id], l.modulo_id, l.modulo_numero,
            l.detalle, l.fecha_evento
        FROM [reclamo].[log_automatizacion] l
        WHERE l.ejecucion_id = @EjecucionId
        ORDER BY CASE WHEN l.accion LIKE 'ALERTA%' THEN 0 ELSE 1 END, l.log_id;
    END TRY
    BEGIN CATCH
        UPDATE [reclamo].[log_ejecucion]
        SET fecha_fin = SYSDATETIME(), estado = 'ERROR', mensaje = ERROR_MESSAGE()
        WHERE ejecucion_id = @EjecucionId;
        THROW;
    END CATCH
END;

GO

-- Live define-sequence SP
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
