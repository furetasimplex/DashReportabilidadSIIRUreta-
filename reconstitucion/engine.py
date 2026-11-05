"""Reparto de masa apilada por turno y modulo — motor simple.

Regla unica: la masa se reparte igual que el volumen.

    fraccion de masa (turno, modulo) = fraccion de volumen (turno, modulo)

La masa seca se reparte por fraccion de volumen dentro del dia. El timeline
horario se reconstruye por separado desde TMH acumulada de totalizadores
validados de 10 segundos; A/B es un respaldo declarado de menor resolucion.

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
    AVANCE_CIERRE, BOUNDARY_SRC, DIAS, DIAS_SEM_MIN, LARGO_T1,
    SEMANA_DEF, SHIFT1_FRAC, SHIFT1_START, opcion,
)


class MissingCaseMassError(ValueError):
    """El Caso solicitado no tiene masa validada en su ventana publicada."""

# Columnas que shift_table necesita si o si en el frame de masa. El resto
# (boundary, boundary_h, H_op_src, turnos_ok) son opcionales y cada una declara
# su valor por defecto donde se lee.
MASA_OBLIGATORIAS = ("fecha", "TMH", "TMS", "H_op")

# Apertura del dia operacional (08:00), reusada donde se ancla una ventana o se
# construye un timestamp a partir de una fecha sin hora.
_OFF_08 = pd.Timedelta(hours=SHIFT1_START)






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

    AVANCE_CIERRE identifica los módulos ya cerrados que la planilla arrastra."""
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
    del resumen semanal. Esta densidad no determina el horario del modulo.

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
FRAMES_FECHADOS = ("apilado", "masa", "shift_table", "inactivos", "cuadratura", "masa_por_pad", "cuadratura_pad", "module_timeline", "nuevo_itinerario", "asignaciones", "sin_asignar")


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
    timeline = res.get("module_timeline", res.get("nuevo_itinerario"))
    if timeline is not None and len(timeline):
        out["module_timeline"] = timeline[mascara(timeline)].reset_index(drop=True)
        out["nuevo_itinerario"] = out["module_timeline"]
        out["itinerario"] = out["module_timeline"]
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
    densidad, una semana lo diluye. La densidad semanal es un resumen observado;
    no se usa para reconstruir las horas de cambio de módulo.

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
    # densidad informativa; no determina el horario del modulo
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














# ─────────────────────── 6. Itinerario por modulo ───────────────────────











def inactive_table(apilado: pd.DataFrame) -> pd.DataFrame:
    """Filas donde la planilla arrastra un modulo ya en 100% sin apilar."""
    inact = apilado[apilado["estado"] == "INACTIVO"]
    return inact[["fecha", "pad_id", "campana", "modulo", "avance",
                  "vol_acum_final", "estado"]].reset_index(drop=True)


# ─────────────────────────── 7. Wrappers ───────────────────────────

