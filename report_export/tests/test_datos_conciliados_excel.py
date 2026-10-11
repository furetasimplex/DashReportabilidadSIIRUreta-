from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from openpyxl import load_workbook

from report_export.export_to_excel import (
    _validar_balance_chancado,
    _validar_factor_ajuste_camiones,
    _obtener_fecha_corte_resumen_datos_conciliados,
    aplicar_formato_datos_conciliados,
    calcular_resumen_mtd,
    export_datos_conciliados_to_template,
    obtener_fecha_actualizacion,
    DependenciaDatosExportError,
)
from report_export.report_export import COLUMNAS_DATOS_CONCILIADOS


def test_balance_chancado_bloquea_diferencia_publicada():
    fila = {
        "Fecha": pd.Timestamp("2026-08-05"),
        "Humedad": 2.95,
        "Mineral_Apilado_TMH_Original": 6776.0,
        "Factor_Ajuste": 1.0,
        "Mineral_Apilado_TMH_Ajustado": 6776.0,
        "Delta_Ajuste_TMH": 0.0,
        "Mineral_Chancado_Balance": 6067.95148623553,
        "Material": "OXIDOS",
        "Nivel_Promedio_Chancado": 57.3783866882324,
        "Nivel_Promedio_Harneros": 50.2582168579102,
        "Nivel_Promedio_Silo": 51.4628429412842,
        "Bin_Chancado": 1775.94037697714,
        "Bin_Harneros": 1535.96756156049,
        "Tolva_Compensacion": 1200.0,
        "Silo": 1600.58536424012,
        "Total_TMH": 6112.49330277774,
        "Inventario_Chancado_TMH": 4511.90793853762,
        "Inventario_Silo_TMH": 1600.58536424012,
        "Inventario_Chancado_TMS": 4378.80665435076,
        "Inventario_Silo_TMS": 1553.36809599504,
        "Total_TMS": 5932.1747503458,
        "Diferencia_vs_Datos_Conciliados": 0.0628917435,
    }
    fila.update({f"Nivel_Harnero_{letra}": None for letra in "ABCDE"})
    fila.update({f"Nivel_Chancado_{letra}": None for letra in "ABCDE"})
    fila.update({"Nivel_Silo_A": None, "Nivel_Silo_B": None})

    fila.update(Apilado_TMS_Reporte=6000.0, Delta_Inventario_Chancado_TMS=0.0,
                Sal_TMH_Dia=0.0, SRR_TMS_Dia=0.0, Chancado_TMS_Reporte=6000.0,
                Chancado_TMS_Real=5999.9371082565, Modo_Aplicacion="AUTOMATICO",
                Regla_Aplicacion="APLICA_AJUSTE_VALIDADO")
    with pytest.raises(ValueError, match="Chancado_TMS_Real"):
        _validar_balance_chancado(pd.DataFrame([fila]))


def test_balance_chancado_bloquea_delta_ajuste_inconsistente():
    fila = {
        "Fecha": pd.Timestamp("2026-08-09"),
        "Humedad": 2.95,
        "Mineral_Apilado_TMH_Original": 76951.0,
        "Factor_Ajuste": 0.97335748749593,
        "Mineral_Apilado_TMH_Ajustado": 74900.8320202993,
        "Delta_Ajuste_TMH": -2000.0,
        "Mineral_Chancado_Balance": 72966.991171,
        "Material": "SULFUROS",
        "Nivel_Promedio_Chancado": 1.0,
        "Nivel_Promedio_Harneros": 1.0,
        "Nivel_Promedio_Silo": 1.0,
        "Bin_Chancado": 1.0,
        "Bin_Harneros": 1.0,
        "Tolva_Compensacion": 1.0,
        "Silo": 1.0,
        "Inventario_Chancado_TMH": 1.0,
        "Inventario_Silo_TMH": 1.0,
        "Total_TMH": 2.0,
        "Inventario_Chancado_TMS": 1.0,
        "Inventario_Silo_TMS": 1.0,
        "Total_TMS": 2.0,
    }
    fila.update({f"Nivel_Harnero_{letra}": None for letra in "ABCDE"})
    fila.update({f"Nivel_Chancado_{letra}": None for letra in "ABCDE"})
    fila.update({"Nivel_Silo_A": None, "Nivel_Silo_B": None})

    fila.update(Apilado_TMS_Reporte=None, Delta_Inventario_Chancado_TMS=None,
                Sal_TMH_Dia=None, SRR_TMS_Dia=None, Chancado_TMS_Reporte=None,
                Chancado_TMS_Real=None, Diferencia_vs_Datos_Conciliados=None,
                Modo_Aplicacion="AUTOMATICO", Regla_Aplicacion="APLICA_AJUSTE_VALIDADO")
    with pytest.raises(ValueError, match="09-08-2026"):
        _validar_balance_chancado(pd.DataFrame([fila]))


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

    assert ws.title == "Generador Reporte Diario"
    assert ws.print_area == "'Generador Reporte Diario'!$B$2:$AY$52"
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


