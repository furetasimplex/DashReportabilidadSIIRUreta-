#!/usr/bin/env python3
"""
test_definiciones_pipeline.py
================================
Trae las definiciones COMPLETAS de los SPs reales del pipeline de ajuste,
calificando correctamente schema.objeto (el schema tiene el mismo nombre
que la BD: inventar_SpcHidr.inventar_SpcHidr.sp_...).

Escribe a definiciones_pipeline.txt.

Ejecutar: .venv/bin/python test_definiciones_pipeline.py
"""
from db_connection import get_engine
import pandas as pd

engine = get_engine()
out_lines = []

def w(s=""):
    print(s)
    out_lines.append(str(s))

sps = [
    'sp_rep_build_targets_caso',
    'sp_rep_conductor_pre_ajuste',
    'sp_rep_merge_ajustado',
    'sp_rep_merge_ajustado_dyn',
    'sp_rep_conductor_post_ajuste',
]

with engine.connect() as conn:
    # Primero: encontrar el schema real de cada uno via sys.procedures + sys.schemas
    q = """
    SELECT s.name AS schema_name, o.name AS sp_name
    FROM sys.procedures o
    JOIN sys.schemas s ON o.schema_id = s.schema_id
    WHERE o.name IN ({})
    """.format(",".join(f"'{sp}'" for sp in sps))
    df_schemas = pd.read_sql(q, conn)
    w("=" * 100)
    w("Schemas reales de cada SP")
    w("=" * 100)
    w(df_schemas.to_string(index=False))

    w("\n" + "=" * 100)
    w("Definiciones completas (via sp_helptext, calificado por schema real)")
    w("=" * 100)
    for _, row in df_schemas.iterrows():
        schema_name = row['schema_name']
        sp_name = row['sp_name']
        fq_name = f"{schema_name}.{sp_name}"
        w(f"\n{'='*100}\n>>> {fq_name} <<<\n{'='*100}")
        try:
            result = conn.exec_driver_sql(f"EXEC sp_helptext '{fq_name}'")
            rows = result.fetchall()
            texto = "\n".join(r[0] for r in rows if r[0] is not None)
            w(texto if texto else "(vacio / posiblemente encriptado)")
        except Exception as e:
            w(f"ERROR: {e}")

with open('definiciones_pipeline.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(out_lines))

print("\n\n>>> Guardado en definiciones_pipeline.txt <<<")
