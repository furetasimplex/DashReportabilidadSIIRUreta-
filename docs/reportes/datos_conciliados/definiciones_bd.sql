-- Definiciones actuales extraidas desde SQL Server.
-- Servidor: VPS-5347319-X
-- Base: inventar_SpcHidr
-- Fecha de extraccion: 2026-08-06 19:22:19.318067-03:00
-- Archivo informativo: no ejecutar completo sin revision.

-- ============================================================================
-- inventar_SpcHidr.fn_generador_reporte_diario_emision_test (SQL_INLINE_TABLE_VALUED_FUNCTION)
-- Ultima modificacion: 2026-07-31 11:26:39.750000
-- ============================================================================

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
                        THEN 15.0
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
                               + (15.51 * ISNULL(d.CO3_Real_Dia, 0)) < 15.0
                                THEN 15.0
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
                        THEN 15.0
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
                               + (15.51 * ISNULL(pr.CO3_Programa, 0)) < 15.0
                                THEN 15.0
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
GO

-- ============================================================================
-- inventar_SpcHidr.sp_factor_ajuste_camiones_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-08-03 22:31:57.337000
-- ============================================================================
/* ================================================================
   ALTER inventar_SpcHidr.sp_factor_ajuste_camiones_test -- v2
   Redireccion de la fuente de camiones: mov_cam -> mov_cam_powerbi
   ----------------------------------------------------------------
   Cambia UNICAMENTE las secciones 2 y 3 del procedimiento. Las
   secciones 1, 4, 5, 6, 7 y 8 quedan identicas a la version anterior
   (que usaba inventar_SpcHidr.mov_cam).

   Validado antes de este cambio con comparar_mov_cam_vs_powerbi_23jul.sql
   contra el 2026-07-22 (mismo dia usado por el usuario para revisar):
     A_MOV_CAM_ACTUAL:                20346.14 KOM / 1651.999 CAT / 57-7 vueltas
     B_MOV_CAM_POWERBI (ton_descarga):20349.00 KOM / 1652.000 CAT / 57-7 vueltas
   Diferencia 0.013%, explicada por redondeo (ton_descarga en el
   Export de PowerBI viene sin decimales; mov_cam.Tonelaje_Hum_CIO
   trae mas precision). 0 duplicados en ambos lados ese dia, 7 de 7
   registros calzan fila a fila.

   MAPEO DE COLUMNAS confirmado con datos reales (no es el que sugiere
   el nombre a primera vista):
       mov_cam.Tonelaje_Hum_CIO (tonelada humeda, la que usa el SP
       para Produccion_KOM_TMH / Produccion_CAT_TMH)
           <- mov_cam_powerbi.ton_descarga
       mov_cam.Ton / mov_cam.Tonelaje_Seco_CIO (tonelada seca)
           <- mov_cam_powerbi.tonelaje_descarga_tms
       mov_cam.Turno ('A'/'B')       <- mov_cam_powerbi.turno ('TA'/'TB')
           (no se normaliza: Turno no se usa en la agregacion diaria
           de la seccion 4, solo pasa como trazabilidad)
       mov_cam.Fase                  <- mov_cam_powerbi.fase
       mov_cam.Banco                 <- mov_cam_powerbi.banco
           OJO: en mov_cam_powerbi, Banco viene igual a Fase en los
           datos revisados (ej. Fase=STRA, Banco=STRA) mientras en
           mov_cam eran distintos (Fase=STRA, Banco=DESC). Banco NO
           se usa en los totales de la seccion 4 (Produccion/Vueltas),
           solo pasa como trazabilidad -- no afecta este calculo, pero
           queda documentado por si se usa Banco en otro lado despues.
       mov_cam.Pala                  <- mov_cam_powerbi.excavadora
       mov_cam.Destino               <- mov_cam_powerbi.destino_descarga
       mov_cam.Flota_CEX             <- mov_cam_powerbi.flota_cex_tc
       mov_cam.N_BREAK               <- mov_cam_powerbi.n_break
       mov_cam.Origen, Solido, Poligono_CIO, Ton_Hum_Diseno_CAEX,
       PONDHumedad                   <- SIN EQUIVALENTE, quedan NULL.
           Ninguna de estas se usa en la agregacion final de la
           seccion 4 (Produccion/Vueltas/Estado_Calculo); solo
           formaban parte de la llave de deduplicacion de la
           seccion 3 anterior, que ya no aplica (ver mas abajo).

   DEDUPLICACION (seccion 3): mov_cam_powerbi ya tiene un indice
   unico de 9 columnas (fecha+turno+tipo_movimiento+fase+banco+
   excavadora+destino_descarga+flota_cex_tc+grade) que impide filas
   operacionales repetidas por diseno de la tabla. Por eso la
   deduplicacion por ROW_NUMBER() de la version anterior (necesaria
   porque mov_cam SI puede traer duplicados) se reemplaza por un
   passthrough: todas las filas de #MovCamNormalizado ya son unicas,
   entonces todas quedan con rn = 1. Se mantiene el nombre de la
   tabla temporal #MovCamClasificado y la columna rn para no romper
   la seccion 4, que sigue igual.

   Si en algun momento se necesita volver a comparar contra mov_cam,
   usar comparar_mov_cam_vs_powerbi_23jul.sql (parametrizable a
   cualquier fecha cambiando @FechaTest).
================================================================ */

CREATE PROCEDURE [inventar_SpcHidr].[sp_factor_ajuste_camiones_test]
    @FechaInicio date,
    @FechaFin    date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF @FechaInicio IS NULL OR @FechaFin IS NULL
    BEGIN
        THROW 50001, 'FechaInicio y FechaFin son obligatorias.', 1;
    END;
    IF @FechaInicio > @FechaFin
    BEGIN
        THROW 50002, 'FechaInicio no puede ser mayor que FechaFin.', 1;
    END;
    /* ============================================================
       1. SRR diario desde el reporte por turno
       ============================================================ */
    ;WITH SRR_Diario AS
    (
        SELECT
            CAST(r.Fecha AS date) AS Fecha,
            SUM
            (
                CASE
                    WHEN UPPER(LTRIM(RTRIM(r.Turno))) = 'A'
                    THEN
                        COALESCE(
                            TRY_CONVERT(float, r.Apilado_TMS_Real),
                            0.0
                        )
                        *
                        COALESCE(
                            TRY_CONVERT(float, r.SRR),
                            0.0
                        )
                        / 100.0
                    ELSE 0.0
                END
            ) AS SRR_TMS_Turno_A,
            SUM
            (
                CASE
                    WHEN UPPER(LTRIM(RTRIM(r.Turno))) = 'B'
                    THEN
                        COALESCE(
                            TRY_CONVERT(float, r.Apilado_TMS_Real),
                            0.0
                        )
                        *
                        COALESCE(
                            TRY_CONVERT(float, r.SRR),
                            0.0
                        )
                        / 100.0
                    ELSE 0.0
                END
            ) AS SRR_TMS_Turno_B,
            SUM
            (
                COALESCE(
                    TRY_CONVERT(float, r.Apilado_TMS_Real),
                    0.0
                )
                *
                COALESCE(
                    TRY_CONVERT(float, r.SRR),
                    0.0
                )
                / 100.0
            ) AS SRR_TMS_Dia,
            COUNT(*) AS Cantidad_Registros_SRR
        FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test] AS r
        WHERE CAST(r.Fecha AS date)
              BETWEEN @FechaInicio AND @FechaFin
        GROUP BY CAST(r.Fecha AS date)
    ),
    Base AS
    (
        SELECT
            i.Fecha,
            TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
                AS Apilado_TMH_Neto,
            TRY_CONVERT(float, a.Sal_promedio_dia)
                AS Sal_Dia,
            TRY_CONVERT(float, a.TMH_Bruto_Dia)
                AS Apilado_TMH_Bruto,
            TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
            + TRY_CONVERT(float, a.Sal_promedio_dia)
                AS Apilado_TMH_Bruto_Reconstruido,
            TRY_CONVERT(float, a.TMH_Bruto_Dia)
            -
            (
                TRY_CONVERT(float, a.Apilado_TMH_promedio_dia)
                + TRY_CONVERT(float, a.Sal_promedio_dia)
            ) AS Check_TMH_Bruto,
            h.Humedad_Inventario,
            h.Regla_Humedad_Inventario,
            h.Flag_Humedad_Inventario_Valida,
            i.Total_Inventario_Chancado_TMS,
            i.Inventario_Chancado_TMS_Anterior,
            i.Delta_Inventario_Chancado_TMS,
            i.Flag_Continuidad_Diaria,
            i.Flag_Inventario_Valido,
            COALESCE(s.SRR_TMS_Turno_A, 0.0)
                AS SRR_TMS_Turno_A,
            COALESCE(s.SRR_TMS_Turno_B, 0.0)
                AS SRR_TMS_Turno_B,
            COALESCE(s.SRR_TMS_Dia, 0.0)
                AS SRR_TMS_Dia,
            COALESCE(s.Cantidad_Registros_SRR, 0)
                AS Cantidad_Registros_SRR
        FROM [inventar_SpcHidr].[v_inventario_chancado_test] AS i
        LEFT JOIN [inventar_SpcHidr].[Historico_Apilado_Diario] AS a
            ON CAST(a.Fecha AS date) = i.Fecha
        LEFT JOIN [inventar_SpcHidr].[v_humedad_inventario_test] AS h
            ON h.Fecha = i.Fecha
        LEFT JOIN SRR_Diario AS s
            ON s.Fecha = i.Fecha
        WHERE i.Fecha BETWEEN @FechaInicio AND @FechaFin
    ),
    CalculoSinAjuste AS
    (
        SELECT
            b.*,
            CASE
                WHEN b.Apilado_TMH_Bruto IS NOT NULL
                 AND b.Flag_Humedad_Inventario_Valida = 1
                THEN
                    b.Apilado_TMH_Bruto
                    *
                    (
                        1.0
                        - b.Humedad_Inventario / 100.0
                    )
                ELSE NULL
            END AS Apilado_TMS_Sin_Ajuste
        FROM Base AS b
    ),
    MineralSinAjuste AS
    (
        SELECT
            c.*,
            CASE
                WHEN c.Apilado_TMS_Sin_Ajuste IS NOT NULL
                 AND c.Flag_Inventario_Valido = 1
                 AND c.Delta_Inventario_Chancado_TMS IS NOT NULL
                THEN
                    c.Apilado_TMS_Sin_Ajuste
                    + c.Delta_Inventario_Chancado_TMS
                ELSE NULL
            END AS Mineral_Chancado_TMS_Sin_Ajuste
        FROM CalculoSinAjuste AS c
    ),
    ChancadoSinAjuste AS
    (
        SELECT
            m.*,
            CASE
                WHEN m.Mineral_Chancado_TMS_Sin_Ajuste IS NOT NULL
                 AND m.Sal_Dia IS NOT NULL
                 AND m.SRR_TMS_Dia IS NOT NULL
                THEN
                    m.Mineral_Chancado_TMS_Sin_Ajuste
                    - m.Sal_Dia
                    - m.SRR_TMS_Dia
                ELSE NULL
            END AS Chancado_TMS_Sin_Ajuste
        FROM MineralSinAjuste AS m
    )
    SELECT
        Fecha,
        Apilado_TMH_Neto,
        Sal_Dia,
        Apilado_TMH_Bruto,
        Apilado_TMH_Bruto_Reconstruido,
        Check_TMH_Bruto,
        Humedad_Inventario,
        Regla_Humedad_Inventario,
        Flag_Humedad_Inventario_Valida,
        Total_Inventario_Chancado_TMS,
        Inventario_Chancado_TMS_Anterior,
        Delta_Inventario_Chancado_TMS,
        Flag_Continuidad_Diaria,
        Flag_Inventario_Valido,
        SRR_TMS_Turno_A,
        SRR_TMS_Turno_B,
        SRR_TMS_Dia,
        Cantidad_Registros_SRR,
        Apilado_TMS_Sin_Ajuste,
        Mineral_Chancado_TMS_Sin_Ajuste,
        Chancado_TMS_Sin_Ajuste
    INTO #BaseBalance
    FROM ChancadoSinAjuste;
    CREATE UNIQUE CLUSTERED INDEX IX_BaseBalance_Fecha
        ON #BaseBalance(Fecha);
    /* ============================================================
       2. Normalizacion de movimientos de camiones -- FUENTE NUEVA:
          inventar_SpcHidr.mov_cam_powerbi (antes mov_cam). Ver mapeo
          de columnas en el encabezado de este script.
       ============================================================ */
    SELECT
        m.fecha AS Fecha,
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(50), m.turno)
            ))
        ) AS Turno,
        CAST(NULL AS nvarchar(255)) AS Origen,          -- sin equivalente en mov_cam_powerbi
        CAST(NULL AS nvarchar(500)) AS Solido,          -- sin equivalente en mov_cam_powerbi
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.fase)
            ))
        ) AS Fase,
        LTRIM(RTRIM(
            CONVERT(nvarchar(100), m.banco)
        )) AS Banco,
        LTRIM(RTRIM(
            CONVERT(nvarchar(100), m.excavadora)
        )) AS Pala,
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.destino_descarga)
            ))
        ) AS Destino,
        CAST(NULL AS nvarchar(500)) AS Poligono_CIO,    -- sin equivalente en mov_cam_powerbi
        UPPER(
            LTRIM(RTRIM(
                CONVERT(nvarchar(100), m.flota_cex_tc)
            ))
        ) AS Flota_CEX,
        TRY_CONVERT(float, m.tonelaje_descarga_tms)
            AS Ton,
        TRY_CONVERT(float, m.n_break)
            AS N_BREAK,
        CAST(NULL AS float) AS Ton_Hum_Diseno_CAEX,     -- sin equivalente en mov_cam_powerbi
        TRY_CONVERT(float, m.ton_descarga)
            AS Tonelaje_Hum_CIO,                        -- validado: ton_descarga = tonelada humeda
        TRY_CONVERT(float, m.tonelaje_descarga_tms)
            AS Tonelaje_Seco_CIO,
        CAST(NULL AS float) AS PONDHumedad,             -- sin equivalente en mov_cam_powerbi
        CAST(NULL AS int) AS mov_id,                    -- mov_cam_powerbi no tiene este concepto
        m.id AS ID
    INTO #MovCamNormalizado
    FROM [inventar_SpcHidr].[mov_cam_powerbi] AS m
    WHERE m.fecha BETWEEN @FechaInicio AND @FechaFin
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.destino_descarga)
              ))
          ) = 'CH01'
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.fase)
              ))
          ) <> 'SRR'
      AND UPPER(
              LTRIM(RTRIM(
                  CONVERT(nvarchar(100), m.flota_cex_tc)
              ))
          ) IN ('KOM', 'CAT');
    CREATE INDEX IX_MovCamNormalizado_Fecha
        ON #MovCamNormalizado(Fecha);
    /* ============================================================
       3. Deduplicacion -- YA NO APLICA con mov_cam_powerbi.
          La tabla tiene un indice unico de 9 columnas
          (fecha+turno+tipo_movimiento+fase+banco+excavadora+
          destino_descarga+flota_cex_tc+grade) que impide filas
          operacionales repetidas por diseno. Se mantiene la
          estructura #MovCamClasificado / columna rn para no romper
          la seccion 4, pero todas las filas quedan rn = 1 (ninguna
          se descarta).
       ============================================================ */
    SELECT
        n.*,
        CAST(1 AS bigint) AS rn
    INTO #MovCamClasificado
    FROM #MovCamNormalizado AS n;
    CREATE INDEX IX_MovCamClasificado_Fecha_RN
        ON #MovCamClasificado(Fecha, rn);
    /* ============================================================
       4. Consolidacion diaria de camiones
       ============================================================ */
    ;WITH ConteoOriginal AS
    (
        SELECT
            Fecha,
            COUNT(*) AS Cantidad_Registros_Originales
        FROM #MovCamNormalizado
        GROUP BY Fecha
    ),
    CamionesValidos AS
    (
        SELECT
            Fecha,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'KOM'
                    THEN COALESCE(Tonelaje_Hum_CIO, 0.0)
                    ELSE 0.0
                END
            ) AS Produccion_KOM_TMH,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'CAT'
                    THEN COALESCE(Tonelaje_Hum_CIO, 0.0)
                    ELSE 0.0
                END
            ) AS Produccion_CAT_TMH,
            SUM
            (
                COALESCE(Tonelaje_Hum_CIO, 0.0)
            ) AS Produccion_Total_MovCam,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'KOM'
                    THEN COALESCE(N_BREAK, 0.0)
                    ELSE 0.0
                END
            ) AS Vueltas_KOM,
            SUM
            (
                CASE
                    WHEN Flota_CEX = 'CAT'
                    THEN COALESCE(N_BREAK, 0.0)
                    ELSE 0.0
                END
            ) AS Vueltas_CAT,
            COUNT(*) AS Cantidad_Registros_Validos
        FROM #MovCamClasificado
        WHERE rn = 1
        GROUP BY Fecha
    )
    SELECT
        c.Fecha,
        c.Produccion_KOM_TMH,
        c.Produccion_CAT_TMH,
        c.Produccion_Total_MovCam,
        c.Vueltas_KOM,
        c.Vueltas_CAT,
        o.Cantidad_Registros_Originales,
        c.Cantidad_Registros_Validos,
        o.Cantidad_Registros_Originales
        - c.Cantidad_Registros_Validos
            AS Cantidad_Duplicados_Eliminados
    INTO #CamionesDiario
    FROM CamionesValidos AS c
    INNER JOIN ConteoOriginal AS o
        ON o.Fecha = c.Fecha;
    CREATE UNIQUE CLUSTERED INDEX IX_CamionesDiario_Fecha
        ON #CamionesDiario(Fecha);
    /* ============================================================
       5. Base del factor
       ============================================================ */
    SELECT
        b.*,
        COALESCE(c.Produccion_KOM_TMH, 0.0)
            AS Produccion_KOM_TMH,
        COALESCE(c.Produccion_CAT_TMH, 0.0)
            AS Produccion_CAT_TMH,
        COALESCE(c.Vueltas_KOM, 0.0)
            AS Vueltas_KOM,
        COALESCE(c.Vueltas_CAT, 0.0)
            AS Vueltas_CAT,
        COALESCE(c.Produccion_Total_MovCam, 0.0)
            AS Produccion_Total_MovCam,
        COALESCE(c.Cantidad_Registros_Originales, 0)
            AS Cantidad_Registros_Originales,
        COALESCE(c.Cantidad_Registros_Validos, 0)
            AS Cantidad_Registros_Validos,
        COALESCE(c.Cantidad_Duplicados_Eliminados, 0)
            AS Cantidad_Duplicados_Eliminados,
        COALESCE(c.Produccion_KOM_TMH, 0.0)
        + COALESCE(c.Produccion_CAT_TMH, 0.0)
            AS Dato_Mina_TMH,
        COALESCE(c.Produccion_Total_MovCam, 0.0)
        -
        (
            COALESCE(c.Produccion_KOM_TMH, 0.0)
            + COALESCE(c.Produccion_CAT_TMH, 0.0)
        ) AS Check_Produccion_Flotas,
        CASE
            WHEN b.Chancado_TMS_Sin_Ajuste IS NOT NULL
             AND b.Humedad_Inventario >= 0
             AND b.Humedad_Inventario < 100
            THEN
                b.Chancado_TMS_Sin_Ajuste
                /
                NULLIF(
                    1.0 - b.Humedad_Inventario / 100.0,
                    0.0
                )
            ELSE NULL
        END AS Chancado_TMH_Sin_Ajuste
    INTO #FactorBase
    FROM #BaseBalance AS b
    LEFT JOIN #CamionesDiario AS c
        ON c.Fecha = b.Fecha;
    CREATE UNIQUE CLUSTERED INDEX IX_FactorBase_Fecha
        ON #FactorBase(Fecha);
    /* ============================================================
       6. Distribucion del chancado por flota y cargas por vuelta
       ============================================================ */
    SELECT
        f.*,
        CASE
            WHEN f.Dato_Mina_TMH > 0
            THEN
                f.Produccion_KOM_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Participacion_KOM,
        CASE
            WHEN f.Dato_Mina_TMH > 0
            THEN
                f.Produccion_CAT_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Participacion_CAT,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
            THEN
                f.Chancado_TMH_Sin_Ajuste
                * f.Produccion_KOM_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Chancado_KOM_TMH_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
            THEN
                f.Chancado_TMH_Sin_Ajuste
                * f.Produccion_CAT_TMH
                / f.Dato_Mina_TMH
            ELSE NULL
        END AS Chancado_CAT_TMH_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
             AND f.Produccion_KOM_TMH > 0
             AND f.Vueltas_KOM > 0
            THEN
                (
                    f.Chancado_TMH_Sin_Ajuste
                    * f.Produccion_KOM_TMH
                    / f.Dato_Mina_TMH
                )
                / f.Vueltas_KOM
            ELSE NULL
        END AS Carga_KOM_Sin_Ajuste,
        CASE
            WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL
             AND f.Dato_Mina_TMH > 0
             AND f.Produccion_CAT_TMH > 0
             AND f.Vueltas_CAT > 0
            THEN
                (
                    f.Chancado_TMH_Sin_Ajuste
                    * f.Produccion_CAT_TMH
                    / f.Dato_Mina_TMH
                )
                / f.Vueltas_CAT
            ELSE NULL
        END AS Carga_CAT_Sin_Ajuste
    INTO #FactorCargas
    FROM #FactorBase AS f;
    CREATE UNIQUE CLUSTERED INDEX IX_FactorCargas_Fecha
        ON #FactorCargas(Fecha);
    /* ============================================================
       7. Aplicacion de limites operacionales
       ============================================================ */
    SELECT
        c.*,
        CASE
            WHEN c.Produccion_KOM_TMH = 0
            THEN 0.0
            WHEN c.Vueltas_KOM <= 0
              OR c.Carga_KOM_Sin_Ajuste IS NULL
            THEN NULL
            WHEN c.Carga_KOM_Sin_Ajuste <= 380.0
            THEN c.Chancado_KOM_TMH_Sin_Ajuste
            ELSE c.Vueltas_KOM * 380.0
        END AS KOM_TMH_Corregido,
        CASE
            WHEN c.Produccion_CAT_TMH = 0
            THEN 0.0
            WHEN c.Vueltas_CAT <= 0
              OR c.Carga_CAT_Sin_Ajuste IS NULL
            THEN NULL
            WHEN c.Carga_CAT_Sin_Ajuste <= 265.0
            THEN c.Chancado_CAT_TMH_Sin_Ajuste
            ELSE c.Vueltas_CAT * 265.0
        END AS CAT_TMH_Corregido
    INTO #FactorCorregido
    FROM #FactorCargas AS c;
    CREATE UNIQUE CLUSTERED INDEX IX_FactorCorregido_Fecha
        ON #FactorCorregido(Fecha);
    /* ============================================================
       8. Resultado final y estado de evaluacion
       ============================================================ */
    SELECT
        c.Fecha,
        /* Trazabilidad del balance */
        c.Apilado_TMH_Bruto,
        c.Apilado_TMH_Neto,
        c.Sal_Dia,
        c.Humedad_Inventario,
        c.Apilado_TMS_Sin_Ajuste,
        c.Total_Inventario_Chancado_TMS,
        c.Inventario_Chancado_TMS_Anterior,
        c.Delta_Inventario_Chancado_TMS,
        c.SRR_TMS_Dia,
        c.Mineral_Chancado_TMS_Sin_Ajuste,
        c.Chancado_TMS_Sin_Ajuste,
        c.Chancado_TMH_Sin_Ajuste,
        /* Trazabilidad de camiones */
        c.Produccion_KOM_TMH,
        c.Produccion_CAT_TMH,
        c.Dato_Mina_TMH,
        c.Vueltas_KOM,
        c.Vueltas_CAT,
        c.Participacion_KOM,
        c.Participacion_CAT,
        c.Chancado_KOM_TMH_Sin_Ajuste,
        c.Chancado_CAT_TMH_Sin_Ajuste,
        c.Carga_KOM_Sin_Ajuste,
        c.Carga_CAT_Sin_Ajuste,
        c.KOM_TMH_Corregido,
        c.CAT_TMH_Corregido,
        CASE
            WHEN c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
            THEN
                c.KOM_TMH_Corregido
                + c.CAT_TMH_Corregido
            ELSE NULL
        END AS Chancado_TMH_Corregido_Total,
        CASE
            WHEN c.Chancado_TMH_Sin_Ajuste > 0
             AND c.Dato_Mina_TMH > 0
             AND c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
             AND
             (
                 c.Produccion_KOM_TMH = 0
                 OR c.Vueltas_KOM > 0
             )
             AND
             (
                 c.Produccion_CAT_TMH = 0
                 OR c.Vueltas_CAT > 0
             )
             AND ABS(c.Check_Produccion_Flotas) <= 0.001
            THEN
                (
                    c.KOM_TMH_Corregido
                    + c.CAT_TMH_Corregido
                )
                / c.Chancado_TMH_Sin_Ajuste
            ELSE NULL
        END AS Factor_Ajuste_Calculado,
        CASE
            WHEN c.Chancado_TMH_Sin_Ajuste > 0
             AND c.Dato_Mina_TMH > 0
             AND c.KOM_TMH_Corregido IS NOT NULL
             AND c.CAT_TMH_Corregido IS NOT NULL
             AND
             (
                 c.Produccion_KOM_TMH = 0
                 OR c.Vueltas_KOM > 0
             )
             AND
             (
                 c.Produccion_CAT_TMH = 0
                 OR c.Vueltas_CAT > 0
             )
             AND ABS(c.Check_Produccion_Flotas) <= 0.001
            THEN 1
            ELSE 0
        END AS Flag_Factor_Ajuste_Valido,
        CASE
            WHEN c.Flag_Humedad_Inventario_Valida <> 1
              OR c.Humedad_Inventario IS NULL
            THEN 'SIN_HUMEDAD'
            WHEN c.Flag_Inventario_Valido <> 1
              OR c.Delta_Inventario_Chancado_TMS IS NULL
            THEN 'SIN_INVENTARIO'
            WHEN c.Chancado_TMH_Sin_Ajuste IS NULL
            THEN 'SIN_BALANCE_CHANCADO'
            WHEN c.Dato_Mina_TMH <= 0
            THEN 'SIN_DATOS_CAMIONES'
            WHEN
            (
                c.Produccion_KOM_TMH > 0
                AND c.Vueltas_KOM <= 0
            )
            OR
            (
                c.Produccion_CAT_TMH > 0
                AND c.Vueltas_CAT <= 0
            )
            THEN 'SIN_VUELTAS'
            WHEN ABS(c.Check_Produccion_Flotas) > 0.001
            THEN 'ERROR_DISTRIBUCION_FLOTAS'
            WHEN c.Carga_KOM_Sin_Ajuste > 380.0
             AND c.Carga_CAT_Sin_Ajuste > 265.0
            THEN 'OK_AJUSTE_AMBAS_FLOTAS'
            WHEN c.Carga_KOM_Sin_Ajuste > 380.0
            THEN 'OK_AJUSTE_KOM'
            WHEN c.Carga_CAT_Sin_Ajuste > 265.0
            THEN 'OK_AJUSTE_CAT'
            ELSE 'OK_SIN_AJUSTE'
        END AS Estado_Calculo,
        /* Control de duplicados */
        c.Cantidad_Registros_Originales,
        c.Cantidad_Registros_Validos,
        c.Cantidad_Duplicados_Eliminados,
        c.Check_TMH_Bruto,
        c.Check_Produccion_Flotas,
        c.Flag_Continuidad_Diaria,
        c.Flag_Inventario_Valido,
        c.Flag_Humedad_Inventario_Valida
    FROM #FactorCorregido AS c
    ORDER BY c.Fecha;
END;
GO

