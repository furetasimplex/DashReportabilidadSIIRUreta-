"""Libro de 15 hojas con el formato del reporte oficial: estructura, formulas,
graficos, Dump reconciliado, recuperacion directa y comparador de formato.

Sin SQL. Las pruebas de valores recalculan las formulas con LibreOffice
(headless) y se saltan si no esta instalado.
"""
import json
import shutil
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

from . import report_dump, report_metodo as report
from .report_layout import ORDEN, ORDEN_HOJAS

ROOT = Path(__file__).resolve().parents[1]
FIRMA = ROOT / 'test_fixtures' / 'referencias' / 'firma_reporte_oficial.json'
HOJAS_OFICIALES = [
    'Oxido', 'Sulfuro', 'Dump', 'Rec Ox', 'Rec Ox 2', 'Prod Cu Oxidos',
    '(Cu) dren Ox', 'Flujo Riego Ox', 'RL Oxidos', 'Rec Sulfuro',
    'Rec Sulfuro 2', 'Prod Cu Sulfuros', '(Cu) dren Sulf.',
    'Flujo Riego Sulf', 'RL Sulfuro']


@pytest.fixture(autouse=True)
def sin_sql(monkeypatch):
    from sqlalchemy.engine import Engine

    def prohibido(*args, **kwargs):
        raise AssertionError('SQL prohibido')
    monkeypatch.setattr(Engine, 'connect', prohibido)


def recalcular(path, outdir):
    """Copia del libro con las formulas calculadas por LibreOffice (o skip)."""
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice:
        pytest.skip('LibreOffice no disponible para recalcular formulas')
    out = Path(outdir) / 'recalculado'
    out.mkdir(exist_ok=True)
    perfil = Path(outdir) / 'perfil_lo'
    subprocess.run([soffice, f'-env:UserInstallation={perfil.as_uri()}', '--headless',
                    '--convert-to', 'xlsx', '--outdir', str(out), str(path)],
                   check=True, capture_output=True, timeout=240)
    return out / Path(path).name


def oficial_doc(dias=40, corte='2026-10-12'):
    """Doc sintetico completo: 32 pilas de oxidos y 28 de sulfuros."""
    fin = pd.Timestamp(corte)
    desde = fin - pd.Timedelta(days=dias - 1)
    calendario = pd.date_range(desde, fin)
    pads = {}
    for label, total in (('OXIDOS', 32), ('SULFUROS', 28)):
        pilas = []
        for num in range(1, total + 1):
            ini = desde + pd.Timedelta(days=num % 5)
            n = (fin - ini).days + 1
            apilado = 1000.0 + 10 * num
            rec = np.round(np.cumsum(np.linspace(2.0, 0.5, n)), 3)
            curva = [None] * 2 + [float(x) for x in rec[2:]]
            pilas.append(dict(
                p='P%02d' % num, num=num, campana=17, ini=str(ini.date()), n=n,
                apilado=apilado, tms=50000.0 + num, t_rec=float(rec[-1]),
                t_med=float(rec[-1]), pct=1.0, planta_rec_termino=70.0 + num % 3,
                rec=[float(x) for x in rec], rec_curve=curva,
                rl_curve=[0.01] * n, rl_accum_curve=[0.01 * (i + 1) for i in range(n)],
                riego_curve=[3000.0 + i for i in range(len(calendario))],
                dren_cu_curve=[2.0 + 0.01 * i for i in range(len(calendario))],
                vol_riego=1.0))
        pads[label] = dict(pilas=pilas, desde=str(desde.date()))
    dump = [dict(fecha=fin - pd.Timedelta(days=k), aporte=10.0 + k, flujo_riego=20000.0,
                 flujo_salida=15000.0, cu_feed=0.2, cu_drenaje=2.0) for k in range(10, -1, -1)]
    return dict(pads=pads, end=corte, corte_planta='2026-07-31', dump=dump,
                casos=[dict(id=10013, desde='2026-10-01', hasta=corte, run=10145)])


