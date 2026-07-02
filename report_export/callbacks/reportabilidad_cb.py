# Auto-generated on 2025-10-27 18:21:09. Edit as needed.

import os
import io
import calendar
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback, clientside_callback, no_update, dcc, html, dash_table, ALL, MATCH, ctx
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc

from report_export.report_export import (
    fetch_report_data,
    fetch_datos_conciliados_report,
    fetch_representatividad_torres_report,
    fetch_bd_ton_report,
    fetch_gestion_representatividad_fy,
    fetch_estado_apilado_turno_representatividad,
    fetch_reporte_turno_report,
    fetch_reporte_turno_cache,
    fetch_generador_reporte_diario,
    export_reporte_turno_estilo_leyes_finos,
)
from report_export.export_to_excel import export_dataframe_with_template, export_datos_conciliados_to_template
from report_export.pdf_generator import (
    generar_pdf_reporte_turno,
    generar_pdf_datos_conciliados,
)
from report_export.xlsx_to_pdf import convert_xlsx_bytes_to_pdf

TEMPLATE_XLSX_PATH = "./reporte/Template_DatosConcialiados.xlsx"
_REPORT_EXPORT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def setup_download_route(server):
    """No-op kept for import compatibility in main.py."""
    pass


def _enviar_descarga(contenido: bytes, nombre_archivo: str):
    """Fuerza una descarga binaria y evita la previsualización inline."""
    return dcc.send_bytes(
        contenido,
        nombre_archivo,
        type="application/octet-stream",
    )


# ── Clientside callback: show "generating" bar immediately on any button click ──
clientside_callback(
    """
    function(export_clicks, pdf_clicks) {
        const ctx = dash_clientside.callback_context;
        if (!ctx || !ctx.triggered || ctx.triggered.length === 0) {
            return window.dash_clientside.no_update;
        }
        const t = ctx.triggered[0];
        if (!t.value || t.value === 0) return window.dash_clientside.no_update;

        const isPdf = t.prop_id.toLowerCase().includes('pdf');
        const label = isPdf ? 'Generando PDF' : 'Generando Excel';

        return {
            props: {
                children: [
                    {
                        type: 'Span',
                        props: {
                            className: 'spinner-border spinner-border-sm me-2',
                            role: 'status'
                        },
                        namespace: 'dash_html_components'
                    },
                    label + ', por favor espere…'
                ],
                className: 'rp-progress-bar'
            },
            type: 'Div',
            namespace: 'dash_html_components'
        };
    }
    """,
    Output("report-progress", "children"),
    Input({"type": "report-export-btn", "tipo": ALL}, "n_clicks"),
    Input({"type": "report-pdf-btn", "tipo": ALL}, "n_clicks"),
    prevent_initial_call=True,
)


@callback(
    Output("report-fecha-mes-wrap", "style"),
    Output("report-fecha-rango-wrap", "style"),
    Output("report-fecha-inicio", "date", allow_duplicate=True),
    Output("report-fecha-final", "date", allow_duplicate=True),
    Output("report-fecha-inicio", "initial_visible_month"),
    Output("report-fecha-final", "initial_visible_month"),
    Input("report-fecha-modo", "value"),
    Input("report-fecha-mes", "value"),
    prevent_initial_call="initial_duplicate",
)
def sync_modo_y_mes(modo, mes_val):
    """Alterna controles visibles y sincroniza fechas al elegir mes completo."""
    if modo == "rango":
        return (
            {"display": "none"},
            {"display": "block"},
            no_update,
            no_update,
            no_update,
            no_update,
        )

    if not mes_val:
        return (
            {"display": "block"},
            {"display": "none"},
            no_update,
            no_update,
            no_update,
            no_update,
        )

    year, month = map(int, mes_val.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    ini = f"{year:04d}-{month:02d}-01"
    fin = f"{year:04d}-{month:02d}-{last_day:02d}"
    return (
        {"display": "block"},
        {"display": "none"},
        ini,
        fin,
        ini,
        fin,
    )


@callback(
    Output("report-fecha-inicio", "date", allow_duplicate=True),
    Output("report-fecha-warning", "children"),
    Output("report-status", "children", allow_duplicate=True),
    Input("report-fecha-inicio", "date"),
    Input("report-fecha-final", "date"),
    State("report-fecha-modo", "value"),
    prevent_initial_call=True,
)
def validar_rango_fechas(fecha_ini, fecha_fin, modo):
    if modo == "mes":
        return no_update, html.Div(), html.Div()

    if not fecha_ini or not fecha_fin:
        return no_update, html.Div(), html.Div()

    ini = pd.to_datetime(fecha_ini)
    fin = pd.to_datetime(fecha_fin)

    if ini > fin:
        corregida = fin - pd.Timedelta(days=7)
        warning = dbc.Alert(
            "Fecha inicio ajustada a una semana antes de Fecha final.",
            color="warning",
            className="py-1 px-2 mb-0 small",
            dismissable=True,
        )
        return corregida.strftime("%Y-%m-%d"), warning, html.Div()

    return no_update, html.Div(), html.Div()


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
_COLUMNAS_VISIBLES_BD_TON = [
    "Fecha",
    "Apilado TMH CV-08 TA",
    "Apilado TMH CV-08 TB",
    "Apilado TMH CV-108 TA",
    "Apilado TMH CV-108 TB",
    "Rep. TM1 TA Qui.",
    "Rep. TM1 TA Fis.",
    "Rep. TM1 TB Qui.",
    "Rep. TM1 TB Fis.",
    "Rep. TM2 TA Qui.",
    "Rep. TM2 TA Fis.",
    "Rep. TM2 TB Qui.",
    "Rep. TM2 TB Fis.",
    "Muestra representativa TM1 TA",
    "Muestra representativa TM1 TB",
    "Muestra representativa TM2 TA",
    "Muestra representativa TM2 TB",
    "FISICO TM1 TA",
    "FISICO TM1 TB",
    "FISICO TM2 TA",
    "FISICO TM2 TB",
]


def _agregar_hoja_bd_ton(wb, df_bd_ton: pd.DataFrame) -> None:
    """
    Agrega la hoja BD Ton con la estética del bloque AT:BM de
    Reporte Diario: fondo blanco, encabezados jerárquicos,
    bordes completos y desplazamiento libre sin paneles inmovilizados.
    """
    from openpyxl.styles import (
        Font,
        Alignment,
        PatternFill,
        Border,
        Side,
    )
    from openpyxl.utils import get_column_letter

    df = df_bd_ton.copy()
    columnas_faltantes = [
        columna
        for columna in _COLUMNAS_VISIBLES_BD_TON
        if columna not in df.columns
    ]
    if columnas_faltantes:
        raise RuntimeError(
            "BD Ton no contiene todas las columnas visibles requeridas. "
            f"Faltantes: {columnas_faltantes}. "
            f"Recibidas: {list(df.columns)}"
        )

    # Las columnas auxiliares de evaluabilidad permanecen disponibles en
    # los DataFrames de cálculo, pero no alteran la estructura visual A:U.
    df = df[_COLUMNAS_VISIBLES_BD_TON].copy()

    if "BD Ton" in wb.sheetnames:
        del wb["BD Ton"]

    ws = wb.create_sheet(title="BD Ton")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = None

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce",
        )
        df = (
            df[df["Fecha"].notna()]
            .sort_values("Fecha", kind="stable")
            .drop_duplicates(
                subset=["Fecha"],
                keep="last",
            )
            .reset_index(drop=True)
        )

    # Paleta equivalente a Reporte Diario, columnas AT:BM.
    color_header = "D7E1E7"
    color_texto = "476475"
    color_borde = "476475"
    color_borde_interno = "A6A6A6"
    color_subtitulo = "666666"

    fill_blanco = PatternFill("solid", fgColor="FFFFFF")
    fill_header = PatternFill("solid", fgColor=color_header)
    fill_alt = PatternFill("solid", fgColor=color_header)

    font_titulo = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=14,
    )
    font_subtitulo = Font(
        name="Arial",
        italic=True,
        color=color_subtitulo,
        size=9,
    )
    font_header = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=10,
    )
    font_normal = Font(
        name="Arial",
        color=color_texto,
        size=9,
    )
    font_fecha = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=9,
    )

    thin = Side(style="thin", color=color_borde_interno)
    thin_header = Side(style="thin", color=color_borde)
    medium = Side(style="medium", color=color_borde)

    border_datos = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin,
    )
    border_header = Border(
        left=thin_header,
        right=thin_header,
        top=thin_header,
        bottom=thin_header,
    )

    center = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )

    def _aplicar_contorno(
        fila_ini: int,
        col_ini: int,
        fila_fin: int,
        col_fin: int,
    ) -> None:
        """Refuerza solo el contorno del bloque, conservando la grilla interna."""
        for fila in range(fila_ini, fila_fin + 1):
            for col in range(col_ini, col_fin + 1):
                celda = ws.cell(fila, col)
                borde_actual = celda.border
                celda.border = Border(
                    left=medium if col == col_ini else borde_actual.left,
                    right=medium if col == col_fin else borde_actual.right,
                    top=medium if fila == fila_ini else borde_actual.top,
                    bottom=medium if fila == fila_fin else borde_actual.bottom,
                )

    # ------------------------------------------------------------
    # Título y descripción
    # ------------------------------------------------------------
    ws.merge_cells("A1:U1")
    ws["A1"] = "Base de datos de tonelajes e indicadores de representatividad"
    ws["A1"].font = font_titulo
    ws["A1"].alignment = center
    ws["A1"].fill = fill_blanco

    ws.merge_cells("A2:U2")
    ws["A2"] = (
        "Detalle diario de tonelajes, representatividad calculada "
        "e indicadores oficiales de muestra."
    )
    ws["A2"].font = font_subtitulo
    ws["A2"].alignment = center
    ws["A2"].fill = fill_blanco

    # ------------------------------------------------------------
    # Encabezados jerárquicos
    # ------------------------------------------------------------
    ws.merge_cells("A4:A6")
    ws.merge_cells("B4:E4")
    ws.merge_cells("F4:M4")
    ws.merge_cells("N4:U4")

    ws.merge_cells("B5:C5")
    ws.merge_cells("D5:E5")
    ws.merge_cells("F5:I5")
    ws.merge_cells("J5:M5")
    ws.merge_cells("N5:Q5")
    ws.merge_cells("R5:U5")

    ws["A4"] = "Fecha"
    ws["B4"] = "Tonelaje apilado TMH"
    ws["F4"] = "Representatividad calculada"
    ws["N4"] = "Indicador oficial de muestra representativa"

    ws["B5"] = "TM1 · CV-08"
    ws["D5"] = "TM2 · CV-108"
    ws["F5"] = "Torre de muestreo 1"
    ws["J5"] = "Torre de muestreo 2"
    ws["N5"] = "Químico"
    ws["R5"] = "Físico"

    headers_fila_6 = [
        "TA",
        "TB",
        "TA",
        "TB",
        "TA Químico",
        "TA Físico",
        "TB Químico",
        "TB Físico",
        "TA Químico",
        "TA Físico",
        "TB Químico",
        "TB Físico",
        "TM1 TA",
        "TM1 TB",
        "TM2 TA",
        "TM2 TB",
        "TM1 TA",
        "TM1 TB",
        "TM2 TA",
        "TM2 TB",
    ]

    for col, valor in enumerate(headers_fila_6, start=2):
        ws.cell(6, col, valor)

    for fila in range(4, 7):
        for col in range(1, 22):
            celda = ws.cell(fila, col)
            celda.fill = fill_header
            celda.font = font_header
            celda.alignment = center
            celda.border = border_header

    # ------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------
    fila_inicio = 7

    for fila_excel, valores in enumerate(
        df.itertuples(index=False, name=None),
        start=fila_inicio,
    ):
        es_alterna = (fila_excel - fila_inicio) % 2 == 1

        for col_idx, valor in enumerate(valores, start=1):
            nombre_columna = str(df.columns[col_idx - 1])

            if pd.isna(valor):
                valor_excel = None
            elif isinstance(valor, pd.Timestamp):
                valor_excel = valor.to_pydatetime()
            elif hasattr(valor, "item"):
                valor_excel = valor.item()
            else:
                valor_excel = valor

            celda = ws.cell(
                row=fila_excel,
                column=col_idx,
                value=valor_excel,
            )
            celda.fill = fill_alt if es_alterna else fill_blanco
            celda.font = font_normal
            celda.alignment = center
            celda.border = border_datos

            if nombre_columna == "Fecha":
                celda.number_format = "dd-mm-yyyy"
                celda.font = font_fecha
            elif nombre_columna.startswith("Apilado TMH"):
                celda.number_format = "#,##0.0"
            elif nombre_columna.startswith("Rep."):
                celda.number_format = "0.000"
            elif (
                nombre_columna.startswith("Muestra representativa")
                or nombre_columna.startswith("FISICO")
            ):
                celda.number_format = "0"

    ultima_fila = max(fila_inicio + len(df) - 1, fila_inicio)

    # Contornos por bloque funcional.
    for col_ini, col_fin in [
        (1, 1),
        (2, 5),
        (6, 13),
        (14, 21),
    ]:
        _aplicar_contorno(4, col_ini, ultima_fila, col_fin)

    # Dimensiones equivalentes al bloque AT:BM.
    ws.column_dimensions["A"].width = 13
    for col in range(2, 6):
        ws.column_dimensions[get_column_letter(col)].width = 14
    for col in range(6, 14):
        ws.column_dimensions[get_column_letter(col)].width = 14
    for col in range(14, 22):
        ws.column_dimensions[get_column_letter(col)].width = 13

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 26
    ws.row_dimensions[6].height = 26
    for fila in range(fila_inicio, ultima_fila + 1):
        ws.row_dimensions[fila].height = 21

    if len(df.columns) > 0 and len(df) > 0:
        ultima_columna = get_column_letter(len(df.columns))
        ws.auto_filter.ref = f"A6:{ultima_columna}{ultima_fila}"


