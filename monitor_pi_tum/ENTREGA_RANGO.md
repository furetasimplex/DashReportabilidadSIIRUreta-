# Contingencia PI por rango inclusivo

El modal Activar contingencia PI utiliza Desde/Hasta, cada uno con fecha y turno.
Ambos extremos se inicializan con el período puntual seleccionado. El selector
principal conserva su función de consulta y el cierre manual conserva su flujo.

## Implementación

- `db.py`: `validar_rango`, `turno_siguiente`, `expandir_turnos`,
  `obtener_preview_rango`, `_preview_rango`, `_validar_solapamiento` y
  `registrar_contingencia_rango`.
- `gestion.py`: formulario dentro del modal existente; `previsualizar_rango`,
  `presentar_preview_rango` y comprobación de que el preview corresponde a las
  fechas actuales. Se extienden los callbacks existentes, sin IDs duplicados.
- `test_rango.py`: casos de límites, consulta, solapamiento, atomicidad e identidad.
- `test_gestion.py`: adaptación al rango y validación HTTP de los nuevos callbacks.

El fin es inclusivo: A cierra en B del mismo día; B cierra en A del siguiente.
15-A a 17-B comprende seis turnos y registra el cierre en 18-A.

El preview hace una consulta parametrizada al resolvedor operacional DEV para
PRINCIPAL_CV008 y PRINCIPAL_CV108. La expansión de turnos incluye también puntos
sin filas: su disponibilidad se presenta como — / Sin información, nunca como No.
El resumen cuenta turnos con TUM completo y no completo, y detalla evaluados sin
TUM y sin información. Estas últimas categorías pueden coincidir en un turno
cuando un equipo tiene No y el otro no tiene información.

El motivo se aplica al rango entero. Otro exige comentario también al guardar.
La falta de TUM no bloquea Confirmar. Sí se bloquea por rango inválido, falta de
usuario, preview fallido/obsoleto o solapamiento. La identidad continúa siendo
exclusivamente `session['user']`.

## Persistencia y protección del historial

Se usa el engine central y una sola transacción `engine.begin()`:

1. Bloqueo `sp_getapplock`, con el mismo recurso que el cierre manual.
2. Revalidación del historial con UPDLOCK/HOLDLOCK. ROW_NUMBER conserva la última
   acción efectiva por fecha/turno; LEAD permite detectar intervalos abiertos,
   contenidos, envolventes o que cruzan el rango solicitado.
3. `sp_registrar_contingencia_pi_test`: una ACTIVAR_CONTINGENCIA al inicio.
4. El mismo SP: una CERRAR_CONTINGENCIA después del fin inclusivo, motivo NULL y
   comentario generado que identifica el intervalo.
5. `sp_mantiene_apilado_tmh_v2_test`: únicamente fechas inicio a fin inclusive,
   con DiasReproceso = DATEDIFF(day,inicio,fin)+1.
6. Commit al terminar; cualquier excepción revierte la transacción completa.

No se escriben eventos diarios ni se actualizan/borran eventos existentes.
Se rechaza también un cierre calculado que coincide con una activación existente:
insertarlo en ese punto sustituiría su efecto. El mensaje explica que debe elegirse
un fin anterior. Un cierre existente dentro del rango también lo bloquea, porque
truncaría la nueva contingencia. Una contingencia anterior cerrada exactamente
en el inicio sí permite comenzar el rango nuevo.

El estado vigente consulta la hora de Chile (Pacific SA Standard Time) y el
turno operacional 08:00–20:00 / 20:00–08:00. Así los eventos futuros del rango no
adelantan su efecto visual. El estado histórico sigue consultando su fecha/turno.
No se prohíben rangos futuros: el SP procesa las fechas existentes según su contrato;
la aplicación no inventa datos ni amplía el intervalo solicitado.

## Validación

`python -m unittest monitor_pi_tum.test_monitor monitor_pi_tum.test_gestion monitor_pi_tum.test_rango monitor_pi_tum.test_cambio_horario -q`

Resultado: 43 pruebas correctas y una prueba de lectura SQL real omitida.
Las regresiones cubren los cuatro rangos solicitados, fechas inválidas, corte,
solapamientos, fin/cierre adyacente, TUM ausente y NULL, usuario ausente, Otro,
errores de ambos eventos y reproceso, dos escrituras y un reproceso, HTTP Dash,
IDs/outputs, navegación y diagnóstico. El SELECT de solapamientos se ejecuta con
eventos en SQLite en memoria; el contrato de transacción se verifica con dobles
de prueba. Compilación Python y git diff --check correctos.

No se ejecutaron escrituras ni pruebas end-to-end contra SQL Server en esta
entrega. No se modificaron objetos SQL, PROD ni Diagnóstico de Correas.
