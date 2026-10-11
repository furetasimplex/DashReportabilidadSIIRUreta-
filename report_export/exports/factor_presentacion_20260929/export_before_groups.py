# Auto-generated on 2025-10-27 18:21:09. Edit as needed.
import copy as copy_module
import calendar
import math
import io
import os
import html
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from zipfile import ZIP_DEFLATED, ZipFile
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.views import Selection
from report_export.report_export import BalanceReportError
from report_export.balance_contract import (
    build_balance_report_identity,
    validate_balance_template_hash,
)
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

COLUMNAS_CORTE_RESUMEN_DATOS_CONCILIADOS = (
    "Chancado_TMS_Real",
    "Apilado_TMS_Real", "Apilado_TMS_Plan",
    "Ley_CuT_Real", "Ley_CuT_Plan",
    "Cobre_fino_Apilado_Real", "Cobre_fino_Apilado_Plan",
    "SRR_TMS_promedio_dia", "SRR_TMS_Plan",
    # Ley_CuT_Real_srr queda fuera del corte a proposito: se calcula por
    # balance residual y depende de un insumo de laboratorio (mov_cam.CuTG00
    # para Destino=CH01) que puede atrasarse varios dias respecto al resto
    # del reporte. Si el dato no esta listo, la celda queda vacia pero ya
    # NO bloquea ni recorta el resto del resumen MTD.
    "Ley_CuT_Plan_srr",
    "TMS_Rotopala_1_Real", "TMS_Rotopala_1_Plan",
    "TMS_Rotopala_2_Real", "TMS_Rotopala_2_Plan",
    "Camiones_TMS_total", "Camiones_TMS_plan",
    "Total_Ripios_Incluye_Camiones_Real",
    "Total_Ripios_Incluye_Camiones_Plan",
    "Produccion_Catodos_Real", "Produccion_Catodos_Plan",
)


class DependenciaDatosExportError(ValueError):
    """Error de datos con contexto seguro para presentar en la interfaz."""

    def __init__(self, mensaje, fecha=None, campos=None):
        super().__init__(mensaje)
        self.fecha = fecha
        self.campos = tuple(campos or ())

MERGES_DATOS_CONCILIADOS = (
    "E12:F12", "Z6:AA6", "E19:G19", "Q19:S19", "O19:P19",
    "AA19:AB19", "Z3:AE3", "AU19:AV19", "AM19:AT19",
    "K19:N19", "Z7:AA7", "Z16:AA16", "AC18:AV18", "H19:J19",
    "AH19:AL19", "Y19:Z19", "C18:C20", "AG3:AU3",
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


def _load_balance_template(template_path: str):
    """Carga Balance sin limpiar nombres, hojas, vinculos ni formulas."""
    if not template_path or not os.path.isfile(template_path):
        raise BalanceReportError(
            f"No existe el template de Balance: {template_path}"
        )
    return load_workbook(
        template_path,
        data_only=False,
        keep_links=True,
        read_only=False,
    )


_BALANCE_SHEETS = (
    "Datos Reconciliados",
    "Análisis Variación-Tolerancias",
)
_BALANCE_ALL_SHEETS = (
    "Resumen",
    "Informe Hidrometalurgia",
    "Balance por Áreas",
    "Diagrama",
    "Datos Reconciliados",
    "Análisis Variación-Tolerancias",
    "Proceso Área Seca",
    "Proceso Área Húmeda",
    "Proceso Área Cátodos",
)
_BALANCE_FIELDS = (
    "tolerancia_masa", "tolerancia_ley", "masa_medida",
    "masa_reconciliada", "ley_cu_medida", "ley_cu_reconciliada",
    "fino_cu_medido", "fino_cu_reconciliado",
)


def _balance_normalize(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.strip().lower())


def _balance_excel_value(value):
    """Convierte NaN/NA a celda vacia sin transformar ceros ni signos."""
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def _balance_metadata_dict(metadata):
    if isinstance(metadata, pd.Series):
        return metadata.to_dict()
    if isinstance(metadata, pd.DataFrame):
        if len(metadata) != 1:
            raise BalanceReportError("La metadata del Run debe contener una fila.")
        return metadata.iloc[0].to_dict()
    if isinstance(metadata, dict):
        return dict(metadata)
    raise BalanceReportError("La metadata del Run no tiene un formato valido.")


def _balance_validate_codes(frame, label):
    if not isinstance(frame, pd.DataFrame):
        raise BalanceReportError(f"{label} debe ser un DataFrame.")
    if len(frame) != 120:
        raise BalanceReportError(
            f"{label} posee {len(frame)} flujos; se esperaban 120."
        )
    if "codigo_flujo" not in frame.columns:
        raise BalanceReportError(f"{label} no contiene codigo_flujo.")
    codes = frame["codigo_flujo"].astype(str).str.strip()
    duplicated = sorted(codes[codes.duplicated(keep=False)].unique())
    if duplicated:
        raise BalanceReportError(
            f"{label} contiene codigos duplicados: "
            + ", ".join(duplicated)
            + "."
        )
    expected = {f"F{i}" for i in range(1, 121)}
    received = set(codes)
    missing_codes = sorted(expected - received, key=lambda x: int(x[1:]))
    extra_codes = sorted(received - expected)
    if missing_codes:
        raise BalanceReportError("Faltan flujos: " + ", ".join(missing_codes) + ".")
    if extra_codes:
        raise BalanceReportError(
            "Existen flujos no esperados: " + ", ".join(extra_codes) + "."
        )
    normalized = frame.copy()
    normalized["codigo_flujo"] = codes
    return normalized.set_index("codigo_flujo", drop=False)


def _balance_validate_inputs(df_periodo, df_acumulado, metadata):
    if not isinstance(df_periodo, pd.DataFrame):
        raise BalanceReportError("El periodo debe ser un DataFrame.")
    if not isinstance(df_acumulado, pd.DataFrame):
        raise BalanceReportError("El acumulado debe ser un DataFrame.")
    missing = sorted(
        set(("codigo_flujo",) + _BALANCE_FIELDS) - set(df_periodo.columns)
    )
    if missing:
        raise BalanceReportError(
            "Faltan columnas para generar Balance: " + ", ".join(missing) + "."
        )
    accumulated_fields = {
        "codigo_flujo",
        "masa_reconciliada_acumulada",
        "ley_cu_reconciliada_acumulada",
        "fino_cu_reconciliado_acumulado",
    }
    missing_accumulated = sorted(accumulated_fields - set(df_acumulado.columns))
    if missing_accumulated:
        raise BalanceReportError(
            "Faltan columnas acumuladas para generar Balance: "
            + ", ".join(missing_accumulated)
            + "."
        )

    meta = _balance_metadata_dict(metadata)
    start = pd.to_datetime(meta.get("fecha_inicio"), errors="coerce")
    end = pd.to_datetime(meta.get("fecha_fin"), errors="coerce")
    if pd.isna(start) or pd.isna(end):
        raise BalanceReportError("El Caso no posee fecha_inicio/fecha_fin validas.")
    if start.date() > end.date():
        raise BalanceReportError("fecha_inicio no puede ser posterior a fecha_fin.")
    if start.year != end.year or start.month != end.month:
        raise BalanceReportError(
            "El Caso seleccionado cruza meses y no puede utilizarse para "
            "construir un acumulado MTD con resultados agregados por Caso."
        )
    mtd_start = pd.to_datetime(
        meta.get("fecha_inicio_acumulado", end.replace(day=1)), errors="coerce"
    )
    mtd_end = pd.to_datetime(
        meta.get("fecha_fin_acumulado", end), errors="coerce"
    )
    if pd.isna(mtd_start) or pd.isna(mtd_end):
        raise BalanceReportError("Las fechas del acumulado MTD no son validas.")
    if mtd_start.date() != end.date().replace(day=1) or mtd_end.date() != end.date():
        raise BalanceReportError("El intervalo acumulado MTD no coincide con el Caso.")
    period = _balance_validate_codes(df_periodo, "El periodo")
    accumulated = _balance_validate_codes(df_acumulado, "El acumulado")
    return (
        period,
        accumulated,
        meta,
        start.date(),
        end.date(),
        mtd_start.date(),
    )


def _balance_flow_rows(ws):
    found = {f"F{i}": [] for i in range(1, 121)}
    for row in ws.iter_rows():
        for cell in row:
            value = str(cell.value).strip() if cell.value is not None else ""
            if value in found:
                found[value].append(cell.coordinate)
    for code, coords in found.items():
        if not coords:
            raise BalanceReportError(
                f"El Flow ID {code} no fue encontrado en {ws.title}."
            )
        if len(coords) != 1:
            raise BalanceReportError(
                f"El Flow ID {code} aparece duplicado en el template "
                f"({ws.title}: {', '.join(coords)})."
            )
    columns = {ws[coords[0]].column for coords in found.values()}
    if len(columns) != 1:
        raise BalanceReportError(
            f"Los Flow ID de {ws.title} no estan en una unica columna."
        )
    return {code: ws[coords[0]].row for code, coords in found.items()}, columns.pop()


def _balance_header_context(ws, column, first_data_row):
    values = []
    start_row = max(1, first_data_row - 12)
    for row in range(start_row, first_data_row):
        cell = ws.cell(row=row, column=column)
        value = cell.value
        if value is None:
            for merged in ws.merged_cells.ranges:
                if cell.coordinate in merged:
                    value = ws.cell(merged.min_row, merged.min_col).value
                    break
        if value is not None:
            values.append(str(value))
    return _balance_normalize(" | ".join(values))


def _balance_find_column(ws, flow_col, first_data_row, description, predicate):
    matches = []
    for column in range(1, ws.max_column + 1):
        if column == flow_col:
            continue
        context = _balance_header_context(ws, column, first_data_row)
        if predicate(context):
            matches.append((column, context))
    if len(matches) != 1:
        detail = "; ".join(f"{get_column_letter(c)}={h}" for c, h in matches)
        raise BalanceReportError(
            f"No fue posible identificar univocamente la columna {description} "
            f"en {ws.title}. Coincidencias: {detail or 'ninguna'}."
        )
    return matches[0][0]


def _balance_columns_reconciliados(ws, flow_col, first_row):
    def period(ctx): return "period" in ctx and "acumul" not in ctx
    def accum(ctx): return "acumul" in ctx
    def ton(ctx): return "tonel" in ctx or "masa" in ctx
    def fine(ctx): return "fino" in ctx
    def grade(ctx): return "ley" in ctx and not fine(ctx)
    return {
        "period_masa": _balance_find_column(ws, flow_col, first_row, "Tonelaje periodo", lambda c: period(c) and ton(c)),
        "period_ley": _balance_find_column(ws, flow_col, first_row, "Ley Cu periodo", lambda c: period(c) and grade(c)),
        "period_fino": _balance_find_column(ws, flow_col, first_row, "Cu fino periodo", lambda c: period(c) and fine(c)),
        "accum_masa": _balance_find_column(ws, flow_col, first_row, "Tonelaje acumulado", lambda c: accum(c) and ton(c)),
        "accum_ley": _balance_find_column(ws, flow_col, first_row, "Ley Cu acumulada", lambda c: accum(c) and grade(c)),
        "accum_fino": _balance_find_column(ws, flow_col, first_row, "Cu fino acumulado", lambda c: accum(c) and fine(c)),
    }


def _balance_columns_analysis(ws, flow_col, first_row):
    def fine(ctx): return "fino" in ctx
    def ton(ctx): return "tonel" in ctx or "masa" in ctx
    def measured(ctx): return "medido" in ctx
    return {
        "tol_masa": _balance_find_column(ws, flow_col, first_row, "Tolerancia", lambda c: "tolerancia" in c and "cu" not in c and "ley" not in c),
        "tol_ley": _balance_find_column(ws, flow_col, first_row, "Tolerancia Cu", lambda c: "tolerancia" in c and ("cu" in c or "ley" in c)),
        "med_masa": _balance_find_column(ws, flow_col, first_row, "Medido Tonelaje", lambda c: measured(c) and ton(c)),
        "med_ley": _balance_find_column(ws, flow_col, first_row, "Medido Ley Cu", lambda c: measured(c) and "ley" in c and not fine(c)),
        "med_fino": _balance_find_column(ws, flow_col, first_row, "Medido Cu fino", lambda c: measured(c) and fine(c)),
    }


def _balance_write_cell(ws, row, column, value):
    cell = ws.cell(row=row, column=column)
    if cell.data_type == "f" or (isinstance(cell.value, str) and cell.value.startswith("=")):
        raise BalanceReportError(
            f"La celda autorizada {ws.title}!{cell.coordinate} contiene una formula."
        )
    cell.value = _balance_excel_value(value)


def _balance_period_text(prefix, start, end):
    months = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )
    return f"{prefix} {start.day:02d} al {end.day:02d} de {months[end.month - 1]} {end.year}"


