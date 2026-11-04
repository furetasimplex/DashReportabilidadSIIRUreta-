import os
import re
import urllib.parse
import math
import time
import pandas as pd
from sqlalchemy import create_engine, text

from env_loader import load_app_env

load_app_env()

# ── 1. Configuration ──────────────────────────────────────────────────────────

# Reuse the SIIR connection; an explicit RECON_SQLALCHEMY_URL overrides it.
# Neither the driver nor credentials are loaded while importing this module.
SCHEMA = os.getenv("RECON_SQL_SCHEMA", "inventar_SpcHidr")
_engine = None


def _resolve_hidro_schema() -> str:
    """Base.schema de casos oficiales (solo lectura).

    Prioridad:
      1. RECON_HIDRO_SCHEMA completo (ej. PROD_SIIR.hidro)
      2. HIDRO_SIIR_DB (mismo override que db_startup_check) + schema hidro
      3. SQLSERVER_DB: *_PROD -> PROD_SIIR; resto -> DEV_SIIR
    """
    explicit = (os.getenv("RECON_HIDRO_SCHEMA") or "").strip()
    if explicit:
        if not re.fullmatch(r"[A-Za-z_][\w]*\.[A-Za-z_][\w]*", explicit):
            raise RuntimeError(
                f"RECON_HIDRO_SCHEMA inválido: {explicit!r}. Use Base.schema."
            )
        return explicit

    siir_db = (os.getenv("HIDRO_SIIR_DB") or "").strip()
    if siir_db not in {"DEV_SIIR", "PROD_SIIR"}:
        sql_db = (os.getenv("SQLSERVER_DB") or "").strip()
        if sql_db.endswith("_PROD") or sql_db == "inventar_SpcHidr_PROD":
            siir_db = "PROD_SIIR"
        else:
            siir_db = "DEV_SIIR"

    schema = (os.getenv("RECON_HIDRO_SCHEMA_NAME") or "hidro").strip()
    if not re.fullmatch(r"[A-Za-z_][\w]*", schema):
        raise RuntimeError(f"RECON_HIDRO_SCHEMA_NAME inválido: {schema!r}.")
    return f"{siir_db}.{schema}"


def configure_engine(engine):
    """Inject the host application's engine (also useful for offline tests)."""
    global _engine
    _engine = engine


def get_engine():
    global _engine
    if _engine is None:
        url = os.getenv('RECON_SQLALCHEMY_URL')
        if url:
            _engine = create_engine(url, fast_executemany=True, pool_pre_ping=True)
        else:
            from db_connection import get_engine as siir_engine
            _engine = siir_engine()
        if _engine is None:
            raise RuntimeError('No está configurada la conexión de datos SIIR.')
    return _engine


def connect():
    return get_engine().connect()


from .local_cache import sql_maps as _sql_maps, sql_rows as _sql_rows, olvidar as _olvidar
from .perf_trace import record_phase

_TABLAS_LISTAS = False


def _ensure_reconciliation_tables():
    """Validate the provisioned schema without creating or altering tables."""
    global _TABLAS_LISTAS
    if _TABLAS_LISTAS:
        return
    required = ('reconciliacion_run', 'reconciliacion_detalle', 'reconciliacion_detalle_dia')
    with get_engine().connect() as conn:
        for table in required:
            present = conn.execute(text("SELECT OBJECT_ID(:table_name, 'U')"),
                                   {'table_name': f'{SCHEMA}.{table}'}).scalar()
            if present is None:
                raise RuntimeError(f'Falta la tabla de reconciliación {table}; '
                                   'instala el esquema antes de habilitar esta sección.')
        for column in ('semana_fin', 'caso_id'):
            present = conn.execute(text('SELECT COL_LENGTH(:table_name, :column_name)'),
                                   {'table_name': f'{SCHEMA}.reconciliacion_run',
                                    'column_name': column}).scalar()
            if present is None:
                raise RuntimeError(f'Falta la columna {column} en reconciliacion_run; '
                                   'actualiza el esquema antes de ejecutar el cálculo.')
    _TABLAS_LISTAS = True


# ── Casos de reconciliacion global (DEV_SIIR.hidro / PROD_SIIR.hidro) ────────
#
# Esquema administrado por Django: SOLO LECTURA desde aca. Nada de DDL ni de
# INSERT/UPDATE/DELETE sobre `recon_*`. Ambiente via .env (ver _resolve_hidro_schema).
HIDRO_SCHEMA = _resolve_hidro_schema()

# Flujos que anclan cada pad, versionados por el codigo del modelo. El mismo
# codigo F cambia de significado entre catalogos; no inferir version por
# numeracion ni por nombre del pad.
#
# En el modelo 125, los caudales de riego conservan sus sumas por origen:
# OXIDOS F70+F60+F81; SULFUROS F72+F66.
# La salida total drenada para curvas incluye las transferencias especificadas
# para cada pad: OXIDOS F44+F45; SULFUROS F47+F48+F49. F50 es inventario y
# no forma parte del total drenado que se reparte entre pilas. F45/F49 son
# codigos requeridos aunque su Cu pueda ser cero en una corrida.
#
# La matriz 120 conserva su mapeo historico independiente.
CASO_FLUJOS_120 = {
    'OXIDOS':   dict(riego=['F39', 'F41', 'F46'], pls=['F48']),
    'SULFUROS': dict(riego=['F44', 'F45'], pls=['F50', 'F49']),
}

# Flujos de origen secundario: si el run no trae la fila, valen 0 y el pad
# igual conserva su ancla. Los runs viejos (caso 17, generado antes de que
# existiera el split por origen) no tienen fila F46 y sin esto se quedarian
# sin ancla de un dia para otro.
CASO_FLUJOS_125 = {
    'OXIDOS':   dict(riego=['F70', 'F60', 'F81'], pls=['F44', 'F45']),
    'SULFUROS': dict(riego=['F72', 'F66'], pls=['F47', 'F48', 'F49']),
}

CASO_FLUJOS_POR_MODELO = {
    'hidrometalurgia_120_completo': ('v1', 120, CASO_FLUJOS_120,
                                     {'F41', 'F45', 'F46'}),
    'hidrometalurgia_125_v2': ('v2', 125, CASO_FLUJOS_125, set()),
}


def _caso_flows_for_model(model_code, model_version=None, total_flows=None):
    """Resolve flow semantics from the authoritative catalog code."""
    try:
        expected_version, expected_count, flows, optional = CASO_FLUJOS_POR_MODELO[str(model_code)]
    except KeyError as exc:
        raise ValueError(
            f'Modelo de reconciliacion sin mapping de ancla: {model_code!r}.'
        ) from exc
    if model_version is not None and str(model_version) != expected_version:
        raise ValueError(
            f'Version de modelo incompatible con el mapping de ancla: '
            f'{model_code!r} version {model_version!r}.'
        )
    if total_flows is not None and int(total_flows) != expected_count:
        raise ValueError(
            f'Catalogo de {model_code!r} declara {total_flows} flujos; '
            f'el mapping requiere {expected_count}.'
        )
    return flows, optional


def load_casos():
    """Casos PAD oficiales con run exitoso, ordenados por fecha descendente.

    Sin filtro por rango de id: se listan todos los oficializados con
    ``solver_run`` en success. La relacion de oficializacion cambia fuera
    de esta aplicacion; por eso esta lectura evita deliberadamente
    ``local_cache``: un puntero viejo usaria el run anterior.
    """
    query = text(f"""
        SELECT c.id, c.nombre_caso, c.fecha_inicio, c.fecha_fin, c.estado,
               o.solver_run_id AS run_id, m.codigo AS modelo_codigo,
               m.version AS modelo_version, m.total_flujos
        FROM {HIDRO_SCHEMA}.recon_caso c
        JOIN {HIDRO_SCHEMA}.recon_caso_oficial o ON o.caso_id = c.id
        JOIN {HIDRO_SCHEMA}.recon_solver_run r
          ON r.id = o.solver_run_id AND r.caso_id = c.id
        JOIN {HIDRO_SCHEMA}.recon_modelo m ON m.id = c.modelo_id
        WHERE r.estado = 'success'
        ORDER BY c.fecha_inicio DESC, c.id DESC
    """)
    with get_engine().connect() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(
        id=int(r[0]), nombre=r[1], fecha_inicio=pd.Timestamp(r[2]).normalize(),
        fecha_fin=pd.Timestamp(r[3]).normalize(), estado=r[4],
        run_id=int(r[5]), modelo_codigo=r[6], modelo_version=r[7],
        total_flujos=int(r[8]) if r[8] is not None else None,
    ) for r in rows]


