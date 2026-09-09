# ajuste_reporte/rep_prod_adjuster.py
import json
import uuid
import datetime as dt
from typing import Dict, Any, Tuple, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from db_connection import get_engine


# ============================================================
# Helpers SQLAlchemy 2.x
# ============================================================
def exec_sql(engine: Engine, sql: str, params: dict | None = None) -> None:
    """Ejecuta SQL/SP (no retorna dataset) compatible con SQLAlchemy 2.x."""
    if engine is None:
        raise RuntimeError("Engine is None (revisa db_connection.get_engine())")
    params = params or {}
    with engine.begin() as conn:
        conn.execute(text(sql), params)


def read_sql_df(engine: Engine, sql: str, params: dict | None = None) -> pd.DataFrame:
    """Lee DataFrame usando conexión explícita (SQLAlchemy 2.x)."""
    if engine is None:
        raise RuntimeError("Engine is None (revisa db_connection.get_engine())")
    params = params or {}
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def get_table_columns(engine: Engine, schema: str, table: str) -> list[str]:
    """Devuelve columnas existentes en una tabla (para filtrar insert)."""
    dfc = read_sql_df(
        engine,
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :s AND TABLE_NAME = :t
        ORDER BY ORDINAL_POSITION
        """,
        {"s": schema, "t": table},
    )
    return dfc["COLUMN_NAME"].tolist() if not dfc.empty else []


# ============================================================
# SPs / Lecturas base
# ============================================================
def sp_get_periodo_caso(engine: Engine, caso_id: int) -> Tuple[pd.Timestamp, pd.Timestamp]:
    df = read_sql_df(
        engine,
        "EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id=:caso_id",
        {"caso_id": caso_id},
    )
    if df.empty:
        raise ValueError(f"No existe periodo para caso_id={caso_id} (sp_rep_get_periodo_caso vacío)")
    return pd.to_datetime(df.loc[0, "fecha_inicio"]), pd.to_datetime(df.loc[0, "fecha_fin"])


def sp_build_targets(engine: Engine, caso_id: int) -> Dict[str, float]:
    # Construye/persist targets en BD
    exec_sql(engine, "EXEC inventar_SpcHidr.sp_rep_build_targets_caso @caso_id=:caso_id", {"caso_id": caso_id})

    # Lee targets
    df = read_sql_df(
        engine,
        """
        SELECT target_code, target_value
        FROM inventar_SpcHidr.rep_prod_targets
        WHERE caso_id = :caso_id
        """,
        {"caso_id": caso_id},
    )
    if df.empty:
        raise ValueError(f"No hay targets en rep_prod_targets para caso_id={caso_id}. Revisa SP build_targets.")
    return dict(zip(df["target_code"], df["target_value"]))


def load_reglas(engine: Engine) -> pd.DataFrame:
    df = read_sql_df(
        engine,
        """
        SELECT regla_id, col_nombre, orden_calculo, tipo_regla, target_code, formula_py, depende_de, params_json
        FROM inventar_SpcHidr.rep_prod_reglas
        WHERE activo = 1 AND reporte_nombre = 'reporte_prod'
        ORDER BY orden_calculo ASC, regla_id ASC
        """,
    )

    def _parse(x):
        if x is None or str(x).strip() == "":
            return {}
        return json.loads(x)

    df["params"] = df["params_json"].apply(_parse)
    return df


def load_query1_all_cols(engine: Engine, fecha_ini: pd.Timestamp, fecha_fin: pd.Timestamp) -> pd.DataFrame:
    # 1) lista columnas (en orden de posición)
    cols_df = read_sql_df(
        engine,
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'inventar_SpcHidr'
          AND TABLE_NAME = 'Datos_conciliados_of'
        ORDER BY ORDINAL_POSITION
        """
    )
    cols = cols_df["COLUMN_NAME"].tolist()
    if not cols:
        raise ValueError("No se pudieron leer columnas de Datos_conciliados_of")

    # 2) arma SELECT con todas las columnas
    col_sql = ", ".join([f"[{c}]" for c in cols])

    df = read_sql_df(
        engine,
        f"""
        SELECT {col_sql}
        FROM inventar_SpcHidr.Datos_conciliados_of
        WHERE [Fecha] BETWEEN :ini AND :fin
        ORDER BY [Fecha] ASC
        """,
        {"ini": pd.to_datetime(fecha_ini).date(), "fin": pd.to_datetime(fecha_fin).date()},
    )

    # Normaliza Fecha
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date

    return df


# ============================================================
# Motor de reglas (extensible)
# ============================================================
def safe_scale_series(s: pd.Series, target_total: float) -> tuple[pd.Series, float]:
    total = float(s.fillna(0).sum())
    if total == 0:
        return s.copy(), 1.0
    factor = float(target_total) / total
    return s * factor, factor


