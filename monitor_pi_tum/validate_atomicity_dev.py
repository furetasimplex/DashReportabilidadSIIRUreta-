"""Validación empírica de rollback PI/TUM. Ejecutar explícitamente en DEV."""
import os
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text

from . import db


DEV_HOST = '149.50.136.234'  # Identidad DEV usada por los validadores del repositorio.
APILADO = 'inventar_SpcHidr.Control_Apilado_TMH_v2_test'
COLUMNAS = ('TMH_CV008_A', 'TMH_CV108_A', 'TMH_Apilado_Total_A',
            'TMH_CV008_B', 'TMH_CV108_B', 'TMH_Apilado_Total_B',
            'TMH_Apilado_Total_Dia', 'Fecha_Calculo')


def apilado(conn, fecha):
    cols = ', '.join(COLUMNAS)
    return [tuple(row) for row in conn.execute(text(
        f'SELECT {cols} FROM {APILADO} WHERE Fecha=:fecha'), {'fecha': fecha})]


def eventos(conn, usuario, comentario):
    return conn.execute(text(f'''SELECT COUNT(*) FROM {db.BITACORA}
        WHERE usuario=:usuario AND (comentario=:comentario OR accion='CERRAR_CONTINGENCIA')'''),
        {'usuario': usuario, 'comentario': comentario}).scalar_one()


def elegir_fecha(conn):
    limite = db._ultima_fecha_materializable(conn)
    if limite is None:
        raise RuntimeError('No hay fecha materializable en DEV.')
    print(f'Última fecha materializable: {limite}')
    # Inspección de bitácora antes de escribir; la función de solapamiento usa la misma bitácora.
    print('Eventos existentes desde el corte:', conn.execute(text(
        f'SELECT COUNT(*) FROM {db.BITACORA} WHERE fecha_operacional>=:corte'),
        {'corte': db.CORTE}).scalar_one())
    for offset in range(min(31, (limite - db.CORTE).days + 1)):
        fecha = limite - timedelta(days=offset)
        if db._estado(conn, fecha, 'A')['contingencia_pi_activa']:
            continue
        if len(apilado(conn, fecha)) != 1:
            continue
        if conn.execute(text(f'''SELECT COUNT(*) FROM {db.BITACORA}
            WHERE fecha_operacional BETWEEN :inicio AND :cierre'''),
            {'inicio': fecha, 'cierre': fecha + timedelta(days=1)}).scalar_one():
            continue
        try:
            db._validar_solapamiento(conn, fecha, 'A', fecha, 'B')
        except ValueError:
            continue
        return fecha
    raise RuntimeError('No se encontró un período reciente sin contingencias incompatibles.')


def caso(engine, fecha, rango):
    token = uuid4().hex
    usuario = f'PRUEBA_ATOMICIDAD_{token}'
    comentario = f'PRUEBA_ROLLBACK_ATOMICIDAD_{token}'
    with engine.connect() as conn:
        antes = apilado(conn, fecha)
    if len(antes) != 1:
        raise RuntimeError(f'Se esperaba una fila de apilado para {fecha}; encontradas: {len(antes)}.')
    llamadas = []

    def fallo(*args):
        llamadas.append(args)
        raise RuntimeError('FALLO_CONTROLADO_REPROCESO')

    try:
        with patch.object(db, 'reprocesar_apilado', side_effect=fallo):
            if rango:
                db.registrar_contingencia_rango(fecha.isoformat(), 'A', fecha.isoformat(), 'B',
                                               'CAIDA_PI', comentario, usuario)
            else:
                db.registrar_contingencia(fecha.isoformat(), 'A', 'ACTIVAR_CONTINGENCIA',
                                         'CAIDA_PI', comentario, usuario)
    except RuntimeError as exc:
        if str(exc) != 'FALLO_CONTROLADO_REPROCESO' or len(llamadas) != 1:
            raise
    else:
        raise AssertionError('No se produjo el fallo controlado.')

    # Nueva conexión después de que engine.begin() haya salido por excepción.
    with engine.connect() as conn:
        filas = eventos(conn, usuario, comentario)
        despues = apilado(conn, fecha)
    igual = antes == despues
    nombre = 'rango' if rango else 'puntual'
    print(f'Prueba {nombre}: excepción inducida OK; filas persistidas {filas}; fila de apilado 1; '
          f'apilado modificado {"NO" if igual else "SÍ"}; resultado {"PASS" if filas == 0 and igual else "FAIL"}')
    if filas or not igual:
        raise AssertionError(f'Fallo crítico de atomicidad en {nombre}.')


def main():
    if os.getenv('SQLSERVER_HOST') != DEV_HOST or os.getenv('SQLSERVER_DB') != 'inventar_SpcHidr':
        raise RuntimeError('Configuración no coincide con host y base DEV documentados.')
    engine = db._engine_dev()
    with engine.connect() as conn:
        identidad = conn.execute(text('SELECT DB_NAME() AS db, @@SERVERNAME AS servidor, '
                                      "CONVERT(varchar(128), SERVERPROPERTY('MachineName')) AS maquina")).mappings().one()
        print(f"Conexión efectiva: base={identidad['db']}; servidor={identidad['servidor']}; máquina={identidad['maquina']}")
        if identidad['db'] != 'inventar_SpcHidr':
            raise RuntimeError('Base efectiva distinta de DEV.')
        fecha = elegir_fecha(conn)
        print(f'Período seleccionado: {fecha} A-B')
    caso(engine, fecha, False)
    caso(engine, fecha, True)
    print('Atomicidad: VALIDADA')


if __name__ == '__main__':
    main()
