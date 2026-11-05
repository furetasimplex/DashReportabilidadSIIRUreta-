# Metodo "maduras fijas, nuevas moviles" (Oxidos y Sulfuros)

Generaliza el ensayo neto local que existia solo para Sulfuros y solo para el
Caso 10009 (ver `METODO_SULFUROS_MENORES_30.md`, antecedente). Vale para
cualquier Caso oficial del modelo `hidrometalurgia_125_v2` y para los dos PAD.
El resultado es LOCAL: no escribe en SQL (decision del usuario) y el cierre del
Cu neto no valida el balance de agua ni la dinamica hidraulica.

## Reglas (sin cambios respecto del ensayo original)

- Edad = dias calendario desde el primer riego real de la campana hasta el
  cierre del Caso; una clasificacion por pila para toda la ventana.
- Mayor de 30 dias (madura): conserva EXACTA la recuperacion observada.
- Menor de 30 dias (nueva): su perfil de drenaje MODELADO (run de asignacion)
  se escala por un factor comun `lambda` para cerrar el Cu neto del PAD. Riego
  y concentraciones observados no se tocan. No se inventan caudales.
- Exactamente 30 dias: conserva la recuperacion oficial (frontera protegida).
- Historia anterior a la ventana: intacta (las filas ni se anotan).
- Objetivo = `fino_cu_reconciliado` del flujo neto del PAD en el run oficial.
  `lambda = (objetivo - Cu neto de las protegidas + Cu del riego de las nuevas) /
  Cu del perfil modelado de las nuevas`, con el Cu en t (`0.024 * Q m3/h * g/L`).

## Flujo objetivo por PAD (F25 / F29)

| PAD | Flujo | Evidencia |
|---|---|---|
| SULFUROS | F29 | `db_pipeline.load_caso_anchor` (`net_target_by_label`), `utils_recon_finalv2.py` (F29 = F47+F48+F49 - (F72+F66)), docs |
| OXIDOS | F25 | `db_pipeline.load_caso_anchor`, `utils_recon_finalv2.py` (F25 = F44 - (F70+F60+F81)), `test_cierre_transferencias.py`, `FLUJO_DB_DASH_METALURGIA.md` ("objetivos F25 OX/F29 SU") |

La asignacion F25 = Oxidos esta confirmada en codigo, docs y fixture
(`curvas_recon/fixtures/modelo125_run10104.json`); NO se pudo contrastar con el
catalogo de flujos en SQL (no hay acceso). Matiz: la definicion de F25 en
`utils_recon_finalv2.py` usa solo F44 como drenaje, mientras que el mapeo de
anclas de `db_pipeline` lista el drenaje de Oxidos como F44+F45 (F45 puede ser
cero). El metodo usa el valor del flujo F25 del run, no una suma de componentes.
Solo se admite el modelo 125 v2; otro modelo falla con mensaje.

## Cargador generico (`curvas_recon/maduras_inputs.py`)

`load_pad_inputs(week_start, week_end, caso_id, label, anchor, expected_run_id=...,
previous_result=None)`; solo SELECT/WITH (cada sentencia se verifica antes de
ejecutar). Una lectura por fuente y PAD, en una sola conexion:

1. Identidad: `recon_caso` + `recon_caso_oficial` + `recon_solver_run` (exito) +
   `recon_modelo`. Exactamente un run oficial; ventana pedida == ventana del
   Caso; run == el seleccionado en pantalla; modelo 125 v2.
2. Objetivo: `recon_resultado_flujo` (F25 o F29) del run oficial; si se entrega el
   ancla, debe coincidir (valor y flujo).
3. Perfil de las nuevas: `reconciliacion_run` del mismo Caso y ventana exacta
   (el mas reciente, que convergio) y `reconciliacion_detalle_dia.q_pls`. Ese
   run no guarda el `solver_run_id` de origen: se une por Caso y ventana y
   queda registrado en `source_ids`. El universo de pilas es el de ese run.
4. Recuperacion: `Recuperaciones_pad` (primaria; oficial y observada coinciden
   en esta fuente, `observation_source` lo declara), campana vigente al cierre.
   Se carga desde el primer dia del mes anterior (historia protegida visible).
5. Cu apilado: `SUM(Finos_cut)` de `modulos_turnos` por pila/campana. Primer
   riego: primer dia con `caudal_m3h > 0` (consolidada UNION ingesta) desde el
   primer apilamiento de la campana.
6. Riego, Cu de riego y Cu de drenaje de la ventana: tabla consolidada manda en
   las fechas que cubre; la vista de ingesta rellena fechas completas
   (mismo criterio que `recon_engine.load_riego/load_drena_cu`).

