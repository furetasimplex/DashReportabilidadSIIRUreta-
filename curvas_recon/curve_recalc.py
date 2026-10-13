#!/usr/bin/env python3
"""
curve_recalc.py — Curvas de recuperacion Cu recalculadas 100% desde
'10 Analisis Oxidos/Sulfuros' (sin ancla a Reporte_Recuperaciones).

Integra dia a dia desde `ini_aporte` (WIP) hasta el ultimo dia disponible
(o `fin_ciclo` si esta definido), y evalua para cada pila:

  factor(d)   = Q(d)[m3/h] * 24 / 1000                              -> t/(g/L)
  Cu_riego(d) = promedio expandido de Cu riego (planta) desde
                ini_aporte hasta d  (placeholder "para ahora", ver abajo)
  Cu_pls(d)   = promedio expandido de Cu PLS/drena de la pila desde
                ini_aporte hasta d  (idem)
  extraccion_base(d) = factor(d) * (FDRENA_MAX * Cu_pls(d) - Cu_riego(d))   [t Cu]
  extraccion(d) = extraccion_base(d) + extra(d)
  pct(d) = pct(d-1) + extraccion(d) / CuTf_p * 100      (pct(ini_aporte)=0)

`extra(d)` es el reparto de la reconciliacion MHE: para cada semana YA
ANCLADA, el delta de planta (mt_opt_t - mt_base_t, JOINT entre materiales)
se reparte entre las pilas activas esa semana proporcional a su propia
produccion medida esa semana:

  extraccion_base_pila_semana = FDRENA_MAX * W_p - Z_p   (W_p, Z_p de
                                 `recon_engine.compute_wz_week`, persistidos
                                 como w_t/z_t en `reconciliacion_detalle`)
  ajuste_pila_semana = (extraccion_base_pila_semana / mt_base_t_semana)
                        * (mt_opt_t_semana - mt_base_t_semana)
  extra(d) = ajuste_pila_semana / 7   para cada dia d de esa semana
             (curva diaria constante dentro de la semana, apuntando a la
             sumatoria semanal — mismo criterio MHE que el resto del
             sistema); 0 fuera de toda semana anclada.

Dias sin riego (Q=0) o sin ningun dato de Cu PLS todavia (promedio aun sin
muestras) no aportan extraccion_base ese dia (pero si `extra(d)`, que no
depende del riego del dia).

Nota metodologica (placeholder, confirmado por el usuario "para ahora"):
Cu riego/Cu PLS usan un PROMEDIO EXPANDIDO (ciclo de la pila a la fecha) en
vez del dato diario crudo, para no depender de la volatilidad diaria de la
lectura. Q (caudal) NO se toca, sigue siendo el dato diario crudo.
"""
from datetime import timedelta

import pandas as pd

from .recon_engine import FDRENA_MAX, CU_RIEGO_FALLBACK


# `campana.cu_tf` ya viene en TONELADAS de Cu fino contenido de la campana:
# `sync_campana` lo agrega como SUM(tms_cargado * cut_tm_total) / 100 sobre los
# ~5 modulos de la parcela. No lleva conversion.
#
# Hasta 2026-08 la columna guardaba otra cosa: `cut_tm_total` es la LEY del
# modulo en %CuT, y sync_campana copiaba la de UN modulo (0,45-1,4). Aqui se
# leia como kilotoneladas y se multiplicaba por 1000 -- ~474 t donde el fino
# contenido son ~5400 t. Esa era la causa de las curvas pegadas en 100 %:
# denominador ~11 veces chico, no leyes de PLS altas. La ley de PLS de una pila
# recien apilada SI sube 10-20x la mediana del pad y eso es real.


def cu_tf_toneladas(cu_tf):
    """`campana.cu_tf` -> t de Cu fino. Ya esta en t; solo valida.

    El NaN se descarta explicito: una pila con riego pero sin campana trae
    CuTf = NaN, que es truthy y sobrevive a `not cu_tf`, y dividir por el
    dibuja una curva entera de NaN en vez de omitirla."""
    if cu_tf is None or cu_tf != cu_tf or cu_tf <= 0:
        return None
    return float(cu_tf)


def _as_date(v):
    return v.date() if hasattr(v, 'date') else v


def _extraccion_base(w_t, z_t):
    """t Cu extraidos por una pila en una semana, a Fdrena base (FDRENA_MAX),
    a partir de W_p/Z_p (`recon_engine.compute_wz_week` / columnas w_t,z_t)."""
    if w_t is None or z_t is None:
        return None
    return FDRENA_MAX * w_t - z_t


