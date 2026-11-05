# Reconstitución de módulos mediante asignación secuencial y densidad recalibrada

Fecha del documento: **5 de noviembre de 2026**.

**Estado:** metodología acordada y prototipo preparado para integración. Las evidencias numéricas citadas corresponden a una captura DB y pruebas locales del 4 de noviembre de 2026. El reemplazo de la metodología del dashboard **todavía no está aplicado ni aprobado como implementación terminada**.

## 1. Objetivo y alcance

Distribuir el material apilado entre módulos y turnos, conservando los totales de masa del Caso seleccionado. La asignación sigue una secuencia: cada módulo recibe material hasta alcanzar su meta húmeda y el residual pasa al siguiente.

Las entradas operacionales deben proceder de la **base de datos**. No se utilizarán masas objetivo copiadas del Excel M&R ni una densidad nominal constante tomada de ese reporte.

La propuesta reproduce el principio de recalibración global y asignación secuencial discutido con el usuario. No implica que todos los detalles internos de M&R hayan sido acreditados ni que ambas implementaciones deban producir resultados idénticos con fuentes diferentes.

En Spence, OX/Óxidos y SU/Sulfuros son nombres heredados de los PAD. Se apila el mismo mineral; estos nombres no justifican asumir densidades o comportamientos distintos por mineralogía.

## 2. Decisiones acordadas

1. Usar datos DB para volúmenes, masas, humedad, identidades y módulos fijados.
2. Recalibrar la **densidad húmeda**, por PAD y campaña, hasta el cierre del Caso.
3. Conservar los módulos ya fijados y acreditados en DB.
4. Seguir el suministro desde el nacimiento de la campaña; no empezar a llenar nuevamente los módulos al inicio de cada semana o Caso.
5. Dentro de la ventana del Caso, conservar las TMS reconciliadas del PAD y su distribución diaria/por turno vigente.
6. Asignar secuencialmente TMH y la fracción correspondiente de TMS.
7. No utilizar el volumen final ni la masa final futura del último módulo abierto.

## 3. Unidades y variables

| Símbolo | Significado | Unidad |
|---|---|---|
| \(W\) | Masa húmeda | TMH |
| \(D\) | Masa seca | TMS |
| \(V\) | Volumen | m³ |
| \(h\) | Humedad en base húmeda, expresada como porcentaje | % |
| \(\rho_h\) | Densidad húmeda de recalibración | TMH/m³ |
| \(c\) | Campaña, identificada junto con su PAD | — |
| \(t_c\) | Fecha final del Caso / corte del cálculo | fecha operacional |
| \(F\) | Conjunto de módulos fijados al corte | — |
| \(A\) | Conjunto de módulos ajustables al corte | — |

Con humedad porcentual válida:

\[
D = W\left(1-\frac{h}{100}\right)
\]

Esta conversión se usa para el perfil **medido**. No se aplica nuevamente a una TMS ya reconciliada.

La columna `disponible_rotopalas.densidad` contrastada en las evidencias corresponde a **TMS/m³**. No debe utilizarse directamente como densidad húmeda.

## 4. Fuentes de datos

Los nombres completos dependen del esquema configurado por la aplicación. Las fuentes identificadas son:

| Fuente | Uso |
|---|---|
| `<SIIR_SCHEMA>.control_apilado_diario` | Fecha, PAD, campaña visible y técnica, módulo, volumen diario, volumen acumulado y volumen total estimado. |
| `<SIIR_SCHEMA>.modulo` | Identidad física del módulo y parcela. |
| `<SIIR_SCHEMA>.v_datos_apilado_tmh_v2` | Perfil de TMH de correas para el tramo histórico aplicable. |
| `<SIIR_SCHEMA>.v_contingencia_totalizador_resuelto_turno` | Perfil resuelto por correa y turno para el tramo aplicable. |
| `fn_humedad_resuelta_tm_turno_test` | Humedad resuelta del perfil por fecha/turno/correa; utilizada mediante SELECT. |
| `<HIDRO_SCHEMA>.recon_caso` | Identidad y fechas del Caso. |
| `<HIDRO_SCHEMA>.recon_caso_oficial` | Run oficial asociado al Caso. |
| `<HIDRO_SCHEMA>.recon_solver_run` | Estado e identidad del run. |
| `<HIDRO_SCHEMA>.recon_modelo` | Modelo, versión y número de flujos. |
| `<HIDRO_SCHEMA>.recon_resultado_flujo` | Masa y fino reconciliados de los flujos de apilamiento. |
| `reclamo.v_modulo_base` | Estado de congelamiento, fechas e identidad de módulos fijados. |
| `<SIIR_SCHEMA>.disponible_rotopalas` | TMH fijada directa, cuando exista y corresponda a la misma identidad. |

