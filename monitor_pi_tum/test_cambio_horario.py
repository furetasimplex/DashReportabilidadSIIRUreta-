"""Regresión 05-09-2026 B: 11 lecturas no implican turno incompleto.

Ejecutar con --dev para comprobar también los datos y el resolvedor SQL activos.
Los conteos abajo identifican el caso histórico; NO son criterios de validez.
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from sqlalchemy import text
from . import panel, db
from .inspect_dev import engine_dev
from .operational_sql import preview_sql

LIVE_DEV = '--dev' in sys.argv
if LIVE_DEV:
    sys.argv.remove('--dev')


class CambioHorarioTests(unittest.TestCase):
    def test_turno_20260905_b_con_11_lecturas_no_se_rechaza_ni_rellena(self):
        # Timestamps locales observados: no se fabrica la medianoche inexistente.
        horas = pd.to_datetime([
            '2026-09-05 20:00', '2026-09-05 21:00', '2026-09-05 22:00', '2026-09-05 23:00',
            '2026-09-06 01:00', '2026-09-06 02:00', '2026-09-06 03:00', '2026-09-06 04:00',
            '2026-09-06 05:00', '2026-09-06 06:00', '2026-09-06 07:00',
        ])
        frame = pd.DataFrame(dict(timestamp=horas, valor=[0.0]*11, correa='CV001',
                                  fuente='datos_filtrados', resolucion_segundos=3600, tipo_senal='TOTALIZADOR'))
        with patch.object(panel.db, 'obtener_tendencia_totalizador', return_value=frame):
            result = panel.actualizar_tendencia(1, '2026-09-05', '2026-09-06', 'CV001')
        self.assertEqual(result[1:4], ('0.00', '0.00', '0.00'))
        self.assertEqual(result[-1], '')
        self.assertEqual(list(pd.to_datetime(result[0].data[0].x)), list(horas))
        self.assertEqual(len(result[0].data[0].y), 11)

    @unittest.skipUnless(LIVE_DEV, 'Lectura SQL DEV explícita: ejecutar con --dev')
    def test_turno_20260905_b_real_no_invalidado_por_11_registros(self):
        with engine_dev().connect() as conn:
            horarios = conn.execute(text('''SELECT fecha_inicial
                FROM inventar_SpcHidr.datos_filtrados
                WHERE fecha_inicial >= :inicio AND fecha_inicial < :fin
                ORDER BY fecha_inicial'''),
                {'inicio':'2026-09-05T20:00:00', 'fin':'2026-09-06T08:00:00'}).scalars().all()
            dia = conn.execute(text('''SELECT fecha_inicial
                FROM inventar_SpcHidr.datos_filtrados
                WHERE fecha_inicial >= :inicio AND fecha_inicial < :fin
                ORDER BY fecha_inicial'''),
                {'inicio':'2026-09-06T00:00:00', 'fin':'2026-09-07T00:00:00'}).scalars().all()
            # Confirma la evidencia histórica, sin usarla para autorizar/rechazar PI.
            self.assertEqual(len(horarios), 11)
            self.assertEqual(len(dia), 23)
            self.assertNotIn(pd.Timestamp('2026-09-06 00:00'), horarios)
            i = horarios.index(pd.Timestamp('2026-09-05 23:00'))
            self.assertEqual(horarios[i+1], pd.Timestamp('2026-09-06 01:00'))
            resultados = []
            for estado in ('OPERATIVO', 'MANTENCION'):
                rows = conn.execute(text(preview_sql()),
                                    {'fecha':'2026-09-05', 'turno':'B', 'estado':estado}).mappings().all()
                self.assertTrue(rows, 'Falta el turno en el resolvedor activo')
                con_pi = [r for r in rows if r['valor_pi_final'] is not None]
                # Los siete equipos tienen PI en este caso real verificado.
                # Si una futura regla de 12 muestras invalida cualquiera, el test falla.
                self.assertEqual({r['equipo_codigo'] for r in con_pi}, set(db.EQUIPOS))
                for r in rows:
                    if r['valor_pi_final'] is not None:
                        self.assertEqual(r['fuente_resuelta'], 'PI')
                        self.assertEqual(r['estado_resolucion'], 'RESUELTO')
                        self.assertEqual(r['valor_final_resuelto'], r['valor_pi_final'])
                    else:
                        # Una falta real de PI sigue pendiente: no se declara válido a ciegas.
                        self.assertIsNone(r['fuente_resuelta'])
                        self.assertEqual(r['estado_resolucion'], 'PENDIENTE_PI')
                    resultados.append({k:r[k] for k in ('equipo_codigo','estado_operacional',
                        'estado_tecnico_pi','estado_fronteras','valor_pi_final','fuente_resuelta','estado_resolucion')})
        reporte = {'fecha_operacional':'2026-09-05', 'turno':'B',
                   'timestamps_turno':[str(t) for t in horarios], 'registros_dia_20260906':len(dia),
                   'resultados':resultados, 'solo_lectura_dev':True}
        (Path(__file__).parent / 'validacion/cambio_horario_20260905_B.json').write_text(
            json.dumps(reporte, default=str, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    unittest.main(verbosity=2)
