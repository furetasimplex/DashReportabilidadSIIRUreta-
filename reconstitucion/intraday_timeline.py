"""Validate observed wet increments and invert their daily cumulative mass."""
import numpy as np
import pandas as pd


def clock_from_intraday(day, profile, intervals):
    """Return a mass-to-clock mapping, or an explicit A/B fallback reason.

    Positive conveyor/shift blocks must cover every 10 s interval and agree
    with their published wet total. Explicit published zeros contribute zero.
    No reference capacity is used. Start/end sides preserve actual pauses.
    """
    required={'fecha_op','turno','tm','start','end','mass_h','quality'}
    if intervals is None or intervals.empty or not required.issubset(intervals):
        return None,'sin_perfil_intraturno'
    if 'tm' not in profile:
        return None,'perfil_sin_identidad_correa'
    date=pd.Timestamp(day).normalize()
    raw=intervals.loc[pd.to_datetime(intervals.fecha_op).dt.normalize().eq(date)]
    blocks=[]
    for row in profile.itertuples():
        expected=float(row.tmh)
        if expected==0:
            continue
        block=raw.loc[raw.turno.eq(row.turno)&raw.tm.eq(row.tm)].copy()
        if block.empty:
            return None,'bloque_intraturno_ausente'
        if block.quality.ne('ok').any() or block.end.duplicated().any():
            return None,'bloque_intraturno_no_valido'
        block['start']=pd.to_datetime(block.start)
        block['end']=pd.to_datetime(block.end)
        if block[['start','end']].isna().any().any():
            return None,'fechas_intraturno_ausentes'
        shift_start=date+pd.Timedelta(hours=8 if row.turno=='A' else 20)
        if (len(block)!=4320 or block.start.min()!=shift_start
                or block.end.max()!=shift_start+pd.Timedelta(hours=12)
                or block.end.sub(block.start).ne(pd.Timedelta(seconds=10)).any()):
            return None,'cobertura_intraturno_incompleta'
        mass=pd.to_numeric(block.mass_h,errors='coerce')
        if (~np.isfinite(mass)).any() or mass.lt(0).any():
            return None,'masa_intraturno_no_valida'
        total=float(mass.sum())
        if not np.isclose(total,expected,rtol=1e-6,atol=.001):
            return None,'total_intraturno_no_cuadra_con_TMH'
        # Only roundoff-sized normalization is permitted after the comparison.
        block['mass_h']=mass*(expected/total)
        blocks.append(block[['start','end','mass_h']])
    if not blocks:
        return None,'sin_incrementos_positivos'
    whole=pd.concat(blocks).groupby(['start','end'],as_index=False).mass_h.sum().sort_values('end')
    positive=whole.loc[whole.mass_h.gt(0)].reset_index(drop=True)
    mass=positive.mass_h.to_numpy(dtype=float)
    ends=np.cumsum(mass)
    before=ends-mass
    total=float(profile.tmh.sum())

    def clock(value,side='end'):
        value=float(np.clip(value,0,total))
        if value<=0:
            return pd.Timestamp(positive.start.iloc[0])
        if value>=total:
            return pd.Timestamp(positive.end.iloc[-1])
        # Floating cumulative sums must not move an exact switch across a pause.
        # Snap only numerical noise (sub-gram at plant-scale totals), preserving
        # right=start after a pause and left=end before it.
        near=int(np.searchsorted(ends,value,side='left'))
        candidates=[i for i in (near-1,near) if 0<=i<len(ends)]
        if candidates:
            edge=min(candidates,key=lambda i:abs(ends[i]-value))
            if abs(ends[edge]-value)<=max(1e-8,abs(total)*1e-12):
                value=float(ends[edge])
        idx=min(int(np.searchsorted(ends,value,side='right' if side=='start' else 'left')),len(mass)-1)
        fraction=float(np.clip((value-before[idx])/mass[idx],0,1))
        start=pd.Timestamp(positive.start.iloc[idx])
        return start+(pd.Timestamp(positive.end.iloc[idx])-start)*fraction

    return clock,'totalizadores_10s_validados_con_TMH_turno'