def analyze_db(fecha_min=None, fecha_max=None, boundary=SHIFT1_FRAC,
               recortar_a_masa=True, boundary_src="masa", sem=SEMANA_DEF,
               caso_id=None, caso=None, use_intraday=False, metodo=None) -> dict:
    """Fuente SQL Server: volumen de control_apilado_diario y masa por turno de
    Datos_conciliados_of_ver, la tabla versionada que guarda, por dia, la fila
    que cerro el caso de reconciliacion validado. TMS y TMH salen de la misma
    fila y llegan ya reconciliados; 'caso_id' dice de que caso.

    Los dias que no pasaron por un caso validado no tienen masa y no se
    rellenan con la tabla base: salen de la serie.

    recortar_a_masa: recorta la ventana a la interseccion de las dos coberturas,
    para que el dashboard no arrastre dias sin uno u otro dato. Recorta los
    bordes, no los huecos de adentro.

    metodo (solo con ``caso``): 'volumen' (por defecto, vigente) o 'recalibrada' (en validacion), que reconstituye por
    densidad humeda recalibrada y asignacion secuencial por turno
    (docs/METODOLOGIA_RECONSTITUCION_DENSIDAD_RECALIBRADA.md); 'volumen' conserva
    el reparto por fraccion de volumen.

    El resultado trae 'avisos': lo que validacion.py encontro en la entrada y en
    la salida. Los de nivel 'error' ya levantaron; los que quedan son dato
    imposible ('dato') o alcance limitado ('info')."""
    from . import db_source as dbs      # solo esta ruta necesita pyodbc

    opcion("boundary_src", boundary_src, BOUNDARY_SRC)
    if metodo is not None and metodo not in METODOS_RECONSTITUCION:
        raise ValueError(f"metodo de reconstitucion invalido: {metodo!r}; "
                         f"opciones {METODOS_RECONSTITUCION}")
    if caso is None and metodo == 'recalibrada':
        raise ValueError("La reconstitucion recalibrada requiere un Caso oficial")
    if caso is not None:
        if (caso_id is not None and int(caso_id) != int(caso['id'])) or (
                pd.Timestamp(fecha_min).normalize() != pd.Timestamp(caso['fecha_inicio']).normalize()
                or pd.Timestamp(fecha_max).normalize() != pd.Timestamp(caso['fecha_fin']).normalize()):
            raise ValueError('El Caso y la ventana de reconstitución deben coincidir')
        if (metodo or METODO_DEFECTO) == 'volumen':
            return _analyze_flow_case(caso, sem, use_intraday)
        return _analyze_recalibrado(caso, sem, use_intraday)

    if caso_id is not None and (fecha_min is None or fecha_max is None):
        raise ValueError("Un Caso requiere su ventana exacta")
    if caso_id is not None:
        recortar_a_masa = False
    # a Timestamp antes de comparar: los limites llegan como str desde el CLI y
    # desde el dashboard, y la cobertura siempre es Timestamp
    fecha_min = pd.Timestamp(fecha_min) if fecha_min is not None else None
    fecha_max = pd.Timestamp(fecha_max) if fecha_max is not None else None
    if caso_id is not None:
        # El Caso ya define la ventana. Leer su masa primero evita consultar
        # cobertura global, volumen y ticks si no publicó filas en ese período.
        masa = dbs.load_masa(fecha_min, fecha_max, caso_id=caso_id)
        if masa.empty:
            raise MissingCaseMassError("El Caso no tiene masa publicada validada en su ventana")
        apilado = dbs.load_apilado(fecha_min, fecha_max)
        # Bordes observados en los frames cargados; no afirma cobertura interna.
        cov = {
            'apilado': (pd.Timestamp(apilado.fecha.min()).normalize(),
                        pd.Timestamp(apilado.fecha.max()).normalize()) if not apilado.empty else (pd.NaT, pd.NaT),
            'tms': (pd.Timestamp(masa.fecha.min()).normalize(),
                    pd.Timestamp(masa.fecha.max()).normalize()),
        }
    else:
        cov = dbs.coverage()
        t0, t1 = cov["tms"]
        if recortar_a_masa:
            t0 = max(t0, cov['apilado'][0])
            t1 = min(t1, cov['apilado'][1])
            fecha_min = max(fecha_min, t0) if fecha_min is not None else t0
            fecha_max = min(fecha_max, t1) if fecha_max is not None else t1
            if pd.isna(fecha_min) or pd.isna(fecha_max) or fecha_min > fecha_max:
                raise ValueError('La ventana solicitada no tiene cobertura oficial y de volumen coincidente')
        apilado = dbs.load_apilado(fecha_min, fecha_max)
        masa = dbs.load_masa(fecha_min, fecha_max)
    avisos = (v.exigir(v.revisar_apilado(apilado), "control_apilado_diario")
              + v.exigir(v.revisar_masa(masa), "Datos_conciliados_of_ver"))

    apilado = mark_status(apilado)
    st = shift_table(apilado, masa, boundary, boundary_src=boundary_src)
    # Legacy SQL-backed result uses observed wet profile. Missing profile is an
    # explicit failure.
    from . import modelo_flujos as mf
    from .module_timeline import build_module_timeline
    profile = mf.load_profile(fecha_min or apilado.fecha.min(),
                              fecha_max or apilado.fecha.max())
    intraday = None
    if use_intraday:
        intraday, intraday_notice = _optional_intraday(fecha_min, fecha_max)
        if intraday_notice is not None:
            avisos.append(intraday_notice)
    timeline = build_module_timeline(apilado, st, profile, intraday=intraday)
    res = {
        "apilado": apilado,
        "masa": masa,
        "shift_table": st,
        "daily": daily_shift_summary(st, sem),
        "cuadratura": cuadratura_masa(apilado, masa, st),
        "modules": module_summary(st),
        "weekly": weekly_summary(st, sem),
        "itinerario": timeline,
        "module_timeline": timeline,
        "perfil_turnos": profile.copy(),
        "nuevo_itinerario": timeline,
        "inactivos": inactive_table(apilado),
        "cobertura": cov,
        "ventana": (fecha_min, fecha_max),
        "boundary_src": boundary_src,
        "sem": sem,
        "fuente": "sql",
        # los de la ENTRADA se guardan aparte porque sobreviven a cualquier
        # recorte posterior: quien reduzca el resultado a una semana o a una
        # campana vuelve a correr revisar_resultado sobre su subconjunto, pero
        # el dato de origen roto sigue siendo el mismo
        "avisos_entrada": avisos,
    }
    res["avisos"] = avisos + v.revisar_resultado(res)
    return res


