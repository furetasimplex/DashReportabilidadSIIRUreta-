"""Artefactos desde snapshot local; sin SQL ni imports del servidor Dash."""
from pathlib import Path
import sys,pickle,json,html,shutil
ROOT=Path(r'C:\Users\5330\Desktop\HidroNueva\DashReportabilidadSIIR')
sys.path.insert(0,str(ROOT))
OUT=ROOT/'resultados_curvas'/'agosto_septiembre_2026_20261011'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from curvas_recon.test_envolvente_edad_prototipo import techo
with (OUT/'evaluacion.pkl').open('rb') as fh: data=pickle.load(fh)
df=pd.read_csv(OUT/'detalle_diario.csv',parse_dates=['date'])
observed=pd.read_csv(OUT/'medido_agosto_septiembre.csv',parse_dates=['fecha'])
checks=pd.read_csv(OUT/'cierres_por_caso_pad.csv')
C={'medida':'#64748B','actual':'#E86D1F','envolvente':'#2563EB','techo':'#B91C1C'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.15,'figure.facecolor':'#F5F6FA'})
plots={}; recovery=[]; metadata=[]
for lab,nmax in [('OXIDOS',32),('SULFUROS',28)]:
    for num in range(1,nmax+1):
        p=f'P{num:02d}'; cs=data['cycles'][lab].get(num) or []
        cyc=cs[-1] if cs else {'dates':[],'values':[]}
        xs=pd.to_datetime(cyc['dates']); measured=cyc['values']
        info=data['materials'][lab]['wip'].get(p,{})
        cu=info.get('CuTf',np.nan); stale=p in data['summary']['fuentes'][lab]['campanas_atrasadas']
        rows=df[(df.material==lab)&(df.pila==p)].sort_values('date')
        obs=observed[(observed.material==lab)&(observed.pila==p)].sort_values('fecha')
        series={}; base='sin datos'
        for scenario in ('actual','envolvente'):
            rr=rows[rows.escenario==scenario].set_index('date')
            if pd.isna(cu) or cu<=0 or not len(rr) or not len(xs):
                series[scenario]=(pd.DatetimeIndex([]),[]);continue
            start=max(pd.Timestamp('2026-08-01'),xs[0]); prior=[v for d,v in zip(xs,measured) if d<start]
            seed=prior[-1] if prior else measured[0]
            base='lectura previa' if prior else 'primera lectura del tramo (no hay lectura previa)'
            dates=pd.date_range(start,'2026-08-31'); ys=[]; cum=float(seed)*cu/100
            for d in dates:
                if d in rr.index:
                    r=rr.loc[d]; cum+=.024*((r.fino_pls_final if pd.notna(r.fino_pls_final) else 0)-(r.fino_riego_final if pd.notna(r.fino_riego_final) else 0))
                else:
                    prev=[v for date,v in zip(xs,measured) if date<=d]
                    if prev: cum=float(prev[-1])*cu/100
                pct=cum/cu*100;ys.append(pct)
                recovery.append(dict(material=lab,pila=p,escenario=scenario,fecha=d,recuperacion_pct=pct,CuTf_t=cu,CuTf_anterior=stale,base=base))
            series[scenario]=(dates,ys)
        plots[(lab,p)]=dict(xs=xs,measured=measured,series=series,rows=rows,observed=obs,cu=cu,stale=stale,base=base)
        metadata.append(dict(material=lab,pila=p,inicio_ultimo_ciclo=xs[0] if len(xs) else None,ultima_lectura=xs[-1] if len(xs) else None,CuTf_t=cu,CuTf_anterior=stale,base=base,reconciliada=bool(len(rows)),joven=bool(rows.en_rampa.any()) if len(rows) else False))
