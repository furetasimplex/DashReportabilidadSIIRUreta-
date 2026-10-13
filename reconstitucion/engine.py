"""Reparto de masa apilada por turno y modulo — motor simple.

Regla unica: la masa se reparte igual que el volumen.

    fraccion de masa (turno, modulo) = fraccion de volumen (turno, modulo)

El apilador corre a tasa constante dentro del dia, asi que la fraccion de
volumen tambien es la fraccion de tiempo. Un modulo que cruza la frontera entre
turnos aparece en los dos.

Frontera entre turnos. La fuente SQL trae masa pesada por turno: la frontera de
cada dia es TMS_turnoA / suma_TMS_turnos, conservando el total publicado.
Si la suma no cierra, los turnos se etiquetan como estimados. Un turno conocido
en cero conserva cero. Como alternativa se puede
proyectar por horas de apilado (H_op_turno1 / H_op_dia), que tambien corta los
dias en que un turno no registro masa. umbrales.SHIFT1_FRAC (0.5) queda solo
como respaldo para los dias sin ninguna de las dos.

Ventana de produccion. Los totalizadores de balanza definen el dia 'Fecha' como
[Fecha 08:00, Fecha+1 08:00) y 'fecha' de control_apilado_diario empareja 1:1
con esa ventana (densidad TMS/vol: CV 4.2% con lag 0 contra 65% con lag +1 dia).
La ventana de la fila 'fecha' es entonces [fecha 08:00, fecha+1 08:00): turno 1
= 08:00-20:00 (turno A de balanza), turno 2 = 20:00-08:00 (turno B). El
levantamiento que cierra la ventana es el de fecha+1 08:00.

Modulo ya en 100% arrastrado a dias siguientes con vol_diario=0: no hubo
apiladora ahi, se marca INACTIVO y no recibe masa.

Donde vive cada cosa:

    umbrales.py     todo numero que decide algo, con su justificacion
    validacion.py   contrato de entrada, dato imposible, medicion ruidosa
    db_source.py    la fuente SQL
    engine_xlsx.py  la fuente xlsx, heredada, fuera de produccion
"""
import numpy as np
import pandas as pd

from . import validacion as v
from .umbrales import (  # re-exportadas: los consumidores leen engine.X
    AVANCE_CIERRE, AVANCE_OK, BOUNDARY_SRC, COB_HORAS_MIN, DIAS, DIAS_SEM_MIN,
    HORAS_DIA, HOROMETROS_OK, H_OP_MIN, LARGO_T1, LARGO_T2, PROY_MODOS,
    SEMANA_DEF, SHIFT1_END, SHIFT1_FRAC, SHIFT1_START, opcion,
)

# Columnas que shift_table necesita si o si en el frame de masa. El resto
# (boundary, boundary_h, H_op_src, turnos_ok) son opcionales y cada una declara
# su valor por defecto donde se lee.
MASA_OBLIGATORIAS = ("fecha", "TMH", "TMS", "H_op")

# Apertura del dia operacional (08:00), reusada donde se ancla una ventana o se
# construye un timestamp a partir de una fecha sin hora.
_OFF_08 = pd.Timedelta(hours=SHIFT1_START)


def _horas(delta) -> pd.Series:
    """Timedelta -> horas, float."""
    return delta.dt.total_seconds() / 3600.0


def _grp(df: pd.DataFrame, key):
    """Columnas de agrupacion para un groupby por clave compuesta (pad_id,
    campana[, modulo]) sin repetir la comprension en cada sitio que la usa."""
    return [df[c] for c in key]


def _masa_total(df: pd.DataFrame) -> pd.Series:
    """masa_turno1 + masa_turno2, el total de masa del dia/agregado."""
    return df["masa_turno1"] + df["masa_turno2"]


# ─────────────────────────── 1. Estado por fila ───────────────────────────

def mark_status(df: pd.DataFrame) -> pd.DataFrame:
    """ACTIVO      vol_diario > 0 (hubo apiladora en ese modulo ese dia).
    INACTIVO   vol_diario = 0 y avance >= AVANCE_CIERRE: modulo ya cerrado que
               la planilla sigue arrastrando. No hay apiladora, no recibe masa.
    SIN_INICIO vol_diario = 0 y avance < AVANCE_CIERRE: modulo aun no arranca o
               no se trabajo ese dia. Tampoco recibe masa.

    AVANCE_CIERRE no es AVANCE_OK: ver umbrales.py, deciden cosas distintas."""
    df = df.sort_values(["pad_id", "campana", "modulo", "fecha"]).copy()
    activo = df["vol_diario"] > 0
    cerrado = df["avance"] >= AVANCE_CIERRE
    df["estado"] = np.where(activo, "ACTIVO",
                            np.where(cerrado, "INACTIVO", "SIN_INICIO"))
    return df.reset_index(drop=True)


# ─────────────────────── 2. Reparto por turno y modulo ───────────────────

def _order_modules(g):
    """Orden dentro del dia: primero el modulo que venia corriendo (mayor
    avance, el que se esta cerrando), despues el modulo nuevo. Empate por
    numero de modulo para que el resultado sea determinista."""
    return g.sort_values(["avance", "modulo"], ascending=[False, True])


def _overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def split_day(g: pd.DataFrame, masa_dia: float,
              boundary: float = SHIFT1_FRAC) -> list:
    """g: filas ACTIVO de un dia. Devuelve lista de dicts por modulo con la
    fraccion de volumen que cayo en cada turno y la masa correspondiente.

    Se acumula la fraccion de volumen en orden de apilado; el turno 1 es el
    tramo [0, boundary) y el turno 2 el tramo [boundary, 1].

    masa_dia es la columna de masa que se este repartiendo — TMS por la fuente
    SQL, TMH por el xlsx. El parametro se llamaba 'tmh' y llevaba TMS desde la
    migracion."""
    if not np.isfinite(boundary) or not 0 <= boundary <= 1:
        raise ValueError('La frontera de turnos debe estar entre 0 y 1')
    if g['vol_diario'].isna().any() or g['vol_diario'].lt(0).any():
        raise ValueError('El reparto requiere volúmenes no negativos y conocidos')
    V = float(g["vol_diario"].sum())
    if V <= 0:
        return []
    rows, cum = [], 0.0
    for r in _order_modules(g).itertuples():
        f0 = cum
        f1 = cum + float(r.vol_diario) / V
        cum = f1
        frac1 = _overlap(f0, f1, 0.0, boundary)
        frac2 = _overlap(f0, f1, boundary, 1.0)
        rows.append({
            "pad_id": r.pad_id, "campana": r.campana, "modulo": r.modulo,
            "avance": r.avance, "vol_diario": float(r.vol_diario),
            "frac_vol": f1 - f0, "cum_ini": f0, "cum_fin": f1,
            "frac_turno1": frac1, "frac_turno2": frac2,
            "masa_turno1": masa_dia * frac1, "masa_turno2": masa_dia * frac2,
            "cruza_turno": frac1 > 0 and frac2 > 0,
        })
    return rows


