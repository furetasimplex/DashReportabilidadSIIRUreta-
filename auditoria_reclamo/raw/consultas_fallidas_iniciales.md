# Consultas fallidas durante la auditoría

Las dos primeras consultas a las fuentes CV025 usaron erróneamente la columna `fecha`. SQL Server respondió `42S22 / 207: Invalid column name 'fecha'` para:

- `inventar_SpcHidr.vista_resumen_datos_filtrados`
- `inventar_SpcHidr.datos_filtrados`

La inspección de la definición de `sp_cargar_cv25_horas` confirmó que la columna correcta es `fecha_turno`. Ambas consultas se corrigieron, se volvieron a ejecutar solo con `SELECT` y finalizaron correctamente. El archivo `consultas_fallidas.csv` queda vacío porque representa el estado final reproducible; este documento conserva el error inicial exacto y su resolución.

Antes de la extracción se intentó conectar con el entorno configurado ODBC 17 y luego ODBC 18 dentro del sandbox. Ambos intentos fallaron con `pyodbc.OperationalError 08001`, mensaje principal: `No se admite el cifrado en el cliente` / `Proveedor de SSL: No hay credenciales disponibles en el paquete de seguridad`. Al autorizar la conexión de red fuera del sandbox, ODBC 18 conectó correctamente. No se ejecutó SQL durante los intentos fallidos.
