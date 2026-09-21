# FASE 4B3B — implementación para revisión; no cerrada

No se conectó a DEV ni se ejecutó SQL en esta tarea. No se ejecutó el protocolo manual con `--execute-rollback`. **PROD, SQL/SP, F4D2, Representatividad, SRR, aislamiento y fórmulas intactos.** La validación empírica queda a cargo del equipo, después de revisar esta entrega.

## Arquitectura

Una única `engine.begin()` en `preparar_paquete_datos_conciliados_emision` → coordinador DC con conexión externa → coordinador RTO (adquiere el global Transaction existente) → mantenedor DC → lecturas DC/MTD/Factor/Balance → commit → constructor Preview/Excel. No hay segundo lock manual ni commits internos Python. Un fallo de lectura revierte el refresco RTO/DC y llega al manejo de errores vigente del callback, sin artefacto.

El mantenedor DC conserva calendario completo, `dias_reproceso=0`, `refrescar_factor=False` y la conexión de RTO. RTO conserva su corte operacional y cache con fin exclusivo. No se cambia el coordinador RTO ni el paquete RTO validado en 4B3A.

## Firmas

| Función | Antes | Ahora |
|---|---|---|
| `refrescar_dependencias_datos_conciliados_emision` | `(start_date, end_date)` | `(start_date, end_date, *, conn=None)` |
| `fetch_datos_conciliados_emision_report` | `(start_date, end_date)` | `(start_date, end_date, *, conn=None)` |
| `fetch_factor_ajuste_camiones_report` | `(start_date, end_date)` | `(start_date, end_date, *, conn=None)` |
| `fetch_balance_chancado_report` | `(start_date, end_date)` | `(start_date, end_date, *, conn=None)` |
| `preparar_paquete_datos_conciliados_emision` | No existía | `(start_date, end_date, *, salida)` |

`conn=None` conserva el comportamiento standalone. Con conexión externa se usa `nullcontext(conn)`, sin adquirir otra conexión ni confirmar, revertir o cerrar la recibida. El coordinador devuelve la metadata existente. El paquete devuelve `refresco`, `salida`, `df_datos`, `df_factor`, `df_balance`; Excel añade `df_datos_visible` y `df_resumen_mtd`. Los DataFrames están materializados antes del retorno.

## Fuentes y rangos exactos

| Variante | Lecturas en orden |
|---|---|
| Preview | DC principal → Factor → Balance |
| Excel | DC visible → DC MTD condicional → Factor → Balance |
| PDF | DC principal → Factor → Balance |

Todas usan exactamente la misma conexión/transacción del refresco.

| Fuente | Inicio inclusivo | Fin inclusivo |
|---|---|---|
| DC principal, Preview/Excel | solicitado | solicitado, incluidas fechas futuras |
| DC MTD adicional, Excel | primer día del mes del **inicio solicitado** | solicitado |
| Factor | solicitado | `fecha_corte_operacional` |
| Balance | solicitado | `fecha_corte_operacional` |
| Mantenedor DC | solicitado | solicitado |

MTD adicional solamente cuando el inicio no es día 1; en caso contrario se reutiliza DC principal. La corrección del inicio MTD para rangos que cruzan meses es explícita en el pedido de 4B3B y está probada. No se cambian cálculos MTD ni fórmulas.

RTO sigue recortando hasta corte; cache usa corte + 1 exclusivo. El test mensual con coordinador RTO real sobre conexión simulada verifica 01–30 septiembre para DC y hasta 10 septiembre para Factor, cache hasta 11 exclusivo. El script manual además compara filas de Factor/Cache posteriores al corte antes/después del refresco.

Preview materializa Factor y Balance por el contrato solicitado, aunque sus renderers actuales solamente consumen DC principal. Excel entrega las cuatro fuentes al constructor existente. Ningún renderer hace una lectura tardía agregada por esta fase.

## Archivos y alcance

- `report_export/report_export.py`: los tres fetches, coordinador DC y nuevo paquete.
- `report_export/callbacks/reportabilidad_cb.py`: importación y únicamente ramas `prod` de `generar_reporte`, `exportar_excel`.
- `report_export/tests/test_error_modal_exportacion.py`: mocks en coordinador público DC y fetches del repositorio; ejecuta el paquete real sobre motor simulado. Se conserva el test de orden refresh → datos → factor → balance → exportación, MTD y UI de error.
- `report_export/tests/conftest.py`: bloqueo de conexiones reales durante colección y tests.
- `report_export/tests/test_paquete_datos_conciliados.py`: contratos F4B3B, callbacks reales, errores, rangos, standalone y safe-default.
- `scripts/validate_export_dc_read_coherence_dev.py`: diagnóstico manual preparado, no ejecutado con permiso de escritura.

