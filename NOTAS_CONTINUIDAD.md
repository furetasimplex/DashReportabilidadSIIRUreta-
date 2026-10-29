# Notas para continuar — 11 de octubre de 2026

## Solicitud y estado

El usuario pidió incorporar el dashboard de curvas y reconciliación como sección
del menú izquierdo de DashReportabilidadSIIR, usando su formato y paleta. Autorizó
trabajo con agentes Luna y Terra. Luna implementó navegación y estilos; Terra
modularizó interfaz, imports y conexión. La integración se aplicó a este
repositorio y se verificó que los archivos copiados coincidan con los revisados.
El usuario indicó luego continuar el trabajo aquí.

## Cambios aplicados

- `layout.py`: nueva sección «Curvas y reconciliación», selección activa,
  breadcrumb compartido y montaje al entrar.
- `tabs/tab_curvas.py`: puente a la sección nativa, sin iframe ni segundo servidor.
- `assets/curvas_recon.css`: estilos propios encapsulados, responsive y variables SIIR.
- `curvas_recon/`: 11 módulos funcionales, imports relativos, API
  `build_layout()` / `register_callbacks(app)` / `initialize_data(force=False)`.
- Conexión compartida vía `db_connection.get_engine()`, diferida. Validación del
  esquema solo lectura; se eliminó aprovisionamiento automático de tablas.
- Carga con error genérico y reintento; callbacks guardados hasta que los datos
  estén listos; 14 callbacks de curvas con registro idempotente e IDs propios.
- La exportación usa `RECON_PLANTA_XLSX` si se configura. El usuario dijo que
  los informes no son la prioridad por ahora.

Se conservaron `main.py`, `auth.py`, `db_connection.py`, Reportabilidad, tema,
configuración y libros locales del destino. `.serena/project.yml` tenía un
cambio previo ajeno. No se hizo commit, push, despliegue ni reconciliación remota.

## Correcciones previas de pilas nuevas, incluidas en el paquete

1. Historial de cierre por ventana y pila/campaña, en vez de un único cierre
   sobrescrito. Repetir un caso recupera la ventana anterior correcta y no usa
   un estado posterior. Cambiar un cierre invalida los sucesores.
2. Reparto de residuos positivos y negativos solo entre pilas en régimen.
   La holgura positiva respeta el techo diario, no únicamente el agregado.
   Una receptora con PLS cero distribuye el aporte entre días con riego.

La rampa sigue anclada al primer riego real, cruza ventanas y no reinicia sus
30 días cada semana. Persistencia entre reinicios/workers sigue pendiente:
`_RAMP_ESTADO` es memoria de proceso y requiere reconstrucción cronológica.

## Evidencia y próximos pasos

Pasaron 19 pruebas locales: 6 del módulo, 6 HTTP de integración y 7 de rampa.
Incluyeron ausencia de SQL al arrancar, autenticación, navegación de ida y vuelta,
montaje lazy sin colisiones, reintento, esquema solo lectura, empalme de cinco
ventanas, repetición e invalidación de estados y límites diarios.

No se verificó visualmente en navegador: la herramienta disponible no tenía
apps ni navegadores conectados. La vista previa offline estaba en
`http://127.0.0.1:8059`; es un proceso de prueba en el workspace anterior, no la
aplicación de producción. Puede haber terminado al reabrir la sesión.

Prioridad próxima: revisión visual del dashboard real y pruebas con datos de
lectura. Después, diseñar persistencia de estado de rampa para reinicios y
múltiples workers. No presentar las pruebas sintéticas como validación de planta.

Las pruebas se copian aquí para que el trabajo pueda continuar sin depender del
repositorio anterior. Ver comandos en `INTEGRACION_CURVAS.md`.

## Respaldo y ubicación

Respaldo del `layout.py` anterior:
`../curvas_recon/integration_backups/20261011_144049_588539/layout.py`.

Origen histórico del motor: `../curvas_recon`.
Copia de preparación histórica: `../curvas_recon/integracion_siir`.
Esos orígenes no reciben automáticamente cambios hechos aquí.

## Verificación posterior al traslado

Las tres suites se ejecutaron desde DashReportabilidadSIIR y terminaron con código 0: 6 pruebas HTTP, 6 del módulo y 7 de rampa (19 en total). SQL estuvo bloqueado en las pruebas de integración. git diff --check pasó. Este repositorio ya contiene las pruebas necesarias para continuar aquí.



## Pull y rendimiento — 11 de octubre de 2026

Se descargó origin/main hasta 4844237 (97 commits remotos). El commit local
2261a93 se preservó mediante merge b691766. Se resolvió report_export.py con
la nueva firma opcional `conn` y su fallback al engine. Al restaurar el trabajo
local, layout.py tuvo conflictos: se combinaron todas las nuevas secciones
(Reclamo, PowerBI, Monitoreo, Lixiviación, Polinomio Ácido) con Curvas, su
montaje diferido y breadcrumb. `.serena/project.yml` se conserva sin staging.
El stash `codex-before-pull-2026-10-11` se conserva como respaldo. No hubo push.

Luna perfiló sin SQL, usando únicamente la caché local: inicialización anterior
3,855 s en primera pasada y 0,780 s en caliente; construcción de pantalla
0,252 s. Histórico Oxidos 1,076 s; Sulfuros 0,360 s; WIP combinado 1,226 s;
320 campañas/60 pilas en ciclos 0,235 s. Estas cifras excluyen consultas SQL
y no representan medición de producción. El import del módulo fue 18,9 s en
primer proceso; pertenece al arranque, no al click.

La apertura ahora necesita solo una carga de Casos oficiales, sin caché de
oficialización. El histórico, WIP, cortes, producción y actividad se preparan
al ejecutar cálculo, con RLock y reutilización por worker. Un fallo permite
reintentar. Actualizar datos fuerza la recarga después de sync. Las consultas
de frescura (12 SELECT secuenciales) no se lanzan al montar la sección.
También se calcula una sola vez la fecha final de cada material al separar
sus ciclos. No se modificó recon_engine.py ni la rampa entre ventanas.

Pendiente de medición real: latencia de carga de Casos en SQL y ejecución
completa con datos actuales. No se ejecutaron cálculos ni sync reales durante
esta revisión. Los logs `[curvas]` muestran duración de Casos y carga completa
sin datos de conexión.

Validaci?n final: 23 pruebas pasaron (7 HTTP de integraci?n y navegaci?n,
9 de m?dulo/carga diferida y 7 de rampa). git diff --check sin errores.
.serena/project.yml coincide con el stash previo al pull. No se ejecutaron
c?lculos ni sincronizaciones reales; falta medir SQL de Casos en producci?n.

## Experimento de techo por edad

El usuario pidi? probar la propuesta. Nueve pruebas offline correctas en
curvas_recon/test_envolvente_edad_prototipo.py; resultados e hip?tesis en
PRUEBA_TECHO_DRENAJE_EDAD.md. Primer cierre sint?tico: 79,9% actual frente
a 25,9% con envolvente ilustrativa. Motor productivo sin cambios. El mayor
residuo requiere verificar capacidad del resto del pad antes de integrar.

## Evaluaci?n completa agosto?septiembre 2026

Usuario confirm? agosto2026 y agreg? septiembre. Eligi? septiembre medido
sin ajustes al no haber Casos oficiales. Resultados en
resultados_curvas/agosto_septiembre_2026_20261011. Casos5?8 ordenados, motor
real SELECT-only sin persistencia, WIP AS OF ventana. Escenarios actual y
envolvente experimental. 57/64 cierres directos,63/64 con residuo expl?cito.
Error Cu actual Caso8/SULFUROS: +0,632253884t por falta_f ignorado en
_absorber_piso_rampa. Envolvente aumenta residuo y salto a r?gimen de P22
a14,511puntos. Ver HALLAZGOS_ALGORITMO.md y visor HTML. Producci?n intacta.

Artefactos finales generados y PNG revisados visualmente: visor aut?nomo
con60pilas,7PNG,CSV de detalle/cierres/calidad. HTML incluye diagn?stico.
P17OX tiene riego residual~0,001m?/h que dispara detecci?n de campa?a nueva;
recuperaciones>100% en datos/modelo quedan visibles. Copia de entradas_cache
en carpeta final para reproducir sin volver a consultar SQL.


## Corrección de transición y Cu — 2026-10-11

Después de los 30 días, las pilas con historial de rampa conservan el factor
heredado mediante una cola exponencial que puede subir o bajar. El límite
provisional es 0,03 de factor por día calendario (3 puntos porcentuales),
no calibrado con ensayos. La forma diaria está protegida del reparto de
residuos y continúa en las ventanas siguientes. Pilas maduras sin historia
de rampa en este proceso mantienen el ajuste de régimen existente.

`_absorber_piso_rampa` retira caudal y masa de Cu por separado, conserva
masas no negativas y devuelve `(residuo_Q, residuo_F)` firmado. No asumir
que retirar volumen a la ley original de una receptora conserva el Cu.
`inventario_pls` / `inventario_fino_pls` son términos de balance con signo
objetivo menos entregado: positivo requiere aporte, negativo requiere
retención. No son stock físico demostrado. La pantalla muestra m³ y t Cu
pendientes; ese aporte no se asigna a la recuperación de ninguna pila.

Resultados reproducidos sin SQL desde el snapshot de agosto en
`resultados_curvas/agosto_septiembre_2026_suavizado_20261011`.
Septiembre conserva datos observados y PLS proxy 0,95 × riego, sin ajuste.
El techo diario por edad sigue siendo un escenario experimental.

## Entorno de arranque — Terra, 2026-10-11

passlib 1.7.4 está instalado directamente en .venv/Lib/site-packages.
Arrancar con .\.venv\Scripts\python.exe main.py o F5: SIIR - main.py (Python 3.14).
VS Code usa ese intérprete en settings y launch. Validado import incluso -s,
hash Django y login con fixtures sin SQL. No se probó el arranque SQL completo.
Validación final: 33 pruebas matemáticas unittest y 19 de integración pytest.


## Variables de autenticación al arranque — 2026-10-11

El .env local cargaba correctamente pero no contenía LOGIN_DATABASE ni
SECRET_KEY. Se completó el destino de login del perfil dev existente,
validando tabla y columnas con SELECT de metadatos sin leer usuarios.
Se creó una clave local Flask segura sólo porque no existía una clave
configurada; no se reemplazaron credenciales ni claves existentes.
No copiar esta clave local a otros ambientes ni versionar .env.

main.py valida las dos variables antes del chequeo SQL y de importar auth;
auth.py también valida LOGIN_DATABASE cuando se importa por separado.
Los errores sólo nombran las variables faltantes. El loader sigue tomando
el .env de la raíz, independiente del cwd, con override=False, y los
controles estrictos de producción permanecen vigentes.
VS Code usa .venv/Scripts/python.exe y envFile=${workspaceFolder}/.env.
Para activar una terminal PowerShell: . .\.venv\Scripts\Activate.ps1
También puede arrancarse sin activación: .\.venv\Scripts\python.exe main.py.

## Diagnóstico de recuperación P23/P24 — 2026-10-11

La desviación frente a Recuperaciones_pad persiste tras suavizar la rampa.
Al 31/08: P23 medida 28,77%, reconstrucción hidráulica cruda 46,43%,
reconstrucción reconciliada 43,34%; P24: 11,75%, 24,37% y 19,02%.
No atribuir toda la diferencia al ajuste: la reconstrucción sin ajuste ya diverge.
Revisar equivalencia de campaña/CuTf/convención de extracción y proxy PLS 0,95.
El reparto de fino no impone cotas de concentración; P23 Caso6 pasa de ley
media 20,15 a 28,16 g/L. Falta criterio operativo validado para acotar ese Cu
sin inventar umbrales ni imponer parecido visual. No se cambió el reparto.
Ver resultados_curvas/diagnostico_p23_p24_20261011/DIAGNOSTICO.md y su PNG.


