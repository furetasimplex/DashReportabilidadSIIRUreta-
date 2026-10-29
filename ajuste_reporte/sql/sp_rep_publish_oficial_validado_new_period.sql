ALTER PROCEDURE inventar_SpcHidr.sp_rep_publish_oficial_validado
    @run_id UNIQUEIDENTIFIER,
    @caso_id INT,
    @usuario_validacion NVARCHAR(128),
    @resumen_json NVARCHAR(MAX) = NULL,
    @modelo_id INT = NULL,
    @solver_run_id INT = NULL
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

    -- DC_NEW_PERIOD_ONLY_M6_V1: no reemplaza versiones, incluso para legacy120.
    BEGIN TRANSACTION;
    BEGIN TRY
        DECLARE @lock_rows BIGINT;
        SELECT @lock_rows=COUNT_BIG(*) FROM inventar_SpcHidr.Datos_conciliados_of_ver WITH(TABLOCKX,HOLDLOCK);
        DECLARE @modelo_real INT,@codigo_modelo VARCHAR(64);
        SELECT @modelo_real=c.modelo_id,@codigo_modelo=m.codigo
        FROM DEV_SIIR.hidro.recon_caso c WITH(HOLDLOCK)
        JOIN DEV_SIIR.hidro.recon_modelo m WITH(HOLDLOCK) ON m.id=c.modelo_id WHERE c.id=@caso_id;
        INSERT INTO @periodo(caso_id,fecha_inicio,fecha_fin)
        EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id=@caso_id;
        IF (SELECT COUNT(*) FROM @periodo)<>1 THROW 50001,'Periodo ausente o ambiguo.',1;
        SELECT @fecha_inicio=fecha_inicio,@fecha_fin=fecha_fin FROM @periodo WHERE caso_id=@caso_id;
        IF @fecha_inicio IS NULL OR @fecha_fin IS NULL OR @fecha_fin<@fecha_inicio
            THROW 50001,'Periodo invalido.',1;

        -- El indice existente es run_id/Fecha: TABLOCKX evita phantoms tambien sin
        -- indice por Fecha y serializa TODOS los publicadores/escritores de versiones.
        -- Mantener bloqueo hasta COMMIT/ROLLBACK. No es un SELECT fuera del SP.
        DECLARE @fechas NVARCHAR(MAX),@conflicto NVARCHAR(2048);
        SELECT @fechas=STRING_AGG(CONVERT(nvarchar(max),Fecha,23),N',') WITHIN GROUP(ORDER BY Fecha)
        FROM (SELECT DISTINCT Fecha FROM inventar_SpcHidr.Datos_conciliados_of_ver WITH(TABLOCKX,HOLDLOCK)
              WHERE Fecha BETWEEN @fecha_inicio AND @fecha_fin) existentes;
        IF @fechas IS NOT NULL
        BEGIN
            SET @conflicto=N'Publicacion detenida: existen versiones en fechas '+LEFT(@fechas,1900);
            THROW 50004,@conflicto,1;
        END;
        IF @run_id IS NULL OR EXISTS(SELECT 1 FROM inventar_SpcHidr.Datos_conciliados_of_ver WHERE run_id=@run_id)
            THROW 50004,'UUID invalido o ya utilizado en otro periodo.',1;
        DECLARE @dias INT=DATEDIFF(day,@fecha_inicio,@fecha_fin)+1;
        IF (SELECT COUNT(*) FROM inventar_SpcHidr.rep_prod_ajustado_stg WITH(UPDLOCK,HOLDLOCK) WHERE run_id=@run_id)<>@dias
           OR (SELECT COUNT(DISTINCT Fecha) FROM inventar_SpcHidr.rep_prod_ajustado_stg WITH(UPDLOCK,HOLDLOCK) WHERE run_id=@run_id)<>@dias
           OR EXISTS(SELECT 1 FROM inventar_SpcHidr.rep_prod_ajustado_stg WITH(UPDLOCK,HOLDLOCK) WHERE run_id=@run_id
                     AND (caso_id<>@caso_id OR Fecha IS NULL OR Fecha NOT BETWEEN @fecha_inicio AND @fecha_fin))
            THROW 50005,'Staging incompleto, duplicado o fuera del caso/periodo.',1;
        IF @codigo_modelo='hidrometalurgia_125_v2'
        BEGIN
            IF @modelo_id IS NULL OR @solver_run_id IS NULL OR @modelo_id<>@modelo_real
                THROW 50005,'M6 exige identidad explicita de modelo y solver.',1;
            IF (SELECT COUNT(*) FROM DEV_SIIR.hidro.recon_caso_oficial WITH(HOLDLOCK) WHERE caso_id=@caso_id)<>1
               OR NOT EXISTS(SELECT 1 FROM DEV_SIIR.hidro.recon_solver_run r WITH(HOLDLOCK)
                  JOIN DEV_SIIR.hidro.recon_caso_oficial co WITH(HOLDLOCK) ON co.solver_run_id=r.id AND co.caso_id=r.caso_id
                  WHERE r.id=@solver_run_id AND r.caso_id=@caso_id AND r.estado='success')
                THROW 50005,'Run reconciliado M6 no corresponde a la seleccion oficial.',1;
            IF NOT EXISTS(SELECT 1 FROM inventar_SpcHidr.rep_prod_ajuste_log WITH(HOLDLOCK) WHERE run_id=@run_id AND caso_id=@caso_id AND ok=1
                AND ISJSON(totales_json)=1 AND JSON_VALUE(totales_json,'$.modelo_codigo')=@codigo_modelo
                AND TRY_CONVERT(int,JSON_VALUE(totales_json,'$.modelo_id'))=@modelo_id
                AND TRY_CONVERT(int,JSON_VALUE(totales_json,'$.solver_run_id'))=@solver_run_id
                AND JSON_VALUE(totales_json,'$.namespace')='DEV_SIIR.hidro.recon_caso')
                THROW 50005,'UUID sin trazabilidad M6 en el log existente.',1;
        END;

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

        IF @rows_published <> @dias
        BEGIN
            THROW 50002, 'El publicador no inserto todos los dias esperados.', 1;
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