"""Sección «Reportes de reconciliación»: curvas + reconstitución, sin SQL."""
import base64
import json
import zipfile
from io import BytesIO
from unittest.mock import patch

import pandas as pd
import pytest
from dash import Dash, dcc, html
from openpyxl import load_workbook
from plotly.utils import PlotlyJSONEncoder
from sqlalchemy.engine import Engine

from tabs import tab_reportes_recon as tab
from reconstitucion import panel as recon_panel
from curvas_recon import pad_dashboard as dashboard, report_metodo as report
from curvas_recon.test_reporte_curvas import report_doc

CASE = dict(id=10013, nombre='Prueba sintética', run_id=10104,
            fecha_inicio='2026-08-01T00:00:00', fecha_fin='2026-08-03T00:00:00',
            modelo_codigo='hidrometalurgia_125_v2', modelo_version='v2', total_flujos=125)


def ids(tree):
    found = []
    if isinstance(tree, dict):
        if 'props' in tree and 'id' in tree['props']:
            found.append(tree['props']['id'])
        for value in tree.values():
            found.extend(ids(value))
    elif isinstance(tree, list):
        for value in tree:
            found.extend(ids(value))
    return found


@pytest.fixture(autouse=True)
def no_sql(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('SQL prohibido')
    monkeypatch.setattr(Engine, 'connect', forbidden)
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {})
    monkeypatch.setattr(report, 'leer_dump', lambda asof: [])
    tab._recon_cache.clear()


