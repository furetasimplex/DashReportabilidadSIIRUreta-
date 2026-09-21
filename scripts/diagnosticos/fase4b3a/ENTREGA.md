# FASE 4B3A — implementada, pendiente de validación manual DEV

No se declara cerrada ni se promueve. No se modificaron SQL, fórmulas, SRR, aislamiento, Datos Conciliados, Representatividad ni 4D2. No se tocó PROD ni se ejecutó el protocolo manual de escritura.

## Diseño y archivos

`report_export/report_export.py`: nueva `preparar_paquete_reporte_turno_emision(start_date, end_date, *, salida="preview")`. Valida rango y variante antes de abrir una única `engine.begin()`, llama al coordinador RTO con esa conexión, materializa los DataFrames y retorna después del commit. Conserva el applock Exclusive/Transaction del coordinador hasta terminar las lecturas; no adquiere otro lock. Un error de lectura sale del bloque y revierte también el refresco.

Seis fetches incorporan `*, conn=None`: `fetch_reporte_turno_cache_emision`, `fetch_clays_cufe_report`, `fetch_trazabilidad_analitos_report`, `fetch_curva_granulometrica_report`, `fetch_generador_reporte_diario_emision`, `fetch_reconstitucion_srr_report`. Con conexión externa usan `nullcontext`, sin abrir/cerrar/confirmar otra conexión. Sin conexión conservan la adquisición standalone. SQL y transformaciones conservados.

`report_export/callbacks/reportabilidad_cb.py`: únicamente importación y ramas RTO de `generar_reporte`, `exportar_excel`, `generar_pdf`. Construcción Dash/workbook/PDF posterior al retorno del paquete. Se conserva el manejo de errores y de cache vacío. No hay consultas SQL en el constructor del workbook.

`report_export/tests/test_paquete_reporte_turno.py`: tests de conexión, orden, transacción/lock simulados, rangos, fuentes, fallo en cada lectura y compatibilidad standalone. Ejecuta las sentencias reales de las ramas Excel/PDF hasta el constructor, con dependencias simuladas, comprobando commit antes del constructor y ausencia de artefacto ante error. No constituye prueba empírica del applock SQL.

`report_export/tests/test_orquestacion_reporte_turno.py`: adapta el reconocimiento de los tres consumidores al nuevo paquete común.

`scripts/validate_export_rto_read_coherence_dev.py`: protocolo manual descrito abajo.

Diff exacto relativo al estado inicial de esta tarea: [cambio_completo.diff](cambio_completo.diff). Respeta cambios previos del workspace. Copias `.antes`, diffs individuales e [integridad_ast.json](integridad_ast.json) permiten revisar el alcance; solamente cambiaron las siete funciones indicadas del repositorio y los tres callbacks.

## Fuentes y rangos preservados

| Variante | Fuentes |
|---|---|
| Preview | Cache |
| Excel | Cache → Clays → Trazabilidad analitos → Curva → Generador → Reconstitución SRR → Generador mensual condicional |
| PDF (incluidas sus variantes de hoja) | Cache → Generador |

Cache: inicio solicitado y `refresco["fin_sql_exclusivo"]`. Auxiliares: inicio solicitado y fin solicitado + 1 día. Generador mensual: primer día del mes de inicio y fin solicitado + 1 día, únicamente si el inicio no es día 1; de lo contrario reutiliza el DataFrame del generador. Cache vacío evita lecturas auxiliares en Excel/PDF, como antes. No altera corte operacional ni reproceso del coordinador.

## Validación ejecutada

- `venv\Scripts\python.exe -m py_compile` sobre los cinco archivos Python nuevos/modificados: PASS.
- `venv\Scripts\python.exe -m pytest report_export/tests/test_paquete_reporte_turno.py report_export/tests/test_orquestacion_reporte_turno.py report_export/tests/test_refresco_representatividad.py report_export/tests/test_reconst_mod_srr.py -q --disable-warnings`: **73 PASS, 0 SKIP, 0 FAIL**, además 29 subtests PASS.
- `python scripts/validate_export_rto_read_coherence_dev.py`: SAFE, sin conexión ni escritura. También probado bloqueando imports SQL en un test.
- Suite amplia `venv\Scripts\python.exe -m pytest report_export/tests -q`: **280 PASS, 0 SKIP, 11 FAIL**, 36 subtests PASS. Esta ejecución fue anterior a depurar cinco combinaciones PDF sin fuente aplicable del test parametrizado y a agregar el test safe-default; por eso no se deben sumar sus conteos al resultado focalizado final.