def apply_rules(
    df: pd.DataFrame,
    reglas: pd.DataFrame,
    targets: Dict[str, float]
) -> tuple[pd.DataFrame, Dict[str, float]]:
    """
    Tipos soportados:
      - NO_CAMBIA
      - SCALE_TO_TARGET
      - SET_FROM_TARGET
      - PAIR_SCALE_TO_TARGET (params_json: a_col, b_col)
      - DERIVED (formula pandas en formula_py)
      - DERIVED_SAFE_RATIO (params_json: num, den, scale, fill)
      - PROPORTIONAL_SPLIT (params_json: a_col, b_col, total_col)
    """
    out = df.copy()
    factors: Dict[str, float] = {}

    def _eval_expr(expr: str) -> pd.Series:
        local = {c: out[c] for c in out.columns if c in out}
        return eval(expr, {"__builtins__": {}}, local)

    for _, r in reglas.iterrows():
        col = r["col_nombre"]
        rule = r["tipo_regla"]
        target_code = r.get("target_code", None)
        formula_py = r.get("formula_py", None)
        params = r.get("params", {}) or {}

        if rule == "NO_CAMBIA":
            continue

        if rule == "SCALE_TO_TARGET":
            if not target_code or target_code not in targets:
                raise ValueError(f"Target faltante: {target_code} para col={col}")
            if col not in out.columns:
                raise ValueError(f"Columna no existe en datos para SCALE_TO_TARGET: {col}")

            out[col], f = safe_scale_series(out[col].fillna(0.0), targets[target_code])
            factors[f"factor_{col}"] = f
            continue

        if rule == "SET_FROM_TARGET":
            if not target_code or target_code not in targets:
                raise ValueError(f"Target faltante: {target_code} para col={col}")
            # Setea valor constante (mismo valor en todas las filas del periodo)
            out[col] = float(targets[target_code])
            continue

        if rule == "PAIR_SCALE_TO_TARGET":
            if not target_code or target_code not in targets:
                raise ValueError(f"Target faltante: {target_code}")

            a_col = params["a_col"]
            b_col = params["b_col"]

            if a_col not in out.columns or b_col not in out.columns:
                raise ValueError(f"Columnas no existen para PAIR_SCALE_TO_TARGET: {a_col}, {b_col}")

            a = out[a_col].fillna(0.0)
            b = out[b_col].fillna(0.0)

            total_actual = float((a + b).sum())
            if total_actual == 0:
                raise ValueError(f"Total actual 0 para {a_col}+{b_col}; no se puede escalar a {target_code}")

            f = float(targets[target_code]) / total_actual
            out[a_col] = a * f
            out[b_col] = b * f

            factors[f"factor_{a_col}_{b_col}"] = f
            continue

        if rule == "DERIVED":
            if not formula_py:
                raise ValueError(f"DERIVED sin formula_py para col={col}")
            out[col] = _eval_expr(formula_py)
            continue

        if rule == "DERIVED_SAFE_RATIO":
            num = params["num"]
            den = params["den"]
            scale = float(params.get("scale", 1.0))
            fill = params.get("fill", None)

            if num not in out.columns or den not in out.columns:
                raise ValueError(f"Columnas no existen para DERIVED_SAFE_RATIO: {num}, {den}")

            den_s = out[den].fillna(0.0)
            num_s = out[num].fillna(0.0)

            ratio = (num_s / den_s.replace({0.0: pd.NA})) * scale
            if fill is not None:
                ratio = ratio.fillna(float(fill))

            out[col] = ratio
            continue

        if rule == "PROPORTIONAL_SPLIT":
            a_col = params["a_col"]
            b_col = params["b_col"]
            total_col = params["total_col"]

            if a_col not in out.columns or b_col not in out.columns or total_col not in out.columns:
                raise ValueError(f"Columnas no existen para PROPORTIONAL_SPLIT: {a_col}, {b_col}, {total_col}")

            base_sum = out[a_col].fillna(0) + out[b_col].fillna(0)
            prop_a = (out[a_col].fillna(0) / base_sum.replace({0: pd.NA}))
            prop_b = (out[b_col].fillna(0) / base_sum.replace({0: pd.NA}))

            out[a_col] = (out[total_col] * prop_a).fillna(0)
            out[b_col] = (out[total_col] * prop_b).fillna(0)
            continue
        if rule == "GRADE_FROM_TARGET_AND_WEIGHTS":
            if not target_code or target_code not in targets:
                raise ValueError(f"Target faltante: {target_code} para col={col}")

            masa_col = params["masa_col"]
            weight_col = params["weight_col"]
            finos_col = params.get("finos_col", None)
            scale = float(params.get("scale", 100.0))
            fill = params.get("fill", None)

            if masa_col not in out.columns:
                raise ValueError(f"Columna masa_col no existe: {masa_col}")
            if weight_col not in out.columns:
                raise ValueError(f"Columna weight_col no existe: {weight_col}")

            masa = out[masa_col].fillna(0.0).astype(float)
            w = out[weight_col].fillna(0.0).astype(float).clip(lower=0.0)

            masa_total = float(masa.sum())
            if masa_total <= 0:
                raise ValueError(f"Masa total 0 para {masa_col}; no se puede aplicar {rule}")

            ley_target = float(targets[target_code])  # % (si scale=100)
            finos_total_obj = (ley_target / scale) * masa_total

            w_sum = float(w.sum())
            if w_sum <= 0:
                # fallback: si no hay pesos, usa masa como distribución
                w = masa.copy()
                w_sum = float(w.sum())
                if w_sum <= 0:
                    raise ValueError(f"No hay pesos ni masa positiva para distribuir (weight_col={weight_col})")

            finos_i = finos_total_obj * (w / w_sum)

            # ley diaria = finos/masa
            ley_i = (finos_i / masa.replace({0.0: pd.NA})) * scale
            if fill is not None:
                ley_i = ley_i.fillna(float(fill))

            out[col] = ley_i

            if finos_col:
                out[finos_col] = finos_i

            factors[f"check_{col}_ley_target"] = ley_target
            continue
        if rule == "SCALE_FINOS_AND_RECALC_GRADE":
            # params_json:
            #  - masa_col: "SRR_TMS_promedio_dia"
            #  - ley_base_col: "Ley_CuT_Real_srr"   (distribución base)
            #  - finos_out_col: "CuT_fino_srr_adj"  (opcional)
            #  - scale: 100
            #  - fill: 0 (opcional)
            if not target_code or target_code not in targets:
                raise ValueError(f"Target faltante: {target_code} para col={col}")

            masa_col = params["masa_col"]
            ley_base_col = params["ley_base_col"]
            finos_out_col = params.get("finos_out_col", None)
            scale = float(params.get("scale", 100.0))
            fill = params.get("fill", None)

            if masa_col not in out.columns:
                raise ValueError(f"Columna masa_col no existe: {masa_col}")
            if ley_base_col not in out.columns:
                raise ValueError(f"Columna ley_base_col no existe: {ley_base_col}")

            masa = out[masa_col].fillna(0.0).astype(float)
            ley_base = out[ley_base_col].fillna(0.0).astype(float)

            masa_total = float(masa.sum())
            if masa_total <= 0:
                raise ValueError(f"Masa total 0 para {masa_col}; no se puede aplicar {rule}")

            # Fino total objetivo desde ley target (asume target en % si scale=100)
            ley_target = float(targets[target_code])
            finos_total_obj = (ley_target / scale) * masa_total

            # Fino base diario (distribución)
            finos_base = masa * (ley_base / scale)
            finos_base_sum = float(finos_base.sum())

            if finos_base_sum <= 0:
                # fallback: si la distribución base da cero, reparte por masa
                # (equivale a ley constante)
                finos_base = masa.copy()
                finos_base_sum = float(finos_base.sum())
                if finos_base_sum <= 0:
                    raise ValueError("No hay finos_base ni masa positiva para distribuir.")

            k = finos_total_obj / finos_base_sum
            finos_adj = finos_base * k

            ley_adj = (finos_adj / masa.replace({0.0: pd.NA})) * scale
            if fill is not None:
                ley_adj = ley_adj.fillna(float(fill))

            # col = columna a recalcular (normalmente Ley_CuT_Real_srr)
            out[col] = ley_adj

            if finos_out_col:
                out[finos_out_col] = finos_adj

            factors[f"factor_finos_{col}"] = float(k)
            continue

        raise ValueError(f"tipo_regla no soportado: {rule}")

    return out, factors


