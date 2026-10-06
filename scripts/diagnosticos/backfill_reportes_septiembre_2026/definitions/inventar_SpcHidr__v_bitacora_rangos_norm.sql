CREATE   VIEW inventar_SpcHidr.v_bitacora_rangos_norm
AS
SELECT
    fecha_turno = r.fecha_turno,
    turno_op    = r.turno,
    torre_id    = r.torre,
    Torre = CASE r.torre
        WHEN 1 THEN 'T1'
        WHEN 2 THEN 'T2'
        WHEN 3 THEN 'SRR'
        ELSE NULL
    END,
    ts_ini      = r.ts_ini,
    ts_fin      = r.ts_fin,
    flag_arrastre = r.flag_arrastre,
    duracion_min  = r.duracion_min,
    comentario    = r.comentario,
    nombre_archivo= r.nombre_archivo
FROM inventar_SpcHidr.v_bitacora_rangos r;
