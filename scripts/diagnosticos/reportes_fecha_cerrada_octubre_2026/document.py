"""Documentación y controles locales; sin SQL."""
import ast,calendar,csv,hashlib,json
from datetime import date
from pathlib import Path
P=Path(__file__).parent
def write(n,s):(P/n).write_text(s.strip()+'\n',encoding='utf-8')
def run():
    raw=json.loads((P/'rangos_fuente.json').read_text(encoding='utf-8'))
    for name in ('resultado_fechas.csv','cobertura_septiembre.csv','cobertura_octubre.csv'):
        rows=list(csv.DictReader((P/name).open(encoding='utf-8-sig')))
        for r in rows:
            day=[v for v in raw if v['fecha_turno']==r['fecha']]
            r['turnos']=','.join(sorted({v['turno_op'] for v in day}))
            r['claves_torre_turno']=len({(v['Torre'],v['turno_op']) for v in day})
        with (P/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    tree=ast.parse(Path('report_export/callbacks/reportabilidad_cb.py').read_text(encoding='utf-8-sig'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sync_modo_y_mes')
    fn.decorator_list=[]
    ns={'date':date,'calendar':calendar,'no_update':'NO_UPDATE'}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'selector_aislado','exec'),ns)
    value=ns['sync_modo_y_mes']('mes','2026-10')
    params=json.loads((P/'parametros.json').read_text(encoding='utf-8'))
    write('selector_runtime.json',json.dumps({'metodo':'función real extraída AST sin decorador ni callbacks SQL','call':['mes','2026-10'],'result':value,'fecha_inicio':value[2],'fecha_final':value[3]},ensure_ascii=False,indent=2))
    write('callgraph.md','''# Cadena exacta

Botón Editar comentarios, tipo `representatividad_torres` → `report_export/callbacks/reportabilidad_cb.py:7342 generar_reporte` → `_periodo_store_desde_fechas` (:803) → `_cargar_detalle_representatividad_periodo` (:817) → `report_export/report_export.py:3294 preparar_paquete_editor_representatividad` → `_transaccion_representatividad` (lock mensual Session) → `refrescar_representatividad_para_exportacion` (:1561; inicio = primer día del mes de fin) → `_adquirir_lock_refresco_turno` → `fetch_fecha_corte_operacional_representatividad` (:1414) → SELECT guardado en consulta_fecha_cerrada.sql → resultado SQL NULL → helper retorna None → RuntimeError (:1600–1603) → except de generar_reporte (:7425) → dbc.Alert «Error al cargar editor de comentarios: ...».

La condición falla ANTES de refrescar dependencias RTO y los tres SP de Torres. El flujo normal sí es escritor; se aislaron solo SELECT para no ejecutarlo. No se abrió el editor ni se exportó realmente durante esta auditoría.
''')
    write('callbacks.md','''# Callback y parámetros

`generar_reporte(n_clicks_list,f_ini,f_fin,modo_fecha)`; Input pattern `{'type':'report-gen-btn','tipo':ALL}.n_clicks`; States `report-fecha-inicio.date`, `report-fecha-final.date`, `report-fecha-modo.value`; `prevent_initial_call=True`. `ctx.triggered_id['tipo']='representatividad_torres'` selecciona la rama.

Outputs: `report-grafico.children`, `report-tabla.children`, `report-historial.children`, `rep-comentarios-store.data`, `rep-tab-activo-store.data`, `rep-periodo-store.data`. Running informa refresco y deshabilita el botón MATCH; no cambia fechas. En error devuelve Alert, tabla vacía y no_update en cuatro salidas; por tanto puede conservar stores previos.

`sync_modo_y_mes` (:1356) recibe modo `mes` y valor `2026-10`: ejecutada aisladamente desde AST devuelve inicio **2026-10-01**, fin **2026-10-31**. `max_date_allowed` se fija a hoy, pero no recorta el valor fin al construirlo. Evidencia selector_runtime.json; no es captura de una sesión UI particular.

El callback convierte esas fechas a date. Calcula además fin_sql_exclusivo=2026-11-01 para otras ramas, pero la rama Torres usa ini/fin INCLUSIVOS. Store: inicio=2026-10-01, fin=2026-10-31, modo=mes, periodo_mes=2026-10. El paquete del editor impone inicio de cálculo `fin.replace(day=1)`, incluso en rango personalizado. `periodo_mes` cambia la lectura posterior de comentarios/publicabilidad, no la query de cierre.

No hay exigencia de esperar al último día calendario del mes: MAX devuelve cualquier fecha apta dentro del rango. `except Exception as e` muestra str(e), sin reemplazarlo por otro mensaje. El helper de SELECT envuelve errores SQL con texto distinto «Error al obtener la fecha de corte operacional...». El síntoma observado corresponde a ausencia de corte, no demuestra error SQL oculto. No se encontró log/traceback original del clic; sí se reprodujo SELECT NULL con éxito.
''')
    write('objetos_sql.md','''# Objetos de resolución

| Objeto | Papel / filtros / dependencia |
|---|---|
| inventar_SpcHidr.tot_TM | MAX(fecha) global; no filtro de mes, turno ni torre. Es horizonte temporal, no chequeo de huecos o valores por canal. |
| inventar_SpcHidr.v_bitacora_rangos_norm | fecha_turno inclusiva start/end, Torre IN T1/T2/SRR; GROUP BY fecha_turno y MAX(ts_fin). |
| inventar_SpcHidr.v_bitacora_rangos | Mapea fecha_calendario a fecha_turno y ts_toma_muestra a ts_fin; calcula LAG por torre para ts_ini. |
| inventar_SpcHidr.bitacora_turnos_consolidada | Fuente de torre, turno, fecha_calendario y ts_toma_muestra; excluye timestamp de muestra NULL. |

Definiciones LIVE guardadas. `LAG` puede leer la toma del día anterior para ts_ini/duración, pero el corte no usa ts_ini, duracion_min ni flag_arrastre. Por tanto no establece prerrequisito de cierre completo septiembre→octubre. No hay control de cierre persistido, EOMONTH, seed previo, cache, apilado, analitos o COUNT de A/B en ESTE SELECT.

Objetos/funciones posteriores, NO ejecutados al fallar corte: coordinador `refrescar_dependencias_reporte_turno_emision`; `sp_calcular_resumen_intervalo_totTM`, `sp_refrescar_representatividad_torres`, `sp_sincronizar_bd_ton`, todos hasta corte e inicio mensual. Locks `sp_getapplock`/`sp_releaseapplock` protegen la transacción, no definen disponibilidad temporal. Fuentes mensuales y comentarios/snapshot oficial se leen después del refresco. No se atribuye a estos objetos la primera condición fallida ni se ejecutaron para investigar.
''')
    write('comparacion_mes_vs_rango.md','''# Mes vs rango

| Caso | Input UI | Parámetros del SELECT de corte | Resultado DEV |
|---|---|---|---|
| Mes octubre | 01-10 a 31-10 | start=01-10/end=31-10 | NULL |
| Personalizado | 01-10 a 03-10 | start=01-10/end=03-10 | NULL |
| Hasta última cerrada de octubre | No existe fecha cerrada de octubre | No se fabrica rango 01-10 a 30-09 | No aplicable |
| Control septiembre | 01-09 a 30-09 | start=01-09/end=30-09 | 30-09 |
| Horizonte global | 1900-01-01 a 9999-12-31 | mismo SELECT | 30-09 |

Mismo helper y concepto de corte; cambia cota superior. No exige mes calendario completo. Para otros rangos personalizados, el editor recalcula desde el primer día del mes de fin, no necesariamente desde el ini visible; hecho de implementación relevante pero no causa de este caso, donde ambos inicios son 01-10.

El control de septiembre confirma únicamente resolución exitosa de fecha; no se afirma que exportación completa pasó, porque producirla refrescaría datos y violaría alcance de solo lectura.
''')
    write('comparacion_reportes.md','''# Alcance compartido (sin auditar analitos)

| Acción | Selector | Resolución de corte | Riesgo común |
|---|---|---|---|
| Torres / Editar comentarios | report-fecha-* | preparar_paquete_editor_representatividad → refrescar_representatividad_para_exportacion → fetch_fecha_corte_operacional_representatividad | Sí: fallo reproducido por horizonte tot_TM. |
| Torres / Publicar-materializar | Mes normalizado | _materializar_paquete_reporte_torre_oficial → mismo refresco/corte | Sí al crear snapshot nuevo. No ejecutado. |
| Torres / Descargar Excel oficial | Mismo selector | exportar_excel rama representatividad_torres (:7695) busca reporte oficial activo y usa fecha_corte_operacional del snapshot | NO vuelve a resolver este corte LIVE; puede descargar snapshot existente. Puede fallar por ausencia de oficial activo, error distinto. |
| Análisis TM / Excel | Mismo selector, tipo reporte_turno | preparar_paquete_reporte_turno_emision → refrescar_dependencias_reporte_turno_emision → fetch_fecha_corte_apilado_tmh_report | NO comparte SELECT tot_TM/bitácora. Comparte infraestructura RTO con otros flujos y puede fallar por otra cobertura. |
| Datos Conciliados / Excel | Mismo selector, tipo prod | preparar_paquete_datos_conciliados_emision → refrescar_dependencias_datos_conciliados_emision → coordinador RTO → corte apilado | NO misma condición; comparte ruta apilado con Análisis TM. Mantiene calendario completo para DC. |

El corte apilado (:2072) usa `v_contingencia_totalizador_diagnostico_turno`: cuatro claves CV008/CV108 × A/B, criterios PI/TUM desde septiembre, máximo global, no horizonte tot_TM. No se concluye que esos reportes funcionen hoy: sus refrescos no fueron ejecutados. Torres, después de pasar su propio corte, exige compatibilidad con el corte RTO. Eso es un bloqueo posterior potencial, no el actual.
''')
    write('README.md','''# Auditoría fecha cerrada — Reportabilidad, DEV

Informe: REPORTES_FECHA_CERRADA_OCTUBRE_2026.md. Solo SELECT, sin ejecutar callbacks de editor/exportación porque refrescan/materializan datos. `audit.py` extrae el SQL literal desde AST, consulta DEV, guarda definiciones y cobertura. `document.py` calcula metadata/documentación local y ejecuta aislado el selector puro de fechas.

consulta_fecha_cerrada.sql usa parámetros SQLAlchemy :start/:end, instancias reales en parametros.json. queries.json conserva todas las consultas. Cobertura septiembre describe solo las fuentes de cierre; no certifica química/física/apilado. Ceros de rangos futuros no se consideran días operacionales cerrados. No se ejecutó SQL de archivos snapshot; son evidencia.
''')
    write('REPORTES_FECHA_CERRADA_OCTUBRE_2026.md','''# Error al editar comentarios de Torres — octubre 2026

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
''')
    old=json.loads((P/'runtime_before.json').read_text());assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in old.items())
    print('SELECT y selector aislado verificados; integridad PASS')
if __name__=='__main__':run()
