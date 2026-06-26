from pathlib import Path
import sys
import inspect
import hashlib
import datetime as dt

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR if (SCRIPT_DIR / "tabs").exists() else SCRIPT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tabs.procesar_pesos_lab import procesar_bitacora_completa

# ============================================================
# 1. RUTA DEL EXCEL
# ============================================================

# Opción recomendada:
# crear una carpeta "archivos" dentro del proyecto y colocar ahí el Excel.


ruta_excel = Path(
    r"C:\Users\nimun\OneDrive\Escritorio\Simplex\Template Modelo Hidrometalurgia\Template Área seca\Peso Torres\01_Peso Torre Enero 2026.xlsx"
)


if not ruta_excel.exists():
    raise FileNotFoundError(
        f"No se encontró el archivo Excel en:\n{ruta_excel.resolve()}"
    )


# ============================================================
# 2. LEER ARCHIVO
# ============================================================

contenido = ruta_excel.read_bytes()
filename = ruta_excel.name


# ============================================================
# 3. IDENTIFICAR EL CÓDIGO REALMENTE IMPORTADO
# ============================================================

ruta_codigo = inspect.getsourcefile(
    procesar_bitacora_completa
)

codigo_cargado = inspect.getsource(
    procesar_bitacora_completa
)

print("=" * 80)
print("ARCHIVO PYTHON REALMENTE UTILIZADO")
print("=" * 80)
print(ruta_codigo)

print("\n" + "=" * 80)
print("HASH DEL CÓDIGO CARGADO")
print("=" * 80)
print(
    hashlib.sha256(
        codigo_cargado.encode("utf-8")
    ).hexdigest()
)


# ============================================================
# 4. PROCESAR EXCEL SIN GUARDAR EN BASE DE DATOS
# ============================================================

df_prueba, mensaje = procesar_bitacora_completa(
    decoded=contenido,
    filename=filename,
    fecha_manual=None
)

if df_prueba is None:
    raise RuntimeError(
        f"No se pudo procesar el archivo:\n{mensaje}"
    )

print("\n" + "=" * 80)
print("RESULTADO DEL PROCESAMIENTO")
print("=" * 80)
print(mensaje)

print("\n" + "=" * 80)
print("REGISTROS SIN HORA EN TODO EL MES")
print("=" * 80)

sin_hora = df_prueba[df_prueba["ts_toma_muestra"].isna()]

print(f"Cantidad de registros sin hora: {len(sin_hora)}")

if not sin_hora.empty:
    print(
        sin_hora[
            [
                "fecha_calendario",
                "turno",
                "torre",
                "comentario"
            ]
        ].to_string(index=False)
    )


# ============================================================
# 5. FILTRAR FECHAS CRÍTICAS
# ============================================================

filtro = (
    (df_prueba["fecha_calendario"] >= dt.date(2026, 1, 22))
    &
    (df_prueba["fecha_calendario"] <= dt.date(2026, 1, 31))
    &
    (df_prueba["torre"].isin([1, 2]))
)

columnas = [
    "fecha_calendario",
    "turno",
    "torre",
    "ts_toma_muestra",
    "comentario",
    "nombre_archivo"
]

resultado = (
    df_prueba.loc[filtro, columnas]
    .sort_values(
        [
            "fecha_calendario",
            "turno",
            "torre"
        ]
    )
)


# ============================================================
# 6. MOSTRAR RESULTADO
# ============================================================

print("\n" + "=" * 80)
print("VISTA PREVIA SIN GUARDAR EN BASE DE DATOS")
print("=" * 80)

print(
    resultado.to_string(index=False)
)


# ============================================================
# 7. GUARDAR SOLO LA VISTA PREVIA EN CSV
# ============================================================

ruta_salida = Path(
    "resultado_prueba_bitacora_enero.csv"
)

resultado.to_csv(
    ruta_salida,
    index=False,
    encoding="utf-8-sig",
    sep=";"
)

print("\n" + "=" * 80)
print("ARCHIVO DE RESULTADO")
print("=" * 80)
print(ruta_salida.resolve())

print("\nLa base de datos NO fue modificada.")
