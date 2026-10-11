# Fase 1 downstream PI/TUM — implementación DEV

Se corrigió exclusivamente la preparación de Reporte por Turno. El coordinador compartido ejecuta **Apilado → Histórico → Factor → Clays → Cache**. No se modificaron las fórmulas ni las definiciones SQL, las reglas SRR, el flujo de Datos Conciliados o la transacción del evento PI/TUM. No se implementó iteración por cap. No se realizó promoción ni se tocó PROD.

## Archivos y diff

- `report_export/report_export.py`: Histórico explícito después de Apilado y antes de Factor; verifica materialización antes de seguir; agrupa días realmente recalculados, incluyendo faltantes anteriores a la ventana; pasa `DiasReproceso=0` al refrescador; factor y cache respetan corte operacional, cache con fin+1 exclusivo.
- `report_export/callbacks/reportabilidad_cb.py`: Preview, Excel y PDF conservan el único coordinador y usan su fin operacional exclusivo para consultar el cache del reporte.
- `report_export/tests/test_orquestacion_reporte_turno.py`: orden, corte, fechas dispersas, rango Histórico sin ampliación, fallos y commits previos, consumidores compartidos.
- `report_export/tests/validate_downstream_fase1_dev.py`: validación manual con identidad DEV comprobada en cada conexión, snapshots y comparación de resultados.

[FASE1.diff](FASE1.diff) compara los archivos con su estado inmediatamente anterior a esta fase, preservado en `*.antes`. Excluye cambios preexistentes de otras tareas; el diff global contra Git HEAD también contiene trabajo anterior y no representa por sí solo esta entrega.

El refresco de Histórico no se aproxima al rango solicitado ni amplía siete días: usa `Fecha_Calculo >= inicio SQL de la operación` sobre Control dentro del rango operacional y agrupa únicamente fechas contiguas. La ventana normal existente de Apilado se mantiene. Fuera de ella solo se copia Histórico para fechas que el mantenedor efectivamente materializó. Cada wrapper conserva su conexión/transacción independiente.

## Evidencia DEV persistida

Se ejecutó el coordinador real para `[2026-09-04, 2026-09-10]`, con cache `[2026-09-04, 2026-09-11)`. Resultado: **42/42 checks**, 14 turnos. El guard verificó servidor/máquina DEV y base `inventar_SpcHidr` antes de cada lectura/escritura. El intento inicial dentro del sandbox falló antes de conectar; la ejecución autorizada posterior completó los cinco pasos.

|10-09|Resultado|
|---|---|
|Control TMH A / B / día|41.462 / 42.168 / 83.630|
|Histórico bruto A / B / día|41.462 / 42.168 / 83.630|
|Input bruto original del factor|83.630|
|Factor calculado y aplicado|0,9983502509529375|
|Estado|OK_AJUSTE_KOM|
|TMS cache A / B|39.408,079368 / 40.089,655081|

La [tabla 04–10](COMPARACION.md) muestra por fecha/turno Control, Histórico, fecha de cálculo, factor anterior/nuevo, estado, SP directo, cache, fecha de actualización y diferencia. Todos los deltas TMS directo−cache son menores de 0,000001; el máximo absoluto es aproximadamente 0,0000004633, compatible con redondeo del cache a seis decimales.

Clasificación comprobada contra el SP directo **anterior** al refresco:

- **04, 05, 06:** sin cambio de factor ni TMS del cache; se actualizan timestamps.
- **07-A:** cambio legítimo por factor diario nuevo; el cache anterior coincidía con el SP anterior.
- **07-B y 08 A/B:** reparación del cache que usaba TMH anterior, además del cambio legítimo de factor.
- **09 A/B:** reparación del cache anterior y factor que pasa de 1 a 0,9960450786747628.
- **10 A/B:** el cache anterior ya usaba TMH vigente, pero factor stale=1. El cambio TMS proviene del factor corregido.

Factores nuevos 07 y 08: 0,8197348329929123 y 0,9575324560717768. No se comparan erróneamente los resultados finales con la vista antigua que omite factor V2.

Artefactos: [antes.json](antes.json), [despues.json](despues.json), [coordinador.json](coordinador.json), [checks.json](checks.json). El directo de comparación reutiliza el cuerpo vigente del SP redirigiendo solamente su escritura de trazabilidad a `#traza`, sin ALTER ni persistencia adicional de esa comparación. El refresco real de cache sí conserva los efectos existentes de trazabilidad y Clays de los wrappers.

El hash del conjunto de definiciones visibles `sys.sql_modules` antes/después es idéntico. No se modificó ningún procedimiento o vista, incluidos `sp_reporte_turno_emision_test`, `sp_factor_ajuste_camiones_test` y `v_srr_tms_origen_turno_emision_test`. No se usaron tags SRR.

## Pruebas de fallo y persistencia actual

Comandos y resultados:

