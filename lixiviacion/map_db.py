"""Estado operacional diario: una lectura parametrizada, sin derivar estados."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from sqlalchemy import text
from .db import _connection

SOURCE = 'inventar_SpcHidr.fn_estado_operacional_parcela_diario'
FIELDS = ('fecha','pad_id','nombre_pad','parcela_id','numero_parcela','campana_id',
          'numero_campana','modulos_total','estados_distintos','estado_operacional',
          'composicion_modulos','tiene_dato_riego','riego_activo','tiene_dato_drenaje',
          'drenaje_activo','fecha_ini_carguio','fecha_conformado','fecha_primer_riego',
          'fecha_ultima_actividad_riego','fecha_ini_drenaje','fecha_ultima_actividad_drenaje',
          'fecha_ini_reclamo','fecha_fin_reclamo','calidad_estado')
DAILY_SQL = f"SELECT {','.join(FIELDS)} FROM {SOURCE}(:fecha)"

MODULE_SQL = '''SELECT
    fecha, pad_id, nombre_pad, parcela_id, numero_parcela,
    campana_id, numero_campana, modulo_id, nombre_modulo,
    secuencia_carguio, secuencia_retiro, estado_modulo,
    fecha_ini_carguio, fecha_fin_carguio, fecha_ini_reclamo, fecha_fin_reclamo
FROM inventar_SpcHidr.fn_estado_operacional_modulo_diario(
    :fecha, :pad_id, :parcela_id
)
ORDER BY COALESCE(secuencia_carguio, 999999), nombre_modulo'''


# Fechas registradas en las mismas fuentes que usa SOURCE; no infiere estados.
LATEST_DATE_SQL = '''WITH parcelas AS (
    SELECT id_pad AS pad_id, id_parcela AS parcela_id, numero
    FROM inventar_SpcHidr.parcela
    WHERE (id_pad=1 AND numero BETWEEN 1 AND 32)
       OR (id_pad=2 AND numero BETWEEN 1 AND 28)
), fechas AS (
    SELECT MAX(r.fecha_registro) AS fecha
    FROM inventar_SpcHidr.v_flujos_oxido_unpivot r
    INNER JOIN parcelas p ON p.pad_id=1 AND p.numero=r.parcela_numero
    WHERE r.fecha_registro < DATEADD(day,1,CAST(:hasta AS date))
    UNION ALL
    SELECT MAX(r.fecha_registro)
    FROM inventar_SpcHidr.v_flujos_sulfuro_unpivot r
    INNER JOIN parcelas p ON p.pad_id=2 AND p.numero=r.parcela_numero
    WHERE r.fecha_registro < DATEADD(day,1,CAST(:hasta AS date))
    UNION ALL
    SELECT MAX(d.fecha_operacional)
    FROM inventar_SpcHidr.v_drena_oxido_operacional d
    INNER JOIN parcelas p ON p.pad_id=1 AND p.numero=d.parcela_numero
    WHERE d.fecha_operacional <= CAST(:hasta AS date)
    UNION ALL
    SELECT MAX(d.fecha_operacional)
    FROM inventar_SpcHidr.v_drena_sulfuro_operacional d
    INNER JOIN parcelas p ON p.pad_id=2 AND p.numero=d.parcela_numero
    WHERE d.fecha_operacional <= CAST(:hasta AS date)
    UNION ALL
    SELECT MAX(h.fecha)
    FROM inventar_SpcHidr.campana_parcela_control c
    INNER JOIN parcelas p ON p.pad_id=c.pad_id AND p.parcela_id=c.parcela_id
    CROSS APPLY (VALUES (c.fecha_ini_carguio), (c.fecha_fin_carguio),
                        (c.fecha_ini_retiro), (c.fecha_fin_retiro)) h(fecha)
    WHERE c.fecha_ini_carguio <= CAST(:hasta AS date)
      AND h.fecha <= CAST(:hasta AS date)
)
SELECT CAST(MAX(fecha) AS date) AS ultima_fecha FROM fechas'''


def latest_operational_date():
    """Última fecha registrada del mapa hasta hoy en Chile, o None sin fuentes."""
    today = datetime.now(ZoneInfo('America/Santiago')).date()
    with _connection() as conn:
        latest = conn.execute(text(LATEST_DATE_SQL), {'hasta': today}).scalar_one()
    return latest.isoformat() if latest is not None else None


def source_coverage(selected_date):
    """Metadatos de las mismas vistas V2; cero observado cuenta como dato."""
    from . import phase_flags
    day = date.fromisoformat(selected_date)
    parts = []
    for pad, count, irrigation, chemistry in (
        (1,32,'v_flujos_oxido_unpivot','v_drena_oxido_operacional'),
        (2,28,'v_flujos_sulfuro_unpivot','v_drena_sulfuro_operacional'),
    ):
        for kind, view, field, day_field in (
            ('riego',irrigation,'caudal','fecha_registro'),
            ('quimica',chemistry,'cu_pp','fecha_operacional'),
        ):
            parts.append(f"""SELECT {pad} pad_id, '{kind}' fuente,
                MAX(CASE WHEN {field} IS NOT NULL THEN CAST({day_field} AS date) END) ultima_fecha,
                COUNT(DISTINCT CASE WHEN CAST({day_field} AS date)=:fecha AND {field} IS NOT NULL
                                    THEN parcela_numero END) parcelas_con_dato,
                {count} parcelas_esperadas
                FROM inventar_SpcHidr.{view} WHERE parcela_numero BETWEEN 1 AND {count}""")
    with _connection() as conn:
        phase_flags.guard_connection(conn)
        return [dict(r) for r in conn.execute(text(' UNION ALL '.join(parts)),{'fecha':day}).mappings()]


def fetch_modulos_parcela(fecha, pad_id, parcela_id):
    params = {'fecha': date.fromisoformat(fecha), 'pad_id': int(pad_id), 'parcela_id': int(parcela_id)}
    with _connection() as conn:
        return [dict(r) for r in conn.execute(text(MODULE_SQL), params).mappings()]


def snapshot(selected_date):
    try:
        day = date.fromisoformat(selected_date)
    except (ValueError, TypeError):
        raise ValueError('Seleccione una fecha operacional válida.') from None
    with _connection() as conn:
        rows = [dict(r) for r in conn.execute(text(DAILY_SQL), {'fecha': day}).mappings()]
    return validate_snapshot(rows, day.isoformat())


def validate_snapshot(rows, day):
    """Validar contrato sin deduplicar, rellenar ni clasificar datos SQL."""
    expected = {(1,n) for n in range(1,33)} | {(2,n) for n in range(1,29)}
    keys, numbers = set(), set()
    for row in rows:
        if any(field not in row for field in FIELDS):
            raise ValueError('Contrato operacional incompleto. Revisar función SQL.')
        key = (row['pad_id'], row['parcela_id'])
        number = (row['pad_id'], row['numero_parcela'])
        if None in key or key in keys or number in numbers:
            raise ValueError('Duplicados o identidades inválidas por PAD/parcela/fecha. Mapa detenido.')
        if str(row['fecha'])[:10] != day:
            raise ValueError('La fotografía contiene una fecha diferente de la seleccionada.')
        keys.add(key)
        numbers.add(number)
    if len(rows) != 60 or numbers != expected:
        raise ValueError('La función debe devolver 60 parcelas: 32 Óxidos y 28 Sulfuros. No se fabrican filas faltantes.')
    return sorted(rows, key=lambda r: (r['pad_id'], r['numero_parcela']))
