# Entrypoint

## Desarrollo local

- Archivo: `main.py`
- Guardia: `if __name__ == "__main__"`
- Comando implicito: Python ejecutando `main.py`
- Inicio: `app.run(debug=True, port=PORT|8065)`
- En esta modalidad Dash/Flask usa debug y el reloader queda habilitado por defecto salvo override externo.

## Produccion declarada por el repositorio

- `Dockerfile`: `WORKDIR /app`
- Entrypoint WSGI: `wsgi.py`, objeto `application = server`
- Comando exacto declarado: `gunicorn -w 2 -b 0.0.0.0:${PORT:-10000} wsgi:application`
- Python: `/usr/local/bin/python` de la imagen `python:3.13-slim` (deducido del Dockerfile; no comprobado en host vivo)
- Virtualenv: ninguno declarado dentro de la imagen; dependencias instaladas globalmente con pip.
- Reload: Gunicorn no recibe `--reload`; los workers conservan el codigo importado hasta que el contenedor/proceso se recrea o reinicia.

## Proceso real observado

No hay proceso Dash local. El comando y working directory del servidor que genero los eventos SQL no pueden confirmarse desde este host.

## Cadena de registro de callbacks

```text
Dockerfile
  -> gunicorn ... wsgi:application
  -> wsgi.py
  -> from main import server
  -> main.py
  -> from layout import create_layout, register_callbacks
  -> layout.py
  -> from reclamo import panel as reclamo_panel
  -> reclamo.panel (decoradores globales @callback)
  -> from . import db
  -> reclamo.db
```

## Respuesta sobre reload

En la configuracion de produccion documentada, un cambio en `reclamo/db.py` **requiere reemplazo/reinicio del proceso o contenedor** para ser cargado. No hay autoreload. En desarrollo con `main.py`, normalmente se recarga automaticamente por `debug=True`.
