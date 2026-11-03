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


def solution_figures(res, label, num):
    """Only current-Case flows/concentrations. NULL drainage stays a gap."""
    rows = sorted([r for r in res.get('daily', [])
                   if r.get('label') == label and r.get('parcela') == f'P{num:02d}'],
                  key=lambda r: r['date'])
    xs = [r['date'] for r in rows]
    flow = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         subplot_titles=('Riego observado', 'Drenaje modelado'))
    concentrations = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                   subplot_titles=('Cu riego observado', 'Cu drenaje observado'))
    for fig, fields in ((flow, ('q_riego_final', 'q_pls_final')),
                        (concentrations, ('cu_riego_recon', 'cu_pls_recon'))):
        for index, field in enumerate(fields, 1):
            fig.add_trace(go.Scatter(x=xs, y=[r.get(field) for r in rows],
                                    mode='lines+markers', connectgaps=False,
                                    name=('Riego' if index == 1 else 'Drenaje')),
                          row=index, col=1)
        fig.update_layout(template='plotly_white', height=540, hovermode='x unified',
                          title=f'{label} P{num:02d} · ventana del ensayo local')
    flow.update_yaxes(title_text='m³/h')
    concentrations.update_yaxes(title_text='g/L')
    if rows and all(r.get('q_pls_final') is None for r in rows):
        flow.add_annotation(text='Sin caudal de drenaje independiente; se usa recuperación observada',
                            x=.5, y=.2, xref='paper', yref='paper', showarrow=False)
    return flow, concentrations


def recovery_figure(res, label, num, cycles=()):
    series = direct_series(res, label, num, cycles)
    fig = go.Figure()
    if series:
        fig.add_trace(go.Scatter(x=series['xs'], y=series['ys'], customdata=series['sources'],
                                mode='lines+markers', name='Resultado local', connectgaps=False,
                                hovertemplate='%{x|%d/%m/%Y}<br>%{y:.3f}%<br>%{customdata}<extra></extra>'))
        fig.add_trace(go.Scatter(x=series['xs'], y=series['measured_ys'],
                                mode='lines', name='Observado', connectgaps=False,
                                line=dict(color='#9CA3AF', dash='dot')))
    fig.update_layout(template='plotly_white', title=f'{label} P{num:02d} · recuperación directa',
                      yaxis_title='Recuperación (%)', hovermode='x unified')
    fig.add_annotation(text='Caso e historia de agosto: fuente congelada · ensayo neto local',
                       x=.5, y=1.08, xref='paper', yref='paper', showarrow=False)
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


def trial_bars(res, tab_value):
    """Source-backed summary; no zero/proxy substitution for unknown flows."""
    keys, before, after = [], [], []
    ws, we = pd.Timestamp(res['week_start']), pd.Timestamp(res['week_end'])
    for pile in res.get('piles', []):
        label, p = pile['label'], pile['parcela']
        rows = pile['daily']
        keys.append(f'{label[:2]}-{p}')
        if tab_value == 'tab-flujo':
            vals = [r.get('q_riego_final') for r in rows]
            value = sum(vals)*24 if all(v is not None for v in vals) else None
            before.append(value)
            after.append(value)
        elif tab_value == 'tab-cus':
            vals = [r.get('cu_pls_recon') for r in rows]
            value = sum(v for v in vals if v is not None)/sum(v is not None for v in vals) if any(v is not None for v in vals) else None
            before.append(value)
            after.append(value)
        else:
            rr = sorted([r for r in res.get('recovery_rows', [])
                         if r['pad'] == label and r['pile'] == p], key=lambda r: r['date'])
            base = next((r for r in rr if pd.Timestamp(r['date']) == ws-pd.Timedelta(days=1)), None)
            last = next((r for r in rr if pd.Timestamp(r['date']) == we), None)
            before.append((last['observed_pct']-base['official_pct'])*base['cu_apilado_t']/100 if base and last else None)
            if base and last:
                after.append((last['reconciled_pct']-base['official_pct'])*base['cu_apilado_t']/100)
            else:
                values = [None if r.get('fino_pls_final') is None or r.get('fino_riego_final') is None else
                          .024*(r['fino_pls_final']-r['fino_riego_final']) for r in rows]
                after.append(sum(values) if all(v is not None for v in values) else None)
    fig = go.Figure([go.Bar(x=keys, y=before, name='Observado / base oficial'),
                     go.Bar(x=keys, y=after, name='Resultado local')])
    title, unit = {'tab-flujo': ('Riego de la ventana', 'm³'),
                   'tab-cus': ('Cu drenaje: media diaria', 'g/L')}.get(tab_value, ('Cu neto de la ventana', 't Cu'))
    fig.update_layout(template='plotly_white', barmode='group', title=title, yaxis_title=unit)
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
