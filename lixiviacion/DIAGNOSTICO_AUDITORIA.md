# Auditoría funcional y técnica de Diagnóstico de Lixiviación

Fecha de inspección: 05-10-2026. Repositorio actual y lecturas directas de **DEV `inventar_SpcHidr`**. Sin cambios runtime, DDL, DML, PROD, commit ni push. Las definiciones guardadas son snapshots de DEV obtenidos durante esta auditoría, no scripts ejecutados ni evidencia de PROD.

## 1. Conclusiones

Diagnóstico es hoy un tablero de balance físico/químico por período; **no explica ni consulta el estado operacional**. Su única fuente de negocio directa es `inventar_SpcHidr.vw_tablero_lixiviacion_final_v2`. Hay **tres gráficos**, no dos. No usa pandas, ni funciones de módulos, ni el Store del mapa.

V2 tiene 33 columnas y grano observado PAD + parcela + fecha: 60 claves el 10/09, 600 del 01 al 10/09 y 6.120 del 01/06 al 10/09, sin duplicados. La unión con `fn_estado_operacional_parcela_diario` por las tres claves no multiplica filas en las dos ventanas exigidas. Es una comprobación empírica, no una garantía de unicidad para todos los datos futuros.

**La campaña no tiene el mismo significado en ambas fuentes:** hay 23 discrepancias de asignación el 10/09 y 230 en diez días. Por ejemplo OX P17 tiene campaña operacional 11 y estado MIXTO, pero campaña hidráulica NULL en V2. No agregar campaña a la clave de unión ni sustituir `estado_asignacion` por `estado_operacional`.

## 2. Arquitectura y call graph real

Referencias estáticas: [layout.py](../layout.py), [panel.py](panel.py), [callbacks.py](callbacks.py), [db.py](db.py), [db_connection.py](../db_connection.py).

```text
layout.py → lixiviacion_panel.layout() (líneas 162–163)
  → panel.layout() → diagnostic_layout() [panel.py:12,73]
    → callbacks.options(...) [callbacks.py:82]
      → filters → db.where → db.options [db.py:49]
        → 2 SELECT DISTINCT sobre V2
        → listas Python de opciones Campaña/Parcela y limpieza de valores inválidos
    → botón lix-consultar → callbacks.load(...) [callbacks.py:104]
      → filters → db.overview [db.py:64]
        → SELECT agregado período + SELECT agregado fecha/PAD sobre V2
      → number → cuatro KPI
      → figures → figure → plotly.graph_objects → tres gráficos
      → lix-aplicado.data = diccionario de filtros aplicados
        → callbacks.table [callbacks.py:123]
          → db.detail → where + table_predicate [db.py:105,80]
          → COUNT + SELECT paginado sobre V2 → serial → DataTable
        → callbacks.delta_label [callbacks.py:135] → texto del KPI ΔCu
```

La conexión es `db._connection()` → `db_connection.get_engine()` → SQLAlchemy. No hay transformación pandas. Se usan diccionarios/listas, Decimal, conversión Decimal→float para JSON/gráficos y suma visual Python de subtotales de transferencia por PAD. `number` conserva precisión de entrada hasta formatear tres decimales; no recalcula V2.

### Componentes y Store

| Rol | IDs reales |
|---|---|
| Contenedor / tabs | `subtabs-lixiviacion`, `lix-tabs`, `lix-diagnostic-tab` |
| Controles | `lix-fechas`, `lix-pad`, `lix-campana`, `lix-parcela`, `lix-estado`, `lix-consultar` |
| Store | `lix-aplicado`: filtros desde/hasta/pad/campana/parcela/estado; no dataset, sin persistencia declarada |
| KPI | `lix-kpi-flujo`, `lix-kpi-cu`, `lix-kpi-delta`, `lix-kpi-fuera` |
| Labels KPI | `lix-label-kpi-flujo`, `lix-label-kpi-cu`, `lix-label-kpi-delta`, `lix-label-kpi-fuera` |
| Gráficos | `lix-flujo`, `lix-quimica`, `lix-transferencia` |
| Tabla / avisos | `lix-tabla`, `lix-tabla-total`, `lix-tabla-error`, `lix-opciones-error`, `lix-error`, `lix-resumen` |