_MESES_ABR_TORRES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}

_MESES_NOMBRE_TORRES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

def _obtener_rango_fiscal_hasta_mes(fecha_reporte) -> dict:
    """
    Obtiene el rango desde el inicio del año fiscal hasta el último
    día del mes evaluado.

    Ejemplo:
        Enero 2026 -> FY26
        Desde 01-07-2025 hasta 31-01-2026.
    """

    fecha = pd.to_datetime(fecha_reporte).date()

    anio_fiscal = (
        fecha.year + 1
        if fecha.month >= 7
        else fecha.year
    )

    fecha_inicio_fy = pd.Timestamp(
        year=anio_fiscal - 1,
        month=7,
        day=1,
    ).date()

    ultimo_dia_mes = calendar.monthrange(
        fecha.year,
        fecha.month,
    )[1]

    fecha_fin_mes = fecha.replace(
        day=ultimo_dia_mes
    )

    return {
        "anio_fiscal": anio_fiscal,
        "fecha_inicio": fecha_inicio_fy,
        "fecha_fin": fecha_fin_mes,
    }

def _normalizar_turno_torres(valor) -> str:
    texto = str(valor or "").strip().upper().replace(" ", "")

    if texto in {"A", "TA", "TURNOA"}:
        return "TA"
    if texto in {"B", "TB", "TURNOB"}:
        return "TB"

    return texto


def _normalizar_material_torres(valor) -> str:
    texto = str(valor or "").strip().upper()

    if "SULF" in texto:
        return "Sulfuro"
    if "OX" in texto or "ÓX" in texto:
        return "Óxido"

    return "Sin clasificar"