meta=pd.DataFrame(metadata)
meta.to_csv(OUT/'campanas_y_calidad.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(recovery).to_csv(OUT/'curvas_recuperacion.csv',index=False,encoding='utf-8-sig')

def panel(ax,lab,p,kind):
    o=plots[(lab,p)]
    if kind=='recuperacion':
        ax.plot(o['xs'],o['measured'],color=C['medida'],label='Recuperación medida',lw=1.1)
        for sc in ('actual','envolvente'):ax.plot(*o['series'][sc],color=C[sc],label=sc.title(),lw=1.3)
        ax.set_ylabel('Recuperación (%)')
        if o['stale']:ax.text(.02,.95,'CuTf anterior: provisional',transform=ax.transAxes,va='top',fontsize=6,color=C['techo'])
        if not pd.notna(o['cu']):ax.text(.02,.95,'Sin CuTf válido',transform=ax.transAxes,va='top',fontsize=6,color=C['techo'])
    elif kind=='drenaje':
        for sc in ('actual','envolvente'):
            rr=o['rows'][o['rows'].escenario==sc]
            ax.plot(rr.date,100*rr.factor_drenaje_real,color=C[sc],label=sc.title(),lw=1.3)
        rr=o['rows'][o['rows'].escenario=='envolvente']
        if len(rr):ax.plot(rr.date,100*rr.dia_rampa.map(techo),'--',color=C['techo'],label='Techo edad',lw=1)
        obs=o['observed']; sep=obs[obs.fecha>='2026-09-01']
        ax.plot(sep.fecha,np.where(sep.q_riego_m3h>0,95.,np.nan),':',color=C['medida'],label='Sept.: proxy 0,95')
        ax.set_ylim(0,105);ax.set_ylabel('Q PLS / Q riego (%)')
    else:
        obs=o['observed'];ax.plot(obs.fecha,obs.q_riego_m3h,color=C['medida'],label='Riego medido',lw=1.1)
        ax.plot(obs.fecha,obs.q_pls_proxy_m3h,color='#94A3B8',label='PLS proxy medido',ls=':',lw=1.1)
        for sc in ('actual','envolvente'):
            rr=o['rows'][o['rows'].escenario==sc]
            ax.plot(rr.date,rr.q_pls_final,color=C[sc],label='PLS '+sc,lw=1.3)
        ax.set_ylabel('Caudal (m³/h)')
    ax.axvspan(pd.Timestamp('2026-09-01'),pd.Timestamp('2026-09-30'),color='#CBD5E1',alpha=.2)
    ax.set_xlim(pd.Timestamp('2026-08-01'),pd.Timestamp('2026-09-30'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3,maxticks=4));ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.tick_params(axis='x',labelsize=7);ax.set_title(p,fontsize=9)

for lab,nmax in [('OXIDOS',32),('SULFUROS',28)]:
    for kind in ('recuperacion','drenaje','caudales'):
        fig,axes=plt.subplots((nmax+3)//4,4,figsize=(17,2.6*((nmax+3)//4)),squeeze=False)
        for n,ax in enumerate(axes.flat,1):
            if n>nmax:ax.set_visible(False);continue
            panel(ax,lab,f'P{n:02d}',kind)
        fig.suptitle(f'{lab} · última campaña disponible · {kind}\nAgosto 2026 reconciliado · Septiembre medido sin ajustes (zona gris)',fontsize=13,y=.998)
        handles,labels=next((ax.get_legend_handles_labels() for ax in axes.flat if ax.get_legend_handles_labels()[0]),([],[]))
        fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.97),ncol=5,fontsize=8,frameon=False)
        fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/f'{kind}_{lab.lower()}.png',dpi=150);plt.close(fig)
