"""Nucleo "maduras fijas, nuevas moviles": cierre, bordes, infactibilidad, cadena."""
from copy import deepcopy
from datetime import date, timedelta

import pandas as pd
import pytest

from curvas_recon.maduras_nuevas import (
    CoverageError, InfeasibleError, MadurasError, carry_previous_result,
    direct_recovery_series, reconcile_chain, reconcile_pad,
)
from curvas_recon.test_maduras_support import expected_target, mixed_pad, pile_rows

START, END = '2026-09-01', '2026-09-07'


@pytest.mark.parametrize('pad', ['SULFUROS', 'OXIDOS'])
def test_exact_closure_and_lambda_recovered_for_both_pads(pad):
    rows = mixed_pad(pad)
    target = expected_target(rows, START, END, 0.8)
    out, audit = reconcile_pad(rows, START, END, target, pad=pad)
    assert audit['lambda'] == pytest.approx(0.8, rel=1e-12)
    assert audit['curve_net_t'] == pytest.approx(target, abs=1e-9)
    assert abs(audit['net_residual_t']) < 1e-9
    # Independent check: recovery curves at Case end reproduce the target.
    by_key = {}
    for r in out:
        by_key.setdefault((r['pile'], r['campaign']), {})[r['date']] = r
    net = 0.0
    for (pile, _), days in by_key.items():
        base_day = date.fromisoformat(min(d for d in days if d >= START)) - timedelta(days=1)
        base = days.get(base_day.isoformat(), {}).get('official_pct', 0.0)
        net += days[END]['cu_apilado_t'] * (days[END]['reconciled_pct'] - base) / 100
    assert net == pytest.approx(target, abs=1e-9)


def test_classes_mature_young_boundary_and_birth_in_window():
    rows = mixed_pad()
    target = expected_target(rows, START, END, 0.8)
    _, audit = reconcile_pad(rows, START, END, target, pad='SULFUROS')
    keys = lambda names: {k[1] for k in names}
    assert keys(audit['mature']) == {'P01', 'P02', 'P03'}
    assert keys(audit['exact_30_pending']) == {'P04'}
    assert keys(audit['young']) == {'P05', 'P06'}
    assert keys(audit['born_in_window']) == {'P06'}
    assert audit['age_by_pile'][('SULFUROS', 'P04', 11)] == 30


def test_mature_exact_observed_boundary_official_and_input_untouched():
    rows = mixed_pad()
    original = deepcopy(rows)
    target = expected_target(rows, START, END, 0.8)
    out, _ = reconcile_pad(rows, START, END, target, pad='SULFUROS')
    assert rows == original
    for r in out:
        in_case = START <= r['date'] <= END
        if r['pile'] in ('P01', 'P02', 'P03') and in_case:
            assert r['reconciled_pct'] == r['observed_pct'] != r['official_pct']
            assert r['recovery_source'] == 'observed'
            assert 'fitted_q_drenaje_m3h' not in r
        if r['pile'] == 'P04' and in_case:
            assert r['reconciled_pct'] == r['official_pct']
            assert r['recovery_source'] == 'official'


@pytest.mark.parametrize('birth,kind', [
    ('2026-08-09', 'young'),      # 29 dias
    ('2026-08-08', 'boundary'),   # exactamente 30
    ('2026-08-07', 'mature'),     # 31 dias
])
def test_age_threshold_is_30_days_calendar_at_case_end(birth, kind):
    rows = (pile_rows('SULFUROS', 'P01', birth='2025-10-01', start=START, end=END, rec0=60)
            + pile_rows('SULFUROS', 'P02', birth=birth, start=START, end=END, rec0=20)
            + pile_rows('SULFUROS', 'P03', birth='2026-08-25', start=START, end=END, rec0=8))
    target = expected_target(rows, START, END, 0.9)
    _, audit = reconcile_pad(rows, START, END, target, pad='SULFUROS')
    name = {'young': 'young', 'boundary': 'exact_30_pending', 'mature': 'mature'}[kind]
    assert 'P02' in {k[1] for k in audit[name]}
    assert audit['lambda'] == pytest.approx(0.9)


