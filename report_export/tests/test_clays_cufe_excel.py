import io

import pandas as pd
from openpyxl import load_workbook
from pandas.testing import assert_frame_equal

from report_export.report_export import (
    agregar_hoja_clays_cufe,
    export_reporte_turno_estilo_leyes_finos,
)


def _df_clays():
    return pd.DataFrame({
        "Fecha": pd.to_datetime([
            "2026-08-01", "2026-08-01", "2026-08-01", "2026-08-01",
        ]),
        "Torre": ["TM2", "TM1", "TM1", "TM2"],
        "Turno": ["B", "B", "A", "A"],
        "CaolBeta": [None, 8.53, 7.12, 6.42],
        "CuFe": [0.21, 0.26, 0.18, 0.32],
        "Fuente_CaolBeta": ["IMP", "TM2", "MB", "TM1"],
        "Fuente_CuFe": ["IMP", "TM2", "MB", "TM1"],
    })


def _workbook_clays(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        agregar_hoja_clays_cufe(writer, df)
    return load_workbook(io.BytesIO(output.getvalue()), data_only=True)


def test_colores_fuente_null_y_tm2_compartido_en_fila_tm1():
    workbook = _workbook_clays(_df_clays())
    ws = workbook["Clays-CuFe"]

    # Orden: Fecha, TM1 TA, TM1 TB, TM2 TA, TM2 TB.
    assert ws["A6"].value == "01-08-2026 TORRE N°1 TB"
    assert ws["G6"].value == "TM2"
    assert ws["H6"].value == "TM2"
    assert ws["E6"].fill.fgColor.rgb == "FF92D050"
    assert ws["F6"].fill.fgColor.rgb == "FF92D050"

    assert ws["E5"].fill.fgColor.rgb == "FFFFC000"  # MB
    assert ws["F5"].fill.fgColor.rgb == "FFFFC000"
    assert ws["E7"].fill.fgColor.rgb == "FF00B0F0"  # TM1
    assert ws["F7"].fill.fgColor.rgb == "FF00B0F0"
    assert ws["F8"].fill.fgColor.rgb == "FFFF0000"  # IMP
    assert ws["E8"].value is None


def test_dataframe_original_no_se_muta():
    original = _df_clays()
    esperado = original.copy(deep=True)
    _workbook_clays(original)
    assert_frame_equal(original, esperado)


def test_clays_cufe_es_ultima_hoja_y_workbook_abre():
    turno = pd.DataFrame({
        "Fecha": pd.to_datetime(["2026-08-01"]),
        "Turno": ["A"],
    })
    diario = pd.DataFrame({"Fecha": pd.to_datetime(["2026-08-01"])})
    output = io.BytesIO()
    export_reporte_turno_estilo_leyes_finos(
        turno,
        output,
        df_generador=diario,
        df_clays_cufe=_df_clays(),
    )
    workbook = load_workbook(io.BytesIO(output.getvalue()), data_only=True)
    assert workbook.sheetnames == [
        "Reporte por Turno", "Generador Reporte", "Malla #100", "Clays-CuFe",
    ]


def test_agregar_clays_no_cambia_valores_de_hojas_existentes():
    turno = pd.DataFrame({
        "Fecha": pd.to_datetime(["2026-08-01", "2026-08-01"]),
        "Turno": ["A", "B"],
        "CuFe_Real": [0.26, 0.31],
        "CaolBeta_Real": [8.53, 9.10],
    })
    diario = pd.DataFrame({
        "Fecha": pd.to_datetime(["2026-08-01"]),
        "CuFe_Real_Dia": [0.285],
        "CaolBeta_Real_Dia": [8.815],
    })

    libros = []
    for clays in (None, _df_clays()):
        output = io.BytesIO()
        export_reporte_turno_estilo_leyes_finos(
            turno,
            output,
            df_generador=diario,
            df_clays_cufe=clays,
        )
        libros.append(load_workbook(io.BytesIO(output.getvalue()), data_only=False))

    for sheet_name in ("Reporte por Turno", "Generador Reporte", "Malla #100"):
        antes = libros[0][sheet_name]
        despues = libros[1][sheet_name]
        assert antes.max_row == despues.max_row
        assert antes.max_column == despues.max_column
        assert [
            cell.value for row in antes.iter_rows() for cell in row
        ] == [
            cell.value for row in despues.iter_rows() for cell in row
        ]
