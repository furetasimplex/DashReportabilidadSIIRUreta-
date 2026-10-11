# Auditoría de rendimiento — DEV

Solo medición. No ejecutar los snapshots de definición como DDL. No se modifican objetos, datos, índices, estadísticas ni runtime.

Auditoría completada: 85 mediciones en la matriz (45 timeline normales, 3 calendario, 12 directas/cabecera, 4 capturas reales y 21 sondas), más la prueba inicial conservada y dos perfiles del callback. Ver [informe principal](../DIAGNOSTICO_PERFORMANCE.md), [hallazgos](hallazgos.md) y [tablas](mediciones_tablas.md).

## Captura

- `audit.py`: ejecuta secuencialmente el SQL literal importado de `lixiviacion.db.OP_TIMELINE_SQL`, enlazado por SQLAlchemy/ODBC con los mismos parámetros. Guarda mensajes completos STATISTICS IO/TIME por ejecución y planes reales en pruebas separadas. STATISTICS XML no está activo durante las tres repeticiones de la matriz principal.
- `timeline_actual.sql`, `cabecera_actual.sql`: copias textuales del runtime; `calendar_only.sql` y `single_day.sql`: controles de medición separados, no sustituciones del runtime.
- `mediciones.json`: cada repetición, parámetros reales, filas devueltas, tiempo cliente execute/fetch, todos los pares CPU/elapsed emitidos (compilación y ejecución separados en el texto original), IO por objeto.
- `statistics_io_time/`: mensajes completos del driver. `plans/`: XML completo, sin truncar. La extensión `actualplan` se usa solo para XML devuelto por SET STATISTICS XML ON después de ejecutar.
- `indices.json`, `estadisticas.json`, `dmv_query_store.json`, `metadata_supplement.json`: lecturas de catálogo, estadísticas y candidatos de consultas; no se activa Query Store.
- `python_profile.json`: construcción de figura y serialización de cada resultado ya recuperado; no incluye render DOM del navegador.
- `supplement.py`: llama el callback real con un wrapper temporal en memoria para cronometrar execute/fetch; no escribe logging ni modifica archivos runtime. `callback_profile.json` documenta esos tiempos.
- `analyze.py`: análisis local de XML y agregación min/mediana/max. Genera `resumen.json` y `planes_analizados.json`.
- `tables.py` y `plan_tables.py`: tablas locales de mediciones y operadores; no conectan a SQL. Los JSON de metadatos principales conservan la estructura de resultsets del driver (lista de listas).

## Método y límites

Fecha fin 10-09-2026. Rangos inclusivos 1, 7, 31, 62, 102 días para OX P1/SULF P7. Los otros cinco casos usan 102 días. Tres repeticiones secuenciales; se conserva la primera observada. No se vacían caches, no se usan hints nuevos ni se altera MAXDOP. MAXRECURSION 32767 es parte del SQL original.

Las fechas iniciales se calculan como fecha fin menos (días−1): para 62 días corresponde **11-07-2026**. Se resuelven IDs desde la función oficial, no a partir del número de parcela. Los resultados completos no se guardan.

Las pruebas de `COUNT_BIG(*)` de fuentes son sondas de acceso/tamaño, no reproducciones de las ramas de extremos: el optimizador puede simplificarlas. No sumarlas como si fueran tiempos independientes de cada CTE de la función. Los tiempos inclusivos de operadores tampoco deben sumarse: padres e hijos se superponen.

Primera ejecución observada no significa caché fría. Existe actividad previa del mismo módulo y no se controla carga ajena del servidor. No se ejecutan consultas V2 aparte del JOIN de la cabecera; no se abre Dash/browser durante la matriz para evitar interferencia de esta auditoría.

Los planes reales añaden instrumentación y transmisión XML; sus tiempos cliente no se incorporan a la mediana de las tres repeticiones sin XML. Las estadísticas IO/TIME también añaden alguna instrumentación. El perfil posterior del callback se realiza sin esos SET activos.

`runtime_before.json` / `runtime_after.json` acreditan hashes de archivos Python runtime y CSS. Los scripts de esta carpeta son herramientas de auditoría independientes del flujo de la aplicación.
