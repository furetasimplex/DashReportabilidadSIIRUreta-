# Memoria del proyecto — DashReportabilidadSIIR

Contexto operativo para agentes/desarrolladores que entran frío al repo.
Lo que el código **no** dice solo: qué está vivo, qué está muerto, qué
dispara escrituras en producción y dónde están las trampas.

> Investigado: 2026-08-03 · Actualizado: 2026-08-05 (commit `62807ce`)
> Verificado corriendo: `python -m pytest report_export/tests -q` → **92 passed,
> 1 failed** (17 s). El fallo es previo y ajeno a Representatividad, ver §10.10.

---

## 1. Qué es

Dashboard **Dash/Flask** (SIIR — Sistema Integrado de Información y
Reconciliación) para hidrometalurgia de **BHP Spence**, desarrollado por
Simplex Ingeniería. Su trabajo real: leer SQL Server, disparar stored
procedures de cálculo, y **emitir reportes oficiales en XLSX/PDF** con
formato institucional BHP.

No es una app de visualización: es una **fábrica de reportes con snapshot
versionado**. El grueso del código es armado de Excel celda por celda.

- Entrada dev: `main.py` (`app.run(debug=True, port=$PORT|8065)`).
- Entrada prod: `wsgi.py` → `gunicorn -w 2 wsgi:application` (Dockerfile, `PORT|10000`).
- BD: **SQL Server**, base `inventar_SpcHidr` (+ esquema `reclamo`).

---

## 2. Mapa de lo que está vivo

```
main.py
 ├─ auth.py                     Blueprint /auth (login contra tabla Django)
 ├─ db_connection.py            get_engine() SQLAlchemy + get_connection() pyodbc
 ├─ report_export/callbacks/reportabilidad_cb.py → setup_download_route(server)
 └─ layout.py                   shell SIIR (sidebar + header + footer)
      ├─ tabs/tab_report.py  (12 líneas) → report_export/layouts/reportabilidad_page.py
      │      └─ import report_export.callbacks.reportabilidad_cb   ← 8.113 líneas, el corazón
      │             └─ report_export/report_export.py              ← 3.763 líneas, capa de datos
      │                    ├─ export_to_excel.py   plantilla Datos Conciliados
      │                    ├─ pdf_generator.py     PDF reportlab (conciliados/turno)
      │                    ├─ pdf_torres.py        PDF representatividad (reportlab)
      │                    └─ xlsx_to_pdf.py       ruta legacy LibreOffice
      └─ reclamo/panel.py  (1.555 líneas) → reclamo/db.py (503, todo el SQL)
```

**Solo hay dos secciones en la UI**: `Reportabilidad` y `Administración de
Reclamo` (`layout.py:151` `toggle_subtabs`).

### ⚠️ `ARCHITECTURE.md` de la raíz está obsoleto
Describe 5 secciones y `tabs/tab1..tab6`, `tab_ripios`, `tab_import_*`,
`tab_recon_*`. Nada de eso está montado hoy. No lo uses como mapa; usa este
archivo o `docs/project_memory/`.

### Código muerto (importado por nadie, no lo "arregles" — bórralo o ignóralo)
| Ruta | Estado |
|---|---|
| `tabs/` completo salvo `tab_report.py` | ~4.500 líneas huérfanas (tab1–tab6, ripios, imports, recon) |
| `report_export/callbacks/report_cb.py` | huérfano **y roto**: llama `export_dataframe_with_template` sin importarlo → `NameError` si se montara |
| `report_export/layouts/report_tab.py` | huérfano |
| `report_export/callbacks/reportabilidad_cb_backup.py` | copia vieja, 1.719 líneas |
| `versiones_prueba/reportabilidad_cb_hojas_mensuales_v6..v10.py` | 5 copias históricas del callback |
| `dash_carga_excel_mysql.py`, `mov_cam_loader.py`, `prueba_bitacora_*.py`, `setup.py` | scripts sueltos legacy (MySQL) |

Si buscas una función con grep vas a encontrarla 6 veces. **La copia viva es
siempre `report_export/callbacks/reportabilidad_cb.py`.**

---

## 3. Convenciones que hay que saber antes de tocar SQL

1. **Los SP que terminan en `_test` son los de producción.** No son pruebas.
   `sp_mantiene_datos_conciliados_emision_test`, `sp_reporte_turno_test`,
   `sp_actualizar_reporte_turno_cache_emision_test`,
   `sp_generador_reporte_diario_emision_test`. Los homónimos sin sufijo son
   las versiones viejas, deliberadamente sin uso (ver docstring de
   `reclamo/db.py:publicar`, decisión 2026-08-02: v1.15 vs v1.14).
