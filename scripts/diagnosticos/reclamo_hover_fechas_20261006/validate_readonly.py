"""SELECT-only comparison of original quadrature figures and new movement dates."""
import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import db
from reclamo import panel

old_sql = """SELECT [campaña_id] AS campana_id, pad_id, modulo_id, modulo_numero,
    m3_totales, m3_camiones_total, m3_rotopala_total, m3_extraido_total,
    porcentaje_extraido, tms_camiones_total, tms_rotopala_total, tms_extraido_total,
    tms_saldo_disponible, m3_excedente, tms_excedente
    FROM reclamo.v_cuadratura_modulo"""
with db.get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name")).mappings().one())
    if identity["database_name"].lower() != "inventar_spchidr":
        raise RuntimeError("Expected DEV database")
    old = [dict(r) for r in conn.execute(text(old_sql)).mappings()]
new = db.cuadratura()
key = lambda r: (int(r["campana_id"]), int(r["modulo_id"]))
old_by_key = {key(r): r for r in old}
new_by_key = {key(r): r for _, r in new.iterrows()}
columns = ["pad_id", "modulo_numero", "m3_totales", "m3_camiones_total", "m3_rotopala_total",
           "m3_extraido_total", "porcentaje_extraido", "tms_camiones_total", "tms_rotopala_total",
           "tms_extraido_total", "tms_saldo_disponible", "m3_excedente", "tms_excedente"]
different = []
for k in sorted(set(old_by_key) | set(new_by_key)):
    if k not in old_by_key or k not in new_by_key:
        different.append({"key": k, "reason": "missing row"})
        continue
    for col in columns:
        a, b = old_by_key[k][col], new_by_key[k][col]
        if (a is None) != bool(__import__("pandas").isna(b)) or (a is not None and float(a) != float(b)):
            different.append({"key": k, "column": col, "before": str(a), "after": str(b)})
samples = []
figure_checks = {}
original_cuadratura = panel.db.cuadratura
panel.db.cuadratura = lambda: new.copy()
try:
    for pad in (1, 2):
        figure, _ = panel.cb_cuadratura(0, None, str(pad))
        expected = new[new["pad_id"] == pad].sort_values(["campana", "modulo_numero"]).head(40)
        figure_checks[str(pad)] = {
            "three_original_traces": [t.name for t in figure.data] == ["Camiones", "Rotopala", "Volumen congelado"],
            "camiones_unchanged": [float(v) for v in figure.data[0].y] == [float(v) for v in expected["m3_camiones_total"]],
            "rotopala_unchanged": [float(v) for v in figure.data[1].y] == [float(v) for v in expected["m3_rotopala_total"]],
            "volumen_unchanged": [float(v) for v in figure.data[2].y] == [float(v) for v in expected["m3_totales"]],
            "dates_in_hover": "Fecha inicio" in figure.data[2].hovertemplate and "Fecha fin" in figure.data[2].hovertemplate,
        }
finally:
    panel.db.cuadratura = original_cuadratura
for pad in (1, 2):
    rows = new[(new["pad_id"] == pad) & new["fecha_inicio_movimiento"].notna()]
    if not rows.empty:
        r = rows.iloc[0]
        samples.append({"pad_id": pad, "campana_id": int(r["campana_id"]), "modulo_id": int(r["modulo_id"]),
                        "inicio": str(r["fecha_inicio_movimiento"]), "fin": str(r["fecha_fin_movimiento"])})
result = {"identity": identity, "rows_before": len(old), "rows_after": len(new),
          "numeric_columns_checked": columns, "numeric_differences": different, "samples": samples,
          "figure_checks": figure_checks,
          "pass": not different and len(old) == len(new) and len(samples) == 2
                  and all(all(checks.values()) for checks in figure_checks.values()),
          "sql_write_executed": False}
Path(__file__).with_name("validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if not result["pass"]:
    raise SystemExit(1)
