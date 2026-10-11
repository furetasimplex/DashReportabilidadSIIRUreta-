# Conclusion

CAUSA PRINCIPAL:

El Dash que produjo las ejecuciones SQL posteriores a la corrida 447 no estaba ejecutando la implementacion actual auditada de `reclamo.db.recalcular`; la evidencia es compatible con un artefacto o codigo cargado anterior al commit `bd5568f` del 2026-08-05 18:34 -04. En particular, `a9fd8da` ejecuta sync + CV25 + calculo, pero no auto_mantener. El mecanismo de produccion declarado (Gunicorn sin reload) conserva el codigo importado hasta reemplazo/reinicio.

EVIDENCIA:

1. El `reclamo/db.py` actual ejecuta `conn.execute(sql_mantener)` antes de sync y calculo dentro de la misma transaccion. No es compatible que esta version complete los pasos posteriores sin haber invocado primero auto_mantener.
2. Git demuestra que `sp_auto_mantener_secuencia` fue agregado a `recalcular` en `bd5568f`; la version inmediatamente anterior `a9fd8da` contiene precisamente sync + cargar_cv25 + calcular sin auto_mantener.
3. El venv local resuelve `reclamo.db` al archivo esperado, con SHA256 `47B80...E657`; no hay duplicados ni shadowing dentro del checkout.
4. Produccion se declara como `gunicorn -w 2 ... wsgi:application`, sin `--reload`; cambios en disco no actualizan workers ya iniciados.
5. No hay proceso Dash ni logs Python locales, por lo que la ruta absoluta, hash, fecha de inicio y `sys.modules` del servidor que genero la traza no pudieron observarse.

ESTADO:

**[MUY PROBABLE]** para desfase/version antigua del runtime de Recalcular.

**[NO DETERMINADO]** para la razon especifica por la que la pulsacion de Actualizar modulos no alcanzo `mantener_secuencia`.

ARCHIVO QUE ESTA EJECUTANDO PYTHON:

**NO DETERMINADO EN PROCESO VIVO.** La huella funcional de Recalcular coincide con una revision historica de `reclamo/db.py` anterior a `bd5568f` (posiblemente `a9fd8da`), pero una huella SQL no demuestra una ruta absoluta.

ARCHIVO QUE CREIAMOS ACTIVO:

`C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\reclamo\db.py`

¿SON EL MISMO?

**NO DETERMINADO para el servidor vivo. SI en la prueba aislada con el venv local.**

¿RECALCULAR REAL LLAMA sp_auto_mantener_secuencia?

**NO**, segun la traza SQL suministrada para las pulsaciones posteriores a la ejecucion 447. El codigo actual local sí lo llama.

¿BOTON ACTUALIZAR MODULOS REAL LLAMA mantener_secuencia?

**NO DETERMINADO.** El callback actual e historico del repositorio sí la llama; la ausencia de log demuestra que la pulsacion observada no completo el camino esperado, no cual fue el punto de desvio.

¿EXISTE CODIGO DUPLICADO?

**NO dentro del repositorio auditado.** No determinado fuera de esta raiz o dentro del artefacto remoto.

¿EL PROCESO REQUIERE REINICIO PARA TOMAR LOS CAMBIOS?

**SI** bajo el despliegue Gunicorn/Docker declarado, porque no usa reload. No se reinicio nada.

## Respuesta a la pregunta central

Al presionar Recalcular no aparece auto_mantener porque el servidor que produjo la traza no ejecutaba la revision actual: su secuencia coincide con el `recalcular` historico anterior a `bd5568f`. La falta de auto_mantener tras Actualizar modulos confirma que ese segundo click tampoco recorrio el callback que existe en el repositorio, pero sin proceso/log Python del host vivo no puede distinguirse de forma responsable entre artefacto alternativo, callback no registrado, fallo previo a la ejecucion SQL o solicitud que no llego al worker.
