"""Validación SQL DEV: reglas sintéticas, casos reales y persistencia con ROLLBACK.

No deja declaraciones vigentes de prueba. IDENTITY puede consumir números.
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from .inspect_dev import engine_dev, definiciones
from .operational_sql import BASE, ACTUAL, RESUELTO, TABLA, SP, resolver_select, preview_sql
from .db import EQUIPOS

ROOT = Path(__file__).parent
KEY = ('fecha_operacional', 'turno', 'equipo_codigo')
RESULT = ('fuente_resuelta', 'valor_bruto_resuelto', 'valor_final_resuelto', 'motivo_decision')


def guardar(conn, fecha, turno, estado):
    return conn.execute(text(f'EXEC {SP} :fecha, :turno, :estado, :comentario, :usuario'),
                        dict(fecha=fecha, turno=turno, estado=estado,
                             comentario='Validación transaccional; se revierte.', usuario='VALIDACION_DEV_ROLLBACK')).mappings().one()


def filas(conn, origen, fecha, turno):
    return conn.execute(text(f'SELECT * FROM {origen} WHERE fecha_operacional=:f AND turno=:t'),
                        {'f': fecha, 't': turno}).mappings().all()


def probar_matriz(conn):
    conn.exec_driver_sql(f'SELECT TOP (0) * INTO #base FROM {BASE}')
    conn.exec_driver_sql('''CREATE TABLE #declaracion (id_declaracion bigint, fecha_operacional date,
        turno char(1), estado_operacional varchar(20), comentario nvarchar(1000),
        usuario nvarchar(255), fecha_registro datetime2(3))''')
    casos = []
    contador = 0
    for estado in (None, 'OPERATIVO', 'MANTENCION', 'CAIDA_PI'):
        for equipo in EQUIPOS:
            for pi in (None, 0, 150):
                for tum in (None, -1, 0, 100, 101):
                    for disponible in (0, 1):
                        fecha = date(2030, 1, 1) + timedelta(days=contador)
                        tipo = ('TUM_DIRECTO', 'TUM_MIXTO', 'TUM_CALCULADO')[contador % 3]
                        casos.append(dict(fecha=fecha, equipo=equipo, pi=pi, tum=tum, disponible=disponible, estado=estado, tipo=tipo))
                        contador += 1
    insertar_lotes(conn, '''INSERT INTO #base (fecha_operacional,turno,equipo_codigo,
        valor_pi_bruto,valor_pi_final,valor_turno_tum,tum_disponible,tipo_tum,
        estado_tecnico_pi,estado_fronteras,fuente_resuelta,valor_bruto_resuelto,valor_final_resuelto,motivo_decision)
        VALUES ''', '''(:fecha,'A',:equipo,:pi,:pi,:tum,:disponible,:tipo,
        'SIN_CAMBIO_TURNO_COMPLETO','FRONTERAS_COMPLETAS','TUM',777,777,'LEGACY_INTACTO')''', casos)
    insertar_lotes(conn, 'INSERT INTO #declaracion (id_declaracion,fecha_operacional,turno,estado_operacional) VALUES ',
                   "(1,:fecha,'A',:estado)", [c for c in casos if c['estado']])
    resultados = {r['fecha_operacional']: r for r in conn.execute(text(resolver_select('#base', '#declaracion'))).mappings()}
    for c in casos:
        r = resultados[c['fecha']]
        if c['estado'] is None:
            esperado = ('TUM', 777, 'RESUELTO', 'AUTOMATICO_LEGACY', 'LEGACY_INTACTO')
        elif c['estado'] in ('OPERATIVO', 'MANTENCION'):
            hay_pi = c['pi'] is not None
            esperado = ('PI' if hay_pi else None, c['pi'], 'RESUELTO' if hay_pi else 'PENDIENTE_PI',
                        'DECLARACION_ESPECIALISTA', 'DECLARACION_' + c['estado'] + ('_USA_PI' if hay_pi else '_PI_NO_DISPONIBLE'))
        else:
            valido = c['disponible'] == 1 and c['tum'] is not None and c['tum'] >= 0
            final = c['tum'] if valido else None
            if valido and c['equipo'].startswith('PRINCIPAL_') and final <= 100:
                final = 0
            esperado = ('TUM' if valido else None, final, 'RESUELTO' if valido else 'PENDIENTE_TUM',
                        'DECLARACION_ESPECIALISTA', 'DECLARACION_CAIDA_PI_USA_' + c['tipo'] if valido else 'DECLARACION_CAIDA_PI_PENDIENTE_TUM')
        actual = tuple(r[k] for k in ('fuente_resuelta','valor_final_resuelto','estado_resolucion','modo_resolucion','motivo_decision'))
        assert actual == esperado, (c, actual, esperado)
        bruto = 777 if c['estado'] is None else (c['pi'] if c['estado'] in ('OPERATIVO','MANTENCION') else (c['tum'] if esperado[0] == 'TUM' else None))
        assert r['valor_bruto_resuelto'] == bruto
        assert r['estado_tecnico_pi'] == 'SIN_CAMBIO_TURNO_COMPLETO'
    # Desempate temporal: id mayor gana con igual fecha_registro.
    conn.exec_driver_sql(f'''SELECT TOP (0) * INTO #versiones FROM {TABLA};
        SET IDENTITY_INSERT #versiones ON;
        INSERT INTO #versiones (id,fecha_operacional,turno,estado_operacional,usuario,fecha_registro)
        VALUES (1,'20300101','A','OPERATIVO','test','20300101'),(2,'20300101','A','CAIDA_PI','test','20300101');
        SET IDENTITY_INSERT #versiones OFF;''')
    # Ejecuta el cuerpo exacto de la vista vigente, sustituyendo solo la tabla temporal.
    definition = conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'), {'n': ACTUAL}).scalar()
    body = definition.split('AS\n', 1)[1].replace(TABLA, '#versiones')
    assert conn.exec_driver_sql(body).mappings().one()['id_declaracion'] == 2
    return len(casos)


def insertar_lotes(conn, prefix, fila, registros):
    """Parámetros enlazados, en lotes pequeños para evitar 1470 viajes ODBC."""
    import re
    for inicio in range(0, len(registros), 80):
        values, params = [], {}
        for i, registro in enumerate(registros[inicio:inicio+80]):
            values.append(re.sub(r':(\w+)', lambda m: ':' + m[1] + str(i), fila))
            params.update({k + str(i):v for k,v in registro.items()})
        conn.execute(text(prefix + ','.join(values)), params)


def main():
    reporte = {'matriz_sql': 0, 'casos_reales': [], 'bloqueos': []}
    before = json.loads((ROOT / 'validacion/objetos_protegidos_antes.json').read_text(encoding='utf-8'))
    with engine_dev().connect() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar() == 'inventar_SpcHidr'
        conn.commit()
        trans = conn.begin()
        try:
            reporte['matriz_sql'] = probar_matriz(conn)
        finally:
            trans.rollback()
        print('Matriz SQL correcta:', reporte['matriz_sql'], flush=True)
        reporte['rechazos_sp'] = probar_rechazos(conn)
        trans = conn.begin()
        try:
            cantidad_antes = conn.execute(text(f'SELECT COUNT_BIG(*) FROM {TABLA}')).scalar()
            casos = [('2026-09-07','A','CAIDA_PI'), ('2026-09-07','B','CAIDA_PI'),
                     ('2026-09-01','B','MANTENCION'), ('2026-09-04','A','OPERATIVO')]
            for fecha, turno, estado in casos:
                assert not filas(conn, ACTUAL, fecha, turno), 'Ya hay declaración real: no sustituir durante validación.'
                legacy = filas(conn, BASE, fecha, turno)
                auto = filas(conn, RESUELTO, fecha, turno)
                assert {tuple(r[k] for k in KEY): tuple(r[k] for k in RESULT) for r in legacy} == {
                    tuple(r[k] for k in KEY): tuple(r[k] for k in RESULT) for r in auto}
                assert all(r['modo_resolucion'] == 'AUTOMATICO_LEGACY' for r in auto)
                assert len(legacy) == 7, (fecha, turno, len(legacy))
                preview = conn.execute(text(preview_sql()), {'fecha':fecha,'turno':turno,'estado':estado}).mappings().all()
                first = guardar(conn, fecha, turno, 'OPERATIVO')
                second = guardar(conn, fecha, turno, estado)
                actual = filas(conn, ACTUAL, fecha, turno)
                assert len(actual) == 1 and actual[0]['id_declaracion'] == second['id']
                assert second['id'] > first['id']
                history = filas(conn, TABLA, fecha, turno)
                assert len(history) == 2 and history[0]['usuario'] == 'VALIDACION_DEV_ROLLBACK'
                resolved = filas(conn, RESUELTO, fecha, turno)
                assert {r['equipo_codigo']:tuple(r[k] for k in RESULT) for r in preview} == {
                    r['equipo_codigo']:tuple(r[k] for k in RESULT) for r in resolved}
                assert all(r['modo_resolucion'] == 'DECLARACION_ESPECIALISTA' for r in resolved)
                esperado = {('2026-09-07','A'): {'PRINCIPAL_CV008':6126,'PRINCIPAL_CV108':2926},
                            ('2026-09-07','B'): {'PRINCIPAL_CV008':16340,'RIPIOS_CV025':31387},
                            ('2026-09-01','B'): {'PRINCIPAL_CV008':0},
                            ('2026-09-04','A'): {'PRINCIPAL_CV008':19994}}[(fecha,turno)]
                for r in resolved:
                    if r['equipo_codigo'] in esperado and r['valor_final_resuelto'] != esperado[r['equipo_codigo']]:
                        reporte['bloqueos'].append(f"Valor runtime distinto del ejemplo: {fecha} {turno} {r['equipo_codigo']} = {r['valor_final_resuelto']}, esperado {esperado[r['equipo_codigo']]}")
                reporte['casos_reales'].extend([{k:r[k] for k in KEY + ('estado_operacional','valor_pi_final','valor_turno_tum','fuente_automatica','fuente_resuelta','valor_final_resuelto','estado_resolucion','motivo_decision')} for r in resolved])
                print('Caso validado:', fecha, turno, estado, flush=True)
            assert conn.execute(text(f'SELECT COUNT_BIG(*) FROM {TABLA}')).scalar() == cantidad_antes + 8
        finally:
            trans.rollback()
        assert conn.execute(text(f'SELECT COUNT_BIG(*) FROM {TABLA}')).scalar() == cantidad_antes
        assert definiciones(conn) == before, 'Cambio de objetos protegidos detectado'
        reporte['rollback_confirmado'] = True
        reporte['objetos_protegidos_sin_cambios'] = True
    (ROOT / 'validacion/resultados_operacional.json').write_text(json.dumps(reporte, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Validación completada; declaraciones revertidas. Bloqueos:', reporte['bloqueos'])


def probar_rechazos(conn):
    rechazados = 0
    for cambio in ({'fecha':None}, {'turno':'C'}, {'estado':'PI'}, {'usuario':''}, {'usuario':None}, {'comentario':'x'*1001}):
        params = dict(fecha='2030-01-01', turno='A', estado='OPERATIVO', comentario=None, usuario='VALIDACION_DEV_ROLLBACK')
        params.update(cambio)
        trans = conn.begin()
        try:
            try:
                conn.execute(text(f'EXEC {SP} :fecha, :turno, :estado, :comentario, :usuario'), params)
            except DBAPIError as exc:
                assert any(str(n) in str(exc.orig) for n in range(50011, 50016)), str(exc.orig)
                rechazados += 1
            else:
                raise AssertionError('SP aceptó datos inválidos: ' + str(cambio))
        finally:
            trans.rollback()
    return rechazados


if __name__ == '__main__':
    import sys
    if '--estado-consultas' in sys.argv:
        with engine_dev().connect() as conn:
            print(conn.execute(text('''SELECT session_id,status,command,wait_type,wait_time,
                blocking_session_id,total_elapsed_time,cpu_time
                FROM sys.dm_exec_requests WHERE database_id=DB_ID()''')).mappings().all())
    elif '--solo-diagnostico' in sys.argv:
        import pandas as pd
        from unittest.mock import patch
        from . import db, panel
        result = []
        for correa in ('CV008', 'CV001', 'CV025'):
            frame = db.obtener_tendencia_totalizador('2026-09-13', '2026-09-13', correa)
            assert not frame.empty
            with patch.object(db, 'obtener_tendencia_totalizador', return_value=frame):
                grafico = panel.actualizar_tendencia(1, '2026-09-13', '2026-09-13', correa)[0]
            assert grafico.data[0].type == 'scattergl'
            pd.testing.assert_series_equal(pd.Series(grafico.data[0].y), frame.sort_values('timestamp',kind='stable').valor.reset_index(drop=True), check_names=False)
            result.append({'correa':correa,'filas':len(frame), 'metadata':frame[['fuente','resolucion_segundos','tipo_senal']].drop_duplicates().to_dict('records')})
        (ROOT / 'validacion/diagnostico_fase2.json').write_text(json.dumps(result, default=str, indent=2), encoding='utf-8')
        print(result)
    elif '--solo-rechazos' in sys.argv:
        with engine_dev().connect() as conn:
            result = {'rechazos_sp': probar_rechazos(conn)}
            (ROOT / 'validacion/rechazos_sp.json').write_text(json.dumps(result), encoding='utf-8')
            print(result)
    else:
        main()
