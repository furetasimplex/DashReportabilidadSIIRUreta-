CREATE PROCEDURE

    [inventar_SpcHidr].[sp_refrescar_clays_cufe]

(

    @FechaInicio date = NULL,

    @FechaFin date = NULL,

    @SoloVistaPrevia bit = 1

)

AS

BEGIN

    SET NOCOUNT ON;

    SET XACT_ABORT ON;



    /* ========================================================

       CONFIGURACIÓN Y FECHAS

       ======================================================== */



    DECLARE @FechaCorteProtegida date = '20260801';



    DECLARE @FechaFinEfectiva date;



    DECLARE @FechaInicioSolicitada date;



    DECLARE @FechaInicioEfectiva date;



    DECLARE @IdEjecucion uniqueidentifier = NEWID();



    DECLARE @FechaProceso datetime2(3) = SYSDATETIME();



    SET @FechaFinEfectiva =

        ISNULL

        (

            @FechaFin,

            DATEADD

            (

                DAY,

                -1,

                CONVERT(date, GETDATE())

            )

        );



    SET @FechaInicioSolicitada =

        ISNULL

        (

            @FechaInicio,

            DATEADD

            (

                DAY,

                -7,

                @FechaFinEfectiva

            )

        );



    SET @FechaInicioEfectiva =

        CASE

            WHEN @FechaInicioSolicitada < @FechaCorteProtegida

                THEN @FechaCorteProtegida

            ELSE @FechaInicioSolicitada

        END;



    /* ========================================================

       VALIDACIONES

       ======================================================== */



    IF OBJECT_ID

    (

        N'[inventar_SpcHidr].[v_clays_cufe_calculado_v2_test]',

        N'V'

    ) IS NULL

    BEGIN

        THROW 50001,

            'No existe la vista v_clays_cufe_calculado_v2_test.',

            1;

    END;



    IF OBJECT_ID

    (

        N'[inventar_SpcHidr].[Clays_CuFe]',

        N'U'

    ) IS NULL

    BEGIN

        THROW 50002,

            'No existe la tabla Clays_CuFe.',

            1;

    END;



    IF @SoloVistaPrevia = 0

       AND OBJECT_ID

       (

           N'[inventar_SpcHidr].[Clays_CuFe_trazabilidad]',

           N'U'

       ) IS NULL

    BEGIN

        THROW 50003,

            'No existe la tabla Clays_CuFe_trazabilidad.',

            1;

    END;



    IF @FechaFinEfectiva < @FechaCorteProtegida

    BEGIN

        THROW 50004,

            'El período solicitado termina antes del corte protegido 01-08-2026.',

            1;

    END;



    IF @FechaInicioEfectiva > @FechaFinEfectiva

    BEGIN

        THROW 50005,

            'La fecha inicial efectiva es posterior a la fecha final.',

            1;

    END;



    DROP TABLE IF EXISTS #fuente;

    DROP TABLE IF EXISTS #destino;

    DROP TABLE IF EXISTS #acciones;



    /* ========================================================

       FUENTE CALCULADA

       ======================================================== */



    SELECT

        v.Fecha,

        v.Turno,

        v.Torre,



        CASE

            WHEN v.Torre = 'TM1' THEN 'TM-1'

            WHEN v.Torre = 'TM2' THEN 'TM-2'

        END AS Torre_Destino,



        CASE

            WHEN v.Turno = 'A' THEN 'TA'

            WHEN v.Turno = 'B' THEN 'TB'

        END AS Turno_Destino,



        v.Representatividad_Quimica,

        v.Representatividad_Quimica_TM2,



        v.ID_NIR,

        v.Muestra_NIR,

        v.CaolBeta_NIR,

        v.Fecha_Carga_NIR,

        v.Cantidad_Registros_NIR,



        v.ID_NIR_TM2,

        v.Muestra_NIR_TM2,

        v.CaolBeta_NIR_TM2,

        v.Fecha_Carga_NIR_TM2,



        v.CaolBeta_MB,

        v.CaolBeta_Final,



        CAST

        (

            v.CaolBeta_Final_2D

            AS decimal(18,2)

        ) AS CaolBeta_Nuevo,



        v.Fuente_CaolBeta,



        v.ID_Registro_CuFe,

        v.CuFe_Laboratorio,

        v.Fecha_Carga_Laboratorio,

        v.Cantidad_Registros_Laboratorio,



        v.ID_Registro_CuFe_TM2,

        v.CuFe_Laboratorio_TM2,

        v.Fecha_Carga_Laboratorio_TM2,



        v.CuFe_MB,

        v.CuFe_Final,



        CAST

        (

            v.CuFe_Final_2D

            AS decimal(18,2)

        ) AS CuFe_Nuevo,



        v.Fuente_CuFe,

        v.Cantidad_Registros_MB



    INTO #fuente



    FROM

        [inventar_SpcHidr].[v_clays_cufe_calculado_v2_test] AS v



    WHERE

        v.Fecha BETWEEN

            @FechaInicioEfectiva

            AND @FechaFinEfectiva



        AND

        (

            v.CaolBeta_Final_2D IS NOT NULL

            OR v.CuFe_Final_2D IS NOT NULL

        );



    /* ========================================================

       CONTROL DE DUPLICADOS EN LA FUENTE

       ======================================================== */



    IF EXISTS

    (

        SELECT

            Fecha,

            Turno,

            Torre

        FROM #fuente

        GROUP BY

            Fecha,

            Turno,

            Torre

        HAVING COUNT(*) > 1

    )

    BEGIN

        THROW 50006,

            'La vista calculada contiene claves duplicadas.',

            1;

    END;



    /* ========================================================

       DESTINO ACTUAL NORMALIZADO

       ======================================================== */



    SELECT

        c.Fecha,



        c.Torre AS Torre_Original,

        c.Turno AS Turno_Original,



        CASE

            WHEN norm.Torre_Normalizada

                 IN ('TM1', 'T1', 'TORRE1')

                THEN 'TM1'



            WHEN norm.Torre_Normalizada

                 IN ('TM2', 'T2', 'TORRE2')

                THEN 'TM2'

        END AS Torre,



        CASE

            WHEN norm.Turno_Normalizado

                 IN ('A', 'TA', 'TURNOA')

                THEN 'A'



            WHEN norm.Turno_Normalizado

                 IN ('B', 'TB', 'TURNOB')

                THEN 'B'

        END AS Turno,



        TRY_CONVERT

        (

            decimal(18,2),

            c.CaolBeta

        ) AS CaolBeta_Anterior,



        TRY_CONVERT

        (

            decimal(18,2),

            c.CuFe

        ) AS CuFe_Anterior,

        hist.Fuente_CaolBeta
            AS Fuente_CaolBeta_Anterior,

        hist.Fuente_CuFe
            AS Fuente_CuFe_Anterior



    INTO #destino



    FROM

        [inventar_SpcHidr].[Clays_CuFe] AS c



    CROSS APPLY

    (

        VALUES

        (

            REPLACE

            (

                REPLACE

                (

                    REPLACE

                    (

                        UPPER

                        (

                            LTRIM

                            (

                                RTRIM

                                (

                                    ISNULL(c.Torre, '')

                                )

                            )

                        ),

                        ' ',

                        ''

                    ),

                    '-',

                    ''

                ),

                '_',

                ''

            ),



            REPLACE

            (

                REPLACE

                (

                    REPLACE

                    (

                        UPPER

                        (

                            LTRIM

                            (

                                RTRIM

                                (

                                    ISNULL(c.Turno, '')

                                )

                            )

                        ),

                        ' ',

                        ''

                    ),

                    '-',

                    ''

                ),

                '_',

                ''

            )

        )

    ) AS norm

    (

        Torre_Normalizada,

        Turno_Normalizado

    )

    OUTER APPLY
    (
        SELECT TOP (1)
            t.Fuente_CaolBeta,
            t.Fuente_CuFe
        FROM [inventar_SpcHidr].[Clays_CuFe_trazabilidad] AS t
        WHERE t.Fecha = c.Fecha
          AND t.Torre = CASE
                WHEN norm.Torre_Normalizada IN ('TM1', 'T1', 'TORRE1') THEN 'TM1'
                WHEN norm.Torre_Normalizada IN ('TM2', 'T2', 'TORRE2') THEN 'TM2'
              END
          AND t.Turno = CASE
                WHEN norm.Turno_Normalizado IN ('A', 'TA', 'TURNOA') THEN 'A'
                WHEN norm.Turno_Normalizado IN ('B', 'TB', 'TURNOB') THEN 'B'
              END
        ORDER BY t.fecha_proceso DESC, t.id_trazabilidad DESC
    ) AS hist



    WHERE

        c.Fecha BETWEEN

            @FechaInicioEfectiva

            AND @FechaFinEfectiva;



    /* ========================================================

       CONTROL DE DUPLICADOS EN CLAYS_CUFE

       ======================================================== */



    IF EXISTS

    (

        SELECT

            Fecha,

            Turno,

            Torre

        FROM #destino

        WHERE

            Turno IS NOT NULL

            AND Torre IS NOT NULL

        GROUP BY

            Fecha,

            Turno,

            Torre

        HAVING COUNT(*) > 1

    )

    BEGIN

        THROW 50007,

            'Clays_CuFe contiene claves duplicadas en el período solicitado.',

            1;

    END;



    /* ========================================================

       CLASIFICACIÓN DE ACCIONES

       ======================================================== */



    SELECT

        f.*,



        d.CaolBeta_Anterior,

        d.CuFe_Anterior,

        d.Fuente_CaolBeta_Anterior,
        d.Fuente_CuFe_Anterior,



        CASE

            WHEN d.Fecha IS NULL

                THEN 'INSERTAR'



            WHEN

            (

                f.CaolBeta_Nuevo IS NOT NULL

                AND

                (

                    d.CaolBeta_Anterior IS NULL

                    OR d.CaolBeta_Anterior <> f.CaolBeta_Nuevo

                )

            )

            OR

            (

                f.CuFe_Nuevo IS NOT NULL

                AND

                (

                    d.CuFe_Anterior IS NULL

                    OR d.CuFe_Anterior <> f.CuFe_Nuevo

                )

            )

                THEN 'ACTUALIZAR'



            WHEN
            (
                d.Fuente_CaolBeta_Anterior IS NOT NULL
                AND ISNULL(d.Fuente_CaolBeta_Anterior, '') <> ISNULL(f.Fuente_CaolBeta, '')
            )
            OR
            (
                d.Fuente_CuFe_Anterior IS NOT NULL
                AND ISNULL(d.Fuente_CuFe_Anterior, '') <> ISNULL(f.Fuente_CuFe, '')
            )
                THEN 'TRAZABILIDAD'

            ELSE 'SIN_CAMBIO'

        END AS Accion



    INTO #acciones



    FROM #fuente AS f



    LEFT JOIN #destino AS d

        ON d.Fecha = f.Fecha

       AND d.Turno = f.Turno

       AND d.Torre = f.Torre;



    /* ========================================================

       VISTA PREVIA

       ======================================================== */



    IF @SoloVistaPrevia = 1

    BEGIN

        SELECT

            @IdEjecucion AS id_ejecucion,

            @FechaInicioSolicitada AS fecha_inicio_solicitada,

            @FechaInicioEfectiva AS fecha_inicio_efectiva,

            @FechaFinEfectiva AS fecha_fin_efectiva,

            @FechaCorteProtegida AS fecha_corte_protegida;



        SELECT

            Accion,

            COUNT(*) AS Cantidad

        FROM #acciones

        GROUP BY

            Accion

        ORDER BY

            Accion;



        SELECT

            Fecha,

            Turno,

            Torre,

            Accion,



            Representatividad_Quimica,

            Representatividad_Quimica_TM2,



            CaolBeta_Anterior,

            CaolBeta_Nuevo,

            Fuente_CaolBeta,



            CuFe_Anterior,

            CuFe_Nuevo,

            Fuente_CuFe



        FROM #acciones



        ORDER BY

            Fecha,

            Turno,

            Torre;



        RETURN;

    END;



    /* ========================================================

       EJECUCIÓN REAL

       ======================================================== */



    BEGIN TRY

        BEGIN TRANSACTION;



        DECLARE @ResultadoLock int;



        EXEC @ResultadoLock = sys.sp_getapplock

            @Resource =

                N'inventar_SpcHidr.sp_refrescar_clays_cufe',

            @LockMode = N'Exclusive',

            @LockOwner = N'Transaction',

            @LockTimeout = 10000;



        IF @ResultadoLock < 0

        BEGIN

            THROW 50008,

                'No fue posible obtener el bloqueo exclusivo del proceso.',

                1;

        END;



        /* ====================================================

           ACTUALIZACIÓN

           ==================================================== */



        UPDATE c

        SET

            c.CaolBeta =

                CASE

                    WHEN a.CaolBeta_Nuevo IS NOT NULL

                        THEN CONVERT(float, a.CaolBeta_Nuevo)

                    ELSE c.CaolBeta

                END,



            c.CuFe =

                CASE

                    WHEN a.CuFe_Nuevo IS NOT NULL

                        THEN CONVERT(float, a.CuFe_Nuevo)

                    ELSE c.CuFe

                END



        FROM

            [inventar_SpcHidr].[Clays_CuFe] AS c



        CROSS APPLY

        (

            VALUES

            (

                CASE

                    WHEN REPLACE

                    (

                        REPLACE

                        (

                            REPLACE

                            (

                                UPPER

                                (

                                    LTRIM

                                    (

                                        RTRIM

                                        (

                                            ISNULL(c.Torre, '')

                                        )

                                    )

                                ),

                                ' ',

                                ''

                            ),

                            '-',

                            ''

                        ),

                        '_',

                        ''

                    ) IN ('TM1', 'T1', 'TORRE1')

                        THEN 'TM1'



                    WHEN REPLACE

                    (

                        REPLACE

                        (

                            REPLACE

                            (

                                UPPER

                                (

                                    LTRIM

                                    (

                                        RTRIM

                                        (

                                            ISNULL(c.Torre, '')

                                        )

                                    )

                                ),

                                ' ',

                                ''

                            ),

                            '-',

                            ''

                        ),

                        '_',

                        ''

                    ) IN ('TM2', 'T2', 'TORRE2')

                        THEN 'TM2'

                END,



                CASE

                    WHEN REPLACE

                    (

                        REPLACE

                        (

                            REPLACE

                            (

                                UPPER

                                (

                                    LTRIM

                                    (

                                        RTRIM

                                        (

                                            ISNULL(c.Turno, '')

                                        )

                                    )

                                ),

                                ' ',

                                ''

                            ),

                            '-',

                            ''

                        ),

                        '_',

                        ''

                    ) IN ('A', 'TA', 'TURNOA')

                        THEN 'A'



                    WHEN REPLACE

                    (

                        REPLACE

                        (

                            REPLACE

                            (

                                UPPER

                                (

                                    LTRIM

                                    (

                                        RTRIM

                                        (

                                            ISNULL(c.Turno, '')

                                        )

                                    )

                                ),

                                ' ',

                                ''

                            ),

                            '-',

                            ''

                        ),

                        '_',

                        ''

                    ) IN ('B', 'TB', 'TURNOB')

                        THEN 'B'

                END

            )

        ) AS norm

        (

            Torre_Normalizada,

            Turno_Normalizado

        )



        INNER JOIN #acciones AS a

            ON a.Fecha = c.Fecha

           AND a.Torre = norm.Torre_Normalizada

           AND a.Turno = norm.Turno_Normalizado

           AND a.Accion = 'ACTUALIZAR';



        /* ====================================================

           INSERCIÓN

           ==================================================== */



        INSERT INTO

            [inventar_SpcHidr].[Clays_CuFe]

        (

            Fecha,

            Torre,

            Turno,

            Caolinita,

            Qz,

            CaolBeta,

            CuFe

        )

        SELECT

            a.Fecha,

            a.Torre_Destino,

            a.Turno_Destino,

            NULL,

            NULL,

            CONVERT(float, a.CaolBeta_Nuevo),

            CONVERT(float, a.CuFe_Nuevo)



        FROM #acciones AS a



        WHERE

            a.Accion = 'INSERTAR'

            AND

            (

                a.CaolBeta_Nuevo IS NOT NULL

                OR a.CuFe_Nuevo IS NOT NULL

            );



        /* ====================================================

           TRAZABILIDAD

           ==================================================== */



        INSERT INTO

            [inventar_SpcHidr].[Clays_CuFe_trazabilidad]

        (

            id_ejecucion,

            fecha_proceso,

            fecha_inicio_proceso,

            fecha_fin_proceso,

            accion,



            Fecha,

            Turno,

            Torre,



            Representatividad_Quimica,

            Representatividad_Quimica_TM2,



            ID_NIR,

            Muestra_NIR,

            CaolBeta_NIR,

            Fecha_Carga_NIR,



            ID_NIR_TM2,

            Muestra_NIR_TM2,

            CaolBeta_NIR_TM2,

            Fecha_Carga_NIR_TM2,



            CaolBeta_MB,

            CaolBeta_Final,

            CaolBeta_Final_2D,

            Fuente_CaolBeta,



            ID_Registro_CuFe,

            CuFe_Laboratorio,

            Fecha_Carga_Laboratorio,



            ID_Registro_CuFe_TM2,

            CuFe_Laboratorio_TM2,

            Fecha_Carga_Laboratorio_TM2,



            CuFe_MB,

            CuFe_Final,

            CuFe_Final_2D,

            Fuente_CuFe,



            CaolBeta_Anterior,

            CuFe_Anterior,



            usuario_ejecucion,

            host_ejecucion,

            aplicacion_ejecucion

        )

        SELECT

            @IdEjecucion,

            @FechaProceso,

            @FechaInicioEfectiva,

            @FechaFinEfectiva,

            a.Accion,



            a.Fecha,

            a.Turno,

            a.Torre,



            a.Representatividad_Quimica,

            a.Representatividad_Quimica_TM2,



            a.ID_NIR,

            a.Muestra_NIR,

            a.CaolBeta_NIR,

            a.Fecha_Carga_NIR,



            a.ID_NIR_TM2,

            a.Muestra_NIR_TM2,

            a.CaolBeta_NIR_TM2,

            a.Fecha_Carga_NIR_TM2,



            a.CaolBeta_MB,

            a.CaolBeta_Final,

            a.CaolBeta_Nuevo,

            a.Fuente_CaolBeta,



            a.ID_Registro_CuFe,

            a.CuFe_Laboratorio,

            a.Fecha_Carga_Laboratorio,



            a.ID_Registro_CuFe_TM2,

            a.CuFe_Laboratorio_TM2,

            a.Fecha_Carga_Laboratorio_TM2,



            a.CuFe_MB,

            a.CuFe_Final,

            a.CuFe_Nuevo,

            a.Fuente_CuFe,



            a.CaolBeta_Anterior,

            a.CuFe_Anterior,



            ORIGINAL_LOGIN(),

            HOST_NAME(),

            APP_NAME()



        FROM #acciones AS a



        WHERE

            a.Accion IN

            (

                'INSERTAR',

                'ACTUALIZAR',

                'TRAZABILIDAD'

            );



        COMMIT TRANSACTION;

    END TRY



    BEGIN CATCH

        IF @@TRANCOUNT > 0

            ROLLBACK TRANSACTION;



        THROW;

    END CATCH;



    /* ========================================================

       RESULTADO DE LA EJECUCIÓN

       ======================================================== */



    SELECT

        @IdEjecucion AS id_ejecucion,

        @FechaInicioEfectiva AS fecha_inicio_efectiva,

        @FechaFinEfectiva AS fecha_fin_efectiva,

        @FechaProceso AS fecha_proceso,



        SUM

        (

            CASE

                WHEN Accion = 'INSERTAR' THEN 1

                ELSE 0

            END

        ) AS Registros_Insertados,



        SUM

        (

            CASE

                WHEN Accion = 'ACTUALIZAR' THEN 1

                ELSE 0

            END

        ) AS Registros_Actualizados,

        SUM
        (
            CASE
                WHEN Accion = 'TRAZABILIDAD' THEN 1
                ELSE 0
            END
        ) AS Registros_Trazabilidad_Actualizada,



        SUM

        (

            CASE

                WHEN Accion = 'SIN_CAMBIO' THEN 1

                ELSE 0

            END

        ) AS Registros_Sin_Cambio



    FROM #acciones;



    SELECT

        Fecha,

        Turno,

        Torre,

        Accion,



        CaolBeta_Anterior,

        CaolBeta_Nuevo,

        Fuente_CaolBeta,



        CuFe_Anterior,

        CuFe_Nuevo,

        Fuente_CuFe



    FROM #acciones



    WHERE

        Accion IN

        (

            'INSERTAR',

            'ACTUALIZAR',

            'TRAZABILIDAD'

        )



    ORDER BY

        Fecha,

        Turno,

        Torre;

END;
