import numpy as np
import pandas as pd
from dash import html, dash_table
from . import engine as e, validacion as val
C = {'bg': '#f5f6fa', 'panel': '#ffffff', 'text': '#2d2d2d', 'sub': '#8a8a9a', 'grid': '#edeff4', 'border': '#e5e7eb', 'track': '#eef0f5', 'accent': '#e86d1f', 'shift1': '#e86d1f', 'shift2': '#3b82f6', 'warn': '#ef4444', 'ok': '#22c55e', 'amber': '#f59e0b', 'dark': '#1a1a2e', 'linea': '#cbd0d9', 'inactivo': '#dfe3ea', 'zebra': '#fafbfd'}
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
SANS = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
PAD_COLORS = {1: '#3b82f6', 2: '#e86d1f'}
MOD_COLORS = ['#e86d1f', '#3b82f6', '#22c55e', '#7c3aed', '#ef4444', '#d05c10', '#2563eb', '#16a34a', '#6d28d9', '#dc2626', '#b45309', '#1d4ed8', '#15803d', '#5b21b6', '#b91c1c', '#f59e0b', '#0891b2', '#059669', '#4338ca', '#e11d48', '#c2410c', '#0e7490', '#047857', '#4c1d95', '#be185d', '#92400e', '#0369a1', '#065f46', '#3b0764', '#9f1239', '#78350f', '#164e63', '#14532d', '#1e1b4b', '#881337', '#431407', '#0c4a6e', '#052e16', '#1a1a2e', '#155e75', '#166534', '#312e81', '#4c0519', '#0f172a']
GRID_MAX_DIAS = 24

def timestamp_text(value, include_date=True):
    t = pd.Timestamp(value).round("s")
    return t.strftime('%d-%m %H:%M:%S' if include_date else '%H:%M:%S')

def resolution_label(origen, resolucion):
    text = f'{origen or ""} {resolucion or ""}'.lower().replace('_', '')
    if '10s' in text or '10sec' in text:
        return 'Perfil validado 10 s'
    if '12h' in text:
        return 'Estimacion A/B 12 h'
    return 'Resolucion indicada en detalle'

def mod_color(mod):
    """Color estable por numero de modulo, como modColor() del jsx."""
    return MOD_COLORS[abs(int(mod)) % len(MOD_COLORS)]

def sem_de_rango(f0, f1):
    """Fase del ciclo de reconstitucion implicada por el rango elegido.

    El ancla no se puede leer del dato — probadas las 7 fases, el CV de la
    densidad semanal queda entre 8.4% y 11.5% sin minimo marcado — asi que la
    fija el rango: el ciclo arranca el dia de la semana del primer dia elegido.

    Rango de una semana o menos: el ultimo dia elegido cierra el ciclo, y los
    dias que quedan fuera no pertenecen a ninguna reconstitucion. Rango mas
    largo: son varias semanas, el ciclo son los 7 dias completos."""
    f0, f1 = (pd.Timestamp(f0), pd.Timestamp(f1))
    if (f1 - f0).days + 1 >= 7:
        return (f0.weekday(), (f0.weekday() + 6) % 7)
    return (f0.weekday(), f1.weekday())

def gantt_labels(d):
    """Etiqueta de fila del Gantt, unica dentro de lo que se este mostrando.

    El numero de modulo se repite entre pads y campanas —88 de 171 filas lo
    comparten con otra— asi que con 'Todo' seleccionado dos modulos distintos
    caian en la misma fila del grafico. La etiqueta lleva solo lo que hace falta
    para desambiguar dentro del cuadro: con los pads en cuadros separados, el
    numero de pad ya lo dice el titulo."""
    n_pad = d['pad_id'].nunique()
    n_cam = d[['pad_id', 'campana']].drop_duplicates().shape[0]
    if n_cam <= 1:
        return [f'M{int(m)}' for m in d['modulo']]
    if n_pad <= 1:
        return [f'C{int(c)}·M{int(m)}' for c, m in zip(d['campana'], d['modulo'])]
    return [f'P{int(p)}C{int(c)}·M{int(m)}' for p, c, m in zip(d['pad_id'], d['campana'], d['modulo'])]

