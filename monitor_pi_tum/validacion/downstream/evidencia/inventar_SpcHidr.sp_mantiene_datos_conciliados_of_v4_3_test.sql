
CREATE   PROCEDURE [inventar_SpcHidr].[sp_mantiene_datos_conciliados_of_v4_3_test]
(
    @FechaInicio   date,
    @FechaFin      date,
    @DiasReproceso int = 7
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

    SELECT
        @FechaCorteCamiones = MAX(CAST(cr.[fecha] AS date))
    FROM [inventar_SpcHidr].[control_reclamo_sulfuro_camiones_thm_diario] cr
    WHERE CAST(cr.[fecha] AS date) >= @InicioMesCorte
      AND CAST(cr.[fecha] AS date) <= @FechaFin;

    IF @FechaCorteCamiones IS NULL
        THROW 52001,
              'No existe informacion de camiones para resolver el corte dinamico del periodo.',
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
    DECLARE @t0 datetime2        = SYSDATETIME();
    DECLARE @t1 datetime2;

    PRINT '-- INICIO: ' + CONVERT(varchar, @t0, 121);
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
    PRINT 'PASO 1  Calendario       : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 2: Chancado TMH
       Fuente : mov_cam, Fase != SRR, campo Tonelaje_Hum_CIO
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Chancado') IS NOT NULL DROP TABLE #Chancado;
    SELECT
        CAST(Fecha AS date)                AS Fecha,
        SUM(COALESCE(Tonelaje_Hum_CIO,0))  AS Chancado_TMH_Dia
    INTO #Chancado
    FROM [inventar_SpcHidr].[mov_cam]
    WHERE Fase NOT LIKE '%SRR%'
      AND CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin
    GROUP BY CAST(Fecha AS date);
    CREATE CLUSTERED INDEX ix_ch ON #Chancado(Fecha);
    PRINT 'PASO 2  Chancado         : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 3: Ley CuT SRR
       Fuente : mov_cam, Fase = SRR
       Metodo : promedio ponderado SUM(Ton * CuTG00) / SUM(Ton)
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#LeySrr') IS NOT NULL DROP TABLE #LeySrr;
    SELECT
        CAST(Fecha AS date) AS Fecha,
        CASE
            WHEN SUM(Ton) IS NULL OR SUM(Ton) = 0 THEN NULL
            ELSE SUM(Ton * CuTG00) / SUM(Ton)
        END AS Ley_CuT_Real_srr
    INTO #LeySrr
    FROM [inventar_SpcHidr].[mov_cam]
    WHERE Fase = 'SRR'
      AND CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin
    GROUP BY CAST(Fecha AS date);
    CREATE CLUSTERED INDEX ix_ls ON #LeySrr(Fecha);
    PRINT 'PASO 3  Ley CuT SRR      : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 4: Humedad / Sal / Apilado TMH
       Fuente : [inventar_SpcHidr].[Historico_Apilado_Diario]  (TABLA)
                Reemplaza a v_reporte_diario_apilado_test a partir de v1.6.
                La vista en vivo mide 67.3 s para rangos que cruzan el
                hueco de datos de junio 2026; la tabla mide ~0.2 s.
                Se mantiene con sp_refrescar_historico_apilado_test.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Apilado') IS NOT NULL DROP TABLE #Apilado;
    SELECT
        CAST(Fecha AS date)      AS Fecha,
        Humedad_Turno_A,
        Humedad_Turno_B,
        Humedad_promedio_dia,
        Sal_turno_A,
        Sal_Turno_B,
        Sal_promedio_dia,
        Apilado_TMH_turno_A,
        Apilado_TMH_turno_B,
        Apilado_TMH_promedio_dia
    INTO #Apilado
    FROM [inventar_SpcHidr].[Historico_Apilado_Diario]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_ap ON #Apilado(Fecha);
    PRINT 'PASO 4  Apilado/Humedad  : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 5: Generador diario
       Fuente : [inventar_SpcHidr].[fn_generador_reporte_diario](@fecha_inicio, @fecha_fin)
                (FUNCION TVF). Lee directo de reporte_turno_cache y agrega
                a grano diario internamente. Desde v1.9 reemplaza a la
                tabla cache Historico_Generador_Reporte (que no tenia SP
                de refresco propio).
       Columnas usadas mas abajo en el MERGE (se mantienen los mismos
       nombres de salida que en versiones anteriores; no se trae el
       resto de columnas de la funcion -Solubilidad, CO3, CuFe, Mallas,
       Dosis Acido, etc.- por no ser parte de la definicion original
       del reporte):
           Apilado_TMS_Real_Dia, Apilado_TMS_Plan,
           CuT_Real_Dia,         CuT_Plan,
           Material_Operacion,   Modulo, Avance
       NOTA: se usa @FechaInicioProceso/@FechaFinExclusiva (limite
       superior EXCLUSIVO), tal como espera la funcion.
       ADVERTENCIA DE RENDIMIENTO: v1.5 habia movido este PASO a una
       tabla cache. Revisar el tiempo impreso abajo; si sube de forma
       notoria respecto a los ~0.2 s previos, evaluar volver a
       Historico_Generador_Reporte con un refresco propio.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Generador') IS NOT NULL DROP TABLE #Generador;
    SELECT
        g.Fecha,
        g.Apilado_TMS_Real_Dia,
        g.Apilado_TMS_Plan,
        g.Material_Operacion,
        g.Modulo,
        g.Avance,
        g.CuT_Real_Dia,
        g.CuT_Plan
    INTO #Generador
    FROM [inventar_SpcHidr].[fn_generador_reporte_diario](@FechaInicioProceso, @FechaFinExclusiva) g;
    CREATE CLUSTERED INDEX ix_gen ON #Generador(Fecha);
    PRINT 'PASO 5  Generador diario : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 6: SRR diario
       Fuente : [inventar_SpcHidr].[reporte_turno_cache]  (TABLA origen,
                grano Fecha + Turno), columnas SRR y Apilado_TMS_Real.
                Confirmada via EXEC sp_help (2026-07-24).
       CAMBIO DE METODOLOGIA v1.9 (decision expresa del usuario): deja de
       usar Historico_SRR_Diario (CV001 corregido,
       CV001_CORREGIDO_50_50_HUMEDAD_DIARIA_POR_TORRE), que hasta esta
       version era la metodologia provisional vigente documentada como
       aprobada por jefatura.
       CORRECCION v1.10 (misma fecha, misma sesion): la columna SRR de
       reporte_turno_cache es un PORCENTAJE del apilado del turno, no un
       TMS directo (mismo patron que CuT_Real/CuS_Real: ver
       Cobre_fino_Apilado_Real mas abajo, que tambien divide por 100).
       Formula aplicada por turno:
           SRR_TMS_Turno = Apilado_TMS_Real_Turno * SRR_Turno / 100.0
       y se totaliza (SUM) por Fecha para obtener SRR_TMS_Dia.
       PENDIENTE: validar numericamente el SRR_TMS_Dia resultante contra
       el historico oficial antes de dar esta fuente por cerrada, y
       confirmar que la division por 100 es correcta (SRR en escala
       0-100 y no ya como fraccion 0-1).
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
        FROM [inventar_SpcHidr].[reporte_turno_cache]
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
    PRINT 'PASO 6  SRR              : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 7: Produccion catodica
       Fuente : v_produccion_catodica_diaria_test
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
    PRINT 'PASO 7  Catodos          : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 8: Plan mensual
       Fuente : v_planes_mensuales_diarios_test
       Columnas verificadas (posiciones reales):
           Ley_CuT_Plan_Fuente (3)              -- NO es Ley_CuT_Plan
           Cobre_Fino_Apilado_Plan_Fuente (4)   -- NO es Cobre_fino_Apilado_Plan
           TMS_Rotopala_1_Plan (5), TMS_Rotopala_2_Plan (6)
           Camiones_TMS_Plan (7), Produccion_Catodos_Plan (8)
           SRR_TMS_Plan (9), Ley_CuT_Plan_SRR (10)
       NOTA: Apilado_TMS_Plan NO existe en esta vista -> viene de #Generador
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Plan') IS NOT NULL DROP TABLE #Plan;
    SELECT
        CAST(Fecha AS date)             AS Fecha,
        Ley_CuT_Plan_Fuente,            -- nombre real confirmado
        Cobre_Fino_Apilado_Plan_Fuente, -- nombre real confirmado
        TMS_Rotopala_1_Plan,
        TMS_Rotopala_2_Plan,
        Camiones_TMS_Plan,
        Produccion_Catodos_Plan,
        SRR_TMS_Plan,
        Ley_CuT_Plan_SRR
    INTO #Plan
    FROM [inventar_SpcHidr].[v_planes_mensuales_diarios_test]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_pm ON #Plan(Fecha);
    PRINT 'PASO 8  Plan mensual     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 9: Reclamo base
       Fuente : vista_reclamo_diario_calculado
       Fecha  : fecha_operacion (ya desplazada -1 dia en la vista)
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoBase') IS NOT NULL DROP TABLE #ReclamoBase;
    SELECT
        fecha_operacion           AS Fecha,
        pad_id,
        [campaña_id],
        modulo_id,
        avance_porcentaje,
        tonelaje_reclamado_diario
    INTO #ReclamoBase
    FROM [inventar_SpcHidr].[vista_reclamo_diario_calculado_v4_3_corte_dinamico_test]
    WHERE fecha_operacion >= @FechaInicioProceso
      AND fecha_operacion <= @FechaFin;
    CREATE CLUSTERED INDEX ix_rb ON #ReclamoBase(Fecha, pad_id);
    PRINT 'PASO 9  Reclamo base     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@@ROWCOUNT AS varchar) + ' filas';

    /* ================================================================
       PASO 10: Reclamo TMS y contexto por pad
       PAD 1 = oxido  -> TMS_Rotopala_1_Real, Campana/Modulo/Avance oxidos
       PAD 2 = sulfuro -> TMS_Rotopala_2_Real, Campana/Modulo/Avance sulfuros
       Contexto: modulo/avance del dia con reclamo real (tonelaje > 0),
       con LOCF (last-observation-carried-forward) en dias sin tonelaje.
       Se publica el numero de modulo operacional (tabla [modulo].numero),
       no el id_modulo interno. Ver v1.7 en el encabezado para el detalle
       de los 3 bugs corregidos.
       Escrito con tablas temporales fisicas paso a paso (no CTEs
       anidadas) para maxima compatibilidad con clientes ODBC/FreeTDS y
       para poder inspeccionar cada paso con SELECT * FROM #Tabla.
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

    -- TMS por pad
    SELECT Fecha, SUM(tonelaje_reclamado_diario) AS TMS_Rotopala_1_Real
    INTO #ReclamoOxidosTMS  FROM #ReclamoBase WHERE pad_id = 1 GROUP BY Fecha;

    SELECT Fecha, SUM(tonelaje_reclamado_diario) AS TMS_Rotopala_2_Real
    INTO #ReclamoSulfurosTMS FROM #ReclamoBase WHERE pad_id = 2 GROUP BY Fecha;

    -- Contexto oxidos (pad 1): candidatos del dia con reclamo real,
    -- ordenados por tonelaje (desempate por modulo_id, el mas reciente)
    SELECT
        rb.Fecha,
        rb.modulo_id,
        md.numero                                 AS modulo_numero,
        rb.avance_porcentaje,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
        ROW_NUMBER() OVER (
            PARTITION BY rb.Fecha
            ORDER BY rb.tonelaje_reclamado_diario DESC, rb.modulo_id DESC
        ) AS rn
    INTO #GanadorOxRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c
        ON c.[id_campaña] = rb.[campaña_id]
    LEFT JOIN [inventar_SpcHidr].[modulo] md
        ON md.[id_modulo] = rb.[modulo_id]
    WHERE rb.pad_id = 1
      AND rb.tonelaje_reclamado_diario > 0;

    -- Ganador del dia (pad 1)
    SELECT Fecha, modulo_numero, avance_porcentaje, campana_nombre
    INTO #GanadorOx
    FROM #GanadorOxRaw
    WHERE rn = 1;

    -- LOCF: arrastra el ultimo ganador valido a los dias sin reclamo
    SELECT
        f.Fecha,
        g.modulo_numero,
        g.avance_porcentaje,
        g.campana_nombre,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END)
            OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoOx
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase WHERE pad_id = 1) f
    LEFT JOIN #GanadorOx g
        ON g.Fecha = f.Fecha;

    SELECT
        Fecha,
        MAX(campana_nombre)    OVER (PARTITION BY grp) AS campana_nombre,
        MAX(modulo_numero)     OVER (PARTITION BY grp) AS modulo_numero,
        MAX(avance_porcentaje) OVER (PARTITION BY grp) AS avance_porcentaje
    INTO #ReclamoOxidosCtx
    FROM #GrupoOx;

    -- Contexto sulfuros (pad 2): misma logica que oxidos
    SELECT
        rb.Fecha,
        rb.modulo_id,
        md.numero                                 AS modulo_numero,
        rb.avance_porcentaje,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
        ROW_NUMBER() OVER (
            PARTITION BY rb.Fecha
            ORDER BY rb.tonelaje_reclamado_diario DESC, rb.modulo_id DESC
        ) AS rn
    INTO #GanadorSuRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c
        ON c.[id_campaña] = rb.[campaña_id]
    LEFT JOIN [inventar_SpcHidr].[modulo] md
        ON md.[id_modulo] = rb.[modulo_id]
    WHERE rb.pad_id = 2
      AND rb.tonelaje_reclamado_diario > 0;

    SELECT Fecha, modulo_numero, avance_porcentaje, campana_nombre
    INTO #GanadorSu
    FROM #GanadorSuRaw
    WHERE rn = 1;

    SELECT
        f.Fecha,
        g.modulo_numero,
        g.avance_porcentaje,
        g.campana_nombre,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END)
            OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoSu
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase WHERE pad_id = 2) f
    LEFT JOIN #GanadorSu g
        ON g.Fecha = f.Fecha;

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
       PASO 10b: Reclamo Camiones Sulfuros
       Fuente : inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario
                INNER JOIN inventar_SpcHidr.disponible_rotopalas
                ON campaña_id + modulo_id.
       Formula: Ton_reclamo = volumen_diario_m3 * densidad
       Grano  : puede existir mas de una fila por fecha (distinta campaña
                / modulo el mismo dia). Se suma Ton_reclamo por fecha
                para Camiones_TMS_Reclamo_Sulfuros y se aplica el mismo
                criterio de "ganador del dia" (mayor Ton_reclamo) + LOCF
                en dias sin reclamo, igual metodologia que PASO 10, para
                no introducir filas duplicadas por Fecha en el MERGE.
       Camiones_TMS_total = Camiones_TMS_Reclamo_Sulfuros. No se inventa
                Camiones_TMS_Reclamo_Oxidos: sigue pendiente.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoCamionesBase') IS NOT NULL DROP TABLE #ReclamoCamionesBase;
    IF OBJECT_ID('tempdb..#ReclamoCamionesTMS')  IS NOT NULL DROP TABLE #ReclamoCamionesTMS;
    IF OBJECT_ID('tempdb..#GanadorCamRaw')       IS NOT NULL DROP TABLE #GanadorCamRaw;
    IF OBJECT_ID('tempdb..#GanadorCam')          IS NOT NULL DROP TABLE #GanadorCam;
    IF OBJECT_ID('tempdb..#GrupoCam')            IS NOT NULL DROP TABLE #GrupoCam;
    IF OBJECT_ID('tempdb..#ReclamoCamionesCtx')  IS NOT NULL DROP TABLE #ReclamoCamionesCtx;

    SELECT
        CAST(crc.fecha AS date)                    AS Fecha,
        CAST(crc.[campaña] AS nvarchar(255))       AS Campana_reclamo_camiones,
        CAST(crc.modulo AS nvarchar(255))          AS Modulo_reclamo_camiones,
        crc.[campaña_id],
        crc.modulo_id,
        crc.volumen_diario_m3,
        dr.densidad,
        crc.volumen_diario_m3 * dr.densidad        AS Ton_reclamo
    INTO #ReclamoCamionesBase
    FROM [inventar_SpcHidr].[control_reclamo_sulfuro_camiones_thm_diario] crc
    INNER JOIN [inventar_SpcHidr].[disponible_rotopalas] dr
        ON  crc.[campaña_id] = dr.[campaña_id]
        AND crc.modulo_id    = dr.modulo_id
    WHERE CAST(crc.fecha AS date) >= @FechaInicioProceso
      AND CAST(crc.fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_rcb ON #ReclamoCamionesBase(Fecha);

    -- Total diario: suma de todas las filas (campaña/modulo) de la fecha
    SELECT Fecha, SUM(Ton_reclamo) AS Camiones_TMS_Reclamo_Sulfuros
    INTO #ReclamoCamionesTMS
    FROM #ReclamoCamionesBase
    GROUP BY Fecha;
    CREATE CLUSTERED INDEX ix_rct ON #ReclamoCamionesTMS(Fecha);

    -- Ganador del dia: mayor Ton_reclamo (desempate por modulo_id DESC),
    -- solo entre filas con Ton_reclamo > 0, igual criterio que PASO 10.
    SELECT
        Fecha,
        Modulo_reclamo_camiones,
        Campana_reclamo_camiones,
        ROW_NUMBER() OVER (
            PARTITION BY Fecha
            ORDER BY Ton_reclamo DESC, modulo_id DESC
        ) AS rn
    INTO #GanadorCamRaw
    FROM #ReclamoCamionesBase
    WHERE Ton_reclamo > 0;

    SELECT Fecha, Modulo_reclamo_camiones, Campana_reclamo_camiones
    INTO #GanadorCam
    FROM #GanadorCamRaw
    WHERE rn = 1;

    -- LOCF: en dias sin ganador (sin Ton_reclamo > 0) se mantiene el
    -- ultimo contexto valido dentro del rango procesado.
    SELECT
        f.Fecha,
        g.Campana_reclamo_camiones,
        g.Modulo_reclamo_camiones,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END)
            OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoCam
    FROM (SELECT DISTINCT Fecha FROM #ReclamoCamionesBase) f
    LEFT JOIN #GanadorCam g
        ON g.Fecha = f.Fecha;

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
       Todas las fuentes ya materializadas en temp tables -> joins simples
    ================================================================ */
    SET @t1 = SYSDATETIME();

    MERGE [inventar_SpcHidr].[Datos_conciliados_of_v4_3_test] AS tgt
    USING
    (
        SELECT
            f.Fecha,

            /* -- CHANCADO TMS
               TMH (mov_cam) * (1 - humedad / 100)
               Humedad desde #Apilado (Historico_Apilado_Diario) */
            CASE
                WHEN c.Chancado_TMH_Dia IS NULL    THEN NULL
                WHEN a.Humedad_promedio_dia IS NULL THEN NULL
                ELSE c.Chancado_TMH_Dia * (1.0 - a.Humedad_promedio_dia / 100.0)
            END AS Chancado_TMS_Real,

            /* -- HUMEDAD */
            a.Humedad_Turno_A,
            a.Humedad_Turno_B,
            a.Humedad_promedio_dia,

            /* -- SAL */
            a.Sal_turno_A,
            a.Sal_Turno_B,
            a.Sal_promedio_dia,

            /* -- APILADO TMH */
            a.Apilado_TMH_turno_A,
            a.Apilado_TMH_turno_B,
            a.Apilado_TMH_promedio_dia,

            /* -- APILADO TMS (fn_generador_reporte_diario, neto de sal) */
            g.Apilado_TMS_Real_Dia AS Apilado_TMS_Real,
            g.Apilado_TMS_Plan     AS Apilado_TMS_Plan,

            /* -- CONTEXTO OPERACIONAL APILADO */
            CASE
                WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion))) IN ('SULFURO','SULFUROS') THEN 'Sulfuro'
                WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion))) IN ('OXIDO','OXIDOS','OXIDO','OXIDOS') THEN 'Oxido'
                ELSE g.Material_Operacion
            END AS Campana_apilado,
            g.Modulo AS Modulo_apilado,
            g.Avance AS Avance_apilado,

            /* -- LEY CuT APILADO (fn_generador_reporte_diario) */
            g.CuT_Real_Dia AS Ley_CuT_Real,
            g.CuT_Plan     AS Ley_CuT_Plan,

            /* -- COBRE FINO APILADO
               Real : calculado desde fn_generador_reporte_diario
               Plan : desde v_planes_mensuales_diarios_test (Cobre_Fino_Apilado_Plan_Fuente) */
            CASE
                WHEN COALESCE(g.Apilado_TMS_Real_Dia, 0) = 0 THEN 0
                WHEN g.CuT_Real_Dia IS NULL                   THEN NULL
                ELSE g.Apilado_TMS_Real_Dia * g.CuT_Real_Dia / 100.0
            END AS Cobre_fino_Apilado_Real,
            pm.Cobre_Fino_Apilado_Plan_Fuente AS Cobre_fino_Apilado_Plan,

            /* -- RECLAMO OXIDOS (pad 1) */
            ro_tms.TMS_Rotopala_1_Real,
            pm.TMS_Rotopala_1_Plan,
            CAST(ro_ctx.campana_nombre    AS nvarchar(255)) AS Campana_reclamo_oxidos,
            CAST(ro_ctx.modulo_numero     AS int)           AS Modulo_reclamo_oxidos,
            CAST(ro_ctx.avance_porcentaje AS float)         AS Avance_reclamo_oxidos,

            /* -- RECLAMO SULFUROS (pad 2) */
            rs_tms.TMS_Rotopala_2_Real,
            pm.TMS_Rotopala_2_Plan,
            CAST(rs_ctx.campana_nombre    AS nvarchar(255)) AS Campana_reclamo_sulfuros,
            CAST(rs_ctx.modulo_numero     AS int)           AS modulo_reclamo_sulfuros,
            CAST(rs_ctx.avance_porcentaje AS float)         AS Avance_reclamo_sulfuros,

            /* -- CAMIONES
               Oxidos / Movido / Extraido: pendiente, sin fuente identificada.
               Sulfuros / total / contexto: PASO 10b, control_reclamo_sulfuro_
               camiones_thm_diario x disponible_rotopalas. */
            CAST(NULL AS float)         AS Camiones_TMS_Reclamo_Oxidos,
            rc_tms.Camiones_TMS_Reclamo_Sulfuros,
            CAST(NULL AS nvarchar(255)) AS Movido,
            CAST(NULL AS nvarchar(255)) AS Extraido,
            rc_tms.Camiones_TMS_Reclamo_Sulfuros                  AS Camiones_TMS_total,
            pm.Camiones_TMS_Plan        AS Camiones_TMS_plan,
            rc_ctx.Campana_reclamo_camiones,
            rc_ctx.Modulo_reclamo_camiones,

            /* -- RIPIOS */
            CASE
                WHEN rc_tms.Camiones_TMS_Reclamo_Sulfuros IS NULL
                  OR ro_tms.TMS_Rotopala_1_Real            IS NULL
                  OR rs_tms.TMS_Rotopala_2_Real            IS NULL
                    THEN NULL
                ELSE
                    rc_tms.Camiones_TMS_Reclamo_Sulfuros
                    + ro_tms.TMS_Rotopala_1_Real
                    + rs_tms.TMS_Rotopala_2_Real
            END AS Total_Ripios_Incluye_Camiones_Real,
            CASE
                WHEN pm.TMS_Rotopala_1_Plan IS NOT NULL
                 AND pm.TMS_Rotopala_2_Plan IS NOT NULL
                 AND pm.Camiones_TMS_Plan   IS NOT NULL
                THEN CAST(pm.TMS_Rotopala_1_Plan AS float)
                   + CAST(pm.TMS_Rotopala_2_Plan AS float)
                   + CAST(pm.Camiones_TMS_Plan   AS float)
                ELSE NULL
            END AS Total_Ripios_Incluye_Camiones_Plan,

            /* -- PRODUCCION CATODICA */
            p.Produccion_Catodos_Real,
            pm.Produccion_Catodos_Plan,

            /* -- SRR (CV001 corregido, solo cuando Flag = OK) */
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Turno_A ELSE NULL END AS SRR_TMS_Turno_A,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Turno_B ELSE NULL END AS SRR_TMS_Turno_B,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Dia      ELSE NULL END AS SRR_TMS_promedio_dia,
            pm.SRR_TMS_Plan,

            /* -- LEY CuT SRR */
            ls.Ley_CuT_Real_srr,
            pm.Ley_CuT_Plan_SRR AS Ley_CuT_Plan_srr,

            /* -- ESTADO
               0 = completo | 1 = sin catodos | 2 = apilado sin ley */
            CASE
                WHEN COALESCE(g.Apilado_TMS_Real_Dia, 0) > 0
                 AND g.CuT_Real_Dia IS NULL THEN 2
                WHEN p.Produccion_Catodos_Real IS NULL    THEN 1
                ELSE 0
            END AS estado

        FROM #Fechas       f
        LEFT JOIN #Chancado          c      ON c.Fecha      = f.Fecha
        LEFT JOIN #Apilado           a      ON a.Fecha      = f.Fecha
        LEFT JOIN #Generador         g      ON g.Fecha      = f.Fecha
        LEFT JOIN #SRR               s      ON s.Fecha      = f.Fecha
        LEFT JOIN #Catodos           p      ON p.Fecha      = f.Fecha
        LEFT JOIN #Plan              pm     ON pm.Fecha     = f.Fecha
        LEFT JOIN #LeySrr            ls     ON ls.Fecha     = f.Fecha
        LEFT JOIN #ReclamoOxidosTMS  ro_tms ON ro_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoOxidosCtx  ro_ctx ON ro_ctx.Fecha = f.Fecha
        LEFT JOIN #ReclamoSulfurosTMS rs_tms ON rs_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoSulfurosCtx rs_ctx ON rs_ctx.Fecha = f.Fecha
        LEFT JOIN #ReclamoCamionesTMS rc_tms ON rc_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoCamionesCtx rc_ctx ON rc_ctx.Fecha = f.Fecha
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

    PRINT 'PASO 11 MERGE            : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — '
        + CAST(@@ROWCOUNT AS varchar) + ' filas afectadas';
    PRINT '-- TOTAL                 : ' + CAST(DATEDIFF(ms,@t0,SYSDATETIME()) AS varchar) + ' ms';

    /* Limpieza */
    DROP TABLE IF EXISTS #Fechas;
    DROP TABLE IF EXISTS #Chancado;
    DROP TABLE IF EXISTS #LeySrr;
    DROP TABLE IF EXISTS #Apilado;
    DROP TABLE IF EXISTS #Generador;
    DROP TABLE IF EXISTS #SRR;
    DROP TABLE IF EXISTS #Catodos;
    DROP TABLE IF EXISTS #Plan;
    DROP TABLE IF EXISTS #ReclamoBase;
    DROP TABLE IF EXISTS #ReclamoOxidosTMS;
    DROP TABLE IF EXISTS #ReclamoSulfurosTMS;
    DROP TABLE IF EXISTS #GanadorOxRaw;
    DROP TABLE IF EXISTS #GanadorSuRaw;
    DROP TABLE IF EXISTS #GanadorOx;
    DROP TABLE IF EXISTS #GanadorSu;
    DROP TABLE IF EXISTS #GrupoOx;
    DROP TABLE IF EXISTS #GrupoSu;
    DROP TABLE IF EXISTS #ReclamoOxidosCtx;
    DROP TABLE IF EXISTS #ReclamoSulfurosCtx;
    DROP TABLE IF EXISTS #ReclamoCamionesBase;
    DROP TABLE IF EXISTS #ReclamoCamionesTMS;
    DROP TABLE IF EXISTS #ReclamoCamionesCtx;

    /* Limpiar el contexto aun cuando la ejecucion termine correctamente. */
    EXEC sys.sp_set_session_context
        @key   = N'fecha_corte_camiones',
        @value = NULL;

    END TRY
    BEGIN CATCH

        /* Evita que el pool de conexiones reutilice un corte antiguo. */
        EXEC sys.sp_set_session_context
            @key   = N'fecha_corte_camiones',
            @value = NULL;

        THROW;

    END CATCH
END;

