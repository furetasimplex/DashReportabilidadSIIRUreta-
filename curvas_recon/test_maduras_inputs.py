"""Cargador generico SELECT-only con SQL simulado: identidad, fuentes y cierre."""
from datetime import date, timedelta
import re

import pytest
import sqlalchemy.engine

from curvas_recon.maduras_inputs import (
    MadurasInputError, assert_select_only, default_history_start, load_pad_inputs,
)
from curvas_recon.maduras_nuevas import as_date, reconcile_pad
from curvas_recon.test_maduras_support import DAY, expected_target, pile_rows

S, H = 'inventar_SpcHidr', 'DEV_SIIR.hidro'
START, END = date(2026, 9, 1), date(2026, 9, 7)
CASE, SOLVER_RUN, ALLOC_RUN = 20001, 30001, 777
MATERIAL_ID = {'OXIDO': 1, 'SULFURO': 2}
LAMBDA_TRUE = 0.75


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, clause, params=None):
        sql, params = str(clause), dict(params or {})
        self.db.statements.append((sql, params))
        return FakeResult(self.db.answer(sql, params))


class FakeEngine:
    def __init__(self, db):
        self.db = db

    def connect(self):
        return FakeConn(self.db)


class FakeDB:
    """SQL Server simulado: dos PAD, dos Casos consecutivos (1-7 y 8-14 sep)."""

    WINDOWS = {  # caso -> (inicio, fin, run oficial, run de asignacion)
        CASE: (START, END, SOLVER_RUN, ALLOC_RUN),
        CASE + 1: (date(2026, 9, 8), date(2026, 9, 14), SOLVER_RUN + 1, ALLOC_RUN + 1),
    }

    def __init__(self):
        self.statements = []
        kw = dict(start=START, end=date(2026, 9, 14), obs_delta=0.0)
        self.pads = {}
        for pad in ('SULFUROS', 'OXIDOS'):
            rows = []
            rows += pile_rows(pad, 'P01', birth='2025-10-01', cu_tf=5000, rec0=60, **kw)
            rows += pile_rows(pad, 'P02', birth='2025-12-15', cu_tf=4000, rec0=50, **kw)
            rows += pile_rows(pad, 'P04', birth='2026-08-08', cu_tf=2500, rec0=20, **kw)
            rows += pile_rows(pad, 'P05', birth='2026-08-20', cu_tf=2000, rec0=8, **kw)
            rows += pile_rows(pad, 'P06', birth='2026-09-04', cu_tf=1800, rec0=0.0, pct_per_day=0.1,
                              first_row='2026-09-04', **kw)
            self.pads[pad] = rows
        case1 = [r for r in self.pads['SULFUROS'] if r['date'] <= END.isoformat()]
        case1_ox = [r for r in self.pads['OXIDOS'] if r['date'] <= END.isoformat()]
        self.flows_by_run = {SOLVER_RUN: {'F29': expected_target(case1, START, END, LAMBDA_TRUE),
                                          'F25': expected_target(case1_ox, START, END, 0.65)},
                             SOLVER_RUN + 1: {'F29': 1.0, 'F25': 1.0}}
        self.flows = self.flows_by_run[SOLVER_RUN]
        self.targets = dict(self.flows)
        self.caso = [(c, f'Caso {c}', w[0], w[1], 'reconciliado', w[2],
                      'hidrometalurgia_125_v2', 'v2', 125) for c, w in self.WINDOWS.items()]
        self.runs = [(w[3], c, w[0], w[1], 'Flowsheet', True) for c, w in self.WINDOWS.items()]
        self.runs.append((ALLOC_RUN - 5, CASE, START, END, 'Flowsheet', True))   # corrida anterior
        self.extra_universe = {'P32': 'sin curva'}
        self.irrigation_extra = {}
        self.drop_recovery, self.drop_flow = set(), set()
        self.extra_recovery = []
        self.profile_override = {}

    # --- dispatch -------------------------------------------------------
    def answer(self, sql, p):
        if 'recon_caso c' in sql:
            return [r for r in self.caso if r[0] == p['caso']]
        if 'recon_resultado_flujo' in sql:
            flows = self.flows_by_run.get(p['run'], self.flows if p['run'] == SOLVER_RUN else {})
            return [(p['flow'], flows[p['flow']])] if p['flow'] in flows else []
        if 'reconciliacion_detalle_dia' in sql:
            run = next(w for w in self.WINDOWS.values() if w[3] == p['run'])
            out = []
            for r in self.pads[p['label']]:
                if 'profile_q_drenaje_m3h' in r and run[0] <= as_date(r['date']) <= run[1]:
                    out.append((r['pile'], r['date'], self.profile_override.get((r['pile'], r['date']), r['profile_q_drenaje_m3h'])))
            return out + [(pile, run[0], 1.0) for pile in self.extra_universe]
        if re.search(r'\.reconciliacion_run', sql):
            return [r for r in self.runs if r[1] == p['caso'] and r[2] == p['start'] and r[3] == p['end']]
        if '.material WHERE nombre' in sql:
            return [(MATERIAL_ID[p['n']],)]
        pad_of_id, pad_of_material = {1: 'OXIDOS', 2: 'SULFUROS'}, {'OXIDO': 'OXIDOS', 'SULFURO': 'SULFUROS'}
        if 'modulos_turnos' in sql:
            seen = {}
            for r in self.pads[pad_of_id[p['pad']]]:
                seen.setdefault((int(r['pile'][1:]), r['campaign']),
                                (as_date(r['first_irrigation']) - timedelta(days=40), r['cu_apilado_t']))
            return [(a, b, c, d) for (a, b), (c, d) in seen.items()]
        if 'Recuperaciones_pad' in sql:
            rows = [(int(r['pile'][1:]), r['campaign'], as_date(r['date']), r['official_pct'])
                    for r in self.pads[p['pad']] if (r['pile'], r['date']) not in self.drop_recovery
                    and p['hist'] <= as_date(r['date']) <= p['end']]
            return rows + self.extra_recovery
        if 'UNION' in sql:
            label = pad_of_material[p['material']]
            out = set()
            for r in self.pads[label]:
                birth = as_date(r['first_irrigation'])
                out |= {(r['pile'], birth + i * DAY) for i in range((p['end'] - birth).days + 1)}
            out.add(('P02', as_date('2025-01-10')))        # riego de una campana anterior (antes del apilamiento)
            return sorted(out | set(self.irrigation_extra.get(label, ())))
        label = pad_of_material.get(p.get('material'))
        days = [p['start'] + i * DAY for i in range((p['end'] - p['start']).days + 1)] if 'start' in p else []

        def series(field, consolidated):
            # La consolidada cubre solo los 3 primeros dias de la ventana; la vista de ingesta
            # trae todo, con +999 en las fechas que la consolidada ya cubre (debe ignorarse).
            cut = p['start'] + 2 * DAY
            out = []
            for r in self.pads[label]:
                day = as_date(r['date'])
                if not (p['start'] <= day <= p['end']) or 'q_riego_m3h' not in r or (r['pile'], r['date']) in self.drop_flow:
                    continue
                if consolidated and day <= cut:
                    out.append((day, r['pile'], r[field]))
                elif not consolidated:
                    out.append((day, r['pile'], r[field] + (999 if day <= cut else 0)))
            return out
        if 'vw_riego_diario_ingest v' in sql:
            return series('q_riego_m3h', False)
        if 'riego_diario v' in sql:
            return series('q_riego_m3h', True)
        if 'vw_drena_quimica_ingest v' in sql:
            return series('cu_drenaje_gL', False)
        if 'drena_cu_diario v' in sql:
            return series('cu_drenaje_gL', True)
        if 'cu_riego_diario c' in sql:
            return [(d, 0.4) for d in days if d <= p['start'] + 2 * DAY]
        if 'vw_riego_' in sql:
            return [(d, 0.4) for d in days]
        raise AssertionError(f'consulta no prevista: {sql[:80]}')


