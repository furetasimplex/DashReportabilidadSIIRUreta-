# Factor de ajuste camiones — Fase 1

Ubicación: Monitoreo Correas Área Seca → Diagnóstico de Correas, inmediatamente después de la tendencia del totalizador. Reutiliza `pitum-fechas` y `pitum-actualizar`.

## Cambios

- `db.py`: agrega `FACTOR_CAMIONES_SQL` y `obtener_factor_camiones(fecha_inicio, fecha_fin)`. Valida fechas, orden del rango, conexión DEV y unicidad diaria; retorna DataFrame ordenado.
- `panel.py`: importa el módulo e inserta su layout. No modifica callbacks anteriores.
- `factor_camiones_panel.py` (nuevo): card, gráfico de tres series TMH, dos factores en eje secundario, referencia 1.0000 y detalle de todos los campos por día. Conserva NULL como `None`/«—». Solo deriva sumas y cargas corregidas por viaje.
- `test_factor_camiones.py` (nuevo): pruebas focalizadas de consulta, validación, valores materializados, NULL, selección y actualización del detalle, respuestas Dash y callbacks.

Los callbacks globales `@callback` se registran al importar el módulo desde `panel.py`, siguiendo la arquitectura existente:

1. `actualizar_factor`: entradas `pitum-fechas.start_date`, `pitum-fechas.end_date`, `pitum-actualizar.n_clicks`; salidas `pitum-factor-grafico.figure`, `pitum-factor-datos.data`, `pitum-factor-alerta.children`.
2. `actualizar_detalle`: entradas `pitum-factor-datos.data`, `pitum-factor-grafico.clickData`; salida `pitum-factor-detalle.children`. Un nuevo conjunto de datos selecciona su primer día.

## SQL final

```sql
SELECT Fecha, Apilado_TMH_Bruto_Original, Apilado_TMS_Bruto_Sin_Ajuste,
       Apilado_TMS_Neto_Sin_Ajuste, Chancado_TMH_Sin_Ajuste, Chancado_TMS_Sin_Ajuste,
       Produccion_KOM_TMH, Produccion_CAT_TMH, KOM_TMH_Corregido, CAT_TMH_Corregido,
       Vueltas_KOM, Vueltas_CAT,
       Carga_KOM_TMH_Viaje_Sin_Ajuste, Carga_CAT_TMH_Viaje_Sin_Ajuste,
       Factor_Ajuste_Calculado, Factor_Aplicacion_Reportes, Flag_Factor_Ajuste_Valido,
       Estado_Calculo, Regla_Aplicacion, SRR_TMS_Dia, Metodo, Fuente_Camiones, Fecha_Calculo
FROM inventar_SpcHidr.v_ajuste_camiones_emision_test
WHERE Fecha >= :fecha_inicio AND Fecha <= :fecha_fin
ORDER BY Fecha
```

Parámetros enlazados mediante SQLAlchemy; no interpolación de fechas. Los factores se seleccionan directamente, sin fórmulas Python ni sustitución de NULL.

## Validación ejecutada

- `venv\Scripts\python.exe -m unittest monitor_pi_tum.test_factor_camiones monitor_pi_tum.test_monitor`: 7 pruebas OK. Incluye importación del layout general, navegación, IDs únicos, endpoints de layout/dependencias de Dash, rango vacío, errores controlados, NULL y selección de fecha.
- `py_compile`: OK para main.py, layout.py y los cuatro módulos Python de esta integración.
- `git diff --check`: OK.
- Consulta real del 07 al 19 de septiembre de 2026: 13 filas, ninguna fecha duplicada. Factores calculado/aplicado coincidentes: 07 → 0.819735; 08 → 0.957532; 16 → 0.215205; 19 → 0.951849. Totales corregidos: 26220, 45220, 380 y 42180 TMH, respectivamente.

No se ejecutó una revisión visual en navegador ni se arrancó el servidor completo con sus procesos de inicio. La validación de UI es estructural y mediante callbacks/endpoints de Dash.

## Alcance y dependencias

Solo SELECT a la vista indicada. Sin escrituras, refresh, mantenedores, procedimientos, cambios de objetos SQL, migraciones ni cambios de metodología. No se modificaron Reporte por Turno, Datos Conciliados, balance ni publicación.

Se conserva la restricción DEV existente del monitor (`SQLSERVER_DB` y base del engine deben ser `inventar_SpcHidr`). Requiere conectividad ODBC y permiso SELECT sobre la vista y sus columnas. La primera conexión falló dentro del sandbox; la consulta autorizada fuera de él funcionó. No se cambiaron credenciales ni configuración.

Los prototipos indicados no estaban en el workspace. Se utilizó la arquitectura real y la definición SQL de referencia disponible, corroborada con la consulta real. Los cambios preexistentes en `reclamo/db.py`, `release/` y las evidencias de calendario no forman parte de esta entrega.
