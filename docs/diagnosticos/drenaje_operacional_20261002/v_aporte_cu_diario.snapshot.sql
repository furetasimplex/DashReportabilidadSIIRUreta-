-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/*
================================================================================
  03_vista_aporte_cu_diario.sql
  Esquema : inventar_SpcHidr

  Vista que calcula el aporte diario de Cu combinando:
    • recuperaciones_pad       → recuperación acumulada diaria (%)
    • parcela_campana_base     → TMS ponderado, ley CuT, estado
    • parcela_campana_cinetica → parámetros cinéticos (LEFT JOIN, opcional)

  Columnas eliminadas de la vista para evitar error 207:
    • area_m2  — no existe en parcela_campana_base actual; agregar con ALTER TABLE si se necesita
    • modulo   — ídem; disponible via modulos_turnos si se requiere

  Para cada (pad, parcela, campaña, día):
    Δrec      = rec(t) − rec(t−1)            [% diferencial]
    cu_ton(t) = TMS × CuT/100 × Δrec/100    [ton Cu diario]
    cu_kg(t)  = cu_ton(t) × 1000             [kg Cu diario]

  Uso:
      SELECT * FROM inventar_SpcHidr.v_aporte_cu_diario
      WHERE campana_id = 11 AND pad_id = 2
      ORDER BY parcela_id, Fecha_drenaje;
================================================================================
*/

CREATE   VIEW inventar_SpcHidr.v_aporte_cu_diario
AS
WITH cte_rec AS (

    SELECT
        r.id_rec,
        r.pad_id,
        r.parcela_id,
        CAST(r.campaña_id AS INT)                           AS campana_id,
        r.Fecha_drenaje,
        r.Recuperacion_parcela                              AS rec_acum_pct,

        -- Diferencial diario (rec del día − rec del día anterior)
        r.Recuperacion_parcela
            - ISNULL(
                LAG(r.Recuperacion_parcela) OVER (
                    PARTITION BY r.pad_id, r.parcela_id, r.campaña_id
                    ORDER BY r.Fecha_drenaje
                ), 0
              )                                             AS rec_diaria_pct,

        -- Día de ciclo (1-based desde la primera fecha del grupo)
        DATEDIFF(day,
            MIN(r.Fecha_drenaje) OVER (
                PARTITION BY r.pad_id, r.parcela_id, r.campaña_id
            ),
            r.Fecha_drenaje
        ) + 1                                               AS dia_ciclo

    FROM inventar_SpcHidr.recuperaciones_pad r
    WHERE r.Recuperacion_parcela IS NOT NULL
),

cte_join AS (
    SELECT
        rec.id_rec,
        rec.pad_id,
        ISNULL(b.pad_nombre,   rec.pad_id)                  AS pad_nombre,
        rec.parcela_id,
        rec.campana_id,
        b.numero_campana,
        rec.Fecha_drenaje,
        rec.dia_ciclo,

        -- Recuperación
        ROUND(rec.rec_acum_pct,   2)                        AS rec_acum_pct,
        ROUND(rec.rec_diaria_pct, 4)                        AS rec_diaria_pct,

        -- Tonelaje y ley (de parcela_campana_base)
        ISNULL(b.tms_total, 0)                              AS tms_total,
        ISNULL(b.cut_pond,  0)                              AS cut_pond,
        b.estado_ciclo,

        -- Cu diario (ton) = TMS × CuT% × Δrec%  /  10000
        ROUND(
            ISNULL(b.tms_total, 0)
            * ISNULL(b.cut_pond, 0) / 100.0
            * (CASE WHEN rec.rec_diaria_pct > 0
                    THEN rec.rec_diaria_pct ELSE 0 END) / 100.0,
        4)                                                  AS cu_diario_ton,

        -- Cu acumulado (ton)
        ROUND(
            ISNULL(b.tms_total, 0)
            * ISNULL(b.cut_pond, 0) / 100.0
            * rec.rec_acum_pct / 100.0,
        4)                                                  AS cu_acum_ton,

        -- Cu diario (kg)
        ROUND(
            ISNULL(b.tms_total, 0)
            * ISNULL(b.cut_pond, 0) / 100.0
            * (CASE WHEN rec.rec_diaria_pct > 0
                    THEN rec.rec_diaria_pct ELSE 0 END) / 100.0
            * 1000.0,
        2)                                                  AS cu_diario_kg,

        -- Parámetros cinéticos (NULL si no existen aún)
        ck.Rmax,
        ck.k1,
        ck.k2,
        ck.A                                                AS fraccion_rapida,
        ck.r2                                               AS r2_cinetica,

        -- Recuperación proyectada por modelo cinético en el día actual
        CASE WHEN ck.Rmax IS NOT NULL THEN
            ROUND(
                ck.Rmax * (
                      ck.A        * (1 - EXP(-ck.k1 * rec.dia_ciclo))
                    + (1 - ck.A)  * (1 - EXP(-ck.k2 * rec.dia_ciclo))
                ), 2)
        ELSE NULL END                                       AS rec_modelo_pct

    FROM cte_rec rec

    LEFT JOIN inventar_SpcHidr.parcela_campana_base b
           ON b.pad_id     = rec.pad_id
          AND b.parcela_id = rec.parcela_id
          AND b.campana_id = rec.campana_id

    LEFT JOIN inventar_SpcHidr.parcela_campana_cinetica ck
           ON ck.pad_id     = rec.pad_id
          AND ck.parcela_id = rec.parcela_id
          AND ck.campana_id = rec.campana_id
)

SELECT * FROM cte_join;
