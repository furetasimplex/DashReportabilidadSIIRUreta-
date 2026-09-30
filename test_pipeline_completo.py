#!/usr/bin/env python3
"""
test_pipeline_completo.py
============================
Ultima pieza antes de programar el motor de reglas en Python:
- Definiciones de sp_rep_get_periodo_caso, sp_rep_log_start, sp_rep_log_end,
  sp_rep_prod_sync_schema
- Columnas completas de Data_balance_rec (input del solver por caso+flujo)
- Columnas completas de rep_prod_ajustado_stg / rep_prod_ajustado (output)
- Columnas completas de Datos_conciliados_of (medido/plan diario, sin caso_id)
- Muestra de Data_balance_rec para un caso real (caso_id=70, que ya vimos en
  rep_prod_targets)

Escribe a pipeline_completo.txt

Ejecutar: .venv/bin/python test_pipeline_completo.py
"""
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_colwidth', 200)
pd.set_option('display.width', 250)
pd.set_option('display.max_columns', None)

engine = get_engine()
out_lines = []

def w(s=""):
    print(s)
    out_lines.append(str(s))

sps = ['sp_rep_get_periodo_caso', 'sp_rep_log_start', 'sp_rep_log_end', 'sp_rep_prod_sync_schema']

with engine.connect() as conn:
    q = """
    SELECT s.name AS schema_name, o.name AS sp_name
    FROM sys.procedures o
    JOIN sys.schemas s ON o.schema_id = s.schema_id
    WHERE o.name IN ({})
    """.format(",".join(f"'{sp}'" for sp in sps))
    df_schemas = pd.read_sql(q, conn)
    w("=" * 100)
    w("Definiciones de SPs de apoyo (periodo, log_start, log_end, sync_schema)")
    w("=" * 100)
    for _, row in df_schemas.iterrows():
        fq_name = f"{row['schema_name']}.{row['sp_name']}"
        w(f"\n>>> {fq_name} <<<")
        try:
            result = conn.exec_driver_sql(f"EXEC sp_helptext '{fq_name}'")
            rows = result.fetchall()
            texto = "\n".join(
                r[0].rstrip()
                for r in rows
                if r[0] is not None
            )
            w(texto if texto else "(vacio)")
        except Exception as e:
            w(f"ERROR: {e}")

for tabla in ['Data_balance_rec', 'rep_prod_ajustado_stg', 'rep_prod_ajustado', 'Datos_conciliados_of']:
    w(f"\n{'='*100}\nColumnas de {tabla}\n{'='*100}")
    try:
        q = f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{tabla}'
        ORDER BY ORDINAL_POSITION
        """
        df = pd.read_sql(q, engine)
        w(df.to_string(index=False))
    except Exception as e:
        w(f"ERROR: {e}")

w(f"\n{'='*100}\nMuestra Data_balance_rec para caso_id=70\n{'='*100}")
try:
    df = pd.read_sql("SELECT * FROM Data_balance_rec WHERE caso_id = 70 ORDER BY Flujo", engine)
    w(df.to_string(index=False))
except Exception as e:
    w(f"ERROR: {e}")

w(f"\n{'='*100}\nrep_prod_ajustado: filas existentes para caso_id=70 (TOP 5 mas recientes)\n{'='*100}")
try:
    df = pd.read_sql("SELECT TOP 5 * FROM rep_prod_ajustado WHERE caso_id = 70 ORDER BY Fecha DESC", engine)
    w(df.to_string(index=False))
except Exception as e:
    w(f"ERROR: {e}")

with open('pipeline_completo.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(out_lines))

print("\n\n>>> Guardado en pipeline_completo.txt <<<")
