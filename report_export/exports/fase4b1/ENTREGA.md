# FASE 4B1 — refresco atómico de Reporte por Turno

Implementada únicamente la atomicidad y exclusión del refresco normal. No se avanzó a FASE 4B2. No se ejecutaron conexiones SQL, exportaciones reales, mantenedores reales ni modificaciones de datos en esta fase. No hubo commit ni push.

## Archivos modificados y diff

- `report_export/report_export.py`: conexión externa opcional en los cuatro wrappers y en la consulta de corte; helper privado del lock; coordinador con una sola transacción externa.
- `report_export/tests/test_orquestacion_reporte_turno.py`: contratos de conexión/orden/rollback/standalone y conservación de fechas; corrección de una expectativa preexistente del número de consumidores.

[FASE4B1.diff](FASE4B1.diff) compara exclusivamente con la fotografía inmediatamente anterior a esta fase, guardada en `*.antes`. No incluye cambios anteriores del workspace.

## Firmas

Se agregó el argumento opcional **keyword-only `conn=None`**, conservando todos los parámetros posicionales y valores previos:

```python
refrescar_historico_apilado_report(start_date, end_date, dias_reproceso=0, *, conn=None)
actualizar_apilado_tmh_v2_report(start_date, end_date, dias_reproceso=7, *, conn=None)
actualizar_factor_ajuste_camiones_v2_report(start_date, end_date, dias_reproceso=0, *, conn=None)
actualizar_reporte_turno_cache_emision(start_date, end_date, *, conn=None)
fetch_fecha_corte_apilado_tmh_report(start_date, end_date, *, conn=None)
```

El coordinador conserva su firma pública. No se agregaron parámetros a validadores en memoria ni a funciones de Datos Conciliados.

Con conexión recibida, `nullcontext(conn)` utiliza exactamente ese objeto sin abrir/cerrar conexión ni hacer begin/commit/rollback. Sin conexión, se conserva el contexto anterior: Apilado, Histórico y Factor abren su propia transacción; el wrapper Clays/cache abre una transacción por paso; la lectura de corte abre una conexión de lectura. Los bloques de manejo de errores existentes siguen relanzando sus excepciones y no continúan tras fallar.

## Transacción y lock

`report_export.py:2087`, `_adquirir_lock_refresco_turno(conn)`, usa exactamente:

- Resource: `SIIR_CONTINGENCIA_PI_APILADO_DEV`.
- LockMode: `Exclusive`.
- LockOwner: `Transaction`.
- LockTimeout: `10000` ms.

Resultado negativo o ausente genera RuntimeError claro; los errores SQL también se propagan. No hay retry ni liberación manual. No se importa `monitor_pi_tum.db` ni se crea un módulo compartido nuevo.

En `refrescar_dependencias_reporte_turno_emision`, línea 2111, un único `with _get_engine().begin() as conn` contiene:

1. Adquisición del lock.
2. Consulta de corte operacional en esa conexión.
3. Apilado y lectura de fechas materializadas.
4. Histórico únicamente para grupos materializados, `DiasReproceso=0`.
5. Factor hasta corte operacional, `DiasReproceso=0`.
6. Clays con corte 2026-08-01.
7. Cache con fin operacional + 1 exclusivo.
8. Lectura y validación final del cache.

No hay commits manuales o intermedios Python. El retorno dentro del `with` solo llega al caller después de salir correctamente del contexto. Un error de etapa o validación sale con excepción y revierte la transacción externa. Se conserva el comportamiento SQL ya diagnosticado: los COMMIT internos anidados no confirman la transacción externa; un ROLLBACK global de Clays/cache aborta toda la unidad y la excepción impide continuar.

## Tests y evidencia

Ejecutado con el venv existente:

```text
python -m py_compile report_export/report_export.py
python -m pytest report_export/tests/test_orquestacion_reporte_turno.py
                 report_export/tests/test_factor_ajuste_camiones_report.py
                 report_export/tests/test_refresco_representatividad.py
                 monitor_pi_tum -q --disable-warnings
```

Resultado: **106 PASS, 1 SKIP, 0 FAIL; 138 subtests PASS**. `py_compile` y `git diff --check`: OK. El SKIP es la prueba de lectura SQL DEV que requiere activación explícita, no ejecutada por las restricciones de esta fase.

Cobertura:

- `test_periodos_y_orden`: todos los wrappers reciben el mismo `conn`, una sola apertura `begin`, sin conexiones auxiliares; conserva casos de corte y fin solicitado más allá del corte.
- `test_una_conexion_lock_orden_y_commit_despues_de_validar`: ejecuta wrappers y consulta de corte reales sobre conexión simulada; verifica `begin → lock → corte → Apilado → Histórico → Factor → Clays → Cache → validación → commit`.
- `test_fallo_cualquier_etapa_revierte_todo_y_detiene_downstream`: inyecta fallo en cada uno de los cinco mantenedores y en validación final; confirma cero pasos confirmados y ausencia de llamadas posteriores.
- Lock: códigos negativos/None y excepción SQL impiden incluso consultar el corte; se propaga el error sin reintentar.
- Standalone: cuatro wrappers conservan sus aperturas anteriores; con conexión externa no llaman a `_get_engine`, begin ni commit propios.
- Corte: usa conexión externa cuando se proporciona y conserva lectura standalone.
- Clays: casos anteriores a agosto y rango que cruza el 01-08; cache conserva intervalo semiabierto.
- Histórico: fechas antiguas faltantes se agrupan sin ampliar huecos; factor no pasa el corte; validación de apilado/cache conserva bloqueos existentes.

Las pruebas simulan transacciones y ejecución SQL. No sustituyen una validación futura de rollback/concurrencia real del coordinador nuevo; no se realizaron escrituras DEV para obtenerla.

### Fallo preexistente

Antes de editar: suite coordinador/factor/monitor = **89 PASS, 1 SKIP, 1 FAIL; 125 subtests PASS**. Fallaba `test_consumidores_comparten_orquestacion` porque esperaba tres consumidores y actualmente hay cuatro: Preview, Excel, PDF y el helper de Datos Conciliados incorporado en FASE 2. Se corrigió la expectativa a esos cuatro nombres explícitos; no se cambió el flujo DC.

## Integridad y límites

[integridad.json](integridad.json) confirma que solo cambiaron las seis funciones autorizadas preexistentes (más el helper nuevo), que `actualizar_datos_conciliados_emision_report` y Representatividad son textualmente idénticas y que los hashes de callbacks y ambos archivos PI/TUM son iguales antes/después.

**Datos Conciliados quedó intacto**, incluido `refrescar_factor=False` y su calendario completo. Al reutilizar el coordinador común, su preparación de Reporte por Turno ahora es atómica; el mantenedor propio DC sigue fuera de esa transacción como antes. No se afirma atomicidad de toda la ruta DC.

**Callbacks, Representatividad, definiciones SQL, fórmulas, reglas SRR y PROD quedaron intactos.** PI/TUM de FASES 3/4A no fue modificado. La configuración del engine se conserva; no hubo conexión ni promoción a otro ambiente.

La protección termina al salir del coordinador. Las lecturas posteriores de exportación y los writers secundarios que no usan el lock global siguen fuera de esta garantía. Los wrappers standalone conservan deliberadamente su comportamiento previo y no adquieren por sí mismos el lock global. Estos límites corresponden a las fases posteriores, no implementadas aquí.
