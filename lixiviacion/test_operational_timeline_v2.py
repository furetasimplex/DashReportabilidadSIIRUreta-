import copy
from datetime import date
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from . import callbacks,phase_db,map_panel
from .phase_model import PHASES,CONDITIONS
from .test_diagnostic_operational import v2row

def control():
    return [dict(v2row('HUMECTACION'),fecha=date(2025,12,15),condicion_dia='RIEGO_ACTIVO'),
            dict(v2row(),fecha=date(2025,12,16))]

def test_control_transition_has_two_map_colors_and_separate_condition():
    rows=control();before=copy.deepcopy(rows)
    fig=callbacks.operational_timeline(rows,dict(desde='2025-12-15',hasta='2025-12-16'))
    assert [t.name for t in fig.data]==['Humectación','Riego continuo']
    assert len({t.marker.color for t in fig.data})==2
    assert 'Estado operacional:' not in fig.data[0].hovertemplate and 'Condición diaria:' in fig.data[0].hovertemplate
    for trace,row in zip(fig.data,rows):
        assert trace.name==map_panel.state(dict(row,model_v2=True))[0]
        assert trace.customdata[0][2]==CONDITIONS[row['condicion_dia']]
    assert rows==before and all(t.x==(86400000,) for t in fig.data)

def test_does_not_color_by_legacy_or_repeat_final_date():
    rows=control()
    for row in rows:row.update(estado_operacional='RIEGO',fase_visual_legacy='CICLO_HIDRAULICO')
    fig=callbacks.operational_timeline(rows,dict(desde='2025-12-15',hasta='2025-12-16'))
    assert [t.name for t in fig.data]==['Humectación','Riego continuo']
    assert fig.data[0].base==('2025-12-15',) and fig.data[1].base==('2025-12-16',)

def test_every_structural_phase_remains_distinct():
    rows=[dict(v2row(k),fecha=date(2026,1,i+1)) for i,k in enumerate(k for k in PHASES if k!='SIN_COBERTURA')]
    fig=callbacks.operational_timeline(rows,dict(desde='2026-01-01',hasta='2026-01-31'))
    assert len(fig.data)==len(rows) and {t.name for t in fig.data}=={PHASES[r['fase_final']][0] for r in rows}

def reader(monkeypatch,rows):
    calls=[]
    class Conn:
        def execute(self,sql,params):calls.append((str(sql),params));return SimpleNamespace(mappings=lambda:rows)
    @contextmanager
    def connection():yield Conn()
    monkeypatch.setattr(phase_db,'_connection',connection)
    monkeypatch.setattr(phase_db.phase_flags,'guard_connection',lambda c:None)
    monkeypatch.setattr(phase_db.phase_flags,'enabled',lambda n:True)
    return calls

def test_reader_uses_daily_tvf_and_existing_cleaner_without_reclassifying(monkeypatch):
    rows=control();calls=reader(monkeypatch,rows)
    f=dict(desde='2025-12-15',hasta='2025-12-16',pad=1,parcela=17,campana=999,estado='FUERA_VENTANA_RIEGO')
    with patch('lixiviacion.phase_model.calculate',side_effect=AssertionError('No recalcular')):
        header,timeline=phase_db.operational(f)
    assert header['fecha']==date(2025,12,16) and len(timeline)==2
    assert len(calls)==2 and 'CROSS APPLY inventar_SpcHidr.fn_estado_operacional_parcela_v2(d.fecha)' in calls[0][0]
    assert 'vw_tablero_lixiviacion_final_v2' in calls[1][0]
    assert 'estado_operacional_parcela_diario' not in calls[0][0]
    assert calls[0][1]['desde']==date(2025,12,15) and calls[0][1]['hasta']==date(2025,12,16)
    assert timeline[0]['riego_activo']==timeline[0]['riego_activo_v2']

@pytest.mark.parametrize('bad',['duplicate','outside','wrong_parcel','hydraulic_as_phase'])
def test_reader_rejects_invalid_grain_or_phase_without_fallback(monkeypatch,bad):
    rows=control()
    if bad=='duplicate':rows.append(rows[0])
    elif bad=='outside':rows[0]['fecha']=date(2025,12,1)
    elif bad=='wrong_parcel':rows[0]['parcela_id']=999
    else:rows[0]['fase_final']='CICLO_HIDRAULICO'
    reader(monkeypatch,rows)
    with pytest.raises(ValueError):phase_db.operational(dict(desde='2025-12-15',hasta='2025-12-16',pad=1,parcela=17))

def test_v2_disabled_does_not_fall_back_or_open_connection(monkeypatch):
    monkeypatch.setattr(phase_db.phase_flags,'enabled',lambda n:False)
    with patch.object(phase_db,'_connection') as connect:
        with pytest.raises(PermissionError):phase_db.operational({'parcela':17})
        connect.assert_not_called()
