-- READ ONLY, NO EJECUTADO. TEST V4 funcional VALIDADO LIVE; candidato local no equiparado al contrato LIVE33.
-- Los mismos CTE de 01 son generados desde generar_candidato.py, sin placeholders.
-- Ejecutar futuro manualmente sobre corte estable; no presupone snapshot isolation.
-- EXCEPT compara NULL sin rellenar cero, pero elimina duplicados: revisar 01/02/04.
-- Si V2 solo existe en ensayo de 01, ejecutar aqui EN LA MISMA SESION antes de rollback.
SET NOCOUNT ON;
IF OBJECT_ID(N'inventar_SpcHidr.vw_tablero_lixiviacion_final_v2',N'V') IS NULL
 THROW 51300,'No existe V2 visible para validar.',1;
DECLARE @ctes nvarchar(max)=N'WITH flujo AS (
 -- Fuente/grano aprobados como DISENO; conservacion TEST V4 VALIDADO LIVE segun usuario; equivalencia local pendiente.
 SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM inventar_SpcHidr.vw_flujos_reales_oxido_long
 UNION ALL
 SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM inventar_SpcHidr.vw_flujos_reales_sulfuro_long
), drenaje_raw AS (
 -- VALIDADO LIVE (evidencia usuario 04/10): fecha operacional, PAD y siete analitos.
 -- Se normaliza desde timestamp RAW; nunca desde s.fecha ya normalizada.
 -- Los casts decimal(12,2) pertenecen a *_long y no se agregan ni cambian aqui.
SELECT 1 AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 CASE WHEN s.fecha_registro >= ''2026-06-01T21:00:00'' AND DATEPART(HOUR,s.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST(s.fecha_registro AS date)) ELSE CAST(s.fecha_registro AS date) END AS fecha,s.nro_parcela_pad,
 s.cu_pp,s.h_p,s.ph,s.cl,s.fet,s.fe2,s.eh
 FROM inventar_SpcHidr.vw_drena_concentrados_oxido_long s
 UNION ALL
SELECT 2 AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 CASE WHEN s.fecha_registro >= ''2026-06-01T21:00:00'' AND DATEPART(HOUR,s.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST(s.fecha_registro AS date)) ELSE CAST(s.fecha_registro AS date) END AS fecha,s.nro_parcela_pad,
 s.cu_pp,s.h_p,s.ph,s.cl,s.fet,s.fe2,s.eh
 FROM inventar_SpcHidr.vw_drena_concentrados_sulfuro_long s
), drenaje AS (
 SELECT d.*,p.id_parcela AS parcela_id
 FROM drenaje_raw d LEFT JOIN inventar_SpcHidr.parcela p
 ON p.numero=d.nro_parcela_pad AND p.id_pad=d.pad_id
 -- P29-P32 SULF permanecen en fuente. Sin flujo fisico no crean filas V2.
 -- JOIN TEST V4 VALIDADO LIVE; equivalencia de este candidato local pendiente.
), refino AS (
 -- VALIDADO LIVE: regla operacional y PAD 1/2. Sin nuevos casts quimicos.
 -- Composicion inline equivalente a los fragmentos conceptuales aportados;
 -- no supone publicacion de nuevas vistas operacionales ni altera vistas base.
SELECT 1 AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 CASE WHEN s.fecha_registro >= ''2026-06-01T21:00:00'' AND DATEPART(HOUR,s.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST(s.fecha_registro AS date)) ELSE CAST(s.fecha_registro AS date) END AS fecha,
 s.cu_pp,s.h_p,s.ph,s.cl,s.fet,s.fe2,s.eh
 FROM inventar_SpcHidr.vw_riego_oxido_refino_base s
 UNION ALL
SELECT 2 AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 CASE WHEN s.fecha_registro >= ''2026-06-01T21:00:00'' AND DATEPART(HOUR,s.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST(s.fecha_registro AS date)) ELSE CAST(s.fecha_registro AS date) END AS fecha,
 s.cu_pp,s.h_p,s.ph,s.cl,s.fet,s.fe2,s.eh
 FROM inventar_SpcHidr.vw_riego_sulfuro_refino_base s
), campana_parcela_base AS (
 -- VALIDADO LIVE: SOLO preagregacion hidraulica. No agrega TMS/leyes/modulos.
 SELECT c.pad_id,c.campana_id,c.numero_campana,c.parcela_id,
 MIN(c.fecha_primer_riego) AS fecha_primer_riego,
 MAX(c.fecha_ultimo_riego) AS fecha_ultimo_riego
 FROM inventar_SpcHidr.campana_parcela_control c
 GROUP BY c.pad_id,c.campana_id,c.numero_campana,c.parcela_id
), campana_parcela_orden AS (
 SELECT c.*,LEAD(c.fecha_primer_riego) OVER (
 PARTITION BY c.pad_id,c.parcela_id ORDER BY c.fecha_primer_riego,c.campana_id
 ) AS siguiente_primer_riego FROM campana_parcela_base c
), campana_parcela AS (
 SELECT c.*,CASE
 WHEN c.fecha_ultimo_riego IS NULL THEN NULL
 WHEN c.siguiente_primer_riego IS NULL THEN c.fecha_ultimo_riego
 WHEN c.fecha_ultimo_riego < DATEADD(DAY,-1,c.siguiente_primer_riego) THEN c.fecha_ultimo_riego
 ELSE DATEADD(DAY,-1,c.siguiente_primer_riego)
 END AS fecha_limite_hidraulica FROM campana_parcela_orden c
),v AS (SELECT * FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2) ';
DECLARE @sql nvarchar(max);

