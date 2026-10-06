"""Offline, read-only comparison of downloaded September workbooks."""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
DOWNLOADS = Path.home() / "Downloads"
REPORTS = {
    "analisis_tm": "Analisis_Torres_de_Muestreo_20260901_20260930",
    "datos_conciliados": "Reporte_DatosConciliados_20260901_20260930",
}

def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(Decimal(str(a)) - Decimal(str(b))) <= Decimal("0.000001")
    except (InvalidOperation, ValueError):
        return str(a) == str(b)

out = {}
for name, stem in REPORTS.items():
    files = [DOWNLOADS / f"{stem} ({n}).xlsx" for n in (34, 35)]
    if not all(f.exists() for f in files):
        out[name] = {"available": False}
        continue
    books = [openpyxl.load_workbook(f, read_only=True, data_only=True) for f in files]
    sheets = {}
    for sheet in sorted(set(books[0].sheetnames) | set(books[1].sheetnames)):
        rows = [list(wb[sheet].iter_rows(values_only=True)) if sheet in wb else [] for wb in books]
        differences = []
        for r in range(max(map(len, rows))):
            a = rows[0][r] if r < len(rows[0]) else []
            b = rows[1][r] if r < len(rows[1]) else []
            for c in range(max(len(a), len(b))):
                av, bv = (a[c] if c < len(a) else None), (b[c] if c < len(b) else None)
                if not same(av, bv):
                    differences.append({"cell": f"{openpyxl.utils.get_column_letter(c+1)}{r+1}",
                                        "file_34": str(av), "file_35": str(bv)})
        sheets[sheet] = {"differences": len(differences), "cells": differences}
    out[name] = {
        "available": True,
        "files": [{"name": f.name, "size": f.stat().st_size,
                   "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                   "modified_time": f.stat().st_mtime} for f in files],
        "sheets": sheets,
    }
    print(name, {k: v["differences"] for k, v in sheets.items()})
(HERE / "workbook_comparison.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
