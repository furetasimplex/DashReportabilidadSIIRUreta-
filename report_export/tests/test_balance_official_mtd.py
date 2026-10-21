import unittest
import inspect
import hashlib
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from zipfile import ZipFile

import pandas as pd
from openpyxl import load_workbook

from report_export.balance_service import (
    build_balance_official_report,
    get_balance_case_status,
)
from report_export.balance_contract import (
    BALANCE_TEMPLATE_SHA256,
    build_balance_report_identity,
)
from report_export.export_to_excel import export_balance_reconciliacion_to_template
from report_export.report_export import (
    BalanceReportError,
    fetch_recon_balance_official_case,
)
from report_export.callbacks import reportabilidad_cb as cb


def _flows(mass=Decimal("100"), fine=Decimal("1"), count=120):
    return pd.DataFrame([{
        "codigo_flujo": f"F{number}",
        "tolerancia_masa": Decimal("5"),
        "tolerancia_ley": Decimal("1"),
        "masa_medida": mass,
        "masa_reconciliada": mass,
        "ley_cu_medida": Decimal("1"),
        "ley_cu_reconciliada": Decimal("1"),
        "fino_cu_medido": fine,
        "fino_cu_reconciliado": fine,
    } for number in range(1, count + 1)])


def _metadata(case_id, run_id, start, end, model=1):
    return {
        "caso_id": case_id,
        "solver_run_id": run_id,
        "run_id": run_id,
        "nombre_caso": f"Caso {case_id}",
        "fecha_inicio": start,
        "fecha_fin": end,
        "modelo_id": model,
        "estado_run": "success",
        "solver_name": "test",
        "solver_version": "1",
        "es_oficial": True,
    }


def _candidate(case_id, run_id, start, end, mass, fine, model=1):
    frame = _flows(mass, fine)
    meta = _metadata(case_id, run_id, start, end, model)
    for key, value in meta.items():
        if key != "run_id":
            frame[key] = value
    frame["oficializado_en"] = pd.Timestamp("2026-08-31")
    return frame


def _providers(selected_meta, candidates, selected_flows=None):
    period = selected_flows if selected_flows is not None else _flows()
    return (
        lambda caso_id: (period.set_index("codigo_flujo", drop=False), selected_meta),
        lambda modelo_id, start, end: pd.concat(candidates, ignore_index=True),
    )


class OfficialCaseQueryTests(unittest.TestCase):
    def _engine(self):
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = MagicMock()
        return engine

    def test_caso_oficial_valido_devuelve_f1_f120(self):
        meta = pd.DataFrame([_metadata(
            29, 174, date(2026, 8, 20), date(2026, 8, 27)
        )])
        with patch("report_export.report_export._get_engine", return_value=self._engine()), patch(
            "report_export.report_export.pd.read_sql_query",
            side_effect=[pd.DataFrame([{"caso_id": 29}]), meta, _flows()],
        ):
            result, metadata = fetch_recon_balance_official_case(29)
        self.assertEqual(len(result), 120)
        self.assertEqual(set(result["codigo_flujo"]), {f"F{i}" for i in range(1, 121)})
        self.assertEqual(metadata["solver_run_id"], 174)

    def test_caso_sin_oficial_error(self):
        with patch("report_export.report_export._get_engine", return_value=self._engine()), patch(
            "report_export.report_export.pd.read_sql_query",
            side_effect=[pd.DataFrame([{"caso_id": 29}]), pd.DataFrame(), pd.DataFrame()],
        ):
            with self.assertRaisesRegex(BalanceReportError, "no posee un Run oficial"):
                fetch_recon_balance_official_case(29)

    def test_run_oficial_incompleto_error(self):
        meta = pd.DataFrame([_metadata(
            29, 174, date(2026, 8, 20), date(2026, 8, 27)
        )])
        with patch("report_export.report_export._get_engine", return_value=self._engine()), patch(
            "report_export.report_export.pd.read_sql_query",
            side_effect=[pd.DataFrame([{"caso_id": 29}]), meta, _flows(count=119)],
        ):
            with self.assertRaisesRegex(BalanceReportError, "119 flujos"):
                fetch_recon_balance_official_case(29)


