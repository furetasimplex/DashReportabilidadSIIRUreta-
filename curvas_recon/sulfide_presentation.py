"""Render/export direct recovery without inferring unmeasured drainage."""
from io import BytesIO
import json

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def direct_series(res, label, num, cycles=()):
    rows = [r for r in res.get('recovery_rows', [])
            if r['pad'] == label and r['pile'] == f'P{num:02d}']
    if not rows:
        return None
    if len({r['campaign'] for r in rows}) != 1:
        raise ValueError('Varias campanas para una pila; seleccione una campana')
    rows.sort(key=lambda r: r['date'])
    earliest = pd.Timestamp(rows[0]['date'])
    birth = pd.Timestamp(rows[0]['first_irrigation'])
    context = {}
    for cycle in cycles:
        for day, value in zip(cycle.get('dates') or [], cycle.get('values') or []):
            stamp = pd.Timestamp(day).normalize()
            if birth <= stamp < earliest and pd.notna(value):
                context[stamp] = dict(rows[0], date=stamp.date().isoformat(),
                                      reconciled_pct=float(value), observed_pct=float(value),
                                      recovery_source='measured_history')
    rows = [context[d] for d in sorted(context)] + rows
    names = {'official': 'Historico oficial conservado',
             'observed': 'Medido (pila protegida)', 'net_fit': 'Reconciliado del Caso',
             'measured_history': 'Historico medido (contexto de campana)'}
    return dict(xs=[pd.Timestamp(r['date']) for r in rows],
                ys=[r['reconciled_pct'] for r in rows],
                measured_ys=[r['observed_pct'] for r in rows],
                sources=[names.get(r.get('recovery_source'), 'Historico oficial conservado') for r in rows],
                cu_tf=rows[0]['cu_apilado_t'], capped=False,
                historical_available=True, historical_error=None)


FDRENA_PROXY = 0.95        # Q PLS medido = 0.95 x riego medido (no hay sensor de drenaje)
K_F = 0.024                # m3/h * g/L * 24 h / 1000 -> t Cu/dia
OFFICIAL_COLOR, MEASURED_COLOR, RECON_COLOR = '#6B7280', '#9CA3AF', '#2a78d6'


def _number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value == value else None


def _window(res):
    return pd.Timestamp(res['week_start']).normalize(), pd.Timestamp(res['week_end']).normalize()


def _daily_rows(res, label, pile):
    """Filas diarias de una pila (ambos pads), ordenadas por fecha."""
    return sorted((r for r in res.get('daily', [])
                   if r.get('label') == label and r.get('parcela') == pile),
                  key=lambda r: pd.Timestamp(r['date']))


def _series(rows, field, fallback=None):
    out = []
    for row in rows:
        value = _number(row.get(field))
        if value is None and fallback is not None:
            value = fallback(row)
        out.append(value)
    return out


def _proxy_pls(row):
    q = _number(row.get('q_riego_medido'))
    return None if q is None else FDRENA_PROXY * q


