# Candidato de timeline operacional por parcela y rango — DEV

**Resultado:** equivalencia exacta en74/74 comparaciones; genérico102 días=1,003 s OX y1,376 s SULF, contra50,871/50,583 s del baseline. No se integró al runtime. **Limitación de diseño pendiente:** la reutilización lógica por campaña no se convierte todavía en una única ejecución física de extremos/contexto. Recomendación: otra iteración sobre el genérico antes de cerrar ese requisito.

## 1. Diseño genérico

Prototipo SELECT/CTE con parámetros enlazados `desde`, `hasta`, `pad_id`, `parcela_id`. La primera relación física es una sola parcela; no se construyen primero las60. Las fuentes hidráulicas se unen con UNION ALL condicionado por PAD. No se llama la función diaria desde el candidato.

Se agrupan todas las campañas de esa parcela antes de LEAD, y solo después se eligen ventanas que intersectan el rango. MIN/MAX hidráulicos abarcan la campaña completa, aunque parte de su historia quede fuera del rango visible. La actividad diaria usa los COUNT/MAX oficiales. Se copia literalmente la precedencia CASE del estado, sustituyendo el parámetro diario por la fecha de fila, sin cambiar umbrales ni NULL.

## 2. Diseño especializado

Misma lógica y contrato, con SQL separado para OX y SULF, seleccionado solo por el script de auditoría. El texto especializado no contiene la familia contraria. No se incorporó esa selección a Python runtime.

Archivos: [genérico](diagnostico_performance_candidate/candidate_generic.sql), [OX](diagnostico_performance_candidate/candidate_ox.sql), [SULF](diagnostico_performance_candidate/candidate_sulf.sql). Son candidatos de revisión, no objetos SQL desplegados.

## 3. Diferencias funcionales y contrato

Resultado final: **SOLO_BASELINE=0, SOLO_CANDIDATO=0, DIFERENCIAS_COLUMNAS=0** en las74 comparaciones, con hashes idénticos y sin claves duplicadas. También pasan las37 comparaciones de la proyección runtime contra la referencia completa. No hubo diferencias funcionales que corregir ni cambios de orden de STRING_AGG para obtener PASS.

El runtime real proyecta12 columnas; el pedido define24. Se preserva la consulta exacta en `baseline_runtime.sql` y se agrega una referencia de auditoría `baseline_full_contract.sql` que solo amplía la proyección. Por cada caso se comprueba que sus12 columnas coincidan con runtime y que los candidatos coincidan en las24. Esto evita presentar columnas nunca comparadas como equivalentes.

Las comparaciones son bidireccionales por valores y multiplicidad; verifican claves duplicadas, nombres/orden de columnas y diferencias por columna, preservando NULL frente a cero/vacío. La composición se compara textualmente, sin ordenar sus fragmentos ni imponer WITHIN GROUP. Los resultados no se normalizan para obtener PASS.

## 4. Siete parcelas

Las70 comparaciones de la matriz principal (7 parcelas ×5 rangos ×2 diseños) resultaron PASS. Cero filas exclusivas en ambas direcciones, diferencias de columnas, claves duplicadas o reversas. La composición textual coincide sin normalización.

| PAD / parcela | Estado canónico 10-09 | Campañas observadas en102 días |
|---|---|---|
| OX P1 | RIEGO_DRENAJE | 11 |
| OX P17 | MIXTO | 4,11 |
| OX P29 | REPOSO_PRE_RECLAMO | 4 |
| SULF P1 | MIXTO | 10 |
| SULF P7 | RIEGO_DRENAJE | 10 |
| SULF P9 | REPOSO_PRE_RECLAMO | 10 |
| SULF P28 | APILADO | 8,10 |

OX P17 y SULF P28 prueban más de una campaña dentro de un mismo rango. No existe una columna que haya quedado siempre NULL en toda la matriz principal, aunque eso no cubre todas las combinaciones posibles de datos/calidad.

Matriz completa y parámetros reales en [comparacion_funcional.json](diagnostico_performance_candidate/comparacion_funcional.json). IDs OX P1/P17/P29 =1/17/29; SULF P1/P7/P9/P28 =33/39/41/60. Se resuelven con la función instalada y no se suponen iguales al número de parcela.

## 5. Auditoría ampliada

Se extiende OX P1 y SULF P7 a 01-01-2026–10-09-2026, 253 días inclusivos. Se conservan conteos, hashes estables, campañas cubiertas, NULL por columna y diferencias, sin persistir datasets completos. La definición oficial live se compara con el snapshot antes de ejecutar cada etapa.

