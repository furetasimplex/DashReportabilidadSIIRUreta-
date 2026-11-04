"""Entradas del ajuste de Sulfuros para un Caso cualquiera; sin SQL."""
import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from curvas_recon.sulfide_db_inputs import (
    FLAT_PROFILE_SOURCE, SAVED_PROFILE_SOURCE, build_sulfide_rows, make_source_provider)
from curvas_recon.sulfide_inputs import SulfideInputError, load_sulfide_inputs
from curvas_recon.sulfide_method import reconcile_sulfides


def case10009_series():
    """Series del Caso 10009 tal como las entregaria el dash, desde el paquete."""
    fx = json.loads((ROOT / 'test_fixtures/caso10009_sulfuros_net_inputs.json').read_text(encoding='utf-8'))
    history = csv.DictReader((ROOT / 'test_fixtures/caso10009_sulfuros_historia_agosto.csv')
                             .read_text(encoding='utf-8').splitlines())
    by = defaultdict(dict)
    for r in fx['rows']:
        by[r['pile']][r['date']] = r
    window = sorted(d for d in {r['date'] for r in fx['rows']} if d >= '2026-09-01')
    idx = pd.DatetimeIndex(window)
    material = {
        'riego': pd.DataFrame({p: [g[d]['q_riego_m3h'] for d in window] for p, g in by.items()}, index=idx),
        'cu_riego': pd.Series([by['P07'][d]['cu_riego_gL'] for d in window], index=idx),
        'drena_cu': pd.DataFrame({p: [g[d]['cu_drenaje_gL'] for d in window] for p, g in by.items()}, index=idx),
    }
    points = defaultdict(dict)
    for h in history:
        points[int(h['pile'][1:])][date.fromisoformat(h['date'])] = float(h['official_pct'])
    for p, g in by.items():
        for d, r in g.items():
            points[int(p[1:])].setdefault(date.fromisoformat(d), r['observed_pct'])
    curves = {k: {'dates': sorted(v), 'values': [v[d] for d in sorted(v)]} for k, v in points.items()}
    wip = {p: {'CuTf': g['2026-08-31']['cu_apilado_t']} for p, g in by.items()}
    first = {p: g['2026-08-31']['first_irrigation'] for p, g in by.items()}
    saved = {(r['pile'], r['date']): r['profile_q_drenaje_m3h'] for r in fx['rows']
             if r.get('profile_q_drenaje_m3h') is not None}
    return fx, material, curves, wip, first, saved


def test_generic_rows_reproduce_frozen_case_10009_exactly():
    fx, material, curves, wip, first, saved = case10009_series()
    rows, source = build_sulfide_rows('2026-09-01', '2026-09-07', material, curves, wip, first, saved)
    assert source == SAVED_PROFILE_SOURCE
    reference = {(r['pile'], r['date']): r for r in fx['rows']}
    assert {(r['pile'], r['date']) for r in rows} == set(reference)
    for row in rows:
        ref = reference[(row['pile'], row['date'])]
        for field in ('official_pct', 'observed_pct', 'cu_apilado_t', 'first_irrigation',
                      'q_riego_m3h', 'cu_riego_gL', 'cu_drenaje_gL', 'profile_q_drenaje_m3h'):
            if field == 'profile_q_drenaje_m3h' and row['pile'] not in ('P24', 'P25'):
                assert field not in row        # las maduras no usan perfil de drenaje
            elif ref.get(field) is not None:
                assert row[field] == pytest.approx(ref[field], abs=1e-12) if isinstance(ref[field], float) else row[field] == ref[field]
    out, audit = reconcile_sulfides(rows, '2026-09-01', '2026-09-07', fx['target_net_t'])
    end = {r['pile']: r['reconciled_pct'] for r in out if r['date'] == '2026-09-07'}
    assert audit['lambda'] == pytest.approx(0.7214427195956585, rel=1e-12)
    assert end['P24'] == pytest.approx(15.847805, abs=1e-6)
    assert end['P25'] == pytest.approx(5.480463, abs=1e-6)
    assert audit['net_residual_t'] == pytest.approx(0, abs=1e-9)


def test_without_complete_saved_profile_uses_flat_profile_for_all_young_piles():
    fx, material, curves, wip, first, saved = case10009_series()
    saved.pop(('P25', '2026-09-03'))
    rows, source = build_sulfide_rows('2026-09-01', '2026-09-07', material, curves, wip, first, saved)
    assert source == FLAT_PROFILE_SOURCE
    young = [r for r in rows if 'profile_q_drenaje_m3h' in r]
    assert all(r['profile_q_drenaje_m3h'] == r['q_riego_m3h'] for r in young)
    _, audit = reconcile_sulfides(rows, '2026-09-01', '2026-09-07', fx['target_net_t'])
    assert audit['lambda'] == pytest.approx(0.542865, abs=1e-6)


# --- casos sinteticos -------------------------------------------------------
START, END = date(2026, 10, 1), date(2026, 10, 7)
DAYS = [START + timedelta(days=i) for i in range(7)]


def curve(first, step, last=END):
    ds = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return {'dates': ds, 'values': [step * i for i in range(len(ds))]}


