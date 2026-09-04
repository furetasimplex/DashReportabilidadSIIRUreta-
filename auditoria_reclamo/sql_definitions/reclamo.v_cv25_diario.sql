/* ============================================================================
   V4. reclamo.v_cv25_diario

   Consolida el totalizador CV25 y las horas de rotopala a grano diario.
   Es la base del preliminar y del control de rendimiento.

   Regla R7: el tonelaje CV25 corresponde a rotopala 1 mas rotopala 2.

   CORRECCION 30-07-2026: la fuente es diaria, no por turno. Las horas si
   conservan el desglose por turno, porque datos_filtrados tiene su propia
   columna turno.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_cv25_diario]
AS
WITH hr AS
(
    SELECT
        h.fecha_turno                       AS fecha,
        SUM(CASE WHEN h.rotopala_id = 1 THEN h.horas_operacion ELSE 0 END) AS horas_r1,
        SUM(CASE WHEN h.rotopala_id = 2 THEN h.horas_operacion ELSE 0 END) AS horas_r2,
        SUM(h.horas_operacion)              AS horas_total,
        COUNT(DISTINCT h.turno)             AS turnos_con_dato
    FROM [reclamo].[rotopala_horas_turno] h
    GROUP BY h.fecha_turno
)
SELECT
    COALESCE(cv.fecha, hr.fecha)            AS fecha,
    cv.tmh_dia,
    cv.tms_dia,
    cv.tmh_cv025tot,
    cv.tmh_cv025_tot,
    cv.tag_utilizado,
    cv.flag                                 AS flag_cv25,

    /* Contraste entre los dos tags del mismo totalizador. */
    cv.tmh_cv025tot - cv.tmh_cv025_tot      AS diferencia_entre_tags,
    CASE
        WHEN cv.tmh_cv025tot IS NULL OR cv.tmh_cv025_tot IS NULL
            THEN 'SIN_CONTRASTE'
        WHEN cv.tmh_cv025_tot = 0
            THEN 'TAG_SECUNDARIO_CERO'
        WHEN ABS(cv.tmh_cv025tot - cv.tmh_cv025_tot) * 100.0 / cv.tmh_cv025_tot > 1
            THEN 'TAGS_DIFIEREN_SOBRE_1_PCT'
        ELSE 'OK'
    END                                     AS flag_tags,

    hr.horas_r1,
    hr.horas_r2,
    hr.horas_total,
    hr.turnos_con_dato,

    /* Reparto proporcional del tonelaje CV25 entre ambas rotopalas.
       Si no hay horas, no se puede repartir y el preliminar no aplica. */
    CASE
        WHEN COALESCE(hr.horas_total,0) = 0 THEN NULL
        ELSE cv.tms_dia * hr.horas_r1 / hr.horas_total
    END                                     AS tms_estimado_r1,
    CASE
        WHEN COALESCE(hr.horas_total,0) = 0 THEN NULL
        ELSE cv.tms_dia * hr.horas_r2 / hr.horas_total
    END                                     AS tms_estimado_r2,

    CASE
        WHEN cv.fecha IS NULL                     THEN 'SIN_CV25'
        WHEN COALESCE(hr.horas_total,0) = 0       THEN 'SIN_HORAS_NO_REPARTIBLE'
        WHEN COALESCE(cv.tms_dia,0) = 0           THEN 'CV25_CERO_SIN_OPERACION'
        ELSE 'OK'
    END                                     AS flag_preliminar
FROM [reclamo].[cv25_diario] cv
FULL OUTER JOIN hr
    ON hr.fecha = cv.fecha;