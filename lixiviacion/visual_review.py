"""Revisión automatizada en DEV local. No cambia auth ni SQL.

Usa una sesión Flask de prueba en memoria y Chrome headless instalado.
El servidor de prueba se limita a 127.0.0.1 y se apaga al terminar.
"""
import json
import os
import re
from pathlib import Path
from threading import Thread
from env_loader import load_app_env


def run():
    load_app_env()
    if os.getenv('SQLSERVER_DB', '').lower() != 'inventar_spchidr':
        raise RuntimeError('Revisión restringida a DEV.')
    # Evitar diagnóstico de bases peer PROD al arrancar; solo este proceso.
    os.environ['DB_STARTUP_CHECK'] = '0'
    from main import app
    from werkzeug.serving import make_server
    from playwright.sync_api import sync_playwright
    output = (Path(__file__).resolve().parents[1] / 'auditorias/archivo/lixiviacion/visual_promocion')
    output.mkdir(parents=True, exist_ok=True)
    with app.server.test_client() as client:
        with client.session_transaction() as session:
            session['user'] = 'revision-local-dev'
        cookie = client.get_cookie(app.server.config['SESSION_COOKIE_NAME']).value
    server = make_server('127.0.0.1', 8066, app.server, threaded=True)
    Thread(target=server.serve_forever, daemon=True).start()
    report = {'checks': [], 'page_errors': [], 'callback_errors': []}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            context.add_cookies([dict(name=app.server.config['SESSION_COOKIE_NAME'], value=cookie,
                                     url='http://127.0.0.1:8066')])
            page = context.new_page()
            page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
            page.on('response', lambda r: report['callback_errors'].append(r.status)
                    if '_dash-update-component' in r.url and r.status >= 400 else None)
            page.goto('http://127.0.0.1:8066', wait_until='domcontentloaded')
            page.locator('#nav-lixiviacion').click(timeout=60000)
            page.wait_for_function("document.querySelectorAll('.lix-parcel').length===60", timeout=60000)
            report['map'] = {'parcels':page.locator('.lix-parcel').count(),
                             'labels':page.locator('.lix-parcel-label').all_text_contents()}
            page.screenshot(path=str(output/'mapa.png'),full_page=True)
            page.screenshot(path=str(output/'mapa_desktop.png'),full_page=True)
            assert page.locator('#lix-tabs').get_by_role('tab').all_text_contents()==[
                'Mapa operacional de pilas','Diagnóstico','Recomendador de Riegos y Drenajes']
            report['visual_cases']=[]
            for pad,number,expected in [('Óxidos',1,'Riego + drenaje'),('Óxidos',29,'Espera de reclamo'),
                                        ('Óxidos',17,'Mixto'),('Sulfuros',1,'Mixto'),
                                        ('Sulfuros',7,'Riego + drenaje'),('Sulfuros',28,'Apilado')]:
                page.get_by_role('button',name=re.compile(f'^{pad} P{number}:')).click()
                page.locator('#lix-map-detail').wait_for(state='visible')
                page.wait_for_timeout(400)
                body=page.locator('#lix-map-detail').inner_text()
                report['visual_cases'].append({'pad':pad,'parcela':number,'expected':expected,
                                               'matches_expected':expected in body,'detail':body})
                assert 'Último riego registrado en campaña' in body
                assert 'Los extremos de campaña pueden ser posteriores' in body
                if expected!='Riego + drenaje':
                    assert expected in body and 'Fase operacional' not in body and 'Condición actual' not in body
                else:
                    assert 'Fase operacional' in body and 'Condición actual' in body
                if expected=='Mixto':
                    assert body.count('Mixto')==1 and '_PRE_' not in body and ' = ' not in body
                expected_modules={('Óxidos',29):[['M57','Espera de reclamo'],['M58','Espera de reclamo']],
                                  ('Óxidos',17):[['M33','Conformado / espera de riego'],['M34','Apilado']],
                                  ('Sulfuros',1):[[f'M{n}','Reclamado' if n<5 else 'Reclamo'] for n in range(1,6)]}
                if (pad,number) in expected_modules:
                    actual=page.locator('.lix-module-table tbody tr').evaluate_all('(rows)=>rows.map(r=>Array.from(r.cells).map(c=>c.innerText))')
                    assert actual==expected_modules[(pad,number)]
                    assert 'Inconsistencia' not in body
                    assert 'COMPOSICIÓN' not in body
                if (pad,number) in [('Óxidos',29),('Óxidos',17),('Sulfuros',1)]:
                    page.screenshot(path=str(output/f'drawer_{"ox" if pad=="Óxidos" else "sulf"}_p{number}.png'))
                page.locator('#lix-map-modal .btn-close').click()
                page.locator('#lix-map-modal').wait_for(state='hidden')
            page.locator('.lix-map-block').nth(0).screenshot(path=str(output/'mapa_oxidos.png'))
            page.locator('.lix-map-block').nth(1).screenshot(path=str(output/'mapa_sulfuros.png'))
            target=page.get_by_role('button',name='Óxidos P17: Mixto',exact=True)
            base_color=target.locator('.lix-parcel-cell').evaluate('(e)=>getComputedStyle(e).backgroundColor')
            target.click()
            page.locator('#lix-map-detail').wait_for(state='visible')
            page.wait_for_timeout(500)
            report['map']['detail']=page.locator('#lix-map-detail').inner_text()
            assert 'Conformado / espera de riego' in report['map']['detail']
            assert 'Estado operacional' in report['map']['detail'] and 'Condición actual' not in report['map']['detail']
            page.screenshot(path=str(output/'detalle.png'),full_page=True)
            page.screenshot(path=str(output/'detalle_lateral.png'))
            assert page.locator('#lix-map-modal').bounding_box()['width']==400
            assert page.locator('.lix-parcel.selected').count()==1
            assert page.locator('.lix-parcel.selected .lix-parcel-cell').evaluate('(e)=>getComputedStyle(e).backgroundColor')==base_color
            page.locator('#lix-map-modal .btn-close').click()
            page.locator('#lix-map-modal').wait_for(state='hidden')
            page.screenshot(path=str(output/'mapa_parcela_seleccionada.png'),full_page=True)
            page.locator('#lix-map-pad').click()
            page.locator('#lix-map-pad').get_by_text('Óxidos',exact=True).click()
            page.wait_for_function("document.querySelectorAll('.lix-parcel').length===32")
            report['map']['ox']=page.locator('.lix-parcel').count()
            page.locator('#lix-map-pad').click()
            page.locator('#lix-map-pad').get_by_text('Sulfuros',exact=True).click()
            page.wait_for_function("document.querySelectorAll('.lix-parcel').length===28")
            report['map']['sulf']=page.locator('.lix-parcel').count()
            for number,condition,composition in [(1,'Mixto','RECLAMADO = 4 | RECLAMO = 1'),
                (2,'Mixto','RECLAMO = 1 | REPOSO_PRE_RECLAMO = 4'),
                (26,'Conformado / espera de riego',None),(27,'Conformado / espera de riego',None),
                (28,'Apilado',None)]:
                page.get_by_role('button',name=f'Sulfuros P{number}: {condition}',exact=True).click()
                page.locator('#lix-map-detail').wait_for(state='visible')
                if composition:
                    assert page.locator('.lix-module-table').count()==1
                    assert ' = ' not in page.locator('#lix-map-detail').inner_text()
                page.locator('#lix-map-modal .btn-close').click()
                page.locator('#lix-map-modal').wait_for(state='hidden')
            date_input=page.locator('#lix-map-date input')
            date_input.fill('11-09-2026')
            date_input.press('Tab')
            page.wait_for_timeout(2000)
            report['map']['date']=date_input.input_value()
            page.locator('.lix-parcel').first.click()
            page.locator('#lix-map-detail').wait_for(state='visible')
            assert '11-09-2026' in page.locator('#lix-map-detail').inner_text()
            page.locator('#lix-map-modal .btn-close').click()
            page.locator('.lix-operational h3').click()
            page.set_viewport_size({'width':520,'height':900})
            page.wait_for_timeout(500)
            page.screenshot(path=str(output/'mapa_mobile.png'),full_page=True)
            report['map']['document_overflow']=page.evaluate('document.documentElement.scrollWidth>innerWidth')
            report['map']['internal_scroll']=page.locator('.lix-map-scroll').evaluate('(e)=>e.scrollWidth>e.clientWidth')
            assert report['map']['internal_scroll']
            page.set_viewport_size({'width':1440,'height':1000})
            page.get_by_role('tab',name='Recomendador de Riegos y Drenajes').click()
            page.get_by_text('Funcionalidad en desarrollo',exact=True).wait_for(state='visible')
            page.get_by_role('tab',name='Diagnóstico',exact=True).click()
            page.locator('#lix-consultar').click()
            page.wait_for_function("document.querySelector('#lix-resumen')?.textContent.includes('6120')", timeout=90000)
            def wait_table(count):
                page.wait_for_function("n => document.querySelector('#lix-tabla-total')?.textContent.startsWith(n+' filas')", arg=str(count), timeout=60000)
                page.locator('#lix-tabla td.dash-cell').first.wait_for(state='visible', timeout=60000)
                page.wait_for_timeout(500)
            wait_table(6120)
            report['checks'].append({'total': page.locator('#lix-resumen').inner_text(),
                                     'kpis': [page.locator('#lix-'+k).inner_text() for k in ('kpi-flujo','kpi-cu','kpi-delta','kpi-fuera')]})
            page.screenshot(path=str(output/'desktop.png'), full_page=True)
            for nav, section in [('reportabilidad','report'),('reclamo','reclamo'),('powerbi','powerbi'),('monitor-pitum','monitor-pitum'),('lixiviacion','lixiviacion')]:
                page.locator('#nav-'+nav).click()
                page.locator('#subtabs-'+section).wait_for(state='visible')
                report['checks'].append({'navigation': nav, 'visible': True})
            # React-select: seleccionar por texto visible y valor observado, sin manipular datos React.
            def choose(control, label):
                page.locator('#lix-'+control).click()
                page.locator('#lix-'+control).get_by_text(label, exact=True).last.click()
                page.wait_for_timeout(2500)
            choose('pad', 'Óxidos')
            page.locator('#lix-consultar').click()
            page.wait_for_function("document.querySelector('#lix-resumen')?.textContent.includes('3264')",timeout=60000)
            report['checks'].append({'pad_ox':page.locator('#lix-resumen').inner_text()})
            choose('estado','Fuera de ventana hidráulica')
            page.locator('#lix-consultar').click()
            page.wait_for_function("document.querySelector('#lix-resumen')?.textContent.includes('1045')",timeout=60000)
            wait_table(1045)
            page.locator('#lix-tabla').scroll_into_view_if_needed()
            page.screenshot(path=str(output/'fuera_ventana.png'), full_page=True)
            report['checks'].append({'fuera':page.locator('#lix-resumen').inner_text(),
                                     'table_text': page.locator('#lix-tabla').inner_text()[:1600]})
            # Limpiar estado con teclado; filtros campaña/parcela sobre opciones observadas.
            page.locator('#lix-estado input').fill('')
            page.locator('#lix-estado input').press('Backspace')
            page.locator('#lix-estado input').press('Escape')
            page.wait_for_timeout(2500)
            for field in ('campana','parcela'):
                page.locator('#lix-'+field).click()
                option = page.locator('#lix-'+field+' .VirtualizedSelectOption').first
                report['checks'].append({'filter':field, 'selected':option.inner_text()})
                option.click()
                page.wait_for_timeout(2500)
            page.locator('#lix-consultar').click()
            page.wait_for_timeout(4000)
            report['checks'].append({'filtered':page.locator('#lix-resumen').inner_text(),
                                    'errors':page.locator('#lix-error').inner_text()})
            page.locator('#lix-tabla td.dash-cell').first.wait_for(state='visible', timeout=60000)
            for width in (900,520):
                page.set_viewport_size({'width':width,'height':900})
                page.wait_for_timeout(1200)
                page.screenshot(path=str(output/f'responsive_{width}.png'),full_page=True)
                report['checks'].append({'width':width,'overflow':page.evaluate('document.documentElement.scrollWidth>innerWidth')})
            browser.close()
    except Exception as exc:
        report['failure'] = str(exc)
        try:
            page.screenshot(path=str(output/'failure.png'), full_page=True)
            report['failure_body'] = page.locator('#subtabs-lixiviacion').inner_text()
        except Exception:
            pass
        raise
    finally:
        server.shutdown()
        (output/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    run()
