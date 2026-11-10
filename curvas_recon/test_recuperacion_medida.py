"""Recuperacion medida desde riego y Cu; contrasta con las lecturas reales de septiembre 2026."""
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from curvas_recon.recuperacion_medida import extend_recovery

D = lambda n: date(2026, 10, 1) + timedelta(days=n - 1)
FLAT = dict(cu_tf_t=100.0, first_irrigation=date(2026, 6, 1), until=D(5))


def series(value, days=range(2, 6)):
    return {D(n): value for n in days}


def test_formula_and_continuity_from_last_reading():
    rows, stop = extend_recovery(D(1), 50.0, q_riego=series(100.0), cu_riego=series(0.4), cu_drena=series(1.0), **FLAT)
    daily = 100 * 0.024 * (0.95 * 100 * 1.0 - 100 * 0.4) / 100.0
    assert stop is None and [d for d, _ in rows] == [D(n) for n in range(2, 6)]
    assert [p for _, p in rows] == pytest.approx([50.0 + daily * i for i in range(1, 5)])


def test_young_piles_are_never_completed():
    young = dict(FLAT, first_irrigation=D(1) - timedelta(days=30))     # 31 dias el 2-oct, 30 el 1-oct
    rows, stop = extend_recovery(D(1), 20.0, q_riego=series(100.0), cu_riego=series(0.4), cu_drena=series(1.0), **young)
    assert [d for d, _ in rows] == [D(n) for n in range(2, 6)] and stop is None   # 31 dias el 2-oct: ya es madura
    rows, stop = extend_recovery(D(1), 20.0, q_riego=series(100.0), cu_riego=series(0.4), cu_drena=series(1.0),
                                 **dict(FLAT, first_irrigation=D(1) - timedelta(days=29)))
    assert rows == [] and 'el metodo' in stop


@pytest.mark.parametrize('missing, expected', [('q', 'sin riego medido'), ('cr', 'Cu de riego'), ('cd', 'Cu de drenaje')])
def test_stops_at_first_unmeasurable_day_without_filling(missing, expected):
    q, cr, cd = series(100.0), series(0.4), series(1.0)
    {'q': q, 'cr': cr, 'cd': cd}[missing].pop(D(4))
    rows, stop = extend_recovery(D(1), 50.0, q_riego=q, cu_riego=cr, cu_drena=cd, **FLAT)
    assert [d for d, _ in rows] == [D(2), D(3)] and expected in stop and D(4).isoformat() in stop


def test_day_without_irrigation_adds_nothing_and_needs_no_concentrations():
    q = series(100.0); q[D(3)] = 0.0
    cr, cd = series(0.4), series(1.0); del cr[D(3)], cd[D(3)]
    rows, stop = extend_recovery(D(1), 50.0, q_riego=q, cu_riego=cr, cu_drena=cd, **FLAT)
    assert stop is None and rows[1][1] == pytest.approx(rows[0][1])


def test_reproduces_measured_september_recovery_of_mature_piles():
    fx = json.loads((ROOT / 'test_fixtures/caso10009_sulfuros_net_inputs.json').read_text(encoding='utf-8'))
    by = defaultdict(dict)
    for r in fx['rows']:
        by[r['pile']][r['date']] = r
    checked = 0
    for pile, g in by.items():
        base = g['2026-08-31']
        if (date(2026, 9, 7) - date.fromisoformat(base['first_irrigation'])).days <= 37:
            continue                                   # P23-P25 no estan en el rango validado
        win = {date.fromisoformat(d): r for d, r in g.items() if d >= '2026-09-01'}
        rows, stop = extend_recovery(
            date(2026, 8, 31), base['observed_pct'], base['cu_apilado_t'], base['first_irrigation'], date(2026, 9, 7),
            {d: r['q_riego_m3h'] for d, r in win.items()}, {d: r['cu_riego_gL'] for d, r in win.items()},
            {d: r['cu_drenaje_gL'] for d, r in win.items()})
        assert stop is None and len(rows) == 7
        assert abs(rows[-1][1] - g['2026-09-07']['observed_pct']) < 0.025, pile     # pp en 7 dias
        checked += 1
    assert checked == 15


