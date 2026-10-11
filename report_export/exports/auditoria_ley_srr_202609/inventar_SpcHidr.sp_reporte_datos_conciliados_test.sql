
CREATE PROCEDURE
[inventar_SpcHidr].[sp_reporte_datos_conciliados_test]
(
    @FechaInicio date = NULL,
    @FechaFin    date = NULL
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    /* ============================================================
       1. VALIDACIÓN DE PARÁMETROS
       ============================================================ */

    IF @FechaInicio IS NULL
    BEGIN
        SELECT
            @FechaInicio = MIN(CAST(Fecha AS date))
        FROM [inventar_SpcHidr].[Datos_conciliados_of];
    END;

    IF @FechaFin IS NULL
    BEGIN
        SELECT
            @FechaFin = MAX(CAST(Fecha AS date))
        FROM [inventar_SpcHidr].[Datos_conciliados_of];
    END;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
    BEGIN
        THROW 50002,
              'No fue posible determinar el rango de fechas del reporte.',
              1;
    END;

    IF @FechaInicio > @FechaFin
    BEGIN
        THROW 50001,
              'La fecha inicial no puede ser mayor que la fecha final.',
              1;
    END;

    /*
       La función diaria utiliza fecha final exclusiva.
    */
    DECLARE @FechaFinExclusiva date =
        DATEADD(DAY, 1, @FechaFin);


    /* ============================================================
       2. CALENDARIO + SELECCIÓN HISTÓRICA
       ============================================================ */

    ;WITH Fechas AS
    (
        SELECT
            @FechaInicio AS Fecha

        UNION ALL

        SELECT
            DATEADD(DAY, 1, Fecha)
        FROM Fechas
        WHERE Fecha < @FechaFin
    ),

    DatosBase AS
    (
        SELECT
            d.*,

            ROW_NUMBER() OVER
            (
                PARTITION BY CAST(d.Fecha AS date)

                ORDER BY
                    /*
                       Preferencia por avances en escala interna 0–1.
                    */
                    CASE
                        WHEN
                            (
                                d.Avance_apilado IS NULL
                                OR d.Avance_apilado BETWEEN 0 AND 1
                            )
                            AND
                            (
                                d.Avance_reclamo_oxidos IS NULL
                                OR d.Avance_reclamo_oxidos BETWEEN 0 AND 1
                            )
                            AND
                            (
                                d.Avance_reclamo_sulfuros IS NULL
                                OR d.Avance_reclamo_sulfuros BETWEEN 0 AND 1
                            )
                        THEN 0
                        ELSE 1
                    END,

                    /*
                       Preferencia temporal por registros de chancado
                       que conserven decimales.
                    */
                    CASE
                        WHEN ABS
                        (
                            COALESCE(d.Chancado_TMS_Real, 0)
                            - ROUND
                            (
                                COALESCE(d.Chancado_TMS_Real, 0),
                                0
                            )
                        ) > 0.000001
                        THEN 0
                        ELSE 1
                    END,

                    /*
                       Desempate técnico temporal.
                       Debe reemplazarse por ID o fecha de actualización
                       cuando esos campos estén disponibles.
                    */
                    CHECKSUM
                    (
                        d.Fecha,
                        d.Chancado_TMS_Real,
                        d.Apilado_TMS_Real,
                        d.Avance_apilado,
                        d.Avance_reclamo_oxidos,
                        d.Avance_reclamo_sulfuros,
                        d.Produccion_Catodos_Real
                    ) DESC
            ) AS rn

        FROM [inventar_SpcHidr].[Datos_conciliados_of] d

        WHERE CAST(d.Fecha AS date) >= @FechaInicio
          AND CAST(d.Fecha AS date) <= @FechaFin
    ),

    DatosUnicos AS
    (
        SELECT *
        FROM DatosBase
        WHERE rn = 1
    )

    SELECT
        f.Fecha,

        /* ========================================================
           CHANCADO
           Fuente histórica temporal
           ======================================================== */

        d.Chancado_TMS_Real,


        /* ========================================================
           HUMEDAD
           ======================================================== */

        a.Humedad_Turno_A,
        a.Humedad_Turno_B,
        a.Humedad_promedio_dia,


        /* ========================================================
           SAL
           ======================================================== */

        a.Sal_turno_A,
        a.Sal_Turno_B,
        a.Sal_promedio_dia,


        /* ========================================================
           APILADO TMH
           ======================================================== */

        a.Apilado_TMH_turno_A,
        a.Apilado_TMH_turno_B,
        a.Apilado_TMH_promedio_dia,


        /* ========================================================
           APILADO TMS
           Consolidación oficial Turno → Día
           ======================================================== */

        g.Apilado_TMS_Real_Dia
            AS Apilado_TMS_Real,

        g.Apilado_TMS_Plan
            AS Apilado_TMS_Plan,


        /* ========================================================
           MATERIAL, MÓDULO Y AVANCE
           ======================================================== */

        CASE
            WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion)))
                IN ('SULFURO', 'SULFUROS')
                THEN 'Sulfuro'

            WHEN UPPER(LTRIM(RTRIM(g.Material_Operacion)))
                IN ('OXIDO', 'OXIDOS', 'ÓXIDO', 'ÓXIDOS')
                THEN 'Oxido'

            ELSE g.Material_Operacion
        END AS Campana_apilado,

        g.Modulo
            AS Modulo_apilado,

        g.Avance
            AS Avance_apilado,


        /* ========================================================
           LEY CuT DEL APILADO
           ======================================================== */

        g.CuT_Real_Dia
            AS Ley_CuT_Real,

        g.CuT_Plan
            AS Ley_CuT_Plan,


        /* ========================================================
           COBRE FINO APILADO

           Sin apilado:
           cobre fino = 0.

           Con apilado pero sin CuT:
           cobre fino = NULL.
           ======================================================== */

        CASE
            WHEN COALESCE(g.Apilado_TMS_Real_Dia, 0) = 0
                THEN CAST(0 AS decimal(20,6))

            WHEN g.CuT_Real_Dia IS NULL
                THEN NULL

            ELSE
                CAST
                (
                    g.Apilado_TMS_Real_Dia
                    * g.CuT_Real_Dia
                    / 100.0
                    AS decimal(20,6)
                )
        END AS Cobre_fino_Apilado_Real,

        CASE
            WHEN g.Apilado_TMS_Plan IS NULL
              OR g.CuT_Plan IS NULL
                THEN NULL

            ELSE
                CAST
                (
                    g.Apilado_TMS_Plan
                    * g.CuT_Plan
                    / 100.0
                    AS decimal(20,6)
                )
        END AS Cobre_fino_Apilado_Plan,


        /* ========================================================
           RECLAMO ÓXIDOS
           Fuente histórica temporal
           ======================================================== */

        d.TMS_Rotopala_1_Real,

        pm.TMS_Rotopala_1_Plan
            AS TMS_Rotopala_1_Plan,

        d.Campana_reclamo_oxidos,
        d.Modulo_reclamo_oxidos,
        d.Avance_reclamo_oxidos,


        /* ========================================================
           RECLAMO SULFUROS
           Fuente histórica temporal
           ======================================================== */

        d.TMS_Rotopala_2_Real,

        pm.TMS_Rotopala_2_Plan
            AS TMS_Rotopala_2_Plan,

        d.Campana_reclamo_sulfuros,
        d.modulo_reclamo_sulfuros,
        d.Avance_reclamo_sulfuros,


        /* ========================================================
           CAMIONES
           Fuente histórica temporal
           ======================================================== */

        d.Camiones_TMS_Reclamo_Oxidos,
        d.Camiones_TMS_Reclamo_Sulfuros,

        d.Movido,
        d.Extraido,

        d.Camiones_TMS_total,

        pm.Camiones_TMS_Plan
            AS Camiones_TMS_plan,

        d.Campana_reclamo_camiones,
        d.Modulo_reclamo_camiones,


        /* ========================================================
           RIPIOS

           Real:
           histórico temporal.

           Plan:
           Rotopala 1 + Rotopala 2 + Camiones.
           ======================================================== */

        d.Total_Ripios_Incluye_Camiones_Real,

        CASE
            WHEN pm.TMS_Rotopala_1_Plan IS NOT NULL
             AND pm.TMS_Rotopala_2_Plan IS NOT NULL
             AND pm.Camiones_TMS_Plan IS NOT NULL
            THEN
                CAST(pm.TMS_Rotopala_1_Plan AS decimal(20,3))
                + CAST(pm.TMS_Rotopala_2_Plan AS decimal(20,3))
                + CAST(pm.Camiones_TMS_Plan AS decimal(20,3))

            ELSE
                d.Total_Ripios_Incluye_Camiones_Plan
        END AS Total_Ripios_Incluye_Camiones_Plan,


        /* ========================================================
           PRODUCCIÓN CATÓDICA
           ======================================================== */

        p.Produccion_Catodos_Real
            AS Produccion_Catodos_Real,

        pm.Produccion_Catodos_Plan
            AS Produccion_Catodos_Plan,


        /* ========================================================
           SRR REAL

           Fuente primaria:
           v_srr_tms_diario_test.

           Fallback:
           Datos_conciliados_of.
           ======================================================== */

        CASE
            WHEN s.Flag_SRR_TMS_Dia = 'OK'
                THEN s.SRR_TMS_Turno_A

            ELSE d.SRR_TMS_Turno_A
        END AS SRR_TMS_Turno_A,

        CASE
            WHEN s.Flag_SRR_TMS_Dia = 'OK'
                THEN s.SRR_TMS_Turno_B

            ELSE d.SRR_TMS_Turno_B
        END AS SRR_TMS_Turno_B,

        CASE
            WHEN s.Flag_SRR_TMS_Dia = 'OK'
                THEN s.SRR_TMS_Dia

            ELSE d.SRR_TMS_promedio_dia
        END AS SRR_TMS_promedio_dia,

        pm.SRR_TMS_Plan
            AS SRR_TMS_Plan,

        d.Ley_CuT_Real_srr,

        pm.Ley_CuT_Plan_SRR
            AS Ley_CuT_Plan_srr,


        /* ========================================================
           ESTADO HISTÓRICO
           ======================================================== */

        d.estado,


        /* ========================================================
           TRAZABILIDAD DE FUENTES
           ======================================================== */

        CASE
            WHEN d.Fecha IS NOT NULL
                THEN 'DATOS_CONCILIADOS_OF_TEMPORAL'
            ELSE 'SIN_DATO'
        END AS Fuente_Chancado,

        CASE
            WHEN a.Fecha IS NOT NULL
                THEN 'REPORTE_DIARIO_APILADO_TEST'
            ELSE 'SIN_DATO'
        END AS Fuente_Humedad,

        CASE
            WHEN a.Fecha IS NOT NULL
                THEN 'PESOMETROS_CORREGIDOS_Y_TOPOGRAFIA'
            ELSE 'SIN_DATO'
        END AS Fuente_Sal,

        CASE
            WHEN g.Fecha IS NOT NULL
                THEN 'FN_GENERADOR_REPORTE_DIARIO'
            ELSE 'SIN_DATO'
        END AS Fuente_Apilado,

        CASE
            WHEN d.Fecha IS NOT NULL
                THEN 'DATOS_CONCILIADOS_OF_TEMPORAL'
            ELSE 'SIN_DATO'
        END AS Fuente_Reclamo,

        CASE
            WHEN p.Fecha IS NOT NULL
                THEN 'PRODUCCION_CATODICA'
            ELSE 'SIN_DATO'
        END AS Fuente_Produccion_Catodos,

        CASE
            WHEN s.Flag_SRR_TMS_Dia = 'OK'
                THEN 'CALCULO_SRR_TEST'

            WHEN d.SRR_TMS_promedio_dia IS NOT NULL
                THEN 'DATOS_CONCILIADOS_OF_FALLBACK'

            ELSE 'SIN_DATO'
        END AS Fuente_SRR,


        /* ========================================================
           BANDERAS DE CONTROL
           ======================================================== */

        CASE
            WHEN d.Fecha IS NOT NULL
                THEN 1
            ELSE 0
        END AS Flag_Historico_Disponible,

        CASE
            WHEN s.Flag_SRR_TMS_Dia = 'OK'
                THEN 0

            WHEN d.SRR_TMS_promedio_dia IS NOT NULL
                THEN 1

            ELSE 0
        END AS Flag_SRR_Fallback,

        CASE
            WHEN COALESCE(g.Apilado_TMS_Real_Dia, 0) > 0
             AND g.CuT_Real_Dia IS NULL
                THEN 1
            ELSE 0
        END AS Flag_Ley_Apilado_Faltante,

        CASE
            WHEN p.Produccion_Catodos_Real IS NULL
                THEN 1
            ELSE 0
        END AS Flag_Produccion_Catodos_Faltante,


        /* ========================================================
           ESTADO GENERAL DEL CÁLCULO
           ======================================================== */

        CASE
            WHEN COALESCE(g.Apilado_TMS_Real_Dia, 0) > 0
             AND g.CuT_Real_Dia IS NULL
                THEN 'REVISAR LEY APILADO'

            WHEN s.Flag_SRR_TMS_Dia <> 'OK'
             AND d.SRR_TMS_promedio_dia IS NOT NULL
                THEN 'CON FALLBACK SRR'

            WHEN p.Produccion_Catodos_Real IS NULL
                THEN 'REVISAR PRODUCCION CATODICA'

            WHEN d.Fecha IS NULL
                THEN 'SIN BASE HISTORICA'

            ELSE 'OK'
        END AS Estado_Calculo

    FROM Fechas f

    LEFT JOIN DatosUnicos d
        ON CAST(d.Fecha AS date) = f.Fecha

    LEFT JOIN
        [inventar_SpcHidr].[v_reporte_diario_apilado_test] a
        ON CAST(a.Fecha AS date) = f.Fecha

    LEFT JOIN
        [inventar_SpcHidr].[fn_generador_reporte_diario]
        (
            @FechaInicio,
            @FechaFinExclusiva
        ) g
        ON CAST(g.Fecha AS date) = f.Fecha

    LEFT JOIN
        [inventar_SpcHidr].[v_srr_tms_diario_test] s
        ON CAST(s.Fecha AS date) = f.Fecha

    LEFT JOIN
        [inventar_SpcHidr].[v_produccion_catodica_diaria_test] p
        ON CAST(p.Fecha AS date) = f.Fecha

    LEFT JOIN
        [inventar_SpcHidr].[v_planes_mensuales_diarios_test] pm
        ON CAST(pm.Fecha AS date) = f.Fecha

    ORDER BY
        f.Fecha

    OPTION (MAXRECURSION 32767);

END;
