"""Chrome headless local: comprobar solo navegación, con SELECT DEV."""
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
    output=Path(__file__).parent/'visual'
    output.mkdir(exist_ok=True)
    with app.server.test_client() as client:
        with client.session_transaction() as session:session['user']='revision-local-dev'
        cookie=client.get_cookie(app.server.config['SESSION_COOKIE_NAME']).value
    server=make_server('127.0.0.1',8066,app.server,threaded=True)
    Thread(target=server.serve_forever,daemon=True).start()
    report={'passed':False,'page_errors':[],'callback_errors':[],'cases':[]}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1100})
            context.add_cookies([dict(name=app.server.config['SESSION_COOKIE_NAME'],value=cookie,url='http://127.0.0.1:8066')])
            page=context.new_page()
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            page.on('response',lambda r:report['callback_errors'].append(r.status) if '_dash-update-component' in r.url and r.status>=400 else None)
            page.goto('http://127.0.0.1:8066',wait_until='domcontentloaded')
            page.locator('#nav-lixiviacion').click(timeout=60000)
            for mode,width,height in [('desktop',1440,1100),('mobile',520,950)]:
                page.set_viewport_size({'width':width,'height':height})
                page.wait_for_function("document.querySelectorAll('.lix-parcel').length===60",timeout=60000)
                tabs=page.get_by_role('tab')
                labels=tabs.all_text_contents()
                assert labels==['Mapa operacional de pilas','Diagnóstico'],labels
                assert 'active' in page.get_by_role('tab',name='Mapa operacional de pilas',exact=True).get_attribute('class').split()
                assert page.get_by_text('Funcionalidad en desarrollo',exact=True).count()==0
                assert page.get_by_role('tab',name='Recomendador de Riegos y Drenajes',exact=True).count()==0
                page.wait_for_timeout(800)
                page.screenshot(path=str(output/f'{mode}_mapa.png'),full_page=True)
                page.get_by_role('tab',name='Diagnóstico',exact=True).click()
                page.locator('#lix-consultar').click()
                page.wait_for_function("document.querySelector('#lix-resumen')?.textContent.includes('6120')",timeout=90000)
                page.wait_for_function("document.querySelector('#lix-tabla-total')?.textContent.includes('6120')",timeout=90000)
                assert 'active' in page.get_by_role('tab',name='Diagnóstico',exact=True).get_attribute('class').split()
                page.wait_for_timeout(1200)
                page.screenshot(path=str(output/f'{mode}_diagnostico.png'),full_page=True)
                overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
                assert not overflow
                page.get_by_role('tab',name='Mapa operacional de pilas',exact=True).click()
                page.wait_for_function("document.querySelectorAll('.lix-parcel').length===60",timeout=60000)
                page.wait_for_timeout(800)
                assert 'active' in page.get_by_role('tab',name='Mapa operacional de pilas',exact=True).get_attribute('class').split()
                report['cases'].append({'mode':mode,'tabs':labels,'map_count':60,'diagnostic_rows':6120,'return_to_map':True,'document_overflow':overflow})
            assert not report['page_errors'] and not report['callback_errors']
            report['passed']=True
            browser.close()
    except Exception as exc:
        report['failure']=str(exc)
        try:page.screenshot(path=str(output/'failure.png'),full_page=True)
        except Exception:pass
        raise
    finally:
        server.shutdown()
        (output/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':run()