`layout.toggle_subtabs` controla navegación global. `options` solo consulta si Diagnóstico está activo y el contenedor visible. `load` tiene únicamente el botón como Input y los filtros como State, con `prevent_initial_call=True`. **El vacío inicial de KPI/gráficos es deliberado en el código**: las opciones se cargan al abrir, los resultados solo al pulsar Consultar. Cambiar filtros después no refresca resultados; `lix-resumen` lo advierte. No hay enlace automático desde la parcela seleccionada del mapa.

## 3. Fuentes SQL y contrato real

Todos los nombres de la tabla siguiente pertenecen al esquema `inventar_SpcHidr`. Las dos variantes OX/SULF se enumeran expresamente; no se presupone equivalencia de otros analitos.

| Objeto | Tipo / consumo | Columnas relevantes y transformación | Grano / riesgo |
|---|---|---|---|
| `vw_tablero_lixiviacion_final_v2` | Vista; única fuente directa de Diagnóstico | fecha, pad_id, parcela_id, nro_parcela_pad, campana_id, numero_campana, estado_asignacion, flujo_m3_d, cu_drenaje_gl, cu_refino_gl, delta_cu_gl, transferencia_cu_t_d | Físico parcela-día; todos los helpers filtran fecha y facetas; sin JOIN Python |
| `vw_flujos_reales_oxido_long`, `vw_flujos_reales_sulfuro_long` | Vistas; V2 | parcela_id, nro_parcela_pad, fecha, flujo_m3_h, flujo_m3_d; V2 añade PAD literal 1/2 y UNION ALL | CROSS APPLY VALUES de columnas parcela; LEFT JOIN parcela. Sin SUM/deduplicación |
| `flujos_reales_oxido`, `flujos_reales_sulfuro` | Tablas; vistas de flujo | fecha_registro, parcela_01…32 OX / …28 SULF; CAST(fecha_registro AS date); flujo_m3_d=CAST(valor*24.0 AS decimal(38,15)) | Una lectura diaria esperada. Más de una lectura/día se expandiría; no integra intradía |
| `parcela` | Tabla; vistas de flujo | numero, id_pad, id_parcela; LEFT JOIN numero y PAD | Multiplicaría si catálogo no fuera único; sin duplicación observada |
| `vw_drena_concentrados_oxido_long_operacional`, `vw_drena_concentrados_sulfuro_long_operacional` | Vistas; V2 | fecha operacional, nro_parcela_pad, cu_pp y h_p/ph/cl/fet/fe2/eh | CROSS APPLY VALUES; sin agregación. JOIN V2 por PAD+número parcela+fecha |
| `drena_concentrados_oxido`, `drena_concentrados_sulfuro` | Tablas; drenaje | id_registro, fecha_registro, pN_cu_pp y restantes analitos | CAST analitos decimal(12,2); sin COALESCE/NULL→0 |
| `vw_riego_oxido_refino_operacional`, `vw_riego_sulfuro_refino_operacional` | Vistas; V2 | fecha operacional, cu_pp y restantes analitos | PAD-día, sin agrupación. JOIN V2 PAD+fecha, comparte química de refino entre parcelas |
| `vw_riego_oxido_refino_base`, `vw_riego_sulfuro_refino_base` | Vistas; refino operacional | fecha_registro, refino_cu_pp→cu_pp y otros aliases | Su fecha CAST es reemplazada en la capa operacional a partir de fecha_registro |
| `riego_concentrados_oxido`, `riego_concentrados_sulfuro` | Tablas; vistas base refino | id_registro, fecha_registro, refino_cu_pp y otros refino_* | Una fila por fecha operacional esperada; duplicados multiplicarían parcelas |
| `campana_parcela_control` | Tabla; V2 | pad_id, campana_id, numero_campana, parcela_id; MIN primer riego/inicio operación/inicio drenaje; MAX último riego/fin operación/fin drenaje | GROUP BY campaña+parcela reduce contexto módulo antes del JOIN físico |

