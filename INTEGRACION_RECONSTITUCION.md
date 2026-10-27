# Reconstitución de Módulos integrada en SIIR

Integración del 12/10/2026 desde `C:\Users\5330\Desktop\Reconstitucion`.
La sección «Reconstitución de Módulos» se abre desde el menú lateral usando
la única app Dash, autenticación, encabezado y paleta existentes.

## Cableado

- `layout.py` añade navegación, selección activa y breadcrumb. Crea el árbol
  del panel solo al entrar y lo conserva al navegar a otras secciones.
- `tabs/tab_reconstitucion.py` registra callbacks idempotentes e inyecta
  `db_connection.get_engine` mediante un proveedor diferido. El esquema fuente
  es explícito: `inventar_SpcHidr.inventar_SpcHidr`; no se sustituye por DEV_SIIR.
- `reconstitucion/` contiene motor, SQL de lectura, validaciones y presentación
  con imports relativos. No carga un `.env` propio ni ejecuta SQL al importar,
  registrar callbacks o montar la sección.
- `assets/reconstitucion.css` encapsula estilos dentro de `.reconstitucion-shell`
  y usa variables del tema SIIR. IDs propios `reconstitucion-*`.

«Actualizar Casos» lee el catálogo oficial compartido con Curvas. «Cargar datos» consulta la masa validada del Caso seleccionado y utiliza su período exacto; las fechas son de solo lectura.
El botón muestra «Calculando…» y queda deshabilitado durante la petición.
Los filtros actualizan resultados en memoria. Se preservan la autenticación,
validación SQL de arranque y todas las secciones anteriores.

## Gráfico y metodología conservados

Hay un único Gantt con identidad completa pad/campaña/módulo. Naranja representa
días operacionales con volumen medido, 08:00–08:00; no horas efectivas de operación.
Se omiten días sin volumen. Azul aparece en otro carril solo cuando la proyección
dispone de densidad y tasa válidas, evitando superponer la misma información.
El hover muestra masa y volumen diarios y la tabla cronológica permanece plegada.
«Consideraciones» abre y cierra el modal manualmente.

El total oficial se conserva, turnos conocidos en cero siguen en cero y los
datos ausentes permanecen ausentes. La masa sin volumen queda pendiente global,
sin asignarse arbitrariamente a un módulo. Septiembre medido de las pruebas y
preview del origen no es un fallback automático de la fuente oficial en SIIR.
Por tanto, si esta fuente sigue cerrada al 31/08/2026, cargar agosto-septiembre
mostrará la cobertura oficial disponible, no inventará reconciliación septiembre.

## Pruebas offline

