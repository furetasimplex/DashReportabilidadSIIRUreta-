"""Construcción, validación transaccional y despliegue DEV de límites V2.

No publica ni conserva recálculos históricos. Ver informe en docs/migrations.
"""
import argparse
import difflib
import math
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
from scripts.validate_factor_camiones_fase2a_baseline import compare, rows, save, CONTROL, VIEW, SCHEMA

ROOT = Path('docs/migrations/factor_camiones_fase2a')
NAMES = ('sp_factor_ajuste_camiones_test', 'sp_mantiene_factor_ajuste_camiones_v2_test', 'v_ajuste_camiones_emision_test')
PARAM = SCHEMA + 'factor_camiones_parametro_vigencia_test'
AUDIT = SCHEMA + 'factor_camiones_parametro_auditoria_test'
REG = SCHEMA + 'sp_registrar_limite_factor_camiones_vigencia_test'


def equivalent(before, after):
    """No redondea: conserva diferencias y separa ruido FLOAT de cambios funcionales.

    Ocho ULP cubren acumulaciones FLOAT y las operaciones posteriores. Para
    checks de cancelación se usa la escala de sus operandos, no la del cero.
    NULL, enteros, flags y estados requieren igualdad exacta.
    """
    result = compare(before, after)
    source = {r['Fecha']: r for r in before}
    functional = []
    for diff in result['diferencias']:
        a,b=diff.get('antes'),diff.get('despues')
        if isinstance(a,float) and isinstance(b,float):
            scale=max(abs(a),abs(b))
            if diff['columna'].startswith('Check_'):
                row=source[diff['Fecha']]
                scale=max(scale,abs(row.get('Dato_Mina_TMH') or 0),abs(row.get('Apilado_TMH_Bruto') or 0))
            bound=8*math.ulp(scale)
            diff['diferencia_absoluta']=abs(a-b)
            diff['cota_8_ULP']=bound
            diff['solo_representacion_float']=abs(a-b)<=bound
            if diff['solo_representacion_float']:
                continue
        functional.append(diff)
    result['diferencias_funcionales']=functional
    return result

RESOLVER = '''
    -- FASE 2A: una copia consistente de las vigencias, nunca valores de respaldo.
    -- HOLDLOCK protege la lectura completa frente al registro transaccional.
    SELECT flota,parametro,valor,vigencia_desde,vigencia_hasta
    INTO #ParametrosFactorV2
    FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (HOLDLOCK)
    WHERE activo=1 AND parametro='LIMITE_CARGA_AJUSTE';
    ;WITH Dias AS (
        SELECT @FechaInicio AS Fecha
        UNION ALL SELECT DATEADD(day,1,Fecha) FROM Dias WHERE Fecha<@FechaFin
    )
    SELECT d.Fecha,f.flota,COUNT(p.flota) AS cantidad,CAST(MIN(p.valor) AS float) AS limite
    INTO #LimitesFactorV2
    FROM Dias d CROSS JOIN (VALUES ('KOM'),('CAT')) f(flota)
    LEFT JOIN #ParametrosFactorV2 p ON p.flota=f.flota AND p.vigencia_desde<=d.Fecha
        AND (p.vigencia_hasta IS NULL OR d.Fecha<p.vigencia_hasta)
    GROUP BY d.Fecha,f.flota OPTION (MAXRECURSION 0);
    DECLARE @ErrorLimite nvarchar(2048);
    SELECT TOP(1) @ErrorLimite=CONCAT(
        CASE WHEN cantidad=0 THEN 'No existe limite vigente ' ELSE 'Existen multiples limites vigentes ' END,
        flota,' para ',CONVERT(varchar(10),Fecha,23),'.')
    FROM #LimitesFactorV2 WHERE cantidad<>1 ORDER BY Fecha,flota;
    IF @ErrorLimite IS NOT NULL THROW 51020,@ErrorLimite,1;
    CREATE UNIQUE CLUSTERED INDEX IX_LimitesFactorV2 ON #LimitesFactorV2(Fecha,flota);
'''