## Matriz y SP de flujos — 2026-10-11

Leer docs/diagnosticos/matriz_flujos_20261011/README.md antes de cambiar anclas.
El XLSX contiene numeración antigua y bloque M6. SP nueva instalada:
sp_calcular_balance_flujos_modelo6_v2 (modelo_id2 en DEV, no6).
Agosto oficial sigue modelo1/run46,66,50,47, sourceSP sp_calcular_balance_flujos.
No atribuir la elevación de ley solo al reparto: Caso6 SULF CuPLS ratio1,369179
y CuRiego ratio2,545644 vienen del ancla. Priorizar balance/fuentes y equivalencia
de campañas antes de imponer cotas o forzar curvas. CASO_FLUJOS actual es legado;
para adoptar modelo2 requiere mapeo por modelo, no renombrar todos los históricos.
No se ejecutaron SPs ni se modificó el XLSX. Comprobación entorno final16testsPASS.

## Criterio metodológico confirmado por el usuario — 2026-10-11

Si la diferencia de recuperación proviene del reconciliador de flujos, mantener
la metodología y el reparto: no cambiar leyes ni curvas por parecido visual.
Validar identidad del modelo, códigos/origen/unidades, anclas y conservación.
Luna contrastó las122 filas M6 con125 del catálogo: hoja sinF123-F125,
3 diferencias literales de nombres y21 sinfuente/dependencia textual.
Cruce completo e informe en docs/diagnosticos/matriz_flujos_20261011.


## Actualización parcial de resultados — 2026-10-11

El Loading exterior solo observa curvas-recon-content.children (carga inicial
o reintento); no se activa por los resultados descendientes. Seleccionar pila
actualiza los gráficos y los bordes de las celdas, sin recrear la grilla ni
reiniciar n_clicks. Los controles y el encabezado permanecen montados.
Consideraciones abre un modal manual con las notas de lectura, el estado de
fuentes y los avisos del cálculo, incluido el balance pendiente de inventario.
Calcular no abre automáticamente el modal. La metodología no se modificó.

Validación: 22 pruebas de integración y callbacks pasan sin SQL.

## Comentarios nulos en Polinomio Ácido — 2026-10-11

El panel normaliza comentarios al renderizar: `None`, `NaN` y `pd.NA` muestran «Sin comentario»; los números se convierten a texto y los comentarios textuales se conservan. Aplicado al historial, estado vigente y confirmación. Sin cambios a SQL ni persistencia. Prueba puntual: `python -m pytest -q polinomio_acido/test_polinomio_acido.py` — 12 pasaron; sin conexión SQL.

## Barras medidas del Caso default — 2026-10-11

El default sigue siendo el Caso oficial más reciente por fecha: Caso 8,
2026-08-22..31 (ventana reconciliada 2026-08-22..31). En la validación
SELECT-only de `_build_bar(tab-rec)`, el Cu fino medido suma 2067,786663 t y
el reconciliado 1961,523661 t; P23 marca 411,498682 / 391,992585 t y P24
684,494413 / 618,773682 t. Hay una pila sin dato medido; se mantiene como
faltante, no como cero. No se modificaron W/Z, factores ni reparto.

La causa confirmada de barras reconciliadas en cero era comparar `date` con
`Timestamp`, lo que impedía encontrar las filas diarias/semanales. El detalle
diario ahora se filtra por `dia_offset` para respetar el fin del Caso cuando
varios Casos comparten lunes. Si una pila tuvo riego pero no un día con Cu de
drenaje medido, W/Z cero del motor se expone como faltante en el gráfico; el
cero se conserva cuando hay cobertura de riego completa y no hubo riego. Las
leyendas identifican Cu fino medido y reconciliado.

Regresión offline: `curvas_recon/test_bar_metrics.py` — 3 pruebas pasaron; cubre
matching de fecha, límite de ventana, fallback semanal y Cu no observado. No
se ejecutaron SP, sync, ni escrituras de runs/DB.


## Botón y rendimiento del cálculo — 2026-10-11

compute_recon usa running: botón Calculando…/disabled durante ejecución,
restaurado al terminar. Agente boton_calculando implementó el contrato y prueba.
Root midió con SELECT-only y guardado sustituido: demora inicial concentrada
en detección histórica de campañas. _fechas_actividad usa sort_values; inicio_campana
reemplaza recorrido inverso por diferencia vectorizada, mismo corte > gap_days.
Comparación fría Caso8: 6,7519 s a 1,5783 s, resultado completo idéntico. No
confundir con tiempo end-to-end ni persistencia: no se guardaron runs en prueba.
29 pruebas offline pasan. Ver docs/diagnosticos/rendimiento_curvas_20261011.

Verificación conjunta de root: 32 pruebas offline pasan (gráfico, campañas y callbacks).
Trazas reales del Caso default en docs/diagnosticos/grafico_inferior_default_20261011/validacion.json;
lecturas con caché existente, guard SELECT-only y persistencia sustituida. No se guardaron runs.


## Contraste entre gráfico superior e inferior — pendiente pila del usuario

El usuario indica que arriba hay lecturas y abajo no. La corrección anterior
no demuestra resolver esa observación. En tab-rec el superior usa observaciones
de recuperación de la campaña completa (%) y el inferior calcula masa neta
de Cu desde riego/concentraciones (.95*W-Z, t): no son la misma variable/fuente.
Comparación SELECT-only de todas las pilas activas del default Caso8 (22–31/08):
la única masa medida nula/faltante fue OXIDOS/P17. Su última recuperación de
la curva hasta fin del Caso es 28/02/2026 (110,504629%), fuera de agosto;
W=Z=0, n_irr=1, n_days=0. No confundir esa lectura histórica con dato de Cu
de agosto ni convertirla a masa inventada. Resto de pilas muestra masa medida
positiva en esta ejecución. Usuario está revisando qué pila observó; falta
confirmar esa identidad y vista antes de afirmar que es P17 o cambiar unidades
del gráfico. Evidencia en contraste_fuentes.json junto a la validación previa.
No se cambió metodología ni gráficos en esta revisión de fuentes.

## Reconstitución de apilado preparada — 12/10/2026

Fuente activa preparada: C:\Users\5330\Desktop\Reconstitucion. Ver docs/INTEGRACION_RECONSTITUCION_PENDIENTE.md y NOTAS_CONTINUIDAD.md del repositorio fuente. Copiar paquete reconstitucion/, assets/reconstitucion.css y tabs/tab_reconstitucion.py; registrar callbacks una vez e inyectar db_connection.get_engine con esquema explícito inventar_SpcHidr.inventar_SpcHidr. Extender navegación siguiendo montaje diferido de curvas. No copiar app.py standalone ni .env. Esta sección aún NO fue incorporada al menú ni a main.py/layout.py de este repositorio.

Presentación preparada: un único Gantt, carriles Medido/Proyectado separados, identidad completa pad/campaña/módulo, paleta SIIR, hover diario, tabla plegada y Consideraciones modal. No SQL al importar/montar; carga por botón con estado Calculando. Snapshot agosto reconciliado/septiembre medido preserva masa oficial y el pendiente por falta de volumen. 25 pruebas + validación snapshot y arranque offline OK. Vista en navegador pendiente, herramienta sin browser disponible. Exportación de informes y caché multiworker requieren integración específica; los archivos originales se conservan.

## Reconstitución incorporada al menú SIIR — 12/10/2026

Completado el cableado pendiente descrito en docs/INTEGRACION_RECONSTITUCION_PENDIENTE.md.
Ver INTEGRACION_RECONSTITUCION.md para el contrato actual. layout.py monta lazy
«Reconstitución de apilado», conserva el árbol al salir/volver y actualiza
selección activa/breadcrumb. Puente tabs/tab_reconstitucion.py inyecta proveedor
lazy de db_connection.get_engine y schema inventar_SpcHidr.inventar_SpcHidr.
Sin cambios a main.py, autenticación, entorno, validación de arranque ni otras
secciones. Registro/montaje sin SQL; cargar es lectura explícita por botón/rango.

Se copiaron paquete reconstitucion/, CSS encapsulado SIIR y pruebas portables.
Un Gantt, medición y proyección en carriles distintos, huecos reales y hover
diario; no se añadieron gráficos que repitan datos. Consideraciones modal,
tabla plegada y botón Calculando preservados. Producción sigue fuente oficial;
septiembre medido del preview no se incorporó como respaldo automático.

54 pruebas offline pasaron en staging, incluyendo 14 HTTP del host y regresiones
existentes de curvas. Revisión en navegador pendiente por herramienta sin browser.
No SQL real/XLSX, escrituras DB, commits ni push. Cache local hasta16 sesiones;
multiworker requiere afinidad o cache compartida. Exportación legacy permanece
en origen y no está incorporada al panel.


Verificación posterior a aplicación: 54 pruebas offline pasan en el repositorio destino (19.86 s), incluyendo navegación HTTP, montaje sin SQL, Gantt y metodología. git diff --check sin errores. Hash de main.py coincide con la línea base. Sin prueba de carga SQL real ni revisión interactiva de navegador.
## Reconstitución de Módulos por Caso — 12/10/2026

Nombre visible actualizado en menú, breadcrumb y panel. El selector usa el mismo catálogo oficial 1..8 de `curvas_recon.db_pipeline.load_casos`, inyectado por proveedor lazy del puente. «Actualizar Casos» realiza la lectura explícita; montaje/registro/filtros no consultan SQL. Las fechas son de solo lectura y proceden de recon_caso; no hay rango independiente.

La carga exige Caso seleccionado, fija su ventana exacta y consulta masa por caso_id, origen AJUSTE_REPORTE y estado validado (preserva COALESCE histórico). Se filtra Caso antes de elegir la última validación por fecha. No exigir es_activa permite reconstruir publicaciones históricas validadas sustituidas por otra ventana; sin masa del Caso no se rellena desde otro Caso ni desde base medida. No se recorta a extremos globales para ocultar huecos de cobertura. No se cruza el nombre con casos_balance para Casos del solver nuevo.

Relación comprobada en ajuste_reporte/rep_prod_adjuster.py: run_ajuste_reporte_prod_solver_nuevo conserva recon_caso.id en el pipeline de reportabilidad; run_id de reporte es UUID nuevo, distinto del solver_run_id entero. Publicación SP copia Caso y UUID con origen literal AJUSTE_REPORTE. El resultado identifica Caso/ventana en pantalla y guarda toda su identidad (incluido run oficial) en caché. Consideraciones explica que no se certifica correspondencia entre UUID histórico y run oficial actual. No se realizó SQL real ni escritura, y no se ajustaron masas/cálculos ni se ejecutó SP.

Cambiar Caso, fechas del catálogo o run oficial invalida visualización y detalle de resultados antiguos; una respuesta tardía de carga A no se muestra como B. El token continúa aislando resultados por sesión. Nuevas pruebas cubren catálogo compartido, periodo exacto, IDs con fechas iguales, respuesta tardía, cambio de run y periodo, ausencia de masa, SQL parametrizado histórico y ventana sin recorte global. Sin cambios a main.py, autenticación o validación SQL de arranque.


Verificación del cambio por Caso: 63 pruebas offline pasaron en el repositorio destino (66.06 s). Incluye 15 HTTP SIIR, 8 regresiones nuevas de Casos, panel/Gantt, metodología y curvas. git diff --check limpio; main.py conserva el hash anterior. SQL real y navegador interactivo no verificados. Sin commits ni push.

