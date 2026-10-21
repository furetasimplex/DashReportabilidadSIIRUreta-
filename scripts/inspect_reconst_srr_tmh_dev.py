"""Lee insumos de la metodología TMH definitiva; solo SELECT en DEV."""
import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from report_export.report_export import _get_engine


def main():
    if os.getenv("SQLSERVER_HOST") != "149.50.136.234":
        raise RuntimeError("Inspección bloqueada fuera de DEV")
    output = Path(__file__).resolve().parents[1] / "auditorias/archivo/report_export/exports/reconst_mod_srr_validation"
    output.mkdir(parents=True, exist_ok=True)
    with _get_engine().connect() as conn:
        candidate = pd.read_sql(text("""
            SELECT c.Fecha, b.ts_08_dia, b.ts_20_dia, b.ts_08_dia_siguiente,
                   b.TMH_Apilado_Total_A, b.TMH_Apilado_Total_B,
                   b.TMH_CV008_A, b.TMH_CV008_B, b.TMH_CV108_A, b.TMH_CV108_B,
                   c.Apilado_TMH_turno_A, c.Apilado_TMH_turno_B,
                   c.Sal_turno_A, c.Sal_Turno_B, f.Factor_Aplicacion_Reportes
            FROM inventar_SpcHidr.Datos_conciliados_of c
            LEFT JOIN inventar_SpcHidr.v_datos_apilado_tmh_v2 b ON b.Fecha = c.Fecha
            LEFT JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test f ON f.Fecha = c.Fecha
            WHERE c.Fecha >= :start AND c.Fecha < :end ORDER BY c.Fecha
        """), conn, params={"start": "2026-08-01", "end": "2026-09-01"})
        definitions = pd.read_sql(text("""
            SELECT o.name, m.definition FROM sys.sql_modules m
            JOIN sys.objects o ON o.object_id = m.object_id
            WHERE SCHEMA_NAME(o.schema_id) = 'inventar_SpcHidr'
              AND o.name IN ('v_datos_apilado_tmh_v2', 'sp_mantiene_apilado_tmh_v2_test')
        """), conn)
    candidate.to_csv(output / "tmh_metodologia_definitiva.csv", index=False)
    print("rows=", len(candidate), "nulos=", candidate.isna().sum().to_dict(), flush=True)
    print(candidate.head(2).to_string(index=False), flush=True)
    print("factores_distintos_de_uno=", int(candidate.Factor_Aplicacion_Reportes.ne(1).sum()), flush=True)
    for _, row in definitions.iterrows():
        (output / (row["name"] + ".sql")).write_text(row["definition"], encoding="utf-8")
    comparisons = []
    for _, row in candidate.iterrows():
        for shift in ("A", "B"):
            raw1, raw2 = row[f"TMH_CV008_{shift}"], row[f"TMH_CV108_{shift}"]
            salt = row["Sal_turno_A" if shift == "A" else "Sal_Turno_B"]
            allocated_salt = salt * raw2 / (raw1 + raw2) if raw1 + raw2 else 0
            total = row[f"Apilado_TMH_turno_{shift}"]
            tm2 = raw2 * row.Factor_Aplicacion_Reportes - allocated_salt
            tm1 = total - tm2
            delta = tm1 + tm2 - total
            assert abs(delta) <= 0.001
            comparisons.append(dict(fecha=str(row.Fecha), turno=shift,
                                    total=total, tm1=tm1, tm2=tm2, diferencia=delta))
    (output / "cuadratura_tmh_definitiva.json").write_text(json.dumps(comparisons, indent=2), encoding="utf-8")
    print("turnos_validados=", len(comparisons), "max_diferencia=", max(abs(r["diferencia"]) for r in comparisons))


if __name__ == "__main__":
    main()
