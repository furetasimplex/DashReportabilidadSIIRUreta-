"""Corrección acotada DEV: prueba reversible y despliegue sin reprocesar datos."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
from scripts.validate_factor_nominales_dev import lock, snapshot, same, rows

MIG = ROOT / 'docs/migrations/factor_camiones_nominales_dev'
OUT = ROOT / 'report_export/exports/validacion_nbreak_textual_20260930'
OBJECTS = {
    'fn_resolver_vueltas_camiones_test': '04_resolver_vueltas.sql',
    'v_vueltas_camiones_diarias_test': '05_vueltas_diarias.sql',
}


def save(name, data):
    (OUT / name).write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding='utf-8')


def definitions(c):
    return {n: c.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'),
                        {'n': 'inventar_SpcHidr.' + n}).scalar_one() for n in OBJECTS}


def regression(c):
    result = {'snapshot': snapshot(c)}
    control = result['snapshot']['control']
    assert len(control) == 89, 'Cambió el rango materializado; revisar antes de desplegar'
    start, end = min(r['Fecha'] for r in control), max(r['Fecha'] for r in control)
    for suffix in ('test', 'standalone_test'):
        result[suffix] = rows(c, 'EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_' + suffix +
                             ' @FechaInicio=:a,@FechaFin=:b', {'a': start, 'b': end})
        assert len(result[suffix]) == 89
    result['vueltas'] = rows(c, 'SELECT * FROM inventar_SpcHidr.v_vueltas_camiones_diarias_test '
                              'WHERE Fecha BETWEEN :a AND :b ORDER BY Fecha', {'a': start, 'b': end})
    return result


def textual_cases(c):
    # Ejecuta el cuerpo real de la vista con fixtures CTE; no inserta datos fuente.
    body = c.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.v_vueltas_camiones_diarias_test'))")).scalar_one()
    body = body[body.index('WITH Movimientos AS'):]
    body = body.replace('inventar_SpcHidr.mov_cam_powerbi', 'FixtureBI').replace('inventar_SpcHidr.mov_cam', 'FixtureMOV')
    cases = [(repr(v), [], [v], state, source) for v, state, source in [
        (None, 'NBREAK_NULL', 'SIN_DATOS_CAMIONES'),
        ('', 'NBREAK_NO_NUMERICO', 'SIN_DATOS_CAMIONES'),
        ('   ', 'NBREAK_NO_NUMERICO', 'SIN_DATOS_CAMIONES'),
        ('abc', 'NBREAK_NO_NUMERICO', 'SIN_DATOS_CAMIONES'),
        ('-1', 'NBREAK_NEGATIVO', 'SIN_DATOS_CAMIONES'),
        ('0', 'SOLO_CEROS', 'SIN_DATOS_CAMIONES'),
        (' 0 ', 'SOLO_CEROS', 'SIN_DATOS_CAMIONES'),
        ('1', 'OK', 'MOV_CAM_POWERBI'), ('1.5', 'OK', 'MOV_CAM_POWERBI')]]
    cases += [('10 + ' + repr(v), [], ['10', v], state, 'MOV_CAM_POWERBI' if state == 'OK' else 'SIN_DATOS_CAMIONES')
              for v, state in [('', 'NBREAK_NO_NUMERICO'), ('abc', 'NBREAK_NO_NUMERICO'),
                               (None, 'NBREAK_NULL'), ('-1', 'NBREAK_NEGATIVO'), ('0', 'OK')]]
    cases += [('fallback', [-1], ['10'], 'OK', 'MOV_CAM_POWERBI'),
              ('prioridad', [5], ['abc'], 'NBREAK_NO_NUMERICO', 'MOV_CAM'),
              ('ambas_invalidas', [None], [''], 'NBREAK_NO_NUMERICO', 'SIN_DATOS_CAMIONES')]
    evidence = []
    for label, mov, bi, state, source in cases:
        params = {}
        def fixture(values, prefix, integer=False):
            values_sql = []
            for i, value in enumerate(values or [None]):
                key = prefix + str(i)
                params[key] = value
                values_sql.append('(CAST(:' + key + ' AS ' + ('int' if integer else 'nvarchar(100)') + '))')
            return '(VALUES ' + ','.join(values_sql) + ') x(n)' + (' WHERE 1=0' if not values else '')
        prefix = "WITH FixtureMOV AS (SELECT CAST('20260916' AS date) Fecha,'KOM' Flota_CEX,'CH01' Destino,'MINA' Fase,n N_BREAK FROM " + fixture(mov, 'm', True) + '),\n'
        prefix += "FixtureBI AS (SELECT CAST('20260916' AS date) fecha,'CAT' flota_cex_tc,'CH01' destino_descarga,'MINA' fase,n n_break FROM " + fixture(bi, 'p') + '),\n'
        r = rows(c, prefix + body.removeprefix('WITH '), params)[0]
        assert r['Estado_Fuente_POWERBI'] == state, (label, r)
        assert r['Fuente_Camiones'] == source, (label, r)
        assert r['Vueltas_CAT'] == (sum(float(v) for v in bi) if source == 'MOV_CAM_POWERBI' else 0), (label, r)
        assert r['Vueltas_KOM'] == (sum(mov) if source == 'MOV_CAM' else 0), (label, r)
        evidence.append({'caso': label, **r})
    return evidence


def run(mode):
    OUT.mkdir(exist_ok=True, parents=True)
    with _engine_dev().connect() as c:
        _assert_dev_connection(c)
        lock(c)
        before_defs = definitions(c)
        before = regression(c)
        if mode == 'trial':
            assert not (OUT / 'before_definitions.json').exists(), 'No sobrescribir respaldo'
            save('before_definitions.json', before_defs)
            save('before.json', before)
        else:
            assert (OUT / 'trial_OK.json').exists(), 'Falta ensayo reversible aprobado'
            assert same(before_defs, json.loads((OUT / 'before_definitions.json').read_text(encoding='utf-8')))
            assert same(before, json.loads((OUT / 'before.json').read_text(encoding='utf-8'))), 'DEV cambió desde ensayo'
        for filename in OBJECTS.values():
            c.exec_driver_sql((MIG / filename).read_text(encoding='utf-8')).close()
        cases = textual_cases(c)
        after = regression(c)
        assert same(before, after), 'Diferencia histórica: ABORTAR, no persistir'
        save(mode + '_cases.json', cases)
        save(mode + '_after.json', after)
        expected_defs = definitions(c)
        if mode == 'trial':
            c.rollback()
            assert same(definitions(c), before_defs)
            assert same(regression(c), before)
        else:
            c.commit()
    if mode == 'deploy':
        with _engine_dev().connect() as c:
            _assert_dev_connection(c)
            assert same(definitions(c), expected_defs)
            assert same(regression(c), before)
            save('postdeploy_cases.json', textual_cases(c))
            save('deployed_definitions.json', definitions(c))
    save(mode + '_OK.json', {'estado': 'OK', 'commit': mode == 'deploy', 'fechas': 89,
                            'casos': len(cases), 'comparacion_exacta': True})
    with (OUT / (mode + '_comparacion.csv')).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['Fecha', 'Delta_factor', 'Fuente_sin_cambios', 'Vueltas_sin_cambios', 'Produccion_sin_cambios'])
        for r in before['snapshot']['control']:
            w.writerow([r['Fecha'], 0, True, True, True])
    print(mode, 'OK: 17 casos, 89 fechas idénticas; COMMIT=' + str(mode == 'deploy'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['trial', 'deploy'])
    run(parser.parse_args().mode)
