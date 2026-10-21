"""Pruebas UI sin SQL: claves estables, simulación, consentimiento y navegación."""
import ast,json,time
from pathlib import Path
from unittest.mock import patch
import pytest
from flask import Flask,session
from dash import no_update
from plotly.utils import PlotlyJSONEncoder
from . import panel,service,presentation as ui
from .test_contingencia import row

def dump(x):return json.dumps(x,cls=PlotlyJSONEncoder,ensure_ascii=False)
def source():
    return ui.decorate([{**row(),'pi_tmh':32768.,'fuente_m6':'TUM','modo_m6':'TUM'},
                       {**row(),'pi_tmh':32768.,'fecha_operacional':'2026-10-05','fuente_m6':'TUM','modo_m6':'AUTO'}])
def comparison():
    a=[dict(Flujo=f'F{i}',Tonelaje=100.,Ley_Cu=0.,FCu=0.) for i in range(1,126)]
    b=[dict(r) for r in a];b[9]['Tonelaje']=90.
    return service.compare(a,b)

@pytest.fixture
def auth():
    server=Flask(__name__);server.secret_key='unit-test-only'
    with server.test_request_context('/'):
        session['user']='tester'
        yield
    panel._pending.clear()

def args(case=None,mode='TUM'):
    rows=source()
    return [1,None,'2026-10-01','A','2026-10-12','B',list(panel.EQUIPOS),case,rows,[rows[0]['id']],mode,'revisado','',None,[]]

def test_stable_keys_survive_sort_filter_page_and_hidden_selection_warning():
    rows=source();ids=[r['id'] for r in rows]
    assert panel.selected_records(list(reversed(rows)),[ids[0]])==[rows[0]]
    metrics,message=panel.summary(rows,ids,[ids[1]])
    assert '1 registros seleccionados están ocultos' in dump(message)
    assert 'ya tienen una decisión manual' in dump(message)
    assert 'Manuales vigentes' in dump(metrics)
    # AUTO · TUM nunca se cuenta como manual.
    assert rows[1]['modo_visible']=='AUTO · TUM'
    assert rows[0]['modo_visible']=='MANUAL · TUM'

def test_marks_consulted_and_clears_without_automatic_selection():
    rows=source()
    with patch.object(panel,'ctx') as context:
        context.triggered_id='m6ct-todos';assert panel.mark(1,None,None,rows)==([0,1],[r['id'] for r in rows])
        context.triggered_id='m6ct-raw';assert panel.mark(None,None,rows,rows)==([],[])
        context.triggered_id='m6ct-ninguno';assert panel.mark(None,1,None,rows)==([],[])

def test_manual_filter_preserves_other_filters_and_never_removes_raw_rows():
    query='{turno} = "A"'
    manual=panel.manual_filter(['SI'],query)
    assert panel.manual_filter([],manual)==query
    assert panel.manual_filter(['SI'],manual)==manual
    assert panel.filter_rows(source())[0]==source()

def test_number_precision_and_audit_columns_remain_available():
    assert ui.number(32768.)=='32.768,00'
    r=source()[0];r['pi_tmh']=32768.123456
    shown=ui.decorate([r])[0]
    assert shown['pi_tmh']==32768.123456
    assert ui.tooltips([shown])[0]['pi_tmh']['value']=='32.768,123456'
    assert panel.extra_columns(ui.EXTRA)==[]
    assert panel.extra_columns([])==ui.EXTRA

@pytest.mark.parametrize('case',[4136,4137,None])
@pytest.mark.parametrize('mode',['AUTO','TUM'])
def test_preview_optional_case_and_single_return_auto_are_read_only(auth,case,mode):
    a=args(case,mode)
    with patch.object(panel,'ctx') as context,patch.object(service,'load_rows',return_value=list(reversed(source()))),patch.object(service,'preview',return_value={'comparacion':comparison(),'huella_entradas':'B'*64}) as preview,patch.object(service,'persist') as persist:
        context.triggered_id='m6ct-preview'
        rendered,token,status,checked=panel.act(*a)
        assert token and checked==[] and status==''
        assert preview.call_args.args[2]==case
        keys=preview.call_args.args[3]
        assert len(keys)==1 and keys[0]['fecha_operacional']=='2026-10-04' and keys[0]['modo']==mode
        assert 'caso_id' not in keys[0]
        assert 'Ver los 125 flujos' in dump(rendered) and 'Flujos con variación' in dump(rendered)
        persist.assert_not_called()

@pytest.mark.parametrize('change',['case','reason','selection','mode','user','ttl'])
def test_changed_inputs_expired_token_or_other_user_cannot_confirm(auth,change):
    a=args()
    with patch.object(panel,'ctx') as context,patch.object(service,'load_rows',return_value=source()),patch.object(service,'preview',return_value={'comparacion':comparison(),'huella_entradas':'B'*64}),patch.object(service,'persist') as persist:
        context.triggered_id='m6ct-preview';a[13]=panel.act(*a)[1];a[14]=['SI']
        if change=='case':a[7]=4137
        if change=='reason':a[11]='otro'
        if change=='selection':a[9]=[]
        if change=='mode':a[10]='AUTO'
        if change=='user':session['user']='other'
        if change=='ttl':panel._pending[a[13]]['time']=time.monotonic()-panel.TTL-1
        context.triggered_id='m6ct-guardar';result=panel.handle_action(*a)
        assert 'Preview vencido' in dump(result[2]) and result[4] is no_update
        persist.assert_not_called()

def test_success_refresh_double_click_and_sql_rejection(auth):
    a=args()
    with patch.object(panel,'ctx') as context,patch.object(service,'load_rows',return_value=source()),patch.object(service,'preview',return_value={'comparacion':comparison(),'huella_entradas':'B'*64}),patch.object(service,'persist') as persist:
        context.triggered_id='m6ct-preview';a[13]=panel.act(*a)[1];a[14]=['SI']
        context.triggered_id='m6ct-guardar'
        persist.side_effect=ValueError('Entradas obsoletas')
        rejected=panel.handle_action(*a);assert rejected[4] is no_update and 'Entradas obsoletas' in dump(rejected[2])
        persist.side_effect=None
        saved=panel.handle_action(*a);assert saved[4] is not no_update and '1 decisiones' in dump(saved[2])
        persist.reset_mock();again=panel.handle_action(*a)
        persist.assert_not_called();assert 'Preview vencido' in dump(again[2])

def test_history_keeps_request_id_and_current_historical_labels():
    rows=[dict(fecha_operacional='2026-10-04',turno='A',equipo_codigo='SRR_CV003',modo='TUM',version=1,usuario='test',fecha_registro='2026-10-20',motivo='motivo',vigente=v,solicitud_id='uuid',comentario='',id=i) for i,v in enumerate((True,False))]
    rendered=dump(panel.history_table(rows))
    assert all(s in rendered for s in ('VIGENTE','HISTÓRICA','Solicitud','uuid'))

def test_host_legacy_link_opens_same_monitor_tab_and_no_duplicate_tree():
    path=Path(__file__).resolve().parents[1]/'layout.py'
    tree=ast.parse(path.read_text(encoding='utf8'))
    fn=next(x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name=='toggle_subtabs')
    text=ast.get_source_segment(path.read_text(encoding='utf8'),fn)
    assert '"nav-balance-m6": "monitor-pitum"' in text
    assert '"pitum-contingencia-m6" if triggered' in text
    assert 'balance_m6_panel.layout()' not in text

def test_unknown_selection_rejected():
    with pytest.raises(ValueError,match='fuera de la consulta'):panel.selected_records(source(),['fake-key'])
