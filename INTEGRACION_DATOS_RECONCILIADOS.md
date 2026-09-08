# Integración: Funcionalidades datos_reconciliados_of en DashReportabilidadSIIR

**Fecha**: Septiembre 2026  
**Estado**: Implementación (Fase 1-2 completada)  
**Objetivo**: Incorporar distribución proporcional, auditoría y versionamiento de balances

---

## 📋 RESUMEN DE CAMBIOS

Se han creado **5 módulos Python** en la carpeta `modules/` que implementan la lógica de reportabilidad post-balance:

### Módulos Creados

1. **`modules/data_loader.py`** (Carga de datos)
   - `DataLoader.get_reconciliation_results()` → Obtiene datos de reconciliación
   - `DataLoader.get_daily_measured_data()` → Obtiene datos diarios medidos
   - `DataLoader.get_available_runs()` → Lista versiones disponibles
   - `DataLoader.get_audit_history()` → Historial de ajustes

2. **`modules/reconciliation_engine.py`** (Distribución proporcional)
   - `ReconciliationEngine.calculate_daily_contributions()` → Calcula % aporte diario
   - `ReconciliationEngine.apply_proportional_adjustment()` → Distribuye diferencias
   - `ReconciliationEngine.process_all_flujos()` → Procesa todos los flujos

3. **`modules/validators.py`** (Validaciones)
   - `Validators.validate_sum_integrity()` → Verifica SUM = reconciliado
   - `Validators.check_zero_day_adjustments()` → Detecta ajustes en días cero
   - `Validators.detect_outliers()` → Identifica valores anómalos
   - `Validators.validate_all()` → Ejecuta todas las validaciones

4. **`modules/audit_manager.py`** (Auditoría)
   - `AuditManager.record_adjustment()` → Registra ajustes en BD
   - `AuditManager.mark_balance_official()` → Marca como oficial
   - `AuditManager.get_audit_trail()` → Obtiene log de auditoría
   - `AuditManager.generate_trazabilidad_report()` → Reporte de trazabilidad

5. **`modules/versioning.py`** (Control de versiones)
   - `VersionControl.get_active_version()` → Obtiene balance oficial
   - `VersionControl.list_all_versions()` → Lista todas las versiones
   - `VersionControl.compare_versions()` → Compara dos versiones
   - `VersionControl.archive_version()` → Archiva una versión

---

## 🔧 INSTALACIÓN

### Paso 1: Crear tabla de auditoría en SQL Server

```bash
# Conectarse a SQL Server y ejecutar:
USE SIIR_Dev;
GO

-- Ejecutar el script:
-- DashReportabilidadSIIR/scripts/create_audit_table.sql
```

O ejecutar manualmente el SQL proporcionado.

### Paso 2: Importar módulos en los callbacks

En tu archivo de callbacks (ej. `callbacks/reportabilidad_callbacks.py`):

```python
from modules.data_loader import get_data_loader
from modules.reconciliation_engine import get_reconciliation_engine
from modules.validators import get_validators
from modules.audit_manager import get_audit_manager
from modules.versioning import get_version_control

# Obtener instancias
data_loader = get_data_loader()
recon_engine = get_reconciliation_engine()
validators = get_validators()
audit_mgr = get_audit_manager()
version_ctrl = get_version_control()
```

### Paso 3: Usar en callbacks

Ejemplo callback para procesar reconciliación:

