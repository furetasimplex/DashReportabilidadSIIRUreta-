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

def mod_color(mod):
    """Color estable por numero de modulo, como modColor() del jsx."""
    return MOD_COLORS[abs(int(mod)) % len(MOD_COLORS)]
MODO_LABEL = {'apilado': 'calendario de apilado', 'calendario': 'utilización de calendario', 'campana': 'calibrado por campaña'}

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

def _table(d, cols, cond=None, orden=True, page_size=20):
    return dash_table.DataTable(data=d[cols].to_dict('records'), columns=[{'name': c, 'id': c} for c in cols], page_size=page_size, sort_action='native' if orden else 'none', filter_action='native' if orden else 'none', style_table={'overflowX': 'auto'}, style_header={'backgroundColor': C['bg'], 'color': C['sub'], 'fontWeight': '600', 'fontFamily': MONO, 'fontSize': '10px', 'textTransform': 'uppercase', 'letterSpacing': '0.04em', 'border': f"1px solid {C['border']}", 'padding': '8px 10px'}, style_cell={'backgroundColor': C['panel'], 'color': C['text'], 'border': f"1px solid {C['border']}", 'padding': '6px 10px', 'fontFamily': MONO, 'fontSize': '12px'}, style_data_conditional=(cond or []) + [{'if': {'row_index': 'odd'}, 'backgroundColor': C['zebra']}])

def _h(v):
    """Horas con dos decimales; vacio si el modulo no cierra antes del cruce."""
    return '' if pd.isna(v) else f'{v:.2f}'

def tabla_itinerario(res):
    it = res.get('itinerario')
    if it is None or it.empty:
        return html.Div('Sin datos', style={'color': C['sub']})
    d = it.sort_values(['pad_id', 'campana', 'act_ini']).copy()
    d['Pad'] = d['pad_id'].astype(int)
    d['Campaña'] = d['campana'].astype(int)
    d['Módulo'] = d['modulo'].astype(int)
    d['Medido desde'] = d['real_ini'].dt.strftime('%Y-%m-%d')
    d['Medido hasta'] = d['real_fin'].dt.strftime('%Y-%m-%d')
    d['Días apilando'] = d['n_dias_act']
    d['Días sin apilar'] = d['n_dias_inact']
    d['Vol m³'] = d['vol_total'].round(0)
    d['Proy. h'] = d['proy_h'].round(0)
    d['Inicio proyectado'] = d['proy_ini'].dt.strftime('%Y-%m-%d %H:%M')
    d['Fin proyectado'] = d['proy_fin'].dt.strftime('%Y-%m-%d %H:%M')
    d['Cruce turno'] = d['cruce_turno'].dt.strftime('%Y-%m-%d %H:%M')
    d['Cierra en'] = pd.Series(d['turno_fin']).map({1.0: 'T1 (antes del cruce)', 2.0: 'T2'}).fillna('')
    d['Adelanto al cruce h'] = d['delta_cruce'].map(_h)
    d['Cierre corrido'] = d['cierre_corrido'].dt.strftime('%Y-%m-%d %H:%M')
    d['Δ medición h'] = d['atraso_h'].round(0)
    d['Tasa aparente m³/h'] = d['rate_mod'].round(0)
    d['× tasa común'] = d['rate_dev'].round(2)
    cols = ['Pad', 'Campaña', 'Módulo', 'Medido desde', 'Medido hasta', 'Días apilando', 'Días sin apilar', 'Vol m³', 'Proy. h', 'Inicio proyectado', 'Fin proyectado', 'Cruce turno', 'Cierra en', 'Adelanto al cruce h', 'Cierre corrido', 'Δ medición h', 'Tasa aparente m³/h', '× tasa común']
    return _table(d, cols, [{'if': {'filter_query': '{× tasa común} > 1.3 || {× tasa común} < 0.77', 'column_id': '× tasa común'}, 'color': C['sub'], 'fontStyle': 'italic'}, {'if': {'filter_query': '{Días sin apilar} > 0', 'column_id': 'Días sin apilar'}, 'color': C['amber']}, {'if': {'filter_query': '{Δ medición h} > 0', 'column_id': 'Δ medición h'}, 'color': C['warn']}, {'if': {'column_id': 'Adelanto al cruce h'}, 'color': C['amber'], 'fontWeight': '600'}, {'if': {'filter_query': '{Cierra en} = T2', 'column_id': 'Cierra en'}, 'color': C['shift2']}, {'if': {'column_id': 'Cierre corrido'}, 'color': C['ok']}])

