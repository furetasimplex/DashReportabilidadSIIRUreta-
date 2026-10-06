# Backfill extraordinario septiembre 2026 — DEV

Período fijo: **01-09-2026 a 30-09-2026 inclusive**. No usar estos scripts como runtime.

Estado ejecutor: **BACKFILL_PASS_CON_OBSERVACIONES**. Estado aplicación: **PASS_CALLBACKS_NO_REVISION_VISUAL**.

## Flujo y límites

Ver [entrypoints.md](entrypoints.md), [limites.md](limites.md) y [plan_bloques.json](plan_bloques.json).
No hay máximo general de rango encontrado. Ventanas runtime 7/7/15 intactas; bloques de 7/7/15 días para refrescar fechas existentes.
Representatividad incluye preparación RTO upstream; se conservó ese orden interno. No se publicó un snapshot oficial nuevo.

## Ejecuciones

| Reporte | Desde | Hasta | Estado | Segundos |
|---|---|---|---|---:|
| representatividad | 2026-09-01 | 2026-09-07 | COMMIT | 54.22 |
| representatividad | 2026-09-08 | 2026-09-14 | COMMIT | 45.82 |
| representatividad | 2026-09-15 | 2026-09-21 | COMMIT | 53.90 |
| representatividad | 2026-09-22 | 2026-09-28 | COMMIT | 55.96 |
| representatividad | 2026-09-29 | 2026-09-30 | COMMIT | 50.58 |
| analisis_tm | 2026-09-01 | 2026-09-07 | COMMIT | 22.11 |
| analisis_tm | 2026-09-08 | 2026-09-14 | COMMIT | 22.53 |
| analisis_tm | 2026-09-15 | 2026-09-21 | COMMIT | 21.94 |
| analisis_tm | 2026-09-22 | 2026-09-28 | COMMIT | 28.64 |
| analisis_tm | 2026-09-29 | 2026-09-30 | COMMIT | 21.45 |
| datos_conciliados | 2026-09-01 | 2026-09-15 | COMMIT | 32.18 |
| datos_conciliados | 2026-09-16 | 2026-09-30 | COMMIT | 41.57 |

## Cobertura / filas

| Tabla | Antes | Después | Duplicados después |
|---|---:|---:|---:|
| Resumen_Intervalo_TotTM | 180 | 180 | 0 |
| BD_Ton | 30 | 30 | 0 |
| representatividad_torres_resultado | 30 | 30 | 0 |
| Control_Apilado_TMH_v2_test | 30 | 30 | 0 |
| Control_Factor_Ajuste_Camiones_v2_test | 30 | 30 | 0 |
| Historico_Apilado_Diario | 30 | 30 | 0 |
| Clays_CuFe | 104 | 104 | 0 |
| Clays_CuFe_trazabilidad | 289 | 289 | 0 |
| trazabilidad_analitos_tm_emision_test | 1160 | 1160 | 0 |
| reporte_turno_cache_emision_test | 60 | 60 | 0 |
| Datos_conciliados_of | 30 | 30 | 0 |

Las tablas diarias tienen 30 fechas; RTO se valida en Fecha/Turno A/B. La ausencia de una fuente/analito no se reemplaza por datos inventados.
Comparación de campos y fechas en [comparacion.json](comparacion.json); perfiles y NULL en after.json/perfiles_fuentes.json.

## Validaciones

- representatividad: **PASS**, [validacion_representatividad.json](validacion_representatividad.json).
- analisis_tm: **PASS**, [validacion_analisis_tm.json](validacion_analisis_tm.json).
- datos_conciliados: **PASS**, [validacion_datos_conciliados.json](validacion_datos_conciliados.json).
- Unit tests de orquestación/paquetes: **118 passed, 31 subtests passed**.
- Suite adicional de exportación: **40 PASS, 3 FAIL** en runtime intacto (Campaña y dos pruebas de celdas posteriores al corte). Detalle: [tests.json](tests.json). No se corrigió código funcional.
- `git diff --check`: PASS (aviso de conversión LF/CRLF en layout.py preexistente).
- Resultados fuera de septiembre idénticos por hash: **True**.
- Octubre, solo lectura: corte Torres **2026-10-03**, corte apilado **2026-10-04**.
- Los cortes de octubre se resuelven desde las fuentes actuales y se contrastan con precheck.json; no se recalculó octubre.

