#!/usr/bin/env python3
"""
Test simple para verificar cross-database query a DEV_SIIR
Ejecutar desde cualquier carpeta del proyecto
"""

import sys
import os
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "=" * 70)
print("🔍 TEST: Cross-Database Query a DEV_SIIR.hidro")
print("=" * 70)

# Agregar ruta del proyecto al path
# Buscar DashReportabilidadSIIR en varias ubicaciones posibles
def find_project_root():
    """Encuentra la carpeta DashReportabilidadSIIR"""
    # Opción 1: Está en el mismo nivel que el script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Opción 2: Está en uploads/
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
    print(f"   Buscadas en:")
    for c in candidates:
        print(f"   - {c}")
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
    print(f"   Engine URL: {data_loader.engine.url}")

except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Ejecutar query cross-database
print("\n[3/4] 🔍 Ejecutando query cross-database a [DEV_SIIR].[hidro]...")
try:
    df_casos = data_loader.get_available_casos()

    if len(df_casos) == 0:
        print("   ⚠️  DataFrame vacío - No hay casos en BD")
        print("\n   Soluciones:")
        print("   1. Verificar que DEV_SIIR.hidro.recon_caso_oficial existe")
        print("   2. Verificar que tiene datos con estado='ACTIVO'")
        print("   3. Ejecutar en SQL Server:")
        print("      SELECT COUNT(*) FROM [DEV_SIIR].[hidro].[recon_caso_oficial]")
        print("      WHERE estado = 'ACTIVO'")
    else:
        print(f"   ✓ {len(df_casos)} casos encontrados\n")
        print("   Primeros casos:")
        print(df_casos.to_string(index=False))

except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Generar opciones dropdown
print("\n[4/4] 📋 Generando opciones para dropdown...")
try:
    opciones = [
        {
            'label': f"{row['caso_balance']} - {row['descripcion']}",
            'value': row['caso_balance']
        }
        for _, row in df_casos.iterrows()
    ]

    print(f"   ✓ {len(opciones)} opciones generadas")
    if opciones:
        print("\n   Ejemplo (primeras 3):")
        for opt in opciones[:3]:
            print(f"   - {opt['label']} (value='{opt['value']}')")

except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Resumen final
print("\n" + "=" * 70)
if len(df_casos) > 0:
    print("✅ TODO FUNCIONA CORRECTAMENTE")
    print("\nProximos pasos:")
    print("  1. El dropdown debería mostrar estos casos automáticamente")
    print("  2. Si sigue vacío, problema está en Dash (callbacks, Store)")
    print("  3. Ejecutar app: python3 main.py")
else:
    print("⚠️  Conexión OK pero sin datos en BD")
print("=" * 70 + "\n")
