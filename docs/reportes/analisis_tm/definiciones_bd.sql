-- Definiciones actuales extraidas desde SQL Server.
-- Servidor: VPS-5347319-X
-- Base: inventar_SpcHidr
-- Fecha de extraccion: 2026-08-21 14:13:53.510616-03:00
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
-- inventar_SpcHidr.resumen_mina (VIEW)
-- Ultima modificacion: 2026-02-11 13:13:03.167000
-- ============================================================================
CREATE VIEW [inventar_SpcHidr].[resumen_mina] AS
SELECT
   mov_cam.Fecha AS Fecha,
   mov_cam.Turno AS Turno,
   mov_cam.Origen AS Origen,
   mov_cam.Fase AS Fase,

   -- Tonelaje
   SUM(mov_cam.Ton) AS Ton,

   -- Leyes Ponderadas
   SUM(mov_cam.Ton * mov_cam.CuTG00) / NULLIF(SUM(mov_cam.Ton),0) AS PONDCuTG00,
   SUM(mov_cam.Ton * mov_cam.CusG01) / NULLIF(SUM(mov_cam.Ton),0) AS PONDCusG01,
   SUM(mov_cam.Ton * mov_cam.RS) / NULLIF(SUM(mov_cam.Ton),0) AS PONDRS,
   SUM(mov_cam.Ton * mov_cam.C03G02) / NULLIF(SUM(mov_cam.Ton),0) AS PONDC03G02,
   SUM(mov_cam.Ton * mov_cam.RecLixG03) / NULLIF(SUM(mov_cam.Ton),0) AS PONDRecLixG03,

   -- Granulometría Ponderada
   SUM(mov_cam.Ton * mov_cam.[100G07]) / NULLIF(SUM(mov_cam.Ton),0) AS POND100G07,

   -- Mineralogía Ponderada
   SUM(mov_cam.Ton * mov_cam.ClayBG10) / NULLIF(SUM(mov_cam.Ton),0) AS PONDClayBG10,
   SUM(mov_cam.Ton * mov_cam.CUFE) / NULLIF(SUM(mov_cam.Ton),0) AS PONDCUFE,
   SUM(mov_cam.Ton * mov_cam.FE) / NULLIF(SUM(mov_cam.Ton),0) AS PONDFE

FROM
   mov_cam
GROUP BY
   mov_cam.Fecha,
   mov_cam.Turno,
   mov_cam.Origen,
   mov_cam.Fase;
GO

-- ============================================================================
-- inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-07-31 11:23:14.840000
-- ============================================================================

/* ============================================================================
   ACTUALIZADOR DE LA CACHÉ GEMELA
   ============================================================================ */
CREATE   PROCEDURE
    [inventar_SpcHidr].[sp_actualizar_reporte_turno_cache_emision_test]
    @fecha_inicio date,
    @fecha_fin    date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @fecha_inicio IS NULL OR @fecha_fin IS NULL
        THROW 51010, 'Debe informar @fecha_inicio y @fecha_fin.', 1;

    IF @fecha_inicio >= @fecha_fin
        THROW 51011, '@fecha_fin debe ser posterior a @fecha_inicio.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        DELETE FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test]
        WHERE Fecha >= @fecha_inicio
          AND Fecha <  @fecha_fin;

        INSERT INTO [inventar_SpcHidr].[reporte_turno_cache_emision_test]
        (
            Fecha,
            Campania,
            Material,
            Modulo,
            Avance,
            Turno,
            Apilado_TMS_Real,
            Apilado_TMS_Plan_Mensual,
            STOCK,
            MINA,
            SRR,
            CuT_Real,
            CuT_Plan_Mensual,
            CuT_Plan_Semanal,
            CuS_Real,
            CuS_Plan_Mensual,
            CuS_Plan_Semanal,
            Solubilidad_Real,
            Solubilidad_Plan_Mensual,
            Solubilidad_Plan_Semanal,
            CO3_Real,
            CO3_Plan_Mensual,
            CO3_Plan_Semanal,
            CuFe_Real,
            CuFe_Plan_Mensual,
            CuFe_Plan_Semanal,
            FeT_Real,
            FeS_Real,
            ConsH_Real,
            Malla_Menos_1_2_Real,
            Malla_Menos_1_2_Plan_Semanal,
            Malla_Menos_100_Real,
            Malla_Menos_100_Plan_Mensual,
            Malla_Menos_100_Plan_Semanal,
            CaolBeta_Real,
            CaolBeta_Plan_Mensual,
            CaolBeta_Plan_Semanal,
            Dosis_Acido_Ideal_TM,
            Dosis_Acido_Programa_Semanal,
            Fuente_Info_Quimica,
            Fuente_Info_Fisica,
            Muestra_Quimica,
            Muestra_Fisica
        )
        EXEC [inventar_SpcHidr].[sp_reporte_turno_emision_test]
            @fecha_inicio = @fecha_inicio,
            @fecha_fin    = @fecha_fin;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        THROW;
    END CATCH;
END;
GO

-- ============================================================================
-- inventar_SpcHidr.sp_factor_ajuste_camiones_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-08-21 13:33:37.403000
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

CREATE   PROCEDURE [inventar_SpcHidr].[sp_factor_ajuste_camiones_test]
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
            s.Fecha,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'A' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_A,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'B' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_B,
            SUM(COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0)) AS SRR_TMS_Dia,
            COUNT(*) AS Cantidad_Registros_SRR
        FROM [inventar_SpcHidr].[v_srr_tms_origen_turno_emision_test] AS s
        WHERE s.Fecha BETWEEN @FechaInicio AND @FechaFin
        GROUP BY s.Fecha
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
-- inventar_SpcHidr.sp_generador_reporte_diario_emision_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-07-31 11:39:34.093000
-- ============================================================================

CREATE   PROCEDURE
    [inventar_SpcHidr].[sp_generador_reporte_diario_emision_test]