2. **Sufijo `_emision`** = la línea nueva de Datos Conciliados (incluye ajuste
   de Chancado y `Ley_CuT_Real_srr` por balance residual). La UI usa `_emision`;
   las funciones sin sufijo siguen existiendo y ya no se llaman desde la UI viva.
3. **Contrato de fechas mixto.** Los SP de turno/cache usan **fin exclusiva**
   (`Fecha >= @ini AND Fecha < @fin`); las vistas de lectura (`fetch_bd_ton_report`)
   usan **fin inclusiva**. En los callbacks verás
   `fin_sql_exclusivo = f_fin + 1 día` — no lo borres.
4. **Año fiscal = julio–junio** (`_obtener_rango_fiscal_hasta_mes`).
5. **Fecha de corte operacional**: nunca se reporta hasta "hoy", se reporta
   hasta el último día operacionalmente cerrado. Existen **dos definiciones**,
   pero hoy **solo una está en uso**:
   - ✅ `fetch_fecha_corte_operacional_representatividad` → `tot_TM` +
     `v_bitacora_rangos_norm` (T1/T2/SRR cubiertos por el totalizador de 10 s).
     **La usan grilla, publicación y exportación por igual**, desde que el
     refresco se centralizó en `refrescar_representatividad_para_exportacion`.
   - ⚰️ `fetch_fecha_corte_representatividad` → vista `v_datos_apilado_tmh_v2`.
     **Sin uso en el código vivo** desde 2026-08-03. Antes la usaba la grilla y
     era la causa de "el Excel no coincide con la pantalla". No la revivas: si
     necesitas el corte, usa la de arriba.

---

## 4. Reportes de la sección Reportabilidad

`reportabilidad_page.py` dibuja tarjetas; cada botón es un `id` pattern-matching
(`{"type": "report-export-btn", "tipo": ...}`) y **un solo callback** atiende a
todos, ramificando por `tipo`.

| Tarjeta | `tipo` | Estado |
|---|---|---|
| Representatividad Torres | `representatividad_torres` (+ `_quimico`/`_fisico`/`_srr` para PDF) | Completo, con snapshot oficial e historial |
| Análisis Torres de Muestreo (por turno) | `reporte_turno` (+ `_turno`/`_generador`) | Completo, sin snapshot |
| Datos Conciliados | `prod` | Completo, plantilla `reporte/Template_DatosConcialiados.xlsx` |
| Balance Semanal / Conciliación Mensual | `balance`, `conciliacion` | **Placeholder legacy**: caen al `else` genérico, `fetch_report_data` + `export_dataframe_with_template`. Gráficos de ejemplo con `Produccion_Catodos_Real`. No es funcionalidad real |

Callbacks principales en `reportabilidad_cb.py`:
`generar_reporte` (6905) · `exportar_excel` (7216) · `generar_pdf` (7456) ·
`publicar_reporte_representatividad` (7805) · historial (8051/8083) ·
borrado con modal + texto "confirmar borrado" (7913–7968).

---

## 5. 🎯 Representatividad de Torres: grilla vs XLSX vs PDF — qué dispara cada botón

Esta es la pregunta cara del módulo, porque **tres botones que parecen
"mirar lo mismo" tocan la base de forma muy distinta**. Dos de ellos
**escriben** en tablas derivadas de producción.

### 5.1 "Editar comentarios" → la grilla (`generar_reporte`, tipo `representatividad_torres`)

Ruta: `generar_reporte` → `_cargar_detalle_representatividad_periodo(ini, fin, paquete=None)`
→ `_fetch_fuentes_mensuales_torres` (la copia local de `reportabilidad_cb.py:4540`).

**Desde 2026-08-03 abrir la grilla refresca primero** (antes era solo lectura, y
mostraba el estado que había dejado la última publicación o PDF):

```
refrescar_representatividad_para_exportacion(mes_de_fin_día1, fin)   ⚠️ ESCRIBE
   → fetch_fecha_corte_operacional_representatividad   (tot_TM + v_bitacora_rangos_norm)
   → EXEC sp_mantiene_apilado_tmh_v2_test  @DiasReproceso=7   ← desde 2026-08-05
   → EXEC sp_calcular_resumen_intervalo_totTM
   → EXEC sp_refrescar_representatividad_torres
   → EXEC sp_sincronizar_bd_ton
```

