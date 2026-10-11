CREATE   VIEW inventar_SpcHidr.vw_datos_conciliados_publicacion_base
AS
WITH HumedadesLimpio AS (
    SELECT
        CAST(Fecha AS date) AS Fecha,
        AVG(Humedades_Turno_A) AS Humedad_Turno_A,
        AVG(Humedades_Turno_B) AS Humedad_Turno_B,
        AVG(Humedades_Dia)     AS Humedad_promedio_dia
    FROM inventar_SpcHidr.import_leyes_torres
    GROUP BY CAST(Fecha AS date)
),

LeySrrDiaria AS (
    SELECT
        CAST(Fecha AS date) AS Fecha,
        CASE
            WHEN SUM(Ton) IS NULL OR SUM(Ton) = 0 THEN NULL
            ELSE SUM(Ton * CuTG00) / SUM(Ton)
        END AS Ley_CuT_Real_srr
    FROM inventar_SpcHidr.mov_cam
    WHERE Fase = 'SRR'
    GROUP BY CAST(Fecha AS date)
),

LeyMineralDiaria AS (
    SELECT
        CAST(Fecha AS date) AS Fecha,
        CASE
            WHEN SUM(Ton) IS NULL OR SUM(Ton) = 0 THEN NULL
            ELSE SUM(Ton * CuTG00) / SUM(Ton)
        END AS Ley_CuT_Real
    FROM inventar_SpcHidr.mov_cam
    WHERE Fase IN ('Apilado', 'Chancado')
    GROUP BY CAST(Fecha AS date)
),

PlanMensualDiario AS (
    SELECT
        CAST(fecha AS date) AS Fecha,

        mineral_tms       AS Apilado_TMS_Plan,
        ley_cut_global    AS Ley_CuT_Plan,
        cu_fino_total     AS Cobre_fino_Apilado_Plan,

        mineral_srr_tms   AS SRR_TMS_Plan,
        ley_cut_srr       AS Ley_CuT_Plan_srr,

        rotopala_oxido    AS TMS_Rotopala_1_Plan,
        rotopala_sulfuro  AS TMS_Rotopala_2_Plan,

        camiones_sulfuros AS Camiones_TMS_plan,
        cosecha_mdc       AS Produccion_Catodos_Plan,

        (rotopala_oxido + rotopala_sulfuro + camiones_sulfuros)
            AS Total_Ripios_Incluye_Camiones_Plan

    FROM inventar_SpcHidr.plan_mensual_hidro
),

ResumenTurnos AS (
    SELECT
        CAST(Fecha AS date) AS Fecha,

        SUM(COALESCE(cv201_tot_TurnoA, 0)) AS cv201_tot_TurnoA,
        SUM(COALESCE(cv201_tot_TurnoB, 0)) AS cv201_tot_TurnoB,
        SUM(COALESCE(cv201_tot_Dia, 0))    AS cv201_tot_Dia,

        SUM(COALESCE(cv202_tot_TurnoA, 0)) AS cv202_tot_TurnoA,
        SUM(COALESCE(cv202_tot_TurnoB, 0)) AS cv202_tot_TurnoB,
        SUM(COALESCE(cv202_tot_Dia, 0))    AS cv202_tot_Dia,

        SUM(COALESCE(cv001_tot_TurnoA, 0)) AS cv001_tot_TurnoA,
        SUM(COALESCE(cv001_tot_TurnoB, 0)) AS cv001_tot_TurnoB,
        SUM(COALESCE(cv001_tot_Dia, 0))    AS cv001_tot_Dia,

        /* APILADO EN BASE HÚMEDA */
        SUM(COALESCE(apilado_ton_TurnoA, 0)) AS apilado_tmh_TurnoA,
        SUM(COALESCE(apilado_ton_TurnoB, 0)) AS apilado_tmh_TurnoB,
        SUM(COALESCE(apilado_ton_Dia, 0))    AS apilado_tmh_Dia
    FROM inventar_SpcHidr.vista_resumen_turnos_dia
    GROUP BY CAST(Fecha AS date)
),

ChancadoData AS (
    SELECT
        CAST(fecha_turno AS date) AS Fecha,
        SUM(COALESCE(cv006_tot, 0)) AS Chancado_TMH
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
    GROUP BY CAST(fecha_turno AS date)
),

