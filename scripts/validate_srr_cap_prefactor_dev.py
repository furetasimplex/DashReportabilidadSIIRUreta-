"""Real DEV pipeline and Excel checks; all test data are rolled back."""
import hashlib
import io
from contextlib import contextmanager
from datetime import date
from unittest.mock import patch

import pandas as pd
from openpyxl import load_workbook
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
from report_export import report_export as repo
from scripts.deploy_srr_cap_prefactor_dev import ROOT, SCHEMA, VIEW, rows, save, definition

DAY = date(2026, 9, 16)
PROTECTED = ['Control_Factor_Ajuste_Camiones_v2_test', 'reporte_turno_cache_emision_test',
             'Datos_conciliados_of', 'factor_camiones_override_aplicacion_test',
             'factor_camiones_parametro_vigencia_test']


def snapshots(c):
    return {n: hashlib.sha256(repr(sorted(repr(tuple(r)) for r in c.execute(text('SELECT * FROM ' + SCHEMA + n)))).encode()).hexdigest()
            for n in PROTECTED}


def state(c):
    srr = sorted(rows(c, VIEW, "Fecha='20260916'"), key=lambda r: r['Turno'])
    factor = rows(c, 'v_ajuste_camiones_emision_test', "Fecha='20260916'")[0]
    cache = sorted(rows(c, 'reporte_turno_cache_emision_test', "Fecha='20260916'"), key=lambda r: r['Turno'])
    fields = ['Factor_Ajuste_Calculado', 'Factor_Aplicacion_Reportes', 'Factor_Aplicacion_Automatica',
              'SRR_TMS_Turno_A', 'SRR_TMS_Turno_B', 'SRR_TMS_Dia', 'Modo_Aplicacion',
              'Flag_Override_1', 'Id_Control_Aplicacion', 'Limite_KOM_TMH_Viaje', 'Limite_CAT_TMH_Viaje']
    result = {'factor': {k: factor[k] for k in fields}, 'srr': srr,
              'cache': [{k: r[k] for k in ('Fecha', 'Turno', 'Apilado_TMS_Real', 'SRR')} for r in cache]}
    assert abs(factor['Factor_Ajuste_Calculado'] - 0.21963019549669) < 1e-9
    assert factor['Factor_Aplicacion_Reportes'] == factor['Factor_Aplicacion_Automatica']
    assert factor['Modo_Aplicacion'] == 'AUTOMATICO' and not factor['Flag_Override_1']
    assert factor['Id_Control_Aplicacion'] == 7
    assert factor['Limite_KOM_TMH_Viaje'] == 380 and factor['Limite_CAT_TMH_Viaje'] == 265
    a = srr[0]
    assert a['Turno'] == 'A' and a['Estado_SRR'] == 'OK' and not a['Flag_SRR_Capeado_Por_Apilado']
    assert abs(float(a['Ton_SRR_Usado_Actual']) - 489.214821763) < 1e-9
    assert abs(float(cache[0]['Apilado_TMS_Real']) - 465.364996) < 1e-6
    assert cache[0]['SRR'] == 100
    return result


def export(package, start, end, name):
    output = io.BytesIO()
    repo.export_reporte_turno_estilo_leyes_finos(
        package['df_turno'], output, periodo_inicio=start, periodo_fin=end,
        **{k: v for k, v in package.items() if k.startswith('df_') and k != 'df_turno'})
    wb = load_workbook(io.BytesIO(output.getvalue()), data_only=True)
    assert len(wb.sheetnames) == 7 and 'Reconst Mod SRR' in wb.sheetnames
    ws = wb['Reconst Mod SRR']
    excelrow = next(n for n in range(9, ws.max_row + 1) if ws.cell(n, 3).value is not None
                    and pd.Timestamp(ws.cell(n, 3).value).date() == DAY)
    reconst = [ws.cell(excelrow, n).value for n in range(4, 10)]
    (ROOT / name).write_bytes(output.getvalue())
    return {'bytes': len(output.getvalue()), 'sheets': wb.sheetnames, 'reconst_16': reconst}