@pytest.fixture
def db(monkeypatch):
    # Ningun camino puede abrir un motor real.
    monkeypatch.setattr(sqlalchemy.engine.Engine, 'connect',
                        lambda self, *a, **k: (_ for _ in ()).throw(AssertionError('SQL real bloqueado')))
    return FakeDB()


def load(db, pad='SULFUROS', **kw):
    flow = {'OXIDOS': 'F25', 'SULFUROS': 'F29'}[pad]
    anchor = kw.pop('anchor', {pad: {'net_cu_target_t': db.targets[flow], 'net_cu_target_flow': flow}})
    kw.setdefault('expected_run_id', SOLVER_RUN)
    return load_pad_inputs(START, END, CASE, pad, anchor, engine=FakeEngine(db), schema=S,
                           hidro_schema=H, **kw)


def test_loader_emits_only_select_statements(db):
    load(db)
    load(db, 'OXIDOS')
    assert len(db.statements) > 25
    for sql, _ in db.statements:
        assert re.match(r'(?is)^\s*(select|with)\b', sql), sql[:60]
        assert not re.search(r'(?i)\b(insert|update|delete|merge|truncate|alter|drop|create|exec|execute|into)\b', sql)


def test_select_guard_blocks_writes():
    for bad in ('DELETE FROM x', 'SELECT 1; DROP TABLE x', 'EXEC sp_x', 'UPDATE t SET a=1',
                'WITH c AS (SELECT 1) INSERT INTO t SELECT * FROM c', 'SELECT * INTO #t FROM u'):
        with pytest.raises(MadurasInputError, match='no SELECT'):
            assert_select_only(bad)
    assert assert_select_only('-- nota\nSELECT 1').endswith('SELECT 1')


