# Curvas y reconciliación dentro de SIIR

La sección se abre desde el menú izquierdo, debajo de Reportabilidad. Comparte
la instancia Dash, sesión Flask, encabezado y paleta de `assets/theme.css`.
El contenido se carga al entrar en la sección; los callbacks se registran al
arrancar el servidor. No hay un segundo servidor de curvas ni un iframe.

## Archivos de integración

- `layout.py`: navegación, estado activo y breadcrumb.
- `tabs/tab_curvas.py`: puente de la sección.
- `assets/curvas_recon.css`: estilos encapsulados con variables SIIR.
- `curvas_recon/`: interfaz modular y motor actual, con imports relativos.

La conexión se obtiene de `db_connection.get_engine()` del dashboard SIIR.
Opcionalmente `RECON_SQLALCHEMY_URL` selecciona otra conexión y
`RECON_SQL_SCHEMA` otro esquema. Los casos oficiales se leen desde
`HIDRO_SIIR_DB.hidro` (o `RECON_HIDRO_SCHEMA` completo); por defecto
`SQLSERVER_DB` con sufijo `_PROD` implica `PROD_SIIR`, el resto `DEV_SIIR`.
No se distribuye un `.env` en este paquete. Las dependencias de cálculo ya
están en `requirements.txt` de SIIR.

Las tablas de reconciliación deben existir previamente. Navegar por la sección
no crea ni modifica tablas. **Ejecutar cálculo** conserva el comportamiento
del dashboard original: calcula y guarda la corrida. **Actualizar datos**
ejecuta la sincronización original. Ambos botones tienen efectos sobre la base
cuando se usan en la aplicación real.

La exportación de curvas puede necesitar el libro de planta; su ubicación se
configura mediante `RECON_PLANTA_XLSX`. No se incluyeron libros Excel en la
copia de integración. La pantalla de reconciliación funciona sin ese libro;
si se solicita una exportación sin el insumo, se muestra un mensaje.

## Rampa de pilas nuevas

El día de rampa se calcula desde el inicio real de la campaña, sin reiniciarlo
al cambiar de semana. La rampa cruza ventanas durante sus primeros 30 días.
El historial conserva cierres por ventana, permite repetir una ventana y
descarta estados posteriores si cambia un cierre anterior. Los residuos se
redistribuyen exclusivamente entre pilas en régimen y respetan límites diarios.

El historial de continuidad todavía reside en memoria del proceso. Para
recuperarlo tras reiniciar, deben reconciliarse las ventanas cronológicamente.
La continuidad entre distintos workers requiere persistencia del estado;
esa ampliación no está implementada. El prototipo debe validarse con este
límite antes de un despliegue con múltiples workers.

## Verificación local

`python -B -m unittest test_integration -v` comprueba inicio sin SQL,
autenticación, menú y retorno a Reportabilidad, montaje dinámico sin colisiones,
error de carga con reintento y registro idempotente de callbacks.

`python -B -m pytest curvas_recon/test_integration_module.py -q -p no:cacheprovider`
comprueba import seguro, guardas de callbacks, reintento y conexión inyectable,
y que la validación de esquema sea solo lectura.

`python -B -m unittest discover -s curvas_recon -p test_ramp_regression.py -v`
comprueba las siete regresiones de rampa en este repositorio. Las verificaciones no ejecutan casos
contra SQL Server ni sustituyen la revisión visual y validación con datos reales.

La copia histórica `../curvas_recon/integracion_siir/preview_integration.py`
permite una vista previa offline en `http://127.0.0.1:8059`, con datos de ejemplo,
SQL bloqueado y botones de escritura deshabilitados. No refleja automáticamente
los cambios posteriores de este repositorio ni forma parte de producción.

Para ejecutar la aplicación real, mantener la configuración SIIR existente y
arrancar `python main.py` como antes. Los archivos originales de autenticación,
Reportabilidad, conexión, plantillas Excel y configuración se conservan.


## Actualización del 11 de octubre de 2026

Pull integrado: origin/main 4844237, merge local b691766, sin push. Se
preservaron todas las secciones nuevas y los cambios locales de integración.
La apertura carga solo Casos oficiales; el histórico completo se difiere al
cálculo. Las consultas de frescura se ejecutan con Actualizar datos.

El Python por defecto de esta máquina es 3.14. Faltaba passlib de las nuevas
dependencias de autenticación: se instaló passlib==1.7.4, declarado en
requirements.txt. Las pruebas offline sustituyen el chequeo SQL de arranque
y las conexiones crudas usadas por otros paneles únicamente en el fixture;
main.py conserva su validación real de arranque.

## Curvas: integración y reporte — 20/10/2026
Se separó el contrato de flujos de los modelos 120 y 125, validando código, versión y cantidad. El catálogo oficial se consulta sin caché; las anclas se identifican por run. La descarga valida Caso/run/ventana/modelo para rechazar resultados desactualizados.
SQL y caché respetan el rango solicitado. Los 60 días corresponden al margen previo de química, nunca al límite de la campaña. El reporte conserva la historia desde el inicio de campaña, acota apilado al corte y reutiliza la lectura de riego. Se probó una campaña de más de 1000 días. Excel de planta opcional, descarga repetible durante TTL y limpieza de temporales incluso al fallar el envío.
115 pruebas pasaron. La optimización reduce lecturas y caché; no elimina el costo del motor. El reporte consulta fuentes históricas al exportar: no congela todas en una instantánea. No se cambió la rampa ni se implementó un nuevo balance de inventario. main.py, recon_engine.py y tabs/tab_curvas.py se preservaron. Sin escrituras DB ni SP, sin commit ni push. Los payloads internos de DB no se copiaron a estas notas ni al directorio de diagnósticos.

## Reporte de curvas y hoja Prod — 20/10/2026
Se adaptó el escritor al formato de recuperaciones de la referencia del 12 de octubre: cabeceras distintas por pad (OX curva desde fila 10; SU desde fila 11), Arial y colores de referencia, cuatro hojas existentes más Prod. Prod contiene Cu neto diario reconstruido por pila, con fechas desde el inicio de su campaña; no representa cátodos. Las sumas diarias coinciden con Aporte Parcelas. Recuperación máxima usa el máximo de la curva y el aporte conserva el acumulado terminal. Lector reconoce parcelas por identificador, excluye encabezados de las curvas y conserva huecos internos. Gráficos separados para evitar superposición.
Indicación explícita del usuario: algunas curvas de la referencia suman varias pilas; esa agrupación se utiliza SOLO para la comparación externa, nunca como regla del reporte. Reporte/Prod y sus series continúan individuales por pila. Los archivos de contraste y la salida Excel quedan en la carpeta de trabajo; no se copian payloads internos DB al repositorio.
Validación: 119 pruebas offline pasaron y se verificaron las cinco hojas, cuatro gráficos, referencias de series y sumas de Prod con el escritor real. Prueba de motor online fue SELECT-only; no se ejecutó callback de persistencia ni SP. main.py no se modificó. Sin commit ni push.


## Sulfuros menores de 30 dias — 03/11/2026

El selector de metodologia incorpora el ensayo neto local: solo jovenes ajustables,
maduras con recuperacion observada y mes anterior protegido. Disponible con
fuentes capturadas del Caso 10009/run10082; perfil de referencia2348. No guarda
este ensayo en SQL. El metodo anterior sigue seleccionable y conserva su guardado.
Contrato, fuentes, limites fisicos y pruebas: [METODO_SULFUROS_MENORES_30](docs/METODO_SULFUROS_MENORES_30.md).
