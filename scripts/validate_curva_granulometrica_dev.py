import io
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from report_export.report_export import (  # noqa: E402
    export_reporte_turno_estilo_leyes_finos,
    fetch_clays_cufe_report,
    fetch_curva_granulometrica_report,
    fetch_generador_reporte_diario_emision,
    fetch_reporte_turno_cache_emision,
    fetch_trazabilidad_analitos_report,
)


load_dotenv()
if os.getenv("SQLSERVER_HOST") != "149.50.136.234":
    raise RuntimeError("Validacion bloqueada fuera de DEV")

inicio = date(2026, 8, 1)
fin_exclusivo = date(2026, 9, 1)
df_turno = fetch_reporte_turno_cache_emision(inicio, fin_exclusivo)
df_generador = fetch_generador_reporte_diario_emision(inicio, fin_exclusivo)
df_clays = fetch_clays_cufe_report(inicio, fin_exclusivo)
df_trazabilidad = fetch_trazabilidad_analitos_report(inicio, fin_exclusivo)
df_curva = fetch_curva_granulometrica_report(inicio, fin_exclusivo)

output = io.BytesIO()
common = dict(
    df_generador=df_generador,
    df_generador_resumen=df_generador,
    df_clays_cufe=df_clays,
    df_trazabilidad_analitos=df_trazabilidad,
    periodo_inicio=inicio,
    periodo_fin=date(2026, 8, 31),
)
export_reporte_turno_estilo_leyes_finos(
    df_turno,
    output,
    df_curva_granulometrica=df_curva,
    **common,
)
target = ROOT / "report_export" / "exports" / (
    "Analisis_Torres_de_Muestreo_20260801_20260831.xlsx"
)
target.write_bytes(output.getvalue())

wb = load_workbook(target, data_only=True)
esperadas = [
    "Reporte por Turno", "Generador Reporte", "Malla #100",
    "Curva Granulométrica", "Clays-CuFe", "Trazabilidad Analitos",
]
if wb.sheetnames != esperadas:
    raise AssertionError(f"Orden inesperado: {wb.sheetnames}")
ws = wb["Curva Granulométrica"]
if ws.max_row != len(df_curva) + 8:
    raise AssertionError("Cantidad de filas distinta de la vista SQL")
if ws["J9"].value != df_curva.iloc[0]["P2"]:
    raise AssertionError("P2 fue alterado durante la exportacion")

control = df_curva.loc[
    (df_curva["Fecha"] >= date(2026, 8, 1))
    & (df_curva["Fecha"] <= date(2026, 8, 26))
].copy()
distribucion = Counter(control["Torres_Utilizadas"])
esperada = Counter({"SIN_DATO": 17, "TM1": 23, "TM1+TM2": 10, "TM2": 2})
if len(control) != 52 or distribucion != esperada:
    raise AssertionError(
        f"Control 01-26 agosto inesperado: rows={len(control)} {distribucion}"
    )

def fila(fecha, turno):
    resultado = df_curva.loc[
        (df_curva["Fecha"] == fecha) & (df_curva["Turno"] == turno)
    ]
    if len(resultado) != 1:
        raise AssertionError(f"Caso inexistente o duplicado: {fecha} {turno}")
    return resultado.iloc[0]


caso_21a = fila(date(2026, 8, 21), "A")
esperado_21a = {
    "Ton_TM1": 7111.0, "Ton_TM2": 6769.0, "Tiene_Curva_TM1": 1,
    "Tiene_Curva_TM2": 0, "Torres_Utilizadas": "TM1", "P2": 100.0,
    "P1": 98.294, "P34": 93.678, "P12": 81.084, "P14": 64.225,
    "P10": 50.075, "P35": 39.438, "P100": 33.919, "P150": 0.0,
    "P200": 0.0, "P325": 0.0, "PBajo325": 0.0,
}
for columna, esperado in esperado_21a.items():
    real = caso_21a[columna]
    if isinstance(esperado, float):
        if abs(float(real) - esperado) > 1e-9:
            raise AssertionError(f"21-08 A {columna}: {real} != {esperado}")
    elif real != esperado:
        raise AssertionError(f"21-08 A {columna}: {real} != {esperado}")

caso_20b = fila(date(2026, 8, 20), "B")
if caso_20b["Torres_Utilizadas"] != "TM1+TM2":
    raise AssertionError("20-08 B no utiliza TM1+TM2")
if abs(float(caso_20b["P2"]) - 100.0) > 1e-9:
    raise AssertionError("20-08 B P2 distinto de 100")
if abs(float(caso_20b["P100"]) - 26.7875700201893) > 1e-9:
    raise AssertionError("20-08 B P100 inesperado")

baseline = io.BytesIO()
export_reporte_turno_estilo_leyes_finos(df_turno, baseline, **common)
wb_base = load_workbook(io.BytesIO(baseline.getvalue()), data_only=False)
wb_final = load_workbook(target, data_only=False)
for nombre in [
    "Reporte por Turno", "Generador Reporte", "Malla #100", "Clays-CuFe",
    "Trazabilidad Analitos",
]:
    antes = wb_base[nombre]
    despues = wb_final[nombre]
    if (antes.max_row, antes.max_column) != (despues.max_row, despues.max_column):
        raise AssertionError(f"Dimensiones alteradas en {nombre}")
    valores_antes = [c.value for row in antes.iter_rows() for c in row]
    valores_despues = [c.value for row in despues.iter_rows() for c in row]
    if valores_antes != valores_despues:
        raise AssertionError(f"Valores alterados en {nombre}")

print(target.resolve())
print(f"rows_curva_total={len(df_curva)} rows_01_26={len(control)}")
print(f"distribucion_01_26={dict(distribucion)}")
print(
    "caso_21A=" + str({k: caso_21a[k] for k in esperado_21a})
)
print(
    "caso_20B=" + str({
        "Torres_Utilizadas": caso_20b["Torres_Utilizadas"],
        "P2": caso_20b["P2"], "P100": caso_20b["P100"],
    })
)
print(f"sheets={wb.sheetnames}")
print("hojas_existentes_sin_cambios=OK")
