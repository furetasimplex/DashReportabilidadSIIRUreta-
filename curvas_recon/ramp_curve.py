# -*- coding: utf-8 -*-
"""Curva de ramp-up del factor de drenaje, para pilas EN ARRANQUE: las que
nacen en la ventana y las que ya nacieron pero siguen dentro de sus primeros
`DIAS_RAMPA` dias de ciclo. Modulo independiente: matematica pura, sin DB y
sin importar `recon_engine` (para poder testearlo solo).

La curva es SIEMPRE creciente. Ese es el punto de una pila nueva: el dia 1
drena poco y va subiendo mientras el lecho se satura. Una curva plana no es
un ramp-up, es el regimen -- y el regimen ya tiene su propio camino en el
motor (reparto proporcional al riego, `_solve_meseta` status 'regimen').

La curva se ajusta SEMANA A SEMANA pero esta anclada al dia de ciclo, no a la
ventana: la semana de arranque ve los dias 1-7 de la curva, la siguiente los
dias 8-14, y asi hasta el dia DIAS_RAMPA. El ajuste de cada semana mueve la
tension del dial, no el ancla, asi que la pila no "reinicia" su rampa cada
lunes ni salta a la meseta al cerrar su primera ventana.

    f(n) = M - (M - i0) * (1 - alpha)^(n-1)

      n     dia de ciclo de la pila, 1 = primer dia de riego real
      i0    factor del dia 1
      M     meseta: la ASINTOTA, no un valor que la curva alcance
      alpha velocidad de acercamiento a la meseta, en (0, 1)

Propiedades que el modulo garantiza y verifica (`validar`):

  * f(1) = i0 exacto.
  * f estrictamente creciente mientras M > i0 y alpha en (0,1).
  * f(n) < M para todo n finito: la curva NUNCA toca la meseta. Con
    M <= cap queda f(n) < cap estricto, o sea el techo de reconciliacion
    es una cota que no se alcanza, no un valor al que se aplasta la curva.


UN SOLO DIAL: la familia de un parametro
----------------------------------------
El ajuste NO despeja i0, M y alpha por separado ni en etapas. Los tres se
mueven JUNTOS a lo largo de un unico parametro continuo `t` en (0, 1], la
tension de la rampa:

    M(t)     = cap * t
    i0(t)    = frac * t * M(t)      = frac * cap * t^2
    alpha(t) = alpha_0 + (ALPHA_MAX - alpha_0) * t

`t` es lo unico que el solver toca. La lectura fisica es directa: a una pila a
la que el balance le pide poco PLS le queda una curva de meseta baja, arranque
casi nulo y subida lenta; a una que tiene que entregar mucho le queda un
arranque mas alto, una subida mas rapida y una meseta mas alta. En t = 1 la
rampa es la mas cargada que el metodo admite: meseta en el techo, arranque en
su tope fisico (frac * M) y la subida mas empinada (ALPHA_MAX).

El area semanal a lo largo del dial,

    S(t) = Sum_d q_d f(n_d; t)
         = cap * Sum_d q_d * t * [1 - (1 - frac*t) * (1-alpha(t))^(n_d - 1)]

es CONTINUA y ESTRICTAMENTE CRECIENTE en t, con S(0) = 0 y S(1) = AREA_MAX.
Derivando termino a termino, con b_d(t) = (1-alpha(t))^(n_d-1) <= 1:

    d/dt [ t - t(1 - frac*t) b_d ] = 1 - (1 - 2*frac*t) b_d
                                       - t(1 - frac*t) b_d'(t)   > 0

porque el primer parentesis nunca pasa de 1 y b_d' < 0 (alpha sube con t).
Biyeccion, entonces: para cada objetivo en (0, AREA_MAX] hay UN solo t y una
sola curva, y se encuentra con UNA llamada a `scipy.optimize.brentq` sobre
[0, 1] (biseccion de respaldo si no hay scipy). No hay etapas, no hay saltos
de status, no hay parametros que se topen mientras otro sigue libre: mover el
objetivo un 1 % mueve la curva un poco, no la cambia de regimen.

De ahi sale el limite duro del metodo:

    AREA_MAX = S(1) = Sum_d q_d [cap - (cap - frac*cap) (1-ALPHA_MAX)^(n_d-1)]

SIEMPRE menor que cap * Sum q_d, porque el dia 1 no puede pasar de una
fraccion de la meseta y la subida tiene velocidad tope. Si el Q PLS que paso
4 le pide a la pila supera AREA_MAX, NO existe curva creciente bajo el techo
que lo entregue. El ajuste correcto ahi no es aplastar la curva contra el
techo (eso publica un Fdrena de 0.99 el dia 1 de una pila recien regada, que
es fisicamente falso): es entregar la rampa de t = 1 y DEVOLVER EL RESIDUO
para que el motor lo redistribuya entre las pilas en regimen, que si pueden
drenarlo.

Por que i0 no es una constante: clavarlo en 0.1 era una suposicion, y una
cara -- el dia 1 suele pesar mucho del riego de la semana, asi que el area de
la curva es muy sensible a f(1). El dato medido tampoco sirve de referencia
para una pila nueva: `q_pls_medido` de esos dias viene fabricado como
FDRENA_MAX * riego, o sea 0.95 los 8 dias, que es justamente el supuesto que
la rampa existe para corregir. Lo unico que lo acota es fisica: una pila
recien armada no puede drenar una fraccion grande de su meseta el primer dia,
porque el lecho todavia esta absorbiendo. De ahi el techo del dial,
i0 <= INICIO_FRAC_MAX * M.

Status posibles, y son solo tres:
    'ok'         se encontro t en (0,1): la curva cierra exacto.
    'infactible' target > AREA_MAX: se entrega t = 1 y `residuo` > 0.
    'sin_riego'  no hay dias utiles o el target no es positivo.
"""