## Prueba real de dos Casos — 12/10/2026
Se probaron Caso8/run47 (22–31 agosto) y Caso7/run50 (15–21 agosto), usando catálogo de Curvas. Ambos tienen cero filas de masa elegible publicada bajo su Caso y período (origen AJUSTE_REPORTE, validada). Motor y callback real rechazan la carga, token vacío; no se reemplazan por masa de otros Casos. Por tanto no están verificados balances ni gráficos reales de esos dos Casos. Evidencia en docs/diagnosticos/reconstitucion_dos_casos_20261012/RESULTADO.md y resultado.json. La ejecución fue SELECT-only, sin SP ni publicaciones. Falta vínculo/publicación de masa para probar dos cálculos completos.

## Rendimiento Reconstitución Caso8 — 13/10/2026
Perfil online de analyze_db para Caso8/run47/22–31 agosto: antes 8.546/14.398 s (ticks 7.120/13.007 s, fetch incluido); después 0.274/0.266 s. Caso sin masa publicada, por lo tanto cálculo y gráfico no se alcanzan. Ahora masa primero, sin cobertura global en modoCaso, sin apilado/ticks cuando masa vacía, y mensaje específico MissingCaseMassError. Cobertura del Caso con masa se deriva de frames observados; la ruta sinCaso mantiene clipping previo. Cinco SELECTs de datos pasan a uno para caso vacío. No son tiempos totales de UI. Cambios aplicados en engine/db_source/panel/test_casos; 66 tests offline pasan y main.py intacto. Evidencia: docs/diagnosticos/rendimiento_reconstitucion_caso8_20261013/PERFIL_CASO8.md y JSONs. Sin escriturasDB, SP, XLSX, commits o push.

## Curvas: integración y reporte — 20/10/2026
Se separó el contrato de flujos de los modelos 120 y 125, validando código, versión y cantidad. El catálogo oficial se consulta sin caché; las anclas se identifican por run. La descarga valida Caso/run/ventana/modelo para rechazar resultados desactualizados.
SQL y caché respetan el rango solicitado. Los 60 días corresponden al margen previo de química, nunca al límite de la campaña. El reporte conserva la historia desde el inicio de campaña, acota apilado al corte y reutiliza la lectura de riego. Se probó una campaña de más de 1000 días. Excel de planta opcional, descarga repetible durante TTL y limpieza de temporales incluso al fallar el envío.
115 pruebas pasaron. La optimización reduce lecturas y caché; no elimina el costo del motor. El reporte consulta fuentes históricas al exportar: no congela todas en una instantánea. No se cambió la rampa ni se implementó un nuevo balance de inventario. main.py, recon_engine.py y tabs/tab_curvas.py se preservaron. Sin escrituras DB ni SP, sin commit ni push. Los payloads internos de DB no se copiaron a estas notas ni al directorio de diagnósticos.

## Reporte de curvas y hoja Prod — 20/10/2026
Se adaptó el escritor al formato de recuperaciones de la referencia del 12 de octubre: cabeceras distintas por pad (OX curva desde fila 10; SU desde fila 11), Arial y colores de referencia, cuatro hojas existentes más Prod. Prod contiene Cu neto diario reconstruido por pila, con fechas desde el inicio de su campaña; no representa cátodos. Las sumas diarias coinciden con Aporte Parcelas. Recuperación máxima usa el máximo de la curva y el aporte conserva el acumulado terminal. Lector reconoce parcelas por identificador, excluye encabezados de las curvas y conserva huecos internos. Gráficos separados para evitar superposición.
Indicación explícita del usuario: algunas curvas de la referencia suman varias pilas; esa agrupación se utiliza SOLO para la comparación externa, nunca como regla del reporte. Reporte/Prod y sus series continúan individuales por pila. Los archivos de contraste y la salida Excel quedan en la carpeta de trabajo; no se copian payloads internos DB al repositorio.
Validación: 119 pruebas offline pasaron y se verificaron las cinco hojas, cuatro gráficos, referencias de series y sumas de Prod con el escritor real. Prueba de motor online fue SELECT-only; no se ejecutó callback de persistencia ni SP. main.py no se modificó. Sin commit ni push.

## Casos del PAD - 2026-10-20

`load_casos()` ya no acota IDs: conserva la oficializacion y el run `success`,
la union al modelo y ordena por `fecha_inicio DESC, id DESC`. El dropdown y el
guardado de calculo ya no reimponen un rango de IDs. Asi, Casos futuros con run
oficial se incluyen y el mas reciente por fecha queda primero. Prueba offline
captura SQL sin conexion y verifica filtro, orden e identidad de modelo.

## Reconstitucion con flujos oficiales por modelo - 21/10/2026

Reconstitucion de Modulos usa los flujos solidos del run oficial del Caso:
125 v2: OX F18, SU F19; 120 v1 conserva OX F15, SU F14. Se verifica metadata,
periodo e identidad del run sin cache ni escrituras DB. modelo_flujos.py lee
perfil operativo de correas/humedad y engine.py conserva cada total por PAD
antes de distribuir por volumen a sus modulos. Los dias/turnos son distribuidos
del total reconciliado, no mediciones reconciliadas independientes. La UI pasa
el Caso completo y lo explica en Consideraciones; no depende de publicaciones
AJUSTE_REPORTE de casos_balance para los Casos hidro con modelo conocido.

SELECT-only online: Caso10013/run10104 cierra 728062.407300 t SU (F19), OX0;
Caso8/run47 cierra 598606.933440 t SU (F14), OX0; pendientes diarios y por PAD0.
Se construyeron ambos Gantt en Python. Suite integrada:154passed. Lecturas
perfil/horas paralelas: motor+figuras18.162s/16.920s, no tiempos UI. Evidencia:
auditorias/reconstitucion_modelo125_20261021/RESULTADO.md y JSONs.
No se ejecuto SP, solver, sync, publicacion ni escritura DB. Sin commit/push.

## 2026-10-21 — Revisión XLSX Caso10013 y Prod por pad
Se separó Prod en Prod Oxidos y Prod Sulfuros, manteniendo datos/formato y
agregando Caso/run/período. Suite155passed y render de ambas hojas verificado.
Comparación1–12oct2026: OX166.029 vs156.926tCu (+5.80%);
SU2279.031 vs1691.492tCu (+34.74%). Core puro SELECT-only run10134 reproduce
el adjunto al redondeo. La base operativa de pilas difiere de la del ancla;
los ratios no garantizan cierre absoluto: SU2279.031 vs1929.949tCu netos
por componentes, OX166.030 vs157.036. F29 almacenado1923.609 difiere6.340t
de sus componentes. No se cambió metodología ni se forzó escala/historia.
Evidencia: auditorias/revision_reporte_prod_20261021/RESULTADO.md.
No hubo SP, persistencia DB, commit ni push. El adjunto no identifica su run.

## 2026-10-21 — Cierre neto curvas con F25/F29 (modelo125)
El usuario confirmó que producción=Cu drenaje−Cu riego y debe igualar el fino
reconciliado F25OX/F29SU. Se incorporó objetivo absoluto neto al motor antes
del reparto y validación sobre diarios post-rampa; no-cierre detiene antes de
guardar. Se conserva riego por ratios y forma Q/rampa; modelo120 intacto.
DB loader lee F25/F29 reales (no derivados de componentes); raw payload v2
invalida exportaciones de corridas previas al fix. No tocar solver constraints.
Caso10013/run10134: motor OX157.036198tCu, SU1923.608655tCu, residuo0;
constructor reporte157.037/1923.610 por redondeo3dec (<1.4kg). Historial previo
no corregido. 164tests pasan11.01s y diffcheck limpio. Validación live SELECT
only47+5WITH, sin persistencia/SP. Evidencia auditorias/cierre_transferencias_20261021.
Para proceso ya iniciado: reiniciar servidor y recalcular; no se reinició desde
el agente. Sin commit/push. No confundir40.502s del diagnóstico completo sin
caché+reporte con tiempo UI Calcular.

## 2026-10-21 - Recuperaciones oficiales y saldo historico del reporte
Por instruccion del usuario se cargaron1181 filas faltantes de todas las pilas
OX/SU disponibles en oficial, rango2026-01-01..2026-10-01 inclusivo.
Transaccion confirmada con verificacion1181/1181; no se reemplazaron555
valores validos diferentes ni se cargaron blancos/errores de formula.
Campanias reales id11=496,id4=93,id10=592. Evidencia ignorada porGit:
auditorias/recuperaciones_oficiales_20261021/{summary,apply_audit}.json.
Reporte usa recuperacion primaria preCaso por campania y mantiene netos
reconciliados diarios; corrige prefijo reconstruido inflado, no escala aloficial.
167pruebas pasan17.09s. MotorF25/F29 sin cambios. Sin commit/push de estefix.

## 2026-10-23 - Auditoria todas las curvas y vigencia de fuente
Se reviso Auditoria_Recuperaciones_SIIR_vs_Oficial_20261012.xlsx: 10028 comparables en2026,9951 coinciden y77 difieren (agosto). Sept1-Oct1:1180/1180 coinciden. No sobrescribir77validos ni cargarOct2-12 por esta auditoria. Se revisaron60pilas;36activas enCaso10013,24excluidas por actividad no son faltantes.
Export1743 usa run10134; catalogo online actual apunta10145 (modelo125_v2,Oct1-12). Lectura fresca pura10145 cierra motor conF25=157.036198t yF29=1764.541907t. Reporte redondeado157.039/1764.544t. Sin SP ni escriturasDB.
Corregida cache primaria con firmaSELECT COUNT/MAX/CHECKSUM porPAD, claves versionadas solo Recuperaciones_pad. Calcular refresca catalogo oficial y, con worker caliente, solo DATA/CYCLES primarias+caches de curvas. GenerarReporte refresca catalogo y rechaza store de run anterior. No cambia metodologia ni escala al oficial.173pruebas pasan;diffcheck limpio. Reiniciar servicio para cargar codigo y volver a calcular antes de descargar.
Evidencia en auditorias/comparacion_todas_20261023. No commit/push; archivo auditoriaxlsx del usuario sin modificar.

## 2026-10-23 - Grupos locales de curvas de recuperacion
Agregado boton Sumar curvas en subtab Curvas de Recuperacion. Modal permite crear/editar/quitar/restaurar grupos de2+ pilas activas del Caso; configuracion en dcc.Store storage_type local (navegador), sinDB ni reglas nuevas en Excel. Predeterminado: curvas individuales actuales. Seleccionar grupo reemplaza visualmente el grafico individual; Flujos/Concentraciones conservan su vista.
Curva agrupada por fecha calendario:100*SUM(Cu recuperado acumulado)/SUM(Cu apilado), usando CuTf en toneladas y netos diarios (fino_pls_final-fino_riego_final)*0.024. No promediar porcentajes. Fuente: mediciones residentes y raw local validado porCaso/run/ventana; edicion/render grupos no consultanSQL. Cache raw acotada aunCaso. No sumar miembros inactivos, rellenar gaps ni reutilizar anclas de otra campania. Base al dia anterior del Caso o inicio de pila dentro ventana; falta de base se indica. Azul solo ventanaCase. Archivo curve_aggregation.py helper puro; tests test_curve_aggregation.py/test_curve_groups_ui.py incluyen apertura/guardado HTTP Dash, gap, nueva campania, rawstale y persistencia local.181pruebas pasan14.87s; diffcheck limpio. Sin commit/push. Reiniciar servicio y refrescar navegador para cargar codigo.