class BalanceMtdServiceTests(unittest.TestCase):
    def _build(self, selected_meta, candidates, selected_flows=None):
        fetch_case, fetch_candidates = _providers(
            selected_meta, candidates, selected_flows
        )
        return build_balance_official_report(
            selected_meta["caso_id"], fetch_case, fetch_candidates
        )

    def test_acumulado_normal_ley_ponderada(self):
        selected = _metadata(29, 174, date(2026, 8, 8), date(2026, 8, 14))
        candidates = [
            _candidate(23, 131, date(2026, 8, 1), date(2026, 8, 7), Decimal("100"), Decimal("1")),
            _candidate(29, 174, date(2026, 8, 8), date(2026, 8, 14), Decimal("300"), Decimal("6")),
        ]
        _, accumulated, metadata = self._build(
            selected, candidates, _flows(Decimal("300"), Decimal("6"))
        )
        self.assertEqual(accumulated.loc["F1", "masa_reconciliada_acumulada"], Decimal("400"))
        self.assertEqual(accumulated.loc["F1", "fino_cu_reconciliado_acumulado"], Decimal("7"))
        self.assertEqual(accumulated.loc["F1", "ley_cu_reconciliada_acumulada"], Decimal("1.7500"))
        self.assertEqual(metadata["casos_mtd"], [23, 29])

    def test_gap_temporal_error(self):
        selected = _metadata(29, 174, date(2026, 8, 9), date(2026, 8, 14))
        candidates = [
            _candidate(23, 131, date(2026, 8, 1), date(2026, 8, 7), 100, 1),
            _candidate(29, 174, date(2026, 8, 9), date(2026, 8, 14), 100, 1),
        ]
        with self.assertRaisesRegex(BalanceReportError, "No existe una cobertura"):
            self._build(selected, candidates)

    def test_overlap_error(self):
        selected = _metadata(29, 174, date(2026, 8, 7), date(2026, 8, 14))
        candidates = [
            _candidate(23, 131, date(2026, 8, 1), date(2026, 8, 7), 100, 1),
            _candidate(29, 174, date(2026, 8, 7), date(2026, 8, 14), 100, 1),
        ]
        with self.assertRaisesRegex(BalanceReportError, "deberia terminar 06-08-2026"):
            self._build(selected, candidates)

    def test_sin_cobertura_desde_dia_uno_error(self):
        selected = _metadata(29, 174, date(2026, 8, 8), date(2026, 8, 14))
        with self.assertRaisesRegex(BalanceReportError, "No existe una cobertura"):
            self._build(selected, [
                _candidate(29, 174, date(2026, 8, 8), date(2026, 8, 14), 100, 1)
            ])

    def test_caso_24_dia_uno_ignora_alternativas_y_no_consulta_candidatos(self):
        selected = _metadata(24, 150, date(2026, 8, 1), date(2026, 8, 23))
        period = _flows().set_index("codigo_flujo", drop=False)
        fetch_candidates = MagicMock(side_effect=AssertionError("no debe consultarse"))
        _, _, metadata = build_balance_official_report(
            24, lambda caso_id: (period, selected), fetch_candidates
        )
        fetch_candidates.assert_not_called()
        self.assertEqual(metadata["casos_mtd"], [24])

    def test_caso_21_dia_uno_es_su_propio_mtd(self):
        selected = _metadata(21, 121, date(2026, 8, 1), date(2026, 8, 8))
        _, _, metadata = build_balance_official_report(
            21,
            lambda caso_id: (_flows().set_index("codigo_flujo", drop=False), selected),
            MagicMock(side_effect=AssertionError("no debe consultarse")),
        )
        self.assertEqual(metadata["casos_mtd"], [21])

    def test_caso_22_rechaza_predecesor_que_comparte_dia_08(self):
        selected = _metadata(22, 122, date(2026, 8, 8), date(2026, 8, 15))
        candidates = [
            _candidate(21, 121, date(2026, 8, 1), date(2026, 8, 8), 100, 1),
            _candidate(22, 122, date(2026, 8, 8), date(2026, 8, 15), 100, 1),
        ]
        with self.assertRaisesRegex(BalanceReportError, "deberia terminar 07-08-2026"):
            self._build(selected, candidates)

    def test_caso_23_no_encadena_periodos_con_dias_compartidos(self):
        selected = _metadata(23, 123, date(2026, 8, 15), date(2026, 8, 22))
        candidates = [
            _candidate(21, 121, date(2026, 8, 1), date(2026, 8, 8), 100, 1),
            _candidate(22, 122, date(2026, 8, 8), date(2026, 8, 15), 100, 1),
            _candidate(23, 123, date(2026, 8, 15), date(2026, 8, 22), 100, 1),
        ]
        with self.assertRaisesRegex(BalanceReportError, "deberia terminar 14-08-2026"):
            self._build(selected, candidates)

    def test_predecesor_inclusivo_exacto_construye_cadena(self):
        selected = _metadata(22, 122, date(2026, 8, 8), date(2026, 8, 15))
        candidates = [
            _candidate(21, 121, date(2026, 8, 1), date(2026, 8, 7), 100, 1),
            _candidate(22, 122, date(2026, 8, 8), date(2026, 8, 15), 100, 1),
        ]
        _, _, metadata = self._build(selected, candidates)
        self.assertEqual(metadata["casos_mtd"], [21, 22])

    def test_dos_predecesores_exactos_producen_ambiguedad(self):
        selected = _metadata(23, 123, date(2026, 8, 8), date(2026, 8, 15))
        candidates = [
            _candidate(20, 120, date(2026, 8, 1), date(2026, 8, 7), 100, 1),
            _candidate(21, 121, date(2026, 8, 1), date(2026, 8, 7), 100, 1),
            _candidate(23, 123, date(2026, 8, 8), date(2026, 8, 15), 100, 1),
        ]
        with self.assertRaisesRegex(BalanceReportError, "ambigua"):
            self._build(selected, candidates)