RAMP_INITIAL = 0.1          # f(1) de respaldo, solo sin dias utiles
# Techo fisico de f(1) como fraccion de la meseta: el primer dia de riego el
# lecho todavia esta absorbiendo y no drena ni la mitad de lo que drenara en
# regimen. Es lo que impide que la rampa mas cargada degenere en curva plana.
INICIO_FRAC_MAX = 0.5

# CUANTO DURA EL ARRANQUE. La saturacion del lecho no se cierra en una semana:
# la rampa no tiene por que llegar a la meseta dentro de la ventana en que la
# pila nace, y el motor la sigue aplicando mientras el dia de ciclo sea
# <= DIAS_RAMPA. Un mes es el plazo operativo: el exceso de PLS contra la hoja
# de la planta vive casi entero en los dias 1-60 de ciclo (94 % en oxidos,
# 98 % en sulfuros, ver `Detalle_Diferencias`), o sea mucho mas alla de la
# semana de arranque, y ahi el supuesto plano de 0.95 desde el dia 1 es lo que
# sobra.
DIAS_RAMPA = 30

# Los dos extremos del dial se derivan de DIAS_RAMPA en vez de ser numeros
# sueltos: alpha es la velocidad con que se cierra el hueco a la meseta, y
# "cerrar el 99 % del hueco al dia D" fija alpha = 1 - 0.01^(1/(D-1)).
#
#   ALPHA_MAX  extremo cargado del dial: 99 % del hueco al dia DIAS_RAMPA.
#   RAMP_ALPHA alpha_0, extremo flojo: el doble de plazo (99 % al dia 2*D).
#
# Antes eran 0.5 y 4/17, o sea 99 % al dia 8 y al dia 18: toda la rampa
# quedaba adentro de la semana de arranque y, desde el lunes siguiente, la
# pila entraba en regimen plano contra el techo. Eso es lo que fabricaba el
# exceso de los dias 8-60.
ALPHA_MAX = 1.0 - 0.01 ** (1.0 / (DIAS_RAMPA - 1))          # ~0.1468
RAMP_ALPHA = 1.0 - 0.01 ** (1.0 / (2 * DIAS_RAMPA - 1))     # ~0.0751
EPS = 1e-12


# ------------------------------------------------------------------ curva

def factores(dias_ciclo, meseta, initial=RAMP_INITIAL, alpha=RAMP_ALPHA):
    """f(n) para cada dia de ciclo. `None` o n < 1 -> 0.0 (la pila todavia
    no operaba ese dia)."""
    out = []
    for n in dias_ciclo:
        if n is None or n < 1:
            out.append(0.0)
        else:
            out.append(meseta - (meseta - initial) * (1.0 - alpha) ** (float(n) - 1.0))
    return out