def test_protected_history_rows_are_identical_and_not_annotated():
    rows = mixed_pad()
    target = expected_target(rows, START, END, 0.8)
    out, audit = reconcile_pad(rows, START, END, target, pad='SULFUROS')
    history = [i for i, r in enumerate(rows) if r['date'] < START]
    assert history and len(audit['protected_history']) == len(history)
    for i in history:
        assert out[i] == rows[i]
        assert 'reconciled_pct' not in out[i]


def test_birth_mid_window_starts_at_birth_without_filling_measurements():
    rows = mixed_pad()
    born = [r for r in rows if r['pile'] == 'P06']
    assert born[0]['date'] == '2026-09-04' and len(born) == 4          # sin filas antes de nacer
    target = expected_target(rows, START, END, 0.8)
    out, audit = reconcile_pad(rows, START, END, target, pad='SULFUROS')
    out_born = [r for r in out if r['pile'] == 'P06']
    assert [r['date'] for r in out_born] == ['2026-09-04', '2026-09-05', '2026-09-06', '2026-09-07']
    assert audit['baseline_by_pile'][('SULFUROS', 'P06', 11)] == {
        'pct': 0.0, 'source': 'campaign_birth_zero', 'day': '2026-09-03'}
    assert out_born[0]['recovery_source'] == 'net_fit'
    # Recuperacion parte de 0 y acumula solo los flujos desde el nacimiento.
    first = out_born[0]
    expected_first = 100 * .024 * (0.8 * first['profile_q_drenaje_m3h'] * first['cu_drenaje_gL']
                                   - first['q_riego_m3h'] * first['cu_riego_gL']) / first['cu_apilado_t']
    assert first['reconciled_pct'] == pytest.approx(expected_first)


def test_birth_mid_window_uses_existing_day_before_birth_as_baseline_and_keeps_prebirth_rows():
    rows = (pile_rows('SULFUROS', 'P01', birth='2025-10-01', start=START, end=END, rec0=60)
            + pile_rows('SULFUROS', 'P02', birth='2026-09-04', start=START, end=END, rec0=0.01,
                        first_row='2026-09-02', pct_per_day=0.002))
    target = expected_target(rows, START, END, 1.0)
    out, audit = reconcile_pad(rows, START, END, target, pad='SULFUROS')
    base = audit['baseline_by_pile'][('SULFUROS', 'P02', 11)]
    assert base['source'] == 'row' and base['day'] == '2026-09-03'
    pre = [r for r in out if r['pile'] == 'P02' and r['date'] < '2026-09-04']
    assert pre and all(r['reconciled_pct'] == r['official_pct'] for r in pre)
    assert audit['lambda'] == pytest.approx(1.0)


def test_missing_day_after_birth_or_missing_baseline_fails_coverage_without_filling():
    rows = mixed_pad()
    target = expected_target(rows, START, END, 0.8)
    holes = [r for r in rows if not (r['pile'] == 'P06' and r['date'] == '2026-09-06')]
    with pytest.raises(CoverageError, match='incomplete daily coverage.*P06'):
        reconcile_pad(holes, START, END, target, pad='SULFUROS')
    no_base = [r for r in rows if not (r['pile'] == 'P05' and r['date'] == '2026-08-31')]
    with pytest.raises(CoverageError, match='missing prior baseline.*P05'):
        reconcile_pad(no_base, START, END, target, pad='SULFUROS')


def test_cap_qd_le_qr_is_explained_not_silently_clipped():
    rows = mixed_pad()
    target = expected_target(rows, START, END, 1.6)      # 80/100 -> tope ~1.25
    with pytest.raises(InfeasibleError, match=r'Qd <= Qr.*P0[56]') as err:
        reconcile_pad(rows, START, END, target, pad='SULFUROS')
    assert err.value.details['lambda_required'] == pytest.approx(1.6)
    assert err.value.details['lambda_cap'] < 1.6
    assert 'alcanzable' in str(err.value)


def test_lambda_outside_reasonable_bounds_and_overridable():
    rows = mixed_pad()
    low = expected_target(rows, START, END, 0.05)
    with pytest.raises(InfeasibleError, match='cota minima'):
        reconcile_pad(rows, START, END, low, pad='SULFUROS')
    _, audit = reconcile_pad(rows, START, END, low, pad='SULFUROS', lambda_bounds=(0.01, 5.0))
    assert audit['lambda'] == pytest.approx(0.05)


