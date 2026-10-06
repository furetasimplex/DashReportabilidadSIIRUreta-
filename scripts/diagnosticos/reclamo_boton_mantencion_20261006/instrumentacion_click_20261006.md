# Instrumentación del helper y comprobaciones del runtime (2026-10-06)

## Cambios temporales en código

`reclamo/panel.py::cb_automatizacion` emite `DEBUG_RECLAMO_CLICK` al entrar.

`reclamo/db.py::mantener_secuencia` emite:

- `DEBUG_RECLAMO_MANTENER` al entrar al helper.
- `DEBUG_RECLAMO_DB` con `@@SERVERNAME`, `DB_NAME()` y `SUSER_SNAME()` en la misma conexión SQLAlchemy (no contraseña).
- `DEBUG_RECLAMO_BEFORE_EXEC` inmediatamente antes del EXEC.
- `DEBUG_RECLAMO_AFTER_EXEC` con `returns_rows` y `keys`.
- `DEBUG_RECLAMO_AFTER_FETCH` con número de filas y keys.
- `DEBUG_RECLAMO_AFTER_COMMIT` solo si termina el context manager de transacción.
- `DEBUG_RECLAMO_EXCEPTION` con `log.exception`, fase y traceback completo, re-lanzando la excepción original.

El SP y las reglas de negocio no se modificaron. La consulta adicional de identidad es read-only y usa la misma conexión/engine que el EXEC.

## Identidad del engine configurado por el checkout

La consulta read-only devolvió:

```text
server_name=VPS-5347319-X
database_name=inventar_SpcHidr
login_name=sa
```

La configuración no secreta del checkout indica `SQLSERVER_NAME=DEV_SIIR` y `LOGIN_DATABASE=DEV_SIIR.dbo.auth_user`; además el `.env` apunta a `inventar_SpcHidr`. No se imprimieron credenciales. Este resultado identifica el engine local, no necesariamente la conexión del browser ni del servidor que atendió el click reportado.

## Instancia local observada

- PID 26004 ejecuta `python.exe main.py`, inició 2026-10-06 09:53:47 y es dueño de `127.0.0.1:8065`.
- PID 51316 ejecuta `python.exe main.py`, es hijo de 26004 e inició 10:31:18. No tenía listener Dash propio.
- GET read-only de `http://127.0.0.1:8065/_dash-dependencies` devolvió el HTML del formulario de login **Capacitaciones Simplex**, no una respuesta Dash de Control de Reclamo. Por lo tanto ese listener no es la instancia correcta de esta tarea y no fue reiniciado ni detenido.
- CUA reportó `apps: []`, `browsers: []`; no hay navegador/ventana DEV controlable en esta sesión.

## Ejecución del click y correlación SQL

No se reinició ni pulsó ningún botón: la única instancia local identificable sirve otra aplicación, y no hay ventana del dashboard correcta. No hay líneas `DEBUG_RECLAMO_*` de ejecución ni se hizo una consulta de correlación de `reclamo.log_ejecucion` posterior al click. No se ejecutó el SP desde el checkout.

## Determinación

- DB distinta: el engine de este checkout sí alcanza el destino DEV esperado; no se puede comparar con la conexión del browser/runtime ausente.
- Error de ejecución/resultset: no determinado; sin click no se generó `AFTER_EXEC`/`AFTER_FETCH` ni traceback de runtime.
- Rollback: no determinado; sin transacción ejecutada no hay `AFTER_COMMIT` ni log de excepción.

La evidencia sí indica una discrepancia de instancia local: el puerto 8065 sirve otra aplicación. Hace falta abrir/identificar el DEV de Control de Reclamo correcto para completar el único click instrumentado.
