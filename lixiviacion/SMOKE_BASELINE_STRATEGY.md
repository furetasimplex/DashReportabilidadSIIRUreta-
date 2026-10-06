# Baselines, smokes y regresión de Lixiviación

## Separación de responsabilidades

**HISTORICAL_BASELINE** es una observación aprobada de un dataset y período concretos. No es una expectativa eterna del LIVE. **CURRENT_SMOKE** verifica contrato, coherencia interna y canónicos explícitos del LIVE. **REGRESSION_TEST** compara implementaciones sobre los mismos datos o fixtures. **STRUCTURAL_TEST** verifica interfaces, dependencias y forma del código sin interpretar importes históricos como salud actual.

Cada artefacto del [inventario](baselines/INVENTARIO.csv) tiene una categoría primaria única. Los informes de auditoría/metadata son evidencia estructural, no pruebas ejecutables. Un archivo de tests puede contener controles estructurales auxiliares dentro de una suite de regresión; no convierte un total histórico citado en expected del LIVE.

## Inventario de entradas y evidencia

| Entrada / evidencia | Categoría | Propósito, período y expectativas | Dependencias / escrituras / riesgo por datos |
|---|---|---|---|
| `smoke_dev.py`, `SMOKE_DEV.json` | HISTORICAL_BASELINE | 01-06→10-09-2026; 3264/2856/6120 filas; importes exactos OX/SULF/total aprobados. | V2 mediante db.overview. El script original sobrescribe SMOKE_DEV.json: **no ejecutarlo como smoke actual**. Falla legítimamente por deriva histórica. Se conserva íntegro. |
| `smoke_current_dev.py` | CURRENT_SMOKE | Contrato de 33 columnas/tipos/nullability; 60 parcelas/día del período aprobado; claves únicas; fórmulas con NULL; suma PAD/total. Ninguna constante esperada de toneladas. | SELECT V2/sys.columns/OBJECT_DEFINITION. Archivos únicos `test_evidence/smoke_current_v2_*.json`. Cambios de contrato/cobertura/fórmula fallan; variación coherente de toneladas no. |
| `smoke_map_dev.py`, `SMOKE_MAP_DEV.json` | CURRENT_SMOKE | Estado y distribución aprobados 10-09; consulta adicional 11-09. 32 OX/28 SULF; seis casos de composición. | Función diaria oficial mediante map_db. Canónicos pueden cambiar legítimamente por corrección de datos: investigar, nunca ajustar automáticamente. Original escribe ruta fija; usar ejecutor versionado. |
| `smoke_modules_dev.py`, `SMOKE_MODULES_DEV.json` | CURRENT_SMOKE | 10-09; módulos reales de OX P29/P17 y SULF P1, IDs/nombres/estados aprobados y conteo vs parcela. | Funciones oficiales parcela/módulo. Mismo riesgo canónico; original escribe ruta fija. Usar ejecutor versionado. |
| `smoke_diagnostic_dev.py`, `diagnostico_fase1/smoke.json` | REGRESSION_TEST | General + siete parcelas, 102 días; código anterior vs actual, cuatro KPI/tres gráficos/todas las filas y hashes. Siete estados canónicos al 10-09, campañas hidráulicas separadas de operacionales. | V2 y función diaria/timeline. Original escribe ruta fija. La cifra 30136 es anotación, **no** aserción de toneladas. Incluye hashes de preservación del cambio Fase 1; puede fallar por evolución legítima de archivos. |
| `test_lixiviacion.py` | REGRESSION_TEST | Filtros, NULL, cálculos de presentación, consultas y contrato usando fixtures. | Sin LIVE; no escribe evidencia histórica. Expected sintéticos son casos unitarios, no totales actuales. |
| `test_map.py`, `test_modules.py` | REGRESSION_TEST | Grano, selección, composición, estados y presentación con fixtures/mocks. | Sin LIVE; depende de módulos Python. No falla por nuevas cargas SQL. |
| `test_diagnostic_operational.py` | REGRESSION_TEST | Cabecera/timeline, aislamiento de errores, separación estados/filtros/campañas; mocks. | Sin LIVE; no sobrescribe artefactos. |
| `test_promocion.py` | STRUCTURAL_TEST | Separación de cabecera/cuerpo SQL y preservación literal mediante hashes, incluso strings/comentarios. | Fixtures SQL locales; no promociona SQL. Falla por cambios de código, no por volumen LIVE. |
| `test_timeline_runtime.py` | REGRESSION_TEST | Contrato12/CASE/NULL/AST y evidencia exacta 37 casos/multicampaña. | Archivos SQL/JSON congelados. No revalida SQL LIVE por leer un JSON PASS. |
| `test_smoke_strategy.py` | STRUCTURAL_TEST | Evitar NULL=0, duplicados y mezcla estados; escritura sin colisiones/sobrescritura. | Fixtures y tmp_path, sin SQL. |
| `diagnostico_timeline_runtime/*`, `diagnostico_performance_candidate/*` | REGRESSION_TEST | Comparaciones y benchmark de implementaciones sobre lecturas de aquella sesión; períodos 1/7/31/62/102/253 días según archivo. | Evidencia histórica del cambio, no baseline permanente de toneladas. Los harness originales tienen destinos fijos: no reutilizarlos para una nueva campaña sin otro directorio. |
| `diagnostico_auditoria/*`, `transferencia_cu_auditoria/*`, informes de rendimiento | STRUCTURAL_TEST | Evidencia de inspecciones en una fecha, contratos/definiciones/grano/agregados. | JSON/Markdown no ejecutables. Las capturas LIVE no se convierten en expected eterno. |
| `promocion_estado_operacional*/smoke_*previo*.json`, informes visuales y JSON de Chrome | STRUCTURAL_TEST | Evidencia archivada de promoción o revisión visual, con canónicos de su fecha. | No son entradas para afirmar salud LIVE ni autorización para ejecutar scripts de promoción. |

