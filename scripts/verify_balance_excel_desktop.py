"""Abre una instancia aislada de Excel, sin reparar, actualizar vínculos ni guardar."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import win32com.client


def verify(path, case_id=24, run_id=147, days=23):
    path = Path(path).resolve()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    excel = win32com.client.DispatchEx('Excel.Application')
    workbook = None
    try:
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.EnableEvents = False
        excel.AutomationSecurity = 3
        workbook = excel.Workbooks.Open(
            str(path), UpdateLinks=0, ReadOnly=True, IgnoreReadOnlyRecommended=True,
            AddToMru=False, CorruptLoad=0,
        )
        deadline = time.monotonic() + 20
        while excel.CalculationState == 1 and time.monotonic() < deadline:
            time.sleep(0.1)
        print('Estado de cálculo:', excel.CalculationState,
              'Resumen!E12:', workbook.Worksheets('Resumen').Range('E12').Value,
              'Informe!F15:', workbook.Worksheets('Informe Hidrometalurgia').Range('F15').Value)
        assert excel.CalculationState != 1, 'Excel sigue calculando'
        report = {'file': str(path), 'excel_version': excel.Version,
                  'calculation_state': excel.CalculationState,
                  'active_cell': excel.ActiveCell.Address,
                  'selection': excel.Selection.Address,
                  'active_sheet': workbook.ActiveSheet.Name,
                  'scroll_row': workbook.Windows(1).ScrollRow,
                  'scroll_column': workbook.Windows(1).ScrollColumn,
                  'selected_sheets': workbook.Windows(1).SelectedSheets.Count,
                  'zoom': workbook.Windows(1).Zoom,
                  'normal_open_succeeded': True, 'corrupt_load': 0,
                  'sheets': workbook.Worksheets.Count,
                  'case_run': workbook.Worksheets('Resumen').Range('F10').Value,
                  'days': [workbook.Worksheets('Datos Reconciliados').Range(c).Value for c in ('L3', 'L4')],
                  'summary_e12': workbook.Worksheets('Resumen').Range('E12').Value,
                  'report_f15': workbook.Worksheets('Informe Hidrometalurgia').Range('F15').Value,
                  'data_f1_mass': workbook.Worksheets('Datos Reconciliados').Range('D3').Value,
                  'data_f1_fine': workbook.Worksheets('Datos Reconciliados').Range('F3').Value,
                  'summary_period': workbook.Worksheets('Resumen').Range('E11').Value,
                  'summary_accumulated': workbook.Worksheets('Resumen').Range('F11').Value,
                  'analysis_g4_k4_o4': [workbook.Worksheets('Análisis Variación-Tolerancias').Range(c).Value for c in ('G4', 'K4', 'O4')]}
        assert report['sheets'] == 9
        assert report['case_run'] == f'Caso {case_id} | Run oficial {run_id}'
        assert report['days'] == [days, days]
        assert report['report_f15'] == days
        assert report['summary_e12'] == report['data_f1_mass']
        assert report['analysis_g4_k4_o4'] == [workbook.Worksheets('Datos Reconciliados').Range(c).Value for c in ('D3', 'E3', 'F3')]
        assert report['summary_period'] == f'Período 01 al {days:02d}'
        assert report['summary_accumulated'] == f'Acumulado al {days:02d}'
        if case_id == 21:
            assert math.isclose(report['summary_e12'], 253003.6957, rel_tol=1e-12)
            assert math.isclose(report['data_f1_fine'], 2203.433327, rel_tol=1e-12)
        assert report['active_sheet'] == 'Resumen'
        assert report['scroll_row'] == report['scroll_column'] == 1
        assert report['selected_sheets'] == 1
        assert report['active_cell'] == report['selection'] == '$A$1'
        assert report['zoom'] == 85
        return report
    finally:
        if workbook is not None:
            workbook.Close(SaveChanges=False)
        excel.Quit()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('workbook')
    parser.add_argument('report')
    parser.add_argument('--case', type=int, default=24)
    parser.add_argument('--run', type=int, default=147)
    parser.add_argument('--days', type=int, default=23)
    args = parser.parse_args()
    result = verify(args.workbook, args.case, args.run, args.days)
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
