from db_connection import get_engine
import pandas as pd
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', 60)
engine = get_engine()
df = pd.read_sql("SELECT run_id, caso_id, fecha_ini, fecha_fin, ts_inicio, ts_fin, ok, mensaje FROM inventar_SpcHidr.rep_prod_ajuste_log ORDER BY ts_inicio DESC", engine)
print(df.to_string(index=False))
