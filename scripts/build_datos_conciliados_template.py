"""Construye la plantilla de Datos Conciliados desde el reporte oficial.

El libro fuente contiene pivotes heredados que openpyxl no puede interpretar.
Se eliminan esas partes en memoria, se conserva únicamente la hoja visible del
reporte diario y se limpia la zona de datos para dejar una plantilla reusable.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook


def _xlsx_sin_pivotes(source: Path) -> io.BytesIO:
    output = io.BytesIO()
    with ZipFile(source, "r") as zin, ZipFile(output, "w", ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            name = item.filename
            if name.startswith(("xl/pivotCache/", "xl/pivotTables/")):
                continue
            data = zin.read(name)
            if name == "xl/workbook.xml":
                text = data.decode("utf-8")
                text = re.sub(r"<pivotCaches[^>]*>.*?</pivotCaches>", "", text, flags=re.S)
                data = text.encode("utf-8")
            elif name == "xl/_rels/workbook.xml.rels":
                text = data.decode("utf-8")
                text = re.sub(
                    r"<Relationship[^>]+Type=\"[^\"]+/pivotCacheDefinition\"[^>]*/>",
                    "",
                    text,
                )
                data = text.encode("utf-8")
            elif name.startswith("xl/worksheets/_rels/"):
                text = data.decode("utf-8")
                text = re.sub(
                    r"<Relationship[^>]+Type=\"[^\"]+/pivotTable\"[^>]*/>",
                    "",
                    text,
                )
                data = text.encode("utf-8")
            elif name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                text = data.decode("utf-8")
                text = re.sub(r"<pivotTableParts[^>]*>.*?</pivotTableParts>", "", text, flags=re.S)
                data = text.encode("utf-8")
            zout.writestr(item, data)
    output.seek(0)
    return output


def build(source: Path, destination: Path) -> None:
    workbook = load_workbook(_xlsx_sin_pivotes(source), keep_links=False)
    report_sheet = workbook["Generador Reporte diario"]

    for sheet in list(workbook.worksheets):
        if sheet is not report_sheet:
            workbook.remove(sheet)
    report_sheet.title = "Datos Conciliados"

    # Mantener exclusivamente el área oficial solicitada y hacerla imprimible.
    report_sheet.print_area = "B2:AY52"
    report_sheet.freeze_panes = "B1"
    report_sheet.sheet_view.zoomScale = 55
    report_sheet.sheet_view.showGridLines = False

    # La fila 1 del archivo fuente contiene bloques amarillos auxiliares que no
    # forman parte del reporte oficial visible.
    for col in range(1, 53):
        cell = report_sheet.cell(1, col)
        cell.value = None
        cell._style = report_sheet["A2"]._style
    report_sheet.row_dimensions[1].height = None

    # La fila 21 conserva los estilos de apertura; la 22, el estilo regular.
    # El exportador replica ambos estilos y mueve el cierre de la fila 52.
    for row in range(21, 52):
        for col in range(3, 52):
            report_sheet.cell(row, col).value = None

    # El reporte oficial entregable termina en la fila 52.
    for merged_range in list(report_sheet.merged_cells.ranges):
        if merged_range.min_row >= 53:
            report_sheet.unmerge_cells(str(merged_range))
    report_sheet._images = [
        image for image in report_sheet._images
        if not hasattr(image.anchor, "_from") or image.anchor._from.row < 52
    ]
    report_sheet._charts = [
        chart for chart in report_sheet._charts
        if not hasattr(chart.anchor, "_from") or chart.anchor._from.row < 52
    ]
    if report_sheet.max_row > 52:
        report_sheet.delete_rows(53, report_sheet.max_row - 52)

    # Fórmulas de resumen reusables, acotadas a los 31 días del mes.
    formulas = {
        "Z3": '="MTD "&TEXT($I$5,"mmmm yyyy")',
        "AB5": "=IFERROR(SUM(T21:T51),0)",
        "AC5": "=IFERROR(SUM(U21:U51),0)",
        "AD5": "=IFERROR((AB5-AC5)/AC5,0)",
        "AE5": "=AB5-AC5",
        "AB6": "=IFERROR(SUM(AA21:AA51)/AB5*100,0)",
        "AC6": "=IFERROR(SUMPRODUCT(U21:U51,Z21:Z51)/SUM(U21:U51),0)",
        "AD6": "=IFERROR((AB6-AC6)/AC6,0)",
        "AE6": "=AB6-AC6",
        "AB7": "=IFERROR(SUM(AA21:AA51),0)",
        "AC7": "=AC6*AC5/100",
        "AD7": "=IFERROR((AB7-AC7)/AC7,0)",
        "AE7": "=AB7-AC7",
        "AB8": "=IFERROR(SUM(M21:M51),0)",
        "AC8": "=IFERROR(SUM(N21:N51),0)",
        "AD8": "=IFERROR((AB8-AC8)/AC8,0)",
        "AE8": "=AB8-AC8",
        "AB9": "=AB15-AB14",
        "AC9": "=AC15-AC14",
        "AD9": "=IFERROR((AB9-AC9)/AC9,0)",
        "AE9": "=AB9-AC9",
        "AB14": "=IFERROR(SUM(AQ21:AQ51),0)",
        "AC14": "=IFERROR(SUM(AR21:AR51),0)",
        "AD14": "=IFERROR((AB14-AC14)/AC14,0)",
        "AE14": "=AB14-AC14",
        "AB15": "=IFERROR(SUM(AU21:AU51),0)",
        "AC15": "=IFERROR(SUM(AV21:AV51),0)",
        "AD15": "=IFERROR((AB15-AC15)/AC15,0)",
        "AE15": "=AB15-AC15",
        "AB16": "=IFERROR(SUM(AW21:AW51),0)",
        "AC16": "=IFERROR(SUM(AX21:AX51),0)",
        "AD16": "=IFERROR((AB16-AC16)/AC16,0)",
        "AE16": "=AB16-AC16",
    }
    for coordinate, formula in formulas.items():
        report_sheet[coordinate] = formula

    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.defined_names.clear()
    report_sheet.defined_names.clear()

    destination.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(destination)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: build_datos_conciliados_template.py ORIGEN.xlsx DESTINO.xlsx")
    build(Path(sys.argv[1]), Path(sys.argv[2]))
