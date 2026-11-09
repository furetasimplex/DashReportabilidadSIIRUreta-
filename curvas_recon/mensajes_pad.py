"""Mensajes para el operador de la pantalla de curvas / reconciliacion (sin SQL, sin Dash).

Cada mensaje es un dict `{nivel, titulo, texto, accion, detalle, ambito}`:
  * `nivel`: 'error' (bloquea: no hay resultado confiable), 'advertencia' (hay resultado con supuestos o desvios que
    conviene revisar) o 'informacion' (contexto, no requiere accion).
  * `texto`: que paso, con valor, limite y unidad; `accion`: que hacer; `detalle`: dato tecnico secundario (codigo de
    causa, texto original del motor), que la pantalla muestra plegado.
  * `ambito`: pila, flujo, nodo o material al que se refiere (puede ser None).

Fuentes:
  * `traducir_aviso_motor`: reescribe los avisos del motor de reconciliacion (`recon_engine`), que no se modifican.
  * `mensajes_reconciliacion_pad`: resultado de `reconciliacion_pad.reconcile_pad` (causas de infactibilidad, banda
    provisional, maduras en tope, factores de pilas nuevas, brecha de recuperacion al cierre).
  * `mensajes_run_solver`: estado y avisos del run del solver (solo si el dato esta disponible; el dash no consulta SQL
    al montar).
"""
from __future__ import annotations

import re

ERROR, ADVERTENCIA, INFORMACION = 'error', 'advertencia', 'informacion'
NIVELES = (ERROR, ADVERTENCIA, INFORMACION)

# Umbrales de aviso (provisionales, no calibrados con ensayos; configurables por argumento).
UMBRAL_FACTOR_NUEVA = 0.25        # |factor - 1| a partir del cual una pila nueva se avisa (caudal o ley)
UMBRAL_BRECHA_T_CU = 1.0          # |brecha de recuperacion al cierre| [t Cu] a partir de la cual se avisa
BANDA_ESTRICTA = 0.001            # banda de referencia (0,1 %); por encima se avisa como provisional


def _n(v, d=0):
    """Numero con coma decimal y punto de miles (es-CL)."""
    if v is None:
        return 'sin dato'
    s = f'{float(v):,.{d}f}'
    return s.replace(',', '\x00').replace('.', ',').replace('\x00', '.')


def _pct(v, d=1):
    return f'{_n(100 * float(v), d)} %'


def mensaje(nivel, titulo, texto, accion=None, detalle=None, ambito=None):
    assert nivel in NIVELES
    return dict(nivel=nivel, titulo=titulo, texto=texto, accion=accion, detalle=detalle, ambito=ambito)


def _pad(label):
    return {'SULFUROS': 'Sulfuros', 'OXIDOS': 'Óxidos'}.get(label, label)


# ── Avisos del motor ──────────────────────────────────────────────────────────

_F = r'(-?\d+(?:\.\d+)?)'
_MOTOR = []        # (regex, funcion(match, original) -> mensaje)


def _regla(patron):
    def deco(fn):
        _MOTOR.append((re.compile(patron, re.S), fn))
        return fn
    return deco


@_regla(rf'^(?:(\w+): )?Fdrena del pad reconciliado por flujos = {_F} > {_F}:.*?recortado de {_F} a {_F} m3/h \({_F}%\)')
def _fdrena_alto(m, orig):
    pad, f, lim, a, b, p = m.groups()
    return mensaje(ADVERTENCIA, 'Drenaje del pad sobre el límite físico',
                   f'Los flujos reconciliados del run oficial indican que el pad drena {_n(float(f), 3)} veces lo que riega, '
                   f'sobre el límite físico de {_n(float(lim), 2)}. El caudal de solución rica (PLS) se redujo de {_n(float(a), 1)} '
                   f'a {_n(float(b), 1)} m³/h ({_n(float(p), 1)} %).',
                   'Revisar el balance del run oficial (riego y PLS del pad) antes de usar este resultado.',
                   orig, _pad(pad) if pad else None)


@_regla(rf'^(?:(\w+): )?Fdrena del pad reconciliado por flujos = {_F} < {_F}:.*?Q riego {_F}, Q PLS {_F} m3/h')
def _fdrena_bajo(m, orig):
    pad, f, lim, qr, qp = m.groups()
    return mensaje(ADVERTENCIA, 'El pad drena mucho menos de lo que riega',
                   f'La razón drenaje/riego reconciliada es {_n(float(f), 3)}, bajo el umbral de aviso de {_n(float(lim), 2)} '
                   f'(riego {_n(float(qr), 1)} m³/h, PLS {_n(float(qp), 1)} m³/h). No se corrigió el valor.',
                   'Verificar si el lecho está absorbiendo solución o si falta un flujo de PLS en el run oficial.',
                   orig, _pad(pad) if pad else None)


