Esta auditoría registra la migración inicial. El ajuste cosmético posterior y
el hash contractual vigente se documentan en [BALANCE_COSMETIC_FIX.md](BALANCE_COSMETIC_FIX.md).

La migración utiliza exclusivamente `Template_Balance_Planta_Hidrometalurgia(3).xlsx`,
con SHA-256 de entrada `f1b7e6073a386c3f26df1d55ae858acbefc041b190a0ac72b3bf8adffac64a44`.
No se utilizó ningún template anterior como base de la migración.

El archivo canónico final es `reporte/Template_Balance_Planta_Hidrometalurgia.xlsx`.
Su SHA-256 contractual, calculado después de la estandarización, es:

`340B4CFD40B51E8D4E748BD1C2988F5D8BD2BDD68AF5FA13ACE99F513C273302`

Se corrigieron 35 nodos de texto visibles y el espaciado de un cuadro DrawingML de
período. Las correcciones incluyen Período/período, Días/días, Variación,
Producción, Lixiviación, Sulfuros, Piscinas, Catódica/catódica, Catódico, cátodo,
Pérdidas, Ácido Sulfúrico/ácido sulfúrico y Macroproceso. Se mantiene `tmf`.
El detalle antes/después está en `balance_template_migration_audit.json`.
Solo cambiaron sharedStrings.xml y los textos de drawing1.xml, drawing2.xml y
drawing3.xml. No se reserializaron las hojas: todos sus bytes se preservaron
durante la estandarización, incluidas fórmulas, estilos, referencias y merges.

La auditoría de entrada y salida confirma 9 hojas y 66 partes ZIP, CRC válido,
cero partes duplicadas, XML y relaciones parseables, cero referencias de celda
duplicadas por fila y ausencia de vínculos externos del workbook.

| Hoja | Fórmulas conservadas |
| --- | ---: |
| Resumen | 50 |
| Informe Hidrometalurgia | 123 |
| Balance por Áreas | 437 |
| Diagrama | 0 |
| Datos Reconciliados | 2 |
| Análisis Variación-Tolerancias | 1.080 |
| Proceso Área Seca | 298 |
| Proceso Área Húmeda | 684 |
| Proceso Área Cátodos | 100 |
| Total | 2.774 |

El nuevo contrato de Análisis conserva B = ID Flujo, C = Nombre y F1–F120 en
las filas 4:123. Python escribe exclusivamente los datos fuente:

| Columnas | Contenido |
| --- | --- |
| D / E | Tolerancia masa / tolerancia ley Cu |
| F / J / N | Masa medida / ley Cu medida / fino Cu medido |
| G:I | Reconciliado, diferencia y variación de masa: 360 fórmulas |
| K:M | Reconciliado, diferencia y variación de ley: 360 fórmulas |
| O:Q | Reconciliado, diferencia y variación de fino: 360 fórmulas |

Las 1.080 fórmulas protegidas se preservan. G/K/O enlazan con D/E/F de Datos
Reconciliados, respectivamente. Se conservan merges D1:D3, E1:E3, F1:Q1,
F2:I2, J2:M2 y N2:Q2. Datos Reconciliados conserva B3:B122, D:F para período,
G:I para acumulado y L3/L4 calculados con fecha final inclusiva.

Los encabezados se validan por coordenada y texto contractual: Área Seca!P14,
Área Húmeda!U17 y U105, Área Cátodos!P14. Los cuadros superiores usan
`Período: 01 al 23 de Agosto 2026.` en la regresión. Resumen mantiene F10:G10,
Arial 12, negrita, centrado, relleno, bordes y altura; solo la fuente de F10
se hace negra FF000000 en el output.

| DrawingML de proceso | Shapes | Conectores | Imágenes |
| --- | ---: | ---: | ---: |
| Área Seca | 29 | 35 | 1 |
| Área Húmeda | 38 | 84 | 1 |
| Área Cátodos | 11 | 11 | 1 |

