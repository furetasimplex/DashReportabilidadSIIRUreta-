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