@_regla(r'^QRiego_medido o QPLS_medido = 0')
def _sin_caudal(m, orig):
    return mensaje(ERROR, 'Faltan datos de riego o de PLS',
                   'El riego o el PLS medido de la semana es 0 m³/h y no hay pilas activas con caudal; no se repartió nada.',
                   'Cargar o corregir los caudales medidos de la ventana y volver a calcular.', orig)


@_regla(r'^(\w+)/(P\d+) (\d{4}-\d{2}-\d{2}): sin riego medido')
def _sin_riego_dia(m, orig):
    pad, pila, fecha = m.groups()
    return mensaje(INFORMACION, 'Día sin riego medido',
                   f'La pila {pila} no tiene riego medido el {fecha}; el ajuste de riego se repartió parejo en la semana.',
                   None, orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+)/(P\d+) \(edad=(\S+)\): el objetivo semanal ([\d.]+) queda fuera del perfil factible \((\w+)\)\. Se entrega ([\d.]+)')
def _rampa_fuera(m, orig):
    pad, pila, edad, obj, est, ent = m.groups()
    return mensaje(ADVERTENCIA, 'Pila nueva fuera del perfil de rampa',
                   f'La pila {pila} (edad {edad} d) debía entregar {_n(float(obj), 1)} de PLS en la semana, pero el perfil de rampa '
                   f'solo permite {_n(float(ent), 1)}. La diferencia se reparte entre pilas en régimen o queda como balance pendiente.',
                   'Revisar el caudal de PLS de la pila nueva y el balance pendiente que se muestra aparte.',
                   orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+)/(P\d+): el Q PLS final semanal \(([\d.]+)\) queda por debajo del piso')
def _bajo_piso(m, orig):
    pad, pila, q = m.groups()
    return mensaje(ADVERTENCIA, 'PLS de la pila bajo el mínimo de la rampa',
                   f'El PLS de la semana de la pila {pila} ({_n(float(q), 1)}) queda bajo el mínimo de su curva de rampa; '
                   f'se conservó la forma de la curva y se reescaló.',
                   'Revisar la medición de PLS de la pila.', orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+)/(P\d+): sin riego reconciliado en la ventana')
def _sin_riego_vent(m, orig):
    pad, pila = m.groups()
    return mensaje(INFORMACION, 'Pila sin riego reconciliado en la ventana',
                   f'La pila {pila} no tiene riego reconciliado en la ventana; su PLS se repartió proporcional al riego final.',
                   None, orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+)/(P\d+) (\d{4}-\d{2}-\d{2}): sin peso ramp-up')
def _sin_peso(m, orig):
    pad, pila, fecha = m.groups()
    return mensaje(INFORMACION, 'Sin curva de rampa para el día',
                   f'La pila {pila} no tiene peso de rampa el {fecha}; el PLS del día se repartió parejo.', None, orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+)/(P\d+) (\d{4}-\d{2}-\d{2}): Q PLS final dia \(([\d.]+)\) >= Q riego final dia \(([\d.]+)\) -- recortado a ([\d.]+)')
def _pls_mayor_riego(m, orig):
    pad, pila, fecha, qp, qr, rec = m.groups()
    return mensaje(ADVERTENCIA, 'PLS diario igual o mayor que el riego',
                   f'El {fecha} la pila {pila} drenaba {_n(float(qp), 2)} contra {_n(float(qr), 2)} de riego; se recortó a {_n(float(rec), 2)} '
                   f'para no drenar más de lo que se riega.',
                   'Revisar las mediciones de riego y PLS de ese día.', orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+): el delta de Q (riego|PLS) \(([-\d.]+)\) no cabe en el pool transiente.*?quedan ([-\d.]+) sin repartir')
def _delta_no_cabe(m, orig):
    pad, que, d, resto = m.groups()
    return mensaje(ADVERTENCIA, f'Ajuste de caudal de {"riego" if que == "riego" else "PLS"} no se pudo repartir completo',
                   f'El ajuste de {_n(float(d), 2)} en el caudal de {"riego" if que == "riego" else "PLS"} no cabe entre las pilas nuevas '
                   f'sin dejar caudales negativos; quedan {_n(float(resto), 2)} sin repartir.',
                   'Revisar el balance del run oficial para ese pad.', orig, _pad(pad))


