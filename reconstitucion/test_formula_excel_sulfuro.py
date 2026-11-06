"""La asignacion secuencial replica la hoja Caract_P27c11 (Control Sulfuro Camp 11).

Entradas: pivots TMH/TMS por turno, metas M134/M135 y saldo de apertura del libro.
Sin SQL. Compara cada turno contra los valores guardados del Excel.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from reconstitucion.recalibracion_adapter import _assign

FIX = Path(__file__).resolve().parents[1] / "test_fixtures" / "reconstitucion"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf8"))


def test_secuencial_reproduce_excel_m134_m135():
    f134, f135 = _load("fixture_m134_control_sulfuro.json"), _load("fixture_m135_control_sulfuro.json")
    supplies = {}
    for t in f134["turnos"] + f135["turnos"]:
        shift = "A" if t["turno"] == 4 else "B"  # turno 4 = A, 3 = B
        supplies[(pd.Timestamp(t["date"]), shift)] = (t["tmh_pivot_raw"], t["tms_pivot_raw"])
    ordered = [(d, s, *supplies[(d, s)]) for d, s in sorted(supplies, key=lambda k: (k[0], k[1]))]
    carry = f134["opening_carry"]
    mod = lambda mid, target: {"identity": {"modulo": mid}, "target": target}
    modules = [mod(133, carry["tmh"]), mod(134, f134["target_mass"]["tmh"]),
               mod(135, f135["target_mass"]["tmh"])]
    # M135 queda abierto tras su turno de cierre: sobrante al siguiente modulo.
    modules.append(mod(136, None))
    out, wet, dry = _assign(ordered, modules, None)

    def per_shift(mid):
        return {(r["fecha"], r["turno"]): r for r in out if r["modulo"] == mid}

    for fx, mid, key in ((f134, 134, "m134"), (f135, 135, "m135")):
        got = per_shift(mid)
        for t in fx["turnos"]:
            k = (pd.Timestamp(t["date"]), "A" if t["turno"] == 4 else "B")
            assert got[k]["tmh_asignada"] == pytest.approx(t["tmh_" + key], rel=1e-9, abs=1e-6), (mid, k)
            assert got[k]["tms_asignada"] == pytest.approx(t["tms_" + key], rel=1e-9, abs=1e-6), (mid, k)
    assert wet[1] == pytest.approx(f134["target_mass"]["tmh"], rel=1e-12)
    assert dry[1] == pytest.approx(f134["target_mass"]["tms"], rel=1e-9)
    assert wet[2] == pytest.approx(f135["target_mass"]["tmh"], rel=1e-12)