class BalanceOperationalStatusTests(unittest.TestCase):
    def _build(self, selected_meta, candidates, selected_flows=None):
        fetch_case, fetch_candidates = _providers(
            selected_meta, candidates, selected_flows
        )
        return build_balance_official_report(
            selected_meta["caso_id"], fetch_case, fetch_candidates
        )

    @staticmethod
    def _status(selected, candidates):
        period = _flows().set_index("codigo_flujo", drop=False)
        return get_balance_case_status(
            selected["caso_id"],
            lambda caso_id: (period, selected),
            lambda modelo_id, start, end: pd.concat(candidates, ignore_index=True),
        )

    def test_casos_21_y_24_disponibles_sin_buscar_alternativas(self):
        for case_id, run_id, end in (
            (21, 149, date(2026, 8, 8)),
            (24, 147, date(2026, 8, 23)),
        ):
            selected = _metadata(case_id, run_id, date(2026, 8, 1), end)
            fetch_candidates = MagicMock(side_effect=AssertionError("consulta innecesaria"))
            period = _flows().set_index("codigo_flujo", drop=False)
            status = get_balance_case_status(
                case_id,
                lambda caso_id: (period, selected),
                fetch_candidates,
            )
            self.assertTrue(status["mtd_disponible"])
            self.assertEqual(status["mtd_casos"], [case_id])
            self.assertEqual(status["solver_run_id"], run_id)
            fetch_candidates.assert_not_called()

    def test_caso_22_no_disponible_muestra_overlap(self):
        selected = _metadata(22, 148, date(2026, 8, 8), date(2026, 8, 15))
        status = self._status(selected, [
            _candidate(21, 149, date(2026, 8, 1), date(2026, 8, 8), 100, 1),
            _candidate(22, 148, date(2026, 8, 8), date(2026, 8, 15), 100, 1),
        ])
        self.assertFalse(status["mtd_disponible"])
        self.assertIn("deberia terminar 07-08-2026", status["mensaje_mtd"])

    def test_caso_23_no_disponible_no_encadena_solapamientos(self):
        selected = _metadata(23, 120, date(2026, 8, 15), date(2026, 8, 22))
        status = self._status(selected, [
            _candidate(21, 149, date(2026, 8, 1), date(2026, 8, 8), 100, 1),
            _candidate(22, 148, date(2026, 8, 8), date(2026, 8, 15), 100, 1),
            _candidate(23, 120, date(2026, 8, 15), date(2026, 8, 22), 100, 1),
        ])
        self.assertFalse(status["mtd_disponible"])
        self.assertIn("deberia terminar 14-08-2026", status["mensaje_mtd"])

    def test_error_tecnico_no_se_convierte_en_mtd_no_disponible(self):
        def fail(caso_id):
            raise BalanceReportError("DB inaccesible")
        with self.assertRaisesRegex(BalanceReportError, "DB inaccesible"):
            get_balance_case_status(24, fail, MagicMock())

    def test_caso_cross_month_error(self):
        selected = _metadata(29, 174, date(2026, 7, 29), date(2026, 8, 4))
        fetch_case = lambda caso_id: (
            _flows().set_index("codigo_flujo", drop=False), selected
        )
        with self.assertRaisesRegex(BalanceReportError, "cruza meses"):
            build_balance_official_report(29, fetch_case, lambda *args: pd.DataFrame())

    def test_masa_acumulada_cero_ley_none(self):
        selected = _metadata(29, 174, date(2026, 8, 1), date(2026, 8, 7))
        _, accumulated, _ = self._build(selected, [
            _candidate(29, 174, date(2026, 8, 1), date(2026, 8, 7), Decimal("0"), Decimal("5"))
        ], _flows(Decimal("0"), Decimal("5")))
        self.assertIsNone(accumulated.loc["F1", "ley_cu_reconciliada_acumulada"])

    def test_negativos_conservan_signo(self):
        selected = _metadata(29, 174, date(2026, 8, 1), date(2026, 8, 7))
        _, accumulated, _ = self._build(selected, [
            _candidate(29, 174, date(2026, 8, 1), date(2026, 8, 7), Decimal("-100"), Decimal("-2"))
        ], _flows(Decimal("-100"), Decimal("-2")))
        self.assertEqual(accumulated.loc["F1", "masa_reconciliada_acumulada"], Decimal("-100"))
        self.assertEqual(accumulated.loc["F1", "fino_cu_reconciliado_acumulado"], Decimal("-2"))


