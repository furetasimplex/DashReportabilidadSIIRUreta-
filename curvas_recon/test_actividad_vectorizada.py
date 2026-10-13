"""Regresión del inicio real de campañas: independiente de SQL."""
import numpy as np
import pandas as pd
import pytest
from curvas_recon import recon_engine as motor

def legacy(riego,drena,asof,gap):
    out={}
    for pila,fechas in riego.items():
        fr=fechas[fechas<=asof]
        if not len(fr): continue
        fd=drena.get(pila,pd.DatetimeIndex([]))
        act=fr.union(fd[fd<=asof]) if len(fd) else fr
        ini=act[0]
        for i in range(len(act)-1,0,-1):
            if (act[i]-act[i-1]).days>gap:
                ini=act[i]
                break
        bloque=fr[fr>=ini]
        out[pila]=bloque[0] if len(bloque) else ini
    return out

@pytest.mark.parametrize('gap',[0,1,30,45])
def test_inicio_coincide_con_recorrido_original(monkeypatch,gap):
    rng=np.random.default_rng(714)
    base=pd.Timestamp('2025-01-01')
    riego={f'P{i}':pd.DatetimeIndex(base+pd.to_timedelta(np.unique(rng.integers(0,700,150)),unit='D')) for i in range(5)}
    drena={f'P{i}':pd.DatetimeIndex(base+pd.to_timedelta(np.unique(rng.integers(0,700,80)),unit='D')) for i in range(3)}
    monkeypatch.setattr(motor,'_CAMPANA_CACHE',{})
    monkeypatch.setattr(motor,'_fechas_actividad',lambda label:(riego,drena))
    for day in [-1,0,30,250,500,700]:
        asof=base+pd.Timedelta(days=day)
        assert motor.inicio_campana('SULFUROS',asof,gap)==legacy(riego,drena,asof,gap)

def test_hueco_de_30_dias_no_reinicia_y_drenaje_conecta_bloque(monkeypatch):
    riego={'P1':pd.to_datetime(['2026-07-01','2026-07-31','2026-08-31']),
           'P2':pd.to_datetime(['2026-07-01','2026-08-31'])}
    drena={'P2':pd.to_datetime(['2026-07-31','2026-08-15'])}
    monkeypatch.setattr(motor,'_CAMPANA_CACHE',{})
    monkeypatch.setattr(motor,'_fechas_actividad',lambda label:(riego,drena))
    july=motor.inicio_campana('OXIDOS','2026-07-31')
    august=motor.inicio_campana('OXIDOS','2026-08-31')
    assert july['P1']==pd.Timestamp('2026-07-01')
    assert august['P1']==pd.Timestamp('2026-08-31')
    assert august['P2']==pd.Timestamp('2026-07-01')

def test_actividad_normaliza_ordena_y_elimina_duplicados(monkeypatch):
    frame=pd.DataFrame({'pila':['P1','P1','P1','P2'],
                        'fecha':pd.to_datetime(['2026-08-03 12:00','2026-08-01 00:00','2026-08-03 08:00','2026-08-02 00:00'])})
    monkeypatch.setattr(motor,'_ACTIVIDAD_CACHE',{})
    monkeypatch.setattr(motor,'get_engine',lambda:object())
    calls=[]
    def read(*args,**kwargs):
        calls.append(1)
        return frame.copy()
    monkeypatch.setattr(motor,'_sql_df',read)
    riego,drena=motor._fechas_actividad('OXIDOS')
    expected=pd.to_datetime(['2026-08-01','2026-08-03'])
    assert riego['P1'].equals(expected)
    assert drena['P1'].equals(expected)
    motor._fechas_actividad('OXIDOS')
    assert len(calls)==2