def _preparar_material_por_turno(
    df_turno: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza la fuente independiente de estado de apilado para cada
    Fecha + Turno y entrega:

    - El material informado por la fuente independiente.
    - El apilado oficial del turno.
    - El estado de evaluabilidad según RN-046.

    Desde el 01-01-2026 la evaluabilidad se toma directamente del campo
    oficial Turno_Evaluable. Para fechas anteriores se conserva la regla
    histórica basada en apilado mayor que cero.
    """
    columnas_salida = [
        "Fecha",
        "Turno",
        "Pad",
        "Apilado_TMS_Real_Turno",
        "Turno_Evaluable",
        "Turno_Activo_Oficial",
    ]

    if df_turno is None or df_turno.empty:
        return pd.DataFrame(columns=columnas_salida)

    requeridas = {
        "Fecha",
        "Turno",
        "Material",
        "Apilado_TMS_Real",
    }

    if not requeridas.issubset(df_turno.columns):
        return pd.DataFrame(columns=columnas_salida)

    df = df_turno.copy()

    df["Fecha"] = pd.to_datetime(
        df["Fecha"],
        errors="coerce",
    ).dt.normalize()

    df["Turno"] = df["Turno"].apply(
        _normalizar_turno_torres
    )

    df["Pad"] = df["Material"].apply(
        _normalizar_material_torres
    )

    df["Tonelaje"] = pd.to_numeric(
        df["Apilado_TMS_Real"],
        errors="coerce",
    ).fillna(0.0)

    if "Turno_Evaluable" in df.columns:
        df["Turno_Evaluable"] = (
            pd.to_numeric(
                df["Turno_Evaluable"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )
    else:
        # Compatibilidad con fuentes históricas que no incluían el flag.
        df["Turno_Evaluable"] = 0

    df = df[
        df["Fecha"].notna()
        & df["Turno"].isin(["TA", "TB"])
    ].copy()

    if df.empty:
        return pd.DataFrame(columns=columnas_salida)

    # Normalización defensiva por material para garantizar una sola fila
    # por Fecha + Turno, incluso si la fuente cambia accidentalmente.
    tonelaje_material = (
        df.groupby(
            ["Fecha", "Turno", "Pad"],
            as_index=False,
            dropna=False,
        )["Tonelaje"]
        .sum()
    )

    # Conservar un único material por Fecha + Turno.
    material_predominante = (
        tonelaje_material.sort_values(
            ["Fecha", "Turno", "Tonelaje", "Pad"],
            ascending=[True, True, False, True],
        )
        .drop_duplicates(["Fecha", "Turno"])
        [["Fecha", "Turno", "Pad"]]
    )

    # Obtener el apilado oficial del turno.
    apilado_turno = (
        df.groupby(
            ["Fecha", "Turno"],
            as_index=False,
        )["Tonelaje"]
        .sum()
        .rename(
            columns={
                "Tonelaje": "Apilado_TMS_Real_Turno"
            }
        )
    )

    # Conservar el indicador oficial en la misma granularidad Fecha + Turno.
    evaluabilidad_turno = (
        df.groupby(
            ["Fecha", "Turno"],
            as_index=False,
        )["Turno_Evaluable"]
        .max()
    )

    resultado = material_predominante.merge(
        apilado_turno,
        on=["Fecha", "Turno"],
        how="left",
        validate="one_to_one",
    )
    resultado = resultado.merge(
        evaluabilidad_turno,
        on=["Fecha", "Turno"],
        how="left",
        validate="one_to_one",
    )

    resultado["Apilado_TMS_Real_Turno"] = (
        pd.to_numeric(
            resultado["Apilado_TMS_Real_Turno"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    resultado["Turno_Evaluable"] = (
        pd.to_numeric(
            resultado["Turno_Evaluable"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    resultado["Turno_Activo_Oficial"] = (
        resultado["Apilado_TMS_Real_Turno"] > 0
    )

    mascara_flag_oficial = resultado["Fecha"] >= pd.Timestamp("2026-01-01")
    resultado.loc[
        mascara_flag_oficial,
        "Turno_Activo_Oficial",
    ] = resultado.loc[
        mascara_flag_oficial,
        "Turno_Evaluable",
    ].eq(1)

    resultado["Turno_Activo_Oficial"] = resultado[
        "Turno_Activo_Oficial"
    ].astype(bool)

    return (
        resultado[columnas_salida]
        .sort_values(["Fecha", "Turno"])
        .reset_index(drop=True)
    )

def _numero_semana_mensual(
    fecha: pd.Timestamp,
    primera_fecha: pd.Timestamp,
) -> int:
    """Replica WEEKNUM(fecha, 2) con semanas iniciadas en lunes."""
    fecha = pd.Timestamp(fecha).normalize()
    primera_fecha = pd.Timestamp(primera_fecha).normalize()

    lunes_fecha = fecha - pd.Timedelta(days=fecha.weekday())
    lunes_inicial = primera_fecha - pd.Timedelta(
        days=primera_fecha.weekday()
    )

    return int((lunes_fecha - lunes_inicial).days // 7) + 1


def _numero_torres(valor) -> float:
    numero = pd.to_numeric(valor, errors="coerce")
    return 0.0 if pd.isna(numero) else float(numero)


def _flag_representatividad_torres(
    activo: bool,
    valor_flag,
    valor_representatividad,
) -> int | None:
    if not activo:
        return None

    flag = pd.to_numeric(valor_flag, errors="coerce")
    if pd.notna(flag):
        return 1 if float(flag) >= 1 else 0

    representatividad = pd.to_numeric(
        valor_representatividad,
        errors="coerce",
    )
    if pd.notna(representatividad):
        return 1 if float(representatividad) >= 0.75 else 0

    # El turno posee apilado oficial, pero no existe un indicador
    # trazable de representatividad. Se clasifica provisionalmente
    # como no representativo. El campo Comentarios permanece vacío.
    return 0


def _preparar_detalle_mensual_torres(
    df_bd_ton: pd.DataFrame,
    tipo: str,
    df_material_turno: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Construye el detalle Fecha + Turno de las hojas mensuales.

    La BD Ton aporta tonelajes e indicadores de cada torre.
    La fuente independiente de estado de apilado aporta el material
    y determina si el turno es evaluable por Fecha + Turno,
    según RN-046.
    """
    tipo_normalizado = str(tipo).strip().lower()

    if tipo_normalizado == "quimico":
        config = {
            "tm1_flag": "Muestra representativa TM1 {turno}",
            "tm2_flag": "Muestra representativa TM2 {turno}",
            "tm1_rep": "Rep. TM1 {turno} Qui.",
            "tm2_rep": "Rep. TM2 {turno} Qui.",
        }
    elif tipo_normalizado == "fisico":
        config = {
            "tm1_flag": "FISICO TM1 {turno}",
            "tm2_flag": "FISICO TM2 {turno}",
            "tm1_rep": "Rep. TM1 {turno} Fis.",
            "tm2_rep": "Rep. TM2 {turno} Fis.",
        }
    else:
        raise ValueError(f"Tipo de hoja no soportado: {tipo}")

    df = df_bd_ton.copy()
    if "Fecha" not in df.columns or df.empty:
        return pd.DataFrame()

    df["Fecha"] = pd.to_datetime(
        df["Fecha"],
        errors="coerce",
    ).dt.normalize()

    df = (
        df[df["Fecha"].notna()]
        .sort_values("Fecha")
        .reset_index(drop=True)
    )

    if df.empty:
        return pd.DataFrame()

    primera_fecha = df["Fecha"].min()

    mapa_material = {}
    mapa_actividad = {}
    mapa_apilado_oficial = {}

    if df_material_turno is not None and not df_material_turno.empty:
        for _, fila_material in df_material_turno.iterrows():
            fecha_material = pd.to_datetime(
                fila_material.get("Fecha"),
                errors="coerce",
            )
            turno_material = _normalizar_turno_torres(
                fila_material.get("Turno")
            )

            if pd.isna(fecha_material):
                continue
            if turno_material not in {"TA", "TB"}:
                continue

            clave = (
                fecha_material.normalize(),
                turno_material,
            )

            mapa_material[clave] = _normalizar_material_torres(
                fila_material.get("Pad")
            )

            apilado_oficial = pd.to_numeric(
                fila_material.get("Apilado_TMS_Real_Turno"),
                errors="coerce",
            )
            if pd.isna(apilado_oficial):
                apilado_oficial = 0.0

            apilado_oficial = float(apilado_oficial)
            mapa_apilado_oficial[clave] = apilado_oficial

            actividad_fuente = fila_material.get(
                "Turno_Activo_Oficial"
            )
            if pd.isna(actividad_fuente):
                mapa_actividad[clave] = apilado_oficial > 0
            else:
                mapa_actividad[clave] = bool(actividad_fuente)

    registros = []

    for _, fila in df.iterrows():
        fecha = fila["Fecha"]
        semana_num = _numero_semana_mensual(
            fecha,
            primera_fecha,
        )

        for turno in ["TA", "TB"]:
            clave_turno = (fecha, turno)

            turno_activo_oficial = bool(
                mapa_actividad.get(clave_turno, False)
            )

            tm1_tmh_original = fila.get(
                f"Apilado TMH CV-08 {turno}"
            )
            tm2_tmh_original = fila.get(
                f"Apilado TMH CV-108 {turno}"
            )
            tm1_tmh = _numero_torres(
                tm1_tmh_original
            )
            tm2_tmh = _numero_torres(
                tm2_tmh_original
            )

            if fecha >= pd.Timestamp("2026-01-01"):
                # Desde 2026 existe una sola oportunidad operacional por
                # turno y la fuente oficial determina su evaluabilidad.
                tm1_activo = turno_activo_oficial
                tm2_activo = turno_activo_oficial
            else:
                # En el histórico la evaluabilidad es independiente por
                # torre. El tonelaje original se consulta antes de convertir
                # nulos a cero para no perder la diferencia NULL/0.
                tm1_evaluable = fila.get(f"Evaluable_TM1_{turno}")
                tm2_evaluable = fila.get(f"Evaluable_TM2_{turno}")

                tm1_evaluable_num = pd.to_numeric(
                    tm1_evaluable,
                    errors="coerce",
                )
                tm2_evaluable_num = pd.to_numeric(
                    tm2_evaluable,
                    errors="coerce",
                )

                tm1_activo = (
                    bool(int(tm1_evaluable_num) == 1)
                    if pd.notna(tm1_evaluable_num)
                    else pd.notna(tm1_tmh_original)
                )
                tm2_activo = (
                    bool(int(tm2_evaluable_num) == 1)
                    if pd.notna(tm2_evaluable_num)
                    else pd.notna(tm2_tmh_original)
                )

            turno_activo_combinado = bool(tm1_activo or tm2_activo)

            tm1_flag_fuente = fila.get(
                config["tm1_flag"].format(turno=turno)
            )
            tm2_flag_fuente = fila.get(
                config["tm2_flag"].format(turno=turno)
            )
            tm1_rep_fuente = fila.get(
                config["tm1_rep"].format(turno=turno)
            )
            tm2_rep_fuente = fila.get(
                config["tm2_rep"].format(turno=turno)
            )

            tm1_flag = _flag_representatividad_torres(
                tm1_activo,
                tm1_flag_fuente,
                tm1_rep_fuente,
            )
            tm2_flag = _flag_representatividad_torres(
                tm2_activo,
                tm2_flag_fuente,
                tm2_rep_fuente,
            )

            if tm1_flag == 1 or tm2_flag == 1:
                representatividad_turno = 1
            elif not turno_activo_combinado:
                representatividad_turno = None
            else:
                representatividad_turno = 0

            registros.append({
                "Semana_Num": semana_num,
                "Semana": f"Semana {semana_num}",
                "Fecha": fecha,
                "Pad": mapa_material.get(
                    clave_turno,
                    "Sin clasificar",
                ),
                "Turno": turno,
                "Apilado_Oficial_Turno": mapa_apilado_oficial.get(
                    clave_turno,
                    0.0,
                ),
                "TMH_CV08": tm1_tmh if tm1_activo else None,
                "TM1_Activo": int(tm1_activo),
                "Rep_TM1": tm1_flag,
                "Comentario_TM1": None,
                "TMH_CV108": tm2_tmh if tm2_activo else None,
                "TM2_Activo": int(tm2_activo),
                "Rep_TM2": tm2_flag,
                "Comentario_TM2": None,
                "Rep_Turno": representatividad_turno,
            })

    return pd.DataFrame(registros)


def _calcular_resumen_mensual_torres(
    detalle: pd.DataFrame,
) -> dict:
    """
    Calcula resultados semanales y MTD según RN-046.

    TM1 y TM2:
    - Denominador: turnos oficialmente evaluables.
    - Numerador: turnos representativos de la torre.

    Combinado:
    - Denominador: turnos oficialmente evaluables.
    - Numerador: turnos donde TM1 o TM2 fue representativa.

    El MTD se calcula como cociente de totales acumulados y no como
    promedio de porcentajes semanales.
    """
    resumen = {"TM1": [], "TM2": [], "COMBINADO": []}

    def _fila_resumen(df_semana, etiqueta):
        tm1_activos = int(df_semana["TM1_Activo"].sum())
        tm2_activos = int(df_semana["TM2_Activo"].sum())

        tm1_rep = int((df_semana["Rep_TM1"] == 1).sum())
        tm2_rep = int((df_semana["Rep_TM2"] == 1).sum())

        turnos_activos = int(
            (
                (df_semana["TM1_Activo"] == 1)
                | (df_semana["TM2_Activo"] == 1)
            ).sum()
        )
        turnos_representativos = int(
            (df_semana["Rep_Turno"] == 1).sum()
        )

        valores = {
            "TM1": (tm1_activos, tm1_rep),
            "TM2": (tm2_activos, tm2_rep),
            "COMBINADO": (
                turnos_activos,
                turnos_representativos,
            ),
        }

        for clave, (activos, representativos) in valores.items():
            no_representativos = max(
                activos - representativos,
                0,
            )
            pct_rep = (
                representativos / activos
                if activos
                else 0.0
            )
            pct_no_rep = (
                no_representativos / activos
                if activos
                else 0.0
            )
            total = (
                pct_rep + pct_no_rep
                if activos
                else 0.0
            )

            resumen[clave].append({
                "Periodo": etiqueta,
                "Turnos_Activos": activos,
                "Representativos": representativos,
                "No_Representativos": no_representativos,
                "Pct_Representativos": pct_rep,
                "Pct_No_Representativos": pct_no_rep,
                "Total": total,
            })

    for semana in range(1, 7):
        _fila_resumen(
            detalle[detalle["Semana_Num"] == semana],
            f"Semana {semana}",
        )

    _fila_resumen(detalle, "MTD")
    return resumen


def _calcular_tonelaje_por_material_torres(
    detalle: pd.DataFrame,
) -> list[dict]:
    resultados = []

    for material in ["Óxido", "Sulfuro"]:
        df_material = detalle[detalle["Pad"] == material]

        con_torre = float(
            df_material.loc[df_material["Rep_TM1"] == 1, "TMH_CV08"].sum()
            + df_material.loc[df_material["Rep_TM2"] == 1, "TMH_CV108"].sum()
        )
        sin_torre = float(
            df_material.loc[
                (df_material["TM1_Activo"] == 1)
                & (df_material["Rep_TM1"] != 1),
                "TMH_CV08",
            ].sum()
            + df_material.loc[
                (df_material["TM2_Activo"] == 1)
                & (df_material["Rep_TM2"] != 1),
                "TMH_CV108",
            ].sum()
        )

        total = con_torre + sin_torre
        resultados.extend([
            {
                "Pad": material,
                "Estado": "Con Torre",
                "Tonelaje": con_torre,
                "Distribucion": con_torre / total if total else 0.0,
            },
            {
                "Pad": material,
                "Estado": "Sin Torre",
                "Tonelaje": sin_torre,
                "Distribucion": sin_torre / total if total else 0.0,
            },
        ])

    return resultados


def _normalizar_gestion_fy(
    df_gestion_fy: pd.DataFrame,
    fecha_base,
) -> pd.DataFrame:
    """Adapta la salida del SP FY al contrato canónico del gráfico."""
    from datetime import date
    import re
    import unicodedata

    columnas_canonicas = [
        "Etiqueta",
        "Turnos_Evaluables",
        "Turnos_Representativos",
        "Representatividad",
        "Objetivo",
        "Orden",
        "Es_YTD",
    ]
    if df_gestion_fy is None or df_gestion_fy.empty:
        return pd.DataFrame(columns=columnas_canonicas)

    df = df_gestion_fy.copy()

    def _token(valor) -> str:
        texto = unicodedata.normalize("NFKD", str(valor))
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]", "", texto.lower())

    columnas_por_token = {_token(columna): columna for columna in df.columns}

    def _buscar_columna(*aliases):
        for alias in aliases:
            encontrada = columnas_por_token.get(_token(alias))
            if encontrada is not None:
                return encontrada
        return None

    col_etiqueta = _buscar_columna(
        "Etiqueta",
        "Periodo",
        "Mes",
        "Fecha",
        "Fecha_Mes",
        "Etiqueta_Mes",
        "Mes_Etiqueta",
    )
    col_evaluables = _buscar_columna(
        "Turnos_Evaluables",
        "Evaluables",
        "Total_Evaluables",
        "Cantidad_Evaluable",
    )
    col_representativos = _buscar_columna(
        "Turnos_Representativos",
        "Representativos",
        "Total_Representativos",
        "Cantidad_Representativa",
    )
    col_representatividad = _buscar_columna(
        "Representatividad",
        "Porcentaje",
        "Resultado",
        "Pct_Representatividad",
    )
    col_objetivo = _buscar_columna(
        "Objetivo",
        "Target",
        "Meta",
    )
    col_orden = _buscar_columna(
        "Orden",
        "Orden_Mes",
        "Orden_Fiscal",
    )
    col_es_ytd = _buscar_columna(
        "Es_YTD",
        "Tipo_Fila",
        "Tipo_Registro",
    )

    requeridas = {
        "Etiqueta/Periodo/Mes": col_etiqueta,
        "Turnos_Evaluables/Evaluables": col_evaluables,
        "Turnos_Representativos/Representativos": col_representativos,
        "Objetivo/Target": col_objetivo,
    }
    faltantes = [nombre for nombre, columna in requeridas.items() if columna is None]
    if faltantes:
        raise RuntimeError(
            "La gestión FY no contiene las columnas indispensables. "
            f"Requeridas: {faltantes}. Recibidas: {list(df.columns)}"
        )

    fecha_base = pd.Timestamp(fecha_base).normalize()
    rango_fy = _obtener_rango_fiscal_hasta_mes(fecha_base)
    inicio_fy = pd.Timestamp(rango_fy["fecha_inicio"])
    orden_corte = (
        (fecha_base.year - inicio_fy.year) * 12
        + fecha_base.month
        - inicio_fy.month
        + 1
    )

    etiquetas_originales = df[col_etiqueta]

    def _es_ytd(etiqueta, valor=None) -> bool:
        texto_etiqueta = _token(etiqueta)
        if "ytd" in texto_etiqueta or "acumulado" in texto_etiqueta:
            return True
        if valor is None or pd.isna(valor):
            return False
        if isinstance(valor, (bool, int, float)):
            return bool(valor)
        texto = _token(valor)
        return texto in {"1", "true", "si", "ytd", "acumulado"}

    if col_es_ytd is not None:
        es_ytd = pd.Series(
            [
                _es_ytd(etiqueta, valor)
                for etiqueta, valor in zip(
                    etiquetas_originales,
                    df[col_es_ytd],
                )
            ],
            index=df.index,
            dtype=bool,
        )
    else:
        es_ytd = etiquetas_originales.apply(_es_ytd).astype(bool)

    meses_es = {
        "ene": 1,
        "feb": 2,
        "mar": 3,
        "abr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dic": 12,
    }

    def _orden_desde_etiqueta(valor):
        if pd.isna(valor):
            return None
        if isinstance(valor, (pd.Timestamp, date)):
            fecha = pd.Timestamp(valor)
        elif isinstance(valor, (int, float)) and 1 <= int(valor) <= 12:
            mes = int(valor)
            anio = rango_fy["anio_fiscal"] - 1 if mes >= 7 else rango_fy["anio_fiscal"]
            fecha = pd.Timestamp(year=anio, month=mes, day=1)
        else:
            texto = str(valor).strip()
            token = _token(texto)
            mes = next(
                (numero for nombre, numero in meses_es.items() if token.startswith(nombre)),
                None,
            )
            if mes is not None:
                coincidencia_anio = re.search(r"(\d{2,4})", texto)
                if coincidencia_anio:
                    anio = int(coincidencia_anio.group(1))
                    if anio < 100:
                        anio += 2000
                else:
                    anio = (
                        rango_fy["anio_fiscal"] - 1
                        if mes >= 7
                        else rango_fy["anio_fiscal"]
                    )
                fecha = pd.Timestamp(year=anio, month=mes, day=1)
            else:
                fecha = pd.to_datetime(texto, errors="coerce")
                if pd.isna(fecha):
                    return None

        return int(
            (fecha.year - inicio_fy.year) * 12
            + fecha.month
            - inicio_fy.month
            + 1
        )

    if col_orden is not None:
        orden = pd.to_numeric(df[col_orden], errors="coerce")
    else:
        orden = pd.Series(index=df.index, dtype=float)

    orden_derivado = etiquetas_originales.apply(_orden_desde_etiqueta)
    orden = orden.where(orden.notna(), orden_derivado)
    orden = orden.where(~es_ytd, 13)

    gestion = pd.DataFrame({
        "Etiqueta_Original": etiquetas_originales,
        "Turnos_Evaluables": pd.to_numeric(
            df[col_evaluables], errors="coerce"
        ),
        "Turnos_Representativos": pd.to_numeric(
            df[col_representativos], errors="coerce"
        ),
        "Objetivo": pd.to_numeric(df[col_objetivo], errors="coerce"),
        "Orden": pd.to_numeric(orden, errors="coerce"),
        "Es_YTD": es_ytd,
    })

    if col_representatividad is not None:
        gestion["Representatividad"] = pd.to_numeric(
            df[col_representatividad],
            errors="coerce",
        )
    else:
        gestion["Representatividad"] = pd.NA

    for columna in ["Representatividad", "Objetivo"]:
        gestion[columna] = gestion[columna].apply(
            lambda valor: (
                float(valor) / 100.0
                if pd.notna(valor) and abs(float(valor)) > 1
                else float(valor)
                if pd.notna(valor)
                else float("nan")
            )
        )

    meses = gestion[
        (~gestion["Es_YTD"])
        & gestion["Orden"].between(1, orden_corte, inclusive="both")
    ].copy()
    meses = (
        meses.sort_values("Orden", kind="stable")
        .drop_duplicates("Orden", keep="last")
        .reset_index(drop=True)
    )

    if meses.empty:
        raise RuntimeError(
            "La gestión FY no contiene meses hasta la fecha evaluada. "
            f"Columnas recibidas: {list(df.columns)}"
        )
    if meses[["Turnos_Evaluables", "Turnos_Representativos", "Objetivo"]].isna().any().any():
        raise RuntimeError(
            "La gestión FY contiene valores nulos en evaluables, "
            "representativos u objetivo."
        )

    calculada = meses["Turnos_Representativos"].div(
        meses["Turnos_Evaluables"].where(meses["Turnos_Evaluables"] != 0)
    )
    meses["Representatividad"] = meses["Representatividad"].where(
        meses["Representatividad"].notna(),
        calculada,
    ).fillna(0.0)

    def _etiqueta_fiscal(valor_orden: int) -> str:
        fecha = inicio_fy + pd.DateOffset(months=int(valor_orden) - 1)
        return f"{_MESES_ABR_TORRES[fecha.month]}-{str(fecha.year)[-2:]}"

    meses["Etiqueta"] = meses["Orden"].astype(int).apply(_etiqueta_fiscal)

    total_evaluables = float(meses["Turnos_Evaluables"].sum())
    total_representativos = float(meses["Turnos_Representativos"].sum())
    representatividad_ytd = (
        total_representativos / total_evaluables
        if total_evaluables
        else 0.0
    )

    filas_ytd = gestion[gestion["Es_YTD"]]
    objetivo_ytd = (
        float(filas_ytd["Objetivo"].dropna().iloc[-1])
        if not filas_ytd["Objetivo"].dropna().empty
        else float(meses["Objetivo"].iloc[-1])
    )
    ytd = pd.DataFrame([{
        "Etiqueta": "YTD",
        "Turnos_Evaluables": total_evaluables,
        "Turnos_Representativos": total_representativos,
        "Representatividad": representatividad_ytd,
        "Objetivo": objetivo_ytd,
        "Orden": 13,
        "Es_YTD": True,
    }])

    resultado = pd.concat(
        [meses[columnas_canonicas], ytd[columnas_canonicas]],
        ignore_index=True,
    )
    return resultado


