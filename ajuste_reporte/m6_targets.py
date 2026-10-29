"""Targets y prevalidacion M6 puros: sin conexiones ni persistencia."""
import json
import math
import uuid

import pandas as pd


class M6ValidationError(ValueError):
    def __init__(self, code, message, **details):
        self.code = code
        self.details = details
        super().__init__(f"{code}: {message}")


def _require(condition, code, message, **details):
    if not condition:
        raise M6ValidationError(code, message, **details)


def select_solver_model(context):
    """Identificadores actuales y legacy pertenecen a espacios distintos."""
    for field in ("caso_id", "modelo_id", "solver_run_id", "run_caso_id"):
        value = context.get(field)
        _require(isinstance(value, int) and not isinstance(value, bool) and value > 0,
                 "IDENTIFICADOR_INVALIDO", f"Se requiere {field} entero positivo.")
    _require(context["caso_id"] == context["run_caso_id"], "CASO_RUN_INCOHERENTE",
             "El run no pertenece al caso solicitado.")
    if context.get("modelo_codigo") == "hidrometalurgia_125_v2":
        _require(context.get("estado_run") == "success", "RUN_NO_DISPONIBLE",
                 "El run M6 debe tener resultados disponibles en estado success.")
        _require(context.get("legacy_modelo_id") == 6 and context.get("total_flujos") == 125,
                 "CONTRATO_MODELO_INVALIDO", "M6 requiere codigo125, legacy_modelo_id=6 y 125 flujos.")
        return "m6_125"
    if context.get("modelo_codigo") == "hidrometalurgia_120_completo" and context.get("total_flujos") == 120:
        return "legacy_120"
    raise M6ValidationError("MODELO_NO_SOPORTADO", "El caso/run no identifica un modelo compatible.")


def _numbers(frame, column, *, nonnegative=True, allow_zero_mass_null=None):
    _require(column in frame, "COLUMNA_AUSENTE", f"Falta {column}.")
    values = pd.to_numeric(frame[column], errors="coerce")
    allowed = (allow_zero_mass_null == 0) & frame[column].isna() if allow_zero_mass_null is not None else pd.Series(False, index=frame.index)
    bad = values.isna() & ~allowed
    _require(not bad.any(), "VALOR_AUSENTE", f"{column} contiene valores ausentes/no numericos.", filas=frame.index[bad].tolist())
    finite = values.dropna().map(math.isfinite)
    _require(finite.all(), "VALOR_NO_FINITO", f"{column} contiene valores no finitos.")
    if nonnegative:
        _require(not (values < 0).any(), "PERFIL_NEGATIVO", f"{column} no puede ser negativo.")
    return values


