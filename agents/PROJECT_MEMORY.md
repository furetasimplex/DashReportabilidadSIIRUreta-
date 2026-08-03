# Memoria del proyecto — DashReportabilidadSIIR

Contexto operativo para agentes/desarrolladores que entran frío al repo.
Lo que el código **no** dice solo: qué está vivo, qué está muerto, qué
dispara escrituras en producción y dónde están las trampas.

> Investigado: 2026-08-03 · Rama `main` (limpia) · último commit `fb3003c`
> Verificado corriendo: `python -m pytest report_export/tests -q` → **76 passed** (18 s).

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
   hasta el último día operacionalmente cerrado. Hay **dos definiciones
   distintas y ambas están en uso**:
   - `fetch_fecha_corte_representatividad` → vista `v_datos_apilado_tmh_v2`,
     día con CV-008 A/B y CV-108 A/B no nulos. **La usa la grilla.**
   - `fetch_fecha_corte_operacional_representatividad` → `tot_TM` +
     `v_bitacora_rangos_norm` (T1/T2/SRR cubiertos por el totalizador de 10 s).
     **La usa la publicación/exportación.**
     Pueden dar días distintos: es una fuente conocida de "el Excel no coincide
     con la pantalla".

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
   → EXEC sp_calcular_resumen_intervalo_totTM
   → EXEC sp_refrescar_representatividad_torres
   → EXEC sp_sincronizar_bd_ton
```

Con eso el editor comparte fecha de corte con lo que se va a publicar (antes
cortaba por `v_datos_apilado_tmh_v2` y la publicación por `tot_TM`, y podían
diferir). **`fetch_fecha_corte_representatividad` quedó sin uso en el código vivo.**

⚠️ **Sin lock**: ver deuda §10.6b. Después del refresco, todo lo demás es lectura:

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

Edición de la grilla (`alternar_pad_rep` 7656, `sincronizar_comentarios_desde_grilla`
7693, `cambiar_tab_comentarios_rep` 7719): **100 % en memoria**, sobre
`dcc.Store`. No hay autosave. Nada se persiste hasta "Generar reporte final".

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
 ├─ fetch_bd_ton_report (FY completo) + _fetch_fuentes_mensuales_torres_oficial
 └─ devuelve 6 bloques + fecha_corte_operacional + anio_fiscal
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

| Acción | SP de escritura | SP de lectura | Fuente |
|---|---|---|---|
| Editar comentarios (grilla) | `sp_calcular_resumen_intervalo_totTM`, `sp_refrescar_representatividad_torres`, `sp_sincronizar_bd_ton` (desde 2026-08-03, **sin lock**) | `sp_gestion_representatividad_fy` ×2 | vivo, recién refrescado |
| Generar reporte final | `sp_calcular_resumen_intervalo_totTM`, `sp_refrescar_representatividad_torres`, `sp_sincronizar_bd_ton` | `sp_reporte_representatividad_torres`, `sp_gestion_representatividad_fy` ×2 | vivo → **escribe snapshot** |
| Excel oficial vigente | — | — | snapshot publicado |
| PDF vigente | los mismos 3 de publicar | los mismos de publicar | vivo (**no** snapshot) |
| Historial XLSX/PDF | — | — | snapshot de esa versión |

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

`report_export/tests/` — 76 tests, pytest puro, **todos con la BD mockeada**
(`MagicMock` sobre el engine). Corren en ~18 s sin conexión.

| Test | Protege |
|---|---|
| `test_login.py` | verificación de hash Django, cuentas inactivas |
| `test_datos_conciliados_excel.py` | plantilla, formato, resumen MTD (el más grande) |
| `test_refresco_representatividad.py` | **orden y parámetros de los 3 SP de §5.2** |
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
6b. 🔴 **DEUDA ABIERTA — el refresco de representatividad no tiene lock.**
   `refrescar_representatividad_para_exportacion` son tres `EXEC` sueltos sin
   serializar. Dos ejecuciones concurrentes sobre el mismo mes se entrelazan
   (una reescribe `representatividad_torres_resultado` mientras la otra
   sincroniza BD Ton **desde esa misma tabla**) y dejan una foto inconsistente
   sin error ni log; si además se publica, esa foto queda congelada en el
   snapshot oficial.
   **La exposición creció el 2026-08-03**: antes lo disparaban solo publicar y
   "PDF vigente"; ahora también cada apertura del editor (§5.1). Deuda aceptada
   a conciencia al aplicar ese cambio.
   Mitigado a medias: el `running=` de `generar_reporte` deshabilita el botón
   mientras corre, así que **el doble clic de un mismo usuario ya no lanza dos
   refrescos**. Falta el caso real: dos usuarios distintos sobre el mismo mes.
   Fix diseñado y listo para pegar (`sp_getapplock` por mes, alcance `Session`):
   [FIX_refresco_representatividad_concurrencia.md](FIX_refresco_representatividad_concurrencia.md) §3.1.
   Marcado en el código con `# ponytail:` en `reportabilidad_cb.py:768`.
7. **`FECHA_CORTE_CLAYS_CUFE = 2026-08-01`** hardcodeada (§6).
8. Prints de depuración por todos lados (`[RTO]`, `[EXCEL]`, `[PDF]`, `[DEBUG]`),
   incluido uno con fechas fijas de julio 2026. Son el log de facto en producción.
9. Commits con mensajes de una palabra ("eso", "cambios", "estetica"): el
   historial de git no sirve como memoria. De ahí este archivo.

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
