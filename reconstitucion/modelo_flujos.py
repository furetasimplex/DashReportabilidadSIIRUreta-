"""Read official solid-flow totals and distribute them over an operational profile.

Run masses and copper fines are already tonnes. The daily/shift distribution is
derived from the measured conveyor profile, not a daily reconciled observation.
"""
import math
import numpy as np
import pandas as pd
from sqlalchemy import text

from . import db_source as dbs

MODELS = {
    'hidrometalurgia_125_v2': ('v2', 125, {1: 'F18', 2: 'F19'}),
    'hidrometalurgia_120_completo': ('v1', 120, {1: 'F15', 2: 'F14'}),
}


class FlowCaseError(ValueError):
    """Safe, actionable error for the selected official Case."""


def load_targets(caso, engine=None, hidro_schema=None):
    code = caso.get('modelo_codigo')
    if code not in MODELS:
        raise FlowCaseError('Modelo sin mapeo de masa apilada para reconstitución.')
    version, count, mapping = MODELS[code]
    if caso.get('modelo_version') != version or caso.get('total_flujos') != count:
        raise FlowCaseError('Versión o número de flujos incompatible con el modelo del Caso.')
    if hidro_schema is None:
        from curvas_recon.db_pipeline import HIDRO_SCHEMA
        hidro_schema = HIDRO_SCHEMA
    # Schema originates from the host configuration, never from browser state.
    import re
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?', hidro_schema):
        raise ValueError('Esquema hidro inválido')
    params = {'case': int(caso['id']), 'run': int(caso['run_id'])}
    eng = engine or dbs.get_engine()
    with eng.connect() as conn:
        current = conn.execute(text(f'''
            SELECT c.fecha_inicio, c.fecha_fin, m.codigo, m.version, m.total_flujos
            FROM {hidro_schema}.recon_caso c
            JOIN {hidro_schema}.recon_caso_oficial o ON o.caso_id = c.id
            JOIN {hidro_schema}.recon_solver_run r
              ON r.id = o.solver_run_id AND r.caso_id = c.id
            JOIN {hidro_schema}.recon_modelo m ON m.id = c.modelo_id
            WHERE c.id = :case AND r.id = :run AND r.estado = 'success'
        '''), params).first()
        if current is None or tuple(map(str, current[2:4])) != (code, version) or int(current[4]) != count:
            raise FlowCaseError('El run oficial del Caso cambió. Actualiza la lista de Casos.')
        start, end = (pd.Timestamp(v).normalize() for v in current[:2])
        if (start != pd.Timestamp(caso['fecha_inicio']).normalize()
                or end != pd.Timestamp(caso['fecha_fin']).normalize()):
            raise FlowCaseError('El período del Caso cambió. Actualiza la lista de Casos.')
        rows = conn.execute(text(f'''
            SELECT codigo_flujo, masa_medida, masa_reconciliada,
                   fino_cu_medido, fino_cu_reconciliado
            FROM {hidro_schema}.recon_resultado_flujo
            WHERE run_id = :run AND codigo_flujo IN (:ox, :su)
        '''), dict(params, ox=mapping[1], su=mapping[2])).fetchall()
    by_code = {r[0]: r for r in rows}
    if len(rows) != 2 or set(by_code) != set(mapping.values()):
        raise FlowCaseError('El run oficial no contiene ambos flujos de masa apilada.')
    targets = {}
    for pad, flow in mapping.items():
        vals = by_code[flow][1:]
        if any(v is None or not math.isfinite(float(v)) or float(v) < 0 for v in vals):
            raise FlowCaseError('Masa o fino de apilado ausente, negativo o no finito en el run.')
        targets[pad] = dict(zip(('masa_medida', 'masa_reconciliada',
                                'fino_cu_medido', 'fino_cu_reconciliado'), map(float, vals)), flujo=flow)
    return targets


def load_profile(start, end, engine=None):
    """Same TMH selection and humidity formula used by the solid-flow source.

    Closed days since 2026-09-01 use the resolved PI/TUM conveyor view. Historic
    and open days use the operational PI view. Missing readings stay missing.
    No procedure, temp table, synchronization or publication is executed.
    """
    query = text(f'''
        WITH clock AS (
            SELECT CAST(DATEADD(day,
                CASE WHEN CAST(GETDATE() AS time) >= '08:00:00' THEN -1 ELSE -2 END,
                GETDATE()) AS date) AS closed_day
        ), wet AS (
            SELECT CAST(v.Fecha AS date) AS fecha, x.turno, x.tm,
                   CASE WHEN ABS(TRY_CONVERT(float, x.tmh)) > 150000 THEN 0
                        ELSE TRY_CONVERT(float, x.tmh) END AS tmh,
                   CAST('PI' AS varchar(40)) AS fuente
            FROM {dbs.SCHEMA}.v_datos_apilado_tmh_v2 v
            CROSS JOIN clock
            CROSS APPLY (VALUES
                ('A','TM1',v.TMH_CV008_A), ('B','TM1',v.TMH_CV008_B),
                ('A','TM2',v.TMH_CV108_A), ('B','TM2',v.TMH_CV108_B)
            ) x(turno,tm,tmh)
            WHERE v.Fecha >= :start AND v.Fecha < DATEADD(day,1,:end)
              AND (v.Fecha < '20260901' OR v.Fecha > clock.closed_day)
            UNION ALL
            SELECT CAST(r.fecha_operacional AS date), r.turno,
                   CASE WHEN r.equipo_codigo = 'PRINCIPAL_CV008' THEN 'TM1' ELSE 'TM2' END,
                   CASE WHEN ABS(TRY_CONVERT(float,r.valor_final_resuelto)) > 150000 THEN 0
                        ELSE TRY_CONVERT(float,r.valor_final_resuelto) END,
                   r.fuente_resuelta
            FROM {dbs.SCHEMA}.v_contingencia_totalizador_resuelto_turno r CROSS JOIN clock
            WHERE r.fecha_operacional >= :start AND r.fecha_operacional < DATEADD(day,1,:end)
              AND r.fecha_operacional >= '20260901' AND r.fecha_operacional <= clock.closed_day
              AND r.equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108')
        )
        SELECT w.fecha,w.turno,w.tm,w.tmh,w.fuente,
               CASE WHEN w.tm='TM1' THEN h.Humedad_TM1 ELSE h.Humedad_TM2 END AS humedad
        FROM wet w LEFT JOIN {dbs.SCHEMA}.fn_humedad_resuelta_tm_turno_test(
            :start, DATEADD(day,1,:end)) h ON h.Fecha=w.fecha AND h.Turno=w.turno
        ORDER BY w.fecha,w.turno,w.tm
    ''')
    return pd.read_sql(query, engine or dbs.get_engine(),
                       params={'start': pd.Timestamp(start).date(), 'end': pd.Timestamp(end).date()})


