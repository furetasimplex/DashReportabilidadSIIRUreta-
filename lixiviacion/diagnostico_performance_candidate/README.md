# Prototipos de timeline por parcela/rango — DEV

Solo SELECT/CTE y scripts de diagnóstico. No integrar estos archivos al runtime ni publicar objetos SQL. Sin DDL/DML, tablas temporales, índices, actualización de estadísticas, caché ni materialización.

**Completado:**74 comparaciones exactas PASS (37 casos ×2 diseños), además de37 controles contra la proyección runtime. Benchmark60 ejecuciones sin XML, cuatro planes reales y cuatro perfiles SQLAlchemy. Ver [informe](../DIAGNOSTICO_PERFORMANCE_CANDIDATE.md), [resultados](resultados.md) y [planes](plan_comparison.md).

**Límite importante:** se elimina la evaluación diaria de60 parcelas y las lecturas del PAD contrario, pero algunas ramas de extremos/contexto todavía se ejecutan102 veces. No declarar cumplida la evaluación física única por campaña. Se recomienda otra iteración con el genérico como base; runtime permanece intacto.

## Diseño

`candidate_generic.sql` une las fuentes OX/SULF con predicados de PAD y una parcela filtrada desde el inicio. `candidate_ox.sql` y `candidate_sulf.sql` contienen únicamente sus fuentes hidráulicas respectivas. El script selecciona el especializado por PAD; no cambia callbacks.

Campañas se agrupan por parcela y se calcula LEAD antes de filtrar las que intersectan el rango. Los extremos se agrupan por campaña sobre su ventana completa, incluidas fechas fuera del rango visible. Actividad se agrupa por parcela/fecha con COUNT y MAX oficiales, preservando NULL. Estado de módulo conserva literalmente el CASE instalado, sustituyendo solo el parámetro diario por la columna de fecha. Se consolida fecha/campaña/parcela y se mantienen hitos/calidad y STRING_AGG sin agregar un orden nuevo.

Los CTE no garantizan materialización ni una sola ejecución física. La reutilización efectiva y el empuje de predicados deben verificarse en los planes reales, no deducirse del nombre de los CTE.

## Contrato y baseline

El runtime `OP_TIMELINE_SQL` proyecta 12 columnas. El pedido exige las 24 de la función oficial. Por ello se guardan dos referencias:

- `baseline_runtime.sql`: copia literal del runtime sin cambios.
- `baseline_full_contract.sql`: mismo calendario/APPLY/filtros/orden, ampliando solamente SELECT a las 24 columnas. Es una consulta de auditoría, no una edición de db.py.

Para cada caso se compara el runtime contra la proyección de 12 columnas de la referencia completa; ambos candidatos se comparan contra las 24 columnas. Se ejecutan ambas referencias por caso, sin reutilizar un resultado de otro rango. El costo de la proyección completa puede diferir del runtime; los speedups principales se reportan contra el runtime de 12 columnas medido anteriormente, con esta salvedad explícita.

## Comparación

`run.py` verifica base DEV y que la definición instalada siga siendo igual al snapshot auditado. Resuelve IDs reales. Usa comparación Python exacta NULL-safe y multiconjuntos en ambas direcciones, además de diferencias por clave/columna y duplicados. No normaliza composición, no convierte NULL a 0/vacío, no ordena fragmentos de STRING_AGG. El hash SHA-256 ordena claves JSON para serialización estable y conserva valores/resultados en orden fecha; no sustituye la comparación exacta.

Las reversas se buscan dentro de la misma campaña: desde un estado terminal observado a cualquier estado posterior prohibido, no solo fechas adyacentes. Se contrasta la misma detección en baseline. No se interpreta un cambio de campaña como reversa; el análisis usa estado consolidado de parcela, no reconstruye estados de módulos desde cadenas MIXTO.

## Ejecución

Desde la raíz del repositorio, con el entorno DEV existente:

```powershell
.\venv\Scripts\python.exe -m lixiviacion.diagnostico_performance_candidate.build
.\venv\Scripts\python.exe -m lixiviacion.diagnostico_performance_candidate.run probe
.\venv\Scripts\python.exe -m lixiviacion.diagnostico_performance_candidate.run functional
.\venv\Scripts\python.exe -m lixiviacion.diagnostico_performance_candidate.run benchmark
```

`build` solo escribe SQL local; toma el CASE/quality del snapshot verificado. Parámetros SQLAlchemy enlazados, sin interpolación de datos. `probe` comprueba los siete casos canónicos de un día. `functional` cubre 7×5 rangos y dos rangos ampliados de 253 días. Cualquier diferencia bloquea benchmark. `benchmark` exige 74 comparaciones PASS; captura tres repeticiones por diseño/caso/rango y planes reales aparte, sin incluir XML en medianas. Medición adicional con Connection.execute/mappings de SQLAlchemy, fuera de Dash.

No se vacían caches, no se fijan hints nuevos, MAXDOP ni opciones permanentes. MAXRECURSION32767 se conserva del calendario original. IO/TIME/XML son opciones de sesión y se apagan al cerrar. Las conexiones se cierran con rollback defensivo, sin escrituras de negocio. Los mensajes y planes pueden añadir instrumentación. Primera observada no equivale a caché fría.

El capturador de IO/TIME se reutiliza desde la auditoría anterior con destino cambiado solo en memoria; no se alteran sus archivos ni evidencias. Las únicas escrituras son esta carpeta y el informe de candidato. Los hashes documentan runtime antes/después de cada etapa; el repositorio ya tenía cambios previos.

`report.py` genera las tablas y extractos de XML a partir de evidencia local, sin SQL. `validate_local.py` verifica el comparador NULL-safe, detección de duplicados/reversas, SELECT-only, CASE literal y hashes runtime. No se ejecutan pruebas de interfaz: la interfaz no fue modificada.
