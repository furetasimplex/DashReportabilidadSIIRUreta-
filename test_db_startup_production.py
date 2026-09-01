from db_startup_check import (
    INVENTAR_DB_PROD,
    PRODUCTION_LOGIN_DATABASE,
    _production_config_errors,
)
from scripts.smoke_test_production_db import _extract_failures


def test_production_config_accepts_exact_targets():
    assert _production_config_errors(
        sqlserver_db=INVENTAR_DB_PROD,
        login_database=PRODUCTION_LOGIN_DATABASE,
    ) == []


def test_production_config_rejects_dev_databases():
    errors = _production_config_errors(
        sqlserver_db="inventar_SpcHidr",
        login_database="DEV_SIIR.dbo.auth_user",
    )
    assert any("SQLSERVER_DB" in error for error in errors)
    assert any("LOGIN_DATABASE" in error for error in errors)


def test_production_config_requires_full_login_fqn():
    errors = _production_config_errors(
        sqlserver_db=INVENTAR_DB_PROD,
        login_database="PROD_SIIR.auth_user",
    )
    assert errors == [
        "LOGIN_DATABASE debe ser PROD_SIIR.dbo.auth_user "
        "(actual=PROD_SIIR.auth_user)"
    ]


def test_production_config_rejects_dev_balance_database():
    errors = _production_config_errors(
        sqlserver_db=INVENTAR_DB_PROD,
        login_database=PRODUCTION_LOGIN_DATABASE,
        balance_recon_database="DEV_SIIR",
    )
    assert errors == [
        "BALANCE_RECON_DATABASE debe ser PROD_SIIR (actual=DEV_SIIR)"
    ]


def test_smoke_extracts_only_final_failures():
    report = """cabecera
  [FALTA] ruido
RESULTADO: FALTAN 2 objeto(s) requeridos
  - DEV_SIIR en inventar_SpcHidr.sp_x
  - catalogo inventar_SpcHidr en inventar_SpcHidr.v_x
Modo STRICT: abortando arranque.
"""
    assert _extract_failures(report) == [
        "DEV_SIIR en inventar_SpcHidr.sp_x",
        "catalogo inventar_SpcHidr en inventar_SpcHidr.v_x",
    ]