def test_rango_personalizado_compacta_tabla_y_area_impresion():
    df = _datos_mtd("2026-08-01", 4, 4)
    result = export_datos_conciliados_to_template(
        df,
        "reporte/Template_DatosConcialiados.xlsx",
        rango_personalizado=True,
    )
    ws = load_workbook(BytesIO(result), keep_links=False).active

    assert ws.print_area == "'Generador Reporte Diario'!$B$2:$AY$25"
    assert ws["C21"].value == pd.Timestamp("2026-08-01").to_pydatetime()
    assert ws["C24"].value == pd.Timestamp("2026-08-04").to_pydatetime()
    assert ws["C25"].value is None
    assert not ws.row_dimensions[25].hidden
    assert all(ws.row_dimensions[row].hidden for row in range(26, 52))
    assert all(
        ws.cell(25, col).border.bottom.style == "medium"
        for col in range(2, 52)
    )


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


def _datos_factor_ajuste():
    rows = []
    for fecha in pd.date_range("2026-08-01", periods=5):
        fallback = fecha.day == 5
        rows.append({
            "Fecha": fecha,
            "Chancado_TMH_Sin_Ajuste": 1000.0,
            "Chancado_TMS_Sin_Ajuste": 900.0,
            "Chancado_TMH_Con_Ajuste": 1000.0,
            "Chancado_TMS_Con_Ajuste": 900.0,
            "Carga_KOM_TMH_Viaje_Sin_Ajuste": 50.0,
            "Carga_CAT_TMH_Viaje_Sin_Ajuste": None if fallback else 45.0,
            "Carga_KOM_TMH_Viaje_Con_Ajuste": 50.0,
            "Carga_CAT_TMH_Viaje_Con_Ajuste": None if fallback else 45.0,
            "Factor_Ajuste_Calculado": None if fallback else 1.0,
            "Factor_Aplicacion_Reportes": 1.0,
            "Factor_Aplicacion_Automatica": 1.0,
            "Apilado_TMH_Bruto_Ajustado": None if fallback else 1000.0,
            "Modo_Aplicacion": "AUTOMATICO",
            "Regla_Aplicacion_Automatica": "FALLBACK_SIN_INVENTARIO" if fallback else "APLICA_AJUSTE_VALIDADO",
            "Id_Control_Aplicacion": None,
            "Control_Aplicacion_Motivo": None,
            "Control_Aplicacion_Usuario": None,
            "Control_Aplicacion_Fecha_Registro": None,
            "Vueltas_KOM": 20,
            "Vueltas_CAT": 0 if fallback else 10,
            "Flag_Factor_Ajuste_Valido": 0 if fallback else 1,
            "Estado_Calculo": "SIN_INVENTARIO" if fallback else "OK_SIN_AJUSTE",
            "Regla_Aplicacion": (
                "FALLBACK_SIN_INVENTARIO" if fallback
                else "APLICA_AJUSTE_VALIDADO"
            ),
            "Fecha_Calculo": fecha + pd.Timedelta(hours=8),
        })
    return pd.DataFrame(rows)


def test_export_agrega_hoja_factor_sin_alterar_hoja_principal():
    df = _datos_mtd("2026-08-01", 5, 5)
    template = "reporte/Template_DatosConcialiados.xlsx"
    sin_factor = export_datos_conciliados_to_template(df, template)
    con_factor = export_datos_conciliados_to_template(
        df, template, df_factor_ajuste=_datos_factor_ajuste(),
    )

    wb_sin_factor = load_workbook(BytesIO(sin_factor), keep_links=False)
    wb_con_factor = load_workbook(BytesIO(con_factor), keep_links=False)
    assert "Factor ajuste camiones" in wb_con_factor.sheetnames

    ws_base = wb_sin_factor["Generador Reporte Diario"]
    ws_nueva = wb_con_factor["Generador Reporte Diario"]
    assert [
        [cell.value for cell in row]
        for row in ws_base.iter_rows(min_row=1, max_row=ws_base.max_row)
    ] == [
        [cell.value for cell in row]
        for row in ws_nueva.iter_rows(min_row=1, max_row=ws_nueva.max_row)
    ]

    ws = wb_con_factor["Factor ajuste camiones"]
    assert ws.sheet_view.showGridLines is False
    assert ws.freeze_panes == "A3"
    assert ws.max_column == 14
    assert ws["D2"].value == "Factor calculado"
    assert ws["G2"].value == "Factor aplicado"
    assert ws["A7"].value == pd.Timestamp("2026-08-05").to_pydatetime()
    assert ws["D7"].value is None
    assert ws["L7"].value is None
    assert ws["M7"].value is None
    assert ws["K7"].value == 20
    assert ws["N7"].value == 0
    assert ws["G7"].value == 1
    assert ws["A2"].font.name == "Arial"
    assert ws["A2"].font.bold
    assert ws["A2"].font.color.rgb == "FF476475"
    assert ws["B3"].font.name == "Arial"
    assert ws["B3"].font.sz == 10
    assert ws["B3"].font.color.rgb == "FF476475"
    assert ws["B3"].fill.fgColor.rgb == "FFFFFFFF"
    assert ws["B4"].fill.fgColor.rgb == "FFD7E1E7"
    valores_visibles = {
        ws.cell(row, col).value
        for row in range(1, ws.max_row + 1)
        for col in range(1, ws.max_column + 1)
    }
    assert "Factor aplicado" in valores_visibles
    assert "Factor válido" not in valores_visibles
    assert "Estado cálculo" not in valores_visibles
    assert "Regla aplicación" not in valores_visibles