```python
@app.callback(
    [Output('tabla-ajustes', 'data'),
     Output('validacion-status', 'children')],
    [Input('btn-procesar-reconciliacion', 'n_clicks')],
    [State('dropdown-caso', 'value'),
     State('date-inicio', 'date'),
     State('date-fin', 'date'),
     State('dropdown-run-id', 'value')],
    prevent_initial_call=True
)
def procesar_reconciliacion(n_clicks, caso, fecha_inicio, fecha_fin, run_id):
    """Procesa reconciliación con distribución proporcional"""
    
    if not all([caso, fecha_inicio, fecha_fin, run_id]):
        return [], html.Div("❌ Falta información requerida", className='text-danger')
    
    try:
        # 1. Cargar datos
        recon_data = data_loader.get_reconciliation_results(
            caso, run_id, fecha_inicio, fecha_fin
        )
        daily_data = data_loader.get_daily_measured_data(
            caso, fecha_inicio, fecha_fin
        )
        
        # 2. Procesar distribución proporcional
        resultado = recon_engine.process_all_flujos(daily_data, recon_data)
        datos_ajustados = resultado['datos_consolidados']
        
        # 3. Validar
        valor_esperado = recon_data['diferencia'].sum()
        validacion = validators.validate_sum_integrity(
            datos_ajustados, valor_esperado
        )
        
        # 4. Registrar auditoría
        usuario = get_current_user()  # Tu función para obtener usuario
        audit_id = audit_mgr.record_adjustment(
            caso_balance=caso,
            run_id=run_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            adjustment_detail=datos_ajustados,
            usuario=usuario,
            version_balance=1
        )
        
        # 5. Mostrar resultados
        tabla_data = datos_ajustados.to_dict('records')
        
        status_msg = html.Div([
            html.Div(
                f"✓ Reconciliación procesada: {len(datos_ajustados)} registros",
                className='text-success'
            ),
            html.Div(
                f"✓ {validacion['mensaje']}",
                className='text-success' if validacion['es_valido'] else 'text-danger'
            ),
            html.Div(
                f"✓ Auditoría registrada: audit_id={audit_id}",
                className='text-info'
            )
        ], className='mt-2')
        
        return tabla_data, status_msg
        
    except Exception as e:
        return [], html.Div(f"❌ Error: {str(e)}", className='text-danger')
```

---

## 📊 EJEMPLO: FLUJO COMPLETO

```python
# 1. CARGAR DATOS
recon_data = data_loader.get_reconciliation_results(
    'Lixiviacion_SpcHidr', 
    run_id=5,
    fecha_inicio=date(2026, 9, 1),
    fecha_fin=date(2026, 9, 7)
)
# → DataFrame con [flujo_id, valor_medido, valor_reconciliado, diferencia]

daily_data = data_loader.get_daily_measured_data(
    'Lixiviacion_SpcHidr',
    fecha_inicio=date(2026, 9, 1),
    fecha_fin=date(2026, 9, 7)
)
# → DataFrame con [fecha, flujo_id, valor_medido]

# 2. PROCESAR TODOS LOS FLUJOS
resultado = recon_engine.process_all_flujos(daily_data, recon_data)

# Acceder a resultados
datos_ajustados = resultado['datos_consolidados']
resumen = resultado['resumen']
# → {
#     'total_flujos': 5,
#     'flujos_validos': 5,
#     'flujos_invalidos': 0,
#     'suma_total_ajustes': 200.02
# }

# 3. VALIDAR
validacion = validators.validate_all(daily_data, datos_ajustados, 200)
# → {
#     'es_valido': True,
#     'validaciones': {...},
#     'errores': [],
#     'advertencias': []
# }

# 4. REGISTRAR AUDITORÍA
audit_id = audit_mgr.record_adjustment(
    caso_balance='Lixiviacion_SpcHidr',
    run_id=5,
    fecha_inicio=date(2026, 9, 1),
    fecha_fin=date(2026, 9, 7),
    adjustment_detail=datos_ajustados,
    usuario='lcortes'
)

# 5. MARCAR COMO OFICIAL
audit_mgr.mark_balance_official(
    caso_balance='Lixiviacion_SpcHidr',
    run_id=5,
    fecha_inicio=date(2026, 9, 1),
    fecha_fin=date(2026, 9, 7),
    usuario='lcortes'
)

# 6. OBTENER VERSIONES
versiones = version_ctrl.list_all_versions(
    'Lixiviacion_SpcHidr',
    date(2026, 9, 1),
    date(2026, 9, 7)
)

# 7. COMPARAR VERSIONES
comparativo = version_ctrl.compare_versions(
    'Lixiviacion_SpcHidr',
    date(2026, 9, 1),
    date(2026, 9, 7),
    run_id_1=4,
    run_id_2=5
)
# → {
#     'resumen': {'dias_diferentes': 2, 'suma_diferencias': 12.1},
#     'diferencias_dia_a_dia': [...]
# }
```

