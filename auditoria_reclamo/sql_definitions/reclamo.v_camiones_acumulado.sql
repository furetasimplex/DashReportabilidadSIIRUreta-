/* ============================================================================
   V2. reclamo.v_camiones_acumulado

   Regla R4. El acumulado NO se limita al mes: parte del inicio de la campana,
   porque un modulo puede haber sido reclamado por camiones mucho antes.

   El contraste geomensura contra THM es el control que el Excel hacia a mano
   y que aca queda permanente.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_camiones_acumulado]
AS
SELECT
    cr.fecha,
    cr.[campaña_id],
    cr.pad_id,
    cr.modulo_id,

    cr.m3_oficial                           AS m3_camiones_dia,
    cr.tms_oficial                          AS tms_camiones_dia,

    SUM(cr.m3_oficial) OVER
    (
        PARTITION BY cr.[campaña_id], cr.modulo_id
        ORDER BY cr.fecha
        ROWS UNBOUNDED PRECEDING
    )                                       AS m3_camiones_acum,

    SUM(cr.tms_oficial) OVER
    (
        PARTITION BY cr.[campaña_id], cr.modulo_id
        ORDER BY cr.fecha
        ROWS UNBOUNDED PRECEDING
    )                                       AS tms_camiones_acum,

    cr.m3_geomensura,
    cr.m3_thm,
    cr.vueltas,
    cr.capacidad_camion_m3,
    cr.fuente_oficial,

    /* Brecha relativa entre las dos mediciones, solo cuando ambas existen. */
    CASE
        WHEN cr.m3_geomensura IS NULL OR cr.m3_thm IS NULL THEN NULL
        WHEN cr.m3_thm = 0 THEN NULL
        ELSE (cr.m3_geomensura - cr.m3_thm) * 100.0 / cr.m3_thm
    END                                     AS brecha_geomensura_thm_pct,

    CASE
        WHEN cr.m3_geomensura IS NULL OR cr.m3_thm IS NULL
            THEN 'SIN_CONTRASTE'
        WHEN cr.m3_thm = 0
            THEN 'THM_CERO'
        WHEN ABS((cr.m3_geomensura - cr.m3_thm) * 100.0 / cr.m3_thm) > 10
            THEN 'BRECHA_SOBRE_10_PCT'
        ELSE 'OK'
    END                                     AS flag_contraste_camiones
FROM [reclamo].[camiones_reclamo] cr
WHERE cr.estado = 'VIGENTE';