# Regla Chancado TMS Real sin flujos — DEV

## Ruta oficial verificada

`report_export/callbacks/reportabilidad_cb.py` exporta el paquete preparado por
`preparar_paquete_datos_conciliados_emision` en `report_export/report_export.py`.
Este llama a `actualizar_datos_conciliados_emision_report`, que ejecuta
`inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test`. El SP lee
`inventar_SpcHidr.v_ajuste_camiones_emision_test` (`aj`), asigna
el Chancado reportable a `Datos_conciliados_of.Chancado_TMS_Real` y el
exportador lee esa tabla. La hoja Balance Chancado consulta `aj`, inventario y
`Datos_conciliados_of` mediante `fetch_balance_chancado_report`.

## Diagnóstico previo

| Objeto | Campo | Fórmula / función |
|---|---|---|
| `v_ajuste_camiones_emision_test` | `Apilado_TMS_Reporte` | Apilado neto de sal, con override/factor vigente. |
| `v_ajuste_camiones_emision_test` | `Sal_TMH_Dia` | Sal preservada como flujo independiente; no se vuelve a descontar del apilado neto. |
| `v_ajuste_camiones_emision_test` | `SRR_TMS_Dia` | SRR físico del balance. |
| `v_ajuste_camiones_emision_test` | `Delta_Inventario_Chancado_TMS` | Variación de inventario preservada. |
| `v_ajuste_camiones_emision_test` | `Chancado_TMS_Reporte` | Cálculo efectivo anterior, `Apilado_TMS_Reporte + Delta_Inventario_Chancado_TMS - SRR_TMS_Dia`, comprobado por el validador del balance. |
| `sp_mantiene_datos_conciliados_emision_test` | `Chancado_TMS_Real` | Antes: `aj.Chancado_TMS_Reporte`. Después: `ch.Chancado_TMS_Real`, calculado antes de los consumidores aguas abajo; cero si apilado, sal y SRR son exactamente cero. |

La causa de los valores del 01 y 02 de octubre era el paso directo del delta
de inventario al campo reportable cuando los tres flujos eran cero.

Se conservó `Chancado_TMS_Reporte` como valor calculado y
`Delta_Inventario_Chancado_TMS` como trazabilidad. `fetch_balance_chancado_report`
también expone `Chancado_TMS_Reconstruido`. No se agregaron columnas a contratos
existentes. El motivo `SIN_APILADO_SAL_SRR` se reconoce por las tres columnas
iguales a cero; no se creó una columna `Motivo_Ajuste`.

En las 96 filas disponibles de enero al 04-10, los tres campos del gate no son
NULL. La nueva condición SQL exige que cada uno sea exactamente cero; ante un
NULL no activa el gate y conserva el cálculo anterior. No se equiparó ausencia
desconocida con cero.

## Diff funcional y dependencia SRR

```sql
-- Antes
aj.Chancado_TMS_Reporte AS Chancado_TMS_Real,

-- Después: un solo cálculo antes de los campos derivados
CASE
    WHEN aj.Apilado_TMS_Reporte = 0
     AND aj.Sal_TMH_Dia = 0
     AND aj.SRR_TMS_Dia = 0 THEN 0
    ELSE aj.Chancado_TMS_Reporte
END AS Chancado_TMS_Real -- en CROSS APPLY ch

ch.Chancado_TMS_Real, -- salida de Datos Conciliados
-- Ley_CuT_Real_srr usa también ch.Chancado_TMS_Real
```

La definición previa completa, ALTER mínimo y rollback están en
`definicion_before.sql`, `alter_sp_mantiene_datos_conciliados_emision_test.sql`
y `rollback.sql`. La segunda pasada crítica está documentada por
`dependency_before.sql`, `alter_dependency_srr.sql`,
`diff_dependency_srr.patch` y `rollback_dependency_srr.sql`.

Antes de esta segunda pasada, `Ley_CuT_Real_srr` leía directamente
`aj.Chancado_TMS_Reporte`. Ahora la columna emitida, su control de NULL y el
término de Chancado en esa ley leen el mismo `ch.Chancado_TMS_Real`. El gate
solo consulta `aj.Apilado_TMS_Reporte`, `aj.Sal_TMH_Dia` y
**`aj.SRR_TMS_Dia`**, que es el flujo SRR de entrada; no consulta la ley SRR
calculada ni crea dependencia circular. `aj.Delta_Inventario_Chancado_TMS`
conserva sus referencias y valor.

## Resultado octubre

| Fecha | Antes Chancado real | Después | Δ Inventario TMS preservado |
|---|---:|---:|---:|
| 01-10 | +147,512386 | 0 | +147,512386 |
| 02-10 | −133,401347 | 0 | −133,401347 |
| 03-10 | 11.969,149069 | 11.969,149069 | −432,990706 |
| 04-10 | 49.152,535057 | 49.152,535057 | +1.386,535504 |

La comparación transaccional de los 50 campos de `Datos_conciliados_of` para
01–04 confirmó que solo cambió `Chancado_TMS_Real` en 01–02. La vista de
ajuste conservó todas sus columnas en los cuatro días. El validador del Excel
se adaptó al nuevo campo reportable y mantuvo la verificación de la fórmula
física de `Chancado_TMS_Reporte`. Se generó y releyó
`balance_chancado_dev_preview.xlsx` con la función oficial de la hoja.

## Impacto histórico

Consulta sobre 01-01 a 04-10-2026: **cuatro fechas** con apilado, sal y SRR
iguales a cero y delta de inventario distinto de cero:

| Fecha | Chancado anterior | Esperado | Δ Inventario |
|---|---:|---:|---:|
| 02-09 | +16,790951 | 0 | +16,790951 |
| 21-09 | +774,601415 | 0 | +774,601415 |
| 01-10 | +147,512386 | 0 | +147,512386 |
| 02-10 | −133,401347 | 0 | −133,401347 |

Las dos fechas de septiembre **no se reprocesaron**. El impacto histórico es
potencial hasta que se decida su reproceso.

## Pruebas y límite operacional

- Pasaron los cinco casos pedidos: delta positivo/negativo sin flujos, tres
  flujos, solo Sal y solo SRR. También pasó un caso adicional con Apilado NULL:
  no se aplica el gate.
- Pasó la lectura y validación de Balance Chancado oficial de cuatro días y la
  construcción/lectura de su hoja Excel.
- El `ALTER PROCEDURE` compiló y la definición quedó instalada en DEV.
- La segunda pasada del SP también compiló. `OBJECT_DEFINITION` registra una
  referencia al Chancado calculado dentro de `CROSS APPLY` y tres usos de
  `ch.Chancado_TMS_Real` aguas abajo. Las cuatro filas materializadas de
  octubre quedaron idénticas antes y después de este ALTER de definición.
- Un ensayo de refresco completo del SP, dentro de una transacción revertida,
  reveló que además modificaría tres campos de Reclamo por camiones del 01-10
  (`Camiones_TMS_Reclamo_Sulfuros`, `Camiones_TMS_total` y
  `Total_Ripios_Incluye_Camiones_Real`) por deriva independiente de fuentes.
  Para cumplir el alcance de esta tarea se materializó únicamente el campo
  Chancado de 01–02, después de instalar la regla en el SP oficial. El próximo
  refresco integral del exportador debe considerar esa deriva de Reclamo.

**Variación Inventario TMS preservada: Sí. Apilado preservado: Sí. Sal
preservada: Sí. SRR preservado: Sí. En esta materialización solo cambió
Chancado TMS Real: Sí.**

No se ejecutó PROD ni se publicó allí.