def _agregar_grafico_gestion_fy(
    ws,
    df_gestion_fy: pd.DataFrame,
    tipo: str,
    fecha_base,
    fila_inicio: int,
) -> None:
    """Agrega el gráfico FY y su tabla auxiliar oculta en T:X."""
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.chart.data_source import (
        AxDataSource,
        NumData,
        NumVal,
        StrData,
        StrRef,
        StrVal,
    )
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.series import SeriesLabel
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import quote_sheetname

    if df_gestion_fy is None or df_gestion_fy.empty:
        raise RuntimeError("La gestión FY normalizada está vacía.")

    fecha_base = pd.Timestamp(fecha_base)
    anio_fiscal = _obtener_rango_fiscal_hasta_mes(fecha_base)["anio_fiscal"]
    tipo_texto = "química" if str(tipo).lower() == "quimico" else "física"
    titulo = (
        f"Gestión de representatividad {tipo_texto} "
        f"FY{anio_fiscal % 100:02d}"
    )

    ws.merge_cells(
        start_row=fila_inicio,
        start_column=3,
        end_row=fila_inicio,
        end_column=13,
    )
    celda_titulo = ws.cell(fila_inicio, 3, f"6.- {titulo}.")
    celda_titulo.font = Font(
        name="Arial",
        bold=True,
        color="476475",
        size=10,
    )
    celda_titulo.alignment = Alignment(horizontal="left", vertical="center")
    lado = Side(style="thin", color="595959")
    for columna in range(3, 14):
        ws.cell(fila_inicio, columna).border = Border(bottom=lado)

    # Tabla auxiliar del gráfico FY: T:X.
    fila_tabla = fila_inicio
    encabezados = [
        "Periodo",
        "Turnos evaluables",
        "Turnos representativos",
        "Representatividad",
        "Objetivo",
    ]
    for columna, encabezado in enumerate(encabezados, start=20):
        ws.cell(fila_tabla, columna, encabezado)

    etiquetas = []
    valores_representatividad = []
    valores_objetivo = []

    for offset, (_, fila) in enumerate(df_gestion_fy.iterrows(), start=1):
        etiqueta = str(fila["Etiqueta"])
        representatividad = float(fila["Representatividad"])
        objetivo = float(fila["Objetivo"])

        valores = [
            etiqueta,
            float(fila["Turnos_Evaluables"]),
            float(fila["Turnos_Representativos"]),
            representatividad,
            objetivo,
        ]
        for columna, valor in enumerate(valores, start=20):
            ws.cell(fila_tabla + offset, columna, valor)

        ws.cell(fila_tabla + offset, 23).number_format = "0%"
        ws.cell(fila_tabla + offset, 24).number_format = "0%"

        etiquetas.append(etiqueta)
        valores_representatividad.append(representatividad)
        valores_objetivo.append(objetivo)

    fila_final = fila_tabla + len(df_gestion_fy)
    categorias = Reference(
        ws,
        min_col=20,
        min_row=fila_tabla + 1,
        max_row=fila_final,
    )

    # Categorías como texto explícito y con caché. Esto evita que Excel
    # transforme o descarte las categorías cuando T:X están ocultas.
    formula_categorias = (
        f"{quote_sheetname(ws.title)}!"
        f"$T${fila_tabla + 1}:$T${fila_final}"
    )

    def _fuente_categorias() -> AxDataSource:
        return AxDataSource(
            strRef=StrRef(
                f=formula_categorias,
                strCache=StrData(
                    ptCount=len(etiquetas),
                    pt=[
                        StrVal(idx=indice, v=etiqueta)
                        for indice, etiqueta in enumerate(etiquetas)
                    ],
                ),
            )
        )

    chart = BarChart()
    chart.type = "col"
    chart.style = 2
    chart.grouping = "clustered"
    chart.varyColors = False
    chart.title = titulo
    chart.width = 19
    chart.height = 8

    # Fundamental: el gráfico debe leer los datos aunque T:X estén ocultas.
    # openpyxl lo serializa como <plotVisOnly val="0"/>.
    chart.visible_cells_only = False

    chart.y_axis.scaling.min = 0
    chart.y_axis.scaling.max = 1
    chart.y_axis.numFmt = "0%"
    chart.y_axis.majorUnit = 0.1
    chart.y_axis.title = "Representatividad"
    chart.x_axis.title = None
    chart.legend.position = "b"

    datos = Reference(
        ws,
        min_col=23,
        min_row=fila_tabla,
        max_row=fila_final,
    )
    chart.add_data(datos, titles_from_data=True)
    chart.set_categories(categorias)
    chart.series[0].cat = _fuente_categorias()
    chart.series[0].tx = SeriesLabel(v="Representatividad")
    chart.series[0].graphicalProperties.solidFill = "476475"
    chart.series[0].graphicalProperties.line.noFill = True

    # Caché numérica explícita para que Excel, LibreOffice y los
    # previsualizadores rendericen el gráfico sin depender de recálculo.
    chart.series[0].val.numRef.numCache = NumData(
        formatCode="0%",
        ptCount=len(valores_representatividad),
        pt=[
            NumVal(idx=indice, v=valor)
            for indice, valor in enumerate(valores_representatividad)
        ],
    )

    chart.dLbls = DataLabelList()
    chart.dLbls.showVal = True
    chart.dLbls.showLegendKey = False
    chart.dLbls.showCatName = False
    chart.dLbls.showSerName = False
    chart.dLbls.showPercent = False
    chart.dLbls.showBubbleSize = False
    chart.dLbls.numFmt = "0%"
    chart.dLbls.position = "outEnd"

    target_chart = LineChart()
    target_chart.visible_cells_only = False
    target_data = Reference(
        ws,
        min_col=24,
        min_row=fila_tabla,
        max_row=fila_final,
    )
    target_chart.add_data(target_data, titles_from_data=True)
    target_chart.set_categories(categorias)
    target_chart.series[0].cat = _fuente_categorias()
    target_chart.series[0].tx = SeriesLabel(v="Objetivo 85%")
    target_chart.series[0].val.numRef.numCache = NumData(
        formatCode="0%",
        ptCount=len(valores_objetivo),
        pt=[
            NumVal(idx=indice, v=valor)
            for indice, valor in enumerate(valores_objetivo)
        ],
    )
    target_chart.series[0].graphicalProperties.line.solidFill = "4F81BD"
    target_chart.series[0].graphicalProperties.line.prstDash = "dash"
    target_chart.series[0].graphicalProperties.line.width = 22225
    target_chart.series[0].marker.symbol = "none"
    target_chart.x_axis.axId = chart.x_axis.axId
    target_chart.y_axis.axId = chart.y_axis.axId
    target_chart.x_axis.delete = True
    target_chart.y_axis.delete = True
    chart += target_chart

    ws.add_chart(chart, f"C{fila_inicio + 2}")

    # La tabla auxiliar sigue oculta, pero el gráfico puede leerla porque
    # visible_cells_only=False.
    for columna in range(20, 25):
        ws.column_dimensions[
            ws.cell(1, columna).column_letter
        ].hidden = True

    fila_fin_impresion = fila_inicio + 34
    ws.print_area = f"A1:M{fila_fin_impresion}"