@pytest.mark.parametrize('pad,flow,view,material', [
    ('SULFUROS', 'F29', 'vw_riego_sulfuro_refino_base', 'SULFURO'),
    ('OXIDOS', 'F25', 'vw_riego_oxido_refino_base', 'OXIDO'),
])
def test_identity_target_flow_and_material_per_pad(db, pad, flow, view, material):
    payload = load(db, pad)
    ids = payload['source_ids']
    assert (ids['case_id'], ids['solver_run_id'], ids['allocation_profile_run_id']) == (CASE, SOLVER_RUN, ALLOC_RUN)
    assert ids['net_target_flow'] == flow and ids['model_code'] == 'hidrometalurgia_125_v2'
    assert payload['target_net_t'] == pytest.approx(db.flows[flow])
    assert payload['target_period_start'] == '2026-09-01'
    assert ids['allocation_candidate_run_ids'] == [ALLOC_RUN, ALLOC_RUN - 5]
    flow_params = [p for sql, p in db.statements if 'recon_resultado_flujo' in sql]
    assert flow_params[-1]['flow'] == flow
    assert any(view in sql for sql, _ in db.statements)
    assert any(p.get('material') == material for _, p in db.statements)
    assert all(row['pad'] == pad for row in payload['rows'])


def test_rows_cohorts_births_exclusions_and_modeled_profile(db):
    payload = load(db)
    rows = payload['rows']
    piles = {r['pile'] for r in rows}
    assert piles == {'P01', 'P02', 'P04', 'P05', 'P06'}               # P32 excluida, explicita
    assert payload['metadata']['excluded_piles'] == {'P32': 'sin campana de lixiviacion ni recuperacion (riego sin curva)'}
    # Primer riego derivado de riego > 0 desde el apilamiento (ignora riego de la campana anterior).
    assert payload['metadata']['first_irrigation']['P02'] == '2025-12-15'
    born = [r for r in rows if r['pile'] == 'P06']
    assert born[0]['date'] == '2026-09-04' and len(born) == 4          # sin relleno antes de nacer
    assert all(r['observation_source'] == 'Recuperaciones_pad (primary)' for r in rows)
    window = [r for r in rows if r['pile'] == 'P05' and START <= as_date(r['date']) <= END]
    assert len(window) == 7 and all('not measured' in r['drainage_profile_source'] for r in window)
    assert payload['metadata']['database_writes'] is False


def test_measurement_precedence_consolidated_by_date_then_ingest(db):
    payload = load(db)
    p05 = {r['date']: r for r in payload['rows'] if r['pile'] == 'P05'}
    source = {r['date']: r for r in db.pads['SULFUROS'] if r['pile'] == 'P05'}
    for day in ('2026-09-02', '2026-09-03', '2026-09-05'):
        # Los +999 de la fuente que no manda no deben aparecer.
        assert p05[day]['q_riego_m3h'] == source[day]['q_riego_m3h']
        assert p05[day]['cu_drenaje_gL'] == source[day]['cu_drenaje_gL']
        assert p05[day]['cu_riego_gL'] == 0.4


@pytest.mark.parametrize('pad', ['SULFUROS', 'OXIDOS'])
def test_loaded_payload_closes_target_exactly(db, pad):
    payload = load(db, pad)
    out, audit = reconcile_pad(payload['rows'], START, END, payload['target_net_t'], pad=pad)
    assert audit['lambda'] == pytest.approx(LAMBDA_TRUE if pad == 'SULFUROS' else 0.65, rel=1e-9)
    assert audit['curve_net_t'] == pytest.approx(db.flows['F29' if pad == 'SULFUROS' else 'F25'], abs=1e-9)
    assert {k[1] for k in audit['mature']} == {'P01', 'P02'}
    assert {k[1] for k in audit['exact_30_pending']} == {'P04'}
    assert {k[1] for k in audit['young']} == {'P05', 'P06'}
    assert {k[1] for k in audit['born_in_window']} == {'P06'}


def test_default_history_start_is_previous_month_start():
    assert default_history_start(date(2026, 9, 8)) == date(2026, 8, 1)
    assert default_history_start('2026-01-15') == date(2025, 12, 1)


