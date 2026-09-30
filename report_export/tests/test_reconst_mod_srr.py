import io
from contextlib import nullcontext
from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest
from openpyxl import load_workbook

from report_export import report_export as reports


LAWS = ["CuT_SRR", "CuS_SRR", "ClayBeta_SRR", "Malla100_SRR", "CO3_SRR", "Recuperacion_SRR"]
MB = ["CuT_MinaStock", "CuS_MinaStock", "ClayBeta_MinaStock", "Malla100_MinaStock", "CO3_MinaStock"]


def sources():
    rows = []
    for day in (8, 21, 22, 23, 31):
        for shift in ("A", "B"):
            row = dict(Fecha=pd.Timestamp(2026, 8, day), Turno=shift,
                       SRR_TMS_Turno=0 if day == 22 or (day, shift) in {(8, "A"), (21, "B")} else 100,
                       SRR_TMS_Dia=0 if day == 22 else 100,
                       Flag_Sensibilidad="ALTA_SENSIBILIDAD",
                       TMH_Total_Conciliado=1100.0, TMH_CV008=600.0, TMH_CV108=400.0,
                       Sal_Turno=100.0, Factor_Aplicacion_Reportes=1.2)
            row.update({name: None if day == 22 else (i + 1) / 7 for i, name in enumerate(LAWS)})
            row.update({name: (i + 1) / 13 for i, name in enumerate(MB)})
            rows.append(row)
    srr = pd.DataFrame(rows)
    turno = srr[["Fecha", "Turno"]].copy()
    turno["Apilado_TMS_Real"] = 0.0
    # La preparación histórica transforma orígenes cuando no hay apilado.
    # SRR debe conservar los valores fuente incluso en ese caso.
    turno["STOCK"], turno["MINA"], turno["SRR"] = 12.345678, 0.0, 87.654322
    return srr, turno


def export(srr, turno):
    output = io.BytesIO()
    reports.export_reporte_turno_estilo_leyes_finos(turno, output, df_reconst_srr=srr)
    return load_workbook(io.BytesIO(output.getvalue()))


def test_preserves_null_daily_laws_zero_shift_and_original_inputs():
    srr, turno = sources()
    srr_before, turno_before = srr.copy(deep=True), turno.copy(deep=True)
    wb = export(srr, turno)
    pd.testing.assert_frame_equal(srr, srr_before)
    pd.testing.assert_frame_equal(turno, turno_before)
    assert wb.sheetnames == ["Reporte por Turno", "Reconst Mod SRR"]
    assert wb.active.title == "Reporte por Turno"
    ws = wb["Reconst Mod SRR"]
    assert ws["S9"].value == ws["T10"].value == 0
    for row in (9, 10, 12, 13):
        for col in range(21, 33, 2):
            assert ws.cell(row, col).value == ws.cell(row, col + 1).value
            assert ws.cell(row, col).value is not None
    assert ws["S11"].value == ws["T11"].value == 0
    assert all(ws.cell(11, c).value is None for c in range(21, 33))
    assert ws["M9"].value == 12.345678 and ws["O9"].value == 0
    assert ws["Q9"].value == 87.654322
    assert ws["U9"].number_format == "0.00"
    assert ws["Y9"].number_format == "0.00"
    assert ws.freeze_panes is None
    assert ws["U9"].font.name == wb["Reporte por Turno"]["N23"].font.name
    assert ws["U9"].alignment.horizontal == "center"
    assert ws["D7"].fill.fgColor.rgb == "FF018982"
    assert ws["D7"].font.sz == 12
    assert ws["D9"].number_format == "#,##0"
    assert ws["C9"].number_format == "dd-mm-yyyy"
    assert ws.auto_filter.ref is None
    assert ws.page_setup.fitToHeight == 0
    assert ws.sheet_view.showGridLines is False
    for row in range(9, 14):
        assert [ws.cell(row, col).value for col in range(4, 10)] == [1100, 1100, 660, 660, 440, 440]
    assert all(c.data_type != "f" for row in ws for c in row)


@pytest.mark.parametrize("column", MB + ["SRR_TMS_Dia"])
def test_rejects_inconsistent_daily_values(column):
    srr, turno = sources()
    srr.loc[1, column] = 999
    with pytest.raises(ValueError, match="datos diarios inconsistentes"):
        export(srr, turno)


def test_rejects_daily_null_value_disagreement_and_missing_law():
    srr, turno = sources()
    srr.loc[1, MB[0]] = None
    with pytest.raises(ValueError, match="datos diarios inconsistentes"):
        export(srr, turno)
    with pytest.raises(ValueError, match="faltan columnas SQL"):
        export(srr.drop(columns=[LAWS[0]]), turno)


def test_partial_range_and_absent_shift_are_valid():
    srr, turno = sources()
    wb = export(srr.iloc[[0]], turno.iloc[[0]])
    ws = wb["Reconst Mod SRR"]
    assert ws.max_row == 9
    assert ws["U9"].value is not None and ws["V9"].value is None
    assert ws["AH9"].value == pytest.approx(srr.iloc[0][MB[0]])


