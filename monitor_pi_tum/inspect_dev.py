"""Inspección de solo lectura de objetos activos DEV para esta fase."""
import json
from pathlib import Path
from sqlalchemy import text
from .db import get_engine
import os

PROTEGIDOS = (
    'v_contingencia_totalizador_resuelto_turno', 'sp_calcular_balance_flujos',
    'sp_calcular_balance_flujos_contingencia_test', 'sp_reporte_turno_emision_test',
    'sp_actualizar_reporte_turno_cache_emision_test', 'v_datos_apilado_tmh_v2',
    'sp_monitor_totalizador_tendencia_test',
)
NUEVOS = ('contingencia_estado_operacional_test',
          'sp_guardar_contingencia_estado_operacional_test',
          'v_contingencia_estado_operacional_actual_test',
          'v_contingencia_totalizador_resuelto_operacional_test')


def engine_dev():
    if os.getenv('SQLSERVER_DB') != 'inventar_SpcHidr':
        raise RuntimeError('Solo DEV')
    engine = get_engine()
    if engine.url.database != 'inventar_SpcHidr':
        raise RuntimeError('Solo DEV')
    return engine


def definiciones(conn):
    return {name: conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:nombre))'),
                              {'nombre': 'inventar_SpcHidr.' + name}).scalar()
            for name in PROTEGIDOS}


if __name__ == '__main__':
    with engine_dev().connect() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar() == 'inventar_SpcHidr'
        defs = definiciones(conn)
        destino = Path(__file__).parent / 'validacion'
        destino.mkdir(exist_ok=True)
        before = destino / 'objetos_protegidos_antes.json'
        if not before.exists():
            before.write_text(json.dumps(defs, ensure_ascii=False, indent=2), encoding='utf-8')
        for name in NUEVOS:
            print(name, conn.execute(text('SELECT OBJECT_ID(:n)'), {'n': 'inventar_SpcHidr.' + name}).scalar())
        print('Columnas resolvedor:', conn.execute(text('SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(:n) ORDER BY column_id'), {'n': 'inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno'}).scalars().all())
        print('CV025 en SP tendencia:', 'CV025' in (defs['sp_monitor_totalizador_tendencia_test'] or ''))
        print('Definiciones guardadas:', before)
