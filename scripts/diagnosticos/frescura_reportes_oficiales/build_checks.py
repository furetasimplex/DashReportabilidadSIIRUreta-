"""Compare read-only evidence and the two downloaded workbooks offline."""
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
ev = json.loads((HERE / "evidencia_dev.json").read_text(encoding="utf-8"))
d = ev["results"]

def eq(a, b):
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(Decimal(str(a)) - Decimal(str(b))) <= Decimal("0.000001")
    except (InvalidOperation, ValueError):
        return str(a) == str(b)

def compare(a, b, key, columns):
    left, right = ({tuple(x[k] for k in key): x for x in rows} for rows in (a, b))
    diffs = []
    for k in sorted(left.keys() | right.keys()):
        x, y = left.get(k), right.get(k)
        if x is None or y is None:
            diffs.append({"key": k, "column": "ROW", "left": x is not None, "right": y is not None})
            continue
        for col in columns:
            if not eq(x.get(col), y.get(col)):
                diffs.append({"key": k, "column": col, "left": x.get(col), "right": y.get(col)})
    return diffs

repcols = [k for k in d["rep_live_month"][0] if k != "Dia"]
snap = {x["bloque"]: json.loads(x["payload"]) for x in d["rep_snapshot"]}
cachecols = [k for k in d["cache_month"][0] if k not in ("Fecha", "Turno", "Fecha_Actualizacion")]
wb_path = Path("C:/Users/nimun/Downloads")
files = [wb_path / f"Analisis_Torres_de_Muestreo_20260901_20260930 ({n}).xlsx" for n in (34, 35)]
wbs = [openpyxl.load_workbook(f, read_only=True, data_only=True) for f in files]
excel = {}
for name in wbs[0].sheetnames:
    aa, bb = [[list(row) for row in wb[name].iter_rows(values_only=True)] for wb in wbs]
    diffs = []
    for r in range(max(len(aa), len(bb))):
        ar = aa[r] if r < len(aa) else []
        br = bb[r] if r < len(bb) else []
        for c in range(max(len(ar), len(br))):
            av = ar[c] if c < len(ar) else None
            bv = br[c] if c < len(br) else None
            if not eq(av, bv):
                diffs.append({"cell": f"{openpyxl.utils.get_column_letter(c+1)}{r+1}", "34": str(av), "35": str(bv)})
    excel[name] = {"n_diff": len(diffs), "diffs": diffs[:100]}
    print(name, len(diffs))

cache_map = {(x["Fecha"], x["Turno"]): x for x in d["cache_month"]}
excel_cache = {}
for n, wb in zip((34, 35), wbs):
    differences = []
    compared = 0
    current_date = None
    for row in wb["Reporte por Turno"].iter_rows(values_only=True):
        if isinstance(row[2], str) and len(row[2]) == 10 and row[2][2] == "-":
            current_date = f"{row[2][6:10]}-{row[2][3:5]}-{row[2][:2]}"
        shift = {"TA": "A", "TB": "B"}.get(row[7])
        key = (current_date, shift)
        if key not in cache_map:
            continue
        compared += 1
        source = cache_map[key]
        for col, index, factor in (("Apilado_TMS_Real", 8, 1), ("STOCK", 10, 1),
                                    ("MINA", 11, 1), ("SRR", 12, 1)):
            if not eq(row[index], float(source[col]) * factor):
                differences.append({"key": key, "column": col, "excel": row[index], "cache": source[col]})
        if shift == "A":
            for col, index, factor in (("Modulo", 5, 1), ("Avance", 6, 100)):
                if not eq(row[index], float(source[col]) * factor):
                    differences.append({"key": key, "column": col, "excel": row[index], "cache": source[col]})
    excel_cache[str(n)] = {"rows_compared": compared, "n_diff": len(differences), "diffs": differences}

checks = {
    "identity": ev["identity"],
    "counts": {k: len(v) for k, v in d.items()},
    "rep_live_vs_result": compare(d["rep_live_month"], d["rep_result_month"], ("Dia",), repcols),
    "rep_snapshot_vs_result": compare(snap["rep_torres"], d["rep_result_month"], ("Dia",), repcols),
    "rep_snapshot_vs_live": compare(snap["rep_torres"], d["rep_live_month"], ("Dia",), repcols),
    "active_report": [x for x in d["rep_cab"] if x["activo"]],
    "cache_timestamp_range": [min(x["Fecha_Actualizacion"] for x in d["cache_month"]), max(x["Fecha_Actualizacion"] for x in d["cache_month"])],
    "cache_keys": {"rows": len(d["cache_month"]), "unique": len({(x["Fecha"],x["Turno"]) for x in d["cache_month"]})},
    "source_20a": d["decision_sep20"],
    "cache_20a": [x for x in d["cache_month"] if x["Fecha"] == "2026-09-20" and x["Turno"] == "A"],
    "excel_34_35": excel,
    "excel_vs_current_cache": excel_cache,
    "errors": ev["errors"],
}
(HERE / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print("rep live/result",len(checks["rep_live_vs_result"]),"snapshot/result",len(checks["rep_snapshot_vs_result"]),"snapshot/live",len(checks["rep_snapshot_vs_live"]))
