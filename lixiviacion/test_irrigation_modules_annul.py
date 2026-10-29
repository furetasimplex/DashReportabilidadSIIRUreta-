import copy,json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from . import irrigation_modules_model as m, irrigation_modules_db as db, irrigation_modules_panel as ui
from .test_irrigation_modules_temporal import point,resolve
from .test_irrigation_modules_db import snapshot,payload,configure
from .test_irrigation_modules_panel import text

def annul(h,identifier=999):return dict(id_evento=identifier,id_confirmacion_modular=h['id_confirmacion'],tipo_evento='ANULAR',fecha_efectiva=h['fecha_efectiva'],actor='tester',motivo='Registro duplicado',fecha_registro='2026-10-27',payload_json='{}')

@pytest.mark.parametrize('other',[[195],[196]])
def test_redundant_or_different_point_is_ignored(other):
 a,ea=point(17,[195]);b,eb=point(19,other)
 s=resolve(20,[a,b],[ea,eb,annul(b)])
 assert s['vigente']==a and s['temporal']['fecha_origen']=='2026-10-17'
 assert resolve(18,[a,b],[ea,eb,annul(b)])['temporal']['fin'] is None

@pytest.mark.parametrize('day,origin',[(14,14),(15,14),(16,14),(17,17),(20,17)])
def test_middle_point_no_longer_cuts_previous(day,origin):
 h,e=zip(*[point(14,[195]),point(15,[196]),point(17,[197])])
 assert resolve(day,h,[*e,annul(h[1])])['temporal']['fecha_origen']==f'2026-10-{origin}'

def test_family_annulled_without_resurrecting_V1_and_originals_immutable():
 h,e=zip(*[point(14,[195]),point(15,[196]),point(15,[],'SIN_INFORMACION',version=2)])
 original=copy.deepcopy((h,e));events=[*e,annul(h[2])]
 assert resolve(16,h,events)['vigente']==h[0] and (h,e)==original
 assert all(p['anulacion'] for p in m.temporal_points(h,events) if p['fecha']=='2026-10-15')

def test_no_previous_and_multiple_annulled_and_closed_boundary():
 h,e=zip(*[point(14,[195]),point(15,[196]),point(16,[197])])
 assert resolve(19,[h[2]],[e[2],annul(h[2])])['vigente'] is None
 assert resolve(19,h,[*e,annul(h[1]),annul(h[2],1000)])['vigente']==h[0]
 close=dict(id_evento=1001,id_confirmacion_modular=h[0]['id_confirmacion'],tipo_evento='CERRAR',fecha_efectiva='2026-10-17')
 assert resolve(19,h,[*e,annul(h[1]),annul(h[2],1000),close])['vigente'] is None

def own():
 s=snapshot(dict(id_confirmacion=18,estado_modular='SELECCION_CONOCIDA',cantidad_confirmada=3,fecha_efectiva='2026-10-19'));s['punto_fecha']=s['vigente'];s['revision'].update(cerrada=False,anulada=False)
 return s

def test_backend_appends_one_event_only_and_actor_is_backend(monkeypatch):
 s=own();before=copy.deepcopy(s);writes,actor=configure(monkeypatch,s)
 p=payload(s);p.update(actor='forged',observacion='Comentario')
 db.annul_modules(p)
 actor.assert_called_once_with();db._lock.assert_called_once()
 assert len(writes)==1 and writes[0][0]==db.EVENT
 v=writes[0][1];assert v['tipo_evento']=='ANULAR' and v['actor']=='admin_qa' and v['id_confirmacion_modular']==18
 assert json.loads(v['payload_json'])['observacion']=='Comentario' and s==before

@pytest.mark.parametrize('problem',['closed','annulled','inherited','motive','stale'])
def test_annul_rejections_never_write(monkeypatch,problem):
 s=own()
 if problem=='closed':s['revision']['cerrada']=True
 if problem=='annulled':s['revision']['anulada']=True
 if problem=='inherited':s['punto_fecha']=None
 writes,_=configure(monkeypatch,s);p=payload(s)
 if problem=='motive':p['motivo']=' '
 if problem=='stale':p['context_token']='old'
 with pytest.raises(ValueError):db.annul_modules(p)
 assert not writes

def test_backend_auth_before_connection(monkeypatch):
 monkeypatch.setattr(db.phase_db,'_actor',Mock(side_effect=PermissionError('denied')))
 conn=Mock();monkeypatch.setattr(db,'_connection',conn)
 with pytest.raises(PermissionError):db.annul_modules(payload(own()))
 conn.assert_not_called()

def test_retry_returns_original_event(monkeypatch):
 s=own();writes,_=configure(monkeypatch,s)
 monkeypatch.setattr(db,'_duplicate',lambda *a:dict(id_confirmacion=18,reintento=True))
 assert db.annul_modules(payload(s))['reintento'] and not writes

@pytest.mark.parametrize('trigger,reason,comment,expected',[
 ('imr-annul',None,None,False),('imr-annul-cancel',None,None,False),
 ('imr-annul-confirm',None,None,False),('imr-annul-confirm','Otro','',False),
 ('imr-annul-confirm','Registro duplicado','comentario',True)])
def test_explicit_modal_and_required_motive(monkeypatch,trigger,reason,comment,expected):
 monkeypatch.setattr(ui,'ctx',SimpleNamespace(triggered_id=trigger));persist=Mock();monkeypatch.setattr(db,'annul_modules',persist)
 result=ui.annul_action(1,0,1,reason,comment,dict(snapshot=own(),can_write=True),'key',0)
 assert persist.called==expected
 if expected:assert result[-1]==1 and not result[0]

def test_history_and_detail_use_previous_point():
 a,ea=point(17,[195,197,198]);b,eb=point(19,[195,197,198]);b.update(detalle=[],eventos=[],anulacion=annul(b),situacion_temporal='ANULADO')
 rendered=text(ui.history_cards([b]));assert all(x in rendered for x in ('ANULADO','Anulado por: tester','Registro duplicado','Fuente fixture'))
 s=own();s.update(resolve(19,[a,b],[ea,eb,annul(b)]));s['seleccion']=[dict(modulo_id=i,nombre_modulo_snapshot=n) for i,n in [(195,'M131'),(197,'M132'),(198,'M133')]]
 detail=text(ui.detail(s));assert '3 de 5 módulos' in detail and 'Vigente desde: 17-10-2026' in detail and 'ANULADO' not in detail

@pytest.mark.parametrize('editable',[True,False])
def test_ui_exact_only_and_readonly(editable):
 s=own();rendered=text(ui.editor(s,editable,[]))
 if not editable:assert 'imr-annul' not in rendered
 else:
  assert 'Anular decisión modular' in rendered
  s['punto_fecha']=None
  view=ui.editor(s,True,[])
  def find(c):
   if getattr(c,'id',None)=='imr-annul':return c
   children=getattr(c,'children',[])
   for child in children if isinstance(children,list) else [children]:
    result=find(child)
    if result is not None:return result
  assert find(view).style=={'display':'none'}

