#!/usr/bin/env python3
"""
recon_engine.py
================
Motor de reconciliacion de pilas de lixiviacion. Combina en un solo modulo:

1. Utilidades base (ex `mhe_recon.py`): carga de datos (WIP/riego/Cu riego/
   Cu drena/produccion) desde la DB online, match produccion<->semana,
   clasificacion transiente/SS por dia de ciclo, calculo experimental de
   W_p/Z_p por pila-semana (`compute_wz_week`) y el prior de Fdrena
   (`fdrena_prior`).

   Todas las cantidades de masa (W, Z, MT, actual, b) estan en TONELADAS.
     factor[t/dia] = Q[m3/h] * 24[h] * Cu[g/L] / 1000   (m3*g/L = 1000L*g/L = 1000g = 1kg -> /1000 = t)

   Balance de masa por pila (dia d):
     Cu_ext[t/d] = factor(d) x (Fdrena x Cu_drena[g/L] - Cu_riego[g/L])
     (positivo = extraccion, Cu sale del mineral hacia la solucion PLS)

   Estados de una pila en la ventana, y no hay mas:
     INACTIVA      sin riego medido -> fuera del pool, no aporta nada.
     ACTIVA        ya venia operando -> reconciliacion uniforme por dia,
                   curva de drenaje plana en la meseta.
     ACTIVA NUEVA  arranca dentro de la ventana (`arranque_en_ventana`,
                   por riego y drenaje reales) -> ramp-up desde su dia 1.
   El corte viejo transiente/SS por `dia_ciclo < TRANSIENT_DAYS` se elimino:
   dependia de `lectura_recuperacion`, que abre campana para todo un pad el
   mismo dia. El ratio rec_pct/max_rec se conserva solo como columna
   informativa.

   Balance semanal para semana k (solo pilas activas esa semana):
     actual_k = Sum_p [ Fdrena_p x W_p^k  -  Z_p^k ]

2. Metodologia de reconciliacion ACTIVA, wireada a `pad_dashboard.py` via
   `reconcile_week_flowsheet_dash` (ex `mhe_recon_flowsheet_updated.py`).
   A diferencia de un ajuste MHE via solver (min Sum_k w_k*(C[k]@f-b[k])^2
   s.a. 0<=f_p<=FDRENA_MAX, con variantes WLS/Ridge/Cauchy -- las funciones
   `lsq_linear`/`minimize` de scipy se conservan importadas para ese uso
   pero el metodo activo hoy NO llama a un solver), este metodo reparte una
   correccion de CAUDAL (riego y PLS) a nivel de planta completa hacia las
   pilas transientes, proporcional al aporte de caudal de cada una. Es un
   calculo cerrado (sin solver), a nivel SEMANAL (un valor por pila por
   semana, no diario).

   Algoritmo (spec del usuario, 2026-07-22):

     Paso 1 - Delta de planta (nivel flowsheet global, TODOS los materiales
     juntos, TODAS las pilas activas esa semana):
         QPLS_medido    = Sum_i Qplsi        (i = toda pila activa)
         QRiego_medido  = Sum_i Qriegoi
         Delta_Recon_PLS   = QPLS_recon   - QPLS_medido
         Delta_Recon_Riego = QRiego_recon - QRiego_medido
       QPLS_recon / QRiego_recon salen de una reconciliacion de flowsheet
       global (balance de planta completo: agua, soluciones, etc.) que HOY NO
       EXISTE en este repo. PLACEHOLDER SINTETICO confirmado por el usuario:
       QX_recon = QX_medido + N(0, (sigma_rel*QX_medido)^2), semilla
       determinista por (semana, variable) -- reproducible, facil de
       reemplazar cuando exista el balance de flowsheet real (buscar
       `_noisy_global`).

     Paso 2 - Estado de cada pila activa: ACTIVA o ACTIVA NUEVA, segun
     `arranque_en_ventana()` (riego y Cu de drenaje, NO la curva de
     recuperacion). Solo las nuevas llevan ramp-up.

     dia_ciclo SIN informacion de futuro: `mat['wip']` (10 Analisis *.xlsx,
     hoja WIP) trae UNA sola fila por pila -- la campana VIGENTE al momento
     en que se cargo el Excel, no un historial. Usar su `ini_aporte` para
     clasificar una semana VIEJA es survivorship: si la pila ya tuvo una
     campana anterior (terminada, reemplazada), esa campana no existe en WIP
     y la pila queda excluida (ini de la campana actual > week_end) en vez de
     clasificarse con su campana real de esa epoca.
     Fix: `_campaign_asof()` reconstruye la campana vigente A ESA SEMANA
     cortando la curva de recuperacion cruda (`pad_data.py` +
     `pad_cycles.split_into_cycles`, historial real 2017-2025 por pila) a
     lecturas <= fin de semana ANTES de segmentar en campanas -- ninguna
     lectura posterior a la semana entra al calculo. Limite real de dato:
     el reporte de curvas (`Reporte_Recuperaciones 31 de Agosto 2025.xlsx`)
     no tiene lecturas mas alla de 2025-08-31; para semanas posteriores no
     hay forma de reconstruir la campana "como se veia entonces" con este
     archivo, se cae a `mat['wip']` (unico dato disponible) con warning
     explicito.

     Paso 3 - Fraccion de aporte de cada pila TRANSIENTE sobre el total
     medido, pesado por VARIANZA propia (no por caudal): pesar por caudal
     da Fracriegoi_i=Qriegoi_i/QRiego_medido, y aporte_i/Qriegoi_i =
     Delta_Recon_Riego/QRiego_medido para TODA pila -- Qriegoi_i se cancela
     algebraicamente y el % de ajuste sale identico para toda pila del pool
     sin importar su tamano. Pesando por la varianza de la lectura diaria de
     cada pila dentro de la semana, la pila mas erratica (menos confiable)
     absorbe mas correccion y la de caudal estable absorbe poco/nada:
         Fracriegoi_i = VarQriegoi_i / Sum_transientes(VarQriegoi_i)
         Fracplsi_i   = Fracriegoi_i  (Qplsi = FDRENA_MAX*Qriegoi siempre,
           la razon de varianzas es la misma con o sin ese factor constante)
         (fallback a Qriegoi_i/QRiego_medido si el pool no tiene varianza,
         ej. solo 1 dia de dato por pila esa semana)

     Paso 4 - Delta a distribuir por pila transiente, y su valor final:
         Dplsi_i   = Fracplsi_i   * Delta_Recon_PLS
         Driegoi_i = Fracriegoi_i * Delta_Recon_Riego
         Qplsi_final_i   = Qplsi_i   + Dplsi_i
         Qriegoi_final_i = Qriegoi_i + Driegoi_i

     Paso 5 - Validacion: `run_report()` corre esto sobre muchas semanas y
     arma un reporte (ver bloque `__main__`), sin persistir en DB ni tocar
     el dashboard.

     Paso 7 - Distribucion diaria del ajuste semanal, DENTRO de cada pila
     ACTIVA (corre despues de paso 4/6, reparte sus resultados semanales
     entre los dias de la ventana -- unico paso diario de este metodo). Ya no
     existe "pila transiente": se reconcilian todas las activas de una pasada,
     el corte TRANSIENTE/SS murio junto con el loop adaptativo:
       Sub-orden: 7a riego, 7b meseta de drenaje, 7c drenaje + Cu. El
       riego va primero porque la curva de drenaje se despeja contra el
       caudal de riego YA reconciliado, no contra el medido.
       7a Riego (Q riego): fraccion = Qriego_dia_medido / Qriegoi_medido_i
         (medido, semanal, de esa pila). Ajuste_dia = fraccion * Driegoi_i
         (paso 4). Qriego_dia_final = Qriego_dia_medido + Ajuste_dia.
       7b/7c Drenaje (Q PLS): el factor de drenaje del dia se resuelve por
         pila, y el metodo BIFURCA segun si la pila arranco DENTRO de la
         ventana (`nace_en_ventana`, o sea `ini_ciclo is not None`):

         (i) PILA EN REGIMEN -- el caso normal (286 de 290 pilas en los 7
         Casos). `_solve_meseta` retorna factor PLANO `target / q_tot` por
         retorno TEMPRANO, antes de cualquier chequeo de cota: la suma diaria
         cierra EXACTO por construccion y la rampa no se aplica. No es un
         atajo: el peso transiente (1-alpha)^(dia_ciclo-1) vale 4.4e-4 al dia
         30 y ~0 al dia 400, asi que la rampa no aporta nada numerico a una
         pila madura, y aplicarsela ensuciaba el diagnostico (una pila de 400
         dias salia marcada 'cap').

         (ii) PILA NUEVA -- se le ajusta la rampa con `ramp_curve.ajustar`:
             f(n) = M - (M - i0) * (1 - alpha)^(n-1)
         M es la ASINTOTA, no un valor que la curva alcance: f(n) < M
         estrictamente para todo n, con M topada en FDRENA_RECON_MAX. Los
         tres parametros NO se despejan por separado ni en etapas: se mueven
         juntos sobre un unico dial continuo `t` en (0,1], la tension de la
         rampa,
             M(t)     = FDRENA_RECON_MAX * t
             i0(t)    = INICIO_FRAC_MAX * t * M(t)
             alpha(t) = alpha_0 + (ALPHA_MAX - alpha_0) * t
         El area semanal S(t) = Sum_dias f(dia_ciclo_d; t) * q_d es continua
         y estrictamente creciente, con S(0) = 0 y S(1) = AREA_MAX, asi que
         `S(t) = target` tiene raiz UNICA y sale con UNA llamada a
         `scipy.optimize.brentq` sobre [0,1] (biseccion de 300 iteraciones de
         respaldo si no hay scipy). Status 'ok'. Lectura fisica: a la pila a
         la que el balance le pide poco PLS le queda meseta baja, arranque
         casi nulo y subida lenta; a la que le pide mucho, arranque alto,
         subida rapida y meseta alta. Mover el target un 1 % mueve la curva
         un poco -- no la cambia de regimen ni de status.
         Si target > AREA_MAX = S(1) NO existe rampa creciente bajo el techo
         que lo entregue: se publica la rampa de t = 1 (i0 =
         INICIO_FRAC_MAX*M, alpha = ALPHA_MAX) y se devuelve `residuo` = lo
         que falto. Status 'infactible', el dia se marca `clipped` y paso 7e
         reparte ese residuo entre las pilas en regimen del pad que tengan
         holgura bajo el techo. Si ninguna la tiene, el faltante se DECLARA:
         el pad esta pidiendo mas drenaje que riego, lo que apunta a descarga
         de inventario interno del lecho, que este metodo no modela.
         Qpls_dia_final = f(dia_ciclo_dia) * Qriego_dia_final.

         Tres constantes de drenaje distintas, no confundirlas:
           FDRENA_MAX       = 0.95  lado MEDIDO. Fabrica Q_PLS_medido = 0.95 *
                                    Q_riego porque no hay flujometro de PLS.
           FDRENA_FLOW_MAX  = 0.99  tope del PAD, aplicado sobre el ANCLA
                                    antes de repartir. Es lo que deja a 70
                                    pilas leyendo Fdrena = 0.9900: son pilas
                                    en regimen, la rampa no las toca.
           FDRENA_RECON_MAX = 0.99  asintota M de la rampa, SOLO pilas nuevas.
         El techo de M es el reconciliado y no 0.95 porque 0.95 es el factor
         MEDIDO: una curva que arranca bajo y debe promediar 0.95 en la
         semana pasa necesariamente de 0.95 en sus dias tardios.
       Cu en riego: fino_dia_medido = Qriego_dia_medido*Cu_riego_dia_medido
         ("produccion" diaria, medida). fraccion_fino_dia = fino_dia_medido /
         Sum_dias(fino_dia_medido) (de esa pila, no de toda la planta).
         aporte_fino_riego_dia = fraccion_fino_dia * aporte_fino_riego_i
         (paso 6). Cu_riego_dia_recon = (fino_dia_medido +
         aporte_fino_riego_dia) / Qriego_dia_final.
       Cu en PLS: mismo patron que Cu riego, con Q/Cu/aporte de PLS.
       Guardrail de paso 4 (Qpls_dia_final < Qriego_dia_final) queda como
       backstop: con f(n) < M <= FDRENA_RECON_MAX < 1 se cumple por
       construccion en la pila nueva, y en la pila en regimen lo garantiza el
       tope FDRENA_FLOW_MAX sobre el ancla del pad.

   Caudal medido por pila (semanal, no diario):
     Qriegoi = q_mean de `compute_wz_week` (promedio de caudal de riego
       medido en los dias con dato de riego Y drena Cu validos esa semana).
     Qplsi   = FDRENA_MAX * Qriegoi -- no existe medicion de CAUDAL de PLS en
       este dataset (`drena_cu_diario` solo mide concentracion, no caudal);
       se usa el mismo supuesto baseline que el resto del repo usa cuando no
       hay Fdrena reconciliado.
"""
import hashlib
import math
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import lsq_linear, minimize
from sqlalchemy import text

from .db_pipeline import get_engine, SCHEMA
# Toda lectura a la DB pasa por aca: cachea el CRUDO (ver local_cache.py),
# asi que cada loader vuelve a correr sus pivots y su ffill sobre la ventana
# que le toca y devuelve lo mismo que devolveria la query directa.
from .local_cache import sql_df as _sql_df, sql_rows as _sql_rows
from .perf_trace import record_phase
from . import pad_data
from .pad_cycles import split_into_cycles
from . import ramp_curve

# ── Configuracion ──────────────────────────────────────────────────────────────
# Conservados solo para scripts legacy (identificar_transientes.py, etc) que aun
# leen Excel directo -- load_wip/load_riego/load_cu_riego/load_drena_cu/
# load_produccion de este modulo ya NO los usan (leen de la DB online).
SULFUROS_FILE = r'C:\Users\5330\Desktop\Recon curvas\10 Análisis Sulfuros.xlsx'
OXIDOS_FILE   = r'C:\Users\5330\Desktop\Recon curvas\10 Análisis Oxidos.xlsx'
PROD_FILE     = r'C:\Users\5330\Desktop\Recon curvas\Produccion.xlsx'

LABEL_MATERIAL = {'OXIDOS': 'OXIDO', 'SULFUROS': 'SULFURO'}
_FFILL_LOOKBACK_DAYS = 60   # margen antes de `start` para que ffill() no caiga en fallback por falta de historia

SS_THRESHOLD   = 0.95           # umbral informativo rec_pct/max_rec (ya no es criterio)
TRANSIENT_DAYS = 30             # N: dia de ciclo < N => transiente (unico umbral; default del input 'Dias activos' del dash, ajustable por semana)
FDRENA_MAX     = 0.95           # limite superior del factor de drenaje / valor SS fijo
TOL_DAYS       = 7              # tolerancia de match semana<->produccion

# El dia de OPERACION no es el dia calendario: va de 08:00 a 08:00 y se rotula
# con su fecha de INICIO (el turno que parte 08:00 del dia D es el dia D, aunque
# cierre a las 08:00 del D+1). La convencion esta en la propia base: en
# `bitacora_turnos_consolidada` el turno B se muestrea entre 07:10 y 09:00 del
# dia calendario SIGUIENTE y queda grabado con `fecha_turno` del dia anterior.
#
# Las series diarias que consume el motor (`riego_diario`,
# `vw_riego_diario_ingest`, `cu_riego_diario`, `drena_cu_diario`) son de tipo
# DATE: ya vienen agregadas por dia y NO traen detalle sub-diario que permita
# re-cortar la ventana. Por eso `OPERATIONAL_DAY_START_HOUR` no reparte de nuevo
# esos valores -- declara la convencion y sirve para bucketear cualquier fuente
# CON hora (bitacoras, eventos de campana) al dia operacional correcto en vez de
# al dia calendario.
OPERATIONAL_DAY_START_HOUR = 8
CU_RIEGO_FALLBACK = 0.5         # g/L, usado cuando no hay dato de Cu riego
CU_RIEGO_COL      = 36          # columna 0-indexed = AK ("Refino"/"Cu++"), hoja 'Riego' -- igual para ambos materiales (spec usuario 2026-07-24)
RIEGO_FLUJO_COLS  = {            # rango 0-indexed [inicio, fin] de columnas de caudal por pila, hoja 'Ajuste Flujos'
    'SULFUROS': (31, 58),        # AF:BG (28 pilas)
    'OXIDOS':   (35, 68),        # AJ:BQ (32 pilas + una columna sobrante 'Factor Ajuste', se descarta por header)
}


# ── Carga de datos ─────────────────────────────────────────────────────────────

def operational_date(ts, hour=OPERATIONAL_DAY_START_HOUR) -> pd.Timestamp:
    """Dia de operacion al que pertenece el instante `ts`, normalizado a
    medianoche para poder compararlo con las columnas DATE de la base.

    El dia de operacion parte a las `hour` y se rotula con su fecha de inicio,
    asi que todo lo ocurrido antes de esa hora pertenece al dia anterior: una
    muestra tomada a las 07:55 del 2026-08-27 es del dia operacional
    2026-08-26. Restar la hora de corte y normalizar hace exactamente eso.

    Sobre una fecha sin hora (medianoche) esto restaria un dia entero, que NO
    es lo que se quiere: una columna DATE ya viene rotulada por dia operacional.
    Por eso el caso sin hora se devuelve tal cual."""
    t = pd.Timestamp(ts)
    if t == t.normalize():          # fecha pura: ya es el dia operacional
        return t
    return (t - pd.Timedelta(hours=hour)).normalize()


def window_bounds(week_start, week_end, hour=OPERATIONAL_DAY_START_HOUR):
    """Instantes reales de apertura y cierre de una ventana de dias
    operacionales: [08:00 del primer dia, 08:00 del dia siguiente al ultimo).

    `resolve_window` devuelve fechas (dias operacionales, rotulados por su
    inicio); esta funcion las convierte en el intervalo de tiempo que de verdad
    cubren, para filtrar fuentes que traen hora. El cierre es exclusivo."""
    ws = pd.Timestamp(week_start).normalize() + pd.Timedelta(hours=hour)
    we = pd.Timestamp(week_end).normalize() + pd.Timedelta(days=1, hours=hour)
    return ws, we


def week_monday(d) -> pd.Timestamp:
    d = pd.Timestamp(d)
    return d - pd.Timedelta(days=d.weekday())


def resolve_window(week_start, week_end=None):
    """(inicio, fin, n_dias) de la ventana de trabajo.

    Las tres cosas estan en DIAS OPERACIONALES, no calendario: cada dia va de
    08:00 a 08:00 y se rotula con su fecha de inicio (ver
    `OPERATIONAL_DAY_START_HOUR`). Para el intervalo de tiempo real que cubre la
    ventana, usar `window_bounds(ws, we)`.

    Sin `week_end` mantiene el comportamiento historico y es lo que usan
    todos los llamadores viejos: snap a lunes + 7 dias corridos. Con
    `week_end` toma la ventana EXACTA que le pasan, sin snap ni relleno --
    es el caso de un Caso de reconciliacion global, cuya ventana
    (`recon_caso.fecha_inicio` .. `fecha_fin`) no tiene por que empezar
    lunes ni durar 7 dias.
    """
    ws = pd.Timestamp(week_start).normalize()
    if week_end is None:
        ws = week_monday(ws)
        we = ws + pd.Timedelta(days=6)
    else:
        we = pd.Timestamp(week_end).normalize()
        if we < ws:
            raise ValueError('ventana invalida: fin %s < inicio %s' % (we.date(), ws.date()))
    return ws, we, int((we - ws).days) + 1


def sanitize_fin(ini, fin):
    """
    Sanea 'Fin ciclo' del WIP. Las hojas traen basura (fechas 2016) en la
    columna Fin ciclo mientras ini_aporte es 2024-2025 -> fin < ini es
    imposible fisicamente. En ese caso (o si fin es NaT) se devuelve NaT,
    de modo que la pila no se declare "terminada" por un dato corrupto.
    """
    if pd.isna(fin):
        return pd.NaT
    if pd.notna(ini) and fin < ini:
        return pd.NaT
    return fin


UNLISTED_GAP_DAYS = 30


def load_riego_ini(label, excluir=(), gap_days=UNLISTED_GAP_DAYS):
    """`ini_aporte` inferido desde el propio riego, para las pilas que NO
    tienen fila en `campana`.

    Existen pilas que riegan pero no son campanas de lixiviacion (zonas de
    riego permanente): P32 de oxidos lleva 2.223 dias regados desde 2016 y
    nunca aparece en campana_parcela_control. Sin esto quedaban FUERA del
    universo del motor y su caudal (~3 % del pad) desaparecia del balance.

    Se toma el inicio del ULTIMO bloque contiguo de riego, tolerando huecos
    de hasta `gap_days` dias. El resultado es estable: para P32 cualquier
    tolerancia >= 15 d da 2025-10-13. Se lee de riego_diario UNION la vista
    de ingesta, porque la tabla consolidada va por detras de la ingesta.
    """
    material = LABEL_MATERIAL[label]
    query = f"""
        SELECT p.nombre AS pila, r.fecha
        FROM (
            SELECT parcela_id, fecha, caudal_m3h FROM {SCHEMA}.riego_diario
            UNION
            SELECT parcela_id, fecha, caudal_m3h FROM {SCHEMA}.vw_riego_diario_ingest
        ) r
        JOIN {SCHEMA}.parcela p ON p.id_parcela = r.parcela_id
        JOIN {SCHEMA}.material m ON m.id = p.id_pad
        WHERE m.nombre = :material AND r.caudal_m3h > 0
    """
    df = _sql_df(get_engine(), text(query), {"material": material})
    out = {}
    if df.empty:
        return out
    df['fecha'] = pd.to_datetime(df['fecha'])
    for pila, g in df.groupby('pila'):
        if pila in excluir:
            continue
        f = g['fecha'].drop_duplicates().sort_values()
        if f.empty:
            continue
        gaps = f.diff().dt.days
        corte = f[(gaps.isna()) | (gaps > gap_days)]
        out[pila] = pd.Timestamp(corte.iloc[-1])
    return out


def load_wip(label, incluir_sin_campana=True):
    """Campana vigente (mas reciente por fecha_inicio) por pila, desde la
    tabla `campana` (poblada por db_pipeline.sync_campana desde
    campana_parcela_control). rec_actual no tiene fuente en la DB y no se
    consume en ningun lado (columna informativa muerta en el Excel original)
    -- se deja en NaN.

    Con `incluir_sin_campana` (default) el WIP deja de ser el unico universo:
    se agregan las pilas que tienen riego real pero ninguna campana, con
    `ini_aporte` inferido por `load_riego_ini` y `sin_campana=True`. Sin
    esto el motor reconciliaba sobre un pad incompleto y la diferencia de
    universo contra el Caso habia que absorberla aplicando el ancla como
    razon."""
    material = LABEL_MATERIAL[label]
    query = f"""
        WITH ranked AS (
            SELECT p.nombre AS pila, c.fecha_inicio, c.fecha_fin, c.cu_tf,
                ROW_NUMBER() OVER (PARTITION BY c.parcela_id ORDER BY c.fecha_inicio DESC) AS rn
            FROM {SCHEMA}.campana c
            JOIN {SCHEMA}.parcela p ON p.id_parcela = c.parcela_id
            JOIN {SCHEMA}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material
        )
        SELECT pila, fecha_inicio, fecha_fin, cu_tf FROM ranked WHERE rn = 1
    """
    rows = _sql_rows(get_engine(), text(query), {"material": material})
    if not rows:
        print(f'[recon_engine] load_wip({label!r}): 0 filas -- sin campana vigente en la tabla campana.')
    pilas = {}
    for pila, ini, fin, cutf in rows:
        pilas[pila] = dict(
            ini_aporte=pd.Timestamp(ini) if ini is not None else pd.NaT,
            fin_ciclo=pd.Timestamp(fin) if fin is not None else pd.NaT,
            CuTf=float(cutf) if cutf is not None else np.nan,
            rec_actual=np.nan,
            sin_campana=False,
        )
    if incluir_sin_campana:
        extra = load_riego_ini(label, excluir=set(pilas))
        for pila, ini in sorted(extra.items()):
            pilas[pila] = dict(
                ini_aporte=ini,
                fin_ciclo=pd.NaT,
                CuTf=np.nan,
                rec_actual=np.nan,
                sin_campana=True,
            )
        if extra:
            print('[recon_engine] load_wip(%r): +%d pila(s) con riego pero sin '
                  'campana: %s' % (label, len(extra),
                                   ', '.join('%s (ini %s)' % (p, d.date())
                                             for p, d in sorted(extra.items()))))
    _campana_vencida(label, pilas)
    return pilas


_CAMPANA_ATRASADA_CACHE = {}


