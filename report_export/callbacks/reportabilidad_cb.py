# Auto-generated on 2025-10-27 18:21:09. Edit as needed.

import base64
import os
import io
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, no_update, dcc, html, dash_table
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc

from report_export.report_export import (
    fetch_report_data,
    fetch_datos_conciliados_report,
    fetch_representatividad_torres_report
)
from report_export.export_to_excel import export_dataframe_with_template, export_datos_conciliados_to_template

TEMPLATE_XLSX_PATH = "./reporte/Template_DatosConcialiados.xlsx"
# Plantilla "Datos conciliados" para Producción Diaria (datos desde D16, columnas D–AS)
_REPORT_EXPORT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _find_plantilla_propuesta():
    """Resuelve la ruta de la plantilla VF listando el directorio (evita problemas con 'á' en Windows)."""
    try:
        for name in os.listdir(_REPORT_EXPORT_DIR):
            if not name.startswith("~$") and name.endswith(".xlsx"):
                if "Propuesta_Identidad" in name and "DatosConcialiados" in name and "VF" in name:
                    return os.path.join(_REPORT_EXPORT_DIR, name)
    except OSError:
        pass
    return os.path.join(_REPORT_EXPORT_DIR, "Propuesta_Identidad_Gráfica_DatosConcialiados VF.xlsx")

def _style_table(df: pd.DataFrame) -> dbc.Table:
    return dbc.Table.from_dataframe(
        df,
        striped=True,
        bordered=True,
        hover=True,
        className="mt-3"
    )
def _tabla_representatividad_torres(df: pd.DataFrame):
    df = df.copy()

    if "Dia" in df.columns:
        df["Dia"] = pd.to_datetime(df["Dia"]).dt.strftime("%d-%m-%Y")

    columnas_pct = [
        "TM1_TurnoA_Quimico",
        "TM1_TurnoA_Fisico",
        "TM1_TurnoB_Quimico",
        "TM1_TurnoB_Fisico",
        "TM2_TurnoA_Quimico",
        "TM2_TurnoA_Fisico",
        "TM2_TurnoB_Quimico",
        "TM2_TurnoB_Fisico",
    ]

    df_num = df.copy()

    for col in columnas_pct:
        if col in df_num.columns:
            df_num[col] = pd.to_numeric(df_num[col], errors="coerce")

    # Crear columnas auxiliares ocultas para definir el color de cada celda
    hidden_cols = []

    for col in columnas_pct:
        if col not in df.columns:
            continue

        estado_col = f"estado_{col}"
        hidden_cols.append(estado_col)

        valores_formateados = []
        estados = []

        for valor in df_num[col]:
            if pd.isna(valor):
                valores_formateados.append("Tambor detenido")
                estados.append("detenido")
            else:
                valores_formateados.append(f"{valor * 100:.1f}%")

                if valor < 0.75:
                    estados.append("bajo")
                else:
                    estados.append("normal")

        df[col] = valores_formateados
        df[estado_col] = estados

    columns = [
        {"name": ["", "Día"], "id": "Dia"},

        {"name": ["Representatividad TM1", "Turno A - Químico"], "id": "TM1_TurnoA_Quimico"},
        {"name": ["Representatividad TM1", "Turno A - Físico"], "id": "TM1_TurnoA_Fisico"},
        {"name": ["Representatividad TM1", "Turno B - Químico"], "id": "TM1_TurnoB_Quimico"},
        {"name": ["Representatividad TM1", "Turno B - Físico"], "id": "TM1_TurnoB_Fisico"},

        {"name": ["Representatividad TM2", "Turno A - Químico"], "id": "TM2_TurnoA_Quimico"},
        {"name": ["Representatividad TM2", "Turno A - Físico"], "id": "TM2_TurnoA_Fisico"},
        {"name": ["Representatividad TM2", "Turno B - Químico"], "id": "TM2_TurnoB_Quimico"},
        {"name": ["Representatividad TM2", "Turno B - Físico"], "id": "TM2_TurnoB_Fisico"},
    ]

    # Agregar columnas auxiliares ocultas al DataTable
    for col in hidden_cols:
        columns.append({"name": col, "id": col})

    style_data_conditional = [
        {
            "if": {"row_index": "odd"},
            "backgroundColor": "#eef3f6",
        },
        {
            "if": {"column_id": "Dia"},
            "backgroundColor": "#fff2cc",
            "fontWeight": "bold",
        },
    ]

    # Estilos por columna usando la columna auxiliar de estado
    for col in columnas_pct:
        estado_col = f"estado_{col}"

        if estado_col not in df.columns:
            continue

        # Tambor detenido: azul/gris, nunca rojo
        style_data_conditional.append({
            "if": {
                "filter_query": f'{{{estado_col}}} = "detenido"',
                "column_id": col
            },
            "color": "#1f4e79",
            "fontWeight": "500"
        })

        # Representatividad menor a 75%, incluyendo 0.0%: rojo
        style_data_conditional.append({
            "if": {
                "filter_query": f'{{{estado_col}}} = "bajo"',
                "column_id": col
            },
            "color": "red",
            "fontWeight": "bold"
        })

    return dash_table.DataTable(
        id="tabla-representatividad-torres",
        columns=columns,
        data=df.to_dict("records"),
        merge_duplicate_headers=True,
        hidden_columns=hidden_cols,

        style_table={
            "overflowX": "auto",
            "width": "100%",
        },

        style_cell={
            "textAlign": "center",
            "fontFamily": "Arial",
            "fontSize": "13px",
            "padding": "7px",
            "border": "1px solid #b8b8b8",
            "minWidth": "115px",
            "width": "125px",
            "maxWidth": "160px",
            "whiteSpace": "normal",
        },

        style_header={
            "backgroundColor": "#d9e3ea",
            "fontWeight": "bold",
            "color": "#1f4e79",
            "border": "1px solid #7f9db9",
            "textAlign": "center",
        },

        style_data_conditional=style_data_conditional,

        page_size=40,
        sort_action="native",
        filter_action="native",
    )
