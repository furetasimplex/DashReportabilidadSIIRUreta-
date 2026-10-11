CREATE OR ALTER VIEW inventar_SpcHidr.v_vueltas_camiones_diarias_test
AS
WITH Movimientos AS (
 SELECT CAST(Fecha AS date) Fecha,'MOV_CAM' Fuente,
        UPPER(LTRIM(RTRIM(Flota_CEX))) Flota,TRY_CONVERT(float,N_BREAK) Vueltas,
        CASE WHEN N_BREAK IS NULL THEN 1 ELSE 0 END NuloReal,
        0 NoNumerico
 FROM inventar_SpcHidr.mov_cam
 WHERE UPPER(LTRIM(RTRIM(Destino)))='CH01'
   AND UPPER(LTRIM(RTRIM(Fase)))<>'SRR'
   AND UPPER(LTRIM(RTRIM(Flota_CEX))) IN ('KOM','CAT')
 UNION ALL
 SELECT CAST(fecha AS date),'MOV_CAM_POWERBI',
        UPPER(LTRIM(RTRIM(flota_cex_tc))),TRY_CONVERT(float,NULLIF(LTRIM(RTRIM(n_break)),N'')),
        CASE WHEN n_break IS NULL THEN 1 ELSE 0 END,
        CASE WHEN n_break IS NOT NULL AND
             TRY_CONVERT(float,NULLIF(LTRIM(RTRIM(n_break)),N'')) IS NULL
             THEN 1 ELSE 0 END
 FROM inventar_SpcHidr.mov_cam_powerbi
 WHERE UPPER(LTRIM(RTRIM(destino_descarga)))='CH01'
   AND UPPER(LTRIM(RTRIM(fase)))<>'SRR'
   AND UPPER(LTRIM(RTRIM(flota_cex_tc))) IN ('KOM','CAT')
), Totales AS (
 SELECT Fecha,Fuente,COUNT(*) Registros,
        SUM(NuloReal) Nulos,
        SUM(NoNumerico) NoNumericos,
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
  COALESCE(p.Registros,0),p.Nulos,p.Negativos,p.KOM,p.CAT,m.NoNumericos,p.NoNumericos) r;