⚠️ **El primer paso es nuevo y es el que faltaba** — ver §5.7. El aviso en
pantalla (`_AVISO_REFRESCO_EDITOR`) lista los cuatro; si agregas un paso,
actualiza también esa lista.

Con eso el editor comparte fecha de corte con lo que se va a publicar (antes
cortaba por `v_datos_apilado_tmh_v2` y la publicación por `tot_TM`, y podían
diferir). **`fetch_fecha_corte_representatividad` quedó sin uso en el código vivo.**

⚠️ Serializado por mes con `sp_getapplock` (Exclusive, Session) dentro de
`refrescar_representatividad_para_exportacion`. Después del refresco, todo lo
demás es lectura:

| Llamada | Objeto BD | Tipo |
|---|---|---|
| `fetch_bd_ton_report` | vista `v_bd_ton_reportabilidad` | SELECT |
| `fetch_estado_apilado_turno_representatividad` | vistas `v_estado_apilado_turno_representatividad` + `v_reporte_turno_campania_modulo_test` | SELECT |
| `fetch_gestion_representatividad_fy` ×2 (QUIMICO y FISICO) | **SP** `sp_gestion_representatividad_fy` | EXEC de solo lectura |
| `fetch_reporte_torre_oficial_detalle` / `fetch_comentarios_representatividad_periodo` | `reporte_torre_oficial_detalle` | SELECT (recupera comentarios ya publicados) |
| `fetch_historial_reporte_torre_oficial`, `mes_tiene_reporte_activo` | `reporte_torre_oficial_cab` | SELECT |

Después arma el detalle **en Python**: `_preparar_material_por_turno` →
`_preparar_detalle_mensual_torres` (×2, químico/físico) →
`_fusionar_detalle_representatividad` → `_completar_tm3_editor_desde_fuente_viva`
→ `_fusionar_solo_comentarios_en_detalle_vivo`.

Detalle no obvio: **la grilla ejecuta `sp_gestion_representatividad_fy` dos
veces aunque el editor no muestre el indicador FY** — viene de reusar
`_fetch_fuentes_mensuales_torres`, que también valida que el FY traiga filas
(lanza `RuntimeError` si viene vacío). Es la causa más probable de un "no puedo
abrir el editor" que en realidad es un problema de FY, no de comentarios.

Edición de la grilla (`alternar_pad_rep`, `sincronizar_comentarios_desde_grilla`,
`cambiar_tab_comentarios_rep`, ~7930–8010): **100 % en memoria**, sobre
`dcc.Store`. No hay autosave. Nada se persiste hasta "Generar reporte final".

**Publicar es lento y el spinner tiene que decir la verdad.** El modal
`rep-publicar-modal` lo *abre* un `clientside_callback` y lo *cierra*
`running=` del callback servidor `publicar_reporte_representatividad`. Hasta
2026-08-05 se cerraba con un `setTimeout` de 1 s: el spinner desaparecía y la
publicación seguía corriendo minutos. Dos cosas que no hay que deshacer:
- El cierre va en `running=`, **no** en un `Output` normal — `running` se apaga
  también cuando el callback lanza excepción; un `Output` dejaría el spinner
  girando para siempre ante cualquier error.
- El `Output` del modal en `running` necesita `allow_duplicate=True` porque el
  clientside ya es dueño de esa prop. Verificado que Dash 4.2 lo registra
  (`runningOff` incluye `rep-publicar-modal.is_open: False`).

### 5.2 "Generar reporte final" → publicar (`publicar_reporte_representatividad`)

El **único camino que escribe el snapshot oficial**, y solo en modo *Mes completo*.

```
armar_paquete_reporte_torre_oficial(ini, fin)              [report_export.py:1496]
 └─ refrescar_representatividad_para_exportacion()         ← ⚠️ ESCRIBE
      1. fetch_fecha_corte_operacional_representatividad   (tot_TM + v_bitacora_rangos_norm)
      2. EXEC sp_calcular_resumen_intervalo_totTM  @FechaInicio/@FechaFin
      3. EXEC sp_refrescar_representatividad_torres @fecha_inicio/@fecha_fin
      4. EXEC sp_sincronizar_bd_ton                @fecha_inicio/@fecha_fin
    (los 3 se ejecutan con rango [inicio, fecha_corte], cada uno en su propia
     transacción; si uno falla se aborta con RuntimeError)
 ├─ fetch_representatividad_torres_report → SP sp_reporte_representatividad_torres
 ├─ fetch_pesos_representatividad_report  → SELECT v_peso_teorico_turno_torre_excel
 │     + peso_real_torre_turno (hoja trazabilidad pesos, desde 777a4bc; la
 │       grilla no la tiene)
 ├─ fetch_bd_ton_report (FY completo) + _fetch_fuentes_mensuales_torres_oficial
 └─ devuelve 7 bloques + fecha_corte_operacional + anio_fiscal
→ _cargar_detalle_representatividad_periodo(paquete=paquete)   ← detalle "vivo", NO la grilla
→ _fusionar_solo_comentarios_en_detalle_vivo(detalle, registros)
→ write_reporte_torre_oficial()   soft-delete del activo del mes + INSERT en 3 tablas
→ relee lo guardado y rearma el editor
```

