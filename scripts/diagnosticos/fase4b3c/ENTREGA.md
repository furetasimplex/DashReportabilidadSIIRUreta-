# FASE 4B3C — implementación para revisión, no cerrada

**No se ejecutó SQL ni se conectó a DEV. No se ejecutó `--execute-rollback`. PROD, F4D2, RTO 4B3A y DC 4B3B intactos.** No se modificaron objetos SQL/SP, consultas de datos, aislamiento, SRR/Torre 3, umbral 0.75, RN-027/RN-028 ni fórmulas Excel/PDF.

## Diseño y ownership

F4C ya tenía un único owner: conexión → mensual Session → commit de adquisición (sin DML) → transacción de datos → global Transaction → RTO → resumen intervalo → representatividad → BD Ton → validación → commit/rollback → release mensual → commit de control → pool. Se extrajo ese mismo owner a `_transaccion_representatividad`, sin duplicar los writers.

El paquete oficial vivo y el paquete del editor ahora usan ese owner y mantienen la transacción de datos abierta hasta materializar las fuentes. `refrescar_representatividad_para_exportacion(..., conn=None)` conserva standalone; con conexión externa el owner debe mantener el mensual y administrar la transacción. El cuerpo de refresco no hace begin/commit/rollback/close ni release propios. Sigue adquiriendo el global antes de determinar corte y reutiliza RTO en la misma conexión, con la reentrada existente del global.

```text
monthly Session Exclusive
  BEGIN datos
    global Transaction Exclusive
    refresh F4C existente
    fetches y validaciones de fuentes
  COMMIT / ROLLBACK
release monthly Session (finally)
comprobar NoLock → terminar transacción de control → devolver conexión
constructor de grilla / workbook / PDF
```

La comprobación nueva usa únicamente `APPLOCK_MODE` después del release: no cambia SQL de negocio. Si release, comprobación o commit de control fallan, se invalida la conexión; no vuelve utilizable al pool con un Session lock incierto. Ante fallo del refresco se preserva el error original aunque falle la limpieza.

Un fallo de lectura/validación del paquete revierte todos sus writers antes del release mensual y no genera artefacto. La construcción/formato y validación del workbook ocurren después del retorno; un fallo allí no revierte el refresh ya confirmado. Un fallo de release posterior a commit invalida la conexión y evita el artefacto, pero tampoco deshace datos ya confirmados.

## Funciones y archivos

En `report_export/report_export.py`:

- Nuevo `_transaccion_representatividad(end_date)`, owner extraído de F4C.
- `refrescar_representatividad_para_exportacion(start_date, end_date, *, conn=None)`.
- `armar_paquete_reporte_torre_oficial(periodo_inicio, periodo_fin)`: firma pública conservada; retorna después del commit y release. Internamente materializa mediante `_materializar_paquete_reporte_torre_oficial(..., conn=...)`.
- Nuevo `preparar_paquete_editor_representatividad(ini, fin, *, periodo_mes=None)`; refresca desde día 1 del mes de `fin`, como hacía el editor.
- `_fetch_fuentes_mensuales_torres_oficial(..., *, conn=None)` transmite la conexión a cada fuente mensual/FY.
- Fetches con nuevo `*, conn=None`: `fetch_representatividad_torres_report`, `fetch_pesos_representatividad_report`, `fetch_bd_ton_report`, `fetch_estado_apilado_turno_representatividad`, `fetch_gestion_representatividad_fy`, `fetch_comentarios_representatividad_periodo`, `fetch_reporte_torre_oficial_detalle`.

Con `conn` externa los fetches usan esa conexión sin cerrarla ni administrar transacciones. Sin ella conservan standalone, incluida compatibilidad DBAPI de BD Ton/Gestión FY. El fallback BD Ton dentro de representatividad recibe también la conexión externa. No se altera selección, ordenamiento ni transformación de datos.

En `report_export/callbacks/reportabilidad_cb.py` solamente cambiaron:

- `_cargar_detalle_representatividad_periodo`: obtiene fuentes/comentarios del paquete del editor y construye el detalle después del retorno. Si recibe un paquete desde publicación, reutiliza sus fuentes y mantiene los comentarios del editor como antes.
- `_construir_fuente_unica_representatividad`: obtiene primero el paquete; los comentarios persistidos ya vienen materializados. Si el caller aporta un mapa en memoria, sigue teniendo precedencia. Construye workbook/PDF después de cerrar SQL.

