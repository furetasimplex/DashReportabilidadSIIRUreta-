"""Contrato de presentacion compacto, sin cambiar seleccion ni calculos."""
from datetime import date
from unittest.mock import patch
import json
import pandas as pd
from plotly.utils import PlotlyJSONEncoder
from report_export.callbacks import reportabilidad_cb as cb
from report_export.tests.test_balance_interfaz import status

def rendered(value):return json.dumps(value,cls=PlotlyJSONEncoder,ensure_ascii=False)

def test_selector_compacto_busqueda_y_seleccion_conservada():
    rows=pd.DataFrame([
        dict(caso_id=10009,modelo_id=2,nombre_caso='Nombre completo extenso '*20,fecha_inicio=date(2026,9,1),fecha_fin=date(2026,9,7)),
        dict(caso_id=8,modelo_id=1,nombre_caso='Caso hidrometalurgia',fecha_inicio=date(2026,8,22),fecha_fin=date(2026,8,31)),
    ])
    with patch.object(cb,'fetch_recon_balance_official_cases',return_value=rows) as reader:
        options,selected=cb.cargar_casos_oficiales_balance('tab-semanales',8)
    reader.assert_called_once_with()
    assert selected==8
    assert options[0]['value']==10009
    assert options[0]['label'].children=='Caso 10009 · V2 · 01–07 sep 2026'
    assert options[1]['label'].children=='Caso 8 · V1 · 22–31 ago 2026'
    assert rows.iloc[0]['nombre_caso'] in options[0]['search']
    assert '10009' in options[0]['search']

def test_fechas_cruzan_mes_y_ano():
    assert cb._balance_compact_period(date(2026,8,28),date(2026,9,3))=='28 ago–03 sep 2026'
    assert cb._balance_compact_period(date(2025,12,29),date(2026,1,4))=='29 dic 2025–04 ene 2026'
    assert cb._balance_compact_period(date(2026,9,1),date(2026,9,1))=='01 sep 2026'

def test_resumen_mtd_coincidente_y_distinto_con_fechas_accesibles():
    same=rendered(cb._balance_status_content(status()))
    assert 'mismo período operacional' in same
    assert 'title' in same and '01-09-2026 al 07-09-2026' in same
    different=rendered(cb._balance_status_content(status(mtd_fecha_inicio=date(2026,8,1))))
    assert 'mismo período operacional' not in different
    assert '01-08-2026 al 07-09-2026' in different

def test_detalle_cerrado_sin_repetir_aviso_y_con_metadatos_completos():
    raw={'solver_converged':False,'officializable':False,'warning_message':'Advertencia original',
         'solver_math_status':'local_infeasibility_or_solution_not_found','solver_attempt':'strict_official_input'}
    s=status(solver_metadata_json=json.dumps(raw),observacion_solver='Seleccion oficial SQL con observaciones del solver: solver_converged=False; officializable=False. No constituye certificacion matematica.')
    detail=cb._balance_solver_detail(s)
    assert detail.children[1].open is False
    out=rendered(detail)
    assert out.count('Advertencia original')==1
    assert 'Seleccion oficial SQL con observaciones del solver:' not in out
    for value in raw.values():assert str(value) in out
    assert 'La selección oficial SQL no certifica convergencia matemática.' in out
