# Monitoreo Correas Área Seca — fase operacional DEV

## Regla crítica: cambio de horario

Los timestamps locales `datetime2` sin offset no permiten deducir horas físicas
con `DATEDIFF(HOUR, inicio, fin)`. No se usan conteos fijos de 24 lecturas por día
ni de 12 por turno, ni umbrales equivalentes, para decidir validez o completitud.
La evaluación debe respetar cobertura temporal contextualizada, fronteras
operacionales, continuidad, gaps y las reglas de negocio. Un salto de reloj
conocido no debe confundirse automáticamente con pérdida de señal.

Caso de regresión: 05-09-2026 turno B (20:00 a 08:00 local siguiente), con 11
registros horarios. La secuencia 05-09 23:00 → 06-09 01:00 no contiene medianoche;
el día calendario 06-09 tiene 23 lecturas. Esos conteos describen este caso real,
no fijan una nueva regla de completitud. No se reconstruyen puntos faltantes.

`test_cambio_horario.py` comprueba la conservación de las 11 lecturas en el
diagnóstico y, con `--dev`, consulta el caso real y verifica que OPERATIVO y
MANTENCION autoricen PI disponible sin invalidarlo por el número de muestras.
La ausencia real de PI conserva PENDIENTE_PI; no se valida el turno a ciegas.
Esta fase no redefine los diagnósticos técnicos del resolvedor oficial.

Validación DEV de la regresión: **11 registros en el turno y 23 en el día**,
con la secuencia de reloj esperada. Los siete equipos quedaron RESUELTO por PI
tanto para OPERATIVO como para MANTENCION (incluidos ceros). La prueba exige
que los siete conserven PI disponible; no basta con que pase uno de ellos.
No se insertaron declaraciones ni se modificaron objetos SQL.
Evidencia: [validacion/cambio_horario_20260905_B.json](validacion/cambio_horario_20260905_B.json).

## Implementación

La cuarta sección se llama **Monitoreo Correas Área Seca**. Se conservan
`monitor_pi_tum`, `nav-monitor-pitum`, `subtabs-monitor-pitum` y todos los IDs
anteriores. Los controles nuevos llevan `pitum-gestion-`.

Navegación:

1. Reportabilidad (inicial).
2. Administración de Reclamo.
3. Carga PowerBI Camiones.
4. Monitoreo Correas Área Seca.
   - Diagnóstico de Correas: gráfico acumulado anterior, sin cambio de metodología.
   - Gestión PI / TUM: fecha operacional, turno, estado, comentario, previsualización,
     Guardar decisión e historial del período seleccionado.

La declaración es por **fecha operacional + turno**, para los siete equipos;
no se ofrece selección manual de fuente ni declaración por tag.

### Archivos Python

Modificados en esta fase:

- `layout.py`: solo cambia la etiqueta visible respecto de la fase anterior.
- `monitor_pi_tum/panel.py`: cambia el título y monta Gestión en lugar del placeholder.
- `monitor_pi_tum/db.py`: agrega previsualización, guardado transaccional, validación
  e historial; conserva la consulta del diagnóstico.

Creados:

- `monitor_pi_tum/gestion.py`: formulario, callbacks, alertas, historial y usuario
  tomado exclusivamente de `session['user']`. Sin usuario identificado, no guarda.
- `monitor_pi_tum/operational_sql.py`: expresión SQL compartida entre la nueva
  vista y la previsualización; definición de los cuatro objetos.
- `monitor_pi_tum/inspect_dev.py`: inspección DEV y captura de definiciones protegidas.
- `monitor_pi_tum/deploy_dev.py`: genera DDL y crea los cuatro objetos en una
  transacción; rechaza objetos existentes y cualquier base distinta de DEV.
- `monitor_pi_tum/validate_operational_dev.py`: pruebas SQL con ROLLBACK.
- `monitor_pi_tum/test_gestion.py`: pruebas de identidad, formulario, validaciones,
  errores y respuesta HTTP Dash. Se conserva `test_monitor.py` de la fase anterior.

### Objetos SQL creados

