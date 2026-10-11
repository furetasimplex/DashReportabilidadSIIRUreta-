SELECT e.fecha,e.pad_id,e.parcela_id,e.numero_parcela,e.campana_id,e.numero_campana,e.estado_operacional,e.calidad_estado,e.tiene_dato_riego,e.riego_activo,e.tiene_dato_drenaje,e.drenaje_activo,
    v.campana_id AS campana_hidraulica_id,v.numero_campana AS numero_campana_hidraulica,
    v.estado_asignacion
    FROM inventar_SpcHidr.fn_estado_operacional_parcela_diario(:fecha) e LEFT JOIN inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 v
      ON v.fecha=e.fecha AND v.pad_id=e.pad_id AND v.parcela_id=e.parcela_id
    WHERE (:pad_id IS NULL OR e.pad_id=:pad_id) AND e.parcela_id=:parcela_id