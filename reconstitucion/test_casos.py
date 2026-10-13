import unittest
from unittest.mock import patch
import pandas as pd
from dash import Dash
from . import panel, db_source as db, engine as e
from .test_integration_module import sample
from .test_metodologia import masa, apilado
CASES=[dict(id=i,nombre=f'Caso {i}',run_id=10+i,fecha_inicio='2026-08-03',fecha_fin='2026-08-09') for i in (1,2)]
def result(i): return dict(sample(),masa=pd.DataFrame({'caso_id':[i],'reporte_run_id':['fixture']}))
def callbacks(loader=None):
 app=Dash(__name__,suppress_callback_exceptions=True);panel.register_callbacks(app,loader=loader,case_loader=lambda:CASES)
 return {k:v['callback'].__wrapped__ for k,v in app.callback_map.items()}
def find(fns,key):return next(fn for k,fn in fns.items() if key in k)
class Casos(unittest.TestCase):
 def test_catalogo_y_periodo(self):
  f=callbacks();cases,opts,default,_=find(f,'reconstitucion-casos.data')(1)
  self.assertEqual([o['value'] for o in opts],[1,2]);self.assertEqual(default,1)
  self.assertEqual(find(f,'reconstitucion-rango.start_date')(2,cases),(cases[1]['fecha_inicio'],cases[1]['fecha_fin']))
 def test_carga_id_periodo(self):
  calls=[]
  def loader(**kw):calls.append(kw);return result(2)
  loaded=find(callbacks(loader),'reconstitucion-token.data')(1,2,CASES)
  self.assertEqual(calls,[dict(caso_id=2,fecha_min='2026-08-03',fecha_max='2026-08-09')]);self.assertEqual(panel._results[loaded[0]]['caso'],CASES[1])
 def test_respuesta_tardia_otro_caso_y_detalle(self):
  f=callbacks(lambda **kw:result(1));token=find(f,'reconstitucion-token.data')(1,1,CASES)[0]
  out=find(f,'reconstitucion-resultados.children')(token,'all','apilado',2,CASES);self.assertIn('Caso seleccionado',out.children)
  self.assertIsNone(find(f,'reconstitucion-detalle.children')({'points':[{'customdata':[1,7,1]}]},token,'all','apilado',2,CASES))
 def test_mismo_id_otro_run_o_periodo(self):
  f=callbacks(lambda **kw:result(1));token=find(f,'reconstitucion-token.data')(1,1,CASES)[0]
  for update in (dict(run_id=99),dict(fecha_fin='2026-08-10')):
   out=find(f,'reconstitucion-resultados.children')(token,'all','apilado',1,[dict(CASES[0],**update)]);self.assertIn('Caso seleccionado',out.children)
 def test_sin_masa_y_otro_caso(self):
  for r in (dict(sample(),masa=pd.DataFrame()),result(2)):
   loaded=find(callbacks(lambda **kw:r),'reconstitucion-token.data')(1,1,CASES)
   self.assertIsNone(loaded[0]);self.assertIn('No se usan datos de otros Casos',loaded[-1])
 def test_error_catalogo_sin_secretos(self):
  app=Dash(__name__)
  def fail():raise RuntimeError('SECRET_FIXTURE')
  panel.register_callbacks(app,case_loader=fail);f={k:v['callback'].__wrapped__ for k,v in app.callback_map.items()}
  out=find(f,'reconstitucion-casos.data')(1);self.assertEqual(out[:3],(None,[],None));self.assertNotIn('SECRET',out[-1])
 def test_sql_historico_parametrizado(self):
  m=masa(1).drop(columns=['H_op','H_op_src']).assign(TMH_T1=900,TMH_T2=900,humedad=.1,sal=0,caso_id=1,caso=None,reporte_run_id='fixture')
  tor=pd.DataFrame({'fecha':[pd.Timestamp('2026-08-03')],'H_op':[10.],'H_torres':[12.],'H_op_T1':[5.],'H_op_T2':[5.]})
  with patch.object(db.pd,'read_sql',side_effect=[m,tor]) as query:out=db.load_masa('2026-08-03','2026-08-09',engine=object(),caso_id=1)
  sql=str(query.call_args_list[0].args[0]);self.assertIn('caso_id = :caso_id',sql);self.assertNotIn('es_activa = 1',sql);self.assertNotIn('casos_balance',sql)
  self.assertIn("origen = 'AJUSTE_REPORTE'",sql);self.assertIn("COALESCE(estado_validacion, 'VALIDADO')",sql);self.assertEqual(query.call_args_list[0].kwargs['params'],{'caso_id':1});self.assertEqual(out.caso_id.tolist(),[1])
 def test_motor_no_recorta_periodo(self):
  cov={'tms':(pd.Timestamp('2026-08-05'),pd.Timestamp('2026-08-07')),'apilado':(pd.Timestamp('2026-08-03'),pd.Timestamp('2026-08-09'))}
  with patch.object(db,'coverage',return_value=cov),patch.object(db,'load_apilado',return_value=apilado(7)),patch.object(db,'load_masa',return_value=masa(7).assign(caso_id=1)) as load:r=e.analyze_db('2026-08-03','2026-08-09',caso_id=1)
  self.assertEqual(r['ventana'],(pd.Timestamp('2026-08-03'),pd.Timestamp('2026-08-09')));self.assertEqual(load.call_args.kwargs,{'caso_id':1})
