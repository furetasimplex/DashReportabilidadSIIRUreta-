"""Promoción explícita DEV: precheck separado, copias literales y validación antes de COMMIT."""
import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from sqlalchemy import text
from .db import _connection
from .map_db import validate_snapshot

OUT = Path(__file__).with_name('promocion_estado_operacional_reanudada_20261005')
PAIRS = {
    'parcela': ('inventar_SpcHidr.fn_estado_operacional_parcela_diario_test_v2',
                'inventar_SpcHidr.fn_estado_operacional_parcela_diario'),
    'modulo': ('inventar_SpcHidr.fn_estado_operacional_modulo_diario_test',
               'inventar_SpcHidr.fn_estado_operacional_modulo_diario'),
}
EXPECTED = {1: {'MIXTO': 1, 'REPOSO_PRE_RECLAMO': 12, 'RIEGO_DRENAJE': 19},
            2: {'APILADO': 1, 'CONFORMADO_PRE_RIEGO': 2, 'MIXTO': 2,
                'REPOSO_PRE_RECLAMO': 5, 'RIEGO_DRENAJE': 18}}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str)+'\n', encoding='utf-8')


def definition(conn, name):
    return conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:name))'), {'name': name}).scalar_one()


def split_definition(ddl, name):
    # Solo la cabecera se sustituye: el sufijo (parámetros/cuerpo/comentarios) queda byte a byte.
    schema, obj = name.split('.')
    pattern = r'\A\s*(?:CREATE\s+OR\s+ALTER|CREATE|ALTER)\s+FUNCTION\s+(?:\['+schema+r'\]|'+schema+r')\s*\.\s*(?:\['+obj+r'\]|'+obj+r')(?=\s|\()'
    match = re.match(pattern, ddl, re.I)
    if not match:
        raise RuntimeError('Cabecera no reconocida; no reconstruir DDL: '+name)
    return ddl[match.end():]


def functional_hash(ddl, name):
    # Más estricto que ignorar comentarios/espacios: se preserva todo el sufijo literal.
    return hashlib.sha256(split_definition(ddl, name).encode('utf-8')).hexdigest()


def columns(conn, name):
    return [tuple(r) for r in conn.execute(text('''SELECT column_id,name,system_type_id,
        user_type_id,max_length,precision,scale,is_nullable FROM sys.columns
        WHERE object_id=OBJECT_ID(:name) ORDER BY column_id'''), {'name': name})]


def guard(conn):
    if os.getenv('SQLSERVER_DB', '').lower() != 'inventar_spchidr':
        raise RuntimeError('Solo configuración DEV.')
    if conn.execute(text('SELECT DB_NAME()')).scalar_one().lower() != 'inventar_spchidr':
        raise RuntimeError('Solo conexión DEV.')