def build_extra_lookup(hist_rows, week_totals):
    """hist_rows: `db_pipeline.load_pila_history(...)` (todas las semanas ya
    ancladas de UNA pila, con w_t/z_t). week_totals:
    `db_pipeline.load_week_totals(...)` -> {semana_lunes (str ISO): dict(
    mt_base_t, mt_opt_t)} JOINT (todos los materiales).

    Retorna {date: extra t Cu ese dia} repartiendo el delta de cada semana
    anclada proporcional a la produccion medida de esa pila esa semana.
    Solo pilas TRANS reciben ajuste esa semana -- las SS quedan a Fdrena
    base sin correccion (mismo criterio que los metodos slope/gekko previos,
    ver fix de "curvas SS mostrando cambios")."""
    lookup = {}
    for row in hist_rows:
        if row.get('estado') != 'TRANS':
            continue
        totals = week_totals.get(row['semana_lunes'])
        if not totals:
            continue
        mt_base, mt_opt = totals.get('mt_base_t'), totals.get('mt_opt_t')
        if not mt_base:
            continue
        extraccion_base = _extraccion_base(row.get('w_t'), row.get('z_t'))
        if extraccion_base is None:
            continue
        ajuste = (extraccion_base / mt_base) * ((mt_opt if mt_opt is not None else mt_base) - mt_base)
        extra_per_day = ajuste / 7.0
        wk = _as_date(pd.Timestamp(row['semana_lunes']))
        for i in range(7):
            lookup[wk + timedelta(days=i)] = extra_per_day
    return lookup


def pila_curve(p_name, cu_tf, ini_aporte, fin_ciclo, last_day, extra_lookup,
                riego, cu_riego, drena_cu):
    """Retorna {date: pct} recalculado dia a dia para una pila, o {} si
    faltan datos minimos (CuTf, ini_aporte, o la pila no esta en riego).
    extra_lookup: dict {date: t Cu extra ese dia} (ver `build_extra_lookup`
    / `recompute_curves`); dias ausentes no reciben ajuste."""
    cu_tf_t = cu_tf_toneladas(cu_tf)
    if cu_tf_t is None or pd.isna(ini_aporte):
        return {}
    if p_name not in riego.columns:
        return {}

    start_day = _as_date(ini_aporte)
    end_day = last_day
    if pd.notna(fin_ciclo):
        fin_day = _as_date(fin_ciclo)
        if fin_day < end_day:
            end_day = fin_day
    if end_day is None or end_day < start_day:
        return {}

    out = {}
    cum_cu = 0.0
    sum_r, n_r = 0.0, 0
    sum_d, n_d = 0.0, 0
    d_ts = pd.Timestamp(start_day)
    end_ts = pd.Timestamp(end_day)
    while d_ts <= end_ts:
        d = d_ts.date()
        # Promedios expandidos: incorporan el dia d ANTES de usarlo.
        # Nota: los indices de riego/cu_riego/drena_cu son datetime64
        # (Timestamp) -> comparar/indexar SIEMPRE con d_ts, nunca con `d`
        # (un `datetime.date` no matchea un DatetimeIndex ni en `in` ni en
        # comparaciones, y `d` solo se usa para las claves de salida y de
        # extra_lookup, que son dicts en Python puro).
        if d_ts in cu_riego.index:
            v = cu_riego.at[d_ts]
            if v == v:  # not NaN
                sum_r += float(v)
                n_r += 1
        if p_name in drena_cu.columns and d_ts in drena_cu.index:
            v = drena_cu.at[d_ts, p_name]
            if v == v:
                sum_d += float(v)
                n_d += 1

        q = float(riego.at[d_ts, p_name]) if d_ts in riego.index else 0.0
        extraccion = 0.0
        if q > 0 and n_d > 0:
            cu_r_mean = (sum_r / n_r) if n_r else CU_RIEGO_FALLBACK
            cu_d_mean = sum_d / n_d
            factor = q * 24.0 / 1000.0
            extraccion = factor * (FDRENA_MAX * cu_d_mean - cu_r_mean)
        extraccion += extra_lookup.get(d, 0.0)
        cum_cu += extraccion

        out[d] = min(cum_cu / cu_tf_t * 100.0, 100.0)
        d_ts += timedelta(days=1)
    return out