def _export_representatividad_torres_to_excel(df: pd.DataFrame) -> bytes:
    """
    Exporta el reporte de Representatividad Torres a Excel
    con formato similar a la tabla visual de Dash.
    """

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    df = df.copy()

    columnas_pct = [
        "TM1_TurnoA_Quimico",
        "TM1_TurnoA_Fisico",
        "TM1_TurnoB_Quimico",
        "TM1_TurnoB_Fisico",
        "TM2_TurnoA_Quimico",
        "TM2_TurnoA_Fisico",
        "TM2_TurnoB_Quimico",
        "TM2_TurnoB_Fisico",
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Representatividad Torres"

    # Estilos
    fill_header = PatternFill("solid", fgColor="D9E3EA")
    fill_dia = PatternFill("solid", fgColor="FFF2CC")
    fill_alt = PatternFill("solid", fgColor="EEF3F6")

    font_header = Font(bold=True, color="1F4E79")
    font_normal = Font(color="404040")
    font_red = Font(color="FF0000", bold=True)
    font_det = Font(color="1F4E79")

    thin = Side(style="thin", color="B8B8B8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Título
    ws.merge_cells("A1:I1")
    ws["A1"] = "Representatividad diaria de torres de muestreo"
    ws["A1"].font = Font(bold=True, size=14, color="1F4E79")
    ws["A1"].alignment = center

    ws.merge_cells("A2:I2")
    ws["A2"] = "Valores expresados en porcentaje. Los valores menores a 75% se destacan en rojo."
    ws["A2"].font = Font(size=10, color="808080")
    ws["A2"].alignment = center

    # Encabezados agrupados
    ws.merge_cells("A4:A5")
    ws["A4"] = "Día"

    ws.merge_cells("B4:E4")
    ws["B4"] = "Representatividad TM1"

    ws.merge_cells("F4:I4")
    ws["F4"] = "Representatividad TM2"

    headers = [
        "Turno A - Químico",
        "Turno A - Físico",
        "Turno B - Químico",
        "Turno B - Físico",
        "Turno A - Químico",
        "Turno A - Físico",
        "Turno B - Químico",
        "Turno B - Físico",
    ]

    for idx, header in enumerate(headers, start=2):
        ws.cell(row=5, column=idx).value = header

    # Estilo encabezados
    for row in range(4, 6):
        for col in range(1, 10):
            cell = ws.cell(row=row, column=col)
            cell.fill = fill_header
            cell.font = font_header
            cell.alignment = center
            cell.border = border

    ws["A4"].fill = fill_dia
    ws["A4"].font = font_header

    # Datos
    start_row = 6

    for r_idx, (_, row) in enumerate(df.iterrows(), start=start_row):
        if "Dia" in df.columns:
            dia = pd.to_datetime(row["Dia"]).strftime("%d-%m-%Y")
        else:
            dia = ""

        ws.cell(row=r_idx, column=1).value = dia
        ws.cell(row=r_idx, column=1).fill = fill_dia
        ws.cell(row=r_idx, column=1).font = Font(bold=True, color="404040")
        ws.cell(row=r_idx, column=1).alignment = center
        ws.cell(row=r_idx, column=1).border = border

        for c_idx, col in enumerate(columnas_pct, start=2):
            cell = ws.cell(row=r_idx, column=c_idx)
            valor = pd.to_numeric(row.get(col), errors="coerce")

            if pd.isna(valor):
                cell.value = "Tambor detenido"
                cell.font = font_det
            else:
                cell.value = f"{valor * 100:.1f}%"

                if valor < 0.75:
                    cell.font = font_red
                else:
                    cell.font = font_normal

            cell.alignment = center
            cell.border = border

            if (r_idx - start_row) % 2 == 1:
                cell.fill = fill_alt

    # Anchos
    ws.column_dimensions["A"].width = 14
    for col_letter in ["B", "C", "D", "E", "F", "G", "H", "I"]:
        ws.column_dimensions[col_letter].width = 20

    ws.freeze_panes = "B6"

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
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
        return (
            no_update,
            no_update,
            dbc.Alert("⚠️ Debe seleccionar rango de fechas.", color="warning")
        )

    ini = pd.to_datetime(f_ini).date()
    fin = pd.to_datetime(f_fin).date()

    # ------------------------------------------------------------
    # REPORTE REPRESENTATIVIDAD TORRES
    # ------------------------------------------------------------
    if tipo == "representatividad_torres":
        try:
            df_rep = fetch_representatividad_torres_report(
                start_date=ini,
                end_date=fin
            )
        except Exception as e:
            return (
                dbc.Alert(
                    f"Error al consultar representatividad de torres: {e}",
                    color="danger"
                ),
                no_update,
                no_update
            )

        if df_rep.empty:
            return (
                dbc.Alert(
                    "Sin datos de representatividad para el rango seleccionado.",
                    color="info"
                ),
                no_update,
                no_update
            )

        titulo = html.Div([
            html.H5("Representatividad diaria de torres de muestreo", className="mb-2"),
            html.P(
                "Valores expresados en porcentaje. Los valores menores a 75% se destacan en rojo.",
                className="text-muted mb-3"
            )
        ])

        tabla = html.Div([
            titulo,
            _tabla_representatividad_torres(df_rep)
        ])

        historial = dbc.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Fecha"),
                        html.Th("Tipo"),
                        html.Th("Usuario")
                    ]),
                    style={"backgroundColor": "#FEEBC8"}
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(pd.Timestamp.now().strftime("%d-%m-%Y")),
                        html.Td("Representatividad Torres"),
                        html.Td("usuario_actual")
                    ]),
                ])
            ],
            bordered=True,
            hover=True
        )

        return html.Div(), tabla, historial

    # ------------------------------------------------------------
    # REPORTES ANTIGUOS
    # ------------------------------------------------------------
    fecha_hasta = f_fin
    end_date = pd.to_datetime(fecha_hasta).date()

    df = fetch_report_data(end_date=end_date)

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
    ini_d = pd.to_datetime(f_ini).date()
    fin_d = pd.to_datetime(f_fin).date()

    try:
        if tipo == "representatividad_torres":
            df = fetch_representatividad_torres_report(
                start_date=ini_d,
                end_date=fin_d
            )

            if df.empty:
                return no_update, "ℹ️ Sin datos para exportar en el rango seleccionado."

            xbytes = _export_representatividad_torres_to_excel(df)

            filename = (
                f"Reporte_Representatividad_Torres_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )

            status = f"✔️ Exportado: {filename} — Registros: {len(df)}"
            encoded = base64.b64encode(xbytes).decode("utf-8")

            return dict(content=encoded, filename=filename, base64=True), status        
        if tipo == "prod":
            # Producción Diaria: consulta exacta por rango de fechas y plantilla Datos conciliados (D16–AS)
            template_path = _find_plantilla_propuesta()
            if not os.path.isfile(template_path):
                return no_update, f"❌ No se encuentra la plantilla en {_REPORT_EXPORT_DIR}"
            df = fetch_datos_conciliados_report(start_date=ini_d, end_date=fin_d)
            if df.empty:
                return no_update, "ℹ️ Sin datos para exportar en el rango seleccionado."
            xbytes = export_datos_conciliados_to_template(df, template_path)
        else:
            df = fetch_report_data(end_date=fin_d)
            df = df[(pd.to_datetime(df["Fecha"]).dt.date >= ini_d) &
                    (pd.to_datetime(df["Fecha"]).dt.date <= fin_d)].copy()
            if df.empty:
                return no_update, "ℹ️ Sin datos para exportar en el rango seleccionado."
            xbytes = export_dataframe_with_template(df, TEMPLATE_XLSX_PATH)

        filename = f"Reporte_{tipo}_{pd.to_datetime(f_ini).strftime('%Y%m%d')}_{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
        status = f"✔️ Exportado: {filename} — Registros: {len(df)}"
        # dcc.Download requiere contenido serializable: usar Base64 para binarios
        encoded = base64.b64encode(xbytes).decode("utf-8")
        return dict(content=encoded, filename=filename, base64=True), status
    except Exception as e:
        return no_update, f"❌ Error al exportar: {e}"
