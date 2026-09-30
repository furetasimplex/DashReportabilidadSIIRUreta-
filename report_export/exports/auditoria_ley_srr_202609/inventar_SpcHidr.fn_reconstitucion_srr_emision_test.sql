CREATE   FUNCTION
[inventar_SpcHidr].[fn_reconstitucion_srr_emision_test]
(
    @fecha_inicio date,
    @fecha_fin    date
)
RETURNS TABLE
AS
RETURN
(
    WITH generador AS
    (
        SELECT
            Fecha,
            Apilado_TMS_Real_Dia,
            CuT_Real_Dia,
            CuS_Real_Dia,
            CO3_Real_Dia,
            Malla_Menos_100_Real_Dia,
            CaolBeta_Real_Dia
        FROM [inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]
        (
            @fecha_inicio,
            @fecha_fin
        )
    ),

    mb_mina_stock AS
    (
        SELECT
            CAST(r.Fecha AS date) AS Fecha,

            SUM(
                CASE
                    WHEN NOT
                    (
                        UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                        AND
                        UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                    )
                    THEN COALESCE(r.Ton,0)
                    ELSE 0
                END
            ) AS TMS_MB_MinaStock,

            /* ============================
               CuT Mina + Stock sin SRR
               ============================ */
            SUM(
                CASE
                    WHEN NOT
                    (
                        UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                        AND
                        UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                    )
                    AND r.PONDCuTG00 IS NOT NULL
                    THEN COALESCE(r.Ton,0) * r.PONDCuTG00
                    ELSE 0
                END
            )
            /
            NULLIF(
                SUM(
                    CASE
                        WHEN NOT
                        (
                            UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                            AND
                            UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                        )
                        AND r.PONDCuTG00 IS NOT NULL
                        THEN COALESCE(r.Ton,0)
                        ELSE 0
                    END
                ),
                0
            ) AS CuT_MinaStock,

            /* CuS */
            SUM(
                CASE
                    WHEN NOT
                    (
                        UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                        AND
                        UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                    )
                    AND r.PONDCusG01 IS NOT NULL
                    THEN COALESCE(r.Ton,0) * r.PONDCusG01
                    ELSE 0
                END
            )
            /
            NULLIF(
                SUM(
                    CASE
                        WHEN NOT
                        (
                            UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                            AND
                            UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                        )
                        AND r.PONDCusG01 IS NOT NULL
                        THEN COALESCE(r.Ton,0)
                        ELSE 0
                    END
                ),
                0
            ) AS CuS_MinaStock,

            /* CO3 */
            SUM(
                CASE
                    WHEN NOT
                    (
                        UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                        AND
                        UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                    )
                    AND r.PONDC03G02 IS NOT NULL
                    THEN COALESCE(r.Ton,0) * r.PONDC03G02
                    ELSE 0
                END
            )
            /
            NULLIF(
                SUM(
                    CASE
                        WHEN NOT
                        (
                            UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                            AND
                            UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                        )
                        AND r.PONDC03G02 IS NOT NULL
                        THEN COALESCE(r.Ton,0)
                        ELSE 0
                    END
                ),
                0
            ) AS CO3_MinaStock,

            /* Malla -100 */
            SUM(
                CASE
                    WHEN NOT
                    (
                        UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                        AND
                        UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                    )
                    AND r.POND100G07 IS NOT NULL
                    THEN COALESCE(r.Ton,0) * r.POND100G07
                    ELSE 0
                END
            )
            /
            NULLIF(
                SUM(
                    CASE
                        WHEN NOT
                        (
                            UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                            AND
                            UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                        )
                        AND r.POND100G07 IS NOT NULL
                        THEN COALESCE(r.Ton,0)
                        ELSE 0
                    END
                ),
                0
            ) AS Malla100_MinaStock,

            /* ============================================================
               ClayBeta Mina + Stock sin SRR
               Mismo criterio MB que CuT / CuS / CO3 / Malla100
               ============================================================ */
            SUM(
                CASE
                    WHEN NOT
                    (
                        UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                        AND
                        UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                    )
                    AND r.PONDClayBG10 IS NOT NULL
                    THEN COALESCE(r.Ton,0) * r.PONDClayBG10
                    ELSE 0
                END
            )
            /
            NULLIF(
                SUM(
                    CASE
                        WHEN NOT
                        (
                            UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
                            AND
                            UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'
                        )
                        AND r.PONDClayBG10 IS NOT NULL
                        THEN COALESCE(r.Ton,0)
                        ELSE 0
                    END
                ),
                0
            ) AS ClayBeta_MinaStock

        FROM [inventar_SpcHidr].[resumen_mina] r

        WHERE CAST(r.Fecha AS date) >= @fecha_inicio
          AND CAST(r.Fecha AS date) <  @fecha_fin

        GROUP BY CAST(r.Fecha AS date)
    ),

mb_srr AS
(
    SELECT
        CAST(r.Fecha AS date) AS Fecha,

        /* =====================================================
           Masa SRR directa MB
           ===================================================== */
        SUM(COALESCE(r.Ton,0)) AS TMS_MB_SRR,

        /* =====================================================
           CuT SRR MB
           SOLO DIAGNÓSTICO
           ===================================================== */
        SUM(
            CASE
                WHEN r.PONDCuTG00 IS NOT NULL
                THEN COALESCE(r.Ton,0) * r.PONDCuTG00
                ELSE 0
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN r.PONDCuTG00 IS NOT NULL
                    THEN COALESCE(r.Ton,0)
                    ELSE 0
                END
            ),
            0
        ) AS CuT_SRR_MB,

        /* =====================================================
           CuS SRR MB
           SOLO DIAGNÓSTICO
           ===================================================== */
        SUM(
            CASE
                WHEN r.PONDCusG01 IS NOT NULL
                THEN COALESCE(r.Ton,0) * r.PONDCusG01
                ELSE 0
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN r.PONDCusG01 IS NOT NULL
                    THEN COALESCE(r.Ton,0)
                    ELSE 0
                END
            ),
            0
        ) AS CuS_SRR_MB,

        /* =====================================================
           CO3 SRR MB
           SOLO DIAGNÓSTICO
           ===================================================== */
        SUM(
            CASE
                WHEN r.PONDC03G02 IS NOT NULL
                THEN COALESCE(r.Ton,0) * r.PONDC03G02
                ELSE 0
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN r.PONDC03G02 IS NOT NULL
                    THEN COALESCE(r.Ton,0)
                    ELSE 0
                END
            ),
            0
        ) AS CO3_SRR_MB,

        /* =====================================================
           Malla -100 SRR MB
           SOLO DIAGNÓSTICO
           ===================================================== */
        SUM(
            CASE
                WHEN r.POND100G07 IS NOT NULL
                THEN COALESCE(r.Ton,0) * r.POND100G07
                ELSE 0
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN r.POND100G07 IS NOT NULL
                    THEN COALESCE(r.Ton,0)
                    ELSE 0
                END
            ),
            0
        ) AS Malla100_SRR_MB,

        /* =====================================================
           ClayBeta SRR
           DATO DIRECTO OFICIAL MB
           ===================================================== */
        SUM(
            CASE
                WHEN r.PONDClayBG10 IS NOT NULL
                THEN COALESCE(r.Ton,0) * r.PONDClayBG10
                ELSE 0
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN r.PONDClayBG10 IS NOT NULL
                    THEN COALESCE(r.Ton,0)
                    ELSE 0
                END
            ),
            0
        ) AS ClayBeta_SRR_MB,

        /* =====================================================
           Recuperación SRR
           DATO DIRECTO OFICIAL MB
           ===================================================== */
        SUM(
            CASE
                WHEN r.PONDRecLixG03 IS NOT NULL
                THEN COALESCE(r.Ton,0) * r.PONDRecLixG03
                ELSE 0
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN r.PONDRecLixG03 IS NOT NULL
                    THEN COALESCE(r.Ton,0)
                    ELSE 0
                END
            ),
            0
        ) AS Recuperacion_SRR_MB

    FROM [inventar_SpcHidr].[resumen_mina] r

    WHERE CAST(r.Fecha AS date) >= @fecha_inicio
      AND CAST(r.Fecha AS date) <  @fecha_fin

      AND UPPER(LTRIM(RTRIM(ISNULL(r.Origen,'')))) = 'STOCK'
      AND UPPER(LTRIM(RTRIM(ISNULL(r.Fase,'')))) = 'SRR'

    GROUP BY CAST(r.Fecha AS date)
),

    base AS
    (
        SELECT
            g.Fecha,

            /* ================================
               MASAS
               ================================ */
            g.Apilado_TMS_Real_Dia,

            a.Delta_Inventario_Chancado_TMS,

            g.Apilado_TMS_Real_Dia
                + a.Delta_Inventario_Chancado_TMS
                AS TMS_Total_Operacion,

            a.Chancado_TMS_Reporte
                AS TMS_MinaStock,

            a.SRR_TMS_Dia,

            a.Chancado_TMS_Reporte
                + a.SRR_TMS_Dia
                AS TMS_Total_Cierre_Componentes,

            /* ================================
               LEYES TOTALES
               ================================ */
            g.CuT_Real_Dia,
            g.CuS_Real_Dia,
            g.CO3_Real_Dia,
            g.Malla_Menos_100_Real_Dia,
            g.CaolBeta_Real_Dia,

            /* ================================
               MODELO BLOQUES MINA + STOCK
               ================================ */
                mb.TMS_MB_MinaStock,
                mb.CuT_MinaStock,
                mb.CuS_MinaStock,
                mb.CO3_MinaStock,
                mb.Malla100_MinaStock,
                mb.ClayBeta_MinaStock,

            /* ================================
               MODELO BLOQUES SRR
               ================================ */
            s.TMS_MB_SRR,

            /* Diagnóstico solamente */
            s.CuT_SRR_MB,
            s.CuS_SRR_MB,
            s.CO3_SRR_MB,
            s.Malla100_SRR_MB,

            /* Fuentes finales directas */
            s.ClayBeta_SRR_MB,
            s.Recuperacion_SRR_MB,

            /* ================================
               TRAZABILIDAD AJUSTE
               ================================ */
            a.Factor_Ajuste_Calculado,
            a.Flag_Usa_Ajuste,
            a.Regla_Aplicacion,
            a.Inventario_Chancado_TMS_Anterior,
            a.Inventario_Chancado_TMS_Actual

        FROM generador g

        LEFT JOIN
            [inventar_SpcHidr].[v_ajuste_camiones_emision_test] a
            ON a.Fecha = g.Fecha

        LEFT JOIN mb_mina_stock mb
            ON mb.Fecha = g.Fecha

        LEFT JOIN mb_srr s
            ON s.Fecha = g.Fecha
   
    ),

    calc AS
    (
        SELECT
            b.*,

            b.TMS_Total_Operacion
            - b.TMS_Total_Cierre_Componentes
                AS Diferencia_Cierre_TMS,

            /* Participación SRR */
            b.SRR_TMS_Dia
            / NULLIF(b.TMS_Total_Operacion,0)
                AS Participacion_SRR,

            /* Amplificación del despeje */
            b.TMS_Total_Operacion
            / NULLIF(b.SRR_TMS_Dia,0)
                AS Factor_Sensibilidad_Reconstitucion,

            /* ==========================
               CuT
               ========================== */
            CASE
                WHEN b.SRR_TMS_Dia IS NULL
                  OR b.SRR_TMS_Dia <= 0
                  OR b.CuT_Real_Dia IS NULL
                  OR b.CuT_MinaStock IS NULL
                  OR b.TMS_Total_Operacion IS NULL
                  OR b.TMS_MinaStock IS NULL
                    THEN NULL
                ELSE
                    (
                        b.CuT_Real_Dia
                        * b.TMS_Total_Operacion
                        -
                        b.CuT_MinaStock
                        * b.TMS_MinaStock
                    )
                    /
                    NULLIF(b.SRR_TMS_Dia,0)
            END AS CuT_SRR_Reconst,

            /* ==========================
               CuS
               ========================== */
            CASE
                WHEN b.SRR_TMS_Dia IS NULL
                  OR b.SRR_TMS_Dia <= 0
                  OR b.CuS_Real_Dia IS NULL
                  OR b.CuS_MinaStock IS NULL
                    THEN NULL
                ELSE
                    (
                        b.CuS_Real_Dia
                        * b.TMS_Total_Operacion
                        -
                        b.CuS_MinaStock
                        * b.TMS_MinaStock
                    )
                    /
                    NULLIF(b.SRR_TMS_Dia,0)
            END AS CuS_SRR_Reconst,

            /* ==========================
               CO3
               ========================== */
            CASE
                WHEN b.SRR_TMS_Dia IS NULL
                  OR b.SRR_TMS_Dia <= 0
                  OR b.CO3_Real_Dia IS NULL
                  OR b.CO3_MinaStock IS NULL
                    THEN NULL
                ELSE
                    (
                        b.CO3_Real_Dia
                        * b.TMS_Total_Operacion
                        -
                        b.CO3_MinaStock
                        * b.TMS_MinaStock
                    )
                    /
                    NULLIF(b.SRR_TMS_Dia,0)
            END AS CO3_SRR_Reconst,

            /* ==========================
               Malla -100
               ========================== */
            CASE
                WHEN b.SRR_TMS_Dia IS NULL
                  OR b.SRR_TMS_Dia <= 0
                  OR b.Malla_Menos_100_Real_Dia IS NULL
                  OR b.Malla100_MinaStock IS NULL
                    THEN NULL
                ELSE
                    (
                        b.Malla_Menos_100_Real_Dia
                        * b.TMS_Total_Operacion
                        -
                        b.Malla100_MinaStock
                        * b.TMS_MinaStock
                    )
                    /
                    NULLIF(b.SRR_TMS_Dia,0)
            END AS Malla100_SRR_Reconst

        FROM base b
    )

    SELECT
        c.*,

        /* ========================================================
           Reconstitución vs MB SRR
           DIAGNÓSTICO, NO reemplazo
           ======================================================== */

        c.CuT_SRR_Reconst
        - c.CuT_SRR_MB
            AS Delta_CuT_Reconst_MB,

        ABS(
            c.CuT_SRR_Reconst
            - c.CuT_SRR_MB
        ) AS AbsDelta_CuT_Reconst_MB,

        c.CuS_SRR_Reconst
        - c.CuS_SRR_MB
            AS Delta_CuS_Reconst_MB,

        ABS(
            c.CuS_SRR_Reconst
            - c.CuS_SRR_MB
        ) AS AbsDelta_CuS_Reconst_MB,

        c.CO3_SRR_Reconst
        - c.CO3_SRR_MB
            AS Delta_CO3_Reconst_MB,

        ABS(
            c.CO3_SRR_Reconst
            - c.CO3_SRR_MB
        ) AS AbsDelta_CO3_Reconst_MB,

        c.Malla100_SRR_Reconst
        - c.Malla100_SRR_MB
            AS Delta_M100_Reconst_MB,

        ABS(
            c.Malla100_SRR_Reconst
            - c.Malla100_SRR_MB
        ) AS AbsDelta_M100_Reconst_MB,

        /* ========================================================
           Estado
           ======================================================== */
        CAST(
            CASE
                WHEN c.SRR_TMS_Dia IS NULL
                    THEN 'SIN_DATO_SRR'

                WHEN c.SRR_TMS_Dia <= 0
                    THEN 'SRR_CERO'

                WHEN c.TMS_Total_Operacion IS NULL
                  OR c.TMS_MinaStock IS NULL
                    THEN 'SIN_MASA_BALANCE'

                WHEN ABS(c.Diferencia_Cierre_TMS) > 0.01
                    THEN 'REVISAR_CIERRE_MASA'

                  WHEN c.CuT_Real_Dia IS NULL
                  OR c.CuT_MinaStock IS NULL
                  OR c.CuS_Real_Dia IS NULL
                  OR c.CuS_MinaStock IS NULL
                  OR c.CO3_Real_Dia IS NULL
                  OR c.CO3_MinaStock IS NULL
                  OR c.Malla_Menos_100_Real_Dia IS NULL
                  OR c.Malla100_MinaStock IS NULL
                    THEN 'RECONSTITUCION_PARCIAL'

                ELSE 'OK'
            END
            AS varchar(40)
        ) AS Flag_Reconstitucion,

        /* ========================================================
           Sensibilidad
           SOLO DIAGNÓSTICO
           ======================================================== */
        CAST(
            CASE
                WHEN c.SRR_TMS_Dia IS NULL
                    THEN 'SIN_DATO_SRR'

                WHEN c.SRR_TMS_Dia <= 0
                    THEN 'SIN_RECONSTITUCION_SRR_CERO'

                WHEN c.Factor_Sensibilidad_Reconstitucion >= 5
                    THEN 'ALTA_SENSIBILIDAD'

                ELSE 'SENSIBILIDAD_NORMAL'
            END
            AS varchar(40)
        ) AS Flag_Sensibilidad

    FROM calc c
);
