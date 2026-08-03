# Fix propuesto — refresco de Representatividad de Torres: frescura + concurrencia

| Parte | Estado |
|---|---|
| §3.2 — disparar el refresco al abrir la grilla | ✅ **APLICADA** 2026-08-03 (`reportabilidad_cb.py:768`), 78 tests verdes |
| §3.1 — `sp_getapplock` (concurrencia) | 🔴 **DEUDA TÉCNICA ABIERTA** — decisión explícita del usuario: aplicar el fix sin concurrencia |
| §3.3 — tests | ✅ dos tests nuevos del camino de la grilla; los del lock quedan pendientes con §3.1 |

**Se aplicó la parte que aumenta el riesgo antes que la que lo contiene.** El
entrelazado descrito en §1.3 ya no requiere que dos usuarios publiquen a la vez:
basta con que dos abran el editor del mismo mes. El patch del lock está listo
para pegar (§3.1) y su flujo está validado contra un motor falso (3 escenarios);
lo que falta verificar contra la base sigue en §4.

> Redactado 2026-08-03 · Contexto completo en [PROJECT_MEMORY.md](PROJECT_MEMORY.md) §5.

---

## 1. El problema

### 1.1 La grilla muestra el estado de la última publicación, no el actual

La cadena de materialización es lineal y la grilla está al final:

```
tot_TM  →  sp_calcular_resumen_intervalo_totTM   →  Resumen_Intervalo_TotTM
        →  sp_refrescar_representatividad_torres →  representatividad_torres_resultado
        →  sp_sincronizar_bd_ton                 →  BD Ton (v_bd_ton_reportabilidad)
        →  fetch_bd_ton_report()  →  _preparar_detalle_mensual_torres()  →  GRILLA
```

Esos tres SP corren **solo** dentro de `refrescar_representatividad_para_exportacion`
(`report_export.py:634`), llamada desde `armar_paquete_reporte_torre_oficial`
(`:1509`) — es decir, al **publicar** o al pedir **PDF vigente**. Abrir la
grilla no los dispara.

Resultado: el usuario comenta sobre datos viejos, aprieta "Generar reporte
final", y recién ahí se recalcula todo. El detalle publicado se reconstruye
desde cero (`_cargar_detalle_representatividad_periodo(paquete=paquete)`,
`reportabilidad_cb.py:7849`) conservando solo los 6 comentarios y el Pad: **las
cifras que ve al publicar pueden no ser las que estaba mirando.**

### 1.2 Dos definiciones de fecha de corte conviviendo

| Camino | Función | Fuente |
|---|---|---|
| Grilla | `fetch_fecha_corte_representatividad` | `v_datos_apilado_tmh_v2` (CV-008/CV-108 A y B no nulos) |
| Publicar / PDF | `fetch_fecha_corte_operacional_representatividad` | `tot_TM` + `v_bitacora_rangos_norm` (T1/T2/SRR) |

Pueden devolver días distintos: el editor ofrece días para comentar que la
publicación después no incluye, o al revés.

### 1.3 Concurrencia — y esto **ya pasa hoy**, sin mover nada

`refrescar_representatividad_para_exportacion` no tiene ninguna protección: son
tres `EXEC` sueltos, cada uno en su propia transacción. Hoy mismo, dos usuarios
apretando "Generar reporte final" y "PDF Químico vigente" al mismo tiempo sobre
el mismo mes ejecutan las dos cadenas **entrelazadas** sobre las mismas tablas.
El escenario feo es concreto:

```
Usuario A: sp_refrescar_representatividad_torres (mes 07) ──┐
Usuario B: sp_sincronizar_bd_ton (mes 07)  ←── lee representatividad_torres_resultado
           mientras A la está reescribiendo                 ┘
```

B sincroniza BD Ton contra una tabla a medio reescribir. No hay error, no hay
log: queda una foto inconsistente, y si B además publica, esa foto se congela
en el snapshot oficial.

Mover el disparo a la apertura de la grilla (§1.1) **multiplica la exposición**:
pasa de "dos acciones raras" a "cada vez que alguien abre el editor". Por eso el
fix de frescura y el de concurrencia van juntos o no van.

---

## 2. El fix

Tres piezas, en este orden de importancia:

1. **Serializar el refresco por período** con un *application lock* de SQL
   Server (`sp_getapplock` / `sp_releaseapplock`). Es la pieza que corrige un
   problema que ya existe, y se puede aplicar sola.
2. **Disparar el refresco al abrir la grilla**, reusando la misma función.
3. **Alinear el rango y la fecha de corte** de la grilla con los de la
   publicación (sale gratis: la función de refresco ya devuelve el corte).

### Por qué `sp_getapplock` y no un lock en Python

