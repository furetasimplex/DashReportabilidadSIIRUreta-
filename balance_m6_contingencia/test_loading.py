"""Carga UI: consulta completa, conteos y resultados vacíos ante fallos."""
import copy
from unittest.mock import patch
import pytest
from flask import Flask,session
from . import panel,service
from .test_presentation import source,dump

@pytest.fixture
def authenticated():
    app=Flask(__name__);app.secret_key='QA_ONLY'
    with app.test_request_context('/'):
        session['user']='tester'
        yield

@pytest.mark.parametrize('rows,expected',[(source(),'2 registros consultados: 1 AUTO y 1 manual vigente'),([], '0 registros consultados: 0 AUTO y 0 manuales vigentes')])
def test_load_counts_only_after_all_sources_complete(authenticated,rows,expected):
    original=copy.deepcopy(rows)
    with patch.object(service,'load_rows',return_value=rows) as read,patch.object(service,'cases',return_value=[]),patch.object(service,'history',return_value=[]) as history,patch.object(service,'persist') as persist:
        result=panel.load(1,None,'2026-10-04','A','2026-10-05','B',['SRR_CV003'])
        assert expected in result[-1]
        read.assert_called_once_with('2026-10-04','A','2026-10-05','B',['SRR_CV003'])
        history.assert_called_once_with('2026-10-04','2026-10-05')
        assert rows==original and result[0]==panel.ui.decorate(rows)
        persist.assert_not_called()

@pytest.mark.parametrize('stage',['load_rows','cases','history'])
def test_error_discards_table_cases_history_and_success_message(authenticated,stage):
    with patch.object(service,'load_rows',return_value=source()),patch.object(service,'cases',return_value=[]),patch.object(service,'history',return_value=[]),patch.object(service,stage,side_effect=RuntimeError('private SQL error')):
        result=panel.load(1,None,'2026-10-04','A','2026-10-04','B',list(panel.EQUIPOS))
        assert result[:3]==([],[],[])
        assert 'No se pudo consultar' in dump(result[-1]) and 'registros consultados' not in dump(result[-1])
        assert 'private SQL error' not in dump(result[-1])

def test_no_session_returns_empty_results():
    app=Flask(__name__);app.secret_key='QA_ONLY'
    with app.test_request_context('/'),patch.object(service,'load_rows') as read:
        assert panel.load(1,None,'2026-10-04','A','2026-10-04','B',list(panel.EQUIPOS))[:3]==([],[],[])
        read.assert_not_called()
