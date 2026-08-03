from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from openpyxl import load_workbook

from report_export.export_to_excel import (
    _obtener_fecha_corte_resumen_datos_conciliados,
    aplicar_formato_datos_conciliados,
    calcular_resumen_mtd,
    export_datos_conciliados_to_template,
    obtener_fecha_actualizacion,
)
from report_export.report_export import COLUMNAS_DATOS_CONCILIADOS


def test_export_datos_conciliados_replica_layout_oficial():
    template = Path("reporte/Template_DatosConcialiados.xlsx")
    row = {column: index for index, column in enumerate(COLUMNAS_DATOS_CONCILIADOS)}
    row["Fecha"] = pd.Timestamp("2026-05-30")
    row["Estado"] = 0

    result = export_datos_conciliados_to_template(
        pd.DataFrame([row], columns=COLUMNAS_DATOS_CONCILIADOS),
        str(template),
    )
    ws = load_workbook(BytesIO(result), keep_links=False).active

    assert ws.title == "Datos Conciliados"
    assert ws.print_area == "'Datos Conciliados'!$B$2:$AY$52"
    assert not ws.column_dimensions["AY"].hidden
    assert ws.freeze_panes is None
    assert ws.max_row <= 52
    assert ws["C18"].value == "Día"
    assert ws["AW18"].value == "Producción Cátodos"
    assert ws["C21"].value == pd.Timestamp("2026-05-30").to_pydatetime()
    assert ws["D21"].value == COLUMNAS_DATOS_CONCILIADOS.index("Chancado_TMS_Real")
    assert ws["AX21"].value == COLUMNAS_DATOS_CONCILIADOS.index("Produccion_Catodos_Plan")
    assert ws["AY21"].value is None
    assert not any(
        merged.min_row <= 11 and merged.max_row >= 10
        and merged.min_col <= 18 and merged.max_col >= 16
        for merged in ws.merged_cells.ranges
    )
    assert all(
        cell.value is None and not cell.has_style
        for row_cells in ws["P10:R11"] for cell in row_cells
    )
    assert ws["I3"].value == "mayo"
    assert ws["I4"].value == "FY26"
    assert ws["I5"].value == pd.Timestamp("2026-05-30").to_pydatetime()
    assert ws["Z3"].value == "MTD mayo 2026 al 30-05-2026"
    assert ws["C22"].value is None
    assert ws["C22"].style_id != ws["C52"].style_id
    assert ws["C22"].fill.fgColor.rgb[-6:] == "D7E1E7"
    assert ws["C23"].fill.fgColor.rgb[-6:] == "FFFFFF"
    assert ws["C24"].fill.fgColor.rgb[-6:] == "D7E1E7"
    assert ws["C25"].fill.fgColor.rgb[-6:] == "FFFFFF"
    assert all(ws.row_dimensions[row].hidden for row in range(10, 14))
    assert len(ws._images) == 1
    assert ws._images[0].anchor._from.row < 17
    wb = load_workbook(BytesIO(result), keep_links=False)
    # Ya no se compacta cellXfs con xml.etree.ElementTree (ver
    # _normalizar_y_compactar_estilos_xlsx): ese roundtrip dejaba
    # <selection pane="topRight"> huerfanas al quitar freeze_panes, lo que
    # disparaba el aviso de reparacion de Excel. Sin compactar, un mes
    # completo genera unos cientos de cellXfs -- muy por debajo del limite
    # real de Excel (64.000) -- asi que el techo aqui es solo una guarda
    # contra un crecimiento desmedido, no un valor de compactacion.
    assert len(wb._cell_styles) <= 400
    assert all(ws[f"C{row}"].font.name == "Arial" for row in range(21, 52))
    assert all(ws[f"C{row}"].font.sz == 11 for row in range(21, 52))
    assert all(ws[f"C{row}"].font.color.rgb == "FF476475" for row in range(21, 52))
    assert all(ws[f"D{row}"].font.sz == 10 for row in range(21, 52))
    assert all(ws[f"D{row}"].font.color.rgb == "FF476475" for row in range(21, 52))
    with ZipFile(BytesIO(result)) as archive:
        styles_xml = archive.read("xl/styles.xml").decode("utf-8")
    assert 'rgb="00' not in styles_xml


