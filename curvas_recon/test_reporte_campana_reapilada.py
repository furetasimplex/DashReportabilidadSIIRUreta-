"""Riego de la campana siguiente (pila reapilada) no debe sumarse a la campana vigente."""
import numpy as np
import pandas as pd
import pytest

from . import report_metodo as report


def _doc(monkeypatch, tmp_path, points):
    # campana 10: riega 20 dias, pausa de 150 dias, y reanuda con PLS fresco (20 g/L)
    days = pd.date_range('2026-01-01', periods=200)
    q = np.zeros(len(days))
    q[:20] = 10.0
    q[170:] = 10.0                       # reanudacion: otra campana
    drena = np.where(q > 0, 20.0, np.nan)
    apilado = {(2, 1): dict(camp=10, f0=days[0], f1=days[0], fin=100.0, tms=1000.0, ley=10.0),
               (2, 2): dict(camp=10, f0=days[0], f1=days[0], fin=100.0, tms=1000.0, ley=10.0)}
    monkeypatch.setattr(report, 'leer_apilado', lambda **kw: apilado)
    monkeypatch.setattr(report.E, 'load_riego', lambda *a: pd.DataFrame({'P01': q, 'P02': q}, index=days))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *a: pd.Series(0.4, index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *a: pd.DataFrame({'P01': drena, 'P02': drena}, index=days))
    monkeypatch.setattr(report.E, 'FDRENA_MAX', 0.95)
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {
        1: [{'dates': [days[i] for i in points], 'values': [50.0] * len(points)}],
        2: [{'dates': [days[i] for i in points], 'values': [50.0] * len(points)}]})
    raw = {'piles': [dict(label='SULFUROS', parcela='P02', daily=[])]}
    runs = {1: dict(ws=days[150], we=days[160], caso={'run_id': 1}, pads={'SULFUROS': {'res': raw}})}
    return report.construir_doc(runs, end=days[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False), days


def test_riego_de_campana_siguiente_no_suma_a_la_vigente(monkeypatch, tmp_path):
    doc, days = _doc(monkeypatch, tmp_path, points=[10, 15])
    piles = {p['num']: p for p in doc['pads']['SULFUROS']['pilas']}
    for pile in piles.values():
        curve = [v for v in pile['rec_curve'] if v is not None]
        assert max(curve) < 100.0 * 1.0
        # tras el ultimo dia regado de la campana la curva queda plana
        assert pile['rec'][30:] == pytest.approx([pile['rec'][30]] * (len(pile['rec']) - 30))
        assert pile['dias_riego'] == 20


def test_pila_inactiva_en_casos_se_ancla_a_puntos_oficiales_posteriores(monkeypatch, tmp_path):
    # P01 no aparece en ningun Caso (ventana 150..160): sus puntos medidos de la ventana anclan
    doc, days = _doc(monkeypatch, tmp_path, points=[10, 155])
    p01 = next(p for p in doc['pads']['SULFUROS']['pilas'] if p['num'] == 1)
    assert p01['rec'][155] == pytest.approx(50.0)
    assert p01['rec'][199] == pytest.approx(50.0)
