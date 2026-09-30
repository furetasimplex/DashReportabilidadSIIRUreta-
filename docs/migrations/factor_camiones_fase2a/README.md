# Límites de carga para ajuste — Fase 2A, cadena V2 DEV

## Alcance

Parametriza exclusivamente 380 KOM / 265 CAT. No modifica producción/viajes de `mov_cam_powerbi`, fórmulas de balance/factor, cadena antigua, reportes, publicación o dashboard. No introduce constantes 357/236 ni overrides de factor.

Objetos modificados, esquema `inventar_SpcHidr`:

- `sp_factor_ajuste_camiones_test`: captura una copia consistente de vigencias, valida exactamente una por día/flota, usa sus límites en la corrección y clasificación de estados y los devuelve al final del resultado.
- `sp_mantiene_factor_ajuste_camiones_v2_test`: amplía las dos columnas finales de `#CalculoFactorV2` usadas por `INSERT EXEC` y persiste sus valores, sin otra consulta de vigencias.
- `v_ajuste_camiones_emision_test`: agrega al final `Limite_KOM_TMH_Viaje` y `Limite_CAT_TMH_Viaje` de la tabla V2. Las columnas anteriores conservan orden y fórmulas.

Objetos nuevos:

- `factor_camiones_parametro_vigencia_test`.
- `factor_camiones_parametro_auditoria_test`.
- `sp_registrar_limite_factor_camiones_vigencia_test`.
- `tr_factor_camiones_vigencia_solapamiento_test`: salvaguarda breve de intervalos, incluso frente a DML privilegiado.

Los dos campos de límites de `Control_Factor_Ajuste_Camiones_v2_test` ya existen y son FLOAT; no se altera su esquema ni se actualiza permanentemente su histórico.

## Scripts y ejecución

- `01_parametros.sql`: DDL, constraints, índices, protección DML, trigger y seed idempotente.
- `02_registro.sql`: procedimiento transaccional y auditoría.
- `03_sp_factor_ajuste_camiones_test.sql`: definición final del cálculo.
- `04_sp_mantiene_factor_ajuste_camiones_v2_test.sql`: definición final del mantenedor.
- `05_v_ajuste_camiones_emision_test.sql`: definición final de emisión.
- Archivos `.diff`: diferencias precisas frente a las definiciones respaldadas.
- `rollback_dev.sql`: restaura las tres definiciones previas y retira los cuatro objetos nuevos. No reprocesa datos.

El runner `scripts/factor_camiones_fase2a.py` valida base efectiva y servidor DEV mediante `_engine_dev()` y `_assert_dev_connection()` antes de cualquier despliegue. Sin argumentos ejecuta pruebas transaccionales y revierte todo. `--deploy` permite persistir únicamente tras aprobarlas. Rechaza reinstalación cuando ya existe la tabla: evita tratar una implementación previa como baseline original. La idempotencia de los lotes de migración se comprueba aplicándolos dos veces durante la validación.

Los SQL son artefactos revisables. Ejecutarlos mediante un runner que valide la identidad DEV y dentro de una transacción, no individualmente en una conexión sin verificar. El rollback debe ejecutarse con esa misma protección y como una unidad transaccional, nunca en PROD. Su contenido restaura la configuración previa; no incluye el borrado de resultados históricos.

## Vigencias y auditoría

Intervalos `[vigencia_desde, vigencia_hasta)`: el inicio es inclusivo y el fin exclusivo. NULL en el fin significa hasta nuevo aviso. El procedimiento solo recibe flota, valor, inicio, motivo y usuario. Divide el intervalo que contiene la fecha; si hay una vigencia posterior conserva su inicio como fin de la nueva.

Seed confirmado: KOM=380 y CAT=265 desde **01-07-2026**, basado en MIN(Fecha) de la tabla V2 y confirmado por el usuario. No se toman fechas de la cadena antigua. No se introducen valores predeterminados de respaldo en cálculo ni vista.

Un inicio duplicado se rechaza. Los cambios retroactivos se permiten y registran valor anterior/nuevo, usuario, motivo, fecha efectiva, fecha/hora de registro y retroactividad. Los estados no se traducen ni alteran en esta fase.

El impacto devuelve la fecha efectiva y MAX(Fecha) materializada de V2. Es una estimación conservadora hasta la última materialización, incluso si existe una vigencia futura intermedia. Para un cambio futuro puede devolver fin anterior al inicio: significa que no hay todavía filas materializadas afectadas; no dispara ningún reproceso. Retroactividad se compara con la fecha de `SYSDATETIME()` del servidor SQL, siguiendo el patrón existente.

## Integridad y concurrencia