def shift_table(apilado: pd.DataFrame, masa: pd.DataFrame,
                boundary: float = SHIFT1_FRAC,
                boundary_src: str = "masa") -> pd.DataFrame:
    """Tabla larga (fecha, pad, campana, modulo) con masa por turno.

    masa      DataFrame con MASA_OBLIGATORIAS y, opcionalmente, 'boundary' /
              'boundary_h' (frontera turno1/turno2 medida o proyectada del dia),
              'H_op_src' y 'turnos_ok'.
    Reparte TMS: Apilado_TMS_Real ya es masa seca y no se le vuelve a descontar
    humedad. La ventana de la fila 'fecha' es [fecha 08:00, fecha+1 08:00).

    boundary  frontera de respaldo cuando el dia no trae una medida.
    boundary_src  'masa'  -> proporción TMS_turnoA / suma_TMS_turnos.
                  'horas' -> frontera proyectada por hora de apilado. Ver
                             umbrales.BOUNDARY_SRC.
              Un valor fuera de esas dos opciones levanta ValueError: antes caia
              callado al respaldo fijo de 0.5 para TODOS los dias y dejaba el
              nombre equivocado escrito en el resultado.

    Dias sin pesaje quedan con masa NaN (la fraccion de volumen igual se
    reporta)."""
    bnd_col = BOUNDARY_SRC[opcion("boundary_src", boundary_src, BOUNDARY_SRC)]
    falta = [c for c in MASA_OBLIGATORIAS if c not in masa.columns]
    if falta:
        raise ValueError(f"shift_table: al frame de masa le faltan {falta}")

    m = masa.set_index("fecha")
    if not m.index.is_unique:
        raise ValueError("shift_table: el frame de masa repite fechas")
    tmh_s, tms_s, hop_s = m["TMH"], m["TMS"], m["H_op"]
    # Opcionales, cada una con su default explicito. La frontera puede no estar
    # (el xlsx no la trae): ahi todos los dias caen al respaldo, que es correcto
    # para esa fuente y distinto de recibir un selector mal escrito.
    bnd_s = m[bnd_col] if bnd_col in m.columns else None
    src_s = m["H_op_src"] if "H_op_src" in m.columns else None
    tok_s = m["turnos_ok"] if "turnos_ok" in m.columns else None

    out = []
    for fecha, g in apilado.groupby("fecha"):
        act = g[g["estado"] == "ACTIVO"]
        if act.empty:
            continue
        masa_dia = float(tms_s.get(fecha, np.nan))
        if not np.isfinite(masa_dia) or masa_dia < 0:
            masa_dia = np.nan

        # frontera medida del dia; si no hay pesaje por turno, cae al respaldo
        b, medida = boundary, False
        if bnd_s is not None:
            bv = bnd_s.get(fecha, np.nan)
            if pd.notna(bv):
                b, medida = float(bv), True
        normalizada = (bool(m.loc[fecha, 'boundary_normalizada'])
                       if fecha in m.index and 'boundary_normalizada' in m.columns
                       and pd.notna(m.loc[fecha, 'boundary_normalizada'])
                       and boundary_src == 'masa' and medida else False)

        ventana_ini = pd.Timestamp(fecha) + _OFF_08
        for row in split_day(act, masa_dia, b):
            row.update({
                "fecha": fecha,
                # levantamiento que cierra la ventana de 24 h
                "medido_en": ventana_ini + pd.Timedelta(days=1),
                "turno1_ini": ventana_ini,
                "turno2_ini": ventana_ini + pd.Timedelta(hours=LARGO_T1),
                "boundary": b,
                "boundary_medida": medida and boundary_src == 'masa' and not normalizada,
                "boundary_disponible": medida,
                "boundary_normalizada": normalizada,
                "frontera_tipo": ('normalizada_al_total' if normalizada else
                                  'proyectada_horas' if medida and boundary_src == 'horas' else
                                  'medida' if medida else 'respaldo_50pct'),
                "boundary_src": boundary_src,
                "masa_dia": masa_dia,
                "fuente_masa": (m.loc[fecha, 'fuente_masa'] if fecha in m.index
                                and 'fuente_masa' in m.columns else 'NO_DECLARADA'),
                "TMS_dia": masa_dia,
                "TMH_dia": float(tmh_s.get(fecha, np.nan)),
                "H_op": float(hop_s.get(fecha, np.nan)),
                "H_op_src": (src_s.get(fecha, "n/d") if src_s is not None
                             else "chancador"),
                "turnos_ok": (bool(tok_s.get(fecha, False))
                              if tok_s is not None else True),
                "vol_dia_total": float(act["vol_diario"].sum()),
                "n_modulos_dia": int(len(act)),
            })
            out.append(row)
    df = pd.DataFrame(out)
    if df.empty:
        return df
    df["masa_total"] = _masa_total(df)
    df["densidad"] = df["masa_total"] / df["vol_diario"]
    # dias sin pesaje: la fraccion de volumen es valida pero no hay masa. Se
    # marca para no arrastrar ese volumen al calcular densidades acumuladas
    # (contarlo sin su masa hunde la densidad del modulo).
    df["con_masa"] = df["masa_dia"].notna()
    df["vol_con_masa"] = df["vol_diario"].where(df["con_masa"], 0.0)
    return df.sort_values(["fecha", "cum_ini"]).reset_index(drop=True)


def _hop_por_dia(df):
    """Una H_op por dia. El horometro es del DIA, no de la fila: sumarlo sobre
    las filas del reparto lo contaria una vez por modulo activo."""
    return df.groupby("fecha")["H_op"].first()


def _sum_known(s):
    """No transforma un grupo enteramente sin observación en cero."""
    return s.sum(min_count=1)


def cuadratura_masa(apilado, masa, st):
    """Balance diario global: masa publicada = asignada + pendiente.

    Sin volumen no inventa módulos ni tonelaje de turnos. La masa pendiente
    conserva su fecha y fuente, incluso si el reparto quedó vacío.
    """
    volumen = apilado.groupby('fecha')['vol_diario'].sum(min_count=1).rename('volumen')
    diario = masa.drop(columns=['volumen'], errors='ignore').set_index('fecha').join(volumen, how='outer').reset_index()
    asignada = (st.groupby('fecha')['masa_total'].sum(min_count=1)
                if not st.empty else pd.Series(dtype=float))
    diario['masa_asignada'] = diario['fecha'].map(asignada)
    valida = diario['TMS'].notna() & np.isfinite(diario['TMS']) & diario['TMS'].ge(0)
    sin_vol = diario['volumen'].fillna(0).le(0)
    diario.loc[valida & sin_vol, 'masa_asignada'] = 0.0
    diario['masa_pendiente'] = (diario['TMS'] - diario['masa_asignada']).where(valida)
    diario.loc[diario['masa_pendiente'].abs().le(1e-6), 'masa_pendiente'] = 0.0
    diario['estado_masa'] = np.select(
        [~valida, valida & sin_vol & diario['TMS'].gt(0)],
        ['SIN_MASA_VALIDA', 'PENDIENTE_SIN_VOLUMEN'], default='ASIGNADA')
    return diario.sort_values('fecha').reset_index(drop=True)


