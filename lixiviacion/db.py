"""Solo lectura de V2. Sin reglas hidráulicas, conversiones ni deduplicaciones."""
from datetime import date
import re
from sqlalchemy import text
from db_connection import get_engine

SOURCE = 'inventar_SpcHidr.vw_tablero_lixiviacion_final_v2'
HYDRAULIC_LABELS = {'CAMPANA_HIDRAULICA': 'Campaña hidráulica',
                    'FUERA_VENTANA_RIEGO': 'Fuera de ventana hidráulica'}
OP_SOURCE = 'inventar_SpcHidr.fn_estado_operacional_parcela_diario'
OP_FIELDS = ('fecha','pad_id','parcela_id','numero_parcela','campana_id','numero_campana',
             'estado_operacional','calidad_estado','tiene_dato_riego','riego_activo',
             'tiene_dato_drenaje','drenaje_activo')
OP_HEADER_SQL = f'''SELECT {','.join('e.'+c for c in OP_FIELDS)},
    v.campana_id AS campana_hidraulica_id,v.numero_campana AS numero_campana_hidraulica,
    v.estado_asignacion
    FROM {OP_SOURCE}(:fecha) e LEFT JOIN {SOURCE} v
      ON v.fecha=e.fecha AND v.pad_id=e.pad_id AND v.parcela_id=e.parcela_id
    WHERE (:pad_id IS NULL OR e.pad_id=:pad_id) AND e.parcela_id=:parcela_id'''
