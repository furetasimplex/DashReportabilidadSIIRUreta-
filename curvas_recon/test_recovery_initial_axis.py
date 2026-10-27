import ast
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest


@pytest.mark.parametrize('initial', [0.0, 0.8668012268859595, 30.0])
def test_recovery_yaxis_starts_at_campaign_initial_without_changing_points(initial):
    path=Path(__file__).with_name('pad_dashboard.py')
    tree=ast.parse(path.read_text(encoding='utf8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=='_join_recovery_boundary')
    ns={'np':np,'pd':pd}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns)
    fig=go.Figure([go.Scatter(x=['2026-09-01','2026-10-01'],y=[68.083276,69.331149],
                             name='Curva reconciliada histórica')])
    ns['_join_recovery_boundary'](fig,initial)
    assert fig.layout.yaxis.range[0]==initial
    assert fig.layout.yaxis.range[1]>69.331149
    assert fig.layout.yaxis.autorange is False
    assert list(fig.data[0].y)==[68.083276,69.331149]
    assert len(fig.data[0].x)==2


def test_initial_axis_does_not_clip_a_lower_visible_recovery():
    path=Path(__file__).with_name('pad_dashboard.py')
    tree=ast.parse(path.read_text(encoding='utf8'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=='_join_recovery_boundary')
    ns={'np':np,'pd':pd}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns)
    fig=go.Figure([go.Scatter(x=['2026-09-01','2026-10-01'],y=[2.0,4.0])])
    ns['_join_recovery_boundary'](fig,3.0)
    assert fig.layout.yaxis.range[0]==2.0
