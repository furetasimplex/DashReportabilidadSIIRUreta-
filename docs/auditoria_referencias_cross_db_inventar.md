# Auditoría de referencias cross-database para promoción a PROD

Fecha de inspección: 2026-09-01  
Servidor inspeccionado: `VPS-5347319-X`  
Base efectiva: `inventar_SpcHidr`

## Objetivo

Identificar vistas, funciones y procedimientos cuyo SQL fija explícitamente una
base mediante nombres de tres o cuatro partes, para preparar el despliegue en
`inventar_SpcHidr_PROD` y reemplazar dependencias de `DEV_SIIR` por la base SIIR
de producción.

## Alcance y limitación

Se inspeccionaron `sys.sql_modules` y `sys.sql_expression_dependencies` de
`inventar_SpcHidr`. El catálogo contiene 258 módulos SQL:

- 165 vistas.
- 84 procedimientos almacenados.
- 6 funciones inline table-valued.
- 3 funciones escalares.

La inspección inicial se realizó contra el servidor DEV. Los nombres canónicos
confirmados para producción son exclusivamente `inventar_SpcHidr_PROD` y
`PROD_SIIR`. Los resultados de PROD deben validarse ejecutando
`docs/diagnostics/auditar_referencias_cross_db.sql` en el servidor que aloja
`inventar_SpcHidr_PROD`.

## Hallazgo 1: referencias fijadas a `inventar_SpcHidr`

Se encontraron 2 vistas y 4 dependencias reales. No se encontraron funciones ni
procedimientos con una dependencia de catálogo hacia `inventar_SpcHidr`.

| Módulo | Tipo | Referencia actual |
|---|---|---|
| `inventar_SpcHidr.vw_drena_quimica_ingest` | VIEW | `inventar_SpcHidr.inventar_SpcHidr.drena_concentrados_oxido` |
| `inventar_SpcHidr.vw_drena_quimica_ingest` | VIEW | `inventar_SpcHidr.inventar_SpcHidr.drena_concentrados_sulfuro` |
| `inventar_SpcHidr.vw_riego_diario_ingest` | VIEW | `inventar_SpcHidr.inventar_SpcHidr.flujos_reales_oxido` |
| `inventar_SpcHidr.vw_riego_diario_ingest` | VIEW | `inventar_SpcHidr.inventar_SpcHidr.flujos_reales_sulfuro` |

Estas referencias están amarradas a DEV aunque las vistas se creen dentro de
otra base. Al desplegarlas sin cambios en `inventar_SpcHidr_PROD`, continuarán
leyendo las cuatro tablas de `inventar_SpcHidr`.

### Ajuste recomendado

Usar nombres de dos partes, ya que ambas bases usan el esquema
`inventar_SpcHidr`:

```sql
[inventar_SpcHidr].[drena_concentrados_oxido]
[inventar_SpcHidr].[drena_concentrados_sulfuro]
[inventar_SpcHidr].[flujos_reales_oxido]
[inventar_SpcHidr].[flujos_reales_sulfuro]
```

Así el destino lo determina la base donde vive la vista. Alternativamente se
puede fijar `inventar_SpcHidr_PROD.inventar_SpcHidr.<tabla>`, pero eso elimina la
portabilidad del mismo DDL entre DEV y PROD.

## Hallazgo 2: módulos fijados a `DEV_SIIR`

`sys.sql_expression_dependencies` devuelve 10 módulos con dependencias reales:

| Módulo | Tipo | Objeto de DEV |
|---|---|---|
| `dbo.v_imp_conciliacion_chancado` | VIEW | `DEV_SIIR.hidro.imp_csv` |
| `inventar_SpcHidr.sp_calcular_balance_flujos` | SP | `DEV_SIIR.hidro.v_imp_chancado_normalizado` |
| `inventar_SpcHidr.sp_calcular_balance_flujos_copy1` | SP | `DEV_SIIR.hidro.v_imp_chancado_normalizado` |
| `inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test` | SP | `DEV_SIIR.hidro.imp_csv` |
| `inventar_SpcHidr.sp_mantiene_datos_conciliados_of` | SP | `DEV_SIIR.hidro.imp_csv` |
| `inventar_SpcHidr.sp_reporte_turno_emision_srr_origen_sim_test` | SP | `DEV_SIIR.hidro.v_imp_chancado_normalizado` |
| `inventar_SpcHidr.sp_reporte_turno_emision_test` | SP | `DEV_SIIR.hidro.v_imp_chancado_normalizado` |
| `inventar_SpcHidr.sp_reporte_turno_test` | SP | `DEV_SIIR.hidro.v_imp_chancado_normalizado` |
| `inventar_SpcHidr.v_conciliacion_chancado_v2` | VIEW | `DEV_SIIR.hidro.v_imp_conciliacion_chancado` |
| `inventar_SpcHidr.v_srr_tms_origen_turno_emision_test` | VIEW | `DEV_SIIR.hidro.v_imp_chancado_normalizado` |

Antes de promover, todas deben apuntar a la base productiva canónica
`PROD_SIIR`, comprobando que contiene:

- `hidro.imp_csv`
- `hidro.v_imp_chancado_normalizado`
- `hidro.v_imp_conciliacion_chancado`

## Casos descartados correctamente

Expresiones como `inventar_SpcHidr.flujo_coord.ID` y
`inventar_SpcHidr.tot_TM.tot_001` tienen tres tokens, pero representan
`schema.tabla.columna`; no fijan una base. Asimismo, las referencias normales
`inventar_SpcHidr.objeto` son `schema.objeto` y son portables entre ambas bases.

No se registraron dependencias de cuatro partes (`servidor.base.schema.objeto`)
en el catálogo inspeccionado.

## Plan de promoción

1. Usar únicamente los nombres productivos `inventar_SpcHidr_PROD` y
   `PROD_SIIR`.
2. Ejecutar el diagnóstico en el servidor de `inventar_SpcHidr_PROD` y guardar
   el resultado como evidencia previa.
3. Corregir las 2 vistas para usar referencias de dos partes.
4. Cambiar los 10 módulos de `DEV_SIIR` al catálogo productivo confirmado.
5. Verificar existencia y permisos `SELECT` sobre las tres dependencias `hidro`.
6. Repetir el diagnóstico: PROD debe arrojar cero referencias a
   `inventar_SpcHidr` como catálogo y cero referencias a `DEV_SIIR`.
7. Ejecutar `sp_refreshview`/`sp_refreshsqlmodule` y pruebas funcionales de
   riego, drena, conciliación, reporte por turno y balance de flujos.
