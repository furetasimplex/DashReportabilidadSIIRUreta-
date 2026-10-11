"""Genera y valida Análisis TM 01-04/08/2026 sin ejecutar mantenedores."""

from datetime import date
from pathlib import Path
import io
import sys

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from report_export.report_export import (
    export_reporte_turno_estilo_leyes_finos,
    fetch_generador_reporte_diario_emision,
    fetch_reporte_turno_cache_emision,
)


OUTPUT = Path("report_export/exports/Analisis_Torres_de_Muestreo_20260801_20260804_ACUMULADOS.xlsx")


def main() -> None:
    inicio = date(2026, 8, 1)
    fin_exclusivo = date(2026, 8, 5)
    df_turno = fetch_reporte_turno_cache_emision(inicio, fin_exclusivo)
    df_generador = fetch_generador_reporte_diario_emision(inicio, fin_exclusivo)
    if df_turno.empty or df_generador.empty:
        raise RuntimeError(
            f"Fuentes vacías: turno={len(df_turno)}, generador={len(df_generador)}"
        )

    buffer = io.BytesIO()
    export_reporte_turno_estilo_leyes_finos(
        df=df_turno,
        output=buffer,
        df_generador=df_generador,
        df_generador_resumen=df_generador,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(buffer.getvalue())

    wb = load_workbook(io.BytesIO(buffer.getvalue()), data_only=True)
    ws = wb["Generador Reporte"]
    print(f"archivo={OUTPUT.resolve()}")
    print(f"turno={len(df_turno)} generador={len(df_generador)} semana={ws['V5'].value}")
    for row in range(6, 17):
        print(
            f"{ws.cell(row, 22).value}: "
            f"sem_real={ws.cell(row, 28).value!r} "
            f"sem_programa={ws.cell(row, 29).value!r} "
            f"mes_real={ws.cell(row, 30).value!r} "
            f"mes_plan={ws.cell(row, 31).value!r}"
        )


if __name__ == "__main__":
    main()