## 2026-10-23 - Comparacion exploratoria actual vs solo ramp-up
Solicitud: seguir desde primer riego real las cohortes jovenes y trasladar ajustes similares al Caso oficial a fechas sin reconciliacion. No se modifico el motor ni la DB. Export SELECT-only (26 consultas) congelo junio-septiembre2026: SHA256 ed7f1f226b12273aefce20acd716cf6cf9b80ee1da3e1337a61e35de26910a9b. Caso10013/run10145 modelo125_v2: F25 neto ratio1; F29 medido1628.848095 -> reconciliado1764.541907t, ratio1.0833066093864328. Objetivos son hipoteticos, por ventana, no reconciliaciones historicas reales.
Experimento actual invoca motor productivo con force_all_active=True, sigma0, anclas por PAD, caches y ultimo_riego inyectados desde snapshot offline, estado restaurado al finalizar. Alternativa: misma familia ramp_curve, un dial comun solo edades1..30 (edad transcurrida0..29); concentracion drenaje medida, entradas riego/Cu iguales al candidato actual; despues conserva factor del dia30; maduras sin reparto de residuos. Prioriza neto y declara diferencia de caudal contra meta comun. Acumulados separados por metodo/PAD/pila/nacimiento, cero inicial, sin reanclajes semanales. Birth SU21Jun21,22Jul8,23Aug1,24Aug15,25Sep1,26Sep18; todas las fechas cubiertas.
IMPORTANTE: el replay ESTRICTO no completo calentamiento. Guard rechazo OXJun1(94.737t)/Jun8(114.555t), SUJun22(55.070t). Se preservan resultados estrictos fallidos. Para mostrar perfiles completos se implemento modo DIAGNOSTICO opt-in: captura locales del candidato ya calculado cuando el guard EXACTO lanza RuntimeError, registra rechazo y conserva estado SOLO para continuacion diagnostica. No desactiva guard ni altera produccion. No presentar esas curvas como corridas reconciliadas validas: agosto-septiembre hereda estado diagnostico.
Bajo esa condicion,9/9 ventanas AugSep por PAD cierran numericamente con actual. SU objetivo14839.230929t; solo-ramp13625.855217t, deficit1213.375712t(8.1768%),0/9 cierres; OX objetivo978.060835t, solo-ramp985.097474t, exceso7.036639t. En SU21..26 solo-ramp baja recuperacion final0.93..2.72pp frente al candidato actual; no elimina brecha frente DB, que tambien depende de proxy0.95/objetivo hipotetico/denominador CuTf fijo. Actual ademas ajusta Cu fino/concentraciones, por lo que no es una diferencia unicamente de poblacion elegible. OX contiene3 registros P17 sin Cu drenaje, Q<0.0015m3/h, limitacion declarada.
3 pruebas pasan; replay completo repetido determinista con Engine.connect bloqueado y0 intentosSQL. QA verifica cumsum por metodo, entradas comunes, rampa monotona, techo y congelamiento dia30, cohortes desde nacimiento,9 cierres numericos AugSep porPAD y3 rechazos previos. HTML portable con3PNG, CSV, metadata, VALIDACION.json en auditorias/comparacion_ramp_solo_20261023. Scripts/snapshot24MB quedan en workspace hermano ../curvas_recon/auditorias/comparacion_ramp_solo_20261023. No commit/push.

## 2026-10-23 - Correccion del supuesto del ensayo de ramp-up
El usuario aclaro: las concentraciones NO son fijas; el metodo distribuye flujos y concentraciones, solo cambia en que pilas se hace. Por tanto, el ensayo previo de Cd fija y sus deficits/cotas NO responden a la comparacion solicitada y no prueban inviabilidad del metodo con Cu reconciliable. Informe anterior marcado como escenario descartado. Nueva evaluacion conserva el asignador actual de Q y fino/Cu, rampa fisica30dias y estado; modifica solo el pool por edad. Fuera del pool no deben quedar ajustes del benchmark all-active. Estudio en ../curvas_recon/auditorias/umbral_secuencial_ramp_20261023. No cambios productivos ni DB.

## 2026-10-24 - Pool por edad corregido y sumas en el esquema
La comparacion ahora cambia SOLO el pool elegible, conserva distribucion Q+fino/concentraciones C=F/Q, rampa fisica30 y cola del motor actual. No fija concentraciones. H fuera del pool recibe delta0 con su propio historial; E compensa los cuatro objetivos globales. Se prueba30 y cada breakpoint de admision desde el MISMO estado heredado; solo persiste primer factible o mejor candidato explicito. Busqueda reinicia30 en cada ventana, curvas/estados NO se reinician. Replay June1-Sep30 snapshot previo offline, referencias F25/F29 run10145 hipoteticas. AugSep18/18 cierran cuatro masas+neto y limites; maxnet4.55e-13t; edadOX54..145,SU32..267. 238 candidatos exactos, no151replays completos. Warm-up conserva3rechazos y continuidaddiagnostica, no corridasoficialesvalidas. QA independiente: segundo replay determinista,0conexionesSQL, miembros anidados/primer factible, Cu realmente variable y C=F/Q. InformeHTML/3PNG/CSV+VALIDACION en auditorias/umbral_secuencial_ramp_20261024. Archivo HTML previamente abierto se reemplazo con comparacionCORRECTA; escenarioCdFija preservado como ESCENARIO_Cd_Fija_DESCARTADO.html en workspacehermano.
Sumas: grupos locales aparecen como botones Curvas sumadas bajo esquema de pilas; seleccion grupo/pila exclusiva y resaltado sin redibujar grilla. Callback de seleccion unificado evita ciclosDash, ALL identifica click porid+indice sin ctx.triggered.value. Eliminacion/reset limpia seleccion. Miembros suman EXACTAS curvasindividuales completas (medidas+operacionales+Case) ponderandoCuTf, no una reconstruccionmasrestrictiva. Resuelve falta de ancla primaria justoantesCase si individualpuedecompletarconoperacion. Cache96porrawtoken/caso/ventana/fuenteporCuTf, invalidadaalrefrescarciclos, sinconfigcompartida. HistoriapuedeconsultarseSELECTprimeravez, edicionusa cache; noDBwrites.
185pruebas pasan20.31s; browserheadless14checksfuncionales pasan (fixtureSQLbloqueado), suma17.5%medido y17.98/18.46/18.94%reconciliado, CRUD/localStorage/volverindividual/ceroerroresdeconsola. VerificacionvisualpopupconCSSpublico localfixture se registraenbrowser_qa. No cambios en solver/metodoproductivo por experimento, sincommit/push. Reiniciar main.py para cargar cambiosUI.

QA visual completada: popup role=dialog/aria-modal, position fixed y centrado, panel dentro viewport, backdrop completo y esquema+grafico detras. Flatly5.3.6exacto y CSS activos servidos localmente soloenfixture (sin cambiosglobalesCSS). Captura05-popup-centered-with-group-and-chart.png y browser_modal_qa_results.json en auditorias/sumas_esquema_20261024. FuenteGooglebloqueadaenfixture no afectofuncionamiento. ServidorQA detenido. Sourcepad_dashboard app coincide SHA con stageprobado9332C2FDD91B6867E6CAEEBBE422662995F2FE0D22ADFEFE05FF6CAB2FEECEC7.

## 2026-10-24 - Subtab Recuperación y RL

Agregada subtab Recuperación y RL para pilas individuales y grupos locales: recuperación (%) a la izquierda y RL acumulada (m³/t) a la derecha sobre fecha calendario. Conserva las trazas originales de recuperación. RL = volumen de riego acumulado / TMS apiladas; los grupos suman volumen y TMS, sin promediar RL ni usar ponderaciones de Cu.

Historia desde el primer riego de la campaña, sin reinicio al comenzar el Caso. Riego medido fuera de la ventana y q_riego_final dentro. TMS desde apilado a la fecha de corte. Carga diferida con cachés acotadas; no carga RL al montar ni en otras subtabs. Miembros con TMS/historia faltante no se excluyen silenciosamente; se conserva recuperación y se indica RL incompleta. Cambiar subtab evita recalcular barras ajenas.

Validación: 194 pruebas pasan (dos avisos previos de Dash DataTable), git diff --check sin errores. QA Playwright usa layout/callbacks reales con datos controlados y SQL bloqueado; verifica dos ejes, continuidad, ponderación física, grupos persistidos y reutilización de cachés. No cambios al solver ni escrituras DB. Sin commit/push. Reiniciar main.py y refrescar navegador para cargar la nueva subtab.

QA navegador: 18 comprobaciones pasan con SQL bloqueado. RL individual 2.4 antesCaso y6.0/9.6/13.2 enCaso; grupo1.8 antesCaso y3.6/5.4/7.2 m3/t enCaso. Ajuste visual de nota validado;21pruebas focalizadas posteriores pasan. Evidencia en auditorias/subtab_rl_20261024.

## 2026-10-25 - Selector de fuente RL
Subtab Recuperacion y RL incorpora radio Reconciliado (default) / Medido. Medido usa Q medido en toda la campania; Reconciliado sustituye q_riego_final dentro del Caso y conserva medido fuera. Aplica a pilas y grupos, cache diaria distingue modo; selector solo dispara render RL, no motor. Recuperacion mantiene sus trazas previas. Etiquetas visibles usan RL (m3/t), sin acumulado; definicion fisica volumen historico/TMS sin cambios. 22 pruebas focalizadas pasan, sin SQL ni escrituras DB. Reiniciar main.py y refrescar navegador. Sin commit/push. Staging: ../curvas_recon/auditorias/rl_selector_20261025/stage.

## 2026-10-25 - Miembros del grupo en azul
Al seleccionar boton de grupo, callback highlight_recon_pila pinta sus miembros en azul #2a78d6 mediante estilos de celdas existentes. No reconstruye grilla por click. Al cambiar grupo, quitarlo o elegir pila individual restaura verde/naranja/gris desde estado reconciliado, sin reutilizar azul como color base; mantiene borde naranja individual. Conserva selector RL. 23 pruebas RL/grupos pasan, incluyendo transicion grupo A a B a individual. Sin SQL ni cambios DB; sin commit/push. Reiniciar main.py y refrescar.

## 2026-10-25 - Recuperación por ventana, auditoría de 60 pilas y hojas DUMP/RL

Medido y Reconciliado se dibujan por separado únicamente en la ventana del Caso. El parser admite res.daily y res.piles[].daily. La lectura primaria válida tiene prioridad para Medido; los campos operacionales medidos completan fechas sin esa lectura. El acumulado reconciliado no se reinicia con cada lectura primaria: conserva sus propios incrementos. Un dato realmente ausente rompe la acumulación hasta una nueva base válida; no se sustituye por cero ni por Medido.

Antes del Caso se dibuja únicamente histórico respaldado como reconciliado. El manifiesto oficial fija 1180 valores contrastados del 1-sep al 1-oct de 2026; solo clasifica un punto primario actual si coinciden pila, fecha y valor (0.0001 pp). No reemplaza valores actuales desde el CSV. Para Caso 10013 son 1144 puntos estrictamente anteriores. El SELECT histórico adicional devolvió 259 filas del 1 al 7-sep para 37 pilas. Las tablas no conservan solver_run_id de origen: la elegibilidad actual se valida por Caso oficial/modelo125/convergencia, sin afirmar identidad exacta del solver que produjo cada fila. Una carga por token/ventana, cachés acotadas y fallos temporalmente cacheados; no consulta por cada pila.

Auditoría Caso 10013/run10145, 1-12 octubre: matriz de 60 pilas x 12 fechas = 720 cruces. Hay 432 filas diarias de 36 pilas con las cuatro mediciones completas. Las 42 filas con concentraciones reconciliadas nulas tienen ambos caudales cero y aporte fino explícito cero: recuperación válida, sin hueco. Las 24 pilas restantes no figuran en ese resultado; sus 288 cruces sí tienen fuentes medidas en la caché vigente. No se inventa reconciliación para ellas ni se afirma inactividad solo por esa omisión. QA del parser aplicado con payload real y denominador sintético: 432/432 medidos y 432/432 reconciliados válidos, sin consultas DB.

RL mantiene la base numérica desde el primer riego. El radio Medido/Reconciliado selecciona solo la ventana del Caso. Cuando el prefijo de Q reconciliado está incompleto, se conserva la base histórica necesaria para el cálculo y se oculta ese prefijo en el gráfico; se indica el alcance, sin presentarlo como historia reconciliada.