Ninguna consulta de Diagnóstico usa la vista legacy, funciones de estado o funciones de módulo. Estas últimas se inspeccionaron solamente para la compatibilidad solicitada. Su rama separada está en `resultados.json`: función oficial → CPC/pad/parcela + `v_flujos_oxido_unpivot`, `v_flujos_sulfuro_unpivot`, `v_drena_oxido_operacional`, `v_drena_sulfuro_operacional` → vistas unpivot/tablas correspondientes. **No presentar esas dependencias como fuentes actuales de Diagnóstico.**

### Fechas y JOINs internos de V2

Flujo usa fecha calendario `CAST(fecha_registro AS date)`. Drenaje/refino usan:

```sql
CASE WHEN fecha_registro >= '2026-06-01T21:00:00'
      AND DATEPART(HOUR, fecha_registro) >= 20
     THEN DATEADD(DAY,1,CAST(fecha_registro AS date))
     ELSE CAST(fecha_registro AS date) END
```

V2 arranca desde flujo y hace tres LEFT JOIN: campaña por PAD/parcela y ventana inclusiva, drenaje por PAD/número parcela/fecha, refino por PAD/fecha. Química sin fila de flujo no genera fila V2. No hay módulo ni `id_campana_parcela_control` en las 33 columnas; no se agrega CPC inventada.

La ventana utiliza `LEAD(fecha_primer_riego)` por PAD/parcela, ordenado por primer riego y campaña. El límite es NULL si último riego es NULL; si no hay siguiente campaña, último riego; en otro caso el menor entre último riego y día anterior al siguiente primer riego. No se reemplazan MIN/MAX ni se interpreta esta ventana como toda la vida operacional.

En la rama V2 y los helpers no hay COALESCE ni conversión de valores numéricos NULL a 0. Los CASE de transferencia requieren datos presentes. SUM/AVG ignoran NULL; COUNT(*) incluye filas con valores ausentes. Los JOINs podrían multiplicar si se rompe unicidad de fuentes o ventanas; los filtros WHERE por sí mismos no duplican filas.

## 4. SQL exacto de los helpers

Se capturaron las seis sentencias realmente generadas por `db.options`, `db.overview` y `db.detail` para el período inicial. Están en [consultas_readonly.json](diagnostico_auditoria/consultas_readonly.json), entradas `runtime_helper`, y [consultas_readonly.sql](diagnostico_auditoria/consultas_readonly.sql). Los placeholders `:nombre` son SQLAlchemy y sus parámetros acompañan cada consulta; no son scripts T-SQL autónomos para pegar sin adaptar parámetros.

Resumen exacto (`{w}` es `fecha BETWEEN :desde AND :hasta` más las igualdades seleccionadas, todas parametrizadas):

```sql
SELECT COUNT_BIG(*) AS registros,SUM(flujo_m3_d) AS flujo,
       SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,
       COUNT_BIG(CASE WHEN estado_asignacion='FUERA_VENTANA_RIEGO' THEN 1 END) AS fuera
FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE {w}

SELECT fecha,pad_id,SUM(flujo_m3_d) AS flujo,
       AVG(cu_drenaje_gl) AS drenaje,AVG(cu_refino_gl) AS refino,
       SUM(transferencia_cu_t_d) AS transferencia
FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2 WHERE {w}
GROUP BY fecha,pad_id ORDER BY fecha,pad_id
```

Opciones: `SELECT DISTINCT pad_id,campana_id,numero_campana` con `campana_id IS NOT NULL`; segunda consulta `SELECT DISTINCT pad_id,parcela_id,nro_parcela_pad`. Orden por esas mismas columnas. Cada consulta omite su propia faceta, conservando las restantes.

Detalle: COUNT_BIG(*) con filtros generales y filtros de tabla; SELECT explícito de 10 campos de `db.DETAIL` con aliases `fecha,pad,parcela,campana,estado,flujo_m3_d,cu_drenaje_gl,cu_refino_gl,delta_cu_gl,transferencia_cu_t_d`. PAD es un CASE a etiqueta. Orden solicitado validado y desempate `fecha,pad_id,parcela_id`; OFFSET/FETCH parametrizados. **No hay SELECT * en consultas runtime**; sí en consultas de auditoría y en CTEs internos del snapshot SQL.

## 5. Filtros actuales

