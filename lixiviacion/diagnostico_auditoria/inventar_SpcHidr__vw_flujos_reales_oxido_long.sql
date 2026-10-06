CREATE VIEW [inventar_SpcHidr].[vw_flujos_reales_oxido_long] AS SELECT
    fr.id_flujo_real,
    CAST(fr.fecha_registro AS date) AS fecha,
    fr.fecha_registro,

    p.id_pad       AS pad_id,
    p.id_parcela   AS parcela_id,
    v.nro_parcela_pad,

    CAST(v.flujo_m3_h AS decimal(38,15)) AS flujo_m3_h,
    CAST(v.flujo_m3_h * 24.0 AS decimal(38,15)) AS flujo_m3_d
FROM inventar_SpcHidr.flujos_reales_oxido fr
CROSS APPLY (VALUES
    (1 , fr.parcela_01),(2 , fr.parcela_02),(3 , fr.parcela_03),(4 , fr.parcela_04),
    (5 , fr.parcela_05),(6 , fr.parcela_06),(7 , fr.parcela_07),(8 , fr.parcela_08),
    (9 , fr.parcela_09),(10, fr.parcela_10),(11, fr.parcela_11),(12, fr.parcela_12),
    (13, fr.parcela_13),(14, fr.parcela_14),(15, fr.parcela_15),(16, fr.parcela_16),
    (17, fr.parcela_17),(18, fr.parcela_18),(19, fr.parcela_19),(20, fr.parcela_20),
    (21, fr.parcela_21),(22, fr.parcela_22),(23, fr.parcela_23),(24, fr.parcela_24),
    (25, fr.parcela_25),(26, fr.parcela_26),(27, fr.parcela_27),(28, fr.parcela_28),
    (29, fr.parcela_29),(30, fr.parcela_30),(31, fr.parcela_31),(32, fr.parcela_32)
) v(nro_parcela_pad, flujo_m3_h)
LEFT JOIN inventar_SpcHidr.parcela p
    ON v.nro_parcela_pad = p.numero and id_pad=1;