OP_TIMELINE_SQL = '''-- Timeline DEV: candidato genérico validado, contrato runtime original de 12 columnas.
-- Parámetros enlazados SQLAlchemy: desde, hasta, pad_id, parcela_id.
-- CASE de estado y calidad copiados de la definición oficial capturada.
WITH fechas AS (
    SELECT CAST(:desde AS date) AS fecha
    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(:hasta AS date)
), parcela AS (
    SELECT p.id_pad AS pad_id,pa.nombre AS nombre_pad,p.id_parcela AS parcela_id,p.numero AS numero_parcela
    FROM inventar_SpcHidr.parcela p INNER JOIN inventar_SpcHidr.pad pa ON pa.id_pad=p.id_pad
    WHERE p.id_pad=:pad_id AND p.id_parcela=:parcela_id
      AND ((p.id_pad=1 AND p.numero BETWEEN 1 AND 32) OR (p.id_pad=2 AND p.numero BETWEEN 1 AND 28))
), campanas AS (
    SELECT c.pad_id,c.campana_id,c.parcela_id,MAX(c.numero_campana) AS numero_campana,
           MIN(c.fecha_ini_carguio) AS fecha_ini_campana
    FROM inventar_SpcHidr.campana_parcela_control c
    INNER JOIN parcela p ON p.pad_id=c.pad_id AND p.parcela_id=c.parcela_id
    WHERE c.fecha_ini_carguio IS NOT NULL
    GROUP BY c.pad_id,c.campana_id,c.parcela_id
), ventanas AS (
    SELECT c.*,LEAD(c.fecha_ini_campana) OVER
        (PARTITION BY c.pad_id,c.parcela_id ORDER BY c.fecha_ini_campana,c.campana_id) AS fecha_ini_campana_siguiente
    FROM campanas c
), campanas_rango AS (
    -- LEAD ya calculado sobre todas las campañas de la parcela, antes del filtro de rango.
    SELECT * FROM ventanas
    WHERE fecha_ini_campana<=CAST(:hasta AS date)
      AND (fecha_ini_campana_siguiente IS NULL OR fecha_ini_campana_siguiente>CAST(:desde AS date))
), riego_fuente AS (
    SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor
        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_oxido_unpivot s
          ON p.pad_id=1 AND s.parcela_numero=p.numero_parcela
        UNION ALL
        SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor
        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_sulfuro_unpivot s
          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela
), drenaje_fuente AS (
    SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor
        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_oxido_operacional s
          ON p.pad_id=1 AND s.parcela_numero=p.numero_parcela
        UNION ALL
        SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor
        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_sulfuro_operacional s
          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela
), riego_extremos AS (
    -- Ventana completa, nunca recortada a las fechas visibles.
    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(r.fecha) AS fecha_primer_riego_real,
           MAX(r.fecha) AS fecha_ultimo_riego_real
    FROM campanas_rango c INNER JOIN riego_fuente r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id
      AND r.fecha>=c.fecha_ini_campana
      AND (c.fecha_ini_campana_siguiente IS NULL OR r.fecha<c.fecha_ini_campana_siguiente)
      AND r.valor>1
    GROUP BY c.pad_id,c.parcela_id,c.campana_id
), drenaje_extremos AS (
    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(d.fecha) AS fecha_primer_drenaje_real,
           MAX(d.fecha) AS fecha_ultimo_drenaje_real
    FROM campanas_rango c INNER JOIN drenaje_fuente d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id
      AND d.fecha>=c.fecha_ini_campana
      AND (c.fecha_ini_campana_siguiente IS NULL OR d.fecha<c.fecha_ini_campana_siguiente)
      AND d.valor>0
    GROUP BY c.pad_id,c.parcela_id,c.campana_id
), contexto AS (
    SELECT c.*,r.fecha_primer_riego_real,r.fecha_ultimo_riego_real,d.fecha_primer_drenaje_real,d.fecha_ultimo_drenaje_real
    FROM campanas_rango c
    LEFT JOIN riego_extremos r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id AND r.campana_id=c.campana_id
    LEFT JOIN drenaje_extremos d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id AND d.campana_id=c.campana_id
), riego_dia AS (
    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_riego,
        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>1 THEN 1 ELSE 0 END) END AS riego_activo
    FROM riego_fuente WHERE fecha BETWEEN CAST(:desde AS date) AND CAST(:hasta AS date)
    GROUP BY pad_id,parcela_id,fecha
), drenaje_dia AS (
    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_drenaje,
        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>0 THEN 1 ELSE 0 END) END AS drenaje_activo
    FROM drenaje_fuente WHERE fecha BETWEEN CAST(:desde AS date) AND CAST(:hasta AS date)
    GROUP BY pad_id,parcela_id,fecha
), dias AS (
    SELECT f.fecha,p.*,c.campana_id,c.numero_campana,
        c.fecha_primer_riego_real,c.fecha_ultimo_riego_real,c.fecha_primer_drenaje_real,c.fecha_ultimo_drenaje_real,
        r.tiene_dato_riego,r.riego_activo,d.tiene_dato_drenaje,d.drenaje_activo
    FROM fechas f CROSS JOIN parcela p
    LEFT JOIN contexto c ON c.pad_id=p.pad_id AND c.parcela_id=p.parcela_id
      AND f.fecha>=c.fecha_ini_campana AND (c.fecha_ini_campana_siguiente IS NULL OR f.fecha<c.fecha_ini_campana_siguiente)
    LEFT JOIN riego_dia r ON r.pad_id=p.pad_id AND r.parcela_id=p.parcela_id AND r.fecha=f.fecha
    LEFT JOIN drenaje_dia d ON d.pad_id=p.pad_id AND d.parcela_id=p.parcela_id AND d.fecha=f.fecha
), base_modulos AS (
    SELECT c.*,d.fecha,d.tiene_dato_riego,d.riego_activo,d.tiene_dato_drenaje,d.drenaje_activo,
        d.fecha_primer_riego_real,d.fecha_ultimo_riego_real,d.fecha_primer_drenaje_real,d.fecha_ultimo_drenaje_real
    FROM dias d INNER JOIN inventar_SpcHidr.campana_parcela_control c
      ON c.pad_id=d.pad_id AND c.parcela_id=d.parcela_id AND c.campana_id=d.campana_id
    WHERE c.fecha_ini_carguio IS NOT NULL AND c.fecha_ini_carguio<=d.fecha
), estado_modulo AS (
    SELECT b.*,CASE

                WHEN b.fecha_fin_retiro IS NOT NULL
                 AND b.fecha > b.fecha_fin_retiro
                    THEN 'RECLAMADO'

                WHEN b.fecha_ini_retiro IS NOT NULL
                 AND b.fecha >= b.fecha_ini_retiro
                 AND
                 (
                     b.fecha_fin_retiro IS NULL
                     OR b.fecha <= b.fecha_fin_retiro
                 )
                    THEN 'RECLAMO'

                WHEN b.fecha >= b.fecha_ini_carguio
                 AND
                 (
                     b.fecha_fin_carguio IS NULL
                     OR b.fecha < b.fecha_fin_carguio
                 )
                    THEN 'APILADO'

                WHEN b.fecha_fin_carguio IS NOT NULL
                 AND b.fecha >= b.fecha_fin_carguio
                 AND
                 (
                     b.fecha_primer_riego_real IS NULL
                     OR b.fecha < b.fecha_primer_riego_real
                 )
                    THEN 'CONFORMADO_PRE_RIEGO'

                WHEN b.fecha_primer_riego_real IS NOT NULL
                 AND b.fecha >= b.fecha_primer_riego_real
                 AND
                 (
                     b.tiene_dato_riego IS NULL
                     OR b.riego_activo IS NULL
                     OR b.tiene_dato_drenaje IS NULL
                     OR b.drenaje_activo IS NULL
                 )
                    THEN 'SIN_COBERTURA_HIDRAULICA'

                WHEN b.riego_activo = 1
                 AND b.drenaje_activo = 1
                    THEN 'RIEGO_DRENAJE'

                WHEN b.riego_activo = 1
                 AND b.drenaje_activo = 0
                    THEN 'RIEGO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 1
                 AND b.fecha_ultimo_riego_real IS NOT NULL
                 AND b.fecha > b.fecha_ultimo_riego_real
                    THEN 'DRENAJE_RESIDUAL'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 1
                    THEN 'DRENAJE_CON_RIEGO_PAUSADO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 0

                 AND b.fecha_ultimo_riego_real IS NOT NULL
                 AND b.fecha > b.fecha_ultimo_riego_real

                 AND
                 (
                     b.fecha_ultimo_drenaje_real IS NULL
                     OR b.fecha > b.fecha_ultimo_drenaje_real
                 )

                 AND
                 (
                     b.fecha_ini_retiro IS NULL
                     OR b.fecha < b.fecha_ini_retiro
                 )
                    THEN 'REPOSO_PRE_RECLAMO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 0
                    THEN 'PAUSA_HIDRAULICA'

                ELSE 'SIN_CLASIFICAR'

            END AS estado_modulo FROM base_modulos b
), distribucion AS (
    SELECT fecha,pad_id,campana_id,parcela_id,MAX(numero_campana) AS numero_campana,
        estado_modulo,COUNT(*) AS cantidad_modulos
    FROM estado_modulo GROUP BY fecha,pad_id,campana_id,parcela_id,estado_modulo
), resumen AS (
    SELECT fecha,pad_id,campana_id,parcela_id,MAX(numero_campana) AS numero_campana,
        SUM(cantidad_modulos) AS modulos_total,COUNT(*) AS estados_distintos,
        CASE WHEN COUNT(*)=1 THEN MAX(estado_modulo) ELSE 'MIXTO' END AS estado_operacional,
        STRING_AGG(CAST(CONCAT(estado_modulo,' = ',cantidad_modulos) AS varchar(max)),' | ') AS composicion_modulos
    FROM distribucion GROUP BY fecha,pad_id,campana_id,parcela_id
), hitos AS (
    SELECT fecha,pad_id,campana_id,parcela_id,MIN(fecha_ini_carguio) AS fecha_ini_carguio,
        MAX(fecha_fin_carguio) AS fecha_conformado,MIN(fecha_ini_retiro) AS fecha_ini_reclamo,MAX(fecha_fin_retiro) AS fecha_fin_reclamo
    FROM estado_modulo GROUP BY fecha,pad_id,campana_id,parcela_id
)
SELECT d.fecha,
    d.pad_id,
    d.parcela_id,
    d.numero_parcela,
    d.campana_id,
    d.numero_campana,
    COALESCE(r.estado_operacional,'SIN_INFORMACION') AS estado_operacional,
    CASE
            WHEN r.estado_operacional IS NULL
                THEN 'SIN_INFORMACION'

            WHEN r.estado_operacional =
                 'SIN_COBERTURA_HIDRAULICA'
                THEN 'NO_EVALUABLE'

            WHEN r.estado_operacional = 'MIXTO'
             AND r.composicion_modulos
                 LIKE '%SIN_COBERTURA_HIDRAULICA%'
                THEN 'PARCIAL'

            ELSE 'EVALUABLE'
        END AS calidad_estado,
    d.tiene_dato_riego,
    d.riego_activo,
    d.tiene_dato_drenaje,
    d.drenaje_activo
FROM dias d
LEFT JOIN resumen r ON r.fecha=d.fecha AND r.pad_id=d.pad_id AND r.parcela_id=d.parcela_id AND r.campana_id=d.campana_id
LEFT JOIN hitos h ON h.fecha=d.fecha AND h.pad_id=d.pad_id AND h.parcela_id=d.parcela_id AND h.campana_id=d.campana_id
ORDER BY d.fecha OPTION (MAXRECURSION 32767)
'''
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
        if col == 'estado':
            value = {label: code for code, label in HYDRAULIC_LABELS.items()}.get(value, value)
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


