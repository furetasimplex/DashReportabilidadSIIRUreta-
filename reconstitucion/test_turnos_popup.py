from pathlib import Path
import importlib
import sys
import types

import pandas as pd

ACTIVE=Path(__file__).resolve().parent
from . import panel
from . import presentacion as pres


def fixture():
    day=pd.Timestamp('2026-10-01')
    timeline=pd.DataFrame([
        dict(pad_id=2,campana=12,modulo=5,fecha=day,start=day+pd.Timedelta(hours=8),end=day+pd.Timedelta(hours=14),mass_h=400,mass_dry=320,origen='totalizadores_TMH_validados',resolucion='perfil_10s'),
        dict(pad_id=2,campana=12,modulo=6,fecha=day,start=day+pd.Timedelta(hours=14),end=day+pd.Timedelta(hours=20),mass_h=300,mass_dry=240,origen='totalizadores_TMH_validados',resolucion='perfil_10s'),
    ])
    shift=pd.DataFrame([
        dict(pad_id=2,campana=12,modulo=5,fecha=day,vol_diario=1000,masa_total=320,masa_turno1=200,masa_turno2=120,boundary_medida=False,frontera_tipo='distribuida_del_caso'),
        dict(pad_id=2,campana=12,modulo=6,fecha=day,vol_diario=800,masa_total=240,masa_turno1=150,masa_turno2=90,boundary_medida=False,frontera_tipo='distribuida_del_caso'),
    ])
    ap=pd.DataFrame([
        dict(id=81,pad_id=2,campana=12,modulo=5,fecha=day,altura_prom=8.2,grado_prom=0.64,modulo_id=5,campana_id=12,vol_total_est=15000,vol_diario=1000,vol_acum_final=14900,avance=0.9),
        dict(id=82,pad_id=2,campana=12,modulo=6,fecha=day,altura_prom=8.4,grado_prom=0.61,modulo_id=6,campana_id=12,vol_total_est=12000,vol_diario=800,vol_acum_final=300,avance=0.2),
    ])
    profile=pd.DataFrame([dict(fecha=day,turno='A',tm='TM1',tmh=210,humedad=8.0,fuente='PI'),dict(fecha=day,turno='B',tm='TM2',tmh=140,humedad=8.2,fuente='PI')])
    return dict(module_timeline=timeline,shift_table=shift,apilado=ap,perfil_turnos=profile,horas_turnos=pd.DataFrame([dict(fecha=day,H_op=10.5)]))


def walk(node):
    out=[node]
    kids=getattr(node,'children',None)
    if isinstance(kids,(list,tuple)):
        for child in kids: out+=walk(child)
    elif kids is not None and not isinstance(kids,str): out+=walk(kids)
    return out


def test_original_two_lane_contract_and_reconstructed_clock():
    assert Path(panel.e.__file__).resolve()==ACTIVE/'engine.py'
    fig=panel.fig_gantt(fixture())
    assert len(fig.data)==1 and fig.data[0].type=='bar'
    assert fig.data[0].name=='Reconstituido'
    assert list(fig.data[0].y)==['P2 / C12 / M5','P2 / C12 / M6']
    assert fig.data[0].marker.color==panel.C['shift2']
    assert all(shape.line.color==panel.C['accent'] and shape.line.dash=='dot' for shape in fig.layout.shapes)
    assert fig.layout.xaxis.type=='date' and fig.layout.xaxis.tickformat=='%d-%m'
    assert 'Click: detalle' in fig.data[0].hovertemplate


def test_measurements_survive_empty_timeline_and_ignore_zero_rows():
    res=fixture(); res['module_timeline']=res['module_timeline'].iloc[0:0]
    fig=panel.fig_gantt(res)
    assert len(fig.data)==0
    res=fixture(); extra=res['shift_table'].iloc[[0]].copy(); extra['fecha']=pd.Timestamp('2026-10-03'); extra['vol_diario']=0
    res['shift_table']=pd.concat([res['shift_table'],extra],ignore_index=True)
    fig=panel.fig_gantt(res)
    assert len(fig.data[0].x)==2


def test_clickable_table_contains_raw_loaded_module_and_shift_data_and_server_popup():
    res=fixture()
    table=pres.tabla_itinerario(res)
    assert table.id=='reconstitucion-itinerario'
    assert table.cell_selectable is True
    assert len(table.data)==4
    row_id=table.data[0]['id']
    popup=pres.detalle_itinerario(res,row_id)
    content=' '.join(str(x.children) for x in walk(popup) if getattr(x,'children',None) is not None)
    assert 'Altura promedio apilada' in content and '8.2' in content
    assert 'Grado promedio apilado' in content and '0.64' in content
    assert 'ID registro' in content and '81' in content
    assert 'Volumen diario' in content and '1000' in content
    assert 'turno A (08-20)' in content and 'TMS asignada al turno en shift_table: 200 t' in content
    assert 'TMS diaria del modulo' in content and 'no se replica como TMS por tramo' in content
    assert pres.detalle_itinerario(res,'forged-row-id') is None
    # Stable id is reconstructed from the current server result, not table row_data.
    assert pres.detalle_itinerario(res,row_id) is not None