Todos pertenecen al esquema `inventar_SpcHidr` de la base DEV `inventar_SpcHidr`:

1. `contingencia_estado_operacional_test`: tabla con IDENTITY, restricciones,
   fecha SQL e índice `(fecha_operacional, turno, fecha_registro DESC, id DESC)`.
2. `sp_guardar_contingencia_estado_operacional_test`: valida e inserta; no contiene
   UPDATE ni DELETE. Retorna identificador y fecha del registro insertado.
3. `v_contingencia_estado_operacional_actual_test`: ROW_NUMBER por fecha/turno,
   ordenando por fecha de registro e id descendentes.
4. `v_contingencia_totalizador_resuelto_operacional_test`: LEFT JOIN desde el
   resolvedor automático a la declaración vigente, sin reconstruir señales.

El **DDL exacto ejecutado**, incluidas las definiciones completas del SP y ambas
vistas, está en [validacion/ddl_ejecutado.sql](validacion/ddl_ejecutado.sql).
[operacional_dev.sql](operacional_dev.sql) contiene el mismo DDL para revisión.
El script de despliegue comprueba la base antes de ejecutar cada conjunto de DDL;
no se ejecutó un cambio de base ni una instrucción sobre PROD.

El SP usa parámetros de texto más amplios que las columnas para poder rechazar
comentarios/usuarios demasiado largos antes de truncarlos. La tabla mantiene
los tipos y límites pedidos. La aplicación y el SP comprueban el largo Unicode.

## Comportamiento

- OPERATIVO / MANTENCION autorizan el valor PI del resolvedor base si no es NULL,
  incluido cero. Sin PI, la resolución queda PENDIENTE_PI, con fuente y valores NULL.
- CAIDA_PI inhabilita PI. TUM disponible y no negativo resuelve por TUM, incluido
  cero, manteniendo el umbral de 100 para CV008/CV108. No se aplican factores.
- CAIDA_PI sin TUM utilizable queda PENDIENTE_TUM, con fuente y valores NULL.
  La alerta enumera equipos pendientes y **no bloquea el guardado**.
- Sin declaración se conservan fuente, valor bruto/final y motivo automáticos,
  bajo AUTOMATICO_LEGACY.
- Se conservan diagnóstico técnico, fronteras, trazabilidad TUM y valores originales.
  También se exponen `fuente_automatica`, valores/motivo automáticos e id de declaración.
- La previsualización ejecuta únicamente SELECT con el estado propuesto. Utiliza
  la misma expresión SQL que la vista, reemplazando solo la relación de declaración.
- Guardar agrega una nueva fila y refresca el historial. La pantalla no ofrece
  UPDATE/DELETE. No se persistió `fuente_resuelta`.
- El modelo append-only se aplica en el SP y en la aplicación; no se cambiaron
  permisos globales ni se impide a un administrador SQL modificar directamente tablas.

Si el resolvedor base no tiene fila para un equipo/período, la tabla de preview
lo muestra sin tonelaje y advierte que la vista operacional no tendrá esa fila
hasta que exista en la base. No se inventa una fila persistida ni una señal.

## Runtime verificado y alcance

Se verificó la ruta activa desde `main.py` y la identidad de `auth.py`.
El login escribe `session['user']`; no se usa `username` como alternativa.
Los cuatro objetos nuevos no existían antes de esta fase.
El SP de tendencia vigente ya incluye CV025, a diferencia de la inspección de
la fase anterior; no se modificó en esta fase.

**PROD no fue tocado. El resolvedor oficial no fue modificado. El balance oficial
no fue modificado. Reporte por Turno no fue modificado.** No se conectaron
consumidores oficiales a la nueva vista.

Se conservaron los cambios preexistentes en `report_export/report_export.py` y
los demás archivos ajenos a esta tarea. El arranque `main.py` no se ejecutó para
las pruebas, pues su chequeo puede inspeccionar el peer PROD. La prueba del layout
usa conexiones sustituidas y la prueba HTTP usa un servidor de prueba en memoria.

## Evidencia de validación

