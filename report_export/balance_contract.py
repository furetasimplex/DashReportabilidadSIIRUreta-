"""Contrato operacional central del Reporte de Balance."""

from datetime import date, datetime
import hashlib
import os
import re
from dotenv import load_dotenv


load_dotenv()


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
            "Balance_Planta_Hidrometalurgia_"
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


def validate_balance_template_hash(template_path):
    digest = hashlib.sha256()
    with open(template_path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest().upper()
    if actual != BALANCE_TEMPLATE_SHA256:
        raise ValueError(
            "El template maestro de Balance fue modificado y no coincide "
            "con la version validada."
        )
    return actual
