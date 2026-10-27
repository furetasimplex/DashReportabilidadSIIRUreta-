"""Recovery history plus measured/reconciled daily RL in the Case only."""
import ast
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from curvas_recon.rl_series import visible_xaxis_range


@pytest.mark.parametrize('has_history', [False, True])
@pytest.mark.parametrize('group', [False, True])
@pytest.mark.parametrize('missing_measured', [False, True])
def test_both_rl_series_only_in_case_preserve_recovery_and_real_zeros(has_history, group, missing_measured):
    days = pd.date_range('2026-09-26', '2026-10-03')
    source = Path(__file__).with_name('pad_dashboard.py')
    tree = ast.parse(source.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == '_rl_chart_for_members')
    calls=[]
    def daily(_label, num, *args, mode, riego_frame):
        calls.append((num,mode))
        assert riego_frame is not None
        factor=(1 if num==10 else 2)*(1 if mode=='medido' else 1.5)
        history_factor=1 if num==10 else 2
        values=[0,0,0,10*history_factor,20*history_factor,10*factor,0,20*factor]
        if mode=='medido' and missing_measured:
            values[5]=None
        return dict(zip(days, values)),True
    ns = dict(__package__='curvas_recon', pd=pd, np=np, go=go,
              _store_matches_case=lambda *_: True, _get_group_raw=lambda *_: {},
              _store_window=lambda *_: (pd.Timestamp('2026-10-01'), days[-1], 3),
              _rl_tms_by_pile=lambda *_: {
                  ('SULFUROS',10): {'tms':100,'f0':days[0]},
                  ('SULFUROS',26): {'tms':200,'f0':days[0]}},
              _PAD_TO_LABEL={'rsu': 'SULFUROS'}, _rl_member_daily=daily,
              visible_xaxis_range=visible_xaxis_range,
              _RL_RIEGO_CACHE_LOCK=__import__('threading').RLock(),
              _RL_RIEGO_CACHE=__import__('collections').OrderedDict({
                  ('qa','SULFUROS','2026-09-26','2026-09-30'):object()}))
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), ns)
    original=go.Figure([go.Scatter(x=days,y=[None]*5+[50,51,52],name='Recuperación reconciliada')])
    if has_history:
        original.add_trace(go.Scatter(x=days,y=[None]*3+[48,49]+[None]*3,name='Curva reconciliada histórica'))
    members=['rsu-P10','rsu-P26'] if group else ['rsu-P10']
    fig=ns['_rl_chart_for_members'](members,{'raw_token':'qa'},10013,original,'QA')
    assert len(calls)==len(members)*2
    assert list(fig.data[0].y)[-3:]==[50,51,52]
    assert list(original.data[0].y)[-3:]==[50,51,52]
    rl={t.name:t for t in fig.data if t.yaxis=='y2'}
    assert set(rl)=={'Tasa de lixiviaci\u00f3n medida','Tasa de lixiviaci\u00f3n reconciliada','Curva de tasa de lixiviaci\u00f3n reconciliada hist\u00f3rica'}
    for name,color in [('Tasa de lixiviaci\u00f3n medida','#8B5CF6'),('Tasa de lixiviaci\u00f3n reconciliada','#E86D1F')]:
        trace=rl[name]
        assert trace.line.color==color and trace.line.dash=='solid'
        assert all(y is None for d,y in zip(trace.x,trace.y) if pd.Timestamp(d)<pd.Timestamp('2026-10-01'))
        assert list(trace.y)[-2]==0
    measured=list(rl['Tasa de lixiviaci\u00f3n medida'].y)[-3:]
    recon=list(rl['Tasa de lixiviaci\u00f3n reconciliada'].y)[-3:]
    if missing_measured:
        assert measured[0] is None
    else:
        assert measured[0]==pytest.approx(2.4)
    assert measured[1:]==pytest.approx([0,4.8])
    assert recon==pytest.approx([3.6,0,7.2])
    assert fig.layout.xaxis.type=='date'
    assert pd.Timestamp(fig.layout.xaxis.range[0])==pd.Timestamp('2026-09-29')
    history=rl['Curva de tasa de lixiviaci\u00f3n reconciliada hist\u00f3rica']
    values=dict(zip(history.x,history.y))
    assert values[pd.Timestamp('2026-09-30')]==pytest.approx(4.8)
    assert values[pd.Timestamp('2026-10-01')]==pytest.approx(3.6)
    assert all(v is None for d,v in values.items() if pd.Timestamp(d)>pd.Timestamp('2026-10-01'))


def test_rl_selector_removed_from_layout_and_callback():
    source=Path(__file__).with_name('pad_dashboard.py').read_text(encoding='utf8')
    assert 'curvas-rl-source' not in source
    tree=ast.parse(source)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render_rl_chart')
    assert [a.arg for a in fn.args.args]==['tab_value','data','selected_pila','group_id','groups','caso_id']