def _agregar_hoja_mensual_torres(
    wb,
    df_bd_ton_mes: pd.DataFrame,
    tipo: str,
    df_material_turno_mes: pd.DataFrame | None = None,
    df_gestion_fy: pd.DataFrame | None = None,
) -> str | None:
    """
    Agrega una hoja mensual Químico/Físico al libro.

    Los resultados se escriben como valores calculados en Python para
    evitar GETPIVOTDATA, tablas dinámicas y fórmulas manuales frágiles.
    """
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.chart.axis import ChartLines
    from openpyxl.chart.data_source import NumData, NumVal
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.layout import Layout, ManualLayout
    from openpyxl.chart.legend import LegendEntry
    from openpyxl.chart.series import SeriesLabel
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.spreadsheet_drawing import (
        AnchorMarker,
        TwoCellAnchor,
    )
    from openpyxl.drawing.text import (
        CharacterProperties,
        Paragraph,
        ParagraphProperties,
        RichTextProperties,
    )
    from openpyxl.styles import (
        Alignment,
        Border,
        Font,
        PatternFill,
        Side,
    )
    from openpyxl.utils import get_column_letter

    detalle = _preparar_detalle_mensual_torres(
        df_bd_ton=df_bd_ton_mes,
        tipo=tipo,
        df_material_turno=df_material_turno_mes,
    )

    if detalle.empty:
        return None

    fecha_base = pd.to_datetime(detalle["Fecha"].min())
    nombre_hoja = (
        f"01_{_MESES_ABR_TORRES[fecha_base.month]}_"
        f"{str(fecha_base.year)[-2:]} {tipo}"
    )
    nombre_hoja = nombre_hoja[:31]

    if nombre_hoja in wb.sheetnames:
        del wb[nombre_hoja]

    ws = wb.create_sheet(title=nombre_hoja)
    ws.sheet_view.showGridLines = False

    resumen = _calcular_resumen_mensual_torres(detalle)
    tonelaje_material = _calcular_tonelaje_por_material_torres(detalle)

    # Paleta y tipografías replicadas desde el reporte histórico.
    azul_header = PatternFill("solid", fgColor="D7E1E7")
    azul_grupo = PatternFill("solid", fgColor="D7E1E7")
    azul_alt = PatternFill("solid", fgColor="D7E1E7")
    amarillo = PatternFill("solid", fgColor="FFF2CC")
    gris = PatternFill("solid", fgColor="F2F2F2")

    font_header = Font(
        name="Arial",
        bold=True,
        color="476475",
        size=10,
    )
    font_resumen_header = Font(
        name="Arial",
        bold=False,
        color="476475",
        size=10,
    )
    font_titulo = Font(
        name="Arial",
        bold=True,
        color="476475",
        size=12,
    )
    font_normal = Font(
        name="Arial",
        color="476475",
        size=10,
    )
    font_nota = Font(
        name="Arial",
        color="666666",
        italic=True,
        size=9,
    )

    thin = Side(style="thin", color="595959")
    medium = Side(style="medium", color="404040")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    border_grupo = Border(
        left=medium,
        right=medium,
        top=medium,
        bottom=medium,
    )

    def _aplicar_bordes_tabla(
        fila_ini: int,
        col_ini: int,
        fila_fin: int,
        col_fin: int,
        borde_exterior=medium,
        borde_interior=thin,
    ) -> None:
        """Aplica grilla interna y contorno reforzado, incluso en rangos combinados."""
        for fila in range(fila_ini, fila_fin + 1):
            for col in range(col_ini, col_fin + 1):
                ws.cell(fila, col).border = Border(
                    left=(borde_exterior if col == col_ini else borde_interior),
                    right=(borde_exterior if col == col_fin else borde_interior),
                    top=(borde_exterior if fila == fila_ini else borde_interior),
                    bottom=(borde_exterior if fila == fila_fin else borde_interior),
                )

    def _aplicar_subrayado(
        fila: int,
        col_ini: int,
        col_fin: int,
        lado=thin,
    ) -> None:
        """Replica la línea inferior de los títulos de sección del reporte oficial."""
        for col in range(col_ini, col_fin + 1):
            celda = ws.cell(fila, col)
            celda.border = Border(bottom=lado)

    def _aplicar_semaforo(cell, valor, center_align):
        """
        Muestra un semáforo visual:
        - 1 -> círculo verde
        - 0 -> círculo rojo
        - None -> vacío
        """
        if valor == 1:
            cell.value = "●"
            cell.font = Font(
                name="Arial",
                bold=True,
                color="70AD47",
                size=16,
            )
            cell.alignment = center_align

        elif valor == 0:
            cell.value = "●"
            cell.font = Font(
                name="Arial",
                bold=True,
                color="C55A11",
                size=16,
            )
            cell.alignment = center_align

        else:
            cell.value = None
            cell.font = font_normal
            cell.alignment = center_align

    center = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )
    left = Alignment(
        horizontal="left",
        vertical="center",
        wrap_text=True,
    )
    left_no_wrap = Alignment(
        horizontal="left",
        vertical="center",
        wrap_text=False,
    )

    tipo_titulo = "Química" if tipo.lower() == "quimico" else "Física"
    mes_texto = f"{_MESES_NOMBRE_TORRES[fecha_base.month]}, {fecha_base.year}"

    ws.merge_cells("C5:M7")
    ws["C5"] = (
        "Muestras representativas y no representativas de torres de muestreo - "
        f"Muestra {tipo_titulo} - {mes_texto}"
    )
    ws["C5"].font = font_titulo
    ws["C5"].alignment = center

    ws.merge_cells("K2:M4")
    ws["K2"] = (
        "Superintendencia de Medición y Reconciliación\n"
        "Gerencia de Planificación de la Producción"
    )
    ws["K2"].font = Font(
        name="Arial",
        bold=True,
        color="476475",
        size=10,
    )
    ws["K2"].alignment = center

    # ------------------------------------------------------------
    # 1. Tonelaje por material y condición de representatividad
    # ------------------------------------------------------------
    ws.merge_cells("C9:F9")
    ws["C9"] = (
        "1.- Mineral apilado y caracterizado con información "
        f"{tipo_titulo.lower()} de torres de muestreo."
    )
    ws["C9"].font = font_header
    ws["C9"].alignment = left_no_wrap
    _aplicar_subrayado(9, 3, 6)

    # Misma estructura visual del reporte de referencia:
    # "Pad" y un encabezado agrupado para las tres columnas de mineral.
    ws["C10"] = "Pad"
    ws.merge_cells("D10:F10")
    ws["D10"] = "Mineral Apilado (ton)"

    for celda in ["C10", "D10"]:
        ws[celda].font = font_header
        ws[celda].alignment = center
        ws[celda].border = border

    for idx, fila in enumerate(tonelaje_material, start=11):
        ws.cell(idx, 3, fila["Pad"])
        ws.cell(idx, 4, fila["Estado"])
        ws.cell(idx, 5, fila["Tonelaje"])
        ws.cell(idx, 6, fila["Distribucion"])

        for col in range(3, 7):
            cell = ws.cell(idx, col)
            cell.font = font_normal
            cell.alignment = center
            cell.border = border

        ws.cell(idx, 5).number_format = "#,##0.0"
        ws.cell(idx, 6).number_format = "0.0%"

    ws.merge_cells("C11:C12")
    ws.merge_cells("C13:C14")
    ws["C11"].alignment = center
    ws["C13"].alignment = center

    # Contorno y grilla del bloque superior, como en la hoja oficial.
    _aplicar_bordes_tabla(10, 3, 14, 6, borde_exterior=thin)

    # ------------------------------------------------------------
    # Resúmenes semanales y MTD
    # ------------------------------------------------------------
    # Serie auxiliar de target. Se escriben siete valores para mantener
    # correspondencia exacta con las seis semanas y el MTD. Esta igualdad
    # de longitudes mejora la compatibilidad del gráfico entre Excel y
    # otros renderizadores sin alterar el target oficial de 85%.
    ws["Q1"] = "Target"
    ws["Q1"].font = font_header
    ws["Q1"].fill = azul_header
    ws["Q1"].alignment = center
    ws["Q1"].border = border
    for fila_target_aux in range(2, 9):
        ws.cell(fila_target_aux, 17, 0.85)
        ws.cell(fila_target_aux, 17).number_format = "0%"
        ws.cell(fila_target_aux, 17).alignment = center
        ws.cell(fila_target_aux, 17).border = border
    # Ocultar visualmente la tabla auxiliar del target sin eliminar
    # los valores utilizados por los gráficos.
    for fila_aux in range(1, 9):
        celda_aux = ws.cell(fila_aux, 17)

        celda_aux.number_format = ";;;"
        celda_aux.font = Font(
            name="Arial",
            color="FFFFFF",
            size=1,
        )
        celda_aux.fill = PatternFill(
            fill_type=None,
        )
        celda_aux.border = Border()

    secciones = [
        (
            "TM1",
            16,
            "2.- Torre de muestreo #1: Distribución porcentual de muestras representativas y no representativas.",
            "Torre #1",
        ),
        (
            "TM2",
            27,
            "3.- Torre de muestreo #2: Distribución porcentual de muestras representativas y no representativas.",
            "Torre #2",
        ),
        (
            "COMBINADO",
            38,
            "4.- Sistema TM1 y TM2: Distribución porcentual de muestras representativas y no representativas.",
            "Torre #1 y #2",
        ),
    ]

    for clave, fila_inicio, titulo_seccion, titulo_grafico in secciones:
        ws.merge_cells(
            start_row=fila_inicio,
            start_column=3,
            end_row=fila_inicio,
            end_column=6,
        )
        ws.cell(fila_inicio, 3, titulo_seccion)
        ws.cell(fila_inicio, 3).font = font_header
        ws.cell(fila_inicio, 3).alignment = left_no_wrap
        _aplicar_subrayado(fila_inicio, 3, 6)

        encabezados_por_seccion = {
            "TM1": [
                f"{_MESES_NOMBRE_TORRES[fecha_base.month]} {fecha_base.year}",
                "Muestras representativas TM1",
                "Muestras no representativas TM1",
                "Total TM1",
            ],
            "TM2": [
                f"{_MESES_NOMBRE_TORRES[fecha_base.month]} {fecha_base.year}",
                "Muestras representativas TM2",
                "Muestras no representativas TM2",
                "Total TM2",
            ],
            "COMBINADO": [
                f"{_MESES_NOMBRE_TORRES[fecha_base.month]} {fecha_base.year}",
                "Muestras representativas TM1+TM2",
                "Muestras no representativas TM1+TM2",
                "Total TM1+TM2",
            ],
        }
        encabezados = encabezados_por_seccion[clave]
        for col, valor in enumerate(encabezados, start=3):
            cell = ws.cell(fila_inicio + 1, col, valor)
            cell.font = font_resumen_header
            cell.alignment = center
            cell.border = border

        for offset, fila_resumen in enumerate(resumen[clave], start=2):
            fila_excel = fila_inicio + offset
            ws.cell(fila_excel, 3, fila_resumen["Periodo"])
            ws.cell(
                fila_excel,
                4,
                fila_resumen["Pct_Representativos"],
            )
            ws.cell(
                fila_excel,
                5,
                fila_resumen["Pct_No_Representativos"],
            )
            ws.cell(fila_excel, 6, fila_resumen["Total"])

            for col in range(3, 7):
                cell = ws.cell(fila_excel, col)
                cell.font = font_normal
                cell.alignment = center
                cell.border = border

            for col in range(4, 7):
                ws.cell(fila_excel, col).number_format = "0.0%"

            if fila_resumen["Periodo"] == "MTD":
                for col in range(3, 7):
                    ws.cell(fila_excel, col).font = Font(
                        name="Arial",
                        color="476475",
                        size=10,
                    )

        fila_target = fila_inicio + 9
        ws.merge_cells(
            start_row=fila_target,
            start_column=4,
            end_row=fila_target,
            end_column=6,
        )
        ws.cell(
            fila_target,
            4,
            "Target de muestras representativas: 85%",
        )
        ws.cell(fila_target, 4).font = Font(
            name="Arial",
            bold=True,
            color="476475",
            size=10,
        )
        ws.cell(fila_target, 4).alignment = left_no_wrap

        # Grilla visible y contorno reforzado de la tabla semanal.
        _aplicar_bordes_tabla(
            fila_inicio + 1,
            3,
            fila_inicio + 8,
            6,
            borde_exterior=thin,
            borde_interior=thin,
        )
        # La fila MTD queda separada visualmente, como en el reporte base.
        for col in range(3, 7):
            celda_mtd = ws.cell(fila_inicio + 8, col)
            celda_mtd.border = Border(
                left=(thin if col == 3 else thin),
                right=(thin if col == 6 else thin),
                top=medium,
                bottom=medium,
            )

        # Gráfico equivalente al reporte oficial:
        # columnas 100% apiladas, etiquetas porcentuales y línea target 85%.
        chart = BarChart()
        chart.style = 2
        chart.type = "col"
        chart.grouping = "percentStacked"
        chart.overlap = 100
        chart.gapWidth = 150
        chart.varyColors = False
        chart.title = titulo_grafico
        # El título no debe superponerse con la leyenda. En el reporte
        # oficial ambos elementos reservan su propio espacio vertical.
        chart.title.overlay = False
        chart.roundedCorners = False
        chart.height = 7.24
        chart.width = 18.40

        # Ejes como en el reporte oficial:
        # - Eje Y con porcentajes visibles
        # - Eje X con Semana 1 ... Semana 6 y MTD
        # - sin título de eje X
        chart.x_axis.title = None
        chart.y_axis.title = "Muestras representativas"

        chart.x_axis.delete = False
        chart.y_axis.delete = False

        chart.y_axis.scaling.min = 0
        chart.y_axis.scaling.max = 1
        chart.y_axis.numFmt = "0%"
        chart.y_axis.majorUnit = 0.1
        chart.y_axis.axPos = "l"
        chart.y_axis.tickLblPos = "nextTo"
        chart.y_axis.majorTickMark = "none"
        chart.y_axis.minorTickMark = "none"
        chart.y_axis.crossBetween = "between"

        chart.x_axis.axPos = "b"
        chart.x_axis.tickLblPos = "nextTo"
        chart.x_axis.majorTickMark = "none"
        chart.x_axis.minorTickMark = "none"

        chart.legend.position = "t"
        chart.legend.overlay = False
        chart.y_axis.majorGridlines = ChartLines()

        data = Reference(
            ws,
            min_col=4,
            max_col=5,
            min_row=fila_inicio + 1,
            max_row=fila_inicio + 8,
        )
        categorias = Reference(
            ws,
            min_col=3,
            min_row=fila_inicio + 2,
            max_row=fila_inicio + 8,
        )
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categorias)

        # Nombres explícitos para que Excel y otros renderizadores conserven
        # exactamente la leyenda del reporte de referencia.
        chart.series[0].tx = SeriesLabel(v=encabezados[1])
        chart.series[1].tx = SeriesLabel(v=encabezados[2])

        # OpenPyXL no siempre escribe el caché de los datos del gráfico.
        # Se incorpora explícitamente para que Excel, LibreOffice y los
        # previsualizadores interpreten 0,125 como 12,5% y no como 125m.
        valores_series = [
            [
                float(ws.cell(fila_inicio + offset, 4).value or 0.0)
                for offset in range(2, 9)
            ],
            [
                float(ws.cell(fila_inicio + offset, 5).value or 0.0)
                for offset in range(2, 9)
            ],
        ]
        for indice_serie, valores_cache in enumerate(valores_series):
            chart.series[indice_serie].val.numRef.numCache = NumData(
                formatCode="0%",
                ptCount=len(valores_cache),
                pt=[
                    NumVal(idx=indice, v=valor)
                    for indice, valor in enumerate(valores_cache)
                ],
            )

        # Colores y bordes de las series del reporte oficial.
        chart.series[0].graphicalProperties.solidFill = "476475"
        chart.series[0].graphicalProperties.line.noFill = True
        chart.series[1].graphicalProperties.solidFill = "E65400"
        chart.series[1].graphicalProperties.line.noFill = True

        # Etiquetas dentro de las columnas, en porcentaje y texto blanco.
        chart.dLbls = DataLabelList()
        chart.dLbls.position = "ctr"
        chart.dLbls.numFmt = "0%"
        chart.dLbls.showLegendKey = False
        # Se muestran los valores con formato porcentual, igual que en
        # el reporte oficial. Más abajo se incorporan cachés numéricas
        # para mejorar la compatibilidad con otros renderizadores.
        chart.dLbls.showVal = True
        chart.dLbls.showCatName = False
        chart.dLbls.showSerName = False
        chart.dLbls.showPercent = False
        chart.dLbls.showLeaderLines = False
        chart.dLbls.txPr = RichText(
            bodyPr=RichTextProperties(anchor="ctr"),
            p=[
                Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(
                            sz=1050,
                            solidFill="FFFFFF",
                        )
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )
            ],
        )

        # Tipografía del título, leyenda y ejes según el reporte histórico.
        # El título y la leyenda se reducen al tamaño del reporte
        # oficial para evitar superposición entre ambos elementos.
        chart.title.tx.rich.p[0].pPr.defRPr.sz = 1200
        chart.title.tx.rich.p[0].pPr.defRPr.b = False
        chart.legend.txPr = RichText(
            bodyPr=RichTextProperties(),
            p=[
                Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(sz=900)
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )
            ],
        )
        chart.x_axis.txPr = RichText(
            bodyPr=RichTextProperties(),
            p=[
                Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(sz=900)
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )
            ],
        )
        chart.y_axis.txPr = RichText(
            bodyPr=RichTextProperties(),
            p=[
                Paragraph(
                    pPr=ParagraphProperties(
                        defRPr=CharacterProperties(sz=900)
                    ),
                    endParaRPr=CharacterProperties(lang="es-CL"),
                )
            ],
        )

        # Línea de target en el mismo eje de las columnas. Esto evita el
        # segundo eje vertical que aparecía en la versión anterior.
        target_chart = LineChart()
        target_data = Reference(
            ws,
            min_col=17,
            min_row=1,
            max_row=8,
        )
        target_chart.add_data(target_data, titles_from_data=True)
        target_chart.set_categories(categorias)
        target_chart.series[0].tx = SeriesLabel(v="Target")
        target_chart.series[0].val.numRef.numCache = NumData(
            formatCode="0%",
            ptCount=7,
            pt=[NumVal(idx=indice, v=0.85) for indice in range(7)],
        )
        target_chart.series[0].graphicalProperties.line.solidFill = "4F81BD"
        target_chart.series[0].graphicalProperties.line.prstDash = "dash"
        target_chart.series[0].graphicalProperties.line.width = 22225
        target_chart.series[0].marker.symbol = "none"
        target_chart.x_axis.axId = chart.x_axis.axId
        target_chart.y_axis.axId = chart.y_axis.axId
        target_chart.y_axis.title = None
        target_chart.x_axis.title = None
        target_chart.x_axis.delete = True
        target_chart.y_axis.delete = True

        chart += target_chart

        # El target no aparece en la leyenda del reporte oficial.
        chart.legend.legendEntry = [LegendEntry(idx=2, delete=True)]

        # Área interna del gráfico. Los dos primeros gráficos poseen
        # ajustes ligeramente distintos en el archivo de referencia.
        if clave == "TM1":
            chart.layout = Layout(
                manualLayout=ManualLayout(
                    layoutTarget="inner",
                    xMode="edge",
                    yMode="edge",
                    x=0.0754470505,
                    y=0.2985221576,
                    w=0.9098901360,
                    h=0.5962449842,
                )
            )
        elif clave == "TM2":
            chart.layout = Layout(
                manualLayout=ManualLayout(
                    layoutTarget="inner",
                    xMode="edge",
                    yMode="edge",
                    x=0.0885002013,
                    y=0.2532549190,
                    w=0.9044311103,
                    h=0.6453989123,
                )
            )
        elif clave == "COMBINADO":
            chart.layout = Layout(
                manualLayout=ManualLayout(
                    layoutTarget="inner",
                    xMode="edge",
                    yMode="edge",
                    x=0.100,
                    y=0.2532549190,
                    w=0.885,
                    h=0.6453989123,
                )
            )

        # Anclajes exactos de los tres gráficos visibles del reporte.
        anclajes_quimico = {
            "TM1": (
                AnchorMarker(col=8, colOff=1761016, row=7, rowOff=168004),
                AnchorMarker(col=12, colOff=1074579, row=20, rowOff=125697),
            ),
            "TM2": (
                AnchorMarker(col=8, colOff=1787486, row=21, rowOff=63262),
                AnchorMarker(col=12, colOff=1095969, row=34, rowOff=25940),
            ),
            "COMBINADO": (
                AnchorMarker(col=8, colOff=1798841, row=34, rowOff=96617),
                AnchorMarker(col=12, colOff=1090637, row=47, rowOff=58082),
            ),
        }
        anclajes_fisico = {
            "TM1": (
                AnchorMarker(col=8, colOff=1856513, row=7, rowOff=83409),
                AnchorMarker(col=12, colOff=1238983, row=20, rowOff=96459),
            ),
            "TM2": (
                AnchorMarker(col=8, colOff=1862862, row=21, rowOff=9405),
                AnchorMarker(col=12, colOff=1249142, row=34, rowOff=13565),
            ),
            "COMBINADO": (
                AnchorMarker(col=8, colOff=1860322, row=34, rowOff=118566),
                AnchorMarker(col=12, colOff=1246602, row=47, rowOff=123996),
            ),
        }
        anclajes = (
            anclajes_quimico
            if tipo.lower() == "quimico"
            else anclajes_fisico
        )
        desde, hasta = anclajes[clave]
        chart.anchor = TwoCellAnchor(
            editAs="twoCell",
            _from=desde,
            to=hasta,
        )
        ws.add_chart(chart)

    # ------------------------------------------------------------
    # Detalle turno a turno
    # ------------------------------------------------------------
    ws.merge_cells("C53:M53")
    ws["C53"] = (
        "5.- Detalle turno a turno de mineral apilado, muestras "
        "representativas y estados trazables."
    )
    ws["C53"].font = font_header
    ws["C53"].alignment = left
    _aplicar_subrayado(53, 3, 13)

    ws.merge_cells("G55:I55")
    ws["G55"] = "Torre de muestreo #1"
    ws.merge_cells("J55:L55")
    ws["J55"] = "Torre de muestreo #2"

    for celda in ["G55", "J55"]:
        ws[celda].fill = azul_grupo
        ws[celda].font = font_header
        ws[celda].alignment = center
        ws[celda].border = border_grupo

    headers_detalle = [
        "Semana",
        "Fecha",
        "Pad",
        "Turno",
        "TMH\nCV-08",
        "Muestra representativa CV-08",
        "Comentarios",
        "TMH\nCV-108",
        "Muestra representativa CV-108",
        "Comentarios",
        "Representatividad Turno\n(árbol de decisión)",
    ]

    for col, valor in enumerate(headers_detalle, start=3):
        cell = ws.cell(56, col, valor)
        cell.fill = azul_header
        cell.font = font_header
        cell.alignment = center
        cell.border = border_grupo

    # Tablas auxiliares de auditoría: reemplazan los conteos ocultos y
    # fórmulas COUNTIFS del archivo histórico.
    auditorias = [
        ("TM1", 55, "Auditoría TM1"),
        ("TM2", 66, "Auditoría TM2"),
        ("COMBINADO", 77, "Auditoría TM1 + TM2"),
    ]

    for clave, fila_inicio_auditoria, titulo_auditoria in auditorias:
        ws.merge_cells(
            start_row=fila_inicio_auditoria,
            start_column=15,
            end_row=fila_inicio_auditoria,
            end_column=18,
        )
        ws.cell(fila_inicio_auditoria, 15, titulo_auditoria)
        ws.cell(fila_inicio_auditoria, 15).fill = amarillo
        ws.cell(fila_inicio_auditoria, 15).font = font_header
        ws.cell(fila_inicio_auditoria, 15).alignment = center

        encabezados_auditoria = [
            "Periodo",
            "Turnos activos",
            "Representativos",
            "No representativos",
        ]
        for col, valor in enumerate(encabezados_auditoria, start=15):
            cell = ws.cell(fila_inicio_auditoria + 1, col, valor)
            cell.fill = amarillo
            cell.font = font_header
            cell.alignment = center
            cell.border = border

        for offset, fila_resumen in enumerate(resumen[clave], start=2):
            fila_excel = fila_inicio_auditoria + offset
            valores_auditoria = [
                fila_resumen["Periodo"],
                fila_resumen["Turnos_Activos"],
                fila_resumen["Representativos"],
                fila_resumen["No_Representativos"],
            ]
            for col, valor in enumerate(valores_auditoria, start=15):
                cell = ws.cell(fila_excel, col, valor)
                cell.fill = amarillo
                cell.font = font_normal
                cell.alignment = center
                cell.border = border

            if fila_resumen["Periodo"] == "MTD":
                for col in range(15, 19):
                    ws.cell(fila_excel, col).font = Font(
                        name="Arial",
                        bold=True,
                        color="476475",
                        size=10,
                    )

    fila_datos = 57
    for indice, (_, fila) in enumerate(detalle.iterrows()):
        row_excel = fila_datos + indice

        valores = [
            fila["Semana"],
            fila["Fecha"].to_pydatetime(),
            fila["Pad"],
            fila["Turno"],
            fila["TMH_CV08"] if fila["TM1_Activo"] else None,
            fila["Rep_TM1"] if fila["TM1_Activo"] else None,
            fila["Comentario_TM1"],
            fila["TMH_CV108"] if fila["TM2_Activo"] else None,
            fila["Rep_TM2"] if fila["TM2_Activo"] else None,
            fila["Comentario_TM2"],
            fila["Rep_Turno"],
        ]

        for col, valor in enumerate(valores, start=3):
            cell = ws.cell(row_excel, col, valor)
            cell.font = font_normal
            cell.alignment = center if col not in [9, 12] else left
            cell.border = border

            if indice % 2 == 1:
                cell.fill = azul_alt

        ws.cell(row_excel, 4).number_format = "dd-mm-yyyy"
        ws.cell(row_excel, 7).number_format = "#,##0.0"
        ws.cell(row_excel, 10).number_format = "#,##0.0"

        for col in [8, 11, 13]:
            valor = ws.cell(row_excel, col).value
            _aplicar_semaforo(
                ws.cell(row_excel, col),
                valor,
                center,
            )

        if fila["Pad"] == "Sin clasificar":
            ws.cell(row_excel, 5).fill = gris

    ultima_fila = fila_datos + len(detalle) - 1

    # Bordes del detalle: contorno oscuro, divisiones internas finas y
    # grupos de torres claramente delimitados.
    _aplicar_bordes_tabla(
        56,
        3,
        ultima_fila,
        13,
        borde_exterior=medium,
        borde_interior=thin,
    )
    _aplicar_bordes_tabla(55, 7, 55, 9, borde_exterior=medium)
    _aplicar_bordes_tabla(55, 10, 55, 12, borde_exterior=medium)

    # Cada tabla de auditoría mantiene una grilla completa y un contorno
    # visible para que no quede como un bloque suelto sin terminación.
    for _, fila_inicio_auditoria, _ in auditorias:
        _aplicar_bordes_tabla(
            fila_inicio_auditoria,
            15,
            fila_inicio_auditoria + 8,
            18,
            borde_exterior=thin,
            borde_interior=thin,
        )

    # La nota y el gráfico FY deben quedar después tanto del detalle como
    # de las tres auditorías auxiliares (la última termina en la fila 85).
    nota_fila = max(ultima_fila, 85) + 2

    ws.merge_cells(
        start_row=nota_fila,
        start_column=3,
        end_row=nota_fila + 1,
        end_column=13,
    )
    ws.cell(
        nota_fila,
        3,
        "Nota metodológica: desde el 01-01-2026 la evaluabilidad se "
        "determina mediante Turno_Evaluable por Fecha + Turno. Para el "
        "histórico anterior se conserva la evaluabilidad independiente "
        "por torre informada en BD Ton, con fallback en la existencia del "
        "tonelaje original. Las columnas de comentarios permanecen vacías "
        "mientras no exista una fuente oficial y trazable de causas "
        "operacionales.",
    )
    ws.cell(nota_fila, 3).font = font_nota
    ws.cell(nota_fila, 3).alignment = left

    gestion_fy_normalizada = _normalizar_gestion_fy(
        df_gestion_fy,
        fecha_base,
    )
    if gestion_fy_normalizada.empty:
        raise RuntimeError(
            f"La gestión FY {tipo.lower()} no entregó resultados "
            "para construir el gráfico."
        )

    fila_grafico = nota_fila + 4
    _agregar_grafico_gestion_fy(
        ws=ws,
        df_gestion_fy=gestion_fy_normalizada,
        tipo=tipo,
        fecha_base=fecha_base,
        fila_inicio=fila_grafico,
    )

    ws.auto_filter.ref = f"C56:M{ultima_fila}"
    ws.freeze_panes = None

    # Dimensiones replicadas desde las hojas oficiales. Estas medidas
    # controlan tanto la lectura de las tablas como el tamaño real de los
    # gráficos, porque estos utilizan anclajes de dos celdas.
    if tipo.lower() == "quimico":
        anchos = {
            "A": 4.08203125,
            "B": 1.5,
            "C": 15.08203125,
            "D": 15.5,
            "E": 16.5,
            "F": 15.5,
            "G": 10.08203125,
            "H": 13.5,
            "I": 42.9140625,
            "J": 9.5,
            "K": 13.5,
            "L": 44.0,
            "M": 19.9140625,
            "N": 3.5,
        }
    else:
        anchos = {
            "A": 4.9140625,
            "B": 1.5,
            "C": 12.9140625,
            "D": 15.5,
            "E": 16.5,
            "F": 15.5,
            "G": 9.0,
            "H": 13.5,
            "I": 44.6640625,
            "J": 9.5,
            "K": 13.5,
            "L": 47.08203125,
            "M": 19.9140625,
            "N": 1.5,
        }

    # Las columnas de auditoría quedan fuera del cuerpo principal y con
    # ancho suficiente para que sus encabezados no se recorten.
    anchos.update({
        "O": 15.0,
        "P": 18.0,
        "Q": 18.0,
        "R": 18.0,
    })

    for columna, ancho in anchos.items():
        ws.column_dimensions[columna].width = ancho

    # N funciona como separación visual entre el reporte y la auditoría.
    ws.column_dimensions["N"].hidden = True

    alturas = {
        2: 14.25,
        3: 14.5,
        4: 14.5,
        5: 14.5,
        6: 14.5,
        7: 14.5,
        9: 20.0,
        10: 18.0,
        16: 20.0,
        17: 37.5,
        27: 20.0,
        28: 37.5,
        38: 20.0,
        39: 37.5,
        53: 20.0,
        55: 15.0,
        56: 39.5,
    }
    for fila, altura in alturas.items():
        ws.row_dimensions[fila].height = altura

    # Encabezados de las tablas auxiliares de auditoría.
    for fila in [56, 67, 78]:
        ws.row_dimensions[fila].height = 39.5
    for fila in [55, 66, 77]:
        ws.row_dimensions[fila].height = 18.0

    ws.sheet_view.zoomScale = 85
    ws.sheet_view.zoomScaleNormal = 85

    ws.page_setup.orientation = "landscape"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5

    return nombre_hoja


