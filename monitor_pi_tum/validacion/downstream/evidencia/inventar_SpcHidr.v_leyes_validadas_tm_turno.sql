    CREATE   VIEW inventar_SpcHidr.v_leyes_validadas_tm_turno AS

SELECT
    Fecha,
    'TM1' AS TM,
    'A' AS Turno,

    [Rep. TM1 A] AS Representatividad_TM,

    [CuT Final A] AS CuT,
    [Fuente CuT A] AS Fuente_CuT,

    [CuS Final A] AS CuS,
    [Fuente CuS A] AS Fuente_CuS,

    [FeT Final A] AS FeT,
    [Fuente FeT A] AS Fuente_FeT,

    [FeS Final A] AS FeS,
    [Fuente FeS A] AS Fuente_FeS,

    [CO3 Final A] AS CO3,
    [Fuente CO3 A] AS Fuente_CO3,

    [ConsH Final A] AS ConsH,
    [Fuente ConsH A] AS Fuente_ConsH,

    [Malla -1/2 Final A] AS Malla_Menos_1_2,
    [Fuente Malla -1/2 A] AS Fuente_Malla_Menos_1_2,

    [Malla -100 Final A] AS Malla_Menos_100,
    [Fuente Malla -100 A] AS Fuente_Malla_Menos_100,

    [CuFe Final A] AS CuFe,
    [Fuente CuFe A] AS Fuente_CuFe,

    [Caolinita Final A] AS Caolinita,
    [Fuente Caolinita A] AS Fuente_Caolinita,

    [CaolBeta Final A] AS CaolBeta,
    [Fuente CaolBeta A] AS Fuente_CaolBeta,

    [Cuarzo Final A] AS Cuarzo,
    [Fuente Cuarzo A] AS Fuente_Cuarzo

FROM inventar_SpcHidr.v_validacion_leyes_tm1_v2

UNION ALL

SELECT
    Fecha,
    'TM1' AS TM,
    'B' AS Turno,

    [Rep. TM1 B] AS Representatividad_TM,

    [CuT Final B] AS CuT,
    [Fuente CuT B] AS Fuente_CuT,

    [CuS Final B] AS CuS,
    [Fuente CuS B] AS Fuente_CuS,

    [FeT Final B] AS FeT,
    [Fuente FeT B] AS Fuente_FeT,

    [FeS Final B] AS FeS,
    [Fuente FeS B] AS Fuente_FeS,

    [CO3 Final B] AS CO3,
    [Fuente CO3 B] AS Fuente_CO3,

    [ConsH Final B] AS ConsH,
    [Fuente ConsH B] AS Fuente_ConsH,

    [Malla -1/2 Final B] AS Malla_Menos_1_2,
    [Fuente Malla -1/2 B] AS Fuente_Malla_Menos_1_2,

    [Malla -100 Final B] AS Malla_Menos_100,
    [Fuente Malla -100 B] AS Fuente_Malla_Menos_100,

    [CuFe Final B] AS CuFe,
    [Fuente CuFe B] AS Fuente_CuFe,

    [Caolinita Final B] AS Caolinita,
    [Fuente Caolinita B] AS Fuente_Caolinita,

    [CaolBeta Final B] AS CaolBeta,
    [Fuente CaolBeta B] AS Fuente_CaolBeta,

    [Cuarzo Final B] AS Cuarzo,
    [Fuente Cuarzo B] AS Fuente_Cuarzo

FROM inventar_SpcHidr.v_validacion_leyes_tm1_v2

UNION ALL

SELECT
    Fecha,
    'TM2' AS TM,
    'A' AS Turno,

    [Rep. TM2 A] AS Representatividad_TM,

    [CuT Final A] AS CuT,
    [Fuente CuT A] AS Fuente_CuT,

    [CuS Final A] AS CuS,
    [Fuente CuS A] AS Fuente_CuS,

    [FeT Final A] AS FeT,
    [Fuente FeT A] AS Fuente_FeT,

    [FeS Final A] AS FeS,
    [Fuente FeS A] AS Fuente_FeS,

    [CO3 Final A] AS CO3,
    [Fuente CO3 A] AS Fuente_CO3,

    [ConsH Final A] AS ConsH,
    [Fuente ConsH A] AS Fuente_ConsH,

    [Malla -1/2 Final A] AS Malla_Menos_1_2,
    [Fuente Malla -1/2 A] AS Fuente_Malla_Menos_1_2,

    [Malla -100 Final A] AS Malla_Menos_100,
    [Fuente Malla -100 A] AS Fuente_Malla_Menos_100,

    [CuFe Final A] AS CuFe,
    [Fuente CuFe A] AS Fuente_CuFe,

    [Caolinita Final A] AS Caolinita,
    [Fuente Caolinita A] AS Fuente_Caolinita,

    [CaolBeta Final A] AS CaolBeta,
    [Fuente CaolBeta A] AS Fuente_CaolBeta,

    [Cuarzo Final A] AS Cuarzo,
    [Fuente Cuarzo A] AS Fuente_Cuarzo

FROM inventar_SpcHidr.v_validacion_leyes_tm2_v2

UNION ALL

SELECT
    Fecha,
    'TM2' AS TM,
    'B' AS Turno,

    [Rep. TM2 B] AS Representatividad_TM,

    [CuT Final B] AS CuT,
    [Fuente CuT B] AS Fuente_CuT,

    [CuS Final B] AS CuS,
    [Fuente CuS B] AS Fuente_CuS,

    [FeT Final B] AS FeT,
    [Fuente FeT B] AS Fuente_FeT,

    [FeS Final B] AS FeS,
    [Fuente FeS B] AS Fuente_FeS,

    [CO3 Final B] AS CO3,
    [Fuente CO3 B] AS Fuente_CO3,

    [ConsH Final B] AS ConsH,
    [Fuente ConsH B] AS Fuente_ConsH,

    [Malla -1/2 Final B] AS Malla_Menos_1_2,
    [Fuente Malla -1/2 B] AS Fuente_Malla_Menos_1_2,

    [Malla -100 Final B] AS Malla_Menos_100,
    [Fuente Malla -100 B] AS Fuente_Malla_Menos_100,

    [CuFe Final B] AS CuFe,
    [Fuente CuFe B] AS Fuente_CuFe,

    [Caolinita Final B] AS Caolinita,
    [Fuente Caolinita B] AS Fuente_Caolinita,

    [CaolBeta Final B] AS CaolBeta,
    [Fuente CaolBeta B] AS Fuente_CaolBeta,

    [Cuarzo Final B] AS Cuarzo,
    [Fuente Cuarzo B] AS Fuente_Cuarzo

FROM inventar_SpcHidr.v_validacion_leyes_tm2_v2;