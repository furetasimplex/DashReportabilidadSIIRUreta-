"""Verify required v2 outcomes from separately captured DEV evidence files."""
from __future__ import annotations
import json
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
before = json.loads((HERE / "migration_persisted.json").read_text(encoding="utf-8"))
after = json.loads((HERE / "post_reprocess_v2.json").read_text(encoding="utf-8"))
expected = json.loads((HERE / "timeline_76_80_expected.json").read_text(encoding="utf-8"))
checks = {}
checks["same_guarded_dev"] = before["identity"] == after["identity"]
checks["operational_dates_idempotent"] = before["sequence"] == after["sequence"] and after["dates_match_expected"]
checks["m14_close_m15_open_same_day"] = next(r for r in after["sequence"] if r["modulo_id"] == 78)["cierre"] == next(r for r in after["sequence"] if r["modulo_id"] == 79)["apertura"] == "2026-09-29"
checks["m16_without_invented_dates"] = all(next(r for r in after["sequence"] if r["modulo_id"] == 80)[k] is None for k in ("apertura","cierre"))
checks["no_04oct_topography"] = after["topography_04oct"] == []
checks["topography_days_retained"] = before["topography_26sep_03oct"] == after["topography_26sep_03oct"] and all(r["fuente_reclamo"] == "TOPOGRAFIA" for r in after["daily_topography"])
prelim = [r for r in after["preliminary_04oct"] if r["modulo_id"] == 79 and r["rotopala_id"] == 2]
checks["preliminary_m15_r2"] = len(prelim) == 1 and prelim[0]["fuente_reclamo"] == "PRELIMINAR_CV25" and prelim[0]["flag_preliminar"] == "OK" and Decimal(prelim[0]["tms_preliminar_dia"]) == Decimal("40157.4375") and Decimal(prelim[0]["horas_rotopala"]) == 20
checks["daily_04oct_preliminary"] = len(after["daily_04oct"]) == 1 and after["daily_04oct"][0]["modulo_id"] == 79 and after["daily_04oct"][0]["fuente_reclamo"] == "PRELIMINAR_CV25"
difference = after["difference_04oct"]
checks["cv25_04oct_not_lost"] = len(difference) == 1 and Decimal(difference[0]["tms_cv25"]) == Decimal("40157.4375") and Decimal(difference[0]["tms_topografia"]) == 0 and Decimal(difference[0]["tms_preliminar"]) == Decimal("40157.4375") and difference[0]["modulos_preliminar"] >= 1
result = {"result": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
          "before": "migration_persisted.json", "after": "post_reprocess_v2.json",
          "expected": "timeline_76_80_expected.json"}
(HERE / "v2_acceptance.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
(HERE / "timeline_76_80_after.json").write_text(json.dumps({"identity": after["identity"], "captured_utc": after["captured_utc"], "rows": after["sequence"], "dates_match_expected": after["dates_match_expected"]}, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
if result["result"] != "PASS":
    raise SystemExit(1)
