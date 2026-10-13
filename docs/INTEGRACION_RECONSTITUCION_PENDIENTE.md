# Reconstitución de apilado dentro de SIIR

Preparado el 12/10/2026. El módulo está listo para compartir la única app Dash,
autenticación, encabezado y navegación del destino. El menú lateral de SIIR
todavía no se modificó; el cableado siguiente completa su incorporación.
No requiere iframe ni servidor adicional en Reportabilidad.

## Cambios de presentación

Un único Gantt reúne pads y campañas con identidad completa P/C/M. Naranja
marca días operacionales con volumen medido, 08:00–08:00. Estos segmentos
delimitan levantamientos, no horas efectivas. Huecos significan días sin
volumen. La proyección azul ocupa un carril separado del medido y solo aparece
cuando tiene tasa y densidad válidas. Se eliminaron pistas, topes y adornos
superpuestos. La tabla cronológica está plegada; el desglose se abre al clic.
Los mensajes técnicos quedan en el botón Consideraciones. El pendiente global
permanece visible y no se atribuye a una campaña al seleccionar un pad.

La instantánea real de agosto y septiembre carece de horómetro validado; su
Gantt muestra medición y declara proyección no disponible. La prueba de dos
carriles usa geometría sintética, claramente separada de la validación real.

## Archivos para copiar al repositorio destino

- `reconstitucion/`: motor corregido, fuente SQL, validación, umbrales y panel.
- `assets/reconstitucion.css`: estilos encapsulados; paleta #E86D1F, #F5F6FA,
  blanco, Inter y azul informativo #3B82F6 del tema SIIR.
- `tabs/tab_reconstitucion.py`: puente para montar y registrar callbacks.

No copiar `app.py` del standalone al destino ni un `.env`. No se copiaron ni
abrieron XLSX. Los motores raíz de Reconstitucion permanecen para CLI/reportes;
los del paquete tienen imports relativos para evitar colisiones con curvas.

## Cableado de `layout.py` en SIIR

1. Importar `tab_reconstitucion` junto a `tab_curvas`.
2. Agregar enlace lateral `nav-reconstitucion` y contenedor inicialmente oculto
   `subtabs-reconstitucion`.
3. Extender el callback de navegación con Input de ese enlace, State children
   y Outputs style/children/clase, siguiendo el montaje diferido de curvas.
4. Montar `tab_reconstitucion.layout()` solo cuando se abre la sección y el
   contenedor está vacío. Añadir título/breadcrumb `RECONSTITUCIÓN DE APILADO`.
5. Registrar una vez en el arranque:

```python
from db_connection import get_engine
tab_reconstitucion.configure(get_engine, schema='inventar_SpcHidr.inventar_SpcHidr')
tab_reconstitucion.register_callbacks(app)
```

El esquema es explícito: no sustituirlo silenciosamente por DEV_SIIR. La cuenta
SIIR debe tener lectura sobre esas fuentes. Navegar/montar no consulta SQL.
Solo Cargar datos consulta, y exige rango válido. La barra indica cobertura
realmente cargada; filtros actúan en memoria y advierten si se pide un período
más amplio. Botón deshabilitado con texto Calculando durante la carga.

## Compatibilidad y límites

`app.py` standalone pasa a montar este mismo panel en puerto 8050; inyecta la
conexión original al cargar, sin leerla en el import del panel. La fuente sigue
siendo masa oficial versionada. Septiembre medido se usa únicamente en preview
y pruebas; no es respaldo automático de datos oficiales.

El dashboard anterior se conserva en
`archivo/legado/app_pre_integracion_reportabilidad_20261012.py`; desde la raíz
puede abrirse con `python -m archivo.legado.app_pre_integracion_reportabilidad_20261012`.
El antiguo botón de exportar XLSX no forma parte del nuevo panel: permanecen
`informe_modulos.py`, plantillas y scripts de reporte. Su integración visual se
debe resolver aparte conservando su contrato. No se eliminan esos archivos.

Resultados guardados por token en memoria, máximo 16 sesiones por proceso:
tras reinicio, expulsión o cambio de worker se requiere cargar nuevamente.
Despliegues multiworker deben configurar afinidad o caché compartida antes de
usar esta sección a escala. No hay escritura DB ni cálculo persistido.

## Validación offline

```powershell
python -B tests/test_integracion_reportabilidad.py -v
python -B tests/test_metodologia.py
python -B tests/validar_agosto_septiembre.py docs/diagnosticos/metodologia_db_20261012
python -B preview.py --audit docs/diagnosticos/metodologia_db_20261012
```

Preview en http://127.0.0.1:8061, snapshot real y SQL desactivado. Los tests
comprueban identidad de módulo/actividad, carriles sin superposición, ausencia
de proyección inventada, masa/volumen del hover, conservación, import/montaje
sin SQL, IDs únicos e idempotencia de callbacks. HTML autónomo generado en
`docs/preview_reportabilidad/itinerario_agosto_septiembre.html`. La interfaz
completa aún requiere revisión en navegador: control de browser no disponible
durante esta preparación.

Actualización 12/10/2026: integración incorporada al menú. El contrato vigente está en ../INTEGRACION_RECONSTITUCION.md; el cableado descrito como pendiente arriba ya está completado.
