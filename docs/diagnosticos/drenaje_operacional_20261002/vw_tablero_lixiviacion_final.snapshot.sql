-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
CREATE   VIEW inventar_SpcHidr.vw_tablero_lixiviacion_final
AS
WITH flujo_union AS
(
    SELECT
        1 AS pad_tipo,
        fecha,
        nro_parcela_pad,
        flujo_m3_h,
        flujo_m3_d
    FROM inventar_SpcHidr.vw_flujos_reales_oxido_long

    UNION ALL

    SELECT
        2 AS pad_tipo,
        fecha,
        nro_parcela_pad,
        flujo_m3_h,
        flujo_m3_d
    FROM inventar_SpcHidr.vw_flujos_reales_sulfuro_long
),
drenaje_union AS
(
    SELECT
        1 AS pad_tipo,
        fecha,
        nro_parcela_pad,
        cu_pp,
        h_p,
        ph,
        cl,
        fet,
        fe2,
        eh
    FROM inventar_SpcHidr.vw_drena_concentrados_oxido_long

    UNION ALL

    SELECT
        2 AS pad_tipo,
        fecha,
        nro_parcela_pad,
        cu_pp,
        h_p,
        ph,
        cl,
        fet,
        fe2,
        eh
    FROM inventar_SpcHidr.vw_drena_concentrados_sulfuro_long
),
refino_union AS
(
    SELECT
        1 AS pad_tipo,
        fecha,
        cu_pp,
        h_p,
        ph,
        cl,
        fet,
        fe2,
        eh
    FROM inventar_SpcHidr.vw_riego_oxido_refino_base

    UNION ALL

    SELECT
        2 AS pad_tipo,
        fecha,
        cu_pp,
        h_p,
        ph,
        cl,
        fet,
        fe2,
        eh
    FROM inventar_SpcHidr.vw_riego_sulfuro_refino_base
)
SELECT
    c.id_campana_parcela_control,
    c.campana_id,
    c.pad_id,
    c.parcela_id,
    c.modulo_id,
    c.numero_campana,
    c.nombre_pad,
    c.nombre_parcela,
    c.nombre_modulo,
    f.fecha,
    c.secuencia_carguio,
    c.secuencia_retiro,
    c.fecha_ini_carguio,
    c.fecha_fin_carguio,
    c.fecha_ini_reposo,
    c.fecha_fin_reposo,
    c.fecha_ini_operacion,
    c.fecha_fin_operacion,
    c.fecha_ini_drenaje,
    c.fecha_fin_drenaje,
    c.fecha_ini_retiro,
    c.fecha_fin_retiro,
    f.flujo_m3_h,
    f.flujo_m3_d,
    d.cu_pp AS cu_drenaje_ppm,
    d.h_p AS h_drenaje,
    d.ph AS ph_drenaje,
    d.cl AS cl_drenaje,
    d.fet AS fet_drenaje,
    d.fe2 AS fe2_drenaje,
    d.eh AS eh_drenaje,
    r.cu_pp AS cu_refino_ppm,
    r.h_p AS h_refino,
    r.ph AS ph_refino,
    r.cl AS cl_refino,
    r.fet AS fet_refino,
    r.fe2 AS fe2_refino,
    r.eh AS eh_refino,
    CASE WHEN d.cu_pp IS NOT NULL AND r.cu_pp IS NOT NULL
         THEN d.cu_pp - r.cu_pp
         ELSE NULL END AS delta_cu_ppm,
    CASE WHEN d.h_p IS NOT NULL AND r.h_p IS NOT NULL
         THEN d.h_p - r.h_p
         ELSE NULL END AS delta_h,
    CASE WHEN f.flujo_m3_d IS NOT NULL
           AND d.cu_pp IS NOT NULL
           AND r.cu_pp IS NOT NULL
         THEN f.flujo_m3_d * (d.cu_pp - r.cu_pp) / 1000.0
         ELSE NULL END AS transferencia_cu_kg_d,
    DATEDIFF(DAY, c.fecha_ini_carguio, f.fecha) + 1 AS dia_relativo_campana,
    CASE
        WHEN f.fecha BETWEEN c.fecha_ini_carguio AND c.fecha_fin_carguio THEN 'CARGUIO'
        WHEN f.fecha BETWEEN c.fecha_ini_reposo AND c.fecha_fin_reposo THEN 'REPOSO'
        WHEN f.fecha BETWEEN c.fecha_ini_operacion AND c.fecha_fin_operacion THEN 'OPERACION'
        WHEN f.fecha BETWEEN c.fecha_ini_drenaje AND c.fecha_fin_drenaje THEN 'DRENAJE'
        WHEN f.fecha BETWEEN c.fecha_ini_retiro AND c.fecha_fin_retiro THEN 'RETIRO'
        ELSE 'FUERA_CICLO'
    END AS fase_operacional,
    c.tmh_cargado,
    c.tms_cargado,
    c.humedad_promedio,
    c.sal_promedio,
    c.cut_tm_total,
    c.cus_tm_total,
    c.cu_insoluble_total,
    c.altura_modulo_max
FROM inventar_SpcHidr.campana_parcela_control c
LEFT JOIN flujo_union f
    ON f.nro_parcela_pad = TRY_CAST(c.nombre_parcela AS INT)
   AND f.fecha BETWEEN c.fecha_ini_carguio AND ISNULL(c.fecha_fin_retiro, '2099-12-31')
   AND (
        (c.pad_id = 1 AND f.pad_tipo = 1)
        OR
        (c.pad_id = 65 AND f.pad_tipo = 2)
        OR
        (c.pad_id NOT IN (1,65))
   )
LEFT JOIN drenaje_union d
    ON d.nro_parcela_pad = f.nro_parcela_pad
   AND d.fecha = f.fecha
   AND d.pad_tipo = f.pad_tipo
LEFT JOIN refino_union r
    ON r.fecha = f.fecha
   AND r.pad_tipo = f.pad_tipo;
