from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from report_export.callbacks.reportabilidad_cb import _agregar_hoja_grafico_gestion_fy


OUTPUT = Path("report_export/exports/prueba_etiquetas_fy27.xlsx")


workbook = Workbook()
workbook.remove(workbook.active)

for tipo, valores in (
    ("Fisico", [0.044, 0.000, 0.037]),
    ("Quimico", [0.123, 0.067, 0.111]),
):
    dataframe = pd.DataFrame(
        {
            "Etiqueta": ["Jul-26", "Ago-26", "YTD"],
            "Turnos_Evaluables": [100, 100, 200],
            "Turnos_Representativos": [round(v * 100) for v in valores],
            "Representatividad": valores,
            "Objetivo": [0.85, 0.85, 0.85],
        }
    )
    _agregar_hoja_grafico_gestion_fy(
        workbook,
        dataframe,
        tipo,
        pd.Timestamp("2026-08-08"),
    )

workbook.save(OUTPUT)
print(OUTPUT.resolve())
