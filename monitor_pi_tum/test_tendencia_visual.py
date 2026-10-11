import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from . import panel


class TendenciaVisualTests(unittest.TestCase):
    def test_extremos_reinicio_y_huecos_sin_alterar_lecturas(self):
        y = np.arange(30000, dtype=float)
        y[800:900] = np.nan
        y[1500] = 90000
        y[1800] = -50
        frame = pd.DataFrame({'valor': y})
        before = frame.copy(deep=True)
        visual = panel._puntos_visuales(frame)
        pd.testing.assert_frame_equal(frame, before)
        pd.testing.assert_frame_equal(visual, frame.loc[visual.index])
        for index in (0, 29999, 799, 800, 899, 900, 1500, 1501, 1799, 1800):
            self.assertIn(index, visual.index)
        self.assertLess(len(visual), 6500)

    def test_indicadores_completos_y_eje_fecha(self):
        frame = pd.DataFrame(dict(timestamp=pd.date_range('2026-09-01', periods=235801, freq='10s'),
                                  valor=np.arange(235801, dtype=float), correa='CV008',
                                  fuente='tot_TM', resolucion_segundos=10, tipo_senal='TOTALIZADOR'))
        with patch.object(panel.db, 'obtener_tendencia_totalizador', return_value=frame):
            result = panel.actualizar_tendencia(1, '2026-09-01', '2026-09-29', 'CV008')
        self.assertEqual(result[1:4], ('0,00', '235.800,00', '235.800,00'))
        self.assertLessEqual(len(result[0].data[0].x), 6000)
        self.assertEqual(result[0].layout.xaxis.type, 'date')
        self.assertEqual(result[0].data[0].type, 'scatter')
        self.assertIn('Visualización resumida', str(result[4]))
        self.assertIn('235.801', str(result[4]))
        self.assertEqual(result[0].layout.separators, ',.')
        self.assertEqual(result[0].layout.xaxis.tickformat, '%d-%b')
        self.assertEqual(panel.LOCALE_ES['format']['shortMonths'][8], 'sep')
        self.assertEqual(result[0].layout.yaxis.title.text, 'Totalizador acumulado [TMH]')
        self.assertIn('%{y:,.2f}', result[0].data[0].hovertemplate)
        self.assertEqual(panel.numero_chileno(16887710), '16.887.710,00')

    def test_rango_pequeno_no_se_reduce(self):
        frame = pd.DataFrame({'valor': [1, np.nan, 0, 5]})
        pd.testing.assert_frame_equal(panel._puntos_visuales(frame), frame)