Regla de oro codificada aquí: **la grilla nunca es fuente de tonelajes,
actividad ni representatividad**. De la grilla solo se toman los seis
comentarios editables y el Pad ajustado, por `Fecha + Turno`. Todo lo demás se
reconstruye desde el paquete recién refrescado.

Tablas del snapshot (DDL en `docs/stored_procedures/reporte_torre_oficial.sql`):
`reporte_torre_oficial_cab` (1 activo por mes, soft-delete) ·
`reporte_torre_oficial_snapshot` (6 bloques JSON) ·
`reporte_torre_oficial_detalle` (Fecha+Turno, reps + comentarios + Pad).

### 5.3 "Descargar Excel oficial vigente" → `exportar_excel`, tipo `representatividad_torres`

**El más barato y el único puramente de lectura del trío.** No recalcula nada,
no toca ningún SP:

```
_reporte_oficial_activo_para_periodo(ini, fin)     → SELECT cab
  ↳ si no hay reporte activo del mes: aborta con mensaje, no exporta
fetch_reporte_torre_oficial_snapshot(id_reporte)   → SELECT snapshot (JSON)
fetch_reporte_torre_oficial_detalle(id_reporte)    → SELECT detalle
_export_representatividad_desde_paquete(...)       → XlsxWriter en memoria
```

Es decir: **el XLSX es una foto de lo publicado**. Si nadie publicó el mes, no
hay XLSX. Es intencional, no un bug.

### 5.4 "PDF Químico / Físico / SRR vigente" → `generar_pdf`

⚠️ **Aquí está la asimetría importante.** A pesar de decir "vigente" igual que
el botón de Excel, el PDF **no** lee el snapshot: reconstruye todo en vivo.

```
_construir_fuente_unica_representatividad(ini, fin)     [reportabilidad_cb.py:6262]
 ├─ fetch_comentarios_representatividad_periodo(...)    ← rescata comentarios publicados
 ├─ armar_paquete_reporte_torre_oficial(...)            ← ⚠️ los MISMOS 3 SP de escritura de 5.2
 ├─ _export_representatividad_desde_paquete(...)        → workbook base
 └─ _validar_workbook_representatividad(...)
→ _pdf_representatividad_desde_xlsx(...) → pdf_torres.render_torres / render_srr (reportlab)
```

Consecuencias prácticas:
- Apretar "PDF vigente" **dispara recálculo y escritura** en
  `Resumen_Intervalo_TotTM`, `representatividad_torres_resultado` y BD Ton.
  Es lento y no es una operación inocua.
- El PDF puede **diferir del XLSX** del mismo mes: el XLSX viene del snapshot
  congelado, el PDF de datos recalculados hoy. Si alguien reporta "el PDF no
  cuadra con el Excel", esta es la causa.
- Sí comparten comentarios: el PDF los relee de `reporte_torre_oficial_detalle`
  y los inyecta como `paquete["mapa_comentarios"]`.

### 5.5 Historial (por versión publicada) — 8051 / 8083

Ambos (XLSX y PDF) leen **solo del snapshot** de ese `id_reporte`. Reproducible,
sin SP, sin recálculo. Si necesitas un PDF que cuadre con el Excel oficial,
sácalo del **historial**, no del botón "vigente".

### 5.6 Resumen en una tabla

Los 4 SP de escritura son siempre los mismos y en el mismo orden, porque viven
en `refrescar_representatividad_para_exportacion`:
`sp_mantiene_apilado_tmh_v2_test` → `sp_calcular_resumen_intervalo_totTM` →
`sp_refrescar_representatividad_torres` → `sp_sincronizar_bd_ton`.

| Acción | Escribe | SP de lectura | Fuente |
|---|---|---|---|
| Editar comentarios (grilla) | los 4 (desde 2026-08-03, serializados con `sp_getapplock` por mes) | `sp_gestion_representatividad_fy` ×2 | vivo, recién refrescado |
| Generar reporte final | los 4 | `sp_reporte_representatividad_torres`, `sp_gestion_representatividad_fy` ×2 | vivo → **escribe snapshot** |
| Excel oficial vigente | — | — | snapshot publicado |
| PDF vigente | los 4 | los mismos de publicar | vivo (**no** snapshot) |
| Historial XLSX/PDF | — | — | snapshot de esa versión |

