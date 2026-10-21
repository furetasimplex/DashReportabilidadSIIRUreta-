"""Contrato del editor nativo Dash 3.1.1; sin conexión SQL."""
import ast
from pathlib import Path
import pytest
from . import db


@pytest.mark.parametrize('prefix', ['', 's', 'i'])
@pytest.mark.parametrize('op,sql', [('=','='),('>','>'),('>=','>='),('<','<'),('<=','<='),
                                   ('eq','='),('gt','>'),('ge','>='),('lt','<'),('le','<='),('ne','<>'),('!=','<>')])
def test_operator_normalization_only(prefix, op, sql):
    assert db.table_predicate(f' {{parcela}} {prefix}{op} 24 ') == (
        [f'nro_parcela_pad {sql} :tf0'], {'tf0':'24'})


@pytest.mark.parametrize('col', ['parcela','campana','flujo_m3_d','cu_drenaje_gl',
                                'cu_refino_gl','delta_cu_gl','transferencia_cu_t_d','fecha'])
def test_column_types_keep_existing_sql_expression(col):
    assert db.table_predicate(f'{{{col}}} s>= 0')[0] == [f'{db.DETAIL[col]} >= :tf0']


@pytest.mark.parametrize('value', ['Ox','Óxidos','óxidos','Campaña','s= i= scontains',
                                  'A && B',"x'; DROP TABLE t;--",'%_~['])
@pytest.mark.parametrize('op', ['contains','scontains','icontains','SCONTAINS'])
def test_text_is_parameterized_and_not_operator_normalized(value, op):
    clauses, params = db.table_predicate(f'{{pad}} {op} "{value}"')
    expected=value.replace('~','~~').replace('%','~%').replace('_','~_').replace('[','~[')
    assert params == {'tf0':'%'+expected+'%'}
    assert clauses == [f"CONVERT(nvarchar(100),{db.DETAIL['pad']},23) LIKE :tf0 ESCAPE '~'"]
    assert 'DROP' not in clauses[0]


def test_combined_same_column_and_quoted_conjunction():
    assert db.table_predicate('{parcela} s>= 20 && {parcela} s<= 25') == (
        ['nro_parcela_pad >= :tf0','nro_parcela_pad <= :tf1'], {'tf0':'20','tf1':'25'})
    clauses,params=db.table_predicate('{pad} scontains "s= A && B" && {campana} i= 17')
    assert len(clauses)==2 and params=={'tf0':'%s= A && B%','tf1':'17'}


def test_quoted_escapes_date_and_hydraulic_label():
    assert db.table_predicate(r'''{pad} scontains "A\"B"''')[1]=={'tf0':'%A"B%'}
    assert db.table_predicate('{fecha} datestartswith "2026-09"')[1]=={'tf0':'2026-09%'}
    assert db.table_predicate('{estado} s= "Campaña hidráulica"')[1]=={'tf0':'CAMPANA_HIDRAULICA'}
    assert db.table_predicate('{pad} = "==texto"')[1]=={'tf0':'==texto'}
    assert db.table_predicate('{pad} contains ""')[1]=={'tf0':'%%'}


@pytest.mark.parametrize('query', ['DROP TABLE', '{parcela} == 24','{parcela} <> 24',
    '{parcela} s== 24','{parcela} > =24','{parcela} unknown 24','{password} = 24',
    '{parcela} =','{parcela} = 24 &&','{parcela} = 24 || {parcela} = 25',
    '{pad} containsfoo','{pad} contains "sin cierre','&& {parcela} = 24'])
def test_invalid_queries_fail_with_controlled_message(query):
    with pytest.raises(ValueError, match='Filtro no válido'):
        db.table_predicate(query)


def test_business_sql_and_other_functions_unchanged():
    root=Path(__file__).resolve().parents[1]
    def tree(path):
        module=ast.parse(path.read_text(encoding='utf8'))
        module.body=[n for n in module.body if not(isinstance(n,ast.FunctionDef) and n.name=='table_predicate')]
        return ast.dump(module,include_attributes=False)
    assert tree(root/'lixiviacion/db.py')==tree(root/'test_fixtures/lixiviacion/filter_contract_db_before.py')
