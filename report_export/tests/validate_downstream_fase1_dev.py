"""Validación manual autorizada: refresca 04–10 septiembre SOLO en DEV.

Ejecutar como módulo. Usa el coordinador real y sus transacciones vigentes.
Guarda antes/después y ejecuta el directo con trazabilidad temporal.
"""
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import re

from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
from monitor_pi_tum.validacion.downstream.comparar import body, run
from report_export import report_export as repo

OUT = Path('auditorias/archivo/report_export/exports/validacion_downstream_fase1')
TABLES = ('Control_Apilado_TMH_v2_test', 'Historico_Apilado_Diario',
          'Control_Factor_Ajuste_Camiones_v2_test', 'v_ajuste_camiones_emision_test',
          'reporte_turno_cache_emision_test', 'v_srr_tms_origen_turno_emision_test')


def save(name, value):
    (OUT / (name + '.json')).write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding='utf-8')


class GuardedEngine:
    def __init__(self, engine):
        self.engine = engine

    @contextmanager
    def connect(self):
        with self.engine.connect() as conn:
            _assert_dev_connection(conn)
            yield conn

    @contextmanager
    def begin(self):
        with self.engine.begin() as conn:
            _assert_dev_connection(conn)
            yield conn


def snapshot(engine):
    with engine.connect() as conn:
        result = {n: [dict(r) for r in conn.execute(text(
            'SELECT * FROM inventar_SpcHidr.' + n + " WHERE Fecha BETWEEN '20260904' AND '20260910'"
        )).mappings()] for n in TABLES}
        mods = [dict(r) for r in conn.execute(text(
            'SELECT object_id, definition FROM sys.sql_modules ORDER BY object_id')).mappings()]
        result['sql_definitions_sha256'] = hashlib.sha256(json.dumps(mods, default=str).encode()).hexdigest()
        original = conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_reporte_turno_emision_test'))")).scalar_one()
        report = re.sub(r'\[?inventar_SpcHidr\]?\s*\.\s*\[?trazabilidad_analitos_tm_emision_test\]?',
                        '#traza', body(original), flags=re.I)
        assert '#traza' in report
        direct = "DECLARE @fecha_inicio date='20260904',@fecha_fin date='20260911';\n" + report
        (OUT / 'directo_trazabilidad_temporal.sql').write_text(direct, encoding='utf-8')
        run(conn, 'SELECT TOP (0) * INTO #traza FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test;')
        result['directo'] = run(conn, direct)
        return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # No sobrescribir el baseline de una ejecución anterior.
    if (OUT / 'antes.json').exists():
        raise RuntimeError('Ya existe antes.json; conservar la evidencia antes de otra ejecución.')
    engine = GuardedEngine(_engine_dev())
    before = snapshot(engine)
    save('antes', before)
    print('Baseline DEV guardado; iniciando coordinador real 04-10.', flush=True)
    with patch.object(repo, '_get_engine', return_value=engine):
        result = repo.refrescar_dependencias_reporte_turno_emision(date(2026, 9, 4), date(2026, 9, 10))
    save('coordinador', result)
    after = snapshot(engine)
    save('despues', after)
    checks = {'definiciones_sql_sin_cambios': before['sql_definitions_sha256'] == after['sql_definitions_sha256']}
    idx = lambda rows: {(str(r['Fecha'])[:10], str(r.get('Turno', '')).strip()): r for r in rows}
    controls = idx(after[TABLES[0]])
    histories = idx(after[TABLES[1]])
    oldf, newf = idx(before[TABLES[2]]), idx(after[TABLES[2]])
    cache, direct = idx(after[TABLES[4]]), idx(after['directo'])
    oldcache, olddirect = idx(before[TABLES[4]]), idx(before['directo'])
    checks['14_turnos_directo_cache'] = len(cache) == len(direct) == 14 and cache.keys() == direct.keys()
    rows = []
    for (d, t), c in sorted(cache.items()):
        key = (d, '')
        co, h, f, prev = controls[key], histories[key], newf[key], oldf[key]
        delta = float(direct[(d, t)]['Apilado_TMS_Real']) - float(c['Apilado_TMS_Real'])
        repairs = abs(float(oldcache[(d,t)]['Apilado_TMS_Real']) - float(olddirect[(d,t)]['Apilado_TMS_Real'])) > 1e-6
        changed = abs(float(f['Factor_Ajuste']) - float(prev['Factor_Ajuste'])) > 1e-12
        classification = ('nuevo factor' if changed else 'factor sin cambio') + (' + reparación cache stale' if repairs else ' + cache previo coherente con factor anterior')
        rows.append([d, t, co['TMH_Apilado_Total_'+t], h['TMH_Bruto_'+t], h['Fecha_Calculo'],
                     prev['Factor_Ajuste'], f['Factor_Ajuste'], f['Estado_Calculo'],
                     direct[(d,t)]['Apilado_TMS_Real'], c['Apilado_TMS_Real'], c['Fecha_Actualizacion'], delta, classification])
        checks[d+'_'+t+'_directo_cache'] = abs(delta) < 1e-6
        checks[d+'_'+t+'_historico_control'] = abs(float(co['TMH_Apilado_Total_'+t]) - float(h['TMH_Bruto_'+t])) < 1e-6
        checks[d+'_factor_historico'] = abs(float(f['Apilado_TMH_Bruto_Original']) - float(h['TMH_Bruto_Dia'])) < 1e-6
    f10 = newf[('2026-09-10','')]
    checks['factor_10'] = abs(float(f10['Factor_Ajuste']) - 0.9983502509529375) < 1e-10
    checks['estado_10'] = f10['Estado_Calculo'] == 'OK_AJUSTE_KOM'
    applied = idx(after[TABLES[3]])[('2026-09-10','')]['Factor_Aplicacion_Reportes']
    checks['factor_realmente_aplicado_10'] = abs(float(applied) - 0.9983502509529375) < 1e-10
    for turno, expected in [('A',39408.079368), ('B',40089.655081)]:
        checks['tms_10_'+turno] = abs(float(cache[('2026-09-10',turno)]['Apilado_TMS_Real']) - expected) < 1e-6
    save('checks', checks)
    headers = ['Fecha','Turno','TMH Control','TMH Histórico','Cálculo Histórico','Factor anterior','Factor nuevo','Estado','TMS directo','TMS cache','Actualización cache','Directo−cache','Clasificación']
    table = '|'+ '|'.join(headers)+'|\n|'+'|'.join(['---']*len(headers))+'|\n'
    table += '\n'.join('|'+ '|'.join(map(str,r))+'|' for r in rows)
    (OUT/'COMPARACION.md').write_text('# Validación DEV persistida 04–10 septiembre\n\n'+table+'\n\nChecks: '+str(sum(checks.values()))+'/'+str(len(checks))+'\n',encoding='utf-8')
    print(json.dumps(checks, indent=2), flush=True)
    assert all(checks.values()), 'Revisar checks.json; no se revierte automáticamente el refresco autorizado.'


if __name__ == '__main__':
    main()
