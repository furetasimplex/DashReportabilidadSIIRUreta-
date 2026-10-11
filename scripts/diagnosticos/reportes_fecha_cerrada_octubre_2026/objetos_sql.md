# Objetos de resolución

| Objeto | Papel / filtros / dependencia |
|---|---|
| inventar_SpcHidr.tot_TM | MAX(fecha) global; no filtro de mes, turno ni torre. Es horizonte temporal, no chequeo de huecos o valores por canal. |
| inventar_SpcHidr.v_bitacora_rangos_norm | fecha_turno inclusiva start/end, Torre IN T1/T2/SRR; GROUP BY fecha_turno y MAX(ts_fin). |
| inventar_SpcHidr.v_bitacora_rangos | Mapea fecha_calendario a fecha_turno y ts_toma_muestra a ts_fin; calcula LAG por torre para ts_ini. |
| inventar_SpcHidr.bitacora_turnos_consolidada | Fuente de torre, turno, fecha_calendario y ts_toma_muestra; excluye timestamp de muestra NULL. |

Definiciones LIVE guardadas. `LAG` puede leer la toma del día anterior para ts_ini/duración, pero el corte no usa ts_ini, duracion_min ni flag_arrastre. Por tanto no establece prerrequisito de cierre completo septiembre→octubre. No hay control de cierre persistido, EOMONTH, seed previo, cache, apilado, analitos o COUNT de A/B en ESTE SELECT.

Objetos/funciones posteriores, NO ejecutados al fallar corte: coordinador `refrescar_dependencias_reporte_turno_emision`; `sp_calcular_resumen_intervalo_totTM`, `sp_refrescar_representatividad_torres`, `sp_sincronizar_bd_ton`, todos hasta corte e inicio mensual. Locks `sp_getapplock`/`sp_releaseapplock` protegen la transacción, no definen disponibilidad temporal. Fuentes mensuales y comentarios/snapshot oficial se leen después del refresco. No se atribuye a estos objetos la primera condición fallida ni se ejecutaron para investigar.
