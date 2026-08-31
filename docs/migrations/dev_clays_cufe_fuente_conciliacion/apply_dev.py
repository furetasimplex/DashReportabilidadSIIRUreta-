from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from db_connection import get_engine  # noqa: E402


def main() -> None:
    expected_host = "149.50.136.234"
    if os.getenv("SQLSERVER_HOST") != expected_host:
        raise RuntimeError("Despliegue bloqueado: SQLSERVER_HOST no corresponde a DEV.")

    engine = get_engine()
    with engine.connect() as conn:
        identity = conn.execute(text("SELECT @@SERVERNAME, DB_NAME()"), {}).one()
        columns = pd.read_sql(
            text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA='inventar_SpcHidr'
                  AND TABLE_NAME='Clays_CuFe_trazabilidad'
            """),
            conn,
        )
        cardinality = pd.read_sql(
            text("""
                SELECT CAST(c.Fecha AS date) Fecha,
                       UPPER(LTRIM(RTRIM(c.Turno))) Turno,
                       COUNT(*) Cantidad,
                       COUNT(DISTINCT UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato,''))))) Fuentes_Distintas
                FROM inventar_SpcHidr.v_conciliacion_chancado_v2 c
                WHERE c.Fecha >= '20260801' AND c.Fecha < '20260901'
                GROUP BY CAST(c.Fecha AS date), UPPER(LTRIM(RTRIM(c.Turno)))
                HAVING COUNT(*) > 1
                    OR COUNT(DISTINCT UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato,''))))) > 1
            """),
            conn,
        )
    if "id_trazabilidad" not in set(columns["COLUMN_NAME"]):
        raise RuntimeError("Falta id_trazabilidad en la tabla histórica DEV.")
    if not cardinality.empty:
        cardinality.to_csv(HERE / "cardinalidad_conflictiva.csv", index=False)
        raise RuntimeError("Conciliación tiene cardinalidad/fuentes ambiguas; no se despliega.")

    print(f"Destino verificado: servidor={identity[0]} base={identity[1]}")
    view_sql = (HERE / "v_clays_cufe_calculado_v2_test.after.sql").read_text(encoding="utf-8")
    sp_sql = (HERE / "sp_refrescar_clays_cufe.after.sql").read_text(encoding="utf-8")
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute(view_sql)
        cursor.execute(sp_sql)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    print("Vista y SP desplegados en DEV.")


if __name__ == "__main__":
    main()