@pytest.fixture(scope='module')
def libro(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp('oficial')
    doc = oficial_doc()
    ruta = carpeta / 'libro.xlsx'
    report.escribir_libro(doc, ruta)
    return doc, ruta, carpeta


def test_quince_hojas_visibles_en_orden_oficial_sin_ocultas(libro):
    _, ruta, _ = libro
    book = load_workbook(ruta)
    assert book.sheetnames == HOJAS_OFICIALES == ORDEN_HOJAS
    assert all(ws.sheet_state == 'visible' for ws in book)
    for oculta in ('Budget FY16 y Q1', 'Rec Ox_gr', 'Rec Sulfuro_gr'):
        assert oculta not in book.sheetnames


def test_encabezado_rec_ox_y_rec_sulfuro_con_formulas_oficiales(libro):
    _, ruta, _ = libro
    book = load_workbook(ruta)
    ox = book['Rec Ox']
    assert [ox.cell(r, 1).value for r in range(1, 9)] == [
        'Campaña', 'Ciclos', 'Recuperación máx.', 'Aporte Parcelas', 'Apilado tmf',
        'Rec por especie', 'Recuperable', 'WIP']
    assert [ox.cell(9, c).value for c in range(2, 34)] == list(range(1, 33))
    assert ox['B1'].value == 17
    assert ox['B2'].value.startswith('=+LOOKUP(B3,B10:B')
    assert ox['B3'].value.startswith('=+MAX(B10:B')
    assert ox['B4'].value.startswith("=+SUM('Prod Cu Oxidos'!B")
    assert ox['B5'].value == "=+'Rec Ox 2'!C3"
    assert ox['AG5'].value == "=+'Rec Ox 2'!AH3"          # P32 = columna AH
    assert ox['B6'].value == 71.0                           # valor (viene de libro externo)
    assert ox['B7'].value == '=+B5*B6/100' and ox['B8'].value == '=+B7-B4'
    assert ox['A10'].value == 1 and ox.freeze_panes == 'B10'

    su = book['Rec Sulfuro']
    assert [su.cell(10, c).value for c in range(2, 30)] == list(range(21, 29)) + list(range(1, 21))
    assert su['A10'].value == 'Dias Lix' and su['A11'].value == 1
    assert su['B5'].value == "=+'Rec Sulfuro 2'!D1"
    assert su['B2'].value.startswith('=+LOOKUP(B3,B11:B') and su.freeze_panes == 'B11'


def test_rec2_acumula_prod_sobre_apilado_por_fecha(libro):
    doc, ruta, carpeta = libro
    book = load_workbook(ruta)
    ox = book['Rec Ox 2']
    assert ox['B5'].value == 'Parcela' and ox['C5'].value == 1 and ox['AH5'].value == 32
    assert ox['C3'].value == doc['pads']['OXIDOS']['pilas'][0]['apilado']
    pila1 = doc['pads']['OXIDOS']['pilas'][0]
    fila_ini = 6 + (pd.Timestamp(pila1['ini']) - pd.Timestamp(doc['pads']['OXIDOS']['desde'])).days
    assert ox.cell(fila_ini, 3).value == f"=+'Prod Cu Oxidos'!B{fila_ini - 1}*100/$C$3"
    assert ox.cell(fila_ini + 1, 3).value == (
        f"=+'Prod Cu Oxidos'!B{fila_ini}*100/$C$3+C{fila_ini}")
    assert ox.freeze_panes == 'A4'
    su = book['Rec Sulfuro 2']
    assert su['C4'].value == 'Parcela' and su['D4'].value == 21 and su['L4'].value == 1
    assert su['D1'].value == doc['pads']['SULFUROS']['pilas'][20]['apilado']  # P21
    assert su.freeze_panes == 'D5'
    # valores recalculados: Rec Ox 2 == curva reconstruida en % del apilado
    calc = load_workbook(recalcular(ruta, carpeta), data_only=True)
    fin = calc['Rec Ox 2'].cell(fila_ini + pila1['n'] - 1, 3).value
    assert fin == pytest.approx(pila1['rec'][-1] * 100 / pila1['apilado'], rel=1e-6)
    assert calc['Rec Ox']['B4'].value == pytest.approx(pila1['rec'][-1], rel=1e-6)
    # los dias ocultos (rec_curve None) quedan en blanco en la curva de Rec Ox
    assert calc['Rec Ox']['B10'].value is None and calc['Rec Ox']['B11'].value is None
    assert calc['Rec Ox']['B12'].value == pytest.approx(pila1['rec'][2] * 100 / pila1['apilado'], rel=1e-6)
    assert calc['Rec Ox']['B3'].value == pytest.approx(pila1['rec'][-1] * 100 / pila1['apilado'], rel=1e-6)


def test_prod_total_diario_y_total_suma_del_mes_hasta_el_corte(libro):
    doc, ruta, carpeta = libro
    book = load_workbook(ruta)
    ox, su = book['Prod Cu Oxidos'], book['Prod Cu Sulfuros']
    assert [ox.cell(4, c).value for c in (1, 2, 3, 33, 34, 36)] == ['Parcela', 1, 2, 32, 'PH', 'Total Prod']
    assert [su.cell(4, c).value for c in (1, 2, 9, 10, 29, 31)] == ['Parcela', 21, 28, 1, 20, 'Total Prod']
    assert ox['AJ5'].value == '=+SUM(B5:AH5)' and su['AE5'].value == '=+SUM(B5:AC5)'
    desde = pd.Timestamp(doc['pads']['OXIDOS']['desde'])
    fila_mes = 5 + (pd.Timestamp('2026-10-01') - desde).days
    fila_corte = 5 + (pd.Timestamp('2026-10-12') - desde).days
    assert ox.cell(fila_mes, 38).value == 'Total Suma'
    assert ox.cell(fila_mes + 1, 38).value == f'=+SUM(AJ{fila_mes}:AJ{fila_corte})'
    assert su.cell(fila_mes, 33).value == 'Total Suma'
    assert su.cell(fila_mes + 1, 33).value == f'=+SUM(AE{fila_mes}:AE{fila_corte})'
    calc = load_workbook(recalcular(ruta, carpeta), data_only=True)
    pc = calc['Prod Cu Oxidos']
    esperado = sum(pc.cell(r, 36).value for r in range(fila_mes, fila_corte + 1))
    assert pc.cell(fila_mes + 1, 38).value == pytest.approx(esperado)
    # el total diario es la suma de las pilas de ese dia
    fila = fila_corte
    assert pc.cell(fila, 36).value == pytest.approx(
        sum(pc.cell(fila, c).value or 0 for c in range(2, 35)))


def test_dren_y_flujo_riego_por_pila_con_encabezado_oficial(libro):
    doc, ruta, carpeta = libro
    book = load_workbook(ruta)
    dren = book['(Cu) dren Ox']
    assert [dren.cell(4, c).value for c in (1, 2, 3, 33, 34)] == ['Cu++', 'P1Cu++', 'P2Cu++', 'P32Cu++', 'PHCu++']
    assert dren['A5'].value == pd.Timestamp(doc['pads']['OXIDOS']['desde']).to_pydatetime()
    assert dren['B5'].value == pytest.approx(2.0)
    assert dren.freeze_panes == 'B5'
    sulf = book['(Cu) dren Sulf.']
    assert [sulf.cell(4, c).value for c in (2, 9, 10, 29)] == ['P21Cu++', 'P28Cu++', 'P1Cu++', 'P20Cu++']
    flujo = book['Flujo Riego Ox']
    assert [flujo.cell(r, 1).value for r in range(1, 6)] == [
        'RL/días de riego', 'RL', 'TMS apiladas', 'Sum riego', 'Parcela']
    assert flujo['B3'].value == doc['pads']['OXIDOS']['pilas'][0]['tms']
    assert flujo['B2'].value == '=+B4/B3'
    assert flujo['B4'].value.startswith('=+SUM(B')
    assert flujo['B1'].value.startswith('=(B2/(COUNTIF(B') and flujo['B1'].value.endswith(',">0")))*1000')
    assert flujo['B5'].value == 1 and flujo['B6'].value == pytest.approx(3000.0)
    assert flujo.freeze_panes == 'B6'
    assert [book['Flujo Riego Sulf'].cell(5, c).value for c in (2, 9, 10)] == [21, 28, 1]
    calc = load_workbook(recalcular(ruta, carpeta), data_only=True)
    pila = doc['pads']['OXIDOS']['pilas'][0]
    ini = (pd.Timestamp(pila['ini']) - pd.Timestamp(doc['pads']['OXIDOS']['desde'])).days
    suma = sum(pila['riego_curve'][ini:])
    assert calc['Flujo Riego Ox']['B4'].value == pytest.approx(suma)
    assert calc['Flujo Riego Ox']['B2'].value == pytest.approx(suma / pila['tms'])


def test_graficos_agrupados_titulos_series_y_estilo(libro):
    _, ruta, _ = libro
    book = load_workbook(ruta)

    def titulo(chart):
        return ''.join(r.t for p in chart.title.tx.rich.p for r in (p.r or []))

    esperados = {
        'Oxido': (['% Extracción Parcelas 1-8 Óxidos', '% Extracción Parcelas 9-16 Óxidos',
                   '% Extracción Parcelas 17-24 Óxidos', '% Extracción Parcelas 25-32 Óxidos'], 8),
        'Sulfuro': (['% Extracción Parcelas 1-7: Lado Este', '% Extracción Parcelas 8-14: Lado Este',
                     '% Extracción Parcelas 15-21: Lado Oeste', '% Extracción Parcelas 22-28: Lado Oeste'], 7),
        'RL Oxidos': (['Recuperación vs RL (P1-8 Oxidos)', 'Recuperación vs RL (P9-16 Oxidos)',
                       'Recuperación vs RL (P17-24 Oxidos)', 'Recuperación vs RL (P25-32 Oxidos)'], 8),
        'RL Sulfuro': (['Recuperación vs RL (P1-7 Sulfuros)', 'Recuperación vs RL (P8-14 Sulfuros)',
                        'Recuperación vs RL (P15-21 Sulfuros)', 'Recuperación vs RL (P22-28 Sulfuros)'], 7),
    }
    for hoja, (titulos, n_series) in esperados.items():
        charts = book[hoja]._charts
        assert [titulo(c) for c in charts] == titulos
        assert all(type(c).__name__ == 'ScatterChart' for c in charts)
        assert [len(c.series) for c in charts] == [n_series] * 4
    ox = book['Oxido']._charts
    assert ox[0].series[0].tx.strRef.f == "'Rec Ox'!$B$9"
    assert ox[2].series[0].tx.strRef.f == "'Rec Ox'!$R$9"         # P17 = columna R
    assert ox[0].series[0].xVal.numRef.f.startswith("'Rec Ox'!$A$10:$A$")
    assert ox[0].series[0].yVal.numRef.f.startswith("'Rec Ox'!$B$10:$B$")
    assert ox[0].series[0].graphicalProperties.line.w == 19050
    assert ox[0].series[0].marker.symbol in (None, 'none') and ox[0].series[0].smooth
    assert ox[0].y_axis.scaling.max == 100 and ox[1].y_axis.scaling.max == 110
    assert ox[0].x_axis.scaling.max == 360 and ox[0].x_axis.majorUnit == 30
    assert ox[0].y_axis.title is not None
    su = book['Sulfuro']._charts
    # Rec Sulfuro lista P21..P28, P1..P20: P1 es la columna J, P8 la Q
    assert su[0].series[0].tx.strRef.f == "'Rec Sulfuro'!$J$10"
    assert su[1].series[0].tx.strRef.f == "'Rec Sulfuro'!$Q$10"
    rl = book['RL Oxidos']._charts
    assert rl[0].series[0].xVal.numRef.f.startswith("'RL Oxidos'!$B$2:$B$")
    assert rl[0].series[0].yVal.numRef.f.startswith("'RL Oxidos'!$")


def test_rl_orden_ascendente_y_bloque_de_recuperacion(libro):
    doc, ruta, carpeta = libro
    book = load_workbook(ruta)
    rl = book['RL Sulfuro']
    assert [rl.cell(1, c).value for c in range(1, 4)] == ['Parcela', 1, 2]
    assert rl['AC1'].value == 28
    assert rl['A2'].value == 1 and rl['B2'].value == pytest.approx(0.01)
    # bloque de recuperacion a la derecha de los graficos, formulas hacia Rec Sulfuro
    cabecera = [c.column for c in rl[1] if c.value == 'Recuperación [%]']
    assert len(cabecera) == 1
    col = cabecera[0] + 1
    assert rl.cell(1, col).value == 1
    assert str(rl.cell(4, col).value).startswith("=+'Rec Sulfuro'!J")
    calc = load_workbook(recalcular(ruta, carpeta), data_only=True)
    pila1 = doc['pads']['SULFUROS']['pilas'][0]
    assert calc['RL Sulfuro'].cell(4, col).value == pytest.approx(
        pila1['rec'][2] * 100 / pila1['apilado'], rel=1e-6)


# ── Dump reconciliado ───────────────────────────────────────────────────────

def _medidos():
    dias = pd.date_range('2026-10-01', periods=5)
    return [dict(fecha=d, aporte=None, flujo_riego=1000.0 * (i + 1), flujo_salida=500.0,
                 cu_feed=0.2, cu_drenaje=2.0) for i, d in enumerate(dias)]


def test_dump_reconciliado_aplica_factor_global_y_deja_en_blanco_fuera_del_caso():
    runs = {10013: dict(ws=pd.Timestamp('2026-10-02'), we=pd.Timestamp('2026-10-04'),
                        caso=dict(run_id=10145, modelo_codigo='hidrometalurgia_125_v2'))}
    # F77: medido 10.000 -> reconciliado 12.000 (x1,2); F51 reconciliado 9.000 => F = 0,75
    lector = lambda run: {'F77': (10000.0, 12000.0), 'F51': (8000.0, 9000.0)}
    filas, meta, avisos = report_dump.dump_reconciliado(_medidos(), runs, lector=lector)
    assert avisos == []
    assert meta[10013]['razon_riego'] == pytest.approx(1.2)
    assert meta[10013]['factor_drenaje'] == pytest.approx(0.75)
    # filas desde el primer dia del Caso (02) hasta el ultimo dato medido (05)
    assert [f['fecha'] for f in filas] == list(pd.date_range('2026-10-02', '2026-10-05'))
    d2 = filas[0]
    assert d2['flujo_riego'] == pytest.approx(2000.0 * 1.2)
    assert d2['flujo_salida'] == pytest.approx(0.75 * 2000.0 * 1.2)
    assert d2['aporte'] == pytest.approx((0.75 * 2400.0 * 2.0 - 2400.0 * 0.2) / 1000.0)
    assert (d2['cu_feed'], d2['cu_drenaje']) == (0.2, 2.0)
    # drenaje reconciliado = F x riego reconciliado, todos los dias del Caso
    for f in filas[:3]:
        assert f['flujo_salida'] == pytest.approx(0.75 * f['flujo_riego'])
    # 05 esta fuera del Caso: solo la fecha
    fuera = filas[3]
    assert fuera['fecha'] == pd.Timestamp('2026-10-05')
    assert all(fuera[k] is None for k in ('aporte', 'flujo_riego', 'flujo_salida', 'cu_feed', 'cu_drenaje'))


@pytest.mark.parametrize('flujos, caso, motivo', [
    ({}, dict(run_id=1, modelo_codigo='hidrometalurgia_125_v2'), 'F77'),
    ({'F77': (10.0, 12.0)}, dict(run_id=1), 'F51'),
    ({'F77': (0.0, 0.0), 'F51': (1.0, 1.0)}, dict(run_id=1), 'no positivo'),
    ({'F77': (1.0, 1.0), 'F51': (1.0, 1.0)}, dict(run_id=1, modelo_codigo='hidrometalurgia_120_completo'), 'modelo'),
    ({'F77': (1.0, 1.0), 'F51': (1.0, 1.0)}, dict(run_id=None), 'sin run'),
])
def test_dump_sin_flujos_del_run_queda_en_blanco_con_aviso(flujos, caso, motivo):
    runs = {7: dict(ws=pd.Timestamp('2026-10-01'), we=pd.Timestamp('2026-10-02'), caso=caso)}
    filas, meta, avisos = report_dump.dump_reconciliado(_medidos(), runs, lector=lambda run: flujos)
    assert len(avisos) == 1 and motivo in avisos[0]
    assert all(f['flujo_riego'] is None and f['aporte'] is None for f in filas)


def test_dump_lee_flujos_del_run_solo_con_select(monkeypatch):
    class Conexion:
        consulta, parametros = '', None

        def execute(self, query, params):
            self.consulta, self.parametros = str(query), params
            return SimpleNamespace(fetchall=lambda: [('F77', 10.0, 12.0), ('F51', 8.0, 9.0)])

    falsa = Conexion()
    motor = SimpleNamespace(connect=lambda: nullcontext(falsa))
    import curvas_recon.db_pipeline as db
    monkeypatch.setattr(db, 'get_engine', lambda: motor)
    assert report_dump.leer_flujos_dump_caso(10145) == {'F77': (10.0, 12.0), 'F51': (8.0, 9.0)}
    sql = falsa.consulta.upper()
    assert 'SELECT' in sql and 'RECON_RESULTADO_FLUJO' in sql
    assert falsa.parametros == dict(run=10145, riego='F77', drenaje='F51')
    assert not any(w in sql for w in ('INSERT', 'UPDATE', 'DELETE', 'EXEC '))


def test_construir_doc_usa_flujos_reconciliados_del_run_en_dump(monkeypatch, tmp_path):
    dias = pd.date_range('2026-08-01', periods=3)
    apilado = {(1, 1): dict(camp=17, f0=dias[0], f1=dias[0], fin=100.0, tms=1000.0, ley=10.0)}
    monkeypatch.setattr(report, 'leer_apilado', lambda **kw: apilado)
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {})
    monkeypatch.setattr(report.E, 'load_riego', lambda *a: pd.DataFrame({'P01': 10.0}, index=dias))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *a: pd.Series(1.0, index=dias))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *a: pd.DataFrame({'P01': 2.0}, index=dias))
    monkeypatch.setattr(report, 'leer_dump', lambda asof: [
        dict(fecha=d, aporte=None, flujo_riego=100.0, flujo_salida=50.0, cu_feed=0.2, cu_drenaje=2.0)
        for d in dias])
    monkeypatch.setattr(report_dump, 'leer_flujos_dump_caso',
                        lambda run: {'F77': (10.0, 20.0), 'F51': (5.0, 10.0)})
    raw = {'piles': [dict(label='OXIDOS', parcela='P01', daily=[dict(
        date=dias[1], fino_pls_final=30.0, fino_riego_final=10.0, q_riego_final=10.0,
        q_pls_final=9.0, cu_pls_recon=3.3)])]}
    runs = {10013: dict(ws=dias[1], we=dias[2], caso={'run_id': 10104, 'modelo_codigo': 'hidrometalurgia_125_v2'},
                        pads={'OXIDOS': {'res': raw}})}
    doc = report.construir_doc(runs, end=dias[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False)
    assert [f['fecha'] for f in doc['dump']] == list(dias[1:])
    # razon de riego 2,0; F = 10/20 = 0,5
    assert doc['dump'][0]['flujo_riego'] == pytest.approx(200.0)
    assert doc['dump'][0]['flujo_salida'] == pytest.approx(100.0)
    assert doc['dump'][0]['aporte'] == pytest.approx((100.0 * 2.0 - 200.0 * 0.2) / 1000.0)
    assert doc['dump_meta'][10013]['factor_drenaje'] == pytest.approx(0.5)
    # ley de drenaje: reconciliada dentro del Caso (dia 2), medida fuera (dia 1)
    pila = doc['pads']['OXIDOS']['pilas'][0]
    assert pila['dren_cu_curve'] == pytest.approx([2.0, 3.3, 2.0])
    # riego m3/dia: medido x24 fuera del Caso, q_riego_final x24 dentro
    assert pila['riego_curve'] == pytest.approx([240.0, 240.0, 240.0])


# ── recuperacion directa ────────────────────────────────────────────────────

def _entorno_directa(monkeypatch):
    dias = pd.date_range('2026-08-01', periods=5)
    apilado = {(pid, 1): dict(camp=17, f0=dias[0], f1=dias[0], fin=200.0, tms=1000.0, ley=10.0)
               for pid in (1, 2)}
    monkeypatch.setattr(report, 'leer_apilado', lambda **kw: apilado)
    monkeypatch.setattr(report, 'leer_dump', lambda asof: [])
    monkeypatch.setattr(report, '_campaign_recovery_points', lambda label: {})
    monkeypatch.setattr(report.E, 'load_riego', lambda *a: pd.DataFrame({'P01': 10.0}, index=dias))
    monkeypatch.setattr(report.E, 'load_cu_riego', lambda *a: pd.Series(1.0, index=dias))
    monkeypatch.setattr(report.E, 'load_drena_cu', lambda *a: pd.DataFrame({'P01': 2.0}, index=dias))
    raw = {'piles': [dict(label=label, parcela='P01', daily=[]) for label in ('OXIDOS', 'SULFUROS')]}
    runs = {1: dict(ws=dias[2], we=dias[2], caso={'run_id': 1},
                    pads={label: {'res': raw} for label in ('OXIDOS', 'SULFUROS')})}
    return dias, runs


def test_recuperacion_directa_reemplaza_la_curva_de_la_pila(monkeypatch, tmp_path):
    dias, runs = _entorno_directa(monkeypatch)
    directa = pd.Series([5.0, 10.0, np.nan, 20.0], index=dias[1:5])   # hueco el dia 3
    kw = dict(end=dias[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False)
    base = report.construir_doc(runs, **kw)
    doc = report.construir_doc(runs, direct_recovery={('OXIDOS', 1): directa}, **kw)
    ox, su = doc['pads']['OXIDOS']['pilas'][0], doc['pads']['SULFUROS']['pilas'][0]
    # t Cu acumulado = % x apilado (200 t); antes del primer valor 0; hueco = ultimo acumulado
    assert ox['rec'] == pytest.approx([0.0, 10.0, 20.0, 20.0, 40.0])
    assert ox['rec_curve'] == [None, 10.0, 20.0, None, 40.0]
    assert ox['t_rec'] == 40.0 and ox['pct'] == pytest.approx(20.0)
    assert ox['recuperacion_directa'] is True
    # la reconstruccion medida se conserva y las demas pilas no cambian
    assert ox['med'] == base['pads']['OXIDOS']['pilas'][0]['med']
    assert su['rec'] == base['pads']['SULFUROS']['pilas'][0]['rec'] and not su['recuperacion_directa']
    # el libro la usa: Prod = diferencias diarias y Rec Ox deja el hueco en blanco
    ruta = tmp_path / 'directa.xlsx'
    report.escribir_libro(doc, ruta)
    book = load_workbook(ruta)
    prod = [book['Prod Cu Oxidos'].cell(r, 2).value for r in range(5, 10)]
    assert prod == pytest.approx([0.0, 10.0, 10.0, 0.0, 20.0])
    assert book['Rec Ox']['B13'].value is None and book['Rec Ox']['B14'].value is not None


def test_recuperacion_directa_ignora_pila_sin_apilado_o_serie_vacia(monkeypatch, tmp_path):
    dias, runs = _entorno_directa(monkeypatch)
    kw = dict(end=dias[-1], xl=str(tmp_path / 'ausente.xlsx'), verbose=False)
    base = report.construir_doc(runs, **kw)
    doc = report.construir_doc(runs, direct_recovery={
        ('OXIDOS', 1): pd.Series(dtype=float), ('OXIDOS', 9): pd.Series([1.0], index=dias[:1])}, **kw)
    assert doc['pads']['OXIDOS']['pilas'][0]['rec'] == base['pads']['OXIDOS']['pilas'][0]['rec']
    assert not doc['pads']['OXIDOS']['pilas'][0]['recuperacion_directa']


# ── comparador de formato ───────────────────────────────────────────────────

def _comparador():
    sys.path.insert(0, str(ROOT / 'tools'))
    import compare_report_format
    return compare_report_format


def test_libro_generado_cumple_firma_del_oficial(libro):
    comparador = _comparador()
    _, ruta, _ = libro
    firma = comparador.cargar_firma(FIRMA)
    assert [h['nombre'] for h in firma['hojas'] if h['estado'] == 'visible'] == HOJAS_OFICIALES
    diferencias = comparador.comparar(comparador.extraer_firma(ruta), firma)
    errores = [d for d in diferencias if d[0] == 'ERROR']
    assert errores == []


def test_comparador_detecta_hoja_renombrada_grafico_y_codigo_de_salida(libro, tmp_path, capsys):
    comparador = _comparador()
    _, ruta, _ = libro
    malo = tmp_path / 'malo.xlsx'
    book = load_workbook(ruta)
    book['Prod Cu Oxidos'].title = 'Prod Oxidos'
    book['Oxido']._charts.pop()
    book.save(malo)
    codigo = comparador.main([str(malo), '--firma', str(FIRMA)])
    salida = capsys.readouterr().out
    assert codigo == 1
    assert 'hojas faltantes: Prod Cu Oxidos' in salida
    assert 'hojas sobrantes: Prod Oxidos' in salida
    assert 'cantidad de graficos 3 (generado) vs 4 (oficial)' in salida
    assert comparador.main([str(ruta), '--firma', str(FIRMA)]) == 0
    assert comparador.main([str(tmp_path / 'no_existe.xlsx'), '--firma', str(FIRMA)]) == 2


def test_pila_fuera_de_las_32_del_oficial_desplaza_ph_y_total_prod(tmp_path):
    from copy import deepcopy
    doc = oficial_doc(dias=10)
    extra = deepcopy(doc['pads']['OXIDOS']['pilas'][0])
    extra.update(num=33, p='P33')
    doc['pads']['OXIDOS']['pilas'].append(extra)
    ruta = tmp_path / 'extra.xlsx'
    report.escribir_libro(doc, ruta)
    book = load_workbook(ruta)
    prod = book['Prod Cu Oxidos']
    assert [prod.cell(4, c).value for c in (33, 34, 35, 37)] == [32, 33, 'PH', 'Total Prod']
    assert prod['AK5'].value == '=+SUM(B5:AI5)'
    assert book['Rec Ox'].cell(9, 34).value == 33
    assert book['Rec Ox 2'].cell(5, 35).value == 33
    assert book['(Cu) dren Ox'].cell(4, 34).value == 'P33Cu++'
    assert book['(Cu) dren Ox'].cell(4, 35).value == 'PHCu++'
