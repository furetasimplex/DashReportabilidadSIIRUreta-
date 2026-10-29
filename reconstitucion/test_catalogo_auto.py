from unittest.mock import patch
from dash import Dash
from . import panel

def walk(node):
    yield node
    children=getattr(node,'children',None)
    for child in children if isinstance(children,(list,tuple)) else [children]:
        if child is not None and not isinstance(child,str):yield from walk(child)

def test_catalogo_automatico_sin_sql_al_montar_y_sin_boton():
    calls=[]
    cases=[dict(id=i,nombre=f'Caso {i}',run_id=100+i,
        fecha_inicio='2026-10-01',fecha_fin='2026-10-12') for i in (1,2)]
    app=Dash(__name__)
    with patch('sqlalchemy.engine.Engine.connect',side_effect=AssertionError('SQL al montar')):
        layout=panel.build_layout()
        panel.register_callbacks(app,case_loader=lambda:(calls.append(1) or cases))
    nodes=list(walk(layout))
    assert not any(getattr(n,'id',None)=='reconstitucion-actualizar-casos' for n in nodes)
    timer=next(n for n in nodes if getattr(n,'id',None)=='reconstitucion-iniciar-casos')
    assert timer.max_intervals==1
    callback=next(v['callback'].__wrapped__ for k,v in app.callback_map.items() if 'reconstitucion-casos.data' in k)
    callback(0,2)
    assert not calls
    data,options,selected,status=callback(1,2)
    assert len(calls)==1 and selected==2
    assert len(data)==len(options)==2
