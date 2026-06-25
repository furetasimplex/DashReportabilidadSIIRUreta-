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
    fetch_representatividad_torres_report,
    fetch_reporte_turno_report,
    fetch_reporte_turno_cache,
    fetch_generador_reporte_diario,
    export_reporte_turno_estilo_leyes_finos,
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

def _style_table(df: pd.DataFrame) -> dash_table.DataTable:
    df = df.copy()
    columnas_numericas = [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
    ]

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col]).dt.strftime("%d-%m-%Y")

    df = df.astype(object).where(pd.notna(df), None)

    return dash_table.DataTable(
        id="tabla-reporte-general",
        columns=[
            {
                "name": col,
                "id": col,
                "type": "numeric" if col in columnas_numericas else "text",
            }
            for col in df.columns
        ],
        data=df.to_dict("records"),
        page_size=20,
        sort_action="native",
        filter_action="none",
        fixed_rows={"headers": True},
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "650px",
            "width": "100%",
            "maxWidth": "100%",
            "border": "1px solid #d0d0d0",
        },
        style_cell={
            "textAlign": "center",
            "fontFamily": "Arial",
            "fontSize": "11px",
            "padding": "5px",
            "minWidth": "90px",
            "width": "105px",
            "maxWidth": "140px",
            "whiteSpace": "normal",
            "height": "auto",
            "border": "1px solid #d9d9d9",
        },
        style_header={
            "backgroundColor": "#9DC3E6",
            "fontWeight": "bold",
            "color": "#1f4e79",
            "textAlign": "center",
            "border": "1px solid #7f9db9",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f7f3ef"},
            {"if": {"column_id": "Fecha"}, "backgroundColor": "#d9eaf7", "fontWeight": "bold"},
        ],
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
def _export_dataframe_simple_to_excel(df: pd.DataFrame, sheet_name: str = "Reporte") -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

    output.seek(0)
    return output.getvalue()