- CHECK: flota, parámetro, valor positivo e intervalo válido.
- UNIQUE: inicio por flota/parámetro, y una sola vigencia activa abierta.
- Trigger corto: rechazo de intervalos activos superpuestos.
- DML denegado a `public` sobre las dos tablas; la operación normal debe pasar por el procedimiento mediante ownership chaining. No se otorgan nuevos permisos de ejecución masivos. La asignación de permisos al futuro rol especialista queda fuera de la UI actual.
- Registro: `sp_getapplock`, recurso `SIIR_FACTOR_CAMIONES_PARAMETROS_DEV`, modo exclusivo, propietario transacción; bloqueo exclusivo solo sobre la pequeña tabla de parámetros. Una llamada dentro de una transacción ajena no la confirma.
- Cálculo: una sola captura de las vigencias con `HOLDLOCK`, con las dos flotas; la copia temporal se usa para todo el rango. El mantenedor persiste los valores devueltos, aunque posteriormente se registre otra vigencia.
- Configuración ausente o múltiple: error explícito con fecha y flota, sin COALESCE/DEFAULT a 380/265. Fechas anteriores al seed fallan expresamente.

## Validación: tres comparaciones distintas

### A. Deriva preexistente — H vs O

Conservar el diagnóstico aprobado: **172 diferencias de celdas**, seis días de septiembre que pasan de `SIN_DATOS_CAMIONES` a cálculo válido, 22-09 con factor original actual aproximado 0.9588138 frente a factor almacenado NULL/aplicado 1, más diferencias menores de precisión. Evidencia original en `docs/diagnosticos/factor_camiones_fase2a/baseline_20260928_100315/`.

El conteo exacto de celdas puede variar en nuevas ejecuciones por FLOAT; no reemplaza ni invalida ese diagnóstico. Las comparaciones nuevas se guardan separadamente. H no se corrige ni se usa como aceptación de la parametrización.

### B. Parametrización — O vs P_BASE

Misma conexión, misma transacción SERIALIZABLE y mismo rango de 84 días (01-07 a 22-09). O se ejecuta antes de los ALTER; P después, dentro de esa misma transacción. Los locks de lectura retenidos mantienen el snapshot lógico de entradas y bloquean cambios concurrentes relevantes durante la prueba. No se cambia configuración global de aislamiento del servidor.

Se compara cada columna del cálculo original, control y vista, excluyendo únicamente Fecha_Calculo. Los límites nuevos se verifican expresamente en 380/265. Se guardan originales, diferencias y máximos por columna. No se redondean los datos.

SQL FLOAT tiene acumulaciones no asociativas: también se ejecuta O dos veces para evidenciar variabilidad previa. Las diferencias de representación se registran individualmente y se aceptan solo dentro de 8 ULP; para checks de cancelación se usa la escala de sus operandos. NULL, flags, enteros y estados exigen igualdad exacta. Una diferencia funcional detiene el despliegue.

### C. Vigencia temporal — P_BASE vs P_PRUEBA

El candidato se selecciona del cálculo actual buscando carga KOM >350 y <=380, con margen de cinco días para probar la frontera. Se valida reducción real de toneladas/factor, D-1/D/D+1, CAT sin cambios, segundo cambio 350→365, inserción entre vigencias, cambio futuro, retroactividad, auditoría y reproceso D-5→D+5. También se prueba CAT temporal=250. Ningún valor provisional es una regla oficial.

Todos los recálculos y registros provisionales terminan en ROLLBACK. Después se compara exactamente el control V2 completo, incluidos timestamps, la vista previa y la tabla antigua. Las definiciones se restauran tras la prueba. Se ensaya asimismo el rollback técnico dentro de una transacción reversible.

Las pruebas negativas usan una transacción independiente por caso y comprueban el código SQL esperado, no solo cualquier excepción. Incluyen superposición, dos intervalos abiertos, inicio duplicado, faltante, múltiples coincidencias (corrupción simulada reversible), fechas anteriores al seed, parámetros inválidos e intervalos inválidos.

## Limitaciones operacionales

La salida del SP de cálculo agrega dos columnas al final. Su consumidor SQL identificado con `INSERT EXEC`, el mantenedor V2, se actualiza conjuntamente. Un consumidor externo no inventariado que dependa del número exacto de columnas debe adaptar su contrato.

Una vez registrada una nueva vigencia real, los resultados históricos almacenados no se actualizan automáticamente: el reproceso explícito sigue siendo una operación separada. Esta fase no publica ni habilita formularios de edición.

Las pruebas de concurrencia posteriores al despliegue revierten todas sus filas; como es normal en SQL Server, los contadores IDENTITY pueden tener huecos tras ROLLBACK. No son vigencias ni eventos residuales.
