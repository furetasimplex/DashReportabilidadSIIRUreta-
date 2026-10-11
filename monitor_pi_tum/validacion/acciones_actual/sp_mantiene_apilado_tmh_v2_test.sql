CREATE PROCEDURE [inventar_SpcHidr].[sp_mantiene_apilado_tmh_v2_test]
(
    @FechaInicio    date,
    @FechaFin       date,
    @DiasReproceso  int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    /* ============================================================
       VALIDACIONES
       ============================================================ */

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50901, 'Debe informar @FechaInicio y @FechaFin.', 1;

    IF @FechaInicio > @FechaFin
        THROW 50902, 'La fecha inicial no puede ser mayor que la fecha final.', 1;

    IF @DiasReproceso IS NULL OR @DiasReproceso < 0
        THROW 50903, '@DiasReproceso debe ser mayor o igual que cero.', 1;

    IF OBJECT_ID(
        'inventar_SpcHidr.Control_Apilado_TMH_v2_test',
        'U'
    ) IS NULL
        THROW 50904,
              'No existe la tabla Control_Apilado_TMH_v2_test.',
              1;


    /* ============================================================
       CORTE DE METODOLOGÍA

       Antes:
           metodología histórica exacta desde tot_TM.

       Desde:
           resolver oficial PI / TUM.
       ============================================================ */

    DECLARE @FechaCorteTUM date = '2026-09-01';


    /* ============================================================
       VENTANA DE REPROCESO

       Se conserva exactamente el comportamiento vigente.
       ============================================================ */

    DECLARE @FechaInicioVentana date =
        CASE
            WHEN DATEADD(
                    DAY,
                    -(@DiasReproceso - 1),
                    @FechaFin
                 ) > @FechaInicio
            THEN DATEADD(
                    DAY,
                    -(@DiasReproceso - 1),
                    @FechaFin
                 )
            ELSE @FechaInicio
        END;


    DECLARE @FechaCalculo datetime2(7) = SYSDATETIME();


    /* ============================================================
       1. FECHAS A PROCESAR

       Histórico:
           fechas existentes en tot_TM.

       Desde 01-09-2026:
           tot_TM
           UNION
           fechas presentes en resolver PI/TUM.

       Esto permite materializar un día con TUM aunque PI/tot_TM
       esté completamente ausente.
       ============================================================ */

    DROP TABLE IF EXISTS #fechas;

    ;WITH fechas_candidatas AS
    (
        /* --------------------------------------------------------
           Universo histórico / PI
           -------------------------------------------------------- */
        SELECT DISTINCT
            CAST(t.fecha AS date) AS Fecha
        FROM inventar_SpcHidr.tot_TM AS t
        WHERE t.fecha >= @FechaInicio
          AND t.fecha < DATEADD(DAY, 1, @FechaFin)


        UNION


        /* --------------------------------------------------------
           Universo adicional de contingencia TUM
           -------------------------------------------------------- */
        SELECT DISTINCT
            r.fecha_operacional AS Fecha
        FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test AS r
      
        WHERE r.fecha_operacional >= @FechaInicio
          AND r.fecha_operacional <= @FechaFin
          AND r.fecha_operacional >= @FechaCorteTUM
          AND r.equipo_codigo IN
          (
              'PRINCIPAL_CV008',
              'PRINCIPAL_CV108'
          )
    )

    SELECT
        fc.Fecha
    INTO #fechas
    FROM fechas_candidatas AS fc
    WHERE
        fc.Fecha >= @FechaInicioVentana

        OR NOT EXISTS
        (
            SELECT 1
            FROM inventar_SpcHidr.Control_Apilado_TMH_v2_test AS c
            WHERE c.Fecha = fc.Fecha
        );


    CREATE UNIQUE CLUSTERED INDEX IX_fechas
        ON #fechas(Fecha);


    IF NOT EXISTS (SELECT 1 FROM #fechas)
    BEGIN
        PRINT
        'sp_mantiene_apilado_tmh_v2_test: nada que reprocesar, todo el rango ya estaba vigente.';

        RETURN;
    END;


    /* ============================================================
       2. TABLA TEMPORAL DE RESULTADO

       Mantiene exactamente el contrato de la tabla persistida.
       ============================================================ */

    DROP TABLE IF EXISTS #resultado;

    CREATE TABLE #resultado
    (
        Fecha date NOT NULL,

        ts_08_dia datetime2 NULL,
        ts_20_dia datetime2 NULL,
        ts_08_dia_siguiente datetime2 NULL,

        CV008_Totalizador_08 float NULL,
        CV008_Totalizador_20 float NULL,
        CV008_Totalizador_08_Dia_Siguiente float NULL,

        CV108_Totalizador_08 float NULL,
        CV108_Totalizador_20 float NULL,
        CV108_Totalizador_08_Dia_Siguiente float NULL,

        TMH_CV008_A_Bruto float NULL,
        TMH_CV008_B_Bruto float NULL,
        TMH_CV108_A_Bruto float NULL,
        TMH_CV108_B_Bruto float NULL,

        Flag_Apilado_Valido bit NULL,

        TMH_CV008_A float NULL,
        TMH_CV008_B float NULL,
        TMH_CV108_A float NULL,
        TMH_CV108_B float NULL,

        TMH_Apilado_Total_A float NULL,
        TMH_Apilado_Total_B float NULL,
        TMH_Apilado_Total_Dia float NULL,

        Flag_Apilado_Valido_A bit NULL,
        Flag_Apilado_Valido_B bit NULL,

        Fecha_Calculo datetime2(7) NULL
    );


    /* ============================================================
       3. HISTÓRICO ANTES DEL 01-09-2026

       LÓGICA PRODUCTIVA ANTERIOR SIN CAMBIOS.
       ============================================================ */

    ;WITH marcas AS
    (
        SELECT
            f.Fecha,

            CAST(
                DATEADD(
                    HOUR,
                    8,
                    CAST(f.Fecha AS datetime2)
                )
                AS datetime2
            ) AS ts_08_dia,

            CAST(
                DATEADD(
                    HOUR,
                    20,
                    CAST(f.Fecha AS datetime2)
                )
                AS datetime2
            ) AS ts_20_dia,

            CAST(
                DATEADD(
                    HOUR,
                    8,
                    DATEADD(
                        DAY,
                        1,
                        CAST(f.Fecha AS datetime2)
                    )
                )
                AS datetime2
            ) AS ts_08_dia_siguiente

        FROM #fechas AS f

        WHERE f.Fecha < @FechaCorteTUM
    ),

    totales AS
    (
        SELECT
            m.Fecha,

            m.ts_08_dia,
            m.ts_20_dia,
            m.ts_08_dia_siguiente,

            CAST(t08.tot_008 AS float)
                AS CV008_Totalizador_08,

            CAST(t20.tot_008 AS float)
                AS CV008_Totalizador_20,

            CAST(t08s.tot_008 AS float)
                AS CV008_Totalizador_08_Dia_Siguiente,

            CAST(t08.tot_108 AS float)
                AS CV108_Totalizador_08,

            CAST(t20.tot_108 AS float)
                AS CV108_Totalizador_20,

            CAST(t08s.tot_108 AS float)
                AS CV108_Totalizador_08_Dia_Siguiente

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

            CV008_Totalizador_20
            - CV008_Totalizador_08
                AS TMH_CV008_A_Bruto,

            CV008_Totalizador_08_Dia_Siguiente
            - CV008_Totalizador_20
                AS TMH_CV008_B_Bruto,

            CV108_Totalizador_20
            - CV108_Totalizador_08
                AS TMH_CV108_A_Bruto,

            CV108_Totalizador_08_Dia_Siguiente
            - CV108_Totalizador_20
                AS TMH_CV108_B_Bruto

        FROM totales
    ),

    validacion AS
    (
        SELECT
            *,

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

            TMH_CV008_A_Valido
            + TMH_CV108_A_Valido
                AS TMH_Total_A_Valido,

            TMH_CV008_B_Valido
            + TMH_CV108_B_Valido
                AS TMH_Total_B_Valido,

            CASE
                WHEN TMH_CV008_A_Valido
                   + TMH_CV108_A_Valido > 100
                    THEN 1
                ELSE 0
            END AS Flag_Apilado_Valido_A,

            CASE
                WHEN TMH_CV008_B_Valido
                   + TMH_CV108_B_Valido > 100
                    THEN 1
                ELSE 0
            END AS Flag_Apilado_Valido_B

        FROM validacion
    )

    INSERT INTO #resultado
    (
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

        Flag_Apilado_Valido,

        TMH_CV008_A,
        TMH_CV008_B,
        TMH_CV108_A,
        TMH_CV108_B,

        TMH_Apilado_Total_A,
        TMH_Apilado_Total_B,
        TMH_Apilado_Total_Dia,

        Flag_Apilado_Valido_A,
        Flag_Apilado_Valido_B,

        Fecha_Calculo
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

        CAST
        (
            CASE
                WHEN Flag_Apilado_Valido_A = 1
                 AND Flag_Apilado_Valido_B = 1
                    THEN 1
                ELSE 0
            END
            AS bit
        ),

        CASE
            WHEN Flag_Apilado_Valido_A = 1
                THEN TMH_CV008_A_Valido
            ELSE 0
        END,

        CASE
            WHEN Flag_Apilado_Valido_B = 1
                THEN TMH_CV008_B_Valido
            ELSE 0
        END,

        CASE
            WHEN Flag_Apilado_Valido_A = 1
                THEN TMH_CV108_A_Valido
            ELSE 0
        END,

        CASE
            WHEN Flag_Apilado_Valido_B = 1
                THEN TMH_CV108_B_Valido
            ELSE 0
        END,

        CASE
            WHEN Flag_Apilado_Valido_A = 1
                THEN TMH_Total_A_Valido
            ELSE 0
        END,

        CASE
            WHEN Flag_Apilado_Valido_B = 1
                THEN TMH_Total_B_Valido
            ELSE 0
        END,

        (
            CASE
                WHEN Flag_Apilado_Valido_A = 1
                    THEN TMH_Total_A_Valido
                ELSE 0
            END
        )
        +
        (
            CASE
                WHEN Flag_Apilado_Valido_B = 1
                    THEN TMH_Total_B_Valido
                ELSE 0
            END
        ),

        CAST(Flag_Apilado_Valido_A AS bit),
        CAST(Flag_Apilado_Valido_B AS bit),

        @FechaCalculo

    FROM validacion_turno;


/* ============================================================
   4. DESDE 01-09-2026

   RESOLUCIÓN OPERACIONAL PI / TUM - DEV.

   No se vuelve a decidir aquí si corresponde PI o TUM:
   esa decisión ya pertenece exclusivamente a
   v_contingencia_totalizador_resuelto_operacional_test.

   valor_bruto_resuelto:
       valor previo a la regla <=100.

   valor_final_resuelto:
       PI/TUM ya resuelto y regla <=100 aplicada.

   PENDIENTE_PI / PENDIENTE_TUM:
       valor_final_resuelto = NULL.
   ============================================================ */

    ;WITH resolver AS
    (
        SELECT
            f.Fecha,

            r.turno,
            r.equipo_codigo,

            r.lectura_inicio_pi,
            r.lectura_fin_pi,

            r.valor_bruto_resuelto,
            r.valor_final_resuelto,

            r.fuente_resuelta

        FROM #fechas AS f

        LEFT JOIN
           inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test
                AS r
            ON r.fecha_operacional = f.Fecha
           AND r.equipo_codigo IN
           (
               'PRINCIPAL_CV008',
               'PRINCIPAL_CV108'
           )

        WHERE f.Fecha >= @FechaCorteTUM
    ),

    p AS
    (
        SELECT
            Fecha,

            /* ====================================================
               FRONTERAS PI - TRAZABILIDAD
               ==================================================== */

            MAX
            (
                CASE
                    WHEN turno = 'A'
                     AND equipo_codigo = 'PRINCIPAL_CV008'
                        THEN lectura_inicio_pi
                END
            ) AS CV008_08,

            COALESCE
            (
                MAX
                (
                    CASE
                        WHEN turno = 'A'
                         AND equipo_codigo = 'PRINCIPAL_CV008'
                            THEN lectura_fin_pi
                    END
                ),

                MAX
                (
                    CASE
                        WHEN turno = 'B'
                         AND equipo_codigo = 'PRINCIPAL_CV008'
                            THEN lectura_inicio_pi
                    END
                )
            ) AS CV008_20,

            MAX
            (
                CASE
                    WHEN turno = 'B'
                     AND equipo_codigo = 'PRINCIPAL_CV008'
                        THEN lectura_fin_pi
                END
            ) AS CV008_08_SIG,


            MAX
            (
                CASE
                    WHEN turno = 'A'
                     AND equipo_codigo = 'PRINCIPAL_CV108'
                        THEN lectura_inicio_pi
                END
            ) AS CV108_08,

            COALESCE
            (
                MAX
                (
                    CASE
                        WHEN turno = 'A'
                         AND equipo_codigo = 'PRINCIPAL_CV108'
                            THEN lectura_fin_pi
                    END
                ),

                MAX
                (
                    CASE
                        WHEN turno = 'B'
                         AND equipo_codigo = 'PRINCIPAL_CV108'
                            THEN lectura_inicio_pi
                    END
                )
            ) AS CV108_20,

            MAX
            (
                CASE
                    WHEN turno = 'B'
                     AND equipo_codigo = 'PRINCIPAL_CV108'
                        THEN lectura_fin_pi
                END
            ) AS CV108_08_SIG,


            /* ====================================================
               BRUTOS RESUELTOS
               ==================================================== */

            MAX
            (
                CASE
                    WHEN turno = 'A'
                     AND equipo_codigo = 'PRINCIPAL_CV008'
                        THEN valor_bruto_resuelto
                END
            ) AS CV008_A_BRUTO,

            MAX
            (
                CASE
                    WHEN turno = 'B'
                     AND equipo_codigo = 'PRINCIPAL_CV008'
                        THEN valor_bruto_resuelto
                END
            ) AS CV008_B_BRUTO,

            MAX
            (
                CASE
                    WHEN turno = 'A'
                     AND equipo_codigo = 'PRINCIPAL_CV108'
                        THEN valor_bruto_resuelto
                END
            ) AS CV108_A_BRUTO,

            MAX
            (
                CASE
                    WHEN turno = 'B'
                     AND equipo_codigo = 'PRINCIPAL_CV108'
                        THEN valor_bruto_resuelto
                END
            ) AS CV108_B_BRUTO,


            /* ====================================================
               FINALES RESUELTOS
               ==================================================== */

            MAX
            (
                CASE
                    WHEN turno = 'A'
                     AND equipo_codigo = 'PRINCIPAL_CV008'
                        THEN valor_final_resuelto
                END
            ) AS CV008_A_FINAL,

            MAX
            (
                CASE
                    WHEN turno = 'B'
                     AND equipo_codigo = 'PRINCIPAL_CV008'
                        THEN valor_final_resuelto
                END
            ) AS CV008_B_FINAL,

            MAX
            (
                CASE
                    WHEN turno = 'A'
                     AND equipo_codigo = 'PRINCIPAL_CV108'
                        THEN valor_final_resuelto
                END
            ) AS CV108_A_FINAL,

            MAX
            (
                CASE
                    WHEN turno = 'B'
                     AND equipo_codigo = 'PRINCIPAL_CV108'
                        THEN valor_final_resuelto
                END
            ) AS CV108_B_FINAL

        FROM resolver

        GROUP BY Fecha
    ),

    evaluacion AS
    (
        SELECT
            *,

            /* ----------------------------------------------------
               Turno A está resuelto sólo si ambas correas tienen
               una resolución explícita.

               NULL no se transforma en cero.
               ---------------------------------------------------- */

            CASE
                WHEN CV008_A_FINAL IS NULL
                  OR CV108_A_FINAL IS NULL
                    THEN 0

                WHEN CV008_A_FINAL + CV108_A_FINAL > 100
                    THEN 1

                ELSE 0
            END AS Flag_A,


            CASE
                WHEN CV008_B_FINAL IS NULL
                  OR CV108_B_FINAL IS NULL
                    THEN 0

                WHEN CV008_B_FINAL + CV108_B_FINAL > 100
                    THEN 1

                ELSE 0
            END AS Flag_B,


            CASE
                WHEN CV008_A_FINAL IS NULL
                  OR CV108_A_FINAL IS NULL
                    THEN 0
                ELSE 1
            END AS Resuelto_A,


            CASE
                WHEN CV008_B_FINAL IS NULL
                  OR CV108_B_FINAL IS NULL
                    THEN 0
                ELSE 1
            END AS Resuelto_B

        FROM p
    )

    INSERT INTO #resultado
    (
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

        Flag_Apilado_Valido,

        TMH_CV008_A,
        TMH_CV008_B,
        TMH_CV108_A,
        TMH_CV108_B,

        TMH_Apilado_Total_A,
        TMH_Apilado_Total_B,
        TMH_Apilado_Total_Dia,

        Flag_Apilado_Valido_A,
        Flag_Apilado_Valido_B,

        Fecha_Calculo
    )

    SELECT
        Fecha,

        CAST(
            DATEADD(HOUR, 8, CAST(Fecha AS datetime2))
            AS datetime2
        ),

        CAST(
            DATEADD(HOUR, 20, CAST(Fecha AS datetime2))
            AS datetime2
        ),

        CAST(
            DATEADD(
                HOUR,
                8,
                DATEADD(DAY, 1, CAST(Fecha AS datetime2))
            )
            AS datetime2
        ),


        CAST(CV008_08 AS float),
        CAST(CV008_20 AS float),
        CAST(CV008_08_SIG AS float),

        CAST(CV108_08 AS float),
        CAST(CV108_20 AS float),
        CAST(CV108_08_SIG AS float),


        CAST(CV008_A_BRUTO AS float),
        CAST(CV008_B_BRUTO AS float),

        CAST(CV108_A_BRUTO AS float),
        CAST(CV108_B_BRUTO AS float),


        CAST
        (
            CASE
                WHEN Flag_A = 1
                 AND Flag_B = 1
                    THEN 1
                ELSE 0
            END
            AS bit
        ),


        /* --------------------------------------------------------
           TURNO A

           SIN_RESOLVER -> NULL
           Resuelto pero turno no válido -> 0
           Resuelto y válido -> valor final
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN Resuelto_A = 0
                    THEN NULL

                WHEN Flag_A = 1
                    THEN CV008_A_FINAL

                ELSE 0
            END
            AS float
        ),


        /* --------------------------------------------------------
           TURNO B - CV008
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN Resuelto_B = 0
                    THEN NULL

                WHEN Flag_B = 1
                    THEN CV008_B_FINAL

                ELSE 0
            END
            AS float
        ),


        /* --------------------------------------------------------
           TURNO A - CV108
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN Resuelto_A = 0
                    THEN NULL

                WHEN Flag_A = 1
                    THEN CV108_A_FINAL

                ELSE 0
            END
            AS float
        ),


        /* --------------------------------------------------------
           TURNO B - CV108
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN Resuelto_B = 0
                    THEN NULL

                WHEN Flag_B = 1
                    THEN CV108_B_FINAL

                ELSE 0
            END
            AS float
        ),


        /* --------------------------------------------------------
           TOTAL A
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN Resuelto_A = 0
                    THEN NULL

                WHEN Flag_A = 1
                    THEN CV008_A_FINAL + CV108_A_FINAL

                ELSE 0
            END
            AS float
        ),


        /* --------------------------------------------------------
           TOTAL B
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN Resuelto_B = 0
                    THEN NULL

                WHEN Flag_B = 1
                    THEN CV008_B_FINAL + CV108_B_FINAL

                ELSE 0
            END
            AS float
        ),


        /* --------------------------------------------------------
           TOTAL DÍA

           Si algún turno está SIN_RESOLVER:
               NULL.

           Si ambos están resueltos:
               se conserva la suma operacional vigente.
           -------------------------------------------------------- */

        CAST
        (
            CASE
                WHEN Resuelto_A = 0
                  OR Resuelto_B = 0
                    THEN NULL

                ELSE
                    CASE
                        WHEN Flag_A = 1
                            THEN CV008_A_FINAL + CV108_A_FINAL
                        ELSE 0
                    END

                    +

                    CASE
                        WHEN Flag_B = 1
                            THEN CV008_B_FINAL + CV108_B_FINAL
                        ELSE 0
                    END
            END
            AS float
        ),


        CAST(Flag_A AS bit),
        CAST(Flag_B AS bit),

        @FechaCalculo

    FROM evaluacion;


    /* ============================================================
       5. MERGE HACIA EL CONTROL OFICIAL DEV
       ============================================================ */

    MERGE
        inventar_SpcHidr.Control_Apilado_TMH_v2_test
        WITH (HOLDLOCK) AS tgt

    USING #resultado AS src
        ON tgt.Fecha = src.Fecha

    WHEN MATCHED THEN
        UPDATE SET

            ts_08_dia =
                src.ts_08_dia,

            ts_20_dia =
                src.ts_20_dia,

            ts_08_dia_siguiente =
                src.ts_08_dia_siguiente,

            CV008_Totalizador_08 =
                src.CV008_Totalizador_08,

            CV008_Totalizador_20 =
                src.CV008_Totalizador_20,

            CV008_Totalizador_08_Dia_Siguiente =
                src.CV008_Totalizador_08_Dia_Siguiente,

            CV108_Totalizador_08 =
                src.CV108_Totalizador_08,

            CV108_Totalizador_20 =
                src.CV108_Totalizador_20,

            CV108_Totalizador_08_Dia_Siguiente =
                src.CV108_Totalizador_08_Dia_Siguiente,

            TMH_CV008_A_Bruto =
                src.TMH_CV008_A_Bruto,

            TMH_CV008_B_Bruto =
                src.TMH_CV008_B_Bruto,

            TMH_CV108_A_Bruto =
                src.TMH_CV108_A_Bruto,

            TMH_CV108_B_Bruto =
                src.TMH_CV108_B_Bruto,

            Flag_Apilado_Valido =
                src.Flag_Apilado_Valido,

            TMH_CV008_A =
                src.TMH_CV008_A,

            TMH_CV008_B =
                src.TMH_CV008_B,

            TMH_CV108_A =
                src.TMH_CV108_A,

            TMH_CV108_B =
                src.TMH_CV108_B,

            TMH_Apilado_Total_A =
                src.TMH_Apilado_Total_A,

            TMH_Apilado_Total_B =
                src.TMH_Apilado_Total_B,

            TMH_Apilado_Total_Dia =
                src.TMH_Apilado_Total_Dia,

            Flag_Apilado_Valido_A =
                src.Flag_Apilado_Valido_A,

            Flag_Apilado_Valido_B =
                src.Flag_Apilado_Valido_B,

            Fecha_Calculo =
                src.Fecha_Calculo


    WHEN NOT MATCHED BY TARGET THEN
        INSERT
        (
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

            Flag_Apilado_Valido,

            TMH_CV008_A,
            TMH_CV008_B,

            TMH_CV108_A,
            TMH_CV108_B,

            TMH_Apilado_Total_A,
            TMH_Apilado_Total_B,
            TMH_Apilado_Total_Dia,

            Flag_Apilado_Valido_A,
            Flag_Apilado_Valido_B,

            Fecha_Calculo
        )

        VALUES
        (
            src.Fecha,

            src.ts_08_dia,
            src.ts_20_dia,
            src.ts_08_dia_siguiente,

            src.CV008_Totalizador_08,
            src.CV008_Totalizador_20,
            src.CV008_Totalizador_08_Dia_Siguiente,

            src.CV108_Totalizador_08,
            src.CV108_Totalizador_20,
            src.CV108_Totalizador_08_Dia_Siguiente,

            src.TMH_CV008_A_Bruto,
            src.TMH_CV008_B_Bruto,

            src.TMH_CV108_A_Bruto,
            src.TMH_CV108_B_Bruto,

            src.Flag_Apilado_Valido,

            src.TMH_CV008_A,
            src.TMH_CV008_B,

            src.TMH_CV108_A,
            src.TMH_CV108_B,

            src.TMH_Apilado_Total_A,
            src.TMH_Apilado_Total_B,
            src.TMH_Apilado_Total_Dia,

            src.Flag_Apilado_Valido_A,
            src.Flag_Apilado_Valido_B,

            src.Fecha_Calculo
        );


    DECLARE @FilasAfectadas int = @@ROWCOUNT;


    PRINT
        'sp_mantiene_apilado_tmh_v2_test finalizado.';

    PRINT
        'Metodologia: historico tot_TM antes de 2026-09-01; PI/TUM resuelto desde 2026-09-01.';

    PRINT
        'Ventana de reproceso obligatorio: '
        + CONVERT(varchar(10), @FechaInicioVentana, 120)
        + ' a '
        + CONVERT(varchar(10), @FechaFin, 120);

    PRINT
        'Filas insertadas/actualizadas: '
        + CONVERT(varchar(20), @FilasAfectadas);

END;
