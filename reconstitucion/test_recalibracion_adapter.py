"""Offline adapter checks using the fresh Case 10013 SELECT snapshot."""
import json
from pathlib import Path
import unittest

import pandas as pd

from recalibracion_adapter import _assign, _profile_turns, apply_recalibrated_distribution
from recalibracion_mr import RecalibrationError


HERE = Path(__file__).resolve().parent


class AdapterTests(unittest.TestCase):
    def test_zero_wet_profile_allows_missing_humidity_but_positive_wet_does_not(self):
        frame = pd.DataFrame([{"fecha": "2026-10-01", "turno": "A", "tm": "TM1",
                               "tmh": 0.0, "humedad": None, "fuente": "TUM"}])
        self.assertEqual(_profile_turns(frame).iloc[0].tms, 0.0)
        frame.loc[0, "tmh"] = 10.0
        with self.assertRaisesRegex(RecalibrationError, "TMH positiva"):
            _profile_turns(frame)

    def test_unresolved_source_is_rejected(self):
        frame = pd.DataFrame([{"fecha": "2026-10-01", "turno": "A", "tm": "TM1",
                               "tmh": 10.0, "humedad": 3.0, "fuente": "SIN_RESOLVER"}])
        with self.assertRaisesRegex(RecalibrationError, "SIN_RESOLVER"):
            _profile_turns(frame)

    def test_residual_moves_to_next_module_and_dry_fraction_is_equal(self):
        modules = [{"identity": {"modulo": 1}, "target": 6.0},
                   {"identity": {"modulo": 2}, "target": None}]
        allocated, wet, dry = _assign([(pd.Timestamp("2026-10-01"), "A", 10.0, 8.0)],
                                      modules, pd.Timestamp("2026-10-01"))
        self.assertEqual(wet, [6.0, 4.0])
        self.assertEqual(dry, [4.8, 3.2])
        self.assertEqual([r["modulo"] for r in allocated], [1, 2])

    def test_case_snapshot_reconstitutes_only_current_case_mass(self):
        snapshot = json.loads((HERE.parent / "test_fixtures" / "reconstitucion" / "RUNTIME_BASELINE_SNAPSHOT.json").read_text(encoding="utf8"))
        frames = {name: pd.DataFrame(rows) for name, rows in snapshot["frames"].items()}
        result = {"apilado": frames["apilado"], "masa": frames["masa"],
                  "masa_por_pad": frames["masa_por_pad"], "shift_table": frames["shift_table"],
                  "sem": tuple(snapshot["sem"]), "fuente_modelo": snapshot["source_modelo"]}
        out = apply_recalibrated_distribution(result, snapshot["history"],
            pd.DataFrame(snapshot["profile"]), snapshot["fixed"], snapshot["case"])
        st = out["shift_table"]
        source = frames["masa_por_pad"]
        check = st.groupby(["fecha", "pad_id"])[["masa_turno1", "masa_turno2"]].sum()
        source["fecha"] = pd.to_datetime(source.fecha).dt.normalize()
        for row in source.itertuples(index=False):
            if row.TMS_T1 == 0 and row.TMS_T2 == 0:
                continue
            actual = check.loc[(row.fecha, row.pad_id)]
            self.assertAlmostEqual(actual.masa_turno1, row.TMS_T1, places=5)
            self.assertAlmostEqual(actual.masa_turno2, row.TMS_T2, places=5)
        self.assertTrue(st.metodo_reparto.eq("SECUENCIAL_DENSIDAD_RECALIBRADA_DB").all())
        self.assertGreater(len(out["module_timeline"]), 0)
        self.assertTrue(out["module_timeline"].resolucion.str.contains("estimado_uniforme_12h").all())
        self.assertAlmostEqual(st.masa_total.sum(), 728062.4073, places=3)
        self.assertAlmostEqual(out["recalibracion_mr"].iloc[0].density_tmh_per_m3,
                               1.8495982341, places=8)


if __name__ == "__main__":
    unittest.main()