def validar(fs, cap, tol=1e-9):
    """Verifica lo que el modulo promete. Devuelve lista de problemas (vacia
    si la curva esta bien). Se ignoran los dias con f = 0 (sin riego)."""
    malos = []
    act = [f for f in fs if f > 0.0]
    for i in range(1, len(act)):
        if act[i] < act[i - 1] - tol:
            malos.append('no creciente en el paso %d: %.6f -> %.6f'
                         % (i, act[i - 1], act[i]))
    for i, f in enumerate(act):
        if f > cap + tol:
            malos.append('dia %d sobre el techo: %.6f > %.6f' % (i + 1, f, cap))
    if len(act) > 1 and abs(act[-1] - act[0]) <= tol:
        malos.append('curva plana (%.6f en todos los dias): no es un ramp-up'
                     % act[0])
    elif len(act) > 2:
        # Escalon: el dia 2 ya llego a la meseta y el dia 1 quedo muy abajo.
        rango = act[-1] - act[0]
        if rango > tol and (act[1] - act[0]) / rango > 0.98:
            malos.append('escalon: el dia 2 ya cubre el %.1f %% del rango '
                         '(%.6f -> %.6f -> %.6f); no es un ramp-up'
                         % (100.0 * (act[1] - act[0]) / rango,
                            act[0], act[1], act[-1]))
    return malos


def _area(q, dc, meseta, initial, alpha):
    return sum(qi * fi for qi, fi in
               zip(q, factores(dc, meseta, initial, alpha)))


# ------------------------------------------------------ el dial (un solo t)

def parametros(t, cap, alpha_0=RAMP_ALPHA, frac=INICIO_FRAC_MAX):
    """(meseta, inicio, alpha) de la rampa en la posicion `t` del dial.

    Los tres suben juntos con t. En t = 1 queda la rampa mas cargada que el
    metodo admite; en t -> 0 la curva se apaga sin dejar de ser creciente
    (i0/M = frac*t -> 0, o sea arranca en casi nada y sube hacia su meseta).
    """
    t = min(max(float(t), 0.0), 1.0)
    meseta = cap * t
    return meseta, frac * t * meseta, alpha_0 + (ALPHA_MAX - alpha_0) * t


def area(q, dc, t, cap, alpha_0=RAMP_ALPHA, frac=INICIO_FRAC_MAX):
    """S(t): Q PLS semanal que entrega la rampa en la posicion `t`. Continua y
    estrictamente creciente en t (ver cabecera del modulo)."""
    m, i0, al = parametros(t, cap, alpha_0, frac)
    return _area(q, dc, m, i0, al)


def inicio_maximo(cap, frac=INICIO_FRAC_MAX):
    """f(1) mas alto admisible: el arranque en el extremo t = 1 del dial."""
    return frac * cap


def area_maxima(q, dc, cap, frac=INICIO_FRAC_MAX, alpha_max=ALPHA_MAX):
    """S(1): area bajo la rampa mas cargada -- meseta en el techo, arranque en
    su tope fisico y la subida mas empinada que el modelo acepta. Es el Q PLS
    semanal mas grande que una pila nueva puede drenar sin romper la
    monotonia, el techo, ni la forma."""
    return _area(q, dc, cap, inicio_maximo(cap, frac), alpha_max)


# ------------------------------------------ continuacion entre semanas

# La reconciliacion es SEMANAL: cada ventana se resuelve sola. Una rampa que
# dura un mes cruza cuatro ventanas, asi que la semana n+1 no puede volver a
# arrancar del dia 1 ni saltar a la meseta -- tiene que PARTIR DEL ESTADO EN
# QUE LA PILA LLEGO al cerrar la semana n, y de ahi seguir subiendo hacia el
# techo. Eso es lo que hace el modo continuacion:
#
#     f(n) = M - (M - f0) * (1 - alpha)^(n - n0)
#
# con (n0, f0) el ultimo dia regado de la ventana anterior y su factor. En
# n = n0 vale f0 exacto: la curva empalma sin escalon.
#
# Diferencia con el modo arranque: aca alpha NO va en el dial. Se hereda el
# alpha que la pila despejo en su semana de arranque -- es la velocidad de
# saturacion de ESE lecho, no un parametro libre que se re-despeja cada lunes.
# Ademas el dial solo mueve la meseta, y asi
#
#     S(t) = Sum_d q_d [cap*t*(1 - r^k_d) + f0*r^k_d],  r = 1-alpha, k_d = n_d-n0
#
# es AFIN y estrictamente creciente en t: raiz unica igual que en el arranque,
# sin la derivada cruzada que aparecia al mover alpha y meseta juntos.


