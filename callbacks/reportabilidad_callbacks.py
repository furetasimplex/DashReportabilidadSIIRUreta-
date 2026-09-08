"""
reportabilidad_callbacks.py
===========================
Callbacks para la integración de funcionalidades datos_reconciliados_of
en el dashboard de reportabilidad.

Incluye:
- Carga de datos de reconciliación
- Procesamiento de distribución proporcional
- Validación de integridad
- Registro en auditoría
- Marcado como oficial
- Comparativo de versiones
"""

from dash import callback, Input, Output, State, html, dcc, no_update, ctx
import dash_bootstrap_components as dbc
from datetime import date, datetime
import pandas as pd
import logging
import plotly.graph_objects as go
import plotly.express as px

# Importar módulos de integración
from modules.data_loader import get_data_loader
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


# ============================================================================
# CALLBACK 1: Cargar casos disponibles
# ============================================================================

@callback(
    Output('dropdown-caso-recon', 'options'),
    Input('store-init-casos', 'data'),
    prevent_initial_call=False
)
def load_casos(_):
    """Carga casos de balance disponibles"""
    try:
        # TODO: Reemplazar con query a BD
        casos = [
            {'label': 'CASO_001', 'value': 'CASO_001'},
            {'label': 'CASO_002', 'value': 'CASO_002'},
            {'label': 'CASO_003', 'value': 'CASO_003'},
        ]
        return casos
    except Exception as e:
        logger.error(f"Error cargando casos: {e}")
        return []


# ============================================================================
# CALLBACK 2: Cargar run_ids disponibles para el caso y rango seleccionado
# ============================================================================

