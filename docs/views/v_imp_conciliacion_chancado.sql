-- Fuente: definición vigente en PROD_SIIR (sys.sql_modules).
-- Extraída: 2026-08-05 16:42:45.363000
USE [PROD_SIIR];
GO

CREATE   VIEW [hidro].[v_imp_conciliacion_chancado]
AS

SELECT
    n.Fecha,
    n.Turno,

    SUM(n.Ton) AS Ton,

    SUM(
        CASE
            WHEN n.CuT BETWEEN 0 AND 100
                THEN n.Ton * n.CuT
            ELSE 0
        END
    )
    /
    NULLIF(
        SUM(
            CASE
                WHEN n.CuT BETWEEN 0 AND 100
                    THEN n.Ton
                ELSE 0
            END
        ),
        0
    ) AS CuT,

    SUM(
        CASE
            WHEN n.CuS BETWEEN 0 AND 100
                THEN n.Ton * n.CuS
            ELSE 0
        END
    )
    /
    NULLIF(
        SUM(
            CASE
                WHEN n.CuS BETWEEN 0 AND 100
                    THEN n.Ton
                ELSE 0
            END
        ),
        0
    ) AS CuS,

    SUM(
        CASE
            WHEN n.Es_SRR = 0
             AND n.CuFe BETWEEN 0 AND 100
                THEN n.Ton * n.CuFe
            ELSE 0
        END
    )
    /
    NULLIF(
        SUM(
            CASE
                WHEN n.Es_SRR = 0
                 AND n.CuFe BETWEEN 0 AND 100
                    THEN n.Ton
                ELSE 0
            END
        ),
        0
    ) AS CuFe,

    SUM(
        CASE
            WHEN n.CO3 BETWEEN 0 AND 100
                THEN n.Ton * n.CO3
            ELSE 0
        END
    )
    /
    NULLIF(
        SUM(
            CASE
                WHEN n.CO3 BETWEEN 0 AND 100
                    THEN n.Ton
                ELSE 0
            END
        ),
        0
    ) AS CO3,

    SUM(
        CASE
            WHEN n.Es_SRR = 0
             AND n.Fe BETWEEN 0 AND 100
                THEN n.Ton * n.Fe
            ELSE 0
        END
    )
    /
    NULLIF(
        SUM(
            CASE
                WHEN n.Es_SRR = 0
                 AND n.Fe BETWEEN 0 AND 100
                    THEN n.Ton
                ELSE 0
            END
        ),
        0
    ) AS Fe,

    SUM(
        CASE
            WHEN n.Malla100 BETWEEN 0 AND 100
                THEN n.Ton * n.Malla100
            ELSE 0
        END
    )
    /
    NULLIF(
        SUM(
            CASE
                WHEN n.Malla100 BETWEEN 0 AND 100
                    THEN n.Ton
                ELSE 0
            END
        ),
        0
    ) AS Malla100,

    SUM(
        CASE
            WHEN n.Clay BETWEEN 0 AND 100
                THEN n.Ton * n.Clay
            ELSE 0
        END
    )
    /
    NULLIF(
        SUM(
            CASE
                WHEN n.Clay BETWEEN 0 AND 100
                    THEN n.Ton
                ELSE 0
            END
        ),
        0
    ) AS Clay_Beta,

    CAST(NULL AS float) AS Cuarzo,
    CAST(NULL AS float) AS Caolinita

FROM hidro.v_imp_chancado_normalizado AS n

GROUP BY
    n.Fecha,
    n.Turno;
GO
