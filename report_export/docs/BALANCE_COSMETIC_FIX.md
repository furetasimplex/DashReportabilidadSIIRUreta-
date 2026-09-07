El ajuste se aplicó al template contractual maestro, mediante parches OOXML
puntuales. No se agregaron correcciones de texto al runtime del exportador.

SHA-256 final y única constante contractual activa:

`C8F5AE2730EAE6827E083031D7A907432B385D9BFFA941E472F44A5D01EEBF8D`

El template de entrada era la versión ya migrada, con hash
`340B4CFD40B51E8D4E748BD1C2988F5D8BD2BDD68AF5FA13ACE99F513C273302`.
El maestro final permanece en `reporte/Template_Balance_Planta_Hidrometalurgia.xlsx`.

| Ubicación | Antes | Después |
| --- | --- | --- |
| Datos Reconciliados!B2 | Flujos Proceso Hidrometalurgía | Flujos Proceso Hidrometalurgia |
| Datos Reconciliados!C110 | Inventrio Cobre Colgado | Inventario Cobre Colgado |
| Análisis Variación-Tolerancias!C111 | Inventrio Cobre colgado | Inventario Cobre colgado |
| Proceso Área Seca!T4 | Codigo : | Código: |
| Proceso Área Húmeda!Y4 | Codigo : | Código: |
| Proceso Área Cátodos!T4 | Codigo : | Código: |
| B6 en las tres hojas de proceso | #VALUE! | Vacío |

B6 no contenía ninguna fórmula. Su OOXML era idéntico en las tres hojas:

```xml
<c r="B6" s="607" t="e" vm="1"><v>#VALUE!</v></c>
```

Era un valor de error almacenado con metadatos de valor. La auditoría de
fórmulas, referencias directas y rangos que incluyen B6, nombres definidos,
validaciones y fórmulas DrawingML no encontró dependencias funcionales. No se
detectaron fórmulas INDIRECT, OFFSET o ADDRESS que requirieran resolver
referencias dinámicas. El único nombre definido es el filtro de Análisis y no
referencia las hojas de proceso. El resultado fue:

```xml
<c r="B6" s="607"/>
```

Se retiraron únicamente el error y sus metadatos de valor. El estilo 607,
relleno, bordes, posición, dimensiones y merges permanecen intactos.
Se eliminaron **cero fórmulas**: el total final sigue en **2.774**, incluidas
las **1.080 fórmulas protegidas** de Análisis. F1–F120 están intactos.

La comparación completa del template antes/después admite exclusivamente
los cuatro textos de sharedStrings.xml (uno se usa en tres hojas) y el
vaciado de B6 en sheet7.xml, sheet8.xml y sheet9.xml. Todas las demás partes
son idénticas byte a byte, incluyendo DrawingML, shapes, conectores, imágenes,
estilos y relaciones. Los tres bloques de validaciones con #REF! en C11 se
conservaron sin modificación. No existen otros #REF! autorizados.

El Caso 24 se regeneró mediante los SELECT existentes: Run oficial 147,
01/08/2026–23/08/2026, L3 = L4 = 23. Filename contractual sin cambios:

`Balance_Planta_Hidrometalurgia_20260801_20260823_Caso24_Run147.xlsx`

Se compararon todas las celdas y todas las fórmulas con la copia previa del
reporte. D:I en Datos Reconciliados, tolerancias y medidos en Análisis,
período/MTD y fórmulas de balances son idénticos. Las únicas diferencias de
contenido son las nueve celdas enumeradas arriba. La copia previa contenía
67 partes, incluida xl/persons/person.xml; por ello, en ese reporte se realizó
comparación semántica de celdas, mientras que el template se comparó byte a
byte con una lista estricta de cambios permitidos. El nuevo exportable tiene
66 partes, CRC válido, XML y relaciones parseables, sin duplicados ZIP ni
referencias de celda duplicadas.

Microsoft Excel Desktop 16.0 abrió el archivo con CorruptLoad=0 (apertura
normal, sin solicitar reparación), solo lectura, sin actualizar vínculos y
cerrando sin guardar. Se verificó que el hash del archivo no cambió.

Pruebas ejecutadas:

- `python -m unittest report_export.tests.test_balance_official_mtd report_export.tests.test_balance_template_migration.TemplateMigrationTests -q`: **41 pruebas aprobadas**.
- `python -m scripts.fix_balance_template_cosmetics ...`: auditoría previa y
  posterior, sin dependencias de B6 y con cero fórmulas eliminadas.
- `python -m scripts.verify_balance_cosmetic_regression ...`: comparación
  estricta del template y comparación de valores/fórmulas del Caso 24.
- `python scripts/verify_balance_excel_desktop.py ...`: apertura normal
  confirmada en Excel Desktop.

Evidencia en `balance_cosmetic_audit.json`,
`balance_cosmetic_template_comparison.json`,
`balance_cosmetic_case24_comparison.json` y
`balance_cosmetic_excel_desktop.json`.

Diff de este ajuste por archivo:

- `reporte/Template_Balance_Planta_Hidrometalurgia.xlsx`: únicamente rótulos y B6 autorizados.
- `report_export/balance_contract.py`: nuevo SHA-256 contractual.
- `report_export/tests/test_balance_template_migration.py`: regresión adicional
  de ortografía y B6 vacío con estilo 607 conservado, en template y output.
- `scripts/fix_balance_template_cosmetics.py`: auditoría de dependencias y
  parche controlado, separado de la exportación.
- `scripts/verify_balance_cosmetic_regression.py`: comparación antes/después.
- Reporte Caso 24 y documentos de evidencia: regenerados para este ajuste.
- `report_export/docs/BALANCE_TEMPLATE_MIGRATION.md`: referencia al contrato
  vigente; conserva la auditoría histórica de la migración anterior.

No se modificó `export_to_excel.py` durante este ajuste cosmético.

Los siguientes KPI permanecen pendientes de definición/fuente, sin lógica nueva:

- Recuperación Lixiviación PAD Óxidos.
- Recuperación Lixiviación PAD Sulfuros.
- Eficiencia de Corriente Real.
- Consumo de Orgánico por Cátodo producido.
- Consumo de Diluyente por Cátodo producido.

No se modificó ningún objeto ni registro de base de datos.

No se modificó ninguna query, vista, SP ni lógica MTD.
