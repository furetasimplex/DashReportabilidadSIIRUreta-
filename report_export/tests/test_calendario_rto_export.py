"""Calendario solicitado vs. cierre operacional, con SQL simulado."""
import io
import json
import re
import time
from datetime import date, datetime

import pandas as pd
import pytest
from openpyxl import load_workbook

from report_export import report_export as repo
from report_export.tests.test_paquete_reporte_turno import Harness, callback_prefix


class CalendarioHarness(Harness):
    def refresh(self, **kw):
        super().refresh(**kw)
        return dict(fecha_corte_operacional=date(2026, 9, 15),
                    fin_sql_exclusivo=date(2026, 9, 16))

    def fetch(self, name, **kw):
        super().fetch(name, **kw)
        fechas = pd.date_range(kw['start_date'], date(2026, 9, 15))
        if name == 'fetch_reporte_turno_cache_emision':
            assert kw['end_date'] == date(2026, 9, 16)
            return pd.DataFrame([
                dict(Fecha=f, Turno=t, Material='Sulfuro', Apilado_TMS_Real=100., CuT_Real=.5)
                for f in fechas for t in ('A', 'B')])
        if name == 'fetch_generador_reporte_diario_emision':
            # Incluye una fila vieja fuera del cierre: jamás exportar sus reales.
            return pd.DataFrame([
                dict(Fecha=f, Apilado_TMS_Real_Dia=200., CuT_Real_Dia=.5,
                     Apilado_TMS_Plan=300.)
                for f in list(fechas) + [pd.Timestamp('2026-09-17')]])
        if name == 'fetch_trazabilidad_analitos_report':
            return pd.DataFrame([
                dict(Fecha=f, Turno=t, TM_Destino=tm, Analito='CuT', Valor_Final=.5,
                     Fuente_Base=tm, Apilado_TMS_Real=100., Fuente_Tecnica='LAB',
                     Resolucion='DIRECTO', Fecha_Origen=f, Turno_Origen=t, TM_Origen=tm,
                     Representatividad_Quimica=1., Representatividad_Fisica=1.)
                for f in fechas for t in ('A', 'B') for tm in ('TM1', 'TM2')])
        return pd.DataFrame()


@pytest.mark.parametrize('inicio,fin', [(1, 30), (4, 23)])
def test_callback_excel_calendario_completo_sin_reales_ficticios(inicio, fin, tmp_path):
    h = CalendarioHarness()
    capturado = {}

    def construir(**kw):
        assert not h.active and not h.lock
        capturado.update(kw)
        repo.export_reporte_turno_estilo_leyes_finos(**kw)

    env = dict(time=time, io=io, ini_d=date(2026, 9, inicio), fin_d=date(2026, 9, fin),
               preparar_paquete_reporte_turno_emision=repo.preparar_paquete_reporte_turno_emision,
               export_reporte_turno_estilo_leyes_finos=construir)
    exec(callback_prefix('exportar_excel'), env)
    with h.patched():
        env['run']()
    assert h.events[-1] == 'COMMIT'
    esperado = set(pd.date_range(env['ini_d'], env['fin_d']))
    for key in ('df', 'df_generador', 'df_generador_resumen'):
        df = capturado[key]
        if key != 'df_generador_resumen':
            assert set(df.Fecha) == esperado
        posterior = df[df.Fecha > pd.Timestamp('2026-09-15')]
        assert not posterior.empty
        assert posterior.filter(like='Real').isna().all().all()
    turno = capturado['df']
    assert all(turnos == {'A', 'B'} for turnos in turno.groupby('Fecha').Turno.apply(set))
    assert turno.loc[turno.Fecha <= '2026-09-15', 'Apilado_TMS_Real'].eq(100).all()
    diario = capturado['df_generador']
    assert diario.loc[diario.Fecha == '2026-09-17', 'Apilado_TMS_Plan'].iloc[0] == 300
    wb = load_workbook(io.BytesIO(capturado['output'].getvalue()), data_only=True)
    for sheet in ('Reporte por Turno', 'Generador Reporte'):
        ws = wb[sheet]
        fechas_excel = {pd.Timestamp(c.value) if isinstance(c.value, datetime)
                        else pd.to_datetime(c.value, format='%d-%m-%Y')
                        for row in ws for c in row
                        if isinstance(c.value, datetime) or
                        (isinstance(c.value, str) and re.fullmatch(r'\d{2}-\d{2}-\d{4}', c.value))}
        assert fechas_excel == esperado
    ws = wb['Reporte por Turno']
    posteriores = [r for r in range(23, ws.max_row + 1)
                   if isinstance(ws.cell(r, 3).value, str)
                   and re.fullmatch(r'\d{2}-\d{2}-\d{4}', ws.cell(r, 3).value)
                   and pd.to_datetime(ws.cell(r, 3).value, format='%d-%m-%Y').date() > date(2026, 9, 15)]
    assert len(posteriores) == fin - 15
    for r in posteriores:
        # Fecha C, Material D, Turno E, TMS Real F, CuT Real G.
        assert all(ws.cell(fila, col).value in (None, 0)
                   for fila in (r, r + 1) for col in (6, 7))
        assert ws.cell(r, 4).value is None
    assert ws.cell(23, 4).value == 'Sulfuro'
    assert all(ws.cell(23 + 2 * dia, 4).value == 'Sulfuro'
               for dia in range(16 - inicio))
    diario_ws = wb['Generador Reporte']
    fila_17 = next(c.row for row in diario_ws for c in row
                   if isinstance(c.value, datetime) and c.value.date() == date(2026, 9, 17))
    # Fixture mínimo: Fecha C, Campaña D, Material E, TMS Real F, Plan G.
    assert diario_ws.cell(fila_17, 7).value == 300
    assert diario_ws.cell(fila_17, 6).value is None
    assert not [(s.title, c.coordinate, c.value) for s in wb for row in s for c in row
                if isinstance(c.value, str) and c.value.strip().lower() in {'nan', 'none', 'nat', '<na>'}]
    (tmp_path / 'Analisis_TM_simulado.xlsx').write_bytes(capturado['output'].getvalue())
    (tmp_path / 'lectura_xlsx.json').write_text(json.dumps({
        'fecha_minima': str(min(fechas_excel).date()),
        'fecha_maxima': str(max(fechas_excel).date()),
        'dias_post_corte': len(posteriores), 'literales_nan_none_nat': 0,
        'material_post_corte': 'vacio', 'reales_post_corte': 'vacios',
        'plan_diario_2026_09_17': 300,
    }, indent=2), encoding='utf-8')


