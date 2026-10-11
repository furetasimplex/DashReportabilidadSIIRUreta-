# Hallazgos verificables

Informe completo: [DIAGNOSTICO_PERFORMANCE.md](../DIAGNOSTICO_PERFORMANCE.md).

| Hallazgo | Evidencia | Alcance |
|---|---|---|
| 102 días cuestan ~51 s y devuelven 102 fechas únicas | 21 repeticiones de siete parcelas en mediciones.json | DEV, rango 01-06 a 10-09-2026 |
| Escala aproximadamente lineal | Matriz 1/7/31/62/102 días, OX P1 y SULF P7 | No extrapolar SLA |
| PAD/parcela se filtran tarde | Planes reales: Filter 1 devuelve 102; Nested Loops 2 recibe/produce 6.120 antes del filtro | Misma estructura/hash en ambos planes |
| Trabajo diario sobre 60 parcelas | Table Spool 15: 102 ejecuciones, 6.120 filas, 102 rebinds y 0 rewinds | No reutiliza ese resultado entre fechas |
| Extremos/contexto se recomputan | Scans históricos 129/152/175/198 con 3.264/2.856 ejecuciones; MIN/MAX y ramas CPC/LEAD | Definición expandida y contadores reales, no solo SQL textual |
| Drenaje domina IO | 17.581.230 de 22.166.901 lecturas lógicas a 102 días | Páginas accedidas repetidamente; no tamaño único |
| Calendario no domina | Mediana 0,038 s; 614 lecturas | COUNT devuelve una fila con valor102 |
| Llamada directa no equivale al plan timeline | OX directa 0,056 s vs timeline1d 0,544 s; 5.228 vs 217.317 lecturas | Optimizaciones diferentes según forma de consulta |
| SQL domina callback | Timeline51,168/51,606 s dentro de callback52,016/52,078 s | Fetch también espera al servidor |
| No evidencia de spills ni espera de grant | XML real, grant11.600 KB/max usado1.936 KB, GrantWait0 | Hay spools; no se midieron páginas tempdb de sesión |
| Advertencias presentes | Optimizer TimeOut y PlanAffectingConvert varchar12 | No prueban causa única; ejecución sí finaliza |
| No histórico Query Store | OFF; consulta sin matches | No se activó |
| Caché DMV no identificada por búsqueda acotada | matching_cache vacío | No implica ausencia de plan; XML RetrievedFromCache=true |
| Índices/estadísticas inventariados | indices.json, estadisticas.json y metadata_supplement.json | Ninguno creado/actualizado por comandos de auditoría |

Posibles siguientes experimentos, no implementados: ruta de rango que limite temprano la parcela; reutilización de contexto/extremos por campaña; revisión de accesos/índices con evidencia; caché/materialización con invalidación. Riesgos, DDL y conservación contractual están en la sección19 del informe.

No se cambió runtime ni se ejecutaron DDL/DML. No PROD, commit ni push. El repositorio ya contenía cambios previos; se comparan hashes contra el inicio de esta auditoría, no contra HEAD.