(
    @fecha_inicio date,
    @fecha_fin    date
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    /* ============================================================
       GENERADOR REPORTE DIARIO — LÍNEA DE EMISIÓN

       La fecha final es exclusiva.

       La lógica Turno → Día se encuentra centralizada en:
       inventar_SpcHidr.fn_generador_reporte_diario_emision_test

       Este procedimiento actúa únicamente como interfaz de consulta.

       No modifica:
       - sp_generador_reporte_diario
       - fn_generador_reporte_diario
       - reporte_turno_cache
       ============================================================ */

    IF @fecha_inicio IS NULL
       OR @fecha_fin IS NULL
    BEGIN
        THROW 50001,
              'Las fechas de inicio y fin son obligatorias.',
              1;
    END;

    IF @fecha_inicio >= @fecha_fin
    BEGIN
        THROW 50002,
              'La fecha de inicio debe ser menor que la fecha de fin.',
              1;
    END;

    SELECT *
    FROM
        [inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]
        (
            @fecha_inicio,
            @fecha_fin
        )
    ORDER BY Fecha;
END;
GO

-- ============================================================================
-- inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-08-04 14:48:06.393000
-- ============================================================================
/* ================================================================
   inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test
   ----------------------------------------------------------------
   Puebla inventar_SpcHidr.Control_Apilado_TMH_v2_test con la misma
   logica que hoy calcula inventar_SpcHidr.v_datos_apilado_tmh_v2
   (TMH bruto por turno desde los totalizadores CV008/CV108 en
   tot_TM), pero SOLO recalcula:

     1) los ultimos @DiasReproceso dias del rango pedido (ventana
        movil, para capturar correcciones tardias del totalizador),
     2) cualquier fecha dentro del rango pedido que TODAVIA NO
        tenga fila en la tabla (huecos -- primera carga o dias
        nuevos nunca procesados).

   Fechas dentro del rango que ya existen en la tabla y estan FUERA
   de la ventana de reproceso NO se recalculan -- ahi esta el
   ahorro real. Sin esto, cada exportacion de un mes completo
   volveria a tocar tot_TM entero otra vez, igual que antes.

   Diferencia importante con sp_mantiene_factor_ajuste_camiones_v2_test:
   ese SP con @DiasReproceso=0 termina procesando el rango COMPLETO
   igual (bug de diseno ya documentado, no corregido aca para no
   tocar un objeto que no es parte de este cambio). Este SP nuevo
   implementa el recorte real: si @DiasReproceso es menor que el
   ancho del rango pedido, los dias mas antiguos que ya existen en
   la tabla se saltan.
================================================================ */
CREATE PROCEDURE
    [inventar_SpcHidr].[sp_mantiene_apilado_tmh_v2_test]
(
    @FechaInicio   date,
    @FechaFin      date,
    @DiasReproceso int = 7
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50901, 'Debe informar @FechaInicio y @FechaFin.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50902, 'La fecha inicial no puede ser mayor que la fecha final.', 1;
    IF @DiasReproceso IS NULL OR @DiasReproceso < 0
        THROW 50903, '@DiasReproceso debe ser mayor o igual que cero.', 1;
    IF OBJECT_ID('inventar_SpcHidr.Control_Apilado_TMH_v2_test', 'U') IS NULL
        THROW 50904, 'No existe la tabla Control_Apilado_TMH_v2_test.', 1;

    /* Inicio de la ventana de reproceso obligatorio: los ultimos
       @DiasReproceso dias del rango pedido. Si @DiasReproceso es
       mayor o igual al ancho del rango, la ventana cubre todo el
       rango (mismo comportamiento que un @FechaInicio normal). */
    DECLARE @FechaInicioVentana date =
        CASE
            WHEN DATEADD(DAY, -(@DiasReproceso - 1), @FechaFin) > @FechaInicio
                THEN DATEADD(DAY, -(@DiasReproceso - 1), @FechaFin)
            ELSE @FechaInicio
        END;
    DECLARE @FechaCalculo datetime2(7) = SYSDATETIME();

    /* ============================================================
       1. Fechas a procesar: ventana de reproceso + huecos
       ============================================================ */
    IF OBJECT_ID('tempdb..#fechas') IS NOT NULL DROP TABLE #fechas;
    ;WITH fechas_candidatas AS
    (
        SELECT DISTINCT
            CAST(fecha AS date) AS Fecha
        FROM inventar_SpcHidr.tot_TM
        WHERE fecha >= @FechaInicio
          AND fecha < DATEADD(DAY, 1, @FechaFin)
    )
    SELECT fc.Fecha
    INTO #fechas
    FROM fechas_candidatas AS fc
    WHERE fc.Fecha >= @FechaInicioVentana
       OR NOT EXISTS
          (
              SELECT 1
              FROM inventar_SpcHidr.Control_Apilado_TMH_v2_test AS c
              WHERE c.Fecha = fc.Fecha
          );
    CREATE UNIQUE CLUSTERED INDEX IX_fechas ON #fechas(Fecha);

    /* Si no hay nada que procesar (todo el rango ya estaba
       calculado y fuera de la ventana), terminar rapido. */
    IF NOT EXISTS (SELECT 1 FROM #fechas)
    BEGIN
        PRINT 'sp_mantiene_apilado_tmh_v2_test: nada que reprocesar, todo el rango ya estaba vigente.';
        RETURN;
    END;

    /* ============================================================
       2. Misma logica que v_datos_apilado_tmh_v2, acotada a #fechas
       ============================================================ */
    ;WITH marcas AS
    (
        SELECT
            f.Fecha,
            CAST(DATEADD(HOUR, 8, CAST(f.Fecha AS datetime2)) AS datetime2) AS ts_08_dia,
            CAST(DATEADD(HOUR, 20, CAST(f.Fecha AS datetime2)) AS datetime2) AS ts_20_dia,
            CAST(DATEADD(HOUR, 8, DATEADD(DAY, 1, CAST(f.Fecha AS datetime2))) AS datetime2) AS ts_08_dia_siguiente
        FROM #fechas AS f
    ),
    totales AS
    (
        SELECT
            m.Fecha,
            m.ts_08_dia,
            m.ts_20_dia,
            m.ts_08_dia_siguiente,
            CAST(t08.tot_008 AS float) AS CV008_Totalizador_08,
            CAST(t20.tot_008 AS float) AS CV008_Totalizador_20,
            CAST(t08s.tot_008 AS float) AS CV008_Totalizador_08_Dia_Siguiente,
            CAST(t08.tot_108 AS float) AS CV108_Totalizador_08,
            CAST(t20.tot_108 AS float) AS CV108_Totalizador_20,
            CAST(t08s.tot_108 AS float) AS CV108_Totalizador_08_Dia_Siguiente
        FROM marcas AS m
        LEFT JOIN inventar_SpcHidr.tot_TM AS t08
            ON t08.fecha = m.ts_08_dia
        LEFT JOIN inventar_SpcHidr.tot_TM AS t20
            ON t20.fecha = m.ts_20_dia
        LEFT JOIN inventar_SpcHidr.tot_TM AS t08s
            ON t08s.fecha = m.ts_08_dia_siguiente
    ),
    calculo_bruto AS
    (
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
            CV008_Totalizador_20 - CV008_Totalizador_08 AS TMH_CV008_A_Bruto,
            CV008_Totalizador_08_Dia_Siguiente - CV008_Totalizador_20 AS TMH_CV008_B_Bruto,
            CV108_Totalizador_20 - CV108_Totalizador_08 AS TMH_CV108_A_Bruto,
            CV108_Totalizador_08_Dia_Siguiente - CV108_Totalizador_20 AS TMH_CV108_B_Bruto
        FROM totales
    ),
    validacion AS
    (
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
            CASE
                WHEN TMH_CV008_A_Bruto IS NULL THEN 0
                WHEN TMH_CV008_A_Bruto <= 100 THEN 0
                ELSE TMH_CV008_A_Bruto
            END AS TMH_CV008_A_Valido,
            CASE
                WHEN TMH_CV108_A_Bruto IS NULL THEN 0
                WHEN TMH_CV108_A_Bruto <= 100 THEN 0
                ELSE TMH_CV108_A_Bruto
            END AS TMH_CV108_A_Valido,
            CASE
                WHEN TMH_CV008_B_Bruto IS NULL THEN 0
                WHEN TMH_CV008_B_Bruto <= 100 THEN 0
                ELSE TMH_CV008_B_Bruto
            END AS TMH_CV008_B_Valido,
            CASE
                WHEN TMH_CV108_B_Bruto IS NULL THEN 0
                WHEN TMH_CV108_B_Bruto <= 100 THEN 0
                ELSE TMH_CV108_B_Bruto
            END AS TMH_CV108_B_Valido
        FROM calculo_bruto
    ),
    validacion_turno AS
    (
        SELECT
            *,
            TMH_CV008_A_Valido + TMH_CV108_A_Valido AS TMH_Total_A_Valido,
            TMH_CV008_B_Valido + TMH_CV108_B_Valido AS TMH_Total_B_Valido,
            CASE WHEN TMH_CV008_A_Valido + TMH_CV108_A_Valido > 100 THEN 1 ELSE 0 END AS Flag_Apilado_Valido_A,
            CASE WHEN TMH_CV008_B_Valido + TMH_CV108_B_Valido > 100 THEN 1 ELSE 0 END AS Flag_Apilado_Valido_B
        FROM validacion
    )
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
        CASE WHEN Flag_Apilado_Valido_A = 1 AND Flag_Apilado_Valido_B = 1 THEN 1 ELSE 0 END AS Flag_Apilado_Valido,
        CASE WHEN Flag_Apilado_Valido_A = 1 THEN TMH_CV008_A_Valido ELSE 0 END AS TMH_CV008_A,
        CASE WHEN Flag_Apilado_Valido_B = 1 THEN TMH_CV008_B_Valido ELSE 0 END AS TMH_CV008_B,
        CASE WHEN Flag_Apilado_Valido_A = 1 THEN TMH_CV108_A_Valido ELSE 0 END AS TMH_CV108_A,
        CASE WHEN Flag_Apilado_Valido_B = 1 THEN TMH_CV108_B_Valido ELSE 0 END AS TMH_CV108_B,
        CASE WHEN Flag_Apilado_Valido_A = 1 THEN TMH_Total_A_Valido ELSE 0 END AS TMH_Apilado_Total_A,
        CASE WHEN Flag_Apilado_Valido_B = 1 THEN TMH_Total_B_Valido ELSE 0 END AS TMH_Apilado_Total_B,
        (CASE WHEN Flag_Apilado_Valido_A = 1 THEN TMH_Total_A_Valido ELSE 0 END)
      + (CASE WHEN Flag_Apilado_Valido_B = 1 THEN TMH_Total_B_Valido ELSE 0 END) AS TMH_Apilado_Total_Dia,
        Flag_Apilado_Valido_A,
        Flag_Apilado_Valido_B,
        @FechaCalculo AS Fecha_Calculo
    INTO #resultado
    FROM validacion_turno;

    /* ============================================================
       3. MERGE hacia la tabla congelada
       ============================================================ */
    MERGE inventar_SpcHidr.Control_Apilado_TMH_v2_test WITH (HOLDLOCK) AS tgt
    USING #resultado AS src
        ON tgt.Fecha = src.Fecha
    WHEN MATCHED THEN
        UPDATE SET
            ts_08_dia = src.ts_08_dia,
            ts_20_dia = src.ts_20_dia,
            ts_08_dia_siguiente = src.ts_08_dia_siguiente,
            CV008_Totalizador_08 = src.CV008_Totalizador_08,
            CV008_Totalizador_20 = src.CV008_Totalizador_20,
            CV008_Totalizador_08_Dia_Siguiente = src.CV008_Totalizador_08_Dia_Siguiente,
            CV108_Totalizador_08 = src.CV108_Totalizador_08,
            CV108_Totalizador_20 = src.CV108_Totalizador_20,
            CV108_Totalizador_08_Dia_Siguiente = src.CV108_Totalizador_08_Dia_Siguiente,
            TMH_CV008_A_Bruto = src.TMH_CV008_A_Bruto,
            TMH_CV008_B_Bruto = src.TMH_CV008_B_Bruto,
            TMH_CV108_A_Bruto = src.TMH_CV108_A_Bruto,
            TMH_CV108_B_Bruto = src.TMH_CV108_B_Bruto,
            Flag_Apilado_Valido = src.Flag_Apilado_Valido,
            TMH_CV008_A = src.TMH_CV008_A,
            TMH_CV008_B = src.TMH_CV008_B,
            TMH_CV108_A = src.TMH_CV108_A,
            TMH_CV108_B = src.TMH_CV108_B,
            TMH_Apilado_Total_A = src.TMH_Apilado_Total_A,
            TMH_Apilado_Total_B = src.TMH_Apilado_Total_B,
            TMH_Apilado_Total_Dia = src.TMH_Apilado_Total_Dia,
            Flag_Apilado_Valido_A = src.Flag_Apilado_Valido_A,
            Flag_Apilado_Valido_B = src.Flag_Apilado_Valido_B,
            Fecha_Calculo = src.Fecha_Calculo
    WHEN NOT MATCHED BY TARGET THEN
        INSERT
        (
            Fecha, ts_08_dia, ts_20_dia, ts_08_dia_siguiente,
            CV008_Totalizador_08, CV008_Totalizador_20, CV008_Totalizador_08_Dia_Siguiente,
            CV108_Totalizador_08, CV108_Totalizador_20, CV108_Totalizador_08_Dia_Siguiente,
            TMH_CV008_A_Bruto, TMH_CV008_B_Bruto, TMH_CV108_A_Bruto, TMH_CV108_B_Bruto,
            Flag_Apilado_Valido,
            TMH_CV008_A, TMH_CV008_B, TMH_CV108_A, TMH_CV108_B,
            TMH_Apilado_Total_A, TMH_Apilado_Total_B, TMH_Apilado_Total_Dia,
            Flag_Apilado_Valido_A, Flag_Apilado_Valido_B,
            Fecha_Calculo
        )
        VALUES
        (
            src.Fecha, src.ts_08_dia, src.ts_20_dia, src.ts_08_dia_siguiente,
            src.CV008_Totalizador_08, src.CV008_Totalizador_20, src.CV008_Totalizador_08_Dia_Siguiente,
            src.CV108_Totalizador_08, src.CV108_Totalizador_20, src.CV108_Totalizador_08_Dia_Siguiente,
            src.TMH_CV008_A_Bruto, src.TMH_CV008_B_Bruto, src.TMH_CV108_A_Bruto, src.TMH_CV108_B_Bruto,
            src.Flag_Apilado_Valido,
            src.TMH_CV008_A, src.TMH_CV008_B, src.TMH_CV108_A, src.TMH_CV108_B,
            src.TMH_Apilado_Total_A, src.TMH_Apilado_Total_B, src.TMH_Apilado_Total_Dia,
            src.Flag_Apilado_Valido_A, src.Flag_Apilado_Valido_B,
            src.Fecha_Calculo
        );

    DECLARE @FilasAfectadas int = @@ROWCOUNT;
    PRINT 'sp_mantiene_apilado_tmh_v2_test finalizado.';
    PRINT 'Ventana de reproceso obligatorio: ' + CONVERT(varchar(10), @FechaInicioVentana, 120) + ' a ' + CONVERT(varchar(10), @FechaFin, 120);
    PRINT 'Filas insertadas/actualizadas: ' + CONVERT(varchar(20), @FilasAfectadas);
END;
GO

-- ============================================================================
-- inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-08-21 13:33:37.463000
-- ============================================================================

CREATE   PROCEDURE [inventar_SpcHidr].[sp_mantiene_factor_ajuste_camiones_v2_test]
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
        s.Fecha,
        SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'A' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_A,
        SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'B' THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0) ELSE 0.0 END) AS SRR_TMS_Turno_B
    INTO #SRRTurnos
    FROM [inventar_SpcHidr].[v_srr_tms_origen_turno_emision_test] AS s
    WHERE s.Fecha BETWEEN @FechaInicioProceso AND @FechaFin
    GROUP BY s.Fecha;

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
-- inventar_SpcHidr.sp_refrescar_clays_cufe (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-08-03 02:46:39.750000
-- ============================================================================

CREATE   PROCEDURE
    [inventar_SpcHidr].[sp_refrescar_clays_cufe]
(
    @FechaInicio date = NULL,
    @FechaFin date = NULL,
    @SoloVistaPrevia bit = 1
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    /* ========================================================
       CONFIGURACIÓN Y FECHAS
       ======================================================== */

    DECLARE @FechaCorteProtegida date = '20260801';

    DECLARE @FechaFinEfectiva date;

    DECLARE @FechaInicioSolicitada date;

    DECLARE @FechaInicioEfectiva date;

    DECLARE @IdEjecucion uniqueidentifier = NEWID();

    DECLARE @FechaProceso datetime2(3) = SYSDATETIME();

    SET @FechaFinEfectiva =
        ISNULL
        (
            @FechaFin,
            DATEADD
            (
                DAY,
                -1,
                CONVERT(date, GETDATE())
            )
        );

    SET @FechaInicioSolicitada =
        ISNULL
        (
            @FechaInicio,
            DATEADD
            (
                DAY,
                -7,
                @FechaFinEfectiva
            )
        );

    SET @FechaInicioEfectiva =
        CASE
            WHEN @FechaInicioSolicitada < @FechaCorteProtegida
                THEN @FechaCorteProtegida
            ELSE @FechaInicioSolicitada
        END;

    /* ========================================================
       VALIDACIONES
       ======================================================== */

    IF OBJECT_ID
    (
        N'[inventar_SpcHidr].[v_clays_cufe_calculado_v2_test]',
        N'V'
    ) IS NULL
    BEGIN
        THROW 50001,
            'No existe la vista v_clays_cufe_calculado_v2_test.',
            1;
    END;

    IF OBJECT_ID
    (
        N'[inventar_SpcHidr].[Clays_CuFe]',
        N'U'
    ) IS NULL
    BEGIN
        THROW 50002,
            'No existe la tabla Clays_CuFe.',
            1;
    END;

    IF @SoloVistaPrevia = 0
       AND OBJECT_ID
       (
           N'[inventar_SpcHidr].[Clays_CuFe_trazabilidad]',
           N'U'
       ) IS NULL
    BEGIN
        THROW 50003,
            'No existe la tabla Clays_CuFe_trazabilidad.',
            1;
    END;

    IF @FechaFinEfectiva < @FechaCorteProtegida
    BEGIN
        THROW 50004,
            'El período solicitado termina antes del corte protegido 01-08-2026.',
            1;
    END;

    IF @FechaInicioEfectiva > @FechaFinEfectiva
    BEGIN
        THROW 50005,
            'La fecha inicial efectiva es posterior a la fecha final.',
            1;
    END;

    DROP TABLE IF EXISTS #fuente;
    DROP TABLE IF EXISTS #destino;
    DROP TABLE IF EXISTS #acciones;

    /* ========================================================
       FUENTE CALCULADA
       ======================================================== */

    SELECT
        v.Fecha,
        v.Turno,
        v.Torre,

        CASE
            WHEN v.Torre = 'TM1' THEN 'TM-1'
            WHEN v.Torre = 'TM2' THEN 'TM-2'
        END AS Torre_Destino,

        CASE
            WHEN v.Turno = 'A' THEN 'TA'
            WHEN v.Turno = 'B' THEN 'TB'
        END AS Turno_Destino,

        v.Representatividad_Quimica,
        v.Representatividad_Quimica_TM2,

        v.ID_NIR,
        v.Muestra_NIR,
        v.CaolBeta_NIR,
        v.Fecha_Carga_NIR,
        v.Cantidad_Registros_NIR,

        v.ID_NIR_TM2,
        v.Muestra_NIR_TM2,
        v.CaolBeta_NIR_TM2,
        v.Fecha_Carga_NIR_TM2,

        v.CaolBeta_MB,
        v.CaolBeta_Final,

        CAST
        (
            v.CaolBeta_Final_2D
            AS decimal(18,2)
        ) AS CaolBeta_Nuevo,

        v.Fuente_CaolBeta,

        v.ID_Registro_CuFe,
        v.CuFe_Laboratorio,
        v.Fecha_Carga_Laboratorio,
        v.Cantidad_Registros_Laboratorio,

        v.ID_Registro_CuFe_TM2,
        v.CuFe_Laboratorio_TM2,
        v.Fecha_Carga_Laboratorio_TM2,

        v.CuFe_MB,
        v.CuFe_Final,

        CAST
        (
            v.CuFe_Final_2D
            AS decimal(18,2)
        ) AS CuFe_Nuevo,

        v.Fuente_CuFe,
        v.Cantidad_Registros_MB

    INTO #fuente

    FROM
        [inventar_SpcHidr].[v_clays_cufe_calculado_v2_test] AS v

    WHERE
        v.Fecha BETWEEN
            @FechaInicioEfectiva
            AND @FechaFinEfectiva

        AND
        (
            v.CaolBeta_Final_2D IS NOT NULL
            OR v.CuFe_Final_2D IS NOT NULL
        );

    /* ========================================================
       CONTROL DE DUPLICADOS EN LA FUENTE
       ======================================================== */

    IF EXISTS
    (
        SELECT
            Fecha,
            Turno,
            Torre
        FROM #fuente
        GROUP BY
            Fecha,
            Turno,
            Torre
        HAVING COUNT(*) > 1
    )
    BEGIN
        THROW 50006,
            'La vista calculada contiene claves duplicadas.',
            1;
    END;

    /* ========================================================
       DESTINO ACTUAL NORMALIZADO
       ======================================================== */

    SELECT
        c.Fecha,

        c.Torre AS Torre_Original,
        c.Turno AS Turno_Original,

        CASE
            WHEN norm.Torre_Normalizada
                 IN ('TM1', 'T1', 'TORRE1')
                THEN 'TM1'

            WHEN norm.Torre_Normalizada
                 IN ('TM2', 'T2', 'TORRE2')
                THEN 'TM2'
        END AS Torre,

        CASE
            WHEN norm.Turno_Normalizado
                 IN ('A', 'TA', 'TURNOA')
                THEN 'A'

            WHEN norm.Turno_Normalizado
                 IN ('B', 'TB', 'TURNOB')
                THEN 'B'
        END AS Turno,

        TRY_CONVERT
        (
            decimal(18,2),
            c.CaolBeta
        ) AS CaolBeta_Anterior,

        TRY_CONVERT
        (
            decimal(18,2),
            c.CuFe
        ) AS CuFe_Anterior

    INTO #destino

    FROM
        [inventar_SpcHidr].[Clays_CuFe] AS c

    CROSS APPLY
    (
        VALUES
        (
            REPLACE
            (
                REPLACE
                (
                    REPLACE
                    (
                        UPPER
                        (
                            LTRIM
                            (
                                RTRIM
                                (
                                    ISNULL(c.Torre, '')
                                )
                            )
                        ),
                        ' ',
                        ''
                    ),
                    '-',
                    ''
                ),
                '_',
                ''
            ),

            REPLACE
            (
                REPLACE
                (
                    REPLACE
                    (
                        UPPER
                        (
                            LTRIM
                            (
                                RTRIM
                                (
                                    ISNULL(c.Turno, '')
                                )
                            )
                        ),
                        ' ',
                        ''
                    ),
                    '-',
                    ''
                ),
                '_',
                ''
            )
        )
    ) AS norm
    (
        Torre_Normalizada,
        Turno_Normalizado
    )

    WHERE
        c.Fecha BETWEEN
            @FechaInicioEfectiva
            AND @FechaFinEfectiva;

    /* ========================================================
       CONTROL DE DUPLICADOS EN CLAYS_CUFE
       ======================================================== */

    IF EXISTS
    (
        SELECT
            Fecha,
            Turno,
            Torre
        FROM #destino
        WHERE
            Turno IS NOT NULL
            AND Torre IS NOT NULL
        GROUP BY
            Fecha,
            Turno,
            Torre
        HAVING COUNT(*) > 1
    )
    BEGIN
        THROW 50007,
            'Clays_CuFe contiene claves duplicadas en el período solicitado.',
            1;
    END;

    /* ========================================================
       CLASIFICACIÓN DE ACCIONES
       ======================================================== */

    SELECT
        f.*,

        d.CaolBeta_Anterior,
        d.CuFe_Anterior,

        CASE
            WHEN d.Fecha IS NULL
                THEN 'INSERTAR'

            WHEN
            (
                f.CaolBeta_Nuevo IS NOT NULL
                AND
                (
                    d.CaolBeta_Anterior IS NULL
                    OR d.CaolBeta_Anterior <> f.CaolBeta_Nuevo
                )
            )
            OR
            (
                f.CuFe_Nuevo IS NOT NULL
                AND
                (
                    d.CuFe_Anterior IS NULL
                    OR d.CuFe_Anterior <> f.CuFe_Nuevo
                )
            )
                THEN 'ACTUALIZAR'

            ELSE 'SIN_CAMBIO'
        END AS Accion

    INTO #acciones

    FROM #fuente AS f

    LEFT JOIN #destino AS d
        ON d.Fecha = f.Fecha
       AND d.Turno = f.Turno
       AND d.Torre = f.Torre;

    /* ========================================================
       VISTA PREVIA
       ======================================================== */

    IF @SoloVistaPrevia = 1
    BEGIN
        SELECT
            @IdEjecucion AS id_ejecucion,
            @FechaInicioSolicitada AS fecha_inicio_solicitada,
            @FechaInicioEfectiva AS fecha_inicio_efectiva,
            @FechaFinEfectiva AS fecha_fin_efectiva,
            @FechaCorteProtegida AS fecha_corte_protegida;

        SELECT
            Accion,
            COUNT(*) AS Cantidad
        FROM #acciones
        GROUP BY
            Accion
        ORDER BY
            Accion;

        SELECT
            Fecha,
            Turno,
            Torre,
            Accion,

            Representatividad_Quimica,
            Representatividad_Quimica_TM2,

            CaolBeta_Anterior,
            CaolBeta_Nuevo,
            Fuente_CaolBeta,

            CuFe_Anterior,
            CuFe_Nuevo,
            Fuente_CuFe

        FROM #acciones

        ORDER BY
            Fecha,
            Turno,
            Torre;

        RETURN;
    END;

    /* ========================================================
       EJECUCIÓN REAL
       ======================================================== */

    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @ResultadoLock int;

        EXEC @ResultadoLock = sys.sp_getapplock
            @Resource =
                N'inventar_SpcHidr.sp_refrescar_clays_cufe',
            @LockMode = N'Exclusive',
            @LockOwner = N'Transaction',
            @LockTimeout = 10000;

        IF @ResultadoLock < 0
        BEGIN
            THROW 50008,
                'No fue posible obtener el bloqueo exclusivo del proceso.',
                1;
        END;

        /* ====================================================
           ACTUALIZACIÓN
           ==================================================== */

        UPDATE c
        SET
            c.CaolBeta =
                CASE
                    WHEN a.CaolBeta_Nuevo IS NOT NULL
                        THEN CONVERT(float, a.CaolBeta_Nuevo)
                    ELSE c.CaolBeta
                END,

            c.CuFe =
                CASE
                    WHEN a.CuFe_Nuevo IS NOT NULL
                        THEN CONVERT(float, a.CuFe_Nuevo)
                    ELSE c.CuFe
                END

        FROM
            [inventar_SpcHidr].[Clays_CuFe] AS c

        CROSS APPLY
        (
            VALUES
            (
                CASE
                    WHEN REPLACE
                    (
                        REPLACE
                        (
                            REPLACE
                            (
                                UPPER
                                (
                                    LTRIM
                                    (
                                        RTRIM
                                        (
                                            ISNULL(c.Torre, '')
                                        )
                                    )
                                ),
                                ' ',
                                ''
                            ),
                            '-',
                            ''
                        ),
                        '_',
                        ''
                    ) IN ('TM1', 'T1', 'TORRE1')
                        THEN 'TM1'

                    WHEN REPLACE
                    (
                        REPLACE
                        (
                            REPLACE
                            (
                                UPPER
                                (
                                    LTRIM
                                    (
                                        RTRIM
                                        (
                                            ISNULL(c.Torre, '')
                                        )
                                    )
                                ),
                                ' ',
                                ''
                            ),
                            '-',
                            ''
                        ),
                        '_',
                        ''
                    ) IN ('TM2', 'T2', 'TORRE2')
                        THEN 'TM2'
                END,

                CASE
                    WHEN REPLACE
                    (
                        REPLACE
                        (
                            REPLACE
                            (
                                UPPER
                                (
                                    LTRIM
                                    (
                                        RTRIM
                                        (
                                            ISNULL(c.Turno, '')
                                        )
                                    )
                                ),
                                ' ',
                                ''
                            ),
                            '-',
                            ''
                        ),
                        '_',
                        ''
                    ) IN ('A', 'TA', 'TURNOA')
                        THEN 'A'

                    WHEN REPLACE
                    (
                        REPLACE
                        (
                            REPLACE
                            (
                                UPPER
                                (
                                    LTRIM
                                    (
                                        RTRIM
                                        (
                                            ISNULL(c.Turno, '')
                                        )
                                    )
                                ),
                                ' ',
                                ''
                            ),
                            '-',
                            ''
                        ),
                        '_',
                        ''
                    ) IN ('B', 'TB', 'TURNOB')
                        THEN 'B'
                END
            )
        ) AS norm
        (
            Torre_Normalizada,
            Turno_Normalizado
        )

        INNER JOIN #acciones AS a
            ON a.Fecha = c.Fecha
           AND a.Torre = norm.Torre_Normalizada
           AND a.Turno = norm.Turno_Normalizado
           AND a.Accion = 'ACTUALIZAR';

        /* ====================================================
           INSERCIÓN
           ==================================================== */

        INSERT INTO
            [inventar_SpcHidr].[Clays_CuFe]
        (
            Fecha,
            Torre,
            Turno,
            Caolinita,
            Qz,
            CaolBeta,
            CuFe
        )
        SELECT
            a.Fecha,
            a.Torre_Destino,
            a.Turno_Destino,
            NULL,
            NULL,
            CONVERT(float, a.CaolBeta_Nuevo),
            CONVERT(float, a.CuFe_Nuevo)

        FROM #acciones AS a

        WHERE
            a.Accion = 'INSERTAR'
            AND
            (
                a.CaolBeta_Nuevo IS NOT NULL
                OR a.CuFe_Nuevo IS NOT NULL
            );

        /* ====================================================
           TRAZABILIDAD
           ==================================================== */

        INSERT INTO
            [inventar_SpcHidr].[Clays_CuFe_trazabilidad]
        (
            id_ejecucion,
            fecha_proceso,
            fecha_inicio_proceso,
            fecha_fin_proceso,
            accion,

            Fecha,
            Turno,
            Torre,

            Representatividad_Quimica,
            Representatividad_Quimica_TM2,

            ID_NIR,
            Muestra_NIR,
            CaolBeta_NIR,
            Fecha_Carga_NIR,

            ID_NIR_TM2,
            Muestra_NIR_TM2,
            CaolBeta_NIR_TM2,
            Fecha_Carga_NIR_TM2,

            CaolBeta_MB,
            CaolBeta_Final,
            CaolBeta_Final_2D,
            Fuente_CaolBeta,

            ID_Registro_CuFe,
            CuFe_Laboratorio,
            Fecha_Carga_Laboratorio,

            ID_Registro_CuFe_TM2,
            CuFe_Laboratorio_TM2,
            Fecha_Carga_Laboratorio_TM2,

            CuFe_MB,
            CuFe_Final,
            CuFe_Final_2D,
            Fuente_CuFe,

            CaolBeta_Anterior,
            CuFe_Anterior,

            usuario_ejecucion,
            host_ejecucion,
            aplicacion_ejecucion
        )
        SELECT
            @IdEjecucion,
            @FechaProceso,
            @FechaInicioEfectiva,
            @FechaFinEfectiva,
            a.Accion,

            a.Fecha,
            a.Turno,
            a.Torre,

            a.Representatividad_Quimica,
            a.Representatividad_Quimica_TM2,

            a.ID_NIR,
            a.Muestra_NIR,
            a.CaolBeta_NIR,
            a.Fecha_Carga_NIR,

            a.ID_NIR_TM2,
            a.Muestra_NIR_TM2,
            a.CaolBeta_NIR_TM2,
            a.Fecha_Carga_NIR_TM2,

            a.CaolBeta_MB,
            a.CaolBeta_Final,
            a.CaolBeta_Nuevo,
            a.Fuente_CaolBeta,

            a.ID_Registro_CuFe,
            a.CuFe_Laboratorio,
            a.Fecha_Carga_Laboratorio,

            a.ID_Registro_CuFe_TM2,
            a.CuFe_Laboratorio_TM2,
            a.Fecha_Carga_Laboratorio_TM2,

            a.CuFe_MB,
            a.CuFe_Final,
            a.CuFe_Nuevo,
            a.Fuente_CuFe,

            a.CaolBeta_Anterior,
            a.CuFe_Anterior,

            ORIGINAL_LOGIN(),
            HOST_NAME(),
            APP_NAME()

        FROM #acciones AS a

        WHERE
            a.Accion IN
            (
                'INSERTAR',
                'ACTUALIZAR'
            );

        COMMIT TRANSACTION;
    END TRY

    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        THROW;
    END CATCH;

    /* ========================================================
       RESULTADO DE LA EJECUCIÓN
       ======================================================== */

    SELECT
        @IdEjecucion AS id_ejecucion,
        @FechaInicioEfectiva AS fecha_inicio_efectiva,
        @FechaFinEfectiva AS fecha_fin_efectiva,
        @FechaProceso AS fecha_proceso,

        SUM
        (
            CASE
                WHEN Accion = 'INSERTAR' THEN 1
                ELSE 0
            END
        ) AS Registros_Insertados,

        SUM
        (
            CASE
                WHEN Accion = 'ACTUALIZAR' THEN 1
                ELSE 0
            END
        ) AS Registros_Actualizados,

        SUM
        (
            CASE
                WHEN Accion = 'SIN_CAMBIO' THEN 1
                ELSE 0
            END
        ) AS Registros_Sin_Cambio

    FROM #acciones;

    SELECT
        Fecha,
        Turno,
        Torre,
        Accion,

        CaolBeta_Anterior,
        CaolBeta_Nuevo,
        Fuente_CaolBeta,

        CuFe_Anterior,
        CuFe_Nuevo,
        Fuente_CuFe

    FROM #acciones

    WHERE
        Accion IN
        (
            'INSERTAR',
            'ACTUALIZAR'
        )

    ORDER BY
        Fecha,
        Turno,
        Torre;
END;
GO

-- ============================================================================
-- inventar_SpcHidr.sp_reporte_turno_emision_test (SQL_STORED_PROCEDURE)
-- Ultima modificacion: 2026-08-04 11:46:16.413000
-- ============================================================================
CREATE   PROCEDURE [inventar_SpcHidr].[sp_reporte_turno_emision_test]
    @fecha_inicio date,
    @fecha_fin    date
AS
BEGIN
    SET NOCOUNT ON;

    /* ============================================================
       LIMPIEZA TEMPORALES
       ============================================================ */

    DROP TABLE IF EXISTS #fechas;
    DROP TABLE IF EXISTS #hum;
    DROP TABLE IF EXISTS #hum_rep;
    DROP TABLE IF EXISTS #hum_torre_dia;
    DROP TABLE IF EXISTS #hum_torre_dia_final;
    DROP TABLE IF EXISTS #candidatos;
    DROP TABLE IF EXISTS #humedad_resuelta;
    DROP TABLE IF EXISTS #fes_candidatos_dia;
    DROP TABLE IF EXISTS #fes_dia_resuelta;

 /* ============================================================
   BLOQUE 1: TMH BASE DESDE APILADO
   Depuración anti-spike por correa/turno
   ============================================================ */

DECLARE @umbral_tmh_spike_turno decimal(18,6) = 150000.0;

WITH tmh_raw AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        CAST(ISNULL(TMH_CV008_A, 0) AS decimal(18,6)) AS TMH_CV008_A_Raw,
        CAST(ISNULL(TMH_CV008_B, 0) AS decimal(18,6)) AS TMH_CV008_B_Raw,
        CAST(ISNULL(TMH_CV108_A, 0) AS decimal(18,6)) AS TMH_CV108_A_Raw,
        CAST(ISNULL(TMH_CV108_B, 0) AS decimal(18,6)) AS TMH_CV108_B_Raw
    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2
    WHERE Fecha >= @fecha_inicio
      AND Fecha <  @fecha_fin
),
tmh_limpia AS
(
    SELECT
        Fecha,
        Flag_Apilado_Valido,

        CASE
            WHEN ABS(TMH_CV008_A_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV008_A_Raw
        END AS TMH_CV008_A,

        CASE
            WHEN ABS(TMH_CV008_B_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV008_B_Raw
        END AS TMH_CV008_B,

        CASE
            WHEN ABS(TMH_CV108_A_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV108_A_Raw
        END AS TMH_CV108_A,

        CASE
            WHEN ABS(TMH_CV108_B_Raw) > @umbral_tmh_spike_turno THEN 0
            ELSE TMH_CV108_B_Raw
        END AS TMH_CV108_B
    FROM tmh_raw
)
SELECT
    Fecha,
    Flag_Apilado_Valido,

    TMH_CV008_A,
    TMH_CV008_B,
    TMH_CV108_A,
    TMH_CV108_B,

    TMH_CV008_A + TMH_CV108_A AS TMH_Apilado_Total_A,
    TMH_CV008_B + TMH_CV108_B AS TMH_Apilado_Total_B,
    TMH_CV008_A + TMH_CV108_A + TMH_CV008_B + TMH_CV108_B AS TMH_Apilado_Total_Dia

INTO #fechas
FROM tmh_limpia;

/* ============================================================
   BLOQUE 2: HUMEDAD LABORATORIO
   Optimizado con ventana histórica razonable
   ============================================================ */

DECLARE @fecha_inicio_humedad date = DATEADD(DAY, -90, @fecha_inicio);

SELECT
    CAST(Fecha AS date) AS Fecha,
    Torre,
    Turno,
    AVG(CAST(Humedad_Prom_Pct AS float)) AS Humedad_Prom_Pct
INTO #hum
FROM inventar_SpcHidr.Informe_TM_lab
WHERE Humedad_Prom_Pct IS NOT NULL
  AND Fecha >= @fecha_inicio_humedad
  AND Fecha <  @fecha_fin
GROUP BY
    CAST(Fecha AS date),
    Torre,
    Turno;

CREATE CLUSTERED INDEX IX_hum
ON #hum (Fecha, Torre, Turno);

/* ============================================================
   BLOQUE 3: HUMEDAD + REPRESENTATIVIDAD FÍSICA
   Optimizado: usa resultado materializado
   ============================================================ */

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
INTO #hum_rep
FROM #hum h
LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado r
    ON r.Dia = h.Fecha;

CREATE CLUSTERED INDEX IX_hum_rep
ON #hum_rep (Fecha, Torre, Turno);

  /* ============================================================
   BLOQUE 4: HUMEDADES REPRESENTATIVAS POR FECHA + TURNO

   Corrección:
   - No se reduce A/B a una sola humedad diaria.
   - Se conserva el orden cronológico A -> B.
   - Cada TM prioriza su humedad propia.
   - Cuando no existe humedad propia más reciente, utiliza
     la humedad representativa vigente de la otra torre.
   ============================================================ */

SELECT
    Fecha,
    Torre,
    Turno AS Turno_Humedad,
    Humedad_Prom_Pct AS Humedad_Torre_Dia,
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

INTO #candidatos

FROM #hum_rep

WHERE Humedad_Prom_Pct IS NOT NULL
  AND Representatividad_Fisica >= 0.75;


CREATE CLUSTERED INDEX IX_candidatos
ON #candidatos
(
    FechaTurno_Origen DESC,
    Torre
);


/* ============================================================
   BLOQUE 5: RESOLUCIÓN CRONOLÓGICA POR FECHA + TURNO
   ============================================================ */

;WITH periodos AS
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

    FROM #fechas AS f

    CROSS JOIN
    (
        VALUES
            ('A'),
            ('B')
    ) AS t(Turno_Objetivo)
),

resuelta_turno AS
(
    SELECT
        p.Fecha,
        p.Turno_Objetivo,

        /* ====================================================
           TM1
           ==================================================== */

        tm1.Humedad_Torre_Dia
            AS Humedad_TM1,

        tm1.Fecha
            AS Fecha_Origen_TM1,

        tm1.Torre
            AS Torre_Origen_TM1,

        tm1.Turno_Humedad
            AS Turno_Origen_TM1,

        tm1.Fuente_Humedad
            AS Fuente_Humedad_TM1,

        /* ====================================================
           TM2
           ==================================================== */

        tm2.Humedad_Torre_Dia
            AS Humedad_TM2,

        tm2.Fecha
            AS Fecha_Origen_TM2,

        tm2.Torre
            AS Torre_Origen_TM2,

        tm2.Turno_Humedad
            AS Turno_Origen_TM2,

        tm2.Fuente_Humedad
            AS Fuente_Humedad_TM2

    FROM periodos AS p

    /* --------------------------------------------------------
       Resolución TM1
       -------------------------------------------------------- */

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno_Humedad,
            c.Humedad_Torre_Dia,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno_Humedad,
                h.Humedad_Torre_Dia,
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

            FROM #candidatos AS h

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

    /* --------------------------------------------------------
       Resolución TM2
       -------------------------------------------------------- */

    OUTER APPLY
    (
        SELECT TOP (1)
            c.Fecha,
            c.Torre,
            c.Turno_Humedad,
            c.Humedad_Torre_Dia,
            c.FechaTurno_Origen,
            c.Fuente_Humedad,
            c.Prioridad

        FROM
        (
            SELECT
                h.Fecha,
                h.Torre,
                h.Turno_Humedad,
                h.Humedad_Torre_Dia,
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

            FROM #candidatos AS h

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
   BLOQUE 6: PIVOT A/B Y HUMEDAD RESUELTA POR FECHA

   Las columnas Humedad_TM1 y Humedad_TM2 se mantienen para
   compatibilidad y representan el valor vigente al cierre del día.
   ============================================================ */

humedad_resuelta_cte AS
(
    SELECT
        f.*,

        /* Humedades efectivas por turno */

        a.Humedad_TM1 AS Humedad_TM1_A,
        b.Humedad_TM1 AS Humedad_TM1_B,

        a.Humedad_TM2 AS Humedad_TM2_A,
        b.Humedad_TM2 AS Humedad_TM2_B,

        /* Humedad vigente al cierre diario */

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

        /* Trazabilidad TM1 */

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

        /* Trazabilidad TM2 */

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

    FROM #fechas AS f

    LEFT JOIN resuelta_turno AS a
        ON a.Fecha = f.Fecha
       AND a.Turno_Objetivo = 'A'

    LEFT JOIN resuelta_turno AS b
        ON b.Fecha = f.Fecha
       AND b.Turno_Objetivo = 'B'
)

SELECT *
INTO #humedad_resuelta
FROM humedad_resuelta_cte;


CREATE CLUSTERED INDEX IX_humedad_resuelta
ON #humedad_resuelta (Fecha);
    /* ============================================================
   BLOQUE 7: FACTOR DE AJUSTE CAMIONES V2 + CÁLCULO TMS

   Fuente única de emisión:
       inventar_SpcHidr.v_ajuste_camiones_emision_test

   Regla:
   - Factor válido: aplica el factor diario a CV008/CV108 por turno.
   - Factor no evaluable: Factor_Aplicacion_Reportes = 1 (fallback),
     conservando por separado el estado real del cálculo.
   - El TMS se calcula DESDE LOS TMH AJUSTADOS.
   - Los bloques posteriores de sal, leyes, ponderaciones, IMP y
     clasificación permanecen sin cambios.
   ============================================================ */
DROP TABLE IF EXISTS #base_tms;
DROP TABLE IF EXISTS #tms_con_sal;

SELECT
    h.*,

    fac.Factor_Ajuste_Calculado,
    fac.Flag_Factor_Ajuste_Valido,
    fac.Flag_Usa_Ajuste,
    fac.Estado_Calculo AS Estado_Factor_Ajuste_Camiones,
    fac.Regla_Aplicacion AS Regla_Factor_Ajuste_Camiones,

    COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS Factor_Ajuste_Camiones_Usado,

    /* TMH ajustado por torre y turno */
    h.TMH_CV008_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV008_A_Factor,

    h.TMH_CV008_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV008_B_Factor,

    h.TMH_CV108_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV108_A_Factor,

    h.TMH_CV108_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_CV108_B_Factor,

    /* Totales ajustados */
    h.TMH_Apilado_Total_A
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_A_Factor,

    h.TMH_Apilado_Total_B
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_B_Factor,

    h.TMH_Apilado_Total_Dia
        * COALESCE(fac.Factor_Aplicacion_Reportes, 1.0)
        AS TMH_Apilado_Total_Dia_Factor

INTO #base_tms
FROM #humedad_resuelta AS h
LEFT JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test AS fac
    ON fac.Fecha = h.Fecha;

CREATE CLUSTERED INDEX IX_base_tms
    ON #base_tms (Fecha);

SELECT
    x.*,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A
           + x.TMS_TM2_Con_Sal_SRR_A
    END AS TMS_Total_Con_Sal_SRR_A,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_B
           + x.TMS_TM2_Con_Sal_SRR_B
    END AS TMS_Total_Con_Sal_SRR_B,

    CASE
        WHEN x.TMS_TM1_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM1_Con_Sal_SRR_B IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_A IS NULL
          OR x.TMS_TM2_Con_Sal_SRR_B IS NULL
            THEN NULL
        ELSE x.TMS_TM1_Con_Sal_SRR_A
           + x.TMS_TM1_Con_Sal_SRR_B
           + x.TMS_TM2_Con_Sal_SRR_A
           + x.TMS_TM2_Con_Sal_SRR_B
    END AS TMS_Total_Con_Sal_SRR_Dia

INTO #tms_con_sal
FROM
(
    SELECT
        b.*,

        CASE
            WHEN b.TMH_CV008_A_Factor = 0 THEN 0
            WHEN b.Humedad_TM1_A IS NULL THEN NULL
            ELSE b.TMH_CV008_A_Factor
                 * (1.0 - b.Humedad_TM1_A / 100.0)
        END AS TMS_TM1_Con_Sal_SRR_A,

        CASE
            WHEN b.TMH_CV008_B_Factor = 0 THEN 0
            WHEN b.Humedad_TM1_B IS NULL THEN NULL
            ELSE b.TMH_CV008_B_Factor
                 * (1.0 - b.Humedad_TM1_B / 100.0)
        END AS TMS_TM1_Con_Sal_SRR_B,

        CASE
            WHEN b.TMH_CV108_A_Factor = 0 THEN 0
            WHEN b.Humedad_TM2_A IS NULL THEN NULL
            ELSE b.TMH_CV108_A_Factor
                 * (1.0 - b.Humedad_TM2_A / 100.0)
        END AS TMS_TM2_Con_Sal_SRR_A,

        CASE
            WHEN b.TMH_CV108_B_Factor = 0 THEN 0
            WHEN b.Humedad_TM2_B IS NULL THEN NULL
            ELSE b.TMH_CV108_B_Factor
                 * (1.0 - b.Humedad_TM2_B / 100.0)
        END AS TMS_TM2_Con_Sal_SRR_B,

        CASE
            WHEN b.TMH_Apilado_Total_Dia_Factor = 0
                THEN 0

            WHEN b.TMH_CV008_A_Factor > 0
             AND b.Humedad_TM1_A IS NULL
                THEN NULL

            WHEN b.TMH_CV008_B_Factor > 0
             AND b.Humedad_TM1_B IS NULL
                THEN NULL

            WHEN b.TMH_CV108_A_Factor > 0
             AND b.Humedad_TM2_A IS NULL
                THEN NULL

            WHEN b.TMH_CV108_B_Factor > 0
             AND b.Humedad_TM2_B IS NULL
                THEN NULL

            ELSE
                (
                    b.TMH_CV008_A_Factor * b.Humedad_TM1_A
                  + b.TMH_CV008_B_Factor * b.Humedad_TM1_B
                  + b.TMH_CV108_A_Factor * b.Humedad_TM2_A
                  + b.TMH_CV108_B_Factor * b.Humedad_TM2_B
                )
                /
                NULLIF(b.TMH_Apilado_Total_Dia_Factor, 0)
        END AS Humedad_Equivalente_Dia

    FROM #base_tms AS b
) AS x;

CREATE CLUSTERED INDEX IX_tms_con_sal
    ON #tms_con_sal (Fecha);

/* ============================================================
   BLOQUE 8: SAL AJUSTADA + DESCUENTO DE SAL
   ============================================================ */

DROP TABLE IF EXISTS #sal_ajustada;
DROP TABLE IF EXISTS #tms_sin_sal;

SELECT
    v.Fecha,
    v.Sal_Pesometros_TA,
    v.Sal_Pesometros_TB,
    v.Sal_Pesometros_Dia,
    v.Sal_Topografia_Dia,
    v.Flag_Sal_Basica_Valida,
    v.Flag_Sal_Ajuste_Valido,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia
               * ISNULL(v.Sal_Pesometros_TA, 0)
               / NULLIF(v.Sal_Pesometros_Dia, 0)

        ELSE ISNULL(v.Sal_Ajustada_TA, 0)
    END AS Sal_Ajustada_TA,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia
               * ISNULL(v.Sal_Pesometros_TB, 0)
               / NULLIF(v.Sal_Pesometros_Dia, 0)

        ELSE ISNULL(v.Sal_Ajustada_TB, 0)
    END AS Sal_Ajustada_TB,

    CASE
        WHEN ISNULL(v.Flag_Sal_Ajuste_Valido, 0) = 0
         AND ISNULL(v.Sal_Topografia_Dia, 0) > 0
         AND ISNULL(v.Sal_Pesometros_Dia, 0) > 0
            THEN v.Sal_Topografia_Dia

        ELSE ISNULL(v.Sal_Ajustada_Dia, 0)
    END AS Sal_Ajustada_Dia

INTO #sal_ajustada
FROM inventar_SpcHidr.v_sal_ajustada v
WHERE v.Fecha >= @fecha_inicio
  AND v.Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_sal_ajustada
ON #sal_ajustada (Fecha);


SELECT
    t.*,

    s.Sal_Pesometros_TA,
    s.Sal_Pesometros_TB,
    s.Sal_Pesometros_Dia,
    s.Sal_Topografia_Dia,

    s.Flag_Sal_Basica_Valida,
    s.Flag_Sal_Ajuste_Valido,

    s.Sal_Ajustada_TA,
    s.Sal_Ajustada_TB,
    s.Sal_Ajustada_Dia,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_A = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TA, 0)
             * t.TMS_TM1_Con_Sal_SRR_A
             / NULLIF(t.TMS_Total_Con_Sal_SRR_A, 0)
    END AS Sal_Asignada_TM1_A,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_A IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_A = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TA, 0)
             * t.TMS_TM2_Con_Sal_SRR_A
             / NULLIF(t.TMS_Total_Con_Sal_SRR_A, 0)
    END AS Sal_Asignada_TM2_A,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_B = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TB, 0)
             * t.TMS_TM1_Con_Sal_SRR_B
             / NULLIF(t.TMS_Total_Con_Sal_SRR_B, 0)
    END AS Sal_Asignada_TM1_B,

    CASE
        WHEN t.TMS_Total_Con_Sal_SRR_B IS NULL THEN NULL
        WHEN t.TMS_Total_Con_Sal_SRR_B = 0 THEN 0
        ELSE COALESCE(s.Sal_Ajustada_TB, 0)
             * t.TMS_TM2_Con_Sal_SRR_B
             / NULLIF(t.TMS_Total_Con_Sal_SRR_B, 0)
    END AS Sal_Asignada_TM2_B

INTO #tms_sin_sal
FROM #tms_con_sal t
LEFT JOIN #sal_ajustada s
    ON s.Fecha = t.Fecha;

CREATE CLUSTERED INDEX IX_tms_sin_sal
ON #tms_sin_sal (Fecha);
/* ============================================================
   BLOQUE 9: TMS SIN SAL EN FORMATO FECHA / TURNO / TM
   ============================================================ */

DROP TABLE IF EXISTS #tms_tm;

SELECT
    Fecha,
    Turno,
    TM,
    TMS
INTO #tms_tm
FROM (
    SELECT
        Fecha,
        'A' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Con_Sal_SRR_A - COALESCE(Sal_Asignada_TM1_A, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'A' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Con_Sal_SRR_A - COALESCE(Sal_Asignada_TM2_A, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Con_Sal_SRR_B - COALESCE(Sal_Asignada_TM1_B, 0) AS TMS
    FROM #tms_sin_sal

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Con_Sal_SRR_B - COALESCE(Sal_Asignada_TM2_B, 0) AS TMS
    FROM #tms_sin_sal
) x;

CREATE CLUSTERED INDEX IX_tms_tm
ON #tms_tm (Fecha, Turno, TM);
/* ============================================================
   BLOQUE 10: LEYES BASE RESUELTAS POR FECHA / TURNO / TM
   ============================================================ */

DROP TABLE IF EXISTS #leyes_base;

DECLARE @fecha_inicio_leyes_arrastre date =
    DATEADD(DAY, -90, @fecha_inicio);

SELECT *
INTO #leyes_base
FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
WHERE Fecha >= @fecha_inicio_leyes_arrastre
  AND Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_leyes_base_fecha_turno_tm
ON #leyes_base (Fecha, Turno, TM);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_fes
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (FeS, Fuente_FeS);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_consh
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (ConsH, Fuente_ConsH);

CREATE NONCLUSTERED INDEX IX_leyes_base_arrastre_malla12
ON #leyes_base (TM, Fecha, Turno)
INCLUDE (Malla_Menos_1_2, Fuente_Malla_Menos_1_2);
/* ============================================================
   BLOQUE 10A: RESOLUCIÓN CRONOLÓGICA DE FeS

   RN-067:
   - El orden operacional es Fecha + Turno A + Turno B.
   - El turno A puede completar el turno B.
   - El turno B no puede modificar retroactivamente el turno A.
   - El valor nuevo del turno B rige desde B hacia adelante.
   - TM2 puede completar TM1.
   - TM1 no puede completar TM2.
   ============================================================ */

DROP TABLE IF EXISTS #fes_candidatos_dia;
DROP TABLE IF EXISTS #fes_dia_resuelta;

/* ------------------------------------------------------------
   Eventos originales válidos de FeS.

   TORRE_OTRO_TURNO_MISMO_DIA no se considera evento original,
   porque puede contener una compartición bidireccional previa.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,
    b.FeS,
    b.Fuente_FeS AS Fuente_Origen

INTO #fes_candidatos_dia

FROM #leyes_base AS b

WHERE b.FeS IS NOT NULL
  AND b.Fuente_FeS IN
  (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );

CREATE CLUSTERED INDEX IX_fes_candidatos_dia
ON #fes_candidatos_dia
(
    Fecha,
    Turno_Origen,
    TM_Origen
);

/* ------------------------------------------------------------
   Resolver cada Fecha + Turno + TM utilizando únicamente
   información cronológicamente disponible.
   ------------------------------------------------------------ */

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    c.FeS AS FeS_Nuevo_Dia,
    c.TM_Origen,
    c.Turno_Origen,

    CASE
        WHEN c.FeS IS NULL
            THEN NULL

        WHEN c.Fecha_Origen < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        /* Misma TM y mismo turno */
        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA'

        /* A completa B en la misma TM */
        WHEN c.TM_Origen = b.TM
         AND b.Turno = 'B'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_QUIMICA_OTRO_TURNO'

        /* TM2 completa TM1 en el mismo turno */
        WHEN b.TM = 'TM1'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1'

        /* TM2-A completa TM1-B */
        WHEN b.TM = 'TM1'
         AND b.Turno = 'B'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = 'A'
            THEN
                'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1_OTRO_TURNO'

        ELSE NULL
    END AS Fuente_Nuevo_Dia

INTO #fes_dia_resuelta

FROM #leyes_base AS b

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha AS Fecha_Origen,
        x.Turno_Origen,
        x.TM_Origen,
        x.FeS,
        x.Fuente_Origen

    FROM #fes_candidatos_dia AS x

    WHERE
        /* Misma TM o compartición permitida TM2 → TM1 */
        (
            x.TM_Origen = b.TM

            OR
            (
                b.TM = 'TM1'
                AND x.TM_Origen = 'TM2'
            )
        )

        /* Restricción cronológica */
        AND
        (
            x.Fecha < b.Fecha

            OR
            (
                x.Fecha = b.Fecha

                AND
                CASE
                    WHEN x.Turno_Origen = 'A' THEN 1
                    WHEN x.Turno_Origen = 'B' THEN 2
                    ELSE 9
                END
                <=
                CASE
                    WHEN b.Turno = 'A' THEN 1
                    WHEN b.Turno = 'B' THEN 2
                    ELSE 9
                END
            )
        )

    ORDER BY
        x.Fecha DESC,

        /* B es posterior a A */
        CASE
            WHEN x.Turno_Origen = 'B' THEN 2
            WHEN x.Turno_Origen = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igualdad temporal, priorizar la propia TM */
        CASE
            WHEN x.TM_Origen = b.TM THEN 1

            WHEN b.TM = 'TM1'
             AND x.TM_Origen = 'TM2' THEN 2

            ELSE 9
        END,

        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 9
        END

) AS c;

CREATE CLUSTERED INDEX IX_fes_dia_resuelta
ON #fes_dia_resuelta
(
    TM,
    Turno,
    Fecha
);
/* ============================================================
   BLOQUE 11A: RESOLUCIÓN CRONOLÓGICA MALLA -1/2

   Regla:
   - El orden operacional es Fecha + turno A + turno B.
   - Una medición válida del turno A puede completar B.
   - Una medición del turno B no puede modificar A.
   - El valor nuevo del turno B rige desde B hacia adelante.
   - TM2 puede completar TM1.
   - TM1 no completa TM2.
   - Se excluyen comparticiones bidireccionales previamente
     generadas por TORRE_OTRO_TURNO_MISMO_DIA.
   ============================================================ */

DROP TABLE IF EXISTS #malla12_candidata_dia_tm;
DROP TABLE IF EXISTS #malla12_dia_resuelta;

/* ------------------------------------------------------------
   Eventos originales válidos
   ------------------------------------------------------------ */

SELECT
    b.Fecha AS Fecha_Origen,
    b.Turno AS Turno_Origen,
    b.TM AS TM_Origen,

    b.Malla_Menos_1_2,
    b.Fuente_Malla_Menos_1_2 AS Fuente_Origen

INTO #malla12_candidata_dia_tm

FROM #leyes_base AS b

WHERE b.Malla_Menos_1_2 IS NOT NULL
  AND b.Malla_Menos_1_2 <> 0
  AND b.Fuente_Malla_Menos_1_2 IN
  (
      'TORRE_MISMO_TURNO',
      'SEMILLA_INICIO_PERIODO'
  );


CREATE CLUSTERED INDEX IX_malla12_candidata_fecha_turno_tm
ON #malla12_candidata_dia_tm
(
    Fecha_Origen,
    Turno_Origen,
    TM_Origen
);


/* ------------------------------------------------------------
   Resolver cada Fecha + Turno + TM utilizando solamente
   información disponible hasta ese instante.
   ------------------------------------------------------------ */

;WITH base AS
(
    SELECT DISTINCT
        Fecha,
        Turno,
        TM
    FROM #leyes_base
)

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    c.Fecha_Origen,
    c.Turno_Origen,
    c.TM_Origen,

    c.Malla_Menos_1_2,
    c.Fuente_Origen,

    CASE
        WHEN c.Malla_Menos_1_2 IS NULL
            THEN NULL

        /* El dato proviene de una fecha anterior */
        WHEN c.Fecha_Origen < b.Fecha
            THEN 'ARRASTRE_ULTIMO_VALIDO'

        WHEN c.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
            THEN 'SEMILLA_INICIO_PERIODO'

        /* Misma TM y mismo turno */
        WHEN c.TM_Origen = b.TM
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_FISICA'

        /* El turno A completa B en la misma TM */
        WHEN c.TM_Origen = b.TM
         AND b.Turno = 'B'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_FISICA_OTRO_TURNO'

        /* TM2 completa TM1 en el mismo turno */
        WHEN b.TM = 'TM1'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = b.Turno
            THEN 'TORRE_REP_FISICA_COMPARTIDA'

        /* TM2-A completa TM1-B */
        WHEN b.TM = 'TM1'
         AND b.Turno = 'B'
         AND c.TM_Origen = 'TM2'
         AND c.Turno_Origen = 'A'
            THEN 'TORRE_REP_FISICA_COMPARTIDA_OTRO_TURNO'

        ELSE NULL
    END AS Fuente_Malla_Resuelta

INTO #malla12_dia_resuelta

FROM base AS b

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha_Origen,
        x.Turno_Origen,
        x.TM_Origen,
        x.Malla_Menos_1_2,
        x.Fuente_Origen

    FROM #malla12_candidata_dia_tm AS x

    WHERE
        /* Misma TM o completitud permitida TM2 → TM1 */
        (
            x.TM_Origen = b.TM

            OR
            (
                b.TM = 'TM1'
                AND x.TM_Origen = 'TM2'
            )
        )

        /* El evento no puede ocurrir después del turno objetivo */
        AND
        (
            x.Fecha_Origen < b.Fecha

            OR
            (
                x.Fecha_Origen = b.Fecha

                AND
                CASE
                    WHEN x.Turno_Origen = 'A' THEN 1
                    WHEN x.Turno_Origen = 'B' THEN 2
                    ELSE 9
                END
                <=
                CASE
                    WHEN b.Turno = 'A' THEN 1
                    WHEN b.Turno = 'B' THEN 2
                    ELSE 9
                END
            )
        )

    ORDER BY
        /* Evento cronológico más reciente */
        x.Fecha_Origen DESC,

        CASE
            WHEN x.Turno_Origen = 'B' THEN 2
            WHEN x.Turno_Origen = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igualdad temporal, priorizar la propia TM */
        CASE
            WHEN x.TM_Origen = b.TM
                THEN 1

            WHEN b.TM = 'TM1'
             AND x.TM_Origen = 'TM2'
                THEN 2

            ELSE 9
        END,

        CASE
            WHEN x.Fuente_Origen = 'TORRE_MISMO_TURNO'
                THEN 1

            WHEN x.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
                THEN 2

            ELSE 9
        END

) AS c;


CREATE CLUSTERED INDEX
    IX_malla12_dia_resuelta_fecha_turno_tm

ON #malla12_dia_resuelta
(
    Fecha,
    Turno,
    TM
);
/* ============================================================
   BLOQUE 11B: ARRASTRE ÚLTIMO VALOR VÁLIDO
   FeS, ConsH y Malla -1/2
   ============================================================ */

DROP TABLE IF EXISTS #leyes_v2;

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    b.CuT,
    b.Fuente_CuT,

    b.CuS,
    b.Fuente_CuS,

    b.CO3,
    b.Fuente_CO3,

    b.CuFe,
    b.Fuente_CuFe,

    b.FeT,
    b.Fuente_FeT,

   ult_fes.FeS_Nuevo_Dia AS FeS,

CASE
    WHEN ult_fes.FeS_Nuevo_Dia IS NULL
        THEN b.Fuente_FeS

    WHEN ult_fes.Fecha = b.Fecha
        THEN ult_fes.Fuente_Nuevo_Dia

    WHEN ult_fes.Fecha < b.Fecha
        THEN 'ARRASTRE_ULTIMO_VALIDO'

    ELSE b.Fuente_FeS
END AS Fuente_FeS,

    ult_fes.Fecha AS Fecha_Origen_FeS,
    b.Turno AS Turno_Origen_FeS,
    b.TM AS TM_Origen_FeS,
/* ============================================================
   ConsH con resolución cronológica

   - A puede completar B.
   - B no puede modificar retroactivamente A.
   - TM2 puede completar TM1.
   - TM1 no completa TM2.
   ============================================================ */

CASE
    WHEN b.ConsH IS NOT NULL
     AND b.ConsH <> 0
     AND b.Fuente_ConsH <> 'NO_APLICA_MINA'

     /* Para A, TORRE_OTRO_TURNO significa que tomó el dato de B */
     AND NOT
     (
         b.Turno = 'A'
         AND b.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
     )
        THEN b.ConsH

    ELSE ult_consh.ConsH
END AS ConsH,

CASE
    /* Valor propio o completitud cronológicamente válida */
    WHEN b.ConsH IS NOT NULL
     AND b.ConsH <> 0
     AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
     AND NOT
     (
         b.Turno = 'A'
         AND b.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
     )
        THEN b.Fuente_ConsH

    WHEN ult_consh.ConsH IS NULL
        THEN b.Fuente_ConsH

    /* Valor de una fecha anterior */
    WHEN ult_consh.Fecha < b.Fecha
        THEN 'ARRASTRE_ULTIMO_VALIDO'

    /* Misma TM y mismo turno */
    WHEN ult_consh.Fecha = b.Fecha
     AND ult_consh.TM_Origen = b.TM
     AND ult_consh.Turno_Origen = b.Turno
        THEN ult_consh.Fuente_ConsH

    /* A completa B dentro de la misma TM */
    WHEN ult_consh.Fecha = b.Fecha
     AND ult_consh.TM_Origen = b.TM
     AND b.Turno = 'B'
     AND ult_consh.Turno_Origen = 'A'
        THEN 'TORRE_OTRO_TURNO_MISMO_DIA'

    /* TM2 completa TM1 */
    WHEN ult_consh.Fecha = b.Fecha
     AND b.TM = 'TM1'
     AND ult_consh.TM_Origen = 'TM2'
        THEN 'TORRE_REP_QUIMICA_COMPARTIDA_TM2_A_TM1'

    ELSE 'ARRASTRE_ULTIMO_VALIDO'
END AS Fuente_ConsH,

    ult_consh.Fecha AS Fecha_Origen_ConsH,
    ult_consh.Turno_Origen AS Turno_Origen_ConsH,
    ult_consh.TM_Origen AS TM_Origen_ConsH,

   ult_malla.Malla_Menos_1_2
    AS Malla_Menos_1_2,

CASE
    WHEN ult_malla.Malla_Menos_1_2 IS NULL
        THEN b.Fuente_Malla_Menos_1_2

    ELSE ult_malla.Fuente_Malla_Resuelta

END AS Fuente_Malla_Menos_1_2,

    ult_malla.Fecha_Origen AS Fecha_Origen_Malla_Menos_1_2,
    ult_malla.Turno_Origen AS Turno_Origen_Malla_Menos_1_2,
    ult_malla.TM_Origen AS TM_Origen_Malla_Menos_1_2,

    b.Malla_Menos_100,
    b.Fuente_Malla_Menos_100,

    b.CaolBeta,
    b.Fuente_CaolBeta

INTO #leyes_v2
FROM #leyes_base b

OUTER APPLY (
    SELECT TOP (1)
        x.Fecha,
        x.FeS_Nuevo_Dia,
        x.Fuente_Nuevo_Dia
    FROM #fes_dia_resuelta x
    WHERE x.TM = b.TM
      AND x.Turno = b.Turno
      AND x.Fecha <= b.Fecha
      AND x.FeS_Nuevo_Dia IS NOT NULL
    ORDER BY
        x.Fecha DESC
) ult_fes

OUTER APPLY
(
    SELECT TOP (1)
        x.Fecha,
        x.Turno AS Turno_Origen,
        x.TM AS TM_Origen,
        x.ConsH,
        x.Fuente_ConsH

    FROM #leyes_base AS x

    WHERE x.ConsH IS NOT NULL
      AND x.ConsH <> 0
      AND x.Fuente_ConsH <> 'NO_APLICA_MINA'

      /* Excluir los A que fueron poblados desde el B futuro */
      AND NOT
      (
          x.Turno = 'A'
          AND x.Fuente_ConsH = 'TORRE_OTRO_TURNO_MISMO_DIA'
      )

      /* Misma TM o compartición permitida TM2 → TM1 */
      AND
      (
          x.TM = b.TM
          OR
          (
              b.TM = 'TM1'
              AND x.TM = 'TM2'
          )
      )

      /* Restricción cronológica:
         - Para objetivo A: solo A del mismo día.
         - Para objetivo B: A o B del mismo día.
         - Siempre se permiten fechas anteriores.
      */
      AND
      (
          x.Fecha < b.Fecha

          OR
          (
              x.Fecha = b.Fecha
              AND
              (
                  (b.Turno = 'A' AND x.Turno = 'A')
                  OR
                  (b.Turno = 'B' AND x.Turno IN ('A', 'B'))
              )
          )
      )

    ORDER BY
        x.Fecha DESC,

        /* B es posterior a A */
        CASE
            WHEN x.Turno = 'B' THEN 2
            WHEN x.Turno = 'A' THEN 1
            ELSE 0
        END DESC,

        /* Ante igual instante, priorizar la propia TM */
        CASE
            WHEN x.TM = b.TM THEN 1
            WHEN b.TM = 'TM1' AND x.TM = 'TM2' THEN 2
            ELSE 9
        END,

        /* Priorizar medición original */
        CASE
            WHEN x.Fuente_ConsH = 'TORRE_MISMO_TURNO' THEN 1
            WHEN x.Fuente_ConsH = 'SEMILLA_INICIO_PERIODO' THEN 2
            ELSE 3
        END

) AS ult_consh
OUTER APPLY
(
    SELECT TOP (1)
        d.Fecha,
        d.Turno,
        d.TM,

        d.Fecha_Origen,
        d.Turno_Origen,
        d.TM_Origen,

        d.Malla_Menos_1_2,
        d.Fuente_Origen,
        d.Fuente_Malla_Resuelta

    FROM #malla12_dia_resuelta AS d

    WHERE d.TM = b.TM
      AND d.Turno = b.Turno
      AND d.Fecha <= b.Fecha
      AND d.Malla_Menos_1_2 IS NOT NULL

    ORDER BY
        d.Fecha DESC

) AS ult_malla;

CREATE CLUSTERED INDEX IX_leyes_v2_fecha_turno_tm
ON #leyes_v2 (Fecha, Turno, TM);

/* ============================================================
   TRAZABILIDAD: estado inicial de #leyes_v2
   Los bloques posteriores actualizan esta metadata junto con el valor.
   ============================================================ */
DROP TABLE IF EXISTS #trazabilidad_analitos;

SELECT
    l.Fecha,
    l.Turno,
    l.TM AS TM_Destino,
    a.Analito,
    a.Valor_Final,
    CASE
        WHEN a.Valor_Final IS NULL THEN NULL
        WHEN a.Fuente_Tecnica = 'MINA' THEN 'MB'
        WHEN a.Fuente_Tecnica = 'IMP' THEN 'IMP'
        WHEN a.TM_Origen IN ('TM1', 'TM2')
         AND a.Fuente_Tecnica IN
             ('ARRASTRE_ULTIMO_VALIDO', 'SEMILLA_INICIO_PERIODO')
            THEN a.TM_Origen
        WHEN a.Fuente_Tecnica LIKE '%TORRE%' AND a.TM_Origen = 'TM1' THEN 'TM1'
        WHEN a.Fuente_Tecnica LIKE '%TORRE%' AND a.TM_Origen = 'TM2' THEN 'TM2'
        WHEN a.Fuente_Tecnica = 'SEMILLA_INICIO_PERIODO'
             AND a.TM_Origen IN ('TM1', 'TM2') THEN a.TM_Origen
    END AS Fuente_Base,
    a.Fuente_Tecnica,
    a.Fecha_Origen,
    a.Turno_Origen,
    a.TM_Origen,
    CASE
        WHEN a.Valor_Final IS NULL THEN 'SIN_DATO'
        WHEN a.Fuente_Tecnica = 'MINA' THEN 'FALLBACK_MB'
        WHEN a.Fuente_Tecnica = 'IMP' THEN 'PROVISIONAL_IMP'
        WHEN a.Fuente_Tecnica = 'ARRASTRE_ULTIMO_VALIDO' THEN 'ARRASTRE'
        WHEN a.Fuente_Tecnica = 'SEMILLA_INICIO_PERIODO' THEN 'SEMILLA'
        WHEN a.Fuente_Tecnica LIKE '%OTRO_TURNO%' THEN 'OTRO_TURNO'
        WHEN a.Fuente_Tecnica LIKE '%COMPARTIDA%' THEN 'COMPARTIDO_TM2_A_TM1'
        WHEN a.Fuente_Tecnica LIKE '%TORRE%' THEN 'PROPIO'
        ELSE 'SIN_DATO'
    END AS Resolucion
INTO #trazabilidad_analitos
FROM #leyes_v2 AS l
CROSS APPLY
(
    VALUES
      ('CuT', l.CuT, l.Fuente_CuT, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CuT LIKE '%TORRE%' THEN l.TM END),
      ('CuS', l.CuS, l.Fuente_CuS, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CuS LIKE '%TORRE%' THEN l.TM END),
      ('FeT', l.FeT, l.Fuente_FeT, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_FeT LIKE '%TORRE%' THEN l.TM END),
      ('FeS', l.FeS, l.Fuente_FeS, l.Fecha_Origen_FeS,
          l.Turno_Origen_FeS, l.TM_Origen_FeS),
      ('CO3', l.CO3, l.Fuente_CO3, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CO3 LIKE '%TORRE%' THEN l.TM END),
      ('ConsH', l.ConsH, l.Fuente_ConsH, l.Fecha_Origen_ConsH,
          l.Turno_Origen_ConsH, l.TM_Origen_ConsH),
      ('CuFe', l.CuFe, l.Fuente_CuFe, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CuFe LIKE '%TORRE%' THEN l.TM END),
      ('CaolBeta', l.CaolBeta, l.Fuente_CaolBeta, l.Fecha, l.Turno,
          CASE WHEN l.Fuente_CaolBeta LIKE '%TORRE%' THEN l.TM END),
      ('Malla_Menos_1_2', l.Malla_Menos_1_2, l.Fuente_Malla_Menos_1_2,
          l.Fecha_Origen_Malla_Menos_1_2, l.Turno_Origen_Malla_Menos_1_2,
          l.TM_Origen_Malla_Menos_1_2),
      ('Malla_Menos_100', l.Malla_Menos_100, l.Fuente_Malla_Menos_100,
          l.Fecha, l.Turno,
          CASE WHEN l.Fuente_Malla_Menos_100 LIKE '%TORRE%' THEN l.TM END)
) AS a(Analito, Valor_Final, Fuente_Tecnica, Fecha_Origen, Turno_Origen, TM_Origen);

/* La etiqueta técnica conserva explícitamente la compartición TM2 -> TM1. */
UPDATE #trazabilidad_analitos
SET Fuente_Base = 'TM2',
    TM_Origen = 'TM2',
    Resolucion = 'COMPARTIDO_TM2_A_TM1'
WHERE Fuente_Tecnica LIKE '%COMPARTIDA%TM2%TM1%';

CREATE UNIQUE CLUSTERED INDEX IX_trazabilidad_analitos_clave
ON #trazabilidad_analitos (Fecha, Turno, TM_Destino, Analito);

/* ============================================================
   BLOQUE 11C - Ajuste CuFe según regla oficial
   Si representatividad química > 0.75, usar Clays_CuFe.
   Si no cumple, mantener CuFe ya resuelto desde MINA/Conciliación.
   ============================================================ */

UPDATE tr
SET
    tr.Fuente_Base = CASE
        WHEN v.Fuente_CuFe LIKE 'LAB_TM2_%' THEN 'TM2'
        WHEN v.Fuente_CuFe LIKE 'LAB_PROPIO_%' THEN l.TM
        WHEN v.Fuente_CuFe LIKE 'MB_%' THEN 'MB'
        WHEN v.Fuente_CuFe LIKE 'IMP%' THEN 'IMP'
    END,
    tr.Fuente_Tecnica = v.Fuente_CuFe,
    tr.Fecha_Origen = l.Fecha,
    tr.Turno_Origen = l.Turno,
    tr.TM_Origen = CASE
        WHEN v.Fuente_CuFe LIKE 'LAB_TM2_%' THEN 'TM2'
        WHEN v.Fuente_CuFe LIKE 'LAB_PROPIO_%' THEN l.TM
    END,
    tr.Resolucion = CASE
        WHEN v.Fuente_CuFe LIKE 'LAB_TM2_%' THEN 'COMPARTIDO_TM2_A_TM1'
        WHEN v.Fuente_CuFe LIKE 'LAB_PROPIO_%' THEN 'PROPIO'
        WHEN v.Fuente_CuFe LIKE 'MB_%' THEN 'FALLBACK_MB'
        WHEN v.Fuente_CuFe LIKE 'IMP%' THEN 'PROVISIONAL_IMP'
        ELSE 'SIN_DATO'
    END
FROM #trazabilidad_analitos AS tr
INNER JOIN #leyes_v2 AS l
    ON l.Fecha = tr.Fecha AND l.Turno = tr.Turno AND l.TM = tr.TM_Destino
INNER JOIN inventar_SpcHidr.representatividad_torres_resultado AS r
    ON r.Dia = l.Fecha
INNER JOIN inventar_SpcHidr.v_clays_cufe_calculado_v2_test AS v
    ON v.Fecha = l.Fecha AND v.Turno = l.Turno AND v.Torre = l.TM
CROSS APPLY (VALUES (CASE
    WHEN l.TM = 'TM1' AND l.Turno = 'A' THEN r.TM1_TurnoA_Quimico
    WHEN l.TM = 'TM1' AND l.Turno = 'B' THEN r.TM1_TurnoB_Quimico
    WHEN l.TM = 'TM2' AND l.Turno = 'A' THEN r.TM2_TurnoA_Quimico
    WHEN l.TM = 'TM2' AND l.Turno = 'B' THEN r.TM2_TurnoB_Quimico
END)) AS rep(Rep_Raw)
CROSS APPLY (VALUES
    (CASE WHEN rep.Rep_Raw > 1 THEN rep.Rep_Raw / 100.0 ELSE rep.Rep_Raw END)
) AS rn(Rep_Normalizada)
WHERE tr.Analito = 'CuFe'
  AND v.CuFe_Final_2D IS NOT NULL
  AND ISNULL(rn.Rep_Normalizada, 0) > 0.75;

UPDATE l
SET
    l.CuFe = TRY_CAST(c.CuFe AS float),
    l.Fuente_CuFe = 'TORRE'
FROM #leyes_v2 l
INNER JOIN inventar_SpcHidr.representatividad_torres_resultado r
    ON r.Dia = l.Fecha
INNER JOIN inventar_SpcHidr.Clays_CuFe c
    ON c.Fecha = l.Fecha
   AND c.Turno = CASE
                    WHEN l.Turno = 'A' THEN 'TA'
                    WHEN l.Turno = 'B' THEN 'TB'
                 END
   AND c.Torre = CASE
                    WHEN l.TM = 'TM1' THEN 'TM-1'
                    WHEN l.TM = 'TM2' THEN 'TM-2'
                 END
CROSS APPLY (
    SELECT
        CASE
            WHEN l.TM = 'TM1' AND l.Turno = 'A' THEN r.TM1_TurnoA_Quimico
            WHEN l.TM = 'TM1' AND l.Turno = 'B' THEN r.TM1_TurnoB_Quimico
            WHEN l.TM = 'TM2' AND l.Turno = 'A' THEN r.TM2_TurnoA_Quimico
            WHEN l.TM = 'TM2' AND l.Turno = 'B' THEN r.TM2_TurnoB_Quimico
        END AS Rep_Quimica_Raw
) rep
CROSS APPLY (
    SELECT
        CASE
            WHEN rep.Rep_Quimica_Raw > 1
                THEN rep.Rep_Quimica_Raw / 100.0
            ELSE rep.Rep_Quimica_Raw
        END AS Rep_Quimica_Normalizada
) rep_norm
WHERE TRY_CAST(c.CuFe AS float) IS NOT NULL
  AND ISNULL(rep_norm.Rep_Quimica_Normalizada, 0) > 0.75;

  /* ============================================================
   BLOQUE 11C.1 - Completitud CuFe TM2 -> TM1

   Si TM2 tiene CuFe representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.

   Esta regla alinea CuFe con la completitud asimétrica ya aplicada
   para CuT, CuS, CO3 y FeT.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'LAB_TM2_COMPARTIDO',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos AS tr
INNER JOIN #leyes_v2 AS tm1
    ON tm1.Fecha = tr.Fecha AND tm1.Turno = tr.Turno AND tm1.TM = tr.TM_Destino
INNER JOIN #leyes_v2 AS tm2
    ON tm2.Fecha = tm1.Fecha AND tm2.Turno = tm1.Turno AND tm2.TM = 'TM2'
WHERE tr.Analito = 'CuFe' AND tm1.TM = 'TM1'
  AND tm2.CuFe IS NOT NULL AND tm2.Fuente_CuFe LIKE '%TORRE%'
  AND (tm1.CuFe IS NULL OR ISNULL(tm1.Fuente_CuFe, '') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.CuFe = tm2.CuFe,
    tm1.Fuente_CuFe = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuFe IS NOT NULL
  AND tm2.Fuente_CuFe LIKE '%TORRE%'
  AND (
        tm1.CuFe IS NULL
     OR ISNULL(tm1.Fuente_CuFe, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11D - Ajuste FeT según regla oficial

   Si TM2 tiene FeT representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.

   Esto evita ponderar TM1 MINA + TM2 TORRE cuando el oficial clasifica
   el turno como TM2 y usa el valor representativo de TM2.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 tm1 ON tm1.Fecha=tr.Fecha AND tm1.Turno=tr.Turno AND tm1.TM=tr.TM_Destino
JOIN #leyes_v2 tm2 ON tm2.Fecha=tm1.Fecha AND tm2.Turno=tm1.Turno AND tm2.TM='TM2'
WHERE tr.Analito='FeT' AND tm1.TM='TM1' AND tm2.FeT IS NOT NULL
  AND tm2.Fuente_FeT LIKE '%TORRE%'
  AND (tm1.FeT IS NULL OR ISNULL(tm1.Fuente_FeT,'') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.FeT = tm2.FeT,
    tm1.Fuente_FeT = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.FeT IS NOT NULL
  AND tm2.Fuente_FeT LIKE '%TORRE%'
  AND (
        tm1.FeT IS NULL
     OR ISNULL(tm1.Fuente_FeT, '') NOT LIKE '%TORRE%'
  );

  /* ============================================================
   BLOQUE 11E - Ajuste CO3 según regla oficial

   Si TM2 tiene CO3 representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 tm1 ON tm1.Fecha=tr.Fecha AND tm1.Turno=tr.Turno AND tm1.TM=tr.TM_Destino
JOIN #leyes_v2 tm2 ON tm2.Fecha=tm1.Fecha AND tm2.Turno=tm1.Turno AND tm2.TM='TM2'
WHERE tr.Analito='CO3' AND tm1.TM='TM1' AND tm2.CO3 IS NOT NULL
  AND tm2.Fuente_CO3 LIKE '%TORRE%'
  AND (tm1.CO3 IS NULL OR ISNULL(tm1.Fuente_CO3,'') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.CO3 = tm2.CO3,
    tm1.Fuente_CO3 = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CO3 IS NOT NULL
  AND tm2.Fuente_CO3 LIKE '%TORRE%'
  AND (
        tm1.CO3 IS NULL
     OR ISNULL(tm1.Fuente_CO3, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11F - Ajuste CaolBeta según reporte oficial

   CaolBeta se toma desde Clays_CuFe cuando existe dato para
   Fecha + Turno + TM. No depende de Conciliación Chancado
   cuando existe dato NIR/Clays disponible.
   ============================================================ */

UPDATE tr
SET
    tr.Fuente_Base = CASE
        WHEN v.Fuente_CaolBeta LIKE 'NIR_TM2_%' THEN 'TM2'
        WHEN v.Fuente_CaolBeta LIKE 'NIR_PROPIO_%' THEN l.TM
        WHEN v.Fuente_CaolBeta LIKE 'MB_%' THEN 'MB'
        WHEN v.Fuente_CaolBeta LIKE 'IMP%' THEN 'IMP'
    END,
    tr.Fuente_Tecnica = v.Fuente_CaolBeta,
    tr.Fecha_Origen = l.Fecha,
    tr.Turno_Origen = l.Turno,
    tr.TM_Origen = CASE
        WHEN v.Fuente_CaolBeta LIKE 'NIR_TM2_%' THEN 'TM2'
        WHEN v.Fuente_CaolBeta LIKE 'NIR_PROPIO_%' THEN l.TM
    END,
    tr.Resolucion = CASE
        WHEN v.Fuente_CaolBeta LIKE 'NIR_TM2_%' THEN 'COMPARTIDO_TM2_A_TM1'
        WHEN v.Fuente_CaolBeta LIKE 'NIR_PROPIO_%' THEN 'PROPIO'
        WHEN v.Fuente_CaolBeta LIKE 'MB_%' THEN 'FALLBACK_MB'
        WHEN v.Fuente_CaolBeta LIKE 'IMP%' THEN 'PROVISIONAL_IMP'
        ELSE 'SIN_DATO'
    END
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 l
  ON l.Fecha=tr.Fecha AND l.Turno=tr.Turno AND l.TM=tr.TM_Destino
JOIN inventar_SpcHidr.v_clays_cufe_calculado_v2_test v
  ON v.Fecha=l.Fecha AND v.Turno=l.Turno AND v.Torre=l.TM
WHERE tr.Analito='CaolBeta' AND v.CaolBeta_Final_2D IS NOT NULL;

UPDATE l
SET
    l.CaolBeta = clay.CaolBeta_Clays,
    l.Fuente_CaolBeta = 'CLAYS'
FROM #leyes_v2 l
INNER JOIN inventar_SpcHidr.Clays_CuFe c
    ON c.Fecha = l.Fecha
   AND c.Turno = CASE
                    WHEN l.Turno = 'A' THEN 'TA'
                    WHEN l.Turno = 'B' THEN 'TB'
                 END
   AND c.Torre = CASE
                    WHEN l.TM = 'TM1' THEN 'TM-1'
                    WHEN l.TM = 'TM2' THEN 'TM-2'
                 END
OUTER APPLY (
    SELECT
        TRY_CONVERT(float, REPLACE(CONVERT(varchar(50), c.CaolBeta), ',', '.')) AS CaolBeta_Clays
) clay
WHERE clay.CaolBeta_Clays IS NOT NULL;

/* ============================================================
   BLOQUE 11G - Ajuste CuT según regla oficial

   Si TM2 tiene CuT representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 tm1 ON tm1.Fecha=tr.Fecha AND tm1.Turno=tr.Turno AND tm1.TM=tr.TM_Destino
JOIN #leyes_v2 tm2 ON tm2.Fecha=tm1.Fecha AND tm2.Turno=tm1.Turno AND tm2.TM='TM2'
WHERE tr.Analito='CuT' AND tm1.TM='TM1' AND tm2.CuT IS NOT NULL
  AND tm2.Fuente_CuT LIKE '%TORRE%'
  AND (tm1.CuT IS NULL OR ISNULL(tm1.Fuente_CuT,'') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.CuT = tm2.CuT,
    tm1.Fuente_CuT = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuT IS NOT NULL
  AND tm2.Fuente_CuT LIKE '%TORRE%'
  AND (
        tm1.CuT IS NULL
     OR ISNULL(tm1.Fuente_CuT, '') NOT LIKE '%TORRE%'
  );
  /* ============================================================
   BLOQUE 11H - Ajuste CuS según regla oficial

   Si TM2 tiene CuS representativo de torre para la misma Fecha + Turno,
   puede completar TM1 cuando TM1 no tiene dato representativo propio.
   ============================================================ */

UPDATE tr
SET tr.Fuente_Base = 'TM2', tr.Fuente_Tecnica = 'TORRE_COMPARTIDA_TM2_A_TM1',
    tr.Fecha_Origen = tm1.Fecha, tr.Turno_Origen = tm1.Turno,
    tr.TM_Origen = 'TM2', tr.Resolucion = 'COMPARTIDO_TM2_A_TM1'
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 tm1 ON tm1.Fecha=tr.Fecha AND tm1.Turno=tr.Turno AND tm1.TM=tr.TM_Destino
JOIN #leyes_v2 tm2 ON tm2.Fecha=tm1.Fecha AND tm2.Turno=tm1.Turno AND tm2.TM='TM2'
WHERE tr.Analito='CuS' AND tm1.TM='TM1' AND tm2.CuS IS NOT NULL
  AND tm2.Fuente_CuS LIKE '%TORRE%'
  AND (tm1.CuS IS NULL OR ISNULL(tm1.Fuente_CuS,'') NOT LIKE '%TORRE%');

UPDATE tm1
SET
    tm1.CuS = tm2.CuS,
    tm1.Fuente_CuS = 'TORRE'
FROM #leyes_v2 tm1
INNER JOIN #leyes_v2 tm2
    ON tm2.Fecha = tm1.Fecha
   AND tm2.Turno = tm1.Turno
   AND tm2.TM = 'TM2'
WHERE tm1.TM = 'TM1'
  AND tm2.CuS IS NOT NULL
  AND tm2.Fuente_CuS LIKE '%TORRE%'
  AND (
        tm1.CuS IS NULL
     OR ISNULL(tm1.Fuente_CuS, '') NOT LIKE '%TORRE%'
  );
/* ============================================================
   BLOQUE 11I - Guarda de evaluabilidad por origen operacional

   RN-064 ampliada:
   - El TMS siempre proviene de CV008/CV108.
   - STOCK, MINA y SRR constituyen evidencia oficial.
   - IMP positivo constituye evidencia operacional provisional.
   - IMP no reemplaza ni distribuye el TMS.
   - Si CV008/CV108 entregan TMS cero, IMP no habilita tonelaje.
   ============================================================ */

UPDATE t
SET
    t.TMS = 0
FROM #tms_tm AS t

LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr AS o
    ON o.Fecha = t.Fecha
   AND o.Turno = t.Turno

LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS c
    ON c.Fecha = t.Fecha
   AND c.Turno = t.Turno

WHERE ISNULL(t.TMS, 0) > 0

  /* No existe evidencia operacional oficial */
  AND ISNULL(o.Ton_Stock_Camiones, 0) = 0
  AND ISNULL(o.Ton_Mina_Camiones, 0) = 0
  AND ISNULL(o.Ton_SRR, 0) = 0

  /* Tampoco existe evidencia provisional IMP */
  AND NOT
  (
      UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato, '')))) = 'IMP'
      AND ISNULL(c.Ton, 0) > 0
  );

