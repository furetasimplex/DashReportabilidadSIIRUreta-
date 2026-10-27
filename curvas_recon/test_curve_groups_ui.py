"""Recovery grouping must remain local and preserve the Case copper balance."""
from collections import OrderedDict
from copy import deepcopy
from datetime import date

import dash
import pytest
import pandas as pd
from sqlalchemy.engine import Engine

from curvas_recon import pad_dashboard as dashboard


@pytest.fixture
def local_case(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Local grouping must not query SQL or operational history')
    monkeypatch.setattr(Engine, 'connect', forbidden)
    monkeypatch.setattr(dashboard, '_fechas_actividad', forbidden)
    monkeypatch.setattr(dashboard, '_GROUP_RAW_CACHE', {})
    monkeypatch.setattr(dashboard, '_GROUP_MEMBER_CACHE', OrderedDict())
    monkeypatch.setattr(dashboard, '_DATA_READY', True)
    monkeypatch.setattr(dashboard, '_FULL_DATA_READY', True)
    monkeypatch.setattr(dashboard, 'WIP_META', {'SULFUROS': {
        'P21': {'CuTf': 100., 'ini_aporte': '2026-09-01'},
        'P22': {'CuTf': 300., 'ini_aporte': '2026-09-01'},
    }})
    monkeypatch.setattr(dashboard, 'CYCLES_SU', {
        21: [{'dates': [date(2026, 9, 30)], 'values': [10.]}],
        22: [{'dates': [date(2026, 9, 30)], 'values': [20.]}],
    })
    raw = {'caso': {'id': 10013, 'run_id': 10145},
           'ws': '2026-10-01', 'we': '2026-10-03', 'res': {'piles': [
               {'label': 'SULFUROS', 'parcela': 'P21', 'daily': []},
               {'label': 'SULFUROS', 'parcela': 'P22', 'daily': []},
           ]}}
    for pile in raw['res']['piles']:
        pile['daily'] = [{'date': f'2026-10-0{day}', 'fino_pls_final': 50.,
                          'fino_riego_final': 10.} for day in (1, 2, 3)]
    monkeypatch.setattr(dashboard, '_load_recon_raw', lambda *_: (raw, None))
    def empty_material(_label, start, end):
        dates = pd.date_range(start, end, freq='D')
        return {'riego': pd.DataFrame(index=dates),
                'cu_riego': pd.Series(index=dates, dtype=float),
                'drena_cu': pd.DataFrame(index=dates)}
    monkeypatch.setattr(dashboard, '_load_material_window', empty_material)
    data = {'caso_id': 10013, 'caso_run_id': 10145, 'raw_token': 'offline',
            'week_start': '2026-10-01', 'week_end': '2026-10-03'}
    group = {'id': 'g', 'name': 'SU21 + SU22', 'members': ['rsu-P21', 'rsu-P22']}
    return raw, data, group


def test_group_graph_uses_net_fines_and_blue_only_inside_case(local_case):
    _, data, group = local_case
    figure, warning = dashboard._build_combined_recovery_chart(group, data, 10013)
    assert not warning
    blue = next(trace for trace in figure.data if trace.line.color == '#2a78d6')
    observed = {pd.Timestamp(day).date().isoformat(): value for day, value in zip(blue.x, blue.y) if value is not None}
    assert observed['2026-10-01'] == pytest.approx(17.98)
    assert observed['2026-10-03'] == pytest.approx(18.94)
    assert all('2026-10-01' <= day <= '2026-10-03' for day in observed)
    assert all(trace.connectgaps is False for trace in figure.data)
    assert len(figure.layout.shapes)==1
    assert pd.Timestamp(figure.layout.shapes[0].x0)==pd.Timestamp('2026-10-01')
    assert pd.Timestamp(figure.layout.shapes[0].x1)==pd.Timestamp('2026-10-04')
    assert figure.layout.shapes[0].opacity==0.08


def test_individual_and_group_initial_axes_exclude_previous_campaigns(local_case, monkeypatch):
    _, data, group = local_case
    monkeypatch.setattr(dashboard, '_measured_cycles_active_in_window',
                        lambda label, num, *_: dashboard._measured_cycles(label, num))
    for num in (21, 22):
        dashboard.CYCLES_SU[num].insert(0, {
            'dates': [date(2025, 9, 1)], 'values': [0.001]})
    individual=dashboard._build_recovery_chart(
        'rsu-P21', pd.Timestamp(data['week_start']), pd.Timestamp(data['week_end']), data,10013)
    assert individual.layout.yaxis.range[0]==pytest.approx(10.0)
    combined, warning=dashboard._build_combined_recovery_chart(group,data,10013)
    assert not warning
    # CuTf weights 100 and 300; previous campaign's 0.001 must not lower the axis.
    assert combined.layout.yaxis.range[0]==pytest.approx((10*100+20*300)/400)


def test_groups_keep_full_historical_primary_records(local_case, monkeypatch):
    _, data, group = local_case
    dates=list(pd.to_datetime(['2026-09-29','2026-09-30','2026-10-01','2026-10-02','2026-10-03']))
    def reconstructed(_label,num,*args,**kwargs):
        base=10.0 if num==21 else 20.0
        return {'xs':dates,'ys':[base+i for i in range(5)],'measured_ys':[None,None,base+2,base+3,base+4],
                'sources':['Histórico reconciliado (registro histórico)']*2+['Reconciliado del Caso']*3,
                'cu_tf':100 if num==21 else 300,'capped':False}
    monkeypatch.setattr(dashboard,'_reconstructed_campaign_series',reconstructed)
    fig,warning=dashboard._build_combined_recovery_chart(group,data,10013)
    assert not warning
    history=next(t for t in fig.data if t.name=='Curva reconciliada histórica')
    points=dict(zip((pd.Timestamp(d).date().isoformat() for d in history.x),history.y))
    assert points['2026-09-29']==pytest.approx(17.5)
    assert points['2026-09-30']==pytest.approx(18.5)


def test_group_unifies_official_and_solver_history_by_date(local_case, monkeypatch):
    _, data, group = local_case
    day = pd.Timestamp('2026-09-20')

    def member(member_id, _raw, _ws, _we):
        pct = 10. if member_id == 'rsu-P21' else 20.
        return {
            'id': member_id,
            'cu_tf_t': 100. if member_id == 'rsu-P21' else 300.,
            'measured_series': {'xs': [], 'ys': []},
            'history_series': {'xs': [day], 'ys': [pct]},
            'official_history_series': {'xs': [day], 'ys': [pct]}
                if member_id == 'rsu-P21' else {'xs': [day], 'ys': [None]},
            'solver_history_series': {'xs': [day], 'ys': [None]}
                if member_id == 'rsu-P21' else {'xs': [day], 'ys': [pct]},
            'reconciled_series': {'xs': [], 'ys': []},
        }

    monkeypatch.setattr(dashboard, '_combined_member_series', member)
    figure, warning = dashboard._build_combined_recovery_chart(group, data, 10013)
    assert warning == ''
    history = next(trace for trace in figure.data if trace.name == 'Curva reconciliada histórica')
    assert [pd.Timestamp(value).normalize() for value in history.x] == [day]
    assert list(history.y) == [pytest.approx(17.5)]


def test_missing_daily_copper_is_not_skipped_in_cumulative_group(local_case):
    raw, data, group = local_case
    raw['res']['piles'][1]['daily'].pop(1)
    figure, _ = dashboard._build_combined_recovery_chart(group, data, 10013)
    for trace in figure.data:
        lookup = dict(zip((pd.Timestamp(d).date().isoformat() for d in trace.x), trace.y))
        assert lookup.get('2026-10-02') is None


def test_group_rejects_stale_run_even_on_warm_cache_and_inactive_members(local_case):
    _, data, group = local_case
    assert dashboard._get_group_raw(data, 10013) is not None
    assert dashboard._get_group_raw(dict(data, caso_run_id=999), 10013) is None
    invalid = dict(group, members=['rsu-P21', 'rsu-P28'])
    figure, warning = dashboard._build_combined_recovery_chart(invalid, data, 10013)
    assert not figure.data and 'activas' in warning


def test_new_campaign_does_not_inherit_previous_campaign_anchor(local_case, monkeypatch):
    raw, _, _ = local_case
    meta = deepcopy(dashboard.WIP_META)
    meta['SULFUROS']['P21']['ini_aporte'] = '2026-10-01'
    monkeypatch.setattr(dashboard, 'WIP_META', meta)
    member = dashboard._combined_member_series('rsu-P21', raw, '2026-10-01', '2026-10-03')
    assert member['series']['ys'][0] == pytest.approx(.96)


def test_popup_layout_local_storage_callback_ids_and_visibility(local_case):
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    app.layout = dashboard._build_content_layout()
    dashboard.register_callbacks(app)
    client = app.server.test_client()
    response = client.get('/_dash-layout')
    assert response.status_code == 200
    ids = {}
    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            props = node.get('props', {})
            identifier = props.get('id')
            if isinstance(identifier, str):
                assert identifier not in ids
                ids[identifier] = props
            walk(props.get('children'))
    walk(response.get_json())
    assert ids['curvas-grupos-store']['storage_type'] == 'local'
    assert ids['curvas-grupos-store']['data'] == []
    assert ids['curvas-grupos-modal']['is_open'] is False
    assert 'curvas-grupo-warning' in ids
    assert client.get('/_dash-dependencies').status_code == 200
    defaults = dashboard.switch_recon_pila_tab('tab-rec', None)
    selected = dashboard.switch_recon_pila_tab('tab-rec', 'g')
    assert defaults[0]['display'] == 'block' and defaults[3]['display'] == 'none'
    assert selected[0]['display'] == 'none' and selected[3]['display'] == 'block'
    assert dashboard.switch_recon_pila_tab('tab-flujo', 'g')[4]['display'] == 'none'
    opened = client.post('/_dash-update-component', json={
        'output': 'curvas-grupos-modal.is_open',
        'outputs': {'id': 'curvas-grupos-modal', 'property': 'is_open'},
        'inputs': [{'id': 'curvas-grupos-open', 'property': 'n_clicks', 'value': 1},
                   {'id': 'curvas-grupos-close', 'property': 'n_clicks', 'value': 0}],
        'state': [], 'changedPropIds': ['curvas-grupos-open.n_clicks'],
    })
    assert opened.status_code == 200
    assert opened.get_json()['response']['curvas-grupos-modal']['is_open'] is True
    key, spec = next((key, spec) for key, spec in app.callback_map.items()
                     if 'curvas-grupos-store.data' in key)
    state_values = {
        'curvas-grupo-edit-picker': None, 'curvas-grupo-name': 'SU21 + SU22',
        'curvas-grupo-members': ['rsu-P21', 'rsu-P22'], 'curvas-grupos-store': [],
    }
    # The members dropdown occurs twice: once as selected values and once as
    # the actual set of active options supplied by the current Case.
    states = []
    for item in spec['state']:
        value = state_values[item['id']]
        if item['property'] == 'options':
            value = [{'label': mid, 'value': mid} for mid in ['rsu-P21', 'rsu-P22']]
        states.append(dict(item, value=value))
    outputs = [{'id': output.component_id, 'property': output.component_property}
               for output in spec['output']]
    saved = client.post('/_dash-update-component', json={
        'output': key, 'outputs': outputs,
        'inputs': [dict(item, value=int(item['id'] == 'curvas-grupo-save'))
                   for item in spec['inputs']],
        'state': states, 'changedPropIds': ['curvas-grupo-save.n_clicks'],
    })
    assert saved.status_code == 200
    groups = saved.get_json()['response']['curvas-grupos-store']['data']
    assert len(groups) == 1 and groups[0]['members'] == ['rsu-P21', 'rsu-P22']

    def edit(action, current_groups, selected_id=None, name='SU21 + SU22'):
        edit_states = []
        for item in spec['state']:
            value = {
                'curvas-grupo-edit-picker': selected_id,
                'curvas-grupo-name': name,
                'curvas-grupo-members': ['rsu-P21', 'rsu-P22'],
                'curvas-grupos-store': current_groups,
            }[item['id']]
            if item['property'] == 'options':
                value = [{'label': mid, 'value': mid}
                         for mid in ['rsu-P21', 'rsu-P22']]
            edit_states.append(dict(item, value=value))
        response = client.post('/_dash-update-component', json={
            'output': key, 'outputs': outputs,
            'inputs': [dict(item, value=int(item['id'] == action))
                       for item in spec['inputs']],
            'state': edit_states, 'changedPropIds': [f'{action}.n_clicks'],
        })
        assert response.status_code == 200, response.get_data(as_text=True)
        return response.get_json()['response']['curvas-grupos-store']['data']

    group_id = groups[0]['id']
    renamed = edit('curvas-grupo-save', groups, group_id, 'Sulfuros actuales')
    assert len(renamed) == 1 and renamed[0]['name'] == 'Sulfuros actuales'
    assert edit('curvas-grupo-delete', renamed, group_id) == []
    recreated = edit('curvas-grupo-save', [], name='Grupo temporal')
    assert len(recreated) == 1
    assert edit('curvas-grupo-reset', recreated, recreated[0]['id']) == []


def test_groups_render_as_selectable_tiles_in_pad_scheme(local_case):
    _, data, group = local_case
    saved = [dict(group)]
    component = dashboard._build_status_grid(
        {'transient': ['P21'], 'ss': [], 'nuevas': []},
        {'transient': [], 'ss': [], 'nuevas': []}, 3,
        selected_pila=None, groups=saved, selected_group='g',
    ).to_plotly_json()

    def find_group_tile(node):
        if isinstance(node, (list, tuple)):
            return next((found for child in node
                         if (found := find_group_tile(child)) is not None), None)
        if hasattr(node, 'to_plotly_json'):
            props = node.to_plotly_json().get('props', {})
            if props.get('id') == {'type': 'curvas-group-cell', 'group': 'g'}:
                return props
            return find_group_tile(props.get('children'))
        if isinstance(node, dict):
            props = node.get('props', {})
            if props.get('id') == {'type': 'curvas-group-cell', 'group': 'g'}:
                return props
            return find_group_tile(props.get('children'))
        return None

    tile = find_group_tile(component)
    assert tile is not None
    assert tile['children'] == 'SU21 + SU22'
    assert tile['n_clicks'] == 0
    assert tile['color'] == 'secondary' and tile['outline'] is True
    assert dashboard.highlight_group_tiles('g', [
        {'type': 'curvas-group-cell', 'group': 'g'},
        {'type': 'curvas-group-cell', 'group': 'other'},
    ]) == (['primary', 'secondary'], [False, True])


def test_pad_group_tile_selects_group_and_individual_click_restores_mode(local_case):
    _, data, group = local_case
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    app.layout = dashboard._build_content_layout()
    dashboard.register_callbacks(app)
    client = app.server.test_client()
    key, spec = next((key, spec) for key, spec in app.callback_map.items()
                     if any(output.component_id == 'curvas-grupo-picker'
                            and output.component_property == 'value'
                            for output in (spec['output'] if isinstance(spec['output'], list)
                                           else [spec['output']])))
    outputs = [{'id': output.component_id, 'property': output.component_property}
               for output in (spec['output'] if isinstance(spec['output'], list)
                              else [spec['output']])]

    def post_selection(trigger, pile_click=False, current_group=None):
        inputs, states = [], []
        for item in spec['inputs']:
            identifier = item['id']
            is_group = 'curvas-group-cell' in identifier
            clicked = (is_group and not pile_click) or ('curvas-recon-cell' in identifier and pile_click)
            if identifier == 'curvas-grupos-store':
                value = [] if trigger == 'curvas-grupos-store.data' else ([group] if current_group else [])
            else:
                value = [1] if clicked else [0]
            inputs.append(dict(item, value=value))
        for item in spec['state']:
            identifier = item['id']
            if identifier == 'curvas-recon-pila-store':
                value = None
            elif 'curvas-group-cell' in identifier:
                value = [{'type': 'curvas-group-cell', 'group': 'g'}]
            elif 'curvas-recon-cell' in identifier:
                value = [{'type': 'curvas-recon-cell', 'pad': 'rsu', 'num': 22}]
            elif identifier == 'curvas-grupo-picker':
                value = current_group
            else:
                value = None
            states.append(dict(item, value=value))
        response = client.post('/_dash-update-component', json={
            'output': key, 'outputs': outputs, 'inputs': inputs, 'state': states,
            'changedPropIds': [trigger],
        })
        assert response.status_code == 200, response.get_data(as_text=True)
        return response.get_json()['response']

    selected = post_selection('{"group":"g","type":"curvas-group-cell"}.n_clicks')
    assert selected['curvas-grupo-picker']['value'] == 'g'
    assert selected['curvas-recon-pila-store']['data'] is None
    individual = post_selection('{"num":22,"pad":"rsu","type":"curvas-recon-cell"}.n_clicks',
                                pile_click=True, current_group='g')
    assert individual['curvas-grupo-picker']['value'] is None
    assert individual['curvas-recon-pila-store']['data'] == 'rsu-P22'
    deleted = post_selection('curvas-grupos-store.data', current_group='g')
    assert deleted['curvas-grupo-picker']['value'] is None
    assert deleted['curvas-recon-pila-store']['data'] is None


def test_group_reuses_individual_reconstruction_when_measured_trace_ends_before_case(
        local_case, monkeypatch):
    raw, data, group = local_case
    monkeypatch.setattr(dashboard, 'CYCLES_SU', {
        21: [{'dates': [date(2026, 9, 10)], 'values': [10.]}],
        22: [{'dates': [date(2026, 9, 10)], 'values': [20.]}],
    })

    def complete_material(_label, start, end):
        dates = pd.date_range(start, end, freq='D')
        return {
            'riego': pd.DataFrame({'P21': 1., 'P22': 1.}, index=dates),
            'cu_riego': pd.Series(1., index=dates),
            'drena_cu': pd.DataFrame({'P21': 10., 'P22': 10.}, index=dates),
        }
    monkeypatch.setattr(dashboard, '_load_material_window', complete_material)
    activity_days = list(pd.date_range('2026-09-10', '2026-10-03', freq='D'))
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda _label: (
        {'P21': activity_days, 'P22': activity_days}, {'P21': [], 'P22': []}))

    members = [dashboard._combined_member_series(member_id, raw,
                data['week_start'], data['week_end']) for member_id in group['members']]
    assert max(members[0]['series']['xs']) >= pd.Timestamp('2026-10-01')
    # The measured campaign proxy is not shown as reconciled pre-Case history.
    # Reconciled daily values remain available throughout the Case window.
    assert all(value is not None for member in members
               for day, value in zip(member['reconciled_series']['xs'],
                                     member['reconciled_series']['ys'])
               if pd.Timestamp('2026-10-01') <= pd.Timestamp(day) <= pd.Timestamp('2026-10-03'))

    figure, warning = dashboard._build_combined_recovery_chart(group, data, 10013)
    assert warning == ''
    individual_group = dashboard.combine_recovery_series([
        {'id': member['id'], 'cu_tf_t': member['cu_tf_t'],
         'series': member['reconciled_series']} for member in members])
    blue = next(trace for trace in figure.data if trace.line.color == '#2a78d6')
    assert list(blue.x) == [pd.Timestamp(d) for d in individual_group['xs']]
    assert list(blue.y) == pytest.approx([
        value if source == 'Reconciliado del Caso' else None
        for value, source in zip(individual_group['ys'], individual_group['sources'])])


