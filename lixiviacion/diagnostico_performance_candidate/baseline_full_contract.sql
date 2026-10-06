WITH fechas AS (
    SELECT CAST(:desde AS date) AS fecha
    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(:hasta AS date)
    ) SELECT e.fecha,e.pad_id,e.nombre_pad,e.parcela_id,e.numero_parcela,e.campana_id,e.numero_campana,e.modulos_total,e.estados_distintos,e.estado_operacional,e.composicion_modulos,e.tiene_dato_riego,e.riego_activo,e.tiene_dato_drenaje,e.drenaje_activo,e.fecha_ini_carguio,e.fecha_conformado,e.fecha_primer_riego,e.fecha_ultima_actividad_riego,e.fecha_ini_drenaje,e.fecha_ultima_actividad_drenaje,e.fecha_ini_reclamo,e.fecha_fin_reclamo,e.calidad_estado
    FROM fechas d CROSS APPLY inventar_SpcHidr.fn_estado_operacional_parcela_diario(d.fecha) e
    WHERE e.pad_id=:pad_id AND e.parcela_id=:parcela_id
    ORDER BY e.fecha OPTION (MAXRECURSION 32767)