def operational(filters):
    """Dos SELECT por parcela; campaña/estado hidráulicos no filtran el ciclo operacional."""
    if filters.get('parcela') is None:
        return None, []
    where(filters)  # validación de las fechas aplicadas, sin modificar filtros
    start, end = date.fromisoformat(filters['desde'][:10]), date.fromisoformat(filters['hasta'][:10])
    if (end-start).days > 32767:
        raise ValueError('Período operacional excede el calendario disponible.')
    params = {'fecha': end, 'pad_id': int(filters['pad']) if filters.get('pad') is not None else None,
              'parcela_id': int(filters['parcela'])}
    with _connection() as conn:
        header = [dict(r) for r in conn.execute(text(OP_HEADER_SQL), params).mappings()]
        if len(header) > 1:
            raise ValueError('Clave operacional duplicada o parcela ambigua.')
        if not header:
            return None, []
        h = header[0]
        if h['fecha'] != end or h['parcela_id'] != params['parcela_id'] or (params['pad_id'] is not None and h['pad_id'] != params['pad_id']):
            raise ValueError('Identidad operacional inconsistente.')
        timeline = [dict(r) for r in conn.execute(text(OP_TIMELINE_SQL),
            {'desde': start, 'hasta': end, 'pad_id': h['pad_id'], 'parcela_id': h['parcela_id']}).mappings()]
    seen = set()
    for row in timeline:
        if row['fecha'] in seen or not start <= row['fecha'] <= end or (row['pad_id'],row['parcela_id']) != (h['pad_id'],h['parcela_id']):
            raise ValueError('Grano operacional inválido; no se deduplican filas.')
        seen.add(row['fecha'])
    return h, timeline
