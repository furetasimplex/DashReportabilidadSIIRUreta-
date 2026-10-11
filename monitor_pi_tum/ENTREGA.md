# Monitoreo PI / TUM — DEV

## Implementación

Ruta verificada: `main.py` → `layout.py` → `tabs/tab_report.py` →
`report_export/layouts/reportabilidad_page.py`. La cuarta área se monta directamente
en `layout.py`, mediante `monitor_pi_tum.panel.layout()`.

- `__init__.py`: paquete independiente.
- `db.py`: contrato parametrizado del SP existente, fecha final inclusiva convertida
  a medianoche del día siguiente. Verifica la base DEV configurada y la del engine
  antes de conectar. No selecciona tablas o columnas por correa.
- `panel.py`: filtros propios, Scattergl sin correcciones, indicadores, metadata SQL,
  estados vacío/error/NULL/cargando y placeholder de gestión. Consulta al pulsar
  Actualizar; no dispara consultas al cargar las otras áreas.
- `test_monitor.py`: pruebas aisladas sin SQL.
- Único archivo existente modificado por esta tarea: `layout.py` (importación,
  enlace, contenedor y extensión de navegación).

Flujo: Reportabilidad (inicial) → Administración de Reclamo → Carga PowerBI
Camiones → Monitoreo PI / TUM. En esta última: Diagnóstico de Correas → elegir
fechas y correa → Actualizar. Gestión PI / TUM muestra únicamente el anuncio de
próxima etapa.

## Validación realizada el 15-09-2026

- `python -m py_compile layout.py monitor_pi_tum/__init__.py monitor_pi_tum/db.py monitor_pi_tum/panel.py`: correcto.
- `python -m unittest monitor_pi_tum.test_monitor -v`: cuatro pruebas correctas.
  Incluyen todos los IDs del layout activo sin duplicados, navegación de las cuatro
  áreas, selección inicial, límite exclusivo del 14-09 para el día 13-09,
  bloqueo de PROD antes de conectar, valores planos, NULL, retrocesos y variación
  negativa sin corrección, rango vacío y error sin detalle técnico en pantalla.
- Las dependencias SQL se sustituyen en la prueba del layout. No se invocan
  callbacks de negocio existentes. No se importa `main.py`: su chequeo de arranque
  puede inspeccionar el peer PROD incluso desde DEV.
- Consulta real de solo lectura en `inventar_SpcHidr`, usando el SP solicitado,
  para 13-09-2026 a 13-09-2026:

| Correa | Filas | Fuente | Resolución | Tipo | Diferencias planas |
|---|---:|---|---:|---|---:|
| CV008 | 8640 | tot_TM | 10 segundos | TOTALIZADOR | 2398 |
| CV001 | 24 | datos_filtrados | 3600 segundos | TOTALIZADOR | 2 |

Los intervalos reales fueron uniformes (8639 de 10 segundos y 23 de 3600 segundos).
Ninguna de esas dos series presentó retrocesos ese día; estos se verificaron con
datos sintéticos en la prueba del callback, incluyendo variación de -102.
La revisión visual en navegador queda pendiente: no hay herramienta de navegador
disponible en esta sesión. Las pruebas de navegación son del callback y del árbol
de componentes, no una prueba de interacción visual.

## Diferencia con el contrato esperado / bloqueo CV025

La definición vigente de `inventar_SpcHidr.sp_monitor_totalizador_tendencia_test`
en DEV **no incluye CV025**. Admite CV008/CV108 y el conjunto
CV001/CV002/CV003/CV006/CV201/CV202; las demás entradas terminan en THROW 50002,
«Correa no soportada por el monitor de totalizadores».

Se conserva CV025 en el selector requerido; su consulta muestra el estado de error
amigable y registra el detalle técnico. No se agregó una consulta alternativa ni
se modificó el SP. Para habilitarla, una etapa SQL separada deberá incorporar
`datos_filtrados.cv025tot`, nunca `cv025_tot`. La definición actual sí usa
`datos_filtrados.cv001_tot` para CV001.

## Inspección para fase 2 (sin implementar)

### Identidad y auditoría

- `auth.py:login()` autentica contra `LOGIN_DATABASE`, verifica usuario activo y
  contraseña, y guarda el nombre en `session['user']`. `main.py:protect_dash()`
  exige esa clave. Logout elimina `user`.
- El flujo de login revisado no escribe `username`, identificador numérico ni rol.
  Esto describe las escrituras del código; no se inspeccionó una sesión personal.
- Diferencia vigente: `layout.py:update_username()` consulta `username` con
  fallback Invitado. `powerbi_camiones/panel.py:_usuario_actual()` consulta también
  `username` con fallback desconocido. No se modificaron esas funciones.
- PowerBI tiene un patrón transaccional en `db.py`, con `usuario_carga`,
  `archivo_origen` y `fecha_carga = SYSDATETIME()` tanto al insertar como al actualizar.
- Reclamo consulta `usuario_solicita`, `fecha_solicitud`, `usuario_aprueba`,
  `fecha_aprobacion` y `observacion`.
- El callback activo de reportabilidad consulta el historial `rep_prod_ajuste_log`;
  en su operación de ajuste todavía pasa `usuario='lcortes'` con TODO de sesión.
  Por ello no es una referencia fiable para capturar al usuario autenticado.

Para la futura gestión, conservar la separación panel/db de este paquete: recuperar
`session['user']` en el servidor dentro del callback autenticado y pasarlo a una
operación transaccional parametrizada en `monitor_pi_tum/db.py`. Guardar fecha
operacional, turno, estado, comentario, usuario y fecha de registro SQL, con clave
de equipo para distinguir correas. No aceptar la identidad desde controles del
navegador. No se propone nombre definitivo ni se crea tabla.

### Punto de integración SQL

Se confirmó por lectura de la definición DEV que existe
`inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno`. Su clave es
`fecha_operacional + turno + equipo_codigo`. Usa fronteras PI y diagnóstico,
y decide actualmente PI/TUM/SIN_RESOLVER con reglas técnicas y disponibilidad TUM.

La futura declaración operacional debería incorporarse antes de decidir
`fuente_resuelta` en ese resolvedor, por esa clave, preservando la diferencia entre
diagnóstico y valores productivos. El consumidor activo
`report_export/report_export.py:fetch_fecha_corte_apilado_tmh_report()` consulta
`v_contingencia_totalizador_diagnostico_turno` y reproduce condiciones de elegibilidad
para determinar el corte: también requerirá revisión de coherencia en fase 2.
No se modifica ahora ni se conecta la declaración a este gráfico acumulado.

Regla futura pendiente de implementación:

- OPERATIVO: PI elegible/prioritario.
- MANTENCION: PI elegible/prioritario.
- CAIDA_PI: PI no elegible; usar TUM válido si existe (incluido cero).
- CAIDA_PI sin TUM válido: PENDIENTE_TUM, `fuente_resuelta = NULL`, sin retorno
  silencioso a PI.
- El especialista declara el estado operacional; no selecciona arbitrariamente
  «usar PI / usar TUM».

## Alcance

No se accedió a PROD ni se modificaron objetos SQL, lógica oficial, persistencia
o archivos preexistentes ajenos al cambio. La conexión inicial dentro del sandbox
falló por ODBC/SSL; las lecturas DEV funcionaron con ejecución autorizada fuera
del sandbox. Se conservaron los cambios preexistentes del workspace.