La rama PDF `prod` est? restaurada exactamente al estado previo a 4B3B. Su defecto previo queda como deuda legacy fuera de alcance; no se arregla ni se habilita PDF. `pdf_generator.py` no se modifica.

[Diff exacto](cambio_completo.diff), relativo a las copias `.antes` tomadas al comenzar esta fase, sin atribuir cambios anteriores del workspace. [Auditoría AST](integridad_ast.json): consultas de los tres fetches idénticas; callbacks fuera de `prod` idénticos; RTO/Representatividad no modificados. `export_to_excel.py` y `pdf_generator.py` sin diff Git.

## Reparación de seguridad solicitada antes de 4B3B

**A. Mensaje `Camiones_TMS_plan`: preexistente/fuera de 4B3A.** `git show HEAD:report_export/export_to_excel.py` ya contiene el mensaje genérico y `campos=faltantes`; el archivo no tiene diff. La expectativa correcta es `DependenciaDatosExportError`, mensaje genérico y `Camiones_TMS_plan` en `.campos`. Esa corrección ya estaba presente en el archivo local al tomar la copia `.antes`; se conservó sin cambios funcionales.

**B. Test que permitió SQL accidentalmente:** `test_datos_conciliados_conserva_orden_oficial_y_factor_es_lectura_posterior`, cuando parcheaba helpers antiguos. Los otros dos tests de callback del mismo archivo también tenían originalmente ese patrón. La versión local encontrada antes de implementar 4B3B ya había cambiado sus mocks al helper DC y agregó un guard de `_get_engine`; los cuatro tests aislados pasaron sin SQL. Para 4B3B los mocks ahora interceptan `repo.refrescar_dependencias_datos_conciliados_emision`, y los tres fetches en `repo`; la transacción del paquete es simulada.

**C. Guard:** antes de recolectar tests se bloquean `Engine.connect`, `Engine.raw_connection`, `Pool.connect` y `pyodbc.connect`, con `AssertionError("SQL REAL NO PERMITIDO EN UNIT TEST")`. Los intentos quedan registrados y causan error al finalizar el test aunque el callback haya capturado la excepción. Intentos durante colección también abortan. Los tests de modal usan motor simulado, cuyo `execute` y `connect` fallan, y bloquean además `db_connection.get_engine`. La suite no necesita DEV.

## Validación automática ejecutada

| Ejecución | PASS | SKIP | FAIL | ERROR |
|---|---:|---:|---:|---:|
| Cuatro aislados de DC, antes de implementar 4B3B, con guard activo | 4 | 0 | 0 | 0 |
| Focalizada: paquete DC + paquete RTO + orquestación RTO/DC + modal completo + Excel DC completo | 103 | 0 | 0 | 0 |
| Nuevos tests DC, pasada final incluyendo prueba adicional del owner externo | 34 | 0 | 0 | 0 |
| Suite `report_export/tests` | 313 | 0 | 7 | 1 |

Los conteos se superponen y no se suman. La pasada final DC agrega una prueba respecto de la colección de la suite amplia/focalizada; no hubo cambios funcionales después de esas ejecuciones. La focalizada reporta además 25 subtests PASS; la amplia, 36 subtests PASS. Las 42840 advertencias son de deprecación del formateador Excel existente.

Comandos/evidencia:

```powershell
.\venv\Scripts\python.exe -m pytest report_export/tests/test_paquete_datos_conciliados.py report_export/tests/test_paquete_reporte_turno.py report_export/tests/test_orquestacion_reporte_turno.py report_export/tests/test_error_modal_exportacion.py report_export/tests/test_datos_conciliados_excel.py -q --disable-warnings
.\venv\Scripts\python.exe -m pytest report_export/tests/test_paquete_datos_conciliados.py -q --disable-warnings
.\venv\Scripts\python.exe -m pytest report_export/tests -q --disable-warnings
```

[Focalizados](tests_focalizados.txt), [DC final](tests_dc_final.txt), [suite amplia con fallos completos](tests_suite.txt). `py_compile` PASS para los seis archivos Python nuevos/modificados. Sin instalar dependencias ni acceder a servidores.

Fallos amplios, fuera del alcance funcional de esta fase:

