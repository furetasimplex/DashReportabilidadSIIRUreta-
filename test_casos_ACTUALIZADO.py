#!/usr/bin/env python3
"""
Test script para diagnosticar problema de dropdown de casos vacío
Ejecutar: python3 test_casos.py
"""

import sys
import os

# Agregar ruta del proyecto
sys.path.insert(0, os.path.dirname(__file__))

print("\n" + "=" * 70)
print("🔍 DIAGNÓSTICO: Dropdown de Casos Vacío")
print("=" * 70)

# ============================================================================
# Test 1: Verificar módulos
# ============================================================================
print("\n[1/5] 📦 Importando módulos...")
print("-" * 70)

try:
    from modules.data_loader import get_data_loader
    print("✓ modules.data_loader importado correctamente")
except ImportError as e:
    print(f"✗ ERROR importando data_loader: {e}")
    print("\nSolución: Verifica que la carpeta 'modules/' existe con archivos .py")
    sys.exit(1)

try:
    from modules.reconciliation_engine import get_reconciliation_engine
    from modules.validators import get_validators
    from modules.audit_manager import get_audit_manager
    from modules.versioning import get_version_control
    print("✓ Todos los módulos importados correctamente")
except ImportError as e:
    print(f"✗ ERROR importando módulos: {e}")
    sys.exit(1)

# ============================================================================
# Test 2: Instancias singleton
# ============================================================================
print("\n[2/5] 🔧 Creando instancias singleton...")
print("-" * 70)

try:
    data_loader = get_data_loader()
    print(f"✓ DataLoader: {data_loader}")
    print(f"  - Engine: {data_loader.engine}")
except Exception as e:
    print(f"✗ ERROR creando DataLoader: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 3: Verificar variables de entorno
# ============================================================================
print("\n[3/5] 🌍 Variables de entorno...")
print("-" * 70)

db_host = os.getenv('DB_HOST', 'NO CONFIGURADO')
db_user = os.getenv('DB_USER', 'NO CONFIGURADO')
db_password = os.getenv('DB_PASSWORD', '***OCULTA***' if os.getenv('DB_PASSWORD') else 'NO CONFIGURADA')
db_port = os.getenv('DB_PORT', '1433')

print(f"DB_HOST: {db_host}")
print(f"DB_USER: {db_user}")
print(f"DB_PASSWORD: {db_password}")
print(f"DB_PORT: {db_port}")

if db_host == 'NO CONFIGURADO':
    print("\n⚠️  ALERTA: DB_HOST no está configurado")
    print("   Solución: Ejecutar antes de iniciar app:")
    print("   export DB_HOST=<tu_servidor>")
    print("   export DB_USER=sa")
    print("   export DB_PASSWORD=<tu_contraseña>")

# ============================================================================
# Test 4: Verificar conexión BD
# ============================================================================
print("\n[4/5] 🔌 Verificando conexión a BD...")
print("-" * 70)

# Mostrar drivers disponibles
try:
    import pyodbc
    available_drivers = pyodbc.drivers()
    print(f"Drivers ODBC disponibles:")
    for driver in available_drivers:
        if 'SQL' in driver or 'ODBC' in driver:
            print(f"  • {driver}")
except Exception as e:
    print(f"  No se pudieron listar drivers: {e}")

if data_loader.engine is None:
    print("\n✗ Engine es None - No hay conexión a BD")
    print("\nPosibles causas:")
    print("  1. Variables de entorno no configuradas (DB_HOST, DB_USER, DB_PASSWORD)")
    print("  2. ODBC Driver no instalado (18, 17 o superior)")
    print("  3. Servidor BD no es accesible")
    print("  4. Credenciales incorrectas")
    print("\nPara instalar ODBC Driver en Linux:")
    print("  apt-get install msodbcsql18  (recomendado)")
    print("  o")
    print("  apt-get install msodbcsql17")
    sys.exit(1)
else:
    print(f"\n✓ Conexión BD establecida")
    print(f"  Engine: {data_loader.engine.url}")

# ============================================================================
# Test 5: Ejecutar query
# ============================================================================
print("\n[5/5] 🔍 Ejecutando query get_available_casos()...")
print("-" * 70)

try:
    df_casos = data_loader.get_available_casos()

    print(f"✓ Query ejecutada exitosamente")
    print(f"  Total de casos: {len(df_casos)}")

    if len(df_casos) == 0:
        print("\n⚠️  ALERTA: DataFrame vacío - No hay casos en BD")
        print("\nPosibles causas:")
        print("  1. Tabla recon_caso no existe en dev_siir.hidro")
        print("  2. Tabla recon_caso_oficial no existe en dev_siir.hidro")
        print("  3. Las tablas existen pero no tienen datos")
        print("  4. No hay casos con relación (caso_id) entre las tablas")
        print("\nPara verificar en SQL Server:")
        print("  SELECT COUNT(*) FROM [DEV_SIIR].[hidro].[recon_caso]")
        print("  SELECT COUNT(*) FROM [DEV_SIIR].[hidro].[recon_caso_oficial]")
        print("  SELECT rc.id, rc.nombre_caso FROM [DEV_SIIR].[hidro].[recon_caso] rc")
    else:
        print("\n✓ Datos encontrados:\n")
        print(df_casos.to_string())
        print("\nEstructura del DataFrame:")
        print(f"  Columnas: {list(df_casos.columns)}")
        print(f"  Tipos: {df_casos.dtypes.to_dict()}")

        # Generar opciones para dropdown
        print("\n📋 Opciones que generaría el dropdown:")
        for _, row in df_casos.iterrows():
            label = f"{row['nombre_caso']} ({row['fecha_inicio'].strftime('%Y-%m-%d')} a {row['fecha_fin'].strftime('%Y-%m-%d')})"
            value = row['id']
            print(f"  Label: '{label}'")
            print(f"  Value: {value}")
            print()

except Exception as e:
    print(f"✗ ERROR ejecutando query: {e}")
    import traceback
    traceback.print_exc()

    print("\nDebugging info:")
    print(f"  data_loader.engine: {data_loader.engine}")
    print(f"  DB_HOST: {os.getenv('DB_HOST')}")
    print(f"  DB_USER: {os.getenv('DB_USER')}")
    print(f"  DB_PORT: {os.getenv('DB_PORT')}")

# ============================================================================
# Resumen Final
# ============================================================================
print("\n" + "=" * 70)
print("📊 RESUMEN")
print("=" * 70)

if data_loader.engine is not None and len(df_casos) > 0:
    print("✓ TODO FUNCIONA CORRECTAMENTE")
    print("\nEl problema está en la integración Dash, no en la BD.")
    print("Próximos pasos:")
    print("  1. Verificar que Store component está en layout")
    print("  2. Verificar que prevent_initial_call=False en callback")
    print("  3. Habilitar logging DEBUG en callbacks")
    print("  4. Revisar browser console (F12) para errores JS")
elif data_loader.engine is None:
    print("✗ PROBLEMA: No hay conexión a BD")
    print("\nNecesitas:")
    print("  1. Instalar ODBC Driver 17: apt-get install msodbcsql17")
    print("  2. Configurar variables de entorno (DB_HOST, DB_USER, DB_PASSWORD)")
    print("  3. Verificar que servidor BD es accesible")
else:
    print("✗ PROBLEMA: Conexión OK pero no hay datos")
    print("\nNecesitas:")
    print("  1. Verificar que tablas recon_caso y recon_caso_oficial existen")
    print("  2. Verificar que ambas tablas tienen datos")
    print("  3. Verificar que recon_caso_oficial.caso_id apunta a recon_caso.id")

print("\n" + "=" * 70)
