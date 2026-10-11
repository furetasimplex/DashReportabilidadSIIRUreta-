-- DEV / solo lectura. Compara MAX histórico con el acumulado de la última fecha.
WITH ordenado AS (
    SELECT c.campaña_id,c.modulo_id,c.fecha,c.m3_camiones_dia,c.m3_camiones_acum,
           c.tms_camiones_dia,c.tms_camiones_acum,
           MAX(c.m3_camiones_acum) OVER (PARTITION BY c.campaña_id,c.modulo_id) AS max_historico,
           ROW_NUMBER() OVER (PARTITION BY c.campaña_id,c.modulo_id ORDER BY c.fecha DESC) AS rn
    FROM reclamo.v_camiones_acumulado c
    WHERE c.campaña_id=10 AND c.modulo_id IN (81,87)
)
SELECT o.*,q.modulo_numero,q.m3_camiones_sistema,q.m3_camiones_total,
       q.m3_extraido_total,q.porcentaje_extraido,q.m3_saldo_disponible
FROM ordenado o
JOIN reclamo.v_cuadratura_modulo q
  ON q.campaña_id=o.campaña_id AND q.modulo_id=o.modulo_id
WHERE o.rn=1;

SELECT fecha,campaña_id,modulo_id,m3_camiones_dia,m3_camiones_acum,
       tms_camiones_dia,tms_camiones_acum
FROM reclamo.v_camiones_acumulado
WHERE campaña_id=10 AND modulo_id IN (81,87)
ORDER BY modulo_id,fecha;
