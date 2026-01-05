
import pandas as pd
from dash import Input, Output, State, callback, no_update
from report_export.report_export import fetch_report_data
from report_export.export_to_excel import export_dataframe_with_template

# Ajusta la ruta a tu template:
TEMPLATE_XLSX_PATH = "./reporte/Template_DatosConcialiados.xlsx"

@callback(
    Output("rep_descarga_xlsx", "data"),
    Output("rep_status", "children"),
    Input("report-btn-exportar", "n_clicks"),
    State("report-fecha-final", "date"),
    prevent_initial_call=True
)
def generar_y_descargar(n_clicks, fecha_hasta):
    if not fecha_hasta:
        return no_update, "⚠️ Debe seleccionar una fecha."

    end_date = pd.to_datetime(fecha_hasta).date()
    try:
        df = fetch_report_data(end_date=end_date)
        xbytes = export_dataframe_with_template(df, TEMPLATE_XLSX_PATH)
        filename = f"Reporte_DatosConciliados_{end_date.strftime('%Y%m%d')}.xlsx"
        status = f"✔️ Archivo generado: {filename} — Registros: {len(df)}"
        return dict(content=xbytes, filename=filename, type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), status
    except Exception as e:
        return no_update, f"❌ Error al generar: {e}"