def test_popup_explicitly_says_daily_tms_is_not_duplicated_by_segment():
    res=fixture()
    row_id=pres.tabla_itinerario(res).data[0]['id']
    popup=pres.detalle_itinerario(res,row_id)
    content=' '.join(str(x.children) for x in walk(popup) if getattr(x,'children',None) is not None)
    assert 'no se replica como TMS por tramo' in content


def test_empty_itinerary_keeps_callback_component_mounted_once():
    res=fixture()
    res['module_timeline']=res['module_timeline'].iloc[0:0]
    res['masa']=pd.DataFrame()
    table=pres.tabla_itinerario(res)
    assert any(getattr(node,'id',None)=='reconstitucion-itinerario' for node in walk(table))
    assert len([node for node in walk(table) if getattr(node,'id',None)=='reconstitucion-itinerario'])==1
    assert table.children[1].data==[]
    assert [column['id'] for column in table.children[1].columns]==[
        'id','Caso','Pad','Campana','Parcela','Modulo','Fecha','Turno',
        'Intervalo estimado','TMH asignada a turno (t)','TMS asignada a turno (t)']
    rendered=panel.render(res)
    assert len([node for node in walk(rendered) if getattr(node,'id',None)=='reconstitucion-itinerario'])==1


def test_initial_shell_and_tabs_keep_callback_contract_stable():
    shell=panel.build_layout()
    assert [tab.value for tab in shell.children[7].children]==['1','2']
    app=__import__('dash').Dash(__name__,suppress_callback_exceptions=True)
    panel.register_callbacks(app,loader=lambda **kwargs: {},case_loader=lambda: [])
    detail=next(spec for spec in app._callback_list if 'reconstitucion-tabla-popup.children' in spec['output'])
    assert any(item['id']=='reconstitucion-itinerario' and item['property']=='active_cell'
               for item in detail['inputs'])


def test_callbacks_keep_graph_detail_and_add_server_side_table_selection():
    from dash import Dash
    app=Dash(__name__,suppress_callback_exceptions=True)
    panel.register_callbacks(app,loader=lambda **kwargs: {},case_loader=lambda: [])
    inputs=[(item['id'],item['property']) for spec in app._callback_list for item in spec['inputs']]
    assert ('reconstitucion-gantt','clickData') in inputs
    assert ('reconstitucion-itinerario','active_cell') in inputs
    assert ('reconstitucion-tabla-cerrar','n_clicks') in inputs
    detail=next(spec for spec in app._callback_list if 'reconstitucion-tabla-popup.children' in spec['output'])
    assert [(x['id'],x['property']) for x in detail['inputs']] == [
        ('reconstitucion-gantt','clickData'),('reconstitucion-itinerario','active_cell'),
        ('reconstitucion-tabla-cerrar','n_clicks'),('reconstitucion-token','data'),
        ('reconstitucion-pad-tabs','value'),('reconstitucion-caso','value'),('reconstitucion-casos','data')]


def test_multiple_paused_segments_remain_separate_and_turn_tms_is_not_duplicated():
    res=fixture()
    first=res['module_timeline'].iloc[0].copy()
    second=first.copy(); second['start']=pd.Timestamp('2026-10-01 12:00'); second['end']=pd.Timestamp('2026-10-01 14:00')
    res['module_timeline']=pd.concat([pd.DataFrame([{**first.to_dict(),'start':pd.Timestamp('2026-10-01 08:00'),'end':pd.Timestamp('2026-10-01 10:00')},second]),res['module_timeline'].iloc[[1]].assign(start=pd.Timestamp('2026-10-01 15:00'),end=pd.Timestamp('2026-10-01 18:00'))],ignore_index=True)
    pieces=pres._itinerary_frame(res)
    m5ta=pieces.loc[pieces.modulo.eq(5)&pieces.turno.eq('TA')]
    assert list(zip(m5ta.start,m5ta.end))==[(pd.Timestamp('2026-10-01 08:00'),pd.Timestamp('2026-10-01 10:00')),(pd.Timestamp('2026-10-01 12:00'),pd.Timestamp('2026-10-01 14:00'))]
    assert m5ta.masa_turno_asignada.notna().sum()==1
    assert len(pieces.loc[pieces.modulo.eq(5)&pieces.turno.eq('TB')])==1
    fig=panel.fig_gantt(res)
    assert len(fig.data)==1 and fig.data[0].type=='bar'

