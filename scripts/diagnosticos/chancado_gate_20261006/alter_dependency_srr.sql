/* ================================================================
   ALTER inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test
   v1.15 -> v1.16
   ----------------------------------------------------------------
   UNICO CAMBIO: PASO 3 (Ley CuT mina + stock).

   Motivo: Ley_CuT_Mina_Stock (insumo 4 de 7 para calcular
   Ley_CuT_Real_srr) leia solo mov_cam.CuTG00. Para 01-03 ago 2026
   ese laboratorio todavia no cargaba leyes para los camiones
   Destino=CH01, asi que #LeyMinaStock quedaba con CERO filas esos
   dias y Ley_CuT_Real_srr salia NULL aunque los otros 6 insumos
   estuvieran completos.

   Fix: mismo patron que PASO 2 (Chancado) y que
   v_conciliacion_chancado_v2 -- si mov_cam no tiene fila valida
   para una fecha, se usa como preliminar el promedio ponderado de
   "cut" en DEV_SIIR.hidro.imp_csv con el mismo filtro que ya usa
   Chancado (to='CH01', shovel<>'SRR', origen='IMP'). No reemplaza
   mov_cam cuando este si tiene datos -- solo llena el hueco.

   Se agrega la columna Fuente_Ley_Mina_Stock ('MOV_CAM' o
   'IMP_CSV_PRELIMINAR') a #LeyMinaStock para trazabilidad. No se
   toca el MERGE final ni la tabla Datos_conciliados_of: el JOIN
   contra #LeyMinaStock solo usa Fecha y Ley_CuT_Mina_Stock, asi
   que la columna nueva no requiere cambios aguas abajo.

   Nota: ic.tonnage en imp_csv es tonelaje humedo (no seco), igual
   que ya se acepta como aproximacion preliminar en PASO 2 para
   Chancado -- coherente con la Seccion 9 del prompt maestro
   (diferencia metodologica temporalmente aceptada).

   Todo lo demas (PASO 1, 2, 4-11, limpieza de temporales, manejo
   de errores) queda identico a la version que Luis ya valido.
================================================================ */
ALTER PROCEDURE [inventar_SpcHidr].[sp_mantiene_datos_conciliados_emision_test]
(
    @FechaInicio      date,

    @FechaFin         date,

    @DiasReproceso    int = 7,

    @RefrescarFactor  bit = 1
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;
    /* ================================================================
       CORTE DINAMICO DE CAMIONES
       Resuelve la ultima fecha realmente cargada dentro del mes de
       @FechaFin y no posterior al cierre solicitado.
    ================================================================ */
    DECLARE @InicioMesCorte date =
        DATEFROMPARTS(YEAR(@FechaFin), MONTH(@FechaFin), 1);
    DECLARE @FechaCorteCamiones date;
    /* Periodo cerrado: respetar la fotografia congelada. */
    SELECT TOP (1)
        @FechaCorteCamiones = cfg.[fecha_corte_camiones]
    FROM [inventar_SpcHidr].[configuracion_reclamo_rotopala_periodo] cfg
    WHERE cfg.[periodo_reporte] = @InicioMesCorte
      AND cfg.[pad_id] = 2
      AND cfg.[estado] = 'CERRADO'
      AND cfg.[fecha_corte_camiones] IS NOT NULL;
    /* Periodo abierto: utilizar la ultima carga realmente disponible. */
    IF @FechaCorteCamiones IS NULL
    BEGIN
        SELECT
            @FechaCorteCamiones = MAX(CAST(cr.[fecha] AS date))
        FROM [inventar_SpcHidr].
             [control_reclamo_sulfuro_camiones_thm_diario] cr
        WHERE CAST(cr.[fecha] AS date) >= @InicioMesCorte
          AND CAST(cr.[fecha] AS date) <= @FechaFin;
    END;
    IF @FechaCorteCamiones IS NULL
        THROW 52001,
              'No existe una fecha de corte de camiones valida para el periodo.',
              1;
    EXEC sys.sp_set_session_context
        @key   = N'fecha_corte_camiones',
        @value = @FechaCorteCamiones;
    PRINT '-- Corte dinamico camiones: '
        + CONVERT(varchar(10), @FechaCorteCamiones, 120);
    DECLARE @FechaInicioProceso date =
        CASE
            WHEN DATEADD(DAY, -@DiasReproceso, @FechaFin) < @FechaInicio
                THEN DATEADD(DAY, -@DiasReproceso, @FechaFin)
            ELSE @FechaInicio
        END;
    DECLARE @FechaFinExclusiva date = DATEADD(DAY, 1, @FechaFin);
    IF @RefrescarFactor = 1

    BEGIN

        EXEC [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_test]

             @FechaInicio   = @FechaInicioProceso,

             @FechaFin      = @FechaFin,

             @DiasReproceso = @DiasReproceso;

    END

    ELSE

    BEGIN

        PRINT '-- Factor interno omitido: fotografía preparada por coordinador externo.';

    END;
    DECLARE @t0 datetime2        = SYSDATETIME();
    DECLARE @t1 datetime2;
    PRINT '-- INICIO: ' + CONVERT(varchar, @t0, 121);
    PRINT '-- Version: 1.16 (Ley CuT SRR: fallback IMP en Ley_CuT_Mina_Stock) -- destino: Datos_conciliados_of (PRODUCCION)';
    PRINT '-- Rango efectivo: ' + CONVERT(varchar, @FechaInicioProceso) + ' a ' + CONVERT(varchar, @FechaFin);
    /* ================================================================
       PASO 1: Calendario
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Fechas') IS NOT NULL DROP TABLE #Fechas;
    ;WITH rec AS
    (
        SELECT @FechaInicioProceso AS Fecha
        UNION ALL
        SELECT DATEADD(DAY, 1, Fecha) FROM rec WHERE Fecha < @FechaFin
    )
    SELECT Fecha INTO #Fechas FROM rec OPTION (MAXRECURSION 1000);
    CREATE CLUSTERED INDEX ix_f ON #Fechas(Fecha);
    PRINT 'PASO 1  Calendario       : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 2: Chancado TMH                                   v1.11
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Chancado')        IS NOT NULL DROP TABLE #Chancado;
    IF OBJECT_ID('tempdb..#ChancadoMovCam')  IS NOT NULL DROP TABLE #ChancadoMovCam;
    IF OBJECT_ID('tempdb..#ChancadoImpCsv')  IS NOT NULL DROP TABLE #ChancadoImpCsv;
    SELECT
        CAST(Fecha AS date)                AS Fecha,
        SUM(COALESCE(Tonelaje_Hum_CIO,0))  AS Chancado_TMH_Dia
    INTO #ChancadoMovCam
    FROM [inventar_SpcHidr].[mov_cam]
    WHERE Fase NOT LIKE '%SRR%'
      AND CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin
    GROUP BY CAST(Fecha AS date);
    CREATE CLUSTERED INDEX ix_chmc ON #ChancadoMovCam(Fecha);
    SELECT
        CAST(ic.[date] AS date)             AS Fecha,
        SUM(COALESCE(ic.tonnage,0))         AS Chancado_TMH_Dia
    INTO #ChancadoImpCsv
    FROM [DEV_SIIR].[hidro].[imp_csv] ic
    WHERE ic.[to]     = 'CH01'
      AND ic.shovel  <> 'SRR'
      AND ic.origen   = 'IMP'
      AND CAST(ic.[date] AS date) >= @FechaInicioProceso
      AND CAST(ic.[date] AS date) <= @FechaFin
    GROUP BY CAST(ic.[date] AS date);
    CREATE CLUSTERED INDEX ix_chic ON #ChancadoImpCsv(Fecha);
    SELECT
        mc.Fecha,
        mc.Chancado_TMH_Dia,
        CAST('MOV_CAM' AS varchar(40))
            AS Fuente_Chancado_TMH,
        CAST('SUM_TONELAJE_HUM_CIO_FASE_NO_SRR' AS varchar(60))
            AS Metodo_Calculo_Chancado,
        CAST('OK' AS varchar(40))
            AS Flag_Chancado
    INTO #Chancado
    FROM #ChancadoMovCam mc
    UNION ALL
    SELECT
        ic.Fecha,
        ic.Chancado_TMH_Dia,
        CAST('IMP_CSV_PRELIMINAR' AS varchar(40)),
        CAST('SUM_TONNAGE_CH01_SIN_SRR_ORIGEN_IMP' AS varchar(60)),
        CAST('PRELIMINAR_PENDIENTE_MOV_CAM' AS varchar(40))
    FROM #ChancadoImpCsv ic
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM #ChancadoMovCam mc2
        WHERE mc2.Fecha = ic.Fecha
    );
    CREATE CLUSTERED INDEX ix_ch ON #Chancado(Fecha);
    DECLARE @ChFilas       int;
    DECLARE @ChMovCam      int;
    DECLARE @ChImpCsv      int;
    SELECT
        @ChFilas  = COUNT(*),
        @ChMovCam = SUM(CASE WHEN Fuente_Chancado_TMH = 'MOV_CAM' THEN 1 ELSE 0 END),
        @ChImpCsv = SUM(CASE WHEN Fuente_Chancado_TMH = 'IMP_CSV_PRELIMINAR' THEN 1 ELSE 0 END)
    FROM #Chancado;
    PRINT 'PASO 2  Chancado         : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(COALESCE(@ChFilas,0) AS varchar) + ' filas';
    /* ================================================================
       PASO 3: Ley CuT mina + stock                              v1.16
       Fallback IMP: ver comentario al inicio del script. Mismo
       patron que PASO 2 -- mov_cam manda si tiene datos, imp_csv
       rellena solo los dias que mov_cam dejo vacios.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#LeyMinaStock')        IS NOT NULL DROP TABLE #LeyMinaStock;
    IF OBJECT_ID('tempdb..#LeyMinaStockMovCam')  IS NOT NULL DROP TABLE #LeyMinaStockMovCam;
    IF OBJECT_ID('tempdb..#LeyMinaStockImpCsv')  IS NOT NULL DROP TABLE #LeyMinaStockImpCsv;
    ;WITH MovCam_Deduplicado AS
    (
        SELECT
            m.*,
            rn = ROW_NUMBER() OVER
            (
                PARTITION BY
                    m.Fecha, m.Turno, m.Origen, m.Solido, m.Fase, m.Banco,
                    m.Pala, m.Destino, m.Poligono_CIO, m.Flota_CEX, m.Ton,
                    m.N_BREAK, m.[Ton hum diseño CAEX], m.Tonelaje_Hum_CIO,
                    m.Tonelaje_seco_CIO, m.PONDHumedad
                ORDER BY m.mov_id
            )
        FROM [inventar_SpcHidr].[mov_cam] AS m
        WHERE CAST(m.Fecha AS date) >= @FechaInicioProceso
          AND CAST(m.Fecha AS date) <= @FechaFin
          AND UPPER(LTRIM(RTRIM(ISNULL(m.Destino, '')))) = 'CH01'
          AND UPPER(LTRIM(RTRIM(ISNULL(m.Fase, '')))) <> 'SRR'
    )
    SELECT
        Fecha = CAST(Fecha AS date),
        Tonelaje_Mina_Stock = SUM(Tonelaje_seco_CIO),
        Ley_CuT_Mina_Stock = SUM(Tonelaje_seco_CIO * CuTG00) / NULLIF(SUM(Tonelaje_seco_CIO), 0),
        Cantidad_Registros_Validos = COUNT(*)
    INTO #LeyMinaStockMovCam
    FROM MovCam_Deduplicado
    WHERE rn = 1 AND Tonelaje_seco_CIO > 0 AND CuTG00 IS NOT NULL
    GROUP BY CAST(Fecha AS date);
    CREATE CLUSTERED INDEX ix_lms_mc ON #LeyMinaStockMovCam(Fecha);
    SELECT
        CAST(ic.[date] AS date) AS Fecha,
        SUM(COALESCE(ic.tonnage, 0)) AS Tonelaje_Mina_Stock,
        SUM(ic.tonnage * ic.cut)
            / NULLIF(SUM(CASE WHEN ic.cut IS NOT NULL THEN ic.tonnage ELSE NULL END), 0)
            AS Ley_CuT_Mina_Stock,
        COUNT(*) AS Cantidad_Registros_Validos
    INTO #LeyMinaStockImpCsv
    FROM [DEV_SIIR].[hidro].[imp_csv] ic
    WHERE ic.[to]     = 'CH01'
      AND ic.shovel  <> 'SRR'
      AND ic.origen   = 'IMP'
      AND ic.tonnage  > 0
      AND ic.cut IS NOT NULL
      AND CAST(ic.[date] AS date) >= @FechaInicioProceso
      AND CAST(ic.[date] AS date) <= @FechaFin
    GROUP BY CAST(ic.[date] AS date);
    CREATE CLUSTERED INDEX ix_lms_ic ON #LeyMinaStockImpCsv(Fecha);
    SELECT
        mc.Fecha,
        mc.Tonelaje_Mina_Stock,
        mc.Ley_CuT_Mina_Stock,
        mc.Cantidad_Registros_Validos,
        CAST('MOV_CAM' AS varchar(40)) AS Fuente_Ley_Mina_Stock
    INTO #LeyMinaStock
    FROM #LeyMinaStockMovCam mc
    UNION ALL
    SELECT
        ic.Fecha,
        ic.Tonelaje_Mina_Stock,
        ic.Ley_CuT_Mina_Stock,
        ic.Cantidad_Registros_Validos,
        CAST('IMP_CSV_PRELIMINAR' AS varchar(40))
    FROM #LeyMinaStockImpCsv ic
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM #LeyMinaStockMovCam mc2
        WHERE mc2.Fecha = ic.Fecha
    );
    CREATE CLUSTERED INDEX ix_lms ON #LeyMinaStock(Fecha);
    DECLARE @LmsFilas   int;
    DECLARE @LmsMovCam  int;
    DECLARE @LmsImpCsv  int;
    SELECT
        @LmsFilas  = COUNT(*),
        @LmsMovCam = SUM(CASE WHEN Fuente_Ley_Mina_Stock = 'MOV_CAM' THEN 1 ELSE 0 END),
        @LmsImpCsv = SUM(CASE WHEN Fuente_Ley_Mina_Stock = 'IMP_CSV_PRELIMINAR' THEN 1 ELSE 0 END)
    FROM #LeyMinaStock;
    PRINT 'PASO 3  Ley mina + stock: ' + CAST(DATEDIFF(ms, @t1, SYSDATETIME()) AS varchar) + ' ms - '
        + CAST(COALESCE(@LmsFilas,0) AS varchar) + ' filas ('
        + CAST(COALESCE(@LmsMovCam,0) AS varchar) + ' mov_cam, '
        + CAST(COALESCE(@LmsImpCsv,0) AS varchar) + ' imp_csv preliminar)';
    /* ================================================================
       PASO 4: Humedad / Sal / Apilado TMH
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Apilado') IS NOT NULL DROP TABLE #Apilado;
    SELECT
        CAST(Fecha AS date)      AS Fecha,
        Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia,
        Sal_turno_A, Sal_Turno_B, Sal_promedio_dia,
        Apilado_TMH_turno_A, Apilado_TMH_turno_B, Apilado_TMH_promedio_dia
    INTO #Apilado
    FROM [inventar_SpcHidr].[Historico_Apilado_Diario]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_ap ON #Apilado(Fecha);
    PRINT 'PASO 4  Apilado/Humedad  : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 5: Generador diario
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Generador') IS NOT NULL DROP TABLE #Generador;
    SELECT
        g.Fecha, g.Apilado_TMS_Real_Dia, g.Apilado_TMS_Plan,
        g.Material_Operacion, g.Modulo, g.Avance, g.CuT_Real_Dia, g.CuT_Plan
    INTO #Generador
    FROM [inventar_SpcHidr].[fn_generador_reporte_diario_emision_test](@FechaInicioProceso, @FechaFinExclusiva) g;
    CREATE CLUSTERED INDEX ix_gen ON #Generador(Fecha);
    PRINT 'PASO 5  Generador diario : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 6: SRR diario
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#SRR') IS NOT NULL DROP TABLE #SRR;
    ;WITH srr_turno AS
    (
        SELECT
            CAST(Fecha AS date) AS Fecha,
            Turno,
            CASE
                WHEN SRR IS NULL OR Apilado_TMS_Real IS NULL THEN NULL
                ELSE Apilado_TMS_Real * SRR / 100.0
            END AS SRR_TMS_Turno
        FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test]
        WHERE CAST(Fecha AS date) >= @FechaInicioProceso
          AND CAST(Fecha AS date) <= @FechaFin
    )
    SELECT
        Fecha,
        SUM(CASE WHEN Turno = 'A' THEN SRR_TMS_Turno END) AS SRR_TMS_Turno_A,
        SUM(CASE WHEN Turno = 'B' THEN SRR_TMS_Turno END) AS SRR_TMS_Turno_B,
        SUM(SRR_TMS_Turno)                                AS SRR_TMS_Dia,
        CASE
            WHEN COUNT(DISTINCT Turno) >= 2
             AND SUM(CASE WHEN SRR_TMS_Turno IS NULL THEN 1 ELSE 0 END) = 0
                THEN 'OK'
            WHEN SUM(SRR_TMS_Turno) IS NOT NULL
                THEN 'OK_PARCIAL'
            ELSE 'SIN_SRR_TMS'
        END AS Flag_SRR_TMS_Dia
    INTO #SRR
    FROM srr_turno
    GROUP BY Fecha;
    CREATE CLUSTERED INDEX ix_srr ON #SRR(Fecha);
    PRINT 'PASO 6  SRR              : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 7: Produccion catodica
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Catodos') IS NOT NULL DROP TABLE #Catodos;
    SELECT
        CAST(Fecha AS date)     AS Fecha,
        Produccion_Catodos_Real
    INTO #Catodos
    FROM [inventar_SpcHidr].[v_produccion_catodica_diaria_test]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_cat ON #Catodos(Fecha);
    PRINT 'PASO 7  Catodos          : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 8: Plan mensual
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Plan') IS NOT NULL DROP TABLE #Plan;
    SELECT
        CAST(Fecha AS date)             AS Fecha,
        Ley_CuT_Plan_Fuente, Cobre_Fino_Apilado_Plan_Fuente,
        TMS_Rotopala_1_Plan, TMS_Rotopala_2_Plan,
        Camiones_TMS_Plan, Produccion_Catodos_Plan,
        SRR_TMS_Plan, Ley_CuT_Plan_SRR
    INTO #Plan
    FROM [inventar_SpcHidr].[v_planes_mensuales_diarios_test]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_pm ON #Plan(Fecha);
    PRINT 'PASO 8  Plan mensual     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 9: Reclamo base                                     v1.13
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoBase') IS NOT NULL DROP TABLE #ReclamoBase;
    SELECT
        r.fecha_operacion              AS Fecha,
        r.pad_id, r.[campaña_id], r.modulo_id, r.modulo_numero, r.rotopala_id,
        r.avance_porcentaje, r.avance_total_porcentaje, r.avance_camiones_porcentaje,
        r.tonelaje_reclamado_diario, r.tonelaje_camiones_diario, r.volumen_diario_m3,
        r.fuente_reclamo, r.metodo_calculo, r.flag_calculo
    INTO #ReclamoBase
    FROM [reclamo].[v_reclamo_para_conciliados] r
    WHERE r.fecha_operacion >= @FechaInicioProceso
      AND r.fecha_operacion <= @FechaFin;
    CREATE CLUSTERED INDEX ix_rb ON #ReclamoBase(Fecha, pad_id);
    DECLARE @RbFilas int = @@ROWCOUNT;
    PRINT 'PASO 9  Reclamo base     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@RbFilas AS varchar) + ' filas (fuente: reclamo.v_reclamo_para_conciliados)';
    /* ================================================================
       PASO 10: Reclamo TMS y contexto por pad                  v1.14
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoOxidosTMS')   IS NOT NULL DROP TABLE #ReclamoOxidosTMS;
    IF OBJECT_ID('tempdb..#ReclamoSulfurosTMS')  IS NOT NULL DROP TABLE #ReclamoSulfurosTMS;
    IF OBJECT_ID('tempdb..#GanadorOxRaw')        IS NOT NULL DROP TABLE #GanadorOxRaw;
    IF OBJECT_ID('tempdb..#GanadorSuRaw')        IS NOT NULL DROP TABLE #GanadorSuRaw;
    IF OBJECT_ID('tempdb..#GanadorOx')           IS NOT NULL DROP TABLE #GanadorOx;
    IF OBJECT_ID('tempdb..#GanadorSu')           IS NOT NULL DROP TABLE #GanadorSu;
    IF OBJECT_ID('tempdb..#GrupoOx')             IS NOT NULL DROP TABLE #GrupoOx;
    IF OBJECT_ID('tempdb..#GrupoSu')             IS NOT NULL DROP TABLE #GrupoSu;
    IF OBJECT_ID('tempdb..#ReclamoOxidosCtx')    IS NOT NULL DROP TABLE #ReclamoOxidosCtx;
    IF OBJECT_ID('tempdb..#ReclamoSulfurosCtx')  IS NOT NULL DROP TABLE #ReclamoSulfurosCtx;
    SELECT Fecha, SUM(tonelaje_reclamado_diario) AS TMS_Rotopala_1_Real
    INTO #ReclamoOxidosTMS  FROM #ReclamoBase WHERE pad_id = 1 GROUP BY Fecha;
    SELECT Fecha, SUM(tonelaje_reclamado_diario) AS TMS_Rotopala_2_Real
    INTO #ReclamoSulfurosTMS FROM #ReclamoBase WHERE pad_id = 2 GROUP BY Fecha;
    SELECT
        rb.Fecha, rb.modulo_id, rb.modulo_numero, rb.avance_porcentaje,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
        rb.[campaña_id], rb.tonelaje_reclamado_diario
    INTO #GanadorOxRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.pad_id = 1 AND rb.tonelaje_reclamado_diario > 0;
    CREATE CLUSTERED INDEX ix_gor ON #GanadorOxRaw(Fecha, modulo_numero);
    SELECT
        rb.Fecha, rb.modulo_id, rb.modulo_numero, rb.avance_porcentaje,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
        rb.[campaña_id], rb.tonelaje_reclamado_diario
    INTO #GanadorSuRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.pad_id = 2 AND rb.tonelaje_reclamado_diario > 0;
    CREATE CLUSTERED INDEX ix_gsr ON #GanadorSuRaw(Fecha, modulo_numero);
    CREATE TABLE #GanadorOx (Fecha date NOT NULL PRIMARY KEY, modulo_numero int NULL, avance_porcentaje float NULL, campana_nombre nvarchar(255) NULL);
    CREATE TABLE #GanadorSu (Fecha date NOT NULL PRIMARY KEY, modulo_numero int NULL, avance_porcentaje float NULL, campana_nombre nvarchar(255) NULL);
    DECLARE @PisoOx int = 0, @CampanaPisoOx nvarchar(255) = NULL;
    DECLARE @PisoSu int = 0, @CampanaPisoSu nvarchar(255) = NULL;
    DECLARE @FechaCur date, @ModCur int, @AvanceCur float, @CampCur nvarchar(255);
    DECLARE dias_ox CURSOR LOCAL FAST_FORWARD FOR
        SELECT DISTINCT Fecha FROM #GanadorOxRaw ORDER BY Fecha;
    OPEN dias_ox;
    FETCH NEXT FROM dias_ox INTO @FechaCur;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @ModCur = NULL; SET @AvanceCur = NULL; SET @CampCur = NULL;
        SELECT TOP (1) @ModCur = modulo_numero, @AvanceCur = avance_porcentaje, @CampCur = campana_nombre
        FROM #GanadorOxRaw
        WHERE Fecha = @FechaCur
          AND (@CampanaPisoOx IS NULL OR campana_nombre <> @CampanaPisoOx OR modulo_numero >= @PisoOx)
        ORDER BY avance_porcentaje ASC, modulo_id DESC;
        IF @ModCur IS NOT NULL
        BEGIN
            INSERT INTO #GanadorOx (Fecha, modulo_numero, avance_porcentaje, campana_nombre)
            VALUES (@FechaCur, @ModCur, @AvanceCur, @CampCur);
            IF @CampanaPisoOx IS NULL OR @CampCur <> @CampanaPisoOx
            BEGIN
                SET @CampanaPisoOx = @CampCur;
                SET @PisoOx = @ModCur;
            END
            ELSE IF @ModCur > @PisoOx
                SET @PisoOx = @ModCur;
        END;
        FETCH NEXT FROM dias_ox INTO @FechaCur;
    END;
    CLOSE dias_ox;
    DEALLOCATE dias_ox;
    DECLARE dias_su CURSOR LOCAL FAST_FORWARD FOR
        SELECT DISTINCT Fecha FROM #GanadorSuRaw ORDER BY Fecha;
    OPEN dias_su;
    FETCH NEXT FROM dias_su INTO @FechaCur;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @ModCur = NULL; SET @AvanceCur = NULL; SET @CampCur = NULL;
        SELECT TOP (1) @ModCur = modulo_numero, @AvanceCur = avance_porcentaje, @CampCur = campana_nombre
        FROM #GanadorSuRaw
        WHERE Fecha = @FechaCur
          AND (@CampanaPisoSu IS NULL OR campana_nombre <> @CampanaPisoSu OR modulo_numero >= @PisoSu)
        ORDER BY avance_porcentaje ASC, modulo_id DESC;
        IF @ModCur IS NOT NULL
        BEGIN
            INSERT INTO #GanadorSu (Fecha, modulo_numero, avance_porcentaje, campana_nombre)
            VALUES (@FechaCur, @ModCur, @AvanceCur, @CampCur);
            IF @CampanaPisoSu IS NULL OR @CampCur <> @CampanaPisoSu
            BEGIN
                SET @CampanaPisoSu = @CampCur;
                SET @PisoSu = @ModCur;
            END
            ELSE IF @ModCur > @PisoSu
                SET @PisoSu = @ModCur;
        END;
        FETCH NEXT FROM dias_su INTO @FechaCur;
    END;
    CLOSE dias_su;
    DEALLOCATE dias_su;
    SELECT
        f.Fecha, g.modulo_numero, g.avance_porcentaje, g.campana_nombre,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END) OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoOx
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase WHERE pad_id = 1) f
    LEFT JOIN #GanadorOx g ON g.Fecha = f.Fecha;
    SELECT
        Fecha,
        MAX(campana_nombre)    OVER (PARTITION BY grp) AS campana_nombre,
        MAX(modulo_numero)     OVER (PARTITION BY grp) AS modulo_numero,
        MAX(avance_porcentaje) OVER (PARTITION BY grp) AS avance_porcentaje
    INTO #ReclamoOxidosCtx
    FROM #GrupoOx;
    SELECT
        f.Fecha, g.modulo_numero, g.avance_porcentaje, g.campana_nombre,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END) OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoSu
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase WHERE pad_id = 2) f
    LEFT JOIN #GanadorSu g ON g.Fecha = f.Fecha;
    SELECT
        Fecha,
        MAX(campana_nombre)    OVER (PARTITION BY grp) AS campana_nombre,
        MAX(modulo_numero)     OVER (PARTITION BY grp) AS modulo_numero,
        MAX(avance_porcentaje) OVER (PARTITION BY grp) AS avance_porcentaje
    INTO #ReclamoSulfurosCtx
    FROM #GrupoSu;
    DROP TABLE #GanadorOxRaw;
    DROP TABLE #GanadorSuRaw;
    DROP TABLE #GanadorOx;
    DROP TABLE #GanadorSu;
    DROP TABLE #GrupoOx;
    DROP TABLE #GrupoSu;
    CREATE CLUSTERED INDEX ix_ro  ON #ReclamoOxidosTMS(Fecha);
    CREATE CLUSTERED INDEX ix_rs  ON #ReclamoSulfurosTMS(Fecha);
    CREATE CLUSTERED INDEX ix_roc ON #ReclamoOxidosCtx(Fecha);
    CREATE CLUSTERED INDEX ix_rsc ON #ReclamoSulfurosCtx(Fecha);
    PRINT 'PASO 10 Reclamo ctx/TMS  : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';
    /* ================================================================
       PASO 10b: Reclamo Camiones                                v1.13
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoCamionesTMS')  IS NOT NULL DROP TABLE #ReclamoCamionesTMS;
    IF OBJECT_ID('tempdb..#GanadorCamRaw')       IS NOT NULL DROP TABLE #GanadorCamRaw;
    IF OBJECT_ID('tempdb..#GanadorCam')          IS NOT NULL DROP TABLE #GanadorCam;
    IF OBJECT_ID('tempdb..#GrupoCam')            IS NOT NULL DROP TABLE #GrupoCam;
    IF OBJECT_ID('tempdb..#ReclamoCamionesCtx')  IS NOT NULL DROP TABLE #ReclamoCamionesCtx;
    SELECT
        rb.Fecha,
        SUM(CASE WHEN rb.pad_id = 1 THEN rb.tonelaje_camiones_diario ELSE 0 END) AS Camiones_TMS_Reclamo_Oxidos,
        SUM(CASE WHEN rb.pad_id = 2 THEN rb.tonelaje_camiones_diario ELSE 0 END) AS Camiones_TMS_Reclamo_Sulfuros,
        SUM(rb.tonelaje_camiones_diario) AS Camiones_TMS_total
    INTO #ReclamoCamionesTMS
    FROM #ReclamoBase rb
    GROUP BY rb.Fecha;
    CREATE CLUSTERED INDEX ix_rct ON #ReclamoCamionesTMS(Fecha);
    SELECT
        rb.Fecha,
        CAST(rb.modulo_numero AS nvarchar(255))   AS Modulo_reclamo_camiones,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS Campana_reclamo_camiones,
        ROW_NUMBER() OVER (PARTITION BY rb.Fecha ORDER BY rb.tonelaje_camiones_diario DESC, rb.modulo_id DESC) AS rn
    INTO #GanadorCamRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.tonelaje_camiones_diario > 0;
    SELECT Fecha, Modulo_reclamo_camiones, Campana_reclamo_camiones
    INTO #GanadorCam
    FROM #GanadorCamRaw
    WHERE rn = 1;
    SELECT
        f.Fecha, g.Campana_reclamo_camiones, g.Modulo_reclamo_camiones,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END) OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoCam
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase) f
    LEFT JOIN #GanadorCam g ON g.Fecha = f.Fecha;
    SELECT
        Fecha,
        MAX(Campana_reclamo_camiones) OVER (PARTITION BY grp) AS Campana_reclamo_camiones,
        MAX(Modulo_reclamo_camiones)  OVER (PARTITION BY grp) AS Modulo_reclamo_camiones
    INTO #ReclamoCamionesCtx
    FROM #GrupoCam;
    DROP TABLE #GanadorCamRaw;
    DROP TABLE #GanadorCam;
    DROP TABLE #GrupoCam;
    CREATE CLUSTERED INDEX ix_rcc ON #ReclamoCamionesCtx(Fecha);
    PRINT 'PASO 10b Reclamo camiones: ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';
    /* ================================================================
       PASO 11: MERGE final
       Sin cambios respecto de la version validada -- el JOIN contra
       #LeyMinaStock solo usa Fecha y Ley_CuT_Mina_Stock, asi que la
       columna nueva Fuente_Ley_Mina_Stock (PASO 3) no requiere tocar
       nada aqui.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    MERGE [inventar_SpcHidr].[Datos_conciliados_of] AS tgt
    USING
    (
        SELECT
            f.Fecha,
            ch.Chancado_TMS_Real,
            a.Humedad_Turno_A, a.Humedad_Turno_B, a.Humedad_promedio_dia,
            a.Sal_turno_A, a.Sal_Turno_B, a.Sal_promedio_dia,
            CASE
                WHEN a.Apilado_TMH_turno_A IS NULL THEN NULL
                ELSE (a.Apilado_TMH_turno_A + COALESCE(a.Sal_turno_A, 0)) * COALESCE(aj.Factor_Aplicacion_Reportes, 1.0) - COALESCE(a.Sal_turno_A, 0)
            END AS Apilado_TMH_turno_A,
            CASE
                WHEN a.Apilado_TMH_turno_B IS NULL THEN NULL
                ELSE (a.Apilado_TMH_turno_B + COALESCE(a.Sal_turno_B, 0)) * COALESCE(aj.Factor_Aplicacion_Reportes, 1.0) - COALESCE(a.Sal_turno_B, 0)
            END AS Apilado_TMH_turno_B,
            aj.Apilado_TMH_Reporte AS Apilado_TMH_promedio_dia,
            aj.Apilado_TMS_Reporte AS Apilado_TMS_Real,
            g.Apilado_TMS_Plan     AS Apilado_TMS_Plan,
            CASE
                WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion))) IN ('SULFURO','SULFUROS') THEN 'Sulfuro'
                WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion))) IN ('OXIDO','OXIDOS','OXIDO','OXIDOS') THEN 'Oxido'
                ELSE g.Material_Operacion
            END AS Campana_apilado,
            g.Modulo AS Modulo_apilado,
            g.Avance AS Avance_apilado,
            g.CuT_Real_Dia AS Ley_CuT_Real,
            g.CuT_Plan     AS Ley_CuT_Plan,
            CASE
                WHEN COALESCE(aj.Apilado_TMS_Reporte, 0) = 0 THEN 0
                WHEN g.CuT_Real_Dia IS NULL THEN NULL
                ELSE aj.Apilado_TMS_Reporte * g.CuT_Real_Dia / 100.0
            END AS Cobre_fino_Apilado_Real,
            pm.Cobre_Fino_Apilado_Plan_Fuente AS Cobre_fino_Apilado_Plan,
            ro_tms.TMS_Rotopala_1_Real,
            pm.TMS_Rotopala_1_Plan,
            CAST(ro_ctx.campana_nombre    AS nvarchar(255)) AS Campana_reclamo_oxidos,
            CAST(ro_ctx.modulo_numero     AS int)           AS Modulo_reclamo_oxidos,
            CAST(ro_ctx.avance_porcentaje AS float)         AS Avance_reclamo_oxidos,
            rs_tms.TMS_Rotopala_2_Real,
            pm.TMS_Rotopala_2_Plan,
            CAST(rs_ctx.campana_nombre    AS nvarchar(255)) AS Campana_reclamo_sulfuros,
            CAST(rs_ctx.modulo_numero     AS int)           AS modulo_reclamo_sulfuros,
            CAST(rs_ctx.avance_porcentaje AS float)         AS Avance_reclamo_sulfuros,
            rc_tms.Camiones_TMS_Reclamo_Oxidos,
            rc_tms.Camiones_TMS_Reclamo_Sulfuros,
            CAST(NULL AS nvarchar(255)) AS Movido,
            CAST(NULL AS nvarchar(255)) AS Extraido,
            rc_tms.Camiones_TMS_total                              AS Camiones_TMS_total,
            pm.Camiones_TMS_Plan        AS Camiones_TMS_plan,
            rc_ctx.Campana_reclamo_camiones,
            rc_ctx.Modulo_reclamo_camiones,
            CASE
                WHEN rc_tms.Camiones_TMS_total           IS NULL
                  OR ro_tms.TMS_Rotopala_1_Real            IS NULL
                  OR rs_tms.TMS_Rotopala_2_Real            IS NULL
                    THEN NULL
                ELSE rc_tms.Camiones_TMS_total + ro_tms.TMS_Rotopala_1_Real + rs_tms.TMS_Rotopala_2_Real
            END AS Total_Ripios_Incluye_Camiones_Real,
            CASE
                WHEN pm.TMS_Rotopala_1_Plan IS NOT NULL
                 AND pm.TMS_Rotopala_2_Plan IS NOT NULL
                 AND pm.Camiones_TMS_Plan   IS NOT NULL
                THEN CAST(pm.TMS_Rotopala_1_Plan AS float) + CAST(pm.TMS_Rotopala_2_Plan AS float) + CAST(pm.Camiones_TMS_Plan AS float)
                ELSE NULL
            END AS Total_Ripios_Incluye_Camiones_Plan,
            p.Produccion_Catodos_Real,
            pm.Produccion_Catodos_Plan,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Turno_A ELSE NULL END AS SRR_TMS_Turno_A,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Turno_B ELSE NULL END AS SRR_TMS_Turno_B,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Dia ELSE NULL END AS SRR_TMS_promedio_dia,
            pm.SRR_TMS_Plan,
            CASE
                WHEN ISNULL(s.Flag_SRR_TMS_Dia, '') <> 'OK' OR s.SRR_TMS_Dia IS NULL OR s.SRR_TMS_Dia <= 0 THEN NULL
                WHEN g.CuT_Real_Dia IS NULL THEN NULL
                WHEN lms.Ley_CuT_Mina_Stock IS NULL THEN NULL
                WHEN CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1 THEN aj.Apilado_TMS_Bruto_Ajustado ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END IS NULL THEN NULL
                WHEN aj.Sal_TMH_Dia IS NULL THEN NULL
                WHEN aj.Delta_Inventario_Chancado_TMS IS NULL THEN NULL
                WHEN ch.Chancado_TMS_Real IS NULL THEN NULL
                ELSE
                    (
                        g.CuT_Real_Dia
                        * (
                            CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1 THEN aj.Apilado_TMS_Bruto_Ajustado ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END
                            - aj.Sal_TMH_Dia
                            + aj.Delta_Inventario_Chancado_TMS
                          )
                        - (lms.Ley_CuT_Mina_Stock * ch.Chancado_TMS_Real)
                    )
                    / NULLIF(s.SRR_TMS_Dia, 0)
            END AS Ley_CuT_Real_srr,
            pm.Ley_CuT_Plan_SRR AS Ley_CuT_Plan_srr,
            CASE
                WHEN COALESCE(aj.Apilado_TMS_Reporte, 0) > 0 AND g.CuT_Real_Dia IS NULL THEN 2
                WHEN p.Produccion_Catodos_Real IS NULL THEN 1
                ELSE 0
            END AS estado
        FROM #Fechas       f
        LEFT JOIN #Chancado          c      ON c.Fecha      = f.Fecha
        LEFT JOIN #Apilado           a      ON a.Fecha      = f.Fecha
        LEFT JOIN #Generador         g      ON g.Fecha      = f.Fecha
        LEFT JOIN #SRR               s      ON s.Fecha      = f.Fecha
        LEFT JOIN #Catodos           p      ON p.Fecha      = f.Fecha
        LEFT JOIN #Plan              pm     ON pm.Fecha     = f.Fecha
        LEFT JOIN #LeyMinaStock     lms     ON lms.Fecha     = f.Fecha
        LEFT JOIN #ReclamoOxidosTMS  ro_tms ON ro_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoOxidosCtx  ro_ctx ON ro_ctx.Fecha = f.Fecha
        LEFT JOIN #ReclamoSulfurosTMS rs_tms ON rs_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoSulfurosCtx rs_ctx ON rs_ctx.Fecha = f.Fecha
        LEFT JOIN #ReclamoCamionesTMS rc_tms ON rc_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoCamionesCtx rc_ctx ON rc_ctx.Fecha = f.Fecha
        LEFT JOIN [inventar_SpcHidr].[v_ajuste_camiones_emision_test] aj ON aj.Fecha = f.Fecha
        CROSS APPLY
        (
            SELECT CASE
                WHEN aj.Apilado_TMS_Reporte = 0
                 AND aj.Sal_TMH_Dia = 0
                 AND aj.SRR_TMS_Dia = 0
                    THEN 0
                ELSE aj.Chancado_TMS_Reporte
            END AS Chancado_TMS_Real
        ) ch
    ) AS src ON tgt.Fecha = src.Fecha
    WHEN MATCHED THEN UPDATE SET
        Chancado_TMS_Real                  = src.Chancado_TMS_Real,
        Humedad_Turno_A                    = src.Humedad_Turno_A,
        Humedad_Turno_B                    = src.Humedad_Turno_B,
        Humedad_promedio_dia               = src.Humedad_promedio_dia,
        Sal_turno_A                        = src.Sal_turno_A,
        Sal_Turno_B                        = src.Sal_Turno_B,
        Sal_promedio_dia                   = src.Sal_promedio_dia,
        Apilado_TMH_turno_A                = src.Apilado_TMH_turno_A,
        Apilado_TMH_turno_B                = src.Apilado_TMH_turno_B,
        Apilado_TMH_promedio_dia           = src.Apilado_TMH_promedio_dia,
        Apilado_TMS_Real                   = src.Apilado_TMS_Real,
        Apilado_TMS_Plan                   = src.Apilado_TMS_Plan,
        Campana_apilado                    = src.Campana_apilado,
        Modulo_apilado                     = src.Modulo_apilado,
        Avance_apilado                     = src.Avance_apilado,
        Ley_CuT_Real                       = src.Ley_CuT_Real,
        Ley_CuT_Plan                       = src.Ley_CuT_Plan,
        Cobre_fino_Apilado_Real            = src.Cobre_fino_Apilado_Real,
        Cobre_fino_Apilado_Plan            = src.Cobre_fino_Apilado_Plan,
        TMS_Rotopala_1_Real                = src.TMS_Rotopala_1_Real,
        TMS_Rotopala_1_Plan                = src.TMS_Rotopala_1_Plan,
        Campana_reclamo_oxidos             = src.Campana_reclamo_oxidos,
        Modulo_reclamo_oxidos              = src.Modulo_reclamo_oxidos,
        Avance_reclamo_oxidos              = src.Avance_reclamo_oxidos,
        TMS_Rotopala_2_Real                = src.TMS_Rotopala_2_Real,
        TMS_Rotopala_2_Plan                = src.TMS_Rotopala_2_Plan,
        Campana_reclamo_sulfuros           = src.Campana_reclamo_sulfuros,
        modulo_reclamo_sulfuros            = src.modulo_reclamo_sulfuros,
        Avance_reclamo_sulfuros            = src.Avance_reclamo_sulfuros,
        Camiones_TMS_Reclamo_Oxidos        = src.Camiones_TMS_Reclamo_Oxidos,
        Camiones_TMS_Reclamo_Sulfuros      = src.Camiones_TMS_Reclamo_Sulfuros,
        Movido                             = src.Movido,
        Extraido                           = src.Extraido,
        Camiones_TMS_total                 = src.Camiones_TMS_total,
        Camiones_TMS_plan                  = src.Camiones_TMS_plan,
        Campana_reclamo_camiones           = src.Campana_reclamo_camiones,
        Modulo_reclamo_camiones            = src.Modulo_reclamo_camiones,
        Total_Ripios_Incluye_Camiones_Real = src.Total_Ripios_Incluye_Camiones_Real,
        Total_Ripios_Incluye_Camiones_Plan = src.Total_Ripios_Incluye_Camiones_Plan,
        Produccion_Catodos_Real            = src.Produccion_Catodos_Real,
        Produccion_Catodos_Plan            = src.Produccion_Catodos_Plan,
        SRR_TMS_Turno_A                    = src.SRR_TMS_Turno_A,
        SRR_TMS_Turno_B                    = src.SRR_TMS_Turno_B,
        SRR_TMS_promedio_dia               = src.SRR_TMS_promedio_dia,
        SRR_TMS_Plan                       = src.SRR_TMS_Plan,
        Ley_CuT_Real_srr                   = src.Ley_CuT_Real_srr,
        Ley_CuT_Plan_srr                   = src.Ley_CuT_Plan_srr,
        estado                             = src.estado
    WHEN NOT MATCHED BY TARGET THEN INSERT
    (
        Fecha, Chancado_TMS_Real,
        Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia,
        Sal_turno_A, Sal_Turno_B, Sal_promedio_dia,
        Apilado_TMH_turno_A, Apilado_TMH_turno_B, Apilado_TMH_promedio_dia,
        Apilado_TMS_Real, Apilado_TMS_Plan,
        Campana_apilado, Modulo_apilado, Avance_apilado,
        Ley_CuT_Real, Ley_CuT_Plan,
        Cobre_fino_Apilado_Real, Cobre_fino_Apilado_Plan,
        TMS_Rotopala_1_Real, TMS_Rotopala_1_Plan,
        Campana_reclamo_oxidos, Modulo_reclamo_oxidos, Avance_reclamo_oxidos,
        TMS_Rotopala_2_Real, TMS_Rotopala_2_Plan,
        Campana_reclamo_sulfuros, modulo_reclamo_sulfuros, Avance_reclamo_sulfuros,
        Camiones_TMS_Reclamo_Oxidos, Camiones_TMS_Reclamo_Sulfuros,
        Movido, Extraido, Camiones_TMS_total, Camiones_TMS_plan,
        Campana_reclamo_camiones, Modulo_reclamo_camiones,
        Total_Ripios_Incluye_Camiones_Real, Total_Ripios_Incluye_Camiones_Plan,
        Produccion_Catodos_Real, Produccion_Catodos_Plan,
        SRR_TMS_Turno_A, SRR_TMS_Turno_B, SRR_TMS_promedio_dia, SRR_TMS_Plan,
        Ley_CuT_Real_srr, Ley_CuT_Plan_srr, estado
    )
    VALUES
    (
        src.Fecha, src.Chancado_TMS_Real,
        src.Humedad_Turno_A, src.Humedad_Turno_B, src.Humedad_promedio_dia,
        src.Sal_turno_A, src.Sal_Turno_B, src.Sal_promedio_dia,
        src.Apilado_TMH_turno_A, src.Apilado_TMH_turno_B, src.Apilado_TMH_promedio_dia,
        src.Apilado_TMS_Real, src.Apilado_TMS_Plan,
        src.Campana_apilado, src.Modulo_apilado, src.Avance_apilado,
        src.Ley_CuT_Real, src.Ley_CuT_Plan,
        src.Cobre_fino_Apilado_Real, src.Cobre_fino_Apilado_Plan,
        src.TMS_Rotopala_1_Real, src.TMS_Rotopala_1_Plan,
        src.Campana_reclamo_oxidos, src.Modulo_reclamo_oxidos, src.Avance_reclamo_oxidos,
        src.TMS_Rotopala_2_Real, src.TMS_Rotopala_2_Plan,
        src.Campana_reclamo_sulfuros, src.modulo_reclamo_sulfuros, src.Avance_reclamo_sulfuros,
        src.Camiones_TMS_Reclamo_Oxidos, src.Camiones_TMS_Reclamo_Sulfuros,
        src.Movido, src.Extraido, src.Camiones_TMS_total, src.Camiones_TMS_plan,
        src.Campana_reclamo_camiones, src.Modulo_reclamo_camiones,
        src.Total_Ripios_Incluye_Camiones_Real, src.Total_Ripios_Incluye_Camiones_Plan,
        src.Produccion_Catodos_Real, src.Produccion_Catodos_Plan,
        src.SRR_TMS_Turno_A, src.SRR_TMS_Turno_B, src.SRR_TMS_promedio_dia, src.SRR_TMS_Plan,
        src.Ley_CuT_Real_srr, src.Ley_CuT_Plan_srr, src.estado
    );
    PRINT 'PASO 11 MERGE            : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - '
        + CAST(@@ROWCOUNT AS varchar) + ' filas afectadas';
    PRINT '-- TOTAL                 : ' + CAST(DATEDIFF(ms,@t0,SYSDATETIME()) AS varchar) + ' ms';
    DROP TABLE IF EXISTS #Fechas;
    DROP TABLE IF EXISTS #Chancado;
    DROP TABLE IF EXISTS #ChancadoMovCam;
    DROP TABLE IF EXISTS #ChancadoImpCsv;
    DROP TABLE IF EXISTS #LeyMinaStock;
    DROP TABLE IF EXISTS #LeyMinaStockMovCam;
    DROP TABLE IF EXISTS #LeyMinaStockImpCsv;
    DROP TABLE IF EXISTS #Apilado;
    DROP TABLE IF EXISTS #Generador;
    DROP TABLE IF EXISTS #SRR;
    DROP TABLE IF EXISTS #Catodos;
    DROP TABLE IF EXISTS #Plan;
    DROP TABLE IF EXISTS #ReclamoBase;
    DROP TABLE IF EXISTS #ReclamoOxidosTMS;
    DROP TABLE IF EXISTS #ReclamoSulfurosTMS;
    DROP TABLE IF EXISTS #ReclamoOxidosCtx;
    DROP TABLE IF EXISTS #ReclamoSulfurosCtx;
    DROP TABLE IF EXISTS #ReclamoCamionesTMS;
    DROP TABLE IF EXISTS #ReclamoCamionesCtx;
    EXEC sys.sp_set_session_context @key = N'fecha_corte_camiones', @value = NULL;
    END TRY
    BEGIN CATCH
        EXEC sys.sp_set_session_context @key = N'fecha_corte_camiones', @value = NULL;
        THROW;
    END CATCH
END;
