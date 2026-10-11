El ajuste se aplica exclusivamente al paquete OOXML generado en memoria.
Se eligió limpiar las cachés de **todas las celdas con fórmula**, porque las
2.774 fórmulas pertenecen al workbook del Balance y Excel Desktop es el
consumidor contractual. Esto evita depender de un análisis parcial de
dependencias transitivas y no introduce un evaluador de fórmulas en Python.

Por cada exportación se eliminan **2.774 elementos `<v>` cacheados** de celdas
con `<f>`. Quedan **0 cachés de fórmulas** en el archivo entregado y se conservan
las **2.774 fórmulas**, incluidas las **1.080 protegidas de Análisis**. Se
preservan íntegramente los nodos `<f>`, atributos/tipos de celda y estilos.
Los `<v>` de celdas sin fórmula, incluidos datos oficiales, tolerancias,
medidos y L3/L4, no se modifican por esta limpieza.

La configuración anterior de recálculo del workbook intermedio no se propagaba
al paquete final, que se reconstruye desde el template. Ahora se parchea
`xl/workbook.xml` directamente en la copia final:

| Atributo de calcPr | Antes | Después |
| --- | --- | --- |
| calcId | 191029 | 191029 |
| calcMode | Ausente | auto |
| fullCalcOnLoad | Ausente | 1 |
| forceFullCalc | Ausente | 1 |

Las propiedades válidas adicionales de calcPr se conservan.

| Selección interna de Resumen | Antes | Después |
| --- | --- | --- |
| activeCell | A13 | A1 |
| sqref | A1:XFD1048576 | A1 |

Se mantienen activeTab=0, firstSheet=0, topLeftCell=A1, selección exclusiva de
Resumen y zoom 85 %. No se alteran otras propiedades de las vistas.

Se regeneraron los dos casos con las consultas SELECT existentes, sin cambiar
la capa de datos:

| Validación | Caso 21 / Run 149 | Caso 24 / Run 147 |
| --- | ---: | ---: |
| Período y MTD | 01–08/08/2026 | 01–23/08/2026 |
| L3 / L4 | 8 / 8 | 23 / 23 |
| Masa F1 | 253003.6957 | 713463.52787 |
| Fino F1 | 2203.433327 | 4125.435436 |
| Fórmulas | 2.774 | 2.774 |
| Cachés de fórmulas entregadas | 0 | 0 |
| Partes OOXML | 66 | 66 |

Para los 120 flujos se contrastaron D:F y G:I de Datos Reconciliados contra
los resultados oficiales y el acumulado existente, conservando NULL y cero.
También se comprobaron D=G y F=I y las cinco entradas D/E/F/J/N de Análisis.
Todas las celdas y fórmulas del Caso 24 coinciden con su exportable previo a
este fix, comparadas sin usar valores cacheados de fórmulas.

Los ejemplos Resumen!E12, Informe Hidrometalurgia!F15 y Análisis!G4/K4/O4
conservan sus fórmulas y no tienen ningún `<v>` cacheado en el ZIP entregado.
Se mantienen 9 hojas, CRC válido, cero partes ZIP duplicadas, XML y relaciones
parseables, cero referencias duplicadas por fila y exactamente los tres #REF!
autorizados de dataValidation/formula1 en C11. DrawingML, shapes, conectores,
imágenes, merges y estilos permanecen conservados.

Pruebas:

- `python -m unittest report_export.tests.test_balance_official_mtd report_export.tests.test_balance_template_migration.TemplateMigrationTests -q`: **43 pruebas aprobadas**.
- `python -m scripts.validate_balance_recalculation`: Casos 21/149 y 24/147
  generados y contrastados con datos oficiales; template idéntico antes/después.
- `python scripts/verify_balance_excel_desktop.py ... --case 21 --run 149 --days 8`
  y la misma comprobación para Caso 24: apertura normal en Excel Desktop 16.0,
  CorruptLoad=0, solo lectura, sin actualizar vínculos y sin guardar.

En Excel Desktop se verificaron directamente Resumen!E12, Informe!F15 y
Análisis!G4/K4/O4 después de abrir, sin llamar a Calculate ni CalculateFull.
Los valores coinciden con D3/E3/F3 y los días de cada caso. Ambos abren en
Resumen, ScrollRow=1, ScrollColumn=1, ActiveCell=$A$1, Selection=$A$1,
una hoja seleccionada y zoom 85 %. Excel devuelve CalculationState=2
(pendiente), aunque las celdas verificadas ya muestran los resultados
correctos. Se registra este estado; no se lo presenta como xlDone ni se
requiere recálculo manual para obtener los resultados comprobados.
Ambos archivos se cerraron sin guardar y su hash permaneció igual, por lo
que Excel no repobló las cachés en los archivos entregados.

Evidencia:

- `balance_recalculation_cases.json`.
- `balance_recalculation_ooxml.json`.
- `balance_recalculation_excel_case21.json`.
- `balance_recalculation_excel_case24.json`.

Cambios por archivo:

- `report_export/export_to_excel.py`: parcheo final de calcPr, eliminación
  exclusiva de cachés de fórmula y normalización de selección interna A1.
- `report_export/tests/test_balance_template_migration.py`: regresión de
  calcPr, cero cachés, ejemplos críticos y selección; la comparación de
  fórmulas protegidas permite exclusivamente retirar el `<v>`.
- `scripts/validate_balance_recalculation.py`: regresión real de los dos casos,
  basada en lecturas existentes y sin escrituras en BD.
- `scripts/verify_balance_excel_desktop.py`: parametrización del caso y
  comprobación de valores calculados, selección y zoom.
- Exportables de ambos casos y documentación de evidencia.

No se modificó el template maestro.

El hash contractual sigue siendo
`C8F5AE2730EAE6827E083031D7A907432B385D9BFFA941E472F44A5D01EEBF8D`.

No se modificó ningún objeto ni registro de base de datos.

No se modificó ninguna query, vista, SP ni lógica MTD.

Ampliación: fórmulas especiales y calcChain.

La inspección del template confirma 794 nodos `<f t="shared">`, incluidos
26 maestros con `ref`, y 1.980 fórmulas sin atributos especiales. No hay
fórmulas `t="array"` ni marcadores `dynamicArrayProperties`/`XLDAPR` de
matrices dinámicas. Existe `xl/calcChain.xml`, que se conserva sin modificación
ni reconstrucción desde Python. También se conserva `xl/metadata.xml`.

Se compararon los 2.774 nodos `<f>` byte a byte en los exportables de los Casos
21 y 24: ninguno cambió, incluidos texto y atributos `ref`, `si`, `t` y
cualquier atributo adicional. `calcChain.xml` y `metadata.xml` también son
idénticos al template. La limpieza continúa limitada a los `<v>` cacheados.
Se permite que Excel gestione su cadena de cálculo al abrir, manteniendo
calcMode=auto, fullCalcOnLoad=1 y forceFullCalc=1.

La prueba `test_formula_nodes_and_calcchain_preserved_byte_for_byte` compara
cada fórmula cruda asociada a su coordenada, además de calcChain, metadata y
las relaciones del workbook. Resultado de esta ampliación:
`python -m unittest report_export.tests.test_balance_template_migration.TemplateMigrationTests -q`:
**9 pruebas aprobadas**. No fue necesario modificar el exportador ni regenerar
los archivos entregados. Evidencia: `balance_special_formulas_audit.json`.
