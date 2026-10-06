# Reclamo: flujo operacional visible (DEV, 2026-10-06)

Resultado: **RECLAMO_WORKFLOW_UI_PASS**. Se modificó únicamente `reclamo/panel.py` para orientar la operación; `reclamo/db.py`, los SP y las reglas de negocio no se cambiaron en esta tarea. El checkout ya contenía modificaciones anteriores en esos archivos; no se descartaron.

Capturas locales de 1366 × 768 (viewport, página completa): `before/` y `after/`. El servidor de vista previa ejecutó callbacks de lectura; la captura no pulsó Reprocesar, Actualizar secuencia, Guardar, Insertar, Registrar ajuste ni Publicar.

Ver `CAMBIOS_UI.md`, `DEPENDENCIAS_FILTRO_PAD.md`, `VALIDACION_SEMAFORO.md`, `VALIDACION_BOTONES.md` y `tests.json`.

Pendientes funcionales: bloqueo backend de Publicar basado en controles vigentes, distinción SQL de alertas activas frente a historial y mecanismo de aprobación de ajustes. El botón Publicar sigue habilitado; su `disabled=False` explícito prepara el componente para una fase posterior sin cambiar su conducta.

PROD intacto. Sin publicación, commit ni push.
