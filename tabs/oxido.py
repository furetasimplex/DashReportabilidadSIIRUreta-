# tabs/oxido.py
import dash
from dash import dcc, html, Input, Output, ALL, ctx, dash_table, State
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Conexión a DB
from db_connection import get_connection

# =========================
#  Constantes del módulo
# =========================
PAD_VALUE = "OXIDOS"  # Este módulo corresponde al tab Óxidos

# =========================
#  Datos dummy visual (solo para grilla)
# =========================
def get_parcela_modulo(cell_index):
    return cell_index, 1

# (Opcional) Info estática para tabla (no usada en cálculos)
base_date = pd.to_datetime('2025-01-01')
data = {
    i: {
        'Estado': ('Activo' if (i + 1) % 2 == 0 else 'Inactivo'),
        'Fecha inicio riego': (base_date + pd.Timedelta(days=i-1)).strftime('%Y-%m-%d'),
        'Fecha drenaje': (base_date + pd.Timedelta(days=i-1+100)).strftime('%Y-%m-%d'),
        'Tipo de riego': ('Ninguno' if ((i + 1) % 2) else ('ILS' if i % 2 == 0 else 'Refino')),
    }
    for i in range(1, 33)
}

# =========================
#  Construcción de grilla (32 parcelas)
# =========================
def create_cell(cell_index):
    outer_style = {
        'border': '1px solid black',
        'textAlign': 'center',
        'width': '85px',
        'backgroundColor': '#adc2cc',
        'color': 'black',
        'fontWeight': 'bold',
        'fontSize': '12px'
    }
    grid_style = {
        'display': 'grid',
        'gridTemplateColumns': '1fr',
        'gridTemplateRows': '1fr',
        'height': '40px',
    }
    inner_cell = html.Div(
        id={'type': 'oxido-inner-cell', 'index': f'{cell_index}-0'},
        className='inner-cell',
        style={'cursor': 'pointer', 'backgroundColor': 'white'},
        n_clicks=0
    )
    return html.Div(
        id={'type': 'grid-cell-container', 'index': cell_index},
        children=[html.Div(f'{cell_index}'), html.Div([inner_cell], style=grid_style)],
        className='grid-cell',
        style=outer_style
    )

top_row_cells = [create_cell(i) for i in range(1, 17)]
bottom_row_cells = [create_cell(i) for i in range(32, 16, -1)]
top_row = html.Div(top_row_cells, style={'display': 'flex', 'flexDirection': 'row', 'gap': '5px'})
bottom_row = html.Div(bottom_row_cells, style={'display': 'flex', 'flexDirection': 'row', 'gap': '5px', 'marginTop': '10px'})
grid_children = [top_row, bottom_row]

