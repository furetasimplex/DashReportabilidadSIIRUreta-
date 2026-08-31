SET XACT_ABORT ON;
BEGIN TRANSACTION;

ALTER VIEW

    [inventar_SpcHidr].[v_clays_cufe_calculado_v2_test]

AS



/* ============================================================

   OBJETIVO

   ------------------------------------------------------------

   Resolver CaolBeta y CuFe por:



       Fecha + Turno + Torre



   FUENTES

   ------------------------------------------------------------

   Representatividad química:

       inventar_SpcHidr.representatividad_torres_resultado



   CaolBeta laboratorio:

       inventar_SpcHidr.NIR



   CuFe laboratorio:

       inventar_SpcHidr.Informe_TM_lab



   Modelo de bloques:

       inventar_SpcHidr.v_conciliacion_chancado_v2



   REGLA POR ANALITO

   ------------------------------------------------------------

   1. Laboratorio propio si:

          Representatividad química propia >= 0.75

          y existe resultado de laboratorio propio.



   2. Para TM1 únicamente:

          compartir el resultado de TM2 si

          Representatividad química TM2 >= 0.75

          y existe resultado de laboratorio TM2.



   3. En cualquier otro caso:

          utilizar modelo de bloques.



   4. Si no existe ninguna fuente:

          devolver NULL.



   IMPORTANTE

   ------------------------------------------------------------

   - El umbral se evalúa con precisión completa.

   - No se aplica ROUND antes de evaluar 0.75.

   - No se comparte TM1 hacia TM2.

   - CaolBeta y CuFe se resuelven independientemente.

   - Esta vista no modifica Clays_CuFe.

   ============================================================ */



WITH rep AS

(

    /* Convierte la tabla ancha de representatividad

       en Fecha + Turno + Torre. */

    SELECT

        r.Dia AS Fecha,

        x.Torre,

        x.Turno,



        CAST(

            x.Representatividad_Quimica

            AS decimal(18,10)

        ) AS Representatividad_Quimica



    FROM [inventar_SpcHidr].[representatividad_torres_resultado] AS r



    CROSS APPLY

    (

        VALUES

            ('TM1', 'A', r.TM1_TurnoA_Quimico),

            ('TM1', 'B', r.TM1_TurnoB_Quimico),

            ('TM2', 'A', r.TM2_TurnoA_Quimico),

            ('TM2', 'B', r.TM2_TurnoB_Quimico)

    ) AS x

    (

        Torre,

        Turno,

        Representatividad_Quimica

    )

),



/* ============================================================

   NIR: CaolBeta laboratorio

   ============================================================ */

nir_normalizado AS