young=meta[meta.joven]
if len(young):
    fig,axes=plt.subplots(len(young),3,figsize=(17,3.4*len(young)),squeeze=False)
    for i,r in enumerate(young.itertuples()):
        for j,kind in enumerate(('drenaje','caudales','recuperacion')):
            panel(axes[i,j],r.material,r.pila,kind);axes[i,j].set_title(f'{r.material} {r.pila} · {kind}')
        if i==0:
            for ax in axes[i]:ax.legend(fontsize=7,loc='lower right')
    fig.suptitle('Pilas jóvenes · motor completo\nAgosto actual vs techo por edad experimental · Septiembre medido sin ajuste',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(OUT/'pilas_jovenes.png',dpi=150);plt.close(fig)

sections=[]
for index,((lab,p),o) in enumerate(plots.items()):
    f=make_subplots(rows=3,cols=1,vertical_spacing=.09,subplot_titles=('Recuperación última campaña (%) · sin recorte a 100%','Factor diario Q PLS/Q riego (%)','Caudales (m³/h) · septiembre solo medido'))
    f.add_trace(go.Scatter(x=o['xs'],y=o['measured'],name='Recuperación medida',line=dict(color=C['medida'])),row=1,col=1)
    for sc in ('actual','envolvente'):
        rr=o['rows'][o['rows'].escenario==sc]
        f.add_trace(go.Scatter(x=o['series'][sc][0],y=o['series'][sc][1],name=sc.title(),line=dict(color=C[sc])),row=1,col=1)
        f.add_trace(go.Scatter(x=rr.date,y=rr.factor_drenaje_real*100,name=sc.title(),showlegend=False,line=dict(color=C[sc])),row=2,col=1)
        f.add_trace(go.Scatter(x=rr.date,y=rr.q_pls_final,name='PLS '+sc,showlegend=False,line=dict(color=C[sc])),row=3,col=1)
    rr=o['rows'][o['rows'].escenario=='envolvente'];obs=o['observed']
    f.add_trace(go.Scatter(x=rr.date,y=rr.dia_rampa.map(techo)*100,name='Techo edad experimental',line=dict(color=C['techo'],dash='dash')),row=2,col=1)
    for field,name,dash in [('q_riego_m3h','Riego medido','solid'),('q_pls_proxy_m3h','PLS proxy: 0,95 × riego','dot')]:
        f.add_trace(go.Scatter(x=obs.fecha,y=obs[field],name=name,line=dict(color=C['medida'],dash=dash)),row=3,col=1)
    f.update_layout(height=900,template='plotly_white',font=dict(family='Inter,Arial'),margin=dict(l=65,r=25,t=65,b=35),legend=dict(orientation='h',y=1.08))
    for row in (1,2,3):
        f.update_xaxes(range=['2026-08-01','2026-09-30'],row=row,col=1)
        f.add_vrect(x0='2026-09-01',x1='2026-09-30',fillcolor='#CBD5E1',opacity=.2,line_width=0,row=row,col=1)
    f.update_yaxes(range=[0,105],row=2,col=1)
    quality='CuTf de campaña anterior: recuperación calculada provisional.' if o['stale'] else 'Sin CuTf válido.' if pd.isna(o['cu']) else f'CuTf: {o["cu"]:.1f} t Cu.'
    quality+=' Base: '+o['base']+'.'
    sections.append(f'<section id="{lab}_{p}" class="pile" style="display:{"block" if index==0 else "none"}"><h2>{lab} · {p}</h2><p>{html.escape(quality)}</p>'+f.to_html(full_html=False,include_plotlyjs=index==0)+'</section>')
opts=''.join(f'<option value="{lab}_{p}">{lab} · {p}</option>' for lab,p in plots)
summary=data['summary'];residual=checks[~checks.cierre_sin_inventario]
links=' · '.join(f'<a href="{name}">{label}</a>' for name,label in [('pilas_jovenes.png','Pilas jóvenes'),('recuperacion_oxidos.png','Recuperación óxidos'),('recuperacion_sulfuros.png','Recuperación sulfuros'),('drenaje_oxidos.png','Drenaje óxidos'),('drenaje_sulfuros.png','Drenaje sulfuros'),('caudales_oxidos.png','Caudales óxidos'),('caudales_sulfuros.png','Caudales sulfuros'),('cierres_por_caso_pad.csv','Cierres CSV')])
header=f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Curvas agosto–septiembre 2026</title><style>body{{background:#F5F6FA;color:#1F2937;font:15px Inter,Arial;margin:0}}main{{max-width:1250px;margin:auto;padding:25px}}h1{{color:#E86D1F}}section,.card{{background:#fff;padding:20px;border-radius:12px;margin:16px 0}}select{{font-size:16px;padding:10px}}a{{color:#2563EB}}table{{border-collapse:collapse;font-size:12px}}td,th{{padding:8px;border-bottom:1px solid #ddd}}.warn{{border-left:4px solid #B91C1C}}</style><main><h1>Última campaña disponible · agosto–septiembre 2026</h1>
<div class="card"><p>Agosto: motor completo con anclas oficiales Casos 5–8 (runs 46, 66, 50, 47), en orden cronológico y con campañas vigentes a cada ventana. Naranja: algoritmo actual; azul: techo diario por edad experimental, de 10% al día 1 a 99% al día 30.</p><p>Septiembre: medido sin ajuste reconciliado, según lo solicitado. No hay Casos oficiales para ese mes. La recuperación medida llega al 31/08: no se inventa una curva de recuperación de septiembre; sí se muestran riego y PLS proxy hasta 30/09. PLS por pila = 0,95 × riego es una aproximación, no un sensor.</p></div>
<div class="card warn"><b>Validación y límites</b><p>Cierres directos: {summary['cierres_sin_inventario']}/{summary['cierres_totales']}; con residuo declarado: {summary['cierres_con_inventario']}/{summary['cierres_totales']}. «Inventario» es el residuo del motor; esta prueba no demuestra inventario físico para cubrirlo.</p><p>{int(meta.CuTf_anterior.sum())} pilas usan CuTf de campaña anterior: porcentajes calculados provisionales. Se indica la base acumulada por pila. La envolvente no está calibrada y el estado reconciliado de julio no se hereda. No se escribieron runs ni se sincronizó SQL.</p></div><div class="card">{links}</div><div class="card"><label for="pile">Pila: </label><select id="pile">{opts}</select></div>'''
tail='''<script>document.getElementById('pile').addEventListener('change',function(){document.querySelectorAll('.pile').forEach(p=>p.style.display=p.id===this.value?'block':'none');window.dispatchEvent(new Event('resize'));});</script></main></html>'''
(OUT/'curvas_agosto_septiembre_2026.html').write_text(header+''.join(sections)+tail,encoding='utf-8')
report='# Evaluación del algoritmo completo: agosto–septiembre 2026\n\n'
report+='Agosto reconciliado con Casos 5–8, ventanas 1–7, 8–14, 15–21, 22–31. Septiembre medido sin ajustes, elegido por el usuario al confirmar que no hay Casos oficiales. Sin reconciliación de julio; estado inicial limpio, con edad desde primer riego real. Sin escrituras SQL.\n\n'
report+='WIP reconstruido AS OF cada Caso; no usa una campaña posterior. Se ejecuta reconcile_flowsheet real incluyendo caudal, Cu fino, distribución diaria, rampa, reparto de residuos e inventario declarado. La envolvente sustituye solo el ajuste de rampa en el proceso de prueba. Código productivo intacto.\n\n'
report+='## Diagnóstico\n\n```json\n'+json.dumps({k:v for k,v in summary.items() if k not in ('fuentes','casos')},ensure_ascii=False,indent=2)+'\n```\n\n'
report+=f'{int(meta.reconciliada.sum())} pilas reconciliadas; {len(young)} jóvenes; {int(meta.CuTf_anterior.sum())} con CuTf de campaña anterior. No recortar recuperación a 100% para ocultar anomalías.\n\n'
report+='## Cierres no directos\n\n'+residual.to_csv(index=False)+'\n\n'
report+='Los objetivos PLS usados pueden tener recorte por el techo del PAD; también se conserva objetivo_pls_sin_recorte. Los objetivos son ratios oficiales aplicados al universo de pilas del motor, no igualdad automática a todos los flujos del Caso. El residuo declarado no prueba existencia de inventario físico. No se reconcilia producción de planta.\n\n'
report+='Curvas desde último ciclo medido por pila hasta 31/08. Las series calculadas usan fino diario del run de prueba (0,024 × suma(q·C) en t Cu) y CuTf de WIP AS OF agosto; no se mezclan otros runs del historial SQL. Si no existe lectura previa se usa primera lectura del tramo como base provisional. La edad hidráulica usa primer riego real y puede diferir del inicio del ciclo medido.\n\n'
report+='Caudales diarios m³/h; cierres de caudal m³ (=24 × suma diaria), fino t Cu (=0,024 × suma q·C). Ver detalle_diario.csv, cierres_por_caso_pad.csv, continuidad_rampas.csv, medido_agosto_septiembre.csv, campanas_y_calidad.csv y curvas_recuperacion.csv. Septiembre no tiene curvas reconciliadas ni recuperación medida disponible.\n\n'
report+='Las diferencias en transición a régimen se registran sin interpretar un descenso entre semanas como error de una pila madura. La comprobación de continuidad de rampa considera edad y omite reinicios de campaña. Revisar transición_regimen y delta_factor en continuidad_rampas.csv.\n'
(OUT/'EVALUACION_COMPLETA.md').write_text(report,encoding='utf-8')
print('JOVENES',young[['material','pila']].to_dict('records'))
print('CURVAS_RECUPERACION',len(recovery),'PILAS',len(plots))
print('RESIDUOS',residual[['escenario','caso_id','material','magnitud','residuo','inventario_declarado']].to_json(orient='records'))
print('PLOTS',OUT)