El reporte agrega RL Oxidos y RL Sulfuro con el formato del oficial (día de ciclo en filas, pilas en columnas), q_riego_final dentro del Caso y volumen histórico fuera, dividido por TMS a corte. Faltantes reales conservan huecos. Agrega Dump desde balance_dump_leach_flujos y conc_cu: Feed F77 y DPLS F51, m3/h x 24 a m3/día, Cu g/L, aporte neto t/día = (V51*C51 - V77*C77)/1000, equivalente a F42. F74/refino es otra corriente y no sustituye F77. El mapeo se contrastó con el SP del modelo125 por lectura de código, sin ejecutarlo. La serie DB difiere de la hoja oficial; se conserva la fuente DB y no se calibra para igualarla. Consulta solo SELECT; ningún cambio DB, SP ni configuración de conexión.

El generador también conserva extracción cuando el riego es cero y el drenaje positivo: cada contribución fina se trata por su propio caudal. Finos faltantes con caudal positivo en una fila reconciliada provocan error explícito, no sustitución silenciosa por Medido. Las hojas Rec/Curvas/Prod previas se conservan.

Verificación desde el repositorio activo: 43 pruebas de curvas/historia/grupos/RL y 25 de reporte pasan. Regresión: 209 pruebas pasaron; se actualizó la prueba de integración heredada a la firma del resaltado de grupos y sus 15 pruebas pasan. La única falla de esa corrida era esa expectativa obsoleta; dos avisos de Dash DataTable ya existían. Evidencias en auditorias/series_ventana_20261025, gaps_todas_20261025, qa_ventana_20261025 y dump_rl_reporte_20261025. Reiniciar main.py, refrescar, ejecutar el Caso y descargar un libro nuevo. Sin commit/push.

Cierre: grupos unifican por fecha historicos oficiales y guardados antes de ponderar, sin perder puntos por mezclar fuentes (10%*100t + 20%*300t => 17.5%). DUMP se limita al anio del reporte (2026 para Caso10013); RL conserva toda la campania. QA visual de las matrices RL y de la tabla DUMP legible en PNG. La prueba nueva de grupos normaliza datetime.date/Timestamp; etiqueta comun Historico reconciliado.

## 2026-10-25 - Respuesta callback Recuperacion y RL
Se restauro uso de _RL_RIEGO_CACHE para prefijo de riego, LRU24 por raw_token/PAD/inicio/corte; cambiar pila o radio reutiliza la lectura, invalidaciones existentes conservadas. No cambio metodologia. Prueba aislada:4modos individual/grupo por medido/reconciliado,4POSTDash200,figuras serializables con trazaRL no vacia; lectorlento1llamada y sinlecturasextra alrepetir. Validacion REAL autenticada en127.0.0.1:8065 usando payloadyaexistente Caso10013/run10145, cargaseccion sololectura: grupo reconciliado HTTP200 4.390s, pila reconciliada200 0.370s, pila medida200 0.349s, grupo medido200 0.096s. No se ejecuto Calcular ni SP ni escrituras DB. Las peticionesprevias204 se debian a seccion aun sin inicializar tras recargadecodigo; despuescargaread-only devuelvefiguras. Evidencia live_rl_probe.json y script sincredenciales en workspacehermano auditorias/rl_callback_fix_20261025. No almacenar credenciales/sesion en archivos. Cambiocargadoen servidorlocal, basta reabrirsubtab/refrescarnavegador. Sincommit/push.

QA navegador real 2026-10-25: agente Luna y root verificaron Edge headless/Playwright contra localhost8065 autenticado. Se reutilizo raw existente Caso10013/run10145, restaurando solo stores en contexto browser efimero; no Calcular ni SP. Clics DOM: pilaSU21, tabRL, radiosMedido/Reconciliado y botonlocalgrupoSU21+SU22. Cuatrograficos conrecuperacion/RL yejescorrectos, HTTPsin>=400, sinpageerrors, tiemposclic-render1.072/2.700/2.727/2.055s (conCasoya cargado). Capturas ybrowser_results.json en auditorias/rl_browser_real_20261025. Erroresconsola externos delchequeoversionDashCORS ypeticionesobsoletascanceladas no afectaronplots. PrimerintentoQAfallo porrestauracionincompletastore/racegrilla, corregidoenarnes,noenproduccion. Credenciales soloSTDIN/memoria,noguardadas; grupotestsolo local efimero ycontextocerrado. No otrocambiocodigoenestaverificacion.

## 2026-10-25 - RL diaria, historia completa y etiquetas

El usuario aclaro expresamente que RL NO debe acumularse. Esta aclaracion reemplaza la definicion acumulada de las notas anteriores: RL de cada fecha = Q_riego_m3h de esa fecha x 24 / TMS apiladas. El nombre interno heredado cumulative_rl ahora devuelve valores diarios independientes. Para grupos: sumar volumen de ese dia y dividir por TMS totales, sin promediar razones ni usar pesos de Cu.

La subtab conserva todo el historial de riego disponible de la campania, sin ocultarlo cuando falta algun reconciliado previo. Historia medida y Q final dentro del Caso en modo Reconciliado; modo Medido usa Q medida. Los gaps afectan solo su fecha, cero explicito es cero y las fechas posteriores siguen calculandose. No se inventa riego reconciliado anterior donde solo existe medicion. Se conservan caches por token/PAD/fechas y la metodologia de recuperacion/solver.

Etiquetas: Recuperacion reconciliada, RL medida y RL reconciliada; la traza de recuperacion medida se identifica con su magnitud. Leyenda horizontal para evitar superposicion con el eje derecho; eje x Fecha calendario. Nota explica formula diaria y diferencia historia medida de la ventana reconciliada. Sin acumulacion entre fechas.

Reporte: rl_curve y RL de resumen tambien diarios, usando q_riego_final en el Caso. El escalar RL corresponde al ultimo dia del reporte y queda vacio si falta ese dato, sin arrastrar el ultimo valor conocido. Volumen total de riego mantiene su significado acumulado y su rotulo propio. Hojas RL Oxidos, RL Sulfuro, Dump, Rec, Curvas y Prod conservadas.

Durante QA se reprodujo un fallo independiente al restaurar un resultado despues de reiniciar un worker: render_recon entraba a _build_bar/_load_material_window con REC_META vacio y levantaba KeyError('OXIDOS'), aun con store completo. Se agrego ensure_full_data antes de usar esos metadatos, conservando el retorno no_update de RL sin cargar barras innecesarias. Dos pruebas de regresion verifican inicializacion una sola vez y el camino rapido de RL.

Verificacion: 65 pruebas de curvas/series/grupos/reporte y 15 de integracion pasan en la aplicacion activa. Los dos avisos de Dash DataTable son previos. Sin cambios DB, SP ni commit/push. Evidencia y scripts en auditorias/rl_diaria_20261025 del workspace hermano.

QA Edge final PASS:4modos de pila/grupo Medido/Reconciliado, sinHTTP500 ni pageerrors. SU21 ygrupoSU21+SU22 muestran132puntos históricos (22-may..30-sep) +12diasCaso (1..12oct). RL diaria reconciliada SU21 1oct=0.0145748383 y12oct=0.0171936361 m3/t/dia; 7y8oct=0, retomando datosvalidos despues. 80pruebas pasan (65modulos+15integracion). Capturas confirman etiquetas yleyenda sin superposicion con ejeRL. Los avisos externosCORS chequeoversionDash yrequestsobsoletosabortados no afectan las curvas. Reinicializacion de devserver durante primerintento exigio reintento; resultadofinal registrado sinresets. Fuente actual cargada en localhost8065; basta refrescar para ver cambios. Sincredenciales persistidas, sinCalcular ni SP niDBwrites enQA.

## 2026-10-25 - Fechas positivas comunes en Recuperacion y RL
Corregido filtro de _build_recovery_chart que descartaba la fuente Historico reconciliado (oficial) preCaso. Subtab RL ahora compara una misma malla diaria y soporte de fechas donde recuperacion reconciliada y RL seleccionada son ambas >0. La mascara es solo de presentacion, sobre copia de figura; usa None fuera del soporte comun, connectgaps=False y conserva el calendario. No altera ceros/valores fuente ni otras subtabs/metodologia/reportes. Reindexa customdata por fecha para mantener el hover de Cu/TMS y procedencia. Nota del grafico indica cuantos dias son comparables. Helpers puros common_positive_dates/align_values_to_calendar,4tests nuevos.
Verificacion APP:69pruebas pasan. Edge real localhost8065, resultado guardado10013/run10145, sinCalcular/SP/DBwrites: SU21 individual40puntospositivosRec y40RL, mismas40fechas; grupoSU21+SU22 39y39, mismas39fechas. Coincidencia verificada tanto Medido como Reconciliado, con fechaspreCaso incluidas (primera1sep,ultima12oct2026). CeroHTTP>=400 ysinpageerrors; consola soloCORS chequeoversionDash/requestsantiguoscancelados. Evidencia browser_results.json y4PNG en auditorias/alineacion_rec_rl_20261025. Refrescar dashboard para cargar figuras. Sincommit/push.

## 2026-10-25 - Todas las pilas, mas sumas, eje X y hueco 10+11
Auditadas 60 pilas en dos modos (120 vistas). Las 36 incluidas en el Caso tienen soporte positivo coincidente Recuperacion/RL; las 24 fuera del resultado se clasifican sin reconciliacion. Probados 12 grupos en dos modos (24 vistas), parejas, trios, cuartetos, mixto y todos los activos: 19 OX y 17 SU. Fechas positivas iguales y ponderacion Cu recuperado/Cu apilado verificada (error <1.5e-14 pp).
Eje X limitado a primera/ultima fecha visible finita; cero valido, None/NaN excluidos. Corregido ancla historica duplicada el 30-sep que sobrescribia el dato oficial en sumas 10+11. Se conserva estado acumulado, sin cambiar balance/metodologia. Transicion gris solo entre extremos validos adyacentes; no puentea gaps reales.
QA Edge real Caso10013/run10145 PASS: F actual SU10+11 en Recuperacion y cuatro vistas RL pila/grupo Medido/Reconciliado; sin errores HTTP>=400 ni pageerrors. Pruebas: 52/53 inicialmente, corregido namespace pd/np del test restante; los 9 tests de eje/gap pasan al repetir. Evidencia copiada a auditorias/validacion_grupos_eje_20261025. Sin DBwrites, SP, Calcular, commit ni push.

## 2026-10-25 - Presentacion solicitada directamente: historico, Caso y RL
Trabajo realizado por el principal, sin agentes por instruccion expresa para esta tarea. Recuperacion previa al Caso: una sola traza Curva reconciliada historica. Ventana: Recuperacion medida y Recuperacion reconciliada. Sin traza de transicion punteada: el historico continua con linea solida hasta el primer punto reconciliado adyacente, sin inventar fechas ni puentear faltantes reales. Todas las fechas normalizadas Timestamp, eje explicito date y uirevision renovada.
Se elimina la mascara por soporte positivo compartido en RL: RL diaria cero no borra una recuperacion acumulada valida. Cada serie conserva ceros y faltantes de su propia fuente. Esta decision de presentacion reemplaza el filtro registrado anteriormente; no cambia balance, distribucion ni valores de origen. RL medida violeta #8B5CF6; RL reconciliada naranja #E86D1F. Leyenda en dos columnas para separar titulo.
Validacion: 35 tests pasan. Datos reales Caso10013/run10145: OX10+11 y SU10+11 conservan ambas recuperaciones en los 12 dias del Caso. Edge real: cuatro vistas pila/grupo y Medido/Reconciliado; colores, etiquetas, 12 puntos por serie y espaciado Sep29/Sep30/Oct1 verificados en DOM (redondeo Plotly 0.01px). Sin errores de pagina ni HTTP >=400. Primer intento no espero la carga inicial completa; reintento captura todas las vistas. Verificador final browser_verification.json corrige criterio QA anterior que comparaba inicio del eje con recuperacion en vez de incluir RL historica visible. Evidencias en workspace hermano auditorias/presentacion_curvas_20261025. Sin escrituras DB, SP, Calcular, commit ni push.

