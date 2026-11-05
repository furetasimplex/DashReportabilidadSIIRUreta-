"""Cargador generico SELECT-only para el metodo "maduras fijas, nuevas moviles".

Reune, para un Caso oficial y un PAD (OXIDOS o SULFUROS), todo lo que necesita
:mod:`curvas_recon.maduras_nuevas`:

* identidad Caso -> run oficial (recon_caso_oficial) -> modelo 125 v2;
* objetivo de Cu neto del PAD: ``fino_cu_reconciliado`` de F25 (Oxidos) o F29
  (Sulfuros) en ``recon_resultado_flujo`` del run oficial;
* perfil de drenaje MODELADO de las pilas, del run de asignacion guardado
  (reconciliacion_run / reconciliacion_detalle_dia) del mismo Caso y ventana;
* recuperacion observada (Recuperaciones_pad, fuente primaria), Cu apilado
  (SUM(Finos_cut) de modulos_turnos) y primer riego real de la campana;
* riego, Cu de riego y Cu de drenaje medidos (consolidadas con relleno por
  fecha desde las vistas de ingesta, como los cargadores del motor).

Solo emite SELECT/WITH (se verifica cada sentencia antes de ejecutarla). Sin
respaldo silencioso: cualquier identidad, cobertura o fuente faltante levanta
:class:`MadurasInputError` con la causa. Las consultas se basan en los scripts
de captura de ``auditorias/metodologia_sulfuros_10009`` y en ``db_pipeline``.
"""
from __future__ import annotations

from datetime import timedelta
from math import isfinite
from numbers import Real
import re

from sqlalchemy import text

from .maduras_nuevas import (
    CoverageError, MadurasError, as_date, carry_previous_result, normalize_pad,
    plan_cohorts,
)

LABEL_MATERIAL = {'OXIDOS': 'OXIDO', 'SULFUROS': 'SULFURO'}
# Mismo mapeo que db_pipeline.load_caso_anchor (modelo 125 v2): F25/F29 son el
# objetivo neto absoluto de Cu por PAD. La confirmacion es de codigo/docs; el
# catalogo SQL de flujos no se pudo consultar al escribir este modulo.
NET_TARGET_FLOW = {'OXIDOS': 'F25', 'SULFUROS': 'F29'}
NET_TARGET_MODEL = 'hidrometalurgia_125_v2'
REFINO_VIEW = {'OXIDOS': 'vw_riego_oxido_refino_base', 'SULFUROS': 'vw_riego_sulfuro_refino_base'}
PRIMARY_SOURCE = 'Recuperaciones_pad (primary)'
RECOVERY_MAX_PCT = 200.0   # mismo tope que pad_data._load_material

_FORBIDDEN_SQL = re.compile(
    r'\b(insert|update|delete|merge|truncate|alter|drop|create|exec|execute|call|grant|revoke|into)\b', re.I)


class MadurasInputError(ValueError):
    """Fuentes ausentes, vencidas o que no corresponden al Caso pedido."""


def assert_select_only(sql):
    cleaned = re.sub(r'/\*.*?\*/|--[^\n]*', '', sql, flags=re.S).strip()
    if not re.match(r'(?is)^(select|with)\b', cleaned) or _FORBIDDEN_SQL.search(cleaned):
        raise MadurasInputError('Sentencia SQL no SELECT bloqueada por el cargador de solo lectura')
    return cleaned


class _Reader:
    def __init__(self, conn, schema, hidro):
        self.conn, self.s, self.h = conn, schema, hidro
        self.statements = 0

    def rows(self, sql, **params):
        assert_select_only(sql)
        self.statements += 1
        result = self.conn.execute(text(sql), params)
        return [tuple(r) for r in result.fetchall()]