def load_caso_anchor(run_id, model_code, model_version=None, total_flows=None):
    """Ancla POR PAD desde los flujos del run oficial de un Caso.

    Devuelve {'OXIDOS': {...}, 'SULFUROS': {...}} con las claves que espera
    `recon_engine.reconcile_flowsheet`: masa y fino, medidos y reconciliados.
    Los componentes conservan la razon reconciliado/medido para repartir
    entre pilas. En el modelo 125, F25/F29 son además el objetivo neto
    absoluto por pad para la curva diaria; no se derivan de la diferencia de
    componentes porque el balance puede no cerrar exactamente.

    Un pad al que le falte cualquiera de sus flujos queda FUERA del dict --
    mejor correr ese material sin ancla que anclarlo a una suma incompleta.
    """
    if run_id is None:
        return {}
    caso_flujos, flujos_opcionales = _caso_flows_for_model(
        model_code, model_version, total_flows)
    codes = sorted({c for f in caso_flujos.values() for c in f['riego'] + f['pls']})
    # In the 125-flow catalog these net balance outputs are authoritative
    # for each pad. Keep the component flows above for Q/fine ratios, but do
    # not derive the net target from them: F29 can differ from that sum.
    net_target_by_label = ({'OXIDOS': 'F25', 'SULFUROS': 'F29'}
                           if str(model_code) == 'hidrometalurgia_125_v2' else {})
    codes = sorted(set(codes) | set(net_target_by_label.values()))
    query = text(f"""
        SELECT codigo_flujo, masa_medida, masa_reconciliada,
               fino_cu_medido, fino_cu_reconciliado
        FROM {HIDRO_SCHEMA}.recon_resultado_flujo
        WHERE run_id = :run AND codigo_flujo IN ({','.join(':c%d' % i for i in range(len(codes)))})
    """)
    params = {'run': int(run_id)}
    params.update({'c%d' % i: c for i, c in enumerate(codes)})
    rows = _sql_rows(get_engine(), query, params, etiqueta='recon_caso')
    by_code = {r[0]: tuple(float(v) if v is not None else None for v in r[1:]) for r in rows}

    out = {}
    for label, flows in caso_flujos.items():
        needed = [c for c in flows['riego'] + flows['pls']
                  if c not in flujos_opcionales]
        target_flow = net_target_by_label.get(label)
        if target_flow:
            needed.append(target_flow)
        if any(c not in by_code for c in needed):
            print(f'[db_pipeline] load_caso_anchor(run={run_id}): {label} sin ancla, '
                  f'faltan flujos {[c for c in needed if c not in by_code]}.')
            continue
        faltan_opt = [c for c in flows['riego'] + flows['pls']
                      if c in flujos_opcionales and c not in by_code]
        if faltan_opt:
            print(f'[db_pipeline] load_caso_anchor(run={run_id}): {label} sin '
                  f'{faltan_opt} en el run, se asumen 0. El ancla de riego puede '
                  f'quedar corta si ese origen si aporto caudal.')

        def _sum(cods, idx):
            vals = [by_code[c][idx] for c in cods if c in by_code]
            return sum(vals) if vals and all(v is not None for v in vals) else None

        out[label] = dict(
            q_riego_medido=_sum(flows['riego'], 0), q_riego_recon=_sum(flows['riego'], 1),
            q_pls_medido=_sum(flows['pls'], 0), q_pls_recon=_sum(flows['pls'], 1),
            fino_riego_medido=_sum(flows['riego'], 2), fino_riego_recon=_sum(flows['riego'], 3),
            fino_pls_medido=_sum(flows['pls'], 2), fino_pls_recon=_sum(flows['pls'], 3),
            **({'net_cu_target_t': by_code[target_flow][3],
                'net_cu_target_flow': target_flow} if target_flow else {}),
        )
    return out


CASO_ANCHOR_KEYS = (
    'q_riego_medido', 'q_riego_recon', 'q_pls_medido', 'q_pls_recon',
    'fino_riego_medido', 'fino_riego_recon', 'fino_pls_medido',
    'fino_pls_recon',
)


def caso_anchor_completo(anchor):
    """True si ambos pads tienen un ancla numérica utilizable completa."""
    return not diagnose_caso_anchor(anchor)


def diagnose_caso_anchor(anchor):
    """Lista fallas del ancla para ambos pads, o lista vacía si está completa."""
    denominadores = {
        'q_riego_medido', 'q_pls_medido',
        'fino_riego_medido', 'fino_pls_medido',
    }
    etiquetas = {
        'q_riego_medido': 'caudal riego medido',
        'q_pls_medido': 'caudal PLS medido',
        'fino_riego_medido': 'fino Cu riego medido',
        'fino_pls_medido': 'fino Cu PLS medido',
        'q_riego_recon': 'caudal riego reconciliado',
        'q_pls_recon': 'caudal PLS reconciliado',
        'fino_riego_recon': 'fino Cu riego reconciliado',
        'fino_pls_recon': 'fino Cu PLS reconciliado',
    }
    fallas = []
    anchor = anchor or {}
    for label in ('OXIDOS', 'SULFUROS'):
        if label not in anchor:
            fallas.append(f'{label}: faltan flujos obligatorios del run oficial')
            continue
        valores = anchor[label] or {}
        for key in CASO_ANCHOR_KEYS:
            value = valores.get(key)
            nombre = etiquetas.get(key, key)
            if value is None or not pd.notna(value):
                fallas.append(f'{label}: {nombre} ausente')
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                fallas.append(f'{label}: {nombre} no numérico')
                continue
            if not math.isfinite(number) or number < 0:
                fallas.append(f'{label}: {nombre} no finito o negativo')
            elif key in denominadores and number <= 0:
                fallas.append(f'{label}: {nombre} = {number:.6g} (debe ser > 0)')
        # 120-flow anchors do not carry these fields. 125-flow anchors must
        # have the separate authoritative net output, which may be zero or
        # negative when its implied absolute PLS fine remains feasible.
        target_flow = valores.get('net_cu_target_flow')
        if target_flow:
            target = valores.get('net_cu_target_t')
            if target is None:
                fallas.append(f'{label}: fino Cu reconciliado de {target_flow} ausente')
            else:
                try:
                    target_number = float(target)
                except (TypeError, ValueError):
                    target_number = float('nan')
                if not math.isfinite(target_number):
                    fallas.append(f'{label}: fino Cu reconciliado de {target_flow} no finito')
    return fallas


def get_material_id(conn, label):
    """Resolve the material id for a dashboard label like OXIDOS/SULFUROS."""
    material_name = {'OXIDOS': 'OXIDO', 'SULFUROS': 'SULFURO'}.get(label, label)
    query = text(f"SELECT id FROM {SCHEMA}.material WHERE nombre = :nombre")
    rows = _sql_rows(get_engine(), query, {"nombre": material_name}, etiqueta='material')
    return int(rows[0][0]) if rows else None


# Backwards-compatible name used by older pipeline code.
get_id_pad = get_material_id


def load_pila_history(conn, id_pad, parcela_name):
    """Filas SEMANALES reconciliadas de una pila, UNA por semana.

    `reconciliacion_run` guarda una fila por corrida, no por semana: el mismo
    lunes puede tener varias corridas (Casos distintos que arrancan el mismo
    lunes y terminan en fechas distintas, o el mismo Caso corrido de nuevo).
    El 2026-07-01 tiene 6 y el 2026-08-01 tiene 3. Sin filtrar por corrida,
    el consumidor recibe la misma semana repetida N veces: los graficos
    dibujan N puntos por fecha y las comparaciones medido/reconciliado suman
    N veces la misma masa. Se toma la corrida MAS RECIENTE de cada semana
    (MAX(id)), que es la reconciliacion vigente de ese lunes.

    La query NO filtra por parcela: baja el pad entero y se corta aca. El
    dashboard pide esto una vez por pila -- 44 pilas eran 44 idas al servidor
    de ~0,4 s cada una, todas contra las mismas dos tablas. Cacheado por pad
    es UNA, y las otras 43 salen de memoria. Igual que el corte por fecha de
    `local_cache.sql_df`: el WHERE que se saca es una igualdad simple sobre
    una columna que viene en el SELECT, asi que filtrar en pandas/Python da
    fila por fila lo mismo."""
    _ensure_reconciliation_tables()
    query = text(f"""
        WITH ultima AS (
            SELECT semana_lunes, MAX(id) AS id
            FROM {SCHEMA}.reconciliacion_run
            GROUP BY semana_lunes
        )
        SELECT
            r.semana_lunes AS semana_lunes,
            r.semana_fin AS semana_fin,
            r.caso_id AS caso_id,
            r.id AS run_id,
            d.estado,
            d.fdrena,
            d.fdrena_prior,
            d.dia_ciclo,
            d.q_mean,
            d.q_pls_mean,
            d.cu_drena_mean,
            d.cu_riego_mean,
            d.parcela_nombre
        FROM {SCHEMA}.reconciliacion_detalle d
        JOIN {SCHEMA}.reconciliacion_run r ON r.id = d.run_id
        JOIN ultima u ON u.id = r.id
        WHERE d.material_id = :id_pad
        ORDER BY r.semana_lunes, d.id
    """)
    filas = _sql_maps(get_engine(), query, {"id_pad": id_pad}, etiqueta='recon_semana')
    return [r for r in filas if r.get('parcela_nombre') == parcela_name]