## 2026-10-26 - RL medida y reconciliada simultaneas, solo ventana del Caso
Instruccion final del usuario reemplaza la radio Medido/Reconciliado: eliminado componente curvas-rl-source y su Input/argumento del callback. Ambas series RL diarias visibles simultaneamente dentro del Caso: medida violeta #8B5CF6, reconciliada naranja #E86D1F. Antes del Caso se muestra solo recuperacion reconciliada historica. Se elimina consulta de riego historico de la subtab RL. Ninguna RL se dibuja antes o despues del Caso. No hay union historica RL ni trazas punteadas. Recuperacion historica/caso mantiene extremos reales adyacentes unidos.
Eje X comienza con recuperacion existente o RL positiva; no lo expanden ceros RL iniciales sin recuperacion. Ceros y faltantes reales del Caso conservados; RL=0 no borra recuperacion. Revision de eje v5 evita conservar el zoom previo. Titulo y leyenda sin superposicion.
QA:18tests pasan (pilas y grupos, ambas RL, ponderacion TMS, faltante solo medido, cero real y recuperacion intacta; eje y union historica). Edge real localhost8065 Caso10013/run10145 PASS en SU26 y grupo F actual SU10+11, sin selector, cinco trazas, ambas recuperaciones 12dias, ambas RL sin valores preCaso, colores correctos y sinHTTP>=400 ni pageerrors. SU26 inicia18sep2026, F inicia1sep2026. Capturas revisadas visualmente; evidencia auditorias/rl_ventana_caso_20261026. SinCalcular, SP, DBwrites ni commit/push. Realizado directamente por el principal segun instruccion del usuario para esta correccion.

## 2026-10-26 - RL historica considerada reconciliada
El usuario aclaro incluir RL previa al Caso y considerarla reconciliada, usando el nombre de la recuperacion con RL: Curva RL reconciliada historica. Agregada traza de RL diaria historica desde riego operativo en el calendario de campania de la recuperacion. Dentro del Caso permanecen ambas RL, medida violeta y reconciliada naranja, sin selector. Historia en tono ocre; ponderacion de sumas por TMS y sin acumulacion diaria. Su ultimo punto se une al primer reconciliado del Caso solo si son finitos y adyacentes, en la misma traza solida. No se inventan datos ni se puentean faltantes reales.
Restaurada consulta historica por PAD con cache acotada24 entradas; cache diaria distingue prefijo historico disponible de modo soloCaso para evitar reutilizar los vacios del cambio anterior. Eje mantiene exclusiones de ceros iniciales sin recuperacion y conserva ceros interiores.
QA18tests PASS. Edge real Caso10013/run10145: SU26 y F actual SU10+11, seis trazas con RL historica, ambas RL del Caso sin puntos previos, sin selector, sin gaps artificiales en limite, eje sin tramo inicial vacio, sinHTTP>=400 ni pageerrors. Captura SU26 revisada visualmente. Evidencia auditorias/rl_historica_20261026. SinDBwrites/SP/Calcular/commit/push; correccion directa del principal.

## 2026-10-26 - Eje Y desde recuperacion inicial de campania
Aclaracion del usuario sobre OX-P30: el eje Y debe partir en la minima inicial. Consulta real confirma campania vigente con primera recuperacion primaria 0.8668012268859595% el5nov2025. Historico reconciliado visible comienza1sep2026 en68.083276%, lo que causaba autoescala68..70. Ajustado limite inferior Y con primera recuperacion de campania activa, filtrando ini_aporte y fecha del Caso; no se altera ni rellena ningun punto historico. Para sumas se pondera inicial por CuTf; si no existe inicial, se conserva autoescala. Limite nunca recorta valores visibles inferiores. Escala se conserva al copiar figura a Recuperacion y RL y cambia revision del eje para evitar zoom antiguo. Sin modificaciones en balance/metodologia ni DB.
QA:42tests de curvas/grupos/RL pasan. Verificacion real de _build_recovery_chart OX-P30 Caso10013/run10145 devuelve yaxis.range=[0.8668012268859595,72.48912199443069]. Audit inicial_values.json en workspace hermano auditorias/ox30_20261026. Agente Luna reviso causa/cobertura, principal verifico DB y aplico eje. SinSP/Calcular/commit/push.

## 2026-10-26 - Auditoria exhaustiva de ejes, todas las pilas del Caso
Solicitud verificar TODAS. Verificadas60posiciones en Caso10013/run10145 (1..12oct2026): 36activas (19OX/17SU),24sinresultadoenCaso. Oraculo independiente lee todos los ciclos primarios filtrados por ini_aporte WIP y finCaso; ninguna activa sin lectura inicial. Principal verifico36graficos de recuperacion y12sumas contra iniciales independientes, incluyendo grupos completos19OX/17SU: error inferior Y maximo0.0, sinrecortes. Agente Luna construyo36graficos RL reales y confirmo que el rango Y1 se conserva identico en todos;12grupos tambienPASS. Entregables del agente revisados por principal. No se atribuyen resultados a24inactivas.
Agregada regresion test_individual_and_group_initial_axes_exclude_previous_campaigns: cicloantiguo0.001 excluido del inicialvigente10/20, suma ponderada100/300 resulta17.5. Dos tests de grupo relacionados pasan; restantes46pasaron previamente sin nuevos cambios en funciones. No hicieron falta ajustes adicionales en la aplicacion: regla general ya cubre todas las activas. Evidencia auditorias/ejes_todas_20261026, CSV Auditoria_Ejes_Todas_Pilas.csv y resumen JSON. SoloSELECT, sinSP, DBwrites, Calcular, commit ni push.

## 2026-10-26 - Historial completo de recuperacion, no solo escala inicial
Usuario detecto OX-P01 limitada a Sep-Oct. Auditoria anterior comprobaba ejes, no cobertura historica; persistia filtro que ocultaba lecturas primarias previas a fixture oficialSep. Corregido: _historical_recovery_values conserva baseline original ANTES de completar solo puntos historicos visibles con lecturas primarias fechadas donde no hay punto oficial/persistido. Oficial validado y reconciliado guardado conservan prioridad. Origen interno explicito Historico reconciliado (registro historico); leyenda sigue unica Curva reconciliada historica. Tags ya aceptados por grafico individual y sumas. No interpolar niinventar; excluir antes ini_aporteWIP y curvas de otras campanias. Contratohelper tripledefault, cuatrovalorescon return_sources=True.
Verificacion real antes/despues36activasCaso10013/run10145: antes35confechas primarias omitidas, despues0; restaurados5164puntos. OX01 muestra289lecturas anteriores al Caso desde16dic2025, conservando exactamente TODAS las recuperaciones medida/reconciliada del Caso en36pilas. Las12sumas tienen todas las fechas comunes disponibles; diferencia ponderada enCaso max1.42e-14pp porredondeo. Baseline numerico, solver y Cu neto del Caso no cambiaron.
53tests pertinentes pasan contando51 iniciales + regresion actualizada de traza historica + nueva prueba de historial en grupos. Fuente de agente Luna revisada/rebasada por principal para preservar cambios de Y y corregir filtrado de sumas y contrato. Verificacion visual Edge: captura OX01_recuperacion_completa.png confirma curva desdeDic2025 hastaOct2026 con evolucion desde0.1437%; smoke mas amplio RL fue interrumpido por recarga del devserver al actualizar tests, sinHTTP>=400. No afirmar PASS de ese smoke completo. RevisionUI renovada para no conservar zoomSep antiguo. Evidencia en auditorias/historial_completo_20261026. Sin escriturasDB/SP/Calcular/commit/push.

## 2026-10-26 - Nueva subtab Recuperacion vs RL acumulada
Agregada tab-rl-acum y grafico curvas-recon-chart-rl-acum. X RL acumulada(m3/t), Y Recuperacion(%); historica gris, medida violeta y reconciliada azul. Usa historia completa de recuperacion y Q desde primer riego positivo de campania, consultando desde apilado.f0 para no perder riego previo a primera recuperacion. Denominador TMS apiladas al corteCaso. No reset en semanaCaso. Grupos: suma volumen de miembros desde su nacimiento / sumaTMS, no mediaRL. Se preserva rango inicialY y temaInter/blanco; ejeXnumerico sin rectangulos de fechas heredados. Hover incluye fecha,RL yrecuperacion.
Callback independiente lazy, con metadatos cargados solo al abrir si es necesario; fastbranch principal evita recalcular barras al alternar. RL diaria anterior conserva su semantica. Caches diarias ahora incluyen limites reales del DataFramehistorico: una vista diaria con prefijo corto no envenena la acumulada. Helper cumulative_campaign_rl: calendario normalizado completo; prefijo anterior primerQpositivo no suma, ceroexplicito conserva plateau; gap desde inicio vuelve desconocidas fechas posteriores. Si nunca hay Qpositivo, no se inventa0 en datosfaltantes.
QA automatizada: helpers, grupos distintos TMS/fechasnacimiento, campania sinreset, cero, huecos, caché, conservacionY/tema, fechas hover, visibilidad/callbacksinSQL al inactivo; regresiones35curvas/historicos/ejes pasan. Verificacionreal36pilas+12sumas Caso10013/run10145: errorXmaximo0.0 contra sumaindependiente de volumen; Ysinmodificaciones y Xmonotono. Edge realPASS OX01, SU26 y Factual:3trazas, ejeXlinear y ejeYRec sinsegundoeje, historia completa y RLdiaria intacta;0pageerrors/HTTP>=400. Evidencia auditorias/rec_vs_rl_acumulada_20261026. AgenteLunastaging revisado/aplicado/verificado por principal. SinDBwrites/SP/Calcular/commit/push, sin cambios en solver ni reporteExcel.

## 2026-10-26 - Nombre de magnitud diaria: Tasa de lixiviacion
Por instruccion del usuario, RL noacumulada pasa a Tasa de lixiviacion(m3/t/dia): subtab Recuperacion y tasa de lixiviacion, eje derecho, leyendasmedida/reconciliada/historica, hover y notas. Reporte: hojas Tasa lixiviacion Oxidos(23) y Tasa lixiviacion Sulfuro(24); resumen Tasa de lixiviacion [m3/t/dia]. RLacumulada conserva nombre/calculo/subtab. IDs tab-rl/curvas-* y APIs/claves rl/rl_curve quedan para compatibilidad; cumulative_rl sigue siendo el helper diario legacy, cumulative_campaign_rl el acumulado.
Root comparoAST antes/despues normalizando textos/hover: aritmetica, control de flujo y APIs sin cambios; helper acumulado identico. Validacion62pruebas unicas PASS:37UI/helpers/acumulado y25reporte. Reintento de testsreporte con basetemp nuevo en auditoria resolvio permisos del temporal general; no es fallo del exportador. StagingLuna revisado/aplicado por principal. Sin DBwrites/SP/Calcular/sync/commit/push. Resumen auditorias/tasa_lixiviacion_20261026/RESUMEN.md.

