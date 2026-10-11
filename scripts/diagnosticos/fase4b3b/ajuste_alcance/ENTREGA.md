# Ajuste de alcance 4B3B — Preview/Excel exclusivamente

La rama PDF `prod` quedó **idéntica al texto previo a 4B3B**, extraído de `../reportabilidad_cb.py.antes`. También se verificó que toda la función `generar_pdf` tiene AST idéntico al previo a 4B3B. Su defecto legacy no se arregla y no se habilita PDF DC.

Cambios:

- `report_export/callbacks/reportabilidad_cb.py`: restauración exclusiva de la rama PDF `prod`.
- `report_export/report_export.py`: el paquete DC acepta únicamente `preview` y `excel`; rechaza cualquier otra salida antes de abrir transacción.
- `report_export/tests/test_paquete_datos_conciliados.py`: retiradas únicamente las siete combinaciones nuevas destinadas a validar PDF DC (tres de fuentes/rangos y cuatro de callbacks). La prueba de fecha final ausente ahora usa Excel. Ningún test histórico ni de Representatividad fue eliminado o modificado.

Contrato vigente, sin cambios en este ajuste: Preview y Excel leen DC principal `ini_d → fin_d`; Excel lee MTD adicional desde primer día del mes del inicio cuando corresponde; Factor/Balance hasta corte operacional. Mantenedor DC calendario completo, `dias_reproceso=0`, `refrescar_factor=False`. Todo bajo una conexión/transacción; construcción fuera de SQL.

[Diff del ajuste](ajuste.diff) · [Integridad comprobada](integridad.json) · [Diff integral 4B3B actualizado](../cambio_completo.diff).

## Validación sin SQL

`py_compile` PASS en los tres archivos Python modificados.

```powershell
.\venv\Scripts\python.exe -m pytest report_export/tests/test_paquete_datos_conciliados.py report_export/tests/test_error_modal_exportacion.py report_export/tests/test_datos_conciliados_excel.py report_export/tests/test_paquete_reporte_turno.py report_export/tests/test_orquestacion_reporte_turno.py -q --disable-warnings
```

Resultado: **97 PASS, 0 SKIP, 0 FAIL**, además 25 subtests PASS. [Salida completa](tests.txt). Las 42840 advertencias corresponden a deprecaciones existentes del formateador Excel. Guards SQLAlchemy/ODBC activos; ningún intento de conexión reportado. No se ejecutó suite amplia en este ajuste.

El script manual DEV no se modificó. Su llamada al paquete sigue usando exclusivamente `salida='excel'`, comprobado por AST. No se ejecutó `--execute-rollback` ni se conectó a DEV.

**PROD, SQL, `pdf_generator.py`, Representatividad y F4D2 intactos.** El paquete RTO y sus tests históricos de 4B3A tampoco se modificaron. PDF RTO/DC no se habilita ni se declara validado como artefacto oficial. PDF DC queda fuera del alcance, como deuda legacy.

**4B3B no se declara cerrada.** Esta entrega reemplaza el alcance PDF y los conteos vigentes de la entrega inicial; sus logs anteriores se conservan como historial.