(

    SELECT

        n.id,

        n.dia AS Fecha,



        CASE

            WHEN norm.Torre_Normalizada

                 IN ('TM1', 'T1', 'TORRE1')

                THEN 'TM1'



            WHEN norm.Torre_Normalizada

                 IN ('TM2', 'T2', 'TORRE2')

                THEN 'TM2'



            ELSE NULL

        END AS Torre,



        CASE

            WHEN norm.Turno_Normalizado

                 IN ('A', 'TA', 'TURNOA')

                THEN 'A'



            WHEN norm.Turno_Normalizado

                 IN ('B', 'TB', 'TURNOB')

                THEN 'B'



            ELSE NULL

        END AS Turno,



        n.muestra,



        CAST(n.caolbeta AS float)

            AS CaolBeta_NIR,



        n.fecha_carga



    FROM [inventar_SpcHidr].[NIR] AS n



    CROSS APPLY

    (

        VALUES

        (

            /* TM-1 / TM_1 / TM 1 / TM1 -> TM1 */

            REPLACE(

                REPLACE(

                    REPLACE(

                        UPPER(

                            LTRIM(

                                RTRIM(

                                    ISNULL(n.torre, '')

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



            /* TA / T-A / Turno A / A */

            REPLACE(

                REPLACE(

                    REPLACE(

                        UPPER(

                            LTRIM(

                                RTRIM(

                                    ISNULL(n.turno, '')

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

),



nir_ranked AS

(

    SELECT

        n.*,



        COUNT(*) OVER

        (

            PARTITION BY

                n.Fecha,

                n.Turno,

                n.Torre

        ) AS Cantidad_Registros_NIR,



        ROW_NUMBER() OVER

        (

            PARTITION BY

                n.Fecha,

                n.Turno,

                n.Torre



            ORDER BY

                ISNULL(

                    n.fecha_carga,

                    CONVERT(datetime2, '19000101')

                ) DESC,



                n.id DESC

        ) AS rn



    FROM nir_normalizado AS n



    WHERE n.Fecha IS NOT NULL

      AND n.Turno IS NOT NULL

      AND n.Torre IS NOT NULL

),



nir AS

(

    SELECT

        Fecha,

        Turno,

        Torre,



        id AS ID_NIR,

        muestra AS Muestra_NIR,

        CaolBeta_NIR,

        fecha_carga AS Fecha_Carga_NIR,

        Cantidad_Registros_NIR



    FROM nir_ranked



    WHERE rn = 1

),



/* ============================================================

   Informe TM: CuFe laboratorio

   ============================================================ */

lab_normalizado AS

(

    SELECT

        l.ID_Registro,

        l.Fecha,



        CASE

            WHEN norm.Torre_Normalizada

                 IN ('TM1', 'T1', 'TORRE1')

                THEN 'TM1'



            WHEN norm.Torre_Normalizada

                 IN ('TM2', 'T2', 'TORRE2')

                THEN 'TM2'



            ELSE NULL

        END AS Torre,



        CASE

            WHEN norm.Turno_Normalizado

                 IN ('A', 'TA', 'TURNOA')

                THEN 'A'



            WHEN norm.Turno_Normalizado

                 IN ('B', 'TB', 'TURNOB')

                THEN 'B'



            ELSE NULL

        END AS Turno,



        CAST(l.CuFe_Global AS float)

            AS CuFe_Laboratorio,



        l.Fecha_Carga AS Fecha_Carga_Laboratorio



    FROM [inventar_SpcHidr].[Informe_TM_lab] AS l



    CROSS APPLY

    (

        VALUES

        (

            REPLACE(

                REPLACE(

                    REPLACE(

                        UPPER(

                            LTRIM(

                                RTRIM(

                                    ISNULL(l.Torre, '')

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



            REPLACE(

                REPLACE(

                    REPLACE(

                        UPPER(

                            LTRIM(

                                RTRIM(

                                    ISNULL(l.Turno, '')

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



    WHERE l.Fecha IS NOT NULL

      AND l.CuFe_Global IS NOT NULL

),



lab_ranked AS

(

    SELECT

        l.*,



        COUNT(*) OVER

        (

            PARTITION BY

                l.Fecha,

                l.Turno,

                l.Torre

        ) AS Cantidad_Registros_Laboratorio,



        ROW_NUMBER() OVER

        (

            PARTITION BY

                l.Fecha,

                l.Turno,

                l.Torre



            ORDER BY

                ISNULL(

                    l.Fecha_Carga_Laboratorio,

                    CONVERT(datetime, '19000101')

                ) DESC,



                l.ID_Registro DESC

        ) AS rn



    FROM lab_normalizado AS l



    WHERE l.Turno IS NOT NULL

      AND l.Torre IS NOT NULL

),



lab AS

(

    SELECT

        Fecha,

        Turno,

        Torre,



        ID_Registro AS ID_Registro_CuFe,

        CuFe_Laboratorio,

        Fecha_Carga_Laboratorio,

        Cantidad_Registros_Laboratorio



    FROM lab_ranked



    WHERE rn = 1

),



/* ============================================================

   Modelo de bloques

   ============================================================ */

mb_base AS

(

    SELECT

        CAST(c.Fecha AS date) AS Fecha,



        CASE

            WHEN norm.Turno_Normalizado

                 IN ('A', 'TA', 'TURNOA')

                THEN 'A'



            WHEN norm.Turno_Normalizado

                 IN ('B', 'TB', 'TURNOB')

                THEN 'B'



            ELSE NULL

        END AS Turno,



        TRY_CONVERT(float, c.Clay_Beta)

            AS CaolBeta_MB,



        TRY_CONVERT(float, c.CuFe)

            AS CuFe_MB,

        UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato, ''))))
            AS Fuente_Conciliacion



    FROM [inventar_SpcHidr].[v_conciliacion_chancado_v2] AS c



    CROSS APPLY

    (

        VALUES

        (

            REPLACE(

                REPLACE(

                    REPLACE(

                        UPPER(

                            LTRIM(

                                RTRIM(

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

        Turno_Normalizado

    )



    WHERE c.Fecha IS NOT NULL

),



mb AS

(

    SELECT

        Fecha,

        Turno,



        COUNT(*) AS Cantidad_Registros_MB,



        MAX(CaolBeta_MB)

            AS CaolBeta_MB,



        MAX(CuFe_MB)

            AS CuFe_MB,

        MAX(Fuente_Conciliacion)
            AS Fuente_Conciliacion



    FROM mb_base



    WHERE Turno IS NOT NULL



    GROUP BY

        Fecha,

        Turno

),



/* ============================================================

   Construcción de la grilla Fecha + Turno + Torre

   ============================================================ */

fecha_turno AS

(

    SELECT Fecha, Turno

    FROM rep



    UNION



    SELECT Fecha, Turno

    FROM nir



    UNION



    SELECT Fecha, Turno

    FROM lab



    UNION



    SELECT Fecha, Turno

    FROM mb

),



grilla AS

(

    SELECT

        ft.Fecha,

        ft.Turno,

        t.Torre



    FROM fecha_turno AS ft



    CROSS JOIN

    (

        VALUES

            ('TM1'),

            ('TM2')

    ) AS t(Torre)



    WHERE ft.Fecha IS NOT NULL

      AND ft.Turno IS NOT NULL

),



/* ============================================================

   Fuentes propias de cada torre

   ============================================================ */

fuentes_propias AS

(

    SELECT

        g.Fecha,

        g.Turno,

        g.Torre,



        r.Representatividad_Quimica,



        CASE

            WHEN r.Representatividad_Quimica >= 0.75

                THEN CAST(1 AS bit)



            WHEN r.Representatividad_Quimica IS NULL

                THEN NULL



            ELSE CAST(0 AS bit)

        END AS Flag_Representativa_Quimica,



        /* CaolBeta propio */

        n.ID_NIR,

        n.Muestra_NIR,

        n.CaolBeta_NIR,

        n.Fecha_Carga_NIR,

        n.Cantidad_Registros_NIR,



        /* CuFe propio */

        l.ID_Registro_CuFe,

        l.CuFe_Laboratorio,

        l.Fecha_Carga_Laboratorio,

        l.Cantidad_Registros_Laboratorio,



        /* Modelo de bloques */

        m.CaolBeta_MB,

        m.CuFe_MB,
        m.Fuente_Conciliacion,

        m.Cantidad_Registros_MB



    FROM grilla AS g



    LEFT JOIN rep AS r

        ON r.Fecha = g.Fecha

       AND r.Turno = g.Turno

       AND r.Torre = g.Torre



    LEFT JOIN nir AS n

        ON n.Fecha = g.Fecha

       AND n.Turno = g.Turno

       AND n.Torre = g.Torre



    LEFT JOIN lab AS l

        ON l.Fecha = g.Fecha

       AND l.Turno = g.Turno

       AND l.Torre = g.Torre



    LEFT JOIN mb AS m

        ON m.Fecha = g.Fecha

       AND m.Turno = g.Turno

),



/* ============================================================

   Fuentes disponibles específicamente en TM2

   para la regla de compartición hacia TM1

   ============================================================ */

fuentes_tm2 AS

(

    SELECT

        f.Fecha,

        f.Turno,



        f.Representatividad_Quimica

            AS Representatividad_Quimica_TM2,



        f.Flag_Representativa_Quimica

            AS Flag_Representativa_Quimica_TM2,



        f.ID_NIR

            AS ID_NIR_TM2,



        f.Muestra_NIR

            AS Muestra_NIR_TM2,



        f.CaolBeta_NIR

            AS CaolBeta_NIR_TM2,



        f.Fecha_Carga_NIR

            AS Fecha_Carga_NIR_TM2,



        f.ID_Registro_CuFe

            AS ID_Registro_CuFe_TM2,



        f.CuFe_Laboratorio

            AS CuFe_Laboratorio_TM2,



        f.Fecha_Carga_Laboratorio

            AS Fecha_Carga_Laboratorio_TM2



    FROM fuentes_propias AS f



    WHERE f.Torre = 'TM2'

),



fuentes_completas AS

(

    SELECT

        f.Fecha,

        f.Turno,

        f.Torre,



        /* Representatividad propia */

        f.Representatividad_Quimica,

        f.Flag_Representativa_Quimica,



        /* CaolBeta propio */

        f.ID_NIR,

        f.Muestra_NIR,

        f.CaolBeta_NIR,

        f.Fecha_Carga_NIR,

        f.Cantidad_Registros_NIR,



        /* CuFe propio */

        f.ID_Registro_CuFe,

        f.CuFe_Laboratorio,

        f.Fecha_Carga_Laboratorio,

        f.Cantidad_Registros_Laboratorio,



        /* Fuentes TM2 para compartir */

        t2.Representatividad_Quimica_TM2,

        t2.Flag_Representativa_Quimica_TM2,



        t2.ID_NIR_TM2,

        t2.Muestra_NIR_TM2,

        t2.CaolBeta_NIR_TM2,

        t2.Fecha_Carga_NIR_TM2,



        t2.ID_Registro_CuFe_TM2,

        t2.CuFe_Laboratorio_TM2,

        t2.Fecha_Carga_Laboratorio_TM2,



        /* Modelo de bloques */

        f.CaolBeta_MB,

        f.CuFe_MB,
        f.Fuente_Conciliacion,

        f.Cantidad_Registros_MB



    FROM fuentes_propias AS f



    LEFT JOIN fuentes_tm2 AS t2

        ON t2.Fecha = f.Fecha

       AND t2.Turno = f.Turno

),



resuelto AS

(

    SELECT

        f.*,



        /* ====================================================

           Resolución CaolBeta

           ==================================================== */

        CASE

            /* Laboratorio propio */

            WHEN f.Representatividad_Quimica >= 0.75

             AND f.CaolBeta_NIR IS NOT NULL

                THEN f.CaolBeta_NIR



            /* Compartición TM2 -> TM1 */

            WHEN f.Torre = 'TM1'

             AND f.Representatividad_Quimica_TM2 >= 0.75

             AND f.CaolBeta_NIR_TM2 IS NOT NULL

                THEN f.CaolBeta_NIR_TM2



            /* Modelo de bloques */

            WHEN f.CaolBeta_MB IS NOT NULL

                THEN f.CaolBeta_MB



            ELSE NULL

        END AS CaolBeta_Final,



        CASE

            WHEN f.Representatividad_Quimica >= 0.75

             AND f.CaolBeta_NIR IS NOT NULL

                THEN 'NIR_PROPIO_REPRESENTATIVO'



            WHEN f.Torre = 'TM1'

             AND f.Representatividad_Quimica_TM2 >= 0.75

             AND f.CaolBeta_NIR_TM2 IS NOT NULL

                THEN 'NIR_TM2_COMPARTIDO'



            WHEN f.CaolBeta_MB IS NOT NULL

             AND f.Representatividad_Quimica IS NULL

                THEN CASE WHEN f.Fuente_Conciliacion = 'IMP' THEN 'IMP_SIN_REPRESENTATIVIDAD' ELSE 'MB_SIN_REPRESENTATIVIDAD' END



            WHEN f.CaolBeta_MB IS NOT NULL

             AND f.Representatividad_Quimica < 0.75

                THEN CASE WHEN f.Fuente_Conciliacion = 'IMP' THEN 'IMP_NO_REPRESENTATIVO' ELSE 'MB_NO_REPRESENTATIVO' END



            WHEN f.CaolBeta_MB IS NOT NULL

             AND f.Representatividad_Quimica >= 0.75

             AND f.CaolBeta_NIR IS NULL

                THEN CASE WHEN f.Fuente_Conciliacion = 'IMP' THEN 'IMP_SIN_RESULTADO_NIR' ELSE 'MB_SIN_RESULTADO_NIR' END



            ELSE 'SIN_DATO'

        END AS Fuente_CaolBeta,



        /* ====================================================

           Resolución CuFe

           ==================================================== */

        CASE

            /* Laboratorio propio */

            WHEN f.Representatividad_Quimica >= 0.75

             AND f.CuFe_Laboratorio IS NOT NULL

                THEN f.CuFe_Laboratorio



            /* Compartición TM2 -> TM1 */

            WHEN f.Torre = 'TM1'

             AND f.Representatividad_Quimica_TM2 >= 0.75

             AND f.CuFe_Laboratorio_TM2 IS NOT NULL

                THEN f.CuFe_Laboratorio_TM2



            /* Modelo de bloques */

            WHEN f.CuFe_MB IS NOT NULL

                THEN f.CuFe_MB



            ELSE NULL

        END AS CuFe_Final,



        CASE

            WHEN f.Representatividad_Quimica >= 0.75

             AND f.CuFe_Laboratorio IS NOT NULL

                THEN 'LAB_PROPIO_REPRESENTATIVO'



            WHEN f.Torre = 'TM1'

             AND f.Representatividad_Quimica_TM2 >= 0.75

             AND f.CuFe_Laboratorio_TM2 IS NOT NULL

                THEN 'LAB_TM2_COMPARTIDO'



            WHEN f.CuFe_MB IS NOT NULL

             AND f.Representatividad_Quimica IS NULL

                THEN CASE WHEN f.Fuente_Conciliacion = 'IMP' THEN 'IMP_SIN_REPRESENTATIVIDAD' ELSE 'MB_SIN_REPRESENTATIVIDAD' END



            WHEN f.CuFe_MB IS NOT NULL

             AND f.Representatividad_Quimica < 0.75

                THEN CASE WHEN f.Fuente_Conciliacion = 'IMP' THEN 'IMP_NO_REPRESENTATIVO' ELSE 'MB_NO_REPRESENTATIVO' END



            WHEN f.CuFe_MB IS NOT NULL

             AND f.Representatividad_Quimica >= 0.75

             AND f.CuFe_Laboratorio IS NULL

                THEN CASE WHEN f.Fuente_Conciliacion = 'IMP' THEN 'IMP_SIN_RESULTADO_CUFE' ELSE 'MB_SIN_RESULTADO_CUFE' END



            ELSE 'SIN_DATO'

        END AS Fuente_CuFe



    FROM fuentes_completas AS f

)



SELECT

    Fecha,

    Turno,

    Torre,



    /* Representatividad propia */

    Representatividad_Quimica,

    Flag_Representativa_Quimica,



    /* Representatividad TM2 para revisar compartición */

    Representatividad_Quimica_TM2,

    Flag_Representativa_Quimica_TM2,



    /* ========================================================

       CaolBeta propio

       ======================================================== */

    ID_NIR,

    Muestra_NIR,

    CaolBeta_NIR,

    Fecha_Carga_NIR,

    Cantidad_Registros_NIR,



    /* CaolBeta TM2 potencialmente compartido */

    ID_NIR_TM2,

    Muestra_NIR_TM2,

    CaolBeta_NIR_TM2,

    Fecha_Carga_NIR_TM2,



    /* Modelo de bloques */

    CaolBeta_MB,



    /* Resultado con precisión completa */

    CaolBeta_Final,



    /* Resultado compatible con histórico */

    CAST(

        ROUND(CaolBeta_Final, 2)

        AS decimal(18,2)

    ) AS CaolBeta_Final_2D,



    Fuente_CaolBeta,



    /* ========================================================

       CuFe propio

       ======================================================== */

    ID_Registro_CuFe,

    CuFe_Laboratorio,

    Fecha_Carga_Laboratorio,

    Cantidad_Registros_Laboratorio,



    /* CuFe TM2 potencialmente compartido */

    ID_Registro_CuFe_TM2,

    CuFe_Laboratorio_TM2,

    Fecha_Carga_Laboratorio_TM2,



    /* Modelo de bloques */

    CuFe_MB,

    Fuente_Conciliacion,



    /* Resultado con precisión completa */

    CuFe_Final,



    /* Resultado compatible con histórico */

    CAST(

        ROUND(CuFe_Final, 2)

        AS decimal(18,2)

    ) AS CuFe_Final_2D,



    Fuente_CuFe,



    /* Control de duplicidad o cardinalidad MB */

    Cantidad_Registros_MB



FROM resuelto;

GO

ALTER PROCEDURE

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

GO

COMMIT TRANSACTION;
GO
