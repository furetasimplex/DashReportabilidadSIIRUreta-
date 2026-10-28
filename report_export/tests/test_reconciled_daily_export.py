import io
import json
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import Mock
import pandas as pd
import pytest
from openpyxl import load_workbook
from ajuste_reporte.rep_prod_adjuster import _m6_payload_digest
from report_export import reconciled_daily_export as r


@pytest.fixture
def sample():
    dates=pd.date_range('2026-10-05','2026-10-08')
    data=pd.DataFrame([{**{f:float(i+1) for _,f in r.COLUMN_MAP},'Fecha':d,
        'run_id':'00000000-0000-0000-0000-000000000001','caso_id':234,
        'estado_validacion':'VALIDADO','es_activa':True} for i,d in enumerate(dates)])
    for f in ['Campana_apilado','Campana_reclamo_oxidos','Campana_reclamo_sulfuros','Campana_reclamo_camiones']:
        data[f]='Sulfuro'
    data['Ley_CuT_Real']=[1.,2.,3.,4.]
    meta=dict(caso_id=234,modelo_id=2,solver_run_id=567,modelo_codigo='hidrometalurgia_125_v2',estado_solver='success',
              fecha_inicio=dates.min(),fecha_fin=dates.max())
    trace=dict(namespace='DEV_SIIR.hidro.recon_caso',modelo_codigo=meta['modelo_codigo'],caso_id=234,modelo_id=2,
        solver_run_id=567,periodo=['2026-10-05','2026-10-08'],columnas_operacionales=r.FIELDS,
        payload_sha256=_m6_payload_digest(data,sorted(r.FIELDS)))
    meta['totales_json']=json.dumps(trace)
    candidates=data[['Fecha','run_id']].assign(fecha_validacion=pd.Timestamp('2026-10-26'),validation_id=99)
    return data,meta,candidates


def test_template_all47_exact_nulls_dates_mtd_styles_and_mail(sample):
    data,meta,candidates=sample
    identity=r.validate_published(data,meta,data.copy(),candidates)
    data.loc[1,'Movido']=None
    blob=r.export_published_reconciled(data,identity)
    out=load_workbook(io.BytesIO(blob));reference=load_workbook(r.TEMPLATE)
    assert out.sheetnames==['Generador Reporte Diario','Datos para correo']
    ws=out.worksheets[0]
    for col,f in r.COLUMN_MAP:
        for i,row in data.iterrows():
            actual=ws[f'{col}{20+row.Fecha.day}'].value
            assert actual is None if pd.isna(row[f]) else actual==row[f]
    assert ws['C21'].value.day==1 and ws['C51'].value.day==31
    assert ws['D21'].value is None and ws['D29'].value is None
    assert ws['AC5'].value==10.0  # plan del caso 5–8, no del mes entero
    assert ws['AB6'].value==pytest.approx(3.0)  # (1+4+9+16)/(1+2+3+4)
    assert '05-10-2026 a 08-10-2026' in ws['Z3'].value
    assert '234' in ws['AG3'].value
    for sheet in out:
        src=reference[sheet.title]
        assert str(sheet.merged_cells)==str(src.merged_cells)
        assert str(sheet.print_area)==str(src.print_area)
        assert dict(sheet.page_setup)==dict(src.page_setup)
        for row in src:
            for cell in row:assert sheet[cell.coordinate].style_id==cell.style_id
        assert {k:v.width for k,v in sheet.column_dimensions.items()}=={k:v.width for k,v in src.column_dimensions.items()}
        assert {k:v.height for k,v in sheet.row_dimensions.items()}=={k:v.height for k,v in src.row_dimensions.items()}
    mail=' '.join(str(c.value) for row in out.worksheets[1] for c in row if c.value)
    assert '8 de octubre, 2026' in mail and '-329' not in mail and '24 de octubre' not in mail
    assert 'información no disponible' in mail
    with ZipFile(io.BytesIO(blob)) as z,ZipFile(r.TEMPLATE) as original:
        assert z.read('xl/styles.xml')==original.read('xl/styles.xml')


