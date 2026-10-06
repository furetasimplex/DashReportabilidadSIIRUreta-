/* -----------------------------------------------------------
   SECCION 2: Vistas consumen la tabla resumen en vez de recalcular
----------------------------------------------------------- */
CREATE   VIEW inventar_SpcHidr.v_ton_por_intervalo_excel
AS
SELECT
    dia_op            = s.fecha_turno,
    Torre             = s.Torre,
    turno_op          = s.turno_op,
    ts_ini            = s.ts_ini,
    ts_fin            = s.ts_fin,
    tot_ini           = s.tot_ini,
    tot_fin           = s.tot_fin,
    toneladas_intervalo = s.toneladas_intervalo,
    flag_intervalo_ok = s.flag_intervalo_ok,
    s.torre_id,
    s.flag_arrastre,
    s.duracion_min,
    s.comentario,
    s.nombre_archivo
FROM inventar_SpcHidr.Resumen_Intervalo_TotTM s;