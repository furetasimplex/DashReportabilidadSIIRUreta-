import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tabs.procesar_pesos_lab import procesar_pesos_reales_torre, guardar_pesos_reales_bd
ruta_excel = r"C:\Users\nimun\OneDrive\Escritorio\Simplex\Template Modelo Hidrometalurgia\Template Área seca\Representatividad\01_Peso Torre Enero 2026.xlsx"

with open(ruta_excel, "rb") as f:
    contenido = f.read()

filename = "01_Peso Torre Enero 2026.xlsx"

df_pesos, msg_pesos = procesar_pesos_reales_torre(contenido, filename)

print(msg_pesos)

if df_pesos is not None:
    print(df_pesos.head(20))

    ok, msg_bd = guardar_pesos_reales_bd(df_pesos)
    print(msg_bd)
else:
    print("No se generó dataframe de pesos.")