-- 01. Claves NULL/duplicadas FUENTE (cero filas esperado)
SET @sql=@ctes+N'SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) AS filas FROM flujo
GROUP BY pad_id,parcela_id,fecha HAVING COUNT_BIG(*)>1 OR pad_id IS NULL OR parcela_id IS NULL OR fecha IS NULL;';
EXEC sys.sp_executesql @sql;

-- 02. Claves NULL/duplicadas V2 (cero filas)
SET @sql=@ctes+N'SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) AS filas FROM v
GROUP BY pad_id,parcela_id,fecha HAVING COUNT_BIG(*)>1 OR pad_id IS NULL OR parcela_id IS NULL OR fecha IS NULL;';
EXEC sys.sp_executesql @sql;

-- 03. Conservacion EXACTA flujo menos v (cero filas; combinar unicidad/conteos)
SET @sql=@ctes+N'SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM flujo
EXCEPT SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM v;';
EXEC sys.sp_executesql @sql;

-- 03. Conservacion EXACTA v menos flujo (cero filas; combinar unicidad/conteos)
SET @sql=@ctes+N'SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM v
EXCEPT SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM flujo;';
EXEC sys.sp_executesql @sql;

-- 04. Cobertura por PAD/fecha (informativo; comparar pares)
SET @sql=@ctes+N'SELECT ''FUENTE'' AS origen,pad_id,fecha,COUNT_BIG(*) AS filas,COUNT(flujo_m3_d) AS no_null,SUM(flujo_m3_d) AS m3 FROM flujo GROUP BY pad_id,fecha
UNION ALL SELECT ''V2'',pad_id,fecha,COUNT_BIG(*),COUNT(flujo_m3_d),SUM(flujo_m3_d) FROM v GROUP BY pad_id,fecha ORDER BY pad_id,fecha,origen;';
EXEC sys.sp_executesql @sql;

-- 05. Drenaje raw por PAD/numero/fecha (cero duplicados)
SET @sql=@ctes+N'SELECT pad_id,nro_parcela_pad,fecha,COUNT_BIG(*) AS filas FROM drenaje_raw
GROUP BY pad_id,nro_parcela_pad,fecha HAVING COUNT_BIG(*)>1 OR fecha IS NULL;';
EXEC sys.sp_executesql @sql;

-- 06. Refino PAD/fecha (cero duplicados)
SET @sql=@ctes+N'SELECT pad_id,fecha,COUNT_BIG(*) AS filas FROM refino GROUP BY pad_id,fecha HAVING COUNT_BIG(*)>1 OR fecha IS NULL;';
EXEC sys.sp_executesql @sql;

-- 07. Dimension parcela: unicidad PAD/numero (cero filas)
SET @sql=@ctes+N'SELECT id_pad,numero,COUNT_BIG(*) AS filas FROM inventar_SpcHidr.parcela
WHERE id_pad IN (1,2) GROUP BY id_pad,numero HAVING COUNT_BIG(*)>1;';
EXEC sys.sp_executesql @sql;

