#!/usr/bin/env python3
"""
pad_dashboard.py — Pads de Lixiviacion: Curvas + Reconciliacion MHE
=============================================================================
Fuente curvas: Reporte_Recuperaciones 31 de Agosto 2025.xlsx
Fuente reconciliacion: 10 Analisis Sulfuros.xlsx / 10 Analisis Oxidos.xlsx / Produccion.xlsx
Ejecutar: python pad_dashboard.py   ->   http://localhost:8051

Instalar: pip install dash dash-bootstrap-components plotly pandas openpyxl scipy
"""
import os
import pickle
import tempfile
import time
import uuid
import threading
from collections import OrderedDict
from functools import wraps
from datetime import datetime, timedelta

import dash
from dash import dcc, html, Input, Output, State, ctx, ALL
import dash.exceptions
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .pad_data import load_oxido, load_sulfuro
from .pad_layout import build_pad, STATUS_COLORS, RECON_STATUS_COLORS
from .pad_selection import toggle_selection
from .pad_cycles import split_into_cycles
from .curve_recalc import (
    pila_curve, pila_curve_v2, build_extra_lookup, build_daily_lookup, _as_date,
    cu_tf_toneladas,
)
from .recon_engine import (
    FDRENA_MAX, UNLISTED_GAP_DAYS,
    week_monday, load_wip, load_rec_curves, load_riego, load_cu_riego,
    load_drena_cu, load_produccion, compute_wz_week, material_cutoff,
    reconcile_week_flowsheet_dash, N_TRANSIENT_DEFAULT, clear_curve_cache,
    active_pilas_by_riego, resolve_window, clear_actividad_cache,
    _fechas_actividad,
)
from .input_preparation import prepare_recon_inputs
from .perf_trace import record_phase, set_trace_id, reset_trace_id
from .db_pipeline import (
    connect, get_material_id, load_pila_daily_history, load_pila_history, load_week_totals, save_run,
    load_casos, load_caso_anchor,
    caso_anchor_completo, diagnose_caso_anchor, HIDRO_SCHEMA,
)

# Todo lo que se lee de la DB pasa por un cache local en disco (`local_cache.py`).
from .local_cache import limpiar as limpiar_cache_local, estado as estado_cache_local

# Corridas crudas del motor (`res` con `piles` y detalle diario). No caben en
# `dcc.Store`, pero tampoco pueden vivir en un global del proceso: dos usuarios
# (o dos workers) terminarian exportando la corrida equivocada. Cada corrida se
# guarda transitoriamente en disco y el navegador conserva solo su token opaco.
_RECON_RAW_DIR = os.path.join(tempfile.gettempdir(), 'hidronueva_recon_runs')
_RECON_RAW_TTL_SECONDS = 24 * 60 * 60
# Change this when the meaning of a stored reconciliation changes. Browser
# stores can outlive a deployment and otherwise export pre-fix results.
_RECON_RAW_PAYLOAD_VERSION = 2

TOP_OX = list(range(1, 17))
BOTTOM_OX = list(range(32, 16, -1))
TOP_SU = list(range(1, 15))
BOTTOM_SU = list(range(28, 14, -1))

# Paleta categorica validada (dataviz skill, orden fijo — ver palette.md),
# sin el naranja/vermillion reservado a la marca SIIR / MT_opt. Asignada por
# ORDEN DE SELECCION (no hash de id): la 1ra parcela seleccionada siempre
# toma el slot 1, etc. — es la asignacion que el par adyacente fue validado
# para (`node validate_palette.js` PASS, 7 slots, modo light, surface #fcfcfb).
CURVA_PALETTE = ['#2a78d6', '#008300', '#e87ba4', '#eda100', '#1baf7a', '#4a3aa7', '#e34948']

CHART_SURFACE = '#FFFFFF'
CHART_INK_PRIMARY = '#1F2937'
CHART_INK_SECONDARY = '#4B5563'
CHART_INK_MUTED = '#6B7280'
CHART_GRIDLINE = '#E5E7EB'
CHART_BASELINE = '#D1D5DB'


def _series_color(idx: int) -> str:
    return CURVA_PALETTE[idx % len(CURVA_PALETTE)]


def _recon_raw_path(token):
    """Ruta segura del payload temporal de una corrida, o None si no es UUID."""
    try:
        return os.path.join(_RECON_RAW_DIR, f'{uuid.UUID(str(token)).hex}.pkl')
    except (TypeError, ValueError, AttributeError):
        return None


def _clean_recon_raw_cache():
    """Borra payloads vencidos; payloads descargados siguen disponibles hasta vencer."""
    if not os.path.isdir(_RECON_RAW_DIR):
        return
    cutoff = time.time() - _RECON_RAW_TTL_SECONDS
    for name in os.listdir(_RECON_RAW_DIR):
        path = os.path.join(_RECON_RAW_DIR, name)
        try:
            if name.endswith('.pkl') and os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def _save_recon_raw(res, caso, week_start, week_end):
    """Persiste una corrida para SU sesion; funciona aun si la descarga cae en
    otro worker del mismo host."""
    os.makedirs(_RECON_RAW_DIR, exist_ok=True)
    _clean_recon_raw_cache()
    token = uuid.uuid4().hex
    path = _recon_raw_path(token)
    fd, tmp_path = tempfile.mkstemp(dir=_RECON_RAW_DIR, suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as fh:
            pickle.dump(dict(payload_version=_RECON_RAW_PAYLOAD_VERSION,
                             res=res, caso=caso, ws=week_start, we=week_end), fh,
                        protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    return token


def _load_recon_raw(token, caso_id):
    """Lee solamente el payload emitido por este dashboard y valida el Caso."""
    path = _recon_raw_path(token)
    if path is None or not os.path.isfile(path):
        return None, None
    try:
        with open(path, 'rb') as fh:
            raw = pickle.load(fh)
    except (OSError, pickle.PickleError, EOFError):
        return None, path
    if (not isinstance(raw, dict)
            or raw.get('payload_version') != _RECON_RAW_PAYLOAD_VERSION):
        return None, path
    caso = raw.get('caso')
    if not isinstance(caso, dict) or caso.get('id') != caso_id:
        return None, path
    return raw, path


def _global_last_date(data: dict):
    all_dates = [dt for p in data.values() for dt in p['dates']]
    return max(all_dates) if all_dates else None


def _load_material_window(label, start, end):
    """Material completo (wip + curvas + series riego/cu_riego/drena_cu) con
    las series diarias acotadas a [start, end] via query SQL directa -- evita
    cargar el historico completo para cada callback."""
    rec_curves, max_rec, ciclo_d = REC_META[label]
    return dict(
        wip=WIP_META[label], rec_curves=rec_curves, max_rec=max_rec, ciclo_d=ciclo_d,
        riego=load_riego(label, start, end),
        cu_riego=load_cu_riego(label, start, end),
        drena_cu=load_drena_cu(label, start, end),
    )

# Collect callback declarations at import; install them on the host app once.
_CALLBACKS = []
_DATA_READY = False
_FULL_DATA_READY = False

# Avance visible en UI mientras corre carga/cálculo (otra hebra lo lee vía Interval).
_PROGRESS_LOCK = threading.Lock()
_PROGRESS = {
    'active': False,
    'label': '',
    'detail': '',
    'pct': 0,
    'seq': 0,
}


def _progress_begin(label, detail='', pct=0):
    with _PROGRESS_LOCK:
        _PROGRESS.update({
            'active': True, 'label': label, 'detail': detail or '',
            'pct': max(0, min(100, int(pct))), 'seq': _PROGRESS['seq'] + 1,
        })


def _progress_set(label, detail='', pct=None):
    with _PROGRESS_LOCK:
        _PROGRESS['active'] = True
        _PROGRESS['label'] = label
        _PROGRESS['detail'] = detail or ''
        if pct is not None:
            _PROGRESS['pct'] = max(0, min(100, int(pct)))
        _PROGRESS['seq'] += 1


def _progress_end():
    with _PROGRESS_LOCK:
        _PROGRESS.update({
            'active': False, 'label': '', 'detail': '', 'pct': 0,
            'seq': _PROGRESS['seq'] + 1,
        })


def _progress_snapshot():
    with _PROGRESS_LOCK:
        return dict(_PROGRESS)


def _progress_children(snap=None):
    snap = snap or _progress_snapshot()
    if not snap['active'] and not snap['label']:
        return ''
    pct = snap['pct']
    detail = snap['detail']
    return html.Div([
        html.Div([
            html.Strong(snap['label'] or 'Procesando…', className='curvas-progress-label'),
            html.Span(f'{pct} %', className='curvas-progress-pct'),
        ], className='curvas-progress-head'),
        html.Div(
            html.Span(style={'width': f'{pct}%'}),
            className='curvas-progress-bar',
            **{'aria-valuenow': pct, 'aria-valuemin': 0, 'aria-valuemax': 100},
        ),
        html.Div(detail, className='curvas-progress-detail') if detail else None,
    ])
# Empty defaults let the visible controls render without loading all history.
DATA_OX, DATA_SU, CYCLES_OX, CYCLES_SU = {}, {}, {}, {}
GLOBAL_MIN_DATE = GLOBAL_MAX_DATE = JOINT_DATA_CUTOFF = None
MAX_CAMPANAS = 1
CAMPANA_OPTIONS = [{'label': 'Campaña 1', 'value': 1}]
WIP_META, REC_META, _CUTOFFS = {}, {}, {}
CASOS, CASO_OPTIONS, DEFAULT_CASO_ID = [], [], None
DEFAULT_WEEK_STR = None
RECON_PRODUCCION = pd.Series(dtype=float)
RAW_CURVES_BY_MATERIAL = {'OXIDOS': {}, 'SULFUROS': {}}
_ACTIVE_OX, _ACTIVE_SU = set(), set()
_DATA_LOCK = threading.RLock()
# Figuras por pila aisladas por token de corrida y ventana oficial.
_PILA_FIGURE_CACHE = OrderedDict()
_PILA_FIGURE_CACHE_LOCK = threading.RLock()
_PILA_FIGURE_CACHE_TTL = 180
_PILA_FIGURE_CACHE_MAX = 96


def _callback(*args, **kwargs):
    def declare(fn):
        _CALLBACKS.append((args, kwargs, fn))
        return fn
    return declare


def _trace_render(phase):
    def decorate(fn):
        @wraps(fn)
        def measured(*args, **kwargs):
            trace_id = next((arg.get('performance_id') for arg in args
                             if isinstance(arg, dict) and arg.get('performance_id')), None)
            started = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                record_phase(phase, time.perf_counter() - started, trace_id=trace_id)
        return measured
    return decorate


def initialize_data(force=False):
    """Opening the section needs only official Case options, not history."""
    global _DATA_READY, CASOS, CASO_OPTIONS, DEFAULT_CASO_ID
    with _DATA_LOCK:
        if force:
            ensure_full_data(force=True)
        elif not _DATA_READY:
            started = time.perf_counter()
            _progress_begin('Cargando casos oficiales', f'Consultando {HIDRO_SCHEMA}…', 5)
            try:
                CASOS, CASO_OPTIONS, DEFAULT_CASO_ID = _load_caso_options()
                _progress_set('Casos listos', f'{len(CASO_OPTIONS)} opciones', 100)
                _DATA_READY = True
                print(f'[curvas] opciones de casos: {time.perf_counter() - started:.3f}s')
            finally:
                _progress_end()


def ensure_full_data(force=False):
    """Load calculation inputs once per worker, immediately before use."""
    global _DATA_READY, _FULL_DATA_READY
    with _DATA_LOCK:
        if force or not _FULL_DATA_READY:
            _FULL_DATA_READY = False
            started = time.perf_counter()
            owns_progress = not _progress_snapshot()['active']
            if owns_progress:
                _progress_begin('Cargando histórico y metadatos', 'Preparando cachés…', 2)
            try:
                refresh_data_caches(bajar_de_nuevo=force)
                _FULL_DATA_READY = _DATA_READY = True
                print(f'[curvas] histórico y metadatos: {time.perf_counter() - started:.3f}s')
            finally:
                if owns_progress:
                    _progress_end()


# ── Curvas: helpers ──────────────────────────────────────────────────────────────

def _view_data(cycles_map: dict, campana_idx: int) -> dict:
    view = {}
    for num, cycles in cycles_map.items():
        if campana_idx <= len(cycles):
            cyc = cycles[campana_idx - 1]
            status = 'inactiva' if cyc['finished'] else 'activa'
            view[num] = dict(status=status, disabled=False, dates=cyc['dates'], values=cyc['values'])
        else:
            view[num] = dict(status='sin_datos', disabled=True, dates=[], values=[])
    return view


def _load_caso_options():
    """Casos oficiales exitosos, ordenados por fecha descendente."""
    try:
        casos = load_casos()
    except Exception:
        raise RuntimeError('No se pudo cargar la lista de Casos oficiales.') from None
    # load_casos entrega solo runs oficiales exitosos; exige run_id tambi?n aqu?.
    casos = [c for c in casos if c.get('run_id')]
    options = []
    for c in casos:
        dias = (c['fecha_fin'] - c['fecha_inicio']).days + 1
        options.append({
            'label': (f'#{c["id"]} {c["nombre"]} — {c["fecha_inicio"].date()} a '
                      f'{c["fecha_fin"].date()} ({dias} d)'),
            'value': c['id'],
        })
    default = casos[0]['id'] if casos else None
    return casos, options, default


def _caso_by_id(caso_id):
    return next((c for c in (CASOS or []) if c['id'] == caso_id), None)


def _store_window(data):
    """(inicio, fin, n_dias) de la ventana guardada en `recon-store`.

    Stores viejos solo traen `week_start`; para esos se asume la semana de 7
    dias de siempre, para no romper la lectura de una sesion ya abierta."""
    ws = data.get('week_start')
    if not ws:
        return None, None, 0
    return resolve_window(ws, data.get('week_end'))


def _store_matches_case(data, caso_id):
    """True only when the visible result belongs to the selected Case."""
    return bool(data and caso_id is not None and data.get('caso_id') == caso_id)


def refresh_data_caches(bajar_de_nuevo=False):
    """Recalcula TODAS las cachés de datos que hasta ahora se cargaban una
    sola vez al importar el modulo. Un `sync_all()` en la DB no sirve de nada
    si nadie vuelve a llamar a esto -- las globales de abajo (`DATA_OX`,
    `JOINT_DATA_CUTOFF`, `_ACTIVE_OX`, etc.) son las que de verdad alimentan
    la tab de Reconciliacion, y sin este refresco quedan congeladas en lo que
    había al arrancar el proceso.

    Se llama antes de usar resultados/c?lculos; los flujos internos pueden
    solicitar una recarga forzada cuando corresponda.

    `bajar_de_nuevo` bota ademas el cache local en disco (`local_cache.py`).
    Al importar se aprovecha lo guardado, evitando otra bajada al arrancar."""
    global DATA_OX, DATA_SU, CYCLES_OX, CYCLES_SU, GLOBAL_MIN_DATE, GLOBAL_MAX_DATE
    global MAX_CAMPANAS, CAMPANA_OPTIONS, WIP_META, REC_META, _CUTOFFS
    global JOINT_DATA_CUTOFF, DEFAULT_WEEK_STR, RECON_PRODUCCION, RAW_CURVES_BY_MATERIAL
    global CASOS, CASO_OPTIONS, DEFAULT_CASO_ID
    global _ACTIVE_OX, _ACTIVE_SU

    with _PILA_FIGURE_CACHE_LOCK:
        _PILA_FIGURE_CACHE.clear()
    clear_curve_cache()
    # Historico de riego/drenaje con que se detectan las pilas que arrancan:
    # tampoco expira solo, hay que botarlo junto con el resto.
    clear_actividad_cache()
    if bajar_de_nuevo:
        _progress_set('Actualizando datos', 'Limpiando caché local…', 5)
        limpiar_cache_local()

    _progress_set('Curvas de óxido', 'Leyendo recuperaciones…', 12)
    DATA_OX = load_oxido()
    _progress_set('Curvas de sulfuro', 'Leyendo recuperaciones…', 28)
    DATA_SU = load_sulfuro()

    _progress_set('Campañas', 'Partiendo ciclos por pila…', 38)
    last_ox, last_su = _global_last_date(DATA_OX), _global_last_date(DATA_SU)
    CYCLES_OX = {num: split_into_cycles(p['dates'], p['values'], last_ox)
                 for num, p in DATA_OX.items()}
    CYCLES_SU = {num: split_into_cycles(p['dates'], p['values'], last_su)
                 for num, p in DATA_SU.items()}

    _all_curve_dates = [d for p in list(DATA_OX.values()) + list(DATA_SU.values()) for d in p['dates']]
    GLOBAL_MIN_DATE = min(_all_curve_dates) if _all_curve_dates else None
    GLOBAL_MAX_DATE = max(_all_curve_dates) if _all_curve_dates else None

    MAX_CAMPANAS = max(
        [len(c) for c in list(CYCLES_OX.values()) + list(CYCLES_SU.values())] + [1]
    )
    CAMPANA_OPTIONS = [{'label': f'Campaña {i}', 'value': i} for i in range(1, MAX_CAMPANAS + 1)]

    # WIP (parcela/campana actual) y curvas de recuperacion: tablas chicas,
    # sin escala de fecha relevante para el recon semanal.
    _progress_set('WIP y recuperación', 'Óxidos y sulfuros…', 52)
    WIP_META = {label: load_wip(label) for label in ('SULFUROS', 'OXIDOS')}
    REC_META = {label: load_rec_curves(label) for label in ('SULFUROS', 'OXIDOS')}

    # Cruce de fechas: ningun material puede aportar mas alla del corte del
    # OTRO (si uno termina antes, el residuo de planta se concentra mal en el
    # que quedo "solo" — ver fix de "aporte SULFUROS ~0 semana 2025-08-25").
    # El corte se recalcula cada carga contra la DB en vivo.
    _progress_set('Cortes de fecha', 'Alineando materiales…', 64)
    _CUTOFFS = {label: material_cutoff(label) for label in ('SULFUROS', 'OXIDOS')}
    JOINT_DATA_CUTOFF = min(c for c in _CUTOFFS.values() if c is not None)
    # Default heredado (ultimo lunes de semana COMPLETA dentro del corte).
    # Ya no hay selector de fecha -- la ventana la fija el Caso -- pero se
    # deja calculado como fallback para cuando no hay ningun Caso cargado.
    _last_full_monday = week_monday(JOINT_DATA_CUTOFF)
    if _last_full_monday + pd.Timedelta(days=6) > JOINT_DATA_CUTOFF:
        _last_full_monday -= pd.Timedelta(days=7)
    DEFAULT_WEEK_STR = str(_last_full_monday.date())

    # Casos de reconciliacion global. La ventana de trabajo del dashboard
    # sale de aca (`fecha_inicio`..`fecha_fin`), no de un datepicker: el
    # resultado por pila tiene que ser comparable con el flowsheet del Caso,
    # y para eso el periodo tiene que ser EL MISMO. El del caso 17, por
    # ejemplo, dura 8 dias y no empieza lunes.
    _progress_set('Casos oficiales', 'Actualizando lista…', 74)
    CASOS, CASO_OPTIONS, DEFAULT_CASO_ID = _load_caso_options()

    _progress_set('Producción planta', 'Serie diaria…', 84)
    RECON_PRODUCCION = load_produccion()
    RAW_CURVES_BY_MATERIAL = {'OXIDOS': DATA_OX, 'SULFUROS': DATA_SU}

    # Grilla de estado de Reconciliacion MHE: activa = caudal de riego real
    # reciente (`active_pilas_by_riego`), NO clasificacion de curva de
    # recuperacion -- ver su docstring en recon_engine.py.
    _progress_set('Pilas activas', 'Detectando riego reciente…', 94)
    _ACTIVE_OX = active_pilas_by_riego('OXIDOS', JOINT_DATA_CUTOFF)
    _ACTIVE_SU = active_pilas_by_riego('SULFUROS', JOINT_DATA_CUTOFF)
    _progress_set('Histórico listo', 'Metadatos cargados', 100)




def _filter_selected(selected: list, view_ox: dict, view_su: dict) -> list:
    out = []
    for cid in selected:
        pad_id, num_str = cid.split('-P')
        num = int(num_str)
        view = view_ox if pad_id == 'ox' else view_su
        if not view.get(num, {}).get('disabled', True):
            out.append(cid)
    return out


def empty_figure(message='Selecciona una parcela') -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=CHART_SURFACE, plot_bgcolor=CHART_SURFACE,
        font=dict(color=CHART_INK_PRIMARY, family='Inter, system-ui, sans-serif'),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(
            text=message, showarrow=False,
            font=dict(size=16, color=CHART_INK_MUTED),
        )],
        uirevision='keep',
    )
    return fig


