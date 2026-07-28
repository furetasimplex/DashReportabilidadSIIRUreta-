# Auto-generated on 2025-10-27 18:21:09. Edit as needed.
import copy as copy_module
import calendar
import io
import re
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
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
MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

# Campos operacionales usados para determinar hasta qué día existen datos
# efectivos. Se excluyen planes, campañas y módulos, que pueden venir cargados
# para fechas futuras aunque todavía no exista producción real.
COLUMNAS_FECHA_ACTUALIZACION = (
    "Chancado_TMS_Real",
    "Humedad_Turno_A",
    "Humedad_Turno_B",
    "Humedad_promedio_dia",
    "Sal_turno_A",
    "Sal_Turno_B",
    "Sal_promedio_dia",
    "SRR_TMS_Turno_A",
    "SRR_TMS_Turno_B",
    "SRR_TMS_promedio_dia",
    "Ley_CuT_Real_srr",
    "Apilado_TMH_turno_A",
    "Apilado_TMH_turno_B",
    "Apilado_TMH_promedio_dia",
    "Apilado_TMS_Real",
    "Ley_CuT_Real",
    "Cobre_fino_Apilado_Real",
    "TMS_Rotopala_1_Real",
    "TMS_Rotopala_2_Real",
    "Camiones_TMS_Reclamo_Oxidos",
    "Camiones_TMS_Reclamo_Sulfuros",
    "Movido",
    "Extraido",
    "Camiones_TMS_total",
    "Total_Ripios_Incluye_Camiones_Real",
    "Produccion_Catodos_Real",
)

MERGES_DATOS_CONCILIADOS = (
    "E12:F12", "Z6:AA6", "E19:G19", "Q19:S19", "O19:P19",
    "P10:Q10", "AA19:AB19", "Z3:AE3", "AU19:AV19", "AM19:AT19",
    "K19:N19", "Z7:AA7", "Z16:AA16", "AC18:AV18", "H19:J19",
    "AH19:AL19", "P11:Q11", "Y19:Z19", "C18:C20", "AG3:AU3",
    "Z12:AA12", "D18:D19", "E11:F11", "AC19:AG19", "Z5:AA5",
    "Z14:AA14", "Z13:AA13", "E18:AB18", "Z15:AA15",
    "T19:X19", "AW18:AX19", "Z9:AA9",
)

ANCHOS_DATOS_CONCILIADOS = {
    "B": 7.94921875,
    "C": 13.234375,
    "D": 13.09375,
    **{get_column_letter(c): 9.80859375 for c in range(5, 8)},   # E:G
    "H": 11.140625,
    "I": 18.234375,
    **{get_column_letter(c): 9.80859375 for c in range(10, 17)},  # J:P
    "Q": 16.6640625,
    "R": 14.80859375,
    "S": 14.80859375,
    **{get_column_letter(c): 9.80859375 for c in range(20, 39)},  # T:AL
    "AM": 10.90234375,
    "AN": 10.90234375,
    **{get_column_letter(c): 9.80859375 for c in range(41, 51)},  # AO:AX
    "AY": 2.80859375,
}

ALTURAS_DATOS_CONCILIADOS = {
    2: 13.2, 3: 15.9, 4: 16.2, 5: 15.9,
    6: 15.75, 7: 15.75, 8: 15.75, 9: 15,
    10: 15, 11: 15, 12: 15.75, 13: 15.75,
    14: 15.75, 15: 15.6, 16: 15.9, 17: 14.4,
    18: 24.75, 19: 30, 20: 14.1,
}

FUENTE_FECHA_CONCILIADO = Font(
    name="Arial", size=11, color="FF476475", family=2,
)
FUENTE_DATO_CONCILIADO = Font(
    name="Arial", size=10, color="FF476475", family=2,
)
ALINEACION_DATO_CONCILIADO = Alignment(horizontal="center", vertical="center")
RELLENO_BANDA_AZUL = PatternFill("solid", fgColor="FFD7E1E7")
RELLENO_BANDA_BLANCA = PatternFill("solid", fgColor="FFFFFFFF")
LADO_FINO_GRUPO = Side(style="thin", color="FF000000")
LADO_VACIO = Side(style=None)
COLUMNAS_BORDE_DERECHO = {
    4, 7, 10, 14, 16, 19, 24, 26, 28, 33, 38, 46, 48, 50,
}


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