-- ============================================================================
-- inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-08-04 21:35:44.210000
-- ============================================================================
/* ================================================================
   ALTER inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test
   v1.15 -> v1.16
   ----------------------------------------------------------------
   UNICO CAMBIO: PASO 3 (Ley CuT mina + stock).

   Motivo: Ley_CuT_Mina_Stock (insumo 4 de 7 para calcular
   Ley_CuT_Real_srr) leia solo mov_cam.CuTG00. Para 01-03 ago 2026
   ese laboratorio todavia no cargaba leyes para los camiones
   Destino=CH01, asi que #LeyMinaStock quedaba con CERO filas esos
   dias y Ley_CuT_Real_srr salia NULL aunque los otros 6 insumos
   estuvieran completos.

   Fix: mismo patron que PASO 2 (Chancado) y que
   v_conciliacion_chancado_v2 -- si mov_cam no tiene fila valida
   para una fecha, se usa como preliminar el promedio ponderado de
   "cut" en PROD_SIIR.hidro.imp_csv con el mismo filtro que ya usa
   Chancado (to='CH01', shovel<>'SRR', origen='IMP'). No reemplaza
   mov_cam cuando este si tiene datos -- solo llena el hueco.

   Se agrega la columna Fuente_Ley_Mina_Stock ('MOV_CAM' o
   'IMP_CSV_PRELIMINAR') a #LeyMinaStock para trazabilidad. No se
   toca el MERGE final ni la tabla Datos_conciliados_of: el JOIN
   contra #LeyMinaStock solo usa Fecha y Ley_CuT_Mina_Stock, asi
   que la columna nueva no requiere cambios aguas abajo.

   Nota: ic.tonnage en imp_csv es tonelaje humedo (no seco), igual
   que ya se acepta como aproximacion preliminar en PASO 2 para
   Chancado -- coherente con la Seccion 9 del prompt maestro
   (diferencia metodologica temporalmente aceptada).

   Todo lo demas (PASO 1, 2, 4-11, limpieza de temporales, manejo
   de errores) queda identico a la version que Luis ya valido.
================================================================ */
CREATE PROCEDURE [inventar_SpcHidr].[sp_mantiene_datos_conciliados_emision_test]
(
    @FechaInicio   date,
    @FechaFin      date,
    @DiasReproceso int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;
    /* ================================================================
       CORTE DINAMICO DE CAMIONES
       Resuelve la ultima fecha realmente cargada dentro del mes de
       @FechaFin y no posterior al cierre solicitado.
    ================================================================ */
    DECLARE @InicioMesCorte date =
        DATEFROMPARTS(YEAR(@FechaFin), MONTH(@FechaFin), 1);
    DECLARE @FechaCorteCamiones date;
    /* Periodo cerrado: respetar la fotografia congelada. */
    SELECT TOP (1)
        @FechaCorteCamiones = cfg.[fecha_corte_camiones]
    FROM [inventar_SpcHidr].[configuracion_reclamo_rotopala_periodo] cfg
    WHERE cfg.[periodo_reporte] = @InicioMesCorte
      AND cfg.[pad_id] = 2
      AND cfg.[estado] = 'CERRADO'
      AND cfg.[fecha_corte_camiones] IS NOT NULL;
    /* Periodo abierto: utilizar la ultima carga realmente disponible. */
    IF @FechaCorteCamiones IS NULL
    BEGIN
        SELECT
            @FechaCorteCamiones = MAX(CAST(cr.[fecha] AS date))
        FROM [inventar_SpcHidr].
             [control_reclamo_sulfuro_camiones_thm_diario] cr
        WHERE CAST(cr.[fecha] AS date) >= @InicioMesCorte
          AND CAST(cr.[fecha] AS date) <= @FechaFin;
    END;
    IF @FechaCorteCamiones IS NULL
        THROW 52001,
              'No existe una fecha de corte de camiones valida para el periodo.',
              1;
    EXEC sys.sp_set_session_context
        @key   = N'fecha_corte_camiones',
        @value = @FechaCorteCamiones;
    PRINT '-- Corte dinamico camiones: '
        + CONVERT(varchar(10), @FechaCorteCamiones, 120);
    DECLARE @FechaInicioProceso date =
        CASE
            WHEN DATEADD(DAY, -@DiasReproceso, @FechaFin) < @FechaInicio
                THEN DATEADD(DAY, -@DiasReproceso, @FechaFin)
            ELSE @FechaInicio
        END;
    DECLARE @FechaFinExclusiva date = DATEADD(DAY, 1, @FechaFin);
    EXEC [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_test]
         @FechaInicio   = @FechaInicioProceso,
         @FechaFin      = @FechaFin,
         @DiasReproceso = @DiasReproceso;
    DECLARE @t0 datetime2        = SYSDATETIME();
    DECLARE @t1 datetime2;
    PRINT '-- INICIO: ' + CONVERT(varchar, @t0, 121);
    PRINT '-- Version: 1.16 (Ley CuT SRR: fallback IMP en Ley_CuT_Mina_Stock) -- destino: Datos_conciliados_of (PRODUCCION)';
    PRINT '-- Rango efectivo: ' + CONVERT(varchar, @FechaInicioProceso) + ' a ' + CONVERT(varchar, @FechaFin);
    /* ================================================================
       PASO 1: Calendario
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Fechas') IS NOT NULL DROP TABLE #Fechas;
    ;WITH rec AS
    (
        SELECT @FechaInicioProceso AS Fecha
        UNION ALL
        SELECT DATEADD(DAY, 1, Fecha) FROM rec WHERE Fecha < @FechaFin
    )
    SELECT Fecha INTO #Fechas FROM rec OPTION (MAXRECURSION 1000);
    CREATE CLUSTERED INDEX ix_f ON #Fechas(Fecha);
    PRINT 'PASO 1  Calendario       : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 2: Chancado TMH                                   v1.11
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Chancado')        IS NOT NULL DROP TABLE #Chancado;
    IF OBJECT_ID('tempdb..#ChancadoMovCam')  IS NOT NULL DROP TABLE #ChancadoMovCam;
    IF OBJECT_ID('tempdb..#ChancadoImpCsv')  IS NOT NULL DROP TABLE #ChancadoImpCsv;
    SELECT
        CAST(Fecha AS date)                AS Fecha,
        SUM(COALESCE(Tonelaje_Hum_CIO,0))  AS Chancado_TMH_Dia
    INTO #ChancadoMovCam
    FROM [inventar_SpcHidr].[mov_cam]
    WHERE Fase NOT LIKE '%SRR%'
      AND CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin
    GROUP BY CAST(Fecha AS date);
    CREATE CLUSTERED INDEX ix_chmc ON #ChancadoMovCam(Fecha);
    SELECT
        CAST(ic.[date] AS date)             AS Fecha,
        SUM(COALESCE(ic.tonnage,0))         AS Chancado_TMH_Dia
    INTO #ChancadoImpCsv
    FROM [PROD_SIIR].[hidro].[imp_csv] ic
    WHERE ic.[to]     = 'CH01'
      AND ic.shovel  <> 'SRR'
      AND ic.origen   = 'IMP'
      AND CAST(ic.[date] AS date) >= @FechaInicioProceso
      AND CAST(ic.[date] AS date) <= @FechaFin
    GROUP BY CAST(ic.[date] AS date);
    CREATE CLUSTERED INDEX ix_chic ON #ChancadoImpCsv(Fecha);
    SELECT
        mc.Fecha,
        mc.Chancado_TMH_Dia,
        CAST('MOV_CAM' AS varchar(40))
            AS Fuente_Chancado_TMH,
        CAST('SUM_TONELAJE_HUM_CIO_FASE_NO_SRR' AS varchar(60))
            AS Metodo_Calculo_Chancado,
        CAST('OK' AS varchar(40))
            AS Flag_Chancado
    INTO #Chancado
    FROM #ChancadoMovCam mc
    UNION ALL
    SELECT
        ic.Fecha,
        ic.Chancado_TMH_Dia,
        CAST('IMP_CSV_PRELIMINAR' AS varchar(40)),
        CAST('SUM_TONNAGE_CH01_SIN_SRR_ORIGEN_IMP' AS varchar(60)),
        CAST('PRELIMINAR_PENDIENTE_MOV_CAM' AS varchar(40))
    FROM #ChancadoImpCsv ic
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM #ChancadoMovCam mc2
        WHERE mc2.Fecha = ic.Fecha
    );
    CREATE CLUSTERED INDEX ix_ch ON #Chancado(Fecha);
    DECLARE @ChFilas       int;
    DECLARE @ChMovCam      int;
    DECLARE @ChImpCsv      int;
    SELECT
        @ChFilas  = COUNT(*),
        @ChMovCam = SUM(CASE WHEN Fuente_Chancado_TMH = 'MOV_CAM' THEN 1 ELSE 0 END),
        @ChImpCsv = SUM(CASE WHEN Fuente_Chancado_TMH = 'IMP_CSV_PRELIMINAR' THEN 1 ELSE 0 END)
    FROM #Chancado;
    PRINT 'PASO 2  Chancado         : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(COALESCE(@ChFilas,0) AS varchar) + ' filas';
    /* ================================================================
       PASO 3: Ley CuT mina + stock                              v1.16
       Fallback IMP: ver comentario al inicio del script. Mismo
       patron que PASO 2 -- mov_cam manda si tiene datos, imp_csv
       rellena solo los dias que mov_cam dejo vacios.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#LeyMinaStock')        IS NOT NULL DROP TABLE #LeyMinaStock;
    IF OBJECT_ID('tempdb..#LeyMinaStockMovCam')  IS NOT NULL DROP TABLE #LeyMinaStockMovCam;
    IF OBJECT_ID('tempdb..#LeyMinaStockImpCsv')  IS NOT NULL DROP TABLE #LeyMinaStockImpCsv;
    ;WITH MovCam_Deduplicado AS
    (
        SELECT
            m.*,
            rn = ROW_NUMBER() OVER
            (
                PARTITION BY
                    m.Fecha, m.Turno, m.Origen, m.Solido, m.Fase, m.Banco,
                    m.Pala, m.Destino, m.Poligono_CIO, m.Flota_CEX, m.Ton,
                    m.N_BREAK, m.[Ton hum diseño CAEX], m.Tonelaje_Hum_CIO,
                    m.Tonelaje_seco_CIO, m.PONDHumedad
                ORDER BY m.mov_id
            )
        FROM [inventar_SpcHidr].[mov_cam] AS m
        WHERE CAST(m.Fecha AS date) >= @FechaInicioProceso
          AND CAST(m.Fecha AS date) <= @FechaFin
          AND UPPER(LTRIM(RTRIM(ISNULL(m.Destino, '')))) = 'CH01'
          AND UPPER(LTRIM(RTRIM(ISNULL(m.Fase, '')))) <> 'SRR'
    )
    SELECT
        Fecha = CAST(Fecha AS date),
        Tonelaje_Mina_Stock = SUM(Tonelaje_seco_CIO),
        Ley_CuT_Mina_Stock = SUM(Tonelaje_seco_CIO * CuTG00) / NULLIF(SUM(Tonelaje_seco_CIO), 0),
        Cantidad_Registros_Validos = COUNT(*)
    INTO #LeyMinaStockMovCam
    FROM MovCam_Deduplicado
    WHERE rn = 1 AND Tonelaje_seco_CIO > 0 AND CuTG00 IS NOT NULL
    GROUP BY CAST(Fecha AS date);
    CREATE CLUSTERED INDEX ix_lms_mc ON #LeyMinaStockMovCam(Fecha);
    SELECT
        CAST(ic.[date] AS date) AS Fecha,
        SUM(COALESCE(ic.tonnage, 0)) AS Tonelaje_Mina_Stock,
        SUM(ic.tonnage * ic.cut)
            / NULLIF(SUM(CASE WHEN ic.cut IS NOT NULL THEN ic.tonnage ELSE NULL END), 0)
            AS Ley_CuT_Mina_Stock,
        COUNT(*) AS Cantidad_Registros_Validos
    INTO #LeyMinaStockImpCsv
    FROM [PROD_SIIR].[hidro].[imp_csv] ic
    WHERE ic.[to]     = 'CH01'
      AND ic.shovel  <> 'SRR'
      AND ic.origen   = 'IMP'
      AND ic.tonnage  > 0
      AND ic.cut IS NOT NULL
      AND CAST(ic.[date] AS date) >= @FechaInicioProceso
      AND CAST(ic.[date] AS date) <= @FechaFin
    GROUP BY CAST(ic.[date] AS date);
    CREATE CLUSTERED INDEX ix_lms_ic ON #LeyMinaStockImpCsv(Fecha);
    SELECT
        mc.Fecha,
        mc.Tonelaje_Mina_Stock,
        mc.Ley_CuT_Mina_Stock,
        mc.Cantidad_Registros_Validos,
        CAST('MOV_CAM' AS varchar(40)) AS Fuente_Ley_Mina_Stock
    INTO #LeyMinaStock
    FROM #LeyMinaStockMovCam mc
    UNION ALL
    SELECT
        ic.Fecha,
        ic.Tonelaje_Mina_Stock,
        ic.Ley_CuT_Mina_Stock,
        ic.Cantidad_Registros_Validos,
        CAST('IMP_CSV_PRELIMINAR' AS varchar(40))
    FROM #LeyMinaStockImpCsv ic
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM #LeyMinaStockMovCam mc2
        WHERE mc2.Fecha = ic.Fecha
    );
    CREATE CLUSTERED INDEX ix_lms ON #LeyMinaStock(Fecha);
    DECLARE @LmsFilas   int;
    DECLARE @LmsMovCam  int;
    DECLARE @LmsImpCsv  int;
    SELECT
        @LmsFilas  = COUNT(*),
        @LmsMovCam = SUM(CASE WHEN Fuente_Ley_Mina_Stock = 'MOV_CAM' THEN 1 ELSE 0 END),
        @LmsImpCsv = SUM(CASE WHEN Fuente_Ley_Mina_Stock = 'IMP_CSV_PRELIMINAR' THEN 1 ELSE 0 END)
    FROM #LeyMinaStock;
    PRINT 'PASO 3  Ley mina + stock: ' + CAST(DATEDIFF(ms, @t1, SYSDATETIME()) AS varchar) + ' ms - '
        + CAST(COALESCE(@LmsFilas,0) AS varchar) + ' filas ('
        + CAST(COALESCE(@LmsMovCam,0) AS varchar) + ' mov_cam, '
        + CAST(COALESCE(@LmsImpCsv,0) AS varchar) + ' imp_csv preliminar)';
    /* ================================================================
       PASO 4: Humedad / Sal / Apilado TMH
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Apilado') IS NOT NULL DROP TABLE #Apilado;
    SELECT
        CAST(Fecha AS date)      AS Fecha,
        Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia,
        Sal_turno_A, Sal_Turno_B, Sal_promedio_dia,
        Apilado_TMH_turno_A, Apilado_TMH_turno_B, Apilado_TMH_promedio_dia
    INTO #Apilado
    FROM [inventar_SpcHidr].[Historico_Apilado_Diario]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_ap ON #Apilado(Fecha);
    PRINT 'PASO 4  Apilado/Humedad  : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 5: Generador diario
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Generador') IS NOT NULL DROP TABLE #Generador;
    SELECT
        g.Fecha, g.Apilado_TMS_Real_Dia, g.Apilado_TMS_Plan,
        g.Material_Operacion, g.Modulo, g.Avance, g.CuT_Real_Dia, g.CuT_Plan
    INTO #Generador
    FROM [inventar_SpcHidr].[fn_generador_reporte_diario_emision_test](@FechaInicioProceso, @FechaFinExclusiva) g;
    CREATE CLUSTERED INDEX ix_gen ON #Generador(Fecha);
    PRINT 'PASO 5  Generador diario : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 6: SRR diario
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#SRR') IS NOT NULL DROP TABLE #SRR;
    ;WITH srr_turno AS
    (
        SELECT
            CAST(Fecha AS date) AS Fecha,
            Turno,
            CASE
                WHEN SRR IS NULL OR Apilado_TMS_Real IS NULL THEN NULL
                ELSE Apilado_TMS_Real * SRR / 100.0
            END AS SRR_TMS_Turno
        FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test]
        WHERE CAST(Fecha AS date) >= @FechaInicioProceso
          AND CAST(Fecha AS date) <= @FechaFin
    )
    SELECT
        Fecha,
        SUM(CASE WHEN Turno = 'A' THEN SRR_TMS_Turno END) AS SRR_TMS_Turno_A,
        SUM(CASE WHEN Turno = 'B' THEN SRR_TMS_Turno END) AS SRR_TMS_Turno_B,
        SUM(SRR_TMS_Turno)                                AS SRR_TMS_Dia,
        CASE
            WHEN COUNT(DISTINCT Turno) >= 2
             AND SUM(CASE WHEN SRR_TMS_Turno IS NULL THEN 1 ELSE 0 END) = 0
                THEN 'OK'
            WHEN SUM(SRR_TMS_Turno) IS NOT NULL
                THEN 'OK_PARCIAL'
            ELSE 'SIN_SRR_TMS'
        END AS Flag_SRR_TMS_Dia
    INTO #SRR
    FROM srr_turno
    GROUP BY Fecha;
    CREATE CLUSTERED INDEX ix_srr ON #SRR(Fecha);
    PRINT 'PASO 6  SRR              : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 7: Produccion catodica
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Catodos') IS NOT NULL DROP TABLE #Catodos;
    SELECT
        CAST(Fecha AS date)     AS Fecha,
        Produccion_Catodos_Real
    INTO #Catodos
    FROM [inventar_SpcHidr].[v_produccion_catodica_diaria_test]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_cat ON #Catodos(Fecha);
    PRINT 'PASO 7  Catodos          : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 8: Plan mensual
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#Plan') IS NOT NULL DROP TABLE #Plan;
    SELECT
        CAST(Fecha AS date)             AS Fecha,
        Ley_CuT_Plan_Fuente, Cobre_Fino_Apilado_Plan_Fuente,
        TMS_Rotopala_1_Plan, TMS_Rotopala_2_Plan,
        Camiones_TMS_Plan, Produccion_Catodos_Plan,
        SRR_TMS_Plan, Ley_CuT_Plan_SRR
    INTO #Plan
    FROM [inventar_SpcHidr].[v_planes_mensuales_diarios_test]
    WHERE CAST(Fecha AS date) >= @FechaInicioProceso
      AND CAST(Fecha AS date) <= @FechaFin;
    CREATE CLUSTERED INDEX ix_pm ON #Plan(Fecha);
    PRINT 'PASO 8  Plan mensual     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@@ROWCOUNT AS varchar) + ' filas';
    /* ================================================================
       PASO 9: Reclamo base                                     v1.13
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoBase') IS NOT NULL DROP TABLE #ReclamoBase;
    SELECT
        r.fecha_operacion              AS Fecha,
        r.pad_id, r.[campaña_id], r.modulo_id, r.modulo_numero, r.rotopala_id,
        r.avance_porcentaje, r.avance_total_porcentaje, r.avance_camiones_porcentaje,
        r.tonelaje_reclamado_diario, r.tonelaje_camiones_diario, r.volumen_diario_m3,
        r.fuente_reclamo, r.metodo_calculo, r.flag_calculo
    INTO #ReclamoBase
    FROM [reclamo].[v_reclamo_para_conciliados] r
    WHERE r.fecha_operacion >= @FechaInicioProceso
      AND r.fecha_operacion <= @FechaFin;
    CREATE CLUSTERED INDEX ix_rb ON #ReclamoBase(Fecha, pad_id);
    DECLARE @RbFilas int = @@ROWCOUNT;
    PRINT 'PASO 9  Reclamo base     : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - ' + CAST(@RbFilas AS varchar) + ' filas (fuente: reclamo.v_reclamo_para_conciliados)';
    /* ================================================================
       PASO 10: Reclamo TMS y contexto por pad                  v1.14
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoOxidosTMS')   IS NOT NULL DROP TABLE #ReclamoOxidosTMS;
    IF OBJECT_ID('tempdb..#ReclamoSulfurosTMS')  IS NOT NULL DROP TABLE #ReclamoSulfurosTMS;
    IF OBJECT_ID('tempdb..#GanadorOxRaw')        IS NOT NULL DROP TABLE #GanadorOxRaw;
    IF OBJECT_ID('tempdb..#GanadorSuRaw')        IS NOT NULL DROP TABLE #GanadorSuRaw;
    IF OBJECT_ID('tempdb..#GanadorOx')           IS NOT NULL DROP TABLE #GanadorOx;
    IF OBJECT_ID('tempdb..#GanadorSu')           IS NOT NULL DROP TABLE #GanadorSu;
    IF OBJECT_ID('tempdb..#GrupoOx')             IS NOT NULL DROP TABLE #GrupoOx;
    IF OBJECT_ID('tempdb..#GrupoSu')             IS NOT NULL DROP TABLE #GrupoSu;
    IF OBJECT_ID('tempdb..#ReclamoOxidosCtx')    IS NOT NULL DROP TABLE #ReclamoOxidosCtx;
    IF OBJECT_ID('tempdb..#ReclamoSulfurosCtx')  IS NOT NULL DROP TABLE #ReclamoSulfurosCtx;
    SELECT Fecha, SUM(tonelaje_reclamado_diario) AS TMS_Rotopala_1_Real
    INTO #ReclamoOxidosTMS  FROM #ReclamoBase WHERE pad_id = 1 GROUP BY Fecha;
    SELECT Fecha, SUM(tonelaje_reclamado_diario) AS TMS_Rotopala_2_Real
    INTO #ReclamoSulfurosTMS FROM #ReclamoBase WHERE pad_id = 2 GROUP BY Fecha;
    SELECT
        rb.Fecha, rb.modulo_id, rb.modulo_numero, rb.avance_porcentaje,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
        rb.[campaña_id], rb.tonelaje_reclamado_diario
    INTO #GanadorOxRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.pad_id = 1 AND rb.tonelaje_reclamado_diario > 0;
    CREATE CLUSTERED INDEX ix_gor ON #GanadorOxRaw(Fecha, modulo_numero);
    SELECT
        rb.Fecha, rb.modulo_id, rb.modulo_numero, rb.avance_porcentaje,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS campana_nombre,
        rb.[campaña_id], rb.tonelaje_reclamado_diario
    INTO #GanadorSuRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.pad_id = 2 AND rb.tonelaje_reclamado_diario > 0;
    CREATE CLUSTERED INDEX ix_gsr ON #GanadorSuRaw(Fecha, modulo_numero);
    CREATE TABLE #GanadorOx (Fecha date NOT NULL PRIMARY KEY, modulo_numero int NULL, avance_porcentaje float NULL, campana_nombre nvarchar(255) NULL);
    CREATE TABLE #GanadorSu (Fecha date NOT NULL PRIMARY KEY, modulo_numero int NULL, avance_porcentaje float NULL, campana_nombre nvarchar(255) NULL);
    DECLARE @PisoOx int = 0, @CampanaPisoOx nvarchar(255) = NULL;
    DECLARE @PisoSu int = 0, @CampanaPisoSu nvarchar(255) = NULL;
    DECLARE @FechaCur date, @ModCur int, @AvanceCur float, @CampCur nvarchar(255);
    DECLARE dias_ox CURSOR LOCAL FAST_FORWARD FOR
        SELECT DISTINCT Fecha FROM #GanadorOxRaw ORDER BY Fecha;
    OPEN dias_ox;
    FETCH NEXT FROM dias_ox INTO @FechaCur;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @ModCur = NULL; SET @AvanceCur = NULL; SET @CampCur = NULL;
        SELECT TOP (1) @ModCur = modulo_numero, @AvanceCur = avance_porcentaje, @CampCur = campana_nombre
        FROM #GanadorOxRaw
        WHERE Fecha = @FechaCur
          AND (@CampanaPisoOx IS NULL OR campana_nombre <> @CampanaPisoOx OR modulo_numero >= @PisoOx)
        ORDER BY avance_porcentaje ASC, modulo_id DESC;
        IF @ModCur IS NOT NULL
        BEGIN
            INSERT INTO #GanadorOx (Fecha, modulo_numero, avance_porcentaje, campana_nombre)
            VALUES (@FechaCur, @ModCur, @AvanceCur, @CampCur);
            IF @CampanaPisoOx IS NULL OR @CampCur <> @CampanaPisoOx
            BEGIN
                SET @CampanaPisoOx = @CampCur;
                SET @PisoOx = @ModCur;
            END
            ELSE IF @ModCur > @PisoOx
                SET @PisoOx = @ModCur;
        END;
        FETCH NEXT FROM dias_ox INTO @FechaCur;
    END;
    CLOSE dias_ox;
    DEALLOCATE dias_ox;
    DECLARE dias_su CURSOR LOCAL FAST_FORWARD FOR
        SELECT DISTINCT Fecha FROM #GanadorSuRaw ORDER BY Fecha;
    OPEN dias_su;
    FETCH NEXT FROM dias_su INTO @FechaCur;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @ModCur = NULL; SET @AvanceCur = NULL; SET @CampCur = NULL;
        SELECT TOP (1) @ModCur = modulo_numero, @AvanceCur = avance_porcentaje, @CampCur = campana_nombre
        FROM #GanadorSuRaw
        WHERE Fecha = @FechaCur
          AND (@CampanaPisoSu IS NULL OR campana_nombre <> @CampanaPisoSu OR modulo_numero >= @PisoSu)
        ORDER BY avance_porcentaje ASC, modulo_id DESC;
        IF @ModCur IS NOT NULL
        BEGIN
            INSERT INTO #GanadorSu (Fecha, modulo_numero, avance_porcentaje, campana_nombre)
            VALUES (@FechaCur, @ModCur, @AvanceCur, @CampCur);
            IF @CampanaPisoSu IS NULL OR @CampCur <> @CampanaPisoSu
            BEGIN
                SET @CampanaPisoSu = @CampCur;
                SET @PisoSu = @ModCur;
            END
            ELSE IF @ModCur > @PisoSu
                SET @PisoSu = @ModCur;
        END;
        FETCH NEXT FROM dias_su INTO @FechaCur;
    END;
    CLOSE dias_su;
    DEALLOCATE dias_su;
    SELECT
        f.Fecha, g.modulo_numero, g.avance_porcentaje, g.campana_nombre,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END) OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoOx
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase WHERE pad_id = 1) f
    LEFT JOIN #GanadorOx g ON g.Fecha = f.Fecha;
    SELECT
        Fecha,
        MAX(campana_nombre)    OVER (PARTITION BY grp) AS campana_nombre,
        MAX(modulo_numero)     OVER (PARTITION BY grp) AS modulo_numero,
        MAX(avance_porcentaje) OVER (PARTITION BY grp) AS avance_porcentaje
    INTO #ReclamoOxidosCtx
    FROM #GrupoOx;
    SELECT
        f.Fecha, g.modulo_numero, g.avance_porcentaje, g.campana_nombre,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END) OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoSu
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase WHERE pad_id = 2) f
    LEFT JOIN #GanadorSu g ON g.Fecha = f.Fecha;
    SELECT
        Fecha,
        MAX(campana_nombre)    OVER (PARTITION BY grp) AS campana_nombre,
        MAX(modulo_numero)     OVER (PARTITION BY grp) AS modulo_numero,
        MAX(avance_porcentaje) OVER (PARTITION BY grp) AS avance_porcentaje
    INTO #ReclamoSulfurosCtx
    FROM #GrupoSu;
    DROP TABLE #GanadorOxRaw;
    DROP TABLE #GanadorSuRaw;
    DROP TABLE #GanadorOx;
    DROP TABLE #GanadorSu;
    DROP TABLE #GrupoOx;
    DROP TABLE #GrupoSu;
    CREATE CLUSTERED INDEX ix_ro  ON #ReclamoOxidosTMS(Fecha);
    CREATE CLUSTERED INDEX ix_rs  ON #ReclamoSulfurosTMS(Fecha);
    CREATE CLUSTERED INDEX ix_roc ON #ReclamoOxidosCtx(Fecha);
    CREATE CLUSTERED INDEX ix_rsc ON #ReclamoSulfurosCtx(Fecha);
    PRINT 'PASO 10 Reclamo ctx/TMS  : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';
    /* ================================================================
       PASO 10b: Reclamo Camiones                                v1.13
    ================================================================ */
    SET @t1 = SYSDATETIME();
    IF OBJECT_ID('tempdb..#ReclamoCamionesTMS')  IS NOT NULL DROP TABLE #ReclamoCamionesTMS;
    IF OBJECT_ID('tempdb..#GanadorCamRaw')       IS NOT NULL DROP TABLE #GanadorCamRaw;
    IF OBJECT_ID('tempdb..#GanadorCam')          IS NOT NULL DROP TABLE #GanadorCam;
    IF OBJECT_ID('tempdb..#GrupoCam')            IS NOT NULL DROP TABLE #GrupoCam;
    IF OBJECT_ID('tempdb..#ReclamoCamionesCtx')  IS NOT NULL DROP TABLE #ReclamoCamionesCtx;
    SELECT
        rb.Fecha,
        SUM(CASE WHEN rb.pad_id = 1 THEN rb.tonelaje_camiones_diario ELSE 0 END) AS Camiones_TMS_Reclamo_Oxidos,
        SUM(CASE WHEN rb.pad_id = 2 THEN rb.tonelaje_camiones_diario ELSE 0 END) AS Camiones_TMS_Reclamo_Sulfuros,
        SUM(rb.tonelaje_camiones_diario) AS Camiones_TMS_total
    INTO #ReclamoCamionesTMS
    FROM #ReclamoBase rb
    GROUP BY rb.Fecha;
    CREATE CLUSTERED INDEX ix_rct ON #ReclamoCamionesTMS(Fecha);
    SELECT
        rb.Fecha,
        CAST(rb.modulo_numero AS nvarchar(255))   AS Modulo_reclamo_camiones,
        CAST(c.[numero_campaña] AS nvarchar(255)) AS Campana_reclamo_camiones,
        ROW_NUMBER() OVER (PARTITION BY rb.Fecha ORDER BY rb.tonelaje_camiones_diario DESC, rb.modulo_id DESC) AS rn
    INTO #GanadorCamRaw
    FROM #ReclamoBase rb
    LEFT JOIN [inventar_SpcHidr].[campaña] c ON c.[id_campaña] = rb.[campaña_id]
    WHERE rb.tonelaje_camiones_diario > 0;
    SELECT Fecha, Modulo_reclamo_camiones, Campana_reclamo_camiones
    INTO #GanadorCam
    FROM #GanadorCamRaw
    WHERE rn = 1;
    SELECT
        f.Fecha, g.Campana_reclamo_camiones, g.Modulo_reclamo_camiones,
        SUM(CASE WHEN g.Fecha IS NOT NULL THEN 1 ELSE 0 END) OVER (ORDER BY f.Fecha ROWS UNBOUNDED PRECEDING) AS grp
    INTO #GrupoCam
    FROM (SELECT DISTINCT Fecha FROM #ReclamoBase) f
    LEFT JOIN #GanadorCam g ON g.Fecha = f.Fecha;
    SELECT
        Fecha,
        MAX(Campana_reclamo_camiones) OVER (PARTITION BY grp) AS Campana_reclamo_camiones,
        MAX(Modulo_reclamo_camiones)  OVER (PARTITION BY grp) AS Modulo_reclamo_camiones
    INTO #ReclamoCamionesCtx
    FROM #GrupoCam;
    DROP TABLE #GanadorCamRaw;
    DROP TABLE #GanadorCam;
    DROP TABLE #GrupoCam;
    CREATE CLUSTERED INDEX ix_rcc ON #ReclamoCamionesCtx(Fecha);
    PRINT 'PASO 10b Reclamo camiones: ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms';
    /* ================================================================
       PASO 11: MERGE final
       Sin cambios respecto de la version validada -- el JOIN contra
       #LeyMinaStock solo usa Fecha y Ley_CuT_Mina_Stock, asi que la
       columna nueva Fuente_Ley_Mina_Stock (PASO 3) no requiere tocar
       nada aqui.
    ================================================================ */
    SET @t1 = SYSDATETIME();
    MERGE [inventar_SpcHidr].[Datos_conciliados_of] AS tgt
    USING
    (
        SELECT
            f.Fecha,
            aj.Chancado_TMS_Reporte AS Chancado_TMS_Real,
            a.Humedad_Turno_A, a.Humedad_Turno_B, a.Humedad_promedio_dia,
            a.Sal_turno_A, a.Sal_Turno_B, a.Sal_promedio_dia,
            CASE
                WHEN a.Apilado_TMH_turno_A IS NULL THEN NULL
                ELSE (a.Apilado_TMH_turno_A + COALESCE(a.Sal_turno_A, 0)) * COALESCE(aj.Factor_Aplicacion_Reportes, 1.0) - COALESCE(a.Sal_turno_A, 0)
            END AS Apilado_TMH_turno_A,
            CASE
                WHEN a.Apilado_TMH_turno_B IS NULL THEN NULL
                ELSE (a.Apilado_TMH_turno_B + COALESCE(a.Sal_turno_B, 0)) * COALESCE(aj.Factor_Aplicacion_Reportes, 1.0) - COALESCE(a.Sal_turno_B, 0)
            END AS Apilado_TMH_turno_B,
            aj.Apilado_TMH_Reporte AS Apilado_TMH_promedio_dia,
            aj.Apilado_TMS_Reporte AS Apilado_TMS_Real,
            g.Apilado_TMS_Plan     AS Apilado_TMS_Plan,
            CASE
                WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion))) IN ('SULFURO','SULFUROS') THEN 'Sulfuro'
                WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion))) IN ('OXIDO','OXIDOS','OXIDO','OXIDOS') THEN 'Oxido'
                ELSE g.Material_Operacion
            END AS Campana_apilado,
            g.Modulo AS Modulo_apilado,
            g.Avance AS Avance_apilado,
            g.CuT_Real_Dia AS Ley_CuT_Real,
            g.CuT_Plan     AS Ley_CuT_Plan,
            CASE
                WHEN COALESCE(aj.Apilado_TMS_Reporte, 0) = 0 THEN 0
                WHEN g.CuT_Real_Dia IS NULL THEN NULL
                ELSE aj.Apilado_TMS_Reporte * g.CuT_Real_Dia / 100.0
            END AS Cobre_fino_Apilado_Real,
            pm.Cobre_Fino_Apilado_Plan_Fuente AS Cobre_fino_Apilado_Plan,
            ro_tms.TMS_Rotopala_1_Real,
            pm.TMS_Rotopala_1_Plan,
            CAST(ro_ctx.campana_nombre    AS nvarchar(255)) AS Campana_reclamo_oxidos,
            CAST(ro_ctx.modulo_numero     AS int)           AS Modulo_reclamo_oxidos,
            CAST(ro_ctx.avance_porcentaje AS float)         AS Avance_reclamo_oxidos,
            rs_tms.TMS_Rotopala_2_Real,
            pm.TMS_Rotopala_2_Plan,
            CAST(rs_ctx.campana_nombre    AS nvarchar(255)) AS Campana_reclamo_sulfuros,
            CAST(rs_ctx.modulo_numero     AS int)           AS modulo_reclamo_sulfuros,
            CAST(rs_ctx.avance_porcentaje AS float)         AS Avance_reclamo_sulfuros,
            rc_tms.Camiones_TMS_Reclamo_Oxidos,
            rc_tms.Camiones_TMS_Reclamo_Sulfuros,
            CAST(NULL AS nvarchar(255)) AS Movido,
            CAST(NULL AS nvarchar(255)) AS Extraido,
            rc_tms.Camiones_TMS_total                              AS Camiones_TMS_total,
            pm.Camiones_TMS_Plan        AS Camiones_TMS_plan,
            rc_ctx.Campana_reclamo_camiones,
            rc_ctx.Modulo_reclamo_camiones,
            CASE
                WHEN rc_tms.Camiones_TMS_total           IS NULL
                  OR ro_tms.TMS_Rotopala_1_Real            IS NULL
                  OR rs_tms.TMS_Rotopala_2_Real            IS NULL
                    THEN NULL
                ELSE rc_tms.Camiones_TMS_total + ro_tms.TMS_Rotopala_1_Real + rs_tms.TMS_Rotopala_2_Real
            END AS Total_Ripios_Incluye_Camiones_Real,
            CASE
                WHEN pm.TMS_Rotopala_1_Plan IS NOT NULL
                 AND pm.TMS_Rotopala_2_Plan IS NOT NULL
                 AND pm.Camiones_TMS_Plan   IS NOT NULL
                THEN CAST(pm.TMS_Rotopala_1_Plan AS float) + CAST(pm.TMS_Rotopala_2_Plan AS float) + CAST(pm.Camiones_TMS_Plan AS float)
                ELSE NULL
            END AS Total_Ripios_Incluye_Camiones_Plan,
            p.Produccion_Catodos_Real,
            pm.Produccion_Catodos_Plan,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Turno_A ELSE NULL END AS SRR_TMS_Turno_A,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Turno_B ELSE NULL END AS SRR_TMS_Turno_B,
            CASE WHEN s.Flag_SRR_TMS_Dia = 'OK' THEN s.SRR_TMS_Dia ELSE NULL END AS SRR_TMS_promedio_dia,
            pm.SRR_TMS_Plan,
            CASE
                WHEN ISNULL(s.Flag_SRR_TMS_Dia, '') <> 'OK' OR s.SRR_TMS_Dia IS NULL OR s.SRR_TMS_Dia <= 0 THEN NULL
                WHEN g.CuT_Real_Dia IS NULL THEN NULL
                WHEN lms.Ley_CuT_Mina_Stock IS NULL THEN NULL
                WHEN CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1 THEN aj.Apilado_TMS_Bruto_Ajustado ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END IS NULL THEN NULL
                WHEN aj.Sal_TMH_Dia IS NULL THEN NULL
                WHEN aj.Delta_Inventario_Chancado_TMS IS NULL THEN NULL
                WHEN aj.Chancado_TMS_Reporte IS NULL THEN NULL
                ELSE
                    (
                        g.CuT_Real_Dia
                        * (
                            CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1 THEN aj.Apilado_TMS_Bruto_Ajustado ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END
                            - aj.Sal_TMH_Dia
                            + aj.Delta_Inventario_Chancado_TMS
                          )
                        - (lms.Ley_CuT_Mina_Stock * aj.Chancado_TMS_Reporte)
                    )
                    / NULLIF(s.SRR_TMS_Dia, 0)
            END AS Ley_CuT_Real_srr,
            pm.Ley_CuT_Plan_SRR AS Ley_CuT_Plan_srr,
            CASE
                WHEN COALESCE(aj.Apilado_TMS_Reporte, 0) > 0 AND g.CuT_Real_Dia IS NULL THEN 2
                WHEN p.Produccion_Catodos_Real IS NULL THEN 1
                ELSE 0
            END AS estado
        FROM #Fechas       f
        LEFT JOIN #Chancado          c      ON c.Fecha      = f.Fecha
        LEFT JOIN #Apilado           a      ON a.Fecha      = f.Fecha
        LEFT JOIN #Generador         g      ON g.Fecha      = f.Fecha
        LEFT JOIN #SRR               s      ON s.Fecha      = f.Fecha
        LEFT JOIN #Catodos           p      ON p.Fecha      = f.Fecha
        LEFT JOIN #Plan              pm     ON pm.Fecha     = f.Fecha
        LEFT JOIN #LeyMinaStock     lms     ON lms.Fecha     = f.Fecha
        LEFT JOIN #ReclamoOxidosTMS  ro_tms ON ro_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoOxidosCtx  ro_ctx ON ro_ctx.Fecha = f.Fecha
        LEFT JOIN #ReclamoSulfurosTMS rs_tms ON rs_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoSulfurosCtx rs_ctx ON rs_ctx.Fecha = f.Fecha
        LEFT JOIN #ReclamoCamionesTMS rc_tms ON rc_tms.Fecha = f.Fecha
        LEFT JOIN #ReclamoCamionesCtx rc_ctx ON rc_ctx.Fecha = f.Fecha
        LEFT JOIN [inventar_SpcHidr].[v_ajuste_camiones_emision_test] aj ON aj.Fecha = f.Fecha
    ) AS src ON tgt.Fecha = src.Fecha
    WHEN MATCHED THEN UPDATE SET
        Chancado_TMS_Real                  = src.Chancado_TMS_Real,
        Humedad_Turno_A                    = src.Humedad_Turno_A,
        Humedad_Turno_B                    = src.Humedad_Turno_B,
        Humedad_promedio_dia               = src.Humedad_promedio_dia,
        Sal_turno_A                        = src.Sal_turno_A,
        Sal_Turno_B                        = src.Sal_Turno_B,
        Sal_promedio_dia                   = src.Sal_promedio_dia,
        Apilado_TMH_turno_A                = src.Apilado_TMH_turno_A,
        Apilado_TMH_turno_B                = src.Apilado_TMH_turno_B,
        Apilado_TMH_promedio_dia           = src.Apilado_TMH_promedio_dia,
        Apilado_TMS_Real                   = src.Apilado_TMS_Real,
        Apilado_TMS_Plan                   = src.Apilado_TMS_Plan,
        Campana_apilado                    = src.Campana_apilado,
        Modulo_apilado                     = src.Modulo_apilado,
        Avance_apilado                     = src.Avance_apilado,
        Ley_CuT_Real                       = src.Ley_CuT_Real,
        Ley_CuT_Plan                       = src.Ley_CuT_Plan,
        Cobre_fino_Apilado_Real            = src.Cobre_fino_Apilado_Real,
        Cobre_fino_Apilado_Plan            = src.Cobre_fino_Apilado_Plan,
        TMS_Rotopala_1_Real                = src.TMS_Rotopala_1_Real,
        TMS_Rotopala_1_Plan                = src.TMS_Rotopala_1_Plan,
        Campana_reclamo_oxidos             = src.Campana_reclamo_oxidos,
        Modulo_reclamo_oxidos              = src.Modulo_reclamo_oxidos,
        Avance_reclamo_oxidos              = src.Avance_reclamo_oxidos,
        TMS_Rotopala_2_Real                = src.TMS_Rotopala_2_Real,
        TMS_Rotopala_2_Plan                = src.TMS_Rotopala_2_Plan,
        Campana_reclamo_sulfuros           = src.Campana_reclamo_sulfuros,
        modulo_reclamo_sulfuros            = src.modulo_reclamo_sulfuros,
        Avance_reclamo_sulfuros            = src.Avance_reclamo_sulfuros,
        Camiones_TMS_Reclamo_Oxidos        = src.Camiones_TMS_Reclamo_Oxidos,
        Camiones_TMS_Reclamo_Sulfuros      = src.Camiones_TMS_Reclamo_Sulfuros,
        Movido                             = src.Movido,
        Extraido                           = src.Extraido,
        Camiones_TMS_total                 = src.Camiones_TMS_total,
        Camiones_TMS_plan                  = src.Camiones_TMS_plan,
        Campana_reclamo_camiones           = src.Campana_reclamo_camiones,
        Modulo_reclamo_camiones            = src.Modulo_reclamo_camiones,
        Total_Ripios_Incluye_Camiones_Real = src.Total_Ripios_Incluye_Camiones_Real,
        Total_Ripios_Incluye_Camiones_Plan = src.Total_Ripios_Incluye_Camiones_Plan,
        Produccion_Catodos_Real            = src.Produccion_Catodos_Real,
        Produccion_Catodos_Plan            = src.Produccion_Catodos_Plan,
        SRR_TMS_Turno_A                    = src.SRR_TMS_Turno_A,
        SRR_TMS_Turno_B                    = src.SRR_TMS_Turno_B,
        SRR_TMS_promedio_dia               = src.SRR_TMS_promedio_dia,
        SRR_TMS_Plan                       = src.SRR_TMS_Plan,
        Ley_CuT_Real_srr                   = src.Ley_CuT_Real_srr,
        Ley_CuT_Plan_srr                   = src.Ley_CuT_Plan_srr,
        estado                             = src.estado
    WHEN NOT MATCHED BY TARGET THEN INSERT
    (
        Fecha, Chancado_TMS_Real,
        Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia,
        Sal_turno_A, Sal_Turno_B, Sal_promedio_dia,
        Apilado_TMH_turno_A, Apilado_TMH_turno_B, Apilado_TMH_promedio_dia,
        Apilado_TMS_Real, Apilado_TMS_Plan,
        Campana_apilado, Modulo_apilado, Avance_apilado,
        Ley_CuT_Real, Ley_CuT_Plan,
        Cobre_fino_Apilado_Real, Cobre_fino_Apilado_Plan,
        TMS_Rotopala_1_Real, TMS_Rotopala_1_Plan,
        Campana_reclamo_oxidos, Modulo_reclamo_oxidos, Avance_reclamo_oxidos,
        TMS_Rotopala_2_Real, TMS_Rotopala_2_Plan,
        Campana_reclamo_sulfuros, modulo_reclamo_sulfuros, Avance_reclamo_sulfuros,
        Camiones_TMS_Reclamo_Oxidos, Camiones_TMS_Reclamo_Sulfuros,
        Movido, Extraido, Camiones_TMS_total, Camiones_TMS_plan,
        Campana_reclamo_camiones, Modulo_reclamo_camiones,
        Total_Ripios_Incluye_Camiones_Real, Total_Ripios_Incluye_Camiones_Plan,
        Produccion_Catodos_Real, Produccion_Catodos_Plan,
        SRR_TMS_Turno_A, SRR_TMS_Turno_B, SRR_TMS_promedio_dia, SRR_TMS_Plan,
        Ley_CuT_Real_srr, Ley_CuT_Plan_srr, estado
    )
    VALUES
    (
        src.Fecha, src.Chancado_TMS_Real,
        src.Humedad_Turno_A, src.Humedad_Turno_B, src.Humedad_promedio_dia,
        src.Sal_turno_A, src.Sal_Turno_B, src.Sal_promedio_dia,
        src.Apilado_TMH_turno_A, src.Apilado_TMH_turno_B, src.Apilado_TMH_promedio_dia,
        src.Apilado_TMS_Real, src.Apilado_TMS_Plan,
        src.Campana_apilado, src.Modulo_apilado, src.Avance_apilado,
        src.Ley_CuT_Real, src.Ley_CuT_Plan,
        src.Cobre_fino_Apilado_Real, src.Cobre_fino_Apilado_Plan,
        src.TMS_Rotopala_1_Real, src.TMS_Rotopala_1_Plan,
        src.Campana_reclamo_oxidos, src.Modulo_reclamo_oxidos, src.Avance_reclamo_oxidos,
        src.TMS_Rotopala_2_Real, src.TMS_Rotopala_2_Plan,
        src.Campana_reclamo_sulfuros, src.modulo_reclamo_sulfuros, src.Avance_reclamo_sulfuros,
        src.Camiones_TMS_Reclamo_Oxidos, src.Camiones_TMS_Reclamo_Sulfuros,
        src.Movido, src.Extraido, src.Camiones_TMS_total, src.Camiones_TMS_plan,
        src.Campana_reclamo_camiones, src.Modulo_reclamo_camiones,
        src.Total_Ripios_Incluye_Camiones_Real, src.Total_Ripios_Incluye_Camiones_Plan,
        src.Produccion_Catodos_Real, src.Produccion_Catodos_Plan,
        src.SRR_TMS_Turno_A, src.SRR_TMS_Turno_B, src.SRR_TMS_promedio_dia, src.SRR_TMS_Plan,
        src.Ley_CuT_Real_srr, src.Ley_CuT_Plan_srr, src.estado
    );
    PRINT 'PASO 11 MERGE            : ' + CAST(DATEDIFF(ms,@t1,SYSDATETIME()) AS varchar) + ' ms - '
        + CAST(@@ROWCOUNT AS varchar) + ' filas afectadas';
    PRINT '-- TOTAL                 : ' + CAST(DATEDIFF(ms,@t0,SYSDATETIME()) AS varchar) + ' ms';
    DROP TABLE IF EXISTS #Fechas;
    DROP TABLE IF EXISTS #Chancado;
    DROP TABLE IF EXISTS #ChancadoMovCam;
    DROP TABLE IF EXISTS #ChancadoImpCsv;
    DROP TABLE IF EXISTS #LeyMinaStock;
    DROP TABLE IF EXISTS #LeyMinaStockMovCam;
    DROP TABLE IF EXISTS #LeyMinaStockImpCsv;
    DROP TABLE IF EXISTS #Apilado;
    DROP TABLE IF EXISTS #Generador;
    DROP TABLE IF EXISTS #SRR;
    DROP TABLE IF EXISTS #Catodos;
    DROP TABLE IF EXISTS #Plan;
    DROP TABLE IF EXISTS #ReclamoBase;
    DROP TABLE IF EXISTS #ReclamoOxidosTMS;
    DROP TABLE IF EXISTS #ReclamoSulfurosTMS;
    DROP TABLE IF EXISTS #ReclamoOxidosCtx;
    DROP TABLE IF EXISTS #ReclamoSulfurosCtx;
    DROP TABLE IF EXISTS #ReclamoCamionesTMS;
    DROP TABLE IF EXISTS #ReclamoCamionesCtx;
    EXEC sys.sp_set_session_context @key = N'fecha_corte_camiones', @value = NULL;
    END TRY
    BEGIN CATCH
        EXEC sys.sp_set_session_context @key = N'fecha_corte_camiones', @value = NULL;
        THROW;
    END CATCH
