# Detalle real de módulos — integración DEV

Al seleccionar una parcela, `open_detail` consulta sus módulos y abre el drawer. La carga diaria principal sigue ejecutando una consulta a TEST V2 y mantiene su Store de 60 parcelas. El filtro PAD sigue siendo local. Los módulos no se incorporan al Store principal ni cambian colores, estados, leyenda o geometría.

## Consulta exacta

```sql
SELECT
    fecha, pad_id, nombre_pad, parcela_id, numero_parcela,
    campana_id, numero_campana, modulo_id, nombre_modulo,
    secuencia_carguio, secuencia_retiro, estado_modulo,
    fecha_ini_carguio, fecha_fin_carguio, fecha_ini_reclamo, fecha_fin_reclamo
FROM inventar_SpcHidr.fn_estado_operacional_modulo_diario_test(
    :fecha, :pad_id, :parcela_id
)
ORDER BY COALESCE(secuencia_carguio, 999999), nombre_modulo
```

Helper `map_db.fetch_modulos_parcela`, SQLAlchemy `text`, fecha y claves enlazadas como parámetros, conexión `_connection()` existente. Sin columnas hidráulicas por módulo.

## Presentación

Sección «MÓDULOS CONSIDERADOS · N» con nombre `M` + `nombre_modulo`, nunca `modulo_id`. Estados traducidos reutilizando `map_states.ESTADOS`. No hay inferencias ni nuevas reglas. El número del encabezado proviene de `modulos_total`.

La composición agregada se omite cuando el detalle completo la sustituye; se conserva como respaldo si el detalle falla, está vacío o no coincide en cantidad. `composicion_modulos` en Store no cambia.

Error: «No fue posible cargar el detalle de módulos.» El drawer y mapa siguen operativos. Cero filas: «Sin detalle de módulos disponible.» Cantidad distinta de `modulos_total`: mensaje de inconsistencia con conteos; no se fabrican filas.

## Validación

- `python -m pytest lixiviacion -q`: **41 PASS**, incluidos todos los tests previos. Helper parametrizado, nombres reales, traducciones, conteos, error, vacío, consulta solo al clic, carga principal única y filtro PAD local.
- `python -m lixiviacion.smoke_modules_dev`: **PASS DEV**, 60 parcelas y módulos reales de los tres casos, conteo igual a `modulos_total`.
- OX P29: M57/M58 → Espera de reclamo.
- OX P17: M33 → Conformado / espera de riego; M34 → Apilado.
- SULF P1: M1–M4 → Reclamado; M5 → Reclamo. Los IDs SQL son 65–69, pero los nombres visibles son 1–5.
- `python -m lixiviacion.smoke_map_dev`: **FAIL canónico conocido**, esperado RIEGO 19/18, instalado RIEGO_DRENAJE 19/18. No se modificó el smoke ni la función para forzar PASS. La promoción continúa pendiente y no se retomó.
- Evidencia de módulos: `SMOKE_MODULES_DEV.json`. El archivo antiguo `SMOKE_MAP_DEV.json` conserva su ejecución histórica, no representa un PASS nuevo.

`python -m lixiviacion.visual_review`: **PASS**, 13 comprobaciones, sin errores de página ni callbacks y sin overflow horizontal del documento. Capturas de OX P29, OX P17 y SULF P1 revisadas: nombres y estados correctos, tabla legible y sin composición agregada redundante. Evidencia: `visual_modulos/review.json` y capturas en esa carpeta. El servidor local usa sesión de pruebas en memoria y se detuvo al terminar.

`git diff --check`: **PASS**; únicamente advertencia de conversión LF/CRLF en `layout.py`, ajeno a este ajuste.

## Alcance

Modificados: `map_db.py` (helper nuevo; carga principal intacta), `map_panel.py` (detalle y consulta al clic), `visual_review.py` (casos de módulos y capturas).

Creados: `test_modules.py`, `smoke_modules_dev.py`, `SMOKE_MODULES_DEV.json`, este informe y `visual_modulos/`.

Sin cambios en fase_visual, paleta/CSS, geometría, leyenda, Diagnóstico, Recomendador ni objetos SQL. Sin DDL, escrituras SQL, PROD, commit o push. Se mantienen ambas funciones TEST; no se realiza promoción.
