"""Ejecuta el parche de referencias PROD desde el archivo versionado.

Sin argumentos realiza solamente el preflight. Para aplicar los ALTER se exige
la combinación explícita ``--apply --confirm inventar_SpcHidr_PROD``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from db_connection import get_connection

PATCH_PATH = ROOT / "docs" / "migrations" / "fix_prod_cross_db_references.sql"
CONFIRMATION = "inventar_SpcHidr_PROD"
PATCH_VERSION = "2026-09-01.4"


def _load_batches(apply: bool) -> list[str]:
    sql = PATCH_PATH.read_text(encoding="utf-8")
    if f"PATCH_VERSION: {PATCH_VERSION}" not in sql:
        raise RuntimeError(
            f"Version incorrecta del parche; se requiere {PATCH_VERSION}"
        )
    # test_imp solo puede aparecer en la normalización documentada del nombre
    # heredado de dbo.v_imp_conciliacion_chancado.
    if sql.lower().count("test_imp") != 2:
        raise RuntimeError("Cantidad inesperada del token legado test_imp")
    expected = "DECLARE @Aplicar bit = 0;"
    if expected not in sql:
        raise RuntimeError("No se encontro el selector seguro @Aplicar=0")
    if apply:
        sql = sql.replace(expected, "DECLARE @Aplicar bit = 1;", 1)
    return [
        batch for batch in re.split(r"^\s*GO\s*$", sql, flags=re.I | re.M)
        if batch.strip()
    ]


def _consume_results(cursor) -> None:
    while True:
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            if "modulo" in columns:
                module_index = columns.index("modulo")
                for row in rows:
                    print(f"    - {row[module_index]}")
        if not cursor.nextset():
            break


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="aplica los 12 ALTER")
    parser.add_argument("--confirm", help=f"debe ser exactamente {CONFIRMATION}")
    args = parser.parse_args(argv)

    if args.apply and args.confirm != CONFIRMATION:
        parser.error(f"para aplicar use --confirm {CONFIRMATION}")

    mode = "APLICACION" if args.apply else "PREFLIGHT (SOLO LECTURA)"
    print(f"[PATCH-PROD] Archivo: {PATCH_PATH}")
    print(f"[PATCH-PROD] Version: {PATCH_VERSION}")
    print(f"[PATCH-PROD] Modo: {mode}")

    connection = get_connection()
    if connection is None:
        print("[PATCH-PROD] FALLO: no se pudo conectar")
        return 1
    connection.autocommit = True

    try:
        cursor = connection.cursor()
        for batch in _load_batches(args.apply):
            cursor.execute(batch)
            _consume_results(cursor)
    except Exception as exc:
        print(f"[PATCH-PROD] FALLO: {exc}")
        return 1
    finally:
        connection.close()

    if args.apply:
        print("[PATCH-PROD] OK: parche aplicado; ejecute el smoke test")
    else:
        print("[PATCH-PROD] OK: preflight aprobado; no se modifico la base")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