def recon_loader(calls=None):
    def load(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        return dict(masa=pd.DataFrame({'caso_id': [kwargs['caso_id']]}),
                    fuente_modelo={'id': kwargs['caso_id'], 'run_id': 10104},
                    apilado=pd.DataFrame({'pad_id': [1, 2]}))
    return load


@pytest.fixture
def recon_export(monkeypatch):
    monkeypatch.setattr(recon_panel.dbs, 'get_engine', lambda: None)
    monkeypatch.setattr(recon_panel.im, 'preparar_modulos_desde_resultado',
                        lambda res, pad, quality, **kw: pd.DataFrame({'modulo': [1, 2]}))
    monkeypatch.setattr(recon_panel.im, 'exportar_desde_dataframe',
                        lambda frame, output, pad, **kw: output.write(f'xlsx pad {pad}'.encode()))
    return dict(quality_loader=lambda *a, **k: pd.DataFrame(),
                extra_loader=lambda *a: pd.DataFrame())


def fake_curvas(case_id, reconciliar=False, sulfide_policy='net_trial'):
    return (html.Div('Reporte generado (4 pilas).'),
            dcc.send_bytes(b'curvas xlsx', f'Reporte_Recuperaciones_Caso{case_id}.xlsx'))


def test_layout_y_registro_no_abren_sql():
    tree = json.loads(json.dumps(tab.layout(), cls=PlotlyJSONEncoder))
    found = ids(tree)
    assert len(found) == len(set(found))
    assert all(i.startswith('reportes-recon-') for i in found)
    app = Dash(__name__, suppress_callback_exceptions=True)
    tab.register_callbacks(app, case_loader=lambda: [])
    count = len(app.callback_map)
    tab.register_callbacks(app)
    assert count == len(app.callback_map) == 4


def test_paquete_zip_une_curvas_y_reconstitucion(recon_export):
    calls = []
    archivos, filas = tab.generar_paquete(
        CASE, ['curvas', 'recon-1', 'recon-2'], curvas_report=fake_curvas,
        recon_loader=recon_loader(calls), **recon_export)
    assert [ok for _, ok, _ in filas] == [True, True, True]
    assert len(calls) == 1  # una sola carga de reconstitución para ambos PAD
    nombre, data = tab.empaquetar(CASE, archivos, filas, ahora=pd.Timestamp('2026-11-05 10:30'))
    assert nombre == 'Reportes_Reconciliacion_Caso10013_20261105_1030.zip'
    with zipfile.ZipFile(BytesIO(data)) as archive:
        names = archive.namelist()
        assert names == ['LEEME.txt', 'Reporte_Recuperaciones_Caso10013.xlsx',
                         'informe_modulos_oxidos_caso_10013_run_10104.xlsx',
                         'informe_modulos_sulfuros_caso_10013_run_10104.xlsx']
        leeme = archive.read('LEEME.txt').decode()
        assert 'Run oficial: 10104' in leeme and 'Ventana: 01-08-2026 a 03-08-2026' in leeme
        assert archive.read(names[2]) == b'xlsx pad 1'


def test_un_informe_se_descarga_sin_zip(recon_export):
    archivos, filas = tab.generar_paquete(CASE, ['recon-2'], recon_loader=recon_loader(),
                                          **recon_export)
    nombre, data = tab.empaquetar(CASE, archivos, filas)
    assert nombre.endswith('sulfuros_caso_10013_run_10104.xlsx') and data == b'xlsx pad 2'


def test_fallas_son_independientes(recon_export):
    def curvas_sin_corrida(case_id, **kw):
        return html.Div('No hay una reconciliación vigente de este Caso en el servidor.'), None
    def sin_masa(**kwargs):
        return dict(masa=pd.DataFrame({'caso_id': [999]}))
    archivos, filas = tab.generar_paquete(CASE, ['curvas', 'recon-1'],
        curvas_report=curvas_sin_corrida, recon_loader=sin_masa, **recon_export)
    assert archivos == []
    assert [ok for _, ok, _ in filas] == [False, False]
    assert 'vigente' in filas[0][2] and 'otros Casos' in filas[1][2]


def test_callback_generar_entrega_zip_y_estado(recon_export):
    app = Dash(__name__, suppress_callback_exceptions=True)
    tab.register_callbacks(app, case_loader=lambda: [], curvas_report=fake_curvas,
                           recon_loader=recon_loader(), **recon_export)
    fn = next(v['callback'].__wrapped__ for k, v in app.callback_map.items()
              if 'reportes-recon-download.data' in k)
    download, estado = fn(1, CASE['id'], [CASE], ['curvas', 'recon-1'], 'ultima', 'net_trial', 'volumen')
    assert download['type'] == 'application/zip' and download['base64']
    assert zipfile.ZipFile(BytesIO(base64.b64decode(download['content']))).testzip() is None
    assert 'Listo' in json.dumps(estado, cls=PlotlyJSONEncoder)
    assert fn(1, 999, [CASE], ['curvas'], 'ultima', 'net_trial', 'volumen')[0] is None


def test_catalogo_solo_runs_oficiales():
    app = Dash(__name__, suppress_callback_exceptions=True)
    rows = [dict(CASE, fecha_inicio=pd.Timestamp('2026-08-01'), fecha_fin=pd.Timestamp('2026-08-03')),
            dict(CASE, id=1, run_id=None)]
    tab.register_callbacks(app, case_loader=lambda: rows)
    fn = next(v['callback'].__wrapped__ for k, v in app.callback_map.items()
              if 'reportes-recon-casos.data' in k)
    cases, options, value, _ = fn(1, None)
    assert [c['id'] for c in cases] == [10013] and value == 10013
    broken = Dash(__name__, suppress_callback_exceptions=True)
    tab.register_callbacks(broken, case_loader=lambda: 1 / 0)
    fn = next(v['callback'].__wrapped__ for k, v in broken.callback_map.items()
              if 'reportes-recon-casos.data' in k)
    assert fn(1, None)[:3] == (None, [], None)


@pytest.fixture
def saved_runs(monkeypatch, tmp_path):
    start, end = pd.Timestamp('2026-08-01'), pd.Timestamp('2026-08-03')
    case = dict(CASE, fecha_inicio=start, fecha_fin=end)
    other = dict(case, id=10014)
    monkeypatch.setattr(dashboard, 'CASOS', [case, other])
    monkeypatch.setattr(dashboard, '_load_caso_options', lambda: ([case, other], [], case['id']))
    monkeypatch.setattr(dashboard, 'JOINT_DATA_CUTOFF', end)
    monkeypatch.setattr(dashboard, '_RECON_RAW_DIR', str(tmp_path / 'raw'))
    monkeypatch.setattr(dashboard, 'initialize_data', lambda force=False: None)
    monkeypatch.setattr(dashboard, 'ensure_full_data', lambda force=False: None)
    monkeypatch.setattr(report, 'XL_PLANTA', str(tmp_path / 'planta_ausente.xlsx'))
    monkeypatch.setattr(report, 'construir_doc', lambda *args, **kwargs: report_doc())
    import os, time
    old = dashboard._save_recon_raw({'piles': []}, case, start, end)
    os.utime(dashboard._recon_raw_path(old), (time.time() - 60, time.time() - 60))
    new = dashboard._save_recon_raw({'piles': []}, case, start, end)
    dashboard._save_recon_raw({'piles': []}, other, start, end)
    return case, old, new


def test_ultima_corrida_del_caso_genera_libro_sin_recalcular(saved_runs, monkeypatch):
    case, old, new = saved_runs
    monkeypatch.setattr(dashboard, 'compute_recon',
                        lambda *a, **k: pytest.fail('No debe reconciliar'))
    store = dashboard.latest_recon_store(case['id'])
    assert store['raw_token'] == new and store['caso_run_id'] == case['run_id']
    assert dashboard.latest_recon_store(424242) is None
    status, download = dashboard.generate_case_report(case['id'])
    assert download is not None, str(status)
    book = load_workbook(BytesIO(base64.b64decode(download['content'])))
    assert book.sheetnames[:2] == ['Oxido', 'Sulfuro']


def test_sin_corrida_vigente_pide_reconciliar(saved_runs, monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard, '_RECON_RAW_DIR', str(tmp_path / 'vacio'))
    status, download = dashboard.generate_case_report(saved_runs[0]['id'])
    assert download is None and 'Reconciliar ahora' in str(status)


def test_reconciliar_ahora_usa_calculo_de_curvas(saved_runs, monkeypatch):
    case, _old, new = saved_runs
    seen = {}
    def compute(n, caso_id, policy):
        seen.update(caso_id=caso_id, policy=policy)
        return dashboard.latest_recon_store(caso_id), False, None
    monkeypatch.setattr(dashboard, 'compute_recon', compute)
    status, download = dashboard.generate_case_report(case['id'], reconciliar=True,
                                                      sulfide_policy='legacy')
    assert seen == dict(caso_id=case['id'], policy='legacy') and download is not None
    monkeypatch.setattr(dashboard, 'compute_recon',
                        lambda *a: (dashboard.dash.no_update, True, html.Div('Ancla incompleta')))
    status, download = dashboard.generate_case_report(case['id'], reconciliar=True)
    assert download is None and 'Ancla incompleta' in str(status)


def test_reporte_oficial_usa_recuperacion_directa_del_ensayo(saved_runs, monkeypatch):
    """Hito 4: con el método maduras/nuevas, el libro oficial toma la
    recuperación directa en vez de reconstruirla desde Q/Cu."""
    case, _old, _new = saved_runs
    start, end = pd.Timestamp('2026-08-01'), pd.Timestamp('2026-08-03')
    token = dashboard._save_recon_raw({'piles': [], 'local_direct_recovery': True}, case, start, end)
    series = {('SULFUROS', 1): pd.Series([1.0, 2.0], index=pd.to_datetime(['2026-08-01', '2026-08-02']))}
    import curvas_recon.maduras_nuevas as mn
    monkeypatch.setattr(mn, 'direct_recovery_series', lambda res: series)
    seen = {}
    def construir(runs, end=None, direct_recovery=None, **kw):
        seen['direct'] = direct_recovery
        return report_doc()
    monkeypatch.setattr(report, 'construir_doc', construir)
    data = dict(caso_id=case['id'], caso_run_id=case['run_id'], raw_token=token,
                week_start=start.isoformat(), week_end=end.isoformat(), local_direct_recovery=True)
    status, download = dashboard.generate_week_report(1, data, case['id'])
    assert download is not None, str(status)
    assert seen['direct'] is series
    assert 'ensayo neto local' in str(status)
    assert load_workbook(BytesIO(base64.b64decode(download['content']))).sheetnames[0] == 'Oxido'


def test_paquete_agrega_auditoria_del_ensayo(recon_export):
    archivos, filas = tab.generar_paquete(
        CASE, ['curvas'], curvas_report=fake_curvas,
        curvas_audit=lambda cid: (f'Auditoria_Ensayo_Neto_Local_Caso{cid}.xlsx', b'audit'))
    assert [n for n, _ in archivos] == ['Reporte_Recuperaciones_Caso10013.xlsx',
                                        'Auditoria_Ensayo_Neto_Local_Caso10013.xlsx']
    assert all(ok for _, ok, _ in filas)


def test_metodo_recalibrado_se_pide_solo_si_se_elige(recon_export):
    calls = []
    tab.generar_paquete(CASE, ['recon-2'], recon_loader=recon_loader(calls), **recon_export)
    tab.generar_paquete(CASE, ['recon-2'], recon_loader=recon_loader(calls),
                        recon_metodo='recalibrada', **recon_export)
    assert 'metodo' not in calls[0] and calls[1]['metodo'] == 'recalibrada'
    nombre, data = tab.empaquetar(dict(CASE, _recon_metodo='recalibrada'),
                                  [('a.xlsx', b'1'), ('b.xlsx', b'2')], [])
    assert 'densidad recalibrada' in zipfile.ZipFile(BytesIO(data)).read('LEEME.txt').decode()
