# Auto-generated on 2025-10-27 18:21:09. Edit as needed.


import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, no_update, dcc, html
import dash_bootstrap_components as dbc

from report_export.report_export import fetch_report_data
from report_export.export_to_excel import export_dataframe_with_template
TEMPLATE_XLSX_PATH = "./reporte/Template_DatosConcialiados.xlsx"

def _style_table(df: pd.DataFrame) -> dbc.Table:
    return dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True, className="mt-3")

@callback(
    Output("report-grafico", "children"),
    Output("report-tabla", "children"),
    Output("report-historial", "children"),
    Input("report-btn-generar", "n_clicks"),
    Input("report-tipo-reporte", "value"),
    State("report-fecha-inicio", "date"),
    State("report-fecha-final", "date"),
    prevent_initial_call=True
)
def generar_reporte(n_clicks, tipo, f_ini, f_fin):
    if not f_ini or not f_fin:
        return no_update, no_update, dbc.Alert("⚠️ Debe seleccionar rango de fechas.", color="warning")

    ini = pd.to_datetime(f_ini).date()
    fin = pd.to_datetime(f_fin).date()
    fecha_hasta=f_fin
    end_date = pd.to_datetime(fecha_hasta).date()

    df_mensual = fetch_report_data(end_date=fin)
    #df = df_mensual[(pd.to_datetime(df_mensual["Fecha"]).dt.date >= ini) &
     #               (pd.to_datetime(df_mensual["Fecha"]).dt.date <= fin)].copy()
    
    df =fetch_report_data(end_date=end_date)

    if df.empty:
        return dbc.Alert("Sin datos en el rango seleccionado.", color="info"), no_update, no_update

    if tipo == "prod":
        ycol = None
        for c in ["Produccion_Catodos_Real", "Producción_Cátodos_Real", "prod_catodos_real"]:
            if c in df.columns:
                ycol = c
                break
        if ycol is None:
            return dbc.Alert("No se encuentra la columna 'Produccion_Catodos_Real' en la tabla.", color="danger"), no_update, no_update

        plot_df = df.sort_values("Fecha")
        fig = px.line(plot_df, x="Fecha", y=ycol, markers=True, title="Producción Diaria (Cátodos)")
        grafico = dcc.Graph(figure=fig)

        table_df = df.sort_values("Fecha", ascending=False).head(10)
        tabla = _style_table(table_df)

    elif tipo == "balance":
        ycol = "Produccion_Catodos_Real" if "Produccion_Catodos_Real" in df.columns else None
        if ycol:
            df["Semana"] = pd.to_datetime(df["Fecha"]).dt.isocalendar().week
            agg = df.groupby("Semana", as_index=False)[ycol].mean()
            fig = px.bar(agg, x="Semana", y=ycol, title="Balance Semanal (Promedio Producción)")
            grafico = dcc.Graph(figure=fig)
        else:
            grafico = dbc.Alert("Balance: no se encontró columna Produccion_Catodos_Real.", color="warning")
        table_df = df.sort_values("Fecha", ascending=False).head(10)
        tabla = _style_table(table_df)

    else:
        ycol = "Produccion_Catodos_Real" if "Produccion_Catodos_Real" in df.columns else None
        if ycol:
            df["Mes"] = pd.to_datetime(df["Fecha"]).dt.to_period("M").astype(str)
            agg = df.groupby("Mes", as_index=False)[ycol].sum()
            fig = px.bar(agg, x="Mes", y=ycol, title="Conciliación Mensual (Suma Producción)")
            grafico = dcc.Graph(figure=fig)
        else:
            grafico = dbc.Alert("Conciliación: no se encontró columna Produccion_Catodos_Real.", color="warning")
        table_df = df.sort_values("Fecha", ascending=False).head(10)
        tabla = _style_table(table_df)

    historial = dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Fecha"), html.Th("Tipo"), html.Th("Usuario")]),
                    style={"backgroundColor": "#FEEBC8"}),
            html.Tbody([
                html.Tr([html.Td(pd.Timestamp.now().strftime("%d-%m-%Y")), html.Td({"prod":"Producción Diaria","balance":"Balance Semanal","conciliacion":"Conciliación Mensual"}[tipo]), html.Td("usuario_actual")]),
            ])
        ], bordered=True, hover=True
    )

    return grafico, tabla, historial

@callback(
    Output("report-download-xlsx", "data"),
    Output("report-status", "children"),
    Input("report-btn-exportar", "n_clicks"),
    State("report-tipo-reporte", "value"),
    State("report-fecha-inicio", "date"),
    State("report-fecha-final", "date"),
    prevent_initial_call=True
)
def exportar_excel(n_clicks, tipo, f_ini, f_fin):
    if not f_ini or not f_fin:
        return no_update, "⚠️ Debe seleccionar rango de fechas."
    fin = pd.to_datetime(f_fin).date()

    try:
        df = fetch_report_data(end_date=fin)
        ini_d = pd.to_datetime(f_ini).date()
        fin_d = pd.to_datetime(f_fin).date()
        df = df[(pd.to_datetime(df["Fecha"]).dt.date >= ini_d) &
                (pd.to_datetime(df["Fecha"]).dt.date <= fin_d)].copy()

        if df.empty:
            return no_update, "ℹ️ Sin datos para exportar en el rango seleccionado."

        xbytes = export_dataframe_with_template(df, TEMPLATE_XLSX_PATH)
        filename = f"Reporte_{tipo}_{pd.to_datetime(f_ini).strftime('%Y%m%d')}_{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
        status = f"✔️ Exportado: {filename} — Registros: {len(df)}"
        return dict(content=xbytes, filename=filename, type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), status
    except Exception as e:
        return no_update, f"❌ Error al exportar: {e}"