# ============================================================
# Persistencia (staging -> merge SP)
# ============================================================
def write_staging(
    engine: Engine,
    df_adj: pd.DataFrame,
    run_id: uuid.UUID,
    caso_id: int,
    version_reglas: int,
    ts_ajuste: dt.datetime,
    factor_chancado: Optional[float] = None,
    factor_sal: Optional[float] = None,
    factor_finos: Optional[float] = None,
) -> None:
    """
    Inserta en staging SOLO columnas que existan en la tabla staging.
    Esto evita caídas por columnas nuevas en el origen.
    """

    stg = df_adj.copy()

    # metadata
    stg.insert(0, "run_id", str(run_id))
    stg.insert(1, "caso_id", int(caso_id))
    stg["version_reglas"] = int(version_reglas)
    stg["ts_ajuste"] = ts_ajuste
    stg["factor_chancado"] = factor_chancado
    stg["factor_sal"] = factor_sal
    stg["factor_finos"] = factor_finos
    stg["estado"] = 1

    # Fecha segura
    if "Fecha" in stg.columns:
        stg["Fecha"] = pd.to_datetime(stg["Fecha"]).dt.date
    else:
        raise ValueError("No existe columna Fecha en df_adj")

    # filtrar columnas vs DB
    cols_db = set(get_table_columns(engine, "inventar_SpcHidr", "rep_prod_ajustado_stg"))
    if not cols_db:
        raise ValueError("No se pudieron leer columnas de inventar_SpcHidr.rep_prod_ajustado_stg")

    cols_df = [c for c in stg.columns if c in cols_db]
    stg = stg[cols_df]

    stg.to_sql(
        "rep_prod_ajustado_stg",
        con=engine,
        schema="inventar_SpcHidr",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )


# ============================================================
# Orquestador principal
# ============================================================
def run_ajuste_reporte_prod(caso_id: int, version_reglas: int = 1) -> Dict[str, Any]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("get_engine() devolvió None. Revisa parámetros de conexión.")

    run_id = uuid.uuid4()
    fecha_ini, fecha_fin = sp_get_periodo_caso(engine, int(caso_id))

    # log start
    exec_sql(
        engine,
        "EXEC inventar_SpcHidr.sp_rep_log_start @run_id=:run_id, @caso_id=:caso_id, @fecha_ini=:ini, @fecha_fin=:fin",
        {"run_id": str(run_id), "caso_id": int(caso_id), "ini": fecha_ini.date(), "fin": fecha_fin.date()},
    )

    try:
        # (opcional pero recomendado) sincroniza schema staging/final con origen si tienes el SP creado
        # Si NO existe el SP, comenta esta línea.
        exec_sql(engine, "EXEC inventar_SpcHidr.sp_rep_prod_sync_schema")

        targets = sp_build_targets(engine, int(caso_id))

        df = load_query1_all_cols(engine, fecha_ini, fecha_fin)
        if df.empty:
            raise ValueError("Query1 no devolvió filas para el periodo del caso.")

        reglas = load_reglas(engine)
        if reglas.empty:
            raise ValueError("No hay reglas activas en inventar_SpcHidr.rep_prod_reglas (reporte_prod).")

        df_adj, factors = apply_rules(df, reglas, targets)

        # Factores (nombres reales en tu motor)
        factor_ch = factors.get("factor_Chancado_TMS_Real")

        # Para SAL, factor_{a_col}_{b_col}
        factor_sal = (
            factors.get("factor_Sal_turno_A_Sal_Turno_B")
            or factors.get("factor_Sal_Turno_B_Sal_turno_A")  # por si inviertes orden
        )

        factor_fi = factors.get("factor_Cobre_fino_Apilado_Real")

        ts_ajuste = dt.datetime.utcnow()

        write_staging(
            engine,
            df_adj,
            run_id,
            int(caso_id),
            int(version_reglas),
            ts_ajuste,
            factor_chancado=factor_ch,
            factor_sal=factor_sal,
            factor_finos=factor_fi,
        )

        exec_sql(engine, "EXEC inventar_SpcHidr.sp_rep_merge_ajustado_dyn @run_id=:run_id", {"run_id": str(run_id)})

        tot = {
            "sum_chancado": float(df_adj.get("Chancado_TMS_Real", pd.Series(dtype=float)).fillna(0).sum()),
            "sum_sal": float(
                (
                    df_adj.get("Sal_turno_A", pd.Series(dtype=float)).fillna(0)
                    + df_adj.get("Sal_Turno_B", pd.Series(dtype=float)).fillna(0)
                ).sum()
            ),
            "sum_finos": float(df_adj.get("Cobre_fino_Apilado_Real", pd.Series(dtype=float)).fillna(0).sum()),
            "targets": targets,
            "factors": {"factor_chancado": factor_ch, "factor_sal": factor_sal, "factor_finos": factor_fi},
            "periodo": [str(fecha_ini.date()), str(fecha_fin.date())],
        }

        exec_sql(
            engine,
            "EXEC inventar_SpcHidr.sp_rep_log_end @run_id=:run_id, @ok=1, @mensaje=NULL, @totales_json=:tot",
            {"run_id": str(run_id), "tot": json.dumps(tot)},
        )

        return {"ok": True, "run_id": str(run_id), "caso_id": int(caso_id), "totales": tot}



    except Exception as e:
        exec_sql(
            engine,
            "EXEC inventar_SpcHidr.sp_rep_log_end @run_id=:run_id, @ok=0, @mensaje=:msg, @totales_json=NULL",
            {"run_id": str(run_id), "msg": str(e)[:1900]},
        )
        raise

# ============================================================
# NUEVAS FUNCIONES PARA FASE 2
# Agregar al final de ajuste_reporte/rep_prod_adjuster.py
# ============================================================