Para el modelo **`hidrometalurgia_125_v2`**, el contrato vigente de apilamiento es:

| PAD | Flujo de masa apilada |
|---|---|
| PAD1 / OX | F18 |
| PAD2 / SU | F19 |

Estos flujos son de apilamiento. No deben confundirse con las transferencias de solución F25/F29 usadas en el balance de Cu de las curvas de recuperación.

El cálculo propuesto no requiere ejecutar SP, publicar resultados SQL ni modificar el solver.

## 5. Identidad y período de cálculo

La identidad debe conservar, como mínimo:

`PAD + campaña técnica + campaña visible + parcela + módulo físico`.

El número visible de módulo no basta. Un módulo físico puede reutilizarse entre campañas; tampoco deben mezclarse campañas visibles distintas por compartir un identificador técnico en datos históricos.

Antes de calcular, se comprueba que el Caso, el run oficial exitoso, el modelo y las fechas coincidan. Si cambió el run oficial, el resultado anterior deja de representar la selección vigente.

Hay dos intervalos diferentes:

- **Historia de asignación:** desde el nacimiento de la campaña hasta el corte. Determina cuánto material llevaba cada módulo antes del Caso.
- **Ventana presentada del Caso:** desde `fecha_inicio` hasta `fecha_fin`, ambas fechas operacionales incluidas. Se muestran las asignaciones de ese intervalo.

La convención operacional actual es:

- Día de fecha \(d\): desde \(d\) a las 08:00 hasta \(d+1\) a las 08:00.
- TA: 08:00–20:00.
- TB: 20:00–08:00 del día siguiente.

Si falta historia anterior, solo puede sustituirse por un acumulado inicial explícito y acreditado. No se asume cero porque la ventana del Caso comience más tarde.

## 6. Perfil común de masa global

La correa mide masa húmeda. El perfil global de cada fecha y turno se obtiene sumando las corrientes válidas, sin duplicarlas por PAD.

Cuando no existe una medición directa por PAD/campaña, se utiliza una fracción común del volumen diario observado:

\[
s_{p,c,d}=\frac{V_{p,c,d}}{\sum_{p,c} V_{p,c,d}}
\]

\[
W_{p,c,d,\tau}=s_{p,c,d}\,W_{global,d,\tau}
\]

El mismo criterio proporciona la TMS histórica medida anterior al Caso.

**Supuesto:** dentro del día, la masa por unidad de volumen es homogénea entre los destinos considerados. Esta es una hipótesis de asignación; no transforma el reparto calculado en un pesaje directo por módulo o PAD.

Ambas metodologías de una comparación deben recibir la misma masa global y conservar explícitamente cualquier masa no asignable. No se permite modificar el total de entrada para mejorar la coincidencia modular.

## 7. Qué significa un módulo fijado

La selección propuesta se respalda en el estado persistido **`CONGELADO`**, con identidad válida y fechas de congelamiento y cierre no posteriores al corte.

Para descontar su masa del balance húmedo se requiere **TMH fijada directa** y atribuible a esa identidad. Tener solamente `tms_conformado` no equivale a conocer TMH.

No se reutilizan masas o densidades de otra campaña. Tampoco se interpreta el avance cercano a 100 % como prueba suficiente de congelamiento.

Se deben conservar las metas húmedas de los módulos fijados. Si existe TMS conformada, la asignación resultante debe contrastarse también con ella. Una incompatibilidad debe bloquear el resultado y explicarse; no se corrige alterando silenciosamente el módulo fijado.