def _fetch_fuentes_mensuales_torres(fecha_fin) -> dict:
    """
    Consulta las fuentes necesarias para las hojas mensuales RN-046
    (Químico y Físico) del mes evaluado.
    """
    fin_d = pd.to_datetime(fecha_fin).date()
    rango_fy = _obtener_rango_fiscal_hasta_mes(fin_d)

    fecha_inicio_mes = fin_d.replace(day=1)
    fecha_fin_mes = rango_fy["fecha_fin"]
    fecha_fin_mes_exclusiva = (
        pd.Timestamp(fecha_fin_mes) + pd.Timedelta(days=1)
    ).date()

    df_bd_ton_mes = fetch_bd_ton_report(
        start_date=fecha_inicio_mes,
        end_date=fecha_fin_mes,
    )
    if df_bd_ton_mes.empty:
        raise RuntimeError(
            "BD Ton no entregó datos para el mes evaluado."
        )

    try:
        df_turno_mes = fetch_estado_apilado_turno_representatividad(
            start_date=fecha_inicio_mes,
            end_date=fecha_fin_mes_exclusiva,
        )
    except Exception as material_error:
        raise RuntimeError(
            "No fue posible obtener el estado de apilado por turno "
            "necesario para aplicar RN-046."
        ) from material_error

    if df_turno_mes.empty:
        raise RuntimeError(
            "El estado de apilado por turno no entregó datos para el mes "
            "evaluado; no es posible determinar la "
            "evaluabilidad oficial de los turnos."
        )

    df_gestion_fy_quimico = fetch_gestion_representatividad_fy(
        anio_fiscal=rango_fy["anio_fiscal"],
        tipo="QUIMICO",
        alcance="COMBINADO",
        objetivo=0.85,
        fecha_corte=rango_fy["fecha_fin"],
    )
    if df_gestion_fy_quimico.empty:
        raise RuntimeError(
            "La gestión FY química no entregó resultados."
        )

    df_gestion_fy_fisico = fetch_gestion_representatividad_fy(
        anio_fiscal=rango_fy["anio_fiscal"],
        tipo="FISICO",
        alcance="COMBINADO",
        objetivo=0.85,
        fecha_corte=rango_fy["fecha_fin"],
    )
    if df_gestion_fy_fisico.empty:
        raise RuntimeError(
            "La gestión FY física no entregó resultados."
        )

    return {
        "rango_fy": rango_fy,
        "fecha_inicio_mes": fecha_inicio_mes,
        "fecha_fin_mes": fecha_fin_mes,
        "df_bd_ton_mes": df_bd_ton_mes,
        "df_turno_mes": df_turno_mes,
        "df_gestion_fy_quimico": df_gestion_fy_quimico,
        "df_gestion_fy_fisico": df_gestion_fy_fisico,
    }


