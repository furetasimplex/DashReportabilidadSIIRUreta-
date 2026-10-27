import pandas as pd
import pytest
from . import pad_dashboard as dashboard
from .vista_todas_reconciliadas import add_group_curves, make_figure
from .curve_aggregation import save_local_group
from .report_columns import with_group_columns
from .test_reporte_formato_prod import _doc


def test_multiple_sums_create_without_overwriting_and_reset_editor():
    members=['rox-P01','rox-P02']
    a,msg=save_local_group([],None,'A',members,members)
    assert dashboard.new_curve_sum(1)==(None,'',[])
    b,msg=save_local_group(a,None,'B',members,members)
    assert len(b)==2 and b[0]['id']!=b[1]['id']


def test_group_overview_uses_weighted_recovery_without_mutating_cache():
    dates=list(pd.date_range('2026-10-01',periods=2))
    items=[dict(num=1,start=dates[0],xs=dates,ys=[10,20],sources=['Reconciliado del Caso']*2,cu_tf_t=100),
           dict(num=2,start=dates[0],xs=dates,ys=[30,40],sources=['Reconciliado del Caso']*2,cu_tf_t=300)]
    base=dict(case_end=dates[-1],groups=dict(OXIDOS=items,SULFUROS=[]))
    out,warning=add_group_curves(base,[dict(id='a',name='A',members=['rox-P01','rox-P02'])])
    assert not warning and len(base['groups']['OXIDOS'])==2
    fig=make_figure(out,'OXIDOS',[0,1])
    assert fig.data[-1].name=='Σ A'
    assert list(fig.data[-1].y)==pytest.approx([25,35])


def test_group_report_rl_adds_volumes_instead_of_daily_rates():
    doc=_doc()
    ox=doc['pads']['OXIDOS']['pilas'][0]
    su=doc['pads']['SULFUROS']['pilas'][0]
    ox.update(ini='2026-10-01',tms=100.,rl_curve=[.1,.2,.3])
    su.update(ini='2026-10-01',tms=300.,rl_curve=[.3,.4,.5])
    out=with_group_columns(doc,[dict(id='mix',name='Mix',members=['rox-P01','rsu-P21'])])
    q=out['group_columns']['OXIDOS'][0]
    assert q['rl_accum_curve']==pytest.approx([.25,.6,1.05])


def test_buttons_locations_and_rl_label_have_unique_ids():
    root=dashboard._build_content_layout()
    def nodes(c):
        yield c
        children=getattr(c,'children',[])
        for child in children if isinstance(children,list) else [children]:
            if hasattr(child,'to_plotly_json'):
                yield from nodes(child)
    all_nodes=list(nodes(root))
    ids=[str(n.id) for n in all_nodes if getattr(n,'id',None)]
    assert len(ids)==len(set(ids))
    controls=next(n for n in all_nodes if getattr(n,'className',None)=='controls-card')
    control_ids={getattr(n,'id',None) for n in nodes(controls)}
    assert {'curvas-recon-btn','curvas-grupos-open'}<=control_ids
    assert 'curvas-todas-rec-open' not in control_ids
    assert next(n for n in all_nodes if getattr(n,'id',None)=='curvas-grupos-open').children=='Suma de curvas'
    assert 'Recuperación vs RL' in [getattr(n,'label',None) for n in all_nodes]