def daily_shift_summary(st: pd.DataFrame, sem=SEMANA_DEF) -> pd.DataFrame:
    """Masa por turno agregada por dia (todos los modulos).

    Trae la semana de reconstitucion de cada dia: la coherencia entre dias
    vecinos se juzga contra el borde semanal (validacion.pares_corridos) y sin
    esta columna cada consumidor la volvia a derivar por su cuenta."""
    if st.empty:
        return st
    g = st.groupby("fecha").agg(
        masa_turno1=("masa_turno1", _sum_known),
        masa_turno2=("masa_turno2", _sum_known),
        TMH_dia=("TMH_dia", "first"),
        TMS_dia=("TMS_dia", "first"),
        H_op=("H_op", "first"),
        H_op_src=("H_op_src", "first"),
        turnos_ok=("turnos_ok", "first"),
        boundary=("boundary", "first"),
        boundary_medida=("boundary_medida", "first"),
        frontera_tipo=("frontera_tipo", "first"),
        boundary_normalizada=("boundary_normalizada", "first"),
        vol_dia_total=("vol_dia_total", "first"),
        n_modulos=("n_modulos_dia", "first"),
        n_cruces=("cruza_turno", "sum"),
    ).reset_index()
    g["masa_total"] = _masa_total(g)
    g["densidad_dia"] = g["masa_total"] / g["vol_dia_total"]
    g["semana"] = semana_de(g["fecha"], sem)
    return g


# ─────────────────────── 3. Semana de reconstitucion ───────────────────────

def semana_de(fecha, sem=SEMANA_DEF):
    """Bucket de reconstitucion al que pertenece cada fecha.

    El levantamiento topografico es DIARIO y el volumen de cada dia es una
    medicion. La semana no corrige la resolucion del dato: agrega para que un
    dia con volumen centinela o sin masa no se lleve por delante la densidad
    que se usa para proyectar. Ver umbrales, seccion 4.

    sem = (dia_inicial, dia_final), indices 0=lunes..6=domingo. El ciclo es
    siempre de 7 dias contados desde dia_inicial; dia_final marca hasta donde
    llega el levantamiento dentro de ese ciclo. Si la ventana es mas corta que
    7 dias, los dias que quedan fuera no pertenecen a ninguna reconstitucion:
    devuelven NaT y quien los consuma cae a la densidad global.

    El ancla es un selector, no un dato: ver umbrales.SEMANA_DEF."""
    ini, fin = sem
    off = (fecha.dt.weekday - ini) % 7
    largo = (fin - ini) % 7 + 1
    inicio = fecha - pd.to_timedelta(off, unit="D")
    return inicio.where(off < largo)


def dias_por_semana(sem=SEMANA_DEF) -> int:
    """Largo del ciclo de reconstitucion, en dias."""
    return (sem[1] - sem[0]) % 7 + 1


# Los cuatro frames fechados de un resultado. Recortar la ventana de analisis
# es recortarlos a los cuatro: lo derivado (daily, weekly, modules, itinerario)
# se recalcula desde ellos, no se filtra.
FRAMES_FECHADOS = ("apilado", "masa", "shift_table", "inactivos", "cuadratura")


def _recortar(res: dict, mascara) -> dict:
    """Aplica mascara(frame) -> Series booleana a los frames fechados.

    Recorta la ventana de analisis entera — masa, volumen, itinerario y
    graficos — no filtra por calidad: los totales que se muestran despues son
    los de la ventana elegida."""
    out = dict(res)
    for k in FRAMES_FECHADOS:
        d = res.get(k)
        if d is not None and len(d) and "fecha" in d.columns:
            out[k] = d[mascara(d)]
    return out


def recortar_rango(res: dict, f0=None, f1=None) -> dict:
    """Deja solo los dias dentro de [f0, f1]."""
    if f0 is None and f1 is None:
        return res

    def m(d):
        ok = pd.Series(True, index=d.index)
        if f0 is not None:
            ok &= d["fecha"] >= pd.Timestamp(f0)
        if f1 is not None:
            ok &= d["fecha"] <= pd.Timestamp(f1)
        return ok

    return _recortar(res, m)


def recortar_semana(res: dict, sem=SEMANA_DEF) -> dict:
    """Deja solo los dias que caen dentro del ciclo de reconstitucion.

    Con un ciclo de 7 dias no recorta nada. Con uno mas corto, los dias que
    quedan fuera no pertenecen a ninguna reconstitucion y salen de todo."""
    if dias_por_semana(sem) >= 7:
        return res
    return _recortar(res, lambda d: semana_de(d["fecha"], sem).notna())


def rho_semanal(st: pd.DataFrame, sem=SEMANA_DEF) -> pd.Series:
    """Densidad por semana de reconstitucion: masa pesada / volumen levantado.

    No es la unica densidad medida — el levantamiento es diario y las tres
    resoluciones miden lo mismo. En banda fisica [1.2, 2.4]:

        diaria    n=340  mediana 1.737  CV 6.60%  MAD/mediana 3.57%
        modulo    n=148  mediana 1.732  CV 7.83%  MAD/mediana 2.16%
        semanal   n= 55  mediana 1.734  CV 7.31%  MAD/mediana 1.56%

    La semana se usa porque es la que menos unidades pierde fuera de banda
    (98.2% dentro, contra 94.2% de los dias): un dia roto contamina su propia
    densidad, una semana lo diluye. Elegir modulo en vez de semana mueve
    rho_proy 0.033 t/m3 en la mediana (p95 0.31), y como la duracion proyectada
    sale de masa/tasa_de_masa, no de rho, la proyeccion no cambia — solo cambia
    rate_h, que es la traduccion a volumen.

    Las semanas cortadas por el borde de la ventana quedan sin densidad: traen
    el volumen de la semana entera contra los pocos dias de masa que alcanzaron
    a entrar (la primera semana de la ventana da 0.245 t/m3 con 2 dias). El que
    las consume las reemplaza por la densidad global."""
    g = weekly_summary(st, sem)
    if g.empty:
        return pd.Series(dtype=float)
    return g.set_index('semana')['densidad_sem'].where(
        g.set_index('semana')['sem_completa'])


def weekly_summary(st: pd.DataFrame, sem=SEMANA_DEF) -> pd.DataFrame:
    """Resumen a la resolucion de la reconstitucion."""
    if st.empty:
        return st
    s = st.assign(semana=semana_de(st["fecha"], sem)).dropna(subset=["semana"])
    g = s.groupby("semana").agg(
        n_dias=("fecha", "nunique"),
        n_modulos=("modulo", "nunique"),
        vol_total=("vol_diario", "sum"),
        vol_con_masa=("vol_con_masa", "sum"),
        masa_turno1=("masa_turno1", _sum_known),
        masa_turno2=("masa_turno2", _sum_known),
    )
    validas = s['con_masa'] & s['masa_total'].ge(0)
    g['n_dias_con_masa'] = s.loc[validas].groupby('semana')['fecha'].nunique().reindex(g.index, fill_value=0)
    g['fuentes_masa'] = (s.loc[validas].groupby('semana')['fuente_masa'].nunique().reindex(g.index, fill_value=0)
                        if 'fuente_masa' in s.columns else 1)
    # el horometro es del dia: una H_op por fecha y despues se suman las del
    # ciclo. Sumar la columna cruda contaria el dia una vez por modulo activo.
    g["H_op"] = s.groupby(["semana", "fecha"])["H_op"].first().groupby("semana").sum()
    g = g.reset_index()
    g["masa_total"] = _masa_total(g)
    g["densidad_sem"] = (g["masa_total"] / g["vol_con_masa"]).where(
        g["vol_con_masa"] > 0)
    # semana cortada por el borde de la ventana o por un hueco de reporte: su
    # densidad se muestra pero no se usa para proyectar
    g["sem_completa"] = ((g["n_dias_con_masa"] >= min(DIAS_SEM_MIN, dias_por_semana(sem)))
                         & g['n_dias_con_masa'].eq(g['n_dias']) & g['fuentes_masa'].eq(1))
    g["pct_turno1"] = (g["masa_turno1"] / g["masa_total"] * 100).where(
        g["masa_total"] > 0)
    return g