def load_pila_daily_history(conn, id_pad, parcela_name):
    """Filas DIARIAS reconciliadas de una pila, UNA por (semana, dia).

    Mismo filtro por corrida vigente que `load_pila_history` -- ver alli por
    que hace falta. Sin el, una pila del 2026-08-01 devolvia 47 filas para 23
    fechas distintas: tres corridas del mismo lunes con ventanas de largo
    distinto (Casos 21, 16 y 24, que terminan el 08-08, el 08-16 y el
    08-23).

    Tampoco filtra por parcela en el SQL, por lo mismo que
    `load_pila_history`: una query por pad y el corte aca."""
    _ensure_reconciliation_tables()
    query = text(f"""
        WITH ultima AS (
            SELECT semana_lunes, MAX(id) AS id
            FROM {SCHEMA}.reconciliacion_run
            GROUP BY semana_lunes
        )
        SELECT
            r.semana_lunes AS semana_lunes,
            r.semana_fin AS semana_fin,
            r.caso_id AS caso_id,
            r.id AS run_id,
            d.dia_offset,
            d.fdrena,
            d.q,
            d.q_pls,
            d.cu_drena,
            d.cu_riego,
            d.parcela_nombre
        FROM {SCHEMA}.reconciliacion_detalle_dia d
        JOIN {SCHEMA}.reconciliacion_run r ON r.id = d.run_id
        JOIN ultima u ON u.id = r.id
        WHERE d.material_id = :id_pad
        ORDER BY r.semana_lunes, d.dia_offset
    """)
    filas = _sql_maps(get_engine(), query, {"id_pad": id_pad}, etiqueta='recon_dia')
    return [r for r in filas if r.get('parcela_nombre') == parcela_name]


def load_week_totals(conn):
    """Load recent week-level reconciliation rows for reporting."""
    _ensure_reconciliation_tables()
    query = text(f"""
        SELECT semana_lunes, actual_t, mt_base_t, mt_opt_t
        FROM {SCHEMA}.reconciliacion_run
        ORDER BY semana_lunes DESC
    """)
    return _sql_maps(get_engine(), query, etiqueta='recon_run')


