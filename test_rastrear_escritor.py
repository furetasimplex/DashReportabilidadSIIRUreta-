#!/usr/bin/env python3
"""
test_rastrear_escritor.py
==========================
Aisla especificamente: que SP/objeto ESCRIBE en rep_prod_ajustado_stg y
rep_prod_targets (ahi deberia estar el calculo del reparto proporcional),
y vuelca el contenido COMPLETO de rep_prod_reglas.

Escribe el resultado a rastreo_escritor.txt (ademas de imprimir) para que
nada se pierda por el buffer de la terminal.

Ejecutar: .venv/bin/python test_rastrear_escritor.py
"""
from db_connection import get_engine
import pandas as pd

pd.set_option('display.max_colwidth', 200)
pd.set_option('display.width', 250)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

engine = get_engine()
out_lines = []

def w(s=""):
    print(s)
    out_lines.append(str(s))

tablas = ['rep_prod_ajustado_stg', 'rep_prod_targets', 'rep_prod_reglas']

w("=" * 100)
w("QUIEN LEE/ESCRIBE cada tabla (sys.sql_expression_dependencies, objetos tipo P=SP, V=vista, FN=funcion)")
w("=" * 100)
with engine.connect() as conn:
    for t in tablas:
        w(f"\n--- Dependencias de: {t} ---")
        try:
            q = f"""
            SELECT DISTINCT
                o.name AS objeto_dependiente,
                o.type_desc AS tipo,
                s.name AS schema_objeto
            FROM sys.sql_expression_dependencies d
            JOIN sys.objects o ON d.referencing_id = o.object_id
            JOIN sys.schemas s ON o.schema_id = s.schema_id
            WHERE d.referenced_entity_name = '{t}'
            ORDER BY tipo, objeto_dependiente
            """
            df = pd.read_sql(q, conn)
            if df.empty:
                w("  (sin dependencias registradas via sql_expression_dependencies)")
            else:
                w(df.to_string(index=False))
        except Exception as e:
            w(f"  ERROR: {e}")

w("\n" + "=" * 100)
w("Contenido COMPLETO de rep_prod_reglas (sin truncar)")
w("=" * 100)
try:
    df = pd.read_sql("SELECT * FROM rep_prod_reglas", engine)
    w(f"Total filas: {len(df)}")
    w(f"Columnas: {list(df.columns)}")
    w(df.to_string(index=False))
except Exception as e:
    w(f"ERROR leyendo rep_prod_reglas: {e}")

w("\n" + "=" * 100)
w("Buscar SPs que mencionen 'rep_prod_ajustado_stg' o 'factor_chancado' en su definicion (texto plano)")
w("=" * 100)
try:
    q = """
    SELECT o.name, o.type_desc
    FROM sys.sql_modules m
    JOIN sys.objects o ON m.object_id = o.object_id
    WHERE m.definition LIKE '%rep_prod_ajustado_stg%'
       OR m.definition LIKE '%factor_chancado%'
    """
    df = pd.read_sql(q, engine)
    if df.empty:
        w("  (ninguno encontrado en inventar_SpcHidr)")
    else:
        w(df.to_string(index=False))
        w("\n--- Definiciones completas ---")
        for name in df['name'].tolist():
            w(f"\n>>> {name} <<<")
            try:
                defn = pd.read_sql(f"SELECT OBJECT_DEFINITION(OBJECT_ID('{name}')) AS def", engine)
                w(defn['def'].iloc[0])
            except Exception as e:
                w(f"  ERROR obteniendo definicion: {e}")
except Exception as e:
    w(f"ERROR: {e}")

with open('rastreo_escritor.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(out_lines))

print("\n\n>>> Resultado tambien guardado en rastreo_escritor.txt <<<")
