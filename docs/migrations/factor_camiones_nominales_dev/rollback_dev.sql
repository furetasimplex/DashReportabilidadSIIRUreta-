-- Rollback integral de objetos SQL. El runner restaura tambien resultados y Python.
-- Ejecutar solo este DDL no restaura V2/DC/cache: usar el comando rollback del runner.
SET XACT_ABORT ON;
IF DB_NAME()<>N'inventar_SpcHidr' THROW 51000, 'Solo DEV.', 1;
IF @@TRANCOUNT=0 THROW 51030, 'Rollback requiere una transaccion externa.', 1;
-- No destruir historia nominal registrada despues de los seeds de esta migracion.
IF EXISTS (SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
 WHERE parametro='CARGA_NOMINAL_TMH_VIAJE'
 AND (usuario_registro<>N'MIGRACION_NOMINALES_V2_DEV' OR vigencia_desde<>'20260701'
      OR vigencia_hasta IS NOT NULL OR activo<>1
      OR NOT ((flota='KOM' AND valor=357) OR (flota='CAT' AND valor=236))))
 THROW 51032, 'Existen modificaciones nominales posteriores; revisar rollback.', 1;
IF EXISTS (SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_auditoria_test
 WHERE parametro='CARGA_NOMINAL_TMH_VIAJE')
 THROW 51032, 'Existe auditoria nominal posterior; revisar rollback.', 1;
GO

CREATE OR ALTER PROCEDURE inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test
    @Flota varchar(20),
    @Valor decimal(18,6),
    @VigenciaDesde date,
    @Motivo nvarchar(1000),
    @Usuario nvarchar(128)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF DB_NAME()<>N'inventar_SpcHidr' THROW 51000, 'Solo DEV.', 1;
    IF @Flota IS NULL OR @Flota NOT IN ('KOM','CAT') THROW 51010, 'Flota debe ser KOM o CAT.', 1;
    IF @Valor IS NULL OR @Valor<=0 THROW 51011, 'El limite debe ser mayor que cero.', 1;
    IF @VigenciaDesde IS NULL THROW 51012, 'Vigente desde es obligatorio.', 1;
    IF NULLIF(LTRIM(RTRIM(@Motivo)),N'') IS NULL OR NULLIF(LTRIM(RTRIM(@Usuario)),N'') IS NULL
        THROW 51013, 'Usuario y motivo son obligatorios.', 1;
    DECLARE @Propia bit=CASE WHEN @@TRANCOUNT=0 THEN 1 ELSE 0 END;
    IF @Propia=1 BEGIN TRANSACTION;
    BEGIN TRY
        DECLARE @Lock int, @N bigint;
        EXEC @Lock=sys.sp_getapplock @Resource='SIIR_FACTOR_CAMIONES_PARAMETROS_DEV',
            @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=15000;
        IF @Lock<0 THROW 51014, 'No fue posible bloquear los parametros; reintente.', 1;
        SELECT @N=COUNT_BIG(*) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (TABLOCKX,HOLDLOCK);
        DECLARE @Mensaje nvarchar(2048);
        IF EXISTS (SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
                   WHERE flota=@Flota AND parametro='LIMITE_CARGA_AJUSTE' AND vigencia_desde=@VigenciaDesde)
        BEGIN
            SET @Mensaje=CONCAT('Ya existe una vigencia ',@Flota,' iniciada el ',CONVERT(varchar(10),@VigenciaDesde,105),'.');
            THROW 51015, @Mensaje, 1;
        END;
        DECLARE @Id bigint, @Anterior decimal(18,6), @Hasta date, @Siguiente date;
        IF (SELECT COUNT(*) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
            WHERE flota=@Flota AND parametro='LIMITE_CARGA_AJUSTE' AND activo=1
              AND vigencia_desde<=@VigenciaDesde AND (vigencia_hasta IS NULL OR @VigenciaDesde<vigencia_hasta))<>1
            THROW 51016, 'La fecha debe estar cubierta por exactamente una vigencia existente.', 1;
        SELECT @Id=id,@Anterior=valor,@Hasta=vigencia_hasta
        FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
        WHERE flota=@Flota AND parametro='LIMITE_CARGA_AJUSTE' AND activo=1
          AND vigencia_desde<=@VigenciaDesde AND (vigencia_hasta IS NULL OR @VigenciaDesde<vigencia_hasta);
        SELECT @Siguiente=MIN(vigencia_desde) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
        WHERE flota=@Flota AND parametro='LIMITE_CARGA_AJUSTE' AND activo=1 AND vigencia_desde>@VigenciaDesde;
        IF @Hasta<>@Siguiente OR (@Hasta IS NULL AND @Siguiente IS NOT NULL) OR (@Hasta IS NOT NULL AND @Siguiente IS NULL)
            THROW 51017, 'Historia temporal inconsistente; revisar vigencias.', 1;
        DECLARE @Registro datetime2(7)=SYSDATETIME(), @Retro bit, @Fin date;
        SET @Retro=CASE WHEN @VigenciaDesde<CONVERT(date,@Registro) THEN 1 ELSE 0 END;
        UPDATE inventar_SpcHidr.factor_camiones_parametro_vigencia_test SET vigencia_hasta=@VigenciaDesde WHERE id=@Id;
        INSERT inventar_SpcHidr.factor_camiones_parametro_vigencia_test
            (flota,parametro,valor,vigencia_desde,vigencia_hasta,motivo,usuario_registro,fecha_registro)
        VALUES (@Flota,'LIMITE_CARGA_AJUSTE',@Valor,@VigenciaDesde,@Siguiente,@Motivo,@Usuario,@Registro);
        -- Verifica continuidad del historial completo de esta flota.
        IF EXISTS (SELECT 1 FROM (
            SELECT vigencia_hasta, LEAD(vigencia_desde) OVER (ORDER BY vigencia_desde) siguiente
            FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
            WHERE flota=@Flota AND parametro='LIMITE_CARGA_AJUSTE' AND activo=1
        ) h WHERE vigencia_hasta<>siguiente OR (vigencia_hasta IS NULL AND siguiente IS NOT NULL)
                   OR (vigencia_hasta IS NOT NULL AND siguiente IS NULL))
            THROW 51017, 'Historia temporal inconsistente; revisar vigencias.', 1;
        INSERT inventar_SpcHidr.factor_camiones_parametro_auditoria_test
            (flota,parametro,accion,valor_anterior,valor_nuevo,vigencia_desde,usuario,motivo,fecha_registro,es_retroactivo)
        VALUES (@Flota,'LIMITE_CARGA_AJUSTE','NUEVA_VIGENCIA',@Anterior,@Valor,@VigenciaDesde,@Usuario,@Motivo,@Registro,@Retro);
        SELECT @Fin=MAX(Fecha) FROM inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test;
        IF @Propia=1 COMMIT;
        SELECT @Retro AS Es_Retroactivo, @VigenciaDesde AS Fecha_Inicio_Afectada,
               @Fin AS Fecha_Fin_Afectada, @Anterior AS Valor_Anterior, @Valor AS Valor_Nuevo;
    END TRY
    BEGIN CATCH
        IF @Propia=1 AND XACT_STATE()<>0 ROLLBACK;
        THROW;
    END CATCH;
END;

GO


CREATE OR ALTER TRIGGER inventar_SpcHidr.tr_factor_camiones_vigencia_solapamiento_test
ON inventar_SpcHidr.factor_camiones_parametro_vigencia_test
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    -- Salvaguarda también para DML privilegiado. Serializa solo esta tabla pequeña.
    DECLARE @n bigint;
    SELECT @n=COUNT_BIG(*) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (TABLOCKX,HOLDLOCK);
    IF EXISTS (
        SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test a
        JOIN inventar_SpcHidr.factor_camiones_parametro_vigencia_test b
          ON a.id<b.id AND a.flota=b.flota AND a.parametro=b.parametro
        WHERE a.activo=1 AND b.activo=1
          AND (b.vigencia_hasta IS NULL OR a.vigencia_desde<b.vigencia_hasta)
          AND (a.vigencia_hasta IS NULL OR b.vigencia_desde<a.vigencia_hasta)
    ) THROW 51001, 'Existen vigencias superpuestas de limites de carga para ajuste.', 1;
END;

GO

/* ================================================================
   ALTER inventar_SpcHidr.sp_factor_ajuste_camiones_test -- v2
   Redireccion de la fuente de camiones: mov_cam -> mov_cam_powerbi
   ----------------------------------------------------------------
   Cambia UNICAMENTE las secciones 2 y 3 del procedimiento. Las
   secciones 1, 4, 5, 6, 7 y 8 quedan identicas a la version anterior
   (que usaba inventar_SpcHidr.mov_cam).

   Validado antes de este cambio con comparar_mov_cam_vs_powerbi_23jul.sql
   contra el 2026-07-22 (mismo dia usado por el usuario para revisar):
     A_MOV_CAM_ACTUAL:                20346.14 KOM / 1651.999 CAT / 57-7 vueltas
     B_MOV_CAM_POWERBI (ton_descarga):20349.00 KOM / 1652.000 CAT / 57-7 vueltas
   Diferencia 0.013%, explicada por redondeo (ton_descarga en el
   Export de PowerBI viene sin decimales; mov_cam.Tonelaje_Hum_CIO
   trae mas precision). 0 duplicados en ambos lados ese dia, 7 de 7
   registros calzan fila a fila.

   MAPEO DE COLUMNAS confirmado con datos reales (no es el que sugiere
   el nombre a primera vista):
       mov_cam.Tonelaje_Hum_CIO (tonelada humeda, la que usa el SP
       para Produccion_KOM_TMH / Produccion_CAT_TMH)
           <- mov_cam_powerbi.ton_descarga
       mov_cam.Ton / mov_cam.Tonelaje_Seco_CIO (tonelada seca)
           <- mov_cam_powerbi.tonelaje_descarga_tms
       mov_cam.Turno ('A'/'B')       <- mov_cam_powerbi.turno ('TA'/'TB')
           (no se normaliza: Turno no se usa en la agregacion diaria
           de la seccion 4, solo pasa como trazabilidad)
       mov_cam.Fase                  <- mov_cam_powerbi.fase
       mov_cam.Banco                 <- mov_cam_powerbi.banco
           OJO: en mov_cam_powerbi, Banco viene igual a Fase en los
           datos revisados (ej. Fase=STRA, Banco=STRA) mientras en
           mov_cam eran distintos (Fase=STRA, Banco=DESC). Banco NO
           se usa en los totales de la seccion 4 (Produccion/Vueltas),
           solo pasa como trazabilidad -- no afecta este calculo, pero
           queda documentado por si se usa Banco en otro lado despues.
       mov_cam.Pala                  <- mov_cam_powerbi.excavadora
       mov_cam.Destino               <- mov_cam_powerbi.destino_descarga
       mov_cam.Flota_CEX             <- mov_cam_powerbi.flota_cex_tc
       mov_cam.N_BREAK               <- mov_cam_powerbi.n_break
       mov_cam.Origen, Solido, Poligono_CIO, Ton_Hum_Diseno_CAEX,
       PONDHumedad                   <- SIN EQUIVALENTE, quedan NULL.
           Ninguna de estas se usa en la agregacion final de la
           seccion 4 (Produccion/Vueltas/Estado_Calculo); solo
           formaban parte de la llave de deduplicacion de la
           seccion 3 anterior, que ya no aplica (ver mas abajo).

   DEDUPLICACION (seccion 3): mov_cam_powerbi ya tiene un indice
   unico de 9 columnas (fecha+turno+tipo_movimiento+fase+banco+
   excavadora+destino_descarga+flota_cex_tc+grade) que impide filas
   operacionales repetidas por diseno de la tabla. Por eso la
   deduplicacion por ROW_NUMBER() de la version anterior (necesaria
   porque mov_cam SI puede traer duplicados) se reemplaza por un
   passthrough: todas las filas de #MovCamNormalizado ya son unicas,
   entonces todas quedan con rn = 1. Se mantiene el nombre de la
   tabla temporal #MovCamClasificado y la columna rn para no romper
   la seccion 4, que sigue igual.

   Si en algun momento se necesita volver a comparar contra mov_cam,
   usar comparar_mov_cam_vs_powerbi_23jul.sql (parametrizable a
   cualquier fecha cambiando @FechaTest).
================================================================ */

