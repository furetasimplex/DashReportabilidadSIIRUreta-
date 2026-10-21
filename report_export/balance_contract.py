"""Contrato operacional central del Reporte de Balance."""

from datetime import date, datetime
import hashlib
import os
import re
import math
from pathlib import Path
from env_loader import load_app_env


load_app_env()


BALANCE_TEMPLATE_SHA256 = (
    "C8F5AE2730EAE6827E083031D7A907432B385D9BFFA941E472F44A5D01EEBF8D"
)


def _configured_identifier(env_name, fallback=None):
    value = os.getenv(env_name) or fallback
    if not value or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise RuntimeError(
            f"{env_name} debe contener un identificador SQL valido."
        )
    return value


BALANCE_RECON_DATABASE = _configured_identifier(
    "BALANCE_RECON_DATABASE",
    os.getenv("SQLSERVER_NAME")
    or (
        "PROD_SIIR"
        if os.getenv("ENVIRONMENT", "").strip().lower() == "production"
        else "DEV_SIIR"
    ),
)
BALANCE_RECON_SCHEMA = _configured_identifier("BALANCE_RECON_SCHEMA", "hidro")
BALANCE_RECON_SOURCE = (
    f"[{BALANCE_RECON_DATABASE}].[{BALANCE_RECON_SCHEMA}]"
)

BALANCE_MODELS = {
    1: {"flow_count": 120, "template": "Template_Balance_Planta_Hidrometalurgia.xlsx",
        "sha256": BALANCE_TEMPLATE_SHA256, "code": "hidrometalurgia_120_completo"},
    2: {"flow_count": 125, "template": "Template_Balance_Planta_Hidrometalurgia_V2.xlsx",
        "sha256": "B39FE64FD479F4CC0C096B0D5FF790126BA3093F9EF5B19D028D1CE3260447CD",
        "code": "hidrometalurgia_125_v2"},
}


def get_balance_model_contract(modelo_id=1):
    try:
        model = int(modelo_id)
    except (ValueError, TypeError) as exc:
        raise ValueError("El Caso no identifica un modelo compatible de Balance.") from exc
    if model not in BALANCE_MODELS:
        raise ValueError(f"El modelo {model} no dispone de plantilla compatible de Balance.")
    if model == 2 and BALANCE_RECON_DATABASE.upper() != "DEV_SIIR":
        raise ValueError("La exportacion del modelo 2 esta habilitada solo en DEV_SIIR.")
    return dict(BALANCE_MODELS[model], modelo_id=model)


def get_balance_template_path(modelo_id):
    contract = get_balance_model_contract(modelo_id)
    return str(Path(__file__).resolve().parents[1] / "reporte" / contract["template"])


def balance_solver_observation(metadata):
    """Describe el estado persistido sin cambiar la seleccion oficial ni bloquearla."""
    import json
    raw = metadata.get("solver_metadata_json") or metadata.get("metadata_json") or {}
    try:
        details = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (ValueError, TypeError):
        return "Metadata del solver no interpretable; se exporta la seleccion oficial SQL."
    if not isinstance(details, dict):
        return "Metadata del solver sin estructura de objeto; se exporta la seleccion oficial SQL."
    if details.get("solver_converged") is False or details.get("officializable") is False:
        return ("Seleccion oficial SQL con observaciones del solver: "
                f"solver_converged={details.get('solver_converged')}; "
                f"officializable={details.get('officializable')}. "
                "No constituye certificacion matematica.")
    return ""


def is_finite_balance_number(value):
    try:
        return value is not None and math.isfinite(float(value))
    except (ValueError, TypeError, OverflowError):
        return False


def _as_date(value, label):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} no es una fecha valida.") from exc


def build_balance_report_identity(metadata):
    """Construye una identidad única desde metadata oficial validada."""
    caso_id = int(metadata["caso_id"])
    run_id = int(metadata["solver_run_id"])
    start = _as_date(metadata["fecha_inicio"], "fecha_inicio")
    end = _as_date(metadata["fecha_fin"], "fecha_fin")
    mtd_start = _as_date(
        metadata.get("fecha_inicio_acumulado", metadata.get("mtd_fecha_inicio")),
        "fecha_inicio_acumulado",
    )
    mtd_end = _as_date(
        metadata.get("fecha_fin_acumulado", metadata.get("mtd_fecha_fin", end)),
        "fecha_fin_acumulado",
    )
    if start > end or mtd_start > mtd_end:
        raise ValueError("La identidad del Balance contiene fechas invertidas.")
    return {
        "filename": (
            ("Balance_Planta_Hidrometalurgia_V2_" if int(metadata.get("modelo_id", 1)) == 2
             else "Balance_Planta_Hidrometalurgia_")
            +
            f"{start:%Y%m%d}_{end:%Y%m%d}_Caso{caso_id}_Run{run_id}.xlsx"
        ),
        "caso_label": f"Caso {caso_id}",
        "run_label": f"Run oficial {run_id}",
        "periodo_label": f"Período {start:%d/%m/%Y} al {end:%d/%m/%Y}",
        "mtd_label": f"Acumulado {mtd_start:%d/%m/%Y} al {mtd_end:%d/%m/%Y}",
        "caso_id": caso_id,
        "run_id": run_id,
        "fecha_inicio": start,
        "fecha_fin": end,
        "mtd_fecha_inicio": mtd_start,
        "mtd_fecha_fin": mtd_end,
    }


def validate_balance_template_hash(template_path, modelo_id=1):
    digest = hashlib.sha256()
    with open(template_path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest().upper()
    if actual != get_balance_model_contract(modelo_id)["sha256"]:
        raise ValueError(
            "El template maestro de Balance fue modificado y no coincide "
            "con la version validada."
        )
    return actual
