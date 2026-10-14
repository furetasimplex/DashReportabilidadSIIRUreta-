# Polinomio Ácido con vigencia temporal

## Regla de negocio

Los parámetros se seleccionan según la fecha del dato calculado. Una nueva
configuración no cambia el resultado de fechas históricas: cada reporte vuelve
a usar la versión que estaba vigente en su fecha.

La tabla guarda `vigencia_desde`. La fecha final se deriva como el día anterior
a la siguiente `vigencia_desde`; no se almacena para evitar rangos
contradictorios. La última versión queda abierta y se presenta como **En uso**.

## Objetos

- Tabla: `[inventar_SpcHidr].[dosis_acido_configuracion]`.
- Función temporal: `[inventar_SpcHidr].[fn_calcular_dosis_acido_fecha]`.
- Función compatible: `[inventar_SpcHidr].[fn_calcular_dosis_acido]`.
- Registro controlado: `[inventar_SpcHidr].[sp_registrar_dosis_acido_configuracion]`.

Consumidores temporales:

- `[inventar_SpcHidr].[fn_generador_reporte_diario_emision_test]` usa `d.Fecha`.
- `[inventar_SpcHidr].[sp_reporte_turno_emision_test]` usa `r.Fecha`.

No se agregan columnas al resultado de los reportes para no romper la caché,
`INSERT ... EXEC`, la exportación Excel ni otros consumidores posicionales.

## Periodo histórico inicial

La primera versión comienza el `1900-01-01`, con los parámetros estáticos
utilizados antes de incorporar vigencias. Esto garantiza cobertura para los
reportes históricos existentes. Cuando comienza una versión nueva, el fin de la
anterior se deriva automáticamente.

## Registro de versiones

La aplicación no inserta directamente en la tabla. El procedimiento de
registro:

- usa una transacción y bloqueo `UPDLOCK, HOLDLOCK`;
- verifica que la versión revisada siga siendo la última;
- exige que la nueva fecha sea posterior a la última vigencia;
- inserta el conjunto completo de parámetros;
- no actualiza ni elimina versiones históricas.

Las correcciones retroactivas quedan fuera de la UI normal y requieren una
migración SQL revisada expresamente.

## Interfaz temporal

```sql
SELECT [inventar_SpcHidr].[fn_calcular_dosis_acido_fecha]
(
    @fecha_calculo,
    @solubilidad,
    @co3,
    @cus
);
```

La función devuelve `DECIMAL(18,2)`. Los parámetros se almacenan como
`DECIMAL(18,6)` y la UI los presenta sin redondeo visual.

## Orden de despliegue

```text
001_dosis_acido_configuracion.sql
002_fn_calcular_dosis_acido_fecha.sql
003_sp_registrar_dosis_acido_configuracion.sql
004_integrar_consumidores_dosis_acido_fecha.sql
005_verificar_polinomio_acido_vigencia.sql
```

Los scripts apuntan explícitamente a `inventar_SpcHidr_PROD`. El cuarto script
se construyó desde las definiciones de producción extraídas el 08-10-2026 y
conserva el resto de ambos objetos sin cambios.

## Estados mostrados en la UI

- **HISTÓRICA**: su periodo ya terminó.
- **VIGENTE**: aplica a la fecha actual.
- **PROGRAMADA**: comenzará en una fecha futura.

La UI permite consultar una fecha para identificar su versión aplicable y
muestra para cada fila el rango **Desde — Hasta**, usuario, fecha de registro,
comentario y los once parámetros.