def _insert_rows_batched(conn, table, columns, rows, parameter_limit=2000):
    """Insert rows with bounded multi-VALUES on SQL Server, executemany elsewhere.

    The SQL Server batch stays below its 2,100-parameter ceiling and the
    1,000-row VALUES constructor limit. Values remain bound parameters.
    """
    if not rows:
        return 0
    columns = tuple(columns)
    col_sql = ', '.join(columns)
    single_placeholders = ', '.join(':' + col for col in columns)
    if getattr(getattr(conn, 'dialect', None), 'name', None) != 'mssql':
        conn.execute(text(f'INSERT INTO {table} ({col_sql}) VALUES ({single_placeholders})'), rows)
        return 1

    parameter_limit = int(parameter_limit)
    if parameter_limit < len(columns):
        raise ValueError('parameter_limit must fit at least one complete row')
    max_rows = min(1000, parameter_limit // len(columns))
    statements = 0
    for offset in range(0, len(rows), max_rows):
        batch = rows[offset:offset + max_rows]
        params = {}
        value_groups = []
        for row_index, row in enumerate(batch):
            names = []
            for col in columns:
                bind = f'{col}_{row_index}'
                names.append(':' + bind)
                params[bind] = row.get(col)
            value_groups.append('(' + ', '.join(names) + ')')
        statement = text(
            f'INSERT INTO {table} ({col_sql}) VALUES ' + ', '.join(value_groups))
        conn.execute(statement, params)
        statements += 1
    return statements


def save_run(conn, week_start, method, active_days, sigma_rel, r_global, converged,
             week_row, detalle_rows, daily_rows, warnings=None,
             semana_fin=None, caso_id=None):
    """Persist a reconciliation run and its detailed rows in the shared SQL schema."""
    save_started = time.perf_counter()
    phase_started = time.perf_counter()
    _ensure_reconciliation_tables()
    record_phase('save_run.schema_check', time.perf_counter() - phase_started)
    week_start = pd.Timestamp(week_start).date()
    semana_fin = pd.Timestamp(semana_fin).date() if semana_fin is not None else None
    caso_id = int(caso_id) if caso_id is not None else None

    # Reconciliar la misma ventana con el mismo metodo REEMPLAZA la corrida
    # anterior en vez de apilarse. Sin esto cada click en "Reconciliar" suma
    # otras 58 filas de detalle y 406 diarias para la misma semana, y
    # `_week_pila_metrics` (que suma dia a dia sobre reconciliacion_detalle_dia)
    # devolveria masa y caudal multiplicados por la cantidad de corridas.
    #
    # El `caso_id` ES parte de la clave: varios Casos comparten fecha de
    # inicio (1, 13, 14, 15 y 17 arrancan el 2026-07-01), asi que sin el
    # reconciliar uno borraba la corrida de otro. Con caso_id NULL (corrida
    # por semana, sin Caso) solo reemplaza a las otras corridas sin Caso.
    caso_pred = "caso_id = :caso" if caso_id is not None else "caso_id IS NULL"
    phase_started = time.perf_counter()
    old_ids = [r[0] for r in conn.execute(
        text(f"SELECT id FROM {SCHEMA}.reconciliacion_run "
             f"WHERE semana_lunes = :ws AND method = :m AND {caso_pred}"),
        ({"ws": week_start, "m": method, "caso": caso_id} if caso_id is not None
         else {"ws": week_start, "m": method}),
    ).fetchall()]
    record_phase('save_run.find_previous', time.perf_counter() - phase_started,
                 previous_runs=len(old_ids))
    delete_started = time.perf_counter()
    if old_ids:
        ids_csv = ",".join(str(int(i)) for i in old_ids)
        conn.execute(text(f"DELETE FROM {SCHEMA}.reconciliacion_detalle_dia WHERE run_id IN ({ids_csv})"))
        conn.execute(text(f"DELETE FROM {SCHEMA}.reconciliacion_detalle WHERE run_id IN ({ids_csv})"))
        conn.execute(text(f"DELETE FROM {SCHEMA}.reconciliacion_run WHERE id IN ({ids_csv})"))
    record_phase('save_run.delete_previous', time.perf_counter() - delete_started,
                 statements=(3 if old_ids else 0), previous_runs=len(old_ids))

    insert_run = text(f"""
        INSERT INTO {SCHEMA}.reconciliacion_run (
            semana_lunes, semana_fin, caso_id, method, active_days, sigma_rel,
            r_global, converged, warnings, actual_t, mt_base_t, mt_opt_t
        )
        OUTPUT INSERTED.id
        VALUES (
            :semana_lunes, :semana_fin, :caso_id, :method, :active_days, :sigma_rel,
            :r_global, :converged, :warnings, :actual_t, :mt_base_t, :mt_opt_t
        );
    """)
    phase_started = time.perf_counter()
    run_id = conn.execute(insert_run, {
        "semana_lunes": week_start,
        "semana_fin": semana_fin,
        "caso_id": caso_id,
        "method": method,
        "active_days": active_days,
        "sigma_rel": sigma_rel,
        "r_global": r_global,
        "converged": 1 if converged else 0,
        "warnings": "\n".join(warnings or []),
        "actual_t": week_row.get('actual_t'),
        "mt_base_t": week_row.get('mt_base_t'),
        "mt_opt_t": week_row.get('mt_opt_t'),
    }).scalar()
    record_phase('save_run.insert_header', time.perf_counter() - phase_started)

    # id de material resuelto UNA vez por label (antes: un SELECT por fila,
    # ~400 round trips extra por corrida) y INSERT en executemany.
    material_ids = {}
    material_lookup_calls = 0
    material_lookup_seconds = 0.0

    def _material_id(label):
        nonlocal material_lookup_calls, material_lookup_seconds
        if label not in material_ids:
            lookup_started = time.perf_counter()
            material_ids[label] = get_material_id(conn, label)
            material_lookup_seconds += time.perf_counter() - lookup_started
            material_lookup_calls += 1
        return material_ids[label]

    detail_columns = (
        'run_id', 'material_id', 'label', 'parcela_nombre', 'estado', 'fdrena',
        'fdrena_prior', 'dia_ciclo', 'w_t', 'z_t', 'q_mean', 'q_pls_mean',
        'cu_drena_mean', 'cu_riego_mean',
    )
    phase_started = time.perf_counter()
    detalle_params = [{
        'run_id': run_id,
        'material_id': _material_id(row.get('label')),
        'label': row.get('label'),
        'parcela_nombre': row.get('parcela_nombre'),
        'estado': row.get('estado'),
        'fdrena': row.get('fdrena'),
        'fdrena_prior': row.get('fdrena_prior'),
        'dia_ciclo': row.get('dia_ciclo'),
        'w_t': row.get('w_t'),
        'z_t': row.get('z_t'),
        'q_mean': row.get('q_mean'),
        'q_pls_mean': row.get('q_pls_mean'),
        'cu_drena_mean': row.get('cu_drena_mean'),
        'cu_riego_mean': row.get('cu_riego_mean'),
    } for row in detalle_rows]
    record_phase('save_run.prepare_detail_batch', time.perf_counter() - phase_started,
                 rows=len(detalle_params))
    phase_started = time.perf_counter()
    detail_statements = _insert_rows_batched(
        conn, f'{SCHEMA}.reconciliacion_detalle', detail_columns, detalle_params)
    record_phase('save_run.insert_detail_batch', time.perf_counter() - phase_started,
                 rows=len(detalle_params), statements=detail_statements)


    daily_columns = (
        'run_id', 'material_id', 'label', 'parcela_nombre', 'dia_offset',
        'fdrena', 'q', 'q_pls', 'cu_drena', 'cu_riego',
    )
    phase_started = time.perf_counter()
    daily_params = [{
        "run_id": run_id,
        "material_id": _material_id(row.get('label')),
        "label": row.get('label'),
        "parcela_nombre": row.get('parcela_nombre'),
        "dia_offset": row.get('dia_offset'),
        "fdrena": row.get('fdrena'),
        "q": row.get('q'),
        "q_pls": row.get('q_pls'),
        "cu_drena": row.get('cu_drena'),
        "cu_riego": row.get('cu_riego'),
    } for row in daily_rows]
    record_phase('save_run.prepare_daily_batch', time.perf_counter() - phase_started,
                 rows=len(daily_params))
    record_phase('save_run.material_lookups', material_lookup_seconds,
                 lookup_calls=material_lookup_calls, labels=len(material_ids))
    phase_started = time.perf_counter()
    daily_statements = _insert_rows_batched(
        conn, f'{SCHEMA}.reconciliacion_detalle_dia', daily_columns, daily_params)
    record_phase('save_run.insert_daily_batch', time.perf_counter() - phase_started,
                 rows=len(daily_params), statements=daily_statements)

    # `conn` viene de get_engine().connect() (no get_engine().begin()): en SQLAlchemy 2.0
    # eso NO autocommitea, y el conn.close() del llamador hacia rollback de
    # toda la corrida -- las tres tablas de reconciliacion quedaban en 0 filas
    # y por eso los graficos por pila (que leen reconciliacion_detalle_dia)
    # salian siempre vacios.
    phase_started = time.perf_counter()
    conn.commit()
    record_phase('save_run.commit', time.perf_counter() - phase_started)
    # Las tablas de reconciliacion acaban de cambiar: el cache local de sus
    # lecturas queda invalido. El resto (riego, Cu, campanas) no se toca.
    phase_started = time.perf_counter()
    for pre in ('recon_run', 'recon_dia', 'recon_semana'):
        _olvidar(pre)
    record_phase('save_run.invalidate_cache', time.perf_counter() - phase_started)
    record_phase('save_run.total', time.perf_counter() - save_started,
                 previous_runs=len(old_ids), detail_rows=len(detalle_params),
                 daily_rows=len(daily_params), material_lookups=material_lookup_calls,
                 delete_statements=(3 if old_ids else 0),
                 batch_statements=(detail_statements + daily_statements))
    return run_id

# ── 3. Database Teardown & Schema Creation ──────────────────────────────────────

# def initialize_database():
#     """Drops old analytical objects in reverse dependency order and rebuilds them cleanly."""
#     print("[Init] Cleaning up old schema objects if they exist...")

#     # 1. Dynamically find and drop any Foreign Keys pointing to our core tables.
#     # This prevents the "Cannot drop object because it is referenced by a FOREIGN KEY" error.
#     strip_fks_sql = f"""
#     DECLARE @sql NVARCHAR(MAX) = N'';
#     SELECT @sql += 'ALTER TABLE ' + QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + '.' + 
#                    QUOTENAME(OBJECT_NAME(parent_object_id)) + ' DROP CONSTRAINT ' + QUOTENAME(name) + ';'
#     FROM sys.foreign_keys
#     WHERE referenced_object_id IN (
#         OBJECT_ID('{SCHEMA}.material'),
#         OBJECT_ID('{SCHEMA}.parcela'),
#         OBJECT_ID('{SCHEMA}.campana'),
#         OBJECT_ID('{SCHEMA}.reconciliacion_run'),
#         OBJECT_ID('dbo.material'),
#         OBJECT_ID('dbo.parcela')
#     );
#     IF @sql IS NOT NULL AND LEN(@sql) > 0
#         EXEC sp_executesql @sql;
#     """

#     # 2. Drop views first, then tables in reverse FK dependency order
#     cleanup_ddl = [
#         strip_fks_sql,
#         f"IF OBJECT_ID('{SCHEMA}.vw_drena_quimica_ingest', 'V') IS NOT NULL DROP VIEW {SCHEMA}.vw_drena_quimica_ingest;",
#         f"IF OBJECT_ID('{SCHEMA}.vw_riego_diario_ingest', 'V') IS NOT NULL DROP VIEW {SCHEMA}.vw_riego_diario_ingest;",
#         f"IF OBJECT_ID('{SCHEMA}.reconciliacion_detalle_dia', 'U') IS NOT NULL DROP TABLE {SCHEMA}.reconciliacion_detalle_dia;",
#         f"IF OBJECT_ID('{SCHEMA}.reconciliacion_detalle', 'U') IS NOT NULL DROP TABLE {SCHEMA}.reconciliacion_detalle;",
#         f"IF OBJECT_ID('{SCHEMA}.reconciliacion_semana', 'U') IS NOT NULL DROP TABLE {SCHEMA}.reconciliacion_semana;",
#         f"IF OBJECT_ID('{SCHEMA}.reconciliacion_run', 'U') IS NOT NULL DROP TABLE {SCHEMA}.reconciliacion_run;",
#         f"IF OBJECT_ID('{SCHEMA}.produccion_planta', 'U') IS NOT NULL DROP TABLE {SCHEMA}.produccion_planta;",
#         f"IF OBJECT_ID('{SCHEMA}.drena_cu_diario', 'U') IS NOT NULL DROP TABLE {SCHEMA}.drena_cu_diario;",
#         f"IF OBJECT_ID('{SCHEMA}.cu_riego_diario', 'U') IS NOT NULL DROP TABLE {SCHEMA}.cu_riego_diario;",
#         f"IF OBJECT_ID('{SCHEMA}.riego_diario', 'U') IS NOT NULL DROP TABLE {SCHEMA}.riego_diario;",
#         f"IF OBJECT_ID('{SCHEMA}.curva_generica', 'U') IS NOT NULL DROP TABLE {SCHEMA}.curva_generica;",
#         f"IF OBJECT_ID('{SCHEMA}.campana', 'U') IS NOT NULL DROP TABLE {SCHEMA}.campana;",
#         f"IF OBJECT_ID('{SCHEMA}.lectura_recuperacion', 'U') IS NOT NULL DROP TABLE {SCHEMA}.lectura_recuperacion;",
#         f"IF OBJECT_ID('{SCHEMA}.parcela', 'U') IS NOT NULL DROP TABLE {SCHEMA}.parcela;",
#         f"IF OBJECT_ID('{SCHEMA}.material', 'U') IS NOT NULL DROP TABLE {SCHEMA}.material;"
#     ]

#     with get_engine().begin() as conn:
#         for stmt in cleanup_ddl:
#             conn.execute(text(stmt))

#     print("[Init] Building fresh schema and catalogs...")

#     build_ddl = [
#         # Catalogs
#         f"""
#         CREATE TABLE {SCHEMA}.material (
#             id INT IDENTITY(1,1) PRIMARY KEY,
#             nombre NVARCHAR(50) NOT NULL UNIQUE
#         );
#         """,
#         f"""
#         CREATE TABLE {SCHEMA}.parcela (
#             id INT IDENTITY(1,1) PRIMARY KEY,
#             id_pad INT NOT NULL FOREIGN KEY REFERENCES {SCHEMA}.material(id),
#             numero INT NOT NULL,
#             nombre NVARCHAR(10) NOT NULL,
#             CONSTRAINT UQ_parcela_material_numero UNIQUE(id_pad, numero),
#             CONSTRAINT UQ_parcela_material_nombre UNIQUE(id_pad, nombre)
#         );
#         """,
#         # Target Tables
#         f"""
#         CREATE TABLE {SCHEMA}.riego_diario (
#             id INT IDENTITY(1,1) PRIMARY KEY,
#             parcela_id INT NOT NULL FOREIGN KEY REFERENCES {SCHEMA}.parcela(id),
#             fecha DATE NOT NULL,
#             caudal_m3h FLOAT NOT NULL,
#             CONSTRAINT UQ_riego_parcela_fecha UNIQUE(parcela_id, fecha)
#         );
#         """,
#         f"""
#         CREATE TABLE {SCHEMA}.lectura_recuperacion (
#             id INT IDENTITY(1,1) PRIMARY KEY,
#             parcela_id INT NOT NULL FOREIGN KEY REFERENCES {SCHEMA}.parcela(id),
#             fecha DATE NOT NULL,
#             valor_pct FLOAT NOT NULL,
#             CONSTRAINT UQ_lectura_parcela_fecha UNIQUE(parcela_id, fecha)
#         );
#         """,
#         f"""
#         CREATE TABLE {SCHEMA}.drena_cu_diario (
#             id INT IDENTITY(1,1) PRIMARY KEY,
#             parcela_id INT NOT NULL FOREIGN KEY REFERENCES {SCHEMA}.parcela(id),
#             fecha DATE NOT NULL,
#             cu_gl FLOAT NULL,
#             h_p FLOAT NULL,
#             ph FLOAT NULL,
#             cl FLOAT NULL,
#             fet FLOAT NULL,
#             fe2 FLOAT NULL,
#             eh FLOAT NULL,
#             CONSTRAINT UQ_drena_parcela_fecha UNIQUE(parcela_id, fecha)
#         );
#         """,
#         f"""
#         CREATE TABLE {SCHEMA}.campana (
#             id INT IDENTITY(1,1) PRIMARY KEY,
#             parcela_id INT NOT NULL FOREIGN KEY REFERENCES {SCHEMA}.parcela(id),
#             numero_campana NVARCHAR(20) NOT NULL,
#             fecha_inicio DATE NOT NULL,
#             fecha_fin DATE NULL,
#             finished BIT NOT NULL,
#             cu_tf FLOAT NULL,
#             CONSTRAINT UQ_campana_parcela_numero UNIQUE(parcela_id, numero_campana)
#         );
#         """,
#         f"""
#         CREATE TABLE {SCHEMA}.cu_riego_diario (
#             id INT IDENTITY(1,1) PRIMARY KEY,
#             id_pad INT NOT NULL FOREIGN KEY REFERENCES {SCHEMA}.material(id),
#             fecha DATE NOT NULL,
#             cu_gl FLOAT NOT NULL,
#             CONSTRAINT UQ_curiego_material_fecha UNIQUE(id_pad, fecha)
#         );
#         """,
#         f"""
#         CREATE TABLE {SCHEMA}.produccion_planta (
#             id INT IDENTITY(1,1) PRIMARY KEY,
#             fecha DATE NOT NULL UNIQUE,
#             valor_t FLOAT NOT NULL
#         );
#         """,
#         # Seed Materials
#         f"""
#         SET IDENTITY_INSERT {SCHEMA}.material ON;
#         INSERT INTO {SCHEMA}.material (id, nombre) VALUES (1, 'OXIDO'), (2, 'SULFURO');
#         SET IDENTITY_INSERT {SCHEMA}.material OFF;
#         """,
#         # Seed Óxidos Parcels (P01..P32)
#         f"""
#         WITH Nums AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM Nums WHERE n < 32)
#         INSERT INTO {SCHEMA}.parcela (id_pad, numero, nombre)
#         SELECT 1, n, 'P' + RIGHT('0' + CAST(n AS VARCHAR(2)), 2) FROM Nums;
#         """,
#         # Seed Sulfuros Parcels (P01..P28)
#         f"""
#         WITH Nums AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM Nums WHERE n < 28)
#         INSERT INTO {SCHEMA}.parcela (id_pad, numero, nombre)
#         SELECT 2, n, 'P' + RIGHT('0' + CAST(n AS VARCHAR(2)), 2) FROM Nums;
#         """,
#         # Ingestion View: Riego
#         f"""
#         CREATE VIEW {SCHEMA}.vw_riego_diario_ingest AS
#         SELECT p.id AS parcela_id, CAST(f.fecha_registro AS DATE) AS fecha, CAST(v.caudal AS FLOAT) AS caudal_m3h
#         FROM {SCHEMA}.{SCHEMA}.flujos_reales_oxido f
#         CROSS APPLY (VALUES
#             ('P01', f.parcela_01), ('P02', f.parcela_02), ('P03', f.parcela_03), ('P04', f.parcela_04),
#             ('P05', f.parcela_05), ('P06', f.parcela_06), ('P07', f.parcela_07), ('P08', f.parcela_08),
#             ('P09', f.parcela_09), ('P10', f.parcela_10), ('P11', f.parcela_11), ('P12', f.parcela_12),
#             ('P13', f.parcela_13), ('P14', f.parcela_14), ('P15', f.parcela_15), ('P16', f.parcela_16),
#             ('P17', f.parcela_17), ('P18', f.parcela_18), ('P19', f.parcela_19), ('P20', f.parcela_20),
#             ('P21', f.parcela_21), ('P22', f.parcela_22), ('P23', f.parcela_23), ('P24', f.parcela_24),
#             ('P25', f.parcela_25), ('P26', f.parcela_26), ('P27', f.parcela_27), ('P28', f.parcela_28),
#             ('P29', f.parcela_29), ('P30', f.parcela_30), ('P31', f.parcela_31), ('P32', f.parcela_32)
#         ) AS v(nombre_parcela, caudal)
#         JOIN {SCHEMA}.parcela p ON p.nombre = v.nombre_parcela AND p.id_pad = 1
#         UNION ALL
#         SELECT p.id AS parcela_id, CAST(f.fecha_registro AS DATE) AS fecha, CAST(v.caudal AS FLOAT) AS caudal_m3h
#         FROM {SCHEMA}.{SCHEMA}.flujos_reales_sulfuro f
#         CROSS APPLY (VALUES
#             ('P01', f.parcela_01), ('P02', f.parcela_02), ('P03', f.parcela_03), ('P04', f.parcela_04),
#             ('P05', f.parcela_05), ('P06', f.parcela_06), ('P07', f.parcela_07), ('P08', f.parcela_08),
#             ('P09', f.parcela_09), ('P10', f.parcela_10), ('P11', f.parcela_11), ('P12', f.parcela_12),
#             ('P13', f.parcela_13), ('P14', f.parcela_14), ('P15', f.parcela_15), ('P16', f.parcela_16),
#             ('P17', f.parcela_17), ('P18', f.parcela_18), ('P19', f.parcela_19), ('P20', f.parcela_20),
#             ('P21', f.parcela_21), ('P22', f.parcela_22), ('P23', f.parcela_23), ('P24', f.parcela_24),
#             ('P25', f.parcela_25), ('P26', f.parcela_26), ('P27', f.parcela_27), ('P28', f.parcela_28)
#         ) AS v(nombre_parcela, caudal)
#         JOIN {SCHEMA}.parcela p ON p.nombre = v.nombre_parcela AND p.id_pad = 2;
#         """,
#         # Ingestion View: Drena
#         f"""
#         CREATE VIEW {SCHEMA}.vw_drena_quimica_ingest AS
#         SELECT 
#             p.id AS parcela_id, CAST(d.fecha_registro AS DATE) AS fecha,
#             NULLIF(CAST(v.cu_pp AS FLOAT), 0) AS cu_gl, NULLIF(CAST(v.h_p AS FLOAT), 0) AS h_p,
#             NULLIF(CAST(v.ph AS FLOAT), 0) AS ph, NULLIF(CAST(v.cl AS FLOAT), 0) AS cl,
#             NULLIF(CAST(v.fet AS FLOAT), 0) AS fet, NULLIF(CAST(v.fe2 AS FLOAT), 0) AS fe2,
#             NULLIF(CAST(v.eh AS FLOAT), 0) AS eh
#         FROM {SCHEMA}.{SCHEMA}.drena_concentrados_oxido d
#         CROSS APPLY (VALUES
#             ('P01', d.p1_cu_pp,  d.p1_h_p,  d.p1_ph,  d.p1_cl,  d.p1_fet,  d.p1_fe2,  d.p1_eh),
#             ('P02', d.p2_cu_pp,  d.p2_h_p,  d.p2_ph,  d.p2_cl,  d.p2_fet,  d.p2_fe2,  d.p2_eh),
#             ('P03', d.p3_cu_pp,  d.p3_h_p,  d.p3_ph,  d.p3_cl,  d.p3_fet,  d.p3_fe2,  d.p3_eh),
#             ('P04', d.p4_cu_pp,  d.p4_h_p,  d.p4_ph,  d.p4_cl,  d.p4_fet,  d.p4_fe2,  d.p4_eh),
#             ('P05', d.p5_cu_pp,  d.p5_h_p,  d.p5_ph,  d.p5_cl,  d.p5_fet,  d.p5_fe2,  d.p5_eh),
#             ('P06', d.p6_cu_pp,  d.p6_h_p,  d.p6_ph,  d.p6_cl,  d.p6_fet,  d.p6_fe2,  d.p6_eh),
#             ('P07', d.p7_cu_pp,  d.p7_h_p,  d.p7_ph,  d.p7_cl,  d.p7_fet,  d.p7_fe2,  d.p7_eh),
#             ('P08', d.p8_cu_pp,  d.p8_h_p,  d.p8_ph,  d.p8_cl,  d.p8_fet,  d.p8_fe2,  d.p8_eh),
#             ('P09', d.p9_cu_pp,  d.p9_h_p,  d.p9_ph,  d.p9_cl,  d.p9_fet,  d.p9_fe2,  d.p9_eh),
#             ('P10', d.p10_cu_pp, d.p10_h_p, d.p10_ph, d.p10_cl, d.p10_fet, d.p10_fe2, d.p10_eh),
#             ('P11', d.p11_cu_pp, d.p11_h_p, d.p11_ph, d.p11_cl, d.p11_fet, d.p11_fe2, d.p11_eh),
#             ('P12', d.p12_cu_pp, d.p12_h_p, d.p12_ph, d.p12_cl, d.p12_fet, d.p12_fe2, d.p12_eh),
#             ('P13', d.p13_cu_pp, d.p13_h_p, d.p13_ph, d.p13_cl, d.p13_fet, d.p13_fe2, d.p13_eh),
#             ('P14', d.p14_cu_pp, d.p14_h_p, d.p14_ph, d.p14_cl, d.p14_fet, d.p14_fe2, d.p14_eh),
#             ('P15', d.p15_cu_pp, d.p15_h_p, d.p15_ph, d.p15_cl, d.p15_fet, d.p15_fe2, d.p15_eh),
#             ('P16', d.p16_cu_pp, d.p16_h_p, d.p16_ph, d.p16_cl, d.p16_fet, d.p16_fe2, d.p16_eh),
#             ('P17', d.p17_cu_pp, d.p17_h_p, d.p17_ph, d.p17_cl, d.p17_fet, d.p17_fe2, d.p17_eh),
#             ('P18', d.p18_cu_pp, d.p18_h_p, d.p18_ph, d.p18_cl, d.p18_fet, d.p18_fe2, d.p18_eh),
#             ('P19', d.p19_cu_pp, d.p19_h_p, d.p19_ph, d.p19_cl, d.p19_fet, d.p19_fe2, d.p19_eh),
#             ('P20', d.p20_cu_pp, d.p20_h_p, d.p20_ph, d.p20_cl, d.p20_fet, d.p20_fe2, d.p20_eh),
#             ('P21', d.p21_cu_pp, d.p21_h_p, d.p21_ph, d.p21_cl, d.p21_fet, d.p21_fe2, d.p21_eh),
#             ('P22', d.p22_cu_pp, d.p22_h_p, d.p22_ph, d.p22_cl, d.p22_fet, d.p22_fe2, d.p22_eh),
#             ('P23', d.p23_cu_pp, d.p23_h_p, d.p23_ph, d.p23_cl, d.p23_fet, d.p23_fe2, d.p23_eh),
#             ('P24', d.p24_cu_pp, d.p24_h_p, d.p24_ph, d.p24_cl, d.p24_fet, d.p24_fe2, d.p24_eh),
#             ('P25', d.p25_cu_pp, d.p25_h_p, d.p25_ph, d.p25_cl, d.p25_fet, d.p25_fe2, d.p25_eh),
#             ('P26', d.p26_cu_pp, d.p26_h_p, d.p26_ph, d.p26_cl, d.p26_fet, d.p26_fe2, d.p26_eh),
#             ('P27', d.p27_cu_pp, d.p27_h_p, d.p27_ph, d.p27_cl, d.p27_fet, d.p27_fe2, d.p27_eh),
#             ('P28', d.p28_cu_pp, d.p28_h_p, d.p28_ph, d.p28_cl, d.p28_fet, d.p28_fe2, d.p28_eh),
#             ('P29', d.p29_cu_pp, d.p29_h_p, d.p29_ph, d.p29_cl, d.p29_fet, d.p29_fe2, d.p29_eh),
#             ('P30', d.p30_cu_pp, d.p30_h_p, d.p30_ph, d.p30_cl, d.p30_fet, d.p30_fe2, d.p30_eh),
#             ('P31', d.p31_cu_pp, d.p31_h_p, d.p31_ph, d.p31_cl, d.p31_fet, d.p31_fe2, d.p31_eh),
#             ('P32', d.p32_cu_pp, d.p32_h_p, d.p32_ph, d.p32_cl, d.p32_fet, d.p32_fe2, d.p32_eh)
#         ) AS v(nombre_parcela, cu_pp, h_p, ph, cl, fet, fe2, eh)
#         JOIN {SCHEMA}.parcela p ON p.nombre = v.nombre_parcela AND p.id_pad = 1
#         UNION ALL
#         SELECT 
#             p.id AS parcela_id, CAST(d.fecha_registro AS DATE) AS fecha,
#             NULLIF(CAST(v.cu_pp AS FLOAT), 0) AS cu_gl, NULLIF(CAST(v.h_p AS FLOAT), 0) AS h_p,
#             NULLIF(CAST(v.ph AS FLOAT), 0) AS ph, NULLIF(CAST(v.cl AS FLOAT), 0) AS cl,
#             NULLIF(CAST(v.fet AS FLOAT), 0) AS fet, NULLIF(CAST(v.fe2 AS FLOAT), 0) AS fe2,
#             NULLIF(CAST(v.eh AS FLOAT), 0) AS eh
#         FROM {SCHEMA}.{SCHEMA}.drena_concentrados_sulfuro d
#         CROSS APPLY (VALUES
#             ('P01', d.p1_cu_pp,  d.p1_h_p,  d.p1_ph,  d.p1_cl,  d.p1_fet,  d.p1_fe2,  d.p1_eh),
#             ('P02', d.p2_cu_pp,  d.p2_h_p,  d.p2_ph,  d.p2_cl,  d.p2_fet,  d.p2_fe2,  d.p2_eh),
#             ('P03', d.p3_cu_pp,  d.p3_h_p,  d.p3_ph,  d.p3_cl,  d.p3_fet,  d.p3_fe2,  d.p3_eh),
#             ('P04', d.p4_cu_pp,  d.p4_h_p,  d.p4_ph,  d.p4_cl,  d.p4_fet,  d.p4_fe2,  d.p4_eh),
#             ('P05', d.p5_cu_pp,  d.p5_h_p,  d.p5_ph,  d.p5_cl,  d.p5_fet,  d.p5_fe2,  d.p5_eh),
#             ('P06', d.p6_cu_pp,  d.p6_h_p,  d.p6_ph,  d.p6_cl,  d.p6_fet,  d.p6_fe2,  d.p6_eh),
#             ('P07', d.p7_cu_pp,  d.p7_h_p,  d.p7_ph,  d.p7_cl,  d.p7_fet,  d.p7_fe2,  d.p7_eh),
#             ('P08', d.p8_cu_pp,  d.p8_h_p,  d.p8_ph,  d.p8_cl,  d.p8_fet,  d.p8_fe2,  d.p8_eh),
#             ('P09', d.p9_cu_pp,  d.p9_h_p,  d.p9_ph,  d.p9_cl,  d.p9_fet,  d.p9_fe2,  d.p9_eh),
#             ('P10', d.p10_cu_pp, d.p10_h_p, d.p10_ph, d.p10_cl, d.p10_fet, d.p10_fe2, d.p10_eh),
#             ('P11', d.p11_cu_pp, d.p11_h_p, d.p11_ph, d.p11_cl, d.p11_fet, d.p11_fe2, d.p11_eh),
#             ('P12', d.p12_cu_pp, d.p12_h_p, d.p12_ph, d.p12_cl, d.p12_fet, d.p12_fe2, d.p12_eh),
#             ('P13', d.p13_cu_pp, d.p13_h_p, d.p13_ph, d.p13_cl, d.p13_fet, d.p13_fe2, d.p13_eh),
#             ('P14', d.p14_cu_pp, d.p14_h_p, d.p14_ph, d.p14_cl, d.p14_fet, d.p14_fe2, d.p14_eh),
#             ('P15', d.p15_cu_pp, d.p15_h_p, d.p15_ph, d.p15_cl, d.p15_fet, d.p15_fe2, d.p15_eh),
#             ('P16', d.p16_cu_pp, d.p16_h_p, d.p16_ph, d.p16_cl, d.p16_fet, d.p16_fe2, d.p16_eh),
#             ('P17', d.p17_cu_pp, d.p17_h_p, d.p17_ph, d.p17_cl, d.p17_fet, d.p17_fe2, d.p17_eh),
#             ('P18', d.p18_cu_pp, d.p18_h_p, d.p18_ph, d.p18_cl, d.p18_fet, d.p18_fe2, d.p18_eh),
#             ('P19', d.p19_cu_pp, d.p19_h_p, d.p19_ph, d.p19_cl, d.p19_fet, d.p19_fe2, d.p19_eh),
#             ('P20', d.p20_cu_pp, d.p20_h_p, d.p20_ph, d.p20_cl, d.p20_fet, d.p20_fe2, d.p20_eh),
#             ('P21', d.p21_cu_pp, d.p21_h_p, d.p21_ph, d.p21_cl, d.p21_fet, d.p21_fe2, d.p21_eh),
#             ('P22', d.p22_cu_pp, d.p22_h_p, d.p22_ph, d.p22_cl, d.p22_fet, d.p22_fe2, d.p22_eh),
#             ('P23', d.p23_cu_pp, d.p23_h_p, d.p23_ph, d.p23_cl, d.p23_fet, d.p23_fe2, d.p23_eh),
#             ('P24', d.p24_cu_pp, d.p24_h_p, d.p24_ph, d.p24_cl, d.p24_fet, d.p24_fe2, d.p24_eh),
#             ('P25', d.p25_cu_pp, d.p25_h_p, d.p25_ph, d.p25_cl, d.p25_fet, d.p25_fe2, d.p25_eh),
#             ('P26', d.p26_cu_pp, d.p26_h_p, d.p26_ph, d.p26_cl, d.p26_fet, d.p26_fe2, d.p26_eh),
#             ('P27', d.p27_cu_pp, d.p27_h_p, d.p27_ph, d.p27_cl, d.p27_fet, d.p27_fe2, d.p27_eh),
#             ('P28', d.p28_cu_pp, d.p28_h_p, d.p28_ph, d.p28_cl, d.p28_fet, d.p28_fe2, d.p28_eh)
#         ) AS v(nombre_parcela, cu_pp, h_p, ph, cl, fet, fe2, eh)
#         JOIN {SCHEMA}.parcela p ON p.nombre = v.nombre_parcela AND p.id_pad = 2;
#         """
#     ]

#     with get_engine().begin() as conn:
#         for stmt in build_ddl:
#             conn.execute(text(stmt))

#     print("[Init] Schema and views successfully initialized.")

# ── 4. Synchronize Data ───────────────────────────────────────────────────────

def sync_riego_data():
    """Extracts irrigation flow rates from unpivoted view into target table."""
    query = f"SELECT parcela_id, fecha, caudal_m3h FROM {SCHEMA}.vw_riego_diario_ingest"
    df = pd.read_sql(query, get_engine())
    print(f"[Riego Sync] Extracted {len(df)} records from view.")

    if df.empty:
        print("[Riego Sync] No data found.")
        return

    merge_sql = f"""
    MERGE {SCHEMA}.riego_diario AS target
    USING (SELECT :parcela_id AS parcela_id, :fecha AS fecha, :caudal_m3h AS caudal_m3h) AS source
    ON (target.parcela_id = source.parcela_id AND target.fecha = source.fecha)
    WHEN MATCHED THEN
        UPDATE SET caudal_m3h = source.caudal_m3h
    WHEN NOT MATCHED THEN
        INSERT (parcela_id, fecha, caudal_m3h)
        VALUES (source.parcela_id, source.fecha, source.caudal_m3h);
    """
    records = df.to_dict(orient="records")
    with get_engine().begin() as conn:
        conn.execute(text(merge_sql), records)
    print("[Riego Sync] Complete.")

def sync_lectura_recuperacion():
    """Extracts historical recovery curve readings from Recuperaciones_pad into target table."""
    query = f"""
    SELECT p.id_parcela AS parcela_id, r.Fecha_drenaje AS fecha, r.Recuperacion_parcela AS valor_pct
    FROM {SCHEMA}.Recuperaciones_pad r
    JOIN {SCHEMA}.parcela p
        ON p.numero = r.Parcela
        AND p.id_pad = CASE r.PAD WHEN 'OXIDOS' THEN 1 WHEN 'SULFUROS' THEN 2 END
    WHERE r.Recuperacion_parcela IS NOT NULL
      AND r.Fecha_drenaje <= CAST(GETDATE() AS DATE)
    """
    df = pd.read_sql(query, get_engine())
    print(f"[Lectura Recuperacion Sync] Extracted {len(df)} records from Recuperaciones_pad.")

    if df.empty:
        print("[Lectura Recuperacion Sync] No data found.")
        return

    df = df.astype(object).where(pd.notna(df), None)

    merge_sql = f"""
    MERGE {SCHEMA}.lectura_recuperacion AS target
    USING (SELECT :parcela_id AS parcela_id, :fecha AS fecha, :valor_pct AS valor_pct) AS source
    ON (target.parcela_id = source.parcela_id AND target.fecha = source.fecha)
    WHEN MATCHED THEN
        UPDATE SET valor_pct = source.valor_pct
    WHEN NOT MATCHED THEN
        INSERT (parcela_id, fecha, valor_pct)
        VALUES (source.parcela_id, source.fecha, source.valor_pct);
    """
    records = df.to_dict(orient="records")
    with get_engine().begin() as conn:
        conn.execute(text(merge_sql), records)
    print("[Lectura Recuperacion Sync] Complete.")

def sync_drena_data():
    """Extracts drainage chemistry from unpivoted view into target table."""
    query = f"""
    SELECT parcela_id, fecha, cu_gl, h_p, ph, cl, fet, fe2, eh 
    FROM {SCHEMA}.vw_drena_quimica_ingest
    """
    df = pd.read_sql(query, get_engine())
    print(f"[Drena Sync] Extracted {len(df)} records from view.")

    if df.empty:
        print("[Drena Sync] No data found.")
        return

    df = df.astype(object).where(pd.notna(df), None)

    merge_sql = f"""
    MERGE {SCHEMA}.drena_cu_diario AS target
    USING (
        SELECT 
            :parcela_id AS parcela_id, :fecha AS fecha, :cu_gl AS cu_gl, 
            :h_p AS h_p, :ph AS ph, :cl AS cl, :fet AS fet, :fe2 AS fe2, :eh AS eh
    ) AS source
    ON (target.parcela_id = source.parcela_id AND target.fecha = source.fecha)
    WHEN MATCHED THEN
        UPDATE SET 
            cu_gl = source.cu_gl, h_p = source.h_p, ph = source.ph, cl = source.cl,
            fet = source.fet, fe2 = source.fe2, eh = source.eh
    WHEN NOT MATCHED THEN
        INSERT (parcela_id, fecha, cu_gl, h_p, ph, cl, fet, fe2, eh)
        VALUES (source.parcela_id, source.fecha, source.cu_gl, source.h_p, source.ph, source.cl, source.fet, source.fe2, source.eh);
    """
    records = df.to_dict(orient="records")
    with get_engine().begin() as conn:
        conn.execute(text(merge_sql), records)
    print("[Drena Sync] Complete.")

def sync_campana():
    """Llena `campana` cruzando `modulos_turnos` con `campana_parcela_control`.

    El Cu fino y el numero de campana salen de `modulos_turnos`, que es la
    tabla de APILADO por modulo-turno: `Finos_cut` ya viene como TMS * CuT_TM
    / 100, y `SUM(Finos_cut)` por (pad, parcela, campana) da las toneladas de
    Cu fino contenido. Es la misma fuente y la misma formula que usa
    `report_metodo.leer_apilado` para el informe de recuperaciones, asi que
    dashboard y libro quedan con un solo denominador.

    Las fechas salen de `campana_parcela_control` (fila por modulo, con
    `fecha_ini_drenaje` / `fecha_fin_drenaje`), agregadas a la parcela: inicio
    = el primer modulo que empieza a drenar, fin = solo cuando TODOS cerraron.
    Cuando esa tabla todavia no tiene la campana -- va por detras del apilado:
    al 2026-08 le faltan 30 pilas, entre ellas los sulfuros P15-P24 que riegan
    la 11 y ahi solo llega la 10 -- se cae al ultimo dia de apilado, que es la
    cota inferior del inicio de riego; el motor afina el arranque real con
    `load_riego_ini` / `arranque_en_ventana`.

    Join usa pad_id (1=OXIDO, 2=SULFURO) directamente -- nombre_pad tiene
    strings inconsistentes ('Sulfuro'/'OXIDOS'/'Oxido') para el mismo pad_id.
    `Parcela` y `nombre_parcela` son el numero de parcela, no el nombre.

    Cuidado con `campana_parcela_control.cut_tm_total`: pese al nombre es la
    LEY del modulo en %CuT (0,45-1,4), no un tonelaje. Esta funcion la copiaba
    como `cu_tf` (de un solo modulo, ademas), y aguas abajo `cu_tf_toneladas`
    la leia como kilotoneladas y la multiplicaba por 1000: ~474 t donde el
    fino contenido son ~5400 t. Con el denominador 11 veces chico las curvas
    de recuperacion salian pegadas en 100 %.
    """
    query = f"""
    WITH apil AS (
        SELECT
            pad_id,
            TRY_CAST(Parcela AS INT) AS parcela_num,
            TRY_CAST(Campana AS INT) AS campana_num,
            MAX(Fecha) AS apilado_fin,
            SUM(Finos_cut) AS cu_tf
        FROM {SCHEMA}.modulos_turnos
        WHERE Parcela IS NOT NULL AND Campana IS NOT NULL AND pad_id IN (1, 2)
        GROUP BY pad_id, TRY_CAST(Parcela AS INT), TRY_CAST(Campana AS INT)
    ),
    dedup AS (
        SELECT
            pad_id,
            TRY_CAST(nombre_parcela AS INT) AS parcela_num,
            TRY_CAST(numero_campana AS INT) AS campana_num,
            modulo_id, fecha_ini_drenaje, fecha_fin_drenaje,
            ROW_NUMBER() OVER (
                PARTITION BY pad_id, nombre_parcela, numero_campana, modulo_id
                ORDER BY id_campana_parcela_control DESC
            ) AS rn
        FROM {SCHEMA}.campana_parcela_control
        WHERE fecha_ini_drenaje IS NOT NULL AND pad_id IN (1, 2)
    ),
    dren AS (
        SELECT
            pad_id, parcela_num, campana_num,
            MIN(fecha_ini_drenaje) AS fecha_inicio,
            CASE WHEN COUNT(*) = COUNT(fecha_fin_drenaje)
                 THEN MAX(fecha_fin_drenaje) END AS fecha_fin
        FROM dedup WHERE rn = 1
        GROUP BY pad_id, parcela_num, campana_num
    )
    SELECT
        p.id_parcela AS parcela_id,
        CAST(a.campana_num AS NVARCHAR(20)) AS numero_campana,
        CAST(COALESCE(d.fecha_inicio, a.apilado_fin) AS DATE) AS fecha_inicio,
        CAST(d.fecha_fin AS DATE) AS fecha_fin,
        CAST(a.cu_tf AS FLOAT) AS cu_tf
    FROM apil a
    LEFT JOIN dren d
        ON d.pad_id = a.pad_id
        AND d.parcela_num = a.parcela_num
        AND d.campana_num = a.campana_num
    JOIN {SCHEMA}.parcela p
        ON p.numero = a.parcela_num
        AND p.id_pad = a.pad_id
    WHERE a.cu_tf > 0
    """
    df = pd.read_sql(query, get_engine())
    print(f"[Campana Sync] Extracted {len(df)} records from campana_parcela_control.")

    if df.empty:
        print("[Campana Sync] No data found.")
        return

    df['finished'] = df['fecha_fin'].notna()
    df = df.astype(object).where(pd.notna(df), None)

    merge_sql = f"""
    MERGE {SCHEMA}.campana AS target
    USING (
        SELECT :parcela_id AS parcela_id, :numero_campana AS numero_campana,
            :fecha_inicio AS fecha_inicio, :fecha_fin AS fecha_fin,
            :finished AS finished, :cu_tf AS cu_tf
    ) AS source
    ON (target.parcela_id = source.parcela_id AND target.numero_campana = source.numero_campana)
    WHEN MATCHED THEN
        UPDATE SET fecha_inicio = source.fecha_inicio, fecha_fin = source.fecha_fin,
            finished = source.finished, cu_tf = source.cu_tf
    WHEN NOT MATCHED THEN
        INSERT (parcela_id, numero_campana, fecha_inicio, fecha_fin, finished, cu_tf)
        VALUES (source.parcela_id, source.numero_campana, source.fecha_inicio, source.fecha_fin, source.finished, source.cu_tf);
    """
    records = df.to_dict(orient="records")
    with get_engine().begin() as conn:
        conn.execute(text(merge_sql), records)
    print("[Campana Sync] Complete.")

def sync_cu_riego():
    """Extrae Cu++ refino de riego (por material, no por parcela) desde las
    vistas base de oxido/sulfuro hacia cu_riego_diario."""
    query = f"""
    SELECT 1 AS material_id, CAST(fecha AS DATE) AS fecha, CAST(cu_pp AS FLOAT) AS cu_gl
    FROM {SCHEMA}.vw_riego_oxido_refino_base
    WHERE cu_pp IS NOT NULL
    UNION ALL
    SELECT 2 AS material_id, CAST(fecha AS DATE) AS fecha, CAST(cu_pp AS FLOAT) AS cu_gl
    FROM {SCHEMA}.vw_riego_sulfuro_refino_base
    WHERE cu_pp IS NOT NULL
    """
    df = pd.read_sql(query, get_engine())
    print(f"[Cu Riego Sync] Extracted {len(df)} records.")

    if df.empty:
        print("[Cu Riego Sync] No data found.")
        return

    # evita filas duplicadas por (material_id, fecha) en el origen
    df = df.drop_duplicates(subset=["material_id", "fecha"], keep="last")
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    df = df.astype(object).where(pd.notna(df), None)

    merge_sql = f"""
    MERGE {SCHEMA}.cu_riego_diario AS target
    USING (SELECT :material_id AS material_id,
                  :fecha       AS fecha,
                  :cu_gl       AS cu_gl) AS source
        ON target.material_id = source.material_id
       AND target.fecha       = source.fecha
    WHEN MATCHED THEN
        UPDATE SET cu_gl = source.cu_gl
    WHEN NOT MATCHED THEN
        INSERT (material_id, fecha, cu_gl)
        VALUES (source.material_id, source.fecha, source.cu_gl);
    """
    records = df.to_dict(orient="records")
    with get_engine().begin() as conn:
        conn.execute(text(merge_sql), records)
    print(f"[Cu Riego Sync] Complete. {len(records)} rows merged.")

def sync_produccion():
    """Extracts produccion catodica real diaria hacia produccion_planta."""
    query = f"""
    SELECT CAST(fecha_registro AS DATE) AS fecha, CAST(real_produccion_ton AS FLOAT) AS valor_t
    FROM {SCHEMA}.produccion_catodica
    WHERE real_produccion_ton IS NOT NULL
    """
    df = pd.read_sql(query, get_engine())
    print(f"[Produccion Sync] Extracted {len(df)} records.")

    if df.empty:
        print("[Produccion Sync] No data found.")
        return

    df = df.astype(object).where(pd.notna(df), None)

    merge_sql = f"""
    MERGE {SCHEMA}.produccion_planta AS target
    USING (SELECT :fecha AS fecha, :valor_t AS valor_t) AS source
    ON (target.fecha = source.fecha)
    WHEN MATCHED THEN
        UPDATE SET valor_t = source.valor_t
    WHEN NOT MATCHED THEN
        INSERT (fecha, valor_t)
        VALUES (source.fecha, source.valor_t);
    """
    records = df.to_dict(orient="records")
    with get_engine().begin() as conn:
        conn.execute(text(merge_sql), records)
    print("[Produccion Sync] Complete.")

# ── 5. Orquestacion y frescura de datos ─────────────────────────────────────────

# Orden de sync_all(): riego y drena primero (las mas grandes, ~220-250k filas,
# lo que mas tarda), despues las tablas chicas. Cada sync_* corre en su propio
# try/except -- una vista rota (ej. vw_riego_diario_ingest caida) no debe
# bloquear que las demas tablas se actualicen.
_SYNC_STEPS = [
    ("riego_diario", sync_riego_data),
    ("drena_cu_diario", sync_drena_data),
    ("lectura_recuperacion", sync_lectura_recuperacion),
    ("campana", sync_campana),
    ("cu_riego_diario", sync_cu_riego),
    ("produccion_planta", sync_produccion),
]


def sync_all():
    """Corre las seis sync_* en orden, aislando fallas: una vista/tabla origen
    caida no debe abortar el resto. Devuelve una lista de dict
    {tabla, ok, filas, error} -- `filas` es el conteo POST-sync de la tabla
    destino (no "filas nuevas", MERGE no distingue insert de update aqui)."""
    report = []
    for tabla, fn in _SYNC_STEPS:
        try:
            fn()
            with get_engine().connect() as conn:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {SCHEMA}.{tabla}")).scalar()
            report.append(dict(tabla=tabla, ok=True, filas=int(n), error=None))
        except Exception as e:
            report.append(dict(tabla=tabla, ok=False, filas=None, error=str(e)))
    return report


# (tabla destino, columna fecha, SQL de la fuente con columna 'fecha')
_FRESHNESS_SOURCES = [
    ("riego_diario", "fecha", f"SELECT fecha FROM {SCHEMA}.vw_riego_diario_ingest"),
    ("drena_cu_diario", "fecha", f"SELECT fecha FROM {SCHEMA}.vw_drena_quimica_ingest"),
    ("lectura_recuperacion", "fecha", f"SELECT Fecha_drenaje AS fecha FROM {SCHEMA}.Recuperaciones_pad"),
    ("cu_riego_diario", "fecha", f"""
        SELECT fecha FROM {SCHEMA}.vw_riego_oxido_refino_base
        UNION ALL SELECT fecha FROM {SCHEMA}.vw_riego_sulfuro_refino_base
    """),
    ("campana", "fecha_inicio", f"SELECT fecha_ini_drenaje AS fecha FROM {SCHEMA}.campana_parcela_control"),
    ("produccion_planta", "fecha", f"SELECT fecha_registro AS fecha FROM {SCHEMA}.produccion_catodica"),
]


def data_freshness():
    """Compara, para cada tabla materializada que consume la reconciliacion,
    su MAX(fecha) contra el MAX(fecha) de su fuente (vista o tabla origen).
    `dias_atraso` es la brecha en dias -- 0 si esta al dia, None si alguna de
    las dos esta vacia (nunca sincronizada / fuente sin datos)."""
    out = []
    with get_engine().connect() as conn:
        for tabla, col, fuente_sql in _FRESHNESS_SOURCES:
            max_tabla = conn.execute(text(f"SELECT MAX({col}) FROM {SCHEMA}.{tabla}")).scalar()
            max_fuente = conn.execute(text(f"SELECT MAX(fecha) FROM ({fuente_sql}) f")).scalar()
            # DATE vs DATETIME segun la columna/vista -- normalizar antes de
            # restar (datetime.date - datetime.datetime revienta con TypeError).
            if max_tabla is not None and max_fuente is not None:
                dias_atraso = (pd.Timestamp(max_fuente).normalize() - pd.Timestamp(max_tabla).normalize()).days
            else:
                dias_atraso = None
            out.append(dict(
                tabla=tabla, fuente=fuente_sql.strip().splitlines()[0][:60] + "...",
                max_tabla=max_tabla, max_fuente=max_fuente, dias_atraso=dias_atraso,
            ))
    return out


# ── 6. Main Execution ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting database synchronization...")
    #initialize_database()
    for row in sync_all():
        if row["ok"]:
            print(f'  OK   {row["tabla"]:24s} filas={row["filas"]:,}')
        else:
            print(f'  FAIL {row["tabla"]:24s} {row["error"][:120]}')
    print()
    print("Frescura de datos (tabla vs fuente):")
    for row in data_freshness():
        atraso = f'{row["dias_atraso"]} dias' if row["dias_atraso"] is not None else 'n/a'
        print(f'  {row["tabla"]:24s} tabla={row["max_tabla"]}  fuente={row["max_fuente"]}  atraso={atraso}')
    print("Database sync finished.")