def test_group_member_cache_isolated_by_raw_token_and_cutf(monkeypatch, local_case):
    raw, data, _group = local_case
    raw_b = deepcopy(raw)
    for pile in raw_b['res']['piles']:
        for day in pile['daily']:
            day['fino_pls_final'] = 80.
    monkeypatch.setattr(dashboard, '_GROUP_RAW_CACHE', {
        'case-a': raw, 'case-b': raw_b,
    })
    a = dashboard._get_group_raw(dict(data, raw_token='case-a'), 10013)
    b = dashboard._get_group_raw(dict(data, raw_token='case-b'), 10013)
    curve_a = dashboard._combined_member_series('rsu-P21', a, data['week_start'], data['week_end'])
    curve_b = dashboard._combined_member_series('rsu-P21', b, data['week_start'], data['week_end'])
    assert curve_a['series']['ys'] != curve_b['series']['ys']

    changed_meta = deepcopy(dashboard.WIP_META)
    changed_meta['SULFUROS']['P21']['CuTf'] = 200.
    monkeypatch.setattr(dashboard, 'WIP_META', changed_meta)
    curve_new_cutf = dashboard._combined_member_series(
        'rsu-P21', a, data['week_start'], data['week_end'])
    assert curve_new_cutf['cu_tf_t'] == pytest.approx(200.)
    assert curve_new_cutf['series']['ys'] != curve_a['series']['ys']