def _balance_update_authorized_visible_metadata(wb, metadata, start, end):
    """Actualiza los textos visibles autorizados de período, MTD e identidad."""
    months = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )
    month = months[end.month - 1]
    period_without_year = (
        f"Período {start.day:02d} al {end.day:02d} de {month}"
    )
    identity = build_balance_report_identity(metadata)
    mtd_end = pd.to_datetime(metadata.get("mtd_fecha_fin"), errors="coerce")
    if pd.isna(mtd_end):
        raise BalanceReportError("Falta mtd_fecha_fin válida para las cabeceras acumuladas.")
    accumulated_label = f"Acumulado al {mtd_end.day:02d} de {months[mtd_end.month - 1]}"
    values = {
        ("Resumen", "F10"): (
            f"{identity['caso_label']} | {identity['run_label']}"
        ),
        ("Resumen", "E11"): f"Período {start.day:02d} al {end.day:02d}",
        ("Resumen", "F11"): f"Acumulado al {end.day:02d}",
        ("Proceso Área Seca", "P14"): period_without_year,
        ("Proceso Área Húmeda", "U17"): period_without_year,
        ("Proceso Área Húmeda", "U105"): period_without_year,
        ("Proceso Área Cátodos", "P14"): period_without_year,
        ("Proceso Área Seca", "R14"): accumulated_label,
        ("Proceso Área Húmeda", "W17"): accumulated_label,
        ("Proceso Área Húmeda", "W105"): accumulated_label,
        ("Proceso Área Cátodos", "R14"): accumulated_label,
    }
    for (sheet_name, coordinate), value in values.items():
        cell = wb[sheet_name][coordinate]
        if cell.data_type == "f" or (
            isinstance(cell.value, str) and cell.value.startswith("=")
        ):
            raise BalanceReportError(
                f"La celda de metadata {sheet_name}!{coordinate} contiene una formula."
            )
        cell.value = value


def _balance_update_headers_and_metadata(wb, metadata, start, end, mtd_start):
    period_text = _balance_period_text("Período", start, end)
    accumulated_text = _balance_period_text("Acumulado", mtd_start, end)
    for sheet_name in _BALANCE_SHEETS:
        ws = wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str) or cell.value.startswith("="):
                    continue
                normalized = _balance_normalize(cell.value)
                if normalized.startswith("periodo"):
                    cell.value = period_text
                elif normalized.startswith("acumulado"):
                    cell.value = accumulated_text

    label_values = {
        "nombre caso": metadata.get("nombre_caso"),
        "fecha inicio": start,
        "fecha fin": end,
        "run id": metadata.get("run_id"),
        "caso id": metadata.get("caso_id"),
        "modelo id": metadata.get("modelo_id"),
        "solver name": metadata.get("solver_name"),
        "solver version": metadata.get("solver_version"),
        "es oficial": "SI" if bool(metadata.get("es_oficial")) else "NO - DEV",
    }
    occurrences = {label: [] for label in label_values}
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                normalized = _balance_normalize(cell.value)
                if normalized.rstrip(":") in occurrences:
                    occurrences[normalized.rstrip(":")].append((ws, cell))
    for label, locations in occurrences.items():
        if len(locations) != 1:
            continue
        ws, label_cell = locations[0]
        target = ws.cell(label_cell.row, label_cell.column + 1)
        if target.data_type != "f" and not (
            isinstance(target.value, str) and target.value.startswith("=")
        ):
            target.value = _balance_excel_value(label_values[label])
    _balance_update_authorized_visible_metadata(wb, metadata, start, end)


def _balance_cell_snapshot(wb):
    return {
        (ws.title, cell.coordinate): (cell.value, cell.data_type)
        for ws in wb.worksheets
        for row in ws.iter_rows()
        for cell in row
    }


def _balance_sheet_parts(files):
    ns_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ns_pkg = "http://schemas.openxmlformats.org/package/2006/relationships"
    workbook = ET.fromstring(files["xl/workbook.xml"])
    relationships = ET.fromstring(files["xl/_rels/workbook.xml.rels"])
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(f"{{{ns_pkg}}}Relationship")
    }
    result = {}
    for sheet in workbook.findall(f".//{{{ns_main}}}sheet"):
        target = targets[sheet.attrib[f"{{{ns_rel}}}id"]]
        part = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.join("xl", target)
        )
        result[sheet.attrib["name"]] = posixpath.normpath(part)
    return result


def _balance_cell_xml(sheet_xml, coordinate):
    pattern = re.compile(
        rb'<c\b(?=[^>]*\br="' + re.escape(coordinate.encode("ascii"))
        + rb'")[^>]*?(?:\s*/>|>.*?</c>)',
        re.DOTALL,
    )
    match = pattern.search(sheet_xml)
    return match.group(0) if match else None


def _balance_replace_cell_xml(base_xml, source_xml, coordinate):
    replacement = _balance_cell_xml(source_xml, coordinate)
    if replacement is None:
        raise BalanceReportError(
            f"No fue posible serializar la celda autorizada {coordinate}."
        )
    pattern = re.compile(
        rb'<c\b(?=[^>]*\br="' + re.escape(coordinate.encode("ascii"))
        + rb'")[^>]*?(?:\s*/>|>.*?</c>)',
        re.DOTALL,
    )
    base_match = pattern.search(base_xml)
    if base_match:
        original = base_match.group(0)
        original_open = re.match(rb"<c\b[^>]*", original).group(0)
        original_open = re.sub(rb"\s*/\s*$", b"", original_open)
        source_open = re.match(rb"<c\b[^>]*", replacement).group(0)
        source_type = re.search(rb'\bt="([^"]+)"', source_open)
        merged_open = re.sub(rb'\s+t="[^"]+"', b"", original_open)
        if source_type and not replacement.rstrip().endswith(b"/>"):
            merged_open += b' t="' + source_type.group(1) + b'"'
        if replacement.endswith(b"/>"):
            merged = merged_open + b"/>"
        else:
            source_content = replacement[replacement.find(b">") + 1:-4]
            merged = merged_open + b">" + source_content + b"</c>"
        return base_xml[:base_match.start()] + merged + base_xml[base_match.end():]
    row_number = re.search(r"\d+", coordinate).group(0).encode("ascii")
    row_pattern = re.compile(
        rb'(<row\b(?=[^>]*\br="' + row_number + rb'")[^>]*>)(.*?)(</row>)',
        re.DOTALL,
    )
    if not row_pattern.search(base_xml):
        raise BalanceReportError(
            f"No existe la fila OOXML para insertar la celda {coordinate}."
        )
    return row_pattern.sub(
        lambda match: match.group(1) + match.group(2) + replacement + match.group(3),
        base_xml,
        count=1,
    )


def _balance_direct_xf_nodes(cell_xfs_body):
    """Extrae los xf hijos directos sin reserializar el XML del template."""
    nodes = []
    position = 0
    while True:
        start = cell_xfs_body.find(b"<xf", position)
        if start < 0:
            return nodes
        open_end = cell_xfs_body.find(b">", start) + 1
        if open_end == 0:
            raise BalanceReportError("styles.xml contiene un xf incompleto.")
        if cell_xfs_body[open_end - 2:open_end] == b"/>":
            end = open_end
        else:
            end = cell_xfs_body.find(b"</xf>", open_end)
            if end < 0:
                raise BalanceReportError("styles.xml contiene un xf sin cierre.")
            end += len(b"</xf>")
        nodes.append(cell_xfs_body[start:end])
        position = end