@callback(
    [Output('dropdown-run-id-recon', 'options'),
     Output('dropdown-run-id-recon', 'value')],
    [Input('dropdown-caso-recon', 'value'),
     Input('date-inicio-recon', 'date'),
     Input('date-fin-recon', 'date')],
    prevent_initial_call=True
)
def load_run_ids(caso, fecha_inicio, fecha_fin):
    """Carga run_ids disponibles para el caso y rango de fechas"""
    if not caso or not fecha_inicio or not fecha_fin:
        return [], None
    
    try:
        run_ids = data_loader.get_available_runs(
            caso_balance=caso,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        if not run_ids:
            return [], None
        
        options = [
            {
                'label': f"{row['run_id']} ({row['estado']})",
                'value': row['run_id']
            }
            for _, row in run_ids.iterrows()
        ]
        
        # Seleccionar oficial por defecto si existe
        oficial = run_ids[run_ids['estado'] == 'OFICIAL']['run_id'].values
        default_value = oficial[0] if len(oficial) > 0 else options[0]['value']
        
        return options, default_value
    except Exception as e:
        logger.error(f"Error cargando run_ids: {e}")
        return [], None


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
    """Procesa la reconciliación y calcula ajustes proporcionales"""
    
    if not all([caso, fecha_inicio, fecha_fin, run_id]):
        alert_msg = dbc.Alert("Seleccione todos los parámetros", color="warning")
        empty_fig = go.Figure()
        return ([], [], alert_msg, True, {}, True, True, True, empty_fig, empty_fig)
    
    try:
        # Cargar datos
        recon_data = data_loader.get_reconciliation_results(
            caso_balance=caso,
            run_id=run_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        daily_data = data_loader.get_daily_measured_data(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        if recon_data.empty or daily_data.empty:
            alert_msg = dbc.Alert("No hay datos disponibles", color="warning")
            empty_fig = go.Figure()
            return ([], [], alert_msg, True, {}, True, True, True, empty_fig, empty_fig)
        
        # Procesar reconciliación
        ajustes = recon_engine.process_all_flujos(
            recon_data=recon_data,
            daily_data=daily_data
        )
        
        # Preparar datos para la tabla
        tabla_data = ajustes['datos_consolidados'].to_dict('records')
        
        # Definir columnDefs para ag-grid
        columnDefs = [
            {"headerName": "Fecha", "field": "fecha_dia", "filter": "agDateColumnFilter"},
            {"headerName": "Flujo", "field": "flujo_id"},
            {"headerName": "Valor Medido", "field": "valor_medido", "type": "rightAligned"},
            {"headerName": "% Aporte", "field": "porcentaje_aporte", "type": "rightAligned"},
            {"headerName": "Diferencia", "field": "diferencia_reconciliada", "type": "rightAligned"},
            {"headerName": "Ajuste Aplicado", "field": "ajuste_aplicado", "type": "rightAligned"},
            {"headerName": "Valor Final", "field": "valor_final", "type": "rightAligned"},
        ]
        
        # Guardar datos en store
        store_data = {
            'caso': caso,
            'run_id': run_id,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'ajustes': tabla_data,
            'resumen': ajustes['resumen'].to_dict('records'),
        }
        
        # Gráficos
        fig_dias = px.bar(
            ajustes['datos_consolidados'],
            x='fecha_dia',
            y='ajuste_aplicado',
            color='flujo_id',
            title="Ajustes Aplicados por Día",
            labels={'ajuste_aplicado': 'Ajuste (t)', 'fecha_dia': 'Fecha'}
        )
        
        fig_flujos = px.pie(
            ajustes['datos_consolidados'],
            values='valor_final',
            names='flujo_id',
            title="Distribución de Valores Finales por Flujo"
        )
        
        mensaje = dbc.Alert(
            [html.I(className="bi bi-check-circle me-2"),
             f"Reconciliación procesada exitosamente. {len(tabla_data)} registros."],
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
# CALLBACK 4: VALIDACIONES
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
    """Ejecuta todas las validaciones sobre los datos procesados"""
    
    if not store_data:
        empty = html.P("Sin datos procesados", className="text-muted")
        return (empty, empty, empty, empty, {})
    
    try:
        df = pd.DataFrame(store_data['ajustes'])
        
        # Validación 1: Suma integridad
        val_suma = validators.validate_sum_integrity(df)
        
        if val_suma['es_valido']:
            alert_suma = dbc.Alert(
                [html.I(className="bi bi-check-circle-fill me-2", style={"color": "green"}),
                 f"✓ Suma válida. Total: {val_suma['suma_final']:.2f}, "
                 f"Diferencia: {val_suma['diferencia']:.6f} ({val_suma['porcentaje']:.4f}%)"],
                color="success"
            )
        else:
            alert_suma = dbc.Alert(
                [html.I(className="bi bi-x-circle-fill me-2", style={"color": "red"}),
                 f"✗ Suma NO válida. Diferencia: {val_suma['diferencia']:.2f}"],
                color="danger"
            )
        
        # Validación 2: Días con valor cero
        dias_cero = validators.check_zero_day_adjustments(df)
        
        if len(dias_cero) == 0:
            alert_cero = dbc.Alert(
                [html.I(className="bi bi-check-circle-fill me-2", style={"color": "green"}),
                 "✓ Sin ajustes en días con valor_medido = 0"],
                color="success"
            )
        else:
            alert_cero = dbc.Alert(
                [html.I(className="bi bi-exclamation-triangle-fill me-2", style={"color": "orange"}),
                 f"⚠ Se encontraron {len(dias_cero)} días con valor cero ajustados"],
                color="warning"
            )
        
        # Validación 3: Outliers
        outliers = validators.detect_outliers(df)
        
        if len(outliers) == 0:
            alert_outliers = dbc.Alert(
                [html.I(className="bi bi-check-circle-fill me-2", style={"color": "green"}),
                 "✓ Sin anomalías detectadas (Z-score)"],
                color="success"
            )
        else:
            alert_outliers = dbc.Alert(
                [html.I(className="bi bi-flag-fill me-2", style={"color": "red"}),
                 f"🚩 {len(outliers)} anomalías detectadas"],
                color="warning"
            )
        
        # Resumen
        resumen = dbc.Row([
            dbc.Col([
                html.Div(f"Registros procesados: {len(df)}", className="small fw-semibold"),
                html.Div(f"Flujos únicos: {df['flujo_id'].nunique()}", className="small"),
            ]),
            dbc.Col([
                html.Div(f"Suma total ajustes: {df['ajuste_aplicado'].sum():.2f}", 
                        className="small fw-semibold"),
                html.Div(f"Rango de ajustes: [{df['ajuste_aplicado'].min():.2f}, "
                        f"{df['ajuste_aplicado'].max():.2f}]", className="small"),
            ]),
        ], className="g-3")
        
        store_validaciones = {
            'suma_valida': val_suma['es_valido'],
            'dias_cero_count': len(dias_cero),
            'outliers_count': len(outliers),
        }
        
        return (alert_suma, alert_cero, alert_outliers, resumen, store_validaciones)
    
    except Exception as e:
        logger.error(f"Error en validaciones: {e}")
        error_msg = dbc.Alert(f"Error: {str(e)}", color="danger")
        return (error_msg, error_msg, error_msg, error_msg, {})


# ============================================================================
# CALLBACK 5: MARCAR COMO OFICIAL Y AUDITORÍA
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
    """Marca la versión como oficial y registra en auditoría"""
    
    if not store_data:
        mensaje = dbc.Alert("Sin datos para registrar", color="warning")
        return (False, mensaje, True)
    
    try:
        df = pd.DataFrame(store_data['ajustes'])
        
        # Registrar en auditoría
        audit_id = audit_mgr.record_adjustment(
            caso_balance=store_data['caso'],
            run_id=store_data['run_id'],
            fecha_inicio=store_data['fecha_inicio'],
            fecha_fin=store_data['fecha_fin'],
            datos_ajustados=df,
            usuario='lcortes',  # TODO: Obtener de sesión
            metodo='Proporcional_Aporte_Diario'
        )
        
        # Marcar como oficial
        audit_mgr.mark_balance_official(
            caso_balance=store_data['caso'],
            run_id=store_data['run_id'],
            fecha_inicio=store_data['fecha_inicio'],
            fecha_fin=store_data['fecha_fin'],
            usuario='lcortes'
        )
        
        mensaje = dbc.Alert(
            [html.I(className="bi bi-check-circle me-2"),
             f"✓ Registrado con audit_id: {audit_id}. Marcado como oficial."],
            color="success"
        )
        
        return (False, mensaje, True)
    
    except Exception as e:
        logger.error(f"Error marcando oficial: {e}")
        mensaje = dbc.Alert(f"Error: {str(e)}", color="danger")
        return (False, mensaje, True)


# ============================================================================
# CALLBACK 6: CARGAR AUDITORÍA
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
    """Carga historial de auditoría"""
    
    if not all([caso, fecha_inicio, fecha_fin]):
        return [], []
    
    try:
        audit_trail = audit_mgr.generate_trazabilidad_report(
            caso_balance=caso,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        tabla_data = audit_trail.to_dict('records')
        
        columnDefs = [
            {"headerName": "Run ID", "field": "run_id"},
            {"headerName": "Usuario", "field": "usuario_ajuste"},
            {"headerName": "Timestamp", "field": "timestamp_ajuste"},
            {"headerName": "Cantidad Ajustes", "field": "cantidad_ajustes", "type": "rightAligned"},
            {"headerName": "Suma Ajustes", "field": "suma_ajustes", "type": "rightAligned"},
            {"headerName": "Estado", "field": "is_active"},
        ]
        
        return tabla_data, columnDefs
    
    except Exception as e:
        logger.error(f"Error cargando auditoría: {e}")
        return [], []


# ============================================================================
# CALLBACK 7: COMPARAR VERSIONES
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

