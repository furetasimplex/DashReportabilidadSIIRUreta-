from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest
from openpyxl import load_workbook

from . import report_metodo as report
from .test_reporte_formato_prod import _pile


def _doc(label, nums, n=4):
    pilas = [_pile(label, k, 'P%02d' % k, '2026-09-28', [float(i + 1) * (1 + k / 100) for i in range(n)])
             for k in nums]
    for q in pilas:
        q['rl_accum_curve'] = [0.1 * (i + 1) for i in range(n)]
    other = 'SULFUROS' if label == 'OXIDOS' else 'OXIDOS'
    return dict(end='2026-10-01', corte_planta='2026-10-12', casos=[],
                pads={label: dict(desde='2026-09-28', pilas=pilas),
                      other: dict(desde='2026-09-28', pilas=[])})


def test_prod_total_y_mensual_coinciden_con_diario(tmp_path):
    doc = _doc('OXIDOS', [1, 2, 9])
    # el mes cambia a mitad de serie
    for q in doc['pads']['OXIDOS']['pilas']:
        q['ini'] = '2026-09-29'
    path = tmp_path / 'r.xlsx'
    report.escribir_libro(doc, path)
    ws = load_workbook(path)['Prod Oxidos']
    hdr = [c.value for c in ws[4]]
    t = hdr.index('Total Prod') + 1
    assert hdr[t - 2] is None
    nlast = t - 2                      # ultima columna de parcela
    for r in range(5, 9):
        vals = [ws.cell(r, c).value or 0 for c in range(2, nlast + 1)]
        assert ws.cell(r, t).value == pytest.approx(sum(vals))
    m = hdr.index('Mes') + 1
    assert hdr[m - 2] is None and ws.cell(3, m).value == 'Producción mensual [t Cu]'
    assert hdr[m:m + nlast - 1] == hdr[1:nlast] and hdr[-1] == 'Total'
    assert [ws.cell(r, m).value for r in (5, 6)] == ['2026-09', '2026-10']
    for k in range(nlast - 1):
        for r, mes in ((5, 9), (6, 10)):
            exp = sum(ws.cell(rr, 2 + k).value or 0 for rr in range(5, 9) if ws.cell(rr, 1).value.month == mes)
            assert (ws.cell(r, m + 1 + k).value or 0) == pytest.approx(exp)
    tot = [ws.cell(r, len(hdr)).value for r in (5, 6)]
    assert sum(tot) == pytest.approx(sum(ws.cell(r, t).value for r in range(5, 9)))


def _t(c):
    return ''.join(r.t for p in c.title.tx.rich.p for r in p.r)


def test_graficos_agrupados_como_oficial(tmp_path):
    doc = _doc('OXIDOS', [1, 8, 9, 30])
    path = tmp_path / 'g.xlsx'
    report.escribir_libro(doc, path)
    wb = load_workbook(path)
    ch = wb['Curvas Ox']._charts
    # por grupo: % recuperacion; luego los 3 de toneladas. La tasa de riego va en la hoja RL
    assert [c.series.__len__() for c in ch] == [2, 1, 1, 2, 1, 1]
    assert wb['RL Oxidos']._charts.__len__() == 6
    titulos = [_t(c) for c in ch]
    assert titulos[0] == '% Recuperación Parcelas 1-8 Óxidos'
    assert not any(t.startswith('Tasa de riego') for t in titulos)
    anchors = [(c.anchor._from.col, c.anchor._from.row) for c in ch]
    assert len(set(anchors)) == len(anchors)
    rl = [c for c in wb['RL Oxidos']._charts if not _t(c).startswith('Tasa de riego')]
    assert [_t(c) for c in rl] == [
        'Recuperación vs RL (P1-8 Oxidos)', 'Recuperación vs RL (P9-16 Oxidos)',
        'Recuperación vs RL (P24-P32 Oxidos)']


