# Error al editar comentarios de Torres — octubre 2026

## Diagnóstico confirmado (DEV, 06-10-2026)

**Causa primaria: A. DATA_FALTANTE**, específicamente horizonte insuficiente de `inventar_SpcHidr.tot_TM`. La tabla termina el **01-10-2026 08:00:00**. El fin requerido por la bitácora para el primer día operacional de octubre es **02-10-2026 07:25:00**. Por tanto `MAX(ts_fin del día) <= MAX(tot_TM.fecha)` es falso para TODOS los días de octubre disponibles; el SELECT devuelve NULL. No se determinó por qué dejó de cargarse el totalizador ni se atribuye a un proceso de ingesta concreto.

Contribuyente UX: I. MENSAJE_INCORRECTO en contexto (dice exportar al editar y no informa fuente/horizonte faltante); el mensaje representa fielmente el None del helper, pero no explica el dato faltante. El acoplamiento editor/refresco es explícito y documentado en runtime; no se etiqueta BUG_EDITOR ni regla de negocio incorrecta sin validar el requisito.

## Cadena y fecha real

`generar_reporte` → `_cargar_detalle_representatividad_periodo` → `preparar_paquete_editor_representatividad` → `refrescar_representatividad_para_exportacion` → `fetch_fecha_corte_operacional_representatividad` → SELECT NULL → RuntimeError → Alert.

Archivo que lanza: `report_export/report_export.py:1601`; callback que muestra: `report_export/callbacks/reportabilidad_cb.py:7427`. [Call graph](callgraph.md), [contrato callback](callbacks.md).

La función real `sync_modo_y_mes('mes','2026-10')`, ejecutada sin decorador ni DB, devuelve **2026-10-01 → 2026-10-31**. No recorta a hoy ni exige esperar fin de mes. `fin_sql_exclusivo` no se usa en la rama Torres. El selector y el SELECT fueron reproducidos aisladamente, no el clic completo escritor.

## Qué significa cerrada en ESTE código

[SQL exacto](consulta_fecha_cerrada.sql): agrupa bitácora de T1/T2/SRR por fecha_turno dentro del rango inclusivo; calcula MAX(ts_fin); obtiene MAX(fecha) global en tot_TM; toma MAX(fecha_turno) de los grupos cuyo fin no excede ese horizonte.

No verifica ambos turnos ni las tres torres completas, huecos de 10 segundos, valores no NULL por canal, química, física, apilado, cache o tabla de cierre. «Completamente cubierta» del docstring describe intención; el test técnico real es solo horizonte máximo y existencia de al menos un rango del día. No se certifica cobertura integral a partir del nombre.

## Septiembre→octubre

| Fecha operacional | Rangos | Torres/turnos | Fin máximo requerido | ¿Cerrada según query? |
|---|---:|---|---|---|
| 28-09 | 6 | T1/T2/SRR × A/B | 29-09 07:20 | Sí |
| 29-09 | 6 | T1/T2/SRR × A/B | 30-09 07:40 | Sí |
| 30-09 | 6 | T1/T2/SRR × A/B | 01-10 07:40 | Sí |
| 01-10 | 6 | T1/T2/SRR × A/B | 02-10 07:25 | No |
| 02-10 | 6 | T1/T2/SRR × A/B | 03-10 07:25 | No |
| 03-10 | 6 | T1/T2/SRR × A/B | 04-10 07:30 | No |

Máxima fecha de bitácora: **05-10**, fin 06-10 07:30. Días 01–05 octubre tienen rangos, pero cero fechas cerradas. Totalizador sí tiene datos calendario del 01-10 (2.881 registros, 00:00–08:00); eso no cubre el día operacional 01-10. El día 30-09 cierra gracias a datos del 01-10 temprano. Máxima fecha cerrada GLOBAL: **30-09**.

Septiembre tiene 30/30 fechas, seis claves torre-turno por fecha y los 30 fines dentro del horizonte. Esto solo certifica el criterio consultado, no todos los datos del reporte. No se amplió auditoría a fuentes que no participan en cierre.

