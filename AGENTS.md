# Continuidad de trabajo — DashReportabilidadSIIR

## Auditorías y evidencias locales

Guardar todas las auditorías, diagnósticos, capturas y exportaciones de validación
en `auditorias/`; esta carpeta está excluida de Git. No crear nuevas carpetas de
auditoría en la raíz ni dentro de los módulos. El archivo histórico conserva las
rutas anteriores bajo `auditorias/archivo/`. Las referencias pequeñas necesarias
para las pruebas sin SQL se versionan en `test_fixtures/`.

Este repositorio es la base activa de trabajo indicada por el usuario.
Leer `NOTAS_CONTINUIDAD.md` e `INTEGRACION_CURVAS.md` antes de continuar la
integración de curvas. Trabajar sobre los archivos de este repositorio;
la copia `../curvas_recon/integracion_siir` es un antecedente, no la fuente activa.

## Arquitectura y estilo

- `main.py` crea la única aplicación Dash y conserva autenticación Flask.
- `layout.py` define menú, encabezado, breadcrumb y navegación.
- `tabs/tab_curvas.py` integra `curvas_recon.pad_dashboard`.
- `build_layout()` no consulta SQL; `register_callbacks(app)` se llama al inicio.
- Usar `assets/theme.css`: naranja `#E86D1F`, fondo `#F5F6FA`, blanco e Inter.
  Encapsular estilos de curvas en `.curvas-recon-shell` y mantener IDs `curvas-*`.
- Conservar Reportabilidad y la configuración de conexión SIIR existente.
  No imprimir credenciales, cadenas de conexión ni contenido de `.env`.

## Cálculo y pruebas

- La rampa empieza en el primer riego real de campaña y cruza las semanas de
  reconciliación durante sus 30 días. No reiniciarla al comienzo de cada caso.
- Repetir una ventana conserva el empalme; cambiar un cierre anterior invalida
  sus sucesores. Los residuos solo se redistribuyen entre pilas en régimen,
  con límites diarios. El historial sigue en memoria del proceso.
- Las pruebas locales no necesitan SQL. `Ejecutar cálculo` y `Actualizar datos`
  sí guardan o sincronizan datos reales: distinguirlas de la carga de pantalla.
- Preservar cambios del usuario; `.serena/project.yml` ya estaba modificado
  antes de esta integración. El pull se integró con el merge local b691766;
  no se hizo push. Las modificaciones de integración siguen sin commit.


## Apertura de reconciliación

- `initialize_data()` carga solo Casos oficiales para el formulario inicial.
- `ensure_full_data()` prepara el histórico y los metadatos una vez por worker,
  antes del cálculo y de renderizar resultados que los necesitan.
- No consultar `data_freshness()` al montaje: contiene 12 SELECT secuenciales.
  El estado se consulta con Actualizar datos, manteniendo su flujo de sync.
- No eliminar la validación de arranque SQL agregada por upstream en main.py;
  las pruebas sin SQL la sustituyen únicamente dentro del fixture.


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

## Flujo DB + Dash + metodologia metalurgica — 2026-10-26

Aplicar el protocolo operativo de [docs/FLUJO_DB_DASH_METALURGIA.md](docs/FLUJO_DB_DASH_METALURGIA.md): contrato breve, responsable por archivo, revision del diff contra fuente activa, snapshot identificado y reutilizable, lecturas agrupadas por PAD/rango y pruebas proporcionales al riesgo. La verificacion visual va al final, con fuente y pruebas estables. Resumir evidencia y primera discrepancia; evitar volcados grandes y consultas repetidas. Un agente debe entregar trabajo verificado, no solo un plan, y el principal debe revisar su entrega.

La tabla de seleccion flexible de modelos del protocolo es una recomendacion; se conservan las preferencias explicitas del usuario y las excepciones que autorice. No cambia configuracion global ni autoriza escrituras SQL, ejecucion de SP o pulsar Calcular durante QA de lectura.


## Sulfuros: ensayo neto local — 03/11/2026

Las reglas historicas de reparto hacia maduras y cola de rampa corresponden al
selector Metodo anterior. La nueva rama aplica el contrato de
[docs/METODO_SULFUROS_MENORES_30.md](docs/METODO_SULFUROS_MENORES_30.md):
recuperacion directa observada en mayores de30, menores ajustables, historia
protegida, fuente congelada10009 y ninguna persistencia SQL legacy del ensayo.
No reconstruir el drenaje desconocido de maduras ni presentar el cierre neto
como validacion hidraulica. Usar las pruebas offline antes de ampliar fuentes.

## Reportes de reconciliación — 2026-11-05

`tabs/tab_reportes_recon.py` es una sección aparte, solo de generación de
reportes, que une el reporte de curvas reconciliadas
(`pad_dashboard.generate_case_report`) y los informes de módulos de
reconstitución (`reconstitucion.panel.generar_informe_modulos`). Por defecto
usa la última corrida del Caso guardada en el servidor y no escribe en SQL;
«Reconciliar ahora» ejecuta `compute_recon`, que sí guarda la corrida. Varios
informes se descargan en un ZIP con `LEEME.txt`. IDs `reportes-recon-*`.
