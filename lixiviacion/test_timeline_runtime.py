"""Contrato y regresión de la integración autorizada; sin conexión SQL."""
import ast
from datetime import date
import json
from pathlib import Path
import re
from unittest.mock import patch
from . import db
from test_fixtures.lixiviacion.timeline_helpers import expressions,output_name
from .test_diagnostic_operational import fake_connection,row

P=Path(__file__).resolve().parents[1]/'test_fixtures/lixiviacion/diagnostico_timeline_runtime'


def test_timeline_uses_generic_bound_query_without_daily_function():
    assert db.OP_TIMELINE_SQL==(P/'candidate_runtime_12.sql').read_text(encoding='utf-8')
    assert db.OP_SOURCE not in db.OP_TIMELINE_SQL
    assert db.OP_SOURCE in db.OP_HEADER_SQL
    assert set(re.findall(r':(\w+)',db.OP_TIMELINE_SQL))=={'desde','hasta','pad_id','parcela_id'}


def test_exact_twelve_column_names_and_order():
    sql=db.OP_TIMELINE_SQL
    start=sql.rindex('\nSELECT d.fecha,')+len('\nSELECT ')
    final=sql[start:sql.index('\nFROM dias d',start)]
    fields=[output_name(x) for x in expressions(final)]
    contract=json.loads((P/'contract.json').read_text(encoding='utf-8'))
    assert fields==contract['fields']==list(db.OP_FIELDS)
    assert len(fields)==12 and '*' not in fields


def test_case_thresholds_and_null_semantics_unchanged():
    candidate=(P.parent/'diagnostico_performance_candidate'/'candidate_generic.sql').read_text(encoding='utf-8')
    for marker,end in [('), estado_modulo AS (','), distribucion AS ('),
                       ('), riego_dia AS (','), drenaje_dia AS ('),
                       ('), drenaje_dia AS (','), dias AS (')]:
        assert candidate.split(marker)[1].split(end)[0]==db.OP_TIMELINE_SQL.split(marker)[1].split(end)[0]
    original_quality=candidate.rsplit('    CASE\n            WHEN r.estado_operacional IS NULL',1)[1].split(' AS calidad_estado')[0]
    assert original_quality in db.OP_TIMELINE_SQL


def test_only_authorized_timeline_and_filter_parser_changed_in_runtime_module():
    def tree(path):
        t=ast.parse(path.read_text(encoding='utf-8'))
        t.body=[n for n in t.body if not (isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='OP_TIMELINE_SQL' for x in n.targets))]
        # Corrección independiente autorizada del contrato DataTable (2026-10-16).
        # Su alcance completo se protege en test_table_filter_contract.py.
        t.body=[n for n in t.body if not (isinstance(n,ast.FunctionDef) and n.name=='table_predicate')]
        return ast.dump(t,include_attributes=False)
    assert tree(P/'db_before.py')==tree(Path(__file__).parent/'db.py')


def test_live_before_after_evidence_exact_null_safe_and_bidirectional():
    cases=json.loads((P/'comparacion.json').read_text(encoding='utf-8'))
    assert len(cases)==37
    assert all(c['pass'] and c['SOLO_ANTERIOR']==c['SOLO_NUEVO']==c['DIFERENCIAS_COLUMNAS']==0 for c in cases)
    assert all(c['baseline_hash']==c['candidate_hash'] for c in cases)
    assert all(not c['baseline_reversals'] and not c['new_reversals'] for c in cases)


def test_multicampaign_transitions_and_extended_range_preserved():
    cases={c['case']:c for c in json.loads((P/'comparacion.json').read_text(encoding='utf-8'))}
    assert cases['p1_17_102d']['campaigns']==[4,11]
    assert cases['p2_28_102d']['campaigns']==[8,10]
    assert cases['p1_1_253d']['candidate_count']==cases['p2_7_253d']['candidate_count']==253


def test_operational_helper_preserves_null_and_campaign_change():
    old=row(date(2026,9,9));old['campana_id']=4
    new=row();new['campana_id']=11
    old['riego_activo']=None
    calls=[]
    with patch.object(db,'_connection',fake_connection([new],[old,new],calls)):
        _,timeline=db.operational(dict(desde='2026-09-09',hasta='2026-09-10',pad=1,parcela=17))
    assert timeline==[old,new] and timeline[0]['riego_activo'] is None
    assert [r['campana_id'] for r in timeline]==[4,11]
