"""Regresión de coexistencia y transferencia V10; sin SQL ni solver."""
import io
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from openpyxl import load_workbook
from report_export.balance_contract import get_balance_template_path, validate_balance_template_hash
from report_export.balance_service import build_balance_official_report, aggregate_balance_mtd
from report_export.report_export import BalanceReportError, validate_recon_balance_result, fetch_recon_balance_official_case
from report_export.export_to_excel import export_balance_reconciliacion_to_template, validate_balance_output_package
from report_export.tests.test_balance_official_mtd import _flows, _metadata
from report_export.callbacks import reportabilidad_cb as cb

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def inputs():
    frame = _flows(count=125)
    frame['masa_medida'] = [Decimal(k) + Decimal('.123456') for k in range(1,126)]
    frame['masa_reconciliada'] = [Decimal(-k) - Decimal('.234567') for k in range(1,126)]
    # Fino deliberadamente independiente de masa*ley: debe conservarse.
    frame['fino_cu_reconciliado'] = Decimal('4.567891')
    meta = _metadata(10009,10048,date(2026,9,1),date(2026,9,7),model=2)
    meta['solver_metadata_json'] = json.dumps({'solver_converged':False,'officializable':False})
    valid = validate_recon_balance_result(frame,meta,'V2 sintético')
    return build_balance_official_report(10009, fetch_case=lambda _: (valid,meta))


@pytest.fixture(scope='module')
def exported():
    period, accumulated, meta = inputs()
    return period,accumulated,meta,export_balance_reconciliacion_to_template(period,accumulated,meta)


def test_templates_versionados():
    assert get_balance_template_path(1) != get_balance_template_path(2)
    for model in (1,2):validate_balance_template_hash(get_balance_template_path(model),model)
    with pytest.raises(ValueError,match='no dispone'):get_balance_template_path(99)
    with pytest.raises(ValueError,match='version validada'):
        validate_balance_template_hash(get_balance_template_path(1),2)


def test_transferencia_125_periodo_mtd_medidos_tolerancias(exported):
    period, accumulated, meta, data = exported
    wb=load_workbook(io.BytesIO(data),data_only=False)
    assert len(wb.sheetnames)==10
    for k in range(1,126):
        source=period.loc[f'F{k}']; row=k+2; analysis=k+3
        assert wb['Datos Reconciliados'].cell(row,2).value==f'F{k}'
        for col,field in [(4,'masa_reconciliada'),(5,'ley_cu_reconciliada'),(6,'fino_cu_reconciliado')]:
            assert Decimal(str(wb['Datos Reconciliados'].cell(row,col).value))==source[field]
        for col,field in [(7,'masa_reconciliada_acumulada'),(9,'fino_cu_reconciliado_acumulado')]:
            assert Decimal(str(wb['Datos Reconciliados'].cell(row,col).value))==accumulated.loc[f'F{k}',field]
        for col,field in [(4,'tolerancia_masa'),(5,'tolerancia_ley'),(6,'masa_medida'),(10,'ley_cu_medida'),(14,'fino_cu_medido')]:
            assert Decimal(str(wb['Análisis Variación-Tolerancias'].cell(analysis,col).value))==source[field]
    assert wb['Datos Reconciliados']['L3'].value==7
    assert wb['Datos Reconciliados']['L4'].value==7
    assert wb['Análisis Variación-Tolerancias'].auto_filter.ref=='B3:Q128'
    template=load_workbook(get_balance_template_path(2),data_only=False)
    for sheet,coordinates in [('Resumen',['F10','C40','C41','C42']),
                              ('Datos Reconciliados',[f'{col}{row}' for row in range(8,18) for col in ('K','L')])]:
        for coordinate in coordinates:
            assert wb[sheet][coordinate].value==template[sheet][coordinate].value
            assert wb[sheet][coordinate]._style==template[sheet][coordinate]._style
    assert meta['solver_run_id']==10048 and 'observaciones' in meta['observacion_solver']


def test_formulas_objetos_y_fechas_preservados(exported):
    output=exported[3]
    with ZipFile(get_balance_template_path(2)) as a, ZipFile(io.BytesIO(output)) as b:
        assert set(a.namelist())==set(b.namelist())
        count=0
        for name in a.namelist():
            if name.startswith('xl/worksheets/') and name.endswith('.xml'):
                def formulas(raw):
                    root=ET.fromstring(raw)
                    return {c.attrib['r']:ET.tostring(c.find('m:f',NS)) for c in root.findall('.//m:c',NS) if c.find('m:f',NS) is not None}
                assert formulas(a.read(name))==formulas(b.read(name))
                count+=len(formulas(a.read(name)))
            elif name.startswith('xl/media/') or name.endswith('.rels') or name.startswith('xl/drawings/') and name not in [f'xl/drawings/drawing{k}.xml' for k in (1,2,3)]:
                assert a.read(name)==b.read(name)
        assert count==3113
    validate_balance_output_package(output,2)
    wb=load_workbook(io.BytesIO(output),data_only=False)
    for ws in wb:
        for row in ws:
            for cell in row:
                if isinstance(cell.value,str) and not cell.value.startswith('='):
                    assert 'Agosto' not in cell.value
    assert wb.calculation.fullCalcOnLoad and wb.calculation.forceFullCalc


