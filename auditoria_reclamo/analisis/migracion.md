# Qué copiar para mover Reclamo a otra base

Fuente: `inventar_SpcHidr_PROD` @ `VPS-6191873-X`, 2026-10-07. Grafo: `scripts/dump_reclamo_object_graph.py` → CSV `17` / `17b`–`17e`.

Hay **dos capas**. El esquema `reclamo` es autónomo salvo 8 tablas + 2 vistas de `inventar_SpcHidr`. Publicar a `Datos_conciliados_of` arrastra el resto de la planta: no hace falta para que el dashboard calcule.

Únicos consumidores externos de `reclamo.*` en el catálogo: `sp_mantiene_datos_conciliados_emision_test` y `sp_mantiene_datos_conciliados_of` (ambos leen `v_reclamo_para_conciliados`).

## Paquete A — núcleo (copiar entero)

Esquema `reclamo`: 14 tablas + 1 función + 14 SP + 12 vistas de cálculo.

### Tablas (schema + datos)

| Tabla | Rol |
|---|---|
| `configuracion` | corte, tolerancia; la lee `fn_fecha_corte` |
| `rotopala` | catálogo R1/R2; FK padre de horas y secuencia |
| `topologia_pad` | rangos de módulo por PAD |
| `modulo_congelado` | foto de módulo al abrir |
| `secuencia_rotopala` | orden abierto/cerrado |
| `topografia_avance` | topografía sincronizada |
| `camiones_reclamo` | camiones oficiales |
| `cv25_diario` | totalizador diario |
| `rotopala_horas_turno` | horas por turno |
| `ajuste_manual` | ajustes aprobados |
| `calculo_diario` | materialización del recálculo |
| `log_ejecucion` | bitácora de SP |
| `log_sincronizacion` | bitácora ETL / disponible |
| `log_automatizacion` | bitácora secuencia |

FK internas (únicas del esquema): `secuencia_rotopala.rotopala_id` y `rotopala_horas_turno.rotopala_id` → `rotopala`.

### Código (solo definición)

Función: `fn_fecha_corte`.

SP: `sp_congelar_modulo`, `sp_definir_secuencia`, `sp_establecer_linea_base`, `sp_auto_congelar_modulos_nuevos`, `sp_auto_cerrar_y_avanzar_secuencia`, `sp_auto_mantener_secuencia`, `sp_sincronizar_desde_etl`, `sp_cargar_cv25_horas`, `sp_calcular_reclamo_diario`, `sp_registrar_ajuste_manual`, `sp_aprobar_ajuste_manual`, `sp_validar_reglas_negocio`, `sp_actualizar_disponible_rotopala`, `sp_insertar_disponible_rotopala`.

Vistas, en orden de creación:

1. `v_modulo_base` → `v_topografia_resuelta` / `v_camiones_acumulado` / `v_cv25_diario` / `v_ajustes_aplicables`
2. `v_preliminar_cv25` → `v_preliminar_cv25_con_acumulado`
3. `v_reclamo_diario`
4. `v_cuadratura_modulo` / `v_diferencia_cv25` / `v_rendimiento_rotopala` / `v_reclamo_para_conciliados`

## Paquete B — fuentes ETL (obligatorio para que corra)

Objetos `inventar_SpcHidr` que **el esquema `reclamo` o `reclamo/db.py` leen**. Sin esto el dashboard y los SP de sync/recalcular fallan. Copiar tablas con datos, o dejar synonym/vista hacia la base origen.

| Objeto | Tipo | Quién lo usa |
|---|---|---|
| `disponible_rotopalas` | tabla | congelar, insertar/actualizar disponible, `db.py` |
| `modulo` | tabla | `v_modulo_base`, congelar, secuencia, `db.py` |
| `parcela` | tabla | `db.py` (join con `modulo`); FK origen → `pad` |
| `control_reclamo_diario` | tabla | sync ETL, línea base, auto-secuencia, `db.py` |
| `control_reclamo_sulfuro_camiones_thm_diario` | tabla | sync ETL, línea base, auto-congelar, `db.py` |
| `control_medicion_topografia_diaria` | tabla | `sp_sincronizar_desde_etl` |
| `modulos_turnos` | tabla | `sp_congelar_modulo` |
| `datos_filtrados` | tabla | `sp_cargar_cv25_horas` (horas) |
| `vista_resumen_datos_filtrados` | vista | `sp_cargar_cv25_horas` (CV25); solo apunta a `datos_filtrados` |

`modulo` / `parcela` tienen FK hacia `pad` y `campaña` en origen. Si se copian las tablas hay que llevar esas FK o crearlas sin constraint.

## Paquete C — contingencia (opcional)

Cinco vistas `reclamo.*_contingencia_test` más la cadena PI-TUM (`v_contingencia_*`, `contingencia_pi_accion_test`, `tot_TM`, `informe_tum_totalizadores_turno`). **La pantalla no las lee.**

Excepción: el catálogo vivo de `sp_cargar_cv25_horas` también declara dependencia a `v_contingencia_cv025_diario_resuelto`. Esa vista cuelga de `vista_resumen_datos_filtrados` y de `v_contingencia_totalizador_resuelto_turno`. Si el SP en destino se crea desde el snapshot 2026-09-02, no hace falta; si se scriptea el SP **actual** de PROD, hay que llevar esa vista o el CREATE falla.

## Paquete D — publicación (opcional y caro)

Solo si en la base destino también se va a **Publicar**. El botón llama a `inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test`, que escribe `Datos_conciliados_of` y arrastra cache de reporte, factor camiones, planes, leyes, apilado, `mov_cam`, `hidro.imp_csv`, etc. (CSV `17_objetos_cierre.csv` paquete E).

Para un recálculo/dashboard autónomo **no copiar D ni E**.

## Orden práctico

1. Schema `reclamo` + paquete B (tablas fuente + `vista_resumen_datos_filtrados`).
2. Función, tablas `reclamo`, vistas en el orden de arriba, SP.
3. Probar sync / cargar CV25 / calcular. No hace falta Publicar.
4. Contingencia y publicación, solo si se necesitan.

Refresco: `python scripts/dump_reclamo_object_graph.py`.