@pytest.mark.parametrize('faltante', [None, float('nan'), pd.NaT, pd.NA, 'NAN', 'nan', 'None', 'NaT'])
def test_faltantes_textuales_y_numericos_vacios_en_xlsx(faltante):
    df = pd.DataFrame(dict(Fecha=[pd.Timestamp('2026-09-16')], Turno=['A'],
                           Material=[faltante], Campania=[faltante], Modulo=[faltante],
                           Avance=[faltante], Fuente_Info_Quimica=[faltante],
                           Fuente_Info_Fisica=[faltante],
                           Malla_Menos_1_2_Plan_Semanal=[faltante]))
    antes = df.copy(deep=True)
    output = io.BytesIO()
    repo.export_reporte_turno_estilo_leyes_finos(df, output)
    pd.testing.assert_frame_equal(df, antes)
    ws = load_workbook(io.BytesIO(output.getvalue()), data_only=True).active
    assert all(ws.cell(23, c).value is None for c in (4, 5, 6, 7, 9, 10, 11))


def test_encabezado_srr_periodo_solicitado_sin_inventar_reconstruccion():
    from report_export.tests.test_reconst_mod_srr import sources
    srr, turno = sources()
    srr['Fecha'] = pd.Timestamp('2026-09-15')
    srr = srr.iloc[:2].copy()
    turno = turno.iloc[:2].copy()
    turno['Fecha'] = pd.Timestamp('2026-09-15')
    output = io.BytesIO()
    repo.export_reporte_turno_estilo_leyes_finos(
        turno, output, df_reconst_srr=srr,
        periodo_inicio=date(2026, 9, 1), periodo_fin=date(2026, 9, 30))
    ws = load_workbook(io.BytesIO(output.getvalue()), data_only=True)['Reconst Mod SRR']
    assert ws['C4'].value == 'Período: 01-09-2026 al 30-09-2026'
    fechas = [c.value for row in ws for c in row if isinstance(c.value, datetime)]
    assert fechas == [datetime(2026, 9, 15)]


def test_completar_no_muta_fuente_ni_rellena_huecos_operacionales():
    df = pd.DataFrame(dict(Fecha=[pd.Timestamp('2026-09-15')], Turno=['A'],
                           Apilado_TMS_Real=[0.]))
    antes = df.copy(deep=True)
    resultado = repo._completar_calendario_rto(
        df, date(2026, 9, 1), date(2026, 9, 30), date(2026, 9, 15), por_turno=True)
    pd.testing.assert_frame_equal(df, antes)
    assert len(resultado) == 31
    assert resultado.loc[0, 'Apilado_TMS_Real'] == 0