| Filtro | Origen/opciones | Columna y aplicación | Dependencias y NULL |
|---|---|---|---|
| Inicio/fin | DatePickerRange, inicial 01-06-2026→10-09-2026 | `fecha BETWEEN :desde AND :hasta`, inclusivo, SQL | Condiciona ambas facetas. Fecha ausente/inválida o inicio>fin produce aviso; no hay tope de rango |
| PAD | Fijo Óxidos=1/Sulfuros=2 | `pad_id=:pad`, SQL | Condiciona Campaña/Parcela. None significa todos, no IS NULL |
| Campaña | DISTINCT V2, etiquetada PAD + numero_campana; valor campana_id | `campana_id=:campana`, SQL | Opciones ignoran campaña seleccionada pero respetan parcela/estado/fecha/PAD. Excluyen NULL. No hay opción explícita campaña NULL |
| Parcela | DISTINCT V2, etiqueta PAD + nro_parcela_pad; valor parcela_id | `parcela_id=:parcela`, SQL | Opciones ignoran parcela seleccionada pero respetan campaña/estado/fecha/PAD. None significa todas |
| Estado asignación | Dos opciones fijas y whitelist backend | `estado_asignacion=:estado`, SQL | CAMPANA_HIDRAULICA / FUERA_VENTANA_RIEGO. Condiciona ambas facetas. None no filtra |
| Consultar | Botón | Captura State, consulta overview y guarda filtros | No altera cálculo ni fuente; cambios posteriores esperan nuevo clic |
| Filtros de DataTable | Texto por columna; AND `&&`, operadores y columnas restringidos | SQL adicional solo en `db.detail` | No altera KPI/gráficos/opciones. No admite IS NULL; comparaciones SQL con NULL no satisfacen igualdad. contains escapa comodines |

El callback limpia una selección que no figura en las nuevas opciones. Campaña y parcela se condicionan mutuamente; limpiar un valor puede ocasionar otra consulta. Ejemplo: campaña seleccionada y luego FUERA_VENTANA_RIEGO pueden producir un estado transitorio sin opciones hasta limpiar campaña. No se implementó corrección.

## 6. Los cuatro KPI

### Flujo acumulado [m³]

`SUM(flujo_m3_d)` sobre las filas V2 seleccionadas. Cada fila diaria proviene de `valor_flujo_m3_h * 24.0`, casteado a decimal(38,15) en las vistas de flujo. Sumar volúmenes equivalentes de días completos entrega m³ del período. **No es integración de registros intradía ni volumen medido de drenaje**. Operacionalmente expresa el volumen diario equivalente acumulado del flujo fuente para las parcelas/días filtrados. No demuestra continuidad real durante las 24 horas.

SUM ignora NULL; si todo es NULL/sin filas, se muestra Sin dato. Ceros se conservan. Filtro de campaña/parcela restringe filas, no las replica; la garantía depende de la unicidad de V2. Nuevas lecturas intradía sin agregación podrían duplicar días, riesgo no observado en las ventanas inspeccionadas.

### Transferencia Cu [t Cu]

`SUM(transferencia_cu_t_d)`, parcela-día. Fórmula LIVE exacta:

```sql
delta_cu_gl = cu_drenaje_gl - cu_refino_gl
transferencia_cu_kg_d = flujo_m3_d * (cu_drenaje_gl-cu_refino_gl)
transferencia_cu_t_d = CAST(
    CAST(flujo_m3_d*(cu_drenaje_gl-cu_refino_gl) AS decimal(31,6))
    / CAST(1000.0 AS decimal(5,1)) AS decimal(38,9))
```

Solo se calcula con flujo y ambas concentraciones presentes. g/L equivale dimensionalmente a kg/m³; volumen diario × diferencia de concentración produce kg/d y la división produce t/d. El KPI suma el aporte diario calculado en toneladas. **Existe redondeo explícito de kg a seis decimales antes de convertir a t en el SQL instalado**; no se elimina ni se reconstruye en Python.

Es una estimación de transferencia neta según la diferencia drenaje-refino y el flujo fuente; no acredita por sí misma extracción recuperada o una medición independiente de masa de drenaje. Positivos y negativos se suman con su signo, no se recortan. Flujo=0 con química presente produce 0; flujo=0 con química NULL conserva NULL por el CASE.

### ΔCu promedio parcelas [g/L]

