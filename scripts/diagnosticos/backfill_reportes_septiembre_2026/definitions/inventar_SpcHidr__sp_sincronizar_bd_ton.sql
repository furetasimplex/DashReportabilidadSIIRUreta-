CREATE   PROCEDURE [inventar_SpcHidr].[sp_sincronizar_bd_ton]
    @fecha_inicio date,
    @fecha_fin    date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @FechaCorteContingencia date = '2026-09-01';

    /* ============================================================
       1. Validar parámetros
       ============================================================ */
    IF @fecha_inicio IS NULL
       OR @fecha_fin IS NULL
       OR @fecha_inicio > @fecha_fin
    BEGIN
        THROW 50001,
              'El rango de fechas ingresado no es válido.',
              1;
    END;

    DROP TABLE IF EXISTS #src;

    /* ============================================================
       2. Evaluabilidad operacional GLOBAL
          SIN CAMBIOS.
       ============================================================ */
    ;WITH evaluabilidad AS
    (
        SELECT
            Fecha = CAST(Fecha AS date),

            Turno_Evaluable_TA =
                MAX(
                    CASE
                        WHEN Turno = 'A'
                            THEN CAST(Turno_Evaluable AS tinyint)
                    END
                ),

            Turno_Evaluable_TB =
                MAX(
                    CASE
                        WHEN Turno = 'B'
                            THEN CAST(Turno_Evaluable AS tinyint)
                    END
                )

        FROM inventar_SpcHidr.v_estado_apilado_turno_representatividad

        WHERE Fecha >= @fecha_inicio
          AND Fecha < DATEADD(DAY, 1, @fecha_fin)

        GROUP BY
            CAST(Fecha AS date)
    )

    /* ============================================================
       3. Preparar origen completo T1 + T2 + SRR
       ============================================================ */
    SELECT
        Fecha =
            CAST(v.Fecha AS date),

        /* ========================================================
           Tonelajes T1/T2
           ======================================================== */
        Apilado_TMH_CV08_TA =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                        THEN c.TMH_TM1_TA_Resuelto
                    ELSE v.[Apilado TMH CV-08 TA]
                END
                AS decimal(18,3)
            ),

        Apilado_TMH_CV08_TB =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                        THEN c.TMH_TM1_TB_Resuelto
                    ELSE v.[Apilado TMH CV-08 TB]
                END
                AS decimal(18,3)
            ),

        Apilado_TMH_CV108_TA =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                        THEN c.TMH_TM2_TA_Resuelto
                    ELSE v.[Apilado TMH CV-108 TA]
                END
                AS decimal(18,3)
            ),

        Apilado_TMH_CV108_TB =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                        THEN c.TMH_TM2_TB_Resuelto
                    ELSE v.[Apilado TMH CV-108 TB]
                END
                AS decimal(18,3)
            ),

        /* ========================================================
           Representatividad T1
           ======================================================== */
        Rep_TM1_TA_Qui =
            CAST(v.[Rep. TM1 TA Qui.] AS decimal(18,10)),

        Rep_TM1_TA_Fis =
            CAST(v.[Rep. TM1 TA Fis.] AS decimal(18,10)),

        Rep_TM1_TB_Qui =
            CAST(v.[Rep. TM1 TB Qui.] AS decimal(18,10)),

        Rep_TM1_TB_Fis =
            CAST(v.[Rep. TM1 TB Fis.] AS decimal(18,10)),

        /* ========================================================
           Representatividad T2
           ======================================================== */
        Rep_TM2_TA_Qui =
            CAST(v.[Rep. TM2 TA Qui.] AS decimal(18,10)),

        Rep_TM2_TA_Fis =
            CAST(v.[Rep. TM2 TA Fis.] AS decimal(18,10)),

        Rep_TM2_TB_Qui =
            CAST(v.[Rep. TM2 TB Qui.] AS decimal(18,10)),

        Rep_TM2_TB_Fis =
            CAST(v.[Rep. TM2 TB Fis.] AS decimal(18,10)),

        /* ========================================================
           Flags químicos T1/T2
           SIN CAMBIO METODOLÓGICO
           ======================================================== */
        Muestra_representativa_TM1_TA =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                    THEN
                        CASE
                            WHEN COALESCE(c.Evaluable_TM1_TA_Resuelto, 0) = 0
                                THEN NULL
                            WHEN v.[Rep. TM1 TA Qui.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                    ELSE
                        CASE
                            WHEN COALESCE(a.TMH_CV008_A, 0) <= 0
                                THEN NULL
                            WHEN v.[Rep. TM1 TA Qui.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                END
                AS int
            ),

        Muestra_representativa_TM1_TB =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                    THEN
                        CASE
                            WHEN COALESCE(c.Evaluable_TM1_TB_Resuelto, 0) = 0
                                THEN NULL
                            WHEN v.[Rep. TM1 TB Qui.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                    ELSE
                        CASE
                            WHEN COALESCE(a.TMH_CV008_B, 0) <= 0
                                THEN NULL
                            WHEN v.[Rep. TM1 TB Qui.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                END
                AS int
            ),

        Muestra_representativa_TM2_TA =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                    THEN
                        CASE
                            WHEN COALESCE(c.Evaluable_TM2_TA_Resuelto, 0) = 0
                                THEN NULL
                            WHEN v.[Rep. TM2 TA Qui.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                    ELSE
                        CASE
                            WHEN COALESCE(a.TMH_CV108_A, 0) <= 0
                                THEN NULL
                            WHEN v.[Rep. TM2 TA Qui.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                END
                AS int
            ),

        Muestra_representativa_TM2_TB =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                    THEN
                        CASE
                            WHEN COALESCE(c.Evaluable_TM2_TB_Resuelto, 0) = 0
                                THEN NULL
                            WHEN v.[Rep. TM2 TB Qui.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                    ELSE
                        CASE
                            WHEN COALESCE(a.TMH_CV108_B, 0) <= 0
                                THEN NULL
                            WHEN v.[Rep. TM2 TB Qui.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                END
                AS int
            ),

        /* ========================================================
           Flags físicos T1/T2
           ======================================================== */
        FISICO_TM1_TA =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                    THEN
                        CASE
                            WHEN COALESCE(c.Evaluable_TM1_TA_Resuelto, 0) = 0
                                THEN NULL
                            WHEN v.[Rep. TM1 TA Fis.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                    ELSE
                        CASE
                            WHEN COALESCE(a.TMH_CV008_A, 0) <= 0
                                THEN NULL
                            WHEN v.[Rep. TM1 TA Fis.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                END
                AS int
            ),

        FISICO_TM1_TB =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                    THEN
                        CASE
                            WHEN COALESCE(c.Evaluable_TM1_TB_Resuelto, 0) = 0
                                THEN NULL
                            WHEN v.[Rep. TM1 TB Fis.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                    ELSE
                        CASE
                            WHEN COALESCE(a.TMH_CV008_B, 0) <= 0
                                THEN NULL
                            WHEN v.[Rep. TM1 TB Fis.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                END
                AS int
            ),

        FISICO_TM2_TA =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                    THEN
                        CASE
                            WHEN COALESCE(c.Evaluable_TM2_TA_Resuelto, 0) = 0
                                THEN NULL
                            WHEN v.[Rep. TM2 TA Fis.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                    ELSE
                        CASE
                            WHEN COALESCE(a.TMH_CV108_A, 0) <= 0
                                THEN NULL
                            WHEN v.[Rep. TM2 TA Fis.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                END
                AS int
            ),

        FISICO_TM2_TB =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                    THEN
                        CASE
                            WHEN COALESCE(c.Evaluable_TM2_TB_Resuelto, 0) = 0
                                THEN NULL
                            WHEN v.[Rep. TM2 TB Fis.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                    ELSE
                        CASE
                            WHEN COALESCE(a.TMH_CV108_B, 0) <= 0
                                THEN NULL
                            WHEN v.[Rep. TM2 TB Fis.] >= 0.75
                                THEN 1
                            ELSE 0
                        END
                END
                AS int
            ),

        /* ========================================================
           Torre 3 / SRR
           SIN CAMBIOS
           ======================================================== */
        Apilado_TMH_CV01_TA =
            CAST(
                v.[Apilado TMH CV-01 TA]
                AS decimal(18,3)
            ),

        Apilado_TMH_CV01_TB =
            CAST(
                v.[Apilado TMH CV-01 TB]
                AS decimal(18,3)
            ),

        Rep_SRR_TA_Qui =
            CAST(v.[Rep. SRR TA Qui.] AS decimal(18,10)),

        Rep_SRR_TA_Fis =
            CAST(v.[Rep. SRR TA Fis.] AS decimal(18,10)),

        Rep_SRR_TB_Qui =
            CAST(v.[Rep. SRR TB Qui.] AS decimal(18,10)),

        Rep_SRR_TB_Fis =
            CAST(v.[Rep. SRR TB Fis.] AS decimal(18,10)),

        Muestra_representativa_TM3_TA =
            CAST(v.[Muestra representativa TM3 TA] AS int),

        Muestra_representativa_TM3_TB =
            CAST(v.[Muestra representativa TM3 TB] AS int),

        FISICO_TM3_TA =
            CAST(v.[FISICO TM3 TA] AS int),

        FISICO_TM3_TB =
            CAST(v.[FISICO TM3 TB] AS int),

        /* ========================================================
           Evaluabilidad global
           SIN CAMBIOS
           ======================================================== */
        e.Turno_Evaluable_TA,
        e.Turno_Evaluable_TB,

        /* ========================================================
           NUEVO:
           Evaluabilidad independiente T1/T2 persistible.

           Antes del corte se conserva NULL en estas columnas.
           El histórico continúa resolviéndose en la vista.
           ======================================================== */
        Evaluable_TM1_TA =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                        THEN c.Evaluable_TM1_TA_Resuelto
                    ELSE NULL
                END
                AS tinyint
            ),

        Evaluable_TM1_TB =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                        THEN c.Evaluable_TM1_TB_Resuelto
                    ELSE NULL
                END
                AS tinyint
            ),

        Evaluable_TM2_TA =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                        THEN c.Evaluable_TM2_TA_Resuelto
                    ELSE NULL
                END
                AS tinyint
            ),

        Evaluable_TM2_TB =
            CAST(
                CASE
                    WHEN CAST(v.Fecha AS date) >= @FechaCorteContingencia
                        THEN c.Evaluable_TM2_TB_Resuelto
                    ELSE NULL
                END
                AS tinyint
            ),

        /* Control técnico interno. No se persiste. */
        Contingencia_T12_Disponible =
            CAST(
                CASE
                    WHEN c.Fecha IS NOT NULL THEN 1
                    ELSE 0
                END
                AS tinyint
            )

    INTO #src

    FROM inventar_SpcHidr.v_bd_ton_oficial AS v

    LEFT JOIN evaluabilidad AS e
      ON e.Fecha = CAST(v.Fecha AS date)

    LEFT JOIN inventar_SpcHidr.v_datos_apilado_tmh_v2 AS a
      ON a.Fecha = CAST(v.Fecha AS date)

    LEFT JOIN inventar_SpcHidr.v_bd_ton_t12_contingencia_test AS c
      ON c.Fecha = CAST(v.Fecha AS date)
     AND CAST(v.Fecha AS date) >= @FechaCorteContingencia

    WHERE v.Fecha >= @fecha_inicio
      AND v.Fecha < DATEADD(DAY, 1, @fecha_fin);


    /* ============================================================
       4. Validar existencia
       ============================================================ */
    IF NOT EXISTS
    (
        SELECT 1
        FROM #src
    )
    BEGIN
        THROW 50002,
              'v_bd_ton_oficial no devolvió registros para el rango solicitado.',
              1;
    END;


    /* ============================================================
       5. Validar una fila por fecha
       ============================================================ */
    IF EXISTS
    (
        SELECT
            Fecha
        FROM #src
        GROUP BY Fecha
        HAVING COUNT(*) > 1
    )
    BEGIN
        THROW 50003,
              'La vista devolvió más de un registro para una misma fecha.',
              1;
    END;


    /* ============================================================
       5.1 Validar cobertura de PI/TUM desde corte
       ============================================================ */
    IF EXISTS
    (
        SELECT 1
        FROM #src
        WHERE Fecha >= @FechaCorteContingencia
          AND Contingencia_T12_Disponible = 0
    )
    BEGIN
        THROW 50004,
              'Falta cobertura de v_bd_ton_t12_contingencia_test para una o más fechas posteriores al 01-09-2026.',
              1;
    END;


    DECLARE @filas_actualizadas int = 0;
    DECLARE @filas_insertadas  int = 0;


    BEGIN TRY

        BEGIN TRANSACTION;

        /* ========================================================
           6. Actualizar fechas existentes
           ======================================================== */
        UPDATE destino
        SET
            destino.Apilado_TMH_CV08_TA =
                origen.Apilado_TMH_CV08_TA,

            destino.Apilado_TMH_CV08_TB =
                origen.Apilado_TMH_CV08_TB,

            destino.Apilado_TMH_CV108_TA =
                origen.Apilado_TMH_CV108_TA,

            destino.Apilado_TMH_CV108_TB =
                origen.Apilado_TMH_CV108_TB,

            destino.Rep_TM1_TA_Qui =
                origen.Rep_TM1_TA_Qui,

            destino.Rep_TM1_TA_Fis =
                origen.Rep_TM1_TA_Fis,

            destino.Rep_TM1_TB_Qui =
                origen.Rep_TM1_TB_Qui,

            destino.Rep_TM1_TB_Fis =
                origen.Rep_TM1_TB_Fis,

            destino.Rep_TM2_TA_Qui =
                origen.Rep_TM2_TA_Qui,

            destino.Rep_TM2_TA_Fis =
                origen.Rep_TM2_TA_Fis,

            destino.Rep_TM2_TB_Qui =
                origen.Rep_TM2_TB_Qui,

            destino.Rep_TM2_TB_Fis =
                origen.Rep_TM2_TB_Fis,

            destino.Muestra_representativa_TM1_TA =
                origen.Muestra_representativa_TM1_TA,

            destino.Muestra_representativa_TM1_TB =
                origen.Muestra_representativa_TM1_TB,

            destino.Muestra_representativa_TM2_TA =
                origen.Muestra_representativa_TM2_TA,

            destino.Muestra_representativa_TM2_TB =
                origen.Muestra_representativa_TM2_TB,

            destino.FISICO_TM1_TA =
                origen.FISICO_TM1_TA,

            destino.FISICO_TM1_TB =
                origen.FISICO_TM1_TB,

            destino.FISICO_TM2_TA =
                origen.FISICO_TM2_TA,

            destino.FISICO_TM2_TB =
                origen.FISICO_TM2_TB,

            /* SRR */
            destino.Apilado_TMH_CV01_TA =
                origen.Apilado_TMH_CV01_TA,

            destino.Apilado_TMH_CV01_TB =
                origen.Apilado_TMH_CV01_TB,

            destino.Rep_SRR_TA_Qui =
                origen.Rep_SRR_TA_Qui,

            destino.Rep_SRR_TA_Fis =
                origen.Rep_SRR_TA_Fis,

            destino.Rep_SRR_TB_Qui =
                origen.Rep_SRR_TB_Qui,

            destino.Rep_SRR_TB_Fis =
                origen.Rep_SRR_TB_Fis,

            destino.Muestra_representativa_TM3_TA =
                origen.Muestra_representativa_TM3_TA,

            destino.Muestra_representativa_TM3_TB =
                origen.Muestra_representativa_TM3_TB,

            destino.FISICO_TM3_TA =
                origen.FISICO_TM3_TA,

            destino.FISICO_TM3_TB =
                origen.FISICO_TM3_TB,

            destino.Turno_Evaluable_TA =
                origen.Turno_Evaluable_TA,

            destino.Turno_Evaluable_TB =
                origen.Turno_Evaluable_TB,

            /* NUEVO */
            destino.Evaluable_TM1_TA =
                origen.Evaluable_TM1_TA,

            destino.Evaluable_TM1_TB =
                origen.Evaluable_TM1_TB,

            destino.Evaluable_TM2_TA =
                origen.Evaluable_TM2_TA,

            destino.Evaluable_TM2_TB =
                origen.Evaluable_TM2_TB

        FROM inventar_SpcHidr.BD_Ton AS destino

        INNER JOIN #src AS origen
          ON origen.Fecha = destino.Fecha;

        SET @filas_actualizadas = @@ROWCOUNT;


        /* ========================================================
           7. Insertar fechas nuevas
           ======================================================== */
        INSERT INTO inventar_SpcHidr.BD_Ton
        (
            Fecha,

            Apilado_TMH_CV08_TA,
            Apilado_TMH_CV08_TB,
            Apilado_TMH_CV108_TA,
            Apilado_TMH_CV108_TB,

            Rep_TM1_TA_Qui,
            Rep_TM1_TA_Fis,
            Rep_TM1_TB_Qui,
            Rep_TM1_TB_Fis,

            Rep_TM2_TA_Qui,
            Rep_TM2_TA_Fis,
            Rep_TM2_TB_Qui,
            Rep_TM2_TB_Fis,

            Muestra_representativa_TM1_TA,
            Muestra_representativa_TM1_TB,
            Muestra_representativa_TM2_TA,
            Muestra_representativa_TM2_TB,

            FISICO_TM1_TA,
            FISICO_TM1_TB,
            FISICO_TM2_TA,
            FISICO_TM2_TB,

            Apilado_TMH_CV01_TA,
            Apilado_TMH_CV01_TB,

            Rep_SRR_TA_Qui,
            Rep_SRR_TA_Fis,
            Rep_SRR_TB_Qui,
            Rep_SRR_TB_Fis,

            Muestra_representativa_TM3_TA,
            Muestra_representativa_TM3_TB,

            FISICO_TM3_TA,
            FISICO_TM3_TB,

            Turno_Evaluable_TA,
            Turno_Evaluable_TB,

            /* NUEVO */
            Evaluable_TM1_TA,
            Evaluable_TM1_TB,
            Evaluable_TM2_TA,
            Evaluable_TM2_TB
        )

        SELECT
            origen.Fecha,

            origen.Apilado_TMH_CV08_TA,
            origen.Apilado_TMH_CV08_TB,
            origen.Apilado_TMH_CV108_TA,
            origen.Apilado_TMH_CV108_TB,

            origen.Rep_TM1_TA_Qui,
            origen.Rep_TM1_TA_Fis,
            origen.Rep_TM1_TB_Qui,
            origen.Rep_TM1_TB_Fis,

            origen.Rep_TM2_TA_Qui,
            origen.Rep_TM2_TA_Fis,
            origen.Rep_TM2_TB_Qui,
            origen.Rep_TM2_TB_Fis,

            origen.Muestra_representativa_TM1_TA,
            origen.Muestra_representativa_TM1_TB,
            origen.Muestra_representativa_TM2_TA,
            origen.Muestra_representativa_TM2_TB,

            origen.FISICO_TM1_TA,
            origen.FISICO_TM1_TB,
            origen.FISICO_TM2_TA,
            origen.FISICO_TM2_TB,

            origen.Apilado_TMH_CV01_TA,
            origen.Apilado_TMH_CV01_TB,

            origen.Rep_SRR_TA_Qui,
            origen.Rep_SRR_TA_Fis,
            origen.Rep_SRR_TB_Qui,
            origen.Rep_SRR_TB_Fis,

            origen.Muestra_representativa_TM3_TA,
            origen.Muestra_representativa_TM3_TB,

            origen.FISICO_TM3_TA,
            origen.FISICO_TM3_TB,

            origen.Turno_Evaluable_TA,
            origen.Turno_Evaluable_TB,

            /* NUEVO */
            origen.Evaluable_TM1_TA,
            origen.Evaluable_TM1_TB,
            origen.Evaluable_TM2_TA,
            origen.Evaluable_TM2_TB

        FROM #src AS origen

        WHERE NOT EXISTS
        (
            SELECT 1
            FROM inventar_SpcHidr.BD_Ton AS destino
            WHERE destino.Fecha = origen.Fecha
        );

        SET @filas_insertadas = @@ROWCOUNT;

        COMMIT TRANSACTION;

    END TRY

    BEGIN CATCH

        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        THROW;

    END CATCH;


    /* ============================================================
       8. Resumen
       CONTRATO PYTHON/DASH INTACTO
       ============================================================ */
    SELECT
        Fecha_Inicio = @fecha_inicio,
        Fecha_Fin    = @fecha_fin,

        Filas_Origen =
            (SELECT COUNT(*) FROM #src),

        Filas_Actualizadas =
            @filas_actualizadas,

        Filas_Insertadas =
            @filas_insertadas,

        Fechas_Sin_Evaluabilidad =
        (
            SELECT COUNT(*)
            FROM #src
            WHERE Turno_Evaluable_TA IS NULL
               OR Turno_Evaluable_TB IS NULL
        );

END;