def _balance_apply_f10_dark_font(files, summary_part):
    """Crea un estilo negro exclusivo para Resumen!F10 en el output."""
    cell = _balance_cell_xml(files[summary_part], "F10")
    style_match = re.search(rb'\bs="(\d+)"', cell or b"")
    if not style_match:
        raise BalanceReportError("Resumen!F10 no conserva un estilo OOXML base.")
    source_style_id = int(style_match.group(1))

    styles = files["xl/styles.xml"]
    fonts_match = re.search(rb'(<fonts\b[^>]*\bcount=")(\d+)("[^>]*>)(.*?)(</fonts>)', styles, re.DOTALL)
    xfs_match = re.search(rb'(<cellXfs\b[^>]*\bcount=")(\d+)("[^>]*>)(.*?)(</cellXfs>)', styles, re.DOTALL)
    if not fonts_match or not xfs_match:
        raise BalanceReportError("No fue posible localizar fonts/cellXfs en styles.xml.")

    fonts = re.findall(rb"<font>.*?</font>", fonts_match.group(4), re.DOTALL)
    xfs = _balance_direct_xf_nodes(xfs_match.group(4))
    if source_style_id >= len(xfs):
        raise BalanceReportError("El estilo de Resumen!F10 no existe en cellXfs.")
    source_xf = xfs[source_style_id]
    font_match = re.search(rb'\bfontId="(\d+)"', source_xf)
    if not font_match or int(font_match.group(1)) >= len(fonts):
        raise BalanceReportError("El font de Resumen!F10 no existe en styles.xml.")
    source_font = fonts[int(font_match.group(1))]
    dark_font, replacements = re.subn(
        rb'<color\b[^>]*/>', b'<color rgb="FF000000"/>', source_font, count=1
    )
    if replacements != 1:
        raise BalanceReportError("El font de Resumen!F10 no tiene color reemplazable.")

    new_font_id = len(fonts)
    new_style_id = len(xfs)
    dark_xf, replacements = re.subn(
        rb'\bfontId="\d+"', f'fontId="{new_font_id}"'.encode("ascii"), source_xf, count=1
    )
    if replacements != 1:
        raise BalanceReportError("El estilo de Resumen!F10 no referencia un font.")

    new_fonts = (
        fonts_match.group(1) + str(new_font_id + 1).encode("ascii")
        + fonts_match.group(3) + fonts_match.group(4) + dark_font + fonts_match.group(5)
    )
    styles = styles[:fonts_match.start()] + new_fonts + styles[fonts_match.end():]
    xfs_match = re.search(rb'(<cellXfs\b[^>]*\bcount=")(\d+)("[^>]*>)(.*?)(</cellXfs>)', styles, re.DOTALL)
    new_xfs = (
        xfs_match.group(1) + str(new_style_id + 1).encode("ascii")
        + xfs_match.group(3) + xfs_match.group(4) + dark_xf + xfs_match.group(5)
    )
    files["xl/styles.xml"] = styles[:xfs_match.start()] + new_xfs + styles[xfs_match.end():]

    updated_cell = re.sub(
        rb'\bs="\d+"', f's="{new_style_id}"'.encode("ascii"), cell, count=1
    )
    files[summary_part] = files[summary_part].replace(cell, updated_cell, 1)


def validate_balance_output_package(xlsx_bytes):
    """Rechaza ZIP, XML o referencias de celda invalidas antes de exportar."""
    with ZipFile(io.BytesIO(xlsx_bytes), "r") as archive:
        names = [item.filename for item in archive.infolist()]
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        if duplicates:
            raise BalanceReportError(
                "El XLSX contiene partes ZIP duplicadas: " + ", ".join(duplicates)
            )
        corrupt = archive.testzip()
        if corrupt:
            raise BalanceReportError(f"CRC invalido en la parte XLSX {corrupt}.")
        name_set = set(names)
        sheet_parts = _balance_sheet_parts({name: archive.read(name) for name in names})
        permitted_ref_parts = {
            sheet_parts[sheet] for sheet in (
                "Proceso Área Seca", "Proceso Área Húmeda", "Proceso Área Cátodos"
            )
        }
        accepted_ref_parts = set()
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
        content_ns = "{http://schemas.openxmlformats.org/package/2006/content-types}"
        content_types = ET.fromstring(archive.read("[Content_Types].xml"))
        defaults = {
            item.attrib["Extension"]
            for item in content_types.findall(content_ns + "Default")
        }
        overrides = {
            item.attrib["PartName"].lstrip("/")
            for item in content_types.findall(content_ns + "Override")
        }
        missing_types = [
            name for name in names
            if name != "[Content_Types].xml"
            and not name.endswith("/")
            and name not in overrides
            and name.rsplit(".", 1)[-1] not in defaults
        ]
        if missing_types:
            raise BalanceReportError(
                "Partes XLSX sin Content Type: " + ", ".join(missing_types)
            )
        for name in names:
            if not (name.endswith(".xml") or name.endswith(".rels")):
                continue
            try:
                root = ET.fromstring(archive.read(name))
            except ET.ParseError as exc:
                raise BalanceReportError(
                    f"XML invalido en {name}: {exc}."
                ) from exc
            # Strict exception: one preexisting list validation at C11 per process sheet.
            if name in permitted_ref_parts:
                for validation in root.findall("m:dataValidations/m:dataValidation", ns):
                    formula = validation.find("m:formula1", ns)
                    if (validation.attrib.get("sqref") == "C11"
                            and validation.attrib.get("type") == "list"
                            and formula is not None and formula.text == "#REF!"):
                        if name in accepted_ref_parts:
                            raise BalanceReportError(f"#REF! autorizado duplicado en {name}.")
                        accepted_ref_parts.add(name)
                        # Only the parsed audit tree changes; archive bytes remain untouched.
                        formula.text = ""
            if "#REF!" in ET.tostring(root, encoding="unicode"):
                raise BalanceReportError(f"#REF! no autorizado en {name}.")
            if name.endswith(".rels"):
                source_part = (
                    ""
                    if name == "_rels/.rels"
                    else name.replace("/_rels/", "/").removesuffix(".rels")
                )
                base = posixpath.dirname(source_part)
                for relationship in root.findall(rel_ns + "Relationship"):
                    if relationship.attrib.get("TargetMode") == "External":
                        continue
                    target = relationship.attrib["Target"]
                    resolved = (
                        target.lstrip("/")
                        if target.startswith("/")
                        else posixpath.normpath(posixpath.join(base, target))
                    )
                    if resolved not in name_set:
                        raise BalanceReportError(
                            f"Relacion OOXML colgante en {name}: {target}."
                        )
            if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                continue
            for row in root.findall(".//m:row", ns):
                refs = [cell.attrib.get("r") for cell in row.findall("m:c", ns)]
                repeated = sorted(
                    ref for ref, count in Counter(refs).items() if ref and count > 1
                )
                if repeated:
                    raise BalanceReportError(
                        f"Referencias de celda duplicadas en {name}, fila "
                        f"{row.attrib.get('r')}: {', '.join(repeated)}."
                    )
        if accepted_ref_parts != permitted_ref_parts:
            raise BalanceReportError("Deben conservarse exactamente los tres #REF! autorizados en C11.")


def _balance_update_period_textbox(drawing_xml, period_text):
    shape_pattern = re.compile(rb"<xdr:sp\b.*?</xdr:sp>", re.DOTALL)
    text_pattern = re.compile(rb"(<a:t>)(.*?)(</a:t>)", re.DOTALL)
    matches = []
    for match in shape_pattern.finditer(drawing_xml):
        runs = text_pattern.findall(match.group(0))
        combined = "".join(
            html.unescape(value.decode("utf-8")) for _, value, _ in runs
        )
        if _balance_normalize(combined).startswith("periodo:"):
            matches.append((match, runs))
    if len(matches) != 1:
        raise BalanceReportError(
            "No fue posible identificar univocamente el cuadro DrawingML de periodo."
        )
    shape_match, runs = matches[0]
    remaining = period_text
    new_runs = []
    for index, (opening, original, closing) in enumerate(runs):
        original_text = html.unescape(original.decode("utf-8"))
        if index == len(runs) - 1:
            chunk, remaining = remaining, ""
        else:
            chunk = remaining[:len(original_text)]
            remaining = remaining[len(original_text):]
        new_runs.append(
            opening + html.escape(chunk, quote=False).encode("utf-8") + closing
        )
    iterator = iter(new_runs)
    updated_shape = text_pattern.sub(lambda _: next(iterator), shape_match.group(0))
    return drawing_xml[:shape_match.start()] + updated_shape + drawing_xml[shape_match.end():]


def _balance_patch_single_tag_attributes(xml, tag, attributes):
    """Parchea atributos sin reserializar el elemento ni el documento."""
    matches = list(re.finditer(rb"<" + tag + rb"\b[^>]*>", xml))
    if len(matches) != 1:
        raise BalanceReportError(f"El elemento OOXML {tag.decode()} no es univoco.")
    match = matches[0]
    opening = match.group()
    for attribute, value in attributes.items():
        attr_pattern = rb'\s+' + attribute + rb'="[^"]*"'
        replacement = b'' if value is None else b' ' + attribute + b'="' + value + b'"'
        if re.search(attr_pattern, opening):
            opening = re.sub(attr_pattern, lambda _: replacement, opening)
        elif value is not None:
            end = -2 if opening.endswith(b'/>') else -1
            opening = opening[:end] + replacement + opening[end:]
    return xml[:match.start()] + opening + xml[match.end():]


def _balance_set_initial_view(files, sheet_parts):
    """Normaliza solo atributos de apertura en la copia OOXML en memoria."""
    if next(iter(sheet_parts)) != "Resumen":
        raise BalanceReportError("Resumen debe ser la primera hoja del Balance.")
    files["xl/workbook.xml"] = _balance_patch_single_tag_attributes(
        files["xl/workbook.xml"], b'workbookView',
        {b'activeTab': b'0', b'firstSheet': b'0'},
    )
    for sheet, part in sheet_parts.items():
        attributes = {b'tabSelected': b'1', b'topLeftCell': b'A1'} if sheet == 'Resumen' else {b'tabSelected': None}
        files[part] = _balance_patch_single_tag_attributes(files[part], b'sheetView', attributes)
    summary = sheet_parts['Resumen']
    files[summary] = _balance_patch_single_tag_attributes(
        files[summary], b'selection', {b'activeCell': b'A1', b'sqref': b'A1'},
    )


def _balance_clear_formula_caches(files, sheet_parts):
    """Elimina solo <v> de celdas con <f>; Excel calcula al abrir."""
    files['xl/workbook.xml'] = _balance_patch_single_tag_attributes(
        files['xl/workbook.xml'], b'calcPr',
        {b'calcMode': b'auto', b'fullCalcOnLoad': b'1', b'forceFullCalc': b'1'},
    )
    removed = 0
    def clear_cell(match):
        nonlocal removed
        cell = match.group()
        if not re.search(rb'<f\b', cell):
            return cell
        cell, count = re.subn(rb'<v\b[^>]*?(?:/>|>.*?</v>)', b'', cell, flags=re.DOTALL)
        removed += count
        return cell
    for part in sheet_parts.values():
        files[part] = re.sub(
            rb'<c\b[^>]*?(?:/>|>.*?</c>)', clear_cell, files[part], flags=re.DOTALL,
        )
    return removed