def test_young_irrigation_alone_exceeds_target_is_infeasible():
    rows = mixed_pad()
    held_only = expected_target(rows, START, END, 0.0)
    with pytest.raises(InfeasibleError, match='cota minima'):
        reconcile_pad(rows, START, END, held_only - 50, pad='SULFUROS')


def test_no_young_requires_protected_piles_to_close_by_themselves():
    rows = pile_rows('SULFUROS', 'P01', birth='2025-10-01', start=START, end=END, rec0=60)
    held = expected_target(rows, START, END, 0)
    out, audit = reconcile_pad(rows, START, END, held, pad='SULFUROS')
    assert audit['lambda'] is None and audit['young'] == []
    with pytest.raises(InfeasibleError, match='no hay pilas nuevas'):
        reconcile_pad(rows, START, END, held + 1, pad='SULFUROS')


def test_zero_drainage_profile_cannot_be_scaled():
    rows = mixed_pad()
    for r in rows:
        if r['pile'] in ('P05', 'P06') and 'profile_q_drenaje_m3h' in r:
            r['profile_q_drenaje_m3h'] = 0.0
    with pytest.raises(InfeasibleError, match='no entrega Cu'):
        reconcile_pad(rows, START, END, 10.0, pad='SULFUROS')


def test_other_pad_rows_pass_through_and_pad_aliases():
    su = mixed_pad('SU')
    ox = mixed_pad('OX')
    target = expected_target(su, START, END, 0.7)
    out, audit = reconcile_pad(su + ox, START, END, target, pad='SULFUROS')
    assert audit['pad'] == 'SULFUROS' and audit['lambda'] == pytest.approx(0.7)
    assert out[len(su):] == ox
    with pytest.raises(MadurasError):
        reconcile_pad(su, START, END, 0.0, pad='LIXIVIACION')


def _two_case_rows():
    s1, e1, s2, e2 = '2026-09-01', '2026-09-07', '2026-09-08', '2026-09-14'
    rows = []
    for pile, birth, cu, rec0 in (('P01', '2025-10-01', 5000, 60), ('P02', '2025-12-15', 4000, 50),
                                  ('P05', '2026-08-20', 2000, 8), ('P06', '2026-09-04', 1800, 0.0)):
        rows += pile_rows('SULFUROS', pile, birth=birth, start=s1, end=e2, cu_tf=cu, rec0=rec0,
                          first_row='2026-09-04' if pile == 'P06' else None)
    return rows, s1, e1, s2, e2


FLOW_FIELDS = ('q_riego_m3h', 'cu_riego_gL', 'cu_drenaje_gL', 'profile_q_drenaje_m3h', 'drainage_profile_source')


def _case_view(rows, first, last):
    """Lo que ve un Caso: filas hasta su cierre y flujos solo de su ventana."""
    keep = []
    for r in rows:
        r = deepcopy(r)
        if not (first <= r['date'] <= last):
            for f in FLOW_FIELDS:
                r.pop(f, None)
        if r['date'] <= last:
            keep.append(r)
    return keep


