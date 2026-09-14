/* ================================================================
   inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test
   ----------------------------------------------------------------
   Puebla inventar_SpcHidr.Control_Apilado_TMH_v2_test con la misma
   logica que hoy calcula inventar_SpcHidr.v_datos_apilado_tmh_v2
   (TMH bruto por turno desde los totalizadores CV008/CV108 en
   tot_TM), pero SOLO recalcula:

     1) los ultimos @DiasReproceso dias del rango pedido (ventana
        movil, para capturar correcciones tardias del totalizador),
     2) cualquier fecha dentro del rango pedido que TODAVIA NO
        tenga fila en la tabla (huecos -- primera carga o dias
        nuevos nunca procesados).

   Fechas dentro del rango que ya existen en la tabla y estan FUERA
   de la ventana de reproceso NO se recalculan -- ahi esta el
   ahorro real. Sin esto, cada exportacion de un mes completo
   volveria a tocar tot_TM entero otra vez, igual que antes.

   Diferencia importante con sp_mantiene_factor_ajuste_camiones_v2_test:
   ese SP con @DiasReproceso=0 termina procesando el rango COMPLETO
   igual (bug de diseno ya documentado, no corregido aca para no
   tocar un objeto que no es parte de este cambio). Este SP nuevo
   implementa el recorte real: si @DiasReproceso es menor que el
   ancho del rango pedido, los dias mas antiguos que ya existen en
   la tabla se saltan.
================================================================ */
CREATE PROCEDURE
    [inventar_SpcHidr].[sp_mantiene_apilado_tmh_v2_test]