La presencia de un estado congelado con masa o fechas faltantes no permite tratar ese módulo como ajustable sin advertencia.

## 8. Recalibración de densidad

Para un PAD/campaña al corte:

\[
W_{fijo}=\sum_{m\in F} W_m^{fijado}
\]

\[
V_{ajustable}=\sum_{m\in A} V_m^{real}(t_c)
\]

\[
\boxed{\rho_h=\frac{W_{global,campaña}(t_c)-W_{fijo}}{V_{ajustable}}}
\]

`W_global,campaña` es la TMH atribuida a la campaña desde su nacimiento hasta el corte, no únicamente la TMH de la semana seleccionada.

El volumen del denominador es el **volumen real observado hasta el corte**. Incluye el volumen parcial del módulo abierto y excluye el volumen de los módulos fijados descontados en el numerador.

### Casos particulares

| Situación | Tratamiento |
|---|---|
| No hay módulos fijados | \(W_{fijo}=0\); se calibra con toda la masa y volumen ajustables. |
| Todos están fijados y el balance cierra | No hace falta calcular una nueva densidad. |
| Masa fijada mayor que masa global | Error de balance o de identidad. |
| Masa por asignar positiva y volumen ajustable nulo | Error; no se inventa densidad. |
| Masa global explícitamente cero | Conservar cero; no crear material. |

La densidad puede cambiar al actualizar el corte o los datos. Recalibrar no significa modificar los módulos fijados. Los módulos aún ajustables sí pueden cambiar respecto de una evaluación anterior.

## 9. Metas húmedas de los módulos ajustables

Para un módulo cuya meta pueda utilizarse al corte:

\[
W_m^{objetivo}=\rho_h\,V_m^{objetivo}
\]

Hay que distinguir:

- **Volumen real acumulado:** usado para calibrar la densidad.
- **Volumen objetivo del módulo:** usado para determinar cuándo pasa el suministro al siguiente módulo.

El prototipo toma el volumen objetivo de `vol_total_est`, obtenido de `volumen_total_estimado_m3` en la última fila disponible hasta el corte. Su semántica y vigencia deben confirmarse antes de considerar terminado el despliegue.

Filtrar una fila por su fecha operacional no demuestra cuándo se cargó o modificó su valor en DB. La captura disponible refleja los valores actuales asociados a esas fechas; no acredita una versión histórica inmutable de cada revisión topográfica.

No se intercambian automáticamente volumen estimado, volumen acumulado y volumen final observado: pueden diferir.

**Último módulo abierto:** recibe el residual y queda parcial. No se utiliza un volumen final observado después del corte para obligarlo a cerrar.

La detección de ese último abierto debe ser coherente con la secuencia operacional. Inferirlo solo por el número de módulo más alto o por su última actividad es una aproximación del prototipo, pendiente de validación para secuencias que cambian de parcela o reinician numeración.

## 10. Asignación secuencial por turno

Para un turno con \(W_\tau\) TMH y \(D_\tau\) TMS, y un módulo que ya acumula \(W_m^{previo}\):

\[
P_m=\max(0,W_m^{objetivo}-W_m^{previo})
\]

\[
W_{m,\tau}=\min(P_m,W_\tau^{restante})
\]

\[
f=\frac{W_{m,\tau}}{W_\tau^{restante}}
\qquad
D_{m,\tau}=f\,D_\tau^{restante}
\]

Se descuentan ambas masas del turno y se continúa con el siguiente módulo. Si se completa la meta a mitad del turno, el residual pasa inmediatamente al siguiente; no espera al turno siguiente.

La TMS sigue la misma fracción de TMH del material tomado de ese turno. No se aplica una densidad seca histórica ni una nueva corrección de humedad sobre la TMS reconciliada.

### Ejemplo didáctico

Un turno entrega 40 TMH y 38 TMS. Al módulo actual le faltan 10 TMH:

| Destino | TMH | TMS |
|---|---:|---:|
| Módulo actual | 10 | 9,5 |
| Siguiente módulo | 30 | 28,5 |
| Total | **40** | **38** |

