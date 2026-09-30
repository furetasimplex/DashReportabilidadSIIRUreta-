/*
================================================================================
  PROCEDIMIENTO : inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_test
  DESCRIPCION   : Calcula y persiste el factor de ajuste diario (metodologia
                  del Excel "Datos Conciliados Agosto 2025_RevPI SRR.xlsm",
                  hojas Camiones1/Camiones2) en la tabla
                  Control_Factor_Ajuste_Camiones. SP independiente, mismo
                  patron @FechaInicio/@FechaFin/@DiasReproceso que
                  sp_refrescar_historico_apilado_test y
                  sp_refrescar_historico_srr_test. Se llama DESDE la copia
                  sp_mantiene_datos_conciliados_of_v2_ajustado_test, no
                  vive embebido en ella (decision confirmada).

  FUENTES:
      #ViajesCamiones  -> mov_cam, filtro Destino = 'CH01', agrupado por
                          Fecha y Flota_CEX, Num_Viajes = SUM(N_BREAK)
                          (NO es COUNT(*): N_BREAK ya es el numero de
                          viajes/quiebres de esa fila). Query confirmada
                          por el usuario y verificada contra el archivo
                          mov_cam_tipo camion_20260707.csv. Filas con
                          Flota_CEX distinto de KOM/CAT (ej. 'nan',
                          camiones sin clasificar) se acumulan aparte en
                          Otros_Num_Viajes, no se descartan en silencio.
      Historico_Apilado_Diario -> Apilado_TMH_promedio_dia, Sal_promedio_dia,
                          Humedad_promedio_dia
      Historico_SRR_Diario     -> TMH_CV001_Dia (SRR en TMH, CV001 corregido)

  CONSTANTES PROVISIONALES (fijas, confirmado por el usuario):
      357 TMH/viaje KOM , 236 TMH/viaje CAT
      Limite factor de carga: 380 KOM , 265 CAT

  HISTORIAL:
      v1.0 - Version inicial. Bloqueada por @ConfirmarFuenteCamiones hasta
             confirmar la fuente real de segregacion de camiones por flota.
      v1.1 - Fuente confirmada: mov_cam (Fecha, Flota_CEX, N_BREAK,
             Destino = 'CH01'). Reemplazado el bloque #ViajesCamiones por
             la query real (agregada por Flota_CEX, pivoteada a
             KOM_Num_Viajes/CAT_Num_Viajes/Otros_Num_Viajes) y removido el
             candado @ConfirmarFuenteCamiones.
================================================================================
*/
CREATE   PROCEDURE [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_test]
(
    @FechaInicio    date,
    @FechaFin       date,
    @DiasReproceso  int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;

    DECLARE @FechaInicioProceso date =
        CASE
            WHEN DATEADD(DAY, -@DiasReproceso, @FechaFin) < @FechaInicio
                THEN DATEADD(DAY, -@DiasReproceso, @FechaFin)
            ELSE @FechaInicio
        END;

    DECLARE @ConstKOM  float = 357.0;
    DECLARE @ConstCAT  float = 236.0;
    DECLARE @LimiteKOM float = 380.0;
    DECLARE @LimiteCAT float = 265.0;

    /* ================================================================
       PASO A: Calendario
    ================================================================ */
    IF OBJECT_ID('tempdb..#Fechas') IS NOT NULL DROP TABLE #Fechas;
    ;WITH rec AS
    (
        SELECT @FechaInicioProceso AS Fecha
        UNION ALL
        SELECT DATEADD(DAY, 1, Fecha) FROM rec WHERE Fecha < @FechaFin
    )
    SELECT Fecha INTO #Fechas FROM rec OPTION (MAXRECURSION 1000);
    CREATE CLUSTERED INDEX ix_f ON #Fechas(Fecha);

    /* ================================================================
       PASO B: Viajes de camiones por flota (KOM / CAT)
       ---------------------------------------------------------------
       Fuente confirmada: mov_cam, Destino = 'CH01', agrupado por Fecha
       y Flota_CEX. Num_Viajes = SUM(N_BREAK) (no COUNT(*)).
       Query base (entregada por el usuario, sin modificar la logica):
           SELECT mov_cam.Fecha, mov_cam.Flota_CEX,
                  SUM(mov_cam.N_BREAK) AS N_BREAK
           FROM inventar_SpcHidr.mov_cam
           WHERE mov_cam.Fecha BETWEEN @FechaInicioProceso AND @FechaFin
             AND mov_cam.Destino = 'CH01'
           GROUP BY mov_cam.Fecha, mov_cam.Flota_CEX
       Aqui se pivotea directo a columnas KOM/CAT/Otros para dejarlo listo
       para el JOIN de mas abajo, en vez de mantener una fila por flota.
    ================================================================ */
    IF OBJECT_ID('tempdb..#ViajesPorFlota') IS NOT NULL DROP TABLE #ViajesPorFlota;
    SELECT
        CAST(mc.Fecha AS date) AS Fecha,
        mc.Flota_CEX,
        SUM(mc.N_BREAK)        AS N_BREAK
    INTO #ViajesPorFlota
    FROM [inventar_SpcHidr].[mov_cam] mc
    WHERE CAST(mc.Fecha AS date) >= @FechaInicioProceso
      AND CAST(mc.Fecha AS date) <= @FechaFin
      AND mc.Destino = 'CH01'
    GROUP BY CAST(mc.Fecha AS date), mc.Flota_CEX;
    CREATE CLUSTERED INDEX ix_vpf ON #ViajesPorFlota(Fecha, Flota_CEX);

    IF OBJECT_ID('tempdb..#ViajesCamiones') IS NOT NULL DROP TABLE #ViajesCamiones;
    SELECT
        f.Fecha,
        SUM(CASE WHEN vpf.Flota_CEX = 'KOM' THEN vpf.N_BREAK ELSE 0 END) AS KOM_Num_Viajes,
        SUM(CASE WHEN vpf.Flota_CEX = 'CAT' THEN vpf.N_BREAK ELSE 0 END) AS CAT_Num_Viajes,
        SUM(CASE WHEN vpf.Flota_CEX NOT IN ('KOM','CAT') THEN vpf.N_BREAK ELSE 0 END) AS Otros_Num_Viajes,
        CASE
            WHEN SUM(CASE WHEN vpf.Flota_CEX NOT IN ('KOM','CAT') THEN vpf.N_BREAK ELSE 0 END) > 0
                THEN 'CAMIONES_SIN_CLASIFICAR'
            ELSE 'OK'
        END AS Flag_Datos_Incompletos
    INTO #ViajesCamiones
    FROM #Fechas f
    LEFT JOIN #ViajesPorFlota vpf ON vpf.Fecha = f.Fecha
    GROUP BY f.Fecha;
    CREATE CLUSTERED INDEX ix_vc ON #ViajesCamiones(Fecha);

    /* ================================================================
       PASO C: Apilado / Sal / Humedad (Historico_Apilado_Diario)
    ================================================================ */
    IF OBJECT_ID('tempdb..#Apilado') IS NOT NULL DROP TABLE #Apilado;
    SELECT
        CAST(Fecha AS date) AS Fecha,
        Apilado_TMH_promedio_dia,
        Sal_promedio_dia,
        Humedad_promedio_dia
    INTO #Apilado
    FROM [inventar_SpcHidr].[Historico_Apilado_Diario]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_ap ON #Apilado(Fecha);

    /* ================================================================
       PASO D: SRR TMH diario (Historico_SRR_Diario, CV001 corregido)
    ================================================================ */
    IF OBJECT_ID('tempdb..#SRR') IS NOT NULL DROP TABLE #SRR;
    SELECT
        CAST(Fecha AS date) AS Fecha,
        TMH_CV001_Dia AS SRR_TMH_Dia
    INTO #SRR
    FROM [inventar_SpcHidr].[Historico_SRR_Diario]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_srr ON #SRR(Fecha);

    /* ================================================================
       PASO E: MERGE final sobre Control_Factor_Ajuste_Camiones
    ================================================================ */
    MERGE [inventar_SpcHidr].[Control_Factor_Ajuste_Camiones] AS tgt
    USING
    (
        SELECT
            f.Fecha,
            @ConstKOM  AS Constante_KOM_TMH_Viaje,
            @ConstCAT  AS Constante_CAT_TMH_Viaje,
            @LimiteKOM AS Limite_Factor_Carga_KOM,
            @LimiteCAT AS Limite_Factor_Carga_CAT,

            vc.KOM_Num_Viajes,
            vc.CAT_Num_Viajes,
            vc.Otros_Num_Viajes,
            vc.Flag_Datos_Incompletos,
            CAST(vc.KOM_Num_Viajes AS float) * @ConstKOM AS KOM_TMH_Mina,
            CAST(vc.CAT_Num_Viajes AS float) * @ConstCAT AS CAT_TMH_Mina,
            (CAST(vc.KOM_Num_Viajes AS float) * @ConstKOM)
              + (CAST(vc.CAT_Num_Viajes AS float) * @ConstCAT) AS Dato_Mina_TMH,

            a.Apilado_TMH_promedio_dia AS Apilado_TMH_Dia,
            a.Sal_promedio_dia         AS Sal_TMH_Dia,
            s.SRR_TMH_Dia,
            (a.Apilado_TMH_promedio_dia - a.Sal_promedio_dia - s.SRR_TMH_Dia) AS Referencia_Real_TMH,

            a.Humedad_promedio_dia
        FROM #Fechas f
        LEFT JOIN #ViajesCamiones vc ON vc.Fecha = f.Fecha
        LEFT JOIN #Apilado        a  ON a.Fecha  = f.Fecha
        LEFT JOIN #SRR            s  ON s.Fecha  = f.Fecha
    ) AS src
    ON tgt.Fecha = src.Fecha

    WHEN MATCHED THEN UPDATE SET
        Constante_KOM_TMH_Viaje      = src.Constante_KOM_TMH_Viaje,
        Constante_CAT_TMH_Viaje      = src.Constante_CAT_TMH_Viaje,
        Limite_Factor_Carga_KOM      = src.Limite_Factor_Carga_KOM,
        Limite_Factor_Carga_CAT      = src.Limite_Factor_Carga_CAT,
        KOM_Num_Viajes               = src.KOM_Num_Viajes,
        CAT_Num_Viajes               = src.CAT_Num_Viajes,
        Otros_Num_Viajes             = src.Otros_Num_Viajes,
        Flag_Datos_Incompletos       = src.Flag_Datos_Incompletos,
        KOM_TMH_Mina                 = src.KOM_TMH_Mina,
        CAT_TMH_Mina                 = src.CAT_TMH_Mina,
        Dato_Mina_TMH                = src.Dato_Mina_TMH,
        Apilado_TMH_Dia              = src.Apilado_TMH_Dia,
        Sal_TMH_Dia                  = src.Sal_TMH_Dia,
        SRR_TMH_Dia                  = src.SRR_TMH_Dia,
        Referencia_Real_TMH          = src.Referencia_Real_TMH,

        Factor_Ajuste = CASE
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
            WHEN src.Referencia_Real_TMH IS NULL THEN NULL
            ELSE src.Referencia_Real_TMH / src.Dato_Mina_TMH
        END,

        Flag_Factor_Ajuste = CASE
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN 'SIN_DATO_MINA'
            WHEN src.Referencia_Real_TMH IS NULL THEN 'SIN_REFERENCIA'
            ELSE 'OK'
        END,

        KOM_TMH_Corregido = CASE
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
            ELSE src.KOM_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)
        END,
        CAT_TMH_Corregido = CASE
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
            ELSE src.CAT_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)
        END,

        Factor_Carga_KOM_TMH_Viaje = CASE
            WHEN src.KOM_Num_Viajes IS NULL OR src.KOM_Num_Viajes = 0 THEN NULL
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0   THEN NULL
            ELSE (src.KOM_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) / src.KOM_Num_Viajes
        END,
        Factor_Carga_CAT_TMH_Viaje = CASE
            WHEN src.CAT_Num_Viajes IS NULL OR src.CAT_Num_Viajes = 0 THEN NULL
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0   THEN NULL
            ELSE (src.CAT_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) / src.CAT_Num_Viajes
        END,

        Flag_Factor_Carga_KOM = CASE
            WHEN src.KOM_Num_Viajes IS NULL OR src.KOM_Num_Viajes = 0 THEN 'SIN_DATOS'
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0   THEN 'SIN_DATOS'
            WHEN (src.KOM_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) / src.KOM_Num_Viajes > src.Limite_Factor_Carga_KOM
                THEN 'EXCEDE_LIMITE'
            ELSE 'OK'
        END,
        Flag_Factor_Carga_CAT = CASE
            WHEN src.CAT_Num_Viajes IS NULL OR src.CAT_Num_Viajes = 0 THEN 'SIN_DATOS'
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0   THEN 'SIN_DATOS'
            WHEN (src.CAT_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) / src.CAT_Num_Viajes > src.Limite_Factor_Carga_CAT
                THEN 'EXCEDE_LIMITE'
            ELSE 'OK'
        END,

        Humedad_promedio_dia = src.Humedad_promedio_dia,

        Apilado_TMH_Ajustado_OpcionB = CASE
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
            ELSE src.Apilado_TMH_Dia * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)
        END,
        Apilado_TMS_Ajustado_OpcionB = CASE
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
            WHEN src.Humedad_promedio_dia IS NULL THEN NULL
            ELSE (src.Apilado_TMH_Dia * (src.Referencia_Real_TMH / src.Dato_Mina_TMH))
                 * (1.0 - src.Humedad_promedio_dia / 100.0)
        END,
        Apilado_TMS_Sin_Ajuste = CASE
            WHEN src.Apilado_TMH_Dia IS NULL OR src.Humedad_promedio_dia IS NULL THEN NULL
            ELSE src.Apilado_TMH_Dia * (1.0 - src.Humedad_promedio_dia / 100.0)
        END,
        Diferencia_TMS_OpcionB = CASE
            WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
            WHEN src.Humedad_promedio_dia IS NULL THEN NULL
            ELSE ((src.Apilado_TMH_Dia * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) * (1.0 - src.Humedad_promedio_dia / 100.0))
                 - (src.Apilado_TMH_Dia * (1.0 - src.Humedad_promedio_dia / 100.0))
        END,

        Fecha_Calculo = SYSDATETIME()

    WHEN NOT MATCHED BY TARGET THEN INSERT
    (
        Fecha, Constante_KOM_TMH_Viaje, Constante_CAT_TMH_Viaje,
        Limite_Factor_Carga_KOM, Limite_Factor_Carga_CAT,
        KOM_Num_Viajes, CAT_Num_Viajes, Otros_Num_Viajes, Flag_Datos_Incompletos,
        KOM_TMH_Mina, CAT_TMH_Mina, Dato_Mina_TMH,
        Apilado_TMH_Dia, Sal_TMH_Dia, SRR_TMH_Dia, Referencia_Real_TMH,
        Factor_Ajuste, Flag_Factor_Ajuste,
        KOM_TMH_Corregido, CAT_TMH_Corregido,
        Factor_Carga_KOM_TMH_Viaje, Factor_Carga_CAT_TMH_Viaje,
        Flag_Factor_Carga_KOM, Flag_Factor_Carga_CAT,
        Humedad_promedio_dia,
        Apilado_TMH_Ajustado_OpcionB, Apilado_TMS_Ajustado_OpcionB,
        Apilado_TMS_Sin_Ajuste, Diferencia_TMS_OpcionB,
        Fecha_Calculo
    )
    VALUES
    (
        src.Fecha, src.Constante_KOM_TMH_Viaje, src.Constante_CAT_TMH_Viaje,
        src.Limite_Factor_Carga_KOM, src.Limite_Factor_Carga_CAT,
        src.KOM_Num_Viajes, src.CAT_Num_Viajes, src.Otros_Num_Viajes, src.Flag_Datos_Incompletos,
        src.KOM_TMH_Mina, src.CAT_TMH_Mina, src.Dato_Mina_TMH,
        src.Apilado_TMH_Dia, src.Sal_TMH_Dia, src.SRR_TMH_Dia, src.Referencia_Real_TMH,

        CASE WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 OR src.Referencia_Real_TMH IS NULL THEN NULL
             ELSE src.Referencia_Real_TMH / src.Dato_Mina_TMH END,
        CASE WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN 'SIN_DATO_MINA'
             WHEN src.Referencia_Real_TMH IS NULL THEN 'SIN_REFERENCIA'
             ELSE 'OK' END,

        CASE WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
             ELSE src.KOM_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH) END,
        CASE WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
             ELSE src.CAT_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH) END,

        CASE WHEN src.KOM_Num_Viajes IS NULL OR src.KOM_Num_Viajes = 0
                  OR src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
             ELSE (src.KOM_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) / src.KOM_Num_Viajes END,
        CASE WHEN src.CAT_Num_Viajes IS NULL OR src.CAT_Num_Viajes = 0
                  OR src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
             ELSE (src.CAT_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) / src.CAT_Num_Viajes END,

        CASE WHEN src.KOM_Num_Viajes IS NULL OR src.KOM_Num_Viajes = 0
                  OR src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN 'SIN_DATOS'
             WHEN (src.KOM_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) / src.KOM_Num_Viajes > src.Limite_Factor_Carga_KOM THEN 'EXCEDE_LIMITE'
             ELSE 'OK' END,
        CASE WHEN src.CAT_Num_Viajes IS NULL OR src.CAT_Num_Viajes = 0
                  OR src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN 'SIN_DATOS'
             WHEN (src.CAT_TMH_Mina * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) / src.CAT_Num_Viajes > src.Limite_Factor_Carga_CAT THEN 'EXCEDE_LIMITE'
             ELSE 'OK' END,

        src.Humedad_promedio_dia,

        CASE WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 THEN NULL
             ELSE src.Apilado_TMH_Dia * (src.Referencia_Real_TMH / src.Dato_Mina_TMH) END,
        CASE WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 OR src.Humedad_promedio_dia IS NULL THEN NULL
             ELSE (src.Apilado_TMH_Dia * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) * (1.0 - src.Humedad_promedio_dia / 100.0) END,
        CASE WHEN src.Apilado_TMH_Dia IS NULL OR src.Humedad_promedio_dia IS NULL THEN NULL
             ELSE src.Apilado_TMH_Dia * (1.0 - src.Humedad_promedio_dia / 100.0) END,
        CASE WHEN src.Dato_Mina_TMH IS NULL OR src.Dato_Mina_TMH = 0 OR src.Humedad_promedio_dia IS NULL THEN NULL
             ELSE ((src.Apilado_TMH_Dia * (src.Referencia_Real_TMH / src.Dato_Mina_TMH)) * (1.0 - src.Humedad_promedio_dia / 100.0))
                  - (src.Apilado_TMH_Dia * (1.0 - src.Humedad_promedio_dia / 100.0)) END,

        SYSDATETIME()
    );

    DROP TABLE IF EXISTS #Fechas;
    DROP TABLE IF EXISTS #ViajesPorFlota;
    DROP TABLE IF EXISTS #ViajesCamiones;
    DROP TABLE IF EXISTS #Apilado;
    DROP TABLE IF EXISTS #SRR;
END;