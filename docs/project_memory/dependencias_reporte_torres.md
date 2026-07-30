# Reporte de Representatividad de Torres — Mapa de dependencias

Cómo se produce el reporte "Representatividad Torres" (análisis por torre TM1/TM2/TM3),
desde el click en la UI hasta la base de datos y el archivo exportado.

> Generado: 2026-07-22. Base de datos: **SQL Server** `inventar_SpcHidr` (ver `db_connection.py`, ENTORNO 4).

---

## 1. Cadena de dependencias (de arriba hacia abajo)

```
main.py
 └─ layout.py  (register_callbacks, tab "nav-reportabilidad")
     └─ report_export/layouts/reportabilidad_page.py     (UI: fechas, botones)
     └─ import report_export/callbacks/reportabilidad_cb.py   (registra callbacks al importar)
         └─ report_export/report_export.py     (acceso a datos + armado Excel)  ← núcleo
             ├─ db_connection.py  → get_engine()  → SQL Server
             ├─ report_export/export_to_excel.py      (plantillas xlsx)
             ├─ report_export/pdf_generator.py        (PDF reportlab)
             └─ report_export/xlsx_to_pdf.py          (conversión xlsx→pdf)
```

---

## 2. Callbacks (entrypoints de UI) → funciones

Archivo: `report_export/callbacks/reportabilidad_cb.py`

| Callback (línea) | Dispara | Llama a |
|---|---|---|
| `generar_reporte` (~6511) | Botón "Generar" | `fetch_representatividad_torres_report`, `fetch_fecha_corte_representatividad`, tablas/grilla en memoria |
| `exportar_excel` (~6758) | Botón export xlsx | `_export_representatividad_torres_to_excel` / `_generar_excel_representatividad_completo` |
| `generar_pdf` (~6953) | Botón PDF | `pdf_generator.generar_pdf_representatividad_torres` vía `_build_xlsx_pdf_reporte_torre` |
| **publicar oficial** `rep-generar-final-btn` (~7176) | Botón "Generar final" | `armar_paquete_reporte_torre_oficial` → `write_reporte_torre_oficial` |
| `descargar_historial_xlsx/pdf` (~7382/7414) | Historial | `fetch_reporte_torre_oficial_snapshot` → `_export_representatividad_desde_paquete` |
| `eliminar_reporte...` (~7292) | Modal borrar | `soft_delete_reporte_torre_oficial` |
| `cargar_historial...` (~6490) | Al abrir subtab | `fetch_historial_reporte_torre_oficial` |

---

## 3. Núcleo de datos — `report_export/report_export.py`

### 3.1 Fetch (lectura BD)
| Función | Objeto BD que consulta |
|---|---|
| `fetch_representatividad_torres_report` | **SP** `sp_reporte_representatividad_torres` (datos diarios por torre) |
| `fetch_fecha_corte_representatividad` | vista `v_datos_apilado_tmh_v2` (día con CV-008/CV-108 A+B cerrados) |
| `fetch_bd_ton_report` | vista `v_bd_ton_reportabilidad` (flags Rep TM1/TM2/TM3, evaluabilidad, SRR) |
| `fetch_gestion_representatividad_fy` | **SP** `sp_gestion_representatividad_fy` (indicador FY mensual + YTD) |
| `fetch_estado_apilado_turno_representatividad` | vistas `v_estado_apilado_turno_representatividad` + `v_reporte_turno_campania_modulo_test` |

### 3.2 Armado del paquete oficial
- `armar_paquete_reporte_torre_oficial(inicio, fin)` — ejecuta todos los fetch anteriores una sola vez y devuelve dict con 6 bloques:
  `rep_torres`, `bd_ton_fy`, `bd_ton_mes`, `turno_mes`, `gestion_fy_quimico`, `gestion_fy_fisico` + `fecha_corte_operacional`, `anio_fiscal`.
- Helpers: `_fetch_fuentes_mensuales_torres_oficial`, `_obtener_rango_fiscal_hasta_mes` (FY = jul–jun), `_completar_calendario_representatividad`, `normalizar_periodo_mes`.

