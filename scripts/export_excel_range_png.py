"""Exporta rangos de una hoja Excel a PNG mediante Microsoft Excel."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pythoncom
import win32com.client


def export_range(workbook_path: Path, sheet_name: str, cell_range: str, output: Path) -> None:
    pythoncom.CoInitialize()
    excel = None
    workbook = None
    chart_object = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        workbook = excel.Workbooks.Open(str(workbook_path.resolve()), ReadOnly=True)
        sheet = workbook.Worksheets(sheet_name)
        sheet.Activate()
        source = sheet.Range(cell_range)
        source.Select()
        source.CopyPicture(Appearance=1, Format=-4147)  # xlScreen, xlPicture
        chart_object = sheet.ChartObjects().Add(0, 0, source.Width, source.Height)
        chart_object.Activate()
        chart_object.Chart.Paste()
        time.sleep(1)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not chart_object.Chart.Export(str(output.resolve()), "PNG"):
            raise RuntimeError(f"Excel no pudo exportar {cell_range} como PNG.")
    finally:
        if chart_object is not None:
            chart_object.Delete()
        if workbook is not None:
            workbook.Close(False)
        if excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(
            "Uso: export_excel_range_png.py LIBRO.xlsx HOJA RANGO SALIDA.png"
        )
    export_range(Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]))
