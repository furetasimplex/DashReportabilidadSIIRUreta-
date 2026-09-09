#!/usr/bin/env python3
"""
test_runs.py
============
Diagnostico puntual de get_available_runs() para un caso real.
Ejecutar: .venv/bin/python test_runs.py [caso_id]
"""
import sys
import traceback

from modules.data_loader import get_data_loader

dl = get_data_loader()
print("Engine:", dl.engine)

df_casos = dl.get_available_casos()
if df_casos.empty:
    print("✗ No hay casos disponibles (revisa conexión)")
    sys.exit(1)

if len(sys.argv) > 1:
    caso_id = int(sys.argv[1])
else:
    caso_id = int(df_casos.iloc[0]['id'])

row = df_casos[df_casos['id'] == caso_id]
print(f"\nCaso seleccionado: id={caso_id}")
print(row.to_string())

fecha_inicio = row.iloc[0]['fecha_inicio'] if not row.empty else None
fecha_fin = row.iloc[0]['fecha_fin'] if not row.empty else None

print(f"\nLlamando get_available_runs(caso_balance={caso_id}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin})")
print("-" * 70)

try:
    df_runs = dl.get_available_runs(caso_balance=caso_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    print(f"\n✓ Query ejecutada. Total runs: {len(df_runs)}")
    if df_runs.empty:
        print("⚠️  DataFrame vacío -> el dropdown Run ID quedará vacío para este caso")
        print("Verifica en SQL Server:")
        print(f"  SELECT * FROM [DEV_SIIR].[hidro].[recon_caso_oficial] WHERE caso_id = {caso_id}")
    else:
        print(df_runs.to_string())
        print("\nTipos de columnas:")
        print(df_runs.dtypes)

        print("\nSimulando construccion de opciones del dropdown (igual que el callback):")
        for _, r in df_runs.iterrows():
            try:
                label = f"Run {r['solver_run_id']} - {r['oficializado_en'].strftime('%Y-%m-%d %H:%M')}"
                print(f"  OK  -> {label}")
            except Exception as e:
                print(f"  ✗ ERROR construyendo label para run {r['solver_run_id']}: {e}")
                print(f"     oficializado_en = {r['oficializado_en']!r} (tipo: {type(r['oficializado_en'])})")
except Exception as e:
    print(f"\n✗ EXCEPCION en get_available_runs: {e}")
    traceback.print_exc()
