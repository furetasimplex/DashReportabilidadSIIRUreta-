"""Estado operacional diario: una lectura parametrizada, sin derivar estados."""
from datetime import date
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
