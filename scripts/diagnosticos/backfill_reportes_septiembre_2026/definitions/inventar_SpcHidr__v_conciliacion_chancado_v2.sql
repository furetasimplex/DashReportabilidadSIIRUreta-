CREATE   VIEW inventar_SpcHidr.v_conciliacion_chancado_v2
AS

WITH oficial AS
(
    SELECT
        CAST(Fecha AS date) AS Fecha,

        CASE
            WHEN Turno = 'TA' THEN 'A'
            WHEN Turno = 'TB' THEN 'B'
            ELSE Turno
        END AS Turno,

        SUM(Ton) AS Ton,

        SUM(Ton * PONDCuTG00)
            / NULLIF(SUM(Ton), 0) AS CuT,

        SUM(Ton * PONDCusG01)
            / NULLIF(SUM(Ton), 0) AS CuS,

        SUM
        (
            CASE
                WHEN UPPER(LTRIM(RTRIM(ISNULL(Origen, '')))) = 'STOCK'
                 AND UPPER(LTRIM(RTRIM(ISNULL(Fase, '')))) = 'SRR'
                    THEN 0
                ELSE Ton * PONDCUFE
            END
        )
        /
        NULLIF
        (
            SUM
            (
                CASE
                    WHEN UPPER(LTRIM(RTRIM(ISNULL(Origen, '')))) = 'STOCK'
                     AND UPPER(LTRIM(RTRIM(ISNULL(Fase, '')))) = 'SRR'
                        THEN 0
                    ELSE Ton
                END
            ),
            0
        ) AS CuFe,

        SUM(Ton * PONDC03G02)
            / NULLIF(SUM(Ton), 0) AS CO3,

        SUM
        (
            CASE
                WHEN UPPER(LTRIM(RTRIM(ISNULL(Origen, '')))) = 'STOCK'
                 AND UPPER(LTRIM(RTRIM(ISNULL(Fase, '')))) = 'SRR'
                    THEN 0
                ELSE Ton * PONDFE
            END
        )
        /
        NULLIF
        (
            SUM
            (
                CASE
                    WHEN UPPER(LTRIM(RTRIM(ISNULL(Origen, '')))) = 'STOCK'
                     AND UPPER(LTRIM(RTRIM(ISNULL(Fase, '')))) = 'SRR'
                        THEN 0
                    ELSE Ton
                END
            ),
            0
        ) AS Fe,

        SUM(Ton * POND100G07)
            / NULLIF(SUM(Ton), 0) AS Malla100,

        SUM(Ton * PONDClayBG10)
            / NULLIF(SUM(Ton), 0) AS Clay_Beta,

        CAST(NULL AS float) AS Cuarzo,
        CAST(NULL AS float) AS Caolinita

    FROM inventar_SpcHidr.resumen_mina

    GROUP BY
        CAST(Fecha AS date),
        CASE
            WHEN Turno = 'TA' THEN 'A'
            WHEN Turno = 'TB' THEN 'B'
            ELSE Turno
        END
),

imp AS
(
    SELECT
        Fecha,
        Turno,
        Ton,
        CuT,
        CuS,
        CuFe,
        CO3,
        Fe,
        Malla100,
        Clay_Beta,
        Cuarzo,
        Caolinita
    FROM DEV_SIIR.hidro.v_imp_conciliacion_chancado
),

combinado AS
(
    SELECT
        COALESCE(o.Fecha, i.Fecha) AS Fecha,
        COALESCE(o.Turno, i.Turno) AS Turno,

        CASE
            WHEN i.Fecha IS NOT NULL
             AND ISNULL(i.Ton, 0) > 0
             AND
             (
                 o.Fecha IS NULL
                 OR ISNULL(o.Ton, 0) = 0
             )
                THEN 1
            ELSE 0
        END AS Usar_IMP,

        o.Ton AS Ton_Oficial,
        o.CuT AS CuT_Oficial,
        o.CuS AS CuS_Oficial,
        o.CuFe AS CuFe_Oficial,
        o.CO3 AS CO3_Oficial,
        o.Fe AS Fe_Oficial,
        o.Malla100 AS Malla100_Oficial,
        o.Clay_Beta AS Clay_Beta_Oficial,
        o.Cuarzo AS Cuarzo_Oficial,
        o.Caolinita AS Caolinita_Oficial,

        i.Ton AS Ton_IMP,
        i.CuT AS CuT_IMP,
        i.CuS AS CuS_IMP,
        i.CuFe AS CuFe_IMP,
        i.CO3 AS CO3_IMP,
        i.Fe AS Fe_IMP,
        i.Malla100 AS Malla100_IMP,
        i.Clay_Beta AS Clay_Beta_IMP,
        i.Cuarzo AS Cuarzo_IMP,
        i.Caolinita AS Caolinita_IMP

    FROM oficial AS o

    FULL OUTER JOIN imp AS i
        ON i.Fecha = o.Fecha
       AND i.Turno = o.Turno
)

SELECT
    Fecha,
    Turno,

    CASE
        WHEN Usar_IMP = 1 THEN Ton_IMP
        ELSE Ton_Oficial
    END AS Ton,

    CASE
        WHEN Usar_IMP = 1 THEN CuT_IMP
        ELSE CuT_Oficial
    END AS CuT,

    CASE
        WHEN Usar_IMP = 1 THEN CuS_IMP
        ELSE CuS_Oficial
    END AS CuS,

    CASE
        WHEN Usar_IMP = 1 THEN CuFe_IMP
        ELSE CuFe_Oficial
    END AS CuFe,

    CASE
        WHEN Usar_IMP = 1 THEN CO3_IMP
        ELSE CO3_Oficial
    END AS CO3,

    CASE
        WHEN Usar_IMP = 1 THEN Fe_IMP
        ELSE Fe_Oficial
    END AS Fe,

    CASE
        WHEN Usar_IMP = 1 THEN Malla100_IMP
        ELSE Malla100_Oficial
    END AS Malla100,

    CASE
        WHEN Usar_IMP = 1 THEN Clay_Beta_IMP
        ELSE Clay_Beta_Oficial
    END AS Clay_Beta,

    CASE
        WHEN Usar_IMP = 1 THEN Cuarzo_IMP
        ELSE Cuarzo_Oficial
    END AS Cuarzo,

    CASE
        WHEN Usar_IMP = 1 THEN Caolinita_IMP
        ELSE Caolinita_Oficial
    END AS Caolinita,

    CAST
    (
        CASE
            WHEN Usar_IMP = 1
                THEN 'IMP'

            WHEN Ton_Oficial IS NOT NULL
                THEN 'MINA'

            ELSE 'SIN_DATO'
        END
        AS varchar(20)
    ) AS Fuente_Dato

FROM combinado;