def solution_figures(res, label, num, official_rows=()):
    """Flujos y concentraciones de una pila: UNA serie oficial antes de la ventana
    del Caso y, dentro de ella, la serie medida y la reconciliada.

    `official_rows`: filas guardadas de casos oficiales anteriores (claves `date`,
    `q`, `q_pls`, `cu_riego`, `cu_drena`). Caudal PLS medido = 0.95 x riego medido;
    en una pila sin ajuste (madura) el reconciliado es el mismo valor medido."""
    ws, we = _window(res)
    pile = f'P{num:02d}'
    rows = _daily_rows(res, label, pile)
    xs = [pd.Timestamp(r['date']).normalize() for r in rows]
    history = sorted((r for r in official_rows if pd.Timestamp(r['date']).normalize() < ws),
                     key=lambda r: pd.Timestamp(r['date']))
    hx = [pd.Timestamp(r['date']).normalize() for r in history]

    q_med = _series(rows, 'q_riego_medido')
    q_rec = _series(rows, 'q_riego_final', lambda r: _number(r.get('q_riego_medido')))
    pls_med = _series(rows, 'q_pls_medido', _proxy_pls)
    pls_rec = _series(rows, 'q_pls_final', _proxy_pls)
    pls_rec = [rec if rec is not None else med for rec, med in zip(pls_rec, pls_med)]
    cr_med = _series(rows, 'cu_riego_medido')
    cr_rec = _series(rows, 'cu_riego_recon', lambda r: _number(r.get('cu_riego_medido')))
    cp_med = _series(rows, 'cu_pls_medido')
    cp_rec = _series(rows, 'cu_pls_recon', lambda r: _number(r.get('cu_pls_medido')))
    official = lambda field, fallback=None: [
        _number(r.get(field)) if _number(r.get(field)) is not None else (fallback(r) if fallback else None)
        for r in history]
    q_pls_hist = official('q_pls', lambda r: None if _number(r.get('q')) is None or _number(r.get('fdrena')) is None
                          else _number(r['q']) * _number(r['fdrena']))

    def panels(titles, specs, ylabels, title):
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, subplot_titles=titles)
        for row_index, (hist, med, rec, med_name, rec_name, color) in enumerate(specs, 1):
            if any(v is not None for v in hist):
                fig.add_trace(go.Scatter(x=hx, y=hist, mode='lines', name='Oficial (histórico)', connectgaps=False,
                                         line=dict(color=OFFICIAL_COLOR, width=1.8), legendgroup='oficial',
                                         showlegend=row_index == 1), row=row_index, col=1)
            fig.add_trace(go.Scatter(x=xs, y=med, mode='lines', name=med_name, connectgaps=False,
                                     line=dict(color=color, width=1.6, dash='dash')), row=row_index, col=1)
            fig.add_trace(go.Scatter(x=xs, y=rec, mode='lines+markers', name=rec_name, connectgaps=False,
                                     line=dict(color=color, width=3), marker=dict(size=6)), row=row_index, col=1)
        fig.add_vrect(x0=ws, x1=we + pd.Timedelta(days=1), fillcolor='#E86D1F', opacity=0.08, line_width=1,
                      line_color='#E86D1F', layer='below', row='all', col='all')
        fig.update_layout(template='plotly_white', height=640, hovermode='x unified', uirevision='keep',
                          title=f'{label} {pile} · {title}', legend=dict(bgcolor='rgba(0,0,0,0)'),
                          margin=dict(l=50, r=30, t=70, b=40))
        fig.update_yaxes(title_text=ylabels[0], row=1, col=1)
        fig.update_yaxes(title_text=ylabels[1], row=2, col=1)
        return fig

    flow = panels(('Caudal de riego', 'Caudal de PLS'),
                  [(official('q'), q_med, q_rec, 'Riego (medido)', 'Riego (reconciliado)', '#2a78d6'),
                   (q_pls_hist, pls_med, pls_rec, 'PLS (medido, 0,95 × riego)', 'PLS (reconciliado)', '#E86D1F')],
                  ('Q riego (m³/h)', 'Q PLS (m³/h)'), 'caudales: medido y reconciliado en la ventana')
    conc = panels(('Cu de riego', 'Cu de PLS'),
                  [(official('cu_riego'), cr_med, cr_rec, 'Cu riego (medido)', 'Cu riego (reconciliado)', '#2a78d6'),
                   (official('cu_drena'), cp_med, cp_rec, 'Cu PLS (medido)', 'Cu PLS (reconciliado)', '#E86D1F')],
                  ('Cu riego (g/L)', 'Cu PLS (g/L)'), 'concentraciones: medido y reconciliado en la ventana')
    return flow, conc


def recovery_figure(res, label, num, cycles=()):
    """Recuperacion de una pila: serie OFICIAL antes de la ventana del Caso; dentro de
    ella, la serie medida y la reconciliada (en una madura coinciden)."""
    series = direct_series(res, label, num, cycles)
    ws, we = _window(res)
    fig = go.Figure()
    if series:
        points = list(zip(series['xs'], series['ys'], series['measured_ys'], series['sources']))
        before = [(x, y) for x, y, _m, _s in points if x < ws and y is not None]
        inside = [(x, y, m) for x, y, m, _s in points if ws <= x <= we]
        if before:
            fig.add_trace(go.Scatter(x=[x for x, _ in before], y=[y for _, y in before], mode='lines',
                                     name='Oficial (histórico)', connectgaps=False,
                                     line=dict(color=OFFICIAL_COLOR, width=2.2),
                                     hovertemplate='%{x|%d/%m/%Y}<br>%{y:.3f}%<extra>Oficial</extra>'))
        anchor = [before[-1]] if before else []                    # une la ventana con el ultimo dato oficial
        fig.add_trace(go.Scatter(x=[x for x, _ in anchor] + [x for x, _, _ in inside],
                                 y=[y for _, y in anchor] + [m for _, _, m in inside], mode='lines',
                                 name='Medido', connectgaps=False, line=dict(color=MEASURED_COLOR, width=1.8, dash='dash'),
                                 hovertemplate='%{x|%d/%m/%Y}<br>%{y:.3f}%<extra>Medido</extra>'))
        fig.add_trace(go.Scatter(x=[x for x, _ in anchor] + [x for x, _, _ in inside],
                                 y=[y for _, y in anchor] + [y for _, y, _ in inside], mode='lines+markers',
                                 name='Reconciliado', connectgaps=False, line=dict(color=RECON_COLOR, width=2.8),
                                 marker=dict(size=5),
                                 hovertemplate='%{x|%d/%m/%Y}<br>%{y:.3f}%<extra>Reconciliado</extra>'))
        fig.add_vrect(x0=ws, x1=we + pd.Timedelta(days=1), fillcolor='#E86D1F', opacity=0.08, line_width=1,
                      line_color='#E86D1F', layer='below')
        if inside and all(m is None for _, _, m in inside):
            fig.add_annotation(x=.5, y=1.08, xref='paper', yref='paper', showarrow=False,
                               text='Sin recuperación medida en la ventana: pila nueva, solo se muestra el ajuste')
    fig.update_layout(template='plotly_white', title=f'{label} P{num:02d} · recuperación acumulada',
                      yaxis_title='Recuperación (%)', hovermode='x unified', legend=dict(bgcolor='rgba(0,0,0,0)'))
    return fig


