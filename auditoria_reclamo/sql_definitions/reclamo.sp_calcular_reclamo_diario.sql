/* ============================================================================
   SP 6. reclamo.sp_calcular_reclamo_diario

   Materializa reclamo.calculo_diario a partir de reclamo.v_reclamo_diario, y
   deja constancia de la corrida en reclamo.log_ejecucion.

   El calculo es idempotente: reprocesar el mismo rango produce el mismo
   resultado, y una fila PRELIMINAR_CV25 se convierte sola en TOPOGRAFIA en
   cuanto llega la medicion.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_calcular_reclamo_diario]
(
    @FechaInicio    date,
    @FechaFin       date,
    @DiasReproceso  int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @EjecucionId int;
    DECLARE @Desde date;

    BEGIN TRY
        IF @FechaInicio IS NULL OR @FechaFin IS NULL
            THROW 60501, 'Debe informar el rango de fechas.', 1;
        IF @FechaInicio > @FechaFin
            THROW 60502, 'La fecha inicial no puede ser mayor que la final.', 1;

        SET @Desde =
            CASE
                WHEN DATEADD(DAY, -@DiasReproceso, @FechaFin) < @FechaInicio
                    THEN DATEADD(DAY, -@DiasReproceso, @FechaFin)
                ELSE @FechaInicio
            END;

        /* El sistema no calcula hacia atras de la fecha de corte. Lo anterior
           vive como linea base en modulo_congelado y no se recalcula. */
        DECLARE @Corte date = [reclamo].[fn_fecha_corte]();

        IF @Corte IS NULL
            THROW 60503,
                  'No hay FECHA_CORTE_SISTEMA en reclamo.configuracion.', 1;

        IF @Desde < @Corte
        BEGIN
            PRINT '-- El rango solicitado comienza antes de la fecha de corte ('
                + CONVERT(varchar(10), @Corte, 120) + ').';
            PRINT '-- Se recorta al corte. Lo anterior es linea base y no se recalcula.';
            SET @Desde = @Corte;
        END;

        IF @FechaFin < @Corte
            THROW 60504,
                  'Todo el rango solicitado es anterior a la fecha de corte del sistema.', 1;

        INSERT INTO [reclamo].[log_ejecucion]
            (procedimiento, rango_desde, rango_hasta, estado)
        VALUES
            ('reclamo.sp_calcular_reclamo_diario', @Desde, @FechaFin, 'EN_CURSO');

        SET @EjecucionId = SCOPE_IDENTITY();

        PRINT '-- Rango efectivo: ' + CONVERT(varchar(10), @Desde, 120)
            + ' a ' + CONVERT(varchar(10), @FechaFin, 120);

        /* Se borra y recarga el rango completo: mas simple y seguro que un
           MERGE con muchas columnas, y el volumen diario es pequeno. */
        DELETE FROM [reclamo].[calculo_diario]
        WHERE fecha_operacion >= @Desde
          AND fecha_operacion <= @FechaFin;

        INSERT INTO [reclamo].[calculo_diario]
        (
            fecha_operacion, [campaña_id], pad_id, modulo_id, modulo_numero, rotopala_id,
            tms_conformado, m3_totales, densidad_oficial,
            m3_camiones_dia, tms_camiones_dia,
            m3_camiones_acum, tms_camiones_acum,
            m3_disponible_roto, tms_disponible_roto,
            m3_rotopala_dia, tms_rotopala_dia,
            m3_rotopala_acum, tms_rotopala_acum,
            avance_total_pct, avance_roto_pct, avance_camiones_pct,
            ajuste_m3, ajuste_tms, ajustes_aplicados,
            fuente_reclamo, metodo_calculo, flag_calculo, flag_cuadratura,
            ejecucion_id
        )
        SELECT
            rd.fecha_operacion,
            rd.[campaña_id],
            rd.pad_id,
            rd.modulo_id,
            rd.modulo_numero,
            rd.rotopala_id,

            rd.tms_conformado,
            rd.m3_totales,
            rd.densidad_oficial,

            rd.m3_camiones_dia,
            rd.tms_camiones_dia,

            rd.m3_camiones_acum,
            rd.tms_camiones_acum,

            rd.m3_disponible_roto,
            rd.tms_disponible_roto,

            rd.m3_rotopala_dia,
            rd.tms_rotopala_dia,
            rd.m3_rotopala_acum_topografia,
            rd.m3_rotopala_acum_topografia * rd.densidad_oficial,

            rd.avance_total_pct_calculado,
            rd.avance_roto_pct,
            rd.avance_camiones_pct,

            rd.ajuste_m3,
            rd.ajuste_tms,
            rd.ajustes_aplicados,

            rd.fuente_reclamo,
            rd.metodo_calculo,
            rd.flag_calculo,
            cm.flag_cuadratura,

            @EjecucionId
        FROM [reclamo].[v_reclamo_diario] rd
        LEFT JOIN [reclamo].[v_cuadratura_modulo] cm
            ON  cm.[campaña_id] = rd.[campaña_id]
            AND cm.modulo_id    = rd.modulo_id
        WHERE rd.fecha_operacion >= @Desde
          AND rd.fecha_operacion <= @FechaFin;

        DECLARE @Filas int = @@ROWCOUNT;

        DECLARE @Topo  int = (SELECT COUNT(*) FROM [reclamo].[calculo_diario]
                              WHERE ejecucion_id = @EjecucionId AND fuente_reclamo = 'TOPOGRAFIA');
        DECLARE @Prel  int = (SELECT COUNT(*) FROM [reclamo].[calculo_diario]
                              WHERE ejecucion_id = @EjecucionId AND fuente_reclamo = 'PRELIMINAR_CV25');
        DECLARE @Sin   int = (SELECT COUNT(*) FROM [reclamo].[calculo_diario]
                              WHERE ejecucion_id = @EjecucionId AND fuente_reclamo = 'SIN_DATO');

        UPDATE [reclamo].[log_ejecucion]
        SET fecha_fin        = SYSDATETIME(),
            filas_afectadas  = @Filas,
            filas_topografia = @Topo,
            filas_preliminar = @Prel,
            filas_sin_dato   = @Sin,
            estado           = 'OK'
        WHERE ejecucion_id = @EjecucionId;

        PRINT 'Filas calculadas      : ' + CAST(@Filas AS varchar);
        PRINT '  Fuente TOPOGRAFIA   : ' + CAST(@Topo AS varchar) + ' (OFICIAL)';
        PRINT '  Fuente PRELIMINAR   : ' + CAST(@Prel AS varchar) + ' (se reemplaza al llegar topografia)';
        PRINT '  Sin dato            : ' + CAST(@Sin  AS varchar);

        IF @Prel > 0
        BEGIN
            PRINT '';
            PRINT 'ATENCION: hay reclamo publicado con fuente PRELIMINAR_CV25.';
            PRINT 'Estas fechas y modulos se corregiran solos al reprocesar el rango';
            PRINT 'una vez cargada la medicion topografica:';

            SELECT DISTINCT
                cd.fecha_operacion,
                cd.pad_id,
                cd.modulo_numero,
                cd.tms_rotopala_dia,
                cd.flag_calculo
            FROM [reclamo].[calculo_diario] cd
            WHERE cd.ejecucion_id = @EjecucionId
              AND cd.fuente_reclamo = 'PRELIMINAR_CV25'
            ORDER BY cd.fecha_operacion, cd.pad_id, cd.modulo_numero;
        END;

        /* Modulos que superaron el 100 por ciento. */
        IF EXISTS (SELECT 1 FROM [reclamo].[v_cuadratura_modulo]
                   WHERE flag_cuadratura = 'SOBRE_100_PROPONER_TRASPASO')
        BEGIN
            PRINT '';
            PRINT 'ATENCION: modulos con extraccion sobre 100 por ciento.';
            PRINT 'Requieren un ajuste TRASPASO_MODULO documentado.';

            SELECT
                cm.[campaña_id],
                cm.modulo_numero,
                cm.porcentaje_extraido,
                cm.m3_excedente,
                cm.tms_excedente,
                cm.modulo_siguiente_propuesto
            FROM [reclamo].[v_cuadratura_modulo] cm
            WHERE cm.flag_cuadratura = 'SOBRE_100_PROPONER_TRASPASO'
            ORDER BY cm.porcentaje_extraido DESC;
        END;
    END TRY
    BEGIN CATCH
        IF @EjecucionId IS NOT NULL
            UPDATE [reclamo].[log_ejecucion]
            SET fecha_fin = SYSDATETIME(),
                estado    = 'ERROR',
                mensaje   = ERROR_MESSAGE()
            WHERE ejecucion_id = @EjecucionId;
        THROW;
    END CATCH
END;