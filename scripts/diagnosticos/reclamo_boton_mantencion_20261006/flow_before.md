# Flujo LIVE antes de v2

`db.recalcular`: mantener → sync → mantener → sync → CV25/horas → cálculo.

`sp_auto_mantener_secuencia`: backfill de filas de secuencia con `sp_definir_secuencia` → cierre/avance con `sp_auto_cerrar_y_avanzar_secuencia` → congelamiento, línea base y apertura con `sp_auto_congelar_modulos_nuevos` → relleno de cupo huérfano.

`sp_auto_congelar_modulos_nuevos`: detecta actividad en ETL, congela con `sp_congelar_modulo` solo si hay base válida, secuencia con `sp_definir_secuencia`, establece línea base y abre hasta dos módulos con actividad real. No cierra.

`sp_sincronizar_desde_etl`: inserta/actualiza topografía de módulos congelados y registra omisiones; también sincroniza camiones. No define fechas de secuencia.

`sp_congelar_modulo`: fija la base administrativa de `modulo_congelado`. `sp_definir_secuencia`: agrega filas `PENDIENTE` sin reordenar históricos. La fecha de congelamiento se mantiene separada de `fecha_apertura` y `fecha_cierre`.

El primer mantenimiento podía cerrar con `topografia_avance` anterior al sync del rango. La segunda pasada no vuelve a calcular fechas de filas ya `CERRADO`.
