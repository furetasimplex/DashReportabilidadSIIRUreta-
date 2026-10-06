# Rendimiento del timeline operacional de Diagnóstico — DEV

Auditoría del 05-10-2026. Solo medición y documentación; no es una propuesta implementada.

## 1. Resumen ejecutivo

El timeline de 102 días tarda aproximadamente **51 segundos** para devolver 102 filas de una parcela. El costo crece casi linealmente con las fechas y es similar entre PAD/parcelas. Los mensajes de SQL muestran millones de lecturas lógicas repetidas, principalmente de drenaje OX/SULF, aun seleccionando una única parcela.

## 2. Consulta actual

La copia literal de `lixiviacion.db.OP_TIMELINE_SQL` está en [timeline_actual.sql](diagnostico_performance/timeline_actual.sql). Se mantuvieron proyección, CTE recursivo, CROSS APPLY de la función oficial, filtros exteriores PAD/parcela, orden y MAXRECURSION 32767. No se ejecutaron variantes con hints.

## 3. Metodología de medición

Tres ejecuciones secuenciales por caso, con STATISTICS IO/TIME; planes reales en ejecuciones adicionales separadas con STATISTICS XML. No se limpiaron caches, no se cambió compatibilidad/MAXDOP ni se actualizaron estadísticas. La primera es la **primera observada**, no necesariamente fría. Los tiempos cliente incluyen execute/fetch y red.

Fin común 10-09-2026; inicios 10-09, 04-09, 11-08, 11-07 y 01-06 para 1/7/31/62/102 días inclusivos. Los IDs se resolvieron mediante la función oficial: OX P1/P17/P29 = 1/17/29; SULF P1/P7/P9/P28 = 33/39/41/60. Evidencia: [identities.json](diagnostico_performance/identities.json).

Cada resultado timeline se verificó contra días esperados, fechas únicas e identidad PAD/parcela. No se rellenaron días ni se alteraron NULL. No se guardaron datasets masivos. Para el método reproducible y sus límites véase [README](diagnostico_performance/README.md).

## 4. Resultados por rango

Medianas cliente en segundos:

| Días | OX P1 | SULF P7 | UX observada |
|---:|---:|---:|---|
| 1 | 0,544 | 0,629 | Instantánea |
| 7 | 3,480 | 3,536 | Perceptible |
| 31 | 15,469 | 15,315 | Muy lenta (una repetición SULF: 14,904 s) |
| 62 | 31,418 | 30,687 | Muy lenta |
| 102 | 50,871 | 50,583 | Muy lenta |

La pendiente observada ronda 0,5 s/día. Las lecturas escalan de 217.317 a 22.166.901; no se impone un SLA ni se extrapola una garantía fuera de estos rangos.

Las tres repeticiones, min/mediana/max, CPU, elapsed y lecturas están en [mediciones_tablas.md](diagnostico_performance/mediciones_tablas.md) y [mediciones.json](diagnostico_performance/mediciones.json).

## 5. Resultados por parcela/PAD

| Caso | ID PAD / parcela | Mediana 102 días s |
|---|---|---:|
| OX P1 | 1 / 1 | 50,871 |
| OX P17 | 1 / 17 | 51,253 |
| OX P29 | 1 / 29 | 50,894 |
| SULF P1 | 2 / 33 | 50,878 |
| SULF P7 | 2 / 39 | 50,583 |
| SULF P9 | 2 / 41 | 51,334 |
| SULF P28 | 2 / 60 | 50,909 |

Las lecturas lógicas a 102 días son idénticas en los siete casos y sus repeticiones. La diferencia entre medianas es pequeña respecto de los ~51 s totales.

Se midieron las siete parcelas solicitadas a 102 días; todas devolvieron 102 filas únicas. Los detalles y parámetros exactos están en las mediciones enlazadas.

## 6. Primera vs ejecuciones posteriores

No aparece una reducción sostenida e importante después de la primera ejecución. Por ejemplo OX P1 102 días: 50,282 / 50,871 / 51,159 s; SULF P7: 51,350 / 50,583 / 50,581 s. No se atribuye esa variación a caché fría/caliente ni se descarta la primera.

## 7. STATISTICS IO

