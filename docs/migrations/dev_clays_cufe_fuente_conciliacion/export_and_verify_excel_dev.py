from __future__ import annotations

import io
import json
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from report_export.report_export import (  # noqa: E402
    export_reporte_turno_estilo_leyes_finos,
    fetch_clays_cufe_report,
    fetch_generador_reporte_diario_emision,
    fetch_reporte_turno_cache_emision,
    fetch_trazabilidad_analitos_report,
)


def color_tokens(cell) -> set[str]:
    tokens: set[str] = set()
    for color in (cell.font.color, cell.fill.fgColor):
        if color is not None:
            for value in (color.rgb, color.indexed):
                if value is not None:
                    tokens.add(str(value).upper())
    return tokens


def main() -> None:
    if os.getenv("SQLSERVER_HOST") != "149.50.136.234":
        raise RuntimeError("Exportación bloqueada fuera de DEV")
    start = date(2026, 8, 1)
    end = date(2026, 8, 27)
    df_turno = fetch_reporte_turno_cache_emision(start, end)
    df_clays = fetch_clays_cufe_report(start, end)
    df_trace = fetch_trazabilidad_analitos_report(start, end)
    df_gen = fetch_generador_reporte_diario_emision(start, end)
    output = io.BytesIO()
    export_reporte_turno_estilo_leyes_finos(
        df_turno,
        output,
        df_generador=df_gen,
        df_generador_resumen=df_gen,
        df_clays_cufe=df_clays,
        df_trazabilidad_analitos=df_trace,
    )
    target = ROOT / "report_export" / "exports" / "Analisis_Torres_de_Muestreo_20260801_20260826_FUENTE_IMP_DEV.xlsx"
    target.write_bytes(output.getvalue())

    wb = load_workbook(target, data_only=False)
    required_sheets = {"Clays-CuFe", "Trazabilidad Analitos"}
    if not required_sheets.issubset(wb.sheetnames):
        raise AssertionError(f"Faltan hojas: {required_sheets - set(wb.sheetnames)}")
    found = {}
    for sheet_name in required_sheets:
        ws = wb[sheet_name]
        hits = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.value == "IMP":
                    hits.append({"coordinate": cell.coordinate, "colors": sorted(color_tokens(cell))})
        found[sheet_name] = hits
        if not hits:
            raise AssertionError(f"No aparecen fuentes IMP en {sheet_name}")
        if sheet_name == "Trazabilidad Analitos" and not any(any(token.endswith("FF0000") or token.endswith("C00000") for token in hit["colors"]) for hit in hits):
            raise AssertionError(f"IMP no aparece en rojo en {sheet_name}: {hits}")

    ws_clays = wb["Clays-CuFe"]
    clays_imp_value_cells = []
    for row_idx in range(5, ws_clays.max_row + 1):
        if ws_clays.cell(row_idx, 7).value == "IMP":
            value_cell = ws_clays.cell(row_idx, 5)
            colors = sorted(color_tokens(value_cell))
            clays_imp_value_cells.append({"coordinate": value_cell.coordinate, "colors": colors})
    if len(clays_imp_value_cells) != 8:
        raise AssertionError(f"Se esperaban 8 CaolBeta IMP visuales: {clays_imp_value_cells}")
    if not all(any(token.endswith("FF0000") for token in hit["colors"]) for hit in clays_imp_value_cells):
        raise AssertionError(f"CaolBeta IMP no está en rojo: {clays_imp_value_cells}")

    expected_dates = {date(2026, 8, 24), date(2026, 8, 25)}
    clays_imp = df_clays.loc[df_clays["Fuente_CaolBeta"] == "IMP"].copy()
    actual_dates = set(pd.to_datetime(clays_imp["Fecha"]).dt.date)
    if not expected_dates.issubset(actual_dates):
        raise AssertionError(f"Faltan fechas IMP en Clays-CuFe: {expected_dates - actual_dates}")
    trace_imp = df_trace.loc[(df_trace["Analito"] == "CaolBeta") & (df_trace["Fuente_Base"] == "IMP")]
    normalized = set(pd.to_datetime(trace_imp["Fecha"]).dt.strftime("%Y-%m-%d"))
    if not {"2026-08-24", "2026-08-25"}.issubset(normalized):
        raise AssertionError("Trazabilidad Analitos no propagó IMP para 24/25 agosto")

    report = {
        "excel": str(target),
        "size": target.stat().st_size,
        "rows_turno": len(df_turno),
        "rows_clays": len(df_clays),
        "rows_trace": len(df_trace),
        "imp_clays_rows": len(clays_imp),
        "imp_trace_caol_rows": len(trace_imp),
        "imp_cells": found,
        "clays_imp_value_cells": clays_imp_value_cells,
    }
    (HERE / "excel_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
