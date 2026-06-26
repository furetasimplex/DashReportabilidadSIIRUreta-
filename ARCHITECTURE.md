# Arquitectura: Dashboard Hidrometalúrgico Spence

## Punto de entrada

```
main.py
```

- Crea la instancia `Dash` con tema Bootstrap FLATLY y Bootstrap Icons.
- Expone el servidor Flask subyacente (`app.server`).
- Registra el Blueprint de autenticación en `/auth`.
- Llama a `create_layout(app)` y `register_callbacks(app)` desde `layout.py`.
- Protege todas las rutas con `@server.before_request` → redirige a `/auth/login_page` si no hay sesión activa.
- Corre en `debug=True, port=8065`.

---

## Capas de la aplicación

```
main.py
  ├── auth.py                    (Flask Blueprint /auth)
  ├── db_connection.py           (SQLAlchemy engine + pyodbc)
  └── layout.py                  (estructura visual + registro de callbacks)
        ├── Header / Footer
        ├── Navbar  (5 secciones)
        └── subtabs-container
              ├── subtabs-mina        → tabs/tab1.py
              ├── subtabs-seca        → tabs/tab2.py, tab3.py, tab4.py
              ├── subtabs-humeda      → tabs/tab_ripios.py
              ├── subtabs-admin       → tabs/tab_import_container.py
              │                          tabs/tab_recon_container.py
              └── subtabs-report      → tabs/tab_report.py
```

---

## Módulos principales

### `auth.py` — Autenticación
- Flask Blueprint montado en `/auth`.
- Rutas: `GET /login_page`, `POST /login`, `POST /register`, `GET /logout`.
- Usuarios almacenados en `inventar_SpcHidr.usuarios` (SQL Server).
- Contraseñas con hash Werkzeug (`check_password_hash`).

### `db_connection.py` — Capa de datos
- Variable de entorno `ENTORNO` selecciona el backend:
  - `1` → MySQL local (`mysql+pymysql`)
  - `2` → MySQL producción (`mysql+pymysql`)
  - `3` → SQL Server Windows (`mssql+pyodbc` ODBC 17)
  - `4` → SQL Server / macOS (`mssql+pyodbc` ODBC 18, activo por defecto)
- `get_engine()` — SQLAlchemy engine (singleton, `pool_pre_ping`, `pool_recycle=1800`).
- `get_connection()` — conexión pyodbc cruda para queries directas.

### `layout.py` — Shell del dashboard
| Función/Objeto | Rol |
|---|---|
| `render_header()` | Logo BHP Spence + título |
| `render_footer()` | Logo Simplex + contacto |
| `navbar` | Barra de navegación con 5 secciones y menú de usuario |
| `subtabs` | Contenedor que aloja los 5 paneles (uno visible a la vez) |
| `create_layout(app)` | Registra todos los callbacks de tabs y devuelve el layout raíz |
| `register_callbacks(app)` | Callback de visibilidad de secciones + logout clientside |

**Lógica de navegación:** un solo callback `toggle_subtabs` alterna `display:block/none` entre los 5 `html.Div` de `subtabs-container` según el NavLink clickeado.

---

## Secciones del dashboard

### Resumen Estadístico Mina — `tabs/tab1.py`
- `render_tab1()` / `register_tab1_callbacks(app)`

### Control Área Seca — `tabs/tab2.py`, `tab3.py`, `tab4.py`
| Sub-tab | Archivo | Contenido |
|---|---|---|
| Conciliación Operacional | `tab2.py` | `render_tab2` / `register_tab2_callbacks` |
| Control Apilado | `tab3.py` | `render_tab3` / `register_tab3_callbacks` |
| Torres de Muestreo | `tab4.py` | `render_tab4` / `register_tab4_callbacks` |

### Control Área Húmeda — `tabs/tab_ripios.py`
- Sub-tab activa: **Recuperación** (`render_tab()`).
- Sub-tabs deshabilitadas: Control de Riego, Producción Catódica.

### Administración y Reconciliación
| Sub-tab | Módulo |
|---|---|
| Importar data base | `tabs/tab_import_container.py` |
| Reconciliador Área Seca | `tabs/tab_recon_container.py` |

### Reportabilidad — `tabs/tab_report.py`
- Layout desde `tab_report.layout()`.
- Callbacks en `report_export/callbacks/reportabilidad_cb.py` y `report_export/callbacks/report_cb.py`.

---

## Módulos de soporte

```
tabs/
  ├── sulfuro.py                 register_callbacks(app)
  ├── oxido.py                   register_callbacks(app)
  ├── tabreportabilidad.py       register_callbacks_reporte(app)
  ├── tabReconHidro/
  │     ├── tabreportabilidad_hidro.py   register_callbacks_reporte(app)
  │     └── tab_recon_container_hidro.py register_callbacks(app)  [registrado pero tab deshabilitada]
  └── db_helpers.py              helpers de consulta compartidos

report_export/
  ├── report_export.py
  ├── export_to_excel.py
  ├── layouts/
  │     ├── report_tab.py
  │     └── reportabilidad_page.py
  └── callbacks/
        ├── report_cb.py
        └── reportabilidad_cb.py
```

---

## Flujo de request

```
Browser → Flask (before_request)
           ├── no sesión → redirect /auth/login_page
           └── sesión OK → Dash app
                            ├── layout.py (render estático al cargar)
                            └── callbacks (reactividad Dash)
                                  ├── toggle_subtabs   → muestra/oculta secciones
                                  ├── logout clientside → fetch /auth/logout
                                  └── callbacks de cada tab (datos desde DB)
```

---

## Variables de entorno clave (`.env`)

| Variable | Uso |
|---|---|
| `ENTORNO` | Selecciona backend de DB (1-4) |
| `SQLSERVER_HOST` | Host SQL Server |
| `SQLSERVER_PORT` | Puerto (default 1433) |
| `SQLSERVER_DB` | Nombre de base de datos |
| `SQLSERVER_USER` / `SQLSERVER_PASSWORD` | Credenciales |
| `SQLSERVER_DRIVER` | Driver ODBC (default ODBC Driver 18) |
