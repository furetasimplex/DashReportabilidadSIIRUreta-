"""Checks locales de la migración y del comparador de evidencia."""
import math
import unittest
from pathlib import Path

from scripts.factor_camiones_fase2a import equivalent, ROOT


class Fase2ATests(unittest.TestCase):
    def test_float_no_se_oculta(self):
        a=[{'Fecha':'2026-07-01','Factor':1.0}]
        b=[{'Fecha':'2026-07-01','Factor':math.nextafter(1.,2.)}]
        r=equivalent(a,b)
        self.assertEqual(len(r['diferencias']),1)
        self.assertEqual(r['diferencias_funcionales'],[])
        self.assertEqual(r['diferencias'][0]['antes'],1.)
        self.assertGreater(r['diferencias'][0]['diferencia_absoluta'],0)

    def test_rechaza_diferencias_funcionales_y_null(self):
        for a,b in [(1.,0.999999),(None,1.),('SIN_DATOS','OK'),(0,1)]:
            r=equivalent([{'Fecha':'2026-07-01','valor':a}],[{'Fecha':'2026-07-01','valor':b}])
            self.assertEqual(len(r['diferencias_funcionales']),1)

    def test_sin_constantes_y_contrato(self):
        calc=(ROOT/'03_sp_factor_ajuste_camiones_test.sql').read_text(encoding='utf-8')
        maintain=(ROOT/'04_sp_mantiene_factor_ajuste_camiones_v2_test.sql').read_text(encoding='utf-8')
        view=(ROOT/'05_v_ajuste_camiones_emision_test.sql').read_text(encoding='utf-8')
        for code in (calc,maintain):
            for constant in ('380.0','265.0','357.0','236.0'):
                self.assertNotIn(constant,code)
        self.assertIn('mov_cam_powerbi',calc)
        self.assertIn('cantidad<>1',calc)
        self.assertIn('d.Fecha<p.vigencia_hasta',calc)
        for fleet in ('KOM','CAT'):
            col='Limite_'+fleet+'_TMH_Viaje'
            self.assertIn('c.'+col,calc)
            self.assertIn(col+' float NOT NULL',maintain)
            self.assertIn('b.'+col,maintain)
            self.assertIn('f.'+col,view)

    def test_secciones_balance_y_camiones_intactas(self):
        baseline=Path('docs/diagnosticos/factor_camiones_fase2a/baseline_20260928_100315/sp_factor_ajuste_camiones_test.sql').read_text(encoding='utf-8')
        current=(ROOT/'03_sp_factor_ajuste_camiones_test.sql').read_text(encoding='utf-8')
        start='    ;WITH SRR_Diario AS'
        end='       7. Aplicacion de limites operacionales'
        self.assertEqual(baseline.split(start)[1].split(end)[0],current.split(start)[1].split(end)[0])


if __name__=='__main__':
    unittest.main()
