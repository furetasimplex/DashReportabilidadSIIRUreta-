-- Parche DEV_SIIR -> PROD_SIIR en inventar_SpcHidr_PROD
-- Schema inventar_SpcHidr NO se renombra.
-- Aplicar cada batch por separado (GO). Una transaccion por objeto.
-- Estado: aplicado 2026-08-13 contra inventar_SpcHidr_PROD.
USE inventar_SpcHidr_PROD;
GO

-- ==== inventar_SpcHidr.v_conciliacion_chancado_v2 ====
CREATE OR ALTER VIEW inventar_SpcHidr.v_conciliacion_chancado_v2
AS

WITH oficial AS
(
    SELECT
        CAST(Fecha AS date) AS Fecha,

        CASE
            WHEN Turno = 'TA' THEN 'A'
            WHEN Turno = 'TB' THEN 'B'
            ELSE Turno
        END AS Turno,

        SUM(Ton) AS Ton,

        SUM(Ton * PONDCuTG00)
            / NULLIF(SUM(Ton), 0) AS CuT,

        SUM(Ton * PONDCusG01)
            / NULLIF(SUM(Ton), 0) AS CuS,

        SUM
        (
            CASE
                WHEN UPPER(LTRIM(RTRIM(ISNULL(Origen, '')))) = 'STOCK'
                 AND UPPER(LTRIM(RTRIM(ISNULL(Fase, '')))) = 'SRR'
                    THEN 0
                ELSE Ton * PONDCUFE
            END
        )
        /
        NULLIF
        (
            SUM
            (
                CASE
                    WHEN UPPER(LTRIM(RTRIM(ISNULL(Origen, '')))) = 'STOCK'
                     AND UPPER(LTRIM(RTRIM(ISNULL(Fase, '')))) = 'SRR'
                        THEN 0
                    ELSE Ton
                END
            ),
            0
        ) AS CuFe,

        SUM(Ton * PONDC03G02)
            / NULLIF(SUM(Ton), 0) AS CO3,

        SUM
        (
            CASE
                WHEN UPPER(LTRIM(RTRIM(ISNULL(Origen, '')))) = 'STOCK'
                 AND UPPER(LTRIM(RTRIM(ISNULL(Fase, '')))) = 'SRR'
                    THEN 0
                ELSE Ton * PONDFE
            END
        )
        /
        NULLIF
        (
            SUM
            (
                CASE
                    WHEN UPPER(LTRIM(RTRIM(ISNULL(Origen, '')))) = 'STOCK'
                     AND UPPER(LTRIM(RTRIM(ISNULL(Fase, '')))) = 'SRR'
                        THEN 0
                    ELSE Ton
                END
            ),
            0
        ) AS Fe,

        SUM(Ton * POND100G07)
            / NULLIF(SUM(Ton), 0) AS Malla100,

        SUM(Ton * PONDClayBG10)
            / NULLIF(SUM(Ton), 0) AS Clay_Beta,

        CAST(NULL AS float) AS Cuarzo,
        CAST(NULL AS float) AS Caolinita

    FROM inventar_SpcHidr.resumen_mina

    GROUP BY
        CAST(Fecha AS date),
        CASE
            WHEN Turno = 'TA' THEN 'A'
            WHEN Turno = 'TB' THEN 'B'
            ELSE Turno
        END
),

imp AS
(
    SELECT
        Fecha,
        Turno,
        Ton,
        CuT,
        CuS,
        CuFe,
        CO3,
        Fe,
        Malla100,
        Clay_Beta,
        Cuarzo,
        Caolinita
    FROM PROD_SIIR.hidro.v_imp_conciliacion_chancado
),

combinado AS
(
    SELECT
        COALESCE(o.Fecha, i.Fecha) AS Fecha,
        COALESCE(o.Turno, i.Turno) AS Turno,

        CASE
            WHEN i.Fecha IS NOT NULL
             AND ISNULL(i.Ton, 0) > 0
             AND
             (
                 o.Fecha IS NULL
                 OR ISNULL(o.Ton, 0) = 0
             )
                THEN 1
            ELSE 0
        END AS Usar_IMP,

        o.Ton AS Ton_Oficial,
        o.CuT AS CuT_Oficial,
        o.CuS AS CuS_Oficial,
        o.CuFe AS CuFe_Oficial,
        o.CO3 AS CO3_Oficial,
        o.Fe AS Fe_Oficial,
        o.Malla100 AS Malla100_Oficial,
        o.Clay_Beta AS Clay_Beta_Oficial,
        o.Cuarzo AS Cuarzo_Oficial,
        o.Caolinita AS Caolinita_Oficial,

        i.Ton AS Ton_IMP,
        i.CuT AS CuT_IMP,
        i.CuS AS CuS_IMP,
        i.CuFe AS CuFe_IMP,
        i.CO3 AS CO3_IMP,
        i.Fe AS Fe_IMP,
        i.Malla100 AS Malla100_IMP,
        i.Clay_Beta AS Clay_Beta_IMP,
        i.Cuarzo AS Cuarzo_IMP,
        i.Caolinita AS Caolinita_IMP

    FROM oficial AS o

    FULL OUTER JOIN imp AS i
        ON i.Fecha = o.Fecha
       AND i.Turno = o.Turno
)

SELECT
    Fecha,
    Turno,

    CASE
        WHEN Usar_IMP = 1 THEN Ton_IMP
        ELSE Ton_Oficial
    END AS Ton,

    CASE
        WHEN Usar_IMP = 1 THEN CuT_IMP
        ELSE CuT_Oficial
    END AS CuT,

    CASE
        WHEN Usar_IMP = 1 THEN CuS_IMP
        ELSE CuS_Oficial
    END AS CuS,

    CASE
        WHEN Usar_IMP = 1 THEN CuFe_IMP
        ELSE CuFe_Oficial
    END AS CuFe,

    CASE
        WHEN Usar_IMP = 1 THEN CO3_IMP
        ELSE CO3_Oficial
    END AS CO3,

    CASE
        WHEN Usar_IMP = 1 THEN Fe_IMP
        ELSE Fe_Oficial
    END AS Fe,

    CASE
        WHEN Usar_IMP = 1 THEN Malla100_IMP
        ELSE Malla100_Oficial
    END AS Malla100,

    CASE
        WHEN Usar_IMP = 1 THEN Clay_Beta_IMP
        ELSE Clay_Beta_Oficial
    END AS Clay_Beta,

    CASE
        WHEN Usar_IMP = 1 THEN Cuarzo_IMP
        ELSE Cuarzo_Oficial
    END AS Cuarzo,

    CASE
        WHEN Usar_IMP = 1 THEN Caolinita_IMP
        ELSE Caolinita_Oficial
    END AS Caolinita,

    CAST
    (
        CASE
            WHEN Usar_IMP = 1
                THEN 'IMP'

            WHEN Ton_Oficial IS NOT NULL
                THEN 'MINA'

            ELSE 'SIN_DATO'
        END
        AS varchar(20)
    ) AS Fuente_Dato

FROM combinado;
GO

-- ==== dbo.v_imp_conciliacion_chancado ====
CREATE OR ALTER VIEW dbo.v_imp_conciliacion_chancado
AS
SELECT id, batch_id, imported_at, date, datetime, origen, acf, ag, sag_tph, alt, [as], au, clay, bclaymusc, bm_tph, bwi, calidad, ci, circuit_tph, co3, conc_ag, conc_as, conc_au, conc_cu, conc_mo, conc_sb, csrcc, csrcpy, csrcuins, csrcuoxi, csrcv, cufe, cus, cut, densidad, fe, hum_estim, lito, m100, 
             mg, minty, minty_corto, mo, musc, py, quar, rec_ag, rec_au, rec_cu, rec_denver_nir_min20_recmass10, rec_denver_nir_min20_recmass11, rec_denver_nir_min20_recmass23, rec_denver_nir_min20_recmass8, rec_denver_nir_min20_recmass9, rec_mo, rec_mx_cu, s2, sb, solub, spi, 
             ugrec, zn, humedad_categ_final, ugt19_v3, yield_stress, magnesio, bwi_nir, ci_nir, spi_nir, nag, np, ph, phnag, ys_cp47_testing, ys_cp49_testing, ys_cp51_testing, ys_cp53_testing, ys_cp55_testing, categoria, rec_denver_nir_min20_recmass12, rec_denver_nir_min20_recmass13, 
             rec_denver_nir_min20_recmass14, rec_denver_nir_min20_recmass15, rec_denver_nir_min20_recmass16, rec_denver_nir_min20_recmass17, rec_denver_nir_min20_recmass18, rec_denver_nir_min20_recmass19, rec_denver_nir_min20_recmass20, rec_denver_nir_min20_recmass21, 
             rec_denver_nir_min20_recmass22, rec_denver_nir_min20_recmass10_fix, banco, pol_index, circuit_tph_cap4583, clusters_ve, minty_corto_calc, csrcc_equ, rec_denver_nir_min20_recmass10_ug, ys_cp51_oficial, ys_cp53_oficial, ys_cp55_oficial, ys_cp57_testing, ys_cp60_testing, 
             ys_cp57_oficial, ys_cp60_oficial, m02, m04, rec_min05, m07, m09, recmass10_fix_tph_4167, recmass10_fix_tph_4250, recmass10_fix_tph_4350, m03, m06, m12, m15, dumpid, tonnage, [from], [to], shovel, loadx, loady, loadz, dumpx, dumpy, dumpz, 
             rec_denver_nir_min20_recmass10_ug_gte_65, recup, pm10_campamento, recup_estimada, ton_sag
FROM   PROD_SIIR.hidro.imp_csv;
GO

-- ==== inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test ====
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
   "cut" en PROD_SIIR.hidro.imp_csv con el mismo filtro que ya usa
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
CREATE   PROCEDURE [inventar_SpcHidr].[sp_mantiene_datos_conciliados_emision_test]
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
    EXEC [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_test]
         @FechaInicio   = @FechaInicioProceso,
         @FechaFin      = @FechaFin,
         @DiasReproceso = @DiasReproceso;
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
    FROM [PROD_SIIR].[hidro].[imp_csv] ic
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
    FROM [PROD_SIIR].[hidro].[imp_csv] ic
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
            aj.Chancado_TMS_Reporte AS Chancado_TMS_Real,
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
                WHEN aj.Chancado_TMS_Reporte IS NULL THEN NULL
                ELSE
                    (
                        g.CuT_Real_Dia
                        * (
                            CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1 THEN aj.Apilado_TMS_Bruto_Ajustado ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END
                            - aj.Sal_TMH_Dia
                            + aj.Delta_Inventario_Chancado_TMS
                          )
                        - (lms.Ley_CuT_Mina_Stock * aj.Chancado_TMS_Reporte)
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
GO

-- ==== inventar_SpcHidr.sp_mantiene_datos_conciliados_of ====
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
    FROM [PROD_SIIR].[hidro].[imp_csv] ic
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
GO

-- ==== inventar_SpcHidr.sp_reporte_turno_test ====
CREATE OR ALTER PROCEDURE inventar_SpcHidr.sp_reporte_turno_test
    @fecha_inicio date,
    @fecha_fin    date
AS
BEGIN
    SET NOCOUNT ON;

    /* ============================================================
       LIMPIEZA TEMPORALES
       ============================================================ */

    DROP TABLE IF EXISTS #fechas;
    DROP TABLE IF EXISTS #hum;
    DROP TABLE IF EXISTS #hum_rep;
    DROP TABLE IF EXISTS #hum_torre_dia;
    DROP TABLE IF EXISTS #hum_torre_dia_final;
    DROP TABLE IF EXISTS #candidatos;
    DROP TABLE IF EXISTS #humedad_resuelta;
    DROP TABLE IF EXISTS #fes_candidatos_dia;
    DROP TABLE IF EXISTS #fes_dia_resuelta;

 /* ============================================================
   BLOQUE 1: TMH BASE DESDE APILADO
   Depuración anti-spike por correa/turno
   ============================================================ */

DECLARE @umbral_tmh_spike_turno decimal(18,6) = 150000.0;

WITH tmh_raw AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        CAST(ISNULL(TMH_CV008_A, 0) AS decimal(18,6)) AS TMH_CV008_A_Raw,
        CAST(ISNULL(TMH_CV008_B, 0) AS decimal(18,6)) AS TMH_CV008_B_Raw,
        CAST(ISNULL(TMH_CV108_A, 0) AS decimal(18,6)) AS TMH_CV108_A_Raw,
        CAST(ISNULL(TMH_CV108_B, 0) AS decimal(18,6)) AS TMH_CV108_B_Raw
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2
    WHERE Fecha >= @fecha_inicio
      AND Fecha <  @fecha_fin
),
tmh_limpia AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        CASE
            WHEN ABS(TMH_CV008_A_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV008_A_Raw
        END AS TMH_CV008_A,

        CASE
            WHEN ABS(TMH_CV008_B_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV008_B_Raw
        END AS TMH_CV008_B,

        CASE
            WHEN ABS(TMH_CV108_A_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV108_A_Raw
        END AS TMH_CV108_A,

        CASE
            WHEN ABS(TMH_CV108_B_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV108_B_Raw
        END AS TMH_CV108_B
    FROM tmh_raw
)
SELECT
    Fecha,
    Flag_Apilado_Valido,

    TMH_CV008_A,
    TMH_CV008_B,
    TMH_CV108_A,
    TMH_CV108_B,

    TMH_CV008_A + TMH_CV108_A AS TMH_Apilado_Total_A,
    TMH_CV008_B + TMH_CV108_B AS TMH_Apilado_Total_B,
    TMH_CV008_A + TMH_CV108_A + TMH_CV008_B + TMH_CV108_B AS TMH_Apilado_Total_Dia

INTO #fechas
FROM tmh_limpia;

/* ============================================================
   BLOQUE 2: HUMEDAD LABORATORIO
   Optimizado con ventana histórica razonable
   ============================================================ */

DECLARE @fecha_inicio_humedad date = DATEADD(DAY, -90, @fecha_inicio);

SELECT
    CAST(Fecha AS date) AS Fecha,
    Torre,
    Turno,
    AVG(CAST(Humedad_Prom_Pct AS float)) AS Humedad_Prom_Pct
INTO #hum
FROM inventar_SpcHidr.Informe_TM_lab
WHERE Humedad_Prom_Pct IS NOT NULL
  AND Fecha >= @fecha_inicio_humedad
  AND Fecha <  @fecha_fin
GROUP BY
    CAST(Fecha AS date),
    Torre,
    Turno;

CREATE CLUSTERED INDEX IX_hum
ON #hum (Fecha, Torre, Turno);

/* ============================================================
   BLOQUE 3: HUMEDAD + REPRESENTATIVIDAD FÍSICA
   Optimizado: usa resultado materializado
   ============================================================ */

SELECT
    h.Fecha,
    h.Torre,
    h.Turno,
    h.Humedad_Prom_Pct,
    CASE
        WHEN h.Torre = 'T1' AND h.Turno = 'A' THEN r.TM1_TurnoA_Fisico
        WHEN h.Torre = 'T1' AND h.Turno = 'B' THEN r.TM1_TurnoB_Fisico
        WHEN h.Torre = 'T2' AND h.Turno = 'A' THEN r.TM2_TurnoA_Fisico
        WHEN h.Torre = 'T2' AND h.Turno = 'B' THEN r.TM2_TurnoB_Fisico
    END AS Representatividad_Fisica
INTO #hum_rep
FROM #hum h
LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado r
    ON r.Dia = h.Fecha;

CREATE CLUSTERED INDEX IX_hum_rep
ON #hum_rep (Fecha, Torre, Turno);

  /* ============================================================
   BLOQUE 4: HUMEDADES REPRESENTATIVAS POR FECHA + TURNO

   Corrección:
   - No se reduce A/B a una sola humedad diaria.
   - Se conserva el orden cronológico A -> B.
   - Cada TM prioriza su humedad propia.
   - Cuando no existe humedad propia más reciente, utiliza
     la humedad representativa vigente de la otra torre.
   ============================================================ */

SELECT
    Fecha,
    Torre,
    Turno AS Turno_Humedad,
    Humedad_Prom_Pct AS Humedad_Torre_Dia,
    Representatividad_Fisica,

    DATEADD
    (
        HOUR,
        CASE
            WHEN Turno = 'A' THEN 8
            ELSE 20
        END,
        CAST(Fecha AS datetime2(0))
    ) AS FechaTurno_Origen

INTO #candidatos

FROM #hum_rep

WHERE Humedad_Prom_Pct IS NOT NULL
  AND Representatividad_Fisica >= 0.75;


CREATE CLUSTERED INDEX IX_candidatos
ON #candidatos
(
    FechaTurno_Origen DESC,
    Torre
);


/* ============================================================
   BLOQUE 5: RESOLUCIÓN CRONOLÓGICA POR FECHA + TURNO
   ============================================================ */

;WITH periodos AS
(
    SELECT
        f.Fecha,
        t.Turno_Objetivo,

        DATEADD
        (
            HOUR,
            CASE
                WHEN t.Turno_Objetivo = 'A' THEN 8
                ELSE 20
            END,
            CAST(f.Fecha AS datetime2(0))
        ) AS FechaTurno_Objetivo

    FROM #fechas AS f

    CROSS JOIN
    (
        VALUES
            ('A'),
            ('B')
    ) AS t(Turno_Objetivo)
),

resuelta_turno AS
(
    SELECT
        p.Fecha,
        p.Turno_Objetivo,

        /* ====================================================
           TM1
           ==================================================== */

        tm1.Humedad_Torre_Dia
            AS Humedad_TM1,

        tm1.Fecha
            AS Fecha_Origen_TM1,

        tm1.Torre
            AS Torre_Origen_TM1,

        tm1.Turno_Humedad
            AS Turno_Origen_TM1,

        tm1.Fuente_Humedad
            AS Fuente_Humedad_TM1,

        /* ====================================================
           TM2
           ==================================================== */

        tm2.Humedad_Torre_Dia
            AS Humedad_TM2,

        tm2.Fecha
            AS Fecha_Origen_TM2,

        tm2.Torre
            AS Torre_Origen_TM2,

        tm2.Turno_Humedad
            AS Turno_Origen_TM2,

        tm2.Fuente_Humedad
            AS Fuente_Humedad_TM2

    FROM periodos AS p

    /* --------------------------------------------------------
       Resolución TM1
       -------------------------------------------------------- */

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno_Humedad,
            c.Humedad_Torre_Dia,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno_Humedad,
                h.Humedad_Torre_Dia,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T1'
                            THEN 'PROPIA_TM1'
                        ELSE 'COMPARTIDA_DESDE_TM2'
                    END
                    AS varchar(23)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T1' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM #candidatos AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(10)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'HUMEDAD_INICIAL_PERIODO'
                    AS varchar(23)
                ),

                3

            FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s

            WHERE s.tm = 'TM1'
              AND CAST(s.fecha_origen AS datetime2(0))
                    <= p.FechaTurno_Objetivo
        ) AS c

        ORDER BY
            c.FechaTurno_Origen DESC,
            c.Prioridad ASC

    ) AS tm1

    /* --------------------------------------------------------
       Resolución TM2
       -------------------------------------------------------- */

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno_Humedad,
            c.Humedad_Torre_Dia,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno_Humedad,
                h.Humedad_Torre_Dia,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T2'
                            THEN 'PROPIA_TM2'
                        ELSE 'COMPARTIDA_DESDE_TM1'
                    END
                    AS varchar(23)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T2' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM #candidatos AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(10)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'HUMEDAD_INICIAL_PERIODO'
                    AS varchar(23)
                ),

                3

            FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s

            WHERE s.tm = 'TM2'
              AND CAST(s.fecha_origen AS datetime2(0))
                    <= p.FechaTurno_Objetivo
        ) AS c

        ORDER BY
            c.FechaTurno_Origen DESC,
            c.Prioridad ASC

    ) AS tm2
),