## 2026-10-26 - Paneles y bandas para grupos; protocolo operativo Sol6.1
Corregida selecciongrupal: render_recon_pila_charts recibegrupo/grupos y entrega panelesFlujos/Cu sin depender de pilaindividual; Recuperacion mantiene wrappergrupal. Nuevo group_solution_series agrega Q y CuporΣQCu/ΣQ, preservando faltantes y ceroQ/Cuindefinido. group_solution_charts lee una ventana porPAD/rango, usa rawdiariovalidado enCaso y cache16grupos. HistoriaPLS mantiene proxyFDRENA_MAX*riego; no cambia solver. Bandas ws..we+1 enRecgrupal, Tasa heredada y ambos panelesFlujos/Cu. RLacumulada usa bandanumerica baselinews-1..maxdosiswe entre ramas; no fechas en ejeXnumerico.
Validacion37testsPASS. Caso10013/run10145:12grupos y576controlesCaseQ/Cu vsraw, errormax0.0; auditagrupadaen2lecturasmaterialPAD. EdgePASS enFactual5subtabs conbandas visibles (1,2,2,1,1), sinpageerrors/HTTP>=400. Evidencia auditorias/graficos_grupos_20261026. HelperLuna; integracion/pruebas/revisionprincipal. SinDBwrites/SP/Calcular/sync/commit/push.
Por peticion explicita se envioSol6.1 aoptimizartrabajoDB+Dash+metalurgia: protocolo docs/FLUJO_DB_DASH_METALURGIA.md revisado yreferenciado enAGENTS. Adoptadas reglasoperativas decontextominimo, unresponsableporarchivo, snapshotidentificado, batchingporPAD/rango, pruebasporriesgo, UIalfinalconfuenteestable ysalidasresumidas. ModelosLuna/Sol/Astra seguncomplejidad se describen comorecomendacion, sin sobreescribirpreferenciaexplicitaLunani configuracionglobal. No se inventancostos/precios/ahorro de tokens.


## 2026-10-26 ? Grupos como pilas virtuales en Excel

El callback de descarga captura los grupos locales del navegador y los pasa al writer opcionalmente. El reporte agrega resumen Pilas virtuales y una hoja Virtual NNN por grupo con miembros, recuperaci?n ponderada por CuTf, Cu neto acumulado, producci?n diaria, riego y tasa. No incorpora virtuales a las hojas f?sicas ni totales. Grupos inv?lidos devuelven motivo; no se omiten miembros. Sin grupos se conserva el reporte previo.

Validaci?n: 38 tests aprobados; callback real con descarga base64, gr?ficos, gaps e invariancia de hojas originales. Snapshot offline Caso10013/run10145 (1?12 octubre): 36 f?sicas y 12 virtuales, 24 gr?ficos, error m?ximo 1.42e-14 puntos porcentuales, hojas f?sicas id?nticas. Snapshot no contiene rl_curve; no se inventan tasas. Sin consultas/escrituras DB nuevas. Evidencia en repositorio vecino curvas_recon/auditorias/reporte_pilas_virtuales_20261026.


## 2026-10-26 ? Vista global de recuperaci?n reconciliada

Bot?n Ver todas las recuperaciones reconciliadas abre un modal con gr?ficos OX/SU separados y RangeSliders independientes por antig?edad al cierre del Caso. Muestra historia reconciliada y tramo del Caso, sin medido ni fechas posteriores. Cada filtro selecciona pilas completas y conserva su historial; edad desde primer Q positivo de campa?a. Dataset cacheado por Caso/run/token/ventana, una carga material compartida por pad; sliders s?lo filtran en memoria. M?dulo nuevo vista_todas_reconciliadas.py; _reconstructed_campaign_series admite material opcional sin alterar llamadas previas.

33 tests aprobados; layout real63IDs ?nicos/31callbacks idempotentes. Edge en harness aislado con snapshot10013/run10145:19OX/17SU, filtros independientes comprobados sin errores. Servicio8065 inactivo duranteQA; harness8076 detenido despu?s. Evidencia en repo vecino curvas_recon/auditorias/vista_todas_reconciliadas_20261026. Sin escriturasDB/Calcular ni cambios de metodolog?a.


### Revisi?n vista global: slider, velocidad y habilitaci?n
Slider ?nico con m?nimo fijo0 para ambos pads, ancho520px, separaci?n y gr?ficos390px. Filtros ahora clientside sobre figuras ya preparadas: no reenv?an datasets ni ejecutan Python/DB al cambiar edad. El bot?n inicia disabled y se habilita s?lo con Store/raw calculado v?lido del Caso seleccionado. Verificado4tests y Edge con snapshot36pilas; filtro392ms, ceroPOST, independencia pads y desactivaci?n al vaciar Store. Medida del harness aislado, no de DB/apertura inicial. Evidencia actualizada en auditor?a vista_todas_reconciliadas_20261026.


## 2026-10-26 ? Correcci?n del formato din?mico del reporte

Rec/Prod/Tasa reservan todas las posiciones32OX/28SU (m?s IDs nuevos si existen). Construcci?n incluye historial de campa?as actuales aunque la pila no est? en la corrida; s?lo se aplica ajuste del Caso a quienes tienen filas reconciliadas. Sumatorias locales ahora son columnas en Rec y series con leyenda ? nombre en ambos gr?ficos del pad. Ya no se anexan hojas virtuales separadas. Grupos mixtos se rotulan [OX+SU] expl?citamente en ambas vistas; las sumas no entran en producci?n f?sica ni totales. Nuevo report_columns.py.

28tests aprobados, incluidas descarga, formato e inactiva sin ajuste del Caso. Snapshot offline10013/run10145 con12grupos:32+6columnasOX,28+7SU, series ponderadas y leyendas verificadas. Evidencia en repo vecino curvas_recon/auditorias/reporte_dinamico_20261026; preview marcado Snapshot, no DB fresca. Sin escriturasDB ni cambios al solver.


## 2026-10-26 - Cinco ajustes de RL, controles y sumas
RL acumulada se llama RL en UI. Vista global bajo esquema y encima de subtabs; Suma de curvas en barra de calculo; Nueva suma limpia ID/editor sin sobrescribir anteriores. Informe RL Oxidos/RL Sulfuros usa volumen acumulado/TMS desde primer riego, con gaps estrictos y sumas ponderadas; mantiene rl_curve diaria para compatibilidad. Vista global incluye grupos locales ponderados por Cu apilado, recalcula al editar grupos y mantiene filtros clientside. Edad de suma desde miembro mas antiguo.
Validacion:45 regresiones+4 nuevas; RL reconciliada y sumas numericas comprobadas,33callbacks idempotentes. Edge sobre snapshot36pilas+3sumas,leyendas/filtros correctos,ceroPOST al filtrar,322ms observados. Sin DB fresca, sin escriturasDB/solver. Evidencia vecina auditorias/rl_informe_20261026/RESULTADO.md y browser_results de vista_todas_reconciliadas_20261026.


## 2026-10-26 - Reconstitucion retomada: run actual y lecturas mas rapidas
Verificada online mediante SELECT la ruta125 de Caso10013/run10145 (1-12octubre): F18=0t, F19=728062.4073t,5modulos,16turnos,cuadratura<1e-6t. Caso8/run47 legado120: F15=0t,F14=598606.93344t,5modulos,15turnos,cuadratura<1e-6t.
En reconstitucion/modelo_flujos.py se agrego OPTION(RECOMPILE) al SELECT del perfil y se acoto el LAG de horas al rango solicitado mas timestamp anterior como contexto. Perfiles y horas anteriores/nuevos comparados en ambas ventanas sin diferencias; no cambia distribucion ni metodologia. La separacion perfil/humedad no se integro por no mejorar el costo.
Tiempo total observado10013:17.221->13.070s; Caso8:18.737->2.960s. Persiste cuello12s en vista de totalizadores para octubre.41tests offline pasan y git diff --check limpio. Browserreal8065 confirma carga10013 en12.643s y Gantt con16segmentos medidos/5proyectados,5modulos,pendiente0t,sin erroresHTTP/page. Sin DBwrites/SP ni cambios de esquema/indices. Evidencia en repo vecino curvas_recon/auditorias/retomar_reconstitucion_20261026/RESULTADO.md. SQL descargado es evidencia,no instrucciones.


## 2026-10-26 - Revision independiente Astra (metodo) y Luna (graficos)
Usuario pidio explicitamente Astra para esta revision (excepcion de modelo solicitada). Sin cambios al producto/DB. Se capturaron por SELECT fuentes y resultados10013/run10145 y8/run47 una vez; snapshots/hash reutilizados sin repetirSQL por agentes.
Astra: balancesPAD cierran, pero proyeccion no coincide con masa/tasa. Real PAD2/C12/M5 completo en octubre:57.6583h vs47.3242h por masa asignada/tasa (+21.8367%). Calculo usa volumen*rho_semanal/tasa; debe resolverse semantica/documentacion antes de corregir. M4 es parcial y no se uso como demostracion. Riesgo sintetico de perfil positivo en fecha sin volumen eliminado y reescalado a otros dias; no ocurre en las2ventanas actuales (0perfil positivo excluido). No validar Cu por modulo ni simultaneidad de ambosPADpositivos a partir de estos casos.
Luna: barras/08-08/gaps/carriles/hover desktop correctos,30tests offline pasan. Defecto movil390px: tooltip fuera de viewport y recortado. Harness con wrapper real, snapshot verificado; servidor8077 detenido.
Informes/evidencia en repo vecino curvas_recon/auditorias/validacion_reconstitucion_astra_luna_20261026/RESUMEN_VALIDACION.md, metodo/INFORME_METODOLOGIA.md y graficos/INFORME.md. Son hallazgos de revision, aun no correcciones implementadas.


## 2026-10-26 - Correcciones Astra aplicadas y recomendacion intraturno
Aplicado: engine.module_itinerary usa masa_total/rate_masa_h para duracionbase, con controles previos rho_proy/tasa elegibles, sin cambiar ajustes de modos. proy_masa_t explicita masa de seleccion. modelo_flujos.distribute_profile bloquea perfil positivo/humedad irresuelta sin volumen GLOBAL en fecha, sin reasignarlo a otrosdias; ceros y actividad porPAD distinta admitidos. panel hover compacto sin extra, masa/duracion de seleccion y densidad referencia; presentacion etiqueta referencia y nota de parciales.
Verificado41tests existentes+7nuevos, sourceactivo y snapshots: masas/volumen/shift_table intactos, error nuevo duracion-masa/tasa0h, M5 PAD2/C12 ahora47.3242h. Browser panelactivo+snapshot corregido:8/8hovers desktop390px dentroviewport; sin pageerrors, servidor8077 detenido. Sin DBwrites ni nuevas consultas durantecorreccion.
Usuario pregunto si usar TMH para hora de cambio. Astra recomienda reconstruccion con acumuladoTMS=deltaTMH*(1-H/100), rutaPAD/orden conocidos, cruce de umbral de masa; con densidad comun equivale a fraccionvolumen. Factorreconciliado comun se cancela,no anade informacionhoraria. Loader actual A/B no da hora observada; validar primero totalizadores intraturno (resets/gaps/unidades/destino). Separar de proyeccion masa/tasa. Estimador intraturno NO implementado con esta pregunta. Evidencia ../curvas_recon/auditorias/correcciones_reconstitucion_20261026/RESULTADO.md.


### Aclaracion posterior: metodo TMH propuesto por el usuario
Usuario recuerda que la correa mide masa humeda y pide compararlo con su propuesta. Astra rectifico: no exigir conversion TMS para la hora solo porque objetivo oficial sea TMS. Cruce W(t)/W_dia=fraccionvolumen es valido bajo densidad HUMEDA comun; S(t)/S_dia usa densidad SECA comun. Con humedad comun, fracciones equivalentes; con humedad variable pueden cambiar tanto hora como TMS derivada por modulo. Mantener TMSmodulo=q*TMSdia y a la vez frontera humeda=q*TMHdia no es identidad general. Elegir contrato antes de implementar.
Comparacion offline con snapshots: umbral hipotetico40% y distribucion uniforme dentroturnoA/B, diferencia maxima9.062seg agosto y0.169seg octubre. No son precisiones observadas. Preferencia razonada para reconstruccionfisica propuesta: TMHacumulada normalizada, ruta/orden y densidadhumeda declarados; objetivoTMS para balance y proyeccionTMS/tasa. Falta validar serie intraturno para hora mas precisa. No se implemento nuevoestimador con esta pregunta. Informe ../curvas_recon/auditorias/validacion_reconstitucion_astra_luna_20261026/metodo/COMPARACION_TMH_TMS.md.