def load_script():
    import importlib.util
    spec = importlib.util.spec_from_file_location('completar', ROOT / 'scripts' / 'completar_recuperaciones_medidas.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sql_guard_allows_selects_and_only_the_one_insert_when_applying():
    script = load_script()
    schema = 'dbo'
    select = 'SELECT a FROM dbo.Recuperaciones_pad'
    insert = 'INSERT INTO dbo.Recuperaciones_pad (Fecha_drenaje, PAD) VALUES (:a, :b)'
    assert script.statement_allowed(select, schema) and script.statement_allowed('WITH x AS (SELECT 1) SELECT * FROM x', schema)
    assert not script.statement_allowed(insert, schema)                       # prueba en seco: ni un INSERT
    assert script.statement_allowed(insert, schema, apply=True)
    for bad in ('INSERT INTO dbo.otra_tabla (a) VALUES (1)', 'UPDATE dbo.Recuperaciones_pad SET a=1',
                'DELETE FROM dbo.Recuperaciones_pad', 'INSERT INTO dbo.Recuperaciones_pad (a) SELECT 1; DROP TABLE x',
                'SELECT * INTO dbo.copia FROM dbo.Recuperaciones_pad', 'EXEC sp_x'):
        assert not script.statement_allowed(bad, schema, apply=True), bad


def test_plan_completes_only_mature_piles_with_complete_measurements_and_keeps_ids():
    from curvas_recon.recuperacion_medida import plan_completion
    base = {p: dict(fecha=D(1), pct=50.0, ids={'Parcela': int(p[1:]), 'Campana': 11}) for p in ('P10', 'P26', 'P30', 'P31')}
    base['P31']['fecha'] = date(2026, 6, 1)                                     # lectura base muy antigua
    first = {'P10': date(2026, 6, 1), 'P26': D(1) - timedelta(days=13), 'P30': date(2026, 6, 1), 'P31': date(2026, 6, 1)}
    q = {p: series(100.0) for p in first}
    cd = {p: series(1.0) for p in first}; del cd['P30'][D(3)]
    plan, report = plan_completion(base, {p: 100.0 for p in first}, first, q, series(0.4), cd, D(5), window_start=D(1))
    by = {r['pila']: r for r in report}
    assert by['P10']['estado'] == 'completa' and by['P10']['filas'] == 4
    assert by['P26']['estado'] == 'omitida' and 'el metodo' in by['P26']['motivo']
    assert by['P30']['estado'] == 'parcial' and by['P30']['filas'] == 1 and 'Cu de drenaje' in by['P30']['motivo']
    assert by['P31']['estado'] == 'omitida' and 'antes de la ventana' in by['P31']['motivo']
    assert {r['pila'] for r in plan} == {'P10', 'P30'} and all(r['ids']['Campana'] == 11 for r in plan)


def test_comparison_with_official_flags_differences_except_new_piles():
    from curvas_recon.recuperacion_medida import compare_with_official, plan_completion
    first = {p: date(2026, 6, 1) for p in ('P10', 'P11', 'P12')}
    first['P26'] = D(1) - timedelta(days=13)
    base = {p: dict(fecha=D(1), pct=50.0, ids={}) for p in first}
    plan, report = plan_completion(base, {p: 100.0 for p in first}, first, {p: series(100.0) for p in first},
                                   series(0.4), {p: series(1.0) for p in first}, D(5), window_start=D(1))
    calc = {r['fecha'].isoformat(): r['recuperacion_pct'] for r in plan if r['pila'] == 'P10'}
    official = {'P10': dict(calc), 'P11': {d: v + 0.2 for d, v in calc.items()}, 'P26': {D(5).isoformat(): 9.0}}
    rows, equal = compare_with_official(plan, report, official, tol_pp=0.05, tol_new_pp=0.05)
    by = {r['pila']: r for r in rows}
    assert by['P10']['estado'] == 'igual' and by['P10']['max_abs_pp'] == pytest.approx(0)
    assert by['P11']['estado'] == 'difiere' and by['P11']['max_abs_pp'] == pytest.approx(0.2)
    assert by['P12']['estado'] == 'sin curva oficial en esas fechas'
    assert by['P12']['estado'] == 'sin curva oficial en esas fechas' and by['P11']['estado'] == 'difiere'
    assert by['P26']['estado'].startswith('no completada')          # la pila nueva no se compara
    assert equal is False
    ok_rows, ok = compare_with_official([r for r in plan if r['pila'] == 'P10'], [r for r in report if r['pila'] in ('P10', 'P26')],
                                        official, 0.05)
    assert ok is True


def test_small_variations_are_accepted_more_loosely_for_relatively_new_piles():
    from curvas_recon.recuperacion_medida import compare_with_official, plan_completion
    first = {'P20': date(2026, 6, 1), 'P25': D(1) - timedelta(days=40)}      # 126+ dias y 44 dias al 5-oct
    base = {p: dict(fecha=D(1), pct=50.0, ids={}) for p in first}
    plan, report = plan_completion(base, {p: 5000.0 for p in first}, first, {p: series(100.0) for p in first},
                                   series(0.4), {p: series(1.0) for p in first}, D(5), window_start=D(1))
    calc = {p: {r['fecha'].isoformat(): r['recuperacion_pct'] for r in plan if r['pila'] == p} for p in first}
    shift = lambda p, delta: {d: v - delta for d, v in calc[p].items()}
    small = compare_with_official(plan, report, {'P20': shift('P20', 0.09), 'P25': shift('P25', 0.3)})
    assert [r['estado'] for r in small[0]] == ['igual', 'igual'] and small[1] is True           # pequena: ok en ambas
    assert small[0][1]['dif_final_cu_t'] == pytest.approx(0.3 * 5000 / 100)
    large = compare_with_official(plan, report, {'P20': shift('P20', 0.3), 'P25': shift('P25', 0.3)})
    assert [r['estado'] for r in large[0]] == ['difiere', 'igual'] and large[1] is False         # 0.3 pp es grande en una madura
    huge = compare_with_official(plan, report, {'P20': shift('P20', 0.09), 'P25': shift('P25', 1.2)})
    assert [r['estado'] for r in huge[0]] == ['igual', 'difiere']                                  # 1.2 pp es grande incluso en una nueva


def test_daily_diagnostics_recovers_the_drainage_factor_used_by_the_official_curve():
    from curvas_recon.recuperacion_medida import daily_diagnostics, plan_completion
    first = {'P25': date(2026, 6, 1)}
    base = {'P25': dict(fecha=D(1), pct=30.0, ids={})}
    q, cr, cd = {'P25': series(120.0)}, series(0.4), {'P25': series(5.0)}
    plan, _ = plan_completion(base, {'P25': 5000.0}, first, q, cr, cd, D(5), window_start=D(1))
    f = 0.93                                          # el oficial drena menos que el 0.95
    official, pct = {'P25': {D(1).isoformat(): 30.0}}, 30.0
    for n in range(2, 6):
        pct += 100 * 0.024 * (f * 120.0 * 5.0 - 120.0 * 0.4) / 5000.0
        official['P25'][D(n).isoformat()] = pct
    detail = daily_diagnostics(plan, base, {'P25': 5000.0}, q, cr, cd, official)
    assert [d['factor_drenaje_implicito'] for d in detail] == pytest.approx([0.93] * 4)
    # con f = 0.95 el oficial equivale a un Cu de drenaje de 5.0 * 0.93 / 0.95
    expected = 5.0 * 0.93 / 0.95
    assert [d['cu_drena_implicito_gL'] for d in detail] == pytest.approx([expected] * 4)
    assert all(d['dif_pp'] > 0 for d in detail) and detail[-1]['dif_pp'] > detail[0]['dif_pp']   # calculada sobre el oficial, creciendo


def test_piles_outside_the_official_report_are_not_counted_as_differences():
    from curvas_recon.recuperacion_medida import compare_with_official, plan_completion
    first = {'P10': date(2026, 6, 1), 'P07': date(2026, 6, 1)}
    base = {p: dict(fecha=D(1), pct=50.0, ids={}) for p in first}
    plan, report = plan_completion(base, {p: 100.0 for p in first}, first, {p: series(100.0) for p in first},
                                   series(0.4), {p: series(1.0) for p in first}, D(5), window_start=D(1))
    official = {'P10': {r['fecha'].isoformat(): r['recuperacion_pct'] for r in plan if r['pila'] == 'P10'}}
    rows, equal = compare_with_official(plan, report, official)
    assert {r['pila']: r['estado'] for r in rows} == {'P10': 'igual', 'P07': 'sin curva oficial en esas fechas'}
    assert equal is True