def build_daily_lookup(daily_hist, estado_by_week):
    """daily_hist: `db_pipeline.load_pila_daily_history(...)`. estado_by_week:
    {semana_lunes: estado} de `db_pipeline.load_pila_history(...)`. Retorna
    {date: dict(fdrena, q, cu_drena, cu_riego)} -- serie diaria REAL
    reconciliada (redisenio GEKKO/Pendiente). Semanas ancladas ANTES del
    rediseno no tienen filas en `reconciliacion_detalle_dia` y por lo tanto
    no aparecen aqui -- el llamador debe caer a `build_extra_lookup` +
    `pila_curve` (bolt-on semanal) para esas, ver `pila_curve_v2`. Semanas
    SS se excluyen (mismo criterio que `build_extra_lookup`/`pad_dashboard.
    _daily_series`): en SS el dato diario reconciliado ya es igual al
    crudo, pero incluirlo aqui dibujaria igual la traza "reconciliado"
    encima de la de medido y aparentaria ajuste donde no lo hay."""
    lookup = {}
    for row in daily_hist:
        if estado_by_week.get(row['semana_lunes']) != 'TRANS':
            continue
        wk = _as_date(pd.Timestamp(row['semana_lunes']))
        lookup[wk + timedelta(days=row['dia_offset'])] = dict(
            fdrena=row['fdrena'], q=row['q'], cu_drena=row['cu_drena'], cu_riego=row['cu_riego'])
    return lookup


def pila_curve_v2(p_name, cu_tf, ini_aporte, fin_ciclo, last_day, daily_lookup, extra_lookup,
                   riego, cu_riego, drena_cu, medido_lookup=None):
    """Como `pila_curve`, pero para dias con serie diaria real ya reconciliada
    (`daily_lookup`, ver `build_daily_lookup`) usa Fdrena/Q/Cu PLS/Cu riego
    RECONCILIADOS de ese dia exacto en vez del promedio expandido + parche
    `extra_lookup` -- ya no hace falta el bolt-on, el dato diario YA es el
    resultado de la reconciliacion (GEKKO o Pendiente). Dias sin fila diaria
    Y sin `extra_lookup` (nunca reconciliados: pre-ancla, o semana SS)
    NO acumulan con la formula promedio-expandido -- esa formula usa
    FDRENA_MAX como tasa fija y diverge fuerte de medido en pocas semanas
    (satura a 100% aunque no haya ajuste real). En vez de eso, `cum_cu` se
    sincroniza directo al valor medido de ese dia (`medido_lookup`), asi el
    tramo reconciliado siempre arranca desde la misma base que medido y solo
    diverge por un ajuste MHE real, nunca por dias sin reconciliar."""
    cu_tf_t = cu_tf_toneladas(cu_tf)
    if cu_tf_t is None or pd.isna(ini_aporte):
        return {}
    if p_name not in riego.columns:
        return {}

    start_day = _as_date(ini_aporte)
    end_day = last_day
    if pd.notna(fin_ciclo):
        fin_day = _as_date(fin_ciclo)
        if fin_day < end_day:
            end_day = fin_day
    if end_day is None or end_day < start_day:
        return {}

    medido_lookup = medido_lookup or {}
    out = {}
    # El acumulado NO arranca en cero: arranca donde la curva medida dejo a la
    # pila el dia anterior al primero del tramo. Si no se siembra, una pila
    # madura cuya ventana entera esta reconciliada (no queda ningun dia por el
    # que pasar por la sincronizacion de abajo) se dibuja re-integrando su
    # ciclo desde cero, y en un dia de riego ya supera su Cu fino: la curva
    # reconciliada sale pegada en 100 % mientras la medida va en 69 %.
    cum_cu = medido_lookup.get(start_day - timedelta(days=1), 0.0)
    sum_r, n_r = 0.0, 0
    sum_d, n_d = 0.0, 0
    d_ts = pd.Timestamp(start_day)
    end_ts = pd.Timestamp(end_day)
    while d_ts <= end_ts:
        d = d_ts.date()
        if d_ts in cu_riego.index:
            v = cu_riego.at[d_ts]
            if v == v:
                sum_r += float(v)
                n_r += 1
        if p_name in drena_cu.columns and d_ts in drena_cu.index:
            v = drena_cu.at[d_ts, p_name]
            if v == v:
                sum_d += float(v)
                n_d += 1

        daily = daily_lookup.get(d)
        if daily is None and d not in extra_lookup:
            if d in medido_lookup:
                cum_cu = medido_lookup[d]
            out[d] = min(cum_cu / cu_tf_t * 100.0, 100.0)
            d_ts += timedelta(days=1)
            continue

        extraccion = 0.0
        if daily is not None:
            q = daily['q'] or 0.0
            if q > 0 and daily['cu_drena'] is not None:
                factor = q * 24.0 / 1000.0
                fdrena_d = daily['fdrena'] if daily['fdrena'] is not None else FDRENA_MAX
                cu_r_d = daily['cu_riego'] if daily['cu_riego'] is not None else CU_RIEGO_FALLBACK
                extraccion = factor * (fdrena_d * daily['cu_drena'] - cu_r_d)
        else:
            q = float(riego.at[d_ts, p_name]) if d_ts in riego.index else 0.0
            if q > 0 and n_d > 0:
                cu_r_mean = (sum_r / n_r) if n_r else CU_RIEGO_FALLBACK
                cu_d_mean = sum_d / n_d
                factor = q * 24.0 / 1000.0
                extraccion = factor * (FDRENA_MAX * cu_d_mean - cu_r_mean)
            extraccion += extra_lookup.get(d, 0.0)
        cum_cu += extraccion

        out[d] = min(cum_cu / cu_tf_t * 100.0, 100.0)
        d_ts += timedelta(days=1)
    return out