@_regla(r'^(\w+)/(P\d+): Cu (riego|PLS) reconciliado negativo \(([-\d.]+)\)')
def _cu_negativo(m, orig):
    pad, pila, que, v = m.groups()
    return mensaje(ERROR, f'Ley de Cu de {"riego" if que == "riego" else "PLS"} negativa',
                   f'La pila {pila} resultó con una ley de Cu de {"riego" if que == "riego" else "PLS"} de {_n(float(v), 4)} g/L, que no es posible; '
                   f'las pilas nuevas no tienen holgura para el ajuste de fino.',
                   'No usar la curva de esta pila; revisar los finos del run oficial.', orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+)/(P\d+): la pila queda con Q riego final 0')
def _riego_cero(m, orig):
    pad, pila = m.groups()
    return mensaje(ADVERTENCIA, 'Pila con riego final en cero',
                   f'La pila {pila} absorbió un ajuste de −100 % y queda sin caudal de riego.',
                   'Revisar el riego medido de la pila y el balance del run oficial.', orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+): el residuo de rampa \(([-\d.]+)\) no se pudo repartir')
def _residuo_sin_repartir(m, orig):
    pad, r = m.groups()
    return mensaje(ADVERTENCIA, 'Residuo de rampa sin pilas donde repartirlo',
                   f'El residuo de rampa de {_n(float(r), 2)} no se pudo repartir porque ninguna pila en régimen tiene holgura bajo el techo de drenaje. '
                   f'Queda como balance pendiente del pad (no se atribuye a ninguna pila).',
                   'Revisar el techo de drenaje y el caudal de PLS del pad.', orig, _pad(pad))


@_regla(r'^(\w+): residuo de rampa ([-\d.]+) m3/h-dia de (.+?) repartido entre (\d+) pila')
def _residuo_repartido(m, orig):
    pad, r, donantes, n = m.groups()
    return mensaje(INFORMACION, 'Residuo de rampa repartido',
                   f'El residuo de {_n(float(r), 2)} m³/h·día de {donantes} se repartió entre {n} pila(s) en régimen, según su holgura bajo el techo de drenaje.',
                   None, orig, _pad(pad))


@_regla(r'^(\w+): quedaron ([-\d.]+) m3/h-dia del residuo de rampa SIN colocar.*?holgura total del pad \(([-\d.]+)\)')
def _residuo_sin_colocar(m, orig):
    pad, q, h = m.groups()
    return mensaje(ADVERTENCIA, 'Parte del residuo de rampa quedó sin colocar',
                   f'Quedaron {_n(float(q), 2)} m³/h·día sin colocar: la holgura total del pad ({_n(float(h), 2)}) no alcanza. '
                   f'Se declara como balance pendiente con signo; no prueba inventario en el lecho.',
                   'Considerar el balance pendiente como diferencia por explicar, no como recuperación.', orig, _pad(pad))


@_regla(r'^(\w+): piso de rampa ([-\d.]+) m3/h-dia y ([-\d.]+) de fino de (.+?) compensado')
def _piso_comp(m, orig):
    pad, q, f, pilas = m.groups()
    return mensaje(INFORMACION, 'Piso de rampa compensado',
                   f'El mínimo de rampa de {pilas} ({_n(float(q), 2)} m³/h·día de caudal y {_n(float(f), 2)} de fino) se compensó entre pilas en régimen.',
                   None, orig, _pad(pad))


@_regla(r'^(\w+): capacidad insuficiente para compensar el piso de rampa; termino de balance pendiente Q=([-\d.]+), fino=([-\d.]+)')
def _piso_insuf(m, orig):
    pad, q, f = m.groups()
    return mensaje(ADVERTENCIA, 'Balance pendiente por mínimo de rampa',
                   f'No hubo capacidad para compensar el mínimo de rampa: quedan {_n(float(q), 4)} de caudal y {_n(float(f), 4)} de fino pendientes (con signo).',
                   'Tratarlo como diferencia de balance; no se suma a ninguna pila.', orig, _pad(pad))


@_regla(r'^(\w+)/(P\d+): sin dato de curva hasta (\d{4}-\d{2}-\d{2})')
def _sin_curva(m, orig):
    pad, pila, fecha = m.groups()
    return mensaje(ADVERTENCIA, 'Sin curva oficial para la pila',
                   f'No hay dato de curva de {pila} hasta el {fecha}; se usó el dato del WIP como respaldo.',
                   'Verificar la recuperación oficial de la pila.', orig, f'{_pad(pad)} / {pila}')


