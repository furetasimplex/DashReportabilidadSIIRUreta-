"""Chrome headless local, DEV de solo lectura; sesión temporal y servidor apagado al terminar."""
import json
import os
from pathlib import Path
from threading import Thread
from env_loader import load_app_env


def run():
    load_app_env()
    assert os.getenv('SQLSERVER_DB','').lower()=='inventar_spchidr'
    os.environ['DB_STARTUP_CHECK']='0'
    from main import app
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    output=Path(__file__).with_name('diagnostico_fase1')/'visual'
    output.mkdir(exist_ok=True)
    with app.server.test_client() as client:
        with client.session_transaction() as session: session['user']='revision-local-dev'
        cookie=client.get_cookie(app.server.config['SESSION_COOKIE_NAME']).value
    server=make_server('127.0.0.1',8066,app.server,threaded=True)
    Thread(target=server.serve_forever,daemon=True).start()
    report={'page_errors':[],'callback_errors':[],'cases':[]}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1100})
            context.add_cookies([dict(name=app.server.config['SESSION_COOKIE_NAME'],value=cookie,url='http://127.0.0.1:8066')])
            page=context.new_page()
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            page.on('response',lambda r:report['callback_errors'].append(r.status) if '_dash-update-component' in r.url and r.status>=400 else None)
            page.goto('http://127.0.0.1:8066',wait_until='domcontentloaded')
            page.wait_for_timeout(2500)
            report['initial_url']=page.url
            report['initial_body']=page.locator('body').inner_text()[:1200]
            page.screenshot(path=str(output/'initial.png'))
            page.locator('#nav-lixiviacion').click(timeout=60000)
            page.wait_for_function("document.querySelectorAll('.lix-parcel').length===60",timeout=60000)
            page.get_by_role('tab',name='Diagnóstico',exact=True).click()
            page.locator('#lix-consultar').click()
            page.wait_for_function("document.querySelector('#lix-resumen')?.textContent.includes('6120')",timeout=90000)
            page.wait_for_function("document.querySelector('#lix-tabla-total')?.textContent.includes('6120')",timeout=90000)
            assert 'Seleccione una parcela' in page.locator('#lix-operacional').inner_text()
            page.screenshot(path=str(output/'diagnostico_general.png'),full_page=True)
            report['general_kpis']=[page.locator('#lix-'+k).inner_text() for k in ('kpi-flujo','kpi-cu','kpi-delta','kpi-fuera')]
            for label,expected,filename in [('Óxidos · P1','Riego + drenaje','ox_p1'),('Óxidos · P17','Mixto','ox_p17'),
                                            ('Sulfuros · P7','Riego + drenaje','sulf_p7'),('Sulfuros · P28','Apilado','sulf_p28')]:
                prior=page.locator('#lix-operacional').inner_text()
                control=page.locator('#lix-parcela')
                control.click()
                control.locator('input').fill(label)
                control.get_by_text(label,exact=True).last.click()
                page.wait_for_timeout(1200)
                assert page.locator('#lix-operacional').inner_text()==prior, 'Controles pendientes alteran estado aplicado'
                page.locator('#lix-consultar').click()
                pad,number=label.split(' · ')
                page.wait_for_function("([pad,number]) => {let t=document.querySelector('#lix-operacional')?.textContent||'';return t.includes(pad+' · '+number)&&t.includes('10-09-2026')}",arg=[pad,number],timeout=120000)
                page.wait_for_function("document.querySelector('#lix-timeline .js-plotly-plot')?.data?.length>0",timeout=120000)
                page.wait_for_function("document.querySelector('#lix-tabla-total')?.textContent.startsWith('102 filas')",timeout=60000)
                body=page.locator('#lix-operacional').inner_text()
                assert expected in body
                assert 'Campaña operacional' in body and 'Asignación hidráulica' in body
                assert 'No fue posible' not in body
                page.locator('#lix-operacional').scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                page.screenshot(path=str(output/(filename+'.png')),full_page=True)
                report['cases'].append({'parcel':label,'text':body,'overflow':page.evaluate('document.documentElement.scrollWidth>innerWidth')})
                assert not report['cases'][-1]['overflow']
            page.set_viewport_size({'width':520,'height':950})
            page.wait_for_timeout(1500)
            report['mobile_overflow']=page.evaluate('document.documentElement.scrollWidth>innerWidth')
            page.screenshot(path=str(output/'responsive.png'),full_page=True)
            assert not report['mobile_overflow']
            page.set_viewport_size({'width':1440,'height':1100})
            report['navigation']=[]
            for nav,section in [('reportabilidad','report'),('reclamo','reclamo'),('powerbi','powerbi'),('monitor-pitum','monitor-pitum'),('lixiviacion','lixiviacion')]:
                page.locator('#nav-'+nav).click()
                page.locator('#subtabs-'+section).wait_for(state='visible')
                report['navigation'].append(nav)
            page.get_by_role('tab',name='Mapa operacional de pilas',exact=True).click()
            assert page.locator('.lix-parcel').count()==60
            page.get_by_role('tab',name='Recomendador de Riegos y Drenajes',exact=True).click()
            page.get_by_text('Funcionalidad en desarrollo',exact=True).wait_for(state='visible')
            assert not report['page_errors'] and not report['callback_errors']
            report['passed']=True
            browser.close()
    except Exception as exc:
        report['failure']=str(exc)
        try: page.screenshot(path=str(output/'failure.png'),full_page=True)
        except Exception: pass
        raise
    finally:
        server.shutdown()
        (output/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': run()
