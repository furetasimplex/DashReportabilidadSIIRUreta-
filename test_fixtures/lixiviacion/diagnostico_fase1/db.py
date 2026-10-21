"""Solo lectura de V2. Sin reglas hidráulicas, conversiones ni deduplicaciones."""
from datetime import date
import re
from sqlalchemy import text
from db_connection import get_engine

SOURCE = 'inventar_SpcHidr.vw_tablero_lixiviacion_final_v2'
PAD = "CASE pad_id WHEN 1 THEN N'Óxidos' WHEN 2 THEN N'Sulfuros' ELSE N'PAD desconocido' END"
DETAIL = {
    'fecha': 'fecha', 'pad': PAD, 'parcela': 'nro_parcela_pad',
    'campana': 'numero_campana', 'estado': 'estado_asignacion',
    'flujo_m3_d': 'flujo_m3_d', 'cu_drenaje_gl': 'cu_drenaje_gl',
    'cu_refino_gl': 'cu_refino_gl', 'delta_cu_gl': 'delta_cu_gl',
    'transferencia_cu_t_d': 'transferencia_cu_t_d',
}


def where(filters):
    try:
        start = date.fromisoformat(filters['desde'][:10])
        end = date.fromisoformat(filters['hasta'][:10])
    except (TypeError, KeyError, ValueError):
        raise ValueError('Seleccione fecha inicio y fecha fin válidas.') from None
    if start > end:
        raise ValueError('La fecha inicio debe ser anterior o igual a la fecha fin.')
    clauses = ['fecha BETWEEN :desde AND :hasta']
    params = {'desde': start, 'hasta': end}
    for field, column in [('pad', 'pad_id'), ('campana', 'campana_id'), ('parcela', 'parcela_id')]:
        value = filters.get(field)
        if value not in (None, ''):
            params[field] = int(value)
            clauses.append(f'{column} = :{field}')
    state = filters.get('estado')
    if state:
        if state not in ('CAMPANA_HIDRAULICA', 'FUERA_VENTANA_RIEGO'):
            raise ValueError('Estado no válido.')
        params['estado'] = state
        clauses.append('estado_asignacion = :estado')
    return ' AND '.join(clauses), params


def _connection():
    engine = get_engine()
    if engine is None:
        raise RuntimeError('Conexión SQL no disponible.')
    return engine.connect()


def options(filters):
    # Facetas mutuamente filtradas; omitir solo la selección propia.
    with _connection() as conn:
        result = []
        for field, cols in [('campana', 'pad_id,campana_id,numero_campana'),
                            ('parcela', 'pad_id,parcela_id,nro_parcela_pad')]:
            w, params = where({**filters, field: None})
            sql = f'SELECT DISTINCT {cols} FROM {SOURCE} WHERE {w}'
            if field == 'campana':
                sql += ' AND campana_id IS NOT NULL'
            sql += ' ORDER BY ' + cols
            result.append([dict(r) for r in conn.execute(text(sql), params).mappings()])
    return result


def overview(filters):
    w, params = where(filters)
    summary = f'''SELECT COUNT_BIG(*) AS registros,SUM(flujo_m3_d) AS flujo,
        SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,
        COUNT_BIG(CASE WHEN estado_asignacion='FUERA_VENTANA_RIEGO' THEN 1 END) AS fuera
        FROM {SOURCE} WHERE {w}'''
    daily = f'''SELECT fecha,pad_id,SUM(flujo_m3_d) AS flujo,
        AVG(cu_drenaje_gl) AS drenaje,AVG(cu_refino_gl) AS refino,
        SUM(transferencia_cu_t_d) AS transferencia
        FROM {SOURCE} WHERE {w} GROUP BY fecha,pad_id ORDER BY fecha,pad_id'''
    with _connection() as conn:
        totals = dict(conn.execute(text(summary), params).mappings().one())
        rows = [dict(r) for r in conn.execute(text(daily), params).mappings()]
    return totals, rows


def table_predicate(query):
    """Gramática restringida: expresiones {columna} operador valor unidas por &&."""
    clauses, params = [], {}
    if not query:
        return clauses, params
    operators = {'eq': '=', 'ne': '<>', 'ge': '>=', 'le': '<=', 'gt': '>', 'lt': '<',
                 '=': '=', '!=': '<>', '>=': '>=', '<=': '<=', '>': '>', '<': '<'}
    for i, fragment in enumerate(query.split('&&')):
        match = re.fullmatch(r'\s*\{(\w+)\}\s*(contains|datestartswith|eq|ne|ge|le|gt|lt|>=|<=|!=|=|>|<)\s*(.*?)\s*', fragment)
        if not match or match[1] not in DETAIL:
            raise ValueError('Filtro de tabla no válido. Use =, >=, <= o contains; combine con &&.')
        col, op, value = match.groups()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '\"\'':
            value = value[1:-1]
        key = f'tf{i}'
        if op in ('contains', 'datestartswith'):
            value = value.replace('~', '~~').replace('%', '~%').replace('_', '~_').replace('[', '~[')
            params[key] = ('%' if op == 'contains' else '') + value + '%'
            clauses.append(f"CONVERT(nvarchar(100),{DETAIL[col]},23) LIKE :{key} ESCAPE '~'")
        else:
            params[key] = value
            clauses.append(f'{DETAIL[col]} {operators[op]} :{key}')
    return clauses, params


def detail(filters, page=0, page_size=25, sort_by=None, filter_query=''):
    w, params = where(filters)
    clauses, extra = table_predicate(filter_query)
    if clauses:
        w += ' AND ' + ' AND '.join(clauses)
    params.update(extra)
    order = []
    for item in sort_by or []:
        if item.get('column_id') not in DETAIL or item.get('direction') not in ('asc', 'desc'):
            raise ValueError('Orden de tabla no válido.')
        order.append(f"{DETAIL[item['column_id']]} {item['direction']}")
    order.extend(['fecha', 'pad_id', 'parcela_id'])
    size = min(100, max(1, int(page_size)))
    with _connection() as conn:
        count = conn.execute(text(f'SELECT COUNT_BIG(*) FROM {SOURCE} WHERE {w}'), params).scalar_one()
        page = min(max(0, int(page)), max(0, (count-1)//size))
        params.update(offset=page*size, size=size)
        sql = f'''SELECT {','.join(expr+' AS '+col for col, expr in DETAIL.items())}
            FROM {SOURCE} WHERE {w} ORDER BY {','.join(order)}
            OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY'''
        rows = [dict(r) for r in conn.execute(text(sql), params).mappings()]
    return rows, count, page