def sql(conn, source):
    for batch in re.split(r'^\s*GO\s*$', source, flags=re.M | re.I):
        if batch.strip():
            conn.exec_driver_sql(batch)


def alter(source):
    return re.sub(r'\bCREATE\s+(?:OR\s+ALTER\s+)?(PROCEDURE|VIEW)\b', r'ALTER \1', source, count=1, flags=re.I)


def build(defs):
    calc, maintain, view = (defs[n] for n in NAMES)
    marker = '    ;WITH SRR_Diario AS'
    assert calc.count(marker) == 1
    calc = calc.replace(marker, RESOLVER + '\n' + marker)
    # Sección 7: límites efectivos acompañan cada fecha a través del resultado.
    old = '    SELECT\n        c.*,\n        CASE\n            WHEN c.Produccion_KOM_TMH = 0'
    assert calc.count(old) == 1
    calc = calc.replace(old, '    SELECT\n        c.*,\n        lk.limite AS Limite_KOM_TMH_Viaje,\n        lc.limite AS Limite_CAT_TMH_Viaje,\n        CASE\n            WHEN c.Produccion_KOM_TMH = 0')
    for number, alias, col in [('380.0','lk','KOM'),('265.0','lc','CAT')]:
        assert calc.count(number) == 4
        # Primeras dos ocurrencias: corrección; últimas dos: estado final.
        calc = calc.replace(number, alias + '.limite', 2)
        calc = calc.replace(number, 'c.Limite_' + col + '_TMH_Viaje')
    calc = calc.replace('FROM #FactorCargas AS c;', '''FROM #FactorCargas AS c
    JOIN #LimitesFactorV2 lk ON lk.Fecha=c.Fecha AND lk.flota='KOM'
    JOIN #LimitesFactorV2 lc ON lc.Fecha=c.Fecha AND lc.flota='CAT';''')
    end = '        c.Flag_Humedad_Inventario_Valida\n    FROM #FactorCorregido AS c'
    assert calc.count(end) == 1
    calc = calc.replace(end, '        c.Flag_Humedad_Inventario_Valida,\n        c.Limite_KOM_TMH_Viaje,\n        c.Limite_CAT_TMH_Viaje\n    FROM #FactorCorregido AS c')
    maintain, count = re.subn(r'(Flag_Humedad_Inventario_Valida bit NULL)(\s*\);)',
        r'\1,\n        Limite_KOM_TMH_Viaje float NOT NULL,\n        Limite_CAT_TMH_Viaje float NOT NULL\2', maintain)
    assert count == 1
    for number, flota in [('380.0','KOM'),('265.0','CAT')]:
        old = f'CAST({number} AS float) AS Limite_{flota}_TMH_Viaje'
        assert maintain.count(old) == 1
        maintain = maintain.replace(old, f'b.Limite_{flota}_TMH_Viaje')
    # Conserva orden de columnas de la vista; agrega al final.
    view, count = re.subn(r'(f\.Fecha_Calculo)(\s+FROM)',
        r'\1,\n    f.Limite_KOM_TMH_Viaje,\n    f.Limite_CAT_TMH_Viaje\2', view)
    assert count == 1
    result = dict(zip(NAMES, map(alter, (calc, maintain, view))))
    for i, (name, content) in enumerate(result.items(), 3):
        (ROOT / f'{i:02}_{name}.sql').write_text(content, encoding='utf-8')
        (ROOT / f'{name}.diff').write_text(''.join(difflib.unified_diff(
            defs[name].splitlines(True), content.splitlines(True), fromfile='antes/'+name, tofile='despues/'+name)), encoding='utf-8')
    rollback = "IF DB_NAME()<>N'inventar_SpcHidr' THROW 51000,'Solo DEV.',1;\nGO\n"
    rollback += '\nGO\n'.join(alter(defs[n]) for n in NAMES)
    rollback += '''
GO
DROP PROCEDURE IF EXISTS inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test;
DROP TRIGGER IF EXISTS inventar_SpcHidr.tr_factor_camiones_vigencia_solapamiento_test;
DROP TABLE IF EXISTS inventar_SpcHidr.factor_camiones_parametro_auditoria_test;
DROP TABLE IF EXISTS inventar_SpcHidr.factor_camiones_parametro_vigencia_test;
'''
    (ROOT / 'rollback_dev.sql').write_text(rollback, encoding='utf-8')
    return result


