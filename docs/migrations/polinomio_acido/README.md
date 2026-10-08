# Polinomio Ácido

## Estado de implementación

La configuración versionada del polinomio de ácido está centralizada en los siguientes objetos:

- Tabla: `[inventar_SpcHidr].[dosis_acido_configuracion]`.
- Función escalar: `[inventar_SpcHidr].[fn_calcular_dosis_acido]`.

La versión vigente corresponde a la fila con el mayor `configuracion_id`. Cada cambio inserta una fila nueva y no modifica ni elimina versiones históricas.

Los siguientes objetos consumidores ya fueron actualizados para utilizar la función centralizada:

- `[inventar_SpcHidr].[sp_reporte_turno_emision_test]`.
- `[inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]`.

Con esta integración, los coeficientes y umbrales ya no deben quedar codificados directamente en esos dos objetos. Cualquier nueva configuración guardada desde el módulo **Polinomio Ácido** pasa a ser utilizada por ambos.

## Firma pública

```sql
[inventar_SpcHidr].[fn_calcular_dosis_acido]
(
    @solubilidad DECIMAL(18,6),
    @co3         DECIMAL(18,6),
    @cus         DECIMAL(18,6)
)
```

La función devuelve `DECIMAL(18,2)`. Los parámetros almacenados conservan precisión `DECIMAL(18,6)`.

## Integración en el reporte por turno

En `[inventar_SpcHidr].[sp_reporte_turno_emision_test]`, el cálculo de `Dosis_Acido_Ideal_TM` utiliza:

```sql
[inventar_SpcHidr].[fn_calcular_dosis_acido]
(
    CAST(Solubilidad_Real AS DECIMAL(18,6)),
    CAST(CO3_Real         AS DECIMAL(18,6)),
    CAST(CuS_Real         AS DECIMAL(18,6))
)
```

El cálculo de `Dosis_Acido_Programa_Semanal` utiliza:

```sql
[inventar_SpcHidr].[fn_calcular_dosis_acido]
(
    CAST(CuS_Programa / NULLIF(CuT_Programa, 0) AS DECIMAL(18,6)),
    CAST(CO3_Programa                              AS DECIMAL(18,6)),
    CAST(CuS_Programa                              AS DECIMAL(18,6))
)
```

## Integración en el reporte diario

En `[inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]`, el cálculo de `Dosis_Acido_Ideal_Dia` utiliza:

```sql
[inventar_SpcHidr].[fn_calcular_dosis_acido]
(
    CAST(Solubilidad_Real_Dia AS DECIMAL(18,6)),
    CAST(CO3_Real_Dia         AS DECIMAL(18,6)),
    CAST(CuS_Real_Dia         AS DECIMAL(18,6))
)
```

El cálculo de `Dosis_Acido_Programa_Semanal` mantiene el mismo mapeo de programa indicado para el reporte por turno.

## Validaciones conservadas en los consumidores

Los objetos consumidores mantienen sus condiciones previas para decidir si el resultado es evaluable. Por ejemplo, ausencia o valor cero del tonelaje base y datos requeridos nulos pueden producir `NULL` antes de invocar la función. La función centralizada se ocupa exclusivamente de aplicar la fórmula con la configuración vigente.

## Migración

El script idempotente que crea la tabla, registra la configuración inicial y crea o actualiza la función está en [`001_dosis_acido_configuracion.sql`](001_dosis_acido_configuracion.sql).

Después de crear esos objetos, ejecutar
[`002_integrar_consumidores_polinomio_acido.sql`](002_integrar_consumidores_polinomio_acido.sql)
para actualizar las definiciones completas de producción de:

- `[inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]`.
- `[inventar_SpcHidr].[sp_reporte_turno_emision_test]`.

La segunda migración fue construida desde las definiciones extraídas de
`inventar_SpcHidr_PROD` el 08-10-2026. Es idempotente mediante `CREATE OR ALTER`,
comprueba primero que exista `[inventar_SpcHidr].[fn_calcular_dosis_acido]` y
conserva el resto de cada definición sin cambios.

Orden de ejecución:

```text
001_dosis_acido_configuracion.sql
002_integrar_consumidores_polinomio_acido.sql
```
