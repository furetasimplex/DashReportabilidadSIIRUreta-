CREATE VIEW [reclamo].[v_cv25_diario_contingencia_test]
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
    -- Si CV025 > 0 pero no hay horas:
    -- no podemos repartir el tonelaje.
    ------------------------------------------------------------
    CASE
        WHEN cv.pendiente = 1 THEN NULL
        WHEN COALESCE(cv.tms_dia, 0) = 0
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
        WHEN cv.pendiente = 1 THEN NULL
        WHEN COALESCE(cv.tms_dia, 0) = 0
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
        WHEN cv.pendiente = 1 THEN 'PENDIENTE_TUM'
        WHEN cv.fecha IS NULL
            THEN 'SIN_CV25'

        WHEN cv.pendiente = 1 THEN NULL
        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 'CV25_CERO_SIN_OPERACION'

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN 'SIN_HORAS_NO_REPARTIBLE'

        ELSE 'OK'
    END AS flag_preliminar

FROM (
    SELECT COALESCE(base.fecha,op.Fecha) AS fecha,
           CONVERT(decimal(30,12), CASE WHEN op.activa=1 THEN op.tmh ELSE base.tmh_dia END) AS tmh_dia,
           CONVERT(decimal(30,12), CASE WHEN op.activa=1 THEN op.tmh *
                (1.0 - COALESCE(base.humedad_pct,0) / 100.0)
                ELSE base.tms_dia END) AS tms_dia,
           base.tmh_cv025tot,base.tmh_cv025_tot,
           CASE WHEN op.activa=1 THEN 'RO_CV025' ELSE base.tag_utilizado END AS tag_utilizado,
           CASE WHEN op.activa=1 AND op.tmh IS NULL THEN 'PENDIENTE_TUM'
                WHEN op.activa=1 THEN 'OPERACIONAL_PI_TUM' ELSE base.flag END AS flag,
           CASE WHEN op.activa=1 AND op.tmh IS NULL THEN 1 ELSE 0 END AS pendiente
    FROM [reclamo].[cv25_diario] base
    FULL OUTER JOIN (
        SELECT fecha_operacional AS Fecha,
               MAX(CONVERT(int,contingencia_pi_activa)) AS activa,
               CASE WHEN COUNT(*)<>2 OR SUM(CASE WHEN valor_final_resuelto IS NULL THEN 1 ELSE 0 END)>0
                    THEN NULL ELSE SUM(CONVERT(decimal(28,6),valor_final_resuelto)) END AS tmh
        FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test
        WHERE equipo_codigo='RIPIOS_CV025'
        GROUP BY fecha_operacional
    ) op ON op.Fecha=base.fecha
) cv

FULL OUTER JOIN hr
    ON hr.fecha = cv.fecha;
