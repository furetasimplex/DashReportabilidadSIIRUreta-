CREATE   PROCEDURE inventar_SpcHidr.sp_rep_publish_oficial_validado
    @run_id UNIQUEIDENTIFIER,
    @caso_id INT,
    @usuario_validacion NVARCHAR(128),
    @resumen_json NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @fecha_inicio DATE = NULL;
    DECLARE @fecha_fin DATE = NULL;
    DECLARE @validation_id BIGINT = NULL;
    DECLARE @rows_published INT = 0;

    DECLARE @periodo TABLE
    (
        caso_id INT,
        fecha_inicio DATE,
        fecha_fin DATE
    );

    INSERT INTO @periodo(caso_id, fecha_inicio, fecha_fin)
    EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id = @caso_id;

    SELECT TOP 1
        @fecha_inicio = fecha_inicio,
        @fecha_fin = fecha_fin
    FROM @periodo;

    IF @fecha_inicio IS NULL OR @fecha_fin IS NULL
    BEGIN
        THROW 50001, 'No se pudo obtener el período del caso.', 1;
    END;

    BEGIN TRANSACTION;

    BEGIN TRY
        IF OBJECT_ID('inventar_SpcHidr.rep_prod_validacion_log', 'U') IS NOT NULL
        BEGIN
            INSERT INTO inventar_SpcHidr.rep_prod_validacion_log
            (
                run_id,
                caso_id,
                fecha_inicio,
                fecha_fin,
                decision,
                usuario_validacion,
                resumen_json
            )
            VALUES
            (
                @run_id,
                @caso_id,
                @fecha_inicio,
                @fecha_fin,
                'ACEPTADO',
                @usuario_validacion,
                @resumen_json
            );

            SET @validation_id = CAST(SCOPE_IDENTITY() AS BIGINT);
        END;

        DELETE FROM inventar_SpcHidr.Datos_conciliados_of_ver
        WHERE Fecha BETWEEN @fecha_inicio AND @fecha_fin;

        INSERT INTO inventar_SpcHidr.Datos_conciliados_of_ver
        (
            [Fecha],
            [Chancado_TMS_Real],
            [Humedad_Turno_A],
            [Humedad_Turno_B],
            [Humedad_promedio_dia],
            [Sal_turno_A],
            [Sal_Turno_B],
            [Sal_promedio_dia],
            [Apilado_TMH_turno_A],
            [Apilado_TMH_turno_B],
            [Apilado_TMH_promedio_dia],
            [Apilado_TMS_Real],
            [Apilado_TMS_Plan],
            [Campana_apilado],
            [Modulo_apilado],
            [Avance_apilado],
            [Ley_CuT_Real],
            [Ley_CuT_Plan],
            [Cobre_fino_Apilado_Real],
            [Cobre_fino_Apilado_Plan],
            [TMS_Rotopala_1_Real],
            [TMS_Rotopala_1_Plan],
            [Campana_reclamo_oxidos],
            [Modulo_reclamo_oxidos],
            [Avance_reclamo_oxidos],
            [TMS_Rotopala_2_Real],
            [TMS_Rotopala_2_Plan],
            [Campana_reclamo_sulfuros],
            [modulo_reclamo_sulfuros],
            [Avance_reclamo_sulfuros],
            [Camiones_TMS_Reclamo_Oxidos],
            [Camiones_TMS_Reclamo_Sulfuros],
            [Movido],
            [Extraido],
            [Camiones_TMS_total],
            [Camiones_TMS_plan],
            [Campana_reclamo_camiones],
            [Modulo_reclamo_camiones],
            [Total_Ripios_Incluye_Camiones_Real],
            [Total_Ripios_Incluye_Camiones_Plan],
            [Produccion_Catodos_Real],
            [Produccion_Catodos_Plan],
            [SRR_TMS_Turno_A],
            [SRR_TMS_Turno_B],
            [SRR_TMS_promedio_dia],
            [SRR_TMS_Plan],
            [Ley_CuT_Real_srr],
            [Ley_CuT_Plan_srr],
            [estado],
            [run_id],
            [caso_id],
            [version_reglas],
            [ts_ajuste],
            [es_activa],
            [origen],
            [comentario],
            [fecha_validacion],
            [usuario_validacion],
            [estado_validacion],
            [validation_id]
        )
        SELECT
            s.[Fecha],
            s.[Chancado_TMS_Real],
            s.[Humedad_Turno_A],
            s.[Humedad_Turno_B],
            s.[Humedad_promedio_dia],
            s.[Sal_turno_A],
            s.[Sal_Turno_B],
            s.[Sal_promedio_dia],
            s.[Apilado_TMH_turno_A],
            s.[Apilado_TMH_turno_B],
            s.[Apilado_TMH_promedio_dia],
            s.[Apilado_TMS_Real],
            s.[Apilado_TMS_Plan],
            s.[Campana_apilado],
            s.[Modulo_apilado],
            s.[Avance_apilado],
            s.[Ley_CuT_Real],
            s.[Ley_CuT_Plan],
            s.[Cobre_fino_Apilado_Real],
            s.[Cobre_fino_Apilado_Plan],
            s.[TMS_Rotopala_1_Real],
            s.[TMS_Rotopala_1_Plan],
            s.[Campana_reclamo_oxidos],
            s.[Modulo_reclamo_oxidos],
            s.[Avance_reclamo_oxidos],
            s.[TMS_Rotopala_2_Real],
            s.[TMS_Rotopala_2_Plan],
            s.[Campana_reclamo_sulfuros],
            s.[modulo_reclamo_sulfuros],
            s.[Avance_reclamo_sulfuros],
            s.[Camiones_TMS_Reclamo_Oxidos],
            s.[Camiones_TMS_Reclamo_Sulfuros],
            s.[Movido],
            s.[Extraido],
            s.[Camiones_TMS_total],
            s.[Camiones_TMS_plan],
            s.[Campana_reclamo_camiones],
            s.[Modulo_reclamo_camiones],
            s.[Total_Ripios_Incluye_Camiones_Real],
            s.[Total_Ripios_Incluye_Camiones_Plan],
            s.[Produccion_Catodos_Real],
            s.[Produccion_Catodos_Plan],
            s.[SRR_TMS_Turno_A],
            s.[SRR_TMS_Turno_B],
            s.[SRR_TMS_promedio_dia],
            s.[SRR_TMS_Plan],
            s.[Ley_CuT_Real_srr],
            s.[Ley_CuT_Plan_srr],
            ISNULL(s.[estado], 1),
            @run_id,
            @caso_id,
            ISNULL(s.[version_reglas], 1),
            ISNULL(s.[ts_ajuste], SYSUTCDATETIME()),
            CAST(1 AS bit),
            N'AJUSTE_REPORTE',
            N'Publicado desde rep_prod_ajustado_stg tras aceptación en modal',
            SYSDATETIME(),
            @usuario_validacion,
            'VALIDADO',
            @validation_id
        FROM inventar_SpcHidr.rep_prod_ajustado_stg s
        WHERE s.run_id = @run_id
          AND s.caso_id = @caso_id
          AND s.Fecha BETWEEN @fecha_inicio AND @fecha_fin
        ORDER BY s.Fecha;

        SET @rows_published = @@ROWCOUNT;

        IF @rows_published = 0
        BEGIN
            THROW 50002, 'No se encontraron filas en rep_prod_ajustado_stg para publicar.', 1;
        END;

        IF @validation_id IS NOT NULL
        BEGIN
            UPDATE inventar_SpcHidr.rep_prod_validacion_log
            SET filas_publicadas = @rows_published
            WHERE validation_id = @validation_id;
        END;

        COMMIT TRANSACTION;

        SELECT
            @validation_id AS validation_id,
            @rows_published AS rows_published;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
        THROW 50003, @msg, 1;
    END CATCH
END