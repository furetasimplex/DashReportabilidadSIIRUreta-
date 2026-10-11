import io

import pandas as pd
import pytest
from openpyxl import load_workbook
from pandas.testing import assert_frame_equal

from report_export.report_export import (
    agregar_hoja_trazabilidad_analitos,
    export_reporte_turno_estilo_leyes_finos,
)


def _traza(apilado_tms_real=100.0):
    casos = [
        ("TM1", "CuT", 0.61, "TM1", "TORRE", "PROPIO"),
        ("TM1", "CuS", 0.22, "TM2", "TORRE_COMPARTIDA_TM2_A_TM1", "COMPARTIDO_TM2_A_TM1"),
        ("TM1", "FeT", 3.1, "MB", "MINA", "FALLBACK_MB"),
        ("TM1", "CO3", 0.4, "IMP", "IMP", "PROVISIONAL_IMP"),
        ("TM2", "FeS", 1.82, "TM1", "ARRASTRE_ULTIMO_VALIDO", "ARRASTRE"),
        ("TM2", "ConsH", 12.0, "TM2", "TORRE_OTRO_TURNO_MISMO_DIA", "OTRO_TURNO"),
        ("TM2", "CuFe", 0.32, "TM2", "LAB_PROPIO_REPRESENTATIVO", "PROPIO"),
        ("TM2", "CaolBeta", 8.04, "MB", "MB_SIN_RESULTADO_NIR", "FALLBACK_MB"),
        ("TM2", "Malla_Menos_1_2", 95.0, "TM2", "SEMILLA_INICIO_PERIODO", "SEMILLA"),
        # IMP existió antes, pero la metadata FINAL es MB: IMP no aparece.
        ("TM2", "Malla_Menos_100", 66.0, "MB", "MINA", "FALLBACK_MB"),
    ]
    rows = []
    for tm, analito, valor, fuente, tecnica, resolucion in casos:
        rows.append({
            "Fecha": pd.Timestamp("2026-08-19"), "Turno": "B",
            "TM_Destino": tm, "Analito": analito, "Valor_Final": valor,
            "Fuente_Base": fuente, "Fuente_Tecnica": tecnica,
            "Fecha_Origen": pd.Timestamp("2026-08-18") if resolucion == "ARRASTRE" else pd.Timestamp("2026-08-19"),
            "Turno_Origen": "A" if resolucion in {"ARRASTRE", "OTRO_TURNO"} else "B",
            "TM_Origen": fuente if fuente in {"TM1", "TM2"} else None,
            "Resolucion": resolucion,
            "Representatividad_Quimica": 0.8,
            "Representatividad_Fisica": 0.9,
            "Apilado_TMS_Real": apilado_tms_real,
        })
    return pd.DataFrame(rows)


def test_fuentes_finales_colores_y_dataframe_inmutable():
    df = _traza()
    esperado = df.copy(deep=True)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        agregar_hoja_trazabilidad_analitos(writer, df)
    assert_frame_equal(df, esperado)

    ws = load_workbook(io.BytesIO(output.getvalue()), data_only=True)["Trazabilidad Analitos"]
    # Los valores quedan neutros; el mapa de color se concentra en Fuente.
    assert ws.cell(8, 7).fill.fgColor.rgb == "FFFFFFFF"
    assert ws.cell(8, 8).fill.fgColor.rgb == "FF00B0F0"
    assert ws.cell(8, 10).fill.fgColor.rgb == "FF92D050"
    assert ws.cell(8, 12).fill.fgColor.rgb == "FFFFC000"
    assert ws.cell(8, 16).fill.fgColor.rgb == "FFFF0000"
    assert ws.cell(8, 10).value == "TM2"

    # Malla -100 final MB: no conserva el IMP candidato previo.
    assert ws.cell(9, 26).value == "MB"
    assert ws.cell(9, 25).fill.fgColor.rgb == "FFFFFFFF"
    assert ws.cell(9, 26).fill.fgColor.rgb == "FFFFC000"

    assert ws["A5"].value == "IDENTIFICACIÓN"
    assert ws["G5"].value == "QUÍMICA"
    assert ws["W5"].value == "FÍSICA"
    assert ws["AA5"].value == "RESUMEN"
    assert ws["D7"].value == "Estado Operacional"
    assert ws["AA7"].value == "Fuentes Químicas Turno"
    assert ws["AB7"].value == "Fuentes Físicas Turno"
    assert "ponderación por TMS" in ws["A4"].value
    assert ws["AA8"].value == "TM1; TM2; MB; IMP"
    assert ws.freeze_panes == "G8"