END;
GO

-- ============================================================================
-- inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-08-02 20:56:20.490000
-- ============================================================================

CREATE   PROCEDURE
    [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_test]
(
    @FechaInicio   date,
    @FechaFin      date,
    @DiasReproceso int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    /* ============================================================
       0. Validaciones
       ============================================================ */

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;

    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;

    IF @DiasReproceso IS NULL OR @DiasReproceso < 0
        THROW 50003, '@DiasReproceso debe ser mayor o igual que cero.', 1;

    IF OBJECT_ID
    (
        '[inventar_SpcHidr].[Control_Factor_Ajuste_Camiones_v2_test]',
        'U'
    ) IS NULL
        THROW 50004,
              'No existe la tabla Control_Factor_Ajuste_Camiones_v2_test.',
              1;

    DECLARE @FechaInicioProceso date =
        CASE
            WHEN DATEADD(DAY, -@DiasReproceso, @FechaFin) < @FechaInicio
                THEN DATEADD(DAY, -@DiasReproceso, @FechaFin)
            ELSE @FechaInicio
        END;

    DECLARE @FechaCalculo datetime2(7) = SYSDATETIME();


    /* ============================================================
       1. Capturar la salida del cálculo validado
       ============================================================ */

    IF OBJECT_ID('tempdb..#CalculoFactorV2') IS NOT NULL
        DROP TABLE #CalculoFactorV2;

    CREATE TABLE #CalculoFactorV2
    (
        Fecha date NOT NULL,

        Apilado_TMH_Bruto float NULL,
        Apilado_TMH_Neto float NULL,
        Sal_Dia float NULL,
        Humedad_Inventario float NULL,

        Apilado_TMS_Sin_Ajuste float NULL,

        Total_Inventario_Chancado_TMS float NULL,
        Inventario_Chancado_TMS_Anterior float NULL,
        Delta_Inventario_Chancado_TMS float NULL,

        SRR_TMS_Dia float NULL,

        Mineral_Chancado_TMS_Sin_Ajuste float NULL,
        Chancado_TMS_Sin_Ajuste float NULL,
        Chancado_TMH_Sin_Ajuste float NULL,

        Produccion_KOM_TMH float NULL,
        Produccion_CAT_TMH float NULL,
        Dato_Mina_TMH float NULL,

        Vueltas_KOM float NULL,
        Vueltas_CAT float NULL,

        Participacion_KOM float NULL,
        Participacion_CAT float NULL,

        Chancado_KOM_TMH_Sin_Ajuste float NULL,
        Chancado_CAT_TMH_Sin_Ajuste float NULL,

        Carga_KOM_Sin_Ajuste float NULL,
        Carga_CAT_Sin_Ajuste float NULL,

        KOM_TMH_Corregido float NULL,
        CAT_TMH_Corregido float NULL,
        Chancado_TMH_Corregido_Total float NULL,

        Factor_Ajuste_Calculado float NULL,
        Flag_Factor_Ajuste_Valido bit NULL,
        Estado_Calculo varchar(40) NULL,

        Cantidad_Registros_Originales int NULL,
        Cantidad_Registros_Validos int NULL,
        Cantidad_Duplicados_Eliminados int NULL,

        Check_TMH_Bruto float NULL,
        Check_Produccion_Flotas float NULL,

        Flag_Continuidad_Diaria bit NULL,
        Flag_Inventario_Valido bit NULL,
        Flag_Humedad_Inventario_Valida bit NULL
    );

    INSERT INTO #CalculoFactorV2
    EXEC [inventar_SpcHidr].[sp_factor_ajuste_camiones_test]
        @FechaInicio = @FechaInicioProceso,
        @FechaFin    = @FechaFin;

    CREATE UNIQUE CLUSTERED INDEX IX_CalculoFactorV2_Fecha
        ON #CalculoFactorV2(Fecha);


    /* ============================================================
       2. Recuperar SRR por turno para trazabilidad
       ============================================================ */

    IF OBJECT_ID('tempdb..#SRRTurnos') IS NOT NULL
        DROP TABLE #SRRTurnos;

    SELECT
        CAST(r.Fecha AS date) AS Fecha,

        SUM
        (
            CASE
                WHEN UPPER(LTRIM(RTRIM(r.Turno))) = 'A'
                THEN
                    COALESCE(
                        TRY_CONVERT(float, r.Apilado_TMS_Real),
                        0.0
                    )
                    *
                    COALESCE(
                        TRY_CONVERT(float, r.SRR),
                        0.0
                    )
                    / 100.0
                ELSE 0.0
            END
        ) AS SRR_TMS_Turno_A,

        SUM
        (
            CASE
                WHEN UPPER(LTRIM(RTRIM(r.Turno))) = 'B'
                THEN
                    COALESCE(
                        TRY_CONVERT(float, r.Apilado_TMS_Real),
                        0.0
                    )
                    *
                    COALESCE(
                        TRY_CONVERT(float, r.SRR),
                        0.0
                    )
                    / 100.0
                ELSE 0.0
            END
        ) AS SRR_TMS_Turno_B

    INTO #SRRTurnos

    FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test] AS r

    WHERE CAST(r.Fecha AS date)
          BETWEEN @FechaInicioProceso AND @FechaFin

    GROUP BY CAST(r.Fecha AS date);

    CREATE UNIQUE CLUSTERED INDEX IX_SRRTurnos_Fecha
        ON #SRRTurnos(Fecha);


    /* ============================================================
       3. Construir fuente persistible

       Si el factor no es válido:
       - Factor_Ajuste queda NULL.
       - Los valores ajustados quedan NULL.
       - Los reportes decidirán posteriormente si aplican fallback
         hacia el valor basal.
       ============================================================ */

    IF OBJECT_ID('tempdb..#FuenteFactorV2') IS NOT NULL
        DROP TABLE #FuenteFactorV2;

    ;WITH Base AS
    (
        SELECT
            c.*,

            COALESCE(s.SRR_TMS_Turno_A, 0.0)
                AS SRR_TMS_Turno_A,

            COALESCE(s.SRR_TMS_Turno_B, 0.0)
                AS SRR_TMS_Turno_B,

            CASE
                WHEN c.Humedad_Inventario >= 0
                 AND c.Humedad_Inventario < 100
                    THEN 1.0 - c.Humedad_Inventario / 100.0
                ELSE NULL
            END AS Factor_Seco

        FROM #CalculoFactorV2 AS c

        LEFT JOIN #SRRTurnos AS s
            ON s.Fecha = c.Fecha
    ),

    AjusteTMH AS
    (
        SELECT
            b.*,

            CASE
                WHEN b.Flag_Factor_Ajuste_Valido = 1
                 AND b.Factor_Ajuste_Calculado IS NOT NULL
                THEN
                    b.Apilado_TMH_Bruto
                    * b.Factor_Ajuste_Calculado
                ELSE NULL
            END AS Apilado_TMH_Bruto_Ajustado,

            CASE
                WHEN b.Flag_Factor_Ajuste_Valido = 1
                 AND b.Factor_Ajuste_Calculado IS NOT NULL
                 AND b.Sal_Dia IS NOT NULL
                THEN
                    (
                        b.Apilado_TMH_Bruto
                        * b.Factor_Ajuste_Calculado
                    )
                    - b.Sal_Dia
                ELSE NULL
            END AS Apilado_TMH_Neto_Ajustado,

            CASE
    WHEN b.Apilado_TMS_Sin_Ajuste IS NOT NULL
     AND b.Sal_Dia IS NOT NULL
    THEN
        b.Apilado_TMS_Sin_Ajuste
        - b.Sal_Dia
    ELSE NULL
END AS Apilado_TMS_Neto_Sin_Ajuste

        FROM Base AS b
    ),

    AjusteTMS AS
    (
        SELECT
            a.*,

            CASE
                WHEN a.Apilado_TMH_Bruto_Ajustado IS NOT NULL
                 AND a.Factor_Seco IS NOT NULL
                THEN
                    a.Apilado_TMH_Bruto_Ajustado
                    * a.Factor_Seco
                ELSE NULL
            END AS Apilado_TMS_Bruto_Ajustado,

           CASE
    WHEN a.Apilado_TMH_Bruto_Ajustado IS NOT NULL
     AND a.Factor_Seco IS NOT NULL
     AND a.Sal_Dia IS NOT NULL
    THEN
        (
            a.Apilado_TMH_Bruto_Ajustado
            * a.Factor_Seco
        )
        - a.Sal_Dia
    ELSE NULL
END AS Apilado_TMS_Neto_Ajustado

        FROM AjusteTMH AS a
    ),

    BalanceAjustado AS
    (
        SELECT
            a.*,

            CASE
                WHEN a.Apilado_TMS_Bruto_Ajustado IS NOT NULL
                 AND a.Delta_Inventario_Chancado_TMS IS NOT NULL
                THEN
                    a.Apilado_TMS_Bruto_Ajustado
                    + a.Delta_Inventario_Chancado_TMS
                ELSE NULL
            END AS Mineral_Chancado_TMS_Ajustado

        FROM AjusteTMS AS a
    )

    SELECT
        b.Fecha,

        CAST(380.0 AS float) AS Limite_KOM_TMH_Viaje,
        CAST(265.0 AS float) AS Limite_CAT_TMH_Viaje,

        b.Apilado_TMH_Bruto
            AS Apilado_TMH_Bruto_Original,

        b.Apilado_TMH_Neto
            AS Apilado_TMH_Neto_Original,

        b.Sal_Dia
            AS Sal_TMH_Dia,

        b.Humedad_Inventario
            AS Humedad_Pct,

        b.Apilado_TMS_Sin_Ajuste
            AS Apilado_TMS_Bruto_Sin_Ajuste,

        b.Apilado_TMS_Neto_Sin_Ajuste,

        b.Total_Inventario_Chancado_TMS
            AS Inventario_Chancado_TMS_Actual,

        b.Inventario_Chancado_TMS_Anterior,
        b.Delta_Inventario_Chancado_TMS,

        b.Flag_Continuidad_Diaria,
        b.Flag_Inventario_Valido,

        b.Flag_Humedad_Inventario_Valida
            AS Flag_Humedad_Valida,

        b.SRR_TMS_Turno_A,
        b.SRR_TMS_Turno_B,
        b.SRR_TMS_Dia,

        b.Mineral_Chancado_TMS_Sin_Ajuste,
        b.Chancado_TMS_Sin_Ajuste,
        b.Chancado_TMH_Sin_Ajuste,

        b.Produccion_KOM_TMH,
        b.Produccion_CAT_TMH,
        b.Dato_Mina_TMH,

        b.Vueltas_KOM,
        b.Vueltas_CAT,

        b.Participacion_KOM,
        b.Participacion_CAT,

        b.Chancado_KOM_TMH_Sin_Ajuste,
        b.Chancado_CAT_TMH_Sin_Ajuste,

        b.Carga_KOM_Sin_Ajuste
            AS Carga_KOM_TMH_Viaje_Sin_Ajuste,

        b.Carga_CAT_Sin_Ajuste
            AS Carga_CAT_TMH_Viaje_Sin_Ajuste,

        b.KOM_TMH_Corregido,
        b.CAT_TMH_Corregido,
        b.Chancado_TMH_Corregido_Total,

        CASE
            WHEN b.Flag_Factor_Ajuste_Valido = 1
                THEN b.Factor_Ajuste_Calculado
            ELSE NULL
        END AS Factor_Ajuste,

        b.Flag_Factor_Ajuste_Valido,
        b.Estado_Calculo,

        b.Apilado_TMH_Bruto_Ajustado,
        b.Apilado_TMS_Bruto_Ajustado,

        b.Mineral_Chancado_TMS_Ajustado,

        CASE
            WHEN b.Mineral_Chancado_TMS_Ajustado IS NOT NULL
             AND b.Sal_Dia IS NOT NULL
             AND b.SRR_TMS_Dia IS NOT NULL
            THEN
                b.Mineral_Chancado_TMS_Ajustado
                - b.Sal_Dia
                - b.SRR_TMS_Dia
            ELSE NULL
        END AS Chancado_TMS_Ajustado,

        b.Apilado_TMH_Neto_Ajustado,
        b.Apilado_TMS_Neto_Ajustado,

        b.Cantidad_Registros_Originales,
        b.Cantidad_Registros_Validos,
        b.Cantidad_Duplicados_Eliminados,

        b.Check_TMH_Bruto,
        b.Check_Produccion_Flotas,

        CAST('BALANCE_INVENTARIO_CAMIONES_V2' AS varchar(100))
            AS Metodo,

        CAST('MOV_CAM_DEDUP_OPERACIONAL' AS varchar(100))
            AS Fuente_Camiones,

        @FechaCalculo AS Fecha_Calculo

    INTO #FuenteFactorV2

    FROM BalanceAjustado AS b;

    CREATE UNIQUE CLUSTERED INDEX IX_FuenteFactorV2_Fecha
        ON #FuenteFactorV2(Fecha);


    /* ============================================================
       4. Persistencia en tabla V2
       ============================================================ */

    MERGE
        [inventar_SpcHidr].[Control_Factor_Ajuste_Camiones_v2_test]
        WITH (HOLDLOCK) AS tgt

    USING #FuenteFactorV2 AS src
        ON tgt.Fecha = src.Fecha

    WHEN MATCHED THEN
        UPDATE SET
            Limite_KOM_TMH_Viaje =
                src.Limite_KOM_TMH_Viaje,

            Limite_CAT_TMH_Viaje =
                src.Limite_CAT_TMH_Viaje,

            Apilado_TMH_Bruto_Original =
                src.Apilado_TMH_Bruto_Original,

            Apilado_TMH_Neto_Original =
                src.Apilado_TMH_Neto_Original,

            Sal_TMH_Dia =
                src.Sal_TMH_Dia,

            Humedad_Pct =
                src.Humedad_Pct,

            Apilado_TMS_Bruto_Sin_Ajuste =
                src.Apilado_TMS_Bruto_Sin_Ajuste,

            Apilado_TMS_Neto_Sin_Ajuste =
                src.Apilado_TMS_Neto_Sin_Ajuste,

            Inventario_Chancado_TMS_Actual =
                src.Inventario_Chancado_TMS_Actual,

            Inventario_Chancado_TMS_Anterior =
                src.Inventario_Chancado_TMS_Anterior,

            Delta_Inventario_Chancado_TMS =
                src.Delta_Inventario_Chancado_TMS,

            Flag_Continuidad_Diaria =
                src.Flag_Continuidad_Diaria,

            Flag_Inventario_Valido =
                src.Flag_Inventario_Valido,

            Flag_Humedad_Valida =
                src.Flag_Humedad_Valida,

            SRR_TMS_Turno_A =
                src.SRR_TMS_Turno_A,

            SRR_TMS_Turno_B =
                src.SRR_TMS_Turno_B,

            SRR_TMS_Dia =
                src.SRR_TMS_Dia,

            Mineral_Chancado_TMS_Sin_Ajuste =
                src.Mineral_Chancado_TMS_Sin_Ajuste,

            Chancado_TMS_Sin_Ajuste =
                src.Chancado_TMS_Sin_Ajuste,

            Chancado_TMH_Sin_Ajuste =
                src.Chancado_TMH_Sin_Ajuste,

            Produccion_KOM_TMH =
                src.Produccion_KOM_TMH,

            Produccion_CAT_TMH =
                src.Produccion_CAT_TMH,

            Dato_Mina_TMH =
                src.Dato_Mina_TMH,

            Vueltas_KOM =
                src.Vueltas_KOM,

            Vueltas_CAT =
                src.Vueltas_CAT,

            Participacion_KOM =
                src.Participacion_KOM,

            Participacion_CAT =
                src.Participacion_CAT,

            Chancado_KOM_TMH_Sin_Ajuste =
                src.Chancado_KOM_TMH_Sin_Ajuste,

            Chancado_CAT_TMH_Sin_Ajuste =
                src.Chancado_CAT_TMH_Sin_Ajuste,

            Carga_KOM_TMH_Viaje_Sin_Ajuste =
                src.Carga_KOM_TMH_Viaje_Sin_Ajuste,

            Carga_CAT_TMH_Viaje_Sin_Ajuste =
                src.Carga_CAT_TMH_Viaje_Sin_Ajuste,

            KOM_TMH_Corregido =
                src.KOM_TMH_Corregido,

            CAT_TMH_Corregido =
                src.CAT_TMH_Corregido,

            Chancado_TMH_Corregido_Total =
                src.Chancado_TMH_Corregido_Total,

            Factor_Ajuste =
                src.Factor_Ajuste,

            Flag_Factor_Ajuste_Valido =
                src.Flag_Factor_Ajuste_Valido,

            Estado_Calculo =
                src.Estado_Calculo,

            Apilado_TMH_Bruto_Ajustado =
                src.Apilado_TMH_Bruto_Ajustado,

            Apilado_TMS_Bruto_Ajustado =
                src.Apilado_TMS_Bruto_Ajustado,

            Mineral_Chancado_TMS_Ajustado =
                src.Mineral_Chancado_TMS_Ajustado,

            Chancado_TMS_Ajustado =
                src.Chancado_TMS_Ajustado,

            Apilado_TMH_Neto_Ajustado =
                src.Apilado_TMH_Neto_Ajustado,

            Apilado_TMS_Neto_Ajustado =
                src.Apilado_TMS_Neto_Ajustado,

            Cantidad_Registros_Originales =
                src.Cantidad_Registros_Originales,

            Cantidad_Registros_Validos =
                src.Cantidad_Registros_Validos,

            Cantidad_Duplicados_Eliminados =
                src.Cantidad_Duplicados_Eliminados,

            Check_TMH_Bruto =
                src.Check_TMH_Bruto,

            Check_Produccion_Flotas =
                src.Check_Produccion_Flotas,

            Metodo =
                src.Metodo,

            Fuente_Camiones =
                src.Fuente_Camiones,

            Fecha_Calculo =
                src.Fecha_Calculo

    WHEN NOT MATCHED BY TARGET THEN
        INSERT
        (
            Fecha,

            Limite_KOM_TMH_Viaje,
            Limite_CAT_TMH_Viaje,

            Apilado_TMH_Bruto_Original,
            Apilado_TMH_Neto_Original,
            Sal_TMH_Dia,
            Humedad_Pct,

            Apilado_TMS_Bruto_Sin_Ajuste,
            Apilado_TMS_Neto_Sin_Ajuste,

            Inventario_Chancado_TMS_Actual,
            Inventario_Chancado_TMS_Anterior,
            Delta_Inventario_Chancado_TMS,

            Flag_Continuidad_Diaria,
            Flag_Inventario_Valido,
            Flag_Humedad_Valida,

            SRR_TMS_Turno_A,
            SRR_TMS_Turno_B,
            SRR_TMS_Dia,

            Mineral_Chancado_TMS_Sin_Ajuste,
            Chancado_TMS_Sin_Ajuste,
            Chancado_TMH_Sin_Ajuste,

            Produccion_KOM_TMH,
            Produccion_CAT_TMH,
            Dato_Mina_TMH,

            Vueltas_KOM,
            Vueltas_CAT,

            Participacion_KOM,
            Participacion_CAT,

            Chancado_KOM_TMH_Sin_Ajuste,
            Chancado_CAT_TMH_Sin_Ajuste,

            Carga_KOM_TMH_Viaje_Sin_Ajuste,
            Carga_CAT_TMH_Viaje_Sin_Ajuste,

            KOM_TMH_Corregido,
            CAT_TMH_Corregido,
            Chancado_TMH_Corregido_Total,

            Factor_Ajuste,
            Flag_Factor_Ajuste_Valido,
            Estado_Calculo,

            Apilado_TMH_Bruto_Ajustado,
            Apilado_TMS_Bruto_Ajustado,

            Mineral_Chancado_TMS_Ajustado,
            Chancado_TMS_Ajustado,

            Apilado_TMH_Neto_Ajustado,
            Apilado_TMS_Neto_Ajustado,

            Cantidad_Registros_Originales,
            Cantidad_Registros_Validos,
            Cantidad_Duplicados_Eliminados,

            Check_TMH_Bruto,
            Check_Produccion_Flotas,

            Metodo,
            Fuente_Camiones,
            Fecha_Calculo
        )
        VALUES
        (
            src.Fecha,

            src.Limite_KOM_TMH_Viaje,
            src.Limite_CAT_TMH_Viaje,

            src.Apilado_TMH_Bruto_Original,
            src.Apilado_TMH_Neto_Original,
            src.Sal_TMH_Dia,
            src.Humedad_Pct,

            src.Apilado_TMS_Bruto_Sin_Ajuste,
            src.Apilado_TMS_Neto_Sin_Ajuste,

            src.Inventario_Chancado_TMS_Actual,
            src.Inventario_Chancado_TMS_Anterior,
            src.Delta_Inventario_Chancado_TMS,

            src.Flag_Continuidad_Diaria,
            src.Flag_Inventario_Valido,
            src.Flag_Humedad_Valida,

            src.SRR_TMS_Turno_A,
            src.SRR_TMS_Turno_B,
            src.SRR_TMS_Dia,

            src.Mineral_Chancado_TMS_Sin_Ajuste,
            src.Chancado_TMS_Sin_Ajuste,
            src.Chancado_TMH_Sin_Ajuste,

            src.Produccion_KOM_TMH,
            src.Produccion_CAT_TMH,
            src.Dato_Mina_TMH,

            src.Vueltas_KOM,
            src.Vueltas_CAT,

            src.Participacion_KOM,
            src.Participacion_CAT,

            src.Chancado_KOM_TMH_Sin_Ajuste,
            src.Chancado_CAT_TMH_Sin_Ajuste,

            src.Carga_KOM_TMH_Viaje_Sin_Ajuste,
            src.Carga_CAT_TMH_Viaje_Sin_Ajuste,

            src.KOM_TMH_Corregido,
            src.CAT_TMH_Corregido,
            src.Chancado_TMH_Corregido_Total,

            src.Factor_Ajuste,
            src.Flag_Factor_Ajuste_Valido,
            src.Estado_Calculo,

            src.Apilado_TMH_Bruto_Ajustado,
            src.Apilado_TMS_Bruto_Ajustado,

            src.Mineral_Chancado_TMS_Ajustado,
            src.Chancado_TMS_Ajustado,

            src.Apilado_TMH_Neto_Ajustado,
            src.Apilado_TMS_Neto_Ajustado,

            src.Cantidad_Registros_Originales,
            src.Cantidad_Registros_Validos,
            src.Cantidad_Duplicados_Eliminados,

            src.Check_TMH_Bruto,
            src.Check_Produccion_Flotas,

            src.Metodo,
            src.Fuente_Camiones,
            src.Fecha_Calculo
        );

    DECLARE @FilasAfectadas int = @@ROWCOUNT;

    PRINT 'Proceso V2 finalizado.';
    PRINT 'Rango procesado: '
        + CONVERT(varchar(10), @FechaInicioProceso, 120)
        + ' a '
        + CONVERT(varchar(10), @FechaFin, 120);

    PRINT 'Filas insertadas/actualizadas: '
        + CONVERT(varchar(20), @FilasAfectadas);
END;
GO