- `test_comentarios_tm3.py::PublicacionSeguraTM3Tests::test_publicar_reconstruye_fuente_viva_antes_del_writer`: aislamiento incompleto de una prueba de Representatividad. Intentó conexión; el guard la bloqueó **antes de SQL/red**. La aserción del resultado falla y el guard marca adicionalmente ERROR en teardown. No se corrigió Representatividad.
- `test_pdf_torres_python.py::PdfTorresPythonTests::test_el_semaforo_es_un_circulo_dibujado_y_no_un_glifo`: falta `reportlab`.
- `...::test_los_graficos_conservan_la_proporcion_de_la_figura`: misma dependencia ausente.
- `...::test_srr_entrega_una_pagina_con_sus_cuatro_secciones`: misma dependencia ausente.
- `...::test_un_mes_mas_largo_sigue_cabiendo_en_una_pagina`: misma dependencia ausente.
- Dos subcasos (`quimico`, `fisico`) de `...::test_una_pagina_a3_con_las_seis_secciones_sin_solape`: misma dependencia ausente.

La suite amplia no está verde. No se ocultaron fallos ni se modificaron módulos ajenos para resolverlos.

## Script manual pendiente

Sin flag, se ejecutó únicamente:

```text
SAFE: no se conecta ni escribe. Requiere --execute-rollback.
```

El test safe-default bloquea imports SQL y verifica ese resultado. No se importan repositorio/SQLAlchemy/guard DEV antes del flag.

Comandos preparados **NO ejecutados**:

```powershell
.\venv\Scripts\python.exe scripts/validate_export_dc_read_coherence_dev.py --execute-rollback --output scripts/diagnosticos/fase4b3b/manual_dia.json
.\venv\Scripts\python.exe scripts/validate_export_dc_read_coherence_dev.py --execute-rollback --monthly --output scripts/diagnosticos/fase4b3b/manual_mes.json
.\venv\Scripts\python.exe scripts/validate_export_dc_read_coherence_dev.py --execute-rollback --fail-fetch 4 --output scripts/diagnosticos/fase4b3b/manual_fallo_balance.json
```

Fecha diaria: 10–10 septiembre; Excel lee DC 10–10, MTD 01–10, Factor/Balance hasta corte. Mensual: 01–30 septiembre; tres lecturas, sin MTD extra. `--fail-fetch` admite 1..4 en modo diario y 1..3 en mensual.

Se reutiliza el patrón del script RTO validado sin modificarlo: validación de identidad DEV, conexión rollback-only inyectada en el paquete real, bloqueo de commits Python, baseline bajo global antes del primer mantenedor, instrumentación SPID/TRANCOUNT/XACT_STATE/applock en todos los mantenedores y fetches, segunda sesión bloqueada acreditada por DMV y adquisición tras rollback. Se permite que Histórico ejecute múltiples tramos. Se comprueban los rangos de writers/lectores y Factor/Cache futuros sin modificaciones.

Tras materializar todas las fuentes lanza SENTINEL y revierte, luego invoca constructor simulado con frames materializados fuera de SQL. No genera Excel/PDF. En `--fail-fetch` no invoca constructor y compara restauración tras rollback. Hashes exactos de columnas/filas de las siete tablas, incluidos timestamps y decimales sin pérdida. Política IDENTITY heredada: únicamente `Clays_CuFe_trazabilidad.id_trazabilidad`, con before/after/delta registrados; no reseed ni `DBCC CHECKIDENT`. Ese contador puede avanzar aun con rollback: la restauración exacta acreditada corresponde a filas/valores, no a ese contador permitido.

## Riesgos y pendientes

- Falta validación manual empírica de 4B3B. No se declara cerrada.
- Coherencia frente a writers F4 cooperativos; no snapshot absoluto frente a externos que ignoren el global. F4D2 sigue bloqueada.
- Más duración de transacción/lock por las lecturas; potenciales esperas/timeouts. Formateo y PDF permanecen fuera.
- Prueba manual exige guard DEV configurado, permisos DMV y ventana controlada; otro writer entre rollback y snapshot posterior puede producir un FAIL. Presupone SP transaccionales F4 ya validados; no neutraliza efectos externos/no transaccionales nuevos.
- Los tests de PDF mockean el renderer para verificar orquestación; no sustituyen una validación visual ni resuelven la dependencia `reportlab` ausente.
- Persisten los fallos amplios enumerados. Ninguno justifica habilitar SQL real en unit tests.
