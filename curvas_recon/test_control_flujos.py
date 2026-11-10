"""Control contra flujos globales y razon de drenaje de maduras (fuera del dash); sin SQL."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curvas_recon.control_flujos import flow_control, global_concentration, mature_drainage_ratio
from curvas_recon.sulfide_method import match_pad_flows

# Flujos globales de Sulfuros del Caso 10013 (run 10145), tomados del Excel de extraccion.
ANCHOR = dict(q_riego_medido=974266.0, q_riego_recon=987521.0, fino_riego_recon=394.63,
              q_pls_medido=961778.0, q_pls_recon=960444.0, fino_pls_recon=2165.52)


def test_mature_drainage_ratio_comes_from_the_global_measured_flows_with_a_safe_fallback():
    assert mature_drainage_ratio(ANCHOR) == pytest.approx(0.98718, abs=1e-5)
    assert mature_drainage_ratio({}) == 0.95
    assert mature_drainage_ratio(dict(q_riego_medido=1000.0, q_pls_medido=300.0)) == 0.95     # razon no creible
    assert mature_drainage_ratio(dict(q_riego_medido=0.0, q_pls_medido=5.0)) == 0.95
    assert global_concentration(394.63, 987521.0) == pytest.approx(0.39961, abs=1e-5)


def day(q, cr, cd, q_pls=None):
    return dict(label='SULFUROS', q_riego_final=q, q_pls_final=q_pls, cu_riego_recon=cr, cu_pls_recon=cd)


def test_control_flags_differences_and_uses_the_case_ratio_for_piles_without_drainage_data():
    rows = [day(100.0, 0.4, 2.0) for _ in range(10)] + [day(50.0, 0.4, 10.0, q_pls=30.0) for _ in range(10)]
    goal = dict(q_riego_recon=1500.0 * 24, fino_riego_recon=0.4 * 1500 * 24 / 1000,
                q_pls_recon=(1000.0 * 0.95 + 300.0) * 24, fino_pls_recon=(2.0 * 950.0 + 10.0 * 300.0) * 24 / 1000)
    ok = flow_control(rows, {'SULFUROS': goal}, {'SULFUROS': 0.95})
    assert [r['estado'] for r in ok] == ['ok', 'ok'] and ok[1]['masa_pilas_m3'] == pytest.approx(goal['q_pls_recon'])
    assert ok[1]['cu_pilas_gL'] == pytest.approx(1000 * goal['fino_pls_recon'] / goal['q_pls_recon'])
    other = flow_control(rows, {'SULFUROS': goal}, {'SULFUROS': 0.99})                          # otra razon cambia la masa de PLS
    assert other[1]['masa_pilas_m3'] > ok[1]['masa_pilas_m3'] and other[1]['dif_masa'] > 0
    off = flow_control(rows, {'SULFUROS': dict(goal, q_pls_recon=goal['q_pls_recon'] * 1.10)}, {'SULFUROS': 0.95})
    assert off[1]['estado'] == 'revisar' and off[1]['dif_masa'] == pytest.approx(1 / 1.10 - 1)
    assert flow_control(rows, {}, {})[0]['estado'] == 'sin objetivo global'


def test_matching_uses_the_case_ratio_for_the_weights_of_mature_piles():
    mature = [dict(q_riego_m3h=100.0, cu_riego_gL=0.4, cu_drenaje_gL=2.0)] * 5
    young = [dict(q_riego_m3h=100.0, cu_riego_gL=0.4, cu_drenaje_gL=20.0, profile_q_drenaje_m3h=50.0)] * 5
    rows, held = dict(mature=mature, young=young), 0.024 * 5 * (0.95 * 100 * 2.0 - 100 * 0.4)
    goals = dict(cu_riego_g_l=1.0, cu_pls_g_l=1.0)
    default = match_pad_flows(rows, held, held + 10.0, goals, 0.30, 0.0001)
    case = match_pad_flows(rows, held, held + 10.0, goals, 0.30, 0.0001, mature_ratio=0.987)
    assert default['cu_pls_pad_g_l_antes'] != case['cu_pls_pad_g_l_antes']       # los pesos de las maduras cambian
