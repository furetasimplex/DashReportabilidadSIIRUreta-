from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from report_export import report_export as repo


class _Conexion:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _Motor:
    def connect(self):
        return _Conexion()


def test_fetch_factor_es_solo_lectura_semiabierta_y_normaliza_fechas():
    resultado_sql = pd.DataFrame({
        "Fecha": ["2026-08-02 12:30", "2026-08-01 08:00"],
        "Factor_Aplicacion_Reportes": [1.0, 0.95],
        "Fecha_Calculo": ["2026-08-02 13:00", "2026-08-01 09:00"],
    })
    captura = {}

    def _read_sql(sql, conn, params):
        captura["sql"] = str(sql)
        captura["params"] = params
        return resultado_sql.copy()

    with (
        patch.object(repo, "_get_engine", return_value=_Motor()),
        patch.object(repo.pd, "read_sql", side_effect=_read_sql),
    ):
        df = repo.fetch_factor_ajuste_camiones_report(
            date(2026, 8, 1), date(2026, 8, 2),
        )

    sql = captura["sql"]
    assert "v_ajuste_camiones_emision_test" in sql
    assert "Fecha >= :fecha_inicio" in sql
    assert "Fecha < DATEADD(DAY, 1, :fecha_fin)" in sql
    assert "EXEC" not in sql.upper()
    assert captura["params"] == {
        "fecha_inicio": date(2026, 8, 1),
        "fecha_fin": date(2026, 8, 2),
    }
    assert df["Fecha"].tolist() == [
        pd.Timestamp("2026-08-01"), pd.Timestamp("2026-08-02"),
    ]
    assert pd.api.types.is_datetime64_any_dtype(df["Fecha_Calculo"])


def test_fetch_factor_rechaza_fechas_duplicadas():
    duplicados = pd.DataFrame({
        "Fecha": [pd.Timestamp("2026-08-01"), pd.Timestamp("2026-08-01 12:00")],
        "Fecha_Calculo": [None, None],
    })
    with (
        patch.object(repo, "_get_engine", return_value=_Motor()),
        patch.object(repo.pd, "read_sql", return_value=duplicados),
        pytest.raises(ValueError, match="duplicadas"),
    ):
        repo.fetch_factor_ajuste_camiones_report(
            date(2026, 8, 1), date(2026, 8, 1),
        )
