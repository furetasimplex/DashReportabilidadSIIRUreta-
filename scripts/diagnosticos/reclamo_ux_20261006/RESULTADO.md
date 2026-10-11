# Control de Reclamo: revisión UX en DEV

## Cambio

La pantalla se organizó en cuatro pestañas: Resumen, Reclamo diario, Módulos y Ajustes y publicación. El filtro de período y PAD, el refresco y el reproceso permanecen visibles arriba. La publicación se ubicó al final del flujo, junto a su confirmación existente. Las tablas muestran nombres legibles y priorizan las columnas operativas; los formularios avanzados quedaron plegados.

El semáforo agrupa bloqueos, advertencias y controles OK. Los eventos históricos de automatización indican expresamente que pueden incluir repeticiones y ejecuciones pasadas. Los valores de origen CV25, topografía y excedente se presentan con etiquetas comprensibles. Las transformaciones son de presentación; se conservan los valores y consultas originales.

## Contrato técnico

`verify_ui.py` y `tests.json` comparan el inventario previo con el final: 74 IDs originales conservados, un ID nuevo (`reclamo-main-tabs`), cero IDs estáticos duplicados, 26 decoradores de callback sin cambios y 25 llamadas a `db` sin cambios. La app registra 26 callbacks, incluido el Input `btn-automatizacion.n_clicks`. `panel.py` compila y `git diff --check` no detectó espacios defectuosos.

## Evidencia visual

`before/` contiene las capturas previas a 1366 y 1920 px. Se tomaron con el preview local cuando el sandbox no permitía consultar DEV, por lo que algunos bloques muestran errores de conexión; documentan la estructura anterior. `after/` contiene las cuatro pestañas a 1366 y 1920 px y capturas móviles a 390 px, con lectura de datos de DEV. La vista se levantó en `127.0.0.1:8099` sin el contenedor de autenticación del sitio; no se pulsaron botones de escritura.

## Alcance

El diff de esta tarea corresponde a `reclamo/panel.py` y a esta carpeta de evidencia. `reclamo/db.py` ya tenía cambios anteriores y no se modificó en esta revisión UX. No se modificó SQL, SP, reglas, datos, ni PROD. No hubo publicación, commit ni push.
