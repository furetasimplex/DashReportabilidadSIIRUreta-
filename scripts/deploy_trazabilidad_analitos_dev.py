"""Despliega y valida trazabilidad de analitos exclusivamente en DEV."""
from __future__ import annotations

import difflib
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine


DEFINICIONES = ROOT / "docs/reportes/analisis_tm/definiciones_bd.sql"
DDL = ROOT / "docs/migrations/dev_trazabilidad_analitos_tm_emision_test.sql"
OUT = ROOT / "docs/migrations/dev_trazabilidad_analitos_tm_emision_test"
PROC = "inventar_SpcHidr.sp_reporte_turno_emision_test"
INI = date(2026, 8, 1)
FIN = date(2026, 8, 10)


def _extraer_procedimiento(texto: str) -> str:
    marker = "CREATE   PROCEDURE [inventar_SpcHidr].[sp_reporte_turno_emision_test]"
    inicio = texto.index(marker)
    fin = texto.index("\nGO\n\n-- ====", inicio)
    return texto[inicio:fin].replace("CREATE   PROCEDURE", "ALTER PROCEDURE", 1)


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(["Fecha", "Turno"], kind="stable").reset_index(drop=True)


def main() -> None:
    print("[1/7] conectando", flush=True)
    engine = get_engine()
    OUT.mkdir(parents=True, exist_ok=True)
    sql_nuevo = _extraer_procedimiento(DEFINICIONES.read_text(encoding="utf-8"))

    with engine.connect() as conn:
        sql_anterior = conn.scalar(text(
            "SELECT OBJECT_DEFINITION(OBJECT_ID(:objeto))"
        ), {"objeto": PROC})
    if not sql_anterior:
        raise RuntimeError(f"No existe {PROC} en la base configurada")

    sql_anterior_alter = sql_anterior.replace("CREATE   PROCEDURE", "ALTER PROCEDURE", 1)
    (OUT / "sp_reporte_turno_emision_test.before.sql").write_text(
        sql_anterior_alter, encoding="utf-8"
    )
    (OUT / "sp_reporte_turno_emision_test.after.sql").write_text(
        sql_nuevo, encoding="utf-8"
    )
    diff = difflib.unified_diff(
        sql_anterior_alter.splitlines(True), sql_nuevo.splitlines(True),
        fromfile="sp_reporte_turno_emision_test.before.sql",
        tofile="sp_reporte_turno_emision_test.after.sql",
    )
    (OUT / "sp_reporte_turno_emision_test.diff").write_text(
        "".join(diff), encoding="utf-8"
    )

    print("[2/7] diff generado", flush=True)
    # Línea base del cache DEV antes del ALTER. El refresco se valida aparte
    # para evitar que un fallo/timeout del SP oculte el resultado del DDL.
    with engine.connect() as conn:
        print("[3/5] leyendo baseline", flush=True)
        baseline = pd.read_sql(text(
            "SELECT * FROM inventar_SpcHidr.reporte_turno_cache_emision_test "
            "WHERE Fecha>=:ini AND Fecha<:fin ORDER BY Fecha,Turno"
        ), conn, params={"ini": INI, "fin": FIN})
    baseline.to_csv(OUT / "baseline_cache_20260801_20260809.csv", index=False)

    ddl = DDL.read_text(encoding="utf-8").split("GO", 1)[0]
    with engine.begin() as conn:
        print("[4/5] desplegando DDL y ALTER", flush=True)
        conn.execute(text(ddl))
        conn.exec_driver_sql(sql_nuevo)
    print("[5/5] DDL y ALTER confirmados; falta ejecutar regresión", flush=True)
    print(f"OK baseline={len(baseline)}")


if __name__ == "__main__":
    main()
