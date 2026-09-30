/*
================================================================================
  PROCEDIMIENTO : inventar_SpcHidr.sp_mantiene_datos_conciliados_of_v2_ajustado_test
  DESCRIPCION   : Copia (segunda fase) de sp_mantiene_datos_conciliados_of
                  que aplica el factor de ajuste por camiones (Control_
                  Factor_Ajuste_Camiones) al Apilado humedo y recalcula
                  las columnas dependientes usando la humedad del dia.
                  Escribe en una tabla ALTERNATIVA (Datos_conciliados_of_
                  ajustado_test), nunca en la tabla productiva
                  Datos_conciliados_of. Toda la logica de PASO 1 a PASO 10
                  es identica al SP productivo (mismas fuentes ya validadas);
                  solo cambia el PASO de Apilado (se agrega #Factor) y el
                  MERGE final.

  PARAMETRO NUEVO:
      @MetodoFactorAjuste char(1) = 'A' | 'B'
          'A' = Opcion A (redistribucion, igual al Excel). El Apilado_TMS_Real
                oficial de esta tabla NO cambia respecto al SP productivo;
                el factor solo se deja como columna de control/diagnostico
                (Factor_Carga_KOM/CAT_TMH_Viaje vs limites 380/265).
          'B' = Opcion B (correccion directa). Apilado_TMH_promedio_dia y
                Apilado_TMS_Real de esta tabla SE RECALCULAN aplicando el
                factor de ajuste y la humedad del dia. Cobre_fino_Apilado_Real
                se recalcula en consecuencia.
      En ambos casos la tabla deja SIEMPRE guardados los valores originales
      (Apilado_TMH_promedio_dia_Original, Apilado_TMS_Real_Original) y los
      de la Opcion B (Apilado_TMH_promedio_dia_OpcionB, Apilado_TMS_Real_
      OpcionB) para poder comparar ambos metodos sin volver a ejecutar nada.

  PRERREQUISITO: Control_Factor_Ajuste_Camiones debe estar poblada para el
  rango de fechas (ejecutar antes sp_mantiene_factor_ajuste_camiones_test).

  HISTORIAL:
      v1.0 - Version inicial, copia de sp_mantiene_datos_conciliados_of v1.6
             + integracion del factor de ajuste por camiones.
================================================================================
*/
CREATE   PROCEDURE [inventar_SpcHidr].[sp_mantiene_datos_conciliados_of_v2_ajustado_test]
(
    @FechaInicio         date,
    @FechaFin            date,
    @DiasReproceso       int     = 7,
    @MetodoFactorAjuste  char(1) = 'A'
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;
    IF @MetodoFactorAjuste NOT IN ('A','B')
        THROW 50003, 'Metodo invalido. Use A (redistribucion) o B (correccion directa apilado).', 1;

    DECLARE @FechaInicioProceso date =
        CASE
            WHEN DATEADD(DAY, -@DiasReproceso, @FechaFin) < @FechaInicio
                THEN DATEADD(DAY, -@DiasReproceso, @FechaFin)
            ELSE @FechaInicio
        END;

    DECLARE @t0 datetime2 = SYSDATETIME();
    DECLARE @t1 datetime2;

    PRINT '-- INICIO: ' + CONVERT(varchar, @t0, 121) + ' -- Metodo: ' + @MetodoFactorAjuste;
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
    PRINT 'PASO 1  Calendario       : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 2: Chancado TMH (identico al SP productivo)
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
    PRINT 'PASO 2  Chancado         : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 3: Ley CuT SRR (identico al SP productivo)
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
    PRINT 'PASO 3  Ley CuT SRR      : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 4: Humedad / Sal / Apilado TMH (identico al SP productivo)
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
    PRINT 'PASO 4  Apilado/Humedad  : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 4b: Factor de ajuste por camiones (NUEVO)
       Fuente : Control_Factor_Ajuste_Camiones, poblada previamente por
                sp_mantiene_factor_ajuste_camiones_test.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Factor') IS NOT NULL DROP TABLE #Factor;
    SELECT
        CAST(Fecha AS date) AS Fecha,
        Factor_Ajuste,
        Flag_Factor_Ajuste,
        Factor_Carga_KOM_TMH_Viaje,
        Factor_Carga_CAT_TMH_Viaje,
        Flag_Factor_Carga_KOM,
        Flag_Factor_Carga_CAT,
        Apilado_TMH_Ajustado_OpcionB,
        Apilado_TMS_Ajustado_OpcionB
    INTO #Factor
    FROM [inventar_SpcHidr].[Control_Factor_Ajuste_Camiones]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_fa ON #Factor(Fecha);
    PRINT 'PASO 4b Factor camiones  : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 5: Generador diario (identico al SP productivo)
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Generador') IS NOT NULL DROP TABLE #Generador;
    SELECT
        CAST(Fecha AS date)  AS Fecha,
        Apilado_TMS_Real_Dia,
        Apilado_TMS_Plan,
        Material_Operacion,
        Modulo,
        Avance,
        CuT_Real_Dia,
        CuT_Plan
    INTO #Generador
    FROM [inventar_SpcHidr].[Historico_Generador_Reporte]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_gen ON #Generador(Fecha);
    PRINT 'PASO 5  Generador diario : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 6: SRR diario (identico al SP productivo)
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#SRR') IS NOT NULL DROP TABLE #SRR;
    SELECT
        CAST(Fecha AS date) AS Fecha,
        SRR_TMS_Turno_A,
        SRR_TMS_Turno_B,
        SRR_TMS_Dia,
        Flag_SRR_TMS_Dia
    INTO #SRR
    FROM [inventar_SpcHidr].[Historico_SRR_Diario]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_srr ON #SRR(Fecha);
    PRINT 'PASO 6  SRR              : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 7: Produccion catodica (identico al SP productivo)
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
    PRINT 'PASO 7  Catodos          : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 8: Plan mensual (identico al SP productivo)
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Plan') IS NOT NULL DROP TABLE #Plan;
    SELECT
        CAST(Fecha AS date)             AS Fecha,
        Ley_CuT_Plan_Fuente,
        Cobre_Fino_Apilado_Plan_Fuente,
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
    PRINT 'PASO 8  Plan mensual     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 9: Reclamo base (identico al SP productivo)
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
    FROM [inventar_SpcHidr].[vista_reclamo_diario_calculado]
    WHERE fecha_operacion >= @FechaInicioProceso
      AND fecha_operacion <= @FechaFin;
    CREATE CLUSTERED INDEX ix_rb ON #ReclamoBase(Fecha, pad_id);
    PRINT 'PASO 9  Reclamo base     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 10: Reclamo TMS y contexto por pad (identico al SP productivo)
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoOxidosTMS')   IS NOT NULL DROP TABLE #ReclamoOxidosTMS;
    IF OBJECT_ID('tempdb..#ReclamoSulfurosTMS')  IS NOT NULL DROP TABLE #ReclamoSulfurosTMS;
    IF OBJECT_ID('tempdb..#ReclamoOxidosCtx')    IS NOT NULL DROP TABLE #ReclamoOxidosCtx;
    IF OBJECT_ID('tempdb..#ReclamoSulfurosCtx')  IS NOT NULL DROP TABLE #ReclamoSulfurosCtx;

    SELECT Fecha, SUM(tonelaje_reclamado_diario) AS TMS_Rotopala_1_Real
    INTO #ReclamoOxidosTMS  FROM #ReclamoBase WHERE pad_id = 1 GROUP BY Fecha;

    SELECT Fecha, SUM(tonelaje_reclamado_diario) AS TMS_Rotopala_2_Real
    INTO #ReclamoSulfurosTMS FROM #ReclamoBase WHERE pad_id = 2 GROUP BY Fecha;

    ;WITH RankOx AS
    (
        SELECT
            rb.Fecha,
            c.id_modulo                               AS modulo_id,
            rb.avance_porcentaje,
            CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
            ROW_NUMBER() OVER (
                PARTITION BY rb.Fecha
                ORDER BY rb.tonelaje_reclamado_diario DESC
            ) AS rn
        FROM #ReclamoBase rb
        LEFT JOIN [inventar_SpcHidr].[campaña] c
            ON c.[id_campaña] = rb.[campaña_id]
        WHERE rb.pad_id = 1
    )
    SELECT Fecha, campana_nombre, modulo_id, avance_porcentaje
    INTO #ReclamoOxidosCtx FROM RankOx WHERE rn = 1;

    ;WITH RankSu AS
    (
        SELECT
            rb.Fecha,
            c.id_modulo                               AS modulo_id,
            rb.avance_porcentaje,
            CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
            ROW_NUMBER() OVER (
                PARTITION BY rb.Fecha
                ORDER BY rb.tonelaje_reclamado_diario DESC
            ) AS rn
        FROM #ReclamoBase rb
        LEFT JOIN [inventar_SpcHidr].[campaña] c
            ON c.[id_campaña] = rb.[campaña_id]
        WHERE rb.pad_id = 2
    )
    SELECT Fecha, campana_nombre, modulo_id, avance_porcentaje
    INTO #ReclamoSulfurosCtx FROM RankSu WHERE rn = 1;

    CREATE CLUSTERED INDEX ix_ro  ON #ReclamoOxidosTMS(Fecha);
    CREATE CLUSTERED INDEX ix_rs  ON #ReclamoSulfurosTMS(Fecha);
    CREATE CLUSTERED INDEX ix_roc ON #ReclamoOxidosCtx(Fecha);
    CREATE CLUSTERED INDEX ix_rsc ON #ReclamoSulfurosCtx(Fecha);
    PRINT 'PASO 10 Reclamo ctx/TMS  : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';

    /* ================================================================
       PASO 11: MERGE final sobre tabla ALTERNATIVA
       Aplica el metodo elegido (@MetodoFactorAjuste) solo a las columnas
       "oficiales" de esta tabla (Apilado_TMH_promedio_dia, Apilado_TMS_Real,
       Cobre_fino_Apilado_Real). Las columnas _Original y _OpcionB quedan
       siempre pobladas para trazabilidad y comparacion.
    ================================================================ */
    SET @t1 = SYSDATETIME();

    MERGE [inventar_SpcHidr].[Datos_conciliados_of_ajustado_test] AS tgt
    USING
    (
        SELECT
            f.Fecha,
            @MetodoFactorAjuste AS Metodo_Factor_Ajuste,

            CASE
                WHEN c.Chancado_TMH_Dia IS NULL    THEN NULL
                WHEN a.Humedad_promedio_dia IS NULL THEN NULL
                ELSE c.Chancado_TMH_Dia * (1.0 - a.Humedad_promedio_dia / 100.0)
            END AS Chancado_TMS_Real,

            a.Humedad_Turno_A,
            a.Humedad_Turno_B,
            a.Humedad_promedio_dia AS Humedad_promedio_dia_Original,

            a.Sal_turno_A,
            a.Sal_Turno_B,
            a.Sal_promedio_dia,

            a.Apilado_TMH_turno_A,
            a.Apilado_TMH_turno_B,
            a.Apilado_TMH_promedio_dia AS Apilado_TMH_promedio_dia_Original,

            g.Apilado_TMS_Real_Dia AS Apilado_TMS_Real_Original,
            g.Apilado_TMS_Plan     AS Apilado_TMS_Plan,

            fa.Apilado_TMH_Ajustado_OpcionB,
            fa.Apilado_TMS_Ajustado_OpcionB,

            -- Columnas "oficiales" de esta tabla, segun metodo elegido
            CASE
                WHEN @MetodoFactorAjuste = 'B' AND fa.Apilado_TMH_Ajustado_OpcionB IS NOT NULL
                    THEN fa.Apilado_TMH_Ajustado_OpcionB
                ELSE a.Apilado_TMH_promedio_dia
            END AS Apilado_TMH_promedio_dia,

            CASE
                WHEN @MetodoFactorAjuste = 'B' AND fa.Apilado_TMS_Ajustado_OpcionB IS NOT NULL
                    THEN fa.Apilado_TMS_Ajustado_OpcionB
                ELSE g.Apilado_TMS_Real_Dia
            END AS Apilado_TMS_Real,

            CASE
                WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion))) IN ('SULFURO','SULFUROS') THEN 'Sulfuro'
                WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion))) IN ('OXIDO','OXIDOS') THEN 'Oxido'
                ELSE g.Material_Operacion
            END AS Campana_apilado,
            g.Modulo AS Modulo_apilado,
            g.Avance AS Avance_apilado,

            g.CuT_Real_Dia AS Ley_CuT_Real,
            g.CuT_Plan     AS Ley_CuT_Plan,

            -- Cobre fino recalculado con el Apilado_TMS_Real "oficial" de esta tabla
            CASE
                WHEN COALESCE(
                        CASE WHEN @MetodoFactorAjuste = 'B' AND fa.Apilado_TMS_Ajustado_OpcionB IS NOT NULL
                             THEN fa.Apilado_TMS_Ajustado_OpcionB ELSE g.Apilado_TMS_Real_Dia END, 0) = 0 THEN 0
                WHEN g.CuT_Real_Dia IS NULL THEN NULL
                ELSE
                    (CASE WHEN @MetodoFactorAjuste = 'B' AND fa.Apilado_TMS_Ajustado_OpcionB IS NOT NULL
                          THEN fa.Apilado_TMS_Ajustado_OpcionB ELSE g.Apilado_TMS_Real_Dia END)
                    * g.CuT_Real_Dia / 100.0
            END AS Cobre_fino_Apilado_Real,
            pm.Cobre_Fino_Apilado_Plan_Fuente AS Cobre_fino_Apilado_Plan,

            ro_tms.TMS_Rotopala_1_Real,
            pm.TMS_Rotopala_1_Plan,
            CAST(ro_ctx.campana_nombre    AS nvarchar(255)) AS Campana_reclamo_oxidos,
            CAST(ro_ctx.modulo_id         AS int)           AS Modulo_reclamo_oxidos,
            CAST(ro_ctx.avance_porcentaje AS float)         AS Avance_reclamo_oxidos,

            rs_tms.TMS_Rotopala_2_Real,
            pm.TMS_Rotopala_2_Plan,
            CAST(rs_ctx.campana_nombre    AS nvarchar(255)) AS Campana_reclamo_sulfuros,
            CAST(rs_ctx.modulo_id         AS int)           AS modulo_reclamo_sulfuros,
            CAST(rs_ctx.avance_porcentaje AS float)         AS Avance_reclamo_sulfuros,

            pm.Camiones_TMS_Plan AS Camiones_TMS_plan,

            p.Produccion_Catodos_Real,
            pm.Produccion_Catodos_Plan,

            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Turno_A ELSE NULL END AS SRR_TMS_Turno_A,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Turno_B ELSE NULL END AS SRR_TMS_Turno_B,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Dia      ELSE NULL END AS SRR_TMS_promedio_dia,
            pm.SRR_TMS_Plan,

            ls.Ley_CuT_Real_srr,
            pm.Ley_CuT_Plan_SRR AS Ley_CuT_Plan_srr,

            -- Trazabilidad del factor de ajuste
            fa.Factor_Ajuste,
            fa.Flag_Factor_Ajuste,
            fa.Factor_Carga_KOM_TMH_Viaje,
            fa.Factor_Carga_CAT_TMH_Viaje,
            fa.Flag_Factor_Carga_KOM,
            fa.Flag_Factor_Carga_CAT,

            CASE
                WHEN COALESCE(g.Apilado_TMS_Real_Dia, 0) > 0
                 AND g.CuT_Real_Dia IS NULL THEN 2
                WHEN p.Produccion_Catodos_Real IS NULL    THEN 1
                ELSE 0
            END AS estado

        FROM #Fechas       f
        LEFT JOIN #Chancado          c      ON c.Fecha      = f.Fecha
        LEFT JOIN #Apilado           a      ON a.Fecha      = f.Fecha
        LEFT JOIN #Factor            fa     ON fa.Fecha     = f.Fecha
        LEFT JOIN #Generador         g      ON g.Fecha      = f.Fecha
        LEFT JOIN #SRR               s      ON s.Fecha      = f.Fecha
        LEFT JOIN #Catodos           p      ON p.Fecha      = f.Fecha
        LEFT JOIN #Plan              pm     ON pm.Fecha     = f.Fecha
        LEFT JOIN #LeySrr            ls     ON ls.Fecha     = f.Fecha
        LEFT JOIN #ReclamoOxidosTMS  ro_tms ON ro_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoOxidosCtx  ro_ctx ON ro_ctx.Fecha = f.Fecha
        LEFT JOIN #ReclamoSulfurosTMS rs_tms ON rs_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoSulfurosCtx rs_ctx ON rs_ctx.Fecha = f.Fecha
    ) AS src ON tgt.Fecha = src.Fecha

    WHEN MATCHED THEN UPDATE SET
        Metodo_Factor_Ajuste               = src.Metodo_Factor_Ajuste,
        Chancado_TMS_Real                  = src.Chancado_TMS_Real,
        Humedad_Turno_A                    = src.Humedad_Turno_A,
        Humedad_Turno_B                    = src.Humedad_Turno_B,
        Humedad_promedio_dia_Original      = src.Humedad_promedio_dia_Original,
        Sal_turno_A                        = src.Sal_turno_A,
        Sal_Turno_B                        = src.Sal_Turno_B,
        Sal_promedio_dia                   = src.Sal_promedio_dia,
        Apilado_TMH_turno_A                = src.Apilado_TMH_turno_A,
        Apilado_TMH_turno_B                = src.Apilado_TMH_turno_B,
        Apilado_TMH_promedio_dia_Original  = src.Apilado_TMH_promedio_dia_Original,
        Apilado_TMS_Real_Original          = src.Apilado_TMS_Real_Original,
        Apilado_TMS_Plan                   = src.Apilado_TMS_Plan,
        Apilado_TMH_Ajustado_OpcionB       = src.Apilado_TMH_Ajustado_OpcionB,
        Apilado_TMS_Ajustado_OpcionB       = src.Apilado_TMS_Ajustado_OpcionB,
        Apilado_TMH_promedio_dia           = src.Apilado_TMH_promedio_dia,
        Apilado_TMS_Real                   = src.Apilado_TMS_Real,
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
        Camiones_TMS_plan                  = src.Camiones_TMS_plan,
        Produccion_Catodos_Real            = src.Produccion_Catodos_Real,
        Produccion_Catodos_Plan            = src.Produccion_Catodos_Plan,
        SRR_TMS_Turno_A                    = src.SRR_TMS_Turno_A,
        SRR_TMS_Turno_B                    = src.SRR_TMS_Turno_B,
        SRR_TMS_promedio_dia               = src.SRR_TMS_promedio_dia,
        SRR_TMS_Plan                       = src.SRR_TMS_Plan,
        Ley_CuT_Real_srr                   = src.Ley_CuT_Real_srr,
        Ley_CuT_Plan_srr                   = src.Ley_CuT_Plan_srr,
        Factor_Ajuste                      = src.Factor_Ajuste,
        Flag_Factor_Ajuste                 = src.Flag_Factor_Ajuste,
        Factor_Carga_KOM_TMH_Viaje         = src.Factor_Carga_KOM_TMH_Viaje,
        Factor_Carga_CAT_TMH_Viaje         = src.Factor_Carga_CAT_TMH_Viaje,
        Flag_Factor_Carga_KOM              = src.Flag_Factor_Carga_KOM,
        Flag_Factor_Carga_CAT              = src.Flag_Factor_Carga_CAT,
        estado                             = src.estado,
        Fecha_Calculo                      = SYSDATETIME()

    WHEN NOT MATCHED BY TARGET THEN INSERT
    (
        Fecha, Metodo_Factor_Ajuste, Chancado_TMS_Real,
        Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia_Original,
        Sal_turno_A, Sal_Turno_B, Sal_promedio_dia,
        Apilado_TMH_turno_A, Apilado_TMH_turno_B, Apilado_TMH_promedio_dia_Original,
        Apilado_TMS_Real_Original, Apilado_TMS_Plan,
        Apilado_TMH_Ajustado_OpcionB, Apilado_TMS_Ajustado_OpcionB,
        Apilado_TMH_promedio_dia, Apilado_TMS_Real,
        Campana_apilado, Modulo_apilado, Avance_apilado,
        Ley_CuT_Real, Ley_CuT_Plan,
        Cobre_fino_Apilado_Real, Cobre_fino_Apilado_Plan,
        TMS_Rotopala_1_Real, TMS_Rotopala_1_Plan,
        Campana_reclamo_oxidos, Modulo_reclamo_oxidos, Avance_reclamo_oxidos,
        TMS_Rotopala_2_Real, TMS_Rotopala_2_Plan,
        Campana_reclamo_sulfuros, modulo_reclamo_sulfuros, Avance_reclamo_sulfuros,
        Camiones_TMS_plan,
        Produccion_Catodos_Real, Produccion_Catodos_Plan,
        SRR_TMS_Turno_A, SRR_TMS_Turno_B, SRR_TMS_promedio_dia, SRR_TMS_Plan,
        Ley_CuT_Real_srr, Ley_CuT_Plan_srr,
        Factor_Ajuste, Flag_Factor_Ajuste,
        Factor_Carga_KOM_TMH_Viaje, Factor_Carga_CAT_TMH_Viaje,
        Flag_Factor_Carga_KOM, Flag_Factor_Carga_CAT,
        estado, Fecha_Calculo
    )
    VALUES
    (
        src.Fecha, src.Metodo_Factor_Ajuste, src.Chancado_TMS_Real,
        src.Humedad_Turno_A, src.Humedad_Turno_B, src.Humedad_promedio_dia_Original,
        src.Sal_turno_A, src.Sal_Turno_B, src.Sal_promedio_dia,
        src.Apilado_TMH_turno_A, src.Apilado_TMH_turno_B, src.Apilado_TMH_promedio_dia_Original,
        src.Apilado_TMS_Real_Original, src.Apilado_TMS_Plan,
        src.Apilado_TMH_Ajustado_OpcionB, src.Apilado_TMS_Ajustado_OpcionB,
        src.Apilado_TMH_promedio_dia, src.Apilado_TMS_Real,
        src.Campana_apilado, src.Modulo_apilado, src.Avance_apilado,
        src.Ley_CuT_Real, src.Ley_CuT_Plan,
        src.Cobre_fino_Apilado_Real, src.Cobre_fino_Apilado_Plan,
        src.TMS_Rotopala_1_Real, src.TMS_Rotopala_1_Plan,
        src.Campana_reclamo_oxidos, src.Modulo_reclamo_oxidos, src.Avance_reclamo_oxidos,
        src.TMS_Rotopala_2_Real, src.TMS_Rotopala_2_Plan,
        src.Campana_reclamo_sulfuros, src.modulo_reclamo_sulfuros, src.Avance_reclamo_sulfuros,
        src.Camiones_TMS_plan,
        src.Produccion_Catodos_Real, src.Produccion_Catodos_Plan,
        src.SRR_TMS_Turno_A, src.SRR_TMS_Turno_B, src.SRR_TMS_promedio_dia, src.SRR_TMS_Plan,
        src.Ley_CuT_Real_srr, src.Ley_CuT_Plan_srr,
        src.Factor_Ajuste, src.Flag_Factor_Ajuste,
        src.Factor_Carga_KOM_TMH_Viaje, src.Factor_Carga_CAT_TMH_Viaje,
        src.Flag_Factor_Carga_KOM, src.Flag_Factor_Carga_CAT,
        src.estado, SYSDATETIME()
    );

    PRINT 'PASO 11 MERGE            : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — '
        + CAST(@@ROWCOUNT AS varchar) + ' filas afectadas';
    PRINT '-- TOTAL                 : ' + CAST(DATEDIFF(ms,@t0,SYSDATETIME()) AS varchar) + ' ms';

    DROP TABLE IF EXISTS #Fechas;
    DROP TABLE IF EXISTS #Chancado;
    DROP TABLE IF EXISTS #LeySrr;
    DROP TABLE IF EXISTS #Apilado;
    DROP TABLE IF EXISTS #Factor;
    DROP TABLE IF EXISTS #Generador;
    DROP TABLE IF EXISTS #SRR;
    DROP TABLE IF EXISTS #Catodos;
    DROP TABLE IF EXISTS #Plan;
    DROP TABLE IF EXISTS #ReclamoBase;
    DROP TABLE IF EXISTS #ReclamoOxidosTMS;
    DROP TABLE IF EXISTS #ReclamoSulfurosTMS;
    DROP TABLE IF EXISTS #ReclamoOxidosCtx;
    DROP TABLE IF EXISTS #ReclamoSulfurosCtx;
END;