-- ============================================================================
-- inventar_SpcHidr.sp_refrescar_historico_apilado_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-07-23 16:03:32.820000
-- ============================================================================
/* -----------------------------------------------------------
   SECCION B: sp_refrescar_historico_apilado_test sin el PASO 0
   (resumen/purga ahora son pasos independientes 1 y 2)
----------------------------------------------------------- */
CREATE   PROCEDURE [inventar_SpcHidr].[sp_refrescar_historico_apilado_test]
(
    @FechaInicio    date,
    @FechaFin       date,
    @DiasReproceso  int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'Debe informar @FechaInicio y @FechaFin.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50002, 'La fecha inicial no puede ser mayor que la fecha final.', 1;

    DECLARE @FechaLimiteReproceso date = DATEADD(DAY, -@DiasReproceso, @FechaFin);
    DECLARE @FechaInicioBorrado date =
        CASE WHEN @FechaLimiteReproceso < @FechaInicio THEN @FechaLimiteReproceso ELSE @FechaInicio END;

    DELETE FROM [inventar_SpcHidr].[Historico_Apilado_Diario]
    WHERE Fecha BETWEEN @FechaInicioBorrado AND @FechaFin;

    INSERT INTO [inventar_SpcHidr].[Historico_Apilado_Diario]
    (
        Fecha, Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia,
        Sal_turno_A, Sal_Turno_B, Sal_promedio_dia,
        Apilado_TMH_turno_A, Apilado_TMH_turno_B, Apilado_TMH_promedio_dia,
        Apilado_TMS_Real, Apilado_TMS_turno_A_Recalculado, Apilado_TMS_turno_B_Recalculado,
        Factor_Ajuste_Camiones,
        TMH_Bruto_A, TMH_Bruto_B, TMH_Bruto_Dia,
        Sal_Pesometros_TA, Sal_Pesometros_TB, Sal_Pesometros_Dia, Sal_Topografia_Dia,
        Sal_Ajustada_Dia,
        Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido,
        Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS,
        Check_Sal_Dia, Check_TMH_Dia, Check_TMS_Dia,
        Check_TMS_A_Fuente, Check_TMS_B_Fuente, Check_TMS_Dia_Fuente,
        Fecha_Calculo
    )
    SELECT
        v.Fecha, v.Humedad_Turno_A, v.Humedad_Turno_B, v.Humedad_promedio_dia,
        v.Sal_turno_A, v.Sal_Turno_B, v.Sal_promedio_dia,
        v.Apilado_TMH_turno_A, v.Apilado_TMH_turno_B, v.Apilado_TMH_promedio_dia,
        v.Apilado_TMS_Real, v.Apilado_TMS_turno_A_Recalculado, v.Apilado_TMS_turno_B_Recalculado,
        v.Factor_Ajuste_Camiones,
        v.TMH_Bruto_A, v.TMH_Bruto_B, v.TMH_Bruto_Dia,
        v.Sal_Pesometros_TA, v.Sal_Pesometros_TB, v.Sal_Pesometros_Dia, v.Sal_Topografia_Dia,
        v.Sal_Ajustada_Dia,
        v.Flag_Sal_Basica_Valida, v.Flag_Sal_Ajuste_Valido,
        v.Flag_Apilado_Valido, v.Flag_TMS_Valido, v.Observacion_TMS,
        v.Check_Sal_Dia, v.Check_TMH_Dia, v.Check_TMS_Dia,
        v.Check_TMS_A_Fuente, v.Check_TMS_B_Fuente, v.Check_TMS_Dia_Fuente,
        SYSDATETIME()
    FROM [inventar_SpcHidr].[v_reporte_diario_apilado_test] v
    WHERE v.Fecha BETWEEN @FechaInicioBorrado AND @FechaFin
      AND NOT EXISTS
      (
          SELECT 1
          FROM [inventar_SpcHidr].[Historico_Apilado_Diario] h
          WHERE h.Fecha = v.Fecha
      );

    PRINT '-- Historico_Apilado_Diario refrescado: '
        + CONVERT(varchar, @FechaInicioBorrado) + ' a ' + CONVERT(varchar, @FechaFin)
        + ' (ventana de reproceso desde ' + CONVERT(varchar, @FechaLimiteReproceso) + ')';
END;
GO

-- ============================================================================
-- inventar_SpcHidr.v_ajuste_camiones_emision_test (VIEW)
-- Ultima modificacion: 2026-07-31 01:39:53.870000
-- ============================================================================

CREATE   VIEW
    [inventar_SpcHidr].[v_ajuste_camiones_emision_test]
AS
SELECT
    f.Fecha,

    /* ============================================================
       Factor real calculado
       ============================================================ */
    f.Factor_Ajuste
        AS Factor_Ajuste_Calculado,

    f.Flag_Factor_Ajuste_Valido,
    f.Estado_Calculo,

    /* ============================================================
       Control de aplicación
       Solo vale 1 cuando existe un cálculo completo y utilizable.
       ============================================================ */
    CAST
    (
        CASE
            WHEN f.Flag_Factor_Ajuste_Valido = 1
             AND f.Factor_Ajuste IS NOT NULL
             AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
             AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
             AND f.Chancado_TMS_Ajustado IS NOT NULL
                THEN 1
            ELSE 0
        END
        AS bit
    ) AS Flag_Usa_Ajuste,

    /* ============================================================
       Factor operativo para aplicar en los reportes

       Importante:
       - No reemplaza al factor real.
       - Cuando el cálculo no es evaluable, usa 1 solo para mantener
         el valor basal en la salida diaria.
       ============================================================ */
    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Factor_Ajuste IS NOT NULL
            THEN f.Factor_Ajuste
        ELSE 1.0
    END AS Factor_Aplicacion_Reportes,

    /* ============================================================
       Valores originales
       ============================================================ */
    f.Apilado_TMH_Bruto_Original,
    f.Apilado_TMH_Neto_Original,

    f.Apilado_TMS_Bruto_Sin_Ajuste,
    f.Apilado_TMS_Neto_Sin_Ajuste,

    f.Chancado_TMS_Sin_Ajuste,
    f.Chancado_TMH_Sin_Ajuste,

    /* ============================================================
       Valores ajustados calculados
       ============================================================ */
    f.Apilado_TMH_Bruto_Ajustado,
    f.Apilado_TMH_Neto_Ajustado,

    f.Apilado_TMS_Bruto_Ajustado,
    f.Apilado_TMS_Neto_Ajustado,

    f.Chancado_TMS_Ajustado,

    /* ============================================================
       Valores efectivos para Datos Conciliados y Análisis TM
       ============================================================ */
    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
            THEN f.Apilado_TMH_Neto_Ajustado
        ELSE f.Apilado_TMH_Neto_Original
    END AS Apilado_TMH_Reporte,

    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
            THEN f.Apilado_TMS_Neto_Ajustado
        ELSE f.Apilado_TMS_Neto_Sin_Ajuste
    END AS Apilado_TMS_Reporte,

    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Chancado_TMS_Ajustado IS NOT NULL
            THEN f.Chancado_TMS_Ajustado
        ELSE f.Chancado_TMS_Sin_Ajuste
    END AS Chancado_TMS_Reporte,

    /* ============================================================
       Diferencias introducidas por el ajuste
       ============================================================ */
    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
            THEN
                f.Apilado_TMH_Neto_Ajustado
                - f.Apilado_TMH_Neto_Original
        ELSE 0.0
    END AS Diferencia_Apilado_TMH_Ajuste,

    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
            THEN
                f.Apilado_TMS_Neto_Ajustado
                - f.Apilado_TMS_Neto_Sin_Ajuste
        ELSE 0.0
    END AS Diferencia_Apilado_TMS_Ajuste,

    CASE
        WHEN f.Flag_Factor_Ajuste_Valido = 1
         AND f.Chancado_TMS_Ajustado IS NOT NULL
            THEN
                f.Chancado_TMS_Ajustado
                - f.Chancado_TMS_Sin_Ajuste
        ELSE 0.0
    END AS Diferencia_Chancado_TMS_Ajuste,

    /* ============================================================
       Descripción de la regla aplicada
       ============================================================ */
    CAST
    (
        CASE
            WHEN f.Flag_Factor_Ajuste_Valido = 1
             AND f.Factor_Ajuste IS NOT NULL
             AND f.Apilado_TMH_Neto_Ajustado IS NOT NULL
             AND f.Apilado_TMS_Neto_Ajustado IS NOT NULL
             AND f.Chancado_TMS_Ajustado IS NOT NULL
                THEN 'APLICA_AJUSTE_VALIDADO'

            WHEN f.Estado_Calculo = 'SIN_DATOS_CAMIONES'
                THEN 'FALLBACK_SIN_DATOS_CAMIONES'

            WHEN f.Flag_Factor_Ajuste_Valido = 0
                THEN CONCAT(
                    'FALLBACK_',
                    COALESCE(f.Estado_Calculo, 'NO_EVALUABLE')
                )

            ELSE 'FALLBACK_INCONSISTENCIA_CALCULO'
        END
        AS varchar(80)
    ) AS Regla_Aplicacion,

    /* ============================================================
       Trazabilidad complementaria
       ============================================================ */
    f.Sal_TMH_Dia,
    f.Humedad_Pct,

    f.Inventario_Chancado_TMS_Actual,
    f.Inventario_Chancado_TMS_Anterior,
    f.Delta_Inventario_Chancado_TMS,

    f.SRR_TMS_Turno_A,
    f.SRR_TMS_Turno_B,
    f.SRR_TMS_Dia,

    f.Produccion_KOM_TMH,
    f.Produccion_CAT_TMH,

    f.Vueltas_KOM,
    f.Vueltas_CAT,

    f.Carga_KOM_TMH_Viaje_Sin_Ajuste,
    f.Carga_CAT_TMH_Viaje_Sin_Ajuste,

    f.KOM_TMH_Corregido,
    f.CAT_TMH_Corregido,

    f.Cantidad_Registros_Originales,
    f.Cantidad_Registros_Validos,
    f.Cantidad_Duplicados_Eliminados,

    f.Metodo,
    f.Fuente_Camiones,
    f.Fecha_Calculo

FROM
    [inventar_SpcHidr].[Control_Factor_Ajuste_Camiones_v2_test] AS f;
GO

-- ============================================================================
-- inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test (VIEW)
-- Ultima modificacion: 2026-07-24 19:06:44.817000
-- ============================================================================

CREATE   VIEW
    [inventar_SpcHidr].[v_apilado_tms_con_sal_srr_reporte_test]
AS

WITH fechas AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        TMH_CV008_A,
        TMH_CV008_B,
        TMH_CV108_A,
        TMH_CV108_B,

        TMH_CV008_A + TMH_CV108_A
            AS TMH_Apilado_Total_A,

        TMH_CV008_B + TMH_CV108_B
            AS TMH_Apilado_Total_B,

        TMH_CV008_A
      + TMH_CV008_B
      + TMH_CV108_A
      + TMH_CV108_B
            AS TMH_Apilado_Total_Dia

    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2
),

/* ============================================================
   HUMEDAD INFORMADA POR LABORATORIO
   ============================================================ */
hum AS
(
    SELECT
        CAST(Fecha AS date) AS Fecha,
        Torre,
        Turno,
        AVG(CAST(Humedad_Prom_Pct AS float))
            AS Humedad_Prom_Pct

    FROM inventar_SpcHidr.Informe_TM_lab

    WHERE Humedad_Prom_Pct IS NOT NULL

    GROUP BY
        CAST(Fecha AS date),
        Torre,
        Turno
),

/* ============================================================
   CRUCE CON REPRESENTATIVIDAD FÍSICA
   ============================================================ */
hum_rep AS
(
    SELECT
        h.Fecha,
        h.Torre,
        h.Turno,
        h.Humedad_Prom_Pct,

        CASE
            WHEN h.Torre = 'T1'
             AND h.Turno = 'A'
                THEN r.TM1_TurnoA_Fisico

            WHEN h.Torre = 'T1'
             AND h.Turno = 'B'
                THEN r.TM1_TurnoB_Fisico

            WHEN h.Torre = 'T2'
             AND h.Turno = 'A'
                THEN r.TM2_TurnoA_Fisico

            WHEN h.Torre = 'T2'
             AND h.Turno = 'B'
                THEN r.TM2_TurnoB_Fisico
        END AS Representatividad_Fisica

    FROM hum AS h

    LEFT JOIN inventar_SpcHidr.v_representatividad_diaria_calculada AS r
        ON r.Dia = h.Fecha
),

/* ============================================================
   HUMEDADES REPRESENTATIVAS

   Se mantiene la granularidad Fecha + Turno.
   ============================================================ */
hum_validas AS
(
    SELECT
        Fecha,
        Torre,
        Turno,
        Humedad_Prom_Pct,
        Representatividad_Fisica,

        DATEADD
        (
            HOUR,
            CASE
                WHEN Turno = 'A' THEN 8
                ELSE 20
            END,
            CAST(Fecha AS datetime2(0))
        ) AS FechaTurno_Origen

    FROM hum_rep

    WHERE Humedad_Prom_Pct IS NOT NULL
      AND Representatividad_Fisica >= 0.75
),

/* ============================================================
   PERIODOS A/B A RESOLVER
   ============================================================ */
periodos AS
(
    SELECT
        f.Fecha,
        t.Turno_Objetivo,

        DATEADD
        (
            HOUR,
            CASE
                WHEN t.Turno_Objetivo = 'A' THEN 8
                ELSE 20
            END,
            CAST(f.Fecha AS datetime2(0))
        ) AS FechaTurno_Objetivo

    FROM fechas AS f

    CROSS JOIN
    (
        VALUES
            ('A'),
            ('B')
    ) AS t(Turno_Objetivo)
),

/* ============================================================
   RESOLUCIÓN CRONOLÓGICA POR FECHA + TURNO

   Regla de humedad:
   - Cada TM prioriza su dato propio.
   - Si no existe dato propio representativo, puede utilizar
     la humedad representativa de la otra torre.
   - El último valor válido se arrastra cronológicamente.
   ============================================================ */
resuelta_turno AS
(
    SELECT
        p.Fecha,
        p.Turno_Objetivo,

        /* ----------------------------------------------------
           TM1
           ---------------------------------------------------- */
        tm1.Humedad_Prom_Pct
            AS Humedad_TM1,

        tm1.Fecha
            AS Fecha_Origen_TM1,

        tm1.Torre
            AS Torre_Origen_TM1,

        tm1.Turno
            AS Turno_Origen_TM1,

        tm1.Fuente_Humedad
            AS Fuente_Humedad_TM1,

        /* ----------------------------------------------------
           TM2
           ---------------------------------------------------- */
        tm2.Humedad_Prom_Pct
            AS Humedad_TM2,

        tm2.Fecha
            AS Fecha_Origen_TM2,

        tm2.Torre
            AS Torre_Origen_TM2,

        tm2.Turno
            AS Turno_Origen_TM2,

        tm2.Fuente_Humedad
            AS Fuente_Humedad_TM2

    FROM periodos AS p

    /* ========================================================
       TM1: propia T1 o compartida desde T2
       ======================================================== */
    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno,
            c.Humedad_Prom_Pct,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno,
                h.Humedad_Prom_Pct,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T1'
                            THEN 'PROPIA_TM1'
                        ELSE 'COMPARTIDA_DESDE_TM2'
                    END
                    AS varchar(23)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T1' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM hum_validas AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(10)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'HUMEDAD_INICIAL_PERIODO'
                    AS varchar(23)
                ),

                3

            FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s

            WHERE s.tm = 'TM1'
              AND CAST(s.fecha_origen AS datetime2(0))
                    <= p.FechaTurno_Objetivo
        ) AS c

        ORDER BY
            c.FechaTurno_Origen DESC,
            c.Prioridad ASC
    ) AS tm1

    /* ========================================================
       TM2: propia T2 o compartida desde T1
       ======================================================== */
    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno,
            c.Humedad_Prom_Pct,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno,
                h.Humedad_Prom_Pct,
                h.FechaTurno_Origen,

                CAST
                (
                    CASE
                        WHEN h.Torre = 'T2'
                            THEN 'PROPIA_TM2'
                        ELSE 'COMPARTIDA_DESDE_TM1'
                    END
                    AS varchar(23)
                ) AS Fuente_Humedad,

                CASE
                    WHEN h.Torre = 'T2' THEN 1
                    ELSE 2
                END AS Prioridad

            FROM hum_validas AS h

            WHERE h.FechaTurno_Origen
                    <= p.FechaTurno_Objetivo
              AND h.Torre IN ('T1', 'T2')

            UNION ALL

            SELECT
                CAST(s.fecha_origen AS date),
                CAST(s.torre AS varchar(20)),
                CAST(NULL AS varchar(10)),
                CAST(s.humedad_pct AS float),
                CAST(s.fecha_origen AS datetime2(0)),

                CAST
                (
                    'HUMEDAD_INICIAL_PERIODO'
                    AS varchar(23)
                ),

                3

            FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s

            WHERE s.tm = 'TM2'
              AND CAST(s.fecha_origen AS datetime2(0))
                    <= p.FechaTurno_Objetivo
        ) AS c

        ORDER BY
            c.FechaTurno_Origen DESC,
            c.Prioridad ASC
    ) AS tm2
),

/* ============================================================
   PIVOT A/B A UNA FILA DIARIA

   Humedad_TM1 y Humedad_TM2 mantienen compatibilidad:
   representan el valor vigente al cierre del día.
   ============================================================ */
humedad_resuelta AS
(
    SELECT
        f.*,

        /* Humedades internas por turno */
        a.Humedad_TM1 AS Humedad_TM1_A,
        b.Humedad_TM1 AS Humedad_TM1_B,

        a.Humedad_TM2 AS Humedad_TM2_A,
        b.Humedad_TM2 AS Humedad_TM2_B,

        /* Columnas existentes: valor vigente al cierre del día */
        COALESCE
        (
            b.Humedad_TM1,
            a.Humedad_TM1
        ) AS Humedad_TM1,

        COALESCE
        (
            b.Humedad_TM2,
            a.Humedad_TM2
        ) AS Humedad_TM2,

        /* Trazabilidad existente: origen vigente al cierre */
        COALESCE
        (
            b.Fecha_Origen_TM1,
            a.Fecha_Origen_TM1
        ) AS Fecha_Humedad_TM1,

        COALESCE
        (
            b.Torre_Origen_TM1,
            a.Torre_Origen_TM1
        ) AS Torre_Humedad_TM1,

        COALESCE
        (
            b.Turno_Origen_TM1,
            a.Turno_Origen_TM1
        ) AS Turno_Humedad_TM1,

        COALESCE
        (
            b.Fuente_Humedad_TM1,
            a.Fuente_Humedad_TM1
        ) AS Fuente_Humedad_TM1,

        COALESCE
        (
            b.Fecha_Origen_TM2,
            a.Fecha_Origen_TM2
        ) AS Fecha_Humedad_TM2,

        COALESCE
        (
            b.Torre_Origen_TM2,
            a.Torre_Origen_TM2
        ) AS Torre_Humedad_TM2,

        COALESCE
        (
            b.Turno_Origen_TM2,
            a.Turno_Origen_TM2
        ) AS Turno_Humedad_TM2,

        COALESCE
        (
            b.Fuente_Humedad_TM2,
            a.Fuente_Humedad_TM2
        ) AS Fuente_Humedad_TM2

    FROM fechas AS f

    LEFT JOIN resuelta_turno AS a
        ON a.Fecha = f.Fecha
       AND a.Turno_Objetivo = 'A'

    LEFT JOIN resuelta_turno AS b
        ON b.Fecha = f.Fecha
       AND b.Turno_Objetivo = 'B'
),

/* ============================================================
   FACTOR DE AJUSTE
   ============================================================ */
base AS
(
    SELECT
        h.*,

        COALESCE
        (
            fac.factor_ajuste,
            1.0
        ) AS Factor_Ajuste_Camiones_Usado,

        h.TMH_Apilado_Total_A
        * COALESCE(fac.factor_ajuste, 1.0)
            AS TMH_Apilado_Total_A_Factor,

        h.TMH_Apilado_Total_B
        * COALESCE(fac.factor_ajuste, 1.0)
            AS TMH_Apilado_Total_B_Factor,

        h.TMH_Apilado_Total_Dia
        * COALESCE(fac.factor_ajuste, 1.0)
            AS TMH_Apilado_Total_Dia_Factor

    FROM humedad_resuelta AS h

    OUTER APPLY
    (
        SELECT TOP (1)
            f.factor_ajuste

        FROM inventar_SpcHidr.factor_ajuste_camiones AS f

        WHERE f.activo = 1
          AND h.Fecha >= f.fecha_inicio
          AND
          (
              f.fecha_fin IS NULL
              OR h.Fecha <= f.fecha_fin
          )

        ORDER BY
            f.fecha_inicio DESC,
            f.id_factor DESC
    ) AS fac
),

/* ============================================================
   CÁLCULO DE TMS POR TURNO
   ============================================================ */
tms AS
(
    SELECT
        b.*,

        CASE
            WHEN b.TMH_CV008_A = 0
                THEN 0

            WHEN b.Humedad_TM1_A IS NULL
                THEN NULL

            ELSE
                b.TMH_CV008_A
                * (1 - b.Humedad_TM1_A / 100.0)
        END AS TMS_CV008_A,

        CASE
            WHEN b.TMH_CV008_B = 0
                THEN 0

            WHEN b.Humedad_TM1_B IS NULL
                THEN NULL

            ELSE
                b.TMH_CV008_B
                * (1 - b.Humedad_TM1_B / 100.0)
        END AS TMS_CV008_B,

        CASE
            WHEN b.TMH_CV108_A = 0
                THEN 0

            WHEN b.Humedad_TM2_A IS NULL
                THEN NULL

            ELSE
                b.TMH_CV108_A
                * (1 - b.Humedad_TM2_A / 100.0)
        END AS TMS_CV108_A,

        CASE
            WHEN b.TMH_CV108_B = 0
                THEN 0

            WHEN b.Humedad_TM2_B IS NULL
                THEN NULL

            ELSE
                b.TMH_CV108_B
                * (1 - b.Humedad_TM2_B / 100.0)
        END AS TMS_CV108_B

    FROM base AS b
)

SELECT
    Fecha,
    Flag_Apilado_Valido,
    Factor_Ajuste_Camiones_Usado,

    /* Humedad vigente al cierre del día */
    Humedad_TM1,
    Humedad_TM2,

    /* Humedad equivalente ponderada real del día */
    CASE
        WHEN TMH_Apilado_Total_Dia = 0
            THEN 0

        WHEN TMH_CV008_A > 0
         AND Humedad_TM1_A IS NULL
            THEN NULL

        WHEN TMH_CV008_B > 0
         AND Humedad_TM1_B IS NULL
            THEN NULL

        WHEN TMH_CV108_A > 0
         AND Humedad_TM2_A IS NULL
            THEN NULL

        WHEN TMH_CV108_B > 0
         AND Humedad_TM2_B IS NULL
            THEN NULL

        ELSE
            (
                  TMH_CV008_A * Humedad_TM1_A
                + TMH_CV008_B * Humedad_TM1_B
                + TMH_CV108_A * Humedad_TM2_A
                + TMH_CV108_B * Humedad_TM2_B
            )
            /
            NULLIF
            (
                TMH_Apilado_Total_Dia,
                0
            )
    END AS Humedad_Equivalente_Dia,

    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,

    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2,

    TMH_CV008_A AS TMH_TM1_Con_Sal_SRR_A,
    TMH_CV008_B AS TMH_TM1_Con_Sal_SRR_B,
    TMH_CV108_A AS TMH_TM2_Con_Sal_SRR_A,
    TMH_CV108_B AS TMH_TM2_Con_Sal_SRR_B,

    TMH_Apilado_Total_A
        AS TMH_Total_Con_Sal_SRR_A,

    TMH_Apilado_Total_B
        AS TMH_Total_Con_Sal_SRR_B,

    TMH_Apilado_Total_Dia
        AS TMH_Total_Con_Sal_SRR_Dia,

    TMH_Apilado_Total_A_Factor
        AS TMH_Total_Con_Factor_A,

    TMH_Apilado_Total_B_Factor
        AS TMH_Total_Con_Factor_B,

    TMH_Apilado_Total_Dia_Factor
        AS TMH_Total_Con_Factor_Dia,

    TMH_Apilado_Total_A_Factor
      - TMH_Apilado_Total_A
        AS Check_Factor_TMH_A,

    TMH_Apilado_Total_B_Factor
      - TMH_Apilado_Total_B
        AS Check_Factor_TMH_B,

    TMH_Apilado_Total_Dia_Factor
      - TMH_Apilado_Total_Dia
        AS Check_Factor_TMH_Dia,

    TMS_CV008_A AS TMS_TM1_Con_Sal_SRR_A,
    TMS_CV008_B AS TMS_TM1_Con_Sal_SRR_B,
    TMS_CV108_A AS TMS_TM2_Con_Sal_SRR_A,
    TMS_CV108_B AS TMS_TM2_Con_Sal_SRR_B,

    CASE
        WHEN TMS_CV008_A IS NULL
          OR TMS_CV108_A IS NULL
            THEN NULL

        ELSE TMS_CV008_A + TMS_CV108_A
    END AS TMS_Total_Con_Sal_SRR_A,

    CASE
        WHEN TMS_CV008_B IS NULL
          OR TMS_CV108_B IS NULL
            THEN NULL

        ELSE TMS_CV008_B + TMS_CV108_B
    END AS TMS_Total_Con_Sal_SRR_B,

    CASE
        WHEN TMS_CV008_A IS NULL
          OR TMS_CV008_B IS NULL
          OR TMS_CV108_A IS NULL
          OR TMS_CV108_B IS NULL
            THEN NULL

        ELSE
              TMS_CV008_A
            + TMS_CV008_B
            + TMS_CV108_A
            + TMS_CV108_B
    END AS TMS_Total_Con_Sal_SRR_Dia,

    CASE
        WHEN Flag_Apilado_Valido = 0
            THEN 0

        WHEN TMH_CV008_A > 0
         AND Humedad_TM1_A IS NULL
            THEN 0

        WHEN TMH_CV008_B > 0
         AND Humedad_TM1_B IS NULL
            THEN 0

        WHEN TMH_CV108_A > 0
         AND Humedad_TM2_A IS NULL
            THEN 0

        WHEN TMH_CV108_B > 0
         AND Humedad_TM2_B IS NULL
            THEN 0

        ELSE 1
    END AS Flag_TMS_Valido,

    CASE
        WHEN Flag_Apilado_Valido = 0
            THEN 'APILADO_TMH_INVALIDO_O_CERO'

        WHEN TMH_CV008_A > 0
         AND Humedad_TM1_A IS NULL
            THEN 'SIN_HUMEDAD_REPRESENTATIVA_TM1'

        WHEN TMH_CV008_B > 0
         AND Humedad_TM1_B IS NULL
            THEN 'SIN_HUMEDAD_REPRESENTATIVA_TM1'

        WHEN TMH_CV108_A > 0
         AND Humedad_TM2_A IS NULL
            THEN 'SIN_HUMEDAD_REPRESENTATIVA_TM2'

        WHEN TMH_CV108_B > 0
         AND Humedad_TM2_B IS NULL
            THEN 'SIN_HUMEDAD_REPRESENTATIVA_TM2'

        ELSE 'TMS_VALIDO_SEGUN_REGLA_PROVISIONAL'
    END AS Observacion_TMS

FROM tms;
GO

-- ============================================================================
-- inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test (VIEW)
-- Ultima modificacion: 2026-07-29 13:31:05.657000
-- ============================================================================

CREATE   VIEW
[inventar_SpcHidr].[v_apilado_tms_sin_sal_con_srr_reporte_test]
AS
WITH base AS (SELECT t.Fecha, t.Flag_Apilado_Valido, t.Flag_TMS_Valido, t.Observacion_TMS, t.Factor_Ajuste_Camiones_Usado, t.Humedad_TM1, t.Humedad_TM2, t.Humedad_Equivalente_Dia, t.Fecha_Humedad_TM1, t.Torre_Humedad_TM1, t.Turno_Humedad_TM1, 
                                     t.Fuente_Humedad_TM1, t.Fecha_Humedad_TM2, t.Torre_Humedad_TM2, t.Turno_Humedad_TM2, t.Fuente_Humedad_TM2, t.TMH_TM1_Con_Sal_SRR_A, t.TMH_TM1_Con_Sal_SRR_B, t.TMH_TM2_Con_Sal_SRR_A, t.TMH_TM2_Con_Sal_SRR_B, 
                                     t.TMH_Total_Con_Sal_SRR_A, t.TMH_Total_Con_Sal_SRR_B, t.TMH_Total_Con_Sal_SRR_Dia, t.TMS_TM1_Con_Sal_SRR_A, t.TMS_TM1_Con_Sal_SRR_B, t.TMS_TM2_Con_Sal_SRR_A, t.TMS_TM2_Con_Sal_SRR_B, t.TMS_Total_Con_Sal_SRR_A, 
                                     t.TMS_Total_Con_Sal_SRR_B, t.TMS_Total_Con_Sal_SRR_Dia, s.Sal_Pesometros_TA, s.Sal_Pesometros_TB, s.Sal_Pesometros_Dia, s.Sal_Topografia_Dia, s.Flag_Sal_Basica_Valida, s.Flag_Sal_Ajuste_Valido, s.Sal_Ajustada_TA, s.Sal_Ajustada_TB, 
                                     s.Sal_Ajustada_Dia, CASE WHEN t .TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL WHEN t .TMS_Total_Con_Sal_SRR_A = 0 THEN 0 ELSE COALESCE (s.Sal_Ajustada_TA, 0) * t .TMS_TM1_Con_Sal_SRR_A / NULLIF (t .TMS_Total_Con_Sal_SRR_A, 0) 
                                     END AS Sal_Asignada_TM1_A, CASE WHEN t .TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL WHEN t .TMS_Total_Con_Sal_SRR_A = 0 THEN 0 ELSE COALESCE (s.Sal_Ajustada_TA, 0) * t .TMS_TM2_Con_Sal_SRR_A / NULLIF (t .TMS_Total_Con_Sal_SRR_A, 0) 
                                     END AS Sal_Asignada_TM2_A, CASE WHEN t .TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL WHEN t .TMS_Total_Con_Sal_SRR_B = 0 THEN 0 ELSE COALESCE (s.Sal_Ajustada_TB, 0) * t .TMS_TM1_Con_Sal_SRR_B / NULLIF (t .TMS_Total_Con_Sal_SRR_B, 0) 
                                     END AS Sal_Asignada_TM1_B, CASE WHEN t .TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL WHEN t .TMS_Total_Con_Sal_SRR_B = 0 THEN 0 ELSE COALESCE (s.Sal_Ajustada_TB, 0) * t .TMS_TM2_Con_Sal_SRR_B / NULLIF (t .TMS_Total_Con_Sal_SRR_B, 0) 
                                     END AS Sal_Asignada_TM2_B
                        FROM    inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test AS t LEFT OUTER JOIN
                                     inventar_SpcHidr.v_sal_ajustada_operacional_test AS s ON s.Fecha = t.Fecha), tms_sin_sal AS
    (SELECT Fecha, Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS, Factor_Ajuste_Camiones_Usado, Humedad_TM1, Humedad_TM2, Humedad_Equivalente_Dia, Fecha_Humedad_TM1, Torre_Humedad_TM1, Turno_Humedad_TM1, Fuente_Humedad_TM1, Fecha_Humedad_TM2, 
                 Torre_Humedad_TM2, Turno_Humedad_TM2, Fuente_Humedad_TM2, TMH_TM1_Con_Sal_SRR_A, TMH_TM1_Con_Sal_SRR_B, TMH_TM2_Con_Sal_SRR_A, TMH_TM2_Con_Sal_SRR_B, TMH_Total_Con_Sal_SRR_A, TMH_Total_Con_Sal_SRR_B, TMH_Total_Con_Sal_SRR_Dia, 
                 TMS_TM1_Con_Sal_SRR_A, TMS_TM1_Con_Sal_SRR_B, TMS_TM2_Con_Sal_SRR_A, TMS_TM2_Con_Sal_SRR_B, TMS_Total_Con_Sal_SRR_A, TMS_Total_Con_Sal_SRR_B, TMS_Total_Con_Sal_SRR_Dia, Sal_Pesometros_TA, Sal_Pesometros_TB, Sal_Pesometros_Dia, 
                 Sal_Topografia_Dia, Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido, Sal_Ajustada_TA, Sal_Ajustada_TB, Sal_Ajustada_Dia, Sal_Asignada_TM1_A, Sal_Asignada_TM2_A, Sal_Asignada_TM1_B, Sal_Asignada_TM2_B, CASE WHEN b.TMS_TM1_Con_Sal_SRR_A IS NULL THEN NULL 
                 ELSE b.TMS_TM1_Con_Sal_SRR_A - COALESCE (b.Sal_Asignada_TM1_A, 0) END AS TMS_TM1_Sin_Sal_Con_SRR_A, CASE WHEN b.TMS_TM1_Con_Sal_SRR_B IS NULL THEN NULL ELSE b.TMS_TM1_Con_Sal_SRR_B - COALESCE (b.Sal_Asignada_TM1_B, 0) 
                 END AS TMS_TM1_Sin_Sal_Con_SRR_B, CASE WHEN b.TMS_TM2_Con_Sal_SRR_A IS NULL THEN NULL ELSE b.TMS_TM2_Con_Sal_SRR_A - COALESCE (b.Sal_Asignada_TM2_A, 0) END AS TMS_TM2_Sin_Sal_Con_SRR_A, CASE WHEN b.TMS_TM2_Con_Sal_SRR_B IS NULL 
                 THEN NULL ELSE b.TMS_TM2_Con_Sal_SRR_B - COALESCE (b.Sal_Asignada_TM2_B, 0) END AS TMS_TM2_Sin_Sal_Con_SRR_B
    FROM    base AS b)
    SELECT Fecha, Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS, Factor_Ajuste_Camiones_Usado, Humedad_TM1, Humedad_TM2, Humedad_Equivalente_Dia, Fecha_Humedad_TM1, Torre_Humedad_TM1, Turno_Humedad_TM1, Fuente_Humedad_TM1, Fecha_Humedad_TM2, 
                Torre_Humedad_TM2, Turno_Humedad_TM2, Fuente_Humedad_TM2, TMH_TM1_Con_Sal_SRR_A, TMH_TM1_Con_Sal_SRR_B, TMH_TM2_Con_Sal_SRR_A, TMH_TM2_Con_Sal_SRR_B, TMH_Total_Con_Sal_SRR_A, TMH_Total_Con_Sal_SRR_B, TMH_Total_Con_Sal_SRR_Dia, 
                TMS_TM1_Con_Sal_SRR_A, TMS_TM1_Con_Sal_SRR_B, TMS_TM2_Con_Sal_SRR_A, TMS_TM2_Con_Sal_SRR_B, TMS_Total_Con_Sal_SRR_A, TMS_Total_Con_Sal_SRR_B, TMS_Total_Con_Sal_SRR_Dia, Sal_Pesometros_TA, Sal_Pesometros_TB, Sal_Pesometros_Dia, 
                Sal_Topografia_Dia, Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido, Sal_Ajustada_TA, Sal_Ajustada_TB, Sal_Ajustada_Dia, Sal_Asignada_TM1_A, Sal_Asignada_TM2_A, Sal_Asignada_TM1_B, Sal_Asignada_TM2_B, 
                Sal_Asignada_TM1_A + Sal_Asignada_TM2_A AS Sal_Distribuida_A, Sal_Asignada_TM1_B + Sal_Asignada_TM2_B AS Sal_Distribuida_B, TMS_TM1_Sin_Sal_Con_SRR_A, TMS_TM1_Sin_Sal_Con_SRR_B, TMS_TM2_Sin_Sal_Con_SRR_A, TMS_TM2_Sin_Sal_Con_SRR_B, 
                TMS_TM1_Sin_Sal_Con_SRR_A + TMS_TM2_Sin_Sal_Con_SRR_A AS TMS_Total_Sin_Sal_Con_SRR_A, TMS_TM1_Sin_Sal_Con_SRR_B + TMS_TM2_Sin_Sal_Con_SRR_B AS TMS_Total_Sin_Sal_Con_SRR_B, 
                TMS_TM1_Sin_Sal_Con_SRR_A + TMS_TM1_Sin_Sal_Con_SRR_B + TMS_TM2_Sin_Sal_Con_SRR_A + TMS_TM2_Sin_Sal_Con_SRR_B AS TMS_Total_Sin_Sal_Con_SRR_Dia, TMS_Total_Con_Sal_SRR_Dia - COALESCE (Sal_Ajustada_Dia, 0) 
                AS TMS_Total_Sin_Sal_Con_SRR_Dia_Check, Sal_Asignada_TM1_A + Sal_Asignada_TM2_A - COALESCE (Sal_Ajustada_TA, 0) AS Check_Sal_A, Sal_Asignada_TM1_B + Sal_Asignada_TM2_B - COALESCE (Sal_Ajustada_TB, 0) AS Check_Sal_B
   FROM    tms_sin_sal
