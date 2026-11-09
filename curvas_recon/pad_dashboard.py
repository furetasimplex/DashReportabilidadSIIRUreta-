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

from . import vista_todas_reconciliadas as vista_todas_rec
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
    _fechas_actividad, pilas_jovenes, inicio_campana,
)
from .input_preparation import prepare_recon_inputs
from .perf_trace import record_phase, set_trace_id, reset_trace_id
from .curve_aggregation import (
    combine_recovery_series, save_local_group, delete_local_group, restore_local_groups,
)
from .db_pipeline import (
    connect, get_material_id, load_pila_daily_history, load_pila_history, load_week_totals, save_run,
    load_casos, load_caso_anchor, load_solver_run_meta,
    caso_anchor_completo, diagnose_caso_anchor, HIDRO_SCHEMA,
)
from .history_recovery import HistoryReader, calendar_rows
from .metodo_maduras_fijas import (METODO_LOCAL, METODO_REPARTO, METODO_MADURAS_FIJAS, METODO_DEFAULT, ETIQUETAS as METODO_ETIQUETAS,
                                   MetodoInfactible, etiqueta as metodo_etiqueta)

# Selector de metodo (Sulfuros): el primero es el valor por defecto de la pantalla.
METODO_OPTIONS = [dict(label=METODO_ETIQUETAS[METODO_MADURAS_FIJAS], value=METODO_MADURAS_FIJAS),
                  dict(label=METODO_ETIQUETAS[METODO_REPARTO], value=METODO_REPARTO)]
from .rl_series import visible_xaxis_range

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
_RECON_RAW_PAYLOAD_VERSION = 3

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
_RECOVERY_HISTORY_READER = HistoryReader()
_RECOVERY_HISTORY_LOCK = threading.RLock()
_RECOVERY_HISTORY_FAILURES = OrderedDict()
_RECOVERY_HISTORY_FAILURE_TTL = 30.0
_OFFICIAL_HISTORY_CACHE = {}


def _load_official_recovery_history(week_start):
    """Load only manifest-verified official daily values strictly pre-Case."""
    start = pd.Timestamp(week_start).normalize()
    key = start.date()
    if key not in _OFFICIAL_HISTORY_CACHE:
        from pathlib import Path
        from .history_recovery import load_validated_official_history
        fixture = (Path(__file__).parent / 'test_fixtures'
                   / 'historico_oficial_validado_20260901_20261001.csv')
        try:
            _OFFICIAL_HISTORY_CACHE[key] = load_validated_official_history(fixture, start.date())
        except Exception:
            _OFFICIAL_HISTORY_CACHE[key] = []
    return list(_OFFICIAL_HISTORY_CACHE[key])
_GROUP_RAW_CACHE = {}
_GROUP_RAW_LOCK = threading.Lock()
_GROUP_MEMBER_CACHE = OrderedDict()
_GROUP_MEMBER_CACHE_LOCK = threading.RLock()
_GROUP_MEMBER_CACHE_MAX = 96
_RL_TMS_CACHE = {}
_RL_TMS_CACHE_LOCK = threading.RLock()
_RL_DAILY_CACHE = OrderedDict()
_RL_DAILY_CACHE_LOCK = threading.RLock()
_RL_RIEGO_CACHE = OrderedDict()
_RL_RIEGO_CACHE_LOCK = threading.RLock()


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


def _refresh_primary_recovery_curves():
    """Refresh only the primary measurements and their cycle projections."""
    global DATA_OX, DATA_SU, CYCLES_OX, CYCLES_SU
    global GLOBAL_MIN_DATE, GLOBAL_MAX_DATE, MAX_CAMPANAS, CAMPANA_OPTIONS
    global RAW_CURVES_BY_MATERIAL
    with _DATA_LOCK:
        clear_curve_cache()
        DATA_OX = load_oxido()
        DATA_SU = load_sulfuro()
        last_ox, last_su = _global_last_date(DATA_OX), _global_last_date(DATA_SU)
        CYCLES_OX = {num: split_into_cycles(p['dates'], p['values'], last_ox)
                     for num, p in DATA_OX.items()}
        CYCLES_SU = {num: split_into_cycles(p['dates'], p['values'], last_su)
                     for num, p in DATA_SU.items()}
        all_dates = [d for p in list(DATA_OX.values()) + list(DATA_SU.values())
                     for d in p['dates']]
        GLOBAL_MIN_DATE = min(all_dates) if all_dates else None
        GLOBAL_MAX_DATE = max(all_dates) if all_dates else None
        MAX_CAMPANAS = max(
            [len(c) for c in list(CYCLES_OX.values()) + list(CYCLES_SU.values())] + [1]
        )
        CAMPANA_OPTIONS = [
            {'label': f'Campaña {i}', 'value': i}
            for i in range(1, MAX_CAMPANAS + 1)
        ]
        RAW_CURVES_BY_MATERIAL = {'OXIDOS': DATA_OX, 'SULFUROS': DATA_SU}
        with _PILA_FIGURE_CACHE_LOCK:
            _PILA_FIGURE_CACHE.clear()
        with _GROUP_MEMBER_CACHE_LOCK:
            _GROUP_MEMBER_CACHE.clear()
        with _RL_TMS_CACHE_LOCK:
            _RL_TMS_CACHE.clear()
        with _RL_DAILY_CACHE_LOCK:
            _RL_DAILY_CACHE.clear()
        with _RL_RIEGO_CACHE_LOCK:
            _RL_RIEGO_CACHE.clear()


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


def _refresh_case_catalog():
    """Refresh official run identity at calculation/report boundaries only."""
    global CASOS, CASO_OPTIONS, DEFAULT_CASO_ID
    refreshed = _load_caso_options()
    with _DATA_LOCK:
        CASOS, CASO_OPTIONS, DEFAULT_CASO_ID = refreshed
    return refreshed


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

    Se llama antes de usar resultados/cálculos; los flujos internos pueden
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
    with _RL_TMS_CACHE_LOCK:
        _RL_TMS_CACHE.clear()
    with _RL_DAILY_CACHE_LOCK:
        _RL_DAILY_CACHE.clear()
    with _RL_RIEGO_CACHE_LOCK:
        _RL_RIEGO_CACHE.clear()
    clear_curve_cache()
    # Historico de riego/drenaje con que se detectan las pilas que arrancan:
    # tampoco expira solo, hay que botarlo junto con el resto.
    clear_actividad_cache()
    if bajar_de_nuevo:
        _progress_set('Actualizando datos', 'Limpiando caché local…', 5)
        limpiar_cache_local()

    _progress_set('Curvas de óxido', 'Leyendo recuperaciones…', 12)
    _refresh_primary_recovery_curves()
    _progress_set('Campañas', 'Campañas primarias listas', 38)

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
    if data.get('local_direct_recovery'):
        raw = _get_group_raw(data, data.get('caso_id'))
        if not raw:
            return empty_figure('El resultado ya no está disponible; vuelve a calcular')
        from .sulfide_presentation import trial_bars
        return trial_bars(raw['res'], tab_value)
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
    reconciliadas = set(res.get('transient') or ()) | set(res.get('ss') or ()) | set(res.get('fixed_transient') or ())
    view = {}
    for n in range(1, max_num + 1):
        p = f'P{n:02d}'
        if n not in active_set or p not in reconciliadas:
            view[n] = dict(status='inactiva', disabled=True)
            continue
        view[n] = dict(status=('activa_nueva' if p in nuevas else 'activa'), disabled=False)
    return view


def _build_status_grid(res_s: dict, res_o: dict, n_days: int, selected_pila=None,
                      groups=None, selected_group=None):
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
    group_tiles = []
    for group in groups or []:
        group_id = group.get('id')
        if not group_id:
            continue
        active = group_id == selected_group
        group_tiles.append(dbc.Button(
            group.get('name') or 'Grupo',
            id={'type': 'curvas-group-cell', 'group': group_id}, n_clicks=0,
            color='secondary', outline=True, className='me-2 mb-2',
            title='Mostrar la suma de curvas de recuperacion',
        ))
    group_scheme = html.Div([
        html.Div('Curvas sumadas', className='pad-group-title'),
        html.Div(group_tiles or html.Small('Guarda una suma para verla en el esquema.',
                                           className='text-muted'),
                 className='pad-group-tiles'),
    ], className='pad-group-scheme')
    return html.Div([legend, html.Div([pad_o, pad_s], className='pad-grid'),
                     group_scheme])


def _solver_run_or_none(run_id):
    """Estado del run del solver para los avisos; opcional (None si la BD no lo entrega)."""
    try:
        return load_solver_run_meta(run_id)
    except Exception:
        return None


def _panel_note(metodo):
    """Contenido de «Cómo leer este panel» para el método seleccionado."""
    from .mensajes_pad import texto_panel
    parrafos = texto_panel(metodo)
    return ([html.Span('Cómo leer este panel · ' + metodo_etiqueta(metodo), className='method-note-title')]
            + [html.P(t, className='method-note-text') for t in parrafos])


def _render_mensaje(tag, m):
    """Un mensaje de `mensajes_pad` como item de la lista de avisos (nivel, titulo, texto, que hacer, detalle plegado)."""
    from .mensajes_pad import ERROR, ADVERTENCIA
    etiqueta = {'error': 'ERROR', 'advertencia': 'ADVERTENCIA'}.get(m['nivel'], 'INFORMACIÓN')
    cuerpo = [html.Span(m['titulo'], className='warning-title'), html.Span(' ' + m['texto'])]
    if m.get('accion'):
        cuerpo.append(html.Span(' Qué hacer: ' + m['accion'], className='warning-action'))
    if m.get('detalle') and m['detalle'] != m['texto']:
        cuerpo.append(html.Details([html.Summary('Detalle técnico'), html.Span(str(m['detalle']))], className='warning-detail'))
    ambito = m.get('ambito')
    return html.Div(
        [html.Span(tag, className='warning-tag'),
         html.Span(etiqueta, className=f"warning-level warning-level-{m['nivel']}"),
         html.Div(cuerpo, className='warning-body')],
        className=f"warning-item warning-{m['nivel']}", title=ambito if ambito else None)


def _build_warnings(data: dict):
    """Avisos del run para el operador, con el pad que los origina como etiqueta y su nivel.

    El motor ya rutea: `data['warnings']` trae SOLO los globales (tope de
    Fdrena del ancla, balance incerrable, caso sin run oficializado) y cada
    material trae los suyos. Antes las tres listas eran la misma lista unida,
    asi que el dedupe vaciaba las dos ramas de pad y todo salia [GLOBAL].
    Los textos del motor se reescriben con `mensajes_pad.traducir_aviso_motor`
    (el motor no cambia); lo que no se reconoce se muestra tal cual como
    advertencia. Si `data` trae `solver_run` (estado del run) o `mensajes_pad`
    (mensajes ya armados de la reconciliacion del pad) tambien se muestran."""
    from . import mensajes_pad as MP
    joint_w = list(data.get('warnings', []))
    msgs = []
    balance = data.get('balance_inventario') or {}
    volumen = float(balance.get('volumen_m3') or 0.)
    cobre = float(balance.get('cobre_t') or 0.)
    if abs(volumen) > 1e-6 or abs(cobre) > 1e-6:
        msgs.append(('GLOBAL', MP.mensaje(
            MP.ADVERTENCIA, 'Balance pendiente de inventario',
            f'{volumen:+,.2f} m³ de solución y {cobre:+,.3f} t Cu. Positivo: aporte requerido; negativo: '
            f'retención requerida. Disponibilidad física sin verificar. '
            f'Este término no se atribuye a la recuperación de las pilas.',
            'Tratarlo como diferencia de balance por explicar.', None, None)))
    if data.get('metodo_etiqueta'):
        aplicado = data.get('metodo_aplicado')
        txt = f"Se usó el método «{data['metodo_etiqueta']}»."
        if data.get('metodo') in ('maduras_fijas', 'reparto') and aplicado and 'no aplica' in str(aplicado):
            txt += ' Este método solo aplica a Sulfuros con pilas nuevas; en este Caso se usó el cálculo habitual (motor general).'
        msgs.append(('MÉTODO', MP.mensaje(MP.INFORMACION, 'Método de reconciliación', txt, None, None, None)))
    if data.get('solver_run'):
        msgs += [('SOLVER', m) for m in MP.mensajes_run_solver(data['solver_run'], caso=data.get('caso_id'))]
    msgs += [('PAD', m) for m in (data.get('mensajes_pad') or [])]
    joint_set = set(joint_w)
    msgs += [('GLOBAL', MP.traducir_aviso_motor(w)) for w in joint_w]
    for label in ('SULFUROS', 'OXIDOS'):
        for w in data.get(label, {}).get('warnings', []):
            if w in joint_set:
                continue
            msgs.append((label, MP.traducir_aviso_motor(w)))
    if not msgs:
        return None
    msgs.sort(key=lambda tm: MP.NIVELES.index(tm[1]['nivel']))
    return html.Div([_render_mensaje(tag, m) for tag, m in msgs], className='warning-list')


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