**Se descarta B. CONTINUIDAD_MES_ANTERIOR como causa de este fallo.** La vista fuente usa LAG por torre para ts_ini, pero la selección de corte solo usa ts_fin; no exige ts_ini ni cobertura completa septiembre. No hay condición explícita 01-10 depende de 30-09 para resolver este corte. Dependencias posteriores de refresco no se ejecutan porque falla antes.

## Mes, rango y otros reportes

Mes octubre y rango 01–03 octubre devuelven NULL por la misma query. No existe última fecha cerrada de octubre para construir el caso C; usar 30-09 produciría rango invertido y no es fallback permitido. Septiembre devuelve 30-09 con el mismo SQL. [Comparación](comparacion_mes_vs_rango.md).

La descarga Excel oficial de Torres usa snapshot ya publicado, no resuelve nuevamente este corte LIVE. La creación/publicación de un nuevo snapshot sí comparte el refresco. Análisis TM y Datos Conciliados usan un corte diferente basado en cuatro claves CV008/CV108 A/B y diagnóstico PI/TUM; no puede trasladarse automáticamente esta causa a ellos. [Matriz de reportes](comparacion_reportes.md).

## Manejo de error y limitación de reproducción

El SELECT ejecutado terminó correctamente; su fila contiene NULL. El helper retorna None, luego el refresco lanza RuntimeError. Un error SQL previo produciría otro mensaje envuelto. El callback presenta str(e) y no deja traceback propio en ese except. No se encontró el log original del clic; se reproduce su condición de fallo con código/SELECT exactos, sin afirmar una captura histórica de aquella sesión.

No se ejecutó el flujo completo de septiembre: adquirir locks/refrescar y materializar implicaría escrituras prohibidas. El «caso OK» se limita al resolver de fecha. Definiciones de vistas inspeccionadas LIVE y hashes runtime guardados.

## Propuestas, NO implementadas

**Mínima:** investigar y restablecer mediante proceso autorizado la carga real de tot_TM hasta cubrir los rangos pendientes; para habilitar 01-10 requiere al menos su fin 02-10 07:25. Después repetir SELECT y validaciones de cobertura, sin fabricar registros ni adelantar MAX artificialmente. La mera presencia de un timestamp futuro satisface el código actual pero no garantiza datos íntegros.

**UX mínima:** informar período, máximo totalizador y fin requerido; indicar ausencia de días cerrados en el rango, evitando «exportar» al editar. No rebajar el corte ni reutilizar septiembre silenciosamente.

**Robusta:** separar un preflight de lectura (disponibilidad y diagnóstico) del refresco escritor y de la edición de comentarios, sujeto a aprobación de coherencia de datos/notas. Revisar si la política debe exigir seis claves torre-turno y cobertura real por canal/intervalo, con especificación funcional previa. Mantener locks y garantías transaccionales del refresco existente. Impacto directo: editor/publicación Torres; descarga snapshot debe conservar su contrato. Cambiar la política de corte compartido RTO requeriría otra auditoría, no está propuesto como arreglo de este error.

Riesgos: permitir comentarios sobre datos que luego cambien, declarar cerrado un día parcial por MAX global, alterar snapshots oficiales o saltar validaciones de refresco. No se implementó ninguna propuesta.

## Evidencia e integridad

Carpeta `scripts/diagnosticos/reportes_fecha_cerrada_octubre_2026/`: README, callgraph, callbacks, query literal, parámetros, selector aislado, resultados de fechas, cobertura septiembre/octubre, filas bitácora, conteos de totalizador, definiciones, comparación de reportes y resultados. Todos contienen evidencia real o propuestas identificadas.

Hashes runtime antes/después iguales. `git diff --check` PASS; no se requirió suite completa porque no se cambió código funcional. SQL Server sin escrituras; sin DDL/DML, PROD, commit ni push.
