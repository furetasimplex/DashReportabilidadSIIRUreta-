# Contratos y verificación

- 75 IDs estáticos, incluidos los 74 originales y `reclamo-main-tabs`; sin duplicados.
- 26 decoradores de callback sin cambios; 26 entradas en `app.callback_map`; `btn-automatizacion.n_clicks` presente.
- Hay una nueva lectura del catálogo de campañas tras la ejecución de automatización para etiquetar el resultset del SP. No modifica su resultado ni los parámetros del SP. Las otras ampliaciones de `db.py` son columnas de presentación obtenidas con `OUTER APPLY` read-only.
- `validate_reads.py` ejecutó las siete lecturas modificadas en DEV: cuadratura 85 filas, avance 48, preview 32, ajustes 0, módulos 85, alertas 274, rendimiento 12; sin errores y sin campañas faltantes en los conjuntos no vacíos.
- `test_ux.py` cubre mapeo 4→17, valores internos de dropdown/editor, IDs ocultos, matriz de dos campañas con M33, estado, fecha, número local, IDs Dash, callbacks y compilación. Resultado en `tests.json`.
- `git diff --check` se ejecutó al cierre. Las capturas `before/` son la salida de la primera fase UX, y `after/` se obtuvieron de la vista local con lecturas DEV a 1366 y 1920 px. No se pulsaron botones de escritura.

Pendientes funcionales, sin implementar: decidir cómo tratar el contador histórico en el semáforo, definir criterio para brechas CV25 con denominador pequeño, revisar los dos registros preliminares de tonelaje cero, y decidir si Publicar debe deshabilitarse ante bloqueos reales. El filtro inicial de datos base queda en «Todas» porque no se demostró una regla única de campaña relevante.