GO

-- ============================================================================
-- inventar_SpcHidr.v_bitacora_rangos (VIEW)
-- Ultima modificacion: 2026-05-14 01:24:38.343000
-- ============================================================================
--
CREATE VIEW inventar_SpcHidr.v_bitacora_rangos AS
WITH b AS (
    SELECT
        torre,
        fecha_turno = fecha_calendario,
        turno,
        ts_fin = ts_toma_muestra,
        comentario,
        nombre_archivo,
        ts_fin_prev = LAG(ts_toma_muestra) OVER (
            PARTITION BY torre
            ORDER BY ts_toma_muestra
        )
    FROM inventar_SpcHidr.bitacora_turnos_consolidada
    WHERE ts_toma_muestra IS NOT NULL
)
SELECT
    torre,
    fecha_turno,
    turno,
    ts_ini = ts_fin_prev,
    ts_fin,
    flag_arrastre = CASE WHEN ts_fin_prev = ts_fin THEN 1 ELSE 0 END,
    duracion_min = CASE
        WHEN ts_fin_prev IS NULL THEN NULL
        ELSE DATEDIFF(MINUTE, ts_fin_prev, ts_fin)
    END,
    comentario,
    nombre_archivo
FROM b;
GO

-- ============================================================================
-- inventar_SpcHidr.v_datos_apilado_tmh_v2 (VIEW)
-- Ultima modificacion: 2026-08-04 14:50:41.020000
-- ============================================================================
/* ================================================================
   ALTER inventar_SpcHidr.v_datos_apilado_tmh_v2
   ----------------------------------------------------------------
   Reemplaza el calculo en vivo (3 JOINs contra tot_TM por fecha,
   sin materializar) por una simple lectura de la tabla congelada
   inventar_SpcHidr.Control_Apilado_TMH_v2_test, poblada por
   sp_mantiene_apilado_tmh_v2_test.

   IMPORTANTE -- aplicar SOLO despues de:
   - correr crear_tabla_control_apilado_tmh_v2_test.sql
   - correr crear_sp_mantiene_apilado_tmh_v2_test.sql
   - confirmar que la consulta de comparacion fila a fila de ese
     script no devolvio ninguna diferencia

   Las columnas expuestas quedan exactamente iguales a las que ya
   entrega la vista hoy -- ningun consumidor (incluida
   v_apilado_tms_con_sal_srr_reporte_test, la metodologia de
   Apilado ya validada) necesita cambios.

   Consecuencia operativa: de ahora en adelante, alguien tiene que
   llamar a sp_mantiene_apilado_tmh_v2_test para que la vista vea
   dias nuevos. Mientras no se agregue esa llamada a un proceso
   automatico (job de SQL Agent o al inicio del pipeline de
   exportacion, igual que ya se hace con
   sp_mantiene_factor_ajuste_camiones_v2_test), los dias que no se
   hayan procesado explicitamente NO apareceran en esta vista.
   Recomendacion: agregar la misma llamada en
   report_export/report_export.py, junto al EXEC de
   sp_mantiene_factor_ajuste_camiones_v2_test que ya existe ahi,
   antes de dar esto por completamente integrado al flujo de
   exportacion. Esto queda pendiente de tu confirmacion -- no se
   modifico el Dash todavia.
================================================================ */
CREATE   VIEW
    [inventar_SpcHidr].[v_datos_apilado_tmh_v2]
AS
SELECT
    Fecha,
    ts_08_dia,
    ts_20_dia,
    ts_08_dia_siguiente,
    CV008_Totalizador_08,
    CV008_Totalizador_20,
    CV008_Totalizador_08_Dia_Siguiente,
    CV108_Totalizador_08,
    CV108_Totalizador_20,
    CV108_Totalizador_08_Dia_Siguiente,
    TMH_CV008_A_Bruto,
    TMH_CV008_B_Bruto,
    TMH_CV108_A_Bruto,
    TMH_CV108_B_Bruto,
    Flag_Apilado_Valido,
    TMH_CV008_A,
    TMH_CV008_B,
    TMH_CV108_A,
    TMH_CV108_B,
    TMH_Apilado_Total_A,
    TMH_Apilado_Total_B,
    TMH_Apilado_Total_Dia,
    Flag_Apilado_Valido_A,
    Flag_Apilado_Valido_B
FROM inventar_SpcHidr.Control_Apilado_TMH_v2_test;
GO

-- ============================================================================
-- inventar_SpcHidr.v_estado_apilado_turno_representatividad (VIEW)
-- Ultima modificacion: 2026-07-24 08:01:00.770000
-- ============================================================================
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
GO

-- ============================================================================
-- inventar_SpcHidr.v_he_10s_por_intervalo_excel (VIEW)
-- Ultima modificacion: 2026-07-22 14:05:44.800000
-- ============================================================================
CREATE   VIEW inventar_SpcHidr.v_he_10s_por_intervalo_excel
AS
SELECT
    dia_op            = s.fecha_turno,
    Torre             = s.Torre,
    turno_op          = s.turno_op,
    ts_ini            = s.ts_ini,
    ts_fin            = s.ts_fin,
    HE_horas          = s.HE_horas,
    flag_intervalo_ok = s.flag_intervalo_ok,
    s.torre_id,
    s.flag_arrastre,
    s.duracion_min,
    s.comentario,
    s.nombre_archivo
FROM inventar_SpcHidr.Resumen_Intervalo_TotTM s;
GO

-- ============================================================================
-- inventar_SpcHidr.v_humedad_inventario_test (VIEW)
-- Ultima modificacion: 2026-07-30 22:08:14.490000
-- ============================================================================

CREATE   VIEW
    [inventar_SpcHidr].[v_humedad_inventario_test]
AS

WITH Base AS
(
    SELECT
        CAST(Fecha AS date) AS Fecha,

        TRY_CONVERT(float, Humedad_Turno_A)
            AS Humedad_Turno_A,

        TRY_CONVERT(float, Humedad_Turno_B)
            AS Humedad_Turno_B,

        TRY_CONVERT(float, Humedad_promedio_dia)
            AS Humedad_Promedio_Dia,

        TRY_CONVERT(float, Humedad_TM1)
            AS Humedad_TM1,

        Fecha_Humedad_TM1,
        Torre_Humedad_TM1,
        Turno_Humedad_TM1,
        Fuente_Humedad_TM1,

        TRY_CONVERT(float, Humedad_TM2)
            AS Humedad_TM2,

        Fecha_Humedad_TM2,
        Torre_Humedad_TM2,
        Turno_Humedad_TM2,
        Fuente_Humedad_TM2

    FROM [inventar_SpcHidr].[v_reporte_diario_humedad_test]
),

Resolucion AS
(
    SELECT
        b.*,

        CASE
            /*
              Caso normal:
              existe apilado y la vista ya calculó una humedad
              diaria ponderada por el tonelaje de los turnos.
            */
            WHEN b.Humedad_Promedio_Dia > 0
                THEN b.Humedad_Promedio_Dia

            /*
              Sin apilado:
              ambos turnos mantienen la misma humedad vigente.
            */
            WHEN b.Humedad_Turno_A > 0
             AND b.Humedad_Turno_B > 0
             AND ABS(
                    b.Humedad_Turno_A
                    - b.Humedad_Turno_B
                 ) <= 0.000001
                THEN
                    (
                        b.Humedad_Turno_A
                        + b.Humedad_Turno_B
                    ) / 2.0

            /*
              Solo existe humedad vigente en el turno A.
            */
            WHEN b.Humedad_Turno_A > 0
             AND
             (
                    b.Humedad_Turno_B IS NULL
                 OR b.Humedad_Turno_B <= 0
             )
                THEN b.Humedad_Turno_A

            /*
              Solo existe humedad vigente en el turno B.
            */
            WHEN b.Humedad_Turno_B > 0
             AND
             (
                    b.Humedad_Turno_A IS NULL
                 OR b.Humedad_Turno_A <= 0
             )
                THEN b.Humedad_Turno_B

            /*
              Respaldo: ambas torres mantienen la misma humedad
              ya resuelta mediante representatividad y arrastre.
            */
            WHEN b.Humedad_TM1 > 0
             AND b.Humedad_TM2 > 0
             AND ABS(
                    b.Humedad_TM1
                    - b.Humedad_TM2
                 ) <= 0.000001
                THEN
                    (
                        b.Humedad_TM1
                        + b.Humedad_TM2
                    ) / 2.0

            /*
              Solo TM1 tiene una humedad operacional resuelta.
            */
            WHEN b.Humedad_TM1 > 0
             AND
             (
                    b.Humedad_TM2 IS NULL
                 OR b.Humedad_TM2 <= 0
             )
                THEN b.Humedad_TM1

            /*
              Solo TM2 tiene una humedad operacional resuelta.
            */
            WHEN b.Humedad_TM2 > 0
             AND
             (
                    b.Humedad_TM1 IS NULL
                 OR b.Humedad_TM1 <= 0
             )
                THEN b.Humedad_TM2

            /*
              Si existen valores diferentes sin una humedad
              diaria ponderada, no se inventa un promedio.
            */
            ELSE NULL
        END AS Humedad_Inventario,

        CASE
            WHEN b.Humedad_Promedio_Dia > 0
                THEN 'HUMEDAD_DIARIA_PONDERADA'

            WHEN b.Humedad_Turno_A > 0
             AND b.Humedad_Turno_B > 0
             AND ABS(
                    b.Humedad_Turno_A
                    - b.Humedad_Turno_B
                 ) <= 0.000001
                THEN 'HUMEDAD_RESUELTA_SIN_APILADO'

            WHEN b.Humedad_Turno_A > 0
             AND
             (
                    b.Humedad_Turno_B IS NULL
                 OR b.Humedad_Turno_B <= 0
             )
                THEN 'HUMEDAD_RESUELTA_TURNO_A'

            WHEN b.Humedad_Turno_B > 0
             AND
             (
                    b.Humedad_Turno_A IS NULL
                 OR b.Humedad_Turno_A <= 0
             )
                THEN 'HUMEDAD_RESUELTA_TURNO_B'

            WHEN b.Humedad_TM1 > 0
             AND b.Humedad_TM2 > 0
             AND ABS(
                    b.Humedad_TM1
                    - b.Humedad_TM2
                 ) <= 0.000001
                THEN 'HUMEDAD_RESUELTA_TORRES'

            WHEN b.Humedad_TM1 > 0
             AND
             (
                    b.Humedad_TM2 IS NULL
                 OR b.Humedad_TM2 <= 0
             )
                THEN 'HUMEDAD_RESUELTA_TM1'

            WHEN b.Humedad_TM2 > 0
             AND
             (
                    b.Humedad_TM1 IS NULL
                 OR b.Humedad_TM1 <= 0
             )
                THEN 'HUMEDAD_RESUELTA_TM2'

            ELSE 'PENDIENTE_REGLA_CONFLICTO_HUMEDAD'
        END AS Regla_Humedad_Inventario

    FROM Base AS b
)

SELECT
    Fecha,

    Humedad_Inventario,
    Regla_Humedad_Inventario,

    CASE
        WHEN Humedad_Inventario IS NOT NULL
         AND Humedad_Inventario > 0
            THEN 1
        ELSE 0
    END AS Flag_Humedad_Inventario_Valida,

    /* Valores utilizados para auditoría */
    Humedad_Turno_A,
    Humedad_Turno_B,
    Humedad_Promedio_Dia,

    Humedad_TM1,
    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,

    Humedad_TM2,
    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2

FROM Resolucion;
GO

-- ============================================================================
-- inventar_SpcHidr.v_informe_tm_lab_norm (VIEW)
-- Ultima modificacion: 2026-02-16 11:44:09.443000
-- ============================================================================
CREATE   VIEW inventar_SpcHidr.v_informe_tm_lab_norm
AS
WITH B AS (
    SELECT
        l.ID_Registro,
        -- Estandarización de Nombres de Torre
        Torre = CASE 
            WHEN UPPER(LTRIM(RTRIM(l.Torre))) IN ('T1', 'TM1', 'TORRE 1') THEN 'T1'
            WHEN UPPER(LTRIM(RTRIM(l.Torre))) IN ('T2', 'TM2', 'TORRE 2') THEN 'T2'
            WHEN UPPER(LTRIM(RTRIM(l.Torre))) IN ('SRR', 'TM3', 'TORRE 3', 'CV-01') THEN 'SRR'
            ELSE UPPER(LTRIM(RTRIM(l.Torre)))
        END,
        fecha_rec = TRY_CONVERT(date, l.Fecha_Recepcion),
        hora_rec  = TRY_CONVERT(time(0), l.Hora),
        l.CuT_global,
        l.CuS_Global,
        l.Fe_Global,
        l.Humedad_Prom_Pct,
        l.RetParcial_2P, -- Asegúrate de incluir las columnas físicas
        l.RetParcial_1P
    FROM inventar_SpcHidr.informe_tm_lab l
)
SELECT
    ID_Registro,
    Torre,
    fecha_muestra_min =
        CASE
            WHEN fecha_rec IS NOT NULL AND hora_rec IS NOT NULL
            THEN DATEADD(MINUTE, DATEDIFF(MINUTE, 0,
                    DATEADD(SECOND, DATEDIFF(SECOND, 0, hora_rec), CAST(fecha_rec AS datetime2(0)))
                 ), 0)
            ELSE NULL
        END,
    CuT_global,
    CuS_Global,
    Fe_Global,
    Humedad_Prom_Pct,
    RetParcial_2P,
    RetParcial_1P
FROM B
WHERE Torre IN ('T1','T2','SRR'); -- Agregamos SRR al filtro
GO

-- ============================================================================
-- inventar_SpcHidr.v_inventario_chancado_archive_test (VIEW)
-- Ultima modificacion: 2026-08-04 14:18:33.377000
-- ============================================================================
/* ================================================================
   ALTER inventar_SpcHidr.v_inventario_chancado_archive_test
   Fix de performance -- NO cambia ninguna logica de calculo.
   ----------------------------------------------------------------
   Diagnostico (ver memoria de sesion, script
   investigar_hotspot_archive_totTM.sql): las CTE base de esta vista
   (BaseBloqueArchive, RegistrosHora8) leen inventar_SpcHidr.
   datos_filtrados COMPLETO, sin ningun filtro de fecha. La vista
   confia en que quien la consuma filtre despues por la columna final
   Fecha, pero esa columna es una expresion calculada
   (CAST(DATEADD(HOUR,-8, df.fecha_inicial) AS date)) que atraviesa
   varias capas de GROUP BY antes de llegar al SELECT final -- el
   optimizador no puede empujar ese filtro hacia atras, asi que cada
   vez que se invoca la vista escanea datos_filtrados entero.

   Esto explica el consumo medido: 1.325.631 lecturas logicas /
   1312 scans de datos_filtrados en un solo EXEC de
   sp_factor_ajuste_camiones_test para 31 dias.

   FIX: agregar un filtro de fecha SARGABLE (comparacion directa
   contra la columna cruda df.fecha_inicial, sin envolver en
   funciones) en las dos CTE que leen datos_filtrados desde cero.
   Se usa una ventana movil de 400 dias hacia atras desde GETDATE() --
   mismo patron ya usado en sp_reporte_turno_emision_test (Bloque 2,
   90 dias de historia para humedad de laboratorio), solo que aca se
   necesita una ventana mas ancha porque esta vista tambien resuelve
   el "inventario anterior" via LAG, que puede mirar un dia hacia
   atras del rango pedido.

   IMPORTANTE -- limitacion de este fix: si en el futuro se necesita
   consultar esta vista para fechas anteriores a ~13 meses atras de
   HOY, la vista devolvera NULL/vacio para esas fechas en vez de
   calcular el inventario. Mientras el uso real sea el rango de
   trabajo activo del proyecto (enero 2026 en adelante), esto no
   afecta ningun resultado. Si se necesita reconstruir historico mas
   antiguo, ampliar la ventana o quitar el filtro para esa
   ejecucion puntual.

   Todo lo demas queda exactamente igual al original (mismas formulas
   de TMH_Silo/TMH_Harnero/TMH_Chancado, misma validacion de bloque
   Archive, mismo LAG e igual resolucion de inventario anterior via
   semilla_inventario_chancado).
================================================================ */
CREATE   VIEW
    [inventar_SpcHidr].[v_inventario_chancado_archive_test]
AS
WITH Parametros AS
(
    SELECT
        CAST(5.0 AS float) AS Cantidad_Bins,
        CAST(1.6 AS float) AS Densidad_Ton_M3,
        CAST(1200.0 AS float) AS Tolva_Compensacion_TMH
),
/*==============================================================
  1. Base cruda -- FILTRO DE FECHA AGREGADO (fix de performance)
==============================================================*/
BaseBloqueArchive AS
(
    SELECT
        CAST(DATEADD(HOUR, -8, df.fecha_inicial) AS date) AS Fecha_Operacional,
        df.fecha_inicial,
        TRY_CONVERT(float, df.nivel_silo_a) AS nivel_silo_a,
        TRY_CONVERT(float, df.nivel_silo_b) AS nivel_silo_b,
        TRY_CONVERT(float, df.nivel_harnero_a) AS nivel_harnero_a,
        TRY_CONVERT(float, df.nivel_harnero_b) AS nivel_harnero_b,
        TRY_CONVERT(float, df.nivel_harnero_c) AS nivel_harnero_c,
        TRY_CONVERT(float, df.nivel_harnero_d) AS nivel_harnero_d,
        TRY_CONVERT(float, df.nivel_harnero_e) AS nivel_harnero_e,
        TRY_CONVERT(float, df.nivel_chancado_a) AS nivel_chancado_a,
        TRY_CONVERT(float, df.nivel_chancado_b) AS nivel_chancado_b,
        TRY_CONVERT(float, df.nivel_chancado_c) AS nivel_chancado_c,
        TRY_CONVERT(float, df.nivel_chancado_d) AS nivel_chancado_d,
        TRY_CONVERT(float, df.nivel_chancado_e) AS nivel_chancado_e
    FROM [inventar_SpcHidr].[datos_filtrados] AS df
    WHERE df.fecha_inicial >= DATEADD(DAY, -400, CAST(GETDATE() AS date))
),
/*==============================================================
  2. Validacion del parche Archive Value
  Un bloque valido debe cumplir:
  - 24 registros horarios.
  - Inicio a las 08:00.
  - Termino a las 07:00 del dia siguiente.
  - 24 valores no nulos para cada sensor.
  - Un unico valor distinto por sensor dentro del bloque.
==============================================================*/
ValidacionBloqueArchive AS
(
    SELECT
        Fecha_Operacional,
        MIN(fecha_inicial) AS Primera_Fila_Bloque,
        MAX(fecha_inicial) AS Ultima_Fila_Bloque,
        COUNT(*) AS Cantidad_Filas_Bloque,
        CASE
            WHEN COUNT(*) = 24
             AND MIN(fecha_inicial) = DATEADD(HOUR, 8, CAST(Fecha_Operacional AS datetime2))
             AND MAX(fecha_inicial) = DATEADD(HOUR, 7, DATEADD(DAY, 1, CAST(Fecha_Operacional AS datetime2)))
             AND COUNT(nivel_silo_a) = 24 AND COUNT(nivel_silo_b) = 24
             AND COUNT(nivel_harnero_a) = 24 AND COUNT(nivel_harnero_b) = 24
             AND COUNT(nivel_harnero_c) = 24 AND COUNT(nivel_harnero_d) = 24
             AND COUNT(nivel_harnero_e) = 24
             AND COUNT(nivel_chancado_a) = 24 AND COUNT(nivel_chancado_b) = 24
             AND COUNT(nivel_chancado_c) = 24 AND COUNT(nivel_chancado_d) = 24
             AND COUNT(nivel_chancado_e) = 24
             AND COUNT(DISTINCT nivel_silo_a) = 1 AND COUNT(DISTINCT nivel_silo_b) = 1
             AND COUNT(DISTINCT nivel_harnero_a) = 1 AND COUNT(DISTINCT nivel_harnero_b) = 1
             AND COUNT(DISTINCT nivel_harnero_c) = 1 AND COUNT(DISTINCT nivel_harnero_d) = 1
             AND COUNT(DISTINCT nivel_harnero_e) = 1
             AND COUNT(DISTINCT nivel_chancado_a) = 1 AND COUNT(DISTINCT nivel_chancado_b) = 1
             AND COUNT(DISTINCT nivel_chancado_c) = 1 AND COUNT(DISTINCT nivel_chancado_d) = 1
             AND COUNT(DISTINCT nivel_chancado_e) = 1
                THEN 1
            ELSE 0
        END AS Flag_Bloque_Archive_Valido
    FROM BaseBloqueArchive
    GROUP BY Fecha_Operacional
),
/*==============================================================
  3. Seleccion de la fila de las 08:00 -- FILTRO DE FECHA AGREGADO
  Aunque el Archive Value esta repetido durante 24 horas, se
  conserva la estructura anterior de la vista y se utiliza la fila
  de las 08:00 como representante del dia operacional.
==============================================================*/
RegistrosHora8 AS
(
    SELECT
        CAST(df.fecha_inicial AS date) AS Fecha_Lectura_D1,
        df.fecha_inicial,
        TRY_CONVERT(float, df.nivel_silo_a) AS nivel_silo_a,
        TRY_CONVERT(float, df.nivel_silo_b) AS nivel_silo_b,
        TRY_CONVERT(float, df.nivel_harnero_a) AS nivel_harnero_a,
        TRY_CONVERT(float, df.nivel_harnero_b) AS nivel_harnero_b,
        TRY_CONVERT(float, df.nivel_harnero_c) AS nivel_harnero_c,
        TRY_CONVERT(float, df.nivel_harnero_d) AS nivel_harnero_d,
        TRY_CONVERT(float, df.nivel_harnero_e) AS nivel_harnero_e,
        TRY_CONVERT(float, df.nivel_chancado_a) AS nivel_chancado_a,
        TRY_CONVERT(float, df.nivel_chancado_b) AS nivel_chancado_b,
        TRY_CONVERT(float, df.nivel_chancado_c) AS nivel_chancado_c,
        TRY_CONVERT(float, df.nivel_chancado_d) AS nivel_chancado_d,
        TRY_CONVERT(float, df.nivel_chancado_e) AS nivel_chancado_e
    FROM [inventar_SpcHidr].[datos_filtrados] AS df
    WHERE DATEPART(HOUR, df.fecha_inicial) = 8
      AND DATEPART(MINUTE, df.fecha_inicial) = 0
      AND df.fecha_inicial >= DATEADD(DAY, -400, CAST(GETDATE() AS date))
),
/*==============================================================
  4. Consolidacion de registros encontrados a las 08:00
==============================================================*/
PromedioHora8 AS
(
    SELECT
        Fecha_Lectura_D1,
        MIN(fecha_inicial) AS Primera_Lectura_Hora_8,
        MAX(fecha_inicial) AS Ultima_Lectura_Hora_8,
        COUNT(*) AS Cantidad_Registros_Hora_8,
        AVG(nivel_silo_a) AS nivel_silo_a,
        AVG(nivel_silo_b) AS nivel_silo_b,
        AVG(nivel_harnero_a) AS nivel_harnero_a,
        AVG(nivel_harnero_b) AS nivel_harnero_b,
        AVG(nivel_harnero_c) AS nivel_harnero_c,
        AVG(nivel_harnero_d) AS nivel_harnero_d,
        AVG(nivel_harnero_e) AS nivel_harnero_e,
        AVG(nivel_chancado_a) AS nivel_chancado_a,
        AVG(nivel_chancado_b) AS nivel_chancado_b,
        AVG(nivel_chancado_c) AS nivel_chancado_c,
        AVG(nivel_chancado_d) AS nivel_chancado_d,
        AVG(nivel_chancado_e) AS nivel_chancado_e
    FROM RegistrosHora8
    GROUP BY Fecha_Lectura_D1
),
/*==============================================================
  5. Fecha operacional corregida
  El Archive Value del 01-07 ya esta almacenado desde el 01-07 a
  las 08:00, por lo que no corresponde restar un dia.
==============================================================*/
FechaOperacional AS
(
    SELECT
        CAST(p.Fecha_Lectura_D1 AS date) AS Fecha,
        p.Fecha_Lectura_D1,
        p.Primera_Lectura_Hora_8,
        p.Ultima_Lectura_Hora_8,
        p.Cantidad_Registros_Hora_8,
        p.nivel_silo_a,
        p.nivel_silo_b,
        p.nivel_harnero_a,
        p.nivel_harnero_b,
        p.nivel_harnero_c,
        p.nivel_harnero_d,
        p.nivel_harnero_e,
        p.nivel_chancado_a,
        p.nivel_chancado_b,
        p.nivel_chancado_c,
        p.nivel_chancado_d,
        p.nivel_chancado_e
    FROM PromedioHora8 AS p
),
/*==============================================================
  6. Promedio de sensores por instalacion
==============================================================*/
NivelesPromedio AS
(
    SELECT
        f.*,
        silo.Nivel_Inventario_Silo,
        silo.Sensores_Silo_Validos,
        harnero.Nivel_Inventario_Harnero,
        harnero.Sensores_Harnero_Validos,
        chancado.Nivel_Inventario_Chancado,
        chancado.Sensores_Chancado_Validos
    FROM FechaOperacional AS f
    CROSS APPLY
    (
        SELECT AVG(v.Valor) AS Nivel_Inventario_Silo, COUNT(v.Valor) AS Sensores_Silo_Validos
        FROM (VALUES (f.nivel_silo_a), (f.nivel_silo_b)) AS v(Valor)
    ) AS silo
    CROSS APPLY
    (
        SELECT AVG(v.Valor) AS Nivel_Inventario_Harnero, COUNT(v.Valor) AS Sensores_Harnero_Validos
        FROM (VALUES (f.nivel_harnero_a), (f.nivel_harnero_b), (f.nivel_harnero_c), (f.nivel_harnero_d), (f.nivel_harnero_e)) AS v(Valor)
    ) AS harnero
    CROSS APPLY
    (
        SELECT AVG(v.Valor) AS Nivel_Inventario_Chancado, COUNT(v.Valor) AS Sensores_Chancado_Validos
        FROM (VALUES (f.nivel_chancado_a), (f.nivel_chancado_b), (f.nivel_chancado_c), (f.nivel_chancado_d), (f.nivel_chancado_e)) AS v(Valor)
    ) AS chancado
),
/*==============================================================
  7. Incorporacion de humedad, parametros y validacion Archive
==============================================================*/
BaseConHumedad AS
(
    SELECT
        n.*,
        va.Primera_Fila_Bloque,
        va.Ultima_Fila_Bloque,
        va.Cantidad_Filas_Bloque,
        ISNULL(va.Flag_Bloque_Archive_Valido, 0) AS Flag_Bloque_Archive_Valido,
        h.Humedad_Inventario,
        h.Regla_Humedad_Inventario,
        h.Flag_Humedad_Inventario_Valida,
        h.Fecha_Humedad_TM1,
        h.Torre_Humedad_TM1,
        h.Turno_Humedad_TM1,
        h.Fuente_Humedad_TM1,
        h.Fecha_Humedad_TM2,
        h.Torre_Humedad_TM2,
        h.Turno_Humedad_TM2,
        h.Fuente_Humedad_TM2,
        p.Cantidad_Bins,
        p.Densidad_Ton_M3,
        p.Tolva_Compensacion_TMH,
        0.0957 * n.Nivel_Inventario_Harnero + 0.43 AS Y_Harnero,
        0.0957 * n.Nivel_Inventario_Chancado + 0.43 AS Y_Chancado
    FROM NivelesPromedio AS n
    CROSS JOIN Parametros AS p
    LEFT JOIN [inventar_SpcHidr].[v_humedad_inventario_test] AS h
        ON h.Fecha = n.Fecha
    LEFT JOIN ValidacionBloqueArchive AS va
        ON va.Fecha_Operacional = n.Fecha
),
/*==============================================================
  8. Calculo de inventarios humedos TMH
==============================================================*/
InventariosTMH AS
(
    SELECT
        b.*,
        CASE
            WHEN b.Nivel_Inventario_Silo IS NULL THEN NULL
            ELSE PI() * POWER(CAST(7.5 AS float), 2) * CAST(11.0 AS float)
                 * b.Nivel_Inventario_Silo * CAST(b.Densidad_Ton_M3 AS float)
                 / CAST(100.0 AS float)
        END AS TMH_Silo,
        CASE
            WHEN b.Nivel_Inventario_Harnero IS NULL THEN NULL
            WHEN b.Y_Harnero > 0 AND b.Y_Harnero <= 2.268
                THEN (31.6468254 * POWER(b.Y_Harnero, 2) + 63.8 * b.Y_Harnero) * (b.Cantidad_Bins * b.Densidad_Ton_M3 / 5.0)
            WHEN b.Y_Harnero > 2.268 AND b.Y_Harnero <= 2.52
                THEN (25.3173746 * POWER(b.Y_Harnero, 2) + 92.51 * b.Y_Harnero - 32.55714) * (b.Cantidad_Bins * b.Densidad_Ton_M3 / 5.0)
            ELSE (220.11 * b.Y_Harnero - 193.33314) * (b.Cantidad_Bins * b.Densidad_Ton_M3 / 5.0)
        END AS TMH_Harnero,
        CASE
            WHEN b.Nivel_Inventario_Chancado IS NULL THEN NULL
            WHEN b.Y_Chancado > 0 AND b.Y_Chancado <= 2.268
                THEN (31.6468254 * POWER(b.Y_Chancado, 2) + 63.8 * b.Y_Chancado) * (b.Cantidad_Bins * b.Densidad_Ton_M3 / 5.0)
            WHEN b.Y_Chancado > 2.268 AND b.Y_Chancado <= 2.52
                THEN (25.3173746 * POWER(b.Y_Chancado, 2) + 92.51 * b.Y_Chancado - 32.55714) * (b.Cantidad_Bins * b.Densidad_Ton_M3 / 5.0)
            ELSE (220.11 * b.Y_Chancado - 193.33314) * (b.Cantidad_Bins * b.Densidad_Ton_M3 / 5.0)
        END AS TMH_Chancado
    FROM BaseConHumedad AS b
),
/*==============================================================
  9. Inventario total humedo
==============================================================*/
Totales AS
(
    SELECT
        i.*,
        CASE
            WHEN i.TMH_Silo IS NOT NULL AND i.TMH_Harnero IS NOT NULL AND i.TMH_Chancado IS NOT NULL
                THEN i.TMH_Silo + i.TMH_Harnero + i.TMH_Chancado + i.Tolva_Compensacion_TMH
            ELSE NULL
        END AS Total_Inventario_Chancado_TMH
    FROM InventariosTMH AS i
),
/*==============================================================
  10. Conversion del inventario a toneladas secas
==============================================================*/
TotalesSecos AS
(
    SELECT
        t.*,
        CASE
            WHEN t.Flag_Bloque_Archive_Valido = 1
             AND t.Flag_Humedad_Inventario_Valida = 1
             AND t.Total_Inventario_Chancado_TMH IS NOT NULL
                THEN t.Total_Inventario_Chancado_TMH * (1.0 - t.Humedad_Inventario / 100.0)
            ELSE NULL
        END AS Total_Inventario_Chancado_TMS
    FROM Totales AS t
),
/*==============================================================
  11. Recuperacion del inventario anterior mediante LAG
==============================================================*/
ConLagInventario AS
(
    SELECT
        t.*,
        LAG(t.Fecha) OVER (ORDER BY t.Fecha) AS Fecha_Inventario_Anterior_Lag,
        LAG(t.Total_Inventario_Chancado_TMS) OVER (ORDER BY t.Fecha) AS Inventario_Chancado_TMS_Anterior_Lag
    FROM TotalesSecos AS t
),
/*==============================================================
  12. Resolucion entre semilla oficial y LAG
  Prioridad:
  1. Semilla oficial del dia anterior.
  2. Inventario calculado por la propia vista.
==============================================================*/
ConInventarioAnterior AS
(
    SELECT
        l.*,
        CASE
            WHEN s.Inventario_Chancado_TMS IS NOT NULL THEN s.Fecha
            WHEN l.Inventario_Chancado_TMS_Anterior_Lag IS NOT NULL THEN l.Fecha_Inventario_Anterior_Lag
            ELSE NULL
        END AS Fecha_Inventario_Anterior,
        COALESCE(TRY_CONVERT(float, s.Inventario_Chancado_TMS), l.Inventario_Chancado_TMS_Anterior_Lag) AS Inventario_Chancado_TMS_Anterior,
        CASE
            WHEN s.Inventario_Chancado_TMS IS NOT NULL THEN 'SEMILLA_OFICIAL'
            WHEN l.Inventario_Chancado_TMS_Anterior_Lag IS NOT NULL THEN 'LAG_VISTA'
            ELSE 'SIN_INVENTARIO_ANTERIOR'
        END AS Fuente_Inventario_Anterior
    FROM ConLagInventario AS l
    LEFT JOIN [inventar_SpcHidr].[semilla_inventario_chancado] AS s
        ON s.Fecha = DATEADD(DAY, -1, l.Fecha)
       AND s.Activo = 1
),
/*==============================================================
  13. Delta diario de inventario
==============================================================*/
Resultado AS
(
    SELECT
        c.*,
        CASE
            WHEN DATEDIFF(DAY, c.Fecha_Inventario_Anterior, c.Fecha) = 1
             AND c.Total_Inventario_Chancado_TMS IS NOT NULL
             AND c.Inventario_Chancado_TMS_Anterior IS NOT NULL
                THEN 1
            ELSE 0
        END AS Flag_Continuidad_Diaria,
        CASE
            WHEN DATEDIFF(DAY, c.Fecha_Inventario_Anterior, c.Fecha) = 1
             AND c.Total_Inventario_Chancado_TMS IS NOT NULL
             AND c.Inventario_Chancado_TMS_Anterior IS NOT NULL
                THEN c.Total_Inventario_Chancado_TMS - c.Inventario_Chancado_TMS_Anterior
            ELSE NULL
        END AS Delta_Inventario_Chancado_TMS
    FROM ConInventarioAnterior AS c
)
/*==============================================================
  14. Salida final
==============================================================*/
SELECT
    Fecha,
    Fecha_Lectura_D1,
    Primera_Lectura_Hora_8,
    Ultima_Lectura_Hora_8,
    Cantidad_Registros_Hora_8,
    Primera_Fila_Bloque,
    Ultima_Fila_Bloque,
    Cantidad_Filas_Bloque,
    Flag_Bloque_Archive_Valido,
    Nivel_Inventario_Silo,
    Sensores_Silo_Validos,
    Nivel_Inventario_Harnero,
    Sensores_Harnero_Validos,
    Nivel_Inventario_Chancado,
    Sensores_Chancado_Validos,
    TMH_Silo,
    TMH_Harnero,
    TMH_Chancado,
    Tolva_Compensacion_TMH,
    Total_Inventario_Chancado_TMH,
    Humedad_Inventario,
    Regla_Humedad_Inventario,
    Flag_Humedad_Inventario_Valida,
    Total_Inventario_Chancado_TMS,
    Fecha_Inventario_Anterior,
    Inventario_Chancado_TMS_Anterior,
    Fuente_Inventario_Anterior,
    Flag_Continuidad_Diaria,
    Delta_Inventario_Chancado_TMS,
    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,
    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2,
    CASE
        WHEN Cantidad_Registros_Hora_8 = 1
         AND Flag_Bloque_Archive_Valido = 1
         AND Sensores_Silo_Validos = 2
         AND Sensores_Harnero_Validos = 5
         AND Sensores_Chancado_Validos = 5
         AND Flag_Humedad_Inventario_Valida = 1
         AND Flag_Continuidad_Diaria = 1
            THEN 1
        ELSE 0
    END AS Flag_Inventario_Valido