ApiladoControlRanking AS (
    SELECT
        cad.modulo,
        cad.avance_porcentaje,
        cad.volumen_diario_m3,
        CAST(cad.fecha AS date) AS fecha_control,
        cad.pad_id,
        p.nombre AS pad_nombre,
        ROW_NUMBER() OVER (
            PARTITION BY CAST(cad.fecha AS date)
            ORDER BY
                cad.modulo DESC,
                cad.avance_porcentaje DESC,
                cad.volumen_diario_m3 DESC
        ) AS rn
    FROM inventar_SpcHidr.control_apilado_diario cad
    INNER JOIN inventar_SpcHidr.pad p
        ON cad.pad_id = p.id_pad
    WHERE cad.volumen_diario_m3 > 0
),

ApiladoControlDiario AS (
    SELECT
        modulo,
        avance_porcentaje,
        volumen_diario_m3,
        CAST(DATEADD(DAY, -1, fecha_control) AS date) AS Fecha,
        pad_id,
        pad_nombre
    FROM ApiladoControlRanking
    WHERE rn = 1
),

FechasBase AS (
    SELECT Fecha FROM HumedadesLimpio
    UNION
    SELECT Fecha FROM LeySrrDiaria
    UNION
    SELECT Fecha FROM LeyMineralDiaria
    UNION
    SELECT Fecha FROM PlanMensualDiario
    UNION
    SELECT Fecha FROM ResumenTurnos
    UNION
    SELECT Fecha FROM ChancadoData
    UNION
    SELECT Fecha FROM ApiladoControlDiario
)

