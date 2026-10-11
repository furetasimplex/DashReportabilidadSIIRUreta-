/* ============================================================================
   inventar_SpcHidr.sp_mantiene_datos_conciliados_of
   VERSION 1.14 - CRITERIO DE "GANADOR DEL DIA" IGUAL AL DEL DASHBOARD

   ----------------------------------------------------------------------------
   POR QUE ESTE CAMBIO (diagnostico 2026-07-31, continuacion de v1.13)
   ----------------------------------------------------------------------------
   Tras publicar v1.13 (PASO 9/10/10b leyendo reclamo.v_reclamo_para_
   conciliados), el usuario confirmo que TMS_Rotopala_2_Real ya coincide
   exacto con el dashboard para los 26 dias de julio, y que el barrido de no
   regresion de modulo salio vacio. Pero senalo una diferencia puntual: el
   07-01 el SP publicaba Modulo_reclamo_sulfuros = 123 al 98 %, mientras el
   dashboard (que el usuario confirma correcto, ya limpiado previamente)
   muestra modulo 124 al 8 %. El tonelaje total del dia (35.061,85 TMS) es
   igual en ambos: la diferencia esta solo en CUAL modulo se elige como
   protagonista del dia cuando dos modulos tienen tonelaje > 0 el mismo dia
   (123 terminando y 124 recien empezando).

   CAUSA: el cursor del PASO 10 (heredado sin cambios desde v1.12) elige el
   ganador del dia con
       ORDER BY tonelaje_reclamado_diario DESC, modulo_id DESC
   es decir, el modulo con MAS tonelaje ese dia. El dashboard (Vista previa,
   dash/app.py, cb_preview_conciliados) usa un criterio distinto: entre los
   modulos con tms_rotopala_dia > 0 que respetan el piso de secuencia, elige
   el de MENOR avance_roto_pct (idxmin), no el de mayor tonelaje:
       fila_activa = activos.loc[activos["avance_roto_pct"].idxmin()]
   Este criterio es intencional: cuando un modulo casi terminado (123, 98 %)
   y el modulo recien iniciado (124, 8 %) tienen tonelaje el mismo dia, el de
   menor avance es el que realmente esta activo; el de mayor avance esta con
   una lectura residual de cierre. Es la misma logica de fondo que motivo el
   piso de secuencia en v1.12 (no dejar que un modulo casi terminado tape al
   modulo activo), pero aplicada como criterio de desempate en vez de umbral.

   El piso de secuencia por si solo no alcanza a resolver este caso porque
   123 y 124 son consecutivos: 124 >= piso no descarta a 123 (124 tambien
   cumple 124 >= piso). Hace falta el criterio de menor avance para elegir
   entre ambos.

   FIX: se cambia el ORDER BY del cursor, en oxidos y sulfuros, de
   "tonelaje_reclamado_diario DESC" a "avance_porcentaje ASC" (mismo
   desempate por modulo_id DESC). Con el piso de secuencia ya vigente
   (evita elegir un modulo anterior ya superado) mas este criterio (evita
   elegir el modulo de mayor avance cuando hay mas de un candidato el mismo
   dia), el resultado queda alineado con el dashboard.

   ----------------------------------------------------------------------------
   QUE CAMBIA RESPECTO DE v1.13
   ----------------------------------------------------------------------------
   PASO 10  UNICO CAMBIO: el ORDER BY del SELECT TOP (1) dentro de los
            cursores dias_ox y dias_su pasa de
                ORDER BY tonelaje_reclamado_diario DESC, modulo_id DESC
            a
                ORDER BY avance_porcentaje ASC, modulo_id DESC
            Todo lo demas del PASO 10 (piso de secuencia, LOCF, estructura de
            tablas) queda identico a v1.13.

   PASO 10b Sin cambios respecto de v1.13 (no se reporto el mismo problema
            de desempate para camiones).

   PASOS 1 a 9, 10b y 11  Identicos a v1.13.

   ----------------------------------------------------------------------------
   PASO 9   Fuente: reclamo.v_reclamo_para_conciliados en vez de
            inventar_SpcHidr.vista_reclamo_diario_calculado (cambio de
            v1.13, se mantiene). El modulo_numero ya viene resuelto en la
            vista (ya no hace falta LEFT JOIN contra inventar_SpcHidr.modulo).

   PASO 10  Mantiene el piso de secuencia agregado en v1.12 (cursor
            cronologico, sin retroceder a un modulo ya superado dentro de la
            misma campana), MAS el nuevo criterio de desempate por menor
            avance (v1.14, ver arriba).

            CAMBIO DE SEMANTICA DEL AVANCE PUBLICADO (ya aprobado, no es
            nuevo de esta version, viene definido desde el diseño del
            esquema reclamo): Avance_reclamo_oxidos/sulfuros queda referido
            al remanente disponible POST CAMIONES, definicion confirmada por
            Juan Antonio Segura el 29-05-2026. Las cifras cambian respecto de
            lo publicado hasta v1.12 en los modulos con movimiento de
            camiones.

   PASO 10b Lee tonelaje_camiones_diario desde reclamo.v_reclamo_para_
            conciliados (cambio de v1.13, se mantiene), para ambos PAD.
            Camiones_TMS_Reclamo_Oxidos deja de ser NULL fijo. Camiones_TMS_
            total pasa a sumar ambos PAD (antes solo sumaba sulfuros).

   PASO 11  Sin cambios en la lista de columnas del MERGE respecto de v1.13.
            La formula de Total_Ripios_Incluye_Camiones_Real usa Camiones_
            TMS_total (ambos PAD).

   PASOS 1 a 8  Identicos a v1.12/v1.13. El PASO 2 (Chancado TMH con
            respaldo imp_csv) y el PASO 6 (SRR desde reporte_turno_cache) no
            se tocan.

   ----------------------------------------------------------------------------
   REQUISITO: haber ejecutado reclamo.sp_calcular_reclamo_diario para el
   rango a procesar (para que reclamo.v_reclamo_diario tenga base congelada
   resuelta), aunque la vista de consumo calcula en vivo desde
   modulo_congelado / topografia_avance / camiones_reclamo / ajuste_manual y
   no depende de la tabla reclamo.calculo_diario.

   ANTES DE EJECUTAR
       SELECT OBJECT_DEFINITION(OBJECT_ID(
           'inventar_SpcHidr.sp_mantiene_datos_conciliados_of'));
   DESPUES DE EJECUTAR
       38_Validacion_Ganador_Dia_v1.14.sql
   ============================================================================ */
