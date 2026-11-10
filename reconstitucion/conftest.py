import pytest


@pytest.fixture
def legacy_timeline(monkeypatch):
    """Sustituye la recalibracion SQL por el timeline intradia legado.

    Las pruebas de perfil 10 s / fallback A-B no aportan historia de campana;
    el metodo secuencial se prueba en test_recalibracion_*.
    """
    from reconstitucion.module_timeline import build_module_timeline

    def legacy(res, caso, targets, **_):
        res['module_timeline'] = res['itinerario'] = res['nuevo_itinerario'] = build_module_timeline(
            res['apilado'], res['shift_table'], res['perfil_turnos'], intraday=res.pop('_intraday_profile'))
        return res
    monkeypatch.setattr('reconstitucion.recalibracion_runtime.load_runtime_recalibration', legacy)
