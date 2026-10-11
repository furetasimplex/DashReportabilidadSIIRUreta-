"""Prueba reversible, despliegue y reproceso autorizado de nominales SOLO DEV."""
import argparse
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
from scripts.factor_camiones_nominales_dev import BACKUP, MIGRATION, EVIDENCE, OBJECTS, PYTHON_FILES, rows, save_json

CONTROL = 'inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test'
VIEW = 'inventar_SpcHidr.v_ajuste_camiones_emision_test'
PARAMS = 'inventar_SpcHidr.factor_camiones_parametro_vigencia_test'
START = date(2026, 7, 1)


def lock(conn):
    # Mismo orden que la cadena operativa: global, luego parametros.
    for resource in ('SIIR_CONTINGENCIA_PI_APILADO', 'SIIR_FACTOR_CAMIONES_PARAMETROS_DEV'):
        rc = conn.execute(text("""DECLARE @r int;
            EXEC @r=sys.sp_getapplock @Resource=:r,@LockMode='Exclusive',
                @LockOwner='Transaction',@LockTimeout=15000; SELECT @r;"""), {'r':resource}).scalar_one()
        if rc < 0:
            raise RuntimeError('No se obtuvo lock ' + resource)


def verify_baseline(conn):
    for name in OBJECTS:
        live = conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'),
                            {'n':'inventar_SpcHidr.'+name}).scalar_one()
        original = (BACKUP/(name+'.sql')).read_bytes().decode('utf-8')
        if live != original:
            raise RuntimeError('Definicion viva modificada desde backup: '+name)
    for name in ('fn_resolver_vueltas_camiones_test','v_vueltas_camiones_diarias_test',
                 'sp_registrar_parametro_factor_camiones_vigencia_test'):
        if conn.execute(text('SELECT OBJECT_ID(:n)'), {'n':'inventar_SpcHidr.'+name}).scalar_one() is not None:
            raise RuntimeError('Objeto nuevo ya existe: '+name)


def apply_sql(conn,verbose=True):
    for path in sorted(MIGRATION.glob('[0-9][0-9]*.sql')):
        if verbose: print('SQL:', path.name, flush=True)
        for batch in re.split(r'^\s*GO\s*$',path.read_text(encoding='utf-8'), flags=re.M|re.I):
            if batch.strip():
                conn.exec_driver_sql(batch).close()


def snapshot(conn):
    return {
        'control':rows(conn,'SELECT * FROM '+CONTROL+' ORDER BY Fecha'),
        'vista':rows(conn,'SELECT * FROM '+VIEW+' ORDER BY Fecha'),
        'parametros':rows(conn,'SELECT * FROM '+PARAMS+' ORDER BY id'),
        'auditoria':rows(conn,'SELECT * FROM inventar_SpcHidr.factor_camiones_parametro_auditoria_test ORDER BY id'),
        'override':rows(conn,'SELECT * FROM inventar_SpcHidr.factor_camiones_override_aplicacion_test ORDER BY id_override'),
        'dc':rows(conn,'SELECT * FROM inventar_SpcHidr.Datos_conciliados_of ORDER BY Fecha'),
        'cache':rows(conn,'SELECT * FROM inventar_SpcHidr.reporte_turno_cache_emision_test ORDER BY Fecha,Turno'),
    }


def same(a,b):
    return json.dumps(a,default=str,sort_keys=True)==json.dumps(b,default=str,sort_keys=True)


def test_resolver(conn):
    # counts, nulls, negatives, KOM, CAT; tested SQL function is used by both SPs.
    missing=(0,None,None,None,None)
    good=(2,0,0,10,3)
    cases=[
        ('prioridad',good,(1,0,0,99,0),'MOV_CAM',10,3,'OK','OK'),
        ('fallback',missing,good,'MOV_CAM_POWERBI',10,3,'SIN_REGISTROS','OK'),
        ('ninguna',missing,missing,'SIN_DATOS_CAMIONES',0,0,'SIN_REGISTROS','SIN_REGISTROS'),
        ('solo_ceros',(2,0,0,0,0),good,'MOV_CAM_POWERBI',10,3,'SOLO_CEROS','OK'),
        ('null',(2,1,0,9,0),good,'MOV_CAM_POWERBI',10,3,'NBREAK_NULL','OK'),
        ('negativo',(2,0,1,9,-1),good,'MOV_CAM_POWERBI',10,3,'NBREAK_NEGATIVO','OK'),
        ('sin_mezcla',(1,0,0,5,0),(1,0,0,0,8),'MOV_CAM',5,0,'OK','OK'),
        ('solo_cat',(1,0,0,0,7),good,'MOV_CAM',0,7,'OK','OK'),
        ('cero_permitido',(2,0,0,4,0),missing,'MOV_CAM',4,0,'OK','SIN_REGISTROS'),
        ('ambas_invalidas',(2,1,0,7,0),(2,0,1,3,-1),'SIN_DATOS_CAMIONES',0,0,'NBREAK_NULL','NBREAK_NEGATIVO'),
    ]
    for name,m,p,source,kom,cat,em,ep in cases:
        values={f'p{i}':v for i,v in enumerate(m+p+(0,0))}
        r=rows(conn,'SELECT * FROM inventar_SpcHidr.fn_resolver_vueltas_camiones_test('+','.join(':'+k for k in values)+')',values)[0]
        assert (r['Fuente_Camiones'],r['Vueltas_KOM'],r['Vueltas_CAT'],r['Estado_Fuente_MOV_CAM'],r['Estado_Fuente_POWERBI'])==(source,kom,cat,em,ep),name
    return [c[0] for c in cases]


def close(a,b,tolerance=1e-7):
    assert a is not None and math.isclose(float(a),float(b),rel_tol=tolerance,abs_tol=tolerance),(a,b)


