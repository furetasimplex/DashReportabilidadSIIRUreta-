"""Casos de cierre sobre evidencia DEV congelada y contrato real de filtrado."""
import json
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
from . import postprocesar_tum_contingencia as post
from .test_postprocesar_tum_contingencia import Resultado

ROOT=Path(__file__).parent/'validacion/expansion_v1/cierre'

class CierreExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ro=json.loads((ROOT/'RO.json').read_text(encoding='utf-8'))
        cls.rt=json.loads((ROOT/'RT.json').read_text(encoding='utf-8'))

    def rows(self,date,equipo):
        return [r for r in self.ro if r['fecha_operacional']==date and r['equipo_codigo']==equipo]

    def test_normal_pi_cero(self):
        rows=[r for r in self.ro if r['fecha_operacional']=='2026-09-13' and r['equipo_codigo'] in ('SRR_CV002','SRR_CV003') and Decimal(r['valor_pi_final'])==0]
        self.assertEqual(len(rows),3)
        for r in rows:
            self.assertEqual(r['fuente_resuelta'],'PI')
            self.assertEqual(Decimal(r['valor_final_resuelto']),0)
            self.assertEqual(r['fuente_resuelta_legacy'],'TUM')

    def test_contingencia_tum(self):
        for r in self.rows('2026-09-10','RIPIOS_CV025'):
            self.assertTrue(r['contingencia_pi_activa'])
            self.assertEqual(r['fuente_resuelta'],'TUM')
            self.assertEqual(r['valor_final_resuelto'],r['valor_turno_tum'])

    def test_pendiente_sin_pi_ni_cero(self):
        r=self.rows('2026-09-08','RIPIOS_CV025')[1]
        self.assertTrue(r['contingencia_pi_activa'])
        self.assertIsNone(r['valor_turno_tum'])
        self.assertIsNone(r['valor_final_resuelto'])
        self.assertEqual(r['fuente_resuelta'],'PENDIENTE_TUM')

    def test_siete_equipos_cada_turno(self):
        for date in ('2026-09-07','2026-09-08','2026-09-10','2026-09-13'):
            for turno in ('A','B'):
                self.assertEqual({r['equipo_codigo'] for r in self.ro if r['fecha_operacional']==date and r['turno']==turno},set(post.EQUIPOS))

    def test_cv025_mixto(self):
        a,b=self.rows('2026-09-07','RIPIOS_CV025')
        self.assertFalse(a['contingencia_pi_activa'])
        self.assertTrue(b['contingencia_pi_activa'])
        self.assertEqual((Decimal(a['valor_final_resuelto'])+Decimal(b['valor_final_resuelto']))*Decimal('.90'),Decimal('28248.3'))

    def test_pre_cutover_fuera_ro_con_rt_completo(self):
        self.assertEqual(sum(r['fecha_operacional']=='2026-08-31' for r in self.rt),14)
        self.assertFalse(any(r['fecha_operacional']=='2026-08-31' for r in self.ro))

    def test_postproceso_respeta_template_srr(self):
        self.check_template('informe_tum_srr','SRR_CV001')

    def test_postproceso_respeta_template_seca(self):
        self.check_template('informe_tum_seca','PRINCIPAL_CV008')

    def test_postproceso_respeta_template_ripios(self):
        self.check_template('informe_tum_ripios','RIPIOS_CV025')

    def check_template(self,template,equipo):
        conn=MagicMock()
        def execute(sql,params):
            if 'import_batch' in str(sql):
                return Resultado(first={'id':1,'estado':'committed','template_code':template})
            if 'import_row_history' in str(sql):
                rows=[{'fecha_operacional':'2026-09-10','turno':'A','equipo_codigo':equipo}] if params['template']==template else []
                return Resultado(all_rows=rows)
            return Resultado(scalar=True)
        conn.execute.side_effect=execute
        self.assertEqual(post.planificar(conn,1).cambios,1)
