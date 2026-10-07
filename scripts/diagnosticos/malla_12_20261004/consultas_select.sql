/* DEV inventar_SpcHidr. Solo SELECT y metadatos. No ejecutar SP. */
SELECT @@SERVERNAME AS servidor, DB_NAME() AS base, SYSDATETIME() AS observado;

/* Emisión que lee la exportación oficial de Análisis TM en este checkout. */
SELECT Fecha, Turno, Malla_Menos_1_2_Real, Apilado_TMS_Real,
       Muestra_Fisica, Fuente_Info_Fisica, Fecha_Actualizacion
FROM inventar_SpcHidr.reporte_turno_cache_emision_test
WHERE Fecha = '2026-10-04' AND Turno IN ('A','B')
ORDER BY Turno;

/* Representatividad física: peso, denominador y factores. */
SELECT Dia, TM1_TurnoA_Fisico, TM2_TurnoA_Fisico,
       TM1_TurnoB_Fisico, TM2_TurnoB_Fisico
FROM inventar_SpcHidr.v_representatividad_diaria_calculada
WHERE Dia IN ('2026-10-03','2026-10-04');
SELECT Fecha,Turno,Torre,PesoReal_Fisico,nombre_archivo,fecha_carga
FROM inventar_SpcHidr.v_peso_real_torre_turno_excel
WHERE Fecha IN ('2026-10-03','2026-10-04') AND Torre IN ('T1','T2');
SELECT Fecha,Turno,Torre,Horas_Reales,Factor_Masa,ts_ini,ts_fin,
       PesoBase_Fisico_12h,Fraccion_Muestreo,PesoTeo_Fisico
FROM inventar_SpcHidr.v_peso_teorico_turno_torre_excel
WHERE Fecha IN ('2026-10-03','2026-10-04') AND Torre IN ('T1','T2');

/* Laboratorio crudo, con fecha de carga. */
SELECT Fecha,Turno,Torre,Pasante_1_2P,Fecha_Carga,ID_Registro
FROM inventar_SpcHidr.Informe_TM_lab
WHERE (Fecha='2026-10-04' AND Torre IN ('T1','T2'))
   OR (Fecha='2026-10-03' AND Turno='B' AND Torre='T2')
   OR (Fecha='2026-09-28' AND Turno='B' AND Torre='T2')
ORDER BY Fecha,Turno,Torre;

/* Validación y base consumida por el SP de emisión vigente. */
SELECT Fecha,Turno,TM,Representatividad_TM,
       Malla_Menos_1_2,Fuente_Malla_Menos_1_2
FROM inventar_SpcHidr.v_leyes_validadas_tm_turno
WHERE Fecha='2026-10-04'
ORDER BY Turno,TM;
SELECT Fecha,Turno,TM,Malla_Menos_1_2,Fuente_Malla_Menos_1_2
FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
WHERE Fecha='2026-10-04'
ORDER BY Turno,TM;
SELECT TOP (8) Fecha,Turno,TM,Malla_Menos_1_2,Fuente_Malla_Menos_1_2
FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
WHERE Fecha<='2026-10-04' AND TM='TM2'
  AND Fuente_Malla_Menos_1_2 IN ('TORRE_MISMO_TURNO','SEMILLA_INICIO_PERIODO')
  AND Malla_Menos_1_2<>0
ORDER BY Fecha DESC,Turno DESC;

/* Bases de ponderación. El SP resta Sal proporcionalmente a cada TM. */
SELECT Fecha,TMH_CV008_A,TMH_CV008_B,TMH_CV108_A,TMH_CV108_B
FROM inventar_SpcHidr.v_datos_apilado_tmh_v2 WHERE Fecha='2026-10-04';
SELECT Fecha,Sal_Ajustada_TA,Sal_Ajustada_TB
FROM inventar_SpcHidr.v_sal_ajustada WHERE Fecha='2026-10-04';
SELECT Fecha,Factor_Aplicacion_Reportes
FROM inventar_SpcHidr.v_ajuste_camiones_emision_test WHERE Fecha='2026-10-04';

/* Definiciones actuales. El sufijo _test no implica ruta no oficial. */
SELECT o.name,o.type_desc,o.modify_date,OBJECT_DEFINITION(o.object_id) AS definicion
FROM sys.objects o
WHERE o.object_id IN (
    OBJECT_ID('inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test'),
    OBJECT_ID('inventar_SpcHidr.sp_reporte_turno_emision_test'),
    OBJECT_ID('inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test'),
    OBJECT_ID('inventar_SpcHidr.v_leyes_validadas_tm_turno'),
    OBJECT_ID('inventar_SpcHidr.v_validacion_leyes_tm1_v2'),
    OBJECT_ID('inventar_SpcHidr.v_validacion_leyes_tm2_v2'));
