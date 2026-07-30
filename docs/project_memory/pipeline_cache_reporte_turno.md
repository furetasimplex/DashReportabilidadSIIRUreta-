# Pipeline Reporte por Turno / Diario + Cache — dependencias y refresco

Cómo se encadenan `sp_reporte_turno_test`, `reporte_turno_cache`,
`fn_generador_reporte_diario` y `sp_generador_reporte_diario`, y **cómo
mantener el cache al día cuando cambian sus fuentes**.

> BD: SQL Server `inventar_SpcHidr`. Investigado 2026-07-22.

---

## 1. La cadena en capas

```
FUENTES (vistas + tablas de ingesta)
        │
        ▼
sp_reporte_turno_test  ← CÁLCULO PESADO (15 bloques, temporales #, humedad/sal/leyes/arrastre)
        │  produce: 1 fila por Fecha+Turno (A/B)
        ▼
sp_actualizar_reporte_turno_cache  ← DELETE rango + INSERT ... EXEC sp_reporte_turno_test
        │
        ▼
reporte_turno_cache   ← TABLA MATERIALIZADA (persistente, lectura barata)
        │
        ├──► fn_generador_reporte_diario (TVF)  ← lee cache + plan_semanal + plan_mensual
        │          │  consolida Turno A+B → 1 fila por Día (ponderado por Apilado_TMS_Real)
        │          ▼
        │    sp_generador_reporte_diario  ← wrapper: SELECT * FROM fn_... ORDER BY Fecha
        │
        └──► (lectura directa) fetch_reporte_turno_cache  en report_export.py
```

**Idea clave:** `sp_reporte_turno_test` es caro. El cache lo materializa una vez
por rango de fechas. Todo lo aguas abajo (reporte diario, lecturas de la app)
consume el cache barato. Por eso, **si las fuentes cambian y el cache no se
refresca, el reporte diario queda desactualizado silenciosamente.**

---

## 2. Los cuatro objetos

| Objeto | Tipo | Rol | En repo |
|---|---|---|---|
| `sp_reporte_turno_test` | SP | Cálculo pesado turno A/B (bloques 1–15) | ✅ `sp_reporte_turno_test.sql` |
| `sp_actualizar_reporte_turno_cache` | SP | Refresca el cache de un rango: `DELETE` + `INSERT..EXEC` | ✅ `sp_actualizar_reporte_turno_cache.sql` |
| `reporte_turno_cache` | Tabla | Resultado materializado de `sp_reporte_turno_test` | (tabla, sin DDL en repo) |
| `fn_generador_reporte_diario` | TVF inline | Turno→Día ponderado + planes | ✅ `db_functions/fn_generador_reporte_diario.sql` |
| `sp_generador_reporte_diario` | SP | Interfaz de consulta sobre la TVF | ✅ `sp_generador_reporte_diario.sql` |

Contrato de fechas: **fin exclusiva** (`Fecha >= @inicio AND Fecha < @fin`) en
`sp_reporte_turno_test`, `sp_actualizar_reporte_turno_cache`,
`fn_generador_reporte_diario` y `sp_generador_reporte_diario`.

---

## 3. Dependencias que ensucian el cache (upstream de `sp_reporte_turno_test`)

Cualquier cambio en estos objetos, para un rango de fechas, deja **stale** el
cache de ese rango:

| Bloque SP | Objeto fuente | Aporta |
|---|---|---|
| 1 | `v_datos_apilado_tmh_v2` | TMH CV-008/CV-108 por turno |
| 2 | `Informe_TM_lab` | Humedad laboratorio por torre/turno |
| 3 | `v_representatividad_diaria_calculada` | Representatividad física (gate ≥0.75) |
| 5 | `humedad_inicial_tm_periodo` | Semilla humedad inicio periodo |
| 7 | `factor_ajuste_camiones` | Factor de ajuste TMH |
| 8 | `v_sal_ajustada` | Descuento de sal |
| 10 | `v_leyes_resueltas_data_tm_reporte_test` | Leyes químicas base + arrastre |
| 14 | `v_reporte_turno_campania_modulo_test` | Campaña/Material/Módulo/Avance |
| 14 | `plan_mensual_reporte_turno` | Plan mensual |
| 14 | `plan_semanal_reporte_turno` | Plan/Programa semanal |
| 15 | `v_apilado_proporcion_final_reporte_test` | Distribución STOCK/MINA/SRR |
| final | `v_reporte_turno_fuentes_info_test` | Fuente info química/física |

