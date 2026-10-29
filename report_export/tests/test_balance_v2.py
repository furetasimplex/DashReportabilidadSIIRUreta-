"""Regresión de coexistencia y transferencia V10; sin SQL ni solver."""
import io
import json
import re
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
        # Nodo General: se retiraron solo las 26 formulas TMS de G43:G68.
        assert count==3089
    validate_balance_output_package(output,2)
    wb=load_workbook(io.BytesIO(output),data_only=False)
    for ws in wb:
        for row in ws:
            for cell in row:
                if isinstance(cell.value,str) and not cell.value.startswith('='):
                    assert 'Agosto' not in cell.value
    assert wb.calculation.fullCalcOnLoad and wb.calculation.forceFullCalc


def test_modelo_completo_nodo_general_solo_tmf_y_esquema_nativo(exported):
    """La fuente basal aplica el formato en cada exportacion sin tocar G global."""
    wb = load_workbook(io.BytesIO(exported[3]), data_only=False)
    ws = wb['Modelo Completo']
    assert ws['E42'].value is None
    assert ws['F42'].value == 'Nodo General'
    assert ws['G42'].value is None and ws['H42'].value == 'tmf'
    assert ws['F43'].value == 'Entrada' and ws['G43'].value == 25
    assert ws['G58'].value == 101 and ws['G59'].value == 104
    assert ws['H43'].value == '=SUMIFS($Q$16:$Q$35,$N$16:$N$35,G43)'
    assert ws['H68'].value == '=H46-H49-H67'
    assert all(ws.cell(r, 7).data_type != 'f' for r in range(42, 69))
    # Las columnas de tonelaje de periodo/acumulado de la tabla principal siguen.
    assert ws['P15'].value == 'Tonelaje  [tms]'
    assert ws['R15'].value == 'Tonelaje  [tms]'
    assert ws['P16'].data_type == ws['R16'].data_type == 'f'
    with ZipFile(io.BytesIO(exported[3])) as archive:
        drawing = ET.fromstring(archive.read('xl/drawings/drawing8.xml'))
        ns = {'d': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'}
        pictures = drawing.findall('.//d:pic', ns)
        assert len(drawing) == 9
        assert len(pictures) == 1
        assert len(drawing.findall('.//d:sp', ns)) == 2
        assert len(drawing.findall('.//d:cxnSp', ns)) == 6
        assert 'xl/media/modelo_hidro_m6.png' not in archive.namelist()
        with ZipFile(get_balance_template_path(2)) as template:
            for part in ('xl/drawings/drawing8.xml', 'xl/drawings/_rels/drawing8.xml.rels'):
                assert archive.read(part) == template.read(part)
        for coordinate,value in {'E21':25,'F21':29,'G21':42,'I25':111,'I31':112,'G38':'Inventarios'}.items():
            assert ws[coordinate].value == value
        # Excel usa sheetId, que no coincide necesariamente con el numero de parte.
        book = ET.fromstring(archive.read('xl/workbook.xml'))
        sid = next(s.attrib['sheetId'] for s in book.find('m:sheets', NS)
                   if s.attrib['name'] == 'Modelo Completo')
        current = None
        for cell in ET.fromstring(archive.read('xl/calcChain.xml')):
            current = cell.attrib.get('i', current)
            assert not (current == sid and cell.attrib['r'] in
                        {f'G{r}' for r in range(43, 69)})


def test_rechaza_desplazamiento_de_objetos_nativos(exported):
    output = io.BytesIO()
    with ZipFile(io.BytesIO(exported[3])) as source, ZipFile(output,'w') as target:
        for info in source.infolist():
            raw = source.read(info.filename)
            if info.filename == 'xl/drawings/drawing8.xml':
                raw = re.sub(rb'<xdr:col>\d+</xdr:col>', b'<xdr:col>99</xdr:col>', raw, count=1)
                assert raw != source.read(info.filename)
            target.writestr(info,raw)
    with pytest.raises(BalanceReportError, match='nueve objetos nativos'):
        validate_balance_output_package(output.getvalue(),2)


@pytest.mark.parametrize('loss116,loss117', [(0, 0), (0, Decimal('21557.506216')), (7, Decimal('123.456789'))])
def test_humedad_dinamica_nuevos_periodos(loss116, loss117):
    period, accumulated, meta = inputs()
    period = period.copy()
    for code, mass in [('F116', loss116), ('F117', loss117)]:
        period.loc[code, 'masa_reconciliada'] = Decimal(str(mass))
        period.loc[code, 'fino_cu_reconciliado'] = Decimal(0)
    meta = dict(meta, caso_id=99991, solver_run_id=99992, run_id=99992,
                fecha_inicio=date(2026,11,1), fecha_fin=date(2026,11,7),
                fecha_inicio_acumulado=date(2026,11,1), fecha_fin_acumulado=date(2026,11,7))
    out = export_balance_reconciliacion_to_template(period, accumulated, meta)
    wb = load_workbook(io.BytesIO(out), data_only=False)
    ws = wb['Informe Hidrometalurgia']
    assert ws['C40'].value == 'F116, F117' and ws['C41'].value == 'F122'
    for col, source in [('E','D'), ('F','F')]:
        assert ws[f'{col}40'].value == f"='Datos Reconciliados'!{source}118+'Datos Reconciliados'!{source}119"
        assert ws[f'{col}42'].value == f'=SUM({col}31:{col}41)'
        assert ws[f'{col}61'].value == f'=SUM({col}46:{col}60)'
        assert ws[f'{col}64'].value == f'={col}27-{col}42-{col}61'
        assert ws[f'{col}65'].value == f'={col}64/{col}27'
    assert Decimal(str(wb['Datos Reconciliados']['D118'].value)) == Decimal(str(loss116))
    assert Decimal(str(wb['Datos Reconciliados']['D119'].value)) == Decimal(str(loss117))
    for target, source in {'E32':'E68','E33':'E72','E34':'E75','E36':'E77','E37':'E80','E38':'E81'}.items():
        assert wb['Resumen'][target].value == f"='Informe Hidrometalurgia'!{source}"
    assert wb['Modelo Completo']['H51'].data_type == 'f'
    assert wb['Modelo Completo']['E43'].fill.fgColor.rgb == 'FFFFFFFF'


@pytest.mark.parametrize('kind', ['wrong_source', 'duplicate', 'summary', 'flow_order'])
def test_humedad_rechaza_dependencias_incorrectas(kind):
    from report_export.export_to_excel import _balance_validate_template_contract
    wb = load_workbook(get_balance_template_path(2), data_only=False)
    if kind == 'wrong_source':
        wb['Informe Hidrometalurgia']['E40'] = "='Datos Reconciliados'!D117+'Datos Reconciliados'!D118"
    elif kind == 'duplicate':
        wb['Informe Hidrometalurgia']['C39'] = 'F116, F117'
    elif kind == 'summary':
        wb['Resumen']['E32'] = "='Informe Hidrometalurgia'!E67"
    else:
        wb['Datos Reconciliados']['B118'], wb['Datos Reconciliados']['B119'] = 'F117', 'F116'
    with pytest.raises(BalanceReportError):
        _balance_validate_template_contract(wb,2)


def test_nodo_general_conserva_sumifs_compartidas(tmp_path):
    """Excel puede compactar H50:H65; el empaquetador conserva ese XML."""
    from report_export.export_to_excel import _balance_cell_xml
    template = tmp_path / 'template_con_formulas_compartidas.xlsx'
    shared_cells = {}
    with ZipFile(get_balance_template_path(2)) as source, ZipFile(template,'w') as target:
        for info in source.infolist():
            raw = source.read(info.filename)
            if info.filename == 'xl/worksheets/sheet10.xml':
                for row in range(50,66):
                    coord = f'H{row}'
                    old = _balance_cell_xml(raw,coord)
                    if row == 50:
                        new = old.replace(b'<f>',b'<f t="shared" ref="H50:H65" si="0">',1)
                    else:
                        new = re.sub(rb'<f>.*?</f>',b'<f t="shared" si="0"/>',old)
                    assert new != old
                    raw = raw.replace(old,new,1)
                    # El exportador elimina caches antiguos, conserva la formula compartida.
                    shared_cells[coord] = re.sub(rb'<v\b[^>]*(?:/>|>.*?</v>)',b'',new)
            target.writestr(info,raw)
    period, accumulated, meta = inputs()
    with patch('report_export.export_to_excel.validate_balance_template_hash', return_value='fixture_compartidas'):
        out = export_balance_reconciliacion_to_template(period,accumulated,meta,str(template))
    with ZipFile(io.BytesIO(out)) as result:
        raw = result.read('xl/worksheets/sheet10.xml')
        for coord,cell in shared_cells.items():
            assert _balance_cell_xml(raw,coord) == cell
    wb = load_workbook(io.BytesIO(out),data_only=False)
    for row in range(50,66):
        assert wb['Modelo Completo'][f'H{row}'].value == f'=SUMIFS($Q$16:$Q$36,$N$16:$N$36,G{row})'


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
