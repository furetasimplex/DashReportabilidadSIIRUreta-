"""Exercise only Reclamo SELECT helpers after adding operational campaign labels."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import db

result = {}
for name, call in {
    "cuadratura": db.cuadratura,
    "avance_diario": lambda: db.avance_diario("2026-10-01", "2026-10-06"),
    "vista_previa": lambda: db.vista_previa_conciliados("2026-10-01", "2026-10-06"),
    "ajustes": lambda: db.ajustes("2026-10-01", "2026-10-06"),
    "modulos": db.modulos_disponibles,
    "alertas": db.alertas_automatizacion,
    "rendimiento": lambda: db.rendimiento("2026-10-01", "2026-10-06"),
}.items():
    try:
        df = call()
        result[name] = {"rows": len(df), "columns": df.columns.tolist(), "campana_missing":
                        int(df["campana"].isna().sum()) if "campana" in df else None}
    except Exception as exc:
        result[name] = {"error": str(exc)}
Path(__file__).with_name("reads.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: {k: v for k, v in value.items() if k != "columns"} for key,value in result.items()}, ensure_ascii=False))
if any("error" in value for value in result.values()):
    raise SystemExit(1)
