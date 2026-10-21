"""Cambios de presentacion y disponibilidad PDF, sin SQL ni solver."""
import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
import pandas as pd
import pytest
from dash import no_update
from plotly.utils import PlotlyJSONEncoder
from report_export.callbacks import reportabilidad_cb as cb
from report_export.layouts import reportabilidad_page as page


def status(**overrides):
    result=dict(caso_id=234,nombre_caso='Caso dinámico',fecha_inicio=date(2026,9,1),fecha_fin=date(2026,9,7),
                solver_run_id=567,estado_run='success',modelo_id=2,mtd_disponible=True,
                mtd_fecha_inicio=date(2026,9,1),mtd_fecha_fin=date(2026,9,7),mtd_casos=[234],
                observacion_solver='Advertencia original',solver_metadata_json=json.dumps({
                    'solver_converged':False,'officializable':False,'warning_message':'Detalle original de prueba'}))
    return dict(result,**overrides)


def text(component):return json.dumps(component,cls=PlotlyJSONEncoder,ensure_ascii=False)


def test_descripcion_y_datos_dinamicos():
    import inspect
    assert 'Reporte de Balance de Masa de Planta Hidrometalúrgica, correspondiente al caso oficial y período seleccionado.' in inspect.getsource(page.layout)
    rendered=text(cb._balance_status_content(status()))
    for value in ['Caso 234','567','success','01-09-2026','07-09-2026','Período acumulado','Casos MTD','Disponible']:
        assert value in rendered
    assert 'Corrida oficial con observaciones del solver' in rendered
    assert 'Ver detalle técnico' in rendered and 'Details' in rendered and 'Summary' in rendered
    assert 'Detalle original de prueba' in rendered
    assert 'solver_converged' in rendered and 'officializable' in rendered


def test_sin_metadata_no_false_ni_advertencia():
    rendered=text(cb._balance_status_content(status(observacion_solver='',solver_metadata_json=None)))
    assert 'No disponibles; no equivale a False.' in rendered
    assert 'Corrida oficial con observaciones' not in rendered
    assert 'No informado' in rendered


def test_metadata_sin_observaciones():
    rendered=text(cb._balance_status_content(status(observacion_solver='',solver_metadata_json='{"solver_converged":true,"officializable":true}')))
    assert 'Corrida oficial con observaciones' not in rendered
    assert 'True' in rendered


def test_advertencia_disponible_sin_flags():
    rendered=text(cb._balance_status_content(status(observacion_solver='',solver_metadata_json='{"has_solver_warning":true,"warning_message":"Aviso conservado"}')))
    assert 'Aviso conservado' in rendered and 'Corrida oficial con observaciones' in rendered


@pytest.mark.parametrize('context,selected,disabled',[
    ({'caso_id':234,'modelo_id':2},234,True),
    ({'caso_id':8,'modelo_id':1},8,False),
    ({'caso_id':8,'modelo_id':1},234,True),
    (None,234,True),
])
def test_pdf_disponibilidad_y_respuesta_obsoleta(context,selected,disabled):
    actual,note=cb.actualizar_disponibilidad_pdf_balance(context,selected)
    assert actual is disabled
    if context and context.get('modelo_id')==2:assert 'Utilice Exportar Excel' in note


def test_estado_no_bloquea_excel_y_entrega_contexto():
    with patch.object(cb,'get_balance_case_status',return_value=status()):
        card,disabled,context=cb.actualizar_estado_balance(234)
    assert not disabled and context=={'caso_id':234,'modelo_id':2}


def test_pdf_v2_bloqueado_en_backend_antes_de_generar():
    with patch.object(cb,'ctx',SimpleNamespace(triggered_id={'type':'report-pdf-btn','tipo':'balance'})),patch.object(cb,'fetch_balance_case_model',return_value=2),patch.object(cb,'fetch_report_data') as reader,patch.object(cb,'generar_pdf_datos_conciliados') as generator:
        out=cb.generar_pdf([1],'2026-09-01','2026-09-07',234)
    assert out[0] is no_update and 'PDF no disponible para el modelo 2' in out[1]
    reader.assert_not_called();generator.assert_not_called()


def test_pdf_v1_continua_hacia_ruta_historica():
    with patch.object(cb,'ctx',SimpleNamespace(triggered_id={'type':'report-pdf-btn','tipo':'balance'})),patch.object(cb,'fetch_balance_case_model',return_value=1),patch.object(cb,'fetch_report_data',return_value=pd.DataFrame({'Fecha':[]})) as reader:
        out=cb.generar_pdf([1],'2026-08-22','2026-08-31',8)
    reader.assert_called_once_with(end_date=date(2026,8,31))
    assert out[1]=='Sin datos para generar PDF.'


def test_pdf_otro_reporte_no_consulta_modelo_balance():
    with patch.object(cb,'ctx',SimpleNamespace(triggered_id={'type':'report-pdf-btn','tipo':'conciliacion'})),patch.object(cb,'fetch_balance_case_model') as model,patch.object(cb,'fetch_report_data',return_value=pd.DataFrame({'Fecha':[]})):
        cb.generar_pdf([1],'2026-08-22','2026-08-31')
    model.assert_not_called()
