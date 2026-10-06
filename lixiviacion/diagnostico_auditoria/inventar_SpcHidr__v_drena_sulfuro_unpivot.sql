CREATE VIEW inventar_SpcHidr.v_drena_sulfuro_unpivot AS
SELECT id_registro, fecha_registro, parcela_numero, cu_pp
FROM (
    SELECT id_registro, fecha_registro,
        p1_cu_pp,p2_cu_pp,p3_cu_pp,p4_cu_pp,p5_cu_pp,p6_cu_pp,p7_cu_pp,p8_cu_pp,
        p9_cu_pp,p10_cu_pp,p11_cu_pp,p12_cu_pp,p13_cu_pp,p14_cu_pp,p15_cu_pp,p16_cu_pp,
        p17_cu_pp,p18_cu_pp,p19_cu_pp,p20_cu_pp,p21_cu_pp,p22_cu_pp,p23_cu_pp,p24_cu_pp,
        p25_cu_pp,p26_cu_pp,p27_cu_pp,p28_cu_pp
    FROM inventar_SpcHidr.drena_concentrados_sulfuro
) src
UNPIVOT (cu_pp FOR col_name IN (
    p1_cu_pp,p2_cu_pp,p3_cu_pp,p4_cu_pp,p5_cu_pp,p6_cu_pp,p7_cu_pp,p8_cu_pp,
    p9_cu_pp,p10_cu_pp,p11_cu_pp,p12_cu_pp,p13_cu_pp,p14_cu_pp,p15_cu_pp,p16_cu_pp,
    p17_cu_pp,p18_cu_pp,p19_cu_pp,p20_cu_pp,p21_cu_pp,p22_cu_pp,p23_cu_pp,p24_cu_pp,
    p25_cu_pp,p26_cu_pp,p27_cu_pp,p28_cu_pp
)) unpvt
CROSS APPLY (SELECT CAST(SUBSTRING(col_name,2,CHARINDEX('_',col_name,2)-2) AS INT) AS parcela_numero) n;