def _balance_package_preserving_output(template_path, staged_bytes, changed_cells, start, end):
    """Parte del OOXML maestro y sustituye solo celdas/textos autorizados."""
    with ZipFile(template_path, "r") as archive:
        infos = {item.filename: item for item in archive.infolist()}
        files = {item.filename: archive.read(item.filename) for item in archive.infolist()}
    with ZipFile(io.BytesIO(staged_bytes), "r") as archive:
        staged_files = {item.filename: archive.read(item.filename) for item in archive.infolist()}

    base_sheets = _balance_sheet_parts(files)
    staged_sheets = _balance_sheet_parts(staged_files)
    for sheet_name, coordinate in sorted(changed_cells):
        base_part = base_sheets[sheet_name]
        source_part = staged_sheets[sheet_name]
        files[base_part] = _balance_replace_cell_xml(
            files[base_part], staged_files[source_part], coordinate
        )

    _balance_apply_f10_dark_font(files, base_sheets["Resumen"])

    period_text = _balance_period_text("Período:", start, end) + "."
    for part in (
        "xl/drawings/drawing1.xml",
        "xl/drawings/drawing2.xml",
        "xl/drawings/drawing3.xml",
    ):
        files[part] = _balance_update_period_textbox(files[part], period_text)

    _balance_set_initial_view(files, base_sheets)
    removed_caches = _balance_clear_formula_caches(files, base_sheets)
    print(f"[BALANCE EXPORT] caches_formula_eliminados={removed_caches}")
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(infos[name], data)
    result = output.getvalue()
    validate_balance_output_package(result)
    return result


def _balance_enable_full_calculation(wb):
    calc = getattr(wb, "calculation", None) or getattr(wb, "calculation_properties", None)
    if calc is None:
        return
    for attr, value in (
        ("calcMode", "auto"),
        ("fullCalcOnLoad", True),
        ("forceFullCalc", True),
    ):
        if hasattr(calc, attr):
            setattr(calc, attr, value)


def _balance_validate_template_contract(wb):
    """Valida la geometria observada en el template maestro oficial."""
    missing_sheets = [name for name in _BALANCE_ALL_SHEETS if name not in wb.sheetnames]
    if missing_sheets:
        raise BalanceReportError(
            "El template de Balance no contiene las hojas oficiales: "
            + ", ".join(missing_sheets)
            + "."
        )

    ws_data = wb[_BALANCE_SHEETS[0]]
    rows_data, flow_col_data = _balance_flow_rows(ws_data)
    expected_data_rows = {f"F{i}": i + 2 for i in range(1, 121)}
    if flow_col_data != 2 or rows_data != expected_data_rows:
        raise BalanceReportError(
            "La tabla F1-F120 de Datos Reconciliados ya no ocupa B3:B122."
        )
    required_data_merges = {"B2:C2", "D1:F1", "G1:I1", "K2:M2"}
    actual_data_merges = {str(item) for item in ws_data.merged_cells.ranges}
    if not required_data_merges.issubset(actual_data_merges):
        raise BalanceReportError(
            "La estructura de encabezados combinados de Datos Reconciliados cambio."
        )
    cols_data = _balance_columns_reconciliados(ws_data, flow_col_data, 3)
    expected_data_cols = {
        "period_masa": 4,
        "period_ley": 5,
        "period_fino": 6,
        "accum_masa": 7,
        "accum_ley": 8,
        "accum_fino": 9,
    }
    if cols_data != expected_data_cols:
        raise BalanceReportError(
            "Las columnas Periodo/Acumulado de Datos Reconciliados cambiaron."
        )

    ws_analysis = wb[_BALANCE_SHEETS[1]]
    rows_analysis, flow_col_analysis = _balance_flow_rows(ws_analysis)
    expected_analysis_rows = {f"F{i}": i + 3 for i in range(1, 121)}
    if flow_col_analysis != 2 or rows_analysis != expected_analysis_rows:
        raise BalanceReportError(
            "La tabla F1-F120 de Analisis Variacion-Tolerancias ya no ocupa B4:B123."
        )
    required_analysis_merges = {
        "D1:D3", "E1:E3", "F1:Q1", "F2:I2", "J2:M2", "N2:Q2"
    }
    actual_analysis_merges = {
        str(item) for item in ws_analysis.merged_cells.ranges
    }
    if not required_analysis_merges.issubset(actual_analysis_merges):
        raise BalanceReportError(
            "La estructura de encabezados combinados de Analisis "
            "Variacion-Tolerancias cambio."
        )
    cols_analysis = _balance_columns_analysis(ws_analysis, flow_col_analysis, 4)
    expected_analysis_cols = {
        "tol_masa": 4,
        "tol_ley": 5,
        "med_masa": 6,
        "med_ley": 10,
        "med_fino": 14,
    }
    if cols_analysis != expected_analysis_cols:
        raise BalanceReportError(
            "Las columnas escribibles de Analisis Variacion-Tolerancias cambiaron."
        )
    for row in range(4, 124):
        for column in (7, 8, 9, 11, 12, 13, 15, 16, 17):
            if ws_analysis.cell(row, column).data_type != "f":
                raise BalanceReportError(
                    "Falta una formula protegida en Analisis "
                    f"Variacion-Tolerancias!{ws_analysis.cell(row, column).coordinate}."
                )

    for sheet_name, coordinate in (
        ("Proceso Área Seca", "P14"),
        ("Proceso Área Húmeda", "U17"),
        ("Proceso Área Húmeda", "U105"),
        ("Proceso Área Cátodos", "P14"),
    ):
        if wb[sheet_name][coordinate].value != "Período 01 al 23 de Agosto":
            raise BalanceReportError(f"Encabezado contractual inesperado en {sheet_name}!{coordinate}.")
    for row in range(4, 124):
        for column, source_column in ((7, "D"), (11, "E"), (15, "F")):
            if ws_analysis.cell(row, column).value != f"='Datos Reconciliados'!{source_column}{row - 1}":
                raise BalanceReportError(f"Enlace reconciliado inesperado en Analisis, fila {row}.")

    return (
        ws_data,
        rows_data,
        cols_data,
        ws_analysis,
        rows_analysis,
        cols_analysis,
    )


def export_balance_reconciliacion_to_template(
    df_periodo, df_acumulado, metadata, template_path
):
    """Inyecta solamente inputs del reconciliador en el template oficial."""
    try:
        template_hash = validate_balance_template_hash(template_path)
    except (OSError, ValueError) as exc:
        raise BalanceReportError(str(exc)) from exc
    print(f"[BALANCE EXPORT] template_hash={template_hash}")
    data, accumulated, meta, start, end, mtd_start = _balance_validate_inputs(
        df_periodo, df_acumulado, metadata
    )
    wb = _load_balance_template(template_path)
    (
        ws_data,
        rows_data,
        cols_data,
        ws_analysis,
        rows_analysis,
        cols_analysis,
    ) = _balance_validate_template_contract(wb)
    original_cells = _balance_cell_snapshot(wb)
    for code, row in rows_data.items():
        source = data.loc[code]
        _balance_write_cell(ws_data, row, cols_data["period_masa"], source["masa_reconciliada"])
        _balance_write_cell(ws_data, row, cols_data["period_ley"], source["ley_cu_reconciliada"])
        _balance_write_cell(ws_data, row, cols_data["period_fino"], source["fino_cu_reconciliado"])
        accumulated_source = accumulated.loc[code]
        _balance_write_cell(ws_data, row, cols_data["accum_masa"], accumulated_source["masa_reconciliada_acumulada"])
        _balance_write_cell(ws_data, row, cols_data["accum_ley"], accumulated_source["ley_cu_reconciliada_acumulada"])
        _balance_write_cell(ws_data, row, cols_data["accum_fino"], accumulated_source["fino_cu_reconciliado_acumulado"])

    for code, row in rows_analysis.items():
        source = data.loc[code]
        _balance_write_cell(ws_analysis, row, cols_analysis["tol_masa"], source["tolerancia_masa"])
        # La plantilla llama "Tolerancia Cu" a tolerancia_ley; la BD no
        # posee una tolerancia_fino_cu independiente.
        _balance_write_cell(ws_analysis, row, cols_analysis["tol_ley"], source["tolerancia_ley"])
        _balance_write_cell(ws_analysis, row, cols_analysis["med_masa"], source["masa_medida"])
        _balance_write_cell(ws_analysis, row, cols_analysis["med_ley"], source["ley_cu_medida"])
        _balance_write_cell(ws_analysis, row, cols_analysis["med_fino"], source["fino_cu_medido"])

    _balance_write_cell(ws_data, 3, 12, (end - start).days + 1)
    _balance_write_cell(ws_data, 4, 12, (end - mtd_start).days + 1)
    display_metadata = dict(meta)
    # Alias de la fecha MTD entregada por el servicio; nunca usar fecha_fin del Caso.
    display_metadata.setdefault("mtd_fecha_fin", meta.get("fecha_fin_acumulado"))
    display_metadata.setdefault("fecha_inicio_acumulado", mtd_start)
    display_metadata.setdefault("fecha_fin_acumulado", end)
    _balance_update_headers_and_metadata(
        wb, display_metadata, start, end, mtd_start
    )
    _balance_enable_full_calculation(wb)
    current_cells = _balance_cell_snapshot(wb)
    changed_cells = {
        key for key, value in current_cells.items()
        if original_cells.get(key) != value
    }
    changed_formulas = [
        key for key in changed_cells
        if original_cells.get(key, (None, None))[1] == "f"
        or current_cells.get(key, (None, None))[1] == "f"
    ]
    if changed_formulas:
        raise BalanceReportError(
            "La exportacion intento modificar formulas protegidas: "
            + ", ".join(f"{sheet}!{cell}" for sheet, cell in changed_formulas)
        )
    staged = io.BytesIO()
    wb.save(staged)
    result = _balance_package_preserving_output(
        template_path, staged.getvalue(), changed_cells, start, end
    )
    print("[BALANCE EXPORT] validacion_ooxml=OK")
    return result


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


