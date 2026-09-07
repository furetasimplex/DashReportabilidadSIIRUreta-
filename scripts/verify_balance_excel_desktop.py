"""Abre una instancia aislada de Excel, sin reparar, actualizar vínculos ni guardar."""
import argparse
import hashlib
import json
from pathlib import Path

import win32com.client


def verify(path):
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
        report = {'file': str(path), 'excel_version': excel.Version,
                  'active_sheet': workbook.ActiveSheet.Name,
                  'scroll_row': workbook.Windows(1).ScrollRow,
                  'scroll_column': workbook.Windows(1).ScrollColumn,
                  'selected_sheets': workbook.Windows(1).SelectedSheets.Count,
                  'zoom': workbook.Windows(1).Zoom,
                  'normal_open_succeeded': True, 'corrupt_load': 0,
                  'sheets': workbook.Worksheets.Count,
                  'case_run': workbook.Worksheets('Resumen').Range('F10').Value,
                  'days': [workbook.Worksheets('Datos Reconciliados').Range(c).Value for c in ('L3', 'L4')]}
        assert report['sheets'] == 9
        assert report['case_run'] == 'Caso 24 | Run oficial 147'
        assert report['days'] == [23, 23]
        assert report['active_sheet'] == 'Resumen'
        assert report['scroll_row'] == report['scroll_column'] == 1
        assert report['selected_sheets'] == 1
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
    args = parser.parse_args()
    result = verify(args.workbook)
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