### 5.7 🔥 La cadena del apilado: por qué un día con tonelaje desaparecía

**El bug más caro de este módulo, cerrado 2026-08-05 (`62807ce`).** Síntoma:
BD Ton muestra tonelaje para un día, y la grilla (y por lo tanto el XLSX/PDF)
lo oculta entero.

La cadena, verificada contra la base leyendo `sys.sql_modules` — **ninguna de
estas dos vistas tiene DDL en el repo**:

```
sp_mantiene_apilado_tmh_v2_test        (SP de mantención, congela por día)
  → Control_Apilado_TMH_v2_test        (tabla congelada)
  → v_datos_apilado_tmh_v2             (SELECT * de la tabla, nada más)
  → v_estado_apilado_turno_representatividad   (UNION ALL turno A / turno B)
        Turno_Evaluable = Flag_Apilado_Valido_X = 1 AND TMH_Apilado_Total_X > 0
  → fetch_estado_apilado_turno_representatividad
  → _preparar_material_por_turno  →  Turno_Activo_Oficial
  → _preparar_detalle_mensual_torres  →  TMH_CV08 / TMH_CV108 = None si inactivo
```

**El detonante**: `_preparar_material_por_turno` (`reportabilidad_cb.py:1981`)
calcula `Turno_Activo_Oficial = Apilado_TMS_Real_Turno > 0`, pero acto seguido,
**para toda fecha ≥ 2026-01-01**, lo sobrescribe con `Turno_Evaluable == 1`.
Es decir, desde 2026 el tonelaje deja de importar: manda el flag. Si el flag
está viejo, el día se oculta aunque BD Ton tenga cifras.

**Cómo se envenena el flag**: `Control_Apilado_TMH_v2_test` es *congelada*. Si
alguien la puebla para el día D antes de que existan las lecturas de D 20:00 y
D+1 08:00, la fila queda con totalizadores `NULL` → `Flag_Apilado_Valido = 0` →
`Turno_Evaluable = 0`, **y nadie la reprocesa nunca**. Caso real del 2026-08-04:

| Fecha | CV008_Tot_20 | CV008_Tot_08_día_sig | Flag_A | Flag_B |
|---|---|---|---|---|
| 2026-08-03 | 16.078.168 | 16.102.657 | 1 | 1 |
| 2026-08-04 | **NULL** | **NULL** | **0** | **0** |

Mientras tanto pesos/representatividad/BD Ton **sí** se recalcularon al día
siguiente. Resultado: BD Ton nueva, `Turno_Evaluable` viejo, día invisible.

**El arreglo**: `sp_mantiene_apilado_tmh_v2_test` se agregó como **primer paso**
de `refrescar_representatividad_para_exportacion`, dentro del applock, mismo
rango `[inicio, corte]` que los otros tres.

⚠️ **`@DiasReproceso` tiene que ser > 0.** Con `0` el SP solo procesa fechas que
*no tienen fila*; una fila congelada mala se quedaría mala para siempre. Está
hardcodeado en `7` (mismo valor que el flujo de reporte por turno).

⚠️ **No confundir con `sp_refrescar_historico_apilado_test`**
(`refrescar_historico_apilado_report`). Ese alimenta **Datos Conciliados** y no
participa en esta cadena. Es el candidato obvio por el nombre y es el
equivocado: correrlo es caro y no arregla nada acá.

El DDL de `v_datos_apilado_tmh_v2` ya traía esto anotado como deuda desde que se
migró de cálculo en vivo a tabla congelada — *"alguien tiene que llamar a
sp_mantiene_apilado_tmh_v2_test para que la vista vea dias nuevos… queda
pendiente de tu confirmacion"*. Se hizo para reporte por turno
(`exportar_excel`) y se olvidó para Representatividad.

### 5.8 Lo que la grilla y el reporte SÍ comparten (no son dos cálculos)

Malentendido fácil: creer que la grilla y el XLSX/PDF calculan la
representatividad por caminos distintos. **No.** Las hojas mensuales
Químico/Físico/SRR salen de `_agregar_hojas_mensuales_torres` →
`_preparar_detalle_mensual_torres(df_bd_ton_mes, df_turno_mes)`, que son
**exactamente las funciones que usa la grilla**.

