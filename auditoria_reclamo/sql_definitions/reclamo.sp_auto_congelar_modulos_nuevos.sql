/* ============================================================================
   SP 3.c reclamo.sp_auto_congelar_modulos_nuevos

   El usuario no opera la base de datos para congelar modulos: este
   procedimiento reacciona solo a lo que ya llego de topografia o camiones.

   Congela dos tipos de modulo, dentro de la MISMA campana de cada uno:

     - Con movimiento real: aparecio con volumen en control_reclamo_diario o
       en control_reclamo_sulfuro_camiones_thm_diario y todavia no esta en
       modulo_congelado. Es el caso pedido: "cada nuevo modulo que se
       reporte en topografica debe congelar y abrir un modulo".
     - Precongelado ("los siguientes"): hasta @Siguientes modulos por
       delante del maximo alcanzado en la misma campana, siempre que
       disponible_rotopalas ya tenga su base. Asi, cuando le toque el turno,
       sp_auto_cerrar_y_avanzar_secuencia no se encuentra con un modulo sin
       congelar.

   Un modulo sin base valida en disponible_rotopalas NO se congela solo:
   queda como ALERTA_SIN_BASE en reclamo.log_automatizacion, porque
   inventar datos ahi violaria la regla R1.

   Abre automaticamente los que tienen movimiento real, respetando el
   maximo de dos modulos ABIERTO por rotopala (regla R5). Si para una
   rotopala/campana no hay TODAVIA ningun modulo abierto (arranque, o
   catch-up de un bloque historico completo), abre primero los de
   movimiento MAS RECIENTE: son los que la rotopala esta trabajando ahora,
   no los mas antiguos del bloque que recien se esta poniendo al dia.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_auto_congelar_modulos_nuevos]
(
    @VentanaDias int = 90,
    @Siguientes  int = 5,
    @EjecucionId int = NULL
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @Ventana date = DATEADD(DAY, -@VentanaDias, CAST(SYSDATETIME() AS date));
    DECLARE @EjecucionPropia bit = 0;

    IF @EjecucionId IS NULL
    BEGIN
        INSERT INTO [reclamo].[log_ejecucion] (procedimiento, estado)
        VALUES ('reclamo.sp_auto_congelar_modulos_nuevos', 'EN_CURSO');
        SET @EjecucionId = SCOPE_IDENTITY();
        SET @EjecucionPropia = 1;
    END;

    BEGIN TRY
        IF OBJECT_ID('tempdb..#Alcance') IS NOT NULL DROP TABLE #Alcance;

        ;WITH actividad AS
        (
            SELECT pad_id, [campaña_id], modulo_id, fecha
            FROM
            (
                SELECT cr.pad_id, cr.[campaña_id], cr.modulo_id, CAST(cr.fecha AS date) AS fecha
                FROM [inventar_SpcHidr].[control_reclamo_diario] cr
                WHERE CAST(cr.fecha AS date) >= @Ventana
                  AND COALESCE(cr.volumen_diario_m3,0) > 0
                  AND cr.[campaña_id] IS NOT NULL AND cr.modulo_id IS NOT NULL

                UNION ALL

                SELECT crc.pad_id, crc.[campaña_id], crc.modulo_id, CAST(crc.fecha AS date)
                FROM [inventar_SpcHidr].[control_reclamo_sulfuro_camiones_thm_diario] crc
                WHERE CAST(crc.fecha AS date) >= @Ventana
                  AND COALESCE(crc.volumen_diario_m3,0) > 0
            ) x
        ),
        activos AS
        (
            SELECT pad_id, [campaña_id], modulo_id, MAX(fecha) AS ultima_actividad
            FROM actividad
            GROUP BY pad_id, [campaña_id], modulo_id
        ),
        ultimo AS
        (
            SELECT a.pad_id, a.[campaña_id], MAX(md.numero) AS modulo_max
            FROM activos a
            INNER JOIN [inventar_SpcHidr].[modulo] md ON md.id_modulo = a.modulo_id
            GROUP BY a.pad_id, a.[campaña_id]
        ),
        siguientes AS
        (
            /* Precongelado: MISMA campana, dentro del rango fisico del PAD,
               con base ya disponible. No se cruza a otra campana: las
               posiciones se reutilizan y el numero por si solo no identifica
               el modulo fisico si cambia la campana. */
            SELECT dr.pad_id, dr.[campaña_id], dr.modulo_id,
                   CAST(NULL AS date) AS ultima_actividad
            FROM ultimo u
            INNER JOIN [reclamo].[topologia_pad] tp ON tp.pad_id = u.pad_id
            INNER JOIN [inventar_SpcHidr].[disponible_rotopalas] dr
                ON dr.[campaña_id] = u.[campaña_id]
            INNER JOIN [inventar_SpcHidr].[modulo] md2
                ON  md2.id_modulo = dr.modulo_id
                AND md2.numero > u.modulo_max
                AND md2.numero <= u.modulo_max + @Siguientes
                AND md2.numero <= tp.modulo_numero_max
        ),
        alcance AS
        (
            SELECT pad_id, [campaña_id], modulo_id, CAST(1 AS bit) AS con_actividad,
                   ultima_actividad
            FROM activos
            UNION
            SELECT pad_id, [campaña_id], modulo_id, CAST(0 AS bit), ultima_actividad
            FROM siguientes
        )
        SELECT
            al.pad_id, al.[campaña_id], al.modulo_id, al.con_actividad,
            al.ultima_actividad,
            md.numero AS modulo_numero,
            CAST(NULL AS nvarchar(20)) AS resultado
        INTO #Alcance
        FROM alcance al
        INNER JOIN [inventar_SpcHidr].[modulo] md ON md.id_modulo = al.modulo_id
        WHERE NOT EXISTS
        (
            SELECT 1 FROM [reclamo].[modulo_congelado] mc
            WHERE mc.[campaña_id] = al.[campaña_id] AND mc.modulo_id = al.modulo_id
        );

        /* -------------------------------------------------------------
           Congelar, uno por uno. Un fallo no detiene al resto: queda
           como alerta y sigue con el siguiente modulo.
        ------------------------------------------------------------- */
        DECLARE @Camp int, @Mod int, @Pad int, @ModNum int, @ConAct bit;
        DECLARE @Tms decimal(30,12), @M3 decimal(30,12);

        WHILE EXISTS (SELECT 1 FROM #Alcance WHERE resultado IS NULL)
        BEGIN
            SELECT TOP (1) @Pad = pad_id, @Camp = [campaña_id], @Mod = modulo_id,
                   @ModNum = modulo_numero, @ConAct = con_actividad
            FROM #Alcance WHERE resultado IS NULL
            ORDER BY pad_id, modulo_numero;

            SELECT @Tms = dr.tms, @M3 = dr.m3_totales
            FROM [inventar_SpcHidr].[disponible_rotopalas] dr
            WHERE dr.[campaña_id] = @Camp AND dr.modulo_id = @Mod;

            IF COALESCE(@Tms,0) <= 0 OR COALESCE(@M3,0) <= 0
            BEGIN
                INSERT INTO [reclamo].[log_automatizacion]
                    (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
                VALUES
                    (@EjecucionId, 'ALERTA_SIN_BASE', @Pad, @Camp, @Mod, @ModNum,
                     N'disponible_rotopalas no tiene tms/m3_totales validos. No se congelo automaticamente.');

                UPDATE #Alcance SET resultado = 'SIN_BASE'
                WHERE pad_id = @Pad AND [campaña_id] = @Camp AND modulo_id = @Mod;
            END
            ELSE
            BEGIN
                BEGIN TRY
                    EXEC [reclamo].[sp_congelar_modulo]
                         @CampañaId = @Camp, @ModuloId = @Mod, @PadId = @Pad;

                    INSERT INTO [reclamo].[log_automatizacion]
                        (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
                    VALUES
                        (@EjecucionId, 'CONGELADO_AUTOMATICO', @Pad, @Camp, @Mod, @ModNum,
                         CASE WHEN @ConAct = 1
                              THEN N'Movimiento real detectado en topografia o camiones.'
                              ELSE N'Precongelado como siguiente en la secuencia, aun sin movimiento.'
                         END);

                    EXEC [reclamo].[sp_definir_secuencia] @CampañaId = @Camp, @PadId = @Pad;

                    UPDATE #Alcance SET resultado = 'CONGELADO'
                    WHERE pad_id = @Pad AND [campaña_id] = @Camp AND modulo_id = @Mod;
                END TRY
                BEGIN CATCH
                    INSERT INTO [reclamo].[log_automatizacion]
                        (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
                    VALUES
                        (@EjecucionId, 'ALERTA_SIN_BASE', @Pad, @Camp, @Mod, @ModNum,
                         N'Error al congelar: ' + ERROR_MESSAGE());

                    UPDATE #Alcance SET resultado = 'ERROR'
                    WHERE pad_id = @Pad AND [campaña_id] = @Camp AND modulo_id = @Mod;
                END CATCH
            END;
        END;

        /* -------------------------------------------------------------
           Linea base automatica para lo que se acaba de congelar.

           sp_establecer_linea_base estaba pensado como paso manual, unico,
           corrido una vez despues del congelamiento inicial. Como este
           procedimiento congela modulos nuevos en cualquier momento (cada
           vez que aparece topografia o camiones de un modulo que no
           existia), sin este paso esos modulos quedaban con
           m3_rotopala_previo = 0 para siempre -- confirmado en los modulos
           33, 34, 35, 36 y 38 de PAD1/campaña 4, que arrastraban su
           acumulado previo al corte como si fuera tonelaje del primer dia.

           Se llama con @SoloSiVacio = 1: nunca toca un modulo que ya tiene
           linea base, solo rellena los que quedaron en NULL. Por eso es
           seguro llamarlo una vez por cada campaña que tuvo congelamientos
           en esta corrida, aunque esa campaña ya tenga otros modulos con
           linea base buena de antes.
        ------------------------------------------------------------- */
        IF EXISTS (SELECT 1 FROM #Alcance WHERE resultado = 'CONGELADO')
        BEGIN
            IF OBJECT_ID('tempdb..#CandidatosLineaBase') IS NOT NULL
                DROP TABLE #CandidatosLineaBase;

            SELECT mc.[campaña_id], mc.pad_id, mc.modulo_id, mc.modulo_numero
            INTO #CandidatosLineaBase
            FROM [reclamo].[modulo_congelado] mc
            WHERE mc.estado = 'CONGELADO'
              AND mc.fecha_linea_base IS NULL
              AND EXISTS (SELECT 1 FROM #Alcance al
                          WHERE al.[campaña_id] = mc.[campaña_id]
                            AND al.resultado    = 'CONGELADO');

            DECLARE @CampLb int;
            DECLARE campañas_lb CURSOR LOCAL FAST_FORWARD FOR
                SELECT DISTINCT [campaña_id] FROM #Alcance WHERE resultado = 'CONGELADO';

            OPEN campañas_lb;
            FETCH NEXT FROM campañas_lb INTO @CampLb;
            WHILE @@FETCH_STATUS = 0
            BEGIN
                BEGIN TRY
                    EXEC [reclamo].[sp_establecer_linea_base]
                         @CampañaId = @CampLb, @Confirmar = 1, @SoloSiVacio = 1,
                         @Silencioso = 1;
                END TRY
                BEGIN CATCH
                    INSERT INTO [reclamo].[log_automatizacion]
                        (ejecucion_id, accion, [campaña_id], detalle)
                    VALUES
                        (@EjecucionId, 'ALERTA_SIN_BASE', @CampLb,
                         N'Error al establecer linea base automatica: ' + ERROR_MESSAGE());
                END CATCH;

                FETCH NEXT FROM campañas_lb INTO @CampLb;
            END;
            CLOSE campañas_lb;
            DEALLOCATE campañas_lb;

            INSERT INTO [reclamo].[log_automatizacion]
                (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
            SELECT
                @EjecucionId, 'LINEA_BASE_AUTOMATICA', c.pad_id, c.[campaña_id],
                c.modulo_id, c.modulo_numero,
                N'Linea base establecida automaticamente tras el congelamiento.'
            FROM #CandidatosLineaBase c
            INNER JOIN [reclamo].[modulo_congelado] mc
                ON mc.[campaña_id] = c.[campaña_id] AND mc.modulo_id = c.modulo_id
            WHERE mc.fecha_linea_base IS NOT NULL;

            DROP TABLE #CandidatosLineaBase;
        END;

        /* -------------------------------------------------------------
           Abrir los que tienen movimiento real, con cupo (maximo dos
           ABIERTO por rotopala y campana, regla R5). Por cada rotopala y
           campana afectada: si no hay ningun modulo abierto todavia, se
           prioriza por ultima_actividad descendente (el mas reciente
           primero); si ya hay al menos uno abierto, se respeta el orden
           de secuencia (el que sigue).
        ------------------------------------------------------------- */
        DECLARE @RotId tinyint, @CampAbrir int;
        DECLARE @SecuenciaId int, @ModAbrir int, @PadAbrir int, @ModNumAbrir int;
        DECLARE @AbiertosActuales int, @ModoBootstrap bit;

        DECLARE grupos CURSOR LOCAL FAST_FORWARD FOR
            SELECT DISTINCT s.rotopala_id, s.[campaña_id]
            FROM [reclamo].[secuencia_rotopala] s
            INNER JOIN #Alcance al
                ON al.[campaña_id] = s.[campaña_id] AND al.modulo_id = s.modulo_id
            WHERE al.con_actividad = 1 AND al.resultado = 'CONGELADO' AND s.estado = 'PENDIENTE';

        OPEN grupos;
        FETCH NEXT FROM grupos INTO @RotId, @CampAbrir;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @AbiertosActuales =
            (
                SELECT COUNT(*) FROM [reclamo].[secuencia_rotopala]
                WHERE rotopala_id = @RotId AND [campaña_id] = @CampAbrir AND estado = 'ABIERTO'
            );
            SET @ModoBootstrap = CASE WHEN @AbiertosActuales = 0 THEN 1 ELSE 0 END;

            WHILE @AbiertosActuales < 2 AND EXISTS
            (
                SELECT 1
                FROM [reclamo].[secuencia_rotopala] s
                INNER JOIN #Alcance al
                    ON al.[campaña_id] = s.[campaña_id] AND al.modulo_id = s.modulo_id
                WHERE s.rotopala_id = @RotId AND s.[campaña_id] = @CampAbrir
                  AND s.estado = 'PENDIENTE' AND al.con_actividad = 1 AND al.resultado = 'CONGELADO'
            )
            BEGIN
                IF @ModoBootstrap = 1
                    SELECT TOP (1)
                        @SecuenciaId = s.secuencia_id, @ModAbrir = s.modulo_id,
                        @PadAbrir = s.pad_id, @ModNumAbrir = s.modulo_numero
                    FROM [reclamo].[secuencia_rotopala] s
                    INNER JOIN #Alcance al
                        ON al.[campaña_id] = s.[campaña_id] AND al.modulo_id = s.modulo_id
                    WHERE s.rotopala_id = @RotId AND s.[campaña_id] = @CampAbrir
                      AND s.estado = 'PENDIENTE' AND al.con_actividad = 1 AND al.resultado = 'CONGELADO'
                    ORDER BY al.ultima_actividad DESC, s.orden_secuencia DESC;
                ELSE
                    SELECT TOP (1)
                        @SecuenciaId = s.secuencia_id, @ModAbrir = s.modulo_id,
                        @PadAbrir = s.pad_id, @ModNumAbrir = s.modulo_numero
                    FROM [reclamo].[secuencia_rotopala] s
                    INNER JOIN #Alcance al
                        ON al.[campaña_id] = s.[campaña_id] AND al.modulo_id = s.modulo_id
                    WHERE s.rotopala_id = @RotId AND s.[campaña_id] = @CampAbrir
                      AND s.estado = 'PENDIENTE' AND al.con_actividad = 1 AND al.resultado = 'CONGELADO'
                    ORDER BY s.orden_secuencia ASC;

                UPDATE [reclamo].[secuencia_rotopala]
                SET estado = 'ABIERTO', fecha_apertura = CAST(SYSDATETIME() AS date)
                WHERE secuencia_id = @SecuenciaId;

                INSERT INTO [reclamo].[log_automatizacion]
                    (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
                VALUES
                    (@EjecucionId, 'ABIERTO_AUTOMATICO', @PadAbrir, @CampAbrir, @ModAbrir, @ModNumAbrir,
                     CASE WHEN @ModoBootstrap = 1
                          THEN N'Sin modulos abiertos previos para esta rotopala: se abre el de movimiento mas reciente.'
                          ELSE N'Movimiento real detectado y cupo disponible en la rotopala.'
                     END);

                SET @AbiertosActuales = @AbiertosActuales + 1;
            END;

            FETCH NEXT FROM grupos INTO @RotId, @CampAbrir;
        END;
        CLOSE grupos;
        DEALLOCATE grupos;

        DROP TABLE IF EXISTS #Alcance;

        IF @EjecucionPropia = 1
            UPDATE [reclamo].[log_ejecucion] SET fecha_fin = SYSDATETIME(), estado = 'OK'
            WHERE ejecucion_id = @EjecucionId;
    END TRY
    BEGIN CATCH
        IF @EjecucionPropia = 1
            UPDATE [reclamo].[log_ejecucion]
            SET fecha_fin = SYSDATETIME(), estado = 'ERROR', mensaje = ERROR_MESSAGE()
            WHERE ejecucion_id = @EjecucionId;
        THROW;
    END CATCH
END;