def _build_xlsx_solo_hojas_mensuales(fuentes: dict) -> tuple[bytes, list[str]]:
    """
    Arma un libro Excel que contiene únicamente las hojas mensuales
    RN-046 (Químico y Físico).
    """
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)

    nombres = _agregar_hojas_mensuales_torres(
        wb=wb,
        df_bd_ton=fuentes["df_bd_ton_mes"],
        df_turno=fuentes["df_turno_mes"],
        df_gestion_fy_quimico=fuentes["df_gestion_fy_quimico"],
        df_gestion_fy_fisico=fuentes["df_gestion_fy_fisico"],
    )

    if len(nombres) < 2:
        raise RuntimeError(
            "No se generaron las hojas mensuales Químico y Físico "
            "para exportar a PDF."
        )

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue(), nombres


def _prefijo_mes_desde_nombres_hojas(nombres: list[str]) -> str:
    """Extrae '01_Ene_26' desde '01_Ene_26 Quimico'."""
    if not nombres:
        return "mes"
    primera = nombres[0]
    if " " in primera:
        return primera.split(" ", 1)[0]
    return primera[:31]


def _agregar_hojas_mensuales_torres(
    wb,
    df_bd_ton: pd.DataFrame,
    df_turno: pd.DataFrame | None = None,
    df_gestion_fy_quimico: pd.DataFrame | None = None,
    df_gestion_fy_fisico: pd.DataFrame | None = None,
) -> list[str]:
    """Crea un par Químico/Físico por cada mes incluido en BD Ton."""
    if df_bd_ton is None or df_bd_ton.empty or "Fecha" not in df_bd_ton.columns:
        return []

    bd = df_bd_ton.copy()
    bd["Fecha"] = pd.to_datetime(bd["Fecha"], errors="coerce").dt.normalize()
    bd = bd[bd["Fecha"].notna()].copy()

    if bd.empty:
        return []

    material_turno = _preparar_material_por_turno(df_turno)
    nombres = []

    for periodo, bd_mes in bd.groupby(bd["Fecha"].dt.to_period("M"), sort=True):
        material_mes = material_turno
        if not material_turno.empty:
            material_mes = material_turno[
                material_turno["Fecha"].dt.to_period("M") == periodo
            ].copy()

        for tipo in ["Quimico", "Fisico"]:
            df_gestion_tipo = (
                df_gestion_fy_quimico
                if tipo == "Quimico"
                else df_gestion_fy_fisico
            )
            nombre = _agregar_hoja_mensual_torres(
                wb=wb,
                df_bd_ton_mes=bd_mes,
                tipo=tipo,
                df_material_turno_mes=material_mes,
                df_gestion_fy=df_gestion_tipo,
            )
            if nombre:
                nombres.append(nombre)

    return nombres