def _campana_atrasada(label):
    """{pila: (campana viva, campana en la tabla)} de las pilas cuya campana
    vigente todavia no esta en `campana`.

    `campana` se llena desde `campana_parcela_control`, que solo trae modulos
    con `fecha_ini_drenaje`; una campana recien apilada no aparece ahi hasta
    que la cargan. `Recuperaciones_pad`, en cambio, ya viene con el numero de
    campana del dia. Al 2026-08 son 30 pilas: los sulfuros P15-P24 riegan la
    campana 11 y la tabla solo tiene la 10, cerrada el 2025-05-05.

    No se compara por fecha: `fecha_fin_drenaje` va sistematicamente por
    detras del riego real (58 de 60 pilas siguen regando despues del cierre
    nominal), asi que un criterio de fechas avisa de todo y no sirve de nada.
    El numero de campana si distingue.
    """
    if label in _CAMPANA_ATRASADA_CACHE:
        return _CAMPANA_ATRASADA_CACHE[label]
    query = f"""
        WITH viva AS (
            SELECT parcela_id, MAX(TRY_CAST(Campana AS INT)) AS camp_viva
            FROM {SCHEMA}.Recuperaciones_pad
            WHERE Fecha_drenaje >= DATEADD(day, -60,
                  (SELECT MAX(Fecha_drenaje) FROM {SCHEMA}.Recuperaciones_pad))
            GROUP BY parcela_id
        ), tab AS (
            SELECT parcela_id, MAX(TRY_CAST(numero_campana AS INT)) AS camp_tab
            FROM {SCHEMA}.campana GROUP BY parcela_id
        )
        SELECT pa.nombre, v.camp_viva, t.camp_tab
        FROM viva v
        LEFT JOIN tab t ON t.parcela_id = v.parcela_id
        JOIN {SCHEMA}.parcela pa ON pa.id_parcela = v.parcela_id
        JOIN {SCHEMA}.material m ON m.id = pa.id_pad
        WHERE m.nombre = :material
          AND (t.camp_tab IS NULL OR v.camp_viva > t.camp_tab)
    """
    try:
        rows = _sql_rows(get_engine(), text(query), {"material": LABEL_MATERIAL[label]})
    except Exception as e:
        print('[recon_engine] _campana_atrasada(%r): %s' % (label, e))
        rows = []
    out = {p: (viva, tab) for p, viva, tab in rows}
    _CAMPANA_ATRASADA_CACHE[label] = out
    return out


def _campana_vencida(label, pilas):
    """Avisa de las pilas que reconcilian contra el CuTf de la campana anterior.

    No rompe la curva: las campanas de una misma pila mueven ~1 Mt a ~0,55 %
    CuT, asi que el Cu fino de la anterior sirve de sustituto del orden
    correcto y las curvas reconciliadas siguen a las medidas. Pero el
    denominador NO es el de la campana que se esta reconciliando, y eso hay
    que decirlo en vez de dejarlo silencioso.
    """
    atras = {p: v for p, v in _campana_atrasada(label).items() if p in pilas}
    if not atras:
        return
    print('[recon_engine] load_wip(%r): %d pila(s) con la campana vigente aun no '
          'cargada en `campana`; la curva usa el CuTf de la anterior: %s'
          % (label, len(atras),
             ', '.join('%s (viva %s, tabla %s)' % (p, v, t if t is not None else '-')
                       for p, (v, t) in sorted(atras.items(),
                                               key=lambda kv: int(kv[0][1:])))))


def load_rec_curves(label=None):
    """Stub -- rec_curves/ciclo_dias ya no tienen fuente en la DB. Confirmado
    (2026-07) que classify_piles() solo usa esto para `rec_ratio`, que a su
    vez es descartado por el metodo de flowsheet (metodo activo). Con
    rec_curves={} la clasificacion sigue funcionando igual (rec_ratio=0.0
    para todas las pilas, sin efecto en ningun output real)."""
    return {}, {}, {}


_ACTIVIDAD_CACHE = {}


def _fechas_actividad(label):
    """({pila: fechas con riego > 0}, {pila: fechas con Cu++ de drenaje > 0}),
    historico completo, cacheado por label.

    Lee la consolidada UNION la vista de ingesta en las dos series, por la
    misma razon de siempre: la consolidada va por detras de la ingesta y una
    pila recien encendida aparece primero en la vista.
    """
    if label in _ACTIVIDAD_CACHE:
        return _ACTIVIDAD_CACHE[label]
    material = LABEL_MATERIAL[label]

    def _fechas(query):
        df = _sql_df(get_engine(), text(query), {"material": material})
        out = {}
        if df.empty:
            return out
        df['fecha'] = pd.to_datetime(df['fecha']).dt.normalize()
        for pila, g in df.groupby('pila'):
            out[pila] = pd.DatetimeIndex(g['fecha'].drop_duplicates().sort_values())
        return out

    riego = _fechas(f"""
        SELECT p.nombre AS pila, r.fecha
        FROM (
            SELECT parcela_id, fecha FROM {SCHEMA}.riego_diario
            WHERE caudal_m3h > 0
            UNION
            SELECT parcela_id, fecha FROM {SCHEMA}.vw_riego_diario_ingest
            WHERE caudal_m3h > 0
        ) r
        JOIN {SCHEMA}.parcela p ON p.id_parcela = r.parcela_id
        JOIN {SCHEMA}.material m ON m.id = p.id_pad
        WHERE m.nombre = :material
    """)
    drena = _fechas(f"""
        SELECT p.nombre AS pila, d.fecha
        FROM (
            SELECT parcela_id, fecha FROM {SCHEMA}.drena_cu_diario
            WHERE cu_gl > 0
            UNION
            SELECT parcela_id, fecha FROM {SCHEMA}.vw_drena_quimica_ingest
            WHERE cu_gl > 0
        ) d
        JOIN {SCHEMA}.parcela p ON p.id_parcela = d.parcela_id
        JOIN {SCHEMA}.material m ON m.id = p.id_pad
        WHERE m.nombre = :material
    """)
    _ACTIVIDAD_CACHE[label] = (riego, drena)
    return riego, drena


def clear_actividad_cache():
    """Vacia `_ACTIVIDAD_CACHE` y `_CAMPANA_CACHE`. Llamar tras un sync de DB,
    igual que `clear_curve_cache()`."""
    _ACTIVIDAD_CACHE.clear()
    _CAMPANA_CACHE.clear()


def arranque_en_ventana(label, week_start, week_end, gap_days=UNLISTED_GAP_DAYS):
    """{pila: Timestamp del primer dia de riego} para las pilas que ARRANCAN
    dentro de [week_start, week_end].

    Criterio (dato duro de operacion, NO la curva de recuperacion):
    una pila es nueva si dentro de la ventana tiene su primer dia de riego y
    ANTES de la ventana no venia ni regando ni drenando -- ni riego > 0 ni
    Cu++ de drenaje > 0 en los `gap_days` dias previos al arranque.

    Antes esto se decidia con `dia_ciclo <= largo de la ventana`, o sea con la
    campana reconstruida desde `lectura_recuperacion`. Esa fuente tiene un
    hoyo (sin datos entre 2026-06-01 y 2026-07-31) y `Recuperaciones_pad` abre
    la campana 18 el 2026-08-01 para TODO el pad de golpe: con ese criterio el
    Caso 21 daba 37 pilas "nuevas" el mismo dia, todas con ramp-up y casi
    todas topando en `cap`. El riego y el drenaje no tienen ese hoyo.

    `gap_days` (30 d, `UNLISTED_GAP_DAYS`) es la misma tolerancia con la que
    `load_riego_ini` corta bloques de riego: una pila parada mas de un mes que
    vuelve a regar es campana nueva, no continuacion.
    """
    ws, we = pd.Timestamp(week_start), pd.Timestamp(week_end)
    riego, drena = _fechas_actividad(label)
    out = {}
    for pila, fechas in riego.items():
        en_ventana = fechas[(fechas >= ws) & (fechas <= we)]
        if not len(en_ventana):
            continue                       # no rego en la ventana: no arranca
        ini = en_ventana[0]
        desde = ini - pd.Timedelta(days=gap_days)
        previo_riego = fechas[(fechas >= desde) & (fechas < ini)]
        fd = drena.get(pila, pd.DatetimeIndex([]))
        previo_drena = fd[(fd >= desde) & (fd < ini)]
        if len(previo_riego) or len(previo_drena):
            continue                       # ya venia operando: no es nueva
        out[pila] = ini
    return out


_CAMPANA_CACHE = {}


def pilas_jovenes(label, week_start, week_end, max_age_days=30):
    """{pila: primer riego} de las pilas que riegan en la ventana y tienen
    `max_age_days` dias o menos desde el primer riego real de su campana
    vigente al cierre. Mismo criterio de edad que el ajuste de Sulfuros
    (dias calendario transcurridos); si el resultado esta vacio no hay
    curvas nuevas que ajustar."""
    ws, we = pd.Timestamp(week_start).normalize(), pd.Timestamp(week_end).normalize()
    riego, _ = _fechas_actividad(label)
    out = {}
    for pila, ini in inicio_campana(label, we).items():
        fechas = riego.get(pila)
        if fechas is None or not len(fechas[(fechas >= ws) & (fechas <= we)]):
            continue
        if (we - pd.Timestamp(ini).normalize()).days <= max_age_days:
            out[pila] = ini
    return out


def inicio_campana(label, asof, gap_days=UNLISTED_GAP_DAYS):
    """{pila: Timestamp del primer dia de riego de la campana VIGENTE a `asof`}.

    Es `arranque_en_ventana()` sin la restriccion de que el arranque caiga
    dentro de la ventana: sirve para fechar el dia de ciclo de una pila que ya
    venia operando. Mismo criterio y misma fuente -- riego y Cu de drenaje, NO
    `lectura_recuperacion`, que tiene el hoyo de junio-julio 2026 y le pone dia
    de ciclo chico a pilas maduras.

    El bloque vigente se corta hacia atras: se recorre la actividad (riego
    UNION drenaje) desde el ultimo dia y se para en el primer hueco de mas de
    `gap_days` dias. Una pila parada mas de un mes que vuelve a regar es
    campana nueva, no continuacion -- igual que en `load_riego_ini`.
    """
    asof = pd.Timestamp(asof).normalize()
    key = (label, asof, gap_days)
    if key in _CAMPANA_CACHE:
        return _CAMPANA_CACHE[key]
    riego, drena = _fechas_actividad(label)
    out = {}
    for pila, fechas in riego.items():
        fr = fechas[fechas <= asof]
        if not len(fr):
            continue                       # todavia no rego: no hay campana
        fd = drena.get(pila, pd.DatetimeIndex([]))
        act = fr.union(fd[fd <= asof]) if len(fd) else fr
        # Fechas normalizadas: diferencia vectorizada, mismo corte > gap_days.
        # Evita indexar/convertir miles de Timestamp uno a uno por cada pila.
        cortes = np.flatnonzero((act[1:] - act[:-1]) > pd.Timedelta(days=gap_days))
        ini = act[int(cortes[-1]) + 1] if len(cortes) else act[0]
        # El dia 1 del ciclo es el primer dia de RIEGO del bloque (el drenaje
        # de un bloque no puede empezar antes que su riego, pero si el dato
        # llega desordenado esto lo deja en el riego igual).
        del_bloque = fr[fr >= ini]
        out[pila] = del_bloque[0] if len(del_bloque) else ini
    _CAMPANA_CACHE[key] = out
    return out


def load_riego(label, start=None, end=None):
    """Caudal de riego diario por pila, desde riego_diario (DB), acotado a
    [start, end] si se especifican."""
    material = LABEL_MATERIAL[label]
    where_range, params = "", {"material": material}
    if start is not None:
        where_range += " AND r.fecha >= :start"
        params["start"] = start
    if end is not None:
        where_range += " AND r.fecha <= :end"
        params["end"] = end
    def _q(source):
        return f"""
            SELECT r.fecha, p.nombre AS pila, r.caudal_m3h
            FROM {SCHEMA}.{source} r
            JOIN {SCHEMA}.parcela p ON p.id_parcela = r.parcela_id
            JOIN {SCHEMA}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material {where_range}
        """

    # `riego_diario` es la tabla consolidada y va por detras de la ingesta:
    # para julio 2026 tiene 0 filas mientras la vista de ingesta tiene el
    # periodo completo. Sin este relleno la reconciliacion de un Caso de julio
    # corre con caudal cero y "cierra" perfecto contra la nada.
    #
    # El relleno es POR FECHA, no todo-o-nada: una ventana corta caia bien con
    # el `if df.empty` original (la consolidada no tenia NADA de julio), pero
    # un rango largo (p.ej. desde el inicio de ciclo de la pila hasta hoy, que
    # es lo que necesitan las curvas completas) trae filas viejas, deja de
    # estar vacio, y julio/agosto quedaban en cero sin aviso. Mismo criterio
    # que load_cu_riego/load_drena_cu: la consolidada manda donde tiene dato.
    def _wide(frame):
        frame = frame.copy()
        frame['fecha'] = pd.to_datetime(frame['fecha']).dt.normalize()
        return frame.pivot_table(index='fecha', columns='pila',
                                 values='caudal_m3h', aggfunc='first').sort_index()

    df = _sql_df(get_engine(), text(_q('riego_diario')), params)
    wide = _wide(df) if not df.empty else pd.DataFrame()

    ing = _sql_df(get_engine(), text(_q('vw_riego_diario_ingest')), params)
    if not ing.empty:
        ing_wide = _wide(ing)
        falta = ing_wide.index.difference(wide.index)
        if len(falta):
            print(f'[recon_engine] load_riego({label!r}, {start}, {end}): '
                  f'riego_diario no cubre {len(falta)} dias '
                  f'({falta.min().date()}..{falta.max().date()}); se completan '
                  f'desde vw_riego_diario_ingest.')
            wide = pd.concat([wide, ing_wide.loc[falta]]).sort_index()

    if wide.empty:
        print(f'[recon_engine] load_riego({label!r}, {start}, {end}): 0 filas -- '
              f'ni riego_diario ni vw_riego_diario_ingest tienen datos en ese rango.')
        return pd.DataFrame()
    return wide.apply(pd.to_numeric, errors='coerce').fillna(0)


def ultimo_riego(label, pilas, before):
    """Ultimo dia con caudal de riego > 0 por pila, anterior a `before`.

    Sirve para calificar una pila que no rego en la ventana: si el ultimo
    riego fue hace meses la pila esta EN REPOSO (ciclo terminado, campana
    todavia abierta en el WIP), y si fue anteayer es una caida de medicion.

    La consolidada y la vista de ingesta traen 0.0 EXPLICITO para la pila
    apagada, asi que el corte es `caudal_m3h > 0`, no IS NOT NULL. Se calcula
    el maximo de ambas fuentes en SQL y se devuelve una fila por pila.
    """
    if not pilas:
        return {}
    material = LABEL_MATERIAL[label]
    nombres = sorted(set(pilas))
    binds = {f'p{i}': n for i, n in enumerate(nombres)}
    lista = ', '.join(f':{k}' for k in binds)
    params = dict(binds, material=material, before=before)
    query = f"""
        SELECT x.pila, MAX(x.ultima) AS ultima
        FROM (
            SELECT p.nombre AS pila, MAX(r.fecha) AS ultima
            FROM {SCHEMA}.riego_diario r
            JOIN {SCHEMA}.parcela p ON p.id_parcela = r.parcela_id
            JOIN {SCHEMA}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material AND p.nombre IN ({lista})
              AND r.fecha < :before AND r.caudal_m3h > 0
            GROUP BY p.nombre
            UNION ALL
            SELECT p.nombre AS pila, MAX(r.fecha) AS ultima
            FROM {SCHEMA}.vw_riego_diario_ingest r
            JOIN {SCHEMA}.parcela p ON p.id_parcela = r.parcela_id
            JOIN {SCHEMA}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material AND p.nombre IN ({lista})
              AND r.fecha < :before AND r.caudal_m3h > 0
            GROUP BY p.nombre
        ) x
        GROUP BY x.pila
    """
    df = _sql_df(get_engine(), text(query), params)
    out = {}
    for _, row in df.iterrows():
        f = pd.Timestamp(row['ultima'])
        if pd.notna(f):
            out[row['pila']] = f
    return out


# Las tablas consolidadas de quimica (`cu_riego_diario`, `drena_cu_diario`) NO
# son la fuente: las llena `db_pipeline.sync_cu_riego()` / `sync_drena_data()`
# por MERGE desde las vistas de ingesta, y van por detras de esas vistas cuando
# el sync no corre. En 2026-08 la ingesta llegaba al dia 23 y las consolidadas
# cortaban el dia 11: el Caso 23 (2026-08-15..22) quedaba con CERO leyes de Cu.
# Mismo problema y misma solucion que `riego_diario` -> `vw_riego_diario_ingest`
# en load_riego(): se lee la consolidada y se COMPLETA con la vista de ingesta
# solo en las fechas que la consolidada no tiene. La consolidada manda donde si
# tiene dato, asi que ningun caso ya calculado cambia de numero.
_RIEGO_REFINO_VIEW = {'OXIDO': 'vw_riego_oxido_refino_base',
                      'SULFURO': 'vw_riego_sulfuro_refino_base'}


def _cu_riego_ingest(material, start, end):
    """Serie de Cu++ de refino desde la vista de ingesta del material.

    La vista expone `cu_pp`, que es el mismo numero que el `cu_gl` de la
    consolidada (verificado igual dia a dia en todo el solape), sobre una
    `fecha` DATE ya agregada."""
    view = _RIEGO_REFINO_VIEW.get(material)
    if view is None:
        return pd.Series(dtype=float)
    where, params = "", {}
    if start is not None:
        where += " AND v.fecha >= :start"
        params["start"] = pd.Timestamp(start) - pd.Timedelta(days=_FFILL_LOOKBACK_DAYS)
    if end is not None:
        where += " AND v.fecha <= :end"
        params["end"] = end
    df = _sql_df(get_engine(), text(f"""
        SELECT v.fecha, CAST(v.cu_pp AS FLOAT) AS cu_gl
        FROM {SCHEMA}.{view} v
        WHERE 1 = 1 {where}
        ORDER BY v.fecha"""), params)
    if df.empty:
        return pd.Series(dtype=float)
    idx = pd.to_datetime(df['fecha']).dt.normalize()
    ts = pd.Series(df['cu_gl'].values, index=idx.values)
    return ts[ts.index.notna()].sort_index()


def _drena_cu_ingest(material, start, end):
    """Cu de drenaje por pila desde `vw_drena_quimica_ingest` (unpivot de las
    tablas anchas `drena_concentrados_*`). La vista aplica NULLIF(...,0): una
    pila que ya no drena llega como NaN y no como cero, que es lo correcto --
    el ffill del final la deja en su ultima ley conocida en vez de hundirla."""
    where, params = "", {"material": material}
    if start is not None:
        where += " AND v.fecha >= :start"
        params["start"] = pd.Timestamp(start) - pd.Timedelta(days=_FFILL_LOOKBACK_DAYS)
    if end is not None:
        where += " AND v.fecha <= :end"
        params["end"] = end
    df = _sql_df(get_engine(), text(f"""
        SELECT v.fecha, p.nombre AS pila, v.cu_gl
        FROM {SCHEMA}.vw_drena_quimica_ingest v
        JOIN {SCHEMA}.parcela p ON p.id_parcela = v.parcela_id
        JOIN {SCHEMA}.material m ON m.id = p.id_pad
        WHERE m.nombre = :material {where}"""), params)
    if df.empty:
        return pd.DataFrame()
    df['fecha'] = pd.to_datetime(df['fecha']).dt.normalize()
    wide = df.pivot_table(index='fecha', columns='pila', values='cu_gl', aggfunc='first')
    return wide.sort_index().apply(pd.to_numeric, errors='coerce')


def load_cu_riego(label, start=None, end=None, fill=True):
    """Serie unica de Cu++ refino de riego por material, desde cu_riego_diario
    (DB). Se aplica un margen de lookback antes de `start` (no `end`, por la
    regla de no usar datos futuros) para que el ffill() no caiga en el
    fallback por falta de historia justo al inicio de la ventana."""
    material = LABEL_MATERIAL[label]
    where_range, params = "", {"material": material}
    if start is not None:
        where_range += " AND c.fecha >= :start"
        params["start"] = pd.Timestamp(start) - pd.Timedelta(days=_FFILL_LOOKBACK_DAYS)
    if end is not None:
        where_range += " AND c.fecha <= :end"
        params["end"] = end
    query = f"""
        SELECT c.fecha, c.cu_gl
        FROM {SCHEMA}.cu_riego_diario c
        JOIN {SCHEMA}.material m ON m.id = c.material_id
        WHERE m.nombre = :material {where_range}
        ORDER BY c.fecha
    """
    df = _sql_df(get_engine(), text(query), params)
    if df.empty:
        ts = pd.Series(dtype=float)
    else:
        dates = pd.to_datetime(df['fecha']).dt.normalize()
        ts = pd.Series(df['cu_gl'].values, index=dates.values)
        ts = ts[ts.index.notna()].sort_index()

    # Completar SOLO las fechas que la consolidada no trae (ver comentario de
    # _cu_riego_ingest): donde la consolidada tiene dato, manda ella.
    ing = _cu_riego_ingest(material, start, end)
    if not ing.empty:
        falta = ing.index.difference(ts.index)
        if len(falta):
            print(f'[recon_engine] load_cu_riego({label!r}, {start}, {end}): '
                  f'cu_riego_diario no cubre {len(falta)} dias '
                  f'({falta.min().date()}..{falta.max().date()}); se completan '
                  f'desde {_RIEGO_REFINO_VIEW[material]}.')
            ts = pd.concat([ts, ing.loc[falta]]).sort_index()

    if ts.empty:
        print(f'[recon_engine] load_cu_riego({label!r}, {start}, {end}): 0 filas -- '
              f'ni cu_riego_diario ni la vista de ingesta tienen datos en ese rango.')
        return pd.Series(dtype=float, name='cu_riego')
    ts.name = 'cu_riego'
    if not fill:                       # lecturas tal cual: sin ffill ni respaldo
        return ts
    return ts.ffill().fillna(CU_RIEGO_FALLBACK)


def load_drena_cu(label, start=None, end=None, fill=True):
    """Cu_pp de drenaje por pila, desde drena_cu_diario (DB). Mismo margen de
    lookback que load_cu_riego, por la misma razon (ffill por pila)."""
    material = LABEL_MATERIAL[label]
    where_range, params = "", {"material": material}
    if start is not None:
        where_range += " AND d.fecha >= :start"
        params["start"] = pd.Timestamp(start) - pd.Timedelta(days=_FFILL_LOOKBACK_DAYS)
    if end is not None:
        where_range += " AND d.fecha <= :end"
        params["end"] = end
    query = f"""
        SELECT d.fecha, p.nombre AS pila, d.cu_gl
        FROM {SCHEMA}.drena_cu_diario d
        JOIN {SCHEMA}.parcela p ON p.id_parcela = d.parcela_id
        JOIN {SCHEMA}.material m ON m.id = p.id_pad
        WHERE m.nombre = :material {where_range}
    """
    df = _sql_df(get_engine(), text(query), params)
    if df.empty:
        wide = pd.DataFrame()
    else:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.normalize()
        wide = df.pivot_table(index='fecha', columns='pila', values='cu_gl',
                              aggfunc='first').sort_index()
        wide = wide.apply(pd.to_numeric, errors='coerce')

    # Mismo criterio que load_cu_riego: solo las FECHAS que faltan. No se
    # mezcla pila por pila dentro de una fecha ya cubierta, porque ahi la
    # consolidada conserva lecturas que la vista ya no expone (pilas apagadas
    # cuyo `*_cu_pp` quedo en 0 y la vista convierte a NULL).
    ing = _drena_cu_ingest(material, start, end)
    if not ing.empty:
        falta = ing.index.difference(wide.index)
        if len(falta):
            print(f'[recon_engine] load_drena_cu({label!r}, {start}, {end}): '
                  f'drena_cu_diario no cubre {len(falta)} dias '
                  f'({falta.min().date()}..{falta.max().date()}); se completan '
                  f'desde vw_drena_quimica_ingest.')
            wide = pd.concat([wide, ing.loc[falta]]).sort_index()

    if wide.empty:
        print(f'[recon_engine] load_drena_cu({label!r}, {start}, {end}): 0 filas -- '
              f'ni drena_cu_diario ni vw_drena_quimica_ingest tienen datos en ese rango.')
        return pd.DataFrame()
    return wide.sort_index().ffill() if fill else wide.sort_index()


def active_pilas_by_riego(label, cutoff, window_days=21):
    """Numeros de pila con caudal de riego real (`caudal_m3h > 0`) dentro de
    los ultimos `window_days` dias hasta `cutoff`, leido directo de
    riego_diario. Filtra 'activa' SOLO por fecha de dato operativo -- NO por
    clasificacion de curva de recuperacion (`lectura_recuperacion`, hasta 70
    dias atrasada -- confirmado que `campana.finished`/`fecha_fin` tampoco
    sirve como senal de actividad: la fuente los prellena con una fecha
    PLANIFICADA al iniciar la campana, no la fecha real de cierre -- todas
    las filas, incluida la campana vigente, llegan con finished=True)."""
    material = LABEL_MATERIAL[label]
    cutoff = pd.Timestamp(cutoff)
    start = cutoff - pd.Timedelta(days=window_days)
    # Igual que `load_riego`, no se puede depender solo de la tabla
    # materializada: la ingesta suele llegar dias antes. La consolidada manda
    # por FECHA y la ingesta rellena solo fechas ausentes, exactamente como el
    # cargador; un UNION simple mezclaria ambos valores si difieren.
    query = f"""
        SELECT p.nombre AS pila
        FROM (
            SELECT parcela_id, fecha, caudal_m3h FROM {SCHEMA}.riego_diario
            UNION
            SELECT i.parcela_id, i.fecha, i.caudal_m3h
            FROM {SCHEMA}.vw_riego_diario_ingest i
            WHERE NOT EXISTS (
                SELECT 1 FROM {SCHEMA}.riego_diario c
                JOIN {SCHEMA}.parcela cp ON cp.id_parcela = c.parcela_id
                JOIN {SCHEMA}.material cm ON cm.id = cp.id_pad
                WHERE cm.nombre = :material AND c.fecha = i.fecha
            )
        ) r
        JOIN {SCHEMA}.parcela p ON p.id_parcela = r.parcela_id
        JOIN {SCHEMA}.material m ON m.id = p.id_pad
        WHERE m.nombre = :material AND r.fecha >= :start AND r.fecha <= :cutoff AND r.caudal_m3h > 0
        GROUP BY p.nombre
    """
    rows = _sql_rows(get_engine(), text(query), {"material": material, "start": start, "cutoff": cutoff})
    return {int(pila[1:]) for (pila,) in rows}