def synthetic(young_birth=date(2026, 9, 20)):
    index = pd.DatetimeIndex([pd.Timestamp(d) for d in DAYS])
    material = {
        'riego': pd.DataFrame({'P07': [100.0] * 7, 'P24': [100.0] * 7}, index=index),
        'cu_riego': pd.Series([1.0] * 7, index=index),
        'drena_cu': pd.DataFrame({'P07': [2.0] * 7, 'P24': [2.0] * 7}, index=index),
    }
    curves = {7: curve(date(2026, 8, 1), 0.1), 24: curve(young_birth, 0.2)}
    wip = {'P07': {'CuTf': 100.0}, 'P24': {'CuTf': 100.0}}
    first = {'P07': date(2026, 6, 1), 'P24': young_birth}
    return material, curves, wip, first


def close(rows, extra_t):
    held = sum(100.0 * (next(r['observed_pct'] for r in rows if r['pile'] == 'P07' and r['date'] == END.isoformat())
                        - next(r['official_pct'] for r in rows if r['pile'] == 'P07' and r['date'] == (START - timedelta(days=1)).isoformat())) / 100
               for _ in [0])
    return reconcile_sulfides(rows, START, END, held + extra_t)


def test_pile_born_inside_window_starts_from_zero_and_closes():
    material, curves, wip, first = synthetic(young_birth=date(2026, 10, 4))
    material['riego'].loc[:pd.Timestamp('2026-10-03'), 'P24'] = 0.0
    material['drena_cu'].loc[:pd.Timestamp('2026-10-03'), 'P24'] = float('nan')
    rows, _ = build_sulfide_rows(START, END, material, curves, wip, first)
    p24 = {r['date']: r for r in rows if r['pile'] == 'P24'}
    assert p24['2026-09-30']['official_pct'] == 0.0
    out, audit = close(rows, 0.3)
    pct = {r['date']: r['reconciled_pct'] for r in out if r['pile'] == 'P24' and r['date'] >= '2026-10-01'}
    assert pct['2026-10-01'] == pct['2026-10-03'] == 0.0
    assert pct['2026-10-07'] > 0
    assert audit['net_residual_t'] == pytest.approx(0, abs=1e-9)


def test_previous_campaign_of_the_same_pile_is_not_used_as_baseline():
    material, curves, wip, first = synthetic(young_birth=date(2026, 10, 2))
    old = curve(date(2026, 5, 1), 0.3, last=date(2026, 9, 1))           # campana anterior, ~37 %
    new = curve(date(2026, 10, 2), 0.2)
    curves[24] = {'dates': old['dates'] + new['dates'], 'values': old['values'] + new['values']}
    material['riego'].loc[pd.Timestamp('2026-10-01'), 'P24'] = 0.0
    rows, _ = build_sulfide_rows(START, END, material, curves, wip, first)
    p24 = {r['date']: r for r in rows if r['pile'] == 'P24'}
    assert p24['2026-09-30']['official_pct'] == 0.0


def test_provider_passes_common_loader_for_any_case():
    material, curves, wip, first = synthetic()
    provider = make_source_provider(material, curves, wip, first, {'run_id': 55})
    out = load_sulfide_inputs(START, END, 99, {'SULFUROS': {'net_cu_target_t': 1.0}}, source_provider=provider)
    assert out['source_ids'] == {'case_id': 99, 'solver_run_id': 55}
    assert out['metadata']['drainage_profile'] == FLAT_PROFILE_SOURCE


def test_mature_gap_inside_window_stays_a_gap_and_case_still_closes():
    material, curves, wip, first = synthetic()
    gap = date(2026, 10, 4)
    i = curves[7]['dates'].index(gap)
    del curves[7]['dates'][i], curves[7]['values'][i]
    rows, _ = build_sulfide_rows(START, END, material, curves, wip, first)
    assert next(r for r in rows if r['pile'] == 'P07' and r['date'] == gap.isoformat())['observed_pct'] is None
    out, audit = close(rows, 0.3)
    p07 = {r['date']: r['reconciled_pct'] for r in out if r['pile'] == 'P07' and r['date'] >= START.isoformat()}
    assert p07[gap.isoformat()] is None
    assert p07[END.isoformat()] == next(r['observed_pct'] for r in rows if r['pile'] == 'P07' and r['date'] == END.isoformat())
    assert audit['net_residual_t'] == pytest.approx(0, abs=1e-9)


def test_missing_measurements_are_rejected_not_filled():
    material, curves, wip, first = synthetic()
    curves[7] = curve(date(2026, 8, 1), 0.1, last=END - timedelta(days=1))
    with pytest.raises(SulfideInputError, match='P07.*recuperacion medida'):
        build_sulfide_rows(START, END, material, curves, wip, first)
    material, curves, wip, first = synthetic()
    material['drena_cu'].loc[pd.Timestamp(DAYS[3]), 'P24'] = float('nan')
    with pytest.raises(SulfideInputError, match='P24.*cu_drenaje_gL'):
        build_sulfide_rows(START, END, material, curves, wip, first)
    material, curves, wip, first = synthetic()
    wip['P24'] = {'CuTf': float('nan')}
    with pytest.raises(SulfideInputError, match='Cu apilado'):
        build_sulfide_rows(START, END, material, curves, wip, first)