Los callbacks RTO/DC, descargas históricas, publicación del snapshot y renderers no se modificaron. El helper antiguo `_fetch_fuentes_mensuales_torres` se conserva; la ruta viva ya no lo usa para abrir conexiones independientes.

Tests modificados: `test_refresco_representatividad.py` adapta la frontera del editor y verifica la comprobación de release; `test_comentarios_tm3.py` completa el mock de la lectura de detalle después de publicar, que anteriormente intentaba SQL real. Nuevo `test_paquete_representatividad.py`. El guard global existente de tests permanece intacto.

[Diff exacto](cambio_completo.diff) · [Auditoría AST y consultas](integridad_ast.json). Comparación contra copias `.antes` al iniciar esta fase, preservando modificaciones previas del workspace.

## Fuentes exactas por ruta

| Ruta | Fuentes |
|---|---|
| Preview/editor vivo | BD Ton mensual; estado por turno/material; Gestión FY química; Gestión FY física; detalle/comentarios persistidos del mes si corresponde |
| Paquete oficial vivo para publicación y constructor Excel vivo | Representatividad; pesos por turno; BD Ton FY; BD Ton mensual; estado por turno/material; Gestión FY química; Gestión FY física; comentarios persistidos |
| PDF vivo químico/físico/SRR | El mismo paquete oficial vivo; workbook y renderer después de terminar SQL y liberar locks |
| Botón Excel oficial activo e histórico | Snapshot persistido por `id_reporte`, cabecera y detalle. **No ejecuta refresh vivo**, antes ni después de esta fase |
| PDF histórico por `id_reporte` | Snapshot, cabecera, detalle; no se cambia su ruta ni se introduce refresh |

No se convirtió la descarga Excel oficial en un refresh vivo. El helper de construcción Excel vivo comparte paquete con PDF/publicación; se prueban ambos contratos por separado.

Rangos conservados:

- Paquete oficial: exige mes calendario completo como antes. Representatividad/pesos: inicio del mes → corte, inclusivo. Calendario en memoria: inicio → fin del mes solicitado.
- BD Ton FY: inicio del FY obtenido con la función existente → corte inclusivo.
- BD Ton mensual: día 1 del mes de `fin` → corte inclusivo.
- Estado: día 1 → corte + 1 **exclusivo**.
- Gestión FY: mismo año fiscal, tipo QUIMICO/FISICO, COMBINADO, objetivo 0.85 y corte existentes. No cambia el umbral de representatividad 0.75.
- Editor: refresco desde día 1 del mes de `fin` hasta su corte; conserva el fin solicitado para formar su calendario. Selección de comentarios conserva `periodo_mes` explícito o validación de mes completo.

Los comentarios pertenecen al reporte vivo y se movieron dentro del prepare/read. Ya no se leen antes del paquete PDF ni después del release del editor. Un error SQL de comentarios ahora aborta el paquete; un resultado vacío sigue siendo válido.

## Histórico y límites de la garantía

`fetch_reporte_torre_oficial_snapshot` consulta payloads en una conexión y llama después a `fetch_reporte_torre_oficial_cab`, que usa otra. Las descargas leen luego detalle en otra conexión. Cabecera/detalle filtran `activo=1`; payloads se buscan por id. Son consultas separadas bajo el aislamiento vigente, sin refresh.

Una republicación o eliminación concurrente podría cambiar `activo` entre consultas y producir metadata/detalle ausentes respecto del snapshot ya leído. Se clasifica como **deuda separada del histórico**, sin refactorizarla aquí. El escritor `write_reporte_torre_oficial` conserva su transacción independiente posterior a la preparación del paquete; no se hizo atómica publicación + refresh.

Los locks protegen frente a writers F4 cooperativos, no dan snapshot absoluto. En particular, los escritores de cabecera/detalle histórico no adquieren estos locks en la función inspeccionada: leer comentarios dentro del paquete evita la ventana adicional del caller, pero no convierte a esos escritores en cooperativos. Ese límite queda explícito y no se amplía el alcance al histórico.

## Validación automática

- `py_compile`: PASS en los seis archivos Python nuevos/modificados.
- Modo SAFE del script: PASS, salida exacta `SAFE: no se conecta ni escribe. Requiere --execute-rollback.`
- Tests finales del paquete: **32 PASS, 0 SKIP, 0 FAIL**. [Log](tests_paquete_final.txt).
- Regresión focalizada Representatividad/F4C/Excel/PDF/RTO/DC: **175 PASS, 0 SKIP, 6 FAIL**, 32 subtests PASS. Los seis fallos corresponden exclusivamente a `reportlab` ausente. [Log](tests_regresion.txt). Esta colección precedió al último test adicional de descarga histórica, incluido en los 32 finales.
- Se ejecuta una única suite amplia al final; su resultado se registra en [tests_suite_final.txt](tests_suite_final.txt).

