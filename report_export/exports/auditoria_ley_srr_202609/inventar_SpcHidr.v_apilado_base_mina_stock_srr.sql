    CREATE   VIEW inventar_SpcHidr.v_apilado_base_mina_stock_srr AS

WITH base AS (
    SELECT
        CAST(Fecha AS date) AS Fecha,

        CASE
            WHEN Turno IN ('TA', 'A') THEN 'A'
            WHEN Turno IN ('TB', 'B') THEN 'B'
            ELSE Turno
        END AS Turno,

        SUM(
            CASE 
                WHEN Origen = 'Stock' 
                 AND Fase <> 'SRR'
                    THEN COALESCE(Ton, 0)
                ELSE 0
            END
        ) AS Ton_Stock_Camiones,

        SUM(
            CASE 
                WHEN Origen = 'Mina'
                    THEN COALESCE(Ton, 0)
                ELSE 0
            END
        ) AS Ton_Mina_Camiones,

        SUM(
            CASE 
                WHEN Origen = 'Stock'
                 AND Fase = 'SRR'
                    THEN COALESCE(Ton, 0)
                ELSE 0
            END
        ) AS Ton_SRR

    FROM inventar_SpcHidr.mov_cam
    WHERE Fecha IS NOT NULL
    GROUP BY
        CAST(Fecha AS date),
        CASE
            WHEN Turno IN ('TA', 'A') THEN 'A'
            WHEN Turno IN ('TB', 'B') THEN 'B'
            ELSE Turno
        END
)

SELECT
    Fecha,
    Turno,

    Ton_Stock_Camiones,
    Ton_Mina_Camiones,
    Ton_SRR,

    Ton_Stock_Camiones + Ton_Mina_Camiones AS Ton_Stock_Mina_Camiones,

    CASE
        WHEN Ton_Stock_Camiones + Ton_Mina_Camiones = 0 THEN 0
        ELSE Ton_Stock_Camiones 
             / NULLIF(Ton_Stock_Camiones + Ton_Mina_Camiones, 0)
    END AS Prop_Stock_Camiones,

    CASE
        WHEN Ton_Stock_Camiones + Ton_Mina_Camiones = 0 THEN 0
        ELSE Ton_Mina_Camiones
             / NULLIF(Ton_Stock_Camiones + Ton_Mina_Camiones, 0)
    END AS Prop_Mina_Camiones

FROM base;