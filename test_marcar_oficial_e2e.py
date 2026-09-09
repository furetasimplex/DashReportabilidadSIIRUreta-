"""
test_marcar_oficial_e2e.py
============================
Prueba end-to-end de "Marcar como Oficial" para caso_id=22 (Agosto 2,
recon_caso) / run dfb7743e-8d03-4da0-afff-5a625e128a42, usando la MISMA
función que llama el boton del Dash (ajuste_reporte.rep_prod_adjuster.
publicar_run_oficial via modules.data_loader.marcar_run_oficial).

Ejecutar:
    .venv/bin/python test_marcar_oficial_e2e.py
"""
from modules.data_loader import get_data_loader
from db_connection import get_engine
from sqlalchemy import text
import pandas as pd

data_loader = get_data_loader()

CASO_ID = 22
RUN_ID = "dfb7743e-8d03-4da0-afff-5a625e128a42"

print("=" * 80)
print(f"Publicando caso_id={CASO_ID} run_id={RUN_ID} como oficial...")
print("=" * 80)
try:
    resultado = data_loader.marcar_run_oficial(
        caso_id=CASO_ID,
        run_id=RUN_ID,
        usuario="lcortes_test",
        resumen=None,
    )
    print("✓ OK:", resultado)
except Exception as e:
    print(f"✗ ERROR: {e}")

print()
print("=" * 80)
print("Verificando Datos_conciliados_of_ver en el rango 2026-08-08 a 2026-08-15")
print("=" * 80)
engine = get_engine()
with engine.connect() as conn:
    df = pd.read_sql(
        text("""
            SELECT Fecha, Chancado_TMS_Real, run_id, caso_id, estado_validacion, usuario_validacion, validation_id
            FROM inventar_SpcHidr.Datos_conciliados_of_ver
            WHERE Fecha BETWEEN '2026-08-08' AND '2026-08-15'
            ORDER BY Fecha
        """),
        conn,
    )
print(f"filas encontradas: {len(df)}")
print(df.to_string(index=False))
