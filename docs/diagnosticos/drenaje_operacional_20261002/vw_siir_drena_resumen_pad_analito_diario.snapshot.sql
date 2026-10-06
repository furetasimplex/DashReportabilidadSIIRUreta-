-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
CREATE   VIEW siir_mart.vw_siir_drena_resumen_pad_analito_diario

AS

SELECT

    d.fecha_dia,

    d.mes_inicio,

    d.anio,

    d.mes,

    d.pad_id_legacy,

    d.pad_nombre,

    d.analito_codigo,

    d.analito_nombre,

    d.orden_analito,

    COUNT(*) AS cantidad_parcelas_esperadas,

    SUM(CASE WHEN d.valor IS NOT NULL THEN 1 ELSE 0 END) AS cantidad_parcelas_con_dato,

    AVG(CAST(d.valor AS decimal(18,6))) AS valor_promedio,

    MIN(CAST(d.valor AS decimal(18,6))) AS valor_minimo,

    MAX(CAST(d.valor AS decimal(18,6))) AS valor_maximo,

    SUM(CASE WHEN d.flag_valor_negativo = 1 THEN 1 ELSE 0 END) AS cantidad_valores_negativos,

    SUM(CASE WHEN d.flag_ruido_cercano_cero = 1 THEN 1 ELSE 0 END) AS cantidad_valores_ruido_cero

FROM siir_curated.vw_siir_drena_concentrado_parcela_long AS d

GROUP BY

    d.fecha_dia,

    d.mes_inicio,

    d.anio,

    d.mes,

    d.pad_id_legacy,

    d.pad_nombre,

    d.analito_codigo,

    d.analito_nombre,

    d.orden_analito;
