# Callback y parámetros

`generar_reporte(n_clicks_list,f_ini,f_fin,modo_fecha)`; Input pattern `{'type':'report-gen-btn','tipo':ALL}.n_clicks`; States `report-fecha-inicio.date`, `report-fecha-final.date`, `report-fecha-modo.value`; `prevent_initial_call=True`. `ctx.triggered_id['tipo']='representatividad_torres'` selecciona la rama.

Outputs: `report-grafico.children`, `report-tabla.children`, `report-historial.children`, `rep-comentarios-store.data`, `rep-tab-activo-store.data`, `rep-periodo-store.data`. Running informa refresco y deshabilita el botón MATCH; no cambia fechas. En error devuelve Alert, tabla vacía y no_update en cuatro salidas; por tanto puede conservar stores previos.

`sync_modo_y_mes` (:1356) recibe modo `mes` y valor `2026-10`: ejecutada aisladamente desde AST devuelve inicio **2026-10-01**, fin **2026-10-31**. `max_date_allowed` se fija a hoy, pero no recorta el valor fin al construirlo. Evidencia selector_runtime.json; no es captura de una sesión UI particular.

El callback convierte esas fechas a date. Calcula además fin_sql_exclusivo=2026-11-01 para otras ramas, pero la rama Torres usa ini/fin INCLUSIVOS. Store: inicio=2026-10-01, fin=2026-10-31, modo=mes, periodo_mes=2026-10. El paquete del editor impone inicio de cálculo `fin.replace(day=1)`, incluso en rango personalizado. `periodo_mes` cambia la lectura posterior de comentarios/publicabilidad, no la query de cierre.

No hay exigencia de esperar al último día calendario del mes: MAX devuelve cualquier fecha apta dentro del rango. `except Exception as e` muestra str(e), sin reemplazarlo por otro mensaje. El helper de SELECT envuelve errores SQL con texto distinto «Error al obtener la fecha de corte operacional...». El síntoma observado corresponde a ausencia de corte, no demuestra error SQL oculto. No se encontró log/traceback original del clic; sí se reprodujo SELECT NULL con éxito.
