CREATE   VIEW inventar_SpcHidr.v_validacion_leyes_tm1_v2
AS

WITH dias AS
(
    SELECT DISTINCT
        Fecha
    FROM inventar_SpcHidr.v_conciliacion_chancado_v2
),
lab AS
(
    SELECT
        Fecha,
        Turno,
        Torre,
        MAX(CuT_global) AS CuT_global,
        MAX(CuS_Global) AS CuS_Global,
        MAX(Fe_Global) AS Fe_Global,
        MAX(FeS_Global) AS FeS_Global,
        MAX(Carb_Global) AS Carb_Global,
        MAX(Cons_KgTon) AS Cons_KgTon,
        MAX(Pasante_1_2P) AS Pasante_1_2P,
        MAX(Pasante_100m) AS Pasante_100m,
        MAX(CuFe_Global) AS CuFe_Global
    FROM inventar_SpcHidr.Informe_TM_lab
    GROUP BY
        Fecha,
        Turno,
        Torre
),
clays AS
(
    SELECT
        Fecha,
        Turno,
        Torre,
        MAX(
            TRY_CONVERT(
                float,
                REPLACE(REPLACE(Caolinita, ',', '.'), '%', '')
            )
        ) AS Caolinita,
        MAX(
            TRY_CONVERT(
                float,
                REPLACE(REPLACE(Qz, ',', '.'), '%', '')
            )
        ) AS Cuarzo,
        MAX(CaolBeta) AS CaolBeta,
        MAX(CuFe) AS CuFe
    FROM inventar_SpcHidr.Clays_CuFe
    GROUP BY
        Fecha,
        Turno,
        Torre
)

