/* ============================================================================
   SP 3.a reclamo.sp_sincronizar_desde_etl

   PUNTO DE ENTRADA DE LOS DATOS OPERACIONALES.

   La integracion se hace mediante un template y un ETL que llena
   inventar_SpcHidr.control_apilado_diario y control_reclamo_diario. Este
   procedimiento trae esos datos al esquema [reclamo]. No hay carga manual.

   QUE HACE
     1. Deduplica control_reclamo_diario conservando el id mas alto por
        fecha + pad + campana + modulo. El ETL puede reprocesar y dejar mas de
        una fila por clave; es el mismo criterio que usaba la vista vigente.
     2. Resuelve medicion_valida cruzando con
        control_medicion_topografia_diaria, solo excepciones APROBADAS.
     3. Sincroniza hacia reclamo.topografia_avance, respetando la fecha de
        corte del sistema.
     4. Sincroniza el reclamo por camiones desde
        control_reclamo_sulfuro_camiones_thm_diario.
     5. Deja en reclamo.log_sincronizacion todo lo insertado, actualizado u
        omitido, con valor anterior y nuevo cuando el ETL cambio algo.

   POR QUE IMPORTA EL LOG
   Si el ETL reprocesa un dia ya publicado y cambia un volumen, la cifra del
   reporte cambia. Sin bitacora eso ocurriria en silencio. Con ella queda la
   evidencia de que cambio, cuanto y cuando.

   QUE NO HACE
   No congela modulos ni abre la secuencia. Un modulo que no este congelado se
   OMITE y se reporta: es deliberado, porque reclamar sobre una base no fijada
   viola la regla R1.

   control_apilado_diario se lee para resolver la fecha de conformacion, no
   para calcular reclamo. Su estructura debe confirmarse antes con la seccion
   11 del script 00; mientras tanto ese bloque queda desactivado por el
   parametro @SincronizarApilado.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_sincronizar_desde_etl]
(
    @FechaInicio         date,
    @FechaFin            date,
    @SincronizarApilado  bit = 0,
    @Confirmar           bit = 1
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @EjecucionId int;
    DECLARE @Corte date = [reclamo].[fn_fecha_corte]();

    BEGIN TRY
        IF @FechaInicio IS NULL OR @FechaFin IS NULL
            THROW 60701, 'Debe informar el rango de fechas.', 1;

        IF @Corte IS NULL
            THROW 60702, 'No hay FECHA_CORTE_SISTEMA en reclamo.configuracion.', 1;

        IF @FechaInicio < @Corte
        BEGIN
            PRINT '-- El rango comienza antes del corte (' + CONVERT(varchar(10), @Corte, 120)
                + '). Se recorta.';
            SET @FechaInicio = @Corte;
        END;

        IF @FechaFin < @Corte
            THROW 60703, 'Todo el rango es anterior a la fecha de corte del sistema.', 1;

        INSERT INTO [reclamo].[log_ejecucion]
            (procedimiento, rango_desde, rango_hasta, estado)
        VALUES
            ('reclamo.sp_sincronizar_desde_etl', @FechaInicio, @FechaFin, 'EN_CURSO');
        SET @EjecucionId = SCOPE_IDENTITY();

        PRINT '-- Sincronizacion desde el ETL';
        PRINT '-- Rango: ' + CONVERT(varchar(10), @FechaInicio, 120)
            + ' a ' + CONVERT(varchar(10), @FechaFin, 120);

        /* ================================================================
           A. TOPOGRAFIA, desde control_reclamo_diario
        ================================================================ */
        IF OBJECT_ID('tempdb..#Topo') IS NOT NULL DROP TABLE #Topo;

        ;WITH dedup AS
        (
            SELECT
                CAST(cr.fecha AS date)      AS fecha_medicion,
                cr.pad_id,
                cr.[campaña_id],
                cr.modulo_id,
                cr.volumen_final_reclamado  AS m3_reclamado_acum,
                cr.avance_porcentaje,
                cr.id                       AS id_origen,
                ROW_NUMBER() OVER
                (
                    PARTITION BY CAST(cr.fecha AS date), cr.pad_id,
                                 cr.[campaña_id], cr.modulo_id
                    ORDER BY cr.id DESC
                ) AS rn
            FROM [inventar_SpcHidr].[control_reclamo_diario] cr
            WHERE CAST(cr.fecha AS date) >= @FechaInicio
              AND CAST(cr.fecha AS date) <= @FechaFin
              AND cr.[campaña_id] IS NOT NULL
              AND cr.modulo_id    IS NOT NULL
        )
        SELECT
            d.fecha_medicion,
            d.pad_id,
            d.[campaña_id],
            d.modulo_id,
            CAST(COALESCE(d.m3_reclamado_acum, 0) AS decimal(30,12)) AS m3_reclamado_acum,
            CAST(d.avance_porcentaje AS decimal(18,12))              AS avance_total_pct,
            d.id_origen,
            /* Excepcion de medicion, solo si esta APROBADA. */
            COALESCE(cm.[medicion_valida], CAST(1 AS bit))           AS medicion_valida,
            CAST(cm.[motivo] AS nvarchar(400))                       AS motivo_no_medicion,
            CASE WHEN mc.modulo_id IS NULL THEN 0 ELSE 1 END         AS modulo_congelado
        INTO #Topo
        FROM dedup d
        LEFT JOIN [inventar_SpcHidr].[control_medicion_topografia_diaria] cm
            ON  cm.[fecha_operacion] = d.fecha_medicion
            AND cm.[pad_id]          = d.pad_id
            AND cm.[estado]          = 'APROBADO'
        LEFT JOIN [reclamo].[modulo_congelado] mc
            ON  mc.[campaña_id] = d.[campaña_id]
            AND mc.modulo_id    = d.modulo_id
            AND mc.estado       = 'CONGELADO'
        WHERE d.rn = 1;

        /* Bitacora de lo que va a cambiar, ANTES de tocar nada. */
        INSERT INTO [reclamo].[log_sincronizacion]
            (ejecucion_id, tabla_destino, tabla_origen, accion,
             fecha_dato, [campaña_id], modulo_id, campo,
             valor_anterior, valor_nuevo, observacion)
        SELECT
            @EjecucionId, 'topografia_avance', 'control_reclamo_diario',
            CASE
                WHEN t.modulo_congelado = 0 THEN 'OMITIDO'
                WHEN ta.topografia_id IS NULL THEN 'INSERTADO'
                ELSE 'ACTUALIZADO'
            END,
            t.fecha_medicion, t.[campaña_id], t.modulo_id, 'm3_reclamado_acum',
            ta.m3_reclamado_acum, t.m3_reclamado_acum,
            CASE
                WHEN t.modulo_congelado = 0
                    THEN N'Modulo no congelado. No se sincroniza: violaria la regla R1.'
                WHEN ta.topografia_id IS NOT NULL
                 AND ABS(COALESCE(ta.m3_reclamado_acum,0) - t.m3_reclamado_acum) > 0.001
                    THEN N'El ETL cambio un valor ya sincronizado. Reprocesar el rango.'
                ELSE NULL
            END
        FROM #Topo t
        LEFT JOIN [reclamo].[topografia_avance] ta
            ON  ta.fecha_medicion = t.fecha_medicion
            AND ta.[campaña_id]   = t.[campaña_id]
            AND ta.modulo_id      = t.modulo_id
        WHERE t.modulo_congelado = 0
           OR ta.topografia_id IS NULL
           OR ABS(COALESCE(ta.m3_reclamado_acum,0) - t.m3_reclamado_acum) > 0.001
           OR COALESCE(ta.medicion_valida, 1) <> t.medicion_valida;

        IF @Confirmar = 1
        BEGIN
            MERGE [reclamo].[topografia_avance] AS tgt
            USING (SELECT * FROM #Topo WHERE modulo_congelado = 1) AS src
                ON  tgt.fecha_medicion = src.fecha_medicion
                AND tgt.[campaña_id]   = src.[campaña_id]
                AND tgt.modulo_id      = src.modulo_id
            WHEN MATCHED THEN UPDATE SET
                m3_reclamado_acum  = src.m3_reclamado_acum,
                avance_total_pct   = src.avance_total_pct,
                medicion_valida    = src.medicion_valida,
                motivo_no_medicion = CASE
                                        WHEN src.medicion_valida = 0
                                            THEN COALESCE(src.motivo_no_medicion,
                                                 N'Excepcion aprobada sin motivo declarado')
                                        ELSE NULL
                                     END,
                fuente             = 'ETL_CONTROL_RECLAMO_DIARIO',
                metodo             = 'SINCRONIZACION_DEDUPLICADA_ID_MAX',
                fecha_registro     = SYSDATETIME()
            WHEN NOT MATCHED BY TARGET THEN INSERT
            (
                fecha_medicion, [campaña_id], pad_id, modulo_id,
                m3_reclamado_acum, avance_total_pct,
                medicion_valida, motivo_no_medicion,
                fuente, metodo, estado
            )
            VALUES
            (
                src.fecha_medicion, src.[campaña_id], src.pad_id, src.modulo_id,
                src.m3_reclamado_acum, src.avance_total_pct,
                src.medicion_valida,
                CASE
                    WHEN src.medicion_valida = 0
                        THEN COALESCE(src.motivo_no_medicion,
                             N'Excepcion aprobada sin motivo declarado')
                    ELSE NULL
                END,
                'ETL_CONTROL_RECLAMO_DIARIO',
                'SINCRONIZACION_DEDUPLICADA_ID_MAX',
                'VIGENTE'
            );

            PRINT 'Topografia sincronizada  : ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
        END;

        /* ================================================================
           B. CAMIONES, desde control_reclamo_sulfuro_camiones_thm_diario
        ================================================================ */
        IF OBJECT_ID('tempdb..#Cam') IS NOT NULL DROP TABLE #Cam;

        SELECT
            CAST(crc.fecha AS date)                          AS fecha,
            CAST(crc.pad_id AS int)                          AS pad_id,
            CAST(crc.[campaña_id] AS int)                    AS [campaña_id],
            CAST(crc.modulo_id AS int)                       AS modulo_id,
            CAST(SUM(COALESCE(crc.volumen_diario_m3,0)) AS decimal(30,12)) AS m3_thm,
            CASE WHEN MAX(CASE WHEN mc.modulo_id IS NULL THEN 0 ELSE 1 END) = 1
                 THEN 1 ELSE 0 END                           AS modulo_congelado
        INTO #Cam
        FROM [inventar_SpcHidr].[control_reclamo_sulfuro_camiones_thm_diario] crc
        LEFT JOIN [reclamo].[modulo_congelado] mc
            ON  mc.[campaña_id] = crc.[campaña_id]
            AND mc.modulo_id    = crc.modulo_id
            AND mc.estado       = 'CONGELADO'
        WHERE CAST(crc.fecha AS date) >= @FechaInicio
          AND CAST(crc.fecha AS date) <= @FechaFin
        GROUP BY
            CAST(crc.fecha AS date), CAST(crc.pad_id AS int),
            CAST(crc.[campaña_id] AS int), CAST(crc.modulo_id AS int);

        INSERT INTO [reclamo].[log_sincronizacion]
            (ejecucion_id, tabla_destino, tabla_origen, accion,
             fecha_dato, [campaña_id], modulo_id, campo,
             valor_anterior, valor_nuevo, observacion)
        SELECT
            @EjecucionId, 'camiones_reclamo',
            'control_reclamo_sulfuro_camiones_thm_diario',
            CASE
                WHEN c.modulo_congelado = 0 THEN 'OMITIDO'
                WHEN cr.camiones_id IS NULL THEN 'INSERTADO'
                ELSE 'ACTUALIZADO'
            END,
            c.fecha, c.[campaña_id], c.modulo_id, 'm3_thm',
            cr.m3_thm, c.m3_thm,
            CASE
                WHEN c.modulo_congelado = 0
                    THEN N'Modulo no congelado. No se sincroniza.'
                WHEN cr.camiones_id IS NOT NULL
                 AND ABS(COALESCE(cr.m3_thm,0) - c.m3_thm) > 0.001
                    THEN N'El ETL cambio un valor ya sincronizado.'
                ELSE NULL
            END
        FROM #Cam c
        LEFT JOIN [reclamo].[camiones_reclamo] cr
            ON  cr.fecha        = c.fecha
            AND cr.[campaña_id] = c.[campaña_id]
            AND cr.modulo_id    = c.modulo_id
        WHERE c.modulo_congelado = 0
           OR cr.camiones_id IS NULL
           OR ABS(COALESCE(cr.m3_thm,0) - c.m3_thm) > 0.001;

        IF @Confirmar = 1
        BEGIN
            MERGE [reclamo].[camiones_reclamo] AS tgt
            USING (SELECT * FROM #Cam WHERE modulo_congelado = 1) AS src
                ON  tgt.fecha        = src.fecha
                AND tgt.[campaña_id] = src.[campaña_id]
                AND tgt.modulo_id    = src.modulo_id
            WHEN MATCHED THEN UPDATE SET
                m3_thm         = src.m3_thm,
                tms_thm        = src.m3_thm *
                                 (SELECT mc.densidad_oficial
                                  FROM [reclamo].[modulo_congelado] mc
                                  WHERE mc.[campaña_id] = src.[campaña_id]
                                    AND mc.modulo_id    = src.modulo_id),
                fecha_registro = SYSDATETIME()
            WHEN NOT MATCHED BY TARGET THEN INSERT
                (fecha, [campaña_id], pad_id, modulo_id, m3_thm, tms_thm,
                 fuente_oficial, estado)
            VALUES
                (src.fecha, src.[campaña_id], src.pad_id, src.modulo_id,
                 src.m3_thm,
                 src.m3_thm * (SELECT mc.densidad_oficial
                               FROM [reclamo].[modulo_congelado] mc
                               WHERE mc.[campaña_id] = src.[campaña_id]
                                 AND mc.modulo_id    = src.modulo_id),
                 'THM', 'VIGENTE');

            PRINT 'Camiones sincronizados   : ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
        END;

        /* ================================================================
           C. APILADO, desde control_apilado_diario

           Desactivado por defecto. La estructura de esa tabla debe
           confirmarse con la seccion 11 del script 00 antes de habilitarlo.
           Su rol es resolver la fecha de conformacion del modulo, que es el
           inicio de la campana, no calcular reclamo.
        ================================================================ */
        IF @SincronizarApilado = 1
        BEGIN
            PRINT '';
            PRINT 'ATENCION: la sincronizacion de apilado esta declarada pero no';
            PRINT 'implementada, porque la estructura de control_apilado_diario';
            PRINT 'aun no fue verificada. Ejecute la seccion 11 del script 00 y';
            PRINT 'complete este bloque antes de usarlo.';
        END;

        /* ================================================================
           D. RESUMEN
        ================================================================ */
        DECLARE @Ins int, @Act int, @Omi int;
        SELECT
            @Ins = SUM(CASE WHEN accion = 'INSERTADO'   THEN 1 ELSE 0 END),
            @Act = SUM(CASE WHEN accion = 'ACTUALIZADO' THEN 1 ELSE 0 END),
            @Omi = SUM(CASE WHEN accion = 'OMITIDO'     THEN 1 ELSE 0 END)
        FROM [reclamo].[log_sincronizacion]
        WHERE ejecucion_id = @EjecucionId;

        PRINT '';
        PRINT 'Insertados   : ' + CAST(COALESCE(@Ins,0) AS varchar);
        PRINT 'Actualizados : ' + CAST(COALESCE(@Act,0) AS varchar);
        PRINT 'Omitidos     : ' + CAST(COALESCE(@Omi,0) AS varchar);

        IF COALESCE(@Act,0) > 0
        BEGIN
            PRINT '';
            PRINT 'ATENCION: el ETL cambio valores ya sincronizados. Si esas fechas';
            PRINT 'ya fueron publicadas, hay que reprocesar el reporte.';

            SELECT
                l.fecha_dato, l.[campaña_id], l.modulo_id, l.campo,
                l.valor_anterior, l.valor_nuevo,
                l.valor_nuevo - l.valor_anterior AS diferencia,
                l.observacion
            FROM [reclamo].[log_sincronizacion] l
            WHERE l.ejecucion_id = @EjecucionId
              AND l.accion = 'ACTUALIZADO'
            ORDER BY ABS(COALESCE(l.valor_nuevo,0) - COALESCE(l.valor_anterior,0)) DESC;
        END;

        IF COALESCE(@Omi,0) > 0
        BEGIN
            PRINT '';
            PRINT 'Los siguientes datos NO entraron porque su modulo no esta';
            PRINT 'congelado. Congelelos con sp_congelar_modulo y vuelva a';
            PRINT 'sincronizar.';

            SELECT DISTINCT
                l.[campaña_id], l.modulo_id, l.tabla_destino,
                MIN(l.fecha_dato) OVER (PARTITION BY l.[campaña_id], l.modulo_id) AS desde,
                MAX(l.fecha_dato) OVER (PARTITION BY l.[campaña_id], l.modulo_id) AS hasta
            FROM [reclamo].[log_sincronizacion] l
            WHERE l.ejecucion_id = @EjecucionId
              AND l.accion = 'OMITIDO';
        END;

        IF @Confirmar = 0
            PRINT 'MODO VISTA PREVIA. Se registro el diagnostico pero no se escribio.';

        UPDATE [reclamo].[log_ejecucion]
        SET fecha_fin       = SYSDATETIME(),
            filas_afectadas = COALESCE(@Ins,0) + COALESCE(@Act,0),
            estado          = 'OK'
        WHERE ejecucion_id = @EjecucionId;

        DROP TABLE IF EXISTS #Topo;
        DROP TABLE IF EXISTS #Cam;
    END TRY
    BEGIN CATCH
        IF @EjecucionId IS NOT NULL
            UPDATE [reclamo].[log_ejecucion]
            SET fecha_fin = SYSDATETIME(), estado = 'ERROR', mensaje = ERROR_MESSAGE()
            WHERE ejecucion_id = @EjecucionId;
        THROW;
    END CATCH
END;