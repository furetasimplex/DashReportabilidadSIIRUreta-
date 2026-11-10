"""Pruebas de formato para el reporte de recuperación y la hoja Prod.

Se mantienen en staging hasta integrar los cambios del writer al checkout.
Al ejecutarse dentro del paquete usan la importación relativa habitual. Desde
este staging del repositorio, resuelven el paquete DashReportabilidadSIIR.
No consultan SQL ni invocan el callback de descarga.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

try:
    from . import report_metodo as report
except ImportError:  # ejecución desde el staging separado del checkout objetivo
    target_parent = Path(__file__).resolve().parents[3] / "DashReportabilidadSIIR"
    if target_parent.is_dir():
        sys.path.insert(0, str(target_parent))
    from curvas_recon import report_metodo as report


def _write_reference_fixture(path: Path) -> None:
    """Referencia mínima: OX numera en fila 9; SU agrega rótulo en fila 10."""
    wb = Workbook()
    ox = wb.active
    ox.title = "Rec Ox"
    su = wb.create_sheet("Rec Sulfuro")
    for ws in (ox, su):
        for r, value in enumerate((18, 3, 62.5, 5.25, 8.4, 55.0, 4.62, -0.63), 1):
            ws.cell(r, 2, value)
    ox.cell(9, 1, None)
    ox.cell(9, 2, 1)
    ox.cell(10, 1, 1)
    ox.cell(10, 2, 0.125)
    ox.cell(11, 1, 2)
    # Hueco interno deliberado: el tercer dato debe conservar su día.
    ox.cell(12, 1, 3)
    ox.cell(12, 2, 0.375)
    su.cell(10, 1, "Dias Lix")
    su.cell(10, 2, 21)
    su.cell(11, 1, 1)
    su.cell(11, 2, 0.215)
    su.cell(12, 1, 2)
    su.cell(13, 1, 3)
    su.cell(13, 2, 0.465)
    wb.save(path)


def test_lector_toma_curva_despues_de_encabezado_de_pilas_y_preserva_huecos(tmp_path):
    path = tmp_path / "referencia_minima.xlsx"
    _write_reference_fixture(path)

    ox = report.leer_planta("OXIDOS", str(path))[1]
    su = report.leer_planta("SULFUROS", str(path))[21]

    assert ox["campana"] == 18
    assert ox["curva"][0] == pytest.approx(0.125)
    assert ox["curva"][1] is None
    assert ox["curva"][2] == pytest.approx(0.375)
    assert su["campana"] == 18
    assert su["curva"][0] == pytest.approx(0.215)
    assert su["curva"][1] is None
    assert su["curva"][2] == pytest.approx(0.465)


def _pile(label: str, num: int, p: str, start: str, rec: list[float]) -> dict:
    return dict(
        p=p, num=num, campana=18, ini=start, apilado_ini="2026-09-20",
        apilado_fin="2026-09-25", n=len(rec), apilado=100.0, tms=1000.0,
        ley=10.0, vol_riego=2400.0, rl=2.4, dias_riego=len(rec), dias_ley=len(rec),
        t_med=rec[-1], t_rec=rec[-1], pct=rec[-1], rec_corte=None, pct_corte=None,
        planta_ok=False, planta_campana=None, planta_ciclos=None, planta_pct=None,
        planta_apilado=None, planta_rec_termino=None, planta_curva=[],
        med=list(rec), rec=list(rec), cov=[1] * len(rec),
    )


def _doc() -> dict:
    return dict(
        end="2026-10-04", corte_planta="2026-10-12", casos=[dict(id=18, run_id=456, fecha_inicio="2026-10-01", fecha_fin="2026-10-04")],
        pads={
            "OXIDOS": dict(desde="2026-10-01", pilas=[
                _pile("OXIDOS", 1, "P01", "2026-10-01", [0.5, 1.5, 3.0]),
            ]),
            "SULFUROS": dict(desde="2026-10-02", pilas=[
                _pile("SULFUROS", 21, "P21", "2026-10-02", [1.0, 2.0, 4.0]),
            ]),
        },
    )


def _series_formula(series, kind: str) -> str:
    ref = getattr(series, kind)
    numeric = getattr(ref, "numRef", None)
    string = getattr(ref, "strRef", None)
    return (numeric or string).f


def test_libro_final_conserva_layout_pad_curvas_prod_y_agrega_rl(tmp_path):
    path = tmp_path / "reporte.xlsx"
    report.escribir_libro(_doc(), path)
    wb = load_workbook(path, data_only=False)

    assert wb.sheetnames == ["Rec Ox", "Rec Sulfuro", "Curvas Ox", "Curvas Sulfuro", "Prod Oxidos", "Prod Sulfuros", "RL Oxidos", "RL Sulfuros", "Riego Ox", "Riego Sulfuro"]
    ox, su = wb["Rec Ox"], wb["Rec Sulfuro"]
    # La hoja de óxidos conserva su fila 9 con números de pila y curva desde 10.
    assert ox["A1"].value == "Campana"
    assert ox["B9"].value == 1
    assert ox["A10"].value == 1
    assert ox["B10"].value == pytest.approx(0.5)
    # Sulfuros deja la fila 9 libre, identifica el eje en fila 10 y empieza en 11.
    assert su["A1"].value == "Campana"
    assert su["A9"].value is None and su["B9"].value is None
    assert su["A10"].value == "Dias Lix"
    assert su["B10"].value == 21
    assert su["A11"].value == 1
    assert su["B11"].value == pytest.approx(1.0)

    # Cada gráfico usa las celdas de la curva de su pad y el eje de días alineado.
    for name, val_range, cat_range in (
        ("Curvas Ox", "'Rec Ox'!$B$10:$B$12", "'Rec Ox'!$A$10:$A$12"),
        ("Curvas Sulfuro", "'Rec Sulfuro'!$B$11:$B$13", "'Rec Sulfuro'!$A$11:$A$13"),
    ):
        chart_sheet = wb[name]
        assert len(chart_sheet._charts) == 2
        recovery = chart_sheet._charts[0].series[0]
        assert _series_formula(recovery, "yVal") == val_range
        assert _series_formula(recovery, "xVal") == cat_range

    prod_ox, prod_su = wb["Prod Oxidos"], wb["Prod Sulfuros"]
    assert prod_ox["A1"].value == "Cu neto diario [t Cu/dia]"
    assert prod_ox["A2"].value == "Caso 18 / run 456 (2026-10-01–2026-10-04)"
    assert prod_ox["A3"].value.endswith("xidos")
    assert prod_su["A3"].value == "Sulfuros"
    assert prod_ox["A4"].value == prod_su["A4"].value == "Parcela"
    assert prod_ox["B4"].value == 1
    assert prod_su["B4"].value == 21
    # Cada hoja conserva fechas y deltas diarios solo de su pad.
    dates_ox = [prod_ox.cell(row, 1).value for row in range(5, 8)]
    assert [date.fromisoformat(str(value)[:10]) for value in dates_ox] == [
        date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
    ]
    dates_su = [prod_su.cell(row, 1).value for row in range(5, 8)]
    assert [date.fromisoformat(str(value)[:10]) for value in dates_su] == [
        date(2026, 10, 2), date(2026, 10, 3), date(2026, 10, 4),
    ]
    assert [prod_ox.cell(row, 2).value for row in range(5, 8)] == pytest.approx([0.5, 1.0, 1.5])
    assert [prod_su.cell(row, 2).value for row in range(5, 8)] == pytest.approx([1.0, 1.0, 2.0])
    assert sum(prod_ox.cell(row, 2).value or 0 for row in range(5, 8)) == pytest.approx(ox['B4'].value)
    assert sum(prod_su.cell(row, 2).value or 0 for row in range(5, 8)) == pytest.approx(su['B4'].value)
    assert ox['B9'].fill.fgColor.rgb[-6:] == 'FFFF00'
    assert prod_ox['B5'].fill.fgColor.rgb[-6:] == 'FFC000'
    assert ox['B10'].font.name == 'Arial'
    # El lector reconoce las columnas por parcela y puede releer el resultado.
    assert report.leer_planta('OXIDOS', str(path))[1]['curva'] == [0.5, 1.5, 3.0]
    assert report.leer_planta('SULFUROS', str(path))[21]['curva'] == [1.0, 2.0, 4.0]


def test_prod_preserva_extraccion_negativa_y_pads_sin_datos(tmp_path):
    doc = _doc()
    doc['pads']['OXIDOS']['pilas'][0]['rec'] = [0.5, 0.2, 1.0]
    doc['pads']['SULFUROS']['pilas'] = []
    path = tmp_path / 'solo_ox.xlsx'
    report.escribir_libro(doc, path)
    book = load_workbook(path)
    assert book['Prod Oxidos']['B6'].value == pytest.approx(-0.3)
    assert 'Prod Sulfuros' in book.sheetnames
    assert book['Rec Ox']['B4'].value == 1.0
    assert len(book['Curvas Sulfuro']._charts) == 0


def test_recuperacion_maxima_no_confunde_maximo_con_ultimo_punto(tmp_path):
    doc = _doc()
    doc['pads']['OXIDOS']['pilas'][0]['rec'] = [2.0, 1.0, 0.5]
    path = tmp_path / 'curva_con_descenso.xlsx'
    report.escribir_libro(doc, path)
    book = load_workbook(path)
    assert book['Rec Ox']['B3'].value == 2.0
    assert book['Rec Ox']['B4'].value == 0.5
    assert book['Rec Ox']['B12'].value == 0.5


def test_prod_marca_run_y_periodo_ausentes_sin_inventar_metadatos(tmp_path):
    doc = _doc()
    doc["casos"] = [dict(id=19, desde="2026-10-01", hasta="2026-10-04")]
    path = tmp_path / "caso_sin_run.xlsx"
    report.escribir_libro(doc, path)
    book = load_workbook(path)
    assert book["Prod Oxidos"]["A2"].value == "Caso 19 / run no disponible (2026-10-01–2026-10-04)"