### Comparacion pedida TMH vs metodo ACTUAL (fronteras de modulos, no umbral40%)
Luna comparo snapshots10013/run10145 y8/run47, recalculando motoractivo corregido (no usando itinerario viejo del pickle). Actual: asignacionvolumen y boundaryTMS_A/TMSdia; no emite cambio horario observado, proy_fin es masa/tasa encadenada. PropuestaTMH: umbralfraccionvolumendiario en TMHacumulada, con orden actual poravance/modulo e interpolacionuniformeA/B12h.5fronterasagosto y6octubre: diferencias frenteaderivacionhorariaTMS maxima1.58segagosto y0.0045segoctubre. Son cifrasmatematicas,noprecisionmedida.
Ejemplo moduloPAD2/C12/M5 cierre6oct:proy_fin actual03:33:51.932 vscruceTMHestimado15:37:10.801 (12.055hde distancia). Comparan proyeccion ideal y reconstruccion retrospectiva,noerror contraobservacion. Fuenteactual recalculada conserva shift_table de snapshot. No se implemento el estimador nuevo ni hubo SQL/escrituras. Informe yCSV en ../curvas_recon/auditorias/comparacion_tmh_vs_actual_20261026/COMPARACION.md.


## Reconstitucion sin tasa de referencia — 26-10-2026

Se retiro por completo la proyeccion por tasa de referencia del motor y de la interfaz de Reconstitucion de Modulos.

Para cada dia operacional, el tonelaje humedo asignado a cada modulo determina un umbral acumulado. La hora se obtiene cruzando ese umbral con el acumulado real de la correa. Se utilizan incrementos de totalizadores de 10 segundos, validados contra la TMH publicada por turno. Las pausas reales no se sustituyen por capacidad nominal.

La fuente actual no contiene un pesaje humedo independiente por modulo: la asignacion procede de su fraccion del volumen diario. El orden se infiere por avance descendente y numero de modulo. Por eso la hora es reconstruida, no un registro observado del cambio. Si falta un perfil intraturno valido, se declara la interpolacion A/B de 12 horas; no se usa una tasa de referencia. Si hay varios PAD activos sin ruta identificable, se rechaza la reconstruccion ambigua.

Verificacion con entradas congeladas hash-verificadas, obtenidas mediante consultas de solo lectura:

| Caso/run | Intervalos diarios | Modulos | TMH asignadas | TMS asignadas |
|---|---:|---:|---:|---:|
| 10013/10145 | 16 | 5 | 756369 | 728062.4073 |
| 8/47 | 15 | 5 | 635088 | 598606.93344 |

En ambos casos todos los bloques positivos de 10 segundos cierran exactamente con la TMH por turno. El balance y la tabla de asignacion seca conservan sus resultados. La TMS asignada es un contrato separado del reloj humedo, no una integral seca del intervalo reconstruido.

Ejemplo: modulo 5, campana 12, 6 de octubre de 2026: fin reconstruido 15:31:31 con perfil de 10 segundos. La estimacion previa A/B era 15:37; la diferencia refleja el perfil intraturno.

Fuente activa: DashReportabilidadSIIR/reconstitucion. Evidencia: verificar_activo.py, verificacion_datos.json. Respaldo previo: antes_del_cambio/. No se escribieron datos ni se ejecutaron procedimientos almacenados. Sin commit ni push.


## Reconstitucion por turnos y detalle — 27-10-2026

Grafico por TA (08-20) y TB (20-08), barras azules del horario reconstruido y marcas verticales naranjas en cambios entre modulos. Se retiro la barra naranja diaria del nuevo grafico. Respaldo del codigo, HTML y captura anterior en ../curvas_recon/auditorias/reconstitucion_turnos_popup_20261027/respaldo/.

Tabla compacta con popup por fila; clave validada contra el resultado en servidor y guardas de Caso/run/periodo. Cerrar limpia active_cell para reabrir la misma fila. El detalle usa apilado, shift_table, perfil_turnos y horas_turnos ya cargados, sin consultas adicionales. Las masas secas por turno conservan la asignacion original, no se fabrican masas por intervalo de reloj.

Los sinteticos detectaron y permitieron corregir redondeo de acumulados en fronteras que coinciden con una pausa. Se conservan los dos lados de la pausa (fin previo e inicio posterior). Suite activa: 59 passed.

Evaluacion del HTML solicitada: intervalos de casos 10009/run10082 y 10013/run10145, mas siete escenarios sinteticos. Caso 10009: cuatro segmentos con 10 s validado y tres con interpolacion A/B declarada; no presentar todos como perfil intraturno valido. Caso 10013: 16 segmentos con perfil 10 s validado. Lecturas SQL solamente; sin procedimientos ni escritura de datos, commit o push.


## Correccion de ejes de reconstitucion - 27-10-2026

Un carril por Pad/Campana/Modulo en el eje Y. TA 08:00 y TB 20:00 se muestran solamente en el eje de fechas X. Se mantienen segmentos por turno, marcas naranjas y tabla con popup. El HTML de comparacion de metodologias de reconstitucion tambien se corrigio; QA calendario ambos casos y movil sin errores. Suite reconstitucion: 59 passed. Evidencia en ../curvas_recon/auditorias/reconstitucion_eje_turno_x_20261027/.


## Reconstitucion: tabs PAD e informe optimizado - 28-10-2026

Retirados los dropdowns de modulo y PAD del informe. `reconstitucion-pad-tabs` (1 Oxidos, 2 Sulfuros) filtra resultados y determina el informe descargado; al cambiar se limpia el popup. No se cambio la metodologia de asignacion.

Exportacion: limpieza solo de celdas materializadas, sin modificar estilos; XLSX cacheado por resultado/token y PAD. Se mantienen guardas de Caso/run/periodo y boton desactivado mientras genera. Igualdad de valores, estilos, merges y hojas verificada contra baseline para Casos10009/10013 y ambos PAD. Suite93passed. QA navegador con fuentes congeladas/capturadas: Sulfuros primera descarga1.116s, repetida0.197s, Oxidos2.137s (sin latencia SQL); errores JS/HTTP0 y movil390px sin overflow. Repeticion produce mismos bytes. Evidencia ../curvas_recon/auditorias/reconstitucion_informe_tabs_20261028/.

El popup instalado previamente usa claves Caso/PAD/campana/parcela/modulo/fecha/turno, masas del motor y perfil de calidad atribuido. `mov_cam` se consulta de forma diferida por fecha/turno/CH01 y se muestra como contexto secundario: no identifica modulo.


## Informe de m?dulos: atributos de material apilado - 28-10-2026

La descarga integra 23 campos adicionales por modulo: sal, seis atributos SRR, cinco CSR y suma, cinco ACF y suma, tres controles de calidad y suma. Se incorporaron la clasificacion contractual y AE=Z. Mina+Stock se asignan al modulo por sus masas/turnos y participacion de origen; ACF/control se ponderan por masa y CSR por cobre. SRR se pondera por la masa de ese origen asignada al modulo. No se inventa caracterizacion SRR faltante en los ACF/CSR de Mina+Stock. DETALLE conserva fuentes, alcance y cobertura.

`fuentes_informe.cargar_fuentes` realiza tres SELECT acotados al rango (mov_cam CH01, SRR por turno y Datos_conciliados_of medido para sal), sin SP ni escrituras. Los atributos se cargan solo al descargar; popup mantiene loader basico. No se cachean informes con advertencias de fuentes para permitir reintento. No cambia masa ni horario de reconstitucion. Tabs strings1/2 y tabla vacia persistente conservados.

Validacion con fuentes capturadas:7modulos Casos10009/10013; ACF/CSR/control coinciden con auditoria previa, SRR dentro4.7e-9, sal cobertura100%. Descarga en navegador Caso10013 contiene115celdas adicionales,5modulos; repeticion bytes identicos, sin errores callbacks/JS. Render de nuevos bloques conforme plantilla. Evidencia ../curvas_recon/auditorias/reconstitucion_informe_cobertura_20261028/. Fuentes pendientes de definicion no se rellenan con cero.

Se incorporo tambien DL inicio de reposo desde campana_parcela_control, consultando solamente PAD y claves campana/modulo del resultado. Se verificaron C11/M134 yM135 con fechas06-09-2026 y09-09-2026; fechas ausentes se conservan sin dato. No se confunden identificadores internos con numero_campana/nombre_modulo. Pruebas de fuente acotada, cruce de campanas y ausencia aprobadas.


## Formulas de plantilla en informe de modulos - 28-10-2026

El exportador conserva/restaura formulas validas de MODULOS por PAD desde la plantilla, en vez de reemplazar salidas con valores Python. Entradas del Caso se escriben en sus columnas; se eliminan datos y formulas historicas fuera de filas emitidas. Resumen por clave campana/parcela, rangos cerrados a filas del grupo: TMS, humedad por TMH y recuperacion por fino Cu segun ecuacion oficial. Se conserva fecha de reposo explicita; formula DL=D guardada solo como fallback. S=CuS/CuT en SU conforme plantilla. No se agregan ecuaciones SU a columnas OX que no las tenian. Formato de resumen se copia a la fila dinamica, incluyendo cuando empieza en mitad de un bloque historico. Sin fuentes se conserva vacio y con cero medido se conserva cero.

QA:92comprobaciones de recalculo artifact-tool sin diferencias ni errores de celda (2casos reales, OX con2campanas, ausencias/ceros).21pruebas focales pasaron inicialmente; tras guardas/formato/reposo mixto,7pruebas del escritor pasaron. Excel COM no disponible en esta sesion, por lo que no se declara validacion de Excel nativo; libro conserva fullCalcOnLoad=True. El renderer artifact-tool genera PNG y resultados correctos, pero su proceso finaliza con codigo1 sin error de celda; evidencia guardada, no confundir con validacion Excel nativo. Auditoria ../curvas_recon/auditorias/reconstitucion_formulas_20261028/.

Resumen de fuentes y SP integrado en docs/RESUMEN_FUENTES_RECONSTITUCION.md. La seccion consulta SELECT a tablas/funciones; no ejecuta SP productor ni SP actualizador de cache.


## Control mineral, controles y comparativo actualizado - 28-10-2026

Corregido BE:BG de Sulfuros: son entradas numericas en su plantilla, mientras en Oxidos son formulas. El escritor protege solo las columnas cuyo patron de plantilla es realmente una formula, conserva entradas Calidad01/02/03 del dataframe y mantiene BH como suma formulada. Diagnostico contra Downloads/informe_modulos_sulfuros_caso_10013_run_10145 (3).xlsx confirmo atributos en DETALLE y MODULOS vacio; el reexport ya los contiene. Prueba de regresion diferencia ambos PAD. Verificacion de recalculo ampliada a132comparaciones, sin diferencias. Auditoria ../curvas_recon/auditorias/reconstitucion_control_mineral_20261028/.

Retirados el control de rango deshabilitado junto a Cargar datos y el mensaje inicial de itinerario; se conserva metadata de fechas del Caso y se retiro callback de rango. Grilla selectorCaso+boton; siete callbacks. Pruebas:14casos/integracionHTTP y9layout/catalogo; navegador QA confirma ausencia del rango/mensaje y navegacion ambosPAD sin errores.

Comparativo principal Informe_Simple_Reconstitucion.html actualizado desde los XLSX actuales recalculados (Casos10009/run10082 y10013/run10145), 7modulos. Salidas y scripts en auditorias/reconstitucion_informe_comparacion_20261027 y outputs/reconstitucion_modulos_casos_20261027. Fuentecongelada, no se afirma frescura SQL online.