Sin respaldo silencioso. Falla con causa (`MadurasInputError`) si: no hay run
oficial, ventana o modelo distintos, falta F25/F29, no hay run de asignacion
(la opcion no ejecuta ni guarda nada para crearlo), no convergio, pila con riego
fuera del run de asignacion, campana sin Cu apilado, dos campanas con
recuperacion dentro de la ventana, o faltan recuperacion / riego / Cu /
perfil de una nueva en algun dia. Unica exclusion permitida y explicita: pila
del run sin campana ni recuperacion (riego permanente, p. ej. P32 de Oxidos);
queda en `metadata.excluded_piles` y no entra al cierre (su Cu neto no tiene
curva de recuperacion).

`curvas_recon/sulfide_inputs.py` conserva el paquete congelado del Caso 10009
(`test_fixtures/caso10009_*`) como fixture de regresion; comparte el validador
`validate_payload`. Su verificacion SHA-256 normaliza saltos de linea (los
hashes se tomaron con CRLF; un checkout LF daba falso "hash mismatch").

## Casos borde (`curvas_recon/maduras_nuevas.py`)

- Pila que nace a mitad de ventana: su perfil y su curva empiezan en su primer
  riego; no se exigen ni se rellenan filas anteriores. Linea base: la fila
  oficial del dia anterior si existe; si no, 0 % (`campaign_birth_zero`,
  declarado en la auditoria). Filas medidas previas al nacimiento dentro de la
  ventana se conservan como oficiales.
- Edad exactamente 30: oficial protegida (`exact_30_pending`). 29 es nueva, 31
  madura.
- Infactibilidad (`InfeasibleError`, sin cambiar de metodo): sin nuevas y
  protegidas que no cierran; perfil sin Cu; `lambda` bajo/sobre las cotas
  provisionales `LAMBDA_BOUNDS = (0.2, 5.0)` (no calibradas; parametro
  `lambda_bounds`); `Qd > Qr` (tope `lambda <= min Qr/Qd_perfil`). El mensaje da
  el `lambda` requerido, la pila/dia que limita y el rango de Cu neto alcanzable.
- Encadenamiento: `reconcile_chain` (o `previous_result=` del cargador) exige
  Casos consecutivos, usa la recuperacion final del Caso anterior como linea
  base (`baseline_source = previous_case_result`), protege su historia y
  resuelve el `lambda` propio de cada Caso. Desde la UI cada Caso se calcula por
  separado con la linea base de SQL; el encadenamiento automatico entre
  corridas locales de la UI queda pendiente.

## Interfaz para reportes

```python
from curvas_recon.maduras_nuevas import direct_recovery_series
series = direct_recovery_series(res)          # res = joint['res'] o raw['res']
# {('OXIDOS'|'SULFUROS', num_pila): pandas.Series(fecha -> recuperacion %)}
```

Funcion pura. Indice `DatetimeIndex` (`date`), ordenado; incluye la historia
protegida (`case_only=True` recorta a la ventana). Valor = `reconciled_pct`:
observado en maduras, oficial en frontera e historia, ajustado en nuevas.
`with_campaign=True` usa la clave `(pad, num, campana)`; sin ella, una pila con
varias campanas lanza error. `Series.attrs`: `campaign`, `cu_apilado_t`,
`first_irrigation`, `sources` (origen por fecha). Sin resultado local devuelve
`{}`. `res['local_direct_recovery']`, `res['recovery_rows']`,
`res['maduras_audit'][pad]` (y `res['sulfide_audit']`) se mantienen.

## UI

Opcion "Menores de 30 dias: ensayo neto local" (`net_trial`, la inicial) aplica
a ambos PAD de cualquier Caso oficial; "Metodo anterior" no cambia (guarda en
SQL al calcular). Cambiar de opcion limpia resultados sin calcular. Un fallo de
fuentes o una infactibilidad se muestra en el modal de error; no se vuelve al
metodo anterior. Los graficos, grupos y el XLSX (`Recuperacion Sulfuros` /
`Recuperacion Oxidos`) usan la recuperacion directa de cada PAD.

## Pruebas offline

`python -m pytest -q curvas_recon/test_maduras_nuevas.py curvas_recon/test_maduras_inputs.py curvas_recon/test_maduras_dashboard.py curvas_recon/test_sulfide_method.py curvas_recon/test_sulfide_inputs.py curvas_recon/test_sulfide_dashboard.py`

Cubren cierre exacto del objetivo, maduras sin cambios, historia protegida,
nacimiento en la ventana, edad 29/30/31, infactibilidad, ambos PAD,
encadenamiento, regresion del Caso 10009 (`lambda = 0.7214427195956585`, cierre
1069.137402 t) y el cargador con SQL simulado (solo SELECT; `Engine.connect`
real bloqueado).

## No verificado sin SQL

Nombres y semantica de columnas se tomaron de los scripts de captura y del
codigo existente (`modulos_turnos.pad_id` = `material.id`; `Recuperaciones_pad`
como serie primaria; `reconciliacion_run.converged`). No se ejecuto contra
SQL Server: queda pendiente una pasada SELECT real que reproduzca el Caso 10009
con el cargador generico y compare con el paquete congelado, y que pruebe un
Caso con Oxidos (P32 y similares). Las cotas de `lambda` son provisionales.