def precheck():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise RuntimeError('Evidencia existente: no sobrescribir backups.')
    report = {'database': 'inventar_SpcHidr', 'objects': {}, 'ddl_executed': False}
    with _connection() as conn:
        guard(conn)
        for kind, pair in PAIRS.items():
            for role, name in zip(('test', 'official'), pair):
                meta = conn.execute(text('''SELECT o.type,o.type_desc,m.uses_ansi_nulls,m.uses_quoted_identifier
                    FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                    WHERE o.object_id=OBJECT_ID(:name)'''), {'name': name}).mappings().one_or_none()
                ddl = definition(conn, name)
                if meta and ddl is None:
                    raise RuntimeError('Definición no visible: '+name)
                report['objects'][name] = dict(meta) if meta else None
                (OUT / f'{kind}_{role}_original.sql').write_text(ddl if ddl is not None else '-- AUSENTE EN PRECHECK DEV\n', encoding='utf-8', newline='')
                report[name] = {'columns': columns(conn, name), 'dependencies': [dict(r) for r in conn.execute(text('''
                    SELECT OBJECT_SCHEMA_NAME(referencing_id) AS schema_name,OBJECT_NAME(referencing_id) AS object_name,
                    referenced_schema_name,referenced_entity_name,referenced_id,referenced_minor_id
                    FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name)
                    OR referenced_id=OBJECT_ID(:name) OR
                    (referenced_schema_name=:schema AND referenced_entity_name=:object)'''),
                    {'name': name, 'schema': name.split('.')[0], 'object': name.split('.')[1]}).mappings()]}
                report[name]['text_references'] = [dict(r) for r in conn.execute(text('''
                    SELECT OBJECT_SCHEMA_NAME(object_id) AS schema_name,OBJECT_NAME(object_id) AS object_name
                    FROM sys.sql_modules WHERE definition LIKE :needle'''), {'needle': '%'+name.split('.')[1]+'%'}).mappings()]
            test, official = pair
            ddl = definition(conn, test)
            if not ddl or report['objects'][test]['type'] != 'IF':
                raise RuntimeError('TEST debe ser función inline visible.')
            candidate = 'CREATE FUNCTION '+official+split_definition(ddl, test)
            (OUT / f'{kind}_candidate.sql').write_text(candidate, encoding='utf-8', newline='')
            old = definition(conn, official)
            rollback = ('ALTER FUNCTION '+official+split_definition(old, official)) if old else 'DROP FUNCTION '+official+';'
            guarded = "IF DB_NAME() <> 'inventar_SpcHidr' THROW 51000, 'Solo DEV', 1;\nEXEC sys.sp_executesql N'"+rollback.replace("'", "''")+"';\n"
            (OUT / f'{kind}_rollback.sql').write_text(guarded, encoding='utf-8', newline='')
        save('precheck.json', report)
    print(json.dumps(report['objects'], indent=2), flush=True)


def rows(conn, name, day, parcel=None):
    params = {'fecha': day}
    args = ':fecha'
    if parcel is not None:
        params.update(pad=parcel['pad_id'], parcela=parcel['parcela_id'])
        args += ',:pad,:parcela'
    return [dict(r) for r in conn.execute(text(f'SELECT * FROM {name}({args})'), params).mappings()]


def bag(rs):
    return Counter(tuple(r.items()) for r in rs)


