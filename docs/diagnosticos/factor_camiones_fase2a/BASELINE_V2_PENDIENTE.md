# Fase 2A V2: diferencia previa a parametrización

Inspección del 28-09-2026 con el alcance V2 corregido y autorizado. Ambiente DEV validado por `_engine_dev` y `_assert_dev_connection` antes de ejecutar el mantenedor. No se accedió a PROD.

## Prueba realizada

Se respaldaron las definiciones vigentes de cálculo, mantenedor V2, vista y mantenedor antiguo, el esquema de columnas V2, las 84 filas del control V2, la vista y la tabla antigua.

Sin modificar ningún procedimiento ni límite, se ejecutó el mantenedor V2 para 01-07-2026 a 22-09-2026 con `@DiasReproceso=0`, dentro de una transacción explícita que terminó en ROLLBACK. Se comprobó previamente que la tabla destino no tiene triggers habilitados.

Los resultados recalculados con el código original ya difieren del histórico materializado:

- Control V2: 172 diferencias de celdas, excluyendo `Fecha_Calculo`.
- Vista: 153 diferencias de celdas, excluyendo `Fecha_Calculo`.
- Hay diferencias funcionales y también diferencias menores de punto flotante; no deben confundirse.
- Producción KOM difiere en 15 fechas; vueltas KOM en 6 fechas.
- Seis fechas pasan de `SIN_DATOS_CAMIONES` a estados válidos: 11, 12, 13, 14, 21 y 22 de septiembre.
- El 14-09 pasa de factor calculado NULL/aplicado 1 a 0.9969306325085555 para ambos.
- El 22-09 pasa de factor calculado NULL/aplicado 1 a 0.9588137558699753 para ambos.
- El 16-09 presenta una diferencia menor: factor 0.2152051888950802 frente a 0.21520517011568346, junto con variación de SRR de 0.000149 TMS.

Esto prueba que las diferencias preceden a la parametrización. Los valores de entradas recuperados hoy no reproducen íntegramente las filas guardadas. No se atribuye aquí una causa histórica concreta de la modificación de las fuentes sin auditoría adicional.

## Evidencia y diferencias máximas

Directorio: `baseline_20260928_100315/`.

`comparacion.json` contiene todas las diferencias con fecha, columna, antes/después y máximos por columna numérica. Los máximos numéricos comparan pares no NULL; los cambios NULL→valor aparecen por separado en la lista de diferencias y son funcionalmente relevantes.

Ejemplos de máximos absolutos: Produccion_KOM_TMH y Dato_Mina_TMH = 57022.798; Vueltas_KOM = 157; KOM_TMH_Corregido y Chancado_TMH_Corregido_Total = 58438.11535698959. No representan efectos de límites nuevos: los límites continuaron siendo 380/265.

Se confirmó igualdad exacta después del ROLLBACK para:

- todas las filas/columnas del control V2, incluida Fecha_Calculo;
- todas las filas/columnas de la vista;
- toda la tabla de la cadena antigua.

## Estado y decisión necesaria

No se modificaron objetos SQL ni el dashboard. No se crearon vigencias, auditoría, procedimiento de registro ni valores provisionales. No se ejecutaron publicaciones ni los procedimientos de Reporte por Turno, Datos Conciliados o Balance.

La condición de aceptación A (recálculo idéntico al histórico guardado) ya falla antes de esta implementación. Conforme a la regla de seguridad original, se detiene el despliegue ante este supuesto importante no satisfecho.

Cambio mínimo recomendado del criterio de prueba: comparar el cálculo original y el parametrizado con seed 380/265 sobre las mismas entradas, usando un baseline recalculado reversible; exigir cero diferencias atribuibles a parametrización y preservar el histórico almacenado sin refrescarlo permanentemente. Documentar aparte las diferencias previas respecto de la materialización. Este cambio de referencia necesita confirmación del usuario porque sustituye su criterio 1:1 explícito.

No se recomienda sobrescribir ni reconstruir fuentes para forzar igualdad. Si se requiere igualdad estricta con el histórico almacenado, primero se necesita recuperar las entradas exactas utilizadas para materializarlo.

Pruebas de vigencias, seed, frontera, concurrencia y rollback de despliegue pendientes. No se creó un script de rollback de despliegue porque no existe todavía una migración aplicada. El script de validación ejecutado hace ROLLBACK en `finally`.
