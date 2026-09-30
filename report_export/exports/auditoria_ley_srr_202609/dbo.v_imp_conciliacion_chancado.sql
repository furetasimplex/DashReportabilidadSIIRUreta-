CREATE VIEW dbo.test_imp
AS
SELECT id, batch_id, imported_at, date, datetime, origen, acf, ag, sag_tph, alt, [as], au, clay, bclaymusc, bm_tph, bwi, calidad, ci, circuit_tph, co3, conc_ag, conc_as, conc_au, conc_cu, conc_mo, conc_sb, csrcc, csrcpy, csrcuins, csrcuoxi, csrcv, cufe, cus, cut, densidad, fe, hum_estim, lito, m100, 
             mg, minty, minty_corto, mo, musc, py, quar, rec_ag, rec_au, rec_cu, rec_denver_nir_min20_recmass10, rec_denver_nir_min20_recmass11, rec_denver_nir_min20_recmass23, rec_denver_nir_min20_recmass8, rec_denver_nir_min20_recmass9, rec_mo, rec_mx_cu, s2, sb, solub, spi, 
             ugrec, zn, humedad_categ_final, ugt19_v3, yield_stress, magnesio, bwi_nir, ci_nir, spi_nir, nag, np, ph, phnag, ys_cp47_testing, ys_cp49_testing, ys_cp51_testing, ys_cp53_testing, ys_cp55_testing, categoria, rec_denver_nir_min20_recmass12, rec_denver_nir_min20_recmass13, 
             rec_denver_nir_min20_recmass14, rec_denver_nir_min20_recmass15, rec_denver_nir_min20_recmass16, rec_denver_nir_min20_recmass17, rec_denver_nir_min20_recmass18, rec_denver_nir_min20_recmass19, rec_denver_nir_min20_recmass20, rec_denver_nir_min20_recmass21, 
             rec_denver_nir_min20_recmass22, rec_denver_nir_min20_recmass10_fix, banco, pol_index, circuit_tph_cap4583, clusters_ve, minty_corto_calc, csrcc_equ, rec_denver_nir_min20_recmass10_ug, ys_cp51_oficial, ys_cp53_oficial, ys_cp55_oficial, ys_cp57_testing, ys_cp60_testing, 
             ys_cp57_oficial, ys_cp60_oficial, m02, m04, rec_min05, m07, m09, recmass10_fix_tph_4167, recmass10_fix_tph_4250, recmass10_fix_tph_4350, m03, m06, m12, m15, dumpid, tonnage, [from], [to], shovel, loadx, loady, loadz, dumpx, dumpy, dumpz, 
             rec_denver_nir_min20_recmass10_ug_gte_65, recup, pm10_campamento, recup_estimada, ton_sag
FROM   DEV_SIIR.hidro.imp_csv