def _float(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _pile_name(number):
    return f'P{int(number):02d}'


def _pile_sort(name):
    match = re.search(r'(\d+)', str(name))
    return (int(match.group(1)) if match else 10**9, str(name))


def default_history_start(start):
    """Primer dia del mes anterior al del Caso (historia protegida visible)."""
    first = as_date(start).replace(day=1)
    return (first - timedelta(days=1)).replace(day=1)


def _merge_by_date(consolidated, ingest, what):
    """{clave: (valor, fuente)}; la consolidada manda en las fechas que cubre.

    Mismo criterio que ``recon_engine.load_riego/load_drena_cu``: la tabla
    consolidada va por detras de la ingesta, asi que la vista solo rellena
    fechas completas que la consolidada no tiene. Valores nulos no cuentan.
    """
    merged, cons_dates = {}, set()
    for source, rows in (('consolidated', consolidated), ('ingest', ingest)):
        for row in rows:
            day, key, value = row[0], row[1], _float(row[2])
            if value is None:
                continue
            day = as_date(day)
            if source == 'ingest' and day in cons_dates:
                continue
            slot = (day, key)
            if slot in merged and merged[slot][1] == source:
                if abs(merged[slot][0] - value) > 1e-9:
                    raise MadurasInputError(f'{what}: valores distintos para {key} el {day} en {source}')
                continue
            merged[slot] = (value, source)
        if source == 'consolidated':
            cons_dates = {as_date(r[0]) for r in rows if _float(r[2]) is not None}
    return merged


def validate_payload(payload, *, case_id, label, start, end, target,
                     expected_ids=None, target_message=None):
    """Valida un paquete de fuentes (SQL, congelado o inyectado). Fail-closed."""
    label = normalize_pad(label)
    if not isinstance(payload, dict) or not isinstance(payload.get('rows'), list):
        raise MadurasInputError('source provider must return a rows list')
    source_ids = payload.get('source_ids')
    if source_ids is None and isinstance(payload.get('metadata'), dict):
        meta = payload['metadata']
        source_ids = {k: meta.get(k) for k in
                      ('case_id', 'solver_run_id', 'allocation_profile_run_id',
                       'fixture_sha256', 'qualification')}
    if not isinstance(source_ids, dict):
        raise MadurasInputError('source identities are required')
    expected = dict(expected_ids or {})
    expected.setdefault('case_id', case_id)
    for name, want in expected.items():
        try:
            got = int(source_ids.get(name, -1))
        except (TypeError, ValueError):
            got = -1
        if got != int(want):
            raise MadurasInputError(f'unsupported or mismatched {name}')
    try:
        int(source_ids['allocation_profile_run_id'])
    except (KeyError, TypeError, ValueError) as exc:
        raise MadurasInputError('unsupported or mismatched allocation_profile_run_id') from exc
    if as_date(payload.get('target_period_start', start)) != start:
        raise MadurasInputError('source target period does not start at Case window')
    payload_target = payload.get('target_net_t')
    if not isinstance(payload_target, Real) or isinstance(payload_target, bool):
        raise MadurasInputError('captured target net-Cu is missing')
    if abs(float(payload_target) - target) > 1e-8:
        raise MadurasInputError(target_message or 'captured target does not match official Case anchor')
    required = {'pad', 'pile', 'campaign', 'date', 'official_pct', 'observed_pct',
                'cu_apilado_t', 'first_irrigation', 'observation_source'}
    rows = payload['rows']
    for row in rows:
        if not isinstance(row, dict) or not required.issubset(row):
            raise MadurasInputError('row misses canonical cohort fields')
        if normalize_pad(row['pad']) != label:
            raise MadurasInputError(f'row of another PAD in the {label} source bundle')
        if as_date(row['date']) > end:
            raise MadurasInputError('source date exceeds Case window')
    if not rows:
        raise MadurasInputError(f'empty {label} source bundle')
    try:
        plan, _, _ = plan_cohorts(rows, start, end, label)
    except CoverageError as exc:
        raise MadurasInputError(
            f'each {label} cohort requires prior-day baseline and complete Case coverage: {exc}') from exc
    except MadurasError as exc:
        raise MadurasInputError(str(exc)) from exc
    for key, info in plan.items():
        if info['kind'] != 'young':
            continue
        for day in info['expected']:
            row = info['group'][day][1]
            for field in ('q_riego_m3h', 'cu_riego_gL', 'cu_drenaje_gL',
                          'profile_q_drenaje_m3h', 'drainage_profile_source'):
                if row.get(field) is None:
                    raise MadurasInputError(
                        f'missing {field} on Case day for young pile {key[1]} campaign {key[2]} ({day})')
            if 'not measured' not in str(row['drainage_profile_source']).lower():
                raise MadurasInputError('drainage profile provenance must state modeled/not measured')
    return {
        'rows': [dict(row) for row in rows],
        'source_ids': dict(source_ids),
        'target_period_start': start.isoformat(),
        'target_net_t': target,
        'metadata': dict(payload.get('metadata') or {}),
    }


def _read_identity(rd, caso_id, start, end, expected_run_id):
    rows = rd.rows(f"""
        SELECT c.id, c.nombre_caso, c.fecha_inicio, c.fecha_fin, c.estado,
               o.solver_run_id, m.codigo, m.version, m.total_flujos
        FROM {rd.h}.recon_caso c
        JOIN {rd.h}.recon_caso_oficial o ON o.caso_id = c.id
        JOIN {rd.h}.recon_solver_run r ON r.id = o.solver_run_id AND r.caso_id = c.id
        JOIN {rd.h}.recon_modelo m ON m.id = c.modelo_id
        WHERE c.id = :caso AND r.estado = 'success'""", caso=caso_id)
    if len(rows) != 1:
        raise MadurasInputError(
            f'Caso {caso_id}: se esperaba exactamente un run oficial exitoso y hay {len(rows)}')
    (cid, name, f_ini, f_fin, _estado, run_id, model, version, total) = rows[0]
    if int(cid) != caso_id:
        raise MadurasInputError('identidad de Caso inconsistente')
    if as_date(f_ini) != start or as_date(f_fin) != end:
        raise MadurasInputError(
            f'La ventana pedida {start}..{end} no coincide con la del Caso {caso_id} '
            f'({as_date(f_ini)}..{as_date(f_fin)})')
    if expected_run_id is not None and int(run_id) != int(expected_run_id):
        raise MadurasInputError(
            f'El run oficial del Caso {caso_id} es {int(run_id)} y se esperaba {int(expected_run_id)}')
    if str(model) != NET_TARGET_MODEL or str(version) != 'v2' or int(total or 0) != 125:
        raise MadurasInputError(
            f'El Caso {caso_id} usa el modelo {model!r} {version!r} ({total} flujos); el objetivo neto '
            f'F25/F29 solo esta definido para {NET_TARGET_MODEL}')
    return dict(case_id=int(cid), case_name=name, solver_run_id=int(run_id),
                model_code=str(model), model_version=str(version), total_flows=int(total))


def _read_target(rd, run_id, label, anchor):
    flow = NET_TARGET_FLOW[label]
    rows = rd.rows(f"""
        SELECT codigo_flujo, CAST(fino_cu_reconciliado AS float)
        FROM {rd.h}.recon_resultado_flujo WHERE run_id = :run AND codigo_flujo = :flow""",
        run=run_id, flow=flow)
    if len(rows) != 1 or _float(rows[0][1]) is None:
        raise MadurasInputError(f'El run oficial {run_id} no tiene {flow} (fino Cu reconciliado) para {label}')
    target = float(rows[0][1])
    if anchor is not None:
        pad_anchor = anchor.get(label) if isinstance(anchor, dict) else None
        if not isinstance(pad_anchor, dict) or pad_anchor.get('net_cu_target_t') is None:
            raise MadurasInputError(f'El ancla del Caso no trae objetivo neto de {label}')
        if pad_anchor.get('net_cu_target_flow') not in (None, flow):
            raise MadurasInputError(
                f'El ancla de {label} usa {pad_anchor.get("net_cu_target_flow")} y se esperaba {flow}')
        if abs(float(pad_anchor['net_cu_target_t']) - target) > 1e-8:
            raise MadurasInputError(f'El objetivo del ancla de {label} no coincide con {flow} del run oficial')
    return flow, target


def _read_allocation(rd, caso_id, start, end, label):
    runs = rd.rows(f"""
        SELECT id, caso_id, CAST(semana_lunes AS date), CAST(semana_fin AS date), method, converged
        FROM {rd.s}.reconciliacion_run
        WHERE caso_id = :caso AND CAST(semana_lunes AS date) = :start AND CAST(semana_fin AS date) = :end
        ORDER BY id DESC""", caso=caso_id, start=start, end=end)
    if not runs:
        raise MadurasInputError(
            f'No hay un run de asignacion guardado para el Caso {caso_id} y la ventana {start}..{end}. '
            'El perfil de drenaje de las pilas nuevas sale de ese run; esta opcion no ejecuta ni guarda '
            'nada en SQL ni usa otro metodo como respaldo.')
    run_id, run_case, r_start, r_end, method, converged = runs[0]
    if int(run_case) != caso_id or as_date(r_start) != start or as_date(r_end) != end:
        raise MadurasInputError('El run de asignacion no coincide con el Caso y la ventana')
    if not converged:
        raise MadurasInputError(f'El run de asignacion {int(run_id)} no convergio; su perfil no es utilizable')
    detail = rd.rows(f"""
        SELECT d.parcela_nombre, CAST(DATEADD(day, d.dia_offset, r.semana_lunes) AS date), CAST(d.q_pls AS float)
        FROM {rd.s}.reconciliacion_detalle_dia d JOIN {rd.s}.reconciliacion_run r ON r.id = d.run_id
        WHERE d.run_id = :run AND d.label = :label""", run=int(run_id), label=label)
    profile, universe = {}, set()
    for pile, day, q_pls in detail:
        slot = (str(pile), as_date(day))
        if slot in profile:
            raise MadurasInputError(f'Perfil duplicado en el run {int(run_id)}: {slot[0]} {slot[1]}')
        profile[slot] = _float(q_pls)
        universe.add(str(pile))
    if not universe:
        raise MadurasInputError(f'El run de asignacion {int(run_id)} no tiene pilas de {label}')
    return dict(run_id=int(run_id), method=method, candidates=[int(r[0]) for r in runs],
                profile=profile, universe=universe)


def load_pad_inputs(week_start, week_end, caso_id, label, anchor=None, *,
                    expected_run_id=None, engine=None, schema=None, hidro_schema=None,
                    history_start=None, previous_result=None):
    """Carga y valida las fuentes de un PAD para un Caso oficial (solo SELECT).

    ``anchor``: ancla del Caso (``load_caso_anchor``); si se entrega, su objetivo
    neto debe coincidir con el de ``recon_resultado_flujo``. ``expected_run_id``:
    run oficial que la pantalla tiene seleccionado. ``previous_result``: ``res``
    local del Caso consecutivo anterior; si se entrega, su recuperacion pasa a
    ser la linea base (encadenamiento, historia protegida).
    """
    label = normalize_pad(label)
    start, end = as_date(week_start), as_date(week_end)
    try:
        caso_id = int(caso_id)
    except (TypeError, ValueError) as exc:
        raise MadurasInputError('invalid case id') from exc
    if end < start:
        raise MadurasInputError('la ventana termina antes de empezar')
    if engine is None or schema is None or hidro_schema is None:
        from . import db_pipeline
        engine = engine or db_pipeline.get_engine()
        schema = schema or db_pipeline.SCHEMA
        hidro_schema = hidro_schema or db_pipeline.HIDRO_SCHEMA
    if not re.fullmatch(r'[A-Za-z_]\w*', schema) or not re.fullmatch(r'[A-Za-z_]\w*\.[A-Za-z_]\w*', hidro_schema):
        raise MadurasInputError('esquema SQL invalido')
    hist = as_date(history_start) if history_start else default_history_start(start)
    material = LABEL_MATERIAL[label]
    with engine.connect() as conn:
        rd = _Reader(conn, schema, hidro_schema)
        identity = _read_identity(rd, caso_id, start, end, expected_run_id)
        flow, target = _read_target(rd, identity['solver_run_id'], label, anchor)
        alloc = _read_allocation(rd, caso_id, start, end, label)
        mat = rd.rows(f'SELECT id FROM {rd.s}.material WHERE nombre = :n', n=material)
        if len(mat) != 1:
            raise MadurasInputError(f'material {material} no identificado en SQL')
        pad_id = int(mat[0][0])
        stacking = {(int(p), int(c)): (as_date(d), _float(cu)) for p, c, d, cu in rd.rows(f"""
            SELECT TRY_CAST(Parcela AS int), TRY_CAST(Campana AS int), MIN(CAST(Fecha AS date)),
                   SUM(CAST(Finos_cut AS float))
            FROM {rd.s}.modulos_turnos
            WHERE pad_id = :pad AND Fecha <= :end AND Parcela IS NOT NULL AND Campana IS NOT NULL
            GROUP BY TRY_CAST(Parcela AS int), TRY_CAST(Campana AS int)""", pad=pad_id, end=end)
            if p is not None and c is not None}
        recovery_raw = rd.rows(f"""
            SELECT TRY_CAST(Parcela AS int), TRY_CAST(Campana AS int), CAST(Fecha_drenaje AS date),
                   CAST(Recuperacion_parcela AS float)
            FROM {rd.s}.Recuperaciones_pad
            WHERE PAD = :pad AND Recuperacion_parcela IS NOT NULL
              AND Fecha_drenaje >= :hist AND Fecha_drenaje <= :end
            ORDER BY 1, 3""", pad=label, hist=hist, end=end)
        recovery, discarded = {}, 0
        for pile_no, campaign, day, pct in recovery_raw:
            value = _float(pct)
            if pile_no is None or campaign is None or value is None or not 0.0 <= value <= RECOVERY_MAX_PCT:
                discarded += 1
                continue
            slot = (int(pile_no), int(campaign), as_date(day))
            if slot in recovery and abs(recovery[slot] - value) > 1e-9:
                raise MadurasInputError(f'Recuperaciones_pad duplicada con valores distintos: P{slot[0]:02d} {slot[2]}')
            recovery[slot] = value
        # --- pilas del universo con campana y recuperacion -----------------
        chosen, excluded = {}, {}
        for name in sorted(alloc['universe'], key=_pile_sort):
            m = re.fullmatch(r'P(\d+)', name)
            if not m:
                raise MadurasInputError(f'Nombre de pila inesperado en el run de asignacion: {name!r}')
            number = int(m.group(1))
            own = [(c, d) for (p, c, d) in recovery if p == number]
            if not own:
                if not any(p == number for (p, _c) in stacking):
                    excluded[name] = 'sin campana de lixiviacion ni recuperacion (riego sin curva)'
                    continue
                raise MadurasInputError(
                    f'{label} {name}: tiene campana pero ninguna recuperacion en {hist}..{end}')
            last_day = max(d for _, d in own)
            campaigns_last = {c for c, d in own if d == last_day}
            if len(campaigns_last) != 1:
                raise MadurasInputError(f'{label} {name}: campanas ambiguas el {last_day}')
            campaign = campaigns_last.pop()
            other = sorted({c for c, d in own if c != campaign and d >= start})
            if other:
                raise MadurasInputError(
                    f'{label} {name}: la campana {other} tambien tiene recuperacion dentro de la ventana '
                    f'{start}..{end}; el cambio de campana dentro del Caso no esta soportado')
            if (number, campaign) not in stacking or not stacking[(number, campaign)][1] or stacking[(number, campaign)][1] <= 0:
                raise MadurasInputError(f'{label} {name} campana {campaign}: sin Cu apilado en modulos_turnos')
            chosen[name] = (number, campaign)
        if not chosen:
            raise MadurasInputError(f'{label}: ninguna pila del run de asignacion tiene curva de recuperacion')
        # --- primer riego real de la campana --------------------------------
        stack_min = min(stacking[v][0] for v in chosen.values())
        irrigated = rd.rows(f"""
            SELECT p.nombre, CAST(u.fecha AS date)
            FROM (SELECT parcela_id, fecha FROM {rd.s}.riego_diario
                  WHERE caudal_m3h > 0 AND fecha >= :lo AND fecha <= :end
                  UNION
                  SELECT parcela_id, fecha FROM {rd.s}.vw_riego_diario_ingest
                  WHERE caudal_m3h > 0 AND fecha >= :lo AND fecha <= :end) u
            JOIN {rd.s}.parcela p ON p.id_parcela = u.parcela_id
            JOIN {rd.s}.material m ON m.id = p.id_pad
            WHERE m.nombre = :material""", lo=stack_min, end=end, material=material)
        irrigation_days = {}
        for pile, day in irrigated:
            irrigation_days.setdefault(str(pile), set()).add(as_date(day))
        # --- mediciones de la ventana ---------------------------------------
        def _pile_measure(table, column):
            return rd.rows(f"""
                SELECT CAST(v.fecha AS date), p.nombre, CAST(v.{column} AS float)
                FROM {rd.s}.{table} v JOIN {rd.s}.parcela p ON p.id_parcela = v.parcela_id
                JOIN {rd.s}.material m ON m.id = p.id_pad
                WHERE m.nombre = :material AND v.fecha >= :start AND v.fecha <= :end""",
                material=material, start=start, end=end)
        riego = _merge_by_date(_pile_measure('riego_diario', 'caudal_m3h'),
                               _pile_measure('vw_riego_diario_ingest', 'caudal_m3h'), 'riego')
        cu_drena = _merge_by_date(_pile_measure('drena_cu_diario', 'cu_gl'),
                                  _pile_measure('vw_drena_quimica_ingest', 'cu_gl'), 'cu drenaje')
        cu_riego = _merge_by_date(
            [(d, None, v) for d, v in rd.rows(f"""
                SELECT CAST(c.fecha AS date), CAST(c.cu_gl AS float)
                FROM {rd.s}.cu_riego_diario c JOIN {rd.s}.material m ON m.id = c.material_id
                WHERE m.nombre = :material AND c.fecha >= :start AND c.fecha <= :end""",
                material=material, start=start, end=end)],
            [(d, None, v) for d, v in rd.rows(f"""
                SELECT CAST(v.fecha AS date), CAST(v.cu_pp AS float)
                FROM {rd.s}.{REFINO_VIEW[label]} v WHERE v.fecha >= :start AND v.fecha <= :end""",
                start=start, end=end)], 'cu riego')
        statements = rd.statements

    rows, births = [], {}
    profile_source = (f'saved allocation run {alloc["run_id"]}; modeled/reconciled, not measured')
    for name, (number, campaign) in chosen.items():
        first_stack, cu_tf = stacking[(number, campaign)]
        days = sorted(d for d in irrigation_days.get(name, ()) if d >= first_stack)
        if not days:
            raise MadurasInputError(
                f'{label} {name} campana {campaign}: sin riego positivo desde su apilamiento ({first_stack}) '
                f'hasta {end}; no se puede fechar el primer riego')
        birth = days[0]
        births[name] = birth
        for (p, c, day), pct in sorted(recovery.items(), key=lambda kv: kv[0][2]):
            if p != number or c != campaign:
                continue
            row = dict(pad=label, pile=name, campaign=campaign, date=day.isoformat(),
                       official_pct=pct, observed_pct=pct, cu_apilado_t=cu_tf,
                       first_irrigation=birth.isoformat(), observation_source=PRIMARY_SOURCE)
            if start <= day <= end:
                row.update(
                    q_riego_m3h=riego.get((day, name), (None,))[0],
                    cu_riego_gL=cu_riego.get((day, None), (None,))[0],
                    cu_drenaje_gL=cu_drena.get((day, name), (None,))[0],
                    profile_q_drenaje_m3h=alloc['profile'].get((name, day)),
                    drainage_profile_source=profile_source)
            rows.append(row)
    unknown = sorted(
        (n for n, d in irrigation_days.items()
         if n not in alloc['universe'] and any(start <= x <= end for x in d)), key=_pile_sort)
    if unknown:
        raise MadurasInputError(
            f'{label}: pilas con riego en la ventana ausentes del run de asignacion {alloc["run_id"]}: '
            f'{", ".join(unknown)}; el cierre del PAD quedaria incompleto')
    if previous_result is not None:
        prev_end = as_date(previous_result['week_end'])
        if prev_end + timedelta(days=1) != start:
            raise MadurasInputError(
                f'El resultado previo cierra {prev_end}; el Caso debe empezar el dia siguiente')
        rows = carry_previous_result(rows, previous_result.get('recovery_rows') or [],
                                     previous_result['week_start'], prev_end, pad=label)
    payload = {
        'rows': rows, 'target_net_t': target, 'target_period_start': start.isoformat(),
        'source_ids': dict(
            case_id=identity['case_id'], solver_run_id=identity['solver_run_id'],
            allocation_profile_run_id=alloc['run_id'], pad=label, net_target_flow=flow,
            model_code=identity['model_code'], model_version=identity['model_version'],
            loader='maduras_inputs.load_pad_inputs (SQL SELECT-only)',
            allocation_candidate_run_ids=alloc['candidates'],
            qualification='observed Q/Cu and recovery; modeled saved drainage profile; net-only conditional fit'),
        'metadata': dict(
            case=identity, history_start=hist.isoformat(), window=[start.isoformat(), end.isoformat()],
            allocation_solver_link='La tabla de asignacion no guarda el solver_run_id de origen: se une por '
                                   'Caso y ventana exacta (run mas reciente que convergio).',
            excluded_piles=excluded, first_irrigation={k: v.isoformat() for k, v in births.items()},
            discarded_recovery_rows=discarded, select_statements=statements,
            chained_from_previous=previous_result is not None, database_writes=False),
    }
    return validate_payload(
        payload, case_id=caso_id, label=label, start=start, end=end, target=target,
        expected_ids={'solver_run_id': identity['solver_run_id'],
                      'allocation_profile_run_id': alloc['run_id']})
