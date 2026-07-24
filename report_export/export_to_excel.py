# Auto-generated on 2025-10-27 18:21:09. Edit as needed.
import copy as copy_module
import io
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment
# Rango por defecto de la plantilla antigua de Datos conciliados.
# La plantilla vigente se detecta dinamicamente desde el encabezado "Dia".
PLANTILLA_DATOS_START_ROW = 16
PLANTILLA_DATOS_START_COL = 3   # C
PLANTILLA_DATOS_NUM_COLS = 43   # C a AS
PLANTILLA_DATOS_CLEAR_ROWS = 2000  # filas a limpiar para no dejar datos viejos

# Filas de la plantilla usadas como referencia de estilo (alternancia de color)
PLANTILLA_ESTILO_ROW_A = 16
PLANTILLA_ESTILO_ROW_B = 17

# Bordes del marco por defecto para la plantilla antigua.
PLANTILLA_BORDE_IZQ_COL = 2   # B
PLANTILLA_BORDE_DER_COL = 45   # AS
PLANTILLA_BORDE_DER2_COL = 46  # AT
# Fila de la plantilla con el estilo de "cierre" (línea bajo la tabla)
PLANTILLA_FILA_CIERRE = 17

# Columnas Avance: en Excel, si valor > 1 se escribe valor/100; si está entre 0 y 1 se deja igual
COLUMNAS_AVANCE_DIVIDE_100 = ("Avance_apilado", "Avance_reclamo_oxidos", "Avance_reclamo_sulfuros")


def _detectar_layout_datos_conciliados(ws, num_cols: int) -> dict:
    """
    Detecta la zona de datos en plantillas antiguas y nuevas.

    La cabecera de la tabla tiene "Dia"/"Día" en la columna C; los datos
    comienzan en la fila siguiente al ultimo nivel de encabezado.
    """
    start_col = PLANTILLA_DATOS_START_COL
    header_row = None
    for row_idx in range(1, min(ws.max_row or 0, 80) + 1):
        value = ws.cell(row=row_idx, column=start_col).value
        normalized = str(value or "").strip().lower().replace("í", "i")
        if normalized == "dia":
            header_row = row_idx
            break

    if header_row is None:
        start_row = PLANTILLA_DATOS_START_ROW
    else:
        # Las plantillas usan 3 filas de encabezado: grupo, subgrupo y columna.
        start_row = header_row + 3

    data_last_col = start_col + max(num_cols, 1) - 1
    return {
        "start_row": start_row,
        "start_col": start_col,
        "num_cols": num_cols,
        "style_row_a": start_row,
        "style_row_b": start_row + 1,
        "border_left_col": start_col - 1,
        "border_right_col": data_last_col,
        "border_right2_col": data_last_col + 1,
    }


def _copy_cell_style(dest_cell, src_cell):
    """Copia relleno, borde, fuente y alineación de src_cell a dest_cell."""
    if src_cell.fill:
        dest_cell.fill = src_cell.fill.copy()
    if src_cell.border:
        dest_cell.border = src_cell.border.copy()
    if src_cell.font:
        dest_cell.font = src_cell.font.copy()
    if src_cell.alignment:
        dest_cell.alignment = src_cell.alignment.copy()
    if src_cell.number_format is not None:
        dest_cell.number_format = src_cell.number_format


def _load_template(template_path: str):
    """Carga una plantilla sin conservar metadatos externos incompatibles.

    La plantilla de Datos Conciliados heredó miles de nombres definidos y
    vínculos a otros libros. No son utilizados por las fórmulas del reporte y
    Excel intenta repararlos cada vez que abre el archivo exportado.
    """
    wb = load_workbook(template_path, keep_links=False)
    wb.defined_names.clear()
    # openpyxl separa los nombres con localSheetId en cada Worksheet. Limpiar
    # solo wb.defined_names deja esos #REF! dentro de workbook.xml.
    for ws in wb.worksheets:
        ws.defined_names.clear()
    return wb


def _find_template_closing_row(ws, start_row: int, left_col: int) -> int:
    """Ubica la fila de cierre original (borde inferior grueso)."""
    for row_idx in range(start_row + 1, (ws.max_row or start_row) + 1):
        if ws.cell(row=row_idx, column=left_col).border.bottom.style in {
            "medium", "thick", "double"
        }:
            return row_idx
    return start_row + 31

def _match_template_headers(ws):
    headers = []
    max_col = ws.max_column or 0
    for col_idx in range(1, max_col + 1):
        val = ws.cell(row=1, column=col_idx).value
        headers.append(str(val).strip() if val is not None else "")
    while headers and headers[-1] == "":
        headers.pop()
    return headers

def _write_dataframe(ws, df: pd.DataFrame, start_row: int, start_col: int):
    # headers
    for j, col in enumerate(df.columns, start=start_col):
        cell = ws.cell(row=start_row, column=j, value=col)
        cell.alignment = Alignment(vertical="center")
    # data
    for i, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
        for j, col in enumerate(df.columns, start=start_col):
            ws.cell(row=i, column=j, value=row[col])