def load_hours(start, end, engine=None):
    # Calendar union across parallel towers; do not sum their elapsed hours.
    query = text(f'''
        WITH ticks AS (
            SELECT fecha, MAX(CAST(tick_efectivo AS int)) AS any_on
            FROM {dbs.SCHEMA}.v_ticks_efectivos_torre_10s
            WHERE fecha >= :start AND fecha < :end GROUP BY fecha
        )
        SELECT CAST(DATEADD(hour,-8,fecha) AS date) AS fecha,
               SUM(any_on)*10.0/3600 AS H_op
        FROM ticks GROUP BY CAST(DATEADD(hour,-8,fecha) AS date)
    ''')
    return pd.read_sql(query, engine or dbs.get_engine(), params={
        'start': pd.Timestamp(start).normalize()+pd.Timedelta(hours=8),
        'end': pd.Timestamp(end).normalize()+pd.Timedelta(days=1,hours=8)})


def distribute_profile(profile, apilado, targets, caso):
    """Pure adapter: per-pad Case totals -> days/shifts with observed activity."""
    active = apilado.loc[apilado.vol_diario.gt(0), ['fecha', 'pad_id']].drop_duplicates().copy()
    active['fecha'] = pd.to_datetime(active.fecha).dt.normalize()
    p = profile.copy()
    p['fecha'] = pd.to_datetime(p.fecha).dt.normalize()
    p = p[p.fecha.isin(active.fecha)]
    if p.duplicated(['fecha','turno','tm']).any():
        raise FlowCaseError('El perfil operativo repite fecha, turno y correa.')
    expected = pd.MultiIndex.from_product([active.fecha.unique(), ['A','B'], ['TM1','TM2']],
                                         names=['fecha','turno','tm'])
    p = p.set_index(['fecha','turno','tm']).reindex(expected).reset_index()
    wet = pd.to_numeric(p['tmh'], errors='coerce')
    humidity = pd.to_numeric(p['humedad'], errors='coerce')
    bad = ~np.isfinite(wet) | wet.lt(0) | p['fuente'].isna() | p['fuente'].eq('SIN_RESOLVER')
    bad |= wet.gt(0) & (~np.isfinite(humidity) | humidity.lt(0) | humidity.ge(100))
    if bad.any():
        raise FlowCaseError('Faltan lecturas de correa o humedad para distribuir el Caso por turno.')
    p['TMS'] = (wet*(1-humidity/100)).where(wet.ne(0), 0.0)
    p['TMH'] = wet
    daily = p.groupby(['fecha','turno'], as_index=False)[['TMS','TMH']].sum()
    wide = daily.pivot(index='fecha',columns='turno',values=['TMS','TMH'])
    base = pd.DataFrame({'fecha': wide.index,
        'TMS_T1': wide[('TMS','A')].values, 'TMS_T2': wide[('TMS','B')].values,
        'TMH': (wide[('TMH','A')]+wide[('TMH','B')]).values})
    base['TMS_base'] = base.TMS_T1+base.TMS_T2
    frames, balances = [], []
    for pad, target in targets.items():
        frame = active[active.pad_id.eq(pad)].merge(base, on='fecha', how='left')
        total = float(frame.TMS_base.sum())
        reconciled = target['masa_reconciliada']
        if reconciled > 0 and total <= 0:
            raise FlowCaseError(f'PAD {pad}: masa reconciliada positiva sin perfil operativo con apilado.')
        factor = reconciled/total if total > 0 else 0.0
        frame['TMS_T1'] *= factor
        frame['TMS_T2'] *= factor
        frame['TMS'] = frame.TMS_T1+frame.TMS_T2
        frame['boundary'] = (frame.TMS_T1/frame.TMS).where(frame.TMS.gt(0),
            (frame.TMS_T1+frame.TMS_T2)*0.0)  # a zero target receives no mass
        frame['boundary_normalizada'] = True
        frame['turnos_ok'] = frame.TMS_T1.gt(0) & frame.TMS_T2.gt(0)
        frame['fuente_masa'] = 'FLUJOS_CASO_DISTRIBUIDOS'
        frame['caso_id'] = int(caso['id'])
        frame['reporte_run_id'] = str(caso['run_id'])
        frame['flujo'] = target['flujo']
        frame['factor_caso'] = factor
        frames.append(frame)
        balances.append(dict(pad_id=pad, flujo=target['flujo'], objetivo_t=reconciled,
                             perfil_t=total, asignada_t=float(frame.TMS.sum()), factor=factor,
                             fino_cu_t=target['fino_cu_reconciliado']))
    return pd.concat(frames, ignore_index=True), base, pd.DataFrame(balances)