def _campos_incompletos_resumen_datos_conciliados(row: pd.Series) -> list[str]:
    """Devuelve los insumos MTD ausentes, respetando dependencias por tonelaje."""
    dependientes = {
        "Ley_CuT_Real": "Apilado_TMS_Real",
        "Cobre_fino_Apilado_Real": "Apilado_TMS_Real",
        "Ley_CuT_Plan": "Apilado_TMS_Plan",
        "Cobre_fino_Apilado_Plan": "Apilado_TMS_Plan",
        # Ley_CuT_Real_srr ya no esta en COLUMNAS_CORTE_RESUMEN_DATOS_CONCILIADOS
        # (ver comentario ahi), asi que esta entrada no se evalua para esa
        # columna. Se deja Plan por si el dia todavia no tiene tonelaje SRR.
        "Ley_CuT_Plan_srr": "SRR_TMS_Plan",
    }
    incompletos = []
    for columna in COLUMNAS_CORTE_RESUMEN_DATOS_CONCILIADOS:
        if columna in dependientes:
            tonelaje = pd.to_numeric(row[dependientes[columna]], errors="coerce")
            if pd.notna(tonelaje) and tonelaje == 0:
                continue
        if pd.isna(row[columna]):
            incompletos.append(columna)
    return incompletos


def _obtener_fecha_corte_resumen_datos_conciliados(df: pd.DataFrame):
    """Obtiene el fin del primer tramo diario completo del resumen MTD."""
    if df is None or df.empty:
        raise DependenciaDatosExportError(
            "No hay datos disponibles para determinar el corte del resumen MTD."
        )

    requeridas = ("Fecha", *COLUMNAS_CORTE_RESUMEN_DATOS_CONCILIADOS)
    faltantes = [columna for columna in requeridas if columna not in df.columns]
    if faltantes:
        raise DependenciaDatosExportError(
            "Faltan columnas requeridas para construir el resumen MTD.",
            campos=faltantes,
        )

    datos = df.copy()
    datos["Fecha"] = pd.to_datetime(datos["Fecha"], errors="coerce").dt.normalize()
    datos = datos.dropna(subset=["Fecha"]).sort_values("Fecha")
    datos = datos.drop_duplicates(subset=["Fecha"], keep="last")
    if datos.empty:
        raise DependenciaDatosExportError(
            "No existen fechas validas para determinar el corte del resumen MTD.",
            campos=["Fecha"],
        )

    fecha_anterior = None
    fecha_esperada = datos.iloc[0]["Fecha"]
    primera_fecha_incompleta = None
    primeros_campos_incompletos = []
    for _, row in datos.iterrows():
        fecha = row["Fecha"]
        if fecha != fecha_esperada:
            print(f"[DATOS_CONCILIADOS] Primera fecha incompleta: {fecha_esperada:%Y-%m-%d}")
            print("[DATOS_CONCILIADOS] Campos incompletos: Fecha")
            primera_fecha_incompleta = fecha_esperada
            primeros_campos_incompletos = ["Fecha"]
            break
        incompletos = _campos_incompletos_resumen_datos_conciliados(row)
        if incompletos:
            print(f"[DATOS_CONCILIADOS] Primera fecha incompleta: {fecha:%Y-%m-%d}")
            print("[DATOS_CONCILIADOS] Campos incompletos: " + ", ".join(incompletos))
            primera_fecha_incompleta = fecha
            primeros_campos_incompletos = incompletos
            break
        fecha_anterior = fecha
        fecha_esperada = fecha + pd.Timedelta(days=1)

    if fecha_anterior is None:
        raise DependenciaDatosExportError(
            "Datos Conciliados: no existe un tramo consecutivo completo desde "
            "la primera fecha exportada.",
            fecha=primera_fecha_incompleta,
            campos=primeros_campos_incompletos,
        )
    print(f"[DATOS_CONCILIADOS] Fecha corte resumen MTD: {fecha_anterior:%Y-%m-%d}")
    return fecha_anterior


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
    real_ton = pd.to_numeric(datos.get("Apilado_TMS_Real"), errors="coerce")
    real_ley = pd.to_numeric(datos.get("Ley_CuT_Real"), errors="coerce")
    ley_real = None
    if real_ton is not None and real_ley is not None and real_ton.notna().any():
        denominador_real = float(real_ton.sum(skipna=True))
        if denominador_real != 0:
            ley_real = float((real_ton * real_ley).sum(skipna=True)) / denominador_real
    plan_ton = pd.to_numeric(datos.get("Apilado_TMS_Plan"), errors="coerce")
    plan_ley = pd.to_numeric(datos.get("Ley_CuT_Plan"), errors="coerce")
    ley_plan = None
    if plan_ton is not None and plan_ley is not None and plan_ton.notna().any():
        denominador_plan = float(plan_ton.sum(skipna=True))
        if denominador_plan != 0:
            ley_plan = float((plan_ton * plan_ley).sum(skipna=True)) / denominador_plan
    cobre_plan = _suma_mtd(datos, "Cobre_fino_Apilado_Plan")

    total_camiones_real = _suma_mtd(datos, "Camiones_TMS_total")
    total_camiones_plan = _suma_mtd(datos, "Camiones_TMS_plan")
    total_ripios_real = _suma_mtd(datos, "Total_Ripios_Incluye_Camiones_Real")
    total_ripios_plan = _suma_mtd(datos, "Total_Ripios_Incluye_Camiones_Plan")
    rotopala_real = (
        None if total_ripios_real is None or total_camiones_real is None
        else total_ripios_real - total_camiones_real
    )
    rotopala_plan = (
        None if total_ripios_plan is None or total_camiones_plan is None
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
        ws["Z3"] = (
            f"MTD {MESES_ES[fecha.month - 1]} {fecha.year} "
            f"al {fecha:%d-%m-%Y}"
        )
    for indicador, row in FILAS_RESUMEN_MTD.items():
        resultado = resumen_mtd[indicador]
        for col, clave in zip(("AB", "AC", "AD", "AE"), (
            "real", "plan", "varianza", "diferencia",
        )):
            valor = resultado[clave]
            ws[f"{col}{row}"] = None if pd.isna(valor) else float(valor)


def _actualizar_encabezado_datos_conciliados(
    ws, df: pd.DataFrame, fecha_reporte=None,
):
    """Actualiza los metadatos desde la misma fecha usada por el resumen MTD."""
    if fecha_reporte is None:
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
    ws["Z3"] = (
        f"MTD {MESES_ES[fecha_reporte.month - 1]} {fecha_reporte.year} "
        f"al {fecha_reporte:%d-%m-%Y}"
    )
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


def aplicar_formato_datos_conciliados(
    ws,
    cantidad_dias_mes: int,
    *,
    rango_personalizado: bool = False,
    cantidad_filas_reporte: int | None = None,
) -> None:
    """Aplica la presentación oficial, compactando solo rangos personalizados."""
    for column, width in ANCHOS_DATOS_CONCILIADOS.items():
        ws.column_dimensions[column].width = width

    for row, height in ALTURAS_DATOS_CONCILIADOS.items():
        ws.row_dimensions[row].height = height
    filas_visibles = (
        max(int(cantidad_filas_reporte or 0), 0)
        if rango_personalizado
        else min(max(cantidad_dias_mes, 0), 31)
    )
    ultima_fila_datos = 20 + filas_visibles
    fila_cierre = max(21, ultima_fila_datos + 1)

    for row in range(21, 52):
        ws.row_dimensions[row].height = 13.8
        ws.row_dimensions[row].hidden = bool(
            rango_personalizado and row > fila_cierre
        )
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

    # El bloque P10:R11 era una tabla auxiliar vacía heredada de la plantilla.
    # Se elimina por completo para que no deje combinaciones, bordes ni rellenos
    # dentro de la salida oficial.
    default_style = copy_module.copy(ws["A1"]._style)
    for row in ws["P10:R11"]:
        for cell in row:
            cell.value = None
            cell._style = copy_module.copy(default_style)

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
    ultima_fila_formato = ultima_fila_datos if rango_personalizado else 51
    for row in range(21, ultima_fila_formato + 1):
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

    # Mes completo conserva los 31 espacios oficiales. Un rango personalizado
    # muestra solo sus datos y la fila de cierre inmediatamente inferior.
    for row in range(21, min(fila_cierre, 51) + 1):
        ws.row_dimensions[row].hidden = False

    ws.freeze_panes = None
    # openpyxl quita el <pane> al asignar freeze_panes = None, pero no
    # limpia las <selection pane="topRight" .../> que la plantilla traia
    # apuntando a ese pane inmovilizado. El archivo queda con selecciones
    # que referencian un pane inexistente: XML valido contra el schema y
    # abre sin problema en LibreOffice/openpyxl, pero Excel lo detecta como
    # contenido no reconocido y ofrece "reparar" el archivo. Se reemplaza
    # por una unica seleccion por defecto, sin pane, cada vez que se quita
    # el freeze.
    ws.sheet_view.selection = (Selection(),)
    ws.sheet_view.showGridLines = False
    # AY se mantiene con su ancho original para no alterar la escala ni la
    # posición visual del logo, pero el estado no se imprime en sus celdas.
    ws.column_dimensions["AY"].hidden = False
    ws.print_area = (
        f"B2:AY{fila_cierre}"
        if rango_personalizado
        else "B2:AY52"
    )
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
    """Normaliza a ARGB opaco los colores RGB con alfa transparente (00).

    Antes esta funcion tambien compactaba cellXfs/fonts/fills/borders,
    reescribiendo sheet1.xml y styles.xml completos con
    xml.etree.ElementTree (parse + tostring). Se detecto que ese
    roundtrip -- aunque produce XML valido contra el schema de
    SpreadsheetML y semanticamente identico celda a celda (se verifico
    fuente, relleno, borde y formato de cada celda contra la version sin
    compactar, cero diferencias) -- de todas formas dispara el aviso de
    "contenido irrecuperable" de Excel al abrir el archivo: la
    reserializacion de ElementTree no reproduce byte a byte la forma en
    que openpyxl escribe el XML, y Excel es mas estricto que el XSD, que
    LibreOffice y que el propio openpyxl al respecto.
    La compactacion tampoco es necesaria a esta escala: un reporte
    mensual completo genera unos pocos cientos de cellXfs (~300), muy por
    debajo del limite real de Excel (64.000). Por eso ahora se hace
    unicamente el reemplazo puntual del atributo rgb sobre los bytes
    originales de styles.xml, sin tocar el resto de la estructura del
    XML ni reserializar nada con ElementTree.
    """
    source = io.BytesIO(xlsx_bytes)
    files = {}
    infos = {}
    with ZipFile(source, "r") as archive:
        for info in archive.infolist():
            infos[info.filename] = info
            files[info.filename] = archive.read(info.filename)

    if "xl/styles.xml" in files:
        files["xl/styles.xml"] = re.sub(
            rb'rgb="00([0-9A-Fa-f]{6})"',
            rb'rgb="FF\1"',
            files["xl/styles.xml"],
        )

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


def _validar_factor_ajuste_camiones(
    df_datos_conciliados: pd.DataFrame,
    df_factor: pd.DataFrame,
) -> None:
    """Valida la cobertura y trazabilidad del factor oficial a exportar."""
    if df_factor is None:
        raise ValueError("El DataFrame del factor de ajuste no puede ser None.")
    if df_factor.empty:
        raise ValueError("No existen datos del factor de ajuste para el reporte.")

    requeridas = {
        "Fecha", "Factor_Aplicacion_Reportes", "Flag_Factor_Ajuste_Valido",
        "Estado_Calculo", "Regla_Aplicacion", "Factor_Ajuste_Calculado",
        "Factor_Aplicacion_Automatica", "Modo_Aplicacion", "Regla_Aplicacion_Automatica",
        "Id_Control_Aplicacion", "Control_Aplicacion_Motivo",
        "Control_Aplicacion_Usuario", "Control_Aplicacion_Fecha_Registro",
        "Apilado_TMH_Bruto_Ajustado", "Chancado_TMH_Sin_Ajuste", "Chancado_TMS_Sin_Ajuste",
        "Chancado_TMH_Con_Ajuste", "Chancado_TMS_Con_Ajuste",
        "Carga_KOM_TMH_Viaje_Sin_Ajuste", "Carga_CAT_TMH_Viaje_Sin_Ajuste",
        "Carga_KOM_TMH_Viaje_Con_Ajuste", "Carga_CAT_TMH_Viaje_Con_Ajuste",
        "Vueltas_KOM", "Vueltas_CAT",
    }
    faltantes = sorted(requeridas.difference(df_factor.columns))
    if faltantes:
        raise ValueError(
            "Faltan columnas indispensables del factor de ajuste: "
            + ", ".join(faltantes)
        )

    fechas_factor = pd.to_datetime(df_factor["Fecha"], errors="coerce").dt.normalize()
    if fechas_factor.isna().any():
        raise ValueError("El factor de ajuste contiene fechas nulas o inválidas.")
    if fechas_factor.duplicated().any():
        raise ValueError("El factor de ajuste contiene más de una fila por Fecha.")

    if "Fecha" not in df_datos_conciliados.columns:
        raise ValueError("Datos Conciliados no contiene la columna Fecha.")
    fechas_reporte = pd.to_datetime(
        df_datos_conciliados["Fecha"], errors="coerce"
    ).dt.normalize()
    if fechas_reporte.isna().any():
        raise ValueError("Datos Conciliados contiene fechas nulas o inválidas.")
    # Datos Conciliados puede incluir el resto del mes con valores planificados,
    # mientras que la vista del factor solo publica días ya calculados. Se exige
    # cobertura hasta el último día efectivamente disponible en esa vista; las
    # fechas posteriores no deben bloquear el Excel ni recibir factores ficticios.
    fecha_maxima_factor = fechas_factor.max()
    fechas_operacionales = fechas_reporte[fechas_reporte <= fecha_maxima_factor]
    faltan_fechas = fechas_operacionales[
        ~fechas_operacionales.isin(fechas_factor)
    ].drop_duplicates()
    if not faltan_fechas.empty:
        raise ValueError(
            "Falta el factor de ajuste para las fechas: "
            + ", ".join(faltan_fechas.dt.strftime("%d-%m-%Y"))
        )

    filas_reporte = df_factor.loc[fechas_factor.isin(fechas_operacionales)]
    for columna in (
        "Factor_Aplicacion_Reportes", "Factor_Aplicacion_Automatica",
        "Modo_Aplicacion", "Regla_Aplicacion_Automatica", "Estado_Calculo", "Regla_Aplicacion",
    ):
        if filas_reporte[columna].isna().any():
            raise ValueError(
                f"{columna} contiene valores NULL para fechas del reporte."
            )


def _agregar_hoja_factor_ajuste_camiones(
    wb,
    df_factor: pd.DataFrame,
) -> None:
    """Agrega el factor de camiones con el formato operacional de referencia."""
    nombre_hoja = "Factor ajuste camiones"
    if nombre_hoja in wb.sheetnames:
        del wb[nombre_hoja]
    ws = wb.create_sheet(nombre_hoja)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    columnas = (
        ("Fecha", "Fecha"),
        ("Chancado TMH sin ajuste", "Chancado_TMH_Sin_Ajuste"),
        ("TMH corregido automático KOM/CAT", "Chancado_TMH_Con_Ajuste"),
        ("Factor calculado", "Factor_Ajuste_Calculado"),
        ("Apilado TMH bruto automático", "Apilado_TMH_Bruto_Ajustado"),
        ("Chancado TMS automático", "Chancado_TMS_Con_Ajuste"),
        ("Factor aplicado", "Factor_Aplicacion_Reportes"),
        ("Modo aplicación", "Modo_Aplicacion"),
        ("Carga KOM sin ajuste [TMH/viaje]", "Carga_KOM_TMH_Viaje_Sin_Ajuste"),
        ("Carga KOM corregida [TMH/viaje]", "Carga_KOM_TMH_Viaje_Con_Ajuste"),
        ("Vueltas KOM", "Vueltas_KOM"),
        ("Carga CAT sin ajuste [TMH/viaje]", "Carga_CAT_TMH_Viaje_Sin_Ajuste"),
        ("Carga CAT corregida [TMH/viaje]", "Carga_CAT_TMH_Viaje_Con_Ajuste"),
        ("Vueltas CAT", "Vueltas_CAT"),
    )
    borde_fino = Side(style="thin", color="000000")
    borde_tabla = Border(
        left=borde_fino, right=borde_fino,
        top=borde_fino, bottom=borde_fino,
    )
    color_texto = "476475"
    relleno_blanco = PatternFill("solid", fgColor="FFFFFF")
    relleno_alterno = PatternFill("solid", fgColor="D7E1E7")
    for indice, (encabezado, _) in enumerate(columnas, start=1):
        celda = ws.cell(1, indice, encabezado)
        celda.font = Font(name="Arial", size=11, bold=True, color=color_texto)
        celda.fill = relleno_blanco
        celda.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        celda.border = borde_tabla
    ws.row_dimensions[1].height = 72
    from openpyxl.comments import Comment
    ws["C1"].comment = Comment("Diagnóstico automático. La suma corregida de flotas no es la conversión húmeda del balance TMS. Celdas vacías: no evaluable o sin dato de origen.", "SIIR")

    for fila_excel, (_, fila) in enumerate(df_factor.iterrows(), start=2):
        for col_excel, (_, columna_fuente) in enumerate(columnas, start=1):
            valor = fila[columna_fuente] if columna_fuente in df_factor.columns else None
            if pd.isna(valor):
                valor = None
            elif columna_fuente in {"Fecha", "Fecha_Calculo", "Control_Aplicacion_Fecha_Registro"} and hasattr(valor, "to_pydatetime"):
                valor = valor.to_pydatetime()
            celda = ws.cell(fila_excel, col_excel, valor)
            celda.font = Font(
                name="Arial",
                size=11 if col_excel == 1 else 10,
                color=color_texto,
            )
            celda.fill = (
                relleno_blanco if fila_excel % 2 == 0 else relleno_alterno
            )
            celda.alignment = Alignment(horizontal="center", vertical="center")
            celda.border = borde_tabla

    ultima_fila = max(2, 1 + len(df_factor))
    for fila in range(2, ultima_fila + 1):
        ws.cell(fila, 1).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(fila, 1).number_format = "dd/mm/yyyy"
        for col in (2, 3, 5, 6, 9, 10, 12, 13):
            ws.cell(fila, col).number_format = "#,##0.000"
        for col in (4, 7):
            ws.cell(fila, col).number_format = "0.000000"
        for col in (11, 14):
            ws.cell(fila, col).number_format = "0"

    anchos = (14, 20, 28, 16, 23, 28, 18, 20, 23, 23, 12, 23, 23, 12)
    for indice, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(indice)].width = ancho