def module_summary(st: pd.DataFrame) -> pd.DataFrame:
    """Densidad por modulo = masa total acumulada / volumen total acumulado.
    Dentro de un dia todos los modulos comparten densidad (la masa se reparte
    por volumen); la diferencia entre modulos aparece al acumular dias."""
    if st.empty:
        return st
    g = st.groupby(["pad_id", "campana", "modulo"]).agg(
        n_dias=("fecha", "nunique"),
        vol_total=("vol_diario", "sum"),
        vol_con_masa=("vol_con_masa", "sum"),
        n_dias_sin_masa=("con_masa", lambda s: int((~s).sum())),
        masa_turno1=("masa_turno1", _sum_known),
        masa_turno2=("masa_turno2", _sum_known),
        avance_final=("avance", "max"),
        fecha_ini=("fecha", "min"),
        fecha_fin=("fecha", "max"),
    ).reset_index()
    g["masa_total"] = _masa_total(g)
    # densidad solo sobre el volumen que tiene masa pesada asociada
    g["densidad"] = (g["masa_total"] / g["vol_con_masa"]).where(g["vol_con_masa"] > 0)
    g["pct_turno1"] = (g["masa_turno1"] / g["masa_total"] * 100).where(g["masa_total"] > 0)
    return g


# ─────────────────────── 4. Tasa del apilador ───────────────────────

def dias_tasa(st: pd.DataFrame) -> pd.Series:
    """Mascara de filas que pueden medir la tasa de maquina.

    Horometro de torre (HOROMETROS_OK; no el chancador, que satura en 24 h, ni
    la rotopala, que es del circuito de reclamo), >= H_OP_MIN h y con los dos
    turnos registrados — un dia con un turno en cero trae media jornada de masa
    contra un dia entero de horas."""
    src = (st["H_op_src"] if "H_op_src" in st.columns
           else pd.Series(HOROMETROS_OK[0], index=st.index))
    tok = (st["turnos_ok"] if "turnos_ok" in st.columns
           else pd.Series(True, index=st.index))
    return (st['H_op'].between(H_OP_MIN, HORAS_DIA)
            & src.isin(HOROMETROS_OK) & tok & st['con_masa'])


def tasa_referencia(st: pd.DataFrame) -> dict:
    """Capacidad del apilador medida sobre los dias con horometro creible.

    Devuelve tasa volumetrica, tasa de masa y utilizacion de calendario. Se
    calcula aparte del itinerario para poder medirla una vez sobre toda la
    ventana y usarla en ventanas cortas: solo 31 de los 405 dias tienen
    horometro de torre, asi que una semana suelta casi nunca alcanza a medirla,
    y sin tasa el proyectado colapsa a cero.

    La tasa de referencia es de MASA, t/h, no m3/h. La correa y la torre estan
    limitadas por tonelaje, no por volumen: un modulo denso pasa los mismos t/h
    que uno suelto, pero menos m3/h."""
    ok = dias_tasa(st)
    horas = (st["frac_vol"] * st["H_op"]).where(ok, 0.0).sum()
    vol = st["vol_diario"].where(ok, 0.0).sum()
    masa = (st["masa_turno1"] + st["masa_turno2"]).where(ok, 0.0).sum()
    # El Gantt corre en calendario y el apilador no apila las 24 h, asi que la
    # duracion proyectada usa la tasa de calendario = tasa de maquina x
    # utilizacion, medida sobre los mismos dias limpios que dan la tasa.
    hop = _hop_por_dia(st.loc[ok])
    return {
        "rate_ref": (vol / horas) if horas > 0 else np.nan,
        "rate_masa_ref": (masa / horas) if horas > 0 else np.nan,
        "util": (hop.sum() / (HORAS_DIA * len(hop))) if len(hop) else np.nan,
        "n_dias_tasa": len(hop),
    }


# ─────────────────────── 5. Cadena proyectada ───────────────────────

def _proy_apilado(it, st, dur_h, key):
    """Coloca la cadena proyectada saltando el calendario ocioso.

    El reloj del proyectado solo avanza los dias en que ESA campana tuvo
    volumen. Cada dia activo aporta sus 24 h; los dias en que el apilador estuvo
    en el otro pad, o detenido, no consumen proyectado. Devuelve (ini, fin) como
    Timestamps.

    Pasado el ultimo dia activo el reloj vuelve a correr continuo: ahi ya no hay
    medicion contra que contrastar, y frenarlo dibujaria una barra infinita.

    key es la clave de la cadena, (pad_id, campana, tramo). El calendario que se
    consume es el de la CAMPANA — los dos primeros niveles — no el del tramo: el
    encadenado se corta por tramo cuando un modulo no cierra, pero los dias
    disponibles siguen siendo los de la campana entera. Cada tramo arranca en el
    primer dia activo de la campana que cae en o despues del arranque real de su
    primer modulo: al re-anclar no se puede volver al dia 0.
    """
    ini = pd.Series(pd.NaT, index=it.index, dtype="datetime64[ns]")
    fin = pd.Series(pd.NaT, index=it.index, dtype="datetime64[ns]")
    pad_col, cam_col = key[0], key[1]
    calendario = {k: np.sort(g["fecha"].unique())
                  for k, g in st.groupby([pad_col, cam_col], sort=False)}
    for k, g in it.groupby(key, sort=False):
        dias = calendario.get((k[0], k[1]), ())
        if not len(dias):
            continue
        dias = pd.DatetimeIndex(dias) + _OFF_08       # cada dia parte a las 08:00
        dias = dias[dias >= g["act_ini_dt"].min()]   # el tramo no retrocede
        if not len(dias):
            continue
        cum = dur_h.loc[g.index].fillna(0.0).cumsum()
        bordes = np.concatenate([[0.0], cum.to_numpy()])
        idx = np.floor(bordes / HORAS_DIA).astype("int64")
        resto = pd.to_timedelta(bordes - idx * HORAS_DIA, unit="h")
        dentro = np.clip(idx, 0, len(dias) - 1)
        base = dias[dentro]
        # tramo que se pasa del ultimo dia activo: calendario continuo
        extra = pd.to_timedelta((idx - dentro) * HORAS_DIA, unit="h")
        t = base + resto + extra
        ini.loc[g.index] = t[:-1]
        fin.loc[g.index] = t[1:]
    return ini, fin


def _cruce_turno(ts):
    """Instante de cambio de turno de la ventana operacional donde cae ts.

    La ventana es [fecha 08:00, fecha+1 08:00) y el cruce cae a las 20:00 de esa
    'fecha'. Un ts entre las 00:00 y las 08:00 todavia pertenece a la ventana del
    dia anterior, asi que el cruce que le corresponde ya paso: por eso se
    descuentan las 8 h antes de truncar al dia."""
    return (ts - _OFF_08).dt.floor("D") + _OFF_08 + pd.Timedelta(hours=LARGO_T1)