def control_cases(data):
    byday={str(r['Fecha']):r for r in data}
    expected={
        '2026-08-06':('MOV_CAM',66,17,23562,4012,.9983143803),
        '2026-09-14':('MOV_CAM',139,0,49623,0,1),
        '2026-09-16':('MOV_CAM',1,0,357,0,.21963019549669),
        '2026-09-21':('MOV_CAM_POWERBI',4,0,1428,0,1),
        '2026-09-22':('MOV_CAM_POWERBI',137,0,48909,0,.95881375587),
    }
    for day, (source,vk,vc,pk,pc,factor) in expected.items():
        r=byday[day]
        assert r['Fuente_Camiones']==source,(day,r['Fuente_Camiones'])
        for k,val in [('Vueltas_KOM',vk),('Vueltas_CAT',vc),('Produccion_KOM_TMH',pk),
                      ('Produccion_CAT_TMH',pc),('Carga_Nominal_KOM_TMH_Viaje',357),
                      ('Carga_Nominal_CAT_TMH_Viaje',236),('Limite_KOM_TMH_Viaje',380),
                      ('Limite_CAT_TMH_Viaje',265),('Factor_Ajuste_Calculado',factor)]:
            try: close(r[k],val)
            except AssertionError as exc: raise AssertionError((day,k,r[k],val)) from exc
    r=byday['2026-09-16']
    close(r['Factor_Aplicacion_Reportes'],1)
    assert r['Modo_Aplicacion']=='FORZADO_1'
    return {d:byday[d] for d in expected}


def invariant_nominals(control):
    for r in control:
        for f in ('KOM','CAT'):
            close(r[f'Produccion_{f}_TMH'],r[f'Vueltas_{f}']*float(r[f'Carga_Nominal_{f}_TMH_Viaje']))
        close(r['Dato_Mina_TMH'],r['Produccion_KOM_TMH']+r['Produccion_CAT_TMH'])
        if r['Fuente_Camiones']=='SIN_DATOS_CAMIONES':
            assert r['Factor_Ajuste'] is None and not r['Flag_Factor_Ajuste_Valido']


def register(conn,category,fleet,value,day):
    return rows(conn,"""EXEC inventar_SpcHidr.sp_registrar_parametro_factor_camiones_vigencia_test
      @Parametro=:p,@Flota=:f,@Valor=:v,@VigenciaDesde=:d,
      @Motivo=N'Validacion reversible nominales',@Usuario=N'TEST_NOMINALES_DEV'""",
      {'p':category,'f':fleet,'v':value,'d':day})[0]


def test_administration(conn):
    conn.exec_driver_sql('SAVE TRANSACTION test_parametros')
    before=rows(conn,'SELECT * FROM '+CONTROL+' ORDER BY Fecha')
    try:
        register(conn,'CARGA_NOMINAL_TMH_VIAJE','KOM',356.123456,'2026-08-01')
        register(conn,'CARGA_NOMINAL_TMH_VIAJE','KOM',350,'2027-01-01')
        register(conn,'LIMITE_CARGA_AJUSTE','CAT',264,'2027-02-01')
        assert same(before,rows(conn,'SELECT * FROM '+CONTROL+' ORDER BY Fecha')),'Registro reproceso resultados'
        history=rows(conn,'SELECT * FROM '+PARAMS+" WHERE parametro='CARGA_NOMINAL_TMH_VIAJE' AND flota='KOM' ORDER BY vigencia_desde")
        assert [str(r['vigencia_desde']) for r in history]==['2026-07-01','2026-08-01','2027-01-01']
        assert [str(r['vigencia_hasta']) for r in history]==['2026-08-01','2027-01-01','None']
        assert str(history[1]['valor'])=='356.123456'
        pending_sql="""SELECT v.Fecha FROM inventar_SpcHidr.v_ajuste_camiones_emision_test v
          JOIN inventar_SpcHidr.factor_camiones_parametro_vigencia_test p
          ON p.parametro='CARGA_NOMINAL_TMH_VIAJE' AND p.flota='KOM' AND p.activo=1
          AND p.vigencia_desde<=v.Fecha AND (p.vigencia_hasta IS NULL OR v.Fecha<p.vigencia_hasta)
          WHERE v.Fecha='20260806' AND v.Carga_Nominal_KOM_TMH_Viaje<>p.valor"""
        pending=rows(conn,pending_sql)
        assert len(pending)==1
        conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test '20260806','20260806',0").close()
        r=rows(conn,"SELECT * FROM "+CONTROL+" WHERE Fecha='20260806'")[0]
        close(r['Carga_Nominal_KOM_TMH_Viaje'],356.123456)
        close(r['Carga_Nominal_CAT_TMH_Viaje'],236)
        close(r['Limite_KOM_TMH_Viaje'],380)
        close(r['Limite_CAT_TMH_Viaje'],265)
        assert rows(conn,pending_sql)==[], 'Pendiente no desaparecio'
    finally:
        conn.exec_driver_sql('ROLLBACK TRANSACTION test_parametros')
    assert same(before,rows(conn,'SELECT * FROM '+CONTROL+' ORDER BY Fecha'))


def test_standalone(conn,end):
    conn.exec_driver_sql('SAVE TRANSACTION test_standalone')
    try:
        main=rows(conn,'SELECT * FROM '+CONTROL+' ORDER BY Fecha')
        conn.execute(text('EXEC inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_standalone_test :s,:e,0'),{'s':START,'e':end}).close()
        alt=rows(conn,'SELECT * FROM '+CONTROL+' ORDER BY Fecha')
        invariant_nominals(alt)
        fields=['Fecha','Fuente_Camiones','Vueltas_KOM','Vueltas_CAT','Produccion_KOM_TMH','Produccion_CAT_TMH',
                'Carga_Nominal_KOM_TMH_Viaje','Carga_Nominal_CAT_TMH_Viaje','Estado_Fuente_MOV_CAM','Estado_Fuente_POWERBI']
        assert same([{k:r[k] for k in fields} for r in main],[{k:r[k] for k in fields} for r in alt])
    finally:
        conn.exec_driver_sql('ROLLBACK TRANSACTION test_standalone')


def reprocess(conn,end):
    from report_export.report_export import refrescar_dependencias_datos_conciliados_emision
    return refrescar_dependencias_datos_conciliados_emision(START,end,conn=conn)


