"""Smoke test de solo lectura para la configuración y dependencias de PROD."""

from __future__ import annotations

import os
import sys
import argparse
import contextlib
import io
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from db_startup_check import run_startup_db_check


def _extract_failures(report: str) -> list[str]:
    """Extrae solo la lista final de requisitos fallidos del reporte."""
    marker = "RESULTADO: FALTAN "
    if marker not in report:
        return []
    tail = report.split(marker, 1)[1]
    failures: list[str] = []
    for line in tail.splitlines()[1:]:
        if line.startswith("  - "):
            failures.append(line[4:])
        elif failures:
            break
    return failures


def _print_failure_summary(failures: list[str], error: Exception) -> None:
    dev_siir = [x.removeprefix("DEV_SIIR en ") for x in failures if x.startswith("DEV_SIIR en ")]
    inventar_dev = [
        x.split(" en ", 1)[1]
        for x in failures
        if x.startswith("catalogo inventar_SpcHidr en ")
    ]
    otros = [
        x for x in failures
        if not x.startswith("DEV_SIIR en ")
        and not x.startswith("catalogo inventar_SpcHidr en ")
    ]

    print("[SMOKE-PROD] RESULTADO: FALLO")
    if failures and not otros:
        print("  Conexion/configuracion/objetos requeridos: OK")
    if dev_siir:
        print(f"  Referencias incorrectas DEV_SIIR -> PROD_SIIR: {len(dev_siir)}")
        for module in dev_siir:
            print(f"    - {module}")
    if inventar_dev:
        print(
            "  Referencias incorrectas inventar_SpcHidr -> "
            f"inventar_SpcHidr_PROD: {len(inventar_dev)}"
        )
        for module in inventar_dev:
            print(f"    - {module}")
    if otros:
        print(f"  Otros requisitos fallidos: {len(otros)}")
        for item in otros:
            print(f"    - {item}")
    if not failures:
        print(f"  Error: {error}")
    print(
        "  Accion: aplicar docs/migrations/fix_prod_cross_db_references.sql "
        "y repetir este smoke."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose", action="store_true", help="muestra el reporte DB-CHECK completo"
    )
    args = parser.parse_args(argv)

    if os.getenv("ENVIRONMENT", "").strip().lower() != "production":
        print("[SMOKE-PROD] FALLO: ENVIRONMENT debe ser production")
        return 2

    captured = io.StringIO()
    db_check_logger = logging.getLogger("db_startup_check")
    logger_was_disabled = db_check_logger.disabled
    db_check_logger.disabled = True
    try:
        with contextlib.redirect_stdout(captured):
            ok = run_startup_db_check(strict=True)
    except Exception as exc:
        report = captured.getvalue()
        if args.verbose:
            print(report, end="")
        _print_failure_summary(_extract_failures(report), exc)
        return 1
    finally:
        db_check_logger.disabled = logger_was_disabled

    report = captured.getvalue()
    if args.verbose:
        print(report, end="")
    if not ok:
        _print_failure_summary(
            _extract_failures(report), RuntimeError("el chequeo devolvio False")
        )
        return 1

    print("[SMOKE-PROD] RESULTADO: OK")
    print("  Base efectiva: inventar_SpcHidr_PROD")
    print("  Auth y dependencias cross-DB: PROD_SIIR")
    print("  Objetos y referencias SQL: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