def test_trazabilidad_es_ultima_hoja_y_no_cambia_hojas_previas():
    turno = pd.DataFrame({"Fecha": pd.to_datetime(["2026-08-19"]), "Turno": ["B"]})
    diario = pd.DataFrame({"Fecha": pd.to_datetime(["2026-08-19"])})
    libros = []
    for traza in (None, _traza()):
        output = io.BytesIO()
        export_reporte_turno_estilo_leyes_finos(
            turno, output, df_generador=diario,
            df_clays_cufe=pd.DataFrame(), df_trazabilidad_analitos=traza,
        )
        libros.append(load_workbook(io.BytesIO(output.getvalue()), data_only=False))
    assert libros[1].sheetnames[-1] == "Trazabilidad Analitos"
    for nombre in libros[0].sheetnames:
        a, b = libros[0][nombre], libros[1][nombre]
        assert [c.value for row in a.iter_rows() for c in row] == [
            c.value for row in b.iter_rows() for c in row
        ]


def test_turno_sin_tms_es_no_evaluable_y_suprime_presentacion():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        agregar_hoja_trazabilidad_analitos(writer, _traza(apilado_tms_real=0))

    ws = load_workbook(
        io.BytesIO(output.getvalue()), data_only=True
    )["Trazabilidad Analitos"]
    for row in (8, 9):
        assert ws.cell(row, 4).value == "NO EVALUABLE"
        assert ws.cell(row, 5).value is None
        assert ws.cell(row, 6).value is None
        assert ws.cell(row, 27).value == "-"
        assert ws.cell(row, 28).value == "-"
        for value_col in range(7, 27, 2):
            assert ws.cell(row, value_col).value is None
            assert ws.cell(row, value_col + 1).value == "-"


def test_orden_turno_t1_t2_y_porcentajes_visuales():
    a = _traza().copy()
    a["Turno"] = "A"
    a["Fecha"] = pd.Timestamp("2026-08-20")
    b = _traza().copy()
    b["Turno"] = "B"
    b["Fecha"] = pd.Timestamp("2026-08-20")
    df = pd.concat([b, a], ignore_index=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        agregar_hoja_trazabilidad_analitos(writer, df)
    ws = load_workbook(io.BytesIO(output.getvalue()), data_only=True)["Trazabilidad Analitos"]

    assert [(ws.cell(r, 2).value, ws.cell(r, 3).value) for r in range(8, 12)] == [
        ("A", "TM1"), ("A", "TM2"), ("B", "TM1"), ("B", "TM2"),
    ]
    assert ws.cell(8, 5).number_format == "0.0%"
    assert ws.cell(8, 6).number_format == "0.0%"


def test_cobertura_visual_agrega_dos_tm_solo_con_tms_cero():
    cobertura = pd.DataFrame({
        "Fecha": [pd.Timestamp("2026-08-26")],
        "Turno": ["A"],
        "Apilado_TMS_Real": [0.0],
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        agregar_hoja_trazabilidad_analitos(
            writer, pd.DataFrame(), df_cobertura_operacional=cobertura,
        )
    ws = load_workbook(io.BytesIO(output.getvalue()), data_only=True)["Trazabilidad Analitos"]

    assert [(ws.cell(r, 2).value, ws.cell(r, 3).value) for r in (8, 9)] == [
        ("A", "TM1"), ("A", "TM2"),
    ]
    for row in (8, 9):
        assert ws.cell(row, 4).value == "NO EVALUABLE"
        assert ws.cell(row, 5).value is None
        assert ws.cell(row, 6).value is None
        assert ws.cell(row, 7).value is None
        assert ws.cell(row, 8).value == "-"
        assert ws.cell(row, 27).value == "-"
        assert ws.cell(row, 28).value == "-"


def test_cobertura_visual_rechaza_tms_positivo_sin_trazabilidad():
    cobertura = pd.DataFrame({
        "Fecha": [pd.Timestamp("2026-08-27")],
        "Turno": ["B"],
        "Apilado_TMS_Real": [25.0],
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        pd.DataFrame({"control": [1]}).to_excel(writer, sheet_name="Control")
        with pytest.raises(RuntimeError, match="ANOMALIA_TRAZABILIDAD"):
            agregar_hoja_trazabilidad_analitos(
                writer, pd.DataFrame(), df_cobertura_operacional=cobertura,
            )