---

## 📝 INTEGRACIÓN EN TABS

### Opción 1: Actualizar `tabs/tabreportabilidad.py`

Agregar nueva sección de "Reconciliación y Ajustes":

```python
def layout():
    return html.Div([
        # ... tabs existentes ...
        
        dbc.Card([
            dbc.CardHeader(html.H5("Reconciliación y Ajustes Post-Balance")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Caso de Balance"),
                        dcc.Dropdown(id='dropdown-caso', options=[...]),
                    ]),
                    dbc.Col([
                        html.Label("Período"),
                        dcc.DatePickerRange(id='date-range'),
                    ]),
                    dbc.Col([
                        html.Label("Versión (Run ID)"),
                        dcc.Dropdown(id='dropdown-run-id'),
                    ]),
                ]),
                
                dbc.Row([
                    dbc.Col([
                        html.Button('Procesar', id='btn-procesar'),
                        html.Button('Marcar como Oficial', id='btn-oficial'),
                        html.Button('Descargar', id='btn-descargar'),
                    ])
                ]),
                
                # Tabla de resultados
                dag.AgGrid(id='tabla-ajustes', columnDefs=[...]),
                
                # Status
                html.Div(id='validacion-status'),
                
                # Auditoría
                html.Div(id='audit-trail')
            ])
        ])
    ])
```

### Opción 2: Crear nuevo Tab `tabs/tab_reconciliacion_ajustes.py`

Crear archivo separado con interfaz completa del nuevo módulo.

---

## 🗄️ ESTRUCTURA DE BD

### Tabla Principal: `inventar_SpcHidr.Audit_Ajustes_Reportabilidad`

```sql
-- Campos clave:
- audit_id: PK
- caso_balance: FK a Casos_Balance
- run_id: ID de reconciliación
- fecha_inicio, fecha_fin: Período del balance
- flujo_id: Identificador del flujo
- fecha_dia: Día específico del ajuste
- valor_medido: Valor original medido
- ajuste_aplicado: Ajuste proporcional aplicado
- porcentaje_aporte: % aporte diario del flujo
- valor_final: valor_medido + ajuste_aplicado
- usuario_ajuste: Usuario que realizó el ajuste
- timestamp_ajuste: Cuándo se realizó
- metodo_distribucion: Método usado (Proporcional_Aporte_Diario)
- is_active: 1 si es oficial, 0 si archivado
```

### Vistas Creadas

- `vw_Audit_Ajustes_Activos` → Solo datos del balance oficial actual
- `vw_Audit_Ajustes_Historial` → Historial completo con estado

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [ ] Crear tabla de auditoría en SQL Server
- [ ] Copiar módulos a carpeta `modules/`
- [ ] Crear callbacks en `callbacks/reportabilidad_callbacks.py`
- [ ] Actualizar `tabs/tabreportabilidad.py` o crear nuevo tab
- [ ] Agregar dependencias (si falta): `pip install pyodbc pandas numpy`
- [ ] Testing: Procesar balance de prueba
- [ ] Validar integridad de sumas
- [ ] Probar marcado como oficial
- [ ] Validar auditoría registrada
- [ ] Documentación operacional
- [ ] Capacitación usuarios

---

## 📞 PRÓXIMOS PASOS

1. **Testing**: Ejecutar flujo completo con datos históricos
2. **Performance**: Optimizar queries si es necesario
3. **UI/Dashboard**: Crear interfaces visuales para nuevas funcionalidades
4. **Capacitación**: Entrenar usuarios en proceso de reportabilidad
5. **Rollout**: Implementar en producción

---

**Contacto**: Luis Cortés (luis@bases.cl)  
**Simplex Ingeniería** - Especialización Hidrometalúrgica
