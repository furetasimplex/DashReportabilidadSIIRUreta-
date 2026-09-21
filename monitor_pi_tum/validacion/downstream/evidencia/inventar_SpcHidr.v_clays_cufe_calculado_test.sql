
CREATE   VIEW
    [inventar_SpcHidr].[v_clays_cufe_calculado_test]
AS

/* ============================================================
   OBJETIVO
   ------------------------------------------------------------
   Resolver CaolBeta y CuFe por:

       Fecha + Turno + Torre

   Fuentes:
     - Representatividad química:
         inventar_SpcHidr.representatividad_torres_resultado

     - CaolBeta laboratorio:
         inventar_SpcHidr.NIR

     - CuFe laboratorio:
         inventar_SpcHidr.Informe_TM_lab

     - Modelo de bloques:
         inventar_SpcHidr.v_conciliacion_chancado_v2

   Reglas por analito:
     1. Representatividad química >= 0,75
        y existe dato propio de laboratorio:
            utilizar laboratorio.

     2. En cualquier otro caso:
            utilizar modelo de bloques.

     3. Si ninguna fuente está disponible:
            devolver NULL.

   IMPORTANTE:
     - Esta vista no modifica Clays_CuFe.
     - No comparte resultados entre TM1 y TM2.
     - Cada torre se evalúa independientemente.
   ============================================================ */

WITH rep AS
(
    /* ========================================================
       Normalización de la tabla ancha de representatividad
       a una estructura:

           Fecha + Turno + Torre
       ======================================================== */
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
            WHEN norm.Torre_Normalizada IN
                 (
                     'TM1',
                     'T1',
                     'TORRE1'
                 )
                THEN 'TM1'

            WHEN norm.Torre_Normalizada IN
                 (
                     'TM2',
                     'T2',
                     'TORRE2'
                 )
                THEN 'TM2'

            ELSE NULL
        END AS Torre,

        CASE
            WHEN norm.Turno_Normalizado IN
                 (
                     'A',
                     'TA',
                     'TURNOA'
                 )
                THEN 'A'

            WHEN norm.Turno_Normalizado IN
                 (
                     'B',
                     'TB',
                     'TURNOB'
                 )
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
            /* Normaliza:
               TM-1, TM 1, TM_1, TM1 → TM1 */
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

            /* Normaliza:
               TA, T-A, Turno A, A → TA/A */
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
    /* Si existe más de una carga para la misma clave,
       conserva la versión más reciente. */
    SELECT
        n.*,

        COUNT(*) OVER
        (
            PARTITION BY
                n.Fecha,
                n.Torre,
                n.Turno
        ) AS Cantidad_Registros_NIR,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                n.Fecha,
                n.Torre,
                n.Turno

            ORDER BY
                ISNULL(
                    n.fecha_carga,
                    CONVERT(datetime2, '19000101')
                ) DESC,

                n.id DESC
        ) AS rn

    FROM nir_normalizado AS n

    WHERE n.Torre IS NOT NULL
      AND n.Turno IS NOT NULL
),

nir AS
(
    SELECT
        Fecha,
        Torre,
        Turno,

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
            WHEN norm.Torre_Normalizada IN
                 (
                     'TM1',
                     'T1',
                     'TORRE1'
                 )
                THEN 'TM1'

            WHEN norm.Torre_Normalizada IN
                 (
                     'TM2',
                     'T2',
                     'TORRE2'
                 )
                THEN 'TM2'

            ELSE NULL
        END AS Torre,

        CASE
            WHEN norm.Turno_Normalizado IN
                 (
                     'A',
                     'TA',
                     'TURNOA'
                 )
                THEN 'A'

            WHEN norm.Turno_Normalizado IN
                 (
                     'B',
                     'TB',
                     'TURNOB'
                 )
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
    /* Conserva el último resultado disponible
       por Fecha + Turno + Torre. */
    SELECT
        l.*,

        COUNT(*) OVER
        (
            PARTITION BY
                l.Fecha,
                l.Torre,
                l.Turno
        ) AS Cantidad_Registros_Laboratorio,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                l.Fecha,
                l.Torre,
                l.Turno

            ORDER BY
                ISNULL(
                    l.Fecha_Carga_Laboratorio,
                    CONVERT(datetime, '19000101')
                ) DESC,

                l.ID_Registro DESC
        ) AS rn

    FROM lab_normalizado AS l

    WHERE l.Torre IS NOT NULL
      AND l.Turno IS NOT NULL
),

