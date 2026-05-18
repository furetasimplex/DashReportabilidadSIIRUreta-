import sys
import os
import datetime as dt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tabs.procesar_pesos_lab import procesar_bitacora_completa

ruta_excel = r"C:\Users\nimun\OneDrive\Escritorio\Simplex\Template Modelo Hidrometalurgia\Template Área seca\Representatividad\01_Peso Torre Enero 2026.xlsx"

with open(ruta_excel, "rb") as f:
    contenido = f.read()

filename = "01_Peso Torre Enero 2026.xlsx"

df_bitacora, msg = procesar_bitacora_completa(contenido, filename)

print(msg)

if df_bitacora is not None:
    print("\n--- 02 al 03 ---")
    print(
        df_bitacora[
            (df_bitacora["fecha_turno"] >= dt.date(2026, 1, 2)) &
            (df_bitacora["fecha_turno"] <= dt.date(2026, 1, 3)) &
            (df_bitacora["torre"].isin([1, 2]))
        ].to_string()
    )

    print("\n--- 05 al 10 ---")
    print(
        df_bitacora[
            (df_bitacora["fecha_turno"] >= dt.date(2026, 1, 5)) &
            (df_bitacora["fecha_turno"] <= dt.date(2026, 1, 10)) &
            (df_bitacora["torre"].isin([1, 2]))
        ].to_string()
    )

    print("\n--- 24 al 27 ---")
    print(
        df_bitacora[
            (df_bitacora["fecha_turno"] >= dt.date(2026, 1, 24)) &
            (df_bitacora["fecha_turno"] <= dt.date(2026, 1, 27)) &
            (df_bitacora["torre"].isin([1, 2]))
        ].to_string()
    )
else:
    print("No se generó dataframe de bitácora.")