-- 08. Drenaje sin dimension (informativo: distinguir historicos SULF29-32, no remapear)
SET @sql=@ctes+N'SELECT pad_id,nro_parcela_pad,COUNT_BIG(*) AS filas FROM drenaje WHERE parcela_id IS NULL GROUP BY pad_id,nro_parcela_pad;';
EXEC sys.sp_executesql @sql;

-- 09. Coincidencias drenaje despues de JOIN fisico (cero multiplicidad)
SET @sql=@ctes+N'SELECT f.pad_id,f.parcela_id,f.fecha,COUNT_BIG(*) AS coincidencias FROM flujo f
JOIN drenaje d ON d.pad_id=f.pad_id AND d.parcela_id=f.parcela_id AND d.fecha=f.fecha
GROUP BY f.pad_id,f.parcela_id,f.fecha HAVING COUNT_BIG(*)>1;';
EXEC sys.sp_executesql @sql;

-- 09. Coincidencias refino despues de JOIN fisico (cero multiplicidad)
SET @sql=@ctes+N'SELECT f.pad_id,f.parcela_id,f.fecha,COUNT_BIG(*) AS coincidencias FROM flujo f
JOIN refino d ON d.pad_id=f.pad_id AND d.fecha=f.fecha
GROUP BY f.pad_id,f.parcela_id,f.fecha HAVING COUNT_BIG(*)>1;';
EXEC sys.sp_executesql @sql;

-- 10. Campanas por clave: contar coincidencias, no esconder con DISTINCT (cero >1)
SET @sql=@ctes+N'SELECT f.pad_id,f.parcela_id,f.fecha,COUNT_BIG(*) AS coincidencias
FROM flujo f JOIN campana_parcela c ON c.pad_id=f.pad_id AND c.parcela_id=f.parcela_id
AND f.fecha>=c.fecha_primer_riego AND f.fecha<=c.fecha_limite_hidraulica
GROUP BY f.pad_id,f.parcela_id,f.fecha HAVING COUNT_BIG(*)>1;';
EXEC sys.sp_executesql @sql;

-- 11. Conservacion filas fuera de ventana (cero filas)
SET @sql=@ctes+N'SELECT f.* FROM flujo f WHERE NOT EXISTS (
SELECT 1 FROM campana_parcela c WHERE c.pad_id=f.pad_id AND c.parcela_id=f.parcela_id
AND f.fecha>=c.fecha_primer_riego AND f.fecha<=c.fecha_limite_hidraulica)
AND NOT EXISTS (SELECT 1 FROM v WHERE v.pad_id=f.pad_id AND v.parcela_id=f.parcela_id AND v.fecha=f.fecha
AND v.campana_id IS NULL AND v.numero_campana IS NULL AND v.estado_asignacion=''FUERA_VENTANA_RIEGO'');';
EXEC sys.sp_executesql @sql;

-- 12. Campana/numero/estado esperado menos V2 (cero filas)
SET @sql=@ctes+N'SELECT f.pad_id,f.parcela_id,f.fecha,c.campana_id,c.numero_campana,
CASE WHEN c.campana_id IS NULL THEN ''FUERA_VENTANA_RIEGO'' ELSE ''CAMPANA_HIDRAULICA'' END AS estado_asignacion
FROM flujo f LEFT JOIN campana_parcela c ON c.pad_id=f.pad_id AND c.parcela_id=f.parcela_id
AND f.fecha>=c.fecha_primer_riego AND f.fecha<=c.fecha_limite_hidraulica
EXCEPT SELECT pad_id,parcela_id,fecha,campana_id,numero_campana,estado_asignacion FROM v;';
EXEC sys.sp_executesql @sql;

-- 13. V2 menos campana/numero/estado esperado (cero filas)
SET @sql=@ctes+N'SELECT pad_id,parcela_id,fecha,campana_id,numero_campana,estado_asignacion FROM v
EXCEPT SELECT f.pad_id,f.parcela_id,f.fecha,c.campana_id,c.numero_campana,
CASE WHEN c.campana_id IS NULL THEN ''FUERA_VENTANA_RIEGO'' ELSE ''CAMPANA_HIDRAULICA'' END AS estado_asignacion
FROM flujo f LEFT JOIN campana_parcela c ON c.pad_id=f.pad_id AND c.parcela_id=f.parcela_id
AND f.fecha>=c.fecha_primer_riego AND f.fecha<=c.fecha_limite_hidraulica;';
EXEC sys.sp_executesql @sql;

