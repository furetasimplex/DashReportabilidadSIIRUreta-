"""ExportaciÃ³n real del libro, sin SQL ni modificaciones a datos de planta."""
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
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {})
    monkeypatch.setattr(report, 'leer_dump', lambda asof: [])


@pytest.fixture
def export_case(monkeypatch, tmp_path):
    start, end = pd.Timestamp('2026-08-01'), pd.Timestamp('2026-08-03')
    case = dict(id=10013, nombre='Prueba sintÃ©tica', run_id=10104,
                fecha_inicio=start, fecha_fin=end, modelo_codigo='hidrometalurgia_125_v2',
                modelo_version='v2', total_flujos=125)
    monkeypatch.setattr(dashboard, 'CASOS', [case])
    monkeypatch.setattr(dashboard, 'CASO_OPTIONS', [])
    monkeypatch.setattr(dashboard, 'DEFAULT_CASO_ID', case['id'])
    monkeypatch.setattr(dashboard, '_load_caso_options', lambda: ([case], [], case['id']))
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
        assert 'sin comparaci' in str(status)
        assert raw_path.is_file()
        book = load_workbook(BytesIO(base64.b64decode(download['content'])))
        assert book.sheetnames == ['Rec Ox', 'Rec Sulfuro', 'Curvas Ox', 'Curvas Sulfuro', 'Prod Oxidos', 'Prod Sulfuros', 'RL Oxidos', 'RL Sulfuros', 'Método usado']
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
        data['week_start'] = 'fecha invÃ¡lida'
    def forbidden(*args, **kwargs):
        raise AssertionError('No debe reconstruir una corrida incompatible')
    monkeypatch.setattr(report, 'construir_doc', forbidden)
    _, download = dashboard.generate_week_report(1, data, selected)
    assert download is None


def test_fallo_envio_limpia_xlsx_sin_consumir_corrida(export_case, monkeypatch):
    data, case = export_case
    written = []
    writer = report.escribir_libro
    def tracked(doc, path, **kwargs):
        written.append(Path(path))
        return writer(doc, path, **kwargs)
    def fail(*args, **kwargs):
        raise OSError('Fallo sintÃ©tico de descarga')
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



def test_primary_gapped_segments_rebase_without_proxy_prefix_peak():
    days = pd.date_range('2026-07-01', periods=31)
    segments = [
        {'dates': [days[2], days[3]], 'values': [40.0, 41.0]},
        {'dates': [days[12], days[13]], 'values': [45.0, 46.0]},
    ]
    points = report._primary_points_for_campaign(segments, days[0], days[20])
    assert [day for day, _ in points] == [days[2], days[3], days[12], days[13]]

    # Proxy history before the first reading is deliberately huge. It must not
    # survive as the plotted historical maximum; after each anchor, gap-day
    # proxy increments continue from that measured baseline.
    increments = [0.0] + [0.1] * 30
    curve = __import__('numpy').cumsum(increments)
    curve[0] = 500.0
    curve[1] = 700.0
    position = {day: i for i, day in enumerate(days)}
    stack_cu = pd.Series(100.0, index=days)
    anchor = report._apply_primary_points(
        curve, increments, 0, points, stack_cu, 100.0, days[-1], position)
    display = report._recovery_curve_for_display(curve, anchor["first"][0], days[0])
    assert curve[2] == pytest.approx(40.0)
    assert curve[12] == pytest.approx(45.0)
    assert display[:2] == [None, None]
    assert display[2] == pytest.approx(40.0)
    assert report._finite_recovery_max(display) == pytest.approx(47.7)