def export_dataframe_with_template(df: pd.DataFrame, template_path: str) -> bytes:
    wb = _load_template(template_path)
    ws = wb.active

    headers = _match_template_headers(ws)
    display_df = df.copy()

    print(f"display_df {display_df}")
    if "es_preliminar" in display_df.columns:
        visible_cols = [c for c in display_df.columns if c != "es_preliminar"]
        if visible_cols:
            first_col = visible_cols[0]
            display_df[first_col] = display_df.apply(
                lambda r: (f"* {r[first_col]}" if r.get("es_preliminar", False) else r[first_col]), axis=1
            )

    if headers:
        cols_in_template = [h for h in headers if h in display_df.columns]
        if cols_in_template:
            data_block = display_df[cols_in_template]
            start_row, start_col = 20, 3
            # clear existing area (simple)
            for i in range(start_row, start_row + len(data_block) + 2000):
                for j in range(start_col, start_col + len(cols_in_template)):
                    ws.cell(row=i, column=j, value=None)
            for i, (_, row) in enumerate(data_block.iterrows(), start=start_row):
                for j, col in enumerate(cols_in_template, start=start_col):
                    ws.cell(row=i, column=j, value=row[col])
        else:
            _write_dataframe(ws, display_df, start_row=20, start_col=3)
    else:
        _write_dataframe(ws, display_df, start_row=20, start_col=3)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def export_datos_conciliados_to_template(df: pd.DataFrame, template_path: str) -> bytes:
    """
    Escribe los datos del reporte 'Datos conciliados' en la plantilla Excel.
    - Datos desde el inicio de la tabla detectado en la plantilla.
    - Se escriben todas las columnas recibidas por el reporte.
    - Se copia el estilo (relleno, borde, fuente) de las dos primeras filas a todas
      las filas de datos para que la tabla crezca sin romper la estructura.
    """
    wb = _load_template(template_path)
    ws = wb.active
    layout = _detectar_layout_datos_conciliados(ws, len(df.columns))
    start_row = layout["start_row"]
    start_col = layout["start_col"]
    num_cols = layout["num_cols"]
    style_row_a = layout["style_row_a"]
    style_row_b = layout["style_row_b"]
    border_left_col = layout["border_left_col"]
    border_right2_col = layout["border_right2_col"]

    last_row = start_row + len(df) - 1
    # El marco debe cerrarse inmediatamente después del último dato. Antes se
    # usaba +2 y quedaba una fila vacía con bordes en medio de la tabla.
    closing_row = max(start_row, last_row + 1)
    template_closing_row = _find_template_closing_row(ws, start_row, border_left_col)
    blank_style_row = template_closing_row + 1
    # Guardar los estilos antes de escribir: si el reporte supera la capacidad
    # original de la plantilla, esas mismas filas pasan a contener datos.
    closing_styles = {
        c: copy_module.copy(ws.cell(template_closing_row, c)._style)
        for c in range(border_left_col, border_right2_col + 1)
    }
    blank_styles = {
        c: copy_module.copy(ws.cell(blank_style_row, c)._style)
        for c in range(border_left_col, border_right2_col + 1)
    }

    # Limpiar únicamente celdas que ya existen en la plantilla. Recorrer 2000
    # filas con ws.cell() creaba celdas/estilos innecesarios y alteraba el XLSX.
    clear_to_row = max(template_closing_row, last_row)
    for r in range(start_row, clear_to_row + 1):
        for c in range(start_col, start_col + num_cols):
            ws.cell(row=r, column=c, value=None)

    # Escribir datos fila a fila. La primera fila del template tiene bordes de
    # apertura; las restantes deben usar siempre el estilo regular de la segunda
    # fila. Alternarlas repetía bordes de apertura dentro de la tabla.
    cols = list(df.columns)[:num_cols]
    for i, (_, row) in enumerate(df.iterrows()):
        excel_row = start_row + i
        ref_row = style_row_a if i == 0 else style_row_b
        for j, col in enumerate(cols):
            val = row[col]
            # Columna de estado: 1 -> vacío, 0 o NULL -> "*"
            if col == "Estado":
                if pd.isna(val) or val in (0, 0.0, "0", "0.0"):
                    val = "*"
                elif val in (1, 1.0, "1"):
                    val = None
            elif col in COLUMNAS_AVANCE_DIVIDE_100 and not pd.isna(val):
                try:
                    v = float(val)
                    val = (v / 100.0) if v > 1 else v
                except (TypeError, ValueError):
                    pass
            elif pd.isna(val):
                val = None
            elif col == "Fecha" and hasattr(val, "strftime"):
                val = val.strftime("%d-%m-%Y") if hasattr(val, "strftime") else val
            col_idx = start_col + j
            cell = ws.cell(row=excel_row, column=col_idx, value=val)
            # Todas las columnas (incluida Estado) usan el formato de la plantilla en esa columna
            src = ws.cell(row=ref_row, column=col_idx)
            _copy_cell_style(cell, src)

    # Copiar el marco lateral original en las filas de datos, sin fabricar
    # bordes nuevos ni alterar los bordes internos del template.
    for i in range(len(df)):
        row_idx = start_row + i
        ref_row = style_row_a if i == 0 else style_row_b
        _copy_cell_style(ws.cell(row=row_idx, column=border_left_col),
                         ws.cell(row=ref_row, column=border_left_col))
        _copy_cell_style(ws.cell(row=row_idx, column=border_right2_col),
                         ws.cell(row=ref_row, column=border_right2_col))

    # Mover la fila de cierre original completa justo debajo de los datos.
    for c in range(border_left_col, border_right2_col + 1):
        dest = ws.cell(row=closing_row, column=c)
        dest.value = None
        dest._style = copy_module.copy(closing_styles[c])

    # Borrar el formato residual de la antigua extensión de la tabla. Se usa
    # como referencia la primera fila realmente vacía debajo del marco original.
    for r in range(closing_row + 1, template_closing_row + 1):
        for c in range(border_left_col, border_right2_col + 1):
            cell = ws.cell(row=r, column=c)
            cell.value = None
            cell._style = copy_module.copy(blank_styles[c])

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
