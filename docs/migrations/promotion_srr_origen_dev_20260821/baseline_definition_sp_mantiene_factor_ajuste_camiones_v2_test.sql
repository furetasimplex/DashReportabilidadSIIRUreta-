-- Snapshot DEV previo a promocion SRR
-- modify_date: 2026-08-02 20:56:20.490000
USE [inventar_SpcHidr];
GO

CREATE   PROCEDURE
    [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_test]
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
        Flag_Humedad_Inventario_Valida bit NULL
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
        CAST(r.Fecha AS date) AS Fecha,

        SUM
        (
            CASE
                WHEN UPPER(LTRIM(RTRIM(r.Turno))) = 'A'
                THEN
                    COALESCE(
                        TRY_CONVERT(float, r.Apilado_TMS_Real),
                        0.0
                    )
                    *
                    COALESCE(
                        TRY_CONVERT(float, r.SRR),
                        0.0
                    )
                    / 100.0
                ELSE 0.0
            END
        ) AS SRR_TMS_Turno_A,

        SUM
        (
            CASE
                WHEN UPPER(LTRIM(RTRIM(r.Turno))) = 'B'
                THEN
                    COALESCE(
                        TRY_CONVERT(float, r.Apilado_TMS_Real),
                        0.0
                    )
                    *
                    COALESCE(
                        TRY_CONVERT(float, r.SRR),
                        0.0
                    )
                    / 100.0
                ELSE 0.0
            END
        ) AS SRR_TMS_Turno_B

    INTO #SRRTurnos

    FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test] AS r

    WHERE CAST(r.Fecha AS date)
          BETWEEN @FechaInicioProceso AND @FechaFin

    GROUP BY CAST(r.Fecha AS date);

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

        CAST(380.0 AS float) AS Limite_KOM_TMH_Viaje,
        CAST(265.0 AS float) AS Limite_CAT_TMH_Viaje,

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