SELECT
    d.Fecha,

    rep.TM1_TurnoA_Quimico AS [Rep. TM1 A],
    rep.TM1_TurnoB_Quimico AS [Rep. TM1 B],

    /* ============================================================
       CuT
       ============================================================ */

    lab_A.CuT_global AS [CuT Torre A],
    mina_A.CuT AS [CuT Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.CuT_global IS NOT NULL
            THEN lab_A.CuT_global
        WHEN mina_A.CuT IS NOT NULL
            THEN mina_A.CuT
        ELSE NULL
    END AS [CuT Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.CuT_global IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.CuT IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CuT A],

    lab_B.CuT_global AS [CuT Torre B],
    mina_B.CuT AS [CuT Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.CuT_global IS NOT NULL
            THEN lab_B.CuT_global
        WHEN mina_B.CuT IS NOT NULL
            THEN mina_B.CuT
        ELSE NULL
    END AS [CuT Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.CuT_global IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.CuT IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CuT B],

    /* ============================================================
       CuS
       ============================================================ */

    lab_A.CuS_Global AS [CuS Torre A],
    mina_A.CuS AS [CuS Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.CuS_Global IS NOT NULL
            THEN lab_A.CuS_Global
        WHEN mina_A.CuS IS NOT NULL
            THEN mina_A.CuS
        ELSE NULL
    END AS [CuS Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.CuS_Global IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.CuS IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CuS A],

    lab_B.CuS_Global AS [CuS Torre B],
    mina_B.CuS AS [CuS Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.CuS_Global IS NOT NULL
            THEN lab_B.CuS_Global
        WHEN mina_B.CuS IS NOT NULL
            THEN mina_B.CuS
        ELSE NULL
    END AS [CuS Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.CuS_Global IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.CuS IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CuS B],

    /* ============================================================
       FeT
       ============================================================ */

    lab_A.Fe_Global AS [FeT Torre A],
    mina_A.Fe AS [FeT Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.Fe_Global IS NOT NULL
            THEN lab_A.Fe_Global
        WHEN mina_A.Fe IS NOT NULL
            THEN mina_A.Fe
        ELSE NULL
    END AS [FeT Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.Fe_Global IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.Fe IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente FeT A],

    lab_B.Fe_Global AS [FeT Torre B],
    mina_B.Fe AS [FeT Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.Fe_Global IS NOT NULL
            THEN lab_B.Fe_Global
        WHEN mina_B.Fe IS NOT NULL
            THEN mina_B.Fe
        ELSE NULL
    END AS [FeT Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.Fe_Global IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.Fe IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente FeT B],

    /* ============================================================
       FeS: lógica original sin modificaciones
       ============================================================ */

    lab_A.FeS_Global AS [FeS Torre A],
    CAST(NULL AS float) AS [FeS Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.FeS_Global IS NOT NULL
            THEN lab_A.FeS_Global
        ELSE 0
    END AS [FeS Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.FeS_Global IS NOT NULL
            THEN 'TORRE'
        ELSE 'NO_APLICA_MINA'
    END AS [Fuente FeS A],

    lab_B.FeS_Global AS [FeS Torre B],
    CAST(NULL AS float) AS [FeS Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.FeS_Global IS NOT NULL
            THEN lab_B.FeS_Global
        ELSE 0
    END AS [FeS Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.FeS_Global IS NOT NULL
            THEN 'TORRE'
        ELSE 'NO_APLICA_MINA'
    END AS [Fuente FeS B],

    /* ============================================================
       CO3
       ============================================================ */

    lab_A.Carb_Global AS [CO3 Torre A],
    mina_A.CO3 AS [CO3 Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.Carb_Global IS NOT NULL
            THEN lab_A.Carb_Global
        WHEN mina_A.CO3 IS NOT NULL
            THEN mina_A.CO3
        ELSE NULL
    END AS [CO3 Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.Carb_Global IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.CO3 IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CO3 A],

    lab_B.Carb_Global AS [CO3 Torre B],
    mina_B.CO3 AS [CO3 Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.Carb_Global IS NOT NULL
            THEN lab_B.Carb_Global
        WHEN mina_B.CO3 IS NOT NULL
            THEN mina_B.CO3
        ELSE NULL
    END AS [CO3 Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.Carb_Global IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.CO3 IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CO3 B],

    /* ============================================================
       ConsH: lógica original sin modificaciones
       ============================================================ */

    lab_A.Cons_KgTon AS [ConsH Torre A],
    CAST(NULL AS float) AS [ConsH Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.Cons_KgTon IS NOT NULL
            THEN lab_A.Cons_KgTon
        ELSE 0
    END AS [ConsH Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND lab_A.Cons_KgTon IS NOT NULL
            THEN 'TORRE'
        ELSE 'NO_APLICA_MINA'
    END AS [Fuente ConsH A],

    lab_B.Cons_KgTon AS [ConsH Torre B],
    CAST(NULL AS float) AS [ConsH Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.Cons_KgTon IS NOT NULL
            THEN lab_B.Cons_KgTon
        ELSE 0
    END AS [ConsH Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND lab_B.Cons_KgTon IS NOT NULL
            THEN 'TORRE'
        ELSE 'NO_APLICA_MINA'
    END AS [Fuente ConsH B],

    /* ============================================================
       Malla -1/2: lógica original sin modificaciones
       ============================================================ */

    lab_A.Pasante_1_2P AS [Malla -1/2 Torre A],
    CAST(NULL AS float) AS [Malla -1/2 Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Fisico > 0.75
         AND lab_A.Pasante_1_2P IS NOT NULL
            THEN lab_A.Pasante_1_2P
        ELSE 0
    END AS [Malla -1/2 Final A],

    CASE
        WHEN rep.TM1_TurnoA_Fisico > 0.75
         AND lab_A.Pasante_1_2P IS NOT NULL
            THEN 'TORRE'
        ELSE 'NO_APLICA_MINA'
    END AS [Fuente Malla -1/2 A],

    lab_B.Pasante_1_2P AS [Malla -1/2 Torre B],
    CAST(NULL AS float) AS [Malla -1/2 Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Fisico > 0.75
         AND lab_B.Pasante_1_2P IS NOT NULL
            THEN lab_B.Pasante_1_2P
        ELSE 0
    END AS [Malla -1/2 Final B],

    CASE
        WHEN rep.TM1_TurnoB_Fisico > 0.75
         AND lab_B.Pasante_1_2P IS NOT NULL
            THEN 'TORRE'
        ELSE 'NO_APLICA_MINA'
    END AS [Fuente Malla -1/2 B],

    /* ============================================================
       Malla -100
       ============================================================ */

    lab_A.Pasante_100m AS [Malla -100 Torre A],
    mina_A.Malla100 AS [Malla -100 Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Fisico > 0.75
         AND lab_A.Pasante_100m IS NOT NULL
            THEN lab_A.Pasante_100m
        WHEN mina_A.Malla100 IS NOT NULL
            THEN mina_A.Malla100
        ELSE NULL
    END AS [Malla -100 Final A],

    CASE
        WHEN rep.TM1_TurnoA_Fisico > 0.75
         AND lab_A.Pasante_100m IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.Malla100 IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente Malla -100 A],

    lab_B.Pasante_100m AS [Malla -100 Torre B],
    mina_B.Malla100 AS [Malla -100 Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Fisico > 0.75
         AND lab_B.Pasante_100m IS NOT NULL
            THEN lab_B.Pasante_100m
        WHEN mina_B.Malla100 IS NOT NULL
            THEN mina_B.Malla100
        ELSE NULL
    END AS [Malla -100 Final B],

    CASE
        WHEN rep.TM1_TurnoB_Fisico > 0.75
         AND lab_B.Pasante_100m IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.Malla100 IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente Malla -100 B],

    /* ============================================================
       CuFe
       ============================================================ */

    COALESCE(clay_A.CuFe, lab_A.CuFe_Global) AS [CuFe Torre A],
    mina_A.CuFe AS [CuFe Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND COALESCE(clay_A.CuFe, lab_A.CuFe_Global) IS NOT NULL
            THEN COALESCE(clay_A.CuFe, lab_A.CuFe_Global)
        WHEN mina_A.CuFe IS NOT NULL
            THEN mina_A.CuFe
        ELSE NULL
    END AS [CuFe Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND COALESCE(clay_A.CuFe, lab_A.CuFe_Global) IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.CuFe IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CuFe A],

    COALESCE(clay_B.CuFe, lab_B.CuFe_Global) AS [CuFe Torre B],
    mina_B.CuFe AS [CuFe Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND COALESCE(clay_B.CuFe, lab_B.CuFe_Global) IS NOT NULL
            THEN COALESCE(clay_B.CuFe, lab_B.CuFe_Global)
        WHEN mina_B.CuFe IS NOT NULL
            THEN mina_B.CuFe
        ELSE NULL
    END AS [CuFe Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND COALESCE(clay_B.CuFe, lab_B.CuFe_Global) IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.CuFe IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CuFe B],

    /* ============================================================
       Caolinita
       ============================================================ */

    clay_A.Caolinita AS [Caolinita Torre A],
    mina_A.Caolinita AS [Caolinita Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND clay_A.Caolinita IS NOT NULL
            THEN clay_A.Caolinita
        WHEN mina_A.Caolinita IS NOT NULL
            THEN mina_A.Caolinita
        ELSE NULL
    END AS [Caolinita Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND clay_A.Caolinita IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.Caolinita IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente Caolinita A],

    clay_B.Caolinita AS [Caolinita Torre B],
    mina_B.Caolinita AS [Caolinita Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND clay_B.Caolinita IS NOT NULL
            THEN clay_B.Caolinita
        WHEN mina_B.Caolinita IS NOT NULL
            THEN mina_B.Caolinita
        ELSE NULL
    END AS [Caolinita Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND clay_B.Caolinita IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.Caolinita IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente Caolinita B],

    /* ============================================================
       CaolBeta
       ============================================================ */

    clay_A.CaolBeta AS [CaolBeta Torre A],
    mina_A.Clay_Beta AS [CaolBeta Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND clay_A.CaolBeta IS NOT NULL
            THEN clay_A.CaolBeta
        WHEN mina_A.Clay_Beta IS NOT NULL
            THEN mina_A.Clay_Beta
        ELSE NULL
    END AS [CaolBeta Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND clay_A.CaolBeta IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.Clay_Beta IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CaolBeta A],

    clay_B.CaolBeta AS [CaolBeta Torre B],
    mina_B.Clay_Beta AS [CaolBeta Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND clay_B.CaolBeta IS NOT NULL
            THEN clay_B.CaolBeta
        WHEN mina_B.Clay_Beta IS NOT NULL
            THEN mina_B.Clay_Beta
        ELSE NULL
    END AS [CaolBeta Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND clay_B.CaolBeta IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.Clay_Beta IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente CaolBeta B],

    /* ============================================================
       Cuarzo
       ============================================================ */

    clay_A.Cuarzo AS [Cuarzo Torre A],
    mina_A.Cuarzo AS [Cuarzo Mina A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND clay_A.Cuarzo IS NOT NULL
            THEN clay_A.Cuarzo
        WHEN mina_A.Cuarzo IS NOT NULL
            THEN mina_A.Cuarzo
        ELSE NULL
    END AS [Cuarzo Final A],

    CASE
        WHEN rep.TM1_TurnoA_Quimico > 0.75
         AND clay_A.Cuarzo IS NOT NULL
            THEN 'TORRE'
        WHEN mina_A.Cuarzo IS NOT NULL
            THEN mina_A.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente Cuarzo A],

    clay_B.Cuarzo AS [Cuarzo Torre B],
    mina_B.Cuarzo AS [Cuarzo Mina B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND clay_B.Cuarzo IS NOT NULL
            THEN clay_B.Cuarzo
        WHEN mina_B.Cuarzo IS NOT NULL
            THEN mina_B.Cuarzo
        ELSE NULL
    END AS [Cuarzo Final B],

    CASE
        WHEN rep.TM1_TurnoB_Quimico > 0.75
         AND clay_B.Cuarzo IS NOT NULL
            THEN 'TORRE'
        WHEN mina_B.Cuarzo IS NOT NULL
            THEN mina_B.Fuente_Dato
        ELSE 'SIN_DATO'
    END AS [Fuente Cuarzo B]

FROM dias AS d

LEFT OUTER JOIN inventar_SpcHidr.representatividad_torres_resultado AS rep
    ON d.Fecha = rep.Dia

LEFT OUTER JOIN lab AS lab_A
    ON d.Fecha = lab_A.Fecha
   AND lab_A.Turno = 'A'
   AND lab_A.Torre = 'T1'

LEFT OUTER JOIN lab AS lab_B
    ON d.Fecha = lab_B.Fecha
   AND lab_B.Turno = 'B'
   AND lab_B.Torre = 'T1'

LEFT OUTER JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS mina_A
    ON d.Fecha = mina_A.Fecha
   AND mina_A.Turno = 'A'

LEFT OUTER JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS mina_B
    ON d.Fecha = mina_B.Fecha
   AND mina_B.Turno = 'B'

LEFT OUTER JOIN clays AS clay_A
    ON d.Fecha = clay_A.Fecha
   AND clay_A.Turno = 'A'
   AND clay_A.Torre = 'T1'

LEFT OUTER JOIN clays AS clay_B
    ON d.Fecha = clay_B.Fecha
   AND clay_B.Turno = 'B'
   AND clay_B.Torre = 'T1';