def build_targets_m6_125(results, catalog, context):
    """Constructor sin efectos: valida las 125 filas y conserva aliases de reglas."""
    _require(select_solver_model(context) == "m6_125", "MODELO_INCORRECTO", "Este constructor solo admite M6 de 125 flujos.")
    expected = {f"F{i}" for i in range(1, 126)}
    for frame, label in ((catalog, "catalogo"), (results, "resultados")):
        _require("codigo_flujo" in frame, "CODIGOS_AUSENTES", f"Faltan codigos en {label}.")
        _require(len(frame) == 125 and not frame.codigo_flujo.duplicated().any()
                 and set(frame.codigo_flujo) == expected,
                 "FLUJOS_INCOMPLETOS_DUPLICADOS", f"{label}: se requieren F1-F125 completos y unicos.",
                 faltantes=sorted(expected - set(frame.codigo_flujo)),
                 inesperados=sorted(str(v) for v in set(frame.codigo_flujo) - expected),
                 duplicados=frame.loc[frame.codigo_flujo.duplicated(), "codigo_flujo"].tolist())
    _require({"id", "modelo_id"}.issubset(catalog.columns), "CATALOGO_INCOMPLETO", "Faltan identificadores del catalogo.")
    _require(not catalog.id.isna().any() and not catalog.id.duplicated().any()
             and catalog.modelo_id.eq(context["modelo_id"]).all(),
             "CATALOGO_MODELO_INCORRECTO", "El catalogo no corresponde al modelo actual del caso.")
    if "activo" in catalog:
        _require(catalog.activo.eq(True).all(), "CATALOGO_INACTIVO", "El catalogo contiene flujos inactivos.")
    for field, value in (("caso_id", context["caso_id"]), ("run_id", context["solver_run_id"])):
        _require(field in results and results[field].eq(value).all(), "RESULTADOS_OTRO_CASO_RUN", f"Resultados con {field} incoherente.")
    _require("flujo_modelo_id" in results, "CLAVE_CATALOGO_AUSENTE", "Falta flujo_modelo_id en resultados.")
    ids = catalog.set_index("codigo_flujo")["id"]
    _require(results.flujo_modelo_id.eq(results.codigo_flujo.map(ids)).all(),
             "RESULTADO_CATALOGO_INCOHERENTE", "Las claves de los flujos no coinciden con el catalogo del caso.")
    # Inventarios no utilizados como targets pueden ser negativos; no se cambia su signo.
    validated = results.copy()
    for field in ("masa_reconciliada", "fino_cu_reconciliado"):
        validated[field] = _numbers(results, field, nonnegative=False)
    flows = validated.set_index("codigo_flujo")
    physical = ["F3", "F9", "F13", "F14", "F16", "F17", "F18", "F19", "F32", "F33", "F35", "F36"]
    for code in physical:
        mass, fine = (float(flows.loc[code, f]) for f in ("masa_reconciliada", "fino_cu_reconciliado"))
        _require(0 <= fine <= mass, "OBJETIVO_FISICO_INVALIDO", f"{code}: masa/fino incompatibles.", masa=mass, fino=fine)
    m = lambda *codes: float(flows.loc[list(codes), "masa_reconciliada"].sum())
    c = lambda *codes: float(flows.loc[list(codes), "fino_cu_reconciliado"].sum())
    return {
        "F3": m("F3"), "F10F11_MASA": m("F13", "F14"),
        "F08F09_MASA": m("F9"), "F08F09_FCU": c("F9"),
        "F08F09_LEY_CU": 100 * c("F9") / m("F9") if m("F9") else 0.0,
        "F14F15_MASA": m("F18", "F19"), "F14F15_FCU": c("F18", "F19"),
        "F19__MASA": m("F32"), "F18__MASA": m("F35"),
        "F22__MASA": m("F33"), "F21__MASA": m("F36"),
    }


def _close(value, target, label):
    # Precision computacional, no tolerancia de reconciliacion ni de negocio.
    _require(math.isfinite(value) and math.isclose(value, target, rel_tol=1e-12, abs_tol=1e-8),
             "NO_CONSERVA_TARGET", f"{label}: distribuido={value}, objetivo={target}.",
             indicador=label, distribuido=value, objetivo=target)


