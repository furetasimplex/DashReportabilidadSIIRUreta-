-- PREPARADO, NO EJECUTADO. Solo metadatos, sin comparar cardinalidad legacy/V2.
-- VALIDADO LIVE: TEST V4 funcional y tipos reportados; detalle sys.columns no recibido.
-- Lista local25 NO es contrato LIVE33: pendiente conciliar antes de exigir igualdad.
-- VALIDADO LIVE: formulas Cu y reglas fuente segun evidencia aportada, no metadata V2.
DECLARE @legacy int=OBJECT_ID(N'inventar_SpcHidr.vw_tablero_lixiviacion_final',N'V'),
        @v2 int=OBJECT_ID(N'inventar_SpcHidr.vw_tablero_lixiviacion_final_v2',N'V');
IF @legacy IS NULL OR @v2 IS NULL
 THROW 51400, 'Falta una vista o permiso de visibilidad; no afirmar compatibilidad.',1;
;WITH l AS (
 SELECT c.name,c.column_id,SCHEMA_NAME(t.schema_id) AS tipo_esquema,
 TYPE_NAME(c.user_type_id) AS tipo,c.max_length,c.precision,c.scale,c.is_nullable,c.collation_name
 FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE c.object_id=@legacy
), v AS (
 SELECT c.name,c.column_id,SCHEMA_NAME(t.schema_id) AS tipo_esquema,
 TYPE_NAME(c.user_type_id) AS tipo,c.max_length,c.precision,c.scale,c.is_nullable,c.collation_name
 FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE c.object_id=@v2
)
SELECT COALESCE(l.name,v.name) AS columna,
 l.column_id AS ordinal_legacy,v.column_id AS ordinal_v2,
 l.tipo_esquema AS esquema_tipo_legacy,v.tipo_esquema AS esquema_tipo_v2,
 l.tipo AS tipo_legacy,v.tipo AS tipo_v2,
 l.max_length AS longitud_bytes_legacy,v.max_length AS longitud_bytes_v2,
 l.precision AS precision_legacy,v.precision AS precision_v2,
 l.scale AS escala_legacy,v.scale AS escala_v2,
 l.is_nullable AS nullable_legacy,v.is_nullable AS nullable_v2,
 l.collation_name AS collation_legacy,v.collation_name AS collation_v2,
 CASE WHEN l.name IS NULL THEN 'NUEVA'
      WHEN v.name IS NULL THEN 'ELIMINADA_O_RENOMBRADA'
      WHEN EXISTS(SELECT l.tipo_esquema,l.tipo,l.max_length,l.precision,l.scale,l.is_nullable,l.collation_name
                  EXCEPT SELECT v.tipo_esquema,v.tipo,v.max_length,v.precision,v.scale,v.is_nullable,v.collation_name)
      THEN 'TIPO_O_NULLABILITY_DISTINTO'
      WHEN l.column_id<>v.column_id THEN 'ORDINAL_DISTINTO'
      ELSE 'METADATOS_IGUALES_NO_PRUEBA_SEMANTICA' END AS resultado
FROM l FULL JOIN v ON v.name=l.name
ORDER BY COALESCE(l.column_id,v.column_id),columna;
-- ATENCION: transferencia_cu_kg_d puede conservar tipo/nombre y cambiar x1000.
-- Esta consulta NO valida unidades, formulas, significado ni grano.
-- Comparar renombres con MATRIZ_CONTRATO.md, no emparejar por ordinal.

-- Contrastar nombres y orden EXACTOS del candidato, no del contrato legacy.
-- No inventar precision/scale/nullable esperados: inspeccionarlos en el resultado previo.
;WITH esperado AS (
 SELECT * FROM (VALUES
 (1,N'pad_id'),(2,N'parcela_id'),(3,N'fecha'),(4,N'campana_id'),
 (5,N'numero_campana'),(6,N'estado_asignacion'),(7,N'flujo_m3_h'),(8,N'flujo_m3_d'),
 (9,N'cu_drenaje_gl'),(10,N'h_drenaje'),(11,N'ph_drenaje'),(12,N'cl_drenaje'),
 (13,N'fet_drenaje'),(14,N'fe2_drenaje'),(15,N'eh_drenaje'),
 (16,N'cu_refino_gl'),(17,N'h_refino'),(18,N'ph_refino'),(19,N'cl_refino'),
 (20,N'fet_refino'),(21,N'fe2_refino'),(22,N'eh_refino'),(23,N'delta_cu_gl'),
 (24,N'transferencia_cu_kg_d'),(25,N'transferencia_cu_t_d')
 ) x(ordinal,nombre)
), actual AS (SELECT column_id,name FROM sys.columns WHERE object_id=@v2)
SELECT e.ordinal AS esperado_ordinal,e.nombre AS esperado_nombre,
 a.column_id AS actual_ordinal,a.name AS actual_nombre
FROM esperado e FULL JOIN actual a ON a.column_id=e.ordinal
WHERE e.nombre IS NULL OR a.name IS NULL OR e.nombre<>a.name;
-- Cero filas esperado. Estado CAMPANA_HIDRAULICA/FUERA_VENTANA_RIEGO se prueba en 02.

-- Tipos reales de las fuentes, sin inferir que todos los analitos sean g/L.
SELECT OBJECT_SCHEMA_NAME(c.object_id) AS esquema,OBJECT_NAME(c.object_id) AS objeto,
 c.column_id,c.name,TYPE_NAME(c.user_type_id) AS tipo,c.max_length,c.precision,c.scale,c.is_nullable
FROM sys.columns c WHERE c.object_id IN (
 OBJECT_ID('inventar_SpcHidr.vw_drena_concentrados_oxido_long'),
 OBJECT_ID('inventar_SpcHidr.vw_drena_concentrados_sulfuro_long'),
 OBJECT_ID('inventar_SpcHidr.vw_riego_oxido_refino_base'),
 OBJECT_ID('inventar_SpcHidr.vw_riego_sulfuro_refino_base'),
 OBJECT_ID('inventar_SpcHidr.vw_flujos_reales_oxido_long'),
 OBJECT_ID('inventar_SpcHidr.vw_flujos_reales_sulfuro_long'))
ORDER BY objeto,c.column_id;