Ambos diseños PASS, 253 filas por caso. Hash OX=`35e1106daf6a6fa341ce4e7fa9d378186140302e34bae8ecee60c680296e8731`; SULF=`7a2ab4d7aa2c350839b9e1a6bb2003ffc583b64f86ae4bd8ba1c04adfece081b`, idénticos a baseline. Estas parcelas ampliadas cubren campañas 11 y 10 respectivamente; la cobertura de múltiples campañas proviene de OX P17/SULF P28 en la matriz principal.

Tiempos de validación, una ejecución (no medianas del benchmark): OX runtime129,830 s / genérico2,773 / especializado3,093; SULF runtime131,520 / genérico3,579 / especializado4,276. Las referencias24 columnas tardaron196,703/196,159 s; no se usan como denominador del speedup principal.

## 6. Reversas terminales

**Cero reversas detectadas** tanto en baseline como en ambos candidatos, en la matriz principal y ampliada. No se infiere de ello cobertura de transiciones internas ocultas dentro de MIXTO.

Se buscan retornos prohibidos después de DRENAJE_RESIDUAL y REPOSO_PRE_RECLAMO dentro de una misma campaña, incluso con fechas intermedias. Se comparan baseline y candidato. No se considera reversa empezar otra campaña. El alcance es el estado consolidado de parcela; no se reconstruyen transiciones de módulos desde una composición MIXTO.

## 7. Benchmark 1/7/31/62/102

Medianas cliente execute+fetch en segundos; cada celda candidata proviene de tres repeticiones:

| Días | Baseline OX | Genérico OX | Especializado OX | Baseline SULF | Genérico SULF | Especializado SULF |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0,544 | 0,063 | 0,068 | 0,629 | 0,068 | 0,068 |
| 7 | 3,480 | 0,117 | 0,125 | 3,536 | 0,137 | 0,164 |
| 31 | 15,469 | 0,323 | 0,365 | 15,315 | 0,436 | 0,648 |
| 62 | 31,418 | 0,611 | 0,686 | 30,687 | 0,823 | 1,005 |
| 102 | 50,871 | 1,003 | 1,124 | 50,583 | 1,376 | 1,628 |

Las60 ejecuciones normales y cuatro capturas de plan están en [benchmark.json](diagnostico_performance_candidate/benchmark.json). [resultados.md](diagnostico_performance_candidate/resultados.md) incluye primera/segunda/tercera, min/mediana/max, CPU, elapsed SQL, reads y mejoras para los20 grupos. Hay variación visible en especializado SULF31d (0,856/0,648/0,504 s); no se descarta la primera.

CPU102d genérico OX953/953/906 ms y SULF1.250/1.344/1.297 ms; especializado OX1.078/1.063/1.062 y SULF1.515/1.485/1.500 ms. Elapsed SQL completo en las tablas; no se suman compilación ni instrumentación XML a las medianas.

SQLAlchemy Connection.execute+mappings, sin STATISTICS: genérico OX1,148 s, especializado OX1,210 s, genérico SULF1,360 s, especializado SULF1,605 s. Hashes de resultados coinciden con la referencia. No aparece sobrecosto cliente de decenas de segundos; el tiempo de fetch incluye espera del servidor. Detalle en [sqlalchemy_profile.json](diagnostico_performance_candidate/sqlalchemy_profile.json).

Solo se habilita después de completar las74 comparaciones exactas (7×5×2 diseños, más2×2 ampliadas). Tres ejecuciones secuenciales, conservando la primera; sin limpiar caché, índices nuevos, hints de acceso, cambios de MAXDOP ni materialización. Planes reales en ejecuciones adicionales, excluidas de las medianas normales.

## 8. Lecturas lógicas

| Caso102d | Total | Drenaje seleccionado | Flujo seleccionado | CPC | Worktable | PAD+parcela | Familia contraria |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 22.166.901 | 17.581.230 ambos PAD | 3.211.980 ambos PAD | 1.057.718 | 192.757 | 123.216 | Sí |
| Genérico OX | 800.400 | 568.101 | 84.118 | 13.530 | 129.323 | 5.328 | 0 |
| Especializado OX | 800.400 | 568.101 | 84.118 | 13.530 | 129.323 | 5.328 | 0 |
| Genérico SULF | 1.271.747 | 1.029.600 | 73.680 | 31.980 | 129.935 | 6.552 | 0 |
| Especializado SULF | 1.253.709 | 1.029.600 | 73.680 | 13.942 | 129.935 | 6.552 | 0 |

Reads idénticos entre las tres repeticiones de cada grupo. Physical/read-ahead cero en las mediciones del benchmark. La especialización SULF reduce CPC18.038 lecturas (~1,42% del total genérico), pero tarda más; no aporta eliminación adicional de la otra familia, que el genérico ya evita.

