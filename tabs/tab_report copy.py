import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np

dash.register_page(__name__, path="/reportabilidad", name="Reportabilidad")

def layout():
    return html.Div([
        dbc.CardHeader(html.H4("📊 Módulo de Reportabilidad", className="p-2 mb-3")),

        # =======================
        # PARÁMETROS DE REPORTE
        # =======================
        dbc.Card([
            dbc.CardHeader("Parámetros de Reporte"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Fecha Inicio"),
                        dcc.DatePickerSingle(
                            id="report-fecha-inicio",
                            display_format="DD-MM-YYYY",
                            date=pd.Timestamp.now().normalize() - pd.Timedelta(days=7)
                        ),
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Fecha Final"),
                        dcc.DatePickerSingle(
                            id="report-fecha-final",
                            display_format="DD-MM-YYYY",
                            date=pd.Timestamp.now().normalize()
                        ),
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Tipo de Reporte"),
                        dcc.Dropdown(
                            id="report-tipo-reporte",
                            options=[
                                {"label": "Producción Diaria", "value": "prod"},
                                {"label": "Balance Semanal", "value": "balance"},
                                {"label": "Conciliación Mensual", "value": "conciliacion"},
                                {"label": "Datos medidos", "value": "Datos medidos"},
                            ],
                            value="prod",
                            placeholder="Seleccione tipo..."
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Button("Generar Reporte", id="report-btn-generar", color="warning", className="mt-4 w-100")
                    ], width=2)
                ])
            ])
        ], className="mb-4 shadow-sm"),

        # =======================
        # VISUALIZACIÓN
        # =======================
        dbc.Card([
            dbc.CardHeader("Visualización del Reporte"),
            dbc.CardBody([
                html.Div(id="report-grafico", className="mb-3"),
                html.Div(id="report-tabla")
            ])
        ], className="mb-4 shadow-sm"),

        # =======================
        # HISTORIAL / EXPORTACIÓN
        # =======================
        dbc.Card([
            dbc.CardHeader("Historial de Reportes"),
            dbc.CardBody([
                html.Div(id="report-historial"),
                dbc.ButtonGroup([
                    dbc.Button("📄 Exportar a Excel", color="success"),
                    dbc.Button("🖨️ Generar PDF", color="primary")
                ], className="mt-2")
            ])
        ], className="shadow-sm mb-4")
    ], className="p-3")


# =======================
# CALLBACKS
# =======================
def register_callbacks(app):

    @app.callback(
        [Output("report-grafico", "children"),
         Output("report-tabla", "children"),
         Output("report-historial", "children")], # Mantenemos el output para no romper tu layout
        Input("report-btn-generar", "n_clicks"),
        [State("report-tipo-reporte", "value"),
         State("report-fecha-inicio", "date"),
         State("report-fecha-final", "date")],
        prevent_initial_call=True
    )
    def generar_reporte(n_clicks, tipo_reporte, start_date, end_date):
        
        # 1. Conectar y Traer datos de tu Vista
        conn = get_connection()
        # Tu vista ya filtra por el caso activo automáticamente
        query = "SELECT * FROM inventar_SpcHidr.vw_Reporte_preliminar ORDER BY dia ASC"
        
        try:
            df = pd.read_sql(query, conn)
            conn.close()
        except Exception as e:
            return dbc.Alert(f"Error SQL: {e}", color="danger"), "", ""

        if df.empty:
            return dbc.Alert("No hay datos disponibles en la vista.", color="warning"), "", ""

        # 2. Procesar Fechas y Nulos
        df["dia"] = pd.to_datetime(df["dia"])
        df = df.fillna(0)

        grafico = html.Div()
        tabla = html.Div()

        # -----------------------------------------------------
        # CASO A: PRODUCCIÓN DIARIA
        # -----------------------------------------------------
        if tipo_reporte == "prod":
            # Gráfico Doble Eje
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Bar(x=df["dia"], y=df["apilado_tms_real"], name="TMS Diario", marker_color="#0984e3", opacity=0.7),
                secondary_y=False
            )
            fig.add_trace(
                go.Scatter(x=df["dia"], y=df["ley_cut_real"], name="Ley Cu (%)", mode='lines+markers', line=dict(color="#d63031", width=3)),
                secondary_y=True
            )

            fig.update_layout(title="Producción Diaria", template="plotly_white", legend=dict(orientation="h", y=1.1))
            fig.update_yaxes(title_text="Tonelaje (TMS)", secondary_y=False)
            fig.update_yaxes(title_text="Ley Cu (%)", secondary_y=True)
            
            grafico = dcc.Graph(figure=fig)
            
            # Tabla Diaria
            cols_view = ["dia", "apilado_tms_real", "ley_cut_real", "cu_fino_apilado_real"]
            df_tabla = df[cols_view].copy()
            df_tabla["dia"] = df_tabla["dia"].dt.strftime('%Y-%m-%d')
            tabla = dbc.Table.from_dataframe(df_tabla.round(2), striped=True, bordered=True, hover=True)

        # -----------------------------------------------------
        # CASO B: REPORTE ACUMULADO (NUEVO)
        # -----------------------------------------------------
        elif tipo_reporte == "acumulado":
            # Cálculos Matemáticos
            df["TMS_Acum"] = df["apilado_tms_real"].cumsum()
            df["Finos_Acum"] = df["cu_fino_apilado_real"].cumsum()
            
            # Ley Ponderada = (Finos Acum / Ton Acum) * 100
            df["Ley_Acum"] = np.where(df["TMS_Acum"] > 0, (df["Finos_Acum"] / df["TMS_Acum"]) * 100, 0)

            # Gráfico Acumulado
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Área rellena (TMS)
            fig.add_trace(go.Scatter(x=df["dia"], y=df["TMS_Acum"], name="TMS Acumulado", fill='tozeroy', mode='lines', line=dict(color="#00b894")), secondary_y=False)
            
            # Línea (Ley)
            fig.add_trace(go.Scatter(x=df["dia"], y=df["Ley_Acum"], name="Ley Cu Acumulada (%)", mode='lines+markers', line=dict(color="#d63031", width=3)), secondary_y=True)

            fig.update_layout(title="Curva Acumulada (Campaña Actual)", template="plotly_white", legend=dict(orientation="h", y=1.1))
            fig.update_yaxes(title_text="TMS Acumulado", secondary_y=False)
            fig.update_yaxes(title_text="Ley Media (%)", secondary_y=True)

            grafico = dcc.Graph(figure=fig)

            # Tabla Acumulada
            df_show = df[["dia", "apilado_tms_real", "TMS_Acum", "ley_cut_real", "Ley_Acum"]].copy()
            df_show["dia"] = df_show["dia"].dt.strftime('%Y-%m-%d')
            df_show.columns = ["Fecha", "TMS Día", "TMS Acum", "Ley Día %", "Ley Acum %"]
            
            tabla = dbc.Table.from_dataframe(df_show.round(2), striped=True, bordered=True, hover=True)

        # Retornamos grafico, tabla y un div vacío para el historial (ya que no estamos consultando historial real aún)
        return grafico, tabla, html.Div("Datos cargados desde Base de Datos")