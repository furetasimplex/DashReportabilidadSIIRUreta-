"""Validacion de entrada y marcado de dato invalido / medicion ruidosa.

Tres niveles, y la diferencia entre ellos importa:

  error   El contrato esta roto y seguir produce basura o una excepcion lejos
          del origen (falta una columna, la fecha viene repetida). Se levanta
          ValueError en el punto de carga.
  dato    El dato existe pero no puede ser cierto (densidad de 0.245 t/m3,
          frontera de turno de 1.7, humedad negativa). No se corrige ni se
          borra: se marca, se cuenta y se deja fuera de lo que proyecta.
  info    El dato es valido pero limitado, y el numero que sale de el hay que
          leerlo sabiendolo (semana cortada por el borde de la ventana, dia sin
          horometro de torre, modulo sin cobertura de horas).

Antes esto estaba disperso: cada funcion del motor ponia su propio .where() sin
nombre y sin dejar rastro de cuantas filas habia descartado, y las condiciones
imposibles —densidad fuera de rango fisico, frontera fuera de [0,1], turnos que
no cuadran con el dia— no se miraban en ninguna parte. El resultado se veia
igual de limpio con dato bueno que con dato roto.

Los umbrales viven en umbrales.py; aqui solo se aplican.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import umbrales as u

NIVELES = ("error", "dato", "info")


@dataclass(frozen=True)
class Aviso:
    nivel: str      # 'error' | 'dato' | 'info'
    codigo: str     # identificador estable, apto para contar entre corridas
    detalle: str    # frase legible, con las cifras dentro
    n: int = 0      # filas afectadas

    def __str__(self):
        n = f" [{self.n}]" if self.n else ""
        return f"{self.nivel:5s} {self.codigo}{n}: {self.detalle}"


# ─────────────────────────── medidas de ruido ───────────────────────────

def cv(s):
    """Coeficiente de variacion de una serie, en fraccion. NaN si no se puede
    medir. Es la medida de ruido que usa todo el proyecto — el motor, el
    dashboard y los tres reportes la calculaban a mano cada uno por su lado."""
    s = pd.Series(s).replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 2:
        return float("nan")
    m = float(s.mean())
    return float(s.std() / m) if m else float("nan")


def es_ruidosa(s, umbral=u.CV_MAX_CONFIABLE):
    """True si el promedio de la serie no significa nada a esa resolucion."""
    c = cv(s)
    return bool(c == c and c > umbral)


def en_banda(s, lo, hi):
    """Mascara de valores dentro de [lo, hi]. NaN queda fuera."""
    s = pd.Series(s)
    return s.between(lo, hi) & s.notna()


def rho_plausible(s):
    """Densidad que puede ser cierta, t/m3. Ver umbrales.RHO_MIN/RHO_MAX."""
    return en_banda(s, u.RHO_MIN, u.RHO_MAX)


# ─────────────────── coherencia entre fuentes ───────────────────
# Todo lo de arriba mira un valor y pregunta si puede ser cierto. Lo de aqui
# mira dos registros que tienen que contarse la misma historia. Es la unica
# forma de ver el dato que es plausible por si solo y falso en contexto: un dia
# corrido, un metro cubico anotado en el modulo vecino, un horometro inventado.
#
# Las tres devuelven filas, no cuentas. Los validadores de mas abajo las usan
# para emitir un Aviso; reporte_anomalias.py las usa para listar los casos.

CLAVE_MODULO = ("pad_id", "campana", "modulo")


def acum_descuadrado(ap):
    """Cierra el acumulado de cada modulo contra sus propios dias.

    vol_acum_final[t] tiene que ser vol_acum_final[t-1] + vol_diario[t]. Cuando
    no cierra, el volumen del modulo y el de sus dias son dos cifras distintas,
    y como la masa se reparte POR volumen, la diferencia se fue —o llego— desde
    otro modulo. Es la unica prueba dura de mala atribucion: no depende de
    ninguna estadistica, solo de que la planilla se sume a si misma.

    Devuelve ap con cuatro columnas nuevas. 'acum_primera' marca la primera fila
    de cada modulo dentro de la ventana: ahi el acumulado arranca cargado desde
    antes y NO es un error, por eso queda fuera de 'acum_ok'.
    """
    cols = set(CLAVE_MODULO) | {"fecha", "vol_diario", "vol_acum_final"}
    d = ap.copy()
    if not len(d) or not cols <= set(d.columns):
        for c in ("acum_prev", "acum_err", "acum_rel"):
            d[c] = np.nan
        d["acum_primera"] = False
        d["acum_ok"] = True
        return d

    d = d.sort_values([*CLAVE_MODULO, "fecha"])
    d["acum_prev"] = d.groupby(list(CLAVE_MODULO), sort=False)[
        "vol_acum_final"].shift(1)
    d["acum_primera"] = d["acum_prev"].isna()
    d["acum_err"] = d["vol_acum_final"] - (d["acum_prev"].fillna(0.0)
                                           + d["vol_diario"])
    d["acum_rel"] = d["acum_err"].abs() / d["vol_acum_final"].replace(0, np.nan)
    d["acum_ok"] = ~(d["acum_rel"] > u.TOL_ACUM) | d["acum_primera"]
    return d




def pares_corridos(daily, umbral=u.DESVIO_SEM_MAX, dias_min=u.DIAS_SEM_MIN):
    """Semanas contiguas que se contradicen y se arreglan moviendo UN dia.

    Deja una firma de balancin: la semana que perdio el dia baja de densidad y
    la que lo recibio sube, en la misma proporcion y en sentidos opuestos.

    Dos pasos, y el segundo es el que vale:
      1. candidato — dos semanas contiguas se apartan de la mediana mas de
         'umbral' en sentidos contrarios. Solo selecciona, no concluye.
      2. reparacion — se pasa la masa del dia del borde al otro lado y se
         vuelve a medir. Si las dos semanas entran en banda, la hipotesis queda
         confirmada; y como se prueban las dos direcciones, tambien queda
         falsificada cuando ninguna repara. Medido: 2 pares en la ventana, cada
         uno repara en una sola direccion y empeora en la otra.

    OJO con la lectura. Esta prueba NO es el unico detector, y su nombre promete
    mas de lo que demuestra. El levantamiento es diario, asi que un dia con masa
    y volumen desalineados suele verse solo, en su propia densidad diaria — de
    hecho los dos pares medidos caen junto a filas que ya estan fuera de banda:

        2025-08-17  vol 2.0 m3 contra 57497 t  ->  rho 28748  (fila centinela)
        2026-03-17  rho 1.335, con 2026-03-19 en 3.142

    En el caso de 2025-08-17 lo que falta es el LEVANTAMIENTO, no la fecha de la
    masa: la masa esta en su dia correcto y el volumen no existe. Mover la masa
    sobre el borde repara la aritmetica de las dos semanas igual, porque es la
    misma cuenta, pero el defecto de origen es otro. Lo que la prueba establece
    es 'este par se cuadra moviendo este dia', no 'este dia estaba misfechado'.

    Devuelve una fila por par candidato, con la reparacion ya evaluada.
    """
    cols = {"fecha", "semana", "masa_total", "vol_dia_total"}
    vacio = pd.DataFrame(columns=[
        "semana_a", "semana_b", "rho_a", "rho_b", "dev_a", "dev_b", "dia",
        "masa_dia", "sentido", "dev_a_rep", "dev_b_rep", "repara"])
    if daily is None or not len(daily) or not cols <= set(daily.columns):
        return vacio

    d = daily.dropna(subset=["semana", "masa_total", "vol_dia_total"])
    w = d.groupby("semana").agg(masa=("masa_total", "sum"),
                                vol=("vol_dia_total", "sum"),
                                dias=("fecha", "size"))
    w = w[(w["dias"] >= dias_min) & (w["vol"] > 0)]
    if len(w) < 2:
        return vacio
    w["rho"] = w["masa"] / w["vol"]
    med = float(w["rho"].median())
    if not med:
        return vacio
    w = w.reset_index().sort_values("semana").reset_index(drop=True)

    ciclo = pd.Timedelta(days=len(u.DIAS))
    filas = []
    for i in range(len(w) - 1):
        a, b = w.iloc[i], w.iloc[i + 1]
        if b["semana"] - a["semana"] != ciclo:
            continue        # hueco entre semanas: no hay borde que cruzar
        dev_a, dev_b = a["rho"] / med - 1, b["rho"] / med - 1
        if np.sign(dev_a) == np.sign(dev_b):
            continue        # las dos se van al mismo lado: no es un traspaso
        if min(abs(dev_a), abs(dev_b)) <= umbral:
            continue

        # el dia del borde puede haberse corrido en cualquiera de los dos
        # sentidos; se prueban ambos y gana el que deje las dos semanas en banda
        borde = (("adelante", d.loc[d["semana"] == a["semana"], "fecha"].max()),
                 ("atras", d.loc[d["semana"] == b["semana"], "fecha"].min()))
        mejor = None
        for sentido, dia in borde:
            t = float(d.loc[d["fecha"] == dia, "masa_total"].sum())
            signo = 1 if sentido == "adelante" else -1
            ra = (a["masa"] - signo * t) / a["vol"]
            rb = (b["masa"] + signo * t) / b["vol"]
            ok = abs(ra / med - 1) <= umbral and abs(rb / med - 1) <= umbral
            cand = dict(dia=dia, masa_dia=t, sentido=sentido,
                        dev_a_rep=ra / med - 1, dev_b_rep=rb / med - 1,
                        repara=ok)
            if ok or mejor is None:
                mejor = cand
            if ok:
                break
        filas.append(dict(semana_a=a["semana"], semana_b=b["semana"],
                          rho_a=a["rho"], rho_b=b["rho"],
                          dev_a=dev_a, dev_b=dev_b, **mejor))
    return pd.DataFrame(filas, columns=vacio.columns) if filas else vacio


# ─────────────────────────── utilidades ───────────────────────────

def _falta(df, cols):
    return [c for c in cols if c not in df.columns]


def _n_fuera(s, lo, hi):
    s = pd.Series(s).replace([np.inf, -np.inf], np.nan).dropna()
    return int((~s.between(lo, hi)).sum())


def exigir(avisos, origen=""):
    """Levanta si algun aviso es de nivel 'error'. Devuelve los avisos que no
    lo son, para que el llamador los adjunte al resultado."""
    duros = [a for a in avisos if a.nivel == "error"]
    if duros:
        cab = f"{origen}: " if origen else ""
        raise ValueError(cab + "datos invalidos\n  " +
                         "\n  ".join(str(a) for a in duros))
    return [a for a in avisos if a.nivel != "error"]


def resumen(avisos, nivel=None):
    """Texto de una linea por aviso, para log o para el pie de un reporte."""
    sel = [a for a in avisos if nivel is None or a.nivel == nivel]
    if not sel:
        return "sin observaciones"
    orden = {n: i for i, n in enumerate(NIVELES)}
    return "\n".join(str(a) for a in
                     sorted(sel, key=lambda a: (orden.get(a.nivel, 9), a.codigo)))


# ─────────────────────────── validadores de entrada ───────────────────────────

COLS_APILADO = ("fecha", "pad_id", "campana", "modulo", "vol_diario", "avance")
COLS_MASA = ("fecha", "TMH", "TMS", "H_op")

AVANCE_MAX = u.AVANCE_MAX   # re-exportado: vivia aqui, su casa es umbrales.py


def revisar_apilado(ap):
    """Volumen diario por modulo. Contrato de engine.mark_status en adelante."""
    a = []
    falta = _falta(ap, COLS_APILADO)
    if falta:
        return [Aviso("error", "apilado_columnas",
                      f"faltan columnas {falta}", len(falta))]
    if not len(ap):
        return [Aviso("dato", "apilado_vacio", "no hay filas de volumen")]

    n = int(ap["fecha"].isna().sum())
    if n:
        a.append(Aviso("error", "apilado_fecha_nula", "filas sin fecha", n))

    # No es 'error': el motor sobrevive a esto y los agregados por modulo salen
    # bien igual (module_summary suma por clave). Lo que se rompe es el orden
    # del dia — el modulo repetido ocupa dos tramos del reparto en vez de uno —
    # y el conteo de filas INACTIVO. Medido: 3 casos el 2026-02-06, dos de ellos
    # filas identicas con vol_diario = 0, que ni siquiera llegan a split_day.
    clave = ["fecha", "pad_id", "campana", "modulo"]
    n = int(ap.duplicated(clave).sum())
    if n:
        a.append(Aviso("dato", "apilado_duplicado",
                       f"la clave {clave} se repite: el modulo entra dos veces "
                       "al orden del dia", n))

    n = int((ap["vol_diario"] < 0).sum())
    if n:
        a.append(Aviso("dato", "vol_negativo",
                       "volumen diario negativo; no se reparte masa contra el", n))

    n = _n_fuera(ap["avance"], 0.0, AVANCE_MAX)
    if n:
        a.append(Aviso("dato", "avance_fuera_rango",
                       f"avance fuera de [0, {AVANCE_MAX}]", n))

    # El acumulado del modulo contra la suma de sus dias. Un descuadre aqui es
    # volumen que entro o salio sin que ningun dia lo declare: la masa se
    # reparte por volumen, asi que ese metro cubico se lo llevo —o se lo quito—
    # otro modulo. Ver acum_descuadrado.
    d = acum_descuadrado(ap)
    mal = d.loc[~d["acum_ok"]]
    if len(mal):
        falta = mal.loc[mal["acum_err"] < 0]
        sobra = mal.loc[mal["acum_err"] > 0]
        a.append(Aviso("dato", "acum_no_cuadra",
                       f"vol_acum_final no cierra contra vol_diario "
                       f"({len(falta)} pierden volumen, {len(sobra)} lo ganan; "
                       f"peor caso {mal['acum_err'].abs().max():,.0f} m3)",
                       len(mal)))
    return a


def revisar_masa(m):
    """Masa por dia y por turno. Contrato de engine.shift_table."""
    a = []
    falta = _falta(m, COLS_MASA)
    if falta:
        return [Aviso("error", "masa_columnas",
                      f"faltan columnas {falta}", len(falta))]
    if not len(m):
        return [Aviso("error", "masa_vacia", "no hay filas de masa")]

    n = int(m["fecha"].isna().sum())
    if n:
        a.append(Aviso("error", "masa_fecha_nula", "filas sin fecha", n))

    # shift_table hace masa.set_index('fecha') y despues .get(fecha) esperando
    # un escalar: con la fecha repetida devuelve una Serie y el float() revienta
    # a quince frames de distancia del origen.
    n = int(m["fecha"].duplicated().sum())
    if n:
        a.append(Aviso("error", "masa_fecha_duplicada",
                       "'fecha' tiene que ser unica: es el indice del reparto", n))

    for c in ("TMH", "TMS"):
        n = int((m[c] < 0).sum())
        if n:
            a.append(Aviso("dato", f"{c.lower()}_negativa", f"{c} negativa", n))

    n = _n_fuera(m["H_op"], 0.0, u.HORAS_DIA)
    if n:
        a.append(Aviso("dato", "horometro_fuera_rango",
                       f"H_op fuera de [0, {u.HORAS_DIA:.0f}] h", n))

    if "humedad" in m.columns:
        n = _n_fuera(m["humedad"], u.HUMEDAD_MIN, u.HUMEDAD_MAX)
        if n:
            a.append(Aviso("dato", "humedad_fuera_rango",
                           f"humedad fuera de [{u.HUMEDAD_MIN:.0%}, "
                           f"{u.HUMEDAD_MAX:.0%}]", n))

    for c in ("boundary", "boundary_h"):
        if c in m.columns:
            n = _n_fuera(m[c], u.BOUNDARY_MIN, u.BOUNDARY_MAX)
            if n:
                a.append(Aviso("dato", f"{c}_fuera_rango",
                               f"'{c}' es una fraccion del dia y sale de "
                               f"[{u.BOUNDARY_MIN:g}, {u.BOUNDARY_MAX:g}]", n))

    # La masa del dia tiene que ser la suma de sus dos turnos. Es la invariante
    # que sostiene todo el reparto: si no cuadra, la frontera medida
    # (TMS_T1 / TMS) esta comparando dos mediciones distintas.
    if {"TMS_T1", "TMS_T2"} <= set(m.columns):
        tot = m["TMS_T1"].fillna(0) + m["TMS_T2"].fillna(0)
        ref = m["TMS"].replace(0, np.nan)
        err = ((tot - m["TMS"]).abs() / ref).dropna()
        n = int((err > u.TOL_CUADRATURA).sum())
        if n:
            a.append(Aviso("dato", "turnos_no_cuadran",
                           f"TMS_T1 + TMS_T2 se aparta de TMS mas de "
                           f"{u.TOL_CUADRATURA:g} (peor caso {err.max():.2e})", n))

    # H_op son las horas de la torre que apila; H_torres, las de todas. Una no
    # puede superar a la otra. Sin violaciones en la ventana medida: es un
    # guardia, no un hallazgo.
    if "H_torres" in m.columns:
        n = int((m["H_op"] > m["H_torres"]).sum())
        if n:
            a.append(Aviso("dato", "hop_sobre_torres",
                           "H_op supera H_torres: la torre apilo mas horas que "
                           "el total de torres", n))

    # Informativos: dato valido, alcance limitado.
    if "H_op_src" in m.columns:
        n = int((~m["H_op_src"].isin(u.HOROMETROS_OK)).sum())
        if n:
            a.append(Aviso("info", "sin_horometro_torre",
                           f"dias sin horometro de {'/'.join(u.HOROMETROS_OK)}: "
                           "la fuente no corresponde al horómetro de apilado", n))
    if "turnos_ok" in m.columns:
        n = int((~m["turnos_ok"].astype(bool)).sum())
        if n:
            a.append(Aviso("info", "turno_sin_pesaje",
                           "dias sin los dos turnos pesados: media jornada de "
                           "masa contra un dia entero de horas", n))
    return a


# ─────────────────────────── validador de salida ───────────────────────────

def revisar_resultado(res):
    """Revisa saldos y densidades semanales producidos por el motor."""
    a = []
    st = res.get("shift_table")
    balance = res.get('cuadratura')
    if balance is not None and len(balance):
        pendientes = balance.loc[balance['masa_pendiente'].gt(u.TOL_CUADRATURA)]
        if len(pendientes):
            fechas = ', '.join(pendientes['fecha'].dt.strftime('%d/%m/%Y'))
            a.append(Aviso('dato', 'masa_pendiente_sin_volumen',
                           f"{pendientes['masa_pendiente'].sum():,.3f} t de masa publicada sin asignar "
                           f"por falta de volumen (balance global): {fechas}", len(pendientes)))
    if st is None or not len(st):
        return a + [Aviso("dato", "sin_reparto", "el reparto quedo vacio")]
    if 'boundary_normalizada' in st.columns:
        n = st.loc[st['boundary_normalizada'], 'fecha'].nunique()
        if n:
            a.append(Aviso('info', 'turnos_normalizados_al_total',
                           'Turnos estimados con proporciones normalizadas al total publicado; '
                           'se conserva la masa oficial, no son masas observadas por turno', int(n)))
    n = st.loc[~st['con_masa'], 'fecha'].nunique()
    if n:
        a.append(Aviso('info', 'dias_sin_masa', 'Fechas activas sin masa válida; '
                       'los resúmenes mantienen el dato ausente', int(n)))
    if 'frontera_tipo' in st.columns:
        n = st.loc[st['frontera_tipo'].eq('respaldo_50pct') & st['con_masa'], 'fecha'].nunique()
        if n:
            a.append(Aviso('info', 'turnos_sin_frontera',
                           'Sin frontera de turnos conocida; reparto de respaldo estimado al 50%', int(n)))

    wk = res.get("weekly")
    if wk is not None and len(wk) and "densidad_sem" in wk.columns:
        v = wk.loc[wk["sem_completa"], "densidad_sem"]
        n = int((~rho_plausible(v) & v.notna()).sum())
        if n:
            a.append(Aviso("dato", "densidad_sem_implausible",
                           f"densidad semanal fuera de [{u.RHO_MIN}, {u.RHO_MAX}] "
                           "t/m3 en semanas marcadas como completas", n))
        if es_ruidosa(v[rho_plausible(v)]):
            a.append(Aviso("info", "densidad_sem_ruidosa",
                           f"CV de la densidad semanal {cv(v):.1%} > "
                           f"{u.CV_MAX_CONFIABLE:.0%}: su promedio no es una "
                           "medicion"))

    # Par de semanas vecinas que se desmienten y se cuadran moviendo un solo
    # dia sobre el borde. Confirma que la aritmetica cierra con ese movimiento;
    # no distingue masa misfechada de levantamiento faltante. Ver pares_corridos.
    par = pares_corridos(res.get("daily"))
    if len(par):
        rep = par.loc[par["repara"].astype(bool)]
        if len(rep):
            d = ", ".join(str(x.date()) for x in rep["dia"])
            a.append(Aviso("dato", "fecha_corrida",
                           f"la densidad de dos semanas vecinas se corrige "
                           f"moviendo un solo dia sobre el borde ({d}): revisar ese "
                           "dia, por masa misfechada o levantamiento faltante",
                           len(rep)))
        n = len(par) - len(rep)
        if n:
            a.append(Aviso("info", "semanas_opuestas",
                           f"semanas vecinas que se apartan de la mediana en "
                           f"sentidos contrarios mas de "
                           f"{u.DESVIO_SEM_MAX:.0%} y que NO se explican "
                           "moviendo el dia del borde", n))

    return a
