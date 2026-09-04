# Resolucion de import

## Prueba separada y segura

Interprete usado:

`C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\venv\Scripts\python.exe`

Working directory:

`C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR`

Solo se importo `reclamo.db` y se uso introspeccion; no se llamo ninguna funcion ni se abrio conexion de base de datos.

## Resultado

- `mod.__name__`: `reclamo.db`
- `mod.__file__`: `C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\reclamo\db.py`
- SHA256: `47B80A9C162C48B982372CF63A9550D3877760834ECF4450665A28DEEE00E657`

Archivo esperado y archivo resuelto por el venv local: **[IGUALES]**.

No hay shadowing en la prueba local. Esta prueba no identifica el archivo cargado en el servidor remoto/no presente.

## Paquete e import

- Paquete: `reclamo`
- Modulo UI: `reclamo.panel`
- Import en `panel.py`: `from . import db`
- Nombre completo importable: `reclamo.db`