def main():
    with _engine_dev().connect() as c:
        _assert_dev_connection(c)
        # SQL dependency metadata confirms the new direct source set.
        deps = [dict(r) for r in c.execute(text('SELECT referenced_database_name,referenced_schema_name,referenced_entity_name FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:n)'), {'n': SCHEMA + VIEW}).mappings()]
        save('dependencias_finales.json', deps)
        assert {d['referenced_entity_name'] for d in deps} == {
            'v_apilado_tms_sin_sal_con_srr_reporte_test', 'v_imp_chancado_normalizado',
            'v_apilado_base_mina_stock_srr', 'v_conciliacion_chancado_v2'}
        before = snapshots(c)
        c.rollback()
        try:
            repo._adquirir_lock_refresco_turno(c)
            c.execute(text("DELETE FROM inventar_SpcHidr.reporte_turno_cache_emision_test WHERE Fecha='20260916'"))
            first = rows(c, VIEW, "Fecha='20260916'")
            assert len(first) == 2 and {r['Turno'] for r in first} == {'A', 'B'}
            assert float(next(r for r in first if r['Turno'] == 'A')['Ton_SRR_Usado_Actual']) == 489.214821763
            save('first_run_sin_cache.json', first)
            print('PASS_FIRST_RUN_SIN_CACHE', flush=True)
            cycles = []
            for i in range(3):
                repo.refrescar_dependencias_reporte_turno_emision(DAY, DAY, conn=c)
                cycles.append(state(c))
                print('CYCLE', i + 1, cycles[-1]['factor'], cycles[-1]['cache'], flush=True)
            save('estabilidad_3x.json', cycles)
            assert cycles[0] == cycles[1] == cycles[2], 'Cycle drift'
            print('PASS_ESTABILIDAD_3X_EXACTA', flush=True)

            class ReversibleEngine:
                @contextmanager
                def begin(self):
                    yield c

            with patch.object(repo, '_get_engine', return_value=ReversibleEngine()):
                daily = repo.preparar_paquete_reporte_turno_emision(DAY, DAY, salida='excel')
                daily_state = state(c)
                daily_file = export(daily, DAY, DAY, 'RTO_20260916_validado.xlsx')
                print('PASS_EXCEL_DIARIO', daily_file, flush=True)
                monthly = repo.preparar_paquete_reporte_turno_emision(date(2026, 9, 1), date(2026, 9, 30), salida='excel')
                monthly_state = state(c)
                monthly_file = export(monthly, date(2026, 9, 1), date(2026, 9, 30), 'RTO_20260901_20260930_validado.xlsx')
            assert daily_state == monthly_state
            compared = {}
            for key in ('df_turno', 'df_generador', 'df_reconst_srr'):
                def day_frame(p):
                    frame = p[key].loc[pd.to_datetime(p[key].Fecha).dt.date.eq(DAY)].copy()
                    frame = frame.drop(columns=['Fecha_Calculo', 'Fecha_Actualizacion'], errors='ignore')
                    return frame.sort_values('Turno' if 'Turno' in frame else 'Fecha').reset_index(drop=True)
                a, b = day_frame(daily), day_frame(monthly)
                pd.testing.assert_frame_equal(a, b, check_exact=True, check_dtype=False)
                compared[key] = a.to_dict('records')
            save('dia_vs_mes_16.json', compared)
            assert daily_file['reconst_16'] == monthly_file['reconst_16']
            save('excel_checks.json', {'diario': daily_file, 'mensual': monthly_file, 'day_month_exact': True})
            print('PASS_DIA_VS_MES_EXACTO', flush=True)
        finally:
            c.rollback()
            after = snapshots(c)
            save('rollback_datos.json', {'before': before, 'after': after, 'equal': before == after})
            assert before == after, 'Data restoration failed'
            for n in ['sp_factor_ajuste_camiones_test', 'sp_mantiene_factor_ajuste_camiones_v2_test', 'v_ajuste_camiones_emision_test']:
                assert definition(c, n).encode('utf-8') == (ROOT / (n + '.exact.sql')).read_bytes()
            print('PASS_ROLLBACK_DATOS_Y_SP_2A_2B_INTACTOS', flush=True)
            c.rollback()


if __name__ == '__main__':
    main()
