# Inventario previo de Control de Reclamo

Estado capturado antes de cambios: `ui_contract_before.json` y `before/`.

| Panel | Título anterior | Propósito | IDs principales | Callback / lectura o escritura |
|---|---|---|---|---|
| Barra superior | Control de Reclamo | Período, PAD, refresco, reproceso, publicación | `rango`, `filtro-pad`, `btn-actualizar`, `btn-recalcular`, `btn-publicar`, `confirmar-publicar`, `mensaje-accion` | `cb_recalcular` escribe resultados; `cb_publicar` publica con confirmación; refresco dispara consultas |
| Mantención automática | Mantencion automatica de modulos | Congelar, abrir, cerrar y mostrar última ejecución | `btn-automatizacion`, `resultado-automatizacion`, `alertas-automatizacion` | `cb_automatizacion` escribe; `cb_alertas_automatizacion` lee historial |
| Semáforo | Semaforo de integridad | Hallazgos previos a publicación | `semaforo` | `cb_semaforo` lee |
| Resumen general | Resumen general | Totales PAD y planta | `resumen-general` | `cb_resumen_general` lee |
| CV25 vs topografía | Totalizador CV25 contra topografia | Tonelaje y brecha | `g-cv25`, `g-brecha` | `cb_cv25` lee |
| Rendimiento | Rendimiento de rotopala | TMS/hora y horas | `rendimiento-rotopala-tabs`, `g-rendimiento`, `g-horas` | `cb_rendimiento` lee |
| Vista mensual | Vista mensual por modulo | Matriz por fuente y PAD | `matriz-metrica`, `matriz-pad-tabs`, `matriz-mensual` | `cb_matriz_mensual` lee |
| Cuadratura | Cuadratura por modulo | Volumen, exceso, historial | `cuadratura-pad-tabs`, `g-cuadratura`, `tabla-cuadratura`, `cuadratura-modulo-select`, `detalle-cuadratura-modulo` | `cb_cuadratura`, `cb_opciones_cuadratura_modulo`, `cb_detalle_cuadratura_modulo` leen |
| Remanente | Resumen por modulo — tonelaje remanente | Saldo por módulo | `remanente-pad-tabs`, `tabla-remanente` | `cb_remanente` lee |
| Avance diario | Avance diario por fuente | Topografía y estimación | `avance-pad-tabs`, `g-avance`, `tabla-avance` | `cb_avance` lee |
| Preview conciliado | Vista previa del dato conciliado | Revisión previa | `preview-pad-tabs`, `tabla-preview-conciliados` | `cb_preview_conciliados` lee |
| Datos base | Disponible para rotopalas | Consulta y edición de base | `dr-*`, `btn-buscar-dr`, `btn-dr-actualizar`, `btn-dr-insertar`, `tabla-disponible-rotopalas`, `store-disponible-rotopalas` | `cb_tabla_disponible_rotopalas` lee; `cb_dr_actualizar` y `cb_dr_insertar` escriben |
| Ajustes | Ajustes manuales | Proponer y consultar ajustes | `aj-*`, `btn-ajuste`, `tabla-ajustes` | `cb_registrar_ajuste` escribe propuesta; `cb_tabla_ajustes` lee |

Los controles de datos base dependen de sus filtros y del `store-disponible-rotopalas`; los paneles de consulta dependen de `btn-actualizar`, `mensaje-accion`, rango y pestañas PAD. El flujo de publicación depende de `btn-publicar`, `confirmar-publicar` y rango. La página está montada en `layout.py` bajo `subtabs-reclamo`. El inventario automático registró 74 IDs estáticos, 26 callbacks y 25 llamadas a `db`, sin duplicados.