def _validar_balance_chancado(df_balance: pd.DataFrame) -> None:
    """Valida estructura, fechas y unicidad del balance."""
    if df_balance is None:
        raise ValueError("El DataFrame de Balance Chancado no puede ser None.")
    if df_balance.empty:
        raise ValueError("No existen datos de Balance Chancado para el reporte.")

    requeridas = {
        "Fecha", "Humedad", "Mineral_Apilado_TMH_Original", "Factor_Ajuste",
        "Mineral_Apilado_TMH_Ajustado", "Delta_Ajuste_TMH",
        "Apilado_TMS_Reporte", "Delta_Inventario_Chancado_TMS", "Sal_TMH_Dia",
        "SRR_TMS_Dia", "Chancado_TMS_Reporte", "Chancado_TMS_Real",
        "Diferencia_vs_Datos_Conciliados", "Modo_Aplicacion", "Regla_Aplicacion",
        "Material", "Nivel_Promedio_Chancado", "Nivel_Promedio_Harneros",
        "Nivel_Promedio_Silo", "Bin_Chancado", "Bin_Harneros",
        "Tolva_Compensacion", "Silo", "Inventario_Chancado_TMH",
        "Inventario_Silo_TMH", "Total_TMH", "Inventario_Chancado_TMS",
        "Inventario_Silo_TMS", "Total_TMS",
        "Nivel_Harnero_A", "Nivel_Harnero_B", "Nivel_Harnero_C",
        "Nivel_Harnero_D", "Nivel_Harnero_E", "Nivel_Chancado_A",
        "Nivel_Chancado_B", "Nivel_Chancado_C", "Nivel_Chancado_D",
        "Nivel_Chancado_E", "Nivel_Silo_A", "Nivel_Silo_B",
    }
    faltantes = sorted(requeridas.difference(df_balance.columns))
    if faltantes:
        raise ValueError(
            "Faltan columnas indispensables de Balance Chancado: "
            + ", ".join(faltantes)
        )

    fechas = pd.to_datetime(df_balance["Fecha"], errors="coerce").dt.normalize()
    if fechas.isna().any():
        raise ValueError("Balance Chancado contiene fechas nulas o inválidas.")
    if fechas.duplicated().any():
        raise ValueError("Balance Chancado contiene más de una fila por Fecha.")
    df_balance["Fecha"] = fechas
    df_balance.sort_values("Fecha", kind="stable", inplace=True)
    df_balance.reset_index(drop=True, inplace=True)

    def numero(nombre):
        return pd.to_numeric(df_balance[nombre], errors="coerce")

    def comprobar(variable, esperado, insumos, tolerancia):
        obtenido = numero(variable)
        evaluables = obtenido.notna() & esperado.notna()
        for campo in insumos:
            evaluables &= numero(campo).notna()
        for indice in df_balance.index[evaluables]:
            exp, real = float(esperado.loc[indice]), float(obtenido.loc[indice])
            diferencia = real - exp
            if not math.isfinite(exp) or not math.isfinite(real) or abs(diferencia) > tolerancia:
                fecha = df_balance.loc[indice, "Fecha"]
                raise ValueError(
                    f"{fecha:%d-%m-%Y}: {variable}; esperado={exp:.12g}; "
                    f"obtenido={real:.12g}; diferencia={diferencia:.12g}; "
                    f"tolerancia={tolerancia:g}."
                )

    comprobar("Mineral_Apilado_TMH_Ajustado",
              numero("Mineral_Apilado_TMH_Original") * numero("Factor_Ajuste"),
              ["Mineral_Apilado_TMH_Original", "Factor_Ajuste"], 0.01)
    comprobar("Delta_Ajuste_TMH",
              numero("Mineral_Apilado_TMH_Ajustado") - numero("Mineral_Apilado_TMH_Original"),
              ["Mineral_Apilado_TMH_Ajustado", "Mineral_Apilado_TMH_Original"], 0.01)
    comprobar("Chancado_TMS_Reporte",
              numero("Apilado_TMS_Reporte") + numero("Delta_Inventario_Chancado_TMS") - numero("SRR_TMS_Dia"),
              ["Apilado_TMS_Reporte", "Delta_Inventario_Chancado_TMS", "SRR_TMS_Dia"], 0.01)
    comprobar("Chancado_TMS_Real", numero("Chancado_TMS_Reporte"),
              ["Chancado_TMS_Reporte"], 0.000001)
    comprobar("Diferencia_vs_Datos_Conciliados",
              numero("Chancado_TMS_Reporte") - numero("Chancado_TMS_Real"),
              ["Chancado_TMS_Reporte", "Chancado_TMS_Real"], 0.000001)


