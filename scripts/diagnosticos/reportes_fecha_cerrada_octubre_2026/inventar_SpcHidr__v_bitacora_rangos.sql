--
CREATE VIEW inventar_SpcHidr.v_bitacora_rangos AS
WITH b AS (
    SELECT
        torre,
        fecha_turno = fecha_calendario,
        turno,
        ts_fin = ts_toma_muestra,
        comentario,
        nombre_archivo,
        ts_fin_prev = LAG(ts_toma_muestra) OVER (
            PARTITION BY torre
            ORDER BY ts_toma_muestra
        )
    FROM inventar_SpcHidr.bitacora_turnos_consolidada
    WHERE ts_toma_muestra IS NOT NULL
)
SELECT
    torre,
    fecha_turno,
    turno,
    ts_ini = ts_fin_prev,
    ts_fin,
    flag_arrastre = CASE WHEN ts_fin_prev = ts_fin THEN 1 ELSE 0 END,
    duracion_min = CASE
        WHEN ts_fin_prev IS NULL THEN NULL
        ELSE DATEDIFF(MINUTE, ts_fin_prev, ts_fin)
    END,
    comentario,
    nombre_archivo
FROM b;