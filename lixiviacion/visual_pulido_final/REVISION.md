# Pulido final UX

Cambios exclusivamente de presentación:

- Hitos: «Último riego registrado en campaña» y «Último drenaje registrado en campaña», sin cambiar columnas ni valores.
- Nota muted sobre extremos de campaña posteriores a la fecha seleccionada.
- Estados hidráulicos: fase y condición. Resto: estado operacional sin redundancia. Mixto aparece una sola vez.
- Composición en tabla Estado/Módulos, traducida con las etiquetas existentes de `map_states.py`. Store original intacto. Texto inesperado muestra «Composición no disponible», nunca códigos desconocidos.
- Tabs reordenadas: Mapa → Diagnóstico → Recomendador, mismos IDs y callbacks.

Archivos modificados: `lixiviacion/map_panel.py`, `lixiviacion/panel.py`, `assets/lixiviacion_map.css`, `lixiviacion/test_map.py`, `lixiviacion/visual_review.py`. Evidencias nuevas en esta carpeta.

Pruebas unitarias: **35 PASS**, incluidos los 27 casos previos con expectativas de presentación actualizadas. SQL Server no es requisito para tests unitarios. `git diff --check` sin errores.

Los seis casos visuales del 10-09-2026 coincidieron: OX P1/P29/P17, SULF P1/P7/P28. OX P1 y SULF P7 muestran «Riego + drenaje» tal como devuelve la fuente actual; no se reinterpretaron estados. Se conservan fechas futuras de campaña, incluida 01-10-2026 de drenaje en OX P1.

Capturas: `mapa_desktop.png`, `drawer_ox_p1.png`, `drawer_ox_p17.png`, `drawer_sulf_p1.png`. Resultados de Chrome en `review.json`.

El primer intento del smoke se detuvo por una expectativa antigua de mayúsculas/minúsculas en «COMPOSICIÓN»; se corrigió solo la prueba.

Repetición final Chrome headless: **PASS**, salida 0. Sin errores JavaScript ni callbacks HTTP fallidos, sin duplicados de callbacks observados. Drawer abre/cierra; tabs y navegación funcionan; Diagnóstico conserva consultas y Recomendador su mensaje. Sin overflow horizontal del documento, scroll interno del mapa conservado. Servidor temporal cerrado al finalizar.

Sin cambios SQL, DDL, fuentes, `map_db.py`, `map_states.py`, fase_visual, colores, cardinalidad, callbacks de datos, Diagnóstico funcional, Recomendador funcional, PROD, commit ni push.