FROM Resultado;
GO

-- ============================================================================
-- inventar_SpcHidr.v_inventario_chancado_test (VIEW)
-- Ultima modificacion: 2026-08-01 16:25:53.713000
-- ============================================================================

CREATE   VIEW
    [inventar_SpcHidr].[v_inventario_chancado_test]
AS
SELECT
    Fecha,
    Fecha_Lectura_D1,

    Primera_Fila_Bloque,
    Ultima_Fila_Bloque,
    Cantidad_Filas_Bloque,
    Flag_Bloque_Archive_Valido,

    Nivel_Inventario_Silo,
    Nivel_Inventario_Harnero,
    Nivel_Inventario_Chancado,

    TMH_Silo,
    TMH_Harnero,
    TMH_Chancado,
    Tolva_Compensacion_TMH,

    Total_Inventario_Chancado_TMH,
    Humedad_Inventario,
    Total_Inventario_Chancado_TMS,

    Fecha_Inventario_Anterior,
    Inventario_Chancado_TMS_Anterior,
    Fuente_Inventario_Anterior,

    Delta_Inventario_Chancado_TMS,

    Flag_Continuidad_Diaria,
    Flag_Inventario_Valido

FROM
    [inventar_SpcHidr].[v_inventario_chancado_archive_test];
GO

-- ============================================================================
-- inventar_SpcHidr.v_peso_real_torre_turno_excel (VIEW)
-- Ultima modificacion: 2026-07-11 12:30:11.863000
-- ============================================================================
CREATE VIEW inventar_SpcHidr.v_peso_real_torre_turno_excel
AS
SELECT
    Fecha,
    Turno,
    Torre,
    PesoReal_Quimico,
    PesoReal_Fisico,
    nombre_archivo,
    fecha_carga
FROM inventar_SpcHidr.peso_real_torre_turno
WHERE Torre IN ('T1', 'T2', 'SRR');
GO

-- ============================================================================
-- inventar_SpcHidr.v_peso_teorico_turno_torre_excel (VIEW)
-- Ultima modificacion: 2026-07-11 13:13:31.710000
-- ============================================================================
CREATE VIEW inventar_SpcHidr.v_peso_teorico_turno_torre_excel
AS

WITH base AS
(
    SELECT
        r.Fecha,
        r.Turno,
        r.Torre,
        r.Horas_Reales,
        r.Factor_Masa,
        r.ts_ini,
        r.ts_fin,
        p.PesoBase_Quimico_12h,
        p.PesoBase_Fisico_12h,

        Fraccion_Muestreo =
            CASE
                WHEN r.ts_ini IS NULL
                  OR r.ts_fin IS NULL
                  OR r.ts_fin <= r.ts_ini
                    THEN 1.0

                ELSE
                    DATEDIFF(MINUTE, r.ts_ini, r.ts_fin)
                    / 720.0
            END,

        Factor_Comun =
            CASE
                WHEN r.Horas_Reales IS NULL
                  OR r.Horas_Reales <= 0
                    THEN NULL

                WHEN r.Factor_Masa IS NULL
                    THEN NULL

                ELSE
                    r.Factor_Masa
                    * (r.Horas_Reales / 12.0)
                    *
                    CASE
                        WHEN r.ts_ini IS NULL
                          OR r.ts_fin IS NULL
                          OR r.ts_fin <= r.ts_ini
                            THEN 1.0

                        ELSE
                            DATEDIFF(
                                MINUTE,
                                r.ts_ini,
                                r.ts_fin
                            ) / 720.0
                    END
            END

    FROM inventar_SpcHidr.v_reporte_diario_emulado_excel AS r

    INNER JOIN inventar_SpcHidr.param_peso_teorico_base AS p
        ON  p.Torre = r.Torre
        AND p.Activo = 1

    WHERE r.Torre IN ('T1', 'T2', 'SRR')
)

SELECT
    Fecha,
    Turno,
    Torre,
    Horas_Reales,
    Factor_Masa,
    ts_ini,
    ts_fin,
    PesoBase_Quimico_12h,
    PesoBase_Fisico_12h,
    Fraccion_Muestreo,

    PesoTeo_Quimico =
        CASE
            WHEN Horas_Reales IS NULL
              OR Horas_Reales <= 0
                THEN 0

            WHEN Factor_Comun IS NULL
                THEN NULL

            WHEN PesoBase_Quimico_12h IS NULL
                THEN NULL

            ELSE
                PesoBase_Quimico_12h
                * Factor_Comun
        END,

    PesoTeo_Fisico =
        CASE
            WHEN Horas_Reales IS NULL
              OR Horas_Reales <= 0
                THEN 0

            WHEN Factor_Comun IS NULL
                THEN NULL

            WHEN PesoBase_Fisico_12h IS NULL
                THEN NULL

            ELSE
                PesoBase_Fisico_12h
                * Factor_Comun
        END

FROM base;
GO

-- ============================================================================
-- inventar_SpcHidr.v_planes_mensuales_diarios_test (VIEW)
-- Ultima modificacion: 2026-06-17 15:52:47.310000
-- ============================================================================

CREATE   VIEW
    [inventar_SpcHidr].[v_planes_mensuales_diarios_test]
AS

WITH PlanesRankeados AS
(
    SELECT
        pm.id,
        pm.fecha,

        pm.cut,
        pm.cu_fino,

        pm.rotopala1,
        pm.rotopala2,
        pm.camiones,

        pm.produccion_catodos,

        pm.srr,
        pm.cut_srr,

        ROW_NUMBER() OVER
        (
            PARTITION BY pm.fecha
            ORDER BY pm.id DESC
        ) AS rn

    FROM [inventar_SpcHidr].[planes_mensuales] pm

    WHERE pm.fecha IS NOT NULL
)

SELECT
    id,
    fecha AS Fecha,

    /* ========================================================
       CAMPOS DE APILADO
       Solo se conservan para diagnóstico.
       No reemplazan la fuente ya validada del reporte.
       ======================================================== */

    cut
        AS Ley_CuT_Plan_Fuente,

    cu_fino
        AS Cobre_Fino_Apilado_Plan_Fuente,

    /* ========================================================
       ROTOPALAS
       ======================================================== */

    rotopala1
        AS TMS_Rotopala_1_Plan,

    rotopala2
        AS TMS_Rotopala_2_Plan,

    /* ========================================================
       CAMIONES
       ======================================================== */

    camiones
        AS Camiones_TMS_Plan,

    /* ========================================================
       PRODUCCIÓN CATÓDICA
       ======================================================== */

    produccion_catodos
        AS Produccion_Catodos_Plan,

    /* ========================================================
       SRR

       En enero, los NULL de SRR y CuT SRR corresponden
       a valores históricos iguales a cero.
       ======================================================== */

    COALESCE(srr, 0)
        AS SRR_TMS_Plan,

    COALESCE(cut_srr, 0)
        AS Ley_CuT_Plan_SRR,

    /* ========================================================
       BANDERAS DE CONTROL
       ======================================================== */

    CASE
        WHEN rotopala1 IS NULL
            THEN 'SIN_PLAN'
        WHEN rotopala1 < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Rotopala_1_Plan,

    CASE
        WHEN rotopala2 IS NULL
            THEN 'SIN_PLAN'
        WHEN rotopala2 < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Rotopala_2_Plan,

    CASE
        WHEN camiones IS NULL
            THEN 'SIN_PLAN'
        WHEN camiones < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Camiones_Plan,

    CASE
        WHEN produccion_catodos IS NULL
            THEN 'SIN_PLAN'
        WHEN produccion_catodos < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Produccion_Catodos_Plan,

    CASE
        WHEN srr IS NULL
            THEN 'OK_CERO_DESDE_NULL'
        WHEN srr < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_SRR_TMS_Plan,

    CASE
        WHEN cut_srr IS NULL
            THEN 'OK_CERO_DESDE_NULL'
        WHEN cut_srr < 0
            THEN 'PLAN_NEGATIVO'
        ELSE 'OK'
    END AS Flag_Ley_CuT_SRR_Plan,

    CASE
        WHEN cut IS NULL
            THEN 'SIN_PLAN'

        WHEN cut < 0
            THEN 'PLAN_NEGATIVO'

        WHEN cut > 2
            THEN 'REVISAR_VALOR_ALTO'

        ELSE 'OK'
    END AS Flag_Ley_CuT_Apilado_Fuente,

    CASE
        WHEN cu_fino IS NULL
            THEN 'SIN_PLAN'

        WHEN cu_fino < 0
            THEN 'PLAN_NEGATIVO'

        WHEN cu_fino > 1000
            THEN 'REVISAR_VALOR_ALTO'

        ELSE 'OK'
    END AS Flag_Cobre_Fino_Apilado_Fuente

FROM PlanesRankeados

WHERE rn = 1;
GO

-- ============================================================================
-- inventar_SpcHidr.v_produccion_catodica_diaria_test (VIEW)
-- Ultima modificacion: 2026-06-17 10:54:09.003000
-- ============================================================================

CREATE   VIEW
    [inventar_SpcHidr].[v_produccion_catodica_diaria_test]
AS

WITH Registros AS
(
    SELECT
        CAST(fecha_registro AS date) AS Fecha,

        id_registro,
        fecha_registro,

        turno_a,
        turno_b,
        real_produccion_ton,
        acumulado_real_ton,
        plan_produccion,

        ROW_NUMBER() OVER
        (
            PARTITION BY CAST(fecha_registro AS date)
            ORDER BY
                fecha_registro DESC,
                id_registro DESC
        ) AS rn

    FROM [inventar_SpcHidr].[produccion_catodica]

    WHERE fecha_registro IS NOT NULL
)

SELECT
    Fecha,

    id_registro,
    fecha_registro AS Fecha_Carga,

    turno_a,
    turno_b,

    real_produccion_ton
        AS Produccion_Catodos_Real,

    acumulado_real_ton,
    plan_produccion,

    CASE
        WHEN real_produccion_ton IS NULL
            THEN 'SIN_PRODUCCION_REAL'

        WHEN real_produccion_ton < 0
            THEN 'PRODUCCION_NEGATIVA'

        ELSE 'OK'
    END AS Flag_Produccion_Catodica

FROM Registros

WHERE rn = 1;
GO

-- ============================================================================
-- inventar_SpcHidr.v_reporte_diario_apilado_test (VIEW)
-- Ultima modificacion: 2026-07-29 13:57:09.160000
-- ============================================================================
CREATE   VIEW
[inventar_SpcHidr].[v_reporte_diario_apilado_test]
AS


WITH base AS (SELECT v.Fecha, CAST(1.0 AS float) AS Factor_Ajuste_Camiones, h.Humedad_Turno_A, h.Humedad_Turno_B, h.Humedad_promedio_dia, v.TMH_Total_Con_Sal_SRR_A AS TMH_Bruto_A, v.TMH_Total_Con_Sal_SRR_B AS TMH_Bruto_B, 
                                     v.TMH_Total_Con_Sal_SRR_Dia AS TMH_Bruto_Dia, v.Sal_Ajustada_TA AS Sal_Ajustada_A, v.Sal_Ajustada_TB AS Sal_Ajustada_B, v.Sal_Ajustada_Dia, v.TMS_Total_Sin_Sal_Con_SRR_A AS TMS_Sin_Sal_A, v.TMS_Total_Sin_Sal_Con_SRR_B AS TMS_Sin_Sal_B, 
                                     v.TMS_Total_Sin_Sal_Con_SRR_Dia AS TMS_Sin_Sal_Dia, v.Sal_Pesometros_TA, v.Sal_Pesometros_TB, v.Sal_Pesometros_Dia, v.Sal_Topografia_Dia, v.Flag_Sal_Basica_Valida, v.Flag_Sal_Ajuste_Valido, v.Flag_Apilado_Valido, v.Flag_TMS_Valido, 
                                     v.Observacion_TMS
                        FROM    inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test AS v LEFT OUTER JOIN
                                     inventar_SpcHidr.v_reporte_diario_humedad_test AS h ON h.Fecha = v.Fecha), calculo AS
    (SELECT Fecha, Factor_Ajuste_Camiones, Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia, TMH_Bruto_A, TMH_Bruto_B, TMH_Bruto_Dia, Sal_Ajustada_A, Sal_Ajustada_B, Sal_Ajustada_Dia, TMS_Sin_Sal_A, TMS_Sin_Sal_B, TMS_Sin_Sal_Dia, Sal_Pesometros_TA, 
                 Sal_Pesometros_TB, Sal_Pesometros_Dia, Sal_Topografia_Dia, Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido, Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS, COALESCE (Sal_Ajustada_A, 0) AS Sal_turno_A, COALESCE (Sal_Ajustada_B, 0) AS Sal_turno_B, 
                 COALESCE (Sal_Ajustada_A, 0) + COALESCE (Sal_Ajustada_B, 0) AS Sal_Dia, TMH_Bruto_A * Factor_Ajuste_Camiones - COALESCE (Sal_Ajustada_A, 0) AS Apilado_TMH_turno_A, TMH_Bruto_B * Factor_Ajuste_Camiones - COALESCE (Sal_Ajustada_B, 0) 
                 AS Apilado_TMH_turno_B, CASE WHEN COALESCE (b.TMH_Bruto_A, 0) = 0 THEN 0 WHEN b.Humedad_Turno_A IS NULL THEN NULL ELSE b.TMH_Bruto_A * b.Factor_Ajuste_Camiones * (1 - b.Humedad_Turno_A / 100.0) - COALESCE (b.Sal_Ajustada_A, 0) 
                 END AS Apilado_TMS_turno_A_Recalculado, CASE WHEN COALESCE (b.TMH_Bruto_B, 0) = 0 THEN 0 WHEN b.Humedad_Turno_B IS NULL THEN NULL ELSE b.TMH_Bruto_B * b.Factor_Ajuste_Camiones * (1 - b.Humedad_Turno_B / 100.0) - COALESCE (b.Sal_Ajustada_B, 0) 
                 END AS Apilado_TMS_turno_B_Recalculado
    FROM    base AS b), resultado AS
    (SELECT Fecha, Factor_Ajuste_Camiones, Humedad_Turno_A, Humedad_Turno_B, Humedad_promedio_dia, TMH_Bruto_A, TMH_Bruto_B, TMH_Bruto_Dia, Sal_Ajustada_A, Sal_Ajustada_B, Sal_Ajustada_Dia, TMS_Sin_Sal_A, TMS_Sin_Sal_B, TMS_Sin_Sal_Dia, Sal_Pesometros_TA, 
                 Sal_Pesometros_TB, Sal_Pesometros_Dia, Sal_Topografia_Dia, Flag_Sal_Basica_Valida, Flag_Sal_Ajuste_Valido, Flag_Apilado_Valido, Flag_TMS_Valido, Observacion_TMS, Sal_turno_A, Sal_turno_B, Sal_Dia, Apilado_TMH_turno_A, Apilado_TMH_turno_B, 
                 Apilado_TMS_turno_A_Recalculado, Apilado_TMS_turno_B_Recalculado, Apilado_TMH_turno_A + Apilado_TMH_turno_B AS Apilado_TMH_Dia, Apilado_TMS_turno_A_Recalculado + Apilado_TMS_turno_B_Recalculado AS Apilado_TMS_Dia_Recalculado
    FROM    calculo AS c)
   
   SELECT
    r.Fecha,

    /* =========================================================
       HUMEDAD OPERACIONAL PUBLICABLE
       ========================================================= */
    CASE
        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) <= 0
            THEN 0.0
        ELSE r.Humedad_Turno_A
    END AS Humedad_Turno_A,

    CASE
        WHEN COALESCE(r.Apilado_TMH_turno_B, 0) <= 0
            THEN 0.0
        ELSE r.Humedad_Turno_B
    END AS Humedad_Turno_B,

    CASE
        /* No hubo apilado durante el día */
        WHEN COALESCE(r.Apilado_TMH_Dia, 0) <= 0
            THEN 0.0

        /* Solo tuvo apilado el turno A */
        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) <= 0
            THEN r.Humedad_Turno_A

        /* Solo tuvo apilado el turno B */
        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) <= 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) > 0
            THEN r.Humedad_Turno_B

        /* Ambos turnos tuvieron apilado */
        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) > 0
            THEN
                (
                    r.Apilado_TMH_turno_A * r.Humedad_Turno_A
                    +
                    r.Apilado_TMH_turno_B * r.Humedad_Turno_B
                )
                / NULLIF(r.Apilado_TMH_Dia, 0)

        ELSE 0.0
    END AS Humedad_promedio_dia,

    /* =========================================================
       SAL
       ========================================================= */
    r.Sal_turno_A,
    r.Sal_turno_B,
    r.Sal_Dia AS Sal_promedio_dia,

    /* =========================================================
       APILADO TMH
       ========================================================= */
    r.Apilado_TMH_turno_A,
    r.Apilado_TMH_turno_B,
    r.Apilado_TMH_Dia AS Apilado_TMH_promedio_dia,

    /* =========================================================
       APILADO TMS
       ========================================================= */
    r.Apilado_TMS_Dia_Recalculado AS Apilado_TMS_Real,
    r.Apilado_TMS_turno_A_Recalculado,
    r.Apilado_TMS_turno_B_Recalculado,

    /* =========================================================
       TRAZABILIDAD
       ========================================================= */
    r.Factor_Ajuste_Camiones,
    r.TMH_Bruto_A,
    r.TMH_Bruto_B,
    r.TMH_Bruto_Dia,

    r.Sal_Pesometros_TA,
    r.Sal_Pesometros_TB,
    r.Sal_Pesometros_Dia,
    r.Sal_Topografia_Dia,
    r.Sal_Ajustada_Dia,

    r.Flag_Sal_Basica_Valida,
    r.Flag_Sal_Ajuste_Valido,

    /* =========================================================
       FLAG DE APILADO RECALCULADO CON EL TMH NETO
       ========================================================= */
    CASE
        WHEN COALESCE(r.Apilado_TMH_Dia, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_A, 0) >= 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) >= 0
            THEN 1
        ELSE 0
    END AS Flag_Apilado_Valido,

    /* =========================================================
       FLAG DE TMS RECALCULADO
       ========================================================= */
    CASE
        WHEN r.Apilado_TMS_Dia_Recalculado IS NOT NULL
         AND r.Apilado_TMS_Dia_Recalculado > 0
         AND COALESCE(
                 r.Apilado_TMS_turno_A_Recalculado,
                 0
             ) >= 0
         AND COALESCE(
                 r.Apilado_TMS_turno_B_Recalculado,
                 0
             ) >= 0
            THEN 1
        ELSE 0
    END AS Flag_TMS_Valido,

    /* =========================================================
       OBSERVACIÓN OPERACIONAL RECALCULADA
       ========================================================= */
    CASE
        WHEN COALESCE(r.Apilado_TMH_Dia, 0) <= 0
            THEN 'SIN_APILADO_DIA'

        WHEN r.Apilado_TMS_Dia_Recalculado IS NULL
            THEN 'HUMEDAD_NO_DISPONIBLE'

        WHEN COALESCE(
                 r.Apilado_TMS_turno_A_Recalculado,
                 0
             ) < 0
          OR COALESCE(
                 r.Apilado_TMS_turno_B_Recalculado,
                 0
             ) < 0
            THEN 'TMS_NEGATIVO'

        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) <= 0
            THEN 'APILADO_VALIDO_SOLO_TURNO_A'

        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) <= 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) > 0
            THEN 'APILADO_VALIDO_SOLO_TURNO_B'

        WHEN COALESCE(r.Apilado_TMH_turno_A, 0) > 0
         AND COALESCE(r.Apilado_TMH_turno_B, 0) > 0
            THEN 'APILADO_VALIDO_AMBOS_TURNOS'

        ELSE 'APILADO_NO_EVALUABLE'
    END AS Observacion_TMS,

    /* =========================================================
       CHECKS EXISTENTES
       ========================================================= */
    r.Sal_Dia
      - COALESCE(r.Sal_Ajustada_Dia, 0)
        AS Check_Sal_Dia,

    r.Apilado_TMH_Dia
      - (
            r.Apilado_TMH_turno_A
          + r.Apilado_TMH_turno_B
        )
        AS Check_TMH_Dia,

    r.Apilado_TMS_Dia_Recalculado
      - (
            r.Apilado_TMS_turno_A_Recalculado
          + r.Apilado_TMS_turno_B_Recalculado
        )
        AS Check_TMS_Dia,

    r.Apilado_TMS_turno_A_Recalculado
      - r.TMS_Sin_Sal_A
        AS Check_TMS_A_Fuente,

    r.Apilado_TMS_turno_B_Recalculado
      - r.TMS_Sin_Sal_B
        AS Check_TMS_B_Fuente,

    r.Apilado_TMS_Dia_Recalculado
      - r.TMS_Sin_Sal_Dia
        AS Check_TMS_Dia_Fuente

FROM resultado AS r;
GO

-- ============================================================================
-- inventar_SpcHidr.v_reporte_diario_emulado_excel (VIEW)
-- Ultima modificacion: 2026-05-19 17:08:29.950000
-- ============================================================================
CREATE   VIEW [inventar_SpcHidr].[v_reporte_diario_emulado_excel]
AS
WITH base AS (
    SELECT
        Fecha        = r.fecha_turno,
        Turno        = r.turno,
        torre_id     = r.torre,
        Torre        = CASE r.torre
                           WHEN 1 THEN 'T1'
                           WHEN 2 THEN 'T2'
                           WHEN 3 THEN 'SRR'
                           ELSE NULL
                       END,
        ts_ini          = r.ts_ini,
        ts_fin          = r.ts_fin,
        flag_arrastre   = r.flag_arrastre,
        duracion_min    = r.duracion_min,
        comentario      = r.comentario,
        nombre_archivo  = r.nombre_archivo,
        rn = ROW_NUMBER() OVER (
                 PARTITION BY r.fecha_turno, r.turno, r.torre, r.ts_ini, r.ts_fin
                 ORDER BY (SELECT NULL)
             )
    FROM inventar_SpcHidr.v_bitacora_rangos r
    WHERE r.torre IN (1, 2, 3)
),
base_dedup AS (
    SELECT
        Fecha, Turno, torre_id, Torre,
        ts_ini, ts_fin,
        flag_arrastre, duracion_min, comentario, nombre_archivo
    FROM base
    WHERE rn = 1
),
metricas AS (
    SELECT
        b.Fecha, b.Turno, b.Torre, b.ts_ini, b.ts_fin,
        b.torre_id, b.flag_arrastre, b.duracion_min,
        b.comentario, b.nombre_archivo,
        t.toneladas_intervalo,
        h.HE_horas,
        TPH = CASE
                  WHEN h.HE_horas IS NULL OR h.HE_horas <= 0                     THEN NULL
                  WHEN t.toneladas_intervalo IS NULL OR t.toneladas_intervalo < 0 THEN NULL
                  ELSE t.toneladas_intervalo / h.HE_horas
              END
    FROM base_dedup b
    LEFT JOIN inventar_SpcHidr.v_ton_por_intervalo_excel t
           ON t.dia_op   = b.Fecha
          AND t.turno_op = b.Turno
          AND t.Torre    = b.Torre
          AND t.ts_ini   = b.ts_ini
          AND t.ts_fin   = b.ts_fin
    LEFT JOIN inventar_SpcHidr.v_he_10s_por_intervalo_excel h
           ON h.dia_op   = b.Fecha
          AND h.turno_op = b.Turno
          AND h.Torre    = b.Torre
          AND h.ts_ini   = b.ts_ini
          AND h.ts_fin   = b.ts_fin
),
lab_asignada AS (
    SELECT
        b.Fecha, b.Turno, b.Torre, b.ts_ini, b.ts_fin,
        l.CuT_global, l.CuS_Global, l.Fe_Global,
        l.Humedad_Prom_Pct, l.RetParcial_2P, l.RetParcial_1P,
        rn = ROW_NUMBER() OVER (
                 PARTITION BY b.Fecha, b.Turno, b.Torre, b.ts_ini, b.ts_fin
                 ORDER BY ABS(DATEDIFF(SECOND, l.fecha_muestra_min, b.ts_fin)) ASC,
                          l.fecha_muestra_min DESC
             )
    FROM base_dedup b
    LEFT JOIN inventar_SpcHidr.v_informe_tm_lab_norm l
           ON l.Torre             = b.Torre
          AND l.fecha_muestra_min >  b.ts_ini
          AND l.fecha_muestra_min <= b.ts_fin
)
SELECT
    m.Fecha,
    m.Turno,
    m.Torre,
    Ton_Real     = m.toneladas_intervalo,
    Horas_Reales = m.HE_horas,
    TPH_Real     = m.TPH,
    Factor_Masa  = CASE
                       WHEN m.TPH IS NULL THEN NULL
                       WHEN m.TPH >= 1875 THEN 1.0
                       ELSE m.TPH / 1875.0
                   END,
    KPI_Representatividad = CASE
                                WHEN la.rn IS NULL THEN 0.0
                                WHEN m.TPH IS NULL THEN 0.0
                                WHEN m.TPH >= 1875 THEN 1.0
                                ELSE m.TPH / 1875.0
                            END,
    Ley_CuT  = la.CuT_global,
    Ley_CuS  = la.CuS_Global,
    Ley_Fe   = la.Fe_Global,
    Humedad  = la.Humedad_Prom_Pct,
    Ret2P    = la.RetParcial_2P,
    Ret1P    = la.RetParcial_1P,
    Estado   = CASE WHEN la.rn = 1 THEN 'Con Muestra' ELSE 'Sin Muestra' END,
    m.ts_ini,
    m.ts_fin,
    m.torre_id,
    m.flag_arrastre,
    m.duracion_min,
    m.comentario,
    m.nombre_archivo
FROM metricas m
LEFT JOIN lab_asignada la
       ON la.Fecha  = m.Fecha
      AND la.Turno  = m.Turno
      AND la.Torre  = m.Torre
      AND la.ts_ini = m.ts_ini
      AND la.ts_fin = m.ts_fin
      AND la.rn     = 1;
GO

-- ============================================================================
-- inventar_SpcHidr.v_reporte_diario_humedad_test (VIEW)
-- Ultima modificacion: 2026-08-04 14:24:53.767000
-- ============================================================================
/* ================================================================
   ALTER inventar_SpcHidr.v_reporte_diario_humedad_test
   Fix de performance -- NO cambia ninguna logica de calculo.
   ----------------------------------------------------------------
   Diagnostico (ver memoria de sesion, fragmento entregado por el
   usuario via OBJECT_DEFINITION): la CTE "hum" de esta vista lee
   inventar_SpcHidr.Informe_TM_lab COMPLETO, sin ningun filtro de
   fecha:

       FROM inventar_SpcHidr.Informe_TM_lab AS l
       WHERE l.Humedad_Prom_Pct IS NOT NULL
       GROUP BY CAST(l.Fecha AS date), l.Torre, l.Turno

   Esta CTE alimenta "candidatos", que a su vez se usa dentro de un
   OUTER APPLY TOP(1) ... ORDER BY FechaTurno_Origen DESC ejecutado
   UNA VEZ POR CADA fila de "periodos" (fecha x turno). Como "hum"
   nunca se acota, cada una de esas busquedas vuelve a escanear
   Informe_TM_lab entero -- esto explica los scan counts medidos
   (5.682 y 39.632 en distintos puntos de sp_reporte_turno_emision_test,
   ya que esta vista se usa indirectamente via
   v_humedad_inventario_test -> v_inventario_chancado_archive_test).

   FIX: agregar un filtro de fecha SARGABLE (columna cruda l.Fecha,
   sin envolver en funciones antes del filtro) a la CTE "hum". Mismo
   criterio de ventana que en v_inventario_chancado_archive_test:
   400 dias hacia atras desde GETDATE(), consistente con el rango de
   trabajo activo del proyecto (enero 2026 en adelante). Ver esa
   misma limitacion documentada en
   alter_v_inventario_chancado_archive_test_fix_performance.sql --
   aplica igual aca.

   Todo lo demas (base, hum_rep, candidatos, periodos,
   humedad_periodo, humedad_turnos, calculos, controles, SELECT
   final) queda identico al original.
================================================================ */
CREATE   VIEW
    [inventar_SpcHidr].[v_reporte_diario_humedad_test]
