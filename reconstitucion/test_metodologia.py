import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    from . import engine as e, db_source as db, validacion as v
except ImportError:
    from reconstitucion import engine as e, db_source as db, validacion as v
from unittest.mock import patch

def apilado(n=7, volumen=1000):
    return e.mark_status(pd.DataFrame({'fecha':pd.date_range('2026-08-03',periods=n),
        'pad_id':2,'campana':1,'modulo':1,'avance':1.0,'vol_diario':volumen,
        'vol_acum_final':np.arange(1,n+1)*volumen,'vol_total_est':n*volumen}))
def masa(n=7,tms=1800):
    return pd.DataFrame({'fecha':pd.date_range('2026-08-03',periods=n),'TMS':tms,
        'TMH':tms,'H_op':10.0,'H_op_src':'torre','TMS_T1':tms/2,'TMS_T2':tms/2})

class Metodo(unittest.TestCase):
    def test_detencion_turno_no_recibe_masa(self):
        m=masa(1);m['TMS_T1']=0;m['TMS_T2']=m.TMS
        st=e.shift_table(apilado(1),db.preparar_frontera(m))
        self.assertEqual(st.masa_turno1.iloc[0],0)
        self.assertEqual(st.masa_turno2.iloc[0],1800)
        m['TMS_T1']=m.TMS;m['TMS_T2']=0
        st=e.shift_table(apilado(1),db.preparar_frontera(m))
        self.assertEqual(st.masa_turno2.iloc[0],0)
    def test_desajuste_conserva_total_y_etiqueta_estimacion(self):
        m=masa(1);m['TMS_T1']=600;m['TMS_T2']=300
        st=e.shift_table(apilado(1),db.preparar_frontera(m))
        self.assertAlmostEqual(st.masa_turno1.iloc[0],1200)
        self.assertAlmostEqual(st.masa_total.sum(),1800)
        self.assertEqual(st.frontera_tipo.iloc[0],'normalizada_al_total')
        self.assertFalse(st.boundary_medida.iloc[0])
    def test_ausencia_no_cero_en_todas_las_agregaciones(self):
        m=masa(1);m['TMS']=np.nan
        st=e.shift_table(apilado(1),m)
        for d,col in [(e.daily_shift_summary(st),'masa_total'),
                      (e.weekly_summary(st),'masa_total'),(e.module_summary(st),'masa_total')]:
            self.assertTrue(d[col].isna().all())
    def test_semana_con_un_dia_no_completa(self):
        st=e.shift_table(apilado(7),masa(1))
        w=e.weekly_summary(st)
        self.assertEqual(w.n_dias_con_masa.iloc[0],1)
        self.assertFalse(w.sem_completa.iloc[0])
        self.assertTrue(e.rho_semanal(st).isna().all())
    def test_semana_valida_conserva_densidad(self):
        st=e.shift_table(apilado(),masa())
        self.assertTrue(e.weekly_summary(st).sem_completa.iloc[0])
        self.assertAlmostEqual(e.rho_semanal(st).iloc[0],1.8)
    def test_densidad_fuera_banda_sigue_observada_y_reportable(self):
        st=e.shift_table(apilado(),masa(tms=500))
        self.assertAlmostEqual(e.rho_semanal(st).iloc[0],.5)
        codes=[a.codigo for a in v.revisar_resultado({'shift_table':st,'weekly':e.weekly_summary(st)})]
        self.assertIn('densidad_sem_implausible',codes)
    def test_pendiente_cierra_balance_sin_inventar_modulos(self):
        ap=apilado(1,volumen=0);m=masa(1)
        st=e.shift_table(ap,m);b=e.cuadratura_masa(ap,m,st)
        self.assertTrue(st.empty)
        self.assertEqual(b.masa_asignada.iloc[0],0)
        self.assertEqual(b.masa_pendiente.iloc[0],1800)
        self.assertEqual(b.estado_masa.iloc[0],'PENDIENTE_SIN_VOLUMEN')
        codes=[a.codigo for a in v.revisar_resultado({'shift_table':st,'cuadratura':b})]
        self.assertIn('masa_pendiente_sin_volumen',codes)
    def test_cero_medido_no_es_pendiente(self):
        ap=apilado(1,0);m=masa(1,0)
        b=e.cuadratura_masa(ap,m,e.shift_table(ap,m))
        self.assertEqual(b.masa_pendiente.iloc[0],0)
        self.assertEqual(b.estado_masa.iloc[0],'ASIGNADA')
    def test_frontera_invalida_rechazada(self):
        for bad in [-.1,1.1,np.nan]:
            with self.assertRaises(ValueError):e.split_day(apilado(1),1800,bad)
    def test_conservacion_varios_modulos(self):
        ap=apilado(1);ap=pd.concat([ap.assign(modulo=i,vol_diario=vol) for i,vol in [(1,100),(2,200),(3,400)]])
        for boundary in [0,.01,.5,.9,1]:
            rows=pd.DataFrame(e.split_day(ap,2000,boundary))
            self.assertAlmostEqual(rows.masa_turno1.sum(),2000*boundary)
            self.assertAlmostEqual(rows.masa_turno2.sum(),2000*(1-boundary))
    def test_hueco_no_tiene_masa_pendiente_cero(self):
        ap=apilado(7);m=masa(1)
        b=e.cuadratura_masa(ap,m,e.shift_table(ap,m))
        self.assertTrue(b.loc[b.fecha.ne(m.fecha.iloc[0]),'masa_pendiente'].isna().all())
    def test_fuentes_distintas_no_forman_semana_oficial(self):
        m=db.preparar_frontera(masa());m['fuente_masa']=['OFICIAL']+['MEDIDA']*6
        st=e.shift_table(apilado(),m)
        self.assertFalse(e.weekly_summary(st).sem_completa.iloc[0])
        self.assertTrue(e.rho_semanal(st).isna().all())
    def test_loader_normaliza_y_recorta_sql_antes_de_agrupar(self):
        m=masa(1).drop(columns=['H_op','H_op_src']).assign(TMH_T1=900,TMH_T2=900,humedad=.1,sal=0,caso_id=21,caso=None,reporte_run_id='fixture')
        m['TMS_T1']=0;m['TMS_T2']=1790
        tor=pd.DataFrame({'fecha':m.fecha,'H_op':10,'H_torres':10,'H_op_T1':0,'H_op_T2':10})
        with patch.object(db.pd,'read_sql',side_effect=[m,tor]) as query:
            out=db.load_masa('2026-08-03','2026-08-03',engine=object())
        self.assertEqual(out.boundary.iloc[0],0)
        self.assertTrue(out.boundary_normalizada.iloc[0])
        sql=query.call_args_list[1].args[0]
        self.assertLess(sql.index("fecha >= '2026-08-03T08:00:00'"),sql.index('GROUP BY fecha'))
    def test_ventana_ticks_respeta_turno_nocturno(self):
        sql=db._tick_window('2026-08-01','2026-09-30')
        self.assertIn("fecha >= '2026-08-01T08:00:00'",sql)
        self.assertIn("fecha < '2026-10-01T08:00:00'",sql)

if __name__=='__main__':unittest.main(verbosity=2)