class BalanceExcelPhase2Tests(unittest.TestCase):
    @staticmethod
    def _export_for_dates(start, end, mtd_start, zero_grade_codes=()):
        period = _flows(Decimal("100"), Decimal("1"))
        accumulated = pd.DataFrame({
            "codigo_flujo": period["codigo_flujo"],
            "masa_reconciliada_acumulada": [Decimal("300")] * 120,
            "ley_cu_reconciliada_acumulada": [Decimal("2")] * 120,
            "fino_cu_reconciliado_acumulado": [Decimal("6")] * 120,
        })
        mask = accumulated["codigo_flujo"].isin(zero_grade_codes)
        accumulated.loc[mask, "masa_reconciliada_acumulada"] = Decimal("0")
        accumulated.loc[mask, "ley_cu_reconciliada_acumulada"] = None
        accumulated.loc[mask, "fino_cu_reconciliado_acumulado"] = Decimal("0")
        metadata = _metadata(24, 147, start, end)
        metadata.update({
            "fecha_inicio_acumulado": mtd_start,
            "fecha_fin_acumulado": end,
        })
        return export_balance_reconciliacion_to_template(
            period,
            accumulated,
            metadata,
            "reporte/Template_Balance_Planta_Hidrometalurgia.xlsx",
        )

    def test_periodo_y_acumulado_se_escriben_en_bloques_separados(self):
        period = _flows(Decimal("100"), Decimal("1"))
        accumulated = pd.DataFrame({
            "codigo_flujo": period["codigo_flujo"],
            "masa_reconciliada_acumulada": [Decimal("300")] * 120,
            "ley_cu_reconciliada_acumulada": [Decimal("2")] * 120,
            "fino_cu_reconciliado_acumulado": [Decimal("6")] * 120,
        })
        metadata = _metadata(
            24, 150, date(2026, 8, 1), date(2026, 8, 23)
        )
        metadata.update({
            "fecha_inicio_acumulado": date(2026, 8, 1),
            "fecha_fin_acumulado": date(2026, 8, 23),
        })
        template = Path("reporte/Template_Balance_Planta_Hidrometalurgia.xlsx")
        content = export_balance_reconciliacion_to_template(
            period, accumulated, metadata, str(template)
        )
        workbook = load_workbook(BytesIO(content), data_only=False, keep_links=True)
        sheet = workbook["Datos Reconciliados"]
        self.assertEqual(sheet["D3"].value, Decimal("100"))
        self.assertEqual(sheet["F3"].value, Decimal("1"))
        self.assertEqual(sheet["G3"].value, Decimal("300"))
        self.assertEqual(sheet["H3"].value, Decimal("2"))
        self.assertEqual(sheet["I3"].value, Decimal("6"))
        self.assertEqual(sheet["D1"].value, "Período 01 al 23 de Agosto 2026")
        self.assertEqual(sheet["G1"].value, "Acumulado 01 al 23 de Agosto 2026")
        analysis = workbook["Análisis Variación-Tolerancias"]
        self.assertEqual(analysis["H4"].value, "=G4-F4")
        self.assertEqual(analysis["L4"].value, "=K4-J4")
        protected_formulas = [
            cell.value
            for row in analysis.iter_rows(min_row=4, max_row=123)
            for cell in row
            if cell.column in (7, 8, 9, 11, 12, 13, 15, 16, 17)
        ]
        self.assertEqual(len(protected_formulas), 1080)
        self.assertTrue(all(
            isinstance(value, str) and value.startswith("=")
            for value in protected_formulas
        ))

        expected_visible = {
            ("Resumen", "E11"): "Período 01 al 23",
            ("Resumen", "F11"): "Acumulado al 23",
            ("Proceso Área Seca", "P14"): "Período 01 al 23 de Agosto",
            ("Proceso Área Húmeda", "U17"): "Período 01 al 23 de Agosto",
            ("Proceso Área Húmeda", "U105"): "Período 01 al 23 de Agosto",
            ("Proceso Área Cátodos", "P14"): "Período 01 al 23 de Agosto",
        }
        for (sheet_name, coordinate), expected in expected_visible.items():
            self.assertEqual(workbook[sheet_name][coordinate].value, expected)
        visible_text = "\n".join(
            str(cell.value)
            for ws in workbook.worksheets
            for row in ws.iter_rows()
            for cell in row
            if cell.value is not None
        )
        self.assertNotIn("01 al 16", visible_text)
        self.assertNotIn("Septiembre", visible_text)
        self.assertEqual(workbook["Proceso Área Seca"]["R14"].value, "Acumulado al 23 de Agosto")
        self.assertEqual(workbook["Proceso Área Húmeda"]["W17"].value, "Acumulado al 23 de Agosto")
        self.assertEqual(workbook["Proceso Área Húmeda"]["W105"].value, "Acumulado al 23 de Agosto")
        self.assertEqual(workbook["Proceso Área Cátodos"]["R14"].value, "Acumulado al 23 de Agosto")
        self.assertEqual(workbook["Resumen"]["F10"].value, "Caso 24 | Run oficial 150")
        self.assertEqual(sheet["L3"].value, 23)
        self.assertEqual(sheet["L4"].value, 23)
        self.assertEqual(
            workbook["Informe Hidrometalurgia"]["F15"].value,
            "='Datos Reconciliados'!L3",
        )

    def test_dias_periodo_y_mtd_se_calculan_independientemente(self):
        eight_days = self._export_for_dates(
            date(2026, 8, 1), date(2026, 8, 8), date(2026, 8, 1)
        )
        workbook = load_workbook(BytesIO(eight_days), data_only=False, keep_links=True)
        self.assertEqual(workbook["Datos Reconciliados"]["L3"].value, 8)
        self.assertEqual(workbook["Datos Reconciliados"]["L4"].value, 8)

        chained = self._export_for_dates(
            date(2026, 8, 8), date(2026, 8, 15), date(2026, 8, 1)
        )
        workbook = load_workbook(BytesIO(chained), data_only=False, keep_links=True)
        self.assertEqual(workbook["Datos Reconciliados"]["L3"].value, 8)
        self.assertEqual(workbook["Datos Reconciliados"]["L4"].value, 15)
        self.assertEqual(
            workbook["Informe Hidrometalurgia"]["F15"].value,
            "='Datos Reconciliados'!L3",
        )

    def test_f10_trazabilidad_visible_preserva_formato_del_template(self):
        template_path = Path("reporte/Template_Balance_Planta_Hidrometalurgia.xlsx")
        template = load_workbook(template_path, data_only=False, keep_links=True)
        output = load_workbook(
            BytesIO(self._export_for_dates(
                date(2026, 8, 1), date(2026, 8, 23), date(2026, 8, 1)
            )),
            data_only=False,
            keep_links=True,
        )
        source_cell = template["Resumen"]["F10"]
        output_cell = output["Resumen"]["F10"]

        self.assertEqual(output_cell.value, "Caso 24 | Run oficial 147")
        self.assertEqual(output_cell.font.color.type, "rgb")
        self.assertEqual(output_cell.font.color.rgb, "FF000000")
        self.assertEqual(output_cell.font.name, source_cell.font.name)
        self.assertEqual(output_cell.font.sz, source_cell.font.sz)
        self.assertEqual(output_cell.font.bold, source_cell.font.bold)
        self.assertEqual(output_cell.font.name, "Arial")
        self.assertEqual(output_cell.font.sz, 12)
        self.assertTrue(output_cell.font.bold)
        self.assertEqual(output_cell.alignment.__dict__, source_cell.alignment.__dict__)
        self.assertEqual(output_cell.fill.__dict__, source_cell.fill.__dict__)
        self.assertEqual(output_cell.border.__dict__, source_cell.border.__dict__)
        self.assertEqual(
            output["Resumen"].row_dimensions[10].height,
            template["Resumen"].row_dimensions[10].height,
        )
        self.assertIn("F10:G10", {str(item) for item in output["Resumen"].merged_cells.ranges})

    def test_drawingml_se_preserva_y_solo_cambia_texto_periodo(self):
        template_path = Path("reporte/Template_Balance_Planta_Hidrometalurgia.xlsx")
        output = self._export_for_dates(
            date(2026, 8, 1), date(2026, 8, 23), date(2026, 8, 1)
        )
        namespace = {
            "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        }
        with ZipFile(template_path) as template, ZipFile(BytesIO(output)) as generated:
            drawing_parts = sorted(
                name for name in template.namelist()
                if name.startswith("xl/drawings/drawing") and name.endswith(".xml")
            )
            self.assertEqual(
                drawing_parts,
                sorted(
                    name for name in generated.namelist()
                    if name.startswith("xl/drawings/drawing") and name.endswith(".xml")
                ),
            )
            for name in sorted(
                item for item in template.namelist()
                if item.startswith("xl/drawings/_rels/")
                or item.startswith("xl/media/")
            ):
                self.assertEqual(generated.read(name), template.read(name), name)
            expected_titles = {
                "xl/drawings/drawing1.xml": "Resumen Balance Planta Hidrometalurgia",
                "xl/drawings/drawing2.xml": "Informe de Balance Planta Hidrometalurgia",
                "xl/drawings/drawing3.xml": "Informe de Balance Planta Hidrometalurgia",
            }
            for name in drawing_parts:
                before = template.read(name)
                after = generated.read(name)
                before_root = ET.fromstring(before)
                after_root = ET.fromstring(after)
                before_counts = tuple(
                    len(before_root.findall(f".//xdr:{kind}", namespace))
                    for kind in ("sp", "cxnSp", "pic", "graphicFrame")
                )
                after_counts = tuple(
                    len(after_root.findall(f".//xdr:{kind}", namespace))
                    for kind in ("sp", "cxnSp", "pic", "graphicFrame")
                )
                self.assertEqual(after_counts, before_counts, name)
                if name in {
                    "xl/drawings/drawing1.xml",
                    "xl/drawings/drawing2.xml",
                    "xl/drawings/drawing3.xml",
                }:
                    texts = [
                        "".join(node.text or "" for node in shape.findall(".//a:t", namespace))
                        for shape in after_root.findall(".//xdr:sp", namespace)
                    ]
                    self.assertIn(expected_titles[name], texts)
                    for root in (before_root, after_root):
                        for node in root.findall(".//a:t", namespace):
                            node.text = ""
                    self.assertEqual(
                        ET.tostring(after_root), ET.tostring(before_root), name
                    )
                    self.assertIn("Período: 01 al 23 de Agosto 2026.", texts)
                else:
                    self.assertEqual(after, before, name)

    def test_none_se_serializa_como_celda_vacia_sin_consumir_el_fino(self):
        zero_grade_codes = {
            "F22", "F30", "F31", "F32", "F34", "F41", "F43", "F45",
            "F47", "F56", "F58", "F66", "F87", "F101", "F102", "F103",
            "F104", "F105", "F106", "F110", "F111", "F112", "F113",
            "F114", "F119", "F120",
        }
        output = self._export_for_dates(
            date(2026, 8, 1),
            date(2026, 8, 23),
            date(2026, 8, 1),
            zero_grade_codes,
        )
        with ZipFile(BytesIO(output)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(archive.infolist()), 66)
            self.assertEqual(
                len({item.filename for item in archive.infolist()}), 66
            )
            sheet_xml = archive.read("xl/worksheets/sheet5.xml")
            root = ET.fromstring(sheet_xml)
        namespace = {
            "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        }
        for code in zero_grade_codes:
            row_number = int(code[1:]) + 2
            grade = root.find(f".//m:c[@r='H{row_number}']", namespace)
            fine = root.find(f".//m:c[@r='I{row_number}']", namespace)
            self.assertIsNotNone(grade, code)
            self.assertNotIn("t", grade.attrib, code)
            self.assertEqual(len(grade), 0, code)
            self.assertIsNotNone(fine, code)
            self.assertEqual(fine.find("m:v", namespace).text, "0", code)
            row = root.find(f".//m:row[@r='{row_number}']", namespace)
            refs = [cell.attrib["r"] for cell in row.findall("m:c", namespace)]
            self.assertEqual(refs.count(f"H{row_number}"), 1, code)
            self.assertEqual(refs.count(f"I{row_number}"), 1, code)


class BalanceDashPhase2Tests(unittest.TestCase):
    def test_selector_muestra_caso_nombre_periodo_y_conserva_caso_id(self):
        cases = pd.DataFrame([
            {
                "caso_id": 24,
                "nombre_caso": "Caso hidrometalurgia Agosto",
                "modelo_id": 2,
                "fecha_inicio": date(2026, 8, 1),
                "fecha_fin": date(2026, 8, 23),
            },
            {
                "caso_id": 22,
                "nombre_caso": "Agosto 2",
                "fecha_inicio": date(2026, 8, 8),
                "fecha_fin": date(2026, 8, 15),
            },
        ])
        with patch.object(cb, "fetch_recon_balance_official_cases", return_value=cases):
            options, selected = cb.cargar_casos_oficiales_balance(
                "tab-semanales", None
            )
        self.assertEqual(selected, 24)
        self.assertEqual(options[0]["value"], 24)
        self.assertEqual(
            options[0]["label"].children,
            "Caso 24 · V2 · 01–23 ago 2026",
        )
        self.assertIn("Caso hidrometalurgia Agosto", options[0]["search"])

    def test_estado_sin_caso_no_consulta_y_deshabilita(self):
        with patch.object(cb, "get_balance_case_status") as service:
            card, disabled, _context = cb.actualizar_estado_balance(None)
        service.assert_not_called()
        self.assertTrue(disabled)
        self.assertEqual(card.color, "secondary")
        self.assertIn("Seleccione un Caso oficial", str(card.children))

    def test_estado_disponible_muestra_run_periodo_y_cadena(self):
        status = {
            "caso_id": 24,
            "nombre_caso": "Caso hidrometalurgia Agosto",
            "fecha_inicio": date(2026, 8, 1),
            "fecha_fin": date(2026, 8, 23),
            "solver_run_id": 147,
            "estado_run": "success",
            "oficial": True,
            "mtd_disponible": True,
            "mtd_fecha_inicio": date(2026, 8, 1),
            "mtd_fecha_fin": date(2026, 8, 23),
            "mtd_casos": [24],
            "mensaje_mtd": None,
        }
        with patch.object(cb, "get_balance_case_status", return_value=status) as service:
            card, disabled, _context = cb.actualizar_estado_balance(24)
        service.assert_called_once_with(24)
        self.assertFalse(disabled)
        self.assertEqual(card.color, "success")
        text = str(card.children)
        for expected in ("Run oficial", "147", "01-08-2026", "23-08-2026", "Casos MTD", "24"):
            self.assertIn(expected, text)

    def test_estado_no_disponible_muestra_warning_y_motivo(self):
        status = {
            "caso_id": 22,
            "nombre_caso": "Agosto 2",
            "fecha_inicio": date(2026, 8, 8),
            "fecha_fin": date(2026, 8, 15),
            "solver_run_id": 148,
            "estado_run": "success",
            "oficial": True,
            "mtd_disponible": False,
            "mtd_fecha_inicio": date(2026, 8, 1),
            "mtd_fecha_fin": date(2026, 8, 15),
            "mtd_casos": [],
            "mensaje_mtd": "El Caso 21 termina 08-08-2026 y debia terminar 07-08-2026.",
        }
        with patch.object(cb, "get_balance_case_status", return_value=status):
            card, disabled, _context = cb.actualizar_estado_balance(22)
        self.assertTrue(disabled)
        self.assertEqual(card.color, "warning")
        self.assertIn("debia terminar 07-08-2026", str(card.children))

    def test_error_tecnico_se_muestra_como_danger(self):
        with patch.object(
            cb, "get_balance_case_status", side_effect=BalanceReportError("DB inaccesible")
        ):
            card, disabled, _context = cb.actualizar_estado_balance(24)
        self.assertTrue(disabled)
        self.assertEqual(card.color, "danger")
        self.assertNotIn("DB inaccesible", str(card.children))

    def test_callback_estado_no_infiere_run_por_max_ni_fechas_globales(self):
        source = inspect.getsource(cb.actualizar_estado_balance).upper()
        self.assertNotIn("MAX(", source)
        self.assertNotIn("REPORT-FECHA", source)
        self.assertIn("GET_BALANCE_CASE_STATUS", source)

    def test_callback_resuelve_balance_por_caso_id(self):
        metadata = _metadata(
            29, 174, date(2026, 8, 20), date(2026, 8, 27)
        )
        metadata.update({
            "fecha_inicio_acumulado": date(2026, 8, 1),
            "fecha_fin_acumulado": date(2026, 8, 27),
        })
        period = _flows()
        accumulated = pd.DataFrame({
            "codigo_flujo": period["codigo_flujo"],
            "masa_reconciliada_acumulada": [100] * 120,
            "ley_cu_reconciliada_acumulada": [1] * 120,
            "fino_cu_reconciliado_acumulado": [1] * 120,
        })
        with (
            patch.object(
                cb,
                "ctx",
                SimpleNamespace(
                    triggered_id={"type": "report-export-btn", "tipo": "balance"}
                ),
            ),
            patch.object(
                cb,
                "build_balance_official_report",
                return_value=(period, accumulated, metadata),
            ) as service,
            patch.object(
                cb,
                "export_balance_reconciliacion_to_template",
                return_value=b"xlsx",
            ) as writer,
        ):
            result = cb.exportar_excel(
                [1], "2026-01-01", "2026-01-31", "mes", 29
            )
        service.assert_called_once_with(29)
        writer.assert_called_once_with(
            period, accumulated, metadata, cb.BALANCE_TEMPLATE_XLSX_PATH
        )
        self.assertIn("Caso 29", result[1])
        self.assertIn("Run oficial 174", result[1])
        self.assertIn(
            "Balance_Planta_Hidrometalurgia_20260820_20260827_Caso29_Run174.xlsx",
            str(result[0]),
        )
        self.assertNotIn("NO OFICIAL", result[1])


class BalanceIdentityPhase4Tests(unittest.TestCase):
    def test_identidad_caso_24(self):
        identity = build_balance_report_identity({
            "caso_id": 24,
            "solver_run_id": 147,
            "fecha_inicio": date(2026, 8, 1),
            "fecha_fin": date(2026, 8, 23),
            "fecha_inicio_acumulado": date(2026, 8, 1),
            "fecha_fin_acumulado": date(2026, 8, 23),
        })
        self.assertEqual(
            identity["filename"],
            "Balance_Planta_Hidrometalurgia_20260801_20260823_Caso24_Run147.xlsx",
        )
        self.assertEqual(identity["caso_label"], "Caso 24")
        self.assertEqual(identity["run_label"], "Run oficial 147")
        self.assertEqual(identity["periodo_label"], "Período 01/08/2026 al 23/08/2026")
        self.assertEqual(identity["mtd_label"], "Acumulado 01/08/2026 al 23/08/2026")

    def test_identidad_otro_mes_y_cambio_de_ano(self):
        for metadata, expected in (
            ({
                "caso_id": 21,
                "solver_run_id": 149,
                "fecha_inicio": date(2026, 8, 1),
                "fecha_fin": date(2026, 8, 8),
                "fecha_inicio_acumulado": date(2026, 8, 1),
                "fecha_fin_acumulado": date(2026, 8, 8),
            }, "Balance_Planta_Hidrometalurgia_20260801_20260808_Caso21_Run149.xlsx"),
            ({
                "caso_id": 40,
                "solver_run_id": 200,
                "fecha_inicio": date(2027, 1, 1),
                "fecha_fin": date(2027, 1, 9),
                "fecha_inicio_acumulado": date(2027, 1, 1),
                "fecha_fin_acumulado": date(2027, 1, 9),
            }, "Balance_Planta_Hidrometalurgia_20270101_20270109_Caso40_Run200.xlsx"),
        ):
            self.assertEqual(build_balance_report_identity(metadata)["filename"], expected)

    def test_hash_contractual_del_template(self):
        digest = hashlib.sha256(
            Path("reporte/Template_Balance_Planta_Hidrometalurgia.xlsx").read_bytes()
        ).hexdigest().upper()
        self.assertEqual(digest, BALANCE_TEMPLATE_SHA256)


if __name__ == "__main__":
    unittest.main()