Consultar [validacion/resultados_operacional.json](validacion/resultados_operacional.json)
para los resultados SQL por equipo y caso. Las declaraciones de prueba se insertan
dentro de transacciones revertidas; no quedan vigentes. SQL Server puede consumir
identificadores IDENTITY aun cuando se haga ROLLBACK.

La validación de UI cubre componentes, IDs, callbacks y HTTP Dash. No equivale
a una inspección visual en navegador, que no se realizó en esta sesión.

### Resultado final

- `python -m unittest monitor_pi_tum.test_monitor monitor_pi_tum.test_gestion -v`:
  **11 pruebas correctas**. Incluyen las cuatro áreas, inicio en Reportabilidad,
  IDs sin duplicados, nombre visible, respuesta HTTP de la previsualización,
  identidad desde `user`, rechazo de `username` sin `user`, los tres guardados,
  validación previa a conectar, errores sin detalle SQL y alerta de TUM sin persistir.
- `python -m compileall -q layout.py monitor_pi_tum`: correcto.
- `git diff --check`: sin errores de espacios.
- Matriz ejecutada en SQL Server: **840 casos correctos**. Cruza los siete equipos,
  ausencia de declaración/tres estados, PI NULL/0/150, TUM NULL/-1/0/100/101 y
  disponibilidad 0/1; incluye los tres tipos TUM y conservación del diagnóstico.
- Se ejecutó el cuerpo exacto de la vista vigente sobre versiones temporales con
  igual fecha de registro: ganó el id mayor.
- **6 rechazos del SP correctos**: fecha NULL, turno inválido, estado inválido,
  usuario vacío, usuario NULL y comentario excesivo. Evidencia separada en
  [validacion/rechazos_sp.json](validacion/rechazos_sp.json).
- Casos reales: siete equipos por período. Sin declaración, coincidencia de las
  cuatro columnas de decisión con legacy; con declaración, igualdad entre
  previsualización y vista persistida. Dos inserciones por período conservaron
  ambas filas y seleccionaron la última como vigente.
- **Ocho inserciones de prueba revertidas**, comprobando el conteo inicial/final.
- Comparación final de las siete definiciones protegidas: **sin cambios**.
- Diagnóstico real del 13-09: CV008 8640 puntos/10 s; CV001 y CV025 24 puntos/3600 s.
  Los valores de Scattergl coinciden exactamente con los del SP. Evidencia en
  [validacion/diagnostico_fase2.json](validacion/diagnostico_fase2.json).

| Fecha / turno | Declaración | Equipo | PI | TUM | Fuente nueva | Valor final |
|---|---|---|---:|---:|---|---:|
| 07-09-2026 A | CAIDA_PI | PRINCIPAL_CV008 | 8960 | 6126 | TUM | 6126 |
| 07-09-2026 A | CAIDA_PI | PRINCIPAL_CV108 | 5491 | 2926 | TUM | 2926 |
| 07-09-2026 B | CAIDA_PI | PRINCIPAL_CV008 | 19130 | 16340 | TUM | 16340 |
| 07-09-2026 B | CAIDA_PI | RIPIOS_CV025 | 0 | 31387 | TUM | 31387 |
| 01-09-2026 B | MANTENCION | PRINCIPAL_CV008 | 0 | 0 | PI | 0 |
| 04-09-2026 A | OPERATIVO | PRINCIPAL_CV008 | 19994 | 19994 | PI | 19994 |

Todos estos resultados quedaron RESUELTO, con los motivos solicitados.
El JSON incluye los 28 resultados, no solo las seis filas destacadas.

### Bloqueos y límites

No quedaron bloqueos funcionales ni diferencias con los ejemplos reales.
La primera conexión dentro del sandbox falló por ODBC/SSL; las operaciones DEV
se ejecutaron con autorización fuera del sandbox. Hubo un timeout transitorio
de conexión durante el diagnóstico; el reintento completó la validación.
Las consultas a la vista base fueron lentas durante las pruebas; la previsualización
depende de ese mismo resolvedor y muestra un indicador de carga. No se modificó
el resolvedor oficial para optimizarlo. La revisión visual en navegador sigue
siendo una limitación de la validación, no una prueba realizada.
