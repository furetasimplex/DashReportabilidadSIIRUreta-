"""Perfila las rutas del dashboard sin guardar runs ni ejecutar SPs."""
from pathlib import Path
import sys, contextlib, io, time, json, re
ROOT=Path(r'C:\Users\5330\Desktop\HidroNueva\DashReportabilidadSIIR')
sys.path.insert(0,str(ROOT))
from sqlalchemy import event
records=[]
sql=[]
def measure(name, fn):
    before=len(sql)
    started=time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        value=fn()
    records.append(dict(etapa=name,segundos=round(time.perf_counter()-started,4),
                        consultas=len(sql)-before,sql_segundos=round(sum(sql[before:]),4)))
    print(json.dumps(records[-1]),flush=True)
    return value
try:
    with contextlib.redirect_stdout(io.StringIO()):
        from env_loader import load_app_env
        load_app_env()
        from db_connection import get_engine
        engine=get_engine()
    engine.echo=False
    @event.listens_for(engine,'do_connect')
    def timeout(dialect,rec,args,params): params['timeout']=15
    @event.listens_for(engine,'before_cursor_execute')
    def readonly(conn,cursor,statement,params,context,many):
        if not re.match(r'^\s*(SELECT|WITH)\b',statement,re.I) or re.search(r'\b(INSERT|UPDATE|DELETE|MERGE|EXEC|EXECUTE|DROP|ALTER|CREATE)\b',statement,re.I):
            raise RuntimeError('Mutacion SQL prohibida')
        context._perf_start=time.perf_counter()
    @event.listens_for(engine,'after_cursor_execute')
    def done(conn,cursor,statement,params,context,many):
        sql.append(time.perf_counter()-context._perf_start)
    from curvas_recon import db_pipeline as pipe, pad_dashboard as dash, local_cache as cache, recon_engine as motor
    pipe.configure_engine(engine)
    cache._disco_escribir=lambda *a: None
    pipe.save_run=lambda *a,**kw: 0
    measure('casos',dash.initialize_data)
    measure('primera_preparacion_historico',dash.ensure_full_data)
    case=next(c for c in dash.CASOS if c['id']==8)
    ws,we,nd=motor.resolve_window(case['fecha_inicio'],case['fecha_fin'])
    anchor=measure('ancla',lambda: pipe.load_caso_anchor(case['run_id']))
    mats=measure('entradas_ventana',lambda:{lab:dash._load_material_window(lab,ws,we) for lab in ('SULFUROS','OXIDOS')})
    joint=measure('motor_y_preparacion_persistencia_sin_escribir',lambda: motor.reconcile_week_flowsheet_dash(ws,mats,dash.RECON_PRODUCCION,object(),force_all_active=True,week_end=we,anchor=anchor,caso_id=case['id']))
    data=dict(caso_id=case['id'],week_start=ws.isoformat(),week_end=we.isoformat(),n_days=nd,
              totals=joint.get('totals'),warnings=joint['warnings'])
    for lab,mat in mats.items():
        sub=joint['materials'][lab]
        wz=motor.compute_wz_week(ws,sub['active'],mat['riego'],mat['cu_riego'],mat['drena_cu'],week_end=we)
        data[lab]=dash._serialize_result(sub,wz)
    measure('barras_recuperacion',lambda:dash._build_bar(data,'tab-rec'))
    measure('barras_flujos',lambda:dash._build_bar(data,'tab-flujo'))
    measure('graficos_pila',lambda:(dash._build_recovery_chart('rsu-P23',ws,we),dash._build_flujo_chart('rsu-P23',ws,we),dash._build_pila_chart('rsu-P23',ws,we)))
    measure('motor_repetido',lambda:motor.reconcile_flowsheet(ws,mats,force_all_active=True,week_end=we,anchor=anchor))
    Path('perfil_curvas_20261011.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
except Exception as exc:
    print('PERF_ERROR',type(exc).__name__,flush=True)
    sys.exit(2)
