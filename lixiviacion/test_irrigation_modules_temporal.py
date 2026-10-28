import copy,json,uuid
import pytest
from . import irrigation_modules_model as m,irrigation_modules_db as db,irrigation_modules_panel as panel
from .test_irrigation_modules_model import roster
from .test_irrigation_modules_db import snapshot,payload,configure
from .test_irrigation_modules_panel import text


def point(day,ids,state='SELECCION_CONOCIDA',version=1,identifier=None,r=None):
    r=copy.deepcopy(r or roster());identifier=identifier or day*10+version
    h=dict(id_confirmacion=identifier,familia_id=str(day),version=version,fecha_efectiva=f'2026-10-{day:02d}',
        pad_id=r['pad_id'],parcela_id=r['parcela_id'],campana_id=r['campana_id'],estado_modular=state,
        cantidad_confirmada=None if state=='SIN_INFORMACION' else len(ids),total_modulos_snapshot=r['total'],
        orden_es_operacional=r['orden_confiable'],roster_snapshot_json=m.dump(r['miembros']),
        usuario='fixture',justificacion='Fuente fixture',created_at='2026-10-27',referencia_snapshot_json=None)
    e=dict(id_evento=identifier,id_confirmacion_modular=identifier,tipo_evento='CONFIRMAR',fecha_efectiva=h['fecha_efectiva'])
    return h,e


def resolve(day,headers,events,r=None,path=()):
    r=copy.deepcopy(r or roster());r['fecha']=f'2026-10-{day:02d}'
    return m.resolve_temporal(r,headers,events,path)


@pytest.mark.parametrize('day',[1,2,4,5])
def test_A_B_P26_inherits_without_daily_rows(day):
    h,e=point(1,[195,196,197]);before=copy.deepcopy((h,e))
    s=resolve(day,[h],[e])
    assert s['vigente']['id_confirmacion']==h['id_confirmacion']
    assert s['temporal']['fecha_origen']=='2026-10-01'
    assert s['temporal']['heredada']==(day>1) and (h,e)==before


@pytest.mark.parametrize('day,start',[(1,1),(2,1),(4,1),(5,1),(6,6),(7,6)])
def test_C_P26_new_date_cuts_previous(day,start):
    pairs=[point(1,[195,196,197]),point(6,[195])]
    h,e=zip(*pairs);s=resolve(day,h,e)
    assert s['temporal']['fecha_origen']==f'2026-10-{start:02d}'
    assert s['vigente']['version']==1


@pytest.mark.parametrize('state,count',[('NINGUN_MODULO',0),('SIN_INFORMACION',None)])
def test_D_E_F_explicit_states_inherit_then_new_selection(state,count):
    pairs=[point(1,[195]),point(10,[],state),point(15,[196])];h,e=zip(*pairs)
    for day in (10,11,14):
        s=resolve(day,h,e);assert s['vigente']['estado_modular']==state and s['vigente']['cantidad_confirmada']==count
    assert resolve(15,h,e)['vigente']['estado_modular']=='SELECCION_CONOCIDA'


def test_G_no_back_propagation():
    h,e=point(6,[195]);assert resolve(5,[h],[e])['vigente'] is None


def test_H_no_campaign_inheritance():
    h,e=point(1,[195]);r=roster();r['campana_id']=999
    assert resolve(4,[h],[e],r)['vigente'] is None


@pytest.mark.parametrize('change',['member','sequence','ambiguous'])
def test_I_incompatible_roster_blocks_without_resurrection(change):
    h,e=point(1,[195]);r=roster()
    if change=='member':r['miembros'][0]['modulo_id']=999
    elif change=='sequence':r['miembros'][0]['secuencia_carguio']=7
    else:r['orden_confiable']=False
    s=resolve(4,[h],[e],r);assert s['vigente'] is None and s['temporal']['aplicabilidad']=='ROSTER_INCOMPATIBLE'
    # Un corte intermedio sigue cortando aunque los extremos vuelvan a coincidir.
    assert resolve(5,[h],[e],path=[r])['vigente'] is None


def test_informational_milestones_do_not_break_compatibility_but_change_stale_hash():
    r=roster();other=copy.deepcopy(r);other['miembros'][0]['fecha_fin_retiro']='2026-10-20'
    other['miembros'][0]['control_id_snapshot']=999;other['miembros'][0]['nombre_visible']='Nombre documental actualizado'
    assert m.compatibility_signature(r)==m.compatibility_signature(other)
    assert m.digest(r)!=m.digest(other)
    h,e=point(1,[195],r=r);assert resolve(4,[h],[e],other)['vigente'] is not None