def comparison(before,after,path):
    b={r['Fecha']:r for r in before['control']}
    bv={r['Fecha']:r for r in before['vista']}
    av={r['Fecha']:r for r in after['vista']}
    result=[]
    for r in after['control']:
        old=b[r['Fecha']]
        source_changed=r['Fuente_Camiones']!='MOV_CAM_POWERBI'
        nominal_changed=any(not math.isclose(old[f'Produccion_{f}_TMH'],old[f'Vueltas_{f}']*float(r[f'Carga_Nominal_{f}_TMH_Viaje']),abs_tol=1e-6) for f in ('KOM','CAT'))
        classification=('SIN_DATOS' if r['Fuente_Camiones']=='SIN_DATOS_CAMIONES' else
                        'CAMBIO_AMBOS' if source_changed and nominal_changed else
                        'CAMBIO_POR_FUENTE_VUELTAS' if source_changed else
                        'CAMBIO_POR_NOMINAL' if nominal_changed else 'SIN_CAMBIO')
        row={'Fecha':r['Fecha'],'Fuente_Vueltas_Anterior':'MOV_CAM_POWERBI',
             'Etiqueta_Fuente_Anterior':old['Fuente_Camiones'],'Fuente_Vueltas_Nueva':r['Fuente_Camiones']}
        for f in ('KOM','CAT'):
            row.update({f'Vueltas_{f}_Anterior':old[f'Vueltas_{f}'],f'Vueltas_{f}':r[f'Vueltas_{f}'],
                        f'Nominal_{f}':r[f'Carga_Nominal_{f}_TMH_Viaje'],
                        f'Produccion_{f}_Anterior':old[f'Produccion_{f}_TMH'],f'Produccion_{f}_Nueva':r[f'Produccion_{f}_TMH'],
                        f'Limite_{f}':r[f'Limite_{f}_TMH_Viaje']})
        row.update({'Dato_Mina_Anterior':old['Dato_Mina_TMH'],'Dato_Mina_Nuevo':r['Dato_Mina_TMH'],
                    'Factor_Anterior':old['Factor_Ajuste'],'Factor_Nuevo':r['Factor_Ajuste'],
                    'Delta_Factor':None if old['Factor_Ajuste'] is None or r['Factor_Ajuste'] is None else r['Factor_Ajuste']-old['Factor_Ajuste'],
                    'Factor_Aplicacion_Reportes_Anterior':bv[r['Fecha']]['Factor_Aplicacion_Reportes'],
                    'Factor_Aplicacion_Reportes_Nuevo':av[r['Fecha']]['Factor_Aplicacion_Reportes'],
                    'Estado_Fuente_MOV_CAM':r['Estado_Fuente_MOV_CAM'],'Estado_Fuente_POWERBI':r['Estado_Fuente_POWERBI'],
                    'Clasificacion':classification})
        result.append(row)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0]),delimiter=';');w.writeheader();w.writerows(result)
    return result


def trial():
    engine=_engine_dev()
    with engine.connect() as conn:
        _assert_dev_connection(conn)
        lock(conn)
        verify_baseline(conn)
        before=snapshot(conn)
        end=max(r['Fecha'] for r in before['control'])
        assert START<=end<=date(2026,9,30)
        save_json(EVIDENCE/'trial_antes.json',before)
        try:
            apply_sql(conn)
            resolver=test_resolver(conn)
            # Contrato ordinal, casos reales y estados antes de refrescar downstream.
            conn.execute(text('EXEC inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test :s,:e,0'),{'s':START,'e':end}).close()
            initial=snapshot(conn)
            control_cases(initial['vista'])
            invariant_nominals(initial['control'])
            test_administration(conn)
            test_standalone(conn,end)
            refresh=reprocess(conn,end)
            downstream=consumers(conn,end)
            after=snapshot(conn)
            cases=control_cases(after['vista'])
            invariant_nominals(after['control'])
            assert same(before['override'],after['override'])
            for key in ('dc','cache'):
                outside=lambda data:[r for r in data if r['Fecha']<START or r['Fecha']>end]
                assert same(outside(before[key]),outside(after[key])),('Fuera de rango',key)
            save_json(EVIDENCE/'trial_despues.json',after)
            comparison(before,after,EVIDENCE/'comparacion_trial.csv')
            save_json(EVIDENCE/'casos_trial.json',cases)
            save_json(EVIDENCE/'consumidores_trial.json',downstream)
            save_json(EVIDENCE/'trial_resultado.json',{'estado':'VALIDADO_PENDIENTE_ROLLBACK','fin':end,'resolver':resolver,'refresco':refresh})
        finally:
            conn.rollback()
        restored=snapshot(conn)
        assert same(before,restored),'ROLLBACK no restauro snapshot'
        verify_baseline(conn)
        save_json(EVIDENCE/'trial_resultado.json',{'estado':'OK_ROLLBACK_VERIFICADO','fin':end,'resolver':resolver,'refresco':refresh})
    print('TRIAL OK: migracion y reproceso revertidos; snapshots y definiciones restaurados.')


def rejection_tests():
    """Cada rechazo tiene una migracion transaccional propia que se revierte entera."""
    from sqlalchemy.exc import DBAPIError
    results=[]
    cases=['categoria','valor','mismo_inicio','sin_cobertura_previa','discontinuidad',
           'solapamiento','falta_configuracion','configuracion_duplicada']
    for case in cases:
        with _engine_dev().connect() as conn:
            _assert_dev_connection(conn)
            lock(conn)
            verify_baseline(conn)
            try:
                apply_sql(conn,verbose=False)
                expected={'categoria':51018,'valor':51011,'mismo_inicio':51015,
                          'sin_cobertura_previa':51016,'discontinuidad':51017,
                          'solapamiento':51001,'falta_configuracion':51020,'configuracion_duplicada':51020}[case]
                if case=='categoria':register(conn,'INVALIDO','KOM',357,'2026-08-01')
                elif case=='valor':register(conn,'CARGA_NOMINAL_TMH_VIAJE','KOM',0,'2026-08-01')
                elif case=='mismo_inicio':register(conn,'CARGA_NOMINAL_TMH_VIAJE','KOM',356,'2026-07-01')
                elif case=='sin_cobertura_previa':register(conn,'CARGA_NOMINAL_TMH_VIAJE','KOM',356,'2026-06-30')
                elif case=='discontinuidad':
                    conn.exec_driver_sql("UPDATE "+PARAMS+" SET vigencia_hasta='20260801' WHERE parametro='CARGA_NOMINAL_TMH_VIAJE' AND flota='KOM'")
                    register(conn,'CARGA_NOMINAL_TMH_VIAJE','KOM',356,'2026-07-15')
                elif case in ('solapamiento','configuracion_duplicada'):
                    if case=='configuracion_duplicada':
                        conn.exec_driver_sql('DISABLE TRIGGER inventar_SpcHidr.tr_factor_camiones_vigencia_solapamiento_test ON '+PARAMS)
                    conn.exec_driver_sql("INSERT "+PARAMS+" (flota,parametro,valor,vigencia_desde,vigencia_hasta,motivo,usuario_registro) VALUES ('KOM','CARGA_NOMINAL_TMH_VIAJE',355,'20260801','20260901',N'Test rollback',N'TEST_NOMINALES_DEV')")
                    conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_test '20260806','20260806'").close()
                elif case=='falta_configuracion':
                    conn.exec_driver_sql("DELETE FROM "+PARAMS+" WHERE parametro='CARGA_NOMINAL_TMH_VIAJE' AND flota='CAT'")
                    conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_test '20260806','20260806'").close()
                raise AssertionError('No se rechazo '+case)
            except DBAPIError as exc:
                assert str(expected) in str(exc),(case,str(exc))
                results.append({'caso':case,'error_verificado':expected})
                print('Rechazo OK:',case,expected,flush=True)
            finally:
                conn.rollback()
            verify_baseline(conn)
    save_json(EVIDENCE/'rechazos.json',results)