El CSV enumera las rutas individuales de JSON/Markdown y tests, SHA256 y constantes extraídas del código. Los respaldos `diagnostico_fase1/db.py` y callbacks son código anterior de comparación, no otra ruta runtime. No se movieron ni borraron archivos históricos.

## Baseline histórico protegido

`baselines/baseline_fecha_no_registrada_20260601_20260910.manifest.json` apunta al JSON original, registra su SHA256, fuente/DEV/período y valores por PAD. La fecha exacta de validación y hash de definición de aquella ejecución **no están registrados**; se conservan NULL. No se inventa una fecha a partir de mtime.

Histórico: **30.136,221811330 t**. LIVE observado 05-10-2026: **30.395,260628596 t**. Diferencia **+259,038817266 t**, reconciliada por PAD, causa no determinable con evidencia disponible. Flujo agregado idéntico: **12.168.556,400321637026000 m³**. [Auditoría causal](TRANSFERENCIA_CU_AUDITORIA.md). Ninguna cifra LIVE nueva se usa como PASS/FAIL permanente.

No ejecutar `python -m lixiviacion.smoke_dev` para salud actual: se preserva byte a byte por trazabilidad y compatibilidad con hashes previos. La deprecación operativa se documenta aquí y en README, sin editar el script histórico.

## Comandos vigentes

```powershell
.\venv\Scripts\python.exe -m pytest lixiviacion -q
.\venv\Scripts\python.exe -m lixiviacion.smoke_current_dev
.\venv\Scripts\python.exe -m lixiviacion.run_versioned_smoke map
.\venv\Scripts\python.exe -m lixiviacion.run_versioned_smoke modules
.\venv\Scripts\python.exe -m lixiviacion.run_versioned_smoke diagnostic
git diff --check
```

El ejecutor conserva las aserciones originales y captura únicamente la escritura del JSON conocido; cualquier otra escritura solicita investigación mediante error. Guarda PASS o excepción en un archivo nuevo. No cambia callbacks, SQL ni expectations para obtener PASS. Los originales siguen disponibles, pero sus entradas directas no deben usarse para nuevas evidencias porque tienen destinos fijos.

