"""Smoke test DEV: Run 150 -> template oficial de Balance."""

from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from report_export.export_to_excel import (
    _balance_columns_analysis,
    _balance_columns_reconciliados,
    _balance_flow_rows,
    export_balance_reconciliacion_to_template,
)
from report_export.report_export import fetch_recon_balance_run_report


RUN_ID = 150
TEMPLATE = Path("reporte/Template_Balance_Planta_Hidrometalurgia.xlsx")
OUTPUT = Path("Balance_DEV_Run150.xlsx")


def _formula_snapshot(workbook):
    return {
        f"{ws.title}!{cell.coordinate}": cell.value
        for ws in workbook.worksheets
        for row in ws.iter_rows()
        for cell in row
        if cell.data_type == "f"
        or (isinstance(cell.value, str) and cell.value.startswith("="))
    }


def _structure_snapshot(workbook):
    return {
        "sheets": tuple(workbook.sheetnames),
        "defined_names": tuple(sorted(workbook.defined_names)),
        "charts": {ws.title: len(ws._charts) for ws in workbook.worksheets},
        "images": {ws.title: len(ws._images) for ws in workbook.worksheets},
        "merged": {
            ws.title: tuple(sorted(str(rng) for rng in ws.merged_cells.ranges))
            for ws in workbook.worksheets
        },
    }


def _assert_close(actual, expected, label):
    if pd.isna(expected):
        assert actual is None, f"{label}: se esperaba celda vacia, se obtuvo {actual!r}"
    else:
        assert abs(float(actual) - float(expected)) < 1e-6, (
            f"{label}: esperado {expected!r}, obtenido {actual!r}"
        )


def main():
    if not TEMPLATE.is_file():
        raise FileNotFoundError(
            f"Falta el template requerido: {TEMPLATE.resolve()}"
        )

    before = load_workbook(TEMPLATE, data_only=False, keep_links=True)
    formulas_before = _formula_snapshot(before)
    structure_before = _structure_snapshot(before)

    df_run, metadata = fetch_recon_balance_run_report(RUN_ID)
    controls = {
        "F1": {"tolerancia_masa": 0.5, "masa_reconciliada": 713470.127360},
        "F4": {"tolerancia_masa": 6.6, "masa_reconciliada": 752094.777510},
        "F49": {"tolerancia_ley": 1.0, "fino_cu_reconciliado": 2000.051305},
        "F108": {"masa_reconciliada": -131.790374, "fino_cu_medido": -131.790374},
        "F117": {"tolerancia_masa": 5.0, "ley_cu_reconciliada": 4.755118},
        "F118": {"fino_cu_medido": 0.0, "fino_cu_reconciliado": 0.0},
    }
    for code, expected_fields in controls.items():
        for field, expected in expected_fields.items():
            _assert_close(df_run.loc[code, field], expected, f"BD {code}.{field}")

    df_acumulado = df_run.loc[:, [
        "codigo_flujo",
        "masa_reconciliada",
        "ley_cu_reconciliada",
        "fino_cu_reconciliado",
    ]].rename(columns={
        "masa_reconciliada": "masa_reconciliada_acumulada",
        "ley_cu_reconciliada": "ley_cu_reconciliada_acumulada",
        "fino_cu_reconciliado": "fino_cu_reconciliado_acumulado",
    })
    output_bytes = export_balance_reconciliacion_to_template(
        df_run, df_acumulado, metadata, str(TEMPLATE)
    )
    OUTPUT.write_bytes(output_bytes)
    after = load_workbook(BytesIO(output_bytes), data_only=False, keep_links=True)

    assert _formula_snapshot(after) == formulas_before, (
        "Se modificaron formulas existentes fuera de los inputs autorizados."
    )
    assert _structure_snapshot(after) == structure_before, (
        "Cambio la estructura, nombres definidos, merges, graficos o imagenes."
    )

    ws_data = after["Datos Reconciliados"]
    rows_data, flow_col_data = _balance_flow_rows(ws_data)
    cols_data = _balance_columns_reconciliados(
        ws_data, flow_col_data, min(rows_data.values())
    )
    ws_analysis = after["Análisis Variación-Tolerancias"]
    rows_analysis, flow_col_analysis = _balance_flow_rows(ws_analysis)
    cols_analysis = _balance_columns_analysis(
        ws_analysis, flow_col_analysis, min(rows_analysis.values())
    )
    for code in controls:
        source = df_run.loc[code]
        _assert_close(
            ws_data.cell(rows_data[code], cols_data["period_masa"]).value,
            source["masa_reconciliada"],
            f"Excel {code}.period_masa",
        )
        _assert_close(
            ws_data.cell(rows_data[code], cols_data["accum_fino"]).value,
            source["fino_cu_reconciliado"],
            f"Excel {code}.accum_fino",
        )
        _assert_close(
            ws_analysis.cell(rows_analysis[code], cols_analysis["tol_masa"]).value,
            source["tolerancia_masa"],
            f"Excel {code}.tolerancia_masa",
        )

    print(f"caso_id: {int(metadata['caso_id'])}")
    print(f"run_id: {int(metadata['run_id'])}")
    print(f"estado: {metadata['estado_run']}")
    print(f"es_oficial: {bool(metadata['es_oficial'])}")
    print(f"fecha_inicio: {metadata['fecha_inicio']}")
    print(f"fecha_fin: {metadata['fecha_fin']}")
    print(f"cantidad flujos: {len(df_run)}")
    print(f"ruta archivo: {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