@_regla(r'^(\w+): (\d+) pila\(s\) EN REPOSO')
def _reposo(m, orig):
    pad, n = m.groups()
    return mensaje(INFORMACION, 'Pilas en reposo',
                   f'{n} pila(s) tienen campaña abierta pero no se regaron en toda la ventana; quedan fuera del cálculo (es lo esperado).',
                   None, orig, _pad(pad))


@_regla(r'^(\w+): (\d+) pila\(s\) sin riego en la ventana pero CON riego reciente')
def _reciente(m, orig):
    pad, n = m.groups()
    return mensaje(ADVERTENCIA, 'Pilas sin riego con riego reciente',
                   f'{n} pila(s) no se regaron en la ventana pero sí poco antes; quedan fuera del cálculo.',
                   'Confirmar si fue una parada real o una caída de medición.', orig, _pad(pad))


@_regla(r'^(\w+): (\d+) pila\(s\) arrancan en la ventana \(ramp-up\)')
def _arranque(m, orig):
    pad, n = m.groups()
    return mensaje(INFORMACION, 'Pilas nuevas en la ventana',
                   f'{n} pila(s) comienzan su riego dentro de la ventana y siguen la curva de rampa.', None, orig, _pad(pad))


@_regla(r'^(\w+): (\d+) pila\(s\) arrancan el ultimo dia de la ventana')
def _arranque_tarde(m, orig):
    pad, n = m.groups()
    return mensaje(INFORMACION, 'Pilas que arrancan el último día',
                   f'{n} pila(s) comienzan el último día de la ventana y quedan fuera; entran en la ventana siguiente.', None, orig, _pad(pad))


@_regla(r'^(\w+): al menos una pila NUEVA quedo infactible')
def _nueva_infactible(m, orig):
    pad = m.group(1)
    return mensaje(ADVERTENCIA, 'Pila nueva fuera de lo factible',
                   'El PLS que el run oficial asigna a al menos una pila nueva supera lo que permite su curva de rampa. '
                   'Se entregó el perfil diario factible y el resto se declaró como balance pendiente.',
                   'Revisar el balance del run oficial para ese pad.', orig, _pad(pad))


def traducir_aviso_motor(texto):
    """Mensaje para un aviso del motor; si no se reconoce, se conserva el texto original como advertencia."""
    t = str(texto).strip()
    for rx, fn in _MOTOR:
        m = rx.search(t)
        if m:
            return fn(m, t)
    return mensaje(ADVERTENCIA, 'Aviso del cálculo', t, None, t)


# ── reconcile_pad ─────────────────────────────────────────────────────────────

