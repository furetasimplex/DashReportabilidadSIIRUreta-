import sys
from pathlib import Path
import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    from . import modelo_flujos as mf
    from .module_timeline import build_module_timeline
except ImportError:
    from reconstitucion import modelo_flujos as mf
    from reconstitucion.module_timeline import build_module_timeline


def test_daily_TMH_cut_uses_one_cumulative_across_both_shifts():
    day = pd.Timestamp('2026-10-06')
    ap = pd.DataFrame([
        dict(fecha=day, pad_id=2, campana=12, modulo=5, avance=.9,
             vol_diario=40., estado='ACTIVO'),
        dict(fecha=day, pad_id=2, campana=12, modulo=6, avance=.1,
             vol_diario=60., estado='ACTIVO'),
    ])
    st = pd.DataFrame([
        dict(fecha=day, pad_id=2, campana=12, modulo=5, masa_turno1=12., masa_turno2=8.),
        dict(fecha=day, pad_id=2, campana=12, modulo=6, masa_turno1=30., masa_turno2=15.),
    ])
    profile = pd.DataFrame([
        dict(fecha=day, turno='A', tm='TM1', tmh=40.),
        dict(fecha=day, turno='A', tm='TM2', tmh=40.),
        dict(fecha=day, turno='B', tm='TM1', tmh=10.),
        dict(fecha=day, turno='B', tm='TM2', tmh=10.),
    ])
    out = build_module_timeline(ap, st, profile).set_index('modulo')
    assert out.loc[5, 'end'] == day + pd.Timedelta(hours=14)
    assert out.loc[6, 'start'] == out.loc[5, 'end']
    assert out.mass_h.sum() == pytest.approx(100.)
    assert out.mass_dry.to_dict() == pytest.approx({5: 20., 6: 45.})


def test_intraday_clock_preserves_pause_at_module_boundary():
    try:
        from .test_module_timeline_intraturno import make_inputs, make_intraday
    except ImportError:
        from .test_module_timeline_intraturno import make_inputs, make_intraday
    day, ap, st, profile = make_inputs()
    raw = make_intraday(day, profile)
    # Move the threshold to 40 t: first 1,280 ten-second buckets carry 40 t,
    # then the entire conveyor pauses for 100 buckets before restarting.
    a_mask = raw.turno.eq('A')
    for tm in ('TM1', 'TM2'):
        mask = a_mask & raw.tm.eq(tm)
        idx = raw.index[mask]
        raw.loc[idx[:1280], 'mass_h'] = 1. / 64
        raw.loc[idx[1280:1380], 'mass_h'] = 0.
        raw.loc[idx[1380:], 'mass_h'] = 20. / (4320 - 1380)
    out = build_module_timeline(ap, st, profile, intraday=raw).set_index('modulo')
    assert abs(out.loc[5, 'end'] - (day + pd.Timedelta(hours=11, minutes=33, seconds=20))) <= pd.Timedelta(microseconds=1)
    assert abs(out.loc[6, 'start'] - (day + pd.Timedelta(hours=11, minutes=50))) <= pd.Timedelta(microseconds=1)
    assert out.loc[6, 'start'] > out.loc[5, 'end']


def profile():
    dates=pd.date_range('2026-10-20',periods=2)
    rows=[dict(fecha=d,turno=t,tm=tm,tmh=25.,humedad=0.,fuente='TEST')
          for d in dates for t in ['A','B'] for tm in ['TM1','TM2']]
    return dates,pd.DataFrame(rows)


TARGET={2:dict(masa_reconciliada=100.,fino_cu_reconciliado=1.,flujo='F19')}


@pytest.mark.parametrize('missing_humidity',[False,True])
def test_mass_without_global_volume_is_not_reassigned(missing_humidity):
    dates,p=profile()
    if missing_humidity:
        p.loc[p.fecha.eq(dates[1]),'humedad']=float('nan')
    ap=pd.DataFrame([dict(fecha=dates[0],pad_id=2,vol_diario=1.)])
    with pytest.raises(mf.FlowCaseError,match='no se redistribuye'):
        mf.distribute_profile(p,ap,TARGET,dict(id=1,run_id=1))


def test_confirmed_zero_profile_and_other_pad_activity_do_not_fail():
    dates,p=profile()
    p.loc[p.fecha.eq(dates[1]),'tmh']=0.
    ap=pd.DataFrame([dict(fecha=dates[0],pad_id=2,vol_diario=1.),
                     dict(fecha=dates[1],pad_id=1,vol_diario=1.)])
    allocated,_,_=mf.distribute_profile(p,ap,TARGET,dict(id=1,run_id=1))
    assert allocated.TMS.sum()==pytest.approx(100.)
