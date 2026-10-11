from db_connection import get_engine
from sqlalchemy import text
import pandas as pd

engine = get_engine()

print("=" * 80)
print("recon_caso: lista completa de ids actual")
print("=" * 80)
with engine.connect() as conn:
    df_rc = pd.read_sql(text("SELECT id, nombre_caso, fecha_inicio, fecha_fin FROM [DEV_SIIR].[hidro].[recon_caso] ORDER BY id"), conn)
    print(df_rc.to_string(index=False))

print()
print("=" * 80)
print("casos_balance: MIN/MAX caso_id")
print("=" * 80)
with engine.connect() as conn:
    df_cb = pd.read_sql(text("SELECT MIN(caso_id) AS min_id, MAX(caso_id) AS max_id, COUNT(*) AS total FROM inventar_SpcHidr.casos_balance"), conn)
    print(df_cb.to_string(index=False))

print()
print("=" * 80)
print("Colisiones actuales (ids presentes en AMBOS sistemas)")
print("=" * 80)
ids_rc = set(df_rc["id"].tolist())
with engine.connect() as conn:
    df_cb_ids = pd.read_sql(text("SELECT caso_id FROM inventar_SpcHidr.casos_balance"), conn)
ids_cb = set(df_cb_ids["caso_id"].tolist())
colisiones = sorted(ids_rc & ids_cb)
print(f"colisiones: {colisiones}")
