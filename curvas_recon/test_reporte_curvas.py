"""Exportación real del libro, sin SQL ni modificaciones a datos de planta."""
import base64
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from openpyxl import load_workbook
from sqlalchemy.engine import Engine

from . import pad_dashboard as dashboard, report_metodo as report


def report_doc():
    pads = {}
    for label in ('OXIDOS', 'SULFUROS'):
        piles = [dict(p=f'P{num:02d}', num=num, campana=17, n=3,
                      apilado=100.0, t_rec=4.0 / num, t_med=3.0 / num,
                      pct=4.0 / num, planta_rec_termino=None,
                      rec=[1.0 / num, 2.5 / num, 4.0 / num]) for num in (1, 2)]
        pads[label] = dict(pilas=piles, desde='2026-08-01')
    return dict(pads=pads, end='2026-08-03', corte_planta='2026-07-31')


@pytest.fixture(autouse=True)
def no_sql(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('SQL prohibido')
    monkeypatch.setattr(Engine, 'connect', forbidden)


@pytest.fixture
def export_case(monkeypatch, tmp_path):
    start, end = pd.Timestamp('2026-08-01'), pd.Timestamp('2026-08-03')
    case = dict(id=10013, nombre='Prueba sintética', run_id=10104,
                fecha_inicio=start, fecha_fin=end, modelo_codigo='hidrometalurgia_125_v2',
                modelo_version='v2', total_flujos=125)
    monkeypatch.setattr(dashboard, 'CASOS', [case])
    monkeypatch.setattr(dashboard, 'JOINT_DATA_CUTOFF', end)
    monkeypatch.setattr(dashboard, '_RECON_RAW_DIR', str(tmp_path / 'raw'))
    token = dashboard._save_recon_raw({'piles': []}, case, start, end)
    data = dict(caso_id=case['id'], caso_run_id=case['run_id'], raw_token=token,
                week_start=start.isoformat(), week_end=end.isoformat())
    monkeypatch.setattr(report, 'XL_PLANTA', str(tmp_path / 'planta_ausente.xlsx'))
    monkeypatch.setattr(report, 'construir_doc', lambda *args, **kwargs: report_doc())
    return data, case


def test_descarga_real_sin_libro_planta_y_repetible(export_case):
    data, case = export_case
    raw_path = Path(dashboard._recon_raw_path(data['raw_token']))
    for click in (1, 2):
        status, download = dashboard.generate_week_report(click, data, case['id'])
        assert 'sin comparación planta' in str(status)
        assert raw_path.is_file()
        book = load_workbook(BytesIO(base64.b64decode(download['content'])))
        assert book.sheetnames == ['Rec Ox', 'Rec Sulfuro', 'Curvas Ox', 'Curvas Sulfuro', 'Prod']
        assert book['Rec Ox']['B12'].value == 4.0
        assert book['Rec Ox']['C12'].value == 2.0
        assert book['Rec Ox']['B7'].value is None
        assert len(book['Curvas Ox']._charts) == 2
        assert len(book['Curvas Sulfuro']._charts) == 2
        with ZipFile(BytesIO(base64.b64decode(download['content']))) as archive:
            assert len([p for p in archive.namelist() if p.startswith('xl/charts/chart') and p.endswith('.xml')]) == 4


@pytest.mark.parametrize('change', ['selected', 'store_run', 'raw_run', 'store_window',
                                  'catalog_window', 'model', 'bad_window', 'bad_payload'])
def test_descarga_rechaza_identidad_obsoleta(export_case, monkeypatch, change):
    data, case = export_case
    selected = case['id']
    if change == 'selected':
        selected += 1
    elif change == 'store_run':
        data['caso_run_id'] += 1
    elif change in ('raw_run', 'bad_payload'):
        raw, _ = dashboard._load_recon_raw(data['raw_token'], case['id'])
        raw = deepcopy(raw)
        if change == 'raw_run':
            raw['caso']['run_id'] += 1
        else:
            raw.pop('ws')
        monkeypatch.setattr(dashboard, '_load_recon_raw', lambda *args: (raw, None))
    elif change == 'store_window':
        data['week_end'] = '2026-08-02'
    elif change == 'catalog_window':
        case['fecha_fin'] = pd.Timestamp('2026-08-02')
    elif change == 'model':
        case['modelo_version'] = 'v1'
    else:
        data['week_start'] = 'fecha inválida'
    def forbidden(*args, **kwargs):
        raise AssertionError('No debe reconstruir una corrida incompatible')
    monkeypatch.setattr(report, 'construir_doc', forbidden)
    _, download = dashboard.generate_week_report(1, data, selected)
    assert download is None


def test_fallo_envio_limpia_xlsx_sin_consumir_corrida(export_case, monkeypatch):
    data, case = export_case
    written = []
    writer = report.escribir_libro
    def tracked(doc, path):
        written.append(Path(path))
        return writer(doc, path)
    def fail(*args, **kwargs):
        raise OSError('Fallo sintético de descarga')
    monkeypatch.setattr(report, 'escribir_libro', tracked)
    monkeypatch.setattr(dashboard.dcc, 'send_file', fail)
    _, download = dashboard.generate_week_report(1, data, case['id'])
    assert download is None and written and not written[0].exists()
    assert Path(dashboard._recon_raw_path(data['raw_token'])).exists()


def test_curva_usa_finos_reconciliados_solo_dentro_del_caso(monkeypatch, tmp_path):
    days = pd.date_range('2026-08-01', periods=3)
    apilado = {(pid, 1): dict(camp=17, f0=days[0], f1=days[0], fin=100.0,
                            tms=1000.0, ley=10.0) for pid in (1, 2)}
    monkeypatch.setattr(report, 'leer_apilado', lambda **kwargs: apilado)
    monkeypatch.setattr(report.E, 'load_riego', lambda *args: pd.DataFrame({'P01': 10.0}, index=days))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *args: pd.Series(1.0, index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *args: pd.DataFrame({'P01': 2.0}, index=days))
    monkeypatch.setattr(report.E, 'FDRENA_MAX', 0.95)
    raw = {'piles': [dict(label=label, parcela='P01', daily=[dict(
        date=days[1], fino_pls_final=30.0, fino_riego_final=10.0)])
        for label in ('OXIDOS', 'SULFUROS')]}
    runs = {10013: dict(ws=days[1], we=days[1], caso={'run_id': 10104},
                       pads={label: {'res': raw} for label in ('OXIDOS', 'SULFUROS')})}
    doc = report.construir_doc(runs, end=days[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False)
    for label in ('OXIDOS', 'SULFUROS'):
        pile = doc['pads'][label]['pilas'][0]
        assert pile['med'] == pytest.approx([0.216, 0.432, 0.648])
        assert pile['rec'] == pytest.approx([0.216, 0.696, 0.912])
        assert pile['pct'] == pytest.approx(0.912)
        assert pile['planta_rec_termino'] is None


def test_reporte_conserva_campana_completa_anterior_a_60_dias(monkeypatch, tmp_path):
    days = pd.date_range('2023-12-01', '2026-10-12')
    apilado = {(1, 1): dict(camp=17, f0=days[0], f1=days[0], fin=10000.0,
                            tms=100000.0, ley=10.0)}
    cuts, requests = [], []
    def apilado_at_cut(**kwargs):
        cuts.append(kwargs['asof'])
        return apilado
    def irrigation(label, start, end):
        requests.append((label, pd.Timestamp(start), pd.Timestamp(end)))
        return pd.DataFrame({'P01': 10.0}, index=days)
    monkeypatch.setattr(report, 'leer_apilado', apilado_at_cut)
    monkeypatch.setattr(report.E, 'load_riego', irrigation)
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *args: pd.Series(1.0, index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *args: pd.DataFrame({'P01': 2.0}, index=days))
    raw = {'piles': [dict(label='OXIDOS', parcela='P01', daily=[])]}
    runs = {10013: dict(ws=pd.Timestamp('2026-10-01'), we=days[-1], caso={'run_id': 10104},
                       pads={'OXIDOS': {'res': raw}})}
    doc = report.construir_doc(runs, end=days[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False)
    pile = doc['pads']['OXIDOS']['pilas'][0]
    assert pile['ini'] == '2023-12-01'
    assert pile['n'] == len(days) > 1000
    assert len(pile['rec']) == len(days)
    assert cuts == [days[-1]]
    assert len([r for r in requests if r[0] == 'OXIDOS']) == 1
    assert requests[0][1] <= days[0]


def test_apilado_excluye_campanas_futuras_antes_de_agrupar(monkeypatch):
    from unittest.mock import MagicMock
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.execute.return_value.fetchall.return_value = []
    monkeypatch.setattr(report, 'connect', lambda: conn)
    assert report.leer_apilado(asof='2026-10-12') == {}
    sql, params = conn.execute.call_args.args
    assert 'WHERE Parcela IS NOT NULL AND Fecha < :hasta_exclusivo' in str(sql)
    assert params == {'hasta_exclusivo': pd.Timestamp('2026-10-13')}
    conn.__exit__.assert_called_once()