def test_fecha_actualizacion_ignora_fechas_futuras_solo_con_plan():
    template = Path("reporte/Template_DatosConcialiados.xlsx")
    rows = []
    for fecha, real, plan in (
        ("2026-05-29", 1200, 1500),
        ("2026-05-30", None, 1500),
        ("2026-05-31", 0, 1500),
    ):
        row = {column: None for column in COLUMNAS_DATOS_CONCILIADOS}
        row.update(Fecha=pd.Timestamp(fecha), Chancado_TMS_Real=real, Apilado_TMS_Plan=plan)
        rows.append(row)

    df = pd.DataFrame(rows, columns=COLUMNAS_DATOS_CONCILIADOS)
    assert obtener_fecha_actualizacion(df) == pd.Timestamp("2026-05-29").to_pydatetime()


def test_formato_visual_no_modifica_valores_ni_formulas():
    workbook = load_workbook("reporte/Template_DatosConcialiados.xlsx", keep_links=False)
    ws = workbook.active
    before = {
        cell.coordinate: (cell.value, cell.data_type)
        for row in ws.iter_rows(min_row=2, max_row=52, min_col=2, max_col=51)
        for cell in row
    }

    aplicar_formato_datos_conciliados(ws, 31)

    after = {
        cell.coordinate: (cell.value, cell.data_type)
        for row in ws.iter_rows(min_row=2, max_row=52, min_col=2, max_col=51)
        for cell in row
    }
    assert after == before


def _datos_mtd(fecha_inicio: str, dias: int, ultimo_dia_real: int):
    rows = []
    for fecha in pd.date_range(fecha_inicio, periods=dias):
        row = {column: None for column in COLUMNAS_DATOS_CONCILIADOS}
        row.update(
            Fecha=fecha,
            Chancado_TMS_Real=300,
            Apilado_TMS_Plan=200,
            Ley_CuT_Plan=0.5,
            Cobre_fino_Apilado_Plan=1,
            SRR_TMS_Plan=80,
            Ley_CuT_Plan_srr=0.4,
            TMS_Rotopala_1_Plan=30,
            TMS_Rotopala_2_Plan=20,
            Camiones_TMS_plan=20,
            Total_Ripios_Incluye_Camiones_Plan=70,
            Produccion_Catodos_Plan=5,
        )
        if fecha.day <= ultimo_dia_real:
            row.update(
                Apilado_TMS_Real=100,
                Ley_CuT_Real=1,
                Cobre_fino_Apilado_Real=1,
                SRR_TMS_promedio_dia=50,
                Ley_CuT_Real_srr=0.6,
                TMS_Rotopala_1_Real=30,
                TMS_Rotopala_2_Real=20,
                Camiones_TMS_total=10,
                Total_Ripios_Incluye_Camiones_Real=60,
                Produccion_Catodos_Real=3,
            )
        rows.append(row)
    return pd.DataFrame(rows, columns=COLUMNAS_DATOS_CONCILIADOS)


def test_fecha_corte_se_detiene_en_primera_fila_incompleta():
    df = _datos_mtd("2026-07-01", 31, 31)
    df.loc[30, ["Ley_CuT_Real_srr", "Cobre_fino_Apilado_Plan"]] = None

    assert _obtener_fecha_corte_resumen_datos_conciliados(df) == pd.Timestamp("2026-07-30")

    output = export_datos_conciliados_to_template(
        df, "reporte/Template_DatosConcialiados.xlsx",
    )
    ws = load_workbook(BytesIO(output), keep_links=False).active
    assert ws["Z3"].value == "MTD julio 2026 al 30-07-2026"
    assert ws["AB5"].value == 3000
    assert ws["AC5"].value == 6000
    assert ws["C51"].value == pd.Timestamp("2026-07-31").to_pydatetime()


def test_fecha_corte_retorna_fecha_maxima_si_todo_esta_completo():
    df = _datos_mtd("2026-07-01", 31, 31)
    assert _obtener_fecha_corte_resumen_datos_conciliados(df) == pd.Timestamp("2026-07-31")


