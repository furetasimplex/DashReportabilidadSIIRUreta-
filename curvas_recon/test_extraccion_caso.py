"""Formato del Excel de extraccion de un Caso: ida y vuelta sin SQL, y guardia de solo lectura."""
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from curvas_recon.extraccion_caso import SHEETS, build_tables, read_workbook, write_workbook


def sample():
    days = pd.date_range('2026-09-25', '2026-10-03')
    series = {
        'SULFUROS': dict(riego=pd.DataFrame({'P24': [100.0] * 9, 'P25': [0.0] * 4 + [120.0] * 5}, index=days),
                         cu_riego=pd.Series([0.4, 0.41, None] + [0.42] * 6, index=days, name='cu_riego'),
                         cu_drena=pd.DataFrame({'P24': [2.0] * 9, 'P25': [None] * 4 + [3.0] * 5}, index=days)),
        'OXIDOS': dict(riego=pd.DataFrame({'P01': [50.0] * 9}, index=days),
                       cu_riego=pd.Series([0.3] * 9, index=days, name='cu_riego'),
                       cu_drena=pd.DataFrame({'P01': [1.5] * 9}, index=days)),
    }
    case = dict(id=10013, nombre='Caso prueba', run_id=10104, fecha_inicio=pd.Timestamp('2026-10-01'),
                fecha_fin=pd.Timestamp('2026-10-03'), modelo_codigo='hidrometalurgia_125_v2', modelo_version='v2',
                total_flujos=125)
    flows = [('F29', 1.0, 1.0, 1781.68, 1781.68), ('F72', 970969.0, 974017.0, 505.5, 516.99)]
    recoveries = [('SULFUROS', 24, 11, date(2026, 10, 1), 33.25), ('SULFUROS', 24, 11, date(2026, 10, 2), 34.0),
                  ('OXIDOS', 1, 18, date(2026, 10, 1), 72.0)]
    wip = {'SULFUROS': {'P24': dict(ini_aporte=pd.Timestamp('2026-08-15'), fin_ciclo=pd.NaT, CuTf=4551.9, sin_campana=False)},
           'OXIDOS': {'P01': dict(ini_aporte=pd.Timestamp('2025-12-16'), fin_ciclo=pd.NaT, CuTf=1415.9, sin_campana=False)}}
    first = {'SULFUROS': {'P24': pd.Timestamp('2026-08-15')}, 'OXIDOS': {'P01': pd.Timestamp('2025-12-16')}}
    stacking = {(2, 24): dict(camp=11, f0=pd.Timestamp('2026-07-20'), f1=pd.Timestamp('2026-08-10'), fin=4551.9, tms=1e5, ley=4.55)}
    saved = {('P24', '2026-10-01'): 80.5, ('P24', '2026-10-02'): 81.0}
    history = [dict(date=date(2026, 9, 30), label='SULFUROS', parcela='P24', caso_id=10009, run_id=1, fdrena=0.9,
                    q=100.0, q_pls=90.0, cu_riego=0.4, cu_drena=2.1)]
    return dict(case=case, window=(pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-03')), flows=flows, series=series,
                recoveries=recoveries, wip=wip, first_irrigation=first, stacking=stacking, saved_profile=saved,
                history=history, notes=('nota de prueba',))


def test_workbook_roundtrip_keeps_every_series_without_filling_gaps(tmp_path):
    data = sample()
    tables = build_tables(**data)
    assert tuple(tables) == SHEETS
    path = write_workbook(tables, tmp_path / 'caso.xlsx')
    back = read_workbook(path)
    assert back['case']['run_id'] == 10104 and back['case']['ventana_inicio'] == '2026-10-01'
    riego = back['series']['SULFUROS']['riego']
    pd.testing.assert_frame_equal(riego, data['series']['SULFUROS']['riego'], check_freq=False, check_names=False)
    cu_riego = back['series']['SULFUROS']['cu_riego']
    assert cu_riego.isna().sum() == 0 and len(cu_riego) == 8                      # el hueco del 27-sep NO se rellena
    cu_drena = back['series']['SULFUROS']['cu_drena']
    assert cu_drena['P25'].isna().sum() == 4 and cu_drena['P24'].tolist() == [2.0] * 9
    assert back['curves']['SULFUROS'][24] == dict(dates=[date(2026, 10, 1), date(2026, 10, 2)], values=[33.25, 34.0])
    assert back['wip']['SULFUROS']['P24']['CuTf'] == pytest.approx(4551.9)
    assert back['first_irrigation']['OXIDOS']['P01'] == pd.Timestamp('2025-12-16')
    assert back['saved_profile'] == {('P24', '2026-10-01'): 80.5, ('P24', '2026-10-02'): 81.0}
    assert back['stacking'].iloc[0]['cu_fino_t'] == pytest.approx(4551.9)
    assert back['flows'].set_index('codigo_flujo').loc['F29', 'fino_cu_reconciliado'] == pytest.approx(1781.68)
    assert len(back['history']) == 1 and 'nota de prueba' in back['summary'].to_string()


def test_extracted_workbook_feeds_the_method_inputs(tmp_path):
    """Lo extraido alcanza para armar las filas del ajuste de Sulfuros (mismo cargador que el dash)."""
    from curvas_recon.sulfide_db_inputs import build_sulfide_rows
    days = pd.date_range('2026-09-28', '2026-10-03')
    data = sample()
    data['series']['SULFUROS'] = dict(riego=pd.DataFrame({'P24': [100.0] * 6}, index=days),
                                      cu_riego=pd.Series([0.4] * 6, index=days, name='cu_riego'),
                                      cu_drena=pd.DataFrame({'P24': [2.0] * 6}, index=days))
    data['recoveries'] = [('SULFUROS', 24, 11, d.date(), 30.0 + 0.1 * i) for i, d in enumerate(pd.date_range('2026-08-15', '2026-10-03'))]
    back = read_workbook(write_workbook(build_tables(**data), tmp_path / 'caso.xlsx'))
    sulfuros = back['series']['SULFUROS']
    window = back['case']
    rows, _ = build_sulfide_rows(window['ventana_inicio'], window['ventana_fin'], sulfuros, back['curves']['SULFUROS'],
                                 back['wip']['SULFUROS'], back['first_irrigation']['SULFUROS'], back['saved_profile'])
    assert {r['pile'] for r in rows} == {'P24'} and rows[-1]['date'] == '2026-10-03'


def test_extraction_script_connection_only_accepts_selects():
    from sqlalchemy import create_engine, text
    spec = importlib.util.spec_from_file_location('extraer', ROOT / 'scripts' / 'extraer_datos_caso.py')
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE t (a INTEGER)'))
    script.install_select_only_guard(engine)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT 1')).scalar() == 1
        assert conn.execute(text('WITH x AS (SELECT 2 AS v) SELECT v FROM x')).scalar() == 2
        for bad in ('INSERT INTO t VALUES (1)', 'UPDATE t SET a = 2', 'DELETE FROM t', 'DROP TABLE t',
                    'SELECT a INTO copia FROM t', 'SELECT 1; DROP TABLE t'):
            with pytest.raises(Exception, match='no SELECT'):
                conn.execute(text(bad))
