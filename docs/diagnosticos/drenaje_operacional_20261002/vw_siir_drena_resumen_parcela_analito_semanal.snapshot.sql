-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
CREATE   VIEW siir_mart.vw_siir_drena_resumen_parcela_analito_semanal

AS

WITH base AS (

    SELECT

        d.fecha_dia,

        DATEADD(day, - (DATEDIFF(day, '19000101', d.fecha_dia) % 7), d.fecha_dia) AS semana_inicio,

        d.pad_id_legacy,

        d.pad_nombre,

        d.parcela_id_global,

        d.nro_parcela_pad,

        d.codigo_parcela_negocio,

        d.analito_codigo,

        d.analito_nombre,

        d.orden_analito,

        d.valor,

        d.flag_valor_negativo,

        d.flag_ruido_cercano_cero

    FROM siir_curated.vw_siir_drena_concentrado_parcela_long AS d

)

SELECT

    semana_inicio,

    YEAR(semana_inicio) AS anio_semana,

    MONTH(semana_inicio) AS mes_semana,

    pad_id_legacy,

    pad_nombre,

    parcela_id_global,

    nro_parcela_pad,

    codigo_parcela_negocio,

    analito_codigo,

    analito_nombre,

    orden_analito,

    COUNT(*) AS cantidad_dias_semana,

    SUM(CASE WHEN valor IS NOT NULL THEN 1 ELSE 0 END) AS cantidad_dias_con_dato,

    AVG(CAST(valor AS decimal(18,6))) AS valor_promedio,

    MIN(CAST(valor AS decimal(18,6))) AS valor_minimo,

    MAX(CAST(valor AS decimal(18,6))) AS valor_maximo,

    SUM(CASE WHEN flag_valor_negativo = 1 THEN 1 ELSE 0 END) AS cantidad_valores_negativos,

    SUM(CASE WHEN flag_ruido_cercano_cero = 1 THEN 1 ELSE 0 END) AS cantidad_valores_ruido_cero

FROM base

GROUP BY

    semana_inicio,

    pad_id_legacy,

    pad_nombre,

    parcela_id_global,

    nro_parcela_pad,

    codigo_parcela_negocio,

    analito_codigo,

    analito_nombre,

    orden_analito;
