# Resultado: CUADRATURA_NEGATIVOS_NO_RESUELTO

La corrección de la vista **sí quedó aplicada en DEV**. El cierre funcional con
negativos reales no pasó porque esos valores no están actualmente en
`reclamo.camiones_reclamo`.

## Cambio comprobado

Antes: `SELECT MAX(c.m3_camiones_acum)`.

Después: `SELECT TOP (1) c.m3_camiones_acum ... ORDER BY c.fecha DESC`.

La definición anterior íntegra quedó en `definicion_before.sql` y la reversión
en `rollback.sql`. No se cambió ningún otro objeto SQL. La búsqueda de expresiones
`MAX(m3_camiones_acum)` / `MAX(tms_camiones_acum)` en las definiciones del esquema
`reclamo` no encontró otros casos después del ALTER. En la captura previa, otros
dos objetos aparecieron en la búsqueda amplia, pero sus `MAX` son de fecha,
número de módulo u otras columnas; no son máximos históricos de acumulados.

## Evidencia de datos

| Fecha | Módulo | Fuente ETL `volumen_diario_m3` | `camiones_reclamo.m3_thm` |
|---|---:|---:|---:|
| 01-10-2026 | M23 / id 87 | −49,596 | 0 |
| 02-10-2026 | M17 / id 81 | −36,690 | 0 |
| 02-10-2026 | M23 / id 87 | −49,454 | 0 |
| 03-10-2026 | M23 / id 87 | 0 | 0 |

La fuente es `inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario`.
El snapshot previo muestra **cero filas negativas** en toda
`reclamo.camiones_reclamo`; tampoco hay deltas negativos en
`reclamo.v_camiones_acumulado`. Por ello, en los módulos 81/87
`MAX(m3_camiones_acum)` y el último acumulado coinciden hoy. No se puede atribuir
una diferencia numérica a este ALTER hasta que los negativos lleguen a la tabla
de Reclamo.

## Regresión posterior

- `OBJECT_DEFINITION` devuelve la nueva vista; el `ALTER VIEW` compiló.
- 85 filas antes y después, 85 pares únicos `campaña_id + modulo_id`.
- 31 módulos con acumulados: `m3_camiones_sistema` coincide con su último
  `m3_camiones_acum`; `m3_camiones_total` coincide con línea base más ese valor.
- Ningún módulo cambió cifra en `before_after.csv`, coherente con la ausencia
  de correcciones negativas en la tabla consumida.
- M17/id 81: último y sistema = 1.469,773 m³; total = 1.469,773 m³;
  extraído = 1.469,773 m³; avance = 1,449807 %; saldo = 99.907,322 m³.
- M23/id 87: último y sistema = 31.361,928 m³; total = 31.361,928 m³;
  extraído = 31.361,928 m³; avance = 30,429211 %; saldo = 71.703,272 m³.

## Pendiente operacional

Revisar por qué la sincronización validada previamente no se refleja en la
tabla actual de DEV y, una vez que las correcciones estén presentes,
repetir `validacion_negativos.sql` y `validacion_regresion.sql`. Solo después
de esa comprobación corresponde considerar el reproceso manual 01-10-2026 →
04-10-2026 y revisar las cinco vistas/tablas indicadas en la tarea. No se
publicó Datos Conciliados ni se ejecutó reproceso.
