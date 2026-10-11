# Flujo de camiones

La fuente sincronizada es `control_reclamo_sulfuro_camiones_thm_diario`. Se suma `volumen_diario_m3` por fecha/PAD/campaña/módulo y se calcula `tms_thm = m3_thm × densidad_oficial`.

Problema estructural: el SP de sincronización solo inserta/actualiza `m3_thm` y `tms_thm`; `v_camiones_acumulado` consume `m3_oficial` y `tms_oficial`. No hay trigger y la búsqueda completa de módulos SQL no encontró escritor para esas columnas. Las 539 filas actuales sí están pobladas en ambos campos, por lo que hubo una carga fuera del flujo SQL activo observado. Las futuras actualizaciones de THM podrían dejar valores oficiales antiguos o `NULL`.

El acumulado se calcula desde el corte por campaña/módulo. Para cuadratura se suma además `m3_camiones_previo`, que proviene de movimientos anteriores al 2026-07-01.