CREATE OR ALTER PROCEDURE [inventar_SpcHidr].[sp_factor_ajuste_camiones_test]
    @FechaInicio date,
    @FechaFin    date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF @FechaInicio IS NULL OR @FechaFin IS NULL
    BEGIN
        THROW 50001, 'FechaInicio y FechaFin son obligatorias.', 1;
    END;
    IF @FechaInicio > @FechaFin
    BEGIN
        THROW 50002, 'FechaInicio no puede ser mayor que FechaFin.', 1;
    END;
    /* ============================================================
       1. SRR diario desde el reporte por turno
       ============================================================ */

    -- FASE 2A: una copia consistente de las vigencias, nunca valores de respaldo.
    -- HOLDLOCK protege la lectura completa frente al registro transaccional.
    SELECT flota,parametro,valor,vigencia_desde,vigencia_hasta
    INTO #ParametrosFactorV2
    FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (HOLDLOCK)
    WHERE activo=1 AND parametro='LIMITE_CARGA_AJUSTE';
    ;WITH Dias AS (
        SELECT @FechaInicio AS Fecha
        UNION ALL SELECT DATEADD(day,1,Fecha) FROM Dias WHERE Fecha<@FechaFin
    )
    SELECT d.Fecha,f.flota,COUNT(p.flota) AS cantidad,CAST(MIN(p.valor) AS float) AS limite
    INTO #LimitesFactorV2
    FROM Dias d CROSS JOIN (VALUES ('KOM'),('CAT')) f(flota)
    LEFT JOIN #ParametrosFactorV2 p ON p.flota=f.flota AND p.vigencia_desde<=d.Fecha
        AND (p.vigencia_hasta IS NULL OR d.Fecha<p.vigencia_hasta)
    GROUP BY d.Fecha,f.flota OPTION (MAXRECURSION 0);
    DECLARE @ErrorLimite nvarchar(2048);
    SELECT TOP(1) @ErrorLimite=CONCAT(
        CASE WHEN cantidad=0 THEN 'No existe limite vigente ' ELSE 'Existen multiples limites vigentes ' END,
        flota,' para ',CONVERT(varchar(10),Fecha,23),'.')
    FROM #LimitesFactorV2 WHERE cantidad<>1 ORDER BY Fecha,flota;
    IF @ErrorLimite IS NOT NULL THROW 51020,@ErrorLimite,1;
    CREATE UNIQUE CLUSTERED INDEX IX_LimitesFactorV2 ON #LimitesFactorV2(Fecha,flota);

    ;WITH SRR_Diario AS
    (
        SELECT
            s.Fecha,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'A' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_A,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'B' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_B,
            SUM(COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0)) AS SRR_TMS_Dia,
            COUNT(*) AS Cantidad_Registros_SRR
        FROM [inventar_SpcHidr].[v_srr_tms_origen_turno_emision_test] AS s
        WHERE s.Fecha BETWEEN @FechaInicio AND @FechaFin
        GROUP BY s.Fecha
    ),
    Base AS
    (
        SELECT
            i.Fecha,
            TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
                AS Apilado_TMH_Neto,
            TRY_CONVERT(float, a.Sal_promedio_dia)
                AS Sal_Dia,
            TRY_CONVERT(float, a.TMH_Bruto_Dia)
                AS Apilado_TMH_Bruto,
            TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
            + TRY_CONVERT(float, a.Sal_promedio_dia)
                AS Apilado_TMH_Bruto_Reconstruido,
            TRY_CONVERT(float, a.TMH_Bruto_Dia)
            -
            (
                TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
                + TRY_CONVERT(float, a.Sal_promedio_dia)
            ) AS Check_TMH_Bruto,
            h.Humedad_Inventario,
            h.Regla_Humedad_Inventario,
            h.Flag_Humedad_Inventario_Valida,
            i.Total_Inventario_Chancado_TMS,
            i.Inventario_Chancado_TMS_Anterior,
            i.Delta_Inventario_Chancado_TMS,
            i.Flag_Continuidad_Diaria,
            i.Flag_Inventario_Valido,
            COALESCE(s.SRR_TMS_Turno_A, 0.0)
                AS SRR_TMS_Turno_A,
            COALESCE(s.SRR_TMS_Turno_B, 0.0)
                AS SRR_TMS_Turno_B,
            COALESCE(s.SRR_TMS_Dia, 0.0)
                AS SRR_TMS_Dia,
            COALESCE(s.Cantidad_Registros_SRR, 0)
                AS Cantidad_Registros_SRR
        FROM [inventar_SpcHidr].[v_inventario_chancado_test] AS i
        LEFT JOIN [inventar_SpcHidr].[Historico_Apilado_Diario] AS a
            ON CAST(a.Fecha AS date) = i.Fecha
        LEFT JOIN [inventar_SpcHidr].[v_humedad_inventario_test] AS h
            ON h.Fecha = i.Fecha
        LEFT JOIN SRR_Diario AS s
            ON s.Fecha = i.Fecha
        WHERE i.Fecha BETWEEN @FechaInicio AND @FechaFin
    ),
    CalculoSinAjuste AS
    (
        SELECT
            b.*,
            CASE
                WHEN b.Apilado_TMH_Bruto IS NOT NULL
                 AND b.Flag_Humedad_Inventario_Valida = 1
                THEN
                    b.Apilado_TMH_Bruto
                    *
                    (
                        1.0
                        - b.Humedad_Inventario / 100.0
                    )
                ELSE NULL
            END AS Apilado_TMS_Sin_Ajuste
        FROM Base AS b
    ),
    MineralSinAjuste AS
    (
        SELECT
            c.*,
            CASE
                WHEN c.Apilado_TMS_Sin_Ajuste IS NOT NULL
                 AND c.Flag_Inventario_Valido = 1
                 AND c.Delta_Inventario_Chancado_TMS IS NOT NULL
                THEN
                    c.Apilado_TMS_Sin_Ajuste
                    + c.Delta_Inventario_Chancado_TMS
                ELSE NULL
            END AS Mineral_Chancado_TMS_Sin_Ajuste
        FROM CalculoSinAjuste AS c
    ),
    ChancadoSinAjuste AS
    (
        SELECT
            m.*,
            CASE
                WHEN m.Mineral_Chancado_TMS_Sin_Ajuste IS NOT NULL
                 AND m.Sal_Dia IS NOT NULL
                 AND m.SRR_TMS_Dia IS NOT NULL
                THEN
                    m.Mineral_Chancado_TMS_Sin_Ajuste
                    - m.Sal_Dia
                    - m.SRR_TMS_Dia
                ELSE NULL
            END AS Chancado_TMS_Sin_Ajuste
        FROM MineralSinAjuste AS m
    )
    SELECT
        Fecha,
        Apilado_TMH_Neto,
        Sal_Dia,
        Apilado_TMH_Bruto,
        Apilado_TMH_Bruto_Reconstruido,
        Check_TMH_Bruto,
        Humedad_Inventario,
        Regla_Humedad_Inventario,
        Flag_Humedad_Inventario_Valida,
        Total_Inventario_Chancado_TMS,
        Inventario_Chancado_TMS_Anterior,
        Delta_Inventario_Chancado_TMS,
        Flag_Continuidad_Diaria,
        Flag_Inventario_Valido,
        SRR_TMS_Turno_A,
        SRR_TMS_Turno_B,
        SRR_TMS_Dia,
        Cantidad_Registros_SRR,
        Apilado_TMS_Sin_Ajuste,
        Mineral_Chancado_TMS_Sin_Ajuste,
        Chancado_TMS_Sin_Ajuste
    INTO #BaseBalance
    FROM ChancadoSinAjuste;
    CREATE UNIQUE CLUSTERED INDEX IX_BaseBalance_Fecha
        ON #BaseBalance(Fecha);
    /* ============================================================
       2. Normalizacion de movimientos de camiones -- FUENTE NUEVA:
          inventar_SpcHidr.mov_cam_powerbi (antes mov_cam). Ver mapeo
          de columnas en el encabezado de este script.
       ============================================================ */
    SELECT
        m.fecha AS Fecha,
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(50), m.turno)
            ))
        ) AS Turno,
        CAST(NULL AS nvarchar(255)) AS Origen,          -- sin equivalente en mov_cam_powerbi
        CAST(NULL AS nvarchar(500)) AS Solido,          -- sin equivalente en mov_cam_powerbi
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.fase)
            ))
        ) AS Fase,
        LTRIM(RTRIM(
            CONVERT(nvarchar(100), m.banco)
        )) AS Banco,
        LTRIM(RTRIM(
            CONVERT(nvarchar(100), m.excavadora)
        )) AS Pala,
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.destino_descarga)
            ))
        ) AS Destino,
        CAST(NULL AS nvarchar(500)) AS Poligono_CIO,    -- sin equivalente en mov_cam_powerbi
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.flota_cex_tc)
            ))
        ) AS Flota_CEX,
        TRY_CONVERT(float, m.tonelaje_descarga_tms)
            AS Ton,
        TRY_CONVERT(float, m.n_break)
            AS N_BREAK,
        CAST(NULL AS float) AS Ton_Hum_Diseno_CAEX,     -- sin equivalente en mov_cam_powerbi
        TRY_CONVERT(float, m.ton_descarga)
            AS Tonelaje_Hum_CIO,                        -- validado: ton_descarga = tonelada humeda
        TRY_CONVERT(float, m.tonelaje_descarga_tms)
            AS Tonelaje_Seco_CIO,
        CAST(NULL AS float) AS PONDHumedad,             -- sin equivalente en mov_cam_powerbi
        CAST(NULL AS int) AS mov_id,                    -- mov_cam_powerbi no tiene este concepto
        m.id AS ID
    INTO #MovCamNormalizado
    FROM [inventar_SpcHidr].[mov_cam_powerbi] AS m
    WHERE m.fecha BETWEEN @FechaInicio AND @FechaFin
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.destino_descarga)
              ))
          ) = 'CH01'
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.fase)
              ))
          ) <> 'SRR'
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.flota_cex_tc)
              ))
          ) IN ('KOM', 'CAT');
    CREATE INDEX IX_MovCamNormalizado_Fecha
        ON #MovCamNormalizado(Fecha);
    /* ============================================================
       3. Deduplicacion -- YA NO APLICA con mov_cam_powerbi.
          La tabla tiene un indice unico de 9 columnas
          (fecha+turno+tipo_movimiento+fase+banco+excavadora+
          destino_descarga+flota_cex_tc+grade) que impide filas
          operacionales repetidas por diseno. Se mantiene la
          estructura #MovCamClasificado / columna rn para no romper
          la seccion 4, pero todas las filas quedan rn = 1 (ninguna
          se descarta).
       ============================================================ */
    SELECT
        n.*,
        CAST(1 AS bigint) AS rn
    INTO #MovCamClasificado
    FROM #MovCamNormalizado AS n;
    CREATE INDEX IX_MovCamClasificado_Fecha_RN
        ON #MovCamClasificado(Fecha, rn);
    /* ============================================================
       4. Consolidacion diaria de camiones
       ============================================================ */
    ;WITH ConteoOriginal AS
    (
        SELECT
            Fecha,
            COUNT(*) AS Cantidad_Registros_Originales
        FROM #MovCamNormalizado
        GROUP BY Fecha
    ),
    CamionesValidos AS
    (
        SELECT
            Fecha,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'KOM'
                    THEN COALESCE(Tonelaje_Hum_CIO, 0.0)
                    ELSE 0.0
                END
            ) AS Produccion_KOM_TMH,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'CAT'
                    THEN COALESCE(Tonelaje_Hum_CIO, 0.0)
                    ELSE 0.0
                END
            ) AS Produccion_CAT_TMH,
            SUM
            (
                COALESCE(Tonelaje_Hum_CIO, 0.0)
            ) AS Produccion_Total_MovCam,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'KOM'
                    THEN COALESCE(N_BREAK, 0.0)
                    ELSE 0.0
                END
            ) AS Vueltas_KOM,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'CAT'
                    THEN COALESCE(N_BREAK, 0.0)
                    ELSE 0.0
                END
            ) AS Vueltas_CAT,
            COUNT(*) AS Cantidad_Registros_Validos
        FROM #MovCamClasificado
        WHERE rn = 1
        GROUP BY Fecha
    )
    SELECT
        c.Fecha,
        c.Produccion_KOM_TMH,
        c.Produccion_CAT_TMH,
        c.Produccion_Total_MovCam,
        c.Vueltas_KOM,
        c.Vueltas_CAT,
        o.Cantidad_Registros_Originales,
        c.Cantidad_Registros_Validos,
        o.Cantidad_Registros_Originales
        - c.Cantidad_Registros_Validos
            AS Cantidad_Duplicados_Eliminados
    INTO #CamionesDiario
    FROM CamionesValidos AS c
    INNER JOIN ConteoOriginal AS o
        ON o.Fecha = c.Fecha;
    CREATE UNIQUE CLUSTERED INDEX IX_CamionesDiario_Fecha
        ON #CamionesDiario(Fecha);
    /* ============================================================
       5. Base del factor
       ============================================================ */
    SELECT
        b.*,
        COALESCE(c.Produccion_KOM_TMH, 0.0)
            AS Produccion_KOM_TMH,
        COALESCE(c.Produccion_CAT_TMH, 0.0)
            AS Produccion_CAT_TMH,
        COALESCE(c.Vueltas_KOM, 0.0)
            AS Vueltas_KOM,
        COALESCE(c.Vueltas_CAT, 0.0)
            AS Vueltas_CAT,
        COALESCE(c.Produccion_Total_MovCam, 0.0)
            AS Produccion_Total_MovCam,
        COALESCE(c.Cantidad_Registros_Originales, 0)
            AS Cantidad_Registros_Originales,
        COALESCE(c.Cantidad_Registros_Validos, 0)
            AS Cantidad_Registros_Validos,
        COALESCE(c.Cantidad_Duplicados_Eliminados, 0)
            AS Cantidad_Duplicados_Eliminados,
        COALESCE(c.Produccion_KOM_TMH, 0.0)
        + COALESCE(c.Produccion_CAT_TMH, 0.0)
            AS Dato_Mina_TMH,
        COALESCE(c.Produccion_Total_MovCam, 0.0)
        -
        (
            COALESCE(c.Produccion_KOM_TMH, 0.0)
            + COALESCE(c.Produccion_CAT_TMH, 0.0)
        ) AS Check_Produccion_Flotas,
        CASE
            WHEN b.Chancado_TMS_Sin_Ajuste IS NOT NULL
             AND b.Humedad_Inventario >= 0
             AND b.Humedad_Inventario < 100
            THEN
                b.Chancado_TMS_Sin_Ajuste
                /
                NULLIF(
                    1.0 - b.Humedad_Inventario / 100.0,
                    0.0
                )
            ELSE NULL
        END AS Chancado_TMH_Sin_Ajuste
    INTO #FactorBase
    FROM #BaseBalance AS b
    LEFT JOIN #CamionesDiario AS c
        ON c.Fecha = b.Fecha;
    CREATE UNIQUE CLUSTERED INDEX IX_FactorBase_Fecha
        ON #FactorBase(Fecha);
    /* ============================================================
       6. Distribucion del chancado por flota y cargas por vuelta
       ============================================================ */
    SELECT
        f.*,
        CASE
            WHEN f.Dato_Mina_TMH > 0
            THEN
                f.Produccion_KOM_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Participacion_KOM,
        CASE
            WHEN f.Dato_Mina_TMH > 0
            THEN
                f.Produccion_CAT_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Participacion_CAT,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
            THEN
                f.Chancado_TMH_Sin_Ajuste
                * f.Produccion_KOM_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Chancado_KOM_TMH_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
            THEN
                f.Chancado_TMH_Sin_Ajuste
                * f.Produccion_CAT_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Chancado_CAT_TMH_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
             AND f.Produccion_KOM_TMH > 0
             AND f.Vueltas_KOM > 0
            THEN
                (
                    f.Chancado_TMH_Sin_Ajuste
                    * f.Produccion_KOM_TMH
                    / f.Dato_Mina_TMH
                )
                / f.Vueltas_KOM
            ELSE NULL
        END AS Carga_KOM_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
             AND f.Produccion_CAT_TMH > 0
             AND f.Vueltas_CAT > 0
            THEN
                (
                    f.Chancado_TMH_Sin_Ajuste
                    * f.Produccion_CAT_TMH
                    / f.Dato_Mina_TMH
                )
                / f.Vueltas_CAT
            ELSE NULL
        END AS Carga_CAT_Sin_Ajuste
    INTO #FactorCargas
    FROM #FactorBase AS f;
    CREATE UNIQUE CLUSTERED INDEX IX_FactorCargas_Fecha
        ON #FactorCargas(Fecha);
    /* ============================================================
       7. Aplicacion de limites operacionales
       ============================================================ */
    SELECT
        c.*,
        lk.limite AS Limite_KOM_TMH_Viaje,
        lc.limite AS Limite_CAT_TMH_Viaje,
        CASE
            WHEN c.Produccion_KOM_TMH = 0
            THEN 0.0
            WHEN c.Vueltas_KOM <= 0
              OR c.Carga_KOM_Sin_Ajuste IS NULL
            THEN NULL
            WHEN c.Carga_KOM_Sin_Ajuste <= lk.limite
            THEN c.Chancado_KOM_TMH_Sin_Ajuste
            ELSE c.Vueltas_KOM * lk.limite
        END AS KOM_TMH_Corregido,
        CASE
            WHEN c.Produccion_CAT_TMH = 0
            THEN 0.0
            WHEN c.Vueltas_CAT <= 0
              OR c.Carga_CAT_Sin_Ajuste IS NULL
            THEN NULL
            WHEN c.Carga_CAT_Sin_Ajuste <= lc.limite
            THEN c.Chancado_CAT_TMH_Sin_Ajuste
            ELSE c.Vueltas_CAT * lc.limite
        END AS CAT_TMH_Corregido
    INTO #FactorCorregido
    FROM #FactorCargas AS c
    JOIN #LimitesFactorV2 lk ON lk.Fecha=c.Fecha AND lk.flota='KOM'
    JOIN #LimitesFactorV2 lc ON lc.Fecha=c.Fecha AND lc.flota='CAT';
    CREATE UNIQUE CLUSTERED INDEX IX_FactorCorregido_Fecha
        ON #FactorCorregido(Fecha);
    /* ============================================================
       8. Resultado final y estado de evaluacion
       ============================================================ */
    SELECT
        c.Fecha,
        /* Trazabilidad del balance */
        c.Apilado_TMH_Bruto,
        c.Apilado_TMH_Neto,
        c.Sal_Dia,
        c.Humedad_Inventario,
        c.Apilado_TMS_Sin_Ajuste,
        c.Total_Inventario_Chancado_TMS,
        c.Inventario_Chancado_TMS_Anterior,
        c.Delta_Inventario_Chancado_TMS,
        c.SRR_TMS_Dia,
        c.Mineral_Chancado_TMS_Sin_Ajuste,
        c.Chancado_TMS_Sin_Ajuste,
        c.Chancado_TMH_Sin_Ajuste,
        /* Trazabilidad de camiones */
        c.Produccion_KOM_TMH,
        c.Produccion_CAT_TMH,
        c.Dato_Mina_TMH,
        c.Vueltas_KOM,
        c.Vueltas_CAT,
        c.Participacion_KOM,
        c.Participacion_CAT,
        c.Chancado_KOM_TMH_Sin_Ajuste,
        c.Chancado_CAT_TMH_Sin_Ajuste,
        c.Carga_KOM_Sin_Ajuste,
        c.Carga_CAT_Sin_Ajuste,
        c.KOM_TMH_Corregido,
        c.CAT_TMH_Corregido,
        CASE
            WHEN c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
            THEN
                c.KOM_TMH_Corregido
                + c.CAT_TMH_Corregido
            ELSE NULL
        END AS Chancado_TMH_Corregido_Total,
        CASE
            WHEN c.Chancado_TMH_Sin_Ajuste > 0
             AND c.Dato_Mina_TMH > 0
             AND c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
             AND
             (
                 c.Produccion_KOM_TMH = 0
                 OR c.Vueltas_KOM > 0
             )
             AND
             (
                 c.Produccion_CAT_TMH = 0
                 OR c.Vueltas_CAT > 0
             )
             AND ABS(c.Check_Produccion_Flotas) <= 0.001
            THEN
                (
                    c.KOM_TMH_Corregido
                    + c.CAT_TMH_Corregido
                )
                / c.Chancado_TMH_Sin_Ajuste
            ELSE NULL
        END AS Factor_Ajuste_Calculado,
        CASE
            WHEN c.Chancado_TMH_Sin_Ajuste > 0
             AND c.Dato_Mina_TMH > 0
             AND c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
             AND
             (
                 c.Produccion_KOM_TMH = 0
                 OR c.Vueltas_KOM > 0
             )
             AND
             (
                 c.Produccion_CAT_TMH = 0
                 OR c.Vueltas_CAT > 0
             )
             AND ABS(c.Check_Produccion_Flotas) <= 0.001
            THEN 1
            ELSE 0
        END AS Flag_Factor_Ajuste_Valido,
        CASE
            WHEN c.Flag_Humedad_Inventario_Valida <> 1
              OR c.Humedad_Inventario IS NULL
            THEN 'SIN_HUMEDAD'
            WHEN c.Flag_Inventario_Valido <> 1
              OR c.Delta_Inventario_Chancado_TMS IS NULL
            THEN 'SIN_INVENTARIO'
            WHEN c.Chancado_TMH_Sin_Ajuste IS NULL
            THEN 'SIN_BALANCE_CHANCADO'
            WHEN c.Dato_Mina_TMH <= 0
            THEN 'SIN_DATOS_CAMIONES'
            WHEN
            (
                c.Produccion_KOM_TMH > 0
                AND c.Vueltas_KOM <= 0
            )
            OR
            (
                c.Produccion_CAT_TMH > 0
                AND c.Vueltas_CAT <= 0
            )
            THEN 'SIN_VUELTAS'
            WHEN ABS(c.Check_Produccion_Flotas) > 0.001
            THEN 'ERROR_DISTRIBUCION_FLOTAS'
            WHEN c.Carga_KOM_Sin_Ajuste > c.Limite_KOM_TMH_Viaje
             AND c.Carga_CAT_Sin_Ajuste > c.Limite_CAT_TMH_Viaje
            THEN 'OK_AJUSTE_AMBAS_FLOTAS'
            WHEN c.Carga_KOM_Sin_Ajuste > c.Limite_KOM_TMH_Viaje
            THEN 'OK_AJUSTE_KOM'
            WHEN c.Carga_CAT_Sin_Ajuste > c.Limite_CAT_TMH_Viaje
            THEN 'OK_AJUSTE_CAT'
            ELSE 'OK_SIN_AJUSTE'
        END AS Estado_Calculo,
        /* Control de duplicados */
        c.Cantidad_Registros_Originales,
        c.Cantidad_Registros_Validos,
        c.Cantidad_Duplicados_Eliminados,
        c.Check_TMH_Bruto,
        c.Check_Produccion_Flotas,
        c.Flag_Continuidad_Diaria,
        c.Flag_Inventario_Valido,
        c.Flag_Humedad_Inventario_Valida,
        c.Limite_KOM_TMH_Viaje,
        c.Limite_CAT_TMH_Viaje
    FROM #FactorCorregido AS c
    ORDER BY c.Fecha;