lab AS
(
    SELECT
        Fecha,
        Torre,
        Turno,

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
            WHEN norm.Turno_Normalizado IN
                 (
                     'A',
                     'TA',
                     'TURNOA'
                 )
                THEN 'A'

            WHEN norm.Turno_Normalizado IN
                 (
                     'B',
                     'TB',
                     'TURNOB'
                 )
                THEN 'B'

            ELSE NULL
        END AS Turno,

        TRY_CONVERT(float, c.Clay_Beta)
            AS CaolBeta_MB,

        TRY_CONVERT(float, c.CuFe)
            AS CuFe_MB

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
    /* La conciliación debería entregar una fila por
       Fecha + Turno.

       Se expone la cantidad para detectar posibles
       duplicidades en la fuente. */
    SELECT
        Fecha,
        Turno,

        COUNT(*) AS Cantidad_Registros_MB,

        MAX(CaolBeta_MB)
            AS CaolBeta_MB,

        MAX(CuFe_MB)
            AS CuFe_MB

    FROM mb_base

    WHERE Turno IS NOT NULL

    GROUP BY
        Fecha,
        Turno
),

/* ============================================================
   Construcción de fechas y turnos disponibles
   ============================================================ */
fecha_turno AS
(
    SELECT
        Fecha,
        Turno
    FROM mb

    UNION

    SELECT
        Fecha,
        Turno
    FROM rep

    UNION

    SELECT
        Fecha,
        Turno
    FROM nir

    UNION

    SELECT
        Fecha,
        Turno
    FROM lab
),

grilla AS
(
    /* Para cada Fecha + Turno genera TM1 y TM2. */
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

fuentes AS
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

        /* NIR */
        n.ID_NIR,
        n.Muestra_NIR,
        n.CaolBeta_NIR,
        n.Fecha_Carga_NIR,
        n.Cantidad_Registros_NIR,

        /* Laboratorio TM */
        l.ID_Registro_CuFe,
        l.CuFe_Laboratorio,
        l.Fecha_Carga_Laboratorio,
        l.Cantidad_Registros_Laboratorio,

        /* Modelo de bloques */
        m.CaolBeta_MB,
        m.CuFe_MB,
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
)

SELECT
    Fecha,
    Turno,
    Torre,

    Representatividad_Quimica,
    Flag_Representativa_Quimica,

    /* ========================================================
       Trazabilidad CaolBeta
       ======================================================== */
    ID_NIR,
    Muestra_NIR,
    CaolBeta_NIR,
    Fecha_Carga_NIR,
    Cantidad_Registros_NIR,

    CaolBeta_MB,

    CASE
        WHEN Representatividad_Quimica >= 0.75
         AND CaolBeta_NIR IS NOT NULL
            THEN CaolBeta_NIR

        WHEN CaolBeta_MB IS NOT NULL
            THEN CaolBeta_MB

        ELSE NULL
    END AS CaolBeta_Final,

    CASE
        WHEN Representatividad_Quimica >= 0.75
         AND CaolBeta_NIR IS NOT NULL
            THEN 'NIR_REPRESENTATIVO'

        WHEN CaolBeta_MB IS NOT NULL
         AND Representatividad_Quimica IS NULL
            THEN 'MB_SIN_REPRESENTATIVIDAD'

        WHEN CaolBeta_MB IS NOT NULL
         AND Representatividad_Quimica < 0.75
            THEN 'MB_NO_REPRESENTATIVO'

        WHEN CaolBeta_MB IS NOT NULL
         AND Representatividad_Quimica >= 0.75
         AND CaolBeta_NIR IS NULL
            THEN 'MB_SIN_RESULTADO_NIR'

        ELSE 'SIN_DATO'
    END AS Fuente_CaolBeta,

    /* ========================================================
       Trazabilidad CuFe
       ======================================================== */
    ID_Registro_CuFe,
    CuFe_Laboratorio,
    Fecha_Carga_Laboratorio,
    Cantidad_Registros_Laboratorio,

    CuFe_MB,

    CASE
        WHEN Representatividad_Quimica >= 0.75
         AND CuFe_Laboratorio IS NOT NULL
            THEN CuFe_Laboratorio

        WHEN CuFe_MB IS NOT NULL
            THEN CuFe_MB

        ELSE NULL
    END AS CuFe_Final,

    CASE
        WHEN Representatividad_Quimica >= 0.75
         AND CuFe_Laboratorio IS NOT NULL
            THEN 'LAB_TORRE_REPRESENTATIVA'

        WHEN CuFe_MB IS NOT NULL
         AND Representatividad_Quimica IS NULL
            THEN 'MB_SIN_REPRESENTATIVIDAD'

        WHEN CuFe_MB IS NOT NULL
         AND Representatividad_Quimica < 0.75
            THEN 'MB_NO_REPRESENTATIVO'

        WHEN CuFe_MB IS NOT NULL
         AND Representatividad_Quimica >= 0.75
         AND CuFe_Laboratorio IS NULL
            THEN 'MB_SIN_RESULTADO_CUFE'

        ELSE 'SIN_DATO'
    END AS Fuente_CuFe,

    /* Control de la fuente MB */
    Cantidad_Registros_MB

FROM fuentes;
