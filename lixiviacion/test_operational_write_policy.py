"""Política temporal DEV: permisos reales del helper, SQL simulado y cero DML."""
import copy
from unittest.mock import Mock,MagicMock
import pytest
from flask import Flask,session
import auth
from . import phase_db,phase_flags,phase_panel,irrigation_modules_panel as panel,irrigation_modules_db as modules
from .test_ux_governance import preview as phase_preview
from .test_irrigation_modules_db import snapshot,payload,configure
from lixiviacion import phase_flags as permission_flags


@pytest.fixture
def policy(monkeypatch):
    records={'active':(1,0,0),'staff':(1,1,0),'super':(1,0,1),'inactive':(0,1,1)}
    calls=[];engine=MagicMock();conn=engine.connect.return_value.__enter__.return_value
    def execute(sql,args):
        sql=str(sql);calls.append((sql,args));r=records.get(args['u'])
        active=None if r is None else r[0]
        result=Mock();result.scalar_one_or_none.return_value=active
        result.scalar.return_value=None if r is None else int(bool(r[0] and (r[1] or r[2])))
        return result
    conn.execute.side_effect=execute
    monkeypatch.setattr(auth,'get_engine',lambda:engine)
    monkeypatch.setattr(auth,'LOGIN_TABLE','DEV_SIIR.dbo.auth_user')
    monkeypatch.setenv('ENVIRONMENT','development')
    monkeypatch.setattr(phase_flags,'is_dev',lambda:True)
    monkeypatch.setattr(permission_flags,'is_dev',lambda:True)
    monkeypatch.setattr(phase_flags,'enabled',lambda _:True)
    guard=Mock();monkeypatch.setattr(phase_flags,'guard_connection',guard)
    monkeypatch.setattr(permission_flags,'guard_connection',guard)
    app=Flask(__name__);app.secret_key='fixture-only'
    return app,records,calls,guard


@pytest.mark.parametrize('username,expected',[('active',True),('staff',True),('super',True),('inactive',False),('missing',False)])
def test_dev_real_permission_helper_and_actor(policy,username,expected):
    app,_,calls,guard=policy
    with app.test_request_context('/',method='POST',base_url='http://localhost',headers={'Origin':'http://localhost'}):
        session['user']=username
        if expected:assert phase_db._actor()==username
        else:
            with pytest.raises(PermissionError):phase_db._actor()
    guard.assert_called_once()
    assert 'is_active=1' in calls[0][0] and 'is_staff' not in calls[0][0] and 'is_superuser' not in calls[0][0]


@pytest.mark.parametrize('username',[None,'',42])
def test_no_authenticated_actor_never_queries_permission(policy,username):
    app,_,calls,_=policy
    with app.test_request_context('/',method='POST'):
        if username is not None:session['user']=username
        with pytest.raises(PermissionError):phase_db._actor()
    assert not calls


@pytest.mark.parametrize('method,origin',[('GET',None),('POST','https://foreign.invalid')])
def test_method_and_origin_are_still_required(policy,method,origin):
    app,_,calls,_=policy
    with app.test_request_context('/',method=method,headers={'Origin':origin} if origin else {}):
        session['user']='active'
        with pytest.raises(PermissionError):phase_db._actor()
    assert not calls


def test_forged_ui_permission_is_not_authority(policy,monkeypatch):
    app,_,calls,_=policy;tx=Mock();connect=Mock()
    monkeypatch.setattr(phase_db,'_transaction',tx);monkeypatch.setattr(modules,'_connection',connect)
    with app.test_request_context('/',method='POST'):
        with pytest.raises(PermissionError):phase_db.decide({'ui_can_write':True,'accion':'CONFIRMAR'})
        with pytest.raises(PermissionError):modules.confirm_modules({'ui_can_write':True,'can_write':True})
    assert not calls;tx.assert_not_called();connect.assert_not_called()


@pytest.mark.parametrize('action',['CONFIRMAR','RECTIFICAR','CERRAR','RESOLVER_CONTRADICCION'])
def test_active_user_passes_authorization_but_incomplete_phase_is_rejected(policy,monkeypatch,action):
    app,_,calls,_=policy;tx=Mock();monkeypatch.setattr(phase_db,'_transaction',tx)
    with app.test_request_context('/',method='POST'):
        session['user']='active'
        with pytest.raises(ValueError):phase_db.decide({'accion':action})
    assert calls;tx.assert_not_called()


@pytest.mark.parametrize('action',['confirm_modules','rectify_modules','close_modules'])
def test_active_user_does_not_skip_modular_payload(policy,monkeypatch,action):
    app,_,calls,_=policy;connect=Mock();monkeypatch.setattr(modules,'_connection',connect)
    with app.test_request_context('/',method='POST'):
        session['user']='active'
        with pytest.raises((ValueError,KeyError,TypeError)):getattr(modules,action)({})
    assert calls;connect.assert_not_called()


