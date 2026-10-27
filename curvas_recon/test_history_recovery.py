import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from history_recovery import (build_readonly_query, calendar_rows,
                              load_validated_official_history, normalize_history_rows,
                              official_history_calendar, reconciled_increment_tcu)


class HistoryRecoveryTests(unittest.TestCase):
    def test_daily_net_uses_separate_reconciled_flows(self):
        row = {"q": 2.0, "q_pls": 3.0, "cu_riego": 0.2,
               "cu_drena": 1.0, "fdrena": 0.1}
        self.assertAlmostEqual(reconciled_increment_tcu(row), 0.0624)

    def test_zero_flows_have_zero_contribution_even_without_cu(self):
        self.assertEqual(reconciled_increment_tcu(
            {"q": 0, "q_pls": 0, "cu_riego": None, "cu_drena": None}), 0.0)

    def test_missing_positive_flow_inputs_remain_gap(self):
        self.assertIsNone(reconciled_increment_tcu(
            {"q": 0, "q_pls": 1, "cu_riego": None, "cu_drena": None}))
        self.assertIsNone(reconciled_increment_tcu(
            {"q": None, "q_pls": 0, "cu_riego": 1, "cu_drena": 1}))

    def test_filter_official_125_case_and_pre_case_dates(self):
        cases = {7: {"modelo_codigo": "hidrometalurgia_125_v2",
                     "modelo_version": "v2", "total_flujos": 125,
                     "fecha_inicio": "2026-09-01", "fecha_fin": "2026-09-30"}}
        base = {"date": "2026-09-30", "semana_lunes": "2026-09-28",
                "label": "OXIDOS", "parcela_nombre": "P01", "caso_id": 7,
                "run_id": 11, "q": 0, "q_pls": 0}
        rows = [base, {**base, "date": "2026-10-01"},
                {**base, "caso_id": 8}, {**base, "run_id": 9}]
        clean = normalize_history_rows(rows, "2026-10-01", official_cases=cases)
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["date"], date(2026, 9, 30))
        self.assertEqual(clean[0]["increment_tcu"], 0.0)

    def test_calendar_gap_is_explicit_none(self):
        row = {"date": date(2026, 9, 30), "semana_lunes": date(2026, 9, 28),
               "label": "OXIDOS", "parcela_nombre": "P01", "caso_id": 1,
               "run_id": 2, "q": 0, "q_pls": 0}
        normalized = normalize_history_rows([row], "2026-10-01")
        series = calendar_rows(normalized, "OXIDOS", "P01",
                               "2026-09-29", "2026-09-30")
        self.assertTrue(series[0]["gap"])
        self.assertIsNone(series[0]["reconciled_increment_tcu"])
        self.assertFalse(series[1]["gap"])

    def test_query_is_select_only_and_ranks_only_eligible_runs(self):
        query = str(build_readonly_query("inventar_SpcHidr", "PROD_SIIR.hidro"))
        self.assertIn("official_cases AS", query)
        self.assertIn("rr.converged = 1", query)
        self.assertIn("PARTITION BY rr.caso_id, rr.semana_lunes", query)
        self.assertNotIn("INSERT", query.upper())
        self.assertNotIn("DELETE", query.upper())
        self.assertNotIn("UPDATE", query.upper())

    def test_official_history_fixture_hash_and_pre_case_window(self):
        fixture = (Path(__file__).parent / "test_fixtures"
                   / "historico_oficial_validado_20260901_20261001.csv")
        rows = load_validated_official_history(fixture, "2026-10-01")
        self.assertEqual(len(rows), 1144)
        p1 = official_history_calendar(rows, "OXIDOS", "P01",
                                       "2026-08-31", "2026-09-02")
        self.assertIsNone(p1[0]["value_pct"])
        self.assertEqual(p1[0]["source"], None)
        self.assertIsNotNone(p1[1]["value_pct"])
        self.assertEqual(p1[1]["source"], "Histórico reconciliado oficial")


if __name__ == "__main__":
    unittest.main()
