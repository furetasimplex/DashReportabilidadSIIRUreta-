-- Replacement for control 2 in reclamo.db.semaforo (read-only SELECT only).
-- Mirrors sp_auto_mantener_secuencia / sp_definir_secuencia default @Siguientes=5.
SELECT COUNT(*)
FROM reclamo.modulo_congelado mc
WHERE mc.estado = 'CONGELADO'
  AND NOT EXISTS (
      SELECT 1 FROM reclamo.secuencia_rotopala s
      WHERE s.[campaña_id] = mc.[campaña_id]
        AND s.modulo_id = mc.modulo_id
  )
  AND (
      EXISTS (
          SELECT 1 FROM inventar_SpcHidr.control_reclamo_diario cr
          WHERE cr.pad_id = mc.pad_id
            AND cr.[campaña_id] = mc.[campaña_id]
            AND cr.modulo_id = mc.modulo_id
            AND COALESCE(cr.volumen_diario_m3, 0) > 0
      )
      OR mc.modulo_numero > (
          SELECT MAX(md.numero)
          FROM inventar_SpcHidr.control_reclamo_diario cr
          JOIN inventar_SpcHidr.modulo md ON md.id_modulo = cr.modulo_id
          WHERE cr.pad_id = mc.pad_id
            AND cr.[campaña_id] = mc.[campaña_id]
            AND COALESCE(cr.volumen_diario_m3, 0) > 0
      )
      AND mc.modulo_numero <= (
          SELECT MAX(md.numero) + 5
          FROM inventar_SpcHidr.control_reclamo_diario cr
          JOIN inventar_SpcHidr.modulo md ON md.id_modulo = cr.modulo_id
          WHERE cr.pad_id = mc.pad_id
            AND cr.[campaña_id] = mc.[campaña_id]
            AND COALESCE(cr.volumen_diario_m3, 0) > 0
      )
  );