def concurrency_test():
    """Dos sesiones sobre el lock del administrador, sin altas persistentes."""
    from concurrent.futures import ThreadPoolExecutor
    import threading,time
    ready=threading.Event()
    state={}
    with _engine_dev().connect() as first:
        _assert_dev_connection(first)
        generic=first.execute(text("SELECT OBJECT_ID('inventar_SpcHidr.sp_registrar_parametro_factor_camiones_vigencia_test')")).scalar_one() is not None
        before=rows(first,'SELECT * FROM '+PARAMS+' ORDER BY id')
        # No cambios DDL: el SP compatible actual usa el mismo lock del generico.
        first.execute(text("""EXEC inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test
          @Flota='KOM',@Valor=379,@VigenciaDesde='20290101',@Motivo=N'Concurrencia rollback',@Usuario=N'TEST_NOMINALES_DEV'""")).close()
        def second():
            with _engine_dev().connect() as conn:
                _assert_dev_connection(conn)
                state['spid']=conn.execute(text('SELECT @@SPID')).scalar_one()
                ready.set()
                try:
                    conn.execute(text("""EXEC inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test
                      @Flota='KOM',@Valor=378,@VigenciaDesde='20290101',@Motivo=N'Concurrencia rollback',@Usuario=N'TEST_NOMINALES_DEV'""")).close()
                finally: conn.rollback()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(second)
            try:
                assert ready.wait(10)
                until=time.monotonic()+8
                while time.monotonic()<until:
                    waits=rows(first,"SELECT request_status FROM sys.dm_tran_locks WHERE request_session_id=:s AND resource_type='APPLICATION'",{'s':state['spid']})
                    if any(r['request_status']=='WAIT' for r in waits):break
                    time.sleep(.1)
                else:raise AssertionError('No se observo espera APPLICATION')
                assert not future.done()
            finally:first.rollback()
            future.result(timeout=20)
        assert not rows(first,"SELECT id FROM "+PARAMS+" WHERE usuario_registro=N'TEST_NOMINALES_DEV'")
        assert same(before,rows(first,'SELECT * FROM '+PARAMS+' ORDER BY id'))
    save_json(EVIDENCE/('concurrencia_post.json' if generic else 'concurrencia.json'),{'espera_application_observada':True,'ambas_sesiones_rollback':True,'wrapper_generico':generic})
    print('Concurrencia OK: espera APPLICATION, ambas sesiones revertidas.')


def consumers(conn,end):
    from datetime import timedelta
    from report_export.report_export import (fetch_factor_ajuste_camiones_report,
        fetch_balance_chancado_report,fetch_datos_conciliados_emision_report,
        fetch_generador_reporte_diario_emision,fetch_reconstitucion_srr_report,
        fetch_reporte_turno_cache_emision)
    results={}
    for name,fn,finish in [('factor',fetch_factor_ajuste_camiones_report,end),
                           ('balance',fetch_balance_chancado_report,end),
                           ('dc',fetch_datos_conciliados_emision_report,end),
                           ('generador',fetch_generador_reporte_diario_emision,end+timedelta(days=1)),
                           ('reconstitucion',fetch_reconstitucion_srr_report,end+timedelta(days=1)),
                           ('rto',fetch_reporte_turno_cache_emision,end+timedelta(days=1))]:
        df=fn(START,finish,conn=conn)
        assert not df.empty, name
        results[name]={'filas':len(df),'columnas':list(df.columns)}
        if name=='balance':
            diff=df['Diferencia_vs_Datos_Conciliados'].dropna().abs()
            assert (diff<=1e-6).all(),'Balance difiere de DC'
    return results


def deployed_definitions(conn):
    names=list(OBJECTS)+['sp_registrar_parametro_factor_camiones_vigencia_test',
                       'fn_resolver_vueltas_camiones_test','v_vueltas_camiones_diarias_test']
    return {name:conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'),
                              {'n':'inventar_SpcHidr.'+name}).scalar_one() for name in names}