def _export_representatividad_torres_to_excel(
    df: pd.DataFrame,
    df_bd_ton_fy: pd.DataFrame,
    df_bd_ton_mes: pd.DataFrame,
    df_turno_mes: pd.DataFrame | None = None,
    df_gestion_fy_quimico: pd.DataFrame | None = None,
    df_gestion_fy_fisico: pd.DataFrame | None = None,
) -> bytes:
    """
    Exporta el reporte de Representatividad Torres a Excel.

    Las hojas Representatividad Torres y BD Ton utilizan la estética
    del bloque AT:BM de Reporte Diario: fondo blanco, encabezados
    jerárquicos, bordes completos y desplazamiento libre.
    """
    from openpyxl import Workbook
    from openpyxl.styles import (
        Font,
        Alignment,
        PatternFill,
        Border,
        Side,
    )
    from openpyxl.cell.cell import MergedCell

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
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = None

    # Paleta equivalente a Reporte Diario, columnas AT:BM.
    color_header = "D7E1E7"
    color_texto = "476475"
    color_borde = "476475"
    color_borde_interno = "A6A6A6"
    color_subtitulo = "666666"

    fill_blanco = PatternFill("solid", fgColor="FFFFFF")
    fill_header = PatternFill("solid", fgColor=color_header)
    fill_alt = PatternFill("solid", fgColor=color_header)

    font_titulo = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=14,
    )
    font_subtitulo = Font(
        name="Arial",
        italic=True,
        color=color_subtitulo,
        size=9,
    )
    font_header = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=11,
    )
    font_normal = Font(
        name="Arial",
        color=color_texto,
        size=10,
    )
    font_fecha = Font(
        name="Arial",
        bold=True,
        color=color_texto,
        size=10,
    )
    font_bajo = Font(
        name="Arial",
        bold=True,
        color="C00000",
        size=10,
    )
    font_detenido = Font(
        name="Arial",
        italic=True,
        color=color_texto,
        size=10,
    )

    thin = Side(style="thin", color=color_borde_interno)
    thin_header = Side(style="thin", color=color_borde)
    medium = Side(style="medium", color=color_borde)

    border_datos = Border(
        left=thin,
        right=thin,
        top=thin,
        bottom=thin,
    )
    border_header = Border(
        left=thin_header,
        right=thin_header,
        top=thin_header,
        bottom=thin_header,
    )

    center = Alignment(
        horizontal="center",
        vertical="center",
        wrap_text=True,
    )

    def _aplicar_contorno(
        fila_ini: int,
        col_ini: int,
        fila_fin: int,
        col_fin: int,
    ) -> None:
        """Refuerza el contorno del bloque sin perder las líneas internas."""
        for fila in range(fila_ini, fila_fin + 1):
            for col in range(col_ini, col_fin + 1):
                celda = ws.cell(fila, col)
                borde_actual = celda.border
                celda.border = Border(
                    left=medium if col == col_ini else borde_actual.left,
                    right=medium if col == col_fin else borde_actual.right,
                    top=medium if fila == fila_ini else borde_actual.top,
                    bottom=medium if fila == fila_fin else borde_actual.bottom,
                )

    # ------------------------------------------------------------
    # Título y subtítulo
    # ------------------------------------------------------------
    ws.merge_cells("A1:I1")
    ws["A1"] = "Representatividad diaria de torres de muestreo"
    ws["A1"].font = font_titulo
    ws["A1"].alignment = center
    ws["A1"].fill = fill_blanco

    ws.merge_cells("A2:I2")
    ws["A2"] = (
        "Valores expresados en porcentaje. Los valores menores a 75% "
        "se destacan en rojo."
    )
    ws["A2"].font = font_subtitulo
    ws["A2"].alignment = center
    ws["A2"].fill = fill_blanco

    # ------------------------------------------------------------
    # Encabezados jerárquicos
    # ------------------------------------------------------------
    ws.merge_cells("A4:A6")
    ws.merge_cells("B4:E4")
    ws.merge_cells("F4:I4")
    ws.merge_cells("B5:C5")
    ws.merge_cells("D5:E5")
    ws.merge_cells("F5:G5")
    ws.merge_cells("H5:I5")

    ws["A4"] = "Día"
    ws["B4"] = "Representatividad TM1"
    ws["F4"] = "Representatividad TM2"
    ws["B5"] = "Turno A"
    ws["D5"] = "Turno B"
    ws["F5"] = "Turno A"
    ws["H5"] = "Turno B"

    headers_fila_6 = [
        "Químico",
        "Físico",
        "Químico",
        "Físico",
        "Químico",
        "Físico",
        "Químico",
        "Físico",
    ]
    for col, header in enumerate(headers_fila_6, start=2):
        ws.cell(6, col, header)

    for fila in range(4, 7):
        for col in range(1, 10):
            celda = ws.cell(fila, col)
            if isinstance(celda, MergedCell):
                continue
            celda.fill = fill_header
            celda.font = font_header
            celda.alignment = center
            celda.border = border_header

    # ------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------
    fila_inicio = 7

    for fila_excel, (_, fila_df) in enumerate(
        df.iterrows(),
        start=fila_inicio,
    ):
        es_alterna = (fila_excel - fila_inicio) % 2 == 1
        fill_fila = fill_alt if es_alterna else fill_blanco

        fecha = pd.to_datetime(
            fila_df.get("Dia"),
            errors="coerce",
        )
        celda_fecha = ws.cell(fila_excel, 1)
        celda_fecha.value = (
            fecha.to_pydatetime()
            if pd.notna(fecha)
            else None
        )
        celda_fecha.number_format = "dd-mm-yyyy"
        celda_fecha.fill = fill_fila
        celda_fecha.font = font_fecha
        celda_fecha.alignment = center
        celda_fecha.border = border_datos

        for col_excel, nombre_columna in enumerate(
            columnas_pct,
            start=2,
        ):
            celda = ws.cell(fila_excel, col_excel)
            valor = pd.to_numeric(
                fila_df.get(nombre_columna),
                errors="coerce",
            )

            celda.fill = fill_fila
            celda.alignment = center
            celda.border = border_datos

            if pd.isna(valor):
                celda.value = "Tambor detenido"
                celda.font = font_detenido
            else:
                celda.value = float(valor)
                celda.number_format = "0.0%"
                celda.font = (
                    font_bajo
                    if float(valor) < 0.75
                    else font_normal
                )

    ultima_fila = max(fila_inicio + len(df) - 1, fila_inicio)

    # Contornos funcionales: Día, TM1 y TM2.
    for col_ini, col_fin in [
        (1, 1),
        (2, 5),
        (6, 9),
    ]:
        _aplicar_contorno(4, col_ini, ultima_fila, col_fin)

    # Dimensiones equivalentes al bloque AT:BM.
    ws.column_dimensions["A"].width = 15
    for columna in ["B", "C", "D", "E", "F", "G", "H", "I"]:
        ws.column_dimensions[columna].width = 15

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 24
    ws.row_dimensions[6].height = 24
    for fila in range(fila_inicio, ultima_fila + 1):
        ws.row_dimensions[fila].height = 21

    if len(df) > 0:
        ws.auto_filter.ref = f"A6:I{ultima_fila}"

    # Segunda hoja: BD Ton con la misma identidad visual.
    _agregar_hoja_bd_ton(
        wb=wb,
        df_bd_ton=df_bd_ton_fy,
    )

    # Hojas mensuales Químico y Físico: solo el mes evaluado.
    _agregar_hojas_mensuales_torres(
        wb=wb,
        df_bd_ton=df_bd_ton_mes,
        df_turno=df_turno_mes,
        df_gestion_fy_quimico=df_gestion_fy_quimico,
        df_gestion_fy_fisico=df_gestion_fy_fisico,
    )

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

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
    Input({"type": "report-gen-btn", "tipo": ALL}, "n_clicks"),
    State("report-fecha-inicio", "date"),
    State("report-fecha-final", "date"),
    prevent_initial_call=True
)
def generar_reporte(n_clicks_list, f_ini, f_fin):
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update, no_update
    if not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update

    tipo = triggered["tipo"]

    if not f_ini or not f_fin:
        return (
            dbc.Alert("⚠️ Debe seleccionar rango de fechas.", color="warning"),
            html.Div(),
            html.Div(),
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
                dbc.Alert(f"Error al consultar representatividad de torres: {e}", color="danger"),
                html.Div(),
                html.Div(),
            )

        if df_rep.empty:
            return (
                dbc.Alert("Sin datos de representatividad para el rango seleccionado.", color="info"),
                html.Div(),
                html.Div(),
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
                dbc.Alert(f"Error al consultar reporte por turno: {e}", color="danger"),
                html.Div(),
                html.Div(),
            )

        if df_turno.empty:
            return (
                dbc.Alert("Sin datos para el reporte por turno en el rango seleccionado.", color="info"),
                html.Div(),
                html.Div(),
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
        return (
            dbc.Alert("Sin datos en el rango seleccionado.", color="info"),
            html.Div(),
            html.Div(),
        )

    if tipo == "prod":
        ycol = None
        for c in ["Produccion_Catodos_Real", "Producción_Cátodos_Real", "prod_catodos_real"]:
            if c in df.columns:
                ycol = c
                break

        if ycol is None:
            return (
                dbc.Alert("No se encuentra la columna 'Produccion_Catodos_Real' en la tabla.", color="danger"),
                html.Div(),
                html.Div(),
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

    return html.Div(), tabla, historial


@callback(
    Output("report-download-xlsx", "data"),
    Output("report-status", "children", allow_duplicate=True),
    Output("report-progress", "children", allow_duplicate=True),
    Input({"type": "report-export-btn", "tipo": ALL}, "n_clicks"),
    State("report-fecha-inicio", "date"),
    State("report-fecha-final", "date"),
    prevent_initial_call=True,
    running=[
        (
            Output({"type": "report-export-btn", "tipo": MATCH}, "disabled"),
            True,
            False,
        ),
    ],
)
def exportar_excel(n_clicks_list, f_ini, f_fin):
    print("\n=== EXPORTAR EXCEL ACTIVADO ===")
    print("n_clicks_list:", n_clicks_list)
    print("triggered_id:", ctx.triggered_id)
    print("fecha inicio:", f_ini)
    print("fecha final:", f_fin)

    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update, no_update
    if not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update

    tipo = triggered["tipo"]
    _done = html.Div()

    print(f"[EXCEL] tipo={tipo} | ini={f_ini} | fin={f_fin}")

    if not f_ini or not f_fin:
        print("[EXCEL] Sin fechas - abortando")
        return no_update, "Debe seleccionar rango de fechas.", _done

    ini_d = pd.to_datetime(f_ini).date()
    fin_d = pd.to_datetime(f_fin).date()
    # El SP usa fecha final exclusiva: Fecha >= inicio AND Fecha < fin
    fin_sql_exclusivo = (pd.to_datetime(f_fin) + pd.Timedelta(days=1)).date()

    try:
        # ------------------------------------------------------------
        # REPORTE REPRESENTATIVIDAD TORRES
        # ------------------------------------------------------------
        if tipo == "representatividad_torres":
            print("Entró a exportación de Representatividad Torres")
            # Hoja 1: reporte diario de representatividad
            df_rep = fetch_representatividad_torres_report(
                start_date=ini_d,
                end_date=fin_d,
            )
            print("Filas Representatividad:", len(df_rep))
            if df_rep.empty:
                return (
                    no_update,
                    "ℹ️ Sin datos de representatividad para exportar "
                    "en el rango seleccionado.",
                    _done,
                )

            rango_fy = _obtener_rango_fiscal_hasta_mes(fin_d)

            # Hoja BD Ton: histórico del FY hasta el mes evaluado.
            df_bd_ton_fy = fetch_bd_ton_report(
                start_date=rango_fy["fecha_inicio"],
                end_date=rango_fy["fecha_fin"],
            )
            print(
                f"Filas BD Ton FY{rango_fy['anio_fiscal'] % 100:02d}:",
                len(df_bd_ton_fy),
            )
            if df_bd_ton_fy.empty:
                raise RuntimeError(
                    "BD Ton no entregó datos históricos para el año fiscal."
                )

            fuentes_mensuales = _fetch_fuentes_mensuales_torres(fin_d)
            df_bd_ton_mes = fuentes_mensuales["df_bd_ton_mes"]
            df_turno_material = fuentes_mensuales["df_turno_mes"]
            df_gestion_fy_quimico = fuentes_mensuales["df_gestion_fy_quimico"]
            df_gestion_fy_fisico = fuentes_mensuales["df_gestion_fy_fisico"]

            print("Filas BD Ton mes evaluado:", len(df_bd_ton_mes))
            print("Filas Estado de Apilado por Turno:", len(df_turno_material))
            print("Filas Gestión FY Químico:", len(df_gestion_fy_quimico))
            print("Filas Gestión FY Físico:", len(df_gestion_fy_fisico))

            xbytes = _export_representatividad_torres_to_excel(
                df=df_rep,
                df_bd_ton_fy=df_bd_ton_fy,
                df_bd_ton_mes=df_bd_ton_mes,
                df_turno_mes=df_turno_material,
                df_gestion_fy_quimico=df_gestion_fy_quimico,
                df_gestion_fy_fisico=df_gestion_fy_fisico,
            )

            print("Excel generado. Tamaño bytes:", len(xbytes))
            
            filename = (
                f"Reporte_Representatividad_Torres_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )

            status = (
                f"✔️ Exportado: {filename} — "
                f"Representatividad: {len(df_rep)} registros — "
                f"BD Ton FY{rango_fy['anio_fiscal'] % 100:02d}: "
                f"{len(df_bd_ton_fy)} registros — "
                f"Mes evaluado: {len(df_bd_ton_mes)} registros — "
                "Hojas RN-046: Químico y Físico"
            )

            return (
                _enviar_descarga(xbytes, filename),
                status,
                _done,
            )

            
        # ------------------------------------------------------------
        # REPORTE POR TURNO + GENERADOR REPORTE
        # ------------------------------------------------------------
        if tipo == "reporte_turno":
            print(f"[EXCEL] Fetching reporte_turno {ini_d} -> {fin_sql_exclusivo}")
            df_turno = fetch_reporte_turno_cache(start_date=ini_d, end_date=fin_sql_exclusivo)
            print(f"[EXCEL] reporte_turno rows={len(df_turno)}")

            if df_turno.empty:
                return no_update, "Sin datos para el rango seleccionado.", _done

            print(f"[EXCEL] Fetching generador_reporte_diario {ini_d} -> {fin_sql_exclusivo}")
            df_generador = fetch_generador_reporte_diario(start_date=ini_d, end_date=fin_sql_exclusivo)
            print(f"[EXCEL] generador rows={len(df_generador)}")

            output = io.BytesIO()
            export_reporte_turno_estilo_leyes_finos(df=df_turno, output=output, df_generador=df_generador)
            output.seek(0)
            xbytes = output.getvalue()
            print(f"[EXCEL] reporte_turno excel size={len(xbytes)} bytes")

            filename = (
                f"Analisis_Torres_de_Muestreo_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )
            status = f"Exportado: {filename} (turno={len(df_turno)}, generador={len(df_generador)})"
            return _enviar_descarga(xbytes, filename), status, _done

        # ------------------------------------------------------------
        # PRODUCCIÓN DIARIA / DATOS CONCILIADOS
        # ------------------------------------------------------------
        if tipo == "prod":
            df = fetch_datos_conciliados_report(
                start_date=ini_d,
                end_date=fin_d
            )

            if df.empty:
                return no_update, "Sin datos para exportar en el rango seleccionado.", _done

            template_path = _find_plantilla_propuesta()
            if os.path.isfile(template_path):
                xbytes = export_datos_conciliados_to_template(df, template_path)
            else:
                xbytes = _export_dataframe_simple_to_excel(df, sheet_name="Datos Conciliados")

            filename = (
                f"Reporte_DatosConciliados_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
            )

            status = f"Exportado: {filename} — Registros: {len(df)}"
            return _enviar_descarga(xbytes, filename), status, _done

        # ------------------------------------------------------------
        # BALANCE / CONCILIACIÓN U OTROS REPORTES ANTIGUOS
        # ------------------------------------------------------------
        print(f"[EXCEL] Fetching report_data tipo={tipo} end={fin_d}")
        df = fetch_report_data(end_date=fin_d)
        df = df[
            (pd.to_datetime(df["Fecha"]).dt.date >= ini_d) &
            (pd.to_datetime(df["Fecha"]).dt.date <= fin_d)
        ].copy()
        print(f"[EXCEL] report_data rows={len(df)}")

        if df.empty:
            return no_update, "Sin datos para exportar en el rango seleccionado.", _done

        xbytes = export_dataframe_with_template(df, TEMPLATE_XLSX_PATH)
        print(f"[EXCEL] {tipo} excel size={len(xbytes)} bytes")

        filename = (
            f"Reporte_{tipo}_"
            f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
            f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.xlsx"
        )
        return _enviar_descarga(xbytes, filename), f"Exportado: {filename} ({len(df)} registros)", _done

    except Exception as e:
        import traceback
        traceback.print_exc()

        return (
            no_update,
            f"❌ Error al exportar: {e}",
            html.Div(),
        )

# Clear the progress bar once report-grafico updates (covers the generar_reporte callback)
@callback(
    Output("report-progress", "children", allow_duplicate=True),
    Input("report-grafico", "children"),
    prevent_initial_call=True,
)
def _clear_progress_on_viz(_):
    return html.Div()


@callback(
    Output("report-download-pdf", "data"),
    Output("report-status", "children", allow_duplicate=True),
    Output("report-progress", "children", allow_duplicate=True),
    Input({"type": "report-pdf-btn", "tipo": ALL}, "n_clicks"),
    State("report-fecha-inicio", "date"),
    State("report-fecha-final", "date"),
    prevent_initial_call=True,
    running=[
        (
            Output({"type": "report-pdf-btn", "tipo": MATCH}, "disabled"),
            True,
            False,
        ),
    ],
)
def generar_pdf(n_clicks_list, f_ini, f_fin):
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update, no_update, no_update
    if not any(n for n in n_clicks_list if n):
        return no_update, no_update, no_update

    tipo = triggered["tipo"]
    _done = html.Div()

    print(f"[PDF] tipo={tipo} | ini={f_ini} | fin={f_fin}")

    if not f_ini or not f_fin:
        print("[PDF] Sin fechas - abortando")
        return no_update, "Debe seleccionar rango de fechas.", _done

    ini_d = pd.to_datetime(f_ini).date()
    fin_d = pd.to_datetime(f_fin).date()
    fin_sql_exclusivo = (pd.to_datetime(f_fin) + pd.Timedelta(days=1)).date()

    try:
        # ── REPRESENTATIVIDAD TORRES ──────────────────────────────────
        if tipo == "representatividad_torres":
            print(f"[PDF] Generando PDF mensual RN-046 {ini_d} -> {fin_d}")
            fuentes_mensuales = _fetch_fuentes_mensuales_torres(fin_d)
            xlsx_bytes, nombres_hojas = _build_xlsx_solo_hojas_mensuales(
                fuentes_mensuales
            )
            print(f"[PDF] Hojas mensuales: {nombres_hojas}")
            pdf_bytes = convert_xlsx_bytes_to_pdf(xlsx_bytes)
            print(f"[PDF] representatividad_torres pdf size={len(pdf_bytes)} bytes")
            prefijo_mes = _prefijo_mes_desde_nombres_hojas(nombres_hojas)
            filename = f"Representatividad_Torres_RN046_{prefijo_mes}.pdf"
            hojas_txt = ", ".join(nombres_hojas)
            return (
                _enviar_descarga(pdf_bytes, filename),
                f"PDF generado: {filename} — Hojas: {hojas_txt}",
                _done,
            )

        # ── REPORTE POR TURNO ─────────────────────────────────────────
        if tipo == "reporte_turno":
            print(f"[PDF] Fetching reporte_turno {ini_d} -> {fin_sql_exclusivo}")
            df = fetch_reporte_turno_cache(start_date=ini_d, end_date=fin_sql_exclusivo)
            print(f"[PDF] reporte_turno rows={len(df)}")
            if df.empty:
                return no_update, "Sin datos para el rango seleccionado.", _done

            pdf_bytes = generar_pdf_reporte_turno(df, f_ini, f_fin)
            print(f"[PDF] reporte_turno pdf size={len(pdf_bytes)} bytes")
            filename = (
                f"Analisis_Torres_Turno_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.pdf"
            )
            return _enviar_descarga(pdf_bytes, filename), f"PDF generado: {filename} ({len(df)} registros)", _done

        # ── PRODUCCIÓN DIARIA / DATOS CONCILIADOS ─────────────────────
        if tipo == "prod":
            print(f"[PDF] Fetching datos_conciliados {ini_d} -> {fin_d}")
            df = fetch_datos_conciliados_report(start_date=ini_d, end_date=fin_d)
            print(f"[PDF] datos_conciliados rows={len(df)}")
            if df.empty:
                return no_update, "Sin datos para generar PDF.", _done

            pdf_bytes = generar_pdf_datos_conciliados(df, f_ini, f_fin)
            print(f"[PDF] prod pdf size={len(pdf_bytes)} bytes")
            filename = (
                f"Produccion_Diaria_"
                f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
                f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.pdf"
            )
            return _enviar_descarga(pdf_bytes, filename), f"PDF generado: {filename} ({len(df)} registros)", _done

        # ── BALANCE / CONCILIACIÓN ────────────────────────────────────
        print(f"[PDF] Fetching report_data tipo={tipo} end={fin_d}")
        df = fetch_report_data(end_date=fin_d)
        df = df[
            (pd.to_datetime(df["Fecha"]).dt.date >= ini_d) &
            (pd.to_datetime(df["Fecha"]).dt.date <= fin_d)
        ].copy()
        print(f"[PDF] report_data rows={len(df)}")

        if df.empty:
            return no_update, "Sin datos para generar PDF.", _done

        pdf_bytes = generar_pdf_datos_conciliados(df, f_ini, f_fin)
        print(f"[PDF] {tipo} pdf size={len(pdf_bytes)} bytes")
        filename = (
            f"Reporte_{tipo}_"
            f"{pd.to_datetime(f_ini).strftime('%Y%m%d')}_"
            f"{pd.to_datetime(f_fin).strftime('%Y%m%d')}.pdf"
        )
        return _enviar_descarga(pdf_bytes, filename), f"PDF generado: {filename} ({len(df)} registros)", _done

    except Exception as e:
        import traceback
        print(f"[PDF ERROR] tipo={tipo}: {e}")
        traceback.print_exc()
        return no_update, f"Error al generar PDF ({tipo}): {e}", _done
