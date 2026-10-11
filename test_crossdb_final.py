#!/usr/bin/env python3
"""
Test final para verificar cross-database query a DEV_SIIR con columnas correctas
Ejecutar desde cualquier carpeta del proyecto
"""

import sys
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "=" * 70)
print("✅ TEST FINAL: Query Corregida a DEV_SIIR.hidro.recon_caso")
print("=" * 70)

# Agregar ruta del proyecto al path
def find_project_root():
    """Encuentra la carpeta DashReportabilidadSIIR"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    candidates = [
        os.path.join(script_dir, 'DashReportabilidadSIIR'),
        os.path.join(os.path.dirname(script_dir), 'DashReportabilidadSIIR'),
        os.path.join(os.path.dirname(script_dir), 'uploads', 'AppHidrometalurgia_integrado', 'DashReportabilidadSIIR'),
        os.path.join(os.path.dirname(script_dir), 'AppHidrometalurgia_integrado', 'DashReportabilidadSIIR'),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            return os.path.dirname(candidate)

    return None

project_root = find_project_root()
if project_root:
    print(f"\n✓ Proyecto encontrado en: {project_root}")
    sys.path.insert(0, project_root)
else:
    print(f"\n✗ No se encontró DashReportabilidadSIIR")
    sys.exit(1)

# Test 1: Import DataLoader
print("\n[1/4] 📦 Importando DataLoader...")
try:
    from DashReportabilidadSIIR.modules.data_loader import get_data_loader
    print("   ✓ DataLoader importado correctamente")
except ImportError as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Test 2: Crear instancia y verificar conexión
print("\n[2/4] 🔌 Verificando conexión a BD...")
try:
    data_loader = get_data_loader()

    if data_loader.engine is None:
        print("   ⚠️  Engine es None - Sin conexión a BD")
        print("\n   Causas posibles:")
        print("   1. Variables de entorno no configuradas (DB_HOST, DB_USER, DB_PASSWORD)")
        print("   2. ODBC Driver no instalado")
        print("   3. Servidor BD no es accesible")
        sys.exit(1)

    print(f"   ✓ Conexión establecida")
    print(f"   Engine: {data_loader.engine.url}")

except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Ejecutar query cross-database (CORREGIDA)
print("\n[3/4] 🔍 Ejecutando query cross-database...")
print("   Query: SELECT ... FROM [DEV_SIIR].[hidro].[recon_caso]")
print("          INNER JOIN [DEV_SIIR].[hidro].[recon_caso_oficial]")
print("          ON rc.id = rco.caso_id")
try:
    df_casos = data_loader.get_available_casos()

    if len(df_casos) == 0:
        print("   ⚠️  DataFrame vacío - No hay casos en BD")
        print("\n   Soluciones:")
        print("   1. Verificar que recon_caso existe en DEV_SIIR.hidro")
        print("   2. Verificar que recon_caso_oficial existe en DEV_SIIR.hidro")
        print("   3. Verificar que hay registros con relación (caso_id)")
        print("\n   SQL para verificar:")
        print("   SELECT COUNT(*) FROM [DEV_SIIR].[hidro].[recon_caso]")
        print("   SELECT COUNT(*) FROM [DEV_SIIR].[hidro].[recon_caso_oficial]")
    else:
        print(f"   ✓ {len(df_casos)} casos encontrados\n")
        print("   Estructura del DataFrame:")
        print(f"   Columnas: {list(df_casos.columns)}")
        print(f"   Tipos: {df_casos.dtypes.to_dict()}\n")

        print("   Primeros casos:")
        print("   " + "-" * 66)
        for _, row in df_casos.head(3).iterrows():
            print(f"\n   ID: {row['id']}")
            print(f"   Nombre: {row['nombre_caso']}")
            print(f"   Período: {row['fecha_inicio']} a {row['fecha_fin']}")
            print(f"   Estado: {row['estado']}")

except Exception as e:
    print(f"   ✗ ERROR en query: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Generar opciones dropdown
print("\n[4/4] 📋 Generando opciones para dropdown...")
try:
    opciones = [
        {
            'label': f"{row['nombre_caso']} ({row['fecha_inicio'].strftime('%Y-%m-%d')} a {row['fecha_fin'].strftime('%Y-%m-%d')})",
            'value': row['id']
        }
        for _, row in df_casos.iterrows()
    ]

    print(f"   ✓ {len(opciones)} opciones generadas")
    if opciones:
        print("\n   Ejemplo de opciones (primeras 3):")
        for opt in opciones[:3]:
            print(f"   - Label: '{opt['label']}'")
            print(f"     Value: {opt['value']}")
            print()

except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Resumen final
print("=" * 70)
if len(df_casos) > 0:
    print("✅ TODO FUNCIONA CORRECTAMENTE")
    print("\n📊 Resumen:")
    print(f"   - Conexión: ✓ OK")
    print(f"   - Query cross-DB: ✓ OK ({len(df_casos)} casos encontrados)")
    print(f"   - Opciones dropdown: ✓ OK ({len(opciones)} opciones generadas)")
    print("\n🚀 Próximos pasos:")
    print("   1. Reinicia la app: python3 main.py")
    print("   2. El dropdown debería mostrar los casos automáticamente")
    print("   3. Verifica en navegador: http://localhost:8050")
else:
    print("⚠️  Conexión OK pero sin datos en BD")
    print("\n   Necesitas:")
    print("   1. Verificar que recon_caso tiene registros")
    print("   2. Verificar que recon_caso_oficial tiene registros")
    print("   3. Verificar que caso_id en recon_caso_oficial referencia recon_caso.id")
print("=" * 70 + "\n")
