import unittest
from copy import deepcopy
from datetime import date, timedelta
from curvas_recon.sulfide_method import reconcile_sulfides


def cohort(birth='2026-09-01', pile='P', start=date(2026, 8, 31), days=8):
    return [dict(pad='SULFUROS', pile=pile, campaign=1, date=(start + timedelta(days=i)).isoformat(),
                 first_irrigation=birth, official_pct=10, observed_pct=12, cu_apilado_t=100,
                 q_riego_m3h=100, cu_riego_gL=1, cu_drenaje_gL=2, profile_q_drenaje_m3h=50)
            for i in range(days)]


class SulfideMethodTests(unittest.TestCase):
    def test_young_net_closes_without_mutating(self):
        rows = cohort()
        original = deepcopy(rows)
        out, audit = reconcile_sulfides(rows, '2026-09-01', '2026-09-07', 0)
        self.assertAlmostEqual(audit['lambda'], 1)
        self.assertAlmostEqual(audit['curve_net_t'], 0)
        self.assertEqual(rows, original)
        self.assertEqual(out[0], original[0])

    def test_exactly_30_days_is_adjustable(self):
        rows = cohort('2026-08-08')
        out, audit = reconcile_sulfides(rows, '2026-09-01', '2026-09-07', 0)
        self.assertEqual(len(audit['young']), 1)
        self.assertEqual(audit['mature'], [])
        self.assertAlmostEqual(audit['lambda'], 1)

    def test_over_30_days_without_young_requires_closure(self):
        rows = cohort('2026-08-07')
        for row in rows[1:]: row['observed_pct'] = 12
        out, audit = reconcile_sulfides(rows, '2026-09-01', '2026-09-07', 2)
        self.assertIsNone(audit['lambda'])
        self.assertEqual(out[-1]['reconciled_pct'], 12)
        with self.assertRaises(ValueError):
            reconcile_sulfides(rows, '2026-09-01', '2026-09-07', 3)

    def test_mature_observed_not_fictitious_flow(self):
        rows = cohort('2026-08-01')
        out, audit = reconcile_sulfides(rows, '2026-09-01', '2026-09-07', 2)
        self.assertEqual(out[-1]['reconciled_pct'], 12)
        self.assertNotIn('fitted_q_drenaje_m3h', out[-1])
        self.assertEqual(len(audit['mature']), 1)

    def test_later_window_uses_day_before_and_preserves_history(self):
        rows = cohort('2026-08-01', start=date(2026, 7, 31), days=15)
        out, audit = reconcile_sulfides(rows, '2026-08-07', '2026-08-14', 0)
        self.assertEqual(out[:7], rows[:7])
        self.assertEqual(audit['water_by_young'][('SULFUROS', 'P', 1)]['irrigation_m3'], 19200)

    def test_invalid_missing_and_infeasible(self):
        rows = cohort()
        for changed, target in ((rows[:-1], 0), (rows, -100), (rows, 10000)):
            with self.subTest(target=target, count=len(changed)), self.assertRaises(ValueError):
                reconcile_sulfides(changed, '2026-09-01', '2026-09-07', target)


if __name__ == '__main__':
    unittest.main()
