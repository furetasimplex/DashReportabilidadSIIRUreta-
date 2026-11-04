import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from browser_probe import *
call('Page.enable')
call('Emulation.setDeviceMetricsOverride',{'width':1450,'height':700,'deviceScaleFactor':1,'mobile':False})
call('Page.navigate',{'url':Path(__file__).with_name('curvas_ensayo_neto_10009.html').as_uri()})
until("document.querySelector('.js-plotly-plot')?.data?.length===4")
assert js("document.querySelector('.js-plotly-plot').data.every(t=>t.x.length===t.y.length)")
screenshot('metodologia10009-curvas.png')
print(js("JSON.stringify({traces:document.querySelector('.js-plotly-plot').data.length,title:document.querySelector('.js-plotly-plot').layout.title.text})"))
call('Browser.close')
