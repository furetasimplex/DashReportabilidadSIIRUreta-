CREATE VIEW inventar_SpcHidr.vw_drena_concentrados_sulfuro_long_operacional
AS
SELECT
    d.id_registro,

    CASE
        WHEN d.fecha_registro >= '2026-06-01T21:00:00'
         AND DATEPART(HOUR, d.fecha_registro) >= 20
        THEN DATEADD(
                DAY,
                1,
                CAST(d.fecha_registro AS date)
             )
        ELSE CAST(d.fecha_registro AS date)
    END AS fecha,

    d.fecha_registro,

    v.nro_parcela_pad,

    CAST(v.cu_pp AS decimal(12,2)) AS cu_pp,
    CAST(v.h_p  AS decimal(12,2)) AS h_p,
    CAST(v.ph   AS decimal(12,2)) AS ph,
    CAST(v.cl   AS decimal(12,2)) AS cl,
    CAST(v.fet  AS decimal(12,2)) AS fet,
    CAST(v.fe2  AS decimal(12,2)) AS fe2,
    CAST(v.eh   AS decimal(12,2)) AS eh

FROM inventar_SpcHidr.drena_concentrados_sulfuro d

CROSS APPLY (VALUES
    (1 , d.p1_cu_pp , d.p1_h_p , d.p1_ph , d.p1_cl , d.p1_fet , d.p1_fe2 , d.p1_eh),
    (2 , d.p2_cu_pp , d.p2_h_p , d.p2_ph , d.p2_cl , d.p2_fet , d.p2_fe2 , d.p2_eh),
    (3 , d.p3_cu_pp , d.p3_h_p , d.p3_ph , d.p3_cl , d.p3_fet , d.p3_fe2 , d.p3_eh),
    (4 , d.p4_cu_pp , d.p4_h_p , d.p4_ph , d.p4_cl , d.p4_fet , d.p4_fe2 , d.p4_eh),
    (5 , d.p5_cu_pp , d.p5_h_p , d.p5_ph , d.p5_cl , d.p5_fet , d.p5_fe2 , d.p5_eh),
    (6 , d.p6_cu_pp , d.p6_h_p , d.p6_ph , d.p6_cl , d.p6_fet , d.p6_fe2 , d.p6_eh),
    (7 , d.p7_cu_pp , d.p7_h_p , d.p7_ph , d.p7_cl , d.p7_fet , d.p7_fe2 , d.p7_eh),
    (8 , d.p8_cu_pp , d.p8_h_p , d.p8_ph , d.p8_cl , d.p8_fet , d.p8_fe2 , d.p8_eh),
    (9 , d.p9_cu_pp , d.p9_h_p , d.p9_ph , d.p9_cl , d.p9_fet , d.p9_fe2 , d.p9_eh),
    (10, d.p10_cu_pp, d.p10_h_p, d.p10_ph, d.p10_cl, d.p10_fet, d.p10_fe2, d.p10_eh),
    (11, d.p11_cu_pp, d.p11_h_p, d.p11_ph, d.p11_cl, d.p11_fet, d.p11_fe2, d.p11_eh),
    (12, d.p12_cu_pp, d.p12_h_p, d.p12_ph, d.p12_cl, d.p12_fet, d.p12_fe2, d.p12_eh),
    (13, d.p13_cu_pp, d.p13_h_p, d.p13_ph, d.p13_cl, d.p13_fet, d.p13_fe2, d.p13_eh),
    (14, d.p14_cu_pp, d.p14_h_p, d.p14_ph, d.p14_cl, d.p14_fet, d.p14_fe2, d.p14_eh),
    (15, d.p15_cu_pp, d.p15_h_p, d.p15_ph, d.p15_cl, d.p15_fet, d.p15_fe2, d.p15_eh),
    (16, d.p16_cu_pp, d.p16_h_p, d.p16_ph, d.p16_cl, d.p16_fet, d.p16_fe2, d.p16_eh),
    (17, d.p17_cu_pp, d.p17_h_p, d.p17_ph, d.p17_cl, d.p17_fet, d.p17_fe2, d.p17_eh),
    (18, d.p18_cu_pp, d.p18_h_p, d.p18_ph, d.p18_cl, d.p18_fet, d.p18_fe2, d.p18_eh),
    (19, d.p19_cu_pp, d.p19_h_p, d.p19_ph, d.p19_cl, d.p19_fet, d.p19_fe2, d.p19_eh),
    (20, d.p20_cu_pp, d.p20_h_p, d.p20_ph, d.p20_cl, d.p20_fet, d.p20_fe2, d.p20_eh),
    (21, d.p21_cu_pp, d.p21_h_p, d.p21_ph, d.p21_cl, d.p21_fet, d.p21_fe2, d.p21_eh),
    (22, d.p22_cu_pp, d.p22_h_p, d.p22_ph, d.p22_cl, d.p22_fet, d.p22_fe2, d.p22_eh),
    (23, d.p23_cu_pp, d.p23_h_p, d.p23_ph, d.p23_cl, d.p23_fet, d.p23_fe2, d.p23_eh),
    (24, d.p24_cu_pp, d.p24_h_p, d.p24_ph, d.p24_cl, d.p24_fet, d.p24_fe2, d.p24_eh),
    (25, d.p25_cu_pp, d.p25_h_p, d.p25_ph, d.p25_cl, d.p25_fet, d.p25_fe2, d.p25_eh),
    (26, d.p26_cu_pp, d.p26_h_p, d.p26_ph, d.p26_cl, d.p26_fet, d.p26_fe2, d.p26_eh),
    (27, d.p27_cu_pp, d.p27_h_p, d.p27_ph, d.p27_cl, d.p27_fet, d.p27_fe2, d.p27_eh),
    (28, d.p28_cu_pp, d.p28_h_p, d.p28_ph, d.p28_cl, d.p28_fet, d.p28_fe2, d.p28_eh),
    (29, d.p29_cu_pp, d.p29_h_p, d.p29_ph, d.p29_cl, d.p29_fet, d.p29_fe2, d.p29_eh),
    (30, d.p30_cu_pp, d.p30_h_p, d.p30_ph, d.p30_cl, d.p30_fet, d.p30_fe2, d.p30_eh),
    (31, d.p31_cu_pp, d.p31_h_p, d.p31_ph, d.p31_cl, d.p31_fet, d.p31_fe2, d.p31_eh),
    (32, d.p32_cu_pp, d.p32_h_p, d.p32_ph, d.p32_cl, d.p32_fet, d.p32_fe2, d.p32_eh)
) v
(
    nro_parcela_pad,
    cu_pp,
    h_p,
    ph,
    cl,
    fet,
    fe2,
    eh
);
