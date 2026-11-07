# Sulfuros menores de 30 dias: ensayo neto local

Contrato aplicado el 3 de noviembre de 2026 al repositorio activo
DashReportabilidadSIIR. Es un cambio de metodologia y presentacion de curvas.

## Uso y alcance

En Curvas > Reconciliacion, seleccionar Caso 10009, ventana 1–7 de septiembre
de 2026, y «Menores de 30 dias: ensayo neto local». Es la opcion inicial.
Ejecutar calculo valida el run oficial vigente contra el paquete de fuentes;
no actualiza resultados SQL para este ensayo. Conserva el resultado completo
en la cache local ya existente y permite descargar un XLSX con recuperaciones,
flujos disponibles y auditoria. La cache local tiene el TTL/limpieza existente:
el XLSX permite conservar evidencia fuera de ella.

El selector «Metodo anterior» conserva el calculo y guardado SQL anteriores.
Cambiar de metodologia limpia los resultados visibles sin ejecutar calculos.
No se altera Oxidos: usa su motor actual; cuando se combina con el ensayo,
el resultado conjunto tambien queda local para no persistir una corrida parcial.

El cargador nuevo contiene exclusivamente un paquete capturado e identificado
del Caso 10009, no un conector SQL generico. Otros casos, ventanas, objetivos o
runs requieren sus fuentes validadas; se rechazan sin recurrir silenciosamente
al metodo anterior. El nucleo puro admite otras ventanas de un mismo mes con
baseline oficial del dia anterior y cierre del mes previo.

## Reglas

- Edad: dias calendario transcurridos desde el primer riego real de la campana
  hasta el cierre del Caso; una clasificacion por pila para toda la ventana.
- Pila nueva (edad de 30 dias o menos, incluido exactamente 30): ajustar el caudal del perfil modelado guardado por un factor
  comun lambda, manteniendo riego y concentraciones observadas; se exige
  cobertura completa y se comprueba el cierre del Cu neto de la ventana.
- Mayor de 30 (madura): recuperacion observada exacta, sin redistribuirle residuos.
- Exactamente 30 dias es pila nueva (decision del usuario; coincide con `MAX_YOUNG_AGE_DAYS = 30` y con
  `test_exactly_30_days_is_adjustable`).
- Historia anterior a la ventana: sin modificaciones en meses calendario anteriores al mes de fecha_fin del Caso
  (dias cerrados). Un Caso que empieza a mitad de mes puede ajustar, solo en pilas nuevas, los dias del mismo mes
  previos a su ventana (vida abierta desde max(primer riego, primer dia del mes)); las maduras solo la ventana.
  Esos dias son de un Caso anterior: `closed_days_check` (`curvas_recon/reconciliacion_pad.py`) lo lista en
  `casos_invalidados` (recalcular) y sus sucesores en `sucesores_afectados`. Datos de esos dias: riego, Cu de riego
  y Cu de drenaje medidos (`build_sulfide_rows(open_from=...)`) y el perfil de drenaje guardado si existe, si no el
  plano marcado como modelado; si faltan se rechaza con error, no se inventan. El cierre es un parametro explicito
  (por defecto primer dia del mes de fecha_fin, declarado en la salida).
- No se inventa caudal de drenaje de maduras a partir de su recuperacion.
  Los caudales desconocidos y agregados incompletos se conservan como nulos.
- El techo Qd <= Qr es una restriccion de este escenario, no una ley hidraulica
  general. Sin jovenes, solo hay resultado si las pilas protegidas ya cierran.

Una pila que empieza a regarse a mitad de la ventana aun requiere ampliar el
contrato de dias anteriores a su nacimiento; el nucleo actual falla por falta
de cobertura, sin rellenar mediciones. No extrapolar las rampas a 30 dias.

## Fuentes y comprobacion

Paquete versionado `test_fixtures/caso10009_sulfuros_net_inputs.json`, verificado
por SHA-256. Identidades separadas: run oficial del balance 10082 y perfil de
asignacion guardado 2348. No esta demostrada una asociacion automatica entre
ambos runs. El objetivo F29 es 1069.137402 t Cu neto. Contiene 18 campanas/pilas
de Sulfuros y siete dias de septiembre. Un CSV complementario verificado por
SHA-256 conserva 514 filas primarias de agosto; resultado total: 640 filas.
El grafico conserva tambien el contexto medido de campana anterior a agosto
si esta cargado, identificado como medido y separado del paquete congelado.

La fuente primaria y lectura_recuperacion difieren en 377 filas historicas del
estudio previo; este paquete explicita la fuente primaria elegida y no afirma
equivalencia entre ambas. Cu apilado corresponde a toneladas de cobre contenido,
no a una ley. La hoja Fuentes y alcance conserva las referencias y hashes.

Caso 10009: P24/P25 ajustables, otras 16 en observacion. Lambda:
0.7214427195956585; cierre neto: 1069.137402 t Cu. El riego menos drenaje modelado
es aproximadamente 19510 m3: es un balance por explicar, no almacenamiento
medido. Se conserva ese diagnostico por pila en la auditoria.

El cierre contable de Cu no valida el balance de agua, la impregnacion ni la
dinamica hidraulica. La recuperacion observada y el Cu neto extraido del mineral
pueden diferir por cambios en el inventario de solucion.

## Verificacion offline

`python -B -m pytest curvas_recon/test_sulfide_method.py curvas_recon/test_sulfide_inputs.py curvas_recon/test_sulfide_dashboard.py curvas_recon/test_integration_module.py -q -p no:cacheprovider`

Pruebas de identidad/hash, cobertura, historia protegida, edad 30, ventanas
posteriores, infactibilidad, cierre independiente por recuperaciones, graficos,
grupos, XLSX y serializacion del callback. La persistencia SQL esta bloqueada
en pruebas y para resultados de recuperacion directa. Los reportes antiguos
que reconstruyen recuperacion desde Q/Cu no consumen este nuevo resultado.

No se ejecutaron procedimientos almacenados ni escrituras SQL, commit o push.