def factores_desde(dias_ciclo, meseta, f0, n0, alpha):
    """f(n) anclado en (n0, f0). `None` o n < 1 -> 0.0."""
    out = []
    for n in dias_ciclo:
        if n is None or n < 1:
            out.append(0.0)
        else:
            k = float(n) - float(n0)
            out.append(meseta - (meseta - f0) * (1.0 - alpha) ** k)
    return out


def area_desde(q, dc, t, cap, f0, n0, alpha):
    """S(t) en modo continuacion. Afin y creciente en t."""
    return sum(qi * fi for qi, fi in
               zip(q, factores_desde(dc, cap * min(max(t, 0.0), 1.0), f0, n0, alpha)))


def tension_minima(f0, cap):
    """Extremo bajo del dial de continuacion: la meseta no puede quedar por
    DEBAJO del estado con que la pila llego, o la curva bajaria. El piso es la
    curva PLANA en f0 -- la pila se queda donde llego -- y de ahi para arriba."""
    return min(max(float(f0) / float(cap), 0.0), 1.0)


def limites_desde(q, dc, cap, f0, n0, alpha):
    """(S(t_min), S(1)) del dial de continuacion.

    S(t_min) es la curva PLANA en f0: el piso de lo que la pila puede
    entregar sin des-saturarse, o sea quedarse en el estado en que llego.
    S(1) es la rampa que sigue subiendo desde f0 hacia el techo.
    """
    return (area_desde(q, dc, tension_minima(f0, cap), cap, f0, n0, alpha),
            area_desde(q, dc, 1.0, cap, f0, n0, alpha))


# ------------------------------------------------------------------ ajuste

def _brentq(f, lo, hi):
    try:
        from scipy.optimize import brentq
        return brentq(f, lo, hi, xtol=1e-14, rtol=8.9e-16, maxiter=200)
    except Exception:
        # Respaldo sin scipy: biseccion; f es monotona por construccion.
        f_lo = f(lo)
        for _ in range(300):
            mid = 0.5 * (lo + hi)
            if (f(mid) < 0) == (f_lo < 0):
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)