def tabla_detalle_modulo(res, lab, pad=None):
    """Detalle dia a dia del modulo que se clickeo en el Gantt.

    Es el desglose de una fila del Gantt: cada dia que el modulo recibio
    volumen, con la fraccion del dia que se llevo y la masa que le tocó de cada
    turno. La suma de las columnas de masa da la barra del itinerario.

    `pad` tiene que ser el mismo del cuadro donde se hizo click: las etiquetas
    se arman por cuadro, asi que 'C18·M5' del cuadro del pad 1 no es la misma
    fila que 'C18·M5' del cuadro del pad 2."""
    it, st = (res.get('itinerario'), res['shift_table'])
    if it is None or it.empty or (not lab):
        return None
    d = it if pad is None else it[it['pad_id'] == pad]
    if d.empty:
        return None
    d = d.sort_values(['pad_id', 'campana', 'act_ini'], ascending=[True, True, False]).copy()
    d['lab'] = gantt_labels(d)
    sel = d[d['lab'] == lab]
    if sel.empty:
        return None
    r = sel.iloc[0]
    g = st[(st.pad_id == r.pad_id) & (st.campana == r.campana) & (st.modulo == r.modulo)].sort_values('fecha').copy()
    if g.empty:
        return None
    g['Fecha'] = g['fecha'].dt.strftime('%Y-%m-%d')
    g['Avance %'] = (g['avance'] * 100).round(1)
    g['Vol m³'] = g['vol_diario'].round(0)
    g['% del día'] = (g['frac_vol'] * 100).round(1)
    g['Masa T1 t'] = g['masa_turno1'].round(0)
    g['Masa T2 t'] = g['masa_turno2'].round(0)
    g['Masa t'] = g['masa_total'].round(0)
    g['Frontera T1 %'] = (g['boundary'] * 100).round(1)
    g['Cruza turno'] = g['cruza_turno'].map({True: 'sí', False: ''})
    g['H torre'] = g['H_op'].round(1)
    cols = ['Fecha', 'Avance %', 'Vol m³', '% del día', 'Masa T1 t', 'Masa T2 t', 'Masa t', 'Frontera T1 %', 'Cruza turno', 'H torre']
    tot = {c: '' for c in cols}

    def total_masa(col):
        total = g[col].sum(min_count=1)
        return round(total) if pd.notna(total) else None
    tot.update({'Fecha': f'{len(g)} días', 'Vol m³': round(g['vol_diario'].sum()), 'Masa T1 t': total_masa('masa_turno1'), 'Masa T2 t': total_masa('masa_turno2'), 'Masa t': total_masa('masa_total'), 'H torre': round(g['H_op'].sum(min_count=1), 1) if g['H_op'].notna().any() else None})
    tabla = pd.concat([g[cols], pd.DataFrame([tot])], ignore_index=True)
    cab = f'MÓDULO {int(r.modulo)} · PAD {int(r.pad_id)} · CAMPAÑA {int(r.campana)} — {r.n_dias_act} días apilando, {r.n_dias_inact} sin apilar · {r.vol_total:,.0f} m³ · {r.masa_total:,.0f} t · ρ {r.rho_proy:.3f} t/m³'
    if pd.isna(r.proy_fin):
        cruce = 'Proyección no disponible: faltan una tasa o una densidad válidas. Se muestra la medición.'
    elif pd.isna(r.delta_cruce):
        cruce = f'Cierra {r.proy_fin:%Y-%m-%d %H:%M}, en turno 2 — después del cruce de las {r.cruce_turno:%H:%M} del {r.cruce_turno:%d-%m}. No corre el cierre de ventana: {r.cierre_corrido:%d-%m %H:%M}.'
    else:
        cruce = f'Cierra {r.proy_fin:%Y-%m-%d %H:%M}, {r.delta_cruce:.2f} h ANTES del cruce de las {r.cruce_turno:%H:%M} del {r.cruce_turno:%d-%m}. El bloque siguiente arranca ahí y no a las 20:00, y el cierre de ventana se corre lo mismo: {r.cierre_corrido:%d-%m %H:%M} en vez de 08:00.'
    return html.Div([html.Div(cab, style={'fontFamily': MONO, 'fontSize': '11px', 'color': C['text'], 'fontWeight': '700', 'letterSpacing': '0.04em', 'marginBottom': '6px'}), html.Div(cruce, style={'fontFamily': MONO, 'fontSize': '11px', 'color': C['amber'], 'lineHeight': '1.5', 'borderLeft': f"2px solid {C['amber']}", 'paddingLeft': '10px', 'marginBottom': '10px'}), _table(tabla, cols, [{'if': {'column_id': 'Masa T1 t'}, 'color': C['shift1']}, {'if': {'column_id': 'Masa T2 t'}, 'color': C['shift2']}, {'if': {'filter_query': '{Cruza turno} = sí', 'column_id': 'Cruza turno'}, 'color': C['ok']}, {'if': {'row_index': len(g)}, 'fontWeight': '700', 'backgroundColor': C['bg']}], orden=False, page_size=max(len(g) + 1, 5))])

def kpi(label, value, color=C['text']):
    return html.Div([html.Div(label, style={'fontFamily': MONO, 'fontSize': '9.5px', 'color': C['sub'], 'textTransform': 'uppercase', 'letterSpacing': '0.05em'}), html.Div(value, style={'fontFamily': MONO, 'fontSize': '21px', 'fontWeight': '700', 'color': color, 'marginTop': '4px'})], style={'background': C['panel'], 'border': f"1.5px solid {C['border']}", 'borderRadius': '10px', 'boxShadow': '0 1px 4px rgba(26, 26, 46, 0.05)', 'padding': '14px 14px 12px', 'flex': '1', 'minWidth': '150px'})

def _rho_sem_txt(res):
    """Mediana y dispersion de la densidad a la resolucion del levantamiento.

    La dispersion es el CV de validacion.cv, el mismo que usan el motor y los
    reportes: antes cada uno lo escribia a mano y no todos trataban igual los
    infinitos ni las series de un solo dato."""
    w = res.get('weekly')
    if w is None or not len(w):
        return 'n/d'
    d = w.loc[w.sem_completa, 'densidad_sem'].replace([np.inf, -np.inf], np.nan).dropna()
    if not len(d):
        return 'n/d'
    c = val.cv(d)
    return f'{d.median():.3f} ±{c:.0%}' if c == c else f'{d.median():.3f}'
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