- `venv/Scripts/python.exe -m pytest report_export/tests/test_orquestacion_reporte_turno.py report_export/tests/test_factor_ajuste_camiones_report.py monitor_pi_tum -q --disable-warnings`: **85 PASS, 1 SKIP, 0 FAIL; 118 subtests PASS**.
- Focalizada coordinador/factor: **11 PASS, 12 subtests PASS**.
- `venv/Scripts/python.exe -m report_export.tests.validate_downstream_fase1_dev`: **42/42 checks DEV**.
- Suite ampliada `report_export/tests monitor_pi_tum --maxfail=3`: **155 PASS, 3 FAIL, 19 subtests PASS**, detenida en el tercer fallo; no es una suite completa aprobada. Fallos: `test_comentarios_tm3.py::PublicacionSeguraTM3Tests::test_publicar_reconstruye_fuente_viva_antes_del_writer` intenta una conexión SQL no simulada y falla por restricciones de conexión; `test_datos_conciliados_excel.py::test_fecha_corte_informa_columnas_estructurales_faltantes` espera un mensaje que incluya `Camiones_TMS_plan`; `test_pdf_torres_python.py::PdfTorresPythonTests::test_el_semaforo_es_un_circulo_dibujado_y_no_un_glifo` requiere `reportlab`, ausente del venv.
- El fallo de mensaje de Datos Conciliados se reprodujo cargando `report_export.py.antes`: **1 FAIL idéntico**, previo a esta fase. No se modificaron esos tests ni sus funciones ajenas al alcance.

El Python global no tenía pytest; se usó el venv existente. La primera colección ampliada detectó `passlib` ausente; se instaló únicamente esa dependencia en el venv para continuar. No se cambió configuración ni archivos de dependencias del proyecto.

Las pruebas inyectan excepciones ejecutando el coordinador y wrappers reales con conexiones simuladas que modelan commit/rollback al salir de cada contexto. No inyectan fallos destructivos en DEV. Confirman que no se ejecutan pasos posteriores al error.

|Punto de fallo|Queda confirmado bajo el diseño actual|No se actualiza|
|---|---|---|
|Histórico, después de Apilado|Apilado|Histórico revierte su transacción; Factor, Clays, Cache no se ejecutan|
|Factor, después de Histórico|Apilado e Histórico|Factor revierte; Clays y Cache no se ejecutan|
|Clays, después de Factor|Apilado, Histórico y Factor|Clays revierte; Cache no se ejecuta|
|Cache, después de Clays|Apilado, Histórico, Factor y Clays|Cache y su trazabilidad transaccional revierten|

Un fallo de validación de materialización tras Apilado también detiene el proceso antes de Histórico, conservando el commit de Apilado. Un fallo de validación **posterior** al cache no revierte los commits ya realizados. Esta fase no promete atomicidad global.

## Datos Conciliados: cambio pendiente, no implementado

`report_export/callbacks/reportabilidad_cb.py::_refrescar_dependencias_datos_conciliados` sigue ejecutando Histórico → Clays/Cache → `actualizar_datos_conciliados_emision_report`. Dentro de `sp_mantiene_datos_conciliados_emision_test` se mantiene factor V2, por lo que el cache puede quedar construido con el factor anterior.

La corrección futura debe preparar **Histórico → Factor → Clays/Cache → Datos Conciliados**, y verificar que la llamada interna al factor conserve esa fotografía antes de publicar. El mantenedor de Datos Conciliados llama a factor en la línea 92 y lee `reporte_turno_cache_emision_test` en la línea 313 de su definición capturada. Por ello no basta con moverlo antes del cache ni con añadir un cache final después: el primer cambio le haría leer cache anterior y el segundo no repararía sus datos ya materializados. Para el caso normal, se necesita mantener factor explícitamente antes del cache y asegurar que la llamada interna posterior sea numéricamente estable. Si no lo es, se requiere resolver esa coordinación en otra fase antes de publicar. Esta función quedó sin cambios; la solución condicional por cap no forma parte de esta entrega.

## Riesgos y alcance pendientes

- Persistencia parcial entre wrappers: documentada arriba; atomicidad global y conexión común corresponden a otra fase.
- Concurrencia: las fechas recién materializadas se reconocen por timestamp SQL; una ejecución concurrente sobre el mismo rango podría entrar en esa selección o cambiar fuentes entre pasos. No se añadió bloqueo/coordinación global.
- Las fechas anteriores fuera de la ventana que no se recalculan no reparan un Histórico previamente stale. Para una reparación explícita completa se debe dimensionar `dias_reproceso` al rango afectado; la validación 04–10 cubrió los siete días completos.
- Cap, cero o cache ausente pueden requerir otra política; no se añadió cache preliminar ni iteración. El resultado validado corresponde al caso normal diagnosticado.
- No se integró downstream en alta/cierre/TUM tardío, ni se cambió la propagación por humedad/inventario a días vecinos.
- Se verificó el contrato común de Preview/Excel/PDF mediante pruebas; esta fase no incluye inspección visual de los tres formatos.

**Confirmaciones:** DEV únicamente; PROD intacto; fórmulas SQL/SRR intactas; sin cambios de definición SQL; sin cambios de reglas de negocio; sin promoción.