**Tablas físicas escritas por la app** (tabs de importación → gatillos de refresco):
`Informe_TM_lab` (pesos/humedad torre), `NIR`, leyes, `plan_mensual_reporte_turno`,
`plan_semanal_reporte_turno`, `factor_ajuste_camiones`, `humedad_inicial_tm_periodo`,
`reclamos_tonelaje`, `Recuperaciones_pad`, `mov_cam`, `datos_filtrados`.
(Ver `tabs/tab_import*.py`, `tabs/tab_importar_*.py`.)

> Nota: `fn_generador_reporte_diario` además lee **directo** `plan_semanal_reporte_turno`
> y `plan_mensual_reporte_turno`. Los planes se leen tanto vía cache como directo,
> así que un cambio de plan impacta el diario aunque no toques el cache — pero el
> `Apilado_TMS_Real` ponderado sí sale del cache y sí requiere refresco.

---

## 4. Consumo desde Python (`report_export/report_export.py`)

| Función | Ejecuta |
|---|---|
| `fetch_reporte_turno_report(ini, fin)` | `sp_reporte_turno_test` **en vivo** (sin cache, lento) |
| `fetch_reporte_turno_cache(ini, fin)` | `SELECT` directo sobre `reporte_turno_cache` (rápido) |
| `fetch_generador_reporte_diario(ini, fin)` | `sp_generador_reporte_diario` (lee cache) |

> Hoy **no existe** una función Python que llame `sp_actualizar_reporte_turno_cache`.
> El refresco es manual/externo. Ese es el hueco a cerrar (sección 5).

---

## 5. Idea: cómo mantener el cache al día

Unidad de refresco = **rango de fechas**. Comando único:

```sql
EXEC inventar_SpcHidr.sp_actualizar_reporte_turno_cache
     @fecha_inicio = '2026-07-01',
     @fecha_fin    = '2026-08-01';   -- fin exclusiva
```

Opciones, de más simple (recomendada) a más pesada:

1. **Refresco tras cada importación (recomendado, ponytail).**
   En cada tab de importación, después del `to_sql`/INSERT exitoso, calcular
   `min(Fecha)`…`max(Fecha)+1 día` de lo cargado y llamar
   `sp_actualizar_reporte_turno_cache`. Una función Python nueva
   (`refrescar_cache_reporte_turno(ini, fin)`) en `report_export.py` y una
   llamada en cada callback de import. Barato, correcto, sin infraestructura.

2. **Refresco perezoso al leer.** Antes de servir el diario, comparar un
   watermark (`MAX(fecha_modificacion)` de las fuentes) contra el del cache y
   refrescar solo si está atrás. Requiere columnas de auditoría que hoy no
   existen en todas las fuentes → más trabajo.

3. **Job programado (SQL Agent / cron).** Refrescar una ventana móvil (p.ej.
   últimos 45 días) cada noche. Simple pero con latencia: el diario del día
   puede quedar viejo hasta el próximo job.

**Recomendación:** opción 1 como mecanismo principal (frescura inmediata donde
importa), opción 3 como red de seguridad nocturna sobre ventana móvil.

### Boceto opción 1 (aún no implementado)

```python
# report_export/report_export.py
def refrescar_cache_reporte_turno(fecha_inicio: date, fecha_fin_exclusiva: date) -> None:
    """Rematerializa reporte_turno_cache para [inicio, fin). fin exclusiva."""
    sql = _sa_text("""
        EXEC inventar_SpcHidr.sp_actualizar_reporte_turno_cache
            @fecha_inicio = :ini, @fecha_fin = :fin
    """)
    with _get_engine().begin() as conn:
        conn.execute(sql, {"ini": fecha_inicio, "fin": fecha_fin_exclusiva})
```

**Rango de refresco decidido:** desde la **fecha mínima cargada hasta hoy+1**
(fin exclusiva). Motivo: el SP arrastra el último valor válido hacia adelante
(leyes/humedad/malla), así que refrescar solo el rango importado dejaría días
posteriores con arrastre viejo. Se acepta el mayor costo por refresco a cambio
de correctitud.

```python
from datetime import date, timedelta
ini = df_cargado["Fecha"].min().date()   # fecha mínima efectivamente importada
fin = date.today() + timedelta(days=1)    # fin exclusiva
refrescar_cache_reporte_turno(ini, fin)
```

> Estado: **solo documentado**, sin implementar (decisión 2026-07-22). El boceto
> de arriba es la guía para cuando se enganche en los tabs de importación.
