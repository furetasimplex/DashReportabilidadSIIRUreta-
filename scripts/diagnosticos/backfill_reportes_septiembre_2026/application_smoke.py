"""Callbacks reales con datos DEV, sin publicar ni guardar comentarios.

Prueba de integración de aplicación, no prueba visual de navegador. Los previews y
exports conservan sus refrescos runtime de septiembre. Requiere --execute explícito.
"""
import argparse
import base64
from datetime import datetime
import io
import json
import os
import time
import zipfile
from dash._callback_context import context_value
from dash._utils import AttributeDict
from flask import Flask
from plotly.utils import PlotlyJSONEncoder
from scripts.backfill_septiembre_2026_reportes import P,read,save
from report_export.callbacks import reportabilidad_cb as cb

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');parser.add_argument('--resume-harness',action='store_true');args=parser.parse_args()
    if not args.execute:
        print('Dry-run: 3 previews, editor Representatividad y 3 descargas, todos septiembre. Sin publicación.');return
    assert os.getenv('SQLSERVER_DB','').lower()=='inventar_spchidr'
    assert read('ejecucion.json')['estado']=='BACKFILL_PASS_PENDIENTE_UI'
    (P/'exports').mkdir(exist_ok=True)
    log={'estado':'EN_CURSO','alcance':'Callbacks reales con contexto Dash/Flask; no navegador, sin publicación/comentarios guardados','casos':[]}
    if (P/'ui_smoke.json').exists():
        if not args.resume_harness:raise RuntimeError('Smoke ya registrado; revisar antes de repetir')
        old=read('ui_smoke.json'); preview=read('representatividad_torres_preview.json')
        assert old['estado']=='FAIL' and len(old['casos'])==1
        assert preview[0]=={'props':{'children':None},'type':'Div','namespace':'dash_html_components'}
        assert len(preview[3])==60 and preview[5]['periodo_mes']=='2026-09'
        save('ui_smoke_harness_falso_positivo.json',old)
        entry=old['casos'][0];entry.update(estado='PASS',registros_editor=60,editor_disponible=True,nota='Falso positivo del harness: botones PDF color danger, no Alert. Área de error vacía. Se reutiliza respuesta real; no se repite callback.')
        entry.pop('error',None);log['casos'].append(entry)
    app=Flask('backfill_septiembre_smoke')
    try:
        with app.test_request_context('/'):
            for tipo in ('representatividad_torres','reporte_turno','prod'):
                for action in ('preview','excel'):
                    if any(e['reporte']==tipo and e['accion']==action and e['estado']=='PASS' for e in log['casos']):continue
                    entry={'reporte':tipo,'accion':action,'inicio':datetime.now().isoformat(),'estado':'INICIADO'}
                    log['casos'].append(entry);save('ui_smoke.json',log);t=time.monotonic()
                    print('INICIO SMOKE',tipo,action,flush=True)
                    button='report-gen-btn' if action=='preview' else 'report-export-btn'
                    prop=json.dumps({'type':button,'tipo':tipo},sort_keys=True,separators=(',',':'))+'.n_clicks'
                    token=context_value.set(AttributeDict(triggered_inputs=[{'prop_id':prop,'value':1}]))
                    try:
                        if action=='preview':
                            result=cb.generar_reporte([1],'2026-09-01','2026-09-30','mes')
                            serialized=json.dumps(result,cls=PlotlyJSONEncoder,ensure_ascii=False)
                            (P/(tipo+'_preview.json')).write_text(serialized,encoding='utf-8')
                            status=json.dumps(result[0],cls=PlotlyJSONEncoder,ensure_ascii=False)
                            assert '"color": "danger"' not in status and 'Error al' not in status, status
                            if tipo=='representatividad_torres':
                                assert isinstance(result[3],list) and len(result[3])>0,'Editor sin registros'
                                entry['registros_editor']=len(result[3]);entry['editor_disponible']=True
                            else:
                                assert 'Sin datos para' not in serialized
                            entry['componentes_json_bytes']=len(serialized.encode())
                        else:
                            if tipo=='representatividad_torres':
                                active=cb._reporte_oficial_activo_para_periodo('2026-09-01','2026-09-30')
                                entry['snapshot_activo']={k:active.get(k) for k in ('id_reporte','periodo_mes','fecha_corte_operacional')} if active else None
                            result=cb.exportar_excel([1],'2026-09-01','2026-09-30','mes')
                            entry['mensaje']=str(result[1])
                            assert isinstance(result[0],dict) and 'content' in result[0],str(result[1])
                            payload=result[0];data=base64.b64decode(payload['content']) if payload.get('base64') else payload['content'].encode()
                            with zipfile.ZipFile(io.BytesIO(data)) as z:
                                assert z.testzip() is None and 'xl/workbook.xml' in z.namelist()
                            (P/'exports'/PathSafe(payload['filename'])).write_bytes(data)
                            entry.update(archivo=payload['filename'],bytes=len(data),xlsx_valido=True)
                            if tipo=='representatividad_torres':
                                # Artefacto vivo separado: nunca llama write_reporte_torre_oficial.
                                _,live,metrics=cb._construir_fuente_unica_representatividad('2026-09-01','2026-09-30')
                                filename='Representatividad_Septiembre_2026_LIVE_sin_publicar.xlsx'
                                (P/'exports'/filename).write_bytes(live)
                                entry.update(archivo_live=filename,metricas_live=metrics,publicado=False)
                        entry.update(estado='PASS',duracion_segundos=time.monotonic()-t)
                        print('PASS SMOKE',tipo,action,flush=True)
                    except Exception as e:
                        entry.update(estado='FAIL',error=str(e),duracion_segundos=time.monotonic()-t);raise
                    finally:
                        context_value.reset(token);save('ui_smoke.json',log)
        log['estado']='PASS_CALLBACKS_NO_REVISION_VISUAL'
    except Exception as e:
        log.update(estado='FAIL',error=str(e));raise
    finally:save('ui_smoke.json',log)

def PathSafe(name):
    from pathlib import Path
    if Path(name).name!=name:raise RuntimeError('Nombre de archivo inválido')
    return name

if __name__=='__main__':main()
