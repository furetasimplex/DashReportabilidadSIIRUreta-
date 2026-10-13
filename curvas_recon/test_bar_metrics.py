"""Regresiones del gráfico agregado del Caso con fuentes inyectadas."""
import pandas as pd

from . import pad_dashboard as dash


def _mat():
    day = pd.Timestamp('2026-08-17')
    return {
        'riego': pd.DataFrame({'P1': [2.0]}, index=[day]),
        'cu_riego': pd.Series([1.0], index=[day]),
        'drena_cu': pd.DataFrame({'P1': [3.0]}, index=[day]),
    }


def test_week_pila_metrics_uses_daily_rows_for_timestamp_window(monkeypatch):
    day = pd.Timestamp('2026-08-17')
    monkeypatch.setattr(dash, 'get_material_id', lambda conn, label: 7)
    monkeypatch.setattr(dash, 'load_pila_daily_history', lambda *args: [
        {'semana_lunes': day, 'dia_offset': 0, 'q': 2.0, 'cu_riego': 1.0,
         'cu_drena': 3.0, 'fdrena': 0.8},
        # Otro Caso puede compartir lunes y extenderse más días.
        {'semana_lunes': day, 'dia_offset': 1, 'q': 10.0, 'cu_riego': 1.0,
         'cu_drena': 3.0, 'fdrena': 0.8},
    ])
    monkeypatch.setattr(dash, 'load_pila_history', lambda *args: [])

    got = dash._week_pila_metrics(
        object(), 'OXIDOS', 'P1', day, _mat(),
        {'W': 0.144, 'Z': 0.048, 'n_days': 1, 'n_irr': 1},
        week_end=day,
    )

    assert got['q_total_rec'] == 48.0
    assert got['mass_rec'] == pytest.approx(0.0672)


def test_week_pila_metrics_weekly_fallback_uses_normalized_date(monkeypatch):
    day = pd.Timestamp('2026-08-17')
    monkeypatch.setattr(dash, 'get_material_id', lambda conn, label: 7)
    monkeypatch.setattr(dash, 'load_pila_daily_history', lambda *args: [])
    monkeypatch.setattr(dash, 'load_pila_history', lambda *args: [{
        'semana_lunes': day, 'q_mean': 2.0, 'cu_riego_mean': 1.0,
        'cu_drena_mean': 3.0, 'fdrena': 0.8,
    }])

    got = dash._week_pila_metrics(
        object(), 'OXIDOS', 'P1', day, _mat(),
        {'W': 0.144, 'Z': 0.048, 'n_days': 1, 'n_irr': 1},
        week_end=day,
    )

    assert got['q_total_rec'] == 48.0
    assert got['mass_rec'] == pytest.approx(0.0672)


def test_week_pila_metrics_preserves_missing_measured_cu_as_missing(monkeypatch):
    monkeypatch.setattr(dash, 'get_material_id', lambda conn, label: 7)
    monkeypatch.setattr(dash, 'load_pila_daily_history', lambda *args: [])
    monkeypatch.setattr(dash, 'load_pila_history', lambda *args: [])
    got = dash._week_pila_metrics(
        object(), 'OXIDOS', 'P1', pd.Timestamp('2026-08-17'), _mat(),
        {'W': 0.0, 'Z': 0.0, 'n_days': 0, 'n_irr': 1},
    )

    assert got['mass_med'] is None


import pytest
