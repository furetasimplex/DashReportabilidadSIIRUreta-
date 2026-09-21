"""Render the real sidebar component and theme without importing database callbacks."""
import ast
import html as escaping
import json
from pathlib import Path
import subprocess
import tempfile
from html.parser import HTMLParser

from dash import html
import dash_bootstrap_components as dbc

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
source = ast.parse((ROOT / 'layout.py').read_text(encoding='utf-8'))
function = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'render_sidebar')
scope = {'html': html, 'dbc': dbc}
exec(compile(ast.Module(body=[function], type_ignores=[]), 'layout.py', 'exec'), scope)


def render(node):
    if node is None:
        return ''
    if isinstance(node, (tuple, list)):
        return ''.join(map(render, node))
    if not hasattr(node, 'to_plotly_json'):
        return escaping.escape(str(node))
    value = node.to_plotly_json()
    props = value['props']
    tag = {'Nav': 'nav', 'NavLink': 'a'}.get(value['type'], value['type'].lower())
    attrs = []
    for name in ('id', 'className', 'href'):
        if props.get(name):
            attrs.append(f'{"class" if name == "className" else name}="{escaping.escape(props[name], quote=True)}"')
    if tag == 'nav':
        attrs.append('style="display:flex;flex-direction:column"')
    return f'<{tag} {" ".join(attrs)}>{render(props.get("children"))}</{tag}>'


class Metrics(HTMLParser):
    data = None

    def handle_starttag(self, tag, attrs):
        if tag == 'html':
            self.data = dict(attrs).get('data-sidebar-metrics')


script = """
window.addEventListener('load', async () => {
  await document.fonts.ready;
  document.querySelectorAll('.siir-nav-link').forEach(link => {
    link.classList.toggle('active', link.id === ACTIVE);
  });
  const sidebar = document.querySelector('.siir-sidebar');
  const main = document.querySelector('.siir-main');
  const links = Array.from(document.querySelectorAll('.siir-nav-link'), link => {
    const range = document.createRange();
    range.selectNode(link.lastChild);
    const box = link.getBoundingClientRect(), text = range.getBoundingClientRect();
    return {label: link.textContent, active: link.classList.contains('active'),
      textRight: text.right, linkRight: box.right, textFits: text.right <= box.right,
      iconLeft: link.querySelector('i').getBoundingClientRect().left,
      scrollWidth: link.scrollWidth, clientWidth: link.clientWidth};
  });
  document.documentElement.dataset.sidebarMetrics = JSON.stringify({
    viewport: innerWidth, sidebar: sidebar.getBoundingClientRect().width,
    sidebarScroll: sidebar.scrollWidth, sidebarClient: sidebar.clientWidth,
    mainLeft: main.getBoundingClientRect().left,
    globalOverflow: document.documentElement.scrollWidth > innerWidth,
    font: getComputedStyle(sidebar.querySelector('a')).fontFamily,
    links
  });
});
"""


def check(width, height, active):
    name = f'{width}x{height}_{active}'
    page = OUT / (name + '.html')
    sidebar_html = render(scope['render_sidebar']()).replace('siir-nav-link active', 'siir-nav-link')
    sidebar_html = sidebar_html.replace(f'id="{active}" class="siir-nav-link"',
                                        f'id="{active}" class="siir-nav-link active"')
    page.write_text('''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
<link rel="stylesheet" href="''' + (ROOT / 'assets/theme.css').as_uri() + '''">
</head><body><div class="siir-wrapper">''' + sidebar_html + '''
<main class="siir-main"><h1 class="siir-main-title">Sistema Integrado de Información y Reconciliación</h1>
<p>Validación visual del menú lateral · contenido de referencia</p>
<div style="border:1px solid #E5E7EB;background:white;padding:24px;border-radius:8px">
El contenido comienza a la derecha del menú y se ajusta al espacio disponible.</div></main></div>
<script>const ACTIVE = ''' + json.dumps(active) + ';' + script + '</script></body></html>', encoding='utf-8')
    page.write_text(page.read_text(encoding='utf-8').replace(
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css', dbc.themes.FLATLY), encoding='utf-8')
    command = [r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless',
        '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--hide-scrollbars', '--force-device-scale-factor=1',
        '--user-data-dir=' + tempfile.mkdtemp(prefix='siir-sidebar-'),
        f'--window-size={width},{height}', '--virtual-time-budget=15000', '--dump-dom',
        '--screenshot=' + str(OUT / (name + '.png')), page.as_uri()]
    result = subprocess.run(command, capture_output=True, timeout=50)
    parser = Metrics()
    parser.feed(result.stdout.decode('utf-8', errors='replace'))
    if not parser.data:
        raise RuntimeError('Chrome did not return layout measurements: ' + result.stderr.decode('utf-8', errors='replace')[-1200:])
    metrics = json.loads(parser.data)
    (OUT / (name + '.json')).write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metrics, ensure_ascii=True), flush=True)
    if '--baseline' not in __import__('sys').argv:
        assert not metrics['globalOverflow'], metrics
        assert metrics['sidebarScroll'] == metrics['sidebarClient'], metrics
        assert metrics['mainLeft'] == metrics['sidebar'], metrics
        assert all(link['textFits'] for link in metrics['links']), metrics
        assert len({link['iconLeft'] for link in metrics['links']}) == 1, metrics


if __name__ == '__main__':
    import sys
    if '--baseline' in sys.argv:
        check(1440, 900, 'nav-monitor-pitum')
    else:
        for width, height, active in [(1920,1080,'nav-monitor-pitum'),
                (1366,768,'nav-monitor-pitum'), (900,800,'nav-monitor-pitum'),
                (520,844,'nav-monitor-pitum'), (1366,768,'nav-reportabilidad')]:
            check(width, height, active)
