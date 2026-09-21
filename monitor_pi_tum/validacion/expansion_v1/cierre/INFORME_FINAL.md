# Cierre de validación PI/TUM — 19-09-2026

**Recomendación: NO-GO para promoción o ampliación funcional.** Se entregó la evidencia ejecutable de los controles, pero no corresponde declarar aprobación integral: hay dos tests fallidos del postproceso, un turno PENDIENTE_TUM, cobertura incompleta de rollback del módulo y limitaciones de integración visual/consumidores sin datos. No se corrigieron esas fallas durante este cierre.

**A. Implementación existente.** Gestión GLOBAL para siete señales; resolvedor operacional PI/TUM; variantes TEST de Balance, Representatividad y cadena Reclamo CV025; postproceso TUM que materializa únicamente apilado principal. Los ocho DDL de expansión coinciden con las definiciones desplegadas en DEV, normalizando espacios y CREATE/ALTER. El módulo está completo sin seguimiento Git: no se puede atribuir cada archivo a una fase histórica con `git diff`.

**B. Validado.** Conexión DEV verificada con nombre de base, servidor y máquina. Se extrajeron 70 filas RT y 56 RO para cinco fechas, ambos turnos y siete equipos. Se ejecutaron ambos SP actuales del Balance para cada fecha, modelo 1; resultados completos en JSON. Pre-cutover: igualdad de los 120 flujos. El 13-09 ambos devuelven 117 filas y solo F6/F7/F8/F9 cambian. Se compararon bases, pesos y representatividades TM1/TM2, y fuente/valores de Reclamo. La ausencia de RO antes del 01-09 es su frontera temporal, no una resolución pendiente.

**C. Diferencias esperadas.** NORMAL conserva PI incluso si PI=0. El 13-09 CV002 A y CV003 A/B cumplen RT→TUM y RO→PI=0: CAMBIO_ESPERADO_NUEVA_GOBERNANZA. CV002 B tiene PI=32768. F20 mixto 07-09: `(0 + 31387) × 0,90 = 28248,3 TMS`; baseline=0. F20 normal 13-09: oficial=TEST=42643,125 TMS. Las matrices contienen cifras exactas, deltas y clasificación por flujo.

**D. Regresiones / defectos.** El postproceso admite `informe_tum_srr` e `informe_tum_ripios`, pero enlaza `template=informe_tum_seca` en la consulta de historial. Por ello omite los cambios SRR/Ripios en sus batches reales. Dos nuevos tests reproducen 0 cambios detectados cuando se espera 1. El historial DEV confirma los templates propios: batch 20454 tiene 10 filas de totalizadores por cada señal SRR; 10439/10463/20455 tienen 15/3/10 filas CV025. No se afirma que el resolvedor dinámico pierda esos valores: la falla está en detección/informe de downstream. No se encontraron regresiones numéricas inexplicadas en los controles ejecutados del Balance; esto no certifica fechas no ensayadas.

**E. PENDIENTE_TUM.** CV025 08-09 B: PI=0, TUM=NULL, contingencia activa, RO=NULL y fuente PENDIENTE_TUM. A sí tiene TUM=4616. TEST lanza error 51025: bloquea toda la matriz, sin emitir fila F20 ni sustituir por PI/cero. Reclamo expone NULL y PENDIENTE_TUM en la fuente diaria. No se verificó una pantalla de Balance conectada a TEST; su tratamiento visual queda abierto.

**F. Objetos a evaluar para una futura promoción.** `inventar_SpcHidr.sp_calcular_balance_flujos`; cadena oficial de Representatividad (`v_peso_teorico_turno_torre_excel`, `v_representatividad_diaria_calculada` y su consumidor de tonelajes); `reclamo.v_cv25_diario`, `v_preliminar_cv25`, `v_preliminar_cv25_con_acumulado`, `v_reclamo_diario`, `v_diferencia_cv25`; resolvedor/estado operacional y consumidor materializado de apilado. Es un mapa de impacto, no un plan DDL aprobado: `v_bd_ton_t12` no existe con ese nombre en DEV y debe identificarse el consumidor oficial efectivo. Las dependencias exactas extraídas están en `dependencias.json`. La variante de Balance no es una copia estructural íntegra del SP oficial actual (p. ej. el oficial incluye guardas de ajustes acotados): no promover mediante reemplazo ciego.