def tramo_cadena(it: pd.DataFrame, key, umbral=None) -> pd.Series:
    """Corta la cadena proyectada donde un modulo no llego a cerrar.

    La cadena supone que el modulo n+1 arranca donde el proyectado del n
    termino. Eso solo vale si el n efectivamente cerro: si quedo a medias, su
    'fin' proyectado es ficcion y arrastrarlo corre todo lo que viene detras.
    En 2026 pasa 11 veces — el apilador se va al otro pad o la planta para, el
    modulo queda abierto y se reanuda dias despues (M92 quedo abierto el 04-21 y
    cerro el 05-07, 15 dias despues).

    Devuelve un entero por fila: el numero de tramo dentro de la campana. El
    tramo sube en el modulo SIGUIENTE al que no cerro, no en el incompleto —
    el incompleto todavia hereda el arranque de su antecesor, que si cerro.
    Cada tramo se re-ancla en el arranque real (act_ini) de su primer modulo.

    Con todos los modulos sobre el umbral devuelve 0 en todas las filas y la
    cadena queda igual que antes: es una regla que solo actua donde hay dano.

    umbral=None toma AVANCE_OK. Para barrer el umbral se pasa por aqui — o por
    module_itinerary(avance_ok=...) — y NO reasignando engine.AVANCE_OK, que es
    estado global compartido: con el dashboard cacheando resultados, una corrida
    con el umbral parchado deja el cache envenenado para todas las siguientes."""
    umbral = AVANCE_OK if umbral is None else umbral
    a = it["avance_final"]
    rompe = a.isna() | (a < umbral)
    g = _grp(it, key)
    return rompe.groupby(g, sort=False).shift(1).fillna(False).astype(int) \
                .groupby(g, sort=False).cumsum()


# ─────────────────────── 6. Itinerario por modulo ───────────────────────

def _presencia(apilado, key):
    """Ventana de MEDICION por modulo: del primer al ultimo levantamiento que lo
    registro, incluyendo los dias sin apilar que la planilla arrastra."""
    return apilado.groupby(key).agg(
        real_ini=("fecha", "min"),
        real_fin=("fecha", "max"),
        n_dias_planilla=("fecha", "nunique"),
    ).reset_index()


def _actividad(st, key):
    """Dias efectivamente apilados, con masa, volumen y horas imputadas.

    Las horas del dia se reparten entre los modulos activos en proporcion a su
    volumen, y solo cuentan los dias con horometro creible (dias_tasa): los de
    0 y 1 h son huecos de registro contra 40-50 mil m3 apilados, y meterlos
    dispara la tasa a valores imposibles."""
    st = st.copy()
    ok = dias_tasa(st)
    st["horas_mod"] = (st["frac_vol"] * st["H_op"]).where(ok, 0.0)
    st["vol_con_horas"] = st["vol_diario"].where(ok, 0.0)
    st["masa_con_horas"] = (st["masa_turno1"] + st["masa_turno2"]).where(ok, 0.0)
    act = st.groupby(key).agg(
        act_ini=("fecha", "min"),
        act_fin=("fecha", "max"),
        n_dias_act=("fecha", "nunique"),
        vol_total=("vol_diario", "sum"),
        vol_con_masa=("vol_con_masa", "sum"),
        masa_turno1=("masa_turno1", _sum_known),
        masa_turno2=("masa_turno2", _sum_known),
        horas=("horas_mod", "sum"),
        vol_con_horas=("vol_con_horas", "sum"),
        masa_con_horas=("masa_con_horas", "sum"),
        avance_final=("avance", "max"),
    ).reset_index()
    act["masa_total"] = act["masa_turno1"] + act["masa_turno2"]
    return act


def _rho_proyeccion(it, st, key, sem):
    """Densidad con que se proyecta cada modulo.

    NO es la del modulo, aunque la del modulo tambien sea una medicion valida
    (n=148 en banda, CV 7.83%, a 0.033 t/m3 de la semanal en la mediana). Se
    usa la de la semana porque pierde menos unidades fuera de banda: 172 de 177
    modulos duran menos de 7 dias, asi que un solo dia roto se lleva la densidad
    del modulo entero, mientras que en la semana se diluye.

    La semana se le pasa a cada modulo ponderando por el volumen que ese modulo
    puso en cada semana; el modulo que no aporta volumen con masa toma la
    densidad global de la ventana."""
    diario = daily_shift_summary(st)
    limpio = diario.loc[v.rho_plausible(diario['densidad_dia'])]
    fuentes = (st.loc[st['fecha'].isin(limpio['fecha']) & st['con_masa'], 'fuente_masa'].nunique()
               if 'fuente_masa' in st.columns else 1)
    rho_glob = (limpio['masa_total'].sum() / limpio['vol_dia_total'].sum()
                if limpio['fecha'].nunique() >= min(DIAS_SEM_MIN, dias_por_semana(sem))
                and limpio['vol_dia_total'].sum() > 0 and fuentes == 1 else np.nan)
    if not np.isfinite(rho_glob) or not v.rho_plausible(pd.Series([rho_glob])).iloc[0]:
        rho_glob = np.nan
    ws = st.assign(semana=semana_de(st["fecha"], sem))
    ws["rho_sem"] = ws["semana"].map(rho_semanal(st, sem))
    ws['rho_sem'] = ws['rho_sem'].where(v.rho_plausible(ws['rho_sem']))
    # el volumen de las semanas sin densidad valida no pondera: si entrara al
    # denominador sin su masa hundiria la densidad del modulo
    ws["vol_sem"] = ws["vol_con_masa"].where(ws["rho_sem"].notna(), 0.0)
    ws["masa_sem"] = ws["vol_sem"] * ws["rho_sem"]
    r = ws.groupby(key).agg(masa_sem=("masa_sem", "sum"),
                            vol_sem=("vol_sem", "sum"))
    rho_mod = (r["masa_sem"] / r["vol_sem"]).where(r["vol_sem"] > 0)
    rho_sem = it.set_index(key).index.map(rho_mod)
    return pd.Series(rho_sem, index=it.index), rho_glob


def _duracion(it, st, dur_h, proy_modo, util, rate_masa_ref):
    """Lleva la duracion proyectada al calendario segun el modo. La tasa de
    maquina es la misma en los tres; lo que cambia es cuanto calendario se le
    concede. Devuelve (dur_h ajustada, util efectiva, factor imputado).

      apilado     El reloj del proyectado corre solo los dias en que la campana
                  tuvo volumen. El apilador alterna entre pads (los spans de
                  cam17, cam18 y cam11 se solapan aunque solo 17 dias tengan dos
                  campanas activas): los dias que apilo en el otro pad no son
                  atraso de esta campana. Deja a la vista el atraso que si lo es.
      calendario  util de calendario sobre toda la ventana (masa / 24 h por dia)
                  en vez de la util de los dias limpios. La util medida (0.84)
                  sale solo de los dias que pasan el filtro de horometro, o sea
                  los buenos; la de calendario es ~0.59.
      campana     util recalibrada por campana para que la cadena cubra
                  exactamente el span medido. Es lo que hace el jsx — sus
                  duraciones suman el span (4443 h contra 4560 medidos en
                  pad1/cam17) y por eso no deriva. Deriva cero por construccion:
                  sirve para ver el orden relativo de los modulos, no para saber
                  si la campana se atraso.
    """
    imputado = pd.Series(False, index=it.index)
    if proy_modo == "calendario":
        dias_win = (st["fecha"].max() - st["fecha"].min()).days + 1
        masa_win = (st["masa_turno1"] + st["masa_turno2"]).sum()
        util_cal = (masa_win / (rate_masa_ref * HORAS_DIA * dias_win)
                    if rate_masa_ref > 0 and dias_win > 0 else np.nan)
        if util_cal > 0:
            return dur_h * (util / util_cal), util_cal, imputado
        return dur_h, util_cal, imputado
    if proy_modo == "campana":
        g = it.groupby(["pad_id", "campana"], sort=False)
        span = _horas(g["real_fin_dt"].transform("max")
                      - g["act_ini_dt"].transform("min"))
        tot = dur_h.groupby(_grp(it, ["pad_id", "campana"])).transform("sum")
        factor = (span / tot).replace([np.inf, -np.inf], np.nan)
        # campana degenerada (span o duracion nulos): sin factor medible se deja
        # la duracion cruda, y se marca para que no se lea como calibrada
        imputado = factor.isna()
        factor = factor.fillna(1.0)
        return dur_h * factor, util / factor, imputado
    return dur_h, util, imputado