Desde el repositorio destino, usando su entorno:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider test_integration.py reconstitucion/test_integration_module.py reconstitucion/test_metodologia.py reconstitucion/test_casos.py curvas_recon/test_integration_module.py curvas_recon/test_bar_metrics.py curvas_recon/test_actividad_vectorizada.py
```

54 pruebas pasaron en staging: 14 HTTP de SIIR, 5 del panel/gráfico nuevo,
14 de metodología y 21 regresiones de curvas. SQL y ODBC están bloqueados en
la fixture de integración; solo esa fixture sustituye la validación de arranque.
No se consultó ni modificó la DB, ni se abrieron XLSX. Los tests nuevos son
portables: no dependen de `preview.py` ni de snapshots o rutas del repositorio origen.

La revisión visual interactiva queda pendiente: el control de navegador no tiene
un navegador disponible en esta sesión. Las pruebas de geometría, colores, hover,
identidad única y ausencia de superposición son offline; no sustituyen esa revisión.

## Límites operativos

La cuenta de conexión SIIR debe tener lectura sobre el esquema fuente explícito.
El caché conserva hasta 16 sesiones por proceso. Reiniciar, expulsar una sesión o
cambiar de worker requiere recargar; para múltiples workers hacen falta afinidad
de sesión o caché compartida. No hay persistencia ni escrituras de resultados DB.
La exportación del dashboard legado no se integra en este panel; los scripts
y plantillas originales permanecen en Reconstitucion. No se copió su `app.py`
standalone, `.env`, ni informes/datos al servidor anfitrión.

Validación tras aplicar en destino: 54 passed en 19.86 s; git diff --check limpio. main.py conserva el hash previo a la integración.
## Reconstitución de Módulos por Caso — 12/10/2026

Nombre visible actualizado en menú, breadcrumb y panel. El selector usa el mismo catálogo oficial 1..8 de `curvas_recon.db_pipeline.load_casos`, inyectado por proveedor lazy del puente. «Actualizar Casos» realiza la lectura explícita; montaje/registro/filtros no consultan SQL. Las fechas son de solo lectura y proceden de recon_caso; no hay rango independiente.

La carga exige Caso seleccionado, fija su ventana exacta y consulta masa por caso_id, origen AJUSTE_REPORTE y estado validado (preserva COALESCE histórico). Se filtra Caso antes de elegir la última validación por fecha. No exigir es_activa permite reconstruir publicaciones históricas validadas sustituidas por otra ventana; sin masa del Caso no se rellena desde otro Caso ni desde base medida. No se recorta a extremos globales para ocultar huecos de cobertura. No se cruza el nombre con casos_balance para Casos del solver nuevo.

Relación comprobada en ajuste_reporte/rep_prod_adjuster.py: run_ajuste_reporte_prod_solver_nuevo conserva recon_caso.id en el pipeline de reportabilidad; run_id de reporte es UUID nuevo, distinto del solver_run_id entero. Publicación SP copia Caso y UUID con origen literal AJUSTE_REPORTE. El resultado identifica Caso/ventana en pantalla y guarda toda su identidad (incluido run oficial) en caché. Consideraciones explica que no se certifica correspondencia entre UUID histórico y run oficial actual. No se realizó SQL real ni escritura, y no se ajustaron masas/cálculos ni se ejecutó SP.

Cambiar Caso, fechas del catálogo o run oficial invalida visualización y detalle de resultados antiguos; una respuesta tardía de carga A no se muestra como B. El token continúa aislando resultados por sesión. Nuevas pruebas cubren catálogo compartido, periodo exacto, IDs con fechas iguales, respuesta tardía, cambio de run y periodo, ausencia de masa, SQL parametrizado histórico y ventana sin recorte global. Sin cambios a main.py, autenticación o validación SQL de arranque.


Verificación del cambio por Caso: 63 pruebas offline pasaron en el repositorio destino (66.06 s). Incluye 15 HTTP SIIR, 8 regresiones nuevas de Casos, panel/Gantt, metodología y curvas. git diff --check limpio; main.py conserva el hash anterior. SQL real y navegador interactivo no verificados. Sin commits ni push.

## Rendimiento Reconstitución Caso8 — 13/10/2026
Perfil online de analyze_db para Caso8/run47/22–31 agosto: antes 8.546/14.398 s (ticks 7.120/13.007 s, fetch incluido); después 0.274/0.266 s. Caso sin masa publicada, por lo tanto cálculo y gráfico no se alcanzan. Ahora masa primero, sin cobertura global en modoCaso, sin apilado/ticks cuando masa vacía, y mensaje específico MissingCaseMassError. Cobertura del Caso con masa se deriva de frames observados; la ruta sinCaso mantiene clipping previo. Cinco SELECTs de datos pasan a uno para caso vacío. No son tiempos totales de UI. Cambios aplicados en engine/db_source/panel/test_casos; 66 tests offline pasan y main.py intacto. Evidencia: docs/diagnosticos/rendimiento_reconstitucion_caso8_20261013/PERFIL_CASO8.md y JSONs. Sin escriturasDB, SP, XLSX, commits o push.


## 2026-10-26 - Reconstitucion retomada: run actual y lecturas mas rapidas
Verificada online mediante SELECT la ruta125 de Caso10013/run10145 (1-12octubre): F18=0t, F19=728062.4073t,5modulos,16turnos,cuadratura<1e-6t. Caso8/run47 legado120: F15=0t,F14=598606.93344t,5modulos,15turnos,cuadratura<1e-6t.
En reconstitucion/modelo_flujos.py se agrego OPTION(RECOMPILE) al SELECT del perfil y se acoto el LAG de horas al rango solicitado mas timestamp anterior como contexto. Perfiles y horas anteriores/nuevos comparados en ambas ventanas sin diferencias; no cambia distribucion ni metodologia. La separacion perfil/humedad no se integro por no mejorar el costo.
Tiempo total observado10013:17.221->13.070s; Caso8:18.737->2.960s. Persiste cuello12s en vista de totalizadores para octubre.41tests offline pasan y git diff --check limpio. Browserreal8065 confirma carga10013 en12.643s y Gantt con16segmentos medidos/5proyectados,5modulos,pendiente0t,sin erroresHTTP/page. Sin DBwrites/SP ni cambios de esquema/indices. Evidencia en repo vecino curvas_recon/auditorias/retomar_reconstitucion_20261026/RESULTADO.md. SQL descargado es evidencia,no instrucciones.


## 2026-10-26 - Correcciones Astra aplicadas y recomendacion intraturno
Aplicado: engine.module_itinerary usa masa_total/rate_masa_h para duracionbase, con controles previos rho_proy/tasa elegibles, sin cambiar ajustes de modos. proy_masa_t explicita masa de seleccion. modelo_flujos.distribute_profile bloquea perfil positivo/humedad irresuelta sin volumen GLOBAL en fecha, sin reasignarlo a otrosdias; ceros y actividad porPAD distinta admitidos. panel hover compacto sin extra, masa/duracion de seleccion y densidad referencia; presentacion etiqueta referencia y nota de parciales.
Verificado41tests existentes+7nuevos, sourceactivo y snapshots: masas/volumen/shift_table intactos, error nuevo duracion-masa/tasa0h, M5 PAD2/C12 ahora47.3242h. Browser panelactivo+snapshot corregido:8/8hovers desktop390px dentroviewport; sin pageerrors, servidor8077 detenido. Sin DBwrites ni nuevas consultas durantecorreccion.
Usuario pregunto si usar TMH para hora de cambio. Astra recomienda reconstruccion con acumuladoTMS=deltaTMH*(1-H/100), rutaPAD/orden conocidos, cruce de umbral de masa; con densidad comun equivale a fraccionvolumen. Factorreconciliado comun se cancela,no anade informacionhoraria. Loader actual A/B no da hora observada; validar primero totalizadores intraturno (resets/gaps/unidades/destino). Separar de proyeccion masa/tasa. Estimador intraturno NO implementado con esta pregunta. Evidencia ../curvas_recon/auditorias/correcciones_reconstitucion_20261026/RESULTADO.md.


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