def mensajes_reconciliacion_pad(res, *, banda=None, banda_estricta=BANDA_ESTRICTA, umbral_factor=UMBRAL_FACTOR_NUEVA,
                                recuperaciones=None, umbral_brecha_t=UMBRAL_BRECHA_T_CU, tope_drenaje=None, ambito='Sulfuros', metodo=None):
    """Mensajes de un resultado de `reconcile_pad`.

    `banda`: banda relativa usada (si es mayor que `banda_estricta` se avisa como provisional).
    `recuperaciones`: {pila nueva: dict(metodo_pct, oficial_pct, cu_apilado_t)} para la brecha de cierre en t Cu."""
    out = []
    if res.get('status') != 'ok':
        causa = res.get('causa'); d = res.get('detalle') or {}
        det = f"causa={causa}: {res.get('motivo')}"
        if causa == 'masa_agua':
            out.append(mensaje(ERROR, 'El agua del pad no cierra',
                               f"Con el drenaje limitado a {_n(d.get('tope_drenaje_max'), 2)} veces el riego, el pad debería entregar al menos "
                               f"{_n(d.get('pls_minimo_exigido_m3'))} m³ de PLS y solo puede entregar {_n(d.get('pls_maximo_permitido_m3'))} m³. "
                               f"El objetivo del run es {_n(d.get('pls_global_objetivo_m3'))} m³ de PLS para {_n(d.get('riego_global_objetivo_m3'))} m³ de riego "
                               f"(razón {_n(d.get('drenaje_riego_global_objetivo'), 3)}).",
                               f"Revisar el balance de agua del run oficial; el tope de drenaje mínimo que permitiría cerrar es "
                               f"{_n(res.get('tope_comun_minimo_factible'), 3)} veces el riego.", det, ambito))
        elif causa == 'cobre':
            out.append(mensaje(ERROR, 'El cobre de las pilas maduras no cierra',
                               'Con la recuperación observada de las pilas maduras fija, las leyes de riego y de PLS del pad no pueden quedar dentro de la banda del run.',
                               'Revisar los finos de riego y de PLS del run oficial y las recuperaciones de las pilas maduras.', det, ambito))
        elif causa == 'neto_f29':
            g = res.get('desviacion_minima_neto_t')
            out.append(mensaje(ERROR, 'El cobre neto del pad no coincide con el flujo F29',
                               f"La menor diferencia posible entre el cobre neto del pad y F29 es {_n(g, 2)} t Cu"
                               + (f" ({_pct(res['desviacion_minima_neto_relativa'], 2)})" if res.get('desviacion_minima_neto_relativa') is not None else '') + '.',
                               'Revisar F29 (transferencia de Cu al pad) y los finos del run oficial.', det, ambito))
        elif causa == 'limites_movimiento':
            out.append(mensaje(ERROR, 'El ajuste exige mover los datos más de lo permitido',
                               'No existe solución que respete el límite de movimiento permitido de cada variable.',
                               'Revisar el run oficial o ampliar el límite de movimiento solo si hay respaldo.', det, ambito))
        elif causa == 'limites_fisicos':
            out.append(mensaje(ERROR, 'El cierre exige valores fuera del rango físico',
                               f"Para cerrar el balance habría que cambiar el caudal o la ley de alguna pila fuera del rango permitido "
                               f"(caudal {_n(d['q'][0], 2)} a {_n(d['q'][1], 2)} veces lo medido; ley {_n(d['conc'][0], 2)} a {_n(d['conc'][1], 2)} veces). "
                               f"Sin ese rango sí cierra, con valores poco creíbles." if d.get('q') and d.get('conc') else
                               'Para cerrar el balance habría que mover alguna pila fuera del rango físico permitido.',
                               'Revisar los flujos globales del run oficial; no ampliar el rango sin respaldo metalúrgico.', det, ambito))
        elif causa == 'solucion_no_fisica':
            probs = d.get('problemas') or []
            out.append(mensaje(ERROR, 'La solución calculada no es físicamente posible',
                               'El ajuste produjo valores inaceptables: ' + '; '.join(probs[:3]) + (f' (y {len(probs) - 3} más)' if len(probs) > 3 else '') + '.',
                               'No usar este resultado; revisar los flujos globales del run oficial.', det, ambito))
        elif causa == 'dias_cerrados_en_ventana':
            c = res.get('cierre') or {}
            n = len(c.get('dias_cerrados_en_ventana') or [])
            out.append(mensaje(ERROR, 'La ventana incluye días de un mes ya cerrado',
                               f"{n} día(s) con riego de la ventana son anteriores al cierre del {c.get('cierre_fecha')}; no se modifican días cerrados.",
                               'Calcular desde el primer día del mes del Caso o reabrir el cierre con la aprobación correspondiente.', det, ambito))
        else:
            out.append(mensaje(ERROR, 'No se pudo reconciliar el pad', res.get('motivo') or 'El ajuste no tiene solución.',
                               'Revisar los flujos globales del run oficial.', det, ambito))
        return out

    if banda is not None and banda > banda_estricta + 1e-12:
        out.append(mensaje(ADVERTENCIA, 'Banda de cierre provisional',
                           f'El pad se cierra contra los flujos globales con una banda de {_pct(banda, 2)} (referencia estricta {_pct(banda_estricta, 1)}). '
                           f'Los caudales y el cobre del pad pueden diferir hasta esa fracción del run.',
                           'Usar la banda estricta cuando el run del solver lo permita.', f'banda={banda}', ambito))
    piles = res.get('por_pila') or []
    mat = [p for p in piles if not p['young']]
    if metodo == 'reparto' and mat:                     # reparto por aporte: las maduras tambien se ajustan
        mx = max(mat, key=lambda p: abs(p['d_q_pls']) + abs(p['d_cu_pls']))
        out.append(mensaje(INFORMACION, 'Las pilas maduras también se ajustan',
                           f"Con el reparto por aporte ninguna pila queda fija: el mayor cambio de una pila madura es {mx['pile']} "
                           f"(caudal de PLS ×{_n(1 + mx['d_q_pls'], 2)}, ley de Cu del PLS ×{_n(1 + mx['d_cu_pls'], 2)} respecto de lo medido).",
                           'Para conservar la recuperación medida de las maduras use «Maduras fijas, nuevas absorben».', None, ambito))
    if tope_drenaje is None:                       # el tope realmente usado por el ajuste
        tope_drenaje = max((p.get('tope_drenaje', 1.0) for p in mat), default=1.0)
    en_tope = [p for p in mat if p['drenaje_riego'] >= tope_drenaje - 1e-6]
    if en_tope:
        out.append(mensaje(ADVERTENCIA, 'Pilas maduras en el tope de drenaje',
                           f'{len(en_tope)} de {len(mat)} pilas maduras drenan exactamente el tope de {_n(tope_drenaje, 2)} veces su riego '
                           f'({", ".join(p["pile"] for p in en_tope)}). El tope limita el ajuste: el caudal real de PLS de esas pilas puede ser distinto.',
                           'Confirmar con medición de PLS por pila o con el balance del run oficial.', f'en_tope={len(en_tope)}/{len(mat)}', ambito))
    for p in piles:
        if not p['young']:
            continue
        fq, fr, fp = 1 + p['d_q_pls'], 1 + p['d_cu_riego'], 1 + p['d_q_riego']
        fuertes = []
        if abs(fq - 1) > umbral_factor:
            fuertes.append(f'caudal de PLS ×{_n(fq, 2)}')
        if abs(fp - 1) > umbral_factor:
            fuertes.append(f'caudal de riego ×{_n(fp, 2)}')
        if abs(fr - 1) > umbral_factor:
            fuertes.append(f'ley de Cu del riego ×{_n(fr, 2)}')
        if abs(1 + p['d_cu_pls'] - 1) > umbral_factor:
            fuertes.append(f"ley de Cu del PLS ×{_n(1 + p['d_cu_pls'], 2)}")
        if fuertes:
            out.append(mensaje(ADVERTENCIA, 'Pila nueva con ajuste fuerte',
                               f"La pila nueva {p['pile']} se ajustó lejos de lo medido (más de ±{_pct(umbral_factor, 0)}): {', '.join(fuertes)}. "
                               f"La pila nueva absorbe lo que las maduras no explican, por lo que su cinética temprana podría estar mal representada.",
                               'Contrastar con la medición de la pila y con la recuperación oficial antes de usar su curva.',
                               f"d_q_pls={p['d_q_pls']:.3f}, d_cu_riego={p['d_cu_riego']:.3f}", f"{ambito} / {p['pile']}"))
    for pila, r in (recuperaciones or {}).items():
        if r.get('oficial_pct') is None:
            continue
        brecha = (r['oficial_pct'] - r['metodo_pct']) * r['cu_apilado_t'] / 100.0
        if abs(brecha) > umbral_brecha_t:
            sentido = 'sobre' if brecha > 0 else 'bajo'
            out.append(mensaje(ADVERTENCIA, 'Brecha de recuperación al cierre',
                               f"La recuperación de {pila} al cierre es {_n(r['metodo_pct'], 2)} % con el método y {_n(r['oficial_pct'], 2)} % oficial: "
                               f"la oficial está {sentido} el método por {_n(abs(brecha), 1)} t Cu ({_n(abs(r['oficial_pct'] - r['metodo_pct']), 2)} puntos).",
                               'Comparar contra una recuperación oficial calculada con el mismo run; si el run cambió, la brecha mide ese cambio.',
                               f'brecha_t_cu={brecha:.3f}', f'{ambito} / {pila}'))
    if not out:
        out.append(mensaje(INFORMACION, 'Pad reconciliado', 'El pad cierra dentro de la banda, sin pilas en el tope ni ajustes fuertes en pilas nuevas.', None, None, ambito))
    return out


