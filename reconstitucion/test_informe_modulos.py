from io import BytesIO
import base64
import pytest

import pandas as pd
from openpyxl import load_workbook

from reconstitucion import informe_modulos as report


def fixture_result():
    day = pd.Timestamp("2026-09-03")
    ap = pd.DataFrame([
        dict(pad_id=2, campana=42, modulo=101, fecha=day, vol_diario=60.,
             estado="ACTIVO", altura_prom=8.1),
        dict(pad_id=2, campana=42, modulo=102, fecha=day, vol_diario=40.,
             estado="ACTIVO", altura_prom=8.2),
    ])
    st = pd.DataFrame([
        dict(pad_id=2, campana=42, modulo=101, fecha=day, masa_total=600.,
             masa_turno1=350., masa_turno2=250., TMH_dia=1000., vol_dia_total=100.),
        dict(pad_id=2, campana=42, modulo=102, fecha=day, masa_total=400.,
             masa_turno1=240., masa_turno2=160., TMH_dia=1000., vol_dia_total=100.),
    ])
    profile = pd.DataFrame([
        dict(fecha=day, turno="A", tm="TM1", tmh=700., humedad=3.0),
        dict(fecha=day, turno="B", tm="TM1", tmh=300., humedad=5.0),
    ])
    return dict(apilado=ap, shift_table=st, perfil_turnos=profile)


def fixture_quality():
    return pd.DataFrame([
        dict(fecha=pd.Timestamp("2026-09-03"), turno="A", TMS_turno=590.,
             FeT=2., FeS=1., CuT=1.2, CuS=.3, CO3=.5, consumo_H=10.,
             solubilidad=.7, CuFe=.1, beta_clay=.2, origen_stock=10.,
             origen_mina=80., origen_srr=10., malla_100=90., malla_media=65.),
        dict(fecha=pd.Timestamp("2026-09-03"), turno="B", TMS_turno=410.,
             FeT=4., FeS=3., CuT=1.6, CuS=.5, CO3=.7, consumo_H=20.,
             solubilidad=.8, CuFe=.3, beta_clay=.4, origen_stock=20.,
             origen_mina=70., origen_srr=10., malla_100=80., malla_media=55.),
    ])


def test_contract_uses_current_case_allocation_and_module_shift_weights():
    result = report.preparar_modulos_desde_resultado(
        fixture_result(), 2, fixture_quality(), "2026-09-01", "2026-09-07")
    assert list(result.modulo) == [101, 102]
    assert list(result.campana) == [42, 42]
    assert list(result.parcela) == [21, 21]
    assert list(result.TMH) == [600., 400.]
    assert list(result.TMS) == [600., 400.]
    assert list(result.altura_prom) == [8.1, 8.2]
    assert result.loc[0, "CuT"] == (350 * 1.2 + 250 * 1.6) / 600
    assert result.loc[1, "CuT"] == (240 * 1.2 + 160 * 1.6) / 400
    assert result.loc[0, "frac_oxidos"] == (350 * .7 + 250 * .8) / 600
    assert result.loc[1, "frac_sulfuros"] == 1 - (240 * .7 + 160 * .8) / 400
    assert result.loc[0, "cu_fino"] == result.loc[0, "TMS"] * result.loc[0, "CuT"] / 100
    assert result.loc[0, "humedad"] == (350 * 3. + 250 * 5.) / 600


