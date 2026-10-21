"""Genera Datos Conciliados compacto 01-04/08/2026 sin ejecutar mantenedores."""

from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from report_export.export_to_excel import export_datos_conciliados_to_template
from report_export.report_export import (
    fetch_datos_conciliados_emision_report,
    fetch_factor_ajuste_camiones_report,
)


OUTPUT = Path(
    "auditorias/archivo/report_export/exports/Reporte_DatosConciliados_20260801_20260804_RANGO_CORREGIDO.xlsx"
)


def main() -> None:
    inicio = date(2026, 8, 1)
    fin = date(2026, 8, 4)
    datos = fetch_datos_conciliados_emision_report(inicio, fin)
    factor = fetch_factor_ajuste_camiones_report(inicio, fin)
    if datos.empty:
        raise RuntimeError("No existen Datos Conciliados para el rango solicitado.")
    contenido = export_datos_conciliados_to_template(
        datos,
        "reporte/Template_DatosConcialiados.xlsx",
        df_factor_ajuste=factor,
        rango_personalizado=True,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(contenido)
    print(f"archivo={OUTPUT.resolve()} filas={len(datos)}")


if __name__ == "__main__":
    main()