def ajustar(q_riego, dias_ciclo, target, cap,
            alpha=RAMP_ALPHA, frac=INICIO_FRAC_MAX, f0=None, n0=None):
    """Rampa acotada por `cap` que entrega `target` de Q PLS en la ventana.
    Un solo parametro, una sola llamada al solver.

    Dos modos, segun venga o no el estado de la ventana anterior:

      ARRANQUE (`f0` None) -- la pila nace en esta ventana. La curva arranca
      en el dia 1 de ciclo y el dial mueve meseta, arranque y alpha juntos.

      CONTINUACION (`f0`, `n0`) -- la pila ya venia rampando: la curva empalma
      exacto en (n0, f0), el alpha es el heredado y el dial solo mueve la
      meseta. Es lo que hace que una rampa de `DIAS_RAMPA` dias sobreviva a
      una reconciliacion semanal sin reiniciarse ni saltar al techo.

    `q_riego`     caudal de riego YA reconciliado por dia (paso 7a).
    `dias_ciclo`  dia de ciclo de cada dia; None/<1 para los previos al
                  arranque de la pila.
    `target`      Q PLS semanal de la pila (paso 4/6).
    `cap`         techo del factor de drenaje reconciliado (FDRENA_RECON_MAX).
    `alpha`       alpha_0 (arranque) o el alpha heredado (continuacion).
    `frac`        techo de f(1) como fraccion de la meseta (extremo t = 1).
    `f0`, `n0`    factor y dia de ciclo del ultimo dia regado de la ventana
                  anterior. Los dos o ninguno.

    Devuelve dict con:
        factores  f(n) por dia, alineado a las entradas
        tension   el t despejado, en [0, 1]
        inicio    f del primer dia util (i0 en arranque, empalme en continuacion)
        meseta    M(t) (asintota; la curva no la alcanza)
        alpha     alpha(t) en arranque, el heredado en continuacion
        modo      'arranque' | 'continuacion'
        status    'ok' | 'infactible' | 'piso' | 'sin_riego'
        entregado area efectiva = Sum q_d f_d
        residuo   target - entregado. > 0 con 'infactible' (el motor lo
                  redistribuye, no se absorbe en la curva); < 0 con 'piso'.
        area_max  S(1), maximo alcanzable con esta pila y este cap
        area_min  S(t_min). 0 en arranque; en continuacion es la curva PLANA
                  en f0: el piso que impone el estado heredado, porque la pila
                  no se des-satura (`status` 'piso' si el target pide menos).
        f_fin     f del ultimo dia regado de la ventana -- el estado con que
                  la pila llega a la semana siguiente.
        n_fin     dia de ciclo de ese ultimo dia regado.
    """
    idx = [i for i, (qi, n) in enumerate(zip(q_riego, dias_ciclo))
           if qi > 0 and n is not None and n >= 1]
    n_dias = len(q_riego)
    cont = f0 is not None and n0 is not None
    modo = 'continuacion' if cont else 'arranque'
    if not idx or target is None or target <= 0:
        return dict(factores=[0.0] * n_dias, tension=0.0, inicio=0.0, meseta=0.0,
                    alpha=alpha, modo=modo, status='sin_riego', entregado=0.0,
                    residuo=float(target or 0.0), area_max=0.0, area_min=0.0,
                    f_fin=(float(f0) if cont else 0.0),
                    n_fin=(float(n0) if cont else None))

    q = [q_riego[i] for i in idx]
    dc = [float(dias_ciclo[i]) for i in idx]
    if cont:
        a_min, a_max = limites_desde(q, dc, cap, f0, n0, alpha)
    else:
        a_min, a_max = 0.0, area_maxima(q, dc, cap, frac)

    def _salida(t, status, residuo=0.0):
        if cont:
            m, i0, al = cap * t, float(f0), alpha
            fs = factores_desde(dc, m, i0, n0, al)
        else:
            m, i0, al = parametros(t, cap, alpha, frac)
            fs = factores(dc, m, i0, al)
        out = [0.0] * n_dias
        for k, i in enumerate(idx):
            out[i] = fs[k]
        return dict(factores=out, tension=t, inicio=fs[0], meseta=m, alpha=al,
                    modo=modo, status=status,
                    entregado=sum(qi * f for qi, f in zip(q, fs)),
                    residuo=residuo, area_max=a_max, area_min=a_min,
                    f_fin=fs[-1], n_fin=dc[-1])

    # Fuera del alcance del dial: se entrega la rampa mas cargada y el resto
    # vuelve al motor. No se aplasta la curva contra el techo.
    if target >= a_max * (1 - 1e-12):
        r = _salida(1.0, 'infactible')
        r['residuo'] = max(target - r['entregado'], 0.0)
        return r

    # Piso del modo continuacion: el target pide menos que la curva plana en
    # f0. Bajar de ahi seria des-saturar el lecho de un dia para otro, asi que
    # se entrega el piso y el sobrante sale como residuo NEGATIVO, declarado y
    # no escondido dentro de la curva.
    if cont and target <= a_min * (1 + 1e-12):
        r = _salida(tension_minima(f0, cap), 'piso')
        r['residuo'] = target - r['entregado']
        return r

    # S es continua y estrictamente creciente en [0,1], con S(0) < target
    # < S(1): raiz unica, una sola llamada al solver.
    if cont:
        t = _brentq(lambda x: area_desde(q, dc, x, cap, f0, n0, alpha) - target,
                    tension_minima(f0, cap), 1.0)
    else:
        t = _brentq(lambda x: area(q, dc, x, cap, alpha, frac) - target, 0.0, 1.0)
    return _salida(t, 'ok')


# ------------------------------------------------------------------ demo