def test_full_template_writer_keeps_valid_modulos_sheet_and_drops_broken_auxiliary_sheets():
    result = report.preparar_modulos_desde_resultado(
        fixture_result(), 2, fixture_quality())
    output = BytesIO()
    report.exportar_desde_dataframe(result, output, pad=2, detalle=True)
    wb = load_workbook(BytesIO(output.getvalue()), data_only=False)
    assert wb.sheetnames == ["MODULOS", "DETALLE"]
    ws = wb["MODULOS"]
    assert ws.max_column == 120  # Full report header A:DP; legacy scratch formulas extended to MB.
    assert [ws.cell(3, c).value for c in (1, 2, 3, 5, 6, 7, 8, 9, 11)] == [
        42, 21, 101, 600., 600., '=IF(S3="","",S3)',
        '=IF(G3="","",1-G3)', 8.1,
        '=IF(OR(F3="",N3=""),"",F3*N3/100)']
    assert ws['AL3'].value == pytest.approx((350 * 3. + 250 * 5.) / 600)
    assert ws['N3'].value == pytest.approx((350 * 1.2 + 250 * 1.6) / 600)
    assert ws['S3'].value == '=IF(OR(O3="",N3="",N3=0),"",O3/N3)'
    assert ws['BK3'].value == '=+SUM(F3:F4)'
    assert ws['BV3'].value == '=IF(OR(SUM(F3:F4)=0,COUNT(N3:N4)=0),"",SUMPRODUCT(N3:N4,F3:F4)/SUM(F3:F4))'
    assert ws['CH3'].value == '=IF(OR(SUM(E3:E4)=0,COUNT(AL3:AL4)=0),"",SUMPRODUCT(AL3:AL4,E3:E4)/SUM(E3:E4))'
    assert ws['DL3'].value == '=IF(D3="","",D3)'  # official fallback only if no explicit date
    assert ws['DO3'].value == '=IF(OR(DM3="",DL3=""),"",DM3-DL3)'
    assert not any(cell.data_type == "f" and "#REF!" in str(cell.value)
                   for sheet in wb for row in sheet for cell in row)
    assert wb["DETALLE"].max_column >= 20


def test_download_identity_cache_and_empty_pad(monkeypatch):
    from dash import Dash
    from reconstitucion import panel
    calls = []
    def quality(pad, **kwargs):
        calls.append(pad)
        return fixture_quality()
    monkeypatch.setattr(panel.dbs, 'get_engine', lambda: object())
    app = Dash(__name__)
    panel.register_callbacks(app, report_quality_loader=quality, report_extra_loader=lambda *args: pd.DataFrame())
    callbacks = {v['callback'].__wrapped__.__name__: v['callback'].__wrapped__
                 for v in app.callback_map.values()}
    case = dict(id=10013, run_id=10145, fecha_inicio='2026-09-01', fecha_fin='2026-09-07')
    res = dict(fixture_result(), caso=case, fuente_modelo={'run_id': 10145})
    token = panel.remember(res)
    enabled = callbacks['estado_informe']
    download = callbacks['descargar_informe']
    assert enabled(None, 10013, [case]) is True
    assert enabled(token, 10013, [case]) is False
    assert download(1, token, 2, 10009, [case])[0] is None
    assert not calls
    result, status = download(1, token, '2', 10013, [case])
    assert result and '10013_run_10145' in result['filename']
    wb = load_workbook(BytesIO(base64.b64decode(result['content'])))
    assert wb['MODULOS']['N3'].value == pytest.approx(8.2 / 600 * 100)
    assert calls == [2]
    assert download(2, token, 2, 10013, [case])[0]
    assert calls == [2]  # cached; no repeated SELECT
    assert download(3, token, 1, 10013, [case])[0]  # header-only OX
    assert calls == [2]
    changed = dict(case, run_id=10146)
    assert enabled(token, 10013, [changed]) is True
    assert download(4, token, 2, 10013, [changed])[0] is None


def test_missing_quality_stays_missing_and_partial_is_not_finish():
    res = fixture_result()
    res['apilado']['vol_acum_final'] = [100., 40.]
    res['apilado']['avance'] = [.6, 1.]
    out = report.preparar_modulos_desde_resultado(res, 2, None)
    assert out.origen_suma.isna().all()
    assert out.CuT.isna().all()
    assert out.completo.tolist() == [False, True]
    assert pd.isna(out.loc[0, 'fecha_fin_carguio'])
    assert out.loc[1, 'fecha_fin_carguio'] == pd.Timestamp('2026-09-03')


