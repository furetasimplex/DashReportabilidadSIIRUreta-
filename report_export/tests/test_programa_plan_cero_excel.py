"""Semántica visual de masa explícita cero y datos requeridos NULL."""
from decimal import Decimal

import pandas as pd
import pytest

from report_export.report_export import (
    preparar_df_generador_reporte_excel, preparar_df_reporte_turno_excel,
)


@pytest.mark.parametrize("diario", [False, True])
@pytest.mark.parametrize("masa", [0, Decimal("0"), "0", None, 35920])
def test_masa_y_null(diario, masa):
    programa, plan = ("Programa", "Plan") if diario else ("Plan_Semanal", "Plan_Mensual")
    datos = {"Fecha": ["2026-09-01"], f"Apilado_TMS_{programa}": [masa],
             f"Apilado_TMS_{plan}": [masa], f"CuT_{programa}": [None],
             f"CuS_{programa}": [0], f"CO3_{programa}": [0],
             f"Solubilidad_{programa}": [None], f"Solubilidad_{plan}": [None],
             "Dosis_Acido_Programa_Semanal": [None if diario else 14]}
    df = pd.DataFrame(datos)
    original = df.copy(deep=True)
    preparar = preparar_df_generador_reporte_excel if diario else preparar_df_reporte_turno_excel
    result = preparar(df)
    for col in [f"Solubilidad_{programa}", f"Solubilidad_{plan}", "Dosis_Acido_Programa_Semanal"]:
        if masa is not None and float(masa) == 0:
            assert result.at[0, col] == 0
        elif col == "Dosis_Acido_Programa_Semanal" and masa is None and not diario:
            assert result.at[0, col] == 14  # no inferir masa ausente
        else:
            assert pd.isna(result.at[0, col])
    pd.testing.assert_frame_equal(df, original)


@pytest.mark.parametrize("diario", [False, True])
@pytest.mark.parametrize("faltante", [None, "CuT", "CuS", "CO3"])
def test_calculo_evaluable_y_datos_faltantes(diario, faltante):
    sufijo = "Programa" if diario else "Plan_Semanal"
    df = pd.DataFrame({"Fecha": ["2026-09-03"], f"Apilado_TMS_{sufijo}": [35920],
                       f"CuT_{sufijo}": [.477215], f"CuS_{sufijo}": [.074936],
                       f"CO3_{sufijo}": [.107449],
                       f"Solubilidad_{sufijo}": [.074936 / .477215],
                       "Dosis_Acido_Programa_Semanal": [14.]})
    if faltante:
        df[f"{faltante}_{sufijo}"] = None
    preparar = preparar_df_generador_reporte_excel if diario else preparar_df_reporte_turno_excel
    result = preparar(df)
    if faltante:
        assert pd.isna(result.at[0, "Dosis_Acido_Programa_Semanal"])
    else:
        assert result.at[0, "Dosis_Acido_Programa_Semanal"] == 14
    if faltante in ("CuT", "CuS"):
        assert pd.isna(result.at[0, f"Solubilidad_{sufijo}"])
    else:
        assert result.at[0, f"Solubilidad_{sufijo}"] == .074936 / .477215


def test_masa_diaria_por_fecha_sin_poblar_tb_ni_mutar_fuente():
    df = pd.DataFrame({"Fecha": ["2026-09-02", "2026-09-02", "2026-09-01"],
                       "Turno": ["A", "B", "A"], "CuT_Plan_Semanal": [0, None, 0],
                       "Solubilidad_Plan_Semanal": [None, None, None],
                       "Dosis_Acido_Programa_Semanal": [14, None, 14]}, index=[7, 4, 2])
    diario = pd.DataFrame({"Fecha": ["2026-09-01", "2026-09-02"],
                           "Apilado_TMS_Programa": [0, 0]})
    original = diario.copy(deep=True)
    result = preparar_df_reporte_turno_excel(df, diario)
    for col in ["Solubilidad_Plan_Semanal", "Dosis_Acido_Programa_Semanal"]:
        assert result.loc[[7, 2], col].eq(0).all()
        assert pd.isna(result.loc[4, col])
    pd.testing.assert_frame_equal(diario, original)