if __name__ == '__main__':
    # Las dos pilas nuevas de los Casos 21 y 23, con su riego reconciliado.
    CAP = 0.99
    CASOS = {
        'caso 21 / P23': dict(target=1319.4635, q=[
            122.742, 132.965, 150.335, 151.287, 145.578, 145.578, 285.446, 198.861]),
        'caso 23 / P24': dict(target=1041.3934, q=[
            116.908, 91.766, 92.647, 82.981, 123.041, 170.632, 196.116, 177.822]),
    }
    for nom, d in CASOS.items():
        q = d['q']
        dc = list(range(1, len(q) + 1))
        r = ajustar(q, dc, d['target'], CAP)
        print('=== %s   target=%.4f  area_max=%.4f  cap*Sq=%.4f'
              % (nom, d['target'], r['area_max'], CAP * sum(q)))
        print('    status=%s  t=%.6f  f(1)=%.4f  meseta=%.4f  alpha=%.6f' %
              (r['status'], r['tension'], r['inicio'], r['meseta'], r['alpha']))
        print('    %-4s %10s %8s %10s' % ('dia', 'q_riego', 'f(n)', 'q_pls'))
        for n, qi, f in zip(dc, q, r['factores']):
            print('    %-4d %10.3f %8.4f %10.3f' % (n, qi, f, qi * f))
        print('    entregado=%.4f  residuo=%.4f  (%.2f %% del target)'
              % (r['entregado'], r['residuo'],
                 100.0 * r['residuo'] / d['target']))
        malos = validar(r['factores'], CAP)
        print('    validacion: %s' % ('OK' if not malos else '; '.join(malos)))
        print('')

    # Continuidad del dial: el area recorre (0, AREA_MAX] sin saltos.
    q = CASOS['caso 23 / P24']['q']
    dc = list(range(1, len(q) + 1))
    a_max = area_maxima(q, dc, CAP)
    print('=== barrido del dial (caso 23 / P24), area_max=%.4f' % a_max)
    print('    %6s %8s %8s %8s %12s' % ('t', 'i0', 'meseta', 'alpha', 'S(t)'))
    prev = -1.0
    for k in range(0, 11):
        t = k / 10.0
        m, i0, al = parametros(t, CAP)
        s = area(q, dc, t, CAP)
        assert s > prev - 1e-15, 'S(t) no es creciente en t=%.2f' % t
        prev = s
        print('    %6.2f %8.4f %8.4f %8.4f %12.4f' % (t, i0, m, al, s))
    # Ida y vuelta: el t despejado reproduce el objetivo.
    for frac_obj in (0.05, 0.25, 0.5, 0.75, 0.99):
        tgt = frac_obj * a_max
        r = ajustar(q, dc, tgt, CAP)
        assert abs(r['entregado'] - tgt) < 1e-9, r
        assert not validar(r['factores'], CAP), r
    print('    ida y vuelta en 5 objetivos: OK')


def ajustar_regimen_suave(q_riego, dias_ciclo, target, cap, f0, n0,
                         alpha=RAMP_ALPHA, max_paso_diario=0.03):
    """Continuation into steady operation, allowing a gradual rise or fall.

    f(n)=M+(f0-M)*(1-alpha)^(n-n0). Solve M against weekly volume under
    0<=M<=cap, limiting every calendar-day change to max_paso_diario.
    Infeasible targets return an explicit signed target-minus-delivered
    residual; daily factors are never rescaled after fitting.
    """
    if len(q_riego) != len(dias_ciclo) or not 0 <= f0 <= cap:
        raise ValueError('Invalid smooth continuation inputs')
    if not 0 < alpha < 1 or max_paso_diario <= 0:
        raise ValueError('Invalid smooth continuation rate')
    idx=[i for i,(q,n) in enumerate(zip(q_riego,dias_ciclo))
         if q>0 and n is not None and n>=1]
    if any(float(dias_ciclo[i]) < n0 for i in idx):
        raise ValueError('Continuation cannot precede inherited state')
    alpha=min(alpha,max_paso_diario/max(f0,cap-f0,EPS))
    A=B=0.0
    for i in idx:
        r=(1-alpha)**(float(dias_ciclo[i])-n0)
        A+=q_riego[i]*(1-r)
        B+=q_riego[i]*f0*r
    minimum=B
    maximum=B+A*cap
    requested=float(target or 0.)
    level=min(max((requested-B)/A,0.),cap) if A>EPS else f0
    fs=factores_desde(dias_ciclo,level,f0,n0,alpha)
    out=[fs[i] if i in idx else 0. for i in range(len(fs))]
    delivered=sum(q*f for q,f in zip(q_riego,out))
    status=('sin_riego' if not idx else 'piso' if requested<minimum-EPS
            else 'infactible' if requested>maximum+EPS else 'ok')
    return dict(factores=out,tension=level/cap,inicio=out[idx[0]] if idx else 0.,
                meseta=level,alpha=alpha,modo='transicion_regimen',status=status,
                entregado=delivered,residuo=requested-delivered,
                area_max=maximum,area_min=minimum,
                f_fin=out[idx[-1]] if idx else f0,
                n_fin=float(dias_ciclo[idx[-1]]) if idx else None)
