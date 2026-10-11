# Auditoría delta THM, PAD2 campaña 10

Consulta de solo lectura sobre DEV (`inventar_SpcHidr`), capturada el 2026-10-07 00:18, hora del servidor. No se ejecutaron procedimientos ni se modificaron datos.

## Archivos

- `auditoria_delta_thm.sql`: consulta reproducible con `LAG`, `ROW_NUMBER`, cruce con Reclamo y clasificación.
- `detalle_diferencias.csv`: primera fila de cada módulo y filas con diferencia superior a 0,001 m³.
- `resumen_modulos.csv`: resumen y descomposición de la brecha final por módulo.
- `comparacion_30_09.csv`: las once filas fuente del 30-09, aun cuando cuadren.
- `resultado.md`: hallazgos, interpretación y propuesta sin aplicar.
- `audit_readonly.py`, `snapshot.json`, `build_report.py`, `analysis.json`: extracción y cálculo reproducibles. El snapshot contiene datos operacionales DEV y definición del SP; mantenerlo en el ámbito del repositorio local.

## Método

Se ordena por `(campaña_id, modulo_id, fecha)`. Para las filas posteriores a la primera se calcula `delta_acumulado = acumulado_actual - acumulado_anterior`. La primera fila usa `arrastre_inicial = acumulado_actual - volumen_diario_fuente`, sin asignar ese arrastre a la fecha de la primera fila. Se compara el diario de la fuente con `reclamo.camiones_reclamo.m3_thm` y con `reclamo.v_camiones_acumulado.m3_camiones_dia`. La fecha ya fue desplazada por el flujo D-1; aquí se compara la fecha almacenada sin un nuevo desplazamiento.

Las categorías de módulos pueden solaparse. La descomposición algebraica sí es aditiva, por módulo:

`acumulado final fuente - acumulado sistema = arrastre inicial + Σ(delta acumulado - diario fuente) + Σ(diario fuente - m3_thm Reclamo) + Σ(m3_thm Reclamo - m3 oficial)`.

Todos los componentes se obtuvieron con `Decimal`; se valida la identidad para cada módulo antes de escribir los CSV. El umbral de hallazgo es **estrictamente mayor** que 0,001 m³. Las cifras CSV se presentan a seis decimales. La primera fila aparece siempre en detalle, incluso si está clasificada `OK`.
