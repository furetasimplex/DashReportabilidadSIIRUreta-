# Diagnóstico Operacional — Fase 1 DEV

## Alcance

Se conserva `panel.py → callbacks.py → db.py`, SQLAlchemy, los cuatro KPI, los tres gráficos V2 y el Store `lix-aplicado`. La consulta operacional se dispara desde ese Store, después de Consultar. No hay consultas al cambiar controles pendientes, ni elección de un estado representativo cuando no hay parcela seleccionada.

Únicos archivos runtime modificados: `db.py`, `callbacks.py`, `panel.py`. No cambia mapa, CSS del mapa, `map_states.py`, funciones SQL, V2, CPC, Model6 ni Recomendador. No se usa función de módulos.

## Consultas y cardinalidad

SQL exacto: [cabecera.sql](diagnostico_fase1/cabecera.sql) y [timeline.sql](diagnostico_fase1/timeline.sql). Parámetros enlazados SQLAlchemy, exclusivamente SELECT/CTE; no se instala ningún objeto.

Cabecera: función oficial en fecha fin aplicada, proyección explícita de identidad/campaña/estado/calidad/actividad, LEFT JOIN V2 únicamente por **fecha+pad_id+parcela_id** para el contexto hidráulico de ese día. No se filtra estado operacional por campaña hidráulica ni estado de asignación. Si el selector PAD está en Todos, la cabecera resuelve el PAD de la parcela seleccionada y rechaza identidades ambiguas. La campaña operacional conserva `campana_id`/`numero_campana`; la hidráulica conserva aliases separados. Se muestra el **número**, nunca se sustituye por el ID.

Timeline: un CTE recursivo de fechas inclusivas y CROSS APPLY a la función oficial, en **una sola consulta set-based**, con PAD/parcela exactos y ORDER BY fecha. MAXRECURSION 32767; si el período lo supera falla solo el bloque operacional, sin limitar ni cambiar V2. Se rechazan fechas duplicadas, fuera del período o identidad diferente; no se deduplica ni se rellenan días faltantes. El eje incluye el último día completo; huecos siguen vacíos.

Consultas de negocio habituales por Consultar:

- Sin parcela: 2 overview + 2 tabla = **4**, sin consulta operacional.
- Con parcela: las 4 existentes + **1 cabecera y 1 timeline = 6**.
- Si no hay cabecera: solo 1 consulta operacional, devuelve ausencia.
- Las 2 consultas de opciones por cambio de filtros son las existentes, independientes del botón; callbacks adicionales por restablecer página/facetas pueden sumar invocaciones.

## Presentación

Cabecera «Estado operacional al DD-MM-YYYY» anclada a fecha fin aplicada. Fase+condición solo para ciclo hidráulico; en otros casos un único estado amigable. Incluye campañas separadas, calidad y actividad Sí/No/Sin dato. Explica que drenaje es indicador basado en Cu positivo, no caudal, y que fuera de ventana no implica inactividad.

El cuarto gráfico es «Evolución del estado operacional»: barras horizontales diarias, eje categórico, color por fase. Reutiliza `fase_visual`, `FASES`, `ESTADOS`, `CALIDAD`, `actividad`; los colores se leen de las clases existentes en `assets/lixiviacion_map.css`, sin mantener otra paleta. Hover: fecha, condición exacta, fase, número campaña, riego/drenaje y calidad. NULL no se convierte en No.

Etiquetas V2: «Campaña hidráulica» y «Asignación hidráulica». Los dos códigos de asignación se traducen en selector, cabecera y DataTable, conservando códigos SQL y valores de opciones. El filtro de tabla reconoce también las dos etiquetas completas amigables y las traduce al código para compararlas; los códigos anteriores siguen admitidos. No cambia paginación ni campos SQL.

Cada KPI conserva cálculo y añade ayuda nativa `title` mediante ⓘ. `load`, `overview`, `figures`, `figure`, `number`, `serial`, consultas de opciones y helper de detalle mantienen exactamente sus cuerpos anteriores (ver test AST).

El callback operacional independiente contiene sus errores: muestra «No fue posible cargar el estado operacional.» sin modificar ningún output V2. Ausencia: «Sin información operacional para el período seleccionado.» Sin parcela: invitación discreta, sin timeline.

## Validación

