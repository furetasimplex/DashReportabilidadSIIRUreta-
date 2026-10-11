CREATE VIEW inventar_SpcHidr.vw_Reporte_preliminar AS

-- [CTEs DEL 1 AL 8 SE MANTIENEN EXACTAMENTE IGUALES]
-- 1. CTE: Limpieza de Duplicados en Humedades
WITH HumedadesLimpio AS (
    SELECT 
        Fecha,
        AVG(Humedades_Turno_A) AS Humedades_Turno_A,
        AVG(Humedades_Turno_B) AS Humedades_Turno_B,
        AVG(Humedades_Dia) AS Humedades_Dia
    FROM inventar_SpcHidr.import_leyes_torres
    GROUP BY Fecha
),

-- 2. CTE: Ley SRR (Líquido)
LeySrrDiaria AS (
    SELECT
        CAST(Fecha AS DATE) AS dia_cte,
        CASE WHEN SUM(Ton) = 0 OR SUM(Ton) IS NULL THEN 0 ELSE SUM(Ton * CuTG00) / SUM(Ton) END AS ley_cu_srr
    FROM inventar_SpcHidr.mov_cam
    WHERE Fase = 'SRR'
    GROUP BY CAST(Fecha AS DATE)
),

-- 3. CTE: Ley Mineral Sólido
LeyMineralDiaria AS (
    SELECT
        CAST(Fecha AS DATE) AS dia_cte,
        CASE WHEN SUM(Ton) = 0 OR SUM(Ton) IS NULL THEN 0 ELSE SUM(Ton * CuTG00) / SUM(Ton) END AS ley_cut_mineral
    FROM inventar_SpcHidr.mov_cam
    WHERE Fase IN ('Apilado', 'Chancado') 
    GROUP BY CAST(Fecha AS DATE)
),

-- 4. CTE: Datos SAL (Agrupados)
SalCalculada AS (
    SELECT
        Fecha,
        SUM(COALESCE(cv201_tot_TurnoA, 0) + COALESCE(cv202_tot_TurnoA, 0)) AS sal_turno_a,
        SUM(COALESCE(cv201_tot_TurnoB, 0) + COALESCE(cv202_tot_TurnoB, 0)) AS sal_turno_b,
        SUM(COALESCE(cv201_tot_Dia, 0) + COALESCE(cv202_tot_Dia, 0)) AS sal_dia
    FROM inventar_SpcHidr.vista_resumen_turnos_dia
    GROUP BY Fecha
),

-- 5. CTE: Resumen Turnos
ResumenTurnos AS (
    SELECT
        Fecha,
        SUM(cv001_tot_TurnoA) as srr_turno_a,
        SUM(cv001_tot_TurnoB) as srr_turno_b,
        SUM(cv001_tot_Dia) as srr_dia,
        SUM(apilado_ton_TurnoA) as apilado_tmh_TurnoA,
        SUM(apilado_ton_TurnoB) as apilado_tmh_TurnoB,
        SUM(apilado_ton_Dia) as apilado_tmh_Dia
    FROM inventar_SpcHidr.vista_resumen_turnos_dia
    GROUP BY Fecha
),

-- 6. CTE: Chancado Húmedo
ChancadoData AS (
    SELECT 
        fecha_turno, 
        SUM(cv006_tot) as chancado_tmh
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
    GROUP BY fecha_turno
),

-- 7. CTE: Selección del Caso Activo
CasoActivoInfo AS (
    SELECT TOP 1
        fecha_ini, 
        fecha
    FROM inventar_SpcHidr.casos_balance
    ORDER BY caso_id DESC 
),

-- 8. CTE: Generador de Fechas Exactas
DateRange AS (
    SELECT CAST(fecha_ini AS DATE) AS dia_rango
    FROM CasoActivoInfo
    UNION ALL
    SELECT DATEADD(day, 1, dia_rango)
    FROM DateRange dr
    JOIN CasoActivoInfo cai ON 1=1
    WHERE dia_rango < cai.fecha 
)

-- === SELECT FINAL CON EL CAMBIO ===
SELECT
    dr.dia_rango AS dia,

    -- A. CHANCADO (TMS Calculado)
    (COALESCE(ch.chancado_tmh, 0) * (100 - COALESCE(hl.Humedades_Dia, 0)) / 100) AS chancado_tms_real,

    -- B. HUMEDADES (Sin duplicados)
    hl.Humedades_Turno_A AS humedad_turno_a,
    hl.Humedades_Turno_B AS humedad_turno_b,
    hl.Humedades_Dia AS humedad_dia,

    -- C. SAL
    sc.sal_turno_a,
    sc.sal_turno_b,
    sc.sal_dia,

    -- D. SRR
    rt.srr_turno_a,
    rt.srr_turno_b,
    rt.srr_dia,
    lsd.ley_cu_srr AS srr_cu_real,
    
    -- CAMBIO 1: Aquí traemos la columna del plan en lugar de NULL
    pm.ley_cut_srr AS srr_cu_plan,

    -- E. MINERAL APILADO (Cálculos)
    -- 1. Apilado TMH
    (COALESCE(rt.apilado_tmh_TurnoA, 0) - COALESCE(sc.sal_turno_a, 0)) AS apilado_tmh_turno_a,
    (COALESCE(rt.apilado_tmh_TurnoB, 0) - COALESCE(sc.sal_turno_b, 0)) AS apilado_tmh_turno_b,
    (COALESCE(rt.apilado_tmh_Dia, 0) - COALESCE(sc.sal_dia, 0)) AS apilado_tmh_dia,

    -- 2. Apilado TMS
    (
      (COALESCE(rt.apilado_tmh_Dia, 0) - COALESCE(sc.sal_dia, 0)) * (100 - COALESCE(hl.Humedades_Dia, 0)) / 100
    ) AS apilado_tms_real,
    NULL AS apilado_tms_plan,

    -- 3. Leyes y Finos
    lmd.ley_cut_mineral AS ley_cut_real,
    NULL AS ley_cut_plan,
    
    (
      ( (COALESCE(rt.apilado_tmh_Dia, 0) - COALESCE(sc.sal_dia, 0)) * (100 - COALESCE(hl.Humedades_Dia, 0)) / 100 ) 
      * COALESCE(lmd.ley_cut_mineral, 0) / 100
    ) AS cu_fino_apilado_real,
    NULL AS cu_fino_apilado_plan

FROM DateRange dr
LEFT JOIN ChancadoData ch ON dr.dia_rango = ch.fecha_turno
LEFT JOIN HumedadesLimpio hl ON dr.dia_rango = hl.Fecha
LEFT JOIN ResumenTurnos rt ON dr.dia_rango = rt.Fecha
LEFT JOIN SalCalculada sc ON dr.dia_rango = sc.Fecha
LEFT JOIN LeySrrDiaria lsd ON dr.dia_rango = lsd.dia_cte
LEFT JOIN LeyMineralDiaria lmd ON dr.dia_rango = lmd.dia_cte
-- CAMBIO 2: El Join con la tabla de planes
LEFT JOIN inventar_SpcHidr.plan_mensual_hidro pm ON dr.dia_rango = pm.fecha;