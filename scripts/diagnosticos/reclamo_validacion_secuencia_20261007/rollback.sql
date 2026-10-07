-- Original control 2 SELECT. To roll back the Python change, restore this
-- predicate in reclamo.db.semaforo; no database DDL was applied.
SELECT COUNT(*) FROM reclamo.modulo_congelado mc
WHERE mc.estado = 'CONGELADO'
  AND NOT EXISTS (SELECT 1 FROM reclamo.secuencia_rotopala s
                  WHERE s.[campaña_id] = mc.[campaña_id]
                    AND s.modulo_id = mc.modulo_id);