END;
GO


CREATE OR ALTER PROCEDURE [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_test]
(
    @FechaInicio   date,
    @FechaFin      date,
    @DiasReproceso int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    /* ============================================================
       0. Validaciones
       ============================================================ */

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;

    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;

    IF @DiasReproceso IS NULL OR @DiasReproceso < 0
        THROW 50003, '@DiasReproceso debe ser mayor o igual que cero.', 1;

    IF OBJECT_ID
    (
        '[inventar_SpcHidr].[Control_Factor_Ajuste_Camiones_v2_test]',
        'U'
    ) IS NULL
        THROW 50004,
              'No existe la tabla Control_Factor_Ajuste_Camiones_v2_test.',
              1;

    DECLARE @FechaInicioProceso date =
        CASE
            WHEN DATEADD(DAY, -@DiasReproceso, @FechaFin) < @FechaInicio
                THEN DATEADD(DAY, -@DiasReproceso, @FechaFin)
            ELSE @FechaInicio
        END;

    DECLARE @FechaCalculo datetime2(7) = SYSDATETIME();


    /* ============================================================
       1. Capturar la salida del cálculo validado
       ============================================================ */

    IF OBJECT_ID('tempdb..#CalculoFactorV2') IS NOT NULL
        DROP TABLE #CalculoFactorV2;

    CREATE TABLE #CalculoFactorV2
    (
        Fecha date NOT NULL,

        Apilado_TMH_Bruto float NULL,
        Apilado_TMH_Neto float NULL,
        Sal_Dia float NULL,
        Humedad_Inventario float NULL,

        Apilado_TMS_Sin_Ajuste float NULL,

        Total_Inventario_Chancado_TMS float NULL,
        Inventario_Chancado_TMS_Anterior float NULL,
        Delta_Inventario_Chancado_TMS float NULL,

        SRR_TMS_Dia float NULL,

        Mineral_Chancado_TMS_Sin_Ajuste float NULL,
        Chancado_TMS_Sin_Ajuste float NULL,
        Chancado_TMH_Sin_Ajuste float NULL,

        Produccion_KOM_TMH float NULL,
        Produccion_CAT_TMH float NULL,
        Dato_Mina_TMH float NULL,

        Vueltas_KOM float NULL,
        Vueltas_CAT float NULL,

        Participacion_KOM float NULL,
        Participacion_CAT float NULL,

        Chancado_KOM_TMH_Sin_Ajuste float NULL,
        Chancado_CAT_TMH_Sin_Ajuste float NULL,

        Carga_KOM_Sin_Ajuste float NULL,
        Carga_CAT_Sin_Ajuste float NULL,

        KOM_TMH_Corregido float NULL,
        CAT_TMH_Corregido float NULL,
        Chancado_TMH_Corregido_Total float NULL,

        Factor_Ajuste_Calculado float NULL,
        Flag_Factor_Ajuste_Valido bit NULL,
        Estado_Calculo varchar(40) NULL,

        Cantidad_Registros_Originales int NULL,
        Cantidad_Registros_Validos int NULL,
        Cantidad_Duplicados_Eliminados int NULL,

        Check_TMH_Bruto float NULL,
        Check_Produccion_Flotas float NULL,

        Flag_Continuidad_Diaria bit NULL,
        Flag_Inventario_Valido bit NULL,
        Flag_Humedad_Inventario_Valida bit NULL,
        Limite_KOM_TMH_Viaje float NOT NULL,
        Limite_CAT_TMH_Viaje float NOT NULL
    );

    INSERT INTO #CalculoFactorV2
    EXEC [inventar_SpcHidr].[sp_factor_ajuste_camiones_test]
        @FechaInicio = @FechaInicioProceso,
        @FechaFin    = @FechaFin;

    CREATE UNIQUE CLUSTERED INDEX IX_CalculoFactorV2_Fecha
        ON #CalculoFactorV2(Fecha);


    /* ============================================================
       2. Recuperar SRR por turno para trazabilidad
       ============================================================ */

    IF OBJECT_ID('tempdb..#SRRTurnos') IS NOT NULL
        DROP TABLE #SRRTurnos;

    SELECT
        s.Fecha,
        SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'A' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_A,
        SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'B' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_B
    INTO #SRRTurnos
    FROM [inventar_SpcHidr].[v_srr_tms_origen_turno_emision_test] AS s
    WHERE s.Fecha BETWEEN @FechaInicioProceso AND @FechaFin
    GROUP BY s.Fecha;

    CREATE UNIQUE CLUSTERED INDEX IX_SRRTurnos_Fecha
        ON #SRRTurnos(Fecha);


    /* ============================================================
       3. Construir fuente persistible

       Si el factor no es válido:
       - Factor_Ajuste queda NULL.
       - Los valores ajustados quedan NULL.
       - Los reportes decidirán posteriormente si aplican fallback
         hacia el valor basal.
       ============================================================ */

    IF OBJECT_ID('tempdb..#FuenteFactorV2') IS NOT NULL
        DROP TABLE #FuenteFactorV2;

    ;WITH Base AS
    (
        SELECT
            c.*,

            COALESCE(s.SRR_TMS_Turno_A, 0.0)
                AS SRR_TMS_Turno_A,

            COALESCE(s.SRR_TMS_Turno_B, 0.0)
                AS SRR_TMS_Turno_B,

            CASE
                WHEN c.Humedad_Inventario >= 0
                 AND c.Humedad_Inventario < 100
                    THEN 1.0 - c.Humedad_Inventario / 100.0
                ELSE NULL
            END AS Factor_Seco

        FROM #CalculoFactorV2 AS c

        LEFT JOIN #SRRTurnos AS s
            ON s.Fecha = c.Fecha
    ),

    AjusteTMH AS
    (
        SELECT
            b.*,

            CASE
                WHEN b.Flag_Factor_Ajuste_Valido = 1
                 AND b.Factor_Ajuste_Calculado IS NOT NULL
                THEN
                    b.Apilado_TMH_Bruto
                    * b.Factor_Ajuste_Calculado
                ELSE NULL
            END AS Apilado_TMH_Bruto_Ajustado,

            CASE
                WHEN b.Flag_Factor_Ajuste_Valido = 1
                 AND b.Factor_Ajuste_Calculado IS NOT NULL
                 AND b.Sal_Dia IS NOT NULL
                THEN
                    (
                        b.Apilado_TMH_Bruto
                        * b.Factor_Ajuste_Calculado
                    )
                    - b.Sal_Dia
                ELSE NULL
            END AS Apilado_TMH_Neto_Ajustado,

            CASE
    WHEN b.Apilado_TMS_Sin_Ajuste IS NOT NULL
     AND b.Sal_Dia IS NOT NULL
    THEN
        b.Apilado_TMS_Sin_Ajuste
        - b.Sal_Dia
    ELSE NULL
END AS Apilado_TMS_Neto_Sin_Ajuste

        FROM Base AS b
    ),

    AjusteTMS AS
    (
        SELECT
            a.*,

            CASE
                WHEN a.Apilado_TMH_Bruto_Ajustado IS NOT NULL
                 AND a.Factor_Seco IS NOT NULL
                THEN
                    a.Apilado_TMH_Bruto_Ajustado
                    * a.Factor_Seco
                ELSE NULL
            END AS Apilado_TMS_Bruto_Ajustado,

           CASE
    WHEN a.Apilado_TMH_Bruto_Ajustado IS NOT NULL
     AND a.Factor_Seco IS NOT NULL
     AND a.Sal_Dia IS NOT NULL
    THEN
        (
            a.Apilado_TMH_Bruto_Ajustado
            * a.Factor_Seco
        )
        - a.Sal_Dia
    ELSE NULL
END AS Apilado_TMS_Neto_Ajustado

        FROM AjusteTMH AS a
    ),

    BalanceAjustado AS
    (
        SELECT
            a.*,

            CASE
                WHEN a.Apilado_TMS_Bruto_Ajustado IS NOT NULL
                 AND a.Delta_Inventario_Chancado_TMS IS NOT NULL
                THEN
                    a.Apilado_TMS_Bruto_Ajustado
                    + a.Delta_Inventario_Chancado_TMS
                ELSE NULL
            END AS Mineral_Chancado_TMS_Ajustado

        FROM AjusteTMS AS a
    )

    SELECT
        b.Fecha,

        b.Limite_KOM_TMH_Viaje,
        b.Limite_CAT_TMH_Viaje,

        b.Apilado_TMH_Bruto
            AS Apilado_TMH_Bruto_Original,

        b.Apilado_TMH_Neto
            AS Apilado_TMH_Neto_Original,

        b.Sal_Dia
            AS Sal_TMH_Dia,

        b.Humedad_Inventario
            AS Humedad_Pct,

        b.Apilado_TMS_Sin_Ajuste
            AS Apilado_TMS_Bruto_Sin_Ajuste,

        b.Apilado_TMS_Neto_Sin_Ajuste,

        b.Total_Inventario_Chancado_TMS
            AS Inventario_Chancado_TMS_Actual,

        b.Inventario_Chancado_TMS_Anterior,
        b.Delta_Inventario_Chancado_TMS,

        b.Flag_Continuidad_Diaria,
        b.Flag_Inventario_Valido,

        b.Flag_Humedad_Inventario_Valida
            AS Flag_Humedad_Valida,

        b.SRR_TMS_Turno_A,
        b.SRR_TMS_Turno_B,
        b.SRR_TMS_Dia,

        b.Mineral_Chancado_TMS_Sin_Ajuste,
        b.Chancado_TMS_Sin_Ajuste,
        b.Chancado_TMH_Sin_Ajuste,

        b.Produccion_KOM_TMH,
        b.Produccion_CAT_TMH,
        b.Dato_Mina_TMH,

        b.Vueltas_KOM,
        b.Vueltas_CAT,

        b.Participacion_KOM,
        b.Participacion_CAT,

        b.Chancado_KOM_TMH_Sin_Ajuste,
        b.Chancado_CAT_TMH_Sin_Ajuste,

        b.Carga_KOM_Sin_Ajuste
            AS Carga_KOM_TMH_Viaje_Sin_Ajuste,

        b.Carga_CAT_Sin_Ajuste
            AS Carga_CAT_TMH_Viaje_Sin_Ajuste,

        b.KOM_TMH_Corregido,
        b.CAT_TMH_Corregido,
        b.Chancado_TMH_Corregido_Total,

        CASE
            WHEN b.Flag_Factor_Ajuste_Valido = 1
                THEN b.Factor_Ajuste_Calculado
            ELSE NULL
        END AS Factor_Ajuste,

        b.Flag_Factor_Ajuste_Valido,
        b.Estado_Calculo,

        b.Apilado_TMH_Bruto_Ajustado,
        b.Apilado_TMS_Bruto_Ajustado,

        b.Mineral_Chancado_TMS_Ajustado,

        CASE
            WHEN b.Mineral_Chancado_TMS_Ajustado IS NOT NULL
             AND b.Sal_Dia IS NOT NULL
             AND b.SRR_TMS_Dia IS NOT NULL
            THEN
                b.Mineral_Chancado_TMS_Ajustado
                - b.Sal_Dia
                - b.SRR_TMS_Dia
            ELSE NULL
        END AS Chancado_TMS_Ajustado,

        b.Apilado_TMH_Neto_Ajustado,
        b.Apilado_TMS_Neto_Ajustado,

        b.Cantidad_Registros_Originales,
        b.Cantidad_Registros_Validos,
        b.Cantidad_Duplicados_Eliminados,

        b.Check_TMH_Bruto,
        b.Check_Produccion_Flotas,

        CAST('BALANCE_INVENTARIO_CAMIONES_V2' AS varchar(100))
            AS Metodo,

        CAST('MOV_CAM_DEDUP_OPERACIONAL' AS varchar(100))
            AS Fuente_Camiones,

        @FechaCalculo AS Fecha_Calculo

    INTO #FuenteFactorV2

    FROM BalanceAjustado AS b;

    CREATE UNIQUE CLUSTERED INDEX IX_FuenteFactorV2_Fecha
        ON #FuenteFactorV2(Fecha);


    /* ============================================================
       4. Persistencia en tabla V2
       ============================================================ */

    MERGE
        [inventar_SpcHidr].[Control_Factor_Ajuste_Camiones_v2_test]
        WITH (HOLDLOCK) AS tgt

    USING #FuenteFactorV2 AS src
        ON tgt.Fecha = src.Fecha

    WHEN MATCHED THEN
        UPDATE SET
            Limite_KOM_TMH_Viaje =
                src.Limite_KOM_TMH_Viaje,

            Limite_CAT_TMH_Viaje =
                src.Limite_CAT_TMH_Viaje,

            Apilado_TMH_Bruto_Original =
                src.Apilado_TMH_Bruto_Original,

            Apilado_TMH_Neto_Original =
                src.Apilado_TMH_Neto_Original,

            Sal_TMH_Dia =
                src.Sal_TMH_Dia,

            Humedad_Pct =
                src.Humedad_Pct,

            Apilado_TMS_Bruto_Sin_Ajuste =
                src.Apilado_TMS_Bruto_Sin_Ajuste,

            Apilado_TMS_Neto_Sin_Ajuste =
                src.Apilado_TMS_Neto_Sin_Ajuste,

            Inventario_Chancado_TMS_Actual =
                src.Inventario_Chancado_TMS_Actual,

            Inventario_Chancado_TMS_Anterior =
                src.Inventario_Chancado_TMS_Anterior,

            Delta_Inventario_Chancado_TMS =
                src.Delta_Inventario_Chancado_TMS,

            Flag_Continuidad_Diaria =
                src.Flag_Continuidad_Diaria,

            Flag_Inventario_Valido =
                src.Flag_Inventario_Valido,

            Flag_Humedad_Valida =
                src.Flag_Humedad_Valida,

            SRR_TMS_Turno_A =
                src.SRR_TMS_Turno_A,

            SRR_TMS_Turno_B =
                src.SRR_TMS_Turno_B,

            SRR_TMS_Dia =
                src.SRR_TMS_Dia,

            Mineral_Chancado_TMS_Sin_Ajuste =
                src.Mineral_Chancado_TMS_Sin_Ajuste,

            Chancado_TMS_Sin_Ajuste =
                src.Chancado_TMS_Sin_Ajuste,

            Chancado_TMH_Sin_Ajuste =
                src.Chancado_TMH_Sin_Ajuste,

            Produccion_KOM_TMH =
                src.Produccion_KOM_TMH,

            Produccion_CAT_TMH =
                src.Produccion_CAT_TMH,

            Dato_Mina_TMH =
                src.Dato_Mina_TMH,

            Vueltas_KOM =
                src.Vueltas_KOM,

            Vueltas_CAT =
                src.Vueltas_CAT,

            Participacion_KOM =
                src.Participacion_KOM,

            Participacion_CAT =
                src.Participacion_CAT,

            Chancado_KOM_TMH_Sin_Ajuste =
                src.Chancado_KOM_TMH_Sin_Ajuste,

            Chancado_CAT_TMH_Sin_Ajuste =
                src.Chancado_CAT_TMH_Sin_Ajuste,

            Carga_KOM_TMH_Viaje_Sin_Ajuste =
                src.Carga_KOM_TMH_Viaje_Sin_Ajuste,

            Carga_CAT_TMH_Viaje_Sin_Ajuste =
                src.Carga_CAT_TMH_Viaje_Sin_Ajuste,

            KOM_TMH_Corregido =
                src.KOM_TMH_Corregido,

            CAT_TMH_Corregido =
                src.CAT_TMH_Corregido,

            Chancado_TMH_Corregido_Total =
                src.Chancado_TMH_Corregido_Total,

            Factor_Ajuste =
                src.Factor_Ajuste,

            Flag_Factor_Ajuste_Valido =
                src.Flag_Factor_Ajuste_Valido,

            Estado_Calculo =
                src.Estado_Calculo,

            Apilado_TMH_Bruto_Ajustado =
                src.Apilado_TMH_Bruto_Ajustado,

            Apilado_TMS_Bruto_Ajustado =
                src.Apilado_TMS_Bruto_Ajustado,

            Mineral_Chancado_TMS_Ajustado =
                src.Mineral_Chancado_TMS_Ajustado,

            Chancado_TMS_Ajustado =
                src.Chancado_TMS_Ajustado,

            Apilado_TMH_Neto_Ajustado =
                src.Apilado_TMH_Neto_Ajustado,

            Apilado_TMS_Neto_Ajustado =
                src.Apilado_TMS_Neto_Ajustado,

            Cantidad_Registros_Originales =
                src.Cantidad_Registros_Originales,

            Cantidad_Registros_Validos =
                src.Cantidad_Registros_Validos,

            Cantidad_Duplicados_Eliminados =
                src.Cantidad_Duplicados_Eliminados,

            Check_TMH_Bruto =
                src.Check_TMH_Bruto,

            Check_Produccion_Flotas =
                src.Check_Produccion_Flotas,

            Metodo =
                src.Metodo,

            Fuente_Camiones =
                src.Fuente_Camiones,

            Fecha_Calculo =
                src.Fecha_Calculo

    WHEN NOT MATCHED BY TARGET THEN
        INSERT
        (
            Fecha,

            Limite_KOM_TMH_Viaje,
            Limite_CAT_TMH_Viaje,

            Apilado_TMH_Bruto_Original,
            Apilado_TMH_Neto_Original,
            Sal_TMH_Dia,
            Humedad_Pct,

            Apilado_TMS_Bruto_Sin_Ajuste,
            Apilado_TMS_Neto_Sin_Ajuste,

            Inventario_Chancado_TMS_Actual,
            Inventario_Chancado_TMS_Anterior,
            Delta_Inventario_Chancado_TMS,

            Flag_Continuidad_Diaria,
            Flag_Inventario_Valido,
            Flag_Humedad_Valida,

            SRR_TMS_Turno_A,
            SRR_TMS_Turno_B,
            SRR_TMS_Dia,

            Mineral_Chancado_TMS_Sin_Ajuste,
            Chancado_TMS_Sin_Ajuste,
            Chancado_TMH_Sin_Ajuste,

            Produccion_KOM_TMH,
            Produccion_CAT_TMH,
            Dato_Mina_TMH,

            Vueltas_KOM,
            Vueltas_CAT,

            Participacion_KOM,
            Participacion_CAT,

            Chancado_KOM_TMH_Sin_Ajuste,
            Chancado_CAT_TMH_Sin_Ajuste,

            Carga_KOM_TMH_Viaje_Sin_Ajuste,
            Carga_CAT_TMH_Viaje_Sin_Ajuste,

            KOM_TMH_Corregido,
            CAT_TMH_Corregido,
            Chancado_TMH_Corregido_Total,

            Factor_Ajuste,
            Flag_Factor_Ajuste_Valido,
            Estado_Calculo,

            Apilado_TMH_Bruto_Ajustado,
            Apilado_TMS_Bruto_Ajustado,

            Mineral_Chancado_TMS_Ajustado,
            Chancado_TMS_Ajustado,

            Apilado_TMH_Neto_Ajustado,
            Apilado_TMS_Neto_Ajustado,

            Cantidad_Registros_Originales,
            Cantidad_Registros_Validos,
            Cantidad_Duplicados_Eliminados,

            Check_TMH_Bruto,
            Check_Produccion_Flotas,

            Metodo,
            Fuente_Camiones,
            Fecha_Calculo
        )
        VALUES
        (
            src.Fecha,

            src.Limite_KOM_TMH_Viaje,
            src.Limite_CAT_TMH_Viaje,

            src.Apilado_TMH_Bruto_Original,
            src.Apilado_TMH_Neto_Original,
            src.Sal_TMH_Dia,
            src.Humedad_Pct,

            src.Apilado_TMS_Bruto_Sin_Ajuste,
            src.Apilado_TMS_Neto_Sin_Ajuste,

            src.Inventario_Chancado_TMS_Actual,
            src.Inventario_Chancado_TMS_Anterior,
            src.Delta_Inventario_Chancado_TMS,

            src.Flag_Continuidad_Diaria,
            src.Flag_Inventario_Valido,
            src.Flag_Humedad_Valida,

            src.SRR_TMS_Turno_A,
            src.SRR_TMS_Turno_B,
            src.SRR_TMS_Dia,

            src.Mineral_Chancado_TMS_Sin_Ajuste,
            src.Chancado_TMS_Sin_Ajuste,
            src.Chancado_TMH_Sin_Ajuste,

            src.Produccion_KOM_TMH,
            src.Produccion_CAT_TMH,
            src.Dato_Mina_TMH,

            src.Vueltas_KOM,
            src.Vueltas_CAT,

            src.Participacion_KOM,
            src.Participacion_CAT,

            src.Chancado_KOM_TMH_Sin_Ajuste,
            src.Chancado_CAT_TMH_Sin_Ajuste,

            src.Carga_KOM_TMH_Viaje_Sin_Ajuste,
            src.Carga_CAT_TMH_Viaje_Sin_Ajuste,

            src.KOM_TMH_Corregido,
            src.CAT_TMH_Corregido,
            src.Chancado_TMH_Corregido_Total,

            src.Factor_Ajuste,
            src.Flag_Factor_Ajuste_Valido,
            src.Estado_Calculo,

            src.Apilado_TMH_Bruto_Ajustado,
            src.Apilado_TMS_Bruto_Ajustado,

            src.Mineral_Chancado_TMS_Ajustado,
            src.Chancado_TMS_Ajustado,

            src.Apilado_TMH_Neto_Ajustado,
            src.Apilado_TMS_Neto_Ajustado,

            src.Cantidad_Registros_Originales,
            src.Cantidad_Registros_Validos,
            src.Cantidad_Duplicados_Eliminados,

            src.Check_TMH_Bruto,
            src.Check_Produccion_Flotas,

            src.Metodo,
            src.Fuente_Camiones,
            src.Fecha_Calculo
        );

    DECLARE @FilasAfectadas int = @@ROWCOUNT;

    PRINT 'Proceso V2 finalizado.';
    PRINT 'Rango procesado: '
        + CONVERT(varchar(10), @FechaInicioProceso, 120)
        + ' a '
        + CONVERT(varchar(10), @FechaFin, 120);

    PRINT 'Filas insertadas/actualizadas: '
        + CONVERT(varchar(20), @FilasAfectadas);
END;

GO

CREATE OR ALTER PROCEDURE [inventar_SpcHidr].[sp_factor_ajuste_camiones_standalone_test]
    @FechaInicio date,
    @FechaFin    date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF @FechaInicio IS NULL OR @FechaFin IS NULL
    BEGIN
        THROW 50001, 'FechaInicio y FechaFin son obligatorias.', 1;
    END;
    IF @FechaInicio > @FechaFin
    BEGIN
        THROW 50002, 'FechaInicio no puede ser mayor que FechaFin.', 1;
    END;
    /* ============================================================
       1. SRR diario desde el reporte por turno
       ============================================================ */

    -- FASE 2A: una copia consistente de las vigencias, nunca valores de respaldo.
    -- HOLDLOCK protege la lectura completa frente al registro transaccional.
    SELECT flota,parametro,valor,vigencia_desde,vigencia_hasta
    INTO #ParametrosFactorV2
    FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (HOLDLOCK)
    WHERE activo=1 AND parametro='LIMITE_CARGA_AJUSTE';
    ;WITH Dias AS (
        SELECT @FechaInicio AS Fecha
        UNION ALL SELECT DATEADD(day,1,Fecha) FROM Dias WHERE Fecha<@FechaFin
    )
    SELECT d.Fecha,f.flota,COUNT(p.flota) AS cantidad,CAST(MIN(p.valor) AS float) AS limite
    INTO #LimitesFactorV2
    FROM Dias d CROSS JOIN (VALUES ('KOM'),('CAT')) f(flota)
    LEFT JOIN #ParametrosFactorV2 p ON p.flota=f.flota AND p.vigencia_desde<=d.Fecha
        AND (p.vigencia_hasta IS NULL OR d.Fecha<p.vigencia_hasta)
    GROUP BY d.Fecha,f.flota OPTION (MAXRECURSION 0);
    DECLARE @ErrorLimite nvarchar(2048);
    SELECT TOP(1) @ErrorLimite=CONCAT(
        CASE WHEN cantidad=0 THEN 'No existe limite vigente ' ELSE 'Existen multiples limites vigentes ' END,
        flota,' para ',CONVERT(varchar(10),Fecha,23),'.')
    FROM #LimitesFactorV2 WHERE cantidad<>1 ORDER BY Fecha,flota;
    IF @ErrorLimite IS NOT NULL THROW 51020,@ErrorLimite,1;
    CREATE UNIQUE CLUSTERED INDEX IX_LimitesFactorV2 ON #LimitesFactorV2(Fecha,flota);

    ;WITH SRR_Diario AS
    (
        SELECT
            s.Fecha,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'A' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_A,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'B' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_B,
            SUM(COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0)) AS SRR_TMS_Dia,
            COUNT(*) AS Cantidad_Registros_SRR
        FROM [inventar_SpcHidr].[v_srr_tms_origen_turno_standalone_test] AS s
        WHERE s.Fecha BETWEEN @FechaInicio AND @FechaFin
        GROUP BY s.Fecha
    ),
    Base AS
    (
        SELECT
            i.Fecha,
            TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
                AS Apilado_TMH_Neto,
            TRY_CONVERT(float, a.Sal_promedio_dia)
                AS Sal_Dia,
            TRY_CONVERT(float, a.TMH_Bruto_Dia)
                AS Apilado_TMH_Bruto,
            TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
            + TRY_CONVERT(float, a.Sal_promedio_dia)
                AS Apilado_TMH_Bruto_Reconstruido,
            TRY_CONVERT(float, a.TMH_Bruto_Dia)
            -
            (
                TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
                + TRY_CONVERT(float, a.Sal_promedio_dia)
            ) AS Check_TMH_Bruto,
            h.Humedad_Inventario,
            h.Regla_Humedad_Inventario,
            h.Flag_Humedad_Inventario_Valida,
            i.Total_Inventario_Chancado_TMS,
            i.Inventario_Chancado_TMS_Anterior,
            i.Delta_Inventario_Chancado_TMS,
            i.Flag_Continuidad_Diaria,
            i.Flag_Inventario_Valido,
            COALESCE(s.SRR_TMS_Turno_A, 0.0)
                AS SRR_TMS_Turno_A,
            COALESCE(s.SRR_TMS_Turno_B, 0.0)
                AS SRR_TMS_Turno_B,
            COALESCE(s.SRR_TMS_Dia, 0.0)
                AS SRR_TMS_Dia,
            COALESCE(s.Cantidad_Registros_SRR, 0)
                AS Cantidad_Registros_SRR
        FROM [inventar_SpcHidr].[v_inventario_chancado_test] AS i
        LEFT JOIN [inventar_SpcHidr].[Historico_Apilado_Diario] AS a
            ON CAST(a.Fecha AS date) = i.Fecha
        LEFT JOIN [inventar_SpcHidr].[v_humedad_inventario_test] AS h
            ON h.Fecha = i.Fecha
        LEFT JOIN SRR_Diario AS s
            ON s.Fecha = i.Fecha
        WHERE i.Fecha BETWEEN @FechaInicio AND @FechaFin
    ),
    CalculoSinAjuste AS
    (
        SELECT
            b.*,
            CASE
                WHEN b.Apilado_TMH_Bruto IS NOT NULL
                 AND b.Flag_Humedad_Inventario_Valida = 1
                THEN
                    b.Apilado_TMH_Bruto
                    *
                    (
                        1.0
                        - b.Humedad_Inventario / 100.0
                    )
                ELSE NULL
            END AS Apilado_TMS_Sin_Ajuste
        FROM Base AS b
    ),
    MineralSinAjuste AS
    (
        SELECT
            c.*,
            CASE
                WHEN c.Apilado_TMS_Sin_Ajuste IS NOT NULL
                 AND c.Flag_Inventario_Valido = 1
                 AND c.Delta_Inventario_Chancado_TMS IS NOT NULL
                THEN
                    c.Apilado_TMS_Sin_Ajuste
                    + c.Delta_Inventario_Chancado_TMS
                ELSE NULL
            END AS Mineral_Chancado_TMS_Sin_Ajuste
        FROM CalculoSinAjuste AS c
    ),
    ChancadoSinAjuste AS
    (
        SELECT
            m.*,
            CASE
                WHEN m.Mineral_Chancado_TMS_Sin_Ajuste IS NOT NULL
                 AND m.Sal_Dia IS NOT NULL
                 AND m.SRR_TMS_Dia IS NOT NULL
                THEN
                    m.Mineral_Chancado_TMS_Sin_Ajuste
                    - m.Sal_Dia
                    - m.SRR_TMS_Dia
                ELSE NULL
            END AS Chancado_TMS_Sin_Ajuste
        FROM MineralSinAjuste AS m
    )
    SELECT
        Fecha,
        Apilado_TMH_Neto,
        Sal_Dia,
        Apilado_TMH_Bruto,
        Apilado_TMH_Bruto_Reconstruido,
        Check_TMH_Bruto,
        Humedad_Inventario,
        Regla_Humedad_Inventario,
        Flag_Humedad_Inventario_Valida,
        Total_Inventario_Chancado_TMS,
        Inventario_Chancado_TMS_Anterior,
        Delta_Inventario_Chancado_TMS,
        Flag_Continuidad_Diaria,
        Flag_Inventario_Valido,
        SRR_TMS_Turno_A,
        SRR_TMS_Turno_B,
        SRR_TMS_Dia,
        Cantidad_Registros_SRR,
        Apilado_TMS_Sin_Ajuste,
        Mineral_Chancado_TMS_Sin_Ajuste,
        Chancado_TMS_Sin_Ajuste
    INTO #BaseBalance
    FROM ChancadoSinAjuste;
    CREATE UNIQUE CLUSTERED INDEX IX_BaseBalance_Fecha
        ON #BaseBalance(Fecha);
    /* ============================================================
       2. Normalizacion de movimientos de camiones -- FUENTE NUEVA:
          inventar_SpcHidr.mov_cam_powerbi (antes mov_cam). Ver mapeo
          de columnas en el encabezado de este script.
       ============================================================ */
    SELECT
        m.fecha AS Fecha,
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(50), m.turno)
            ))
        ) AS Turno,
        CAST(NULL AS nvarchar(255)) AS Origen,          -- sin equivalente en mov_cam_powerbi
        CAST(NULL AS nvarchar(500)) AS Solido,          -- sin equivalente en mov_cam_powerbi
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.fase)
            ))
        ) AS Fase,
        LTRIM(RTRIM(
            CONVERT(nvarchar(100), m.banco)
        )) AS Banco,
        LTRIM(RTRIM(
            CONVERT(nvarchar(100), m.excavadora)
        )) AS Pala,
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.destino_descarga)
            ))
        ) AS Destino,
        CAST(NULL AS nvarchar(500)) AS Poligono_CIO,    -- sin equivalente en mov_cam_powerbi
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.flota_cex_tc)
            ))
        ) AS Flota_CEX,
        TRY_CONVERT(float, m.tonelaje_descarga_tms)
            AS Ton,
        TRY_CONVERT(float, m.n_break)
            AS N_BREAK,
        CAST(NULL AS float) AS Ton_Hum_Diseno_CAEX,     -- sin equivalente en mov_cam_powerbi
        TRY_CONVERT(float, m.ton_descarga)
            AS Tonelaje_Hum_CIO,                        -- validado: ton_descarga = tonelada humeda
        TRY_CONVERT(float, m.tonelaje_descarga_tms)
            AS Tonelaje_Seco_CIO,
        CAST(NULL AS float) AS PONDHumedad,             -- sin equivalente en mov_cam_powerbi
        CAST(NULL AS int) AS mov_id,                    -- mov_cam_powerbi no tiene este concepto
        m.id AS ID
    INTO #MovCamNormalizado
    FROM [inventar_SpcHidr].[mov_cam_powerbi] AS m
    WHERE m.fecha BETWEEN @FechaInicio AND @FechaFin
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.destino_descarga)
              ))
          ) = 'CH01'
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.fase)
              ))
          ) <> 'SRR'
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.flota_cex_tc)
              ))
          ) IN ('KOM', 'CAT');
    CREATE INDEX IX_MovCamNormalizado_Fecha
        ON #MovCamNormalizado(Fecha);
    /* ============================================================
       3. Deduplicacion -- YA NO APLICA con mov_cam_powerbi.
          La tabla tiene un indice unico de 9 columnas
          (fecha+turno+tipo_movimiento+fase+banco+excavadora+
          destino_descarga+flota_cex_tc+grade) que impide filas
          operacionales repetidas por diseno. Se mantiene la
          estructura #MovCamClasificado / columna rn para no romper
          la seccion 4, pero todas las filas quedan rn = 1 (ninguna
          se descarta).
       ============================================================ */
    SELECT
        n.*,
        CAST(1 AS bigint) AS rn
    INTO #MovCamClasificado
    FROM #MovCamNormalizado AS n;
    CREATE INDEX IX_MovCamClasificado_Fecha_RN
        ON #MovCamClasificado(Fecha, rn);
    /* ============================================================
       4. Consolidacion diaria de camiones
       ============================================================ */
    ;WITH ConteoOriginal AS
    (
        SELECT
            Fecha,
            COUNT(*) AS Cantidad_Registros_Originales
        FROM #MovCamNormalizado
        GROUP BY Fecha
    ),
    CamionesValidos AS
    (
        SELECT
            Fecha,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'KOM'
                    THEN COALESCE(Tonelaje_Hum_CIO, 0.0)
                    ELSE 0.0
                END
            ) AS Produccion_KOM_TMH,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'CAT'
                    THEN COALESCE(Tonelaje_Hum_CIO, 0.0)
                    ELSE 0.0
                END
            ) AS Produccion_CAT_TMH,
            SUM
            (
                COALESCE(Tonelaje_Hum_CIO, 0.0)
            ) AS Produccion_Total_MovCam,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'KOM'
                    THEN COALESCE(N_BREAK, 0.0)
                    ELSE 0.0
                END
            ) AS Vueltas_KOM,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'CAT'
                    THEN COALESCE(N_BREAK, 0.0)
                    ELSE 0.0
                END
            ) AS Vueltas_CAT,
            COUNT(*) AS Cantidad_Registros_Validos
        FROM #MovCamClasificado
        WHERE rn = 1
        GROUP BY Fecha
    )
    SELECT
        c.Fecha,
        c.Produccion_KOM_TMH,
        c.Produccion_CAT_TMH,
        c.Produccion_Total_MovCam,
        c.Vueltas_KOM,
        c.Vueltas_CAT,
        o.Cantidad_Registros_Originales,
        c.Cantidad_Registros_Validos,
        o.Cantidad_Registros_Originales
        - c.Cantidad_Registros_Validos
            AS Cantidad_Duplicados_Eliminados
    INTO #CamionesDiario
    FROM CamionesValidos AS c
    INNER JOIN ConteoOriginal AS o
        ON o.Fecha = c.Fecha;
    CREATE UNIQUE CLUSTERED INDEX IX_CamionesDiario_Fecha
        ON #CamionesDiario(Fecha);
    /* ============================================================
       5. Base del factor
       ============================================================ */
    SELECT
        b.*,
        COALESCE(c.Produccion_KOM_TMH, 0.0)
            AS Produccion_KOM_TMH,
        COALESCE(c.Produccion_CAT_TMH, 0.0)
            AS Produccion_CAT_TMH,
        COALESCE(c.Vueltas_KOM, 0.0)
            AS Vueltas_KOM,
        COALESCE(c.Vueltas_CAT, 0.0)
            AS Vueltas_CAT,
        COALESCE(c.Produccion_Total_MovCam, 0.0)
            AS Produccion_Total_MovCam,
        COALESCE(c.Cantidad_Registros_Originales, 0)
            AS Cantidad_Registros_Originales,
        COALESCE(c.Cantidad_Registros_Validos, 0)
            AS Cantidad_Registros_Validos,
        COALESCE(c.Cantidad_Duplicados_Eliminados, 0)
            AS Cantidad_Duplicados_Eliminados,
        COALESCE(c.Produccion_KOM_TMH, 0.0)
        + COALESCE(c.Produccion_CAT_TMH, 0.0)
            AS Dato_Mina_TMH,
        COALESCE(c.Produccion_Total_MovCam, 0.0)
        -
        (
            COALESCE(c.Produccion_KOM_TMH, 0.0)
            + COALESCE(c.Produccion_CAT_TMH, 0.0)
        ) AS Check_Produccion_Flotas,
        CASE
            WHEN b.Chancado_TMS_Sin_Ajuste IS NOT NULL
             AND b.Humedad_Inventario >= 0
             AND b.Humedad_Inventario < 100
            THEN
                b.Chancado_TMS_Sin_Ajuste
                /
                NULLIF(
                    1.0 - b.Humedad_Inventario / 100.0,
                    0.0
                )
            ELSE NULL
        END AS Chancado_TMH_Sin_Ajuste
    INTO #FactorBase
    FROM #BaseBalance AS b
    LEFT JOIN #CamionesDiario AS c
        ON c.Fecha = b.Fecha;
    CREATE UNIQUE CLUSTERED INDEX IX_FactorBase_Fecha
        ON #FactorBase(Fecha);
    /* ============================================================
       6. Distribucion del chancado por flota y cargas por vuelta
       ============================================================ */
    SELECT
        f.*,
        CASE
            WHEN f.Dato_Mina_TMH > 0
            THEN
                f.Produccion_KOM_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Participacion_KOM,
        CASE
            WHEN f.Dato_Mina_TMH > 0
            THEN
                f.Produccion_CAT_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Participacion_CAT,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
            THEN
                f.Chancado_TMH_Sin_Ajuste
                * f.Produccion_KOM_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Chancado_KOM_TMH_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
            THEN
                f.Chancado_TMH_Sin_Ajuste
                * f.Produccion_CAT_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Chancado_CAT_TMH_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
             AND f.Produccion_KOM_TMH > 0
             AND f.Vueltas_KOM > 0
            THEN
                (
                    f.Chancado_TMH_Sin_Ajuste
                    * f.Produccion_KOM_TMH
                    / f.Dato_Mina_TMH
                )
                / f.Vueltas_KOM
            ELSE NULL
        END AS Carga_KOM_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
             AND f.Produccion_CAT_TMH > 0
             AND f.Vueltas_CAT > 0
            THEN
                (
                    f.Chancado_TMH_Sin_Ajuste
                    * f.Produccion_CAT_TMH
                    / f.Dato_Mina_TMH
                )
                / f.Vueltas_CAT
            ELSE NULL
        END AS Carga_CAT_Sin_Ajuste
    INTO #FactorCargas
    FROM #FactorBase AS f;
    CREATE UNIQUE CLUSTERED INDEX IX_FactorCargas_Fecha
        ON #FactorCargas(Fecha);
    /* ============================================================
       7. Aplicacion de limites operacionales
       ============================================================ */
    SELECT
        c.*,
        lk.limite AS Limite_KOM_TMH_Viaje,
        lc.limite AS Limite_CAT_TMH_Viaje,
        CASE
            WHEN c.Produccion_KOM_TMH = 0
            THEN 0.0
            WHEN c.Vueltas_KOM <= 0
              OR c.Carga_KOM_Sin_Ajuste IS NULL
            THEN NULL
            WHEN c.Carga_KOM_Sin_Ajuste <= lk.limite
            THEN c.Chancado_KOM_TMH_Sin_Ajuste
            ELSE c.Vueltas_KOM * lk.limite
        END AS KOM_TMH_Corregido,
        CASE
            WHEN c.Produccion_CAT_TMH = 0
            THEN 0.0
            WHEN c.Vueltas_CAT <= 0
              OR c.Carga_CAT_Sin_Ajuste IS NULL
            THEN NULL
            WHEN c.Carga_CAT_Sin_Ajuste <= lc.limite
            THEN c.Chancado_CAT_TMH_Sin_Ajuste
            ELSE c.Vueltas_CAT * lc.limite
        END AS CAT_TMH_Corregido
    INTO #FactorCorregido
    FROM #FactorCargas AS c
    JOIN #LimitesFactorV2 lk ON lk.Fecha=c.Fecha AND lk.flota='KOM'
    JOIN #LimitesFactorV2 lc ON lc.Fecha=c.Fecha AND lc.flota='CAT';
    CREATE UNIQUE CLUSTERED INDEX IX_FactorCorregido_Fecha
        ON #FactorCorregido(Fecha);
    /* ============================================================
       8. Resultado final y estado de evaluacion
       ============================================================ */
    SELECT
        c.Fecha,
        /* Trazabilidad del balance */
        c.Apilado_TMH_Bruto,
        c.Apilado_TMH_Neto,
        c.Sal_Dia,
        c.Humedad_Inventario,
        c.Apilado_TMS_Sin_Ajuste,
        c.Total_Inventario_Chancado_TMS,
        c.Inventario_Chancado_TMS_Anterior,
        c.Delta_Inventario_Chancado_TMS,
        c.SRR_TMS_Dia,
        c.Mineral_Chancado_TMS_Sin_Ajuste,
        c.Chancado_TMS_Sin_Ajuste,
        c.Chancado_TMH_Sin_Ajuste,
        /* Trazabilidad de camiones */
        c.Produccion_KOM_TMH,
        c.Produccion_CAT_TMH,
        c.Dato_Mina_TMH,
        c.Vueltas_KOM,
        c.Vueltas_CAT,
        c.Participacion_KOM,
        c.Participacion_CAT,
        c.Chancado_KOM_TMH_Sin_Ajuste,
        c.Chancado_CAT_TMH_Sin_Ajuste,
        c.Carga_KOM_Sin_Ajuste,
        c.Carga_CAT_Sin_Ajuste,
        c.KOM_TMH_Corregido,
        c.CAT_TMH_Corregido,
        CASE
            WHEN c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
            THEN
                c.KOM_TMH_Corregido
                + c.CAT_TMH_Corregido
            ELSE NULL
        END AS Chancado_TMH_Corregido_Total,
        CASE
            WHEN c.Chancado_TMH_Sin_Ajuste > 0
             AND c.Dato_Mina_TMH > 0
             AND c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
             AND
             (
                 c.Produccion_KOM_TMH = 0
                 OR c.Vueltas_KOM > 0
             )
             AND
             (
                 c.Produccion_CAT_TMH = 0
                 OR c.Vueltas_CAT > 0
             )
             AND ABS(c.Check_Produccion_Flotas) <= 0.001
            THEN
                (
                    c.KOM_TMH_Corregido
                    + c.CAT_TMH_Corregido
                )
                / c.Chancado_TMH_Sin_Ajuste
            ELSE NULL
        END AS Factor_Ajuste_Calculado,
        CASE
            WHEN c.Chancado_TMH_Sin_Ajuste > 0
             AND c.Dato_Mina_TMH > 0
             AND c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
             AND
             (
                 c.Produccion_KOM_TMH = 0
                 OR c.Vueltas_KOM > 0
             )
             AND
             (
                 c.Produccion_CAT_TMH = 0
                 OR c.Vueltas_CAT > 0
             )
             AND ABS(c.Check_Produccion_Flotas) <= 0.001
            THEN 1
            ELSE 0
        END AS Flag_Factor_Ajuste_Valido,
        CASE
            WHEN c.Flag_Humedad_Inventario_Valida <> 1
              OR c.Humedad_Inventario IS NULL
            THEN 'SIN_HUMEDAD'
            WHEN c.Flag_Inventario_Valido <> 1
              OR c.Delta_Inventario_Chancado_TMS IS NULL
            THEN 'SIN_INVENTARIO'
            WHEN c.Chancado_TMH_Sin_Ajuste IS NULL
            THEN 'SIN_BALANCE_CHANCADO'
            WHEN c.Dato_Mina_TMH <= 0
            THEN 'SIN_DATOS_CAMIONES'
            WHEN
            (
                c.Produccion_KOM_TMH > 0
                AND c.Vueltas_KOM <= 0
            )
            OR
            (
                c.Produccion_CAT_TMH > 0
                AND c.Vueltas_CAT <= 0
            )
            THEN 'SIN_VUELTAS'
            WHEN ABS(c.Check_Produccion_Flotas) > 0.001
            THEN 'ERROR_DISTRIBUCION_FLOTAS'
            WHEN c.Carga_KOM_Sin_Ajuste > c.Limite_KOM_TMH_Viaje
             AND c.Carga_CAT_Sin_Ajuste > c.Limite_CAT_TMH_Viaje
            THEN 'OK_AJUSTE_AMBAS_FLOTAS'
            WHEN c.Carga_KOM_Sin_Ajuste > c.Limite_KOM_TMH_Viaje
            THEN 'OK_AJUSTE_KOM'
            WHEN c.Carga_CAT_Sin_Ajuste > c.Limite_CAT_TMH_Viaje
            THEN 'OK_AJUSTE_CAT'
            ELSE 'OK_SIN_AJUSTE'
        END AS Estado_Calculo,
        /* Control de duplicados */
        c.Cantidad_Registros_Originales,
        c.Cantidad_Registros_Validos,
        c.Cantidad_Duplicados_Eliminados,
        c.Check_TMH_Bruto,
        c.Check_Produccion_Flotas,
        c.Flag_Continuidad_Diaria,
        c.Flag_Inventario_Valido,
        c.Flag_Humedad_Inventario_Valida,
        c.Limite_KOM_TMH_Viaje,
        c.Limite_CAT_TMH_Viaje
    FROM #FactorCorregido AS c
    ORDER BY c.Fecha;
