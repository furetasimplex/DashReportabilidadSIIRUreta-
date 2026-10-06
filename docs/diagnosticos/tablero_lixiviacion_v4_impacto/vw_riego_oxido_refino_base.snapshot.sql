-- EVIDENCIA HISTORICA; NO DESPLEGAR. Origen: report_export/exports/auditoria_ley_srr_202609/catalogo.json
CREATE   VIEW inventar_SpcHidr.vw_riego_oxido_refino_base
AS
SELECT
    id_registro,
    CAST(fecha_registro AS DATE) AS fecha,
    fecha_registro,
    refino_cu_pp AS cu_pp,
    refino_h_p   AS h_p,
    refino_ph    AS ph,
    refino_cl    AS cl,
    refino_fet   AS fet,
    refino_fe2   AS fe2,
    refino_eh    AS eh
FROM inventar_SpcHidr.riego_concentrados_oxido;