(
    @FechaInicio   date,
    @FechaFin      date,
    @DiasReproceso int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50901, 'Debe informar @FechaInicio y @FechaFin.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50902, 'La fecha inicial no puede ser mayor que la fecha final.', 1;
    IF @DiasReproceso IS NULL OR @DiasReproceso < 0
        THROW 50903, '@DiasReproceso debe ser mayor o igual que cero.', 1;
    IF OBJECT_ID('inventar_SpcHidr.Control_Apilado_TMH_v2_test', 'U') IS NULL
        THROW 50904, 'No existe la tabla Control_Apilado_TMH_v2_test.', 1;

    /* Inicio de la ventana de reproceso obligatorio: los ultimos
       @DiasReproceso dias del rango pedido. Si @DiasReproceso es
       mayor o igual al ancho del rango, la ventana cubre todo el
       rango (mismo comportamiento que un @FechaInicio normal). */
    DECLARE @FechaInicioVentana date =
        CASE
            WHEN DATEADD(DAY, -(@DiasReproceso - 1), @FechaFin) > @FechaInicio
                THEN DATEADD(DAY, -(@DiasReproceso - 1), @FechaFin)
            ELSE @FechaInicio
        END;
    DECLARE @FechaCalculo datetime2(7) = SYSDATETIME();

    /* ============================================================
       1. Fechas a procesar: ventana de reproceso + huecos
       ============================================================ */
    IF OBJECT_ID('tempdb..#fechas') IS NOT NULL DROP TABLE #fechas;
    ;WITH fechas_candidatas AS
    (
        SELECT DISTINCT
            CAST(fecha AS date) AS Fecha
        FROM inventar_SpcHidr.tot_TM
        WHERE fecha >= @FechaInicio
          AND fecha < DATEADD(DAY, 1, @FechaFin)
    )
    SELECT fc.Fecha
    INTO #fechas
    FROM fechas_candidatas AS fc
    WHERE fc.Fecha >= @FechaInicioVentana
       OR NOT EXISTS
          (
              SELECT 1
              FROM inventar_SpcHidr.Control_Apilado_TMH_v2_test AS c
              WHERE c.Fecha = fc.Fecha
          );
    CREATE UNIQUE CLUSTERED INDEX IX_fechas ON #fechas(Fecha);

    /* Si no hay nada que procesar (todo el rango ya estaba
       calculado y fuera de la ventana), terminar rapido. */
    IF NOT EXISTS (SELECT 1 FROM #fechas)
    BEGIN
        PRINT 'sp_mantiene_apilado_tmh_v2_test: nada que reprocesar, todo el rango ya estaba vigente.';
        RETURN;
    END;

    /* ============================================================
       2. Misma logica que v_datos_apilado_tmh_v2, acotada a #fechas
       ============================================================ */
    ;WITH marcas AS
    (
        SELECT
            f.Fecha,
            CAST(DATEADD(HOUR, 8, CAST(f.Fecha AS datetime2)) AS datetime2) AS ts_08_dia,
            CAST(DATEADD(HOUR, 20, CAST(f.Fecha AS datetime2)) AS datetime2) AS ts_20_dia,
            CAST(DATEADD(HOUR, 8, DATEADD(DAY, 1, CAST(f.Fecha AS datetime2))) AS datetime2) AS ts_08_dia_siguiente
        FROM #fechas AS f
    ),
    totales AS
    (
        SELECT
            m.Fecha,
            m.ts_08_dia,
            m.ts_20_dia,
            m.ts_08_dia_siguiente,
            CAST(t08.tot_008 AS float) AS CV008_Totalizador_08,
            CAST(t20.tot_008 AS float) AS CV008_Totalizador_20,
            CAST(t08s.tot_008 AS float) AS CV008_Totalizador_08_Dia_Siguiente,
            CAST(t08.tot_108 AS float) AS CV108_Totalizador_08,
            CAST(t20.tot_108 AS float) AS CV108_Totalizador_20,
            CAST(t08s.tot_108 AS float) AS CV108_Totalizador_08_Dia_Siguiente
        FROM marcas AS m
        LEFT JOIN inventar_SpcHidr.tot_TM AS t08
            ON t08.fecha = m.ts_08_dia
        LEFT JOIN inventar_SpcHidr.tot_TM AS t20
            ON t20.fecha = m.ts_20_dia
        LEFT JOIN inventar_SpcHidr.tot_TM AS t08s
            ON t08s.fecha = m.ts_08_dia_siguiente
    ),
    calculo_bruto AS
    (
        SELECT
            Fecha,
            ts_08_dia,
            ts_20_dia,
            ts_08_dia_siguiente,
            CV008_Totalizador_08,
            CV008_Totalizador_20,
            CV008_Totalizador_08_Dia_Siguiente,
            CV108_Totalizador_08,
            CV108_Totalizador_20,
            CV108_Totalizador_08_Dia_Siguiente,
            CV008_Totalizador_20 - CV008_Totalizador_08 AS TMH_CV008_A_Bruto,
            CV008_Totalizador_08_Dia_Siguiente - CV008_Totalizador_20 AS TMH_CV008_B_Bruto,
            CV108_Totalizador_20 - CV108_Totalizador_08 AS TMH_CV108_A_Bruto,
            CV108_Totalizador_08_Dia_Siguiente - CV108_Totalizador_20 AS TMH_CV108_B_Bruto
        FROM totales
    ),
    validacion AS
    (
        SELECT
            Fecha,
            ts_08_dia,
            ts_20_dia,
            ts_08_dia_siguiente,
            CV008_Totalizador_08,
            CV008_Totalizador_20,
            CV008_Totalizador_08_Dia_Siguiente,
            CV108_Totalizador_08,
            CV108_Totalizador_20,
            CV108_Totalizador_08_Dia_Siguiente,
            TMH_CV008_A_Bruto,
            TMH_CV008_B_Bruto,
            TMH_CV108_A_Bruto,
            TMH_CV108_B_Bruto,
            CASE
                WHEN TMH_CV008_A_Bruto IS NULL THEN 0
                WHEN TMH_CV008_A_Bruto <= 100 THEN 0
                ELSE TMH_CV008_A_Bruto
            END AS TMH_CV008_A_Valido,
            CASE
                WHEN TMH_CV108_A_Bruto IS NULL THEN 0
                WHEN TMH_CV108_A_Bruto <= 100 THEN 0
                ELSE TMH_CV108_A_Bruto
            END AS TMH_CV108_A_Valido,
            CASE
                WHEN TMH_CV008_B_Bruto IS NULL THEN 0
                WHEN TMH_CV008_B_Bruto <= 100 THEN 0
                ELSE TMH_CV008_B_Bruto
            END AS TMH_CV008_B_Valido,
            CASE
                WHEN TMH_CV108_B_Bruto IS NULL THEN 0
                WHEN TMH_CV108_B_Bruto <= 100 THEN 0
                ELSE TMH_CV108_B_Bruto
            END AS TMH_CV108_B_Valido
        FROM calculo_bruto
    ),
    validacion_turno AS
    (
        SELECT
            *,
            TMH_CV008_A_Valido + TMH_CV108_A_Valido AS TMH_Total_A_Valido,
            TMH_CV008_B_Valido + TMH_CV108_B_Valido AS TMH_Total_B_Valido,
            CASE WHEN TMH_CV008_A_Valido + TMH_CV108_A_Valido > 100 THEN 1 ELSE 0 END AS Flag_Apilado_Valido_A,
            CASE WHEN TMH_CV008_B_Valido + TMH_CV108_B_Valido > 100 THEN 1 ELSE 0 END AS Flag_Apilado_Valido_B
        FROM validacion
    )
    SELECT
        Fecha,
        ts_08_dia,
        ts_20_dia,
        ts_08_dia_siguiente,
        CV008_Totalizador_08,
        CV008_Totalizador_20,
        CV008_Totalizador_08_Dia_Siguiente,
        CV108_Totalizador_08,
        CV108_Totalizador_20,
        CV108_Totalizador_08_Dia_Siguiente,
        TMH_CV008_A_Bruto,
        TMH_CV008_B_Bruto,
        TMH_CV108_A_Bruto,
        TMH_CV108_B_Bruto,
        CASE WHEN Flag_Apilado_Valido_A = 1 AND Flag_Apilado_Valido_B = 1 THEN 1 ELSE 0 END AS Flag_Apilado_Valido,
        CASE WHEN Flag_Apilado_Valido_A = 1 THEN TMH_CV008_A_Valido ELSE 0 END AS TMH_CV008_A,
        CASE WHEN Flag_Apilado_Valido_B = 1 THEN TMH_CV008_B_Valido ELSE 0 END AS TMH_CV008_B,
        CASE WHEN Flag_Apilado_Valido_A = 1 THEN TMH_CV108_A_Valido ELSE 0 END AS TMH_CV108_A,
        CASE WHEN Flag_Apilado_Valido_B = 1 THEN TMH_CV108_B_Valido ELSE 0 END AS TMH_CV108_B,
        CASE WHEN Flag_Apilado_Valido_A = 1 THEN TMH_Total_A_Valido ELSE 0 END AS TMH_Apilado_Total_A,
        CASE WHEN Flag_Apilado_Valido_B = 1 THEN TMH_Total_B_Valido ELSE 0 END AS TMH_Apilado_Total_B,
        (CASE WHEN Flag_Apilado_Valido_A = 1 THEN TMH_Total_A_Valido ELSE 0 END)
      + (CASE WHEN Flag_Apilado_Valido_B = 1 THEN TMH_Total_B_Valido ELSE 0 END) AS TMH_Apilado_Total_Dia,
        Flag_Apilado_Valido_A,
        Flag_Apilado_Valido_B,
        @FechaCalculo AS Fecha_Calculo
    INTO #resultado
    FROM validacion_turno;

    /* ============================================================
       3. MERGE hacia la tabla congelada
       ============================================================ */
    MERGE inventar_SpcHidr.Control_Apilado_TMH_v2_test WITH (HOLDLOCK) AS tgt
    USING #resultado AS src
        ON tgt.Fecha = src.Fecha
    WHEN MATCHED THEN
        UPDATE SET
            ts_08_dia = src.ts_08_dia,
            ts_20_dia = src.ts_20_dia,
            ts_08_dia_siguiente = src.ts_08_dia_siguiente,
            CV008_Totalizador_08 = src.CV008_Totalizador_08,
            CV008_Totalizador_20 = src.CV008_Totalizador_20,
            CV008_Totalizador_08_Dia_Siguiente = src.CV008_Totalizador_08_Dia_Siguiente,
            CV108_Totalizador_08 = src.CV108_Totalizador_08,
            CV108_Totalizador_20 = src.CV108_Totalizador_20,
            CV108_Totalizador_08_Dia_Siguiente = src.CV108_Totalizador_08_Dia_Siguiente,
            TMH_CV008_A_Bruto = src.TMH_CV008_A_Bruto,
            TMH_CV008_B_Bruto = src.TMH_CV008_B_Bruto,
            TMH_CV108_A_Bruto = src.TMH_CV108_A_Bruto,
            TMH_CV108_B_Bruto = src.TMH_CV108_B_Bruto,
            Flag_Apilado_Valido = src.Flag_Apilado_Valido,
            TMH_CV008_A = src.TMH_CV008_A,
            TMH_CV008_B = src.TMH_CV008_B,
            TMH_CV108_A = src.TMH_CV108_A,
            TMH_CV108_B = src.TMH_CV108_B,
            TMH_Apilado_Total_A = src.TMH_Apilado_Total_A,
            TMH_Apilado_Total_B = src.TMH_Apilado_Total_B,
            TMH_Apilado_Total_Dia = src.TMH_Apilado_Total_Dia,
            Flag_Apilado_Valido_A = src.Flag_Apilado_Valido_A,
            Flag_Apilado_Valido_B = src.Flag_Apilado_Valido_B,
            Fecha_Calculo = src.Fecha_Calculo
    WHEN NOT MATCHED BY TARGET THEN
        INSERT
        (
            Fecha, ts_08_dia, ts_20_dia, ts_08_dia_siguiente,
            CV008_Totalizador_08, CV008_Totalizador_20, CV008_Totalizador_08_Dia_Siguiente,
            CV108_Totalizador_08, CV108_Totalizador_20, CV108_Totalizador_08_Dia_Siguiente,
            TMH_CV008_A_Bruto, TMH_CV008_B_Bruto, TMH_CV108_A_Bruto, TMH_CV108_B_Bruto,
            Flag_Apilado_Valido,
            TMH_CV008_A, TMH_CV008_B, TMH_CV108_A, TMH_CV108_B,
            TMH_Apilado_Total_A, TMH_Apilado_Total_B, TMH_Apilado_Total_Dia,
            Flag_Apilado_Valido_A, Flag_Apilado_Valido_B,
            Fecha_Calculo
        )
        VALUES
        (
            src.Fecha, src.ts_08_dia, src.ts_20_dia, src.ts_08_dia_siguiente,
            src.CV008_Totalizador_08, src.CV008_Totalizador_20, src.CV008_Totalizador_08_Dia_Siguiente,
            src.CV108_Totalizador_08, src.CV108_Totalizador_20, src.CV108_Totalizador_08_Dia_Siguiente,
            src.TMH_CV008_A_Bruto, src.TMH_CV008_B_Bruto, src.TMH_CV108_A_Bruto, src.TMH_CV108_B_Bruto,
            src.Flag_Apilado_Valido,
            src.TMH_CV008_A, src.TMH_CV008_B, src.TMH_CV108_A, src.TMH_CV108_B,
            src.TMH_Apilado_Total_A, src.TMH_Apilado_Total_B, src.TMH_Apilado_Total_Dia,
            src.Flag_Apilado_Valido_A, src.Flag_Apilado_Valido_B,
            src.Fecha_Calculo
        );

    DECLARE @FilasAfectadas int = @@ROWCOUNT;
    PRINT 'sp_mantiene_apilado_tmh_v2_test finalizado.';
    PRINT 'Ventana de reproceso obligatorio: ' + CONVERT(varchar(10), @FechaInicioVentana, 120) + ' a ' + CONVERT(varchar(10), @FechaFin, 120);
    PRINT 'Filas insertadas/actualizadas: ' + CONVERT(varchar(20), @FilasAfectadas);
END;