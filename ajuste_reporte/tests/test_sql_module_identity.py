import json
import uuid
from pathlib import Path
from unittest.mock import Mock
import pytest
from ajuste_reporte import rep_prod_adjuster as w

@pytest.mark.parametrize('kind', ['PROCEDURE', 'VIEW'])
def test_only_initial_create_alter_representation_is_equivalent(kind):
    a=f"ALTER {kind} dbo.example\nAS\nSELECT 'ALTER VIEW x', 'a  b' -- preserve comment\n"
    b=a.replace('ALTER', 'CREATE', 1).replace('\n', '\r\n')
    assert w._sql_module_comparison_text(a)==w._sql_module_comparison_text(b)
    for changed in (a.replace('a  b','a b'), a.replace('ALTER VIEW x','CREATE VIEW x'),
                    a.replace('preserve comment','different comment'), a+'DELETE FROM historic;'):
        assert w._sql_module_comparison_text(a)!=w._sql_module_comparison_text(changed)

@pytest.mark.parametrize('bad', [None,'checksum','verify','uuid','risk','tests'])
def test_reduced_dev_backup_protocol_keeps_all_checks(monkeypatch,bad):
    from lixiviacion import phase_flags
    p=Path(w.__file__).resolve().parents[1]/'auditorias/m6_adaptacion_directa_20261026'/('test_reduced_'+uuid.uuid4().hex+'.json')
    proof=dict(backup_protocol='DEV_CHECKSUM_VERIFYONLY',backup_set_id=7003,
               backup_set_uuid='51F1E39A-980D-4675-BE94-87D832BD35F4',
               backup_checksum_ok=True,verifyonly_checksum_ok=True,residual_risk_accepted=True,
               execute_dev=True,backup_reference='MOCK_TEST_ONLY',database_name='inventar_SpcHidr',
               server_name='VPS-5347319-X',new_period_publisher_tested=True,consumers_review_passed=True)
    if bad:
        field={'checksum':'backup_checksum_ok','verify':'verifyonly_checksum_ok','uuid':'backup_set_uuid',
               'risk':'residual_risk_accepted','tests':'new_period_publisher_tested'}[bad]
        proof[field]=False
    p.write_text(json.dumps(proof),encoding='utf8')
    monkeypatch.setenv('ENABLE_M6_DATOS_CONCILIADOS_DEV','1');monkeypatch.setenv('M6_DEV_BACKUP_EVIDENCE',str(p))
    monkeypatch.setattr(phase_flags,'is_dev',lambda:True);monkeypatch.setattr(phase_flags,'guard_connection',lambda c:None)
    guard=Mock();monkeypatch.setattr(w,'_assert_standard_publication_sql',guard)
    try:
        if bad:
            with pytest.raises(w.M6ValidationError):w._m6_standard_guard(Mock(),connection=Mock())
            guard.assert_not_called()
        else:
            w._m6_standard_guard(Mock(),connection=Mock());guard.assert_called_once()
    finally:p.unlink()