def _safe_float(v, default=0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def _build_metric_row(metrica: str, ajustado: float, target: float, tolerancia_pct: float = 0.5) -> dict:
    ajustado = _safe_float(ajustado)
    target = _safe_float(target)

    dif_abs = ajustado - target
    dif_pct = None
    if target != 0:
        dif_pct = (dif_abs / target) * 100.0

    estado = "OK"
    if dif_pct is None:
        estado = "SIN_TARGET"
    elif abs(dif_pct) > tolerancia_pct:
        estado = "DESVIADO"

    return {
        "metrica": metrica,
        "ajustado": round(ajustado, 6),
        "target": round(target, 6),
        "dif_abs": round(dif_abs, 6),
        "dif_pct": None if dif_pct is None else round(dif_pct, 4),
        "estado": estado,
    }


def read_targets_df(engine: Engine, caso_id: int) -> pd.DataFrame:
    return read_sql_df(
        engine,
        """
        SELECT target_code, target_value
        FROM inventar_SpcHidr.rep_prod_targets
        WHERE caso_id = :caso_id
        ORDER BY target_code
        """,
        {"caso_id": caso_id},
    )


def read_ajustado_run_df(engine: Engine, caso_id: int, run_id: str) -> pd.DataFrame:
    """
    Lee la corrida actual desde staging.
    Staging es la fuente confiable para run_id/caso_id del ajuste recién ejecutado.
    """
    df = read_sql_df(
        engine,
        """
        SELECT *
        FROM inventar_SpcHidr.rep_prod_ajustado_stg
        WHERE caso_id = :caso_id
          AND run_id = :run_id
        ORDER BY Fecha
        """,
        {"caso_id": caso_id, "run_id": run_id},
    )

    if not df.empty:
        return df

    # Fallback opcional por compatibilidad futura
    df2 = read_sql_df(
        engine,
        """
        SELECT *
        FROM inventar_SpcHidr.rep_prod_ajustado
        WHERE caso_id = :caso_id
          AND run_id = :run_id
        ORDER BY Fecha
        """,
        {"caso_id": caso_id, "run_id": run_id},
    )

    if not df2.empty:
        return df2

    raise ValueError(
        f"No existen filas ni en rep_prod_ajustado_stg ni en rep_prod_ajustado "
        f"para caso_id={caso_id}, run_id={run_id}"
    )


def _get_periodo_caso_con_fallback(engine: Engine, caso_id: int) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Intenta obtener el periodo desde recon_caso (solver nuevo) PRIMERO; si
    el caso no existe ahi, cae a casos_balance (sistema viejo).

    Invertido 2026-09-09: se asumia que los dos espacios de caso_id nunca se
    cruzaban, pero casos_balance ocupa IDs bajos y densos (29 en adelante,
    con muchos huecos ya llenos hasta el 134+) que EMPEZARON a colisionar
    con IDs nuevos de recon_caso a medida que se crean mas casos del solver
    (caso real: id=29 existe en ambos sistemas con periodos distintos -
    marzo 2025 en casos_balance vs. agosto 2026 en recon_caso). Como el
    dropdown "Caso Balance" de la UI SIEMPRE viene de recon_caso, ese debe
    tener prioridad siempre; casos_balance sólo aplica a corridas viejas que
    ya no son seleccionables desde la UI actual."""
    try:
        fecha_ini, fecha_fin, _solver_run_id = get_periodo_y_run_solver(engine, caso_id)
        return fecha_ini, fecha_fin
    except ValueError:
        return sp_get_periodo_caso(engine, caso_id)


def build_resumen_comparativo_run(caso_id: int, run_id: str) -> Dict[str, Any]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Engine is None (revisa db_connection.get_engine())")

    fecha_ini, fecha_fin = _get_periodo_caso_con_fallback(engine, int(caso_id))
    dft = read_targets_df(engine, int(caso_id))
    dfa = read_ajustado_run_df(engine, int(caso_id), str(run_id))

    targets = dict(zip(dft["target_code"], dft["target_value"]))

    def colsum(c: str) -> float:
        return _safe_float(dfa[c].fillna(0).sum()) if c in dfa.columns else 0.0

    rows = []

    # 1. Chancado
    rows.append(_build_metric_row(
        "Σ Chancado_TMS_Real",
        colsum("Chancado_TMS_Real"),
        _safe_float(targets.get("F3"))
    ))

    # 2. Sal
    sal_sum = 0.0
    if "Sal_turno_A" in dfa.columns:
        sal_sum += _safe_float(dfa["Sal_turno_A"].fillna(0).sum())
    if "Sal_Turno_B" in dfa.columns:
        sal_sum += _safe_float(dfa["Sal_Turno_B"].fillna(0).sum())

    rows.append(_build_metric_row(
        "Σ (Sal_turno_A + Sal_Turno_B)",
        sal_sum,
        _safe_float(targets.get("F10F11_MASA"))
    ))

    # 3. Finos apilado
    rows.append(_build_metric_row(
        "Σ Cobre_fino_Apilado_Real",
        colsum("Cobre_fino_Apilado_Real"),
        _safe_float(targets.get("F14F15_FCU"))
    ))

    # 4. Reclamo / ripios
    rows.append(_build_metric_row(
        "Σ TMS_Rotopala_1_Real",
        colsum("TMS_Rotopala_1_Real"),
        _safe_float(targets.get("F19__MASA"))
    ))

    rows.append(_build_metric_row(
        "Σ TMS_Rotopala_2_Real",
        colsum("TMS_Rotopala_2_Real"),
        _safe_float(targets.get("F18__MASA"))
    ))

    rows.append(_build_metric_row(
        "Σ Camiones_TMS_Reclamo_Oxidos",
        colsum("Camiones_TMS_Reclamo_Oxidos"),
        _safe_float(targets.get("F22__MASA"))
    ))

    rows.append(_build_metric_row(
        "Σ Camiones_TMS_Reclamo_Sulfuros",
        colsum("Camiones_TMS_Reclamo_Sulfuros"),
        _safe_float(targets.get("F21__MASA"))
    ))

    # 5. SRR masa
    rows.append(_build_metric_row(
        "Σ SRR_TMS_promedio_dia",
        colsum("SRR_TMS_promedio_dia"),
        _safe_float(targets.get("F08F09_MASA"))
    ))

    # 6. Ley SRR ponderada
    ley_srr_pond = 0.0
    if "Ley_CuT_Real_srr" in dfa.columns and "SRR_TMS_promedio_dia" in dfa.columns:
        masa = dfa["SRR_TMS_promedio_dia"].fillna(0).astype(float)
        ley = dfa["Ley_CuT_Real_srr"].fillna(0).astype(float)
        masa_total = float(masa.sum())
        if masa_total > 0:
            ley_srr_pond = float((masa * ley).sum() / masa_total)
        else:
            ley_srr_pond = _safe_float(ley.mean())

    rows.append(_build_metric_row(
        "Ley_CuT_Real_srr ponderada",
        ley_srr_pond,
        _safe_float(targets.get("F08F09_LEY_CU"))
    ))

    return {
        "run_id": str(run_id),
        "caso_id": int(caso_id),
        "periodo": {
            "fecha_inicio": str(pd.to_datetime(fecha_ini).date()),
            "fecha_fin": str(pd.to_datetime(fecha_fin).date()),
        },
        "rows": rows,
        "targets": {k: _safe_float(v) for k, v in targets.items()},
    }


def publicar_run_oficial(
    caso_id: int,
    run_id: str,
    usuario_validacion: str,
    resumen_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Engine is None (revisa db_connection.get_engine())")

    resumen_json = json.dumps(resumen_payload or {}, ensure_ascii=False)

    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                EXEC inventar_SpcHidr.sp_rep_publish_oficial_validado
                    @run_id=:run_id,
                    @caso_id=:caso_id,
                    @usuario_validacion=:usuario_validacion,
                    @resumen_json=:resumen_json
                """
            ),
            {
                "run_id": str(run_id),
                "caso_id": int(caso_id),
                "usuario_validacion": str(usuario_validacion),
                "resumen_json": resumen_json,
            },
        )

        rows = result.fetchall()
        if not rows:
            raise RuntimeError("El SP sp_rep_publish_oficial_validado no devolvió filas.")

        row0 = rows[0]
        return {
            "ok": True,
            "run_id": str(run_id),
            "caso_id": int(caso_id),
            "validation_id": int(row0[0]),
            "rows_published": int(row0[1]),
        }


