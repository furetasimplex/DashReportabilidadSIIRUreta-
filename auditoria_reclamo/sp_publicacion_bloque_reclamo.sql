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
       