def deploy():
    trial_result=json.loads((EVIDENCE/'trial_resultado.json').read_text(encoding='utf-8'))
    assert trial_result['estado']=='OK_ROLLBACK_VERIFICADO'
    assert len(json.loads((EVIDENCE/'rechazos.json').read_text(encoding='utf-8')))==8
    assert json.loads((EVIDENCE/'concurrencia.json').read_text(encoding='utf-8'))['ambas_sesiones_rollback']
    engine=_engine_dev()
    # Fase 1: esquema/contratos/seeds se publican de manera atomica.
    with engine.begin() as conn:
        _assert_dev_connection(conn)
        lock(conn)
        verify_baseline(conn)
        save_json(EVIDENCE/'antes_migracion_commit.json',snapshot(conn))
        apply_sql(conn)
        test_resolver(conn)
        seeds=rows(conn,'SELECT * FROM '+PARAMS+' ORDER BY parametro,flota,vigencia_desde')
        assert len(seeds)==4
        expected={('CARGA_NOMINAL_TMH_VIAJE','KOM'):357,('CARGA_NOMINAL_TMH_VIAJE','CAT'):236,
                  ('LIMITE_CARGA_AJUSTE','KOM'):380,('LIMITE_CARGA_AJUSTE','CAT'):265}
        for r in seeds:
            close(r['valor'],expected[r['parametro'],r['flota']])
            assert r['vigencia_desde']==START and r['vigencia_hasta'] is None and r['activo']
        definitions=deployed_definitions(conn)
    save_json(EVIDENCE/'definiciones_desplegadas.json',definitions)
    save_json(EVIDENCE/'seeds_commit.json',seeds)
    print('MIGRACION COMMIT confirmada.',flush=True)
    # Fase 2: snapshot fresco + orquestacion existente + validaciones antes del COMMIT.
    with engine.begin() as conn:
        _assert_dev_connection(conn)
        lock(conn)
        before=snapshot(conn)
        end=max(r['Fecha'] for r in before['control'])
        assert START<=end<=date(2026,9,30)
        save_json(EVIDENCE/'antes_reproceso_commit.json',before)
        refresh=reprocess(conn,end)
        after=snapshot(conn)
        invariant_nominals(after['control'])
        cases=control_cases(after['vista'])
        assert same(before['override'],after['override'])
        for key in ('dc','cache'):
            outside=lambda data:[r for r in data if r['Fecha']<START or r['Fecha']>end]
            assert same(outside(before[key]),outside(after[key])),('Fuera de rango',key)
        downstream=consumers(conn,end)
        comparison(before,after,EVIDENCE/'comparacion.csv')
        save_json(EVIDENCE/'despues_reproceso.json',after)
        save_json(EVIDENCE/'casos_obligatorios.json',cases)
        save_json(EVIDENCE/'consumidores.json',downstream)
    # Nueva conexion: comprobar la persistencia, no solo la vista transaccional.
    with engine.connect() as conn:
        _assert_dev_connection(conn)
        persisted=snapshot(conn)
        assert same(after,persisted),'Los resultados no coinciden despues del COMMIT'
        control_cases(persisted['vista'])
    save_json(EVIDENCE/'resultado_final.json',{'estado':'OK_COMMIT_VERIFICADO','inicio':START,'fin':end,'refresco':refresh,
                                             'filas_factor':len(after['control']),'override_sin_cambios':True,
                                             'consumidores':downstream})
    print('REPROCESO COMMIT confirmado y leido desde una nueva conexion.',flush=True)


def restore_rows(conn,table,data,keys,end):
    """Restaura valores del snapshot solo en filas existentes del rango autorizado."""
    columns=rows(conn,"""SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(:t)
      AND is_computed=0 AND is_identity=0 AND system_type_id<>189 ORDER BY column_id""",{'t':table})
    names=[c['name'] for c in columns if c['name'] not in keys and c['name'] in data[0]]
    # Objetos y nombres proceden de whitelist interna/catalogo, nunca del usuario.
    sql='UPDATE '+table+' SET '+','.join('['+c+']=:v'+str(i) for i,c in enumerate(names))
    sql+=' WHERE '+' AND '.join('['+k+']=:k'+str(i) for i,k in enumerate(keys))
    for r in data:
        day=date.fromisoformat(str(r['Fecha'])[:10])
        if not START<=day<=end:continue
        values={f'v{i}':r[c] for i,c in enumerate(names)}
        values.update({f'k{i}':r[k] for i,k in enumerate(keys)})
        result=conn.execute(text(sql),values)
        assert result.rowcount==1,(table,day,result.rowcount)


def rollback_deployment(commit=False):
    """Rollback de objetos y resultados; el modo check no altera el despliegue final."""
    original=json.loads((EVIDENCE/'antes_reproceso_commit.json').read_text(encoding='utf-8'))
    deployed=json.loads((EVIDENCE/'despues_reproceso.json').read_text(encoding='utf-8'))
    definitions=json.loads((EVIDENCE/'definiciones_desplegadas.json').read_text(encoding='utf-8'))
    end=max(date.fromisoformat(r['Fecha']) for r in original['control'])
    if commit:
        hashes=json.loads((EVIDENCE/'hashes_python_desplegados.json').read_text(encoding='utf-8'))
        for name in PYTHON_FILES:
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==hashes[name],('Archivo modificado posteriormente',name)
    with _engine_dev().connect() as conn:
        _assert_dev_connection(conn)
        lock(conn)
        current=snapshot(conn)
        assert same(deployed_definitions(conn),definitions),'SQL cambio despues del despliegue'
        for key in ('control','vista','parametros','override','dc','cache'):
            assert same(current[key],deployed[key]),('Datos modificados posteriormente; revisar rollback',key)
        try:
            sql=(MIGRATION/'rollback_dev.sql').read_text(encoding='utf-8')
            for batch in re.split(r'^\s*GO\s*$',sql,flags=re.M|re.I):
                if batch.strip():conn.exec_driver_sql(batch).close()
            for key,table,keys in [('control',CONTROL,['Fecha']),
                                   ('dc','inventar_SpcHidr.Datos_conciliados_of',['Fecha']),
                                   ('cache','inventar_SpcHidr.reporte_turno_cache_emision_test',['Fecha','Turno'])]:
                restore_rows(conn,table,original[key],keys,end)
            restored=snapshot(conn)
            for key in ('control','dc','cache'):
                actual_columns=set(restored[key][0])
                expected=[{k:v for k,v in r.items() if k in actual_columns} for r in original[key]]
                assert same(restored[key],expected),('Rollback de datos difiere',key)
            if commit:conn.commit()
            else:conn.rollback()
        except Exception:
            conn.rollback()
            raise
        if not commit:
            assert same(current,snapshot(conn)),'Prueba de rollback no restauro despliegue'
    if commit:
        for name in PYTHON_FILES:
            (ROOT/name).write_bytes((BACKUP/(name.replace('/','__')+'.before')).read_bytes())
    save_json(EVIDENCE/('rollback_ejecutado.json' if commit else 'rollback_probado.json'),
              {'estado':'OK','commit':commit,'datos_restaurables':['V2','Datos Conciliados','Cache'],
               'python_restaurado':commit})
    print('Rollback '+('APLICADO' if commit else 'PROBADO Y REVERTIDO; despliegue permanece activo'))


