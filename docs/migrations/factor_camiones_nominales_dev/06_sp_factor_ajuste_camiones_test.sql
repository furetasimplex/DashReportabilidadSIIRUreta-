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

    -- Fotografia temporal unica para ambas categorias; sin valores de respaldo.
    SELECT flota,parametro,valor,vigencia_desde,vigencia_hasta
    INTO #ParametrosFactorV2
    FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (HOLDLOCK)
    WHERE activo=1 AND parametro IN ('LIMITE_CARGA_AJUSTE','CARGA_NOMINAL_TMH_VIAJE');
    ;WITH Dias AS (
        SELECT @FechaInicio Fecha
        UNION ALL SELECT DATEADD(day,1,Fecha) FROM Dias WHERE Fecha<@FechaFin
    )
    SELECT d.Fecha,f.flota,t.parametro,COUNT(p.flota) cantidad,
           MIN(p.valor) valor
    INTO #ConfiguracionFactorV2
    FROM Dias d CROSS JOIN (VALUES ('KOM'),('CAT')) f(flota)
    CROSS JOIN (VALUES ('LIMITE_CARGA_AJUSTE'),('CARGA_NOMINAL_TMH_VIAJE')) t(parametro)
    LEFT JOIN #ParametrosFactorV2 p ON p.flota=f.flota AND p.parametro=t.parametro
      AND p.vigencia_desde<=d.Fecha AND (p.vigencia_hasta IS NULL OR d.Fecha<p.vigencia_hasta)
    GROUP BY d.Fecha,f.flota,t.parametro OPTION (MAXRECURSION 0);
    DECLARE @ErrorLimite nvarchar(2048);
    SELECT TOP(1) @ErrorLimite=CONCAT('Configuracion no unica: ',parametro,' ',flota,' ',Fecha)
    FROM #ConfiguracionFactorV2 WHERE cantidad<>1 ORDER BY Fecha,parametro,flota;
    IF @ErrorLimite IS NOT NULL THROW 51020,@ErrorLimite,1;
    SELECT Fecha,flota,CAST(valor AS float) limite INTO #LimitesFactorV2
    FROM #ConfiguracionFactorV2 WHERE parametro='LIMITE_CARGA_AJUSTE';
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
    -- Resolucion comun de vueltas por dia completo. Nunca mezclar flotas de fuentes diferentes.
    SELECT b.Fecha,
           COALESCE(v.Vueltas_KOM,0.0) Vueltas_KOM,
           COALESCE(v.Vueltas_CAT,0.0) Vueltas_CAT,
           nk.valor Carga_Nominal_KOM_TMH_Viaje,
           nc.valor Carga_Nominal_CAT_TMH_Viaje,
           COALESCE(v.Vueltas_KOM,0.0)*nk.valor Produccion_KOM_TMH,
           COALESCE(v.Vueltas_CAT,0.0)*nc.valor Produccion_CAT_TMH,
           COALESCE(v.Vueltas_KOM,0.0)*nk.valor+COALESCE(v.Vueltas_CAT,0.0)*nc.valor Produccion_Total_MovCam,
           COALESCE(v.Fuente_Camiones,'SIN_DATOS_CAMIONES') Fuente_Camiones,
           COALESCE(v.Estado_Fuente_MOV_CAM,'SIN_REGISTROS') Estado_Fuente_MOV_CAM,
           COALESCE(v.Estado_Fuente_POWERBI,'SIN_REGISTROS') Estado_Fuente_POWERBI,
           COALESCE(v.Cantidad_Registros_Originales,0) Cantidad_Registros_Originales,
           COALESCE(v.Cantidad_Registros_Validos,0) Cantidad_Registros_Validos,
           CAST(0 AS int) Cantidad_Duplicados_Eliminados
    INTO #CamionesDiario
    FROM #BaseBalance b
    JOIN #ConfiguracionFactorV2 nk ON nk.Fecha=b.Fecha AND nk.flota='KOM' AND nk.parametro='CARGA_NOMINAL_TMH_VIAJE'
    JOIN #ConfiguracionFactorV2 nc ON nc.Fecha=b.Fecha AND nc.flota='CAT' AND nc.parametro='CARGA_NOMINAL_TMH_VIAJE'
    LEFT JOIN inventar_SpcHidr.v_vueltas_camiones_diarias_test v ON v.Fecha=b.Fecha;
    CREATE UNIQUE CLUSTERED INDEX IX_CamionesDiario_Fecha ON #CamionesDiario(Fecha);
    /* ============================================================
       5. Base del factor
       ============================================================ */
    SELECT
        b.*,
        c.Carga_Nominal_KOM_TMH_Viaje,
        c.Carga_Nominal_CAT_TMH_Viaje,
        c.Fuente_Camiones,
        c.Estado_Fuente_MOV_CAM,
        c.Estado_Fuente_POWERBI,
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
        c.Limite_CAT_TMH_Viaje,
        c.Carga_Nominal_KOM_TMH_Viaje,
        c.Carga_Nominal_CAT_TMH_Viaje,
        c.Fuente_Camiones,
        c.Estado_Fuente_MOV_CAM,
        c.Estado_Fuente_POWERBI
    FROM #FactorCorregido AS c
    ORDER BY c.Fecha;
END;