# ── Reconciliacion: helpers ──────────────────────────────────────────────────────

def _clean_nan(x):
    if isinstance(x, dict):
        return {k: _clean_nan(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean_nan(v) for v in x]
    if isinstance(x, float) and np.isnan(x):
        return None
    return x


def _serialize_weeks(weeks: dict) -> dict:
    return _clean_nan({wm.isoformat(): dict(w) for wm, w in weeks.items()})


def _serialize_result(result: dict, wz_base: dict) -> dict:
    weeks = {wm.isoformat(): dict(w) for wm, w in result['weeks'].items()}
    out = dict(
        Fdrena=result['Fdrena'], Fdrena_prior=result['Fdrena_prior'],
        method=result['method'], transient=result['transient'], ss=result['ss'],
        fixed_transient=result['fixed_transient'], active=result['active'],
        weeks=weeks, converged=result['converged'], warnings=result['warnings'],
        R_global=result['R_global'], day_in_cycle=result['day_in_cycle'],
        rec_ratio=result['rec_ratio'], wz=wz_base,
        # Pilas que arrancan en la ventana (ver `arranque_en_ventana`).
        nuevas=result.get('nuevas') or {},
        # Curva de drenaje diaria reconciliada (paso 7). `.get` porque la ruta
        # W/Z no la produce -- ahi Fdrena es un escalar semanal de verdad.
        Fdrena_dia=result.get('Fdrena_dia') or {},
    )
    return _clean_nan(out)


def _combine(data: dict) -> dict:
    """Combina usando las semanas del resultado JOINT (ya sumadas sobre
    materiales); los conteos de pilas provienen de cada sub-resultado."""
    res_s, res_o = data['SULFUROS'], data['OXIDOS']
    combined = data.get('combined', {})
    wm_keys = sorted(combined.keys(), reverse=True)
    rows = []
    for wm in wm_keys:
        w = combined[wm]
        mt_base = w.get('mt_base_t') or 0.0
        mt_opt = w.get('mt_opt_t', w.get('mt_base_t', 0.0)) or 0.0
        rows.append(dict(wm=wm, actual=w.get('actual'), mt_base=mt_base, mt_opt=mt_opt))

    base_wm = max(wm_keys) if wm_keys else None
    base_row = next((r for r in rows if r['wm'] == base_wm), None)
    resid_base = [r['actual'] - r['mt_base'] for r in rows if r['actual'] is not None]
    resid_opt  = [r['actual'] - r['mt_opt']  for r in rows if r['actual'] is not None]
    rmse_b = float(np.sqrt(np.mean(np.array(resid_base) ** 2))) if resid_base else float('nan')
    rmse_o = float(np.sqrt(np.mean(np.array(resid_opt) ** 2))) if resid_opt else float('nan')
    mejora = (1 - rmse_o / rmse_b) * 100 if np.isfinite(rmse_b) and rmse_b else float('nan')
    err_pct = ((base_row['mt_opt'] - base_row['actual']) / base_row['actual'] * 100
               if base_row and base_row['actual'] else float('nan'))

    # Conteo que se muestra arriba: sale de `_status_view`, el MISMO criterio
    # que pinta la grilla, para que el tile y el pad no se contradigan (la
    # grilla ademas exige riego reciente via `active_pilas_by_riego`). El
    # corte TRANS/SS se sigue calculando -- lo necesita el motor -- pero ya
    # no se publica.
    n_act = n_nue = 0
    for res, mx, act in ((res_o, 32, _ACTIVE_OX), (res_s, 28, _ACTIVE_SU)):
        for v in _status_view(res, mx, act).values():
            n_act += v['status'] != 'inactiva'
            n_nue += v['status'] == 'activa_nueva'

    return dict(
        rows=rows, base_row=base_row,
        n_activas=n_act, n_nuevas=n_nue,
        n_reconciliadas=len(res_s['transient']) + len(res_o['transient']),
        rmse_base=rmse_b, rmse_opt=rmse_o, mejora=mejora, err_pct=err_pct,
        R_global=data.get('R_global', 1.0), estimate_scale=data.get('estimate_scale', False),
    )


def _kpi_tile(label, value):
    return html.Div([
        html.Div(label, className='kpi-label'),
        html.Div(value, className='kpi-value'),
    ], className='kpi-tile')


def _fmt_kpi(value, suffix=''):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return 'N/A'
    return f"{value:+.1f}{suffix}" if suffix == '%' else f"{value:.1f}{suffix}"


def _rel_pct(delta, base):
    """delta/base en %, o NaN si no hay base con que normalizar."""
    if delta is None or not base:
        return float('nan')
    return delta / base * 100.0


def _build_kpis(combined: dict, totals: dict = None):
    """Cuatro metricas + conteo de pilas activas. Con dato de planta (metodos que
    reconcilian contra produccion) se muestran Real/Produccion/Err/Mejora;
    el metodo de flowsheet no toca planta -- ahi esos cuatro tiles salian
    todos 'N/A', asi que se cambian por los deltas del balance de caudal y
    Cu fino, que son los que ese metodo si calcula. Los deltas van en % para
    no atribuirles una unidad que el motor no declara."""
    br = combined['base_row'] or {}
    if br.get('actual') is None and totals:
        return html.Div([
            _kpi_tile('Δ caudal riego / medido', _fmt_kpi(_rel_pct(totals.get('delta_recon_riego'),
                                                        totals.get('q_riego_medido')), '%')),
            _kpi_tile('Δ caudal PLS / medido', _fmt_kpi(_rel_pct(totals.get('delta_recon_pls'),
                                                      totals.get('q_pls_medido')), '%')),
            _kpi_tile('Δ Cu fino riego / medido', _fmt_kpi(_rel_pct(totals.get('delta_fino_riego'),
                                                              totals.get('cu_fino_riego_medido')), '%')),
            _kpi_tile('Δ Cu fino PLS / medido', _fmt_kpi(_rel_pct(totals.get('delta_fino_pls'),
                                                            totals.get('cu_fino_pls_medido')), '%')),
            _kpi_tile('Activas / nuevas', f"{combined['n_activas']} / {combined['n_nuevas']}"),
        ], className='kpi-grid')
    return html.Div([
        _kpi_tile('Real t', _fmt_kpi(br.get('actual'))),
        _kpi_tile('Producción t', _fmt_kpi(br.get('mt_opt') if br.get('actual') is not None else None)),
        _kpi_tile('Err %', _fmt_kpi(combined['err_pct'], '%')),
        _kpi_tile('Mejora RMSE', _fmt_kpi(combined['mejora'], '%')),
        _kpi_tile('Activas / nuevas', f"{combined['n_activas']} / {combined['n_nuevas']}"),
    ], className='kpi-grid')


def _week_pila_metrics(conn, label, p, week_start, mat, wz_p, week_end=None,
                       daily_override=None):
    """Metricas medido/reconciliado de UNA pila para la semana reconciliada
    ACTUAL (usadas por el bar chart de subtabs): masa Cu fino (t), caudal
    TOTAL semanal (m3, suma de q*24h) y Cu riego/PLS PROMEDIO semanal (g/L)
    — 'Cu usa media, Flujo usa total' (criterio del usuario).

    La masa reconciliada NO puede reconstruirse solo con Fdrena_reconciliado
    * W - Z (formula de `curve_recalc._extraccion_base`): esa formula asume
    que SOLO Fdrena cambia y Cu_drena queda igual al medido (cierto para
    GEKKO), pero el metodo 'Pendiente' hace lo opuesto — deja Fdrena fijo en
    FDRENA_MAX y corrige Cu_drena dia a dia. Por eso la masa reconciliada se
    recalcula dia a dia desde `reconciliacion_detalle_dia` (fdrena, q,
    cu_drena, cu_riego REALES de esa fila), valido para ambos metodos.

    Prioriza filas diarias reales (la semana recien reconciliada siempre
    las tiene con el rediseno GEKKO/Pendiente); si no hubiera, cae al
    promedio semanal constante x7 de `reconciliacion_detalle`."""
    ws, we, n_days = resolve_window(week_start, week_end)
    days = [ws + pd.Timedelta(days=i) for i in range(n_days)]

    riego_col = mat['riego'][p] if p in mat['riego'].columns else None
    drena_col = mat['drena_cu'][p] if p in mat['drena_cu'].columns else None
    cu_riego_s = mat['cu_riego']
    riego_completo = (riego_col is not None
                      and all(d in mat['riego'].index for d in days))

    q_total_med, cur_med, cud_med = 0.0, [], []
    for d in days:
        q = riego_col.get(d, 0.0) if riego_col is not None else 0.0
        q_total_med += float(q or 0.0) * 24.0
        cr = cu_riego_s.get(d, np.nan)
        if pd.notna(cr):
            cur_med.append(float(cr))
        if drena_col is not None:
            cd = drena_col.get(d, np.nan)
            if pd.notna(cd):
                cud_med.append(float(cd))

    # compute_wz_week devuelve W=Z=0 cuando una pila tuvo riego pero no
    # hay ningun dia con Cu de drenaje medido. Ese cero es falta de evidencia,
    # no una masa medida de cero. Si no hubo riego en la ventana, el cero si es
    # real; si faltan W/Z o el dia completo, se conserva como dato faltante.
    wz_complete = riego_completo and (
        wz_p.get('n_days', 0) > 0 or wz_p.get('n_irr', 0) == 0)
    mass_med = None
    W = float(wz_p['W']) if wz_p.get('W') is not None else None
    Z = float(wz_p['Z']) if wz_p.get('Z') is not None else None
    if wz_complete and W is not None and Z is not None:
        mass_med = FDRENA_MAX * W - Z

    daily = []
    if daily_override is None:
        material_id = get_material_id(conn, label)
        daily_source = load_pila_daily_history(conn, material_id, p)
    else:
        # El callback de calculo acaba de persistir estas mismas filas y
        # `_save_recon_raw` conserva el resultado diario bajo raw_token. Usar
        # esa fuente evita releer/copiar el historial completo del pad por
        # cada pila al construir la barra.
        daily_source = daily_override
    for row in daily_source:
        if _as_date(pd.Timestamp(row['semana_lunes'])) != _as_date(ws):
            continue
        # La tabla retiene la corrida más reciente por lunes, que puede ser
        # otro Caso con un fin distinto. Limitar por offset preserva la
        # ventana exacta seleccionada aunque ambos Casos compartan semana.
        offset = row.get('dia_offset')
        if offset is not None and not 0 <= int(offset) < n_days:
            continue
        daily.append(row)
    if daily:
        q_total_rec = sum(float(r['q'] or 0.0) * 24.0 for r in daily)
        cur_rec = [r['cu_riego'] for r in daily if r['cu_riego'] is not None]
        cud_rec = [r['cu_drena'] for r in daily if r['cu_drena'] is not None]
        mass_rec = sum(
            (float(r['q'] or 0.0) * 24.0 / 1000.0)
            * ((float(r['fdrena']) * float(r['cu_drena'] or 0.0)) - float(r['cu_riego'] or 0.0))
            for r in daily if r['fdrena'] is not None
        )
    else:
        if daily_override is not None:
            material_id = get_material_id(conn, label)
        hist_row = next((r for r in load_pila_history(conn, material_id, p)
                          if _as_date(pd.Timestamp(r['semana_lunes'])) == _as_date(ws)), None)
        if hist_row:
            # Algunos Casos duran ocho días. Este fallback se usa solo para
            # corridas antiguas sin detalle diario, pero debe respetar igual
            # la ventana que el usuario acaba de reconciliar.
            q_total_rec = float(hist_row.get('q_mean') or 0.0) * 24.0 * n_days
            cur_rec = [hist_row['cu_riego_mean']] if hist_row.get('cu_riego_mean') is not None else []
            cud_rec = [hist_row['cu_drena_mean']] if hist_row.get('cu_drena_mean') is not None else []
            fdrena_rec = hist_row.get('fdrena')
            mass_rec = ((fdrena_rec if fdrena_rec is not None else FDRENA_MAX) * W - Z
                        if W is not None and Z is not None else None)
        else:
            q_total_rec, cur_rec, cud_rec, mass_rec = 0.0, [], [], mass_med

    return dict(
        mass_med=mass_med, mass_rec=mass_rec,
        q_total_med=q_total_med if riego_completo else None,
        q_total_rec=q_total_rec,
        cu_riego_med=(sum(cur_med) / len(cur_med)) if cur_med else 0.0,
        cu_riego_rec=(sum(cur_rec) / len(cur_rec)) if cur_rec else 0.0,
        cu_pls_med=(sum(cud_med) / len(cud_med)) if cud_med else 0.0,
        cu_pls_rec=(sum(cud_rec) / len(cud_rec)) if cud_rec else 0.0,
    )


def _pila_recovery_week(conn, material_id, label, num, p, mat, week_start, week_totals, days):
    """{fecha: (recup_medida_%, recup_reconciliada_%)} para los 7 dias de la
    semana. Misma construccion que `_build_recovery_chart`, extraida aqui
    para el reporte -- si diverge, el Excel y el grafico dejan de coincidir.

    El medido es un escalon: `lectura_recuperacion` no es diaria, asi que se
    propaga el ultimo valor <= al dia. El reconciliado sale de
    `pila_curve_v2` y solo existe en dias efectivamente reconciliados (pilas
    TRANS); en SS queda None a proposito, mismo criterio que `_daily_series`
    -- el valor persistido es igual al crudo y publicarlo como "reconciliado"
    sugiere un ajuste que no hubo."""
    out = {d: (None, None) for d in days}
    start_day, end_day = _active_wip_bounds(label, num)
    if start_day is None:
        return out

    cyc = _current_cycle_series(label, num)
    pairs = sorted((_as_date(dt), v) for dt, v in zip(cyc.get('dates') or [], cyc.get('values') or []))
    med = {}
    for d in days:
        dd = _as_date(d)
        last = None
        for pdt, pv in pairs:
            if pdt <= dd:
                last = pv
            else:
                break
        med[d] = last
        out[d] = (last, None)

    cu_tf = (mat['wip'].get(p) or {}).get('CuTf')
    if not cu_tf:
        return out

    hist = load_pila_history(conn, material_id, p)
    if not hist:
        return out
    estado_by_week = {row['semana_lunes']: row['estado'] for row in hist}
    daily_hist = _window_filter(load_pila_daily_history(conn, material_id, p), week_start, days[-1])
    weeks_with_daily = {row['semana_lunes'] for row in daily_hist}
    old_hist = [row for row in _week_filter(hist, week_start)
                if row['semana_lunes'] not in weeks_with_daily]
    daily_lookup = build_daily_lookup(daily_hist, estado_by_week)
    extra_lookup = build_extra_lookup(old_hist, week_totals)
    if not daily_lookup and not extra_lookup:
        return out
    medido_lookup = _medido_cum_lookup(cyc, cu_tf, start_day, end_day)
    series = pila_curve_v2(p, cu_tf, start_day, end_day, end_day, daily_lookup, extra_lookup,
                            mat['riego'], mat['cu_riego'], mat['drena_cu'],
                            medido_lookup=medido_lookup)
    reconciled_days = set(daily_lookup) | set(extra_lookup)
    for d in days:
        dd = _as_date(d)
        if dd in reconciled_days and dd in series:
            out[d] = (med[d], series[dd])
    return out


def _daily_rows(conn, material_id, p, week_start):
    """Filas diarias reconciliadas de UNA pila en la semana `week_start`."""
    ws = _as_date(pd.Timestamp(week_start))
    return [r for r in load_pila_daily_history(conn, material_id, p)
            if _as_date(pd.Timestamp(r['semana_lunes'])) == ws]


def _build_bar(data: dict, tab_value: str) -> go.Figure:
    """Barras por pila (TODAS las activas, ambos materiales) de la semana
    reconciliada actual, medido vs. reconciliado — la magnitud depende del
    subtab activo, igual criterio que el grafico de arriba: 'Curvas' = masa
    Cu fino aportada/producida (t); 'Flujos' = caudal TOTAL semanal (m3);
    'Cus' = Cu riego/PLS PROMEDIO semanal (g/L). Ver `_week_pila_metrics`
    para el detalle de por que la masa reconciliada se recalcula dia a dia
    (valido tanto para GEKKO como para 'Pendiente')."""
    week_start = data.get('week_start')
    if not week_start:
        return go.Figure()

    labels_x, y_med, y_rec, y_med2, y_rec2 = [], [], [], [], []
    ws, we, _n_days = _store_window(data)

    # El token identifica el resultado crudo generado por este mismo click.
    # Solo se usa si Caso y ventana coinciden; para Stores antiguos, expirados
    # o incompletos se conserva el camino historico de DB como fallback.
    daily_by_pile = {}
    raw, _ = _load_recon_raw(data.get('raw_token'), data.get('caso_id'))
    raw_matches = False
    if raw:
        raw_case = raw.get('caso')
        try:
            raw_matches = (
                isinstance(raw_case, dict)
                and data.get('caso_run_id') is not None
                and raw_case.get('run_id') == data.get('caso_run_id')
                and _as_date(pd.Timestamp(raw.get('ws'))) == _as_date(ws)
                and _as_date(pd.Timestamp(raw.get('we'))) == _as_date(we)
            )
        except (TypeError, ValueError, OverflowError):
            raw_matches = False
    if raw_matches:
        raw_res = raw.get('res')
        raw_daily = raw_res.get('daily') if isinstance(raw_res, dict) else None
        if isinstance(raw_daily, list):
            parsed = {}
            valid = True
            for row in raw_daily:
                try:
                    date = _as_date(pd.Timestamp(row['date']))
                    offset = (date - _as_date(ws)).days
                    if not 0 <= offset < _n_days:
                        valid = False
                        break
                    q = float(row['q_riego_final'] or 0.0)
                    q_pls = float(row['q_pls_final'] or 0.0)
                    parsed.setdefault((row['label'], row['parcela']), []).append({
                        'semana_lunes': ws, 'dia_offset': offset,
                        'fdrena': q_pls / q if q else FDRENA_MAX,
                        'q': q, 'q_pls': q_pls,
                        'cu_drena': row.get('cu_pls_recon'),
                        'cu_riego': row.get('cu_riego_recon'),
                    })
                except (KeyError, TypeError, ValueError):
                    valid = False
                    break
            if valid:
                daily_by_pile = parsed

    needs_db_history = any(
        not daily_by_pile.get((label, p))
        for label in ('OXIDOS', 'SULFUROS')
        for p in data.get(label, {}).get('active', [])
    )

    conn = connect() if needs_db_history else None
    try:
        for label, short in (('OXIDOS', 'Ox'), ('SULFUROS', 'Su')):
            sub = data.get(label, {})
            mat = _load_material_window(label, ws, we)
            active = sub.get('active', [])
            wz = sub.get('wz', {})
            for p in active:
                labels_x.append(f'{short}-{p}')
                m = _week_pila_metrics(
                    conn, label, p, ws, mat, wz.get(p, {}), week_end=we,
                    daily_override=daily_by_pile.get((label, p)),
                )
                if tab_value == 'tab-flujo':
                    y_med.append(m['q_total_med'])
                    y_rec.append(m['q_total_rec'])
                elif tab_value == 'tab-cus':
                    y_med.append(m['cu_riego_med'])
                    y_rec.append(m['cu_riego_rec'])
                    y_med2.append(m['cu_pls_med'])
                    y_rec2.append(m['cu_pls_rec'])
                else:
                    y_med.append(m['mass_med'])
                    y_rec.append(m['mass_rec'])
    finally:
        if conn is not None:
            conn.close()

    fig = go.Figure()
    if tab_value == 'tab-cus':
        fig.add_trace(go.Bar(x=labels_x, y=y_med, name='Cu riego (medido)', marker_color='#9CA3AF'))
        fig.add_trace(go.Bar(x=labels_x, y=y_rec, name='Cu riego (reconciliado)', marker_color='#2a78d6'))
        fig.add_trace(go.Bar(x=labels_x, y=y_med2, name='Cu PLS (medido)', marker_color='#6B7280'))
        fig.add_trace(go.Bar(x=labels_x, y=y_rec2, name='Cu PLS (reconciliado)', marker_color='#E86D1F'))
        y_title = 'Media aritmética diaria (g/L)'
    elif tab_value == 'tab-flujo':
        fig.add_trace(go.Bar(x=labels_x, y=y_med, name='Caudal (medido)', marker_color='#9CA3AF'))
        fig.add_trace(go.Bar(x=labels_x, y=y_rec, name='Caudal (reconciliado)', marker_color='#E86D1F'))
        y_title = 'Q total semana (m³)'
    else:
        fig.add_trace(go.Bar(x=labels_x, y=y_med, name='Cu fino (medido)', marker_color='#9CA3AF'))
        fig.add_trace(go.Bar(x=labels_x, y=y_rec, name='Cu fino (reconciliado)', marker_color='#E86D1F'))
        y_title = 'Cu fino (t)'

    fig.update_layout(
        barmode='group', paper_bgcolor=CHART_SURFACE, plot_bgcolor=CHART_SURFACE,
        font=dict(color='#1F2429'), yaxis_title=y_title,
        legend=dict(bgcolor='rgba(0,0,0,0)'), hovermode='x unified', uirevision='keep',
        margin=dict(l=50, r=20, t=20, b=60),
        yaxis=dict(gridcolor='#E5E7EB'), xaxis=dict(gridcolor='#E5E7EB', tickangle=-45),
    )
    return fig


def _status_view(res: dict, max_num: int, active_set: set) -> dict:
    """Estado de cada pila para la grilla: activa / activa nueva / inactiva.

    Ya no se marca transiente vs estado estacionario. Esa division sigue
    existiendo dentro del motor -- es la que decide a que pilas se les reparte
    la correccion de caudal -- pero no es lo que se lee en el pad.

    ACTIVA NUEVA es la que ARRANCA DENTRO DE LA VENTANA: primer dia de riego
    adentro del periodo, sin riego ni Cu++ de drenaje en los 30 dias previos.
    El set lo calcula el motor (`recon_engine.arranque_en_ventana`) y es el
    MISMO con el que decide a quien le toca ramp-up y a quien curva plana, asi
    que lo pintado y lo calculado no se pueden separar.

    Antes esto se decidia con `dia_ciclo <= n_days`, o sea con la campana de
    `lectura_recuperacion`: esa tabla no tiene junio ni julio 2026 y abre la
    campana 18 el 2026-08-01 para todo el pad, con lo que el Caso 21 mostraba
    37 pilas "nuevas" el mismo dia.
    """
    nuevas = set(res.get('nuevas') or ())
    reconciliadas = set(res.get('transient') or ()) | set(res.get('ss') or ())
    view = {}
    for n in range(1, max_num + 1):
        p = f'P{n:02d}'
        if n not in active_set or p not in reconciliadas:
            view[n] = dict(status='inactiva', disabled=True)
            continue
        view[n] = dict(status=('activa_nueva' if p in nuevas else 'activa'), disabled=False)
    return view


def _build_status_grid(res_s: dict, res_o: dict, n_days: int, selected_pila=None):
    selected = [selected_pila] if selected_pila else []
    view_o = _status_view(res_o, 32, _ACTIVE_OX)
    view_s = _status_view(res_s, 28, _ACTIVE_SU)
    pad_o = html.Div(
        build_pad('rox', 'PAD Óxido — Estado', TOP_OX, BOTTOM_OX, view_o, selected,
                  color_map=RECON_STATUS_COLORS, id_type='curvas-recon-cell'),
        className='pad-panel',
    )
    pad_s = html.Div(
        build_pad('rsu', 'PAD Sulfuro — Estado', TOP_SU, BOTTOM_SU, view_s, selected,
                  color_map=RECON_STATUS_COLORS, id_type='curvas-recon-cell'),
        className='pad-panel',
    )
    legend = html.Div([
        html.Span('● Activa', style={'color': RECON_STATUS_COLORS['activa'], 'marginRight': '12px'}),
        html.Span('● Activa nueva (primer riego dentro del periodo)',
                   style={'color': RECON_STATUS_COLORS['activa_nueva'], 'marginRight': '12px'}),
        html.Span('● No activa', style={'color': RECON_STATUS_COLORS['inactiva']}),
        html.Span('  (click en una pila activa para comparar medido vs. reconciliado)',
                   style={'color': '#6B7280', 'fontStyle': 'italic'}),
    ], className='pad-legend')
    return html.Div([legend, html.Div([pad_o, pad_s], className='pad-grid')])


def _build_warnings(data: dict):
    """Avisos del run, con el pad que los origina como etiqueta.

    El motor ya rutea: `data['warnings']` trae SOLO los globales (tope de
    Fdrena del ancla, balance incerrable, caso sin run oficializado) y cada
    material trae los suyos. Antes las tres listas eran la misma lista unida,
    asi que el dedupe vaciaba las dos ramas de pad y todo salia [GLOBAL].
    El texto del motor ya empieza con 'LABEL: ' / 'LABEL/Pxx', que aqui
    duplicaria la etiqueta, asi que se recorta el prefijo redundante."""
    joint_w = list(data.get('warnings', []))
    balance = data.get('balance_inventario') or {}
    volumen = float(balance.get('volumen_m3') or 0.)
    cobre = float(balance.get('cobre_t') or 0.)
    if abs(volumen) > 1e-6 or abs(cobre) > 1e-6:
        joint_w.insert(0,
            f'Balance pendiente de inventario: {volumen:+,.2f} m³ de solución '
            f'y {cobre:+,.3f} t Cu. Positivo: aporte requerido; negativo: '
            f'retención requerida. Disponibilidad física sin verificar. '
            f'Este término no se atribuye a la recuperación de las pilas.')
    joint_set = set(joint_w)
    msgs = [('GLOBAL', w) for w in joint_w]
    for label in ('SULFUROS', 'OXIDOS'):
        for w in data.get(label, {}).get('warnings', []):
            if w in joint_set:
                continue
            if w.startswith(label + ': '):
                w = w[len(label) + 2:]
            msgs.append((label, w))
    if not msgs:
        return None
    return html.Div(
        [html.Div([html.Span(tag, className='warning-tag'), html.Span(w)], className='warning-item')
         for tag, w in msgs],
        className='warning-list')


_PAD_TO_LABEL = {'rox': 'OXIDOS', 'rsu': 'SULFUROS'}


def _current_cycle_series(label, num):
    """Ciclo VIGENTE de una pila (el ultimo de `split_into_cycles`).

    NO usar `_view_data(cycles_map, MAX_CAMPANAS)`: MAX_CAMPANAS es el maximo
    GLOBAL de campanas sobre todas las pilas (hoy 7), asi que pedirle esa
    campana a una pila que solo tuvo 5 devolvia 'sin_datos'. Con eso las 32
    pilas de OXIDO y 23 de las 28 de SULFURO caian en el branch vacio y los
    tres graficos por pila salian sin trazas. El ciclo vigente es siempre el
    ULTIMO de la lista, sin importar cuantos tenga esa pila.

    El estado sale del mismo criterio que la grilla (`active_pilas_by_riego`),
    no de `cyc['finished']`: `lectura_recuperacion` se sincroniza aparte de
    riego/drenaje y puede ir semanas atrasada, lo que marcaria como inactiva
    una pila que si esta regando."""
    cycles = (CYCLES_OX if label == 'OXIDOS' else CYCLES_SU).get(num) or []
    if not cycles:
        return {}
    cyc = cycles[-1]
    active = _ACTIVE_OX if label == 'OXIDOS' else _ACTIVE_SU
    return dict(status=('activa' if num in active else 'inactiva'), disabled=False,
                dates=cyc['dates'], values=cyc['values'])


def _active_wip_bounds(label, num):
    """(inicio_ciclo_vigente, fin_ventana) de una pila activa.

    El inicio sale de `_current_cycle_series` (ciclo vigente segun
    `pad_cycles.split_into_cycles`), NO del WIP crudo: el WIP puede apuntar a
    un ciclo ya terminado si esta desactualizado respecto a la fuente de
    reconciliacion -> usarlo mezclaria mas de un ciclo bajo el mismo CuTf e
    inflaria el % muy por encima de lo real.

    El fin se extiende hasta JOINT_DATA_CUTOFF en vez de quedarse en la
    ultima lectura de recuperacion. `lectura_recuperacion` va atrasada
    respecto a riego/drenaje, asi que cortar ahi dejaba la semana recien
    reconciliada FUERA de la ventana y la traza reconciliada no se dibujaba
    nunca. Retorna (None, None) si la pila no esta activa o no tiene curva."""
    cyc = _current_cycle_series(label, num)
    dates = cyc.get('dates')
    if not dates or cyc.get('status') != 'activa':
        return None, None
    return dates[0], max(dates[-1], _as_date(JOINT_DATA_CUTOFF))


def _clip_series(s, start_day, end_day):
    """Recorta una Serie con indice datetime64 a [start_day, end_day]
    (`datetime.date`). Comparar un DatetimeIndex contra `date` crudo lanza
    TypeError en pandas -> siempre normalizar a Timestamp primero."""
    if start_day is None or s is None or len(s) == 0:
        return s
    idx = s.index
    start_ts, end_ts = pd.Timestamp(start_day), pd.Timestamp(end_day)
    return s[(idx >= start_ts) & (idx <= end_ts)]


def _medido_cum_lookup(cyc, cu_tf, start_day, end_day):
    """{date: cum_cu} = pct medido (`cyc['dates']`/`cyc['values']`, ver
    `_current_cycle_series`) convertido a t Cu acumulado y propagado
    (forward-fill) a cada dia calendario del rango -- usado por
    `pila_curve_v2` para sincronizar el acumulado reconciliado en dias sin
    reconciliacion real, en vez de dejarlo divergir con la formula
    promedio-expandido (ver fix de "curvas SS/pre-ancla mostrando ajuste
    donde no hubo ninguno")."""
    dates, values = cyc.get('dates') or [], cyc.get('values') or []
    cu_tf_t = cu_tf_toneladas(cu_tf)
    if not dates or cu_tf_t is None:
        return {}
    pairs = sorted(zip(dates, values))
    out = {}
    # El dia previo al tramo no tiene lectura propia: se rellena con la
    # PRIMERA del tramo, no con cero. La curva medida de una pila madura
    # arranca el tramo en 69 %, no en 0, y ese es el nivel del que parte el
    # acumulado reconciliado. Para una pila nueva la primera lectura es ~0 y
    # el relleno no cambia nada.
    idx, last_val = 0, (pairs[0][1] if pairs else 0.0)
    # Arranca un dia ANTES del tramo: ese valor es la base con la que
    # `pila_curve_v2` siembra su acumulado (el medido del dia d ya incluye la
    # extraccion del dia d, asi que sumarle encima la del dia d reconciliado
    # contaria ese dia dos veces).
    d = start_day - timedelta(days=1)
    while d <= end_day:
        while idx < len(pairs) and pairs[idx][0] <= d:
            last_val = pairs[idx][1]
            idx += 1
        out[d] = last_val / 100.0 * cu_tf_t
        d += timedelta(days=1)
    return out


def _weekly_step_series(hist, field, n_days=7):
    """Expande cada corrida anclada (valor reconciliado constante) en sus
    dias reales, en vez de un segmento de 2 puntos. Usado SOLO como fallback para
    semanas ancladas ANTES del rediseno diario (sin filas en
    `reconciliacion_detalle_dia`) — ver `_daily_series`."""
    xs, ys = [], []
    for row in hist:
        wk = pd.Timestamp(row['semana_lunes'])
        val = row[field]
        for i in range(n_days):
            xs.append(wk + pd.Timedelta(days=i))
            ys.append(val)
    return xs, ys


def _week_filter(rows, week_start):
    """Restringe `rows` (dicts con 'semana_lunes') a la UNICA semana anclada
    `week_start` -- el ajuste MHE/Pendiente es por semana, no acumulativo;
    mostrar semanas ya pasadas mezcladas con la actual confunde cual es el
    ajuste vigente (mas de 7 puntos, semana resaltada sin datos encima).
    Sin `week_start`, retorna `rows` sin filtrar (comportamiento anterior)."""
    if not week_start:
        return rows
    ws = str(pd.Timestamp(week_start).date())
    return [row for row in rows if str(pd.Timestamp(row['semana_lunes']).date()) == ws]


def _daily_series(conn, material_id, p, hist, field_daily, field_weekly_mean,
                  week_start=None, week_end=None):
    """Serie reconciliada real dia-a-dia de la UNICA semana anclada
    `week_start` (un punto por día si TRANS y con tabla diaria; escalon semanal
    constante si es una semana anclada ANTES del rediseno
    GEKKO/Pendiente sin filas en `reconciliacion_detalle_dia`; vacio si esa
    semana es SS -- el valor persistido ya es igual al crudo, delta=0, dibujar
    la traza igual solo superpondria "reconciliado" sobre medido sin ajuste
    real). Retorna (xs, ys) ordenado por fecha."""
    estado_by_week = {row['semana_lunes']: row['estado'] for row in hist}
    daily_hist_all = _window_filter(load_pila_daily_history(conn, material_id, p), week_start, week_end)
    weeks_with_daily = {row['semana_lunes'] for row in daily_hist_all}
    daily_hist = [row for row in daily_hist_all if estado_by_week.get(row['semana_lunes']) == 'TRANS']
    xs = [pd.Timestamp(row['semana_lunes']) + pd.Timedelta(days=row['dia_offset']) for row in daily_hist]
    ys = [row[field_daily] for row in daily_hist]

    old_hist = [row for row in _week_filter(hist, week_start)
                if row['semana_lunes'] not in weeks_with_daily and row['estado'] == 'TRANS']
    n_days = resolve_window(week_start, week_end)[2] if week_start else 7
    ox, oy = _weekly_step_series(old_hist, field_weekly_mean, n_days)
    xs.extend(ox)
    ys.extend(oy)

    pairs = sorted(zip(xs, ys), key=lambda t: t[0])
    return [x for x, _ in pairs], [y for _, y in pairs]


def _add_week_zoom_box(fig, week_start, week_end=None):
    """Resalta la ventana reconciliada con un rectangulo translucido sobre el
    eje x — referencia visual rapida de donde cae el ajuste dentro de la
    serie completa. La ventana es la del Caso, no 7 dias fijos."""
    if not week_start:
        return
    ws, we, _n = resolve_window(week_start, week_end)
    fig.add_vrect(x0=ws, x1=we + pd.Timedelta(days=1), fillcolor='#E86D1F', opacity=0.08,
                  line_width=1, line_color='#E86D1F', layer='below',
                  row='all', col='all')


def _stacked_figure(top_title, bottom_title):
    """Dos paneles apilados con eje x compartido: riego arriba, PLS abajo.
    Reemplaza el eje derecho superpuesto (`yaxis2`) que mezclaba dos rangos
    independientes en un solo panel."""
    return make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                         subplot_titles=(top_title, bottom_title))