def pad_color(p):
    return PAD_COLORS.get(int(p), MOD_COLORS[int(p) % len(MOD_COLORS)])

def _table(d, cols, cond=None, orden=True, page_size=20, active_cell=False):
    return dash_table.DataTable(data=d.to_dict('records'), columns=[{'name': c, 'id': c} for c in cols],
        page_size=page_size, sort_action='native' if orden else 'none',
        filter_action='native' if orden else 'none', active_cell=None,
        cell_selectable=active_cell, style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': C['bg'], 'color': C['sub'], 'fontWeight': '600', 'fontFamily': MONO, 'fontSize': '10px', 'textTransform': 'uppercase', 'letterSpacing': '0.04em', 'border': f"1px solid {C['border']}", 'padding': '8px 10px'},
        style_cell={'backgroundColor': C['panel'], 'color': C['text'], 'border': f"1px solid {C['border']}", 'padding': '6px 10px', 'fontFamily': MONO, 'fontSize': '12px'},
        style_data_conditional=(cond or []) + [{'if': {'row_index': 'odd'}, 'backgroundColor': C['zebra']}])

def _h(v):
    """Horas con dos decimales; vacio si el modulo no cierra antes del cruce."""
    return '' if pd.isna(v) else f'{v:.2f}'

def _itinerary_frame(res):
    """Recreate one server-side row per reconstructed interval and TA/TB split."""
    timeline=res.get('module_timeline')
    if timeline is None or timeline.empty:
        return pd.DataFrame()
    base=timeline.sort_values(['pad_id','campana','modulo','start']).reset_index(drop=True).copy()
    base['fecha']=pd.to_datetime(base.fecha).dt.normalize()
    shifts=res.get('shift_table')
    if shifts is not None and not shifts.empty:
        shift_cols=[c for c in ('pad_id','campana','modulo','fecha','masa_turno1','masa_turno2','boundary_medida','frontera_tipo') if c in shifts.columns]
        if {'pad_id','campana','modulo','fecha'}.issubset(shift_cols):
            lookup=shifts[shift_cols].copy()
            lookup['fecha']=pd.to_datetime(lookup.fecha).dt.normalize()
            base=base.merge(lookup,on=['pad_id','campana','modulo','fecha'],how='left',validate='many_to_one',sort=False)
    ap=res.get('apilado')
    if ap is not None and not ap.empty:
        raw_cols=[c for c in ('pad_id','campana','modulo','fecha','id','altura_prom','grado_prom','modulo_id','campana_id','vol_total_est','vol_diario','vol_acum_final','avance') if c in ap.columns]
        if {'pad_id','campana','modulo','fecha'}.issubset(raw_cols):
            raw=ap[raw_cols].copy()
            raw['fecha']=pd.to_datetime(raw.fecha).dt.normalize()
            raw=raw.rename(columns={'id':'id_apilado'})
            base=base.merge(raw,on=['pad_id','campana','modulo','fecha'],how='left',validate='many_to_one',sort=False)
    pieces=[]
    for source in base.to_dict('records'):
        start,end=pd.Timestamp(source['start']),pd.Timestamp(source['end'])
        cursor=start
        while cursor < end:
            operational_day=(cursor-pd.Timedelta(hours=8)).normalize()
            ta_end=operational_day+pd.Timedelta(hours=20)
            turno='TA' if cursor < ta_end else 'TB'
            boundary=ta_end if turno=='TA' else operational_day+pd.Timedelta(days=1,hours=8)
            stop=min(end,boundary)
            row=dict(source,start=cursor,end=stop,turno=turno)
            row['id']=f"seg-{int(source['pad_id'])}-{int(source['campana'])}-{int(source['modulo'])}-{pd.Timestamp(source['fecha']).date()}-{turno}-{cursor.isoformat()}"
            pieces.append(row)
            cursor=stop
    if not pieces:
        return pd.DataFrame()
    out=pd.DataFrame(pieces).sort_values(['pad_id','campana','modulo','fecha','turno','start']).reset_index(drop=True)
    group=['pad_id','campana','modulo','fecha','turno']
    out['masa_turno_asignada']=np.where(out.turno.eq('TA'),out.get('masa_turno1',np.nan),out.get('masa_turno2',np.nan))
    out['tms_primera_fila']=~out.duplicated(group)
    # Keep the module/turn TMS once when several reconstructed pieces exist in that turn.
    out.loc[~out.tms_primera_fila,'masa_turno_asignada']=np.nan
    out['id']=[f"{r.id}" for r in out.itertuples()]
    present=set(tuple(x) for x in out[group].drop_duplicates().itertuples(index=False,name=None))
    placeholders=[]
    for source in base.to_dict('records'):
        for turno in ('TA','TB'):
            key=(source['pad_id'],source['campana'],source['modulo'],source['fecha'],turno)
            if key in present: continue
            row=dict(source,start=pd.NaT,end=pd.NaT,turno=turno,
                masa_turno_asignada=source.get('masa_turno1' if turno=='TA' else 'masa_turno2',np.nan),tms_primera_fila=True)
            row['id']=f"seg-{int(source['pad_id'])}-{int(source['campana'])}-{int(source['modulo'])}-{pd.Timestamp(source['fecha']).date()}-{turno}-sin-horario"
            placeholders.append(row)
            present.add(key)
    if placeholders:
        out=pd.concat([out,pd.DataFrame(placeholders)],ignore_index=True).sort_values(['pad_id','campana','modulo','fecha','turno','start'],na_position='last').reset_index(drop=True)
    return out