/* ============================================================
   BLOQUE 6: PIVOT A/B Y HUMEDAD RESUELTA POR FECHA

   Las columnas Humedad_TM1 y Humedad_TM2 se mantienen para
   compatibilidad y representan el valor vigente al cierre del día.
   ============================================================ */

humedad_resuelta_cte AS
(
    SELECT
        f.*,

        /* Humedades efectivas por turno */

        a.Humedad_TM1 AS Humedad_TM1_A,
        b.Humedad_TM1 AS Humedad_TM1_B,

        a.Humedad_TM2 AS Humedad_TM2_A,
        b.Humedad_TM2 AS Humedad_TM2_B,

        /* Humedad vigente al cierre diario */

        COALESCE
        (
            b.Humedad_TM1,
            a.Humedad_TM1
        ) AS Humedad_TM1,

        COALESCE
        (
            b.Humedad_TM2,
            a.Humedad_TM2
        ) AS Humedad_TM2,

        /* Trazabilidad TM1 */

        COALESCE
        (
            b.Fecha_Origen_TM1,
            a.Fecha_Origen_TM1
        ) AS Fecha_Humedad_TM1,

        COALESCE
        (
            b.Torre_Origen_TM1,
            a.Torre_Origen_TM1
        ) AS Torre_Humedad_TM1,

        COALESCE
        (
            b.Turno_Origen_TM1,
            a.Turno_Origen_TM1
        ) AS Turno_Humedad_TM1,

        COALESCE
        (
            b.Fuente_Humedad_TM1,
            a.Fuente_Humedad_TM1
        ) AS Fuente_Humedad_TM1,

        /* Trazabilidad TM2 */

        COALESCE
        (
            b.Fecha_Origen_TM2,
            a.Fecha_Origen_TM2
        ) AS Fecha_Humedad_TM2,

        COALESCE
        (
            b.Torre_Origen_TM2,
            a.Torre_Origen_TM2
        ) AS Torre_Humedad_TM2,

        COALESCE
        (
            b.Turno_Origen_TM2,
            a.Turno_Origen_TM2
        ) AS Turno_Humedad_TM2,

        COALESCE
        (
            b.Fuente_Humedad_TM2,
            a.Fuente_Humedad_TM2
        ) AS Fuente_Humedad_TM2

    FROM #fechas AS f

    LEFT JOIN resuelta_turno AS a
        ON a.Fecha = f.Fecha
       AND a.Turno_Objetivo = 'A'

    LEFT JOIN resuelta_turno AS b
        ON b.Fecha = f.Fecha
       AND b.Turno_Objetivo = 'B'
)

SELECT *
INTO #humedad_resuelta
FROM humedad_resuelta_cte;


CREATE CLUSTERED INDEX IX_humedad_resuelta
ON #humedad_resuelta (Fecha);
    /* ============================================================
   BLOQUE 7: FACTOR DE AJUSTE CAMIONES + CÁLCULO TMS CON SAL/SRR
   ============================================================ */

DROP TABLE IF EXISTS #base_tms;
DROP TABLE IF EXISTS #tms_con_sal;

SELECT
    h.*,
    COALESCE(fac.factor_ajuste, 1.0) AS Factor_Ajuste_Camiones_Usado,

    h.TMH_Apilado_Total_A   * COALESCE(fac.factor_ajuste, 1.0) AS TMH_Apilado_Total_A_Factor,
    h.TMH_Apilado_Total_B   * COALESCE(fac.factor_ajuste, 1.0) AS TMH_Apilado_Total_B_Factor,
    h.TMH_Apilado_Total_Dia * COALESCE(fac.factor_ajuste, 1.0) AS TMH_Apilado_Total_Dia_Factor

INTO #base_tms
FROM #humedad_resuelta h
OUTER APPLY (
    SELECT TOP (1)
        f.factor_ajuste
    FROM inventar_SpcHidr.factor_ajuste_camiones f
    WHERE f.activo = 1
      AND h.Fecha >= f.fecha_inicio
      AND (f.fecha_fin IS NULL OR h.Fecha <= f.fecha_fin)
    ORDER BY
        f.fecha_inicio DESC,
        f.id_factor DESC
) fac;

CREATE CLUSTERED INDEX IX_base_tms
ON #base_tms (Fecha);

SELECT
    x.*,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
        THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A + x.TMS_TM2_Con_Sal_SRR_A
    END AS TMS_Total_Con_Sal_SRR_A,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
        THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_B + x.TMS_TM2_Con_Sal_SRR_B
    END AS TMS_Total_Con_Sal_SRR_B,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
        THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A
           + x.TMS_TM1_Con_Sal_SRR_B
           + x.TMS_TM2_Con_Sal_SRR_A
           + x.TMS_TM2_Con_Sal_SRR_B
    END AS TMS_Total_Con_Sal_SRR_Dia

INTO #tms_con_sal
FROM (
    SELECT
        b.*,

CASE
    WHEN b.TMH_CV008_A = 0 THEN 0
    WHEN b.Humedad_TM1_A IS NULL THEN NULL
    ELSE
        b.TMH_CV008_A
        * (1 - b.Humedad_TM1_A / 100.0)
END AS TMS_TM1_Con_Sal_SRR_A,

CASE
    WHEN b.TMH_CV008_B = 0 THEN 0
    WHEN b.Humedad_TM1_B IS NULL THEN NULL
    ELSE
        b.TMH_CV008_B
        * (1 - b.Humedad_TM1_B / 100.0)
END AS TMS_TM1_Con_Sal_SRR_B,

CASE
    WHEN b.TMH_CV108_A = 0 THEN 0
    WHEN b.Humedad_TM2_A IS NULL THEN NULL
    ELSE
        b.TMH_CV108_A
        * (1 - b.Humedad_TM2_A / 100.0)
END AS TMS_TM2_Con_Sal_SRR_A,

CASE
    WHEN b.TMH_CV108_B = 0 THEN 0
    WHEN b.Humedad_TM2_B IS NULL THEN NULL
    ELSE
        b.TMH_CV108_B
        * (1 - b.Humedad_TM2_B / 100.0)
END AS TMS_TM2_Con_Sal_SRR_B,

     CASE
    WHEN b.TMH_Apilado_Total_Dia = 0
        THEN 0

    WHEN b.TMH_CV008_A > 0
     AND b.Humedad_TM1_A IS NULL
        THEN NULL

    WHEN b.TMH_CV008_B > 0
     AND b.Humedad_TM1_B IS NULL
        THEN NULL

    WHEN b.TMH_CV108_A > 0
     AND b.Humedad_TM2_A IS NULL
        THEN NULL

    WHEN b.TMH_CV108_B > 0
     AND b.Humedad_TM2_B IS NULL
        THEN NULL

    ELSE
        (
              b.TMH_CV008_A * b.Humedad_TM1_A
            + b.TMH_CV008_B * b.Humedad_TM1_B
            + b.TMH_CV108_A * b.Humedad_TM2_A
            + b.TMH_CV108_B * b.Humedad_TM2_B
        )
        /
        NULLIF
        (
            b.TMH_Apilado_Total_Dia,
            0
        )
END AS Humedad_Equivalente_Dia

    FROM #base_tms AS b
) AS x;

CREATE CLUSTERED INDEX IX_tms_con_sal
ON #tms_con_sal (Fecha);
/* ============================================================
   BLOQUE 8: SAL AJUSTADA + DESCUENTO DE SAL
   ============================================================ */

DROP TABLE IF EXISTS #sal_ajustada;
DROP TABLE IF EXISTS #tms_sin_sal;

SELECT
    v.Fecha,
    v.Sal_Pesometros_TA,
    v.Sal_Pesometros_TB,
    v.Sal_Pesometros_Dia,
    v.Sal_Topografia_Dia,
    v.Flag_Sal_Basica_Valida,
    v.Flag_Sal_Ajuste_Valido,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia
               * ISNULL(v.Sal_Pesometros_TA, 0)
               / NULLIF(v.Sal_Pesometros_Dia, 0)

        ELSE ISNULL(v.Sal_Ajustada_TA, 0)
    END AS Sal_Ajustada_TA,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia
               * ISNULL(v.Sal_Pesometros_TB, 0)
               / NULLIF(v.Sal_Pesometros_Dia, 0)

        ELSE ISNULL(v.Sal_Ajustada_TB, 0)
    END AS Sal_Ajustada_TB,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia

        ELSE ISNULL(v.Sal_Ajustada_Dia, 0)
    END AS Sal_Ajustada_Dia

INTO #sal_ajustada
FROM inventar_SpcHidr.v_sal_ajustada v
WHERE v.Fecha >= @fecha_inicio
  AND v.Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_sal_ajustada
ON #sal_ajustada (Fecha);


SELECT
    t.*,

    s.Sal_Pesometros_TA,
    s.Sal_Pesometros_TB,
    s.Sal_Pesometros_Dia,
    s.Sal_Topografia_Dia,

    s.Flag_Sal_Basica_Valida,
    s.Flag_Sal_Ajuste_Valido,

    s.Sal_Ajustada_TA,
    s.Sal_Ajustada_TB,
    s.Sal_Ajustada_Dia,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_A = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TA, 0)
             * t.TMS_TM1_Con_Sal_SRR_A
             / NULLIF(t.TMS_Total_Con_Sal_SRR_A, 0)
    END AS Sal_Asignada_TM1_A,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_A = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TA, 0)
             * t.TMS_TM2_Con_Sal_SRR_A
             / NULLIF(t.TMS_Total_Con_Sal_SRR_A, 0)
    END AS Sal_Asignada_TM2_A,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_B = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TB, 0)
             * t.TMS_TM1_Con_Sal_SRR_B
             / NULLIF(t.TMS_Total_Con_Sal_SRR_B, 0)
    END AS Sal_Asignada_TM1_B,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_B = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TB, 0)
             * t.TMS_TM2_Con_Sal_SRR_B
             / NULLIF(t.TMS_Total_Con_Sal_SRR_B, 0)
    END AS Sal_Asignada_TM2_B

INTO #tms_sin_sal
FROM #tms_con_sal t
LEFT JOIN #sal_ajustada s
    ON s.Fecha = t.Fecha;

CREATE CLUSTERED INDEX IX_tms_sin_sal
ON #tms_sin_sal (Fecha);
/* ============================================================
   BLOQUE 9: TMS SIN SAL EN FORMATO FECHA / TURNO / TM
   ============================================================ */

DROP TABLE IF EXISTS #tms_tm;

SELECT
    Fecha,
    Turno,
    TM,
    TMS