def module_itinerary(apilado: pd.DataFrame, st: pd.DataFrame,
                     proy_modo: str = "apilado", sem=SEMANA_DEF, tasa=None,
                     avance_ok=None) -> pd.DataFrame:
    """Itinerario por modulo — equivalente al GanttSVG del jsx.

    Dos cosas distintas, no dos versiones de lo mismo:

    proy_ini / proy_fin  El proyectado: cuanto deberia durar el modulo a su
                         tasa de apilado, encadenado. El modulo n+1 arranca
                         exactamente donde termina el proyectado del modulo n;
                         la medicion no manda sobre el arranque. La campana se
                         ancla una sola vez, en el arranque real del primero.

    real_ini / real_fin  La ventana de MEDICION: del primer al ultimo
                         levantamiento topografico que registro el modulo.
                         No es tiempo de apilado — incluye los dias sin apilar
                         (vol_diario = 0) que caen dentro de la ventana o que
                         la planilla arrastra al final.

    Proyeccion: TODOS los modulos avanzan al mismo TONELAJE por hora — es una
    sola maquina y su capacidad no cambia de un modulo a otro. Lo que si cambia
    es la densidad, asi que los m3/h no son constantes: el modulo denso avanza
    menos volumen con el mismo tonelaje. La duracion proyectada es entonces
    masa / tasa de masa, no volumen / tasa de volumen. Proyectar con un m3/h
    unico le da al modulo denso menos tiempo del que le toca, y como el
    itinerario se encadena ese error no se cancela: se acumula modulo a modulo.
    Es lo que hace el jsx — ahi rate_h x rho es constante dentro de cada campana
    (2813 t/h en pad1/cam17, 3654 en cam18, 2986 en pad2/cam11, CV 0.003%)
    mientras su rate_h volumetrico varia 65-82% entre modulos.

    La tasa por modulo no se proyecta, y la razon NO es que el volumen diario
    sea prorrateo — el levantamiento es diario. Es que rate_mod = volumen/horas
    necesita horas creibles, y el horometro de torre solo cubre 53 de 422 dias:
    en la mayoria de los modulos el denominador no existe o cubre una fraccion
    del volumen. Por eso rate_mod se gatilla en COB_HORAS_MIN y queda como
    diagnostico de dispersion, y la tasa que proyecta sale del agregado de la
    ventana, donde si hay horas suficientes para medirla.

    rate_masa_ref es la tasa de maquina, t por hora de torre andando.
    rate_masa_h es la de calendario, rate_masa_ref x util, y es la que da la
    duracion: el Gantt corre en dias y el apilador no apila las 24 h.
    rate_h es la traduccion a volumen de cada modulo, rate_masa_h / densidad,
    y cumple rate_h x rho_proy = rate_masa_h para todos.

    tasa       tasa ya medida, para reusarla en ventanas cortas. Solo 31 de los
               405 dias tienen horometro de torre, asi que una semana suelta
               casi nunca alcanza a medirla y sin tasa el proyectado colapsa. La
               capacidad de la maquina no es propiedad de la ventana.
    avance_ok  umbral de cierre para encadenar. None = umbrales.AVANCE_OK. Es el
               punto de entrada para barrer el umbral; ver tramo_cadena."""
    if st.empty:
        return pd.DataFrame()
    opcion("proy_modo", proy_modo, PROY_MODOS)

    key = ["pad_id", "campana", "modulo"]
    it = _actividad(st, key).merge(_presencia(apilado, key), on=key, how="left")

    # el modulo solo existe en el grafico desde que arranca: los dias previos en
    # que la planilla ya lo lista con avance 0 no son parte del itinerario
    it["real_ini"] = it[["real_ini", "act_ini"]].max(axis=1)
    # defensa del merge how='left': un modulo presente en st y ausente de la
    # planilla llega con real_fin NaT y toma su ultimo dia activo
    it["real_fin"] = it[["real_fin", "act_fin"]].max(axis=1)
    it["n_dias_inact"] = ((it["real_fin"] - it["real_ini"]).dt.days + 1
                          - it["n_dias_act"]).clip(lower=0)
    it["densidad"] = (it["masa_total"] / it["vol_con_masa"]).where(it["vol_con_masa"] > 0)

    # Tasa unica del apilador: una sola maquina, una sola capacidad. Se mide
    # sobre el agregado de la ventana porque es la unica escala donde hay
    # horometro de torre suficiente, no porque el volumen diario sea ruido.
    t = tasa or tasa_referencia(st)
    rate_ref, rate_masa_ref, util = t["rate_ref"], t["rate_masa_ref"], t["util"]
    it["rate_ref"] = rate_ref
    it["rate_masa_ref"] = rate_masa_ref
    it["util"] = util
    it["rate_masa_h"] = rate_masa_ref * util

    it["rho_sem"], rho_glob = _rho_proyeccion(it, st, key, sem)
    it["rho_proy"] = it["rho_sem"].where(v.rho_plausible(it["rho_sem"])).fillna(rho_glob)
    # tasa volumetrica de calendario del modulo. Equivalente al rate_h del jsx:
    # rate_h x rho_proy = rate_masa_h para todos
    it["rate_h"] = it["rate_masa_h"] / it["rho_proy"]
    # diagnostico, no entra en la proyeccion: cuanto se aparta cada modulo de la
    # tasa comun. Dispersion alta = cobertura de horometro irregular dentro del
    # modulo, antes que apilador lento
    it["cob_horas"] = (it["vol_con_horas"] / it["vol_total"]).where(it["vol_total"] > 0)
    # sin COB_HORAS_MIN del volumen respaldado por dias con horometro, la tasa
    # aparente no dice nada del modulo: queda vacia en vez de mentir
    it["rate_mod"] = (it["vol_con_horas"] / it["horas"]).where(
        (it["horas"] >= H_OP_MIN) & (it["cob_horas"] >= COB_HORAS_MIN))
    it["rate_dev"] = it["rate_mod"] / rate_ref
    it["n_dias_tasa"] = t["n_dias_tasa"]

    # ventanas operacionales completas: el dia 'fecha' cierra a las 08:00 del
    # dia siguiente, asi que la ventana de medicion llega hasta ahi
    it["real_ini_dt"] = it["real_ini"] + _OFF_08
    it["real_fin_dt"] = it["real_fin"] + pd.Timedelta(days=1) + _OFF_08
    it["act_ini_dt"] = it["act_ini"] + _OFF_08
    it["act_fin_dt"] = it["act_fin"] + pd.Timedelta(days=1) + _OFF_08

    # El proyectado es una secuencia continua: el modulo siguiente arranca
    # exactamente cuando termina el proyectado del anterior, no cuando la
    # medicion dice que se empezo a apilar. Solo el primer modulo del tramo se
    # ancla en su instante real de arranque; de ahi en adelante la cadena es
    # puro volumen / tasa. La distancia entre el bloque verde y la linea de
    # color es lo que la operacion se corrio del plan.
    it = it.sort_values(["pad_id", "campana", "act_ini", "modulo"]).reset_index(drop=True)
    dur_h = (it["vol_total"] / it["rate_h"]).where(np.isfinite(it["rate_h"]) & it["rate_h"].gt(0))

    it["proy_modo"] = proy_modo
    dur_h, util_ef, imputado = _duracion(it, st, dur_h, proy_modo, util,
                                         rate_masa_ref)
    it["util_ef"] = util_ef
    it["factor_imputado"] = imputado
    it["proy_h"] = dur_h
    dur = pd.to_timedelta(dur_h.fillna(0.0), unit="h")

    # La cadena se encadena por tramo, no por campana: un modulo que no cerro no
    # puede fijar el arranque del siguiente. Ver tramo_cadena. Con toda la
    # campana sobre el umbral hay un solo tramo y esto es la cadena de siempre.
    umbral = AVANCE_OK if avance_ok is None else float(avance_ok)
    it["avance_ok"] = it["avance_final"].fillna(0.0) >= umbral
    it["avance_umbral"] = umbral
    it["tramo"] = tramo_cadena(it, ["pad_id", "campana"], umbral)
    it["reancla"] = it["tramo"] > it.groupby(["pad_id", "campana"],
                                             sort=False)["tramo"].shift(1).fillna(0)
    cad = ["pad_id", "campana", "tramo"]

    if proy_modo == "apilado":
        it["proy_ini"], it["proy_fin"] = _proy_apilado(it, st, dur_h, cad)
    else:
        g = it.groupby(cad, sort=False)
        ancla = g["act_ini_dt"].transform("first")
        fin = ancla + g["proy_h"].cumsum().pipe(pd.to_timedelta, unit="h")
        it["proy_fin"] = fin
        it["proy_ini"] = fin - dur

    # Sin duración conocida no se inventa un cierre ni un arranque posterior.
    desconocida = (~np.isfinite(it['proy_h'])).groupby(_grp(it, cad)).cummax()
    it.loc[desconocida, ['proy_ini', 'proy_fin']] = pd.NaT

    # Regla del cruce de turno: el bloque siguiente arranca donde cerro el
    # anterior, aunque eso caiga antes de las 20:00 — nunca espera al reloj.
    # No hay nada que corregir aqui: las dos ramas de arriba encadenan
    # fin[n] == ini[n+1] dentro del tramo, asi que la regla ya se cumple por
    # construccion. Lo que sigue la MIDE. Al re-anclar arranca un tramo nuevo y
    # el adelanto del anterior no viaja.

    # Diagnostico del cruce, sobre el cierre proyectado de cada modulo.
    # delta_cruce > 0: el modulo cerro antes del cambio de turno y ese adelanto
    # se le resta al bloque siguiente, que termina en 08:00 - delta_cruce.
    it["cruce_turno"] = _cruce_turno(it["proy_fin"])
    delta = _horas(it["cruce_turno"] - it["proy_fin"])
    it["delta_cruce"] = delta.where(delta > 0)
    # 1 = cierra en turno 1 (antes del cruce), 2 = en turno 2. Es categorico:
    # entero anulable, no float con NaN.
    tf = pd.array(np.where(delta > 0, 1, 2), dtype="Int8")
    tf[delta.isna().to_numpy()] = pd.NA
    it["turno_fin"] = tf
    # cierre de la ventana operacional corrido por la regla: 08:00 - delta
    it["cierre_corrido"] = (it["cruce_turno"] + pd.Timedelta(hours=LARGO_T2)
                            - pd.to_timedelta(it["delta_cruce"].fillna(0.0), unit="h"))

    # cuanto se estiro la medicion respecto de lo proyectado
    it["atraso_h"] = _horas(it["real_fin_dt"] - it["proy_fin"])
    return it


