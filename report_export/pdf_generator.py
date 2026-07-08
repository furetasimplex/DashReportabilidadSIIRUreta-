"""
PDF generation for reportabilidad reports using reportlab.
"""
import io
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
BHP_LOGO_PATH = os.path.join(PROJECT_DIR, "assets", "pampa-norte-bhp.png")

# Brand colors
_DARK_BLUE = "#1F4E79"
_MID_BLUE = "#9DC3E6"
_LIGHT_BLUE = "#D9EAF7"
_ORANGE = "#E86D1F"
_ALT_ROW = "#EEF3F6"
_YELLOW = "#FFF2CC"
_GREY = "#F2F2F2"
_BORDER = "#B8B8B8"
_RED = "#CC0000"


def _c(hex_str):
    from reportlab.lib.colors import HexColor
    return HexColor(hex_str)


def _logo_image(width_mm, height_mm):
    """Return a reportlab Image for the BHP logo, or None if not found."""
    if not os.path.exists(BHP_LOGO_PATH):
        return None
    from reportlab.platypus import Image
    from reportlab.lib.units import mm
    return Image(BHP_LOGO_PATH, width=width_mm * mm, height=height_mm * mm)


def _page_header(title: str, subtitle: str, fecha_range: str):
    """Returns a list of flowables for the page header (logo + titles)."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import mm

    h_title = ParagraphStyle(
        "h_title",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=_c(_DARK_BLUE),
        leading=16,
    )
    h_sub = ParagraphStyle(
        "h_sub",
        fontName="Helvetica",
        fontSize=9,
        textColor=_c("#555555"),
        leading=12,
    )

    logo = _logo_image(58, 9)
    logo_cell = logo if logo else ""

    title_para = Paragraph(title, h_title)
    sub_para = Paragraph(
        f"Superintendencia de Medición y Reconciliación &nbsp;|&nbsp; {fecha_range}",
        h_sub,
    )

    header_table = Table(
        [[logo_cell, [title_para, Spacer(1, 1 * mm), sub_para]]],
        colWidths=[32 * mm, None],
    )
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    return [header_table, Spacer(1, 5 * mm)]


# ──────────────────────────────────────────────────────────────────────────────
# REPRESENTATIVIDAD TORRES
# ──────────────────────────────────────────────────────────────────────────────

def generar_pdf_representatividad_torres(
    df: pd.DataFrame, f_ini: str, f_fin: str
) -> bytes:
    """Landscape A4 PDF for the representatividad de torres report."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
    from reportlab.lib.units import mm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    fecha_range = (
        f"{pd.to_datetime(f_ini).strftime('%d-%m-%Y')} — "
        f"{pd.to_datetime(f_fin).strftime('%d-%m-%Y')}"
    )

    story = _page_header(
        "Representatividad diaria de torres de muestreo",
        "Superintendencia de Medición y Reconciliación",
        fecha_range,
    )

    columnas_pct = [
        "TM1_TurnoA_Quimico", "TM1_TurnoA_Fisico",
        "TM1_TurnoB_Quimico", "TM1_TurnoB_Fisico",
        "TM2_TurnoA_Quimico", "TM2_TurnoA_Fisico",
        "TM2_TurnoB_Quimico", "TM2_TurnoB_Fisico",
    ]

    sub_headers = ["TA - Quím.", "TA - Fís.", "TB - Quím.", "TB - Fís."]

    # 2-row header
    row0 = ["Día", "Representatividad TM1", "", "", "", "Representatividad TM2", "", "", ""]
    row1 = ["", "TA - Quím.", "TA - Fís.", "TB - Quím.", "TB - Fís.",
            "TA - Quím.", "TA - Fís.", "TB - Quím.", "TB - Fís."]

    # Build data + track cell colours
    cell_colors = {}
    table_data = [row0, row1]

    for r_i, (_, row) in enumerate(df.iterrows()):
        dia_val = row.get("Dia")
        dia = pd.to_datetime(dia_val).strftime("%d-%m-%Y") if pd.notna(dia_val) else ""
        data_row = [dia]
        for c_i, col in enumerate(columnas_pct):
            valor = pd.to_numeric(row.get(col), errors="coerce") if col in df.columns else float("nan")
            if pd.isna(valor):
                data_row.append("Tambor\ndetenido")
                cell_colors[(r_i + 2, c_i + 1)] = "detenido"
            else:
                data_row.append(f"{valor * 100:.1f}%")
                if valor < 0.75:
                    cell_colors[(r_i + 2, c_i + 1)] = "bajo"
                else:
                    cell_colors[(r_i + 2, c_i + 1)] = "normal"
        table_data.append(data_row)

    # Column widths: A4 landscape usable = 272mm, Día=22, rest=31.25 each
    usable = (297 - 24) * mm
    dia_w = 22 * mm
    col_w = (usable - dia_w) / 8
    col_widths = [dia_w] + [col_w] * 8

    tbl = Table(table_data, colWidths=col_widths, repeatRows=2)

    cmds = [
        # Header group spans
        ("SPAN", (0, 0), (0, 1)),
        ("SPAN", (1, 0), (4, 0)),
        ("SPAN", (5, 0), (8, 0)),

        # Header style
        ("BACKGROUND", (0, 0), (-1, 1), _c(_LIGHT_BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 1), _c(_DARK_BLUE)),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Día column highlight
        ("BACKGROUND", (0, 2), (0, -1), _c(_YELLOW)),
        ("FONTNAME", (0, 2), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, -1), 8),

        # Grid
        ("GRID", (0, 0), (-1, -1), 0.4, _c(_BORDER)),

        # Row heights
        ("ROWBACKGROUND", (0, 2), (-1, -1), [_c("#FFFFFF"), _c(_ALT_ROW)]),
    ]

    # Conditional cell colors
    for (row_i, col_i), state in cell_colors.items():
        if state == "bajo":
            cmds += [
                ("TEXTCOLOR", (col_i, row_i), (col_i, row_i), _c(_RED)),
                ("FONTNAME", (col_i, row_i), (col_i, row_i), "Helvetica-Bold"),
            ]
        elif state == "detenido":
            cmds.append(("TEXTCOLOR", (col_i, row_i), (col_i, row_i), _c(_DARK_BLUE)))

    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)

    story.append(Spacer(1, 4 * mm))

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(_c("#888888"))
        canvas.drawRightString(
            doc.pagesize[0] - 12 * mm,
            8 * mm,
            f"Página {doc.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# REPORTE POR TURNO  (2 pages: chemistry / granulometries)
# ──────────────────────────────────────────────────────────────────────────────

def generar_pdf_reporte_turno(df: pd.DataFrame, f_ini: str, f_fin: str) -> bytes:
    """
    Landscape A3 PDF for the reporte por turno.
    Splits into two pages: chemistry / granulometries+sources.
    """
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak
    from reportlab.lib.units import mm

    # Re-use the same prep function used for Excel
    from report_export.report_export import preparar_df_reporte_turno_excel

    df = preparar_df_reporte_turno_excel(df.copy())

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A3),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    fecha_range = (
        f"{pd.to_datetime(f_ini).strftime('%d-%m-%Y')} — "
        f"{pd.to_datetime(f_fin).strftime('%d-%m-%Y')}"
    )

    # ── Column groups ─────────────────────────────────────────────────────────
    # Page 1: info + chemistry
    cols_p1 = [
        ("Fecha", "Fecha"),
        ("Campania", "Campaña"),
        ("Material", "Material"),
        ("Modulo", "Módulo"),
        ("Avance", "Avance"),
        ("Turno_excel", "Turno"),
        ("Apilado_TMS_Real", "Apilado\nTMS"),
        ("Apilado_TMS_Plan_Mensual", "Apilado\nPlan"),
        ("STOCK", "Stock%"),
        ("MINA", "Mina%"),
        ("SRR", "SRR%"),
        ("CuT_Real", "CuT\nReal"),
        ("CuT_Plan_Semanal", "CuT\nProg"),
        ("CuT_Plan_Mensual", "CuT\nPlan"),
        ("CuS_Real", "CuS\nReal"),
        ("CuS_Plan_Semanal", "CuS\nProg"),
        ("CuS_Plan_Mensual", "CuS\nPlan"),
        ("Solubilidad_Real", "Sol.\nReal"),
        ("Solubilidad_Plan_Semanal", "Sol.\nProg"),
        ("Solubilidad_Plan_Mensual", "Sol.\nPlan"),
        ("CO3_Real", "CO3\nReal"),
        ("CO3_Plan_Semanal", "CO3\nProg"),
        ("CO3_Plan_Mensual", "CO3\nPlan"),
    ]

    # Page 2: remaining analysis + granulometry + sources
    cols_p2 = [
        ("Fecha", "Fecha"),
        ("Turno_excel", "Turno"),
        ("CuFe_Real", "CuFe\nReal"),
        ("FeT_Real", "FeT\nReal"),
        ("FeS_Real", "FeS\nReal"),
        ("ConsH_Real", "ConsH\n(kg/t)"),
        ("Malla_Menos_1_2_Real", "-1/2\nReal"),
        ("Malla_Menos_1_2_Plan_Semanal", "-1/2\nPlan"),
        ("Malla_Menos_100_Real", "-100#\nReal"),
        ("Malla_Menos_100_Plan_Semanal", "-100#\nProg"),
        ("Malla_Menos_100_Plan_Mensual", "-100#\nPlan"),
        ("CaolBeta_Real", "NIR\nReal"),
        ("CaolBeta_Plan_Semanal", "NIR\nProg"),
        ("CaolBeta_Plan_Mensual", "NIR\nPlan"),
        ("Dosis_Acido_Ideal_TM", "Dosis\nIdeal"),
        ("Dosis_Acido_Programa_Semanal", "Dosis\nProg"),
        ("Fuente_Info_Quimica", "Fuente\nQuímica"),
        ("Fuente_Info_Fisica", "Fuente\nFísica"),
    ]

    usable_w = (420 - 20) * mm  # A3 landscape - margins

    def _build_section(col_defs):
        """Build a reportlab Table from a list of (col_name, header_label) tuples."""
        cols_present = [(c, h) for c, h in col_defs if c in df.columns]
        if not cols_present:
            return None

        col_names = [c for c, _ in cols_present]
        col_labels = [h for _, h in cols_present]
        n = len(col_names)

        # Width distribution: text columns get more space
        text_cols = {"Fecha", "Campania", "Material", "Modulo", "Turno_excel",
                     "Fuente_Info_Quimica", "Fuente_Info_Fisica"}
        total_units = sum(2 if c in text_cols else 1 for c in col_names)
        unit = usable_w / total_units
        col_widths = [2 * unit if c in text_cols else unit for c in col_names]

        header_row = col_labels
        table_data = [header_row]

        for _, row in df.iterrows():
            data_row = []
            for col in col_names:
                val = row.get(col, "")
                if col == "Fecha":
                    try:
                        val = pd.to_datetime(val).strftime("%d-%m-%Y")
                    except Exception:
                        val = str(val) if val else ""
                elif isinstance(val, float):
                    if pd.isna(val):
                        val = ""
                    else:
                        val = f"{val:.2f}"
                elif val is None or (isinstance(val, str) and val.lower() in ("nan", "none", "")):
                    val = ""
                data_row.append(str(val))
            table_data.append(data_row)

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)

        cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), _c(_MID_BLUE)),
            ("TEXTCOLOR", (0, 0), (-1, 0), _c(_DARK_BLUE)),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, _c(_BORDER)),
            ("ROWBACKGROUND", (0, 1), (-1, -1), [_c("#FFFFFF"), _c(_ALT_ROW)]),
        ]

        # Highlight Fecha and Turno columns
        for i, col in enumerate(col_names):
            if col == "Fecha":
                cmds.append(("BACKGROUND", (i, 1), (i, -1), _c(_LIGHT_BLUE)))
                cmds.append(("FONTNAME", (i, 1), (i, -1), "Helvetica-Bold"))
            elif col == "Turno_excel":
                cmds.append(("BACKGROUND", (i, 1), (i, -1), _c(_GREY)))

        tbl.setStyle(TableStyle(cmds))
        return tbl

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(_c("#888888"))
        canvas.drawRightString(doc.pagesize[0] - 10 * mm, 6 * mm, f"Página {doc.page}")
        canvas.restoreState()

    story = _page_header(
        "Análisis de las Torres de Muestreo por Turno — Química",
        "Superintendencia de Medición y Reconciliación",
        fecha_range,
    )
    tbl1 = _build_section(cols_p1)
    if tbl1:
        story.append(tbl1)

    story.append(PageBreak())

    story += _page_header(
        "Análisis de las Torres de Muestreo por Turno — Granulometrías y Fuentes",
        "Superintendencia de Medición y Reconciliación",
        fecha_range,
    )
    tbl2 = _build_section(cols_p2)
    if tbl2:
        story.append(tbl2)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# DATOS CONCILIADOS
