# Auditoría de diferencia histórica de Transferencia Cu — DEV

Período: 01-06-2026 a 10-09-2026. Captura: 05-10-2026 22:54 UTC. Solo consultas SELECT; evidencia local en [transferencia_cu_auditoria/](transferencia_cu_auditoria/).

## Conclusión

**HECHO:** se confirma el incremento de **259,038817266 t Cu**, desde **30.136,221811330** hasta **30.395,260628596**. El 94,1635% corresponde al agregado SULF y el 5,8365% a OX. Esto localiza el delta por PAD, pero **no explica su causa**.

**NO DETERMINABLE CON EVIDENCIA ACTUAL:** qué fechas/parcelas cambiaron, cuánto aportaron flujo, drenaje, refino, NULL/cobertura o modificaciones SQL entre el baseline y el LIVE. No se encontró el dataset histórico necesario ni una definición SQL inequívocamente asociada a la ejecución del baseline. No se inventa un Top 20 ni una descomposición causal.

## Baseline y alcance histórico

La referencia se define explícitamente en `lixiviacion/smoke_dev.py`, diccionario `expected`, y está registrada como resultado real PASS en `lixiviacion/SMOKE_DEV.json`. `lixiviacion/README.md` conserva la tabla aprobada. `smoke_diagnostic_dev.py`, sus JSON y los informes posteriores citan el baseline; no son nuevas observaciones del estado antiguo. Las rutas, líneas y SHA256 están en [baseline_evidence.json](transferencia_cu_auditoria/baseline_evidence.json).

| Pregunta | Evidencia disponible |
|---|---|
| A. ¿Solo agregado esperado? | Hay constantes esperadas y resultado agregado PASS; global y por PAD. |
| B. ¿Snapshot histórico parcela-día completo? | No encontrado vinculado a las 30.136,221811330 t. |
| C. ¿Serie histórica fecha/PAD? | No encontrada. `dias_pad=204` es un conteo, no conserva los valores diarios. |
| D. ¿Definición SQL/V2 de aquel momento? | Hay candidato local no ejecutado y snapshots posteriores; no acreditan el DDL exacto del baseline. |
| E. ¿Hash V2 asociado a aquel baseline? | No encontrado. Hashes posteriores de consultas/resultados no reconstruyen el baseline. |
| F. ¿Resultado anterior reconstruible? | Sí, sumando los dos totales PAD: 6.801,723817085 + 23.334,497994245 = 30.136,221811330. No permite reconstruir filas. |

Clasificación: **nivel D enriquecido con total por PAD**. No cumple B, porque B requiere fecha + PAD. Se buscaron referencias numéricas en código, Markdown, JSON, CSV, SQL y evidencias del repositorio. Los catálogos SQL encontrados en `report_export/exports` contienen definiciones/metadatos, no observaciones químicas del baseline. No hay historial Git de `SMOKE_DEV.json` disponible en el checkout actual.

`diagnostico_auditoria/resultados.json` (05-10-2026) ya registra 30.395,260628596 t, agregados de algunos períodos y siete ejemplos parcela-día. Esos siete ejemplos coinciden con la captura actual en flujo/química/transferencia ([comparación posterior](transferencia_cu_auditoria/later_sample_comparison.json)); **no** son el histórico que produjo 30.136 t. Los snapshots de invariancia del timeline guardan hashes/KPIs, no las 6.120 filas originales. No se usa ninguna de estas evidencias posteriores como baseline antiguo.

## Reconciliación exacta

| PAD | Baseline t Cu | LIVE t Cu | Delta t Cu | Delta flujo m³ |
|---|---:|---:|---:|---:|
| OX / 1 | 6.801,723817085 | 6.816,842571007 | +15,118753922 | 0 exacto |
| SULF / 2 | 23.334,497994245 | 23.578,418057589 | +243,920063344 | 0 exacto |
| Total | 30.136,221811330 | 30.395,260628596 | **+259,038817266** | **0 exacto** |

Flujo global histórico/LIVE: **12.168.556,400321637026000 m³**. OX: 2.908.120,161887395403000; SULF: 9.260.436,238434241623000. Coincide a toda la precisión almacenada en el baseline, sin sumar subtotales previamente redondeados. **No demuestra igualdad fila a fila ni descarta compensaciones de flujo**.

AVG(delta_cu_gl) global: histórico 1,206011; actual 1,179640. OX: 1,220839 → 1,191387; SULF: 1,189065 → 1,166214. Estos agregados cambiaron, pero no identifican qué concentración, cobertura, distribución de flujo o definición cambió. Que el promedio disminuya y la transferencia aumente no es una contradicción: transferencia depende de valores por fila y del flujo asociado, no del promedio simple global.

## Snapshot LIVE, grano y NULL

[live_snapshot.json](transferencia_cu_auditoria/live_snapshot.json) conserva las once columnas solicitadas, decimales como strings exactos y NULL como `null`. No se convierte NULL a cero.

- 6.120 filas = 6.120 claves fecha + PAD + parcela; cero duplicados.
- OX 3.264 filas; SULF 2.856.
- 6.120 transferencias no NULL. Cero NULL en flujo, drenaje, refino, delta y transferencia.
- `campana_id` tiene 2.062 NULL; las demás columnas extraídas no tienen NULL.
- Ceros actuales: flujo 2.221; drenaje 2.314; refino 0; delta 0; transferencia 2.221.
- La suma exacta del JSON coincide con SUM SQL para flujo y transferencia. Los agregados al inicio y al cierre coinciden. No se fuerza aislamiento snapshot del servidor: esta comprobación no equivale a una garantía transaccional de inmutabilidad de todas las fuentes concurrentes.