END;
GO

CREATE OR ALTER PROCEDURE [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_standalone_test]
(
    @FechaInicio   date,
    @FechaFin      date,
    @DiasReproceso int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    /* ============================================================
       0. Validaciones
       ============================================================ */

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;

    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;

    IF @DiasReproceso IS NULL OR @DiasReproceso < 0
        THROW 50003, '@DiasReproceso debe ser mayor o igual que cero.', 1;

    IF OBJECT_ID
    (
        '[inventar_SpcHidr].[Control_Factor_Ajuste_Camiones_v2_test]',
        'U'
    ) IS NULL
        THROW 50004,
              'No existe la tabla Control_Factor_Ajuste_Camiones_v2_test.',
              1;

    DECLARE @FechaInicioProceso date =
        CASE
            WHEN DATEADD(DAY, -@DiasReproceso, @FechaFin) < @FechaInicio
                THEN DATEADD(DAY, -@DiasReproceso, @FechaFin)
            ELSE @FechaInicio
        END;

    DECLARE @FechaCalculo datetime2(7) = SYSDATETIME();


    /* ============================================================
       1. Capturar la salida del cálculo validado
       ============================================================ */

    IF OBJECT_ID('tempdb..#CalculoFactorV2') IS NOT NULL
        DROP TABLE #CalculoFactorV2;

    CREATE TABLE #CalculoFactorV2
    (
        Fecha date NOT NULL,

        Apilado_TMH_Bruto float NULL,
        Apilado_TMH_Neto float NULL,
        Sal_Dia float NULL,
        Humedad_Inventario float NULL,

        Apilado_TMS_Sin_Ajuste float NULL,

        Total_Inventario_Chancado_TMS float NULL,
        Inventario_Chancado_TMS_Anterior float NULL,
        Delta_Inventario_Chancado_TMS float NULL,

        SRR_TMS_Dia float NULL,

        Mineral_Chancado_TMS_Sin_Ajuste float NULL,
        Chancado_TMS_Sin_Ajuste float NULL,
        Chancado_TMH_Sin_Ajuste float NULL,

        Produccion_KOM_TMH float NULL,
        Produccion_CAT_TMH float NULL,
        Dato_Mina_TMH float NULL,

        Vueltas_KOM float NULL,
        Vueltas_CAT float NULL,

        Participacion_KOM float NULL,
        Participacion_CAT float NULL,

        Chancado_KOM_TMH_Sin_Ajuste float NULL,
        Chancado_CAT_TMH_Sin_Ajuste float NULL,

        Carga_KOM_Sin_Ajuste float NULL,
        Carga_CAT_Sin_Ajuste float NULL,

        KOM_TMH_Corregido float NULL,
        CAT_TMH_Corregido float NULL,
        Chancado_TMH_Corregido_Total float NULL,

        Factor_Ajuste_Calculado float NULL,
        Flag_Factor_Ajuste_Valido bit NULL,
        Estado_Calculo varchar(40) NULL,

        Cantidad_Registros_Originales int NULL,
        Cantidad_Registros_Validos int NULL,
        Cantidad_Duplicados_Eliminados int NULL,

        Check_TMH_Bruto float NULL,
        Check_Produccion_Flotas float NULL,

        Flag_Continuidad_Diaria bit NULL,
        Flag_Inventario_Valido bit NULL,
        Flag_Humedad_Inventario_Valida bit NULL,
        Limite_KOM_TMH_Viaje float NOT NULL,
        Limite_CAT_TMH_Viaje float NOT NULL
    );

    INSERT INTO #CalculoFactorV2
    EXEC [inventar_SpcHidr].[sp_factor_ajuste_camiones_standalone_test]
        @FechaInicio = @FechaInicioProceso,
        @FechaFin    = @FechaFin;

    CREATE UNIQUE CLUSTERED INDEX IX_CalculoFactorV2_Fecha
        ON #CalculoFactorV2(Fecha);


    /* ============================================================
       2. Recuperar SRR por turno para trazabilidad
       ============================================================ */

    IF OBJECT_ID('tempdb..#SRRTurnos') IS NOT NULL
        DROP TABLE #SRRTurnos;

    SELECT
        s.Fecha,
        SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'A' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_A,
        SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'B' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_B
    INTO #SRRTurnos
    FROM [inventar_SpcHidr].[v_srr_tms_origen_turno_standalone_test] AS s
    WHERE s.Fecha BETWEEN @FechaInicioProceso AND @FechaFin
    GROUP BY s.Fecha;

    CREATE UNIQUE CLUSTERED INDEX IX_SRRTurnos_Fecha
        ON #SRRTurnos(Fecha);


    /* ============================================================
       3. Construir fuente persistible

       Si el factor no es válido:
       - Factor_Ajuste queda NULL.
       - Los valores ajustados quedan NULL.
       - Los reportes decidirán posteriormente si aplican fallback
         hacia el valor basal.
       ============================================================ */

    IF OBJECT_ID('tempdb..#FuenteFactorV2') IS NOT NULL
        DROP TABLE #FuenteFactorV2;

    ;WITH Base AS
    (
        SELECT
            c.*,

            COALESCE(s.SRR_TMS_Turno_A, 0.0)
                AS SRR_TMS_Turno_A,

            COALESCE(s.SRR_TMS_Turno_B, 0.0)
                AS SRR_TMS_Turno_B,

            CASE
                WHEN c.Humedad_Inventario >= 0
                 AND c.Humedad_Inventario < 100
                    THEN 1.0 - c.Humedad_Inventario / 100.0
                ELSE NULL
            END AS Factor_Seco

        FROM #CalculoFactorV2 AS c

        LEFT JOIN #SRRTurnos AS s
            ON s.Fecha = c.Fecha
    ),

    AjusteTMH AS
    (
        SELECT
            b.*,

            CASE
                WHEN b.Flag_Factor_Ajuste_Valido = 1
                 AND b.Factor_Ajuste_Calculado IS NOT NULL
                THEN
                    b.Apilado_TMH_Bruto
                    * b.Factor_Ajuste_Calculado
                ELSE NULL
            END AS Apilado_TMH_Bruto_Ajustado,

            CASE
                WHEN b.Flag_Factor_Ajuste_Valido = 1
                 AND b.Factor_Ajuste_Calculado IS NOT NULL
                 AND b.Sal_Dia IS NOT NULL
                THEN
                    (
                        b.Apilado_TMH_Bruto
                        * b.Factor_Ajuste_Calculado
                    )
                    - b.Sal_Dia
                ELSE NULL
            END AS Apilado_TMH_Neto_Ajustado,

            CASE
    WHEN b.Apilado_TMS_Sin_Ajuste IS NOT NULL
     AND b.Sal_Dia IS NOT NULL
    THEN
        b.Apilado_TMS_Sin_Ajuste
        - b.Sal_Dia
    ELSE NULL
END AS Apilado_TMS_Neto_Sin_Ajuste

        FROM Base AS b
    ),

    AjusteTMS AS
    (
        SELECT
            a.*,

            CASE
                WHEN a.Apilado_TMH_Bruto_Ajustado IS NOT NULL
                 AND a.Factor_Seco IS NOT NULL
                THEN
                    a.Apilado_TMH_Bruto_Ajustado
                    * a.Factor_Seco
                ELSE NULL
            END AS Apilado_TMS_Bruto_Ajustado,

           CASE
    WHEN a.Apilado_TMH_Bruto_Ajustado IS NOT NULL
     AND a.Factor_Seco IS NOT NULL
     AND a.Sal_Dia IS NOT NULL
    THEN
        (
            a.Apilado_TMH_Bruto_Ajustado
            * a.Factor_Seco
        )
        - a.Sal_Dia
    ELSE NULL
END AS Apilado_TMS_Neto_Ajustado

        FROM AjusteTMH AS a
    ),

    BalanceAjustado AS
    (
        SELECT
            a.*,

            CASE
                WHEN a.Apilado_TMS_Bruto_Ajustado IS NOT NULL
                 AND a.Delta_Inventario_Chancado_TMS IS NOT NULL
                THEN
                    a.Apilado_TMS_Bruto_Ajustado
                    + a.Delta_Inventario_Chancado_TMS
                ELSE NULL
            END AS Mineral_Chancado_TMS_Ajustado

        FROM AjusteTMS AS a
    )

    SELECT
        b.Fecha,

        b.Limite_KOM_TMH_Viaje,
        b.Limite_CAT_TMH_Viaje,

        b.Apilado_TMH_Bruto
            AS Apilado_TMH_Bruto_Original,

        b.Apilado_TMH_Neto
            AS Apilado_TMH_Neto_Original,

        b.Sal_Dia
            AS Sal_TMH_Dia,

        b.Humedad_Inventario
            AS Humedad_Pct,

        b.Apilado_TMS_Sin_Ajuste
            AS Apilado_TMS_Bruto_Sin_Ajuste,

        b.Apilado_TMS_Neto_Sin_Ajuste,

        b.Total_Inventario_Chancado_TMS
            AS Inventario_Chancado_TMS_Actual,

        b.Inventario_Chancado_TMS_Anterior,
        b.Delta_Inventario_Chancado_TMS,

        b.Flag_Continuidad_Diaria,
        b.Flag_Inventario_Valido,

        b.Flag_Humedad_Inventario_Valida
            AS Flag_Humedad_Valida,

        b.SRR_TMS_Turno_A,
        b.SRR_TMS_Turno_B,
        b.SRR_TMS_Dia,

        b.Mineral_Chancado_TMS_Sin_Ajuste,
        b.Chancado_TMS_Sin_Ajuste,
        b.Chancado_TMH_Sin_Ajuste,

        b.Produccion_KOM_TMH,
        b.Produccion_CAT_TMH,
        b.Dato_Mina_TMH,

        b.Vueltas_KOM,
        b.Vueltas_CAT,

        b.Participacion_KOM,
        b.Participacion_CAT,

        b.Chancado_KOM_TMH_Sin_Ajuste,
        b.Chancado_CAT_TMH_Sin_Ajuste,

        b.Carga_KOM_Sin_Ajuste
            AS Carga_KOM_TMH_Viaje_Sin_Ajuste,

        b.Carga_CAT_Sin_Ajuste
            AS Carga_CAT_TMH_Viaje_Sin_Ajuste,

        b.KOM_TMH_Corregido,
        b.CAT_TMH_Corregido,
        b.Chancado_TMH_Corregido_Total,

        CASE
            WHEN b.Flag_Factor_Ajuste_Valido = 1
                THEN b.Factor_Ajuste_Calculado
            ELSE NULL
        END AS Factor_Ajuste,

        b.Flag_Factor_Ajuste_Valido,
        b.Estado_Calculo,

        b.Apilado_TMH_Bruto_Ajustado,
        b.Apilado_TMS_Bruto_Ajustado,

        b.Mineral_Chancado_TMS_Ajustado,

        CASE
            WHEN b.Mineral_Chancado_TMS_Ajustado IS NOT NULL
             AND b.Sal_Dia IS NOT NULL
             AND b.SRR_TMS_Dia IS NOT NULL
            THEN
                b.Mineral_Chancado_TMS_Ajustado
                - b.Sal_Dia
                - b.SRR_TMS_Dia
            ELSE NULL
        END AS Chancado_TMS_Ajustado,

        b.Apilado_TMH_Neto_Ajustado,
        b.Apilado_TMS_Neto_Ajustado,

        b.Cantidad_Registros_Originales,
        b.Cantidad_Registros_Validos,
        b.Cantidad_Duplicados_Eliminados,

        b.Check_TMH_Bruto,
        b.Check_Produccion_Flotas,

        CAST('BALANCE_INVENTARIO_CAMIONES_V2' AS varchar(100))
            AS Metodo,

        CAST('MOV_CAM_DEDUP_OPERACIONAL' AS varchar(100))
            AS Fuente_Camiones,

        @FechaCalculo AS Fecha_Calculo

    INTO #FuenteFactorV2

    FROM BalanceAjustado AS b;

    CREATE UNIQUE CLUSTERED INDEX IX_FuenteFactorV2_Fecha
        ON #FuenteFactorV2(Fecha);


    /* ============================================================
       4. Persistencia en tabla V2
       ============================================================ */

    MERGE
        [inventar_SpcHidr].[Control_Factor_Ajuste_Camiones_v2_test]
        WITH (HOLDLOCK) AS tgt

    USING #FuenteFactorV2 AS src
        ON tgt.Fecha = src.Fecha

    WHEN MATCHED THEN
        UPDATE SET
            Limite_KOM_TMH_Viaje =
                src.Limite_KOM_TMH_Viaje,

            Limite_CAT_TMH_Viaje =
                src.Limite_CAT_TMH_Viaje,

            Apilado_TMH_Bruto_Original =
                src.Apilado_TMH_Bruto_Original,

            Apilado_TMH_Neto_Original =
                src.Apilado_TMH_Neto_Original,

            Sal_TMH_Dia =
                src.Sal_TMH_Dia,

            Humedad_Pct =
                src.Humedad_Pct,

            Apilado_TMS_Bruto_Sin_Ajuste =
                src.Apilado_TMS_Bruto_Sin_Ajuste,

            Apilado_TMS_Neto_Sin_Ajuste =
                src.Apilado_TMS_Neto_Sin_Ajuste,

            Inventario_Chancado_TMS_Actual =
                src.Inventario_Chancado_TMS_Actual,

            Inventario_Chancado_TMS_Anterior =
                src.Inventario_Chancado_TMS_Anterior,

            Delta_Inventario_Chancado_TMS =
                src.Delta_Inventario_Chancado_TMS,

            Flag_Continuidad_Diaria =
                src.Flag_Continuidad_Diaria,

            Flag_Inventario_Valido =
                src.Flag_Inventario_Valido,

            Flag_Humedad_Valida =
                src.Flag_Humedad_Valida,

            SRR_TMS_Turno_A =
                src.SRR_TMS_Turno_A,

            SRR_TMS_Turno_B =
                src.SRR_TMS_Turno_B,

            SRR_TMS_Dia =
                src.SRR_TMS_Dia,

            Mineral_Chancado_TMS_Sin_Ajuste =
                src.Mineral_Chancado_TMS_Sin_Ajuste,

            Chancado_TMS_Sin_Ajuste =
                src.Chancado_TMS_Sin_Ajuste,

            Chancado_TMH_Sin_Ajuste =
                src.Chancado_TMH_Sin_Ajuste,

            Produccion_KOM_TMH =
                src.Produccion_KOM_TMH,

            Produccion_CAT_TMH =
                src.Produccion_CAT_TMH,

            Dato_Mina_TMH =
                src.Dato_Mina_TMH,

            Vueltas_KOM =
                src.Vueltas_KOM,

            Vueltas_CAT =
                src.Vueltas_CAT,

            Participacion_KOM =
                src.Participacion_KOM,

            Participacion_CAT =
                src.Participacion_CAT,

            Chancado_KOM_TMH_Sin_Ajuste =
                src.Chancado_KOM_TMH_Sin_Ajuste,

            Chancado_CAT_TMH_Sin_Ajuste =
                src.Chancado_CAT_TMH_Sin_Ajuste,

            Carga_KOM_TMH_Viaje_Sin_Ajuste =
                src.Carga_KOM_TMH_Viaje_Sin_Ajuste,

            Carga_CAT_TMH_Viaje_Sin_Ajuste =
                src.Carga_CAT_TMH_Viaje_Sin_Ajuste,

            KOM_TMH_Corregido =
                src.KOM_TMH_Corregido,

            CAT_TMH_Corregido =
                src.CAT_TMH_Corregido,

            Chancado_TMH_Corregido_Total =
                src.Chancado_TMH_Corregido_Total,

            Factor_Ajuste =
                src.Factor_Ajuste,

            Flag_Factor_Ajuste_Valido =
                src.Flag_Factor_Ajuste_Valido,

            Estado_Calculo =
                src.Estado_Calculo,

            Apilado_TMH_Bruto_Ajustado =
                src.Apilado_TMH_Bruto_Ajustado,

            Apilado_TMS_Bruto_Ajustado =
                src.Apilado_TMS_Bruto_Ajustado,

            Mineral_Chancado_TMS_Ajustado =
                src.Mineral_Chancado_TMS_Ajustado,

            Chancado_TMS_Ajustado =
                src.Chancado_TMS_Ajustado,

            Apilado_TMH_Neto_Ajustado =
                src.Apilado_TMH_Neto_Ajustado,

            Apilado_TMS_Neto_Ajustado =
                src.Apilado_TMS_Neto_Ajustado,

            Cantidad_Registros_Originales =
                src.Cantidad_Registros_Originales,

            Cantidad_Registros_Validos =
                src.Cantidad_Registros_Validos,

            Cantidad_Duplicados_Eliminados =
                src.Cantidad_Duplicados_Eliminados,

            Check_TMH_Bruto =
                src.Check_TMH_Bruto,

            Check_Produccion_Flotas =
                src.Check_Produccion_Flotas,

            Metodo =
                src.Metodo,

            Fuente_Camiones =
                src.Fuente_Camiones,

            Fecha_Calculo =
                src.Fecha_Calculo

    WHEN NOT MATCHED BY TARGET THEN
        INSERT
        (
            Fecha,

            Limite_KOM_TMH_Viaje,
            Limite_CAT_TMH_Viaje,

            Apilado_TMH_Bruto_Original,
            Apilado_TMH_Neto_Original,
            Sal_TMH_Dia,
            Humedad_Pct,

            Apilado_TMS_Bruto_Sin_Ajuste,
            Apilado_TMS_Neto_Sin_Ajuste,

            Inventario_Chancado_TMS_Actual,
            Inventario_Chancado_TMS_Anterior,
            Delta_Inventario_Chancado_TMS,

            Flag_Continuidad_Diaria,
            Flag_Inventario_Valido,
            Flag_Humedad_Valida,

            SRR_TMS_Turno_A,
            SRR_TMS_Turno_B,
            SRR_TMS_Dia,

            Mineral_Chancado_TMS_Sin_Ajuste,
            Chancado_TMS_Sin_Ajuste,
            Chancado_TMH_Sin_Ajuste,

            Produccion_KOM_TMH,
            Produccion_CAT_TMH,
            Dato_Mina_TMH,

            Vueltas_KOM,
            Vueltas_CAT,

            Participacion_KOM,
            Participacion_CAT,

            Chancado_KOM_TMH_Sin_Ajuste,
            Chancado_CAT_TMH_Sin_Ajuste,

            Carga_KOM_TMH_Viaje_Sin_Ajuste,
            Carga_CAT_TMH_Viaje_Sin_Ajuste,

            KOM_TMH_Corregido,
            CAT_TMH_Corregido,
            Chancado_TMH_Corregido_Total,

            Factor_Ajuste,
            Flag_Factor_Ajuste_Valido,
            Estado_Calculo,

            Apilado_TMH_Bruto_Ajustado,
            Apilado_TMS_Bruto_Ajustado,

            Mineral_Chancado_TMS_Ajustado,
            Chancado_TMS_Ajustado,

            Apilado_TMH_Neto_Ajustado,
            Apilado_TMS_Neto_Ajustado,

            Cantidad_Registros_Originales,
            Cantidad_Registros_Validos,
            Cantidad_Duplicados_Eliminados,

            Check_TMH_Bruto,
            Check_Produccion_Flotas,

            Metodo,
            Fuente_Camiones,
            Fecha_Calculo
        )
        VALUES
        (
            src.Fecha,

            src.Limite_KOM_TMH_Viaje,
            src.Limite_CAT_TMH_Viaje,

            src.Apilado_TMH_Bruto_Original,
            src.Apilado_TMH_Neto_Original,
            src.Sal_TMH_Dia,
            src.Humedad_Pct,

            src.Apilado_TMS_Bruto_Sin_Ajuste,
            src.Apilado_TMS_Neto_Sin_Ajuste,

            src.Inventario_Chancado_TMS_Actual,
            src.Inventario_Chancado_TMS_Anterior,
            src.Delta_Inventario_Chancado_TMS,

            src.Flag_Continuidad_Diaria,
            src.Flag_Inventario_Valido,
            src.Flag_Humedad_Valida,

            src.SRR_TMS_Turno_A,
            src.SRR_TMS_Turno_B,
            src.SRR_TMS_Dia,

            src.Mineral_Chancado_TMS_Sin_Ajuste,
            src.Chancado_TMS_Sin_Ajuste,
            src.Chancado_TMH_Sin_Ajuste,

            src.Produccion_KOM_TMH,
            src.Produccion_CAT_TMH,
            src.Dato_Mina_TMH,

            src.Vueltas_KOM,
            src.Vueltas_CAT,

            src.Participacion_KOM,
            src.Participacion_CAT,

            src.Chancado_KOM_TMH_Sin_Ajuste,
            src.Chancado_CAT_TMH_Sin_Ajuste,

            src.Carga_KOM_TMH_Viaje_Sin_Ajuste,
            src.Carga_CAT_TMH_Viaje_Sin_Ajuste,

            src.KOM_TMH_Corregido,
            src.CAT_TMH_Corregido,
            src.Chancado_TMH_Corregido_Total,

            src.Factor_Ajuste,
            src.Flag_Factor_Ajuste_Valido,
            src.Estado_Calculo,

            src.Apilado_TMH_Bruto_Ajustado,
            src.Apilado_TMS_Bruto_Ajustado,

            src.Mineral_Chancado_TMS_Ajustado,
            src.Chancado_TMS_Ajustado,

            src.Apilado_TMH_Neto_Ajustado,
            src.Apilado_TMS_Neto_Ajustado,

            src.Cantidad_Registros_Originales,
            src.Cantidad_Registros_Validos,
            src.Cantidad_Duplicados_Eliminados,

            src.Check_TMH_Bruto,
            src.Check_Produccion_Flotas,

            src.Metodo,
            src.Fuente_Camiones,
            src.Fecha_Calculo
        );

    DECLARE @FilasAfectadas int = @@ROWCOUNT;

    PRINT 'Proceso V2 finalizado.';
    PRINT 'Rango procesado: '
        + CONVERT(varchar(10), @FechaInicioProceso, 120)
        + ' a '
        + CONVERT(varchar(10), @FechaFin, 120);

    PRINT 'Filas insertadas/actualizadas: '
        + CONVERT(varchar(20), @FilasAfectadas);
END;

GO


    CREATE OR ALTER VIEW
        [inventar_SpcHidr].[v_ajuste_camiones_emision_test]
    AS

    SELECT
        f.Fecha,

        /* --------------------------------------------------------
           FACTOR REAL CALCULADO
           -------------------------------------------------------- */

        f.Factor_Ajuste
            AS Factor_Ajuste_Calculado,

        f.Flag_Factor_Ajuste_Valido,
        f.Estado_Calculo,


        /* --------------------------------------------------------
           APLICACIÓN EFECTIVA
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN ov.modo = 'FORZADO_1'
                    THEN 0
                ELSE auto.Flag_Usa_Ajuste_Automatico
            END
            AS bit
        ) AS Flag_Usa_Ajuste,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN 1.0
            ELSE auto.Factor_Aplicacion_Automatica
        END AS Factor_Aplicacion_Reportes,


        /* --------------------------------------------------------
           VALORES ORIGINALES
           -------------------------------------------------------- */

        f.Apilado_TMH_Bruto_Original,
        f.Apilado_TMH_Neto_Original,

        f.Apilado_TMS_Bruto_Sin_Ajuste,
        f.Apilado_TMS_Neto_Sin_Ajuste,

        f.Chancado_TMS_Sin_Ajuste,
        f.Chancado_TMH_Sin_Ajuste,


        /* --------------------------------------------------------
           VALORES AJUSTADOS CALCULADOS
           NO se alteran por override.
           -------------------------------------------------------- */

        f.Apilado_TMH_Bruto_Ajustado,
        f.Apilado_TMH_Neto_Ajustado,

        f.Apilado_TMS_Bruto_Ajustado,
        f.Apilado_TMS_Neto_Ajustado,

        f.Chancado_TMS_Ajustado,


        /* --------------------------------------------------------
           VALORES EFECTIVOS PARA REPORTE
           -------------------------------------------------------- */

        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN f.Apilado_TMH_Neto_Original
            ELSE auto.Apilado_TMH_Reporte_Automatico
        END AS Apilado_TMH_Reporte,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN f.Apilado_TMS_Neto_Sin_Ajuste
            ELSE auto.Apilado_TMS_Reporte_Automatico
        END AS Apilado_TMS_Reporte,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN f.Chancado_TMS_Sin_Ajuste
            ELSE auto.Chancado_TMS_Reporte_Automatico
        END AS Chancado_TMS_Reporte,


        /* --------------------------------------------------------
           DIFERENCIAS EFECTIVAMENTE APLICADAS
           -------------------------------------------------------- */

        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN 0.0
            ELSE auto.Diferencia_Apilado_TMH_Automatica
        END AS Diferencia_Apilado_TMH_Ajuste,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN 0.0
            ELSE auto.Diferencia_Apilado_TMS_Automatica
        END AS Diferencia_Apilado_TMS_Ajuste,


        CASE
            WHEN ov.modo = 'FORZADO_1'
                THEN 0.0
            ELSE auto.Diferencia_Chancado_TMS_Automatica
        END AS Diferencia_Chancado_TMS_Ajuste,


        CAST
        (
            CASE
                WHEN ov.modo = 'FORZADO_1'
                    THEN 'FORZADO_1_USUARIO'
                ELSE auto.Regla_Aplicacion_Automatica
            END
            AS varchar(80)
        ) AS Regla_Aplicacion,


        /* --------------------------------------------------------
           TRAZABILIDAD EXISTENTE
           -------------------------------------------------------- */

        f.Sal_TMH_Dia,
        f.Humedad_Pct,

        f.Inventario_Chancado_TMS_Actual,
        f.Inventario_Chancado_TMS_Anterior,
        f.Delta_Inventario_Chancado_TMS,

        f.SRR_TMS_Turno_A,
        f.SRR_TMS_Turno_B,
        f.SRR_TMS_Dia,

        f.Produccion_KOM_TMH,
        f.Produccion_CAT_TMH,

        f.Vueltas_KOM,
        f.Vueltas_CAT,

        f.Carga_KOM_TMH_Viaje_Sin_Ajuste,
        f.Carga_CAT_TMH_Viaje_Sin_Ajuste,

        f.KOM_TMH_Corregido,
        f.CAT_TMH_Corregido,

        f.Cantidad_Registros_Originales,
        f.Cantidad_Registros_Validos,
        f.Cantidad_Duplicados_Eliminados,

        f.Metodo,
        f.Fuente_Camiones,
        f.Fecha_Calculo,

        f.Limite_KOM_TMH_Viaje,
        f.Limite_CAT_TMH_Viaje,


        /* --------------------------------------------------------
           NUEVA TRAZABILIDAD 2B
           -------------------------------------------------------- */

        auto.Factor_Aplicacion_Automatica,

        auto.Flag_Usa_Ajuste_Automatico,

        auto.Regla_Aplicacion_Automatica,

        CAST
        (
            CASE
                WHEN ov.modo = 'FORZADO_1'
                    THEN 'FORZADO_1'
                ELSE 'AUTOMATICO'
            END
            AS varchar(20)
        ) AS Modo_Aplicacion,

        CAST
        (
            CASE
                WHEN ov.modo = 'FORZADO_1'
                    THEN 1
                ELSE 0
            END
            AS bit
        ) AS Flag_Override_1,

        ov.id_override
            AS Id_Control_Aplicacion,

        ov.motivo
            AS Control_Aplicacion_Motivo,

        ov.usuario
            AS Control_Aplicacion_Usuario,

        ov.fecha_registro
            AS Control_Aplicacion_Fecha_Registro


    FROM
        inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test AS f


    OUTER APPLY
    (
        SELECT TOP (1)
            o.id_override,
            o.modo,
            o.motivo,
            o.usuario,
            o.fecha_registro

        FROM
            inventar_SpcHidr.factor_camiones_override_aplicacion_test AS o

        WHERE
            f.Fecha >= o.fecha_desde
            AND f.Fecha <= o.fecha_hasta

        ORDER BY
            o.fecha_registro DESC,
            o.id_override DESC

    ) AS ov


    CROSS APPLY
    (
        SELECT

            CAST
            (
                CASE
                    WHEN f.Flag_Factor_Ajuste_Valido = 1
                     AND f.Factor_Ajuste IS NOT NULL
                     AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
                     AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
                     AND f.Chancado_TMS_Ajustado IS NOT NULL
                        THEN 1
                    ELSE 0
                END
                AS bit
            ) AS Flag_Usa_Ajuste_Automatico,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Factor_Ajuste IS NOT NULL
                    THEN f.Factor_Ajuste
                ELSE 1.0
            END AS Factor_Aplicacion_Automatica,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
                    THEN f.Apilado_TMH_Neto_Ajustado
                ELSE f.Apilado_TMH_Neto_Original
            END AS Apilado_TMH_Reporte_Automatico,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
                    THEN f.Apilado_TMS_Neto_Ajustado
                ELSE f.Apilado_TMS_Neto_Sin_Ajuste
            END AS Apilado_TMS_Reporte_Automatico,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Chancado_TMS_Ajustado IS NOT NULL
                    THEN f.Chancado_TMS_Ajustado
                ELSE f.Chancado_TMS_Sin_Ajuste
            END AS Chancado_TMS_Reporte_Automatico,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
                    THEN
                        f.Apilado_TMH_Neto_Ajustado
                        - f.Apilado_TMH_Neto_Original
                ELSE 0.0
            END AS Diferencia_Apilado_TMH_Automatica,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
                    THEN
                        f.Apilado_TMS_Neto_Ajustado
                        - f.Apilado_TMS_Neto_Sin_Ajuste
                ELSE 0.0
            END AS Diferencia_Apilado_TMS_Automatica,


            CASE
                WHEN f.Flag_Factor_Ajuste_Valido = 1
                 AND f.Chancado_TMS_Ajustado IS NOT NULL
                    THEN
                        f.Chancado_TMS_Ajustado
                        - f.Chancado_TMS_Sin_Ajuste
                ELSE 0.0
            END AS Diferencia_Chancado_TMS_Automatica,


            CAST
            (
                CASE
                    WHEN f.Flag_Factor_Ajuste_Valido = 1
                     AND f.Factor_Ajuste IS NOT NULL
                     AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
                     AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
                     AND f.Chancado_TMS_Ajustado IS NOT NULL
                        THEN 'APLICA_AJUSTE_VALIDADO'

                    WHEN f.Estado_Calculo = 'SIN_DATOS_CAMIONES'
                        THEN 'FALLBACK_SIN_DATOS_CAMIONES'

                    WHEN f.Flag_Factor_Ajuste_Valido = 0
                        THEN CONCAT
                        (
                            'FALLBACK_',
                            COALESCE(
                                f.Estado_Calculo,
                                'NO_EVALUABLE'
                            )
                        )

                    ELSE 'FALLBACK_INCONSISTENCIA_CALCULO'
                END
                AS varchar(80)
            ) AS Regla_Aplicacion_Automatica

        ) AS auto;
    
GO


DROP PROCEDURE IF EXISTS inventar_SpcHidr.sp_registrar_parametro_factor_camiones_vigencia_test;
DELETE FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
 WHERE parametro='CARGA_NOMINAL_TMH_VIAJE';
ALTER TABLE inventar_SpcHidr.factor_camiones_parametro_vigencia_test
 DROP CONSTRAINT CK__factor_ca__param__41EF6173;
ALTER TABLE inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH CHECK
 ADD CONSTRAINT CK__factor_ca__param__41EF6173 CHECK (parametro='LIMITE_CARGA_AJUSTE');
IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Carga_Nominal_KOM_TMH_Viaje') IS NOT NULL
 ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test DROP COLUMN Carga_Nominal_KOM_TMH_Viaje;
IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Carga_Nominal_CAT_TMH_Viaje') IS NOT NULL
 ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test DROP COLUMN Carga_Nominal_CAT_TMH_Viaje;

DROP VIEW IF EXISTS inventar_SpcHidr.v_vueltas_camiones_diarias_test;
DROP FUNCTION IF EXISTS inventar_SpcHidr.fn_resolver_vueltas_camiones_test;
IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Estado_Fuente_MOV_CAM') IS NOT NULL
 ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test DROP COLUMN Estado_Fuente_MOV_CAM;
IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Estado_Fuente_POWERBI') IS NOT NULL
 ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test DROP COLUMN Estado_Fuente_POWERBI;
