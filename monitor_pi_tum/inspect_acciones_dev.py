"""Captura de contratos SQL vigentes, solo lectura DEV."""
import json
from pathlib import Path
from sqlalchemy import text
from .db import _engine_dev

OBJETOS = ('contingencia_pi_accion_test', 'sp_registrar_contingencia_pi_test',
           'v_contingencia_pi_estado_turno_test', 'v_contingencia_totalizador_resuelto_operacional_test',
           'sp_mantiene_apilado_tmh_v2_test', 'Control_Apilado_TMH_v2_test',
           'v_contingencia_totalizador_resuelto_turno')


def main():
    root = Path(__file__).parent / 'validacion/acciones_actual'
    root.mkdir(parents=True, exist_ok=True)
    with _engine_dev().connect() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar() == 'inventar_SpcHidr'
        for name in OBJETOS:
            fqn = 'inventar_SpcHidr.' + name
            definition = conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'), {'n':fqn}).scalar()
            if definition:
                path = root / (name + '.sql')
                if not path.exists():
                    path.write_text(definition, encoding='utf-8')
            cols = conn.execute(text('''SELECT name, TYPE_NAME(user_type_id) AS tipo, max_length,
                is_nullable FROM sys.columns WHERE object_id=OBJECT_ID(:n) ORDER BY column_id'''), {'n':fqn}).mappings().all()
            params = conn.execute(text('''SELECT name, TYPE_NAME(user_type_id) AS tipo, max_length
                FROM sys.parameters WHERE object_id=OBJECT_ID(:n) ORDER BY parameter_id'''), {'n':fqn}).mappings().all()
            print(name, 'columnas=', [dict(r) for r in cols], 'parametros=', [dict(r) for r in params])
        print('ACCIONES:', conn.execute(text('''SELECT TOP (10) id,fecha_operacional,turno,accion,motivo,
            fecha_registro FROM inventar_SpcHidr.contingencia_pi_accion_test
            ORDER BY fecha_registro DESC,id DESC''')).mappings().all())


if __name__ == '__main__':
    main()
