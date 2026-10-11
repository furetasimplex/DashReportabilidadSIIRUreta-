/* ============================================================================
   CORRECCIÓN FINAL: v_preliminar_cv25_con_acumulado
   
   EL BUG: La fórmula anterior restaba al final, anulando la suma anterior
   
   CORRECCIÓN: 
   m3_preliminar_acum = m3_acum_ultima_topografia + SUM(m3_preliminar_dia)
   
   Sin restar nada. Simple suma de acumulados.
   ============================================================================ */

CREATE VIEW [reclamo].[v_preliminar_cv25_con_acumulado] AS
WITH abiertos AS
(
    SELECT [campaña_id], modulo_id, MAX(fecha_medicion) AS ultima_topografia_fecha
    FROM [reclamo].[v_topografia_resuelta]
    GROUP BY [campaña_id], modulo_id
),
cv AS
(
    SELECT 
        [campaña_id], 
        modulo_id, 
        ultima_topografia_fecha,
        (SELECT MAX(m3_reclamado_acum) 
         FROM [reclamo].[v_topografia_resuelta] tr
         WHERE tr.[campaña_id] = ab.[campaña_id]
           AND tr.modulo_id = ab.modulo_id
           AND tr.fecha_medicion = ab.ultima_topografia_fecha) AS m3_acum_ultima_topografia
    FROM abiertos ab
),
base AS
(
    SELECT 
        c.[campaña_id],
        c.modulo_id,
        c.m3_acum_ultima_topografia,
        pv.fecha_operacion,
        pv.m3_preliminar_dia,
        pv.tms_preliminar_dia,
        pv.fuente_reclamo,
        pv.metodo_calculo
    FROM cv c
    LEFT JOIN [reclamo].[v_preliminar_cv25] pv
        ON pv.[campaña_id] = c.[campaña_id]
       AND pv.modulo_id = c.modulo_id
       AND pv.fecha_operacion > c.ultima_topografia_fecha
),
preliminar_diario AS
(
    SELECT 
        [campaña_id],
        modulo_id,
        m3_acum_ultima_topografia,
        fecha_operacion,
        m3_preliminar_dia,
        tms_preliminar_dia,
        fuente_reclamo,
        metodo_calculo
    FROM base
),
preliminar_acum AS
(
    SELECT
        pd.[campaña_id],
        pd.modulo_id,
        pd.fecha_operacion,
        pd.m3_preliminar_dia,
        pd.tms_preliminar_dia,
        /* CORRECCIÓN: sumar acumulado anterior + preliminar actual (SIN restar nada) */
        COALESCE(pd.m3_acum_ultima_topografia, 0)
        + SUM(COALESCE(pd.m3_preliminar_dia, 0))
          OVER (
              PARTITION BY pd.[campaña_id], pd.modulo_id
              ORDER BY pd.fecha_operacion
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
          ) AS m3_preliminar_acum,
        COALESCE(pd.tms_preliminar_dia, 0) * 
        (
            SELECT COALESCE(densidad_oficial, 1) 
            FROM [reclamo].[v_modulo_base] mb
            WHERE mb.[campaña_id] = pd.[campaña_id]
              AND mb.modulo_id = pd.modulo_id
        )
        + SUM(COALESCE(pd.tms_preliminar_dia, 0) * 
              (SELECT COALESCE(densidad_oficial, 1) FROM [reclamo].[v_modulo_base] mb 
               WHERE mb.[campaña_id] = pd.[campaña_id] AND mb.modulo_id = pd.modulo_id))
          OVER (
              PARTITION BY pd.[campaña_id], pd.modulo_id
              ORDER BY pd.fecha_operacion
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
          ) AS tms_preliminar_acum,
        pd.m3_acum_ultima_topografia,
        pd.fuente_reclamo,
        pd.metodo_calculo
    FROM preliminar_diario pd
)
SELECT
    pa.fecha_operacion,
    pa.[campaña_id],
    pa.modulo_id,
    pa.tms_preliminar_dia,
    pa.m3_preliminar_dia,
    pa.m3_preliminar_acum,
    pa.m3_acum_ultima_topografia,
    pa.fuente_reclamo,
    pa.metodo_calculo
FROM preliminar_acum pa;