def direct_member(res, label, num, ws, we, cycles=()):
    """Campaign identity and Cu denominator come from the captured rows."""
    s = direct_series(res, label, num, cycles)
    if s is None:
        return None
    inside = [i for i, d in enumerate(s['xs']) if ws <= d <= we]
    before = [i for i, d in enumerate(s['xs']) if d < ws]
    def curve(indices, values):
        return dict(xs=[s['xs'][i] for i in indices], ys=[values[i] for i in indices],
                    sources=[s['sources'][i] for i in indices])
    hist = curve(before, s['ys'])
    return dict(id=f'rsu-P{num:02d}', cu_tf_t=s['cu_tf'],
                initial_recovery_pct=s['ys'][0] if before else None,
                series=curve(list(range(len(s['xs']))), s['ys']),
                measured_series=curve(inside, s['measured_ys']),
                reconciled_series=curve(inside, s['ys']),
                official_history_series=hist, solver_history_series=dict(xs=[], ys=[], sources=[]),
                history_series=hist)


def pile_window_metrics(res, label, pile):
    """Metricas medido / reconciliado de una pila en la ventana del Caso (ambos pads).

    Cu neto (t): Oxidos desde sus finos diarios; Sulfuros reconciliado desde el metodo
    (recuperacion) y medido desde la recuperacion observada, o 0.95 x riego si la pila no
    tiene lectura al cierre (`net_med_proxy`). Caudales en m3 de la ventana; Cu en g/L medios."""
    ws, we = _window(res)
    rows = _daily_rows(res, label, pile)
    days = lambda field, fallback=None: _series(rows, field, fallback)
    total = lambda values, factor=24.0: (sum(v for v in values if v is not None) * factor
                                         if any(v is not None for v in values) else None)
    mean = lambda values: (sum(v for v in values if v is not None) / len([v for v in values if v is not None])
                           if any(v is not None for v in values) else None)
    q_pls_med = days('q_pls_medido', _proxy_pls)
    out = dict(
        q_riego_med=total(days('q_riego_medido')),
        q_riego_rec=total(days('q_riego_final', lambda r: _number(r.get('q_riego_medido')))),
        q_pls_med=total(q_pls_med),
        q_pls_rec=total([rec if rec is not None else med for rec, med in zip(days('q_pls_final'), q_pls_med)]),
        cu_riego_med=mean(days('cu_riego_medido')),
        cu_riego_rec=mean(days('cu_riego_recon', lambda r: _number(r.get('cu_riego_medido')))),
        cu_pls_med=mean(days('cu_pls_medido')),
        cu_pls_rec=mean(days('cu_pls_recon', lambda r: _number(r.get('cu_pls_medido')))),
        net_med=None, net_rec=None, net_med_proxy=False)
    recovery = sorted((r for r in res.get('recovery_rows', []) if r['pad'] == label and r['pile'] == pile),
                      key=lambda r: pd.Timestamp(r['date']))
    base = next((r for r in recovery if pd.Timestamp(r['date']) == ws - pd.Timedelta(days=1)), None)
    last = next((r for r in recovery if pd.Timestamp(r['date']) == we), None)
    if base and last:                                            # Sulfuros: resultado del metodo
        cu = base['cu_apilado_t']
        out['net_rec'] = (last['reconciled_pct'] - base['official_pct']) * cu / 100
        if last.get('observed_pct') is not None:
            out['net_med'] = (last['observed_pct'] - base['official_pct']) * cu / 100
        else:                                                    # sin lectura al cierre: 0.95 x riego
            ext = [K_F * (FDRENA_PROXY * q * cd - q * cr) if q else 0.0
                   for q, cd, cr in zip(days('q_riego_medido'), days('cu_pls_medido'), days('cu_riego_medido'))
                   if q is not None and (not q or (cd is not None and cr is not None))]
            out['net_med'], out['net_med_proxy'] = (sum(ext) if ext else None), True
    else:                                                        # Oxidos (motor): finos diarios
        def net(pls, riego):
            pairs = [(a, b) for a, b in zip(days(pls), days(riego)) if a is not None and b is not None]
            return K_F * sum(a - b for a, b in pairs) if pairs else None
        out['net_med'] = net('fino_pls_medido', 'fino_riego_medido')
        out['net_rec'] = net('fino_pls_final', 'fino_riego_final')
    return out