El smoke V2 admite química NULL cuando el contrato lo permite y exige propagación NULL consistente en la fórmula; no exige química cargada para todas las filas. Valida `campana_id` nullable y su relación con `estado_asignacion`. La cobertura 60/día es explícita para el período aprobado, no una regla universal para fechas futuras. Los canónicos/filtros y distinción campaña operacional/hidráulica se completan con regresión de Diagnóstico y tests unitarios: no son inferidos del importe total.

## Versionado y futuras regresiones

Convención: `baseline_<fecha_validacion>_<periodo>.json`, `smoke_current_<caso>_<UTC>_<id>.json`, `regression_<cambio>_<UTC>_<id>.json`. Fecha UTC con microsegundos e ID único, creación exclusiva `x`. Metadata: categoría, ejecución, DEV/DB, período, objetos y hashes de definición, resultado observado y checks/expected cuando aplica. El nombre del manifiesto antiguo dice `fecha_no_registrada` deliberadamente. No sobrescribir resultados previos, incluso los FAIL.

Para un cambio futuro: capturar antes el dataset/definiciones/hashes, ejecutar ambas implementaciones sobre ese mismo dataset, comparar KPI, JSON de gráficos, filas y hashes. Conservar expected y observed juntos bajo un identificador del cambio. Si se consulta LIVE en dos momentos y cambian fuentes, la comparación no aísla el efecto del código: marcar deriva/inconcluso y repetir sobre snapshot. El smoke de Fase 1 compara lecturas consecutivas y no ofrece aislamiento transaccional del conjunto; no atribuir automáticamente todo fallo a código.

Los snapshots estructurales de contrato se actualizan solo ante un cambio de contrato aprobado. Los canónicos cambian solo con evidencia funcional y aprobación explícita. Una nueva referencia numérica requiere aprobación expresa del responsable funcional/usuario, motivo, fecha, snapshot completo y hash de SQL, y **otra versión**; nunca sustituir la original para silenciar un FAIL.

## Interpretar fallos

| Señal | Interpretación / siguiente comprobación |
|---|---|
| Solo difiere total histórico | Deriva respecto del baseline; no prueba un error runtime. Comparar fuentes/definiciones históricas si existen. |
| Contrato/tipos/grano falla | Cambio de contrato o multiplicación; revisar antes de continuar. |
| Fórmula/NULL falla | Inconsistencia real respecto del contrato vigente, o deriva de definición durante lectura. |
| Canónico de mapa/módulos falla | Puede ser cambio legítimo de datos o regla; capturar observed y pedir validación funcional, sin ajustar expected automáticamente. |
| Regresión falla y hashes/dataset cambiaron | Inconclusa para atribución a código; congelar entradas. |
| Mismo dataset, definición y contrato; salida diferente | Regresión de implementación investigable. |
| Hash de preservación de Fase 1 falla | El scope histórico ya no representa el cambio nuevo; diseñar otra regresión, no borrar el control existente. |

## Validación de esta separación

67 tests PASS. Se excluyeron de doctest únicamente `diagnostico_timeline_runtime/tests_before.txt` y `tests_after.txt`: son logs históricos, el segundo UTF-16; no se alteraron. Smoke V2, mapa y módulos PASS; regresión Diagnóstico general + siete parcelas PASS. Resultados completos versionados en `test_evidence/`. `baselines/integrity_final.json` verifica los archivos previos: solo README fue modificado para advertir sobre el comando histórico. `git diff --check` PASS.

Sin cambios de runtime, baseline, V2, funciones SQL, fuentes, Mapa, Diagnóstico funcional ni Recomendador. Solo SELECT DEV; sin DDL/DML, PROD, commit o push.

Un reintento de módulos registró error de conexión previo al login (10054), conservado como FAIL versionado. El siguiente intento pasó con el hash de la función de módulos incluido. No se cambió ninguna expectativa por ese error de infraestructura.