def tabla_itinerario(res):
    d=_itinerary_frame(res)
    if d.empty: return html.Div('Horario reconstruido no disponible: falta perfil TMH completo.')
    d['Pad']=d.pad_id.astype(int); d['Campana']=d.campana.astype(int); d['Modulo']=d.modulo.astype(int)
    d['Fecha']=d.fecha.dt.strftime('%Y-%m-%d')
    d['Turno']=d.turno.map({'TA':'TA (08-20)','TB':'TB (20-08)'})
    d['Intervalo estimado']=d.apply(lambda r:'Sin interseccion del horario reconstruido' if pd.isna(r.start) else f"{timestamp_text(r.start, False)} a {timestamp_text(r.end, False)}",axis=1)
    d['TMS asignada a turno (t)']=d.masa_turno_asignada.round(0)
    d['Origen horario']=d.origen; d['Resolucion horario']=d.resolucion
    show=[('id','id'),('Pad','Pad'),('Campana','Campana'),('Modulo','Modulo'),
          ('Fecha','Fecha'),('Turno','Turno'),('Intervalo estimado','Intervalo estimado'),
          ('TMS asignada a turno (t)','TMS asignada a turno (t)')]
    for c,_ in show:
        if c not in d:
            d[c]=np.nan
    cols=['id']+[label for key,label in show if key!='id']
    view=d[[key for key,_ in show]].copy()
    view.columns=cols
    table=_table(view,cols,page_size=20,orden=False,active_cell=True)
    table.id='reconstitucion-itinerario'
    table.style_cell_conditional=[{'if':{'column_id':'id'},'display':'none'}]
    return table