`paquete["rep_torres"]` (lo que devuelve `sp_reporte_representatividad_torres`)
alimenta **solo la hoja diaria "Representatividad Torres"**, no las mensuales.
Por eso la grilla nunca ejecuta ese SP y aun así coincide.

La regla vigente: **grilla == reporte, más comentarios y Pad encima**. Si
divergen, el problema está en las *entradas* (rango, fecha de corte, capa sin
refrescar), no en la lógica. Corolario práctico: cualquier refresco nuevo va en
`refrescar_representatividad_para_exportacion` y no en un callback, o vuelve la
asimetría.

Divergencia cerrada el 2026-08-05: el editor releía BD Ton con `[ini, fin]` solo
para el TM3 y mostraba días posteriores al corte operacional que el reporte no
incluye. Ahora usa `fuentes["df_bd_ton_mes"]` = `[día1, corte]`, igual que las
hojas.

---

## 6. Los otros dos flujos de reporte

### Análisis Torres de Muestreo por turno (`reporte_turno`)
Tanto en "generar" como en PDF, **siempre escribe antes de leer**:
```
actualizar_factor_ajuste_camiones_v2_report(ini, fin-1)     EXEC sp_mantiene_factor_ajuste_camiones_v2_test
actualizar_reporte_turno_cache_emision(ini, fin_exclusivo)  ← ver abajo
fetch_reporte_turno_cache_emision(...)                      SELECT sobre el cache
```
`actualizar_reporte_turno_cache_emision` (último commit `fb3003c`, 2026-08-03)
ahora encadena **`sp_refrescar_clays_cufe` antes del cache**, pero solo para
fechas ≥ `FECHA_CORTE_CLAYS_CUFE = 2026-08-01` (`report_export.py:83`). Valida
`start < end` (fin exclusiva) y envuelve los errores con el nombre del SP.
Ese corte duro por fecha es la clase de constante que caduca: revísala si
aparecen diferencias de Clays/CuFe en periodos viejos.

### Datos Conciliados (`prod`)
```
refrescar_historico_apilado_report()          EXEC sp_refrescar_historico_apilado_test
actualizar_datos_conciliados_emision_report() EXEC sp_mantiene_datos_conciliados_emision_test
fetch_datos_conciliados_emision_report()      SELECT Datos_conciliados_of
export_datos_conciliados_to_template(df, reporte/Template_DatosConcialiados.xlsx)
```
También escribe en producción. Ojo: el callback tiene un **print de depuración
hardcodeado** para el 14 y 21 de julio 2026 (`reportabilidad_cb.py:7364`).

`export_to_excel.py` escribe sobre la plantilla con openpyxl a coordenadas
fijas (`PLANTILLA_DATOS_START_ROW=16`, col C, 43 columnas, limpia 2000 filas).
**Cambiar la plantilla rompe el exportador**: hay `_detectar_layout_datos_conciliados`
para tolerar corrimientos, pero los merges/anchos/alturas están tabulados a mano.

---

## 7. Módulo Reclamo (`reclamo/`)

Panel separado, esquema SQL propio (`reclamo.*`), y **la mejor documentación
del repo está en los docstrings de `reclamo/db.py`** — léelos antes de tocar nada.

- Todo el SQL vive en `db.py`. `panel.py` solo dibuja y llama.
- Lecturas: `v_diferencia_cv25`, `v_rendimiento_rotopala`, `v_cuadratura_modulo`,
  `v_reclamo_diario`, `v_reclamo_para_conciliados`, `log_automatizacion`.
- **Escrituras (botones)**:
  - `recalcular()` → `sp_sincronizar_desde_etl` (+`@Confirmar=1`) **y luego**
    `sp_calcular_reclamo_diario`. Encadenados a propósito desde 2026-08-02: sin
    el sync, `calculo_diario` se quedaba congelado en silencio (bug real:
    corte en 2026-07-26 con datos publicados hasta el 31).
  - `publicar()` → `sp_mantiene_datos_conciliados_emision_test`.
    **ESCRIBE EN PRODUCCIÓN** (`inventar_SpcHidr.Datos_conciliados_of`). Exige
    confirmación explícita en la UI (`cb_pedir_confirmacion_publicar`).
  - `registrar_ajuste()` → `sp_registrar_ajuste_manual`.
  - `mantener_secuencia()` → `sp_auto_mantener_secuencia` (congela módulos
    nuevos, cierra al 100 %, abre el siguiente; deja bitácora con alertas).
- Cuidado con `[campaña_id]` (con ñ) en SQL: siempre se aliasa a `campana_id`.

