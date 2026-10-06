CREATE   VIEW inventar_SpcHidr.v_validacion_leyes_tm2_v2
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
        MAX
        (
            TRY_CONVERT
            (
                float,
                REPLACE(REPLACE(Caolinita, ',', '.'), '%', '')
            )
        ) AS Caolinita,
        MAX
        (
            TRY_CONVERT
            (
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
),
base AS
(
    SELECT
        d.Fecha,
        x.Turno,

        CASE
            WHEN x.Turno = 'A'
                THEN rep.TM2_TurnoA_Quimico
            WHEN x.Turno = 'B'
                THEN rep.TM2_TurnoB_Quimico
        END AS Rep_TM2,

        CASE
            WHEN x.Turno = 'A'
                THEN rep.TM2_TurnoA_Fisico
            WHEN x.Turno = 'B'
                THEN rep.TM2_TurnoB_Fisico
        END AS Rep_Fisica_TM2,

        lab.CuT_global,
        lab.CuS_Global,
        lab.Fe_Global,
        lab.FeS_Global,
        lab.Carb_Global,
        lab.Cons_KgTon,
        lab.Pasante_1_2P,
        lab.Pasante_100m,
        lab.CuFe_Global,

        mina.CuT AS CuT_Mina,
        mina.CuS AS CuS_Mina,
        mina.Fe AS FeT_Mina,
        mina.CO3 AS CO3_Mina,
        mina.Malla100 AS Malla100_Mina,
        mina.CuFe AS CuFe_Mina,
        mina.Caolinita AS Caolinita_Mina,
        mina.Clay_Beta AS CaolBeta_Mina,
        mina.Cuarzo AS Cuarzo_Mina,

        /* Nueva trazabilidad: MINA o IMP */
        mina.Fuente_Dato AS Fuente_Conciliacion,

        clay.Caolinita AS Caolinita_Clays,
        clay.Cuarzo AS Cuarzo_Clays,
        clay.CaolBeta AS CaolBeta_Clays,
        clay.CuFe AS CuFe_Clays

    FROM dias AS d

    CROSS APPLY
    (
        VALUES ('A'), ('B')
    ) AS x(Turno)

    LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado AS rep
        ON d.Fecha = rep.Dia

    LEFT JOIN lab
        ON d.Fecha = lab.Fecha
       AND x.Turno = lab.Turno
       AND lab.Torre = 'T2'

    LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS mina
        ON d.Fecha = mina.Fecha
       AND x.Turno = mina.Turno

    LEFT JOIN clays AS clay
        ON d.Fecha = clay.Fecha
       AND x.Turno = clay.Turno
       AND clay.Torre = 'T2'
),
calc AS
(
    SELECT
        Fecha,
        Turno,
        Rep_TM2,
        Rep_Fisica_TM2,

        /* ========================================================
           CuT
           ======================================================== */

        CuT_global AS CuT_Torre,
        CuT_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND CuT_global IS NOT NULL
                THEN CuT_global
            WHEN CuT_Mina IS NOT NULL
                THEN CuT_Mina
            ELSE NULL
        END AS CuT_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND CuT_global IS NOT NULL
                THEN 'TORRE'
            WHEN CuT_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_CuT,

        /* ========================================================
           CuS
           ======================================================== */

        CuS_Global AS CuS_Torre,
        CuS_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND CuS_Global IS NOT NULL
                THEN CuS_Global
            WHEN CuS_Mina IS NOT NULL
                THEN CuS_Mina
            ELSE NULL
        END AS CuS_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND CuS_Global IS NOT NULL
                THEN 'TORRE'
            WHEN CuS_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_CuS,

        /* ========================================================
           FeT
           ======================================================== */

        Fe_Global AS FeT_Torre,
        FeT_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Fe_Global IS NOT NULL
                THEN Fe_Global
            WHEN FeT_Mina IS NOT NULL
                THEN FeT_Mina
            ELSE NULL
        END AS FeT_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Fe_Global IS NOT NULL
                THEN 'TORRE'
            WHEN FeT_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_FeT,

        /* ========================================================
           FeS: lógica original sin modificaciones
           ======================================================== */

        FeS_Global AS FeS_Torre,
        CAST(NULL AS float) AS FeS_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND FeS_Global IS NOT NULL
                THEN FeS_Global
            ELSE 0
        END AS FeS_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND FeS_Global IS NOT NULL
                THEN 'TORRE'
            ELSE 'NO_APLICA_MINA'
        END AS Fuente_FeS,

        /* ========================================================
           CO3
           ======================================================== */

        Carb_Global AS CO3_Torre,
        CO3_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Carb_Global IS NOT NULL
                THEN Carb_Global
            WHEN CO3_Mina IS NOT NULL
                THEN CO3_Mina
            ELSE NULL
        END AS CO3_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Carb_Global IS NOT NULL
                THEN 'TORRE'
            WHEN CO3_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_CO3,

        /* ========================================================
           ConsH: lógica original sin modificaciones
           ======================================================== */

        Cons_KgTon AS ConsH_Torre,
        CAST(NULL AS float) AS ConsH_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Cons_KgTon IS NOT NULL
                THEN Cons_KgTon
            ELSE 0
        END AS ConsH_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Cons_KgTon IS NOT NULL
                THEN 'TORRE'
            ELSE 'NO_APLICA_MINA'
        END AS Fuente_ConsH,

        /* ========================================================
           Malla -1/2: lógica original sin modificaciones
           ======================================================== */

        Pasante_1_2P AS Malla_1_2_Torre,
        CAST(NULL AS float) AS Malla_1_2_Mina,

        CASE
            WHEN Rep_Fisica_TM2 > 0.75
             AND Pasante_1_2P IS NOT NULL
                THEN Pasante_1_2P
            ELSE 0
        END AS Malla_1_2_Final,

        CASE
            WHEN Rep_Fisica_TM2 > 0.75
             AND Pasante_1_2P IS NOT NULL
                THEN 'TORRE'
            ELSE 'NO_APLICA_MINA'
        END AS Fuente_Malla_1_2,

        /* ========================================================
           Malla -100
           ======================================================== */

        Pasante_100m AS Malla100_Torre,
        Malla100_Mina,

        CASE
            WHEN Rep_Fisica_TM2 > 0.75
             AND Pasante_100m IS NOT NULL
                THEN Pasante_100m
            WHEN Malla100_Mina IS NOT NULL
                THEN Malla100_Mina
            ELSE NULL
        END AS Malla100_Final,

        CASE
            WHEN Rep_Fisica_TM2 > 0.75
             AND Pasante_100m IS NOT NULL
                THEN 'TORRE'
            WHEN Malla100_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_Malla100,

        /* ========================================================
           CuFe
           ======================================================== */

        COALESCE(CuFe_Clays, CuFe_Global) AS CuFe_Torre,
        CuFe_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND COALESCE(CuFe_Clays, CuFe_Global) IS NOT NULL
                THEN COALESCE(CuFe_Clays, CuFe_Global)
            WHEN CuFe_Mina IS NOT NULL
                THEN CuFe_Mina
            ELSE NULL
        END AS CuFe_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND COALESCE(CuFe_Clays, CuFe_Global) IS NOT NULL
                THEN 'TORRE'
            WHEN CuFe_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_CuFe,

        /* ========================================================
           Caolinita
           ======================================================== */

        Caolinita_Clays AS Caolinita_Torre,
        Caolinita_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Caolinita_Clays IS NOT NULL
                THEN Caolinita_Clays
            WHEN Caolinita_Mina IS NOT NULL
                THEN Caolinita_Mina
            ELSE NULL
        END AS Caolinita_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Caolinita_Clays IS NOT NULL
                THEN 'TORRE'
            WHEN Caolinita_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_Caolinita,

        /* ========================================================
           CaolBeta
           ======================================================== */

        CaolBeta_Clays AS CaolBeta_Torre,
        CaolBeta_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND CaolBeta_Clays IS NOT NULL
                THEN CaolBeta_Clays
            WHEN CaolBeta_Mina IS NOT NULL
                THEN CaolBeta_Mina
            ELSE NULL
        END AS CaolBeta_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND CaolBeta_Clays IS NOT NULL
                THEN 'TORRE'
            WHEN CaolBeta_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_CaolBeta,

        /* ========================================================
           Cuarzo
           ======================================================== */

        Cuarzo_Clays AS Cuarzo_Torre,
        Cuarzo_Mina,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Cuarzo_Clays IS NOT NULL
                THEN Cuarzo_Clays
            WHEN Cuarzo_Mina IS NOT NULL
                THEN Cuarzo_Mina
            ELSE NULL
        END AS Cuarzo_Final,

        CASE
            WHEN Rep_TM2 > 0.75
             AND Cuarzo_Clays IS NOT NULL
                THEN 'TORRE'
            WHEN Cuarzo_Mina IS NOT NULL
                THEN Fuente_Conciliacion
            ELSE 'SIN_DATO'
        END AS Fuente_Cuarzo

    FROM base
)

SELECT
    Fecha,

    MAX(CASE WHEN Turno = 'A' THEN Rep_TM2 END) AS [Rep. TM2 A],
    MAX(CASE WHEN Turno = 'B' THEN Rep_TM2 END) AS [Rep. TM2 B],

    MAX(CASE WHEN Turno = 'A' THEN CuT_Torre END) AS [CuT Torre A],
    MAX(CASE WHEN Turno = 'A' THEN CuT_Mina END) AS [CuT Mina A],
    MAX(CASE WHEN Turno = 'A' THEN CuT_Final END) AS [CuT Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_CuT END) AS [Fuente CuT A],

    MAX(CASE WHEN Turno = 'B' THEN CuT_Torre END) AS [CuT Torre B],
    MAX(CASE WHEN Turno = 'B' THEN CuT_Mina END) AS [CuT Mina B],
    MAX(CASE WHEN Turno = 'B' THEN CuT_Final END) AS [CuT Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_CuT END) AS [Fuente CuT B],

    MAX(CASE WHEN Turno = 'A' THEN CuS_Torre END) AS [CuS Torre A],
    MAX(CASE WHEN Turno = 'A' THEN CuS_Mina END) AS [CuS Mina A],
    MAX(CASE WHEN Turno = 'A' THEN CuS_Final END) AS [CuS Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_CuS END) AS [Fuente CuS A],

    MAX(CASE WHEN Turno = 'B' THEN CuS_Torre END) AS [CuS Torre B],
    MAX(CASE WHEN Turno = 'B' THEN CuS_Mina END) AS [CuS Mina B],
    MAX(CASE WHEN Turno = 'B' THEN CuS_Final END) AS [CuS Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_CuS END) AS [Fuente CuS B],

    MAX(CASE WHEN Turno = 'A' THEN FeT_Torre END) AS [FeT Torre A],
    MAX(CASE WHEN Turno = 'A' THEN FeT_Mina END) AS [FeT Mina A],
    MAX(CASE WHEN Turno = 'A' THEN FeT_Final END) AS [FeT Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_FeT END) AS [Fuente FeT A],

    MAX(CASE WHEN Turno = 'B' THEN FeT_Torre END) AS [FeT Torre B],
    MAX(CASE WHEN Turno = 'B' THEN FeT_Mina END) AS [FeT Mina B],
    MAX(CASE WHEN Turno = 'B' THEN FeT_Final END) AS [FeT Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_FeT END) AS [Fuente FeT B],

    MAX(CASE WHEN Turno = 'A' THEN FeS_Torre END) AS [FeS Torre A],
    MAX(CASE WHEN Turno = 'A' THEN FeS_Mina END) AS [FeS Mina A],
    MAX(CASE WHEN Turno = 'A' THEN FeS_Final END) AS [FeS Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_FeS END) AS [Fuente FeS A],

    MAX(CASE WHEN Turno = 'B' THEN FeS_Torre END) AS [FeS Torre B],
    MAX(CASE WHEN Turno = 'B' THEN FeS_Mina END) AS [FeS Mina B],
    MAX(CASE WHEN Turno = 'B' THEN FeS_Final END) AS [FeS Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_FeS END) AS [Fuente FeS B],

    MAX(CASE WHEN Turno = 'A' THEN CO3_Torre END) AS [CO3 Torre A],
    MAX(CASE WHEN Turno = 'A' THEN CO3_Mina END) AS [CO3 Mina A],
    MAX(CASE WHEN Turno = 'A' THEN CO3_Final END) AS [CO3 Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_CO3 END) AS [Fuente CO3 A],

    MAX(CASE WHEN Turno = 'B' THEN CO3_Torre END) AS [CO3 Torre B],
    MAX(CASE WHEN Turno = 'B' THEN CO3_Mina END) AS [CO3 Mina B],
    MAX(CASE WHEN Turno = 'B' THEN CO3_Final END) AS [CO3 Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_CO3 END) AS [Fuente CO3 B],

    MAX(CASE WHEN Turno = 'A' THEN ConsH_Torre END) AS [ConsH Torre A],
    MAX(CASE WHEN Turno = 'A' THEN ConsH_Mina END) AS [ConsH Mina A],
    MAX(CASE WHEN Turno = 'A' THEN ConsH_Final END) AS [ConsH Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_ConsH END) AS [Fuente ConsH A],

    MAX(CASE WHEN Turno = 'B' THEN ConsH_Torre END) AS [ConsH Torre B],
    MAX(CASE WHEN Turno = 'B' THEN ConsH_Mina END) AS [ConsH Mina B],
    MAX(CASE WHEN Turno = 'B' THEN ConsH_Final END) AS [ConsH Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_ConsH END) AS [Fuente ConsH B],

    MAX(CASE WHEN Turno = 'A' THEN Malla_1_2_Torre END) AS [Malla -1/2 Torre A],
    MAX(CASE WHEN Turno = 'A' THEN Malla_1_2_Mina END) AS [Malla -1/2 Mina A],
    MAX(CASE WHEN Turno = 'A' THEN Malla_1_2_Final END) AS [Malla -1/2 Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_Malla_1_2 END) AS [Fuente Malla -1/2 A],

    MAX(CASE WHEN Turno = 'B' THEN Malla_1_2_Torre END) AS [Malla -1/2 Torre B],
    MAX(CASE WHEN Turno = 'B' THEN Malla_1_2_Mina END) AS [Malla -1/2 Mina B],
    MAX(CASE WHEN Turno = 'B' THEN Malla_1_2_Final END) AS [Malla -1/2 Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_Malla_1_2 END) AS [Fuente Malla -1/2 B],

    MAX(CASE WHEN Turno = 'A' THEN Malla100_Torre END) AS [Malla -100 Torre A],
    MAX(CASE WHEN Turno = 'A' THEN Malla100_Mina END) AS [Malla -100 Mina A],
    MAX(CASE WHEN Turno = 'A' THEN Malla100_Final END) AS [Malla -100 Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_Malla100 END) AS [Fuente Malla -100 A],

    MAX(CASE WHEN Turno = 'B' THEN Malla100_Torre END) AS [Malla -100 Torre B],
    MAX(CASE WHEN Turno = 'B' THEN Malla100_Mina END) AS [Malla -100 Mina B],
    MAX(CASE WHEN Turno = 'B' THEN Malla100_Final END) AS [Malla -100 Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_Malla100 END) AS [Fuente Malla -100 B],

    MAX(CASE WHEN Turno = 'A' THEN CuFe_Torre END) AS [CuFe Torre A],
    MAX(CASE WHEN Turno = 'A' THEN CuFe_Mina END) AS [CuFe Mina A],
    MAX(CASE WHEN Turno = 'A' THEN CuFe_Final END) AS [CuFe Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_CuFe END) AS [Fuente CuFe A],

    MAX(CASE WHEN Turno = 'B' THEN CuFe_Torre END) AS [CuFe Torre B],
    MAX(CASE WHEN Turno = 'B' THEN CuFe_Mina END) AS [CuFe Mina B],
    MAX(CASE WHEN Turno = 'B' THEN CuFe_Final END) AS [CuFe Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_CuFe END) AS [Fuente CuFe B],

    MAX(CASE WHEN Turno = 'A' THEN Caolinita_Torre END) AS [Caolinita Torre A],
    MAX(CASE WHEN Turno = 'A' THEN Caolinita_Mina END) AS [Caolinita Mina A],
    MAX(CASE WHEN Turno = 'A' THEN Caolinita_Final END) AS [Caolinita Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_Caolinita END) AS [Fuente Caolinita A],

    MAX(CASE WHEN Turno = 'B' THEN Caolinita_Torre END) AS [Caolinita Torre B],
    MAX(CASE WHEN Turno = 'B' THEN Caolinita_Mina END) AS [Caolinita Mina B],
    MAX(CASE WHEN Turno = 'B' THEN Caolinita_Final END) AS [Caolinita Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_Caolinita END) AS [Fuente Caolinita B],

    MAX(CASE WHEN Turno = 'A' THEN CaolBeta_Torre END) AS [CaolBeta Torre A],
    MAX(CASE WHEN Turno = 'A' THEN CaolBeta_Mina END) AS [CaolBeta Mina A],
    MAX(CASE WHEN Turno = 'A' THEN CaolBeta_Final END) AS [CaolBeta Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_CaolBeta END) AS [Fuente CaolBeta A],

    MAX(CASE WHEN Turno = 'B' THEN CaolBeta_Torre END) AS [CaolBeta Torre B],
    MAX(CASE WHEN Turno = 'B' THEN CaolBeta_Mina END) AS [CaolBeta Mina B],
    MAX(CASE WHEN Turno = 'B' THEN CaolBeta_Final END) AS [CaolBeta Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_CaolBeta END) AS [Fuente CaolBeta B],

    MAX(CASE WHEN Turno = 'A' THEN Cuarzo_Torre END) AS [Cuarzo Torre A],
    MAX(CASE WHEN Turno = 'A' THEN Cuarzo_Mina END) AS [Cuarzo Mina A],
    MAX(CASE WHEN Turno = 'A' THEN Cuarzo_Final END) AS [Cuarzo Final A],
    MAX(CASE WHEN Turno = 'A' THEN Fuente_Cuarzo END) AS [Fuente Cuarzo A],

    MAX(CASE WHEN Turno = 'B' THEN Cuarzo_Torre END) AS [Cuarzo Torre B],
    MAX(CASE WHEN Turno = 'B' THEN Cuarzo_Mina END) AS [Cuarzo Mina B],
    MAX(CASE WHEN Turno = 'B' THEN Cuarzo_Final END) AS [Cuarzo Final B],
    MAX(CASE WHEN Turno = 'B' THEN Fuente_Cuarzo END) AS [Fuente Cuarzo B]

FROM calc
GROUP BY Fecha;
