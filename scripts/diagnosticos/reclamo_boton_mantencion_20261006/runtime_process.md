# Proceso y runtime

Fecha de inspección: 2026-10-06 (local).

- `Get-Process python,pythonw` mostró PID 26004 y 58712, Python 3.13, inicio 09:53:47 y 09:54:06. `Get-CimInstance Win32_Process` y `Get-NetTCPConnection` devolvieron Acceso denegado; no se conocen línea de comando, cwd ni puertos. No se puede afirmar que sean servidores Dash.
- El artefacto archivado `auditoria_runtime_reclamo/05_procesos_python.txt` refiere a una inspección de 2026-09-03, por tanto no demuestra el estado de hoy.
- Código local: `main.py` configura `suppress_callback_exceptions=True`, puerto por `PORT` (default 8065), debug True si se ejecuta directamente. `wsgi.py` importa `main.server`; Docker declara Gunicorn en puerto 10000 y sin reload.
- La importación de `main` activa `run_startup_db_check`; no fue posible completar la inicialización: ODBC 17 informó que el cliente no admite el cifrado requerido / error de credenciales SChannel.
- No se adjuntó debugger ni se reinició o detuvo proceso alguno.