def detalle_itinerario(res, row_id):
    """Resolve a browser row key only against current server-side result frames."""
    d=_itinerary_frame(res)
    match=d.loc[d.id.eq(row_id)] if not d.empty else d
    if match.empty:
        return None
    row=match.iloc[0]
    interval='Sin interseccion del horario reconstruido' if pd.isna(row.start) else f'{timestamp_text(row.start)} a {timestamp_text(row.end)}'
    turno='A (08-20)' if row.turno=='TA' else 'B (20-08)'
    facts=[html.P(f"Pad {int(row.pad_id)} / campana {int(row.campana)} / modulo {int(row.modulo)} / fecha {row.fecha:%d-%m-%Y} / turno {turno}"),
        html.P(f"Horario reconstruido del turno: {interval}."),
        html.P(f"TMS asignada al turno en shift_table: {'Sin dato' if pd.isna(row.masa_turno_asignada) else f'{row.masa_turno_asignada:,.0f} t'}. La TMS diaria del modulo es {row.mass_dry:,.0f} t total y no se replica como TMS por tramo."),
        html.P(f"Origen: {row.origen}. Resolucion: {row.resolucion}."),
        html.P('No hay evento de cambio registrado; la marca naranja asigna la fecha original al cambio estimado.')]
    fields=[('id_apilado','ID registro'),('altura_prom','Altura promedio apilada (m)'),('grado_prom','Grado promedio apilado'),
        ('modulo_id','ID modulo'),('campana_id','ID campana'),('vol_total_est','Volumen total estimado (m3)'),
        ('vol_diario','Volumen diario modulo (m3)'),('vol_acum_final','Volumen acumulado final (m3)'),('avance','Avance (%)')]
    raw=[]
    for key,label in fields:
        if key in row.index and pd.notna(row[key]):
            raw.append(html.Li(f'{label}: {row[key]}'))
    if raw:
        facts += [html.H4('Registro de apilado disponible en esta carga'),html.Ul(raw)]
    # Engines recientes conservan los frames brutos ya leidos para que el detalle
    # muestre perfil por turno sin volver a consultar la base.
    profile=res.get('perfil_turnos')
    if profile is not None and not profile.empty and 'fecha' in profile.columns:
        day=pd.Timestamp(row.fecha).normalize()
        q=profile.loc[pd.to_datetime(profile.fecha).dt.normalize().eq(day)].copy()
        target_turn='A' if row.turno=='TA' else 'B'
        if 'turno' in q.columns: q=q.loc[q.turno.astype(str).str.upper().eq(target_turn)]
        wanted=[c for c in ('turno','tm','tmh','humedad','fuente') if c in q.columns]
        if not q.empty and wanted:
            items=[]
            sort_cols=[c for c in ('turno','tm') if c in wanted]
            profile_records=(q[wanted].sort_values(sort_cols) if sort_cols else q[wanted]).to_dict('records')
            for record in profile_records:
                values=' / '.join(f'{c}={record[c]}' for c in wanted if pd.notna(record[c]))
                items.append(html.Li(values))
            facts += [html.H4('Perfil TMH y humedad por turno (lectura cargada)'),html.Ul(items)]
    hours=res.get('horas_turnos')
    if hours is not None and not hours.empty and 'fecha' in hours.columns:
        day=pd.Timestamp(row.fecha).normalize()
        q=hours.loc[pd.to_datetime(hours.fecha).dt.normalize().eq(day)]
        if not q.empty:
            fields=[c for c in q.columns if c not in ('fecha',) and pd.api.types.is_numeric_dtype(q[c])]
            if fields:
                values=' / '.join(f'{c}={q.iloc[0][c]}' for c in fields if pd.notna(q.iloc[0][c]))
                facts.append(html.P('Horas de actividad disponibles para esta fecha: '+values))
    style={'position':'fixed','zIndex':1100,'inset':'15% 15% auto 15%','maxHeight':'70vh','overflowY':'auto','background':C['panel'],'border':f"1px solid {C['border']}",'borderRadius':'10px','boxShadow':'0 10px 35px #0003','padding':'20px'}
    return html.Div([html.Div([html.H3('Detalle del tramo reconstruido')]+facts,style=style),html.Div(style={'position':'fixed','zIndex':1099,'inset':0,'background':'#1118'})],id='reconstitucion-tabla-detalle',style={'position':'fixed','inset':0,'zIndex':1099},role='dialog', **{'aria-modal':'true','aria-label':'Datos del modulo y turno'})


