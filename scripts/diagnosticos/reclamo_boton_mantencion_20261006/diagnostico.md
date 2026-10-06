# Diagnóstico

## Evidencia local

`reclamo/panel.py` contiene los componentes `btn-automatizacion`, `resultado-automatizacion`, `btn-recalcular` y `mensaje-accion`. El callback verde recibe `Input('btn-automatizacion','n_clicks')`, dos outputs (el segundo permite duplicado), `prevent_initial_call=True` y llama `db.mantener_secuencia()`. El callback de recálculo recibe rango/fecha y llama `db.recalcular(desde,hasta)`.

`reclamo/db.py` tiene una sola definición local de `mantener_secuencia`: ejecuta `EXEC reclamo.sp_auto_mantener_secuencia @VentanaDias=:ventana, @Siguientes=:siguientes`. El recálculo actual ejecuta dos ciclos mantener -> sincronizar, luego CV25 y cálculo, todo dentro de una transacción SQLAlchemy. Con este código cargado y una transacción completada, la explicación de sincronizaciones completadas sin llamada previa a mantener requiere otra causa observable (rollback/log de SP no confirmado, proceso/versión diferente, u origen de ejecuciones distinto); no se puede escoger sin telemetría.

## Contradicción histórica

El historial local muestra que `a9fd8da` tenía sync -> CV25 -> cálculo sin mantener y `bd5568f` agrega el paso de mantener. Esto hace plausible un runtime anterior para parte de la traza de recálculo, pero no identifica el proceso ni explica por sí solo el clic verde. El artefacto previo de runtime llegó a la misma hipótesis y explícitamente dejó sin determinar el servidor vivo; sus datos de procesos son del 2026-09-03.

## Clasificación

Clasificación provisional: **L. MULTICAUSAL (hipótesis; no confirmada)**. La clasificación demostrable para el motivo del clic verde es **M. NO_DETERMINADO**. No hay evidencia para declarar A, B, C, D, E o F. La anomalía del recálculo es compatible con runtime desactualizado, pero sin correlación de logs/proceso tampoco es concluyente.

## Bloqueos probatorios

- `callback_map` de la instancia real, archivo/hash cargado y cwd: no accesibles; el import de `main` local activó la guardia de conexión y falló.
- DB servidor/base/login del engine real: no consultados porque falló el handshake TLS desde este entorno.
- Procesos, puertos y hora de inicio: CIM y listeners denegados; los dos procesos python observados carecen de información suficiente.
- Logs Python/Dash/Flask y petición del navegador: no disponibles.
- Definiciones SQL guardadas son extracción previa, no hash/definición live del día.
- La elegibilidad y datos actuales de 78/79, topografía sincronizada y clasificación del gráfico: no validados.

No se ejecutó DML, SP, publicación, recálculo ni botón. Sin diagnóstico inequívoco no procede fix/reinicio.

## Seguimiento de clic (nueva evidencia)

La inspección reproducible `inspect_callback_registration.py` importa `main`, confirma `reclamo.panel` en `sys.modules`, ejecuta `app._setup_server()` y encuentra 94 callbacks. Hay exactamente un match para `btn-automatizacion.n_clicks`: función `cb_automatizacion` del módulo `reclamo.panel`, archivo `reclamo/panel.py`, outputs `resultado-automatizacion.children` y `mensaje-accion.children`. La raíz del layout contiene el botón; no hay IDs duplicados en ese layout. `suppress_callback_exceptions=True` está activo. No se observaron imports condicionales del panel en `layout.py`; se importa al nivel superior.

Por tanto el caso **B. CALLBACK_NO_REGISTRADO** queda descartado para este checkout local después de setup. El proceso navegador/runtime del clic no se pudo observar. No se inició servidor ni se pulsó el botón: el helper ejecutaría el SP y la instrucción expresa prohíbe ejecutarlo. Por eso el caso A/B/C/D en el runtime que recibió el clic sigue sin clasificación. La falta de contenido UI por sí sola no localiza el punto de corte.

No se encontró un segundo panel activo de Reclamo ni un duplicado del ID en el layout raíz. Existe una salida `mensaje-accion.children` compartida con otros callbacks, pero el output del botón verde usa `allow_duplicate=True`; el callback correspondiente sí aparece en el mapa. La app instala callbacks globales de Dash al hacer `_setup_server()`, no inmediatamente tras `import main`.