def material_cutoff(label):
    """Ultima fecha con dato real EN LAS TRES series de este material (riego,
    cu_riego, drena_cu) -- la serie que termina antes acota al resto (mismo
    criterio que los cargadores híbridos). Incluye las vistas de ingesta para
    no congelar el dashboard en la ultima sincronización materializada."""
    material = LABEL_MATERIAL[label]
    query = f"""
        SELECT MAX(fecha) FROM (
            SELECT MAX(r.fecha) AS fecha
            FROM {SCHEMA}.riego_diario r
            JOIN {SCHEMA}.parcela p ON p.id_parcela = r.parcela_id
            JOIN {SCHEMA}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material
            UNION ALL
            SELECT MAX(r.fecha)
            FROM {SCHEMA}.vw_riego_diario_ingest r
            JOIN {SCHEMA}.parcela p ON p.id_parcela = r.parcela_id
            JOIN {SCHEMA}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material
        ) riego
        UNION ALL
        SELECT MAX(fecha) FROM (
            SELECT MAX(c.fecha) AS fecha
            FROM {SCHEMA}.cu_riego_diario c
            JOIN {SCHEMA}.material m ON m.id = c.material_id
            WHERE m.nombre = :material
            UNION ALL
            SELECT MAX(c.fecha)
            FROM {SCHEMA}.vw_riego_oxido_refino_base c
            WHERE :material = 'OXIDO'
            UNION ALL
            SELECT MAX(c.fecha)
            FROM {SCHEMA}.vw_riego_sulfuro_refino_base c
            WHERE :material = 'SULFURO'
        ) cu_riego
        UNION ALL
        SELECT MAX(fecha) FROM (
            SELECT MAX(d.fecha) AS fecha
            FROM {SCHEMA}.drena_cu_diario d
            JOIN {SCHEMA}.parcela p ON p.id_parcela = d.parcela_id
            JOIN {SCHEMA}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material
            UNION ALL
            SELECT MAX(d.fecha)
            FROM {SCHEMA}.vw_drena_quimica_ingest d
            JOIN {SCHEMA}.parcela p ON p.id_parcela = d.parcela_id
            JOIN {SCHEMA}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material AND d.cu_gl IS NOT NULL
        ) drena
    """
    rows = _sql_rows(get_engine(), text(query), {"material": material})
    maxes = [pd.Timestamp(r[0]) for r in rows if r[0] is not None]
    if not maxes:
        print(f'[recon_engine] material_cutoff({label!r}): sin MAX(fecha) en riego/cu_riego/drena, incluyendo ingesta.')
    return min(maxes) if maxes else None


def load_produccion(start=None, end=None):
    """Produccion catodica real diaria, desde produccion_planta (DB). Margen
    de TOL_DAYS antes de `start` para no excluir candidatos de
    match_production justo en el borde de la ventana -- no se extiende
    despues de `end` (regla de no usar datos futuros)."""
    where_range, params = "", {}
    if start is not None:
        where_range += " AND fecha >= :start"
        params["start"] = pd.Timestamp(start) - pd.Timedelta(days=TOL_DAYS)
    if end is not None:
        where_range += " AND fecha <= :end"
        params["end"] = end
    query = f"SELECT fecha, valor_t FROM {SCHEMA}.produccion_planta WHERE 1=1 {where_range}"
    df = _sql_df(get_engine(), text(query), params)
    if df.empty:
        print(f'[recon_engine] load_produccion({start}, {end}): 0 filas -- produccion_planta sin datos en ese rango.')
        return pd.Series(dtype=float, name='produccion_cu')
    dates = pd.to_datetime(df['fecha'])
    ts = pd.Series(df['valor_t'].values, index=dates.values, name='produccion_cu')
    return ts[ts.index.notna()].sort_index()


# ── Match produccion <-> semana (unico, con dedup) ──────────────────────────────

def match_production(week, produccion, used_idx=None, tol_days=TOL_DAYS):
    """
    Empareja `week` (lunes) con el indice mas cercano de `produccion` que no
    este ya en `used_idx`, dentro de `tol_days`.

    Retorna (actual_t | None, idx | None). El llamador debe agregar `idx` a
    `used_idx` si lo usa, para evitar reutilizar la misma fila de produccion.
    """
    if len(produccion) == 0:
        return None, None
    used_idx = used_idx or set()
    diffs = np.abs((produccion.index - week).days).to_numpy(dtype=float)
    for i in used_idx:
        diffs[i] = np.inf
    idx = int(np.argmin(diffs))
    if diffs[idx] > tol_days:
        return None, None
    return float(produccion.iloc[idx]), idx


# ── Clasificacion transiente / SS ────────────────────────────────────────────────