@pytest.mark.parametrize('mutate,message', [
    (lambda db: setattr(db, 'caso', []), 'exactamente un run oficial'),
    (lambda db: setattr(db, 'caso', db.caso * 2), 'exactamente un run oficial'),
    (lambda db: setattr(db, 'caso', [db.caso[0][:3] + (END + DAY,) + db.caso[0][4:]]), 'no coincide con la del Caso'),
    (lambda db: setattr(db, 'caso', [db.caso[0][:6] + ('hidrometalurgia_120_completo', 'v1', 120)]), 'solo esta definido'),
    (lambda db: db.flows.pop('F29'), 'no tiene F29'),
    (lambda db: setattr(db, 'runs', []), 'no ejecuta ni guarda'),
    (lambda db: setattr(db, 'runs', [(ALLOC_RUN, CASE, START, END, 'Flowsheet', False)]), 'no convergio'),
    (lambda db: db.irrigation_extra.update(SULFUROS={('P40', START)}), 'ausentes del run de asignacion'),
])
def test_strict_identity_and_source_failures_are_explained(db, mutate, message):
    mutate(db)
    with pytest.raises(MadurasInputError, match=message):
        load(db)


def test_wrong_expected_run_or_anchor_is_rejected(db):
    with pytest.raises(MadurasInputError, match=f'se esperaba {SOLVER_RUN + 1}'):
        load(db, expected_run_id=SOLVER_RUN + 1)
    with pytest.raises(MadurasInputError, match='no coincide con F29'):
        load(db, anchor={'SULFUROS': {'net_cu_target_t': db.flows['F29'] + 1, 'net_cu_target_flow': 'F29'}})
    with pytest.raises(MadurasInputError, match='se esperaba F29'):
        load(db, anchor={'SULFUROS': {'net_cu_target_t': db.flows['F29'], 'net_cu_target_flow': 'F25'}})
    with pytest.raises(MadurasInputError, match='no trae objetivo neto'):
        load(db, anchor={'OXIDOS': {}})


def test_missing_measurements_or_recovery_fail_without_filling(db):
    db.drop_recovery = {('P05', '2026-09-04')}
    with pytest.raises(MadurasInputError, match='complete Case coverage.*P05'):
        load(db)
    db.drop_recovery = set()
    db.drop_flow = {('P06', '2026-09-05')}
    with pytest.raises(MadurasInputError, match='missing q_riego_m3h.*P06'):
        load(db)
    db.drop_flow = set()
    db.profile_override = {('P05', '2026-09-02'): None}
    with pytest.raises(MadurasInputError, match='missing profile_q_drenaje_m3h.*P05'):
        load(db)


def test_campaign_change_inside_window_is_rejected(db):
    db.extra_recovery = [(1, 10, date(2026, 9, 2), 99.0)]
    with pytest.raises(MadurasInputError, match='cambio de campana dentro del Caso'):
        load(db)


def test_chained_cases_through_loader_protect_history_and_fit_own_lambda(db):
    first = load(db)
    out1, a1 = reconcile_pad(first['rows'], START, END, first['target_net_t'], pad='SULFUROS')
    previous = dict(local_direct_recovery=True, recovery_rows=out1, week_start=START, week_end=END)
    s2, e2 = date(2026, 9, 8), date(2026, 9, 14)

    def load_case2():
        return load_pad_inputs(s2, e2, CASE + 1, 'SULFUROS', None, expected_run_id=SOLVER_RUN + 1,
                               engine=FakeEngine(db), schema=S, hidro_schema=H, previous_result=previous)
    probe = load_case2()                                  # objetivo provisional: solo fija la linea base
    db.flows_by_run[SOLVER_RUN + 1]['F29'] = expected_target(probe['rows'], s2, e2, 0.6)
    second = load_case2()
    out2, a2 = reconcile_pad(second['rows'], s2, e2, second['target_net_t'], pad='SULFUROS')
    assert a1['lambda'] == pytest.approx(LAMBDA_TRUE) and a2['lambda'] == pytest.approx(0.6)
    assert second['metadata']['chained_from_previous'] and second['source_ids']['solver_run_id'] == SOLVER_RUN + 1
    prior = {(r['pile'], r['date']): r['reconciled_pct'] for r in out1 if r['date'] >= '2026-09-01' and 'reconciled_pct' in r}
    carried = [r for r in out2 if (r['pile'], r['date']) in prior]
    assert carried and all(r['official_pct'] == prior[(r['pile'], r['date'])] for r in carried)
    young_a1 = {k[1] for k in a1['young']}
    assert young_a1 == {'P05', 'P06'} and {k[1] for k in a2['young']} == {'P05', 'P06'}
    assert {k[1] for k in a2['mature']} == {'P01', 'P02', 'P04'}      # P04 cruza los 30 dias


def test_chain_loader_requires_the_next_day(db):
    first = load(db)
    out, _ = reconcile_pad(first['rows'], START, END, first['target_net_t'], pad='SULFUROS')
    previous = dict(local_direct_recovery=True, recovery_rows=out, week_start=START, week_end=END)
    with pytest.raises(MadurasInputError, match='dia siguiente'):
        load(db, previous_result=previous)