**G. Riesgos abiertos.** Rollback comprobado por archivos para los ocho objetos de expansión; no hay paquete integral verificable para todas las tablas/SP/vistas previas del módulo. Reclamo conserva valores normales, pero sus columnas de masa pasan de decimal a float en TEST. Las vistas preliminares no tienen filas en las fechas de control: no se certifica reparto/acumulado real bajo contingencia. En 07/10-09 faltan horas para repartir y se devuelve SIN_HORAS_NO_REPARTIBLE. Falta comprobar interfaz de Balance frente a error 51025. La suite omite explícitamente un test SQL de cambio horario; no se ejecutaron validadores antiguos que registran declaraciones o despliegan objetos. Las lecturas se hicieron secuencialmente, no en un snapshot global de base.

**H. Siguiente etapa.** NO-GO hasta resolver el filtro de template y volver a pasar esos tests, completar rollback integral y cerrar los consumidores/estados visuales abiertos. Este informe termina la auditoría con hallazgos; no autoriza ni inicia esas correcciones.

## Evidencia entregada

1. [Trazabilidad de las siete señales, 70 filas](01_trazabilidad.md).
2. [Inventario de archivos, objetos DEV y ocho rollback](02_inventario_rollback.md).
3. [Matriz de Balance y todos los campos que cambian](03_balance_matriz.md).
4. [PI=0 y demostración algebraica del 13-09](04_impacto_13.md).
5. [CV025 mixto, pendiente y normal](05_cv025.md).
6. [Reclamo: cadena, humedad y comparación](06_reclamo.md).
7. [Representatividad: tonelajes, pesos y razones](07_representatividad.md).
8. [Tests completos con los dos fallos visibles](tests_completos.txt).

## Postproceso y Gestión

|Equipo|Detecta batch propio|Acción downstream implementada|
|---|---|---|
|CHANCADOR_CV006|Sí, template seca; validación de contrato|Consumidor dinámico; sin reproceso|
|PRINCIPAL_CV008|Sí, template seca; validación de contrato|Reproceso de apilado en fechas afectadas bajo contingencia|
|PRINCIPAL_CV108|Sí, template seca; validación de contrato|Reproceso de apilado en fechas afectadas bajo contingencia|
|SRR_CV001|No: filtro incorrecto|Consumidores dinámicos; sin reproceso previsto|
|SRR_CV002|No: filtro incorrecto|Consumidores dinámicos; sin reproceso previsto|
|SRR_CV003|No: filtro incorrecto|Consumidores dinámicos; sin reproceso previsto|
|RIPIOS_CV025|No: filtro incorrecto|Balance y capa RO de Reclamo dinámicos; tabla base Reclamo sigue materializada|

La agrupación declarada en `db.GRUPOS_EQUIPOS` y usada por la tabla de Gestión es CHANCADO/CV006, APILADO PRINCIPAL/CV008-CV108, SRR/CV001-CV002-CV003, RIPIOS/CV025. Se comprobó el código de presentación: no hay selector por equipo en Gestión; los selectores corresponden a fechas, turnos y motivo. Las acciones son globales. No se hizo una nueva prueba visual en navegador.

Suite existente: 64 PASS, 0 FAIL, 1 SKIP. Suite ampliada: **73 total, 70 PASS, 2 FAIL, 1 SKIP**, sin errores de carga. Los ocho casos nuevos cubren NORMAL PI=0, contingencia TUM, pendiente sin fallback, siete equipos por turno, CV025 mixto, pre-cutover y templates SRR/Ripios. Los tests de evidencia usan la captura DEV de este cierre; no equivalen a una matriz sintética exhaustiva de SQL. `pytest` no estaba instalado; se ejecutó el runner `unittest` utilizado por el módulo.

Durante este trabajo solo se añadieron scripts de auditoría, un archivo de tests y resultados/documentación. No hubo DDL, declaraciones, cambios de objetos oficiales, promoción, limpieza, refresh de cache/factor ni rollback ejecutado. Los SP de cálculo se ejecutaron en DEV y la conexión se cerró con rollback de la transacción de consulta, sin invocar scripts de rollback de objetos.