@pytest.mark.parametrize('failure',['hole','duplicate','mixed','trace','hash','view','tie','winner','inactive'])
def test_refuses_unverifiable_publication(sample,failure):
    data,meta,candidates=sample;official=data.copy()
    if failure=='hole':data=data.iloc[:-1]
    if failure=='duplicate':data=pd.concat([data,data.iloc[:1]])
    if failure=='mixed':data.loc[0,'run_id']='00000000-0000-0000-0000-000000000002'
    if failure=='trace':meta['solver_run_id']=999
    if failure=='hash':data.loc[0,'Sal_turno_A']=999
    if failure=='view':official.loc[0,'SRR_TMS_Turno_A']=999
    if failure=='inactive':data.loc[0,'es_activa']=False
    if failure in ('tie','winner'):
        other=candidates.iloc[:1].copy();other['run_id']='00000000-0000-0000-0000-000000000002'
        if failure=='winner':other['validation_id']=100
        candidates=pd.concat([candidates,other])
    with pytest.raises(ValueError):r.validate_published(data,meta,official,candidates)


def test_callback_read_only_branch_without_dates_and_pdf_hidden(monkeypatch):
    from report_export.callbacks import reportabilidad_cb as cb
    from report_export.layouts import reportabilidad_page as page
    from report_export import report_export as repo
    from types import SimpleNamespace
    monkeypatch.setattr(cb,'ctx',SimpleNamespace(triggered_id={'type':'report-export-btn','tipo':'conciliacion'}))
    monkeypatch.setattr(repo,'_get_engine',lambda:Mock())
    identity=dict(caso_id=234,solver_run_id=567,run_id='published-uuid',fecha_inicio=pd.Timestamp('2026-10-05'),fecha_fin=pd.Timestamp('2026-10-08'))
    build=Mock(return_value=(b'xlsx','case.xlsx',identity));monkeypatch.setattr(cb,'build_reconciled_daily_excel',build)
    for method in ('preparar_paquete_datos_conciliados_emision','build_balance_official_report','actualizar_datos_conciliados_report'):
        monkeypatch.setattr(cb,method,lambda *a,**k:pytest.fail('No refrescar datos ni balance'))
    response=cb.exportar_excel([1],None,None,None,234)
    assert '234' in response[1] and 'published-uuid' in response[1]
    build.assert_called_once()
    def ids(component):
        if hasattr(component,'id'):yield component.id
        children=getattr(component,'children',None)
        for child in (children if isinstance(children,list) else [children]):
            if child is not None:yield from ids(child)
    card=page._report_card('Datos Conciliados Reconciliados','Publicados','conciliacion')
    assert {'type':'report-pdf-btn','tipo':'conciliacion'} not in list(ids(card))
    assert 'PDF reconciliado no disponible' in cb.generar_pdf([1],None,None,234)[1]


def test_component_summary_ignores_inherited_totals_and_preserves_shared_summary(sample):
    data,meta,_=sample
    data['Camiones_TMS_total']=9999.0
    data['Total_Ripios_Incluye_Camiones_Real']=8888.0
    original=data.copy(deep=True)
    shared=r.calcular_resumen_mtd(data,meta['fecha_fin'])
    summary=r.calcular_resumen_reconciliado_mtd(data,meta['fecha_inicio'],meta['fecha_fin'])
    assert summary['Rotopala']['real']==20.0
    assert summary['Total Camiones']['real']==20.0
    assert summary['Total Ripios']['real']==40.0
    assert summary['Rotopala']['plan']==20.0
    assert summary['Total Camiones']['plan']==10.0
    assert summary['Total Ripios']['plan']==10.0
    assert summary['Total Camiones']['diferencia']==10.0
    assert summary['Total Camiones']['varianza']==1.0
    assert shared['Total Camiones']['real']==39996.0
    assert shared==r.calcular_resumen_mtd(data,meta['fecha_fin'])
    for name in set(summary)-{'Rotopala','Total Camiones','Total Ripios'}:
        assert summary[name]==shared[name]
    pd.testing.assert_frame_equal(data,original)
    # Filas ajenas al caso no deben entrar, aunque sean del mismo mes.
    extra=data.iloc[:1].copy();extra['Fecha']=pd.Timestamp('2026-10-01')
    assert r.calcular_resumen_reconciliado_mtd(pd.concat([extra,data]),meta['fecha_inicio'],meta['fecha_fin'])==summary


def test_component_summary_missing_is_not_zero_and_zero_plan_has_no_variance(sample):
    data,meta,_=sample
    data.loc[0,'TMS_Rotopala_2_Real']=None
    data['Camiones_TMS_plan']=0.0
    summary=r.calcular_resumen_reconciliado_mtd(data,meta['fecha_inicio'],meta['fecha_fin'])
    assert summary['Rotopala']['real'] is None
    assert summary['Total Ripios']['real'] is None
    assert summary['Total Camiones']['real']==20.0
    assert summary['Total Camiones']['varianza'] is None