AS
WITH base AS
(
    SELECT
        v.Fecha,
        v.Humedad_TM1,
        v.Humedad_TM2,
        v.Fecha_Humedad_TM1,
        v.Torre_Humedad_TM1,
        v.Turno_Humedad_TM1,
        v.Fuente_Humedad_TM1,
        v.Fecha_Humedad_TM2,
        v.Torre_Humedad_TM2,
        v.Turno_Humedad_TM2,
        v.Fuente_Humedad_TM2,
        v.TMH_TM1_Con_Sal_SRR_A AS TMH_TM1_A,
        v.TMH_TM2_Con_Sal_SRR_A AS TMH_TM2_A,
        v.TMH_TM1_Con_Sal_SRR_B AS TMH_TM1_B,
        v.TMH_TM2_Con_Sal_SRR_B AS TMH_TM2_B,
        v.Humedad_Equivalente_Dia,
        v.TMS_TM1_Con_Sal_SRR_A AS TMS_TM1_A,
        v.TMS_TM2_Con_Sal_SRR_A AS TMS_TM2_A,
        v.TMS_TM1_Con_Sal_SRR_B AS TMS_TM1_B,
        v.TMS_TM2_Con_Sal_SRR_B AS TMS_TM2_B,
        v.TMS_Total_Con_Sal_SRR_A,
        v.TMS_Total_Con_Sal_SRR_B,
        v.TMS_Total_Con_Sal_SRR_Dia,
        v.Flag_Apilado_Valido,
        v.Flag_TMS_Valido,
        v.Observacion_TMS
    FROM inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test AS v
),
/* ============================================================
   HUMEDADES REPRESENTATIVAS PARA RESPALDO DE TURNOS SIN TMH
   Esta seccion no recalcula el TMS.
   Solo permite mostrar la humedad vigente cuando el turno
   tiene TMH igual a cero.
   FILTRO DE FECHA AGREGADO (fix de performance) -- ver encabezado.
   ============================================================ */
hum AS
(
    SELECT
        CAST(l.Fecha AS date) AS Fecha,
        l.Torre,
        l.Turno,
        AVG(CAST(l.Humedad_Prom_Pct AS float)) AS Humedad_Prom_Pct
    FROM inventar_SpcHidr.Informe_TM_lab AS l
    WHERE l.Humedad_Prom_Pct IS NOT NULL
      AND l.Fecha >= DATEADD(DAY, -400, CAST(GETDATE() AS date))
    GROUP BY
        CAST(l.Fecha AS date),
        l.Torre,
        l.Turno
),
hum_rep AS
(
    SELECT
        h.Fecha,
        h.Torre,
        h.Turno,
        h.Humedad_Prom_Pct,
        CASE
            WHEN h.Torre = 'T1' AND h.Turno = 'A' THEN r.TM1_TurnoA_Fisico
            WHEN h.Torre = 'T1' AND h.Turno = 'B' THEN r.TM1_TurnoB_Fisico
            WHEN h.Torre = 'T2' AND h.Turno = 'A' THEN r.TM2_TurnoA_Fisico
            WHEN h.Torre = 'T2' AND h.Turno = 'B' THEN r.TM2_TurnoB_Fisico
        END AS Representatividad_Fisica
    FROM hum AS h
    LEFT JOIN inventar_SpcHidr.v_representatividad_diaria_calculada AS r
        ON r.Dia = h.Fecha
),
candidatos AS
(
    SELECT
        h.Fecha,
        h.Torre,
        h.Turno,
        h.Humedad_Prom_Pct,
        h.Representatividad_Fisica,
        DATEADD(
            HOUR,
            CASE WHEN h.Turno = 'A' THEN 8 ELSE 20 END,
            CAST(h.Fecha AS datetime2(0))
        ) AS FechaTurno_Origen,
        CAST('HUMEDAD_REPRESENTATIVA' AS varchar(30)) AS Fuente
    FROM hum_rep AS h
    WHERE h.Humedad_Prom_Pct IS NOT NULL
      AND h.Representatividad_Fisica >= 0.75

    UNION ALL

    SELECT
        CAST(s.fecha_origen AS date),
        CAST(s.torre AS varchar(20)),
        CAST(NULL AS varchar(10)),
        CAST(s.humedad_pct AS float),
        CAST(1.0 AS float),
        CAST(s.fecha_origen AS datetime2(0)),
        CAST('HUMEDAD_INICIAL_PERIODO' AS varchar(30))
    FROM inventar_SpcHidr.humedad_inicial_tm_periodo AS s
),
/* ============================================================
   EXPANSION A FECHA + TURNO
   ============================================================ */
periodos AS
(
    SELECT
        b.Fecha,
        CAST('A' AS varchar(1)) AS Turno,
        DATEADD(HOUR, 8, CAST(b.Fecha AS datetime2(0))) AS FechaTurno_Objetivo,
        b.TMH_TM1_A,
        b.TMH_TM2_A,
        COALESCE(b.TMH_TM1_A, 0) + COALESCE(b.TMH_TM2_A, 0) AS TMH_Total_Turno,
        b.TMS_Total_Con_Sal_SRR_A AS TMS_Total_Turno
    FROM base AS b

    UNION ALL

    SELECT
        b.Fecha,
        CAST('B' AS varchar(1)),
        DATEADD(HOUR, 20, CAST(b.Fecha AS datetime2(0))),
        b.TMH_TM1_B,
        b.TMH_TM2_B,
        COALESCE(b.TMH_TM1_B, 0) + COALESCE(b.TMH_TM2_B, 0),
        b.TMS_Total_Con_Sal_SRR_B
    FROM base AS b
),
/* ============================================================
   HUMEDAD EFECTIVAMENTE UTILIZADA EN CADA TURNO
   Cuando existe TMH: se despeja desde el TMS realmente calculado.
   Cuando TMH = 0: se muestra la ultima humedad representativa
   vigente.
   ============================================================ */
humedad_periodo AS
(
    SELECT
        p.Fecha,
        p.Turno,
        p.TMH_TM1_A,
        p.TMH_TM2_A,
        p.TMH_Total_Turno,
        p.TMS_Total_Turno,
        CASE
            WHEN p.TMH_Total_Turno = 0 THEN vigente.Humedad_Prom_Pct
            WHEN p.TMS_Total_Turno IS NULL THEN NULL
            ELSE 100.0 * (1.0 - p.TMS_Total_Turno / NULLIF(p.TMH_Total_Turno, 0))
        END AS Humedad_Turno
    FROM periodos AS p
    OUTER APPLY
    (
        SELECT TOP (1)
            c.Humedad_Prom_Pct
        FROM candidatos AS c
        WHERE c.FechaTurno_Origen <= p.FechaTurno_Objetivo
        ORDER BY
            c.FechaTurno_Origen DESC,
            CASE
                WHEN c.Torre = 'T2' THEN 1
                WHEN c.Torre = 'T1' THEN 2
                ELSE 3
            END
    ) AS vigente
),
/* ============================================================
   PIVOT DIARIO
   ============================================================ */
humedad_turnos AS
(
    SELECT
        Fecha,
        MAX(CASE WHEN Turno = 'A' THEN Humedad_Turno END) AS Humedad_Turno_A,
        MAX(CASE WHEN Turno = 'B' THEN Humedad_Turno END) AS Humedad_Turno_B
    FROM humedad_periodo
    GROUP BY Fecha
),
calculos AS
(
    SELECT
        b.*,
        h.Humedad_Turno_A,
        h.Humedad_Turno_B,
        COALESCE(b.TMH_TM1_A, 0) + COALESCE(b.TMH_TM2_A, 0) AS TMH_Total_A,
        COALESCE(b.TMH_TM1_B, 0) + COALESCE(b.TMH_TM2_B, 0) AS TMH_Total_B,
        COALESCE(b.TMH_TM1_A, 0) + COALESCE(b.TMH_TM2_A, 0)
        + COALESCE(b.TMH_TM1_B, 0) + COALESCE(b.TMH_TM2_B, 0) AS TMH_Total_Dia
    FROM base AS b
    LEFT JOIN humedad_turnos AS h
        ON h.Fecha = b.Fecha
),
controles AS
(
    SELECT
        c.*,
        CASE
            WHEN c.TMH_Total_Dia = 0 THEN 0
            WHEN c.Humedad_Turno_A IS NULL OR c.Humedad_Turno_B IS NULL THEN NULL
            ELSE
                (c.TMH_Total_A * c.Humedad_Turno_A + c.TMH_Total_B * c.Humedad_Turno_B)
                / NULLIF(c.TMH_Total_Dia, 0)
        END AS Humedad_Dia_Recalculada,
        CASE
            WHEN c.Humedad_Turno_A IS NULL THEN NULL
            ELSE c.TMH_Total_A * (1.0 - c.Humedad_Turno_A / 100.0)
        END AS TMS_Recalculado_A,
        CASE
            WHEN c.Humedad_Turno_B IS NULL THEN NULL
            ELSE c.TMH_Total_B * (1.0 - c.Humedad_Turno_B / 100.0)
        END AS TMS_Recalculado_B
    FROM calculos AS c
)
SELECT
    Fecha,
    Humedad_Turno_A,
    Humedad_Turno_B,
    Humedad_Equivalente_Dia AS Humedad_promedio_dia,
    Humedad_TM1,
    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,
    Humedad_TM2,
    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2,
    TMH_TM1_A,
    TMH_TM2_A,
    TMH_Total_A,
    TMH_TM1_B,
    TMH_TM2_B,
    TMH_Total_B,
    TMH_Total_Dia,
    Humedad_Dia_Recalculada,
    Humedad_Dia_Recalculada - Humedad_Equivalente_Dia AS Check_Humedad_Dia,
    TMS_Recalculado_A,
    TMS_Total_Con_Sal_SRR_A AS TMS_Fuente_A,
    TMS_Recalculado_A - TMS_Total_Con_Sal_SRR_A AS Check_TMS_A,
    TMS_Recalculado_B,
    TMS_Total_Con_Sal_SRR_B AS TMS_Fuente_B,
    TMS_Recalculado_B - TMS_Total_Con_Sal_SRR_B AS Check_TMS_B,
    TMS_Total_Con_Sal_SRR_Dia AS TMS_Fuente_Dia,
    Flag_Apilado_Valido,
    Flag_TMS_Valido,
    Observacion_TMS
FROM controles;
GO

-- ============================================================================
-- inventar_SpcHidr.v_representatividad_diaria_calculada (VIEW)
-- Ultima modificacion: 2026-07-11 13:30:22.050000
-- ============================================================================
CREATE VIEW inventar_SpcHidr.v_representatividad_diaria_calculada
AS

WITH representatividad_t12 AS
(
    SELECT
        r.Fecha AS Dia,

        MAX(
            CASE
                WHEN r.Torre = 'T1'
                 AND r.Turno = 'A'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Quimico IS NULL
                          OR pt.PesoTeo_Quimico <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico IS NULL
                          OR pr.PesoReal_Quimico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico >= 1
                            THEN 1.0

                        ELSE pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico
                    END
            END
        ) AS TM1_TurnoA_Quimico,

        MAX(
            CASE
                WHEN r.Torre = 'T1'
                 AND r.Turno = 'A'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Fisico IS NULL
                          OR pt.PesoTeo_Fisico <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico IS NULL
                          OR pr.PesoReal_Fisico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico >= 1
                            THEN 1.0

                        ELSE pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico
                    END
            END
        ) AS TM1_TurnoA_Fisico,

        MAX(
            CASE
                WHEN r.Torre = 'T1'
                 AND r.Turno = 'B'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Quimico IS NULL
                          OR pt.PesoTeo_Quimico <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico IS NULL
                          OR pr.PesoReal_Quimico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico >= 1
                            THEN 1.0

                        ELSE pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico
                    END
            END
        ) AS TM1_TurnoB_Quimico,

        MAX(
            CASE
                WHEN r.Torre = 'T1'
                 AND r.Turno = 'B'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Fisico IS NULL
                          OR pt.PesoTeo_Fisico <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico IS NULL
                          OR pr.PesoReal_Fisico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico >= 1
                            THEN 1.0

                        ELSE pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico
                    END
            END
        ) AS TM1_TurnoB_Fisico,

        MAX(
            CASE
                WHEN r.Torre = 'T2'
                 AND r.Turno = 'A'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Quimico IS NULL
                          OR pt.PesoTeo_Quimico <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico IS NULL
                          OR pr.PesoReal_Quimico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico >= 1
                            THEN 1.0

                        ELSE pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico
                    END
            END
        ) AS TM2_TurnoA_Quimico,

        MAX(
            CASE
                WHEN r.Torre = 'T2'
                 AND r.Turno = 'A'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Fisico IS NULL
                          OR pt.PesoTeo_Fisico <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico IS NULL
                          OR pr.PesoReal_Fisico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico >= 1
                            THEN 1.0

                        ELSE pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico
                    END
            END
        ) AS TM2_TurnoA_Fisico,

        MAX(
            CASE
                WHEN r.Torre = 'T2'
                 AND r.Turno = 'B'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Quimico IS NULL
                          OR pt.PesoTeo_Quimico <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico IS NULL
                          OR pr.PesoReal_Quimico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico >= 1
                            THEN 1.0

                        ELSE pr.PesoReal_Quimico
                             / pt.PesoTeo_Quimico
                    END
            END
        ) AS TM2_TurnoB_Quimico,

        MAX(
            CASE
                WHEN r.Torre = 'T2'
                 AND r.Turno = 'B'
                THEN
                    CASE
                        WHEN pt.PesoTeo_Fisico IS NULL
                          OR pt.PesoTeo_Fisico <= 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico IS NULL
                          OR pr.PesoReal_Fisico < 0
                            THEN NULL

                        WHEN pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico >= 1
                            THEN 1.0

                        ELSE pr.PesoReal_Fisico
                             / pt.PesoTeo_Fisico
                    END
            END
        ) AS TM2_TurnoB_Fisico

    FROM inventar_SpcHidr.v_reporte_diario_emulado_excel AS r

    LEFT JOIN inventar_SpcHidr.v_peso_real_torre_turno_excel AS pr
        ON  pr.Torre = r.Torre
        AND pr.Fecha = r.Fecha
        AND pr.Turno = r.Turno

    LEFT JOIN inventar_SpcHidr.v_peso_teorico_turno_torre_excel AS pt
        ON  pt.Torre = r.Torre
        AND pt.Fecha = r.Fecha
        AND pt.Turno = r.Turno

    WHERE r.Torre IN ('T1', 'T2')

    GROUP BY
        r.Fecha
),

representatividad_srr AS
(
    SELECT
        Fecha AS Dia,

        CAST(
            MAX(
                CASE
                    WHEN Turno = 'A'
                        THEN Representatividad_Quimica
                END
            )
            AS float
        ) AS SRR_TurnoA_Quimico,

        CAST(
            MAX(
                CASE
                    WHEN Turno = 'A'
                        THEN Representatividad_Fisica
                END
            )
            AS float
        ) AS SRR_TurnoA_Fisico,

        CAST(
            MAX(
                CASE
                    WHEN Turno = 'B'
                        THEN Representatividad_Quimica
                END
            )
            AS float
        ) AS SRR_TurnoB_Quimico,

        CAST(
            MAX(
                CASE
                    WHEN Turno = 'B'
                        THEN Representatividad_Fisica
                END
            )
            AS float
        ) AS SRR_TurnoB_Fisico

    FROM inventar_SpcHidr.v_representatividad_srr_turno_calculada

    GROUP BY
        Fecha
)

SELECT
    t12.Dia,

    t12.TM1_TurnoA_Quimico,
    t12.TM1_TurnoA_Fisico,
    t12.TM1_TurnoB_Quimico,
    t12.TM1_TurnoB_Fisico,

    t12.TM2_TurnoA_Quimico,
    t12.TM2_TurnoA_Fisico,
    t12.TM2_TurnoB_Quimico,
    t12.TM2_TurnoB_Fisico,

    srr.SRR_TurnoA_Quimico,
    srr.SRR_TurnoA_Fisico,
    srr.SRR_TurnoB_Quimico,
    srr.SRR_TurnoB_Fisico

FROM representatividad_t12 AS t12

LEFT JOIN representatividad_srr AS srr
    ON srr.Dia = t12.Dia;
GO

-- ============================================================================
-- inventar_SpcHidr.v_representatividad_srr_turno_calculada (VIEW)
-- Ultima modificacion: 2026-07-11 13:19:23.893000
-- ============================================================================
CREATE   VIEW
    inventar_SpcHidr.v_representatividad_srr_turno_calculada
AS

WITH base AS
(
    SELECT
        Fecha =
            CAST(r.Fecha AS date),

        Turno =
            CAST(r.Turno AS varchar(1)),

        Torre =
            CAST('SRR' AS varchar(10)),

        r.Ton_Real,
        r.Horas_Reales,
        r.TPH_Real,
        r.Factor_Masa,
        r.ts_ini,
        r.ts_fin,

        e.Apilado_TMH_Base,
        e.Flag_Apilado_Valido,
        e.Turno_Evaluable,

        Fecha_Registro_Peso =
            pr.Fecha,

        pr.PesoReal_Quimico,
        pr.PesoReal_Fisico,

        pt.Fraccion_Muestreo,
        pt.PesoBase_Quimico_12h,
        pt.PesoBase_Fisico_12h,
        pt.PesoTeo_Quimico,
        pt.PesoTeo_Fisico

    FROM inventar_SpcHidr.v_reporte_diario_emulado_excel AS r

    LEFT JOIN
        inventar_SpcHidr.v_estado_apilado_turno_representatividad AS e
        ON  e.Fecha = r.Fecha
        AND e.Turno = r.Turno

    LEFT JOIN
        inventar_SpcHidr.v_peso_real_torre_turno_excel AS pr
        ON  pr.Fecha = r.Fecha
        AND pr.Turno = r.Turno
        AND pr.Torre = r.Torre

    LEFT JOIN
        inventar_SpcHidr.v_peso_teorico_turno_torre_excel AS pt
        ON  pt.Fecha = r.Fecha
        AND pt.Turno = r.Turno
        AND pt.Torre = r.Torre

    WHERE r.Torre = 'SRR'
),

clasificacion AS
(
    SELECT
        *,

        Estado_SRR =
            CASE
                WHEN Turno_Evaluable IS NULL
                    THEN 'SIN_ESTADO_EVALUABILIDAD'

                WHEN Turno_Evaluable = 0
                    THEN 'NO_EVALUABLE'

                WHEN COALESCE(Ton_Real, 0) <= 0
                  OR COALESCE(Horas_Reales, 0) <= 0
                  OR COALESCE(PesoTeo_Quimico, 0) <= 0
                  OR COALESCE(PesoTeo_Fisico, 0) <= 0
                    THEN 'EVALUABLE_SIN_FLUJO_SRR'

                WHEN Fecha_Registro_Peso IS NULL
                    THEN 'EVALUABLE_SIN_REGISTRO_PESO_REAL'

                WHEN PesoReal_Quimico < 0
                  OR PesoReal_Fisico < 0
                    THEN 'EVALUABLE_PESO_REAL_INVALIDO'

                WHEN COALESCE(PesoReal_Quimico, 0) <= 0
                 AND COALESCE(PesoReal_Fisico, 0) <= 0
                    THEN 'EVALUABLE_SIN_MUESTRA'

                WHEN COALESCE(PesoReal_Quimico, 0) <= 0
                  OR COALESCE(PesoReal_Fisico, 0) <= 0
                    THEN 'EVALUABLE_MUESTRA_PARCIAL'

                ELSE 'EVALUABLE_CON_MUESTRA'
            END

    FROM base
),

ratios AS
(
    SELECT
        *,

        Representatividad_Quimica =
            CAST
            (
                CASE
                    WHEN Turno_Evaluable IS NULL
                        THEN NULL

                    WHEN Turno_Evaluable = 0
                        THEN NULL

                    WHEN COALESCE(Ton_Real, 0) <= 0
                      OR COALESCE(Horas_Reales, 0) <= 0
                      OR COALESCE(PesoTeo_Quimico, 0) <= 0
                        THEN NULL

                    WHEN Fecha_Registro_Peso IS NULL
                        THEN NULL

                    WHEN PesoReal_Quimico < 0
                        THEN NULL

                    WHEN
                        COALESCE(PesoReal_Quimico, 0)
                        / NULLIF(PesoTeo_Quimico, 0) >= 1
                        THEN 1.0

                    ELSE
                        COALESCE(PesoReal_Quimico, 0)
                        / NULLIF(PesoTeo_Quimico, 0)
                END
                AS decimal(18,10)
            ),

        Representatividad_Fisica =
            CAST
            (
                CASE
                    WHEN Turno_Evaluable IS NULL
                        THEN NULL

                    WHEN Turno_Evaluable = 0
                        THEN NULL

                    WHEN COALESCE(Ton_Real, 0) <= 0
                      OR COALESCE(Horas_Reales, 0) <= 0
                      OR COALESCE(PesoTeo_Fisico, 0) <= 0
                        THEN NULL

                    WHEN Fecha_Registro_Peso IS NULL
                        THEN NULL

                    WHEN PesoReal_Fisico < 0
                        THEN NULL

                    WHEN
                        COALESCE(PesoReal_Fisico, 0)
                        / NULLIF(PesoTeo_Fisico, 0) >= 1
                        THEN 1.0

                    ELSE
                        COALESCE(PesoReal_Fisico, 0)
                        / NULLIF(PesoTeo_Fisico, 0)
                END
                AS decimal(18,10)
            )

    FROM clasificacion
)

SELECT
    Fecha,
    Turno,
    Torre,

    Ton_Real,
    Horas_Reales,
    TPH_Real,
    Factor_Masa,
    ts_ini,
    ts_fin,

    Apilado_TMH_Base,
    Flag_Apilado_Valido,
    Turno_Evaluable,

    PesoReal_Quimico,
    PesoReal_Fisico,

    Fraccion_Muestreo,
    PesoBase_Quimico_12h,
    PesoBase_Fisico_12h,
    PesoTeo_Quimico,
    PesoTeo_Fisico,

    Representatividad_Quimica,
    Representatividad_Fisica,

    Muestra_Quimica_Representativa =
        CAST
        (
            CASE
                WHEN Representatividad_Quimica IS NULL
                    THEN NULL

                WHEN Representatividad_Quimica >= 0.75
                    THEN 1

                ELSE 0
            END
            AS bit
        ),

    Muestra_Fisica_Representativa =
        CAST
        (
            CASE
                WHEN Representatividad_Fisica IS NULL
                    THEN NULL

                WHEN Representatividad_Fisica >= 0.75
                    THEN 1

                ELSE 0
            END
            AS bit
        ),

    Estado_SRR

FROM ratios;
GO

-- ============================================================================
-- inventar_SpcHidr.v_sal_ajustada (VIEW)
-- Ultima modificacion: 2026-05-28 19:21:46.190000
-- ============================================================================
CREATE   VIEW inventar_SpcHidr.v_sal_ajustada AS

WITH sal_marcas AS (
    SELECT DISTINCT
        CAST(fecha_turno AS date) AS Fecha,

        CAST(DATEADD(HOUR, 8, CAST(CAST(fecha_turno AS date) AS datetime2)) AS datetime2)
            AS ts_08_dia,

        CAST(DATEADD(HOUR, 20, CAST(CAST(fecha_turno AS date) AS datetime2)) AS datetime2)
            AS ts_20_dia,

        CAST(DATEADD(HOUR, 8, DATEADD(DAY, 1, CAST(CAST(fecha_turno AS date) AS datetime2))) AS datetime2)
            AS ts_08_dia_siguiente

    FROM inventar_SpcHidr.datos_filtrados
),

sal_base AS (
    SELECT
        m.Fecha,

        CAST(t08.cv201_tot AS float)  AS CV201_08,
        CAST(t20.cv201_tot AS float)  AS CV201_20,
        CAST(t08s.cv201_tot AS float) AS CV201_08_sig,

        CAST(t08.cv202_tot AS float)  AS CV202_08,
        CAST(t20.cv202_tot AS float)  AS CV202_20,
        CAST(t08s.cv202_tot AS float) AS CV202_08_sig

    FROM sal_marcas m

    LEFT JOIN inventar_SpcHidr.datos_filtrados t08
        ON t08.fecha_final = m.ts_08_dia

    LEFT JOIN inventar_SpcHidr.datos_filtrados t20
        ON t20.fecha_final = m.ts_20_dia

    LEFT JOIN inventar_SpcHidr.datos_filtrados t08s
        ON t08s.fecha_final = m.ts_08_dia_siguiente
),

sal_calc AS (
    SELECT
        Fecha,

        (CV201_20 - CV201_08) / 1000.0 AS CV201_TA_Bruto,
        (CV201_08_sig - CV201_20) / 1000.0 AS CV201_TB_Bruto,

        (CV202_20 - CV202_08) / 1000.0 AS CV202_TA_Bruto,
        (CV202_08_sig - CV202_20) / 1000.0 AS CV202_TB_Bruto

    FROM sal_base
),

sal_validacion AS (
    SELECT
        c.*,

        CASE
            WHEN CV201_TA_Bruto IS NULL THEN 0
            WHEN CV201_TB_Bruto IS NULL THEN 0
            WHEN CV202_TA_Bruto IS NULL THEN 0
            WHEN CV202_TB_Bruto IS NULL THEN 0

            WHEN CV201_TA_Bruto < 0 THEN 0
            WHEN CV201_TB_Bruto < 0 THEN 0
            WHEN CV202_TA_Bruto < 0 THEN 0
            WHEN CV202_TB_Bruto < 0 THEN 0

            ELSE 1
        END AS Flag_Sal_Basica_Valida

    FROM sal_calc c
),

sal_total AS (
    SELECT
        Fecha,

        CASE WHEN Flag_Sal_Basica_Valida = 1 THEN CV201_TA_Bruto ELSE 0 END AS CV201_TA,
        CASE WHEN Flag_Sal_Basica_Valida = 1 THEN CV201_TB_Bruto ELSE 0 END AS CV201_TB,
        CASE WHEN Flag_Sal_Basica_Valida = 1 THEN CV202_TA_Bruto ELSE 0 END AS CV202_TA,
        CASE WHEN Flag_Sal_Basica_Valida = 1 THEN CV202_TB_Bruto ELSE 0 END AS CV202_TB,

        Flag_Sal_Basica_Valida

    FROM sal_validacion
),

sal_ajuste_base AS (
    SELECT
        s.Fecha,

        s.CV201_TA,
        s.CV201_TB,
        s.CV202_TA,
        s.CV202_TB,

        s.CV201_TA + s.CV202_TA AS Sal_Pesometros_TA,
        s.CV201_TB + s.CV202_TB AS Sal_Pesometros_TB,

        s.CV201_TA
      + s.CV201_TB
      + s.CV202_TA
      + s.CV202_TB AS Sal_Pesometros_Dia,

        CAST(topo.tonelaje_topografia AS float) AS Sal_Topografia_Dia,

        s.Flag_Sal_Basica_Valida,

        CASE
            WHEN s.Flag_Sal_Basica_Valida = 0 THEN 0
            WHEN topo.tonelaje_topografia IS NULL THEN 0
            WHEN topo.tonelaje_topografia <= 0 THEN 0

            WHEN s.CV201_TA + s.CV202_TA <= 0 THEN 0
            WHEN s.CV201_TB + s.CV202_TB <= 0 THEN 0

            WHEN s.CV201_TA
               + s.CV201_TB
               + s.CV202_TA
               + s.CV202_TB <= 0 THEN 0

            ELSE 1
        END AS Flag_Sal_Ajuste_Valido

    FROM sal_total s

    LEFT JOIN inventar_SpcHidr.topografia_sal topo
        ON topo.fecha = s.Fecha
)

SELECT
    Fecha,

    CV201_TA,
    CV201_TB,
    CV202_TA,
    CV202_TB,

    Sal_Pesometros_TA,
    Sal_Pesometros_TB,
    Sal_Pesometros_Dia,

    Sal_Topografia_Dia,

    Flag_Sal_Basica_Valida,
    Flag_Sal_Ajuste_Valido,

    CASE
        WHEN Flag_Sal_Ajuste_Valido = 1 THEN
            Sal_Pesometros_TA
            * Sal_Topografia_Dia
            / NULLIF(Sal_Pesometros_Dia, 0)
        ELSE 0
    END AS Sal_Ajustada_TA,

    CASE
        WHEN Flag_Sal_Ajuste_Valido = 1 THEN
            Sal_Pesometros_TB
            * Sal_Topografia_Dia
            / NULLIF(Sal_Pesometros_Dia, 0)
        ELSE 0
    END AS Sal_Ajustada_TB,

    CASE
        WHEN Flag_Sal_Ajuste_Valido = 1 THEN
            Sal_Topografia_Dia
        ELSE 0
    END AS Sal_Ajustada_Dia

FROM sal_ajuste_base;
GO

-- ============================================================================
-- inventar_SpcHidr.v_sal_ajustada_operacional_test (VIEW)
-- Ultima modificacion: 2026-07-29 13:20:09.397000
-- ============================================================================

CREATE   VIEW
[inventar_SpcHidr].[v_sal_ajustada_operacional_test]
AS

WITH base AS
(
    SELECT
        s.Fecha,

        s.CV201_TA,
        s.CV201_TB,
        s.CV202_TA,
        s.CV202_TB,

        s.Sal_Pesometros_TA,
        s.Sal_Pesometros_TB,
        s.Sal_Pesometros_Dia,

        s.Sal_Topografia_Dia,

        s.Flag_Sal_Basica_Valida,

        s.Flag_Sal_Ajuste_Valido
            AS Flag_Sal_Ajuste_Valido_Origen,

        s.Sal_Ajustada_TA
            AS Sal_Ajustada_TA_Origen,

        s.Sal_Ajustada_TB
            AS Sal_Ajustada_TB_Origen,

        s.Sal_Ajustada_Dia
            AS Sal_Ajustada_Dia_Origen,

        t.TMH_Total_Con_Sal_SRR_A
            AS TMH_Bruto_A,

        t.TMH_Total_Con_Sal_SRR_B
            AS TMH_Bruto_B

    FROM [inventar_SpcHidr].[v_sal_ajustada] s

    LEFT JOIN
        [inventar_SpcHidr].
        [v_apilado_tms_con_sal_srr_reporte_test] t
        ON t.Fecha = s.Fecha
),

calculo AS
(
    SELECT
        b.*,

        CASE
            WHEN COALESCE(b.Sal_Topografia_Dia, 0) <= 0
                THEN 0

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 0

            /* Solo A tuvo apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN b.Sal_Topografia_Dia

            /* Solo B tuvo apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN 0

            /* Ambos turnos tuvieron apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
             AND
                 COALESCE(b.Sal_Pesometros_TA, 0)
               + COALESCE(b.Sal_Pesometros_TB, 0) > 0
                THEN
                    b.Sal_Topografia_Dia
                    * COALESCE(b.Sal_Pesometros_TA, 0)
                    /
                    NULLIF
                    (
                        COALESCE(b.Sal_Pesometros_TA, 0)
                      + COALESCE(b.Sal_Pesometros_TB, 0),
                        0
                    )

            ELSE 0
        END AS Sal_Ajustada_TA_Candidata,

        CASE
            WHEN COALESCE(b.Sal_Topografia_Dia, 0) <= 0
                THEN 0

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 0

            /* Solo A tuvo apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 0

            /* Solo B tuvo apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN b.Sal_Topografia_Dia

            /* Ambos turnos tuvieron apilado */
            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
             AND
                 COALESCE(b.Sal_Pesometros_TA, 0)
               + COALESCE(b.Sal_Pesometros_TB, 0) > 0
                THEN
                    b.Sal_Topografia_Dia
                    * COALESCE(b.Sal_Pesometros_TB, 0)
                    /
                    NULLIF
                    (
                        COALESCE(b.Sal_Pesometros_TA, 0)
                      + COALESCE(b.Sal_Pesometros_TB, 0),
                        0
                    )

            ELSE 0
        END AS Sal_Ajustada_TB_Candidata,

        CASE
            WHEN COALESCE(b.Sal_Topografia_Dia, 0) <= 0
                THEN 0

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 0

            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 1

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN 1

            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
             AND b.Flag_Sal_Basica_Valida = 1
             AND
                 COALESCE(b.Sal_Pesometros_TA, 0)
               + COALESCE(b.Sal_Pesometros_TB, 0) > 0
                THEN 1

            ELSE 0
        END AS Flag_Sal_Ajuste_Valido_Candidato,

        CASE
            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 'SIN_APILADO'

            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) <= 0
                THEN 'TODA_SAL_TURNO_A'

            WHEN COALESCE(b.TMH_Bruto_A, 0) <= 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN 'TODA_SAL_TURNO_B'

            WHEN COALESCE(b.TMH_Bruto_A, 0) > 0
             AND COALESCE(b.TMH_Bruto_B, 0) > 0
                THEN 'AMBOS_TURNOS_PROPORCIONAL'

            ELSE 'NO_EVALUABLE'
        END AS Regla_Distribucion

    FROM base b
)

SELECT
    Fecha,

    CV201_TA,
    CV201_TB,
    CV202_TA,
    CV202_TB,

    Sal_Pesometros_TA,
    Sal_Pesometros_TB,
    Sal_Pesometros_Dia,

    Sal_Topografia_Dia,

    TMH_Bruto_A,
    TMH_Bruto_B,

    Flag_Sal_Basica_Valida,
    Flag_Sal_Ajuste_Valido_Origen,

    Sal_Ajustada_TA_Origen,
    Sal_Ajustada_TB_Origen,
    Sal_Ajustada_Dia_Origen,

    Flag_Sal_Ajuste_Valido_Candidato
        AS Flag_Sal_Ajuste_Valido,

    Sal_Ajustada_TA_Candidata
        AS Sal_Ajustada_TA,

    Sal_Ajustada_TB_Candidata
        AS Sal_Ajustada_TB,

    Sal_Ajustada_TA_Candidata
    + Sal_Ajustada_TB_Candidata
        AS Sal_Ajustada_Dia,

    TMH_Bruto_A
    - Sal_Ajustada_TA_Candidata
        AS Apilado_TMH_A_Candidato,

    TMH_Bruto_B
    - Sal_Ajustada_TB_Candidata
        AS Apilado_TMH_B_Candidato,

    Regla_Distribucion

