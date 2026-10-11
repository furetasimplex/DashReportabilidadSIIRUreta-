-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
CREATE PROCEDURE [inventar_SpcHidr].[sp_calcular_balance_flujos_v2]
(
    @fecha_inicio date,
    @fecha_fin    date
)
AS
BEGIN
    SET NOCOUNT ON;

    -------------------------------------------------------------------------
    -- 0) NORMALIZAR FECHAS
    -------------------------------------------------------------------------
    IF @fecha_inicio > @fecha_fin
    BEGIN
        DECLARE @tmp date = @fecha_inicio;
        SET @fecha_inicio = @fecha_fin;
        SET @fecha_fin = @tmp;
    END;

    DECLARE @ff_mas_1 date = DATEADD(DAY, 1, @fecha_fin);

    -------------------------------------------------------------------------
    -- 1) TABLA TEMPORAL DE RESULTADOS
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#flujos_resultado') IS NOT NULL
        DROP TABLE #flujos_resultado;

    CREATE TABLE #flujos_resultado
    (
        codigo_flujo varchar(10)  NOT NULL PRIMARY KEY,
        TMS_Inicial  decimal(18,6) NULL,
        Ley_Cu_1     decimal(18,6) NULL,
        TMS_Final    decimal(18,6) NULL,
        Ley_Cu_2     decimal(18,6) NULL,
        Tonelaje     decimal(18,6) NULL,
        Ley_Cu       decimal(18,6) NULL
    );

    -------------------------------------------------------------------------
    -- 2) FLUJOS BASE F1..F15, F20..F25
    -------------------------------------------------------------------------

    -- F1
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT
        'F1',
        ISNULL(SUM(Ton), 0),
        ISNULL((SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0, 0)
    FROM inventar_SpcHidr.mov_cam
    WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin
      AND Origen = 'Stock'
      AND Fase <> 'SRR'
      AND Destino = 'CH01';

    -- F2
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT
        'F2',
        ISNULL(SUM(Ton), 0),
        ISNULL((SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0, 0)
    FROM inventar_SpcHidr.mov_cam
    WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin
      AND Origen = 'Mina'
      AND Fase <> 'SRR'
      AND Destino = 'CH01';

    -- F3
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT
        'F3',
        ISNULL(SUM(Ton), 0),
        ISNULL((SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0, 0)
    FROM inventar_SpcHidr.mov_cam
    WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin
      AND Fase <> 'SRR'
      AND Destino = 'CH01';

    -- F4
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT
        'F4',
        ROUND(
            COALESCE((
                SELECT SUM(CV006_tot)
                FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                WHERE fecha_turno >= @fecha_inicio
                  AND fecha_turno < DATEADD(DAY, 1, @fecha_fin)
            ), 0) * (1 - 2.5 / 100.0),
            2
        ) AS Tonelaje,
        COALESCE((
            SELECT (SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0
            FROM inventar_SpcHidr.mov_cam
            WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin
              AND Fase <> 'SRR'
              AND Destino = 'CH01'
        ), 0) AS Ley_Cu;

    -- F5
    ;WITH
    tms_i AS (
        SELECT AVG(31.1017672705390 * ((v.niv_silo_a + v.niv_silo_b) / 2.0) * (1 - 2.5 / 100.0)) AS total_tms
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados v
        WHERE CAST(v.Fecha_turno AS date) = @fecha_inicio
    ),
    tms_f AS (
        SELECT AVG(31.1017672705390 * ((v.niv_silo_a + v.niv_silo_b) / 2.0) * (1 - 2.5 / 100.0)) AS total_tms
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados v
        WHERE CAST(v.Fecha_turno AS date) = @fecha_fin
    ),
    ley_i AS (
        SELECT (SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0 AS ley_cu
        FROM inventar_SpcHidr.mov_cam
        WHERE fecha = @fecha_inicio AND Fase <> 'SRR' AND Destino = 'CH01'
    ),
    ley_f AS (
        SELECT (SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0 AS ley_cu
        FROM inventar_SpcHidr.mov_cam
        WHERE fecha = @fecha_fin AND Fase <> 'SRR' AND Destino = 'CH01'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT
        'F5',
        COALESCE(tms_i.total_tms, 0),
        COALESCE(ley_i.ley_cu, ley_f.ley_cu, 0),
        COALESCE(tms_f.total_tms, 0),
        COALESCE(ley_f.ley_cu, ley_i.ley_cu, 0),
        COALESCE(tms_f.total_tms, 0) - COALESCE(tms_i.total_tms, 0),
        COALESCE(
            ((COALESCE(tms_f.total_tms,0)*COALESCE(ley_f.ley_cu,ley_i.ley_cu,0)/100.0)
            -(COALESCE(tms_i.total_tms,0)*COALESCE(ley_i.ley_cu,ley_f.ley_cu,0)/100.0))
            / NULLIF(COALESCE(tms_f.total_tms,0)-COALESCE(tms_i.total_tms,0),0)*100.0, 0)
    FROM tms_i CROSS JOIN tms_f CROSS JOIN ley_i CROSS JOIN ley_f;

    -- F6
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F6',
        (ISNULL((SELECT ROUND(SUM(D.tsd),2) FROM (
            SELECT SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd
            FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
            JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
            WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1
            GROUP BY CAST(vrdf.fecha_turno AS date)) D),0)
        -ISNULL((SELECT SUM(cv002_tot)*0.97 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0)
        -ISNULL((SELECT SUM(cv201_tot) FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0)) AS Tonelaje,
        ((ISNULL((SELECT SUM(D.Finos) FROM (
            SELECT (SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0))*AVG(i.CuT_Dia)/100.0 AS Finos
            FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
            JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
            WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1
            GROUP BY CAST(vrdf.fecha_turno AS date)) D),0)
        -ISNULL((SELECT SUM(cv002_tot)*0.97 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin))*
            (SELECT SUM(Ton*CuTG00/100.0)/NULLIF(SUM(Ton),0) FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin AND Fase='SRR' AND (Destino='prueba' OR Destino='CH01')),0))
        /NULLIF((ISNULL((SELECT ROUND(SUM(D.tsd),2) FROM (
            SELECT SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd
            FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
            JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
            WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1
            GROUP BY CAST(vrdf.fecha_turno AS date)) D),0)
        -ISNULL((SELECT SUM(cv002_tot)*0.97 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0)
        -ISNULL((SELECT SUM(cv201_tot) FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0)),0))*100.0 AS Ley_Cu;

    -- F7
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F7',
        (ISNULL((SELECT ROUND(SUM(D.tsd),2) FROM (
            SELECT SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd
            FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
            JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
            WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2
            GROUP BY CAST(vrdf.fecha_turno AS date)) D),0)
        -ISNULL((SELECT SUM(cv003_tot)*0.97 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0)
        -ISNULL((SELECT SUM(cv202_tot) FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0)) AS Tonelaje,
        ((ISNULL((SELECT SUM(D.Finos) FROM (
            SELECT (SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0))*AVG(i.CuT_Dia)/100.0 AS Finos
            FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
            JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
            WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2
            GROUP BY CAST(vrdf.fecha_turno AS date)) D),0)
        -ISNULL((SELECT SUM(cv003_tot)*0.97 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin))*
            (SELECT SUM(Ton*CuTG00/100.0)/NULLIF(SUM(Ton),0) FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin AND Fase='SRR' AND (Destino='prueba' OR Destino='CH01')),0))
        /NULLIF((ISNULL((SELECT ROUND(SUM(D.tsd),2) FROM (
            SELECT SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd
            FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
            JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
            WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2
            GROUP BY CAST(vrdf.fecha_turno AS date)) D),0)
        -ISNULL((SELECT SUM(cv003_tot)*0.97 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0)
        -ISNULL((SELECT SUM(cv202_tot) FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0)),0))*100.0 AS Ley_Cu;

    -- F8
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F8',
        ISNULL((SELECT SUM(cv002_tot)*0.97 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0),
        ISNULL((SELECT (SUM(Ton*CuTG00/100.0)/NULLIF(SUM(Ton),0))*100.0 FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin AND Fase='SRR' AND (Destino='prueba' OR Destino='CH01')),0);

    -- F9
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F9',
        ISNULL((SELECT SUM(cv003_tot)*0.97 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0),
        ISNULL((SELECT (SUM(Ton*CuTG00/100.0)/NULLIF(SUM(Ton),0))*100.0 FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin AND Fase='SRR' AND (Destino='prueba' OR Destino='CH01')),0);

    -- F10
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F10', ISNULL(SUM(cv201_tot),0), 0
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
    WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin);

    -- F11
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F11', ISNULL(SUM(cv202_tot),0), 0
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
    WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin);

    -- F12
    ;WITH D AS (
        SELECT SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd, AVG(i.CuT_Dia) AS ld
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1
        GROUP BY CAST(vrdf.fecha_turno AS date)
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F12', ISNULL(ROUND(SUM(tsd),2),0), ISNULL(ROUND(SUM(ld*tsd)/NULLIF(SUM(tsd),0),4),0) FROM D;

    -- F13
    ;WITH D AS (
        SELECT SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd, AVG(i.CuT_Dia) AS ld
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2
        GROUP BY CAST(vrdf.fecha_turno AS date)
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F13', ISNULL(ROUND(SUM(tsd),2),0), ISNULL(ROUND(SUM(ld*tsd)/NULLIF(SUM(tsd),0),4),0) FROM D;

    -- F14
    ;WITH datos_diarios_por_torre AS (
        SELECT CAST(vrdf.fecha_turno AS date) AS fecha_operacion,
               SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd, AVG(i.CuT_Dia) AS ld
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1
        GROUP BY CAST(vrdf.fecha_turno AS date)
        UNION ALL
        SELECT CAST(vrdf.fecha_turno AS date),
               SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0), AVG(i.CuT_Dia)
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2
        GROUP BY CAST(vrdf.fecha_turno AS date)
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F14', ISNULL(ROUND(SUM(dd.tsd),2),0), ISNULL(ROUND(SUM(dd.tsd*dd.ld)/NULLIF(SUM(dd.tsd),0),4),0)
    FROM datos_diarios_por_torre dd
    WHERE dd.fecha_operacion IN (
        SELECT DISTINCT DATEADD(DAY,-1,cad.fecha)
        FROM inventar_SpcHidr.control_apilado_diario cad
        WHERE cad.fecha BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin)
          AND cad.pad_id=2 AND cad.volumen_diario_m3>0);

    -- F15
    ;WITH datos_diarios_por_torre AS (
        SELECT CAST(vrdf.fecha_turno AS date) AS fecha_operacion,
               SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd, AVG(i.CuT_Dia) AS ld
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1
        GROUP BY CAST(vrdf.fecha_turno AS date)
        UNION ALL
        SELECT CAST(vrdf.fecha_turno AS date),
               SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0), AVG(i.CuT_Dia)
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2
        GROUP BY CAST(vrdf.fecha_turno AS date)
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F15', ISNULL(ROUND(SUM(dd.tsd),2),0), ISNULL(ROUND(SUM(dd.tsd*dd.ld)/NULLIF(SUM(dd.tsd),0),4),0)
    FROM datos_diarios_por_torre dd
    WHERE dd.fecha_operacion IN (
        SELECT DISTINCT DATEADD(DAY,-1,cad.fecha)
        FROM inventar_SpcHidr.control_apilado_diario cad
        WHERE cad.fecha BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin)
          AND cad.pad_id=1 AND cad.volumen_diario_m3>0);

    -- F20
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F20', ISNULL(SUM(cv025_tot*0.90),0), 0
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
    WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin);

    -- F21
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F21', ISNULL(SUM(ton_reclamo_camiones),0), 0
    FROM inventar_SpcHidr.reclamos_tonelaje
    WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin;

    -- F22
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F22', ISNULL(SUM(Camiones_TMS_Reclamo_Oxidos),0), 0
    FROM inventar_SpcHidr.Datos_conciliados_of
    WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin;

    -- F23
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F23', COALESCE(SUM(v.fino_dia),0), 100
    FROM inventar_SpcHidr.control_ley_ripio_diario v
    WHERE v.Fecha_drenaje>@fecha_inicio AND v.Fecha_drenaje<=@fecha_fin AND v.PAD='OXIDOS';

    -- F24
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F24', COALESCE(SUM(v.fino_dia),0), 100
    FROM inventar_SpcHidr.control_ley_ripio_diario v
    WHERE v.Fecha_drenaje>@fecha_inicio AND v.Fecha_drenaje<=@fecha_fin AND v.PAD='SULFUROS';

    -- F25
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F25',
        ISNULL((SELECT SUM(cv001_tot)*0.975 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno>=@fecha_inicio AND fecha_turno<DATEADD(DAY,1,@fecha_fin)),0),
        ISNULL((SELECT (SUM(Ton*CuTG00/100.0)/NULLIF(SUM(Ton),0))*100.0 FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin AND Fase='SRR' AND (Destino='prueba' OR Destino='CH01')),0);

    -------------------------------------------------------------------------
    -- 3) F18
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#tmp_f18_oficial') IS NOT NULL DROP TABLE #tmp_f18_oficial;

    ;WITH
    Tms_Apilado_Por_Modulo AS (
        SELECT mt.[campaña_id], mt.modulo_id, SUM(mt.TMS) AS tms_total_apilado
        FROM inventar_SpcHidr.modulos_turnos mt
        GROUP BY mt.[campaña_id], mt.modulo_id
    ),
    Pct_Diario AS (
        SELECT CAST(crd.fecha AS date) AS fecha, crd.pad_id, crd.[campaña_id], crd.modulo_id,
            CASE WHEN MAX(crd.avance_porcentaje)<0 THEN 0 WHEN MAX(crd.avance_porcentaje)>1 THEN 1
                 ELSE MAX(crd.avance_porcentaje) END AS pct_clip
        FROM inventar_SpcHidr.control_reclamo_diario crd
        WHERE CAST(crd.fecha AS date) BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin)
        GROUP BY CAST(crd.fecha AS date), crd.pad_id, crd.[campaña_id], crd.modulo_id
    ),
    Pct_Segmentado AS (
        SELECT p.*,
            CASE WHEN p.pct_clip < LAG(p.pct_clip,1,0) OVER (PARTITION BY p.[campaña_id],p.modulo_id,p.pad_id ORDER BY p.fecha) THEN 1 ELSE 0 END AS reset_flag
        FROM Pct_Diario p
    ),
    Pct_Seg_Id AS (
        SELECT ps.*,
            SUM(ps.reset_flag) OVER (PARTITION BY ps.[campaña_id],ps.modulo_id,ps.pad_id ORDER BY ps.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS seg_id
        FROM Pct_Segmentado ps
    ),
    Avance_Incremental_Diario AS (
        SELECT p.fecha, p.pad_id, p.[campaña_id], p.modulo_id, p.pct_clip AS avance_porcentaje,
            CASE WHEN (p.pct_clip-LAG(p.pct_clip,1,0) OVER (PARTITION BY p.[campaña_id],p.modulo_id,p.pad_id,p.seg_id ORDER BY p.fecha))<0 THEN 0
                 ELSE (p.pct_clip-LAG(p.pct_clip,1,0) OVER (PARTITION BY p.[campaña_id],p.modulo_id,p.pad_id,p.seg_id ORDER BY p.fecha)) END AS avance_incremental
        FROM Pct_Seg_Id p
    ),
    Volumen_Diario AS (
        SELECT CAST(fecha AS date) AS fecha, pad_id, [campaña_id], modulo_id, MAX(volumen_diario_m3) AS vol_m3
        FROM inventar_SpcHidr.control_reclamo_diario
        WHERE CAST(fecha AS date) BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin)
        GROUP BY CAST(fecha AS date), pad_id, [campaña_id], modulo_id
    ),
    Reclamo_Diario AS (
        SELECT DATEADD(DAY,-1,a.fecha) AS fecha_operacion, a.[campaña_id], a.modulo_id,
            (tm.tms_total_apilado*a.avance_incremental) AS tonelaje_reclamado_diario
        FROM Avance_Incremental_Diario a
        JOIN Tms_Apilado_Por_Modulo tm ON tm.[campaña_id]=a.[campaña_id] AND tm.modulo_id=a.modulo_id
        JOIN Volumen_Diario vd ON vd.fecha=a.fecha AND vd.pad_id=a.pad_id AND vd.[campaña_id]=a.[campaña_id] AND vd.modulo_id=a.modulo_id
        WHERE a.pad_id=2 AND vd.vol_m3>0
    ),
    Calculo_Tonelaje AS (SELECT COALESCE(SUM(r.tonelaje_reclamado_diario),0) AS Tonelaje FROM Reclamo_Diario r WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin),
    ModulosActivos AS (
        SELECT r.[campaña_id], r.modulo_id, SUM(r.tonelaje_reclamado_diario) AS tms_reclamado_modulo
        FROM Reclamo_Diario r WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY r.[campaña_id], r.modulo_id HAVING SUM(r.tonelaje_reclamado_diario)>0
    ),
    Calculo_Ley AS (
        SELECT COALESCE((SUM(ma.tms_reclamado_modulo*clr.ley_ripio/100.0)/NULLIF(SUM(ma.tms_reclamado_modulo),0))*100.0,0) AS Ley_Cu
        FROM ModulosActivos ma
        INNER JOIN inventar_SpcHidr.campaña c ON ma.[campaña_id]=c.[id_campaña]
        INNER JOIN inventar_SpcHidr.modulo m ON ma.modulo_id=m.id_modulo
        INNER JOIN inventar_SpcHidr.parcela p ON m.id_parcela=p.id_parcela
        INNER JOIN inventar_SpcHidr.pad pd ON p.id_pad=pd.id_pad
        INNER JOIN inventar_SpcHidr.control_ley_ripio clr ON clr.Campana=c.[numero_campaña] AND clr.Parcela=p.numero AND UPPER(clr.PAD) LIKE UPPER(pd.nombre)+'%'
        WHERE pd.id_pad=2
    )
    SELECT t.Tonelaje, l.Ley_Cu INTO #tmp_f18_oficial FROM Calculo_Tonelaje t CROSS JOIN Calculo_Ley l;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F18', Tonelaje, Ley_Cu FROM #tmp_f18_oficial;

    -------------------------------------------------------------------------
    -- 4) F19
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#tmp_f19_oficial') IS NOT NULL DROP TABLE #tmp_f19_oficial;

    ;WITH
    Tms_Apilado_Por_Modulo AS (
        SELECT mt.[campaña_id], mt.modulo_id, SUM(mt.TMS) AS tms_total_apilado
        FROM inventar_SpcHidr.modulos_turnos mt
        GROUP BY mt.[campaña_id], mt.modulo_id
    ),
    Pct_Diario AS (
        SELECT CAST(crd.fecha AS date) AS fecha, crd.pad_id, crd.[campaña_id], crd.modulo_id,
            CASE WHEN MAX(crd.avance_porcentaje)<0 THEN 0 WHEN MAX(crd.avance_porcentaje)>1 THEN 1
                 ELSE MAX(crd.avance_porcentaje) END AS pct_clip
        FROM inventar_SpcHidr.control_reclamo_diario crd
        WHERE CAST(crd.fecha AS date) BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin)
        GROUP BY CAST(crd.fecha AS date), crd.pad_id, crd.[campaña_id], crd.modulo_id
    ),
    Pct_Segmentado AS (
        SELECT p.*,
            CASE WHEN p.pct_clip < LAG(p.pct_clip,1,0) OVER (PARTITION BY p.[campaña_id],p.modulo_id,p.pad_id ORDER BY p.fecha) THEN 1 ELSE 0 END AS reset_flag
        FROM Pct_Diario p
    ),
    Pct_Seg_Id AS (
        SELECT ps.*,
            SUM(ps.reset_flag) OVER (PARTITION BY ps.[campaña_id],ps.modulo_id,ps.pad_id ORDER BY ps.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS seg_id
        FROM Pct_Segmentado ps
    ),
    Avance_Incremental_Diario AS (
        SELECT p.fecha, p.pad_id, p.[campaña_id], p.modulo_id, p.pct_clip AS avance_porcentaje,
            CASE WHEN (p.pct_clip-LAG(p.pct_clip,1,0) OVER (PARTITION BY p.[campaña_id],p.modulo_id,p.pad_id,p.seg_id ORDER BY p.fecha))<0 THEN 0
                 ELSE (p.pct_clip-LAG(p.pct_clip,1,0) OVER (PARTITION BY p.[campaña_id],p.modulo_id,p.pad_id,p.seg_id ORDER BY p.fecha)) END AS avance_incremental
        FROM Pct_Seg_Id p
    ),
    Volumen_Diario AS (
        SELECT CAST(fecha AS date) AS fecha, pad_id, [campaña_id], modulo_id, MAX(volumen_diario_m3) AS vol_m3
        FROM inventar_SpcHidr.control_reclamo_diario
        WHERE CAST(fecha AS date) BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin)
        GROUP BY CAST(fecha AS date), pad_id, [campaña_id], modulo_id
    ),
    Reclamo_Diario AS (
        SELECT DATEADD(DAY,-1,a.fecha) AS fecha_operacion, a.[campaña_id], a.modulo_id,
            (tm.tms_total_apilado*a.avance_incremental) AS tonelaje_reclamado_diario
        FROM Avance_Incremental_Diario a
        JOIN Tms_Apilado_Por_Modulo tm ON tm.[campaña_id]=a.[campaña_id] AND tm.modulo_id=a.modulo_id
        JOIN Volumen_Diario vd ON vd.fecha=a.fecha AND vd.pad_id=a.pad_id AND vd.[campaña_id]=a.[campaña_id] AND vd.modulo_id=a.modulo_id
        WHERE a.pad_id=1 AND vd.vol_m3>0
    ),
    Calculo_Tonelaje AS (SELECT COALESCE(SUM(r.tonelaje_reclamado_diario),0) AS Tonelaje FROM Reclamo_Diario r WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin),
    ModulosActivos AS (
        SELECT r.[campaña_id], r.modulo_id, SUM(r.tonelaje_reclamado_diario) AS tms_reclamado_modulo
        FROM Reclamo_Diario r WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY r.[campaña_id], r.modulo_id HAVING SUM(r.tonelaje_reclamado_diario)>0
    ),
    Calculo_Ley AS (
        SELECT COALESCE((SUM(ma.tms_reclamado_modulo*clr.ley_ripio/100.0)/NULLIF(SUM(ma.tms_reclamado_modulo),0))*100.0,0) AS Ley_Cu
        FROM ModulosActivos ma
        INNER JOIN inventar_SpcHidr.campaña c ON ma.[campaña_id]=c.[id_campaña]
        INNER JOIN inventar_SpcHidr.modulo m ON ma.modulo_id=m.id_modulo
        INNER JOIN inventar_SpcHidr.parcela p ON m.id_parcela=p.id_parcela
        INNER JOIN inventar_SpcHidr.pad pd ON p.id_pad=pd.id_pad
        INNER JOIN inventar_SpcHidr.control_ley_ripio clr ON clr.Campana=c.[numero_campaña] AND clr.Parcela=p.numero AND UPPER(clr.PAD) LIKE UPPER(pd.nombre)+'%'
        WHERE pd.id_pad=1
    )
    SELECT t.Tonelaje, l.Ley_Cu INTO #tmp_f19_oficial FROM Calculo_Tonelaje t CROSS JOIN Calculo_Ley l;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F19', Tonelaje, Ley_Cu FROM #tmp_f19_oficial;

    -------------------------------------------------------------------------
    -- 5) F16 Y F17 POR DIFERENCIA
    -------------------------------------------------------------------------
    DECLARE
        @ton_f14 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F14'),0),
        @ley_f14 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo='F14'),0),
        @ton_f18 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F18'),0),
        @ley_f18 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo='F18'),0),
        @ton_f21 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F21'),0),
        @ley_f21 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo='F21'),0),
        @ton_f24 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F24'),0),
        @ley_f24 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo='F24'),0),
        @ton_f15 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F15'),0),
        @ley_f15 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo='F15'),0),
        @ton_f19 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F19'),0),
        @ley_f19 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo='F19'),0),
        @ton_f22 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F22'),0),
        @ley_f22 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo='F22'),0),
        @ton_f23 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F23'),0),
        @ley_f23 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo='F23'),0);

    DECLARE @ton_f16 decimal(18,6), @ley_f16 decimal(18,6), @ton_f17 decimal(18,6), @ley_f17 decimal(18,6);

    SET @ton_f16 = @ton_f14-@ton_f18-@ton_f21-@ton_f24;
    SET @ley_f16 = CASE WHEN @ton_f16=0 THEN 0 ELSE ((@ton_f14*@ley_f14)-(@ton_f18*@ley_f18)-(@ton_f21*@ley_f18)-(@ton_f24*@ley_f24))/@ton_f16 END;
    SET @ton_f17 = @ton_f15-@ton_f19-@ton_f22-@ton_f23;
    SET @ley_f17 = CASE WHEN @ton_f17=0 THEN 0 ELSE ((@ton_f15*@ley_f15)-(@ton_f19*@ley_f19)-(@ton_f22*@ley_f19)-(@ton_f23*@ley_f23))/@ton_f17 END;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F16',@ton_f16,@ley_f16), ('F17',@ton_f17,@ley_f17);

    -------------------------------------------------------------------------
    -- 6) INVENTARIO INICIAL DE F16 Y F17
    -------------------------------------------------------------------------
    DECLARE
        @ton14_i decimal(18,6)=0, @ley14_i decimal(18,6)=0,
        @ton15_i decimal(18,6)=0, @ley15_i decimal(18,6)=0,
        @ton18_i decimal(18,6)=0, @ley18_i decimal(18,6)=0,
        @ton19_i decimal(18,6)=0, @ley19_i decimal(18,6)=0,
        @tms_ini_f16 decimal(18,6)=0, @ley_ini_f16 decimal(18,6)=0,
        @tms_ini_f17 decimal(18,6)=0, @ley_ini_f17 decimal(18,6)=0;

    ;WITH datos_diarios_por_torre AS (
        SELECT CAST(vrdf.fecha_turno AS date) AS fecha_operacion,
               SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd, AVG(i.CuT_Dia) AS ld
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_inicio) AND i.id_torre=1
        GROUP BY CAST(vrdf.fecha_turno AS date)
        UNION ALL
        SELECT CAST(vrdf.fecha_turno AS date),
               SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0), AVG(i.CuT_Dia)
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_inicio) AND i.id_torre=2
        GROUP BY CAST(vrdf.fecha_turno AS date)
    )
    SELECT @ton14_i=ISNULL(ROUND(SUM(dd.tsd),2),0), @ley14_i=ISNULL(ROUND(SUM(dd.tsd*dd.ld)/NULLIF(SUM(dd.tsd),0),4),0)
    FROM datos_diarios_por_torre dd
    WHERE dd.fecha_operacion IN (SELECT DISTINCT DATEADD(DAY,-1,cad.fecha) FROM inventar_SpcHidr.control_apilado_diario cad WHERE cad.fecha BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_inicio) AND cad.pad_id=2 AND cad.volumen_diario_m3>0);

    ;WITH datos_diarios_por_torre AS (
        SELECT CAST(vrdf.fecha_turno AS date) AS fecha_operacion,
               SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd, AVG(i.CuT_Dia) AS ld
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_inicio) AND i.id_torre=1
        GROUP BY CAST(vrdf.fecha_turno AS date)
        UNION ALL
        SELECT CAST(vrdf.fecha_turno AS date),
               SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0), AVG(i.CuT_Dia)
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_inicio) AND i.id_torre=2
        GROUP BY CAST(vrdf.fecha_turno AS date)
    )
    SELECT @ton15_i=ISNULL(ROUND(SUM(dd.tsd),2),0), @ley15_i=ISNULL(ROUND(SUM(dd.tsd*dd.ld)/NULLIF(SUM(dd.tsd),0),4),0)
    FROM datos_diarios_por_torre dd
    WHERE dd.fecha_operacion IN (SELECT DISTINCT DATEADD(DAY,-1,cad.fecha) FROM inventar_SpcHidr.control_apilado_diario cad WHERE cad.fecha BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_inicio) AND cad.pad_id=1 AND cad.volumen_diario_m3>0);

    SELECT @ton18_i=Tonelaje, @ley18_i=Ley_Cu FROM #tmp_f18_oficial;
    SELECT @ton19_i=Tonelaje, @ley19_i=Ley_Cu FROM #tmp_f19_oficial;

    SET @tms_ini_f16=@ton14_i-@ton18_i;
    SET @ley_ini_f16=CASE WHEN @tms_ini_f16=0 THEN 0 ELSE ((@ton14_i*@ley14_i)-(@ton18_i*@ley18_i))/@tms_ini_f16 END;
    SET @tms_ini_f17=@ton15_i-@ton19_i;
    SET @ley_ini_f17=CASE WHEN @tms_ini_f17=0 THEN 0 ELSE ((@ton15_i*@ley15_i)-(@ton19_i*@ley19_i))/@tms_ini_f17 END;

    UPDATE #flujos_resultado SET TMS_Inicial=@tms_ini_f16, Ley_Cu_1=@ley_ini_f16 WHERE codigo_flujo='F16';
    UPDATE #flujos_resultado SET TMS_Inicial=@tms_ini_f17, Ley_Cu_1=@ley_ini_f17 WHERE codigo_flujo='F17';

    -------------------------------------------------------------------------
    -- 7) AJUSTES FINALES DE LEYES
    -------------------------------------------------------------------------
    UPDATE #flujos_resultado SET Ley_Cu=@ley_f18 WHERE codigo_flujo='F21';
    UPDATE #flujos_resultado SET Ley_Cu=@ley_f19 WHERE codigo_flujo='F22';
    UPDATE #flujos_resultado SET Ley_Cu=CASE WHEN (@ton_f18+@ton_f19)=0 THEN 0 ELSE ((@ton_f18*@ley_f18)+(@ton_f19*@ley_f19))/(@ton_f18+@ton_f19) END WHERE codigo_flujo='F20';

    -------------------------------------------------------------------------
    -- 8) FLUJOS F26..F120
    -------------------------------------------------------------------------

    -- F26
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F26', COALESCE(SUM(v.fino_dia),0), 0
    FROM inventar_SpcHidr.control_ley_ripio_diario v
    WHERE v.Fecha_drenaje>@fecha_inicio AND v.Fecha_drenaje<=@fecha_fin AND v.PAD='OXIDOS';

    -- F27
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F27', COALESCE(SUM(v.fino_dia),0), 0
    FROM inventar_SpcHidr.control_ley_ripio_diario v
    WHERE v.Fecha_drenaje>@fecha_inicio AND v.Fecha_drenaje<=@fecha_fin AND v.PAD='SULFUROS';

    -- F28
    ;WITH base_f28 AS (SELECT COALESCE(t.acido_aglomerado_1_m3h,0)*1.84 AS flujo_ton_dia FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F28', COALESCE(SUM(flujo_ton_dia),0), 0.0 FROM base_f28;

    -- F29
    ;WITH base_f29 AS (SELECT COALESCE(t.acido_aglomerado_100_m3h,0)*1.84 AS flujo_ton_dia FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F29', COALESCE(SUM(flujo_ton_dia),0), 0.0 FROM base_f29;

    -- F30-F34, F36
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F30',0,0),('F31',0,0),('F32',0,0),('F33',0,0),('F34',0,0),('F36',0,0);

    -- F37
    ;WITH flujo_diario AS (
        SELECT CAST(t.fecha_inicio AS date) AS fecha, COALESCE(SUM(t.flujo_dpls_m3h),0) AS flujo_m3_dia
        FROM inventar_SpcHidr.tags_sx_ew t
        WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin)
        GROUP BY CAST(t.fecha_inicio AS date)
    ),
    cu_diario AS (SELECT CAST(c.fecha_registro AS date) AS fecha, COALESCE(c.dump_dpls_cu,0) AS cu_g_l FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    base AS (SELECT fd.flujo_m3_dia, cd.cu_g_l FROM flujo_diario fd INNER JOIN cu_diario cd ON fd.fecha=cd.fecha)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F37', COALESCE(SUM(flujo_m3_dia),0), COALESCE(SUM(flujo_m3_dia*cu_g_l)/NULLIF(SUM(flujo_m3_dia),0),0)/10.0 FROM base;

    -- F38
    ;WITH flujo_diario AS (
        SELECT CAST(t.fecha_inicio AS date) AS fecha, COALESCE(SUM(t.flujo_feed_dump_m3h),0) AS flujo_m3_dia
        FROM inventar_SpcHidr.tags_sx_ew t
        WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin)
        GROUP BY CAST(t.fecha_inicio AS date)
    ),
    cu_diario AS (SELECT CAST(c.fecha_registro AS date) AS fecha, COALESCE(c.dump_feed_cu,0) AS cu_g_l FROM inventar_SpcHidr.conc_cu c WHERE c.fecha_registro>=@fecha_inicio AND c.fecha_registro<DATEADD(DAY,1,@fecha_fin)),
    base AS (SELECT fd.flujo_m3_dia, cd.cu_g_l FROM flujo_diario fd INNER JOIN cu_diario cd ON fd.fecha=cd.fecha)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F38', COALESCE(SUM(flujo_m3_dia),0), COALESCE(SUM(flujo_m3_dia*cu_g_l)/NULLIF(SUM(flujo_m3_dia),0),0)/10.0 FROM base;

    -- F35 = F38 - F37
    ;WITH f37 AS (SELECT COALESCE(Tonelaje,0) AS Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F37'),
          f38 AS (SELECT COALESCE(Tonelaje,0) AS Tonelaje, COALESCE(Ley_Cu,0) AS Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F38')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F35', COALESCE(f38.Tonelaje,0)-COALESCE(f37.Tonelaje,0), COALESCE(f38.Ley_Cu,0) FROM f37 CROSS JOIN f38;

    -- F39
    ;WITH flujo_diario AS (
        SELECT CAST(f.fecha_registro AS date) AS fecha,
            (COALESCE(f.parcela_01,0)+COALESCE(f.parcela_02,0)+COALESCE(f.parcela_03,0)+COALESCE(f.parcela_04,0)+COALESCE(f.parcela_05,0)+COALESCE(f.parcela_06,0)+COALESCE(f.parcela_07,0)+COALESCE(f.parcela_08,0)+COALESCE(f.parcela_09,0)+COALESCE(f.parcela_10,0)+COALESCE(f.parcela_11,0)+COALESCE(f.parcela_12,0)+COALESCE(f.parcela_13,0)+COALESCE(f.parcela_14,0)+COALESCE(f.parcela_15,0)+COALESCE(f.parcela_16,0)+COALESCE(f.parcela_17,0)+COALESCE(f.parcela_18,0)+COALESCE(f.parcela_19,0)+COALESCE(f.parcela_20,0)+COALESCE(f.parcela_21,0)+COALESCE(f.parcela_22,0)+COALESCE(f.parcela_23,0)+COALESCE(f.parcela_24,0)+COALESCE(f.parcela_25,0)+COALESCE(f.parcela_26,0)+COALESCE(f.parcela_27,0)+COALESCE(f.parcela_28,0)+COALESCE(f.parcela_29,0)+COALESCE(f.parcela_30,0)+COALESCE(f.parcela_31,0)+COALESCE(f.parcela_32,0))*24.0 AS flujo_ton_dia
        FROM inventar_SpcHidr.flujos_reales_oxido f WHERE CAST(f.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    cu_diario AS (SELECT CAST(c.fecha_registro AS date) AS fecha, COALESCE(c.oxidos_refino_cu,0) AS cu_g_l FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    base AS (SELECT fd.flujo_ton_dia, cd.cu_g_l FROM flujo_diario fd INNER JOIN cu_diario cd ON fd.fecha=cd.fecha)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F39', COALESCE(SUM(flujo_ton_dia),0), COALESCE(SUM(flujo_ton_dia*cu_g_l)/NULLIF(SUM(flujo_ton_dia),0),0)/10.0 FROM base;

    -- F40 y F42 (proporcionales a F15 y F14 respectivamente)
    ;WITH datos_f14 AS (
        SELECT CAST(vrdf.fecha_turno AS date) AS fecha_operacion, SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1 GROUP BY CAST(vrdf.fecha_turno AS date)
        UNION ALL
        SELECT CAST(vrdf.fecha_turno AS date), SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0)
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2 GROUP BY CAST(vrdf.fecha_turno AS date)
    ),
    f14_ton AS (SELECT ISNULL(ROUND(SUM(dd.tsd),2),0) AS tonelaje_f14 FROM datos_f14 dd WHERE dd.fecha_operacion IN (SELECT DISTINCT DATEADD(DAY,-1,cad.fecha) FROM inventar_SpcHidr.control_apilado_diario cad WHERE cad.fecha BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin) AND cad.pad_id=2 AND cad.volumen_diario_m3>0)),
    datos_f15 AS (
        SELECT CAST(vrdf.fecha_turno AS date) AS fecha_operacion, SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1 GROUP BY CAST(vrdf.fecha_turno AS date)
        UNION ALL
        SELECT CAST(vrdf.fecha_turno AS date), SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0)
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2 GROUP BY CAST(vrdf.fecha_turno AS date)
    ),
    f15_ton AS (SELECT ISNULL(ROUND(SUM(dd.tsd),2),0) AS tonelaje_f15 FROM datos_f15 dd WHERE dd.fecha_operacion IN (SELECT DISTINCT DATEADD(DAY,-1,cad.fecha) FROM inventar_SpcHidr.control_apilado_diario cad WHERE cad.fecha BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin) AND cad.pad_id=1 AND cad.volumen_diario_m3>0)),
    proporcion AS (
        SELECT COALESCE(f14_ton.tonelaje_f14/NULLIF(f14_ton.tonelaje_f14+f15_ton.tonelaje_f15,0),0) AS prop_f14,
               COALESCE(f15_ton.tonelaje_f15/NULLIF(f14_ton.tonelaje_f14+f15_ton.tonelaje_f15,0),0) AS prop_f15
        FROM f14_ton CROSS JOIN f15_ton
    ),
    total_f40_f42 AS (
        SELECT COALESCE(SUM(COALESCE(t.refino_ox_aglomerado_1_m3h,0)+COALESCE(t.refino_ox_aglomerado_100_m3h,0)),0) AS total_ton,
               COALESCE(SUM((COALESCE(t.refino_ox_aglomerado_1_m3h,0)+COALESCE(t.refino_ox_aglomerado_100_m3h,0))*COALESCE(t.refino_ox_aglomerado_100_cu_gl,0))/NULLIF(SUM(COALESCE(t.refino_ox_aglomerado_1_m3h,0)+COALESCE(t.refino_ox_aglomerado_100_m3h,0)),0),0)/10.0 AS ley_pct
        FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin)
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F40', COALESCE(b.total_ton*p.prop_f15,0), COALESCE(b.ley_pct,0) FROM total_f40_f42 b CROSS JOIN proporcion p;

    ;WITH datos_f14 AS (
        SELECT CAST(vrdf.fecha_turno AS date) AS fecha_operacion, SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1 GROUP BY CAST(vrdf.fecha_turno AS date)
        UNION ALL
        SELECT CAST(vrdf.fecha_turno AS date), SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0)
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2 GROUP BY CAST(vrdf.fecha_turno AS date)
    ),
    f14_ton AS (SELECT ISNULL(ROUND(SUM(dd.tsd),2),0) AS tonelaje_f14 FROM datos_f14 dd WHERE dd.fecha_operacion IN (SELECT DISTINCT DATEADD(DAY,-1,cad.fecha) FROM inventar_SpcHidr.control_apilado_diario cad WHERE cad.fecha BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin) AND cad.pad_id=2 AND cad.volumen_diario_m3>0)),
    datos_f15 AS (
        SELECT CAST(vrdf.fecha_turno AS date) AS fecha_operacion, SUM(vrdf.cv008_tot)*(1-AVG(i.Humedades_Dia)/100.0) AS tsd
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=1 GROUP BY CAST(vrdf.fecha_turno AS date)
        UNION ALL
        SELECT CAST(vrdf.fecha_turno AS date), SUM(vrdf.cv108_tot)*(1-AVG(i.Humedades_Dia)/100.0)
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS date)=i.fecha
        WHERE vrdf.fecha_turno>=@fecha_inicio AND vrdf.fecha_turno<DATEADD(DAY,1,@fecha_fin) AND i.id_torre=2 GROUP BY CAST(vrdf.fecha_turno AS date)
    ),
    f15_ton AS (SELECT ISNULL(ROUND(SUM(dd.tsd),2),0) AS tonelaje_f15 FROM datos_f15 dd WHERE dd.fecha_operacion IN (SELECT DISTINCT DATEADD(DAY,-1,cad.fecha) FROM inventar_SpcHidr.control_apilado_diario cad WHERE cad.fecha BETWEEN @fecha_inicio AND DATEADD(DAY,1,@fecha_fin) AND cad.pad_id=1 AND cad.volumen_diario_m3>0)),
    proporcion AS (
        SELECT COALESCE(f14_ton.tonelaje_f14/NULLIF(f14_ton.tonelaje_f14+f15_ton.tonelaje_f15,0),0) AS prop_f14,
               COALESCE(f15_ton.tonelaje_f15/NULLIF(f14_ton.tonelaje_f14+f15_ton.tonelaje_f15,0),0) AS prop_f15
        FROM f14_ton CROSS JOIN f15_ton
    ),
    total_f40_f42 AS (
        SELECT COALESCE(SUM(COALESCE(t.refino_ox_aglomerado_1_m3h,0)+COALESCE(t.refino_ox_aglomerado_100_m3h,0)),0) AS total_ton,
               COALESCE(SUM((COALESCE(t.refino_ox_aglomerado_1_m3h,0)+COALESCE(t.refino_ox_aglomerado_100_m3h,0))*COALESCE(t.refino_ox_aglomerado_100_cu_gl,0))/NULLIF(SUM(COALESCE(t.refino_ox_aglomerado_1_m3h,0)+COALESCE(t.refino_ox_aglomerado_100_m3h,0)),0),0)/10.0 AS ley_pct
        FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin)
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F42', COALESCE(b.total_ton*p.prop_f14,0), COALESCE(b.ley_pct,0) FROM total_f40_f42 b CROSS JOIN proporcion p;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F41',0,0),('F43',0,0),('F45',0,0),('F46',0,0),('F47',0,0);

    -- F44
    ;WITH flujo_diario AS (
        SELECT CAST(f.fecha_registro AS date) AS fecha,
            (COALESCE(f.parcela_01,0)+COALESCE(f.parcela_02,0)+COALESCE(f.parcela_03,0)+COALESCE(f.parcela_04,0)+COALESCE(f.parcela_05,0)+COALESCE(f.parcela_06,0)+COALESCE(f.parcela_07,0)+COALESCE(f.parcela_08,0)+COALESCE(f.parcela_09,0)+COALESCE(f.parcela_10,0)+COALESCE(f.parcela_11,0)+COALESCE(f.parcela_12,0)+COALESCE(f.parcela_13,0)+COALESCE(f.parcela_14,0)+COALESCE(f.parcela_15,0)+COALESCE(f.parcela_16,0)+COALESCE(f.parcela_17,0)+COALESCE(f.parcela_18,0)+COALESCE(f.parcela_19,0)+COALESCE(f.parcela_20,0)+COALESCE(f.parcela_21,0)+COALESCE(f.parcela_22,0)+COALESCE(f.parcela_23,0)+COALESCE(f.parcela_24,0)+COALESCE(f.parcela_25,0)+COALESCE(f.parcela_26,0)+COALESCE(f.parcela_27,0)+COALESCE(f.parcela_28,0))*24.0 AS flujo_ton_dia
        FROM inventar_SpcHidr.flujos_reales_sulfuro f WHERE CAST(f.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    cu_diario AS (SELECT CAST(c.fecha_registro AS date) AS fecha, COALESCE(c.sulfuros_refino_cu,0) AS cu_g_l FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    base AS (SELECT fd.flujo_ton_dia, cd.cu_g_l FROM flujo_diario fd INNER JOIN cu_diario cd ON fd.fecha=cd.fecha)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F44', COALESCE(SUM(flujo_ton_dia),0), COALESCE(SUM(flujo_ton_dia*cu_g_l)/NULLIF(SUM(flujo_ton_dia),0),0)/10.0 FROM base;

    -- F48
    ;WITH flujo_f48 AS (
        SELECT CAST(f.fecha_registro AS date) AS fecha,
            (COALESCE(f.parcela_01,0)+COALESCE(f.parcela_02,0)+COALESCE(f.parcela_03,0)+COALESCE(f.parcela_04,0)+COALESCE(f.parcela_05,0)+COALESCE(f.parcela_06,0)+COALESCE(f.parcela_07,0)+COALESCE(f.parcela_08,0)+COALESCE(f.parcela_09,0)+COALESCE(f.parcela_10,0)+COALESCE(f.parcela_11,0)+COALESCE(f.parcela_12,0)+COALESCE(f.parcela_13,0)+COALESCE(f.parcela_14,0)+COALESCE(f.parcela_15,0)+COALESCE(f.parcela_16,0)+COALESCE(f.parcela_17,0)+COALESCE(f.parcela_18,0)+COALESCE(f.parcela_19,0)+COALESCE(f.parcela_20,0)+COALESCE(f.parcela_21,0)+COALESCE(f.parcela_22,0)+COALESCE(f.parcela_23,0)+COALESCE(f.parcela_24,0)+COALESCE(f.parcela_25,0)+COALESCE(f.parcela_26,0)+COALESCE(f.parcela_27,0)+COALESCE(f.parcela_28,0)+COALESCE(f.parcela_29,0)+COALESCE(f.parcela_30,0)+COALESCE(f.parcela_31,0)+COALESCE(f.parcela_32,0))*24.0*0.95 AS flujo_ton_dia
        FROM inventar_SpcHidr.flujos_reales_oxido f WHERE CAST(f.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f48 AS (SELECT CAST(p.fecha_registro AS date) AS fecha, NULLIF(p.ingreso_piscina_pls_cu_pp,0) AS cu_g_l FROM inventar_SpcHidr.riego_concentrados_oxido p WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    base AS (SELECT f.flujo_ton_dia, l.cu_g_l FROM flujo_f48 f INNER JOIN ley_f48 l ON f.fecha=l.fecha)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F48', COALESCE(SUM(flujo_ton_dia),0), COALESCE(SUM(CASE WHEN cu_g_l IS NOT NULL THEN flujo_ton_dia*cu_g_l END)/NULLIF(SUM(CASE WHEN cu_g_l IS NOT NULL THEN flujo_ton_dia END),0),0)/10.0 FROM base;

    -- F49
    ;WITH flujo_f49 AS (SELECT CAST(r.fecha_registro AS date) AS fecha, COALESCE(r.bleed,0)*24.0 AS flujo_ton_dia FROM inventar_SpcHidr.riego_bleed r WHERE CAST(r.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f49 AS (SELECT CAST(p.fecha_registro AS date) AS fecha, NULLIF(p.bleed_cu_pp,0) AS cu_g_l FROM inventar_SpcHidr.riego_concentrados_oxido p WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    base AS (SELECT f.flujo_ton_dia, l.cu_g_l FROM flujo_f49 f INNER JOIN ley_f49 l ON f.fecha=l.fecha)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F49', COALESCE(SUM(flujo_ton_dia),0), COALESCE(SUM(CASE WHEN cu_g_l IS NOT NULL THEN flujo_ton_dia*cu_g_l END)/NULLIF(SUM(CASE WHEN cu_g_l IS NOT NULL THEN flujo_ton_dia END),0),0)/10.0 FROM base;

    -- F50
    ;WITH f44 AS (SELECT TOP 1 Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F44'),
          f49 AS (SELECT TOP 1 Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F49'),
          ley_f50 AS (SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F50', (COALESCE(f44.Tonelaje,0)*0.95-COALESCE(f49.Tonelaje,0)), COALESCE(lf50.Ley_Cu,0)
    FROM f44 CROSS JOIN f49 CROSS JOIN ley_f50 lf50;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F51',0,0);

    -- F52
    ;WITH flujo_diario AS (
        SELECT CAST(t.fecha_inicio AS date) AS fecha, COALESCE(SUM(t.flujo_refino_feed_dump_m3h),0) AS flujo_m3_dia
        FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin)
        GROUP BY CAST(t.fecha_inicio AS date)
    ),
    cu_diario AS (SELECT CAST(c.fecha_registro AS date) AS fecha, COALESCE(c.oxidos_refino_cu,0) AS cu_g_l FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    base AS (SELECT fd.flujo_m3_dia, cd.cu_g_l FROM flujo_diario fd INNER JOIN cu_diario cd ON fd.fecha=cd.fecha)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F52', COALESCE(SUM(flujo_m3_dia),0), COALESCE(SUM(flujo_m3_dia*cu_g_l)/NULLIF(SUM(flujo_m3_dia),0),0)/10.0 FROM base;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F56',0,0);

    -- F57
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F57', COALESCE(Tonelaje,0)*0.07, 0.0 FROM #tmp_f18_oficial;

    -- F58
    ;WITH f44 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F44')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F58', COALESCE(Tonelaje,0)*0.05, 0.0 FROM f44;

    -- F59
    ;WITH base_f59 AS (SELECT COALESCE(t.agua_refino_sulf_m3h,0) AS flujo_ton_dia FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F59', COALESCE(SUM(flujo_ton_dia),0), 0.0 FROM base_f59;

    -- F60
    ;WITH volumen_inicial AS (SELECT TOP 1 COALESCE(i.volumen_ref_sulfuros,0)*1.0 AS TMS_Inicial FROM inventar_SpcHidr.inv_sol_sulfuros i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) ASC),
    volumen_final AS (SELECT TOP 1 COALESCE(i.volumen_ref_sulfuros,0)*1.0 AS TMS_Final FROM inventar_SpcHidr.inv_sol_sulfuros i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) DESC),
    ley_inicial AS (SELECT TOP 1 COALESCE(c.sulfuros_refino_cu,0) AS Ley_i_gL FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(c.fecha_registro AS date) ASC),
    ley_final AS (SELECT TOP 1 COALESCE(c.sulfuros_refino_cu,0) AS Ley_f_gL FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(c.fecha_registro AS date) DESC)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT 'F60', vi.TMS_Inicial, li.Ley_i_gL/10.0, vf.TMS_Final, lf.Ley_f_gL/10.0, (vf.TMS_Final-vi.TMS_Inicial), COALESCE((((vf.TMS_Final*lf.Ley_f_gL)-(vi.TMS_Inicial*li.Ley_i_gL))/NULLIF((vf.TMS_Final-vi.TMS_Inicial),0))/10.0,0)
    FROM volumen_inicial vi CROSS JOIN volumen_final vf CROSS JOIN ley_inicial li CROSS JOIN ley_final lf;

    -- F55
    ;WITH f44 AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F44'),
          f60 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F60'),
          f43 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F43'),
          f59 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F59')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F55', ((COALESCE(f44.Tonelaje,0)+COALESCE(f60.Tonelaje,0)+COALESCE(f43.Tonelaje,0))/0.95)-COALESCE(f59.Tonelaje,0), COALESCE(f44.Ley_Cu,0)
    FROM f44 CROSS JOIN f60 CROSS JOIN f43 CROSS JOIN f59;

    -- F61
    ;WITH f55 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F55'), f59 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F59')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F61', (COALESCE(f55.Tonelaje,0)+COALESCE(f59.Tonelaje,0))*0.05, 0.0 FROM f55 CROSS JOIN f59;

    -- F62
    ;WITH f51 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F51')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F62', COALESCE(Tonelaje,0)*0.005, 0.0 FROM f51;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F63',0,0);

    -- F64
    ;WITH f50 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F50')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F64', COALESCE(Tonelaje,0)*0.005, 0.0 FROM f50;

    -- F65
    ;WITH volumen_inicial AS (SELECT TOP 1 COALESCE(i.volumen_pls_sulfuros,0)*1.0 AS TMS_Inicial FROM inventar_SpcHidr.inv_sol_sulfuros i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) ASC),
    volumen_final AS (SELECT TOP 1 COALESCE(i.volumen_pls_sulfuros,0)*1.0 AS TMS_Final FROM inventar_SpcHidr.inv_sol_sulfuros i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) DESC),
    ley_inicial AS (SELECT TOP 1 COALESCE(c.sulfuros_pls_a_sx_cu,0) AS Ley_i_gL FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(c.fecha_registro AS date) ASC),
    ley_final AS (SELECT TOP 1 COALESCE(c.sulfuros_pls_a_sx_cu,0) AS Ley_f_gL FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(c.fecha_registro AS date) DESC)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT 'F65', vi.TMS_Inicial, li.Ley_i_gL/10.0, vf.TMS_Final, lf.Ley_f_gL/10.0, (vf.TMS_Final-vi.TMS_Inicial), COALESCE((((vf.TMS_Final*lf.Ley_f_gL)-(vi.TMS_Inicial*li.Ley_i_gL))/NULLIF((vf.TMS_Final-vi.TMS_Inicial),0))/10.0,0)
    FROM volumen_inicial vi CROSS JOIN volumen_final vf CROSS JOIN ley_inicial li CROSS JOIN ley_final lf;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F66',0,0);

    -- F67
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F67', COALESCE(Tonelaje,0)*0.07, 0.0 FROM #tmp_f19_oficial;

    -- F68
    ;WITH f39 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F39'), f43 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F43')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F68', (COALESCE(f39.Tonelaje,0)+COALESCE(f43.Tonelaje,0))*0.05, 0.0 FROM f39 CROSS JOIN f43;

    -- F69
    ;WITH inv_i AS (SELECT COALESCE(AVG(i.volumen_pond_dpls),0) AS inventario_inicial FROM inventar_SpcHidr.inv_sol_oxidos i WHERE CAST(i.fecha_registro AS date)=@fecha_inicio),
    inv_f AS (SELECT COALESCE(AVG(i.volumen_pond_dpls),0) AS inventario_final FROM inventar_SpcHidr.inv_sol_oxidos i WHERE CAST(i.fecha_registro AS date)=@fecha_fin),
    ley_i AS (SELECT COALESCE(AVG(c.dump_dpls_cu),0) AS ley_inicial FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date)=@fecha_inicio),
    ley_f AS (SELECT COALESCE(AVG(c.dump_dpls_cu),0) AS ley_final FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date)=@fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT 'F69', COALESCE(inv_i.inventario_inicial,0), COALESCE(ley_i.ley_inicial,0)/10.0, COALESCE(inv_f.inventario_final,0), COALESCE(ley_f.ley_final,0)/10.0,
        COALESCE(inv_f.inventario_final,0)-COALESCE(inv_i.inventario_inicial,0),
        CASE WHEN (COALESCE(inv_f.inventario_final,0)-COALESCE(inv_i.inventario_inicial,0))=0 THEN 0
             ELSE ((COALESCE(inv_f.inventario_final,0)*(COALESCE(ley_f.ley_final,0)/10.0))-(COALESCE(inv_i.inventario_inicial,0)*(COALESCE(ley_i.ley_inicial,0)/10.0)))/NULLIF(COALESCE(inv_f.inventario_final,0)-COALESCE(inv_i.inventario_inicial,0),0) END
    FROM inv_i CROSS JOIN inv_f CROSS JOIN ley_i CROSS JOIN ley_f;

    -- F53
    ;WITH f37 AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F37'),
          f46 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F46'),
          f69 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F69')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F53', CASE WHEN (COALESCE(f37.Tonelaje,0)*0.95)-COALESCE(f46.Tonelaje,0)-COALESCE(f69.Tonelaje,0)<0 THEN 0 ELSE (COALESCE(f37.Tonelaje,0)*0.95)-COALESCE(f46.Tonelaje,0)-COALESCE(f69.Tonelaje,0) END, COALESCE(f37.Ley_Cu,0)
    FROM f37 CROSS JOIN f46 CROSS JOIN f69;

    -- F70
    ;WITH inv_i AS (SELECT COALESCE(AVG(i.volumen_refino_dump),0) AS inventario_inicial FROM inventar_SpcHidr.inv_sol_oxidos i WHERE CAST(i.fecha_registro AS date)=@fecha_inicio),
    inv_f AS (SELECT COALESCE(AVG(i.volumen_refino_dump),0) AS inventario_final FROM inventar_SpcHidr.inv_sol_oxidos i WHERE CAST(i.fecha_registro AS date)=@fecha_fin),
    ley_i AS (SELECT COALESCE(AVG(c.dump_feed_cu),0) AS ley_inicial FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date)=@fecha_inicio),
    ley_f AS (SELECT COALESCE(AVG(c.dump_feed_cu),0) AS ley_final FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date)=@fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT 'F70', COALESCE(inv_i.inventario_inicial,0), COALESCE(ley_i.ley_inicial,0)/10.0, COALESCE(inv_f.inventario_final,0), COALESCE(ley_f.ley_final,0)/10.0,
        COALESCE(inv_f.inventario_final,0)-COALESCE(inv_i.inventario_inicial,0),
        CASE WHEN (COALESCE(inv_f.inventario_final,0)-COALESCE(inv_i.inventario_inicial,0))=0 THEN 0
             ELSE ((COALESCE(inv_f.inventario_final,0)*(COALESCE(ley_f.ley_final,0)/10.0))-(COALESCE(inv_i.inventario_inicial,0)*(COALESCE(ley_i.ley_inicial,0)/10.0)))/NULLIF(COALESCE(inv_f.inventario_final,0)-COALESCE(inv_i.inventario_inicial,0),0) END
    FROM inv_i CROSS JOIN inv_f CROSS JOIN ley_i CROSS JOIN ley_f;

    -- F71
    ;WITH f37 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F37')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F71', COALESCE(f37.Tonelaje,0)*0.05, 0.0 FROM f37;

    -- F72
    ;WITH f38 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F38')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F72', COALESCE(f38.Tonelaje,0)*0.05, 0.0 FROM f38;

    -- F73
    ;WITH volumen_inicial AS (SELECT TOP 1 COALESCE(i.volumen_refino_oxidos,0)*1.0 AS TMS_Inicial FROM inventar_SpcHidr.inv_sol_oxidos i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) ASC),
    volumen_final AS (SELECT TOP 1 COALESCE(i.volumen_refino_oxidos,0)*1.0 AS TMS_Final FROM inventar_SpcHidr.inv_sol_oxidos i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) DESC),
    ley_inicial AS (SELECT TOP 1 COALESCE(c.oxidos_refino_cu,0) AS Ley_i_gL FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(c.fecha_registro AS date) ASC),
    ley_final AS (SELECT TOP 1 COALESCE(c.oxidos_refino_cu,0) AS Ley_f_gL FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(c.fecha_registro AS date) DESC)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT 'F73', vi.TMS_Inicial, li.Ley_i_gL/10.0, vf.TMS_Final, lf.Ley_f_gL/10.0, vf.TMS_Final-vi.TMS_Inicial,
        CASE WHEN vf.TMS_Final-vi.TMS_Inicial=0 THEN 0 ELSE ((li.Ley_i_gL+lf.Ley_f_gL)/2.0)/10.0 END
    FROM volumen_inicial vi CROSS JOIN volumen_final vf CROSS JOIN ley_inicial li CROSS JOIN ley_final lf;

    -- F54
    ;WITH f39 AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F39'),
          f40 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F40'),
          f42 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F42'),
          f52 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F52'),
          f73 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F73')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F54', (COALESCE(f39.Tonelaje,0)+COALESCE(f40.Tonelaje,0)+COALESCE(f42.Tonelaje,0)+COALESCE(f52.Tonelaje,0)+COALESCE(f73.Tonelaje,0))/0.95, COALESCE(f39.Ley_Cu,0)
    FROM f39 CROSS JOIN f40 CROSS JOIN f42 CROSS JOIN f52 CROSS JOIN f73;

    -- F74
    ;WITH f54 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F54')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F74', COALESCE(Tonelaje,0)*0.05, 0.0 FROM f54;

    -- F75
    ;WITH f47 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F47')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F75', COALESCE(Tonelaje,0)*0.005, 0.0 FROM f47;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F76',0,0);

    -- F77
    ;WITH f48 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F48'), f49 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F49')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F77', (COALESCE(f48.Tonelaje,0)+COALESCE(f49.Tonelaje,0))*0.005, 0.0 FROM f48 CROSS JOIN f49;

    -- F78
    ;WITH volumen_inicial AS (SELECT TOP 1 COALESCE(i.volumen_pls_oxido,0)*1.0 AS TMS_Inicial FROM inventar_SpcHidr.inv_sol_oxidos i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) ASC),
    volumen_final AS (SELECT TOP 1 COALESCE(i.volumen_pls_oxido,0)*1.0 AS TMS_Final FROM inventar_SpcHidr.inv_sol_oxidos i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) DESC),
    ley_inicial AS (SELECT TOP 1 COALESCE(c.oxidos_pls_a_sx_cu,0) AS Ley_i_gL FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(c.fecha_registro AS date) ASC),
    ley_final AS (SELECT TOP 1 COALESCE(c.oxidos_pls_a_sx_cu,0) AS Ley_f_gL FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(c.fecha_registro AS date) DESC)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT 'F78', vi.TMS_Inicial, li.Ley_i_gL/10.0, vf.TMS_Final, lf.Ley_f_gL/10.0, (vf.TMS_Final-vi.TMS_Inicial), COALESCE((((vf.TMS_Final*lf.Ley_f_gL)-(vi.TMS_Inicial*li.Ley_i_gL))/NULLIF((vf.TMS_Final-vi.TMS_Inicial),0))/10.0,0)
    FROM volumen_inicial vi CROSS JOIN volumen_final vf CROSS JOIN ley_inicial li CROSS JOIN ley_final lf;

    -- F79-F82
    ;WITH masico_f79 AS (SELECT COALESCE(SUM(s.pls_oxido_sx_tren_a_m3_h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_pls_ep s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f79 AS (SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F79', m.Tonelaje, l.Ley_Cu FROM masico_f79 m CROSS JOIN ley_f79 l;

    ;WITH masico_f80 AS (SELECT COALESCE(SUM(s.pls_oxido_sx_tren_b_m3_h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_pls_ep s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f80 AS (SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F80', m.Tonelaje, l.Ley_Cu FROM masico_f80 m CROSS JOIN ley_f80 l;

    ;WITH masico_f81 AS (SELECT COALESCE(SUM(s.pls_oxido_sx_tren_c_m3_h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_pls_ep s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f81 AS (SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F81', m.Tonelaje, l.Ley_Cu FROM masico_f81 m CROSS JOIN ley_f81 l;

    ;WITH masico_f82 AS (SELECT COALESCE(SUM(s.pls_oxido_sx_tren_d_m3_h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_pls_ep s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f82 AS (SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F82', m.Tonelaje, l.Ley_Cu FROM masico_f82 m CROSS JOIN ley_f82 l;

    -- F83-F86
    ;WITH masico_f83 AS (SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_a_m3_h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_pls_ep s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f83 AS (SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F83', m.Tonelaje, l.Ley_Cu FROM masico_f83 m CROSS JOIN ley_f83 l;

    ;WITH masico_f84 AS (SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_b_m3_h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_pls_ep s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f84 AS (SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F84', m.Tonelaje, l.Ley_Cu FROM masico_f84 m CROSS JOIN ley_f84 l;

    ;WITH masico_f85 AS (SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_c_m3_h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_pls_ep s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f85 AS (SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F85', m.Tonelaje, l.Ley_Cu FROM masico_f85 m CROSS JOIN ley_f85 l;

    ;WITH masico_f86 AS (SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_d_m3_h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_pls_ep s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f86 AS (SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.conc_cu c WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F86', m.Tonelaje, l.Ley_Cu FROM masico_f86 m CROSS JOIN ley_f86 l;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F87',0,0);

    -- F88-F91
    ;WITH b AS (SELECT COALESCE(t.acido_sx_tren_a_m3h,0)*1.84 AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F88', COALESCE(SUM(ton),0), 0 FROM b;
    ;WITH b AS (SELECT COALESCE(t.acido_sx_tren_b_m3h,0)*1.84 AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F89', COALESCE(SUM(ton),0), 0 FROM b;
    ;WITH b AS (SELECT COALESCE(t.acido_sx_tren_c_m3h,0)*1.84 AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F90', COALESCE(SUM(ton),0), 0 FROM b;
    ;WITH b AS (SELECT COALESCE(t.acido_sx_tren_d_m3h,0)*1.84 AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F91', COALESCE(SUM(ton),0), 0 FROM b;

    -- F92-F95
    ;WITH b AS (SELECT COALESCE(t.agua_sx_tren_a_m3h,0) AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F92', COALESCE(SUM(ton),0), 0 FROM b;
    ;WITH b AS (SELECT COALESCE(t.agua_sx_tren_b_m3h,0) AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F93', COALESCE(SUM(ton),0), 0 FROM b;
    ;WITH b AS (SELECT COALESCE(t.agua_sx_tren_c_m3h,0) AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F94', COALESCE(SUM(ton),0), 0 FROM b;
    ;WITH b AS (SELECT COALESCE(t.agua_sx_tren_d_m3h,0) AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F95', COALESCE(SUM(ton),0), 0 FROM b;

    -- F96-F99
    ;WITH masico_f96 AS (SELECT COALESCE(SUM(s.ep_tren_a_m3h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_ep_flujos_niveles s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f96 AS (SELECT COALESCE(AVG((COALESCE(p.cu_electrolito_pobre_c1_g_l,0)+COALESCE(p.cu_electrolito_pobre_c2_g_l,0)+COALESCE(p.cu_electrolito_pobre_c3_g_l,0))/3.0),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.sx_pls_ep p WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F96', m.Tonelaje, l.Ley_Cu FROM masico_f96 m CROSS JOIN ley_f96 l;

    ;WITH masico_f97 AS (SELECT COALESCE(SUM(s.ep_tren_b_m3h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_ep_flujos_niveles s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f97 AS (SELECT COALESCE(AVG((COALESCE(p.cu_electrolito_pobre_c1_g_l,0)+COALESCE(p.cu_electrolito_pobre_c2_g_l,0)+COALESCE(p.cu_electrolito_pobre_c3_g_l,0))/3.0),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.sx_pls_ep p WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F97', m.Tonelaje, l.Ley_Cu FROM masico_f97 m CROSS JOIN ley_f97 l;

    ;WITH masico_f98 AS (SELECT COALESCE(SUM(s.ep_tren_c_m3h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_ep_flujos_niveles s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f98 AS (SELECT COALESCE(AVG((COALESCE(p.cu_electrolito_pobre_c1_g_l,0)+COALESCE(p.cu_electrolito_pobre_c2_g_l,0)+COALESCE(p.cu_electrolito_pobre_c3_g_l,0))/3.0),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.sx_pls_ep p WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F98', m.Tonelaje, l.Ley_Cu FROM masico_f98 m CROSS JOIN ley_f98 l;

    ;WITH masico_f99 AS (SELECT COALESCE(SUM(s.ep_tren_d_m3h),0)*24.0 AS Tonelaje FROM inventar_SpcHidr.sx_ep_flujos_niveles s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin),
    ley_f99 AS (SELECT COALESCE(AVG((COALESCE(p.cu_electrolito_pobre_c1_g_l,0)+COALESCE(p.cu_electrolito_pobre_c2_g_l,0)+COALESCE(p.cu_electrolito_pobre_c3_g_l,0))/3.0),0)/10.0 AS Ley_Cu FROM inventar_SpcHidr.sx_pls_ep p WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F99', m.Tonelaje, l.Ley_Cu FROM masico_f99 m CROSS JOIN ley_f99 l;

    -- F100
    ;WITH masico_f100 AS (
        SELECT COALESCE(SUM(COALESCE(t.ercc_c1_m3h,0)+COALESCE(t.ercc_c2_m3h,0)+COALESCE(t.ercc_c3_m3h,0)),0) AS Tonelaje
        FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin)
    ),
    ley_f100 AS (
        SELECT NULLIF(SUM(CASE WHEN NULLIF(n.er_ecc1_gl,0) IS NOT NULL AND NULLIF(e.ercc_c1_m3h,0) IS NOT NULL THEN e.ercc_c1_m3h*n.er_ecc1_gl ELSE 0 END+CASE WHEN NULLIF(n.er_ecc2_gl,0) IS NOT NULL AND NULLIF(e.ercc_c2_m3h,0) IS NOT NULL THEN e.ercc_c2_m3h*n.er_ecc2_gl ELSE 0 END+CASE WHEN NULLIF(n.er_ecc3_gl,0) IS NOT NULL AND NULLIF(e.ercc_c3_m3h,0) IS NOT NULL THEN e.ercc_c3_m3h*n.er_ecc3_gl ELSE 0 END)/NULLIF(SUM(CASE WHEN NULLIF(n.er_ecc1_gl,0) IS NOT NULL AND NULLIF(e.ercc_c1_m3h,0) IS NOT NULL THEN e.ercc_c1_m3h ELSE 0 END+CASE WHEN NULLIF(n.er_ecc2_gl,0) IS NOT NULL AND NULLIF(e.ercc_c2_m3h,0) IS NOT NULL THEN e.ercc_c2_m3h ELSE 0 END+CASE WHEN NULLIF(n.er_ecc3_gl,0) IS NOT NULL AND NULLIF(e.ercc_c3_m3h,0) IS NOT NULL THEN e.ercc_c3_m3h ELSE 0 END),0),0)/10.0 AS Ley_Cu
        FROM inventar_SpcHidr.sx_ep_flujos_niveles n INNER JOIN inventar_SpcHidr.tags_sx_ew e ON CAST(n.fecha_registro AS date)=CAST(e.fecha_inicio AS date)
        WHERE CAST(n.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin AND e.fecha_inicio>=@fecha_inicio AND e.fecha_inicio<DATEADD(DAY,1,@fecha_fin)
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F100', NULLIF(m.Tonelaje,0), l.Ley_Cu FROM masico_f100 m CROSS JOIN ley_f100 l WHERE NULLIF(m.Tonelaje,0) IS NOT NULL;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F101',0,0),('F102',0,0),('F103',0,0),('F104',0,0),('F106',0,0);

    -- F108
    ;WITH ini AS (SELECT TOP 1 COALESCE(i.cobre_colgado_ton,0) AS v FROM inventar_SpcHidr.inventario_cobre_colgado i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) ASC),
    fin AS (SELECT TOP 1 COALESCE(i.cobre_colgado_ton,0) AS v FROM inventar_SpcHidr.inventario_cobre_colgado i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) DESC)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT 'F108', ini.v, 100.0, fin.v, 100.0, fin.v-ini.v, 100.0 FROM ini CROSS JOIN fin;

    -- F109
    ;WITH base_f109 AS (SELECT COALESCE(p.real_produccion_ton,0) AS ton FROM inventar_SpcHidr.produccion_catodica p WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin)
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F109', COALESCE(SUM(ton),0), 100.0 FROM base_f109;

    -- F107
    ;WITH f108 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F108'), f109 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F109')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F107', COALESCE(f108.Tonelaje,0)+COALESCE(f109.Tonelaje,0), 100.0 FROM f108 CROSS JOIN f109;

    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F110',0,0),('F111',0,0),('F112',0,0),('F113',0,0),('F114',0,0);

    -- F115
    ;WITH f109 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F109'),
          f110 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F110'),
          f111 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F111'),
          f112 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F112'),
          f113 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F113'),
          f114 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F114')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F115', COALESCE(f109.Tonelaje,0)-COALESCE(f110.Tonelaje,0)-COALESCE(f111.Tonelaje,0)-COALESCE(f112.Tonelaje,0)-COALESCE(f113.Tonelaje,0)-COALESCE(f114.Tonelaje,0), 100.0
    FROM f109 CROSS JOIN f110 CROSS JOIN f111 CROSS JOIN f112 CROSS JOIN f113 CROSS JOIN f114;

    -- F116
    ;WITH f100 AS (SELECT COALESCE(MAX(Tonelaje),0) AS Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F100'),
    ley_f116 AS (
        SELECT SUM(CASE WHEN NULLIF(t.ep_ecc1_gl,0) IS NOT NULL AND NULLIF(s.ercc_c1_m3h,0) IS NOT NULL THEN s.ercc_c1_m3h*t.ep_ecc1_gl ELSE 0 END+CASE WHEN NULLIF(t.ep_ecc2_gl,0) IS NOT NULL AND NULLIF(s.ercc_c2_m3h,0) IS NOT NULL THEN s.ercc_c2_m3h*t.ep_ecc2_gl ELSE 0 END+CASE WHEN NULLIF(t.ep_ecc3_gl,0) IS NOT NULL AND NULLIF(s.ercc_c3_m3h,0) IS NOT NULL THEN s.ercc_c3_m3h*t.ep_ecc3_gl ELSE 0 END)/NULLIF(SUM(CASE WHEN NULLIF(t.ep_ecc1_gl,0) IS NOT NULL AND NULLIF(s.ercc_c1_m3h,0) IS NOT NULL THEN s.ercc_c1_m3h ELSE 0 END+CASE WHEN NULLIF(t.ep_ecc2_gl,0) IS NOT NULL AND NULLIF(s.ercc_c2_m3h,0) IS NOT NULL THEN s.ercc_c2_m3h ELSE 0 END+CASE WHEN NULLIF(t.ep_ecc3_gl,0) IS NOT NULL AND NULLIF(s.ercc_c3_m3h,0) IS NOT NULL THEN s.ercc_c3_m3h ELSE 0 END),0)/10.0 AS Ley_Cu
        FROM inventar_SpcHidr.sx_ep_flujos_niveles t INNER JOIN inventar_SpcHidr.tags_sx_ew s ON CAST(t.fecha_registro AS datetime)=CAST(s.fecha_inicio AS datetime)
        WHERE CAST(t.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin AND s.fecha_inicio>=@fecha_inicio AND s.fecha_inicio<DATEADD(DAY,1,@fecha_fin)
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F116', NULLIF(COALESCE(f100.Tonelaje,0),0), NULLIF(l.Ley_Cu,0) FROM f100 CROSS JOIN ley_f116 l WHERE NULLIF(COALESCE(f100.Tonelaje,0),0) IS NOT NULL;

    -- F105
    ;WITH volumen_inicial AS (SELECT TOP 1 COALESCE(i.inventario_sol_ew,0)*1.0 AS TMS_Inicial FROM inventar_SpcHidr.inv_solucion_ew i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) ASC),
    volumen_final AS (SELECT TOP 1 COALESCE(i.inventario_sol_ew,0)*1.0 AS TMS_Final FROM inventar_SpcHidr.inv_solucion_ew i WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin ORDER BY CAST(i.fecha_registro AS date) DESC),
    f100 AS (SELECT COALESCE(MAX(Tonelaje),0) AS Tonelaje, COALESCE(MAX(Ley_Cu),0) AS Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F100'),
    f116 AS (SELECT COALESCE(MAX(Tonelaje),0) AS Tonelaje, COALESCE(MAX(Ley_Cu),0) AS Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F116'),
    ley_f105 AS (SELECT CASE WHEN COALESCE(f100.Tonelaje,0)+COALESCE(f116.Tonelaje,0)=0 THEN 0 ELSE (COALESCE(f100.Tonelaje,0)*COALESCE(f100.Ley_Cu,0)+COALESCE(f116.Tonelaje,0)*COALESCE(f116.Ley_Cu,0))/NULLIF(COALESCE(f100.Tonelaje,0)+COALESCE(f116.Tonelaje,0),0) END AS Ley_Cu FROM f100 CROSS JOIN f116)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT 'F105', vi.TMS_Inicial, l.Ley_Cu, vf.TMS_Final, l.Ley_Cu, vf.TMS_Final-vi.TMS_Inicial, l.Ley_Cu
    FROM volumen_inicial vi CROSS JOIN volumen_final vf CROSS JOIN ley_f105 l;

    -- F117
    ;WITH f96 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F96'),
          f97 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F97'),
          f98 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F98'),
          f99 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F99'),
          f102 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F102'),
          f103 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F103'),
    ley_f117 AS (
        SELECT COALESCE(AVG((NULLIF(s.conc_er_ta_gl,0)+NULLIF(s.conc_er_tb_gl,0)+NULLIF(s.conc_er_tc_gl,0)+NULLIF(s.conc_er_td_gl,0))/NULLIF((CASE WHEN NULLIF(s.conc_er_ta_gl,0) IS NOT NULL THEN 1 ELSE 0 END+CASE WHEN NULLIF(s.conc_er_tb_gl,0) IS NOT NULL THEN 1 ELSE 0 END+CASE WHEN NULLIF(s.conc_er_tc_gl,0) IS NOT NULL THEN 1 ELSE 0 END+CASE WHEN NULLIF(s.conc_er_td_gl,0) IS NOT NULL THEN 1 ELSE 0 END),0)),0)/10.0 AS Ley_Cu
        FROM inventar_SpcHidr.sx_ep_flujos_niveles s WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F117', COALESCE(f96.Tonelaje,0)+COALESCE(f97.Tonelaje,0)+COALESCE(f98.Tonelaje,0)+COALESCE(f99.Tonelaje,0)+COALESCE(f102.Tonelaje,0)+COALESCE(f103.Tonelaje,0), COALESCE(l.Ley_Cu,0)
    FROM f96 CROSS JOIN f97 CROSS JOIN f98 CROSS JOIN f99 CROSS JOIN f102 CROSS JOIN f103 CROSS JOIN ley_f117 l;

    -- F118
    ;WITH base_f118 AS (SELECT SUM(COALESCE(t.agua_adasa_sx_tren_a_m3h,0)+COALESCE(t.agua_adasa_sx_tren_b_m3h,0)+COALESCE(t.agua_adasa_sx_tren_c_m3h,0)+COALESCE(t.agua_adasa_sx_tren_d_m3h,0)) AS ton FROM inventar_SpcHidr.tags_sx_ew t WHERE t.fecha_inicio>=@fecha_inicio AND t.fecha_inicio<DATEADD(DAY,1,@fecha_fin))
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) SELECT 'F118', COALESCE(SUM(ton),0), 0 FROM base_f118;

    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu) VALUES ('F119',0,0,0,0,0,0);

    -- F120
    ;WITH f38 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F38'),
          f70 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F70'),
          f52 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F52')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F120', CASE WHEN (COALESCE(f38.Tonelaje,0)*1.05)+COALESCE(f70.Tonelaje,0)-COALESCE(f52.Tonelaje,0)<0 THEN 0 ELSE (COALESCE(f38.Tonelaje,0)*1.05)+COALESCE(f70.Tonelaje,0)-COALESCE(f52.Tonelaje,0) END, 0.0
    FROM f38 CROSS JOIN f70 CROSS JOIN f52;

    -------------------------------------------------------------------------
    -- 8b) FLUJOS F121..F128 desde campana_parcela_control
    -------------------------------------------------------------------------

    -- F121: Pad SULFURO - tms_cargado con fecha_ini_operacion en el período
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F121',
        COALESCE(SUM(cpc.tms_cargado), 0),
        COALESCE(SUM(cpc.tms_cargado * cpc.cut_tm_total / 100.0) / NULLIF(SUM(cpc.tms_cargado), 0), 0) * 100.0
    FROM inventar_SpcHidr.campana_parcela_control cpc
    INNER JOIN inventar_SpcHidr.parcela p  ON p.id_parcela = cpc.parcela_id
    INNER JOIN inventar_SpcHidr.[pad]  pa ON pa.id_pad    = p.id_pad
    WHERE pa.id_pad = 2
      AND cpc.fecha_ini_operacion BETWEEN @fecha_inicio AND @fecha_fin
      AND cpc.tms_cargado IS NOT NULL;

    -- F122: Pad OXIDO - tms_cargado con fecha_ini_operacion en el período
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F122',
        COALESCE(SUM(cpc.tms_cargado), 0),
        COALESCE(SUM(cpc.tms_cargado * cpc.cut_tm_total / 100.0) / NULLIF(SUM(cpc.tms_cargado), 0), 0) * 100.0
    FROM inventar_SpcHidr.campana_parcela_control cpc
    INNER JOIN inventar_SpcHidr.parcela p  ON p.id_parcela = cpc.parcela_id
    INNER JOIN inventar_SpcHidr.[pad]  pa ON pa.id_pad    = p.id_pad
    WHERE pa.id_pad = 1
      AND cpc.fecha_ini_operacion BETWEEN @fecha_inicio AND @fecha_fin
      AND cpc.tms_cargado IS NOT NULL;

    -- F123: Pad OXIDO - fino residual en pilas en reclamo
    ;WITH reclamo_oxido AS (
        SELECT cpc.campana_id, cpc.parcela_id, cpc.tms_cargado, cpc.cut_tm_total
        FROM inventar_SpcHidr.campana_parcela_control cpc
        INNER JOIN inventar_SpcHidr.parcela p  ON p.id_parcela = cpc.parcela_id
        INNER JOIN inventar_SpcHidr.[pad]  pa ON pa.id_pad    = p.id_pad
        WHERE pa.id_pad = 1
          AND cpc.fecha_ini_retiro IS NOT NULL
          AND cpc.fecha_ini_retiro <= @fecha_fin
          AND ISNULL(cpc.fecha_fin_retiro, @fecha_fin) >= @fecha_inicio
          AND cpc.tms_cargado IS NOT NULL
    ),
    recuperacion_max_ox AS (
        SELECT r.campaña_id, r.parcela_id, MAX(r.Recuperacion_parcela) AS rec_max
        FROM inventar_SpcHidr.Recuperaciones_pad r
        WHERE r.Fecha_drenaje <= @fecha_fin AND r.pad_id = 1
        GROUP BY r.campaña_id, r.parcela_id
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F123',
        COALESCE(SUM(ro.tms_cargado * ro.cut_tm_total / 100.0) - SUM(COALESCE(rm.rec_max, 0)), 0),
        COALESCE((SUM(ro.tms_cargado * ro.cut_tm_total / 100.0) - SUM(COALESCE(rm.rec_max, 0))) / NULLIF(SUM(ro.tms_cargado), 0) * 100.0, 0)
    FROM reclamo_oxido ro
    LEFT JOIN recuperacion_max_ox rm ON rm.campaña_id = ro.campana_id AND rm.parcela_id = ro.parcela_id;

    -- F124: Pad SULFURO - fino residual en pilas en reclamo
    ;WITH reclamo_sulfuro AS (
        SELECT cpc.campana_id, cpc.parcela_id, cpc.tms_cargado, cpc.cut_tm_total
        FROM inventar_SpcHidr.campana_parcela_control cpc
        INNER JOIN inventar_SpcHidr.parcela p  ON p.id_parcela = cpc.parcela_id
        INNER JOIN inventar_SpcHidr.[pad]  pa ON pa.id_pad    = p.id_pad
        WHERE pa.id_pad = 2
          AND cpc.fecha_ini_retiro IS NOT NULL
          AND cpc.fecha_ini_retiro <= @fecha_fin
          AND ISNULL(cpc.fecha_fin_retiro, @fecha_fin) >= @fecha_inicio
          AND cpc.tms_cargado IS NOT NULL
    ),
    recuperacion_max_su AS (
        SELECT r.campaña_id, r.parcela_id, MAX(r.Recuperacion_parcela) AS rec_max
        FROM inventar_SpcHidr.Recuperaciones_pad r
        WHERE r.Fecha_drenaje <= @fecha_fin AND r.pad_id = 2
        GROUP BY r.campaña_id, r.parcela_id
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F124',
        COALESCE(SUM(rs.tms_cargado * rs.cut_tm_total / 100.0) - SUM(COALESCE(rm.rec_max, 0)), 0),
        COALESCE((SUM(rs.tms_cargado * rs.cut_tm_total / 100.0) - SUM(COALESCE(rm.rec_max, 0))) / NULLIF(SUM(rs.tms_cargado), 0) * 100.0, 0)
    FROM reclamo_sulfuro rs
    LEFT JOIN recuperacion_max_su rm ON rm.campaña_id = rs.campana_id AND rm.parcela_id = rs.parcela_id;

    -- F125: F121 - F24
    ;WITH f121 AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F121'),
          f24  AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F24')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F125',
        COALESCE(f121.Tonelaje,0) - COALESCE(f24.Tonelaje,0),
        CASE WHEN (COALESCE(f121.Tonelaje,0)-COALESCE(f24.Tonelaje,0))=0 THEN 0
             ELSE (COALESCE(f121.Tonelaje,0)*COALESCE(f121.Ley_Cu,0)/100.0 - COALESCE(f24.Tonelaje,0)*COALESCE(f24.Ley_Cu,0)/100.0)
                  /NULLIF(COALESCE(f121.Tonelaje,0)-COALESCE(f24.Tonelaje,0),0)*100.0 END
    FROM f121 CROSS JOIN f24;

    -- F126: F122 - F23
    ;WITH f122 AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F122'),
          f23  AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F23')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F126',
        COALESCE(f122.Tonelaje,0) - COALESCE(f23.Tonelaje,0),
        CASE WHEN (COALESCE(f122.Tonelaje,0)-COALESCE(f23.Tonelaje,0))=0 THEN 0
             ELSE (COALESCE(f122.Tonelaje,0)*COALESCE(f122.Ley_Cu,0)/100.0 - COALESCE(f23.Tonelaje,0)*COALESCE(f23.Ley_Cu,0)/100.0)
                  /NULLIF(COALESCE(f122.Tonelaje,0)-COALESCE(f23.Tonelaje,0),0)*100.0 END
    FROM f122 CROSS JOIN f23;

    -- F127: F124 - F21 - F18
    ;WITH f124 AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F124'),
          f21  AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F21'),
          f18  AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F18')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F127',
        COALESCE(f124.Tonelaje,0) - COALESCE(f21.Tonelaje,0) - COALESCE(f18.Tonelaje,0),
        CASE WHEN (COALESCE(f124.Tonelaje,0)-COALESCE(f21.Tonelaje,0)-COALESCE(f18.Tonelaje,0))=0 THEN 0
             ELSE (COALESCE(f124.Tonelaje,0)*COALESCE(f124.Ley_Cu,0)/100.0 - COALESCE(f21.Tonelaje,0)*COALESCE(f21.Ley_Cu,0)/100.0 - COALESCE(f18.Tonelaje,0)*COALESCE(f18.Ley_Cu,0)/100.0)
                  /NULLIF(COALESCE(f124.Tonelaje,0)-COALESCE(f21.Tonelaje,0)-COALESCE(f18.Tonelaje,0),0)*100.0 END
    FROM f124 CROSS JOIN f21 CROSS JOIN f18;

    -- F128: F123 - F22 - F19
    ;WITH f123 AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F123'),
          f22  AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F22'),
          f19  AS (SELECT Tonelaje, Ley_Cu FROM #flujos_resultado WHERE codigo_flujo='F19')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F128',
        COALESCE(f123.Tonelaje,0) - COALESCE(f22.Tonelaje,0) - COALESCE(f19.Tonelaje,0),
        CASE WHEN (COALESCE(f123.Tonelaje,0)-COALESCE(f22.Tonelaje,0)-COALESCE(f19.Tonelaje,0))=0 THEN 0
             ELSE (COALESCE(f123.Tonelaje,0)*COALESCE(f123.Ley_Cu,0)/100.0 - COALESCE(f22.Tonelaje,0)*COALESCE(f22.Ley_Cu,0)/100.0 - COALESCE(f19.Tonelaje,0)*COALESCE(f19.Ley_Cu,0)/100.0)
                  /NULLIF(COALESCE(f123.Tonelaje,0)-COALESCE(f22.Tonelaje,0)-COALESCE(f19.Tonelaje,0),0)*100.0 END
    FROM f123 CROSS JOIN f22 CROSS JOIN f19;

    -------------------------------------------------------------------------
    -- 9) SALIDA FINAL — incluye F1..F128
    -------------------------------------------------------------------------
    SELECT
        codigo_flujo AS Flujo,
        TMS_Inicial,
        Ley_Cu_1,
        TMS_Final,
        Ley_Cu_2,
        Tonelaje,
        Ley_Cu,
        Tonelaje * Ley_Cu / 100.0 AS FCu
    FROM #flujos_resultado
    ORDER BY TRY_CONVERT(int, REPLACE(codigo_flujo, 'F', ''));

END;
