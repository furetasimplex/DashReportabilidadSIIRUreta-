CREATE   VIEW
inventar_SpcHidr.v_estado_apilado_turno_representatividad
AS

SELECT
    CAST(Fecha AS date) AS Fecha,
    CAST('A' AS varchar(1)) AS Turno,

    CAST(
        COALESCE(TMH_Apilado_Total_A, 0)
        AS decimal(18, 3)
    ) AS Apilado_TMH_Base,

    Flag_Apilado_Valido_A AS Flag_Apilado_Valido,

    CASE
        WHEN Flag_Apilado_Valido_A = 1
         AND COALESCE(TMH_Apilado_Total_A, 0) > 0
            THEN CAST(1 AS bit)
        ELSE CAST(0 AS bit)
    END AS Turno_Evaluable

FROM inventar_SpcHidr.v_datos_apilado_tmh_v2

UNION ALL

SELECT
    CAST(Fecha AS date) AS Fecha,
    CAST('B' AS varchar(1)) AS Turno,

    CAST(
        COALESCE(TMH_Apilado_Total_B, 0)
        AS decimal(18, 3)
    ) AS Apilado_TMH_Base,

    Flag_Apilado_Valido_B AS Flag_Apilado_Valido,

    CASE
        WHEN Flag_Apilado_Valido_B = 1
         AND COALESCE(TMH_Apilado_Total_B, 0) > 0
            THEN CAST(1 AS bit)
        ELSE CAST(0 AS bit)
    END AS Turno_Evaluable

FROM inventar_SpcHidr.v_datos_apilado_tmh_v2;
