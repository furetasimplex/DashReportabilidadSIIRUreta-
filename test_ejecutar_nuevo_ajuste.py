#!/usr/bin/env python3
"""
test_ejecutar_nuevo_ajuste.py
================================
Ejecuta un ajuste NUEVO end-to-end para un caso del solver nuevo
(recon_caso), usando el puente agregado 2026-09-09, y luego carga el
resultado (get_reconciliation_results + get_resumen_comparativo) igual
que haria el callback 'procesar_reconciliacion' del Dash.

OJO: esto SI escribe en la BD (rep_prod_targets, rep_prod_ajustado_stg,
rep_prod_ajustado, rep_prod_ajuste_log) - es voluntario, para probar el
flujo real.

Ejecutar: .venv/bin/python test_ejecutar_nuevo_ajuste.py [caso_id]
"""
import sys
from modules.data_loader import get_data_loader

caso_id = int(sys.argv[1]) if len(sys.argv) > 1 else 18  # "Semana 2", 2026-07-08 a 2026-07-15

dl = get_data_loader()

print(f"Ejecutando ajuste nuevo para caso_id={caso_id} ...")
try:
    resultado = dl.ejecutar_nuevo_ajuste(caso_id)
    print("OK:", resultado)
except Exception as e:
    print(f"FALLO: {e}")
    sys.exit(1)

run_id = resultado['run_id']

print(f"\n{'='*80}\nDatos ajustados (run_id={run_id})\n{'='*80}")
df = dl.get_reconciliation_results(caso_balance=caso_id, run_id=run_id)
cols = [c for c in ['Fecha', 'Chancado_TMS_Real', 'Sal_promedio_dia', 'Apilado_TMS_Real',
                     'Ley_CuT_Real', 'Cobre_fino_Apilado_Real',
                     'factor_chancado', 'factor_sal', 'factor_finos'] if c in df.columns]
print(f"Filas: {len(df)}")
print(df[cols].to_string(index=False))

print(f"\n{'='*80}\nComparativo ajustado vs target\n{'='*80}")
comparativo = dl.get_resumen_comparativo(caso_id, run_id)
for row in comparativo['rows']:
    print(f"  {row['metrica']:<35} ajustado={row['ajustado']:>14.2f}  target={row['target']:>14.2f}  "
          f"dif%={row['dif_pct']}  estado={row['estado']}")

print("\n>>> TEST COMPLETO OK <<<")