---

## 8. Autenticación y configuración

- `auth.py`: login contra la **tabla de usuarios de Django** definida en
  `LOGIN_DATABASE` (ej. `DEV_SIIR.dbo.auth_user`), verificado con
  `passlib.django_pbkdf2_sha256`. **La app no crea usuarios**: eso se hace desde
  Django. Los hashes `!xxx` (cuenta sin password usable) se filtran con `identify()`.
- `LOGIN_DATABASE` se valida con regex `[\w.]+` porque se interpola en el SQL
  (no se puede parametrizar un nombre de tabla). No relajes esa validación.
- `main.py:@server.before_request` protege todo salvo `/static` y `/auth`.
- `SECRET_KEY` es **obligatoria** (`os.environ[...]`, revienta al arrancar si falta).
- `db_connection.py`: `ENTORNO` elige backend — `1`/`2` MySQL (**devuelven `None`,
  deshabilitados**), `3` SQL Server ODBC 17 sin cifrado, `4` SQL Server ODBC 18
  con TLS. En esta máquina: `ENTORNO=3`, `ODBC Driver 17`, DB `inventar_SpcHidr`.
  El código llama "macOS" al entorno 4 por herencia; en realidad es "ODBC 18 + TLS".
### ⚠️ Dos bases parecidas: `inventar_SpcHidr` vs `inventar_SpcHidr_PROD`

El servidor tiene ambas, y **las dos contienen un esquema llamado
`inventar_SpcHidr`** — por eso los nombres de dos partes del código
(`inventar_SpcHidr.sp_x`) resuelven en cualquiera de las dos y *no* delatan a
cuál estás conectado. Lo que manda es `SQLSERVER_DB` del `.env`.

Comparación medida el **2026-08-03**:

| | `inventar_SpcHidr` | `inventar_SpcHidr_PROD` |
|---|---|---|
| `sp_calcular_resumen_intervalo_totTM` | ✅ | ❌ **falta** |
| `Resumen_Intervalo_TotTM` (tabla) | ✅ 1.470 filas | ❌ **falta** |
| `sp_mantiene_datos_conciliados_emision_test` | ✅ | ❌ **falta** |
| `sp_actualizar_reporte_turno_cache_emision_test` | ✅ | ❌ **falta** |
| `sp_refrescar_clays_cufe` | ✅ | ❌ **falta** |
| resto de SP/vistas del reporte | ✅ | ✅ |
| `reporte_torre_oficial_cab` | 64 reportes, hasta 2026-08 | 24 reportes, hasta 2026-07 |
| `tot_TM` | 383.041 filas | 2.264.041 filas (¿sin purgar? en la otra hay `sp_purgar_totTM_diario`) |

**Contra `inventar_SpcHidr_PROD` la app está rota en tres reportes**
(Representatividad, Datos Conciliados y Reporte por Turno): el código vivo pide
objetos que esa base no tiene desplegados. El síntoma es siempre el mismo,
`Could not find stored procedure`. Antes de depurar cualquier reporte,
**verifica a qué base apunta `SQLSERVER_DB`**. Ayuda `log_db_destino_reporte_torre()`
(`report_export.py:22`), que imprime el destino.

- `PDF_ENGINE`: `python` (default, reportlab) o `libreoffice` (legacy).
  El comentario en `_motor_pdf()` explica por qué se abandonó LibreOffice: no es
  reproducible entre versiones (decide alturas de fila y anclaje de objetos por
  su cuenta, el gráfico FY se montaba sobre la tabla en el servidor). No vuelvas
  a esa ruta sin motivo fuerte.

---

## 9. Tests

`report_export/tests/` — 93 tests, pytest puro, **todos con la BD mockeada**
(`MagicMock` sobre el engine). Corren en ~17 s sin conexión.

| Test | Protege |
|---|---|
| `test_login.py` | verificación de hash Django, cuentas inactivas |
| `test_datos_conciliados_excel.py` | plantilla, formato, resumen MTD (el más grande) |
| `test_refresco_representatividad.py` | **orden y parámetros de los 4 SP de §5.2**, y que el apilado lleve `@DiasReproceso=7` (§5.7) |
| `test_comentarios_tm3.py`, `test_borrar_comentarios.py`, `test_pad_editable.py` | reglas de la grilla |
| `test_pdf_torres_python.py`, `test_pdf_representatividad_layout.py` | layout del PDF |

No hay `conftest.py` ni fixtures compartidos. Ruido: ~38k `DeprecationWarning`
de openpyxl (`Style.copy()`), inofensivo.

