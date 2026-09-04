# Callbacks de Control de Reclamo

| Boton | Archivo | Callback | Funcion llamada |
| --- | --- | --- | --- |
| `btn-recalcular` | `reclamo/panel.py` | `cb_recalcular` | `db.recalcular(desde, hasta)` |
| `btn-automatizacion` | `reclamo/panel.py` | `cb_automatizacion` | `db.mantener_secuencia()` |

## Recalcular

```text
Input("btn-recalcular", "n_clicks")
  -> cb_recalcular(n, desde, hasta)
  -> db.recalcular(desde, hasta)
```

En el archivo actual, `recalcular` ejecuta en una transaccion y en este orden:

1. `reclamo.sp_auto_mantener_secuencia`
2. `reclamo.sp_sincronizar_desde_etl`
3. SELECT read-only del ultimo resumen de sincronizacion
4. `reclamo.sp_cargar_cv25_horas`
5. `reclamo.sp_calcular_reclamo_diario`

## Actualizar modulos

```text
Input("btn-automatizacion", "n_clicks")
  -> cb_automatizacion(n)
  -> db.mantener_secuencia()
  -> reclamo.sp_auto_mantener_secuencia
```

## Duplicados

No se encontraron IDs ni callbacks duplicados en el repositorio. La misma asociacion de callbacks ya estaba presente en los commits historicos `fb2532f`, `6cd9288` y `bd5568f`.

## Registro

`main.py` importa `layout.py`; `layout.py` importa `reclamo.panel`; ese import registra los decoradores globales `@callback`. Por tanto, con el entrypoint declarado, el archivo actual sí se importa durante el arranque.