La app corre bajo `gunicorn -w 2` (Dockerfile): **dos procesos**. Un
`threading.Lock` protege un worker e ignora al otro — y no serviría de nada
contra un `EXEC` lanzado desde SSMS o un job. El lock tiene que vivir donde
está el recurso: en la base. `sp_getapplock` es nativo, no agrega
infraestructura ni tablas, y SQL Server lo libera solo si la conexión muere.

**Alcance `Session`, no `Transaction`**: con `Transaction` habría que envolver
los tres SP en una sola transacción, y sus DELETE/INSERT bloquearían a los
lectores (otra grilla leyendo `v_bd_ton_reportabilidad`) hasta el commit final.
Con `Session` cada SP conserva su transacción propia — exactamente el
comportamiento actual sobre las tablas de datos — y solo se serializa el
refresco entre sí. El precio es que el release tiene que ser explícito: va en
un `finally`.

### Clave del lock: el mes de `end_date`

`_fetch_fuentes_mensuales_torres` arma la grilla siempre con el **mes de la
fecha final** (`fecha_inicio_mes = fin_d.replace(day=1)`), y la publicación
normaliza a mes completo con `normalizar_periodo_mes`. Usar el mes de `fin` como
clave hace que ambos caminos compitan por el mismo recurso, que es lo que
queremos, y deja meses distintos trabajando en paralelo sin estorbarse.

---

## 3. Patch

### 3.1 `report_export/report_export.py` — el lock

Sobre `refrescar_representatividad_para_exportacion` (línea 634):

```python
# ponytail: applock de SQL Server en vez de tabla de estado o lock en Python.
# gunicorn corre 2 workers: un lock de proceso no sirve.
LOCK_REFRESCO_REP_TIMEOUT_MS = 180_000

SQL_GETAPPLOCK_REFRESCO_REP = """
    SET NOCOUNT ON;
    DECLARE @rc int;
    EXEC @rc = sp_getapplock
        @Resource = :recurso,
        @LockMode = 'Exclusive',
        @LockOwner = 'Session',
        @LockTimeout = :timeout;
    SELECT @rc AS rc;
"""

SQL_RELEASEAPPLOCK_REFRESCO_REP = """
    SET NOCOUNT ON;
    EXEC sp_releaseapplock @Resource = :recurso, @LockOwner = 'Session';
"""


def _recurso_lock_representatividad(end_date: date) -> str:
    """Un lock por mes de reporte: la grilla y la publicación usan el mismo."""
    return f"rep_torres_refresco:{end_date:%Y-%m}"


def refrescar_representatividad_para_exportacion(
    start_date: date,
    end_date: date,
) -> date:
    """
    Calcula el corte operacional y refresca, en orden, las capas requeridas
    antes de que el exportador realice cualquier lectura.

    Serializado por mes con un applock de sesión: dos refrescos del mismo
    período no pueden entrelazarse (uno reescribiendo
    representatividad_torres_resultado mientras el otro sincroniza BD Ton
    desde esa misma tabla).
    """
    fecha_corte = fetch_fecha_corte_operacional_representatividad(
        start_date=start_date,
        end_date=end_date,
    )
    if fecha_corte is None:
        raise RuntimeError(
            "No existe una fecha operacional cerrada para exportar "
            "Representatividad de Torres."
        )

    print(f"[RTO] Fecha corte operacional: {fecha_corte:%Y-%m-%d}")
    pasos = (
        # ... sin cambios: los tres SP en el mismo orden ...
    )

    recurso = _recurso_lock_representatividad(end_date)
    engine = _get_engine()
    with engine.connect() as conn:
        rc = conn.execute(
            _sa_text(SQL_GETAPPLOCK_REFRESCO_REP),
            {"recurso": recurso, "timeout": LOCK_REFRESCO_REP_TIMEOUT_MS},
        ).scalar()
        conn.commit()  # el lock de sesión sobrevive al commit
        if rc is None or int(rc) < 0:
            raise RuntimeError(
                "Otro proceso está actualizando la representatividad de "
                f"{recurso.split(':')[1]}. Espere a que termine y reintente."
            )
        print(f"[RTO] Lock {recurso} tomado (rc={rc})")
        try:
            for nombre_sp, mensaje, sql in pasos:
                print(mensaje)
                try:
                    with conn.begin():
                        conn.execute(
                            _sa_text(sql),
                            {"start": start_date, "end": fecha_corte},
                        )
                except Exception as exc:
                    raise RuntimeError(
                        f"Error al ejecutar {nombre_sp}: {exc}"
                    ) from exc
        finally:
            # Sin este release el lock viaja de vuelta al pool y bloquea al
            # resto hasta pool_recycle (30 min).
            conn.execute(
                _sa_text(SQL_RELEASEAPPLOCK_REFRESCO_REP),
                {"recurso": recurso},
            )
            conn.commit()

    return fecha_corte
```

