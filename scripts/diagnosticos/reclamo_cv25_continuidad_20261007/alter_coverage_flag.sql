ALTER VIEW [reclamo].[v_cv25_diario]
AS

WITH hr AS
(
    SELECT
        fecha_turno AS fecha,

        SUM
        (
            CASE
                WHEN h.rotopala_id = 1
                THEN h.horas_operacion
                ELSE 0
            END
        ) AS horas_r1,

        SUM
        (
            CASE
                WHEN h.rotopala_id = 2
                THEN h.horas_operacion
                ELSE 0
            END
        ) AS horas_r2,

        SUM(h.horas_operacion) AS horas_total,

        COUNT(DISTINCT h.turno) AS turnos_con_dato

    FROM [reclamo].[rotopala_horas_turno] h

    GROUP BY
        fecha_turno
)

SELECT
    COALESCE(cv.fecha, hr.fecha) AS fecha,

    cv.tmh_dia,
    cv.tms_dia,

    cv.tmh_cv025tot,
    cv.tmh_cv025_tot,

    cv.tag_utilizado,

    cv.flag AS flag_cv25,

    cv.tmh_cv025tot - cv.tmh_cv025_tot
        AS diferencia_entre_tags,

    ------------------------------------------------------------
    -- Contraste de tags CV025
    ------------------------------------------------------------
    CASE
        WHEN cv.tmh_cv025tot IS NULL
          OR cv.tmh_cv025_tot IS NULL
            THEN 'SIN_CONTRASTE'

        WHEN cv.tmh_cv025_tot = 0
            THEN 'TAG_SECUNDARIO_CERO'

        WHEN
            ABS(cv.tmh_cv025tot - cv.tmh_cv025_tot)
            * 100.0 / cv.tmh_cv025_tot > 1
            THEN 'TAGS_DIFIEREN_SOBRE_1_PCT'

        ELSE 'OK'
    END AS flag_tags,

    hr.horas_r1,
    hr.horas_r2,
    hr.horas_total,
    hr.turnos_con_dato,

    ------------------------------------------------------------
    -- TMS estimado R1
    --
    -- Si CV025 = 0, no hubo operación:
    -- corresponde explícitamente 0 TMS.
    --
    -- Con cobertura de corriente y cero horas: cero confirmado.
    -- Sin cobertura y cero horas: no inferir cero.
    ------------------------------------------------------------
    CASE
        WHEN cv.tms_dia IS NULL THEN NULL
        WHEN COALESCE(hr.horas_r1, 0) = 0
         AND COALESCE(cv.horas_con_dato_r1, 0) = 0
            THEN NULL

        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 0

        WHEN COALESCE(hr.horas_r1, 0) = 0
         AND COALESCE(cv.horas_con_dato_r1, 0) > 0
            THEN 0

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN NULL

        ELSE
            cv.tms_dia
            * hr.horas_r1
            / hr.horas_total
    END AS tms_estimado_r1,

    ------------------------------------------------------------
    -- TMS estimado R2
    ------------------------------------------------------------
    CASE
        WHEN cv.tms_dia IS NULL THEN NULL
        WHEN COALESCE(hr.horas_r2, 0) = 0
         AND COALESCE(cv.horas_con_dato_r2, 0) = 0
            THEN NULL

        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 0

        WHEN COALESCE(hr.horas_r2, 0) = 0
         AND COALESCE(cv.horas_con_dato_r2, 0) > 0
            THEN 0

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN NULL

        ELSE
            cv.tms_dia
            * hr.horas_r2
            / hr.horas_total
    END AS tms_estimado_r2,

    ------------------------------------------------------------
    -- Estado del preliminar
    ------------------------------------------------------------
    CASE
        WHEN cv.fecha IS NULL
            THEN 'SIN_CV25'

        WHEN cv.tms_dia IS NULL THEN 'SIN_RESOLVER_CV25'
        WHEN COALESCE(cv.horas_con_dato_r1, 0) = 0
         AND COALESCE(cv.horas_con_dato_r2, 0) = 0
            THEN 'SIN_COBERTURA_CORRIENTES'
        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 'CV25_CERO_SIN_OPERACION'

        WHEN COALESCE(hr.horas_total, 0) = 0
         AND (
             (COALESCE(hr.horas_r1, 0) = 0 AND COALESCE(cv.horas_con_dato_r1, 0) > 0)
             OR (COALESCE(hr.horas_r2, 0) = 0 AND COALESCE(cv.horas_con_dato_r2, 0) > 0)
         )
            THEN 'CERO_OPERACION_CONFIRMADO'

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN 'SIN_HORAS_NO_REPARTIBLE'

        ELSE 'OK'
    END AS flag_preliminar

FROM [reclamo].[cv25_diario] cv

FULL OUTER JOIN hr
    ON hr.fecha = cv.fecha;