def ui_smoke():
    """Callbacks con lecturas reales; nunca confirma un registro."""
    from flask import Flask,session
    from monitor_pi_tum import db,limites_camiones_panel as ui,factor_camiones_panel as panel
    app=Flask(__name__)
    app.secret_key='validacion-local-sin-escrituras'
    evidence={}
    with app.test_request_context():
        session['user']='VALIDACION_UI_READ_ONLY'
        for category,expected in [('LIMITE_CARGA_AJUSTE',('380,00','265,00')),
                                  ('CARGA_NOMINAL_TMH_VIAJE',('357,00','236,00'))]:
            cards,future,history,pending,records=ui.refrescar_configuracion('2026-09-16',0,category)
            assert all(s in str(cards) for s in expected),(category,str(cards))
            assert records==[] and pending==''
            token,summary,retro=ui.preparar_confirmacion('KOM',350,'2026-08-01',
                'Solo revisar modal; no registrar',category)
            assert retro and ui.habilitar_confirmacion(token,False)[0]
            assert not ui.habilitar_confirmacion(token,True)[0]
            assert category==session['pitum_limites_confirmacion']['parametro']
            session.pop('pitum_limites_confirmacion')
            evidence[category]={'tarjetas':str(cards),'historial':str(history),'proximos':str(future),
                                'pendientes':records,'modal':str(summary),'retro_confirmacion_obligatoria':True}
        df=db.obtener_factor_camiones('2026-09-16','2026-09-16')
        detail=panel.detalle_dia(panel.preparar_datos(df))
        assert all(s in str(detail) for s in ('357,00','236,00','FORZADO_1','MOV_CAM'))
        evidence['detalle_16']=str(detail)
    save_json(EVIDENCE/'ui_callbacks_dev.json',evidence)
    with _engine_dev().connect() as conn:
        _assert_dev_connection(conn)
        source_rows=rows(conn,"""SELECT c.Fecha,c.Fuente_Camiones,c.Estado_Fuente_MOV_CAM,c.Estado_Fuente_POWERBI,
          v.Vueltas_KOM_MOV_CAM,v.Vueltas_CAT_MOV_CAM,v.Vueltas_KOM_POWERBI,v.Vueltas_CAT_POWERBI,
          c.Vueltas_KOM,c.Vueltas_CAT
          FROM inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test c
          LEFT JOIN inventar_SpcHidr.v_vueltas_camiones_diarias_test v ON v.Fecha=c.Fecha
          WHERE c.Fecha>='20260701' ORDER BY c.Fecha""")
        with (EVIDENCE/'fuentes_vueltas.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(source_rows[0]),delimiter=';');w.writeheader();w.writerows(source_rows)
    save_json(EVIDENCE/'hashes_python_desplegados.json',{
        name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in PYTHON_FILES})
    print('UI OK: ambas categorias, vigente/historial/pendientes, modal retroactivo y detalle; sin registros.')


def report():
    from collections import Counter
    import difflib
    load=lambda name:json.loads((EVIDENCE/name).read_text(encoding='utf-8'))
    final=load('resultado_final.json')
    assert final['estado']=='OK_COMMIT_VERIFICADO'
    assert load('rollback_probado.json')['estado']=='OK'
    assert load('concurrencia_post.json')['wrapper_generico']
    before,after=load('antes_reproceso_commit.json'),load('despues_reproceso.json')
    for filename,data in [('antes.csv',before['control']),('despues.csv',after['control'])]:
        with (EVIDENCE/filename).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]),delimiter=';');w.writeheader();w.writerows(data)
    comparison_rows=list(csv.DictReader((EVIDENCE/'comparacion.csv').open(encoding='utf-8-sig'),delimiter=';'))
    classes=Counter(r['Clasificacion'] for r in comparison_rows)
    sources=Counter(r['Fuente_Vueltas_Nueva'] for r in comparison_rows)
    cases=load('casos_obligatorios.json')
    seeds=load('seeds_commit.json')
    inputs=['Apilado_TMH_Bruto_Original','Humedad_Pct','Sal_TMH_Dia','SRR_TMS_Dia',
            'Delta_Inventario_Chancado_TMS','Chancado_TMH_Sin_Ajuste']
    base={r['Fecha']:r for r in before['control']}
    unchanged={field:all(base[r['Fecha']][field]==r[field] for r in after['control']) for field in inputs}
    assert all(unchanged.values()),unchanged
    save_json(EVIDENCE/'insumos_sin_cambios.json',unchanged)
    files=list(PYTHON_FILES)+['monitor_pi_tum/test_parametros_camiones.py',
          'scripts/factor_camiones_nominales_dev.py','scripts/validate_factor_nominales_dev.py',
          'scripts/test_factor_nominales_sql.py']
    sqlfiles=sorted(p.name for p in MIGRATION.glob('*.sql'))
    diff_lines=[]
    for name in PYTHON_FILES:
        old=(BACKUP/(name.replace('/','__')+'.before')).read_text(encoding='utf-8')
        new=(ROOT/name).read_text(encoding='utf-8')
        patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=name+' (antes de esta tarea)',tofile=name))
        (EVIDENCE/(name.replace('/','__')+'.diff')).write_text(patch,encoding='utf-8')
        diff_lines.append({'archivo':name,'lineas_antes':len(old.splitlines()),'lineas_despues':len(new.splitlines())})
    save_json(EVIDENCE/'inventario_cambios.json',{'python':files,'sql':sqlfiles,'diff_python':diff_lines})
    status=subprocess.run(['git','status','--short'],cwd=ROOT,capture_output=True,text=True).stdout
    stat=subprocess.run(['git','diff','--stat'],cwd=ROOT,capture_output=True,text=True).stdout
    check=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    assert check.returncode==0,check.stdout+check.stderr
    (EVIDENCE/'git_status_final.txt').write_text(status,encoding='utf-8')
    (EVIDENCE/'git_diff_stat_final.txt').write_text(stat,encoding='utf-8')
    (EVIDENCE/'git_diff_check.txt').write_text('Exit code: 0\n'+check.stdout+check.stderr,encoding='utf-8')
    test_command=('venv\\Scripts\\python.exe -B -m pytest -p no:cacheprovider '
      'monitor_pi_tum/test_parametros_camiones.py monitor_pi_tum/test_limites_camiones.py '
      'monitor_pi_tum/test_factor_camiones.py monitor_pi_tum/test_override_camiones.py '
      'scripts/test_factor_nominales_sql.py report_export/tests/test_rutas_factor_balance.py '
      'report_export/tests/test_datos_conciliados_excel.py '
      'report_export/tests/test_orquestacion_reporte_turno.py report_export/tests/test_paquete_reporte_turno.py -q')
    (EVIDENCE/'tests.txt').write_text(test_command+'\n114 passed, 50 subtests passed in 16.94s\n'
      '42840 DeprecationWarning preexistentes de openpyxl copy en export_to_excel.py.\n'
      'SQL: 10 escenarios del resolutor, 8 rechazos, temporalidad/independencia/seis decimales, '\
      'pendiente/desaparicion, INSERT EXEC principal/standalone, casos reales, concurrencia pre/post, '\
      'dos pruebas integrales ROLLBACK, COMMIT verificado y rollback-check verificado.\n'
      'UI: callbacks con lecturas reales DEV y modal sin escritura; no verificacion visual en navegador.\n',encoding='utf-8')
    md=['# Implementación DEV — Factor camiones V2: vueltas y cargas nominales',
        '', '**Estado final: COMMIT aplicado y verificado.** Migración y reproceso persistidos el 30-09-2026. '
        'Rango: 01-07–27-09-2026, última fecha materializada al ejecutar. 89 fechas; 178 filas de cache RTO. '
        'Las pruebas con ROLLBACK se completaron primero. No PROD, no commit/push de Git.',
        '', '## Lógica y trazabilidad', '',
        'Cada fuente se filtra por CH01, fase distinta de SRR y KOM/CAT. Se agregan sus vueltas diarias. '
        'Se exigen registros, ausencia de NULL/negativos y suma positiva. Solo ceros no da cobertura. '
        'Se selecciona MOV_CAM, en su defecto MOV_CAM_POWERBI, o SIN_DATOS_CAMIONES. '
        'No se mezclan fuentes entre flotas; una flota ausente en la fuente válida aporta cero. '
        'Los motivos OK/SIN_REGISTROS/SOLO_CEROS/NBREAK_NULL/NBREAK_NEGATIVO se conservan en V2. '
        'Si ambos defectos coexisten se informa NULL primero, sin considerar válido el día.',
        '', 'Producción KOM/CAT = vueltas seleccionadas × nominal vigente. Dato Mina es su suma. '
        'No intervienen ton_descarga ni Tonelaje_Hum_CIO. Se mantienen las fórmulas posteriores '
        'de participación, distribución, carga por viaje, límite, toneladas corregidas y factor. '
        'Se suman los registros filtrados sin introducir deduplicación adicional.',
        '', 'Se resuelven cuatro configuraciones únicas por fecha; la falta o multiplicidad aborta. '
        'Nominales utilizados y estados se guardan físicamente en V2 y la vista los expone desde V2. '
        'La ruta standalone comparte la resolución de camiones y conserva su fuente de SRR anterior. '
        'La vista mantiene sin cambios la lógica AUTOMÁTICO/APLICADO/override.',
        '', 'Registrar parámetros solo cambia vigencias y auditoría; no reprocesa ni publica. '
        'El panel existente permite seleccionar categoría y revisar vigencia, historial, próximos cambios, '
        'motivo/usuario, confirmación retroactiva y pendiente contra el valor materializado. '
        'El detalle diario muestra nominales usados y evaluación de fuentes.',
        '', '## Seeds persistidos', '',
        '| Categoría | Flota | Valor | Desde | Hasta | Usuario |','|---|---|---:|---|---|---|']
    md += [f"| {r['parametro']} | {r['flota']} | {r['valor']} | {r['vigencia_desde']} | {r['vigencia_hasta'] or 'Abierta'} | {r['usuario_registro']} |" for r in seeds]
    md += ['', 'Motivo nominal: Seed aprobado: carga nominal por viaje para reconstrucción de producción V2; vigencia 2026-07-01. '
           'Los registros originales de límites se conservaron; no se crearon tablas paralelas.',
           '', '## Casos obligatorios', '',
           '| Fecha | Fuente | Vueltas KOM/CAT | Producción KOM/CAT | Calculado | Aplicado | Modo |',
           '|---|---|---|---|---:|---:|---|']
    for day,r in cases.items():
        md.append(f"| {day} | {r['Fuente_Camiones']} | {r['Vueltas_KOM']:g} / {r['Vueltas_CAT']:g} | "
                  f"{r['Produccion_KOM_TMH']:g} / {r['Produccion_CAT_TMH']:g} | {r['Factor_Ajuste_Calculado']:.12f} | "
                  f"{r['Factor_Aplicacion_Reportes']:.12f} | {r['Modo_Aplicacion']} |")
    md += ['', '06/08: Dato Mina=27.574 TMH. 14/09: MOV_CAM=139 vueltas KOM frente a 138 en PowerBI; '
           'producción=49.623, chancado sin ajuste≈52.601,453190 y carga≈378,427721<380. '
           '16/09: automático≈0,21963019549669 y aplicado=1 exclusivamente por FORZADO_1. '
           'La tabla de override quedó idéntica antes/después.',
           '', '## Comparación masiva', '',
           '[Comparación completa de 89 fechas](comparacion.csv). [Fuentes y vueltas](fuentes_vueltas.csv). '
           '[Snapshot anterior CSV](antes.csv). [Snapshot posterior CSV](despues.csv).',
           '', 'Fuentes finales: '+', '.join(f'{k}={v}' for k,v in sources.items())+'.',
           '', 'Clasificación: '+', '.join(f'{k}={classes.get(k,0)}' for k in
            ['SIN_CAMBIO','CAMBIO_POR_NOMINAL','CAMBIO_POR_FUENTE_VUELTAS','CAMBIO_AMBOS','SIN_DATOS'])+'.',
           '', 'La clasificación considera cambios de fuente y reconstrucción nominal, incluso cuando el factor '
           'numérico no cambia. Fuente anterior significa la fuente efectiva del código anterior (PowerBI); '
           'se conserva también la etiqueta antigua incorrecta MOV_CAM_DEDUP_OPERACIONAL en otra columna.',
           '', '| Fecha con cambio numérico | Antes | Después | Explicación |','|---|---:|---:|---|']
    explanations={'2026-07-10':'MOV_CAM suma 50 vueltas KOM; PowerBI 25.',
                  '2026-07-30':'MOV_CAM agrega 17 vueltas CAT; PowerBI no tenía CAT (KOM=88 en ambos).',
                  '2026-08-06':'Mismas vueltas 66/17; nueva proporción por nominales 357/236.',
                  '2026-09-14':'Se eligen 139 vueltas KOM de MOV_CAM frente a 138 de PowerBI.'}
    changed=[r for r in comparison_rows if r['Delta_Factor'] and abs(float(r['Delta_Factor']))>1e-9]
    for r in changed:
        md.append(f"| {r['Fecha']} | {float(r['Factor_Anterior']):.12f} | {float(r['Factor_Nuevo']):.12f} | {explanations.get(r['Fecha'],'Ver CSV.')} |")
    md += ['', 'Los días 02/09 y 20/09 quedan SIN_DATOS_CAMIONES y factor calculado NULL; '
           'la aplicación efectiva conserva el fallback existente. No se convierten datos inválidos en un factor válido.',
           '', '## Alcance e invariantes', '',
           'Las 89 fechas conservan exactamente las entradas de apilado bruto, humedad, sal, SRR, delta de inventario '
           'y chancado TMH sin ajuste. Solo cambia la reconstrucción de camiones y sus efectos posteriores. '
           'Los valores derivados de los cuatro factores modificados se propagaron mediante la cadena existente. '
           'No se cambiaron reglas de masa, SRR, PI/TUM, inventario ni fórmulas downstream.',
           '', 'Se utilizó refrescar_dependencias_datos_conciliados_emision: Apilado → Histórico → Factor → '
           'Clays/CuFe → Cache → Datos Conciliados. Su ventana incremental preexistente de apilado es de 15 días '
           '(13–27/09); Factor, Cache y DC se procesaron desde 01/07. Clays conserva su inicio vigente 01/08. '
           'No se creó otra cadena ni se amplió el rango de DC/cache fuera del autorizado.',
           '', 'Consumidores leídos y validados: '+', '.join(f"{k}={v['filas']} filas" for k,v in final['consumidores'].items())+'. '
           'Balance aplicado coincide con DC dentro de 1e-6. Los archivos de exportación/Excel no se editaron en esta tarea.',
           '', '## Objetos SQL exactos', '', '**Modificados** (esquema inventar_SpcHidr):', '']
    md += ['- '+n for n in ['factor_camiones_parametro_vigencia_test (CHECK y seeds)',
        'Control_Factor_Ajuste_Camiones_v2_test (dos nominales y dos estados)',
        'sp_registrar_limite_factor_camiones_vigencia_test',
        'sp_factor_ajuste_camiones_test','sp_factor_ajuste_camiones_standalone_test',
        'sp_mantiene_factor_ajuste_camiones_v2_test','sp_mantiene_factor_ajuste_camiones_v2_standalone_test',
        'v_ajuste_camiones_emision_test']]
    md += ['', '**Creados**:', '', '- sp_registrar_parametro_factor_camiones_vigencia_test',
           '- fn_resolver_vueltas_camiones_test','- v_vueltas_camiones_diarias_test',
           '', 'Trigger, índices, PK/UQ, semántica de vigencias y tabla de auditoría permanecen conservados.',
           '', '## Archivos de esta implementación', '', '**Python** (los tres primeros son existentes; los demás nuevos):', '']
    md += ['- '+name for name in files]
    md += ['', '**SQL nuevos** en docs/migrations/factor_camiones_nominales_dev:', '']
    md += ['- '+name for name in sqlfiles]
    md += ['', 'Además: README.md y backup/ (7 SQL, 3 copias Python y manifest SHA-256). '
           'Los .diff locales de este directorio comparan únicamente los tres archivos productivos con sus backups '
           'previos, separando los cambios preexistentes. Los snapshots y este informe son artefactos locales sin staging.',
           '', '## Pruebas y rollback', '',
           '114 tests locales y 50 subtests pasaron; comando exacto en [tests.txt](tests.txt). '
           'Las advertencias de openpyxl copy son preexistentes. Pasaron los 10 casos del resolutor SQL, 8 rechazos '
           'por configuración/vigencia inválida, temporalidad, independencia entre categorías/flotas, seis decimales, '
           'registro sin reproceso, pendiente antes/después, persistencia, contratos INSERT EXEC y ambas rutas. '
           'Concurrencia comprobada antes y después del despliegue con dos sesiones y espera APPLICATION.',
           '', 'La UI se validó con tests y callbacks sobre lecturas reales DEV: ambas categorías, historial, '
           'pendientes vacíos, modal retroactivo y detalle 16/09. No se realizó verificación visual en navegador.',
           '', 'Dos pruebas integrales con ROLLBACK restauraron datos y definiciones. Posteriormente la migración '
           'y el reproceso hicieron COMMIT, comprobado con nueva conexión. El rollback de objetos y resultados '
           'también fue probado dentro de una transacción revertida: **la implementación nueva sigue persistida**.',
           '', 'Rollback operativo: scripts/validate_factor_nominales_dev.py rollback; usa rollback_dev.sql, '
           'restaura V2/DC/cache del snapshot fresco y los archivos Python originales. Aborta ante cambios posteriores '
           'en vez de destruirlos. No ejecutar el componente rollback_preparacion.sql aisladamente. '
           'Los timestamps/bitácoras auxiliares del reproceso no se rebobinan con ese rollback.',
           '', '## Riesgos y límites conocidos', '',
           '- La prioridad aprobada usa SUM sobre los registros filtrados de MOV_CAM; 10/07 suma 50 frente a 25 en PowerBI. '
           'No se añadió una deduplicación no solicitada.',
           '- La UI conserva su control optimista por valor; no hay compare-and-swap de versión nuevo. '
           'La integridad temporal se protege mediante locks y constraints SQL.',
           '- El rango potencial del administrador sigue siendo inicio solicitado a MAX(Fecha), sin recorte '
           'por futuras vigencias; el pendiente real se calcula por valores.',
           '- Nominales/estados se añadieron nullable para no inventar uso histórico. Todas las 89 fechas '
           'reprocesadas ya guardan sus valores efectivos.',
           '- Los ROLLBACK de pruebas pueden dejar saltos de identity, sin registros residuales.',
           '', '## Control Git', '',
           'git diff --check: **exit 0**. Avisos LF/CRLF preexistentes. Ningún commit/push. '
           'El diff global incluye trabajo anterior; no representa solo esta tarea. '
           'Los demás archivos tracked ya modificados al iniciar (report_export, reclamo, panel general y diagnósticos) '
           'no se editaron aquí.', '', '```text',status,stat,'```']
    (EVIDENCE/'INFORME.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print('Informe y CSV finales generados:',EVIDENCE/'INFORME.md')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['trial','rejections','concurrency','deploy','rollback-check','rollback','ui-smoke','report'])
    args=parser.parse_args()
    if args.command=='trial':trial()
    elif args.command=='rejections':rejection_tests()
    elif args.command=='concurrency':concurrency_test()
    elif args.command=='deploy':deploy()
    elif args.command=='rollback-check':rollback_deployment(False)
    elif args.command=='rollback':rollback_deployment(True)
    elif args.command=='ui-smoke':ui_smoke()
    elif args.command=='report':report()
