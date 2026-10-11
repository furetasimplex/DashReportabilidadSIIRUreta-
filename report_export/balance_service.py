"""Servicio de Balance oficial y acumulado MTD, sin escrituras en BD."""

from datetime import timedelta

import pandas as pd

from report_export.report_export import (
    BalanceReportError,
    fetch_recon_balance_mtd_candidates,
    fetch_recon_balance_official_case,
    validate_recon_balance_result,
)


_FLOW_FIELDS = (
    "codigo_flujo",
    "tolerancia_masa",
    "tolerancia_ley",
    "masa_medida",
    "masa_reconciliada",
    "ley_cu_medida",
    "ley_cu_reconciliada",
    "fino_cu_medido",
    "fino_cu_reconciliado",
)


class BalanceMtdUnavailableError(BalanceReportError):
    """Cobertura MTD esperadamente no construible para el Caso elegido."""


def _date(value, label):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise BalanceReportError(f"{label} no es una fecha valida.")
    return parsed.date()


def _candidate_cases(raw_candidates):
    if raw_candidates is None or raw_candidates.empty:
        return []
    required = {
        "caso_id", "fecha_inicio", "fecha_fin", "modelo_id",
        "solver_run_id", "estado_run", *_FLOW_FIELDS,
    }
    missing = sorted(required - set(raw_candidates.columns))
    if missing:
        raise BalanceReportError(
            "La consulta MTD no devolvio columnas requeridas: "
            + ", ".join(missing)
            + "."
        )

    runs_by_case = raw_candidates.groupby("caso_id")["solver_run_id"].nunique()
    ambiguous = sorted(int(value) for value in runs_by_case[runs_by_case != 1].index)
    if ambiguous:
        raise BalanceReportError(
            "Casos con oficialidad ambigua: "
            + ", ".join(map(str, ambiguous))
            + "."
        )

    cases = []
    for (case_id, run_id), group in raw_candidates.groupby(
        ["caso_id", "solver_run_id"], sort=False
    ):
        first = group.iloc[0]
        metadata = {
            "caso_id": int(case_id),
            "solver_run_id": int(run_id),
            "run_id": int(run_id),
            "nombre_caso": first.get("nombre_caso"),
            "fecha_inicio": first["fecha_inicio"],
            "fecha_fin": first["fecha_fin"],
            "modelo_id": first["modelo_id"],
            "estado_run": first["estado_run"],
            "solver_name": first.get("solver_name"),
            "solver_version": first.get("solver_version"),
            "oficializado_en": first.get("oficializado_en"),
            "es_oficial": True,
        }
        flows = group.loc[:, _FLOW_FIELDS].copy()
        validated = validate_recon_balance_result(
            flows, metadata, f"El Run oficial {int(run_id)}"
        )
        cases.append({
            "metadata": metadata,
            "flows": validated,
            "fecha_inicio": _date(first["fecha_inicio"], "fecha_inicio"),
            "fecha_fin": _date(first["fecha_fin"], "fecha_fin"),
        })
    return cases


def validate_balance_mtd_coverage(cases, mtd_start, mtd_end, selected_key):
    """Construye una cadena inclusiva continua, anclada en el Caso elegido."""
    if not cases:
        raise BalanceMtdUnavailableError(
            "No existen Casos oficiales para construir el acumulado MTD."
        )

    selected = [
        item for item in cases
        if (
            int(item["metadata"]["caso_id"]),
            int(item["metadata"]["solver_run_id"]),
        ) == selected_key
    ]
    if len(selected) != 1:
        raise BalanceReportError(
            "El Caso seleccionado y su Run oficial no aparecen de forma "
            "univoca entre los candidatos MTD."
        )
    current = selected[0]
    if current["fecha_fin"] != mtd_end:
        raise BalanceReportError(
            "La fecha_fin del candidato seleccionado no coincide con el Caso."
        )
    chain_reversed = [current]
    used = {selected_key}
    while current["fecha_inicio"] > mtd_start:
        required_end = current["fecha_inicio"] - timedelta(days=1)
        predecessors = [
            item for item in cases
            if item["fecha_fin"] == required_end
            and item["fecha_inicio"] >= mtd_start
            and (
                int(item["metadata"]["caso_id"]),
                int(item["metadata"]["solver_run_id"]),
            ) not in used
        ]
        if not predecessors:
            overlaps = sorted(
                (
                    item for item in cases
                    if item["fecha_inicio"] < current["fecha_inicio"]
                    and item["fecha_fin"] >= current["fecha_inicio"]
                ),
                key=lambda item: item["metadata"]["caso_id"],
            )
            context = ""
            if overlaps:
                nearby = overlaps[0]
                context = (
                    f" El Caso {nearby['metadata']['caso_id']} termina "
                    f"{nearby['fecha_fin']:%d-%m-%Y}, pero para preceder al "
                    f"Caso {current['metadata']['caso_id']} deberia terminar "
                    f"{required_end:%d-%m-%Y}."
                )
            raise BalanceMtdUnavailableError(
                "No existe una cobertura oficial MTD continua y sin "
                "solapamientos desde el inicio del mes hasta el Caso "
                "seleccionado." + context
            )
        if len(predecessors) > 1:
            ids = ", ".join(
                str(item["metadata"]["caso_id"])
                for item in sorted(
                    predecessors, key=lambda item: item["metadata"]["caso_id"]
                )
            )
            raise BalanceReportError(
                "La cobertura oficial MTD es ambigua: los Casos "
                f"{ids} son predecesores exactos del Caso "
                f"{current['metadata']['caso_id']}."
            )
        current = predecessors[0]
        current_key = (
            int(current["metadata"]["caso_id"]),
            int(current["metadata"]["solver_run_id"]),
        )
        used.add(current_key)
        chain_reversed.append(current)
    if current["fecha_inicio"] != mtd_start:
        raise BalanceMtdUnavailableError(
            "No existe una cobertura oficial MTD continua y sin "
            "solapamientos desde el inicio del mes hasta el Caso seleccionado."
        )
    return list(reversed(chain_reversed))


