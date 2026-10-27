from contextlib import nullcontext
from datetime import date
from io import BytesIO
from types import SimpleNamespace

import pandas as pd
from openpyxl import Workbook, load_workbook
import pytest

from . import report_metodo as report


def test_dump_query_is_select_and_uses_feed_dpls_sources(monkeypatch):
    class FakeConnection:
        query = ''

        def execute(self, query, params):
            self.query = str(query)
            assert params['hasta'] == pd.Timestamp('2026-04-03')
            assert params['desde'] == pd.Timestamp('2026-01-01')
            return SimpleNamespace(fetchall=lambda: [
                (date(2026, 4, 1), 100.0, 80.0, 0.25, 2.0)])

    fake = FakeConnection()
    monkeypatch.setattr(report, 'connect', lambda: nullcontext(fake))
    rows = report.leer_dump(pd.Timestamp('2026-04-02'))
    assert rows == [dict(fecha=pd.Timestamp('2026-04-01'), aporte=3.24,
                         flujo_riego=2400.0, flujo_salida=1920.0,
                         cu_feed=0.25, cu_drenaje=2.0)]
    sql = fake.query.upper()
    assert 'SELECT' in sql and 'FLUJO_FEED_DUMP_M3H' in sql and 'DUMP_FEED_CU' in sql
    assert not any(word in sql for word in ('INSERT', 'UPDATE', 'DELETE', 'EXEC '))


def test_writer_keeps_official_rl_matrix_and_dump_shape():
    doc = {
        'end': '2026-10-12',
        'pads': {
            'OXIDOS': {'pilas': [dict(num=1, rl_curve=[0.1, 0.2]),
                                dict(num=2, rl_curve=[0.3, 0.4])]},
            'SULFUROS': {'pilas': [dict(num=21, rl_curve=[0.5, 0.6])]},
        },
        'dump': [dict(fecha=pd.Timestamp('2026-04-01'), aporte=3.24,
                      flujo_riego=2400.0, flujo_salida=1920.0,
                      cu_feed=0.25, cu_drenaje=2.0)],
    }
    book = Workbook()
    book.remove(book.active)
    writer = SimpleNamespace(book=book)
    report._escribir_dump(writer, doc)
    report._escribir_rl(writer, doc)
    output = BytesIO()
    book.save(output)
    output.seek(0)
    check = load_workbook(output, data_only=True)
    assert check.sheetnames == ['Dump', 'RL Oxidos', 'RL Sulfuros']
    assert tuple(check['Dump'].values)[0] == (
        'Fecha', 'Aporte', 'Flujo riego dump [m3/dia]',
        'Flujo salida dump [m3/dia]', 'Concentracion riego ',
        'Concentracion drenaje')
    assert tuple(check['RL Oxidos'].values)[0][:3] == ('Parcela', 1, 2)
    assert tuple(check['RL Oxidos'].values)[1][:3] == (1, 0.1, 0.3)
    assert tuple(check['RL Oxidos'].values)[2][:3] == (2, pytest.approx(0.3), pytest.approx(0.7))
    assert tuple(check['RL Sulfuros'].values)[0][:2] == ('Parcela', 21)
    check.close()


def test_rl_uses_case_final_flow_and_does_not_add_cu_when_q_is_zero(monkeypatch):
    days = pd.date_range('2026-08-01', periods=5)
    apilado = {(1, 1): dict(camp=1, f0=days[0], f1=days[0], fin=100.0,
                            tms=1000.0, ley=10.0)}
    monkeypatch.setattr(report, 'leer_dump', lambda *args, **kwargs: [])
    monkeypatch.setattr(report, 'leer_apilado', lambda **kwargs: apilado)
    monkeypatch.setattr(report, 'leer_planta', lambda *args, **kwargs: {})
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {})
    monkeypatch.setattr(report.E, 'load_riego', lambda label, *args: (
        pd.DataFrame({'P01': [5.0, 4.0, 3.0, 2.0, 1.0]}, index=days)
        if label == 'OXIDOS' else pd.DataFrame(index=days)))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *args: pd.Series(0.5, index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *args: pd.DataFrame(
        {'P01': [2.0, 2.0, 2.0, 2.0, 2.0]}, index=days))
    daily = [
        dict(date=days[1], q_riego_final=10.0, q_pls_final=8.0, fino_pls_final=20.0,
             fino_riego_final=5.0),
        dict(date=days[2], q_riego_final=0.0, q_pls_final=4.0, fino_pls_final=5.0,
             fino_riego_final=None),
        dict(date=days[3], q_riego_final=0.0, q_pls_final=0.0, fino_pls_final=None,
             fino_riego_final=None),
        dict(date=days[4], q_riego_final=None, q_pls_final=None, fino_pls_final=None,
             fino_riego_final=None),
    ]
    raw = {'piles': [dict(label='OXIDOS', parcela='P01', daily=daily)]}
    runs = {17: dict(ws=days[1], we=days[4], caso={'run_id': 101},
                     pads={'OXIDOS': {'res': raw}})}
    doc = report.construir_doc(runs, end=days[-1], verbose=False)
    pile = doc['pads']['OXIDOS']['pilas'][0]
    assert pile['rl_curve'][:4] == pytest.approx([0.12, 0.24, 0.0, 0.0])
    assert pile['rl_accum_curve'][:4] == pytest.approx([0.12,0.36,0.36,0.36])
    assert pile['rl_accum_curve'][4] is None
    assert pile['rl_curve'][4] is None
    assert pile['rl'] is None
    assert pile['med'][2] > pile['med'][1]
    assert pile['rec'][2] > pile['rec'][1]
    assert pile['rec'][3] == pytest.approx(pile['rec'][2])


def test_positive_case_flow_with_missing_final_fino_is_rejected(monkeypatch):
    days = pd.date_range('2026-08-01', periods=2)
    apilado = {(1, 1): dict(camp=1, f0=days[0], f1=days[0], fin=100.0,
                            tms=1000.0, ley=10.0)}
    monkeypatch.setattr(report, 'leer_dump', lambda *args, **kwargs: [])
    monkeypatch.setattr(report, 'leer_apilado', lambda **kwargs: apilado)
    monkeypatch.setattr(report, 'leer_planta', lambda *args, **kwargs: {})
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {})
    monkeypatch.setattr(report.E, 'load_riego', lambda label, *args: (
        pd.DataFrame({'P01': [5.0, 4.0]}, index=days)
        if label == 'OXIDOS' else pd.DataFrame(index=days)))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *args: pd.Series(0.5, index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *args: pd.DataFrame(
        {'P01': [2.0, 2.0]}, index=days))
    raw = {'piles': [dict(label='OXIDOS', parcela='P01', daily=[dict(
        date=days[1], q_riego_final=10.0, q_pls_final=8.0,
        fino_pls_final=None, fino_riego_final=0.1)])]}
    runs = {17: dict(ws=days[1], we=days[1], caso={'run_id': 101},
                     pads={'OXIDOS': {'res': raw}})}
    with pytest.raises(ValueError, match='caso 17, P01, 2026-08-02'):
        report.construir_doc(runs, end=days[-1], verbose=False)
