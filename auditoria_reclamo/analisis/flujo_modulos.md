# Congelamiento, línea base y secuencia

Congelar significa copiar una fotografía de TMS, m³ y densidad a `modulo_congelado`. La fuente oficial es `disponible_rotopalas`; `modulos_turnos` se usa solo como contraste. Si densidad falta o es cero, se deriva como TMS/m³.

La línea base usa movimientos estrictamente anteriores a `FECHA_CORTE_SISTEMA`: camiones suma `control_reclamo_sulfuro_camiones_thm_diario.volumen_diario_m3`; rotopala suma `control_reclamo_diario.volumen_diario_m3`. Normalmente solo se establece si está vacía.

La automatización detecta actividad en una ventana de 90 días, congela el módulo y hasta cinco siguientes con base disponible, define la secuencia y abre módulos con movimiento real hasta un máximo de dos por rotopala/campaña. En bootstrap prioriza la actividad más reciente.

Un módulo abierto se cierra si la cuadratura queda sobre 100,5 %, o si existen al menos dos módulos de número mayor con medición topográfica vigente. Abre el siguiente por `orden_secuencia`, nunca por `numero+1`.

Las fechas automáticas de cierre y apertura usan `CAST(SYSDATETIME() AS date)`, no la fecha operacional de la evidencia. Esto hace que un reproceso histórico ejecute transiciones con fecha de ejecución y cambie la elegibilidad temporal del preliminar CV025. Es un bug probable de reproducibilidad histórica.

Los cambios de campaña y fines de PAD no se resuelven automáticamente: generan alertas. La evidencia actual incluye cierres manuales masivos con observaciones que incluso mencionan “campaña 10” en filas cuyo `campaña_id` es 8, por lo que esas anotaciones requieren reconciliación operacional.

