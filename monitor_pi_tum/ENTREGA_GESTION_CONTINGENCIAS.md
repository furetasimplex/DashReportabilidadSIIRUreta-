# Gestión de contingencias PI / TUM v1 — DEV

La implementación encontrada ya sustituía el placeholder mediante `gestion.layout()`
en `panel.py`. Se completó esa misma pantalla, conservando la navegación, los IDs
existentes y la lógica de Diagnóstico de Correas. Este documento describe el modelo
actual de acciones; `ENTREGA_FASE2.md` es evidencia histórica de una metodología anterior.

## Archivos modificados en esta revisión

- `db.py`: agrega `obtener_estado_actual()`. `_estado()` permite consultar la última
  acción cronológica de SQL sin restringirse al período del preview.
- `gestion.py`: separa estado vigente y estado del período seleccionado; muestra
  el preview y la advertencia de TUM faltante dentro de la confirmación; presenta
  errores de validación dentro del modal. Se extendieron los callbacks existentes
  `cargar` y `gestionar`, sin registrar callbacks paralelos.
- `test_gestion.py`: agrega regresiones de estado vigente frente a histórico,
  confirmación con TUM ausente, validación visible, orden SQL, IDs y botón en proceso.

## Comportamiento integrado

La gestión se limita a PRINCIPAL_CV008 y PRINCIPAL_CV108. PI es la fuente normal;
las decisiones y los valores resueltos se leen del resolver SQL. La aplicación
no reconstruye su lógica. El preview hipotético muestra el TUM informado y
advierte PENDIENTE_TUM sin impedir activar ni convertir NULL en cero.

Las acciones son ACTIVAR_CONTINGENCIA y CERRAR_CONTINGENCIA. Los cinco motivos
son CAIDA_PI, MANTENCION, COMUNICACIONES, SERVIDOR y OTRO; el cierre envía NULL.
La identidad proviene exclusivamente de `session['user']`. La confirmación
conserva fecha, turno, usuario y acción vigente esperada en la sesión firmada.
Sin usuario o con una transición concurrente, la escritura se rechaza.

`registrar_contingencia()` valida el corte 2026-09-01 y abre una transacción
mediante el engine central de `db_connection.py`. `_registrar_y_reprocesar()`
serializa acciones mediante `sp_getapplock`, registra por SP y llama a
`reprocesar_apilado()` dentro de la misma transacción. Una excepción provoca rollback.
El botón Confirmar se deshabilita durante la operación; una repetición encuentra
una acción vigente diferente y no vuelve a insertar la misma transición.

Activar reprocesa desde la fecha de activación; cerrar desde el inicio de la
contingencia vigente en el turno de cierre. El final proviene de MAX(fecha_operacional)
del resolver para los dos equipos, limitado a la fecha actual de SQL Server.
La definición SQL local inspeccionada calcula la ventana como el mayor entre
FechaInicio y FechaFin menos DiasReproceso-1. Por eso se envía
DATEDIFF(day, inicio, fin)+1 para abarcar todo el intervalo.

Tras guardar se refrescan estado vigente, estado seleccionado, ambos equipos,
historial y apilado. La bitácora es de solo lectura, ordenada por fecha_registro
DESC, id DESC. Los errores técnicos van al log y no al mensaje del usuario.

## Contratos SQL utilizados

Todos en esquema `inventar_SpcHidr`, base DEV del mismo nombre:

- `contingencia_pi_accion_test`: estado cronológico e historial.
- `v_contingencia_totalizador_resuelto_operacional_test`: preview y límite materializable.
- `Control_Apilado_TMH_v2_test`: lectura del resultado materializado.
- `sp_registrar_contingencia_pi_test`: única escritura de acciones.
- `sp_mantiene_apilado_tmh_v2_test`: única materialización de apilado.
- `sys.sp_getapplock`: exclusión entre acciones de esta aplicación.

No se modificaron objetos SQL, consumidores adicionales, ni historia anterior
al corte. No se accedió a PROD ni se ejecutaron acciones operacionales reales.

## Verificación y límites

Comando: `python -m unittest monitor_pi_tum.test_monitor monitor_pi_tum.test_gestion monitor_pi_tum.test_cambio_horario -v`.

Resultado: 20 pruebas correctas; una prueba SQL real omitida porque requiere
`--dev`. Incluyen identidad, PI cero, TUM ausente, cierre, rango de reproceso,
rollback simulado, concurrencia, historial, navegación, diagnóstico, importación
del layout con conexiones sustituidas, HTTP Dash e IDs/outputs sin duplicados.

La inspección directa con `python -m monitor_pi_tum.inspect_acciones_dev` falló:
primero ODBC/SSL dentro del sandbox y luego timeout de conexión fuera de él.
La semántica de los SP se revisó en las definiciones existentes de
`validacion/acciones_actual/`. No se afirma una nueva validación end-to-end real.
Tampoco se realizó inspección visual en navegador.

Supuestos conservados: la última acción por fecha operacional, turno,
fecha_registro e id representa el estado vigente de la bitácora; los botones
actúan sobre el período seleccionado, permitiendo cierres retroactivos. La
fecha y turno se eligen antes de abrir el modal y se muestran allí para confirmar.
El estado vigente independiente evita presentar un período histórico como actual.
