-- DEV / solo lectura. La primera consulta debe devolver cero filas.
WITH ultimo AS (
    SELECT campaña_id,modulo_id,m3_camiones_acum,
           ROW_NUMBER() OVER (PARTITION BY campaña_id,modulo_id ORDER BY fecha DESC) AS rn
    FROM reclamo.v_camiones_acumulado
)
SELECT q.campaña_id,q.modulo_id,q.m3_camiones_sistema,u.m3_camiones_acum
FROM reclamo.v_cuadratura_modulo q
JOIN ultimo u ON u.campaña_id=q.campaña_id AND u.modulo_id=q.modulo_id AND u.rn=1
WHERE ABS(q.m3_camiones_sistema-u.m3_camiones_acum)>0.000001;

SELECT COUNT(*) AS filas,COUNT(DISTINCT CONCAT(campaña_id,':',modulo_id)) AS pares_unicos
FROM reclamo.v_cuadratura_modulo;

SELECT campaña_id,modulo_id,COUNT(*) AS duplicados
FROM reclamo.v_cuadratura_modulo
GROUP BY campaña_id,modulo_id HAVING COUNT(*)>1;

SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_cuadratura_modulo')) AS definicion;
