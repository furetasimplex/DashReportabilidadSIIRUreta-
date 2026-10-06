CREATE VIEW inventar_SpcHidr.v_flujos_oxido_unpivot AS
SELECT id_flujo_real, fecha_registro, parcela_numero, caudal
FROM (
    SELECT id_flujo_real, fecha_registro,
        parcela_01,parcela_02,parcela_03,parcela_04,parcela_05,parcela_06,parcela_07,parcela_08,
        parcela_09,parcela_10,parcela_11,parcela_12,parcela_13,parcela_14,parcela_15,parcela_16,
        parcela_17,parcela_18,parcela_19,parcela_20,parcela_21,parcela_22,parcela_23,parcela_24,
        parcela_25,parcela_26,parcela_27,parcela_28,parcela_29,parcela_30,parcela_31,parcela_32
    FROM inventar_SpcHidr.flujos_reales_oxido
) src
UNPIVOT (caudal FOR col_name IN (
    parcela_01,parcela_02,parcela_03,parcela_04,parcela_05,parcela_06,parcela_07,parcela_08,
    parcela_09,parcela_10,parcela_11,parcela_12,parcela_13,parcela_14,parcela_15,parcela_16,
    parcela_17,parcela_18,parcela_19,parcela_20,parcela_21,parcela_22,parcela_23,parcela_24,
    parcela_25,parcela_26,parcela_27,parcela_28,parcela_29,parcela_30,parcela_31,parcela_32
)) unpvt
CROSS APPLY (SELECT CAST(RIGHT(col_name,2) AS INT) AS parcela_numero) n;