METODOS_RECONSTITUCION = ('recalibrada', 'volumen')
# La recalibrada queda opt-in hasta validarla contra la DB real (columnas
# tmh_apilado / vol_total_est y orden operacional sin confirmar).
METODO_DEFECTO = 'volumen'


def _optional_intraday(start, end):
    """10-second observations improve the clock but are not required for A/B."""
    from .wet_profile import load_intraday_profile
    try:
        frame = load_intraday_profile(start, end)
        if frame is not None and not frame.empty:
            return frame, None
    except Exception:
        # Only this optional source is caught. Never expose SQL/connection text.
        pass
    notice = v.Aviso('info', 'perfil_intraturno_no_disponible',
        'Perfil de 10 s no disponible; horario estimado desde TMH A/B con '
        'interpolacion uniforme de 12 h. Consultar resolucion de cada modulo.')
    return None, notice


def _analyze_flow_case(caso, sem, use_intraday=False):
    """Official model solids, independently conserved for each PAD."""
    from . import db_source as dbs, modelo_flujos as mf
    start, end = (pd.Timestamp(caso[k]).normalize() for k in ('fecha_inicio', 'fecha_fin'))
    import time
    timings = {}
    started = time.perf_counter()
    targets = mf.load_targets(caso)
    timings['targets'] = time.perf_counter()-started
    started = time.perf_counter()
    ap = mark_status(dbs.load_apilado(start, end))
    timings['apilado'] = time.perf_counter()-started
    avisos = v.exigir(v.revisar_apilado(ap), 'control_apilado_diario')
    if not ap.vol_diario.gt(0).any():
        raise mf.FlowCaseError('El Caso no tiene volumen de apilado para distribuir sus flujos.')
    from concurrent.futures import ThreadPoolExecutor

    def read_source(loader):
        began = time.perf_counter()
        return loader(start, end), time.perf_counter()-began

    # Independent SELECTs, each using its own pooled connection. No solver,
    # shared SQL transaction or mutable reconciliation state runs in workers.
    with ThreadPoolExecutor(max_workers=3 if use_intraday else 2) as workers:
        profile_job = workers.submit(read_source, mf.load_profile)
        hours_job = workers.submit(read_source, mf.load_hours)
        if use_intraday:
            wet_job = workers.submit(read_source, _optional_intraday)
        profile, timings['profile'] = profile_job.result()
        hours, timings['hours'] = hours_job.result()
        intraday = None
        if use_intraday:
            (intraday, intraday_notice), timings['intraday'] = wet_job.result()
            if intraday_notice is not None:
                avisos.append(intraday_notice)
    by_pad, base, balance = mf.distribute_profile(profile, ap, targets, caso)
    hours['fecha'] = pd.to_datetime(hours.fecha).dt.normalize()
    by_pad = by_pad.merge(hours, on='fecha', how='left', validate='many_to_one')
    by_pad['H_op_src'] = np.where(by_pad.H_op.notna(), 'torre', 'n/d')
    mass = by_pad.groupby('fecha', as_index=False)[['TMS','TMS_T1','TMS_T2']].sum()
    mass = mass.merge(base[['fecha','TMH','TMS_base']], on='fecha', validate='one_to_one')
    mass = mass.merge(hours, on='fecha', how='left', validate='one_to_one')
    mass['H_op_src'] = np.where(mass.H_op.notna(), 'torre', 'n/d')
    mass['boundary'] = mass.TMS_T1.div(mass.TMS).where(mass.TMS.gt(0), 0.0)
    mass['boundary_normalizada'] = True
    mass['turnos_ok'] = mass.TMS_T1.gt(0) & mass.TMS_T2.gt(0)
    mass['fuente_masa'] = 'FLUJOS_CASO_DISTRIBUIDOS'
    mass['caso_id'] = int(caso['id'])
    mass['reporte_run_id'] = str(caso['run_id'])
    avisos += v.exigir(v.revisar_masa(mass), 'Perfil distribuido del Caso')
    parts, pad_checks = [], []
    for pad in targets:
        pad_ap = ap[ap.pad_id.eq(pad)]
        pad_mass = by_pad[by_pad.pad_id.eq(pad)].copy()
        if pad_mass.empty:
            continue
        # There is no independently reconciled daily/shift mass: its boundary
        # comes from the measured conveyor profile, with a single PAD factor.
        part = shift_table(pad_ap, pad_mass, boundary_src='masa')
        if not part.empty:
            part['boundary_medida'] = False
            part['frontera_tipo'] = 'distribuida_del_caso'
            parts.append(part)
        check = cuadratura_masa(pad_ap, pad_mass, part)
        check['pad_id'] = pad
        pad_checks.append(check)
    if not parts:
        raise mf.FlowCaseError('No hay módulos activos para distribuir los flujos del Caso.')
    st = pd.concat(parts, ignore_index=True)
    global_mass = mass.set_index('fecha')
    volumes = ap[ap.estado.eq('ACTIVO')].groupby('fecha').vol_diario.sum()
    counts = ap[ap.estado.eq('ACTIVO')].groupby('fecha').size()
    # Global daily columns are repeated on module rows and aggregated with
    # first(); keep them global even when the mass split is PAD-specific.
    for output, source in [('TMS_dia','TMS'), ('masa_dia','TMS'), ('TMH_dia','TMH'),
                           ('H_op','H_op'), ('H_op_src','H_op_src')]:
        st[output] = st.fecha.map(global_mass[source])
    st['vol_dia_total'] = st.fecha.map(volumes)
    st['n_modulos_dia'] = st.fecha.map(counts)
    # Hours and percentages retain the observed global volume share; mass is
    # conserved separately within each PAD rather than crossing to another PAD.
    st['frac_vol'] = st.vol_diario/st.vol_dia_total
    from .module_timeline import build_module_timeline
    timeline = build_module_timeline(ap, st, profile, intraday=intraday)
    for pad, row in balance.set_index('pad_id').iterrows():
        allocated = st.loc[st.pad_id.eq(pad), 'masa_total'].sum()
        if not np.isclose(allocated, row.objetivo_t, rtol=1e-10, atol=1e-6):
            raise mf.FlowCaseError(f'PAD {pad}: los módulos no cierran con el flujo reconciliado.')
    res = dict(apilado=ap, masa=mass, masa_por_pad=by_pad, shift_table=st,
        daily=daily_shift_summary(st, sem), cuadratura=cuadratura_masa(ap, mass, st),
        cuadratura_pad=pd.concat(pad_checks, ignore_index=True), balance_flujos=balance,
        modules=module_summary(st), weekly=weekly_summary(st, sem),
        perfil_turnos=profile.copy(), horas_turnos=hours.copy(),
        itinerario=timeline, module_timeline=timeline,
        nuevo_itinerario=timeline, inactivos=inactive_table(ap),
        cobertura={'apilado': (ap.fecha.min(), ap.fecha.max()), 'tms': (mass.fecha.min(), mass.fecha.max())},
        ventana=(start,end), boundary_src='masa', sem=sem,
        fuente='sql',
        fuente_modelo=dict(caso), avisos_entrada=avisos, _phase_seconds=timings)
    avisos.append(v.Aviso('info','perfil_caso_distribuido',
        'Totales reconciliados por PAD; distribución diaria y por turno desde el perfil operativo. '
        'Los turnos distribuidos no son mediciones reconciliadas independientes.'))
    res['avisos'] = avisos + v.revisar_resultado(res)
    return res


