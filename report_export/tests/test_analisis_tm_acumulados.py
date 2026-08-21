from datetime import date
import io

import numpy as np
import pandas as pd
from openpyxl import load_workbook
import pytest

from report_export.report_export import (
    _promedio_ponderado_periodo,
    _semana_mes_lunes_domingo,
    agregar_hoja_generador_reporte,
    export_reporte_turno_estilo_leyes_finos,
    preparar_df_generador_reporte_excel,
    preparar_df_reporte_turno_excel,
)


def test_semana_mes_lunes_domingo_agosto_2026():
    casos = {
        "2026-08-01": 1,
        "2026-08-02": 1,
        "2026-08-03": 2,
        "2026-08-09": 2,
        "2026-08-10": 3,
        "2026-08-16": 3,
        "2026-08-17": 4,
        "2026-08-23": 4,
        "2026-08-24": 5,
        "2026-08-30": 5,
        "2026-08-31": 6,
    }
    assert {
        fecha: _semana_mes_lunes_domingo(fecha) for fecha in casos
    } == casos


def test_preparar_reporte_turno_usa_semana_calendario():
    df = pd.DataFrame({
        "Fecha": pd.to_datetime(["2026-08-02", "2026-08-03", "2026-08-31"]),
        "Turno": ["A", "A", "B"],
    })
    resultado = preparar_df_reporte_turno_excel(df)
    assert resultado["Semana"].tolist() == ["Semana 1", "Semana 2", "Semana 6"]


def test_campana_se_normaliza_y_exporta_como_entero_en_ambos_reportes():
    turno = pd.DataFrame({
        "Fecha": pd.to_datetime(["2026-08-03"]),
        "Turno": ["A"],
        "Campania": [11.0],
        "Modulo": [7.0],
    })
    diario = pd.DataFrame({
        "Fecha": pd.to_datetime(["2026-08-03"]),
        "Campania": [11.0],
        "Modulo": [7.0],
    })

    assert preparar_df_reporte_turno_excel(turno)["Campania"].iloc[0] == 11
    assert preparar_df_generador_reporte_excel(diario)["Campaña"].iloc[0] == 11

    output = io.BytesIO()
    export_reporte_turno_estilo_leyes_finos(
        turno,
        output,
        df_generador=diario,
    )
    workbook = load_workbook(io.BytesIO(output.getvalue()), data_only=True)

    celda_turno = workbook["Reporte por Turno"]["D23"]
    celda_generador = workbook["Generador Reporte"]["D22"]
    assert celda_turno.value == 11
    assert celda_turno.number_format == "#,##0"
    assert celda_generador.value == 11
    assert celda_generador.number_format == "#,##0"


def test_promedio_ponderado_no_es_promedio_simple():
    df = pd.DataFrame({
        "Fecha": pd.to_datetime(["2026-08-03", "2026-08-04"]),
        "TMS": [100, 300],
        "Ley": [0.50, 0.70],
    })
    resultado = _promedio_ponderado_periodo(
        df, date(2026, 8, 4), "Ley", "TMS", solo_semana=True
    )
    assert resultado == 0.65
    assert resultado != 0.60


def test_promedio_ponderado_excluye_nulos_y_peso_cero_pero_incluye_valor_cero():
    df = pd.DataFrame({
        "Fecha": pd.to_datetime(["2026-08-03"] * 5),
        "TMS": [100, np.nan, 0, 100, 300],
        "Ley": [0.0, 0.9, 0.8, np.nan, 0.8],
    })
    resultado = _promedio_ponderado_periodo(
        df, date(2026, 8, 3), "Ley", "TMS", solo_semana=True
    )
    assert resultado == 0.60


def test_resumen_usa_fuente_mensual_separada_y_conserva_tabla_visible():
    resumen = pd.DataFrame({
        "Fecha": pd.to_datetime([
            "2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04"
        ]),
        "Apilado_TMS_Real_Dia": [100, 100, 100, 300],
        "Apilado_TMS_Programa": [100, 100, 100, 300],
        "Apilado_TMS_Plan": [100, 100, 100, 300],
        "CuT_Real_Dia": [0.50, 0.60, 0.50, 0.70],
        "CuT_Programa": [0.40, 0.40, 0.50, 0.70],
        "CuT_Plan": [0.30, 0.30, 0.50, 0.70],
    })
    visible = resumen.loc[resumen["Fecha"].dt.day.ge(3)].copy()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        agregar_hoja_generador_reporte(
            writer,
            df_diario=visible,
            df_diario_resumen=resumen,
        )

    workbook = load_workbook(io.BytesIO(output.getvalue()), data_only=True)
    ws = workbook["Generador Reporte"]
    assert ws["V5"].value == "Semana 2"
    assert ws["AB6"].value == 0.65
    assert ws["AC6"].value == 0.65
    assert ws["AD6"].value == pytest.approx(0.6166666666666667)
    assert ws["AE6"].value == pytest.approx(0.5333333333333333)
    fechas_visibles = [ws["C22"].value, ws["C23"].value]
    assert [fecha.day for fecha in fechas_visibles] == [3, 4]
