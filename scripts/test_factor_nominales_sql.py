"""Protege las partes de balance/override que esta migración no debe cambiar."""
import unittest
from scripts.factor_camiones_nominales_dev import BACKUP,MIGRATION,build_calculation


class ScopeTests(unittest.TestCase):
    def test_base_srr_inventario_apilado_no_cambia(self):
        for name in ('sp_factor_ajuste_camiones_test','sp_factor_ajuste_camiones_standalone_test'):
            before=(BACKUP/(name+'.sql')).read_text(encoding='utf-8')
            after=build_calculation(name)
            begin='    ;WITH SRR_Diario AS'
            end='        ON #BaseBalance(Fecha);'
            self.assertEqual(before.split(begin)[1].split(end)[0],after.split(begin)[1].split(end)[0])

    def test_vista_solo_agrega_columnas_no_reescribe_override(self):
        from scripts.factor_camiones_nominales_dev import EXTRA_COLUMNS,alter_definition
        before=alter_definition((BACKUP/'v_ajuste_camiones_emision_test.sql').read_text(encoding='utf-8'))
        after=(MIGRATION/'10_v_ajuste_camiones_emision_test.sql').read_text(encoding='utf-8')
        for column in EXTRA_COLUMNS:
            after=after.replace('        f.'+column+',\n','',1)
        self.assertEqual(before,after)

    def test_formula_no_consume_tonelaje_externo_ni_nominal_literal(self):
        for name in ('sp_factor_ajuste_camiones_test','sp_factor_ajuste_camiones_standalone_test'):
            sql=build_calculation(name)
            for forbidden in ('ton_descarga','Tonelaje_Hum_CIO','357','236','380','265'):
                self.assertNotIn(forbidden,sql)


if __name__=='__main__':unittest.main()
