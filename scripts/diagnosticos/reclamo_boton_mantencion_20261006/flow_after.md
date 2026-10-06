# Flujo v2 de reproceso

1. Preparación: `sp_auto_congelar_modulos_nuevos @SoloPreparar=1` congela, secuencia y establece línea base; omite la apertura. El parámetro predeterminado `0` conserva el comportamiento de las llamadas existentes.
2. Sync: `sp_sincronizar_desde_etl` incorpora la evidencia del rango para módulos congelados.
3. Transiciones: `sp_auto_mantener_secuencia` ejecuta cierre/avance y apertura con topografía ya sincronizada. Sus reglas siguen en SQL.
4. Sync de seguridad: incorpora módulos habilitados en la fase anterior.
5. `sp_cargar_cv25_horas`.
6. `sp_calcular_reclamo_diario`.

La corrección de fechas históricas de 76–79 se aplica aparte una sola vez a partir de topografía LIVE `VIGENTE`; no cambia estados. Las siguientes ejecuciones de `recalcular` deben preservar esas fechas. El SP de apertura usa ahora `@CampAbrir`, `@PadAbrir` y `@ModAbrir` al calcular la primera evidencia del módulo elegido, en vez de variables retenidas por el cursor de congelamiento.
