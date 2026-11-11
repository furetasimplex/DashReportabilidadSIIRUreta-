from contextlib import nullcontext
from datetime import date
from io import BytesIO
from types import SimpleNamespace

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from curvas_recon import db_pipeline as db
from curvas_recon import report_metodo as report

OPER = [(date(2026, 4, 1), 100.0, 80.0, 0.25, 2.0),
        (date(2026, 4, 2), 100.0, 80.0, 0.25, 2.0),
        (date(2026, 4, 3), 100.0, 80.0, 0.25, 2.0)]


class Cn:
    def __init__(self, tabla, missing=False):
        self.tabla, self.missing = tabla, missing

    def execute(self, q, p):
        sql = str(q)
        if 'dump_diario' in sql:
            if self.missing:
                raise RuntimeError('Invalid object name')
            return SimpleNamespace(fetchall=lambda: self.tabla)
        return SimpleNamespace(fetchall=lambda: OPER)


def _leer(monkeypatch, tabla, caso_ids=None, missing=False, asof='2026-04-03'):
    monkeypatch.setattr(report, 'connect',
                        lambda: nullcontext(Cn(tabla, missing)))
    return report.leer_dump(pd.Timestamp(asof), caso_ids=caso_ids)


def _t(d, fuente, caso, ap):
    return (date(2026, 4, d), fuente, caso, ap, 10.0, 9.0, 1.0, 3.0, f'obs{caso}')


def test_prioridad_reconciliacion_oficial_operacional(monkeypatch):
    tabla = [_t(1, 'oficial', None, 5.0), _t(1, 'reconciliacion', 3, 7.0),
             _t(1, 'reconciliacion', 9, 8.0), _t(2, 'oficial', None, 6.0)]
    out = _leer(monkeypatch, tabla, caso_ids=[3, 9])
    assert [r['fuente'] for r in out] == [
        'reconciliacion Caso 9', 'oficial', 'operacional']
    assert out[0]['aporte'] == 8.0 and out[0]['observacion'] == 'obs9'
    assert out[1]['aporte'] == 6.0
    assert out[2]['aporte'] == pytest.approx(3.24)
    # caso fuera de caso_ids se ignora
    out = _leer(monkeypatch, tabla, caso_ids=None)
    assert out[0]['fuente'] == 'oficial'


def test_fechas_solo_en_tabla_y_limite_asof(monkeypatch):
    tabla = [(date(2026, 3, 1), 'oficial', None, None, 1.0, 1.0, 1.0, 1.0, None),
             _t(5, 'oficial', None, 1.0)]
    out = _leer(monkeypatch, tabla)
    assert out[0]['fecha'] == pd.Timestamp('2026-03-01') and out[0]['aporte'] is None
    assert [r['fecha'].day for r in out] == [1, 1, 2, 3]
    assert all(r['fecha'] <= pd.Timestamp('2026-04-03') for r in out)


def test_tabla_inexistente_cae_a_operacional(monkeypatch):
    out = _leer(monkeypatch, [], missing=True)
    assert len(out) == 3 and {r['fuente'] for r in out} == {'operacional'}


def test_hoja_dump_columna_fuente():
    doc = {'dump': [dict(fecha=pd.Timestamp('2026-04-01'), aporte=1.0,
                         flujo_riego=2.0, flujo_salida=3.0, cu_feed=0.1,
                         cu_drenaje=0.2, observacion=None, fuente='oficial')]}
    book = Workbook()
    book.remove(book.active)
    report._escribir_dump(SimpleNamespace(book=book), doc)
    out = BytesIO()
    book.save(out)
    out.seek(0)
    rows = tuple(load_workbook(out)['Dump'].values)
    assert rows[0][-1] == 'Fuente' and rows[1][-1] == 'oficial' and len(rows[0]) == 8


# --- guardar_dump_reconciliado -------------------------------------------

class Eng:
    def __init__(self, flujos):
        self.flujos, self.calls = flujos, []

    def begin(self):
        eng = self

        class C:
            def __enter__(s):
                return s

            def __exit__(s, *a):
                eng.committed = a[0] is None

            def execute(s, q, p=None):
                eng.calls.append((str(q), p))
                if 'recon_resultado_flujo' in str(q):
                    return SimpleNamespace(fetchall=lambda: eng.flujos)
                return SimpleNamespace(fetchall=lambda: [])
        return C()


def _base(ap=(2.0, 2.0)):
    return [dict(fecha=pd.Timestamp('2026-04-0%d' % (i + 1)), aporte=a,
                 flujo_riego=100.0, flujo_salida=80.0, cu_feed=0.5,
                 cu_drenaje=2.0, observacion=None, fuente='oficial')
            for i, a in enumerate(ap)]


def _run(monkeypatch, flujos, base, model='hidrometalurgia_125_v2'):
    eng = Eng(flujos)
    monkeypatch.setattr(db, 'get_engine', lambda: eng)
    monkeypatch.setattr(report, 'leer_dump', lambda *a, **k: base)
    n = db.guardar_dump_reconciliado(7, 55, '2026-04-01', '2026-04-02', model)
    return n, eng


FLUJOS = [('F77', 200.0, 220.0, 100.0, 132.0),
          ('F51', 160.0, 144.0, 320.0, 288.0),
          ('F42', None, None, 5.0, 6.0)]


def test_factores_y_sql(monkeypatch):
    n, eng = _run(monkeypatch, FLUJOS, _base())
    assert n == 2 and eng.committed
    sqls = [c[0] for c in eng.calls]
    assert 'DELETE FROM' in sqls[1] and 'dump_diario' in sqls[1]
    assert eng.calls[1][1] == {'caso': 7}
    ins = [c for c in eng.calls if 'INSERT INTO' in c[0]]
    assert len(ins) == 2
    p = ins[0][1]
    assert p['qi'] == pytest.approx(100 * 1.1)
    assert p['qo'] == pytest.approx(80 * 0.9)
    # F77: ley_rec 0.6 / ley_med 0.5 = 1.2; F51: 2.0/2.0 = 1.0
    assert p['ci'] == pytest.approx(0.5 * 1.2)
    assert p['co'] == pytest.approx(2.0)
    assert p['ap'] == pytest.approx(2.0 * 6.0 / 4.0)
    assert p['caso'] == 7 and p['run'] == 55 and p['obs'] == 'Reconciliado Caso 7 run 55'


def test_modelo_distinto_no_escribe(monkeypatch):
    n, eng = _run(monkeypatch, FLUJOS, _base(), model='otro')
    assert n == 0 and eng.calls == []


def test_guardas_cero_y_none(monkeypatch):
    flujos = [('F77', 0.0, 10.0, None, 5.0), ('F51', 160.0, 144.0, 320.0, 288.0),
              ('F42', None, None, 5.0, 6.0)]
    n, eng = _run(monkeypatch, flujos, _base(ap=(None, 0.0)))
    p = [c[1] for c in eng.calls if 'INSERT INTO' in c[0]][0]
    assert p['qi'] is None and p['ci'] is None
    assert p['qo'] == pytest.approx(72.0)
    assert p['ap'] is None  # suma de aporte base = 0
    n, eng = _run(monkeypatch, [], _base())
    p = [c[1] for c in eng.calls if 'INSERT INTO' in c[0]][0]
    assert n == 2 and p['qi'] is None and p['qo'] is None and p['ap'] is None