# ── Run del solver ────────────────────────────────────────────────────────────

_ESTADOS_OK = ('validated',)


def mensajes_run_solver(meta, *, caso=None):
    """Mensajes del run del solver. `meta`: dict con `estado`, `closure_kind`, `fuera_tol` (n de ajustes fuera de tolerancia),
    `intentos` (lista), `motivo_reintento`, `mensaje`, `razones` ({pad: razon drenaje/riego}) y/o `max_res_kg_masa`.
    Solo se llama si el dato esta disponible; no consulta SQL."""
    out = []
    ambito = f'Caso {caso}' if caso else None
    estado = meta.get('estado')
    if estado is None:
        return out
    if estado not in _ESTADOS_OK:
        out.append(mensaje(ERROR, 'El run del solver no está validado',
                           f"El run oficial del Caso tiene estado «{estado}»: su cierre físico no está confirmado, por lo que las curvas no son confiables.",
                           'Volver a ejecutar el solver o seleccionar un run validado.', f'estado={estado}', ambito))
        return out
    kind = meta.get('closure_kind')
    if kind == 'rounding_absorbed':
        out.append(mensaje(INFORMACION, 'Cierre con residuo de redondeo',
                           f"El balance cierra dentro del redondeo de los datos; residuo máximo {_n(meta.get('max_res_kg_masa'), 3)} kg de masa.",
                           None, f'closure_kind={kind}', ambito))
    elif kind == 'precision_adjusted':
        out.append(mensaje(ADVERTENCIA, 'Cierre usando la precisión de los datos fijos',
                           'Para cerrar el balance se ajustaron flujos fijos dentro de medio decimal de su valor reportado.',
                           'Revisar el detalle de ajustes en el run si se necesita trazabilidad.', f'closure_kind={kind}', ambito))
    n = meta.get('fuera_tol')
    if n:
        out.append(mensaje(ADVERTENCIA, 'Ajustes fuera de tolerancia',
                           f'{n} flujo(s) se movieron más que su tolerancia declarada en el run.',
                           'Revisar esos flujos en el reporte del solver antes de oficializar.', f'fuera_tol={n}', ambito))
    ints = meta.get('intentos') or []
    if len(ints) > 1:
        out.append(mensaje(INFORMACION, 'El solver necesitó reintentos',
                           f"El solver resolvió el Caso en {len(ints)} intentos" + (f" ({meta.get('motivo_reintento')})." if meta.get('motivo_reintento') else '.'),
                           None, None, ambito))
    for pad, r in (meta.get('razones') or {}).items():
        if r is not None and r > 1.0 + 1e-6:
            out.append(mensaje(ADVERTENCIA, 'Drenaje sobre el riego en el run',
                               f'En {pad} el run entrega {_n(r, 3)} veces el riego como PLS, sobre el máximo físico de 1,0.',
                               'Revisar el balance de agua del pad.', f'razon={r}', f'{ambito or ""} {pad}'.strip()))
    return out


