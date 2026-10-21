# -*- coding: utf-8 -*-
"""Cache local de las lecturas contra el SQL Server remoto (149.50.136.234).

El dashboard llama `_load_material_window` desde siete callbacks distintos, y
cada llamada son tres queries: ~8 s por pad, ~16 s por callback. Nada de eso
cambia entre clicks.

El cache NO envuelve a los loaders sino a la lectura cruda, una capa mas
abajo. Es a proposito: los loaders hacen pivot, mezcla con la vista de ingesta
y `ffill()` al final. Sus consultas ya incluyen los limites efectivos y el
lookback de 60 dias necesario para Cu. Se cachea el resultado crudo por
consulta, material y ventana; repetir el mismo Caso no vuelve al servidor y
una ventana corta no transfiere todo el historico.

Persiste en `.cache_datos/` con pickle, asi que reiniciar el proceso tampoco
vuelve a bajar nada. `limpiar()` borra memoria y disco, y la llama el boton
'Actualizar datos' del dashboard.

Variables de entorno:
  `RECON_SIN_CACHE=1`      apaga todo, queda la query directa.
  `RECON_CACHE_TTL_H=<h>`  vida de lo guardado en disco (default 24 h; 0 = sin
                           vencimiento).
"""
import hashlib
import os
import pickle
import threading
import time

import pandas as pd

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache_datos')
ACTIVA = os.environ.get('RECON_SIN_CACHE', '') not in ('1', 'true', 'True')
TTL_S = float(os.environ.get('RECON_CACHE_TTL_H', '24')) * 3600

# Límites usados por la antigua cache `@completo`; se conservan para reconocer
# claves heredadas en inspecciones. La cache por ventanas no los consulta.
RANGO_INI = pd.Timestamp('2000-01-01')
RANGO_FIN = pd.Timestamp('2035-01-01')

_MEM = {}
_STATS = {'hits': 0, 'misses': 0, 'segundos_ahorrados': 0.0}

# Dash atiende los callbacks en hilos: dos pueden fallar el cache sobre la
# MISMA clave a la vez, bajarla dos veces y despues pelearse el archivo. El
# candado es por clave -- uno global serializaria queries independientes.
_LOCK_MAESTRO = threading.Lock()
_LOCKS = {}


def _lock_de(clave):
    with _LOCK_MAESTRO:
        l = _LOCKS.get(clave)
        if l is None:
            l = _LOCKS[clave] = threading.Lock()
        return l


def _clave(etiqueta, crudo):
    return '%s__%s' % (etiqueta, hashlib.md5(repr(crudo).encode()).hexdigest()[:16])


def _ruta(clave):
    return os.path.join(DIR, clave + '.pkl')


def _disco_leer(clave):
    try:
        with open(_ruta(clave), 'rb') as f:
            t, v = pickle.load(f)
    except Exception:
        return None
    if TTL_S and time.time() - t > TTL_S:
        return None
    return v


def _disco_escribir(clave, valor):
    # El temporal lleva pid+hilo: con un nombre fijo, dos escritores de la
    # misma clave se pisan el .tmp y Windows tira WinError 32 al renombrar
    # ('el proceso no tiene acceso al archivo').
    tmp = '%s.%d.%d.tmp' % (_ruta(clave), os.getpid(), threading.get_ident())
    try:
        os.makedirs(DIR, exist_ok=True)
        with open(tmp, 'wb') as f:
            pickle.dump((time.time(), valor), f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, _ruta(clave))
    except Exception as e:
        print('[local_cache] no se pudo escribir %s: %s' % (clave, e))
        try:
            os.remove(tmp)
        except OSError:
            pass


def _traer(clave, produce):
    """Memoria -> disco -> `produce()`, una sola vez por clave.

    El candado por clave existe porque los callbacks de Dash corren en hilos:
    sin el, dos hilos que fallan el cache a la vez bajan lo mismo dos veces
    (dos idas al servidor) y despues escriben el mismo .pkl en paralelo."""
    if clave in _MEM:
        _STATS['hits'] += 1
        return _MEM[clave]
    with _lock_de(clave):
        if clave in _MEM:                   # otro hilo lo bajo mientras esperabamos
            _STATS['hits'] += 1
            return _MEM[clave]
        v = _disco_leer(clave)
        if v is not None:
            _MEM[clave] = v
            _STATS['hits'] += 1
            return v
        t0 = time.time()
        v = produce()
        dt = time.time() - t0
        _STATS['misses'] += 1
        _STATS['segundos_ahorrados'] += dt  # lo que costaria cada repeticion
        _MEM[clave] = v
        _disco_escribir(clave, v)
        print('[local_cache] %s bajado en %.2f s' % (clave.split('__')[0], dt))
        return v