/* ============================================================
   BLOQUE 12: PONDERACIÓN DE LEYES REALES POR TMS
   ============================================================ */

/* TRAZABILIDAD FINAL: despues de resoluciones y antes de ponderacion. */
UPDATE tr
SET tr.Valor_Final = CASE tr.Analito
    WHEN 'CuT' THEN l.CuT WHEN 'CuS' THEN l.CuS WHEN 'FeT' THEN l.FeT
    WHEN 'FeS' THEN l.FeS WHEN 'CO3' THEN l.CO3 WHEN 'ConsH' THEN l.ConsH
    WHEN 'CuFe' THEN l.CuFe WHEN 'CaolBeta' THEN l.CaolBeta
    WHEN 'Malla_Menos_1_2' THEN l.Malla_Menos_1_2
    WHEN 'Malla_Menos_100' THEN l.Malla_Menos_100 END
FROM #trazabilidad_analitos tr
JOIN #leyes_v2 l
  ON l.Fecha=tr.Fecha AND l.Turno=tr.Turno AND l.TM=tr.TM_Destino;

DELETE FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
WHERE Fecha >= @fecha_inicio AND Fecha < @fecha_fin;

INSERT INTO inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
(
    Fecha, Turno, TM_Destino, Analito, Valor_Final,
    Fuente_Base, Fuente_Tecnica, Fecha_Origen, Turno_Origen, TM_Origen,
    Resolucion, Representatividad_Quimica, Representatividad_Fisica,
    Fecha_Proceso
)
SELECT
    tr.Fecha, tr.Turno, tr.TM_Destino, tr.Analito, tr.Valor_Final,
    CASE WHEN tr.Valor_Final IS NULL THEN NULL ELSE tr.Fuente_Base END,
    tr.Fuente_Tecnica, tr.Fecha_Origen, tr.Turno_Origen, tr.TM_Origen,
    CASE WHEN tr.Valor_Final IS NULL THEN 'SIN_DATO' ELSE tr.Resolucion END,
    TRY_CONVERT(decimal(18,10), rep.Rep_Quimica),
    TRY_CONVERT(decimal(18,10), rep.Rep_Fisica), SYSDATETIME()