def registrar_rechazo_validacion(
    caso_id: int,
    run_id: str,
    usuario_validacion: str,
    resumen_payload: Dict[str, Any] | None = None,
    observacion: str | None = None,
) -> None:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Engine is None (revisa db_connection.get_engine())")

    resumen_json = json.dumps(resumen_payload or {}, ensure_ascii=False)

    exec_sql(
        engine,
        """
        EXEC inventar_SpcHidr.sp_rep_log_validacion_decision
            @run_id=:run_id,
            @caso_id=:caso_id,
            @decision=:decision,
            @usuario_validacion=:usuario_validacion,
            @resumen_json=:resumen_json,
            @observacion=:observacion
        """,
        {
            "run_id": str(run_id),
            "caso_id": int(caso_id),
            "decision": "RECHAZADO",
            "usuario_validacion": str(usuario_validacion),
            "resumen_json": resumen_json,
            "observacion": observacion,
        }
    )


def load_reporte_oficial_df(caso_id: int | None = None) -> pd.DataFrame:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Engine is None (revisa db_connection.get_engine())")

    sql = """
    SELECT *
    FROM inventar_SpcHidr.Datos_conciliados_of_ver
    WHERE 1=1
    """
    params = {}

    if caso_id is not None:
        sql += " AND caso_id = :caso_id"
        params["caso_id"] = int(caso_id)

    sql += " ORDER BY Fecha"

    return read_sql_df(engine, sql, params)


