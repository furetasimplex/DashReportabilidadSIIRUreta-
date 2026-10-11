from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine  # noqa: E402


INI = "2026-08-01"
FIN_INCLUSIVE = "2026-08-31"
FIN_EXCLUSIVE = "2026-09-01"
KEY_VIEW = ["Fecha", "Turno", "Torre"]


def run_proc(raw, sql: str, params: tuple) -> list[pd.DataFrame]:
    cur = raw.cursor()
    cur.execute(sql, *params)
    frames: list[pd.DataFrame] = []
    while True:
        if cur.description:
            columns = [item[0] for item in cur.description]
            frames.append(pd.DataFrame.from_records(cur.fetchall(), columns=columns))
        if not cur.nextset():
            break
    return frames


def assert_numeric_equal(before: pd.DataFrame, after: pd.DataFrame, columns: list[str], keys: list[str]) -> None:
    left = before.copy()
    right = after.copy()
    date_key = "Fecha" if "Fecha" in keys else "Dia"
    for frame in (left, right):
        frame[date_key] = pd.to_datetime(frame[date_key])
    merged = left[keys + columns].merge(right[keys + columns], on=keys, how="outer", suffixes=("_antes", "_despues"), indicator=True)
    if not (merged["_merge"] == "both").all():
        raise AssertionError(f"Cambió la malla de claves: {merged[merged['_merge'] != 'both'].to_dict('records')}")
    differences = []
    for col in columns:
        a = pd.to_numeric(merged[f"{col}_antes"], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(merged[f"{col}_despues"], errors="coerce").to_numpy(dtype=float)
        # Los snapshots CSV conservan 15-17 dígitos; tolerancia exclusiva de
        # serialización, muy inferior a cualquier precisión funcional.
        bad = ~(np.isclose(a, b, rtol=1e-14, atol=1e-12, equal_nan=True))
        if bad.any():
            differences.append(merged.loc[bad, keys + [f"{col}_antes", f"{col}_despues"]])
    if differences:
        raise AssertionError(pd.concat(differences).to_string(index=False))


def main() -> None:
    if os.getenv("SQLSERVER_HOST") != "149.50.136.234":
        raise RuntimeError("Refresco bloqueado fuera de DEV")
    engine = get_engine()
    before_view = pd.read_csv(HERE / "view_before.csv")
    before_clays = pd.read_csv(HERE / "clays_before.csv")
    before_reps = pd.read_csv(HERE / "reps_before.csv")
    before_cache = pd.read_csv(HERE / "cache_before.csv")
    validate_only = "--validate-only" in sys.argv

    with engine.connect() as conn:
        history_count_before = conn.execute(text("SELECT COUNT_BIG(*) FROM inventar_SpcHidr.Clays_CuFe_trazabilidad")).scalar_one()
        corrected_view = pd.read_sql(text("""
            SELECT * FROM inventar_SpcHidr.v_clays_cufe_calculado_v2_test
            WHERE Fecha >= :ini AND Fecha < :fin ORDER BY Fecha,Turno,Torre
        """), conn, params={"ini": INI, "fin": FIN_EXCLUSIVE})

    assert_numeric_equal(
        before_view, corrected_view,
        ["Representatividad_Quimica", "Representatividad_Quimica_TM2", "CaolBeta_MB", "CaolBeta_Final", "CaolBeta_Final_2D", "CuFe_MB", "CuFe_Final", "CuFe_Final_2D"],
        KEY_VIEW,
    )

    if not validate_only:
        raw = engine.raw_connection()
        try:
            refresh_sets = run_proc(
                raw,
                "EXEC inventar_SpcHidr.sp_refrescar_clays_cufe @FechaInicio=?, @FechaFin=?, @SoloVistaPrevia=0",
                (INI, FIN_INCLUSIVE),
            )
            raw.commit()
        except Exception:
            raw.rollback()
            raise
        finally:
            raw.close()
        for index, frame in enumerate(refresh_sets, 1):
            frame.to_csv(HERE / f"refresh_resultset_{index}.csv", index=False)

        raw = engine.raw_connection()
        try:
            emission_sets = run_proc(
                raw,
                "EXEC inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test @fecha_inicio=?, @fecha_fin=?",
                (INI, FIN_EXCLUSIVE),
            )
            raw.commit()
        except Exception:
            raw.rollback()
            raise
        finally:
            raw.close()
        for index, frame in enumerate(emission_sets, 1):
            frame.to_csv(HERE / f"emission_resultset_{index}.csv", index=False)

    with engine.connect() as conn:
        after_clays = pd.read_sql(text("SELECT * FROM inventar_SpcHidr.Clays_CuFe WHERE Fecha>=:ini AND Fecha<:fin ORDER BY Fecha,Turno,Torre"), conn, params={"ini": INI, "fin": FIN_EXCLUSIVE})
        after_reps = pd.read_sql(text("SELECT * FROM inventar_SpcHidr.representatividad_torres_resultado WHERE Dia>=:ini AND Dia<:fin ORDER BY Dia"), conn, params={"ini": INI, "fin": FIN_EXCLUSIVE})
        after_cache = pd.read_sql(text("SELECT * FROM inventar_SpcHidr.reporte_turno_cache_emision_test WHERE Fecha>=:ini AND Fecha<:fin ORDER BY Fecha,Turno"), conn, params={"ini": INI, "fin": FIN_EXCLUSIVE})
        history_count_after = conn.execute(text("SELECT COUNT_BIG(*) FROM inventar_SpcHidr.Clays_CuFe_trazabilidad")).scalar_one()
        new_history = pd.read_sql(text("""
            SELECT TOP (100) *
            FROM inventar_SpcHidr.Clays_CuFe_trazabilidad
            WHERE fecha_proceso >= (SELECT MIN(fecha_proceso) FROM inventar_SpcHidr.Clays_CuFe_trazabilidad WHERE accion='TRAZABILIDAD')
              AND accion='TRAZABILIDAD'
            ORDER BY fecha_proceso DESC,id_trazabilidad DESC
        """), conn)
        trace = pd.read_sql(text("""
            SELECT * FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
            WHERE Fecha>=:ini AND Fecha<:fin ORDER BY Fecha,Turno,TM_Destino,Analito
        """), conn, params={"ini": INI, "fin": FIN_EXCLUSIVE})

    assert_numeric_equal(before_clays, after_clays, ["CaolBeta", "CuFe"], ["Fecha", "Turno", "Torre"])
    assert_numeric_equal(before_reps, after_reps, [c for c in before_reps.columns if c not in ("Dia", "fecha_calculo")], ["Dia"])
    cache_excluded = {"Fecha_Actualizacion", "Fuente_Info_Quimica", "Fuente_Info_Fisica"}
    cache_columns = [c for c in before_cache.columns if c not in cache_excluded and c not in ("Fecha", "Turno")]
    # Compara texto y números de cache sin tolerancia, excluyendo exclusivamente fuente/auditoría.
    left = before_cache.copy(); right = after_cache.copy()
    left["Fecha"] = pd.to_datetime(left["Fecha"]); right["Fecha"] = pd.to_datetime(right["Fecha"])
    left = left.sort_values(["Fecha", "Turno"]).reset_index(drop=True)
    right = right.sort_values(["Fecha", "Turno"]).reset_index(drop=True)
    if left[["Fecha", "Turno"]].to_dict("records") != right[["Fecha", "Turno"]].to_dict("records"):
        raise AssertionError("Cambió la malla del cache operacional")
    for col in cache_columns:
        a = left[col].where(left[col].notna(), "<NULL>").astype(str)
        b = right[col].where(right[col].notna(), "<NULL>").astype(str)
        if not a.equals(b):
            raise AssertionError(f"Cambió cache operacional en {col}")

    expected = {
        ("2026-08-22", "A", "TM1"): "MB",
        ("2026-08-22", "A", "TM2"): "MB",
        ("2026-08-22", "B", "TM1"): "TM2",
        ("2026-08-22", "B", "TM2"): "TM2",
        ("2026-08-23", "A", "TM1"): "TM2",
        ("2026-08-23", "A", "TM2"): "TM2",
        ("2026-08-23", "B", "TM1"): "TM2",
        ("2026-08-23", "B", "TM2"): "TM2",
        ("2026-08-24", "A", "TM1"): "IMP",
        ("2026-08-24", "A", "TM2"): "IMP",
        ("2026-08-24", "B", "TM1"): "IMP",
        ("2026-08-24", "B", "TM2"): "IMP",
        ("2026-08-25", "A", "TM1"): "IMP",
        ("2026-08-25", "A", "TM2"): "IMP",
        ("2026-08-25", "B", "TM1"): "IMP",
        ("2026-08-25", "B", "TM2"): "IMP",
    }
    view_check = corrected_view.copy(); view_check["Fecha"] = pd.to_datetime(view_check["Fecha"]).dt.strftime("%Y-%m-%d")
    for key, source in expected.items():
        row = view_check[(view_check.Fecha == key[0]) & (view_check.Turno == key[1]) & (view_check.Torre == key[2])].iloc[0]
        actual = "TM2" if row.Fuente_CaolBeta == "NIR_TM2_COMPARTIDO" else ("TM2" if row.Fuente_CaolBeta == "NIR_PROPIO_REPRESENTATIVO" and key[2] == "TM2" else ("MB" if str(row.Fuente_CaolBeta).startswith("MB_") else "IMP"))
        if actual != source:
            raise AssertionError(f"Fuente inesperada {key}: {actual} != {source}")

    after_clays.to_csv(HERE / "clays_after.csv", index=False)
    after_reps.to_csv(HERE / "reps_after.csv", index=False)
    after_cache.to_csv(HERE / "cache_after.csv", index=False)
    new_history.to_csv(HERE / "history_source_corrections.csv", index=False)
    trace.to_csv(HERE / "trace_analitos_after.csv", index=False)
    refresh_summary = pd.read_csv(HERE / "refresh_resultset_1.csv").iloc[0]
    summary = {
        "view_rows": len(corrected_view),
        "history_rows_added": int(refresh_summary["Registros_Trazabilidad_Actualizada"]),
        "source_only_rows": int((new_history["accion"] == "TRAZABILIDAD").sum()),
        "cache_rows": len(after_cache),
        "trace_rows": len(trace),
        "numeric_view_differences": 0,
        "numeric_clays_differences": 0,
        "representativity_differences": 0,
        "operational_cache_differences": 0,
    }
    (HERE / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