INTO #tms_tm
FROM (
    SELECT
        Fecha,
        'A' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Con_Sal_SRR_A - COALESCE(Sal_Asignada_TM1_A, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'A' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Con_Sal_SRR_A - COALESCE(Sal_Asignada_TM2_A, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Con_Sal_SRR_B - COALESCE(Sal_Asignada_TM1_B, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Con_Sal_SRR_B - COALESCE(Sal_Asignada_TM2_B, 0) AS TMS
    FROM #tms_sin_sal
) x;

CREATE CLUSTERED INDEX IX_tms_tm
ON #tms_tm (Fecha, Turno, TM);
/* ============================================================
   BLOQUE 10: LEYES BASE RESUELTAS POR FECHA / TURNO / TM
   ============================================================ */

DROP TABLE IF EXISTS #leyes_base;

DECLARE @fecha_inicio_leyes_arrastre date =
    DATEADD(DAY, -90, @fecha_inicio);

SELECT *
INTO #leyes_base
FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
WHERE Fecha >= @fecha_inicio_leyes_arrastre
  AND Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_leyes_base_fecha_turno_tm
ON #leyes_base (Fecha, Turno, TM);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_fes
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (FeS, Fuente_FeS);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_consh
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (ConsH, Fuente_ConsH);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_malla12
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (Malla_Menos_1_2, Fuente_Malla_Menos_1_2);
/* ============================================================
   BLOQUE 10A: RESOLUCIÓN CRONOLÓGICA DE FeS

   RN-067:
   - El orden operacional es Fecha + Turno A + Turno B.
   - El turno A puede completar el turno B.
   - El turno B no puede modificar retroactivamente el turno A.
   - El valor nuevo del turno B rige desde B hacia adelante.
   - TM2 puede completar TM1.
   - TM1 no puede completar TM2.
   ============================================================ */

DROP TABLE IF EXISTS #fes_candidatos_dia;
DROP TABLE IF EXISTS #fes_dia_resuelta;

/* ------------------------------------------------------------
   Eventos originales válidos de FeS.

   TORRE_OTRO_TURNO_MISMO_DIA no se considera evento original,
   porque puede contener una compartición bidireccional previa.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,
    b.FeS,
    b.Fuente_FeS AS Fuente_Origen

INTO #fes_candidatos_dia

FROM #leyes_base AS b

WHERE b.FeS IS NOT NULL
  AND b.Fuente_FeS IN
  (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );

CREATE CLUSTERED INDEX IX_fes_candidatos_dia
ON #fes_candidatos_dia
(
    Fecha,
    Turno_Origen,
    TM_Origen
);

/* ------------------------------------------------------------
   Resolver cada Fecha + Turno + TM utilizando únicamente
   información cronológicamente disponible.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    c.FeS AS FeS_Nuevo_Dia,
    c.TM_Origen,
    c.Turno_Origen,

    CASE
        WHEN c.FeS IS NULL
            THEN NULL

        WHEN c.Fecha_Origen < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        /* Misma TM y mismo turno */
        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA'

        /* A completa B en la misma TM */
        WHEN c.TM_Origen = b.TM
         AND b.Turno = 'B'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_QUIMICA_OTRO_TURNO'

        /* TM2 completa TM1 en el mismo turno */
        WHEN b.TM = 'TM1'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1'

        /* TM2-A completa TM1-B */
        WHEN b.TM = 'TM1'
         AND b.Turno = 'B'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = 'A'
            THEN
                'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1_OTRO_TURNO'

        ELSE NULL
    END AS Fuente_Nuevo_Dia

INTO #fes_dia_resuelta

FROM #leyes_base AS b

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha AS Fecha_Origen,
        x.Turno_Origen,
        x.TM_Origen,
        x.FeS,
        x.Fuente_Origen

    FROM #fes_candidatos_dia AS x

    WHERE
        /* Misma TM o compartición permitida TM2 → TM1 */
        (
            x.TM_Origen = b.TM

            OR
            (
                b.TM = 'TM1'
                AND x.TM_Origen = 'TM2'
            )
        )

        /* Restricción cronológica */
        AND
        (
            x.Fecha < b.Fecha

            OR
            (
                x.Fecha = b.Fecha

                AND
                CASE
                    WHEN x.Turno_Origen = 'A' THEN 1
                    WHEN x.Turno_Origen = 'B' THEN 2
                    ELSE 9
                END
                <=
                CASE
                    WHEN b.Turno = 'A' THEN 1
                    WHEN b.Turno = 'B' THEN 2
                    ELSE 9
                END
            )
        )

    ORDER BY
        x.Fecha DESC,

        /* B es posterior a A */
        CASE
            WHEN x.Turno_Origen = 'B' THEN 2
            WHEN x.Turno_Origen = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igualdad temporal, priorizar la propia TM */
        CASE
            WHEN x.TM_Origen = b.TM THEN 1

            WHEN b.TM = 'TM1'
             AND x.TM_Origen = 'TM2' THEN 2

            ELSE 9
        END,

        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 9
        END

) AS c;

CREATE CLUSTERED INDEX IX_fes_dia_resuelta
ON #fes_dia_resuelta
(
    TM,
    Turno,
    Fecha
);
/* ============================================================
   BLOQUE 11A: RESOLUCIÓN CRONOLÓGICA MALLA -1/2

   Regla:
   - El orden operacional es Fecha + turno A + turno B.
   - Una medición válida del turno A puede completar B.
   - Una medición del turno B no puede modificar A.
   - El valor nuevo del turno B rige desde B hacia adelante.
   - TM2 puede completar TM1.
   - TM1 no completa TM2.
   - Se excluyen comparticiones bidireccionales previamente
     generadas por TORRE_OTRO_TURNO_MISMO_DIA.
   ============================================================ */

DROP TABLE IF EXISTS #malla12_candidata_dia_tm;
DROP TABLE IF EXISTS #malla12_dia_resuelta;

/* ------------------------------------------------------------
   Eventos originales válidos
   ------------------------------------------------------------ */

SELECT
    b.Fecha AS Fecha_Origen,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,

    b.Malla_Menos_1_2,
    b.Fuente_Malla_Menos_1_2 AS Fuente_Origen

INTO #malla12_candidata_dia_tm

FROM #leyes_base AS b

WHERE b.Malla_Menos_1_2 IS NOT NULL
  AND b.Malla_Menos_1_2 <> 0
  AND b.Fuente_Malla_Menos_1_2 IN
  (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );


CREATE CLUSTERED INDEX IX_malla12_candidata_fecha_turno_tm
ON #malla12_candidata_dia_tm
(
    Fecha_Origen,
    Turno_Origen,
    TM_Origen
);


/* ------------------------------------------------------------
   Resolver cada Fecha + Turno + TM utilizando solamente
   información disponible hasta ese instante.
   ------------------------------------------------------------ */

;WITH base AS
(
    SELECT DISTINCT
        Fecha,
        Turno,
        TM
    FROM #leyes_base
)

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    c.Fecha_Origen,
    c.Turno_Origen,
    c.TM_Origen,

    c.Malla_Menos_1_2,
    c.Fuente_Origen,

    CASE
        WHEN c.Malla_Menos_1_2 IS NULL
            THEN NULL

        /* El dato proviene de una fecha anterior */
        WHEN c.Fecha_Origen < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        /* Misma TM y mismo turno */
        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_FISICA'

        /* El turno A completa B en la misma TM */
        WHEN c.TM_Origen = b.TM
         AND b.Turno = 'B'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_FISICA_OTRO_TURNO'

        /* TM2 completa TM1 en el mismo turno */
        WHEN b.TM = 'TM1'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_FISICA_COMPARTIDA'

        /* TM2-A completa TM1-B */
        WHEN b.TM = 'TM1'
         AND b.Turno = 'B'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_FISICA_COMPARTIDA_OTRO_TURNO'

        ELSE NULL
    END AS Fuente_Malla_Resuelta

INTO #malla12_dia_resuelta

FROM base AS b

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha_Origen,
        x.Turno_Origen,
        x.TM_Origen,
        x.Malla_Menos_1_2,
        x.Fuente_Origen

    FROM #malla12_candidata_dia_tm AS x

    WHERE
        /* Misma TM o completitud permitida TM2 → TM1 */
        (
            x.TM_Origen = b.TM

            OR
            (
                b.TM = 'TM1'
                AND x.TM_Origen = 'TM2'
            )
        )

        /* El evento no puede ocurrir después del turno objetivo */
        AND
        (
            x.Fecha_Origen < b.Fecha

            OR
            (
                x.Fecha_Origen = b.Fecha

                AND
                CASE
                    WHEN x.Turno_Origen = 'A' THEN 1
                    WHEN x.Turno_Origen = 'B' THEN 2
                    ELSE 9
                END
                <=
                CASE
                    WHEN b.Turno = 'A' THEN 1
                    WHEN b.Turno = 'B' THEN 2
                    ELSE 9
                END
            )
        )

    ORDER BY
        /* Evento cronológico más reciente */
        x.Fecha_Origen DESC,

        CASE
            WHEN x.Turno_Origen = 'B' THEN 2
            WHEN x.Turno_Origen = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igualdad temporal, priorizar la propia TM */
        CASE
            WHEN x.TM_Origen = b.TM
                THEN 1

            WHEN b.TM = 'TM1'
             AND x.TM_Origen = 'TM2'
                THEN 2

            ELSE 9
        END,

        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO'
                THEN 1

            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
                THEN 2

            ELSE 9
        END

) AS c;


CREATE CLUSTERED INDEX
    IX_malla12_dia_resuelta_fecha_turno_tm

ON #malla12_dia_resuelta
(
    Fecha,
    Turno,
    TM
);
/* ============================================================
   BLOQUE 11B: ARRASTRE ÚLTIMO VALOR VÁLIDO
   FeS, ConsH y Malla -1/2
   ============================================================ */

DROP TABLE IF EXISTS #leyes_v2;

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    b.CuT,
    b.Fuente_CuT,

    b.CuS,
    b.Fuente_CuS,

    b.CO3,
    b.Fuente_CO3,

    b.CuFe,
    b.Fuente_CuFe,

    b.FeT,
    b.Fuente_FeT,

   ult_fes.FeS_Nuevo_Dia AS FeS,

CASE
    WHEN ult_fes.FeS_Nuevo_Dia IS NULL
        THEN b.Fuente_FeS

    WHEN ult_fes.Fecha = b.Fecha
        THEN ult_fes.Fuente_Nuevo_Dia

    WHEN ult_fes.Fecha < b.Fecha
        THEN 'ARRASTRE_ULTIMO_VALIDO'

    ELSE b.Fuente_FeS
END AS Fuente_FeS,
/* ============================================================
   ConsH con resolución cronológica

   - A puede completar B.
   - B no puede modificar retroactivamente A.
   - TM2 puede completar TM1.
   - TM1 no completa TM2.
   ============================================================ */

CASE
    WHEN b.ConsH IS NOT NULL
     AND b.ConsH <> 0
     AND b.Fuente_ConsH <> 'NO_APLICA_MINA'

     /* Para A, TORRE_OTRO_TURNO significa que tomó el dato de B */
     AND NOT
     (
         b.Turno = 'A'
         AND b.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
     )
        THEN b.ConsH

    ELSE ult_consh.ConsH
END AS ConsH,

CASE
    /* Valor propio o completitud cronológicamente válida */
    WHEN b.ConsH IS NOT NULL
     AND b.ConsH <> 0
     AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
     AND NOT
     (
         b.Turno = 'A'
         AND b.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
     )
        THEN b.Fuente_ConsH

    WHEN ult_consh.ConsH IS NULL
        THEN b.Fuente_ConsH

    /* Valor de una fecha anterior */
    WHEN ult_consh.Fecha < b.Fecha
        THEN 'ARRASTRE_ULTIMO_VALIDO'

    /* Misma TM y mismo turno */
    WHEN ult_consh.Fecha = b.Fecha
     AND ult_consh.TM_Origen = b.TM
     AND ult_consh.Turno_Origen = b.Turno
        THEN ult_consh.Fuente_ConsH

    /* A completa B dentro de la misma TM */
    WHEN ult_consh.Fecha = b.Fecha
     AND ult_consh.TM_Origen = b.TM
     AND b.Turno = 'B'
     AND ult_consh.Turno_Origen = 'A'
        THEN 'TORRE_OTRO_TURNO_MISMO_DIA'

    /* TM2 completa TM1 */
    WHEN ult_consh.Fecha = b.Fecha
     AND b.TM = 'TM1'
     AND ult_consh.TM_Origen = 'TM2'
        THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1'

    ELSE 'ARRASTRE_ULTIMO_VALIDO'
END AS Fuente_ConsH,

   ult_malla.Malla_Menos_1_2
    AS Malla_Menos_1_2,

CASE
    WHEN ult_malla.Malla_Menos_1_2 IS NULL
        THEN b.Fuente_Malla_Menos_1_2

    ELSE ult_malla.Fuente_Malla_Resuelta

END AS Fuente_Malla_Menos_1_2,

    b.Malla_Menos_100,
    b.Fuente_Malla_Menos_100,

    b.CaolBeta,
    b.Fuente_CaolBeta

INTO #leyes_v2
FROM #leyes_base b

OUTER APPLY (
    SELECT TOP (1)
        x.Fecha,
        x.FeS_Nuevo_Dia,
        x.Fuente_Nuevo_Dia
    FROM #fes_dia_resuelta x
    WHERE x.TM = b.TM
      AND x.Turno = b.Turno
      AND x.Fecha <= b.Fecha
      AND x.FeS_Nuevo_Dia IS NOT NULL
    ORDER BY
        x.Fecha DESC
) ult_fes

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha,
        x.Turno AS Turno_Origen,
        x.TM AS TM_Origen,
        x.ConsH,
        x.Fuente_ConsH

    FROM #leyes_base AS x

    WHERE x.ConsH IS NOT NULL
      AND x.ConsH <> 0
      AND x.Fuente_ConsH <> 'NO_APLICA_MINA'

      /* Excluir los A que fueron poblados desde el B futuro */
      AND NOT
      (
          x.Turno = 'A'
          AND x.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
      )

      /* Misma TM o compartición permitida TM2 → TM1 */
      AND
      (
          x.TM = b.TM
          OR
          (
              b.TM = 'TM1'
              AND x.TM = 'TM2'
          )
      )

      /* Restricción cronológica:
         - Para objetivo A: solo A del mismo día.
         - Para objetivo B: A o B del mismo día.
         - Siempre se permiten fechas anteriores.
      */
      AND
      (
          x.Fecha < b.Fecha

          OR
          (
              x.Fecha = b.Fecha
              AND
              (
                  (b.Turno = 'A' AND x.Turno = 'A')
                  OR
                  (b.Turno = 'B' AND x.Turno IN ('A', 'B'))
              )
          )
      )

    ORDER BY
        x.Fecha DESC,

        /* B es posterior a A */
        CASE
            WHEN x.Turno = 'B' THEN 2
            WHEN x.Turno = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igual instante, priorizar la propia TM */
        CASE
            WHEN x.TM = b.TM THEN 1
            WHEN b.TM = 'TM1' AND x.TM = 'TM2' THEN 2
            ELSE 9
        END,

        /* Priorizar medición original */
        CASE
            WHEN x.Fuente_ConsH = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_ConsH = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 3
        END

) AS ult_consh
OUTER APPLY
(
    SELECT TOP (1)
        d.Fecha,
        d.Turno,
        d.TM,

        d.Fecha_Origen,
        d.Turno_Origen,
        d.TM_Origen,

        d.Malla_Menos_1_2,
        d.Fuente_Origen,
        d.Fuente_Malla_Resuelta

    FROM #malla12_dia_resuelta AS d

    WHERE d.TM = b.TM
      AND d.Turno = b.Turno
      AND d.Fecha <= b.Fecha
      AND d.Malla_Menos_1_2 IS NOT NULL

    ORDER BY
        d.Fecha DESC

) AS ult_malla;

CREATE CLUSTERED INDEX IX_leyes_v2_fecha_turno_tm
ON #leyes_v2 (Fecha, Turno, TM);

/* ============================================================
   BLOQUE 11C - Ajuste CuFe según regla oficial
   Si representatividad química > 0.75, usar Clays_CuFe.
   Si no cumple, mantener CuFe ya resuelto desde MINA/Conciliación.
   ============================================================ */

UPDATE l
SET
    l.CuFe = TRY_CAST(c.CuFe AS float),
    l.Fuente_CuFe = 'TORRE'
FROM #leyes_v2 l
INNER JOIN inventar_SpcHidr.representatividad_torres_resultado r
    ON r.Dia = l.Fecha
INNER JOIN inventar_SpcHidr.Clays_CuFe c
    ON c.Fecha = l.Fecha
   AND c.Turno = CASE
                    WHEN l.Turno = 'A' THEN 'TA'
                    WHEN l.Turno = 'B' THEN 'TB'
                 END
   AND c.Torre = CASE
                    WHEN l.TM = 'TM1' THEN 'TM-1'
                    WHEN l.TM = 'TM2' THEN 'TM-2'
                 END
CROSS APPLY (
    SELECT
        CASE
            WHEN l.TM = 'TM1' AND l.Turno = 'A' THEN r.TM1_TurnoA_Quimico
            WHEN l.TM = 'TM1' AND l.Turno = 'B' THEN r.TM1_TurnoB_Quimico
            WHEN l.TM = 'TM2' AND l.Turno = 'A' THEN r.TM2_TurnoA_Quimico
            WHEN l.TM = 'TM2' AND l.Turno = 'B' THEN r.TM2_TurnoB_Quimico
        END AS Rep_Quimica_Raw
) rep
CROSS APPLY (
    SELECT
        CASE
            WHEN rep.Rep_Quimica_Raw > 1
                THEN rep.Rep_Quimica_Raw / 100.0
            ELSE rep.Rep_Quimica_Raw
        END AS Rep_Quimica_Normalizada
) rep_norm
WHERE TRY_CAST(c.CuFe AS float) IS NOT NULL
  AND ISNULL(rep_norm.Rep_Quimica_Normalizada, 0) > 0.75;

  /* ============================================================
   BLOQUE 11C.1 - Completitud CuFe TM2 -> TM1

   Si TM2 tiene CuFe representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.

   Esta regla alinea CuFe con la completitud asimétrica ya aplicada
   para CuT, CuS, CO3 y FeT.
   ============================================================ */

UPDATE tm1
SET
    tm1.CuFe = tm2.CuFe,
    tm1.Fuente_CuFe = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuFe IS NOT NULL
  AND tm2.Fuente_CuFe LIKE '%TORRE%'
  AND (
        tm1.CuFe IS NULL
     OR ISNULL(tm1.Fuente_CuFe, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11D - Ajuste FeT según regla oficial

   Si TM2 tiene FeT representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.

   Esto evita ponderar TM1 MINA + TM2 TORRE cuando el oficial clasifica
   el turno como TM2 y usa el valor representativo de TM2.
   ============================================================ */

UPDATE tm1
SET
    tm1.FeT = tm2.FeT,
    tm1.Fuente_FeT = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.FeT IS NOT NULL
  AND tm2.Fuente_FeT LIKE '%TORRE%'
  AND (
        tm1.FeT IS NULL
     OR ISNULL(tm1.Fuente_FeT, '') NOT LIKE '%TORRE%'
  );

  /* ============================================================
   BLOQUE 11E - Ajuste CO3 según regla oficial

   Si TM2 tiene CO3 representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tm1
SET
    tm1.CO3 = tm2.CO3,
    tm1.Fuente_CO3 = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CO3 IS NOT NULL
  AND tm2.Fuente_CO3 LIKE '%TORRE%'
  AND (
        tm1.CO3 IS NULL
     OR ISNULL(tm1.Fuente_CO3, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11F - Ajuste CaolBeta según reporte oficial

   CaolBeta se toma desde Clays_CuFe cuando existe dato para
   Fecha + Turno + TM. No depende de Conciliación Chancado
   cuando existe dato NIR/Clays disponible.
   ============================================================ */

UPDATE l
SET
    l.CaolBeta = clay.CaolBeta_Clays,
    l.Fuente_CaolBeta = 'CLAYS'
FROM #leyes_v2 l
INNER JOIN inventar_SpcHidr.Clays_CuFe c
    ON c.Fecha = l.Fecha
   AND c.Turno = CASE
                    WHEN l.Turno = 'A' THEN 'TA'
                    WHEN l.Turno = 'B' THEN 'TB'
                 END
   AND c.Torre = CASE
                    WHEN l.TM = 'TM1' THEN 'TM-1'
                    WHEN l.TM = 'TM2' THEN 'TM-2'
                 END
OUTER APPLY (
    SELECT
        TRY_CONVERT(float, REPLACE(CONVERT(varchar(50), c.CaolBeta), ',', '.')) AS CaolBeta_Clays
) clay
WHERE clay.CaolBeta_Clays IS NOT NULL;

/* ============================================================
   BLOQUE 11G - Ajuste CuT según regla oficial

   Si TM2 tiene CuT representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tm1
SET
    tm1.CuT = tm2.CuT,
    tm1.Fuente_CuT = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuT IS NOT NULL
  AND tm2.Fuente_CuT LIKE '%TORRE%'
  AND (
        tm1.CuT IS NULL
     OR ISNULL(tm1.Fuente_CuT, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11H - Ajuste CuS según regla oficial

   Si TM2 tiene CuS representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tm1
SET
    tm1.CuS = tm2.CuS,
    tm1.Fuente_CuS = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuS IS NOT NULL
  AND tm2.Fuente_CuS LIKE '%TORRE%'
  AND (
        tm1.CuS IS NULL
     OR ISNULL(tm1.Fuente_CuS, '') NOT LIKE '%TORRE%'
  );
/* ============================================================
   BLOQUE 11I - Guarda de evaluabilidad por origen operacional

   RN-064 ampliada:
   - El TMS siempre proviene de CV008/CV108.
   - STOCK, MINA y SRR constituyen evidencia oficial.
   - IMP positivo constituye evidencia operacional provisional.
   - IMP no reemplaza ni distribuye el TMS.
   - Si CV008/CV108 entregan TMS cero, IMP no habilita tonelaje.
   ============================================================ */

UPDATE t
SET
    t.TMS = 0
FROM #tms_tm AS t

LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr AS o
    ON o.Fecha = t.Fecha
   AND o.Turno = t.Turno

LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS c
    ON c.Fecha = t.Fecha
   AND c.Turno = t.Turno

WHERE ISNULL(t.TMS, 0) > 0

  /* No existe evidencia operacional oficial */
  AND ISNULL(o.Ton_Stock_Camiones, 0) = 0
  AND ISNULL(o.Ton_Mina_Camiones, 0) = 0
  AND ISNULL(o.Ton_SRR, 0) = 0

  /* Tampoco existe evidencia provisional IMP */
  AND NOT
  (
      UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato, '')))) = 'IMP'
      AND ISNULL(c.Ton, 0) > 0
  );