Cambio respecto de hoy: una sola conexión (antes un `engine.begin()` por SP) y
el bloque `try/finally`. Cada SP sigue en su propia transacción.

### 3.2 `report_export/callbacks/reportabilidad_cb.py` — disparar al abrir

En el `import` de `report_export.report_export` (línea 13) agregar
`refrescar_representatividad_para_exportacion`. Luego, en el `else` de
`_cargar_detalle_representatividad_periodo` (líneas 768-782):

```python
    else:
-       fecha_corte_operacional = fetch_fecha_corte_representatividad(
-           start_date=ini,
-           end_date=fin,
-       )
-       if fecha_corte_operacional is None:
-           raise RuntimeError(
-               "Sin datos operacionales cerrados para el rango seleccionado."
-           )
-       fuentes = _fetch_fuentes_mensuales_torres(
-           fin,
-           fecha_corte_operacional,
-       )
+       # Mismo refresco que usa la publicación, sobre el mes que la grilla
+       # realmente muestra (_fetch_fuentes_mensuales_torres trabaja el mes de
+       # `fin`). Así el editor deja de mostrar el estado de la publicación
+       # anterior y comparte fecha de corte con lo que se va a publicar.
+       fecha_corte_operacional = refrescar_representatividad_para_exportacion(
+           start_date=pd.to_datetime(fin).date().replace(day=1),
+           end_date=fin,
+       )
+       fuentes = _fetch_fuentes_mensuales_torres(
+           fin,
+           fecha_corte_operacional,
+       )
```

El `raise` propio sobra: `refrescar_...` ya lanza `RuntimeError("No existe una
fecha operacional cerrada…")`. `generar_reporte` captura la excepción y la
muestra como `dbc.Alert("Error al cargar editor de comentarios: …")`, así que
tanto el timeout de lock como la falta de corte llegan al usuario con texto
legible.

Tras este cambio `fetch_fecha_corte_representatividad` queda sin uso en el
código vivo (§1.2 se cierra sola). Dejarla o borrarla es aparte.

### 3.3 `report_export/tests/test_refresco_representatividad.py`

El test vigente afirma "tres EXEC en orden" recorriendo `sql.split("EXEC ")`;
con el lock hay cinco sentencias, así que hay que ajustarlo. Los fakes necesitan
`scalar()`, `begin()` y `commit()`:

```python
class _Result:
    def __init__(self, valor):
        self.valor = valor

    def scalar(self):
        return self.valor


class _Conexion:
    """Registra cada sentencia; devuelve rc para sp_getapplock."""
    def __init__(self, ejecuciones=None, falla_en=None, rc=0):
        self.ejecuciones = ejecuciones if ejecuciones is not None else []
        self.falla_en = falla_en
        self.rc = rc

    def execute(self, sentencia, parametros=None):
        sql = str(sentencia)
        if self.falla_en and self.falla_en in sql:
            raise Exception("fallo simulado")
        self.ejecuciones.append((sql, parametros))
        return _Result(self.rc if "sp_getapplock" in sql else None)

    def commit(self):
        pass

    def begin(self):
        return _Contexto(self)
```

Y tres casos nuevos, además de los cuatro que ya existen:

| Test | Afirma |
|---|---|
| `test_toma_y_libera_el_applock_del_mes` | primera sentencia `sp_getapplock` con `@Resource='rep_torres_refresco:2026-07'` y `@LockOwner='Session'`; última, `sp_releaseapplock` con el mismo recurso |
| `test_lock_no_obtenido_aborta_sin_ejecutar_sp` | con `rc=-1`: `RuntimeError` mencionando el mes, y **ningún** `EXEC` de los tres SP en la bitácora |
| `test_libera_el_lock_aunque_falle_un_sp` | con `falla_en=sp_refrescar_representatividad_torres`: `RuntimeError` con el nombre del SP **y** `sp_releaseapplock` presente |

Los cuatro tests actuales siguen valiendo; solo hay que actualizar el filtro de
`ejecuciones` para ignorar las dos sentencias de lock antes de comparar el orden
de los tres SP.

---

## 4. Qué queda validado y qué no

**Validado** (motor falso, `scratchpad/check_applock.py`, los 3 escenarios pasan):
el orden de sentencias en el camino feliz, que un `rc < 0` aborta sin ejecutar
ningún SP, y que el `finally` libera el lock aunque falle un SP intermedio.

**Pendiente de verificar contra la base** — no se puede resolver desde el repo
porque el DDL de los tres SP **no está versionado** (`docs/stored_procedures/`
solo tiene los de lectura):

1. ¿Son idempotentes y está su DELETE/INSERT acotado al rango recibido? Si
   alguno reescribe la tabla completa, la clave de lock por mes no alcanza y hay
   que serializar globalmente.