# ──────────────────────────────────────────────────────────────────────────────

_COLS_PROD_LABELS = {
    "Fecha": "Fecha",
    "Apilado_TMS_Real": "Apilado\nTMS Real",
    "Apilado_TMS_Plan": "Apilado\nTMS Plan",
    "Ley_CuT_Real": "Ley CuT\nReal (%)",
    "Ley_CuT_Plan": "Ley CuT\nPlan (%)",
    "Cobre_fino_Apilado_Real": "Cu Fino\nReal",
    "Cobre_fino_Apilado_Plan": "Cu Fino\nPlan",
    "Produccion_Catodos_Real": "Prod.\nCátodos Real",
    "Produccion_Catodos_Plan": "Prod.\nCátodos Plan",
    "Estado": "Estado",
}


def generar_pdf_datos_conciliados(
    df: pd.DataFrame, f_ini: str, f_fin: str
) -> bytes:
    """Landscape A4 PDF for producción diaria / datos conciliados."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
    from reportlab.lib.units import mm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    fecha_range = (
        f"{pd.to_datetime(f_ini).strftime('%d-%m-%Y')} — "
        f"{pd.to_datetime(f_fin).strftime('%d-%m-%Y')}"
    )

    story = _page_header(
        "Producción Diaria — Datos Conciliados",
        "Superintendencia de Medición y Reconciliación",
        fecha_range,
    )

    cols_present = [(col, label) for col, label in _COLS_PROD_LABELS.items() if col in df.columns]
    if not cols_present:
        return buffer.getvalue()

    col_names = [c for c, _ in cols_present]
    col_labels = [h for _, h in cols_present]
    n = len(col_names)
    usable = (297 - 24) * mm
    fecha_w = 22 * mm
    rest_w = (usable - fecha_w) / (n - 1) if n > 1 else usable
    col_widths = [fecha_w if c == "Fecha" else rest_w for c in col_names]

    header_row = col_labels
    table_data = [header_row]

    for _, row in df.iterrows():
        data_row = []
        for col in col_names:
            val = row.get(col, "")
            if col == "Fecha":
                try:
                    val = pd.to_datetime(val).strftime("%d-%m-%Y")
                except Exception:
                    val = str(val)
            elif isinstance(val, float):
                val = "" if pd.isna(val) else f"{val:,.2f}"
            elif val is None:
                val = ""
            data_row.append(str(val))
        table_data.append(data_row)

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    fecha_idx = col_names.index("Fecha") if "Fecha" in col_names else -1

    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), _c(_MID_BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), _c(_DARK_BLUE)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, _c(_BORDER)),
        ("ROWBACKGROUND", (0, 1), (-1, -1), [_c("#FFFFFF"), _c(_ALT_ROW)]),
    ]

    if fecha_idx >= 0:
        cmds += [
            ("BACKGROUND", (fecha_idx, 1), (fecha_idx, -1), _c(_LIGHT_BLUE)),
            ("FONTNAME", (fecha_idx, 1), (fecha_idx, -1), "Helvetica-Bold"),
        ]

    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(_c("#888888"))
        canvas.drawRightString(doc.pagesize[0] - 12 * mm, 8 * mm, f"Página {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
