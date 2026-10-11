CREATE OR ALTER FUNCTION inventar_SpcHidr.fn_resolver_vueltas_camiones_test
(
 @Reg_MOV int, @Null_MOV int, @Neg_MOV int, @Kom_MOV float, @Cat_MOV float,
 @Reg_BI int, @Null_BI int, @Neg_BI int, @Kom_BI float, @Cat_BI float,
 @NoNum_MOV int = 0, @NoNum_BI int = 0
)
RETURNS TABLE
AS RETURN
WITH Estados AS (
 SELECT
 CAST(CASE WHEN @Reg_MOV=0 THEN 'SIN_REGISTROS'
           WHEN @Null_MOV>0 THEN 'NBREAK_NULL'
           WHEN @NoNum_MOV>0 THEN 'NBREAK_NO_NUMERICO'
           WHEN @Neg_MOV>0 THEN 'NBREAK_NEGATIVO'
           WHEN @Kom_MOV+@Cat_MOV=0 THEN 'SOLO_CEROS'
           WHEN @Kom_MOV+@Cat_MOV>0 THEN 'OK'
           ELSE 'NBREAK_NULL' END AS varchar(24)) Estado_Fuente_MOV_CAM,
 CAST(CASE WHEN @Reg_BI=0 THEN 'SIN_REGISTROS'
           WHEN @Null_BI>0 THEN 'NBREAK_NULL'
           WHEN @NoNum_BI>0 THEN 'NBREAK_NO_NUMERICO'
           WHEN @Neg_BI>0 THEN 'NBREAK_NEGATIVO'
           WHEN @Kom_BI+@Cat_BI=0 THEN 'SOLO_CEROS'
           WHEN @Kom_BI+@Cat_BI>0 THEN 'OK'
           ELSE 'NBREAK_NULL' END AS varchar(24)) Estado_Fuente_POWERBI
)
SELECT *,
 CAST(CASE WHEN Estado_Fuente_MOV_CAM='OK' THEN 'MOV_CAM'
           WHEN Estado_Fuente_POWERBI='OK' THEN 'MOV_CAM_POWERBI'
           ELSE 'SIN_DATOS_CAMIONES' END AS varchar(100)) Fuente_Camiones,
 CASE WHEN Estado_Fuente_MOV_CAM='OK' THEN @Kom_MOV
      WHEN Estado_Fuente_POWERBI='OK' THEN @Kom_BI ELSE 0.0 END Vueltas_KOM,
 CASE WHEN Estado_Fuente_MOV_CAM='OK' THEN @Cat_MOV
      WHEN Estado_Fuente_POWERBI='OK' THEN @Cat_BI ELSE 0.0 END Vueltas_CAT,
 CASE WHEN Estado_Fuente_MOV_CAM='OK' THEN @Reg_MOV
      WHEN Estado_Fuente_POWERBI='OK' THEN @Reg_BI ELSE 0 END Cantidad_Registros_Validos
FROM Estados;