def _load_recovery_history(label, num, week_start, cache_token):
    """Load stored, official reconciliation rows before this Case (SELECT only)."""
    from . import db_pipeline
    key = (str(cache_token or 'no-token'), pd.Timestamp(week_start).date())
    now = time.monotonic()
    with _RECOVERY_HISTORY_LOCK:
        failed_at = _RECOVERY_HISTORY_FAILURES.get(key)
        if failed_at is not None and now - failed_at < _RECOVERY_HISTORY_FAILURE_TTL:
            _RECOVERY_HISTORY_FAILURES.move_to_end(key)
            return [], 'No se pudo consultar el historial reconciliado anterior al Caso.'
        if failed_at is not None:
            _RECOVERY_HISTORY_FAILURES.pop(key, None)
    try:
        with _RECOVERY_HISTORY_LOCK:
            rows = _RECOVERY_HISTORY_READER.load(
                db_pipeline.get_engine(), db_pipeline.SCHEMA, db_pipeline.HIDRO_SCHEMA,
                cache_token or f'{label}:{num}:{pd.Timestamp(week_start).date()}',
                pd.Timestamp(week_start).date())
        pile = f'P{int(num):02d}'
        with _RECOVERY_HISTORY_LOCK:
            _RECOVERY_HISTORY_FAILURES.pop(key, None)
        return [row for row in rows
                if str(row.get('label', '')).upper() == label.upper()
                and str(row.get('parcela', '')).upper() == pile], ''
    except Exception:
        with _RECOVERY_HISTORY_LOCK:
            _RECOVERY_HISTORY_FAILURES[key] = now
            _RECOVERY_HISTORY_FAILURES.move_to_end(key)
            while len(_RECOVERY_HISTORY_FAILURES) > 128:
                _RECOVERY_HISTORY_FAILURES.popitem(last=False)
        return [], 'No se pudo consultar el historial reconciliado anterior al Caso.'


def _historical_recovery_values(label, num, start, week_start, cu_tf_t,
                                measured_cycles, rows, official_rows,
                                return_sources=False):
    """Cumulative historical recon points; gaps break the cumulative until an observed anchor."""
    ws = pd.Timestamp(week_start).normalize()
    start = pd.Timestamp(start).normalize()
    if ws <= start or (not rows and not measured_cycles and not official_rows):
        result = ({}, None, set())
        return (*result, {}) if return_sources else result
    points = {}
    point_sources = {}
    increments = {pd.Timestamp(row['date']).normalize(): row.get('increment_tcu')
                  for row in rows}
    anchors = {}
    anchor_pct = {}
    audited_official = {}
    official_by_day = {pd.Timestamp(row['date']).normalize(): row['value_pct']
                       for row in official_rows
                       if row.get('label') == label.upper()
                       and row.get('parcela') == f'P{int(num):02d}'}
    for cycle in measured_cycles:
        for day, pct in zip(cycle.get('dates') or [], cycle.get('values') or []):
            try:
                stamp, value = pd.Timestamp(day).normalize(), float(pct)
                if start <= stamp < ws and np.isfinite(value):
                    anchors[stamp] = value * cu_tf_t / 100.0
                    anchor_pct[stamp] = value
            except (TypeError, ValueError, OverflowError):
                continue
    audited_official = {
        day: float(row['value_pct']) for row in official_rows
        if str(row.get('label', '')).upper() == label.upper()
        and str(row.get('parcela', '')).upper() == f'P{int(num):02d}'
        and (day := pd.Timestamp(row['date']).normalize()) in anchor_pct
        and abs(anchor_pct[day] - float(row['value_pct'])) <= 0.0001
    }
    day = start
    cumulative = None
    last = ws - pd.Timedelta(days=1)
    while day <= last:
        # Use dated official values only from the hash-validated fixture.
        # These are separately sourced historical reconciliation values.
        if day in audited_official:
            official_pct = audited_official[day]
            points[day] = official_pct
            point_sources[day] = 'Histórico reconciliado (oficial)'
            cumulative = official_pct * cu_tf_t / 100.0
            audited_official[day] = official_pct
            day += pd.Timedelta(days=1)
            continue
        # An observed primary reading is a numerical anchor only when the
        # reconciled cumulative is already unknown; it never resets a valid
        # persisted reconciliation.
        if cumulative is None and day in anchors:
            cumulative = anchors[day]
            points[day] = None
            day += pd.Timedelta(days=1)
            continue
        inc = increments.get(day)
        if cumulative is None or inc is None or not np.isfinite(float(inc)):
            cumulative = None
            points[day] = None
        else:
            cumulative += float(inc)
            points[day] = cumulative / cu_tf_t * 100.0
            point_sources[day] = 'Histórico reconciliado guardado'
        day += pd.Timedelta(days=1)
    # Primary fallback is visual only. Capture the existing baseline first so
    # it cannot change the Case's initial Cu state.
    baseline = points.get(last)
    for day in anchors:
        if points.get(day) is None:
            points[day] = anchor_pct[day]
            point_sources[day] = 'Histórico reconciliado (registro histórico)'
    result = (points, baseline * cu_tf_t / 100.0 if baseline is not None else None,
              set(audited_official))
    return (*result, point_sources) if return_sources else result


