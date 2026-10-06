from decimal import Decimal
import json
import pytest
from .smoke_current_dev import check_rows
from . import smoke_evidence


def row():
    return dict(fecha='2026-09-10',pad_id=1,parcela_id=1,nro_parcela_pad=1,campana_id=None,
                estado_asignacion='FUERA_VENTANA_RIEGO',delta_cu_gl=None,expected_delta=None,
                transferencia_cu_t_d=None,expected_t=None)


def test_null_is_not_zero():
    r=row(); check_rows([r]); r['delta_cu_gl']=Decimal(0)
    with pytest.raises(AssertionError,match='FORMULA'): check_rows([r])


def test_duplicate_is_not_silently_removed():
    with pytest.raises(AssertionError,match='duplicadas'): check_rows([row(),row()])


def test_operational_state_cannot_replace_hydraulic_assignment():
    r=row(); r['estado_asignacion']='RIEGO_DRENAJE'
    with pytest.raises(AssertionError,match='hidráulica'): check_rows([r])


def test_evidence_runs_never_overwrite(monkeypatch,tmp_path):
    monkeypatch.setattr(smoke_evidence,'OUT',tmp_path)
    first=smoke_evidence.write_evidence('CURRENT_SMOKE','v2',{'passed':True},period={})
    second=smoke_evidence.write_evidence('CURRENT_SMOKE','v2',{'passed':False},period={})
    assert first!=second and json.loads(first.read_text())['result']['passed'] is True