CREATE   PROCEDURE [inventar_SpcHidr].[sp_mantiene_datos_conciliados_of]
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
    /* Período cerrado: respetar la fotografía congelada. */
    SELECT TOP (1)
        @FechaCorteCamiones = cfg.[fecha_corte_camiones]
    FROM [inventar_SpcHidr].[configuracion_reclamo_rotopala_periodo] cfg
    WHERE cfg.[periodo_reporte] = @InicioMesCorte
      AND cfg.[pad_id] = 2
      AND cfg.[estado] = 'CERRADO'
      AND cfg.[fecha_corte_camiones] IS NOT NULL;
    /* Período abierto: utilizar la última carga realmente disponible. */
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
              'No existe una fecha de corte de camiones válida para el período.',
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
    PRINT '-- Version: 1.14 (reclamo desde el esquema [reclamo]; ganador del dia por menor avance)';
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
       PASO 2: Chancado TMH                                   v1.11
       ----------------------------------------------------------------
       FUENTE OFICIAL      : [inventar_SpcHidr].[mov_cam]
                             Fase NOT LIKE '%SRR%', campo Tonelaje_Hum_CIO.
                             Validada contra el Excel BD_CIO_Spence_CH01
                             para el 01 al 24 de julio de 2026: coincidencia
                             exacta, diferencia 0,000 en las 24 fechas.
       FUENTE PRELIMINAR   : [inventar_SpcHidr].[imp_csv]
                             [to] = 'CH01', shovel <> 'SRR', origen = 'IMP',
                             campo tonnage.
       REGLA DE PRECEDENCIA:
           mov_cam manda siempre que exista AL MENOS UNA FILA para la fecha,
           aunque el tonelaje sume cero. imp_csv solo cubre fechas que no
           tienen ninguna fila en mov_cam.
       CARACTER DEL DATO   : el valor tomado de imp_csv es PROVISIONAL. Se
           reemplaza solo con reprocesar el rango una vez que mov_cam reciba
           la carga de esa fecha, porque el NOT EXISTS deja de cumplirse.
           No queda ningun valor congelado ni requiere limpieza manual.
       ESQUEMA DE imp_csv:
           la tabla vive en inventar_SpcHidr, confirmado por el usuario el
           29-07-2026. La columna Owner que devuelve sp_help NO es el esquema
           sino el propietario del esquema, por eso mostraba dbo: para
           resolver el esquema real hay que consultar sys.objects unido a
           sys.schemas (seccion 1.a del script de validacion).
           Se referencia SIEMPRE calificada. Sin calificar, dentro de un
           procedimiento un nombre resuelve primero contra el esquema del
           procedimiento y solo despues contra dbo; calificar evita depender
           de ese orden y de la creacion futura de un homonimo.
       ADVERTENCIA SOBRE shovel <> 'SRR':
           el predicado se mantiene tal como fue entregado. En T-SQL una
           fila con shovel NULL NO cumple shovel <> 'SRR' y queda excluida
           silenciosamente. El script de validacion cuantifica ese efecto.
           Si resultara relevante, corresponde decidir expresamente si pasa
           a (shovel IS NULL OR shovel <> 'SRR').
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Chancado')        IS NOT NULL DROP TABLE #Chancado;
    IF OBJECT_ID('tempdb..#ChancadoMovCam')  IS NOT NULL DROP TABLE #ChancadoMovCam;
    IF OBJECT_ID('tempdb..#ChancadoImpCsv')  IS NOT NULL DROP TABLE #ChancadoImpCsv;
    /* 2.a  Fuente oficial: mov_cam */
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
    /* 2.b  Fuente preliminar: imp_csv */
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
    /* 2.c  Consolidacion con trazabilidad de fuente */
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
    /* 2.d  Diagnostico de fuentes */
    DECLARE @ChFilas       int;
    DECLARE @ChMovCam      int;
    DECLARE @ChImpCsv      int;
    DECLARE @ChFechasPrelim varchar(max);
    SELECT
        @ChFilas  = COUNT(*),
        @ChMovCam = SUM(CASE WHEN Fuente_Chancado_TMH = 'MOV_CAM' THEN 1 ELSE 0 END),
        @ChImpCsv = SUM(CASE WHEN Fuente_Chancado_TMH = 'IMP_CSV_PRELIMINAR' THEN 1 ELSE 0 END)
    FROM #Chancado;
    PRINT 'PASO 2  Chancado         : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(COALESCE(@ChFilas,0) AS varchar) + ' filas';
    PRINT '        Fuente MOV_CAM   : ' + CAST(COALESCE(@ChMovCam,0) AS varchar) + ' dias';
    PRINT '        Fuente IMP_CSV   : ' + CAST(COALESCE(@ChImpCsv,0) AS varchar) + ' dias (PRELIMINAR)';
    IF COALESCE(@ChImpCsv,0) > 0
    BEGIN
        SELECT @ChFechasPrelim =
            STUFF(
            (
                SELECT ', ' + CONVERT(varchar(10), ch.Fecha, 120)
                FROM #Chancado ch
                WHERE ch.Fuente_Chancado_TMH = 'IMP_CSV_PRELIMINAR'
                ORDER BY ch.Fecha
                FOR XML PATH(''), TYPE
            ).value('.', 'varchar(max)'), 1, 2, '');
        PRINT '        ATENCION: las siguientes fechas quedaron con Chancado';
        PRINT '        PRELIMINAR desde imp_csv y se corregiran solas al';
        PRINT '        reprocesar el rango una vez cargado mov_cam:';
        PRINT '        ' + COALESCE(@ChFechasPrelim, '(sin detalle)');
    END;
    /* ================================================================
       PASO 3: Ley CuT SRR
       Fuente : mov_cam, Fase = SRR
       Metodo : promedio ponderado SUM(Ton * CuTG00) / SUM(Ton)
       NOTA v1.11: la ley de SRR NO tiene respaldo en imp_csv. Un dia
       cubierto por el preliminar de Chancado seguira sin Ley_CuT_Real_srr.
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
       PASO 9: Reclamo base                                     v1.13
       FUENTE NUEVA: reclamo.v_reclamo_para_conciliados. Reemplaza a
       inventar_SpcHidr.vista_reclamo_diario_calculado (objeto totalmente
       independiente del esquema [reclamo], por eso nunca reflejaba las
       correcciones ya validadas de densidad, secuencia y camiones).
       El modulo_numero ya viene resuelto en la vista.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoBase') IS NOT NULL DROP TABLE #ReclamoBase;
    SELECT
        r.fecha_operacion              AS Fecha,
        r.pad_id,
        r.[campaña_id],
        r.modulo_id,
        r.modulo_numero,
        r.rotopala_id,
        r.avance_porcentaje,
        r.avance_total_porcentaje,
        r.avance_camiones_porcentaje,
        r.tonelaje_reclamado_diario,
        r.tonelaje_camiones_diario,
        r.volumen_diario_m3,
        r.fuente_reclamo,
        r.metodo_calculo,
        r.flag_calculo
    INTO #ReclamoBase
    FROM [reclamo].[v_reclamo_para_conciliados] r
    WHERE r.fecha_operacion >= @FechaInicioProceso
      AND r.fecha_operacion <= @FechaFin;
    CREATE CLUSTERED INDEX ix_rb ON #ReclamoBase(Fecha, pad_id);
    DECLARE @RbFilas int = @@ROWCOUNT;
    DECLARE @RbPreliminar int =
    (
        SELECT COUNT(*) FROM #ReclamoBase WHERE fuente_reclamo = 'PRELIMINAR_CV25'
    );
    PRINT 'PASO 9  Reclamo base     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms — ' + CAST(@RbFilas AS varchar) + ' filas (fuente: reclamo.v_reclamo_para_conciliados)';
    IF @RbFilas = 0
        PRINT '        ADVERTENCIA: sin filas en reclamo.v_reclamo_para_conciliados para el rango.';
    IF @RbPreliminar > 0
        PRINT '        ' + CAST(@RbPreliminar AS varchar) + ' filas con fuente PRELIMINAR_CV25 (proyeccion CV25, no topografia).';
    /* ================================================================
       PASO 10: Reclamo TMS y contexto por pad                  v1.14
       PAD 1 = oxido  -> TMS_Rotopala_1_Real, Campana/Modulo/Avance oxidos
       PAD 2 = sulfuro -> TMS_Rotopala_2_Real, Campana/Modulo/Avance sulfuros
       Contexto: modulo/avance del dia con reclamo real (tonelaje > 0),
       con LOCF (last-observation-carried-forward) en dias sin tonelaje.

       PISO DE SECUENCIA (agregado en v1.12, INTACTO en v1.13 y v1.14)
       Cursor cronologico con un "piso de secuencia" por PAD: el ganador
       del dia debe tener modulo_numero mayor o igual al piso vigente PARA
       LA MISMA CAMPAÑA, para no retroceder a un modulo ya superado en la
       secuencia por una lectura residual minima (caso confirmado 2026-07-
       30: modulo 37 al 99,8% tapando al modulo 38 activo en 11,2%). Si el
       unico candidato del dia esta bajo el piso, no se elige ganador ese
       dia y el LOCF existente mantiene el ultimo modulo/avance valido. El
       piso se reinicia solo cuando cambia la campana.

       CRITERIO DE DESEMPATE POR MENOR AVANCE (v1.14)
       El piso de secuencia no alcanza a resolver el caso de dos modulos
       CONSECUTIVOS con tonelaje el mismo dia (ej. 123 terminando al 98% y
       124 recien iniciado al 8%: 124 >= piso no descarta a 123, porque 123
       tambien cumple). Por eso el ganador del dia, entre los candidatos que
       pasan el piso, se elige por MENOR avance_porcentaje (no por mayor
       tonelaje como hasta v1.13): el modulo con menos avance es el que
       realmente esta activo; el de mayor avance tiene una lectura residual
       de cierre. Mismo criterio ya usado y validado en el dashboard
       (dash/app.py, cb_preview_conciliados: activos.loc[avance_roto_pct
       .idxmin()]). Caso confirmado 2026-07-31: 07-01, PAD2/sulfuros,
       campaña 10 -- el SP con el criterio viejo (mayor tonelaje) publicaba
       modulo 123 al 98%; con este fix publica modulo 124 al 8%, igual que
       el dashboard. El tonelaje total del dia no cambia (35.061,85 TMS),
       solo cambia cual modulo se le atribuye.

       Origen de #GanadorOxRaw/#GanadorSuRaw (desde v1.13): #ReclamoBase
       (ya trae modulo_numero resuelto desde reclamo.v_reclamo_para_
       conciliados); no hace falta LEFT JOIN contra inventar_SpcHidr.modulo.
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
    -- Candidatos oxidos (pad 1): TODOS los modulos con reclamo real ese
    -- dia, no solo el de mas tonelaje (eso lo decide el cursor de mas
    -- abajo, con el piso de secuencia aplicado). modulo_numero ya viene
    -- resuelto desde #ReclamoBase.
    SELECT
        rb.Fecha,
        rb.modulo_id,
        rb.modulo_numero,
        rb.avance_porcentaje,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
        rb.[campaña_id],
        rb.tonelaje_reclamado_diario
    INTO #GanadorOxRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c
        ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.pad_id = 1
      AND rb.tonelaje_reclamado_diario > 0;
    CREATE CLUSTERED INDEX ix_gor ON #GanadorOxRaw(Fecha, modulo_numero);
    -- Candidatos sulfuros (pad 2): misma logica que oxidos
    SELECT
        rb.Fecha,
        rb.modulo_id,
        rb.modulo_numero,
        rb.avance_porcentaje,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
        rb.[campaña_id],
        rb.tonelaje_reclamado_diario
    INTO #GanadorSuRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c
        ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.pad_id = 2
      AND rb.tonelaje_reclamado_diario > 0;
    CREATE CLUSTERED INDEX ix_gsr ON #GanadorSuRaw(Fecha, modulo_numero);
    -- Ganador del dia por PAD, con piso de secuencia. Cursor cronologico:
    -- requiere memoria entre filas (el piso vigente), no es expresable de
    -- forma set-based simple.
    CREATE TABLE #GanadorOx
    (
        Fecha date NOT NULL PRIMARY KEY,
        modulo_numero int NULL,
        avance_porcentaje float NULL,
        campana_nombre nvarchar(255) NULL
    );
    CREATE TABLE #GanadorSu
    (
        Fecha date NOT NULL PRIMARY KEY,
        modulo_numero int NULL,
        avance_porcentaje float NULL,
        campana_nombre nvarchar(255) NULL
    );
    DECLARE @PisoOx int = 0, @CampanaPisoOx nvarchar(255) = NULL;
    DECLARE @PisoSu int = 0, @CampanaPisoSu nvarchar(255) = NULL;
    DECLARE @FechaCur date, @ModCur int, @AvanceCur float, @CampCur nvarchar(255);
    -- Oxidos (pad 1)
    DECLARE dias_ox CURSOR LOCAL FAST_FORWARD FOR
        SELECT DISTINCT Fecha FROM #GanadorOxRaw ORDER BY Fecha;
    OPEN dias_ox;
    FETCH NEXT FROM dias_ox INTO @FechaCur;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @ModCur = NULL; SET @AvanceCur = NULL; SET @CampCur = NULL;
        SELECT TOP (1)
            @ModCur = modulo_numero, @AvanceCur = avance_porcentaje,
            @CampCur = campana_nombre
        FROM #GanadorOxRaw
        WHERE Fecha = @FechaCur
          AND
          (
              @CampanaPisoOx IS NULL
              OR campana_nombre <> @CampanaPisoOx
              OR modulo_numero >= @PisoOx
          )
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
        -- Si no hay candidato valido (todo lo que tuvo tonelaje ese dia es
        -- un modulo ya superado de la misma campana), no se inserta fila:
        -- el LOCF de #GrupoOx mantiene el ultimo modulo/avance valido.
        FETCH NEXT FROM dias_ox INTO @FechaCur;
    END;
    CLOSE dias_ox;
    DEALLOCATE dias_ox;
    -- Sulfuros (pad 2)
    DECLARE dias_su CURSOR LOCAL FAST_FORWARD FOR
        SELECT DISTINCT Fecha FROM #GanadorSuRaw ORDER BY Fecha;
    OPEN dias_su;
    FETCH NEXT FROM dias_su INTO @FechaCur;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @ModCur = NULL; SET @AvanceCur = NULL; SET @CampCur = NULL;
        SELECT TOP (1)
            @ModCur = modulo_numero, @AvanceCur = avance_porcentaje,
            @CampCur = campana_nombre
        FROM #GanadorSuRaw
        WHERE Fecha = @FechaCur
          AND
          (
              @CampanaPisoSu IS NULL
              OR campana_nombre <> @CampanaPisoSu
              OR modulo_numero >= @PisoSu
          )
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
    -- LOCF: arrastra el ultimo ganador valido a los dias sin ganador nuevo
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
       PASO 10b: Reclamo Camiones                                v1.13
       FUENTE NUEVA: reclamo.v_reclamo_para_conciliados (misma fila base
       que PASO 9, columna tonelaje_camiones_diario). Reemplaza a la union
       control_reclamo_sulfuro_camiones_thm_diario x disponible_rotopalas
       de v1.11/v1.12, que solo cubria PAD 2 y calculaba volumen x densidad
       a mano (duplicando la formula que ya resuelve el esquema [reclamo]).

       Camiones_TMS_Reclamo_Oxidos deja de ser NULL fijo: se publica lo que
       exista para PAD 1 en el esquema [reclamo]. Camiones_TMS_total pasa a
       sumar ambos PAD (antes solo sumaba sulfuros).

       Ganador del dia y LOCF: mismo criterio que hasta v1.12 (mayor
       tonelaje_camiones_diario del dia, desempate por modulo_id DESC), sin
       piso de secuencia -- no se reporto el mismo problema de retroceso
       para camiones.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoCamionesTMS')  IS NOT NULL DROP TABLE #ReclamoCamionesTMS;
    IF OBJECT_ID('tempdb..#GanadorCamRaw')       IS NOT NULL DROP TABLE #GanadorCamRaw;
    IF OBJECT_ID('tempdb..#GanadorCam')          IS NOT NULL DROP TABLE #GanadorCam;
    IF OBJECT_ID('tempdb..#GrupoCam')            IS NOT NULL DROP TABLE #GrupoCam;
    IF OBJECT_ID('tempdb..#ReclamoCamionesCtx')  IS NOT NULL DROP TABLE #ReclamoCamionesCtx;
    SELECT
        rb.Fecha,
        SUM(CASE WHEN rb.pad_id = 1 THEN rb.tonelaje_camiones_diario ELSE 0 END)
            AS Camiones_TMS_Reclamo_Oxidos,
        SUM(CASE WHEN rb.pad_id = 2 THEN rb.tonelaje_camiones_diario ELSE 0 END)
            AS Camiones_TMS_Reclamo_Sulfuros,
        SUM(rb.tonelaje_camiones_diario)
            AS Camiones_TMS_total
    INTO #ReclamoCamionesTMS
    FROM #ReclamoBase rb
    GROUP BY rb.Fecha;
    CREATE CLUSTERED INDEX ix_rct ON #ReclamoCamionesTMS(Fecha);
    -- Ganador del dia: mayor tonelaje_camiones_diario (desempate por
    -- modulo_id DESC), solo entre filas con tonelaje > 0.
    SELECT
        rb.Fecha,
        CAST(rb.modulo_numero AS nvarchar(255))   AS Modulo_reclamo_camiones,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS Campana_reclamo_camiones,
        ROW_NUMBER() OVER (
            PARTITION BY rb.Fecha
            ORDER BY rb.tonelaje_camiones_diario DESC, rb.modulo_id DESC
        ) AS rn
    INTO #GanadorCamRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c
        ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.tonelaje_camiones_diario > 0;
    SELECT Fecha, Modulo_reclamo_camiones, Campana_reclamo_camiones
    INTO #GanadorCam
    FROM #GanadorCamRaw
    WHERE rn = 1;
    -- LOCF: en dias sin ganador (sin tonelaje_camiones_diario > 0) se
    -- mantiene el ultimo contexto valido dentro del rango procesado.
    SELECT
        f.Fecha,
        g.Campana_reclamo_camiones,
        g.Modulo_reclamo_camiones,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END)
            OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoCam
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase) f
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
       PASO 11: MERGE final                                      v1.13
       Todas las fuentes ya materializadas en temp tables -> joins simples.
       UNICOS CAMBIOS RESPECTO DE v1.12: Camiones_TMS_Reclamo_Oxidos ya no
       es NULL fijo, Camiones_TMS_total suma ambos PAD, y la formula de
       Total_Ripios_Incluye_Camiones_Real usa Camiones_TMS_total en vez de
       solo Camiones_TMS_Reclamo_Sulfuros.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    MERGE [inventar_SpcHidr].[Datos_conciliados_of] AS tgt
    USING
    (
        SELECT
            f.Fecha,
            /* -- CHANCADO TMS
               TMH * (1 - humedad / 100)
               TMH desde #Chancado: mov_cam cuando existe la fecha, y en su
               defecto imp_csv como PRELIMINAR (ver PASO 2 v1.11).
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
            /* -- CAMIONES, esquema reclamo, ambos PAD                  v1.13 */
            rc_tms.Camiones_TMS_Reclamo_Oxidos,
            rc_tms.Camiones_TMS_Reclamo_Sulfuros,
            CAST(NULL AS nvarchar(255)) AS Movido,
            CAST(NULL AS nvarchar(255)) AS Extraido,
            rc_tms.Camiones_TMS_total                              AS Camiones_TMS_total,
            pm.Camiones_TMS_Plan        AS Camiones_TMS_plan,
            rc_ctx.Campana_reclamo_camiones,
            rc_ctx.Modulo_reclamo_camiones,
            /* -- RIPIOS                                              v1.13 */
            CASE
                WHEN rc_tms.Camiones_TMS_total           IS NULL
                  OR ro_tms.TMS_Rotopala_1_Real            IS NULL
                  OR rs_tms.TMS_Rotopala_2_Real            IS NULL
                    THEN NULL
                ELSE
                    rc_tms.Camiones_TMS_total
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
    DROP TABLE IF EXISTS #ChancadoMovCam;
    DROP TABLE IF EXISTS #ChancadoImpCsv;
    DROP TABLE IF EXISTS #LeySrr;
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