def test_baseline_usa_lectura_primaria_pre_caso_y_preserva_varios_casos(monkeypatch, tmp_path):
    days = pd.date_range('2026-08-01', periods=6)
    apilado = {(pid, 1): dict(camp=17, f0=days[0], f1=days[4], fin=100.0,
                            tms=1000.0, ley=10.0) for pid in (1, 2)}
    monkeypatch.setattr(report, 'leer_apilado', lambda **kwargs: apilado)
    monkeypatch.setattr(report.E, 'load_riego', lambda *args: pd.DataFrame({'P01': 10.0}, index=days))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *args: pd.Series(1.0, index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *args: pd.DataFrame({'P01': 2.0}, index=days))
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {
        1: [
            {'dates': [days[0] - pd.Timedelta(days=3)], 'values': [90.0]},
            {'dates': [days[1], days[3]], 'values': [10.0, 99.0]},
        ]
    })
    monkeypatch.setattr(report, '_campaign_cu_daily', lambda *args: {
        1: pd.Series([80.0], index=[days[1]])
    })

    def case_result(day):
        return {'piles': [dict(label=label, parcela='P01', daily=[dict(
            date=day, fino_pls_final=30.0, fino_riego_final=10.0)])
            for label in ('OXIDOS', 'SULFUROS')]}

    runs = {
        1: dict(ws=days[2], we=days[2], caso={'run_id': 1},
                pads={label: {'res': case_result(days[2])} for label in ('OXIDOS', 'SULFUROS')}),
        2: dict(ws=days[4], we=days[4], caso={'run_id': 2},
                pads={label: {'res': case_result(days[4])} for label in ('OXIDOS', 'SULFUROS')}),
    }
    doc = report.construir_doc(runs, end=days[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False)
    for label in ('OXIDOS', 'SULFUROS'):
        pile = doc['pads'][label]['pilas'][0]
        assert pile['primary_anchor_date'] == str(days[1].date())
        assert pile['primary_anchor_pct'] == pytest.approx(10.0)
        assert pile['med'][1:] == pytest.approx([8.0, 8.216, 8.432, 8.648, 8.864])
        assert pile['rec'][1:] == pytest.approx([8.0, 8.48, 8.696, 9.176, 9.392])


def test_primary_baseline_does_not_use_measurements_after_first_case(monkeypatch, tmp_path):
    days = pd.date_range('2026-08-01', periods=5)
    apilado = {(pid, 1): dict(camp=17, f0=days[0], f1=days[0], fin=100.0,
                            tms=1000.0, ley=10.0) for pid in (1, 2)}
    monkeypatch.setattr(report, 'leer_apilado', lambda **kwargs: apilado)
    monkeypatch.setattr(report.E, 'load_riego', lambda *args: pd.DataFrame({'P01': 10.0}, index=days))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *args: pd.Series(1.0, index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *args: pd.DataFrame({'P01': 2.0}, index=days))
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {
        1: [{'dates': [days[1], days[3]], 'values': [10.0, 99.0]}]
    })
    raw = {'piles': [dict(label=label, parcela='P01', daily=[dict(
        date=days[2], fino_pls_final=30.0, fino_riego_final=10.0)])
        for label in ('OXIDOS', 'SULFUROS')]}
    runs = {1: dict(ws=days[2], we=days[2], caso={'run_id': 1},
                    pads={label: {'res': raw} for label in ('OXIDOS', 'SULFUROS')})}
    doc = report.construir_doc(runs, end=days[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False)
    for label in ('OXIDOS', 'SULFUROS'):
        pile = doc['pads'][label]['pilas'][0]
        assert pile['primary_anchor_date'] == str(days[1].date())
        assert pile['primary_anchor_pct'] == pytest.approx(10.0)
        assert pile['rec'] == pytest.approx([0.216, 10.0, 10.48, 10.696, 10.912])


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


def test_report_includes_inactive_campaign_history_without_case_adjustment(monkeypatch, tmp_path):
    days = pd.date_range('2026-08-01', periods=3)
    apilado = {(1, num): dict(camp=17, f0=days[0], f1=days[0], fin=100.,
                            tms=1000., ley=10.) for num in (1, 2)}
    monkeypatch.setattr(report, 'leer_apilado', lambda **kw: apilado)
    monkeypatch.setattr(report.E, 'load_riego', lambda *a: pd.DataFrame({'P01':10., 'P02':[10.,0.,0.]}, index=days))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *a: pd.Series(1., index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *a: pd.DataFrame({'P01':2.,'P02':2.},index=days))
    monkeypatch.setattr(report.E, 'FDRENA_MAX', .95)
    raw={'piles':[dict(label='OXIDOS',parcela='P01',daily=[dict(date=days[1],fino_pls_final=30.,fino_riego_final=10.)])]}
    runs={10013:dict(ws=days[1],we=days[1],caso={'run_id':10104},pads={'OXIDOS':{'res':raw}})}
    doc=report.construir_doc(runs,end=days[-1],xl=str(tmp_path/'absent.xlsx'),verbose=False)
    piles={p['num']:p for p in doc['pads']['OXIDOS']['pilas']}
    assert set(piles)=={1,2}
    assert piles[1]['rec']==pytest.approx([.216,.696,.912])
    assert piles[2]['rec']==pytest.approx([.216,.216,.216])
    out=tmp_path/'all.xlsx'
    report.escribir_libro(doc,out)
    book=load_workbook(out)
    assert [book['Rec Ox'].cell(9,c).value for c in range(2,34)]==list(range(1,33))
    assert book['Rec Ox']['C12'].value==pytest.approx(.216)
    assert book['Rec Ox']['D10'].value is None


def test_informe_global_toma_el_resultado_del_metodo_de_sulfuros_dentro_de_la_ventana(monkeypatch, tmp_path):
    days = pd.date_range('2026-08-01', periods=5)
    apilado = {(pid, 1): dict(camp=17, f0=days[0], f1=days[0], fin=100.0,
                              tms=1000.0, ley=10.0) for pid in (1, 2)}
    monkeypatch.setattr(report, 'leer_apilado', lambda **kwargs: apilado)
    monkeypatch.setattr(report.E, 'load_riego', lambda *args: pd.DataFrame({'P01': 10.0}, index=days))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *args: pd.Series(1.0, index=days))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *args: pd.DataFrame({'P01': 2.0}, index=days))
    monkeypatch.setattr(report.E, 'FDRENA_MAX', 0.95)
    rows = [dict(pad='SULFUROS', pile='P01', date='2026-08-01', reconciled_pct=50.0, recovery_source='official'),
            dict(pad='SULFUROS', pile='P01', date='2026-08-02', reconciled_pct=7.0, recovery_source='observed'),
            dict(pad='SULFUROS', pile='P01', date='2026-08-03', reconciled_pct=7.5, recovery_source='net_fit'),
            dict(pad='SULFUROS', pile='P01', date='2026-08-04', reconciled_pct=99.0, recovery_source='official')]
    res = {'piles': [dict(label='SULFUROS', parcela='P01', daily=[])], 'local_direct_recovery': True,
           'recovery_rows': rows}
    runs = {10013: dict(ws=days[1], we=days[2], caso={'run_id': 10104},
                        pads={label: {'res': res} for label in ('OXIDOS', 'SULFUROS')})}
    doc = report.construir_doc(runs, end=days[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False)
    sulfuros = doc['pads']['SULFUROS']['pilas'][0]
    # antes de la ventana y las filas oficiales no cambian; dentro manda el metodo; despues sigue con sus incrementos
    assert sulfuros['rec'] == pytest.approx([0.216, 7.0, 7.5, 7.5 + 0.216, 7.5 + 0.432])
    assert sulfuros['pct'] == pytest.approx(7.932)
    assert doc['pads']['OXIDOS']['pilas'][0]['rec'] == pytest.approx([0.216, 0.432, 0.648, 0.864, 1.08])   # Oxidos no cambia


def test_descarga_con_metodo_de_sulfuros_entrega_el_informe_global_de_ambos_pads(export_case, monkeypatch):
    data, case = export_case
    raw, _ = dashboard._load_recon_raw(data['raw_token'], case['id'])
    raw['res'] = {'piles': [], 'local_direct_recovery': True, 'recovery_rows': []}
    monkeypatch.setattr(dashboard, '_load_recon_raw', lambda *args: (raw, None))
    status, download = dashboard.generate_week_report(1, data, case['id'])
    assert 'Reporte generado' in str(status)
    book = load_workbook(BytesIO(base64.b64decode(download['content'])))
    assert {'Rec Ox', 'Rec Sulfuro', 'Curvas Ox', 'Curvas Sulfuro'} <= set(book.sheetnames)
    assert download['filename'].startswith('Reporte_Recuperaciones_Metodo_Reconciliado_Caso')
