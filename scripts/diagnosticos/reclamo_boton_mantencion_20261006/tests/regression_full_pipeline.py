"""Exercise db.recalcular's exact stage order with a stateful fake connection."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from reclamo import db

HERE = Path(__file__).resolve().parents[1]

class Result:
    def scalar(self):
        return 0

class Connection:
    def __init__(self, state):
        self.state = state
        self.calls = []

    def execute(self, statement, params=None):
        sql = str(statement)
        if "sp_auto_congelar_modulos_nuevos" in sql:
            assert "@SoloPreparar = 1" in sql
            self.calls.append("PREPARAR")
            self.state["b_congelado"] = True
        elif "SELECT TOP (1) filas_afectadas" in sql:
            self.calls.append("RESUMEN_SYNC")
        elif "sp_sincronizar_desde_etl" in sql:
            self.calls.append("SYNC")
            assert self.state["b_congelado"]
            self.state["topografia_b"] = "2026-09-29"
        elif "sp_auto_mantener_secuencia" in sql:
            self.calls.append("MANTENER")
            assert self.state["topografia_b"] == "2026-09-29", "Transition preceded sync"
            self.state["a_cierre"] = self.state["topografia_b"]
            self.state["b_apertura"] = self.state["topografia_b"]
        elif "sp_cargar_cv25_horas" in sql:
            self.calls.append("CV25")
        elif "sp_calcular_reclamo_diario" in sql:
            self.calls.append("CALCULO")
        else:
            raise AssertionError(sql)
        return Result()

class Context:
    def __init__(self, conn): self.conn = conn
    def __enter__(self): return self.conn
    def __exit__(self, *args): return False

class Engine:
    def __init__(self, conn): self.conn = conn
    def begin(self): return Context(self.conn)

state = {"b_congelado": False, "topografia_b": None, "a_cierre": None, "b_apertura": None}
original = db.get_engine
try:
    runs = []
    for _ in range(2):
        conn = Connection(state)
        db.get_engine = lambda: Engine(conn)
        message = db.recalcular("2026-09-26", "2026-10-04")
        assert "Reclamo recalculado" in message
        assert conn.calls == ["PREPARAR", "SYNC", "RESUMEN_SYNC", "MANTENER",
                              "SYNC", "RESUMEN_SYNC", "CV25", "CALCULO"]
        assert state["a_cierre"] == "2026-09-29"
        assert state["b_apertura"] == "2026-09-29"
        runs.append({"calls": conn.calls, "a_cierre": state["a_cierre"],
                     "b_apertura": state["b_apertura"]})
finally:
    db.get_engine = original

result = {"result": "PASS", "scenario": "source contains B; topografia_avance initially lacks B",
          "execution_date": "2026-10-06", "runs": runs,
          "limitation": "Stateful fake verifies Python order; DEV integration remains required."}
(HERE / "regression_full_pipeline.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