@pytest.mark.parametrize('day,active',[(4,True),(5,False),(6,False)])
def test_J_close_is_half_open_and_never_resurrects_previous(day,active):
    h0,e0=point(1,[195]);h,e=point(3,[196]);close=dict(id_evento=999,id_confirmacion_modular=h['id_confirmacion'],tipo_evento='CERRAR',fecha_efectiva='2026-10-05')
    s=resolve(day,[h0,h],[e0,e,close]);assert bool(s['vigente'])==active
    assert s['temporal']['fecha_origen']=='2026-10-03'


def test_K_correction_changes_same_point_not_later_family():
    pairs=[point(1,[195]),point(1,[195,196],version=2),point(6,[197])];h,e=zip(*pairs)
    assert resolve(4,h,e)['vigente']['version']==2
    assert resolve(6,h,e)['vigente']['version']==1
    assert resolve(6,h,e)['temporal']['fecha_origen']=='2026-10-06'


def test_L_new_date_is_new_family_V1_not_supersede(monkeypatch):
    s=snapshot({'id_confirmacion':1});s['punto_fecha']=None;s['revision'].update(id=None,version=0)
    s['temporal']=dict(heredada=True,cierre=None)
    writes,_=configure(monkeypatch,s);db.confirm_modules(payload(s))
    h=writes[0][1];assert h['version']==1 and h['supersede_id'] is None and h['version_anterior'] is None


def test_new_date_retroactive_boundary_is_derived_not_written():
    pairs=[point(1,[195]),point(10,[197]),point(6,[196])];h,e=zip(*pairs)
    assert resolve(5,h,e)['temporal']['fecha_origen']=='2026-10-01'
    assert resolve(9,h,e)['temporal']['fecha_origen']=='2026-10-06'
    assert resolve(10,h,e)['temporal']['fecha_origen']=='2026-10-10'


def test_editor_inherited_confirm_not_rectify_and_dates_are_explicit():
    h,e=point(1,[195]);s=snapshot();s.update(resolve(6,[h],[e]));s['roster']['fecha']='2026-10-06'
    s['seleccion']=[dict(modulo_id=195,nombre_modulo_snapshot='M131')]
    p=dict(snapshot=s,can_write=True)
    assert panel.availability('SELECCION_CONOCIDA',[195],'Fuente',p)[1:]==(False,True,False)
    rendered=text(panel.editor(s,True,[]))
    for expected in ('Vigente desde: 01-10-2026','Fecha consultada: 06-10-2026','Registrar cambio desde 06-10-2026'):
        assert expected in rendered


def test_no_reopen_or_rectify_closed_point(monkeypatch):
    s=snapshot({'id_confirmacion':1});s['punto_fecha']=s['vigente'];s['revision']['cerrada']=True;s['temporal']={'cierre':'2026-10-20'}
    writes,_=configure(monkeypatch,s)
    for action in (db.confirm_modules,db.rectify_modules,db.close_modules):
        with pytest.raises(ValueError):action(payload(s))
    assert not writes


def test_history_versions_group_by_effective_point_not_campaign():
    a,_=point(1,[195],version=2);b,_=point(6,[196],version=1)
    for h in (a,b):h.update(detalle=[],eventos=[])
    rendered=text(panel.history_cards([a,b]))
    assert rendered.count('Vigente')==2 and 'Supersedida' not in rendered
    assert 'Punto desde 01-10-2026' in rendered and 'Punto desde 06-10-2026' in rendered


@pytest.mark.parametrize('offset,accepted',[(0,False),(1,True)])
def test_new_point_after_closure_requires_later_effective_date(monkeypatch,offset,accepted):
    s=snapshot();s['roster']['fecha']=f'2026-10-{19+offset:02d}'
    s['punto_fecha']=None;s['temporal']=dict(aplicabilidad='CERRADA',cierre='2026-10-19')
    writes,_=configure(monkeypatch,s);p=payload(s);p['fecha']=s['roster']['fecha']
    if accepted:db.confirm_modules(p)
    else:
        with pytest.raises(ValueError,match='posterior al cierre'):db.confirm_modules(p)
        assert not writes
    assert panel.availability('SELECCION_CONOCIDA',[195],'Fuente',dict(snapshot=s,can_write=True))[1] is (not accepted)


@pytest.mark.parametrize('day,expected',[(1,2),(5,2),(6,4),(7,4),(8,5),(13,5),(14,4),(16,4),(17,3),(27,3)])
def test_P27_conceptual_intervals(day,expected):
    pairs=[point(d,list(range(195,195+n))) for d,n in [(1,2),(6,4),(8,5),(14,4),(17,3)]]
    h,e=zip(*pairs);assert resolve(day,h,e)['vigente']['cantidad_confirmada']==expected