def tabla_detalle_modulo(res, lab, pad=None):
    timeline=res.get('module_timeline')
    if timeline is None or timeline.empty: return html.Div('Horario reconstruido no disponible: falta perfil TMH completo.')
    g=timeline.copy()
    if pad is not None: g=g[g.pad_id.eq(pad)]
    if lab and isinstance(lab, tuple): g=g[g.campana.eq(lab[0]) & g.modulo.eq(lab[1])]
    if g.empty: return None
    g=g.sort_values(['fecha','start']).copy()
    g['Fecha']=g.fecha.dt.strftime('%Y-%m-%d')
    g['Intervalo estimado']=g.apply(lambda r:f"{timestamp_text(r.start, False)} a {timestamp_text(r.end, False)}",axis=1)
    g['TMH asignada (t)']=g.mass_h.round(0); g['TMS asignada (t)']=g.mass_dry.round(0)
    g['Origen']=g.origen; g['Resoluci\u00f3n']=g.resolucion
    cols=['Fecha','Intervalo estimado','TMH asignada (t)','TMS asignada (t)','Origen','Resoluci\u00f3n']
    return html.Div([html.Div('INTERVALOS ESTIMADOS - hora reconstruida, no observada; fin de segmento no equivale a cierre f\u00edsico',style={'fontFamily':MONO,'fontSize':'11px','fontWeight':'700','marginBottom':'6px'}),_table(g,cols,orden=False,page_size=max(len(g),5))])

def kpi(label, value, color=C['text']):
    return html.Div([html.Div(label, style={'fontFamily': MONO, 'fontSize': '9.5px', 'color': C['sub'], 'textTransform': 'uppercase', 'letterSpacing': '0.05em'}), html.Div(value, style={'fontFamily': MONO, 'fontSize': '21px', 'fontWeight': '700', 'color': color, 'marginTop': '4px'})], style={'background': C['panel'], 'border': f"1.5px solid {C['border']}", 'borderRadius': '10px', 'boxShadow': '0 1px 4px rgba(26, 26, 46, 0.05)', 'padding': '14px 14px 12px', 'flex': '1', 'minWidth': '150px'})


NIVEL_COLOR = {'error': C['warn'], 'dato': C['amber'], 'info': C['sub']}
NIVEL_TXT = {'error': 'dato roto', 'dato': 'dato imposible', 'info': 'alcance'}

def panel_calidad(res):
    """Lo que validacion.py encontro en el dato que sostiene esta pantalla.

    Va abierto, no escondido detras de un toggle: el numero de arriba se lee
    igual de limpio con dato bueno que con dato roto, y esa es exactamente la
    razon por la que existe este panel."""
    avisos = res.get('avisos') or []
    if not avisos:
        return None
    orden = {n: i for i, n in enumerate(val.NIVELES)}
    filas = []
    for a in sorted(avisos, key=lambda a: (orden.get(a.nivel, 9), a.codigo)):
        filas.append(html.Div([html.Span(NIVEL_TXT.get(a.nivel, a.nivel), style={'fontFamily': MONO, 'fontSize': '9.5px', 'textTransform': 'uppercase', 'letterSpacing': '0.05em', 'color': NIVEL_COLOR.get(a.nivel, C['sub']), 'minWidth': '108px', 'display': 'inline-block'}), html.Span(f'{a.n} ' if a.n else '', style={'fontFamily': MONO, 'fontSize': '11.5px', 'fontWeight': '700', 'color': C['text']}), html.Span(a.detalle, style={'fontFamily': SANS, 'fontSize': '11.5px', 'color': C['sub']})], style={'marginBottom': '3px'}))
    n_dato = sum((1 for a in avisos if a.nivel == 'dato'))
    return html.Div([html.Div(f'CALIDAD DEL DATO · {n_dato} imposible(s), {len(avisos) - n_dato} de alcance', style={'fontFamily': MONO, 'fontSize': '9.5px', 'color': C['sub'], 'textTransform': 'uppercase', 'letterSpacing': '0.05em', 'marginBottom': '8px'})] + filas, style={'background': C['panel'], 'border': f"1.5px solid {C['border']}", 'borderLeft': f"4px solid {C['amber']}", 'borderRadius': '10px', 'boxShadow': '0 1px 4px rgba(26, 26, 46, 0.05)', 'padding': '14px 14px 12px', 'marginBottom': '16px'})
