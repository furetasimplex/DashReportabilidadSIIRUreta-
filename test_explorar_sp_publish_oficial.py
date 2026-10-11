#!/usr/bin/env python3
"""
test_explorar_sp_publish_oficial.py
=====================================
Vuelca la definicion de los objetos que escriben/leen Datos_conciliados_of_ver:
sp_rep_publish_oficial_validado, sp_DatosConciliados_SetActiveRun,
sp_DatosConciliados_ClearActiveRun, vw_Datos_conciliados_of_activo,
vw_datos_conciliados_reporte. Estan en inventar_SpcHidr, que es la BD
default del engine (no requiere cross-db).

Ejecutar: .venv/bin/python test_explorar_sp_publish_oficial.py
"""
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 220)

engine = get_engine()

def dump_obj(schema, name):
    print(f"\n{'='*100}\nDefinicion de [{schema}].[{name}]\n{'='*100}")
    try:
        with engine.connect() as conn:
            rows = conn.exec_driver_sql(f"EXEC sp_helptext '{schema}.{name}'").fetchall()
            if not rows:
                print("(sin texto -- encriptado o no accesible)")
            else:
                texto = "".join(r[0] for r in rows if r[0] is not None)
                print(texto)
    except Exception as e:
        print(f"✗ ERROR: {e}")

objetos = [
    ('inventar_SpcHidr', 'sp_rep_publish_oficial_validado'),
    ('inventar_SpcHidr', 'sp_DatosConciliados_SetActiveRun'),
    ('inventar_SpcHidr', 'sp_DatosConciliados_ClearActiveRun'),
    ('inventar_SpcHidr', 'vw_Datos_conciliados_of_activo'),
    ('inventar_SpcHidr', 'vw_datos_conciliados_reporte'),
]
for schema, name in objetos:
    dump_obj(schema, name)

print("\n" + "=" * 100)
print("Copia y pega TODA esta salida.")