FROM #trazabilidad_analitos tr
LEFT JOIN inventar_SpcHidr.representatividad_torres_resultado r
  ON r.Dia=tr.Fecha
CROSS APPLY (VALUES
(
    CASE
      WHEN tr.TM_Destino='TM1' AND tr.Turno='A' THEN r.TM1_TurnoA_Quimico
      WHEN tr.TM_Destino='TM1' AND tr.Turno='B' THEN r.TM1_TurnoB_Quimico
      WHEN tr.TM_Destino='TM2' AND tr.Turno='A' THEN r.TM2_TurnoA_Quimico
      WHEN tr.TM_Destino='TM2' AND tr.Turno='B' THEN r.TM2_TurnoB_Quimico END,
    CASE
      WHEN tr.TM_Destino='TM1' AND tr.Turno='A' THEN r.TM1_TurnoA_Fisico
      WHEN tr.TM_Destino='TM1' AND tr.Turno='B' THEN r.TM1_TurnoB_Fisico
      WHEN tr.TM_Destino='TM2' AND tr.Turno='A' THEN r.TM2_TurnoA_Fisico
      WHEN tr.TM_Destino='TM2' AND tr.Turno='B' THEN r.TM2_TurnoB_Fisico END
)) rep(Rep_Quimica, Rep_Fisica)
WHERE tr.Fecha >= @fecha_inicio AND tr.Fecha < @fecha_fin;