def mensajes_sin_nuevas(label, metodo_etiqueta, daily, anchor, ws, we, n_nuevas=0, banda=BANDA_ESTRICTA):
    """Aviso de un pad SIN pilas nuevas (30 dias o menos desde el primer riego) en la ventana.

    Sin nuevas el metodo elegido en el selector no aplica (Sulfuros) o nunca aplica (Oxidos, siempre motor general): el
    motor general reparte la diferencia frente al run entre todas las pilas. Para que el pad quede en lo medido se fija
    el pad (tolerancia 0) en el solver de flujos. Solo informa: no cambia el
    calculo. `daily`: filas diarias del resultado; `anchor`: ancla del Caso para el pad (caudal m3 y fino t Cu del run).
    Devuelve [] si el pad tiene nuevas. Sulfuros: advertencia; Oxidos: informacion."""
    import pandas as pd
    if n_nuevas:
        return []
    dias = {d.date() for d in pd.date_range(ws, we)}
    tot = dict(riego=0., pls=0., fino_riego=0., fino_pls=0.)
    for d in daily or []:
        if d.get('label') != label or pd.Timestamp(d['date']).date() not in dias:
            continue
        tot['riego'] += 24 * (d.get('q_riego_final') or 0)
        tot['pls'] += 24 * (d.get('q_pls_final') or 0)
        tot['fino_riego'] += .024 * (d.get('fino_riego_final') or 0)
        tot['fino_pls'] += .024 * (d.get('fino_pls_final') or 0)
    objetivo = dict(riego=(anchor or {}).get('q_riego_recon'), pls=(anchor or {}).get('q_pls_recon'),
                    fino_riego=(anchor or {}).get('fino_riego_recon'), fino_pls=(anchor or {}).get('fino_pls_recon'))
    nombres = dict(riego='riego', pls='PLS', fino_riego='fino del riego', fino_pls='fino del PLS')
    difs, dentro = [], True
    for k, nom in nombres.items():
        if objetivo[k]:
            r = tot[k] / objetivo[k] - 1
            difs.append(f'{nom} {"+" if r >= 0 else "-"}{_pct(abs(r), 2)}')
            dentro &= abs(r) <= banda
    pad = _pad(label)
    if label == 'SULFUROS':
        que = (f'El método «{metodo_etiqueta}» no aplica: solo actúa sobre pilas nuevas. El cálculo usó el motor general, que '
               f'reparte la diferencia frente al run entre todas las pilas activas (también las maduras) y cierra el Cu neto.')
        nivel, titulo = ADVERTENCIA, 'Sulfuros sin pilas nuevas: el método elegido no aplica'
    else:
        que = ('Óxidos usa siempre el motor general, sin método seleccionable: reparte la diferencia frente al run '
               'entre todas las pilas activas y cierra el Cu neto.')
        nivel, titulo = INFORMACION, 'Óxidos sin pilas nuevas'
    cierre = ('Cierre de riego, PLS y finos frente al run (banda de %s): ' % _pct(banda, 1)
              + (', '.join(difs) if difs else 'sin dato del run') + '.')
    if difs and dentro:
        cierre += ' Dentro de la banda.'
    elif difs:
        cierre += ' Fuera de la banda: la diferencia queda sin absorber en el cálculo.'
    texto = f'En {pad} no hay pilas nuevas (30 días o menos desde el primer riego) en la ventana. {que} {cierre}'
    accion = (f'Fijar el pad {pad} (tolerancia 0) en el solver de flujos para que el desbalance lo absorba el solver '
              f'y no el cálculo de curvas.')
    return [mensaje(nivel, titulo, texto, accion, 'sin_pilas_nuevas', pad)]


