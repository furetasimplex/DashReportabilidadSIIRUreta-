CREATE VIEW [inventar_SpcHidr].[resumen_mina] AS 
SELECT
   mov_cam.Fecha AS Fecha,
   mov_cam.Turno AS Turno,
   mov_cam.Origen AS Origen,
   mov_cam.Fase AS Fase,
   
   -- Tonelaje
   SUM(mov_cam.Ton) AS Ton,
   
   -- Leyes Ponderadas
   SUM(mov_cam.Ton * mov_cam.CuTG00) / NULLIF(SUM(mov_cam.Ton),0) AS PONDCuTG00,
   SUM(mov_cam.Ton * mov_cam.CusG01) / NULLIF(SUM(mov_cam.Ton),0) AS PONDCusG01,
   SUM(mov_cam.Ton * mov_cam.RS) / NULLIF(SUM(mov_cam.Ton),0) AS PONDRS,
   SUM(mov_cam.Ton * mov_cam.C03G02) / NULLIF(SUM(mov_cam.Ton),0) AS PONDC03G02,
   SUM(mov_cam.Ton * mov_cam.RecLixG03) / NULLIF(SUM(mov_cam.Ton),0) AS PONDRecLixG03,
   
   -- Granulometría Ponderada
   SUM(mov_cam.Ton * mov_cam.[100G07]) / NULLIF(SUM(mov_cam.Ton),0) AS POND100G07,
   
   -- Mineralogía Ponderada
   SUM(mov_cam.Ton * mov_cam.ClayBG10) / NULLIF(SUM(mov_cam.Ton),0) AS PONDClayBG10,
   SUM(mov_cam.Ton * mov_cam.CUFE) / NULLIF(SUM(mov_cam.Ton),0) AS PONDCUFE,
   SUM(mov_cam.Ton * mov_cam.FE) / NULLIF(SUM(mov_cam.Ton),0) AS PONDFE

FROM
   mov_cam
GROUP BY
   mov_cam.Fecha,
   mov_cam.Turno,
   mov_cam.Origen,
   mov_cam.Fase;