def test_active_user_stale_is_rejected_and_idempotency_remains(policy,monkeypatch):
    app,_,_,_=policy;real_actor=phase_db._actor;s=snapshot();writes,_=configure(monkeypatch,s)
    monkeypatch.setattr(phase_db,'_actor',real_actor)
    p=payload(s);p['context_token']='STALE'
    with app.test_request_context('/',method='POST'):
        session['user']='active'
        with pytest.raises(modules.model.StaleContextError):modules.confirm_modules(p)
        assert not writes
        monkeypatch.setattr(modules,'_duplicate',lambda *a:dict(id_confirmacion=7,reintento=True))
        assert modules.confirm_modules(payload(s))['reintento'] is True
        assert not writes


def test_active_status_is_revalidated_on_every_action(policy):
    app,records,_,_=policy
    with app.test_request_context('/',method='POST'):
        session['user']='active';assert phase_db._actor()=='active'
        records['active']=(0,0,0)
        with pytest.raises(PermissionError):phase_db._actor()


@pytest.mark.parametrize('username,expected',[('active',False),('staff',True),('super',True),('inactive',False),('missing',False)])
@pytest.mark.parametrize('scope',['non_dev','production'])
def test_non_dev_and_production_keep_admin_policy(policy,monkeypatch,username,expected,scope):
    _,_,calls,guard=policy
    if scope=='non_dev':
        monkeypatch.setattr(phase_flags,'is_dev',lambda:False)
        monkeypatch.setattr(permission_flags,'is_dev',lambda:False)
    else:monkeypatch.setenv('ENVIRONMENT','production')
    assert auth.user_can_write_operational_decisions(username) is expected
    assert 'is_staff=1 OR is_superuser=1' in calls[0][0]
    guard.assert_not_called()


def test_dev_requires_matching_auth_table_and_effective_connection(policy,monkeypatch):
    _,_,calls,guard=policy
    monkeypatch.setattr(auth,'LOGIN_TABLE','PROD_SIIR.dbo.auth_user')
    assert not auth.user_can_write_operational_decisions('active') and not calls
    monkeypatch.setattr(auth,'LOGIN_TABLE','DEV_SIIR.dbo.auth_user')
    guard.side_effect=PermissionError('Identidad SQL incorrecta')
    assert not auth.user_can_write_operational_decisions('active') and not calls


def test_dev_sql_failure_denies(policy,monkeypatch):
    monkeypatch.setattr(auth,'get_engine',Mock(side_effect=RuntimeError('SQL no disponible')))
    assert not auth.user_can_write_operational_decisions('active')


def test_dev_flags_still_deny(policy,monkeypatch):
    app,_,calls,_=policy;monkeypatch.setattr(phase_flags,'enabled',lambda _:False)
    with app.test_request_context('/',method='POST'):
        session['user']='active'
        with pytest.raises(PermissionError):phase_db._actor()
    assert not calls


def test_guest_label_does_not_authenticate_or_deny_a_real_user(policy):
    app,_,calls,_=policy
    with app.test_request_context('/',method='POST'):
        session['username']='Invitado'
        with pytest.raises(PermissionError):phase_db._actor()
        assert not calls
        session['user']='active'
        assert phase_db._actor()=='active'


def test_active_nonstaff_gets_both_editors_without_bypassing_button_conditions(policy,monkeypatch):
    app,_,_,_=policy;e=phase_preview();e['context_token']='token';r=e['row']
    selected={k:r[k] for k in ('pad_id','parcela_id','campana_id')}
    monkeypatch.setattr(phase_db,'preview',lambda *a:copy.deepcopy(e))
    monkeypatch.setattr(phase_db,'history',lambda *a:([],[]))
    monkeypatch.setattr(phase_db,'clean',lambda x:dict(x))
    s=snapshot();monkeypatch.setattr(modules,'modular_snapshot',lambda *a:copy.deepcopy(s))
    monkeypatch.setattr(modules,'modular_history',lambda *a:[])
    with app.test_request_context('/',method='POST'):
        session['user']='active'
        phase=phase_panel.preview_admin(selected,r['fecha'],0)
        assert phase[2]['ui_can_write'] is True and phase[6] is None
        assert phase_panel.form_editability(phase[2])[:6]==(False,)*6
        assert phase_panel.action_buttons(phase[2],None,None,'',r['fecha'])==(True,True,True,True)
        modular=panel.preview({'pad_id':2,'parcela_id':59},'2026-10-19')
        assert modular[1]['can_write'] is True
        from .test_irrigation_modules_panel import text
        assert 'imr-form' in text(modular[3]) and 'Solo lectura' not in text(modular[3])
        assert panel.availability(None,[],'',modular[1])[1:] == (True,True,True)
