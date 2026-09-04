# Runtime vs repositorio

## Archivo esperado

Ruta: `C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\reclamo\db.py`

SHA256: `47B80A9C162C48B982372CF63A9550D3877760834ECF4450665A28DEEE00E657`

Fecha modificacion: `2026-08-06 12:04:11.464 -04:00`

## Archivo resuelto por Python

Ruta local: `C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\reclamo\db.py`

SHA256 local: `47B80A9C162C48B982372CF63A9550D3877760834ECF4450665A28DEEE00E657`

Fecha modificacion local: `2026-08-06 12:04:11.464 -04:00`

Resultado de la prueba local: **[IGUALES]**.

Archivo del proceso que genero los logs SQL: **NO DETERMINADO EN PROCESO VIVO**, porque no existe un proceso Dash local y no se proporciono acceso al host/contenedor activo.

## recalcular esperado

```python
def recalcular(desde, hasta, dias_reproceso: int = 7) -> str:
    sql_mantener = text("""
        EXEC reclamo.sp_auto_mantener_secuencia
             @VentanaDias = 90,
             @Siguientes  = 5
    """)
    sql_sync = text("""
        EXEC reclamo.sp_sincronizar_desde_etl
             @FechaInicio = :desde, @FechaFin = :hasta,
             @SincronizarApilado = 0, @Confirmar = 1
    """)
    sql_cv25 = text("""
        EXEC reclamo.sp_cargar_cv25_horas
             @FechaInicio = :desde, @FechaFin = :hasta
    """)
    sql_calc = text("""
        EXEC reclamo.sp_calcular_reclamo_diario
             @FechaInicio = :desde, @FechaFin = :hasta,
             @DiasReproceso = :dias
    """)
    with get_engine().begin() as conn:
        conn.execute(sql_mantener)
        conn.execute(sql_sync, {"desde": desde, "hasta": hasta})
        # SELECT read-only de filas sincronizadas
        conn.execute(sql_cv25, {"desde": desde, "hasta": hasta})
        conn.execute(sql_calc, {"desde": desde, "hasta": hasta, "dias": dias_reproceso})
```

## recalcular resuelto

La introspeccion con el venv local devolvio exactamente la implementacion esperada anterior, incluyendo `conn.execute(sql_mantener)` como primera sentencia de la transaccion.

La version del proceso vivo no se pudo introspectar. Sin embargo, Git conserva una version cuya secuencia coincide con la evidencia SQL:

- `a9fd8da` (2026-08-05 13:18 -04): sync -> cargar_cv25 -> calcular, sin auto_mantener.
- `bd5568f` (2026-08-05 18:34 -04): agrega auto_mantener al principio.

## mantener_secuencia esperado

```python
def mantener_secuencia(ventana_dias: int = 90, siguientes: int = 5):
    sql = text("""
        EXEC reclamo.sp_auto_mantener_secuencia
             @VentanaDias = :ventana,
             @Siguientes = :siguientes
    """)
    with get_engine().begin() as conn:
        result = conn.execute(sql, {"ventana": ventana_dias,
                                    "siguientes": siguientes})
```

## mantener_secuencia resuelto

La introspeccion local devolvio exactamente la funcion esperada. Esta funcion ya existia con la llamada al SP en `fb2532f` (2026-07-31), antes de las revisiones historicas de `recalcular` que no contenian auto_mantener.

## Diferencia encontrada

La copia actual en disco y la resolucion del venv local son iguales; no hay duplicado ni shadowing local. Pero esa copia es incompatible con la traza SQL atribuida al boton Recalcular: si la transaccion actual hubiese completado sync y calcular, necesariamente habria ejecutado primero auto_mantener. La explicacion mas fuerte es un **desfase entre el artefacto/codigo cargado por el servidor activo y el checkout auditado**. La traza de Recalcular tiene la firma exacta de una revision anterior a `bd5568f`, especialmente `a9fd8da` si cargar_cv25 tambien aparece.

La pulsacion del boton Actualizar modulos no permite identificar una revision equivalente: todas las revisiones Git inspeccionadas que contienen ese boton llaman `db.mantener_secuencia()`. Su falta de ejecucion significa que esa pulsacion no alcanzo/completo ese callback, que el UI pertenece a otro artefacto no presente, o que faltan logs Python/remotos. No es posible elegir entre esas alternativas con la evidencia accesible.

## ¿Explica los logs SQL?

**Sí, para Recalcular; parcialmente para el conjunto de ambos botones.**

Justificacion: una version pre-`bd5568f` explica exactamente sync/calcular sin auto_mantener al recalcular. No explica por si sola la ausencia al pulsar Actualizar modulos, porque el callback historico ya llamaba mantener_secuencia. Esa segunda parte requiere metadata/logs del host activo.