def _analyze_recalibrado(caso, sem, use_intraday=False):
    """Caso oficial reconstituido por densidad humeda recalibrada (PAD+campana).

    Historia desde el nacimiento de cada campana; TMS reconciliada F18/F19 del
    Caso distribuida por turno dentro de la ventana; modulos fijados
    preservados; asignacion secuencial por turno. Solo SELECT."""
    from . import db_source as dbs, modelo_flujos as mf
    from . import recalibracion_db as rdb, recalibracion_caso as rcc
    from . import recalibracion as rc
    start, end = (pd.Timestamp(caso[k]).normalize() for k in ('fecha_inicio', 'fecha_fin'))
    import time
    timings = {}
    started = time.perf_counter()
    targets = mf.load_targets(caso)
    timings['targets'] = time.perf_counter()-started
    started = time.perf_counter()
    ap = mark_status(dbs.load_apilado(start, end))
    timings['apilado'] = time.perf_counter()-started
    avisos = v.exigir(v.revisar_apilado(ap), 'control_apilado_diario')
    if not ap.vol_diario.gt(0).any():
        raise mf.FlowCaseError('El Caso no tiene volumen de apilado para distribuir sus flujos.')
    started = time.perf_counter()
    nacim = rdb.load_nacimientos(start, end)
    desde = min([start] + ([pd.Timestamp(nacim.nacimiento.min())] if len(nacim) else []))
    hist = dbs.load_apilado(desde, end) if desde < start else ap
    timings['historia'] = time.perf_counter()-started
    from concurrent.futures import ThreadPoolExecutor

    def read_source(loader, *args):
        began = time.perf_counter()
        return loader(*args), time.perf_counter()-began

    with ThreadPoolExecutor(max_workers=2) as workers:
        profile_job = workers.submit(read_source, mf.load_profile, desde, end)
        hours_job = workers.submit(read_source, mf.load_hours, start, end)
        profile_hist, timings['profile'] = profile_job.result()
        hours, timings['hours'] = hours_job.result()
    profile_hist = profile_hist.copy()
    profile_hist['fecha'] = pd.to_datetime(profile_hist.fecha).dt.normalize()
    profile = profile_hist[profile_hist.fecha.between(start, end)].copy()
    by_pad, base, balance = mf.distribute_profile(profile, ap, targets, caso)
    started = time.perf_counter()
    campaigns = ap.loc[ap.vol_diario.gt(0)]
    cids = campaigns['campana_id'].dropna().unique() if 'campana_id' in campaigns else campaigns['campana'].unique()
    catalogo = rdb.load_modulos()
    fijados = rdb.load_modulos_fijados(cids)
    timings['modulos'] = time.perf_counter()-started
    out = rcc.reconstituir(
        hist, profile_hist, by_pad[['fecha', 'pad_id', 'TMS_T1', 'TMS_T2']], start, end,
        fijados=fijados, modulos_cat=catalogo)
    avisos = avisos + list(out['avisos'])
    hours['fecha'] = pd.to_datetime(hours.fecha).dt.normalize()
    by_pad = by_pad.merge(hours, on='fecha', how='left', validate='many_to_one')
    by_pad['H_op_src'] = np.where(by_pad.H_op.notna(), 'torre', 'n/d')
    mass = by_pad.groupby('fecha', as_index=False)[['TMS', 'TMS_T1', 'TMS_T2']].sum()
    mass = mass.merge(base[['fecha', 'TMH', 'TMS_base']], on='fecha', validate='one_to_one')
    mass = mass.merge(hours, on='fecha', how='left', validate='one_to_one')
    mass['H_op_src'] = np.where(mass.H_op.notna(), 'torre', 'n/d')
    mass['boundary'] = mass.TMS_T1.div(mass.TMS).where(mass.TMS.gt(0), 0.0)
    mass['boundary_normalizada'] = True
    mass['turnos_ok'] = mass.TMS_T1.gt(0) & mass.TMS_T2.gt(0)
    mass['fuente_masa'] = rcc.FUENTE_MASA
    mass['caso_id'] = int(caso['id'])
    mass['reporte_run_id'] = str(caso['run_id'])
    avisos += v.exigir(v.revisar_masa(mass), 'Perfil distribuido del Caso')
    st = out['shift_table']
    global_mass = mass.set_index('fecha')
    st['H_op'] = st.fecha.map(global_mass['H_op'])
    st['H_op_src'] = st.fecha.map(global_mass['H_op_src'])
    pad_checks = []
    for pad in targets:
        pad_ap = ap[ap.pad_id.eq(pad)]
        pad_mass = by_pad[by_pad.pad_id.eq(pad)]
        if pad_mass.empty:
            continue
        check = cuadratura_masa(pad_ap, pad_mass, st[st.pad_id.eq(pad)])
        check['pad_id'] = pad
        pad_checks.append(check)
    if st.empty:
        raise mf.FlowCaseError('No hay módulos activos para distribuir los flujos del Caso.')
    for pad, row in balance.set_index('pad_id').iterrows():
        allocated = st.loc[st.pad_id.eq(pad), 'masa_total'].sum()
        if not np.isclose(allocated, row.objetivo_t, rtol=1e-10, atol=1e-6):
            raise mf.FlowCaseError(f'PAD {pad}: los módulos no cierran con el flujo reconciliado.')
    sin = out['sin_asignar']
    ventana_sin = sin.loc[sin.fecha.between(start, end)]
    if len(ventana_sin) and (ventana_sin.tmh.sum() > rc.TOL_ABS):
        raise mf.FlowCaseError(
            f'{ventana_sin.tmh.sum():,.3f} TMH de la ventana no son asignables a ningún módulo '
            '(sin volumen de destino o metas agotadas); el Caso no cierra de forma exhaustiva.')
    if len(sin):
        avisos.append(v.Aviso('dato', 'masa_sin_asignar_historia',
            f'{sin.tmh.sum():,.3f} TMH de la historia previa no asignables a un destino; '
            'se reportan en sin_asignar y no se trasladan a otra fecha.', int(len(sin))))
    if use_intraday:
        avisos.append(v.Aviso('info', 'perfil_10s_no_usado',
            'La reconstitución recalibrada no usa el perfil de 10 s; no se presenta con esa precisión.'))
    avisos.append(v.Aviso('info', 'horario_estimado_12h',
        'Horas de cambio estimadas con interpolación uniforme de 12 h por turno sobre la TMH '
        'asignada; no son observaciones.'))
    rho = ', '.join(f"PAD {int(r.pad_id)}/C{int(r.campana)}: "
                    f"{'n/a' if pd.isna(r.rho_h) else f'{r.rho_h:.4f}'} TMH/m³"
                    for r in out['grupos'].itertuples())
    avisos.append(v.Aviso('info', 'densidad_humeda_recalibrada',
        f'Densidad húmeda recalibrada por PAD/campaña: {rho}.'))
    avisos.append(v.Aviso('info', 'perfil_caso_distribuido',
        'Totales reconciliados por PAD; distribución diaria y por turno desde el perfil operativo. '
        'Los turnos distribuidos no son mediciones reconciliadas independientes.'))
    timeline = out['timeline']
    res = dict(apilado=ap, masa=mass, masa_por_pad=by_pad, shift_table=st,
        asignaciones=out['asignaciones'], sin_asignar=sin,
        recalibracion_grupos=out['grupos'], recalibracion_modulos=out['modulos'],
        metodo_reconstitucion=rcc.METODO, historia_desde=desde,
        daily=daily_shift_summary(st, sem), cuadratura=cuadratura_masa(ap, mass, st),
        cuadratura_pad=pd.concat(pad_checks, ignore_index=True), balance_flujos=balance,
        modules=module_summary(st), weekly=weekly_summary(st, sem),
        perfil_turnos=profile.copy(), horas_turnos=hours.copy(),
        itinerario=timeline, module_timeline=timeline,
        nuevo_itinerario=timeline, inactivos=inactive_table(ap),
        cobertura={'apilado': (ap.fecha.min(), ap.fecha.max()), 'tms': (mass.fecha.min(), mass.fecha.max())},
        ventana=(start, end), boundary_src='masa', sem=sem,
        fuente='sql', fuente_modelo=dict(caso), avisos_entrada=avisos, _phase_seconds=timings)
    res['avisos'] = avisos + v.revisar_resultado(res)
    return res


