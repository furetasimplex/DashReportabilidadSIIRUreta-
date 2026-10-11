#!/usr/bin/env python3
"""
test_pipeline_integrado.py
=============================
Smoke test del pipeline reescrito (data_loader.py + ajuste_reporte/rep_prod_adjuster.py)
SIN ejecutar un ajuste nuevo (usa un run_id historico ya exitoso para no generar
efectos secundarios en la BD).

Ejecutar: .venv/bin/python test_pipeline_integrado.py
"""
import sys
from modules.data_loader import get_data_loader

dl = get_data_loader()

print("=" * 80)
print("1) get_available_casos()")
print("=" * 80)
df_casos = dl.get_available_casos()
print(f"Total casos: {len(df_casos)}")
print(df_casos.head(5).to_string(index=False))

caso_id = 70
print(f"\n{'='*80}\n2) get_available_runs(caso_id={caso_id})\n{'='*80}")
df_runs = dl.get_available_runs(caso_id)
print(f"Total runs exitosos: {len(df_runs)}")
print(df_runs.to_string(index=False))

if df_runs.empty:
    print("No hay runs previos para probar get_reconciliation_results. Abortando.")
    sys.exit(0)

run_id = df_runs.iloc[0]['solver_run_id']
print(f"\nUsando run_id existente (sin recalcular): {run_id}")

print(f"\n{'='*80}\n3) get_reconciliation_results(caso_id={caso_id}, run_id={run_id})\n{'='*80}")
df_result = dl.get_reconciliation_results(caso_balance=caso_id, run_id=run_id)
print(f"Filas: {len(df_result)}")
cols_mostrar = [c for c in ['Fecha', 'Chancado_TMS_Real', 'Sal_promedio_dia',
                             'Apilado_TMS_Real', 'Ley_CuT_Real',
                             'Cobre_fino_Apilado_Real', 'factor_chancado',
                             'factor_sal', 'factor_finos'] if c in df_result.columns]
print(df_result[cols_mostrar].to_string(index=False))

print(f"\n{'='*80}\n4) get_resumen_comparativo(caso_id={caso_id}, run_id={run_id})\n{'='*80}")
comparativo = dl.get_resumen_comparativo(caso_id, run_id)
for row in comparativo['rows']:
    print(f"  {row['metrica']:<35} ajustado={row['ajustado']:>14.2f}  target={row['target']:>14.2f}  "
          f"dif%={row['dif_pct']}  estado={row['estado']}")

print(f"\n{'='*80}\n5) get_historial_ajustes(caso_id={caso_id}) (para pestaña Auditoria)\n{'='*80}")
df_hist = dl.get_historial_ajustes(caso_id)
print(f"Total corridas (exitosas+fallidas): {len(df_hist)}")
print(df_hist[['run_id', 'ts_inicio', 'ok']].head(10).to_string(index=False))

print("\n>>> TEST COMPLETO OK <<<")