OX P1, 102 días, primera observada: **22.166.901 lecturas lógicas**. Drenaje OX 9.209.070 y SULF 8.372.160 dominan; flujo OX 1.816.620 y SULF 1.395.360; CPC 1.057.718; Worktable 192.757; parcela 98.736; PAD 24.480. En esa ejecución physical y read-ahead son cero. Las lecturas son accesos a páginas, no páginas únicas ni tamaño residente.

Los mensajes completos por caso se conservan en [statistics_io_time/](diagnostico_performance/statistics_io_time/). La tabla detallada incluye scan count; no se interpreta automáticamente como cantidad de ejecuciones del operador, especialmente con seeks.

## 8. STATISTICS TIME

OX P1 102 días: CPU 50.188 / 50.719 / 51.078 ms; elapsed SQL 50.180 / 50.782 / 51.108 ms. SULF P7: CPU 51.296 / 50.532 / 50.468 ms; elapsed 51.308 / 50.539 / 50.470 ms. CPU cercana a elapsed, plan serial y lecturas físicas cero apoyan un costo de procesamiento repetido sobre páginas en buffer, no una conclusión de espera dominante por disco.

Los tiempos de compilación y ejecución están separados en los mensajes originales. Las tablas resumen el último par de ejecución; no suman compilación como si fuera CPU de ejecución. Los tiempos de captura/transmisión XML se excluyen de las medianas principales.

## 9. Plan real/estimado

Se capturaron **planes reales**, no estimados: [OX P1](diagnostico_performance/plans/timeline_102d_ox_p1_actualplan.sqlplan) y [SULF P7](diagnostico_performance/plans/timeline_102d_sulf_p7_actualplan.sqlplan). Ambos tienen QueryHash `0xDC6F7FA1FB43E983`, PlanHash `0x75F647FB677DE496`, CE 140 y costo estimado 9,29993 (unidad interna del optimizador, no segundos). Raíz física Compute Scalar, seguida de Filter. Ambos se recuperaron de caché; compilación registrada 202 ms.

DOP real 1; cero operadores Parallelism. Grant solicitado/concedido 11.600 KB; máximo utilizado 1.936 KB; espera de grant 0. No aparecen avisos de sort/hash spill ni sugerencias MissingIndexes. Existen spools y lecturas Worktable; no equivalen por sí solos a spills. No se capturaron páginas de tempdb asignadas por sesión, por lo que no se afirma consumo cero de tempdb.

Warnings: `PlanAffectingConvert` sobre `CONVERT_IMPLICIT(varchar(12),[Expr1595],0)` en la composición STRING_AGG, y `StatementOptmEarlyAbortReason=TimeOut`. Este último limita la búsqueda del optimizador; no indica timeout de ejecución. No hay evidencia de que esa conversión aislada sea el cuello principal.

WaitStats XML OX/SULF: SOS_SCHEDULER_YIELD 54/56 ms, MEMORY_ALLOCATION_EXT 55/56 ms, RESERVED_MEMORY_ALLOCATION_EXT 85/87 ms. No son una captura general de waits del servidor. QueryTimeStats instrumentado: OX elapsed/CPU 69.410/69.406 ms y SULF 70.735/70.732 ms. Instrumentación de plan incrementa el tiempo frente a las repeticiones sin XML; no usar esos ~70 s como mediana UX.

## 10. Operadores costosos

Inventario de cada timeline: Nested Loops 42, Hash Match 6, Sort 21, Stream Aggregate 28, Window Spool 7, Index Spool 3, Table Spool 3, Clustered Index Scan 19, Clustered Index Seek 13, Index Seek 3, Compute Scalar 48, Segment 14, Sequence Project 7, Concatenation 1, Filter 25, Constant Scan 14 y Assert 1. No aparecen Merge Join, Key Lookup, Table Scan, operador Sequence independiente ni Parallelism. La recursión se representa mediante Concatenation + spools + Assert, no un operador llamado literalmente Recursive Union.

La rama bajo Table Spool 15 ejecuta 102 veces y produce 6.120 filas. Los loops correlacionados disparan actividad diaria y extremos para múltiples parcelas. En OX, scan 175 (drenaje histórico) lee 4.533.696 páginas y scan 198 (SULF) 4.112.640; sus tiempos inclusivos son 6.177 y 5.791 ms. También hay trabajo en filtros/unpivot, agregados y loops padres; no sumar tiempos de padres/hijos. El costo real no se reduce a un único sort.

