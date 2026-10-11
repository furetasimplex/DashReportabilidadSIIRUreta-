# Integración controlada DEV — timeline operacional de Diagnóstico

## Resultado final — 05-10-2026

Integración completada en DEV. 37/37 comparaciones exactas PASS: mismas 12 columnas y orden, hashes idénticos, cero diferencias bidireccionales, duplicados o reversas adicionales. OX P17 conserva las campañas 4/11 y SULF P28 las campañas 8/10 en los rangos evaluados. Los dos controles ampliados devuelven 253 filas idénticas. En esos controles se observaron 135,493 → 2,647 s (OX P1) y 135,140 → 3,328 s (SULF P7); son observaciones de equivalencia, no medianas de benchmark.

### Rendimiento de la consulta integrada

| 102 días | Baseline12 mediana s | Runtime12 mediana s | Speedup | Logical reads antes | Logical reads después | Reducción IO |
|---|---:|---:|---:|---:|---:|---:|
| OX P1 | 50,8707 | 0,9464 | 53,75× | 22.166.901 | 729.933 | 96,71% |
| SULF P7 | 50,5831 | 1,3428 | 37,67× | 22.166.901 | 1.195.083 | 94,61% |

Las 30 mediciones del SQL exacto importado, sus CPU/elapsed, lecturas y min/mediana/max para 1/7/31/62/102 días están en [benchmark_tablas.md](diagnostico_timeline_runtime/benchmark_tablas.md). Ninguna ejecución normal de 102 días superó 5 s. Los dos planes reales se capturaron aparte: 1,664 y 1,862 s con instrumentación XML, excluidos de las medianas.

Planes: DOP físico 1; nodos de la familia opuesta presentes en el plan genérico pero con cero ejecuciones/filas leídas. Persiste el trabajo repetido de extremos por expansión de CTE; no se intervino. El optimizador informa `TimeOut`, `PlanAffectingConvert` y `Excessive Grant` (3.904 KB concedidos, 40 KB usados). Estos avisos no son fallos de ejecución. Evidencia completa: [planes_analizados.json](diagnostico_timeline_runtime/planes_analizados.json) y [plans/](diagnostico_timeline_runtime/plans/).

### Callback, regresión y navegador

| Caso | Cabecera SQL s | Timeline SQL s | Resto callback s | Callback total s | Clic → cabecera s | Clic → timeline s |
|---|---:|---:|---:|---:|---:|---:|
| OX P1 | 0,094 | 1,035 | 0,188 | 1,317 | 3,182 | 3,182 |
| SULF P7 | 0,093 | 1,323 | 0,189 | 1,605 | 4,094 | 4,094 |

OX P17: clic → cabecera/timeline 3,807 s. SULF P28: 3,582 s. Cabecera y timeline llegan juntos en el mismo callback; los tiempos del navegador incluyen además las consultas físicas V2, transporte y render. No se presenta el tiempo SQL aislado como latencia total de pantalla.

Invariancia PASS en general + siete parcelas: cuatro KPI idénticos, JSON de los tres gráficos idéntico y todas las filas de DataTable idénticas. `python -m pytest lixiviacion -q`: **63 PASS** (56 anteriores + 7 nuevos). `python -m lixiviacion.smoke_diagnostic_dev`: **PASS** general + siete parcelas, sin cambiar expectativas. El resultado nuevo se guardó en [smoke.json](diagnostico_timeline_runtime/smoke.json) y se restauró el artefacto histórico original.

Chrome headless: **PASS** general, OX P1/P17, SULF P7/P28, retorno al mapa y recomendador; cero errores JavaScript/callback HTTP. Capturas revisadas en [visual/](diagnostico_timeline_runtime/visual/). Cabecera, timeline, gráficos y tabla se renderizan en desktop. En móvil de 520 px no hay overflow del documento, pero el sidebar deja poco ancho: título/leyenda de química se recortan y la tabla exige desplazamiento interno. Se documenta esta limitación visual; no se modifica shell/CSS por estar fuera del alcance. OX P17 muestra `-0,000` en transferencia por su valor negativo pequeño: formato actual preservado, no introducido por el timeline.

`git diff --check`: **PASS**, con aviso de conversión futura LF→CRLF en `layout.py`, archivo preexistente sin cambios en esta tarea. Como `lixiviacion/` ya estaba sin seguimiento en Git, el diff exacto de runtime se entrega en `runtime.diff`. El control AST verifica que no cambió ninguna otra asignación/función de db.py. Hashes confirman callbacks, panel, mapa, layout, CSS y smoke sin cambios. Durante la fase functional se actualizaron tests, por eso su hash global registra actividad; el hash de db.py se verificó intacto antes de integrar. Véase [integrity_final.json](diagnostico_timeline_runtime/integrity_final.json).

