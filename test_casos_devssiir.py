#!/usr/bin/env python3
"""
Test específico para casos en DEV_SIIR (cross-database query)
Ejecutar desde carpeta DashReportabilidadSIIR: python3 ../test_casos_devssiir.py
"""

import sys
import os

# Agregar ruta del proyecto
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'DashReportabilidadSIIR'))

print("\n" + "=" * 70)
print("🔍 TEST: Cargar Casos desde DEV_SIIR.hidro (Cross-Database)")
print("=" * 70)

# Test 1: Import
print("\n[1/4] 📦 Importando DataLoader...")
try:
    from DashReportabilidadSIIR.modules.data_loader import get_data_loader
    print("✓ DataLoader importado")
except Exception as e:
    print(f"✗ ERROR: {e}")
    sys.exit(1)

# Test 2: Instancia
print("\n[2/4] 🔧 Creando instancia...")
try:
    data_loader = get_data_loader()
    if data_loader.engine is None:
        print("✗ Engine es None - Sin conexión a BD")
        sys.exit(1)
    print(f"✓ Conexión OK: {data_loader.engine.url}")
except Exception as e:
    print(f"✗ ERROR: {e}")
    sys.exit(1)

# Test 3: Query a DEV_SIIR
print("\n[3/4] 🔍 Ejecutando query cross-database a DEV_SIIR.hidro...")
print("   Query: SELECT ... FROM [DEV_SIIR].[hidro].[recon_caso_oficial]")

try:
    df = data_loader.get_available_casos()

    if len(df) == 0:
        print("⚠️  DataFrame vacío")
        print("\nPosibles causas:")
        print("  1. DEV_SIIR.hidro.recon_caso_oficial no existe")
        print("  2. No hay registros con estado='ACTIVO'")
        print("  3. Permisos insuficientes para acceder a DEV_SIIR")
        print("\nVerifica con SQL Server:")
        print("  SELECT COUNT(*) FROM [DEV_SIIR].[hidro].[recon_caso_oficial]")
        print("  WHERE estado = 'ACTIVO'")
    else:
        print(f"✓ {len(df)} casos encontrados en DEV_SIIR.hidro\n")
        print(df.to_string(index=False))

except Exception as e:
    print(f"✗ ERROR en query: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Generar opciones para dropdown
print("\n[4/4] 📋 Generando opciones para dropdown...")

try:
    opciones = [
        {
            'label': f"{row['caso_balance']} - {row['descripcion']}",
            'value': row['caso_balance']
        }
        for _, row in df.iterrows()
    ]

    print(f"✓ {len(opciones)} opciones generadas:\n")
    for opt in opciones[:5]:  # Mostrar primeras 5
        print(f"  • {opt['label']} (value={opt['value']})")
    if len(opciones) > 5:
        print(f"  ... y {len(opciones) - 5} más")

except Exception as e:
    print(f"✗ ERROR generando opciones: {e}")
    sys.exit(1)

# Resumen
print("\n" + "=" * 70)
if len(df) > 0:
    print("✅ TODO FUNCIONA - Dropdown debería tener casos ahora")
    print("\nProximos pasos:")
    print("  1. Actualiza tu DashReportabilidadSIIR/modules/data_loader.py")
    print("  2. Reinicia la app: python3 main.py")
    print("  3. El dropdown debería mostrar los casos automáticamente")
else:
    print("❌ Problema con datos - Ver soluciones arriba")
print("=" * 70 + "\n")
