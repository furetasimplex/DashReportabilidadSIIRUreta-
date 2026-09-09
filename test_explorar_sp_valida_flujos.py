#!/usr/bin/env python3
"""
test_explorar_sp_valida_flujos.py
===================================
Vuelca la definicion de sp_valida_flujos_balance (DEV_SIIR.control_diario) y de
cualquier SP con 'concilia' o 'flujo' o 'mapeo' en el nombre en DEV_SIIR,
usando sp_helptext ejecutado DENTRO del contexto de esa BD para evitar el
problema de resolucion cross-database de OBJECT_ID.

Ejecutar: .venv/bin/python test_explorar_sp_valida_flujos.py
"""
from db_connection import get_engine
import pandas as pd
from sqlalchemy import text

pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 220)

engine = get_engine()

def dump_sp(schema, name):
    print(f"\n{'='*100}\nDefinicion de DEV_SIIR.[{schema}].[{name}]\n{'='*100}")
    try:
        with engine.connect() as conn:
            # USE DEV_SIIR + sp_helptext dentro de la misma sesion/conexion
            conn.exec_driver_sql("USE DEV_SIIR")
            rows = conn.exec_driver_sql(f"EXEC sp_helptext '{schema}.{name}'").fetchall()
            if not rows:
                print("(sin texto devuelto por sp_helptext -- puede estar encriptado o no accesible)")
            else:
                texto = "".join(r[0] for r in rows if r[0] is not None)
                print(texto)
    except Exception as e:
        print(f"✗ ERROR: {e}")

# Candidatos puntuales por nombre
candidatos = [
    ('control_diario', 'sp_valida_flujos_balance'),
    ('hidro', 'sp_reporte_representatividad_torres'),
]
for schema, name in candidatos:
    dump_sp(schema, name)

# Busqueda ampliada en DEV_SIIR por si hay mas candidatos con otros patrones
print(f"\n{'='*100}\nBusqueda ampliada de SPs en DEV_SIIR (concilia / mapeo / rep_flujo / oficial)\n{'='*100}")
try:
    df = pd.read_sql(
        "SELECT s.name AS esquema, p.name AS procedimiento "
        "FROM [DEV_SIIR].sys.procedures p JOIN [DEV_SIIR].sys.schemas s ON p.schema_id = s.schema_id "
        "WHERE p.name LIKE '%concilia%' OR p.name LIKE '%mapeo%' OR p.name LIKE '%oficial%' "
        "OR p.name LIKE '%publish%' OR p.name LIKE '%recon%' "
        "ORDER BY s.name, p.name",
        engine
    )
    print(df.to_string() if not df.empty else "(sin resultados)")
    for _, row in df.iterrows():
        dump_sp(row['esquema'], row['procedimiento'])
except Exception as e:
    print(f"✗ ERROR: {e}")

print("\n" + "=" * 100)
print("Copia y pega TODA esta salida.")
