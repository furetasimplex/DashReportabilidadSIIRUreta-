Los cuatro encabezados acumulados de procesos se generan exclusivamente desde
`metadata.mtd_fecha_fin`, con formato `Acumulado al DD de Mes`:

- Proceso Área Seca!R14.
- Proceso Área Húmeda!W17 y W105.
- Proceso Área Cátodos!R14.

El servicio existente entrega el cierre MTD como `fecha_fin_acumulado`; el
exportador normaliza ese alias a `mtd_fecha_fin` en la metadata de presentación
cuando este último no viene informado. No usa `fecha_fin` del Caso como
fallback para estos rótulos. Una fecha MTD ausente/inválida provoca error.
No se modifica el servicio ni el cálculo MTD. Los cuatro rótulos de período
mantienen su lógica y posiciones.

Regresión real mediante los SELECT existentes:

| Caso / Run | Cierre MTD | Resultado en los cuatro encabezados |
| --- | --- | --- |
| 18 / 113 | 2026-07-15 | Acumulado al 15 de Julio |
| 24 / 147 | 2026-08-23 | Acumulado al 23 de Agosto |

El Caso 18 conserva su cadena MTD de Casos 1 y 18, Runs 9 y 113, desde el
01/07/2026 hasta el 15/07/2026. Evidencia de los archivos regenerados:
`balance_accumulated_headers_cases.json`.

Pruebas: `python -m unittest report_export.tests.test_balance_official_mtd report_export.tests.test_balance_template_migration.TemplateMigrationTests -q`:
**46 pruebas aprobadas**. Se agregaron regresiones para ambos casos y una
prueba aislada del formateador con fecha MTD diferente de la fecha del Caso,
para comprobar cuál campo utiliza. Las pruebas existentes preservan 2.774
fórmulas, 1.080 protegidas, nodos `<f>`/calcChain byte a byte, cero cachés de
fórmula, calcPr, DrawingML, tres #REF! autorizados y apertura Resumen!A1.

Cambios limitados a `report_export/export_to_excel.py` y
`report_export/tests/test_balance_template_migration.py`, más exportables y
evidencia. El template no cambió y conserva SHA-256:

`C8F5AE2730EAE6827E083031D7A907432B385D9BFFA941E472F44A5D01EEBF8D`.

No se modificaron datos F1–F120, lógica MTD, fórmulas, DrawingML, SQL, BD,
solver ni oficialización.