# ============================================================================
# PUENTE: solver nuevo (DEV_SIIR.hidro.recon_caso / recon_resultado_flujo)
# ============================================================================
# Agregado 2026-09-09: el motor de ajuste de arriba fue diseñado y probado
# contra inventar_SpcHidr.casos_balance / Data_balance_rec (sistema viejo,
# 127 casos historicos desde marzo 2025). Pero el dropdown "Caso Balance"
# del Dash muestra los casos del solver NUEVO (DEV_SIIR.hidro.recon_caso +
# recon_caso_oficial, confirmado por Luis como "la tabla oficial"), que es
# un espacio de caso_id totalmente distinto (0 coincidencias entre ambos).
#
# Hallazgo clave: DEV_SIIR.hidro.recon_flujo_modelo.codigo_flujo usa
# exactamente la misma numeracion (F3, F8/F9, F10/F11, F14/F15, F18, F19,
# F21, F22, ...) que los target_code que ya construye sp_rep_build_targets_caso
# desde Data_balance_rec.Flujo ("Flujo 03", "Flujo 08", etc). O sea: es el
# mismo diccionario de flujos, solo que el solver nuevo lo formalizo en una
# tabla propia. Esto permite calcular los mismos targets directamente desde
# recon_resultado_flujo (masa_reconciliada / fino_cu_reconciliado), sin
# pasar por casos_balance ni Data_balance_rec para los casos nuevos.
#
# A partir de aqui, para un caso de recon_caso, el caso_id que se usa en
# TODO el pipeline de ajuste (rep_prod_targets, rep_prod_ajustado_stg,
# rep_prod_ajuste_log) es el mismo recon_caso.id que aparece en el dropdown
# - no hace falta crear nada en casos_balance.

def get_periodo_y_run_solver(engine: Engine, caso_id: int) -> Tuple[pd.Timestamp, pd.Timestamp, int]:
    """Obtiene fecha_inicio/fecha_fin (de recon_caso) y el solver_run_id
    oficial (de recon_caso_oficial, el mas reciente) para un caso del
    solver nuevo."""
    df = read_sql_df(
        engine,
        """
        SELECT rc.fecha_inicio, rc.fecha_fin, rco.solver_run_id
        FROM [DEV_SIIR].[hidro].[recon_caso] rc
        INNER JOIN [DEV_SIIR].[hidro].[recon_caso_oficial] rco ON rco.caso_id = rc.id
        WHERE rc.id = :caso_id
        ORDER BY rco.oficializado_en DESC
        """,
        {"caso_id": caso_id},
    )
    if df.empty:
        raise ValueError(
            f"caso_id={caso_id} no tiene un run oficial en DEV_SIIR.hidro.recon_caso_oficial "
            f"(no se puede ejecutar el ajuste sin un solver_run_id oficializado)."
        )
    row = df.iloc[0]
    return pd.to_datetime(row["fecha_inicio"]), pd.to_datetime(row["fecha_fin"]), int(row["solver_run_id"])


