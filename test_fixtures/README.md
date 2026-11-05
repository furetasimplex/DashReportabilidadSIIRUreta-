# Datos mínimos de prueba

Estos archivos pequeños son referencias necesarias para las pruebas automáticas sin SQL.
Se conservan en Git para que las pruebas funcionen en un clon limpio.

Los informes, capturas, exportaciones y auditorías completas están en `/auditorias/`,
que se conserva localmente y se excluye mediante `.gitignore`.

`referencias/firma_reporte_oficial.json` es la firma de formato (hojas, encabezados,
formatos numericos, anchos, paneles y graficos) del reporte oficial
`Reporte_Recuperaciones_12_de_Octubre_2026.xlsx` (21 MB, no versionado). La usa
`curvas_recon/test_reporte_oficial.py` y `tools/compare_report_format.py`; se
regenera con `python tools/compare_report_format.py --extraer <oficial.xlsx> --salida <firma.json>`.