def _reconstructed_campaign_series(label, num, week_start, week_end, raw=None,
                                   history_token=None, material=None):
    """Recuperación histórica neta; gaps permanecen como None.

    Fuera del Caso comparte con report_metodo la base FDRENA_MAX=0.95; dentro
    del Caso usa únicamente los flujos diarios de la corrida validada.
    """
    if label == 'SULFUROS' and isinstance(raw, dict) and (raw.get('res') or {}).get('local_direct_recovery'):
        from .sulfide_presentation import direct_series
        series = direct_series(raw['res'], label, num, _measured_cycles(label, num))
        if series is not None:
            return series
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
    mat = material if material is not None else _load_material_window(label, first, end)
    riego, cu_riego, drena_cu = mat['riego'], mat['cu_riego'], mat['drena_cu']
    reconciled = {}
    measured_case = {}
    if isinstance(raw, dict):
        res = raw.get('res') or {}
        # Current payloads may store all pile-days under res.daily, while
        # older payloads nest them under res.piles[].daily. Read both forms;
        # absent or invalid daily values remain gaps below.
        rows = list(res.get('daily') or [])
        if not rows:
            rows = [dict(row,
                         label=row.get('label', pile.get('label')),
                         parcela=row.get('parcela', row.get('p',
                                     pile.get('parcela', pile.get('p')))))
                    for pile in (res.get('piles') or [])
                    for row in (pile.get('daily') or [])]
        for row in rows:
            parcela = row.get('parcela', row.get('p', ''))
            if isinstance(parcela, str):
                parcela = parcela.strip().upper().removeprefix('P')
            try:
                parcela_num = int(parcela)
                d = pd.Timestamp(row['date']).normalize()
                fp, fr = row.get('fino_pls_final'), row.get('fino_riego_final')
                if (row.get('label', label) != label or parcela_num != num
                        or d < ws or d > we):
                    continue
                # A zero final flow has exactly zero fine-Cu contribution even
                # when its undefined concentration/fino fields are NULL.
                qpf, qrf = row.get('q_pls_final'), row.get('q_riego_final')
                if (fp is None and qpf is not None and np.isfinite(float(qpf))
                        and float(qpf) == 0.0):
                    fp = 0.0
                if (fr is None and qrf is not None and np.isfinite(float(qrf))
                        and float(qrf) == 0.0):
                    fr = 0.0
                if (fp is not None and fr is not None
                        and np.isfinite(float(fp)) and np.isfinite(float(fr))):
                    reconciled[d] = (float(fp) - float(fr)) * 0.024
                try:
                    qr = float(row['q_riego_medido'])
                    qp = float(row['q_pls_medido'])
                    cr, cp = row.get('cu_riego_medido'), row.get('cu_pls_medido')
                    riego_fine = 0.0 if qr == 0 else qr * float(cr)
                    pls_fine = 0.0 if qp == 0 else qp * float(cp)
                    if all(np.isfinite(v) for v in (qr, qp, riego_fine, pls_fine)):
                        measured_case[d] = (pls_fine - riego_fine) * 0.024
                except (KeyError, TypeError, ValueError, OverflowError):
                    pass
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
    history_token = (history_token or (raw or {}).get('raw_token')
                     or (raw or {}).get('caso', {}).get('run_id'))
    history_rows, history_error = _load_recovery_history(label, num, ws, history_token)
    official_history_rows = _load_official_recovery_history(ws)
    historical_points, historical_baseline, official_history_days, historical_point_sources = _historical_recovery_values(
        label, num, start, ws, cu_tf_t, measured, history_rows, official_history_rows,
        return_sources=True)
    from . import report_metodo
    prior_anchors = {}
    for cycle in measured:
        for day, pct in zip(cycle.get('dates') or [], cycle.get('values') or []):
            try:
                stamp, numeric = pd.Timestamp(day).normalize(), float(pct)
                if start <= stamp < ws and np.isfinite(numeric):
                    prior_anchors[stamp] = numeric * cu_tf_t / 100.0
            except (TypeError, ValueError, OverflowError):
                continue
    if historical_baseline is not None:
        cum_cu = historical_baseline
    else:
        # The observed cycle value remains a numerical base for comparing
        # Case increments. This fallback is never rendered as pre-Case history.
        d = first
        while d < ws and d <= end:
            if d in riego.index and p in riego.columns:
                q = riego.at[d, p]
                cd = drena_cu.at[d, p] if p in drena_cu.columns and d in drena_cu.index else None
                cr = cu_riego.at[d] if d in cu_riego.index else None
                base_inc = report_metodo.net_recovery_increment(q, cd, cr)
                if base_inc is not None and np.isfinite(base_inc) and cum_cu is not None:
                    cum_cu += float(base_inc)
                else:
                    cum_cu = None
            if d in prior_anchors:
                cum_cu = prior_anchors[d]
            d += pd.Timedelta(days=1)
    measured_cum_cu = cum_cu
    case_anchors = {}
    for cycle in measured:
        for day, pct in zip(cycle.get('dates') or [], cycle.get('values') or []):
            try:
                stamp, numeric = pd.Timestamp(day).normalize(), float(pct)
                if ws <= stamp <= we and np.isfinite(numeric):
                    case_anchors[stamp] = numeric * cu_tf_t / 100.0
            except (TypeError, ValueError, OverflowError):
                continue
    measured_values = {}
    # The historical calendar already owns any pre-Case measured anchor.
    # Keep its value as numerical state, but don't append a second point with
    # source `medido (ancla)` that can overwrite the validated history point.
    # `cum_cu` and `first` remain unchanged for Case-day calculations.
    xs, ys, sources = [], [], []
    d = max(first, ws)
    while d <= end:
        source, inc = 'Medido', None
        if ws <= d <= we:
            if isinstance(raw, dict):
                source, inc = 'Reconciliado del Caso', reconciled.get(d)
            else:
                source = 'Reconciliación no disponible'
        elif d in riego.index and p in riego.columns:
            q = riego.at[d, p]
            cd = drena_cu.at[d, p] if p in drena_cu.columns and d in drena_cu.index else None
            cr = cu_riego.at[d] if d in cu_riego.index else None
            inc = report_metodo.net_recovery_increment(q, cd, cr)
        if inc is not None and np.isfinite(inc) and cum_cu is not None:
            cum_cu += float(inc)
            value = cum_cu / cu_tf_t * 100.0
        else:
            cum_cu = None
            value = None
        if ws <= d <= we and isinstance(raw, dict):
            measured_inc = measured_case.get(d)
        elif d in riego.index and p in riego.columns:
            q = riego.at[d, p]
            cd = drena_cu.at[d, p] if p in drena_cu.columns and d in drena_cu.index else None
            cr = cu_riego.at[d] if d in cu_riego.index else None
            measured_inc = report_metodo.net_recovery_increment(q, cd, cr)
        else:
            measured_inc = None
        if measured_inc is not None and np.isfinite(measured_inc) and measured_cum_cu is not None:
            measured_cum_cu += float(measured_inc)
            measured_values[d] = measured_cum_cu / cu_tf_t * 100.0
        else:
            measured_cum_cu = None
            measured_values[d] = None
        # Recovery readings are numerical anchors for following dates, but the
        # anchor itself remains visibly measured and is not relabeled as recon.
        if d in case_anchors:
            if cum_cu is None:
                cum_cu = case_anchors[d]
            # The measured stream may use its own primary anchor; the
            # reconciled cumulative above is never reset while still valid.
            measured_cum_cu = case_anchors[d]
        xs.append(d)
        ys.append(value)
        sources.append(source)
        d += pd.Timedelta(days=1)
    valid = [v for v in ys if v is not None and np.isfinite(v)]
    measured_ys = [measured_values.get(day) for day in xs]
    historical_days = list(pd.date_range(start, ws - pd.Timedelta(days=1), freq='D'))
    combined_xs = historical_days + xs
    combined_ys = [historical_points.get(day) for day in historical_days] + ys
    historical_source_days = {day for day, value in historical_points.items()
                              if value is not None and np.isfinite(float(value))}
    combined_sources = [historical_point_sources.get(day, 'Sin histórico reconciliado')
                        for day in historical_days] + sources
    combined_measured = [None] * len(historical_days) + measured_ys
    valid = [v for v in combined_ys if v is not None and np.isfinite(v)]
    return dict(xs=combined_xs, ys=combined_ys, measured_ys=combined_measured,
                sources=combined_sources, cu_tf=cu_tf, historical_error=history_error,
                historical_available=bool(historical_source_days),
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


def _combined_member_series(member_id, raw, ws, we):
    """Return separate measured, Case, and historical series for aggregation."""
    try:
        pad_id, num_text = member_id.split('-P')
        label, num = _PAD_TO_LABEL[pad_id], int(num_text)
        pile = f'P{num:02d}'
        if label == 'SULFUROS' and isinstance(raw, dict) and (raw.get('res') or {}).get('local_direct_recovery'):
            from .sulfide_presentation import direct_member
            return direct_member(raw['res'], label, num, pd.Timestamp(ws), pd.Timestamp(we), _measured_cycles(label, num))
        info = WIP_META.get(label, {}).get(pile) or {}
        cu_tf_t = cu_tf_toneladas(info.get('CuTf'))
        if cu_tf_t is None or cu_tf_t <= 0 or not isinstance(raw, dict):
            return None
        ws, we = pd.Timestamp(ws).normalize(), pd.Timestamp(we).normalize()
        if pd.isna(ws) or pd.isna(we) or we < ws:
            return None
        token = raw.get('raw_token') or (raw.get('caso') or {}).get('run_id')
        cycles = _measured_cycles(label, num)
        source_signature = tuple((tuple(pd.Timestamp(day).isoformat() for day in cycle.get('dates') or []),
                                  tuple(cycle.get('values') or [])) for cycle in cycles)
        cache_key = (token, raw.get('caso', {}).get('run_id'), member_id,
                     ws.isoformat(), we.isoformat(), float(cu_tf_t),
                     str(info.get('ini_aporte')), source_signature,
                     id(WIP_META), _RECON_RAW_PAYLOAD_VERSION)
        with _GROUP_MEMBER_CACHE_LOCK:
            cached = _GROUP_MEMBER_CACHE.get(cache_key)
            if cached is not None:
                _GROUP_MEMBER_CACHE.move_to_end(cache_key)
                return cached

        primary = _measured_cycles_active_in_window(label, num, ws, we)
        reconstructed = _reconstructed_campaign_series(
            label, num, ws, we, raw=raw, history_token=token)
        source_points = {}
        for day, value, source in zip(reconstructed.get('xs') or [],
                                      reconstructed.get('ys') or [],
                                      reconstructed.get('sources') or []):
            stamp = pd.Timestamp(day).normalize()
            try:
                number = float(value) if value is not None else None
            except (TypeError, ValueError, OverflowError):
                number = None
            if number is not None and not np.isfinite(number):
                number = None
            source_points[stamp] = (number, source)

        measured_map = {}
        for day, value in zip(reconstructed.get('xs') or [],
                              reconstructed.get('measured_ys') or []):
            stamp = pd.Timestamp(day).normalize()
            if ws <= stamp <= we:
                try:
                    measured_map[stamp] = float(value) if value is not None else None
                except (TypeError, ValueError, OverflowError):
                    measured_map[stamp] = None
        for cycle in primary:
            for day, pct in zip(cycle.get('dates') or [], cycle.get('values') or []):
                try:
                    stamp, number = pd.Timestamp(day).normalize(), float(pct)
                except (TypeError, ValueError, OverflowError):
                    continue
                if ws <= stamp <= we and np.isfinite(number):
                    measured_map[stamp] = number  # A valid primary point wins.

        case_days = list(pd.date_range(ws, we, freq='D'))
        historical_days = [day for day in sorted(source_points) if day < ws]
        ordered = historical_days + case_days
        reconciled_map = {
            day: (source_points.get(day, (None, None))[0]
                  if source_points.get(day, (None, None))[1] == 'Reconciliado del Caso'
                  else None)
            for day in case_days
        }
        official_map = {
            day: (source_points.get(day, (None, None))[0]
                  if 'oficial' in str(source_points.get(day, (None, None))[1]).lower()
                  else None)
            for day in historical_days
        }
        solver_map = {
            day: (source_points.get(day, (None, None))[0]
                  if ('guardado' in str(source_points.get(day, (None, None))[1]).lower()
                      or 'registro histórico' in str(source_points.get(day, (None, None))[1]).lower())
                  else None)
            for day in historical_days
        }

        def curve(days, values, source):
            return {'xs': days, 'ys': values, 'sources': [source] * len(days)}

        default_hist = [official_map[day]
                        if 'oficial' in str(source_points.get(day, (None, None))[1]).lower()
                        else solver_map.get(day) for day in historical_days]
        default_sources = [
            (source_points.get(day, (None, 'Sin histórico reconciliado'))[1]
             if source_points.get(day, (None, None))[0] is not None
             else 'Sin histórico reconciliado') for day in historical_days
        ]
        unified_history = curve(historical_days, default_hist, 'Histórico reconciliado')
        initial_points = [(pd.Timestamp(day).normalize(), float(value))
                          for cycle in primary
                          for day, value in zip(cycle.get('dates') or [], cycle.get('values') or [])
                          if value is not None and np.isfinite(float(value))
                          and (pd.isna(pd.Timestamp(info.get('ini_aporte')))
                               or pd.Timestamp(day).normalize() >= pd.Timestamp(info.get('ini_aporte')).normalize())
                          and pd.Timestamp(day).normalize() <= we]
        result = {
            'id': member_id, 'cu_tf_t': float(cu_tf_t),
            'initial_recovery_pct': (min(initial_points, key=lambda point: point[0])[1]
                                     if initial_points else None),
            'series': {
                'xs': ordered,
                'ys': default_hist + [reconciled_map.get(day) for day in case_days],
                'sources': default_sources + ['Reconciliado del Caso'] * len(case_days),
            },
            'measured_series': curve(case_days, [measured_map.get(day) for day in case_days], 'Medido'),
            'reconciled_series': curve(
                case_days, [reconciled_map.get(day) for day in case_days], 'Reconciliado del Caso'),
            'official_history_series': curve(
                historical_days, [official_map.get(day) for day in historical_days],
                'Histórico reconciliado (oficial)'),
            'solver_history_series': curve(
                historical_days, [solver_map.get(day) for day in historical_days],
                'Histórico reconciliado guardado'),
            'history_series': unified_history,
        }
        with _GROUP_MEMBER_CACHE_LOCK:
            _GROUP_MEMBER_CACHE[cache_key] = result
            _GROUP_MEMBER_CACHE.move_to_end(cache_key)
            while len(_GROUP_MEMBER_CACHE) > _GROUP_MEMBER_CACHE_MAX:
                _GROUP_MEMBER_CACHE.popitem(last=False)
        return result
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

def _get_group_raw(data, caso_id):
    if not _store_matches_case(data, caso_id):
        return None
    token = data.get('raw_token')
    if not token:
        return None
    with _GROUP_RAW_LOCK:
        if token not in _GROUP_RAW_CACHE:
            try:
                raw, _ = _load_recon_raw(token, caso_id)
            except Exception:
                raw = None
            # One bounded entry: avoid holding several full local payloads.
            _GROUP_RAW_CACHE.clear()
            _GROUP_RAW_CACHE[token] = raw
        raw = _GROUP_RAW_CACHE[token]
        stored_ws, stored_we, _ = _store_window(data)
        try:
            valid = (isinstance(raw, dict)
                     and raw.get('caso', {}).get('id') == caso_id
                     and raw.get('caso', {}).get('run_id') == data.get('caso_run_id')
                     and pd.Timestamp(raw.get('ws')).normalize() == pd.Timestamp(stored_ws).normalize()
                     and pd.Timestamp(raw.get('we')).normalize() == pd.Timestamp(stored_we).normalize())
        except (TypeError, ValueError):
            valid = False
        if not valid:
            return None
        # Keep browser token on a shallow per-request copy, never mutate the
        # shared raw payload loaded from disk.
        return dict(raw, raw_token=token)


def _join_recovery_boundary(fig, initial_recovery=None):
    """Connect adjacent observed endpoints within the existing history trace.

    No extra trace, synthetic day or interpolation across missing dates.
    Calendar timestamps are used consistently by individual and group charts.
    """
    for trace in fig.data:
        trace.x = [pd.Timestamp(day).normalize() for day in trace.x]
    # Set the recovery scale from the current campaign's observed initial
    # value, even if only later official historical points are displayed.
    # This changes the axis, never the plotted recovery values or dates.
    if initial_recovery is not None and np.isfinite(float(initial_recovery)):
        visible = [float(v) for t in fig.data for v in t.y
                   if v is not None and np.isfinite(float(v))]
        if visible:
            lower = min(float(initial_recovery), min(visible))
            upper = max(max(visible), float(initial_recovery))
            upper += max((upper - lower) * 0.04, 0.1)
            fig.update_yaxes(range=[lower, upper], autorange=False,
                             uirevision=f'campaign-initial-{lower}')
    history = next((t for t in fig.data if t.name == 'Curva reconciliada histórica'), None)
    case = next((t for t in fig.data if t.name == 'Recuperación reconciliada'), None)
    if history is None or case is None or not len(history.x) or not len(case.x):
        return
    # Only the actual edge samples qualify; never skip an explicit missing day.
    left, right = history.y[-1], case.y[0]
    if (left is None or right is None or not np.isfinite(float(left))
            or not np.isfinite(float(right))
            or case.x[0] - history.x[-1] != pd.Timedelta(days=1)):
        return
    history.x = list(history.x) + [case.x[0]]
    history.y = list(history.y) + [right]
    if history.customdata is not None:
        custom = list(case.customdata) if case.customdata is not None else []
        history.customdata = list(history.customdata) + [custom[0] if custom else None]


def _build_combined_recovery_chart(group, data, caso_id):
    fig = go.Figure()
    if not isinstance(group, dict) or not _store_matches_case(data, caso_id):
        return fig, ''
    if not _FULL_DATA_READY:
        ensure_full_data()
    ws, we, _ = _store_window(data)
    raw = _get_group_raw(data, caso_id)
    if not isinstance(raw, dict):
        return fig, 'No hay datos locales válidos para el Caso seleccionado.'
    active_ids = set()
    for pile in (raw.get('res') or {}).get('piles', []):
        label = pile.get('label')
        num = pile.get('parcela', pile.get('p'))
        if isinstance(num, str):
            num = num.strip().upper().removeprefix('P')
        try:
            pid = 'rox' if label == 'OXIDOS' else 'rsu' if label == 'SULFUROS' else None
            if pid:
                active_ids.add(f'{pid}-P{int(num):02d}')
        except (TypeError, ValueError):
            continue
    requested = list(dict.fromkeys(group.get('members') or []))
    if len(requested) < 2 or any(mid not in active_ids for mid in requested):
        return fig, 'El grupo requiere al menos dos pilas activas en el Caso actual.'
    members = [_combined_member_series(mid, raw, ws, we) for mid in requested]
    if any(member is None for member in members):
        return fig, 'Falta CuTf válido para una o más pilas del grupo.'
    curve_specs = [
        ('measured_series', 'Recuperación medida', '#6B7280'),
        ('history_series', 'Curva reconciliada histórica', '#9CA3AF'),
        ('reconciled_series', 'Recuperación reconciliada', '#2a78d6'),
    ]
    rendered = 0
    for series_key, name, color in curve_specs:
        inputs = [{'id': member['id'], 'cu_tf_t': member['cu_tf_t'],
                   'series': member.get(series_key) or {'xs': [], 'ys': []}}
                  for member in members]
        combined = combine_recovery_series(inputs)
        if not combined['xs'] or not any(value is not None for value in combined['ys']):
            continue
        rendered += 1
        fig.add_trace(go.Scatter(
            x=combined['xs'], y=combined['ys'], mode='lines', name=name,
            connectgaps=False, line=dict(color=color, width=2.5),
            customdata=[[r, t] if r is not None else [None, None]
                        for r, t in zip(combined['recovered_cu_t'], combined['cu_tf_t'])],
            hovertemplate='%{x|%d/%m/%Y}<br>Recuperación: %{y:.2f}%'
                          '<br>Cu fino recuperado: %{customdata[0]:.2f} t'
                          '<br>Cu apilado: %{customdata[1]:.2f} t<extra></extra>'))
    if not rendered:
        return fig, 'No hay fechas comunes con datos completos para las pilas seleccionadas.'
    initial_members = [member.get('initial_recovery_pct') for member in members]
    initial_recovery = None
    if all(value is not None for value in initial_members):
        total_cu = sum(member['cu_tf_t'] for member in members)
        initial_recovery = sum(value * member['cu_tf_t']
                               for value, member in zip(initial_members, members)) / total_cu
    _join_recovery_boundary(fig, initial_recovery)
    _add_week_zoom_box(fig, ws, we)

    fig.update_layout(title=f"{group.get('name', 'Grupo')}: recuperación combinada",
        paper_bgcolor=CHART_SURFACE, plot_bgcolor=CHART_SURFACE,
        font=dict(color=CHART_INK_PRIMARY, family='Inter, system-ui, sans-serif'),
        yaxis_title='Recuperación (%)', xaxis_title='Fecha calendario',
        hovermode='x unified', uirevision='recovery-full-history-v3', margin=dict(l=50, r=20, t=40, b=40),
        xaxis=dict(type='date', gridcolor='#E5E7EB'), yaxis=dict(gridcolor='#E5E7EB'))
    visible_range = visible_xaxis_range([(trace.x, trace.y) for trace in fig.data])
    if visible_range:
        fig.update_xaxes(range=visible_range)
    return fig, ''


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
    rs = _reconstructed_campaign_series(
        label, num, week_start, week_end, raw=raw,
        history_token=(data or {}).get('raw_token') if isinstance(data, dict) else None)
    if not _operational_activity_in_window(label, num, week_start, week_end) and raw is None:
        rs = dict(xs=[], ys=[], sources=[], cu_tf=rs.get('cu_tf'), capped=rs.get('capped', False))
    if not measured and not rs['xs']:
        return empty_figure(
            'No hay serie disponible para esta pila. El historial reconciliado previo al Caso requiere consulta histórica.')
    fig = go.Figure()
    case_start = pd.Timestamp(week_start).normalize()
    case_end = pd.Timestamp(week_end).normalize()
    measured_primary = {}
    for campaign in measured:
        for day, value in zip(campaign.get('dates') or [], campaign.get('values') or []):
            try:
                stamp, numeric = pd.Timestamp(day).normalize(), float(value)
            except (TypeError, ValueError, OverflowError):
                continue
            if case_start <= stamp <= case_end and np.isfinite(numeric):
                measured_primary[stamp] = numeric
    measured_daily = {}
    for day, value in zip(rs.get('xs') or [], rs.get('measured_ys') or []):
        stamp = pd.Timestamp(day).normalize()
        if case_start <= stamp <= case_end:
            measured_daily[stamp] = (float(value) if value is not None else None)
    measured_daily.update(measured_primary)
    case_dates = sorted(measured_daily)
    measured_case = [measured_daily[day] for day in case_dates]
    if any(value is not None and np.isfinite(value) for value in measured_case):
        fig.add_trace(go.Scatter(
            x=case_dates, y=measured_case, mode='lines', name='Recuperación medida',
            line=dict(color='#9CA3AF', width=1.8), connectgaps=False,
            hovertemplate='%{x|%d/%m/%Y}<br>%{y:.2f}%<extra>Recuperación medida</extra>'))
    if rs['xs']:
        case_start = pd.Timestamp(week_start).normalize()
        case_end = pd.Timestamp(week_end).normalize()
        dates = [pd.Timestamp(day).normalize() for day in rs['xs']]
        values = list(rs['ys'])
        sources = list(rs['sources'])
        in_case = [case_start <= day <= case_end for day in dates]

        def add_operational_segment(indices, name, color):
            if not indices or not any(values[idx] is not None
                                      and np.isfinite(values[idx]) for idx in indices):
                return
            fig.add_trace(go.Scatter(
                x=[rs['xs'][idx] for idx in indices],
                y=[values[idx] for idx in indices],
                mode='lines+markers' if len(indices) == 1 else 'lines', name=name,
                line=dict(color=color, width=2.5), connectgaps=False,
                marker=dict(size=5, color=color) if len(indices) == 1 else None,
                customdata=[sources[idx] for idx in indices],
                hovertemplate='%{x|%d/%m/%Y}<br>%{y:.2f}%<br>%{customdata}<extra></extra>'))

        before = [i for i, day in enumerate(dates)
                  if day < case_start and (sources[i].startswith('Hist')
                      or sources[i] == 'Sin histórico reconciliado')]
        after = [i for i, day in enumerate(dates) if day > case_end]
        inside = [i for i, active in enumerate(in_case) if active]
        # Carry only the exact observed endpoint into the adjacent gray segment.
        # No interpolation is added, and None gaps remain visible in all traces.
        if inside:
            _first_inside, last_inside = inside[0], inside[-1]
            if last_inside + 1 < len(dates) and dates[last_inside + 1] > case_end:
                after.insert(0, last_inside)
        case_name = ('Recuperación reconciliada'
                     if any(sources[idx] == 'Reconciliado del Caso'
                            and values[idx] is not None and np.isfinite(values[idx])
                            for idx in inside)
                     else 'Recuperación medida')
        add_operational_segment(before, 'Curva reconciliada histórica', '#9CA3AF')
        add_operational_segment(inside, case_name, '#2a78d6')
        add_operational_segment(after, 'Medido (fuera del Caso)', '#9CA3AF')
        if inside and not any(values[idx] is not None and np.isfinite(values[idx])
                              for idx in inside):
            fig.add_annotation(x=0.5, y=0.96, xref='paper', yref='paper', yanchor='bottom',
                               showarrow=False, font=dict(color='#B45309', size=10),
                               text='Sin Cu acumulado válido en la ventana del Caso; se conservan los vacíos')
        historical_indexes = [i for i, day in enumerate(dates) if day < case_start]
        historical_has_points = any(values[i] is not None and np.isfinite(values[i])
                                     for i in historical_indexes)
        if not rs.get('historical_available') or rs.get('historical_error') or not historical_has_points:
            fig.add_annotation(x=0.5, y=1.0, xref='paper', yref='paper', yanchor='bottom',
                               showarrow=False, font=dict(color='#B45309', size=10),
                               text=(rs.get('historical_error') or
                                     'Sin filas reconciliadas históricas válidas antes de la ventana del Caso.'))
        if rs['capped']:
            fig.add_annotation(x=0.5, y=1.0, xref='paper', yref='paper', yanchor='bottom',
                               showarrow=False, font=dict(color='#B45309', size=11),
                               text='La serie supera 100 % segun Cu neto acumulado y CuTf de campana')
    campaign_start = pd.Timestamp((globals().get('WIP_META', {}).get(label, {}).get(f'P{num:02d}') or {}).get('ini_aporte'))
    initial_points = [(pd.Timestamp(day).normalize(), float(value))
                      for cycle in measured
                      for day, value in zip(cycle.get('dates') or [], cycle.get('values') or [])
                      if value is not None and np.isfinite(float(value))
                      and (pd.isna(campaign_start) or pd.Timestamp(day).normalize() >= campaign_start)
                      and pd.Timestamp(day).normalize() <= case_end]
    initial_recovery = min(initial_points, key=lambda point: point[0])[1] if initial_points else None
    _join_recovery_boundary(fig, initial_recovery)
    _add_week_zoom_box(fig, week_start, week_end)
    fig.update_layout(
        title=f'{label} - P{num:02d}: Recuperacion acumulada - medido / reconciliado',
        paper_bgcolor=CHART_SURFACE, plot_bgcolor=CHART_SURFACE,
        font=dict(color=CHART_INK_PRIMARY, family='Inter, system-ui, sans-serif'),
        yaxis_title='Recuperacion (%)', legend=dict(bgcolor='rgba(0,0,0,0)'),
        hovermode='x unified', uirevision='recovery-full-history-v3', margin=dict(l=50, r=20, t=40, b=40),
        xaxis=dict(type='date', gridcolor='#E5E7EB'), yaxis=dict(gridcolor='#E5E7EB'))
    visible_range = visible_xaxis_range([(trace.x, trace.y) for trace in fig.data])
    if visible_range:
        fig.update_xaxes(range=visible_range)
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
    all_rec_components = vista_todas_rec.layout_components(dbc, dcc, html, go)
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
        dbc.Col([
            html.Label('Método de reconciliación', htmlFor='curvas-recon-metodo', className='control-label'),
            dcc.Dropdown(id='curvas-recon-metodo', options=METODO_OPTIONS, value=METODO_DEFAULT,
                          clearable=False, className='case-dropdown'),
        ], xs=12, lg=3, className='control-field'),
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
        dbc.Col(dbc.Button('Suma de curvas', id='curvas-grupos-open', n_clicks=0,
                           color='secondary', outline=True, className='action-secondary'),
                xs=12, sm='auto'),
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
        dcc.Tab(label='Recuperaci\u00f3n y tasa de lixiviaci\u00f3n', value='tab-rl', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
        dcc.Tab(label='Recuperación vs RL', value='tab-rl-acum', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
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
            html.Div(all_rec_components[1:]),
        ], className='overview-card'),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle('Consideraciones')),
            dbc.ModalBody([
                html.Div(_panel_note(METODO_DEFAULT), id='curvas-recon-panel-note', className='method-note'),
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
        dcc.Store(id='curvas-grupos-store', storage_type='local', data=[]),
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
        html.Div(all_rec_components[0], className='mb-3'),
        html.Div(recon_pila_tabs, className='chart-tabs-wrap'),
        html.Div([
            dcc.Dropdown(id='curvas-grupo-picker', options=[], value=None, clearable=True,
                         placeholder='Curvas individuales (predeterminado)', className='mb-2'),
            html.Div(id='curvas-grupo-warning', className='text-warning mb-2'),
            html.Div(dcc.Graph(id='curvas-grupo-chart', figure=go.Figure()),
                id='curvas-grupo-chart-wrap', style={'display': 'none'}),
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle('Suma de curvas')),
                dbc.ModalBody([
                    html.Label('Grupo guardado'),
                    dcc.Dropdown(id='curvas-grupo-edit-picker', options=[], value=None, clearable=True),
                    dbc.Input(id='curvas-grupo-name', placeholder='Nombre del grupo', className='mt-2'),
                    dcc.Dropdown(id='curvas-grupo-members', options=[], value=[], multi=True,
                                 placeholder='Selecciona dos o más pilas activas', className='mt-2'),
                    html.Div(id='curvas-grupo-validation', className='text-warning mt-2'),
                    html.Small('Suma Cu apilado y Cu fino recuperado por fecha calendario. '
                               'Los datos quedan en este navegador.', className='text-muted'),
                ]),
                dbc.ModalFooter([
                    dbc.Button('Nueva suma', id='curvas-grupo-new', n_clicks=0,
                               color='secondary', outline=True, className='action-secondary'),
                    dbc.Button('Guardar grupo', id='curvas-grupo-save', n_clicks=0,
                               color='primary', className='action-primary'),
                    dbc.Button('Quitar', id='curvas-grupo-delete', n_clicks=0,
                               color='secondary', outline=True, className='action-secondary'),
                    dbc.Button('Restaurar individuales', id='curvas-grupo-reset', n_clicks=0,
                               color='secondary', outline=True, className='action-secondary'),
                    dbc.Button('Cerrar', id='curvas-grupos-close', n_clicks=0,
                               color='secondary', outline=True, className='action-secondary'),
                ]),
            ], id='curvas-grupos-modal', is_open=False, size='lg', centered=True,
               className='curvas-recon-shell'),
        ], id='curvas-grupos-controls', className='siir-card chart-card')
        ,dcc.Loading(html.Div([
            html.Div(dcc.Graph(id='curvas-recon-chart-rec', figure=empty_figure()), id='curvas-recon-chart-rec-wrap'),
            html.Div(dcc.Graph(id='curvas-recon-chart-flujo', figure=empty_figure()), id='curvas-recon-chart-flujo-wrap',
                     style={'display': 'none'}),
            html.Div(dcc.Graph(id='curvas-recon-chart-cus', figure=empty_figure()), id='curvas-recon-chart-cus-wrap',
                     style={'display': 'none'}),
            html.Div([
                dcc.Graph(id='curvas-recon-chart-rl', figure=empty_figure()),
            ], id='curvas-recon-chart-rl-wrap', style={'display': 'none'}),
            html.Div(dcc.Graph(id='curvas-recon-chart-rl-acum', figure=empty_figure()),
                     id='curvas-recon-chart-rl-acum-wrap', style={'display': 'none'}),
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

def _error_modal_body(titulo, detalle, fallas=None, accion=None):
    """Contenido del modal de error (sin URLs ni secretos): que paso, detalle y que hacer."""
    items = []
    if fallas:
        items.append(html.Ul([html.Li(f) for f in fallas], className='mb-0 ps-3'))
    elif detalle:
        items.append(html.P(detalle, className='mb-0'))
    if accion:
        items.append(html.P('Qué hacer: ' + accion, className='mt-2 mb-0 fw-semibold'))
    return html.Div([
        dbc.Alert(titulo, color='danger', className='mb-3'),
        *items,
    ])


@_callback(
    Output('curvas-recon-panel-note', 'children'),
    Input('curvas-recon-metodo', 'value'),
)
def update_panel_note(metodo):
    return _panel_note(metodo)


@_callback(
    Output('curvas-recon-store', 'data'),
    Output('curvas-recon-error-modal', 'is_open'),
    Output('curvas-recon-error-body', 'children'),
    Input('curvas-recon-btn', 'n_clicks'),
    State('curvas-recon-caso', 'value'),
    State('curvas-recon-metodo', 'value'),
    prevent_initial_call=True,
    running=[
        (Output('curvas-recon-btn', 'disabled'), True, False),
        (Output('curvas-recon-btn', 'children'), 'Calculando…', 'Ejecutar cálculo'),
    ],
)
def compute_recon(_n_clicks, caso_id, metodo=None):
    """Reconcile every active pile over the selected official Case window."""
    # Sin metodo (llamada directa, sin selector): ajuste local de pilas nuevas de siempre (`reconcile_sulfides`), no expuesto en el selector.
    metodo = metodo if metodo in METODO_ETIQUETAS else METODO_LOCAL
    profile_total_t0 = time.perf_counter()
    perf_trace_id = uuid.uuid4().hex
    record_phase('compute.start', 0.0, trace_id=perf_trace_id)
    try:
        _refresh_case_catalog()
    except Exception:
        return (dash.no_update, True,
                _error_modal_body('No se pudo verificar el Caso oficial actual.',
                                  'La consulta del Caso oficial no respondió, por lo que no se ejecutó el cálculo.',
                                  None, 'Verifique la conexión con la base de datos y vuelva a pulsar Ejecutar cálculo.'))
    caso = _caso_by_id(caso_id)
    if caso is None or not caso.get('run_id'):
        return (dash.no_update, True,
                _error_modal_body('El Caso seleccionado ya no tiene un run oficial exitoso.', None, []))

    _progress_begin(
        'Ejecutando calculo',
        f'Caso #{caso["id"]} — {caso["nombre"]}',
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
                f'Run oficial {caso["run_id"]} · ventana {ws.date()}..{week_end.date()} ({n_days} d)',
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
            # Con curvas nuevas (30 dias o menos desde el primer riego) se
            # ajustan solo ellas; sin curvas nuevas el respaldo es la
            # distribucion del ajuste entre todas las curvas.
            # Ambos metodos del selector usan el paquete local de Sulfuros (flujos absolutos del run, misma base por pila) y cierran contra
            # los mismos objetivos; solo difieren en quien absorbe el ajuste (ver `metodo_maduras_fijas`).
            sulfide_young = pilas_jovenes('SULFUROS', ws, week_end)
            if sulfide_young:
                method = tag = 'Sulfuros: ajuste de curvas de hasta 30 días'

            phase_t0 = time.perf_counter()
            _progress_set('Historico y metadatos', 'Asegurando caches...', 28)
            primary_curves_were_ready = _FULL_DATA_READY
            ensure_full_data()
            if primary_curves_were_ready:
                _progress_set('Histórico y metadatos', 'Actualizando recuperaciones primarias…', 38)
                _refresh_primary_recovery_curves()
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
            if sulfide_young:
                from .sulfide_db_inputs import load_saved_profile, make_source_provider
                from .sulfide_inputs import load_sulfide_inputs
                # Concentraciones medidas tal cual (sin ffill ni respaldo) y el
                # perfil modelado guardado del Caso, si existe.
                raw_series = dict(
                    riego=materials['SULFUROS']['riego'],
                    cu_riego=load_cu_riego('SULFUROS', ws, week_end, fill=False),
                    drena_cu=load_drena_cu('SULFUROS', ws, week_end, fill=False))
                provider = make_source_provider(
                    raw_series, DATA_SU, WIP_META['SULFUROS'],
                    inicio_campana('SULFUROS', week_end), caso,
                    saved_profile=load_saved_profile(caso['id'], ws, week_end))
                sulfide_inputs = load_sulfide_inputs(
                    ws, week_end, caso['id'], anchor, source_provider=provider)
                if sulfide_inputs['source_ids']['solver_run_id'] != caso['run_id']:
                    raise ValueError('Las fuentes de Sulfuros no corresponden al run oficial seleccionado')
                materials['SULFUROS']['sulfide_inputs'] = sulfide_inputs
                materials['SULFUROS']['sulfide_metodo'] = metodo
            else:
                materials['SULFUROS']['sulfide_policy'] = 'legacy'
            phase_materials = time.perf_counter() - phase_t0
            record_phase('compute.inputs', phase_materials, trace_id=perf_trace_id,
                         activity_dates=len(activity_dates), labels=len(materials))

            _progress_set('Reconciliación pendiente', 'Resolviendo flowsheet…', 72)
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
            # Aviso de pad sin pilas nuevas (solo informa; no cambia el calculo).
            from .mensajes_pad import mensajes_sin_nuevas
            _res_j = joint.get('res') or {}
            _res_j['mensajes_pad'] = list(_res_j.get('mensajes_pad') or []) + [
                m for lab in labels for m in mensajes_sin_nuevas(
                    lab, metodo_etiqueta(metodo), _res_j.get('daily') or [], anchor.get(lab), ws, week_end,
                    len(sulfide_young) if lab == 'SULFUROS' else len(pilas_jovenes(lab, ws, week_end)))]

            _progress_set('Guardando resultado', 'Corrida lista para la UI...', 92)
            phase_t0 = time.perf_counter()
            raw_token = _save_recon_raw(joint.get('res'), caso, ws, week_end)
            phase_raw = time.perf_counter() - phase_t0
            record_phase('compute.raw_pickle', phase_raw, trace_id=perf_trace_id)
        except MetodoInfactible as exc:
            print(f'[curvas] metodo {metodo} infactible caso=#{caso["id"]}: {exc}')
            return (dash.no_update, True,
                    _error_modal_body('El método «%s» no pudo cerrar el pad' % metodo_etiqueta(metodo), None,
                                      [f"{m['titulo']}: {m['texto']} Qué hacer: {m['accion']}" if m.get('accion') else f"{m['titulo']}: {m['texto']}"
                                       for m in exc.mensajes],
                                      'Revise el run del Caso. Puede probar el método «%s», pero ambos usan los mismos objetivos, '
                                      'banda y tope: si la causa es el agua o el Cu del run, tampoco cerrará.'
                                      % METODO_ETIQUETAS[METODO_REPARTO if metodo == METODO_MADURAS_FIJAS else METODO_MADURAS_FIJAS]))
        except Exception as exc:
            record_phase('compute.error', time.perf_counter() - profile_total_t0,
                         trace_id=perf_trace_id, error_type=type(exc).__name__)
            print(f'[curvas] error en cálculo caso=#{caso["id"]}: {exc}')
            mensaje = str(exc).strip() or 'Error inesperado durante el cálculo.'
            if 'password' in mensaje.lower() or 'pwd=' in mensaje.lower():
                mensaje = 'Error de conexión o de datos. Revisa el servidor y reintenta.'
            return (
                dash.no_update,
                True,
                _error_modal_body('No se pudo ejecutar el cálculo', mensaje, None,
                                  'Revise el mensaje, corrija el dato indicado y vuelva a calcular; si persiste, informe al administrador la hora del intento y el Caso.'),
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
        vals = [v for v in (sub.get('Fdrena') or {}).values() if v is not None]
        rng = f'[{min(vals):.3f}, {max(vals):.3f}]' if vals else 'n/a'
        dia = [v for lst in (sub.get('Fdrena_dia') or {}).values() for v in lst if v is not None]
        rng_dia = f'[{min(dia):.6f}, {max(dia):.6f}]' if dia else 'n/a (sin pilas activas)'
        print(f'[{tag}]   {label}: activas={len(sub["active"])} '
              f'Fdrena semanal agregado={rng} | Fdrena diario RECONCILIADO={rng_dia}')

    phase_t0 = time.perf_counter()
    out = dict(
        week_start=ws.isoformat(), week_end=week_end.isoformat(), n_days=n_days,
        caso_id=caso['id'], caso_nombre=caso['nombre'], caso_run_id=caso['run_id'],
        raw_token=raw_token, performance_id=perf_trace_id,
        local_direct_recovery=bool((joint.get('res') or {}).get('local_direct_recovery')),
        sulfide_audit=_clean_nan((joint.get('res') or {}).get('sulfide_audit') or {}),
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
        metodo=metodo, metodo_etiqueta=metodo_etiqueta(metodo),
        metodo_aplicado=((joint.get('res') or {}).get('metodo_sulfuros')
                         or 'no aplica (sin pilas nuevas de Sulfuros)'),
        mensajes_pad=_clean_nan((joint.get('res') or {}).get('mensajes_pad') or []),
        solver_run=_clean_nan(_solver_run_or_none(caso['run_id'])),
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
    if ctx.triggered_id == 'curvas-recon-pila-tabs' and tab_value in ('tab-rl', 'tab-rl-acum'):
        return dash.no_update, dash.no_update, dash.no_update
    if not _FULL_DATA_READY:
        ensure_full_data()
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
    Output('curvas-grupo-picker', 'value'),
    Input({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'n_clicks'),
    Input({'type': 'curvas-group-cell', 'group': ALL}, 'n_clicks'),
    Input('curvas-grupos-store', 'data'),
    State({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'id'),
    State({'type': 'curvas-group-cell', 'group': ALL}, 'id'),
    State('curvas-recon-pila-store', 'data'),
    State('curvas-grupo-picker', 'value'),
    prevent_initial_call=True,
)
def select_recon_pila(_pile_clicks, _group_clicks, groups, pile_ids, group_ids,
                      current, selected_group):
    trig = ctx.triggered_id
    # Dash's ctx.triggered value can be None for ALL inputs. Match the actual
    # triggered component to its id and n_clicks instead of checking whether
    # any other, previously clicked cell has a nonzero count.
    if trig == 'curvas-grupos-store':
        valid_ids = {group.get('id') for group in (groups or [])}
        if selected_group and selected_group not in valid_ids:
            return current, None
        raise dash.exceptions.PreventUpdate
    if isinstance(trig, dict) and trig.get('type') == 'curvas-group-cell':
        clicked = next((count for item_id, count in zip(group_ids or [], _group_clicks or [])
                        if item_id == trig), 0)
        if clicked <= 0:
            raise dash.exceptions.PreventUpdate
        return None, trig.get('group')
    if isinstance(trig, dict) and trig.get('type') == 'curvas-recon-cell':
        clicked = next((count for item_id, count in zip(pile_ids or [], _pile_clicks or [])
                        if item_id == trig), 0)
        if clicked <= 0:
            raise dash.exceptions.PreventUpdate
        clicked_id = f"{trig['pad']}-P{trig['num']}"
        return (None if clicked_id == current else clicked_id), None
    raise dash.exceptions.PreventUpdate


@_callback(
    Output('curvas-recon-grid-container', 'children'),
    Input('curvas-recon-store', 'data'),
    Input('curvas-recon-caso', 'value'),
    Input('curvas-grupos-store', 'data'),
    State('curvas-recon-pila-store', 'data'),
    prevent_initial_call=False,
)
@_trace_render('render.grid')
def render_recon_grid(data, caso_id, groups, selected_pila):
    """Reconstruye la grilla solo al calcular o cambiar de Caso."""
    if not _store_matches_case(data, caso_id):
        return html.Div([
            html.Div('Aún no hay un cálculo para mostrar', className='empty-title'),
            html.Div('Elige un Caso oficial y ejecuta el cálculo. Aquí aparecerá el estado de las pilas.',
                     className='empty-copy'),
        ], className='empty-state')
    ensure_full_data()
    return _build_status_grid(data['SULFUROS'], data['OXIDOS'],
                              int(data.get('n_days') or 0), selected_pila,
                              groups)


@_callback(
    Output({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'style'),
    Input('curvas-recon-pila-store', 'data'),
    Input('curvas-grupo-picker', 'value'),
    Input('curvas-grupos-store', 'data'),
    Input('curvas-recon-store', 'data'),
    State({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'id'),
    State({'type': 'curvas-recon-cell', 'pad': ALL, 'num': ALL}, 'style'),
    prevent_initial_call=True,
)
def highlight_recon_pila(selected_pila, selected_group, groups, data, cell_ids, styles):
    """Actualiza estilo in situ y conserva estado de actividad y n_clicks."""
    group = next((item for item in (groups or [])
                  if item.get('id') == selected_group), None)
    members = set((group or {}).get('members') or [])
    view_s = _status_view((data or {}).get('SULFUROS') or {}, 28, _ACTIVE_SU)
    view_o = _status_view((data or {}).get('OXIDOS') or {}, 32, _ACTIVE_OX)
    result = []
    for cell, style in zip(cell_ids or [], styles or []):
        pile_id = f"{cell['pad']}-P{cell['num']}"
        view = view_o if cell['pad'] == 'rox' else view_s
        status = view.get(int(cell['num']), {}).get('status', 'inactiva')
        updated = dict(style or {})
        updated['backgroundColor'] = '#2a78d6' if pile_id in members else RECON_STATUS_COLORS[status]
        updated['border'] = '2px solid ' + ('#f57c00' if pile_id == selected_pila else '#ced4da')
        result.append(updated)
    return result


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
    Input('curvas-grupo-picker', 'value'),
    Input('curvas-grupos-store', 'data'),
    prevent_initial_call=False,
)
@_trace_render('render.pile_charts')
def render_recon_pila_charts(data, selected_pila, caso_id, group_id=None, groups=None):
    """Los tres graficos por pila. Lo unico que depende de la seleccion y lo
    unico que muestra spinner al hacer click."""
    if not _store_matches_case(data, caso_id):
        prompt = 'Ejecuta el cálculo del Caso seleccionado para consultar las pilas'
        return empty_figure(prompt), empty_figure(prompt), empty_figure(prompt)
    group = next((g for g in (groups or []) if g.get('id') == group_id), None)
    if group is not None:
        ensure_full_data()
        from .group_solution_charts import build_group_solution_charts
        import sys
        flows, concentrations = build_group_solution_charts(sys.modules[__name__], group, data, caso_id)
        return dash.no_update, flows, concentrations
    if selected_pila:
        ensure_full_data()
    ws, we, _n = _store_window(data)
    cache_key = _pila_chart_cache_key(data, selected_pila, caso_id, ws, we)
    cached = _get_cached_pila_figures(cache_key)
    if cached is not None:
        return cached
    if data.get('local_direct_recovery') and selected_pila:
        raw = _get_group_raw(data, caso_id)
        if not raw:
            return (empty_figure('El resultado ya no está disponible; vuelve a calcular'),) * 3
        from .sulfide_presentation import solution_figures
        selected_pad, selected_num = selected_pila.split('-P')
        # Antes del Caso: una sola serie con el historico oficial guardado; en la ventana: medido y reconciliado.
        official_rows, _history_error = _load_recovery_history(
            _PAD_TO_LABEL[selected_pad], int(selected_num), ws, data.get('raw_token'))
        flow, concentrations = solution_figures(raw['res'], _PAD_TO_LABEL[selected_pad], int(selected_num), official_rows)
        if _PAD_TO_LABEL[selected_pad] == 'SULFUROS':
            from .sulfide_presentation import recovery_figure
            recovery = recovery_figure(raw['res'], 'SULFUROS', int(selected_num), _measured_cycles('SULFUROS', int(selected_num)))
        else:
            recovery = _build_recovery_chart(selected_pila, ws, we, data, caso_id)
        figures = (recovery, flow, concentrations)
        _cache_pila_figures(cache_key, figures)
        return figures
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
    Output('curvas-grupo-chart-wrap', 'style'),
    Output('curvas-grupos-controls', 'style'),
    Output('curvas-recon-chart-rl-wrap', 'style'),
    Output('curvas-recon-chart-rl-acum-wrap', 'style'),
    Input('curvas-recon-pila-tabs', 'value'), Input('curvas-grupo-picker', 'value'),
    prevent_initial_call=False,
)
def switch_recon_pila_tab(tab_value, group_id):
    show, hide = {'display': 'block'}, {'display': 'none'}
    if tab_value == 'tab-rec':
        return ((hide, hide, hide, show, show, hide, hide) if group_id
                else (show, hide, hide, hide, show, hide, hide))
    if tab_value == 'tab-flujo':
        return hide, show, hide, hide, hide, hide, hide
    if tab_value == 'tab-cus':
        return hide, hide, show, hide, hide, hide, hide
    if tab_value == 'tab-rl':
        return hide, hide, hide, hide, hide, show, hide
    if tab_value == 'tab-rl-acum':
        return hide, hide, hide, hide, hide, hide, show
    return hide, hide, hide, hide, hide, hide, hide




def _rl_tms_by_pile(asof, token):
    """Lazy authoritative stack TMS map, one report_metodo read per Case token/cut."""
    from .rl_series import cached_tms_map
    key = (str(token), str(pd.Timestamp(asof).normalize().date()))
    with _RL_TMS_CACHE_LOCK:
        def load():
            from .report_metodo import leer_apilado
            stack = leer_apilado(asof=pd.Timestamp(asof).normalize())
            return {('OXIDOS' if pid == 1 else 'SULFUROS', int(num)): row
                    for (pid, num), row in stack.items() if pid in (1, 2)}
        result = cached_tms_map(_RL_TMS_CACHE, key, load)
        while len(_RL_TMS_CACHE) > 12:
            _RL_TMS_CACHE.pop(next(iter(_RL_TMS_CACHE)))
        return result


def _rl_member_daily(label, num, stack_row, raw, ws, we, token, mode='reconciliado', riego_frame=None):
    """Use measured Q for full pre-Case history and selected Case Q inside it."""
    f0 = pd.Timestamp(stack_row.get('f0')).normalize()
    ws, we = pd.Timestamp(ws).normalize(), pd.Timestamp(we).normalize()
    if pd.isna(f0) or f0 > we or we < ws:
        return None, False
    frame_bounds = (str(pd.Timestamp(riego_frame.index.min()).normalize()),
                    str(pd.Timestamp(riego_frame.index.max()).normalize())) if (
                        riego_frame is not None and not riego_frame.empty) else None
    key = (str(token), label, int(num), str(f0.date()), str(ws.date()), str(we.date()), str(mode),
           'history-v3' if riego_frame is not None else 'case-only', frame_bounds)
    with _RL_DAILY_CACHE_LOCK:
        cached = _RL_DAILY_CACHE.get(key)
        if cached is not None:
            _RL_DAILY_CACHE.move_to_end(key)
            daily, history_complete = cached
            return dict(daily), history_complete
    measured = {}
    if riego_frame is not None and f0 < ws:
        frame = riego_frame.copy()
        frame.index = pd.DatetimeIndex(frame.index).normalize()
        pile = f'P{int(num):02d}'
        if pile in frame.columns:
            measured = {pd.Timestamp(day).normalize(): (float(value) if pd.notna(value) else None)
                        for day, value in frame[pile].items()
                        if f0 <= pd.Timestamp(day).normalize() < ws}
    history_days = list(pd.date_range(f0, ws - pd.Timedelta(days=1), freq='D'))
    history_complete = all(day in measured and measured[day] is not None for day in history_days)
    daily = {}
    for day in history_days:
        value = measured.get(day)
        try:
            daily[day] = float(value) if value is not None and np.isfinite(float(value)) and float(value) >= 0 else None
        except (TypeError, ValueError, OverflowError):
            daily[day] = None
    from .rl_series import case_irrigation_rows, measured_irrigation_rows
    if mode == 'reconciliado':
        case_q = case_irrigation_rows(raw, label, num, ws, we)
    elif mode == 'medido':
        case_q = measured_irrigation_rows(raw, label, num, ws, we)
    else:
        raise ValueError("RL mode must be 'medido' or 'reconciliado'")
    for day in pd.date_range(ws, we, freq='D'):
        value = case_q.get(day)
        try:
            daily[day] = float(value) if value is not None and np.isfinite(float(value)) and float(value) >= 0 else None
        except (TypeError, ValueError, OverflowError):
            daily[day] = None
    with _RL_DAILY_CACHE_LOCK:
        _RL_DAILY_CACHE[key] = (dict(daily), history_complete)
        _RL_DAILY_CACHE.move_to_end(key)
        while len(_RL_DAILY_CACHE) > 192:
            _RL_DAILY_CACHE.popitem(last=False)
    return daily, history_complete


def _rl_chart_for_members(member_ids, data, caso_id, recovery_fig, title, accumulated=False):
    from .rl_series import cumulative_rl, aggregate_weighted_rl, align_values_to_calendar
    if not _store_matches_case(data, caso_id) or not data.get('raw_token'):
        return empty_figure('Ejecuta el c\u00e1lculo del Caso seleccionado para consultar la tasa de lixiviaci\u00f3n')
    raw = _get_group_raw(data, caso_id)
    if not isinstance(raw, dict):
        return empty_figure('No hay payload local válido para el Caso seleccionado')
    ws, we, _ = _store_window(data)
    try:
        stack = _rl_tms_by_pile(we, data.get('raw_token'))
    except Exception:
        fig = go.Figure(recovery_fig)
        fig.add_annotation(text='No se pudo obtener TMS de apilado; gráfico no disponible',
                           x=0.5, y=0, xref='paper', yref='paper', showarrow=False)
        return fig
    member_daily_by_mode = {'medido': {}, 'reconciliado': {}}
    member_full_by_mode = {'medido': {}, 'reconciliado': {}}
    member_history = {}
    member_tms = {}
    member_meta = {}
    for member in member_ids:
        try:
            pad_id, num_text = member.split('-P', 1)
            label, num = _PAD_TO_LABEL[pad_id], int(num_text)
            stack_row = stack.get((label, num))
            if not stack_row or not float(stack_row.get('tms') or 0) > 0:
                fig = go.Figure(recovery_fig)
                fig.add_annotation(text=f'Falta TMS v\u00e1lido de la pila {member}; gráfico no disponible',
                                   x=0.5, y=0, xref='paper', yref='paper', showarrow=False)
                return fig
            member_meta[member] = (label, num, stack_row)
        except (KeyError, TypeError, ValueError, OverflowError):
            fig = go.Figure(recovery_fig)
            fig.add_annotation(text='Falta TMS v\u00e1lido de una pila; gráfico no disponible',
                               x=0.5, y=0, xref='paper', yref='paper', showarrow=False)
            return fig
    # Historical RL uses the operational history accepted by the application,
    # labeled reconciled historical by convention. Load each pad prefix once.
    recovery_dates = [pd.Timestamp(day).normalize() for t in recovery_fig.data
                      for day in (list(t.x) if t.x is not None else [])]
    chart_start = min(recovery_dates) if recovery_dates else pd.Timestamp(ws).normalize()
    riego_frames = {}
    for label in {meta[0] for meta in member_meta.values()}:
        earliest = min(pd.Timestamp(meta[2]['f0']).normalize()
                       for meta in member_meta.values() if meta[0] == label)
        if not accumulated:
            earliest = max(chart_start, earliest)
        history_end = pd.Timestamp(ws).normalize() - pd.Timedelta(days=1)
        if earliest > history_end:
            continue
        key = (str(data['raw_token']), label, str(earliest.date()), str(history_end.date()))
        with _RL_RIEGO_CACHE_LOCK:
            frame = _RL_RIEGO_CACHE.get(key)
            if frame is not None:
                _RL_RIEGO_CACHE.move_to_end(key)
        if frame is None:
            from .recon_engine import load_riego
            frame = load_riego(label, start=earliest.date(), end=history_end.date())
            with _RL_RIEGO_CACHE_LOCK:
                _RL_RIEGO_CACHE[key] = frame
                while len(_RL_RIEGO_CACHE) > 24:
                    _RL_RIEGO_CACHE.popitem(last=False)
        riego_frames[label] = frame
    for member, (label, num, stack_row) in member_meta.items():
        member_tms[member] = float(stack_row['tms'])
        for mode, member_daily in member_daily_by_mode.items():
            daily, _ = _rl_member_daily(
                label, num, stack_row, raw, ws, we, data['raw_token'],
                mode=mode, riego_frame=riego_frames.get(label))
            if daily is None:
                daily = {}
            member_full_by_mode[mode][member] = dict(daily)
            if mode == 'reconciliado':
                member_history[member] = {
                    pd.Timestamp(day).normalize(): value for day, value in daily.items()
                    if (pd.Timestamp(stack_row['f0']).normalize() if accumulated else chart_start)
                    <= pd.Timestamp(day).normalize() < pd.Timestamp(ws).normalize()}
            member_daily[member] = {
                pd.Timestamp(day).normalize(): value for day, value in daily.items()
                if pd.Timestamp(ws).normalize() <= pd.Timestamp(day).normalize()
                <= pd.Timestamp(we).normalize()}
    dates = list(pd.date_range(pd.Timestamp(ws).normalize(), pd.Timestamp(we).normalize(), freq='D'))
    fig = go.Figure(recovery_fig)
    for trace in fig.data:
        trace.yaxis = 'y'
        if trace.name == 'Reconciliado del Caso':
            trace.name = 'Recuperaci\u00f3n reconciliada'
        elif trace.name == 'Medido en Caso':
            trace.name = 'Recuperación medida'
    fig.update_layout(yaxis_title='Recuperaci\u00f3n reconciliada (%)',
                      yaxis={'gridcolor': '#E5E7EB'},
                      yaxis2={'title': 'Tasa de lixiviaci\u00f3n (m\u00b3/t/d\u00eda)', 'overlaying': 'y',
                              'side': 'right', 'showgrid': False},
                      xaxis_title='Fecha calendario', xaxis={'type': 'date'}, hovermode='x unified')
    history_rl = (cumulative_rl(next(iter(member_history.values())), next(iter(member_tms.values())))
                  if len(member_history) == 1 else aggregate_weighted_rl(member_history, member_tms))
    history_dates = sorted(history_rl)
    history_values = [history_rl[day] for day in history_dates]
    for mode, member_daily in member_daily_by_mode.items():
        if len(member_daily) == 1:
            rl = cumulative_rl(next(iter(member_daily.values())), next(iter(member_tms.values())))
        else:
            rl = aggregate_weighted_rl(member_daily, member_tms)
        values = [rl.get(day) for day in dates]
        if (mode == 'reconciliado' and history_dates and dates
                and dates[0] - history_dates[-1] == pd.Timedelta(days=1)
                and history_values[-1] is not None and values[0] is not None):
            history_dates.append(dates[0])
            history_values.append(values[0])
        if any(value is not None for value in values):
            fig.add_trace(go.Scatter(
                x=dates, y=values, mode='lines',
                name='Tasa de lixiviaci\u00f3n medida' if mode == 'medido' else 'Tasa de lixiviaci\u00f3n reconciliada',
                line={'color': '#8B5CF6' if mode == 'medido' else '#E86D1F',
                      'width': 2.5, 'dash': 'solid'},
                connectgaps=False, yaxis='y2',
            hovertemplate='Fecha: %{x|%d-%m-%Y}<br>Tasa de lixiviaci\u00f3n: %{y:.3f} m\u00b3/t/d\u00eda<extra>%{fullData.name}</extra>'))
    if any(v is not None for v in history_values):
        fig.add_trace(go.Scatter(
            x=history_dates, y=history_values, mode='lines',
            name='Curva de tasa de lixiviaci\u00f3n reconciliada hist\u00f3rica',
            line={'color': '#C49A6C', 'width': 2.5}, connectgaps=False, yaxis='y2',
            hovertemplate='Fecha: %{x|%d-%m-%Y}<br>Tasa de lixiviaci\u00f3n: %{y:.3f} m\u00b3/t/d\u00eda<extra>%{fullData.name}</extra>'))
    calendar_days = {pd.Timestamp(day).normalize() for trace in fig.data
                     for day in (list(trace.x) if trace.x is not None else [])}
    full_calendar = (list(pd.date_range(min(calendar_days), max(calendar_days), freq='D'))
                     if calendar_days else [])
    for trace in fig.data:
        source_dates = list(trace.x) if trace.x is not None else []
        source_values = list(trace.y) if trace.y is not None else []
        trace.x = full_calendar
        trace.y = align_values_to_calendar(source_dates, source_values, full_calendar)
        if trace.customdata is not None:
            trace.customdata = align_values_to_calendar(
                source_dates, list(trace.customdata), full_calendar)
        trace.connectgaps = False

    # Leading RL zeros alone do not establish the displayed campaign start.
    # Recovery (including an observed zero) or positive RL does. Keep actual
    # zeros and missing days after this start, without masking recovery.
    axis_series = []
    for trace in fig.data:
        values = list(trace.y)
        if trace.yaxis == 'y2':
            values = [v if v is not None and np.isfinite(float(v)) and float(v) > 0
                      else None for v in values]
        axis_series.append((trace.x, values))
    visible_range = visible_xaxis_range(axis_series)
    if visible_range:
        full_range = visible_xaxis_range([(t.x, t.y) for t in fig.data])
        if full_range:
            visible_range[1] = full_range[1]
        fig.update_xaxes(range=visible_range)
    else:
        fig.update_xaxes(range=[pd.Timestamp(ws).isoformat(), pd.Timestamp(we).isoformat()])
    fig.update_layout(uirevision='rl-full-history-v7')

    rl_note = 'Tasa de lixiviaci\u00f3n diaria = volumen de riego del d\u00eda / TMS apiladas; hist\u00f3rico y comparaci\u00f3n del Caso.'

    fig.add_annotation(text=rl_note, x=0, y=-0.28, xref='paper', yref='paper',
                       showarrow=False, xanchor='left', yanchor='top',
                       font={'size': 11, 'color': '#6B7280'})
    fig.update_layout(title={'text': title, 'x': 0.05, 'y': 0.98, 'yanchor': 'top'},
                      margin={'l': 50, 'r': 100, 't': 110, 'b': 150},
                      legend={'orientation': 'h', 'x': 0, 'xanchor': 'left',
                              'y': 1.03, 'yanchor': 'bottom',
                              'entrywidth': 0.5, 'entrywidthmode': 'fraction',
                              'font': {'size': 11}})
    if accumulated:
        from .rl_series import cumulative_campaign_rl
        f0_by_member = {member: meta[2]['f0'] for member, meta in member_meta.items()}
        fig = go.Figure(layout=recovery_fig.layout)
        # Date rectangles and ranges from the recovery/time chart do not
        # describe this numerical X axis. Preserve its theme and Y scale.
        fig.layout.shapes = []
        specs = [
            ('Curva reconciliada histórica', 'reconciliado', '#9CA3AF'),
            ('Recuperación medida', 'medido', '#8B5CF6'),
            ('Recuperación reconciliada', 'reconciliado', '#2a78d6'),
        ]
        accumulated_by_mode = {
            mode: cumulative_campaign_rl(member_full_by_mode[mode], member_tms, f0_by_member)
            for mode in ('medido', 'reconciliado')
        }
        for rec_name, mode, color in specs:
            source = next((trace for trace in recovery_fig.data if trace.name == rec_name), None)
            if source is None:
                continue
            xs, ys, hover_dates = [], [], []
            for day, recovery in zip(list(source.x) if source.x is not None else [],
                                     list(source.y) if source.y is not None else []):
                value = accumulated_by_mode[mode].get(pd.Timestamp(day).normalize())
                if value is None or recovery is None:
                    xs.append(None); ys.append(None)
                else:
                    xs.append(value); ys.append(recovery)
                hover_dates.append(pd.Timestamp(day).date().isoformat())
            if any(value is not None for value in xs):
                fig.add_trace(go.Scatter(x=xs, y=ys, customdata=hover_dates,
                    mode='lines', name=rec_name,
                    hovertemplate='Fecha: %{customdata}<br>RL: %{x:.3f} m³/t'
                                  '<br>Recuperación: %{y:.2f}%<extra>%{fullData.name}</extra>',
                    line={'color': color, 'width': 2.5}, connectgaps=False))
        fig.update_layout(title={'text': title, 'x': 0.05, 'y': 0.98, 'yanchor': 'top'},
            xaxis_title='RL (m³/t)', yaxis_title='Recuperación (%)',
            xaxis={'type': 'linear', 'range': None, 'autorange': True,
                   'rangemode': 'nonnegative', 'gridcolor': '#E5E7EB'},
            yaxis={'gridcolor': '#E5E7EB'}, hovermode='closest',
            margin={'l': 50, 'r': 30, 't': 110, 'b': 95},
            legend={'orientation': 'h', 'x': 0, 'xanchor': 'left',
                    'y': 1.03, 'yanchor': 'bottom', 'entrywidth': 0.5,
                    'entrywidthmode': 'fraction', 'font': {'size': 11}},
            uirevision='rec-vs-rl-acumulada-v1')
        # Reconciliation window expressed as accumulated dose on this X axis.
        bounds = []
        for cumulative in accumulated_by_mode.values():
            previous = ws - pd.Timedelta(days=1)
            left = cumulative.get(previous)
            if left is None and cumulative and previous < min(cumulative):
                left = 0.0
            right = cumulative.get(we)
            if left is not None and right is not None and np.isfinite(float(left)) and np.isfinite(float(right)):
                bounds.append((float(left), float(right)))
        if bounds:
            fig.add_vrect(x0=min(b[0] for b in bounds), x1=max(b[1] for b in bounds),
                          fillcolor='#E86D1F', opacity=0.08, line_width=1,
                          line_color='#E86D1F', layer='below')
        fig.add_annotation(text='RL = volumen de riego desde el inicio de campaña / TMS.',
                           x=0, y=-0.25, xref='paper', yref='paper', showarrow=False,
                           xanchor='left', yanchor='top', font={'size': 11, 'color': '#6B7280'})
        if not fig.data:
            fig.add_annotation(text='No hay recuperación y RL disponibles en las mismas fechas.',
                               x=0.5, y=0.5, xref='paper', yref='paper', showarrow=False)
        return fig
    return fig


@_callback(
    Output('curvas-recon-chart-rl', 'figure'),
    Input('curvas-recon-pila-tabs', 'value'),
    Input('curvas-recon-store', 'data'),
    Input('curvas-recon-pila-store', 'data'),
    Input('curvas-grupo-picker', 'value'),
    Input('curvas-grupos-store', 'data'),
    Input('curvas-recon-caso', 'value'),
    prevent_initial_call=False,
)
def render_rl_chart(tab_value, data, selected_pila, group_id, groups, caso_id):
    # No stack read, history scan, or unrelated figure render until this tab is selected.
    if tab_value != 'tab-rl':
        return empty_figure('Selecciona Recuperaci\u00f3n y tasa de lixiviaci\u00f3n')
    if not _store_matches_case(data, caso_id):
        return empty_figure('Ejecuta el c\u00e1lculo del Caso seleccionado para consultar la tasa de lixiviaci\u00f3n')
    group = next((g for g in (groups or []) if g.get('id') == group_id), None) if group_id else None
    if group:
        members = list(dict.fromkeys(group.get('members') or []))
        if len(members) < 2:
            return empty_figure('El grupo requiere al menos dos pilas')
        rec_fig, warning = _build_combined_recovery_chart(group, data, caso_id)
        if warning:
            return empty_figure(warning)
        return _rl_chart_for_members(members, data, caso_id, rec_fig, group.get('name', 'Grupo'))
    if not selected_pila:
        return empty_figure('Selecciona una pila')
    ws, we, _ = _store_window(data)
    cache_key = _pila_chart_cache_key(data, selected_pila, caso_id, ws, we)
    cached_figures = _get_cached_pila_figures(cache_key)
    rec_fig = cached_figures[0] if cached_figures is not None else _build_recovery_chart(
        selected_pila, ws, we, data, caso_id)
    return _rl_chart_for_members([selected_pila], data, caso_id, rec_fig, selected_pila)


@_callback(
    Output('curvas-recon-chart-rl-acum', 'figure'),
    Input('curvas-recon-pila-tabs', 'value'),
    Input('curvas-recon-store', 'data'),
    Input('curvas-recon-pila-store', 'data'),
    Input('curvas-grupo-picker', 'value'),
    Input('curvas-grupos-store', 'data'),
    Input('curvas-recon-caso', 'value'),
    prevent_initial_call=False,
)
def render_rl_acumulada_chart(tab_value, data, selected_pila, group_id, groups, caso_id):
    if tab_value != 'tab-rl-acum':
        return empty_figure('Selecciona Recuperación vs RL')
    if not _store_matches_case(data, caso_id):
        return empty_figure('Ejecuta el cálculo del Caso seleccionado para consultar RL')
    if not _FULL_DATA_READY:
        ensure_full_data()
    group = next((g for g in (groups or []) if g.get('id') == group_id), None) if group_id else None
    if group:
        members = list(dict.fromkeys(group.get('members') or []))
        if len(members) < 2:
            return empty_figure('El grupo requiere al menos dos pilas')
        rec_fig, warning = _build_combined_recovery_chart(group, data, caso_id)
        if warning:
            return empty_figure(warning)
        return _rl_chart_for_members(members, data, caso_id, rec_fig,
                                     group.get('name', 'Grupo'), accumulated=True)
    if not selected_pila:
        return empty_figure('Selecciona una pila')
    ws, we, _ = _store_window(data)
    cache_key = _pila_chart_cache_key(data, selected_pila, caso_id, ws, we)
    cached_figures = _get_cached_pila_figures(cache_key)
    rec_fig = cached_figures[0] if cached_figures is not None else _build_recovery_chart(
        selected_pila, ws, we, data, caso_id)
    return _rl_chart_for_members([selected_pila], data, caso_id, rec_fig,
                                 selected_pila, accumulated=True)

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
    return ('Cálculo listo' + (f" · {data['metodo_etiqueta']}" if data.get('metodo_etiqueta') else '')), {**base_style, 'backgroundColor': '#13795B'}


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
    State('curvas-grupos-store', 'data'),
    prevent_initial_call=True,
)
def generate_week_report(_n_clicks, data, selected_case_id, groups=None):
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
    try:
        _refresh_case_catalog()
    except Exception:
        return html.Div('No se pudo verificar el Caso oficial actual.',
                        style={'color': '#B45309'}), None
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
        _aud = (res or {}).get('sulfide_audit') or {}
        meta_libro = {'Método de reconciliación': data.get('metodo_etiqueta') or metodo_etiqueta(None),
                      'Aplicado en Sulfuros': data.get('metodo_aplicado'),
                      'Banda de cierre del pad': (f"{100 * _aud['banda']:.3g} %" if _aud.get('banda') is not None else 'no aplica'),
                      'Caso': caso['id'], 'Run oficial': caso.get('run_id'),
                      'Estado del run del solver': (data.get('solver_run') or {}).get('estado', 'sin dato')}
        if groups is not None and groups != []:
            from .virtual_pile_report import VirtualGroupError
            try:
                report_metodo.escribir_libro(doc, tmp_path, groups=groups, meta=meta_libro)
            except VirtualGroupError as exc:
                return html.Div(f'No se pudo exportar la pila virtual: {exc}',
                                style={'color': '#B45309'}), None
        else:
            report_metodo.escribir_libro(doc, tmp_path, meta=meta_libro)
        stamp = datetime.now().strftime('%Y%m%d_%H%M')
        download = dcc.send_file(
            tmp_path,
            filename=f'Reporte_Recuperaciones_Metodo_Reconciliado_Caso{caso["id"]}_{data.get("metodo") or "reparto"}_{stamp}.xlsx')
    except Exception:
        return html.Div('No se pudo generar el informe. Revisa los datos fuente y, si existe, el libro de planta.',
                        style={'color': '#DC2626'}), None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
    comparacion = ('con comparación planta' if os.path.isfile(report_metodo.XL_PLANTA)
                   else 'sin comparación planta')
    return html.Div(
        f'Reporte generado ({n_pilas} pilas, {len(groups or [])} pilas virtuales, '
        f'curva hasta {JOINT_DATA_CUTOFF.date()}, {comparacion}).',
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


@_callback(
    Output('curvas-grupos-modal', 'is_open'),
    Input('curvas-grupos-open', 'n_clicks'), Input('curvas-grupos-close', 'n_clicks'),
    prevent_initial_call=True,
)
def toggle_grupos(_open, _close):
    return ctx.triggered_id == 'curvas-grupos-open'


def highlight_group_tiles(selected_group, tile_ids):
    # Mark the selected saved group without rebuilding the pad grid.
    colors, outlines = [], []
    for tile in tile_ids or []:
        active = tile.get('group') == selected_group
        colors.append('primary' if active else 'secondary')
        outlines.append(not active)
    return colors, outlines


@_callback(
    Output({'type': 'curvas-group-cell', 'group': ALL}, 'color'),
    Output({'type': 'curvas-group-cell', 'group': ALL}, 'outline'),
    Input('curvas-grupo-picker', 'value'),
    State({'type': 'curvas-group-cell', 'group': ALL}, 'id'),
    prevent_initial_call=False,
)
def update_group_tile_selection(selected_group, tile_ids):
    return highlight_group_tiles(selected_group, tile_ids)


@_callback(
    Output('curvas-grupo-members', 'options'),
    Output('curvas-grupo-edit-picker', 'options'),
    Output('curvas-grupo-picker', 'options'),
    Input('curvas-recon-store', 'data'), Input('curvas-recon-caso', 'value'),
    Input('curvas-grupos-store', 'data'),
    prevent_initial_call=False,
)
def group_editor_options(data, caso_id, groups):
    options, raw = [], None
    if _store_matches_case(data, caso_id):
        if not _FULL_DATA_READY:
            ensure_full_data()
        raw = _get_group_raw(data, caso_id)
    if isinstance(raw, dict):
        for pile in (raw.get('res') or {}).get('piles', []):
            label = pile.get('label')
            num = pile.get('parcela', pile.get('p'))
            if isinstance(num, str):
                num = num.strip().upper().removeprefix('P')
            try:
                num = int(num)
                pid = ('rox' if label == 'OXIDOS' else 'rsu' if label == 'SULFUROS' else None)
                if pid and WIP_META.get(label, {}).get(f'P{num:02d}'):
                    options.append({'label': f"{label.title()} P{num:02d}", 'value': f'{pid}-P{num:02d}'})
            except (TypeError, ValueError):
                continue
    group_options = [{'label': g.get('name', 'Grupo'), 'value': g.get('id')}
                     for g in (groups or []) if g.get('id')]
    return options, group_options, group_options


@_callback(
    Output('curvas-grupo-edit-picker', 'value'),
    Input('curvas-grupos-store', 'data'),
    State('curvas-grupo-edit-picker', 'value'), prevent_initial_call=True,
)
def keep_group_editor_selection(groups, current):
    ids = [g.get('id') for g in (groups or [])]
    return current if current in ids else (ids[-1] if ids else None)


@_callback(
    Output('curvas-grupo-name', 'value'), Output('curvas-grupo-members', 'value'),
    Input('curvas-grupo-edit-picker', 'value'), State('curvas-grupos-store', 'data'),
    prevent_initial_call=True,
)
def load_group_editor(group_id, groups):
    group = next((g for g in (groups or []) if g.get('id') == group_id), None)
    return ((group or {}).get('name', ''), (group or {}).get('members', []))


@_callback(
    Output('curvas-grupos-store', 'data'), Output('curvas-grupo-validation', 'children'),
    Input('curvas-grupo-save', 'n_clicks'), Input('curvas-grupo-delete', 'n_clicks'),
    Input('curvas-grupo-reset', 'n_clicks'),
    State('curvas-grupo-edit-picker', 'value'), State('curvas-grupo-name', 'value'),
    State('curvas-grupo-members', 'value'), State('curvas-grupos-store', 'data'),
    State('curvas-grupo-members', 'options'),
    prevent_initial_call=True,
)
def edit_local_groups(_save, _delete, _reset, selected_id, name, members, groups, member_options):
    action = ctx.triggered_id
    if action == 'curvas-grupo-reset':
        return restore_local_groups(), 'Se restauraron las curvas individuales.'
    if action == 'curvas-grupo-delete':
        return delete_local_group(groups, selected_id), 'Se quitó el grupo.'
    if action == 'curvas-grupo-save':
        active = {option.get('value') for option in (member_options or [])}
        return save_local_group(groups, selected_id, name, members, active)
    raise dash.exceptions.PreventUpdate


@_callback(
    Output('curvas-grupo-edit-picker', 'value', allow_duplicate=True),
    Output('curvas-grupo-name', 'value', allow_duplicate=True),
    Output('curvas-grupo-members', 'value', allow_duplicate=True),
    Input('curvas-grupo-new', 'n_clicks'), prevent_initial_call=True,
)
def new_curve_sum(_clicks):
    return None, '', []


@_callback(
    Output('curvas-grupo-chart', 'figure'), Output('curvas-grupo-warning', 'children'),
    Input('curvas-grupo-picker', 'value'), Input('curvas-grupos-store', 'data'),
    Input('curvas-recon-store', 'data'), Input('curvas-recon-caso', 'value'),
    prevent_initial_call=False,
)
def render_combined_group(group_id, groups, data, caso_id):
    group = next((g for g in (groups or []) if g.get('id') == group_id), None)
    if not group_id:
        return go.Figure(), ''
    return _build_combined_recovery_chart(group, data, caso_id)


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
    vista_todas_rec.register_callbacks(
        app, callback=app.callback, Input=Input, Output=Output, State=State, ctx=ctx,
        build_kwargs=lambda: dict(
            get_raw=_get_group_raw, ensure_full_data=ensure_full_data,
            wip_meta=lambda: WIP_META, reconstruct=_reconstructed_campaign_series,
            load_material=_load_material_window, cutoff=lambda: JOINT_DATA_CUTOFF))
    app._siir_curvas_callbacks_registered = True


if __name__ == '__main__':
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY],
                    suppress_callback_exceptions=True, title='Curvas y reconciliación',
                    update_title=None)
    app.layout = build_layout
    register_callbacks(app)
    app.run(debug=os.environ.get('DASH_DEBUG', '0') == '1',
            port=int(os.environ.get('DASH_PORT', '8051')))
