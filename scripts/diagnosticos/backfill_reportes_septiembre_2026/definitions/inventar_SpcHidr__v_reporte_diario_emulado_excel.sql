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