-- 14. Cu de fuentes menos V2 (cero filas)
SET @sql=@ctes+N'SELECT f.pad_id,f.parcela_id,f.fecha,d.cu_pp,r.cu_pp FROM flujo f
LEFT JOIN drenaje d ON d.pad_id=f.pad_id AND d.parcela_id=f.parcela_id AND d.fecha=f.fecha
LEFT JOIN refino r ON r.pad_id=f.pad_id AND r.fecha=f.fecha
EXCEPT SELECT pad_id,parcela_id,fecha,cu_drenaje_gl,cu_refino_gl FROM v;';
EXEC sys.sp_executesql @sql;

-- 14b. Otros seis analitos por lado (cero diferencias)
SET @sql=@ctes+N'SELECT f.pad_id,f.parcela_id,f.fecha,
d.h_p,d.ph,d.cl,d.fet,d.fe2,d.eh,r.h_p,r.ph,r.cl,r.fet,r.fe2,r.eh FROM flujo f
LEFT JOIN drenaje d ON d.pad_id=f.pad_id AND d.parcela_id=f.parcela_id AND d.fecha=f.fecha
LEFT JOIN refino r ON r.pad_id=f.pad_id AND r.fecha=f.fecha
EXCEPT SELECT pad_id,parcela_id,fecha,h_drenaje,ph_drenaje,cl_drenaje,fet_drenaje,fe2_drenaje,eh_drenaje,
h_refino,ph_refino,cl_refino,fet_refino,fe2_refino,eh_refino FROM v;';
EXEC sys.sp_executesql @sql;

-- 14c. Fuera de ventana con numero o estado contradictorio (cero filas)
SET @sql=@ctes+N'SELECT * FROM v
WHERE (campana_id IS NULL AND (numero_campana IS NOT NULL OR estado_asignacion<>''FUERA_VENTANA_RIEGO''))
OR (campana_id IS NOT NULL AND estado_asignacion<>''CAMPANA_HIDRAULICA'') OR estado_asignacion IS NULL;';
EXEC sys.sp_executesql @sql;

-- 15. Formulas y NULL (cero diferencias; precision final pendiente)
SET @sql=@ctes+N'SELECT pad_id,parcela_id,fecha,delta_cu_gl,transferencia_cu_kg_d,transferencia_cu_t_d FROM v
EXCEPT SELECT pad_id,parcela_id,fecha,cu_drenaje_gl-cu_refino_gl,
flujo_m3_d*(cu_drenaje_gl-cu_refino_gl),(flujo_m3_d*(cu_drenaje_gl-cu_refino_gl))/1000.0 FROM v;';
EXEC sys.sp_executesql @sql;

-- 16. NULL/negativos (informativo, no rechazar ni convertir a cero)
SET @sql=@ctes+N'SELECT * FROM v WHERE delta_cu_gl IS NULL OR delta_cu_gl<0;';
EXEC sys.sp_executesql @sql;

-- 17. Reconciliacion periodo LIVE aportado (informativa; V2 aun pendiente)
SET @sql=@ctes+N'SELECT pad_id,COUNT_BIG(*) AS claves,
SUM(CASE WHEN campana_id IS NOT NULL THEN 1 ELSE 0 END) AS con_campana,
SUM(CASE WHEN campana_id IS NULL THEN 1 ELSE 0 END) AS fuera,
SUM(CASE WHEN campana_id IS NULL AND flujo_m3_d>0 THEN 1 ELSE 0 END) AS positivos_fuera,
SUM(CASE WHEN campana_id IS NULL THEN flujo_m3_d END) AS m3_fuera
FROM v WHERE fecha BETWEEN ''20260601'' AND ''20260910'' GROUP BY pad_id;';
EXEC sys.sp_executesql @sql;

-- Referencias LIVE aportadas (NO resultados ejecutados aqui):
-- OX: 3264 claves,2219 con campana,1045 fuera,106 positivos fuera,6.128278 m3.
-- SULF:2856 claves,1839 con campana,1017 fuera,0 positivos fuera.
-- 6.128278 y desglose por parcela son cifras reportadas; precision exacta pendiente.
-- No usar umbral de descarte: conservar incluso flujo_m3_h positivo <0.01.
-- Ejemplo dimensional aportado:672*(2.03-0.28)=1176 kg/d=1.176 t/d.
-- No exigir igualdad de conteos V2 contra legacy ni aprobar tolerancias arbitrarias.
