from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest
from openpyxl import Workbook

from report_export import report_export as repo
from report_export import export_to_excel as excel
from report_export.tests.test_datos_conciliados_excel import _datos_factor_ajuste


def balance():
    base = dict(Humedad=3.3, Material='SULFUROS', Sal_TMH_Dia=0., SRR_TMS_Dia=0.,
                Factor_Ajuste=1., Mineral_Apilado_TMH_Original=0.,
                Mineral_Apilado_TMH_Ajustado=0., Delta_Ajuste_TMH=0.,
                Apilado_TMS_Reporte=0., Diferencia_vs_Datos_Conciliados=0.,
                Modo_Aplicacion='AUTOMATICO', Regla_Aplicacion='FALLBACK_SIN_DATOS_CAMIONES')
    for name in ('Nivel_Promedio_Chancado', 'Nivel_Promedio_Harneros', 'Nivel_Promedio_Silo',
                 'Bin_Chancado', 'Bin_Harneros', 'Tolva_Compensacion', 'Silo',
                 'Inventario_Chancado_TMH', 'Inventario_Silo_TMH', 'Total_TMH',
                 'Inventario_Chancado_TMS', 'Inventario_Silo_TMS', 'Total_TMS'):
        base[name] = None
    for group, letters in [('Harnero', 'ABCDE'), ('Chancado', 'ABCDE'), ('Silo', 'AB')]:
        base.update({f'Nivel_{group}_{letter}': None for letter in letters})
    first = dict(base, Fecha=pd.Timestamp('2026-09-02'), Total_TMS=6023.7382281485225,
                 Inventario_Chancado_TMS_Anterior=6006.94727751255,
                 Delta_Inventario_Chancado_TMS=16.790950635972877,
                 Chancado_TMS_Reporte=16.790950635972877, Chancado_TMS_Real=16.790950635972877)
    second = dict(base, Fecha=pd.Timestamp('2026-09-16'),
                  Mineral_Apilado_TMH_Original=2466., Mineral_Apilado_TMH_Ajustado=2466.,
                  Apilado_TMS_Reporte=2326.252, Sal_TMH_Dia=58.37, SRR_TMS_Dia=489.214821763,
                  Delta_Inventario_Chancado_TMS=-163.95211282058517,
                  Chancado_TMS_Reporte=1673.0850654164149, Chancado_TMS_Real=1673.0850654164149,
                  Modo_Aplicacion='FORZADO_1', Regla_Aplicacion='FORZADO_1_USUARIO')
    return pd.DataFrame([first, second])


def test_residual_inventario_y_forzado_conservan_valores_en_excel():
    df = balance()
    excel._validar_balance_chancado(df)
    wb = Workbook()
    excel._agregar_hoja_balance_chancado(wb, df)
    ws = wb['Balance Chancado']
    assert ws['K6'].value == pytest.approx(16.790950635972877)
    assert ws['E6'].value == 0
    assert ws['D7'].value == 1 and ws['E7'].value == 2466 and ws['F7'].value == 0
    assert ws['K7'].value == pytest.approx(1673.0850654164149)
    assert ws['L7'].value == 'FORZADO_1'
    assert ws.max_column == 38
    assert ws['J5'].value == 'SRR TMS Balance'


@pytest.mark.parametrize('campo,valor', [
    ('Mineral_Apilado_TMH_Ajustado', 541.6080620948381),
    ('Delta_Ajuste_TMH', -1924.3919379051617),
    ('Chancado_TMS_Reporte', 1614.7150654164149),  # sal descontada dos veces
    ('Chancado_TMS_Real', 1673.0850754164149),
    ('SRR_TMS_Dia', 500),
])
def test_fail_fast_con_fecha_valores_y_diferencia(campo, valor):
    df = balance()
    df.loc[1, campo] = valor
    with pytest.raises(ValueError, match=r'16-09-2026: .*esperado=.*obtenido=.*diferencia='):
        excel._validar_balance_chancado(df)


def test_nulos_no_se_imputan_y_srr_publicado_no_alimenta_balance():
    df = balance()
    df['SRR_TMS_promedio_dia'] = -9999  # no participa de ninguna ecuación
    excel._validar_balance_chancado(df)
    df.loc[0, ['Chancado_TMS_Reporte', 'Chancado_TMS_Real']] = None
    excel._validar_balance_chancado(df)
    wb = Workbook()
    excel._agregar_hoja_balance_chancado(wb, df)
    assert wb['Balance Chancado']['K6'].value is None


def test_factor_diagnostico_no_se_sobrescribe_por_override():
    df = _datos_factor_ajuste().iloc[:2].copy()
    df['Fecha'] = pd.to_datetime(['2026-09-02', '2026-09-16'])
    df.loc[0, ['Factor_Ajuste_Calculado', 'Apilado_TMH_Bruto_Ajustado']] = None
    df.loc[1, 'Factor_Ajuste_Calculado'] = 0.21963019549669024
    df.loc[1, 'Factor_Aplicacion_Automatica'] = 0.21963019549669024
    df.loc[1, 'Apilado_TMH_Bruto_Ajustado'] = 541.6080620948381
    df.loc[1, 'Chancado_TMS_Con_Ajuste'] = -187.80193853787665
    df.loc[1, 'Modo_Aplicacion'] = 'FORZADO_1'
    excel._validar_factor_ajuste_camiones(df[['Fecha']], df)
    wb = Workbook()
    excel._agregar_hoja_factor_ajuste_camiones(wb, df)
    ws = wb['Factor ajuste camiones']
    assert ws['D3'].value is None and ws['G3'].value == 1
    assert ws['D4'].value == pytest.approx(0.21963019549669024)
    assert ws['E4'].value == pytest.approx(541.6080620948381)
    assert ws['F4'].value == pytest.approx(-187.80193853787665)
    assert ws['G4'].value == 1


def test_select_balance_no_mezcla_automatico_o_srr_reconstruido():
    with patch.object(repo.pd, 'read_sql', return_value=pd.DataFrame(columns=['Fecha'])) as read:
        repo.fetch_balance_chancado_report(date(2026, 9, 2), date(2026, 9, 16), conn=object())
    sql = str(read.call_args.args[0])
    assert 'aj.Apilado_TMH_Bruto_Ajustado' not in sql
    assert 'SRR_TMS_promedio_dia' not in sql
    assert 'aj.Apilado_TMH_Reporte + aj.Sal_TMH_Dia' in sql
    assert 'aj.Diferencia_Apilado_TMH_Ajuste' in sql
    assert 'Apilado_TMS_Reporte + Delta_Inventario_Chancado_TMS - SRR_TMS_Dia' in sql
