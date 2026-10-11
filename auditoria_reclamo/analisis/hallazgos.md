# Hallazgos

## [BUG PROBABLE] H1 — columnas oficiales de camiones sin escritor activo

Objeto: `sp_sincronizar_desde_etl`, `v_camiones_acumulado`.

Evidencia: el SP llena THM, la vista consume `m3_oficial/tms_oficial`; no hay trigger ni módulo SQL que escriba estos campos. Hoy 539/539 filas están pobladas, indicando una intervención externa/histórica no trazada.

Impacto: filas nuevas o reprocesadas pueden no alimentar el cálculo, o conservar oficiales obsoletos.

## [RIESGO] H2/H3 — reparto igualitario entre módulos abiertos

`v_preliminar_cv25` divide `tms_rotopala_dia_total / modulos_abiertos`. No usa saldo, corriente por módulo ni movimiento físico. Con dos abiertos y uno inmóvil, asigna 50/50.

## [BUG PROBABLE] H4/H5 — fecha automática no operacional

La apertura/cierre usa `SYSDATETIME()`. Un reproceso histórico cambia las ventanas de elegibilidad del preliminar y puede producir resultados distintos según el día en que se ejecuta.

## [BUG CONFIRMADO] H6 — semáforo no bloquea Publicar

El callback de publicación no consulta el semáforo. “NO PUBLICAR” es solo texto visual.

## [OK CON SALVEDAD] H7 — vista previa y SP comparten contrato

Ambos consumen `v_reclamo_para_conciliados`. Pueden divergir de una publicación histórica o de `calculo_diario` si no hubo reproceso/publicación posterior a cambios de vistas.

## [REVISAR] H8 — TMS disponible depende de los campos oficiales

La fórmula resta correctamente `tms_camiones_acum`, pero este acumulado depende de `tms_oficial`, afectado por H1.

## [OK] H9 — topografía no duplica línea base en la vista actual

La primera medición descuenta la línea base para el incremento. En cuadratura, el acumulado topográfico reemplaza la línea base; no se suma encima.

## [REVISAR] H10 — contexto publicado usa un ganador

Los TMS suman módulos, pero campaña/módulo/avance representan un único ganador diario. Es coherente como etiqueta, no como desglose completo; verificar que el criterio de ganador coincide con la definición operacional esperada.

## [OK] H11 — tag oficial predeterminado

El SP usa `cv025tot` por defecto y Dash no sobrescribe el parámetro.

## [BUG PROBABLE] H12 — humedad nula equivale a cero implícito

En una inserción sin `@HumedadPct`, `tms_dia=tmh_dia` y humedad queda NULL. En actualización puede conservar un porcentaje antiguo. El mismo botón puede producir semánticas distintas según exista previamente la fila.

## [OK CON SALVEDAD] H13 — la vista origen se trata como delta diario

El SP no diferencia totalizadores. La vista usa la convención `DELTA_TOTALIZADOR_CV25_DIARIO`; debe auditarse la definición interna de esa vista para demostrar matemáticamente el delta.

## [OK] H14 — granularidad horaria

Julio presenta 24 filas diarias y dos turnos. Una hora por muestra es coherente con la frecuencia observada.

## [DEUDA TÉCNICA] vistas activas modificadas el día de la auditoría

`v_preliminar_cv25` y `v_reclamo_diario` fueron modificadas el 2026-09-02, mientras `calculo_diario` observado fue calculado anteriormente. Comparar la vista actual con materializaciones históricas requiere controlar explícitamente esa diferencia temporal.

## [OBJETO HISTÓRICO]

Las vistas `vista_reclamo_diario_calculado_v2_test` a `v4_*` no aparecen en el flujo Python actual. Su clasificación preliminar por dependencias está en `15_objetos_reclamo_antiguos.csv`; “NO_REFERENCIADA” significa sin dependencia SQL catalogada, no autorización para eliminarlas.

