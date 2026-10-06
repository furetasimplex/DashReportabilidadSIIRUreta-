# Segunda pasada exclusivamente visual — 05-10-2026

Cambios: bloques de parcela con relieve discreto, cards PAD compactas, título menor, hover y selección con outline sin cambiar color base. Geometría e identidades intactas. Se conserva el elemento button por accesibilidad/teclado, con apariencia de bloque físico.

Detalle: Offcanvas derecho de 400 px, máximo 100vw, con cierre, scroll propio y secciones Identificación, Estado, Ciclo hidráulico, Operación, Drenaje y Flujo. Fechas formateadas DD-MM-YYYY solo para presentación. Sin encabezado técnico de V2. Estado con etiqueta amigable; códigos/datos originales intactos.

Archivos modificados: `lixiviacion/map_panel.py`, `assets/lixiviacion_map.css`, `lixiviacion/visual_review.py`. Evidencia nueva en esta carpeta. Se agregó un callback exclusivamente visual para className/aria-pressed; `load_map` y `open_detail` conservan su lógica y firmas. No cambian consultas, fuentes, estados, cardinalidad, reglas, Diagnóstico ni shell.

Hashes SHA256 antes/después idénticos:

- db.py: `49AAE2EE028C025F0A47B30422A3C3E3BBC816694FA9894D745C6208E5743FCD`
- map_db.py: `6B975172A5B1E1257ADCDE58751C55F12004125B7B858B16B41F82CC87FCA567`
- callbacks.py: `6C6D7C32B91410C40C20B7E06114963279B35084340FF40A434198108D3077E1`
- panel.py: `3F12D248157398C83FE8DB76A0A9B80226A28860EA2FB3072B5897B9CC5A04DD`

Validación:

- `python -m pytest lixiviacion -q`: 12 PASS, sin modificar tests existentes.
- `python -m lixiviacion.visual_review`: Chrome headless local DEV, finalizado sin fallos ni errores JS. Navegación anterior y Diagnóstico comprobados.
- Desktop: 60 parcelas, SULF 28; drawer medido 400 px, una parcela seleccionada, fondo idéntico antes/después.
- Cambio de fecha confirmado por detalle DD-MM-YYYY. Fecha sin registros conserva parcelas.
- A 520 px: `document_overflow=false`, `internal_scroll=true`. Sidebar/shell global sin modificaciones.
- `git diff --check`: sin errores (aviso de conversión LF/CRLF en layout.py preexistente).

Capturas solicitadas: `mapa_desktop.png`, `mapa_oxidos.png`, `mapa_sulfuros.png`, `mapa_parcela_seleccionada.png`, `detalle_lateral.png`. Revisadas visualmente. `review.json` contiene resultados de navegador.

Servidor temporal detenido. No se modificó SQL, datos ni PROD. Sin commit/push.
