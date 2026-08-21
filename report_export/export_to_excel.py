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
from openpyxl.worksheet.views import Selection
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
        "Estado_Calculo", "Regla_Aplicacion",
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
        "Factor_Aplicacion_Reportes", "Estado_Calculo", "Regla_Aplicacion",
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
        ("TMH Sin ajuste", "Chancado_TMH_Sin_Ajuste"),
        ("TMS Sin ajuste", "Chancado_TMS_Sin_Ajuste"),
        ("TMH Con ajuste", "Chancado_TMH_Con_Ajuste"),
        ("TMS Con ajuste", "Chancado_TMS_Con_Ajuste"),
        ("Factor de Carga KOM Sin ajuste", "Carga_KOM_TMH_Viaje_Sin_Ajuste"),
        ("Factor de Carga CAT Sin ajuste", "Carga_CAT_TMH_Viaje_Sin_Ajuste"),
        ("Factor de Carga KOM con ajuste", "Carga_KOM_TMH_Viaje_Con_Ajuste"),
        ("Factor de Carga CAT con ajuste", "Carga_CAT_TMH_Viaje_Con_Ajuste"),
        ("Factor ajuste", "Factor_Ajuste_Calculado"),
        ("n° vueltas KOM", "Vueltas_KOM"),
        ("n° vueltas CAT", "Vueltas_CAT"),
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
    ws.row_dimensions[1].height = 57.6

    for fila_excel, (_, fila) in enumerate(df_factor.iterrows(), start=2):
        for col_excel, (_, columna_fuente) in enumerate(columnas, start=1):
            valor = fila[columna_fuente] if columna_fuente in df_factor.columns else None
            if pd.isna(valor):
                valor = None
            elif columna_fuente in {"Fecha", "Fecha_Calculo"} and hasattr(valor, "to_pydatetime"):
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
        for col in range(2, 10):
            ws.cell(fila, col).number_format = "#,##0"
        ws.cell(fila, 10).number_format = "0.00"
        for col in (11, 12):
            ws.cell(fila, col).number_format = "0"

    anchos = (13.8, 12, 12, 12, 12, 15, 15, 15, 15, 10, 9, 9)
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
        "Mineral_Chancado_Balance",
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

    originales = pd.to_numeric(
        df_balance["Mineral_Apilado_TMH_Original"], errors="coerce"
    )
    ajustados = pd.to_numeric(
        df_balance["Mineral_Apilado_TMH_Ajustado"], errors="coerce"
    )
    deltas = pd.to_numeric(df_balance["Delta_Ajuste_TMH"], errors="coerce")
    comparables = originales.notna() & ajustados.notna() & deltas.notna()
    diferencias = (deltas - (ajustados - originales)).abs()
    inconsistentes = comparables & diferencias.gt(0.01)
    if inconsistentes.any():
        indice = inconsistentes[inconsistentes].index[0]
        raise ValueError(
            "Delta_Ajuste_TMH no coincide con ajustado menos original para "
            f"{df_balance.loc[indice, 'Fecha']:%d-%m-%Y}."
        )


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
        ("Mineral Apilado TMH Original", "Mineral_Apilado_TMH_Original"),
        ("Factor Ajuste", "Factor_Ajuste"),
        ("Mineral Apilado TMH Ajustado", "Mineral_Apilado_TMH_Ajustado"),
        ("Delta Ajuste TMH", "Delta_Ajuste_TMH"),
        ("Mineral Chancado", "Mineral_Chancado_Balance"),
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
        ("A4:H4", "Balance diario"), ("I4:K4", "Niveles promedio"),
        ("L4:U4", "Inventarios"), ("V4:Z4", "Niveles Harneros"),
        ("AA4:AE4", "Niveles Chancado"), ("AF4:AG4", "Niveles Silo"),
    )
    color_texto = "476475"
    relleno_azul = PatternFill("solid", fgColor="D7E1E7")
    relleno_blanco = PatternFill("solid", fgColor="FFFFFF")
    lado = Side(style="thin", color="808080")
    borde = Border(left=lado, right=lado, top=lado, bottom=lado)

    ws.merge_cells("A1:AG1")
    ws["A1"] = "Balance Chancado"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color=color_texto)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("A2:AG2")
    ws["A2"] = "Balance diario de apilado, inventarios y mineral chancado"
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
        for col_excel, (_, fuente) in enumerate(columnas, start=1):
            valor = fila[fuente]
            if pd.isna(valor):
                valor = None
            elif fuente == "Fecha" and hasattr(valor, "to_pydatetime"):
                valor = valor.to_pydatetime()
            celda = ws.cell(fila_excel, col_excel, valor)
            celda.font = Font(name="Arial", size=10, color=color_texto)
            celda.fill = relleno_blanco if fila_excel % 2 == 0 else relleno_azul
            celda.alignment = Alignment(horizontal="center", vertical="center")
            celda.border = borde
        ws.row_dimensions[fila_excel].height = 20

    ultima_fila = 5 + len(df_balance)
    for fila in range(6, ultima_fila + 1):
        ws.cell(fila, 1).number_format = "dd-mm-yyyy"
        ws.cell(fila, 2).number_format = "0.000"
        ws.cell(fila, 4).number_format = "0.000000"
        for col in (3, 5, 6, 7, *range(12, 22)):
            ws.cell(fila, col).number_format = "#,##0.00"
        for col in (*range(9, 12), *range(22, 34)):
            ws.cell(fila, col).number_format = "0.00"

    anchos = (13, 10, 20, 14, 20, 16, 17, 12) + (17,) * 3 + (16,) * 10 + (12,) * 12
    for indice, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(indice)].width = ancho
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 42
    ws.auto_filter.ref = f"A5:AG{ultima_fila}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:AG{ultima_fila}"


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
        _validar_balance_chancado(df_balance_chancado)
        _agregar_hoja_balance_chancado(wb, df_balance_chancado)

    if df_factor_ajuste is not None:
        _validar_factor_ajuste_camiones(df, df_factor_ajuste)
        _agregar_hoja_factor_ajuste_camiones(wb, df_factor_ajuste)

    out = io.BytesIO()
    wb.save(out)
    return _normalizar_y_compactar_estilos_xlsx(out.getvalue())
