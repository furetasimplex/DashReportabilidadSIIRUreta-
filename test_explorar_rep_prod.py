#!/usr/bin/env python3
"""
test_explorar_rep_prod.py
===========================
Rastrea la familia rep_prod_* (ajustado_stg, reglas, targets, ajuste_log,
validacion_log) y reglas_negocio_reporte: quien las escribe/lee, columnas,
y muestra de datos.

Ejecutar: .venv/bin/python test_explorar_rep_prod.py
"""
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_colwidth', 120)
pd.set_option('display.width', 220)
pd.set_option('display.max_columns', None)

engine = get_engine()

def q(sql, label):
    print(f"\n{'='*100}\n{label}\n{'='*100}")
    try:
        df = pd.read_sql(sql, engine)
        print(df.to_string() if not df.empty else "(sin resultados)")
        return df
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return pd.DataFrame()

def dump_sp(schema, name):
    print(f"\n{'='*100}\nDefinicion de [{schema}].[{name}]\n{'='*100}")
    try:
        with engine.connect() as conn:
            rows = conn.exec_driver_sql(f"EXEC sp_helptext '{schema}.{name}'").fetchall()
            if not rows:
                print("(sin texto -- encriptado o no accesible)")
            else:
                print("".join(r[0] for r in rows if r[0] is not None))
    except Exception as e:
        print(f"✗ ERROR: {e}")

tablas = ['rep_prod_ajustado_stg', 'rep_prod_reglas', 'rep_prod_targets',
          'rep_prod_ajuste_log', 'rep_prod_validacion_log', 'reglas_negocio_reporte']

# 1) Quien ESCRIBE/LEE cada tabla de la familia rep_prod_*
for t in tablas:
    q(
        f"SELECT o.name AS objeto, o.type_desc AS tipo, OBJECT_SCHEMA_NAME(o.object_id) AS esquema "
        f"FROM sys.sql_expression_dependencies d JOIN sys.objects o ON d.referencing_id = o.object_id "
        f"WHERE d.referenced_entity_name = '{t}' AND o.type IN ('V','P') "
        f"ORDER BY o.type_desc, o.name",
        f"Objetos que referencian {t}"
    )

# 2) Columnas de cada tabla
for t in tablas:
    q(
        f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        f"WHERE TABLE_NAME='{t}' ORDER BY ORDINAL_POSITION",
        f"Columnas de {t}"
    )

# 3) Muestra de rep_prod_reglas y reglas_negocio_reporte (deberian ser tablas de configuracion, chicas)
q(f"SELECT TOP 50 * FROM [inventar_SpcHidr].[rep_prod_reglas]", "Contenido rep_prod_reglas")
q(f"SELECT TOP 50 * FROM [inventar_SpcHidr].[reglas_negocio_reporte]", "Contenido reglas_negocio_reporte")
q(f"SELECT TOP 10 * FROM [inventar_SpcHidr].[rep_prod_targets]", "Muestra rep_prod_targets")
q(f"SELECT TOP 5 * FROM [inventar_SpcHidr].[rep_prod_ajustado_stg] ORDER BY 1 DESC", "Muestra rep_prod_ajustado_stg (mas reciente)")

print("\n" + "=" * 100)
print("Copia y pega TODA esta salida.")