---

## 10. Deuda y trampas conocidas

1. **`ARCHITECTURE.md` miente** (§2). El mapa fiable es este archivo y
   `docs/project_memory/`.
2. **`reportabilidad_cb.py` tiene 8.113 líneas** y mezcla UI, reglas de negocio
   y generación de Excel. Cualquier cambio ahí necesita grep cuidadoso: hay 6
   copias del archivo en el repo (backup + `versiones_prueba/`).
3. **`assets/bdd.env` está versionado en git** con credenciales MySQL
   (`root`/password en claro). Legacy, ya no se usa, pero está en el historial:
   si esa contraseña se reutiliza en algún lado, rótala.
4. **El repo pesa 152 MiB** por xlsx/pdf de datos operacionales versionados
   (`Datos Hidro/`, `Datos imput/`, `Desbalances/`, `report_export.zip`).
5. **Cache de reporte por turno sin refresco automático** — pendiente
   documentado y decidido, no implementado. Ver
   `docs/project_memory/pipeline_cache_reporte_turno.md` §5 (opción 1 elegida:
   refrescar tras cada importación, rango desde la mínima fecha cargada hasta
   hoy+1 exclusiva, por el arrastre de leyes/humedad).
6. **PDF "vigente" ≠ Excel "vigente"** (§5.4). Es la inconsistencia más
   probable de aparecer como bug reportado por usuario.
6b. ✅ **Cerrada 2026-08-03 — applock de refresco de representatividad.**
   `refrescar_representatividad_para_exportacion` serializa por mes con
   `sp_getapplock` Exclusive/Session (`rep_torres_refresco:YYYY-MM`). Detalle:
   [FIX_refresco_representatividad_concurrencia.md](FIX_refresco_representatividad_concurrencia.md).
   Pendiente de verificación contra la base: idempotencia/alcance de los tres
   SP y duración real vs timeout de 180 s (§4 del fix).
6c. ✅ **Cerrada 2026-08-05 — `Turno_Evaluable` desactualizado ocultaba días
   con tonelaje.** Ver §5.7. Pendiente de verificar contra la base que el
   2026-08-04 quedó con `Flag_Apilado_Valido = 1` tras el primer refresco.
7. **`FECHA_CORTE_CLAYS_CUFE = 2026-08-01`** hardcodeada (§6).
8. Prints de depuración por todos lados (`[RTO]`, `[EXCEL]`, `[PDF]`, `[DEBUG]`),
   incluido uno con fechas fijas de julio 2026. Son el log de facto en producción.
9. Commits con mensajes de una palabra ("eso", "cambios", "estetica",
   "PARCHE MUNDIAL"): el historial de git no sirve como memoria. De ahí este
   archivo.
10. **Test rojo heredado**: `test_datos_conciliados_excel.py::
   test_fecha_corte_informa_columnas_estructurales_faltantes` falla en `main`
   desde antes del 2026-08-05 (`AssertionError` en la línea 198). No tiene
   relación con Representatividad. Si tu suite marca 92/1, es este; si marca
   otra cosa, rompiste algo.
11. **`v_datos_apilado_tmh_v2` y `v_estado_apilado_turno_representatividad` no
   tienen DDL en `docs/views/`** (solo hay dos vistas de chancado ahí), pese a
   decidir la evaluabilidad de todo el reporte. Para leerlas:
   `SELECT m.definition FROM sys.sql_modules m JOIN sys.objects o
   ON o.object_id = m.object_id WHERE o.name = '<vista>'`.

---

## 11. Arranque rápido

```bash
pip install -r requirements.txt          # requiere driver ODBC de SQL Server instalado
cp .env.example .env                     # completar SQLSERVER_*, SECRET_KEY, LOGIN_DATABASE
python main.py                           # http://127.0.0.1:8065  → redirige a /auth/login_page
python -m pytest report_export/tests -q  # 76 tests, sin BD
```

Docker: `docker build . && docker run -e PORT=10000 ...` (la imagen instala
`libreoffice-calc` solo por la ruta PDF legacy).

---

## 12. Documentos relacionados

- `docs/project_memory/dependencias_reporte_torres.md` — mapa BD del reporte de torres.
- `docs/project_memory/pipeline_cache_reporte_turno.md` — cadena SP → cache → diario.
- `docs/stored_procedures/*.sql`, `docs/views/*.sql`, `docs/db_functions/*.sql` —
  copias versionadas de los objetos de BD (no todos: `reporte_turno_cache` y las
  tablas del esquema `reclamo` no tienen DDL en el repo).