FROM calculo;
GO

-- ============================================================================
-- inventar_SpcHidr.v_ton_por_intervalo_excel (VIEW)
-- Ultima modificacion: 2026-07-22 14:05:44.643000
-- ============================================================================
/* -----------------------------------------------------------
   SECCION 2: Vistas consumen la tabla resumen en vez de recalcular
----------------------------------------------------------- */
CREATE   VIEW inventar_SpcHidr.v_ton_por_intervalo_excel
AS
SELECT
    dia_op            = s.fecha_turno,
    Torre             = s.Torre,
    turno_op          = s.turno_op,
    ts_ini            = s.ts_ini,
    ts_fin            = s.ts_fin,
    tot_ini           = s.tot_ini,
    tot_fin           = s.tot_fin,
    toneladas_intervalo = s.toneladas_intervalo,
    flag_intervalo_ok = s.flag_intervalo_ok,
    s.torre_id,
    s.flag_arrastre,
    s.duracion_min,
    s.comentario,
    s.nombre_archivo
FROM inventar_SpcHidr.Resumen_Intervalo_TotTM s;
GO

-- ============================================================================
-- reclamo.fn_fecha_corte (SQL_SCALAR_FUNCTION)
-- Ultima modificacion: 2026-07-30 22:47:05.120000
-- ============================================================================
/* Funcion de acceso, para que las vistas puedan leer la fecha de corte sin
   repetir el literal. */
CREATE   FUNCTION [reclamo].[fn_fecha_corte]()
RETURNS date
AS
BEGIN
    RETURN
    (
        SELECT TRY_CONVERT(date, c.valor)
        FROM [reclamo].[configuracion] c
        WHERE c.clave = 'FECHA_CORTE_SISTEMA'
    );
END;
GO

-- ============================================================================
-- reclamo.v_ajustes_aplicables (VIEW)
-- Ultima modificacion: 2026-07-30 10:03:49.203000
-- ============================================================================
/* ============================================================================
   V6. reclamo.v_ajustes_aplicables

   Regla R10. Solo los ajustes APROBADOS afectan el calculo. Los PROPUESTOS
   quedan visibles en el dashboard pero con delta cero.

   TRASPASO_MODULO genera DOS efectos: descuenta del modulo origen y abona al
   modulo destino. Por eso la vista devuelve dos filas por ajuste de ese tipo.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_ajustes_aplicables]
AS
SELECT
    a.fecha_operacion,
    a.[campaña_id],
    a.pad_id,
    a.modulo_id,
    a.tipo_ajuste,
    a.delta_m3,
    a.delta_tms,
    a.motivo,
    a.antecedente_tipo,
    a.antecedente_ref,
    a.usuario_solicita,
    a.usuario_aprueba,
    a.fecha_aprobacion,
    a.ajuste_id,
    CAST('ORIGEN' AS varchar(10))           AS rol_en_ajuste
FROM [reclamo].[ajuste_manual] a
WHERE a.estado = 'APROBADO'

UNION ALL

/* Contrapartida del traspaso: lo que sale del origen entra al destino. */
SELECT
    a.fecha_operacion,
    a.[campaña_id],
    a.pad_id,
    a.modulo_destino_id                     AS modulo_id,
    a.tipo_ajuste,
    -a.delta_m3                             AS delta_m3,
    -a.delta_tms                            AS delta_tms,
    a.motivo,
    a.antecedente_tipo,
    a.antecedente_ref,
    a.usuario_solicita,
    a.usuario_aprueba,
    a.fecha_aprobacion,
    a.ajuste_id,
    CAST('DESTINO' AS varchar(10))          AS rol_en_ajuste
FROM [reclamo].[ajuste_manual] a
WHERE a.estado = 'APROBADO'
  AND a.tipo_ajuste = 'TRASPASO_MODULO'
  AND a.modulo_destino_id IS NOT NULL;
GO

-- ============================================================================
-- reclamo.v_camiones_acumulado (VIEW)
-- Ultima modificacion: 2026-07-30 10:03:48.773000
-- ============================================================================
/* ============================================================================
   V2. reclamo.v_camiones_acumulado

   Regla R4. El acumulado NO se limita al mes: parte del inicio de la campana,
   porque un modulo puede haber sido reclamado por camiones mucho antes.

   El contraste geomensura contra THM es el control que el Excel hacia a mano
   y que aca queda permanente.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_camiones_acumulado]
AS
SELECT
    cr.fecha,
    cr.[campaña_id],
    cr.pad_id,
    cr.modulo_id,

    cr.m3_oficial                           AS m3_camiones_dia,
    cr.tms_oficial                          AS tms_camiones_dia,

    SUM(cr.m3_oficial) OVER
    (
        PARTITION BY cr.[campaña_id], cr.modulo_id
        ORDER BY cr.fecha
        ROWS UNBOUNDED PRECEDING
    )                                       AS m3_camiones_acum,

    SUM(cr.tms_oficial) OVER
    (
        PARTITION BY cr.[campaña_id], cr.modulo_id
        ORDER BY cr.fecha
        ROWS UNBOUNDED PRECEDING
    )                                       AS tms_camiones_acum,

    cr.m3_geomensura,
    cr.m3_thm,
    cr.vueltas,
    cr.capacidad_camion_m3,
    cr.fuente_oficial,

    /* Brecha relativa entre las dos mediciones, solo cuando ambas existen. */
    CASE
        WHEN cr.m3_geomensura IS NULL OR cr.m3_thm IS NULL THEN NULL
        WHEN cr.m3_thm = 0 THEN NULL
        ELSE (cr.m3_geomensura - cr.m3_thm) * 100.0 / cr.m3_thm
    END                                     AS brecha_geomensura_thm_pct,

    CASE
        WHEN cr.m3_geomensura IS NULL OR cr.m3_thm IS NULL
            THEN 'SIN_CONTRASTE'
        WHEN cr.m3_thm = 0
            THEN 'THM_CERO'
        WHEN ABS((cr.m3_geomensura - cr.m3_thm) * 100.0 / cr.m3_thm) > 10
            THEN 'BRECHA_SOBRE_10_PCT'
        ELSE 'OK'
    END                                     AS flag_contraste_camiones
FROM [reclamo].[camiones_reclamo] cr
WHERE cr.estado = 'VIGENTE';
GO

-- ============================================================================
-- reclamo.v_cv25_diario (VIEW)
-- Ultima modificacion: 2026-07-30 10:03:48.977000
-- ============================================================================
/* ============================================================================
   V4. reclamo.v_cv25_diario

   Consolida el totalizador CV25 y las horas de rotopala a grano diario.
   Es la base del preliminar y del control de rendimiento.

   Regla R7: el tonelaje CV25 corresponde a rotopala 1 mas rotopala 2.

   CORRECCION 30-07-2026: la fuente es diaria, no por turno. Las horas si
   conservan el desglose por turno, porque datos_filtrados tiene su propia
   columna turno.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_cv25_diario]
AS
WITH hr AS
(
    SELECT
        h.fecha_turno                       AS fecha,
        SUM(CASE WHEN h.rotopala_id = 1 THEN h.horas_operacion ELSE 0 END) AS horas_r1,
        SUM(CASE WHEN h.rotopala_id = 2 THEN h.horas_operacion ELSE 0 END) AS horas_r2,
        SUM(h.horas_operacion)              AS horas_total,
        COUNT(DISTINCT h.turno)             AS turnos_con_dato
    FROM [reclamo].[rotopala_horas_turno] h
    GROUP BY h.fecha_turno
)
SELECT
    COALESCE(cv.fecha, hr.fecha)            AS fecha,
    cv.tmh_dia,
    cv.tms_dia,
    cv.tmh_cv025tot,
    cv.tmh_cv025_tot,
    cv.tag_utilizado,
    cv.flag                                 AS flag_cv25,

    /* Contraste entre los dos tags del mismo totalizador. */
    cv.tmh_cv025tot - cv.tmh_cv025_tot      AS diferencia_entre_tags,
    CASE
        WHEN cv.tmh_cv025tot IS NULL OR cv.tmh_cv025_tot IS NULL
            THEN 'SIN_CONTRASTE'
        WHEN cv.tmh_cv025_tot = 0
            THEN 'TAG_SECUNDARIO_CERO'
        WHEN ABS(cv.tmh_cv025tot - cv.tmh_cv025_tot) * 100.0 / cv.tmh_cv025_tot > 1
            THEN 'TAGS_DIFIEREN_SOBRE_1_PCT'
        ELSE 'OK'
    END                                     AS flag_tags,

    hr.horas_r1,
    hr.horas_r2,
    hr.horas_total,
    hr.turnos_con_dato,

    /* Reparto proporcional del tonelaje CV25 entre ambas rotopalas.
       Si no hay horas, no se puede repartir y el preliminar no aplica. */
    CASE
        WHEN COALESCE(hr.horas_total,0) = 0 THEN NULL
        ELSE cv.tms_dia * hr.horas_r1 / hr.horas_total
    END                                     AS tms_estimado_r1,
    CASE
        WHEN COALESCE(hr.horas_total,0) = 0 THEN NULL
        ELSE cv.tms_dia * hr.horas_r2 / hr.horas_total
    END                                     AS tms_estimado_r2,

    CASE
        WHEN cv.fecha IS NULL                     THEN 'SIN_CV25'
        WHEN COALESCE(hr.horas_total,0) = 0       THEN 'SIN_HORAS_NO_REPARTIBLE'
        WHEN COALESCE(cv.tms_dia,0) = 0           THEN 'CV25_CERO_SIN_OPERACION'
        ELSE 'OK'
    END                                     AS flag_preliminar
FROM [reclamo].[cv25_diario] cv
FULL OUTER JOIN hr
    ON hr.fecha = cv.fecha;
GO

-- ============================================================================
-- reclamo.v_modulo_base (VIEW)
-- Ultima modificacion: 2026-07-30 10:03:48.680000
-- ============================================================================
/* ============================================================================
   V1. reclamo.v_modulo_base

   Une el modulo congelado con su posicion en la secuencia de la rotopala.
   Es el punto de entrada de todas las demas vistas: si un modulo no esta
   congelado, no aparece aca y por lo tanto no puede reclamarse.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_modulo_base]
AS
SELECT
    mc.[campaña_id],
    mc.pad_id,
    mc.parcela_id,
    mc.modulo_id,
    COALESCE(mc.modulo_numero, md.numero)   AS modulo_numero,

    mc.fecha_conformacion,
    mc.fecha_congelamiento,

    mc.tms_conformado,
    mc.m3_totales,
    mc.densidad_oficial,
    mc.humedad_conformacion,

    /* Linea base: lo extraido antes de la fecha de corte del sistema. */
    mc.m3_camiones_previo,
    mc.m3_rotopala_previo,
    mc.fecha_linea_base,

    /* Topologia fija del PAD. */
    tp.nombre                               AS pad_nombre,
    tp.material,
    tp.parcelas,
    tp.modulos_por_parcela,
    tp.modulos_totales,
    tp.modulo_numero_max,

    sr.rotopala_id,
    sr.orden_secuencia,
    sr.estado                               AS estado_secuencia,
    sr.fecha_apertura,
    sr.fecha_cierre,

    mc.fuente                               AS fuente_base,
    mc.metodo                               AS metodo_base,
    mc.estado                               AS estado_congelamiento,

    /* Coherencia interna de la base congelada. La densidad declarada deberia
       reproducir el TMS al multiplicarla por el volumen. */
    CASE
        WHEN mc.m3_totales = 0 THEN NULL
        ELSE mc.tms_conformado / mc.m3_totales
    END                                     AS densidad_implicita,
    CASE
        WHEN mc.m3_totales = 0 THEN 'SIN_VOLUMEN'
        WHEN ABS(mc.tms_conformado / mc.m3_totales - mc.densidad_oficial)
             > 0.01 THEN 'DENSIDAD_DECLARADA_DIFIERE'
        ELSE 'OK'
    END                                     AS flag_densidad,

    /* El numero de modulo debe caer dentro del rango fisico de su PAD.
       Oxido 1 a 64, sulfuro 1 a 140. */
    CASE
        WHEN tp.pad_id IS NULL
            THEN 'PAD_SIN_TOPOLOGIA_DEFINIDA'
        WHEN COALESCE(mc.modulo_numero, md.numero) IS NULL
            THEN 'SIN_NUMERO_DE_MODULO'
        WHEN COALESCE(mc.modulo_numero, md.numero)
             NOT BETWEEN tp.modulo_numero_min AND tp.modulo_numero_max
            THEN 'MODULO_FUERA_DEL_RANGO_DEL_PAD'
        ELSE 'OK'
    END                                     AS flag_topologia
FROM [reclamo].[modulo_congelado] mc
LEFT JOIN [reclamo].[secuencia_rotopala] sr
    ON  sr.[campaña_id] = mc.[campaña_id]
    AND sr.modulo_id    = mc.modulo_id
LEFT JOIN [inventar_SpcHidr].[modulo] md
    ON md.id_modulo = mc.modulo_id
LEFT JOIN [reclamo].[topologia_pad] tp
    ON tp.pad_id = mc.pad_id
WHERE mc.estado = 'CONGELADO';
GO

-- ============================================================================
-- reclamo.v_preliminar_cv25 (VIEW)
-- Ultima modificacion: 2026-07-30 10:03:49.060000
-- ============================================================================
/* ============================================================================
   V5. reclamo.v_preliminar_cv25

   Regla R8, segunda parte. Cuando un dia no tiene medicion topografica, se
   proyecta el reclamo desde el tonelaje CV25 repartido por horas de
   operacion, y se asigna al modulo ABIERTO de esa rotopala.

   Si hay mas de un modulo abierto (la regla permite hasta dos), el tonelaje
   se reparte en proporcion al remanente disponible de cada uno. Esa es una
   decision de diseno, no una regla que el usuario haya fijado: queda anotada
   como supuesto S7 en el instructivo.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_preliminar_cv25]
AS
WITH abiertos AS
(
    SELECT
        mb.[campaña_id],
        mb.pad_id,
        mb.modulo_id,
        mb.modulo_numero,
        mb.rotopala_id,
        mb.orden_secuencia,
        mb.m3_totales,
        mb.densidad_oficial,
        mb.fecha_apertura,
        mb.fecha_cierre
    FROM [reclamo].[v_modulo_base] mb
    WHERE mb.estado_secuencia = 'ABIERTO'
      AND mb.rotopala_id IS NOT NULL
),
cv AS
(
    SELECT
        d.fecha,
        d.tms_estimado_r1,
        d.tms_estimado_r2,
        d.horas_r1,
        d.horas_r2,
        d.flag_preliminar
    FROM [reclamo].[v_cv25_diario] d
),
base AS
(
    SELECT
        cv.fecha,
        a.[campaña_id],
        a.pad_id,
        a.modulo_id,
        a.modulo_numero,
        a.rotopala_id,
        a.m3_totales,
        a.densidad_oficial,
        CASE WHEN a.rotopala_id = 1 THEN cv.tms_estimado_r1 ELSE cv.tms_estimado_r2 END
            AS tms_rotopala_dia_total,
        CASE WHEN a.rotopala_id = 1 THEN cv.horas_r1 ELSE cv.horas_r2 END
            AS horas_rotopala,
        cv.flag_preliminar,
        COUNT(*) OVER (PARTITION BY cv.fecha, a.rotopala_id) AS modulos_abiertos
    FROM cv
    CROSS JOIN abiertos a
    WHERE (a.fecha_apertura IS NULL OR cv.fecha >= a.fecha_apertura)
      AND (a.fecha_cierre   IS NULL OR cv.fecha <= a.fecha_cierre)
)
SELECT
    b.fecha                                 AS fecha_operacion,
    b.[campaña_id],
    b.pad_id,
    b.modulo_id,
    b.modulo_numero,
    b.rotopala_id,
    b.horas_rotopala,
    b.modulos_abiertos,

    /* Reparto entre modulos abiertos de la misma rotopala. */
    CAST(b.tms_rotopala_dia_total / b.modulos_abiertos AS decimal(30,12))
                                            AS tms_preliminar_dia,
    CAST
    (
        CASE
            WHEN b.densidad_oficial = 0 THEN NULL
            ELSE (b.tms_rotopala_dia_total / b.modulos_abiertos) / b.densidad_oficial
        END AS decimal(30,12)
    )                                       AS m3_preliminar_dia,

    CAST('PRELIMINAR_CV25' AS varchar(40))  AS fuente_reclamo,
    CAST('CV25_REPARTIDO_POR_HORAS_ROTOPALA' AS varchar(80)) AS metodo_calculo,
    b.flag_preliminar
FROM base b
WHERE b.tms_rotopala_dia_total IS NOT NULL;
GO

-- ============================================================================
-- reclamo.v_reclamo_diario (VIEW)
-- Ultima modificacion: 2026-07-30 10:03:49.290000
-- ============================================================================
/* ============================================================================
   V7. reclamo.v_reclamo_diario

   Vista central. Resuelve, para cada fecha y modulo:
     - la base congelada
     - lo ya extraido por camiones a esa fecha
     - la base disponible para la rotopala, neta de camiones (regla R3)
     - el reclamo del dia, oficial si hay topografia y preliminar si no
     - los ajustes aprobados
     - los porcentajes, incluido el avance referido al remanente post camiones

   avance_roto_pct es el porcentaje que el Excel oficial publica en Datos
   Conciliados, segun el comentario de Juan Antonio Segura del 29-05-2026:
   el avance respecto de lo que queda disponible para reclamar post camiones.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_reclamo_diario]
AS
WITH universo AS
(
    /* Todas las combinaciones fecha x modulo con algun movimiento. */
    SELECT fecha_medicion AS fecha_operacion, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_topografia_resuelta]
    UNION
    SELECT fecha_operacion, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_preliminar_cv25]
    UNION
    SELECT fecha, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_camiones_acumulado]
    UNION
    SELECT fecha_operacion, [campaña_id], pad_id, modulo_id
    FROM [reclamo].[v_ajustes_aplicables]
),
corte AS
(
    SELECT [reclamo].[fn_fecha_corte]() AS fecha_corte
),
cam AS
(
    /* Acumulado de camiones vigente A LA FECHA, no solo del dia. */
    SELECT
        u.fecha_operacion,
        u.[campaña_id],
        u.modulo_id,
        (
            SELECT TOP (1) c.m3_camiones_acum
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = u.[campaña_id]
              AND c.modulo_id    = u.modulo_id
              AND c.fecha       <= u.fecha_operacion
            ORDER BY c.fecha DESC
        ) AS m3_camiones_acum,
        (
            SELECT TOP (1) c.tms_camiones_acum
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = u.[campaña_id]
              AND c.modulo_id    = u.modulo_id
              AND c.fecha       <= u.fecha_operacion
            ORDER BY c.fecha DESC
        ) AS tms_camiones_acum,
        (
            SELECT TOP (1) c.m3_camiones_dia
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = u.[campaña_id]
              AND c.modulo_id    = u.modulo_id
              AND c.fecha        = u.fecha_operacion
        ) AS m3_camiones_dia,
        (
            SELECT TOP (1) c.tms_camiones_dia
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = u.[campaña_id]
              AND c.modulo_id    = u.modulo_id
              AND c.fecha        = u.fecha_operacion
        ) AS tms_camiones_dia
    FROM universo u
),
aju AS
(
    SELECT
        a.fecha_operacion,
        a.[campaña_id],
        a.modulo_id,
        SUM(COALESCE(a.delta_m3, 0))  AS ajuste_m3,
        SUM(COALESCE(a.delta_tms, 0)) AS ajuste_tms,
        COUNT(*)                      AS ajustes_aplicados
    FROM [reclamo].[v_ajustes_aplicables] a
    GROUP BY a.fecha_operacion, a.[campaña_id], a.modulo_id
)
SELECT
    u.fecha_operacion,
    u.[campaña_id],
    u.pad_id,
    u.modulo_id,
    mb.modulo_numero,
    mb.rotopala_id,
    mb.orden_secuencia,

    /* base congelada */
    mb.tms_conformado,
    mb.m3_totales,
    mb.densidad_oficial,

    /* camiones */
    COALESCE(cam.m3_camiones_dia, 0)        AS m3_camiones_dia,
    COALESCE(cam.tms_camiones_dia, 0)       AS tms_camiones_dia,
    COALESCE(cam.m3_camiones_acum, 0)       AS m3_camiones_acum,
    COALESCE(cam.tms_camiones_acum, 0)      AS tms_camiones_acum,

    /* base disponible para la rotopala, neta de camiones. Piso en cero. */
    CASE
        WHEN mb.m3_totales - COALESCE(cam.m3_camiones_acum,0) < 0 THEN 0
        ELSE mb.m3_totales - COALESCE(cam.m3_camiones_acum,0)
    END                                     AS m3_disponible_roto,
    CASE
        WHEN mb.tms_conformado - COALESCE(cam.tms_camiones_acum,0) < 0 THEN 0
        ELSE mb.tms_conformado - COALESCE(cam.tms_camiones_acum,0)
    END                                     AS tms_disponible_roto,

    /* reclamo de rotopala del dia: topografia manda, preliminar rellena */
    COALESCE(tr.m3_incremento, pc.m3_preliminar_dia, 0)
        + COALESCE(aju.ajuste_m3, 0)        AS m3_rotopala_dia,

    CASE
        WHEN tr.m3_incremento IS NOT NULL
            THEN tr.m3_incremento * mb.densidad_oficial
        ELSE COALESCE(pc.tms_preliminar_dia, 0)
    END + COALESCE(aju.ajuste_tms, 0)       AS tms_rotopala_dia,

    tr.m3_reclamado_acum                    AS m3_rotopala_acum_topografia,
    tr.avance_total_pct,

    /* ajustes */
    COALESCE(aju.ajuste_m3, 0)              AS ajuste_m3,
    COALESCE(aju.ajuste_tms, 0)             AS ajuste_tms,
    COALESCE(aju.ajustes_aplicados, 0)      AS ajustes_aplicados,

    /* porcentajes */
    CASE
        WHEN COALESCE(mb.m3_totales,0) = 0 THEN NULL
        ELSE COALESCE(cam.m3_camiones_acum,0) / mb.m3_totales
    END                                     AS avance_camiones_pct,

    CASE
        WHEN COALESCE(mb.m3_totales,0) = 0 THEN NULL
        ELSE (COALESCE(cam.m3_camiones_acum,0) + COALESCE(tr.m3_reclamado_acum,0))
             / mb.m3_totales
    END                                     AS avance_total_pct_calculado,

    /* EL PORCENTAJE QUE VA AL REPORTE: referido al remanente post camiones */
    CASE
        WHEN mb.m3_totales - COALESCE(cam.m3_camiones_acum,0) <= 0 THEN NULL
        ELSE COALESCE(tr.m3_reclamado_acum,0)
             / (mb.m3_totales - COALESCE(cam.m3_camiones_acum,0))
    END                                     AS avance_roto_pct,

    /* trazabilidad */
    CASE
        WHEN tr.m3_incremento IS NOT NULL AND COALESCE(aju.ajustes_aplicados,0) > 0
            THEN 'TOPOGRAFIA'
        WHEN tr.m3_incremento IS NOT NULL
            THEN 'TOPOGRAFIA'
        WHEN pc.tms_preliminar_dia IS NOT NULL
            THEN 'PRELIMINAR_CV25'
        WHEN COALESCE(aju.ajustes_aplicados,0) > 0
            THEN 'AJUSTE_MANUAL'
        ELSE 'SIN_DATO'
    END                                     AS fuente_reclamo,

    COALESCE(tr.metodo, pc.metodo_calculo, 'SIN_METODO')
                                            AS metodo_calculo,

    CASE
        WHEN mb.modulo_id IS NULL
            THEN 'MODULO_NO_CONGELADO'
        WHEN tr.flag_topografia IS NOT NULL
            THEN tr.flag_topografia
        WHEN pc.flag_preliminar IS NOT NULL
            THEN pc.flag_preliminar
        WHEN COALESCE(aju.ajustes_aplicados,0) > 0
            THEN 'SOLO_AJUSTE_MANUAL'
        ELSE 'SIN_DATO'
    END                                     AS flag_calculo,

    COALESCE(aju.ajustes_aplicados,0)       AS n_ajustes
FROM universo u
CROSS JOIN corte
LEFT JOIN [reclamo].[v_modulo_base] mb
    ON  mb.[campaña_id] = u.[campaña_id]
    AND mb.modulo_id    = u.modulo_id
LEFT JOIN [reclamo].[v_topografia_resuelta] tr
    ON  tr.[campaña_id]    = u.[campaña_id]
    AND tr.modulo_id       = u.modulo_id
    AND tr.fecha_medicion  = u.fecha_operacion
LEFT JOIN [reclamo].[v_preliminar_cv25] pc
    ON  pc.[campaña_id]     = u.[campaña_id]
    AND pc.modulo_id        = u.modulo_id
    AND pc.fecha_operacion  = u.fecha_operacion
LEFT JOIN cam
    ON  cam.[campaña_id]     = u.[campaña_id]
    AND cam.modulo_id        = u.modulo_id
    AND cam.fecha_operacion  = u.fecha_operacion
LEFT JOIN aju
    ON  aju.[campaña_id]     = u.[campaña_id]
    AND aju.modulo_id        = u.modulo_id
    AND aju.fecha_operacion  = u.fecha_operacion
/* El sistema no calcula hacia atras de la fecha de corte. Lo anterior vive
   como linea base en modulo_congelado. */
WHERE u.fecha_operacion >= corte.fecha_corte;
GO

-- ============================================================================
-- reclamo.v_reclamo_para_conciliados (VIEW)
-- Ultima modificacion: 2026-08-01 19:38:04.040000
-- ============================================================================
/* ================================================================
   FIX: reclamo.v_reclamo_para_conciliados descarta camiones de
   modulos que ese dia solo tuvieron camiones y ninguna medicion de
   rotopala (topografia, preliminar o ajuste).

   Causa raiz: el filtro WHERE rd.fuente_reclamo <> 'SIN_DATO' usa
   fuente_reclamo (que solo describe el origen del dato de ROTOPALA)
   como filtro de fila completa. Cuando fuente_reclamo = SIN_DATO
   por falta de rotopala ese dia, se pierde tambien el
   tms_camiones_dia de esa fila aunque sea distinto de cero.

   Evidencia 2026-07-01 PAD 2: modulos 192, 193, 194, 199, 200, 201
   tienen tms_camiones_dia > 0 y fuente_reclamo = SIN_DATO. Suma de
   esos seis modulos = 17995.070451, exactamente la diferencia que
   se observaba ese dia entre el dashboard (reclamo.calculo_diario)
   y la fuente del SP (reclamo.v_reclamo_para_conciliados).

   Fix: conservar la fila si hay fuente de rotopala valida O si hay
   camiones distintos de cero ese dia. Los modulos realmente vacios
   (sin rotopala y sin camiones) se siguen excluyendo igual que
   antes.

   No se toca reclamo.v_reclamo_diario (esa vista ya calcula bien
   tms_camiones_dia; el problema es solo el filtro de esta vista).
================================================================ */

CREATE VIEW [reclamo].[v_reclamo_para_conciliados]
AS
SELECT
    rd.fecha_operacion,
    rd.pad_id,
    rd.[campaña_id],
    rd.modulo_id,
    rd.modulo_numero,
    rd.rotopala_id,
    CAST(rd.avance_roto_pct AS float)              AS avance_porcentaje,
    CAST(rd.avance_total_pct_calculado AS float)   AS avance_total_porcentaje,
    CAST(rd.avance_camiones_pct AS float)          AS avance_camiones_porcentaje,
    CAST(rd.tms_rotopala_dia AS float)             AS tonelaje_reclamado_diario,
    CAST(rd.m3_rotopala_dia AS float)              AS volumen_diario_m3,
    CAST(rd.tms_camiones_dia AS float)             AS tonelaje_camiones_diario,
    CAST(rd.tms_disponible_roto AS float)          AS tms_disponible_roto,
    CAST(rd.tms_conformado AS float)               AS tms_conformado,
    CAST(rd.densidad_oficial AS float)             AS densidad_oficial,
    rd.fuente_reclamo,
    rd.metodo_calculo,
    rd.flag_calculo,
    rd.ajustes_aplicados
FROM [reclamo].[v_reclamo_diario] rd
WHERE rd.fuente_reclamo <> 'SIN_DATO'
   OR COALESCE(rd.tms_camiones_dia, 0) <> 0;
GO

-- ============================================================================
-- reclamo.v_topografia_resuelta (VIEW)
-- Ultima modificacion: 2026-07-30 10:03:48.890000
-- ============================================================================
/* ============================================================================
   V3. reclamo.v_topografia_resuelta

   Deriva el incremento diario a partir del acumulado, comparando cada
   medicion contra la anterior del MISMO modulo. Nunca compara entre modulos.

   El incremento se acota en cero: un retroceso topografico no produce
   tonelaje negativo, pero queda marcado en flag_topografia para que alguien
   lo revise.

   CASO DE LA PRIMERA MEDICION DE CADA MODULO (sin fila anterior via LAG):
   el acumulado que llega desde la fuente (m3_reclamado_acum) NO se reinicia
   en la fecha de corte -- es el mismo acumulado corrido desde el inicio real
   del modulo. Si el modulo ya tenia extraccion previa capturada como linea
   base (modulo_congelado.m3_rotopala_previo, via sp_establecer_linea_base),
   esa porcion YA esta incluida dentro del primer acumulado sincronizado y
   debe descontarse antes de tratarlo como el incremento de ese dia. De lo
   contrario el modulo recibe de golpe todo lo que llevaba desde antes del
   corte como si fuera tonelaje de un solo dia (bug confirmado en modulo_id
   187, campaña 8, 2026-07-01: 100.439,216 m3 tratados como incremento del
   dia en vez de 10.325,714 m3, el incremento real).
   ============================================================================ */
CREATE   VIEW [reclamo].[v_topografia_resuelta]
AS
WITH sec AS
(
    SELECT
        ta.fecha_medicion,
        ta.[campaña_id],
        ta.pad_id,
        ta.modulo_id,
        ta.m3_reclamado_acum,
        ta.avance_total_pct,
        ta.medicion_valida,
        ta.motivo_no_medicion,
        ta.fuente,
        ta.metodo,
        mc.m3_rotopala_previo,

        LAG(ta.fecha_medicion) OVER
        (
            PARTITION BY ta.[campaña_id], ta.modulo_id
            ORDER BY ta.fecha_medicion
        ) AS fecha_medicion_anterior,

        LAG(ta.m3_reclamado_acum) OVER
        (
            PARTITION BY ta.[campaña_id], ta.modulo_id
            ORDER BY ta.fecha_medicion
        ) AS m3_acum_anterior
    FROM [reclamo].[topografia_avance] ta
    LEFT JOIN [reclamo].[modulo_congelado] mc
        ON mc.[campaña_id] = ta.[campaña_id] AND mc.modulo_id = ta.modulo_id
    WHERE ta.estado = 'VIGENTE'
)
SELECT
    s.fecha_medicion,
    s.[campaña_id],
    s.pad_id,
    s.modulo_id,

    s.m3_reclamado_acum,
    s.m3_acum_anterior,
    s.fecha_medicion_anterior,
    DATEDIFF(day, s.fecha_medicion_anterior, s.fecha_medicion) AS dias_entre_mediciones,

    CAST
    (
        CASE
            WHEN s.medicion_valida = 0 THEN 0
            WHEN s.m3_acum_anterior IS NULL
                 AND s.m3_reclamado_acum - COALESCE(s.m3_rotopala_previo, 0) < 0 THEN 0
            WHEN s.m3_acum_anterior IS NULL
                 THEN s.m3_reclamado_acum - COALESCE(s.m3_rotopala_previo, 0)
            WHEN s.m3_reclamado_acum - s.m3_acum_anterior < 0 THEN 0
            ELSE s.m3_reclamado_acum - s.m3_acum_anterior
        END AS decimal(30,12)
    )                                       AS m3_incremento,

    s.avance_total_pct,
    s.medicion_valida,
    s.motivo_no_medicion,
    s.fuente,
    s.metodo,

    CASE
        WHEN s.medicion_valida = 0
            THEN 'SIN_MEDICION'
        WHEN s.m3_acum_anterior IS NULL
             AND s.m3_reclamado_acum - COALESCE(s.m3_rotopala_previo, 0) < 0
            THEN 'PRIMERA_MEDICION_BAJO_LINEA_BASE_REVISAR'
        WHEN s.m3_acum_anterior IS NULL
            THEN 'PRIMERA_MEDICION_DEL_MODULO'
        WHEN s.m3_reclamado_acum < s.m3_acum_anterior
            THEN 'RETROCESO_ACUMULADO_REVISAR'
        WHEN DATEDIFF(day, s.fecha_medicion_anterior, s.fecha_medicion) > 1
            THEN 'INCREMENTO_ACUMULA_VARIOS_DIAS'
        ELSE 'OK'
    END                                     AS flag_topografia
FROM sec s;
GO
