"""Ley de riego mezclada de OXIDOS (F70 refino + F81 DPLS + F60), sin SQL."""
import unittest
import numpy as np
import pandas as pd
from . import recon_engine as E


def _anchor(f81_masa, f81_fino):
    comp = {'F70': dict(masa_medida=297426.0, fino_medido=88.75),
            'F60': dict(masa_medida=0.0, fino_medido=0.0),
            'F81': dict(masa_medida=f81_masa, fino_medido=f81_fino)}
    return {'OXIDOS': dict(riego_comp=comp, riego_refino='F70')}


def _mats():
    idx = pd.date_range('2026-09-25', '2026-10-10')
    s = pd.Series(0.300, index=idx, name='cu_riego')
    riego = pd.DataFrame({'A': 10.0, 'B': 5.0}, index=idx)
    riego.loc['2026-10-03', 'A'] = 30.0            # ponderacion diaria distinta de la media simple
    s.loc['2026-10-03'] = 0.340
    return {'OXIDOS': dict(cu_riego=s, riego=riego, drena_cu=pd.DataFrame()),
            'SULFUROS': dict(cu_riego=s.copy(), riego=pd.DataFrame(), drena_cu=pd.DataFrame())}


class LeyRiegoMezclada(unittest.TestCase):
    def test_mezcla_ventana_cierra_fino_medido_de_los_flujos(self):
        a = _anchor(6877.0, 11.15)
        k = E.factor_ley_riego_mezclada(a['OXIDOS'])
        masa = 297426.0 + 6877.0
        fino_flujos = 88.75 + 11.15
        # sum(masa refino+DPLS) * ley refino * k == fino medido total (misma base de masa)
        self.assertAlmostEqual(masa * (88.75 / 297426.0) * k, fino_flujos, delta=1e-3 * fino_flujos)

    def test_k_usa_ley_refino_ponderada_por_pilas_y_cierra_exacto(self):
        m = _mats()
        a = _anchor(6877.0, 11.15)
        ws, we = '2026-10-01', '2026-10-07'
        ley_pond = E.ley_refino_ponderada_ventana(m['OXIDOS'], ws, we)
        self.assertNotAlmostEqual(ley_pond, 0.300, places=3)       # ponderada != media simple
        k = E.factor_ley_riego_mezclada(a['OXIDOS'], m['OXIDOS'], ws, we)
        ley_mezc = 1000 * (88.75 + 11.15) / (297426.0 + 6877.0)
        self.assertAlmostEqual(k, ley_mezc / ley_pond, places=10)
        out = E.aplicar_ley_riego_mezclada(m, a, ws, we)
        r = m['OXIDOS']['riego'].loc[ws:we].sum(axis=1)
        s = out['OXIDOS']['cu_riego'].loc[ws:we]
        self.assertAlmostEqual(float((r * s).sum() / r.sum()), ley_mezc, places=10)

    def test_dia_sin_ley_usa_fallback_y_tambien_cierra(self):
        m = _mats()
        m['OXIDOS']['cu_riego'].loc['2026-10-02'] = np.nan
        out = E.aplicar_ley_riego_mezclada(m, _anchor(6877.0, 11.15), '2026-10-01', '2026-10-07')
        r = m['OXIDOS']['riego'].loc['2026-10-01':'2026-10-07'].sum(axis=1)
        s = out['OXIDOS']['cu_riego'].loc['2026-10-01':'2026-10-07']
        self.assertAlmostEqual(float((r * s).sum() / r.sum()), 1000 * (88.75 + 11.15) / (297426.0 + 6877.0), places=12)

    def test_aplica_solo_en_ventana_y_solo_oxidos(self):
        m = _mats()
        out = E.aplicar_ley_riego_mezclada(m, _anchor(6877.0, 11.15), '2026-10-01', '2026-10-07')
        s = out['OXIDOS']['cu_riego']
        k = out['OXIDOS']['ley_riego_factor_mezcla']
        self.assertGreater(k, 1.0)
        base = m['OXIDOS']['cu_riego']['2026-10-01':'2026-10-07']
        self.assertTrue(np.allclose(s['2026-10-01':'2026-10-07'], base * k))
        self.assertTrue(np.allclose(s[:'2026-09-30'], 0.300))        # dias cerrados fuera de la ventana
        self.assertTrue(np.allclose(s['2026-10-08':], 0.300))
        self.assertTrue(out['SULFUROS']['cu_riego'].equals(m['SULFUROS']['cu_riego']))   # Sulfuros no cambia
        self.assertEqual(m['OXIDOS']['cu_riego']['2026-10-03'], 0.340)    # no muta la entrada

    def test_sin_f81_ni_f60_la_ley_de_refino_queda_intacta(self):
        m = _mats()
        a = _anchor(0.0, 0.0)
        self.assertIsNone(E.factor_ley_riego_mezclada(a['OXIDOS']))
        self.assertIsNone(E.factor_ley_riego_mezclada(a['OXIDOS'], m['OXIDOS'], '2026-10-01', '2026-10-07'))
        self.assertIs(E.aplicar_ley_riego_mezclada(m, a, '2026-10-01', '2026-10-07'), m)

    def test_sin_componentes_no_cambia(self):
        m = _mats()
        self.assertIs(E.aplicar_ley_riego_mezclada(m, {'OXIDOS': {}}, '2026-10-01', '2026-10-07'), m)


if __name__ == '__main__':
    unittest.main()