def ordenar(mensajes):
    """Errores primero, luego advertencias e informacion."""
    return sorted(mensajes, key=lambda m: NIVELES.index(m['nivel']))


def texto_panel(metodo):
    """Párrafos del panel «Cómo leer este panel» según el método de reconciliación seleccionado (lista de str)."""
    from . import reconciliacion_pad as RP
    from .metodo_maduras_fijas import METODO_MADURAS_FIJAS
    comunes = ('Los deltas de caudal y Cu fino son relativos al medido. Los agregados de Cu fino son proporcionales, no toneladas. '
               'En las barras de concentración, la media diaria es aritmética sobre los días con dato y no está ponderada por caudal. '
               '«Cálculo listo» confirma que hay datos y pilas para mostrar; revise los avisos y los gráficos para evaluar el resultado.')
    if metodo == METODO_MADURAS_FIJAS:
        return [
            'Método «Maduras fijas, nuevas absorben» (Sulfuros). Las pilas maduras (más de 30 días desde el primer riego) conservan lo medido '
            'en la ventana del Caso: su recuperación acumulada y su neto diario no cambian. Las pilas nuevas (30 días o menos) absorben el '
            'residuo para cerrar el cobre neto del pad (F29) y los flujos globales del run. Los días de meses anteriores al Caso están cerrados '
            'y no se modifican.',
            f'El pad cierra contra los flujos globales (riego, PLS y sus finos) con una banda de {_pct(RP.BAND_DEFAULT, 1)} (provisional). '
            f'Ninguna pila drena más de {_n(RP.MAX_DRAIN_RATIO_DEFAULT, 2)} veces su riego: es un supuesto, no una medición, y puede dejar '
            f'pilas maduras en ese tope; el aviso lo indica. El caudal y la ley de cada pila se limitan a un rango físico '
            f'(caudal entre {_n(RP.PHYS_Q_RANGE[0], 1)} y {_n(RP.PHYS_Q_RANGE[1], 1)} veces lo medido; ley de Cu hasta {_n(RP.PHYS_CONC_RANGE[1], 0)} veces).',
            f'Atención con las pilas nuevas: como absorben el residuo, un ajuste de caudal o de ley que se aparte más de ±{_pct(UMBRAL_FACTOR_NUEVA, 0)} '
            'de lo medido se avisa, porque su cinética temprana puede estar mal representada. El drenaje de las maduras es un proxy '
            '(0,95 veces el riego): cerrar el Cu neto no valida el balance de agua. Si el pad no cierra, el cálculo se detiene y explica la causa.',
            comunes]
    return [
        'Método «Reparto por aporte» (Sulfuros). Parte de los mismos objetivos absolutos del run (riego, PLS, finos y cobre neto F29) y de la '
        'misma base por pila que el otro método. El ajuste entre lo medido y esos objetivos se reparte entre TODAS las pilas activas en '
        'proporción a su aporte (caudal para el agua, fino para el cobre), con un factor común. Ninguna pila queda fija: las maduras '
        'también cambian respecto de lo medido. Una pila que alcanza un límite (tope de drenaje o rango físico) se queda en él y las demás '
        'absorben el resto en la misma proporción. El mes anterior al Caso no se modifica.',
        f'Cierra contra los flujos globales con una banda de {_pct(RP.BAND_DEFAULT, 1)} (provisional), con el mismo tope de drenaje de '
        f'{_n(RP.MAX_DRAIN_RATIO_DEFAULT, 2)} veces el riego y el mismo rango físico de caudal y ley que «Maduras fijas». El drenaje de las '
        'maduras es un proxy (0,95 veces el riego); cerrar el Cu neto no valida el balance de agua. Si el pad no cierra, el cálculo se '
        'detiene y explica la causa.',
        comunes]