def _preparar_reporte_turno_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ordena las columnas del reporte por turno en el mismo orden visual del formato BHP
    y reemplaza valores vacíos:
      - columnas numéricas: NULL/NaN -> 0
      - columnas de texto: NULL/NaN -> "-"
    Además redondea valores numéricos para visualización y exportación.
    """
    df = df.copy()

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.strftime("%d-%m-%Y")
    if "Material" in df.columns:
        df["Material"] = (
            df["Material"]
            .astype(str)
            .str.upper()
            .str.strip()
            .replace({
                "SULFUROS": "Sulfuro",
                "SULFURO": "Sulfuro",
                "OXIDOS": "Óxido",
                "OXIDO": "Óxido",
                "ÓXIDOS": "Óxido",
                "ÓXIDO": "Óxido",
            })
        )
    columnas_ordenadas = [
        "Fecha",
        "Campania",
        "Material",
        "Modulo",
        "Avance",
        "Turno",

        "Apilado_TMS_Real",
        "Apilado_TMS_Plan_Mensual",

        "STOCK",
        "MINA",
        "SRR",

        "CuT_Real",
        "CuT_Plan_Semanal",
        "CuT_Plan_Mensual",

        "CuS_Real",
        "CuS_Plan_Semanal",
        "CuS_Plan_Mensual",

        "Solubilidad_Real",
        "Solubilidad_Plan_Semanal",
        "Solubilidad_Plan_Mensual",

        "CO3_Real",
        "CO3_Plan_Semanal",
        "CO3_Plan_Mensual",

        "CuFe_Real",
        "CuFe_Plan_Semanal",
        "CuFe_Plan_Mensual",

        "FeT_Real",
        "FeS_Real",
        "ConsH_Real",

        "Malla_Menos_1_2_Real",
        "Malla_Menos_1_2_Plan_Semanal",

        "Malla_Menos_100_Real",
        "Malla_Menos_100_Plan_Semanal",
        "Malla_Menos_100_Plan_Mensual",

        "CaolBeta_Real",
        "CaolBeta_Plan_Semanal",
        "CaolBeta_Plan_Mensual",

        "Dosis_Acido_Ideal_TM",
        "Dosis_Acido_Programa_Semanal",

        "Fuente_Info_Quimica",
        "Fuente_Info_Fisica",
    ]

    columnas_ordenadas = [c for c in columnas_ordenadas if c in df.columns]
    df = df[columnas_ordenadas]

    columnas_texto = [
        "Fecha",
        "Turno",
        "Campania",
        "Material",
        "Modulo",
        "Fuente_Info_Quimica",
        "Fuente_Info_Fisica",
        "Malla_Menos_1_2_Plan_Semanal",  # puede venir como "<75%"
    ]

    columnas_texto = [c for c in columnas_texto if c in df.columns]
    columnas_numericas = [c for c in df.columns if c not in columnas_texto]

    for col in columnas_numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Avance viene desde SQL/cache en escala 0-1.
    # Para visualización se muestra en escala 0-100.
    if "Avance" in df.columns:
        df["Avance"] = pd.to_numeric(df["Avance"], errors="coerce") * 100

    # STOCK, MINA y SRR ya vienen desde SQL/cache en escala 0-100.
    # No multiplicar ni dividir.
    for col in ["STOCK", "MINA", "SRR"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Solubilidad es razón CuS/CuT, no porcentaje.
    # No multiplicar por 100.
    for col in ["Solubilidad_Real", "Solubilidad_Plan_Semanal", "Solubilidad_Plan_Mensual"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Limpiar objetivo granulométrico.
    if "Malla_Menos_1_2_Plan_Semanal" in df.columns:
        df["Malla_Menos_1_2_Plan_Semanal"] = (
            df["Malla_Menos_1_2_Plan_Semanal"]
            .astype(str)
            .str.replace("%", "", regex=False)
            .replace({"nan": "", "None": "", "NULL": ""})
        )

    cols_0_dec = [
        "Apilado_TMS_Real",
        "Apilado_TMS_Plan_Mensual",
    ]

    cols_2_dec = [
        "Avance",
        "STOCK",
        "MINA",
        "SRR",

        "CuT_Real",
        "CuT_Plan_Semanal",
        "CuT_Plan_Mensual",

        "CuS_Real",
        "CuS_Plan_Semanal",
        "CuS_Plan_Mensual",

        "Solubilidad_Real",
        "Solubilidad_Plan_Semanal",
        "Solubilidad_Plan_Mensual",

        "CO3_Real",
        "CO3_Plan_Semanal",
        "CO3_Plan_Mensual",

        "CuFe_Real",
        "CuFe_Plan_Semanal",
        "CuFe_Plan_Mensual",

        "FeT_Real",
        "FeS_Real",
        "ConsH_Real",

        "Malla_Menos_1_2_Real",
        "Malla_Menos_100_Real",
        "Malla_Menos_100_Plan_Semanal",
        "Malla_Menos_100_Plan_Mensual",

        "CaolBeta_Real",
        "CaolBeta_Plan_Semanal",
        "CaolBeta_Plan_Mensual",

        "Dosis_Acido_Ideal_TM",
        "Dosis_Acido_Programa_Semanal",
    ]

    for col in cols_0_dec:
        if col in df.columns:
            df[col] = df[col].round(0)

    for col in cols_2_dec:
        if col in df.columns:
            df[col] = df[col].round(2)

    for col in columnas_texto:
        df[col] = df[col].fillna("-")

    return df


def _tabla_reporte_turno(df: pd.DataFrame):
    df = _preparar_reporte_turno_df(df)

    # Encabezados agrupados tipo BHP
    column_headers = {
    "Fecha": ["", "Fecha"],
    "Campania": ["", "Campaña"],
    "Material": ["", "Material"],
    "Modulo": ["", "Módulo"],
    "Avance": ["", "Avance (%)"],
    "Turno": ["", "Turno"],

    "Apilado_TMS_Real": ["Apilado TMS", "Real"],
    "Apilado_TMS_Plan_Mensual": ["Apilado TMS", "Plan"],

    "STOCK": ["Distribución origen", "Stock (%)"],
    "MINA": ["Distribución origen", "Mina (%)"],
    "SRR": ["Distribución origen", "SRR (%)"],

    "CuT_Real": ["Análisis Químicos", "CuT Real (%)"],
    "CuT_Plan_Semanal": ["Análisis Químicos", "CuT Programa (%)"],
    "CuT_Plan_Mensual": ["Análisis Químicos", "CuT Plan (%)"],

    "CuS_Real": ["Análisis Químicos", "CuS Real (%)"],
    "CuS_Plan_Semanal": ["Análisis Químicos", "CuS Programa (%)"],
    "CuS_Plan_Mensual": ["Análisis Químicos", "CuS Plan (%)"],

    "Solubilidad_Real": ["Análisis Químicos", "Solubilidad Real"],
    "Solubilidad_Plan_Semanal": ["Análisis Químicos", "Solubilidad Programa"],
    "Solubilidad_Plan_Mensual": ["Análisis Químicos", "Solubilidad Plan"],

    "CO3_Real": ["Análisis Químicos", "CO3 Real (%)"],
    "CO3_Plan_Semanal": ["Análisis Químicos", "CO3 Programa (%)"],
    "CO3_Plan_Mensual": ["Análisis Químicos", "CO3 Plan (%)"],

    "CuFe_Real": ["Análisis Químicos", "CuFe Real (%)"],
    "CuFe_Plan_Semanal": ["Análisis Químicos", "CuFe Programa (%)"],
    "CuFe_Plan_Mensual": ["Análisis Químicos", "CuFe Plan (%)"],

    "FeT_Real": ["Análisis Químicos", "FeT Real (%)"],
    "FeS_Real": ["Análisis Químicos", "FeS Real (%)"],

    "ConsH_Real": ["Análisis Químicos", "Consumo de Ácido (kg/ton)"],

    "Malla_Menos_1_2_Real": ["Granulometrías", "-1/2 Real (%)"],
    "Malla_Menos_1_2_Plan_Semanal": ["Granulometrías", "-1/2 Plan (%)"],

    "Malla_Menos_100_Real": ["Granulometrías", "-100#Ty Real (%)"],
    "Malla_Menos_100_Plan_Semanal": ["Granulometrías", "-100#Ty Programa (%)"],
    "Malla_Menos_100_Plan_Mensual": ["Granulometrías", "-100#Ty Plan (%)"],

    "CaolBeta_Real": ["NIR", "CaolBeta Real (%)"],
    "CaolBeta_Plan_Semanal": ["NIR", "CaolBeta Programa (%)"],
    "CaolBeta_Plan_Mensual": ["NIR", "CaolBeta Plan (%)"],

    "Dosis_Acido_Ideal_TM": ["Dosis de ácido (kg/ton)", "Ideal TM"],
    "Dosis_Acido_Programa_Semanal": ["Dosis de ácido (kg/ton)", "Programa"],

    "Fuente_Info_Quimica": ["Fuentes de información", "Muestra química"],
    "Fuente_Info_Fisica": ["Fuentes de información", "Muestra física"],
 }

    columnas_texto = [
    "Fecha",
    "Turno",
    "Campania",
    "Material",
    "Modulo",
    "Fuente_Info_Quimica",
    "Fuente_Info_Fisica",
    "Malla_Menos_1_2_Plan_Semanal",
 ]
    columnas_numericas = [c for c in df.columns if c not in columnas_texto]

    return dash_table.DataTable(
        id="tabla-reporte-turno",
        columns=[
            {
                "name": column_headers.get(c, ["", c]),
                "id": c,
                "type": "numeric" if c in columnas_numericas else "text",
            }
            for c in df.columns
        ],
        data=df.to_dict("records"),
        merge_duplicate_headers=True,
        page_size=20,
        sort_action="native",
        filter_action="none",
        fixed_rows={"headers": True},
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "650px",
            "width": "100%",
            "maxWidth": "100%",
            "border": "1px solid #d0d0d0",
        },
        style_cell={
            "textAlign": "center",
            "fontFamily": "Arial",
            "fontSize": "11px",
            "padding": "5px",
            "minWidth": "90px",
            "width": "105px",
            "maxWidth": "140px",
            "whiteSpace": "normal",
            "height": "auto",
            "border": "1px solid #d9d9d9",
        },
        style_header={
            "backgroundColor": "#9DC3E6",
            "fontWeight": "bold",
            "color": "#1f4e79",
            "textAlign": "center",
            "border": "1px solid #7f9db9",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f7f3ef"},
            {"if": {"column_id": "Fecha"}, "backgroundColor": "#d9eaf7", "fontWeight": "bold"},
            {"if": {"column_id": "Turno"}, "backgroundColor": "#f2f2f2", "fontWeight": "bold"},
        ],
        style_cell_conditional=[
            {
                "if": {"column_id": "ConsH_Real"},
                "minWidth": "150px",
                "width": "160px",
                "maxWidth": "180px",
            },
            {
                "if": {"column_id": "Dosis_Acido_Ideal_TM"},
                "minWidth": "130px",
                "width": "140px",
                "maxWidth": "160px",
            },
            {
                "if": {"column_id": "Dosis_Acido_Programa_Semanal"},
                "minWidth": "130px",
                "width": "140px",
                "maxWidth": "160px",
            },

        ],
    )



def _export_reporte_turno_formateado(df: pd.DataFrame) -> bytes:
    """
    Exporta el reporte por turno con formato tipo BHP:
    encabezados agrupados, mismo orden de columnas de la visualización y reemplazo de vacíos por cero.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    df = _preparar_reporte_turno_df(df)

    wb = Workbook()
    ws = wb.active
    ws.title = "Analisis Turno"

    # Estilos
    azul = PatternFill("solid", fgColor="9DC3E6")
    celeste = PatternFill("solid", fgColor="D9EAF7")
    gris = PatternFill("solid", fgColor="F2F2F2")
    beige = PatternFill("solid", fgColor="F7F3EF")
    blanco = PatternFill("solid", fgColor="FFFFFF")

    font_bhp = Font(bold=True, size=28, color="E97132")
    font_titulo = Font(bold=True, size=14, color="1F4E79")
    font_header = Font(bold=True, color="1F4E79")
    font_normal = Font(color="404040")

    thin = Side(style="thin", color="B8B8B8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    max_col = len(df.columns)
    last_col = get_column_letter(max_col)

    # Encabezado superior
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    ws["A1"] = "BHP"
    ws["A1"].font = font_bhp
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=max_col)
    ws["A3"] = "Análisis de las Torres de Muestreo por Turno"
    ws["A3"].font = font_titulo
    ws["A3"].alignment = center

    ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=max_col)
    ws["A4"] = "Superintendencia de Medición y Reconciliación - Gerencia de Planificación de la Producción"
    ws["A4"].font = Font(size=10, color="404040")
    ws["A4"].alignment = center

    row_group = 7
    row_header = 8
    row_data = 9

    # Nombres visibles
    headers = {
        "Fecha": "Fecha",
        "Campania": "Campaña",
        "Material": "Material",
        "Modulo": "Módulo",
        "Avance": "Avance",
        "Turno": "Turno",

        "Apilado_TMS_Real": "Real",
        "Apilado_TMS_Plan_Mensual": "Plan",

        "STOCK": "Stock",
        "MINA": "Mina",
        "SRR": "SRR",

        "CuT_Real": "Real",
        "CuT_Plan_Mensual": "Programa",
        "CuT_Plan_Semanal": "Plan",

        "CuS_Real": "Real",
        "CuS_Plan_Mensual": "Programa",
        "CuS_Plan_Semanal": "Plan",

        "Solubilidad_Real": "Real",
        "Solubilidad_Plan_Mensual": "Programa",
        "Solubilidad_Plan_Semanal": "Plan",

        "CO3_Real": "Real",
        "CO3_Plan_Mensual": "Programa",
        "CO3_Plan_Semanal": "Plan",

        "CuFe_Real": "Real",
        "CuFe_Plan_Mensual": "Programa",
        "CuFe_Plan_Semanal": "Plan",

        "FeT_Real": "Real",
        "FeS_Real": "Real",
        "ConsH_Real": "Consumo ácido kg/t",

        "Malla_Menos_1_2_Real": "Real",
        "Malla_Menos_1_2_Plan_Semanal": "Plan",

        "Malla_Menos_100_Real": "Real",
        "Malla_Menos_100_Plan_Mensual": "Programa",
        "Malla_Menos_100_Plan_Semanal": "Plan",

        "CaolBeta_Real": "Real",
        "CaolBeta_Plan_Mensual": "Programa",
        "CaolBeta_Plan_Semanal": "Plan",

        "Dosis_Acido_Ideal_TM": "Ideal TM",
        "Dosis_Acido_Programa_Semanal": "Programa semanal",

        "Fuente_Info_Quimica": "Muestra química",
        "Fuente_Info_Fisica": "Muestra física",
    }

    for idx, col in enumerate(df.columns, start=1):
        cell = ws.cell(row=row_header, column=idx)
        cell.value = headers.get(col, col)
        cell.fill = celeste
        cell.font = font_header
        cell.alignment = center
        cell.border = border

    # Grupos por rangos según el orden de columnas
    def col_pos(col_name):
        try:
            return list(df.columns).index(col_name) + 1
        except ValueError:
            return None

    grupos = []

    # General: Fecha a Turno
    if col_pos("Fecha") and col_pos("Turno"):
        grupos.append(("", col_pos("Fecha"), col_pos("Turno")))

    if col_pos("Apilado_TMS_Real") and col_pos("Apilado_TMS_Plan_Mensual"):
        grupos.append(("Apilado TMS", col_pos("Apilado_TMS_Real"), col_pos("Apilado_TMS_Plan_Mensual")))

    if col_pos("STOCK") and col_pos("SRR"):
        grupos.append(("Distribución origen", col_pos("STOCK"), col_pos("SRR")))

    if col_pos("CuT_Real") and col_pos("ConsH_Real"):
        grupos.append(("Análisis Químicos", col_pos("CuT_Real"), col_pos("ConsH_Real")))

    if col_pos("Malla_Menos_1_2_Real") and col_pos("Malla_Menos_100_Plan_Semanal"):
        grupos.append(("Granulometrías", col_pos("Malla_Menos_1_2_Real"), col_pos("Malla_Menos_100_Plan_Semanal")))

    if col_pos("CaolBeta_Real") and col_pos("CaolBeta_Plan_Semanal"):
        grupos.append(("NIR", col_pos("CaolBeta_Real"), col_pos("CaolBeta_Plan_Semanal")))

    if col_pos("Dosis_Acido_Ideal_TM") and col_pos("Dosis_Acido_Programa_Semanal"):
        grupos.append(("Dosis de ácido", col_pos("Dosis_Acido_Ideal_TM"), col_pos("Dosis_Acido_Programa_Semanal")))

    if col_pos("Fuente_Info_Quimica") and col_pos("Fuente_Info_Fisica"):
        grupos.append(("Fuentes de información", col_pos("Fuente_Info_Quimica"), col_pos("Fuente_Info_Fisica")))

    for titulo, c_ini, c_fin in grupos:
        if c_ini is None or c_fin is None:
            continue
        ws.merge_cells(start_row=row_group, start_column=c_ini, end_row=row_group, end_column=c_fin)
        cell = ws.cell(row=row_group, column=c_ini)
        cell.value = titulo
        cell.fill = azul if titulo else blanco
        cell.font = font_header
        cell.alignment = center
        cell.border = border
        for c in range(c_ini, c_fin + 1):
            ws.cell(row=row_group, column=c).fill = azul if titulo else blanco
            ws.cell(row=row_group, column=c).border = border

    # Datos
    for r_idx, (_, row) in enumerate(df.iterrows(), start=row_data):
        for c_idx, col in enumerate(df.columns, start=1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.value = row[col]
            cell.font = font_normal
            cell.alignment = center
            cell.border = border

            if (r_idx - row_data) % 2 == 1:
                cell.fill = beige

            if col == "Fecha":
                cell.fill = celeste
            elif col in ["Campania", "Material", "Modulo", "Avance", "Turno"]:
                cell.fill = gris

            if isinstance(cell.value, float):
                cell.number_format = "0.00"

    # Anchos y filtros
    for c_idx, col in enumerate(df.columns, start=1):
        col_letter = get_column_letter(c_idx)
        ws.column_dimensions[col_letter].width = 15

    ws.freeze_panes = "G9"
    ws.auto_filter.ref = f"A8:{last_col}{ws.max_row}"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
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
    print("DEBUG GENERAR REPORTE")
    print("n_clicks:", n_clicks)
    print("tipo:", tipo)
    print("fecha inicio:", f_ini)
    print("fecha fin:", f_fin)
    if not f_ini or not f_fin:
        return (
            no_update,
            no_update,
            dbc.Alert("⚠️ Debe seleccionar rango de fechas.", color="warning")
        )

    ini = pd.to_datetime(f_ini).date()
    fin = pd.to_datetime(f_fin).date()
    # El SP usa fecha final exclusiva: Fecha >= inicio AND Fecha < fin
    fin_sql_exclusivo = (pd.to_datetime(f_fin) + pd.Timedelta(days=1)).date()

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
    # REPORTE POR TURNO
    # ------------------------------------------------------------
    if tipo == "reporte_turno":
        print("ENTRÓ A REPORTE TURNO")
        print("fecha fin SQL exclusiva:", fin_sql_exclusivo)
        try:
            df_turno = fetch_reporte_turno_cache(
                start_date=ini,
                end_date=fin_sql_exclusivo
            )
            print("Columnas reporte turno:", df_turno.columns.tolist())
            print("Filas reporte turno:", len(df_turno))
        except Exception as e:
            return (
                dbc.Alert(
                    f"Error al consultar reporte por turno: {e}",
                    color="danger"
                ),
                no_update,
                no_update
            )

        if df_turno.empty:
            return (
                dbc.Alert("Sin datos para el reporte por turno en el rango seleccionado.", color="info"),
                no_update,
                no_update
            )

        tabla = html.Div([
            html.H5("Análisis de las Torres de Muestreo por Turno", className="mb-2"),
            html.P(
                "Vista preliminar del reporte. Puede desplazarse horizontalmente para revisar todas las variables.",
                className="text-muted mb-3"
            ),
            _tabla_reporte_turno(df_turno)
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
                       html.Td("Análisis de las Torres de Muestreo por Turno"),
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
            return (
                dbc.Alert("No se encuentra la columna 'Produccion_Catodos_Real' en la tabla.", color="danger"),
                no_update,
                no_update
            )

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

    nombres_tipo = {
        "prod": "Producción Diaria",
        "balance": "Balance Semanal",
        "conciliacion": "Conciliación Mensual",
    }

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
                    html.Td(nombres_tipo.get(tipo, tipo)),
                    html.Td("usuario_actual")
                ]),
            ])
        ],
        bordered=True,
        hover=True
    )

    return None,tabla, historial #para devolver grafico cambiar "none" por "grafico".


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
    # El SP usa fecha final exclusiva: Fecha >= inicio AND Fecha < fin
    fin_sql_exclusivo = (pd.to_datetime(f_fin) + pd.Timedelta(days=1)).date()

    try:
        # ------------------------------------------------------------
        # REPORTE REPRESENTATIVIDAD TORRES
        # ------------------------------------------------------------
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

        # ------------------------------------------------------------
        # REPORTE POR TURNO + GENERADOR REPORTE
        # ------------------------------------------------------------
        if tipo == "reporte_turno":
            df_turno = fetch_reporte_turno_cache(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )

            if df_turno.empty:
                return (
                    no_update,
                    "ℹ️ Sin datos del Reporte por Turno para el rango seleccionado.",
                )

            # Segunda capa: una fila diaria consolidada.
            # Se exporta en el mismo archivo y no reemplaza la hoja por turno.
            df_generador = fetch_generador_reporte_diario(
                start_date=ini_d,
                end_date=fin_sql_exclusivo,
            )

            output = io.BytesIO()

            export_reporte_turno_estilo_leyes_finos(
                df=df_turno,
                output=output,
                df_generador=df_generador,
            )

            output.seek(0)
            xbytes = output.getvalue()

            filename = (
                f"Analisis_Torres_de_Muestreo"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )

            status = (
                f"✔️ Exportado: {filename} — "
                f"Reporte por Turno: {len(df_turno)} registros — "
                f"Generador Reporte: {len(df_generador)} registros"
            )

            encoded = base64.b64encode(xbytes).decode("utf-8")

            return (
                dict(
                    content=encoded,
                    filename=filename,
                    base64=True,
                ),
                status,
            )

        # ------------------------------------------------------------
        # PRODUCCIÓN DIARIA / DATOS CONCILIADOS
        # ------------------------------------------------------------
        if tipo == "prod":
            template_path = _find_plantilla_propuesta()

            if not os.path.isfile(template_path):
                return no_update, f"❌ No se encuentra la plantilla en {_REPORT_EXPORT_DIR}"

            df = fetch_datos_conciliados_report(
                start_date=ini_d,
                end_date=fin_d
            )

            if df.empty:
                return no_update, "ℹ️ Sin datos para exportar en el rango seleccionado."

            xbytes = export_datos_conciliados_to_template(df, template_path)

            filename = (
                f"Reporte_prod_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )

            status = f"✔️ Exportado: {filename} — Registros: {len(df)}"
            encoded = base64.b64encode(xbytes).decode("utf-8")

            return dict(content=encoded, filename=filename, base64=True), status

        # ------------------------------------------------------------
        # BALANCE / CONCILIACIÓN U OTROS REPORTES ANTIGUOS
        # ------------------------------------------------------------
        df = fetch_report_data(end_date=fin_d)

        df = df[
            (pd.to_datetime(df["Fecha"]).dt.date >= ini_d) &
            (pd.to_datetime(df["Fecha"]).dt.date <= fin_d)
        ].copy()

        if df.empty:
            return no_update, "ℹ️ Sin datos para exportar en el rango seleccionado."

        xbytes = export_dataframe_with_template(df, TEMPLATE_XLSX_PATH)

        filename = (
            f"Reporte_{tipo}_"
            f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
            f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
        )

        status = f"✔️ Exportado: {filename} — Registros: {len(df)}"
        encoded = base64.b64encode(xbytes).decode("utf-8")

        return dict(content=encoded, filename=filename, base64=True), status

    except Exception as e:
        return no_update, f"❌ Error al exportar: {e}"
