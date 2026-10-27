from contextlib import contextmanager
from unittest.mock import patch
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    from . import modelo_flujos as mf, engine as e, panel, db_source
    from .test_metodologia import apilado
    from .test_casos import find, result
except ImportError:
    from reconstitucion import modelo_flujos as mf, engine as e, panel, db_source
    from reconstitucion.test_metodologia import apilado
    from reconstitucion.test_casos import find, result


def case(i=10013, old=False):
    return dict(id=i, run_id=i+100, nombre='fixture', fecha_inicio='2026-08-03',
                fecha_fin='2026-08-04', modelo_codigo=('hidrometalurgia_120_completo' if old else 'hidrometalurgia_125_v2'),
                modelo_version='v1' if old else 'v2', total_flujos=120 if old else 125)


def inputs():
    a = apilado(2).assign(pad_id=1, vol_diario=200.0)
    b = a.assign(pad_id=2, vol_diario=100.0)
    ap = pd.concat([a,b], ignore_index=True)
    p = pd.DataFrame([dict(fecha=d, turno=s, tm=tm, tmh=100., humedad=10., fuente='PI')
                      for d in a.fecha for s in ['A','B'] for tm in ['TM1','TM2']])
    targets = {pad: dict(flujo=f'F{17+pad}', masa_medida=720., masa_reconciliada=target,
                        fino_cu_medido=3.6, fino_cu_reconciliado=target*.005)
               for pad,target in [(1,600.),(2,400.)]}
    return ap,p,targets


@pytest.mark.parametrize('old', [False, True])
def test_catalogue_mapping_and_units(old):
    c=case(old=old)
    codes=mf.MODELS[c['modelo_codigo']][2]
    class Rows:
        def __init__(self, rows): self.rows=rows
        def first(self): return self.rows[0]
        def fetchall(self): return self.rows
    class Connection:
        def execute(self, sql, params):
            assert str(sql).lstrip().startswith('SELECT')
            if 'recon_caso c' in str(sql):
                return Rows([(c['fecha_inicio'],c['fecha_fin'],c['modelo_codigo'],c['modelo_version'],c['total_flujos'])])
            return Rows([(codes[1], 100., 110., .5, .55), (codes[2], 200., 220., 1., 1.1)])
    class Engine:
        @contextmanager
        def connect(self): yield Connection()
    loaded=mf.load_targets(c, engine=Engine(), hidro_schema='test.hidro')
    assert loaded[1]['flujo']==('F15' if old else 'F18')
    assert loaded[2]['flujo']==('F14' if old else 'F19')
    assert loaded[1]['fino_cu_reconciliado']==.55  # tonnes already, no 0.024 multiplier


def test_invalid_catalogue_fails_before_sql():
    with pytest.raises(mf.FlowCaseError, match='Versi'):
        mf.load_targets(dict(case(),total_flujos=120), engine=object())


def test_distribution_conserves_both_pads_and_preserves_stopped_shift():
    ap,p,targets=inputs()
    p.loc[p.turno.eq('B'),'tmh']=0.
    frames,base,balance=mf.distribute_profile(p,ap,targets,case())
    assert frames.groupby('pad_id').TMS.sum().to_dict()==pytest.approx({1:600.,2:400.})
    assert frames.TMS_T2.eq(0).all()
    assert frames.boundary.eq(1).all()
    assert balance.asignada_t.tolist()==pytest.approx([600.,400.])


@pytest.mark.parametrize('kind',['missing','humidity','duplicate','no_pad_profile'])
def test_bad_profile_is_rejected_without_fallback(kind):
    ap,p,targets=inputs()
    if kind=='missing': p=p.iloc[1:]
    if kind=='humidity': p.loc[0,'humedad']=np.nan
    if kind=='duplicate': p=pd.concat([p,p.iloc[:1]],ignore_index=True)
    if kind=='no_pad_profile': ap=ap[ap.pad_id.eq(1)]
    with pytest.raises(mf.FlowCaseError): mf.distribute_profile(p,ap,targets,case())


def test_full_engine_rejects_unidentified_simultaneous_pad_routes():
    ap,p,targets=inputs()
    hours=pd.DataFrame({'fecha':sorted(ap.fecha.unique()),'H_op':[10.,10.]})
    with patch.object(mf,'load_targets',return_value=targets), \
         patch.object(mf,'load_profile',return_value=p), \
         patch.object(mf,'load_hours',return_value=hours), \
         patch.object(db_source,'load_apilado',return_value=ap), \
         patch.object(db_source,'load_masa',side_effect=AssertionError('Caso no usa masa legacy')):
        with pytest.raises(ValueError, match='más de un PAD activo'):
            e.analyze_db(caso=case(),caso_id=10013,fecha_min=case()['fecha_inicio'],
                         fecha_max=case()['fecha_fin'])


def test_panel_passes_official_run_metadata_to_loader():
    c=case()
    calls=[]
    def loader(**kwargs): calls.append(kwargs); return result(c['id'])
    from dash import Dash
    app=Dash(__name__,suppress_callback_exceptions=True)
    panel.register_callbacks(app,loader=loader,case_loader=lambda:[c])
    fns={k:v['callback'].__wrapped__ for k,v in app.callback_map.items()}
    out=find(fns,'reconstitucion-token.data')(1,c['id'],[c])
    assert out[0]
    assert calls[0]['caso']==c


def test_stale_official_run_fails_before_reading_flows():
    class Result:
        def first(self): return None
    class Connection:
        def execute(self,*args): return Result()
    class Engine:
        @contextmanager
        def connect(self): yield Connection()
    with pytest.raises(mf.FlowCaseError,match='run oficial'):
        mf.load_targets(case(),engine=Engine(),hidro_schema='test.hidro')