def _agregar_hoja_balance_chancado(wb, df_balance: pd.DataFrame) -> None:
    """Agrega las tablas superiores diarias de Balance Chancado."""
    nombre_hoja = "Balance Chancado"
    if nombre_hoja in wb.sheetnames:
        del wb[nombre_hoja]
    ws = wb.create_sheet(title=nombre_hoja, index=1)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = None

    columnas = (
        ("Fecha", "Fecha"), ("Humedad", "Humedad"),
        ("Apilado TMH bruto original", "Mineral_Apilado_TMH_Original"),
        ("Factor aplicado", "Factor_Ajuste"),
        ("Apilado TMH bruto aplicado", "Mineral_Apilado_TMH_Ajustado"),
        ("Delta TMH aplicado", "Delta_Ajuste_TMH"),
        ("Apilado TMS neto aplicado", "Apilado_TMS_Reporte"),
        ("Variación inventario TMS", "Delta_Inventario_Chancado_TMS"),
        ("Sal", "Sal_TMH_Dia"),
        ("SRR TMS Balance", "SRR_TMS_Dia"),
        ("Chancado TMS", "Chancado_TMS_Real"),
        ("Modo aplicación", "Modo_Aplicacion"),
        ("Material", "Material"),
        ("Nivel promedio Chancado", "Nivel_Promedio_Chancado"),
        ("Nivel promedio Harneros", "Nivel_Promedio_Harneros"),
        ("Nivel promedio Silo", "Nivel_Promedio_Silo"),
        ("Bin Chancado", "Bin_Chancado"), ("Bin Harneros", "Bin_Harneros"),
        ("Tolva Compensación", "Tolva_Compensacion"), ("Silo", "Silo"),
        ("Inventario Chancado TMH", "Inventario_Chancado_TMH"),
        ("Inventario Silo TMH", "Inventario_Silo_TMH"),
        ("Total TMH", "Total_TMH"),
        ("Inventario Chancado TMS", "Inventario_Chancado_TMS"),
        ("Inventario Silo TMS", "Inventario_Silo_TMS"),
        ("Total TMS", "Total_TMS"),
        ("Harnero A", "Nivel_Harnero_A"), ("Harnero B", "Nivel_Harnero_B"),
        ("Harnero C", "Nivel_Harnero_C"), ("Harnero D", "Nivel_Harnero_D"),
        ("Harnero E", "Nivel_Harnero_E"),
        ("Chancado A", "Nivel_Chancado_A"),
        ("Chancado B", "Nivel_Chancado_B"),
        ("Chancado C", "Nivel_Chancado_C"),
        ("Chancado D", "Nivel_Chancado_D"),
        ("Chancado E", "Nivel_Chancado_E"),
        ("Silo A", "Nivel_Silo_A"), ("Silo B", "Nivel_Silo_B"),
    )
    grupos = (
        ("A4:M4", "Balance diario — ruta aplicada"), ("N4:P4", "Niveles promedio"),
        ("Q4:Z4", "Inventarios"), ("AA4:AE4", "Niveles Harneros"),
        ("AF4:AJ4", "Niveles Chancado"), ("AK4:AL4", "Niveles Silo"),
    )
    color_texto = "476475"
    relleno_azul = PatternFill("solid", fgColor="D7E1E7")
    relleno_blanco = PatternFill("solid", fgColor="FFFFFF")
    relleno_oxido = PatternFill("solid", fgColor="FCE4D6")
    relleno_sulfuro = PatternFill("solid", fgColor="E2F0D9")
    lado = Side(style="thin", color="808080")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)

    ws.merge_cells("A1:AL1")
    ws["A1"] = "Balance Chancado"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color=color_texto)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("A2:AL2")
    ws["A2"] = "Ruta aplicada. Apilado TMS ya neto de sal: Chancado = Apilado neto + variación inventario − SRR físico. Celdas vacías: no evaluable."
    ws["A2"].font = Font(name="Arial", size=9, italic=True, color=color_texto)
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    for rango, etiqueta in grupos:
        ws.merge_cells(rango)
        celda = ws[rango.split(":")[0]]
        celda.value = etiqueta
        celda.font = Font(name="Arial", bold=True, color=color_texto)
        celda.fill = relleno_azul
        celda.alignment = Alignment(horizontal="center", vertical="center")
        for fila in ws[rango]:
            for item in fila:
                item.fill = relleno_azul
                item.border = borde

    for col_excel, (encabezado, _) in enumerate(columnas, start=1):
        celda = ws.cell(5, col_excel, encabezado)
        celda.font = Font(name="Arial", bold=True, color=color_texto)
        celda.fill = relleno_azul
        celda.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        celda.border = borde

    for fila_excel, (_, fila) in enumerate(df_balance.iterrows(), start=6):
        valor_material = fila.get("Material")
        material = (
            ""
            if pd.isna(valor_material)
            else str(valor_material).strip().upper()
        )
        material = (
            material.replace("Á", "A")
            .replace("É", "E")
            .replace("Í", "I")
            .replace("Ó", "O")
            .replace("Ú", "U")
        )
        if material in {"OXIDO", "OXIDOS"}:
            relleno_fila = relleno_oxido
        elif material in {"SULFURO", "SULFUROS"}:
            relleno_fila = relleno_sulfuro
        else:
            relleno_fila = (
                relleno_blanco if fila_excel % 2 == 0 else relleno_azul
            )

        for col_excel, (_, fuente) in enumerate(columnas, start=1):
            valor = fila[fuente]
            if pd.isna(valor):
                valor = None
            elif fuente == "Fecha" and hasattr(valor, "to_pydatetime"):
                valor = valor.to_pydatetime()
            celda = ws.cell(fila_excel, col_excel, valor)
            celda.font = Font(name="Arial", size=10, color=color_texto)
            celda.fill = relleno_fila
            celda.alignment = Alignment(horizontal="center", vertical="center")
            celda.border = borde
        ws.row_dimensions[fila_excel].height = 20

    ultima_fila = 5 + len(df_balance)
    for fila in range(6, ultima_fila + 1):
        ws.cell(fila, 1).number_format = "dd-mm-yyyy"
        ws.cell(fila, 2).number_format = "0.000"
        ws.cell(fila, 4).number_format = "0.000000"
        for col in (3, *range(5, 12), *range(17, 27)):
            ws.cell(fila, col).number_format = "#,##0.000"
        for col in (*range(14, 17), *range(27, 39)):
            ws.cell(fila, col).number_format = "0.00"

    anchos = (13, 10, 22, 15, 22, 18, 22, 22, 14, 24, 22, 20, 12) + (17,) * 3 + (16,) * 10 + (12,) * 12
    for indice, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(indice)].width = ancho
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 60
    ws.auto_filter.ref = f"A5:AL{ultima_fila}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:AL{ultima_fila}"

    relleno_ajuste_manual = PatternFill("solid", fgColor="D7E1E7")
    fuente_ajuste_manual = Font(
        name="Arial", size=11, bold=True, color="476475"
    )
    alineacion_ajuste_manual = Alignment(
        horizontal="center", vertical="center"
    )
    lado_ajuste_manual = Side(style="medium", color="000000")
    borde_ajuste_manual = Border(
        left=lado_ajuste_manual,
        right=lado_ajuste_manual,
        top=lado_ajuste_manual,
        bottom=lado_ajuste_manual,
    )
    for fila in range(39, 44):
        celda = ws.cell(fila, 9)
        celda.value = None
        celda.fill = relleno_ajuste_manual
        celda.font = fuente_ajuste_manual
        celda.alignment = alineacion_ajuste_manual
        celda.border = borde_ajuste_manual
        celda.number_format = "#,##0.00"