@pytest.mark.parametrize("value", [None, pd.DataFrame()])
def test_omitted_or_empty_srr_keeps_legacy_export(value):
    _, turno = sources()
    assert export(value, turno).sheetnames == ["Reporte por Turno"]


def test_fetch_uses_existing_engine_named_dates_and_preserves_nulls(monkeypatch):
    srr, _ = sources()
    srr.loc[0, "Turno"] = " ta "
    read = Mock(return_value=srr)
    connection = object()
    engine = Mock()
    engine.connect.return_value = nullcontext(connection)
    monkeypatch.setattr(reports, "_get_engine", lambda: engine)
    monkeypatch.setattr(reports.pd, "read_sql", read)
    start, end = date(2026, 8, 1), date(2026, 9, 1)
    result = reports.fetch_reconstitucion_srr_report(start, end)
    sql, received_connection = read.call_args.args
    assert received_connection is connection
    assert read.call_args.kwargs["params"] == {"start": start, "end": end}
    assert str(sql).count(":start, :end") == 2
    assert "LEFT JOIN inventar_SpcHidr.fn_reconstitucion_srr_emision_test" in str(sql)
    assert result.iloc[0].Turno == "A" and srr.iloc[0].Turno == " ta "
    assert result.loc[result.Fecha.dt.day == 22, LAWS].isna().all().all()
    duplicated = pd.concat([srr, srr.iloc[[0]].assign(Turno="A")], ignore_index=True)
    read.return_value = duplicated
    with pytest.raises(ValueError, match="contiene duplicados Fecha/Turno"):
        reports.fetch_reconstitucion_srr_report(start, end)


def test_fetch_rejects_invalid_range_without_sql(monkeypatch):
    engine = Mock(side_effect=AssertionError("No SQL para rango inválido"))
    monkeypatch.setattr(reports, "_get_engine", engine)
    with pytest.raises(ValueError, match="fin exclusivo"):
        reports.fetch_reconstitucion_srr_report(date(2026, 9, 1), date(2026, 9, 1))
    engine.assert_not_called()


def test_tmh_uses_published_total_even_if_it_differs_from_gross_factor_minus_salt():
    srr, _ = sources()
    srr["TMH_Total_Conciliado"] = 1200.0
    before = srr.copy(deep=True)
    result = reports._calcular_tmh_reconst_srr(srr)
    assert result.TMH_TM2_Final.eq(440).all()
    assert result.TMH_TM1_Final.eq(760).all()
    pd.testing.assert_frame_equal(srr, before)


def test_tmh_without_activity_is_zero_and_inconsistent_zero_gross_is_rejected():
    srr, _ = sources()
    srr[["TMH_CV008", "TMH_CV108", "Sal_Turno", "TMH_Total_Conciliado"]] = 0.0
    result = reports._calcular_tmh_reconst_srr(srr)
    assert result[["TMH_TM1_Final", "TMH_TM2_Final"]].eq(0).all().all()
    srr.loc[0, "TMH_Total_Conciliado"] = 1.0
    with pytest.raises(ValueError, match="total bruto TMH cero"):
        reports._calcular_tmh_reconst_srr(srr)


@pytest.mark.parametrize("column", ["TMH_Total_Conciliado", "Sal_Turno", "Factor_Aplicacion_Reportes", "TMH_CV008", "TMH_CV108"])
@pytest.mark.parametrize("value", [None, float("inf"), float("-inf")])
def test_tmh_preserves_incomplete_rows_and_calculates_complete_rows(column, value):
    srr, _ = sources()
    srr.loc[0, column] = value
    before = srr.copy(deep=True)
    result = reports._calcular_tmh_reconst_srr(srr)
    assert result.loc[0, ["TMH_TM1_Final", "TMH_TM2_Final"]].isna().all()
    assert result.loc[1:, "TMH_TM1_Final"].eq(660).all()
    assert result.loc[1:, "TMH_TM2_Final"].eq(440).all()
    pd.testing.assert_frame_equal(srr, before)
    assert len(result) == len(srr)


def test_incomplete_tmh_is_blank_in_excel():
    srr, turno = sources()
    srr.loc[:1, ["TMH_Total_Conciliado", "Sal_Turno"]] = None
    ws = export(srr, turno)["Reconst Mod SRR"]
    assert all(ws.cell(9, c).value is None for c in range(6, 10))
    assert [ws.cell(10, c).value for c in range(6, 10)] == [660, 660, 440, 440]


def test_evaluable_zero_gross_with_salt_is_rejected():
    srr, _ = sources()
    srr.loc[0, ["TMH_CV008", "TMH_CV108", "TMH_Total_Conciliado"]] = 0
    with pytest.raises(ValueError, match="total bruto TMH cero"):
        reports._calcular_tmh_reconst_srr(srr)


def test_evaluable_quadrature_loss_is_rejected():
    srr, _ = sources()
    srr.loc[0, "Factor_Aplicacion_Reportes"] = 1e20
    with pytest.raises(ValueError, match="cuadratura"):
        reports._calcular_tmh_reconst_srr(srr)
