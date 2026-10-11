# Validación de contratos y botones

`validate.py` importó `main.app`, construyó `callback_map` (94 callbacks), inspeccionó el layout sin IDs duplicados y confirmó los Inputs de los botones principales. `cb_opciones_modulo` se ejecutó solo con un fixture en memoria: devolvió los dos PAD y mantuvo valores `11|1|15` y `11|2|16`. No invocó callbacks de escritura.

Inspección estática: Guardar e Insertar llaman solo a sus helpers de base; Reprocesar llama `db.recalcular`; Actualizar secuencia llama `db.mantener_secuencia`; Publicar confirmado llama `db.publicar`; Refrescar es Input de callbacks de consulta. La confirmación de Publicar sigue vigente. Los mensajes de Guardar e Insertar piden Reprocesar, pero no lo ejecutan.

Comprobaciones: `py_compile` PASS; `validate.py` PASS; 12 tests Reclamo existentes PASS (19 subtests); `git diff --check` PASS. En la vista previa local cargaron `/_dash-layout`, `/_dash-dependencies` y los paneles. Capturas `before/` y `after/` son de navegador de 1366 × 768 y página completa.

No se pulsaron acciones de escritura ni se ejecutaron SP de escritura.
