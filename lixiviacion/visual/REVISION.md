# Segunda pasada DEV — 2026-10-05

Aplicación real `main.app` en servidor local temporal, Chrome headless y sesión Flask de prueba en memoria. No se modificó autenticación, SQL, datos ni PROD. Servidor detenido al finalizar. Evidencia automatizada: `review.json`.

## Resultado

- Smoke exacto OX/SULF/TOTAL PASS: todas las diferencias son cero. Referencias aprobadas, sin sumar subtotales redondeados.
- Período inicial 01-06-2026 → 10-09-2026.
- Navegación desde/hacia Reportabilidad, Reclamo, PowerBI, Monitoreo Correas y Lixiviación: secciones visibles correctamente. Esto comprueba navegación, no todos los procesos internos de las pantallas anteriores.
- Total: 6120 registros. KPIs visibles: flujo 12.168.556,400 m³; transferencia 30.136,222 t Cu; ΔCu promedio parcelas 1,206 g/L; 2062 registros fuera de ventana.
- Filtro PAD Óxidos: 3264 registros.
- Óxidos + FUERA_VENTANA_RIEGO: 1045 registros, conservados en tabla y KPIs.
- Filtros combinados Óxidos / Campaña 17 / Parcela 22: 4 registros, sin mensaje de error.
- Tabla renderizada con 25 filas por página; campaña NULL vacía, ceros numéricos visibles como 0,000. Tratamiento all-NULL como «Sin dato» y huecos en gráficos verificado por tests locales, no mediante modificación de datos DEV.
- Gráficos de flujo, química y transferencia renderizados. Etiquetas químicas distinguen promedio de parcelas de parcela individual.
- Sin errores JavaScript capturados.
- 7 tests locales PASS. `git diff --check` sin errores.

## Hallazgos visuales

Se corrigió la superposición de leyendas con títulos trasladando las leyendas debajo del área de datos. No se alteraron series ni valores.

A 900 y 520 px no se detectó desbordamiento horizontal del documento. La tabla dispone de desplazamiento horizontal. Sin embargo, el sidebar fijo y el encabezado global reducen mucho el espacio en móvil; hay títulos/leyendas de gráficos recortados. No se certifica una experiencia móvil plenamente resuelta ni se modifica el shell global en esta pasada.

El primer timeout de PAD correspondía al selector de la prueba; se restringió al dropdown y se esperó la actualización. Las capturas finales esperan también el fin de carga de la tabla.

## Evidencias

- `desktop.png`: período completo, KPIs, gráficos y tabla.
- `fuera_ventana.png`: estado fuera de ventana, campañas vacías y ceros.
- `responsive_900.png` y `responsive_520.png`: tamaños reducidos.

## Archivos de esta segunda pasada

- `lixiviacion/smoke_dev.py`, `SMOKE_DEV.json`: referencia y resultado exactos.
- `lixiviacion/panel.py`: período inicial y etiqueta de promedio de parcelas.
- `lixiviacion/callbacks.py`: etiquetas químicas según selección y posición de leyendas.
- `lixiviacion/test_lixiviacion.py`: expectativas de presentación y período inicial.
- `lixiviacion/README.md`: resultado actualizado.
- `lixiviacion/visual_review.py` y esta carpeta: revisión y evidencia.

`lixiviacion/db.py` y `layout.py` no se modificaron en esta segunda pasada. SQL SUM/AVG intactos. Sin commit/push.