### 3.3 Persistencia (snapshot oficial)
- `write_reporte_torre_oficial(...)` — soft-delete del reporte activo del mes + INSERT en 3 tablas.
- Lectura: `fetch_reporte_torre_oficial_cab / _snapshot / _detalle`, `fetch_historial_reporte_torre_oficial`, `mes_tiene_reporte_activo`.
- Comentarios editables se preservan entre versiones: `comentarios_mapa_desde_dataframe`, `_merge_comentarios_representatividad`.

### 3.4 Construcción del Excel
- `_generar_excel_representatividad_completo` / `_export_representatividad_torres_to_excel` / `_export_representatividad_desde_paquete`
- Hojas mensuales: `_agregar_hojas_mensuales_torres` → `_agregar_hoja_mensual_torres`, `_preparar_detalle_mensual_torres`, `_calcular_resumen_mensual_torres`, `_calcular_tonelaje_por_material_torres`.
- Estética oficial (logo BHP, marco, dimensiones): `_agregar_encabezado_institucional_torre`, `_agregar_marco_exterior_torre`, `_aplicar_dimensiones_oficiales_torre`. Logo: `assets/pampa-norte-bhp-oficial.png`.
- Validación: `_validar_workbook_representatividad`, `_inspeccionar_workbook_representatividad`.

---

## 4. Objetos de base de datos

### 4.1 Stored procedures
| SP | En repo | Rol |
|---|---|---|
| `sp_reporte_representatividad_torres` | ✅ `docs/stored_procedures/sp_reporte_representatividad_torres.sql` | Detalle diario por torre. Solo hace `SELECT` sobre la tabla precalculada `representatividad_torres_resultado` (Dia, TM1/TM2/SRR × TurnoA/B × Químico/Físico) |
| `sp_gestion_representatividad_fy` | ✅ `docs/stored_procedures/sp_gestion_representatividad_fy.sql` | Indicador FY mensual + YTD (Químico/Físico, objetivo 0.85) |
| `sp_reporte_turno_test` | ✅ `docs/stored_procedures/sp_reporte_turno_test.sql` | Reporte por turno (pipeline relacionado, no es el de torres). Ver [pipeline_cache_reporte_turno.md](pipeline_cache_reporte_turno.md) |

### 4.2 Vistas usadas
`v_bd_ton_reportabilidad`, `v_datos_apilado_tmh_v2`, `v_estado_apilado_turno_representatividad`,
`v_reporte_turno_campania_modulo_test`.

### 4.3 Tablas del snapshot oficial
Definición en `docs/stored_procedures/reporte_torre_oficial.sql`:
| Tabla | Contenido |
|---|---|
| `reporte_torre_oficial_cab` | 1 reporte activo por mes (`periodo_mes`, estado, FY, soft-delete) |
| `reporte_torre_oficial_snapshot` | 6 bloques JSON (`payload` por `bloque`) |
| `reporte_torre_oficial_detalle` | Detalle Fecha+Turno: Rep TM1/TM2/TM3 Químico/Físico + comentarios |

Constantes en código: `RTO_CAB_TABLE`, `RTO_SNAPSHOT_TABLE`, `RTO_DETALLE_TABLE`, `RTO_SNAPSHOT_BLOQUES`, `RTO_DETALLE_COLUMNAS`.

---

## 5. Dos modos de reporte

1. **Vista rápida (borrador):** `generar_reporte` → `sp_reporte_representatividad_torres` en vivo. No persiste.
2. **Reporte oficial (publicado):** `armar_paquete...` → `write_reporte_torre_oficial` → snapshot en 3 tablas. Reproducible/exportable después desde historial sin recalcular.

---

## 6. Salidas
- **XLSX:** vía XlsxWriter (formato oficial BHP), motor en `report_export.py`.
- **PDF:** `pdf_generator.generar_pdf_representatividad_torres` (reportlab) o `xlsx_to_pdf` (render del xlsx a A3).
- Ejemplos generados en `report_export/exports/Reporte_Representatividad_Torres_*.xlsx`.