El ejemplo ilustra la aritmética; no corresponde a un registro de planta.

## 11. TMS del Caso e historia anterior

Antes del Caso, la TMS procede del perfil medido de TMH y humedad.

Dentro del Caso, prevalece la masa seca reconciliada del PAD. Su distribución diaria y por turno se obtiene del perfil operativo mediante la metodología vigente de distribución del Caso.

Por tanto, la TMS por turno presentada es una **distribución del total reconciliado**, no un resultado del solver reconciliado independientemente para cada turno.

Si coinciden varias campañas en un PAD durante un día, la TMS del PAD/turno se reparte entre ellas utilizando la fracción de volumen diario correspondiente. La suma de módulos y campañas debe reproducir el suministro del PAD/turno.

No se reescala toda la historia anterior para hacer cerrar el Caso actual. Se reconstruye el estado histórico y se cambia la fuente de TMS únicamente en la ventana evaluada.

## 12. Horas de cambio y gráfico

La masa determina qué fracción del turno corresponde a cada módulo. Esa fracción se convierte en una hora estimada utilizando el perfil temporal disponible.

Con un perfil uniforme de respaldo, para un turno que comienza en \(t_0\):

\[
t_{cambio}=t_0+12\,h\;\frac{W_{acumulado\ dentro\ del\ turno}}{W_{turno}}
\]

El prototipo de adaptación revisado utiliza interpolación uniforme de 12 horas. Aunque admite una entrada intraturno, **no está acreditado que utilice los datos de 10 segundos** en esta nueva rama. No debe presentarse con esa precisión.

El gráfico y las tablas deben construirse desde las nuevas asignaciones de masa. No deben volver a repartir por volumen al dibujar, pues eso desharía el cambio metodológico.

También deben conservarse los volúmenes observados de módulos con asignación calculada cero y las asignaciones calculadas a módulos sin una fila volumétrica ese día. La unión de datos no puede eliminar ninguna de esas situaciones.

## 13. Ceros, ausencias y errores

| Condición | Regla |
|---|---|
| TMH y TMS explícitamente cero | Conservar cero. |
| TMH cero y humedad ausente | La TMS del perfil es cero; no se inventa humedad. |
| TMH positiva sin humedad válida | No calcular TMS histórica. |
| Falta una correa o un turno necesario | No completar el perfil silenciosamente. |
| Fuente `SIN_RESOLVER` | Rechazar el dato para el cálculo validado. |
| Masa positiva sin volumen de destino | Conservar y reportar la masa sin asignar; no trasladarla a otra fecha. |
| Volumen sin masa medida | Mantener la masa ausente, distinta de cero. |
| Identidad ambigua o duplicada | Detener la asignación. |
| La secuencia agota sus metas y sobra material | Reportar residual; no hacerlo desaparecer. |
| Información posterior al corte | Excluirla del cálculo histórico. |

Si el Caso exige una asignación exhaustiva y existen masas no asignables, no se debe presentar como un Caso cerrado correctamente.

## 14. Invariantes de validación

### Conservación por turno

\[
\sum_m W_{m,\tau}=W_{suministro,\tau}
\]

\[
\sum_m D_{m,\tau}=D_{suministro,\tau}
\]

### Conservación del Caso

\[
\sum_{d,\tau,m\in PAD}D_{m,d,\tau}=D_{PAD,Caso}^{reconciliada}
\]

### Identidad, historia y presentación

- Caso, run, modelo y ventana coinciden con la selección.
- No se duplican masas globales al abrir varios PAD o campañas.
- Se preservan los módulos fijados y se contrasta su TMS conformada cuando exista.
- La historia anterior se utiliza para el estado acumulado, aunque no se muestre completa en la ventana del Caso.
- El último abierto no utiliza una meta futura.
- Gráfico, tabla, detalle y exportación consumen las mismas asignaciones.
- La suma de volúmenes observados se conserva aunque cambie la masa asignada por módulo.
- Los errores numéricos se comparan con tolerancias explícitas; no se fuerzan a cero para declarar cierre.

## 15. Referencia numérica disponible: Caso 10013