def _agregar_hoja_datos_correo(wb, df: pd.DataFrame, fecha_corte) -> None:
    """Agrega un resumen autocontenido listo para copiar en un correo."""
    nombre_hoja = "Datos para correo"
    if nombre_hoja in wb.sheetnames:
        del wb[nombre_hoja]
    ws = wb.create_sheet(title=nombre_hoja)
    ws.sheet_view.showGridLines = False

    datos_correo = df.copy()
    datos_correo["Fecha"] = pd.to_datetime(
        datos_correo["Fecha"], errors="coerce"
    ).dt.normalize()
    fecha_corte = pd.Timestamp(fecha_corte).normalize()
    datos_correo = datos_correo[datos_correo["Fecha"] <= fecha_corte].copy()
    inicio_mes = fecha_corte.replace(day=1)
    datos_mtd = datos_correo[datos_correo["Fecha"] >= inicio_mes]

    def ultimo_avance(campana, modulo, avance):
        columnas = ["Fecha", campana, modulo, avance]
        if any(columna not in datos_correo.columns for columna in columnas):
            return None
        candidatos = datos_correo[columnas].copy()
        candidatos[avance] = pd.to_numeric(candidatos[avance], errors="coerce")
        validos = (
            candidatos["Fecha"].notna()
            & candidatos[campana].notna()
            & candidatos[modulo].notna()
            & candidatos[avance].notna()
            & candidatos[campana].astype(str).str.strip().ne("")
            & candidatos[modulo].astype(str).str.strip().ne("")
        )
        candidatos = candidatos.loc[validos].sort_values(
            "Fecha", kind="stable"
        )
        if candidatos.empty:
            return None
        fila = candidatos.iloc[-1]
        valor_avance = float(fila[avance])
        if valor_avance > 1:
            valor_avance /= 100
        return fila[campana], fila[modulo], valor_avance

    def texto_avance(etiqueta, resultado, material=None):
        if resultado is None:
            return f"{etiqueta}: sin información disponible"
        campana, modulo, avance = resultado
        material_mostrado = material or str(campana).strip()
        modulo_mostrado = str(modulo).strip()
        if isinstance(modulo, (int, float)) and not pd.isna(modulo):
            modulo_mostrado = f"{modulo:g}"
        return (
            f"{etiqueta}: {avance:.0%} del Módulo {modulo_mostrado} "
            f"{material_mostrado}"
        )

    def suma_columna(datos, columna):
        if columna not in datos.columns:
            return 0.0
        return float(pd.to_numeric(datos[columna], errors="coerce").sum())

    def valor_diario(columna):
        datos_dia = datos_correo[datos_correo["Fecha"] == fecha_corte]
        return suma_columna(datos_dia, columna)

    def formato_entero(valor):
        return f"{valor:,.0f}".replace(",", ".")

    apilamiento = ultimo_avance(
        "Campana_apilado", "Modulo_apilado", "Avance_apilado"
    )
    rotopala_1 = ultimo_avance(
        "Campana_reclamo_oxidos",
        "Modulo_reclamo_oxidos",
        "Avance_reclamo_oxidos",
    )
    rotopala_2 = ultimo_avance(
        "Campana_reclamo_sulfuros",
        "modulo_reclamo_sulfuros",
        "Avance_reclamo_sulfuros",
    )

    catodos_diario = valor_diario("Produccion_Catodos_Real")
    catodos_mtd = suma_columna(datos_mtd, "Produccion_Catodos_Real")
    apilado_diario = valor_diario("Apilado_TMS_Real")
    apilado_mtd = suma_columna(datos_mtd, "Apilado_TMS_Real")
    chancado_mtd = suma_columna(datos_mtd, "Chancado_TMS_Real")
    srr_mtd = suma_columna(datos_mtd, "SRR_TMS_promedio_dia")
    check_balance = chancado_mtd - (apilado_mtd - srr_mtd)

    fecha_larga = (
        f"{fecha_corte.day} de {MESES_ES[fecha_corte.month - 1]}, "
        f"{fecha_corte.year}"
    )
    fecha_compacta = (
        f"{fecha_corte.day} {MESES_ES[fecha_corte.month - 1]} "
        f"{fecha_corte.year}"
    )
    textos = {
        3: "Adjunto Producciones Conciliadas.",
        4: f"Chancado, Apilado y Ripios al {fecha_larga}.",
        5: "(Avance, de apilador y rotopala, tomado por geomensura)",
        6: f"Cátodos al {fecha_larga}.",
        8: f"Avances al {fecha_compacta}:",
        9: texto_avance("Apilamiento", apilamiento),
        10: texto_avance("Ripios Rotopala 1", rotopala_1, "Óxido"),
        11: texto_avance("Ripios Rotopala 2", rotopala_2, "Sulfuro"),
        13: "Producción:",
        14: (
            "Producción de Cátodos [t] diario / mensual "
            f"({fecha_compacta}): {formato_entero(catodos_diario)} / "
            f"{formato_entero(catodos_mtd)}"
        ),
        15: (
            f"Apilado [t] diario / mensual ({fecha_compacta}): "
            f"{formato_entero(apilado_diario)} / {formato_entero(apilado_mtd)}"
        ),
    }

    color_texto = "476475"
    relleno_titulo = PatternFill("solid", fgColor="D7E1E7")
    relleno_claro = PatternFill("solid", fgColor="F3F6F8")
    lado = Side(style="thin", color="B7C5CD")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)

    ws.merge_cells("A1:H1")
    ws["A1"] = nombre_hoja
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color=color_texto)
    ws["A1"].fill = relleno_titulo
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    for fila, texto in textos.items():
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=8)
        celda = ws.cell(fila, 1, texto)
        celda.font = Font(
            name="Arial", size=10, color=color_texto,
            bold=fila in {3, 8, 13}, italic=fila == 5,
        )
        celda.alignment = Alignment(vertical="center", wrap_text=True)

    ws.merge_cells("J3:M3")
    ws["J3"] = "Resumen de datos"
    ws["J3"].font = Font(name="Arial", size=11, bold=True, color=color_texto)
    ws["J3"].fill = relleno_titulo
    ws["J3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("J4:M4")
    ws["J4"] = f"Check balance: {formato_entero(check_balance)} t"
    ws["J4"].font = Font(name="Arial", size=11, bold=True, color=color_texto)
    ws["J4"].fill = relleno_claro
    ws["J4"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("J5:M6")
    ws["J5"] = "Nota: este valor no puede ser mayor a 3.000 ton."
    ws["J5"].font = Font(name="Arial", size=9, italic=True, color=color_texto)
    ws["J5"].alignment = Alignment(
        horizontal="center", vertical="center", wrap_text=True
    )
    for rango in ("A1:H1", "J3:M3", "J4:M4", "J5:M6"):
        for fila in ws[rango]:
            for celda in fila:
                celda.border = borde

    for columna in range(1, 9):
        ws.column_dimensions[get_column_letter(columna)].width = 14
    ws.column_dimensions["I"].width = 3
    for columna in range(10, 14):
        ws.column_dimensions[get_column_letter(columna)].width = 14
    ws.row_dimensions[1].height = 24
    for fila in (4, 5, 6, 9, 10, 11, 14, 15):
        ws.row_dimensions[fila].height = 22


def export_datos_conciliados_to_template(
    df: pd.DataFrame,
    template_path: str,
    df_factor_ajuste: pd.DataFrame | None = None,
    df_balance_chancado: pd.DataFrame | None = None,
    rango_personalizado: bool = False,
    df_resumen_mtd: pd.DataFrame | None = None,
) -> bytes:
    """
    Escribe los datos del reporte 'Datos conciliados' en la plantilla Excel.
    - Datos desde el inicio de la tabla detectado en la plantilla.
    - Se escriben todas las columnas recibidas por el reporte.
    - Se copia el estilo (relleno, borde, fuente) de las dos primeras filas a todas
      las filas de datos para que la tabla crezca sin romper la estructura.
    """
    # Fallar antes de construir el workbook, sin recalcular reglas de aplicación.
    if df_balance_chancado is not None:
        _validar_balance_chancado(df_balance_chancado)
    if df_factor_ajuste is not None:
        _validar_factor_ajuste_camiones(df, df_factor_ajuste)
    df_export = df
    df_base_resumen = df_resumen_mtd if df_resumen_mtd is not None else df_export
    fecha_corte_resumen = _obtener_fecha_corte_resumen_datos_conciliados(
        df_base_resumen
    )
    fechas_resumen = pd.to_datetime(
        df_base_resumen["Fecha"], errors="coerce"
    ).dt.normalize()
    df_resumen = df_base_resumen[
        fechas_resumen <= fecha_corte_resumen
    ].copy()

    wb = _load_template(template_path)
    ws = wb.active
    ws.title = "Generador Reporte Diario"
    fecha_actualizacion = _actualizar_encabezado_datos_conciliados(
        ws, df_resumen, fecha_corte_resumen,
    )
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
            # Estado es un dato de control interno y no se muestra en la salida
            # oficial. Antes, 0/NULL se convertía en "*" dentro de AY.
            if col == "Estado":
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

    resumen_mtd = calcular_resumen_mtd(df_resumen, fecha_corte_resumen)
    escribir_resumen_mtd(ws, resumen_mtd, fecha_actualizacion)

    if fecha_actualizacion is not None:
        cantidad_dias_mes = calendar.monthrange(
            fecha_actualizacion.year, fecha_actualizacion.month,
        )[1]
    else:
        cantidad_dias_mes = min(len(df), 31)
    aplicar_formato_datos_conciliados(
        ws,
        cantidad_dias_mes,
        rango_personalizado=rango_personalizado,
        cantidad_filas_reporte=len(df),
    )
    if not rango_personalizado:
        aplicar_borde_inferior_reporte(
            ws,
            fila_inicio_datos=start_row,
            fila_fin_mes=start_row + cantidad_dias_mes - 1,
            columna_inicio=start_col,
            columna_fin=start_col + num_cols - 2,  # C:AX; AY es indicador lateral.
        )

    if df_balance_chancado is not None:
        _agregar_hoja_balance_chancado(wb, df_balance_chancado)

    if df_factor_ajuste is not None:
        _agregar_hoja_factor_ajuste_camiones(wb, df_factor_ajuste)

    _agregar_hoja_datos_correo(wb, df_resumen, fecha_corte_resumen)

    out = io.BytesIO()
    wb.save(out)
    return _normalizar_y_compactar_estilos_xlsx(out.getvalue())