# =========================
#  Layout del tab
# =========================
def layout():
 return html.Div([
    # Fila 1: fechas + reset
    html.Div([
        html.Div([
            html.Label("Seleccionar fecha: ", style={'marginLeft': '10px', 'marginRight': '10px'}),
            dcc.DatePickerRange(
                id='oxido-date-picker-range',
                start_date='2024-01-01',
                end_date='2025-07-31',
                display_format='YYYY-MM-DD'
            ),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Div([html.Button('Reiniciar selección', id='oxido-reset-button', className='btn btn-primary', n_clicks=0)])
    ], style={
        'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
        'marginBottom': '8px', 'padding': '0 20px'
    }),

    # Fila 2: Detectar campañas + selector campañas
    html.Div([
        html.Div([
            html.Button('Detectar campañas por fecha', id='oxido-detect-camp-btn', className='btn btn-primary', n_clicks=0),
            dcc.Dropdown(
                id='oxido-campanias',
                options=[],
                value=[],
                multi=True,
                placeholder="Campañas…",
                style={'minWidth': '260px', 'marginLeft': '12px'}
            ),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Div([html.Div(f"PAD: {PAD_VALUE}", style={'fontWeight': 'bold', 'padding': '6px 10px'})])
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
              'marginBottom': '10px', 'padding': '0 20px'}),

    # Grilla de parcelas
    html.Div(
        id='oxido-grid-main-container',
        children=grid_children,  # precargada
        style={
            'display': 'flex','flexDirection': 'column','alignItems': 'center',
            'gap': '10px','padding': '20px','backgroundColor': '#adc2cc',
            'border': '1px solid #ced4da','borderRadius': '10px'
        }
    ),

    html.Div(id='oxido-cell-click-output', children="Click en parcelas para obtener data",
             style={'marginTop': '20px', 'textAlign': 'center', 'fontWeight': 'bold'}),

    # Fila 3: Tabla + Gráfico (Total ponderado)
    html.Div([
        html.Div(
            dash_table.DataTable(
                id='oxido-cell-table',
                columns=[{"name": "Campo", "id": "Field"}, {"name": "Valor", "id": "Value"}],
                data=[],
            ), style={'width': '48%'}
        ),
        html.Div(id='oxido-graph-container', children=[dcc.Graph(id='oxido-cell-graph', figure={})],
                 style={'width': '48%', 'height': '400px'})
    ], style={'display': 'flex', 'flexDirection': 'row', 'justifyContent': 'space-around',
              'marginTop': '5px', 'padding': '2px'}),

    # Fila 4: Gráfico por parcela
    html.Div([
        html.Hr(),
        html.Div("Curvas por parcela (DB)", style={'fontWeight': 'bold', 'margin': '4px 0 8px 0'}),
        dcc.Graph(id='oxido-cell-graph-parcelas', figure={})
    ], style={'width': '100%', 'padding': '0 20px'})
])

# =========================
#  Utilitarios DB
# =========================
def _query_df(sql, params):
    """ Ejecuta SQL usando get_connection() y retorna DataFrame. """
    conn = get_connection()
    try:
        #cur = conn.cursor(dictionary=True)
        cur = conn.cursor()
        if conn.__class__.__module__.startswith("pyodbc"):
            sql = sql.replace('%s',"?")
        print(f'{sql} and parameters {params}')
        cur.execute(sql, params)
        print(cur.description)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
  
        #print(f"rows: {rows}")
        #df = pd.DataFrame(rows,columns=cols)
        df = pd.DataFrame([dict(zip(columns,r)) for r in rows])
        print(df)
        return df
    finally:
        try: cur.close()
        except Exception: pass
        try: conn.close()
        except Exception: pass

def _in_clause(n):
    """Arma un IN (%s,%s,...) para listas."""
    return "(" + ",".join(["%s"] * n) + ")"

def _parse_selected_parcelas(selected_cells):
    """Convierte ['5-0','7-0'] -> [5,7]"""
    if not selected_cells:
        return []
    try:
        return sorted({int(s.split('-')[0]) for s in selected_cells})
    except Exception:
        return []

# =========================
#  Lógica de campañas / cinética
# =========================
def _detect_campanias(pad, parcelas, start_date, end_date):
    """Detecta campañas por fecha en control_ley_ripio_diario; si no hay, busca en res_parcelas_apilado."""
    if not parcelas:
        return []

    # 1) control_ley_ripio_diario (por drenaje)
    sql1 = f"""
        SELECT DISTINCT Campana
        FROM inventar_SpcHidr.control_ley_ripio_diario
        WHERE PAD = %s
          AND Parcela IN {_in_clause(len(parcelas))}
          AND Fecha_drenaje BETWEEN %s AND %s
        ORDER BY Campana
    """
    params1 = [pad] + parcelas + [start_date, end_date]
    df = _query_df(sql1, params1)
    if not df.empty:
        return df['Campana'].astype(int).tolist()

    # 2) fallback: res_parcelas_apilado (por apilado)
    sql2 = f"""
        SELECT DISTINCT Campana
        FROM inventar_SpcHidr.res_parcelas_apilado
        WHERE PAD = %s
          AND Parcela IN {_in_clause(len(parcelas))}
          AND Fecha_apilado BETWEEN %s AND %s
        ORDER BY Campana
    """
    params2 = [pad] + parcelas + [start_date, end_date]
    df2 = _query_df(sql2, params2)
    return df2['Campana'].astype(int).tolist() if not df2.empty else []

def _load_kinetics_total(pad, parcelas, campanias, start_date, end_date):
    """
    Curva total (ponderada):
      fecha, fino_dia_sel, fino_cum_sel, rec_cum_pct, fino_apilado_total
    Denominador = SUM(fino_apilado_cu) (selección)
    Numerador   = SUM(fino_dia) (selección)
    """
    cols = ['fecha', 'fino_dia_sel', 'fino_cum_sel', 'rec_cum_pct', 'fino_apilado_total']
    if not parcelas or not campanias:
        return pd.DataFrame(columns=cols)

    # Denominador
    sql_den = f"""
        SELECT SUM(fino_apilado_cu) AS fino_apilado_total
        FROM inventar_SpcHidr.res_parcelas_apilado
        WHERE PAD = %s
          AND Parcela IN {_in_clause(len(parcelas))}
          AND Campana IN {_in_clause(len(campanias))}
    """
    params_den = [pad] + parcelas + campanias
    df_den = _query_df(sql_den, params_den)
    denom = float(df_den.iloc[0]['fino_apilado_total'] or 0.0) if not df_den.empty else 0.0
    if denom <= 0:
        return pd.DataFrame(columns=cols)

    # Aporte diario total
    sql_day = f"""
        SELECT Fecha_drenaje AS fecha, SUM(fino_dia) AS fino_dia_sel
        FROM inventar_SpcHidr.control_ley_ripio_diario
        WHERE PAD = %s
          AND Parcela IN {_in_clause(len(parcelas))}
          AND Campana IN {_in_clause(len(campanias))}
          AND Fecha_drenaje BETWEEN %s AND %s
        GROUP BY Fecha_drenaje
        ORDER BY Fecha_drenaje
    """
    params_day = [pad] + parcelas + campanias + [start_date, end_date]
    df = _query_df(sql_day, params_day)
    if df.empty:
        return pd.DataFrame(columns=cols)

    df['fino_dia_sel'] = df['fino_dia_sel'].astype(float)
    df = df.sort_values('fecha')
    df['fino_cum_sel'] = df['fino_dia_sel'].cumsum()
    df['rec_cum_pct'] = 100.0 * df['fino_cum_sel'] / denom
    df['fino_apilado_total'] = denom
    return df[['fecha', 'fino_dia_sel', 'fino_cum_sel', 'rec_cum_pct', 'fino_apilado_total']]

def _load_kinetics_by_parcela(pad, parcelas, campanias, start_date, end_date):
    """
    Curvas por parcela:
      fecha, Parcela, rec_cum_pct_parcela
    Cada parcela se normaliza por su propio SUM(fino_apilado_cu).
    """
    if not parcelas or not campanias:
        return pd.DataFrame(columns=['fecha', 'Parcela', 'rec_cum_pct_parcela'])

    # Denominador por parcela
    sql_den = f"""
        SELECT Parcela, SUM(fino_apilado_cu) AS fino_apilado_total
        FROM inventar_SpcHidr.res_parcelas_apilado
        WHERE PAD = %s
          AND Parcela IN {_in_clause(len(parcelas))}
          AND Campana IN {_in_clause(len(campanias))}
        GROUP BY Parcela
    """
    params_den = [pad] + parcelas + campanias
    df_den = _query_df(sql_den, params_den)
    if df_den.empty:
        return pd.DataFrame(columns=['fecha', 'Parcela', 'rec_cum_pct_parcela'])
    df_den['fino_apilado_total'] = df_den['fino_apilado_total'].astype(float)
    den_map = dict(zip(df_den['Parcela'], df_den['fino_apilado_total']))

    # Aporte diario por parcela
    sql_day = f"""
        SELECT Fecha_drenaje AS fecha, Parcela, SUM(fino_dia) AS fino_dia
        FROM inventar_SpcHidr.control_ley_ripio_diario
        WHERE PAD = %s
          AND Parcela IN {_in_clause(len(parcelas))}
          AND Campana IN {_in_clause(len(campanias))}
          AND Fecha_drenaje BETWEEN %s AND %s
        GROUP BY Fecha_drenaje, Parcela
        ORDER BY Fecha_drenaje, Parcela
    """
    params_day = [pad] + parcelas + campanias + [start_date, end_date]
    df = _query_df(sql_day, params_day)
    if df.empty:
        return pd.DataFrame(columns=['fecha', 'Parcela', 'rec_cum_pct_parcela'])

    df['fino_dia'] = df['fino_dia'].astype(float)
    df = df.sort_values(['Parcela', 'fecha'])
    df['fino_cum'] = df.groupby('Parcela')['fino_dia'].cumsum()
    df['rec_cum_pct_parcela'] = df.apply(
        lambda r: (100.0 * r['fino_cum'] / den_map.get(r['Parcela'], np.nan)) if den_map.get(r['Parcela'], 0) > 0 else np.nan,
        axis=1
    )
    return df[['fecha', 'Parcela', 'rec_cum_pct_parcela']]

# =========================
#  Callbacks
# =========================
def register_callbacks(app):

    # 1) Redibuja grilla con coloreo de celdas seleccionadas
    @app.callback(
        Output('oxido-grid-main-container', 'children'),
        Input('selected-cells-oxido', 'data')
    )
    def update_grid_layout(selected_cells):
        def create_zoomed_cell(cell_index):
            outer_style = {
                'border': '1px solid black',
                'textAlign': 'center',
                'width': '75px',
                'backgroundColor': '#adc2cc',
                'color': 'black',
                'fontWeight': 'bold',
                'fontSize': '12px',
                'padding': '2px'
            }
            grid_style = {
                'display': 'grid',
                'gridTemplateColumns': '1fr',
                'gridTemplateRows': '1fr',
                'height': '39px',
            }
            background_color = '#ef8a62' if f'{cell_index}-0' in (selected_cells or []) else 'white'
            inner_cell = html.Div(
                id={'type': 'oxido-inner-cell', 'index': f'{cell_index}-0'},
                className='inner-cell',
                style={'cursor': 'pointer', 'backgroundColor': background_color},
                n_clicks=0
            )
            return html.Div(
                id={'type': 'grid-cell-container', 'index': cell_index},
                children=[html.Div(f'{cell_index}'), html.Div([inner_cell], style=grid_style)],
                className='grid-cell',
                style=outer_style
            )

        top_row_cells = [create_zoomed_cell(i) for i in range(1, 17)]
        bottom_row_cells = [create_zoomed_cell(i) for i in range(32, 16, -1)]
        top_row = html.Div(top_row_cells, style={'display': 'flex', 'flexDirection': 'row', 'gap': '5px'})
        bottom_row = html.Div(bottom_row_cells, style={'display': 'flex', 'flexDirection': 'row', 'gap': '5px', 'marginTop': '10px'})
        return [top_row, bottom_row]

    # 2) Toggle de selección de celdas (robusto con timestamps)
    @app.callback(
        Output('selected-cells-oxido', 'data', allow_duplicate=True),
        Input({'type': 'oxido-inner-cell', 'index': ALL}, 'n_clicks_timestamp'),
        Input('oxido-reset-button', 'n_clicks'),
        State('selected-cells-oxido', 'data'),
        prevent_initial_call=True
    )
    def update_selected_cells(ts_list, reset_clicks, selected_cells):
        if isinstance(ctx.triggered_id, str) and ctx.triggered_id == 'oxido-reset-button':
            return []
        if not ts_list:
            raise dash.exceptions.PreventUpdate

        timestamps = [(t or -1) for t in ts_list]
        last_pos = int(np.argmax(timestamps))
        if timestamps[last_pos] <= 0:
            raise dash.exceptions.PreventUpdate

        try:
            clicked_index = ctx.inputs_list[0][last_pos]['id']['index']
        except Exception:
            raise dash.exceptions.PreventUpdate

        selected_cells = selected_cells or []
        if clicked_index in selected_cells:
            selected_cells = [x for x in selected_cells if x != clicked_index]
        else:
            selected_cells = selected_cells + [clicked_index]
        return selected_cells

    # 3) Detectar campañas por fecha en función de parcelas seleccionadas
    @app.callback(
        Output('oxido-campanias', 'options'),
        Output('oxido-campanias', 'value'),
        Input('oxido-detect-camp-btn', 'n_clicks'),
        State('selected-cells-oxido', 'data'),
        State('oxido-date-picker-range', 'start_date'),
        State('oxido-date-picker-range', 'end_date'),
        prevent_initial_call=True
    )
    def detect_campanias(n, selected_cells, ini, fin):
        parcelas = _parse_selected_parcelas(selected_cells)
        camps = _detect_campanias(PAD_VALUE, parcelas, ini, fin)
        opts = [{'label': str(c), 'value': int(c)} for c in camps]
        return opts, camps  # selecciona todas por defecto

    # 4) Graficar cinética total ponderada y por parcela (DB) + resumen
    @app.callback(
        Output('oxido-cell-click-output', 'children'),
        Output('oxido-cell-table', 'data'),
        Output('oxido-cell-graph', 'figure'),            # total ponderado
        Output('oxido-cell-graph-parcelas', 'figure'),   # por parcela
        Input('selected-cells-oxido', 'data'),
        Input('oxido-date-picker-range', 'start_date'),
        Input('oxido-date-picker-range', 'end_date'),
        Input('oxido-campanias', 'value')
    )
    def update_output(selected_cells, start_date, end_date, campanias):
        if not selected_cells:
            return "Click en parcelas para obtener data", [], {}, {}

        parcelas = _parse_selected_parcelas(selected_cells)

        # Si usuario no ha elegido campañas, detectarlas automáticamente
        if not campanias:
            campanias = _detect_campanias(PAD_VALUE, parcelas, start_date, end_date)

        # Curva total ponderada
        df_total = _load_kinetics_total(PAD_VALUE, parcelas, campanias, start_date, end_date)
        fig_total = go.Figure()
        kpi = np.nan
        denom = 0.0
        if not df_total.empty:
            fig_total.add_trace(go.Scatter(
                x=pd.to_datetime(df_total['fecha']),
                y=df_total['rec_cum_pct'],
                mode='lines',
                name='Recuperación acumulada (DB) [%]'
            ))
            kpi = float(df_total['rec_cum_pct'].iloc[-1])
            denom = float(df_total['fino_apilado_total'].iloc[0])

        fig_total.update_layout(
            plot_bgcolor='#d6e0e5',
            paper_bgcolor='#d6e0e5',
            font_color='#018582',
            yaxis_title="[%]",
            margin=dict(l=10, r=4, b=4, t=4, pad=4),
            legend=dict(xanchor='right', yanchor='bottom')
        )

        # Curvas por parcela
        df_par = _load_kinetics_by_parcela(PAD_VALUE, parcelas, campanias, start_date, end_date)
        fig_par = go.Figure()
        if not df_par.empty:
            df_par['fecha'] = pd.to_datetime(df_par['fecha'])
            for parcela, dfp in df_par.groupby('Parcela'):
                dfp = dfp.sort_values('fecha')
                fig_par.add_trace(go.Scatter(
                    x=dfp['fecha'],
                    y=dfp['rec_cum_pct_parcela'],
                    mode='lines',
                    name=f'Parcela {parcela}'
                ))
        fig_par.update_layout(
            plot_bgcolor='#d6e0e5',
            paper_bgcolor='#d6e0e5',
            font_color='#018582',
            yaxis_title="[%]",
            margin=dict(l=10, r=4, b=4, t=4, pad=4),
            legend=dict(xanchor='right', yanchor='bottom')
        )

        # Tabla de resumen
        dias_de_riego = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
        resumen = [
            {'Field': 'PAD', 'Value': PAD_VALUE},
            {'Field': 'Parcelas seleccionadas', 'Value': ', '.join(map(str, parcelas))},
            {'Field': 'Campañas', 'Value': ', '.join(map(str, campanias)) if campanias else 'N/A'},
            {'Field': 'Días período', 'Value': dias_de_riego},
            {'Field': 'Fino apilado total [t]', 'Value': f"{denom:,.2f}"},
            {'Field': 'Recuperación acumulada DB [%]', 'Value': (f"{kpi:.2f}" if pd.notna(kpi) else 'N/A')},
        ]

        output_text = f"Parcelas {', '.join(map(str, parcelas))} — {PAD_VALUE}" if len(parcelas) > 1 else f"Parcela {parcelas[0]} — {PAD_VALUE}"
        return output_text, resumen, fig_total, fig_par