def obtener_fecha_actualizacion(df: pd.DataFrame):
    """Obtiene la última fecha con información operacional real y válida."""
    if "Fecha" in df.columns and not df.empty:
        columnas_reales = [c for c in COLUMNAS_FECHA_ACTUALIZACION if c in df.columns]
        con_datos = df
        if columnas_reales:
            valores = df[columnas_reales].apply(pd.to_numeric, errors="coerce")
            con_datos = df[(valores.notna() & valores.ne(0)).any(axis=1)]
        fechas = pd.to_datetime(con_datos["Fecha"], errors="coerce").dropna()
        if not fechas.empty:
            return fechas.max().to_pydatetime()
    return None


def calcular_periodo_mtd(fecha_actualizacion):
    """Devuelve el período MTD inclusivo controlado por una única fecha."""
    if fecha_actualizacion is None:
        return None, None
    fecha_fin = pd.Timestamp(fecha_actualizacion).normalize()
    return fecha_fin.replace(day=1), fecha_fin


def _suma_mtd(datos: pd.DataFrame, columna: str):
    if columna not in datos.columns:
        return None
    valores = pd.to_numeric(datos[columna], errors="coerce")
    if not valores.notna().any():
        return None
    return float(valores.sum(skipna=True))


def _resultado_mtd(real, plan):
    diferencia = None if real is None or plan is None else real - plan
    varianza = (
        None
        if real is None or plan is None or plan == 0
        else (real - plan) / plan
    )
    return {
        "real": real,
        "plan": plan,
        "varianza": varianza,
        "diferencia": diferencia,
    }


def calcular_resumen_mtd(df: pd.DataFrame, fecha_actualizacion) -> dict:
    """Replica las fórmulas oficiales del resumen MTD usando nombres técnicos."""
    fecha_inicio, fecha_fin = calcular_periodo_mtd(fecha_actualizacion)
    if fecha_inicio is None:
        return {
            indicador: _resultado_mtd(None, None)
            for indicador in (
                "Apilado", "Ley", "Cobre Fino Apilado", "SRR",
                "Rotopala", "Total Camiones", "Total Ripios", "Producción",
            )
        }

    fechas = pd.to_datetime(df["Fecha"], errors="coerce").dt.normalize()
    datos = df[(fechas >= fecha_inicio) & (fechas <= fecha_fin)].copy()

    apilado_real = _suma_mtd(datos, "Apilado_TMS_Real")
    apilado_plan = _suma_mtd(datos, "Apilado_TMS_Plan")
    cobre_real = _suma_mtd(datos, "Cobre_fino_Apilado_Real")

    ley_real = (
        None
        if cobre_real is None or apilado_real in (None, 0)
        else cobre_real / apilado_real * 100
    )
    plan_ton = pd.to_numeric(datos.get("Apilado_TMS_Plan"), errors="coerce")
    plan_ley = pd.to_numeric(datos.get("Ley_CuT_Plan"), errors="coerce")
    ley_plan = None
    if plan_ton is not None and plan_ley is not None and plan_ton.notna().any():
        denominador_plan = float(plan_ton.sum(skipna=True))
        if denominador_plan != 0:
            ley_plan = float((plan_ton * plan_ley).sum(skipna=True)) / denominador_plan
    cobre_plan = (
        None
        if ley_plan is None or apilado_plan is None
        else ley_plan * apilado_plan / 100
    )

    total_camiones_real = _suma_mtd(datos, "Camiones_TMS_total")
    total_camiones_plan = _suma_mtd(datos, "Camiones_TMS_plan")
    total_ripios_real = _suma_mtd(datos, "Total_Ripios_Incluye_Camiones_Real")
    total_ripios_plan = _suma_mtd(datos, "Total_Ripios_Incluye_Camiones_Plan")
    rotopala_real = (
        None
        if total_ripios_real is None or total_camiones_real is None
        else total_ripios_real - total_camiones_real
    )
    rotopala_plan = (
        None
        if total_ripios_plan is None or total_camiones_plan is None
        else total_ripios_plan - total_camiones_plan
    )

    return {
        "Apilado": _resultado_mtd(apilado_real, apilado_plan),
        "Ley": _resultado_mtd(ley_real, ley_plan),
        "Cobre Fino Apilado": _resultado_mtd(cobre_real, cobre_plan),
        "SRR": _resultado_mtd(
            _suma_mtd(datos, "SRR_TMS_promedio_dia"),
            _suma_mtd(datos, "SRR_TMS_Plan"),
        ),
        "Rotopala": _resultado_mtd(rotopala_real, rotopala_plan),
        "Total Camiones": _resultado_mtd(total_camiones_real, total_camiones_plan),
        "Total Ripios": _resultado_mtd(total_ripios_real, total_ripios_plan),
        "Producción": _resultado_mtd(
            _suma_mtd(datos, "Produccion_Catodos_Real"),
            _suma_mtd(datos, "Produccion_Catodos_Plan"),
        ),
    }


