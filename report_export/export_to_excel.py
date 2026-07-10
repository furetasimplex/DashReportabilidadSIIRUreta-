# Auto-generated on 2025-10-27 18:21:09. Edit as needed.
import copy as copy_module
import io
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, PatternFill, Side
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
    wb = load_workbook(template_path)
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
    wb = load_workbook(template_path)
    ws = wb.active
    layout = _detectar_layout_datos_conciliados(ws, len(df.columns))
    start_row = layout["start_row"]
    start_col = layout["start_col"]
    num_cols = layout["num_cols"]
    style_row_a = layout["style_row_a"]
    style_row_b = layout["style_row_b"]
    border_left_col = layout["border_left_col"]
    border_right_col = layout["border_right_col"]
    border_right2_col = layout["border_right2_col"]

    last_row = start_row + len(df) - 1
    closing_row = last_row + 2
    # Limpiar solo valores en la zona de datos; no tocar la fila del borde grueso ni la de arriba
    for r in range(start_row, start_row + PLANTILLA_DATOS_CLEAR_ROWS):
        if r >= closing_row - 1 and r <= closing_row:
            continue
        for c in range(start_col, start_col + num_cols):
            ws.cell(row=r, column=c, value=None)

    # Escribir datos fila a fila y copiar estilo de filas 16/17 (alternancia)
    cols = list(df.columns)[:num_cols]
    for i, (_, row) in enumerate(df.iterrows()):
        excel_row = start_row + i
        # Alternar estilo entre las dos primeras filas de datos para mantener el rayado de la tabla
        ref_row = style_row_b if (i % 2) else style_row_a
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

    ref_style_row = style_row_a

    # Extender bordes gruesos izquierdo (B) y derechos (AS, AT) hasta dos filas debajo de los datos (closing_row)
    for r in range(start_row, closing_row + 1):
        _copy_cell_style(ws.cell(row=r, column=border_left_col), ws.cell(row=ref_style_row, column=border_left_col))
        _copy_cell_style(ws.cell(row=r, column=border_right_col), ws.cell(row=ref_style_row, column=border_right_col))
        _copy_cell_style(ws.cell(row=r, column=border_right2_col), ws.cell(row=ref_style_row, column=border_right2_col))

    # Borde normal izquierdo en C y derecho en la ultima columna solo hasta la última fila con datos
    borde_normal = Side(style="thin", color="000000")
    for r in range(start_row, last_row +1):
        cell_c = ws.cell(row=r, column=start_col)
        bc = cell_c.border
        cell_c.border = Border(
            left=borde_normal,
            right=copy_module.copy(bc.right) if bc and bc.right else None,
            top=copy_module.copy(bc.top) if bc and bc.top else None,
            bottom=copy_module.copy(bc.bottom) if bc and bc.bottom else None,
            diagonal=copy_module.copy(bc.diagonal) if bc and bc.diagonal else None,
            diagonal_direction=bc.diagonal_direction if bc else None,
            vertical=copy_module.copy(bc.vertical) if bc and bc.vertical else None,
            horizontal=copy_module.copy(bc.horizontal) if bc and bc.horizontal else None,
        )
        cell_as = ws.cell(row=r, column=border_right_col)
        bas = cell_as.border
        cell_as.border = Border(
            left=copy_module.copy(bas.left) if bas and bas.left else None,
            right=borde_normal,
            top=copy_module.copy(bas.top) if bas and bas.top else None,
            bottom=copy_module.copy(bas.bottom) if bas and bas.bottom else None,
            diagonal=copy_module.copy(bas.diagonal) if bas and bas.diagonal else None,
            diagonal_direction=bas.diagonal_direction if bas else None,
            vertical=copy_module.copy(bas.vertical) if bas and bas.vertical else None,
            horizontal=copy_module.copy(bas.horizontal) if bas and bas.horizontal else None,
        )

    # Crear borde grueso de cierre explícito (sin copiar F1): de B a AT en closing_row
    borde_grueso = Side(style="medium", color="000000")
    relleno_blanco = PatternFill(fill_type="solid", fgColor="FFFFFF")
    for c in range(border_left_col, border_right2_col + 1):
        cell = ws.cell(row=closing_row, column=c)
        cell.value = None
        cell.fill = relleno_blanco
        left_side = borde_grueso if c == border_left_col else None
        right_side = borde_grueso if c == border_right2_col else None
        cell.border = Border(
            left=left_side,
            right=right_side,
            top=None,
            bottom=borde_grueso,
            diagonal=None,
            diagonal_direction=None,
            vertical=None,
            horizontal=None,
        )

    # Limpiar solo debajo del borde grueso; no limpiar arriba. No tocar los bordes externos.
    sin_borde = Border(left=None, right=None, top=None, bottom=None)
    relleno_blanco = PatternFill(fill_type="solid", fgColor="FFFFFF")
    for fila in range(closing_row + 1, closing_row + 201):
        for c in range(start_col, border_right_col + 1):
            cell = ws.cell(row=fila, column=c)
            cell.border = sin_borde
            cell.fill = relleno_blanco
            cell.value = None

    # Cerrar la última fila con datos con un borde inferior visible (negro, fino).
    borde_inferior_normal = Side(style="thin", color="000000")
    for c in range(start_col, border_right_col + 1):
        cell = ws.cell(row=last_row, column=c)
        bc = cell.border
        cell.border = Border(
            left=copy_module.copy(bc.left) if bc and bc.left else None,
            right=copy_module.copy(bc.right) if bc and bc.right else None,
            top=copy_module.copy(bc.top) if bc and bc.top else None,
            bottom=borde_inferior_normal,
            diagonal=copy_module.copy(bc.diagonal) if bc and bc.diagonal else None,
            diagonal_direction=bc.diagonal_direction if bc else None,
            vertical=copy_module.copy(bc.vertical) if bc and bc.vertical else None,
            horizontal=copy_module.copy(bc.horizontal) if bc and bc.horizontal else None,
        )

    # Cerrar esquina inferior derecha con borde derecho e inferior.
    cell_esquina = ws.cell(row=last_row, column=border_right_col)
    be = cell_esquina.border
    cell_esquina.border = Border(
        left=copy_module.copy(be.left) if be and be.left else None,
        right=borde_normal,
        top=copy_module.copy(be.top) if be and be.top else None,
        bottom=borde_inferior_normal,
        diagonal=copy_module.copy(be.diagonal) if be and be.diagonal else None,
        diagonal_direction=be.diagonal_direction if be else None,
        vertical=copy_module.copy(be.vertical) if be and be.vertical else None,
        horizontal=copy_module.copy(be.horizontal) if be and be.horizontal else None,
    )

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
