"""Regresión de agosto en DEV contra el baseline del usuario, sin modificarlo.

Uso: python -m scripts.validate_reconst_mod_srr_dev verify
"""
import io
import hashlib
import json
import os
import sys
import time
from copy import copy
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from openpyxl import load_workbook
from sqlalchemy import text

from report_export import report_export as reports


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "auditorias/archivo/report_export/exports/reconst_mod_srr_validation"
START, END = date(2026, 8, 1), date(2026, 9, 1)
TARGET = ROOT / "auditorias/archivo/report_export/exports/Analisis_Torres_de_Muestreo_20260801_20260831.xlsx"
BASELINE = Path.home() / "Downloads/Analisis_Torres_de_Muestreo_20260801_20260831 (1).xlsx"


def compare_workbooks(before, after, new_sheet=True):
    """Compara estructura lógica y estilos resueltos, no IDs internos del ZIP."""
    a, b = load_workbook(before), load_workbook(after)
    assert b.sheetnames == a.sheetnames + (["Reconst Mod SRR"] if new_sheet else [])
    assert a.views == b.views
    assert a.active.title == b.active.title
    summary = {}
    for name in a.sheetnames:
        left, right = a[name], b[name]
        assert (left.max_row, left.max_column) == (right.max_row, right.max_column), name
        assert set(map(str, left.merged_cells)) == set(map(str, right.merged_cells)), name
        for attr in ("sheet_state", "freeze_panes", "views", "sheet_format",
                     "sheet_properties", "page_setup", "page_margins", "print_options",
                     "print_area", "print_title_rows", "print_title_cols", "auto_filter",
                     "row_breaks", "col_breaks", "protection", "data_validations"):
            assert getattr(left, attr) == getattr(right, attr), (name, attr)
        for dims, attrs in (("column_dimensions", ("min", "max", "width", "hidden", "outlineLevel", "collapsed", "bestFit")),
                            ("row_dimensions", ("height", "hidden", "outlineLevel", "collapsed"))):
            ldim, rdim = getattr(left, dims), getattr(right, dims)
            assert set(ldim) == set(rdim), (name, dims)
            for key in ldim:
                for attr in attrs:
                    assert getattr(ldim[key], attr) == getattr(rdim[key], attr), (name, key, attr)
        for row in left:
            for cell in row:
                other = right[cell.coordinate]
                assert (cell.value, cell.data_type) == (other.value, other.data_type), (name, cell.coordinate)
                for attr in ("font", "fill", "border", "alignment", "protection", "number_format"):
                    assert copy(getattr(cell, attr)) == copy(getattr(other, attr)), (name, cell.coordinate, attr)
        summary[name] = [left.max_row, left.max_column]
    ca, cb = load_workbook(before, data_only=True), load_workbook(after, data_only=True)
    for name in ca.sheetnames:
        assert list(ca[name].values) == list(cb[name].values), (name, "cached values")
    with ZipFile(before) as az, ZipFile(after) as bz:
        for member in az.namelist():
            if member.startswith(("xl/charts/", "xl/drawings/", "xl/media/")):
                assert az.read(member) == bz.read(member), member
    return summary


