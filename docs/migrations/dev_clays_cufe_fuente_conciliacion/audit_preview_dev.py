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
    if os.getenv("SQLSERVER_HOST") != "149.50.136.234":
        raise RuntimeError("Auditoría bloqueada fuera de DEV")
    engine = get_engine()
    with engine.connect() as conn:
        after = pd.read_sql(text("""
            SELECT v.*, UPPER(LTRIM(RTRIM(c.Fuente_Dato))) Fuente_Conciliacion_Origen
            FROM inventar_SpcHidr.v_clays_cufe_calculado_v2_test v
            LEFT JOIN inventar_SpcHidr.v_conciliacion_chancado_v2 c
              ON CAST(c.Fecha AS date)=v.Fecha
             AND CASE WHEN UPPER(LTRIM(RTRIM(c.Turno))) IN ('A','TA','TURNOA') THEN 'A'
                      WHEN UPPER(LTRIM(RTRIM(c.Turno))) IN ('B','TB','TURNOB') THEN 'B' END=v.Turno
            WHERE v.Fecha >= '20260801' AND v.Fecha < '20260901'
            ORDER BY v.Fecha,v.Turno,v.Torre
        """), conn)
        mismatches = after.loc[
            (after["Fuente_Conciliacion_Origen"] == "IMP")
            & (
                after["Fuente_CaolBeta"].fillna("").str.startswith("MB_")
                | after["Fuente_CuFe"].fillna("").str.startswith("MB_")
            )
        ]
    after.to_csv(HERE / "view_after_before_refresh.csv", index=False)
    mismatches.to_csv(HERE / "mismatches_after_view.csv", index=False)

    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute(
            "EXEC inventar_SpcHidr.sp_refrescar_clays_cufe "
            "@FechaInicio=?, @FechaFin=?, @SoloVistaPrevia=1",
            "2026-08-01", "2026-08-31",
        )
        sets = []
        while True:
            if cur.description:
                cols = [c[0] for c in cur.description]
                sets.append(pd.DataFrame.from_records(cur.fetchall(), columns=cols))
            if not cur.nextset():
                break
    finally:
        raw.close()
    for index, frame in enumerate(sets, 1):
        frame.to_csv(HERE / f"preview_resultset_{index}.csv", index=False)
    acciones = sets[1] if len(sets) > 1 else pd.DataFrame()
    print("Mismatches IMP etiquetados MB después de corregir vista:", len(mismatches))
    print(acciones.to_string(index=False))


if __name__ == "__main__":
    main()