def definitions(conn):
    return {n:conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'), {'n':SCHEMA+n}).scalar_one().replace('\r\n','\n').replace('\r','\n') for n in NAMES}


def deploy(conn, generated):
    _assert_dev_connection(conn)
    sql(conn, (ROOT/'01_parametros.sql').read_text(encoding='utf-8'))
    sql(conn, (ROOT/'02_registro.sql').read_text(encoding='utf-8'))
    for code in generated.values():
        sql(conn, code)


def calc(conn, start, end):
    return [dict(r) for r in conn.execute(text('EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_test :a,:b'), {'a':start,'b':end}).mappings()]


def maintain(conn, start, end):
    conn.execute(text('EXEC inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test :a,:b,0'), {'a':start,'b':end})


def register(conn, flota, value, start):
    return dict(conn.execute(text('EXEC '+REG+' :f,:v,:d,:m,:u'),
        {'f':flota,'v':value,'d':start,'m':'PRUEBA REVERSIBLE FASE2A','u':'VALIDACION_FASE2A'}).mappings().one())


def params(conn):
    return [dict(r) for r in conn.execute(text('SELECT * FROM '+PARAM+' ORDER BY flota,vigencia_desde')).mappings()]


def resolve(conn,day,fleet):
    found=conn.execute(text('SELECT valor FROM '+PARAM+''' WHERE flota=:f AND parametro='LIMITE_CARGA_AJUSTE'
        AND activo=1 AND vigencia_desde<=:d AND (vigencia_hasta IS NULL OR :d<vigencia_hasta)'''),{'f':fleet,'d':day}).scalars().all()
    assert len(found)==1
    return float(found[0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', action='store_true', help='Persistir solo después de validación reversible satisfactoria')
    args = parser.parse_args()
    engine = _engine_dev()
    folder = ROOT / ('evidencia_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    folder.mkdir(parents=True, exist_ok=False)
    report = {}
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        try:
            _assert_dev_connection(conn)
            assert conn.execute(text('SELECT OBJECT_ID(:n)'), {'n':PARAM}).scalar() is None, 'Migración ya existente: revisar antes de reinstalar'
            assert not conn.execute(text('SELECT name FROM sys.triggers WHERE parent_id=OBJECT_ID(:n) AND is_disabled=0'), {'n':CONTROL}).all()
            defs = definitions(conn)
            for n,d in defs.items():
                (folder/(n+'.sql')).write_text(d,encoding='utf-8')
            h, hv = rows(conn, CONTROL), rows(conn, VIEW)
            old = rows(conn, SCHEMA+'Control_Factor_Ajuste_Camiones')
            olddef = conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'), {'n':SCHEMA+'sp_mantiene_factor_ajuste_camiones_test'}).scalar()
            save(folder/'H_control.json',h)
            save(folder/'H_vista.json',hv)
            save(folder/'columnas_control.json',[dict(r) for r in conn.execute(text('SELECT name, TYPE_NAME(user_type_id) tipo, precision,scale,is_nullable FROM sys.columns WHERE object_id=OBJECT_ID(:n) ORDER BY column_id'),{'n':CONTROL}).mappings()])
            start,end=h[0]['Fecha'],h[-1]['Fecha']
            original=calc(conn,start,end)
            report['O_vs_O_repetido']=equivalent(original,calc(conn,start,end))
            assert not report['O_vs_O_repetido']['diferencias_funcionales']
            maintain(conn,start,end)
            oc,ov=rows(conn,CONTROL),rows(conn,VIEW)
            report['H_vs_O']=compare(h,oc)
            save(folder/'O_calculo.json',original)
            generated=build(defs)
            deploy(conn,generated)
            seed=params(conn)
            assert len(seed)==2 and {r['flota']:float(r['valor']) for r in seed}=={'KOM':380.,'CAT':265.}
            assert all(r['vigencia_desde']==date(2026,7,1) and r['vigencia_hasta'] is None for r in seed)
            deploy(conn,generated)
            assert params(conn)==seed, 'Seed no idempotente'
            parameterized=calc(conn,start,end)
            report['O_vs_P_calculo']=equivalent(original,parameterized)
            save(folder/'comparaciones.json',report)
            assert not report['O_vs_P_calculo']['diferencias_funcionales'], report['O_vs_P_calculo']
            assert all(r['Limite_KOM_TMH_Viaje']==380 and r['Limite_CAT_TMH_Viaje']==265 for r in parameterized)
            maintain(conn,start,end)
            pc,pv=rows(conn,CONTROL),rows(conn,VIEW)
            report['O_vs_P_control']=equivalent(oc,pc)
            report['O_vs_P_vista']=equivalent(ov,pv)
            save(folder/'comparaciones.json',report)
            assert not report['O_vs_P_control']['diferencias_funcionales'] and not report['O_vs_P_vista']['diferencias_funcionales']
            maintain(conn,start,end)
            report['P_vs_P_repetido']=equivalent(pc,rows(conn,CONTROL))
            assert not report['P_vs_P_repetido']['diferencias_funcionales'], 'Mantenedor no idempotente'
            save(folder/'P_BASE_calculo.json',parameterized)
            candidates=[r for r in parameterized if r['Carga_KOM_Sin_Ajuste'] is not None and 350<r['Carga_KOM_Sin_Ajuste']<=380 and start+timedelta(days=5)<=r['Fecha']<=end-timedelta(days=5)]
            assert candidates, 'Sin candidato KOM entre 350 y 380: elegir otro umbral de prueba'
            d=candidates[0]['Fecha']
            impact=register(conn,'KOM',350,d)
            assert impact['Es_Retroactivo']==1 and impact['Fecha_Inicio_Afectada']==d and impact['Fecha_Fin_Afectada']==end
            changed=calc(conn,start,end)
            report['previo_frontera']=equivalent([r for r in parameterized if r['Fecha']<d],[r for r in changed if r['Fecha']<d])
            assert not report['previo_frontera']['diferencias_funcionales']
            for r in changed:
                assert r['Limite_KOM_TMH_Viaje']==(380 if r['Fecha']<d else 350)
                assert r['Limite_CAT_TMH_Viaje']==265
            original_day=next(r for r in parameterized if r['Fecha']==d)
            changed_day=next(r for r in changed if r['Fecha']==d)
            assert changed_day['KOM_TMH_Corregido']==changed_day['Vueltas_KOM']*350
            assert changed_day['KOM_TMH_Corregido']<original_day['KOM_TMH_Corregido']
            basecols=['Produccion_KOM_TMH','Produccion_CAT_TMH','Vueltas_KOM','Vueltas_CAT','Dato_Mina_TMH']
            report['produccion_viajes']=equivalent(
                [{k:r[k] for k in ['Fecha']+basecols} for r in parameterized],
                [{k:r[k] for k in ['Fecha']+basecols} for r in changed])
            assert not report['produccion_viajes']['diferencias_funcionales']
            maintain(conn,d-timedelta(days=5),d+timedelta(days=5))
            changed_view=next(r for r in rows(conn,VIEW) if r['Fecha']==d)
            assert changed_view['Limite_KOM_TMH_Viaje']==350 and changed_view['Limite_CAT_TMH_Viaje']==265
            assert changed_view['Factor_Aplicacion_Reportes']==changed_view['Factor_Ajuste_Calculado']
            for r in rows(conn,CONTROL):
                if d-timedelta(days=5)<=r['Fecha']<=d+timedelta(days=5):
                    assert r['Limite_KOM_TMH_Viaje']==(380 if r['Fecha']<d else 350)
                    assert r['Limite_CAT_TMH_Viaje']==265
            d2=d+timedelta(days=3)
            register(conn,'KOM',365,d2)
            successive=calc(conn,start,end)
            assert all(r['Limite_KOM_TMH_Viaje']==(380 if r['Fecha']<d else 350 if r['Fecha']<d2 else 365) for r in successive)
            future=date.today()+timedelta(days=30)
            impact_future=register(conn,'KOM',350,future)
            assert impact_future['Es_Retroactivo']==0
            assert resolve(conn,future-timedelta(days=1),'KOM')==365
            assert resolve(conn,future,'KOM')==350
            assert resolve(conn,future+timedelta(days=180),'KOM')==350
            # Inserción entre vigencias existentes: debe conservar el cambio futuro.
            middle=d+timedelta(days=1)
            register(conn,'KOM',360,middle)
            history=params(conn)
            assert next(r for r in history if r['flota']=='KOM' and r['vigencia_desde']==middle)['vigencia_hasta']==d2
            register(conn,'CAT',250,d)
            cat=calc(conn,d-timedelta(days=1),d+timedelta(days=1))
            assert [r['Limite_CAT_TMH_Viaje'] for r in cat]==[265,250,250]
            report['temporal']={'D':d,'D2':d2,'impacto_retroactivo':impact,'impacto_futuro':impact_future,
                'frontera':[{'Fecha':r['Fecha'],'KOM':r['Limite_KOM_TMH_Viaje'],'CAT':r['Limite_CAT_TMH_Viaje']} for r in changed if d-timedelta(days=1)<=r['Fecha']<=d+timedelta(days=1)],
                'caso_original':original_day,'caso_prueba':changed_day,'vista_prueba':changed_view,'vigencias_provisionales':history,
                'auditoria':[dict(r) for r in conn.execute(text('SELECT * FROM '+AUDIT+' ORDER BY id')).mappings()]}
            assert report['temporal']['auditoria'][0]['valor_anterior']==380
            assert report['temporal']['auditoria'][0]['valor_nuevo']==350
            assert report['temporal']['auditoria'][0]['vigencia_desde']==d
            assert report['temporal']['auditoria'][0]['es_retroactivo'] is True
            assert report['temporal']['auditoria'][0]['usuario']=='VALIDACION_FASE2A'
            # Rollback técnico ensayado dentro de la transacción de prueba.
            sql(conn,(ROOT/'rollback_dev.sql').read_text(encoding='utf-8'))
            restored_definitions=definitions(conn)
            assert {n:alter(v).strip() for n,v in restored_definitions.items()}=={n:alter(v).strip() for n,v in defs.items()}, {
                n:list(difflib.unified_diff(alter(defs[n]).strip().splitlines(),alter(v).strip().splitlines()))
                for n,v in restored_definitions.items() if alter(v).strip()!=alter(defs[n]).strip()}
            assert conn.execute(text('SELECT OBJECT_ID(:n)'),{'n':PARAM}).scalar() is None
            report['rollback_tecnico_ensayado']=True
            save(folder/'comparaciones.json',report)
        finally:
            conn.rollback()
            # Comprueba restauración incluso cuando una prueba falla.
            if 'h' in locals():
                restored=(rows(conn,CONTROL)==h and rows(conn,VIEW)==hv and definitions(conn)==defs)
                save(folder/'restauracion_tras_prueba.json',{'control_vista_definiciones_identicos':restored})
                conn.rollback()
                assert restored, 'Revisar restauración de prueba'
        _assert_dev_connection(conn)
        assert rows(conn,CONTROL)==h and rows(conn,VIEW)==hv and rows(conn,SCHEMA+'Control_Factor_Ajuste_Camiones')==old
        assert definitions(conn)==defs
        assert conn.execute(text('SELECT OBJECT_ID(:n)'),{'n':PARAM}).scalar() is None
        report['rollback_pruebas_identico']=True
        conn.rollback()
        # Pruebas negativas aisladas: cada fallo debe revertir su propia transacción.
        negatives(conn,generated,folder,report)
        if args.deploy:
            try:
                _assert_dev_connection(conn)
                assert definitions(conn)==defs
                assert rows(conn,CONTROL)==h and rows(conn,VIEW)==hv, 'Histórico cambió durante validación'
                deploy(conn,generated)
                assert rows(conn,CONTROL)==h
                assert not compare(hv,rows(conn,VIEW))['diferencias']
                assert rows(conn,SCHEMA+'Control_Factor_Ajuste_Camiones')==old
                assert conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'), {'n':SCHEMA+'sp_mantiene_factor_ajuste_camiones_test'}).scalar()==olddef
                assert len(params(conn))==2
                assert conn.execute(text('SELECT COUNT(*) FROM '+AUDIT)).scalar()==0
                conn.commit()
                report['desplegado']=True
            except Exception:
                conn.rollback()
                raise
        save(folder/'comparaciones.json',report)
        print('Evidencia:',folder)
        print('O vs P: cero diferencias funcionales. Histórico preservado. Desplegado:',report.get('desplegado',False))


def negatives(conn,generated,folder,report):
    cases={
        'valor_cero':"EXEC "+REG+" 'KOM',0,'20261005',N'prueba',N'prueba'",
        'flota_invalida':"EXEC "+REG+" 'XXX',350,'20261005',N'prueba',N'prueba'",
        'motivo_vacio':"EXEC "+REG+" 'KOM',350,'20261005',N'',N'prueba'",
        'valor_negativo':"EXEC "+REG+" 'KOM',-350,'20261005',N'prueba',N'prueba'",
        'inicio_duplicado':"EXEC "+REG+" 'KOM',350,'20260701',N'prueba',N'prueba'",
        'parametro_invalido':"INSERT "+PARAM+"(flota,parametro,valor,vigencia_desde,vigencia_hasta,motivo,usuario_registro) VALUES('KOM','OTRO',350,'20261005','20261006','x','x')",
        'intervalo_invalido':"INSERT "+PARAM+"(flota,parametro,valor,vigencia_desde,vigencia_hasta,motivo,usuario_registro) VALUES('KOM','LIMITE_CARGA_AJUSTE',350,'20261005','20261005','x','x')",
        'solapamiento':"INSERT "+PARAM+"(flota,parametro,valor,vigencia_desde,vigencia_hasta,motivo,usuario_registro) VALUES('KOM','LIMITE_CARGA_AJUSTE',350,'20261005','20261006','x','x')",
        'abiertas_multiples':"INSERT "+PARAM+"(flota,parametro,valor,vigencia_desde,motivo,usuario_registro) VALUES('KOM','LIMITE_CARGA_AJUSTE',350,'20261005','x','x')",
        'faltante':"UPDATE "+PARAM+" SET activo=0 WHERE flota='KOM'; EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_test '20260907','20260907'",
        'previo_seed':"EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_test '20260630','20260701'",
        'multiples_calculo':"DISABLE TRIGGER inventar_SpcHidr.tr_factor_camiones_vigencia_solapamiento_test ON "+PARAM+"; INSERT "+PARAM+"(flota,parametro,valor,vigencia_desde,vigencia_hasta,motivo,usuario_registro) VALUES('KOM','LIMITE_CARGA_AJUSTE',350,'20260901','20260910','x','x'); EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_test '20260907','20260907'",
    }
    results={}
    for name,statement in cases.items():
        try:
            deploy(conn,generated)
            try:
                cursor=conn.connection.driver_connection.cursor()
                try:
                    cursor.execute(statement)
                    while cursor.nextset():
                        pass
                finally:
                    cursor.close()
            except Exception as exc:
                results[name]=str(exc)
                expected={'valor_cero':'51011','valor_negativo':'51011','flota_invalida':'51010',
                    'motivo_vacio':'51013','inicio_duplicado':'51015','parametro_invalido':'547',
                    'intervalo_invalido':'547','solapamiento':'51001','abiertas_multiples':'2601',
                    'faltante':'51020','previo_seed':'51020','multiples_calculo':'51020'}
                assert expected[name] in str(exc), 'Error inesperado en '+name+': '+str(exc)
            else:
                raise AssertionError('No rechazó '+name)
        finally:
            conn.rollback()
    report['rechazos']=results
    save(folder/'rechazos.json',results)


if __name__=='__main__':
    main()
