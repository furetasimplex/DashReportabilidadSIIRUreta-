"""Captura de solo lectura DEV y preview de los componentes de presentación."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dash import Dash, Input, Output, dcc, html
import dash_bootstrap_components as dbc
from monitor_pi_tum import db, factor_camiones_panel as panel

OUT = ROOT / 'auditorias/archivo/report_export/exports/factor_ui_tms_20260930'
DAYS = ('2026-09-16', '2026-09-21', '2026-09-22', '2026-09-02', '2026-09-20')


def capture():
    with db._engine_dev().connect() as conn:
        db._assert_dev_connection(conn)
    frame = db.obtener_factor_camiones('2026-09-01', '2026-09-27')
    with patch.object(db, 'obtener_factor_camiones', return_value=frame):
        fig, records, alert = panel.actualizar_factor('2026-09-01', '2026-09-27', 1)
    assert alert == ''
    byday = {r['Fecha']: r for r in records}
    r = byday[DAYS[0]]
    assert abs(r['Chancado_TMS_Reporte'] - 1673.085065416) < 1e-8
    assert r['Chancado_TMH_Con_Ajuste'] == 380
    assert abs(r['Chancado_TMH_Sin_Ajuste'] - 1730.181039727) < 1e-8
    assert abs(r['Factor_Ajuste_Calculado'] - .21963019549669) < 1e-12
    assert r['Factor_Aplicacion_Reportes'] == 1 and r['Modo_Aplicacion'] == 'FORZADO_1'
    for day, vueltas, prod in ((DAYS[1],4,1428),(DAYS[2],137,48909)):
        assert byday[day]['Fuente_Camiones'] == 'MOV_CAM_POWERBI'
        assert byday[day]['Vueltas_KOM'] == vueltas
        assert byday[day]['Produccion_KOM_TMH'] == prod
    for day in DAYS[3:]:
        assert byday[day]['Factor_Ajuste_Calculado'] is None
        assert byday[day]['Fuente_Camiones'] == 'SIN_DATOS_CAMIONES'
        assert byday[day]['Factor_Aplicacion_Reportes'] == 1
        assert 'FALLBACK' in byday[day]['Regla_Aplicacion']
    assert sum(t.type == 'bar' for t in fig.data) == 3
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'datos.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT / 'grafico.json').write_text(fig.to_json(),encoding='utf-8')
    for day in DAYS:
        text = str(panel.detalle_dia(records, {'points':[{'x':day}]}))
        assert 'Chancado TMS publicado [TMS]' in text
        (OUT / (day + '_detalle.txt')).write_text(text, encoding='utf-8')
    print('OK: 5 casos DEV; solo SELECT; tres barras TMH, dos lineas de factor.')


def serve():
    # Preview aislado: no ofrece registro, publicación ni conexiones SQL.
    records = json.loads((OUT / 'datos.json').read_text(encoding='utf-8'))
    figure = json.loads((OUT / 'grafico.json').read_text(encoding='utf-8'))
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    header = panel.layout().children.children[:4]
    app.layout = dbc.Container([
        html.P('Vista de revisión DEV — datos leídos, sin acciones de escritura',className='text-muted small'),
        *header, dcc.Graph(id='preview-chart',figure=figure,config={'displaylogo':False}),
        dcc.Dropdown(id='preview-day',options=list(DAYS),value=DAYS[0],clearable=False),
        html.Div(id='preview-detail',children=panel.detalle_dia(records,{'points':[{'x':DAYS[0]}]}))
    ], fluid=True, style={'maxWidth':'1400px','padding':'20px'})
    @app.callback(Output('preview-detail','children'),Input('preview-day','value'))
    def day_detail(day):
        return panel.detalle_dia(records,{'points':[{'x':day}]})
    app.run(host='127.0.0.1',port=8067,debug=False)


if __name__ == '__main__':
    if '--serve' in sys.argv:
        serve()
    else:
        capture()
