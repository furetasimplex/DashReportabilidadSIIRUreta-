-- Consultas de diagnóstico; solo lectura. Ejecutar en DEV inventar_SpcHidr.
SELECT @@SERVERNAME AS servidor, DB_NAME() AS base;

-- La clave de MOV_CAM usa TA/TB; la vista de conciliación la normaliza a A/B.
SELECT CAST(Fecha AS date) AS Fecha, Turno, COUNT(*) AS registros,
       SUM(Ton) AS Ton,
       SUM(Ton*CuTG00)/NULLIF(SUM(Ton),0) AS CuT,
       SUM(Ton*CusG01)/NULLIF(SUM(Ton),0) AS CuS,
       SUM(Ton*CUFE)/NULLIF(SUM(Ton),0) AS CuFe,
       SUM(Ton*C03G02)/NULLIF(SUM(Ton),0) AS CO3,
       SUM(Ton*[100G07])/NULLIF(SUM(Ton),0) AS Malla100,
       SUM(Ton*ClayBG10)/NULLIF(SUM(Ton),0) AS ClayBeta
FROM inventar_SpcHidr.mov_cam
WHERE CAST(Fecha AS date) BETWEEN '2026-09-19' AND '2026-09-21'
GROUP BY CAST(Fecha AS date), Turno ORDER BY Fecha, Turno;

SELECT CAST(fecha AS date) AS Fecha, turno AS Turno, COUNT(*) AS registros,
       SUM(TRY_CONVERT(float,tonelaje_descarga_tms)) AS Ton
FROM inventar_SpcHidr.mov_cam_powerbi
WHERE CAST(fecha AS date) BETWEEN '2026-09-19' AND '2026-09-21'
GROUP BY CAST(fecha AS date), turno ORDER BY Fecha, Turno;

SELECT Fecha, Turno, Origen, Fase, Ton, PONDCuTG00, PONDCusG01,
       PONDCUFE, PONDC03G02, POND100G07, PONDClayBG10
FROM inventar_SpcHidr.resumen_mina
WHERE CAST(Fecha AS date) BETWEEN '2026-09-19' AND '2026-09-21'
ORDER BY Fecha, Turno, Origen, Fase;

SELECT Fecha,Turno,Ton,CuT,CuS,CuFe,CO3,Malla100,Clay_Beta,Caolinita
FROM DEV_SIIR.hidro.v_imp_conciliacion_chancado
WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno;

SELECT Fecha,Turno,Ton,CuT,CuS,CuFe,CO3,Malla100,Clay_Beta,Caolinita,Fuente_Dato
FROM inventar_SpcHidr.v_conciliacion_chancado_v2
WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno;

SELECT Fecha,Turno,TM,CuT,Fuente_CuT,CuS,Fuente_CuS,CO3,Fuente_CO3,
       CuFe,Fuente_CuFe,Malla_Menos_100,Fuente_Malla_Menos_100,CaolBeta,Fuente_CaolBeta
FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test
WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno,TM;

SELECT Fecha,Turno,CuT_Real,CuS_Real,CO3_Real,CuFe_Real,
       Malla_Menos_100_Real,CaolBeta_Real,
       Fuente_Info_Quimica,Fuente_Info_Fisica,Fecha_Actualizacion
FROM inventar_SpcHidr.reporte_turno_cache_emision_test
WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21' ORDER BY Fecha,Turno;

SELECT Fecha,Turno,TM_Destino,Analito,Valor_Final,Fuente_Base,
       Fuente_Tecnica,Resolucion,Fecha_Proceso
FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
WHERE Fecha BETWEEN '2026-09-19' AND '2026-09-21'
  AND Analito IN ('CuT','CuS','CuFe','CO3','Malla_Menos_100','CaolBeta')
ORDER BY Fecha,Turno,TM_Destino,Analito;

SELECT Fecha,CuT_Real_Dia,CuS_Real_Dia,CO3_Real_Dia,
       CuFe_Real_Dia,Malla_Menos_100_Real_Dia,CaolBeta_Real_Dia
FROM inventar_SpcHidr.fn_generador_reporte_diario_emision_test('2026-09-19','2026-09-22')
ORDER BY Fecha;

SELECT SCHEMA_NAME(o.schema_id) AS esquema,o.name,o.modify_date,m.definition
FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
WHERE o.name IN ('resumen_mina','v_conciliacion_chancado_v2',
 'v_validacion_leyes_tm1_v2','v_validacion_leyes_tm2_v2',
 'v_leyes_validadas_tm_turno','v_leyes_resueltas_data_tm_reporte_test',
 'sp_reporte_turno_emision_test','sp_actualizar_reporte_turno_cache_emision_test',
 'fn_generador_reporte_diario_emision_test');
