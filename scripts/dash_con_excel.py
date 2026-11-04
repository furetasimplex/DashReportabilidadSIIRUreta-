"""Levanta el dash REAL sin base de datos: las lecturas se reemplazan por el Excel de .

Uso (desde la raiz del repo):

    python scripts/dash_con_excel.py auditorias/datos_caso_10013.xlsx 8070

Luego abrir http://127.0.0.1:8070 y apretar "Ejecutar calculo". Nada se escribe en SQL ni se abre una conexion."""
import os, sys, sqlite3
os.environ['RECON_SIN_CACHE'] = '1'
from pathlib import Path
REPO = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, REPO)
from unittest.mock import MagicMock
import pandas as pd, numpy as np

def install(xlsx):
    from curvas_recon.extraccion_caso import read_workbook
    D = read_workbook(xlsx)
    c = D['case']
    ws, we = pd.Timestamp(c['ventana_inicio']), pd.Timestamp(c['ventana_fin'])
    caso = dict(id=int(c['id']), nombre=str(c['nombre']), fecha_inicio=pd.Timestamp(c['fecha_inicio']),
                fecha_fin=pd.Timestamp(c['fecha_fin']), estado='cerrado', run_id=int(c['run_id']),
                modelo_codigo=c['modelo_codigo'], modelo_version=c['modelo_version'], total_flujos=int(c['total_flujos']))
    from curvas_recon import recon_engine as E, db_pipeline as DB, pad_data as PD, pad_dashboard as P
    from curvas_recon import sulfide_db_inputs as SDB, history_recovery as HR, local_cache as LC
    S = D['series']

    def frames(label):
        s = S[label]
        return s['riego'], s['cu_riego'], s['drena_cu']

    def load_riego(label, start=None, end=None):
        r = frames(label)[0].copy()
        if start is not None: r = r[r.index >= pd.Timestamp(start)]
        if end is not None: r = r[r.index <= pd.Timestamp(end)]
        return r
    def _fill_series(s, start, end):
        s = s.copy()
        if start is not None: s = s[s.index >= pd.Timestamp(start)]
        if end is not None: s = s[s.index <= pd.Timestamp(end)]
        return s
    def load_cu_riego(label, start=None, end=None, fill=True):
        s = _fill_series(frames(label)[1], start, end)
        return s.ffill().bfill() if fill else s
    def load_drena_cu(label, start=None, end=None, fill=True):
        d = _fill_series(frames(label)[2], start, end)
        if fill:
            d = d.ffill().bfill()
            d = d.apply(lambda col: col.fillna(d.mean(axis=1)))
        return d
    def load_wip(label, incluir_sin_campana=True):
        return {p: dict(ini_aporte=pd.Timestamp(v['ini_aporte']) if pd.notna(v['ini_aporte']) else pd.NaT,
                        fin_ciclo=pd.Timestamp(v['fin_ciclo']) if pd.notna(v['fin_ciclo']) else pd.NaT,
                        CuTf=float(v['CuTf']) if pd.notna(v['CuTf']) else np.nan, rec_actual=np.nan,
                        sin_campana=bool(v['sin_campana'])) for p, v in D['wip'][label].items()}
    def inicio_campana(label, asof, gap_days=30):
        return {p: pd.Timestamp(d) for p, d in D['first_irrigation'][label].items()}
    def _fechas_actividad(label):
        r, _cr, cd = frames(label)
        return ({p: pd.DatetimeIndex(r.index[r[p].fillna(0) > 0]) for p in r.columns},
                {p: pd.DatetimeIndex(cd.index[cd[p].fillna(0) > 0]) for p in cd.columns})
    def arranque_en_ventana(label, week_start, week_end, gap_days=30):
        fi = inicio_campana(label, week_end)
        return {p: d for p, d in fi.items() if pd.Timestamp(week_start) <= d <= pd.Timestamp(week_end)}
    def ultimo_riego(label, pilas, before):
        r = frames(label)[0]
        out = {}
        for p in pilas:
            if p in r.columns:
                days = r.index[(r[p].fillna(0) > 0) & (r.index < pd.Timestamp(before))]
                if len(days): out[p] = days.max()
        return out
    def material_cutoff(label): return we
    def load_curves(pad):
        out = {}
        for n in range(1, 33):
            cur = D['curves'].get(pad, {}).get(n)
            dates = list(cur['dates']) if cur else []
            vals = list(cur['values']) if cur else []
            out[n] = dict(dates=dates, values=vals,
                          status='activa' if dates and max(dates) == we.date() else ('inactiva' if dates else 'sin_datos'))
        return out
    def load_oxido(*a, **k): return load_curves('OXIDOS')
    def load_sulfuro(*a, **k): return load_curves('SULFUROS')
    def active_pilas_by_riego(label, asof, *a, **k):
        r = frames(label)[0]
        r = r[r.index <= pd.Timestamp(asof)].tail(7)
        return {int(p[1:]) for p in r.columns if (r[p].fillna(0) > 0).any()}
    def load_casos(): return [caso]
    flows = [tuple(r) for r in D['flows'].itertuples(index=False)]
    def sql_rows(engine, query, params=None, **kw):
        codes = {v for k, v in (params or {}).items() if str(k).startswith('c')}
        return [r for r in flows if r[0] in codes]
    hist = D['history'].to_dict('records')
    class FakeHistory:
        def load(self, *a, **k): return [dict(r) for r in hist]
    saved = D['saved_profile']

    patches = dict(load_riego=load_riego, load_cu_riego=load_cu_riego, load_drena_cu=load_drena_cu,
                   load_wip=load_wip, inicio_campana=inicio_campana, _fechas_actividad=_fechas_actividad,
                   arranque_en_ventana=arranque_en_ventana, ultimo_riego=ultimo_riego, material_cutoff=material_cutoff,
                   load_oxido=load_oxido, load_sulfuro=load_sulfuro, load_casos=load_casos,
                   load_rec_curves=lambda label=None: ({}, {}, {}), load_riego_ini=lambda *a, **k: {},
                   connect=lambda *a, **k: MagicMock(), limpiar_cache_local=lambda: None,
                   load_saved_profile=lambda *a, **k: saved, get_engine=lambda *a, **k: MagicMock(),
                   HistoryReader=FakeHistory, _sql_rows=sql_rows, active_pilas_by_riego=active_pilas_by_riego, load_produccion=lambda *a, **k: pd.DataFrame(), clear_actividad_cache=lambda: None)
    import importlib, pkgutil, curvas_recon
    mods = [m for m in list(sys.modules.values()) if m and getattr(m, '__name__', '').startswith('curvas_recon')]
    for name, fn in patches.items():
        for m in mods:
            if name in vars(m):
                setattr(m, name, fn)
    # db_pipeline._sql_rows solo para load_caso_anchor
    DB._sql_rows = sql_rows
    P.load_caso_anchor.__globals__['_sql_rows'] = sql_rows
    P.load_oxido = load_oxido; P.load_sulfuro = load_sulfuro
    import traceback
    _orig = P._error_modal_body
    def _eb(*a, **k):
        traceback.print_exc(); return _orig(*a, **k)
    P._error_modal_body = _eb
    return D, caso, P

def make_app(xlsx):
    import dash, dash_bootstrap_components as dbc
    D, caso, P = install(xlsx)
    app = dash.Dash('pad', external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True,
                    title='Curvas', update_title=None)
    app.layout = P.build_layout
    P.register_callbacks(app)
    return app

if __name__ == '__main__':
    app = make_app(sys.argv[1])
    app.run(debug=False, port=int(sys.argv[2]) if len(sys.argv) > 2 else 8070)
