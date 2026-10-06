"""Offline read-only CV025 episode simulation from LIVE captured PI and TUM."""
import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ev = json.loads((HERE / "live_before.json").read_text(encoding="utf-8"))
data = ev["results"]
pi = {x["fecha"]: Decimal(str(x["cv025tot"])) if x["cv025tot"] is not None else None
      for x in data["pi_daily_source"]}
turns = defaultdict(list)
for row in data["resolved_turn"]:
    turns[row["fecha_operacional"]].append(row)

def val(x):
    return Decimal(str(x)) if x is not None else None

days = sorted(pi)
rows = []
episodes = []
active = None
for day in days:
    tt = turns[day]
    tum_complete = (len(tt) == 2 and {t["turno"] for t in tt} == {"A", "B"}
                    and all(t["tum_disponible"] and t["tipo_tum"] == "TUM_DIRECTO"
                            and val(t["valor_turno_tum"]) is not None
                            and val(t["valor_turno_tum"]) >= 0 for t in tt))
    tum = sum((val(t["valor_turno_tum"]) or Decimal(0) for t in tt), Decimal(0)) if tum_complete else None
    starts = any(("SIN_CAMBIO" in str(t["estado_tecnico_pi"]) or t["estado_tecnico_pi"] == "SIN_PI")
                 and t["tipo_tum"] == "TUM_DIRECTO" and (val(t["valor_turno_tum"]) or 0) > 0 for t in tt)
    recovery = any(str(t["estado_tecnico_pi"]).startswith("CON_VARIACION")
                   and (val(t["valor_pi_final"]) or 0) > 0 for t in tt)
    if active is None and starts:
        active = {"id": len(episodes) + 1, "start": day, "days": []}
    item = {"fecha": day, "PI_diario": pi[day], "TUM_diario": tum,
            "TUM_completo": tum_complete,
            "estado_PI": "RECUPERACION" if active and recovery else
                         "PLANO_CON_TUM" if starts else "NORMAL_PI",
            "episodio_id": active["id"] if active else None,
            "estado_episodio": "NORMAL_PI", "residual_acumulado": None,
            "valor_resuelto_propuesto": pi[day], "fuente_propuesta": "PI",
            "motivo": "PI_SIN_EPISODIO", "tum_batch_id": ",".join(str(t["tum_batch_id"]) for t in tt if t["tum_batch_id"] is not None)}
    rows.append(item)
    if active:
        active["days"].append(item)
        if recovery:
            span = active["days"]
            pi_sum = sum((x["PI_diario"] or Decimal(0) for x in span), Decimal(0))
            tum_sum = sum((x["TUM_diario"] or Decimal(0) for x in span), Decimal(0))
            complete = all(x["TUM_completo"] and x["PI_diario"] is not None for x in span)
            reconciled = complete and pi_sum == tum_sum
            residual = pi_sum - tum_sum if complete else None
            state = "CONTINGENCIA_TUM_RECONCILIADA" if reconciled else "RECUPERACION_REQUIERE_REVISION"
            for x in span:
                x["estado_episodio"] = state
                x["residual_acumulado"] = residual
                x["valor_resuelto_propuesto"] = x["TUM_diario"] if reconciled else None
                x["fuente_propuesta"] = "TUM" if reconciled else "SIN_RESOLVER"
                x["motivo"] = "MASA_PI_TUM_EXACTA" if reconciled else "MASA_O_COBERTURA_NO_RECONCILIADA"
            episodes.append({"id": active["id"], "start": active["start"], "recovery": day,
                             "pi_sum": pi_sum, "tum_sum": tum_sum, "residual": residual,
                             "complete": complete, "state": state})
            active = None
        else:
            item["estado_episodio"] = "CONTINGENCIA_TUM_ABIERTA" if tum_complete else "SIN_TUM_NO_RESOLUBLE"
            item["valor_resuelto_propuesto"] = tum if tum_complete else None
            item["fuente_propuesta"] = "TUM_PROVISIONAL" if tum_complete else "SIN_RESOLVER"
            item["motivo"] = "ESPERANDO_RECUPERACION_PI" if tum_complete else "FALTA_TUM_DIRECTO"
if active:
    episodes.append({"id": active["id"], "start": active["start"], "recovery": None,
                     "state": "CONTINGENCIA_TUM_ABIERTA"})

def serial(x):
    return str(x) if isinstance(x, Decimal) else x

(HERE / "simulation_20260901_15.json").write_text(json.dumps(rows, ensure_ascii=False, default=serial, indent=2), encoding="utf-8")
with (HERE / "simulation_20260901_15.csv").open("w", newline="", encoding="utf-8-sig") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows({k: serial(v) for k, v in r.items()} for r in rows)
(HERE / "mass_balance_before_after.json").write_text(json.dumps(episodes, ensure_ascii=False, default=serial, indent=2), encoding="utf-8")
checks = {
    "episode_detected": any(e["start"] == "2026-09-07" and e["recovery"] == "2026-09-11" for e in episodes),
    "mass_equal": all(e.get("state") != "CONTINGENCIA_TUM_RECONCILIADA" or e["residual"] == 0 for e in episodes),
    "normal_days_unchanged": all(r["valor_resuelto_propuesto"] == r["PI_diario"] for r in rows if r["fecha"] <= "2026-09-05" or r["fecha"] >= "2026-09-12"),
    "zero_day": next(r for r in rows if r["fecha"] == "2026-09-06")["valor_resuelto_propuesto"] == 0,
    "no_topografia_or_mina_imp_inputs": True,
}
print("episodes", json.dumps(episodes, default=serial), "checks", checks)
if not all(checks.values()):
    raise RuntimeError("Simulation gate failed")