def test_group_highlight_is_blue_and_restores_activity_color(local_case, monkeypatch):
    monkeypatch.setattr(dashboard, '_ACTIVE_SU', {21})
    monkeypatch.setattr(dashboard, '_ACTIVE_OX', set())
    cell_ids = [
        {'type': 'curvas-recon-cell', 'pad': 'rsu', 'num': 21},
        {'type': 'curvas-recon-cell', 'pad': 'rsu', 'num': 22},
    ]
    styles = [
        {'backgroundColor': '#2E9E5B', 'border': '2px solid #ced4da'},
        {'backgroundColor': '#9CA3AF', 'border': '2px solid #ced4da'},
    ]
    res = {'transient': ['P21'], 'ss': [], 'nuevas': []}
    data = {'SULFUROS': res, 'OXIDOS': {}}
    groups = [{'id': 'g1', 'members': ['rsu-P21', 'rsu-P22']},
              {'id': 'g2', 'members': ['rsu-P22']}]

    blue = dashboard.highlight_recon_pila(None, 'g1', groups, data, cell_ids, styles)
    assert [item['backgroundColor'] for item in blue] == ['#2a78d6', '#2a78d6']
    next_group = dashboard.highlight_recon_pila(None, 'g2', groups, data, cell_ids, blue)
    assert [item['backgroundColor'] for item in next_group] == ['#2E9E5B', '#2a78d6']
    individual = dashboard.highlight_recon_pila('rsu-P21', None, groups, data, cell_ids, next_group)
    assert [item['backgroundColor'] for item in individual] == ['#2E9E5B', '#9CA3AF']
    assert individual[0]['border'] == '2px solid #f57c00'