def _etiqueta(query):
    """Nombre legible para los logs: la primera tabla que nombra la query."""
    for t in str(query).replace('\n', ' ').split():
        if '.' in t and not t.startswith(':'):
            return t.split('.')[-1].strip('(),')
    return 'sql'


def sql_df(engine, query, params=None, date_col='fecha'):
    """`pd.read_sql` cacheado. Devuelve siempre una copia: los loaders escriben
    encima del frame que reciben."""
    params = dict(params or {})
    if not ACTIVA:
        return pd.read_sql(query, engine, params=params)

    fechas = [k for k in ('start', 'end') if k in params]
    otros = {k: v for k, v in params.items() if k not in fechas}
    et = _etiqueta(query)

    if not fechas:
        k = _clave(et, (str(query), sorted((a, str(b)) for a, b in otros.items())))
        return _traer(k, lambda: pd.read_sql(query, engine, params=params)).copy()

    # Loaders already pass their effective range, including Cu lookback.
    # Fetching 2000..2035 here transferred full history for every short Case.
    k = _clave(et + '@ventana',
               (str(query), sorted((a, str(b)) for a, b in params.items())))
    return _traer(k, lambda: pd.read_sql(query, engine, params=params)).copy()


def sql_rows(engine, query, params=None, etiqueta=None):
    """`conn.execute(...).fetchall()` cacheado, como lista de tuplas."""
    params = dict(params or {})
    def bajar():
        with engine.connect() as conn:
            return [tuple(r) for r in conn.execute(query, params).fetchall()]
    if not ACTIVA:
        return bajar()
    k = _clave(etiqueta or _etiqueta(query),
               (str(query), sorted((a, str(b)) for a, b in params.items())))
    return list(_traer(k, bajar))


def sql_maps(engine, query, params=None, etiqueta=None):
    """Igual que `sql_rows` pero con `.mappings()`: lista de dicts."""
    params = dict(params or {})
    def bajar():
        with engine.connect() as conn:
            return [dict(r) for r in conn.execute(query, params).mappings().all()]
    if not ACTIVA:
        return bajar()
    k = _clave(etiqueta or _etiqueta(query),
               (str(query), sorted((a, str(b)) for a, b in params.items())))
    return [dict(r) for r in _traer(k, bajar)]


def olvidar(prefijo):
    """Bota solo lo que empiece con `prefijo`. Lo usa `db_pipeline.save_run`:
    despues de guardar una corrida hay que releer las tablas de
    reconciliacion, pero no hace falta volver a bajar el historico de riego."""
    n = 0
    for k in [k for k in _MEM if k.startswith(prefijo)]:
        del _MEM[k]
        n += 1
    try:
        for f in os.listdir(DIR):
            if f.startswith(prefijo) and f.endswith('.pkl'):
                os.remove(os.path.join(DIR, f))
    except FileNotFoundError:
        pass
    return n


def limpiar():
    """Vacia memoria y disco. La llama el boton 'Actualizar datos'."""
    _MEM.clear()
    n = 0
    try:
        for f in os.listdir(DIR):
            if f.endswith('.pkl'):
                os.remove(os.path.join(DIR, f))
                n += 1
    except FileNotFoundError:
        pass
    print('[local_cache] limpiado: %d archivos' % n)
    return n


def estado():
    try:
        arch = [f for f in os.listdir(DIR) if f.endswith('.pkl')]
        mb = sum(os.path.getsize(os.path.join(DIR, f)) for f in arch) / 1e6
    except FileNotFoundError:
        arch, mb = [], 0.0
    return dict(activa=ACTIVA, ttl_h=TTL_S / 3600, en_memoria=len(_MEM),
                en_disco=len(arch), mb=round(mb, 2), **_STATS)
