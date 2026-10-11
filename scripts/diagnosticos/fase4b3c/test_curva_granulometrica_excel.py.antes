import io

import pandas as pd
from openpyxl import load_workbook

from report_export.report_export import export_reporte_turno_estilo_leyes_finos


def _df_turno():
    return pd.DataFrame({
        "Fecha": [pd.Timestamp("2026-08-06")],
        "Turno": ["A"],
        "Apilado_TMS_Real": [1000.0],
    })


def test_curva_granulometrica_usa_valores_sql_y_orden_solicitado():
    curva = pd.DataFrame({
        "Fecha": [pd.Timestamp("2026-08-06")], "Turno": ["A"],
        "Ton_TM1": [16299.0], "Ton_TM2": [3362.0],
        "Rep_Fisica_TM1": [0.4839203607], "Rep_Fisica_TM2": [0.0],
        "Tiene_Curva_TM1": [1], "Tiene_Curva_TM2": [0],
        "Torres_Utilizadas": ["TM1"], "P2": [100.0], "P1": [99.14],
        "P34": [94.841], "P12": [84.975], "P14": [71.76],
        "P10": [58.816], "P35": [48.86], "P100": [43.972],
        "P150": [0.0], "P200": [0.0], "P325": [0.0],
        "PBajo325": [0.0],
    })
    output = io.BytesIO()
    export_reporte_turno_estilo_leyes_finos(
        _df_turno(), output, df_curva_granulometrica=curva,
        periodo_inicio=pd.Timestamp("2026-08-01").date(),
        periodo_fin=pd.Timestamp("2026-08-31").date(),
    )
    workbook = load_workbook(io.BytesIO(output.getvalue()), data_only=True)
    assert workbook.sheetnames == ["Reporte por Turno", "Curva Granulométrica"]
    ws = workbook["Curva Granulométrica"]
    assert ws["A1"].value == "Curva Granulométrica - Torres de Muestreo"
    assert ws["A3"].value == "Período: 01-08-2026 al 31-08-2026"
    assert ws["A7"].value == "IDENTIFICACIÓN"
    assert ws["C7"].value == "MASA"
    assert ws["E7"].value == "REPRESENTATIVIDAD FÍSICA"
    assert ws["G7"].value == "TRAZABILIDAD"
    assert ws["J7"].value == "PASANTE ACUMULADO (%)"
    assert [ws.cell(8, col).value for col in range(10, 22)] == [
        '2"', '1"', '3/4"', '1/2"', '1/4"', '#10', '#35', '#100',
        '#150', '#200', '#325', '-#325',
    ]
    assert ws["A9"].value == pd.Timestamp("2026-08-06").to_pydatetime()
    assert ws["B9"].value == "A"
    assert ws["C9"].value == 16299.0
    assert ws["G9"].value == "Sí"
    assert ws["H9"].value == "No"
    assert ws["I9"].value == "TM1"
    assert ws["J9"].value == 100.0
    assert ws["K9"].value == 99.14
    assert ws["U9"].value == 0.0
    assert ws["E9"].number_format == "0.00%"
    assert ws["J9"].number_format == '0.00 "%"'
    assert ws.freeze_panes == "C9"
    assert ws.auto_filter.ref == "A8:U9"


def test_sin_dataframe_curva_no_cambia_hojas_existentes():
    output = io.BytesIO()
    export_reporte_turno_estilo_leyes_finos(_df_turno(), output)
    workbook = load_workbook(io.BytesIO(output.getvalue()), read_only=True)
    assert workbook.sheetnames == ["Reporte por Turno"]