`AVG(delta_cu_gl)` simple sobre **registros parcela-día no NULL** del período completo. No está ponderado por flujo; no calcula primero media por parcela. Una parcela con más observaciones válidas pesa más. Con todos los días completos, cada parcela-día tiene igual peso; PAD1 aporta 32 observaciones/día y PAD2 28. Si se selecciona una parcela, es media temporal de sus días válidos y cambia la etiqueta a `ΔCu promedio [g/L]`.

Incluye días con flujo cero y deltas negativos. Los ceros químicos no se sustituyen por NULL. El número realmente mostrado es la media del diferencial de concentración de las observaciones válidas filtradas, **no una ley ponderada del volumen ni una media de parcelas con pesos iguales bajo cobertura desigual**. Las medias de drenaje/refino del gráfico ignoran NULL por separado; su diferencia no tiene por qué coincidir con AVG(delta) si falta una de las dos concentraciones en algunos registros.

### Registros fuera de ventana

`COUNT_BIG(CASE WHEN estado_asignacion='FUERA_VENTANA_RIEGO' THEN 1 END)`: cuenta filas parcela-día, no parcelas distintas ni módulos. Fuera de ventana significa que no hubo campaña unida por la ventana hidráulica; no equivale a fuera de operación.

Evidencia DEV 01/06–10/09: **2.062 filas fuera de ventana**, de ellas **106 con flujo positivo almacenado**, todas estas OX; volumen fuera de ventana OX=6,128277530448 m³. Ejemplo OX P20 01/06: 0,032072165277 m³/d, campaña NULL. Son valores fuente; no se infiere su exactitud física ni se aplica umbral nuevo. Seleccionar una campaña específica excluye naturalmente estos NULL.

## 7. Gráficos actuales

Construidos por `callbacks.figures`/`figure`, con **Plotly Graph Objects**, no Plotly Express. X=fecha; altura 340; hover unificado; formato fecha DD-MM-YYYY; sin zoom por rueda. Todos usan filtros aplicados y datos agrupados en SQL por fecha/PAD.

| ID / título | Eje Y / series | Transformación y pregunta |
|---|---|---|
| `lix-flujo` / Flujo diario | m³/d; Scatter por PAD (Óxidos azul, Sulfuros verde) | SUM flujo por fecha/PAD. ¿Cómo varía el volumen diario de las parcelas filtradas? No representa acumulado temporal |
| `lix-quimica` / Cu drenaje vs refino · promedio por fecha/PAD | g/L; dos Scatter por PAD: drenaje sólido, refino discontinuo | AVG por campo/fecha/PAD. ¿Cómo cambian las concentraciones medias? Con parcela elegida cambia título y desaparece «promedio» de series |
| `lix-transferencia` / Transferencia diaria de Cu | t Cu/d; una serie Bar azul | SQL SUM por fecha/PAD, luego Python suma los PAD de cada día conservando Decimal hasta serializar. ¿Cuánto aporte neto calculado hay por día para toda la selección? No separa PAD visualmente |

Flujo y química conservan orden SQL fecha/PAD y `connectgaps=False`; transferencia ordena fechas en Python. NULL se pasa a None, cero a cero. Un día completamente NULL en transferencia queda None; si un PAD es NULL y otro tiene datos, la barra suma únicamente el disponible, sin aviso de cobertura parcial. **No se crea calendario completo:** ausencia total de una fecha no inserta un punto NULL y puede dejar una línea atravesando el intervalo ausente. El comportamiento inicial vacío proviene de prevent_initial_call, no de un error demostrado.

## 8. Grano empírico y compatibilidad

| Período | V2 filas | Claves únicas PAD/parcela/fecha | Duplicados / claves NULL |
|---|---:|---:|---:|
| 10-09-2026 | 60 | 60 | 0 / 0 |
| 01–10-09-2026 | 600 | 600 | 0 / 0 |
| 01-06–10-09-2026 | 6.120 | 6.120 | 0 / 0 |

La clave candidata física es `(pad_id,parcela_id,fecha)`; también se observan números de parcela locales al PAD, pero se recomienda usar IDs al unir. Campaña es nullable, no parte necesaria de la clave. Módulo/CPC individual están ausentes.