def build_targets_from_solver_nuevo(engine: Engine, caso_id: int, solver_run_id: int) -> Dict[str, float]:
    """Calcula los targets (mismo target_code que sp_rep_build_targets_caso)
    desde DEV_SIIR.hidro.recon_resultado_flujo, y los persiste en
    inventar_SpcHidr.rep_prod_targets bajo el mismo caso_id de recon_caso
    (reemplaza los targets previos del caso, igual que hace el SP viejo)."""

    df = read_sql_df(
        engine,
        """
        SELECT codigo_flujo,
               COALESCE(masa_reconciliada, 0) AS masa_reconciliada,
               COALESCE(fino_cu_reconciliado, 0) AS fino_cu_reconciliado
        FROM [DEV_SIIR].[hidro].[recon_resultado_flujo]
        WHERE caso_id = :caso_id AND run_id = :run_id
        """,
        {"caso_id": caso_id, "run_id": solver_run_id},
    )
    if df.empty:
        raise ValueError(
            f"recon_resultado_flujo vacio para caso_id={caso_id}, run_id={solver_run_id}."
        )

    def _sum_masa(codigos):
        return float(df.loc[df["codigo_flujo"].isin(codigos), "masa_reconciliada"].sum())

    def _sum_fcu(codigos):
        return float(df.loc[df["codigo_flujo"].isin(codigos), "fino_cu_reconciliado"].sum())

    masa_srr = _sum_masa(["F8", "F9"])
    fcu_srr = _sum_fcu(["F8", "F9"])

    targets = {
        "F3": _sum_masa(["F3"]),
        "F10F11_MASA": _sum_masa(["F10", "F11"]),
        "F14F15_FCU": _sum_fcu(["F14", "F15"]),
        "F14F15_MASA": _sum_masa(["F14", "F15"]),
        "F19__MASA": _sum_masa(["F19"]),
        "F18__MASA": _sum_masa(["F18"]),
        "F21__MASA": _sum_masa(["F21"]),
        "F22__MASA": _sum_masa(["F22"]),
        "F08F09_MASA": masa_srr,
        "F08F09_FCU": fcu_srr,
        "F08F09_LEY_CU": (fcu_srr / masa_srr * 100.0) if masa_srr != 0 else 0.0,
    }

    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM inventar_SpcHidr.rep_prod_targets WHERE caso_id = :caso_id"),
            {"caso_id": caso_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO inventar_SpcHidr.rep_prod_targets (caso_id, target_code, target_value, fuente)
                VALUES (:caso_id, :target_code, :target_value, 'recon_resultado_flujo')
                """
            ),
            [
                {"caso_id": caso_id, "target_code": k, "target_value": v}
                for k, v in targets.items()
            ],
        )

    return targets


def run_ajuste_reporte_prod_solver_nuevo(caso_id: int, version_reglas: int = 1) -> Dict[str, Any]:
    """Igual que run_ajuste_reporte_prod, pero para un caso del solver NUEVO
    (DEV_SIIR.hidro.recon_caso): el periodo y los targets salen del solver
    nuevo (recon_caso_oficial / recon_resultado_flujo) en vez de
    casos_balance / Data_balance_rec. El resto del pipeline (Datos_conciliados_of,
    rep_prod_reglas, rep_prod_ajustado_stg, merge, log) es identico."""
    engine = get_engine()
    if engine is None:
        raise RuntimeError("get_engine() devolvió None. Revisa parámetros de conexión.")

    run_id = uuid.uuid4()
    fecha_ini, fecha_fin, solver_run_id = get_periodo_y_run_solver(engine, int(caso_id))

    exec_sql(
        engine,
        "EXEC inventar_SpcHidr.sp_rep_log_start @run_id=:run_id, @caso_id=:caso_id, @fecha_ini=:ini, @fecha_fin=:fin",
        {"run_id": str(run_id), "caso_id": int(caso_id), "ini": fecha_ini.date(), "fin": fecha_fin.date()},
    )

    try:
        targets = build_targets_from_solver_nuevo(engine, int(caso_id), solver_run_id)

        df = load_query1_all_cols(engine, fecha_ini, fecha_fin)
        if df.empty:
            raise ValueError("Datos_conciliados_of no devolvió filas para el periodo del caso.")

        reglas = load_reglas(engine)
        if reglas.empty:
            raise ValueError("No hay reglas activas en inventar_SpcHidr.rep_prod_reglas (reporte_prod).")

        df_adj, factors = apply_rules(df, reglas, targets)

        factor_ch = factors.get("factor_Chancado_TMS_Real")
        factor_sal = (
            factors.get("factor_Sal_turno_A_Sal_Turno_B")
            or factors.get("factor_Sal_Turno_B_Sal_turno_A")
        )
        factor_fi = factors.get("factor_Cobre_fino_Apilado_Real")

        ts_ajuste = dt.datetime.utcnow()

        write_staging(
            engine, df_adj, run_id, int(caso_id), int(version_reglas), ts_ajuste,
            factor_chancado=factor_ch, factor_sal=factor_sal, factor_finos=factor_fi,
        )

        exec_sql(engine, "EXEC inventar_SpcHidr.sp_rep_merge_ajustado_dyn @run_id=:run_id", {"run_id": str(run_id)})

        tot = {
            "solver_run_id": solver_run_id,
            "targets": targets,
            "factors": {"factor_chancado": factor_ch, "factor_sal": factor_sal, "factor_finos": factor_fi},
            "periodo": [str(fecha_ini.date()), str(fecha_fin.date())],
        }

        exec_sql(
            engine,
            "EXEC inventar_SpcHidr.sp_rep_log_end @run_id=:run_id, @ok=1, @mensaje=NULL, @totales_json=:tot",
            {"run_id": str(run_id), "tot": json.dumps(tot)},
        )

        return {"ok": True, "run_id": str(run_id), "caso_id": int(caso_id), "totales": tot}

    except Exception as e:
        exec_sql(
            engine,
            "EXEC inventar_SpcHidr.sp_rep_log_end @run_id=:run_id, @ok=0, @mensaje=:msg, @totales_json=NULL",
            {"run_id": str(run_id), "msg": str(e)[:1900]},
        )
        raise
