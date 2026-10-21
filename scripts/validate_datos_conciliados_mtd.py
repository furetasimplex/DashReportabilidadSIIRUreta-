"""Valida rango visible parcial contra MTD desde el día 1, solo con lecturas."""

from datetime import date
from io import BytesIO
from pathlib import Path
import sys

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from report_export.export_to_excel import export_datos_conciliados_to_template
from report_export.report_export import (
    fetch_datos_conciliados_emision_report,
    fetch_factor_ajuste_camiones_report,
)


OUTPUT = Path(
    "auditorias/archivo/report_export/exports/Reporte_DatosConciliados_20260803_20260807_MTD_VALIDADO.xlsx"
)


def main() -> None:
    inicio_mtd = date(2026, 8, 1)
    inicio_visible = date(2026, 8, 3)
    fin = date(2026, 8, 7)
    datos_visibles = fetch_datos_conciliados_emision_report(inicio_visible, fin)
    datos_mtd = fetch_datos_conciliados_emision_report(inicio_mtd, fin)
    factor = fetch_factor_ajuste_camiones_report(inicio_visible, fin)
    if datos_visibles.empty or datos_mtd.empty:
        raise RuntimeError("No existen Datos Conciliados para validar agosto 2026.")

    contenido = export_datos_conciliados_to_template(
        datos_visibles,
        "reporte/Template_DatosConcialiados.xlsx",
        df_factor_ajuste=factor,
        rango_personalizado=True,
        df_resumen_mtd=datos_mtd,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(contenido)

    ws = load_workbook(BytesIO(contenido), data_only=True, keep_links=False).active
    print(f"archivo={OUTPUT.resolve()}")
    print(f"filas_visibles={len(datos_visibles)} rango_visible={ws['C21'].value:%d-%m-%Y}..{ws.cell(20 + len(datos_visibles), 3).value:%d-%m-%Y}")
    print(f"filas_mtd={len(datos_mtd)} fecha_actualizacion={ws['I5'].value:%d-%m-%Y}")
    print(f"titulo={ws['Z3'].value}")
    for fila, indicador in ((5, "Apilado"), (6, "Ley CuT"), (7, "Cobre fino"), (8, "SRR"), (9, "Rotopala"), (14, "Camiones"), (15, "Total Ripios"), (16, "Produccion")):
        print(
            f"{indicador}: real={ws[f'AB{fila}'].value} "
            f"plan={ws[f'AC{fila}'].value} var={ws[f'AD{fila}'].value} "
            f"dif={ws[f'AE{fila}'].value}"
        )


if __name__ == "__main__":
    main()