Unicidad fuentes 01/06–10/09: flujo OX 3.264 y SULF 2.856; drenaje OX 3.264 y SULF **3.264**; refino 102 fechas por PAD; todas sin claves repetidas, máximo 1. La fuente de drenaje SULF expande 32 números mientras el universo de flujo SULF tiene 28; V2 se ancla al flujo y no genera filas para esos números adicionales.

| Período unión | Filas V2 / estado | LEFT JOIN / INNER JOIN | Sin correspondencia ambos lados | Campaña diferente |
|---|---:|---:|---:|---:|
| 10/09 | 60 / 60 | 60 / 60 | 0 / 0 | 23 |
| 01–10/09 | 600 / 600 | 600 / 600 | 0 / 0 | 230 |

**Sí es segura en cardinalidad en las muestras**, usando fecha+PAD+parcela. Para un futuro enriquecimiento de V2, LEFT JOIN preserva el hecho físico aunque falte estado; para una vista operacional completa, decidir conscientemente si el calendario de 60 parcelas es el universo conductor. No usar INNER JOIN como garantía futura de cobertura. No unir por campaña ni por módulo.

## 9. Estado asignación frente a estado operacional

`estado_asignacion` procede exclusivamente de `CASE WHEN c.campana_id IS NULL THEN FUERA_VENTANA_RIEGO ELSE CAMPANA_HIDRAULICA END` en V2. El filtro está correctamente titulado «Estado asignación»; la DataTable lo abrevia a «Estado», donde sí puede confundirse. No hay códigos RIEGO/MIXTO en los controles actuales.

La función oficial selecciona campaña y consolida estados del ciclo operacional, con un criterio diferente de la ventana hidráulica V2. Sus flags distinguen presencia de dato y actividad; `drenaje_activo` se determina a partir de Cu positivo, **no de un caudal de drenaje medido**. El futuro diagnóstico debe mostrarlo como indicador categórico con su fuente, no fabricar una serie m³/d de drenaje.

Propuesta conceptual: conservar dos campos separados, «Asignación hidráulica de campaña» y «Estado operacional al [fecha]», más `campana_id_hidraulica` y `campana_id_operacional` cuando sea necesario explicar diferencias. No alterar el significado del filtro Campaña sin decisión explícita.

## 10. Casos requeridos, 10-09-2026

Resultados directos DEV. Con fecha única y PAD/parcela seleccionados, sin campaña ni estado restrictivos, cada caso tiene **una fila Diagnóstico**. El flujo/transferencia/delta de esa fila son sus KPI y sus puntos en gráficos; «fuera» vale 1 o 0 según la columna.

| Parcela | Estado operacional | Campaña ID operacional / V2 | Asignación V2 | Flujo m³/d | Cu drenaje / refino g/L | ΔCu g/L | Transferencia t/d |
|---|---|---|---|---:|---:|---:|---:|
| OX P1 | RIEGO_DRENAJE | 11 / 11 | CAMPANA_HIDRAULICA | 648 | 2,05 / 0,27 | 1,78 | 1,15344 |
| OX P17 | MIXTO | 11 / NULL | FUERA_VENTANA_RIEGO | 0 | 0 / 0,27 | −0,27 | 0 |
| OX P29 | REPOSO_PRE_RECLAMO | 4 / NULL | FUERA_VENTANA_RIEGO | 0 | 0 / 0,27 | −0,27 | 0 |
| SULF P1 | MIXTO | 10 / NULL | FUERA_VENTANA_RIEGO | 0 | 0 / 0,36 | −0,36 | 0 |
| SULF P7 | RIEGO_DRENAJE | 10 / 10 | CAMPANA_HIDRAULICA | 2.376 | 0,88 / 0,36 | 0,52 | 1,23552 |
| SULF P9 | REPOSO_PRE_RECLAMO | 10 / NULL | FUERA_VENTANA_RIEGO | 0 | 0 / 0,36 | −0,36 | 0 |
| SULF P28 | APILADO | 10 / NULL | FUERA_VENTANA_RIEGO | 0 | 0 / 0,36 | −0,36 | 0 |