def inactive_table(apilado: pd.DataFrame) -> pd.DataFrame:
    """Filas donde la planilla arrastra un modulo ya en 100% sin apilar."""
    inact = apilado[apilado["estado"] == "INACTIVO"]
    return inact[["fecha", "pad_id", "campana", "modulo", "avance",
                  "vol_acum_final", "estado"]].reset_index(drop=True)


# ─────────────────────────── 7. Wrappers ───────────────────────────

def analyze_db(fecha_min=None, fecha_max=None, boundary=SHIFT1_FRAC,
               recortar_a_masa=True, boundary_src="masa", proy_modo="apilado",
               sem=SEMANA_DEF, tasa=None, avance_ok=None, caso_id=None) -> dict:
    """Fuente SQL Server: volumen de control_apilado_diario y masa por turno de
    Datos_conciliados_of_ver, la tabla versionada que guarda, por dia, la fila
    que cerro el caso de reconciliacion validado. TMS y TMH salen de la misma
    fila y llegan ya reconciliados; 'caso_id' dice de que caso.

    Los dias que no pasaron por un caso validado no tienen masa y no se
    rellenan con la tabla base: salen de la serie.

    recortar_a_masa: recorta la ventana a la interseccion de las dos coberturas,
    para que el dashboard no arrastre dias sin uno u otro dato. Recorta los
    bordes, no los huecos de adentro.

    El resultado trae 'avisos': lo que validacion.py encontro en la entrada y en
    la salida. Los de nivel 'error' ya levantaron; los que quedan son dato
    imposible ('dato') o alcance limitado ('info')."""
    from . import db_source as dbs      # solo esta ruta necesita pyodbc

    opcion("boundary_src", boundary_src, BOUNDARY_SRC)
    opcion("proy_modo", proy_modo, PROY_MODOS)

    if caso_id is not None:
        if fecha_min is None or fecha_max is None:
            raise ValueError("Un Caso requiere su ventana exacta")
        recortar_a_masa = False
    cov = dbs.coverage()
    t0, t1 = cov["tms"]
    # a Timestamp antes de comparar: los limites llegan como str desde el CLI y
    # desde el dashboard, y la cobertura siempre es Timestamp
    fecha_min = pd.Timestamp(fecha_min) if fecha_min is not None else None
    fecha_max = pd.Timestamp(fecha_max) if fecha_max is not None else None
    if recortar_a_masa:
        t0 = max(t0, cov['apilado'][0])
        t1 = min(t1, cov['apilado'][1])
        fecha_min = max(fecha_min, t0) if fecha_min is not None else t0
        fecha_max = min(fecha_max, t1) if fecha_max is not None else t1
        if pd.isna(fecha_min) or pd.isna(fecha_max) or fecha_min > fecha_max:
            raise ValueError('La ventana solicitada no tiene cobertura oficial y de volumen coincidente')

    apilado = dbs.load_apilado(fecha_min, fecha_max)
    masa = (dbs.load_masa(fecha_min, fecha_max) if caso_id is None else
            dbs.load_masa(fecha_min, fecha_max, caso_id=caso_id))
    if caso_id is not None and masa.empty:
        raise ValueError("El Caso no tiene masa publicada validada en su ventana")
    avisos = (v.exigir(v.revisar_apilado(apilado), "control_apilado_diario")
              + v.exigir(v.revisar_masa(masa), "Datos_conciliados_of_ver"))

    apilado = mark_status(apilado)
    st = shift_table(apilado, masa, boundary, boundary_src=boundary_src)
    res = {
        "apilado": apilado,
        "masa": masa,
        "shift_table": st,
        "daily": daily_shift_summary(st, sem),
        "cuadratura": cuadratura_masa(apilado, masa, st),
        "modules": module_summary(st),
        "weekly": weekly_summary(st, sem),
        "itinerario": module_itinerary(apilado, st, proy_modo, sem, tasa,
                                       avance_ok),
        "tasa": tasa or tasa_referencia(st),
        "inactivos": inactive_table(apilado),
        "cobertura": cov,
        "ventana": (fecha_min, fecha_max),
        "boundary_src": boundary_src,
        "proy_modo": proy_modo,
        "sem": sem,
        "avance_ok": AVANCE_OK if avance_ok is None else float(avance_ok),
        "fuente": "sql",
        # los de la ENTRADA se guardan aparte porque sobreviven a cualquier
        # recorte posterior: quien reduzca el resultado a una semana o a una
        # campana vuelve a correr revisar_resultado sobre su subconjunto, pero
        # el dato de origen roto sigue siendo el mismo
        "avisos_entrada": avisos,
    }
    res["avisos"] = avisos + v.revisar_resultado(res)
    return res


