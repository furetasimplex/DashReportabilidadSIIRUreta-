"""Reparto secuencial desde los datos iniciales de la campana (metodo Control Sulfuro).

Entradas, todas de la base: masa conciliada por turno (Datos_conciliados_of) y
volumenes diarios por modulo (control_apilado_diario). No lee archivos ni SQL.

Tres ausencias distintas, que no se confunden ni se rellenan:

    sin masa ni volumen   rotopala detenida o sin registro: no se asigna (DIA_SIN_DATOS)
    masa sin volumen      falla de topografia: etiqueta del dia o sin destino
    volumen sin masa      falla de masa: ese volumen sale de la calibracion; no se inventa masa

Hay una sola rotopala: en cada instante la masa va a un unico destino. Un dia con
dos destinos no es un reparto simultaneo, sino uno detras del otro. La fraccion de
volumen fija cuanto recibe cada destino en el dia y el orden fija en que turno cae:
primero el destino que venia trabajando. El orden es una estimacion: la base no
registra la hora del cambio ni si hubo mas de un cambio en el dia.

En cada corte (fin de un Caso oficial) se calibra una densidad:

    rho = (TMH acumulada - TMH ya fijada) / (V de los cerrados + V real del abierto)

Los modulos anteriores al ultimo abierto fijan su meta rho x V y no vuelven a cambiar;
el abierto sigue al corte siguiente. Regla de volumen de los cerrados (R1, medida contra
los libros): VOLUMEN REAL si el modulo no tuvo volumen el dia del corte; ESTIMADO si
tuvo volumen ese dia (sigue en curso) o si hay hueco de topografia entre su inicio y el
inicio del modulo siguiente. Sin umbrales de abandono. El volumen estimado se toma como
estaba al corte: no se usa informacion posterior.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .recalibracion_mr import RecalibrationError

TURNOS = ("A", "B")
PAD_ETIQUETA = (("sulf", 2), ("ox", 1))
# Provisional, no calibrado: masa/volumen diario fuera de este rango se informa.
DENSIDAD_DIA_MIN, DENSIDAD_DIA_MAX = 1.2, 2.6
# Provisionales, no calibrados. Percentil 99 de TMH diaria 2025-2026: 93 mil.
TMH_DIA_MAX = 200_000.0
DESTINO = ["pad_id", "campana_id", "campana"]


def _pad_de_etiqueta(valor):
    texto = str(valor if valor is not None else "").strip().lower()
    for prefijo, pad in PAD_ETIQUETA:
        if texto.startswith(prefijo):
            return pad
    return None


def _orden_destinos(destinos, previos, siguientes):
    """Primero quien venia apilando; ultimo quien sigue al dia siguiente."""
    def clave(destino):
        return (0 if destino in previos else 1, 1 if destino in siguientes else 0, destino)
    return sorted(destinos, key=clave)


def _masa_directa(row, dia, fuente, history, until, filas, aviso, dias_con_masa, ceros_explicitos, directos):
    """Fila de fuente con PAD y campana propios (libro): va directa a su destino, sin repartir por volumen."""
    a, b = float(np.nan_to_num(row.tmh_a)), float(np.nan_to_num(row.tmh_b))
    tmh = a + b
    tms_a, tms_b = float(getattr(row, "tms_a", np.nan)), float(getattr(row, "tms_b", np.nan))
    tms = float(np.nansum([tms_a, tms_b]))
    if np.isfinite(row.tmh_a) and np.isfinite(row.tmh_b) and tmh == 0:
        ceros_explicitos.add(dia)
    if tmh > TMH_DIA_MAX:
        aviso(dia, "MASA_IMPOSIBLE", tmh, tms, f"Supera {TMH_DIA_MAX:,.0f} TMH/dia: excluida del calculo.")
        return
    if tmh <= 0:
        if tms > 0:
            aviso(dia, "TMS_SIN_TMH", 0.0, tms, "Sin TMH no entra a la secuencia, igual que en el libro.")
        return
    pad, visible = int(row.pad_id), int(row.campana)
    if (np.isfinite(tms_a) and tms_a > a + 1e-6) or (np.isfinite(tms_b) and tms_b > b + 1e-6):
        aviso(dia, "LIBRO_TMS_MAYOR_TMH", tmh, tms,
              f"PAD {pad}: el libro trae TMS A/B {tms_a:.1f}/{tms_b:.1f} sobre TMH A/B {a:.1f}/{b:.1f}; "
              "el dia no entra como masa y la TMH no se reconstruye.")
        return
    previa = history.loc[history.pad_id.eq(pad) & history.campana.eq(visible) & history.fecha.le(dia)].sort_values("fecha")
    if previa.empty:
        previa = history.loc[history.pad_id.eq(pad) & history.campana.eq(visible) & history.fecha.le(until)].sort_values("fecha")
    if previa.empty:
        aviso(dia, "MASA_SIN_DESTINO", tmh, tms, f"Libro: PAD {pad} campaña {visible} sin historia de apilado.")
        return
    dias_con_masa.add(dia)
    campana_id = int(previa.campana_id.iloc[-1])
    if not (np.isfinite(tms_a) or np.isfinite(tms_b)):
        aviso(dia, "TMH_SIN_TMS", tmh, 0.0, "La meta usa TMH; la TMS de ese dia queda en cero.")
    directos.setdefault(dia, set()).add(pad)
    if len(directos[dia]) == 2:
        aviso(dia, "DIA_DOS_PAD", tmh, tms, "Masa de ambos PAD en el dia: cada PAD conserva los turnos de su libro.")
    for turno, wet, dry in (("A", a, tms_a), ("B", b, tms_b)):
        if wet > 0 or (np.isfinite(dry) and dry > 0):
            filas.append((dia, turno, pad, campana_id, visible, wet, dry if np.isfinite(dry) else 0.0, fuente))


def despachar(conciliado, history, until):
    """Asigna la masa de cada turno a un destino, con una sola rotopala.

    Devuelve (despacho, excepciones). ``despacho``: fecha/turno/destino/tmh/tms.
    ``excepciones``: una fila por dia y situacion, sin alterar la masa de entrada.
    """
    until = pd.Timestamp(until).normalize()
    h = history.loc[history.fecha.le(until) & history.vol_diario.gt(0)]
    por_dia = {}
    for (dia, *destino), vol in h.groupby(["fecha", *DESTINO]).vol_diario.sum().items():
        por_dia.setdefault(dia, {})[tuple(int(x) for x in destino)] = float(vol)
    dias_con_volumen = sorted(por_dia)
    data = conciliado.loc[conciliado.fecha.le(until)].sort_values("fecha")
    dias_con_masa = set()
    ceros_explicitos = set()
    filas, excepciones = [], []

    def aviso(dia, tipo, tmh=0.0, tms=0.0, detalle=""):
        excepciones.append(dict(fecha=dia, tipo=tipo, tmh=tmh, tms=tms, detalle=detalle))

    directos = {}
    for row in data.itertuples(index=False):
        dia = row.fecha
        fuente = str(getattr(row, "fuente", "") or "")
        if pd.notna(getattr(row, "pad_id", np.nan)):
            _masa_directa(row, dia, fuente, history, until, filas, aviso, dias_con_masa, ceros_explicitos, directos)
            continue
        a, b = float(np.nan_to_num(row.tmh_a)), float(np.nan_to_num(row.tmh_b))
        tmh = a + b
        if np.isfinite(row.tmh_a) and np.isfinite(row.tmh_b) and tmh == 0:
            ceros_explicitos.add(dia)
        tms = float(np.nan_to_num(row.tms))
        if tmh > TMH_DIA_MAX:
            aviso(dia, "MASA_IMPOSIBLE", tmh, tms, f"Supera {TMH_DIA_MAX:,.0f} TMH/dia: excluida del calculo.")
            continue
        if tmh <= 0:
            if tms > 0:
                aviso(dia, "TMS_SIN_TMH", 0.0, tms, "Sin TMH no entra a la secuencia, igual que en el libro.")
            continue
        dias_con_masa.add(dia)
        if not np.isfinite(row.tms):
            aviso(dia, "TMH_SIN_TMS", tmh, 0.0, "La meta usa TMH; la TMS historica de ese dia queda en cero.")
        pad_etiqueta = _pad_de_etiqueta(row.etiqueta)
        destinos = por_dia.get(dia, {})
        i = int(np.searchsorted(dias_con_volumen, dia))
        previos = set(por_dia[dias_con_volumen[i - 1]]) if i > 0 else set()
        posterior = [d for d in dias_con_volumen[i:i + 2] if d > dia]
        siguientes = set(por_dia[posterior[0]]) if posterior else set()
        if not destinos:
            if pad_etiqueta is None:
                aviso(dia, "MASA_SIN_DESTINO", tmh, tms, "Sin volumen ni etiqueta: no se asigna.")
                continue
            candidatos = [d for d in previos if d[0] == pad_etiqueta] or \
                [d for d in siguientes if d[0] == pad_etiqueta]
            if not candidatos:
                aviso(dia, "MASA_SIN_DESTINO", tmh, tms, f"Etiqueta PAD {pad_etiqueta} sin campaña vecina.")
                continue
            aviso(dia, "MASA_SIN_VOLUMEN", tmh, tms, f"Asignada por etiqueta a PAD {pad_etiqueta}.")
            destinos = {sorted(candidatos)[0]: 1.0}
        elif pad_etiqueta is not None and pad_etiqueta not in {d[0] for d in destinos}:
            aviso(dia, "ETIQUETA_CONTRADICE_VOLUMEN", tmh, tms,
                  f"Etiqueta PAD {pad_etiqueta}; volumen en {sorted({d[0] for d in destinos})}. Prevalece el volumen.")
        volumen = sum(destinos.values())
        if len({d[0] for d in destinos}) > 1:
            aviso(dia, "DIA_DOS_PAD", tmh, tms, "Una rotopala: orden estimado, hora del cambio desconocida.")
        elif len(destinos) > 1:
            aviso(dia, "DIA_DOS_CAMPANAS_PAD", tmh, tms, "Orden estimado entre campañas del mismo PAD.")
        densidad = tmh / volumen if volumen > 0 and por_dia.get(dia) else None
        if densidad is not None and not DENSIDAD_DIA_MIN <= densidad <= DENSIDAD_DIA_MAX:
            aviso(dia, "DENSIDAD_DIA_ANOMALA", tmh, tms, f"{densidad:.3f} TMH/m3 en el dia.")
        tasa_seca = tms / tmh
        restante = {"A": a, "B": b}
        for destino in _orden_destinos(destinos, previos, siguientes):
            falta = tmh * destinos[destino] / volumen
            for turno in TURNOS:
                toma = min(falta, restante[turno])
                if toma > 0:
                    filas.append((dia, turno, *destino, toma, toma * tasa_seca, fuente))
                    restante[turno] -= toma
                    falta -= toma
    for dia in dias_con_volumen:
        if dia not in dias_con_masa:
            aviso(dia, "VOLUMEN_SIN_MASA", detalle=f"{sum(por_dia[dia].values()):.0f} m3 sin masa conciliada.")
    if dias_con_volumen:
        for dia in pd.date_range(dias_con_volumen[0], until):
            if dia not in por_dia and dia not in dias_con_masa and dia not in ceros_explicitos:
                if not excepciones or not any(e["fecha"] == dia for e in excepciones):
                    aviso(dia, "DIA_SIN_DATOS", detalle="Sin masa ni volumen: detenida o sin registro.")
    despacho = pd.DataFrame(filas, columns=["fecha", "turno", *DESTINO, "tmh", "tms", "fuente"])
    return despacho, pd.DataFrame(excepciones, columns=["fecha", "tipo", "tmh", "tms", "detalle"])


def chain_targets(supply, modules, cuts, until, dias_sin_volumen=(), dias_sin_masa=()):
    """Metas TMH por modulo y densidades por corte.

    ``modules``: filas fecha/modulo_id/modulo/vol_diario/vol_total_est de la campana.
    ``dias_sin_volumen``: dias con masa y sin volumen registrado. Si caen dentro de
    un modulo, su volumen real esta incompleto y sigue valiendo el estimado (regla R1:
    cerrado sin volumen el dia del corte usa el real; en curso o con hueco, el estimado).
    ``dias_sin_masa``: dias con volumen y sin masa. Ese volumen no entra a la
    densidad ni a la meta: su masa se desconoce y no se reparte la de otros dias.
    Devuelve (metas fijas por modulo_id, id del abierto, registro de calibraciones).
    """
    huecos = {pd.Timestamp(d).normalize() for d in dias_sin_volumen}
    faltantes = {pd.Timestamp(d).normalize() for d in dias_sin_masa}

    def sin_masa(activos, mid):
        filas = activos.loc[activos.modulo_id.eq(mid) & activos.fecha.isin(faltantes)]
        return float(filas.vol_diario.sum())
    until = pd.Timestamp(until).normalize()
    fechas = sorted({pd.Timestamp(c).normalize() for c in cuts if pd.Timestamp(c) <= until} | {until})
    fixed, log, open_id = {}, [], None
    prev_cut, prev_rho = None, None
    for cut in fechas:
        seen = modules.loc[modules.fecha.le(cut)].sort_values("fecha")
        active = seen.loc[seen.vol_diario.gt(0)]
        order = active.drop_duplicates("modulo_id").sort_values(["modulo", "modulo_id"]).modulo_id.tolist()
        # El abierto del corte anterior que no apilo desde entonces, con otro modulo
        # ya en curso, queda con la densidad con que quedo: no se reprecia al reanudar.
        if open_id is not None and open_id not in fixed and prev_cut is not None:
            propio = active.loc[active.modulo_id.eq(open_id)]
            otros = active.loc[active.fecha.gt(prev_cut) & ~active.modulo_id.eq(open_id)]
            hueco_tramo = any(prev_cut < d <= otros.fecha.min() for d in huecos) if not otros.empty else False
            if not propio.fecha.gt(prev_cut).any() and not otros.empty and not hueco_tramo:
                fixed[open_id] = prev_rho * max(0.0, float(propio.vol_diario.sum()) - sin_masa(active, open_id))
        pending = [m for m in order if m not in fixed]
        if not pending:
            continue
        open_id = pending[-1]
        last_est = seen.groupby("modulo_id").vol_total_est.last()
        volumes = {}
        inicio = active.groupby("modulo_id").fecha.min()
        for i, mid in enumerate(pending[:-1]):
            est = last_est.get(mid)
            if est is None or not np.isfinite(est) or est <= 0:
                raise RecalibrationError(f"Módulo {mid}: falta volumen estimado al {cut:%Y-%m-%d}.")
            volumes[mid] = float(est)
            tramo = active.loc[active.modulo_id.eq(mid), "fecha"]
            real_mod = float(active.loc[active.modulo_id.eq(mid), "vol_diario"].sum())
            # El hueco cuenta hasta que parte el modulo siguiente: el volumen faltante
            # puede caer despues del ultimo dia registrado de este modulo.
            siguiente = inicio[pending[i + 1]]
            con_hueco = any(tramo.min() <= d <= siguiente for d in huecos)
            en_curso = tramo.max() == cut  # volumen el dia del corte: sigue cargandose
            if not en_curso and not con_hueco:
                volumes[mid] = real_mod
            volumes[mid] = max(0.0, volumes[mid] - sin_masa(active, mid))
        real = max(0.0, float(active.loc[active.modulo_id.eq(open_id), "vol_diario"].sum()) - sin_masa(active, open_id))
        volume = sum(volumes.values()) + real
        wet = float(supply.loc[supply.fecha.le(cut), "tmh"].sum())
        fixed_wet = sum(fixed.values())
        if volume <= 0:
            if wet - fixed_wet > 1e-6:
                raise RecalibrationError(f"Masa sin volumen ajustable al {cut:%Y-%m-%d}.")
            continue
        rho = (wet - fixed_wet) / volume
        if not np.isfinite(rho) or rho < 0:
            raise RecalibrationError(f"Densidad inválida al {cut:%Y-%m-%d}: la masa fijada supera la acumulada.")
        log.append(dict(fecha_corte=cut, density_tmh_per_m3=rho, tmh_global_campaign=wet,
                        tmh_fixed=fixed_wet, volume_adjustable_real_m3=volume,
                        modulo_abierto=open_id, modulos_fijados=len(volumes)))
        for mid, est in volumes.items():
            fixed[mid] = rho * est
        prev_cut, prev_rho = cut, rho
    if open_id is None or not log:
        raise RecalibrationError("La campaña no tiene módulos con masa y volumen al corte.")
    return fixed, open_id, log
