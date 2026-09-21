CREATE VIEW [inventar_SpcHidr].[v_contingencia_camiones_turno] AS
SELECT r.id,
    r.fecha_operacional,
    r.turno,
    r.contexto,
    r.vueltas,
    r.tonelaje_informado,
    r.unidad_medida,
    r.batch_id,
    r.business_key_hash,
    r.source_sheet,
    r.source_row_number,
    r.source_revision_at,
    r.created_at,
    r.updated_at,
    r.quality_json,
    b.archivo_nombre AS archivo_batch,
    b.archivo_hash, b.created_by_id AS usuario_batch_id,
    N'INFORME_DIARIO' AS fuente
FROM [inventar_SpcHidr].[contingencia_camiones_turno] r
INNER JOIN [DEV_SIIR].[hidro].[import_batch] b ON b.id=r.batch_id
WHERE b.template_code COLLATE DATABASE_DEFAULT=r.template_code
  AND b.estado=N'committed'
  AND EXISTS (SELECT 1 FROM [DEV_SIIR].[hidro].[import_row_history] h
    WHERE h.batch_id=r.batch_id
      AND h.template_code COLLATE DATABASE_DEFAULT=r.template_code
      AND h.dataset_name=N'contingencia_camiones_turno'
      AND h.business_key_hash COLLATE DATABASE_DEFAULT=r.business_key_hash);