import ast
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from . import db, callbacks, panel,phase_db
from .test_map import text_content


def row(day=date(2026,9,10), state='MIXTO'):
    return dict(fecha=day,pad_id=1,parcela_id=17,numero_parcela=17,campana_id=11,numero_campana='18',
                estado_operacional=state,calidad_estado='EVALUABLE',tiene_dato_riego=1,riego_activo=0,
                tiene_dato_drenaje=1,drenaje_activo=None,campana_hidraulica_id=None,
                numero_campana_hidraulica=None,estado_asignacion='FUERA_VENTANA_RIEGO')


def fake_connection(header, timeline, calls):
    class Conn:
        def execute(self,sql,params):
            calls.append((str(sql),params))
            return SimpleNamespace(mappings=lambda: header if len(calls)==1 else timeline)
    @contextmanager
    def connection(): yield Conn()
    return connection


def test_end_date_identity_and_two_queries_ignore_hydraulic_campaign():
    calls=[]
    f=dict(desde='2026-09-01',hasta='2026-09-10',pad=None,parcela=17,campana=999,estado='FUERA_VENTANA_RIEGO')
    with patch.object(db,'_connection',fake_connection([row()],[row()],calls)):
        h,t=db.operational(f)
    assert calls[0][1]=={'fecha':date(2026,9,10),'pad_id':None,'parcela_id':17}
    assert len(calls)==2 and db.OP_SOURCE not in calls[1][0] and 'MAXRECURSION 32767' in calls[1][0]
    assert calls[1][1]['pad_id']==1
    assert 'campana_id=' not in calls[0][0] and 'campana' not in calls[1][1]
    # La lógica de módulos ahora está inline; el contrato expuesto continúa siendo de parcela/día.
    assert all('modulo' not in field for field in db.OP_FIELDS)
    assert 'fn_estado_operacional_modulo_diario' not in calls[1][0]
    assert 'v.fecha=e.fecha AND v.pad_id=e.pad_id AND v.parcela_id=e.parcela_id' in calls[0][0]
    assert h['campana_id']==11 and h['campana_hidraulica_id'] is None


@pytest.mark.parametrize('rows',[[row(),row()],[row(date(2026,8,31))],[dict(row(),parcela_id=18)]])
def test_timeline_rejects_duplicate_outside_or_wrong_identity(rows):
    calls=[]
    with patch.object(db,'_connection',fake_connection([row()],rows,calls)),pytest.raises(ValueError):
        db.operational(dict(desde='2026-09-01',hasta='2026-09-10',pad=1,parcela=17))


def test_no_parcel_no_query_and_empty_message():
    with patch.object(db,'_connection',side_effect=AssertionError):
        assert db.operational({'parcela':None})==(None,[])
        assert 'Seleccione una parcela' in text_content(callbacks.load_operational({'parcela':None}))
    with patch.object(phase_db,'operational',return_value=(None,[])):
        assert 'Sin información operacional' in text_content(callbacks.load_operational({'parcela':17,'hasta':'2026-09-10'}))


def v2row(phase='RIEGO_CONTINUO'):
    return dict(row(),fase_final=phase,fase_calculada_modelo=phase,condicion_dia='RIEGO_DRENAJE',
                origen_fase_final='AUTOMATICO',riego_activo_v2=1)


@pytest.mark.parametrize('state,expected',[('MIXTO','Mixto'),('ESPERA_RECLAMO','Espera de reclamo'),('RIEGO_CONTINUO','Riego continuo'),('APILADO','Apilado')])
def test_friendly_header_and_separate_assignment(state,expected):
    content=text_content(callbacks.operational_header(v2row(state),'2026-09-10'))
    for value in (expected,'10-09-2026','Campaña operacional 18','Campaña hidráulica Sin dato',
                  'Fuera de ventana hidráulica','Drenaje al 10-09-2026 Sin dato','no implica inactividad'):
        assert value in content
    assert 'Condición diaria' in content and 'Fase estructural V2' in content


def test_categorical_timeline_exact_condition_null_activity_and_colors():
    fig=callbacks.operational_timeline([v2row()],{'desde':'2026-09-01','hasta':'2026-09-10'})
    assert fig.data[0].type=='bar' and fig.data[0].orientation=='h'
    assert fig.data[0].customdata[0][1]=='Riego continuo' and fig.data[0].customdata[0][2]=='Riego y aporte de drenaje'
    assert fig.data[0].customdata[0][5]=='Sin dato'
    assert fig.data[0].marker.color==callbacks.operational_colors()['RIEGO_CONTINUO']
    assert fig.layout.yaxis.type=='category'


def test_operational_failure_independent_of_four_kpis_and_three_figures():
    totals=dict(registros=1,flujo=10,transferencia=-2,delta=0,fuera=1)
    with patch.object(db,'overview',return_value=(totals,[])),patch.object(phase_db,'operational',side_effect=RuntimeError):
        physical=callbacks.load(1,'2026-09-01','2026-09-10',1,None,17,None)
        assert physical[:4]==('10,000','-2,000','0,000','1')
        from .test_ux_governance import components
        assert len([n for n in components(physical[4]) if type(n).__name__=='Graph'])==3 and physical[5]['parcela']==17
        assert 'No fue posible cargar el estado operacional.' in text_content(callbacks.load_operational(physical[5]))


def test_existing_metric_and_chart_functions_unchanged_from_baseline():
    def nodes(path):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    root=Path(__file__).parent
    for file,names in [('db.py',['where','options','overview','detail']),
                       ('callbacks.py',['number','serial','figure'])]:
        old,new=nodes(root.parent/'test_fixtures/lixiviacion/diagnostico_fase1'/file),nodes(root/file)
        assert all(old[n]==new[n] for n in names)


def test_visual_labels_keep_sql_codes_and_full_label_filter():
    assert dict(panel.LABELS)['estado']=='Asignación hidráulica'
    assert dict(panel.LABELS)['campana']=='Campaña hidráulica'
    clauses,params=db.table_predicate('{estado} = "Fuera de ventana hidráulica"')
    assert clauses==['estado_asignacion = :tf0'] and params['tf0']=='FUERA_VENTANA_RIEGO'