def classify_piles(week_start, wip, rec_curves, max_rec, ciclo_dias,
                    transient_days=TRANSIENT_DAYS, ss_threshold=SS_THRESHOLD,
                    week_end=None):
    """
    Clasifica pilas activas/transiente/SS segun dia de ciclo < transient_days.
    day_e se calcula al punto medio de la semana (dia +3) para reducir sesgo;
    la ventana de actividad (pila iniciada) se evalua SOLO contra `ini_aporte`
    (fecha real de inicio de aporte). `fin_ciclo` NO se usa para excluir --
    la fuente (`campana_parcela_control.fecha_fin_drenaje`) lo prellena con
    una fecha PLANIFICADA al iniciar la campana, no la fecha real de cierre;
    usarlo como corte apagaba pilas con riego real vigente. rec_pct/max_rec
    se calcula solo como informacion.
    """
    week_start, week_end, n_days = resolve_window(week_start, week_end)
    week_mid = week_start + pd.Timedelta(days=(n_days - 1) // 2)
    active, transient, ss = [], [], []
    day_in_cycle, rec_ratio = {}, {}

    for p, info in wip.items():
        ini = info['ini_aporte']
        if pd.isna(ini) or ini > week_end:
            continue

        day_e  = max(1, (week_mid - ini).days + 1)
        day_in_cycle[p] = day_e

        m_rec = max_rec.get(p, 0.0)
        if p in rec_curves and m_rec > 0:
            days_arr, vals_arr = rec_curves[p]
            rec_pct = float(np.interp(day_e, days_arr, vals_arr))
            rec_ratio[p] = rec_pct / m_rec
        else:
            rec_ratio[p] = 0.0

        active.append(p)
        if day_e < transient_days:
            transient.append(p)
        else:
            ss.append(p)

    return active, transient, ss, day_in_cycle, rec_ratio


# ── Calculo experimental W y Z por pila/semana ───────────────────────────────────

def compute_wz_week(week_start, active_piles, riego, cu_riego, drena_cu, week_end=None):
    """
    Para cada pila activa en la semana, calcula (en toneladas):
      W_p = Sum_dias factor(d) * Cu_drena_p(d)
      Z_p = Sum_dias factor(d) * Cu_riego(d)
      factor(d) = Q_p(d)[m3/h] * 24 / 1000

    Escalamiento: n_irr = dias con riego (q>0); n = dias con q>0 Y Cu_drena
    valido. Si 0 < n < n_irr (i.e. hay dias regados sin dato de Cu_drena),
    W y Z se escalan por n_irr/n para compensar SOLO los dias con Cu_drena
    faltante. Una pila regada deliberadamente pocos dias (n == n_irr) NO se
    infla. n_days se devuelve como n (dias con dato completo); tambien se
    devuelve n_irr.
    """
    week_start, week_end, n_days = resolve_window(week_start, week_end)
    result = {}

    for p in active_piles:
        if p not in riego.columns:
            result[p] = dict(W=0.0, Z=0.0, n_days=0, n_irr=0, q_mean=0.0,
                              cu_d_mean=np.nan, cu_r_mean=np.nan)
            continue

        W, Z, n, n_irr = 0.0, 0.0, 0, 0
        q_list, cud_list, cur_list = [], [], []

        for day_offset in range(n_days):
            d = week_start + pd.Timedelta(days=day_offset)
            if d > week_end:
                break
            if d not in riego.index:
                continue

            q = float(riego.at[d, p])
            if q <= 0:
                continue
            n_irr += 1

            cu_r = CU_RIEGO_FALLBACK
            if d in cu_riego.index:
                v = cu_riego.at[d]
                cu_r = float(v) if pd.notna(v) else CU_RIEGO_FALLBACK

            cu_d = np.nan
            if p in drena_cu.columns and d in drena_cu.index:
                v = drena_cu.at[d, p]
                if pd.notna(v):
                    cu_d = float(v)

            if np.isnan(cu_d):
                continue

            factor = q * 24.0 / 1000.0   # -> toneladas
            W += factor * cu_d
            Z += factor * cu_r
            n += 1
            q_list.append(q)
            cud_list.append(cu_d)
            cur_list.append(cu_r)

        if 0 < n < n_irr:
            scale = n_irr / n
            W *= scale
            Z *= scale

        result[p] = dict(
            W        = W,
            Z        = Z,
            n_days   = n,
            n_irr    = n_irr,
            q_mean   = float(np.mean(q_list))   if q_list   else 0.0,
            cu_d_mean= float(np.mean(cud_list)) if cud_list else np.nan,
            cu_r_mean= float(np.mean(cur_list)) if cur_list else np.nan,
        )
    return result


# ── Fdrena prior: menor para pilas jovenes ────────────────────────────────────────

def fdrena_prior(day_in_cycle, p, f_min=0.40, f_max=FDRENA_MAX, ramp_days=TRANSIENT_DAYS):
    """Prior de Fdrena: rampa desde f_min (dia 1) hasta f_max al dia ramp_days."""
    d = day_in_cycle.get(p, ramp_days)
    if d >= ramp_days:
        return f_max
    return f_min + (f_max - f_min) * (d / ramp_days)


# ═══════════════════════════════════════════════════════════════════════════════
# Metodologia de flowsheet (metodo ACTIVO, wireado a pad_dashboard.py)
# ═══════════════════════════════════════════════════════════════════════════════

# Peso del reparto de paso 4: 'caudal' (frac_i = q_i/q_pool, % de ajuste
# igual para toda pila, imposible dejar caudal negativo) o 'varianza'
# (frac_i = var_i/sum(var), % distinto por pila pero necesita recorte).
PESO_PASO4 = 'caudal'

N_TRANSIENT_DEFAULT = 7   # dia_ciclo < esto => transiente (propio de este metodo)
SIGMA_REL_DEFAULT = 0.03   # ruido sintetico relativo del placeholder de flowsheet
# Techo de la MESETA de la curva de drenaje (paso 7). NO es FDRENA_MAX.
# FDRENA_MAX=0.95 es el factor MEDIDO -- el proxy con que se estima Q PLS
# porque no existe caudalimetro de PLS. La meseta vive del lado
# RECONCILIADO y es otra cosa: una curva que arranca en 0.1 y tiene que
# promediar ~0.95 en la semana necesariamente pasa de 0.95 en sus dias
# tardios, asi que topar la meseta en FDRENA_MAX volvia infactible
# cualquier curva que no fuera plana -- toda pila con dia_ciclo finito
# caia en 'cap' y la expansion adaptativa se tragaba el pool entero.
# El limite fisico real es drenar < regar, o sea 1.0; 0.99 deja el margen.
# Ojo con leer ese 1.0 como ley: vale para una pila EN REGIMEN. En una ventana
# corta una pila puede entregar mas PLS que el riego de esos dias, porque
# ademas del riego descarga INVENTARIO INTERNO -- solucion retenida en el lecho
# de riegos anteriores. El motor de curvas solo ve el riego de la ventana, asi
# que esa desacumulacion no tiene por donde entrar y aparece como un Fdrena
# pedido >= 1. El techo la corta; el faltante se declara, no se reparte.
FDRENA_RECON_MAX = 0.99

# Tope del factor de drenaje del PAD en la reconciliacion POR FLUJOS (paso 1),
# que es otra cosa que los dos anteriores: FDRENA_MAX es el factor MEDIDO con
# que se estima el Q PLS de cada pila, y FDRENA_RECON_MAX topa la MESETA de la
# curva de ramp-up. El ancla, en cambio, entra como dos razones independientes
# (`q_riego_recon/q_riego_medido` y `q_pls_recon/q_pls_medido`) tomadas del run
# oficial, y nada obligaba a que su cociente respetara el limite fisico: un run
# malo podia pedir Q PLS > Q riego, o sea drenar mas de lo que se riega. Paso en
# los casos 19 (Fdrena 1.0107) y 23 (1.0016) de sulfuros.
#
# El tope NO corrige el run: recorta el Q PLS reconciliado al maximo fisico,
# deja constancia en `warnings` y publica el valor crudo en el resultado
# (`fdrena_flow_raw`, `q_pls_recon_raw`) para que el ancla mala quede visible en
# vez de propagarse callada a la recuperacion. 0.99 deja el mismo margen que
# FDRENA_RECON_MAX; subirlo a 1.0 solo atajaria lo estrictamente imposible.
FDRENA_FLOW_MAX = 0.99

# Piso de AVISO del factor de drenaje del pad. NO recorta y no mueve ningun
# numero: el limite fisico es unilateral (no se puede drenar mas de lo que se
# riega, pero SI se puede drenar mucho menos -- lecho absorbiendo, riego
# reciente sobre material seco), asi que un piso duro inventaria PLS. Existe
# solo porque el diagnostico era asimetrico: el lado alto tiene dos topes
# (FDRENA_FLOW_MAX sobre el ancla, FDRENA_RECON_MAX sobre la rampa) mas su
# warning, y el lado bajo no tenia nada -- el caso 19 de oxidos corrio una
# ventana entera con Fdrena 0.5778 en las 22 pilas, 40 % del riego sin
# aparecer como PLS, y no dijo una palabra. 0.70 esta bien debajo del 0.95
# medido: no lo cruza un pad operando normal.
FDRENA_FLOW_MIN_WARN = 0.70

# La ley de PLS de una pila RECIEN APILADA sube muy por encima de la mediana
# de su pad -- caso 21 sulfuros: 16 de 18 pilas entre 1,16 y 2,62 g/L, P22 en
# 14,65 y P23 en 27,00 -- y decae a lo normal en unas cuatro semanas. Eso es
# real: el primer flujo arrastra el cobre soluble del mineral fresco. NO se
# recorta. Si la curva de recuperacion de esa pila se dispara, el problema
# esta en el DENOMINADOR (el Cu fino contenido de la campana), no en la ley.
RAMP_INITIAL_DEFAULT = 0.1  # factor de drenaje, dia_ciclo=1 (paso 7)
# Velocidad de acercamiento a la meseta (alpha_0, extremo flojo del dial). Se
# toma de `ramp_curve`, que la deriva de DIAS_RAMPA: no es un numero suelto,
# es "cerrar el 99 % del hueco a la meseta al dia 2*DIAS_RAMPA". Los
# incrementos son DECRECIENTES (el esquema viejo era lineal, +0.1 por dia,
# y subia parejo hasta chocar con un `min(..., cap)`; una pila nueva no drena
# asi, sube mientras el lecho se satura y despues se aplana).
RAMP_ALPHA_DEFAULT = ramp_curve.RAMP_ALPHA

# CUANTOS DIAS DURA EL ARRANQUE. El ramp-up ya no es privilegio de la semana
# en que la pila nace: aplica mientras el dia de ciclo sea <= DIAS_RAMPA, y la
# curva esta anclada al dia 1 de riego real, no al lunes de la ventana. La
# semana de arranque ve los dias 1-7 de la curva, la siguiente los dias 8-14,
# y asi hasta el dia DIAS_RAMPA; despues la pila entra en regimen (curva plana
# en la meseta), sin salto porque al dia DIAS_RAMPA la rampa ya cerro el 99 %
# del hueco.
#
# Antes el corte era la ventana: desde el lunes siguiente al arranque la pila
# drenaba plana contra el techo. Contra la hoja de la planta eso deja un
# exceso de PLS de +18,8 % en oxidos y +31,0 % en sulfuros, y el 94-98 % de
# ese exceso vive en los dias 1-60 de ciclo (`Detalle_Diferencias`): la
# saturacion del lecho no se cierra en siete dias.
#
# El dia de ciclo con que se decide esto NO es `dia_ciclo` de la fila (que
# viene de `lectura_recuperacion` y tiene el hoyo de junio-julio 2026): es el
# del ancla de actividad, `inicio_campana()`. Ese hoyo fue justamente lo que
# obligo a restringir el ramp-up a la ventana -- con el dia de ciclo malo la
# meseta se topaba en FDRENA_RECON_MAX y una pila de 400 dias salia marcada
# 'cap', disparando la expansion adaptativa del pool sin motivo.
DIAS_RAMPA = ramp_curve.DIAS_RAMPA

_CURVE_CACHE = {}  # label -> {num_parcela(int): {dates, values, status}}


def _pad_curve(label):
    """Historial crudo de curva de recuperacion (`pad_data.py`, fuente
    Reporte_Recuperaciones 31 de Agosto 2025.xlsx) para `label`
    ('OXIDOS'/'SULFUROS'), cacheado -- clave num de parcela (int)."""
    if label not in _CURVE_CACHE:
        loader = pad_data.load_oxido if label == 'OXIDOS' else pad_data.load_sulfuro
        _CURVE_CACHE[label] = loader()
    return _CURVE_CACHE[label]


def clear_curve_cache():
    """Vacia `_CURVE_CACHE`. Llamar despues de un sync de DB para que la
    proxima lectura de curvas refleje datos frescos (la caché nunca expira
    sola -- ver pad_dashboard.refresh_data_caches)."""
    _CURVE_CACHE.clear()


def _campaign_asof(label, p_name, week_end):
    """Dia de ciclo de `p_name` (ej. 'P7') vigente A `week_end`,
    reconstruido cortando su curva cruda a lecturas <= week_end ANTES de
    segmentar en campanas (`split_into_cycles`) -- ninguna lectura futura
    entra al calculo. None si no hay dato de curva hasta esa fecha (pila
    sin lecturas todavia, o semana mas alla del tope 2025-08-31 del
    reporte) -> el llamador debe hacer fallback a WIP en ese caso."""
    curve = _pad_curve(label)
    try:
        num = int(p_name[1:])
    except (ValueError, IndexError):
        return None
    p = curve.get(num)
    if not p or not p.get('dates'):
        return None
    week_end_date = pd.Timestamp(week_end).date()
    cut = [(d, v) for d, v in zip(p['dates'], p['values']) if d <= week_end_date]
    if not cut:
        return None
    cycles = split_into_cycles([d for d, _ in cut], [v for _, v in cut], week_end_date)
    if not cycles:
        return None
    start = cycles[-1]['start_date']
    return (week_end_date - start).days + 1


def _noisy_global(week_start, salt, measured, sigma_rel):
    """Placeholder sintetico para un target de flowsheet GLOBAL (un solo
    escalar por semana). Semilla determinista -> misma semana siempre da el
    mismo valor sintetico (reproducible, necesario si esto llega a
    persistirse). Swap point: cuando exista un balance de flowsheet real,
    reemplazar esta funcion por la lectura de ese resultado."""
    # hash() built-in esta sujeto a randomizacion por proceso (PYTHONHASHSEED)
    # -> NO es estable entre corridas pese al comentario original; usar un
    # hash estable (md5) para que la semilla sea realmente reproducible.
    key = f'{week_start}|{salt}'.encode('utf-8')
    seed = int(hashlib.md5(key).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    v = float(measured)
    # Ruido MULTIPLICATIVO (log-normal), no aditivo: `measured` es siempre
    # una cantidad fisica no-negativa (caudal, masa de fino). v*exp(eps) es
    # > 0 para cualquier eps -- nunca puede cruzar cero. Un Gaussiano aditivo
    # si podia (v + normal(...) < 0), generando un target sintetico invalido
    # desde el origen -- causa raiz de los negativos rio abajo.
    return v * float(np.exp(rng.normal(0.0, sigma_rel)))


def _ramp_factor(dia_ciclo, meseta, initial=RAMP_INITIAL_DEFAULT, alpha=RAMP_ALPHA_DEFAULT):
    """Factor de drenaje (Fdrena) del dia `dia_ciclo` de operacion de una pila:

        f(n) = meseta - (meseta - initial) * (1 - alpha)^(n-1)

    Arranca SIEMPRE en `initial` el dia 1 y se acerca geometricamente a
    `meseta` -- con initial=0.1, meseta=0.95 y alpha=4/17 da la serie
    0.10, 0.30, 0.45, 0.57, 0.63... La serie lineal anterior
    (factor(n)=factor(n-1)+0.1) subia parejo y necesitaba `min(..., cap)`
    para no pasar de 1; esta converge sola y nunca cruza la meseta, asi que
    Qpls_dia = f*Qriego_dia respeta Qpls < Qriego por construccion mientras
    meseta <= FDRENA_MAX.

    `meseta` NO es constante: `_solve_meseta` la despeja pila por pila para
    que la suma semanal del drenaje diario calce con el Q PLS reconciliado
    del paso 4. Para una pila madura (dia_ciclo grande) (1-alpha)^(n-1) ~ 0
    y f = meseta todos los dias, o sea el reparto degenera al pro-rata de
    siempre; la curva solo se nota en pilas nuevas, que es donde importa.

    dia_ciclo < 1 -> 0.0 (la pila todavia no operaba ese dia)."""
    if dia_ciclo is None or dia_ciclo < 1:
        return 0.0
    return meseta - (meseta - initial) * (1.0 - alpha) ** (float(dia_ciclo) - 1.0)


def _solve_meseta(days, target, cap, initial=RAMP_INITIAL_DEFAULT, alpha=RAMP_ALPHA_DEFAULT,
                   nace_en_ventana=None):
    """Despeja la meseta de la curva de drenaje de UNA pila para que el
    drenaje diario sume el Q PLS reconciliado de esa pila (paso 4):

        Sum_dias f(dia_ciclo_d; meseta) * Qriego_dia_final_d = target

    `f` es AFIN en `meseta`, asi que esto sale en forma cerrada -- no hace
    falta bisectar ni iterar. Con b_d = (1-alpha)^(dia_ciclo_d - 1):

        Sum q_d * [meseta - (meseta - initial) * b_d] = target
        meseta * A + initial * B = target,  A = Sum q_d*(1-b_d), B = Sum q_d*b_d
        meseta = (target - initial*B) / A

    Ojo: el peso es Qriego_dia_FINAL (ya reconciliado en 7a), no el medido --
    "respetar los flujos reconciliados" significa que el drenaje se despeja
    contra el riego que quedo despues del paso 4, no contra el crudo.

    `cap` es FDRENA_RECON_MAX, no FDRENA_MAX: la meseta es la ASINTOTA de la
    curva, no su promedio semanal, asi que tiene que poder quedar por encima
    del factor medido 0.95 para que la semana promedie 0.95.

    Devuelve (meseta, status):
      'regimen' la pila NO nace en la ventana -- su dia 1 de ciclo quedo antes
               del periodo -- asi que no hay arranque que modelar y el ramp-up
               no se aplica. La meseta devuelta es el factor plano
               target/Sum q_d y el drenaje diario queda proporcional al riego
               reconciliado. Cierra exacto y NO pasa por el tope `cap`: ese
               tope acota una curva de ramp-up, no el drenaje en regimen.
      'ok'     meseta cae en [0, cap]; el cierre semanal es exacto.
      'cap'    el target exige una meseta > cap: la pila es demasiado nueva
               para drenar eso. Se topa en `cap` y la suma diaria queda POR DEBAJO del
               target: el llamador marca `clipped` y eso dispara la expansion
               adaptativa del pool transiente, que es la salida correcta --
               antes esta condicion se absorbia callada reescalando pesos, o
               sea se publicaba un Fdrena diario fisicamente imposible con tal
               de cerrar la suma.
      'scaled' el target queda por debajo de lo que da la curva con meseta=0
               (piso initial*b_d el dia 1). Se conserva la forma y se reescala.
      'flat'   la pila no tuvo ningun dia con riego reconciliado en la
               ventana, o la meseta no mueve la suma (todos los dias regados
               en dia_ciclo=1). Cae a reparto proporcional."""
    # `nace_en_ventana` lo decide el llamador con `arranque_en_ventana()`:
    # riego y Cu++ de drenaje, no la curva de recuperacion. El fallback de
    # abajo (dia de ciclo mas alto <= largo de la ventana) queda solo para
    # llamadas sueltas que no pasan el flag; NO usarlo como criterio de
    # negocio -- depende de `lectura_recuperacion`, que tiene el hoyo de
    # junio-julio 2026 y abria campana nueva para todo un pad el mismo dia.
    if nace_en_ventana is None:
        dcs = [d['dia_ciclo'] for d in days if d['dia_ciclo'] is not None]
        nace_en_ventana = bool(dcs) and max(dcs) <= len(days)

    A = B = q_tot = 0.0
    for d in days:
        if d['q_riego_medido'] <= 0 or d['q_riego_final'] <= 0:
            continue
        if d['dia_ciclo'] is None or d['dia_ciclo'] < 1:
            continue
        q = d['q_riego_final']
        b = (1.0 - alpha) ** (float(d['dia_ciclo']) - 1.0)
        A += q * (1.0 - b)
        B += q * b
        q_tot += q
    if q_tot <= 1e-12:
        return initial, 'flat'
    if not nace_en_ventana:
        # La pila ya venia operando antes de la ventana: no hay arranque que
        # modelar. Se salta el ramp-up y el drenaje va proporcional al riego
        # reconciliado -- el llamador reescala con esta meseta, asi que la
        # suma semanal cierra exacta contra el target sin tope ni clip.
        return (target / q_tot), 'regimen'
    if A <= 1e-12:
        # Todos los dias con riego caen en dia_ciclo=1, o sea b_d = 1 para
        # todos: la meseta se cancela dentro de la suma (A = Sum q*(1-b) = 0)
        # y no hay ecuacion que despejar -- dividir aca era el
        # ZeroDivisionError. Es el caso 'flat' que ya describe el docstring:
        # la curva es constante en `initial` y el llamador reparte el Q PLS
        # proporcional al riego reconciliado.
        return (target / q_tot), 'flat'
    meseta = (target - initial * B) / A
    if meseta > cap:
        # Para una pila madura la curva ya esta plana y la meseta sale
        # exactamente = q_pls_final/q_riego_final = FDRENA_MAX; el redondeo
        # de punto flotante la deja a veces un ulp por encima y eso no es un
        # clip real.
        return cap, ('ok' if meseta <= cap * (1 + 1e-9) else 'cap')
    if meseta < 0.0:
        return 0.0, 'scaled'
    return meseta, 'ok'


_RAMP_ESTADO = {}   # (label, pila, ancla) -> {inicio_ventana: estado de cierre}


def limpiar_estado_rampa():
    """Vacia el estado de rampa arrastrado entre semanas. Llamar antes de
    recorrer una serie de semanas distinta (otro caso, otra ventana base)."""
    _RAMP_ESTADO.clear()


def _distribute_daily_pile(label, p, week_start, mat, pile_row, ramp_cap, warnings,
                            ramp_initial=RAMP_INITIAL_DEFAULT, ramp_alpha=RAMP_ALPHA_DEFAULT,
                            week_end=None, ini_ciclo=None, ini_campana=None):
    """Paso 7: reparte los resultados SEMANALES de `pile_row` (ya con paso
    4/6 aplicados) entre los 7 dias de `week_start`. Devuelve lista de 7
    dict (uno por dia). Sin solver: la curva de drenaje es afin en su
    meseta, asi que el "goal seek" se resuelve cerrado en `_solve_meseta`.

    Orden: primero 7a (riego diario), porque la meseta del drenaje se
    despeja contra el riego YA reconciliado; despues 7b (meseta) y 7c
    (drenaje + Cu)."""
    dia_ciclo_end = pile_row['dia_ciclo']
    riego_df = mat['riego']
    cu_riego_s = mat['cu_riego']
    drena_cu_df = mat['drena_cu']

    week_start, _week_end, n_days = resolve_window(week_start, week_end)
    # `dia_ciclo` de `pile_row` esta tomado al CIERRE de la ventana, asi que
    # el del primer dia es ese menos (n_dias - 1), no menos 6 fijo.
    dia_ciclo_lunes = (dia_ciclo_end - (n_days - 1)) if dia_ciclo_end is not None else None

    # Pila que ARRANCA dentro de la ventana (`ini_ciclo`, de
    # `arranque_en_ventana()`): el dia de ciclo se cuenta desde su primer dia
    # de riego real, no desde la campana de `lectura_recuperacion`. Asi el
    # dia 1 del ramp-up es el dia que efectivamente empezo a regar.
    nace_en_ventana = ini_ciclo is not None
    if nace_en_ventana:
        ini_ciclo = pd.Timestamp(ini_ciclo).normalize()

    # ANCLA DE LA RAMPA. La rampa dura `DIAS_RAMPA` dias, o sea cruza varias
    # ventanas, asi que necesita un dia 1 que no dependa de la ventana: el
    # primer dia de riego de la campana vigente (`inicio_campana()`, mismo
    # criterio y misma fuente que `arranque_en_ventana()`). Para la pila que
    # nace aca las dos coinciden; para la que ya venia rampando, esta es la
    # unica que existe.
    #
    # El dia de ciclo del ancla se guarda APARTE de `d['dia_ciclo']`: ese
    # ultimo sigue viniendo de `lectura_recuperacion` y lo leen otros pasos
    # (transiente, informes). Mezclarlos cambiaria la clasificacion de medio
    # pad por un cambio que es solo de la curva de drenaje.
    ancla = ini_ciclo if nace_en_ventana else (
        pd.Timestamp(ini_campana).normalize() if ini_campana is not None else None)

    days = []
    for offset in range(n_days):
        date = week_start + pd.Timedelta(days=offset)
        if nace_en_ventana:
            dc = (date - ini_ciclo).days + 1
            dia_ciclo_dia = dc if dc >= 1 else None   # dias previos al arranque
        else:
            dia_ciclo_dia = (dia_ciclo_lunes + offset) if dia_ciclo_lunes is not None else None

        dc_ancla = ((date - ancla).days + 1) if ancla is not None else None
        if dc_ancla is not None and dc_ancla < 1:
            dc_ancla = None                    # dia previo al arranque real

        q_riego_dia = float(riego_df.at[date, p]) if (p in riego_df.columns and date in riego_df.index) else 0.0
        q_riego_dia = q_riego_dia if q_riego_dia > 0 else 0.0

        cu_riego_dia = np.nan
        if date in cu_riego_s.index:
            v = cu_riego_s.at[date]
            if pd.notna(v):
                cu_riego_dia = float(v)

        cu_pls_dia = np.nan
        if p in drena_cu_df.columns and date in drena_cu_df.index:
            v = drena_cu_df.at[date, p]
            if pd.notna(v):
                cu_pls_dia = float(v)

        q_pls_dia = FDRENA_MAX * q_riego_dia
        fino_riego_dia = q_riego_dia * cu_riego_dia if (q_riego_dia > 0 and pd.notna(cu_riego_dia)) else 0.0
        fino_pls_dia = q_pls_dia * cu_pls_dia if (q_pls_dia > 0 and pd.notna(cu_pls_dia)) else 0.0

        days.append(dict(
            date=date, dia_ciclo=dia_ciclo_dia, dia_rampa=dc_ancla,
            q_riego_medido=q_riego_dia, cu_riego_medido=cu_riego_dia, fino_riego_medido=fino_riego_dia,
            q_pls_medido=q_pls_dia, cu_pls_medido=cu_pls_dia, fino_pls_medido=fino_pls_dia,
        ))

    sum_riego = sum(d['q_riego_medido'] for d in days)
    sum_fino_riego = sum(d['fino_riego_medido'] for d in days)
    sum_fino_pls = sum(d['fino_pls_medido'] for d in days)
    n_irr = sum(1 for d in days if d['q_riego_medido'] > 0)

    # --- 7a: caudal de riego diario ---------------------------------------
    for d in days:
        if sum_riego > 0:
            frac_riego_dia = d['q_riego_medido'] / sum_riego
        else:
            frac_riego_dia = (1.0 / n_irr) if n_irr > 0 else (1.0 / n_days)
            warnings.append(f'{label}/{p} {d["date"].date()}: sin riego medido esta semana, ajuste de riego repartido parejo (paso 7).')
        d['frac_riego_dia'] = frac_riego_dia
        d['d_riego'] = frac_riego_dia * pile_row['d_riego']
        d['q_riego_final'] = d['q_riego_medido'] + d['d_riego']

    # --- 7b: meseta de la curva de drenaje --------------------------------
    # Pila que ARRANCA en la ventana: la curva se ajusta con la meseta acotada
    # por `ramp_cap` y cierre exacto (`_fit_ramp_cap`). Pila en regimen: la
    # curva es plana y `_solve_meseta` la resuelve directo.
    ramp_daily = None
    ramp_inicio = ramp_initial
    ramp_alpha_fit = ramp_alpha
    pile_row['ramp_residuo'] = 0.0

    # La pila esta EN ARRANQUE mientras su dia de ciclo (el del ancla) no pase
    # de DIAS_RAMPA. No basta con que nazca en la ventana: la rampa dura un
    # mes y la ventana una semana.
    dcs_utiles = [d['dia_rampa'] for d in days
                  if d['q_riego_medido'] > 0 and d['dia_rampa'] is not None]
    en_rampa = bool(dcs_utiles) and min(dcs_utiles) <= DIAS_RAMPA
    pile_row['dia_rampa_ini'] = min(dcs_utiles) if dcs_utiles else None
    pile_row['en_rampa'] = en_rampa

    # ESTADO ARRASTRADO. La reconciliacion es semanal: la ventana anterior
    # dejo a la pila en un factor de drenaje concreto el ultimo dia que rego.
    # Esta ventana PARTE DE AHI (modo continuacion de `ramp_curve.ajustar`) y
    # sigue subiendo hacia el techo; no reinicia la rampa ni salta a la
    # meseta. Solo se usa el estado de una ventana ANTERIOR: recalcular la
    # misma semana dos veces tiene que dar lo mismo.
    # El `<=` no es `<`: las ventanas de caso COMPARTEN el dia del borde
    # (`fecha_fin` es inclusiva), asi que el ultimo dia regado de la ventana
    # anterior suele ser el primero de esta. Ahi la continuacion evalua k = 0
    # y el dia arranca exactamente en el factor heredado, que es lo correcto:
    # es el mismo dia, no un salto.
    est_key = (label, p, ancla)
    historial = _RAMP_ESTADO.setdefault(est_key, {})
    anteriores = [s for inicio, s in historial.items()
                  if inicio < week_start and dcs_utiles
                  and s['n'] <= min(dcs_utiles)]
    est = max(anteriores, key=lambda s: s['week_start']) if anteriores else None

    # Beyond day 30, continue the inherited factor across all later windows.
    # Protect the fitted daily shape from the residual redistribution step.
    transicion = bool(not en_rampa and est)
    pile_row['transition_protected'] = transicion
    pile_row['transicion_suave'] = transicion
    if en_rampa or transicion:
        qs = [d['q_riego_final'] if d['q_riego_medido'] > 0 else 0.0 for d in days]
        ds = [d['dia_rampa'] for d in days]
        if transicion:
            _fit = ramp_curve.ajustar_regimen_suave(
                qs, ds, pile_row['q_pls_final'], ramp_cap,
                est['f'], est['n'], alpha=est['alpha'])
        else:
            _fit = ramp_curve.ajustar(
                qs, ds, pile_row['q_pls_final'], ramp_cap,
                alpha=(est['alpha'] if est else ramp_alpha),
                f0=(est['f'] if est else None), n0=(est['n'] if est else None))
        ramp_daily = _fit['factores']
        ramp_status = _fit['status']
        meseta = _fit['meseta']
        ramp_inicio = _fit['inicio']
        # `alpha` es parte de lo que el dial despeja en el arranque (y se
        # HEREDA en la continuacion): la curva de esta pila hay que evaluarla
        # con el alpha que quedo, no con el default.
        ramp_alpha_fit = _fit['alpha']
        pile_row['ramp_tension'] = _fit['tension']
        pile_row['ramp_residuo'] = _fit['residuo']
        pile_row['ramp_entregado'] = _fit['entregado']
        pile_row['ramp_modo'] = _fit['modo']
        if _fit['status'] != 'sin_riego' and _fit['n_fin'] is not None:
            fase = ('rampa' if en_rampa else
                    'regimen' if abs(_fit['f_fin']-_fit['meseta']) <= 0.002
                    else 'transicion')
            estado = dict(week_start=week_start, n=_fit['n_fin'],
                          f=_fit['f_fin'], alpha=_fit['alpha'], fase=fase)
            # Conservar las ventanas anteriores permite repetir esta sin
            # perder su empalme. Si cambia el cierre, los estados posteriores
            # deben recalcularse a partir del nuevo resultado.
            if historial.get(week_start) != estado:
                for inicio in list(historial):
                    if inicio > week_start:
                        del historial[inicio]
            historial[week_start] = estado
    else:
        meseta, ramp_status = _solve_meseta(days, pile_row['q_pls_final'], ramp_cap,
                                             ramp_initial, ramp_alpha,
                                             nace_en_ventana=nace_en_ventana)
    if ramp_status in ('piso', 'infactible'):
        warnings.append(
            f'{label}/{p} (edad={pile_row["dia_rampa_ini"]}): el objetivo semanal '
            f'{pile_row["q_pls_final"]:.3f} queda fuera del perfil factible '
            f'({ramp_status}). Se entrega {_fit["entregado"]:.3f}, conservando '
            f'el empalme y el techo {ramp_cap:.2f}; el residuo firmado '
            f'{pile_row["ramp_residuo"]:.3f} se compensa entre pilas elegibles '
            f'o queda como termino pendiente de balance (paso 7e).')
    elif ramp_status == 'scaled':
        warnings.append(
            f'{label}/{p}: el Q PLS final semanal ({pile_row["q_pls_final"]:.3f}) queda por debajo del '
            f'piso de la curva de ramp-up (meseta=0); forma conservada y curva reescalada (paso 7).')
    elif ramp_status == 'flat':
        warnings.append(
            f'{label}/{p}: sin riego reconciliado en la ventana (o todos los dias en dia_ciclo=1), '
            f'la meseta no mueve la suma; Q PLS repartido proporcional al riego final (paso 7).')

    ramp_inicio_semana = _ramp_factor(
        (dia_ciclo_lunes - 1) if dia_ciclo_lunes is not None else None,
        meseta, ramp_inicio, ramp_alpha_fit)

    for i_d, d in enumerate(days):
        d['ramp_meseta'] = meseta
        d['ramp_status'] = ramp_status
        d['ramp_inicio_semana'] = ramp_inicio_semana
        if d['q_riego_medido'] <= 0:
            d['ramp_factor'] = 0.0
        elif ramp_daily is not None:
            # Pila que arranca en la ventana: la curva ES el ramp-up desde el
            # dia 1 de riego real, resuelto por `ramp_curve.ajustar` (no se
            # recalcula con `_ramp_factor`: ese no conoce el f(1) ni el alpha
            # que el ajuste despejo).
            d['ramp_factor'] = ramp_daily[i_d]
        else:
            # Regimen: no hay arranque que modelar, la curva es PLANA en la
            # meseta. No se usa `dia_ciclo` aca a proposito: viene de
            # `lectura_recuperacion`, que tiene el hoyo de junio-julio 2026 y
            # le pone dia_ciclo chico a pilas maduras; con eso la curva
            # rampaba desde 0.1 y el reescalado del Q PLS empujaba el drenaje
            # diario por encima del riego, disparando el backstop 143 veces en
            # el Caso 21. Plana en la meseta, el reparto queda proporcional al
            # riego reconciliado (que es lo que dice el docstring de 'regimen').
            d['ramp_factor'] = meseta
        d['weight_pls'] = d['ramp_factor'] * d['q_riego_final']
    sum_weight_pls = sum(d['weight_pls'] for d in days)

    # --- 7c: drenaje diario + Cu ------------------------------------------
    for d in days:
        if ramp_status in ('ok', 'infactible', 'piso'):  # 'regimen'/'scaled'/'flat'/'sin_riego' reescalan abajo
            # El factor de drenaje del dia ES la curva: no se reescala nada.
            # Con status 'ok' la suma semanal calza exacto por construccion de
            # `_solve_meseta`; con 'cap' queda corta a proposito (ver alli).
            d['q_pls_final'] = d['weight_pls']
        elif sum_weight_pls > 0:
            d['q_pls_final'] = (d['weight_pls'] / sum_weight_pls) * pile_row['q_pls_final']
        else:
            share = (1.0 / n_irr) if n_irr > 0 else (1.0 / n_days)
            d['q_pls_final'] = share * pile_row['q_pls_final']
            warnings.append(f'{label}/{p} {d["date"].date()}: sin peso ramp-up esta semana, Q PLS repartido parejo (paso 7).')

        d['clipped'] = (ramp_status == 'infactible')
        # Backstop fisico. Con meseta <= FDRENA_MAX < 1 no deberia dispararse
        # nunca por la via de la curva; queda por los caminos 'scaled'/'flat'.
        if d['q_riego_final'] > 0 and d['q_pls_final'] >= d['q_riego_final']:
            recorte = d['q_riego_final'] * (1 - 1e-6)
            warnings.append(
                f'{label}/{p} {d["date"].date()}: Q PLS final dia ({d["q_pls_final"]:.3f}) >= '
                f'Q riego final dia ({d["q_riego_final"]:.3f}) -- recortado a {recorte:.3f} (paso 7).')
            d['q_pls_final'] = recorte
            d['clipped'] = True


    # --- 7d: Cu diario -----------------------------------------------------
    # Reparte la MASA final de fino de la pila (no el aporte) entre los dias
    # con caudal final > 0 y despeja la concentracion contra ese caudal
    # final: sum_dia(q_final*cu_recon) = fino_final semanal, exacto. Con el
    # esquema anterior (aporte repartido, division por caudal del dia) el
    # dia que cambiaba de caudal desviaba la masa entregada.
    for qkey, fkey, ckey, akey, mkey in (
            ('q_riego_final', 'fino_riego_final', 'cu_riego_recon',
             'aporte_fino_riego', 'fino_riego_medido'),
            ('q_pls_final', 'fino_pls_final', 'cu_pls_recon',
             'aporte_fino_pls', 'fino_pls_medido')):
        target = pile_row[fkey]
        F = (_split_fino(target, [d[mkey] for d in days], [d[qkey] for d in days])
             if target is not None else [None] * len(days))
        for d, f in zip(days, F):
            d[fkey] = f
            d[akey] = (f - d[mkey]) if f is not None else 0.0
            d[ckey] = (f / d[qkey]) if (f is not None and d[qkey] > 0) else None

    return days


def _distribute_bounded(base, weights, delta, lo=None, hi=None, tol=1e-9):
    """Reparte `delta` entre `base` con pesos `weights` respetando
    lo[i] <= base[i]+d[i] <= hi[i].

    El peso de paso 4 es la VARIANZA de la pila y no guarda relacion con su
    caudal propio, asi que `frac_i*delta` puede superar `q_i` y mandar el
    caudal final bajo cero -- agrandar el pool no lo evita, porque las pilas
    que entran pueden traer varianza ~0 (peso ~0). La pila que topa un borde
    se FIJA ahi y su parte del delta se redistribuye entre las que aun tienen
    holgura (water-filling), de modo que la suma de los d[i] sigue cerrando
    `delta` exacto mientras quede holgura en el pool.

    Devuelve (d, residual). `residual` != 0 solo si el pool COMPLETO topo:
    ahi el delta es infactible con estas pilas y hay que ampliar el pool."""
    n = len(base)
    d = [0.0] * n
    if n == 0:
        return d, float(delta)
    fixed = [False] * n
    for _ in range(n + 2):
        rem = float(delta) - sum(d[i] for i in range(n) if fixed[i])
        free = [i for i in range(n) if not fixed[i]]
        W = sum(weights[i] for i in free)
        nuevo = False
        for i in free:
            share = (rem * weights[i] / W) if W > 0 else 0.0
            x = base[i] + share
            if lo is not None and x < lo[i] - tol:
                d[i], fixed[i], nuevo = lo[i] - base[i], True, True
            elif hi is not None and x > hi[i] + tol:
                d[i], fixed[i], nuevo = hi[i] - base[i], True, True
            else:
                d[i] = share
        if not nuevo:
            return d, (0.0 if W > 0 else float(delta) - sum(d))
    return d, float(delta) - sum(d)


def _split_fino(target, fino_med, q_final):
    """Reparte la MASA de fino objetivo del pool entre las pilas/dias que
    terminan con caudal final > 0, en proporcion a su fino MEDIDO.

    El reparto es multiplicativo (F_i = fino_i * k, k = target/sum_fino) asi
    que nunca cambia de signo mientras el target sea >= 0, y la
    concentracion se despeja SIEMPRE contra el caudal FINAL:
    sum(q_final_i * cu_recon_i) = sum(F_i) = target, exacto.

    La masa de las pilas que quedaron en caudal 0 se redistribuye entre las
    demas (no se pierde). Devuelve lista de F_i (None donde no hay caudal)."""
    n = len(q_final)
    elig = [i for i in range(n) if q_final[i] > 0]
    if not elig:
        return [None] * n
    wsum = sum(fino_med[i] for i in elig)
    qsum = sum(q_final[i] for i in elig)
    out = [None] * n
    for i in elig:
        if wsum > 0:
            sh = fino_med[i] / wsum
        elif qsum > 0:
            sh = q_final[i] / qsum
        else:
            sh = 0.0
        out[i] = sh * target
    return out


def _pls_fine_target_for_net(net_cu_target_t, fino_riego_recon):
    """Absolute PLS fine target that gives the requested net Cu in t Cu.

    Fine values inside the engine are sums of daily Q[m3/h]*Cu[g/L]. One
    such daily unit converts to 0.024 t Cu, matching report_metodo.
    """
    target_t = float(net_cu_target_t)
    riego = float(fino_riego_recon)
    if not math.isfinite(target_t) or not math.isfinite(riego):
        raise ValueError('El objetivo neto y el fino reconciliado de riego deben ser finitos.')
    pls_target = riego + target_t / 0.024
    if not math.isfinite(pls_target) or pls_target < 0:
        raise ValueError(
            'El neto Cu objetivo implicaria fino PLS negativo o no finito; '
            'no se puede cerrar la curva con fino no negativo.')
    return pls_target


def _daily_net_cu_t(daily_rows):
    """Net Cu delivered by the actual post-ramp daily rows, in t Cu."""
    return sum((d.get('fino_pls_final') or 0.0) -
               (d.get('fino_riego_final') or 0.0)
               for d in daily_rows) * 0.024


def _hold_measured(row):
    """Deja cada dia de la pila EXACTAMENTE en lo medido (caudales, Cu y finos): sin ajuste, sin rampa."""
    for d in row['daily']:
        q_r, q_p = d['q_riego_medido'], d['q_pls_medido']
        d.update(q_riego_final=q_r, q_pls_final=q_p,
                 fino_riego_final=d['fino_riego_medido'], fino_pls_final=d['fino_pls_medido'],
                 cu_riego_recon=d['cu_riego_medido'] if q_r > 0 else None,
                 cu_pls_recon=d['cu_pls_medido'] if q_p > 0 else None,
                 d_riego=0.0, d_pls=0.0, aporte_fino_riego=0.0, aporte_fino_pls=0.0,
                 ramp_factor=(q_p / q_r if q_r > 0 else 0.0), weight_pls=q_p, clipped=False)
    days = row['daily']
    row['q_riego_final'] = sum(d['q_riego_final'] for d in days)
    row['q_pls_final'] = sum(d['q_pls_final'] for d in days)
    row['fino_riego_final'] = sum(d['fino_riego_final'] for d in days)
    row['fino_pls_final'] = sum(d['fino_pls_final'] for d in days)
    row['cu_riego_recon'] = row['fino_riego_final'] / row['q_riego_final'] if row['q_riego_final'] > 0 else None
    row['cu_pls_recon'] = row['fino_pls_final'] / row['q_pls_final'] if row['q_pls_final'] > 0 else None
    row['d_riego'] = row['d_pls'] = row['aporte_fino_riego'] = row['aporte_fino_pls'] = 0.0


def _build_piles(rows, materials, week_start, q_riego_medido, q_pls_medido,
                  delta_recon_riego, delta_recon_pls, delta_fino_riego, delta_fino_pls,
                  ramp_cap_by_label, week_end=None, nuevas_by_label=None, hold_measured=False,
                  campana_by_label=None):
    """Paso 3+4+6+7 para TODAS las pilas activas de `rows`.

    `rows` ya viene filtrado por el llamador: una pila sin riego medido en la
    ventana esta INACTIVA y no llega hasta aca. Las que llegan se reconcilian
    todas; lo unico que las diferencia es `estado`, que decide la forma de la
    curva diaria en paso 7 (ver `_distribute_daily_pile`):

      'activa'       ya venia operando -> reparto uniforme por dia, curva
                     plana en la meseta, proporcional al riego reconciliado.
      'activa_nueva' arranca dentro de la ventana -> ramp-up desde su primer
                     dia de riego real.

    Devuelve (piles, daily_rows, warnings, clip_labels, inventario).
    `inventario` es {label: (q_pls, fino_pls)} con el drenaje que el ancla
    pide y ninguna pila del pad puede entregar bajo el techo fisico -- ver
    `_repartir_residuo_rampa`. `clip_labels` es el
    set de materiales con >=1 dia recortado en paso 7, o sea donde el ancla
    pide mas de lo que la curva puede entregar. Es diagnostico: el llamador lo
    convierte en warning."""
    warnings = []
    piles = []
    daily_rows = []
    clip_labels = set()
    tr = list(rows)
    if not tr:
        return piles, daily_rows, warnings, clip_labels, {}
    n = len(tr)

    # Paso 3: fraccion de aporte -- sobre el total SOLO de las pilas
    # transientes (las SS no absorben ajuste, no pueden aportar denominador).
    # Normalizar por el total global inflaba el delta por pila transiente y
    # forzaba a la expansion adaptativa a tragarse pilas de 100-300+ dias
    # buscando cerrar una fraccion que nunca sumaba 1 con pocas transientes.
    q_riego_trans = sum(r['q_riego'] for r in tr)
    # Paso 4 pesa por CAUDAL: frac_i = q_i / q_trans (PESO_PASO4='caudal').
    #
    # El monto que recibe cada pila SI depende de su caudal
    # (d_i = q_i * delta/q_trans), pero el PORCENTAJE de ajuste es el mismo
    # para todas: d_i/q_i = delta/q_trans, el q_i se cancela. Eso es una
    # propiedad deseable, no un defecto -- ninguna pila puede quedar con
    # caudal negativo mientras |delta| <= q_trans, asi que el clamp del
    # water-filling casi nunca se activa y el reparto es proporcional al
    # tamano de cada pila.
    #
    # Alternativa historica PESO_PASO4='varianza': pesa por la varianza de
    # la lectura diaria, para que la pila mas erratica absorba mas ajuste.
    # Diferencia el % por pila, pero la varianza no guarda relacion con el
    # caudal propio, asi que frac_i*delta puede superar q_i y hay que
    # recortar: en caso 17 oxidos apagaba dos pilas completas.
    #
    # Q PLS comparte el peso de Q riego (Qpls = FDRENA_MAX*Qriego siempre).
    var_riego_trans = sum(r['q_riego_var'] for r in tr)
    if PESO_PASO4 == 'varianza' and var_riego_trans > 0:
        w = [r['q_riego_var'] / var_riego_trans for r in tr]
    elif q_riego_trans > 0:
        w = [r['q_riego'] / q_riego_trans for r in tr]
    else:
        w = [0.0] * n

    # --- Paso 4: delta de caudal, ACOTADO ---------------------------------
    # Restriccion dura: el caudal final nunca es negativo. El AJUSTE si puede
    # serlo (hasta -100 %); lo que no existe fisicamente es una pila que
    # riegue o drene caudal negativo. Ver `_distribute_bounded`.
    base_r = [r['q_riego'] for r in tr]
    lo0 = [0.0] * n
    d_riego_v, resid_r = _distribute_bounded(base_r, w, delta_recon_riego, lo=lo0)
    q_riego_final_v = [base_r[i] + d_riego_v[i] for i in range(n)]
    if abs(resid_r) > 1e-6:
        warnings.append(
            f'{tr[0]["label"]}: el delta de Q riego ({delta_recon_riego:.3f}) no cabe en el pool '
            f'transiente sin caudales negativos; quedan {resid_r:.3f} sin repartir (paso 4).')
        clip_labels.update(r['label'] for r in tr)

    # Q PLS: mismo peso, piso 0 y techo el Q riego final de la propia pila
    # (Q riego > Q PLS siempre). El techo entra en el water-filling en vez de
    # aplicarse como recorte posterior, asi el recorte de una pila lo absorben
    # las otras y la suma del pool sigue cerrando el delta.
    base_p = [r['q_pls'] for r in tr]
    hi_p = [q * (1 - 1e-6) for q in q_riego_final_v]
    d_pls_v, resid_p = _distribute_bounded(base_p, w, delta_recon_pls, lo=lo0, hi=hi_p)
    q_pls_final_v = [base_p[i] + d_pls_v[i] for i in range(n)]
    if abs(resid_p) > 1e-6:
        warnings.append(
            f'{tr[0]["label"]}: el delta de Q PLS ({delta_recon_pls:.3f}) no cabe en el pool '
            f'transiente entre 0 y el Q riego final; quedan {resid_p:.3f} sin repartir (paso 4).')
        clip_labels.update(r['label'] for r in tr)

    # --- Paso 6: fino de Cu, EXACTO ---------------------------------------
    # Corre DESPUES de paso 4 a proposito. La pila entrega
    # `q_final * cu_recon`, asi que despejar cu_recon contra el caudal
    # MEDIDO (como se hacia antes) deja un error de cierre igual a
    # sum(F_i * (q_final_i/q_medido_i - 1)) -- en caso 17 sulfuros eso era
    # -51 % del objetivo. Dividiendo por el caudal FINAL el fino entregado
    # reproduce el objetivo del ancla al ultimo decimal.
    fino_riego_med = [(r['q_riego'] * r['cu_riego'])
                      if (r['q_riego'] > 0 and pd.notna(r['cu_riego'])) else 0.0 for r in tr]
    fino_pls_med = [(r['q_pls'] * r['cu_pls'])
                    if (r['q_pls'] > 0 and pd.notna(r['cu_pls'])) else 0.0 for r in tr]
    target_fr = sum(fino_riego_med) + delta_fino_riego
    target_fp = sum(fino_pls_med) + delta_fino_pls
    F_riego = _split_fino(target_fr, fino_riego_med, q_riego_final_v)
    F_pls = _split_fino(target_fp, fino_pls_med, q_pls_final_v)

    for i, r in enumerate(tr):
        frac_riego = w[i]
        frac_pls = w[i]
        d_riego, d_pls = d_riego_v[i], d_pls_v[i]
        q_riego_final, q_pls_final = q_riego_final_v[i], q_pls_final_v[i]

        fino_riego_final = F_riego[i]
        fino_pls_final = F_pls[i]
        aporte_fino_riego = ((fino_riego_final - fino_riego_med[i])
                             if fino_riego_final is not None else 0.0)
        aporte_fino_pls = ((fino_pls_final - fino_pls_med[i])
                           if fino_pls_final is not None else 0.0)
        cu_riego_recon = (fino_riego_final / q_riego_final
                          if (fino_riego_final is not None and q_riego_final > 0) else None)
        cu_pls_recon = (fino_pls_final / q_pls_final
                        if (fino_pls_final is not None and q_pls_final > 0) else None)
        # Con reparto multiplicativo el Cu solo puede salir negativo si el
        # OBJETIVO del pool es negativo (el ancla pide menos fino del que el
        # pool puede soltar). Ampliar el pool si ayuda: agranda el
        # denominador y acerca el factor a 1.
        if cu_riego_recon is not None and cu_riego_recon < 0:
            warnings.append(f'{r["label"]}/{r["parcela"]}: Cu riego reconciliado negativo ({cu_riego_recon:.4f}) -- pool transiente insuficiente para el ajuste de fino.')
            clip_labels.add(r['label'])
        if cu_pls_recon is not None and cu_pls_recon < 0:
            warnings.append(f'{r["label"]}/{r["parcela"]}: Cu PLS reconciliado negativo ({cu_pls_recon:.4f}) -- pool transiente insuficiente para el ajuste de fino.')
            clip_labels.add(r['label'])

        row = dict(
            label=r['label'], parcela=r['parcela'], dia_ciclo=r['dia_ciclo'],
            q_riego_medido=r['q_riego'], q_pls_medido=r['q_pls'],
            cu_riego_medido=r['cu_riego'], cu_pls_medido=r['cu_pls'],
            frac_riego=frac_riego, frac_pls=frac_pls,
            aporte_fino_riego=aporte_fino_riego, aporte_fino_pls=aporte_fino_pls,
            fino_riego_final=fino_riego_final, fino_pls_final=fino_pls_final,
            cu_riego_recon=cu_riego_recon, cu_pls_recon=cu_pls_recon,
            d_riego=d_riego, d_pls=d_pls,
            q_riego_final=q_riego_final, q_pls_final=q_pls_final,
        )
        if q_riego_final <= 0:
            warnings.append(f'{r["label"]}/{r["parcela"]}: la pila queda con Q riego final 0 -- absorbio un ajuste de -100 % (paso 4).')
            clip_labels.add(r['label'])
        piles.append(row)

        # `ini_ciclo` no None <=> la pila arranca dentro de la ventana (sin
        # riego ni Cu de drenaje antes) => le toca ramp-up. Ver
        # `arranque_en_ventana()`.
        ini_ciclo = (nuevas_by_label or {}).get(r['label'], {}).get(r['parcela'])
        row['ini_ciclo'] = ini_ciclo
        # Ancla de la campana vigente para la pila que YA venia operando: es
        # lo que le da dia de ciclo confiable a la rampa mas alla de la
        # semana de arranque (ver `inicio_campana`).
        ini_campana = (campana_by_label or {}).get(r['label'], {}).get(r['parcela'])
        row['ini_campana'] = ini_campana
        row['daily'] = _distribute_daily_pile(
            r['label'], r['parcela'], week_start, materials[r['label']], row,
            ramp_cap_by_label[r['label']], warnings, week_end=week_end,
            ini_ciclo=ini_ciclo, ini_campana=ini_campana)
        if hold_measured:
            _hold_measured(row)
        if any(d['clipped'] for d in row['daily']):
            clip_labels.add(r['label'])

    # --- 7e: el residuo de las rampas va a las pilas en regimen -----------
    # Lo que no cabe bajo el techo de NINGUNA pila del pad no es ajuste de la
    # pila nueva: es INVENTARIO INTERNO del lecho. Sale como termino aparte
    # para que el pad cierre y para que el % de ajuste de la pila nueva siga
    # siendo el de su aporte.
    inventario = ({r['label']: (0.0, 0.0) for r in piles} if hold_measured
                  else _repartir_residuo_rampa(piles, ramp_cap_by_label, warnings))

    # `daily_rows` se arma DESPUES de 7e: antes copiaba los dias de la pila y
    # el reparto los dejaba desactualizados.
    for row in piles:
        for d in row['daily']:
            daily_rows.append(dict(week_start=week_start, label=row['label'],
                                   parcela=row['parcela'], **d))

    return piles, daily_rows, warnings, clip_labels, inventario


def _resembrar_fino_pila(row, target_fino):
    """Vuelve a repartir la MASA de fino de PLS de la pila entre sus dias con
    el mismo criterio del paso 7d, despues de que el reparto del residuo de
    rampa (7e) le movio el caudal. Deja `cu_pls_recon` despejado contra el
    caudal nuevo, que es lo que mantiene sum_dia(q*cu) = fino semanal."""
    days = row['daily']
    F = _split_fino(target_fino,
                    [d['fino_pls_medido'] for d in days],
                    [d['q_pls_final'] for d in days])
    for d, f in zip(days, F):
        d['fino_pls_final'] = f
        d['aporte_fino_pls'] = (f - d['fino_pls_medido']) if f is not None else 0.0
        d['cu_pls_recon'] = (f / d['q_pls_final']) if (f is not None and d['q_pls_final'] > 0) else None
    row['fino_pls_final'] = target_fino
    row['aporte_fino_pls'] = target_fino - sum(d['fino_pls_medido'] for d in days)
    row['cu_pls_recon'] = (target_fino / row['q_pls_final']) if row['q_pls_final'] > 0 else None


def _repartir_residuo_rampa(piles, ramp_cap_by_label, warnings):
    """Paso 7e: el residuo que la rampa de una pila NUEVA no puede drenar se
    traslada a las pilas EN REGIMEN del mismo pad.

    Por que existe este paso. Paso 4/6 le asigna a la pila nueva un Q PLS
    semanal calculado como si drenara igual que una madura (la siembra es
    FDRENA_MAX * riego, 0.95 los 7-8 dias). Una pila de un dia no drena eso:
    su curva arranca en f(1) y sube. `ramp_curve.ajustar` entrega la rampa mas
    alta admisible y devuelve la diferencia como `ramp_residuo`.

    Antes ese residuo se ocultaba de dos formas malas: o se aplastaba la curva
    contra el techo -- publicando Fdrena 0.99 el primer dia de riego de una
    pila recien armada -- o se dejaba la suma diaria corta contra el total de
    la pila, que `_closure_check` no ve porque suma TOTALES, no dias.

    Aca el volumen no se pierde ni se inventa: sale de la pila nueva y entra a
    las maduras, que fisicamente si pueden drenarlo. El total del pad no se
    mueve, asi que el calce con el ancla se conserva. Se reparte proporcional
    a la HOLGURA de cada receptora (cap * riego util - Q PLS ya asignado), lo
    que garantiza que ninguna pase del techo. El fino de PLS viaja en la misma
    proporcion que el caudal, para que la ley de cada pila no salte.

    El residuo tambien puede venir al reves. Una pila a mitad de rampa cierra
    la semana en un factor de drenaje y la siguiente PARTE DE AHI: si el Q PLS
    que le toca esa ventana pide menos que quedarse quieta en ese factor, la
    curva tendria que bajar, o sea des-saturar el lecho de un dia para otro.
    `ramp_curve.ajustar` entrega el piso (curva plana en el factor heredado) y
    devuelve residuo NEGATIVO. Ese sobrante se descuenta de las pilas en
    regimen, proporcional al Q PLS que ya tienen asignado -- el mismo
    movimiento del caso positivo, con el signo dado vuelta.

    Si falta capacidad para compensar volumen o Cu, el remanente se declara
    con signo objetivo menos entregado. La clave histórica ``inventario``
    conserva estos términos contables; su existencia no prueba inventario
    físico del lecho ni autoriza añadir Cu. Los pisos pueden dejar términos
    negativos, y caudal y masa pueden requerir términos de signo distinto.
    """
    # API hist?rica: "inventario" contiene el t?rmino firmado de balance
    # pendiente (objetivo - entrega), sin atribuci?n f?sica autom?tica.
    inventario = {}
    for label in sorted({r['label'] for r in piles}):
        cap = ramp_cap_by_label.get(label, FDRENA_RECON_MAX)
        del_pad = [r for r in piles if r['label'] == label]
        donantes = [r for r in del_pad if r.get('ramp_residuo', 0.0) > 1e-9]
        excedentes = [r for r in del_pad if r.get('ramp_residuo', 0.0) < -1e-9]

        # --- 0) piso de la rampa: la pila entrega MAS de lo que le toco -----
        # El volumen extra no se inventa: lo devuelven las pilas en regimen,
        # que bajan su Q PLS en la misma proporcion. El total del pad no se
        # mueve.
        if excedentes:
            pendiente_q, pendiente_f = _absorber_piso_rampa(label, del_pad, excedentes, warnings)
            if abs(pendiente_q) > 1e-9 or abs(pendiente_f) > 1e-9:
                inventario[label] = (pendiente_q, pendiente_f)

        if not donantes:
            continue

        # --- 1) la pila nueva se queda con lo que su rampa entrega ---------
        residuo_q = 0.0
        residuo_f = 0.0
        for r in donantes:
            q_old = r['q_pls_final']
            q_new = sum(d['q_pls_final'] for d in r['daily'])
            if q_old <= 0 or q_new >= q_old:
                r['ramp_residuo'] = 0.0
                continue
            f_old = r['fino_pls_final'] or 0.0
            f_new = f_old * (q_new / q_old)
            residuo_q += q_old - q_new
            residuo_f += f_old - f_new
            # `d_pls` pasa a mezclar dos cosas distintas: el ajuste que el
            # paso 4 le repartio por aporte (igual en % a toda pila del pad) y
            # el volumen que el TECHO FISICO de la rampa le impide drenar. Se
            # guardan por separado para que el dashboard y el informe no lean
            # el segundo como si la pila nueva hubiera recibido mas ajuste.
            r['d_pls_aporte'] = q_old - r['q_pls_medido']
            r['tope_rampa_q'] = q_old - q_new
            r['tope_rampa_f'] = f_old - f_new
            r['q_pls_final'] = q_new
            r['d_pls'] = q_new - r['q_pls_medido']
            _resembrar_fino_pila(r, f_new)
        if residuo_q <= 1e-9:
            continue
        inv_q = inv_f = 0.0

        # --- 2) receptoras: las de regimen, con holgura bajo el techo ------
        recept = [r for r in del_pad if not r.get('en_rampa', False)
                  and not r.get('transition_protected', False)]
        holgura = []
        for r in recept:
            # Denominador = riego de los dias que EFECTIVAMENTE se regaron:
            # los otros tienen ramp_factor 0 y no admiten drenaje.
            q_util = sum(d['q_riego_final'] for d in r['daily']
                         if d['q_riego_medido'] > 0 and d['q_riego_final'] > 0)
            # Una cota agregada no garantiza el techo de CADA dia si la
            # receptora no tiene factor uniforme. Limitar el reescalado por
            # el dia con menos margen.
            if r['q_pls_final'] > 0:
                limites = [cap * d['q_riego_final'] / d['q_pls_final']
                           for d in r['daily'] if d['q_pls_final'] > 0]
                escala_max = min(limites) if limites else 1.0
                margen = r['q_pls_final'] * max(0.0, escala_max - 1.0)
            else:
                margen = cap * q_util
            holgura.append(max(0.0, min(margen, cap * q_util - r['q_pls_final'])))
        tot_h = sum(holgura)
        if tot_h <= 1e-9:
            warnings.append(
                f'{label}: el residuo de rampa ({residuo_q:.3f}) no se pudo repartir -- '
                f'ninguna pila en regimen tiene holgura bajo el techo {cap:.2f}. El pad entero '
                f'no dispone de capacidad para este reparto. El residuo se declara como '
                f'termino contable de balance, sin atribuirlo a inventario fisico. El pad cierra '
                f'con la suma diaria bajo su total; el faltante se declara como INVENTARIO '
                f'del pad, no como ajuste de la pila nueva (paso 7e).')
            piso_q, piso_f = inventario.get(label, (0.0, 0.0))
            inventario[label] = (piso_q + residuo_q, piso_f + residuo_f)
            continue

        colocado = min(residuo_q, tot_h)
        inv_q = residuo_q - colocado
        inv_f = residuo_f * (inv_q / residuo_q) if residuo_q > 0 else 0.0
        for r, h in zip(recept, holgura):
            if h <= 0:
                continue
            dq = colocado * (h / tot_h)
            df = residuo_f * (h / tot_h) * (colocado / residuo_q)
            q_new = r['q_pls_final'] + dq
            f_new = (r['fino_pls_final'] or 0.0) + df
            k = q_new / r['q_pls_final'] if r['q_pls_final'] > 0 else 0.0
            q_util = sum(d['q_riego_final'] for d in r['daily']
                         if d['q_riego_medido'] > 0 and d['q_riego_final'] > 0)
            for d in r['daily']:
                if r['q_pls_final'] > 0:
                    d['q_pls_final'] *= k
                else:
                    d['q_pls_final'] = (q_new * d['q_riego_final'] / q_util
                                        if q_util > 0 and d['q_riego_medido'] > 0
                                        and d['q_riego_final'] > 0 else 0.0)
            r['q_pls_final'] = q_new
            r['d_pls'] = q_new - r['q_pls_medido']
            r['recibe_residuo_rampa'] = r.get('recibe_residuo_rampa', 0.0) + dq
            _resembrar_fino_pila(r, f_new)

        n_rec = sum(1 for h in holgura if h > 0)
        warnings.append(
            f'{label}: residuo de rampa {residuo_q:.3f} m3/h-dia de '
            f'{", ".join(r["parcela"] for r in donantes)} repartido entre {n_rec} pila(s) en '
            f'regimen proporcional a su holgura bajo el techo {cap:.2f} (paso 7e).')
        if colocado < residuo_q - 1e-6:
            warnings.append(
                f'{label}: quedaron {residuo_q - colocado:.3f} m3/h-dia del residuo de rampa SIN '
                f'colocar -- la holgura total del pad ({tot_h:.3f}) no alcanza. El termino no '
                f'demuestra inventario interno del lecho ni permite añadir Cu para cerrar '
                f'el balance. Se declara el faltante con signo (paso 7e).')
        if abs(inv_q) > 1e-9 or abs(inv_f) > 1e-9:
            piso_q, piso_f = inventario.get(label, (0.0, 0.0))
            inventario[label] = (piso_q + inv_q, piso_f + inv_f)
    return inventario


def _absorber_piso_rampa(label, del_pad, excedentes, warnings):
    """Retira por separado el volumen y el Cu que añade un piso de rampa.

    El Cu retirado debe igualar la masa añadida, aunque las concentraciones
    de las pilas sean distintas. Se reparte el Cu restante entre receptoras
    con drenaje positivo; sus concentraciones se vuelven a despejar.

    Devuelve (Q, fino) pendientes, con signo objetivo menos entregado.
    Son términos de balance no resueltos, no inventario físico demostrado.
    """
    falta_q = falta_f = 0.0
    for r in excedentes:
        q_old = r['q_pls_final']
        q_new = sum(d['q_pls_final'] for d in r['daily'])
        if q_new <= q_old:
            r['ramp_residuo'] = 0.0
            continue
        f_old = r['fino_pls_final'] or 0.0
        # Un objetivo de caudal cero no tiene concentración de referencia:
        # mantener su masa asignada evita inventar Cu al abrir el piso.
        f_new = f_old * (q_new / q_old) if q_old > 0 else f_old
        falta_q += q_new - q_old
        falta_f += f_new - f_old
        r['d_pls_aporte'] = q_old - r['q_pls_medido']
        r['piso_rampa_q'] = q_new - q_old
        r['piso_rampa_f'] = f_new - f_old
        r['q_pls_final'] = q_new
        r['d_pls'] = q_new - r['q_pls_medido']
        _resembrar_fino_pila(r, f_new)
    if falta_q <= 1e-9 and abs(falta_f) <= 1e-9:
        return 0.0, 0.0

    recept = [r for r in del_pad if not r.get('en_rampa', False)
              and not r.get('transition_protected', False)]
    q_antes = [r['q_pls_final'] for r in recept]
    f_antes = [r['fino_pls_final'] or 0.0 for r in recept]
    total_q, total_f = sum(q_antes), sum(f_antes)
    devuelto_q = min(falta_q, total_q)
    for r, q_old in zip(recept, q_antes):
        dq = devuelto_q * q_old / total_q if total_q > 0 else 0.0
        q_new = max(q_old - dq, 0.0)
        k = q_new / q_old if q_old > 0 else 0.0
        for d in r['daily']:
            d['q_pls_final'] *= k
        r['q_pls_final'] = q_new
        r['d_pls'] = q_new - r['q_pls_medido']
        r['devuelve_piso_rampa'] = r.get('devuelve_piso_rampa', 0.0) + dq

    # Retirada exacta de Cu independiente del reparto de agua. El total
    # queda >= 0 y una pila sin caudal no recibe masa sin vía de transporte.
    objetivo_f = max(total_f - falta_f, 0.0)
    nuevos_f = _split_fino(objetivo_f, f_antes,
                          [r['q_pls_final'] for r in recept])
    for r, f_old, f_new in zip(recept, f_antes, nuevos_f):
        f_new = f_new if f_new is not None else 0.0
        r['devuelve_piso_rampa_f'] = r.get('devuelve_piso_rampa_f', 0.0) + f_old - f_new
        _resembrar_fino_pila(r, f_new)
    entregado_f = sum(r['fino_pls_final'] or 0.0 for r in recept)
    residuo_q = devuelto_q - falta_q
    residuo_f = total_f - falta_f - entregado_f
    if abs(residuo_q) <= 1e-9:
        residuo_q = 0.0
    if abs(residuo_f) <= 1e-9:
        residuo_f = 0.0
    warnings.append(
        f'{label}: piso de rampa {falta_q:.3f} m3/h-dia y {falta_f:.3f} de fino '
        f'de {", ".join(r["parcela"] for r in excedentes)} compensado por separado '
        f'en caudal y masa de Cu entre {len(recept)} pila(s) en regimen (paso 7e).')
    if residuo_q or residuo_f:
        warnings.append(
            f'{label}: capacidad insuficiente para compensar el piso de rampa; '
            f'termino de balance pendiente Q={residuo_q:.6f}, fino={residuo_f:.6f} '
            f'(objetivo menos entregado). Se declara con signo; no demuestra '
            f'inventario fisico ni añade Cu a las pilas.')
    return residuo_q, residuo_f


def export_transient_plot(df_pile, output_dir):
    """
    Exporta reconciliación de una pila.
    """
    fig, ax = plt.subplots(figsize=(10,5))

    # Mapeo a las columnas que existen en df_pile (daily_rows)
    ax.plot(df_pile["date"], df_pile["q_riego_medido"], "-o", label="QRiego medido")
    ax.plot(df_pile["date"], df_pile["q_riego_final"], "-o", label="QRiego reconc.")
    ax.plot(df_pile["date"], df_pile["q_pls_medido"], "-o", label="QPLS medido")
    ax.plot(df_pile["date"], df_pile["q_pls_final"], "-o", label="QPLS reconc.")

    ax.grid(True)
    ax.legend()
    ax.set_title(df_pile["parcela"].iloc[0])

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    fig.savefig(
        Path(output_dir) / f"{df_pile['parcela'].iloc[0]}.png",
        dpi=200,
        bbox_inches="tight"
    )
    plt.close(fig)


ANCHOR_KEYS = ('q_riego_medido', 'q_riego_recon', 'q_pls_medido', 'q_pls_recon',
               'fino_riego_medido', 'fino_riego_recon', 'fino_pls_medido', 'fino_pls_recon')


def _anchor_ratio(anchor, key_recon, key_medido):
    """Razon reconciliado/medido del ancla, o None si el ancla no la trae.

    Los caudales y la base reconciliada de riego se aplican como RAZON porque
    el Caso y el motor de curvas NO cubren el mismo universo de parcelas.
    En el modelo 125, el fino PLS se ajusta después para cerrar el neto absoluto
    de F25/F29. El
    Caso y el motor de curvas NO cubren el mismo universo de parcelas, y la
    diferencia va en las dos direcciones: con `incluir_sin_campana` el motor
    ya suma las pilas que riegan sin campana (P32 de oxidos, ~3 % del pad),
    y aun asi la cobertura contra el ancla va de 84,98 % (caso 17 sulfuros,
    run 111) a 102,88 % (caso 18 oxidos) -- ahi el motor mide MAS que el
    Caso. Con el ancla absoluta
    esa diferencia de UNIVERSO entraria al delta disfrazada de ajuste de
    reconciliacion. Con la razon, cada motor reparte sobre su propio
    universo el mismo porcentaje de correccion que decidio el solver.
    """
    if not anchor:
        return None
    rec, med = anchor.get(key_recon), anchor.get(key_medido)
    if rec is None or med is None:
        return None
    rec, med = float(rec), float(med)
    if not (np.isfinite(rec) and np.isfinite(med)) or med == 0.0:
        return None
    return rec / med


ANCHOR_UNCHANGED_TOL = 1e-3     # 0.1 %: dentro de esta banda el global reconciliado = medido


def _anchor_unchanged(anchor, tol=ANCHOR_UNCHANGED_TOL):
    """True si los flujos globales del pad no cambian al reconciliar (riego y PLS, masa y fino, y el neto).

    En ese caso el pad no se mueve: ninguna pila cambia caudal, concentracion ni recuperacion. Sin esto el
    neto absoluto (F25/F29) se imponia igual y movia el fino PLS de las pilas aunque los flujos no cambiaran,
    solo porque el neto que miden las pilas no coincide con el del balance (distinto universo de pilas)."""
    if not anchor:
        return False
    for rec, med in (('q_riego_recon', 'q_riego_medido'), ('q_pls_recon', 'q_pls_medido'),
                     ('fino_riego_recon', 'fino_riego_medido'), ('fino_pls_recon', 'fino_pls_medido')):
        ratio = _anchor_ratio(anchor, rec, med)
        if ratio is None or abs(ratio - 1.0) > tol:
            return False
    target = anchor.get('net_cu_target_t')
    if target is not None:
        net_med = float(anchor['fino_pls_medido']) - float(anchor['fino_riego_medido'])
        if not np.isfinite(float(target)) or abs(float(target) - net_med) > tol * max(abs(net_med), 1e-9):
            return False
    return True


def reconcile_week_flowsheet(week_start, materials, n_transient=N_TRANSIENT_DEFAULT,
                              sigma_rel=SIGMA_REL_DEFAULT, force_all_active=False,
                              week_end=None, anchor=None):
    """
    Resuelve UNA semana con la metodologia de reparto de caudal + fino de
    Cu. No usa `produccion` (no reconcilia masa de Cu contra produccion de
    planta) ni persiste en DB.

    Paso 6 (Cu en PLS y Cu en riego) corre DESPUES del Paso 4 (distribucion
    interna del delta de caudal): la pila entrega `q_final * cu_recon`, asi
    que la concentracion reconciliada se despeja siempre contra el caudal
    FINAL. Dividir por el medido dejaba un error de cierre de fino de hasta
    -51 % del objetivo del ancla.
    """
    week_start, week_end, _n_days = resolve_window(week_start, week_end)
    warnings = []

    # Pilas que ARRANCAN en la ventana, por dato de operacion (primer riego
    # sin riego ni Cu de drenaje en los 30 dias previos). Son las unicas que
    # llevan ramp-up; el resto va en regimen (curva plana). Se calcula ANTES
    # del armado de filas porque `estado` depende de esto.
    nuevas_by_label = {label: arranque_en_ventana(label, week_start, week_end)
                       for label in materials}

    # Ancla de campana de TODAS las pilas activas (no solo las que nacen): la
    # rampa dura `DIAS_RAMPA` dias y necesita fechar el dia de ciclo de una
    # pila que arranco en una ventana anterior. Misma fuente que la de
    # arriba -- riego y drenaje, no `lectura_recuperacion`.
    campana_by_label = {label: inicio_campana(label, week_end)
                        for label in materials}

    # Pila que arranca EL ULTIMO DIA de la ventana NO entra al pool: es
    # demasiado reciente para reconciliar (un solo dia de riego, drenaje
    # todavia sin desarrollar) y ese mismo dia es ademas el primero de la
    # ventana siguiente -- las ventanas de caso comparten el borde porque
    # `fecha_fin` es inclusiva (08:00 del dia inicio a 08:00 del dia fin + 1).
    # Sin este corte la misma pila salia ACTIVA NUEVA en dos casos seguidos y
    # su primer dia de campana se contaba dos veces.
    tardias_by_label = {}
    for label, nv in nuevas_by_label.items():
        tardias = {pila: d for pila, d in nv.items()
                   if pd.Timestamp(d).normalize() == week_end}
        if tardias:
            tardias_by_label[label] = tardias
            for pila in tardias:
                nv.pop(pila, None)

    rows = []  # dict por pila activa (label, p, dia_ciclo, q_riego, q_pls, estado)
    sin_riego = {}  # label -> {pila: dia_ciclo} de las que no regaron en la ventana
    for label, mat in materials.items():
        active, transient, ss, day_in_cycle, _rec_ratio = classify_piles(
            week_start, mat['wip'], mat['rec_curves'], mat['max_rec'], mat['ciclo_d'],
            transient_days=n_transient, week_end=week_end)
        if not active:
            continue
        wz = compute_wz_week(week_start, active, mat['riego'], mat['cu_riego'], mat['drena_cu'],
                              week_end=week_end)
        for p in active:
            if p in tardias_by_label.get(label, {}):
                continue          # arranca el ultimo dia: fuera del pool
            dia_ciclo = _campaign_asof(label, p, week_end)
            if dia_ciclo is None:
                dia_ciclo = day_in_cycle.get(p)
                warnings.append(
                    f'{label}/{p}: sin dato de curva hasta {week_end.date()} '
                    f'(reporte tope 2025-08-31), fallback a WIP (dia_ciclo={dia_ciclo}).')
            # Qriegoi es el APORTE de la pila esa semana -> suma de los 7
            # dias, no el promedio diario (`wz['q_mean']` es un promedio,
            # sirve para Fdrena/prior pero no para el balance de flowsheet
            # de paso 1, que suma "flujo por pila" entre pilas).
            if p in mat['riego'].columns:
                riego_week = mat['riego'].loc[week_start:week_end, p].dropna()
                q_riego_i = float(riego_week.sum())
                # Varianza de la propia lectura diaria dentro de la semana --
                # pila mas erratica/ruidosa (menos confiable) absorbe mas del
                # ajuste de flowsheet; pila con caudal estable (medicion
                # confiable) absorbe poco o nada. Reemplaza el reparto pro-rata
                # por caudal (ver comentario en `_build_piles`).
                q_riego_var_i = float(riego_week.var(ddof=0)) if len(riego_week) > 1 else 0.0
            else:
                q_riego_i = 0.0
                q_riego_var_i = 0.0
            # Pila SIN riego medido en la ventana no entra al pool. La
            # clasificacion (`classify_piles`) la sigue llamando activa porque
            # su campana no cerro, pero si no rego no aporta caudal ni fino:
            # metida en el pool absorbia parte del delta de reconciliacion
            # sobre una base cero, quedaba con `q_riego_final` 0 tras un ajuste
            # de -100 %, y despues recibia Q PLS repartido parejo entre dias
            # sin riego -- PLS inventado para una pila apagada, mas una ristra
            # de warnings por cada dia. Regla del negocio: las inactivas nada
            # (sin riego). Sacarlas no mueve ningun agregado: aportaban 0 a
            # `q_riego_medido`, `q_pls_medido` y a los finos.
            if q_riego_i <= 0:
                sin_riego.setdefault(label, {})[p] = dia_ciclo
                continue
            q_pls_i = FDRENA_MAX * q_riego_i
            cu_riego_i = wz.get(p, {}).get('cu_r_mean', 0.0)
            cu_pls_i = wz.get(p, {}).get('cu_d_mean', 0.0)
            rows.append(dict(
                label=label, parcela=p, dia_ciclo=dia_ciclo,
                # Tres estados y nada mas. INACTIVA no llega aca (se descarto
                # arriba por no tener riego). El corte viejo
                # `dia_ciclo < n_transient` se elimino: dependia de
                # `lectura_recuperacion`, que abre campana para todo el pad el
                # mismo dia, y ademas quedaba muerto porque el unico caller
                # vivo pasa force_all_active=True.
                estado=('activa_nueva'
                        if p in nuevas_by_label.get(label, {}) else 'activa'),
                q_riego=q_riego_i, q_pls=q_pls_i, q_riego_var=q_riego_var_i,
                cu_riego=cu_riego_i, cu_pls=cu_pls_i,
            ))

    # Un solo warning por material, no uno por pila por dia. Se separa REPOSO
    # (la pila no riega hace tiempo: ciclo terminado, campana abierta en el WIP
    # porque `classify_piles` no tiene fecha real de cierre) de CAIDA DE
    # MEDICION (regaba hasta hace poco y la ventana viene en cero). El texto
    # viejo decia solo "activa sin riego medido" y se leia como dato perdido,
    # cuando el caso normal es una pila apagada con 0.0 explicito en origen.
    _REPOSO_DIAS = 14
    for label, pilas_sr in sorted(sin_riego.items()):
        ult = ultimo_riego(label, list(pilas_sr), week_start)

        def _detalle(p):
            f = ult.get(p)
            if f is None:
                return f'{p} (sin riego > 0 registrado nunca)'
            return f'{p} (ultimo riego {f.date()}, hace {(week_start - f).days} d)'

        reposo = [p for p in pilas_sr
                  if p not in ult or (week_start - ult[p]).days > _REPOSO_DIAS]
        reciente = [p for p in pilas_sr if p not in reposo]
        if reposo:
            warnings.append(
                f'{label}: {len(reposo)} pila(s) EN REPOSO -- campana abierta en el '
                f'WIP pero el pad midio 0 m3/h todos los dias de la ventana y su '
                f'ultimo riego es viejo. Fuera del pool, no aportan caudal ni fino '
                f'(esperado, no es falta de dato): '
                f'{", ".join(_detalle(p) for p in sorted(reposo))}.')
        if reciente:
            warnings.append(
                f'{label}: {len(reciente)} pila(s) sin riego en la ventana pero CON '
                f'riego reciente -- revisar si es parada real o caida de medicion. '
                f'Fuera del pool: '
                f'{", ".join(_detalle(p) for p in sorted(reciente))}.')

    for label, nv in sorted(nuevas_by_label.items()):
        if nv:
            warnings.append('%s: %d pila(s) arrancan en la ventana (ramp-up): %s.'
                            % (label, len(nv),
                               ', '.join('%s el %s' % (p, d.date())
                                         for p, d in sorted(nv.items()))))

    for label, td in sorted(tardias_by_label.items()):
        warnings.append(
            '%s: %d pila(s) arrancan el ultimo dia de la ventana (%s) y quedan '
            'FUERA del pool por ser muy recientes (un solo dia de riego); '
            'entran en la ventana siguiente, donde ese dia es el primero: %s.'
            % (label, len(td), week_end.date(),
               ', '.join('%s el %s' % (pila, d.date())
                         for pila, d in sorted(td.items()))))

    n_active = len(rows)
    n_nuevas = sum(1 for r in rows if r['estado'] == 'activa_nueva')

    q_riego_medido = sum(r['q_riego'] for r in rows)
    q_pls_medido = sum(r['q_pls'] for r in rows)
    cu_fino_riego_medido = sum(r['q_riego'] * r['cu_riego'] for r in rows
                                if r['q_riego'] > 0 and pd.notna(r['cu_riego']))
    cu_fino_pls_medido = sum(r['q_pls'] * r['cu_pls'] for r in rows
                              if r['q_pls'] > 0 and pd.notna(r['cu_pls']))

    if q_riego_medido <= 0 or q_pls_medido <= 0:
        target_net_t = (float(anchor['net_cu_target_t'])
                        if anchor and anchor.get('net_cu_target_t') is not None else None)
        if (target_net_t is not None and
                (not math.isfinite(target_net_t) or abs(target_net_t) > 1e-6)):
            flow = anchor.get('net_cu_target_flow', 'el ancla neta')
            raise RuntimeError(
                f'{flow}: objetivo {target_net_t:.9f} t Cu sin pilas activas '
                'con caudal; no se puede construir una curva diaria que lo entregue.')
        warnings.append('QRiego_medido o QPLS_medido = 0 esta semana; sin pilas activas con caudal, no se reparte nada.')
        return dict(
            week_start=week_start, week_end=week_end, anchored=False,
            n_active=n_active, n_nuevas=n_nuevas,
            q_riego_medido=q_riego_medido, q_pls_medido=q_pls_medido,
            q_riego_recon=None, q_pls_recon=None,
            q_pls_recon_raw=None, fdrena_flow_raw=None,
            fdrena_flow_max=FDRENA_FLOW_MAX, fdrena_flow_clipped=False,
            delta_recon_riego=None, delta_recon_pls=None,
            cu_fino_riego_medido=cu_fino_riego_medido, cu_fino_pls_medido=cu_fino_pls_medido,
            cu_fino_riego_recon=None, cu_fino_pls_recon=None,
            delta_fino_riego=None, delta_fino_pls=None,
            ramp_cap_by_label={}, inventario_pls=0.0, inventario_fino_pls=0.0,
            net_cu_target_t=target_net_t, daily_net_cu_t=0.0,
            net_closure_residual_t=(0.0 if target_net_t == 0 else None),
            cu_fino_pls_daily=0.0,
            net_cu_by_label={label: {
                'target_flow': (anchor.get('net_cu_target_flow') if anchor else None),
                'target_t': target_net_t, 'daily_t': 0.0,
                'residual_t': (0.0 if target_net_t == 0 else None),
            } for label in materials} if target_net_t is not None else {},
            all_rows=rows, piles=[], daily=[], warnings=warnings,
        )

    # Paso 1: ancla global. Con `anchor` son los flujos REALES del Caso (su
    # run oficial); sin ancla se cae al placeholder de ruido sintetico, que
    # es lo que hacia el motor antes de que existiera el flowsheet global.
    #
    # Sin ancla: ruido sintetico SOLO en riego; PLS se recalcula con el
    # factor de drenaje fijo FDRENA_MAX (0.95), no con un segundo ruido
    # independiente. Dos ruidos independientes podian generar un par
    # (riego,pls) que viola Q_pls <= Q_riego, disparando el guardrail de
    # recorte sin motivo fisico.
    ratio_riego = _anchor_ratio(anchor, 'q_riego_recon', 'q_riego_medido')
    ratio_pls = _anchor_ratio(anchor, 'q_pls_recon', 'q_pls_medido')
    sin_cambio = _anchor_unchanged(anchor)
    if sin_cambio:                      # flujos globales sin cambio: el pad queda exactamente en lo medido
        ratio_riego = ratio_pls = 1.0
    if ratio_riego is not None:
        q_riego_recon = q_riego_medido * ratio_riego
    else:
        q_riego_recon = _noisy_global(week_start, 'q_riego_global', q_riego_medido, sigma_rel)
    if ratio_pls is not None:
        q_pls_recon = q_pls_medido * ratio_pls
    else:
        q_pls_recon = FDRENA_MAX * q_riego_recon

    # Tope fisico del pad: no se puede drenar mas de lo que se riega. Ver
    # FDRENA_FLOW_MAX. Se guarda el crudo antes de recortar.
    #
    # Con ancla esta funcion corre UN material a la vez (ver
    # `reconcile_flowsheet`), asi que el aviso es de ese pad y lo dice: sin el
    # prefijo, dos pads recortados producian dos lineas identicas y el aviso
    # ademas no se podia rutear a su material en el dashboard.
    _pad = ('%s: ' % next(iter(materials))) if len(materials) == 1 else ''
    q_pls_recon_raw = q_pls_recon
    fdrena_flow_raw = (q_pls_recon / q_riego_recon) if q_riego_recon > 0 else None
    fdrena_flow_clipped = False
    if q_riego_recon > 0 and fdrena_flow_raw > FDRENA_FLOW_MAX:
        q_pls_recon = FDRENA_FLOW_MAX * q_riego_recon
        fdrena_flow_clipped = True
        warnings.append(
            _pad +
            'Fdrena del pad reconciliado por flujos = %.6f > %.2f: el ancla pide '
            'drenar mas que el tope fisico. Q PLS recortado de %.1f a %.1f m3/h '
            '(%.1f%%). Revisar el balance del run oficial.'
            % (fdrena_flow_raw, FDRENA_FLOW_MAX, q_pls_recon_raw, q_pls_recon,
               (q_pls_recon / q_pls_recon_raw - 1.0) * 100.0))
    elif q_riego_recon > 0 and fdrena_flow_raw < FDRENA_FLOW_MIN_WARN:
        # Solo aviso, sin recorte: ver FDRENA_FLOW_MIN_WARN. El pad drena
        # mucho menos de lo que riega -- posible carga de inventario del lecho
        # (lo contrario de la descarga que reporta el lado alto), o un ancla
        # con el flujo de PLS incompleto en el run oficial.
        warnings.append(
            _pad +
            'Fdrena del pad reconciliado por flujos = %.6f < %.2f: el ancla '
            'entrega mucho menos PLS del que el riego permitiria. NO se corrige '
            '(el limite fisico es solo por arriba); puede ser lecho absorbiendo '
            'o un flujo de PLS incompleto en el run oficial. Q riego %.1f, '
            'Q PLS %.1f m3/h.'
            % (fdrena_flow_raw, FDRENA_FLOW_MIN_WARN, q_riego_recon, q_pls_recon))

    delta_recon_riego = q_riego_recon - q_riego_medido
    delta_recon_pls = q_pls_recon - q_pls_medido

    # Paso 6: FINO de Cu. Con ancla, la razon del Caso; sin ancla, el mismo
    # patron sintetico de paso 1 (ver `_noisy_global`).
    ratio_fr = _anchor_ratio(anchor, 'fino_riego_recon', 'fino_riego_medido')
    ratio_fp = _anchor_ratio(anchor, 'fino_pls_recon', 'fino_pls_medido')
    if sin_cambio:
        ratio_fr = ratio_fp = 1.0
    if ratio_fr is not None:
        cu_fino_riego_recon = cu_fino_riego_medido * ratio_fr
    else:
        cu_fino_riego_recon = _noisy_global(week_start, 'cu_fino_riego_global', cu_fino_riego_medido, sigma_rel)
    if ratio_fp is not None:
        cu_fino_pls_recon = cu_fino_pls_medido * ratio_fp
    else:
        cu_fino_pls_recon = _noisy_global(week_start, 'cu_fino_pls_global', cu_fino_pls_medido, sigma_rel)
    # 125-flow runs publish a pad-level net Cu balance (F25/F29). Use that
    # absolute reconciled balance as the PLS fine target after preserving the
    # separately reconciled irrigation fine. Internal fine is sum(Q*Cu); the
    # report's conversion to t Cu is 0.024 per daily Q[m3/h]*Cu[g/L].
    target_net_t = (float(anchor['net_cu_target_t'])
                    if anchor and anchor.get('net_cu_target_t') is not None and not sin_cambio else None)
    if target_net_t is not None:
        cu_fino_pls_recon = _pls_fine_target_for_net(target_net_t,
                                                    cu_fino_riego_recon)
    delta_fino_riego = cu_fino_riego_recon - cu_fino_riego_medido
    delta_fino_pls = cu_fino_pls_recon - cu_fino_pls_medido

    # Techo de la meseta de la curva de drenaje de paso 7. Es un limite del
    # lado RECONCILIADO (FDRENA_RECON_MAX), no el factor medido FDRENA_MAX:
    # la meseta es la asintota de una curva que arranca en 0.1, asi que para
    # que la SEMANA promedie el factor reconciliado (~0.95) la meseta tiene
    # que quedar por encima de ese promedio. Topar en 0.95 hacia infactible
    # toda curva no plana.
    ramp_cap_by_label = {label: FDRENA_RECON_MAX for label in {r['label'] for r in rows}}

    # Se reconcilian TODAS las activas de una sola pasada. No hay set
    # transiente que elegir ni loop adaptativo: eso venia del modelo viejo
    # TRANSIENTE/SS, donde solo un subconjunto de pilas se reconciliaba y el
    # resto quedaba fija en FDRENA_MAX. Ese corte lo decidia `dia_ciclo`, que
    # sale de `lectura_recuperacion` -- la tabla que abre campana para todo el
    # pad el mismo dia -- y ademas ya estaba muerto: el unico caller vivo pasa
    # `force_all_active=True`, que cortocircuitaba la condicion entera.
    piles, daily_rows, loop_warnings, clip_labels, inventario_by_label = _build_piles(
        rows, materials, week_start, q_riego_medido, q_pls_medido,
        delta_recon_riego, delta_recon_pls, delta_fino_riego, delta_fino_pls,
        ramp_cap_by_label, week_end=week_end,
        # sin cambio en los flujos globales no hay ajuste que repartir: tampoco rampa de pila nueva
        nuevas_by_label=({} if sin_cambio else nuevas_by_label), hold_measured=sin_cambio,
        campana_by_label=campana_by_label)
    warnings.extend(loop_warnings)
    daily_net_cu_t = _daily_net_cu_t(daily_rows)
    net_closure_residual_t = None
    if target_net_t is not None:
        net_closure_residual_t = daily_net_cu_t - target_net_t
        # A remaining ramp residue is internal PLS Cu not delivered in the
        # daily pile curves. Keep it explicit instead of changing the daily
        # profile after ramp constraints have been applied.
        if (not math.isfinite(net_closure_residual_t) or
                abs(net_closure_residual_t) > 1e-6):
            raise RuntimeError(
                f'{_pad}No se puede construir una curva diaria cerrada con '
                f'{anchor.get("net_cu_target_flow", "el ancla neta")}: objetivo '
                f'{target_net_t:.9f} t Cu, entrega diaria {daily_net_cu_t:.9f} t Cu, '
                f'residuo {net_closure_residual_t:+.9f} t Cu. La restricción de '
                'rampa/inventario impide entregar ese saldo en las pilas activas.')
    # Antes esto disparaba la expansion del set transiente. Ya no hay a quien
    # sumar -- todas las activas estan dentro -- asi que el recorte se reporta
    # tal cual. `clipped` se marca SOLO cuando `ramp_curve.ajustar` devuelve
    # status 'infactible', y eso solo puede pasarle a una pila NUEVA: la pila
    # en regimen sale por el retorno temprano de `_solve_meseta` con factor
    # plano y cierra exacta. No hay "meseta topada" -- M es la asintota de la
    # rampa y la curva ni siquiera la alcanza; lo que se agoto es el AREA de la
    # rampa de maxima pendiente bajo esa asintota.
    for label in sorted(clip_labels):
        warnings.append(
            f'{label}: al menos una pila NUEVA quedo infactible en paso 7 -- el Q '
            f'PLS que el ancla le asigna supera el area de la rampa mas empinada '
            f'posible bajo FDRENA_RECON_MAX. Se entrego el perfil diario factible y '
            f'el residuo se declaro (paso 7e). Revisar el balance del run oficial.')

    return dict(
        week_start=week_start, week_end=week_end,
        anchored=all(r is not None for r in (ratio_riego, ratio_pls, ratio_fr, ratio_fp)),
        n_active=n_active, n_nuevas=n_nuevas,
        q_riego_medido=q_riego_medido, q_pls_medido=q_pls_medido,
        q_riego_recon=q_riego_recon, q_pls_recon=q_pls_recon,
        q_pls_recon_raw=q_pls_recon_raw, fdrena_flow_raw=fdrena_flow_raw,
        fdrena_flow_max=FDRENA_FLOW_MAX, fdrena_flow_clipped=fdrena_flow_clipped,
        delta_recon_riego=delta_recon_riego, delta_recon_pls=delta_recon_pls,
        cu_fino_riego_medido=cu_fino_riego_medido, cu_fino_pls_medido=cu_fino_pls_medido,
        cu_fino_riego_recon=cu_fino_riego_recon, cu_fino_pls_recon=cu_fino_pls_recon,
        delta_fino_riego=delta_fino_riego, delta_fino_pls=delta_fino_pls,
        net_cu_target_t=target_net_t, daily_net_cu_t=daily_net_cu_t,
        net_closure_residual_t=net_closure_residual_t,
        cu_fino_pls_daily=sum(d.get('fino_pls_final') or 0.0 for d in daily_rows),
        net_cu_by_label=({label: {
            'target_flow': (anchor.get('net_cu_target_flow') if anchor else None),
            'target_t': target_net_t, 'daily_t': daily_net_cu_t,
            'residual_t': net_closure_residual_t,
        } for label in materials} if target_net_t is not None else {}),
        ramp_cap_by_label=ramp_cap_by_label,
        inventario_pls=sum(q for q, _ in inventario_by_label.values()),
        inventario_fino_pls=sum(f for _, f in inventario_by_label.values()),
        nuevas={lab: {p: d.date().isoformat() for p, d in nv.items()}
                for lab, nv in nuevas_by_label.items()},
        all_rows=rows, piles=piles, daily=daily_rows, warnings=warnings,
    )


METHOD_NAME = 'Flowsheet'

# Escalares aditivos del resultado de `reconcile_week_flowsheet`: todos son
# sumas sobre las pilas, asi que unir dos corridas por material es sumarlos.
_MERGE_SUM_KEYS = (
    'n_active', 'n_nuevas',
    'q_riego_medido', 'q_pls_medido', 'q_riego_recon', 'q_pls_recon',
    'delta_recon_riego', 'delta_recon_pls',
    'cu_fino_riego_medido', 'cu_fino_pls_medido',
    'cu_fino_riego_recon', 'cu_fino_pls_recon',
    'delta_fino_riego', 'delta_fino_pls',
    'net_cu_target_t', 'daily_net_cu_t', 'net_closure_residual_t',
    'cu_fino_pls_daily',
    'inventario_pls', 'inventario_fino_pls',
)


def merge_flowsheet_res(parts):
    """Une resultados de `reconcile_week_flowsheet` corrido UN MATERIAL A LA VEZ.

    Con ancla por Caso el paso 1 NO puede seguir siendo global: el Caso da
    un par medido/reconciliado por pad (F39/F48 para oxidos, F44/F50+F49
    para sulfuros) y el delta de oxidos tiene que caer en pilas de oxidos.
    Como `_build_piles` normaliza el paso 3 sobre las filas que recibe,
    correr material por material y unir aca es exactamente eso: cada pad
    reparte su propio delta contra su propio pool transiente.

    Sin ancla el motor sigue corriendo los dos materiales juntos con un
    unico ancla global, que es el comportamiento historico.
    """
    parts = [p for p in parts if p]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    out = dict(parts[0])
    for k in _MERGE_SUM_KEYS:
        vals = [p.get(k) for p in parts if p.get(k) is not None]
        out[k] = sum(vals) if len(vals) == len(parts) else None
    for k in ('all_rows', 'piles', 'daily', 'warnings'):
        out[k] = [x for p in parts for x in (p.get(k) or [])]
    # Diccionarios indexados POR LABEL: cada parte trae solo su material, asi
    # que unirlos es un update. `nuevas` estaba fuera de esta lista y de
    # `_MERGE_SUM_KEYS`, asi que se lo llevaba entero `out = dict(parts[0])`:
    # con dos materiales sobrevivian solo las pilas nuevas del PRIMERO
    # (SULFUROS, por el orden de `materials`) y una pila nueva de oxidos se
    # pintaba 'activa' en la grilla y no contaba en el KPI "activas / nuevas".
    # Los numeros del motor nunca estuvieron mal -- `n_nuevas` si se sumaba y
    # la rampa si se aplicaba --, era solo lo que se mostraba.
    for k in ('ramp_cap_by_label', 'nuevas'):
        merged = {}
        for p in parts:
            merged.update(p.get(k) or {})
        out[k] = merged
    out['local_direct_recovery'] = any(p.get('local_direct_recovery') for p in parts)
    out['recovery_rows'] = [x for p in parts for x in (p.get('recovery_rows') or [])]
    out['sulfide_audit'] = next((p['sulfide_audit'] for p in parts if p.get('sulfide_audit')), None)
    net_by_label = {}
    for p in parts:
        net_by_label.update(p.get('net_cu_by_label') or {})
    out['net_cu_by_label'] = net_by_label
    # Un resultado conjunto solo esta anclado si TODOS sus pads lo estan.
    # ``any`` pintaba una corrida parcial como oficial cuando el otro pad
    # habia caido al objetivo sintetico.
    out['anchored'] = all(p.get('anchored') for p in parts)
    # Diagnostico del tope de flujo del pad (`FDRENA_FLOW_MAX`). Es POR PAD, no
    # global: se recorta un material y el otro no. Al unir, el Q PLS crudo suma
    # como todo lo demas; `clipped` es un OR (basta un pad recortado); y el
    # Fdrena crudo se re-deriva del agregado en vez de heredar el de parts[0],
    # que era el de SULFUROS haciendose pasar por el del conjunto.
    raw = [p.get('q_pls_recon_raw') for p in parts if p.get('q_pls_recon_raw') is not None]
    out['q_pls_recon_raw'] = sum(raw) if raw else None
    out['fdrena_flow_clipped'] = any(p.get('fdrena_flow_clipped') for p in parts)
    q_r = out.get('q_riego_recon') or 0.0
    out['fdrena_flow_raw'] = (out['q_pls_recon_raw'] / q_r
                              if (q_r > 0 and out['q_pls_recon_raw'] is not None) else None)
    return out


# Las concentraciones de las pilas nuevas pueden cambiar hasta este porcentaje para que las ponderadas
# del pad coincidan con las de los flujos globales; la tolerancia (banda) es la diferencia relativa aceptada:
# dentro de ella no se ajusta nada y fuera solo se lleva hasta el borde de la banda.
SULFIDE_CONC_MAX_CHANGE = 0.30
SULFIDE_CONC_TOLERANCE = 0.10


def _sulfide_match_warning(match):
    """Aviso para el usuario sobre el ajuste de las pilas nuevas a los flujos globales."""
    status = match.get('status')
    if status == 'aplicado':
        extra = (f"; el Cu de riego del pad queda {match['diferencia_cu_riego_relativa']:.1%} fuera del global "
                 f"(los flujos globales no cuadran exactamente con F29)" if match.get('con_masas') else '')
        return [f"Sulfuros: pilas nuevas ajustadas a los flujos globales (riego x{match['beta']:.3f}, "
                f"Cu riego x{match['alpha_riego']:.3f}, Cu PLS x{match['alpha_pls']:.3f}){extra}."]
    if status == 'no_aplicado':
        return [f"Sulfuros: no se igualaron las masas y concentraciones de los flujos globales "
                f"({match.get('motivo')}); se conservan los valores medidos."]
    return []


def _sulfide_balance_totals(recovery_rows, piles, ws, we):
    """Totales del balance de Sulfuros para las tarjetas de deltas.

    El metodo conserva el riego y los Cu medidos: delta de riego y de Cu fino de riego
    son 0. El caudal PLS medido sigue la convencion del dash (0.95 x riego) y el
    reconciliado es el ajustado en las jovenes; las maduras no se ajustan. El Cu fino de
    PLS se despeja del Cu neto de cada pila (neto = 0.024 x (fino PLS - fino riego)):
    medido desde la recuperacion observada (0.95 x riego si la pila no tiene lectura al
    cierre) y reconciliado desde el resultado del metodo. Misma unidad que el motor:
    suma diaria de caudal [m3/h] x Cu [g/L]."""
    k_f = 0.024
    base_day = pd.Timestamp(ws).normalize() - pd.Timedelta(days=1)
    end_day = pd.Timestamp(we).normalize()
    by_pile = {}
    for row in recovery_rows:
        by_pile.setdefault(row['pile'], {})[pd.Timestamp(row['date']).normalize()] = row
    t = dict(q_pls_medido=0.0, q_pls_recon=0.0, q_riego_med=0.0, q_riego_rec=0.0, fino_riego=0.0, fino_riego_rec=0.0,
             fino_pls_medido=0.0, fino_pls_recon=0.0)
    for pile in piles:
        entries = pile['daily']
        q = [e['q_riego_medido'] or 0.0 for e in entries]
        q_rec = [e['q_riego_final'] or 0.0 for e in entries]
        fino_riego = sum(qq * e['cu_riego_medido'] for qq, e in zip(q, entries)
                         if qq and e.get('cu_riego_medido') is not None)
        fino_riego_rec = sum(qq * e['cu_riego_recon'] for qq, e in zip(q_rec, entries)
                             if qq and e.get('cu_riego_recon') is not None)
        fitted = [e['q_pls_final'] for e in entries if e.get('q_pls_final') is not None]
        t['q_pls_medido'] += FDRENA_MAX * sum(q)
        t['q_riego_rec'] += sum(q_rec)
        t['q_riego_med'] += sum(q)
        t['q_pls_recon'] += sum(fitted) if pile.get('status') == 'young' else FDRENA_MAX * sum(q)
        t['fino_riego'] += fino_riego
        t['fino_riego_rec'] += fino_riego_rec
        rows = by_pile.get(pile['parcela'], {})
        base, last = rows.get(base_day), rows.get(end_day)
        if base is None or last is None:
            continue
        cu_tf = base['cu_apilado_t']
        net_rec = cu_tf * (last['reconciled_pct'] - base['official_pct']) / 100.0
        if last.get('observed_pct') is not None:
            net_med = cu_tf * (last['observed_pct'] - base['official_pct']) / 100.0
        else:
            net_med = k_f * sum(FDRENA_MAX * qq * e['cu_pls_medido'] - qq * e['cu_riego_medido']
                                for qq, e in zip(q, entries)
                                if qq and e.get('cu_pls_medido') is not None and e.get('cu_riego_medido') is not None)
        t['fino_pls_recon'] += net_rec / k_f + fino_riego_rec
        t['fino_pls_medido'] += net_med / k_f + fino_riego
    return dict(
        q_pls_medido=t['q_pls_medido'], q_pls_recon=t['q_pls_recon'],
        cu_fino_riego_medido=t['fino_riego'], cu_fino_riego_recon=t['fino_riego_rec'],
        cu_fino_pls_medido=t['fino_pls_medido'], cu_fino_pls_recon=t['fino_pls_recon'],
        delta_recon_riego=t['q_riego_rec'] - t['q_riego_med'], delta_recon_pls=t['q_pls_recon'] - t['q_pls_medido'],
        delta_fino_riego=t['fino_riego_rec'] - t['fino_riego'], delta_fino_pls=t['fino_pls_recon'] - t['fino_pls_medido'])


def _reconcile_sulfide_local(week_start, week_end, material, anchor):
    """Produce local direct-recovery data; SQL persistence is unsupported."""
    from .sulfide_method import reconcile_sulfides
    inputs = material.get('sulfide_inputs')
    if not inputs or not inputs.get('rows') or not inputs.get('source_ids'):
        raise ValueError('SULFUROS requiere sulfide_inputs con rows y source_ids')
    if not anchor or anchor.get('net_cu_target_t') is None:
        raise ValueError('SULFUROS requiere objetivo neto F29')
    ws, we, _ = resolve_window(week_start, week_end)
    if pd.Timestamp(inputs.get('target_period_start')).normalize() != ws:
        raise ValueError('SULFUROS target_period_start no coincide con inicio del Caso')
    # Concentraciones globales del Caso (g/L) = 1000 x fino [t] / masa [m3] de los flujos de riego y de PLS del pad.
    def _global_conc(fino, masa):
        return 1000.0 * fino / masa if isinstance(fino, (int, float)) and isinstance(masa, (int, float)) and masa > 0 else None
    _mass = lambda value: float(value) / 24.0 if isinstance(value, (int, float)) and value > 0 else None   # m3 -> suma diaria de m3/h
    conc_targets = dict(cu_riego_g_l=_global_conc(anchor.get('fino_riego_recon'), anchor.get('q_riego_recon')),
                        cu_pls_g_l=_global_conc(anchor.get('fino_pls_recon'), anchor.get('q_pls_recon')),
                        q_riego_m3h_sum=_mass(anchor.get('q_riego_recon')), q_pls_m3h_sum=_mass(anchor.get('q_pls_recon')))
    result, audit = reconcile_sulfides(inputs['rows'], ws, we, anchor['net_cu_target_t'],
                                       concentration_targets=conc_targets,
                                       max_concentration_change=SULFIDE_CONC_MAX_CHANGE,
                                       concentration_tolerance=SULFIDE_CONC_TOLERANCE)
    def _json_safe(value):
        if isinstance(value, dict):
            return {('/'.join(map(str, key)) if isinstance(key, tuple) else str(key)): _json_safe(item)
                    for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(item) for item in value]
        if hasattr(value, 'isoformat') and not isinstance(value, str):
            return value.isoformat()
        return value
    audit['source_ids'] = inputs['source_ids']
    audit['water_balance'] = 'Diferencia riego/drenaje incluye almacenamiento y otras perdidas; no validada fisicamente.'
    by_pile = {}
    for r in result:
        if str(r['pad']).upper() not in ('SU', 'SULFUROS', 'SULFURO'):
            continue
        d = pd.Timestamp(r['date']).normalize()
        if ws <= d <= we:
            by_pile.setdefault((r['pile'], r['campaign']), []).append(r)
    # The legacy persistence schema cannot represent observed recovery without
    # inventing mature drainage. Consumers must use recovery_rows directly.
    recovery_rows = []
    for r in result:
        x = dict(r)
        x['reconciled_pct'] = x.get('reconciled_pct', x['official_pct'])
        x['recovery_source'] = ('observed' if (x['pad'], x['pile'], x['campaign']) in audit['mature'] and ws <= pd.Timestamp(x['date']).normalize() <= we else
                                'net_fit' if (x['pad'], x['pile'], x['campaign']) in audit['young'] and ws <= pd.Timestamp(x['date']).normalize() <= we else 'official')
        recovery_rows.append(x)
    piles, daily, all_rows = [], [], []
    for (pile, campaign), records in by_pile.items():
        age = (we.date() - pd.Timestamp(records[0]['first_irrigation']).date()).days
        entries = []
        for r in records:
            q = r.get('q_riego_m3h')
            q_rec = r.get('q_riego_recon_m3h', q)            # las nuevas pueden traer riego reconciliado
            qd = r.get('fitted_q_drenaje_m3h')
            # Las nuevas pueden traer concentraciones reconciliadas (ajuste a los flujos globales).
            cr_rec = r.get('cu_riego_recon_gL', r.get('cu_riego_gL'))
            cd_rec = r.get('cu_drenaje_recon_gL', r.get('cu_drenaje_gL'))
            entries.append(dict(label='SULFUROS', parcela=pile, campaign=campaign,
                                date=pd.Timestamp(r['date']).normalize(), q_riego_medido=q,
                                q_pls_medido=None, cu_riego_medido=r.get('cu_riego_gL'),
                                cu_pls_medido=r.get('cu_drenaje_gL'), q_riego_final=q_rec,
                                fino_riego_final=(q_rec*cr_rec if q_rec is not None and cr_rec is not None else None),
                                q_pls_final=qd, cu_riego_recon=cr_rec,
                                cu_pls_recon=cd_rec,
                                fino_pls_final=(qd*cd_rec if qd is not None and cd_rec is not None else None),
                                ramp_factor=(qd/q_rec if qd is not None and q_rec else None)))
        piles.append(dict(label='SULFUROS', parcela=pile, campaign=campaign, dia_ciclo=age, daily=entries,
                          status=('young' if age <= 30 else 'measured')))
        all_rows.append(dict(label='SULFUROS', parcela=pile, campaign=campaign, dia_ciclo=age))
        daily.extend(entries)
    q_values = [d['q_riego_final'] for d in daily]
    q_total = sum(q_values) if all(q is not None for q in q_values) else None
    q_meas = [d['q_riego_medido'] for d in daily]
    q_total_medido = sum(q_meas) if all(q is not None for q in q_meas) else None
    totals = _sulfide_balance_totals(recovery_rows, piles, ws, we)
    out = {k: None for k in _MERGE_SUM_KEYS}
    out.update(week_start=ws, week_end=we, anchored=True, n_active=len(piles), n_nuevas=len(audit['young']),
               q_riego_medido=q_total_medido, q_riego_recon=q_total, **totals,
               net_cu_target_t=anchor['net_cu_target_t'], daily_net_cu_t=audit['curve_net_t'],
               net_closure_residual_t=audit['net_residual_t'], all_rows=all_rows, piles=piles,
               daily=daily, warnings=['Sulfuros: resultado local; drenaje de maduras desconocido.']
                                      + _sulfide_match_warning(audit.get('concentration_match') or {}),
               recovery_rows=recovery_rows, sulfide_audit=_json_safe(audit), local_direct_recovery=True,
               ramp_cap_by_label={}, nuevas={'SULFUROS': {pile: str(next(r['first_irrigation'] for r in result if r['pile'] == pile and r['campaign'] == campaign)) for _, pile, campaign in audit['young']}},
               net_cu_by_label={'SULFUROS': {'target_t': anchor['net_cu_target_t'],
                    'daily_t': audit['curve_net_t'], 'residual_t': audit['net_residual_t']}},
               q_pls_recon_raw=None, fdrena_flow_raw=None, fdrena_flow_max=None,
               fdrena_flow_clipped=False)
    return out


def reconcile_flowsheet(week_start, materials, n_transient=N_TRANSIENT_DEFAULT,
                        sigma_rel=SIGMA_REL_DEFAULT, force_all_active=False,
                        week_end=None, anchor=None):
    """Punto de entrada unico. `anchor` es un dict POR LABEL
    ({'OXIDOS': {...}, 'SULFUROS': {...}}, claves de `ANCHOR_KEYS`); con el
    se resuelve un material a la vez y se unen los resultados (ver
    `merge_flowsheet_res`). Sin `anchor` corre los materiales juntos, igual
    que antes."""
    if not anchor:
        return reconcile_week_flowsheet(
            week_start, materials, n_transient=n_transient, sigma_rel=sigma_rel,
            force_all_active=force_all_active, week_end=week_end)
    parts = []
    for label, mat in materials.items():
        if label == 'SULFUROS' and mat.get('sulfide_policy') != 'legacy':
            parts.append(_reconcile_sulfide_local(week_start, week_end, mat, anchor.get(label)))
        else:
            parts.append(reconcile_week_flowsheet(
                week_start, {label: mat}, n_transient=n_transient, sigma_rel=sigma_rel,
                force_all_active=force_all_active, week_end=week_end, anchor=anchor.get(label)))
    return merge_flowsheet_res(parts)


def _raw_daily_pile(mat, p, week_start, week_end=None):
    """Un dict crudo SIN ajuste (q, cu_riego, cu_pls) por dia de la ventana,
    para una pila SS -- mismo patron de lectura que `_distribute_daily_pile`,
    sin ramp."""
    riego_df, cu_riego_s, drena_cu_df = mat['riego'], mat['cu_riego'], mat['drena_cu']
    week_start, _we, n_days = resolve_window(week_start, week_end)
    out = []
    for offset in range(n_days):
        date = week_start + pd.Timedelta(days=offset)
        q = float(riego_df.at[date, p]) if (p in riego_df.columns and date in riego_df.index) else 0.0
        q = q if q > 0 else 0.0
        cu_r = float(cu_riego_s.at[date]) if (date in cu_riego_s.index and pd.notna(cu_riego_s.at[date])) else np.nan
        cu_p = np.nan
        if p in drena_cu_df.columns and date in drena_cu_df.index and pd.notna(drena_cu_df.at[date, p]):
            cu_p = float(drena_cu_df.at[date, p])
        out.append(dict(q=q, cu_riego=cu_r, cu_pls=cu_p))
    return out


def reconcile_week_flowsheet_db(week_start, materials, conn, n_transient=N_TRANSIENT_DEFAULT,
                                 sigma_rel=SIGMA_REL_DEFAULT, force_all_active=False,
                                 week_end=None, anchor=None, caso_id=None, res=None):
    """Corre `reconcile_week_flowsheet` y persiste en la capa de DB compartida
    con el dashboard, usando el mismo esquema legacy para no romper lectores
    existentes del dash. No usa produccion de planta -> actual_t/mt_base_t/
    mt_opt_t quedan en None (campos propios del metodo de masa, no aplican
    aqui)."""
    from .db_pipeline import save_run
    week_start, week_end, _n_days = resolve_window(week_start, week_end)
    # `res` permite persistir EXACTAMENTE el resultado que ya calculo el
    # llamador. Antes `_dash` resolvia la semana y despues llamaba aca, que
    # la volvia a resolver entera: el doble de trabajo y, peor, dos
    # resultados distintos si algo del ancla o del ruido no era determinista
    # (lo que se mostraba no era lo que quedaba guardado).
    if res is None:
        res = reconcile_flowsheet(week_start, materials, n_transient=n_transient, sigma_rel=sigma_rel,
                                   force_all_active=force_all_active, week_end=week_end, anchor=anchor)
    if res.get('local_direct_recovery'):
        raise RuntimeError('La recuperacion directa de Sulfuros no admite persistencia SQL legacy')
    _num = lambda v: v if pd.notna(v) else None

    row_build_started = time.perf_counter()
    trans_keys = {(p['label'], p['parcela']) for p in res['piles']}
    detalle_rows, daily_rows = [], []

    for p in res['piles']:
        for d in p['daily']:
            q, q_pls = d['q_riego_final'], d['q_pls_final']
            daily_rows.append(dict(
                label=p['label'], parcela_nombre=p['parcela'], dia_offset=(d['date'] - week_start).days,
                fdrena=(q_pls / q) if q else FDRENA_MAX, q=q, q_pls=q_pls,
                cu_drena=d['cu_pls_recon'], cu_riego=d['cu_riego_recon'],
            ))

        def _avg(k, days=p['daily']):
            vals = [dd[k] for dd in days if dd[k] is not None]
            return sum(vals) / len(vals) if vals else None

        q_mean, q_pls_mean = _avg('q_riego_final'), _avg('q_pls_final')
        detalle_rows.append(dict(
            label=p['label'], parcela_nombre=p['parcela'], estado='TRANS',
            fdrena=(q_pls_mean / q_mean) if q_mean else FDRENA_MAX, fdrena_prior=FDRENA_MAX,
            dia_ciclo=p['dia_ciclo'], w_t=None, z_t=None,
            q_mean=q_mean, q_pls_mean=q_pls_mean,
            cu_drena_mean=_avg('cu_pls_recon'), cu_riego_mean=_avg('cu_riego_recon'),
        ))

    for r in res['all_rows']:
        if (r['label'], r['parcela']) in trans_keys:
            continue
        raw = _raw_daily_pile(materials[r['label']], r['parcela'], week_start, week_end=week_end)
        for i, rd in enumerate(raw):
            daily_rows.append(dict(
                label=r['label'], parcela_nombre=r['parcela'], dia_offset=i,
                fdrena=FDRENA_MAX, q=rd['q'], q_pls=FDRENA_MAX * rd['q'],
                cu_drena=_num(rd['cu_pls']), cu_riego=_num(rd['cu_riego']),
            ))

        def _avg_raw(k, days=raw):
            vals = [rd[k] for rd in days if pd.notna(rd[k])]
            return float(sum(vals) / len(vals)) if vals else None

        q_mean = _avg_raw('q')
        detalle_rows.append(dict(
            label=r['label'], parcela_nombre=r['parcela'], estado='SS',
            fdrena=FDRENA_MAX, fdrena_prior=FDRENA_MAX, dia_ciclo=r['dia_ciclo'],
            w_t=None, z_t=None, q_mean=q_mean,
            q_pls_mean=(FDRENA_MAX * q_mean) if q_mean else None,
            cu_drena_mean=_avg_raw('cu_pls'), cu_riego_mean=_avg_raw('cu_riego'),
        ))

    # converged=False cuando reconcile_week_flowsheet no tuvo caudal con que
    # repartir (q_riego_medido o q_pls_medido = 0, ver linea ~912) o cuando no
    # quedo ninguna pila activa -- ambos casos dejan *_recon en None y el badge
    # no debe leerse como "Reconciliado".
    converged = res['q_riego_recon'] is not None and res['n_active'] > 0
    record_phase('engine.prepare_persistence_rows',
                 time.perf_counter() - row_build_started,
                 detail_rows=len(detalle_rows), daily_rows=len(daily_rows),
                 active_piles=len(res['piles']), raw_piles=len(res['all_rows']))

    return save_run(
        conn, week_start, method=METHOD_NAME, active_days=n_transient, sigma_rel=sigma_rel,
        r_global=(1.0 if converged else 0.0), converged=converged,
        week_row=dict(actual_t=None, mt_base_t=None, mt_opt_t=None),
        detalle_rows=detalle_rows, daily_rows=daily_rows,
        warnings=res['warnings'], semana_fin=week_end, caso_id=caso_id,
    )


def reconcile_week_flowsheet_dash(week_start, materials, produccion, conn, active_days=N_TRANSIENT_DEFAULT,
                                   force_all_active=False, sigma_rel=SIGMA_REL_DEFAULT,
                                   week_end=None, anchor=None, caso_id=None):
    """Adaptador para `pad_dashboard.compute_recon`: `joint` dict de entrada/
    salida, resuelto y persistido con la metodologia de flowsheet.
    `produccion` no se usa (este metodo no reconcilia contra produccion de
    planta). `force_all_active=True` fuerza TODAS las pilas activas al pool
    transiente/reconciliado, ignorando el corte TRANS/SS por dia_ciclo."""
    week_start, week_end, n_days = resolve_window(week_start, week_end)
    solve_started = time.perf_counter()
    res = reconcile_flowsheet(week_start, materials, n_transient=active_days, sigma_rel=sigma_rel,
                               force_all_active=force_all_active, week_end=week_end, anchor=anchor)
    solve_seconds = time.perf_counter() - solve_started
    record_phase('engine.solve', solve_seconds,
                 active_piles=int(res.get('n_active') or 0),
                 pile_rows=len(res.get('piles') or []))
    # Se persiste EL MISMO `res` que se devuelve para pintar; no se
    # recalcula (ver `res=` en `reconcile_week_flowsheet_db`).
    persist_started = time.perf_counter()
    if not res.get('local_direct_recovery'):
        reconcile_week_flowsheet_db(week_start, materials, conn, n_transient=active_days, sigma_rel=sigma_rel,
                                     force_all_active=force_all_active, week_end=week_end,
                                     anchor=anchor, caso_id=caso_id, res=res)
    persist_seconds = 0.0 if res.get('local_direct_recovery') else time.perf_counter() - persist_started
    record_phase('engine.persist_total', persist_seconds)

    # Misma senal que reconcile_week_flowsheet_db: sin caudal repartido o sin
    # pilas activas, no hay reconciliacion real que mostrar en verde.
    converged = res['q_riego_recon'] is not None and res['n_active'] > 0
    r_global = 1.0 if converged else 0.0

    week_row = dict(actual=None, mt_base_t=None, mt_opt_t=None, resid_base=None, resid_opt=None)

    # Ruteo de warnings por material. `res['warnings']` viene de
    # `merge_flowsheet_res` como UNA sola lista concatenada de los dos pads;
    # el dashboard la ponia entera en el joint Y en cada material, asi que su
    # dedupe (`w not in joint_set`) dejaba todo pintado como [GLOBAL], incluso
    # los avisos que nombran su pad en el propio texto. Cada warning de pad
    # arranca con 'LABEL: ' o 'LABEL/Pxx ', asi que el corte es por prefijo; lo
    # que no matchea ningun label es global de verdad (el tope de Fdrena del
    # ancla, el balance incerrable).
    def _warns(label):
        return [w for w in res['warnings']
                if w.startswith(label + ': ') or w.startswith(label + '/')]
    warns_de_pad = {w for label in materials for w in _warns(label)}
    warns_globales = [w for w in res['warnings'] if w not in warns_de_pad]

    sub = {}
    for label in materials:
        rows_l = [r for r in res['all_rows'] if r['label'] == label]
        piles_l = [p for p in res['piles'] if p['label'] == label]
        # Todas las activas se reconcilian, asi que `piles_l` las cubre por
        # completo. `ss` queda vacia: el estado SS (pila activa que NO se
        # reconciliaba y quedaba fija en FDRENA_MAX) se elimino junto con el
        # corte por `dia_ciclo`. Se conserva la clave porque el dashboard la
        # lee.
        transient = [p['parcela'] for p in piles_l if p.get('status', 'young') == 'young']
        ss = [p['parcela'] for p in piles_l if p.get('status') == 'measured']
        fixed = [p['parcela'] for p in piles_l if p.get('status') == 'official_boundary']
        fdrena, fdrena_prior_map, day_in_cycle = {}, {}, {}
        # Fdrena DIARIO reconciliado: la curva de paso 7, dia a dia. Es lo
        # unico que de verdad varia. `fdrena` (semanal) es otra cosa: en las
        # SS es FDRENA_MAX literal -- el factor MEDIDO -- y en las TRANS es
        # el agregado Sum(q_pls)/Sum(q_riego), que por construccion del paso 4
        # da exactamente FDRENA_MAX tambien (ver METODOLOGIA.md 10.6). Mirar
        # solo `fdrena` da la impresion falsa de que la reconciliacion dejo
        # el drenaje plano.
        fdrena_dia = {}
        for p in piles_l:
            qs = [d['q_riego_final'] for d in p['daily']]
            qps = [d['q_pls_final'] for d in p['daily']]
            q = sum(qs) if all(v is not None for v in qs) else None
            qp = sum(qps) if all(v is not None for v in qps) else None
            fdrena[p['parcela']] = (qp / q) if q and qp is not None else None
            fdrena_prior_map[p['parcela']] = FDRENA_MAX
            day_in_cycle[p['parcela']] = p['dia_ciclo']
            fdrena_dia[p['parcela']] = [float(d['ramp_factor']) if d['ramp_factor'] is not None else None for d in p['daily']]
        sub[label] = dict(
            Fdrena=fdrena, Fdrena_prior=fdrena_prior_map, method=METHOD_NAME,
            transient=transient, ss=ss, fixed_transient=fixed, active=transient + ss + fixed,
            weeks={week_start: dict(week_row)}, converged=converged, warnings=_warns(label),
            R_global=r_global, day_in_cycle=day_in_cycle, rec_ratio={},
            Fdrena_dia=fdrena_dia,
            # {pila: fecha ISO del primer riego} de las que ARRANCAN en la
            # ventana -- las unicas con ramp-up. Lo consume la grilla del
            # dashboard para pintar 'activa nueva' con el mismo criterio con
            # que el motor decide la curva.
            nuevas=dict(res.get('nuevas', {}).get(label, {})),
        )

    # Totales del balance de flowsheet. Este metodo NO reconcilia contra
    # produccion de planta, asi que week_row va todo en None y los KPI de
    # planta (Real t / Err % / Mejora RMSE) quedarian en N/A; `totals` es lo
    # que si tiene sentido mostrar para esta metodologia.
    totals = {k: res.get(k) for k in (
        'n_active', 'n_nuevas', 'anchored',
        'q_riego_medido', 'q_riego_recon', 'q_pls_medido', 'q_pls_recon',
        'cu_fino_riego_medido', 'cu_fino_riego_recon',
        'cu_fino_pls_medido', 'cu_fino_pls_recon',
        'delta_fino_riego', 'delta_fino_pls',
        'delta_recon_riego', 'delta_recon_pls',
    )}

    return dict(
        materials=sub, weeks={week_start: dict(week_row)}, R_global=r_global, converged=converged,
        method=('Sulfuros: ajuste de curvas de hasta 30 días' if res.get('local_direct_recovery') else METHOD_NAME), warnings=warns_globales, estimate_scale=False, targets=None,
        totals=totals, week_start=week_start, week_end=week_end, n_days=n_days,
        # `res` crudo (con `piles` y su detalle diario). No es serializable a
        # JSON y no va al store del dashboard: lo necesita el reporte por el
        # metodo reconciliado (`report_metodo.construir_doc`), que reconstruye
        # la curva de cada pila con el Q y el Cu reconciliados dia a dia.
        res=res,
        _phase_seconds=dict(solve=solve_seconds, persist=persist_seconds),
    )


def run_report(materials, weeks, n_transient=N_TRANSIENT_DEFAULT, sigma_rel=SIGMA_REL_DEFAULT):
    weekly_rows, pile_rows, daily_rows = [], [], []
    for wk in weeks:
        res = reconcile_week_flowsheet(wk, materials, n_transient=n_transient, sigma_rel=sigma_rel)
        n_viol = sum(1 for w in res['warnings'] if 'negativo' in w or 'recortado' in w)
        weekly_rows.append(dict(
            week_start=res['week_start'], n_active=res['n_active'], n_nuevas=res['n_nuevas'],
            q_riego_medido=res['q_riego_medido'], q_pls_medido=res['q_pls_medido'],
            q_riego_recon=res['q_riego_recon'], q_pls_recon=res['q_pls_recon'],
            delta_recon_riego=res['delta_recon_riego'], delta_recon_pls=res['delta_recon_pls'],
            cu_fino_riego_medido=res['cu_fino_riego_medido'], cu_fino_pls_medido=res['cu_fino_pls_medido'],
            cu_fino_riego_recon=res['cu_fino_riego_recon'], cu_fino_pls_recon=res['cu_fino_pls_recon'],
            delta_fino_riego=res['delta_fino_riego'], delta_fino_pls=res['delta_fino_pls'],
            n_warnings=len(res['warnings']), n_violations=n_viol,
        ))
        for p in res['piles']:
            row = dict(week_start=res['week_start'])
            row.update({k: v for k, v in p.items() if k != 'daily'})
            pile_rows.append(row)
        daily_rows.extend(res['daily'])
    weekly_df = pd.DataFrame(weekly_rows)
    piles_df = pd.DataFrame(pile_rows)
    daily_df = pd.DataFrame(daily_rows)
    return weekly_df, piles_df, daily_df


def _closure_check(res):
    q_riego_recon, q_pls_recon = res['q_riego_recon'], res['q_pls_recon']
    if q_riego_recon is None:
        return None
    piles, all_rows = res['piles'], res['all_rows']
    # Sin estado SS ya no hay pilas activas fuera de `piles`: el total es el
    # de las reconciliadas y nada mas.
    total_q_riego = sum(p['q_riego_final'] for p in piles)
    # El PLS entregado por las pilas mas el INVENTARIO declarado: el pad
    # siempre cierra contra el ancla, y lo que no sale del riego de la ventana
    # queda nombrado como descarga del lecho en vez de esconderse como ajuste
    # extra de la pila nueva (paso 7e).
    inventario_pls = res.get('inventario_pls') or 0.0
    total_q_pls = sum(p['q_pls_final'] for p in piles) + inventario_pls
    fino_riego = fino_pls = 0.0
    for p in piles:
        for d in p['daily']:
            if d['cu_riego_recon'] is not None:
                fino_riego += d['cu_riego_recon'] * d['q_riego_final']
            if d['cu_pls_recon'] is not None:
                fino_pls += d['cu_pls_recon'] * d['q_pls_final']
    # El fino viaja con el caudal: si el inventario aporta Q PLS tambien
    # aporta su masa de Cu, si no la ley ponderada sale diluida.
    fino_pls += res.get('inventario_fino_pls') or 0.0
    cu_riego_w = fino_riego / total_q_riego if total_q_riego else None
    cu_pls_w = fino_pls / total_q_pls if total_q_pls else None
    cu_riego_t = res['cu_fino_riego_recon'] / q_riego_recon if q_riego_recon else None
    cu_pls_t = res['cu_fino_pls_recon'] / q_pls_recon if q_pls_recon else None

    def _ok(a, b):
        return a is not None and b is not None and abs(a - b) < 1e-3 * max(1.0, abs(b))

    return dict(
        q_riego_total=total_q_riego, q_riego_recon=q_riego_recon, q_riego_ok=_ok(total_q_riego, q_riego_recon),
        q_pls_total=total_q_pls, q_pls_recon=q_pls_recon, q_pls_ok=_ok(total_q_pls, q_pls_recon),
        cu_riego_w=cu_riego_w, cu_riego_target=cu_riego_t, cu_riego_ok=_ok(cu_riego_w, cu_riego_t),
        cu_pls_w=cu_pls_w, cu_pls_target=cu_pls_t, cu_pls_ok=_ok(cu_pls_w, cu_pls_t),
        inventario_pls=inventario_pls,
        inventario_fino_pls=res.get('inventario_fino_pls') or 0.0,
    )


def format_week_report(res, n_transient=N_TRANSIENT_DEFAULT):
    lines = []
    w = res['week_start']
    lines.append(f'REPORTE PASO A PASO -- semana {w.date()} (lunes) a {(w + pd.Timedelta(days=6)).date()} (domingo)')
    lines.append('=' * 78)
    lines.append(f'n_active={res["n_active"]}  n_nuevas={res["n_nuevas"]}')
    lines.append('')

    lines.append('--- Paso 1: caudal medido vs reconciliado (flowsheet global, placeholder sintetico) ---')
    lines.append(f'  QRiego_medido   = {res["q_riego_medido"]:.4f}')
    lines.append(f'  QRiego_recon    = {res["q_riego_recon"]:.4f}' if res['q_riego_recon'] is not None else '  QRiego_recon    = (sin datos esta semana)')
    lines.append(f'  Delta_Recon_Riego = {res["delta_recon_riego"]:.4f}' if res['delta_recon_riego'] is not None else '')
    lines.append(f'  QPLS_medido     = {res["q_pls_medido"]:.4f}')
    lines.append(f'  QPLS_recon      = {res["q_pls_recon"]:.4f}' if res['q_pls_recon'] is not None else '  QPLS_recon      = (sin datos esta semana)')
    lines.append(f'  Delta_Recon_PLS   = {res["delta_recon_pls"]:.4f}' if res['delta_recon_pls'] is not None else '')
    lines.append('')

    lines.append('--- Paso 2: clasificacion de pilas activas '
                 '(arranque en la ventana => ACTIVA NUEVA, con ramp-up) ---')
    all_df = pd.DataFrame(res['all_rows'])
    if not all_df.empty:
        all_df = all_df.sort_values(['label', 'dia_ciclo'], na_position='last')
        all_df['estado'] = all_df['estado'].map({'activa': 'ACTIVA',
                                                 'activa_nueva': 'ACTIVA NUEVA'})
        cols = ['label', 'parcela', 'dia_ciclo', 'estado', 'q_riego', 'q_pls', 'cu_riego', 'cu_pls']
        lines.append(all_df[cols].to_string(index=False))
    else:
        lines.append('  (sin pilas activas esta semana)')
    lines.append('')

    piles_df = pd.DataFrame(res['piles'])
    if piles_df.empty:
        lines.append('--- Sin pilas transientes esta semana: pasos 3, 6 y 4 no aplican. ---')
    else:
        lines.append('--- Paso 3: fraccion de aporte (sobre el total medido de TODAS las activas) ---')
        lines.append(piles_df[['label', 'parcela', 'frac_riego', 'frac_pls']].to_string(index=False))
        lines.append('')

        lines.append('--- Paso 6: Cu en riego / Cu en PLS reconciliado (corre antes del paso 4) ---')
        lines.append(f'  CuFino_Medido_Riego = {res["cu_fino_riego_medido"]:.4f}   CuFino_recon_Riego = {res["cu_fino_riego_recon"]:.4f}   Delta_Fino_Riego = {res["delta_fino_riego"]:.4f}')
        lines.append(f'  CuFino_Medido_PLS   = {res["cu_fino_pls_medido"]:.4f}   CuFino_recon_PLS   = {res["cu_fino_pls_recon"]:.4f}   Delta_Fino_PLS   = {res["delta_fino_pls"]:.4f}')
        lines.append(piles_df[['label', 'parcela', 'cu_riego_medido', 'aporte_fino_riego', 'cu_riego_recon',
                                'cu_pls_medido', 'aporte_fino_pls', 'cu_pls_recon']].to_string(index=False))
        lines.append('')

        lines.append('--- Paso 4: distribucion interna del delta de caudal (valor final por pila transiente) ---')
        lines.append(piles_df[['label', 'parcela', 'q_riego_medido', 'd_riego', 'q_riego_final',
                                'q_pls_medido', 'd_pls', 'q_pls_final']].to_string(index=False))
        lines.append('')

        lines.append('--- Paso 7: distribucion diaria (ramp-up drenaje) por pila transiente ---')
        lines.append('  Techo de la meseta de drenaje por material:')
        for label, cap in res['ramp_cap_by_label'].items():
            lines.append(f'    {label}: {cap:.4f}')
        for p in res['piles']:
            lines.append(f'  {p["label"]}/{p["parcela"]}:')
            ddf = pd.DataFrame(p['daily'])
            ddf['date'] = ddf['date'].dt.date
            lines.append(f'    meseta despejada={ddf["ramp_meseta"].iloc[0]:.4f}'
                          f'  status={ddf["ramp_status"].iloc[0]}')
            cols = ['date', 'dia_ciclo', 'ramp_factor', 'q_riego_medido', 'q_riego_final',
                    'cu_riego_medido', 'cu_riego_recon',
                    'q_pls_medido', 'q_pls_final', 'cu_pls_medido', 'cu_pls_recon']
            lines.append('  ' + ddf[cols].to_string(index=False).replace('\n', '\n  '))
            lines.append(f'    Sum semana: q_riego_final={ddf["q_riego_final"].sum():.4f}'
                          f' (paso4={p["q_riego_final"]:.4f})  q_pls_final={ddf["q_pls_final"].sum():.4f}'
                          f' (paso4={p["q_pls_final"]:.4f})')
    lines.append('')

    chk = _closure_check(res)
    if chk:
        def _fmt(x):
            return f'{x:.4f}' if x is not None else 'NA'
        lines.append('--- Verificacion de cierre (final vs reconciliado global inicial) ---')
        lines.append(f'  Q riego: total_final={_fmt(chk["q_riego_total"])}  recon={_fmt(chk["q_riego_recon"])}'
                      f'  -> {"OK" if chk["q_riego_ok"] else "NO CIERRA"}')
        lines.append(f'  Q PLS:   total_final={_fmt(chk["q_pls_total"])}  recon={_fmt(chk["q_pls_recon"])}'
                      f'  -> {"OK" if chk["q_pls_ok"] else "NO CIERRA"}')
        lines.append(f'  Cu riego ponderado (dia->pila, por flujo): {_fmt(chk["cu_riego_w"])}'
                      f'  target={_fmt(chk["cu_riego_target"])}  -> {"OK" if chk["cu_riego_ok"] else "NO CIERRA"}')
        lines.append(f'  Cu PLS ponderado (dia->pila, por flujo):   {_fmt(chk["cu_pls_w"])}'
                      f'  target={_fmt(chk["cu_pls_target"])}  -> {"OK" if chk["cu_pls_ok"] else "NO CIERRA"}')
        lines.append('')

    if res['warnings']:
        lines.append(f'--- Warnings ({len(res["warnings"])}) ---')
        lines.extend(f'  - {w_}' for w_ in res['warnings'])
    else:
        lines.append('--- Sin warnings ---')

    return '\n'.join(lines)


def run_week_report(week_start, materials, out_path=None, n_transient=N_TRANSIENT_DEFAULT,
                     sigma_rel=SIGMA_REL_DEFAULT):
    res = reconcile_week_flowsheet(week_start, materials, n_transient=n_transient, sigma_rel=sigma_rel)
    text = format_week_report(res, n_transient=n_transient)
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(text)
    return text


def _collect_dia_ciclo(materials, weeks):
    records = []
    for wk in weeks:
        week_start = week_monday(wk)
        week_end = week_start + pd.Timedelta(days=6)
        for label, mat in materials.items():
            active, _t, _ss, day_in_cycle, _r = classify_piles(
                week_start, mat['wip'], mat['rec_curves'], mat['max_rec'], mat['ciclo_d'])
            for p in active:
                dia_ciclo = _campaign_asof(label, p, week_end)
                if dia_ciclo is None:
                    dia_ciclo = day_in_cycle.get(p)
                records.append(dict(week_start=week_start, label=label, parcela=p, dia_ciclo=dia_ciclo))
    return pd.DataFrame(records)


def _plot_threshold_sensitivity(dia_df, thresholds, out_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    valid = dia_df.dropna(subset=['dia_ciclo'])
    counts = [int((valid['dia_ciclo'] < n).sum()) for n in thresholds]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([str(n) for n in thresholds], counts, color='#2563EB')
    for i, c in enumerate(counts):
        ax.text(i, c, str(c), ha='center', va='bottom', fontsize=8)
    ax.set_xlabel('n_transient (dia_ciclo < n)')
    ax.set_ylabel('filas pila-semana transientes')
    ax.set_title('Sensibilidad del umbral transiente (n=7..20)')
    fig.tight_layout()
    fig.savefig(f'{out_dir}\\flowsheet_plot_threshold_sensitivity.png', dpi=120)
    plt.close(fig)
    return pd.DataFrame({'n_transient': thresholds, 'n_filas_transientes': counts})


def _plot_report(weekly_df, piles_df, out_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    wk = weekly_df['week_start']

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(wk, weekly_df['q_riego_medido'], marker='o', label='Q riego medido', color='#2563EB')
    ax.plot(wk, weekly_df['q_riego_recon'], marker='o', linestyle='--', label='Q riego recon', color='#2563EB', alpha=0.5)
    ax.plot(wk, weekly_df['q_pls_medido'], marker='s', label='Q PLS medido', color='#DC2626')
    ax.plot(wk, weekly_df['q_pls_recon'], marker='s', linestyle='--', label='Q PLS recon', color='#DC2626', alpha=0.5)
    ax.set_title('Caudal medido vs reconciliado (flowsheet global, placeholder sintetico)')
    ax.set_ylabel('Caudal')
    ax.legend(fontsize=8)
    ax.tick_params(axis='x', rotation=45)
    fig.tight_layout()
    fig.savefig(f'{out_dir}\\flowsheet_plot_caudales.png', dpi=120)
    plt.close(fig)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    ax1.axhline(0, color='#999', linewidth=0.8)
    ax1.plot(wk, weekly_df['delta_recon_riego'], marker='o', label='Delta Recon Riego', color='#2563EB')
    ax1.plot(wk, weekly_df['delta_recon_pls'], marker='s', label='Delta Recon PLS', color='#DC2626')
    ax1.set_ylabel('Delta')
    ax1.legend(fontsize=8)
    ax2.bar(wk, weekly_df['n_nuevas'], width=4, color='#F59E0B', label='n pilas nuevas')
    ax2.bar(wk, weekly_df['n_violations'], width=4, color='#DC2626', label='n violaciones')
    ax2.set_ylabel('Conteo')
    ax2.legend(fontsize=8)
    ax2.tick_params(axis='x', rotation=45)
    fig.suptitle('Delta a repartir por semana y pilas transientes/violaciones')
    fig.tight_layout()
    fig.savefig(f'{out_dir}\\flowsheet_plot_delta.png', dpi=120)
    plt.close(fig)

    fig, (axr, axp) = plt.subplots(1, 2, figsize=(11, 5))
    if not piles_df.empty:
        for ax, frac_col, d_col, title in (
            (axr, 'frac_riego', 'd_riego', 'Riego: fraccion aporte vs delta asignado'),
            (axp, 'frac_pls', 'd_pls', 'PLS: fraccion aporte vs delta asignado'),
        ):
            ax.scatter(piles_df[frac_col], piles_df[d_col], c='#2563EB', edgecolor='white', s=60)
            for _, r in piles_df.iterrows():
                ax.annotate(f"{r['label']}/{r['parcela']}", (r[frac_col], r[d_col]), fontsize=7, xytext=(4, 4), textcoords='offset points')
            ax.set_xlabel('fraccion de aporte')
            ax.set_ylabel('delta asignado')
            ax.set_title(title, fontsize=9)
            ax.axhline(0, color='#999', linewidth=0.8)
    else:
        for ax in (axr, axp):
            ax.text(0.5, 0.5, 'sin pilas transientes', ha='center', va='center', transform=ax.transAxes)
    fig.suptitle('Reparto por pila transiente (todas las semanas)')
    fig.tight_layout()
    fig.savefig(f'{out_dir}\\flowsheet_plot_piles.png', dpi=120)
    plt.close(fig)


def _plot_daily(daily_df, week_x, out_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    wdf = daily_df[daily_df['week_start'] == week_x]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    (ax_q, ax_qpls), (ax_cur, ax_cupls) = axes
    colors = plt.cm.tab10.colors
    for i, (pila, g) in enumerate(wdf.groupby(['label', 'parcela'])):
        g = g.sort_values('date')
        c = colors[i % len(colors)]
        label = f'{pila[0]}/{pila[1]}'
        ax_q.plot(g['date'], g['q_riego_final'], marker='o', color=c, label=label)
        ax_qpls.plot(g['date'], g['q_pls_final'], marker='s', color=c, label=label)
        ax_cur.plot(g['date'], g['cu_riego_recon'], marker='o', color=c, label=label)
        ax_cupls.plot(g['date'], g['cu_pls_recon'], marker='s', color=c, label=label)
    ax_q.set_title('Q riego final (dia)')
    ax_qpls.set_title('Q PLS final (dia)')
    ax_cur.set_title('Cu riego reconciliado (dia)')
    ax_cupls.set_title('Cu PLS reconciliado (dia)')
    for ax in (ax_q, ax_qpls, ax_cur, ax_cupls):
        ax.legend(fontsize=7)
        ax.tick_params(axis='x', rotation=45)
    fig.suptitle(f'Paso 7 -- reparto diario, semana {pd.Timestamp(week_x).date()}')
    fig.tight_layout()
    fig.savefig(f'{out_dir}\\flowsheet_plot_daily.png', dpi=120)
    plt.close(fig)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, r'C:\Users\5330\Desktop\Recon curvas')
    from . import pad_dashboard as pd_

    weeks = sorted({d - pd.Timedelta(days=pd.Timestamp(d).weekday()) for d in pd_.RECON_PRODUCCION.index})

    weekly_df, piles_df, daily_df = run_report(pd_.RECON_MATERIALS, weeks)

    out_dir = r'C:\Users\5330\Desktop\Recon curvas'
    weekly_df.to_csv(f'{out_dir}\\flowsheet_report_weekly.csv', index=False)
    piles_df.to_csv(f'{out_dir}\\flowsheet_report_piles.csv', index=False)
    daily_df.to_csv(f'{out_dir}\\flowsheet_report_daily.csv', index=False)
    _plot_report(weekly_df, piles_df, out_dir)

    dia_df = _collect_dia_ciclo(pd_.RECON_MATERIALS, weeks)
    thresholds = list(range(7, 108))
    sens_df = _plot_threshold_sensitivity(dia_df, thresholds, out_dir)
    sens_df.to_csv(f'{out_dir}\\flowsheet_threshold_sensitivity.csv', index=False)
    print()
    print('--- Sensibilidad n_transient (7..20) ---')
    print(sens_df.to_string(index=False))

    print(f'Semanas procesadas: {len(weekly_df)}')
    print(f'Semanas con >=1 pila nueva: {(weekly_df["n_nuevas"] > 0).sum()}')
    print(f'Total filas pila-semana (activas): {len(piles_df)}')
    print(f'Total warnings: {weekly_df["n_warnings"].sum()} (de eso, violaciones riego>pls o negativo: {weekly_df["n_violations"].sum()})')
    print()
    print('--- Resumen semanal (primeras/ultimas filas) ---')
    with pd.option_context('display.width', 160, 'display.max_columns', 20):
        print(weekly_df.head(5).to_string(index=False))
        print('...')
        print(weekly_df.tail(5).to_string(index=False))
    print()
    if not piles_df.empty:
        print('--- Estadisticas de fraccion / delta por pila (transientes) ---')
        print(piles_df[['frac_riego', 'frac_pls', 'd_riego', 'd_pls']].describe().to_string())
    print()
    print(f'CSV: {out_dir}\\flowsheet_report_weekly.csv')
    print(f'CSV: {out_dir}\\flowsheet_report_piles.csv')
    print(f'CSV: {out_dir}\\flowsheet_report_daily.csv')
    print(f'PNG: {out_dir}\\flowsheet_plot_caudales.png')
    print(f'PNG: {out_dir}\\flowsheet_plot_delta.png')
    print(f'PNG: {out_dir}\\flowsheet_plot_piles.png')

    con_nuevas = weekly_df.loc[weekly_df['n_nuevas'] > 0, 'week_start']
    week_x = con_nuevas.iloc[0] if not con_nuevas.empty else weeks[0]
    week_txt = run_week_report(week_x, pd_.RECON_MATERIALS, out_path=f'{out_dir}\\flowsheet_week_report.txt')
    print()
    print(week_txt)
    print()
    print(f'TXT: {out_dir}\\flowsheet_week_report.txt')

    if not daily_df.empty and (daily_df['week_start'] == week_x).any():
        _plot_daily(daily_df, week_x, out_dir)
        print(f'PNG: {out_dir}\\flowsheet_plot_daily.png')

    # Exportación automática (Cambio 9)
    if not daily_df.empty:
        for wk, df_wk in daily_df.groupby("week_start"):
            output_dir = Path(out_dir) / pd.Timestamp(wk).strftime("%Y%m%d") / "transient_plots"
            for parcela, grp in df_wk.groupby("parcela"):
                export_transient_plot(grp, output_dir)
        print(f"Exported transient plots for all weeks.")
