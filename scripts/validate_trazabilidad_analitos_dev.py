from pathlib import Path
import sys
import os
from datetime import date

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db_connection import get_engine

OUT = ROOT / "docs/migrations/dev_trazabilidad_analitos_tm_emision_test"
INI = date(2026, 8, 1)
FIN = date(2026, 8, 10)


def main():
    engine = get_engine()
    baseline = pd.read_csv(OUT / "baseline_cache_20260801_20260809.csv")
    if os.environ.get("TRAZ_READ_ONLY") != "1":
        print("[1/4] ejecutando cache DEV", flush=True)
        raw = engine.raw_connection()
        try:
            cur = raw.cursor()
            cur.execute(
                "EXEC inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test "
                "@fecha_inicio=?, @fecha_fin=?",
                INI, FIN,
            )
            while cur.nextset():
                pass
            raw.commit()
        finally:
            raw.close()
    else:
        print("[1/4] validación de solo lectura", flush=True)
    print("[2/4] leyendo resultados", flush=True)
    with engine.connect() as conn:
        post = pd.read_sql(text(
            "SELECT * FROM inventar_SpcHidr.reporte_turno_cache_emision_test "
            "WHERE Fecha>=:ini AND Fecha<:fin ORDER BY Fecha,Turno"
        ), conn, params={"ini": INI, "fin": FIN})
        trace = pd.read_sql(text(
            "SELECT * FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test "
            "WHERE Fecha>=:ini AND Fecha<:fin "
            "ORDER BY Fecha,Turno,TM_Destino,Analito"
        ), conn, params={"ini": INI, "fin": FIN})
    baseline["Fecha"] = pd.to_datetime(baseline["Fecha"])
    post["Fecha"] = pd.to_datetime(post["Fecha"])
    for audit_col in ("Fecha_Actualizacion",):
        if audit_col in baseline.columns:
            baseline = baseline.drop(columns=[audit_col])
            post = post.drop(columns=[audit_col])
    texto = {
        "Material", "Turno", "Fuente_Info_Quimica", "Fuente_Info_Fisica",
        "Muestra_Quimica", "Muestra_Fisica",
    }
    for col in baseline.columns:
        if col != "Fecha" and col not in texto:
            baseline[col] = pd.to_numeric(baseline[col], errors="coerce")
            post[col] = pd.to_numeric(post[col], errors="coerce")
        elif col in texto:
            baseline[col] = baseline[col].fillna("").astype(str)
            post[col] = post[col].fillna("").astype(str)
    baseline = baseline.sort_values(["Fecha", "Turno"]).reset_index(drop=True)
    post = post.sort_values(["Fecha", "Turno"]).reset_index(drop=True)
    print("[3/4] comparando cache", flush=True)
    pd.testing.assert_frame_equal(
        baseline, post, check_dtype=False, check_exact=False,
        rtol=0, atol=0,
    )
    if trace.empty:
        raise AssertionError("La tabla de trazabilidad quedó vacía")
    invalidas = trace.loc[
        trace["Valor_Final"].notna()
        & ~trace["Fuente_Base"].isin(["TM1", "TM2", "MB", "IMP"])
    ]
    if not invalidas.empty:
        raise AssertionError(f"Valores sin fuente base válida: {len(invalidas)}")
    post.to_csv(OUT / "post_cache_20260801_20260809.csv", index=False)
    trace.to_csv(OUT / "trazabilidad_20260801_20260809.csv", index=False)
    print("[4/4] OK", flush=True)
    print(f"cache={len(post)} trazabilidad={len(trace)}")


if __name__ == "__main__":
    main()
