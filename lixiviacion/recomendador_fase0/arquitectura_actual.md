# Arquitectura actual: evidencia estática

`layout.py:162` incorpora `lixiviacion.panel.layout()`. `panel.py:82–89` construye `dbc.Tabs`: mapa, diagnóstico y `dbc.Tab(dbc.Alert('Funcionalidad en desarrollo', color='light', className='m-4'), tab_id='lix-recommender-tab')`.

```text
layout.py → lixiviacion.panel.layout
  → dbc.Tabs(id=lix-tabs)
    → dbc.Tab(id=lix-recommender-tab)
      → dbc.Alert('Funcionalidad en desarrollo')
      → FIN (sin consulta, reglas ni salida propia)
```

No existe `recommender_layout()`, helper DB, store, filtro, callback de reglas, scoring, prioridad, recomendación ni CSS específico del Recomendador. Bootstrap aporta estilo al Alert. No hay motor oculto identificado en las referencias del repositorio a recommender/recomendador.

Dependencias indirectas de navegación: `callbacks.options` escucha `lix-tabs.active_tab`, pero lanza PreventUpdate salvo Diagnóstico (`callbacks.py:87–89`). `map_panel.load_map` escucha la pestaña y carga únicamente el mapa; callbacks de selección/drawer pueden limpiar selección al cambiar tab. Esto no es lógica de recomendación. No se debe describir la pestaña como una ruta a SQL: sus hermanas sí tienen rutas de datos.

Rutas existentes reutilizables, NO conectadas al placeholder:

- Mapa: `map_panel.load_map` → `map_db.snapshot` → `DAILY_SQL` → función diaria oficial. Store `lix-map-data`; detalle → `fetch_modulos_parcela` → función módulos.
- Diagnóstico: `callbacks.load` → `db.overview`, y tabla → helpers db; fuente V2. `callbacks.load_operational` → `db.operational` → cabecera oficial + `OP_TIMELINE_SQL` optimizado de 12 campos. Filtros y store `lix-aplicado` son de Diagnóstico, no propios del Recomendador.

Tests: `test_map.py:129` exige los tres tab_id. `visual_review.py`, `visual_diagnostic_review.py` y `diagnostico_timeline_runtime/visual_review.py` verifican navegación/texto del placeholder; no prueban recomendaciones. `diagnostico_fase1/panel.py` es respaldo histórico, no segundo runtime. Ningún componente fue implementado en esta auditoría.
