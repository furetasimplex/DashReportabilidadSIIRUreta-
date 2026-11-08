"""Mensajes para el operador: numeros correctos para cada causa y traduccion de avisos del motor; sin SQL."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curvas_recon import mensajes_pad as MP
from curvas_recon.reconciliacion_pad import K_F, reconcile_pad
from curvas_recon.test_reconciliacion_pad import goal_with_pls_ratio, pad_of, setup_case, targets_from


def _txt(ms):
    return ' '.join(m['titulo'] + ' ' + m['texto'] + ' ' + (m['accion'] or '') for m in ms)


def test_water_mass_message_carries_the_numbers_and_the_minimum_cap():
    priors, nets, _, _ = setup_case()
    goal, net_goal = goal_with_pls_ratio(priors, 1.0103)
    res = reconcile_pad(priors, nets, goal, net_goal, tolerance=0.001, net_tolerance=0.001)
    ms = MP.mensajes_reconciliacion_pad(res, banda=0.001)
    assert len(ms) == 1 and ms[0]['nivel'] == MP.ERROR
    d = res['detalle']
    t = _txt(ms)
    assert MP._n(d['pls_minimo_exigido_m3']) in t and MP._n(d['pls_maximo_permitido_m3']) in t
    assert MP._n(res['tope_comun_minimo_factible'], 3) in t and 'm³' in t
    assert 'masa_agua' in ms[0]['detalle'] and 'causa' not in ms[0]['texto'] and 'λ' not in t


def test_f29_message_reports_the_minimum_deviation_in_tonnes_of_copper():
    priors, nets, _, _ = setup_case()
    goal = targets_from(priors)
    q_r, f_r, q_p, f_p = pad_of(priors)
    res = reconcile_pad(priors, nets, goal, K_F * (f_p - f_r) * 0.99, tolerance=0.001, net_tolerance=0.0005)
    ms = MP.mensajes_reconciliacion_pad(res)
    assert ms[0]['nivel'] == MP.ERROR and 'F29' in ms[0]['titulo']
    assert MP._n(res['desviacion_minima_neto_t'], 2) + ' t Cu' in ms[0]['texto']


def test_physical_limits_and_non_physical_solution_and_closed_days_messages():
    ms = MP.mensajes_reconciliacion_pad(dict(status='infactible', causa='limites_fisicos', motivo='x', detalle=dict(q=(0.5, 2.0), conc=(0.0, 3.0))))
    assert '0,50' in ms[0]['texto'] and '2,00' in ms[0]['texto'] and '3,00' in ms[0]['texto'] and ms[0]['nivel'] == MP.ERROR
    ms = MP.mensajes_reconciliacion_pad(dict(status='infactible', causa='solucion_no_fisica', motivo='x', detalle=dict(problemas=['P25: factor q_pls 14 fuera de (0.5, 2.0)'])))
    assert 'P25' in ms[0]['texto'] and ms[0]['nivel'] == MP.ERROR
    cierre = dict(ok=False, cierre_fecha='2026-09-01', dias_cerrados_en_ventana=['2026-08-30', '2026-08-31'])
    ms = MP.mensajes_reconciliacion_pad(dict(status='infactible', causa='dias_cerrados_en_ventana', cierre=cierre, motivo='x'))
    assert '2 día(s)' in ms[0]['texto'] and '2026-09-01' in ms[0]['texto']


def _ok(**over):
    pile = lambda n, young, **k: dict(dict(pile=n, young=young, drenaje_riego=0.9, d_q_riego=0.0, d_cu_riego=0.0, d_q_pls=0.0, d_cu_pls=0.0), **k)
    res = dict(status='ok', por_pila=[pile('P01', False, drenaje_riego=1.0), pile('P02', False), pile('P24', True, d_q_pls=0.35, d_cu_riego=-0.66)])
    res.update(over)
    return res


def test_ok_result_warns_band_caps_strong_new_pile_factors_and_recovery_gap():
    ms = MP.mensajes_reconciliacion_pad(_ok(), banda=0.01, recuperaciones={'P24': dict(metodo_pct=15.0, oficial_pct=15.5, cu_apilado_t=4000.0)})
    titulos = [m['titulo'] for m in ms]
    assert titulos == ['Banda de cierre provisional', 'Pilas maduras en el tope de drenaje', 'Pila nueva con ajuste fuerte', 'Brecha de recuperación al cierre']
    assert all(m['nivel'] == MP.ADVERTENCIA for m in ms)
    t = _txt(ms)
    assert '1,00 %' in t and '1 de 2 pilas maduras' in t and 'P01' in t
    assert 'caudal de PLS ×1,35' in t and 'ley de Cu del riego ×0,34' in t and 'cinética temprana' in t
    assert '20,0 t Cu' in t and '15,00 %' in t and '15,50 %' in t              # (15,5 - 15,0) % de 4000 t = 20 t


def test_ok_result_without_issues_is_informational_and_thresholds_are_configurable():
    res = _ok(por_pila=[dict(pile='P02', young=False, drenaje_riego=0.9, d_q_riego=0, d_cu_riego=0, d_q_pls=0, d_cu_pls=0)])
    ms = MP.mensajes_reconciliacion_pad(res, banda=0.001)
    assert len(ms) == 1 and ms[0]['nivel'] == MP.INFORMACION
    assert not any(m['titulo'] == 'Pila nueva con ajuste fuerte' for m in MP.mensajes_reconciliacion_pad(_ok(), umbral_factor=0.9))


def test_solver_run_messages():
    assert MP.mensajes_run_solver({}) == []
    ms = MP.mensajes_run_solver(dict(estado='failed'), caso=10009)
    assert ms[0]['nivel'] == MP.ERROR and 'failed' in ms[0]['texto'] and 'Caso 10009' == ms[0]['ambito']
    ms = MP.mensajes_run_solver(dict(estado='validated', closure_kind='precision_adjusted', fuera_tol=9, intentos=[1, 2], razones={'Sulfuros': 1.02}))
    assert [m['nivel'] for m in ms] == [MP.ADVERTENCIA, MP.ADVERTENCIA, MP.INFORMACION, MP.ADVERTENCIA]
    assert '9 flujo(s)' in _txt(ms) and '1,020' in _txt(ms)


@pytest.mark.parametrize('texto,titulo,fragmentos', [
    ('SULFUROS: Fdrena del pad reconciliado por flujos = 1.010338 > 1.00: el ancla pide drenar mas que el tope fisico. Q PLS recortado de 30183.0 a 29875.0 m3/h (-1.0%). Revisar el balance del run oficial.',
     'Drenaje del pad sobre el límite físico', ['1,010', '1,00', '30.183,0', '29.875,0', 'm³/h']),
    ('QRiego_medido o QPLS_medido = 0 esta semana; sin pilas activas con caudal, no se reparte nada.', 'Faltan datos de riego o de PLS', ['0 m³/h']),
    ('SULFUROS/P24: Cu PLS reconciliado negativo (-0.1234) -- pool transiente insuficiente para el ajuste de fino.', 'Ley de Cu de PLS negativa', ['P24', '-0,1234 g/L']),
    ('SULFUROS: el residuo de rampa (12.500) no se pudo repartir -- ninguna pila en regimen tiene holgura bajo el techo 0.99. x (paso 7e).', 'Residuo de rampa sin pilas donde repartirlo', ['12,50']),
    ('SULFUROS: 2 pila(s) EN REPOSO -- campana abierta', 'Pilas en reposo', ['2 pila(s)']),
])
def test_engine_warnings_are_rewritten_without_internal_jargon(texto, titulo, fragmentos):
    m = MP.traducir_aviso_motor(texto)
    assert m['titulo'] == titulo and m['detalle'] == texto
    for f in fragmentos:
        assert f in m['texto'], (f, m['texto'])
    cuerpo = m['titulo'] + m['texto'] + (m['accion'] or '')
    assert 'paso 7' not in cuerpo and 'Fdrena' not in cuerpo and 'pool transiente' not in cuerpo


def test_unknown_engine_warning_is_kept_as_a_warning():
    m = MP.traducir_aviso_motor('texto nuevo del motor')
    assert m['nivel'] == MP.ADVERTENCIA and m['texto'] == 'texto nuevo del motor'


def test_dashboard_renders_levels_action_and_collapsed_detail():
    from curvas_recon import pad_dashboard as dashboard
    from plotly.utils import PlotlyJSONEncoder
    data = dict(warnings=['QRiego_medido o QPLS_medido = 0 esta semana; sin pilas activas con caudal, no se reparte nada.'],
                SULFUROS=dict(warnings=['SULFUROS: 2 pila(s) EN REPOSO -- campana abierta']), solver_run=dict(estado='failed'),
                mensajes_pad=MP.mensajes_reconciliacion_pad(_ok(), banda=0.01))
    r = json.dumps(dashboard._build_warnings(data), cls=PlotlyJSONEncoder, ensure_ascii=False)
    assert r.index('warning-level-error') < r.index('warning-level-advertencia') < r.index('warning-level-informacion')
    assert 'Qué hacer' in r and 'Detalle técnico' in r and 'warning-detail' in r


def test_panel_text_depends_on_the_method_and_quotes_the_real_parameters():
    from curvas_recon import reconciliacion_pad as RP
    from curvas_recon.metodo_maduras_fijas import METODO_MADURAS_FIJAS, METODO_REPARTO
    fijas = ' '.join(MP.texto_panel(METODO_MADURAS_FIJAS))
    reparto = ' '.join(MP.texto_panel(METODO_REPARTO))
    assert 'Maduras fijas, nuevas absorben' in fijas and 'Reparto por aporte' in reparto and 'Reparto por aporte' not in fijas
    assert 'conservan lo medido' in fijas and 'absorben el' in fijas and 'meses anteriores' in fijas and 'cinética temprana' in fijas
    assert f"{MP._pct(RP.BAND_DEFAULT, 1)}" in fijas and MP._n(RP.MAX_DRAIN_RATIO_DEFAULT, 2) in fijas and '0,99' in fijas
    assert '±30 %' not in fijas and '±30 %' not in reparto
    assert 'en proporción a su aporte' in reparto and 'todas las pilas activas' in reparto and 'maduras también cambian' in reparto


def test_cap_message_shows_the_real_drain_cap():
    pile = lambda n, **k: dict(dict(pile=n, young=False, drenaje_riego=0.9, tope_drenaje=0.99, d_q_riego=0, d_cu_riego=0, d_q_pls=0, d_cu_pls=0), **k)
    res = dict(status='ok', por_pila=[pile('P01', drenaje_riego=0.99), pile('P02')])
    ms = MP.mensajes_reconciliacion_pad(res, banda=0.001)
    assert ms[0]['titulo'] == 'Pilas maduras en el tope de drenaje' and 'tope de 0,99 veces' in ms[0]['texto'] and '1 de 2' in ms[0]['texto']


def test_dashboard_panel_follows_the_selected_method():
    from curvas_recon import pad_dashboard as dashboard
    from plotly.utils import PlotlyJSONEncoder
    txt = lambda m: json.dumps(dashboard.update_panel_note(m), cls=PlotlyJSONEncoder, ensure_ascii=False)
    assert 'Maduras fijas' in txt('maduras_fijas') and 'cinética temprana' in txt('maduras_fijas')
    assert 'Reparto por aporte' in txt('reparto') and 'cinética temprana' not in txt('reparto')
