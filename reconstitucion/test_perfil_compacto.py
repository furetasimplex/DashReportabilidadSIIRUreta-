import pandas as pd
from .wet_profile import _profile_from_ticks

def test_ticks_preservan_ceros_diagnosticos_y_limites_operacionales():
    start=pd.Timestamp('2026-10-06 08:00:00')
    raw=pd.DataFrame([dict(fecha=start+pd.Timedelta(seconds=t),tot_008=value,tot_108=value)
        for t,value in [(0,100.),(10,110.),(20,110.),(40,120.),(50,90.),
                        (60,300000.),(70,None),(80,300010.),(90,300020.),
                        (43200,300021.),(86400,300022.)]])
    frame=_profile_from_ticks(raw,'2026-10-06','2026-10-06')
    def at(seconds):return frame[frame.end.eq(start+pd.Timedelta(seconds=seconds))]
    assert len(frame)==20
    assert at(20).quality.eq('ok').all() and at(20).mass_h.eq(0).all()
    assert at(40).quality.eq('gap').all() and at(40).mass_h.isna().all()
    assert at(50).quality.eq('reset').all()
    assert at(60).quality.eq('large_jump').all()
    assert at(70).quality.eq('null').all() and at(80).quality.eq('null').all()
    assert at(43200).turno.eq('A').all()
    assert at(86400).turno.eq('B').all()
    assert frame.fecha_op.eq(pd.Timestamp('2026-10-06')).all()

def test_duplicados_conservados_y_rechazados_en_vez_de_promediados():
    start=pd.Timestamp('2026-10-06 08:00:00')
    raw=pd.DataFrame([dict(fecha=start+pd.Timedelta(seconds=t),tot_008=v,tot_108=v)
        for t,v in [(0,100.),(10,110.),(10,115.),(20,120.)]])
    frame=_profile_from_ticks(raw,'2026-10-06','2026-10-06')
    assert len(frame)==6
    assert frame.quality.eq('duplicate').all()
    assert frame.duplicate_flag.all() and frame.mass_h.isna().all()
