# Factor camiones V2: vueltas y nominales temporales — DEV

Implementado y persistido el 30-09-2026 exclusivamente en DEV. Primero pasó la
prueba integral con ROLLBACK; después se confirmó la migración con COMMIT, se tomó
un snapshot fresco y se reprocesó 01-07–27-09-2026 mediante la orquestación existente.
El segundo COMMIT se verificó desde otra conexión. No commit/push de Git.

## Regla

Se filtran CH01, fase distinta de SRR y KOM/CAT. La cobertura por fuente y día exige
registros, ningún N_BREAK NULL/no numérico/negativo y suma >0. NULL real se
clasifica como NBREAK_NULL; vacío, espacios y texto no convertible se clasifican
como NBREAK_NO_NUMERICO. Cero es permitido, pero solo ceros no da cobertura.

MOV_CAM tiene prioridad; PowerBI reemplaza el día completo si MOV_CAM no es válido.
No se completan flotas entre fuentes. La flota ausente en una fuente válida aporta
cero. Sin fuente válida se conserva el factor no evaluable y se registra
SIN_DATOS_CAMIONES. Los motivos son OK, SIN_REGISTROS, SOLO_CEROS, NBREAK_NULL,
NBREAK_NO_NUMERICO y NBREAK_NEGATIVO. Si coexisten defectos, la precedencia es
NULL, no numérico, negativo; cualquiera invalida el día.
No hay arrastre ni deduplicación adicional a los filtros.

Producción = vueltas × nominal vigente. Los tonelajes externos no participan.
Se conservan distribución, cargas efectivas, límites y factor. Se exigen cuatro
configuraciones únicas por fecha; falta/multiplicidad lanza 51020, sin defaults.
Nominales y evaluación de fuentes quedan materializados; el override no cambia.

## Paquete SQL

Desplegar como unidad transaccional, nunca cambiar el result set antes de preparar
su consumidor INSERT EXEC. El runner valida identidad DEV, definiciones vivas y
toma primero el lock global de reportabilidad y después el de parámetros.

| Archivo | Función |
|---|---|
| 01_esquema.sql | CHECK de dos categorías, nominales y seeds 357/236 desde 01-07-2026 |
| 01b_trazabilidad_fuentes.sql | Estados de MOV_CAM y PowerBI |
| 02_administrador_generico.sql | Un algoritmo temporal por categoría |
| 03_wrapper_limites.sql | Compatibilidad del administrador anterior |
| 04_resolver_vueltas.sql | Función común de selección diaria |
| 05_vueltas_diarias.sql | Agregación de las dos fuentes |
| 06_sp_factor_ajuste_camiones_test.sql | Cálculo principal y contrato extendido |
| 07_sp_factor_ajuste_camiones_standalone_test.sql | Misma regla; preserva entrada SRR standalone |
| 08_sp_mantiene_factor_ajuste_camiones_v2_test.sql | Temporal y MERGE principal |
| 09_sp_mantiene_factor_ajuste_camiones_v2_standalone_test.sql | Temporal y MERGE alternativo |
| 10_v_ajuste_camiones_emision_test.sql | Exposición de valores materializados |

No hay tabla paralela. Se conservan PK, UQ, índice filtrado, trigger, [desde,hasta),
auditoría y locks. Registrar no calcula, reprocesa ni publica.

## Backup y ejecución

`backup/` contiene siete definiciones vivas, tres archivos Python originales y
`manifest.json` con SHA-256. Preserva trabajo preexistente; no usar git restore.

`scripts/factor_camiones_nominales_dev.py`: capture obtiene respaldo SELECT sin
sobrescribirlo; prepare genera SQL desde ese respaldo, no desde migraciones antiguas.

`scripts/validate_factor_nominales_dev.py`:

- trial: migración, pruebas y cadena completa con ROLLBACK verificado.
- rejections: rechazos en transacciones independientes revertidas.
- concurrency: dos sesiones, espera APPLICATION y ambos ROLLBACK.
- deploy: exige evidencias; COMMIT de migración y COMMIT de reproceso.
- ui-smoke: callbacks con lecturas DEV; revisa modal sin registrar.
- rollback-check: prueba la reversión y revierte esa prueba; mantiene activo el
  despliegue persistido. Ejecutado correctamente.
- rollback: revierte objetos/configuración, restaura V2/DC/cache desde snapshot
  y restaura los tres archivos Python. No ejecutado definitivamente.

`rollback_dev.sql` restaura CHECK, SPs, vista y estructura V2; elimina los seeds
nominales y objetos nuevos. `rollback_preparacion.sql` es un componente intermedio,
no el rollback integral a ejecutar. Usar el runner rollback para restaurar datos:
ejecutar solo DDL no restaura los resultados.

El rollback aborta ante historia nominal o cambios SQL/datos/Python posteriores;
no destruye modificaciones de otros usuarios. Las pruebas con ROLLBACK pueden
dejar saltos normales de identity. Los timestamps/bitácoras auxiliares de la
orquestación no se rebobinan por el rollback de V2/DC/cache; no se cambiaron sus
reglas ni fuentes. La restitución SQL fue probada reversiblemente.

## Backend/UI

db.py tiene núcleo genérico con whitelist y wrappers compatibles. El panel
existente ofrece Límite máximo/Carga nominal, vigencias, historial, futuros,
motivo/usuario y confirmación retroactiva. El detalle muestra nominales utilizados,
fuente y estados. No se duplicó el panel ni se añadieron columnas Excel.

Se conserva la revalidación optimista por valor y la serialización SQL. No se
introdujo compare-and-swap de versión; permanece la limitación preexistente ante
cambios simultáneos con igual valor. El rango potencial del administrador sigue
usando MAX(Fecha), sin recortarlo por futuras vigencias.

## Evidencia

`report_export/exports/validacion_factor_nominales_20260930/`: INFORME.md,
comparacion.csv, fuentes_vueltas.csv, casos_obligatorios.json, resultado_final.json,
rollback_probado.json y snapshots antes/después.

Factor/Balance/DC/Generador: 89 fechas. RTO/Reconstitución: 178 filas.
16/09: calculado≈0,21963019549669; aplicado=1, FORZADO_1.
Las entradas de apilado, humedad, sal, inventario y SRR permanecieron iguales.


## Correccion textual N_BREAK persistida

El 30/09/2026 se corrigieron solo el resolvedor y la vista diaria: NULL real
se conserva como NBREAK_NULL; vacios, espacios y conversiones fallidas son
NBREAK_NO_NUMERICO. Se completaron ROLLBACK, COMMIT y verificacion post-deploy:
17 casos SQL y 89 fechas exactamente iguales, sin reprocesar datos.
Evidencia: `report_export/exports/validacion_nbreak_textual_20260930/INFORME.md`.
El rollback global anterior se bloquea ante las nuevas definiciones; restaurar
primero la capa textual si se requiere utilizarlo.