def _build_pila_chart(selected_pila, week_start=None, week_end=None) -> go.Figure:
    """Medido (diario, solo ciclo activo) vs. reconciliado (escalon semanal,
    constante dentro de cada semana ya anclada) para la pila seleccionada en
    la grilla de estado — Cu riego (planta, por material, panel superior) y
    Cu PLS (por pila, panel inferior) — paneles separados porque cada uno se
    mueve en su propio rango independiente."""
    if not selected_pila:
        return empty_figure()
    pad_id, num_str = selected_pila.split('-P')
    p = f'P{int(num_str):02d}'
    label = _PAD_TO_LABEL.get(pad_id)
    if label is None or p not in WIP_META.get(label, {}):
        return empty_figure()

    start_day, end_day = _active_wip_bounds(label, int(num_str))
    if start_day is None:
        return empty_figure()
    mat = _load_material_window(label, start_day, end_day)
    if p not in mat['drena_cu'].columns:
        return empty_figure()

    cu_riego_s = _clip_series(mat['cu_riego'], start_day, end_day)
    cu_drena_s = _clip_series(mat['drena_cu'][p].dropna(), start_day, end_day)

    conn = connect()
    try:
        material_id = get_material_id(conn, label)
        hist = load_pila_history(conn, material_id, p)
        if hist:
            rx, ry = _daily_series(conn, material_id, p, hist, 'cu_riego', 'cu_riego_mean',
                                   week_start, week_end)
            px, py = _daily_series(conn, material_id, p, hist, 'cu_drena', 'cu_drena_mean',
                                   week_start, week_end)
    finally:
        conn.close()

    fig = _stacked_figure('Cu riego', 'Cu PLS')
    fig.add_trace(go.Scatter(x=cu_riego_s.index, y=cu_riego_s.values, mode='lines',
                              name='Cu riego (medido)', line=dict(color='#2a78d6', width=1.5, dash='dash')),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=cu_drena_s.index, y=cu_drena_s.values, mode='lines',
                              name='Cu PLS (medido)', line=dict(color='#E86D1F', width=1.5, dash='dash')),
                  row=2, col=1)

    if hist:
        fig.add_trace(go.Scatter(x=rx, y=ry, mode='lines+markers', name='Cu riego (reconciliado)',
                                  line=dict(color='#2a78d6', width=3), marker=dict(size=6)),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=px, y=py, mode='lines+markers', name='Cu PLS (reconciliado)',
                                  line=dict(color='#E86D1F', width=3), marker=dict(size=6)),
                      row=2, col=1)

    _add_week_zoom_box(fig, week_start, week_end)

    fig.update_layout(
        title=f'{label} — {p}: Cu riego / Cu PLS — medido vs. reconciliado',
        paper_bgcolor=CHART_SURFACE, plot_bgcolor=CHART_SURFACE,
        font=dict(color=CHART_INK_PRIMARY, family='Inter, system-ui, sans-serif'),
        legend=dict(bgcolor='rgba(0,0,0,0)'),
        hovermode='x unified', uirevision='keep',
        margin=dict(l=50, r=30, t=60, b=40), height=640,
        xaxis=dict(gridcolor='#E5E7EB'), xaxis2=dict(gridcolor='#E5E7EB'),
        yaxis=dict(title='Cu riego (g/L)', gridcolor='#E5E7EB'),
        yaxis2=dict(title='Cu PLS (g/L)', gridcolor='#E5E7EB'),
    )
    return fig


