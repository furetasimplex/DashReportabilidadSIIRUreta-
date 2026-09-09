"""
reportabilidad_callbacks.py
===========================
Callbacks para la integración de funcionalidades datos_reconciliados_of
en el dashboard de reportabilidad.

Incluye:
- Carga de datos de reconciliación
- Procesamiento de distribución proporcional (motor real: ajuste_reporte/rep_prod_adjuster.py)
- Validación de integridad (comparativo ajustado vs. target)
- Registro en auditoría (historial real de rep_prod_ajuste_log)
- Marcado como oficial (sp_rep_publish_oficial_validado)
- Comparativo de versiones

NOTA (2026-09-09): Reescrito para usar el pipeline real de reportabilidad
(inventar_SpcHidr.casos_balance / rep_prod_* / ajuste_reporte.rep_prod_adjuster),
en reemplazo de las tablas ficticias (recon_detalle, datos_medidos_diarios)
que nunca existieron en la BD. Ver docstring de modules/data_loader.py para
el detalle de la arquitectura real descubierta.

Pendiente / fuera de alcance de esta pasada: el tab "Comparativo" (callbacks
comparar_versiones / load_versions_for_comparison) sigue usando
modules/versioning.py, que no fue validado contra el esquema real todavía.
"""

from dash import callback, Input, Output, State, html, dcc, no_update, ctx
import dash_bootstrap_components as dbc
from datetime import date, datetime
import pandas as pd
import logging
import io
import plotly.graph_objects as go
import plotly.express as px
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

# Importar módulos de integración
from modules.data_loader import get_data_loader, RUN_ID_NUEVO
from modules.reconciliation_engine import get_reconciliation_engine
from modules.validators import get_validators
from modules.audit_manager import get_audit_manager
from modules.versioning import get_version_control

logger = logging.getLogger(__name__)

# Obtener instancias de módulos
data_loader = get_data_loader()
recon_engine = get_reconciliation_engine()
validators = get_validators()
audit_mgr = get_audit_manager()
version_ctrl = get_version_control()


def _sanitize_df_for_json(df: pd.DataFrame) -> list:
    """Convierte un DataFrame a records aptos para dcc.Store / ag-grid:
    fechas a string ISO, NaN/NaT a None."""
    if df is None or df.empty:
        return []
    d = df.copy()
    for col in d.columns:
        if pd.api.types.is_datetime64_any_dtype(d[col]):
            d[col] = d[col].astype(str)
        elif d[col].dtype == object:
            d[col] = d[col].apply(lambda v: v.isoformat() if hasattr(v, "isoformat") else v)
    d = d.where(pd.notnull(d), None)
    return d.to_dict('records')


# ============================================================================
# CALLBACK 1: Cargar casos disponibles
# ============================================================================

@callback(
    [Output('dropdown-caso-recon', 'options'),
     Output('store-casos-data', 'data')],
    Input('store-init-casos', 'data'),
    prevent_initial_call=False
)
def load_casos(data):
    """Carga casos de balance disponibles desde BD"""
    try:
        df_casos = data_loader.get_available_casos()

        if df_casos.empty:
            logger.warning("No casos disponibles en BD")
            return [], []

        casos = [
            {
                'label': f"{row['nombre_caso']} ({row['fecha_inicio'].strftime('%Y-%m-%d')} a {row['fecha_fin'].strftime('%Y-%m-%d')})",
                'value': row['id']
            }
            for _, row in df_casos.iterrows()
        ]

        # Cache con las fechas de cada caso, para autocompletar Fecha Inicio/Fecha Fin
        # al seleccionar un caso (ver autofill_fechas_caso), sin volver a golpear la BD
        casos_cache = [
            {
                'id': row['id'],
                'fecha_inicio': row['fecha_inicio'].strftime('%Y-%m-%d'),
                'fecha_fin': row['fecha_fin'].strftime('%Y-%m-%d'),
            }
            for _, row in df_casos.iterrows()
        ]

        logger.info(f"✓ {len(casos)} casos cargados desde BD")
        return casos, casos_cache
    except Exception as e:
        logger.error(f"Error cargando casos: {e}")
        return [], []