FILAS_RESUMEN_MTD = {
    "Apilado": 5,
    "Ley": 6,
    "Cobre Fino Apilado": 7,
    "SRR": 8,
    "Rotopala": 9,
    "Total Camiones": 14,
    "Total Ripios": 15,
    "Producción": 16,
}


def escribir_resumen_mtd(ws, resumen_mtd: dict, fecha_actualizacion) -> None:
    """Escribe números (no texto) en la tabla MTD conservando su presentación."""
    if fecha_actualizacion is None:
        ws["Z3"] = "MTD"
    else:
        fecha = pd.Timestamp(fecha_actualizacion)
        ws["Z3"] = f"MTD {MESES_ES[fecha.month - 1]} {fecha.year}"
    for indicador, row in FILAS_RESUMEN_MTD.items():
        resultado = resumen_mtd[indicador]
        for col, clave in zip(("AB", "AC", "AD", "AE"), (
            "real", "plan", "varianza", "diferencia",
        )):
            valor = resultado[clave]
            ws[f"{col}{row}"] = None if pd.isna(valor) else float(valor)


def _actualizar_encabezado_datos_conciliados(ws, df: pd.DataFrame):
    """Actualiza los metadatos desde la misma fecha usada por el resumen MTD."""
    fecha_reporte = obtener_fecha_actualizacion(df)
    if fecha_reporte is None:
        ws["I3"] = None
        ws["I4"] = None
        ws["I5"] = None
        ws["Z3"] = "MTD"
        return None

    anio_fiscal = fecha_reporte.year + (1 if fecha_reporte.month >= 7 else 0)
    ws["C3"] = "Reporte Diario Datos Conciliados"
    ws["C4"] = "Superintendencia Medición y Reconciliación"
    ws["C5"] = "Minera Spence S.A."
    ws["G3"] = "Mes"
    ws["G4"] = "Año"
    ws["G5"] = "Fecha actualización"
    ws["I3"] = MESES_ES[fecha_reporte.month - 1]
    ws["I4"] = f"FY{anio_fiscal % 100:02d}"
    ws["I5"] = fecha_reporte
    ws["I5"].number_format = "dd-mm-yyyy"
    ws["Z3"] = f"MTD {MESES_ES[fecha_reporte.month - 1]} {fecha_reporte.year}"
    return fecha_reporte


def aplicar_borde_inferior_reporte(
    ws,
    fila_inicio_datos: int,
    fila_fin_mes: int,
    columna_inicio: int,
    columna_fin: int,
) -> None:
    """Cierra la última fila calendario conservando separadores verticales."""
    if fila_fin_mes < fila_inicio_datos:
        return
    cache = {}
    for col in range(columna_inicio, columna_fin + 1):
        cell = ws.cell(fila_fin_mes, col)
        key = (
            cell.border.left.style,
            cell.border.right.style,
            cell.border.top.style,
        )
        if key not in cache:
            cache[key] = Border(
                left=copy_module.copy(cell.border.left),
                right=copy_module.copy(cell.border.right),
                top=copy_module.copy(cell.border.top),
                bottom=LADO_FINO_GRUPO,
            )
        cell.border = cache[key]