- Tests locales: **56 PASS** en la ejecución final (43 anteriores + 13 casos nuevos).
- Nuevos tests cubren fecha fin, clave física sin campaña, campañas separadas, OX P17 con NULL hidráulico, unicidad, una consulta set-based, etiquetas, actividad NULL, aislamiento de errores y conservación exacta de funciones de cálculo/gráficos.
- `smoke_diagnostic_dev.py` compara código anterior y actual, antes/después de consultar estado: totales, series y todas las filas de detalle (hash, sin guardar datasets). General + siete casos, período 01/06–10/09. Guarda `diagnostico_fase1/smoke.json`.
- `visual_diagnostic_review.py`: Chrome headless local con sesión temporal, sin cambios de auth; cinco capturas, controles pendientes, responsive, navegación y mapa/Recomendador. Evidencia en `diagnostico_fase1/visual/`.
- Las copias `diagnostico_fase1/db.py`, `callbacks.py`, `panel.py` son snapshots anteriores para revisión/invariancia, no otra arquitectura ni módulos importados por la aplicación.

Smoke DEV: **PASS** para selección general y los siete casos. En cada parcela: 102 filas de timeline, 102 fechas únicas. Cuatro KPI, tres figuras Plotly y todas las filas de DataTable V2 comparadas antes/después, sin diferencias. Los estados finales son OX P1 RIEGO_DRENAJE, OX P17 MIXTO, OX P29 REPOSO_PRE_RECLAMO, SULF P1 MIXTO, SULF P7 RIEGO_DRENAJE, SULF P9 REPOSO_PRE_RECLAMO y SULF P28 APILADO. Solo OX P1/SULF P7 tienen CAMPANA_HIDRAULICA entre estos casos; los demás conservan FUERA_VENTANA_RIEGO y campaña hidráulica NULL. OX P1 muestra número operacional 18, no ID 11.

Los hashes del mapa (`map_db.py`, `map_panel.py`, `map_states.py`, CSS), `layout.py` y `smoke_dev.py` permanecen idénticos a la auditoría previa. `git diff --check`: PASS, con advertencia preexistente LF/CRLF en `layout.py`.

Observación de rendimiento: el timeline de 102 días tardó decenas de segundos en las lecturas DEV. Usa una sola consulta y el bloque operacional tiene su propio Loading; V2 permanece disponible. No se cambió la función SQL ni se añadió caché. Medir/optimizar esta consulta puede ser un frente posterior, sin modificar reglas funcionales.

Capturas: [general](diagnostico_fase1/visual/diagnostico_general.png), [OX P1](diagnostico_fase1/visual/ox_p1.png), [OX P17](diagnostico_fase1/visual/ox_p17.png), [SULF P7](diagnostico_fase1/visual/sulf_p7.png), [SULF P28](diagnostico_fase1/visual/sulf_p28.png) y [móvil](diagnostico_fase1/visual/responsive.png). Diff runtime completo: [runtime.diff](diagnostico_fase1/runtime.diff).

Se conservó la evidencia del primer intento de navegador (`review_initial_failure.json`), que no llegó al sidebar en el puerto 8067. La revisión se repitió en el puerto 8066 ya usado por el proyecto. Durante inspección móvil se ajustó exclusivamente el título del nuevo timeline a un encabezado HTML con wrap, sin alterar las figuras existentes.

**Chrome final PASS**, capturas regeneradas tras ese ajuste: general, OX P1/P17, SULF P7/P28 y móvil. Sin errores JavaScript ni callbacks HTTP fallidos; sin overflow horizontal a 1440/520 px. Controles pendientes conservan resultados aplicados, navegación de las cinco secciones intacta, mapa con 60 parcelas y Recomendador sin cambios. El servidor temporal se apagó al terminar. Resultado completo: `diagnostico_fase1/visual/review.json`.

## Pendiente independiente

Transferencia LIVE observada por auditoría: **30.395,260628596 t**. Baseline histórico: **30.136,221811330 t**. Diferencia **+259,038817266 t**, causa no determinada. No se modifica `smoke_dev.py`, no se atribuye ni se corrige el desfase. El smoke nuevo compara invariancia contemporánea, no reemplaza el baseline histórico.

## Archivos y restricciones

Runtime: `db.py`, `callbacks.py`, `panel.py`. Tests/herramientas: `test_diagnostic_operational.py`, `smoke_diagnostic_dev.py`, `visual_diagnostic_review.py`; en `visual_review.py` solo se adapta la selección de la etiqueta traducida. Informe y evidencias: este documento y `diagnostico_fase1/`.

Sin DDL/DML, sin PROD, sin commit ni push. El mapa y el baseline anterior se verifican por hash contra la auditoría previa.
