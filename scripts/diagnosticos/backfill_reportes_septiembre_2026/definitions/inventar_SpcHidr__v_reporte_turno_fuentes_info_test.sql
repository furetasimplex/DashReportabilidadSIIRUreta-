CREATE   VIEW inventar_SpcHidr.v_reporte_turno_fuentes_info_test
AS

WITH fuentes AS
(
    /* ========================================================
       FUENTES QUÍMICAS: TORRES
       ======================================================== */

    SELECT
        l.Fecha,
        l.Turno,
        'QUIMICA' AS Tipo_Muestra,

        CASE
            WHEN l.TM = 'TM1'
             AND
             (
                    l.Fuente_CuT   LIKE '%TORRE%'
                 OR l.Fuente_CuS   LIKE '%TORRE%'
                 OR l.Fuente_FeT   LIKE '%TORRE%'
                 OR l.Fuente_FeS   LIKE '%TORRE%'
                 OR l.Fuente_CO3   LIKE '%TORRE%'
                 OR l.Fuente_ConsH LIKE '%TORRE%'
                 OR l.Fuente_FeS   LIKE '%ARRASTRE%'
                 OR l.Fuente_ConsH LIKE '%ARRASTRE%'
             )
                THEN 'T1'

            WHEN l.TM = 'TM2'
             AND
             (
                    l.Fuente_CuT   LIKE '%TORRE%'
                 OR l.Fuente_CuS   LIKE '%TORRE%'
                 OR l.Fuente_FeT   LIKE '%TORRE%'
                 OR l.Fuente_FeS   LIKE '%TORRE%'
                 OR l.Fuente_CO3   LIKE '%TORRE%'
                 OR l.Fuente_ConsH LIKE '%TORRE%'
                 OR l.Fuente_FeS   LIKE '%ARRASTRE%'
                 OR l.Fuente_ConsH LIKE '%ARRASTRE%'
             )
                THEN 'T2'
        END AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    /* ========================================================
       FUENTES QUÍMICAS: MINA / MB
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'QUIMICA' AS Tipo_Muestra,
        'MB' AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    WHERE
           l.Fuente_CuT LIKE '%MINA%'
        OR l.Fuente_CuS LIKE '%MINA%'
        OR l.Fuente_FeT LIKE '%MINA%'
        OR l.Fuente_CO3 LIKE '%MINA%'
        OR l.Fuente_CuT LIKE '%MB%'
        OR l.Fuente_CuS LIKE '%MB%'
        OR l.Fuente_FeT LIKE '%MB%'
        OR l.Fuente_CO3 LIKE '%MB%'

    /* ========================================================
       FUENTES QUÍMICAS: IMP
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'QUIMICA' AS Tipo_Muestra,
        'IMP' AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    WHERE
           l.Fuente_CuT = 'IMP'
        OR l.Fuente_CuS = 'IMP'
        OR l.Fuente_FeT = 'IMP'
        OR l.Fuente_CO3 = 'IMP'

    /* ========================================================
       FUENTES FÍSICAS: TORRES
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'FISICA' AS Tipo_Muestra,

        CASE
            WHEN l.TM = 'TM1'
             AND
             (
                    l.Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                 OR l.Fuente_Malla_Menos_100 LIKE '%TORRE%'
                 OR l.Fuente_Malla_Menos_1_2 LIKE '%ARRASTRE%'
                 OR l.Fuente_Malla_Menos_100 LIKE '%ARRASTRE%'
             )
                THEN 'T1'

            WHEN l.TM = 'TM2'
             AND
             (
                    l.Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                 OR l.Fuente_Malla_Menos_100 LIKE '%TORRE%'
                 OR l.Fuente_Malla_Menos_1_2 LIKE '%ARRASTRE%'
                 OR l.Fuente_Malla_Menos_100 LIKE '%ARRASTRE%'
             )
                THEN 'T2'
        END AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    /* ========================================================
       FUENTES FÍSICAS: MINA / MB
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'FISICA' AS Tipo_Muestra,
        'MB' AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    WHERE
           l.Fuente_Malla_Menos_100 LIKE '%MINA%'
        OR l.Fuente_Malla_Menos_100 LIKE '%MB%'

    /* ========================================================
       FUENTES FÍSICAS: IMP
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'FISICA' AS Tipo_Muestra,
        'IMP' AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    WHERE l.Fuente_Malla_Menos_100 = 'IMP'
),

fuentes_limpias AS
(
    SELECT DISTINCT
        Fecha,
        Turno,
        Tipo_Muestra,
        Fuente_Info

    FROM fuentes

    WHERE Fuente_Info IS NOT NULL
),

fuentes_agrupadas AS
(
    SELECT
        Fecha,
        Turno,
        Tipo_Muestra,

        STRING_AGG(Fuente_Info, '; ')
        WITHIN GROUP
        (
            ORDER BY
                CASE Fuente_Info
                    WHEN 'T1'  THEN 1
                    WHEN 'T2'  THEN 2
                    WHEN 'MB'  THEN 3
                    WHEN 'IMP' THEN 4
                    ELSE 9
                END
        ) AS Fuente_Info_Detalle

    FROM fuentes_limpias

    GROUP BY
        Fecha,
        Turno,
        Tipo_Muestra
)

SELECT
    Fecha,
    Turno,

    MAX
    (
        CASE
            WHEN Tipo_Muestra = 'QUIMICA'
                THEN Fuente_Info_Detalle
        END
    ) AS Fuente_Info_Quimica,

    MAX
    (
        CASE
            WHEN Tipo_Muestra = 'FISICA'
                THEN Fuente_Info_Detalle
        END
    ) AS Fuente_Info_Fisica

FROM fuentes_agrupadas

GROUP BY
    Fecha,
    Turno;