def aplicar_formato_datos_conciliados(ws, cantidad_dias_mes: int) -> None:
    """Aplica únicamente la presentación oficial al bloque B2:AY52."""
    for column, width in ANCHOS_DATOS_CONCILIADOS.items():
        ws.column_dimensions[column].width = width

    for row, height in ALTURAS_DATOS_CONCILIADOS.items():
        ws.row_dimensions[row].height = height
    for row in range(21, 52):
        ws.row_dimensions[row].height = 13.8
        ws.row_dimensions[row].hidden = False
    for row in range(10, 14):
        ws.row_dimensions[row].hidden = True

    # La plantilla ya contiene las combinaciones oficiales. Solo se corrige una
    # eventual divergencia sin tocar valores ni fórmulas.
    target_merges = set(MERGES_DATOS_CONCILIADOS)
    current_target_merges = {
        str(item) for item in ws.merged_cells.ranges
        if item.min_row <= 52 and item.max_row >= 2
        and item.min_col <= 51 and item.max_col >= 2
    }
    for item in current_target_merges - target_merges:
        ws.unmerge_cells(item)
    for item in target_merges - current_target_merges:
        ws.merge_cells(item)

    # Extender el aspecto del ancla a todas las celdas de cada combinación
    # evita bloques discontinuos; los bordes individuales se conservan.
    for merged_ref in MERGES_DATOS_CONCILIADOS:
        merged = ws[merged_ref]
        anchor = merged[0][0]
        for row in merged:
            for cell in row:
                cell.fill = copy_module.copy(anchor.fill)
                cell.font = copy_module.copy(anchor.font)
                cell.alignment = copy_module.copy(anchor.alignment)

    # Fila 21 mantiene su apertura especial. Desde la 22 se alternan solo dos
    # rellenos compartidos, sin crear estilos según el valor de la celda.
    border_cache = {}
    for row in range(21, 52):
        fill = None
        if row >= 22:
            fill = RELLENO_BANDA_AZUL if row % 2 == 0 else RELLENO_BANDA_BLANCA
        for col in range(3, 51):  # C:AX; AY es el indicador lateral.
            cell = ws.cell(row, col)
            cell.font = FUENTE_FECHA_CONCILIADO if col == 3 else FUENTE_DATO_CONCILIADO
            cell.alignment = ALINEACION_DATO_CONCILIADO
            if col == 3:
                cell.number_format = "dd-mm-yyyy"
            if fill is not None:
                cell.fill = fill
            border_key = (
                col == 3,
                col in COLUMNAS_BORDE_DERECHO,
                cell.border.top.style,
                cell.border.bottom.style,
            )
            if border_key not in border_cache:
                border_cache[border_key] = Border(
                    left=LADO_FINO_GRUPO if col == 3 else LADO_VACIO,
                    right=LADO_FINO_GRUPO if col in COLUMNAS_BORDE_DERECHO else LADO_VACIO,
                    top=copy_module.copy(cell.border.top),
                    bottom=copy_module.copy(cell.border.bottom),
                )
            cell.border = border_cache[border_key]

    # La misma regla de separadores se aplica al encabezado, preservando sus
    # bordes horizontales y evitando líneas dobles P/Q, Y/Z y Z/AA.
    for row in range(18, 21):
        for col in range(3, 51):
            cell = ws.cell(row, col)
            cell.border = Border(
                left=LADO_FINO_GRUPO if col == 3 else LADO_VACIO,
                right=LADO_FINO_GRUPO if col in COLUMNAS_BORDE_DERECHO else LADO_VACIO,
                top=copy_module.copy(cell.border.top),
                bottom=copy_module.copy(cell.border.bottom),
            )

    # Siempre se mantienen visibles los 31 espacios diarios, incluido julio 31.
    for row in range(21, 21 + min(max(cantidad_dias_mes, 0), 31)):
        ws.row_dimensions[row].hidden = False

    ws.freeze_panes = None
    ws.sheet_view.showGridLines = False
    ws.print_area = "B2:AY52"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = "17"
    ws.page_setup.scale = 23
    ws.page_setup.fitToWidth = None
    ws.page_setup.fitToHeight = None
    ws.sheet_properties.pageSetUpPr.fitToPage = False
    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.75
    ws.page_margins.bottom = 0.75
    ws.page_margins.header = 0.3
    ws.page_margins.footer = 0.3