def _daily_drena_series(conn, material_id, p, hist, week_start=None, week_end=None):
    """Caudal PLS/drenado reconciliado, dia a dia, de la UNICA semana anclada
    `week_start`. Usa `q_pls` persistido (variable propia, independiente de
    Q riego, no derivada de Fdrena*Q) cuando existe; si es
    NULL (corridas ancladas antes de introducir Q PLS propio) cae a
    Fdrena*Q como aproximacion. Mismo patron de fallback/filtro SS que
    `_daily_series`."""
    estado_by_week = {row['semana_lunes']: row['estado'] for row in hist}
    daily_hist_all = _window_filter(load_pila_daily_history(conn, material_id, p), week_start, week_end)
    weeks_with_daily = {row['semana_lunes'] for row in daily_hist_all}
    daily_hist = [row for row in daily_hist_all if estado_by_week.get(row['semana_lunes']) == 'TRANS']
    xs = [pd.Timestamp(row['semana_lunes']) + pd.Timedelta(days=row['dia_offset']) for row in daily_hist]
    ys = [row['q_pls'] if row['q_pls'] is not None else (row['q'] or 0.0) * (row['fdrena'] or 0.0)
          for row in daily_hist]

    old_hist = [row for row in _week_filter(hist, week_start)
                if row['semana_lunes'] not in weeks_with_daily and row['estado'] == 'TRANS']
    for row in old_hist:
        wk = pd.Timestamp(row['semana_lunes'])
        val = row['q_pls_mean'] if row['q_pls_mean'] is not None else (row['q_mean'] or 0.0) * (row['fdrena'] or 0.0)
        n_days = resolve_window(week_start, week_end)[2] if week_start else 7
        for i in range(n_days):
            xs.append(wk + pd.Timedelta(days=i))
            ys.append(val)

    pairs = sorted(zip(xs, ys), key=lambda t: t[0])
    return [x for x, _ in pairs], [y for _, y in pairs]