# ============================================================================
# CALLBACK 1b: Autocompletar Fecha Inicio / Fecha Fin al seleccionar un caso
# ============================================================================

@callback(
    [Output('date-inicio-recon', 'date'),
     Output('date-fin-recon', 'date')],
    Input('dropdown-caso-recon', 'value'),
    State('store-casos-data', 'data'),
    prevent_initial_call=True
)
def autofill_fechas_caso(caso_id, casos_cache):
    """Al elegir un caso, completa automáticamente su rango de fechas
    (fecha_ini/fecha de casos_balance), para que no haya que ingresarlas a mano.
    Esto dispara en cadena load_run_ids (que depende de estas fechas)."""
    if not caso_id or not casos_cache:
        return no_update, no_update

    caso = next((c for c in casos_cache if c['id'] == caso_id), None)
    if not caso:
        logger.warning(f"Caso id={caso_id} no encontrado en cache de casos")
        return no_update, no_update

    return caso['fecha_inicio'], caso['fecha_fin']


# ============================================================================
# CALLBACK 2: Cargar run_ids disponibles para el caso (rep_prod_ajuste_log)
# ============================================================================

@callback(
    [Output('dropdown-run-id-recon', 'options'),
     Output('dropdown-run-id-recon', 'value'),
     Output('dropdown-run-id-recon', 'style'),
     Output('label-run-id-recon', 'style'),
     Output('caption-run-id-auto', 'style')],
    [Input('dropdown-caso-recon', 'value'),
     Input('date-inicio-recon', 'date'),
     Input('date-fin-recon', 'date')],
    prevent_initial_call=True
)
def load_run_ids(caso, fecha_inicio, fecha_fin):
    """Carga corridas exitosas previas del motor de ajuste para el caso.

    Simplificación UX (2026-09-09, a pedido de Luis): el Run ID sólo se
    muestra/pide al usuario cuando REALMENTE hay una decisión que tomar
    (existen corridas previas entre las cuales elegir vs. calcular una
    nueva). Si el caso nunca se ha corrido, no tiene sentido pedirlo: se
    oculta el selector y se usa "ejecutar nuevo ajuste" de forma interna
    y automática."""
    oculto = {"display": "none"}
    visible = {}

    if not caso or not fecha_inicio or not fecha_fin:
        return [], None, oculto, oculto, oculto

    try:
        run_ids = data_loader.get_available_runs(
            caso_balance=caso,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        options = [{
            'label': "🔄 Ejecutar nuevo ajuste (recalcular reparto proporcional)",
            'value': RUN_ID_NUEVO,
        }]

        hay_historial = not run_ids.empty
        if hay_historial:
            options += [
                {
                    'label': f"Run {row['solver_run_id'][:8]}… - {row['oficializado_en'].strftime('%Y-%m-%d %H:%M')}",
                    'value': row['solver_run_id']
                }
                for _, row in run_ids.iterrows()
            ]

        # Por defecto: la corrida existente más reciente si hay alguna,
        # o "nuevo ajuste" si el caso nunca se ha corrido.
        default_value = options[1]['value'] if len(options) > 1 else RUN_ID_NUEVO

        if hay_historial:
            # Hay una decisión real que tomar: mostrar el selector.
            return options, default_value, visible, visible, oculto
        else:
            # Sin corridas previas: no se pide nada, se usa "nuevo ajuste"
            # internamente (el value queda seteado igual, sólo oculto).
            return options, default_value, oculto, oculto, visible
    except Exception as e:
        logger.error(f"Error cargando run_ids: {e}")
        return [], None, oculto, oculto, oculto


# ============================================================================
# CALLBACK 3: PROCESAR RECONCILIACIÓN (callback principal)
# ============================================================================

@callback(
    [Output('tabla-ajustes-recon', 'rowData'),
     Output('tabla-ajustes-recon', 'columnDefs'),
     Output('alert-procesar-recon', 'children'),
     Output('alert-procesar-recon', 'is_open'),
     Output('store-datos-procesados', 'data'),
     Output('btn-marcar-oficial', 'disabled'),
     Output('btn-exportar-recon-excel', 'disabled'),
     Output('btn-ejecutar-validaciones', 'disabled'),
     Output('grafico-ajustes-por-dia', 'figure'),
     Output('grafico-distribucion-flujos', 'figure')],
    Input('btn-procesar-recon', 'n_clicks'),
    [State('dropdown-caso-recon', 'value'),
     State('date-inicio-recon', 'date'),
     State('date-fin-recon', 'date'),
     State('dropdown-run-id-recon', 'value')],
    prevent_initial_call=True
)
def procesar_reconciliacion(n_clicks, caso, fecha_inicio, fecha_fin, run_id):
    """Procesa la reconciliación: si run_id es RUN_ID_NUEVO ejecuta el motor
    de reparto proporcional (ajuste_reporte.rep_prod_adjuster) para generar
    una corrida nueva; si no, carga una corrida ya existente."""

    if not all([caso, fecha_inicio, fecha_fin, run_id]):
        alert_msg = dbc.Alert("Seleccione todos los parámetros", color="warning")
        empty_fig = go.Figure()
        return ([], [], alert_msg, True, {}, True, True, True, empty_fig, empty_fig)

    try:
        run_id_efectivo = run_id
        recien_calculado = False

        if run_id == RUN_ID_NUEVO:
            resultado = data_loader.ejecutar_nuevo_ajuste(caso)
            run_id_efectivo = resultado['run_id']
            recien_calculado = True

        # Datos diarios ya ajustados (post reparto proporcional)
        ajustado_df = data_loader.get_reconciliation_results(
            caso_balance=caso,
            run_id=run_id_efectivo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        if ajustado_df.empty:
            alert_msg = dbc.Alert(
                f"No hay datos ajustados para el run {run_id_efectivo}.",
                color="warning"
            )
            empty_fig = go.Figure()
            return ([], [], alert_msg, True, {}, True, True, True, empty_fig, empty_fig)

        # Comparativo ajustado vs. target (chancado / sal / finos / reclamo / SRR)
        comparativo = data_loader.get_resumen_comparativo(caso, run_id_efectivo)

        tabla_data = _sanitize_df_for_json(ajustado_df)

        columnas_clave = [
            ("Fecha", "Fecha"),
            ("Chancado (TMS)", "Chancado_TMS_Real"),
            ("Sal Turno A", "Sal_turno_A"),
            ("Sal Turno B", "Sal_Turno_B"),
            ("Sal prom. día", "Sal_promedio_dia"),
            ("Apilado Real (TMS)", "Apilado_TMS_Real"),
            ("Apilado Plan (TMS)", "Apilado_TMS_Plan"),
            ("Ley CuT Real (%)", "Ley_CuT_Real"),
            ("Cobre fino Apilado Real", "Cobre_fino_Apilado_Real"),
            ("Factor Chancado", "factor_chancado"),
            ("Factor Sal", "factor_sal"),
            ("Factor Finos", "factor_finos"),
        ]
        columnDefs = [
            {"headerName": h, "field": f, "filter": "agDateColumnFilter" if f == "Fecha" else True,
             "type": "rightAligned" if f not in ("Fecha",) else None}
            for h, f in columnas_clave if f in ajustado_df.columns
        ]

        store_data = {
            'caso': caso,
            'run_id': run_id_efectivo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'ajustes': tabla_data,
            'comparativo': comparativo,
        }

        # Gráficos
        fig_dias = go.Figure()
        if 'Fecha' in ajustado_df.columns and 'Chancado_TMS_Real' in ajustado_df.columns:
            fig_dias = px.line(
                ajustado_df, x='Fecha', y='Chancado_TMS_Real', markers=True,
                title="Chancado diario ajustado (TMS)",
                labels={'Chancado_TMS_Real': 'TMS', 'Fecha': 'Fecha'}
            )

        df_comp = pd.DataFrame(comparativo.get('rows', []))
        fig_flujos = go.Figure()
        if not df_comp.empty:
            fig_flujos = px.bar(
                df_comp, x='metrica', y=['ajustado', 'target'], barmode='group',
                title="Ajustado vs. Target por métrica",
                labels={'value': 'Valor', 'metrica': 'Métrica'}
            )
            fig_flujos.update_layout(xaxis_tickangle=-30)

        origen = "recién calculado" if recien_calculado else "corrida existente"
        mensaje = dbc.Alert(
            [html.I(className="bi bi-check-circle me-2"),
             f"Reconciliación procesada ({origen}). Run {run_id_efectivo}. "
             f"{len(tabla_data)} días cargados."],
            color="success"
        )

        return (tabla_data, columnDefs, mensaje, True, store_data,
                False, False, False, fig_dias, fig_flujos)

    except Exception as e:
        logger.error(f"Error procesando reconciliación: {e}")
        mensaje = dbc.Alert(
            [html.I(className="bi bi-exclamation-triangle me-2"),
             f"Error: {str(e)}"],
            color="danger"
        )
        empty_fig = go.Figure()
        return ([], [], mensaje, True, {}, True, True, True, empty_fig, empty_fig)


# ============================================================================
# CALLBACK 3b: EXPORTAR EXCEL (datos ajustados + comparativo del run procesado)
# ============================================================================

def _autoajustar_anchos_columnas(ws):
    """Ajusta el ancho de cada columna al contenido mas largo (con tope)."""
    for col_cells in ws.columns:
        longitud = max((len(str(c.value)) for c in col_cells if c.value is not None), default=8)
        letra = get_column_letter(col_cells[0].column)
        ws.column_dimensions[letra].width = min(max(longitud + 2, 10), 40)


def _escribir_hoja_df(wb, nombre_hoja, df):
    """Escribe un DataFrame en una hoja nueva del workbook, con encabezado
    resaltado y columnas autoajustadas."""
    ws = wb.create_sheet(title=nombre_hoja[:31])  # Excel limita a 31 caracteres
    if df is None or df.empty:
        ws.append(["Sin datos"])
        return ws

    ws.append(list(df.columns))
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="E86D1F", end_color="E86D1F", fill_type="solid")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for _, row in df.iterrows():
        ws.append(list(row.values))

    _autoajustar_anchos_columnas(ws)
    ws.freeze_panes = "A2"
    return ws


@callback(
    Output('download-recon-excel', 'data'),
    Input('btn-exportar-recon-excel', 'n_clicks'),
    State('store-datos-procesados', 'data'),
    prevent_initial_call=True
)
def exportar_excel_recon(n_clicks, store_data):
    """Exporta a Excel los datos ajustados (post reparto proporcional) y el
    comparativo ajustado-vs-target del run actualmente procesado (el mismo
    que se ve en la tabla/gráficos de la pestaña 'Datos Reconciliados')."""

    if not store_data or 'ajustes' not in store_data:
        logger.warning("Exportar Excel: sin datos procesados (presione 'Procesar' primero).")
        return no_update

    try:
        df_ajustes = pd.DataFrame(store_data.get('ajustes') or [])
        comparativo = store_data.get('comparativo') or {}
        df_comparativo = pd.DataFrame(comparativo.get('rows') or [])

        wb = Workbook()
        wb.remove(wb.active)  # quitar la hoja "Sheet" default

        _escribir_hoja_df(wb, "Datos Ajustados", df_ajustes)
        _escribir_hoja_df(wb, "Comparativo vs Target", df_comparativo)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        caso = store_data.get('caso')
        run_id = str(store_data.get('run_id') or '')
        filename = f"ajustes_reconciliacion_caso{caso}_{run_id[:8]}.xlsx"

        return dcc.send_bytes(buffer.getvalue(), filename)

    except Exception as e:
        logger.error(f"Error exportando a Excel: {e}")
        return no_update


# ============================================================================
# CALLBACK 4: VALIDACIONES (comparativo ajustado vs. target)
# ============================================================================

@callback(
    [Output('validacion-suma-integridad', 'children'),
     Output('validacion-dias-cero', 'children'),
     Output('validacion-outliers', 'children'),
     Output('resumen-validaciones', 'children'),
     Output('store-validaciones', 'data')],
    Input('btn-ejecutar-validaciones', 'n_clicks'),
    State('store-datos-procesados', 'data'),
    prevent_initial_call=True
)
def ejecutar_validaciones(n_clicks, store_data):
    """Muestra el comparativo ajustado-vs-target (build_resumen_comparativo_run)
    calculado en el callback de Procesar, con estado OK/DESVIADO/SIN_TARGET
    por métrica."""

    if not store_data or 'comparativo' not in store_data:
        empty = html.P("Sin datos procesados. Presione 'Procesar' primero.", className="text-muted")
        return (empty, empty, empty, empty, {})

    try:
        comparativo = store_data['comparativo']
        rows = comparativo.get('rows', [])
        df_rows = pd.DataFrame(rows)

        if df_rows.empty:
            empty = html.P("Sin métricas comparables", className="text-muted")
            return (empty, empty, empty, empty, {})

        n_ok = int((df_rows['estado'] == 'OK').sum())
        n_desviado = int((df_rows['estado'] == 'DESVIADO').sum())
        n_sin_target = int((df_rows['estado'] == 'SIN_TARGET').sum())

        if n_desviado == 0:
            alert_global = dbc.Alert(
                [html.I(className="bi bi-check-circle-fill me-2", style={"color": "green"}),
                 f"✓ Todas las métricas dentro de tolerancia ({n_ok} OK)."],
                color="success"
            )
        else:
            metricas_desviadas = ", ".join(df_rows.loc[df_rows['estado'] == 'DESVIADO', 'metrica'].tolist())
            alert_global = dbc.Alert(
                [html.I(className="bi bi-x-circle-fill me-2", style={"color": "red"}),
                 f"✗ {n_desviado} métrica(s) desviada(s) del target: {metricas_desviadas}"],
                color="danger"
            )

        if n_sin_target == 0:
            alert_sin_target = dbc.Alert(
                [html.I(className="bi bi-check-circle-fill me-2", style={"color": "green"}),
                 "✓ Todas las métricas tienen target definido"],
                color="success"
            )
        else:
            metricas_sin_target = ", ".join(df_rows.loc[df_rows['estado'] == 'SIN_TARGET', 'metrica'].tolist())
            alert_sin_target = dbc.Alert(
                [html.I(className="bi bi-exclamation-triangle-fill me-2", style={"color": "orange"}),
                 f"⚠ {n_sin_target} métrica(s) sin target en rep_prod_targets: {metricas_sin_target}"],
                color="warning"
            )

        # Tabla detalle como filas de texto (sin ag-grid dedicado en este placeholder)
        filas_detalle = []
        for r in rows:
            color = {"OK": "green", "DESVIADO": "red", "SIN_TARGET": "orange"}.get(r['estado'], "black")
            dif_pct_txt = f"{r['dif_pct']:.2f}%" if r.get('dif_pct') is not None else "s/d"
            filas_detalle.append(
                html.Div(
                    f"{r['metrica']}: ajustado={r['ajustado']:.2f} · target={r['target']:.2f} · "
                    f"dif={dif_pct_txt} · {r['estado']}",
                    className="small", style={"color": color}
                )
            )
        alert_detalle = html.Div(filas_detalle)

        resumen = dbc.Row([
            dbc.Col([
                html.Div(f"Métricas evaluadas: {len(rows)}", className="small fw-semibold"),
                html.Div(f"OK: {n_ok} · Desviadas: {n_desviado} · Sin target: {n_sin_target}", className="small"),
            ]),
            dbc.Col([
                html.Div(f"Periodo: {comparativo.get('periodo', {}).get('fecha_inicio')} a "
                         f"{comparativo.get('periodo', {}).get('fecha_fin')}", className="small fw-semibold"),
                html.Div(f"Run: {comparativo.get('run_id')}", className="small"),
            ]),
        ], className="g-3")

        store_validaciones = {
            'n_ok': n_ok,
            'n_desviado': n_desviado,
            'n_sin_target': n_sin_target,
            'rows': rows,
        }

        return (alert_global, alert_sin_target, alert_detalle, resumen, store_validaciones)

    except Exception as e:
        logger.error(f"Error en validaciones: {e}")
        error_msg = dbc.Alert(f"Error: {str(e)}", color="danger")
        return (error_msg, error_msg, error_msg, error_msg, {})


# ============================================================================
# CALLBACK 5: MARCAR COMO OFICIAL (sp_rep_publish_oficial_validado)
# ============================================================================

@callback(
    [Output('modal-confirmar-oficial', 'is_open', allow_duplicate=True),
     Output('alert-procesar-recon', 'children', allow_duplicate=True),
     Output('alert-procesar-recon', 'is_open', allow_duplicate=True)],
    Input('btn-marcar-oficial', 'n_clicks'),
    State('store-datos-procesados', 'data'),
    prevent_initial_call=True
)
def marcar_oficial(n_clicks, store_data):
    """Publica el run procesado como la versión oficial vigente del periodo
    (Datos_conciliados_of_ver), vía sp_rep_publish_oficial_validado. El SP
    se encarga de la regla de negocio 'solo un oficial por periodo'."""

    if not store_data or 'run_id' not in store_data:
        mensaje = dbc.Alert("Sin datos para registrar. Presione 'Procesar' primero.", color="warning")
        return (False, mensaje, True)

    try:
        resultado = data_loader.marcar_run_oficial(
            caso_id=store_data['caso'],
            run_id=store_data['run_id'],
            usuario='lcortes',  # TODO: obtener usuario real de la sesión de login
            resumen=store_data.get('comparativo'),
        )

        mensaje = dbc.Alert(
            [html.I(className="bi bi-check-circle me-2"),
             f"✓ Run {store_data['run_id']} marcado como oficial. "
             f"validation_id={resultado['validation_id']}, filas publicadas={resultado['rows_published']}."],
            color="success"
        )

        return (False, mensaje, True)

    except Exception as e:
        logger.error(f"Error marcando oficial: {e}")
        mensaje = dbc.Alert(f"Error: {str(e)}", color="danger")
        return (False, mensaje, True)


# ============================================================================
# CALLBACK 6: CARGAR AUDITORÍA (historial real de rep_prod_ajuste_log)
# ============================================================================

@callback(
    [Output('tabla-auditoria', 'rowData'),
     Output('tabla-auditoria', 'columnDefs')],
    Input('btn-cargar-auditoria', 'n_clicks'),
    [State('dropdown-caso-recon', 'value'),
     State('date-inicio-recon', 'date'),
     State('date-fin-recon', 'date')],
    prevent_initial_call=True
)
def cargar_auditoria(n_clicks, caso, fecha_inicio, fecha_fin):
    """Carga el historial COMPLETO (éxitos y fallos) de corridas del motor
    de ajuste para el caso seleccionado, desde rep_prod_ajuste_log."""

    if not caso:
        return [], []

    try:
        historial = data_loader.get_historial_ajustes(caso)

        if historial.empty:
            return [], []

        historial = historial.copy()
        historial['ok'] = historial['ok'].map({True: '✓ Exitoso', False: '✗ Fallido'})
        tabla_data = _sanitize_df_for_json(historial)

        columnDefs = [
            {"headerName": "Run ID", "field": "run_id"},
            {"headerName": "Periodo desde", "field": "fecha_ini"},
            {"headerName": "Periodo hasta", "field": "fecha_fin"},
            {"headerName": "Inicio corrida", "field": "ts_inicio"},
            {"headerName": "Fin corrida", "field": "ts_fin"},
            {"headerName": "Resultado", "field": "ok"},
            {"headerName": "Mensaje", "field": "mensaje", "wrapText": True, "autoHeight": True},
        ]

        return tabla_data, columnDefs

    except Exception as e:
        logger.error(f"Error cargando auditoría: {e}")
        return [], []


# ============================================================================
# CALLBACK 7: COMPARAR VERSIONES
# (Pendiente: version_ctrl / modules/versioning.py no ha sido validado
#  contra el esquema real en esta sesión. Se deja tal como estaba.)
# ============================================================================

@callback(
    [Output('resumen-comparativo', 'children'),
     Output('tabla-comparativo', 'rowData'),
     Output('tabla-comparativo', 'columnDefs'),
     Output('grafico-comparativo', 'figure'),
     Output('store-comparativo', 'data')],
    Input('btn-comparar-versiones', 'n_clicks'),
    [State('dropdown-caso-recon', 'value'),
     State('date-inicio-recon', 'date'),
     State('date-fin-recon', 'date'),
     State('dropdown-run-v1', 'value'),
     State('dropdown-run-v2', 'value')],
    prevent_initial_call=True
)
def comparar_versiones(n_clicks, caso, fecha_inicio, fecha_fin, run_v1, run_v2):
    """Compara dos versiones del balance"""

    if not all([caso, fecha_inicio, fecha_fin, run_v1, run_v2]):
        msg = html.P("Seleccione dos versiones", className="text-muted")
        empty_fig = go.Figure()
        return (msg, [], [], empty_fig, {})

    try:
        comparativo = version_ctrl.compare_versions(
            caso_balance=caso,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            run_id_v1=run_v1,
            run_id_v2=run_v2
        )

        # Resumen
        resumen = dbc.Row([
            dbc.Col([
                html.Div(f"Días diferentes: {comparativo['dias_diferentes']}",
                        className="small fw-semibold"),
                html.Div(f"Suma diferencias: {comparativo['suma_diferencias']:.2f}",
                        className="small"),
            ]),
            dbc.Col([
                html.Div(f"Máx diferencia: {comparativo['max_diferencia']:.2f}",
                        className="small fw-semibold"),
                html.Div(f"% cambio: {comparativo['porcentaje_cambio']:.2f}%",
                        className="small"),
            ]),
        ], className="g-3")

        # Tabla de diferencias
        tabla_data = comparativo['diferencias'].to_dict('records')
        columnDefs = [
            {"headerName": "Fecha", "field": "fecha_dia"},
            {"headerName": "V1", "field": "valor_v1", "type": "rightAligned"},
            {"headerName": "V2", "field": "valor_v2", "type": "rightAligned"},
            {"headerName": "Diferencia", "field": "diferencia", "type": "rightAligned"},
            {"headerName": "% Cambio", "field": "pct_cambio", "type": "rightAligned"},
        ]

        # Gráfico
        fig = px.bar(
            comparativo['diferencias'],
            x='fecha_dia',
            y='diferencia',
            title=f"Diferencias entre {run_v1} y {run_v2}",
            labels={'diferencia': 'Diferencia (t)', 'fecha_dia': 'Fecha'}
        )

        store_data = {
            'run_v1': run_v1,
            'run_v2': run_v2,
            'comparativo': comparativo,
        }

        return (resumen, tabla_data, columnDefs, fig, store_data)

    except Exception as e:
        logger.error(f"Error comparando versiones: {e}")
        error_msg = dbc.Alert(f"Error: {str(e)}", color="danger")
        empty_fig = go.Figure()
        return (error_msg, [], [], empty_fig, {})


# ============================================================================
# CALLBACK ADICIONAL: Cargar versiones para comparación
# ============================================================================

@callback(
    [Output('dropdown-run-v1', 'options'),
     Output('dropdown-run-v2', 'options')],
    [Input('dropdown-caso-recon', 'value'),
     Input('date-inicio-recon', 'date'),
     Input('date-fin-recon', 'date')],
    prevent_initial_call=True
)
def load_versions_for_comparison(caso, fecha_inicio, fecha_fin):
    """Carga versiones disponibles para comparación"""

    if not all([caso, fecha_inicio, fecha_fin]):
        return [], []

    try:
        versiones = version_ctrl.list_all_versions(
            caso_balance=caso,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        options = [
            {'label': f"{row['run_id']} ({row['estado']})", 'value': row['run_id']}
            for _, row in versiones.iterrows()
        ]

        return options, options

    except Exception as e:
        logger.error(f"Error cargando versiones: {e}")
        return [], []
