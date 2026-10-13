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
