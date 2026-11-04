"""Entradas del ajuste de Sulfuros para un Caso cualquiera; sin SQL."""
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curvas_recon.sulfide_db_inputs import build_sulfide_rows, make_source_provider
from curvas_recon.sulfide_inputs import SulfideInputError, load_sulfide_inputs
from curvas_recon.sulfide_method import reconcile_sulfides

START, END = date(2026, 10, 1), date(2026, 10, 7)
DAYS = [START + timedelta(days=i) for i in range(7)]


def curve(first, pct_per_day, last=END):
    ds = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return {'dates': ds, 'values': [pct_per_day * i for i in range(len(ds))]}


def setup(young_birth=date(2026, 9, 20), mature_birth=date(2026, 6, 1)):
    index = pd.DatetimeIndex([pd.Timestamp(d) for d in DAYS])
    material = {
        'riego': pd.DataFrame({'P07': [100.0] * 7, 'P24': [100.0] * 7}, index=index),
        'cu_riego': pd.DataFrame({'cu': [1.0] * 7}, index=index),
        'drena_cu': pd.DataFrame({'P07': [2.0] * 7, 'P24': [2.0] * 7}, index=index),
    }
    curves = {7: curve(date(2026, 9, 25), 0.1), 24: curve(young_birth, 0.2)}
    wip = {'P07': {'CuTf': 100.0}, 'P24': {'CuTf': 100.0}}
    first = {'P07': mature_birth, 'P24': young_birth}
    return material, curves, wip, first


def test_rows_cover_baselines_and_window_and_flag_profile_as_modeled():
    rows = build_sulfide_rows(START, END, *setup())
    p24 = [r for r in rows if r['pile'] == 'P24']
    # La ventana parte el 1 de octubre: el dia previo y el cierre de septiembre coinciden.
    assert sorted(r['date'] for r in p24) == [date(2026, 9, 30).isoformat(), *[d.isoformat() for d in DAYS]]
    assert all('not measured' in r['drainage_profile_source'] for r in p24 if r['date'] >= '2026-10-01')
    mature_window = [r for r in rows if r['pile'] == 'P07' and r['date'] >= '2026-10-01']
    assert all('profile_q_drenaje_m3h' not in r for r in mature_window)


def test_any_case_closes_through_the_common_loader_and_method():
    material, curves, wip, first = setup()
    provider = make_source_provider(material, curves, wip, first, {'run_id': 55})
    anchor = {'SULFUROS': {'net_cu_target_t': 0.0}}
    # El objetivo se fija en lo que ya entregan las maduras mas un aporte positivo.
    base = load_sulfide_inputs(START, END, 99, {'SULFUROS': {'net_cu_target_t': 1.0}}, source_provider=provider)
    assert base['source_ids'] == {'case_id': 99, 'solver_run_id': 55}
    rows = base['rows']
    mature_end = next(r for r in rows if r['pile'] == 'P07' and r['date'] == END.isoformat())
    mature_prev = next(r for r in rows if r['pile'] == 'P07' and r['date'] == (START - timedelta(days=1)).isoformat())
    held = 100.0 * (mature_end['observed_pct'] - mature_prev['official_pct']) / 100
    out, audit = reconcile_sulfides(rows, START, END, held + 0.4)
    assert audit['young'] == [('SULFUROS', 'P24', audit['young'][0][2])]
    assert [m[1] for m in audit['mature']] == ['P07']
    assert audit['net_residual_t'] == pytest.approx(0.0, abs=1e-9)


def test_missing_measured_recovery_or_irrigation_is_rejected_not_filled():
    material, curves, wip, first = setup()
    curves[7]['dates'] = curves[7]['dates'][:-1]; curves[7]['values'] = curves[7]['values'][:-1]
    with pytest.raises(SulfideInputError, match='P07.*recuperacion medida'):
        build_sulfide_rows(START, END, material, curves, wip, first)
    material, curves, wip, first = setup()
    material['riego'].loc[pd.Timestamp(DAYS[3]), 'P24'] = 0.0
    with pytest.raises(SulfideInputError, match='P24.*riego nulo'):
        build_sulfide_rows(START, END, material, curves, wip, first)
    material, curves, wip, first = setup()
    wip['P24'] = {'CuTf': float('nan')}
    with pytest.raises(SulfideInputError, match='Cu apilado'):
        build_sulfide_rows(START, END, material, curves, wip, first)