Extracto completo con nodo/padre, estimaciones, ejecuciones, filas y IO: [operadores_planes.md](diagnostico_performance/operadores_planes.md). XML y [planes_analizados.json](diagnostico_performance/planes_analizados.json) conservan predicados y contadores completos.

## 11. Cardinalidad estimada vs real

Nodos del plan OX (misma estructura SULF):

| Nodo / operador | Est filas por ejecución | Real total | Ejecuciones | Real por ejecución | Ratio real/est |
|---|---:|---:|---:|---:|---:|
| 1 Filter final | 11,5043 | 102 | 1 | 102 | 8,87 |
| 2 Nested Loops calendario/función | 449,1 | 6.120 | 1 | 6.120 | 13,63 |
| 3 Sort calendario | 4 | 102 | 1 | 102 | 25,5 |
| 15 Table Spool rama diaria | 112,275 | 6.120 | 102 | 60 | 0,53 |
| 19 Stream Aggregate resumen | 1 | 6.120 | 102 | 60 | 60 |
| 129 Scan flujo OX histórico | 3.774 | 12.318.336 | 3.264 | 3.774 | 1 |
| 175 Scan drenaje OX histórico | 4.141 | 13.516.224 | 3.264 | 4.141 | 1 |

Las estimaciones fallan en calendario y consolidación, pero los scans históricos pueden estimar correctamente **cada ejecución** y aun así ser costosos por repetición. No atribuir su total de millones de filas a un error de estimación por ejecución. Compute Scalar sin contadores no significa ausencia de trabajo: puede evaluarse de forma diferida.

## 12. Comportamiento inline TVF

La definición está expandida: el plan contiene tablas base, lógica de estados, agregados y ventanas, sin operador TVF opaco. El **Filter 1** contiene exactamente `p.id_pad=@P3 AND p.id_parcela=@P4`; su hijo Nested Loops 2 produce 6.120 filas antes de reducirlas a 102. Por tanto se procesa internamente el universo de 60 parcelas por fecha en esta forma de consulta.

La fecha sí correlaciona las ramas: los scans diarios tienen filtros de fecha convertida/operacional, pero sobre scans; no se consigue un acceso limitado temprano a una sola parcela. Cada fuente física aparece en tres scans: actividad interna por parcela, extremos históricos y actividad de la salida. Flujo/drenaje OX: 3.264 + 3.264 + 102 ejecuciones; SULF: 2.856 + 2.856 + 102, aun al seleccionar OX P1.

Los extremos se recalculan: Stream Aggregate 109 expresa MIN/MAX de fecha; su rama OX 129 recorre 3.774 filas históricas en cada una de 3.264 ejecuciones. Drenaje OX 175 recorre 4.141 y SULF 198 4.291; las ventanas se filtran después en la rama. CPC 107 recorre 978 filas por ejecución, 6.120 veces; CPC 127/150/173/196 y Window Spool/LEAD reaparecen en ramas de extremos. Es evidencia de redescubrimiento de contexto, no solo una hipótesis basada en el texto.

La definición oficial leída en esta auditoría queda en [funcion_instalada_snapshot.sql](diagnostico_performance/funcion_instalada_snapshot.sql), exclusivamente como evidencia, no como DDL ejecutable de esta tarea.

## 13. Costo calendario

COUNT del calendario102: 0,037 / 0,040 / 0,038 s cliente; CPU/elapsed SQL 0 ms reportados (resolución de medición), 614 lecturas Worktable. Devuelve una fila de conteo, cuyo valor es 102; no significa que generase una fecha. Es insignificante frente a ~51 s y 22 millones de lecturas. No justifica reemplazar el CTE como primera solución.

## 14. Costo una sola fecha y cabecera

| Consulta | Mediana cliente OX P1 s | Mediana cliente SULF P7 s | Lecturas OX / SULF |
|---|---:|---:|---:|
| Función directa 10-09 | 0,056 | 0,178 | 5.228 / 5.383 |
| Cabecera 10-09 | 0,068 | 0,098 | 9.009 / 9.044 |
| Timeline de 1 día | 0,544 | 0,629 | 217.317 / 217.317 |
| Timeline de 102 días | 50,871 | 50,583 | 22.166.901 / 22.166.901 |