Verificación DB capturada el **4 de noviembre de 2026**:

| Concepto | Valor |
|---|---|
| Caso | 10013 |
| Run oficial | 10145 |
| Modelo | `hidrometalurgia_125_v2`, v2, 125 flujos |
| Ventana del Caso | 1–12 de octubre de 2026 |
| Campaña evaluada | PAD2, visible 12, identificador técnico 13 |
| Inicio de historia utilizado | 22 de septiembre de 2026 |
| TMS reconciliada F19 / PAD2 del Caso | **728.062,4073 TMS** |
| Masa reconciliada F18 / PAD1 | **0 TMS** |

Registro de la prueba local de recalibración:

| Variable | Valor |
|---|---:|
| TMH global de la campaña hasta el corte | 1.480.960,000 |
| TMH fijada en el snapshot | 0 |
| Volumen real ajustable | 800.692,806 m³ |
| Densidad húmeda recalibrada | **1,8495982341 TMH/m³** |
| TMS asignada en la ventana del Caso | **728.062,4073 TMS** |

La TMH global y el volumen de calibración abarcan **22 de septiembre–12 de octubre**. La TMS reconciliada de la tabla corresponde solo a **1–12 de octubre**. No deben compararse como si tuvieran el mismo alcance temporal.

Esta prueba no valida empíricamente la preservación de módulos congelados reales: el conjunto de fijados del snapshot está vacío. Ese comportamiento requiere pruebas específicas adicionales.

## 16. Estado de implementación y pendientes

### Evidencia disponible

- Asignador secuencial independiente probado previamente.
- Helper de recalibración y loader SELECT preparados y probados localmente.
- Captura real de Caso/run, perfil e historia para evaluar el prototipo sin repetir consultas.
- Registro local de cierre de masa y generación de un gráfico para el Caso 10013.

### Pendiente antes de dar por terminado el despliegue

1. Cerrar la revisión del adaptador: identidades, congelados con datos faltantes, preservación de volúmenes y tratamiento de PAD con masa cero.
2. Ejecutar la validación completa sobre la versión final del parche, no solo sobre un registro anterior del prototipo.
3. Confirmar la semántica del volumen objetivo DB y el orden operacional de los módulos.
4. Confirmar el tratamiento de módulos fijados con TMH/TMS incompatibles con el suministro por turno.
5. Aplicar el parche al repositorio activo y reiniciar el servicio.
6. Verificar el Caso autenticado en pantalla, sus detalles y exportaciones.

La coincidencia algebraica con un factor del Excel M&R no sustituye estas comprobaciones.

## 17. Archivos de referencia

Prototipo y evidencias en [`auditorias/integracion_mr_dashboard_20261104/`](../auditorias/integracion_mr_dashboard_20261104/):

- [`recalibracion_mr.py`](../auditorias/integracion_mr_dashboard_20261104/recalibracion_mr.py): fórmula, metas y validaciones de recalibración.
- [`recalibracion_db_source.py`](../auditorias/integracion_mr_dashboard_20261104/recalibracion_db_source.py): lecturas de historia y módulos fijados.
- [`recalibracion_adapter.py`](../auditorias/integracion_mr_dashboard_20261104/recalibracion_adapter.py): asignación por turno y reconstrucción de resultados.
- [`CASO_ACTUAL_DB.json`](../auditorias/integracion_mr_dashboard_20261104/CASO_ACTUAL_DB.json): Caso, run y objetivos por PAD verificados.
- [`RUNTIME_BASELINE_SNAPSHOT.json`](../auditorias/integracion_mr_dashboard_20261104/RUNTIME_BASELINE_SNAPSHOT.json): captura reutilizable de datos reales.
- [`VERIFICACION_RUNTIME.json`](../auditorias/integracion_mr_dashboard_20261104/VERIFICACION_RUNTIME.json): registro de la prueba local del prototipo; no constituye acta de despliegue.

El repositorio activo de la aplicación es `../DashReportabilidadSIIR`. Los archivos de esta carpeta de auditoría son preparación y evidencia, no prueba de que el proceso del dashboard ya haya cargado el cambio.
