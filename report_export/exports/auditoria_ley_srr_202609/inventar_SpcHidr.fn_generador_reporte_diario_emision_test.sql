
CREATE   FUNCTION
    [inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]
(
    @fecha_inicio date,
    @fecha_fin    date
)
RETURNS TABLE
AS
RETURN
(
    WITH base_turno AS
    (
        SELECT
            Fecha,
            Turno,

            Campania,
            Material,
            Modulo,
            Avance,

            Apilado_TMS_Real,

            STOCK,
            MINA,
            SRR,

            CuT_Real,
            CuS_Real,
            CO3_Real,
            CuFe_Real,
            FeT_Real,
            FeS_Real,
            ConsH_Real,

            Malla_Menos_1_2_Real,
            Malla_Menos_100_Real,
            CaolBeta_Real

        FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test]

        WHERE Fecha >= @fecha_inicio
          AND Fecha <  @fecha_fin
    ),

    diario_base AS
    (
        SELECT
            Fecha,

            MAX(Campania) AS Campania,
            MAX(Material) AS Material,
            MAX(Modulo)   AS Modulo,
            MAX(Avance)   AS Avance,

            COUNT(DISTINCT Turno) AS Cantidad_Turnos,

            CASE
                WHEN COUNT(DISTINCT Campania) <= 1
                 AND COUNT(DISTINCT Material) <= 1
                 AND COUNT(DISTINCT Modulo) <= 1
                THEN 'OK'
                ELSE 'REVISAR'
            END AS Flag_Contexto_Dia,

            SUM(COALESCE(Apilado_TMS_Real, 0))
                AS Apilado_TMS_Real_Dia,

            /* Distribución STOCK / MINA / SRR */
            SUM
            (
                CASE
                    WHEN STOCK IS NOT NULL
                    THEN Apilado_TMS_Real * STOCK
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN STOCK IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS STOCK_Dia,

            SUM
            (
                CASE
                    WHEN MINA IS NOT NULL
                    THEN Apilado_TMS_Real * MINA
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN MINA IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS MINA_Dia,

            SUM
            (
                CASE
                    WHEN SRR IS NOT NULL
                    THEN Apilado_TMS_Real * SRR
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN SRR IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS SRR_Dia,

            /* Análisis químicos */
            SUM
            (
                CASE
                    WHEN CuT_Real IS NOT NULL
                    THEN Apilado_TMS_Real * CuT_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN CuT_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS CuT_Real_Dia,

            SUM
            (
                CASE
                    WHEN CuS_Real IS NOT NULL
                    THEN Apilado_TMS_Real * CuS_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN CuS_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS CuS_Real_Dia,

            SUM
            (
                CASE
                    WHEN CO3_Real IS NOT NULL
                    THEN Apilado_TMS_Real * CO3_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN CO3_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS CO3_Real_Dia,

            SUM
            (
                CASE
                    WHEN CuFe_Real IS NOT NULL
                    THEN Apilado_TMS_Real * CuFe_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN CuFe_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS CuFe_Real_Dia,

            SUM
            (
                CASE
                    WHEN FeT_Real IS NOT NULL
                    THEN Apilado_TMS_Real * FeT_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN FeT_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS FeT_Real_Dia,

            SUM
            (
                CASE
                    WHEN FeS_Real IS NOT NULL
                    THEN Apilado_TMS_Real * FeS_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN FeS_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS FeS_Real_Dia,

            SUM
            (
                CASE
                    WHEN ConsH_Real IS NOT NULL
                    THEN Apilado_TMS_Real * ConsH_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN ConsH_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS ConsH_Real_Dia,

            /* Granulometrías y NIR */
            SUM
            (
                CASE
                    WHEN Malla_Menos_1_2_Real IS NOT NULL
                    THEN Apilado_TMS_Real * Malla_Menos_1_2_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN Malla_Menos_1_2_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS Malla_Menos_1_2_Real_Dia,

            SUM
            (
                CASE
                    WHEN Malla_Menos_100_Real IS NOT NULL
                    THEN Apilado_TMS_Real * Malla_Menos_100_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN Malla_Menos_100_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS Malla_Menos_100_Real_Dia,

            SUM
            (
                CASE
                    WHEN CaolBeta_Real IS NOT NULL
                    THEN Apilado_TMS_Real * CaolBeta_Real
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN CaolBeta_Real IS NOT NULL
                        THEN Apilado_TMS_Real
                        ELSE 0
                    END
                ),
                0
            ) AS CaolBeta_Real_Dia

        FROM base_turno

        GROUP BY Fecha
    ),

    diario_derivado AS
    (
        SELECT
            d.*,

            CASE
                WHEN d.CuT_Real_Dia IS NULL
                  OR d.CuT_Real_Dia = 0
                  OR d.CuS_Real_Dia IS NULL
                THEN NULL
                ELSE d.CuS_Real_Dia / d.CuT_Real_Dia
            END AS Solubilidad_Real_Dia

        FROM diario_base d
    ),

    programa AS
    (
        SELECT
            fecha AS Fecha,

            CAST(
    MAX(ton)
    AS decimal(18,6)
) AS Apilado_TMS_Programa,
            MAX(cut)       AS CuT_Programa,
            MAX(cus)       AS CuS_Programa,
            MAX(co3)       AS CO3_Programa,
            MAX(cl_acido)  AS ConsH_Programa,
            MAX(cufe)      AS CuFe_Programa,
            MAX(porc_1_2)  AS Malla_Menos_1_2_Programa,
            MAX(malla_100) AS Malla_Menos_100_Programa,
            MAX(betaclay)  AS CaolBeta_Programa

        FROM [inventar_SpcHidr].[plan_semanal_reporte_turno]

        WHERE fecha >= @fecha_inicio
          AND fecha <  @fecha_fin

        GROUP BY fecha
    ),

    plan_mensual AS
    (
        SELECT
            fecha AS Fecha,

            MAX(apilamiento) AS Apilado_TMS_Plan,
            MAX(cut)         AS CuT_Plan,
            MAX(cus)         AS CuS_Plan,
            MAX(co3)         AS CO3_Plan,
            MAX(cl_acido)    AS ConsH_Plan,
            MAX(cufe)        AS CuFe_Plan,
            MAX(malla_100)   AS Malla_Menos_100_Plan,
            MAX(caol_beta)   AS CaolBeta_Plan

        FROM [inventar_SpcHidr].[plan_mensual_reporte_turno]

        WHERE fecha >= @fecha_inicio
          AND fecha <  @fecha_fin

        GROUP BY fecha
    )

    SELECT
        d.Fecha,

        d.Campania,
        d.Material AS Material_Operacion,

        CASE
            WHEN d.Solubilidad_Real_Dia IS NULL
                THEN NULL

            WHEN d.Solubilidad_Real_Dia <= 0.25
                THEN 'SULFURO'

            WHEN d.Solubilidad_Real_Dia <= 0.50
                THEN 'MIXTO'

            ELSE 'OXIDO'
        END AS Clasificacion_Solubilidad,

        d.Modulo,
        d.Avance,

        d.Apilado_TMS_Real_Dia,
        pr.Apilado_TMS_Programa,
        pl.Apilado_TMS_Plan,

        d.STOCK_Dia,
        d.MINA_Dia,
        d.SRR_Dia,

        d.CuT_Real_Dia,
        pr.CuT_Programa,
        pl.CuT_Plan,

        d.CuS_Real_Dia,
        pr.CuS_Programa,
        pl.CuS_Plan,

        d.Solubilidad_Real_Dia,

        CASE
            WHEN pr.CuT_Programa IS NULL
              OR pr.CuT_Programa = 0
              OR pr.CuS_Programa IS NULL
            THEN NULL
            ELSE pr.CuS_Programa / pr.CuT_Programa
        END AS Solubilidad_Programa,

        CASE
            WHEN pl.CuT_Plan IS NULL
              OR pl.CuT_Plan = 0
              OR pl.CuS_Plan IS NULL
            THEN NULL
            ELSE pl.CuS_Plan / pl.CuT_Plan
        END AS Solubilidad_Plan,

        d.CO3_Real_Dia,
        pr.CO3_Programa,
        pl.CO3_Plan,

        d.CuFe_Real_Dia,
        pr.CuFe_Programa,
        pl.CuFe_Plan,

        d.FeT_Real_Dia,
        d.FeS_Real_Dia,
        d.ConsH_Real_Dia,

        d.Malla_Menos_1_2_Real_Dia,
        pr.Malla_Menos_1_2_Programa,

        d.Malla_Menos_100_Real_Dia,
        pr.Malla_Menos_100_Programa,
        pl.Malla_Menos_100_Plan,

        d.CaolBeta_Real_Dia,
        pr.CaolBeta_Programa,
        pl.CaolBeta_Plan,

CAST
(
    ROUND(
        CASE
            WHEN d.Apilado_TMS_Real_Dia IS NULL
              OR d.Apilado_TMS_Real_Dia = 0
              OR d.Solubilidad_Real_Dia IS NULL
              OR d.CO3_Real_Dia IS NULL
            THEN NULL

            WHEN ISNULL(d.Solubilidad_Real_Dia, 0) < 0.25
            THEN
                CASE
                    WHEN ISNULL(d.CO3_Real_Dia, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(d.CO3_Real_Dia, 0))
                END

            ELSE
                CASE
                    WHEN d.CuS_Real_Dia IS NULL OR d.CuS_Real_Dia <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(d.CuS_Real_Dia))
                               + 18.99
                               + (15.51 * ISNULL(d.CO3_Real_Dia, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(d.CuS_Real_Dia))
                               + 18.99
                               + (15.51 * ISNULL(d.CO3_Real_Dia, 0))
                        END
                END
        END
    , 2)
    AS decimal(18, 2)
) AS Dosis_Acido_Ideal_Dia,

     CAST
(
    ROUND(
        CASE
            WHEN pr.CuT_Programa IS NULL
              OR pr.CuT_Programa = 0
              OR pr.CuS_Programa IS NULL
              OR pr.CO3_Programa IS NULL
            THEN NULL

            WHEN ISNULL(pr.CuS_Programa / NULLIF(pr.CuT_Programa, 0), 0) < 0.25
            THEN
                CASE
                    WHEN ISNULL(pr.CO3_Programa, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(pr.CO3_Programa, 0))
                END

            ELSE
                CASE
                    WHEN pr.CuS_Programa IS NULL OR pr.CuS_Programa <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(pr.CuS_Programa))
                               + 18.99
                               + (15.51 * ISNULL(pr.CO3_Programa, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(pr.CuS_Programa))
                               + 18.99
                               + (15.51 * ISNULL(pr.CO3_Programa, 0))
                        END
                END
        END
    , 2)
    AS decimal(18, 2)
) AS Dosis_Acido_Programa_Semanal,
        d.Cantidad_Turnos,
        d.Flag_Contexto_Dia

    FROM diario_derivado d

    LEFT JOIN programa pr
        ON pr.Fecha = d.Fecha

    LEFT JOIN plan_mensual pl
        ON pl.Fecha = d.Fecha
);
