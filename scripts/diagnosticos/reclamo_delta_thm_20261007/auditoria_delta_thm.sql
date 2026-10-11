/* DEV, solo lectura. PAD2 / campaña_id 10. Tolerancia 0,001 m3.
   Fuente: inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario.
   Unicidad (campaña_id, modulo_id, fecha) verificada en snapshot de 2026-10-07.
   La fecha de Volumen Pilas opera D-1; no se desplaza aquí otra vez. */
WITH x AS (
    SELECT s.fecha, s.[campaña_id], s.modulo_id, s.modulo,
        CAST(s.volumen_diario_m3 AS decimal(30,12)) AS volumen_diario_fuente,
        CAST(s.volumen_final_reclamado AS decimal(30,12)) AS acumulado_actual,
        CAST(LAG(s.volumen_final_reclamado) OVER (
            PARTITION BY s.[campaña_id], s.modulo_id ORDER BY s.fecha
        ) AS decimal(30,12)) AS acumulado_anterior,
        ROW_NUMBER() OVER (
            PARTITION BY s.[campaña_id], s.modulo_id ORDER BY s.fecha
        ) AS rn
    FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario s
    INNER JOIN reclamo.modulo_congelado mc
        ON mc.[campaña_id] = s.[campaña_id] AND mc.modulo_id = s.modulo_id
       AND mc.pad_id = 2
    WHERE s.[campaña_id] = 10 AND s.pad_id = 2
), y AS (
    SELECT x.*, mc.modulo_numero,
        CASE WHEN rn > 1 THEN acumulado_actual-acumulado_anterior END AS delta_acumulado,
        CASE WHEN rn = 1 THEN acumulado_actual-volumen_diario_fuente END AS arrastre_inicial,
        cr.m3_thm AS m3_thm_reclamo, cr.estado AS estado_reclamo,
        v.m3_camiones_dia AS m3_oficial, v.m3_camiones_acum
    FROM x
    INNER JOIN reclamo.modulo_congelado mc
        ON mc.[campaña_id]=x.[campaña_id] AND mc.modulo_id=x.modulo_id
       AND mc.pad_id=2
    LEFT JOIN reclamo.camiones_reclamo cr
        ON cr.[campaña_id]=x.[campaña_id] AND cr.modulo_id=x.modulo_id
       AND cr.fecha=x.fecha
    LEFT JOIN reclamo.v_camiones_acumulado v
        ON v.[campaña_id]=x.[campaña_id] AND v.modulo_id=x.modulo_id
       AND v.fecha=x.fecha
), z AS (
    SELECT y.*,
        CASE WHEN rn > 1 THEN delta_acumulado-volumen_diario_fuente END AS diferencia_delta,
        volumen_diario_fuente-COALESCE(m3_thm_reclamo,0) AS diferencia_vs_reclamo,
        COALESCE(m3_thm_reclamo,0)-COALESCE(m3_oficial,0) AS diferencia_thm_vs_oficial
    FROM y
)
SELECT fecha,[campaña_id],modulo_id,modulo_numero,rn,
    volumen_diario_fuente,acumulado_anterior,acumulado_actual,
    delta_acumulado,diferencia_delta,arrastre_inicial,m3_thm_reclamo,
    diferencia_vs_reclamo,m3_oficial,estado_reclamo,diferencia_thm_vs_oficial,
    CASE
        WHEN rn=1 AND ABS(arrastre_inicial)>0.001 THEN 'ARRANQUE_CON_ACUMULADO'
        WHEN rn>1 AND ABS(diferencia_delta)>0.001 THEN 'DELTA_INTERNO_INCONSISTENTE'
        WHEN ABS(diferencia_vs_reclamo)>0.001 THEN 'FUENTE_OK_NO_SINCRONIZADA'
        ELSE 'OK'
    END AS clasificacion
FROM z
WHERE rn=1 OR ABS(COALESCE(diferencia_delta,0))>0.001
    OR ABS(diferencia_vs_reclamo)>0.001
    OR ABS(diferencia_thm_vs_oficial)>0.001
ORDER BY modulo_id,fecha;

/* Control focal: repetir la consulta anterior cambiando la cláusula final
   por WHERE fecha='2026-09-30'. No ejecutar el SP de sincronización. */