def test_fecha_corte_acepta_dependientes_vacios_con_tonelaje_cero():
    df = _datos_mtd("2026-07-01", 1, 1)
    df.loc[0, ["Apilado_TMS_Real", "Apilado_TMS_Plan", "SRR_TMS_promedio_dia", "SRR_TMS_Plan"]] = 0
    df.loc[0, [
        "Ley_CuT_Real", "Cobre_fino_Apilado_Real", "Ley_CuT_Plan",
        "Cobre_fino_Apilado_Plan", "Ley_CuT_Real_srr", "Ley_CuT_Plan_srr",
    ]] = None
    assert _obtener_fecha_corte_resumen_datos_conciliados(df) == pd.Timestamp("2026-07-01")


def test_fecha_corte_rechaza_dependiente_vacio_con_tonelaje_positivo():
    df = _datos_mtd("2026-07-01", 2, 2)
    df.loc[1, "Ley_CuT_Real"] = None
    assert _obtener_fecha_corte_resumen_datos_conciliados(df) == pd.Timestamp("2026-07-01")


def test_fecha_corte_no_salta_un_dia_incompleto():
    df = _datos_mtd("2026-07-01", 20, 20)
    df.loc[14, "Produccion_Catodos_Real"] = None
    assert _obtener_fecha_corte_resumen_datos_conciliados(df) == pd.Timestamp("2026-07-14")


def test_fecha_corte_informa_columnas_estructurales_faltantes():
    df = _datos_mtd("2026-07-01", 1, 1).drop(columns=["Camiones_TMS_plan"])
    with pytest.raises(ValueError, match="Camiones_TMS_plan"):
        _obtener_fecha_corte_resumen_datos_conciliados(df)


def test_fecha_corte_rechaza_primera_fecha_incompleta():
    df = _datos_mtd("2026-07-01", 2, 2)
    df.loc[0, "Produccion_Catodos_Real"] = None
    with pytest.raises(ValueError, match="no existe un tramo consecutivo completo"):
        _obtener_fecha_corte_resumen_datos_conciliados(df)


def test_resumen_mtd_actualiza_corte_y_borde_inferior():
    template = "reporte/Template_DatosConcialiados.xlsx"
    resultados = {}
    for corte in (26, 28, 31):
        df = _datos_mtd("2026-07-01", 31, corte)
        fecha = obtener_fecha_actualizacion(df)
        resumen = calcular_resumen_mtd(df, fecha)
        resultados[corte] = resumen["Apilado"]["real"]
        output = export_datos_conciliados_to_template(df, template)
        ws = load_workbook(BytesIO(output), keep_links=False).active

        assert ws["I5"].value == pd.Timestamp(2026, 7, corte).to_pydatetime()
        assert ws["Z3"].value == f"MTD julio 2026 al {corte:02d}-07-2026"
        assert ws["AB5"].value == 100 * corte
        assert ws["AC5"].value == 200 * corte
        assert ws["AB5"].data_type == "n"
        assert ws.freeze_panes is None
        assert all(ws.cell(51, col).border.bottom.style == "thin" for col in range(3, 51))
    assert resultados == {26: 2600.0, 28: 2800.0, 31: 3100.0}


def test_resumen_mtd_agosto_no_acumula_julio():
    julio = _datos_mtd("2026-07-30", 2, 31)
    agosto = _datos_mtd("2026-08-01", 3, 3)
    df = pd.concat([julio, agosto], ignore_index=True)

    output = export_datos_conciliados_to_template(
        df, "reporte/Template_DatosConcialiados.xlsx",
    )
    ws = load_workbook(BytesIO(output), keep_links=False).active

    assert ws["I5"].value == pd.Timestamp("2026-08-03").to_pydatetime()
    assert ws["Z3"].value == "MTD agosto 2026 al 03-08-2026"
    assert ws["AB5"].value == 300
    assert ws["AC5"].value == 600


def test_marco_inferior_dinamico_30_y_28_dias():
    for fecha_inicio, dias, fila_fin in (
        ("2026-09-01", 30, 50),
        ("2026-02-01", 28, 48),
    ):
        df = _datos_mtd(fecha_inicio, dias, dias)
        output = export_datos_conciliados_to_template(
            df, "reporte/Template_DatosConcialiados.xlsx",
        )
        ws = load_workbook(BytesIO(output), keep_links=False).active

        assert ws.freeze_panes is None
        assert all(
            ws.cell(fila_fin, col).border.bottom.style == "thin"
            for col in range(3, 51)
        )
        assert ws.cell(fila_fin, 3).border.left.style == "thin"
        assert ws.cell(fila_fin, 50).border.right.style == "thin"
