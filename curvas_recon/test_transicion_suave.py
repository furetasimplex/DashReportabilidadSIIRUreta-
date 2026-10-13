import unittest
import ramp_curve as ramp


class TransicionSuave(unittest.TestCase):
    def fit(self, target, f0=.845, ages=range(30,38), qs=None):
        ages=list(ages)
        qs=qs if qs is not None else [100.]*len(ages)
        return ramp.ajustar_regimen_suave(qs,ages,target,.99,f0,30)

    def test_inherited_and_feasible_area(self):
        result=self.fit(680.)
        self.assertAlmostEqual(result['factores'][0],.845)
        self.assertAlmostEqual(result['entregado'],680.,places=8)
        self.assertAlmostEqual(result['residuo'],0.,places=8)

    def test_daily_step_bounded_up_and_down(self):
        for target in (0.,800.,-100.,1000.):
            r=self.fit(target)
            fs=[.845]+r['factores']
            self.assertTrue(all(abs(b-a)<=.03+1e-12 for a,b in zip(fs,fs[1:])))
            self.assertTrue(all(0<=f<=.99 for f in fs))

    def test_unreachable_targets_are_signed_residuals(self):
        for target in (0.,1000.):
            r=self.fit(target)
            self.assertAlmostEqual(r['residuo'],target-r['entregado'])
        self.assertLess(self.fit(0.)['residuo'],0.)
        self.assertGreater(self.fit(1000.)['residuo'],0.)

    def test_overlap_and_gap_use_calendar_age(self):
        r=self.fit(400.,ages=[30,32,36,37])
        self.assertAlmostEqual(r['factores'][0],.845)
        for a,b,da,db in zip(r['factores'],r['factores'][1:],[30,32,36],[32,36,37]):
            self.assertLessEqual(abs(b-a),.03*(db-da)+1e-12)

    def test_no_irrigation(self):
        r=self.fit(50.,qs=[0.]*8)
        self.assertEqual(r['entregado'],0.)
        self.assertEqual(r['residuo'],50.)
        self.assertEqual(r['factores'],[0.]*8)

    def test_repeat_deterministic(self):
        self.assertEqual(self.fit(680.),self.fit(680.))

    def test_reject_older_active_age(self):
        with self.assertRaises(ValueError): self.fit(50.,ages=[29])

if __name__=='__main__': unittest.main()