Los drawings de procesos son idénticos byte a byte entre template y output.
También se conservan las relaciones de drawings y las imágenes. Informe
Hidrometalurgia y Balance por Áreas conservan todas sus fórmulas.
Las regresiones históricas verifican F34 en Área Seca!P47:S47, F106 en Área
Cátodos!P16:S16, F119 en Área Cátodos!P26:S26 (período y acumulado, masa y fino),
F118/F120 en Informe Hidrometalurgia!E24 y F69 en E56/F56.

Excepción conocida del template:
3 validaciones de datos preexistentes con #REF! en C11 de las hojas de
proceso. No corresponden a fórmulas de cálculo y fueron preservadas sin
modificación.

La excepción se restringe exactamente a `dataValidation/formula1`, con
`sqref="C11"`, en Proceso Área Seca, Proceso Área Húmeda y Proceso Área Cátodos.
Se verifica igualdad byte a byte de los bloques dataValidations. El validador
rechaza cualquier otro #REF!, una excepción ausente o duplicada:

- #REF! en fórmulas de celdas: 0.
- #REF! en otras validaciones: 0.
- #REF! autorizados: 3.

Pruebas ejecutadas:

`python -m unittest report_export.tests.test_balance_official_mtd report_export.tests.test_balance_template_migration.TemplateMigrationTests -q`

Resultado: **40 pruebas aprobadas**. Incluyen lógica MTD existente, NULL frente a
cero, signos negativos, entradas medidas distintas del reconciliado, integridad
de fórmulas y DrawingML, metadata y la excepción estricta #REF!.

La regresión real se generó mediante las consultas SELECT existentes del Caso
24, Run oficial 147, período y MTD 01/08/2026–23/08/2026; L3 = L4 = 23.
Archivo: `report_export/exports/Balance_Planta_Hidrometalurgia_20260801_20260823_Caso24_Run147.xlsx`.
Microsoft Excel Desktop 16.0 lo abrió correctamente con `CorruptLoad=0`
(apertura normal, sin solicitar reparación), solo lectura y sin actualizar
vínculos. Se cerró sin guardar y se verificó que su hash no cambió.
La evidencia está en `balance_template_excel_desktop.json`.

Cambios por archivo:

- `reporte/Template_Balance_Planta_Hidrometalurgia.xlsx`: adopción de (3) con
  las correcciones de texto autorizadas.
- `report_export/balance_contract.py`: única constante de hash actualizada.
- `report_export/export_to_excel.py`: entradas D/E/F/J/N, validación de las
  1.080 fórmulas y enlaces G/K/O, merges nuevos, U17, Período con tilde y
  excepción #REF! estricta. Se mantiene el ensamblado final desde el paquete
  OOXML original y la sustitución atómica de celdas para None.
- `report_export/tests/test_balance_official_mtd.py`: expectativas actualizadas
  al template actual; se conservan las regresiones existentes.
- `report_export/tests/test_balance_template_migration.py`: cinco regresiones
  nuevas de inputs/fórmulas, referencias históricas, ortografía, DrawingML y
  aceptación/rechazo de #REF!.
- `scripts/migrate_balance_template_contract.py`: adopción reproducible, fuera
  del runtime de exportación, con hash de entrada obligatorio y registro de
  correcciones. Ejecutar como módulo `python -m scripts.migrate_balance_template_contract`.
- `scripts/verify_balance_excel_desktop.py`: verificación aislada, de solo
  lectura, con Excel Desktop.
- Archivos de auditoría y reporte de regresión: evidencia de esta migración.

No se modificó ningún objeto ni registro de base de datos.

No se modificó ninguna vista, SP ni query funcional.

El template maestro aprobado sólo fue reemplazado por la nueva versión
contractual y no es modificado durante la exportación. No se modificó lógica
MTD, reconciliación, solver, oficialización ni selector operacional.