def test_chain_consecutive_cases_protects_history_and_each_case_has_its_lambda():
    rows, s1, e1, s2, e2 = _two_case_rows()
    r1, r2 = _case_view(rows, s1, e1), _case_view(rows, s2, e2)
    t1 = expected_target(r1, s1, e1, 0.8)
    out1, _ = reconcile_pad(r1, s1, e1, t1, pad='SULFUROS')
    r2_carried = carry_previous_result(r2, out1, s1, e1, pad='SULFUROS')
    t2 = expected_target(r2_carried, s2, e2, 0.6)          # linea base = resultado del Caso 1
    (c1, a1), (c2, a2) = reconcile_chain(
        [dict(rows=r1, start=s1, end=e1, target_net_t=t1),
         dict(rows=r2, start=s2, end=e2, target_net_t=t2)], pad='SULFUROS')
    assert c1 == out1
    assert a1['lambda'] == pytest.approx(0.8) and a2['lambda'] == pytest.approx(0.6)
    prior = {(r['pile'], r['date']): r['reconciled_pct'] for r in out1 if s1 <= r['date'] <= e1}
    for r in c2:
        if s1 <= r['date'] <= e1 and (r['pile'], r['date']) in prior:
            assert r['official_pct'] == prior[(r['pile'], r['date'])]
            assert r['baseline_source'] == 'previous_case_result'
            assert 'reconciled_pct' not in r              # historia: el Caso 2 no la mueve
    assert a2['baseline_by_pile'][('SULFUROS', 'P05', 11)]['pct'] == prior[('P05', e1)]
    # Cierre del Caso 2 desde su linea base heredada, calculado aparte.
    net2 = 0.0
    for r in c2:
        if r['date'] == e2:
            base = next(x['official_pct'] for x in c2 if x['pile'] == r['pile'] and x['date'] == e1)
            net2 += r['cu_apilado_t'] * (r['reconciled_pct'] - base) / 100
    assert net2 == pytest.approx(t2, abs=1e-9)
    # La recuperacion de una nueva es continua entre Casos (sin salto en la frontera).
    p5 = sorted((r['date'], r.get('reconciled_pct', r['official_pct'])) for r in c2 if r['pile'] == 'P05'
                if r['date'] >= e1)
    assert p5[0][1] == prior[('P05', e1)] and p5[1][1] > p5[0][1]


def test_chain_requires_consecutive_windows():
    rows = mixed_pad()
    target = expected_target(rows, START, END, 0.8)
    with pytest.raises(MadurasError, match='no consecutivos'):
        reconcile_chain([dict(rows=rows, start=START, end=END, target_net_t=target),
                         dict(rows=rows, start='2026-09-09', end='2026-09-15', target_net_t=0.0)],
                        pad='SULFUROS')


def _recovery_res(rows, target):
    out, audit = reconcile_pad(rows, START, END, target, pad='SULFUROS')
    return dict(local_direct_recovery=True, recovery_rows=out,
                week_start=pd.Timestamp(START), week_end=pd.Timestamp(END), audit=audit)


def test_direct_recovery_series_interface():
    rows = mixed_pad()
    res = _recovery_res(rows, expected_target(rows, START, END, 0.8))
    series = direct_recovery_series(res)
    assert set(series) == {('SULFUROS', n) for n in range(1, 7)}
    s5 = series[('SULFUROS', 5)]
    assert isinstance(s5, pd.Series) and isinstance(s5.index, pd.DatetimeIndex)
    assert s5.index.is_monotonic_increasing and s5.index.name == 'date'
    assert s5.index[0] < pd.Timestamp(START)                      # incluye historia protegida
    expected = {r['date']: r['reconciled_pct'] for r in res['recovery_rows']
                if r['pile'] == 'P05' and 'reconciled_pct' in r}
    assert all(s5[pd.Timestamp(day)] == pytest.approx(v) for day, v in expected.items())
    assert s5.attrs['campaign'] == 11 and s5.attrs['cu_apilado_t'] == 2000
    assert s5.attrs['sources'][pd.Timestamp(END)] == 'net_fit'
    # Mature: serie igual a la observada dentro del Caso.
    s1 = series[('SULFUROS', 1)]
    assert s1[pd.Timestamp(END)] == next(r['observed_pct'] for r in rows
                                         if r['pile'] == 'P01' and r['date'] == END)
    only_case = direct_recovery_series(res, case_only=True)
    assert only_case[('SULFUROS', 5)].index.min() == pd.Timestamp(START)
    assert set(direct_recovery_series(res, with_campaign=True)) == {('SULFUROS', n, 11) for n in range(1, 7)}
    assert direct_recovery_series({'recovery_rows': res['recovery_rows']}) == {}     # no es local
    assert direct_recovery_series({}) == {}


def test_direct_recovery_series_rejects_ambiguous_campaigns():
    rows = mixed_pad() + pile_rows('SULFUROS', 'P01', birth='2025-10-01', start=START, end=END,
                                   campaign=10, rec0=90)
    res = _recovery_res(rows, expected_target(mixed_pad(), START, END, 0.8))
    with pytest.raises(MadurasError, match='varias campanas'):
        direct_recovery_series(res)
    assert ('SULFUROS', 1, 10) in direct_recovery_series(res, with_campaign=True)
