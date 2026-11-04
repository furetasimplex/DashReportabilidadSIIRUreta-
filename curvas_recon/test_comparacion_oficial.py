"""Comparacion metodo vs oficial; sin SQL, con los datos del Caso 10009."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curvas_recon.comparacion_oficial import compare, load_official, render_markdown, write_outputs
from curvas_recon.sulfide_db_inputs import build_sulfide_rows
from curvas_recon.test_sulfide_db_inputs import case10009_series


def inputs():
    fx, material, curves, wip, first, saved = case10009_series()
    rows, _ = build_sulfide_rows('2026-09-01', '2026-09-07', material, curves, wip, first, saved)
    official = {}
    for r in rows:                                   # oficial = medido (como el reporte hasta el 1-oct)
        official.setdefault(r['pile'], {})[r['date']] = r['observed_pct']
    return fx, rows, official


def test_matches_official_where_expected_and_reports_young_gap():
    fx, rows, official = inputs()
    result = compare(rows, fx['target_net_t'], '2026-09-01', '2026-09-07', official)
    s = result['summary']
    assert s['jovenes'] == ['P24', 'P25'] and len(s['maduras']) == 16
    assert s['lambda_'] == pytest.approx(0.7214427195956585, rel=1e-12)
    assert s['max_abs_medido_vs_oficial_maduras_pp'] == 0
    young = {r['pila']: r for r in result['piles'] if r['estado'] == 'joven'}
    assert young['P24']['metodo_fin_pct'] == pytest.approx(15.847805, abs=1e-6)
    assert young['P24']['metodo_menos_oficial_pp'] == pytest.approx(15.847805 - 15.226614, abs=1e-6)
    assert s['cu_neto_jovenes_metodo_t'] + s['cu_neto_maduras_oficial_t'] == pytest.approx(fx['target_net_t'], abs=1e-6)
    assert all(ok for _, ok, _ in result['checks'])


def test_flags_mismatching_or_missing_official_data():
    fx, rows, official = inputs()
    official['P10']['2026-09-07'] += 0.5             # el oficial difiere de lo medido
    del official['P12']
    result = compare(rows, fx['target_net_t'], '2026-09-01', '2026-09-07', official)
    failed = {name for name, ok, _ in result['checks'] if not ok}
    assert failed == {'maduras_medido_igual_oficial', 'oficial_disponible_en_todas_las_pilas'}
    assert result['summary']['pilas_sin_dato_oficial'] == ['P12']


def test_outputs_and_official_loader(tmp_path):
    fx, rows, official = inputs()
    result = compare(rows, fx['target_net_t'], '2026-09-01', '2026-09-07', official)
    folder = write_outputs(result, tmp_path / 'salida', 'Caso #10009')
    assert {p.name for p in folder.iterdir()} == {'RESULTADO.md', 'resumen_por_pila.csv', 'detalle_diario.csv'}
    assert 'Verificaciones' in render_markdown(result) and 'P24' in (folder / 'RESULTADO.md').read_text(encoding='utf-8')
    loaded = load_official(None, Path(__file__).parent / 'test_fixtures' / 'historico_oficial_validado_20260901_20261001.csv')
    assert loaded['P24']['2026-09-30'] == pytest.approx(33.2487028, abs=1e-6)