El paquete nuevo prueba owner F4C real sobre conexiones simuladas: una conexión, mensual antes del refresh, global/reentrada, ambos locks en cada fetch, calendario/rangos, fallback BD Ton, compatibilidad standalone, rollback por cada una de las ocho lecturas oficiales/cinco del editor, invalidación ante release incierto, y grilla/workbook/PDF después del retorno al pool. Los constructores se simulan en las pruebas de orquestación; el render real tiene pruebas separadas que requieren `reportlab`.

Los tests históricos de PDF no se eliminaron ni se saltaron para ocultar la dependencia. No se instaló `reportlab` ni se modificó lógica ajena para dejarlos verdes. No hubo conexiones reales: se mantuvieron guards SQLAlchemy/ODBC durante colección y ejecución.

## Script manual preparado, no ejecutado contra DEV

`scripts/validate_export_representatividad_read_coherence_dev.py` reutiliza el owner F4C real y lanza SENTINEL dentro de él después de materializar las fuentes. El owner hace rollback y release; el script comprueba `NoLock` global/mensual antes del pool. Un hook adicional impide commit de datos si el SENTINEL no se alcanza.

Con flag valida identidad DEV en las conexiones. Registra SPID/TRANCOUNT/XACT_STATE/global/mensual en los ocho mantenedores (Histórico puede ejecutar varios tramos), corte y fetches. Arranca segunda sesión al primer fetch del paquete, acredita espera mediante DMV por el global y verifica adquisición global/mensual después del rollback/release. La segunda sesión también revierte y libera explícitamente el mensual. Se usa constructor simulado, sin producir Excel/PDF.

Inventario de diez tablas reutilizado de `scripts/validate_representatividad_atomicity_dev.py`: seis capas RTO, `trazabilidad_analitos_tm_emision_test`, `Resumen_Intervalo_TotTM`, `representatividad_torres_resultado`, `BD_Ton`. Baseline bajo ambos locks antes del primer mantenedor; compara columnas, count y SHA-256 exacto de todas las filas, preservando decimales y auditoría.

La lista IDENTITY **se inspeccionó en evidencia local**, no se asumió: `report_export/exports/fase4c/manual_dev.json`, `identities_antes/despues`, registra únicamente `Clays_CuFe_trazabilidad.id_trazabilidad`. Se reutiliza su política de avance auditada en 4B3A, registrando before/after/delta. La comprobación runtime contra `sys.identity_columns` ocurre antes de writers; cualquier identidad distinta falla. Sin reseed ni DBCC. Las filas deben restaurarse exactamente; el contador permitido puede avanzar.

Comandos preparados **no ejecutados** (período fijo 01–30 septiembre 2026):

```powershell
.\venv\Scripts\python.exe scripts/validate_export_representatividad_read_coherence_dev.py --execute-rollback --output scripts/diagnosticos/fase4b3c/manual_oficial.json
.\venv\Scripts\python.exe scripts/validate_export_representatividad_read_coherence_dev.py --execute-rollback --editor --output scripts/diagnosticos/fase4b3c/manual_editor.json
.\venv\Scripts\python.exe scripts/validate_export_representatividad_read_coherence_dev.py --execute-rollback --fail-fetch 2 --output scripts/diagnosticos/fase4b3c/manual_fallo.json
```

`--fail-fetch` usa el ordinal real registrado, incluido fallback BD Ton si aparece. Si el ordinal no se alcanza, se revierte y reporta FAIL. El script rechaza sobrescribir evidencia existente. El modo sin flag no importa repositorio ni herramientas SQL, probado con imports SQL bloqueados.

## Pendientes

- Validación manual real DEV de 4B3C pendiente; no se declara cerrada.
- Mayor duración del lock/transacción por lecturas FY/pesos/detalle; puede aumentar esperas y timeout.
- Ventana controlada y permisos DMV necesarios para el protocolo; escrituras externas/no cooperativas no están neutralizadas. Los SP deben conservar el contrato transaccional F4 ya validado.
- Restauración posterior podría diferir si otro writer legítimo confirma entre rollback y snapshot posterior; no ejecutar la prueba con operación concurrente ajena al contendiente controlado.
- Deuda histórica y dependencia PDF descritas arriba. RTO/DC PDF continúan fuera de alcance.
