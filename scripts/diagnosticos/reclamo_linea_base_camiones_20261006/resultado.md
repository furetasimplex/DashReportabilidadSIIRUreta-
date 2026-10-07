# LINEA_BASE_CAMIONES_OK

## Conclusión

`m3_camiones_previo = 0` de M17 y M23 es **correcto según la definición actual**
de `sp_establecer_linea_base`: suma `volumen_diario_m3` de la misma
`campaña_id + modulo_id` solo cuando `fecha < FECHA_CORTE_SISTEMA`.
El corte en DEV es **01-07-2026**. No hay filas THM anteriores al corte para
ninguno de los 26 módulos congelados de PAD2/campaña 10. Todos guardan cero;
la consulta ampliada con diferencia mayor a 0,001 m³ devuelve cero módulos.

El acumulado oficial mayor **no demuestra una línea base faltante**. La
discrepancia aparece en datos posteriores al corte: acumulados fuente que no
cuadran con sus deltas disponibles y negativos del 30-09 que figuran como
cero en `v_camiones_acumulado`. Esos puntos requieren una auditoría separada;
copiarlos a la línea base duplicaría o reclasificaría movimientos posteriores
al corte.

## Comparación al 04-10-2026

| Campo | M17 / id 81 | M23 / id 87 |
|---|---:|---:|
| `m3_camiones_previo` almacenado | 0 | 0 |
| Previo esperado (`SUM` antes de 01-07) | 0 | 0 |
| Diferencia de línea base | 0 | 0 |
| Último `m3_camiones_acum` | 1.486,309 | 31.262,878 |
| Total reconstruido: previo + sistema | 1.486,309 | 31.262,878 |
| Último `volumen_final_reclamado` THM | 2.768,842 | 33.812,535 |
| Total reconstruido − fuente | −1.282,533 | −2.549,657 |

Las fechas comparadas están alineadas al 04-10 en la captura final. Un snapshot
previo durante la auditoría aún terminaba el 03-10 en el acumulado del sistema;
se volvió a capturar y regenerar los CSV al aparecer el 04-10, sin ejecutar
sincronización desde esta auditoría.

## Reconstrucción de la fuente posterior al corte

- **M17:** primera fila disponible 29-09: delta **135,623 m³** pero acumulado
  `volumen_final_reclamado` **1.423,533 m³**. Ya existe una diferencia inicial
  de **1.287,910 m³**; no hay filas previas al 29-09 para este módulo en la
  tabla THM consultada. Al 04-10, la suma de deltas disponibles es
  **1.480,932 m³** y el acumulado fuente **2.768,842 m³**, conservando la
  diferencia de 1.287,910. El negativo del 30-09 (**−5,377**) figura en la
  fuente, mientras `v_camiones_acumulado.m3_camiones_dia` vale **0** ese día.
  Así, el sistema queda 5,377 por encima de la suma fuente; la diferencia
  final contra el acumulado fuente es 1.287,910 − 5,377 = **1.282,533 m³**.
- **M23:** primera fila 01-09: delta y acumulado coinciden en **1.087,228 m³**.
  Hasta el 21-09 la suma de deltas coincide con el acumulado fuente. El 22-09
  el delta diario es **2.643,358**, pero el acumulado fuente aumenta
  **5.233,797**, creando una brecha de **2.590,439 m³**. Los movimientos del
  27–28 de septiembre dejan esa brecha en **2.590,420 m³**. El negativo del
  30-09 (**−40,763**) está en THM, pero el acumulado del sistema registra
  **0** para ese día. La diferencia final es 2.590,420 − 40,763 =
  **2.549,657 m³**.

No hay huecos de fecha entre la primera y última fila THM de M17 (29-09 a
04-10) ni de M23 (01-09 a 04-10). La primera fila de ambos tiene acumulado
positivo; solo M17 presenta un offset frente a su primer delta. La semántica
D−1 del archivo de origen no se cuestionó ni se usó para explicar estas
diferencias.

## Congelamiento y ejecución de línea base

| Módulo | Alertas previas | Congelado | `LINEA_BASE_AUTOMATICA` | `fecha_linea_base` |
|---|---|---|---|---|
| M23 | 02-09, 19:26 | 03-09, 09:39:00.163 | 03-09, 09:39:00.194, ejecución 474 | 01-07-2026 |
| M17 | 23-09, 16:43 | 06-10, 10:39:05.322 | 06-10, 10:39:05.354, ejecución 3601 | 01-07-2026 |

La definición de `sp_auto_congelar_modulos_nuevos` llama a
`sp_establecer_linea_base` para cada campaña con nuevos congelamientos, con
`@CampañaId` de la campaña, `@Confirmar=1`, `@SoloSiVacio=1` y
`@Silencioso=1`; no especifica `@PadId` (queda NULL). Los logs automáticos y
las fechas almacenadas confirman la asignación de línea base a M17/M23.
`log_ejecucion` no contiene una fila independiente de
`sp_establecer_linea_base` para esos eventos; la llamada queda dentro de la
ejecución de automatización.

La tabla THM no tiene columna `fecha_carga` ni otro timestamp de inserción.
Por eso no puede determinarse el instante exacto en que sus filas posteriores
al corte estuvieron disponibles respecto del congelamiento. Ese límite no
afecta la conclusión sobre el previo: ninguna fila disponible pertenece al
período anterior al 01-07.

## Campaña 10 completa

26 módulos congelados de PAD2/campaña 10: **26 con línea base actual = esperada
= 0**; 18 tienen filas THM posteriores al corte y 8 no tienen filas THM en
esta fuente. La fecha THM más antigua de la campaña es 28-07-2026. La
clasificación de los 26 es `SIN_HISTORICO_PRE_CORTE`; no hay
`PREVIO_FALTANTE` ni `PREVIO_INCOMPLETO` bajo la lógica vigente.

En una comparación distinta —último acumulado de fuente contra acumulado del
sistema, con fechas alineadas— **16 de los 18 módulos con filas THM** difieren
en más de 0,001 m³. Esto no es una diferencia de línea base: todas esas filas
son posteriores al corte. El detalle por módulo figura en
`campania10_auditoria.csv`; no se atribuye una causa común sin auditar los
deltas de cada módulo.

## Recomendación sin aplicar

Mantener `m3_camiones_previo` de M17/M23 en cero. Auditar por separado el
origen del offset inicial de M17, el salto del acumulado fuente de M23 el
22-09 y el tratamiento de los negativos THM del 30-09 en la sincronización.
Reconciliar deltas y acumulados desde el corte antes de proponer cualquier
ajuste. No se modificaron líneas base, SP, vistas, tablas ni reportes.