Transiciones NULL→dato, dato→NULL, cero→dato y dato→cero históricas: **no determinables**. Ausencia de NULL actuales no prueba ausencia histórica. Sin snapshot antiguo no se cuantifica transferencia aparecida/desaparecida por cobertura.

## Definiciones, fecha operacional y estado

Se capturaron y compararon V2 y ocho vistas responsables de flujo/drenaje/refino y bases de refino. Las nueve coinciden con los snapshots de `diagnostico_auditoria/` tras normalizar finales de línea y espacio exterior. SHA256 exactos y resultado textual en [definitions_hashes.json](transferencia_cu_auditoria/definitions_hashes.json); definiciones LIVE y diffs en [definitions_diff/](transferencia_cu_auditoria/definitions_diff/).

**HECHO:** no se detecta cambio de definición respecto de esos snapshots posteriores. **NO DETERMINABLE:** si hubo cambios de SQL o datos desde la ejecución del baseline. Los candidatos y snapshots legacy anteriores no son la misma definición instalada de V2; no se presentan diferencias de diseño como un despliegue probado.

Las vistas operacionales conservan la regla de timestamp >= `2026-06-01T21:00:00` y hora >= 20 para pasar al día siguiente. Sin timestamps/fuentes del baseline no se puede demostrar un desplazamiento histórico. No hay fechas Top de diferencia sustentables, por lo que no se eligen arbitrariamente filas fuente como si explicaran el delta.

La fórmula V2 no condiciona transferencia a `estado_asignacion`: este estado proviene de la campaña hidráulica nullable. Actualmente hay 2.062 filas `FUERA_VENTANA_RIEGO`; 106 tienen flujo positivo, con 6,128277530448000 m³ y **−0,004169529 t**. No se descartan. El total dentro de ventana es 30.395,264798125 t; sumando fuera se recupera el global. No se mezcló `campana_id` con `numero_campana`, ni se agregó un JOIN para construir el snapshot.

## Precisión y redondeo

La expresión vigente es:

```sql
CAST(
  CAST(flujo_m3_d * (cu_drenaje_gl-cu_refino_gl) AS decimal(31,6))
  / CAST(1000.0 AS decimal(5,1))
  AS decimal(38,9)
)
```

La comprobación SELECT reproduce esta expresión: **cero diferencias** contra transferencia V2. Todas las entradas actuales son no NULL; no se omitieron discrepancias NULL en esta comprobación.

Como diagnóstico separado se comparó cada transferencia almacenada con el producto de los operandos extraídos usando Decimal de precisión 70, sin sustituir el valor reportado. Residual neto actual: **−0,00000000181213135 t**; suma absoluta: **0,00000079884863151 t**; máximo por fila: **0,00000000049998450 t**. El residual numérico vigente no explica +259 t. Sin expresión y datos vinculados al baseline no se demuestra qué residual tenía el histórico ni se atribuye una diferencia histórica de precisión.

## Qué queda explicado y qué falta

Reconciliación territorial: **100%**; contribuciones PAD suman exactamente +259,038817266 t. Atribución causal probada: **0%**; **259,038817266 t** permanecen sin asignar a causas. En [cause_breakdown.json](transferencia_cu_auditoria/cause_breakdown.json), los efectos desconocidos son NULL, no cero.

No se generan `row_comparison.csv` ni `top_contributors.csv`: faltarían sus operandos históricos. Tampoco se fabrica un Top 20 de fechas/drenaje/refino usando simplemente los mayores valores actuales. Sí se entregan agregados **LIVE** por fecha, PAD, fecha/PAD, parcela y estado; no se etiquetan como diferencias.

Para cerrar causalmente se necesita el dataset que produjo el baseline (fecha/PAD/parcela, flujo, Cu drenaje/refino y transferencia) y la definición SQL de esa ejecución, o una restauración aislada autorizada que permita recuperarlos. Esta auditoría no restaura ni modifica bases. Con esa evidencia podría efectuarse FULL OUTER JOIN exacto y descomposición con orden explícito flujo→drenaje→refino, separando cobertura y residual; no se calculó con valores inventados.

## Artefactos y controles

[README](transferencia_cu_auditoria/README.md), `baseline_evidence.json`, `live_snapshot.json`, `definitions_hashes.json`, `definitions_diff/`, `summary_by_date.csv`, `summary_by_pad.csv`, `summary_by_date_pad.csv`, `summary_by_parcel.csv`, `summary_by_state.csv`, `cause_breakdown.json`, `queries_readonly.sql`, `resultados.json`, `later_sample_comparison.json`, scripts reproducibles y hashes de archivos previos.

Se verificaron sumas, counts, claves únicas, precisión, NULL, estabilidad de agregados y hashes del runtime/evidencia previa. No se ejecutó el smoke histórico, porque escribe su propio archivo y fallaría por la diferencia conocida; no se alteraron sus expectativas. `git diff --check` PASS. Runtime, timeline optimizado, mapa, V2, fuentes y baseline intactos. Solo SELECT en DEV; sin DDL/DML, índices, estadísticas, PROD, commit ni push.