def aggregate_balance_mtd(cases):
    """Suma masa/fino por Flow ID y calcula ley ponderada."""
    rows = []
    for number in range(1, 121):
        code = f"F{number}"
        mass_total = None
        fine_total = None
        for item in cases:
            mass = item["flows"].loc[code, "masa_reconciliada"]
            fine = item["flows"].loc[code, "fino_cu_reconciliado"]
            if pd.isna(mass) or pd.isna(fine):
                raise BalanceReportError(
                    f"El acumulado MTD contiene masa o fino NULL para {code}."
                )
            mass_total = mass if mass_total is None else mass_total + mass
            fine_total = fine if fine_total is None else fine_total + fine
        grade = None if mass_total == 0 else (fine_total / mass_total) * 100
        rows.append({
            "codigo_flujo": code,
            "masa_reconciliada_acumulada": mass_total,
            "ley_cu_reconciliada_acumulada": grade,
            "fino_cu_reconciliado_acumulado": fine_total,
        })
    return pd.DataFrame(rows).set_index("codigo_flujo", drop=False)


def _resolve_balance_mtd_cases(period, metadata, fetch_candidates):
    start = _date(metadata.get("fecha_inicio"), "fecha_inicio")
    end = _date(metadata.get("fecha_fin"), "fecha_fin")
    if start.year != end.year or start.month != end.month:
        raise BalanceReportError(
            "El Caso seleccionado cruza meses y no puede utilizarse para "
            "construir un acumulado MTD con resultados agregados por Caso."
        )
    run_id = int(metadata["solver_run_id"])
    mtd_start = end.replace(day=1)
    selected_case = {
        "metadata": metadata,
        "flows": period,
        "fecha_inicio": start,
        "fecha_fin": end,
    }
    if start == mtd_start:
        ordered = [selected_case]
    else:
        raw_candidates = fetch_candidates(metadata["modelo_id"], mtd_start, end)
        cases = _candidate_cases(raw_candidates)
        ordered = validate_balance_mtd_coverage(
            cases,
            mtd_start,
            end,
            (int(metadata["caso_id"]), run_id),
        )
    return ordered, start, end, mtd_start, run_id


def get_balance_case_status(
    caso_id,
    fetch_case=fetch_recon_balance_official_case,
    fetch_candidates=fetch_recon_balance_mtd_candidates,
):
    """Devuelve estado operacional read-only sin generar el workbook."""
    period, metadata = fetch_case(caso_id)
    start = _date(metadata.get("fecha_inicio"), "fecha_inicio")
    end = _date(metadata.get("fecha_fin"), "fecha_fin")
    run_id = int(metadata["solver_run_id"])
    result = {
        "caso_id": int(metadata["caso_id"]),
        "nombre_caso": metadata.get("nombre_caso"),
        "fecha_inicio": start,
        "fecha_fin": end,
        "solver_run_id": run_id,
        "estado_run": metadata.get("estado_run"),
        "oficial": bool(metadata.get("es_oficial", True)),
        "mtd_disponible": False,
        "mtd_fecha_inicio": end.replace(day=1),
        "mtd_fecha_fin": end,
        "mtd_casos": [],
        "mensaje_mtd": None,
    }
    try:
        ordered, _, _, mtd_start, _ = _resolve_balance_mtd_cases(
            period, metadata, fetch_candidates
        )
    except BalanceMtdUnavailableError as exc:
        result["mensaje_mtd"] = str(exc)
        return result
    result.update({
        "mtd_disponible": True,
        "mtd_fecha_inicio": mtd_start,
        "mtd_casos": [int(item["metadata"]["caso_id"]) for item in ordered],
    })
    return result


def build_balance_official_report(
    caso_id,
    fetch_case=fetch_recon_balance_official_case,
    fetch_candidates=fetch_recon_balance_mtd_candidates,
):
    """Prepara periodo, acumulado y metadata de un Caso oficial."""
    print(f"[BALANCE] caso seleccionado={caso_id}")
    period, metadata = fetch_case(caso_id)
    ordered, start, end, mtd_start, run_id = _resolve_balance_mtd_cases(
        period, metadata, fetch_candidates
    )
    print(f"[BALANCE] run oficial={run_id}")
    print(f"[BALANCE MTD] inicio={mtd_start} fin={end}")
    case_ids = [item["metadata"]["caso_id"] for item in ordered]
    run_ids = [item["metadata"]["solver_run_id"] for item in ordered]
    print(f"[BALANCE MTD] casos incluidos={case_ids}")
    print(f"[BALANCE MTD] runs oficiales={run_ids}")
    print("[BALANCE MTD] cobertura OK")
    accumulated = aggregate_balance_mtd(ordered)
    result_metadata = dict(metadata)
    result_metadata.update({
        "run_id": run_id,
        "es_oficial": True,
        "fecha_inicio_acumulado": mtd_start,
        "fecha_fin_acumulado": end,
        "casos_mtd": case_ids,
        "runs_mtd": run_ids,
    })
    return period, accumulated, result_metadata
