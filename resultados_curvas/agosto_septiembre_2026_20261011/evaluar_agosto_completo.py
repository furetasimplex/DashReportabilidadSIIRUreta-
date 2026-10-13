"""Evaluación real SELECT-only; escenario actual vs envolvente ilustrativa.

Se ejecuta separado de Dash. Nunca llama a rutas que persisten runs.
"""
from pathlib import Path
import sys, os, contextlib, io, re, time, json, pickle, copy
from datetime import datetime
ROOT=Path(r'C:\Users\5330\Desktop\HidroNueva\DashReportabilidadSIIR')
sys.path.insert(0,str(ROOT))
OUT=ROOT/'resultados_curvas'/'agosto_septiembre_2026_20261011'
OUT.mkdir(parents=True,exist_ok=True)
os.environ['MPLBACKEND']='Agg'
from sqlalchemy import event,text
import pandas as pd
import numpy as np
def quiet(fn,*args,**kw):
    with contextlib.redirect_stdout(io.StringIO()): return fn(*args,**kw)

def main():
    from env_loader import load_app_env
    quiet(load_app_env)
    from db_connection import get_engine
    engine=quiet(get_engine)
    sql_count=[0]
    @event.listens_for(engine,'do_connect')
    def timeout(dialect,conn_rec,cargs,cparams): cparams['timeout']=10
    @event.listens_for(engine,'before_cursor_execute')
    def readonly(conn,cursor,statement,params,context,many):
        clean=re.sub(r'--[^\n]*|/\*.*?\*/','',statement,flags=re.S).strip()
        if not re.match(r'^(SELECT|WITH)\b',clean,re.I) or re.search(r'\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|EXEC)\b',clean,re.I):
            raise RuntimeError('SQL no SELECT bloqueado')
        sql_count[0]+=1
    from curvas_recon import local_cache as cache, db_pipeline as pipe, recon_engine as motor, pad_data
    from curvas_recon.pad_cycles import split_into_cycles
    from curvas_recon.test_envolvente_edad_prototipo import ajustar_acotado
    from db_startup_check import _resolver_ambiente
    cache.DIR=str(ROOT/'resultados_curvas'/'agosto_2026_20261011'/'entradas_cache'); cache.TTL_S=0; cache.ACTIVA=True; cache._MEM.clear()
    pipe.configure_engine(engine)
    with engine.connect() as conn:
        perfil=_resolver_ambiente(conn.execute(text('SELECT DB_NAME()')).scalar())
    pipe.HIDRO_SCHEMA=perfil.siir_db+'.hidro'
    def forbidden(*a,**kw): raise RuntimeError('Persistencia bloqueada en evaluación')
    pipe.save_run=pipe.sync_all=forbidden
    motor.save_run=forbidden
    ws,we=pd.Timestamp('2026-08-01'),pd.Timestamp('2026-08-31')
    observed_end=pd.Timestamp('2026-09-30')
    cases=sorted([c for c in quiet(pipe.load_casos) if ws<=c['fecha_inicio']<=c['fecha_fin']<=we],key=lambda c:c['fecha_inicio'])
    covered=[d for c in cases for d in pd.date_range(c['fecha_inicio'],c['fecha_fin'])]
    assert len(covered)==31 and len(set(covered))==31, 'Casos no cubren agosto exactamente una vez'
    print('Casos agosto:', [(c['id'],str(c['fecha_inicio'].date()),str(c['fecha_fin'].date()),c['run_id']) for c in cases],flush=True)
    def wip_asof(label,end):
        query=text(f'''WITH ranked AS (
            SELECT p.nombre AS pila,c.fecha_inicio,c.fecha_fin,c.cu_tf,
            ROW_NUMBER() OVER(PARTITION BY c.parcela_id ORDER BY c.fecha_inicio DESC) AS rn
            FROM {pipe.SCHEMA}.campana c
            JOIN {pipe.SCHEMA}.parcela p ON p.id_parcela=c.parcela_id
            JOIN {pipe.SCHEMA}.material m ON m.id=p.id_pad
            WHERE m.nombre=:material AND c.fecha_inicio<=:asof
        ) SELECT pila,fecha_inicio,fecha_fin,cu_tf FROM ranked WHERE rn=1''')
        rr=pipe._sql_rows(engine,query,{'material':motor.LABEL_MATERIAL[label],'asof':end})
        result={p:dict(ini_aporte=pd.Timestamp(ini),fin_ciclo=pd.Timestamp(fin) if fin is not None else pd.NaT,
                       CuTf=float(cu) if cu is not None else np.nan,rec_actual=np.nan,sin_campana=False) for p,ini,fin,cu in rr}
        for p,ini in motor.inicio_campana(label,end).items():
            if p not in result: result[p]=dict(ini_aporte=ini,fin_ciclo=pd.NaT,CuTf=np.nan,rec_actual=np.nan,sin_campana=True)
        return result
    materials={}; raw={}; cycles={}; anchors={}; sources={}
    for label,loader in [('OXIDOS',pad_data.load_oxido),('SULFUROS',pad_data.load_sulfuro)]:
        started=time.perf_counter()
        wip=quiet(wip_asof,label,we)
        rec,mx,cd=quiet(motor.load_rec_curves,label)
        materials[label]=dict(wip=wip,rec_curves=rec,max_rec=mx,ciclo_d=cd,
                             riego=quiet(motor.load_riego,label,ws,observed_end),
                             cu_riego=quiet(motor.load_cu_riego,label,ws,observed_end),
                             drena_cu=quiet(motor.load_drena_cu,label,ws,observed_end))
        raw[label]=quiet(loader,end_date=we.date())
        all_dates=[d for p in raw[label].values() for d in p['dates']]
        last=max(all_dates) if all_dates else None
        cycles[label]={n:split_into_cycles(p['dates'],p['values'],last) for n,p in raw[label].items()}
        sources[label]=dict(corte=str(quiet(motor.material_cutoff,label)),
                            campanas_atrasadas=quiet(motor._campana_atrasada,label),
                            riego_positivo_dias=[str(d.date()) for d in materials[label]['riego'].index if materials[label]['riego'].loc[d].sum()>0])
        sources[label]['ultima_recuperacion_medida']=str(last)
        print(label,'entradas listas',round(time.perf_counter()-started,2),'s; corte',sources[label]['corte'],flush=True)
    for c in cases:
        anchors[c['id']]=quiet(pipe.load_caso_anchor,c['run_id'])
        assert pipe.caso_anchor_completo(anchors[c['id']]), f"Ancla incompleta Caso {c['id']}"
    orig_fit=motor.ramp_curve.ajustar
    orig_solver=motor.reconcile_week_flowsheet
    def bounded(q,dc,target,cap,alpha=motor.ramp_curve.RAMP_ALPHA,frac=motor.ramp_curve.INICIO_FRAC_MAX,f0=None,n0=None):
        if target is None or target<=0: return orig_fit(q,dc,target,cap,alpha=alpha,frac=frac,f0=f0,n0=n0)
        r=ajustar_acotado(q,dc,target,cap,f0,n0,alpha)
        useful=[i for i,(qi,n) in enumerate(zip(q,dc)) if qi>0 and n is not None and n>=1]
        r.update(inicio=r['factores'][useful[0]] if useful else 0.,modo='continuacion' if f0 is not None else 'arranque')
        if not useful: r['status']='sin_riego'
        return r
    scenarios={}; checks=[]; rows=[]; previous={}; continuity=[]
    for scenario in ('actual','envolvente'):
        motor.limpiar_estado_rampa()
        motor.ramp_curve.ajustar=orig_fit if scenario=='actual' else bounded
        scenario_results=[]
        for case in cases:
            captured=[]
            def capture(*a,**kw):
                r=orig_solver(*a,**kw); captured.append(r); return r
            motor.reconcile_week_flowsheet=capture
            case_mat={label:dict(mat,wip=quiet(wip_asof,label,case['fecha_fin']),riego=mat['riego'].loc[case['fecha_inicio']:case['fecha_fin']],
                                cu_riego=mat['cu_riego'].loc[case['fecha_inicio']:case['fecha_fin']],
                                drena_cu=mat['drena_cu'].loc[case['fecha_inicio']:case['fecha_fin']]) for label,mat in materials.items()}
            result=quiet(motor.reconcile_flowsheet,case['fecha_inicio'],case_mat,force_all_active=True,week_end=case['fecha_fin'],anchor=anchors[case['id']])
            scenario_results.append(dict(caso=case,res=result,parts=captured))
            for part in captured:
                label=part['piles'][0]['label'] if part['piles'] else next(iter(part['ramp_cap_by_label']), 'sin_pilas')
                for field,targetkey,mult in [('q_riego_final','q_riego_recon',24),('q_pls_final','q_pls_recon',24),('fino_riego_final','cu_fino_riego_recon',.024),('fino_pls_final','cu_fino_pls_recon',.024)]:
                    delivered=sum(d.get(field) or 0. for d in part['daily'])
                    target=part.get(targetkey) or 0.
                    inventory=part.get('inventario_pls',0.) if field=='q_pls_final' else part.get('inventario_fino_pls',0.) if field=='fino_pls_final' else 0.
                    error=target-delivered
                    checks.append(dict(escenario=scenario,caso_id=case['id'],material=label,magnitud=field,
                                       objetivo=target*mult,entregado=delivered*mult,residuo=error*mult,
                                       inventario_declarado=inventory*mult,
                                       objetivo_pls_sin_recorte=part.get('q_pls_recon_raw')*24 if field=='q_pls_final' else None,
                                       ancla_pls_recortada=part.get('fdrena_flow_clipped',False),
                                       cierre_sin_inventario=abs(error)<=1e-6*max(1.,abs(target)),
                                       cierre_con_inventario=abs(error-inventory)<=1e-6*max(1.,abs(target))))
                for p in part['piles']:
                    sum_err={f:sum(d.get(f) or 0. for d in p['daily'])-(p.get(f) or 0.) for f in ('q_riego_final','q_pls_final','fino_riego_final','fino_pls_final')}
                    for d in p['daily']:
                        q=d['q_riego_final']; f=d['q_pls_final']/q if q>0 else np.nan
                        rows.append(dict(escenario=scenario,caso_id=case['id'],run_oficial_id=case['run_id'],material=label,pila=p['parcela'],en_rampa=p['en_rampa'],**d,factor_drenaje_real=f,
                                         error_pila_max=max(abs(x) for x in sum_err.values())))
                    useful=[d for d in p['daily'] if d['q_riego_final']>0]
                    key=(scenario,label,p['parcela'])
                    if useful:
                        first,last=useful[0],useful[-1]
                        prev=previous.get(key)
                        continuity.append(dict(escenario=scenario,caso_id=case['id'],material=label,pila=p['parcela'],
                                               dia_inicio=first['dia_rampa'],factor_inicio=first['q_pls_final']/first['q_riego_final'],
                                               factor_previo=prev['factor'] if prev else None,en_rampa=p['en_rampa'],
                                               transicion_regimen=bool(prev and prev['en_rampa'] and not p['en_rampa']),
                                               delta_factor=first['q_pls_final']/first['q_riego_final']-prev['factor'] if prev else None,
                                               creciente_desde_previo=(prev is None or not p['en_rampa'] or not prev['en_rampa'] or first['dia_rampa']<=prev['edad'] or first['q_pls_final']/first['q_riego_final']>=prev['factor']-1e-8)))
                        previous[key]=dict(factor=last['q_pls_final']/last['q_riego_final'],edad=last['dia_rampa'],en_rampa=p['en_rampa'])
            print(scenario,'Caso',case['id'],'pilas',len(result['piles']),'avisos',len(result['warnings']),'inventario Q',round(result['inventario_pls']*24,2),'m3',flush=True)
        scenarios[scenario]=scenario_results
    motor.ramp_curve.ajustar=orig_fit; motor.reconcile_week_flowsheet=orig_solver
    df=pd.DataFrame(rows); cdf=pd.DataFrame(checks); cont=pd.DataFrame(continuity)
    df.to_csv(OUT/'detalle_diario.csv',index=False,encoding='utf-8-sig')
    cdf.to_csv(OUT/'cierres_por_caso_pad.csv',index=False,encoding='utf-8-sig')
    cont.to_csv(OUT/'continuidad_rampas.csv',index=False,encoding='utf-8-sig')
    capviol=df[(df['q_riego_final']>0)&(df['factor_drenaje_real']>.99+1e-7)]
    age=df[(df['escenario']=='envolvente')&df['en_rampa']&(df['q_riego_final']>0)].copy()
    from curvas_recon.test_envolvente_edad_prototipo import techo
    age['techo_edad']=age['dia_rampa'].map(techo)
    ageviol=age[age['factor_drenaje_real']>age['techo_edad']+1e-7]
    negatives=df[(df['q_riego_final']<-1e-9)|(df['q_pls_final']<-1e-9)]
    outside=df[(pd.to_datetime(df.date)<ws)|(pd.to_datetime(df.date)>we)]
    summary=dict(fecha_evaluacion=datetime.now().isoformat(),casos=[{k:str(v) for k,v in c.items()} for c in cases],
                 perfil=perfil.nombre,sql_selects=sql_count[0],filas_diarias=len(df),fuentes=sources,
                 violaciones_techo_general=len(capviol),violaciones_techo_edad=len(ageviol),caudales_negativos=len(negatives),
                 fechas_fuera_agosto=len(outside),errores_suma_diaria_pila=len(df[df.error_pila_max>1e-6][['escenario','caso_id','material','pila']].drop_duplicates()),
                 fallos_continuidad=int((~cont.creciente_desde_previo).sum()) if len(cont) else 0,
                 cierres_sin_inventario=int(cdf.cierre_sin_inventario.sum()),cierres_totales=len(cdf),
                 cierres_con_inventario=int(cdf.cierre_con_inventario.sum()))
    transition=cont[cont.transicion_regimen]
    summary['transiciones_regimen']=len(transition)
    summary['salto_max_transicion_regimen']=float(transition.delta_factor.abs().max()) if len(transition) else None
    (OUT/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    observed=[]
    for label,mat in materials.items():
        for date,row in mat['riego'].iterrows():
            for p,q in row.items():
                cr=mat['cu_riego'].get(date,np.nan)
                cp=mat['drena_cu'].at[date,p] if p in mat['drena_cu'] and date in mat['drena_cu'].index else np.nan
                observed.append(dict(material=label,pila=p,fecha=date,q_riego_m3h=q,q_pls_proxy_m3h=.95*q,cu_riego_gl=cr,cu_drena_gl=cp))
    pd.DataFrame(observed).to_csv(OUT/'medido_agosto_septiembre.csv',index=False,encoding='utf-8-sig')
    with (OUT/'evaluacion.pkl').open('wb') as fh: pickle.dump(dict(materials=materials,raw=raw,cycles=cycles,scenarios=scenarios,summary=summary),fh)
    capviol.to_csv(OUT/'violaciones_techo.csv',index=False); ageviol.to_csv(OUT/'violaciones_edad.csv',index=False)
    print('RESUMEN',json.dumps({k:v for k,v in summary.items() if k not in ('fuentes','casos')},default=str),flush=True)
    print('OUTPUT',OUT,flush=True)

if __name__=='__main__':
    try: main()
    except Exception as exc:
        # Persist no credentials, SQL strings or driver messages in error reports.
        print('ERROR_EVALUACION',type(exc).__name__,flush=True)
        import traceback
        frames=traceback.extract_tb(exc.__traceback__)
        print('UBICACION',[(Path(f.filename).name,f.lineno,f.name) for f in frames],flush=True)
        sys.exit(2)
