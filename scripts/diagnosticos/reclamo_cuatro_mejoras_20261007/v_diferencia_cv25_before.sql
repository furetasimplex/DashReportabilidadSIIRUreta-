/* ============================================================================
   V10. reclamo.v_diferencia_cv25

   Agregado diario a nivel planta del contraste entre el totalizador y la
   topografia. Es la vista que alimenta el grafico principal del dashboard.

   Regla R7: CV25 recibe la carga conjunta de ambas rotopalas y NO recibe
   camiones. Por eso la comparacion se hace contra el reclamo de rotopala
   solamente, sin sumar camiones.
   ============================================================================ */
CREATE VIEW [reclamo].[v_diferencia_cv25]
AS
WITH topo AS
(
    SELECT
        rd.fecha_operacion                  AS fecha,
        SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA'
                 THEN rd.tms_rotopala_dia ELSE 0 END) AS tms_topografia,
        SUM(CASE WHEN rd.fuente_reclamo = 'PRELIMINAR_CV25'
                 THEN rd.tms_rotopala_dia ELSE 0 END) AS tms_preliminar,
        SUM(rd.tms_rotopala_dia)            AS tms_publicado,
        SUM(rd.tms_camiones_dia)            AS tms_camiones,
        SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA' THEN 1 ELSE 0 END)
                                            AS modulos_topografia,
        SUM(CASE WHEN rd.fuente_reclamo = 'PRELIMINAR_CV25' THEN 1 ELSE 0 END)
                                            AS modulos_preliminar
    FROM [reclamo].[v_reclamo_diario] rd
    GROUP BY rd.fecha_operacion
)
SELECT
    COALESCE(cv.fecha, t.fecha)             AS fecha,
    cv.tms_dia                              AS tms_cv25,
    cv.tmh_dia                              AS tmh_cv25,
    cv.horas_r1,
    cv.horas_r2,
    cv.horas_total,

    t.tms_topografia,
    t.tms_preliminar,
    t.tms_publicado,
    t.tms_camiones,
    t.modulos_topografia,
    t.modulos_preliminar,

    t.tms_topografia - cv.tms_dia           AS diferencia_topografia_cv25,
    CASE
        WHEN COALESCE(cv.tms_dia,0) = 0 THEN NULL
        ELSE (t.tms_topografia - cv.tms_dia) * 100.0 / cv.tms_dia
    END                                     AS diferencia_pct,

    CASE
        WHEN cv.fecha IS NULL
            THEN 'SIN_CV25'
        WHEN cv.tms_dia IS NULL THEN 'SIN_RESOLVER_CV25'
        WHEN COALESCE(t.modulos_topografia,0) = 0
            THEN 'SIN_TOPOGRAFIA_SOLO_PRELIMINAR'
        WHEN COALESCE(cv.tms_dia,0) = 0
            THEN 'CV25_CERO'
        WHEN ABS((t.tms_topografia - cv.tms_dia) * 100.0 / cv.tms_dia) > 10
            THEN 'BRECHA_SOBRE_10_PCT'
        ELSE 'OK'
    END                                     AS flag_diferencia
FROM [reclamo].[v_cv25_diario] cv
FULL OUTER JOIN topo t
    ON t.fecha = cv.fecha;