def recompute_curves(recon_data, materials, joint_weeks, active_bounds=None):
    """
    recon_data: {label: sub-resultado} = `reconcile_week_gekko(...)['materials']`
      (necesita 'weeks' y 'wz' con w_t/z_t por pila, claves pd.Timestamp).
    materials: RECON_MATERIALS (wip/riego/cu_riego/drena_cu por material).
    joint_weeks: `reconcile_week_gekko(...)['weeks']` (JOINT, todos los
      materiales) -> {week_start: dict(mt_base_t, mt_opt_t, ...)} — el total
      de planta de la semana recien anclada, para repartir su delta.
    active_bounds: {label: {parcela_num: (ini_aporte, fin_ciclo)}} del CICLO
      ACTIVO de cada pila segun la pestana Curvas (`pad_dashboard._current_
      cycle_series`/CYCLES_OX/CYCLES_SU), NO el WIP crudo — el WIP puede
      apuntar a un ciclo ya terminado si esta desactualizado respecto a la
      fuente de reconciliacion, lo que mezclaria mas de un ciclo bajo el
      mismo CuTf e inflaria el % muy por encima de lo real. Pilas ausentes de
      este dict (o sin bounds) se omiten del resultado -> "solo las curvas
      activas".

    Retorna {label: {parcela_num: {date: pct}}} — SOLO pilas activas, y SOLO
    los dias dentro de la ventana de la semana recien anclada
    (window_start..window_end). La integracion diaria sigue corriendo desde
    el inicio del ciclo activo (se necesita el acumulado para que el pct de
    esos dias sea correcto), pero el reporte/salida no toca dias fuera de
    esa semana -> no se reescribe la curva historica completa.
    """
    out = {}
    for label, mat in materials.items():
        res = recon_data.get(label, {})
        bounds = (active_bounds or {}).get(label, {})
        weeks = sorted(res.get('weeks', {}).keys())
        if weeks:
            ws = weeks[0]
            window_start = _as_date(ws)
            window_end = _as_date(ws + timedelta(days=6))
            totals = joint_weeks.get(ws, {})
            mt_base, mt_opt = totals.get('mt_base_t'), totals.get('mt_opt_t')
        else:
            window_start = window_end = None
            mt_base = mt_opt = None

        riego, cu_riego, drena_cu = mat['riego'], mat['cu_riego'], mat['drena_cu']
        last_candidates = [idx.max() for idx in (riego.index, cu_riego.index, drena_cu.index) if len(idx)]
        last_day = _as_date(max(last_candidates)) if last_candidates else None

        wz = res.get('wz', {})
        transient_set = set(res.get('transient', []))
        series_by_p = {}
        if last_day is not None:
            for p_name, info in mat['wip'].items():
                num = int(p_name[1:])
                ini_aporte, fin_ciclo = bounds.get(num, (None, None))
                if ini_aporte is None:
                    continue
                cu_tf = info.get('CuTf')      # t de Cu fino contenido
                extra_lookup = {}
                if window_start is not None and mt_base and p_name in transient_set:
                    extraccion_base = _extraccion_base(wz.get(p_name, {}).get('W'), wz.get(p_name, {}).get('Z'))
                    if extraccion_base is not None:
                        ajuste = (extraccion_base / mt_base) * ((mt_opt if mt_opt is not None else mt_base) - mt_base)
                        extra_per_day = ajuste / 7.0
                        d = window_start
                        while d <= window_end:
                            extra_lookup[d] = extra_per_day
                            d += timedelta(days=1)
                series = pila_curve(
                    p_name, cu_tf, ini_aporte, fin_ciclo,
                    last_day, extra_lookup, riego, cu_riego, drena_cu,
                )
                if series and window_start is not None:
                    series = {d: v for d, v in series.items() if window_start <= d <= window_end}
                if series:
                    series_by_p[num] = series
        out[label] = series_by_p
    return out