El timeline102 no equivale a 102 llamadas directas (aproximadamente 5,7 s OX y 18,2 s SULF usando medianas cliente, comparación orientativa, no un benchmark de ese diseño). Sí escala aproximadamente con el costo de **un día dentro del plan timeline**. La llamada directa permite un plan mucho más selectivo; no es correcto multiplicar su costo por 102 y atribuir el resto al calendario. En SULF la variabilidad/red es visible: elapsed SQL directo 16/21/21 ms frente a cliente 178/199/97 ms.

Los planes reales directos están en `plans/single_1_actualplan.sqlplan` y `single_2_actualplan.sqlplan`; no se mezclan sus tiempos XML con las tres mediciones normales. La cabecera incluye V2, pero su costo observado es pequeño. No se lanzaron consultas de gráficos/KPI V2 en paralelo durante la matriz.

## 15. Fuentes dominantes

Las sondas COUNT_BIG de las siete fuentes son lecturas separadas de acceso/tamaño, no una reconstrucción de la lógica. El optimizador puede simplificarlas: no equivalen al costo de los extremos hidráulicos y no deben sumarse para explicar el timeline. Para atribuir el cuello de botella se usa IO de la consulta exacta y sus planes reales.

## 16. Índices, estadísticas y Query Store/DMV

Inventario completo de claves/include/unicidad/tipo/filtro: [indices.json](diagnostico_performance/indices.json). Drenaje OX/SULF tienen solo PK clustered por `id_registro`; flujo OX/SULF, PK clustered por `id_flujo_real`. CPC ya tiene `IX_cpc_pad_parcela_fechas(pad_id,parcela_id,fecha_ini_carguio,fecha_fin_retiro)`, `IX_cpc_campana(campana_id,modulo_id,parcela_id)`, PK y varias unicidades de campaña/parcela/módulo. Parcela tiene PK y unicidades PAD/nombre y PAD/número. No se encontraron include ni filtros en estos índices. No se concluye automáticamente que falta un índice; además hay conversiones de fecha y unpivot en los predicados.

Filas base del catálogo: CPC 980, flujo OX/SULF 3.774 cada una, drenaje OX 4.141/SULF 4.291, PAD 2 y parcela 60. Las vistas largas tienen más filas por expansión, documentadas en `metadata_supplement.json`.

[estadisticas.json](diagnostico_performance/estadisticas.json) conserva fecha, muestra, filas y contador por estadística. CPC tiene estadísticas desde marzo hasta 05-10; la PK registra 741 filas y 487 modificaciones, frente a 980 filas actuales; `IX_cpc_pad_parcela_fechas` registra 930/48. También hay autoestadísticas recientes. Flujo SULF tiene autoestadísticas de junio (muestras 3.638/3.656; hasta 738 modificaciones); OX incluye agosto. Drenaje incluye estadísticas de agosto y de 02-10. Algunas PK de flujo reportan propiedades NULL: no convertirlo en cero ni atribuirlo a permisos sin evidencia. Son señales a revisar, no prueba de causalidad ni autorización para UPDATE STATISTICS.

Query Store: OFF; sin registros coincidentes en su consulta. La búsqueda acotada en caché con texto y `t.dbid=DB_ID()` no devolvió filas; esto **no demuestra que no haya plan en caché** (los XML indican RetrievedFromCache=true). No se dispone de un histórico DMV confiable de execution_count/promedios para informar; se usan las mediciones controladas. En los dos planes capturados hay un único PlanHash observado, sin afirmar que sea el único del servidor.

## 17. SQL vs Python

Sobre las 45 mediciones timeline, construcción figura: mediana 0,0549 s, rango 0,0348–0,3968 s; serialización figura: mediana 0,00493 s, rango 0,00212–0,02457 s. Se conservó la primera construcción. Evidencia [python_profile.json](diagnostico_performance/python_profile.json). Son tiempos Python, no render DOM/Plotly en navegador.

Perfil adicional del callback real sin STATISTICS, mediante wrapper temporal de conexión en memoria:

| Caso | Callback total s | Cabecera execute+fetch s | Timeline execute+fetch s | Resto callback s | Serialización componente s |
|---|---:|---:|---:|---:|---:|
| OX P1 | 52,016 | 0,111 | 51,168 | 0,737 | 0,010 |
| SULF P7 | 52,078 | 0,205 | 51,606 | 0,267 | 0,005 |

Detalle en [callback_profile.json](diagnostico_performance/callback_profile.json). La serialización componente se midió después del total callback. `fetch/mappings` tarda ~25 s porque incluye espera por resultados pendientes del servidor; **no son 25 s de transformación Python**. El resto callback incluye conexión/contextos, figura y componentes, no solo CPU Python. No se instaló logging permanente ni se instrumentaron archivos runtime.

## 18. Diagnóstico del cuello de botella

**Confirmado en los planes medidos:** filtrado PAD/parcela posterior a 60 parcelas × fechas, expansión inline repetida, scans de ambas familias de fuentes y recálculo de contexto/extremos históricos. Drenaje aporta ~79,3% de las lecturas y flujo ~14,5%; CPC ~4,8%. La CPU se acumula en scans, filtros/unpivot, loops y agregaciones repetidas.

**Contribuyentes posibles, no aislados experimentalmente:** estimación insuficiente de calendario/resumen y límite de búsqueda del optimizador. **No respaldados como causa principal:** calendario, serialización Python, volumen de salida (102 filas), spill, espera de memory grant o latencia de cabecera. No se atribuye todo a una estadística o a un índice ausente sin un experimento posterior autorizado.

## 19. Familias de optimización posibles — no implementadas

| Opción | Cuello de botella que abordaría | Riesgo funcional / operacional | Complejidad | DDL | Contrato |
|---|---|---|---|---|---|
| Ruta/TVF de rango con PAD/parcela explícitos | Trabajo sobre parcelas ajenas y evaluación diaria repetida | Alto cuidado con ventanas, estados MIXTO y NULL; validar carga/plan en DEV | Alta | Sí si se publica objeto nuevo | Puede preservarse; requiere comparación exhaustiva |
| Separar contexto de campaña/extremos de actividad diaria | Recalcular ventanas y extremos históricos por fecha | No recortar extremos al rango visible; invalidación ante datos tardíos si se persiste | Alta | Según implementación | Puede preservarse si mantiene toda la ventana y hitos |
| Revisar accesos e índices de tablas base con predicados reales | Scans repetidos y filtros sobre conversiones/unpivot | Índices añaden escritura y espacio; no garantizan resolver el trabajo repetido | Media | Sí | Sin cambio lógico esperado; validar antes/después |
| Caché de aplicación o materialización controlada | Latencia de lecturas repetidas del mismo rango | Resultados obsoletos ante cambios CPC/flujo/drenaje; requiere invalidación confiable | Media/alta | No caché app; sí materialización SQL | Solo si asegura frescura y conserva NULL/estados |

## 20. Recomendación para la siguiente fase

Diseñar y comparar un candidato DEV que limite temprano PAD/parcela y reutilice contexto/extremos sin cambiar la ventana. Es una recomendación para experimentar, **no una solución aprobada ni implementada**. Cambiar solo el calendario o unir cabecera y timeline no aborda por sí mismo las lecturas dominantes.

Cualquier candidato debe preservar exactamente fechas, filas, PAD/parcela, campaña operacional, estados (incluido MIXTO), composición cuando aplique, flags, NULL, calidad, hitos, ventana, extremos y cero reversas terminales. Comparar resultados completos en ambas direcciones y conservar los casos funcionales previos; no aceptar rapidez mediante cambio de resultados.

## 21. Límites de evidencia y restricciones

Una sesión DEV y una ventana de datos; sin control de carga concurrente del servidor ni caches. La instrumentación agrega costo. No se midió render DOM del navegador. No se extrapolan mediciones a PROD ni se afirma que un índice sugerido resuelva el problema. V2 no es objetivo de esta auditoría; participa en el JOIN de cabecera, sin modificación.

Archivos runtime intactos, verificables mediante hashes antes/después. Solo se agregaron scripts de auditoría, SELECT de diagnóstico, planes, mensajes y documentación. Sin DDL/DML, cambios a objetos/datos/índices/estadísticas, PROD, commit ni push. Los snapshots de definición son evidencia y **no se ejecutaron**.
