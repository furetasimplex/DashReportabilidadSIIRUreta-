from . import presentation as ui,panel
from .test_presentation import source

def components(node):
    if isinstance(node,(list,tuple)):
        for child in node:yield from components(child)
    elif hasattr(node,'to_plotly_json'):
        yield node
        yield from components(getattr(node,'children',None))

def controls():
    return {n.id:n for n in components(ui.layout()) if getattr(n,'id',None)}

def test_main_columns_identical_and_technical_data_not_offered():
    nodes=controls();table=nodes['m6ct-fuentes'];picker=nodes['m6ct-columnas']
    visible=[c['id'] for c in table.columns if c['id'] not in table.hidden_columns]
    assert visible==['fecha_operacional','turno','correa','pi_tmh','tum_tmh','diferencia','calidad_pi','fuente_auto','modo_visible','fuente_m6','valor_m6']
    assert [o['label'] for o in picker.options]==['Tonelaje AUTO (TMH)','Disponibilidad TUM','Motivo de la decisión','Selección original','Diferencia (TMS)']
    assert not ui.AUDIT_ONLY.intersection(c['id'] for c in table.columns)
    raw=[dict(r,version_m6=4,huella_m6='audit_hash') for r in source()]
    decorated=ui.decorate(raw)
    assert all(all(r[k]==d[k] for k in raw[0]) for r,d in zip(raw,decorated))
    assert all(k in decorated[0] for k in ui.AUDIT_ONLY)

def test_toggle_round_trip_keeps_all_selectable_and_tms_values():
    nodes=controls();ids=[o['value'] for o in nodes['m6ct-columnas'].options]
    assert panel.extra_columns([])==ids
    assert panel.extra_columns(ids)==[]
    assert panel.extra_columns(['diferencia_tms'])==[k for k in ids if k!='diferencia_tms']
    assert panel.extra_columns(list(ui.AUDIT_ONLY))==ids
    row=dict(source()[0],diferencia=-25871.,diferencia_tms=-25094.87)
    data,tooltips=panel.filter_rows([row])
    assert data[0]['diferencia_tms']==-25094.87 and tooltips[0]['diferencia_tms']['value']=='-25.094,870000'

def test_history_keeps_version_request_and_original_equipment():
    row=dict(fecha_operacional='2026-10-04',turno='A',equipo_codigo='SRR_CV003',modo='TUM',
             version=7,usuario='qa',fecha_registro='2026-10-27',motivo='Original',vigente=True,
             solicitud_id='uuid-original',comentario='',id=1)
    table=panel.history_table([row])
    assert {'version','equipo_codigo','solicitud_id'}.issubset(c['id'] for c in table.columns)
    assert table.data[0]['version']==7 and table.data[0]['solicitud_id']=='uuid-original'

def test_manual_filter_uses_visible_label_and_preserves_criteria_and_other_filters():
    query='{turno} = "A"'
    filtered=panel.manual_filter(['SI'],query)
    assert filtered=='{modo_visible} contains "MANUAL · " && '+query
    assert panel.manual_filter([],filtered)==query
    assert panel.manual_filter(['SI'],filtered)==filtered
    assert panel.manual_filter(['SI'],'{modo_m6} = "TUM" && '+query)==filtered
    raw=[dict(source()[0],modo_m6=mode,fuente_m6=resolved) for mode in ('TUM','AUTO') for resolved in ('PI','TUM')]
    shown=ui.decorate(raw)
    assert [r for r in shown if 'MANUAL · ' in r['modo_visible']]==[r for r in shown if r['modo_m6']=='TUM']
