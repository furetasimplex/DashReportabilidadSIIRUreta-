"""Contrato visual: toneladas secas nunca se grafican como toneladas humedas."""
import unittest
from unittest.mock import patch
import pandas as pd
from . import db, factor_camiones_panel as panel
from .test_factor_camiones import datos
from dash._callback_context import context_value
from dash._utils import AttributeDict


class PresentacionTests(unittest.TestCase):
    def test_hover_unificado_y_seleccion_de_fecha_sin_consultar(self):
        with patch.object(db, 'obtener_factor_camiones', return_value=datos()):
            fig, records, _ = panel.actualizar_factor('2026-09-07','2026-09-08',1)
        self.assertEqual(fig.layout.hovermode, 'x unified')
        self.assertEqual(fig.layout.clickmode, 'event')
        for trace in fig.data[:5]:
            templates = trace.hovertemplate if isinstance(trace.hovertemplate, tuple) else [trace.hovertemplate]
            for template in templates:
                for forbidden in ('Fuente', 'Estado', 'nominal', 'Límite', 'customdata[7]', 'customdata[9]'):
                    self.assertNotIn(forbidden, template)
        self.assertIn('Factor calculado: —', fig.data[4].hovertemplate[1])
        self.assertIn('Regla de respaldo', fig.data[4].hovertemplate[1])
        self.assertEqual(panel.motivo_visible({'Factor_Ajuste_Calculado':1,'Factor_Aplicacion_Reportes':1}), '')
        self.assertEqual(panel.motivo_visible({'Factor_Ajuste_Calculado':.2196,'Factor_Aplicacion_Reportes':1,
                                              'Modo_Aplicacion':'FORZADO_1'}), 'Factor 1 forzado por usuario')
        patches = []
        with patch.object(db,'obtener_factor_camiones',side_effect=AssertionError('consulta al seleccionar')):
            for serie in range(5):
                token = context_value.set(AttributeDict(triggered_inputs=[{'prop_id':'pitum-factor-grafico.clickData'}]))
                try:
                    click = {'points':[{'x':'2026-09-08','curveNumber':serie}]}
                    patches.append(panel.seleccionar_fecha(click,records).to_plotly_json())
                    self.assertIn('08-09-2026',str(panel.actualizar_detalle(records,click)))
                finally:
                    context_value.reset(token)
        self.assertTrue(all(p == patches[0] for p in patches))
        shapes = patches[0]['operations'][0]['params']['value']
        self.assertEqual(shapes[-1]['name'],'fecha-seleccionada')
        self.assertEqual(shapes[-1]['x0'],'2026-09-07T12:00:00')
        token = context_value.set(AttributeDict(triggered_inputs=[{'prop_id':'pitum-factor-datos.data'}]))
        try:
            reset = panel.seleccionar_fecha(click,records).to_plotly_json()
            self.assertEqual(reset['operations'][0]['params']['value'][-1]['x0'],'2026-09-06T12:00:00')
        finally:
            context_value.reset(token)

    def test_traduccion_reglas_solo_en_resultado_sin_mutar_codigos(self):
        records = panel.preparar_datos(datos().iloc[:1])
        row = records[0]
        row['Regla_Aplicacion_Automatica'] = 'APLICA_AJUSTE_VALIDADO'
        row['Regla_Aplicacion'] = 'FORZADO_1_USUARIO'
        original = row.copy()
        detail = str(panel.detalle_dia(records))
        self.assertIn('Ajuste automático validado', detail)
        self.assertIn('Factor 1 forzado por usuario', detail)
        self.assertNotIn('APLICA_AJUSTE_VALIDADO', detail)
        self.assertNotIn('FORZADO_1_USUARIO', detail)
        self.assertEqual(row, original)
        # El gráfico y su contrato no cambian en este ajuste puntual.
        self.assertEqual(panel.hover_dia(row)[7], 'FORZADO_1_USUARIO')
        row['Regla_Aplicacion'] = 'FALLBACK_SIN_DATOS_CAMIONES'
        row['Regla_Aplicacion_Automatica'] = None
        detail = str(panel.detalle_dia(records))
        self.assertIn('FALLBACK_SIN_DATOS_CAMIONES', detail)
        self.assertIn('—', detail)

    def test_tres_barras_dos_lineas_eventos_y_tms_sin_recalculo(self):
        frame = pd.concat([datos().iloc[:1]] * 5, ignore_index=True)
        frame['Fecha'] = ['2026-09-02','2026-09-16','2026-09-20','2026-09-21','2026-09-22']
        frame['Fuente_Camiones'] = ['SIN_DATOS_CAMIONES','MOV_CAM','SIN_DATOS_CAMIONES','MOV_CAM_POWERBI','MOV_CAM_POWERBI']
        frame['Modo_Aplicacion'] = ['AUTOMATICO','FORZADO_1','AUTOMATICO','AUTOMATICO','AUTOMATICO']
        frame['Factor_Ajuste_Calculado'] = [None, .21963019549669, None, 1., .95881375587]
        frame['Factor_Aplicacion_Reportes'] = [1., 1., 1., 1., .95881375587]
        frame['Chancado_TMS_Reporte'] = [None, 1673.085065416, None, 100., 200.]
        frame['KOM_TMH_Corregido'] = [None,380.,None,100.,200.]
        frame['CAT_TMH_Corregido'] = 0.
        frame['Estado_Calculo'] = ['SIN_DATOS_CAMIONES','OK_AJUSTE_KOM','SIN_DATOS_CAMIONES','OK_SIN_AJUSTE','OK_AJUSTE_KOM']
        original = frame.copy(deep=True)
        with patch.object(db,'obtener_factor_camiones',return_value=frame):
            fig, records, alert = panel.actualizar_factor('2026-09-01','2026-09-27',1)
        self.assertEqual(alert,'')
        pd.testing.assert_frame_equal(frame,original)
        self.assertEqual(sum(t.type=='bar' for t in fig.data),3)
        self.assertEqual(sum('lines' in (getattr(t,'mode',None) or '') for t in fig.data),2)
        self.assertEqual(list(fig.layout.yaxis2.range),[0,1.05])
        self.assertEqual([t.name for t in fig.data if t.showlegend is not False], [
            'Chancado TMH sin ajuste', 'Producción de referencia',
            'Chancado TMH corregido automático', 'Factor calculado', 'Factor aplicado'])
        self.assertEqual(fig.data[4].marker.symbol[1], 'diamond-open')
        self.assertEqual(fig.data[4].marker.size[1], 10)
        self.assertEqual(fig.data[4].marker.symbol[3], 'circle')
        self.assertTrue(all(t.showlegend is False for t in fig.data[5:]))
        self.assertTrue(all(t.visible is False for t in fig.data[5:]))
        self.assertTrue(all(t.visible is not False for t in fig.data[:5]))
        for marker, dates in [('FORZADO_1',['2026-09-16']),('MOV_CAM_POWERBI',['2026-09-21','2026-09-22']),('SIN_DATOS_CAMIONES',['2026-09-02','2026-09-20'])]:
            self.assertEqual(list(next(t for t in fig.data if t.name==marker).x),dates)
        self.assertIsNone(fig.data[3].y[0])
        self.assertEqual(fig.data[4].y[0],1.)
        self.assertEqual(fig.data[0].customdata[1][22],'1.673,09')
        self.assertEqual(fig.data[0].customdata[0][22],'—')
        for index, day in enumerate(frame['Fecha']):
            self.assertEqual(fig.data[0].customdata[index][9], frame.iloc[index]['Fuente_Camiones'])
            self.assertIn(frame.iloc[index]['Fuente_Camiones'],
                          str(panel.detalle_dia(records, {'points':[{'x':day}]})))
        for label in ('Fuente camiones', 'Estado MOV_CAM', 'Estado PowerBI',
                      'Modo de aplicación', 'Regla efectiva', 'Estado cálculo automático'):
            self.assertIn(label, panel.HOVER_DIA)
        detail=str(panel.detalle_dia(records,{'points':[{'x':'2026-09-16'}]}))
        for label in ['Producción de referencia [TMH]','Estado cálculo automático','Ajuste por límite KOM',
                      'Chancado corregido automático [TMH]','Chancado TMS publicado [TMS]','1.673,09','380,00']:
            self.assertIn(label,detail)
        self.assertNotIn('Chancado TMH efectivo',detail)
        self.assertIn('Chancado TMS publicado [TMS]',panel.HOVER_DIA)
        self.assertIn('Chancado_TMS_Reporte',db.FACTOR_CAMIONES_SQL)
