from types import SimpleNamespace
from collections import OrderedDict
import pandas as pd
import plotly.graph_objects as go
import pytest

from curvas_recon import pad_dashboard as dashboard
from curvas_recon import group_solution_charts as charts


def fixture_data():
    days=pd.date_range('2025-12-31','2026-01-02')
    rows=[]
    for day in days[1:]:
        for num,qr,qp,cr,cp,fr,fp,rc,pc in [
                (10,10,8,1,3,12,9,2,4),(11,30,12,3,5,18,11,6,8)]:
            rows.append(dict(label='SULFUROS',parcela=f'P{num}',date=day,
                q_riego_medido=qr,q_pls_medido=qp,cu_riego_medido=cr,cu_pls_medido=cp,
                q_riego_final=fr,q_pls_final=fp,cu_riego_recon=rc,cu_pls_recon=pc))
    raw={'res':{'daily':rows,'piles':[dict(label='SULFUROS',parcela='P10'),dict(label='SULFUROS',parcela='P11')]}}
    calls=[]
    def material(*args):
        calls.append(args)
        return {'riego':pd.DataFrame({'P10':[5]*3,'P11':[15]*3},index=days),
                'cu_riego':pd.Series(2.0,index=days),
                'drena_cu':pd.DataFrame({'P10':[3]*3,'P11':[7]*3},index=days)}
    a=SimpleNamespace(_get_group_raw=lambda *_:raw,_store_window=lambda *_:(days[1],days[2],2),
        WIP_META={},_PAD_TO_LABEL={'rsu':'SULFUROS'},
        _rl_tms_by_pile=lambda *_:{('SULFUROS',n):{'f0':days[0]} for n in (10,11)},
        _load_material_window=material,FDRENA_MAX=0.95,_stacked_figure=dashboard._stacked_figure,
        _add_week_zoom_box=dashboard._add_week_zoom_box,empty_figure=dashboard.empty_figure,
        visible_xaxis_range=dashboard.visible_xaxis_range,CHART_SURFACE='#FFFFFF',CHART_INK_PRIMARY='#111827')
    return a,calls,{'id':'f','name':'F actual','members':['rsu-P10','rsu-P11']},{'raw_token':'group-test','caso_run_id':1}


def test_group_panels_sum_q_and_weight_cu_on_the_same_case_run():
    charts._CACHE.clear()
    a,calls,group,data=fixture_data()
    flows,cu=charts.build_group_solution_charts(a,group,data,10013)
    assert len(calls)==1  # one shared material window, not per-member queries
    assert len(flows.data)==len(cu.data)==4
    flow_map={t.name:t for t in flows.data};cu_map={t.name:t for t in cu.data}
    assert list(flow_map['Caudal riego (medido)'].y)==[20,40,40]
    assert list(flow_map['Caudal PLS (medido)'].y)==[19,20,20]
    assert list(flow_map['Caudal riego (reconciliado)'].y)==[30,30]
    assert list(flow_map['Caudal PLS (reconciliado)'].y)==[20,20]
    assert list(cu_map['Cu riego (medido)'].y)==pytest.approx([2,2.5,2.5])
    assert list(cu_map['Cu PLS (medido)'].y)==pytest.approx([6,4.2,4.2])
    assert list(cu_map['Cu riego (reconciliado)'].y)==pytest.approx([4.4,4.4])
    assert list(cu_map['Cu PLS (reconciliado)'].y)==pytest.approx([6.2,6.2])
    for fig in (flows,cu):
        assert len(fig.layout.shapes)==2
        assert all(s.opacity==0.08 for s in fig.layout.shapes)
        assert all(pd.Timestamp(s.x0)==pd.Timestamp('2026-01-01') and pd.Timestamp(s.x1)==pd.Timestamp('2026-01-03') for s in fig.layout.shapes)
    charts.build_group_solution_charts(a,group,data,10013)
    assert len(calls)==1


def test_group_selection_routes_panels_without_needing_an_individual_pile(monkeypatch):
    a,_,group,data=fixture_data()
    monkeypatch.setattr(dashboard,'_store_matches_case',lambda *_:True)
    monkeypatch.setattr(dashboard,'ensure_full_data',lambda:None)
    expected=(go.Figure(),go.Figure())
    monkeypatch.setattr(charts,'build_group_solution_charts',lambda *_:expected)
    result=dashboard.render_recon_pila_charts(data,None,10013,'f',[group])
    assert result[0] is dashboard.dash.no_update
    assert result[1:] == expected
