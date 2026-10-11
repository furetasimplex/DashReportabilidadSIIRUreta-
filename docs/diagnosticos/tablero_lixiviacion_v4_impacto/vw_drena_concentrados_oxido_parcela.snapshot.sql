-- EVIDENCIA HISTORICA; NO DESPLEGAR. Origen: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/* ============================================================
   13) DRENAJE OXIDO + PARCELA REAL
   ============================================================ */
CREATE   VIEW inventar_SpcHidr.vw_drena_concentrados_oxido_parcela
AS
SELECT
    d.id_registro,
    d.fecha,
    d.fecha_registro,
    m.id_pad,
    m.nombre_pad,
    m.id_parcela,
    m.nro_parcela_pad,
    d.cu_pp,
    d.h_p,
    d.ph,
    d.cl,
    d.fet,
    d.fe2,
    d.eh
FROM inventar_SpcHidr.vw_drena_concentrados_oxido_long d
INNER JOIN inventar_SpcHidr.vw_pad_parcela_control m
    ON m.nro_parcela_pad = d.nro_parcela_pad
WHERE m.nombre_pad LIKE '%ox%'
   OR m.id_pad IN (
        SELECT DISTINCT id_pad
        FROM inventar_SpcHidr.vw_dim_parcela_pad
        WHERE nro_parcela_pad <= 32
   );
