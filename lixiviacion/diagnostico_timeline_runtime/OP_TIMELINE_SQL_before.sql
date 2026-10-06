WITH fechas AS (
    SELECT CAST(:desde AS date) AS fecha
    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(:hasta AS date)
    ) SELECT e.fecha,e.pad_id,e.parcela_id,e.numero_parcela,e.campana_id,e.numero_campana,e.estado_operacional,e.calidad_estado,e.tiene_dato_riego,e.riego_activo,e.tiene_dato_drenaje,e.drenaje_activo
    FROM fechas d CROSS APPLY inventar_SpcHidr.fn_estado_operacional_parcela_diario(d.fecha) e
    WHERE e.pad_id=:pad_id AND e.parcela_id=:parcela_id
    ORDER BY e.fecha OPTION (MAXRECURSION 32767)