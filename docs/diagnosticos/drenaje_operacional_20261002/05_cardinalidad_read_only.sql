-- PREPARADO, NO EJECUTADO. Solo DEV. Sin inferir agregacion de negocio.
-- Requiere previamente confirmar esquema/columnas con 01 y 02.
DECLARE @desde date='20260601', @hasta date='20260910';
;WITH d AS (
 SELECT 'OX' AS fuente,id_registro,parcela_numero,fecha_registro_raw,fecha_operacional
 FROM inventar_SpcHidr.v_drena_oxido_operacional
 UNION ALL
 SELECT 'SULF',id_registro,parcela_numero,fecha_registro_raw,fecha_operacional
 FROM inventar_SpcHidr.v_drena_sulfuro_operacional
)
SELECT fuente,parcela_numero,fecha_operacional,COUNT_BIG(*) AS registros
FROM d WHERE fecha_operacional BETWEEN @desde AND @hasta
GROUP BY fuente,parcela_numero,fecha_operacional HAVING COUNT_BIG(*)>1;

-- Comparar la regla exacta sin transformar NULL; mostrar discrepancias.
;WITH d AS (
 SELECT 'OX' AS fuente,id_registro,parcela_numero,fecha_registro_raw,fecha_operacional
 FROM inventar_SpcHidr.v_drena_oxido_operacional
 UNION ALL
 SELECT 'SULF',id_registro,parcela_numero,fecha_registro_raw,fecha_operacional
 FROM inventar_SpcHidr.v_drena_sulfuro_operacional
), esperado AS (
 SELECT *, CASE WHEN fecha_registro_raw>='2026-06-01T21:00:00'
                 AND DATEPART(HOUR,fecha_registro_raw)>=20
           THEN DATEADD(DAY,1,CAST(fecha_registro_raw AS date))
           ELSE CAST(fecha_registro_raw AS date) END AS fecha_esperada FROM d
)
SELECT * FROM esperado
WHERE fecha_operacional<>fecha_esperada
 OR (fecha_operacional IS NULL AND fecha_esperada IS NOT NULL)
 OR (fecha_operacional IS NOT NULL AND fecha_esperada IS NULL);

-- Multiplicidad de control: no es automaticamente un defecto (grano modulo).
SELECT campana_id,pad_id,parcela_id,COUNT_BIG(*) AS filas_control,
 COUNT(DISTINCT modulo_id) AS modulos
FROM inventar_SpcHidr.campana_parcela_control
GROUP BY campana_id,pad_id,parcela_id HAVING COUNT_BIG(*)>1;

-- Numero de coincidencias de cada registro de drenaje con el JOIN historico.
-- pad 1/2 son los del SP historico; contrastar con catalogo antes de interpretar.
;WITH d AS (
 SELECT 1 AS pad_id,id_registro,parcela_numero,fecha_operacional
 FROM inventar_SpcHidr.v_drena_oxido_operacional
 UNION ALL
 SELECT 2,id_registro,parcela_numero,fecha_operacional
 FROM inventar_SpcHidr.v_drena_sulfuro_operacional
)
SELECT d.pad_id,d.id_registro,d.parcela_numero,d.fecha_operacional,c.campana_id,
 COUNT_BIG(*) AS coincidencias_control
FROM d JOIN inventar_SpcHidr.parcela p
 ON p.id_pad=d.pad_id AND p.numero=d.parcela_numero
JOIN inventar_SpcHidr.campana_parcela_control c
 ON c.pad_id=p.id_pad AND c.parcela_id=p.id_parcela
 AND d.fecha_operacional BETWEEN c.fecha_primer_riego AND c.fecha_ultimo_riego
WHERE d.fecha_operacional BETWEEN @desde AND @hasta
GROUP BY d.pad_id,d.id_registro,d.parcela_numero,d.fecha_operacional,c.campana_id
HAVING COUNT_BIG(*)>1;

-- Historia de recuperacion que puede multiplicar joins sin fecha en modelo6.
SELECT PAD,Campana,Parcela,COUNT_BIG(*) AS filas,
 COUNT(DISTINCT Fecha_drenaje) AS fechas
FROM inventar_SpcHidr.control_ley_ripio
GROUP BY PAD,Campana,Parcela HAVING COUNT_BIG(*)>1;
-- No elegir MAX/AVG/SUM como solucion a las filas anteriores sin definir semantica.