def test_oxide_summary_formulas_are_dynamic_by_campaign_and_parcel():
    rows = []
    for campana, parcela, modulo in [(11, 5, 10), (11, 5, 11),
                                     (12, 5, 10), (11, 6, 12)]:
        row = {field: None for field in report.COLUMNAS.values()}
        row.update(campana=campana, parcela=parcela, modulo=modulo,
                   fecha_fin_carguio=pd.Timestamp('2026-09-03'), TMH=100., TMS=90.,
                   altura_prom=8., CuT=1.2, CuS=.3, CO3=.5,
                   origen_stock=10., origen_mina=80., origen_srr=10.,
                   origen_suma=100., malla_100=90., malla_media=65., humedad=3.)
        rows.append(row)
    output = BytesIO()
    report.exportar_desde_dataframe(pd.DataFrame(rows), output, pad=1, detalle=True)
    wb = load_workbook(BytesIO(output.getvalue()), data_only=False)
    ws = wb['MODULOS']
    assert ws['BK3'].value == '=+SUM(F3:F4)'
    assert ws['BV3'].value == '=IF(OR(SUM(F3:F4)=0,COUNT(N3:N4)=0),"",SUMPRODUCT(N3:N4,F3:F4)/SUM(F3:F4))'
    assert ws['BK5'].value == '=IF(COUNT(F5:F5)=1,SUM(F5:F5),"")'  # same parcela number, new campaign
    assert ws['BK6'].value == '=IF(COUNT(F6:F6)=1,SUM(F6:F6),"")'  # next parcela
    assert ws['BJ3'].value == '=IF(B3="","",B3)' and ws['BJ5'].value == '=IF(B5="","",B5)'
    assert ws['A3'].value == 11 and ws['A5'].value == 12 and ws['A6'].value == 11
    assert ws['BK5'].number_format == ws['BK3'].number_format
    assert ws['BV5'].number_format == ws['BV3'].number_format
    assert ws['A7'].value is None and ws['BK7'].value is None
    assert not any(c.data_type == 'f' and '#REF!' in str(c.value)
                   for sh in wb for row in sh for c in row)


def test_missing_sulfide_inputs_keep_official_formulas_without_zero_dates():
    m = report.preparar_modulos_desde_resultado(fixture_result(), 2, None)
    output = BytesIO()
    report.exportar_desde_dataframe(m, output, pad=2, detalle=True)
    ws = load_workbook(BytesIO(output.getvalue()), data_only=False)['MODULOS']
    assert ws['K3'].value == '=IF(OR(F3="",N3=""),"",F3*N3/100)'
    assert ws['S3'].value == '=IF(OR(O3="",N3="",N3=0),"",O3/N3)'
    assert ws['T3'].value == '=IF(S3="","",IF(S3 <0.25,"Sulfuros","mixtos"))'
    assert ws['U3'].value.startswith('=IF(OR(O3="",O3<=0,P3=""),"",IF(P3>0.3,')
    assert ws['BK3'].value == '=+SUM(F3:F4)'
    assert ws['BM3'].value == '=IF(OR(SUM(F3:F4)=0,COUNT(G3:G4)=0),"",SUMPRODUCT(G3:G4,F3:F4)/SUM(F3:F4))'
    assert ws['DL3'].value == '=IF(D3="","",D3)'
    assert ws['A8'].value is None and ws['BK8'].value is None


def test_reposo_explicito_y_fallback_conviven_sin_pisar_la_plantilla():
    data = report.preparar_modulos_desde_resultado(fixture_result(), 2, fixture_quality())
    data['fecha_ini_reposo'] = [pd.Timestamp('2026-09-06'), pd.NaT]
    output = BytesIO()
    report.exportar_desde_dataframe(data, output, pad=2)
    ws = load_workbook(BytesIO(output.getvalue()), data_only=False)['MODULOS']
    assert pd.Timestamp(ws['DL3'].value) == pd.Timestamp('2026-09-06')
    assert ws['DL4'].value == '=IF(D4="","",D4)'


def test_control_mineral_usa_entradas_sulfuro_y_formulas_oxido():
    data = report.preparar_modulos_desde_resultado(fixture_result(), 2, fixture_quality())
    for field, value in {'Calidad01':12., 'Calidad02':34., 'Calidad03':54.,
                         'ACF03':1., 'ACF04':2., 'ACF05':3., 'ACF06':4., 'ACF07':90.}.items():
        data[field] = value
    for pad in (1,2):
        output = BytesIO()
        report.exportar_desde_dataframe(data, output, pad=pad)
        ws = load_workbook(BytesIO(output.getvalue()), data_only=False)['MODULOS']
        if pad == 2:
            assert [ws.cell(3,c).value for c in (57,58,59)] == [12.,34.,54.]
        else:
            assert all(ws.cell(3,c).data_type == 'f' for c in (57,58,59))
            assert 'AY3' in ws['BE3'].value and 'AZ3' in ws['BE3'].value
        assert ws['BH3'].data_type == 'f'
