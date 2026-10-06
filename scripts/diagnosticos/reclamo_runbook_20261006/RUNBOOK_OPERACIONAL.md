# Secuencia operacional de Control de Reclamo — DEV actual

**Ruta normal cuando cambió una fuente o la base de un módulo:** completar la base si hace falta → elegir un rango que incluya la primera fecha afectada → **Reprocesar período** → comprobar el mensaje y revisar validaciones, detalle y vista previa → publicar solo si corresponde y está resuelto lo bloqueante. **Actualizar secuencia de módulos no es requisito previo**: Reprocesar la ejecuta internamente después del primer sync.

| Paso | Acción del usuario | Botón | Qué hace internamente | Qué revisar | ¿Escribe datos? | ¿Obligatorio? |
|---|---|---|---|---|---|---|
| 1 | Seleccionar período | selector `rango` | Define rango para acciones y consultas; por sí solo no ejecuta SP | Inicio anterior o igual a la primera fecha afectada; fin cubre días derivados | No | Sí para operar con fechas correctas |
| 2 | Completar base faltante de módulo existente | Buscar → Actualizar registro | Actualiza `disponible_rotopalas`, densidad automática; propaga TMS/m³/densidad si ya congelado | TMS, m³, densidad y mensaje | Sí | Solo si base incompleta o errónea |
| 3 | Dar de alta módulo ausente | Insertar | Crea base; no secuencia ni abre por sí solo | PAD, campaña, módulo, TMS y m³ positivos | Sí | Solo si no existe |
| 4 | Incorporar fuentes y recomputar | **Reprocesar período** | Prepara → sync ETL → mantiene secuencia → sync → CV25/horas → `calculo_diario` | Mensaje de éxito, rango, módulos congelados/abiertos y fuente de cada día | Sí | Sí cuando hubo cambio que deba reflejarse en Reclamo |
| 5 | Revisar | Validaciones, Resumen, CV25 vs Topografía, Avance, Cuadratura/remanente, Vista previa | Consultas `SELECT`; tras Reprocesar suelen dispararse por cambio de `mensaje-accion` | Bloqueos vigentes, advertencias y cifras que se publicarán | No | Validaciones y vista previa: sí como procedimiento operacional; resto según caso |
| 6 | Actualizar manualmente la pantalla si cambió solo el período o faltan opciones en Ajustes | Refrescar vista | Vuelve a consultar; no reprocesa | Que tablas/gráficos corresponden al período seleccionado | No | Según necesidad; **no** paso fijo tras Reprocesar |
| 7 | Publicar tras validar | Publicar reclamo conciliado → confirmar | Recalcula factor de camiones y reporte final; MERGE en `Datos_conciliados_of`; no recalcula Reclamo | Período efectivo, vista previa, confirmación y mensaje | Sí | Solo cuando hay decisión de publicación |

## Escenarios

1. **Solo consultar:** seleccionar período → Refrescar vista → revisar paneles. Cambiar el período solo no dispara todos los paneles porque lo leen como `State`.
2. **Topografía o camiones nuevos (por ejemplo ayer):** seleccionar desde el día que llegó/cambió hasta el último día afectado → Reprocesar → verificar que la fuente dejó de ser preliminar cuando hay topografía, más validaciones y vista previa → publicar si corresponde. Si cambia un acumulado, incluir también los días posteriores impactados.
3. **M15 existe, falta volumen:** Módulos → Datos base → Buscar → elegir registro → informar m³ totales y verificar TMS → Actualizar registro → revisar densidad → Reprocesar desde la primera fecha afectada → revisar. Si ya estaba congelado, la base se propaga al guardar, pero `calculo_diario` no se recalcula al guardar.
4. **M16 ausente:** Módulos → Datos base → Agregar módulo → PAD/campaña/módulo/TMS/m³ → Insertar → Reprocesar el rango donde hay movimiento y sus derivados → revisar congelamiento, secuencia, apertura y cifras. Insertar solo no garantiza congelamiento: el SP de preparación requiere base positiva y aplica ventana de 90 días/5 siguientes, con evidencia operacional o precongelamiento pertinente. Si el caso queda fuera de ese alcance, revisar alerta y tratarlo como excepción; pulsar el botón verde usa la misma ventana y no resuelve por sí mismo un historial arbitrario.
5. **Corrección histórica:** identificar fecha inicial realmente afectada, fecha de corte y último día cuya cifra/acumulado puede cambiar → seleccionar todo ese tramo → Reprocesar → revisar cada día y vista previa antes de publicar. El margen `DiasReproceso=7` del cálculo/publicación no amplía el sync ni la carga CV25. Un tramo totalmente anterior al corte no es reprocesable por los SP actuales.
6. **Ajuste documentado:** Registrar ajuste con motivo y antecedente → comprobar `PROPUESTO` → tramitar aprobación fuera de este panel → comprobar `APROBADO` → Reprocesar el tramo afectado → revisar cálculo y publicar si corresponde. No asumir que Registrar ajuste o Publicar lo aprueba.

## Antes de publicar

**Obligatorio operacional:** Reprocesar el rango completo del cambio; confirmar ejecución sin error; revisar `Validaciones antes de publicar` y resolver bloqueos activos; comprobar `Vista previa antes de publicar` por día/PAD y que refleje los cambios. Confirmar expresamente el alcance de fecha: el SP final puede extender el inicio a `fin - 7 días`.

**Recomendado según el cambio:** Resumen general, CV25 vs Topografía, Avance diario, Cuadratura, Tonelaje remanente y Rendimiento. Una fila preliminar CV25 o brecha >10 % es advertencia, requiere explicación; no es bloqueo técnico por sí misma. El historial de eventos de automatización es evidencia para investigar, no diagnóstico actual automático.

**Limitación actual:** El botón Publicar no se deshabilita ante `NO PUBLICAR`; la confirmación tampoco llama `db.semaforo`. La disciplina anterior es necesaria porque el backend no la impone.

Fuentes: `reclamo/panel.py:976-1025,1075-1188,1830-1915,1982-2190`; `reclamo/db.py:317-423,429-695`; `live_definitions.json` de este directorio.