Campaña visible V2 de OX P1: número 18; SULF P7: número 11. ID y número no son intercambiables. Para las otras cinco parcelas, filtrar por la campaña operacional eliminaría la fila V2 del día: eso no prueba ausencia operacional. Los estados operacionales de la tabla son evidencia de auditoría; **Diagnóstico hoy no los muestra**.

## 11. Rendimiento y comportamiento

- Un Consultar ejecuta normalmente **4 sentencias**: 2 de overview + 2 de detalle disparadas por Store. `delta_label` no consulta. Si el Store repite exactamente el mismo valor, el refresco dependiente puede variar según propagación de Dash; no se instrumentó una cuenta de red por clic en esta auditoría.
- Abrir Diagnóstico o modificar facetas ejecuta 2 consultas DISTINCT por invocación de `options`, sin esperar Consultar. Limpiar valores inválidos puede inducir otra invocación. La visibilidad/tab evita carga de opciones mientras está oculto.
- Paginar, ordenar o filtrar tabla: COUNT + página, 2 consultas; no cambia KPI. Volver de otra página a 0 puede disparar callbacks adicionales. La UI usa 25 filas; helper limita tamaño 1–100.
- No hay caché, debounce ni límite de período; se repite expansión de la vista compleja en cada sentencia. No se analizaron planes de ejecución ni índices: no se afirma un cuello de botella específico.
- Resumen/daily y COUNT/página no forman una fotografía transaccional explícita común; con escrituras concurrentes podrían diferir. La sesión de auditoría solo leyó.
- Hay filtrado Python de la lista daily por cada PAD y agrupación de transferencia, de volumen pequeño (204 filas en período inicial); no hay pandas innecesario ni dataset masivo en Store.
- Cambiar filtros sin Consultar deja el resultado anterior visible intencionalmente; la DataTable usa el Store aplicado, no los controles pendientes.

## 12. Riesgos y hallazgos priorizados

| Prioridad | Hallazgo y evidencia | Consecuencia / recomendación sin implementar |
|---|---|---|
| Imprescindible para integración | Campañas diferentes: 23/230 registros en unión | Separar contrato de asignación hidráulica del ciclo operacional; no sumar campaña a la clave |
| Imprescindible para interpretación | Media de registros parcela-día y no ponderada | Describir denominador/cobertura; no cambiar AVG a ponderado sin decisión |
| Imprescindible | Diagnóstico no consulta estado ni explica causas | Incorporar consulta por fecha/rango a función oficial conservando V2; no reconstruir CASE en Python |
| Imprescindible | Grano observado, no protección ante entradas duplicadas futuras | Validar claves y conservación de métricas al integrar; no deduplicar con MIN/MAX arbitrarios |
| Recomendado | «Estado» genérico en tabla y «fuera» confundible con inactividad | Etiqueta inequívoca y explicación; 106 filas positivas fuera de ventana prueban diferencia |
| Recomendado | SUM/AVG ocultan cobertura parcial; química cero se incluye | Mostrar conteos válidos/ausentes y ceros; no cambiar 0/NULL |
| Recomendado | Fecha faltante sin calendario en gráficos | Evaluar gaps explícitos manteniendo NULL, sin rellenar con cero |
| Recomendado | Cantidad de consultas y rangos ilimitados | Medir latencias/planes antes de optimizar o imponer límite |
| Recomendado | Transferencia LIVE incorpora redondeo kg antes de t | Consumir columna oficial, no recalcular desde gráfico o subtotales redondeados |
| Opcional | Transferencia gráfica total combina PAD | Ofrecer desglose si aporta valor operacional; mantener KPI vigente |

### Diferencia con el smoke histórico: no atribuir causa sin evidencia

Lectura actual del helper, 01/06–10/09: 6.120 filas; flujo **12.168.556,400321637026 m³**; transferencia **30.395,260628596 t**; delta **1,179640 g/L**; fuera **2.062**. Opciones: 3 campañas, 60 parcelas; daily: 204 filas; primera página: 25.

La referencia histórica aprobada de transferencia era 30.136,221811330 t; la diferencia actual es **+259,038817266 t**. El flujo sí coincide exactamente con aquella referencia. Esta auditoría no dispone de una fotografía anterior completa de datos que permita atribuir el cambio a una causa. **No se actualizó el smoke ni se corrigió SQL**; se recomienda trazar la diferencia antes de reutilizar aquel baseline como validación actual. No es evidencia de un error provocado por la unión propuesta, que no se implementó.