@pytest.mark.parametrize('kind',['missing','duplicate','nan','inf','wrong_model','wrong_case','changed_run'])
def test_integridad_resultado(kind):
    frame=_flows(count=125);meta=_metadata(10009,10048,date(2026,9,1),date(2026,9,7),model=2)
    if kind=='missing':frame=frame.iloc[:-1]
    if kind=='duplicate':frame.loc[124,'codigo_flujo']='F124'
    if kind=='nan':frame.loc[124,'masa_reconciliada']=None
    if kind=='inf':frame.loc[124,'fino_cu_reconciliado']=float('inf')
    if kind=='wrong_model':frame['flujo_modelo_coherente']=0
    if kind=='wrong_case':meta['run_caso_id']=999
    if kind=='changed_run':frame['resultado_run_id']=10099
    with pytest.raises(BalanceReportError):validate_recon_balance_result(frame,meta,'prueba')


def test_mtd_no_mezcla_modelos_y_masa_cero():
    p,a,m=inputs()
    with pytest.raises(BalanceReportError,match='mezclar modelos'):
        aggregate_balance_mtd([{'metadata':m,'flows':p},{'metadata':dict(m,modelo_id=1),'flows':p}])
    p=p.copy();p.loc['F125','masa_reconciliada']=Decimal(0)
    out=aggregate_balance_mtd([{'metadata':m,'flows':p}])
    assert pd.isna(out.loc['F125','ley_cu_reconciliada_acumulada'])
    assert out.loc['F125','fino_cu_reconciliado_acumulado']==Decimal('4.567891')


def test_sql_recupera_oficial_y_valida_catalogo():
    frame=_flows(count=125);frame['flujo_modelo_coherente']=1;frame['resultado_caso_coherente']=1;frame['resultado_run_id']=10048
    meta=_metadata(10009,10048,date(2026,9,1),date(2026,9,7),model=2)
    meta.update(run_caso_id=10009,solver_metadata_json='{"solver_converged":false,"officializable":false}')
    engine=MagicMock()
    with patch('report_export.report_export._get_engine',return_value=engine),patch('report_export.report_export.pd.read_sql_query',side_effect=[pd.DataFrame([{'caso_id':10009}]),pd.DataFrame([meta]),frame]) as reader:
        result,metadata=fetch_recon_balance_official_case(10009)
    assert list(result.index)==[f'F{k}' for k in range(1,126)]
    sql=' '.join(str(call.args[0]) for call in reader.call_args_list)
    assert 'co.solver_run_id' in sql and 'fm.id = rf.flujo_modelo_id' in sql
    assert 'MAX(' not in sql and 'recon_caso_flujo_input' not in sql
    assert reader.call_args_list[-1].kwargs['coerce_float'] is False


def test_callback_descarga_v2_y_observacion_sin_bloqueo():
    period,accumulated,meta=inputs()
    with patch.object(cb,'ctx',SimpleNamespace(triggered_id={'type':'report-export-btn','tipo':'balance'})),patch.object(cb,'build_balance_official_report',return_value=(period,accumulated,meta)),patch.object(cb,'export_balance_reconciliacion_to_template',return_value=b'xlsx') as writer:
        result=cb.exportar_excel([1],'2026-01-01','2026-01-31','mes',10009)
    assert writer.call_args.args[3]==get_balance_template_path(2)
    assert 'V2_20260901_20260907_Caso10009_Run10048' in str(result[0])
    assert 'observaciones del solver' in result[1]
    with patch.object(cb,'fetch_recon_balance_official_cases',return_value=pd.DataFrame([meta])):
        options,selected=cb.cargar_casos_oficiales_balance('tab-semanales',10009)
    assert selected==10009 and options[0]['value']==10009


def test_xml_rechaza_nuevas_celdas_fuera_de_orden(exported):
    raw=exported[3]
    with ZipFile(io.BytesIO(raw)) as original:
        files={name:original.read(name) for name in original.namelist()}
    import re
    sheet=files['xl/worksheets/sheet1.xml']
    m=re.search(rb'<c\b[^>]*\br="E11"[^>]*>.*?</c>',sheet)
    assert m
    cell=m.group()
    sheet=sheet.replace(cell,b'')
    sheet=re.sub(rb'(<row\b[^>]*\br="11"[^>]*>)(.*?)(</row>)',lambda m:m[1]+m[2]+cell+m[3],sheet,flags=re.DOTALL)
    files['xl/worksheets/sheet1.xml']=sheet
    out=io.BytesIO()
    with ZipFile(out,'w') as z:
        for name,content in files.items():z.writestr(name,content)
    with pytest.raises(BalanceReportError,match='fuera de orden'):validate_balance_output_package(out.getvalue(),2)