def analyze_group(res: dict, pad_id, campana, sem=None) -> dict:
    """Recorta un resultado de analyze_db() a un pad/campana.

    The module timeline is filtered from the source result, never rebuilt.

    Devuelve las mismas claves que analyze_db(); las que no aplican a un
    subconjunto ('cobertura', 'ventana') se heredan del resultado de origen para
    que un consumidor no tenga que saber cual de los dos wrappers lo produjo."""
    sem = sem or res.get("sem", SEMANA_DEF)
    res = recortar_semana(res, sem)
    st = res["shift_table"]
    ap = res["apilado"]
    sub = st[(st["pad_id"] == pad_id) & (st["campana"] == campana)]
    ap_sub = ap[(ap["pad_id"] == pad_id) & (ap["campana"] == campana)]
    out = dict(res)
    timeline = res.get('module_timeline', res.get('nuevo_itinerario'))
    if timeline is not None:
        dates = set(pd.to_datetime(sub.fecha).dt.normalize()) if not sub.empty else set()
        timeline_sub = timeline.loc[
            timeline.pad_id.eq(pad_id) & timeline.campana.eq(campana) &
            pd.to_datetime(timeline.fecha).dt.normalize().isin(dates)
        ].copy().reset_index(drop=True)
    else:
        timeline_sub = pd.DataFrame()
    out.update({
        "pad_id": pad_id, "campana": campana,
        "apilado": ap_sub,
        "shift_table": sub,
        "daily": daily_shift_summary(sub, sem),
        "modules": module_summary(sub),
        "weekly": weekly_summary(sub, sem),
        "sem": sem,
        "itinerario": timeline_sub,
        "module_timeline": timeline_sub,
        "nuevo_itinerario": timeline_sub,
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
    p.add_argument("--desde", default=None, help="fecha minima YYYY-MM-DD")
    p.add_argument("--hasta", default=None, help="fecha maxima YYYY-MM-DD")
    a = p.parse_args(argv)

    res = analyze_db(fecha_min=a.desde, fecha_max=a.hasta, boundary_src=a.corte)
    f0, f1 = res["ventana"]
    print("fuente: SQL Server — Apilado_TMS_Real por turno")
    print(f"cobertura volumen : {res['cobertura']['apilado'][0]:%Y-%m-%d} -> "
          f"{res['cobertura']['apilado'][1]:%Y-%m-%d}")
    print(f"cobertura TMS     : {res['cobertura']['tms'][0]:%Y-%m-%d} -> "
          f"{res['cobertura']['tms'][1]:%Y-%m-%d}")
    print(f"ventana analizada : {f0:%Y-%m-%d} -> {f1:%Y-%m-%d}")
    print(f"corte {a.corte}")
    print()
    imprimir_resumen(res)
    print()
    print("observaciones:")
    print(v.resumen(res["avisos"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