def test_riego_charts_pareados_y_hoja(tmp_path):
    doc = _doc('OXIDOS', [1, 8, 9, 30])
    for q in doc['pads']['OXIDOS']['pilas']:
        q['q_riego_curve'] = [10.0 + q['num'] + i for i in range(q['n'])]
    path = tmp_path / 'r.xlsx'
    report.escribir_libro(doc, path)
    wb = load_workbook(path)
    ch = wb['Curvas Ox']._charts
    rl = wb['RL Oxidos']._charts
    ext = [c for c in ch if _t(c).startswith('% Recuperación')]
    rie = [c for c in rl if _t(c).startswith('Tasa de riego')]
    assert len(ext) == len(rie) == 3
    fila_rl = max(c.anchor._from.row for c in rl if not _t(c).startswith('Tasa de riego'))
    for e, r in zip(ext, rie):
        assert _t(r) == _t(e).replace('% Recuperación', 'Tasa de riego')
        assert (e.x_axis.scaling.min, e.x_axis.scaling.max) == (r.x_axis.scaling.min, r.x_axis.scaling.max)
        assert r.x_axis.scaling.max is not None
        assert [s.tx.v for s in e.series] == [s.tx.v for s in r.series]   # mismo orden => mismos colores
        assert r.anchor._from.row > fila_rl                               # debajo de los graficos RL
        assert 'm3/h' in ''.join(x.t for p in r.y_axis.title.tx.rich.p for x in p.r)
    ws = wb['Riego Ox']
    assert wb.sheetnames.index('Riego Ox') == wb.sheetnames.index('RL Sulfuros') + 1
    assert [c.value for c in ws[1]][:2] == ['Dia de ciclo', 1]
    assert ws.cell(2, 1).value == 1 and ws.cell(2, 2).value == pytest.approx(11.0)
    assert ws.cell(5, 2).value == pytest.approx(14.0) and ws.cell(6, 2).value is None


def test_graficos_sulfuros_grupos(tmp_path):
    doc = _doc('SULFUROS', [21, 22, 3])
    path = tmp_path / 's.xlsx'
    report.escribir_libro(doc, path)
    wb = load_workbook(path)
    assert len(wb['Curvas Sulfuro']._charts) == 6
    assert len(wb['RL Sulfuros']._charts) == 6


def _dump(rows):
    class Cn:
        def execute(self, q, p):
            return SimpleNamespace(fetchall=lambda: rows)
    return Cn()


def test_dump_dias_invalidos_quedan_en_blanco_con_observacion(monkeypatch):
    rows = [
        (date(2026, 1, 1), 100.0, 80.0, 0.25, 2.0),    # valido
        (date(2026, 1, 2), 100.0, 0.0, 0.25, 2.0),     # salida sin medicion
        (date(2026, 1, 3), 0.0, 80.0, 0.25, 2.0),      # riego sin medicion
        (date(2026, 1, 4), 100.0, 80.0, 3.96, 2.0),    # ley riego fuera de rango
        (date(2026, 1, 5), 100.0, 80.0, None, 2.0),    # faltante
        (date(2026, 1, 6), 100.0, 80.0, 1.9, 2.0),     # negativo valido
    ]
    monkeypatch.setattr(report, 'connect', lambda: nullcontext(_dump(rows)))
    out = report.leer_dump(pd.Timestamp('2026-01-10'))
    assert out[0]['aporte'] == pytest.approx(3.24) and out[0]['observacion'] is None
    assert [r['aporte'] for r in out[1:5]] == [None] * 4
    assert [r['observacion'] for r in out[1:5]] == [
        'Flujo salida sin medición', 'Flujo riego sin medición',
        'Ley riego fuera de rango', 'Dato faltante en la fuente']
    assert out[5]['aporte'] < 0 and out[5]['observacion'] == 'Aporte negativo con datos válidos'
    assert out[1]['flujo_salida'] == 0.0 and out[3]['cu_feed'] == 3.96