def _build_flujo_chart(selected_pila, week_start=None, week_end=None) -> go.Figure:
    """Caudal riego medido (diario, solo ciclo activo) vs. reconciliado (7
    dias por semana ya anclada), panel superior, y caudal PLS medido
    (FDRENA_MAX * riego medido, sin sensor propio) vs. reconciliado en panel
    inferior para la pila seleccionada."""
    if not selected_pila:
        return empty_figure()
    pad_id, num_str = selected_pila.split('-P')
    p = f'P{int(num_str):02d}'
    label = _PAD_TO_LABEL.get(pad_id)
    if label is None or p not in WIP_META.get(label, {}):
        return empty_figure()

    start_day, end_day = _active_wip_bounds(label, int(num_str))
    if start_day is None:
        return empty_figure()
    mat = _load_material_window(label, start_day, end_day)
    if p not in mat['riego'].columns:
        return empty_figure()

    q_s = _clip_series(mat['riego'][p].dropna(), start_day, end_day)
    # Q PLS medido no tiene sensor propio -- mismo criterio usado en todo el
    # resto del modulo de reconciliacion (`_build_piles`, `_distribute_daily_pile`):
    # Q_pls_medido = FDRENA_MAX * Q_riego_medido.
    q_pls_s = q_s * FDRENA_MAX

    conn = connect()
    try:
        material_id = get_material_id(conn, label)
        hist = load_pila_history(conn, material_id, p)
        if hist:
            qx, qy = _daily_series(conn, material_id, p, hist, 'q', 'q_mean', week_start, week_end)
            dx, dy = _daily_drena_series(conn, material_id, p, hist, week_start, week_end)
    finally:
        conn.close()

    fig = _stacked_figure('Caudal riego', 'Caudal PLS')
    fig.add_trace(go.Scatter(x=q_s.index, y=q_s.values, mode='lines',
                              name='Caudal riego (medido)', line=dict(color='#2a78d6', width=1.5, dash='dash')),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=q_pls_s.index, y=q_pls_s.values, mode='lines',
                              name='Caudal PLS (medido)', line=dict(color='#E86D1F', width=1.5, dash='dash')),
                  row=2, col=1)

    if hist:
        fig.add_trace(go.Scatter(x=qx, y=qy, mode='lines+markers', name='Caudal riego (reconciliado)',
                                  line=dict(color='#2a78d6', width=3), marker=dict(size=6)),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=dx, y=dy, mode='lines+markers', name='Caudal PLS (reconciliado)',
                                  line=dict(color='#E86D1F', width=3), marker=dict(size=6)),
                      row=2, col=1)

    _add_week_zoom_box(fig, week_start, week_end)

    fig.update_layout(
        title=f'{label} — {p}: Caudal — medido vs. reconciliado',
        paper_bgcolor=CHART_SURFACE, plot_bgcolor=CHART_SURFACE,
        font=dict(color=CHART_INK_PRIMARY, family='Inter, system-ui, sans-serif'),
        legend=dict(bgcolor='rgba(0,0,0,0)'),
        hovermode='x unified', uirevision='keep',
        margin=dict(l=50, r=30, t=60, b=40), height=640,
        xaxis=dict(gridcolor='#E5E7EB'), xaxis2=dict(gridcolor='#E5E7EB'),
        yaxis=dict(title='Q riego (m³/h)', gridcolor='#E5E7EB'),
        yaxis2=dict(title='Q PLS (m³/h)', gridcolor='#E5E7EB'),
    )
    return fig


def _window_filter(rows, week_start, week_end=None):
    """Restringe filas reconciliadas a la ventana del Caso.

    Filas SEMANALES (sin `dia_offset`): se quedan si su `semana_lunes` cae
    dentro de [ws, we]. Filas DIARIAS: se quedan si el dia real
    (`semana_lunes + dia_offset`) cae dentro. Sin `week_start` no filtra."""
    if not week_start:
        return rows
    ws, we, _n = resolve_window(week_start, week_end)
    out, por_dia = [], {}
    for row in rows:
        d = pd.Timestamp(row['semana_lunes']).normalize()
        if row.get('dia_offset') is None:
            if ws <= d <= we:
                out.append(row)
            continue
        dia = d + pd.Timedelta(days=int(row['dia_offset']))
        if not (ws <= dia <= we):
            continue
        # Cada corrida persiste un dia MAS alla de su `semana_fin` (el dia
        # operacional que cierra a las 08:00 siguientes), asi que el primer
        # dia de un Caso viene dos veces: la cola del Caso anterior y el
        # arranque del propio. Se queda el del Caso mas reciente (mayor
        # `semana_lunes`); sin esto `build_daily_lookup` tomaba el que
        # llegara ultimo de la base, al azar.
        prev = por_dia.get(dia)
        if prev is None or d > pd.Timestamp(prev['semana_lunes']).normalize():
            por_dia[dia] = row
    out.extend(por_dia[k] for k in sorted(por_dia))
    return out


def recovery_series(label, num, week_start=None, week_end=None):
    """Curva medida (ciclo activo completo) y reconciliada ACOTADA a la
    ventana del Caso para una pila.

    Devuelve dict con `cyc` (medido: dates/values), `xs`/`ys` (reconciliado,
    solo dias dentro de [ws-1, we]; el dia previo es la base medida desde la
    que arranca el acumulado), `capped` (toco 100 %) y `cu_tf`. Si la pila no
    tiene ciclo activo o CuTf, `xs` sale vacio.

    La reconciliacion es POR CASO: fuera de su ventana no hay ajuste, asi que
    dibujar dias reconciliados de otros Casos mezclaba ajustes distintos bajo
    una misma linea y mostraba mas datos de los que el Caso seleccionado
    realmente produce. Solo se usan las filas semanales/diarias que caen en
    la ventana; el resto de dias `pila_curve_v2` los sincroniza al medido."""
    p = f'P{num:02d}'
    vacio = dict(cyc={'dates': [], 'values': []}, xs=[], ys=[], capped=False, cu_tf=None)
    start_day, end_day = _active_wip_bounds(label, num)
    if start_day is None:
        return vacio
    mat = _load_material_window(label, start_day, end_day)
    cyc = _current_cycle_series(label, num)
    out = dict(vacio, cyc=cyc)

    info = mat['wip'].get(p, {})
    cu_tf = info.get('CuTf')
    out['cu_tf'] = cu_tf
    if not cu_tf:
        return out

    conn = connect()
    try:
        material_id = get_material_id(conn, label)
        hist = _window_filter(load_pila_history(conn, material_id, p), week_start, week_end)
        week_totals = load_week_totals(conn)
        daily_hist = _window_filter(load_pila_daily_history(conn, material_id, p),
                                    week_start, week_end)
    finally:
        conn.close()

    riego, cu_riego, drena_cu = mat['riego'], mat['cu_riego'], mat['drena_cu']
    estado_by_week = {row['semana_lunes']: row['estado'] for row in hist}
    weeks_with_daily = {row['semana_lunes'] for row in daily_hist}
    old_hist = [row for row in hist if row['semana_lunes'] not in weeks_with_daily]
    daily_lookup = build_daily_lookup(daily_hist, estado_by_week)
    extra_lookup = build_extra_lookup(old_hist, week_totals)
    medido_lookup = _medido_cum_lookup(cyc, cu_tf, start_day, end_day)
    series = pila_curve_v2(p, cu_tf, start_day, end_day, end_day, daily_lookup, extra_lookup,
                           riego, cu_riego, drena_cu, medido_lookup=medido_lookup)
    reconciled_days = set(daily_lookup) | set(extra_lookup)
    if not reconciled_days:
        return out
    # Se incluye el dia previo al primer reconciliado para que la linea
    # arranque visiblemente desde la base medida y no flote en el aire.
    d0 = min(reconciled_days) - timedelta(days=1)
    d1 = max(reconciled_days)
    xs = sorted(d for d in series if d0 <= d <= d1)
    ys = [series[x] for x in xs]
    out.update(xs=xs, ys=ys, capped=bool(ys) and max(ys) >= 99.999)
    return out


def _reconstructed_campaign_series(label, num, week_start, week_end, raw=None):
    """Recuperación histórica neta; gaps permanecen como None.

    Fuera del Caso comparte con report_metodo la base FDRENA_MAX=0.95; dentro
    del Caso usa únicamente los flujos diarios de la corrida validada.
    """
    empty = {'xs': [], 'ys': [], 'sources': [], 'cu_tf': None, 'capped': False}
    p = f'P{num:02d}'
    info = WIP_META.get(label, {}).get(p) or {}
    cu_tf = info.get('CuTf')
    cu_tf_t = cu_tf_toneladas(cu_tf)
    try:
        ws, we = pd.Timestamp(week_start).normalize(), pd.Timestamp(week_end).normalize()
    except (TypeError, ValueError):
        return empty
    if cu_tf_t is None or pd.isna(ws) or pd.isna(we) or we < ws:
        return empty
    measured = _measured_cycles(label, num)
    try:
        start = pd.Timestamp(info.get('ini_aporte'))
    except (TypeError, ValueError):
        start = pd.NaT
    if pd.isna(start):
        # Sin inicio de campaña válido no atribuimos lecturas viejas a WIP.
        # Solo se permite extender desde el tramo medido más reciente.
        if not measured or not measured[-1].get('dates'):
            return empty
        start = pd.Timestamp(measured[-1]['dates'][0]).normalize()
    else:
        start = start.normalize()
    anchors = []
    for cycle in measured:
        for day, pct in zip(cycle.get('dates') or [], cycle.get('values') or []):
            day = pd.Timestamp(day).normalize()
            try:
                pct = float(pct)
            except (TypeError, ValueError):
                continue
            if start <= day < ws and np.isfinite(pct):
                anchors.append((day, pct))
    if anchors:
        anchor, pct = max(anchors, key=lambda x: x[0])
        cum_cu = pct * cu_tf_t / 100.0
        first = anchor + pd.Timedelta(days=1)
        xs, ys, sources = [anchor], [pct], ['medido (ancla)']
    else:
        first, cum_cu = start, 0.0
        xs, ys, sources = [], [], []
    end = min(we, pd.Timestamp(JOINT_DATA_CUTOFF).normalize()) if JOINT_DATA_CUTOFF is not None else we
    if end < first:
        return empty
    mat = _load_material_window(label, first, end)
    riego, cu_riego, drena_cu = mat['riego'], mat['cu_riego'], mat['drena_cu']
    reconciled = {}
    if isinstance(raw, dict):
        for pile in (raw.get('res') or {}).get('piles', []):
            parcela = pile.get('parcela', pile.get('p'))
            if isinstance(parcela, str):
                parcela = parcela.strip().upper().removeprefix('P')
            try:
                parcela_num = int(parcela)
            except (TypeError, ValueError):
                continue
            if pile.get('label', label) != label or parcela_num != num:
                continue
            for row in pile.get('daily', []):
                try:
                    d = pd.Timestamp(row['date']).normalize()
                    fp, fr = row.get('fino_pls_final'), row.get('fino_riego_final')
                    if fp is not None and fr is not None and np.isfinite(float(fp)) and np.isfinite(float(fr)):
                        reconciled[d] = (float(fp) - float(fr)) * 0.024
                except (KeyError, TypeError, ValueError):
                    continue
    from . import report_metodo
    d = first
    while d <= end:
        source, inc = 'Medido', None
        if ws <= d <= we and isinstance(raw, dict):
            source, inc = 'Reconciliado del Caso', reconciled.get(d)
        elif d in riego.index and p in riego.columns:
            q = riego.at[d, p]
            cd = drena_cu.at[d, p] if p in drena_cu.columns and d in drena_cu.index else None
            cr = cu_riego.at[d] if d in cu_riego.index else None
            inc = report_metodo.net_recovery_increment(q, cd, cr)
        if inc is not None and np.isfinite(inc):
            cum_cu += float(inc)
            value = cum_cu / cu_tf_t * 100.0
        else:
            value = None
        xs.append(d)
        ys.append(value)
        sources.append(source)
        d += pd.Timedelta(days=1)
    valid = [v for v in ys if v is not None and np.isfinite(v)]
    return dict(xs=xs, ys=ys, sources=sources, cu_tf=cu_tf,
                capped=bool(valid) and max(valid) >= 100.0)


def _measured_cycles(label, num):
    cycles = (CYCLES_OX if label == 'OXIDOS' else CYCLES_SU).get(num) or []
    return [cycle for cycle in cycles if cycle.get('dates')]


def _operational_activity_in_window(label, num, week_start, week_end):
    """Whether cached operations or a WIP start support activity in a Case."""
    try:
        ws, we = pd.Timestamp(week_start).normalize(), pd.Timestamp(week_end).normalize()
        if pd.isna(ws) or pd.isna(we) or we < ws:
            return False
        riego_by_pile, drena_by_pile = _fechas_actividad(label)
        p = f'P{num:02d}'
        for mapping in (riego_by_pile, drena_by_pile):
            for value in mapping.get(p, ()):
                day = pd.Timestamp(value).normalize()
                if pd.notna(day) and ws <= day <= we:
                    return True
        info = WIP_META.get(label, {}).get(p) or {}
        start = pd.Timestamp(info.get('ini_aporte'))
        return bool(pd.notna(start) and ws <= start.normalize() <= we)
    except Exception:
        return False


def _measured_cycles_active_in_window(label, num, week_start, week_end):
    """Select measured curves belonging to operational campaigns active in a Case.

    Operational campaigns follow the existing 30-day gap rule over the union
    of positive irrigation and drain-Cu dates. A stale last recovery reading
    does not close a campaign: its curve is retained when its readings belong
    to the same uninterrupted operational activity group as the Case window.
    Full curve traces are returned without clipping their dates.
    """
    cycles = _measured_cycles(label, num)
    if not cycles:
        return []
    try:
        ws, we = pd.Timestamp(week_start).normalize(), pd.Timestamp(week_end).normalize()
    except (TypeError, ValueError):
        return []
    if pd.isna(ws) or pd.isna(we) or we < ws:
        return []

    p = f'P{num:02d}'
    try:
        riego_by_pile, drena_by_pile = _fechas_actividad(label)
    except Exception:
        # If cached operational history is unavailable, do not infer an active
        # operation campaign from a stale measured recovery trace.
        riego_by_pile, drena_by_pile = {}, {}
    events = set()
    for mapping in (riego_by_pile, drena_by_pile):
        for value in mapping.get(p, ()):
            day = pd.Timestamp(value).normalize()
            if pd.notna(day):
                events.add(day)

    # WIP start is corroborating evidence only when the start itself lies in
    # this Case window. A pre-window WIP row is not treated as proof that the
    # campaign remained active, because its stored end may be stale.
    info = WIP_META.get(label, {}).get(p) or {}
    try:
        wip_start = pd.Timestamp(info.get('ini_aporte'))
        if pd.notna(wip_start):
            wip_start = wip_start.normalize()
            if ws <= wip_start <= we:
                events.add(wip_start)
    except (TypeError, ValueError):
        pass

    active_groups = []
    for day in sorted(events):
        if not active_groups or (day - active_groups[-1][-1]).days > UNLISTED_GAP_DAYS:
            active_groups.append([day])
        else:
            active_groups[-1].append(day)
    active_groups = [group for group in active_groups
                     if any(ws <= day <= we for day in group)]

    cycle_rows = []
    selected = set()
    for idx, cycle in enumerate(cycles):
        cycle_dates = [pd.Timestamp(day).normalize() for day in cycle.get('dates', ())]
        if not cycle_dates:
            continue
        cycle_start = min(cycle_dates)
        cycle_rows.append((idx, cycle_start, cycle_dates))

    # For each operational day in the Case, show only its latest measured
    # cycle within that same uninterrupted activity group. An earlier reset
    # trace may overlap the group's historical dates but was no longer active
    # once a newer measured cycle had begun.
    for group in active_groups:
        case_days = [day for day in group if ws <= day <= we]
        group_start, group_end = group[0], group[-1]
        group_cycles = [row for row in cycle_rows
                        if row[1] <= we
                        and any(group_start <= day <= group_end for day in row[2])]
        for active_day in case_days:
            eligible = [row for row in group_cycles if row[1] <= active_day]
            if eligible:
                selected.add(max(eligible, key=lambda row: (row[1], row[0]))[0])
    return [cycle for idx, cycle in enumerate(cycles) if idx in selected]


