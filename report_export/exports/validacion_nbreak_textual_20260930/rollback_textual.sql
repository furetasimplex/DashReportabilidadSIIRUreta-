-- Solo DEV. Revierte exclusivamente la correccion textual; no modifica datos.
IF DB_NAME()<>N'inventar_SpcHidr' THROW 51000, 'Solo DEV.', 1;
SET XACT_ABORT ON;
BEGIN TRANSACTION;
GO
CREATE OR ALTER FUNCTION inventar_SpcHidr.fn_resolver_vueltas_camiones_test
(
 @Reg_MOV int, @Null_MOV int, @Neg_MOV int, @Kom_MOV float, @Cat_MOV float,
 @Reg_BI int, @Null_BI int, @Neg_BI int, @Kom_BI float, @Cat_BI float
)
RETURNS TABLE
AS RETURN
WITH Estados AS (
 SELECT
 CAST(CASE WHEN @Reg_MOV=0 THEN 'SIN_REGISTROS'
           WHEN @Null_MOV>0 THEN 'NBREAK_NULL'
           WHEN @Neg_MOV>0 THEN 'NBREAK_NEGATIVO'
           WHEN @Kom_MOV+@Cat_MOV=0 THEN 'SOLO_CEROS'
           WHEN @Kom_MOV+@Cat_MOV>0 THEN 'OK'
           ELSE 'NBREAK_NULL' END AS varchar(24)) Estado_Fuente_MOV_CAM,
 CAST(CASE WHEN @Reg_BI=0 THEN 'SIN_REGISTROS'
           WHEN @Null_BI>0 THEN 'NBREAK_NULL'
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

GO
CREATE OR ALTER VIEW inventar_SpcHidr.v_vueltas_camiones_diarias_test
AS
WITH Movimientos AS (
 SELECT CAST(Fecha AS date) Fecha,'MOV_CAM' Fuente,
        UPPER(LTRIM(RTRIM(Flota_CEX))) Flota,TRY_CONVERT(float,N_BREAK) Vueltas
 FROM inventar_SpcHidr.mov_cam
 WHERE UPPER(LTRIM(RTRIM(Destino)))='CH01'
   AND UPPER(LTRIM(RTRIM(Fase)))<>'SRR'
   AND UPPER(LTRIM(RTRIM(Flota_CEX))) IN ('KOM','CAT')
 UNION ALL
 SELECT CAST(fecha AS date),'MOV_CAM_POWERBI',
        UPPER(LTRIM(RTRIM(flota_cex_tc))),TRY_CONVERT(float,n_break)
 FROM inventar_SpcHidr.mov_cam_powerbi
 WHERE UPPER(LTRIM(RTRIM(destino_descarga)))='CH01'
   AND UPPER(LTRIM(RTRIM(fase)))<>'SRR'
   AND UPPER(LTRIM(RTRIM(flota_cex_tc))) IN ('KOM','CAT')
), Totales AS (
 SELECT Fecha,Fuente,COUNT(*) Registros,
        SUM(CASE WHEN Vueltas IS NULL THEN 1 ELSE 0 END) Nulos,
        SUM(CASE WHEN Vueltas<0 THEN 1 ELSE 0 END) Negativos,
        SUM(CASE WHEN Flota='KOM' THEN Vueltas ELSE 0.0 END) KOM,
        SUM(CASE WHEN Flota='CAT' THEN Vueltas ELSE 0.0 END) CAT
 FROM Movimientos GROUP BY Fecha,Fuente
), Dias AS (SELECT DISTINCT Fecha FROM Totales)
SELECT d.Fecha,r.*,
       COALESCE(m.Registros,0)+COALESCE(p.Registros,0) Cantidad_Registros_Originales,
       m.KOM Vueltas_KOM_MOV_CAM,m.CAT Vueltas_CAT_MOV_CAM,
       p.KOM Vueltas_KOM_POWERBI,p.CAT Vueltas_CAT_POWERBI
FROM Dias d
LEFT JOIN Totales m ON m.Fecha=d.Fecha AND m.Fuente='MOV_CAM'
LEFT JOIN Totales p ON p.Fecha=d.Fecha AND p.Fuente='MOV_CAM_POWERBI'
CROSS APPLY inventar_SpcHidr.fn_resolver_vueltas_camiones_test
 (COALESCE(m.Registros,0),m.Nulos,m.Negativos,m.KOM,m.CAT,
  COALESCE(p.Registros,0),p.Nulos,p.Negativos,p.KOM,p.CAT) r;

GO
COMMIT;