Archivos funcionales: únicamente `lixiviacion/db.py:OP_TIMELINE_SQL`. Pruebas: `test_diagnostic_operational.py` (dos aserciones de implementación) y nuevo `test_timeline_runtime.py`. El resto son respaldo, harness y documentación en la carpeta de evidencia. Rollback preparado, no ejecutado; no se realizaron DDL/DML ni cambios de objetos SQL, PROD, commit o push.

## Cambio y contrato

Único archivo runtime modificado: `lixiviacion/db.py`, únicamente la asignación `OP_TIMELINE_SQL`. La cabecera continúa usando la función diaria oficial. Helpers, callbacks, panel, mapa, CSS y consultas V2 permanecen intactos.

Se extrajeron automáticamente nombres/orden/aliases del SQL anterior y se seleccionaron esas mismas12 columnas de la proyección del candidato genérico. No se copió el contrato24 al runtime. Se conservaron parámetros SQLAlchemy, CTE, CASE, umbrales y NULL del candidato; no se agregó caché, materialización, índices ni una segunda optimización.

Evidencia: [contrato y hash](diagnostico_timeline_runtime/contract.json), [SQL anterior](diagnostico_timeline_runtime/OP_TIMELINE_SQL_before.sql), [SQL runtime12](diagnostico_timeline_runtime/candidate_runtime_12.sql), [diff exacto](diagnostico_timeline_runtime/runtime.diff).

## Equivalencia

Comparación bidireccional exacta antes de editar runtime: siete parcelas ×cinco rangos (1/7/31/62/102 días), más OX P1 y SULF P7 desde01-01 a10-09-2026. Se comparan todas las columnas, nombres/orden, duplicados, campañas, NULL, hashes y reversas dentro de campaña. No se normalizan resultados ni se deduplican.

Resultados detallados en [comparacion.json](diagnostico_timeline_runtime/comparacion.json). OX P17 y SULF P28 son los controles explícitos multicampaña. Los IDs se resuelven desde la función oficial, no suponiendo igualdad con el número de parcela.

## Benchmark runtime12 y planes

Se mide el texto importado realmente de db.py, verificando igualdad con candidate_runtime_12.sql. Tres ejecuciones de cada rango en OX P1/SULF P7. CPU/elapsed e IO completos en `statistics_io_time/`; capturas XML reales102d separadas de las medianas.

No se reutilizan tiempos del candidato24. Se comparan con baseline12 previo y se conservan además las ejecuciones actuales del SQL anterior en functional_timings.json. Primera observada no significa caché fría; no se controla carga ajena del servidor.

## Callback y V2

Se perfila `callbacks.load_operational` real con wrapper temporal de conexión, sin logging permanente. Se separan cabecera, timeline y resto. Fetch incluye espera de SQL; no se atribuye todo su tiempo a transformación Python.

Invariancia de4 KPI,3 figuras y todas las filas de DataTable para general +7 parcelas mediante snapshots antes/después. Se conservan KPI y hashes de JSON/filas. Esto se complementa con prueba AST que comprueba que únicamente cambió la asignación timeline.

## Tests y smoke

Suite previa:56 PASS. Se agregan tests de contrato12, parámetros, ausencia de llamada diaria, CASE/NULL, comparación exacta, multicampaña y alcance exclusivo de la asignación. La prueba existente de aislamiento del error operacional conserva su expectativa funcional. Solo se actualizan sus aserciones ligadas al antiguo CROSS APPLY, incompatible con la implementación autorizada.

El smoke solicitado se ejecuta sin cambiar expectativas de negocio para general +7 parcelas. Su informe se conserva en la carpeta de esta integración; el snapshot histórico no se redefine para obtener PASS.

## Chrome y experiencia

Revisión con Chrome headless y aplicación DEV local: general, OX P1, OX P17, SULF P7, SULF P28 y móvil. Harness derivado del anterior, con misma navegación y capturas. La sesión de prueba es local/temporal y el servidor se apaga al finalizar.

El tiempo clic→cabecera/timeline usa reloj del navegador desde el evento real de Consultar hasta detectar identidad nueva y gráfico renderizado con102 puntos. Incluye V2, callback, transporte y render, no solo SQL. Se registra una observación por caso; no es SLA. Capturas y resultados en [visual/](diagnostico_timeline_runtime/visual/).

## Rollback y límites

[ROLLBACK.md](diagnostico_timeline_runtime/ROLLBACK.md) restaura únicamente OP_TIMELINE_SQL mediante un comando con guardia contra cambios posteriores. El respaldo completo db_before.py y su SHA256 se guardaron antes de editar.

El recálculo residual por expansión de CTE queda documentado, sin optimizarse en esta integración por instrucción expresa. La equivalencia se demuestra en los datos medidos, no en toda combinación futura. No se ejecutaron DDL/DML, cambios de objetos SQL/índices/estadísticas ni acciones sobre PROD. Sin commit ni push.
