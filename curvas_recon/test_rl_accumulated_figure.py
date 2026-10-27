import ast
from collections import OrderedDict
from pathlib import Path
from threading import RLock

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from curvas_recon.rl_series import visible_xaxis_range


def load_function(name, ns):
    source=Path(__file__).with_name('pad_dashboard.py')
    tree=ast.parse(source.read_text(encoding='utf8'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
    return ns[name]


@pytest.mark.parametrize('group', [False, True])
def test_accumulated_chart_includes_irrigation_before_first_recovery_and_keeps_style(group):
    days=pd.date_range('2025-12-29','2026-01-03')
    ws,we=days[3],days[-1]
    def daily(_label,num,*args,mode,riego_frame):
        factor=1 if num==10 else 3
        q=[10*factor]*3+[20*factor,0,30*factor]
        if mode=='reconciliado':q[3:]=[40*factor,0,60*factor]
        if num==26:q[0]=None
        return dict(zip(days,q)),True
    ns=dict(__package__='curvas_recon',pd=pd,np=np,go=go,
        _store_matches_case=lambda *_: True,_get_group_raw=lambda *_: {},
        _store_window=lambda *_:(ws,we,3),
        _rl_tms_by_pile=lambda *_:{('SULFUROS',10):{'tms':100,'f0':days[0]},
                                   ('SULFUROS',26):{'tms':300,'f0':days[1]}},
        _PAD_TO_LABEL={'rsu':'SULFUROS'},_rl_member_daily=daily,
        _RL_RIEGO_CACHE_LOCK=RLock(),
        _RL_RIEGO_CACHE=OrderedDict({('qa','SULFUROS','2025-12-29','2025-12-31'):object()}),
        visible_xaxis_range=visible_xaxis_range)
    source=go.Figure([
        go.Scatter(x=[days[2],days[3]],y=[20,30],name='Curva reconciliada histórica'),
        go.Scatter(x=days[3:],y=[28,29,31],name='Recuperación medida'),
        go.Scatter(x=days[3:],y=[30,31,33],name='Recuperación reconciliada')])
    source.update_layout(paper_bgcolor='#FFFFFF',plot_bgcolor='#FFFFFF',
                         font={'family':'Inter','color':'#111827'},
                         xaxis={'type':'date','range':[str(days[2]),str(days[-1])]},
                         yaxis={'range':[0.5,80],'autorange':False})
    source.add_vrect(x0=ws,x1=we,fillcolor='orange')
    build=load_function('_rl_chart_for_members',ns)
    fig=build(['rsu-P10','rsu-P26'] if group else ['rsu-P10'],
              {'raw_token':'qa'},10013,source,'QA',accumulated=True)
    traces={t.name:t for t in fig.data}
    assert set(traces)==set(t.name for t in source.data)
    assert list(traces['Recuperación medida'].x)==pytest.approx([10.2,10.2,17.4] if group else [12,12,19.2])
    assert list(traces['Recuperación reconciliada'].x)==pytest.approx([15,15,29.4] if group else [16.8,16.8,31.2])
    assert traces['Curva reconciliada histórica'].x[0]==pytest.approx(5.4 if group else 7.2)
    assert list(traces['Recuperación medida'].y)==[28,29,31]
    assert fig.layout.xaxis.type=='linear' and fig.layout.xaxis.range is None
    assert list(fig.layout.yaxis.range)==[0.5,80]
    assert len(fig.layout.shapes)==1 and len(source.layout.shapes)==1
    assert fig.layout.shapes[0].x0==pytest.approx(5.4 if group else 7.2)
    assert fig.layout.shapes[0].x1==pytest.approx(29.4 if group else 31.2)
    assert fig.layout.shapes[0].opacity==0.08
    assert fig.layout.font.family=='Inter' and fig.layout.paper_bgcolor=='#FFFFFF'
    assert list(traces['Recuperación medida'].customdata)==['2026-01-01','2026-01-02','2026-01-03']


def test_daily_partial_history_cache_cannot_hide_full_accumulation_prefix():
    days=pd.date_range('2025-12-29','2026-01-01')
    ns=dict(__package__='curvas_recon',pd=pd,np=np,
            _RL_DAILY_CACHE_LOCK=RLock(),_RL_DAILY_CACHE=OrderedDict())
    read=load_function('_rl_member_daily',ns)
    row={'f0':days[0]}
    raw={'res':{'daily':[{'label':'SULFUROS','parcela':'P10','date':days[-1],
                          'q_riego_medido':20,'q_riego_final':40}]}}
    narrow=pd.DataFrame({'P10':[10]},index=[days[2]])
    full=pd.DataFrame({'P10':[10,10,10]},index=days[:3])
    old,_=read('SULFUROS',10,row,raw,days[-1],days[-1],'qa',riego_frame=narrow)
    new,_=read('SULFUROS',10,row,raw,days[-1],days[-1],'qa',riego_frame=full)
    assert old[days[0]] is None and new[days[0]]==10
    assert len(ns['_RL_DAILY_CACHE'])==2