def validate(conn):
    report = {'hashes': {}, 'historical_rows': 0, 'solo_test': 0, 'solo_oficial': 0,
              'diferencias': 0, 'transiciones_terminales_reversibles': [], 'module_discrepancies': []}
    for kind, (test, official) in PAIRS.items():
        a, b = functional_hash(definition(conn, test), test), functional_hash(definition(conn, official), official)
        report['hashes'][kind] = {'test': a, 'official': b}
        assert a == b, 'Cuerpo funcional distinto'
        assert columns(conn, test) == columns(conn, official), 'Contrato distinto'
        if kind == 'parcela': assert len(columns(conn, official)) == 24
    test, official = PAIRS['parcela']
    previous = {}
    day = date(2026, 1, 1)
    while day <= date(2026, 9, 10):
        a, b = rows(conn, test, day), rows(conn, official, day)
        validate_snapshot(a, day.isoformat())
        validate_snapshot(b, day.isoformat())
        report['solo_test'] += sum((bag(a)-bag(b)).values())
        report['solo_oficial'] += sum((bag(b)-bag(a)).values())
        assert bag(a) == bag(b), 'Diferencia histórica '+str(day)
        report['historical_rows'] += len(b)
        for r in b:
            assert r['estado_operacional'] not in ('SIN_CLASIFICAR','SIN_COBERTURA_HIDRAULICA')
            key = (r['pad_id'], r['parcela_id'], r['campana_id'])
            prior = previous.get(key)
            state = r['estado_operacional']
            forbidden = {'DRENAJE_RESIDUAL': {'RIEGO','RIEGO_DRENAJE'},
                         'REPOSO_PRE_RECLAMO': {'RIEGO','RIEGO_DRENAJE','DRENAJE_RESIDUAL'}}
            if state in forbidden.get(prior, set()):
                report['transiciones_terminales_reversibles'].append((str(day), key, prior, state))
            previous[key] = state
        if day.day == 1: print('Histórico validado hasta', day, flush=True)
        day += timedelta(days=1)
    assert report['historical_rows'] == 15180
    assert not report['transiciones_terminales_reversibles'], report['transiciones_terminales_reversibles']
    report['canonical'] = {p: dict(Counter(r['estado_operacional'] for r in b if r['pad_id']==p)) for p in (1,2)}
    assert report['canonical'] == EXPECTED
    report['canonical_rows'] = b
    cases = {(1,17): ('MIXTO','APILADO = 1 | CONFORMADO_PRE_RIEGO = 1'),
             (2,1): ('MIXTO','RECLAMADO = 4 | RECLAMO = 1'),
             (2,2): ('MIXTO','RECLAMO = 1 | REPOSO_PRE_RECLAMO = 4'),
             (2,26): ('CONFORMADO_PRE_RIEGO',None), (2,27): ('CONFORMADO_PRE_RIEGO',None), (2,28): ('APILADO',None)}
    module_cases = {(1,29): [('57','REPOSO_PRE_RECLAMO'),('58','REPOSO_PRE_RECLAMO')],
                    (1,17): [('33','CONFORMADO_PRE_RIEGO'),('34','APILADO')],
                    (2,1): [(str(i),'RECLAMADO' if i<5 else 'RECLAMO') for i in range(1,6)]}
    report['modules'] = []
    for r in b:
        key = (r['pad_id'],r['numero_parcela'])
        if key in cases:
            state, composition = cases[key]
            assert r['estado_operacional'] == state
            if composition is not None: assert r['composicion_modulos'] == composition
        ma, mb = [rows(conn, name, date(2026,9,10), r) for name in PAIRS['modulo']]
        assert bag(ma) == bag(mb), 'Módulos distintos'
        if len(mb) != r['modulos_total']: report['module_discrepancies'].append(key)
        if key in module_cases:
            assert sorted((str(m['nombre_modulo']),m['estado_modulo']) for m in mb) == sorted(module_cases[key])
        report['modules'].append({'pad': r['pad_id'], 'parcela': r['numero_parcela'], 'expected': r['modulos_total'], 'rows': mb})
    assert not report['module_discrepancies']
    report['passed'] = True
    return report


def deploy():
    pre = json.loads((OUT/'precheck.json').read_text(encoding='utf-8'))
    with _connection() as conn:
        guard(conn)
        for kind, (test, official) in PAIRS.items():
            if definition(conn, official) is not None or pre['objects'][official] is not None:
                raise RuntimeError('Oficial existente: revisar respaldo/dependencias antes de sobrescribir; no se sobrescribe automáticamente.')
            saved = (OUT/f'{kind}_test_original.sql').read_bytes().decode('utf-8')
            assert definition(conn, test) == saved, 'TEST cambió desde precheck'
        try:
            for kind, (test, official) in PAIRS.items():
                meta = pre['objects'][test]
                conn.exec_driver_sql('SET ANSI_NULLS '+('ON' if meta['uses_ansi_nulls'] else 'OFF'))
                conn.exec_driver_sql('SET QUOTED_IDENTIFIER '+('ON' if meta['uses_quoted_identifier'] else 'OFF'))
                conn.exec_driver_sql((OUT/f'{kind}_candidate.sql').read_bytes().decode('utf-8'))
            report = validate(conn)
            save('validation_before_commit.json', report)
            conn.commit()
            save('deployment.json', {'committed': True, 'data_writes': False, 'objects': [v[1] for v in PAIRS.values()]})
            print('COMMIT DEV: ambos oficiales validados.', flush=True)
        except Exception:
            conn.rollback()
            save('deployment.json', {'committed': False, 'rolled_back': True})
            raise
    with _connection() as conn:
        guard(conn)
        for kind, (test, official) in PAIRS.items():
            assert functional_hash(definition(conn,test),test) == functional_hash(definition(conn,official),official)
        save('post_commit.json', {'persisted': True, 'hashes_match': True, 'tests_preserved': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['precheck','deploy'])
    args = parser.parse_args()
    precheck() if args.mode == 'precheck' else deploy()