DROP TABLE IF EXISTS #reales;

SELECT
    t.Fecha,
    t.Turno,

    SUM(t.TMS) AS Apilado_TMS_Real,

    SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuT_Real,

    SUM(t.TMS * l.CuS) / NULLIF(SUM(CASE WHEN l.CuS IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuS_Real,

    CASE
        WHEN SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) IS NULL
          OR SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0) = 0
        THEN NULL
        ELSE
            (
                SUM(t.TMS * l.CuS) / NULLIF(SUM(CASE WHEN l.CuS IS NOT NULL THEN t.TMS ELSE 0 END), 0)
            )
            /
            (
                SUM(t.TMS * l.CuT) / NULLIF(SUM(CASE WHEN l.CuT IS NOT NULL THEN t.TMS ELSE 0 END), 0)
            )
    END AS Solubilidad_Real,

    SUM(t.TMS * l.CO3) / NULLIF(SUM(CASE WHEN l.CO3 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CO3_Real,

    SUM(t.TMS * l.CuFe) / NULLIF(SUM(CASE WHEN l.CuFe IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CuFe_Real,

    SUM(t.TMS * l.FeT) / NULLIF(SUM(CASE WHEN l.FeT IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS FeT_Real,

    SUM(t.TMS * l.FeS) / NULLIF(SUM(CASE WHEN l.FeS IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS FeS_Real,

    SUM(t.TMS * l.ConsH) / NULLIF(SUM(CASE WHEN l.ConsH IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS ConsH_Real,

    SUM(t.TMS * l.Malla_Menos_1_2) / NULLIF(SUM(CASE WHEN l.Malla_Menos_1_2 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS Malla_Menos_1_2_Real,

    SUM(t.TMS * l.Malla_Menos_100) / NULLIF(SUM(CASE WHEN l.Malla_Menos_100 IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS Malla_Menos_100_Real,

    SUM(t.TMS * l.CaolBeta) / NULLIF(SUM(CASE WHEN l.CaolBeta IS NOT NULL THEN t.TMS ELSE 0 END), 0) AS CaolBeta_Real

INTO #reales
FROM #tms_tm t
LEFT JOIN #leyes_v2 l
    ON l.Fecha = t.Fecha
   AND l.Turno = t.Turno
   AND l.TM = t.TM
GROUP BY
    t.Fecha,
    t.Turno;

CREATE CLUSTERED INDEX IX_reales_fecha_turno
ON #reales (Fecha, Turno);

/* ============================================================
   BLOQUE 13: CLASIFICACIÓN DE MUESTRA QUÍMICA Y FÍSICA

   Ajuste:
   - Se incorpora IMP como fuente válida de conciliación.
   - No se modifica la prioridad de TORRE, MINA, ARRASTRE
     ni SEMILLA.
   ============================================================ */

DROP TABLE IF EXISTS #muestras;

WITH fuentes AS
(
    SELECT
        Fecha,
        Turno,

        /* ----------------------------------------------------
           Fuentes químicas
           ---------------------------------------------------- */

        MAX
        (
            CASE
                WHEN Fuente_CuT  LIKE '%TORRE%'
                  OR Fuente_CuS  LIKE '%TORRE%'
                  OR Fuente_CO3  LIKE '%TORRE%'
                  OR Fuente_CuFe LIKE '%TORRE%'
                  OR Fuente_FeT  LIKE '%TORRE%'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Torre,

        MAX
        (
            CASE
                WHEN Fuente_CuT  = 'MINA'
                  OR Fuente_CuS  = 'MINA'
                  OR Fuente_CO3  = 'MINA'
                  OR Fuente_CuFe = 'MINA'
                  OR Fuente_FeT  = 'MINA'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Mina,

        /* Nueva clasificación IMP */
        MAX
        (
            CASE
                WHEN Fuente_CuT  = 'IMP'
                  OR Fuente_CuS  = 'IMP'
                  OR Fuente_CO3  = 'IMP'
                  OR Fuente_CuFe = 'IMP'
                  OR Fuente_FeT  = 'IMP'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_IMP,

        MAX
        (
            CASE
                WHEN Fuente_FeS  = 'ARRASTRE_ULTIMO_VALIDO'
                  OR Fuente_ConsH = 'ARRASTRE_ULTIMO_VALIDO'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Arrastre,

        MAX
        (
            CASE
                WHEN Fuente_CuT   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CuS   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CO3   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_CuFe  = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_FeT   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_FeS   = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_ConsH = 'SEMILLA_INICIO_PERIODO'
                    THEN 1
                ELSE 0
            END
        ) AS Quimica_Semilla,

        /* ----------------------------------------------------
           Fuentes físicas
           ---------------------------------------------------- */

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                  OR Fuente_Malla_Menos_100 LIKE '%TORRE%'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Torre,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'MINA'
                  OR Fuente_Malla_Menos_100 = 'MINA'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Mina,

        /* Nueva clasificación IMP */
        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'IMP'
                  OR Fuente_Malla_Menos_100 = 'IMP'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_IMP,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'ARRASTRE_ULTIMO_VALIDO'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Arrastre,

        MAX
        (
            CASE
                WHEN Fuente_Malla_Menos_1_2 = 'SEMILLA_INICIO_PERIODO'
                  OR Fuente_Malla_Menos_100 = 'SEMILLA_INICIO_PERIODO'
                    THEN 1
                ELSE 0
            END
        ) AS Fisica_Semilla

    FROM #leyes_v2

    GROUP BY
        Fecha,
        Turno
)

SELECT
    Fecha,
    Turno,

    CASE
        WHEN Quimica_Semilla = 1
            THEN 'SEMILLA'

        WHEN Quimica_Arrastre = 1
         AND
         (
             Quimica_Torre = 1
             OR Quimica_Mina = 1
             OR Quimica_IMP = 1
         )
            THEN 'MIXTA'

        WHEN Quimica_Torre + Quimica_Mina + Quimica_IMP >= 2
            THEN 'MIXTA'

        WHEN Quimica_Arrastre = 1
            THEN 'ARRASTRE'

        WHEN Quimica_Torre = 1
            THEN 'TORRE'

        WHEN Quimica_IMP = 1
            THEN 'IMP'

        WHEN Quimica_Mina = 1
            THEN 'MINA'

        ELSE NULL
    END AS Muestra_Quimica,

    CASE
        WHEN Fisica_Semilla = 1
            THEN 'SEMILLA'

        WHEN Fisica_Arrastre = 1
         AND
         (
             Fisica_Torre = 1
             OR Fisica_Mina = 1
             OR Fisica_IMP = 1
         )
            THEN 'MIXTA'

        WHEN Fisica_Torre + Fisica_Mina + Fisica_IMP >= 2
            THEN 'MIXTA'

        WHEN Fisica_Arrastre = 1
            THEN 'ARRASTRE'

        WHEN Fisica_Torre = 1
            THEN 'TORRE'

        WHEN Fisica_IMP = 1
            THEN 'IMP'

        WHEN Fisica_Mina = 1
            THEN 'MINA'

        ELSE NULL
    END AS Muestra_Fisica

INTO #muestras

FROM fuentes;

CREATE CLUSTERED INDEX IX_muestras_fecha_turno
ON #muestras (Fecha, Turno);
/* ============================================================
   BLOQUE 14: CAMPAÑA, MÓDULO, AVANCE Y PLAN
   ============================================================ */

DROP TABLE IF EXISTS #campania_modulo;
DROP TABLE IF EXISTS #plan_mensual;
DROP TABLE IF EXISTS #plan_semanal;
DROP TABLE IF EXISTS #origen_apilado;

SELECT
    Fecha,
    Fecha_Origen_Relleno,
    Fecha_Topografia_Usada,
    Campania,
    Material,
    Modulo,
    Avance,
    Volumen_Diario_Modulo_m3,
    Fuente_Campania_Modulo
INTO #campania_modulo
FROM inventar_SpcHidr.v_reporte_turno_campania_modulo_test
WHERE Fecha >= @fecha_inicio
  AND Fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_campania_modulo
ON #campania_modulo (Fecha);


/* ============================================================
   PLAN MENSUAL
   ============================================================ */

SELECT
    fecha AS Fecha,
    apilamiento AS Apilado_TMS_Plan_Mensual,
    cut AS CuT_Plan_Mensual,
    cus AS CuS_Plan_Mensual,
    CAST(
    CASE
        WHEN cut IS NULL OR cut = 0 OR cus IS NULL THEN NULL
        ELSE cus / cut
    END
    AS decimal(18, 6)) AS Solubilidad_Plan_Mensual,
    co3 AS CO3_Plan_Mensual,
    cl_acido AS ConsH_Plan_Mensual,
    cufe AS CuFe_Plan_Mensual,
    malla_100 AS Malla_Menos_100_Plan_Mensual,
    caol_beta AS CaolBeta_Plan_Mensual
INTO #plan_mensual
FROM inventar_SpcHidr.plan_mensual_reporte_turno
WHERE fecha >= @fecha_inicio
  AND fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_plan_mensual
ON #plan_mensual (Fecha);


/* ============================================================
   PLAN SEMANAL
   ============================================================ */

SELECT
    fecha AS Fecha,
    ton AS Apilado_TMS_Plan_Semanal,
    cut AS CuT_Plan_Semanal,
    cus AS CuS_Plan_Semanal,
    CAST(
    CASE
        WHEN cut IS NULL OR cut = 0 OR cus IS NULL THEN NULL
        ELSE cus / cut
    END
    AS decimal(18, 6)) AS Solubilidad_Plan_Semanal,
    co3 AS CO3_Plan_Semanal,
    cl_acido AS ConsH_Plan_Semanal,
    cufe AS CuFe_Plan_Semanal,
    malla_100 AS Malla_Menos_100_Plan_Semanal,
    betaclay AS CaolBeta_Plan_Semanal,
    porc_1_2 AS Malla_Menos_1_2_Plan_Semanal,
    arcillas AS Arcillas_Plan_Semanal,
    cuarzo AS Cuarzo_Plan_Semanal
INTO #plan_semanal
FROM inventar_SpcHidr.plan_semanal_reporte_turno
WHERE fecha >= @fecha_inicio
  AND fecha <  @fecha_fin;

CREATE CLUSTERED INDEX IX_plan_semanal
ON #plan_semanal (Fecha);


 /* ============================================================
   BLOQUE 15: DISTRIBUCIÓN FINAL STOCK / MINA / SRR

   Prioridad:
   1. Origen oficial desde mov_cam.
   2. IMP provisional:
      - SRR = Es_SRR = 1
      - Camiones = STOCK
      - MINA = 0
   3. Sin origen: proporciones en cero.

   IMPORTANTE:
   IMP no reemplaza Apilado_TMS_Real.
   Solo determina las proporciones de origen.
   ============================================================ */

DROP TABLE IF EXISTS #imp_origen_turno;
DROP TABLE IF EXISTS #origen_apilado;


/* ------------------------------------------------------------
   15A. Consolidación IMP por Fecha + Turno
   ------------------------------------------------------------ */

SELECT
    CAST(i.Fecha AS date) AS Fecha,

    CASE
        WHEN i.Turno IN ('TA', 'A') THEN 'A'
        WHEN i.Turno IN ('TB', 'B') THEN 'B'
        ELSE i.Turno
    END COLLATE DATABASE_DEFAULT AS Turno,

    CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 1
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_SRR,

    CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 0
                 AND UPPER(LTRIM(RTRIM(ISNULL(i.Tipo_Registro, ''))))
                     = 'CAMION'
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_Camiones,

		  CAST
    (
        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 0
                 AND UPPER(LTRIM(RTRIM(ISNULL(i.Tipo_Registro, ''))))
                     = 'MINA'
                    THEN ISNULL(i.Ton, 0)
                ELSE 0
            END
        )
        AS decimal(38,10)
    ) AS Ton_IMP_mina,

    CAST
    (
        SUM(ISNULL(i.Ton, 0))
        AS decimal(38,10)
    ) AS Ton_IMP_Total

INTO #imp_origen_turno

FROM DEV_SIIR.hidro.v_imp_chancado_normalizado AS i

WHERE i.Fecha >= @fecha_inicio
  AND i.Fecha <  @fecha_fin
  AND ISNULL(i.Ton, 0) > 0

GROUP BY
    CAST(i.Fecha AS date),

    CASE
        WHEN i.Turno IN ('TA', 'A') THEN 'A'
        WHEN i.Turno IN ('TB', 'B') THEN 'B'
        ELSE i.Turno
    END COLLATE DATABASE_DEFAULT;


CREATE CLUSTERED INDEX IX_imp_origen_turno
ON #imp_origen_turno (Fecha, Turno);


/* ------------------------------------------------------------
   15B. Determinación de la fuente de origen
   ------------------------------------------------------------ */

;WITH origen_base AS
(
    SELECT
        r.Fecha,
        r.Turno,

        CAST
        (
            ISNULL(r.Apilado_TMS_Real, 0)
            AS decimal(38,10)
        ) AS Apilado_TMS_Real,

        /* Fuente oficial */

        CAST
        (
            ISNULL(p.Ton_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Stock_Oficial,

        CAST
        (
            ISNULL(p.Ton_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Mina_Oficial,

        CAST
        (
            ISNULL(p.Ton_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_SRR_Oficial,

        CAST
        (
            ISNULL(p.Prop_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Prop_Stock_Oficial,

        CAST
        (
            ISNULL(p.Prop_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Prop_Mina_Oficial,

        /* Fuente IMP */

        CAST
        (
            ISNULL(i.Ton_IMP_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_SRR,

        CAST
        (
            ISNULL(i.Ton_IMP_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Camiones,

				CAST
        (
            ISNULL(i.Ton_IMP_mina, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_mina,

        CAST
        (
            ISNULL(i.Ton_IMP_Total, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Total,

        c.Fuente_Dato,

        CASE
            /* Prioridad 1: origen oficial positivo */

            WHEN ISNULL(p.Ton_Stock_Camiones, 0) > 0
              OR ISNULL(p.Ton_Mina_Camiones, 0) > 0
              OR ISNULL(p.Ton_SRR, 0) > 0
                THEN 'OFICIAL'

            /* Prioridad 2: respaldo provisional IMP */

            WHEN UPPER
                 (
                     LTRIM
                     (
                         RTRIM
                         (
                             ISNULL(c.Fuente_Dato, '')
                         )
                     )
                 ) = 'IMP'
             AND ISNULL(i.Ton_IMP_Total, 0) > 0
                THEN 'IMP'

            ELSE 'SIN_ORIGEN'
        END AS Fuente_Origen

    FROM #reales AS r

    LEFT JOIN inventar_SpcHidr.v_apilado_base_mina_stock_srr AS p
        ON p.Fecha = r.Fecha
       AND p.Turno = r.Turno

    LEFT JOIN #imp_origen_turno AS i
        ON i.Fecha = r.Fecha
       AND i.Turno = r.Turno

    LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 AS c
        ON c.Fecha = r.Fecha
       AND c.Turno = r.Turno
),

origen_srr AS
(
    SELECT
        b.*,

        /* SRR limitado al Apilado_TMS_Real */

        CAST
        (
            CASE
                WHEN b.Apilado_TMS_Real <= 0
                    THEN 0

                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN
                        CASE
                            WHEN b.Ton_SRR_Oficial <= 0
                                THEN 0

                            WHEN b.Ton_SRR_Oficial
                               > b.Apilado_TMS_Real
                                THEN b.Apilado_TMS_Real

                            ELSE b.Ton_SRR_Oficial
                        END

                WHEN b.Fuente_Origen = 'IMP'
                    THEN
                        CASE
                            WHEN b.Ton_IMP_SRR <= 0
                                THEN 0

                            WHEN b.Ton_IMP_SRR
                               > b.Apilado_TMS_Real
                                THEN b.Apilado_TMS_Real

                            ELSE b.Ton_IMP_SRR
                        END

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Ton_SRR_Usado,

        /* Proporción de camiones STOCK */

        CAST
        (
            CASE
                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN b.Prop_Stock_Oficial

                WHEN b.Fuente_Origen = 'IMP'
                 AND b.Ton_IMP_Camiones > 0
                    THEN (b.Ton_IMP_Camiones/(b.Ton_IMP_Total-b.Ton_IMP_SRR))

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Prop_Stock_Camiones_Usada,

        /* Proporción de camiones MINA */

        CAST
        (
            CASE
                WHEN b.Fuente_Origen = 'OFICIAL'
                    THEN b.Prop_Mina_Oficial

                WHEN b.Fuente_Origen = 'IMP'
                    AND b.Ton_IMP_mina > 0
                    THEN (b.Ton_IMP_mina/(b.Ton_IMP_Total-b.Ton_IMP_SRR))

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Prop_Mina_Camiones_Usada

    FROM origen_base AS b
),

origen_calculado AS
(
    SELECT
        s.*,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE

									((s.Apilado_TMS_Real- s.Ton_SRR_Usado)*
										s.Prop_Stock_Camiones_Usada)/s.Apilado_TMS_Real

            END
            AS decimal(18,8)
        ) AS Prop_Final_Stock,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
								((s.Apilado_TMS_Real- s.Ton_SRR_Usado)*
										s.Prop_Mina_Camiones_Usada)/s.Apilado_TMS_Real


            END
            AS decimal(18,8)
        ) AS Prop_Final_Mina,

        CAST
        (
            CASE
                WHEN s.Apilado_TMS_Real <= 0
                    THEN 0

                ELSE
                    s.Ton_SRR_Usado
                    / NULLIF(s.Apilado_TMS_Real, 0)
            END
            AS decimal(18,8)
        ) AS Prop_Final_SRR

    FROM origen_srr AS s
)

SELECT
    o.Fecha,
    o.Turno,

    o.Prop_Final_Stock,
    o.Prop_Final_Mina,
    o.Prop_Final_SRR,

    CAST
    (
        o.Prop_Final_Stock
      + o.Prop_Final_Mina
      + o.Prop_Final_SRR
        AS decimal(18,8)
    ) AS Prop_Final_Total,

    /* Diferencia de tonelaje contra TMS real */

    CAST
    (
        (
            (
                o.Apilado_TMS_Real
              - o.Ton_SRR_Usado
            )
            * o.Prop_Stock_Camiones_Usada
        )
      + (
            (
                o.Apilado_TMS_Real
              - o.Ton_SRR_Usado
            )
            * o.Prop_Mina_Camiones_Usada
        )
      + o.Ton_SRR_Usado
      - o.Apilado_TMS_Real

        AS decimal(18,8)
    ) AS Check_Distribucion_Apilado,

    /* Columnas de auditoría */

    o.Fuente_Origen,
    o.Ton_SRR_Usado,
    o.Ton_IMP_SRR,
    o.Ton_IMP_Camiones,
    o.Ton_Stock_Oficial,
    o.Ton_Mina_Oficial,
    o.Ton_SRR_Oficial

INTO #origen_apilado

FROM origen_calculado AS o;


CREATE CLUSTERED INDEX IX_origen_apilado
ON #origen_apilado (Fecha, Turno);

/* ============================================================
   SELECT FINAL - ORDEN FORMATO BHP
   ============================================================ */

SELECT
    r.Fecha,
    cm.Campania,
    cm.Material,
    cm.Modulo,
    cm.Avance,
    r.Turno,

    /* Apilado */
    r.Apilado_TMS_Real,
    pm.Apilado_TMS_Plan_Mensual,

    /* Distribución de origen */
    CAST(100.0 * COALESCE(oa.Prop_Final_Stock, 0) AS decimal(18, 2)) AS STOCK,
    CAST(100.0 * COALESCE(oa.Prop_Final_Mina, 0) AS decimal(18, 2)) AS MINA,
    CAST(100.0 * COALESCE(oa.Prop_Final_SRR, 0) AS decimal(18, 2)) AS SRR,

    /* Análisis químicos */
    r.CuT_Real,
    pm.CuT_Plan_Mensual,
    ps.CuT_Plan_Semanal,

    r.CuS_Real,
    pm.CuS_Plan_Mensual,
    ps.CuS_Plan_Semanal,

    r.Solubilidad_Real,
    pm.Solubilidad_Plan_Mensual,
    ps.Solubilidad_Plan_Semanal,

    r.CO3_Real,
    pm.CO3_Plan_Mensual,
    ps.CO3_Plan_Semanal,

    r.CuFe_Real,
    pm.CuFe_Plan_Mensual,
    ps.CuFe_Plan_Semanal,

    r.FeT_Real,
    r.FeS_Real,

    /* Dosis / consumo ácido */
    r.ConsH_Real,

    /* Granulometrías */
    r.Malla_Menos_1_2_Real,
    ps.Malla_Menos_1_2_Plan_Semanal,

    r.Malla_Menos_100_Real,
    pm.Malla_Menos_100_Plan_Mensual,
    ps.Malla_Menos_100_Plan_Semanal,

 /* NIR */
r.CaolBeta_Real,
pm.CaolBeta_Plan_Mensual,
ps.CaolBeta_Plan_Semanal,

/* Dosis de ácido */
CAST(
    ROUND(
        CASE
            WHEN ISNULL(r.Solubilidad_Real, 0) < 0.25 THEN
                CASE
                    WHEN ISNULL(r.CO3_Real, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(r.CO3_Real, 0))
                END

            ELSE
                CASE
                    WHEN r.CuS_Real IS NULL OR r.CuS_Real <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(r.CuS_Real))
                               + 18.99
                               + (15.51 * ISNULL(r.CO3_Real, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(r.CuS_Real))
                               + 18.99
                               + (15.51 * ISNULL(r.CO3_Real, 0))
                        END
                END
        END
    , 2)
AS decimal(18, 2)) AS Dosis_Acido_Ideal_TM,

CAST(
    ROUND(
        CASE
            WHEN ISNULL(ps.Solubilidad_Plan_Semanal, 0) < 0.25 THEN
                CASE
                    WHEN ISNULL(ps.CO3_Plan_Semanal, 0) <= 0.25
                        THEN 14.0
                    ELSE 11.0 + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0))
                END

            ELSE
                CASE
                    WHEN ps.CuS_Plan_Semanal IS NULL OR ps.CuS_Plan_Semanal <= 0
                        THEN 0.0
                    ELSE
                        CASE
                            WHEN (8.182 * LOG(ps.CuS_Plan_Semanal))
                               + 18.99
                               + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0)) < 14.0
                                THEN 14.0
                            ELSE (8.182 * LOG(ps.CuS_Plan_Semanal))
                               + 18.99
                               + (15.51 * ISNULL(ps.CO3_Plan_Semanal, 0))
                        END
                END
        END
    , 2)
AS decimal(18, 2)) AS Dosis_Acido_Programa_Semanal,

        /* Fuentes de información explícitas */
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN '-'
        ELSE COALESCE(fi.Fuente_Info_Quimica, '-')
    END AS Fuente_Info_Quimica,

    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN '-'
        ELSE COALESCE(fi.Fuente_Info_Fisica, '-')
    END AS Fuente_Info_Fisica,

    /* Clasificación técnica original */
    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN NULL
        ELSE m.Muestra_Quimica
    END AS Muestra_Quimica,

    CASE
        WHEN r.Apilado_TMS_Real IS NULL
          OR r.Apilado_TMS_Real = 0
            THEN NULL
        ELSE m.Muestra_Fisica
    END AS Muestra_Fisica

FROM #reales r

LEFT JOIN #muestras m
    ON m.Fecha = r.Fecha
   AND m.Turno = r.Turno

LEFT JOIN inventar_SpcHidr.v_reporte_turno_fuentes_info_test fi
    ON fi.Fecha = r.Fecha
   AND fi.Turno = r.Turno

LEFT JOIN #campania_modulo cm
    ON cm.Fecha = r.Fecha

LEFT JOIN #origen_apilado oa
    ON oa.Fecha = r.Fecha
   AND oa.Turno = r.Turno

LEFT JOIN #plan_mensual pm
    ON pm.Fecha = r.Fecha

LEFT JOIN #plan_semanal ps
    ON ps.Fecha = r.Fecha

ORDER BY
    r.Fecha,
    r.Turno;
END
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
-- inventar_SpcHidr.v_apilado_base_mina_stock_srr (VIEW)
-- Ultima modificacion: 2026-06-01 10:12:33.767000
-- ============================================================================
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
-- inventar_SpcHidr.v_clays_cufe_calculado_v2_test (VIEW)
-- Ultima modificacion: 2026-08-03 02:32:08.163000
-- ============================================================================

CREATE   VIEW
    [inventar_SpcHidr].[v_clays_cufe_calculado_v2_test]
AS

/* ============================================================
   OBJETIVO
   ------------------------------------------------------------
   Resolver CaolBeta y CuFe por:

       Fecha + Turno + Torre

   FUENTES
   ------------------------------------------------------------
   Representatividad química:
       inventar_SpcHidr.representatividad_torres_resultado

   CaolBeta laboratorio:
       inventar_SpcHidr.NIR

   CuFe laboratorio:
       inventar_SpcHidr.Informe_TM_lab

   Modelo de bloques:
       inventar_SpcHidr.v_conciliacion_chancado_v2

   REGLA POR ANALITO
   ------------------------------------------------------------
   1. Laboratorio propio si:
          Representatividad química propia >= 0.75
          y existe resultado de laboratorio propio.

   2. Para TM1 únicamente:
          compartir el resultado de TM2 si
          Representatividad química TM2 >= 0.75
          y existe resultado de laboratorio TM2.

   3. En cualquier otro caso:
          utilizar modelo de bloques.

   4. Si no existe ninguna fuente:
          devolver NULL.

   IMPORTANTE
   ------------------------------------------------------------
   - El umbral se evalúa con precisión completa.
   - No se aplica ROUND antes de evaluar 0.75.
   - No se comparte TM1 hacia TM2.
   - CaolBeta y CuFe se resuelven independientemente.
   - Esta vista no modifica Clays_CuFe.
   ============================================================ */

WITH rep AS
(
    /* Convierte la tabla ancha de representatividad
       en Fecha + Turno + Torre. */
    SELECT
        r.Dia AS Fecha,
        x.Torre,
        x.Turno,

        CAST(
            x.Representatividad_Quimica
            AS decimal(18,10)
        ) AS Representatividad_Quimica

    FROM [inventar_SpcHidr].[representatividad_torres_resultado] AS r

    CROSS APPLY
    (
        VALUES
            ('TM1', 'A', r.TM1_TurnoA_Quimico),
            ('TM1', 'B', r.TM1_TurnoB_Quimico),
            ('TM2', 'A', r.TM2_TurnoA_Quimico),
            ('TM2', 'B', r.TM2_TurnoB_Quimico)
    ) AS x
    (
        Torre,
        Turno,
        Representatividad_Quimica
    )
),

/* ============================================================
   NIR: CaolBeta laboratorio
   ============================================================ */
nir_normalizado AS
(
    SELECT
        n.id,
        n.dia AS Fecha,

        CASE
            WHEN norm.Torre_Normalizada
                 IN ('TM1', 'T1', 'TORRE1')
                THEN 'TM1'

            WHEN norm.Torre_Normalizada
                 IN ('TM2', 'T2', 'TORRE2')
                THEN 'TM2'

            ELSE NULL
        END AS Torre,

        CASE
            WHEN norm.Turno_Normalizado
                 IN ('A', 'TA', 'TURNOA')
                THEN 'A'

            WHEN norm.Turno_Normalizado
                 IN ('B', 'TB', 'TURNOB')
                THEN 'B'

            ELSE NULL
        END AS Turno,

        n.muestra,

        CAST(n.caolbeta AS float)
            AS CaolBeta_NIR,

        n.fecha_carga

    FROM [inventar_SpcHidr].[NIR] AS n

    CROSS APPLY
    (
        VALUES
        (
            /* TM-1 / TM_1 / TM 1 / TM1 -> TM1 */
            REPLACE(
                REPLACE(
                    REPLACE(
                        UPPER(
                            LTRIM(
                                RTRIM(
                                    ISNULL(n.torre, '')
                                )
                            )
                        ),
                        ' ',
                        ''
                    ),
                    '-',
                    ''
                ),
                '_',
                ''
            ),

            /* TA / T-A / Turno A / A */
            REPLACE(
                REPLACE(
                    REPLACE(
                        UPPER(
                            LTRIM(
                                RTRIM(
                                    ISNULL(n.turno, '')
                                )
                            )
                        ),
                        ' ',
                        ''
                    ),
                    '-',
                    ''
                ),
                '_',
                ''
            )
        )
    ) AS norm
    (
        Torre_Normalizada,
        Turno_Normalizado
    )
),

nir_ranked AS
(
    SELECT
        n.*,

        COUNT(*) OVER
        (
            PARTITION BY
                n.Fecha,
                n.Turno,
                n.Torre
        ) AS Cantidad_Registros_NIR,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                n.Fecha,
                n.Turno,
                n.Torre

            ORDER BY
                ISNULL(
                    n.fecha_carga,
                    CONVERT(datetime2, '19000101')
                ) DESC,

                n.id DESC
        ) AS rn

    FROM nir_normalizado AS n

    WHERE n.Fecha IS NOT NULL
      AND n.Turno IS NOT NULL
      AND n.Torre IS NOT NULL
),

nir AS
(
    SELECT
        Fecha,
        Turno,
        Torre,

        id AS ID_NIR,
        muestra AS Muestra_NIR,
        CaolBeta_NIR,
        fecha_carga AS Fecha_Carga_NIR,
        Cantidad_Registros_NIR

    FROM nir_ranked

    WHERE rn = 1
),

/* ============================================================
   Informe TM: CuFe laboratorio
   ============================================================ */
lab_normalizado AS
(
    SELECT
        l.ID_Registro,
        l.Fecha,

        CASE
            WHEN norm.Torre_Normalizada
                 IN ('TM1', 'T1', 'TORRE1')
                THEN 'TM1'

            WHEN norm.Torre_Normalizada
                 IN ('TM2', 'T2', 'TORRE2')
                THEN 'TM2'

            ELSE NULL
        END AS Torre,

        CASE
            WHEN norm.Turno_Normalizado
                 IN ('A', 'TA', 'TURNOA')
                THEN 'A'

            WHEN norm.Turno_Normalizado
                 IN ('B', 'TB', 'TURNOB')
                THEN 'B'

            ELSE NULL
        END AS Turno,

        CAST(l.CuFe_Global AS float)
            AS CuFe_Laboratorio,

        l.Fecha_Carga AS Fecha_Carga_Laboratorio

    FROM [inventar_SpcHidr].[Informe_TM_lab] AS l

    CROSS APPLY
    (
        VALUES
        (
            REPLACE(
                REPLACE(
                    REPLACE(
                        UPPER(
                            LTRIM(
                                RTRIM(
                                    ISNULL(l.Torre, '')
                                )
                            )
                        ),
                        ' ',
                        ''
                    ),
                    '-',
                    ''
                ),
                '_',
                ''
            ),

            REPLACE(
                REPLACE(
                    REPLACE(
                        UPPER(
                            LTRIM(
                                RTRIM(
                                    ISNULL(l.Turno, '')
                                )
                            )
                        ),
                        ' ',
                        ''
                    ),
                    '-',
                    ''
                ),
                '_',
                ''
            )
        )
    ) AS norm
    (
        Torre_Normalizada,
        Turno_Normalizado
    )

    WHERE l.Fecha IS NOT NULL
      AND l.CuFe_Global IS NOT NULL
),

lab_ranked AS
(
    SELECT
        l.*,

        COUNT(*) OVER
        (
            PARTITION BY
                l.Fecha,
                l.Turno,
                l.Torre
        ) AS Cantidad_Registros_Laboratorio,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                l.Fecha,
                l.Turno,
                l.Torre

            ORDER BY
                ISNULL(
                    l.Fecha_Carga_Laboratorio,
                    CONVERT(datetime, '19000101')
                ) DESC,

                l.ID_Registro DESC
        ) AS rn

    FROM lab_normalizado AS l

    WHERE l.Turno IS NOT NULL
      AND l.Torre IS NOT NULL
),

lab AS
(
    SELECT
        Fecha,
        Turno,
        Torre,

        ID_Registro AS ID_Registro_CuFe,
        CuFe_Laboratorio,
        Fecha_Carga_Laboratorio,
        Cantidad_Registros_Laboratorio

    FROM lab_ranked

    WHERE rn = 1
),

/* ============================================================
   Modelo de bloques
   ============================================================ */
mb_base AS
(
    SELECT
        CAST(c.Fecha AS date) AS Fecha,

        CASE
            WHEN norm.Turno_Normalizado
                 IN ('A', 'TA', 'TURNOA')
                THEN 'A'

            WHEN norm.Turno_Normalizado
                 IN ('B', 'TB', 'TURNOB')
                THEN 'B'

            ELSE NULL
        END AS Turno,

        TRY_CONVERT(float, c.Clay_Beta)
            AS CaolBeta_MB,

        TRY_CONVERT(float, c.CuFe)
            AS CuFe_MB

    FROM [inventar_SpcHidr].[v_conciliacion_chancado_v2] AS c

    CROSS APPLY
    (
        VALUES
        (
            REPLACE(
                REPLACE(
                    REPLACE(
                        UPPER(
                            LTRIM(
                                RTRIM(
                                    ISNULL(c.Turno, '')
                                )
                            )
                        ),
                        ' ',
                        ''
                    ),
                    '-',
                    ''
                ),
                '_',
                ''
            )
        )
    ) AS norm
    (
        Turno_Normalizado
    )

    WHERE c.Fecha IS NOT NULL
),

mb AS
(
    SELECT
        Fecha,
        Turno,

        COUNT(*) AS Cantidad_Registros_MB,

        MAX(CaolBeta_MB)
            AS CaolBeta_MB,

        MAX(CuFe_MB)
            AS CuFe_MB

    FROM mb_base

    WHERE Turno IS NOT NULL

    GROUP BY
        Fecha,
        Turno
),

/* ============================================================
   Construcción de la grilla Fecha + Turno + Torre
   ============================================================ */
fecha_turno AS
(
    SELECT Fecha, Turno
    FROM rep

    UNION

    SELECT Fecha, Turno
    FROM nir

    UNION

    SELECT Fecha, Turno
    FROM lab

    UNION

    SELECT Fecha, Turno
    FROM mb
),

grilla AS
(
    SELECT
        ft.Fecha,
        ft.Turno,
        t.Torre

    FROM fecha_turno AS ft

    CROSS JOIN
    (
        VALUES
            ('TM1'),
            ('TM2')
    ) AS t(Torre)

    WHERE ft.Fecha IS NOT NULL
      AND ft.Turno IS NOT NULL
),

/* ============================================================
   Fuentes propias de cada torre
   ============================================================ */
fuentes_propias AS
(
    SELECT
        g.Fecha,
        g.Turno,
        g.Torre,

        r.Representatividad_Quimica,

        CASE
            WHEN r.Representatividad_Quimica >= 0.75
                THEN CAST(1 AS bit)

            WHEN r.Representatividad_Quimica IS NULL
                THEN NULL

            ELSE CAST(0 AS bit)
        END AS Flag_Representativa_Quimica,

        /* CaolBeta propio */
        n.ID_NIR,
        n.Muestra_NIR,
        n.CaolBeta_NIR,
        n.Fecha_Carga_NIR,
        n.Cantidad_Registros_NIR,

        /* CuFe propio */
        l.ID_Registro_CuFe,
        l.CuFe_Laboratorio,
        l.Fecha_Carga_Laboratorio,
        l.Cantidad_Registros_Laboratorio,

        /* Modelo de bloques */
        m.CaolBeta_MB,
        m.CuFe_MB,
        m.Cantidad_Registros_MB

    FROM grilla AS g

    LEFT JOIN rep AS r
        ON r.Fecha = g.Fecha
       AND r.Turno = g.Turno
       AND r.Torre = g.Torre

    LEFT JOIN nir AS n
        ON n.Fecha = g.Fecha
       AND n.Turno = g.Turno
       AND n.Torre = g.Torre

    LEFT JOIN lab AS l
        ON l.Fecha = g.Fecha
       AND l.Turno = g.Turno
       AND l.Torre = g.Torre

    LEFT JOIN mb AS m
        ON m.Fecha = g.Fecha
       AND m.Turno = g.Turno
),

/* ============================================================
   Fuentes disponibles específicamente en TM2
   para la regla de compartición hacia TM1
   ============================================================ */
fuentes_tm2 AS
(
    SELECT
        f.Fecha,
        f.Turno,

        f.Representatividad_Quimica
            AS Representatividad_Quimica_TM2,

        f.Flag_Representativa_Quimica
            AS Flag_Representativa_Quimica_TM2,

        f.ID_NIR
            AS ID_NIR_TM2,

        f.Muestra_NIR
            AS Muestra_NIR_TM2,

        f.CaolBeta_NIR
            AS CaolBeta_NIR_TM2,

        f.Fecha_Carga_NIR
            AS Fecha_Carga_NIR_TM2,

        f.ID_Registro_CuFe
            AS ID_Registro_CuFe_TM2,

        f.CuFe_Laboratorio
            AS CuFe_Laboratorio_TM2,

        f.Fecha_Carga_Laboratorio
            AS Fecha_Carga_Laboratorio_TM2

    FROM fuentes_propias AS f

    WHERE f.Torre = 'TM2'
),

fuentes_completas AS
(
    SELECT
        f.Fecha,
        f.Turno,
        f.Torre,

        /* Representatividad propia */
        f.Representatividad_Quimica,
        f.Flag_Representativa_Quimica,

        /* CaolBeta propio */
        f.ID_NIR,
        f.Muestra_NIR,
        f.CaolBeta_NIR,
        f.Fecha_Carga_NIR,
        f.Cantidad_Registros_NIR,

        /* CuFe propio */
        f.ID_Registro_CuFe,
        f.CuFe_Laboratorio,
        f.Fecha_Carga_Laboratorio,
        f.Cantidad_Registros_Laboratorio,

        /* Fuentes TM2 para compartir */
        t2.Representatividad_Quimica_TM2,
        t2.Flag_Representativa_Quimica_TM2,

        t2.ID_NIR_TM2,
        t2.Muestra_NIR_TM2,
        t2.CaolBeta_NIR_TM2,
        t2.Fecha_Carga_NIR_TM2,

        t2.ID_Registro_CuFe_TM2,
        t2.CuFe_Laboratorio_TM2,
        t2.Fecha_Carga_Laboratorio_TM2,

        /* Modelo de bloques */
        f.CaolBeta_MB,
        f.CuFe_MB,
        f.Cantidad_Registros_MB

    FROM fuentes_propias AS f

    LEFT JOIN fuentes_tm2 AS t2
        ON t2.Fecha = f.Fecha
       AND t2.Turno = f.Turno
),

resuelto AS
(
    SELECT
        f.*,

        /* ====================================================
           Resolución CaolBeta
           ==================================================== */
        CASE
            /* Laboratorio propio */
            WHEN f.Representatividad_Quimica >= 0.75
             AND f.CaolBeta_NIR IS NOT NULL
                THEN f.CaolBeta_NIR

            /* Compartición TM2 -> TM1 */
            WHEN f.Torre = 'TM1'
             AND f.Representatividad_Quimica_TM2 >= 0.75
             AND f.CaolBeta_NIR_TM2 IS NOT NULL
                THEN f.CaolBeta_NIR_TM2

            /* Modelo de bloques */
            WHEN f.CaolBeta_MB IS NOT NULL
                THEN f.CaolBeta_MB

            ELSE NULL
        END AS CaolBeta_Final,

        CASE
            WHEN f.Representatividad_Quimica >= 0.75
             AND f.CaolBeta_NIR IS NOT NULL
                THEN 'NIR_PROPIO_REPRESENTATIVO'

            WHEN f.Torre = 'TM1'
             AND f.Representatividad_Quimica_TM2 >= 0.75
             AND f.CaolBeta_NIR_TM2 IS NOT NULL
                THEN 'NIR_TM2_COMPARTIDO'

            WHEN f.CaolBeta_MB IS NOT NULL
             AND f.Representatividad_Quimica IS NULL
                THEN 'MB_SIN_REPRESENTATIVIDAD'

            WHEN f.CaolBeta_MB IS NOT NULL
             AND f.Representatividad_Quimica < 0.75
                THEN 'MB_NO_REPRESENTATIVO'

            WHEN f.CaolBeta_MB IS NOT NULL
             AND f.Representatividad_Quimica >= 0.75
             AND f.CaolBeta_NIR IS NULL
                THEN 'MB_SIN_RESULTADO_NIR'

            ELSE 'SIN_DATO'
        END AS Fuente_CaolBeta,

        /* ====================================================
           Resolución CuFe
           ==================================================== */
        CASE
            /* Laboratorio propio */
            WHEN f.Representatividad_Quimica >= 0.75
             AND f.CuFe_Laboratorio IS NOT NULL
                THEN f.CuFe_Laboratorio

            /* Compartición TM2 -> TM1 */
            WHEN f.Torre = 'TM1'
             AND f.Representatividad_Quimica_TM2 >= 0.75
             AND f.CuFe_Laboratorio_TM2 IS NOT NULL
                THEN f.CuFe_Laboratorio_TM2

            /* Modelo de bloques */
            WHEN f.CuFe_MB IS NOT NULL
                THEN f.CuFe_MB

            ELSE NULL
        END AS CuFe_Final,

        CASE
            WHEN f.Representatividad_Quimica >= 0.75
             AND f.CuFe_Laboratorio IS NOT NULL
                THEN 'LAB_PROPIO_REPRESENTATIVO'

            WHEN f.Torre = 'TM1'
             AND f.Representatividad_Quimica_TM2 >= 0.75
             AND f.CuFe_Laboratorio_TM2 IS NOT NULL
                THEN 'LAB_TM2_COMPARTIDO'

            WHEN f.CuFe_MB IS NOT NULL
             AND f.Representatividad_Quimica IS NULL
                THEN 'MB_SIN_REPRESENTATIVIDAD'

            WHEN f.CuFe_MB IS NOT NULL
             AND f.Representatividad_Quimica < 0.75
                THEN 'MB_NO_REPRESENTATIVO'

            WHEN f.CuFe_MB IS NOT NULL
             AND f.Representatividad_Quimica >= 0.75
             AND f.CuFe_Laboratorio IS NULL
                THEN 'MB_SIN_RESULTADO_CUFE'

            ELSE 'SIN_DATO'
        END AS Fuente_CuFe

    FROM fuentes_completas AS f
)

SELECT
    Fecha,
    Turno,
    Torre,

    /* Representatividad propia */
    Representatividad_Quimica,
    Flag_Representativa_Quimica,

    /* Representatividad TM2 para revisar compartición */
    Representatividad_Quimica_TM2,
    Flag_Representativa_Quimica_TM2,

    /* ========================================================
       CaolBeta propio
       ======================================================== */
    ID_NIR,
    Muestra_NIR,
    CaolBeta_NIR,
    Fecha_Carga_NIR,
    Cantidad_Registros_NIR,

    /* CaolBeta TM2 potencialmente compartido */
    ID_NIR_TM2,
    Muestra_NIR_TM2,
    CaolBeta_NIR_TM2,
    Fecha_Carga_NIR_TM2,

    /* Modelo de bloques */
    CaolBeta_MB,

    /* Resultado con precisión completa */
    CaolBeta_Final,

    /* Resultado compatible con histórico */
    CAST(
        ROUND(CaolBeta_Final, 2)
        AS decimal(18,2)
    ) AS CaolBeta_Final_2D,

    Fuente_CaolBeta,

    /* ========================================================
       CuFe propio
       ======================================================== */
    ID_Registro_CuFe,
    CuFe_Laboratorio,
    Fecha_Carga_Laboratorio,
    Cantidad_Registros_Laboratorio,

    /* CuFe TM2 potencialmente compartido */
    ID_Registro_CuFe_TM2,
    CuFe_Laboratorio_TM2,
    Fecha_Carga_Laboratorio_TM2,

    /* Modelo de bloques */
    CuFe_MB,

    /* Resultado con precisión completa */
    CuFe_Final,

    /* Resultado compatible con histórico */
    CAST(
        ROUND(CuFe_Final, 2)
        AS decimal(18,2)
    ) AS CuFe_Final_2D,

    Fuente_CuFe,

    /* Control de duplicidad o cardinalidad MB */
    Cantidad_Registros_MB

FROM resuelto;
GO

-- ============================================================================
-- inventar_SpcHidr.v_conciliacion_chancado_v2 (VIEW)
-- Ultima modificacion: 2026-07-24 08:01:00.463000
-- ============================================================================
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
-- inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test (VIEW)
-- Ultima modificacion: 2026-06-02 14:14:35.280000
-- ============================================================================
CREATE   VIEW inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS

WITH base AS (
    SELECT
        Fecha,
        Turno,
        CASE
            WHEN Turno = 'A' THEN 'B'
            WHEN Turno = 'B' THEN 'A'
        END AS Otro_Turno,
        TM,

        CuT,
        Fuente_CuT,

        CuS,
        Fuente_CuS,

        CO3,
        Fuente_CO3,

        CuFe,
        Fuente_CuFe,

        FeT,
        Fuente_FeT,

        FeS,
        Fuente_FeS,

        ConsH,
        Fuente_ConsH,

        Malla_Menos_1_2,
        Fuente_Malla_Menos_1_2,

        Malla_Menos_100,
        Fuente_Malla_Menos_100,

        CaolBeta,
        Fuente_CaolBeta

    FROM inventar_SpcHidr.v_leyes_validadas_tm_turno
),

unpivot_especial AS (
    SELECT
        Fecha,
        Turno,
        Otro_Turno,
        TM,
        Analito,
        Valor_Base,
        Fuente_Base
    FROM base
    CROSS APPLY (
        VALUES
            ('FeS', FeS, Fuente_FeS),
            ('ConsH', ConsH, Fuente_ConsH),
            ('Malla_Menos_1_2', Malla_Menos_1_2, Fuente_Malla_Menos_1_2)
    ) v(Analito, Valor_Base, Fuente_Base)
),

otro_turno AS (
    SELECT
        Fecha,
        Turno,
        TM,
        Analito,
        Valor_Base AS Valor_Otro_Turno,
        Fuente_Base AS Fuente_Otro_Turno
    FROM unpivot_especial
),

semillas AS (
    SELECT
        fecha AS Fecha,
        turno AS Turno,
        tm AS TM,
        analito AS Analito,
        valor AS Valor_Semilla,
        fuente_semilla AS Fuente_Semilla
    FROM inventar_SpcHidr.analitos_semilla_reporte_turno
),

resueltos AS (
    SELECT
        b.Fecha,
        b.Turno,
        b.TM,
        b.Analito,

        CASE
            WHEN s.Valor_Semilla IS NOT NULL
                THEN s.Valor_Semilla

            WHEN b.Fuente_Base = 'TORRE'
                THEN b.Valor_Base

            WHEN ot.Fuente_Otro_Turno = 'TORRE'
                THEN ot.Valor_Otro_Turno

            ELSE b.Valor_Base
        END AS Valor_Resuelto,

        CASE
            WHEN s.Valor_Semilla IS NOT NULL
                THEN 'SEMILLA_INICIO_PERIODO'

            WHEN b.Fuente_Base = 'TORRE'
                THEN 'TORRE_MISMO_TURNO'

            WHEN ot.Fuente_Otro_Turno = 'TORRE'
                THEN 'TORRE_OTRO_TURNO_MISMO_DIA'

            ELSE b.Fuente_Base
        END AS Fuente_Resuelta

    FROM unpivot_especial b
    LEFT JOIN otro_turno ot
        ON ot.Fecha = b.Fecha
       AND ot.Turno = b.Otro_Turno
       AND ot.TM = b.TM
       AND ot.Analito = b.Analito
    LEFT JOIN semillas s
        ON s.Fecha = b.Fecha
       AND s.Turno = b.Turno
       AND s.TM = b.TM
       AND s.Analito = b.Analito
),

resueltos_pivot AS (
    SELECT
        Fecha,
        Turno,
        TM,

        MAX(CASE WHEN Analito = 'FeS' THEN Valor_Resuelto END) AS FeS_Resuelto,
        MAX(CASE WHEN Analito = 'FeS' THEN Fuente_Resuelta END) AS Fuente_FeS_Resuelto,

        MAX(CASE WHEN Analito = 'ConsH' THEN Valor_Resuelto END) AS ConsH_Resuelto,
        MAX(CASE WHEN Analito = 'ConsH' THEN Fuente_Resuelta END) AS Fuente_ConsH_Resuelto,

        MAX(CASE WHEN Analito = 'Malla_Menos_1_2' THEN Valor_Resuelto END) AS Malla_Menos_1_2_Resuelto,
        MAX(CASE WHEN Analito = 'Malla_Menos_1_2' THEN Fuente_Resuelta END) AS Fuente_Malla_Menos_1_2_Resuelto

    FROM resueltos
    GROUP BY
        Fecha,
        Turno,
        TM
)

SELECT
    b.Fecha,
    b.Turno,
    b.TM,

    b.CuT,
    b.Fuente_CuT,

    b.CuS,
    b.Fuente_CuS,

    b.CO3,
    b.Fuente_CO3,

    b.CuFe,
    b.Fuente_CuFe,

    b.FeT,
    b.Fuente_FeT,

    r.FeS_Resuelto AS FeS,
    r.Fuente_FeS_Resuelto AS Fuente_FeS,

    r.ConsH_Resuelto AS ConsH,
    r.Fuente_ConsH_Resuelto AS Fuente_ConsH,

    r.Malla_Menos_1_2_Resuelto AS Malla_Menos_1_2,
    r.Fuente_Malla_Menos_1_2_Resuelto AS Fuente_Malla_Menos_1_2,

    b.Malla_Menos_100,
    b.Fuente_Malla_Menos_100,

    b.CaolBeta,
    b.Fuente_CaolBeta

FROM base b
LEFT JOIN resueltos_pivot r
    ON r.Fecha = b.Fecha
   AND r.Turno = b.Turno
   AND r.TM = b.TM;
GO

-- ============================================================================
-- inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test_v2 (VIEW)
-- Ultima modificacion: 2026-06-11 13:33:08.517000
-- ============================================================================
CREATE   VIEW [inventar_SpcHidr].[v_leyes_resueltas_data_tm_reporte_test_v2] AS

WITH base AS (
    SELECT *
    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
),

/* ============================================================
   Candidatos diarios de Malla -1/2 ya validados físicamente
   desde la vista base.

   Nota:
   - La vista base debe entregar TORRE_* solo cuando la medición
     de Informe Torre cumple representatividad física >= 0,75.
   - Si existe A y B válidos para una misma TM/fecha, se prioriza
     TORRE_MISMO_TURNO y luego turno B por ser posterior.
   ============================================================ */
malla12_candidata_dia_tm AS (
    SELECT
        Fecha,
        TM,
        TM AS TM_Origen,
        Turno AS Turno_Fuente,
        Malla_Menos_1_2,
        Fuente_Malla_Menos_1_2 AS Fuente_Origen
    FROM (
        SELECT
            b.*,
            ROW_NUMBER() OVER (
                PARTITION BY b.Fecha, b.TM
                ORDER BY
                    CASE
                        WHEN b.Fuente_Malla_Menos_1_2 = 'TORRE_MISMO_TURNO' THEN 3
                        WHEN b.Fuente_Malla_Menos_1_2 = 'TORRE_OTRO_TURNO_MISMO_DIA' THEN 2
                        WHEN b.Fuente_Malla_Menos_1_2 = 'SEMILLA_INICIO_PERIODO' THEN 1
                        ELSE 0
                    END DESC,
                    CASE WHEN b.Turno = 'B' THEN 2 ELSE 1 END DESC
            ) AS rn
        FROM base b
        WHERE b.Malla_Menos_1_2 IS NOT NULL
          AND b.Malla_Menos_1_2 <> 0
          AND b.Fuente_Malla_Menos_1_2 <> 'NO_APLICA_MINA'
    ) x
    WHERE rn = 1
),

fechas AS (
    SELECT DISTINCT Fecha
    FROM base
),

/* ============================================================
   Regla compartible RN-027:
   - Si TM1 y TM2 tienen valor válido en la fecha, cada TM usa el suyo.
   - Si solo una TM tiene valor válido, se comparte hacia ambas TM.
   ============================================================ */
malla12_dia_resuelta AS (
    SELECT
        f.Fecha,
        'TM1' AS TM,
        COALESCE(tm1.Malla_Menos_1_2, tm2.Malla_Menos_1_2) AS Malla_Menos_1_2,
        CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN 'TM1'
             WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN 'TM2'
        END AS TM_Origen,
        CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Turno_Fuente
             WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Turno_Fuente
        END AS Turno_Fuente,
        CASE WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Fuente_Origen
             WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Fuente_Origen
        END AS Fuente_Origen
    FROM fechas f
    LEFT JOIN malla12_candidata_dia_tm tm1
        ON tm1.Fecha = f.Fecha
       AND tm1.TM = 'TM1'
    LEFT JOIN malla12_candidata_dia_tm tm2
        ON tm2.Fecha = f.Fecha
       AND tm2.TM = 'TM2'

    UNION ALL

    SELECT
        f.Fecha,
        'TM2' AS TM,
        COALESCE(tm2.Malla_Menos_1_2, tm1.Malla_Menos_1_2) AS Malla_Menos_1_2,
        CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN 'TM2'
             WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN 'TM1'
        END AS TM_Origen,
        CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Turno_Fuente
             WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Turno_Fuente
        END AS Turno_Fuente,
        CASE WHEN tm2.Malla_Menos_1_2 IS NOT NULL THEN tm2.Fuente_Origen
             WHEN tm1.Malla_Menos_1_2 IS NOT NULL THEN tm1.Fuente_Origen
        END AS Fuente_Origen
    FROM fechas f
    LEFT JOIN malla12_candidata_dia_tm tm1
        ON tm1.Fecha = f.Fecha
       AND tm1.TM = 'TM1'
    LEFT JOIN malla12_candidata_dia_tm tm2
        ON tm2.Fecha = f.Fecha
       AND tm2.TM = 'TM2'
),

ajustada AS (
    SELECT
        b.*,

        CASE
            WHEN b.FeS IS NOT NULL
             AND b.FeS <> 0
             AND b.Fuente_FeS <> 'NO_APLICA_MINA'
            THEN b.FeS
            ELSE ult_fes.FeS
        END AS FeS_Ajustado,

        CASE
            WHEN b.FeS IS NOT NULL
             AND b.FeS <> 0
             AND b.Fuente_FeS <> 'NO_APLICA_MINA'
            THEN b.Fuente_FeS
            WHEN ult_fes.FeS IS NOT NULL
            THEN 'ARRASTRE_ULTIMO_VALIDO'
            ELSE b.Fuente_FeS
        END AS Fuente_FeS_Ajustada,

        CASE
            WHEN b.ConsH IS NOT NULL
             AND b.ConsH <> 0
             AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
            THEN b.ConsH
            ELSE ult_consh.ConsH
        END AS ConsH_Ajustado,

        CASE
            WHEN b.ConsH IS NOT NULL
             AND b.ConsH <> 0
             AND b.Fuente_ConsH <> 'NO_APLICA_MINA'
            THEN b.Fuente_ConsH
            WHEN ult_consh.ConsH IS NOT NULL
            THEN 'ARRASTRE_ULTIMO_VALIDO'
            ELSE b.Fuente_ConsH
        END AS Fuente_ConsH_Ajustada,

        ult_malla.Malla_Menos_1_2 AS Malla_Menos_1_2_Ajustado,

        CASE
            WHEN ult_malla.Malla_Menos_1_2 IS NULL
                THEN b.Fuente_Malla_Menos_1_2

            WHEN ult_malla.Fecha = b.Fecha
             AND ult_malla.Fuente_Origen = 'SEMILLA_INICIO_PERIODO'
                THEN 'SEMILLA_INICIO_PERIODO'

            WHEN ult_malla.Fecha = b.Fecha
             AND ult_malla.TM_Origen = b.TM
                THEN 'TORRE_REP_FISICA'

            WHEN ult_malla.Fecha = b.Fecha
             AND ult_malla.TM_Origen <> b.TM
                THEN 'TORRE_REP_FISICA_COMPARTIDA'

            WHEN ult_malla.Fecha < b.Fecha
                THEN 'ARRASTRE_ULTIMO_VALIDO'

            ELSE b.Fuente_Malla_Menos_1_2
        END AS Fuente_Malla_Menos_1_2_Ajustada

    FROM base b

    OUTER APPLY (
        SELECT TOP 1
            x.FeS
        FROM base x
        WHERE x.TM = b.TM
          AND x.Fecha <= b.Fecha
          AND x.FeS IS NOT NULL
          AND x.FeS <> 0
          AND x.Fuente_FeS <> 'NO_APLICA_MINA'
        ORDER BY
            x.Fecha DESC,
            CASE WHEN x.Turno = b.Turno THEN 0 ELSE 1 END
    ) ult_fes

    OUTER APPLY (
        SELECT TOP 1
            x.ConsH
        FROM base x
        WHERE x.TM = b.TM
          AND x.Fecha <= b.Fecha
          AND x.ConsH IS NOT NULL
          AND x.ConsH <> 0
          AND x.Fuente_ConsH <> 'NO_APLICA_MINA'
        ORDER BY
            x.Fecha DESC,
            CASE WHEN x.Turno = b.Turno THEN 0 ELSE 1 END
    ) ult_consh

    OUTER APPLY (
        SELECT TOP 1
            d.Fecha,
            d.TM_Origen,
            d.Turno_Fuente,
            d.Malla_Menos_1_2,
            d.Fuente_Origen
        FROM malla12_dia_resuelta d
        WHERE d.TM = b.TM
          AND d.Fecha <= b.Fecha
          AND d.Malla_Menos_1_2 IS NOT NULL
        ORDER BY d.Fecha DESC
    ) ult_malla
)

SELECT
    Fecha,
    Turno,
    TM,
    CuT,
    Fuente_CuT,
    CuS,
    Fuente_CuS,
    CO3,
    Fuente_CO3,
    CuFe,
    Fuente_CuFe,
    FeT,
    Fuente_FeT,
    FeS_Ajustado AS FeS,
    Fuente_FeS_Ajustada AS Fuente_FeS,
    ConsH_Ajustado AS ConsH,
    Fuente_ConsH_Ajustada AS Fuente_ConsH,
    Malla_Menos_1_2_Ajustado AS Malla_Menos_1_2,
    Fuente_Malla_Menos_1_2_Ajustada AS Fuente_Malla_Menos_1_2,
    Malla_Menos_100,
    Fuente_Malla_Menos_100,
    CaolBeta,
    Fuente_CaolBeta
FROM ajustada;
GO

-- ============================================================================
-- inventar_SpcHidr.v_leyes_validadas_tm_turno (VIEW)
-- Ultima modificacion: 2026-06-01 09:41:44.870000
-- ============================================================================
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
-- inventar_SpcHidr.v_reporte_turno_campania_modulo_test (VIEW)
-- Ultima modificacion: 2026-07-24 08:01:00.663000
-- ============================================================================
CREATE   VIEW inventar_SpcHidr.v_reporte_turno_campania_modulo_test
AS
WITH fechas_reporte AS
(
    SELECT DISTINCT
        Fecha
    FROM inventar_SpcHidr.v_reporte_turno_reales_test
    WHERE Fecha IS NOT NULL
),

base_topografia AS
(
    SELECT
        CAST(fecha AS date) AS Fecha,
        CAST(fecha AS date) AS Fecha_Topografia,
        [campaña],
        modulo,
        pad_id,
        volumen_diario_m3,
        avance_porcentaje,
        CASE
            WHEN pad_id = 1 THEN 'OXIDOS'
            WHEN pad_id = 2 THEN 'SULFUROS'
            ELSE 'SIN_PAD'
        END AS Material
    FROM inventar_SpcHidr.control_apilado_diario
    WHERE fecha IS NOT NULL
      AND volumen_diario_m3 > 0
),

rankeado AS
(
    SELECT
        *,
        ROW_NUMBER() OVER
        (
            PARTITION BY Fecha
            ORDER BY
                avance_porcentaje ASC,
                volumen_diario_m3 DESC,
                modulo ASC
        ) AS rn
    FROM base_topografia
),

modulo_dia AS
(
    SELECT
        Fecha,
        Fecha_Topografia AS Fecha_Topografia_Usada,
        CAST([campaña] AS varchar(100)) AS Campania,
        Material,
        CAST(modulo AS varchar(100)) AS Modulo,
        avance_porcentaje AS Avance,
        volumen_diario_m3 AS Volumen_Diario_Modulo_m3
    FROM rankeado
    WHERE rn = 1
),

base_reporte AS
(
    SELECT
        f.Fecha,
        md.Fecha_Topografia_Usada,
        md.Campania,
        md.Material,
        md.Modulo,
        md.Avance,
        md.Volumen_Diario_Modulo_m3
    FROM fechas_reporte f
    LEFT JOIN modulo_dia md
        ON md.Fecha = f.Fecha
),

relleno AS
(
    SELECT
        br.Fecha,

        ult.Fecha AS Fecha_Origen_Relleno,
        ult.Fecha_Topografia_Usada,
        ult.Campania,
        ult.Material,
        ult.Modulo,
        ult.Avance,
        ult.Volumen_Diario_Modulo_m3,

        CASE
            WHEN br.Campania IS NOT NULL
                THEN 'VALOR_DIA'

            WHEN ult.Campania IS NOT NULL
                THEN 'ARRASTRE_ULTIMO_VALIDO'

            ELSE 'SIN_DATO'
        END AS Fuente_Campania_Modulo

    FROM base_reporte br

    OUTER APPLY
    (
        SELECT TOP 1
            md.Fecha,
            md.Fecha_Topografia_Usada,
            md.Campania,
            md.Material,
            md.Modulo,
            md.Avance,
            md.Volumen_Diario_Modulo_m3
        FROM modulo_dia md
        WHERE md.Fecha <= br.Fecha
        ORDER BY md.Fecha DESC
    ) ult
)

SELECT
    Fecha,
    Fecha_Origen_Relleno,
    Fecha_Topografia_Usada,
    Campania,
    Material,
    Modulo,
    Avance,
    Volumen_Diario_Modulo_m3,
    Fuente_Campania_Modulo
FROM relleno;
GO

-- ============================================================================
-- inventar_SpcHidr.v_reporte_turno_fuentes_info_test (VIEW)
-- Ultima modificacion: 2026-07-22 21:08:03.533000
-- ============================================================================
CREATE   VIEW inventar_SpcHidr.v_reporte_turno_fuentes_info_test
AS

WITH fuentes AS
(
    /* ========================================================
       FUENTES QUÍMICAS: TORRES
       ======================================================== */

    SELECT
        l.Fecha,
        l.Turno,
        'QUIMICA' AS Tipo_Muestra,

        CASE
            WHEN l.TM = 'TM1'
             AND
             (
                    l.Fuente_CuT   LIKE '%TORRE%'
                 OR l.Fuente_CuS   LIKE '%TORRE%'
                 OR l.Fuente_FeT   LIKE '%TORRE%'
                 OR l.Fuente_FeS   LIKE '%TORRE%'
                 OR l.Fuente_CO3   LIKE '%TORRE%'
                 OR l.Fuente_ConsH LIKE '%TORRE%'
                 OR l.Fuente_FeS   LIKE '%ARRASTRE%'
                 OR l.Fuente_ConsH LIKE '%ARRASTRE%'
             )
                THEN 'T1'

            WHEN l.TM = 'TM2'
             AND
             (
                    l.Fuente_CuT   LIKE '%TORRE%'
                 OR l.Fuente_CuS   LIKE '%TORRE%'
                 OR l.Fuente_FeT   LIKE '%TORRE%'
                 OR l.Fuente_FeS   LIKE '%TORRE%'
                 OR l.Fuente_CO3   LIKE '%TORRE%'
                 OR l.Fuente_ConsH LIKE '%TORRE%'
                 OR l.Fuente_FeS   LIKE '%ARRASTRE%'
                 OR l.Fuente_ConsH LIKE '%ARRASTRE%'
             )
                THEN 'T2'
        END AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    /* ========================================================
       FUENTES QUÍMICAS: MINA / MB
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'QUIMICA' AS Tipo_Muestra,
        'MB' AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    WHERE
           l.Fuente_CuT LIKE '%MINA%'
        OR l.Fuente_CuS LIKE '%MINA%'
        OR l.Fuente_FeT LIKE '%MINA%'
        OR l.Fuente_CO3 LIKE '%MINA%'
        OR l.Fuente_CuT LIKE '%MB%'
        OR l.Fuente_CuS LIKE '%MB%'
        OR l.Fuente_FeT LIKE '%MB%'
        OR l.Fuente_CO3 LIKE '%MB%'

    /* ========================================================
       FUENTES QUÍMICAS: IMP
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'QUIMICA' AS Tipo_Muestra,
        'IMP' AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    WHERE
           l.Fuente_CuT = 'IMP'
        OR l.Fuente_CuS = 'IMP'
        OR l.Fuente_FeT = 'IMP'
        OR l.Fuente_CO3 = 'IMP'

    /* ========================================================
       FUENTES FÍSICAS: TORRES
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'FISICA' AS Tipo_Muestra,

        CASE
            WHEN l.TM = 'TM1'
             AND
             (
                    l.Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                 OR l.Fuente_Malla_Menos_100 LIKE '%TORRE%'
                 OR l.Fuente_Malla_Menos_1_2 LIKE '%ARRASTRE%'
                 OR l.Fuente_Malla_Menos_100 LIKE '%ARRASTRE%'
             )
                THEN 'T1'

            WHEN l.TM = 'TM2'
             AND
             (
                    l.Fuente_Malla_Menos_1_2 LIKE '%TORRE%'
                 OR l.Fuente_Malla_Menos_100 LIKE '%TORRE%'
                 OR l.Fuente_Malla_Menos_1_2 LIKE '%ARRASTRE%'
                 OR l.Fuente_Malla_Menos_100 LIKE '%ARRASTRE%'
             )
                THEN 'T2'
        END AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    /* ========================================================
       FUENTES FÍSICAS: MINA / MB
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'FISICA' AS Tipo_Muestra,
        'MB' AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    WHERE
           l.Fuente_Malla_Menos_100 LIKE '%MINA%'
        OR l.Fuente_Malla_Menos_100 LIKE '%MB%'

    /* ========================================================
       FUENTES FÍSICAS: IMP
       ======================================================== */

    UNION ALL

    SELECT
        l.Fecha,
        l.Turno,
        'FISICA' AS Tipo_Muestra,
        'IMP' AS Fuente_Info

    FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l

    WHERE l.Fuente_Malla_Menos_100 = 'IMP'
),

fuentes_limpias AS
(
    SELECT DISTINCT
        Fecha,
        Turno,
        Tipo_Muestra,
        Fuente_Info

    FROM fuentes

    WHERE Fuente_Info IS NOT NULL
),

fuentes_agrupadas AS
(
    SELECT
        Fecha,
        Turno,
        Tipo_Muestra,

        STRING_AGG(Fuente_Info, '; ')
        WITHIN GROUP
        (
            ORDER BY
                CASE Fuente_Info
                    WHEN 'T1'  THEN 1
                    WHEN 'T2'  THEN 2
                    WHEN 'MB'  THEN 3
                    WHEN 'IMP' THEN 4
                    ELSE 9
                END
        ) AS Fuente_Info_Detalle

    FROM fuentes_limpias

    GROUP BY
        Fecha,
        Turno,
        Tipo_Muestra
)

SELECT
    Fecha,
    Turno,

    MAX
    (
        CASE
            WHEN Tipo_Muestra = 'QUIMICA'
                THEN Fuente_Info_Detalle
        END
    ) AS Fuente_Info_Quimica,

    MAX
    (
        CASE
            WHEN Tipo_Muestra = 'FISICA'
                THEN Fuente_Info_Detalle
        END
    ) AS Fuente_Info_Fisica

FROM fuentes_agrupadas

GROUP BY
    Fecha,
    Turno;
GO

-- ============================================================================
-- inventar_SpcHidr.v_reporte_turno_reales_test (VIEW)
-- Ultima modificacion: 2026-06-03 11:04:41.810000
-- ============================================================================
    CREATE   VIEW inventar_SpcHidr.v_reporte_turno_reales_test AS

WITH tms_tm AS (
    SELECT
        Fecha,
        'A' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Sin_Sal_Con_SRR_A AS TMS
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test

    UNION ALL

    SELECT
        Fecha,
        'A' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Sin_Sal_Con_SRR_A AS TMS
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM1' AS TM,
        TMS_TM1_Sin_Sal_Con_SRR_B AS TMS
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test

    UNION ALL

    SELECT
        Fecha,
        'B' AS Turno,
        'TM2' AS TM,
        TMS_TM2_Sin_Sal_Con_SRR_B AS TMS
    FROM inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test
),

base AS (
    SELECT
        t.Fecha,
        t.Turno,
        t.TM,
        t.TMS,

        l.CuT,
        l.CuS,
        l.CO3,
        l.CuFe,
        l.FeT,
        l.FeS,
        l.ConsH,
        l.Malla_Menos_1_2,
        l.Malla_Menos_100,
        l.CaolBeta

    FROM tms_tm t

    LEFT JOIN inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test_v2 l
        ON l.Fecha = t.Fecha
       AND l.Turno = t.Turno
       AND l.TM = t.TM
),

ponderado AS (
    SELECT
        Fecha,
        Turno,

        SUM(TMS) AS Apilado_TMS_Real,

        SUM(TMS * CuT) / NULLIF(SUM(CASE WHEN CuT IS NOT NULL THEN TMS ELSE 0 END), 0) AS CuT_Real,
        SUM(TMS * CuS) / NULLIF(SUM(CASE WHEN CuS IS NOT NULL THEN TMS ELSE 0 END), 0) AS CuS_Real,
        SUM(TMS * CO3) / NULLIF(SUM(CASE WHEN CO3 IS NOT NULL THEN TMS ELSE 0 END), 0) AS CO3_Real,
        SUM(TMS * CuFe) / NULLIF(SUM(CASE WHEN CuFe IS NOT NULL THEN TMS ELSE 0 END), 0) AS CuFe_Real,
        SUM(TMS * FeT) / NULLIF(SUM(CASE WHEN FeT IS NOT NULL THEN TMS ELSE 0 END), 0) AS FeT_Real,
        SUM(TMS * FeS) / NULLIF(SUM(CASE WHEN FeS IS NOT NULL THEN TMS ELSE 0 END), 0) AS FeS_Real,
        SUM(TMS * ConsH) / NULLIF(SUM(CASE WHEN ConsH IS NOT NULL THEN TMS ELSE 0 END), 0) AS ConsH_Real,
        SUM(TMS * Malla_Menos_1_2) / NULLIF(SUM(CASE WHEN Malla_Menos_1_2 IS NOT NULL THEN TMS ELSE 0 END), 0) AS Malla_Menos_1_2_Real,
        SUM(TMS * Malla_Menos_100) / NULLIF(SUM(CASE WHEN Malla_Menos_100 IS NOT NULL THEN TMS ELSE 0 END), 0) AS Malla_Menos_100_Real,
        SUM(TMS * CaolBeta) / NULLIF(SUM(CASE WHEN CaolBeta IS NOT NULL THEN TMS ELSE 0 END), 0) AS CaolBeta_Real

    FROM base
    GROUP BY
        Fecha,
        Turno
)

SELECT
    Fecha,
    Turno,
    Apilado_TMS_Real,

    CuT_Real,
    CuS_Real,

    CASE
        WHEN CuT_Real IS NULL OR CuT_Real = 0 THEN NULL
        ELSE CuS_Real / CuT_Real
    END AS Solubilidad_Real,

    CO3_Real,
    CuFe_Real,
    FeT_Real,
    FeS_Real,
    ConsH_Real,
    Malla_Menos_1_2_Real,
    Malla_Menos_100_Real,
    CaolBeta_Real

FROM ponderado;
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
-- inventar_SpcHidr.v_srr_tms_origen_turno_emision_test (VIEW)
-- Ultima modificacion: 2026-08-21 12:39:40.797000
-- ============================================================================

CREATE   VIEW [inventar_SpcHidr].[v_srr_tms_origen_turno_emision_test]
AS
WITH turnos_cache AS
(
    SELECT DISTINCT
        CAST(Fecha AS date) AS Fecha,
        UPPER(LTRIM(RTRIM(Turno))) COLLATE DATABASE_DEFAULT AS Turno
    FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test]
),
imp_origen_turno AS
(
    SELECT
        CAST(i.Fecha AS date) AS Fecha,
        CASE
            WHEN i.Turno IN ('TA', 'A') THEN 'A'
            WHEN i.Turno IN ('TB', 'B') THEN 'B'
            ELSE i.Turno
        END COLLATE DATABASE_DEFAULT AS Turno,
        CAST(SUM(CASE WHEN ISNULL(i.Es_SRR, 0) = 1
                      THEN ISNULL(i.Ton, 0) ELSE 0 END) AS decimal(38,10)) AS Ton_SRR_IMP,
        CAST(SUM(ISNULL(i.Ton, 0)) AS decimal(38,10)) AS Ton_IMP_Total
    FROM [DEV_SIIR].[hidro].[v_imp_chancado_normalizado] AS i
    INNER JOIN turnos_cache AS tc
      ON tc.Fecha = CAST(i.Fecha AS date)
     AND tc.Turno = CASE
            WHEN i.Turno IN ('TA', 'A') THEN 'A'
            WHEN i.Turno IN ('TB', 'B') THEN 'B'
            ELSE i.Turno
        END COLLATE DATABASE_DEFAULT
    WHERE ISNULL(i.Ton, 0) > 0
    GROUP BY
        CAST(i.Fecha AS date),
        CASE
            WHEN i.Turno IN ('TA', 'A') THEN 'A'
            WHEN i.Turno IN ('TB', 'B') THEN 'B'
            ELSE i.Turno
        END COLLATE DATABASE_DEFAULT
),
origen_base AS
(
    SELECT
        CAST(r.Fecha AS date) AS Fecha,
        UPPER(LTRIM(RTRIM(r.Turno))) AS Turno,
        CAST(ISNULL(r.Apilado_TMS_Real, 0) AS decimal(38,10)) AS Apilado_TMS_Real,
        CAST(ISNULL(p.Ton_Stock_Camiones, 0) AS decimal(38,10)) AS Ton_Stock_Oficial,
        CAST(ISNULL(p.Ton_Mina_Camiones, 0) AS decimal(38,10)) AS Ton_Mina_Oficial,
        CAST(ISNULL(p.Ton_SRR, 0) AS decimal(38,10)) AS Ton_SRR_Oficial,
        CAST(ISNULL(i.Ton_SRR_IMP, 0) AS decimal(38,10)) AS Ton_SRR_IMP,
        CAST(ISNULL(i.Ton_IMP_Total, 0) AS decimal(38,10)) AS Ton_IMP_Total,
        c.Fuente_Dato,
        CASE
            WHEN ISNULL(p.Ton_Stock_Camiones, 0) > 0
              OR ISNULL(p.Ton_Mina_Camiones, 0) > 0
              OR ISNULL(p.Ton_SRR, 0) > 0 THEN 'OFICIAL'
            WHEN UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato, '')))) = 'IMP'
             AND ISNULL(i.Ton_IMP_Total, 0) > 0 THEN 'IMP'
            ELSE 'SIN_ORIGEN'
        END AS Fuente_SRR
    FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test] AS r
    LEFT JOIN [inventar_SpcHidr].[v_apilado_base_mina_stock_srr] AS p
      ON p.Fecha = CAST(r.Fecha AS date)
     AND p.Turno = UPPER(LTRIM(RTRIM(r.Turno)))
    LEFT JOIN imp_origen_turno AS i
      ON i.Fecha = CAST(r.Fecha AS date)
     AND i.Turno = UPPER(LTRIM(RTRIM(r.Turno))) COLLATE DATABASE_DEFAULT
    LEFT JOIN [inventar_SpcHidr].[v_conciliacion_chancado_v2] AS c
      ON c.Fecha = CAST(r.Fecha AS date)
     AND c.Turno = UPPER(LTRIM(RTRIM(r.Turno)))
),
origen_raw AS
(
    SELECT
        b.*,
        CAST(CASE
            WHEN b.Fuente_SRR = 'OFICIAL' THEN b.Ton_SRR_Oficial
            WHEN b.Fuente_SRR = 'IMP' THEN b.Ton_SRR_IMP
            ELSE 0
        END AS decimal(38,10)) AS Ton_SRR_Origen_Raw
    FROM origen_base AS b
)
SELECT
    Fecha,
    Turno,
    Fuente_SRR,
    Ton_SRR_Oficial,
    Ton_SRR_IMP,
    Ton_SRR_Origen_Raw,
    CAST(CASE
        WHEN Apilado_TMS_Real <= 0 THEN 0
        WHEN Ton_SRR_Origen_Raw <= 0 THEN 0
        WHEN Ton_SRR_Origen_Raw > Apilado_TMS_Real THEN Apilado_TMS_Real
        ELSE Ton_SRR_Origen_Raw
    END AS decimal(38,10)) AS Ton_SRR_Usado_Actual,
    CAST(CASE WHEN Apilado_TMS_Real > 0
                   AND Ton_SRR_Origen_Raw > Apilado_TMS_Real
              THEN 1 ELSE 0 END AS bit) AS Flag_SRR_Capeado_Por_Apilado,
    CAST(CASE WHEN Fuente_SRR <> 'SIN_ORIGEN'
                   AND Apilado_TMS_Real > 0
                   AND Ton_SRR_Origen_Raw > 0
              THEN 1 ELSE 0 END AS bit) AS Flag_SRR_Valido,
    CAST(CASE
        WHEN Fuente_SRR = 'SIN_ORIGEN' THEN 'SIN_ORIGEN'
        WHEN Apilado_TMS_Real <= 0 THEN 'SIN_APILADO'
        WHEN Ton_SRR_Origen_Raw <= 0 THEN 'SIN_SRR_POSITIVO'
        WHEN Ton_SRR_Origen_Raw > Apilado_TMS_Real THEN 'OK_CAP_APILADO'
        ELSE 'OK'
    END AS varchar(40)) AS Estado_SRR,
    Apilado_TMS_Real,
    Ton_Stock_Oficial,
    Ton_Mina_Oficial,
    Ton_IMP_Total,
    Fuente_Dato AS Fuente_Dato_Conciliacion
FROM origen_raw;
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
-- inventar_SpcHidr.v_validacion_leyes_tm1_v2 (VIEW)
-- Ultima modificacion: 2026-07-22 20:31:37.703000
-- ============================================================================
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
GO

-- ============================================================================
-- inventar_SpcHidr.v_validacion_leyes_tm2_v2 (VIEW)
-- Ultima modificacion: 2026-07-22 20:37:04.947000
-- ============================================================================
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
GO