Mensajes completos IO/TIME en [statistics/](diagnostico_performance_candidate/statistics/). Las lecturas representan accesos a páginas repetibles, no tamaño único de datos. `functional_timings.json` también conserva las referencias actuales por caso.

## 9. Planes reales

Cuatro capturas: genérico OX P1/SULF P7 y especializado OX P1/SULF P7, 102 días. XML íntegro en [plans/](diagnostico_performance_candidate/plans/) y análisis en [plan_comparison.md](diagnostico_performance_candidate/plan_comparison.md).

Los CTE no son barreras de materialización. Agrupar extremos por campaña expresa la reutilización lógica, pero solo el plan demuestra cuántas ejecuciones físicas se realizaron; no se afirmará cálculo físico único basándose exclusivamente en el SQL.

**Hallazgos del plan:**

- Desaparece la rama de60 parcelas×102 fechas y su filtrado final6.120→102: el candidato parte de seeks de parcela solicitada y sus nodos superiores producen102 filas. Eso no significa que todos los operadores intermedios deban producir102: hay módulos, historia y expansión UNPIVOT legítimos.
- Genérico conserva nodos de ambos PAD, pero OX tiene nodos SULF85/128/153/177/267/310/338/362 con0 ejecuciones/reads; SULF tiene0 en los simétricos OX. Especializados no contienen la otra familia en el texto ni en el plan.
- Una rama de extremos escanea una vez (genérico OX75/118), pero la copia usada por consolidación ejecuta MIN/MAX nodo228 y scans257/300 **102 veces**. SULF267/310 también102. El especializado mantiene la misma repetición histórica: OX208/239 y SULF207/238,102 ejecuciones. **No se logró completamente una sola evaluación física por campaña.**
- Persisten campañas/LEAD repetidos (genérico Window Spool232 y Aggregate238,102 ejecuciones), actividad diaria y lecturas por módulo: drenaje352 OX204 ejecuciones y362 SULF510. El UNPIVOT todavía expande columnas de la tabla ancha antes de ciertos filtros de número de parcela. No es un procesamiento de estados de las60 parcelas, pero sí trabajo residual de fuente.
- El calendario también se duplica por referencias a CTE: nodo221 produce10.302 filas acumuladas en102 ejecuciones. No es el cuello original; ahora integra el trabajo residual. No se reemplazó el calendario ni se alteró su semántica.

| Plan | Costo estimado | Est salida / real | Loops / scans clustered | DOP | Grant KB / usado KB | CPU / elapsed XML ms |
|---|---:|---:|---:|---:|---:|---:|
| Baseline OX | 9,29993 | 11,5043 /102 | 42 /19 | 1 | 11.600 /1.936 | 69.406 /69.410 |
| Genérico OX | 11,8328 | 7,41779 /102 | 99 /16 (8 activos) | 1 | 5.472 /40 | 1.287 /1.320 |
| Genérico SULF | 11,8328 | 7,41779 /102 | 99 /16 (8 activos) | 1 | 5.472 /40 | 1.759 /1.797 |
| Especializado OX | 6,049 | 7,41779 /102 | 75 /8 | 1 | 6.016 /40 | 1.365 /1.401 |
| Especializado SULF | 6,57943 | 77,1473 /102 | 68 /9 | 1 | 12.480 /344 | 1.872 /1.911 |

Más nodos/costo estimado no implica más tiempo real. Genérico contiene ramas inactivas y tiene más loops que baseline, pero muchísimo menos trabajo por sus ejecuciones. La salida genérica está subestimada13,75×; especialista SULF1,32×. Se conservan sorts/spools; no hay spills observados, GrantWait=0 y no hay MissingIndexes. Todos presentan optimizer TimeOut (búsqueda, no timeout de ejecución), PlanAffectingConvert en STRING_AGG y aviso **Excessive Grant**. El grant usado es muy inferior al concedido; no se modificó configuración.

El genérico comparte PlanHash `0x8135D440A8B32049` en ambos PAD; especializado OX=`0x7F0C920F4F1A8FB4`, SULF=`0xA793AB706EE22B9C`. No se cambió el plan con RECOMPILE ni se probó independencia de parameter sniffing. El plan genérico se reutilizó tras la validación; estas mediciones no garantizan idéntico comportamiento con otra compilación futura.

## 10. Speedup

102d: genérico **50,70× OX /36,76× SULF**; especializado45,25× OX /31,07× SULF. Como control temporal, las ejecuciones runtime actuales durante la validación fueron51,285 s OX P1 y48,881 s SULF P7, cercanas al baseline previo; no son un nuevo conjunto de tres repeticiones.

Se calcula `baseline_mediana/candidato_mediana` contra el runtime medido en la auditoría anterior. Referencia OX P1 102d=50,871 s; SULF P7=50,583 s. Los candidatos devuelven24 columnas, el runtime12: se explicita esa diferencia de proyección. Los tiempos de la referencia completa también se conservan; no se usan para inflar el speedup principal.