def _build_recovery_chart(selected_pila, week_start=None, week_end=None, data=None,
                          caso_id=None) -> go.Figure:
    """Medido por tramos y serie reconstruida/reconciliada del Caso."""
    if not selected_pila:
        return empty_figure()
    pad_id, num_str = selected_pila.split('-P')
    num = int(num_str)
    label = _PAD_TO_LABEL.get(pad_id)
    if label is None:
        return empty_figure()
    measured = _measured_cycles_active_in_window(label, num, week_start, week_end)
    raw = None
    if isinstance(data, dict) and data.get('raw_token'):
        try:
            raw, _ = _load_recon_raw(data.get('raw_token'), caso_id or data.get('caso_id'))
            if (not raw or raw.get('caso', {}).get('run_id') != data.get('caso_run_id')
                    or pd.Timestamp(raw.get('ws')).normalize() != pd.Timestamp(week_start).normalize()
                    or pd.Timestamp(raw.get('we')).normalize() != pd.Timestamp(week_end).normalize()):
                raw = None
        except Exception:
            raw = None
    rs = _reconstructed_campaign_series(label, num, week_start, week_end, raw=raw)
    if not _operational_activity_in_window(label, num, week_start, week_end) and raw is None:
        rs = dict(xs=[], ys=[], sources=[], cu_tf=rs.get('cu_tf'), capped=rs.get('capped', False))
    if not measured and not rs['xs']:
        return empty_figure()
    fig = go.Figure()
    for idx, campaign in enumerate(measured, start=1):
        dates, values = campaign['dates'], campaign['values']
        label_text = 'Medido - tramo %d (%s a %s)' % (
            idx, pd.Timestamp(dates[0]).strftime('%d/%m/%Y'),
            pd.Timestamp(dates[-1]).strftime('%d/%m/%Y'))
        fig.add_trace(go.Scatter(x=dates, y=values, mode='lines', name=label_text,
                                 line=dict(color='#9CA3AF' if idx == len(measured) else '#C5CBD3',
                                           width=1.8 if idx == len(measured) else 1.2),
                                 connectgaps=False))
    if rs['xs']:
        case_start = pd.Timestamp(week_start).normalize()
        case_end = pd.Timestamp(week_end).normalize()
        dates = [pd.Timestamp(day).normalize() for day in rs['xs']]
        values = list(rs['ys'])
        sources = list(rs['sources'])
        in_case = [case_start <= day <= case_end for day in dates]

        def add_operational_segment(indices, name, color):
            if not indices:
                return
            fig.add_trace(go.Scatter(
                x=[rs['xs'][idx] for idx in indices],
                y=[values[idx] for idx in indices],
                mode='lines+markers' if len(indices) == 1 else 'lines', name=name,
                line=dict(color=color, width=2.5), connectgaps=False,
                marker=dict(size=5, color=color) if len(indices) == 1 else None,
                customdata=[sources[idx] for idx in indices],
                hovertemplate='%{x|%d/%m/%Y}<br>%{y:.2f}%<br>%{customdata}<extra></extra>'))

        before = [i for i, day in enumerate(dates) if day < case_start]
        after = [i for i, day in enumerate(dates) if day > case_end]
        inside = [i for i, active in enumerate(in_case) if active]
        # Carry only the exact observed endpoint into the adjacent gray segment.
        # No interpolation is added, and None gaps remain visible in all traces.
        if inside:
            first_inside, last_inside = inside[0], inside[-1]
            if first_inside > 0 and dates[first_inside - 1] < case_start:
                before.append(first_inside)
            if last_inside + 1 < len(dates) and dates[last_inside + 1] > case_end:
                after.insert(0, last_inside)
        add_operational_segment(before, 'Medido (fuera del Caso)', '#9CA3AF')
        case_name = ('Reconciliado del Caso'
                     if any(sources[idx] == 'Reconciliado del Caso' for idx in inside)
                     else 'Medido en Caso')
        add_operational_segment(inside, case_name, '#2a78d6')
        add_operational_segment(after, 'Medido (fuera del Caso)', '#9CA3AF')
        if rs['capped']:
            fig.add_annotation(x=0.5, y=1.0, xref='paper', yref='paper', yanchor='bottom',
                               showarrow=False, font=dict(color='#B45309', size=11),
                               text='La serie supera 100 % segun Cu neto acumulado y CuTf de campana')
    _add_week_zoom_box(fig, week_start, week_end)
    fig.update_layout(
        title=f'{label} - P{num:02d}: Recuperacion acumulada - medido / reconciliado',
        paper_bgcolor=CHART_SURFACE, plot_bgcolor=CHART_SURFACE,
        font=dict(color=CHART_INK_PRIMARY, family='Inter, system-ui, sans-serif'),
        yaxis_title='Recuperacion (%)', legend=dict(bgcolor='rgba(0,0,0,0)'),
        hovermode='x unified', uirevision='keep', margin=dict(l=50, r=20, t=40, b=40),
        xaxis=dict(gridcolor='#E5E7EB'), yaxis=dict(gridcolor='#E5E7EB'))
    return fig


def _pila_chart_cache_key(data, selected_pila, caso_id, week_start, week_end):
    if not selected_pila or not _store_matches_case(data, caso_id):
        return None
    token = data.get('raw_token')
    caso = _caso_by_id(caso_id)
    result_run_id = data.get('caso_run_id')
    if (not token or not caso or not caso.get('run_id')
            or result_run_id != caso.get('run_id')):
        return None
    pad_id, num_text = selected_pila.split('-P', 1)
    label = _PAD_TO_LABEL.get(pad_id)
    if label is None:
        return None
    cycles = _measured_cycles(label, int(num_text))
    cycle_identity = tuple(
        (str(c['dates'][0]), str(c['dates'][-1]), len(c['dates'])) for c in cycles
    )
    ws, we, _ = _store_window(data)
    return (
        str(token), int(caso_id), int(result_run_id),
        str(caso.get('modelo_codigo')), str(caso.get('modelo_version')),
        int(caso.get('total_flujos') or 0),
        str(ws.date() if ws is not None else week_start),
        str(we.date() if we is not None else week_end),
        selected_pila, cycle_identity,
    )


def _get_cached_pila_figures(key):
    if key is None:
        return None
    now = time.monotonic()
    with _PILA_FIGURE_CACHE_LOCK:
        for old_key, (stamp, _) in list(_PILA_FIGURE_CACHE.items()):
            if now - stamp > _PILA_FIGURE_CACHE_TTL:
                _PILA_FIGURE_CACHE.pop(old_key, None)
        item = _PILA_FIGURE_CACHE.get(key)
        if item is None:
            return None
        _PILA_FIGURE_CACHE.move_to_end(key)
        return item[1]


def _cache_pila_figures(key, figures):
    if key is None:
        return
    with _PILA_FIGURE_CACHE_LOCK:
        _PILA_FIGURE_CACHE[key] = (time.monotonic(), figures)
        _PILA_FIGURE_CACHE.move_to_end(key)
        while len(_PILA_FIGURE_CACHE) > _PILA_FIGURE_CACHE_MAX:
            _PILA_FIGURE_CACHE.popitem(last=False)


TAB_STYLE = {
    'padding': '10px 18px', 'fontWeight': '600', 'color': '#6B7280',
    'border': 'none', 'borderBottom': '2px solid transparent', 'backgroundColor': '#ffffff',
}
TAB_SELECTED_STYLE = {
    'padding': '10px 18px', 'fontWeight': '600', 'color': '#E86D1F',
    'border': 'none', 'borderBottom': '2px solid #E86D1F', 'backgroundColor': '#FDEBDD',
}

def _build_content_layout():
    curvas_tab = html.Div([
        dbc.Row([
            dbc.Col(dbc.Switch(id='curvas-compare-switch', label='Comparar', value=False), width='auto'),
            dbc.Col([
                html.Span('Campaña:', style={'marginRight': '8px', 'color': '#212529'}),
                dcc.Dropdown(
                    id='curvas-campana-selector', options=CAMPANA_OPTIONS, value=MAX_CAMPANAS,
                    clearable=False, style={'width': '160px'},
                ),
            ], width='auto', style={'display': 'flex', 'alignItems': 'center'}),
            dbc.Col([
                html.Span('Rango:', style={'marginRight': '8px', 'color': '#212529'}),
                dcc.DatePickerRange(
                    id='curvas-curvas-date-range',
                    min_date_allowed=GLOBAL_MIN_DATE, max_date_allowed=GLOBAL_MAX_DATE,
                    start_date=GLOBAL_MIN_DATE, end_date=GLOBAL_MAX_DATE,
                    display_format='DD/MM/YYYY',
                ),
            ], width='auto', style={'display': 'flex', 'alignItems': 'center'}),
            dbc.Col([
                html.Span('● Activa', style={'color': STATUS_COLORS['activa'], 'marginRight': '12px'}),
                html.Span('● Inactiva', style={'color': STATUS_COLORS['inactiva'], 'marginRight': '12px'}),
                html.Span('● Sin datos', style={'color': STATUS_COLORS['sin_datos']}),
            ], width='auto'),
        ], className='mb-3 mt-3 align-items-center'),

        html.Div(id='curvas-pad-ox-container'),
        html.Div(id='curvas-pad-su-container'),

        dcc.Loading(dcc.Graph(id='curvas-rec-chart', figure=empty_figure(), style={'height': '480px'})),
    ])

    recon_controls = dbc.Row([
        # Sin selector de fecha: la ventana la define el Caso. Elegir fecha a
        # mano permitia reconciliar un periodo distinto al del flowsheet global
        # y comparar resultados que no eran comparables.
        dbc.Col([
            html.Label('Caso oficial', htmlFor='curvas-recon-caso', className='control-label'),
            dcc.Dropdown(id='curvas-recon-caso', options=CASO_OPTIONS, value=DEFAULT_CASO_ID,
                          clearable=False, className='case-dropdown'),
        ], xs=12, lg=5, className='control-field'),
        # 'Reconciliar' corre el proceso; 'Generar reporte' arma el libro de la
        # semana con lo que quedo en `recon-store` (un solo boton de reporte, ya
        # no dos). Ya no hay 'Dias activos' ni checkbox de 'todas las curvas': se
        # reconcilian TODAS las pilas activas siempre (las nuevas con ramp-up, el
        # resto plano) y las inactivas no entran porque no riegan.
        dbc.Col(
            dbc.Button('Ejecutar cálculo', id='curvas-recon-btn', n_clicks=0,
                       color='primary', className='action-primary'),
            xs=12, sm='auto',
        ),
        dbc.Col(
            dbc.Button('Descargar informe', id='curvas-recon-report-btn', n_clicks=0, disabled=True,
                       color='secondary', outline=True, className='action-secondary'),
            xs=12, sm='auto',
        ),
        dbc.Col(
            dbc.Button('Consideraciones', id='curvas-recon-consideraciones-btn', n_clicks=0,
                       color='secondary', outline=True, className='action-secondary'),
            xs=12, sm='auto',
        ),
        dbc.Col(
            html.Div('Pendiente de cálculo', id='curvas-recon-status-badge', className='status-badge status-pending'),
            xs=12, sm='auto', className='status-column',
        ),
    ], className='recon-controls')

    recon_pila_tabs = dcc.Tabs(id='curvas-recon-pila-tabs', value='tab-rec', children=[
        dcc.Tab(label='Curvas de Recuperación', value='tab-rec', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
        dcc.Tab(label='Flujos', value='tab-flujo', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
        dcc.Tab(label='Concentraciones', value='tab-cus', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
    ])

    recon_tab = html.Div([
        html.Section([
            html.Div([
                html.Div([
                    html.P('RECONCILIACIÓN FLOWSHEET', className='eyebrow'),
                    html.H1('Revisión de Caso', className='page-title'),
                    html.P('Selecciona un Caso oficial para distribuir los ajustes medidos entre los pads y revisar el resultado por pila.',
                           className='page-intro'),
                ]),
            ], className='page-heading'),
            html.Div(recon_controls, className='controls-card'),
        ], className='overview-card'),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle('Consideraciones')),
            dbc.ModalBody([
                html.Div([
                    html.Span('Cómo leer este panel', className='method-note-title'),
                    html.Span('Los deltas de caudal y Cu fino son relativos al medido. Los agregados de Cu fino son proporcionales, no toneladas. En las barras de concentración, la media diaria es aritmética sobre los días con dato y no está ponderada por caudal. “Cálculo listo” confirma que hay datos y pilas para mostrar; revisa avisos y gráficos para evaluar el resultado.',
                              className='method-note-text'),
                ], className='method-note'),
                html.H6('Avisos del cálculo', className='mt-3'),
                html.Div(id='curvas-recon-warnings', children=
                         'Ejecuta el cálculo para consultar sus consideraciones.'),
            ]),
            dbc.ModalFooter(dbc.Button('Cerrar', id='curvas-recon-consideraciones-close',
                                      n_clicks=0, className='action-primary')),
        ], id='curvas-recon-consideraciones-modal', is_open=False, size='lg',
                    scrollable=True, className='curvas-recon-shell'),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle('No se pudo completar el cálculo'),
                            close_button=True),
            dbc.ModalBody(id='curvas-recon-error-body'),
            dbc.ModalFooter(dbc.Button('Cerrar', id='curvas-recon-error-close',
                                      n_clicks=0, className='action-primary')),
        ], id='curvas-recon-error-modal', is_open=False, centered=True,
           className='curvas-recon-shell'),
        dcc.Store(id='curvas-recon-store', data=None),
        dcc.Loading(
            html.Div(id='curvas-recon-report-status', className='report-status'),
            type='default', color='#E86D1F',
        ),
        dcc.Download(id='curvas-recon-week-report-download'),
        dcc.Store(id='curvas-recon-pila-store', data=None),
        # El `dcc.Loading` va SOLO alrededor de los tres graficos por pila. Antes
        # envolvia el bloque entero, asi que al hacer click en una pila el spinner
        # blanqueaba grilla + warnings + KPIs + barras aunque ninguno de esos
        # dependa de la seleccion: parecia que se recargaba media pagina.
        html.Div(id='curvas-recon-grid-container', className='siir-card result-card'),
        html.Div(id='curvas-recon-kpis'),
        html.Div(recon_pila_tabs, className='chart-tabs-wrap'),
        dcc.Loading(html.Div([
            html.Div(dcc.Graph(id='curvas-recon-chart-rec', figure=empty_figure()), id='curvas-recon-chart-rec-wrap'),
            html.Div(dcc.Graph(id='curvas-recon-chart-flujo', figure=empty_figure()), id='curvas-recon-chart-flujo-wrap',
                     style={'display': 'none'}),
            html.Div(dcc.Graph(id='curvas-recon-chart-cus', figure=empty_figure()), id='curvas-recon-chart-cus-wrap',
                     style={'display': 'none'}),
        ]), type='default', color='#E86D1F'),
        html.Div(dcc.Graph(id='curvas-recon-bar', figure=empty_figure(
            'Ejecuta el cálculo para ver el resumen del Caso')), className='siir-card chart-card'),
    ], className='recon-workspace')

    return html.Div([
        dcc.Store(id='curvas-selected-store', data=[]),

        dbc.Container([
            html.Div(id='curvas-tab-curvas-content', children=curvas_tab, style={'display': 'none'}),
            # Quedo un solo tab (Reconciliacion MHE), asi que no hay barra de tabs.
            # `curvas_tab` sigue montado pero oculto: sus componentes son Output de
            # varios callbacks y Dash revienta si el ID no existe en el layout.
            html.Div(recon_tab, id='curvas-tab-recon-content'),
        ], fluid=True, className='dashboard-shell'),
    ], style={'backgroundColor': '#F5F6FA', 'minHeight': '100vh'})