SELECT
    fb.Fecha,

    /* CHANCADO */
    CASE
        WHEN ch.Chancado_TMH IS NULL THEN NULL
        ELSE ch.Chancado_TMH * (100.0 - COALESCE(h.Humedad_promedio_dia, 0)) / 100.0
    END AS Chancado_TMS_Real,

    /* HUMEDADES */
    h.Humedad_Turno_A,
    h.Humedad_Turno_B,
    h.Humedad_promedio_dia,

    /* SAL = CV201 + CV202 */
    (COALESCE(r.cv201_tot_TurnoA, 0) + COALESCE(r.cv202_tot_TurnoA, 0)) AS Sal_turno_A,
    (COALESCE(r.cv201_tot_TurnoB, 0) + COALESCE(r.cv202_tot_TurnoB, 0)) AS Sal_Turno_B,
    (COALESCE(r.cv201_tot_Dia, 0)    + COALESCE(r.cv202_tot_Dia, 0))    AS Sal_promedio_dia,

    /* APILADO TMH */
    COALESCE(r.apilado_tmh_TurnoA, 0) AS Apilado_TMH_turno_A,
    COALESCE(r.apilado_tmh_TurnoB, 0) AS Apilado_TMH_turno_B,
    COALESCE(r.apilado_tmh_Dia, 0)    AS Apilado_TMH_promedio_dia,

    /* APILADO TMS */
    (
        COALESCE(r.apilado_tmh_Dia, 0)
        * (100.0 - COALESCE(h.Humedad_promedio_dia, 0)) / 100.0
    ) AS Apilado_TMS_Real,

    pm.Apilado_TMS_Plan,

    /* APILADO CONTEXTO OPERACIONAL */
    CAST(ac.pad_nombre AS nvarchar(255)) AS Campana_apilado,
    CAST(ac.modulo AS int) AS Modulo_apilado,
    CAST(ac.avance_porcentaje AS float) AS Avance_apilado,

    /* LEY MINERAL Y FINOS */
    lm.Ley_CuT_Real,
    pm.Ley_CuT_Plan,

    (
        (
            COALESCE(r.apilado_tmh_Dia, 0)
            * (100.0 - COALESCE(h.Humedad_promedio_dia, 0)) / 100.0
        )
        * COALESCE(lm.Ley_CuT_Real, 0) / 100.0
    ) AS Cobre_fino_Apilado_Real,

    pm.Cobre_fino_Apilado_Plan,

    /* ROTOPALAS */
    CAST(NULL AS float) AS TMS_Rotopala_1_Real,
    pm.TMS_Rotopala_1_Plan,
    CAST(NULL AS nvarchar(255)) AS Campana_reclamo_oxidos,
    CAST(NULL AS int) AS Modulo_reclamo_oxidos,
    CAST(NULL AS float) AS Avance_reclamo_oxidos,

    CAST(NULL AS float) AS TMS_Rotopala_2_Real,
    pm.TMS_Rotopala_2_Plan,
    CAST(NULL AS nvarchar(255)) AS Campana_reclamo_sulfuros,
    CAST(NULL AS int) AS modulo_reclamo_sulfuros,
    CAST(NULL AS float) AS Avance_reclamo_sulfuros,

    /* CAMIONES / RIPIOS */
    CAST(NULL AS float) AS Camiones_TMS_Reclamo_Oxidos,
    CAST(NULL AS float) AS Camiones_TMS_Reclamo_Sulfuros,
    CAST(NULL AS nvarchar(255)) AS Movido,
    CAST(NULL AS nvarchar(255)) AS Extraido,
    CAST(NULL AS float) AS Camiones_TMS_total,
    CAST(pm.Camiones_TMS_plan AS int) AS Camiones_TMS_plan,
    CAST(NULL AS nvarchar(255)) AS Campana_reclamo_camiones,
    CAST(NULL AS nvarchar(255)) AS Modulo_reclamo_camiones,
    CAST(NULL AS float) AS Total_Ripios_Incluye_Camiones_Real,
    pm.Total_Ripios_Incluye_Camiones_Plan,

    /* PRODUCCIÓN */
    CAST(NULL AS float) AS Produccion_Catodos_Real,
    CAST(pm.Produccion_Catodos_Plan AS int) AS Produccion_Catodos_Plan,

    /* SRR = CV001 */
    COALESCE(r.cv001_tot_TurnoA, 0) AS SRR_TMS_Turno_A,
    COALESCE(r.cv001_tot_TurnoB, 0) AS SRR_TMS_Turno_B,
    COALESCE(r.cv001_tot_Dia, 0)    AS SRR_TMS_promedio_dia,
    pm.SRR_TMS_Plan,
    ls.Ley_CuT_Real_srr,
    pm.Ley_CuT_Plan_srr,

    /* ESTADO BASE */
    CAST(0 AS int) AS estado_base_publicacion,

    /* CAMPOS AUXILIARES PARA UI / STAGING */
    CAST(ac.pad_id AS int) AS Pad_id_apilado,
    CAST(ac.volumen_diario_m3 AS float) AS Volumen_diario_m3_apilado,

    /* FLAGS CALIDAD */
    CASE WHEN h.Humedad_promedio_dia IS NOT NULL THEN 1 ELSE 0 END AS flg_humedad,
    CASE WHEN (COALESCE(r.cv201_tot_Dia, 0) + COALESCE(r.cv202_tot_Dia, 0)) <> 0 THEN 1 ELSE 0 END AS flg_sal,
    CASE WHEN COALESCE(r.cv001_tot_Dia, 0) <> 0 THEN 1 ELSE 0 END AS flg_srr,
    CASE WHEN lm.Ley_CuT_Real IS NOT NULL THEN 1 ELSE 0 END AS flg_ley_mineral,
    CASE WHEN ls.Ley_CuT_Real_srr IS NOT NULL THEN 1 ELSE 0 END AS flg_ley_srr,

    CASE
        WHEN
            (CASE WHEN h.Humedad_promedio_dia IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN (COALESCE(r.cv201_tot_Dia, 0) + COALESCE(r.cv202_tot_Dia, 0)) <> 0 THEN 1 ELSE 0 END) +
            (CASE WHEN COALESCE(r.cv001_tot_Dia, 0) <> 0 THEN 1 ELSE 0 END) +
            (CASE WHEN lm.Ley_CuT_Real IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN ls.Ley_CuT_Real_srr IS NOT NULL THEN 1 ELSE 0 END)
            >= 5
        THEN 'COMPLETO'
        WHEN
            (CASE WHEN h.Humedad_promedio_dia IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN (COALESCE(r.cv201_tot_Dia, 0) + COALESCE(r.cv202_tot_Dia, 0)) <> 0 THEN 1 ELSE 0 END) +
            (CASE WHEN COALESCE(r.cv001_tot_Dia, 0) <> 0 THEN 1 ELSE 0 END) +
            (CASE WHEN lm.Ley_CuT_Real IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN ls.Ley_CuT_Real_srr IS NOT NULL THEN 1 ELSE 0 END)
            >= 3
        THEN 'PARCIAL'
        ELSE 'CRITICO'
    END AS nivel_completitud

FROM FechasBase fb
LEFT JOIN HumedadesLimpio h
    ON fb.Fecha = h.Fecha
LEFT JOIN ResumenTurnos r
    ON fb.Fecha = r.Fecha
LEFT JOIN ChancadoData ch
    ON fb.Fecha = ch.Fecha
LEFT JOIN LeySrrDiaria ls
    ON fb.Fecha = ls.Fecha
LEFT JOIN LeyMineralDiaria lm
    ON fb.Fecha = lm.Fecha
LEFT JOIN PlanMensualDiario pm
    ON fb.Fecha = pm.Fecha
LEFT JOIN ApiladoControlDiario ac
    ON fb.Fecha = ac.Fecha;