Fallos de la suite amplia, no corregidos por estar fuera del alcance:

1. `test_comentarios_tm3.py::PublicacionSeguraTM3Tests::test_publicar_reconstruye_fuente_viva_antes_del_writer`: intenta conexión SQL no simulada; falló al conectar por ODBC/SSL.
2. `test_datos_conciliados_excel.py::test_fecha_corte_informa_columnas_estructurales_faltantes`.
3. Tres tests en `test_error_modal_exportacion.py`: `test_datos_conciliados_conserva_orden_oficial_y_factor_es_lectura_posterior`, `test_datos_conciliados_rango_parcial_lee_mtd_desde_dia_uno`, `test_dependencia_datos_abre_modal_con_contexto_ux`.
4. Cuatro tests y dos subcasos de `test_una_pagina_a3_con_las_seis_secciones_sin_solape` en `test_pdf_torres_python.py`: falta `reportlab`.

No se afirma suite completa verde ni se atribuyen todos los fallos a una causa validada contra baseline ejecutable. No se habilitó acceso SQL para resolver la prueba que intentó conectarse. El Python global no tiene pytest; se utilizó el venv del proyecto.

## Protocolo manual pendiente (no ejecutado)

En una ventana DEV sin otros procesos operativos, con configuración DEV vigente y permiso DMV para observar la otra sesión:

```powershell
.\venv\Scripts\python.exe scripts\validate_export_rto_read_coherence_dev.py --execute-rollback
.\venv\Scripts\python.exe scripts\validate_export_rto_read_coherence_dev.py --execute-rollback --fail-fetch 3 --output scripts/diagnosticos/fase4b3a/manual_dev_fail3.json
```

`--fail-fetch` admite 1..7. Fecha fija 2026-09-10; variante Excel, sin generar workbook. El script fuerza un engine rollback-only en el paquete real; el guard valida servidor/base DEV en ambas conexiones. Bloquea commits Python. Toma baseline bajo el global, antes del primer mantenedor. Registra SPID, TRANCOUNT, XACT_STATE y applock en etapas del refresco y cada fetch. Inicia segunda sesión y comprueba mediante DMV que espera por la primera; falla si adquiere antes de terminar. Tras siete fuentes lanza SENTINEL y revierte; la variante fallida revierte al error de fetch. El constructor simulado solamente se acredita fuera del bloque SQL, tras rollback deliberado; no implica que el callback continúe después de un error real.

Verifica adquisición del segundo lock tras rollback y compara columnas, número de filas y hash SHA-256 de todas las filas/valores de las seis tablas requeridas (incluye fechas de auditoría, sin convertir decimales a float). Ambas sesiones revierten. Escribe evidencia local JSON; PASS exige comparación exacta. Si detecta IDENTITY en esas tablas aborta antes de los mantenedores, porque su contador no se restaura con rollback. No modifica definiciones SQL. Ante un error inesperado conserva el diagnóstico FAIL y revierte la conexión; esa salida no acredita todos los checks posteriores.

## Riesgos pendientes

- Garantía frente a writers F4 cooperativos, no snapshot absoluto: READ COMMITTED sigue vigente y writers externos que ignoren el applock quedan fuera. 4D2 sigue bloqueada.
- Lock/transacción duran ahora también todas las lecturas; pueden aumentar esperas, timeout y retención de recursos. No incluyen formateo ni conversión PDF.
- La prueba manual debe acreditar el contrato SQL real, espera de segunda sesión y restauración; aún no existe esa evidencia de 4B3A.
- El protocolo presupone los SP transaccionales previamente validados de F4. No puede revertir efectos externos/no transaccionales introducidos posteriormente. Detiene el caso conocido de IDENTITY; no reseedea ni modifica objetos.
- La comparación posterior requiere una ventana controlada: otro writer legítimo entre rollback y snapshot puede producir un FAIL por cambio concurrente.
- Pendientes los fallos amplios enumerados. No se modifican otras fases para hacerlos pasar en esta entrega.