## 13. Estructura futura propuesta, sin implementación

| Elemento objetivo | Soporte actual | Trabajo/decisión pendiente |
|---|---|---|
| Período, PAD, parcela | Filtros V2 existentes | Mantener; decidir período máximo y cobertura |
| Campaña | Hoy hidráulica V2 | Definir si habrá filtro operacional separado; preservar filas no asignadas |
| Estado a fecha de referencia | Función oficial por fecha | Nueva consulta; definir fecha: fin del período vs fecha independiente, nunca «hoy» implícito |
| Condición hidráulica | Flags y cobertura de función oficial | Nueva consulta; mostrar riego/drenaje como indicadores, no caudales inventados |
| Asignación de campaña | V2 existente | Mostrar separada del estado y de campaña operacional |
| Riego/flujo en el tiempo | V2 flujo_m3_d | Reutilizable; aclarar volumen equivalente diario |
| Drenaje en el tiempo | Cu drenaje y flag de actividad disponibles | No hay serie volumétrica de drenaje demostrada; decidir si usar química/indicador o auditar una fuente volumétrica |
| Timeline estado operacional | Función oficial diaria | Consulta de rango y garantía 1 fila por clave; no persistir ni crear nueva vista todavía |
| KPI físicos/químicos | Los cuatro actuales | Mantener fórmulas, añadir cobertura y explicación |
| «Por qué» y calidad | Flags, hitos, composicion/calidad de la función | Exponer evidencia, no inventar causalidad ni recalcular reglas |

Primera implementación recomendada: enriquecer a nivel parcela-día, con campos de ambas fuentes explícitamente separados; cabecera de estado a fecha definida, timeline categórico y serie física/química existente. Validar conservación de SUM/AVG/COUNT antes/después del JOIN. Un estado «actual» para varias parcelas requiere resumen/distribución, no elegir un estado representativo arbitrario. No incorporar filas de módulos ni replicar medidas; el detalle módulo permanece en el drawer del mapa.

## 14. Qué no se recomienda cambiar

No tocar mapa, funciones oficiales/TEST, V2, CPC, Model6 ni Recomendador. No cambiar fórmula, signos, precisión, nominales, unidades ni fechas operacionales. No filtrar fuera de ventana por defecto, convertir NULL a cero, descartar ceros químicos, ponderar AVG sin aprobación, deduplicar arbitrariamente, mezclar campaña operacional con hidráulica o multiplicar medidas por módulo. No promover objetos como parte de esta auditoría.

## 15. Evidencia y reproducibilidad

- [resultados.json](diagnostico_auditoria/resultados.json): contratos completos, dependencias, grano, agregados, siete casos, unión, conteos de fuentes, cinco ejemplos positivos fuera de ventana y hashes de archivos runtime.
- [consultas_readonly.json](diagnostico_auditoria/consultas_readonly.json) y [consultas_readonly.sql](diagnostico_auditoria/consultas_readonly.sql): SELECT/CTE exactos y parámetros; sin DDL/DML ejecutados. Los tiempos son observaciones puntuales de auditoría, no benchmark.
- [audit_readonly.py](diagnostico_auditoria/audit_readonly.py): ejecutor de inspección, restringido por configuración y DB_NAME a DEV. No se importa desde runtime.
- Snapshots `diagnostico_auditoria/inventar_SpcHidr__*.sql`: definiciones obtenidas con OBJECT_DEFINITION; **contienen CREATE únicamente porque son texto de definición guardado, nunca ejecutado**. Tipos/columnas de tablas se registran en JSON, no datasets completos.
- Hashes de todos los `.py` runtime de Lixiviación, `layout.py` y CSS del mapa idénticos antes/después. Solo se crearon este informe y su carpeta de evidencia.

La captura complementaria terminó sus SELECT y guardó JSON; al exportar el log SQL hubo un error local de serialización de fecha. Se corrigió únicamente el exportador de auditoría y se regeneró el `.sql` desde el log JSON ya capturado, sin repetir ni modificar datos. No se ejecutaron tests de lógica ni navegador: esta tarea fue inspección estática y consultas DEV de solo lectura.