def analyze_group(res: dict, pad_id, campana, proy_modo=None, sem=None,
                  tasa=None, avance_ok=None) -> dict:
    """Recorta un resultado de analyze_db() a un pad/campana.

    proy_modo / sem: recalculan itinerario y resumen semanal. Ninguno de los dos
    toca la masa por turno, asi que no hace falta volver a la base de datos.

    Devuelve las mismas claves que analyze_db(); las que no aplican a un
    subconjunto ('cobertura', 'ventana') se heredan del resultado de origen para
    que un consumidor no tenga que saber cual de los dos wrappers lo produjo."""
    sem = sem or res.get("sem", SEMANA_DEF)
    res = recortar_semana(res, sem)
    st = res["shift_table"]
    ap = res["apilado"]
    sub = st[(st["pad_id"] == pad_id) & (st["campana"] == campana)]
    ap_sub = ap[(ap["pad_id"] == pad_id) & (ap["campana"] == campana)]
    modo = proy_modo or res.get("proy_modo", "apilado")
    out = dict(res)
    out.update({
        "pad_id": pad_id, "campana": campana,
        "apilado": ap_sub,
        "shift_table": sub,
        "daily": daily_shift_summary(sub, sem),
        "modules": module_summary(sub),
        "weekly": weekly_summary(sub, sem),
        "sem": sem,
        "proy_modo": modo,
        "itinerario": module_itinerary(ap_sub, sub, modo, sem,
                                       tasa or res.get("tasa"), avance_ok),
        "inactivos": res["inactivos"][
            (res["inactivos"]["pad_id"] == pad_id)
            & (res["inactivos"]["campana"] == campana)],
    })
    out["avisos"] = res.get("avisos_entrada", []) + v.revisar_resultado(out)
    return out


# ─────────────────────────── 8. Resumen de consola ───────────────────────────

def imprimir_resumen(res: dict) -> None:
    """Huella numerica de una corrida, para revisar el motor desde la terminal."""
    st, daily, mods = res["shift_table"], res["daily"], res["modules"]
    sem = res.get("sem", SEMANA_DEF)

    print(f"filas (fecha,modulo) activas  : {len(st)}")
    print(f"dias con apilado              : {daily['fecha'].nunique()}")
    print(f"dias con modulo cruzando turno: {int((daily['n_cruces'] > 0).sum())}")
    print(f"filas INACTIVO (arrastre 100%): {len(res['inactivos'])}")
    print(f"masa turno 1 total            : {daily['masa_turno1'].sum():,.0f} t")
    print(f"masa turno 2 total            : {daily['masa_turno2'].sum():,.0f} t")
    print(f"densidad global               : "
          f"{st['masa_total'].sum() / st['vol_con_masa'].sum():.3f} t/m3")
    if "boundary_medida" in daily.columns:
        nm = int(daily["boundary_medida"].sum())
        print(f"dias con frontera medida      : {nm}/{len(daily)}")
        b = daily.loc[daily["boundary_medida"], "boundary"]
        if len(b):
            print(f"frontera turno1 (medida)      : media {b.mean():.3f}  "
                  f"min {b.min():.3f}  max {b.max():.3f}")
    d = daily["densidad_dia"].replace([np.inf, -np.inf], np.nan).dropna()
    if len(d):
        print(f"densidad diaria (ruido)       : media {d.mean():.3f}  "
              f"CV {v.cv(d):.1%}")
    wk = res.get("weekly")
    if wk is not None and len(wk):
        w = wk.loc[wk["sem_completa"], "densidad_sem"].replace(
            [np.inf, -np.inf], np.nan).dropna()
        if len(w):
            s0, s1 = sem
            print(f"semana de reconstitucion      : {DIAS[s0]} -> {DIAS[s1]}  "
                  f"({dias_por_semana(sem)} dias)")
            print(f"densidad semanal (recon.)     : media {w.mean():.3f}  "
                  f"mediana {w.median():.3f}  CV {v.cv(w):.1%}  "
                  f"n {len(w)} semanas")
    print()
    print("densidad por modulo (top 12 por volumen):")
    print(mods.sort_values("vol_total", ascending=False).head(12)[
        ["pad_id", "campana", "modulo", "n_dias", "vol_total", "masa_total",
         "densidad", "pct_turno1"]].to_string(index=False))


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--corte", default="masa", choices=tuple(BOUNDARY_SRC),
                   help="tecnica para cortar el dia en turnos")
    p.add_argument("--modo", default="apilado", choices=PROY_MODOS,
                   help="cuanto calendario se le concede a la tasa de maquina")
    p.add_argument("--desde", default=None, help="fecha minima YYYY-MM-DD")
    p.add_argument("--hasta", default=None, help="fecha maxima YYYY-MM-DD")
    p.add_argument("--avance", type=float, default=None,
                   help=f"umbral de cierre para encadenar (def. {AVANCE_OK})")
    a = p.parse_args(argv)

    res = analyze_db(fecha_min=a.desde, fecha_max=a.hasta, boundary_src=a.corte,
                     proy_modo=a.modo, avance_ok=a.avance)
    f0, f1 = res["ventana"]
    print("fuente: SQL Server — Apilado_TMS_Real por turno")
    print(f"cobertura volumen : {res['cobertura']['apilado'][0]:%Y-%m-%d} -> "
          f"{res['cobertura']['apilado'][1]:%Y-%m-%d}")
    print(f"cobertura TMS     : {res['cobertura']['tms'][0]:%Y-%m-%d} -> "
          f"{res['cobertura']['tms'][1]:%Y-%m-%d}")
    print(f"ventana analizada : {f0:%Y-%m-%d} -> {f1:%Y-%m-%d}")
    print(f"corte {a.corte} · modo {a.modo} · AVANCE_OK {res['avance_ok']:.3f}")
    print()
    imprimir_resumen(res)
    print()
    print("observaciones:")
    print(v.resumen(res["avisos"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
