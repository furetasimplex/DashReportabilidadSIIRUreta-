"""Deploy only the SRR view in DEV; compare against the validated standalone."""
import json
import re
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection

ROOT = Path('docs/migrations/srr_cap_prefactor_dev')
SCHEMA = 'inventar_SpcHidr.'
VIEW = 'v_srr_tms_origen_turno_emision_test'


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding='utf-8')


def definition(c, name):
    return c.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'), {'n': SCHEMA + name}).scalar_one()


def rows(c, name, where="Fecha BETWEEN '20260701' AND '20260930'"):
    return [dict(r) for r in c.execute(text('SELECT * FROM ' + SCHEMA + name + ' WHERE ' + where)).mappings()]


def columns(c):
    return [dict(r) for r in c.execute(text('SELECT name,column_id,TYPE_NAME(user_type_id) tipo,max_length,precision,scale FROM sys.columns WHERE object_id=OBJECT_ID(:n) ORDER BY column_id'), {'n': SCHEMA + VIEW}).mappings()]


def historical(c):
    return [dict(r) for r in c.execute(text("EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_test @FechaInicio='20260806', @FechaFin='20260813'")).mappings() if str(r['Fecha'])[:10] in {'2026-08-06','2026-08-09','2026-08-10','2026-08-13'}]


def main():
    with _engine_dev().begin() as c:
        _assert_dev_connection(c)
        rc = c.execute(text("DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource='SIIR_CONTINGENCIA_PI_APILADO', @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=10000; SELECT @r;")).scalar_one()
        assert rc >= 0
        names = [VIEW, 'sp_factor_ajuste_camiones_test', 'sp_mantiene_factor_ajuste_camiones_v2_test', 'v_ajuste_camiones_emision_test']
        defs = {n: definition(c, n) for n in names}
        assert 'reporte_turno_cache_emision_test' in defs[VIEW], 'Already deployed or source changed'
        for n, d in defs.items():
            path = ROOT / (n + '.exact.sql')
            if path.exists():
                assert path.read_bytes() == d.encode('utf-8'), 'Backup no longer matches DEV'
            else:
                path.write_bytes(d.encode('utf-8'))
        for n in names[1:3]:
            source = re.sub(r'/\*.*?\*/|--[^\n]*', '', defs[n], flags=re.S)
            assert 'Ton_SRR_Usado_Actual' in source
            assert 'reporte_turno_cache_emision_test' not in source
            assert not re.search(r'Apilado_TMS_Real\s*\*', source, re.I)
        rollback = re.sub(r'\bCREATE\s+(?:OR\s+ALTER\s+)?VIEW\b', 'ALTER VIEW', defs[VIEW], count=1, flags=re.I)
        (ROOT / '02_rollback.sql').write_bytes(rollback.encode('utf-8'))
        old_cols = columns(c)
        before = rows(c, VIEW)
        baseline = historical(c)
        save('controles_agosto_antes.json', baseline)
        save('srr_julio_septiembre_antes.json', before)
        c.exec_driver_sql((ROOT / '01_alter_vista.sql').read_text(encoding='utf-8'))
        assert columns(c)[:15] == old_cols, 'Legacy columns changed'
        after = rows(c, VIEW)
        standalone = rows(c, 'v_srr_tms_origen_turno_standalone_test')
        key = lambda r: (str(r['Fecha']), r['Turno'])
        expected = {key(r): r for r in standalone}
        mismatches = [{'key': key(r), 'diff': {k: [v, expected.get(key(r), {}).get(k)] for k, v in r.items()
                       if v != expected.get(key(r), {}).get(k)}} for r in after if r != expected.get(key(r))]
        save('standalone_differences.json', mismatches)
        # FLOAT SUM in IMP can round the last decimal(38,10) digit differently
        # between equivalent query plans; keep all operational outputs exact.
        assert all(k in {'Ton_IMP_Total', 'Ton_SRR_IMP'} and abs(a-b) <= Decimal('0.0000000001')
                   for row in mismatches for k, (a, b) in row['diff'].items()), str(mismatches[:3])
        assert len(after) == len(standalone)
        index = {key(r): r for r in before}
        differences = []
        for r in after:
            old = index.get(key(r))
            if old is None or any(old[k] != r[k] for k in ('Ton_SRR_Usado_Actual', 'Flag_SRR_Capeado_Por_Apilado', 'Fuente_SRR')):
                differences.append({'fecha_turno': key(r), 'antes': old, 'despues': r})
        controls = historical(c)
        assert baseline == controls, 'Historical controls changed'
        for n in names[1:]:
            assert definition(c, n) == defs[n], 'Protected object changed'
        save('controles_agosto_despues.json', controls)
        save('impacto_srr.json', differences)
        save('srr_julio_septiembre_despues.json', after)
        save('deploy_checks.json', {'standalone_equal': True, 'legacy_columns_equal': True,
                                   'historical_controls_equal': True, 'changed_rows': len(differences)})
        print('DEPLOY_VALIDATED changed_rows=', len(differences), flush=True)
    print('COMMIT_VIEW_ONLY', flush=True)


if __name__ == '__main__':
    main()
