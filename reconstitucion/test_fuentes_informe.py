import pandas as pd
import pytest
from unittest.mock import patch

from . import fuentes_informe as f


def test_lecturas_acotadas_solo_select_con_fallo_de_fuente_visible():
    calls = []

    def read(sql, engine, params):
        query = str(sql)
        calls.append((query, params))
        assert query.lstrip().startswith('SELECT')
        assert params == {'desde': pd.Timestamp('2026-10-01').date(),
                          'hasta': pd.Timestamp('2026-10-13').date()}
        if '.mov_cam' in query:
            assert "Destino = 'CH01'" in query
            return pd.DataFrame({'mov_id': [1]})
        if '.fn_reconstitucion' in query:
            raise RuntimeError('private_connection_data')
        return pd.DataFrame({'Fecha': [pd.Timestamp('2026-10-01')]})

    with patch.object(f.pd, 'read_sql', side_effect=read):
        result = f.cargar_fuentes(object(), '2026-10-01', '2026-10-12')
    assert len(calls) == 3
    assert result['movcam'].mov_id.tolist() == [1]
    assert result['srr'].empty
    assert len(result['warnings']) == 1
    assert 'srr' in result['warnings'][0]
    assert 'private_connection_data' not in str(result)


def test_rango_invertido_no_consulta():
    with patch.object(f.pd, 'read_sql', side_effect=AssertionError('SQL prohibido')):
        with pytest.raises(ValueError):
            f.cargar_fuentes(object(), '2026-10-13', '2026-10-01')


def test_reposo_filtra_pad_y_claves_sin_inferir_fecha():
    frame = pd.DataFrame({'numero_campana': ['11'], 'nombre_modulo': ['134'],
                          'fecha_ini_reposo': [pd.Timestamp('2026-09-06')]})
    def read(sql, engine, params):
        assert 'campana_parcela_control' in str(sql)
        assert 'pad_id=:pad' in str(sql)
        assert params == {'pad': 2, 'c0': 11, 'm0': 134}
        return frame
    with patch.object(f.pd, 'read_sql', side_effect=read):
        actual, warnings = f.cargar_reposo(object(), 2, [(11, 134)])
    pd.testing.assert_frame_equal(actual, frame)
    assert warnings == []


def test_reposo_no_mezcla_campanas_ni_rellena_ausencia():
    from .informe_modulos import incorporar_reposo
    extras = pd.DataFrame({'campana': [11, 12], 'modulo': [134, 134]})
    cycles = pd.DataFrame({'numero_campana': ['11'], 'nombre_modulo': ['134'],
                           'fecha_ini_reposo': ['2026-09-06']})
    actual = incorporar_reposo(extras, cycles)
    assert actual.loc[0, 'fecha_ini_reposo'] == pd.Timestamp('2026-09-06')
    assert pd.isna(actual.loc[1, 'fecha_ini_reposo'])
    assert actual.cobertura_fecha_ini_reposo.tolist() == [1, 0]
