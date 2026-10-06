CREATE   PROCEDURE [inventar_SpcHidr].[sp_calcular_resumen_intervalo_totTM]
(
    @FechaInicio date,
    @FechaFin    date
)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaCorteSRRInstantaneo datetime2(3) = '2026-07-01T08:00:00.000';
    DECLARE @UmbralSRR_TPH float = 5000.0;

    /*
        Colchón de 1 día hacia atrás para poder calcular el primer
        delta válido del primer tick dentro de la ventana.
    */
    DECLARE @FechaInicioTicks datetime2(3) =
        CAST(DATEADD(DAY, -1, @FechaInicio) AS datetime2(3));

    DECLARE @FechaFinTicks datetime2(3) =
    CAST(DATEADD(DAY, 2, @FechaFin) AS datetime2(3));

    ;WITH TicksBase AS
    (
        SELECT
            fecha = CAST(t.fecha AS datetime2(3)),

            tot_008 = CAST(t.tot_008 AS float),
            tot_108 = CAST(t.tot_108 AS float),
            tot_001 = CAST(t.tot_001 AS float),

            prev_fecha = LAG(CAST(t.fecha AS datetime2(3)))
                         OVER (ORDER BY t.fecha),

            prev_008 = LAG(CAST(t.tot_008 AS float))
                       OVER (ORDER BY t.fecha),

            prev_108 = LAG(CAST(t.tot_108 AS float))
                       OVER (ORDER BY t.fecha),

            prev_001 = LAG(CAST(t.tot_001 AS float))
                       OVER (ORDER BY t.fecha)
        FROM inventar_SpcHidr.tot_TM t
        WHERE t.fecha >= @FechaInicioTicks
          AND t.fecha <= @FechaFinTicks
    ),

    TicksEval AS
    (
        SELECT
            fecha,
            segundos = DATEDIFF(SECOND, prev_fecha, fecha),

            /* =====================================================
               CV008 / T1: totalizador acumulado robusto
               ===================================================== */
            ton_valido_008 =
                CASE
                    WHEN tot_008 IS NULL
                      OR prev_008 IS NULL
                      OR prev_fecha IS NULL
                      OR tot_008 <= 0
                      OR prev_008 <= 0
                      OR DATEDIFF(SECOND, prev_fecha, fecha) <= 0
                      OR (tot_008 - prev_008) < 0
                      OR (tot_008 - prev_008)
                            > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                        THEN 0.0
                    ELSE
                        tot_008 - prev_008
                END,

            tick_ok_008 =
                CASE
                    WHEN tot_008 IS NULL
                      OR prev_008 IS NULL
                      OR prev_fecha IS NULL
                      OR tot_008 <= 0
                      OR prev_008 <= 0
                      OR DATEDIFF(SECOND, prev_fecha, fecha) <> 10
                      OR (tot_008 - prev_008) <= 0
                      OR (tot_008 - prev_008)
                            > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                        THEN 0
                    ELSE 1
                END,

            muestra_anomala_008 =
                CASE
                    WHEN tot_008 IS NULL
                      OR prev_008 IS NULL
                      OR prev_fecha IS NULL
                      OR tot_008 <= 0
                      OR prev_008 <= 0
                      OR DATEDIFF(SECOND, prev_fecha, fecha) <> 10
                      OR (tot_008 - prev_008) <= 0
                      OR (tot_008 - prev_008)
                            > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                        THEN 1
                    ELSE 0
                END,

            /* =====================================================
               CV108 / T2: totalizador acumulado robusto
               ===================================================== */
            ton_valido_108 =
                CASE
                    WHEN tot_108 IS NULL
                      OR prev_108 IS NULL
                      OR prev_fecha IS NULL
                      OR tot_108 <= 0
                      OR prev_108 <= 0
                      OR DATEDIFF(SECOND, prev_fecha, fecha) <= 0
                      OR (tot_108 - prev_108) < 0
                      OR (tot_108 - prev_108)
                            > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                        THEN 0.0
                    ELSE
                        tot_108 - prev_108
                END,

            tick_ok_108 =
                CASE
                    WHEN tot_108 IS NULL
                      OR prev_108 IS NULL
                      OR prev_fecha IS NULL
                      OR tot_108 <= 0
                      OR prev_108 <= 0
                      OR DATEDIFF(SECOND, prev_fecha, fecha) <> 10
                      OR (tot_108 - prev_108) <= 0
                      OR (tot_108 - prev_108)
                            > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                        THEN 0
                    ELSE 1
                END,

            muestra_anomala_108 =
                CASE
                    WHEN tot_108 IS NULL
                      OR prev_108 IS NULL
                      OR prev_fecha IS NULL
                      OR tot_108 <= 0
                      OR prev_108 <= 0
                      OR DATEDIFF(SECOND, prev_fecha, fecha) <> 10
                      OR (tot_108 - prev_108) <= 0
                      OR (tot_108 - prev_108)
                            > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                        THEN 1
                    ELSE 0
                END,

            /* =====================================================
               CV001 / SRR:
               - Antes del corte: totalizador acumulado robusto.
               - Desde el corte: tag instantáneo t/h integrado.
               ===================================================== */
            ton_valido_001 =
                CASE
                    WHEN fecha < @FechaCorteSRRInstantaneo
                    THEN
                        CASE
                            WHEN tot_001 IS NULL
                              OR prev_001 IS NULL
                              OR prev_fecha IS NULL
                              OR tot_001 <= 0
                              OR prev_001 <= 0
                              OR DATEDIFF(SECOND, prev_fecha, fecha) <= 0
                              OR (tot_001 - prev_001) < 0
                              OR (tot_001 - prev_001)
                                    > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                                THEN 0.0
                            ELSE
                                tot_001 - prev_001
                        END

                    ELSE
                        CASE
                            WHEN tot_001 IS NULL
                              OR prev_fecha IS NULL
                              OR DATEDIFF(SECOND, prev_fecha, fecha) <= 0
                              OR DATEDIFF(SECOND, prev_fecha, fecha) > 60
                              OR tot_001 < 0
                              OR tot_001 > @UmbralSRR_TPH
                                THEN 0.0
                            ELSE
                                tot_001
                                * DATEDIFF(SECOND, prev_fecha, fecha)
                                / 3600.0
                        END
                END,

            tick_ok_001 =
                CASE
                    WHEN fecha < @FechaCorteSRRInstantaneo
                    THEN
                        CASE
                            WHEN tot_001 IS NULL
                              OR prev_001 IS NULL
                              OR prev_fecha IS NULL
                              OR tot_001 <= 0
                              OR prev_001 <= 0
                              OR DATEDIFF(SECOND, prev_fecha, fecha) <> 10
                              OR (tot_001 - prev_001) <= 0
                              OR (tot_001 - prev_001)
                                    > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                                THEN 0
                            ELSE 1
                        END

                    ELSE
                        CASE
                            WHEN tot_001 IS NULL
                              OR prev_fecha IS NULL
                              OR DATEDIFF(SECOND, prev_fecha, fecha) <> 10
                              OR tot_001 <= 0
                              OR tot_001 > @UmbralSRR_TPH
                                THEN 0
                            ELSE 1
                        END
                END,

            muestra_anomala_001 =
                CASE
                    WHEN fecha < @FechaCorteSRRInstantaneo
                    THEN
                        CASE
                            WHEN tot_001 IS NULL
                              OR prev_001 IS NULL
                              OR prev_fecha IS NULL
                              OR tot_001 <= 0
                              OR prev_001 <= 0
                              OR DATEDIFF(SECOND, prev_fecha, fecha) <> 10
                              OR (tot_001 - prev_001) <= 0
                              OR (tot_001 - prev_001)
                                    > 14.0 * DATEDIFF(SECOND, prev_fecha, fecha) / 10.0
                                THEN 1
                            ELSE 0
                        END

                    ELSE
                        CASE
                            /*
                                Para SRR instantáneo, un valor cero es una
                                condición operacional válida: no hay flujo.
                                Por eso no se marca como anomalía.
                            */
                            WHEN tot_001 IS NULL
                              OR prev_fecha IS NULL
                              OR DATEDIFF(SECOND, prev_fecha, fecha) <= 0
                              OR DATEDIFF(SECOND, prev_fecha, fecha) > 60
                              OR tot_001 < 0
                              OR tot_001 > @UmbralSRR_TPH
                                THEN 1
                            ELSE 0
                        END
                END
        FROM TicksBase
    )

    SELECT
        fecha,
        Torre = 'T1',
        delta_valido_ton = ton_valido_008,
        tick_efectivo = tick_ok_008,
        muestra_anomala = muestra_anomala_008
    INTO #TicksPorTorre
    FROM TicksEval

    UNION ALL

    SELECT
        fecha,
        Torre = 'T2',
        delta_valido_ton = ton_valido_108,
        tick_efectivo = tick_ok_108,
        muestra_anomala = muestra_anomala_108
    FROM TicksEval

    UNION ALL

    SELECT
        fecha,
        Torre = 'SRR',
        delta_valido_ton = ton_valido_001,
        tick_efectivo = tick_ok_001,
        muestra_anomala = muestra_anomala_001
    FROM TicksEval;

    CREATE CLUSTERED INDEX IX_TicksPorTorre
    ON #TicksPorTorre (Torre, fecha);

    /*
        Agregación por intervalo.
    */
    SELECT
        i.fecha_turno,
        i.torre_id,
        i.Torre,
        turno_op = i.turno_op,
        i.ts_ini,
        i.ts_fin,
        i.flag_arrastre,
        i.duracion_min,
        i.comentario,
        i.nombre_archivo,

        tot_ini =
            CASE
                WHEN i.Torre = 'SRR'
                 AND i.ts_fin >= @FechaCorteSRRInstantaneo
                    THEN NULL
                ELSE ti.total_acum
            END,

        tot_fin =
            CASE
                WHEN i.Torre = 'SRR'
                 AND i.ts_fin >= @FechaCorteSRRInstantaneo
                    THEN NULL
                ELSE tf.total_acum
            END,

        toneladas_intervalo =
            SUM(ISNULL(tk.delta_valido_ton, 0.0)),

        muestras_anomalas =
            SUM(ISNULL(tk.muestra_anomala, 0)),

        HE_horas =
            SUM(ISNULL(CAST(tk.tick_efectivo AS float), 0.0))
            * 10.0 / 3600.0,

        flag_intervalo_ok =
            CASE
                WHEN i.Torre IS NOT NULL
                 AND i.ts_ini IS NOT NULL
                 AND i.ts_fin IS NOT NULL
                 AND i.ts_fin > i.ts_ini
                    THEN 1
                ELSE 0
            END

    INTO #ResumenNuevo

    FROM inventar_SpcHidr.v_bitacora_rangos_norm i

    LEFT JOIN #TicksPorTorre tk
        ON  tk.Torre = i.Torre
        AND tk.fecha >  i.ts_ini
        AND tk.fecha <= i.ts_fin

    OUTER APPLY
    (
        SELECT TOP (1)
            total_acum =
                CASE i.Torre
                    WHEN 'T1'  THEN CAST(tm.tot_008 AS float)
                    WHEN 'T2'  THEN CAST(tm.tot_108 AS float)
                    WHEN 'SRR' THEN CAST(tm.tot_001 AS float)
                    ELSE NULL
                END
        FROM inventar_SpcHidr.tot_TM tm
        WHERE tm.fecha <= i.ts_ini
        ORDER BY tm.fecha DESC
    ) AS ti

    OUTER APPLY
    (
        SELECT TOP (1)
            total_acum =
                CASE i.Torre
                    WHEN 'T1'  THEN CAST(tm.tot_008 AS float)
                    WHEN 'T2'  THEN CAST(tm.tot_108 AS float)
                    WHEN 'SRR' THEN CAST(tm.tot_001 AS float)
                    ELSE NULL
                END
        FROM inventar_SpcHidr.tot_TM tm
        WHERE tm.fecha <= i.ts_fin
        ORDER BY tm.fecha DESC
    ) AS tf

    WHERE i.fecha_turno BETWEEN @FechaInicio AND @FechaFin
      AND i.Torre IN ('T1', 'T2', 'SRR')

    GROUP BY
        i.fecha_turno,
        i.torre_id,
        i.Torre,
        i.turno_op,
        i.ts_ini,
        i.ts_fin,
        i.flag_arrastre,
        i.duracion_min,
        i.comentario,
        i.nombre_archivo,
        ti.total_acum,
        tf.total_acum;

    /*
        Upsert dentro de la ventana solicitada.
    */
    MERGE inventar_SpcHidr.Resumen_Intervalo_TotTM AS destino
    USING #ResumenNuevo AS origen
        ON  destino.torre_id    = origen.torre_id
        AND destino.fecha_turno = origen.fecha_turno
        AND destino.turno_op    = origen.turno_op

    WHEN MATCHED THEN
        UPDATE SET
            ts_ini              = origen.ts_ini,
            ts_fin              = origen.ts_fin,
            flag_arrastre       = origen.flag_arrastre,
            duracion_min        = origen.duracion_min,
            comentario          = origen.comentario,
            nombre_archivo      = origen.nombre_archivo,
            tot_ini             = origen.tot_ini,
            tot_fin             = origen.tot_fin,
            toneladas_intervalo = origen.toneladas_intervalo,
            muestras_anomalas   = origen.muestras_anomalas,
            HE_horas            = origen.HE_horas,
            flag_intervalo_ok   = origen.flag_intervalo_ok,
            Fecha_Calculo       = SYSDATETIME()

    WHEN NOT MATCHED BY TARGET THEN
        INSERT
        (
            fecha_turno,
            torre_id,
            Torre,
            turno_op,
            ts_ini,
            ts_fin,
            flag_arrastre,
            duracion_min,
            comentario,
            nombre_archivo,
            tot_ini,
            tot_fin,
            toneladas_intervalo,
            muestras_anomalas,
            HE_horas,
            flag_intervalo_ok,
            Fecha_Calculo
        )
        VALUES
        (
            origen.fecha_turno,
            origen.torre_id,
            origen.Torre,
            origen.turno_op,
            origen.ts_ini,
            origen.ts_fin,
            origen.flag_arrastre,
            origen.duracion_min,
            origen.comentario,
            origen.nombre_archivo,
            origen.tot_ini,
            origen.tot_fin,
            origen.toneladas_intervalo,
            origen.muestras_anomalas,
            origen.HE_horas,
            origen.flag_intervalo_ok,
            SYSDATETIME()
        );

    DROP TABLE #TicksPorTorre;
    DROP TABLE #ResumenNuevo;

    PRINT '-- Resumen_Intervalo_TotTM actualizado con lógica híbrida SRR: '
        + CONVERT(varchar, @FechaInicio)
        + ' a '
        + CONVERT(varchar, @FechaFin);
END;