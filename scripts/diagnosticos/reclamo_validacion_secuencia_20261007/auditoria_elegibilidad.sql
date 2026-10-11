-- Read-only. Mirrors the A/B eligibility used by the live sequence SPs
-- with their default @Siguientes = 5; trucks are not evidence of rotopala.
WITH frente AS (
    SELECT cr.[campaña_id], cr.pad_id, MAX(md.numero) AS modulo_max_topo
    FROM inventar_SpcHidr.control_reclamo_diario cr
    JOIN inventar_SpcHidr.modulo md ON md.id_modulo = cr.modulo_id
    WHERE COALESCE(cr.volumen_diario_m3, 0) > 0
    GROUP BY cr.[campaña_id], cr.pad_id
), candidatos AS (
    SELECT mc.[campaña_id], mc.pad_id, mc.modulo_id, mc.modulo_numero,
           f.modulo_max_topo,
           CASE WHEN EXISTS (
               SELECT 1 FROM inventar_SpcHidr.control_reclamo_diario cr
               WHERE cr.pad_id = mc.pad_id
                 AND cr.[campaña_id] = mc.[campaña_id]
                 AND cr.modulo_id = mc.modulo_id
                 AND COALESCE(cr.volumen_diario_m3, 0) > 0
           ) THEN 1 ELSE 0 END AS evidencia_rotopala,
           CASE WHEN mc.modulo_numero > f.modulo_max_topo
                  AND mc.modulo_numero <= f.modulo_max_topo + 5
                THEN 1 ELSE 0 END AS cola_fisica
    FROM reclamo.modulo_congelado mc
    LEFT JOIN frente f ON f.[campaña_id] = mc.[campaña_id]
                      AND f.pad_id = mc.pad_id
    WHERE mc.estado = 'CONGELADO'
      AND NOT EXISTS (
          SELECT 1 FROM reclamo.secuencia_rotopala s
          WHERE s.[campaña_id] = mc.[campaña_id]
            AND s.modulo_id = mc.modulo_id
      )
)
SELECT *, CASE WHEN evidencia_rotopala = 1 OR cola_fisica = 1
               THEN 1 ELSE 0 END AS bloqueante_aplicable
FROM candidatos
ORDER BY pad_id, [campaña_id], modulo_numero;
