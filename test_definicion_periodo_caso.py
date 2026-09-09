from db_connection import get_engine
from sqlalchemy import text
import pandas as pd

engine = get_engine()

def show(nombre):
    print("=" * 80)
    print(nombre)
    print("=" * 80)
    with engine.connect() as conn:
        df = pd.read_sql(text(f"SELECT OBJECT_DEFINITION(OBJECT_ID('{nombre}')) AS def"), conn)
        definicion = df.iloc[0]["def"]
        if definicion:
            print(definicion)
        else:
            raw = conn.exec_driver_sql(f"EXEC sp_helptext '{nombre}'")
            for row in raw.fetchall():
                print(row[0], end="")
    print()

show("inventar_SpcHidr.sp_rep_get_periodo_caso")

# Probar directamente que devuelve para caso_id=22 (recon_caso, deberia fallar/vacio)
# y para un caso_id valido de casos_balance
print("=" * 80)
print("EXEC directo sp_rep_get_periodo_caso @caso_id=22 (Agosto 2, recon_caso)")
print("=" * 80)
try:
    with engine.connect() as conn:
        raw = conn.exec_driver_sql("EXEC inventar_SpcHidr.sp_rep_get_periodo_caso @caso_id=22")
        rows = raw.fetchall()
        cols = raw.keys()
        print("columnas:", list(cols))
        print("filas:", rows)
except Exception as e:
    print(f"ERROR: {e}")
