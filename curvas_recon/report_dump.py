# -*- coding: utf-8 -*-
"""Hoja `Dump` reconciliada del reporte de recuperaciones.

Forma oficial de 6 columnas: ``Fecha``, ``Aporte``, ``Flujo riego dump
[m3/dia]``, ``Flujo salida dump [m3/dia]``, ``Concentracion riego `` y
``Concentracion drenaje``.

Regla (decision del usuario, 5-nov-2026), por Caso oficial:

* ``F`` (factor de drenaje global) = Σ drenaje reconciliado / Σ riego
  reconciliado del dump, tomados de los flujos del run oficial del Caso:
  riego = F77 (alimentacion al dump), drenaje = F51 (DPLS), modelo 125.
* riego reconciliado del dia = riego medido del dia × (Σ riego reconciliado /
  Σ riego medido del Caso). ``recon_resultado_flujo`` solo entrega totales por
  Caso (``masa_medida`` / ``masa_reconciliada``); no hay un caudal diario
  reconciliado del dump, asi que se reparte con la forma del dato medido.
* drenaje del dia = ``F`` × riego reconciliado del dia.
* Aporte [t Cu/dia] = (Qd·Cd − Qr·Cr) / 1000, con Q en m3/dia y C en g/L.
* Concentraciones: medidas (``conc_cu``), sin reconciliar.
* Dias fuera de los Casos oficiales del reporte: fila con la fecha y el resto
  en blanco.

Solo SELECT. Si el run no trae F77/F51 (o el modelo no es el 125) el Caso queda
en blanco y se informa en ``doc['dump_avisos']``; no se inventan datos.
"""
import math

import pandas as pd
from sqlalchemy import text

# Flujos del modelo 125: F77 alimentacion (riego) y F51 DPLS (drenaje) del dump.
FLUJO_RIEGO = 'F77'
FLUJO_DRENAJE = 'F51'
MODELO_DUMP = 'hidrometalurgia_125_v2'


def leer_flujos_dump_caso(run_id):
    """{codigo: (masa_medida, masa_reconciliada)} de F77 y F51 del run oficial.

    SELECT sobre ``recon_resultado_flujo`` (esquema administrado por Django,
    solo lectura). Los codigos ausentes no aparecen en el resultado.
    """
    from .db_pipeline import HIDRO_SCHEMA, get_engine
    query = text(f'''
        SELECT codigo_flujo, masa_medida, masa_reconciliada
        FROM {HIDRO_SCHEMA}.recon_resultado_flujo
        WHERE run_id = :run AND codigo_flujo IN (:riego, :drenaje)
    ''')
    params = {'run': int(run_id), 'riego': FLUJO_RIEGO, 'drenaje': FLUJO_DRENAJE}
    with get_engine().connect() as cn:
        rows = cn.execute(query, params).fetchall()
    out = {}
    for code, medida, reconciliada in rows:
        out[str(code)] = (float(medida) if medida is not None else None,
                          float(reconciliada) if reconciliada is not None else None)
    return out


def _finito(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def factores_caso(flujos):
    """(razon_riego, F, motivo) a partir de los flujos del run.

    ``razon_riego`` = Σ riego reconciliado / Σ riego medido; ``F`` = Σ drenaje
    reconciliado / Σ riego reconciliado. ``motivo`` explica por que no se pudo.
    """
    riego = (flujos or {}).get(FLUJO_RIEGO)
    drenaje = (flujos or {}).get(FLUJO_DRENAJE)
    if not riego or not drenaje:
        faltan = [c for c, v in ((FLUJO_RIEGO, riego), (FLUJO_DRENAJE, drenaje)) if not v]
        return None, None, 'el run no trae %s' % ', '.join(faltan)
    r_med, r_rec = _finito(riego[0]), _finito(riego[1])
    d_rec = _finito(drenaje[1])
    if r_med is None or r_rec is None or d_rec is None:
        return None, None, 'masa reconciliada/medida ausente en F77/F51'
    if r_med <= 0 or r_rec <= 0:
        return None, None, 'riego del dump medido o reconciliado no positivo'
    if d_rec < 0:
        return None, None, 'drenaje reconciliado del dump negativo'
    return r_rec / r_med, d_rec / r_rec, None


def dump_reconciliado(medidos, runs, day_caso=None, lector=None):
    """Filas de la hoja Dump con riego y drenaje reconciliados por Caso.

    ``medidos`` son las filas de ``report_metodo.leer_dump`` (caudales y
    concentraciones medidos). ``runs`` es el dict de ``construir_doc``.
    Devuelve ``(filas, meta, avisos)``; ``meta`` guarda por Caso el factor ``F``
    y la razon de riego usados.
    """
    lector = lector or leer_flujos_dump_caso
    medidos = {pd.Timestamp(r['fecha']).normalize(): r for r in (medidos or [])}
    if not medidos:
        return [], {}, []
    # Cada dia pertenece a un solo caso (el primero que lo cubre).
    dia_caso = dict(day_caso or {})
    if not dia_caso:
        for cid in sorted(runs):
            d, we = pd.Timestamp(runs[cid]['ws']).normalize(), pd.Timestamp(runs[cid]['we']).normalize()
            while d <= we:
                dia_caso.setdefault(d, cid)
                d += pd.Timedelta(days=1)
    meta, avisos, factores = {}, [], {}
    for cid in sorted(runs):
        caso = runs[cid].get('caso') or {}
        modelo = caso.get('modelo_codigo')
        if modelo is not None and str(modelo) != MODELO_DUMP:
            motivo = 'modelo %s sin mapping de flujos del dump' % modelo
            razon = factor = None
        elif caso.get('run_id') is None:
            motivo = 'Caso sin run oficial'
            razon = factor = None
        else:
            razon, factor, motivo = factores_caso(lector(caso['run_id']))
        factores[cid] = (razon, factor)
        meta[cid] = dict(run=caso.get('run_id'), razon_riego=razon, factor_drenaje=factor,
                         motivo=motivo)
        if motivo:
            avisos.append('Dump: Caso %s en blanco (%s).' % (cid, motivo))

    primero = min(dia_caso) if dia_caso else min(medidos)
    ultimo = max(max(medidos), max(dia_caso) if dia_caso else max(medidos))
    filas = []
    for dia in pd.date_range(primero, ultimo, freq='D'):
        fila = dict(fecha=dia, aporte=None, flujo_riego=None, flujo_salida=None,
                    cu_feed=None, cu_drenaje=None)
        cid = dia_caso.get(dia)
        medido = medidos.get(dia)
        razon, factor = factores.get(cid, (None, None))
        if cid is not None and medido is not None and razon is not None:
            q_med = _finito(medido.get('flujo_riego'))
            cr, cd = _finito(medido.get('cu_feed')), _finito(medido.get('cu_drenaje'))
            if q_med is not None and q_med >= 0:
                qr = q_med * razon
                qd = factor * qr
                fila.update(flujo_riego=qr, flujo_salida=qd, cu_feed=cr, cu_drenaje=cd)
                if cr is not None and cd is not None:
                    fila['aporte'] = (qd * cd - qr * cr) / 1000.0
        filas.append(fila)
    return filas, meta, avisos