## Aplicación y archivos

Smoke de callbacks reales con contexto Dash/Flask, SQL DEV y exportadores reales. No es revisión visual de navegador.
Resultados en [ui_smoke.json](ui_smoke.json); archivos en exports/. El editor se consulta sin guardar comentarios.
La descarga de Representatividad usa el snapshot activo existente y puede tener un corte distinto al resultado recién refrescado; no se republica automáticamente.

## Alcance y recuperación

Solo DML mediante los coordinadores vigentes en DEV. Sin cambios runtime, fórmulas, límites, reglas, SQL/DDL ni Lixiviación.
Octubre no recalculado. Sin PROD, commit ni push.
Respaldos y firmas: before.json, backup_logico/, outside_before.json. Recuperación: [rollback.md](rollback.md).
Definiciones LIVE de esta inspección: definitions/, objects.json, dependencies.json; no son scripts de despliegue.

## Reproducibilidad

`python -m scripts.backfill_septiembre_2026_reportes` es dry-run (se niega a sobrescribir el respaldo).
`--execute` exige precheck PASS, hashes runtime/DDL iguales y ausencia de ejecución previa. No reanudar automáticamente.
Los scripts inspect_readonly/review_precheck/finish_readonly son SELECT; application_smoke requiere --execute porque conserva refrescos de los callbacks.
summarize.py solamente organiza evidencia local.

## Archivos de salida de aplicación

| Reporte | Acción | Resultado | Archivo / observación |
|---|---|---|---|
| representatividad_torres | preview | PASS | Falso positivo del harness: botones PDF color danger, no Alert. Área de error vacía. Se reutiliza respuesta real; no se repite callback. |
| representatividad_torres | excel | PASS | [Reporte_Representatividad_Torres_20260901_20260930.xlsx](exports/Reporte_Representatividad_Torres_20260901_20260930.xlsx) |
| Representatividad LIVE | Excel sin publicar | PASS | [Representatividad_Septiembre_2026_LIVE_sin_publicar.xlsx](exports/Representatividad_Septiembre_2026_LIVE_sin_publicar.xlsx) |
| reporte_turno | preview | PASS | Sin archivo; vista previa |
| reporte_turno | excel | PASS | [Analisis_Torres_de_Muestreo_20260901_20260930.xlsx](exports/Analisis_Torres_de_Muestreo_20260901_20260930.xlsx) |
| prod | preview | PASS | Sin archivo; vista previa |
| prod | excel | PASS | [Reporte_DatosConciliados_20260901_20260930.xlsx](exports/Reporte_DatosConciliados_20260901_20260930.xlsx) |

Se conservó el falso positivo inicial del harness en ui_smoke_harness_falso_positivo.json: los botones PDF color danger no eran Alert de error. No fue un fallo del callback y no se repitió el preview.
Los tres fallos unitarios adicionales permanecen documentados; no se declara la suite completa como PASS.

## Observaciones que permanecen

- DC materializa 30 días, pero el resumen MTD corta al **2026-09-21**. El 22-09 faltan TMS_Rotopala_2_Real y Total_Ripios_Incluye_Camiones_Real; esos NULL estaban en el respaldo previo y siguen presentes. Ver completitud_dc.json.
- La prueba mensual usa los writers reales. El contexto de reclamo óxidos (módulo/avance) difiere entre dos bloques y una llamada mensual: el SP inicializa @PisoOx y @CampanaPisoOx en cada llamada (definición LIVE, líneas 443–468). El estado final es el de los previews/exports mensuales oficiales, no una reconstrucción manual. Comparación en comparacion_bloques_vs_smoke.json.
- Repetir la misma clave no duplicó resultados. Esto no implica equivalencia entre particiones de rango distintas para el contexto de reclamo. No se cambió esa regla.
- Los factores automáticos 22/09 y 23/09 cambiaron respecto del respaldo previo durante el refresco de sus insumos. La separación calculado/aplicado y FORZADO_1 se mantuvo; 16/09 sigue calculado 0,21963019549669024 y aplicado 1.