/* ============================================================
   BLOQUE 12: PONDERACIÓN DE LEYES REALES POR TMS
   ============================================================ */

DROP TABLE IF EXISTS #reales;

SELECT
    t.Fecha,
    t.Turno,

    SUM(t.TMS) AS Apilado_TMS_Real,

    SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuT_Real,

    SUM(t.TMS * l.CuS) / NULLIF(SUM(CASE WHEN l.CuS IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuS_Real,

    CASE
        WHEN SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) IS NULL
          OR SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) = 0
        THEN NULL
        ELSE
            (
                SUM(t.TMS * l.CuS) / NULLIF(SUM(CASE WHEN l.CuS IS NOT NULL THEN t.TMS ELSE 0 END), 0)
            )
            /
            (
                SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0)
            )
    END AS Solubilidad_Real,

    SUM(t.TMS * l.CO3) / NULLIF(SUM(CASE WHEN l.CO3 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CO3_Real,

    SUM(t.TMS * l.CuFe) / NULLIF(SUM(CASE WHEN l.CuFe IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuFe_Real,

    SUM(t.TMS * l.FeT) / NULLIF(SUM(CASE WHEN l.FeT IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS FeT_Real,

    SUM(t.TMS * l.FeS) / NULLIF(SUM(CASE WHEN l.FeS IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS FeS_Real,

    SUM(t.TMS * l.ConsH) / NULLIF(SUM(CASE WHEN l.ConsH IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS ConsH_Real,

    SUM(t.TMS * l.Malla_Menos_1_2) / NULLIF(SUM(CASE WHEN l.Malla_Menos_1_2 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS Malla_Menos_1_2_Real,

    SUM(t.TMS * l.Malla_Menos_100) / NULLIF(SUM(CASE WHEN l.Malla_Menos_100 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS Malla_Menos_100_Real,

    SUM(t.TMS * l.CaolBeta) / NULLIF(SUM(CASE WHEN l.CaolBeta IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CaolBeta_Real

INTO #reales
FROM #tms_tm t
LEFT JOIN #leyes_v2 l
    ON l.Fecha = t.Fecha
   AND l.Turno = t.Turno
   AND l.TM = t.TM
GROUP BY
    t.Fecha,
    t.Turno;

CREATE CLUSTERED INDEX IX_reales_fecha_turno
ON #reales (Fecha, Turno);

/* ============================================================
   BLOQUE 13: CLASIFICACIÓN DE MUESTRA QUÍMICA Y FÍSICA

   Ajuste:
   - Se incorpora IMP como fuente válida de conciliación.
   - No se modifica la prioridad de TORRE, MINA, ARRASTRE
     ni SEMILLA.
   ============================================================ */

DROP TABLE IF EXISTS #muestras;

WITH fuentes AS
(
    SELECT
        Fecha,
        Turno,

        /* ----------------------------------------------------
           Fuentes químicas
           ---------------------------------------------------- */

        MAX
        (
            CASE
                WHEN Fuente_CuT  LIKE '%TORRE%'
                  OR Fuente_CuS  LIKE '%TORRE%'
                  OR Fuente_CO3  LIKE '%TORRE%'
                  OR Fuente_CuFe LIKE '%TORRE%'
                  OR Fuente_FeT  LIKE '%TORRE%'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Torre,

        MAX
        (
            CASE
                WHEN Fuente_CuT  = 'MINA'
                  OR Fuente_CuS  = 'MINA'
                  OR Fuente_CO3  = 'MINA'
                  OR Fuente_CuFe = 'MINA'
                  OR Fuente_FeT  = 'MINA'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Mina,

        /* Nueva clasificación IMP */
        MAX
        (
            CASE
                WHEN Fuente_CuT  = 'IMP'
                  OR Fuente_CuS  = 'IMP'
                  OR Fuente_CO3  = 'IMP'
                  OR Fuente_CuFe = 'IMP'
                  OR Fuente_FeT  = 'IMP'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_IMP,

        MAX
        (
            CASE
                WHEN Fuente_FeS  = 'ARRASTRE_ULTIMO_VALIDO'
                  OR Fuente_ConsH = 'ARRASTRE_ULTIMO_VALIDO'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Arrastre,

        MAX
        (
            CASE
                WHEN Fuente_CuT   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CuS   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CO3   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CuFe  = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_FeT   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_FeS   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_ConsH = 'SEMILLA_INICIO_PERIODO'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Semilla,

        /* ----------------------------------------------------
           Fuentes físicas
           ---------------------------------------------------- */

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                  OR Fuente_Malla_Menos_100 LIKE '%TORRE%'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Torre,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'MINA'
                  OR Fuente_Malla_Menos_100 = 'MINA'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Mina,

        /* Nueva clasificación IMP */
        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'IMP'
                  OR Fuente_Malla_Menos_100 = 'IMP'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_IMP,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'ARRASTRE_ULTIMO_VALIDO'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Arrastre,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_Malla_Menos_100 = 'SEMILLA_INICIO_PERIODO'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Semilla

    FROM #leyes_v2

    GROUP BY
        Fecha,
        Turno
)

SELECT
    Fecha,
    Turno,

    CASE
        WHEN Quimica_Semilla = 1
            THEN 'SEMILLA'

        WHEN Quimica_Arrastre = 1
         AND
         (
             Quimica_Torre = 1
             OR Quimica_Mina = 1
             OR Quimica_IMP = 1
         )
            THEN 'MIXTA'

        WHEN Quimica_Torre + Quimica_Mina + Quimica_IMP >= 2
            THEN 'MIXTA'

        WHEN Quimica_Arrastre = 1
            THEN 'ARRASTRE'

        WHEN Quimica_Torre = 1
            THEN 'TORRE'

        WHEN Quimica_IMP = 1
            THEN 'IMP'

        WHEN Quimica_Mina = 1
            THEN 'MINA'

        ELSE NULL
    END AS Muestra_Quimica,

    CASE
        WHEN Fisica_Semilla = 1
            THEN 'SEMILLA'

        WHEN Fisica_Arrastre = 1
         AND
         (
             Fisica_Torre = 1
             OR Fisica_Mina = 1
             OR Fisica_IMP = 1
         )
            THEN 'MIXTA'

        WHEN Fisica_Torre + Fisica_Mina + Fisica_IMP >= 2
            THEN 'MIXTA'

        WHEN Fisica_Arrastre = 1
            THEN 'ARRASTRE'

        WHEN Fisica_Torre = 1
            THEN 'TORRE'

        WHEN Fisica_IMP = 1
            THEN 'IMP'

        WHEN Fisica_Mina = 1
            THEN 'MINA'

        ELSE NULL
    END AS Muestra_Fisica

INTO #muestras

FROM fuentes;

CREATE CLUSTERED INDEX IX_muestras_fecha_turno
ON #muestras (Fecha, Turno);
/* ============================================================
   BLOQUE 14: CAMPAÑA, MÓDULO, AVANCE Y PLAN
   ============================================================ */

DROP TABLE IF EXISTS #campania_modulo;
DROP TABLE IF EXISTS #plan_mensual;
DROP TABLE IF EXISTS #plan_semanal;
DROP TABLE IF EXISTS #origen_apilado;

SELECT
    Fecha,
    Fecha_Origen_Relleno,
    Fecha_Topografia_Usada,
    Campania,
    Material,
    Modulo,
    Avance,
    Volumen_Diario_Modulo_m3,
    Fuente_Campania_Modulo
INTO #campania_modulo
FROM inventar_SpcHidr.v_reporte_turno_campania_modulo_test
WHERE Fecha >= @fecha_inicio
  AND Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_campania_modulo
ON #campania_modulo (Fecha);


/* ============================================================
   PLAN MENSUAL
   ============================================================ */

SELECT
    fecha AS Fecha,
    apilamiento AS Apilado_TMS_Plan_Mensual,
    cut AS CuT_Plan_Mensual,
    cus AS CuS_Plan_Mensual,
    CAST(
    CASE
        WHEN cut IS NULL OR cut = 0 OR cus IS NULL THEN NULL
        ELSE cus / cut
    END
    AS decimal(18, 6)) AS Solubilidad_Plan_Mensual,
    co3 AS CO3_Plan_Mensual,
    cl_acido AS ConsH_Plan_Mensual,
    cufe AS CuFe_Plan_Mensual,
    malla_100 AS Malla_Menos_100_Plan_Mensual,
    caol_beta AS CaolBeta_Plan_Mensual
INTO #plan_mensual
FROM inventar_SpcHidr.plan_mensual_reporte_turno
WHERE fecha >= @fecha_inicio
  AND fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_plan_mensual
ON #plan_mensual (Fecha);


/* ============================================================
   PLAN SEMANAL
   ============================================================ */

SELECT
    fecha AS Fecha,
    ton AS Apilado_TMS_Plan_Semanal,
    cut AS CuT_Plan_Semanal,
    cus AS CuS_Plan_Semanal,
    CAST(
    CASE
        WHEN cut IS NULL OR cut = 0 OR cus IS NULL THEN NULL
        ELSE cus / cut
    END
    AS decimal(18, 6)) AS Solubilidad_Plan_Semanal,
    co3 AS CO3_Plan_Semanal,
    cl_acido AS ConsH_Plan_Semanal,
    cufe AS CuFe_Plan_Semanal,
    malla_100 AS Malla_Menos_100_Plan_Semanal,
    betaclay AS CaolBeta_Plan_Semanal,
    porc_1_2 AS Malla_Menos_1_2_Plan_Semanal,
    arcillas AS Arcillas_Plan_Semanal,
    cuarzo AS Cuarzo_Plan_Semanal
INTO #plan_semanal
FROM inventar_SpcHidr.plan_semanal_reporte_turno
WHERE fecha >= @fecha_inicio
  AND fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_plan_semanal
ON #plan_semanal (Fecha);


 /* ============================================================
   BLOQUE 15: DISTRIBUCIÓN FINAL STOCK / MINA / SRR

   Prioridad:
   1. Origen oficial desde mov_cam.
   2. IMP provisional:
      - SRR = Es_SRR = 1
      - Camiones = STOCK
      - MINA = 0
   3. Sin origen: proporciones en cero.

   IMPORTANTE:
   IMP no reemplaza Apilado_TMS_Real.
   Solo determina las proporciones de origen.
   ============================================================ */

DROP TABLE IF EXISTS #imp_origen_turno;
DROP TABLE IF EXISTS #origen_apilado;


/* ------------------------------------------------------------
   15A. Consolidación IMP por Fecha + Turno
   ------------------------------------------------------------ */

SELECT
    CAST(i.Fecha AS date) AS Fecha,

    CASE
        WHEN i.Turno IN ('TA', 'A') THEN 'A'
        WHEN i.Turno IN ('TB', 'B') THEN 'B'
        ELSE i.Turno
    END COLLATE DATABASE_DEFAULT AS Turno,

    CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 1
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_SRR,

    CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 0
                 AND UPPER(LTRIM(RTRIM(ISNULL(i.Tipo_Registro, ''))))
                     = 'CAMION'
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_Camiones,

    CAST
    (
        SUM(ISNULL(i.Ton, 0))
        AS decimal(38,10)
    ) AS Ton_IMP_Total

INTO #imp_origen_turno

FROM PROD_SIIR.hidro.v_imp_chancado_normalizado AS i

WHERE i.Fecha >= @fecha_inicio
  AND i.Fecha <  @fecha_fin
  AND ISNULL(i.Ton, 0) > 0

GROUP BY
    CAST(i.Fecha AS date),

    CASE
        WHEN i.Turno IN ('TA', 'A') THEN 'A'
        WHEN i.Turno IN ('TB', 'B') THEN 'B'
        ELSE i.Turno
    END COLLATE DATABASE_DEFAULT;


CREATE CLUSTERED INDEX IX_imp_origen_turno
ON #imp_origen_turno (Fecha, Turno);


/* ------------------------------------------------------------
   15B. Determinación de la fuente de origen
   ------------------------------------------------------------ */

;WITH origen_base AS
(
    SELECT
        r.Fecha,
        r.Turno,

        CAST
        (
            ISNULL(r.Apilado_TMS_Real, 0)
            AS decimal(38,10)
        ) AS Apilado_TMS_Real,

        /* Fuente oficial */

        CAST
        (
            ISNULL(p.Ton_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Stock_Oficial,

        CAST
        (
            ISNULL(p.Ton_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Mina_Oficial,

        CAST
        (
            ISNULL(p.Ton_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_SRR_Oficial,

        CAST
        (
            ISNULL(p.Prop_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Prop_Stock_Oficial,

        CAST
        (
            ISNULL(p.Prop_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Prop_Mina_Oficial,

        /* Fuente IMP */

        CAST
        (
            ISNULL(i.Ton_IMP_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_SRR,

        CAST
        (
            ISNULL(i.Ton_IMP_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Camiones,

        CAST
        (
            ISNULL(i.Ton_IMP_Total, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Total,

        c.Fuente_Dato,

        CASE
            /* Prioridad 1: origen oficial positivo */

            WHEN ISNULL(p.Ton_Stock_Camiones, 0) > 0
              OR ISNULL(p.Ton_Mina_Camiones, 0) > 0
              OR ISNULL(p.Ton_SRR, 0) > 0
                THEN 'OFICIAL'

            /* Prioridad 2: respaldo provisional IMP */

            WHEN UPPER
                 (
                     LTRIM
                     (
                         RTRIM
                         (
                             ISNULL(c.Fuente_Dato, '')
                         )
                     )
                 ) = 'IMP'
             AND ISNULL(i.Ton_IMP_Total, 0) > 0
                THEN 'IMP'

            ELSE 'SIN_ORIGEN'
        END AS Fuente_Origen

    FROM #reales AS r

    LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr AS p
        ON p.Fecha = r.Fecha
       AND p.Turno = r.Turno

    LEFT JOIN #imp_origen_turno AS i
        ON i.Fecha = r.Fecha
       AND i.Turno = r.Turno

    LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS c
        ON c.Fecha = r.Fecha
       AND c.Turno = r.Turno
),

origen_srr AS
(
    SELECT
        b.*,

        /* SRR limitado al Apilado_TMS_Real */

        CAST
        (
            CASE
                WHEN b.Apilado_TMS_Real <= 0
                    THEN 0

                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN
                        CASE
                            WHEN b.Ton_SRR_Oficial <= 0
                                THEN 0

                            WHEN b.Ton_SRR_Oficial
                               > b.Apilado_TMS_Real
                                THEN b.Apilado_TMS_Real

                            ELSE b.Ton_SRR_Oficial
                        END

                WHEN b.Fuente_Origen = 'IMP'
                    THEN
                        CASE
                            WHEN b.Ton_IMP_SRR <= 0
                                THEN 0

                            WHEN b.Ton_IMP_SRR
                               > b.Apilado_TMS_Real
                                THEN b.Apilado_TMS_Real

                            ELSE b.Ton_IMP_SRR
                        END

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Ton_SRR_Usado,

        /* Proporción de camiones STOCK */

        CAST
        (
            CASE
                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN b.Prop_Stock_Oficial

                WHEN b.Fuente_Origen = 'IMP'
                 AND b.Ton_IMP_Camiones > 0
                    THEN 1.0

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Prop_Stock_Camiones_Usada,

        /* Proporción de camiones MINA */

        CAST
        (
            CASE
                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN b.Prop_Mina_Oficial

                WHEN b.Fuente_Origen = 'IMP'
                    THEN 0

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Prop_Mina_Camiones_Usada

    FROM origen_base AS b
),

origen_calculado AS
(
    SELECT
        s.*,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
                    (
                        s.Apilado_TMS_Real
                      - s.Ton_SRR_Usado
                    )
                    * s.Prop_Stock_Camiones_Usada
                    / NULLIF(s.Apilado_TMS_Real, 0)
            END
            AS decimal(18,8)
        ) AS Prop_Final_Stock,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
                    (
                        s.Apilado_TMS_Real
                      - s.Ton_SRR_Usado
                    )
                    * s.Prop_Mina_Camiones_Usada
                    / NULLIF(s.Apilado_TMS_Real, 0)
            END
            AS decimal(18,8)
        ) AS Prop_Final_Mina,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
                    s.Ton_SRR_Usado
                    / NULLIF(s.Apilado_TMS_Real, 0)
            END
            AS decimal(18,8)
        ) AS Prop_Final_SRR

    FROM origen_srr AS s
)

SELECT
    o.Fecha,
    o.Turno,

    o.Prop_Final_Stock,
    o.Prop_Final_Mina,
    o.Prop_Final_SRR,

    CAST
    (
        o.Prop_Final_Stock
      + o.Prop_Final_Mina
      + o.Prop_Final_SRR
        AS decimal(18,8)
    ) AS Prop_Final_Total,

    /* Diferencia de tonelaje contra TMS real */

    CAST
    (
        (
            (
                o.Apilado_TMS_Real
              - o.Ton_SRR_Usado
            )
            * o.Prop_Stock_Camiones_Usada
        )
      + (
            (
                o.Apilado_TMS_Real
              - o.Ton_SRR_Usado
            )
            * o.Prop_Mina_Camiones_Usada
        )
      + o.Ton_SRR_Usado
      - o.Apilado_TMS_Real

        AS decimal(18,8)
    ) AS Check_Distribucion_Apilado,

    /* Columnas de auditoría */

    o.Fuente_Origen,
    o.Ton_SRR_Usado,
    o.Ton_IMP_SRR,
    o.Ton_IMP_Camiones,
    o.Ton_Stock_Oficial,
    o.Ton_Mina_Oficial,
    o.Ton_SRR_Oficial

INTO #origen_apilado

FROM origen_calculado AS o;


CREATE CLUSTERED INDEX IX_origen_apilado
ON #origen_apilado (Fecha, Turno);

/* ============================================================
   SELECT FINAL - ORDEN FORMATO BHP
   ============================================================ */

SELECT
    r.Fecha,
    cm.Campania,
    cm.Material,
    cm.Modulo,
    cm.Avance,
    r.Turno,

    /* Apilado */
    r.Apilado_TMS_Real,
    pm.Apilado_TMS_Plan_Mensual,

    /* Distribución de origen */
    CAST(100.0 * COALESCE(oa.Prop_Final_Stock, 0) AS decimal(18, 2)) AS STOCK,
    CAST(100.0 * COALESCE(oa.Prop_Final_Mina, 0) AS decimal(18, 2)) AS MINA,
    CAST(100.0 * COALESCE(oa.Prop_Final_SRR, 0) AS decimal(18, 2)) AS SRR,

    /* Análisis químicos */
    r.CuT_Real,
    pm.CuT_Plan_Mensual,
    ps.CuT_Plan_Semanal,

    r.CuS_Real,
    pm.CuS_Plan_Mensual,
    ps.CuS_Plan_Semanal,

    r.Solubilidad_Real,
    pm.Solubilidad_Plan_Mensual,
    ps.Solubilidad_Plan_Semanal,

    r.CO3_Real,
    pm.CO3_Plan_Mensual,
    ps.CO3_Plan_Semanal,

    r.CuFe_Real,
    pm.CuFe_Plan_Mensual,
    ps.CuFe_Plan_Semanal,

    r.FeT_Real,
    r.FeS_Real,

    /* Dosis / consumo ácido */
    r.ConsH_Real,
  
    /* Granulometrías */
    r.Malla_Menos_1_2_Real,
    ps.Malla_Menos_1_2_Plan_Semanal,

    r.Malla_Menos_100_Real,
    pm.Malla_Menos_100_Plan_Mensual,
    ps.Malla_Menos_100_Plan_Semanal,

 /* NIR */
r.CaolBeta_Real,
pm.CaolBeta_Plan_Mensual,
ps.CaolBeta_Plan_Semanal,

/* Dosis de ácido */
CAST(
    ROUND(
        CASE
            WHEN ISNULL(r.Solubilidad_Real, 0) < 0.25 THEN
                CASE
                    WHEN ISNULL(r.CO3_Real, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(r.CO3_Real, 0))
                END

            ELSE
                CASE
                    WHEN r.CuS_Real IS NULL OR r.CuS_Real <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(r.CuS_Real))
                               + 18.99
                               + (15.51 * ISNULL(r.CO3_Real, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(r.CuS_Real))
                               + 18.99
                               + (15.51 * ISNULL(r.CO3_Real, 0))
                        END
                END
        END
    , 2)
AS decimal(18, 2)) AS Dosis_Acido_Ideal_TM,

CAST(
    ROUND(
        CASE
            WHEN ISNULL(ps.Solubilidad_Plan_Semanal, 0) < 0.25 THEN
                CASE
                    WHEN ISNULL(ps.CO3_Plan_Semanal, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0))
                END

            ELSE
                CASE
                    WHEN ps.CuS_Plan_Semanal IS NULL OR ps.CuS_Plan_Semanal <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(ps.CuS_Plan_Semanal))
                               + 18.99
                               + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(ps.CuS_Plan_Semanal))
                               + 18.99
                               + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0))
                        END
                END
        END
    , 2)
AS decimal(18, 2)) AS Dosis_Acido_Programa_Semanal,

        /* Fuentes de información explícitas */
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN '-'
        ELSE COALESCE(fi.Fuente_Info_Quimica, '-')
    END AS Fuente_Info_Quimica,

    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN '-'
        ELSE COALESCE(fi.Fuente_Info_Fisica, '-')
    END AS Fuente_Info_Fisica,

    /* Clasificación técnica original */
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN NULL
        ELSE m.Muestra_Quimica
    END AS Muestra_Quimica,

    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN NULL
        ELSE m.Muestra_Fisica
    END AS Muestra_Fisica

FROM #reales r

LEFT JOIN #muestras m
    ON m.Fecha = r.Fecha
   AND m.Turno = r.Turno

LEFT JOIN inventar_SpcHidr.v_reporte_turno_fuentes_info_test fi
    ON fi.Fecha = r.Fecha
   AND fi.Turno = r.Turno

LEFT JOIN #campania_modulo cm
    ON cm.Fecha = r.Fecha

LEFT JOIN #origen_apilado oa
    ON oa.Fecha = r.Fecha
   AND oa.Turno = r.Turno

LEFT JOIN #plan_mensual pm
    ON pm.Fecha = r.Fecha

LEFT JOIN #plan_semanal ps
    ON ps.Fecha = r.Fecha

ORDER BY
    r.Fecha,
    r.Turno;
END;
GO

-- ==== inventar_SpcHidr.sp_reporte_turno_emision_test ====
CREATE OR ALTER PROCEDURE inventar_SpcHidr.sp_reporte_turno_emision_test
    @fecha_inicio date,
    @fecha_fin    date
AS
BEGIN
    SET NOCOUNT ON;

    /* ============================================================
       LIMPIEZA TEMPORALES
       ============================================================ */

    DROP TABLE IF EXISTS #fechas;
    DROP TABLE IF EXISTS #hum;
    DROP TABLE IF EXISTS #hum_rep;
    DROP TABLE IF EXISTS #hum_torre_dia;
    DROP TABLE IF EXISTS #hum_torre_dia_final;
    DROP TABLE IF EXISTS #candidatos;
    DROP TABLE IF EXISTS #humedad_resuelta;
    DROP TABLE IF EXISTS #fes_candidatos_dia;
    DROP TABLE IF EXISTS #fes_dia_resuelta;

 /* ============================================================
   BLOQUE 1: TMH BASE DESDE APILADO
   Depuración anti-spike por correa/turno
   ============================================================ */

DECLARE @umbral_tmh_spike_turno decimal(18,6) = 150000.0;

WITH tmh_raw AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        CAST(ISNULL(TMH_CV008_A, 0) AS decimal(18,6)) AS TMH_CV008_A_Raw,
        CAST(ISNULL(TMH_CV008_B, 0) AS decimal(18,6)) AS TMH_CV008_B_Raw,
        CAST(ISNULL(TMH_CV108_A, 0) AS decimal(18,6)) AS TMH_CV108_A_Raw,
        CAST(ISNULL(TMH_CV108_B, 0) AS decimal(18,6)) AS TMH_CV108_B_Raw
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2
    WHERE Fecha >= @fecha_inicio
      AND Fecha <  @fecha_fin
),
tmh_limpia AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        CASE
            WHEN ABS(TMH_CV008_A_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV008_A_Raw
        END AS TMH_CV008_A,

        CASE
            WHEN ABS(TMH_CV008_B_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV008_B_Raw
        END AS TMH_CV008_B,

        CASE
            WHEN ABS(TMH_CV108_A_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV108_A_Raw
        END AS TMH_CV108_A,

        CASE
            WHEN ABS(TMH_CV108_B_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV108_B_Raw
        END AS TMH_CV108_B
    FROM tmh_raw
)
SELECT
    Fecha,
    Flag_Apilado_Valido,

    TMH_CV008_A,
    TMH_CV008_B,
    TMH_CV108_A,
    TMH_CV108_B,

    TMH_CV008_A + TMH_CV108_A AS TMH_Apilado_Total_A,
    TMH_CV008_B + TMH_CV108_B AS TMH_Apilado_Total_B,
    TMH_CV008_A + TMH_CV108_A + TMH_CV008_B + TMH_CV108_B AS TMH_Apilado_Total_Dia

INTO #fechas
FROM tmh_limpia;

/* ============================================================
   BLOQUE 2: HUMEDAD LABORATORIO
   Optimizado con ventana histórica razonable
   ============================================================ */

DECLARE @fecha_inicio_humedad date = DATEADD(DAY, -90, @fecha_inicio);

SELECT
    CAST(Fecha AS date) AS Fecha,
    Torre,
    Turno,
    AVG(CAST(Humedad_Prom_Pct AS float)) AS Humedad_Prom_Pct
INTO #hum
FROM inventar_SpcHidr.Informe_TM_lab
WHERE Humedad_Prom_Pct IS NOT NULL
  AND Fecha >= @fecha_inicio_humedad
  AND Fecha <  @fecha_fin
GROUP BY
    CAST(Fecha AS date),
    Torre,
    Turno;

CREATE CLUSTERED INDEX IX_hum
ON #hum (Fecha, Torre, Turno);

/* ============================================================
   BLOQUE 3: HUMEDAD + REPRESENTATIVIDAD FÍSICA
   Optimizado: usa resultado materializado
   ============================================================ */

SELECT
    h.Fecha,
    h.Torre,
    h.Turno,
    h.Humedad_Prom_Pct,
    CASE
        WHEN h.Torre = 'T1' AND h.Turno = 'A' THEN r.TM1_TurnoA_Fisico
        WHEN h.Torre = 'T1' AND h.Turno = 'B' THEN r.TM1_TurnoB_Fisico
        WHEN h.Torre = 'T2' AND h.Turno = 'A' THEN r.TM2_TurnoA_Fisico
        WHEN h.Torre = 'T2' AND h.Turno = 'B' THEN r.TM2_TurnoB_Fisico
    END AS Representatividad_Fisica
INTO #hum_rep
FROM #hum h
LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado r
    ON r.Dia = h.Fecha;

CREATE CLUSTERED INDEX IX_hum_rep
ON #hum_rep (Fecha, Torre, Turno);

  /* ============================================================
   BLOQUE 4: HUMEDADES REPRESENTATIVAS POR FECHA + TURNO

   Corrección:
   - No se reduce A/B a una sola humedad diaria.
   - Se conserva el orden cronológico A -> B.
   - Cada TM prioriza su humedad propia.
   - Cuando no existe humedad propia más reciente, utiliza
     la humedad representativa vigente de la otra torre.
   ============================================================ */

SELECT
    Fecha,
    Torre,
    Turno AS Turno_Humedad,
    Humedad_Prom_Pct AS Humedad_Torre_Dia,
    Representatividad_Fisica,

    DATEADD
    (
        HOUR,
        CASE
            WHEN Turno = 'A' THEN 8
            ELSE 20
        END,
        CAST(Fecha AS datetime2(0))
    ) AS FechaTurno_Origen

INTO #candidatos

FROM #hum_rep

WHERE Humedad_Prom_Pct IS NOT NULL
  AND Representatividad_Fisica >= 0.75;


CREATE CLUSTERED INDEX IX_candidatos
ON #candidatos
(
    FechaTurno_Origen DESC,
    Torre
);


/* ============================================================
   BLOQUE 5: RESOLUCIÓN CRONOLÓGICA POR FECHA + TURNO
   ============================================================ */

;WITH periodos AS
(
    SELECT
        f.Fecha,
        t.Turno_Objetivo,

        DATEADD
        (
            HOUR,
            CASE
                WHEN t.Turno_Objetivo = 'A' THEN 8
                ELSE 20
            END,
            CAST(f.Fecha AS datetime2(0))
        ) AS FechaTurno_Objetivo

    FROM #fechas AS f

    CROSS JOIN
    (
        VALUES
            ('A'),
            ('B')
    ) AS t(Turno_Objetivo)
),

resuelta_turno AS
(
    SELECT
        p.Fecha,
        p.Turno_Objetivo,

        /* ====================================================
           TM1
           ==================================================== */

        tm1.Humedad_Torre_Dia
            AS Humedad_TM1,

        tm1.Fecha
            AS Fecha_Origen_TM1,

        tm1.Torre
            AS Torre_Origen_TM1,

        tm1.Turno_Humedad
            AS Turno_Origen_TM1,

        tm1.Fuente_Humedad
            AS Fuente_Humedad_TM1,

        /* ====================================================
           TM2
           ==================================================== */

        tm2.Humedad_Torre_Dia
            AS Humedad_TM2,

        tm2.Fecha
            AS Fecha_Origen_TM2,

        tm2.Torre
            AS Torre_Origen_TM2,

        tm2.Turno_Humedad
            AS Turno_Origen_TM2,

        tm2.Fuente_Humedad
            AS Fuente_Humedad_TM2

    FROM periodos AS p

    /* --------------------------------------------------------
       Resolución TM1
       -------------------------------------------------------- */

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno_Humedad,
            c.Humedad_Torre_Dia,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno_Humedad,
                h.Humedad_Torre_Dia,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T1'
                            THEN 'PROPIA_TM1'
                        ELSE 'COMPARTIDA_DESDE_TM2'
                    END
                    AS varchar(23)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T1' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM #candidatos AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(10)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'HUMEDAD_INICIAL_PERIODO'
                    AS varchar(23)
                ),

                3

            FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s

            WHERE s.tm = 'TM1'
              AND CAST(s.fecha_origen AS datetime2(0))
                    <= p.FechaTurno_Objetivo
        ) AS c

        ORDER BY
            c.FechaTurno_Origen DESC,
            c.Prioridad ASC

    ) AS tm1

    /* --------------------------------------------------------
       Resolución TM2
       -------------------------------------------------------- */

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno_Humedad,
            c.Humedad_Torre_Dia,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno_Humedad,
                h.Humedad_Torre_Dia,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T2'
                            THEN 'PROPIA_TM2'
                        ELSE 'COMPARTIDA_DESDE_TM1'
                    END
                    AS varchar(23)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T2' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM #candidatos AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(10)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'HUMEDAD_INICIAL_PERIODO'
                    AS varchar(23)
                ),

                3

            FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s

            WHERE s.tm = 'TM2'
              AND CAST(s.fecha_origen AS datetime2(0))
                    <= p.FechaTurno_Objetivo
        ) AS c

        ORDER BY
            c.FechaTurno_Origen DESC,
            c.Prioridad ASC

    ) AS tm2
),

/* ============================================================
   BLOQUE 6: PIVOT A/B Y HUMEDAD RESUELTA POR FECHA

   Las columnas Humedad_TM1 y Humedad_TM2 se mantienen para
   compatibilidad y representan el valor vigente al cierre del día.
   ============================================================ */

humedad_resuelta_cte AS
(
    SELECT
        f.*,

        /* Humedades efectivas por turno */

        a.Humedad_TM1 AS Humedad_TM1_A,
        b.Humedad_TM1 AS Humedad_TM1_B,

        a.Humedad_TM2 AS Humedad_TM2_A,
        b.Humedad_TM2 AS Humedad_TM2_B,

        /* Humedad vigente al cierre diario */

        COALESCE
        (
            b.Humedad_TM1,
            a.Humedad_TM1
        ) AS Humedad_TM1,

        COALESCE
        (
            b.Humedad_TM2,
            a.Humedad_TM2
        ) AS Humedad_TM2,

        /* Trazabilidad TM1 */

        COALESCE
        (
            b.Fecha_Origen_TM1,
            a.Fecha_Origen_TM1
        ) AS Fecha_Humedad_TM1,

        COALESCE
        (
            b.Torre_Origen_TM1,
            a.Torre_Origen_TM1
        ) AS Torre_Humedad_TM1,

        COALESCE
        (
            b.Turno_Origen_TM1,
            a.Turno_Origen_TM1
        ) AS Turno_Humedad_TM1,

        COALESCE
        (
            b.Fuente_Humedad_TM1,
            a.Fuente_Humedad_TM1
        ) AS Fuente_Humedad_TM1,

        /* Trazabilidad TM2 */

        COALESCE
        (
            b.Fecha_Origen_TM2,
            a.Fecha_Origen_TM2
        ) AS Fecha_Humedad_TM2,

        COALESCE
        (
            b.Torre_Origen_TM2,
            a.Torre_Origen_TM2
        ) AS Torre_Humedad_TM2,

        COALESCE
        (
            b.Turno_Origen_TM2,
            a.Turno_Origen_TM2
        ) AS Turno_Humedad_TM2,

        COALESCE
        (
            b.Fuente_Humedad_TM2,
            a.Fuente_Humedad_TM2
        ) AS Fuente_Humedad_TM2

    FROM #fechas AS f

    LEFT JOIN resuelta_turno AS a
        ON a.Fecha = f.Fecha
       AND a.Turno_Objetivo = 'A'

    LEFT JOIN resuelta_turno AS b
        ON b.Fecha = f.Fecha
       AND b.Turno_Objetivo = 'B'
)

SELECT *
INTO #humedad_resuelta
FROM humedad_resuelta_cte;


CREATE CLUSTERED INDEX IX_humedad_resuelta
ON #humedad_resuelta (Fecha);
    /* ============================================================
   BLOQUE 7: FACTOR DE AJUSTE CAMIONES V2 + CÁLCULO TMS

   Fuente única de emisión:
       inventar_SpcHidr.v_ajuste_camiones_emision_test

   Regla:
   - Factor válido: aplica el factor diario a CV008/CV108 por turno.
   - Factor no evaluable: Factor_Aplicacion_Reportes = 1 (fallback),
     conservando por separado el estado real del cálculo.
   - El TMS se calcula DESDE LOS TMH AJUSTADOS.
   - Los bloques posteriores de sal, leyes, ponderaciones, IMP y
     clasificación permanecen sin cambios.
   ============================================================ */
DROP TABLE IF EXISTS #base_tms;
DROP TABLE IF EXISTS #tms_con_sal;

SELECT
    h.*,

    fac.Factor_Ajuste_Calculado,
    fac.Flag_Factor_Ajuste_Valido,
    fac.Flag_Usa_Ajuste,
    fac.Estado_Calculo AS Estado_Factor_Ajuste_Camiones,
    fac.Regla_Aplicacion AS Regla_Factor_Ajuste_Camiones,

    COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS Factor_Ajuste_Camiones_Usado,

    /* TMH ajustado por torre y turno */
    h.TMH_CV008_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV008_A_Factor,

    h.TMH_CV008_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV008_B_Factor,

    h.TMH_CV108_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV108_A_Factor,

    h.TMH_CV108_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV108_B_Factor,

    /* Totales ajustados */
    h.TMH_Apilado_Total_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_A_Factor,

    h.TMH_Apilado_Total_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_B_Factor,

    h.TMH_Apilado_Total_Dia
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_Dia_Factor

INTO #base_tms
FROM #humedad_resuelta AS h
LEFT JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test AS fac
    ON fac.Fecha = h.Fecha;

CREATE CLUSTERED INDEX IX_base_tms
    ON #base_tms (Fecha);

SELECT
    x.*,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A
           + x.TMS_TM2_Con_Sal_SRR_A
    END AS TMS_Total_Con_Sal_SRR_A,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_B
           + x.TMS_TM2_Con_Sal_SRR_B
    END AS TMS_Total_Con_Sal_SRR_B,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A
           + x.TMS_TM1_Con_Sal_SRR_B
           + x.TMS_TM2_Con_Sal_SRR_A
           + x.TMS_TM2_Con_Sal_SRR_B
    END AS TMS_Total_Con_Sal_SRR_Dia

INTO #tms_con_sal
FROM
(
    SELECT
        b.*,

        CASE
            WHEN b.TMH_CV008_A_Factor = 0 THEN 0
            WHEN b.Humedad_TM1_A IS NULL THEN NULL
            ELSE b.TMH_CV008_A_Factor
                 * (1.0 - b.Humedad_TM1_A / 100.0)
        END AS TMS_TM1_Con_Sal_SRR_A,

        CASE
            WHEN b.TMH_CV008_B_Factor = 0 THEN 0
            WHEN b.Humedad_TM1_B IS NULL THEN NULL
            ELSE b.TMH_CV008_B_Factor
                 * (1.0 - b.Humedad_TM1_B / 100.0)
        END AS TMS_TM1_Con_Sal_SRR_B,

        CASE
            WHEN b.TMH_CV108_A_Factor = 0 THEN 0
            WHEN b.Humedad_TM2_A IS NULL THEN NULL
            ELSE b.TMH_CV108_A_Factor
                 * (1.0 - b.Humedad_TM2_A / 100.0)
        END AS TMS_TM2_Con_Sal_SRR_A,

        CASE
            WHEN b.TMH_CV108_B_Factor = 0 THEN 0
            WHEN b.Humedad_TM2_B IS NULL THEN NULL
            ELSE b.TMH_CV108_B_Factor
                 * (1.0 - b.Humedad_TM2_B / 100.0)
        END AS TMS_TM2_Con_Sal_SRR_B,

        CASE
            WHEN b.TMH_Apilado_Total_Dia_Factor = 0
                THEN 0

            WHEN b.TMH_CV008_A_Factor > 0
             AND b.Humedad_TM1_A IS NULL
                THEN NULL

            WHEN b.TMH_CV008_B_Factor > 0
             AND b.Humedad_TM1_B IS NULL
                THEN NULL

            WHEN b.TMH_CV108_A_Factor > 0
             AND b.Humedad_TM2_A IS NULL
                THEN NULL

            WHEN b.TMH_CV108_B_Factor > 0
             AND b.Humedad_TM2_B IS NULL
                THEN NULL

            ELSE
                (
                    b.TMH_CV008_A_Factor * b.Humedad_TM1_A
                  + b.TMH_CV008_B_Factor * b.Humedad_TM1_B
                  + b.TMH_CV108_A_Factor * b.Humedad_TM2_A
                  + b.TMH_CV108_B_Factor * b.Humedad_TM2_B
                )
                /
                NULLIF(b.TMH_Apilado_Total_Dia_Factor, 0)
        END AS Humedad_Equivalente_Dia

    FROM #base_tms AS b
) AS x;

CREATE CLUSTERED INDEX IX_tms_con_sal
    ON #tms_con_sal (Fecha);

/* ============================================================
   BLOQUE 8: SAL AJUSTADA + DESCUENTO DE SAL
   ============================================================ */

DROP TABLE IF EXISTS #sal_ajustada;
DROP TABLE IF EXISTS #tms_sin_sal;

SELECT
    v.Fecha,
    v.Sal_Pesometros_TA,
    v.Sal_Pesometros_TB,
    v.Sal_Pesometros_Dia,
    v.Sal_Topografia_Dia,
    v.Flag_Sal_Basica_Valida,
    v.Flag_Sal_Ajuste_Valido,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia
               * ISNULL(v.Sal_Pesometros_TA, 0)
               / NULLIF(v.Sal_Pesometros_Dia, 0)

        ELSE ISNULL(v.Sal_Ajustada_TA, 0)
    END AS Sal_Ajustada_TA,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia
               * ISNULL(v.Sal_Pesometros_TB, 0)
               / NULLIF(v.Sal_Pesometros_Dia, 0)

        ELSE ISNULL(v.Sal_Ajustada_TB, 0)
    END AS Sal_Ajustada_TB,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia

        ELSE ISNULL(v.Sal_Ajustada_Dia, 0)
    END AS Sal_Ajustada_Dia

INTO #sal_ajustada
FROM inventar_SpcHidr.v_sal_ajustada v
WHERE v.Fecha >= @fecha_inicio
  AND v.Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_sal_ajustada
ON #sal_ajustada (Fecha);


SELECT
    t.*,

    s.Sal_Pesometros_TA,
    s.Sal_Pesometros_TB,
    s.Sal_Pesometros_Dia,
    s.Sal_Topografia_Dia,

    s.Flag_Sal_Basica_Valida,
    s.Flag_Sal_Ajuste_Valido,

    s.Sal_Ajustada_TA,
    s.Sal_Ajustada_TB,
    s.Sal_Ajustada_Dia,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_A = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TA, 0)
             * t.TMS_TM1_Con_Sal_SRR_A
             / NULLIF(t.TMS_Total_Con_Sal_SRR_A, 0)
    END AS Sal_Asignada_TM1_A,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_A = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TA, 0)
             * t.TMS_TM2_Con_Sal_SRR_A
             / NULLIF(t.TMS_Total_Con_Sal_SRR_A, 0)
    END AS Sal_Asignada_TM2_A,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_B = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TB, 0)
             * t.TMS_TM1_Con_Sal_SRR_B
             / NULLIF(t.TMS_Total_Con_Sal_SRR_B, 0)
    END AS Sal_Asignada_TM1_B,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_B = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TB, 0)
             * t.TMS_TM2_Con_Sal_SRR_B
             / NULLIF(t.TMS_Total_Con_Sal_SRR_B, 0)
    END AS Sal_Asignada_TM2_B

INTO #tms_sin_sal
FROM #tms_con_sal t
LEFT JOIN #sal_ajustada s
    ON s.Fecha = t.Fecha;

CREATE CLUSTERED INDEX IX_tms_sin_sal
ON #tms_sin_sal (Fecha);
/* ============================================================
   BLOQUE 9: TMS SIN SAL EN FORMATO FECHA / TURNO / TM
   ============================================================ */

DROP TABLE IF EXISTS #tms_tm;

SELECT
    Fecha,
    Turno,
    TM,
    TMS
INTO #tms_tm
FROM (
    SELECT
        Fecha,
        'A' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Con_Sal_SRR_A - COALESCE(Sal_Asignada_TM1_A, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'A' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Con_Sal_SRR_A - COALESCE(Sal_Asignada_TM2_A, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Con_Sal_SRR_B - COALESCE(Sal_Asignada_TM1_B, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Con_Sal_SRR_B - COALESCE(Sal_Asignada_TM2_B, 0) AS TMS
    FROM #tms_sin_sal
) x;

CREATE CLUSTERED INDEX IX_tms_tm
ON #tms_tm (Fecha, Turno, TM);
/* ============================================================
   BLOQUE 10: LEYES BASE RESUELTAS POR FECHA / TURNO / TM
   ============================================================ */

DROP TABLE IF EXISTS #leyes_base;

DECLARE @fecha_inicio_leyes_arrastre date =
    DATEADD(DAY, -90, @fecha_inicio);

SELECT *
INTO #leyes_base
FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
WHERE Fecha >= @fecha_inicio_leyes_arrastre
  AND Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_leyes_base_fecha_turno_tm
ON #leyes_base (Fecha, Turno, TM);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_fes
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (FeS, Fuente_FeS);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_consh
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (ConsH, Fuente_ConsH);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_malla12
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (Malla_Menos_1_2, Fuente_Malla_Menos_1_2);
/* ============================================================
   BLOQUE 10A: RESOLUCIÓN CRONOLÓGICA DE FeS

   RN-067:
   - El orden operacional es Fecha + Turno A + Turno B.
   - El turno A puede completar el turno B.
   - El turno B no puede modificar retroactivamente el turno A.
   - El valor nuevo del turno B rige desde B hacia adelante.
   - TM2 puede completar TM1.
   - TM1 no puede completar TM2.
   ============================================================ */

DROP TABLE IF EXISTS #fes_candidatos_dia;
DROP TABLE IF EXISTS #fes_dia_resuelta;

/* ------------------------------------------------------------
   Eventos originales válidos de FeS.

   TORRE_OTRO_TURNO_MISMO_DIA no se considera evento original,
   porque puede contener una compartición bidireccional previa.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,
    b.FeS,
    b.Fuente_FeS AS Fuente_Origen

INTO #fes_candidatos_dia

FROM #leyes_base AS b

WHERE b.FeS IS NOT NULL
  AND b.Fuente_FeS IN
  (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );

CREATE CLUSTERED INDEX IX_fes_candidatos_dia
ON #fes_candidatos_dia
(
    Fecha,
    Turno_Origen,
    TM_Origen
);

/* ------------------------------------------------------------
   Resolver cada Fecha + Turno + TM utilizando únicamente
   información cronológicamente disponible.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    c.FeS AS FeS_Nuevo_Dia,
    c.TM_Origen,
    c.Turno_Origen,

    CASE
        WHEN c.FeS IS NULL
            THEN NULL

        WHEN c.Fecha_Origen < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        /* Misma TM y mismo turno */
        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA'

        /* A completa B en la misma TM */
        WHEN c.TM_Origen = b.TM
         AND b.Turno = 'B'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_QUIMICA_OTRO_TURNO'

        /* TM2 completa TM1 en el mismo turno */
        WHEN b.TM = 'TM1'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1'

        /* TM2-A completa TM1-B */
        WHEN b.TM = 'TM1'
         AND b.Turno = 'B'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = 'A'
            THEN
                'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1_OTRO_TURNO'

        ELSE NULL
    END AS Fuente_Nuevo_Dia

INTO #fes_dia_resuelta

FROM #leyes_base AS b

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha AS Fecha_Origen,
        x.Turno_Origen,
        x.TM_Origen,
        x.FeS,
        x.Fuente_Origen

    FROM #fes_candidatos_dia AS x

    WHERE
        /* Misma TM o compartición permitida TM2 → TM1 */
        (
            x.TM_Origen = b.TM

            OR
            (
                b.TM = 'TM1'
                AND x.TM_Origen = 'TM2'
            )
        )

        /* Restricción cronológica */
        AND
        (
            x.Fecha < b.Fecha

            OR
            (
                x.Fecha = b.Fecha

                AND
                CASE
                    WHEN x.Turno_Origen = 'A' THEN 1
                    WHEN x.Turno_Origen = 'B' THEN 2
                    ELSE 9
                END
                <=
                CASE
                    WHEN b.Turno = 'A' THEN 1
                    WHEN b.Turno = 'B' THEN 2
                    ELSE 9
                END
            )
        )

    ORDER BY
        x.Fecha DESC,

        /* B es posterior a A */
        CASE
            WHEN x.Turno_Origen = 'B' THEN 2
            WHEN x.Turno_Origen = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igualdad temporal, priorizar la propia TM */
        CASE
            WHEN x.TM_Origen = b.TM THEN 1

            WHEN b.TM = 'TM1'
             AND x.TM_Origen = 'TM2' THEN 2

            ELSE 9
        END,

        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 9
        END

) AS c;

CREATE CLUSTERED INDEX IX_fes_dia_resuelta
ON #fes_dia_resuelta
(
    TM,
    Turno,
    Fecha
);
/* ============================================================
   BLOQUE 11A: RESOLUCIÓN CRONOLÓGICA MALLA -1/2

   Regla:
   - El orden operacional es Fecha + turno A + turno B.
   - Una medición válida del turno A puede completar B.
   - Una medición del turno B no puede modificar A.
   - El valor nuevo del turno B rige desde B hacia adelante.
   - TM2 puede completar TM1.
   - TM1 no completa TM2.
   - Se excluyen comparticiones bidireccionales previamente
     generadas por TORRE_OTRO_TURNO_MISMO_DIA.
   ============================================================ */

DROP TABLE IF EXISTS #malla12_candidata_dia_tm;
DROP TABLE IF EXISTS #malla12_dia_resuelta;

/* ------------------------------------------------------------
   Eventos originales válidos
   ------------------------------------------------------------ */

SELECT
    b.Fecha AS Fecha_Origen,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,

    b.Malla_Menos_1_2,
    b.Fuente_Malla_Menos_1_2 AS Fuente_Origen

INTO #malla12_candidata_dia_tm

FROM #leyes_base AS b

WHERE b.Malla_Menos_1_2 IS NOT NULL
  AND b.Malla_Menos_1_2 <> 0
  AND b.Fuente_Malla_Menos_1_2 IN
  (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );


CREATE CLUSTERED INDEX IX_malla12_candidata_fecha_turno_tm
ON #malla12_candidata_dia_tm
(
    Fecha_Origen,
    Turno_Origen,
    TM_Origen
);


/* ------------------------------------------------------------
   Resolver cada Fecha + Turno + TM utilizando solamente
   información disponible hasta ese instante.
   ------------------------------------------------------------ */

;WITH base AS
(
    SELECT DISTINCT
        Fecha,
        Turno,
        TM
    FROM #leyes_base
)

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    c.Fecha_Origen,
    c.Turno_Origen,
    c.TM_Origen,

    c.Malla_Menos_1_2,
    c.Fuente_Origen,

    CASE
        WHEN c.Malla_Menos_1_2 IS NULL
            THEN NULL

        /* El dato proviene de una fecha anterior */
        WHEN c.Fecha_Origen < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        /* Misma TM y mismo turno */
        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_FISICA'

        /* El turno A completa B en la misma TM */
        WHEN c.TM_Origen = b.TM
         AND b.Turno = 'B'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_FISICA_OTRO_TURNO'

        /* TM2 completa TM1 en el mismo turno */
        WHEN b.TM = 'TM1'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_FISICA_COMPARTIDA'

        /* TM2-A completa TM1-B */
        WHEN b.TM = 'TM1'
         AND b.Turno = 'B'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_FISICA_COMPARTIDA_OTRO_TURNO'

        ELSE NULL
    END AS Fuente_Malla_Resuelta

INTO #malla12_dia_resuelta

FROM base AS b

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha_Origen,
        x.Turno_Origen,
        x.TM_Origen,
        x.Malla_Menos_1_2,
        x.Fuente_Origen

    FROM #malla12_candidata_dia_tm AS x

    WHERE
        /* Misma TM o completitud permitida TM2 → TM1 */
        (
            x.TM_Origen = b.TM

            OR
            (
                b.TM = 'TM1'
                AND x.TM_Origen = 'TM2'
            )
        )

        /* El evento no puede ocurrir después del turno objetivo */
        AND
        (
            x.Fecha_Origen < b.Fecha

            OR
            (
                x.Fecha_Origen = b.Fecha

                AND
                CASE
                    WHEN x.Turno_Origen = 'A' THEN 1
                    WHEN x.Turno_Origen = 'B' THEN 2
                    ELSE 9
                END
                <=
                CASE
                    WHEN b.Turno = 'A' THEN 1
                    WHEN b.Turno = 'B' THEN 2
                    ELSE 9
                END
            )
        )

    ORDER BY
        /* Evento cronológico más reciente */
        x.Fecha_Origen DESC,

        CASE
            WHEN x.Turno_Origen = 'B' THEN 2
            WHEN x.Turno_Origen = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igualdad temporal, priorizar la propia TM */
        CASE
            WHEN x.TM_Origen = b.TM
                THEN 1

            WHEN b.TM = 'TM1'
             AND x.TM_Origen = 'TM2'
                THEN 2

            ELSE 9
        END,

        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO'
                THEN 1

            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
                THEN 2

            ELSE 9
        END

) AS c;


CREATE CLUSTERED INDEX
    IX_malla12_dia_resuelta_fecha_turno_tm

ON #malla12_dia_resuelta
(
    Fecha,
    Turno,
    TM
);
/* ============================================================
   BLOQUE 11B: ARRASTRE ÚLTIMO VALOR VÁLIDO
   FeS, ConsH y Malla -1/2
   ============================================================ */

DROP TABLE IF EXISTS #leyes_v2;

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    b.CuT,
    b.Fuente_CuT,

    b.CuS,
    b.Fuente_CuS,

    b.CO3,
    b.Fuente_CO3,

    b.CuFe,
    b.Fuente_CuFe,

    b.FeT,
    b.Fuente_FeT,

   ult_fes.FeS_Nuevo_Dia AS FeS,

CASE
    WHEN ult_fes.FeS_Nuevo_Dia IS NULL
        THEN b.Fuente_FeS

    WHEN ult_fes.Fecha = b.Fecha
        THEN ult_fes.Fuente_Nuevo_Dia

    WHEN ult_fes.Fecha < b.Fecha
        THEN 'ARRASTRE_ULTIMO_VALIDO'

    ELSE b.Fuente_FeS
END AS Fuente_FeS,
/* ============================================================
   ConsH con resolución cronológica

   - A puede completar B.
   - B no puede modificar retroactivamente A.
   - TM2 puede completar TM1.
   - TM1 no completa TM2.
   ============================================================ */

CASE
    WHEN b.ConsH IS NOT NULL
     AND b.ConsH <> 0
     AND b.Fuente_ConsH <> 'NO_APLICA_MINA'

     /* Para A, TORRE_OTRO_TURNO significa que tomó el dato de B */
     AND NOT
     (
         b.Turno = 'A'
         AND b.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
     )
        THEN b.ConsH

    ELSE ult_consh.ConsH
END AS ConsH,

CASE
    /* Valor propio o completitud cronológicamente válida */
    WHEN b.ConsH IS NOT NULL
     AND b.ConsH <> 0
     AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
     AND NOT
     (
         b.Turno = 'A'
         AND b.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
     )
        THEN b.Fuente_ConsH

    WHEN ult_consh.ConsH IS NULL
        THEN b.Fuente_ConsH

    /* Valor de una fecha anterior */
    WHEN ult_consh.Fecha < b.Fecha
        THEN 'ARRASTRE_ULTIMO_VALIDO'

    /* Misma TM y mismo turno */
    WHEN ult_consh.Fecha = b.Fecha
     AND ult_consh.TM_Origen = b.TM
     AND ult_consh.Turno_Origen = b.Turno
        THEN ult_consh.Fuente_ConsH

    /* A completa B dentro de la misma TM */
    WHEN ult_consh.Fecha = b.Fecha
     AND ult_consh.TM_Origen = b.TM
     AND b.Turno = 'B'
     AND ult_consh.Turno_Origen = 'A'
        THEN 'TORRE_OTRO_TURNO_MISMO_DIA'

    /* TM2 completa TM1 */
    WHEN ult_consh.Fecha = b.Fecha
     AND b.TM = 'TM1'
     AND ult_consh.TM_Origen = 'TM2'
        THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1'

    ELSE 'ARRASTRE_ULTIMO_VALIDO'
END AS Fuente_ConsH,

   ult_malla.Malla_Menos_1_2
    AS Malla_Menos_1_2,

CASE
    WHEN ult_malla.Malla_Menos_1_2 IS NULL
        THEN b.Fuente_Malla_Menos_1_2

    ELSE ult_malla.Fuente_Malla_Resuelta

END AS Fuente_Malla_Menos_1_2,

    b.Malla_Menos_100,
    b.Fuente_Malla_Menos_100,

    b.CaolBeta,
    b.Fuente_CaolBeta

INTO #leyes_v2
FROM #leyes_base b

OUTER APPLY (
    SELECT TOP (1)
        x.Fecha,
        x.FeS_Nuevo_Dia,
        x.Fuente_Nuevo_Dia
    FROM #fes_dia_resuelta x
    WHERE x.TM = b.TM
      AND x.Turno = b.Turno
      AND x.Fecha <= b.Fecha
      AND x.FeS_Nuevo_Dia IS NOT NULL
    ORDER BY
        x.Fecha DESC
) ult_fes

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha,
        x.Turno AS Turno_Origen,
        x.TM AS TM_Origen,
        x.ConsH,
        x.Fuente_ConsH

    FROM #leyes_base AS x

    WHERE x.ConsH IS NOT NULL
      AND x.ConsH <> 0
      AND x.Fuente_ConsH <> 'NO_APLICA_MINA'

      /* Excluir los A que fueron poblados desde el B futuro */
      AND NOT
      (
          x.Turno = 'A'
          AND x.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
      )

      /* Misma TM o compartición permitida TM2 → TM1 */
      AND
      (
          x.TM = b.TM
          OR
          (
              b.TM = 'TM1'
              AND x.TM = 'TM2'
          )
      )

      /* Restricción cronológica:
         - Para objetivo A: solo A del mismo día.
         - Para objetivo B: A o B del mismo día.
         - Siempre se permiten fechas anteriores.
      */
      AND
      (
          x.Fecha < b.Fecha

          OR
          (
              x.Fecha = b.Fecha
              AND
              (
                  (b.Turno = 'A' AND x.Turno = 'A')
                  OR
                  (b.Turno = 'B' AND x.Turno IN ('A', 'B'))
              )
          )
      )

    ORDER BY
        x.Fecha DESC,

        /* B es posterior a A */
        CASE
            WHEN x.Turno = 'B' THEN 2
            WHEN x.Turno = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igual instante, priorizar la propia TM */
        CASE
            WHEN x.TM = b.TM THEN 1
            WHEN b.TM = 'TM1' AND x.TM = 'TM2' THEN 2
            ELSE 9
        END,

        /* Priorizar medición original */
        CASE
            WHEN x.Fuente_ConsH = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_ConsH = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 3
        END

) AS ult_consh
OUTER APPLY
(
    SELECT TOP (1)
        d.Fecha,
        d.Turno,
        d.TM,

        d.Fecha_Origen,
        d.Turno_Origen,
        d.TM_Origen,

        d.Malla_Menos_1_2,
        d.Fuente_Origen,
        d.Fuente_Malla_Resuelta

    FROM #malla12_dia_resuelta AS d

    WHERE d.TM = b.TM
      AND d.Turno = b.Turno
      AND d.Fecha <= b.Fecha
      AND d.Malla_Menos_1_2 IS NOT NULL

    ORDER BY
        d.Fecha DESC

) AS ult_malla;

CREATE CLUSTERED INDEX IX_leyes_v2_fecha_turno_tm
ON #leyes_v2 (Fecha, Turno, TM);

/* ============================================================
   BLOQUE 11C - Ajuste CuFe según regla oficial
   Si representatividad química > 0.75, usar Clays_CuFe.
   Si no cumple, mantener CuFe ya resuelto desde MINA/Conciliación.
   ============================================================ */

UPDATE l
SET
    l.CuFe = TRY_CAST(c.CuFe AS float),
    l.Fuente_CuFe = 'TORRE'
FROM #leyes_v2 l
INNER JOIN inventar_SpcHidr.representatividad_torres_resultado r
    ON r.Dia = l.Fecha
INNER JOIN inventar_SpcHidr.Clays_CuFe c
    ON c.Fecha = l.Fecha
   AND c.Turno = CASE
                    WHEN l.Turno = 'A' THEN 'TA'
                    WHEN l.Turno = 'B' THEN 'TB'
                 END
   AND c.Torre = CASE
                    WHEN l.TM = 'TM1' THEN 'TM-1'
                    WHEN l.TM = 'TM2' THEN 'TM-2'
                 END
CROSS APPLY (
    SELECT
        CASE
            WHEN l.TM = 'TM1' AND l.Turno = 'A' THEN r.TM1_TurnoA_Quimico
            WHEN l.TM = 'TM1' AND l.Turno = 'B' THEN r.TM1_TurnoB_Quimico
            WHEN l.TM = 'TM2' AND l.Turno = 'A' THEN r.TM2_TurnoA_Quimico
            WHEN l.TM = 'TM2' AND l.Turno = 'B' THEN r.TM2_TurnoB_Quimico
        END AS Rep_Quimica_Raw
) rep
CROSS APPLY (
    SELECT
        CASE
            WHEN rep.Rep_Quimica_Raw > 1
                THEN rep.Rep_Quimica_Raw / 100.0
            ELSE rep.Rep_Quimica_Raw
        END AS Rep_Quimica_Normalizada
) rep_norm
WHERE TRY_CAST(c.CuFe AS float) IS NOT NULL
  AND ISNULL(rep_norm.Rep_Quimica_Normalizada, 0) > 0.75;

  /* ============================================================
   BLOQUE 11C.1 - Completitud CuFe TM2 -> TM1

   Si TM2 tiene CuFe representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.

   Esta regla alinea CuFe con la completitud asimétrica ya aplicada
   para CuT, CuS, CO3 y FeT.
   ============================================================ */

UPDATE tm1
SET
    tm1.CuFe = tm2.CuFe,
    tm1.Fuente_CuFe = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuFe IS NOT NULL
  AND tm2.Fuente_CuFe LIKE '%TORRE%'
  AND (
        tm1.CuFe IS NULL
     OR ISNULL(tm1.Fuente_CuFe, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11D - Ajuste FeT según regla oficial

   Si TM2 tiene FeT representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.

   Esto evita ponderar TM1 MINA + TM2 TORRE cuando el oficial clasifica
   el turno como TM2 y usa el valor representativo de TM2.
   ============================================================ */

UPDATE tm1
SET
    tm1.FeT = tm2.FeT,
    tm1.Fuente_FeT = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.FeT IS NOT NULL
  AND tm2.Fuente_FeT LIKE '%TORRE%'
  AND (
        tm1.FeT IS NULL
     OR ISNULL(tm1.Fuente_FeT, '') NOT LIKE '%TORRE%'
  );

  /* ============================================================
   BLOQUE 11E - Ajuste CO3 según regla oficial

   Si TM2 tiene CO3 representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tm1
SET
    tm1.CO3 = tm2.CO3,
    tm1.Fuente_CO3 = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CO3 IS NOT NULL
  AND tm2.Fuente_CO3 LIKE '%TORRE%'
  AND (
        tm1.CO3 IS NULL
     OR ISNULL(tm1.Fuente_CO3, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11F - Ajuste CaolBeta según reporte oficial

   CaolBeta se toma desde Clays_CuFe cuando existe dato para
   Fecha + Turno + TM. No depende de Conciliación Chancado
   cuando existe dato NIR/Clays disponible.
   ============================================================ */

UPDATE l
SET
    l.CaolBeta = clay.CaolBeta_Clays,
    l.Fuente_CaolBeta = 'CLAYS'
FROM #leyes_v2 l
INNER JOIN inventar_SpcHidr.Clays_CuFe c
    ON c.Fecha = l.Fecha
   AND c.Turno = CASE
                    WHEN l.Turno = 'A' THEN 'TA'
                    WHEN l.Turno = 'B' THEN 'TB'
                 END
   AND c.Torre = CASE
                    WHEN l.TM = 'TM1' THEN 'TM-1'
                    WHEN l.TM = 'TM2' THEN 'TM-2'
                 END
OUTER APPLY (
    SELECT
        TRY_CONVERT(float, REPLACE(CONVERT(varchar(50), c.CaolBeta), ',', '.')) AS CaolBeta_Clays
) clay
WHERE clay.CaolBeta_Clays IS NOT NULL;

/* ============================================================
   BLOQUE 11G - Ajuste CuT según regla oficial

   Si TM2 tiene CuT representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tm1
SET
    tm1.CuT = tm2.CuT,
    tm1.Fuente_CuT = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuT IS NOT NULL
  AND tm2.Fuente_CuT LIKE '%TORRE%'
  AND (
        tm1.CuT IS NULL
     OR ISNULL(tm1.Fuente_CuT, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11H - Ajuste CuS según regla oficial

   Si TM2 tiene CuS representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tm1
SET
    tm1.CuS = tm2.CuS,
    tm1.Fuente_CuS = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuS IS NOT NULL
  AND tm2.Fuente_CuS LIKE '%TORRE%'
  AND (
        tm1.CuS IS NULL
     OR ISNULL(tm1.Fuente_CuS, '') NOT LIKE '%TORRE%'
  );
/* ============================================================
   BLOQUE 11I - Guarda de evaluabilidad por origen operacional

   RN-064 ampliada:
   - El TMS siempre proviene de CV008/CV108.
   - STOCK, MINA y SRR constituyen evidencia oficial.
   - IMP positivo constituye evidencia operacional provisional.
   - IMP no reemplaza ni distribuye el TMS.
   - Si CV008/CV108 entregan TMS cero, IMP no habilita tonelaje.
   ============================================================ */

UPDATE t
SET
    t.TMS = 0
FROM #tms_tm AS t

LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr AS o
    ON o.Fecha = t.Fecha
   AND o.Turno = t.Turno

LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS c
    ON c.Fecha = t.Fecha
   AND c.Turno = t.Turno

WHERE ISNULL(t.TMS, 0) > 0

  /* No existe evidencia operacional oficial */
  AND ISNULL(o.Ton_Stock_Camiones, 0) = 0
  AND ISNULL(o.Ton_Mina_Camiones, 0) = 0
  AND ISNULL(o.Ton_SRR, 0) = 0

  /* Tampoco existe evidencia provisional IMP */
  AND NOT
  (
      UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato, '')))) = 'IMP'
      AND ISNULL(c.Ton, 0) > 0
  );

/* ============================================================
   BLOQUE 12: PONDERACIÓN DE LEYES REALES POR TMS
   ============================================================ */

DROP TABLE IF EXISTS #reales;

SELECT
    t.Fecha,
    t.Turno,

    SUM(t.TMS) AS Apilado_TMS_Real,

    SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuT_Real,

    SUM(t.TMS * l.CuS) / NULLIF(SUM(CASE WHEN l.CuS IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuS_Real,

    CASE
        WHEN SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) IS NULL
          OR SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) = 0
        THEN NULL
        ELSE
            (
                SUM(t.TMS * l.CuS) / NULLIF(SUM(CASE WHEN l.CuS IS NOT NULL THEN t.TMS ELSE 0 END), 0)
            )
            /
            (
                SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0)
            )
    END AS Solubilidad_Real,

    SUM(t.TMS * l.CO3) / NULLIF(SUM(CASE WHEN l.CO3 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CO3_Real,

    SUM(t.TMS * l.CuFe) / NULLIF(SUM(CASE WHEN l.CuFe IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuFe_Real,

    SUM(t.TMS * l.FeT) / NULLIF(SUM(CASE WHEN l.FeT IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS FeT_Real,

    SUM(t.TMS * l.FeS) / NULLIF(SUM(CASE WHEN l.FeS IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS FeS_Real,

    SUM(t.TMS * l.ConsH) / NULLIF(SUM(CASE WHEN l.ConsH IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS ConsH_Real,

    SUM(t.TMS * l.Malla_Menos_1_2) / NULLIF(SUM(CASE WHEN l.Malla_Menos_1_2 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS Malla_Menos_1_2_Real,

    SUM(t.TMS * l.Malla_Menos_100) / NULLIF(SUM(CASE WHEN l.Malla_Menos_100 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS Malla_Menos_100_Real,

    SUM(t.TMS * l.CaolBeta) / NULLIF(SUM(CASE WHEN l.CaolBeta IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CaolBeta_Real

INTO #reales
FROM #tms_tm t
LEFT JOIN #leyes_v2 l
    ON l.Fecha = t.Fecha
   AND l.Turno = t.Turno
   AND l.TM = t.TM
GROUP BY
    t.Fecha,
    t.Turno;

CREATE CLUSTERED INDEX IX_reales_fecha_turno
ON #reales (Fecha, Turno);

/* ============================================================
   BLOQUE 13: CLASIFICACIÓN DE MUESTRA QUÍMICA Y FÍSICA

   Ajuste:
   - Se incorpora IMP como fuente válida de conciliación.
   - No se modifica la prioridad de TORRE, MINA, ARRASTRE
     ni SEMILLA.
   ============================================================ */

DROP TABLE IF EXISTS #muestras;

WITH fuentes AS
(
    SELECT
        Fecha,
        Turno,

        /* ----------------------------------------------------
           Fuentes químicas
           ---------------------------------------------------- */

        MAX
        (
            CASE
                WHEN Fuente_CuT  LIKE '%TORRE%'
                  OR Fuente_CuS  LIKE '%TORRE%'
                  OR Fuente_CO3  LIKE '%TORRE%'
                  OR Fuente_CuFe LIKE '%TORRE%'
                  OR Fuente_FeT  LIKE '%TORRE%'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Torre,

        MAX
        (
            CASE
                WHEN Fuente_CuT  = 'MINA'
                  OR Fuente_CuS  = 'MINA'
                  OR Fuente_CO3  = 'MINA'
                  OR Fuente_CuFe = 'MINA'
                  OR Fuente_FeT  = 'MINA'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Mina,

        /* Nueva clasificación IMP */
        MAX
        (
            CASE
                WHEN Fuente_CuT  = 'IMP'
                  OR Fuente_CuS  = 'IMP'
                  OR Fuente_CO3  = 'IMP'
                  OR Fuente_CuFe = 'IMP'
                  OR Fuente_FeT  = 'IMP'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_IMP,

        MAX
        (
            CASE
                WHEN Fuente_FeS  = 'ARRASTRE_ULTIMO_VALIDO'
                  OR Fuente_ConsH = 'ARRASTRE_ULTIMO_VALIDO'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Arrastre,

        MAX
        (
            CASE
                WHEN Fuente_CuT   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CuS   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CO3   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CuFe  = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_FeT   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_FeS   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_ConsH = 'SEMILLA_INICIO_PERIODO'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Semilla,

        /* ----------------------------------------------------
           Fuentes físicas
           ---------------------------------------------------- */

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                  OR Fuente_Malla_Menos_100 LIKE '%TORRE%'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Torre,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'MINA'
                  OR Fuente_Malla_Menos_100 = 'MINA'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Mina,

        /* Nueva clasificación IMP */
        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'IMP'
                  OR Fuente_Malla_Menos_100 = 'IMP'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_IMP,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'ARRASTRE_ULTIMO_VALIDO'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Arrastre,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_Malla_Menos_100 = 'SEMILLA_INICIO_PERIODO'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Semilla

    FROM #leyes_v2

    GROUP BY
        Fecha,
        Turno
)

SELECT
    Fecha,
    Turno,

    CASE
        WHEN Quimica_Semilla = 1
            THEN 'SEMILLA'

        WHEN Quimica_Arrastre = 1
         AND
         (
             Quimica_Torre = 1
             OR Quimica_Mina = 1
             OR Quimica_IMP = 1
         )
            THEN 'MIXTA'

        WHEN Quimica_Torre + Quimica_Mina + Quimica_IMP >= 2
            THEN 'MIXTA'

        WHEN Quimica_Arrastre = 1
            THEN 'ARRASTRE'

        WHEN Quimica_Torre = 1
            THEN 'TORRE'

        WHEN Quimica_IMP = 1
            THEN 'IMP'

        WHEN Quimica_Mina = 1
            THEN 'MINA'

        ELSE NULL
    END AS Muestra_Quimica,

    CASE
        WHEN Fisica_Semilla = 1
            THEN 'SEMILLA'

        WHEN Fisica_Arrastre = 1
         AND
         (
             Fisica_Torre = 1
             OR Fisica_Mina = 1
             OR Fisica_IMP = 1
         )
            THEN 'MIXTA'

        WHEN Fisica_Torre + Fisica_Mina + Fisica_IMP >= 2
            THEN 'MIXTA'

        WHEN Fisica_Arrastre = 1
            THEN 'ARRASTRE'

        WHEN Fisica_Torre = 1
            THEN 'TORRE'

        WHEN Fisica_IMP = 1
            THEN 'IMP'

        WHEN Fisica_Mina = 1
            THEN 'MINA'

        ELSE NULL
    END AS Muestra_Fisica

INTO #muestras

FROM fuentes;

CREATE CLUSTERED INDEX IX_muestras_fecha_turno
ON #muestras (Fecha, Turno);
/* ============================================================
   BLOQUE 14: CAMPAÑA, MÓDULO, AVANCE Y PLAN
   ============================================================ */

DROP TABLE IF EXISTS #campania_modulo;
DROP TABLE IF EXISTS #plan_mensual;
DROP TABLE IF EXISTS #plan_semanal;
DROP TABLE IF EXISTS #origen_apilado;

SELECT
    Fecha,
    Fecha_Origen_Relleno,
    Fecha_Topografia_Usada,
    Campania,
    Material,
    Modulo,
    Avance,
    Volumen_Diario_Modulo_m3,
    Fuente_Campania_Modulo
INTO #campania_modulo
FROM inventar_SpcHidr.v_reporte_turno_campania_modulo_test
WHERE Fecha >= @fecha_inicio
  AND Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_campania_modulo
ON #campania_modulo (Fecha);


/* ============================================================
   PLAN MENSUAL
   ============================================================ */

SELECT
    fecha AS Fecha,
    apilamiento AS Apilado_TMS_Plan_Mensual,
    cut AS CuT_Plan_Mensual,
    cus AS CuS_Plan_Mensual,
    CAST(
    CASE
        WHEN cut IS NULL OR cut = 0 OR cus IS NULL THEN NULL
        ELSE cus / cut
    END
    AS decimal(18, 6)) AS Solubilidad_Plan_Mensual,
    co3 AS CO3_Plan_Mensual,
    cl_acido AS ConsH_Plan_Mensual,
    cufe AS CuFe_Plan_Mensual,
    malla_100 AS Malla_Menos_100_Plan_Mensual,
    caol_beta AS CaolBeta_Plan_Mensual
INTO #plan_mensual
FROM inventar_SpcHidr.plan_mensual_reporte_turno
WHERE fecha >= @fecha_inicio
  AND fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_plan_mensual
ON #plan_mensual (Fecha);


/* ============================================================
   PLAN SEMANAL
   ============================================================ */

SELECT
    fecha AS Fecha,
    ton AS Apilado_TMS_Plan_Semanal,
    cut AS CuT_Plan_Semanal,
    cus AS CuS_Plan_Semanal,
    CAST(
    CASE
        WHEN cut IS NULL OR cut = 0 OR cus IS NULL THEN NULL
        ELSE cus / cut
    END
    AS decimal(18, 6)) AS Solubilidad_Plan_Semanal,
    co3 AS CO3_Plan_Semanal,
    cl_acido AS ConsH_Plan_Semanal,
    cufe AS CuFe_Plan_Semanal,
    malla_100 AS Malla_Menos_100_Plan_Semanal,
    betaclay AS CaolBeta_Plan_Semanal,
    porc_1_2 AS Malla_Menos_1_2_Plan_Semanal,
    arcillas AS Arcillas_Plan_Semanal,
    cuarzo AS Cuarzo_Plan_Semanal
INTO #plan_semanal
FROM inventar_SpcHidr.plan_semanal_reporte_turno
WHERE fecha >= @fecha_inicio
  AND fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_plan_semanal
ON #plan_semanal (Fecha);


 /* ============================================================
   BLOQUE 15: DISTRIBUCIÓN FINAL STOCK / MINA / SRR

   Prioridad:
   1. Origen oficial desde mov_cam.
   2. IMP provisional:
      - SRR = Es_SRR = 1
      - Camiones = STOCK
      - MINA = 0
   3. Sin origen: proporciones en cero.

   IMPORTANTE:
   IMP no reemplaza Apilado_TMS_Real.
   Solo determina las proporciones de origen.
   ============================================================ */

DROP TABLE IF EXISTS #imp_origen_turno;
DROP TABLE IF EXISTS #origen_apilado;


/* ------------------------------------------------------------
   15A. Consolidación IMP por Fecha + Turno
   ------------------------------------------------------------ */

SELECT
    CAST(i.Fecha AS date) AS Fecha,

    CASE
        WHEN i.Turno IN ('TA', 'A') THEN 'A'
        WHEN i.Turno IN ('TB', 'B') THEN 'B'
        ELSE i.Turno
    END COLLATE DATABASE_DEFAULT AS Turno,

    CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 1
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_SRR,

    CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 0
                 AND UPPER(LTRIM(RTRIM(ISNULL(i.Tipo_Registro, ''))))
                     = 'CAMION'
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_Camiones,
		
		  CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 0
                 AND UPPER(LTRIM(RTRIM(ISNULL(i.Tipo_Registro, ''))))
                     = 'MINA'
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_mina,

    CAST
    (
        SUM(ISNULL(i.Ton, 0))
        AS decimal(38,10)
    ) AS Ton_IMP_Total

INTO #imp_origen_turno

FROM PROD_SIIR.hidro.v_imp_chancado_normalizado AS i

WHERE i.Fecha >= @fecha_inicio
  AND i.Fecha <  @fecha_fin
  AND ISNULL(i.Ton, 0) > 0

GROUP BY
    CAST(i.Fecha AS date),

    CASE
        WHEN i.Turno IN ('TA', 'A') THEN 'A'
        WHEN i.Turno IN ('TB', 'B') THEN 'B'
        ELSE i.Turno
    END COLLATE DATABASE_DEFAULT;


CREATE CLUSTERED INDEX IX_imp_origen_turno
ON #imp_origen_turno (Fecha, Turno);


/* ------------------------------------------------------------
   15B. Determinación de la fuente de origen
   ------------------------------------------------------------ */

;WITH origen_base AS
(
    SELECT
        r.Fecha,
        r.Turno,

        CAST
        (
            ISNULL(r.Apilado_TMS_Real, 0)
            AS decimal(38,10)
        ) AS Apilado_TMS_Real,

        /* Fuente oficial */

        CAST
        (
            ISNULL(p.Ton_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Stock_Oficial,

        CAST
        (
            ISNULL(p.Ton_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Mina_Oficial,

        CAST
        (
            ISNULL(p.Ton_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_SRR_Oficial,

        CAST
        (
            ISNULL(p.Prop_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Prop_Stock_Oficial,

        CAST
        (
            ISNULL(p.Prop_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Prop_Mina_Oficial,

        /* Fuente IMP */

        CAST
        (
            ISNULL(i.Ton_IMP_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_SRR,

        CAST
        (
            ISNULL(i.Ton_IMP_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Camiones,
				
				CAST
        (
            ISNULL(i.Ton_IMP_mina, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_mina,

        CAST
        (
            ISNULL(i.Ton_IMP_Total, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Total,

        c.Fuente_Dato,

        CASE
            /* Prioridad 1: origen oficial positivo */

            WHEN ISNULL(p.Ton_Stock_Camiones, 0) > 0
              OR ISNULL(p.Ton_Mina_Camiones, 0) > 0
              OR ISNULL(p.Ton_SRR, 0) > 0
                THEN 'OFICIAL'

            /* Prioridad 2: respaldo provisional IMP */

            WHEN UPPER
                 (
                     LTRIM
                     (
                         RTRIM
                         (
                             ISNULL(c.Fuente_Dato, '')
                         )
                     )
                 ) = 'IMP'
             AND ISNULL(i.Ton_IMP_Total, 0) > 0
                THEN 'IMP'

            ELSE 'SIN_ORIGEN'
        END AS Fuente_Origen

    FROM #reales AS r

    LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr AS p
        ON p.Fecha = r.Fecha
       AND p.Turno = r.Turno

    LEFT JOIN #imp_origen_turno AS i
        ON i.Fecha = r.Fecha
       AND i.Turno = r.Turno

    LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS c
        ON c.Fecha = r.Fecha
       AND c.Turno = r.Turno
),

origen_srr AS
(
    SELECT
        b.*,

        /* SRR limitado al Apilado_TMS_Real */

        CAST
        (
            CASE
                WHEN b.Apilado_TMS_Real <= 0
                    THEN 0

                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN
                        CASE
                            WHEN b.Ton_SRR_Oficial <= 0
                                THEN 0

                            WHEN b.Ton_SRR_Oficial
                               > b.Apilado_TMS_Real
                                THEN b.Apilado_TMS_Real

                            ELSE b.Ton_SRR_Oficial
                        END

                WHEN b.Fuente_Origen = 'IMP'
                    THEN
                        CASE
                            WHEN b.Ton_IMP_SRR <= 0
                                THEN 0

                            WHEN b.Ton_IMP_SRR
                               > b.Apilado_TMS_Real
                                THEN b.Apilado_TMS_Real

                            ELSE b.Ton_IMP_SRR
                        END

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Ton_SRR_Usado,

        /* Proporción de camiones STOCK */

        CAST
        (
            CASE
                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN b.Prop_Stock_Oficial

                WHEN b.Fuente_Origen = 'IMP'
                 AND b.Ton_IMP_Camiones > 0
                    THEN (b.Ton_IMP_Camiones/(b.Ton_IMP_Total-b.Ton_IMP_SRR))

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Prop_Stock_Camiones_Usada,

        /* Proporción de camiones MINA */

        CAST
        (
            CASE
                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN b.Prop_Mina_Oficial

                WHEN b.Fuente_Origen = 'IMP'
                    AND b.Ton_IMP_mina > 0
                    THEN (b.Ton_IMP_mina/(b.Ton_IMP_Total-b.Ton_IMP_SRR))

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Prop_Mina_Camiones_Usada

    FROM origen_base AS b
),

origen_calculado AS
(
    SELECT
        s.*,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
                   
									((s.Apilado_TMS_Real- s.Ton_SRR_Usado)*
										s.Prop_Stock_Camiones_Usada)/s.Apilado_TMS_Real
                    
            END
            AS decimal(18,8)
        ) AS Prop_Final_Stock,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
								((s.Apilado_TMS_Real- s.Ton_SRR_Usado)*
										s.Prop_Mina_Camiones_Usada)/s.Apilado_TMS_Real
                     
                  
            END
            AS decimal(18,8)
        ) AS Prop_Final_Mina,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
                    s.Ton_SRR_Usado
                    / NULLIF(s.Apilado_TMS_Real, 0)
            END
            AS decimal(18,8)
        ) AS Prop_Final_SRR

    FROM origen_srr AS s
)

SELECT
    o.Fecha,
    o.Turno,

    o.Prop_Final_Stock,
    o.Prop_Final_Mina,
    o.Prop_Final_SRR,

    CAST
    (
        o.Prop_Final_Stock
      + o.Prop_Final_Mina
      + o.Prop_Final_SRR
        AS decimal(18,8)
    ) AS Prop_Final_Total,

    /* Diferencia de tonelaje contra TMS real */

    CAST
    (
        (
            (
                o.Apilado_TMS_Real
              - o.Ton_SRR_Usado
            )
            * o.Prop_Stock_Camiones_Usada
        )
      + (
            (
                o.Apilado_TMS_Real
              - o.Ton_SRR_Usado
            )
            * o.Prop_Mina_Camiones_Usada
        )
      + o.Ton_SRR_Usado
      - o.Apilado_TMS_Real

        AS decimal(18,8)
    ) AS Check_Distribucion_Apilado,

    /* Columnas de auditoría */

    o.Fuente_Origen,
    o.Ton_SRR_Usado,
    o.Ton_IMP_SRR,
    o.Ton_IMP_Camiones,
    o.Ton_Stock_Oficial,
    o.Ton_Mina_Oficial,
    o.Ton_SRR_Oficial

INTO #origen_apilado

FROM origen_calculado AS o;


CREATE CLUSTERED INDEX IX_origen_apilado
ON #origen_apilado (Fecha, Turno);

/* ============================================================
   SELECT FINAL - ORDEN FORMATO BHP
   ============================================================ */

SELECT
    r.Fecha,
    cm.Campania,
    cm.Material,
    cm.Modulo,
    cm.Avance,
    r.Turno,

    /* Apilado */
    r.Apilado_TMS_Real,
    pm.Apilado_TMS_Plan_Mensual,

    /* Distribución de origen */
    CAST(100.0 * COALESCE(oa.Prop_Final_Stock, 0) AS decimal(18, 2)) AS STOCK,
    CAST(100.0 * COALESCE(oa.Prop_Final_Mina, 0) AS decimal(18, 2)) AS MINA,
    CAST(100.0 * COALESCE(oa.Prop_Final_SRR, 0) AS decimal(18, 2)) AS SRR,

    /* Análisis químicos */
    r.CuT_Real,
    pm.CuT_Plan_Mensual,
    ps.CuT_Plan_Semanal,

    r.CuS_Real,
    pm.CuS_Plan_Mensual,
    ps.CuS_Plan_Semanal,

    r.Solubilidad_Real,
    pm.Solubilidad_Plan_Mensual,
    ps.Solubilidad_Plan_Semanal,

    r.CO3_Real,
    pm.CO3_Plan_Mensual,
    ps.CO3_Plan_Semanal,

    r.CuFe_Real,
    pm.CuFe_Plan_Mensual,
    ps.CuFe_Plan_Semanal,

    r.FeT_Real,
    r.FeS_Real,

    /* Dosis / consumo ácido */
    r.ConsH_Real,
  
    /* Granulometrías */
    r.Malla_Menos_1_2_Real,
    ps.Malla_Menos_1_2_Plan_Semanal,

    r.Malla_Menos_100_Real,
    pm.Malla_Menos_100_Plan_Mensual,
    ps.Malla_Menos_100_Plan_Semanal,

 /* NIR */
r.CaolBeta_Real,
pm.CaolBeta_Plan_Mensual,
ps.CaolBeta_Plan_Semanal,

/* Dosis de ácido */
CAST(
    ROUND(
        CASE
            WHEN ISNULL(r.Solubilidad_Real, 0) < 0.25 THEN
                CASE
                    WHEN ISNULL(r.CO3_Real, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(r.CO3_Real, 0))
                END

            ELSE
                CASE
                    WHEN r.CuS_Real IS NULL OR r.CuS_Real <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(r.CuS_Real))
                               + 18.99
                               + (15.51 * ISNULL(r.CO3_Real, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(r.CuS_Real))
                               + 18.99
                               + (15.51 * ISNULL(r.CO3_Real, 0))
                        END
                END
        END
    , 2)
AS decimal(18, 2)) AS Dosis_Acido_Ideal_TM,

CAST(
    ROUND(
        CASE
            WHEN ISNULL(ps.Solubilidad_Plan_Semanal, 0) < 0.25 THEN
                CASE
                    WHEN ISNULL(ps.CO3_Plan_Semanal, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0))
                END

            ELSE
                CASE
                    WHEN ps.CuS_Plan_Semanal IS NULL OR ps.CuS_Plan_Semanal <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(ps.CuS_Plan_Semanal))
                               + 18.99
                               + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(ps.CuS_Plan_Semanal))
                               + 18.99
                               + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0))
                        END
                END
        END
    , 2)
AS decimal(18, 2)) AS Dosis_Acido_Programa_Semanal,

        /* Fuentes de información explícitas */
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN '-'
        ELSE COALESCE(fi.Fuente_Info_Quimica, '-')
    END AS Fuente_Info_Quimica,

    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN '-'
        ELSE COALESCE(fi.Fuente_Info_Fisica, '-')
    END AS Fuente_Info_Fisica,

    /* Clasificación técnica original */
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN NULL
        ELSE m.Muestra_Quimica
    END AS Muestra_Quimica,

    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN NULL
        ELSE m.Muestra_Fisica
    END AS Muestra_Fisica

FROM #reales r

LEFT JOIN #muestras m
    ON m.Fecha = r.Fecha
   AND m.Turno = r.Turno

LEFT JOIN inventar_SpcHidr.v_reporte_turno_fuentes_info_test fi
    ON fi.Fecha = r.Fecha
   AND fi.Turno = r.Turno

LEFT JOIN #campania_modulo cm
    ON cm.Fecha = r.Fecha

LEFT JOIN #origen_apilado oa
    ON oa.Fecha = r.Fecha
   AND oa.Turno = r.Turno

LEFT JOIN #plan_mensual pm
    ON pm.Fecha = r.Fecha

LEFT JOIN #plan_semanal ps
    ON ps.Fecha = r.Fecha

ORDER BY
    r.Fecha,
    r.Turno;
END;
GO