2. ¿Cuánto tardan sobre un mes cerrado? Define si `LOCK_REFRESCO_REP_TIMEOUT_MS
   = 180_000` (3 min) es holgado o corto. No hay ninguna medición en el repo: los
   `print` no llevan timestamp.
3. ¿Alguno abre transacción propia con `BEGIN TRAN` explícito? Cambiaría el
   comportamiento del `with conn.begin()`.

Consulta que lo responde (solo lectura):

```sql
SELECT o.name, m.definition
FROM sys.sql_modules m JOIN sys.objects o ON o.object_id = m.object_id
WHERE o.name IN ('sp_calcular_resumen_intervalo_totTM',
                 'sp_refrescar_representatividad_torres',
                 'sp_sincronizar_bd_ton');
```

---

## 5. Límites conocidos del fix

- **Serializa, no acelera.** Cinco usuarios abriendo el mismo mes a la vez hacen
  cola: el quinto espera cuatro refrescos. Se podría saltar el refresco cuando
  `sp_getapplock` devuelve `1` (concedido *después* de esperar, o sea que otro
  acaba de refrescar el mismo rango), pero eso deja un hueco: si ese otro falló
  y revirtió, se leería data vieja en silencio. Requiere una marca de éxito
  persistida — infraestructura que hoy no existe. **Upgrade path, no ahora.**
- **Abrir el editor pasa a escribir en producción.** Es un clic explícito
  ("Editar comentarios"), no un render de página, pero es un cambio de contrato:
  una acción que hoy es de solo lectura deja de serlo.
- **Rangos personalizados que cruzan meses**: la clave de lock sale del mes de
  `fin`, igual que los datos que la grilla arma. Un rango que empieza el mes
  anterior refresca solo el mes de `fin`; los días previos quedan como estén. Es
  el comportamiento que la grilla ya tiene al leer, no una regresión.
- **Publicar sigue refrescando por su cuenta.** Sesión típica (abrir editor →
  publicar) corre la cadena dos veces. Es correcto y es la garantía de que lo
  publicado es fresco; saltárselo exige la misma marca de estado del primer punto.
- El lock no protege contra un `EXEC` manual desde SSMS que no lo tome. Nada lo
  hace, salvo mover el `sp_getapplock` dentro de los propios SP.

---

## 6. Estado real de aplicación

El orden sugerido era lock primero, disparo después. Se hizo al revés por
decisión explícita: **§3.2 aplicada el 2026-08-03, §3.1 pendiente como deuda.**

### Lo que ya está en el código

`reportabilidad_cb.py:768`, rama `paquete=None` de
`_cargar_detalle_representatividad_periodo`, con el marcador de deuda:

```python
# ponytail: sin lock. Estos tres SP escriben tablas compartidas y ahora
# los dispara cada apertura del editor, no solo publicar/PDF: dos
# usuarios sobre el mismo mes pueden entrelazarlos ... Deuda aceptada
# 2026-08-03. Upgrade: sp_getapplock por mes, ver
# agents/FIX_refresco_representatividad_concurrencia.md
```

Tests agregados en `test_refresco_representatividad.py`:

| Test | Afirma |
|---|---|
| `test_abrir_la_grilla_refresca_el_mes_de_la_fecha_final` | la apertura llama al refresco con `(día 1 del mes de fin, fin)` |
| `test_publicar_no_vuelve_a_refrescar` | con `paquete` armado **no** se refresca de nuevo (evita duplicar la cadena al publicar) |

Suite completa: **78 passed** (76 previos + 2).

### Qué cambia para el usuario, ya en producción al desplegar

- Abrir "Editar comentarios" pasó a **escribir** en tres tablas compartidas y a
  tardar lo que tarde la cadena de refresco (sin medición previa, ver §4.2).
- El editor puede mostrar **otros días** que antes: ahora corta por `tot_TM` +
  `v_bitacora_rangos_norm`, igual que la publicación, y no por
  `v_datos_apilado_tmh_v2`. Conviene avisar a los usuarios del reporte.

### Cómo saldar la deuda

1. Correr la consulta de §4 y confirmar los tres supuestos.
2. Pegar §3.1 en `report_export.py` + los tres tests de lock de §3.3.
3. Borrar el comentario `# ponytail:` de `reportabilidad_cb.py:768` y la
   entrada §10.6b de `PROJECT_MEMORY.md`.

### Señales de que la deuda se está cobrando

Un mes cuyo Excel oficial no cuadra con lo que mostraba el editor, o valores de
BD Ton que no corresponden a la representatividad del mismo día. No hay log que
lo delate: los SP no dejan rastro de ejecución concurrente. Si aparece, subir la
prioridad del lock antes de buscar el error en el cálculo.
