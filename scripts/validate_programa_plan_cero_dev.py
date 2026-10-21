"""Inspección y validación de presentación Programa/Plan, exclusivamente DEV."""
import os
from pathlib import Path
import sys
import io
import json
from datetime import date
from unittest.mock import patch

import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from report_export import report_export as rep
from sqlalchemy import text


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    assert os.getenv("SQLSERVER_HOST") == "149.50.136.234", "Solo DEV"
    target = ROOT / "auditorias/archivo/report_export/exports/validacion_programa_plan_cero"
    target.mkdir(parents=True, exist_ok=True)
    with rep._get_engine().connect() as conn:
        for name in ["inventar_SpcHidr.sp_reporte_turno_emision_test",
                     rep.SP_GENERADOR_REPORTE_DIARIO_EMISION,
                     "inventar_SpcHidr.fn_generador_reporte_diario_emision_test"]:
            definition = conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID(:name))"), {"name": name}).scalar()
            if definition:
                (target / (name.split('.')[-1] + '.sql')).write_text(definition, encoding="utf-8")
                print(name)
    if "--export" not in sys.argv:
        return
    inicio, fin = date(2026, 9, 1), date(2026, 10, 1)
    turno = rep.fetch_reporte_turno_cache_emision(inicio, fin)
    diario = rep.fetch_generador_reporte_diario_emision(inicio, fin)
    kwargs = dict(df_generador=diario, df_generador_resumen=diario,
                  df_clays_cufe=rep.fetch_clays_cufe_report(inicio, fin),
                  df_trazabilidad_analitos=rep.fetch_trazabilidad_analitos_report(inicio, fin),
                  df_curva_granulometrica=rep.fetch_curva_granulometrica_report(inicio, fin),
                  df_reconst_srr=rep.fetch_reconstitucion_srr_report(inicio, fin),
                  periodo_inicio=inicio, periodo_fin=date(2026, 9, 30))
    before, after = io.BytesIO(), io.BytesIO()
    with patch.object(rep, "_presentar_derivados_programa_plan", return_value=None):
        rep.export_reporte_turno_estilo_leyes_finos(turno, before, **kwargs)
    rep.export_reporte_turno_estilo_leyes_finos(turno, after, **kwargs)
    path = target / "Analisis_Torres_de_Muestreo_20260901_20260930.xlsx"
    path.write_bytes(after.getvalue())
    old, new = load_workbook(before), load_workbook(after)
    cambios = []
    for ws in new:
        anterior = old[ws.title]
        assert str(ws.merged_cells) == str(anterior.merged_cells)
        assert (ws.max_row, ws.max_column) == (anterior.max_row, anterior.max_column)
        for row in ws:
            for cell in row:
                prev = anterior[cell.coordinate]
                assert cell._style == prev._style
                if cell.value != prev.value:
                    cambios.append([ws.title, cell.coordinate, prev.value, cell.value])
                    assert ws.title in ["Reporte por Turno", "Generador Reporte"]
                    assert cell.value == 0 and prev.value in (None, 14)
    prepared = [rep.preparar_df_reporte_turno_excel(turno, diario),
                rep.preparar_df_generador_reporte_excel(diario)]
    checks = {}
    for data, sufijos, hoja in zip(prepared, [("Plan_Semanal", "Plan_Mensual"), ("Programa", "Plan")],
                                   ["Reporte por Turno", "Generador Reporte"]):
        cols = [f"Solubilidad_{sufijos[0]}", f"Solubilidad_{sufijos[1]}", "Dosis_Acido_Programa_Semanal"]
        for dia in [1, 2, 3]:
            row = data.loc[data.Fecha.dt.day.eq(dia)].iloc[0]
            valores = [float(row[c]) for c in cols]
            if dia < 3:
                assert valores == [0, 0, 0]
            else:
                assert abs(valores[0] - .074936 / .477215) < .000002
                assert abs(valores[1] - .053639 / .591030) < .000002
                assert valores[2] == 14
            checks[f"{hoja} 2026-09-{dia:02}"] = valores
    real10 = prepared[0].loc[prepared[0].Fecha.dt.day.eq(10)]
    assert real10.Apilado_TMS_Real.tolist() == [34092.869, 34091.902]
    assert real10.CuT_Real.tolist() == [.531817, .572627]
    assert abs(prepared[1].loc[prepared[1].Fecha.dt.day.eq(10), "Apilado_TMS_Real_Dia"].iloc[0] - 68184.771) < .000001
    assert len(cambios) == 12, cambios
    report = {"indicadores": checks, "cambios_celdas": cambios,
              "regresion_10_09": "OK", "fusiones_estilos_otras_celdas": "sin cambios"}
    (target / "validacion.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(path)


if __name__ == "__main__":
    main()
