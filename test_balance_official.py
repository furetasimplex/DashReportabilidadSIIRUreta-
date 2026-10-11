"""Smoke manual de Fase 2 para listar o exportar un Caso oficial DEV."""

import argparse
from pathlib import Path

import pandas as pd

from report_export.balance_service import build_balance_official_report
from report_export.export_to_excel import export_balance_reconciliacion_to_template
from report_export.report_export import fetch_recon_balance_official_cases


TEMPLATE = Path("reporte/Template_Balance_Planta_Hidrometalurgia.xlsx")


def _list_cases():
    cases = fetch_recon_balance_official_cases()
    if cases.empty:
        print("No existen Casos oficializados disponibles.")
        return
    columns = [
        "caso_id", "fecha_inicio", "fecha_fin", "modelo_id",
        "solver_run_id", "estado_run",
    ]
    print(cases.loc[:, columns].drop_duplicates().to_string(index=False))


def _export(case_id):
    period, accumulated, metadata = build_balance_official_report(case_id)
    content = export_balance_reconciliacion_to_template(
        period, accumulated, metadata, str(TEMPLATE)
    )
    start = pd.to_datetime(metadata["fecha_inicio"]).date()
    end = pd.to_datetime(metadata["fecha_fin"]).date()
    run_id = int(metadata["solver_run_id"])
    output = Path(
        f"Balance_Oficial_Caso{case_id}_{start:%Y%m%d}_{end:%Y%m%d}_"
        f"Run{run_id}.xlsx"
    )
    output.write_bytes(content)
    print(f"caso_id: {case_id}")
    print(f"solver_run_id: {run_id}")
    print(f"periodo: {start} al {end}")
    print(
        "acumulado: "
        f"{metadata['fecha_inicio_acumulado']} al "
        f"{metadata['fecha_fin_acumulado']}"
    )
    print(f"casos_mtd: {metadata['casos_mtd']}")
    print(f"runs_mtd: {metadata['runs_mtd']}")
    print(f"ruta archivo: {output.resolve()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("caso_id", type=int, nargs="?")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        _list_cases()
    elif args.caso_id is not None:
        _export(args.caso_id)
    else:
        parser.error("indique caso_id o use --list")


if __name__ == "__main__":
    main()