def prepare_m6_125(results, catalog, context, daily, rules, *, apply_rules,
                   require_pad_distribution=False, adjustment_run_id=None):
    """Ensayo agregado validado, nunca publicable/persistente en esta etapa."""
    targets = build_targets_m6_125(results, catalog, context)
    diagnostics = []
    _require("Fecha" in daily and not daily.empty, "PERFIL_VACIO", "Se requieren fechas diarias.")
    dates = pd.to_datetime(daily.Fecha, errors="coerce")
    start = pd.to_datetime(context.get("fecha_inicio"), errors="coerce")
    end = pd.to_datetime(context.get("fecha_fin"), errors="coerce")
    _require(pd.notna(start) and pd.notna(end) and start <= end, "PERIODO_INVALIDO", "Periodo del caso invalido.")
    _require(not dates.isna().any() and not dates.dt.normalize().duplicated().any(),
             "FECHAS_INVALIDAS_DUPLICADAS", "Fechas ausentes o repetidas; no se agrupan automaticamente.")
    actual_dates = set(dates.dt.normalize())
    expected_dates = set(pd.date_range(start.normalize(), end.normalize()))
    _require(actual_dates == expected_dates, "COBERTURA_INCOMPLETA", "Faltan fechas del caso o existen fechas fuera del periodo.",
             faltantes=[str(v.date()) for v in sorted(expected_dates - actual_dates)],
             fuera_periodo=[str(v.date()) for v in sorted(actual_dates - expected_dates)])
    _require(not rules.empty and {"regla_id", "orden_calculo", "tipo_regla", "col_nombre"}.issubset(rules.columns),
             "REGLAS_AUSENTES", "Se requiere la configuracion de reglas vigente.")
    _require(rules.index.is_unique and not rules.regla_id.duplicated().any()
             and rules.regla_id.tolist() == rules.sort_values(["orden_calculo", "regla_id"]).regla_id.tolist(),
             "ORDEN_REGLAS_INVALIDO", "Las reglas deben conservar orden_calculo,regla_id sin duplicados.")
    _require(not require_pad_distribution, "DETALLE_PAD_NO_DISPONIBLE",
             "El contrato diario vigente no contiene un reparto por PAD validado. Puede prepararse la salida agregada.")
    out = daily.copy()
    configured = rules.copy()
    if "params" not in configured:
        configured["params"] = configured.get("params_json", pd.Series(None, index=configured.index)).map(lambda v: json.loads(v) if pd.notna(v) and v else {})
    factors, adjusted = {}, set()
    supported = {"NO_CAMBIA", "SCALE_TO_TARGET", "PAIR_SCALE_TO_TARGET", "DERIVED", "DERIVED_SAFE_RATIO", "PROPORTIONAL_SPLIT", "SCALE_FINOS_AND_RECALC_GRADE"}
    allowed_adjusted = {
        "Chancado_TMS_Real", "Sal_turno_A", "Sal_Turno_B", "Sal_promedio_dia",
        "SRR_TMS_Turno_A", "SRR_TMS_Turno_B", "SRR_TMS_promedio_dia", "Ley_CuT_Real_srr",
        "Apilado_TMS_Real", "Apilado_TMH_promedio_dia", "Apilado_TMH_turno_A", "Apilado_TMH_turno_B",
        "Cobre_fino_Apilado_Real", "Ley_CuT_Real", "TMS_Rotopala_1_Real", "TMS_Rotopala_2_Real",
        "Camiones_TMS_Reclamo_Oxidos", "Camiones_TMS_Reclamo_Sulfuros", "Total_Ripios_Incluye_Camiones_Real",
    }
    for idx, rule in configured.iterrows():
        kind, col, params = rule["tipo_regla"], rule["col_nombre"], rule["params"] or {}
        _require(kind in supported, "REGLA_M6_NO_VALIDADA", f"Tipo de regla M6 no validado: {kind}.")
        target_code = rule.get("target_code")
        target = targets.get(target_code)
        if kind in {"SCALE_TO_TARGET", "PAIR_SCALE_TO_TARGET", "SCALE_FINOS_AND_RECALC_GRADE"}:
            _require(target is not None and math.isfinite(target), "TARGET_AUSENTE", f"Falta {target_code} para {col}.")
        if kind == "SCALE_TO_TARGET":
            base = _numbers(out, col)
            _require(not (target > 0 and base.sum() <= 0), "TARGET_SIN_BASE", f"{col}: target positivo sin perfil distribuible.")
        elif kind == "PAIR_SCALE_TO_TARGET":
            a, b = (_numbers(out, params[key]) for key in ("a_col", "b_col"))
            _require((a + b).sum() > 0, "PAREJA_SIN_BASE", f"{col}: no existen ponderadores A/B para la regla vigente.")
        elif kind == "PROPORTIONAL_SPLIT":
            total = _numbers(out, params["total_col"])
            a, b = (_numbers(out, params[key]) for key in ("a_col", "b_col"))
            _require(not ((total > 0) & ((a + b) <= 0)).any(), "TURNOS_NO_DISTRIBUIBLES",
                     f"{col}: hay tonelaje diario sin ponderadores A/B validos.")
        elif kind == "SCALE_FINOS_AND_RECALC_GRADE":
            mass = _numbers(out, params["masa_col"])
            _require(mass.sum() > 0, "MASA_SRR_CERO", "La regla de ley SRR vigente requiere masa positiva.")
            grade = _numbers(out, params["ley_base_col"], allow_zero_mass_null=mass)
            _require(not (grade > 100).any(), "LEY_INVALIDA", "Ley SRR superior a 100%.")
            if grade.isna().any():
                diagnostics.append(dict(codigo="LEY_NULL_SIN_MASA", columna=params["ley_base_col"], filas=out.index[grade.isna()].tolist(), tratamiento="Regla vigente aplica fill=0; no se infiere ley con masa positiva."))
            if (mass * grade.fillna(0)).sum() <= 0:
                diagnostics.append(dict(codigo="FINOS_BASE_CERO", tratamiento="La regla vigente utiliza ponderadores de masa."))
        elif kind == "DERIVED" and col == "Apilado_TMH_promedio_dia":
            humidity = _numbers(out, "Humedad_promedio_dia")
            _require((humidity <= 100).all(), "HUMEDAD_INVALIDA", "Humedad fuera de [0,100].")
        elif kind == "DERIVED_SAFE_RATIO":
            numerator, denominator = (_numbers(out, params[key]) for key in ("num", "den"))
            _require(not ((denominator == 0) & (numerator != 0)).any(), "FINO_SIN_MASA",
                     f"{col}: el ratio no puede ocultar fino positivo con masa cero.")
        outputs = [params["a_col"], params["b_col"]] if kind in {"PAIR_SCALE_TO_TARGET", "PROPORTIONAL_SPLIT"} else [col]
        if kind != "NO_CAMBIA":
            _require(set(outputs).issubset(allowed_adjusted), "HEREDADA_NO_AUTORIZADA", "Una regla intenta recalcular una columna heredada no autorizada.")
            adjusted.update(outputs)
        try:
            # Mismos cuerpos numericos y mismo orden; validacion antes de cada paso.
            out, step_factors = apply_rules(out, configured.loc[[idx]], targets)
        except Exception as exc:
            raise M6ValidationError("ERROR_REPARTO", f"Regla {rule['regla_id']} ({col}): {exc}") from exc
        factors.update(step_factors)
        if kind != "NO_CAMBIA":
            for output in outputs:
                values = _numbers(out, output)
                if output.startswith("Ley_CuT"):
                    _require((values <= 100).all(), "LEY_INVALIDA", f"{output}: ley superior a 100%.")
    _require(len(out) == len(daily) and out.Fecha.equals(daily.Fecha), "FECHAS_ALTERADAS", "El reparto altero las filas/fechas.")
    technical = {"Fecha", "dc_id", "estado", "run_id", "caso_id", "version_reglas", "ts_ajuste", "factor_chancado", "factor_sal", "factor_finos"}
    inherited = [c for c in daily if c not in adjusted and c not in technical]
    for col in daily:
        if col not in adjusted:
            _require(out[col].equals(daily[col]), "HEREDADA_ALTERADA", f"Se modifico la columna heredada {col}.")
            if daily[col].isna().any():
                diagnostics.append(dict(codigo="NULL_HEREDADO_CONSERVADO", columna=col, cantidad=int(daily[col].isna().sum())))
    _require(adjusted == allowed_adjusted, "REGLA_REQUERIDA_AUSENTE", "No se prepararon las 19 columnas ajustadas del contrato M6.")
    sums = {c: float(_numbers(out, c).sum()) for c in adjusted}
    checks = {
        "Chancado_TMS_Real": targets["F3"], "Sal_promedio_dia": targets["F10F11_MASA"],
        "SRR_TMS_promedio_dia": targets["F08F09_MASA"], "Apilado_TMS_Real": targets["F14F15_MASA"],
        "Cobre_fino_Apilado_Real": targets["F14F15_FCU"], "TMS_Rotopala_1_Real": targets["F19__MASA"],
        "TMS_Rotopala_2_Real": targets["F18__MASA"], "Camiones_TMS_Reclamo_Oxidos": targets["F22__MASA"],
        "Camiones_TMS_Reclamo_Sulfuros": targets["F21__MASA"],
    }
    for col, target in checks.items():
        _require(col in sums, "REGLA_REQUERIDA_AUSENTE", f"No se preparo {col}.")
        _close(sums[col], target, col)
    _close(sums["Sal_turno_A"] + sums["Sal_Turno_B"], targets["F10F11_MASA"], "Sal A+B")
    _close(sums["SRR_TMS_Turno_A"] + sums["SRR_TMS_Turno_B"], targets["F08F09_MASA"], "SRR A+B")
    _close(sums["Apilado_TMH_turno_A"] + sums["Apilado_TMH_turno_B"], sums["Apilado_TMH_promedio_dia"], "Apilado TMH A+B")
    for mass, grade, fine, target in (
        ("SRR_TMS_promedio_dia", "Ley_CuT_Real_srr", "CuT_fino_srr_adj", targets["F08F09_FCU"]),
        ("Apilado_TMS_Real", "Ley_CuT_Real", "Cobre_fino_Apilado_Real", targets["F14F15_FCU"]),
    ):
        q, l, cu = (_numbers(out, c) for c in (mass, grade, fine))
        _require(not (l > 100).any() and not ((q == 0) & (cu != 0)).any(), "FINO_SIN_MASA", f"{fine}: masa/ley/fino incompatibles.")
        reconstructed = q * l / 100
        for value, expected in zip(reconstructed, cu):
            _close(float(value), float(expected), fine + " diario")
        _close(float(reconstructed.sum()), target, fine + " periodo")
    flows = results.copy().set_index("codigo_flujo")
    for field in ("masa_reconciliada", "fino_cu_reconciliado"):
        flows[field] = pd.to_numeric(flows[field])
    gross = float(flows.loc[["F16", "F17"], "masa_reconciliada"].sum())
    gross_cu = float(flows.loc[["F16", "F17"], "fino_cu_reconciliado"].sum())
    diagnostics.append(dict(codigo="CONTRASTE_BRUTO_ASIGNADO", masa_F16_F17=gross, masa_F18_F19=targets["F14F15_MASA"],
                            diferencia_masa=targets["F14F15_MASA"] - gross, diferencia_fino=targets["F14F15_FCU"] - gross_cu,
                            estado="REVISION_FISICA; no se fuerza igualdad"))
    diagnostics.append(dict(codigo="DETALLE_PAD_NO_VERIFICABLE", ambos_PAD_con_target_positivo=bool(flows.loc["F18", "masa_reconciliada"] > 0 and flows.loc["F19", "masa_reconciliada"] > 0),
                            alcance="Solo totales agregados; no se inventa distribucion diaria por PAD."))
    if "Camiones_TMS_total" in out:
        delta = pd.to_numeric(out.Camiones_TMS_total, errors="coerce") - out.Camiones_TMS_Reclamo_Oxidos - out.Camiones_TMS_Reclamo_Sulfuros
        if delta.abs().gt(1e-8).any():
            diagnostics.append(dict(codigo="TOTAL_HEREDADO_INCOMPATIBLE", columna="Camiones_TMS_total", diferencias_por_fecha=[dict(Fecha=str(date), diferencia=float(diff)) for date, diff in zip(out.Fecha, delta) if abs(diff) > 1e-8]))
    if adjustment_run_id is None:
        adjustment_run_id = uuid.uuid4()
    try:
        adjustment_run_id = uuid.UUID(str(adjustment_run_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise M6ValidationError("UUID_AJUSTE_INVALIDO", "run_id del ajuste debe ser UUID, distinto del solver_run_id entero.") from exc
    return dict(ok=True, modo="prueba_sin_persistencia", persistido=False, publicable=False,
                caso_id=context["caso_id"], modelo_id=context["modelo_id"], legacy_modelo_id=context["legacy_modelo_id"],
                solver_run_id=context["solver_run_id"], run_id=str(adjustment_run_id),
                targets=targets, factores=factors, datos=out, diagnosticos=diagnostics,
                columnas_ajustadas=sorted(adjusted), columnas_heredadas=inherited)