# ── Callbacks: curvas (mega-callback dividido en 3) ─────────────────────────────

@_callback(
    Output('curvas-selected-store', 'data'),
    Input({'type': 'curvas-parcela-cell', 'pad': ALL, 'num': ALL}, 'n_clicks'),
    State('curvas-compare-switch', 'value'),
    State('curvas-selected-store', 'data'),
    prevent_initial_call=True,
)
def on_click(_n_clicks_list, compare_value, selected):
    trig = ctx.triggered_id
    if not isinstance(trig, dict) or trig.get('type') != 'curvas-parcela-cell':
        raise dash.exceptions.PreventUpdate
    selected = selected or []
    clicked_id = f"{trig['pad']}-P{trig['num']}"
    return toggle_selection(selected, clicked_id, bool(compare_value))


@_callback(
    Output('curvas-pad-ox-container', 'children'),
    Output('curvas-pad-su-container', 'children'),
    Input('curvas-selected-store', 'data'),
    Input('curvas-campana-selector', 'value'),
    prevent_initial_call=False,
)
def render_grids(selected, campana_idx):
    selected = selected or []
    view_ox = _view_data(CYCLES_OX, campana_idx)
    view_su = _view_data(CYCLES_SU, campana_idx)
    selected_f = _filter_selected(selected, view_ox, view_su)
    pad_ox = build_pad('ox', 'PAD Oxido', TOP_OX, BOTTOM_OX, view_ox, selected_f)
    pad_su = build_pad('su', 'PAD Sulfuro', TOP_SU, BOTTOM_SU, view_su, selected_f)
    return pad_ox, pad_su


@_callback(
    Output('curvas-rec-chart', 'figure'),
    Input('curvas-selected-store', 'data'),
    Input('curvas-campana-selector', 'value'),
    Input('curvas-curvas-date-range', 'start_date'),
    Input('curvas-curvas-date-range', 'end_date'),
    prevent_initial_call=False,
)
def render_figure(selected, campana_idx, range_start, range_end):
    selected = selected or []
    view_ox = _view_data(CYCLES_OX, campana_idx)
    view_su = _view_data(CYCLES_SU, campana_idx)
    selected_f = _filter_selected(selected, view_ox, view_su)

    if not selected_f:
        return empty_figure()

    # Recorta la lectura a [range_start, range_end] -- consulta la DB solo
    # por el rango elegido en el datepicker, no trae el historico completo.
    start_d = pd.Timestamp(range_start).date() if range_start else None
    end_d = pd.Timestamp(range_end).date() if range_end else None
    materials_needed = {cid.split('-P')[0] for cid in selected_f}
    ranged_ox = load_oxido(start_d, end_d) if 'ox' in materials_needed else {}
    ranged_su = load_sulfuro(start_d, end_d) if 'su' in materials_needed else {}

    direct_labels = len(selected_f) <= 4  # relief rule: yellow/aqua/magenta need visible labels, not color alone
    font_family = 'Inter, system-ui, sans-serif'

    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=CHART_SURFACE, plot_bgcolor=CHART_SURFACE,
        font=dict(color=CHART_INK_PRIMARY, family=font_family),
        xaxis=dict(
            title=dict(text='Fecha', font=dict(color=CHART_INK_SECONDARY)),
            tickformat='%b %Y', hoverformat='%d-%b-%Y',
            gridcolor=CHART_GRIDLINE, griddash='solid', linecolor=CHART_BASELINE,
            tickcolor=CHART_BASELINE, tickfont=dict(color=CHART_INK_MUTED),
            showspikes=True, spikemode='across', spikesnap='cursor',
            spikecolor=CHART_BASELINE, spikethickness=1, spikedash='solid',
        ),
        yaxis=dict(
            title=dict(text='Recuperación acumulada (%)', font=dict(color=CHART_INK_SECONDARY)),
            ticksuffix='%', rangemode='tozero',
            gridcolor=CHART_GRIDLINE, griddash='solid', linecolor=CHART_BASELINE,
            tickcolor=CHART_BASELINE, tickfont=dict(color=CHART_INK_MUTED),
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
            bgcolor='rgba(0,0,0,0)', font=dict(color=CHART_INK_SECONDARY),
        ),
        hoverlabel=dict(bgcolor=CHART_SURFACE, bordercolor=CHART_BASELINE,
                         font=dict(color=CHART_INK_PRIMARY, family=font_family, size=13)),
        margin=dict(l=50, r=(70 if direct_labels else 20), t=40, b=50),
        uirevision='keep', hovermode='x unified',
    )
    for idx, cid in enumerate(selected_f):
        pad_id, num_str = cid.split('-P')
        num = int(num_str)
        ranged = ranged_ox if pad_id == 'ox' else ranged_su
        info = ranged.get(num, {})
        dates, values = info.get('dates', []), info.get('values', [])
        label = f"{'Ox' if pad_id == 'ox' else 'Su'}-P{num}"
        color = _series_color(idx)
        fig.add_trace(go.Scatter(
            x=dates, y=values, mode='lines', name=label,
            line=dict(color=color, width=2, shape='linear'),
            hovertemplate='%{y:.1f}%<extra>' + label + '</extra>',
        ))
        if dates:
            fig.add_trace(go.Scatter(
                x=[dates[-1]], y=[values[-1]], mode='markers' + ('+text' if direct_labels else ''),
                marker=dict(size=9, color=color, line=dict(width=2, color=CHART_SURFACE)),
                text=[label] if direct_labels else None,
                textposition='middle right',
                textfont=dict(color=CHART_INK_SECONDARY, size=11, family=font_family),
                showlegend=False, hoverinfo='skip',
            ))
    return fig


# ── Callbacks: reconciliacion ────────────────────────────────────────────────────

def _error_modal_body(titulo, detalle, fallas=None):
    """Contenido del modal de error (sin URLs ni secretos)."""
    items = []
    if fallas:
        items.append(html.Ul([html.Li(f) for f in fallas], className='mb-0 ps-3'))
    elif detalle:
        items.append(html.P(detalle, className='mb-0'))
    return html.Div([
        dbc.Alert(titulo, color='danger', className='mb-3'),
        *items,
    ])


@_callback(
    Output('curvas-recon-store', 'data'),
    Output('curvas-recon-error-modal', 'is_open'),
    Output('curvas-recon-error-body', 'children'),
    Input('curvas-recon-btn', 'n_clicks'),
    State('curvas-recon-caso', 'value'),
    prevent_initial_call=True,
    running=[
        (Output('curvas-recon-btn', 'disabled'), True, False),
        (Output('curvas-recon-btn', 'children'), 'Calculando…', 'Ejecutar cálculo'),
    ],
)
def compute_recon(_n_clicks, caso_id):
    """Reconcile every active pile over the selected official Case window."""
    profile_total_t0 = time.perf_counter()
    perf_trace_id = uuid.uuid4().hex
    record_phase('compute.start', 0.0, trace_id=perf_trace_id)
    caso = _caso_by_id(caso_id)
    if caso is None or not caso.get('run_id'):
        raise dash.exceptions.PreventUpdate

    _progress_begin(
        'Ejecutando calculo',
        f'Caso #{caso["id"]} ? {caso["nombre"]}',
        3,
    )
    try:
        try:
            ws, week_end, n_days = resolve_window(caso['fecha_inicio'], caso['fecha_fin'])
            active_days = N_TRANSIENT_DEFAULT
            method = 'Pendiente'
            force_all_active = True
            solve = reconcile_week_flowsheet_dash
            tag = method

            _progress_set(
                'Ancla del caso',
                f'Run oficial {caso["run_id"]} ? ventana {ws.date()}..{week_end.date()} ({n_days} d)',
                15,
            )
            phase_t0 = time.perf_counter()
            anchor = load_caso_anchor(
                caso['run_id'], caso['modelo_codigo'], caso['modelo_version'],
                caso['total_flujos'])
            fallas_ancla = diagnose_caso_anchor(anchor)
            if fallas_ancla:
                titulo = (f'Caso #{caso["id"]}: el run oficial {caso["run_id"]} '
                          'no tiene ancla completa y positiva para OXIDOS y SULFUROS.')
                return (
                    dash.no_update,
                    True,
                    _error_modal_body(titulo, None, fallas_ancla),
                )
            phase_anchor = time.perf_counter() - phase_t0
            record_phase('compute.anchor', phase_anchor, trace_id=perf_trace_id)

            phase_t0 = time.perf_counter()
            _progress_set('Historico y metadatos', 'Asegurando caches...', 28)
            ensure_full_data()
            phase_full_data = time.perf_counter() - phase_t0
            record_phase('compute.full_data', phase_full_data, trace_id=perf_trace_id)

            _progress_set(
                'Riego y drenaje',
                'Completando series diarias (oxidos / sulfuros)...',
                45,
            )
            phase_t0 = time.perf_counter()
            labels = ('SULFUROS', 'OXIDOS')
            metadata = {
                label: dict(wip=WIP_META[label], rec_curves=REC_META[label][0],
                            max_rec=REC_META[label][1], ciclo_d=REC_META[label][2])
                for label in labels
            }
            materials, activity_dates = prepare_recon_inputs(
                labels, ws, week_end, metadata,
                {'riego': load_riego, 'cu_riego': load_cu_riego, 'drena_cu': load_drena_cu},
                activity_loader=_fechas_actividad,
            )
            phase_materials = time.perf_counter() - phase_t0
            record_phase('compute.inputs', phase_materials, trace_id=perf_trace_id,
                         activity_dates=len(activity_dates), labels=len(materials))

            _progress_set('Reconciliaci?n Pendiente', 'Resolviendo flowsheet...', 72)
            conn = connect()
            phase_t0 = time.perf_counter()
            trace_token = set_trace_id(perf_trace_id)
            try:
                joint = solve(ws, materials, RECON_PRODUCCION, conn,
                              active_days=active_days, force_all_active=force_all_active,
                              week_end=week_end, anchor=anchor, caso_id=caso['id'])
            finally:
                conn.close()
                reset_trace_id(trace_token)
            phase_solve_and_persist = time.perf_counter() - phase_t0

            _progress_set('Guardando resultado', 'Corrida lista para la UI...', 92)
            phase_t0 = time.perf_counter()
            raw_token = _save_recon_raw(joint.get('res'), caso, ws, week_end)
            phase_raw = time.perf_counter() - phase_t0
            record_phase('compute.raw_pickle', phase_raw, trace_id=perf_trace_id)
        except Exception as exc:
            record_phase('compute.error', time.perf_counter() - profile_total_t0,
                         trace_id=perf_trace_id, error_type=type(exc).__name__)
            print(f'[curvas] error en c?lculo caso=#{caso["id"]}: {exc}')
            mensaje = str(exc).strip() or 'Error inesperado durante el c?lculo.'
            if 'password' in mensaje.lower() or 'pwd=' in mensaje.lower():
                mensaje = 'Error de conexi?n o de datos. Revisa el servidor y reintenta.'
            return (
                dash.no_update,
                True,
                _error_modal_body('No se pudo ejecutar el c?lculo', mensaje),
            )
    finally:
        _progress_end()

    print(f'[{tag}] caso=#{caso["id"]} {caso["nombre"]!r} ventana={ws.date()}..{week_end.date()} '
          f'({n_days} d) run_oficial={caso["run_id"]} ancla={sorted(anchor)} '
          f'active_days={active_days} converged={joint["converged"]} R_global={joint["R_global"]:.4f}')
    if joint['warnings']:
        print(f'[{tag}] warnings: {joint["warnings"]}')
    wk = joint['weeks'].get(ws, {})
    print(f'[{tag}] planta: actual={wk.get("actual")} mt_base={wk.get("mt_base_t")} '
          f'mt_opt={wk.get("mt_opt_t")} resid_opt={wk.get("resid_opt")}')
    for label, sub in joint['materials'].items():
        vals = list((sub.get('Fdrena') or {}).values())
        rng = f'[{min(vals):.3f}, {max(vals):.3f}]' if vals else 'n/a'
        dia = [v for lst in (sub.get('Fdrena_dia') or {}).values() for v in lst]
        rng_dia = f'[{min(dia):.6f}, {max(dia):.6f}]' if dia else 'n/a (sin pilas activas)'
        print(f'[{tag}]   {label}: activas={len(sub["transient"])} '
              f'Fdrena semanal agregado={rng} | Fdrena diario RECONCILIADO={rng_dia}')

    phase_t0 = time.perf_counter()
    out = dict(
        week_start=ws.isoformat(), week_end=week_end.isoformat(), n_days=n_days,
        caso_id=caso['id'], caso_nombre=caso['nombre'], caso_run_id=caso['run_id'],
        raw_token=raw_token, performance_id=perf_trace_id,
        balance_inventario=dict(
            volumen_m3=24.*float((joint.get('res') or {}).get('inventario_pls') or 0.),
            cobre_t=.024*float((joint.get('res') or {}).get('inventario_fino_pls') or 0.),
            disponible_verificado=False),
        anchored=True,
        method=method, transient_days=active_days,
        R_global=joint['R_global'], converged=joint['converged'],
        warnings=list(joint['warnings']),
        combined=_serialize_weeks(joint['weeks']),
        totals=_clean_nan(joint.get('totals') or {}),
    )
    for label, mat in materials.items():
        sub = joint['materials'][label]
        wz_base = compute_wz_week(ws, sub['active'], mat['riego'], mat['cu_riego'],
                                  mat['drena_cu'], week_end=week_end)
        out[label] = _serialize_result(sub, wz_base)
    phase_store = time.perf_counter() - phase_t0
    record_phase('compute.store_serialization', phase_store, trace_id=perf_trace_id)
    engine_phases = joint.get('_phase_seconds') or {}
    print(
        '[RECON_PERF] '
        f'total={time.perf_counter() - profile_total_t0:.3f}s '
        f'full_data={phase_full_data:.3f}s anchor={phase_anchor:.3f}s '
        f'materials={phase_materials:.3f}s activity_prefetched={len(activity_dates)} '
        f'solve={float(engine_phases.get("solve", 0.0)):.3f}s '
        f'save_run={float(engine_phases.get("persist", 0.0)):.3f}s '
        f'solve_plus_persist={phase_solve_and_persist:.3f}s '
        f'raw_pickle={phase_raw:.3f}s store_serialization={phase_store:.3f}s'
    )
    record_phase('compute.callback_total', time.perf_counter() - profile_total_t0,
                 trace_id=perf_trace_id, output_piles=len(materials))
    return out, False, dash.no_update


