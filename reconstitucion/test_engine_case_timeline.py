"""Offline Case wrapper regression: identity, balances and timeline contract."""
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    from . import db_source, engine, modelo_flujos, wet_profile
    from .test_module_timeline_intraturno import make_inputs, make_intraday
except ImportError:
    from reconstitucion import db_source, engine, modelo_flujos, wet_profile  # noqa: E402
    from .test_module_timeline_intraturno import make_inputs, make_intraday


def test_single_pad_case_uses_intraday_and_preserves_case_run_and_TMS(legacy_timeline):
    day, ap, _, profile = make_inputs(two_modules=False)
    profile["humedad"] = 0.
    profile["fuente"] = "TEST"
    ap = ap.assign(vol_acum_final=ap.vol_diario, vol_total_est=ap.vol_diario)
    hours = pd.DataFrame({"fecha": [day], "H_op": [10.]})
    targets = {2: dict(flujo="F19", masa_medida=100., masa_reconciliada=100.,
                       fino_cu_medido=.5, fino_cu_reconciliado=.5)}
    case = dict(id=10013, run_id=10145, fecha_inicio=day, fecha_fin=day,
                modelo_codigo="hidrometalurgia_125_v2", modelo_version="v2",
                total_flujos=125)
    with patch.object(modelo_flujos, "load_targets", return_value=targets), \
         patch.object(modelo_flujos, "load_profile", return_value=profile), \
         patch.object(modelo_flujos, "load_hours", return_value=hours), \
         patch.object(db_source, "load_apilado", return_value=ap), \
         patch.object(wet_profile, "load_intraday_profile",
                      return_value=make_intraday(day, profile)):
        result = engine.analyze_db(fecha_min=day, fecha_max=day, caso=case,
                                   caso_id=case["id"], use_intraday=True)

    assert result["fuente_modelo"]["id"] == 10013
    assert result["fuente_modelo"]["run_id"] == 10145
    assert abs(result["module_timeline"].iloc[0].end -
               (day + pd.Timedelta(days=1, hours=8))) <= pd.Timedelta(microseconds=1)
    assert result["module_timeline"].iloc[0].mass_h == pytest.approx(100.)
    assert result["module_timeline"].iloc[0].mass_dry == pytest.approx(100.)
    assert result["module_timeline"].iloc[0].resolucion == \
        "totalizadores_10s_validados_con_TMH_turno"
    assert result["shift_table"].masa_total.sum() == pytest.approx(100.)
    assert result["cuadratura_pad"].masa_pendiente.abs().max() < 1e-8
    assert not {"tasa", "proy_modo", "avance_ok"}.intersection(result)
    assert result["itinerario"].equals(result["module_timeline"])
    grouped = engine.analyze_group(result, 2, 12)
    assert grouped["fuente_modelo"]["run_id"] == 10145
    assert grouped["module_timeline"].equals(result["module_timeline"])
