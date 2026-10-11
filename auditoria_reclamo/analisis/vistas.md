# Catálogo actual de vistas `reclamo.*`

Fuente: `inventar_SpcHidr_PROD` @ `VPS-6191873-X` (`66.97.44.70`). Extraído 2026-10-07 con `scripts/dump_reclamo_views.py`. Definición completa de cada vista en `sql_definitions/reclamo.v_*.sql`. Inventario, columnas y dependencias en `16_vistas_reclamo.csv`, `16b_columnas_vistas.csv` y `16c_dependencias_vistas.csv`.

Los CSV `01`–`15` y el resto de `sql_definitions/` (SP, funciones) siguen siendo el snapshot de 2026-09-02 sobre DEV `inventar_SpcHidr` @ `VPS-5347319-X`. No mezclar esas fechas con este catálogo.

## Cadena de cálculo (PROD)

```text
v_modulo_base
v_topografia_resuelta
v_camiones_acumulado
v_cv25_diario → v_preliminar_cv25 → v_preliminar_cv25_con_acumulado
v_ajustes_aplicables
        │
        ▼
v_reclamo_diario
        │
        ├─ v_cuadratura_modulo
        ├─ v_diferencia_cv25          ← gráfico del dashboard
        ├─ v_rendimiento_rotopala
        ├─ v_reclamo_para_conciliados ← contrato de Publicar
        └─ sp_calcular_reclamo_diario → calculo_diario
```

`v_reclamo_diario` ya no lee `v_preliminar_cv25` directo: une topografía + preliminar vía `v_preliminar_cv25_con_acumulado` (`m3_acum_ultima_topografia + SUM(m3_preliminar_dia)`), para que el acumulado no retroceda entre mediciones.

Las cinco `*_contingencia_test` son un espejo PI-TUM (septiembre 2026). No las lee `reclamo/db.py`.

## Inventario

| Vista | Uso | Última modificación | vs snapshot 2026-09-02 |
|---|---|---|---|
| `v_modulo_base` | pantalla | 2026-07-30 | igual |
| `v_topografia_resuelta` | pantalla | 2026-07-30 | igual |
| `v_camiones_acumulado` | pantalla | 2026-07-30 | igual |
| `v_ajustes_aplicables` | cadena | 2026-07-30 | igual |
| `v_reclamo_para_conciliados` | pantalla | 2026-08-01 | igual |
| `v_rendimiento_rotopala` | pantalla | 2026-07-30 | igual |
| `v_preliminar_cv25` | cadena | 2026-09-07 | distinta |
| `v_preliminar_cv25_con_acumulado` | cadena | 2026-09-04 | no existía en la auditoría |
| `v_reclamo_diario` | pantalla | 2026-09-04 | distinta (pasa por con_acumulado) |
| `v_cv25_diario` | cadena | 2026-10-06 | distinta |
| `v_diferencia_cv25` | pantalla | 2026-10-06 | distinta |
| `v_cuadratura_modulo` | pantalla | 2026-10-06 | distinta |
| `v_cv25_diario_contingencia_test` | test | 2026-09-19 | no existía |
| `v_preliminar_cv25_contingencia_test` | test | 2026-09-19 | no existía |
| `v_preliminar_cv25_con_acumulado_contingencia_test` | test | 2026-09-19 | no existía |
| `v_reclamo_diario_contingencia_test` | test | 2026-09-19 | no existía |
| `v_diferencia_cv25_contingencia_test` | test | 2026-09-19 | no existía |

**pantalla** = `reclamo/db.py` la consulta. **cadena** = solo la usan otras vistas o el SP de recálculo. `avance_diario` lee la tabla `calculo_diario`, no la vista.

## Cómo refrescar

```text
python scripts/dump_reclamo_views.py
```

Read-only. Reescribe `sql_definitions/reclamo.v_*.sql` y los CSV `16*`. Contrae contra la base del `.env` actual (`SQLSERVER_DB`).