def test_validar_factor_acepta_fechas_futuras_y_factor_calculado_null():
    df = _datos_mtd("2026-08-01", 5, 5)
    factor = _datos_factor_ajuste()
    _validar_factor_ajuste_camiones(df, factor)

    df_mes_completo = _datos_mtd("2026-08-01", 31, 5)
    _validar_factor_ajuste_camiones(df_mes_completo, factor)


def test_validar_factor_rechaza_huecos_dentro_del_periodo_calculado():
    df = _datos_mtd("2026-08-01", 5, 5)
    factor = _datos_factor_ajuste().drop(index=2)
    with pytest.raises(ValueError, match="03-08-2026"):
        _validar_factor_ajuste_camiones(df, factor)


def test_validar_factor_rechaza_duplicados_y_trazabilidad_null():
    df = _datos_mtd("2026-08-01", 5, 5)
    factor = _datos_factor_ajuste()
    with pytest.raises(ValueError, match="más de una fila"):
        _validar_factor_ajuste_camiones(
            df, pd.concat([factor, factor.iloc[[0]]], ignore_index=True),
        )

    factor.loc[0, "Estado_Calculo"] = None
    with pytest.raises(ValueError, match="Estado_Calculo"):
        _validar_factor_ajuste_camiones(df, factor)


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
    with pytest.raises(DependenciaDatosExportError) as captura:
        _obtener_fecha_corte_resumen_datos_conciliados(df)

    assert "Faltan columnas requeridas para construir el resumen MTD." in str(
        captura.value
    )
    assert "Camiones_TMS_plan" in captura.value.campos


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


def test_resumen_mtd_rotopala_usa_ripios_menos_camiones():
    df = _datos_mtd("2026-08-01", 1, 1)
    df.loc[0, "Total_Ripios_Incluye_Camiones_Real"] = 325000
    df.loc[0, "Camiones_TMS_total"] = 48000
    df.loc[0, "Total_Ripios_Incluye_Camiones_Plan"] = 330000
    df.loc[0, "Camiones_TMS_plan"] = 50000
    df.loc[0, ["TMS_Rotopala_1_Real", "TMS_Rotopala_2_Real"]] = [1, 2]
    df.loc[0, ["TMS_Rotopala_1_Plan", "TMS_Rotopala_2_Plan"]] = [3, 4]

    resumen = calcular_resumen_mtd(df, pd.Timestamp("2026-08-01"))

    assert resumen["Rotopala"]["real"] == 277000
    assert resumen["Rotopala"]["plan"] == 280000


def test_rango_visible_parcial_usa_fuente_mtd_desde_dia_uno():
    df_mtd = _datos_mtd("2026-08-01", 7, 7)
    df_visible = df_mtd.loc[
        pd.to_datetime(df_mtd["Fecha"]) >= pd.Timestamp("2026-08-03")
    ].copy()

    output = export_datos_conciliados_to_template(
        df_visible,
        "reporte/Template_DatosConcialiados.xlsx",
        rango_personalizado=True,
        df_resumen_mtd=df_mtd,
    )
    ws = load_workbook(BytesIO(output), keep_links=False).active

    assert ws["C21"].value == pd.Timestamp("2026-08-03").to_pydatetime()
    assert ws["C25"].value == pd.Timestamp("2026-08-07").to_pydatetime()
    assert ws["I5"].value == pd.Timestamp("2026-08-07").to_pydatetime()
    assert ws["Z3"].value == "MTD agosto 2026 al 07-08-2026"
    assert ws["AB5"].value == 700
    assert ws["AC5"].value == 1400
    assert ws["AB9"].value == 350
    assert ws["AC9"].value == 350


def test_fuente_mtd_mantiene_corte_consecutivo_ante_dia_incompleto():
    df_mtd = _datos_mtd("2026-08-01", 5, 5)
    df_mtd.loc[3, "Produccion_Catodos_Real"] = None
    df_visible = df_mtd.iloc[2:].copy()

    output = export_datos_conciliados_to_template(
        df_visible,
        "reporte/Template_DatosConcialiados.xlsx",
        rango_personalizado=True,
        df_resumen_mtd=df_mtd,
    )
    ws = load_workbook(BytesIO(output), keep_links=False).active

    assert ws["I5"].value == pd.Timestamp("2026-08-03").to_pydatetime()
    assert ws["Z3"].value == "MTD agosto 2026 al 03-08-2026"
    assert ws["AB5"].value == 300


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