def main():
    if os.getenv("SQLSERVER_HOST") != "149.50.136.234":
        raise RuntimeError("Validación bloqueada fuera de DEV")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    baseline_hash = hashlib.sha256(BASELINE.read_bytes()).hexdigest()
    fetches = {
        "df": reports.fetch_reporte_turno_cache_emision,
        "df_generador": reports.fetch_generador_reporte_diario_emision,
        "df_clays_cufe": reports.fetch_clays_cufe_report,
        "df_trazabilidad_analitos": reports.fetch_trazabilidad_analitos_report,
        "df_curva_granulometrica": reports.fetch_curva_granulometrica_report,
    }
    frames = {}
    for name, fetch in fetches.items():
        path = ARTIFACTS / (name + ".pkl")
        frames[name] = fetch(START, END)
        frames[name].to_pickle(path)
        print(f"{name}: {len(frames[name])}", flush=True)
    args = dict(frames, df_generador_resumen=frames["df_generador"],
                periodo_inicio=START, periodo_fin=date(2026, 8, 31))
    output = io.BytesIO()
    t0 = time.perf_counter()
    srr = reports.fetch_reconstitucion_srr_report(START, END)
    fetch_seconds = time.perf_counter() - t0
    print(f"[EXCEL-T] Reconst Mod SRR: {fetch_seconds:.2f}s; rows={len(srr)}", flush=True)
    srr.to_pickle(ARTIFACTS / "df_reconst_srr.pkl")
    originals = {k: v.copy(deep=True) for k, v in frames.items()}
    srr_original = srr.copy(deep=True)
    reports.export_reporte_turno_estilo_leyes_finos(
        output=output, df_reconst_srr=srr, **args)
    TARGET.write_bytes(output.getvalue())
    for name, original in originals.items():
        pd.testing.assert_frame_equal(frames[name], original)
    pd.testing.assert_frame_equal(srr, srr_original)
    summary = compare_workbooks(BASELINE, TARGET)
    legacy = io.BytesIO()
    reports.export_reporte_turno_estilo_leyes_finos(output=legacy, **args)
    compare_workbooks(BASELINE, io.BytesIO(legacy.getvalue()), new_sheet=False)
    assert hashlib.sha256(BASELINE.read_bytes()).hexdigest() == baseline_hash
    after = load_workbook(TARGET)
    for name, shape in summary.items():
        print(f"Sin cambios: {name} ({shape[0]} x {shape[1]})", flush=True)
    assert len(srr) == 62 and srr.Fecha.nunique() == 31
    ws = after["Reconst Mod SRR"]
    assert ws.max_row == 39
    assert ws["C39"].value == pd.Timestamp("2026-08-31").to_pydatetime()
    assert not srr.duplicated(["Fecha", "Turno"]).any()
    with reports._get_engine().connect() as conn:
        tmh_source = pd.read_sql(text("""
            SELECT c.Fecha, c.Apilado_TMH_turno_A, c.Apilado_TMH_turno_B,
                   c.Sal_turno_A, c.Sal_Turno_B, b.TMH_CV008_A, b.TMH_CV008_B,
                   b.TMH_CV108_A, b.TMH_CV108_B, f.Factor_Aplicacion_Reportes
            FROM inventar_SpcHidr.Datos_conciliados_of c
            LEFT JOIN inventar_SpcHidr.v_datos_apilado_tmh_v2 b ON b.Fecha = c.Fecha
            LEFT JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test f ON f.Fecha = c.Fecha
            WHERE c.Fecha >= :start AND c.Fecha < :end ORDER BY c.Fecha
        """), conn, params={"start": START, "end": END})
    assert len(tmh_source) == 31
    max_difference = 0.0
    for _, row in tmh_source.iterrows():
        excel_row = pd.Timestamp(row.Fecha).day + 8
        for offset, shift in enumerate(("A", "B")):
            total = ws.cell(excel_row, 4 + offset).value
            tm1 = ws.cell(excel_row, 6 + offset).value
            tm2 = ws.cell(excel_row, 8 + offset).value
            assert abs(total - row[f"Apilado_TMH_turno_{shift}"]) < 1e-8
            raw1, raw2 = row[f"TMH_CV008_{shift}"], row[f"TMH_CV108_{shift}"]
            salt = row["Sal_turno_A" if shift == "A" else "Sal_Turno_B"]
            allocated_salt = salt * raw2 / (raw1 + raw2) if raw1 + raw2 else 0
            assert abs(tm2 - (raw2 * row.Factor_Aplicacion_Reportes - allocated_salt)) < 1e-8
            difference = abs(tm1 + tm2 - total)
            assert difference <= 0.001
            max_difference = max(max_difference, difference)
    factor_days = int(tmh_source.Factor_Aplicacion_Reportes.ne(1).sum())
    assert factor_days > 0
    # Conservación del contenido SRR previo al completar exclusivamente D:I.
    previous = load_workbook(ARTIFACTS / "before_tmh.xlsx")["Reconst Mod SRR"]
    for row in range(9, 40):
        for col in [3] + list(range(12, 39)):
            assert ws.cell(row, col).value == previous.cell(row, col).value, (row, col)
    assert all(c.data_type != "f" for row in ws for c in row)
    expected = [0.51967991668, 0.104380143477, 6.58051682835,
                28.3017129977, 0.115052697325, 76.4399703601]
    for col, value in zip(range(21, 33, 2), expected):
        for offset in (0, 1):
            assert abs(ws.cell(9, col + offset).value - value) < 1e-7
    assert abs(ws["S9"].value - 14692.224627) < 1e-6
    assert abs(ws["T9"].value - 17839.485412) < 1e-6
    assert ws["S30"].value == ws["T30"].value == 0
    assert all(ws.cell(30, c).value is None for c in range(21, 33))
    for day, zero_col in ((8, 19), (21, 20)):
        assert ws.cell(day + 8, zero_col).value == 0
        for col in range(21, 33, 2):
            assert ws.cell(day + 8, col).value is not None
            assert ws.cell(day + 8, col).value == ws.cell(day + 8, col + 1).value
    for col, value in zip(range(34, 39), [0.682355333319423, 0.0486265340967886,
            10.8939366876041, 17.757871969053, 0.153229961351929]):
        assert abs(ws.cell(9, col).value - value) < 1e-10
    for day in (21, 23):
        rows = srr[srr.Fecha == pd.Timestamp(2026, 8, day)]
        assert (rows.Flag_Sensibilidad == "ALTA_SENSIBILIDAD").all()
        assert all(ws.cell(day + 8, c).value is not None for c in range(21, 33))
    for _, row in srr.iterrows():
        excel_row = row.Fecha.day + 8
        offset = 0 if row.Turno == "A" else 1
        for col, name in ((19, "SRR_TMS_Turno"), (21, "CuT_SRR"), (23, "CuS_SRR"),
                          (25, "ClayBeta_SRR"), (27, "Malla100_SRR"), (29, "CO3_SRR"), (31, "Recuperacion_SRR")):
            got, expected = ws.cell(excel_row, col + offset).value, row[name]
            assert got is None if pd.isna(expected) else abs(got - expected) < 1e-8
    for _, row in frames["df"].iterrows():
        excel_row = pd.Timestamp(row.Fecha).day + 8
        offset = 0 if row.Turno == "A" else 1
        for col, name in ((13, "STOCK"), (15, "MINA"), (17, "SRR")):
            got, expected = ws.cell(excel_row, col + offset).value, row[name]
            assert got is None if pd.isna(expected) else abs(got - expected) < 1e-10
    result = dict(baseline=str(BASELINE), baseline_sha256=baseline_hash,
                  existing_sheets=summary, rows_srr=len(srr), dates_srr=31,
                  fetch_seconds=fetch_seconds, controls=[1, 8, 21, 22, 23, 31],
                  regression="OK", tmh="VALIDADO",
                  tmh_max_diferencia=max_difference, dias_factor_distinto_uno=factor_days,
                  target=str(TARGET))
    (ARTIFACTS / "resultado.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print("62 registros / 31 fechas; controles 01, 08, 21, 22, 23, 31 agosto OK")
    print(f"TMH: cuadratura máxima={max_difference:.12f}; días factor != 1: {factor_days}")
    print(TARGET)


if __name__ == "__main__":
    if sys.argv[1:] != ["verify"]:
        raise SystemExit(__doc__)
    main()