@_callback(
    Output('curvas-recon-error-modal', 'is_open', allow_duplicate=True),
    Input('curvas-recon-error-close', 'n_clicks'),
    prevent_initial_call=True,
)
def close_error_modal(_n_clicks):
    return False


@_callback(
    Output('curvas-recon-kpis', 'children'),
    Output('curvas-recon-bar', 'figure'),
    Output('curvas-recon-warnings', 'children'),
    Input('curvas-recon-store', 'data'),
    Input('curvas-recon-pila-tabs', 'value'),
    Input('curvas-recon-caso', 'value'),
    prevent_initial_call=True,
)
@_trace_render('render.recon')
def render_recon(data, tab_value, caso_id):
    if not _store_matches_case(data, caso_id):
        return (
            html.Div('Ejecuta el cálculo del Caso seleccionado para ver sus indicadores.',
                     className='empty-state empty-copy'),
            empty_figure('Ejecuta el cálculo para ver el resumen del Caso'),
            None,
        )
    if ctx.triggered_id == 'curvas-recon-pila-tabs':
        return dash.no_update, _build_bar(data, tab_value), dash.no_update
    combined = _combine(data)
    return (
        _build_kpis(combined, data.get('totals')),
        _build_bar(data, tab_value),
        _build_warnings(data) or html.P('Sin avisos adicionales para este cálculo.'),
    )


@_callback(
    Output('curvas-recon-pila-store', 'data'),
    Input({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'n_clicks'),
    State('curvas-recon-pila-store', 'data'),
    prevent_initial_call=True,
)
def select_recon_pila(_n_clicks_list, current):
    trig = ctx.triggered_id
    if not isinstance(trig, dict) or trig.get('type') != 'curvas-recon-cell':
        raise dash.exceptions.PreventUpdate
    # Montar la grilla crea controles con n_clicks=0; no es una seleccion.
    if not any(value for value in (_n_clicks_list or [])):
        raise dash.exceptions.PreventUpdate
    clicked_id = f"{trig['pad']}-P{trig['num']}"
    return None if clicked_id == current else clicked_id


@_callback(
    Output('curvas-recon-grid-container', 'children'),
    Input('curvas-recon-store', 'data'),
    Input('curvas-recon-caso', 'value'),
    State('curvas-recon-pila-store', 'data'),
    prevent_initial_call=False,
)
@_trace_render('render.grid')
def render_recon_grid(data, caso_id, selected_pila):
    """Reconstruye la grilla solo al calcular o cambiar de Caso."""
    if not _store_matches_case(data, caso_id):
        return html.Div([
            html.Div('Aún no hay un cálculo para mostrar', className='empty-title'),
            html.Div('Elige un Caso oficial y ejecuta el cálculo. Aquí aparecerá el estado de las pilas.',
                     className='empty-copy'),
        ], className='empty-state')
    ensure_full_data()
    return _build_status_grid(data['SULFUROS'], data['OXIDOS'],
                              int(data.get('n_days') or 0), selected_pila)


@_callback(
    Output({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'style'),
    Input('curvas-recon-pila-store', 'data'),
    State({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'id'),
    State({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'style'),
    prevent_initial_call=True,
)
def highlight_recon_pila(selected_pila, cell_ids, styles):
    """Cambia solo el borde, conservando los controles y sus n_clicks."""
    return [dict(style or {}, border='2px solid ' + (
        '#f57c00' if f"{cell['pad']}-P{cell['num']}" == selected_pila else '#ced4da'))
        for cell, style in zip(cell_ids, styles)]


@_callback(
    Output('curvas-recon-consideraciones-modal', 'is_open'),
    Input('curvas-recon-consideraciones-btn', 'n_clicks'),
    Input('curvas-recon-consideraciones-close', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_consideraciones(_open_clicks, _close_clicks):
    return ctx.triggered_id == 'curvas-recon-consideraciones-btn'


@_callback(
    Output('curvas-recon-chart-rec', 'figure'),
    Output('curvas-recon-chart-flujo', 'figure'),
    Output('curvas-recon-chart-cus', 'figure'),
    Input('curvas-recon-store', 'data'),
    Input('curvas-recon-pila-store', 'data'),
    Input('curvas-recon-caso', 'value'),
    prevent_initial_call=False,
)
@_trace_render('render.pile_charts')
def render_recon_pila_charts(data, selected_pila, caso_id):
    """Los tres graficos por pila. Lo unico que depende de la seleccion y lo
    unico que muestra spinner al hacer click."""
    if not _store_matches_case(data, caso_id):
        prompt = 'Ejecuta el cálculo del Caso seleccionado para consultar las pilas'
        return empty_figure(prompt), empty_figure(prompt), empty_figure(prompt)
    if selected_pila:
        ensure_full_data()
    ws, we, _n = _store_window(data)
    cache_key = _pila_chart_cache_key(data, selected_pila, caso_id, ws, we)
    cached = _get_cached_pila_figures(cache_key)
    if cached is not None:
        return cached
    figures = (
        _build_recovery_chart(selected_pila, ws, we, data, caso_id),
        _build_flujo_chart(selected_pila, ws, we),
        _build_pila_chart(selected_pila, ws, we),
    )
    _cache_pila_figures(cache_key, figures)
    return figures


@_callback(
    Output('curvas-recon-chart-rec-wrap', 'style'),
    Output('curvas-recon-chart-flujo-wrap', 'style'),
    Output('curvas-recon-chart-cus-wrap', 'style'),
    Input('curvas-recon-pila-tabs', 'value'),
    prevent_initial_call=False,
)
def switch_recon_pila_tab(tab_value):
    show, hide = {'display': 'block'}, {'display': 'none'}
    styles = {'tab-rec': (show, hide, hide), 'tab-flujo': (hide, show, hide), 'tab-cus': (hide, hide, show)}
    return styles.get(tab_value, styles['tab-rec'])


@_callback(
    Output('curvas-recon-status-badge', 'children'),
    Output('curvas-recon-status-badge', 'style'),
    Input('curvas-recon-store', 'data'),
    Input('curvas-recon-caso', 'value'),
    prevent_initial_call=False,
)
def update_status_badge(data, caso_id):
    base_style = {
        'color': '#ffffff', 'fontWeight': '700', 'padding': '7px 12px',
        'borderRadius': '999px', 'fontSize': '0.82rem', 'whiteSpace': 'nowrap',
    }
    trig = ctx.triggered_id
    # Cambiar de Caso invalida lo que hay en pantalla: es OTRA ventana y otro
    # ancla, no un refresco del mismo resultado.
    if trig == 'curvas-recon-caso' or not data:
        return 'Pendiente de cálculo', {**base_style, 'backgroundColor': '#64748B'}
    if data.get('caso_id') is not None and caso_id != data.get('caso_id'):
        return 'Pendiente de cálculo', {**base_style, 'backgroundColor': '#64748B'}
    if not data.get('converged'):
        warnings = data.get('warnings') or []
        sin_datos = any('QRiego_medido o QPLS_medido' in w for w in warnings)
        if sin_datos:
            return 'Faltan datos de riego', {**base_style, 'backgroundColor': '#B45309'}
        return 'Sin resultado usable', {**base_style, 'backgroundColor': '#B91C1C'}
    # `converged` solo indica que existen datos de caudal y pilas activas;
    # no es una medida de calidad ni una validación del ajuste.
    return 'Cálculo listo', {**base_style, 'backgroundColor': '#13795B'}


@_callback(
    Output('curvas-recon-report-btn', 'disabled'),
    Input('curvas-recon-store', 'data'),
    Input('curvas-recon-caso', 'value'),
    prevent_initial_call=True,
)
def enable_report_btn(data, caso_id):
    return not _store_matches_case(data, caso_id)


@_callback(
    Output('curvas-recon-report-status', 'children'),
    Output('curvas-recon-week-report-download', 'data'),
    Input('curvas-recon-report-btn', 'n_clicks'),
    State('curvas-recon-store', 'data'),
    State('curvas-recon-caso', 'value'),
    prevent_initial_call=True,
)
def generate_week_report(_n_clicks, data, selected_case_id):
    """El libro `Reporte_Recuperaciones_Metodo_Reconciliado.xlsx`, armado con
    la corrida que se acaba de reconciliar.

    Es el MISMO formato del pipeline (`pipeline/p4_reporte_xlsx.py`): Rec Ox,
    Rec Sulfuro, las dos hojas de graficos y Prod (Cu neto diario por pila).
    Las hojas Resumen,
    Comparacion planta y Metodo se sacaron del libro: repetian lo que el
    dashboard ya muestra en pantalla. La curva de cada pila sale de `report_metodo.construir_doc`: Q y Cu
    reconciliados por el motor DENTRO de la ventana del Caso, y leyes medidas
    con el Fdrenaje base fuera de ella, hasta el ultimo dia con datos
    (`JOINT_DATA_CUTOFF`)."""
    selected_case = _caso_by_id(selected_case_id)
    if (not isinstance(data, dict)
            or not _store_matches_case(data, selected_case_id)
            or not selected_case
            or not selected_case.get('run_id')
            or data.get('caso_run_id') != selected_case.get('run_id')):
        return html.Div('Ejecuta una reconciliación primero.', style={'color': '#B45309'}), None
    try:
        raw, _raw_path = _load_recon_raw(data.get('raw_token'), data.get('caso_id'))
    except Exception:
        raw = None
    if not raw:
        return html.Div(
            'La corrida ya no está disponible en este servidor; reconcíliala nuevamente para generar el reporte.',
            style={'color': '#B45309'}), None
    if not isinstance(raw, dict) or any(k not in raw for k in ('res', 'caso', 'ws', 'we')):
        return html.Div('La corrida ya no está disponible en este servidor; reconcíliala nuevamente para generar el reporte.',
                        style={'color': '#B45309'}), None
    try:
        res, caso = raw['res'], raw['caso']
        ws, we = pd.Timestamp(raw['ws']), pd.Timestamp(raw['we'])
        if not isinstance(caso, dict):
            raise ValueError('Identidad de Caso inválida')
    except (TypeError, ValueError, KeyError, AttributeError):
        return html.Div('La identidad de la corrida cambió; vuelve a ejecutar la reconciliación.',
                        style={'color': '#B45309'}), None
    try:
        stored_ws, stored_we, _ = _store_window(data)
        selected_ws, selected_we, _ = resolve_window(
            selected_case.get('fecha_inicio'), selected_case.get('fecha_fin'))
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):
        return html.Div(
            'La identidad de la corrida cambió; vuelve a ejecutar la reconciliación.',
            style={'color': '#B45309'}), None
    if (caso.get('run_id') != data.get('caso_run_id')
            or any(caso.get(key) != selected_case.get(key)
                   for key in ('modelo_codigo', 'modelo_version', 'total_flujos'))
            or ws != stored_ws or we != stored_we
            or ws != selected_ws or we != selected_we):
        return html.Div(
            'La identidad de la corrida cambió; vuelve a ejecutar la reconciliación.',
            style={'color': '#B45309'}), None
    tmp_path = None
    try:
        from . import report_metodo
        runs = {caso['id']: dict(
            ws=ws, we=we, caso=caso,
            pads={label: {'res': res} for label in ('OXIDOS', 'SULFUROS')},
        )}
        doc = report_metodo.construir_doc(runs, end=JOINT_DATA_CUTOFF)
        n_pilas = sum(len(v['pilas']) for v in doc['pads'].values())
        if not n_pilas:
            return html.Div('La reconciliación no dejó ninguna pila con curva.',
                             style={'color': '#B45309'}), None
        fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        report_metodo.escribir_libro(doc, tmp_path)
        stamp = datetime.now().strftime('%Y%m%d_%H%M')
        download = dcc.send_file(
            tmp_path,
            filename=f'Reporte_Recuperaciones_Metodo_Reconciliado_Caso{caso["id"]}_{stamp}.xlsx')
    except Exception:
        return html.Div('No se pudo generar el informe. Revisa los datos fuente y, si existe, el libro de planta.',
                        style={'color': '#DC2626'}), None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
    comparacion = ('con comparación planta' if os.path.isfile(report_metodo.XL_PLANTA)
                   else 'sin comparación planta')
    return html.Div(
        f'Reporte generado ({n_pilas} pilas, curva hasta {JOINT_DATA_CUTOFF.date()}, {comparacion}).',
        style={'color': '#2E9E5B'}), download

def build_layout():
    """Return a lazy section shell, without opening a SQL connection."""
    return html.Div([
        dcc.Interval(id='curvas-recon-load-trigger', interval=100, max_intervals=1),
        dcc.Interval(id='curvas-recon-progress-tick', interval=400, n_intervals=0),
        html.Div(
            id='curvas-recon-progress',
            className='curvas-progress is-idle',
            role='status',
            **{'aria-live': 'polite'},
        ),
        html.Div('Preparando datos de curvas y reconciliación…',
                 id='curvas-recon-load-status', role='status'),
        dbc.Button('Reintentar carga', id='curvas-recon-retry', n_clicks=0,
                   color='primary', className='action-primary mb-3', style={'display': 'none'}),
        dcc.Loading(html.Div(id='curvas-recon-content'), color='#E86D1F',
                    target_components={'curvas-recon-content': 'children'}),
    ], id='curvas-recon-root', className='curvas-recon-section')


@_callback(
    Output('curvas-recon-content', 'children'),
    Output('curvas-recon-load-status', 'children'),
    Output('curvas-recon-retry', 'style'),
    Input('curvas-recon-load-trigger', 'n_intervals'),
    Input('curvas-recon-retry', 'n_clicks'),
)
def load_section(_n_intervals, _retry_clicks):
    try:
        initialize_data()
        return _build_content_layout(), '', {'display': 'none'}
    except Exception:
        # Do not expose SQL URLs, credentials or raw driver errors in the UI.
        return html.Div(), html.Div([
            html.Span('No se pudieron cargar los datos. Revisa la conexión SIIR '
                      'y la disponibilidad de las tablas de curvas. Luego reintenta.'),
        ], className='alert alert-warning', role='alert'), {'display': 'inline-block'}


@_callback(
    Output('curvas-recon-progress', 'children'),
    Output('curvas-recon-progress', 'className'),
    Input('curvas-recon-progress-tick', 'n_intervals'),
)
def poll_progress(_n_intervals):
    """Refresca el avance mientras otra hebra carga o calcula."""
    snap = _progress_snapshot()
    if not snap['active'] and not snap['label']:
        return '', 'curvas-progress is-idle'
    return _progress_children(snap), 'curvas-progress is-busy'


def register_callbacks(app):
    """Install before server startup; safe if the host calls this twice."""
    registered = getattr(app, '_siir_curvas_callbacks_registered', False)
    if registered:
        return
    for args, kwargs, fn in _CALLBACKS:
        @wraps(fn)
        def ready_callback(*values, _fn=fn, **callback_kwargs):
            if _fn not in (load_section, poll_progress) and not _DATA_READY:
                raise dash.exceptions.PreventUpdate
            return _fn(*values, **callback_kwargs)
        app.callback(*args, **kwargs)(ready_callback)
    app._siir_curvas_callbacks_registered = True


if __name__ == '__main__':
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY],
                    suppress_callback_exceptions=True, title='Curvas y reconciliación',
                    update_title=None)
    app.layout = build_layout
    register_callbacks(app)
    app.run(debug=os.environ.get('DASH_DEBUG', '0') == '1',
            port=int(os.environ.get('DASH_PORT', '8051')))
