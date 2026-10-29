# ajuste_reporte/rep_prod_adjuster.py
import json
import uuid
import datetime as dt
import hashlib
import math
import os
import re
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine, Connection

from db_connection import get_engine
from ajuste_reporte.m6_targets import (
    M6ValidationError, build_targets_m6_125, prepare_m6_125, select_solver_model,
)


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
    if isinstance(engine, Connection):
        return pd.read_sql(text(sql), engine, params=params)
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
        f"""
        SELECT regla_id, col_nombre, orden_calculo, tipo_regla, target_code, formula_py, depende_de, params_json
        FROM inventar_SpcHidr.rep_prod_reglas{' WITH(HOLDLOCK)' if isinstance(engine, Connection) else ''}
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
        FROM inventar_SpcHidr.Datos_conciliados_of{' WITH(HOLDLOCK)' if isinstance(engine, Connection) else ''}
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
    parameter_limit: Optional[int] = None,
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
        chunksize=500 if parameter_limit is None else max(1, min(500, parameter_limit // len(stg.columns))),
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

    m6_log = _m6_logged_run(engine, int(caso_id), str(run_id))
    dfa = read_ajustado_run_df(engine, int(caso_id), str(run_id))
    if m6_log:
        targets = m6_log['targets']
        fecha_ini, fecha_fin = (pd.Timestamp(v) for v in m6_log['periodo'])
    else:
        fecha_ini, fecha_fin = _get_periodo_caso_con_fallback(engine, int(caso_id))
        dft = read_targets_df(engine, int(caso_id))
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

    # M6 usa el MISMO publicador, solo si ya fue corregido para periodos nuevos.
    model = read_sql_df(engine, """
        SELECT m.codigo FROM DEV_SIIR.hidro.recon_caso c
        JOIN DEV_SIIR.hidro.recon_modelo m ON m.id=c.modelo_id
        WHERE c.id=:caso_id
    """, {"caso_id": int(caso_id)})
    is_m6 = not model.empty and model.iloc[0]["codigo"] == "hidrometalurgia_125_v2"
    if is_m6:
        _m6_standard_guard(engine, publication=True)

    resumen_json = json.dumps(resumen_payload or {}, ensure_ascii=False)

    with engine.begin() as conn:
        m6_params = {}
        if is_m6:
            _m6_standard_guard(engine, publication=True, connection=conn)
            # Mismo orden de bloqueo que el SP: versiones antes de log/staging.
            conn.execute(text('SELECT COUNT_BIG(*) FROM inventar_SpcHidr.Datos_conciliados_of_ver WITH(TABLOCKX,HOLDLOCK)')).scalar_one()
            trace = _m6_validate_publication(conn, int(caso_id), str(run_id))
            m6_params = {'modelo_id': trace['modelo_id'], 'solver_run_id': trace['solver_run_id']}
        else:
            # Tampoco permitir que un caller120 use el SP destructivo antiguo.
            _assert_standard_publication_sql(conn)
        result = conn.execute(
            text(
                """
                EXEC inventar_SpcHidr.sp_rep_publish_oficial_validado
                    @run_id=:run_id,
                    @caso_id=:caso_id,
                    @usuario_validacion=:usuario_validacion,
                    @resumen_json=:resumen_json
                """ + (", @modelo_id=:modelo_id, @solver_run_id=:solver_run_id" if is_m6 else "")
            ),
            {
                "run_id": str(run_id),
                "caso_id": int(caso_id),
                "usuario_validacion": str(usuario_validacion),
                "resumen_json": resumen_json,
                **m6_params,
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
# La numeracion historica solo corresponde al modelo de 120 flujos.
# El modelo hidrometalurgia_125_v2 tiene otro catalogo: seleccion explicita
# por caso/run y constructor M6 independiente, sin cambiar aliases de reglas.
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


def get_solver_model_context(engine: Engine, caso_id: int, solver_run_id: int | None = None) -> dict:
    """Lee identidad actual/legacy y seleccion oficial sin ejecutar procedimientos."""
    df = read_sql_df(engine, """
        SELECT rc.id caso_id,rc.modelo_id,rc.fecha_inicio,rc.fecha_fin,
               sr.id solver_run_id,sr.caso_id run_caso_id,sr.estado estado_run,
               m.codigo modelo_codigo,m.legacy_modelo_id,m.total_flujos
        FROM DEV_SIIR.hidro.recon_caso rc WITH(HOLDLOCK)
        JOIN DEV_SIIR.hidro.recon_caso_oficial co WITH(HOLDLOCK) ON co.caso_id=rc.id
        JOIN DEV_SIIR.hidro.recon_solver_run sr WITH(HOLDLOCK) ON sr.id=co.solver_run_id
        JOIN DEV_SIIR.hidro.recon_modelo m WITH(HOLDLOCK) ON m.id=rc.modelo_id
        WHERE rc.id=:caso_id AND (:solver_run_id IS NULL OR sr.id=:solver_run_id)
        ORDER BY co.oficializado_en DESC
    """, {"caso_id": int(caso_id), "solver_run_id": solver_run_id})
    if df.empty:
        raise M6ValidationError("CASO_RUN_NO_OFICIAL", "No existe la seleccion oficial solicitada.")
    context = df.iloc[0].to_dict()
    if context['modelo_codigo'] == 'hidrometalurgia_125_v2' and len(df) != 1:
        raise M6ValidationError('CASO_RUN_AMBIGUO', 'M6 requiere una unica seleccion oficial de caso/run.')
    for field in ("caso_id", "modelo_id", "solver_run_id", "run_caso_id", "legacy_modelo_id", "total_flujos"):
        if pd.notna(context.get(field)):
            context[field] = int(context[field])
    select_solver_model(context)
    return context


def _read_m6_result_catalog(engine, context):
    results = read_sql_df(engine, """
        SELECT codigo_flujo,caso_id,run_id,flujo_modelo_id,
               masa_reconciliada,fino_cu_reconciliado
        FROM DEV_SIIR.hidro.recon_resultado_flujo WITH(HOLDLOCK)
        WHERE caso_id=:caso_id AND run_id=:run_id
    """, {"caso_id": context["caso_id"], "run_id": context["solver_run_id"]})
    catalog = read_sql_df(engine, """
        SELECT id,modelo_id,codigo_flujo,activo FROM DEV_SIIR.hidro.recon_flujo_modelo WITH(HOLDLOCK)
        WHERE modelo_id=:modelo_id ORDER BY orden_solver
    """, {"modelo_id": context["modelo_id"]})
    return results, catalog


def prepare_ajuste_m6_125(results, catalog, context, daily, rules, *,
                          require_pad_distribution=False, adjustment_run_id=None):
    """API pura de prueba: no conecta SQL, no escribe ni prepara publicacion."""
    return prepare_m6_125(results, catalog, context, daily, rules, apply_rules=apply_rules,
                         require_pad_distribution=require_pad_distribution,
                         adjustment_run_id=adjustment_run_id)


def preview_m6_from_solver(engine, caso_id, solver_run_id=None, *, require_pad_distribution=False):
    """Adaptador DEV exclusivamente de lectura; las pruebas offline usan la API pura."""
    from lixiviacion import phase_flags
    if isinstance(engine, Connection):
        phase_flags.guard_connection(engine)
    else:
        with engine.connect() as conn:
            phase_flags.guard_connection(conn)
    context = get_solver_model_context(engine, caso_id, solver_run_id)
    results, catalog = _read_m6_result_catalog(engine, context)
    daily = load_query1_all_cols(engine, context["fecha_inicio"], context["fecha_fin"])
    rules = load_reglas(engine)
    return prepare_ajuste_m6_125(results, catalog, context, daily, rules,
                                require_pad_distribution=require_pad_distribution)


def build_targets_from_solver_nuevo(engine: Engine, caso_id: int, solver_run_id: int, *, persist: bool = True) -> Dict[str, float]:
    """Seleccion explicita: 120 historico; M6 solo admite persist=False.

    Los aliases de reglas se conservan. La persistencia historica de 120
    permanece por defecto; M6 usa su constructor puro y nunca escribe targets.
    """

    context = get_solver_model_context(engine, caso_id, solver_run_id)
    if select_solver_model(context) == "m6_125":
        if persist:
            raise M6ValidationError("PERSISTENCIA_M6_BLOQUEADA", "El constructor M6 requiere persist=False; solo prueba en memoria.")
        results, catalog = _read_m6_result_catalog(engine, context)
        return build_targets_m6_125(results, catalog, context)

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

    if persist:
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


def _sql_module_comparison_text(value):
    """Solo normaliza CREATE/ALTER inicial, CRLF y terminacion del archivo.

    SQL Server conserva CREATE en sys.sql_modules tras ejecutar ALTER.
    No normaliza comentarios, espacios internos, literales ni el cuerpo SQL.
    """
    if not isinstance(value, str):
        return None
    value = value.replace('\r\n', '\n').rstrip()
    return re.sub(r'\A(?:CREATE|ALTER)(?= (?:PROCEDURE|VIEW) )',
                  'CREATE', value, count=1)


def _assert_standard_publication_sql(conn, *, include_srr=False):
    objects = [('sp_rep_publish_oficial_validado', 'sp_rep_publish_oficial_validado_new_period.sql')]
    if include_srr:
        objects.append(('vw_datos_conciliados_reporte', 'vw_datos_conciliados_reporte_srr.sql'))
    for name, filename in objects:
        actual = conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:name))'), {'name': 'inventar_SpcHidr.' + name}).scalar_one()
        expected = (Path(__file__).with_name('sql') / filename).read_text(encoding='utf8')
        if _sql_module_comparison_text(actual) != _sql_module_comparison_text(expected):
            raise M6ValidationError('PUBLICADOR_NO_SEGURO', 'No publicar hasta aplicar la correccion revisada de ' + name)


def _m6_standard_guard(engine, *, publication=False, connection=None):
    """Activación DEV explícita con respaldo acreditado y SQL existente corregido.

    No instala objetos ni convierte una mera entrada de MSDB en prueba de respaldo.
    El archivo de evidencia pertenece al operador de despliegue, no al Store de Dash.
    """
    code = 'PUBLICACION_M6_BLOQUEADA' if publication else 'PERSISTENCIA_M6_BLOQUEADA'
    if os.getenv('ENABLE_M6_DATOS_CONCILIADOS_DEV', '').strip() != '1':
        raise M6ValidationError(code, 'Adaptacion M6 preparada; falta habilitacion DEV con respaldo y publicador seguro.')
    from lixiviacion import phase_flags
    if not phase_flags.is_dev():
        raise M6ValidationError(code, 'Esta adaptacion solo admite la conexion DEV autorizada.')
    evidence_path = Path(os.getenv('M6_DEV_BACKUP_EVIDENCE', '')).resolve()
    audit_root = Path(__file__).resolve().parents[1] / 'auditorias'
    if not evidence_path.is_relative_to(audit_root) or not evidence_path.is_file():
        raise M6ValidationError(code, 'Falta evidencia operativa de respaldo en auditorias/.')
    proof = json.loads(evidence_path.read_text(encoding='utf8'))
    full_restore_proof = (proof.get('backup_verified_recoverable') is True
                          and isinstance(proof.get('backup_sha256'), str)
                          and len(proof['backup_sha256']) == 64
                          and all(c in '0123456789abcdef' for c in proof['backup_sha256'].lower()))
    reduced_dev_proof = (proof.get('backup_protocol') == 'DEV_CHECKSUM_VERIFYONLY'
                         and proof.get('backup_set_id') == 7003
                         and str(proof.get('backup_set_uuid', '')).upper() == '51F1E39A-980D-4675-BE94-87D832BD35F4'
                         and proof.get('backup_checksum_ok') is True
                         and proof.get('verifyonly_checksum_ok') is True
                         and proof.get('residual_risk_accepted') is True)
    if (not (full_restore_proof or reduced_dev_proof) or not proof.get('backup_reference')
            or proof.get('database_name') != 'inventar_SpcHidr'
            or proof.get('server_name', '').lower() != 'vps-5347319-x'
            or proof.get('new_period_publisher_tested') is not True
            or proof.get('consumers_review_passed') is not True
            or proof.get('execute_dev') is not True):
        raise M6ValidationError(code, 'Respaldo/ejecucion/pruebas transaccionales DEV no acreditados.')

    def check(conn):
        phase_flags.guard_connection(conn)
        _assert_standard_publication_sql(conn, include_srr=True)
    if connection is not None:
        check(connection)
    else:
        with engine.connect() as conn:
            check(conn)


def _m6_operational_columns(prepared):
    fields = sorted(set(prepared['columnas_ajustadas']) | set(prepared['columnas_heredadas']))
    srr = {'SRR_TMS_Turno_A', 'SRR_TMS_Turno_B', 'SRR_TMS_promedio_dia', 'SRR_TMS_Plan', 'Ley_CuT_Real_srr', 'Ley_CuT_Plan_srr'}
    if len(fields) != 47 or len(prepared['columnas_ajustadas']) != 19 or len(prepared['columnas_heredadas']) != 28 or not srr.issubset(fields):
        raise M6ValidationError('CONTRATO_47_INVALIDO', 'Se requieren 19 ajustadas,28 heredadas y seis SRR.')
    return fields


def _m6_payload_digest(frame, fields):
    """Huella de valores/NULL sin redondear; enteros y floats SQL equivalentes iguales."""
    def value(v):
        if pd.isna(v):
            return None
        if hasattr(v, 'item'):
            v = v.item()
        if isinstance(v, str):
            return ['texto', v]
        number = float(v)
        if not math.isfinite(number):
            raise M6ValidationError('VALOR_NO_FINITO', 'Payload M6 no finito.')
        return ['numero', number.hex()]
    rows = frame[['Fecha'] + fields].copy()
    rows['Fecha'] = pd.to_datetime(rows['Fecha']).dt.date
    records = [[str(r['Fecha']), *[value(r[c]) for c in fields]] for _, r in rows.sort_values('Fecha').iterrows()]
    return hashlib.sha256(json.dumps(records, ensure_ascii=False, separators=(',', ':')).encode('utf8')).hexdigest()


def _m6_logged_run(engine, caso_id, run_id):
    df = read_sql_df(engine, '''SELECT totales_json FROM inventar_SpcHidr.rep_prod_ajuste_log WITH(HOLDLOCK)
        WHERE caso_id=:caso_id AND run_id=:run_id AND ok=1''', {'caso_id': caso_id, 'run_id': str(uuid.UUID(str(run_id)))})
    if df.empty or 'totales_json' not in df or df.iloc[0]['totales_json'] is None:
        return None
    if len(df) != 1:
        raise M6ValidationError('TRAZA_AMBIGUA', 'El UUID tiene mas de un log de ajuste.')
    data = json.loads(df.iloc[0]['totales_json'])
    if data.get('modelo_codigo') != 'hidrometalurgia_125_v2':
        return None
    if data.get('namespace') != 'DEV_SIIR.hidro.recon_caso' or data.get('caso_id') != caso_id:
        raise M6ValidationError('TRAZA_INVALIDA', 'Origen/caso M6 del ajuste incoherente.')
    return data


def _m6_validate_publication(conn, caso_id, run_id):
    trace = _m6_logged_run(conn, caso_id, run_id)
    if not trace:
        raise M6ValidationError('TRAZA_AUSENTE', 'No hay evidencia completa del UUID M6 en el log habitual.')
    current = preview_m6_from_solver(conn, caso_id, trace['solver_run_id'])
    fields = _m6_operational_columns(current)
    if current['modelo_id'] != trace['modelo_id'] or current['targets'] != trace['targets']:
        raise M6ValidationError('ORIGEN_CAMBIO', 'El modelo o los resultados reconciliados cambiaron.')
    staged = read_sql_df(conn, '''SELECT * FROM inventar_SpcHidr.rep_prod_ajustado_stg WITH(UPDLOCK,HOLDLOCK)
        WHERE run_id=:run_id ORDER BY Fecha''', {'run_id': str(uuid.UUID(str(run_id)))})
    if (staged.empty or not staged['caso_id'].eq(caso_id).all()
            or not staged['version_reglas'].eq(trace['version_reglas']).all()):
        raise M6ValidationError('STAGING_INVALIDO', 'UUID sin staging propio del caso.')
    digest = _m6_payload_digest(staged, fields)
    if digest != trace['payload_sha256'] or digest != _m6_payload_digest(current['datos'], fields):
        raise M6ValidationError('PAYLOAD_CAMBIO', 'Las47columnas/NULL ya no coinciden con la preparacion validada.')
    return trace


def _run_m6_standard(engine, context, version_reglas):
    _m6_standard_guard(engine)
    if not isinstance(version_reglas, int) or isinstance(version_reglas, bool) or version_reglas < 1:
        raise ValueError('Version de reglas invalida.')
    # Preaviso solamente: el SP SIEMPRE vuelve a comprobar bajo su bloqueo transaccional.
    conflicts = read_sql_df(engine, '''SELECT DISTINCT Fecha FROM inventar_SpcHidr.Datos_conciliados_of_ver
        WHERE Fecha BETWEEN :ini AND :fin ORDER BY Fecha''', {'ini': context['fecha_inicio'], 'fin': context['fecha_fin']})
    if not conflicts.empty:
        raise M6ValidationError('PERIODO_CON_VERSIONES', 'Fechas con versiones: ' + ', '.join(str(v)[:10] for v in conflicts['Fecha']))
    prepared = preview_m6_from_solver(engine, context['caso_id'], context['solver_run_id'])
    if any(prepared[k] != context[k] for k in ('caso_id', 'modelo_id', 'solver_run_id')):
        raise M6ValidationError('ORIGEN_CAMBIO', 'El origen cambio durante la preparacion.')
    fields = _m6_operational_columns(prepared)
    for table in ('rep_prod_ajustado_stg', 'Datos_conciliados_of_ver'):
        if not set(fields).issubset(get_table_columns(engine, 'inventar_SpcHidr', table)):
            raise M6ValidationError('CONTRATO_47_INVALIDO', 'No se deben perder columnas en ' + table)
    run = uuid.UUID(prepared['run_id'])
    ini, fin = pd.Timestamp(context['fecha_inicio']), pd.Timestamp(context['fecha_fin'])
    exec_sql(engine, 'EXEC inventar_SpcHidr.sp_rep_log_start @run_id=:run_id,@caso_id=:caso_id,@fecha_ini=:ini,@fecha_fin=:fin',
             {'run_id': str(run), 'caso_id': context['caso_id'], 'ini': ini.date(), 'fin': fin.date()})
    try:
        factors = prepared['factores']
        factor_ch = factors.get('factor_Chancado_TMS_Real')
        factor_sal = factors.get('factor_Sal_turno_A_Sal_Turno_B') or factors.get('factor_Sal_Turno_B_Sal_turno_A')
        factor_fi = factors.get('factor_Cobre_fino_Apilado_Real')
        write_staging(engine, prepared['datos'], run, context['caso_id'], version_reglas, dt.datetime.utcnow(),
                      factor_chancado=factor_ch, factor_sal=factor_sal, factor_finos=factor_fi, parameter_limit=2000)
        staged = read_ajustado_run_df(engine, context['caso_id'], str(run))
        digest = _m6_payload_digest(prepared['datos'], fields)
        if _m6_payload_digest(staged, fields) != digest:
            raise M6ValidationError('STAGING_CAMBIO', 'La lectura de staging no conserva las47columnas/NULL.')
        totals = {'namespace': 'DEV_SIIR.hidro.recon_caso', 'caso_id': context['caso_id'],
                  'modelo_id': context['modelo_id'], 'modelo_codigo': context['modelo_codigo'],
                  'solver_run_id': context['solver_run_id'], 'targets': prepared['targets'],
                  'factors': {'factor_chancado': factor_ch, 'factor_sal': factor_sal, 'factor_finos': factor_fi},
                  'periodo': [str(ini.date()), str(fin.date())], 'version_reglas': version_reglas,
                  'payload_sha256': digest, 'columnas_operacionales': fields, 'diagnosticos': prepared['diagnosticos']}
        exec_sql(engine, 'EXEC inventar_SpcHidr.sp_rep_log_end @run_id=:run_id,@ok=1,@mensaje=NULL,@totales_json=:tot',
                 {'run_id': str(run), 'tot': json.dumps(totals, ensure_ascii=False)})
        return {'ok': True, 'run_id': str(run), 'caso_id': context['caso_id'], 'totales': totals}
    except Exception as exc:
        exec_sql(engine, 'EXEC inventar_SpcHidr.sp_rep_log_end @run_id=:run_id,@ok=0,@mensaje=:msg,@totales_json=NULL',
                 {'run_id': str(run), 'msg': str(exc)[:1900]})
        raise


def run_ajuste_reporte_prod_solver_nuevo(caso_id: int, version_reglas: int = 1, *, dry_run: bool = False) -> Dict[str, Any]:
    """120 conserva su pipeline; M6 usa su mapeo validado en el flujo habitual.

    Caso/modelo/run se resuelven desde recon_caso_oficial, sin confundir el
    solver_run_id entero con el UUID local del ajuste de prueba.
    """
    engine = get_engine()
    if engine is None:
        raise RuntimeError("get_engine() devolvió None. Revisa parámetros de conexión.")

    context = get_solver_model_context(engine, int(caso_id))
    if select_solver_model(context) == "m6_125":
        if dry_run:
            return preview_m6_from_solver(engine, int(caso_id), context["solver_run_id"])
        return _run_m6_standard(engine, context, version_reglas)
    if dry_run:
        raise M6ValidationError("PRUEBA_SOLO_M6", "El nuevo modo de prueba es M6; la ejecucion historica de 120 flujos no cambia.")

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
