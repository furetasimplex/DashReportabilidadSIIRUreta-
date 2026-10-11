La apertura se normaliza exclusivamente en el paquete OOXML generado mediante
`_balance_set_initial_view`, al final del ensamblado en memoria del exportador.

| Atributo | Antes | Después |
| --- | --- | --- |
| workbookView activeTab | 8 | 0 |
| workbookView firstSheet | 3 | 0 |
| Resumen sheetView tabSelected | Ausente | 1 |
| Proceso Área Cátodos tabSelected | 1 | Ausente |
| Otras hojas tabSelected | Ausente | Ausente |
| Resumen topLeftCell | A13 | A1 |
| Resumen zoomScale | 85 | 85 |

Solo se parchean los atributos de apertura de workbookView y sheetView.
Se conservan los demás atributos, tamaño de ventana, zoom, selecciones internas,
valores, estilos, merges y contenido DrawingML. No se modifica el template maestro.
El hash contractual continúa siendo:

`C8F5AE2730EAE6827E083031D7A907432B385D9BFFA941E472F44A5D01EEBF8D`

Validaciones:

- 42 pruebas aprobadas con
  `python -m unittest report_export.tests.test_balance_official_mtd report_export.tests.test_balance_template_migration.TemplateMigrationTests -q`.
- La nueva prueba inspecciona el ZIP generado y verifica activeTab=0,
  firstSheet=0, topLeftCell=A1 y selección exclusiva de Resumen. También compara
  el resto de los atributos y los elementos internos de las vistas.
- Se mantienen 66 partes OOXML, CRC válido, XML y relaciones parseables, cero
  duplicados, 2.774 fórmulas, 1.080 fórmulas protegidas y los tres #REF! autorizados.
- Regresiones de DrawingML y fórmulas aprobadas.
- Caso 24 / Run oficial 147 regenerado mediante los SELECT existentes, conservando
  filename, período 01–23/08/2026 y L3/L4 = 23.
- Comparación semántica de valores y fórmulas contra la copia previa; esta había
  sido reserializada por Excel, por lo que no se presume igualdad binaria de
  sus partes. Evidencia: `balance_opening_numeric_comparison.json`.
- Excel Desktop 16.0 abrió en modo normal (CorruptLoad=0), con hoja activa
  Resumen, ScrollRow=1, ScrollColumn=1, una hoja seleccionada y zoom=85.
  Se cerró sin guardar y se comprobó que el hash del exportable no cambió.
  Evidencia: `balance_opening_excel_desktop.json`.

Archivos de código cambiados en este ajuste:

- `report_export/export_to_excel.py`: normalización final de vistas en la copia.
- `report_export/tests/test_balance_template_migration.py`: regresión OOXML de apertura.
- `scripts/verify_balance_excel_desktop.py`: comprobación de hoja activa,
  desplazamiento, selección única y registro de zoom al abrir.

No se modificó el template maestro.

No se modificó ningún objeto ni registro de base de datos.