## 11. Reducción IO

102d: genérico **96,39% OX /94,26% SULF**; especializado96,39% OX /94,34% SULF. La mayor reducción ocurre por evitar otras parcelas y la familia contraria, no por haber eliminado todo recálculo de extremos.

Se calcula `100*(1-candidato_reads/baseline_reads)`, utilizando la mediana de lecturas de cada conjunto de tres ejecuciones. El baseline102d tiene22.166.901 lecturas. No se exige una mejora previa como condición de aprobación funcional.

## 12. Genérico vs especializado

El genérico reduce duplicación de mantenimiento; la especialización garantiza por construcción que el texto no contenga fuentes del otro PAD, a costa de mantener dos variantes. El generador local usa una plantilla común para evitar divergencias. El rendimiento relativo y las ramas efectivamente ejecutadas deben juzgarse por IO/plan, no por contar referencias en el texto.

## 13. Recomendación técnica

**Otra fase necesaria para cerrar el requisito de evaluación física única; usar el genérico como base de esa iteración.** Los dos candidatos son equivalentes en los casos medidos y mucho más rápidos. El genérico gana en las medianas102d y evita mantenimiento de dos variantes, sin leer la familia contraria. La especialización no queda justificada por estas mediciones.

No declarar el candidato listo para runtime bajo el criterio literal «extremos/contexto una vez por campaña»: esa meta permanece parcial. Una siguiente iteración debe reducir la duplicación de ramas de `dias`/`estado_modulo`/`hitos` y demostrar reutilización física mediante planes, manteniendo SELECT-only si ese sigue siendo el alcance autorizado. No añadir índices/cache para ocultar ese punto sin una decisión posterior. Hasta esa autorización, **el runtime mantiene el baseline**.

| Objetivo | Resultado medido |
|---|---|
| Igualdad exacta24 campos y proyección runtime | Cumplido en74 comparaciones /37 casos |
| Sin función diaria dentro de candidatos | Cumplido |
| Evitar evaluación de estados de60 parcelas por fecha | Cumplido en planes capturados |
| Evitar lecturas PAD contrario | Cumplido en ambos diseños |
| Extremos sobre ventana completa | Equivalencia y SQL preservados |
| Una única ejecución física de contexto/extremos por campaña | **Parcial: todavía hay ramas con102 ejecuciones** |
| Cero reversas respecto del baseline | Cumplido en alcance medido |
| Integración runtime | No realizada, según instrucciones |

## 14. Qué requeriría llevarlo a runtime

Una autorización posterior, revisión del SQL candidato y decisión explícita de diseño. Integrar solo la ruta timeline, conservar controles de cardinalidad y selección, contratos/detalle/NULL, y ejecutar regresiones funcionales y de UI. Añadir casos fuera de la ventana medida y de cambios de campaña/datos tardíos. No modificar V2, cabecera, mapas, parámetros ni fuentes como efecto colateral. Mantener rollback de código al SQL original y monitorear planes y latencia en DEV antes de cualquier decisión de PROD.

Nada de ello se implementa en esta tarea. No se requieren índices ni caché para ejecutar los prototipos actuales; cualquier cambio de ese tipo sería otra fase.

La integración deberá decidir explícitamente la proyección: conservar12 columnas del runtime o consumir24 del candidato. Aunque ambas coinciden funcionalmente en esta prueba, cambiar la proyección puede cambiar el plan; debe repetirse el benchmark con el SQL exacto que se vaya a integrar. Tampoco se garantiza una única ejecución física de un CTE por declararlo una vez.

## 15. Límites de evidencia

DEV y datos presentes, sin controlar carga externa ni caches. Comparación exacta sobre casos medidos no demuestra equivalencia para todo dato futuro. Las columnas siempre NULL o estados no presentes no tienen cobertura empírica positiva; se conservan por copia semántica y deben ampliarse pruebas antes de promover. STRING_AGG oficial no declara orden; coincidir ahora no garantiza estabilidad ante otro plan futuro.

STATISTICS y planes añaden costo; captura XML no es mediana de usuario. SQLAlchemy se mide en script separado, sin callback ni navegador; execute/fetch pueden incluir espera del servidor. Comparar velocidad con una auditoría previa no es un experimento aleatorizado simultáneo. No se impone SLA de PROD.

Solo scripts/evidencia y este informe. Runtime intacto, sin DDL/DML, índices, UPDATE STATISTICS, cache, materialización, PROD, commit ni push. La sesión emite SELECT y SET STATISTICS reversibles; no se afirma que un SELECT no afecte caches/telemetría interna del motor.