def _normalizar_y_compactar_estilos_xlsx(xlsx_bytes: bytes) -> bytes:
    """Compacta estilos usados y normaliza todos los colores RGB a ARGB opaco."""
    source = io.BytesIO(xlsx_bytes)
    files = {}
    infos = {}
    with ZipFile(source, "r") as archive:
        for info in archive.infolist():
            infos[info.filename] = info
            files[info.filename] = archive.read(info.filename)

    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    style_refs = {0}
    worksheet_roots = {}
    worksheet_names = [
        name for name in files
        if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
    ]
    for name in worksheet_names:
        root = ET.fromstring(files[name])
        worksheet_roots[name] = root
        for cell in root.iter(f"{{{ns}}}c"):
            if "s" in cell.attrib:
                style_refs.add(int(cell.attrib["s"]))
        for row in root.iter(f"{{{ns}}}row"):
            if "s" in row.attrib:
                style_refs.add(int(row.attrib["s"]))
        for col in root.iter(f"{{{ns}}}col"):
            if "style" in col.attrib:
                style_refs.add(int(col.attrib["style"]))

    styles_root = ET.fromstring(files["xl/styles.xml"])
    cell_xfs = styles_root.find(f"{{{ns}}}cellXfs")
    old_xfs = list(cell_xfs)
    used_xfs = [idx for idx in sorted(style_refs) if idx < len(old_xfs)]
    xf_remap = {old: new for new, old in enumerate(used_xfs)}
    cell_xfs[:] = [old_xfs[idx] for idx in used_xfs]
    cell_xfs.set("count", str(len(cell_xfs)))

    for root in worksheet_roots.values():
        for cell in root.iter(f"{{{ns}}}c"):
            if "s" in cell.attrib:
                cell.set("s", str(xf_remap[int(cell.attrib["s"])]))
        for row in root.iter(f"{{{ns}}}row"):
            if "s" in row.attrib:
                row.set("s", str(xf_remap[int(row.attrib["s"])]))
        for col in root.iter(f"{{{ns}}}col"):
            if "style" in col.attrib:
                col.set("style", str(xf_remap[int(col.attrib["style"])]))

    style_xfs = styles_root.find(f"{{{ns}}}cellStyleXfs")
    all_xfs = list(cell_xfs) + (list(style_xfs) if style_xfs is not None else [])
    for tag, attr, keep_base in (
        ("fonts", "fontId", {0}),
        ("fills", "fillId", {0, 1}),
        ("borders", "borderId", {0}),
    ):
        table = styles_root.find(f"{{{ns}}}{tag}")
        old_items = list(table)
        used = set(keep_base)
        used.update(int(xf.attrib.get(attr, 0)) for xf in all_xfs)
        used = {idx for idx in used if idx < len(old_items)}
        ordered = sorted(used)
        remap = {old: new for new, old in enumerate(ordered)}
        table[:] = [old_items[idx] for idx in ordered]
        table.set("count", str(len(table)))
        for xf in all_xfs:
            xf.set(attr, str(remap[int(xf.attrib.get(attr, 0))]))

    # Algunos estilos heredados guardan RGB con alfa 00. Excel espera ARGB.
    for element in styles_root.iter():
        rgb = element.attrib.get("rgb")
        if rgb and len(rgb) == 8 and rgb.startswith("00"):
            element.set("rgb", "FF" + rgb[2:])

    files["xl/styles.xml"] = ET.tostring(
        styles_root, encoding="utf-8", xml_declaration=True,
    )
    for name, root in worksheet_roots.items():
        files[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(infos[name], data)
    return output.getvalue()


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
    fecha_actualizacion = _actualizar_encabezado_datos_conciliados(ws, df)
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
    if blank_style_row <= (ws.max_row or 0):
        blank_styles = {
            c: copy_module.copy(ws.cell(blank_style_row, c)._style)
            for c in range(border_left_col, border_right2_col + 1)
        }
    else:
        default_blank_style = copy_module.copy(ws["A1"]._style)
        blank_styles = {
            c: copy_module.copy(default_blank_style)
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
        ref_row = (
            style_row_a if i == 0
            else style_row_b if excel_row % 2 == 0
            else style_row_b + 1
        )
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
            elif col == "Fecha" and hasattr(val, "to_pydatetime"):
                val = val.to_pydatetime()
            col_idx = start_col + j
            cell = ws.cell(row=excel_row, column=col_idx, value=val)
            # Todas las columnas (incluida Estado) usan el formato de la plantilla en esa columna
            src = ws.cell(row=ref_row, column=col_idx)
            _copy_cell_style(cell, src)

    # Copiar el marco lateral original en las filas de datos, sin fabricar
    # bordes nuevos ni alterar los bordes internos del template.
    for i in range(len(df)):
        row_idx = start_row + i
        ref_row = (
            style_row_a if i == 0
            else style_row_b if row_idx % 2 == 0
            else style_row_b + 1
        )
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

    resumen_mtd = calcular_resumen_mtd(df, fecha_actualizacion)
    escribir_resumen_mtd(ws, resumen_mtd, fecha_actualizacion)

    if fecha_actualizacion is not None:
        cantidad_dias_mes = calendar.monthrange(
            fecha_actualizacion.year, fecha_actualizacion.month,
        )[1]
    else:
        cantidad_dias_mes = min(len(df), 31)
    aplicar_formato_datos_conciliados(ws, cantidad_dias_mes)
    aplicar_borde_inferior_reporte(
        ws,
        fila_inicio_datos=start_row,
        fila_fin_mes=start_row + cantidad_dias_mes - 1,
        columna_inicio=start_col,
        columna_fin=start_col + num_cols - 2,  # C:AX; AY es indicador lateral.
    )

    out = io.BytesIO()
    wb.save(out)
    return _normalizar_y_compactar_estilos_xlsx(out.getvalue())