def trial_bars(res, tab_value):
    """Barras por pila (Oxidos y Sulfuros), medido y reconciliado, para la ventana del Caso."""
    keys, metrics = [], []
    ordered = sorted(res.get('piles', []), key=lambda p: (p['label'] != 'OXIDOS', int(str(p['parcela']).lstrip('Pp'))))
    for pile in ordered:
        keys.append(f"{pile['label'][:2]}-{pile['parcela']}")
        metrics.append(pile_window_metrics(res, pile['label'], pile['parcela']))
    col = lambda name: [m[name] for m in metrics]
    fig = go.Figure()
    if tab_value == 'tab-flujo':
        title, unit = 'Caudal total de la ventana', 'm³'
        for name, field, color in (('Riego (medido)', 'q_riego_med', '#9CA3AF'), ('Riego (reconciliado)', 'q_riego_rec', '#2a78d6'),
                                   ('PLS (medido, 0,95 × riego)', 'q_pls_med', '#6B7280'), ('PLS (reconciliado)', 'q_pls_rec', '#E86D1F')):
            fig.add_trace(go.Bar(x=keys, y=col(field), name=name, marker_color=color))
    elif tab_value == 'tab-cus':
        title, unit = 'Cu medio de la ventana', 'g/L'
        for name, field, color in (('Cu riego (medido)', 'cu_riego_med', '#9CA3AF'), ('Cu riego (reconciliado)', 'cu_riego_rec', '#2a78d6'),
                                   ('Cu PLS (medido)', 'cu_pls_med', '#6B7280'), ('Cu PLS (reconciliado)', 'cu_pls_rec', '#E86D1F')):
            fig.add_trace(go.Bar(x=keys, y=col(field), name=name, marker_color=color))
    else:
        title, unit = 'Cu neto de la ventana', 't Cu'
        fig.add_trace(go.Bar(x=keys, y=col('net_med'), name='Cu neto (medido)', marker_color='#9CA3AF'))
        fig.add_trace(go.Bar(x=keys, y=col('net_rec'), name='Cu neto (reconciliado)', marker_color='#E86D1F'))
        proxied = [k for k, m in zip(keys, metrics) if m['net_med_proxy']]
        if proxied:
            fig.add_annotation(x=.5, y=1.12, xref='paper', yref='paper', showarrow=False, font=dict(size=11, color='#B45309'),
                               text='Medido estimado con 0,95 × riego (sin lectura de recuperación al cierre): ' + ', '.join(proxied))
    fig.update_layout(template='plotly_white', barmode='group', title=title, yaxis_title=unit,
                      hovermode='x unified', legend=dict(bgcolor='rgba(0,0,0,0)'), margin=dict(t=90))
    return fig


def trial_workbook(res, caso):
    """Export canonical values and provenance; bypass legacy Qd reconstruction."""
    output = BytesIO()
    recovery = pd.DataFrame(res.get('recovery_rows') or [])
    flows = pd.DataFrame(res.get('daily') or [])
    audit = dict(res.get('sulfide_audit') or {})
    audit.update(case_id=caso['id'], official_solver_run_id=caso['run_id'],
                 local_only=True, hydraulic_validation=False,
                 scope='Sulfuros: recuperacion directa. Oxidos: motor existente; flujos en hoja Flujos.')
    metadata = pd.DataFrame([{'campo': k, 'valor': json.dumps(v, ensure_ascii=False, default=str)}
                             for k, v in audit.items()])
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        recovery.to_excel(writer, sheet_name='Recuperacion Sulfuros', index=False)
        flows.to_excel(writer, sheet_name='Flujos', index=False)
        metadata.to_excel(writer, sheet_name='Fuentes y alcance', index=False)
    return output.getvalue()
