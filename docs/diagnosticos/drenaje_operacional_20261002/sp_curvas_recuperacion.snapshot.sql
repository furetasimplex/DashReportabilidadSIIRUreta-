-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/*
================================================================================
  04_sp_curvas_recuperacion_v2.sql
  Esquema : inventar_SpcHidr

  Fuentes de datos:
    - inventar_SpcHidr.v_aporte_cu_diario    (vista sobre recuperaciones_pad
                                              + parcela_campana_base
                                              + parcela_campana_cinetica)

  NO usa campana_parcela_control (tabla no disponible).
================================================================================
*/

/* ============================================================================
   1. sp_curvas_recuperacion
   ============================================================================ */
CREATE   PROCEDURE inventar_SpcHidr.sp_curvas_recuperacion
    @campana_id  INT,
    @pad_id      INT = NULL,
    @parcela_id  INT = NULL,
    @dias_max    INT = 500
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

    SELECT
        v.pad_id,
        v.pad_nombre,
        v.parcela_id,
        v.campana_id,
        v.numero_campana,
        v.Fecha_drenaje,
        v.dia_ciclo,
        v.rec_acum_pct,
        v.rec_diaria_pct,
        v.rec_modelo_pct,
        CASE
            WHEN v.rec_modelo_pct IS NOT NULL
            THEN ROUND(v.rec_acum_pct - v.rec_modelo_pct, 2)
            ELSE NULL
        END         AS brecha_modelo_pct,
        v.cu_diario_ton,
        v.cu_acum_ton,
        v.cu_diario_kg,
        v.tms_total,
        v.cut_pond,
        v.estado_ciclo,
        v.Rmax,
        v.k1,
        v.k2,
        v.fraccion_rapida,
        v.r2_cinetica

    FROM inventar_SpcHidr.v_aporte_cu_diario v
    WHERE v.campana_id = @campana_id
      AND v.dia_ciclo >= 1
      AND v.dia_ciclo <= @dias_max
      AND (@pad_id     IS NULL OR v.pad_id     = @pad_id)
      AND (@parcela_id IS NULL OR v.parcela_id = @parcela_id)

    ORDER BY v.pad_id, v.parcela_id, v.dia_ciclo;

END;
