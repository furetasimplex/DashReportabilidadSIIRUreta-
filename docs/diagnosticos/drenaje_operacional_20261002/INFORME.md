# Impacto de fecha operacional de drenaje — auditoría de repositorio

Fecha: 02/10/2026. Trabajo exclusivamente local; sin conexión SQL, ejecución de SPs, modificación de datos ni promoción. Solo se agregan estos entregables. No se modifican archivos de aplicación ni objetos existentes.

## Conclusión y límite de evidencia

La corrección de `sp_actualizar_campana_parcela_control` **no alcanza automáticamente todas las rutas de drenaje**. Los catálogos guardados contienen lecturas directas de las tablas originales, vistas paralelas con fecha calendario y un consumidor adicional relevante: `sp_razon_lixiviacion`.

Los cuerpos examinados son snapshots del repositorio, no definiciones consultadas hoy en DEV. El documento `docs/ad_hoc/campana_parcela_control/README.md` fecha su extracción el 14/08/2026. También se revisaron `report_export/exports/auditoria_ley_srr_202609/catalogo.json` y `report_export/exports/diagnostico_fase4/catalogo_dev.json`; el nombre de una carpeta no acredita vigencia del objeto. Los archivos `*.snapshot.sql` adjuntos son extracciones literales del primero, para facilitar la revisión; **no son backups actuales ni candidatos de despliegue**.

No se encontró una definición de las nuevas vistas operacionales ni de `sp_flujo_riego_drenaje_test_v2/test_v3` en los archivos inspeccionados. El comentario «v3» del SP **sin sufijo** no acredita que sea el `_test_v3` informado. La validación de 102 días y los casos PAD1/4, PAD1/11 y PAD2/10 son antecedentes aportados por el usuario, no pruebas repetidas aquí. No se contradice la corrección ya promovida: se identifica desactualización de los snapshots.

La regla de referencia aprobada es exactamente:

```sql
CASE
 WHEN fecha_registro >= '2026-06-01T21:00:00'
  AND DATEPART(HOUR, fecha_registro) >= 20
 THEN DATEADD(DAY,1,CAST(fecha_registro AS date))
 ELSE CAST(fecha_registro AS date)
END
```

No equivale a desplazar todas las lecturas desde las 20:00 de cualquier fecha: el umbral inicial de las 21:00 también debe respetarse. No aplicar esa regla a riego, refino, PLS o fechas importadas de recuperación sin demostrar que comparten el contrato temporal.

## Mapa de rutas

```text
drena_concentrados_oxido / sulfuro
 ├─ v_drena_*_unpivot (raw) → actualizar_control [snapshot antiguo]
 │                          → sp_flujo_riego_drenaje [snapshot antiguo]
 │                          → sp_razon_lixiviacion
 ├─ v_drena_*_operacional → actualizar_control [informado corregido]
 │                       → flujo_test_v3 [informado en validación]
 ├─ vw_drena_concentrados_*_long → *_parcela
 │                              → vw_tablero_lixiviacion_final
 ├─ vw_drena_quimica_ingest
 └─ siir_curated.vw_siir_drena_concentrado_parcela_long
       → siir_mart resúmenes diario / semanal

campana_parcela_control (campaña/pad/parcela/módulo)
 ├─ vw_estado_operacional_campana_parcela
 ├─ vw_tablero_lixiviacion_final
 └─ sp_resumen_campana / sp_razon_lixiviacion / sp_flujo_riego_drenaje

Excel de recuperaciones → Recuperaciones_pad.Fecha_drenaje
 ├─ control_ley_ripio → control_ley_ripio_diario → tabs/oxido.py, sulfuro.py
 │                  → tabs/flujos_balance.py / familia SP balance
 ├─ v_aporte_cu_diario → sp_curvas_recuperacion
 ├─ v_recuperacion_real_vs_proyectada (+ proyeccion_serie)
 ├─ sp_compilar_parcela_campana_base / sp_refrescar_produccion_diaria
 └─ sp_resumen_campana / sp_razon_lixiviacion
```

Las dos familias de fechas (registro de drenaje químico y `Recuperaciones_pad.Fecha_drenaje`) no tienen una equivalencia demostrada en el repositorio.

## Matriz de impacto

En las filas SQL, el enlace apunta al cuerpo extraído del catálogo histórico. «Sí» significa recomendación sobre ese cuerpo **si DEV aún lo conserva**, nunca constatación del estado instalado.

| Objeto / archivo | Tipo | Fuente de drenaje usada | Fecha usada | Grano | Riesgo | ¿Requiere cambio? | Cambio recomendado |
|---|---|---|---|---|---|---|---|
| [v_drena_oxido_unpivot](v_drena_oxido_unpivot.snapshot.sql), [sulfuro](v_drena_sulfuro_unpivot.snapshot.sql) | Vistas | Tablas `drena_concentrados_*` | `fecha_registro` raw | Registro × parcela; UNPIVOT omite NULL | Consumidores interpretan raw como día operativo | No reemplazar indiscriminadamente | Migrar consumidores de fecha operacional a las nuevas vistas; conservar contrato raw para otros usos |
| `v_drena_*_operacional` | Vistas nuevas, informadas | Tablas raw | Regla aprobada | Registro × parcela, por confirmar DDL | Definición no versionada en evidencia disponible | Documentación | Incorporar exportación autorizada de DDL y validar claves/NULL, sin recrearlas desde esta auditoría |
| [sp_actualizar_campana_parcela_control](sp_actualizar_campana_parcela_control.snapshot.sql) | SP | Unpivot antiguos en snapshot | MIN/MAX CAST(d.fecha_registro AS DATE), filtros iguales | Campaña/pad/parcela/módulo | Snapshot obsoleto; fechas de ciclo y duración | Sin nueva corrección funcional demostrada | Sincronizar evidencia con versión ya corregida; no redeplegar snapshot |
| [sp_flujo_riego_drenaje](sp_flujo_riego_drenaje.snapshot.sql) | SP | Unpivot OX/SULF | CAST de drenaje en SELECT, JOIN temporal y WHERE | Pretende día/semana/mes × campaña/pad/parcela | Fecha incorrecta y multiplicación por módulos/raw | Sí, según candidato validado | Promover únicamente cuerpo autorizado de test_v3; verificar que conserva EXISTS de test_v2 y contrato de salida |
| `sp_flujo_riego_drenaje_test_v2/test_v3` | SPs informados | V2 legacy; V3 operacional según usuario | V3 fecha_operacional según usuario | Pendiente cuerpo actual | No se puede comprobar último JOIN ni agregados | Obtener evidencia | Comparar cuerpos reales antes de completar migración; no reconstruirlos desde comentarios |
| [sp_razon_lixiviacion](sp_razon_lixiviacion.snapshot.sql) | SP | v_drena_*_unpivot | CAST(d.fecha_registro AS DATE)=CAST(f.fecha_registro AS DATE), líneas 152–174 | Parcela/campaña × lectura de flujo | Desalineación Cu/flujo; duplicación si varias lecturas diarias | Sí para rama drenaje | Usar vista operacional y d.fecha_operacional en ambos JOINs; no desplazar riego ni recuperación importada |
| [vw_drena_concentrados_oxido_long](vw_drena_concentrados_oxido_long.snapshot.sql), [sulfuro](vw_drena_concentrados_sulfuro_long.snapshot.sql) | Vistas multianalito | Tablas raw | CAST(d.fecha_registro AS date) AS fecha, línea 6 | Registro × parcela, 7 analitos en columnas | Desfase propagado al tablero; distinta semántica NULL respecto UNPIVOT | Sí si su fecha pretende ser operacional | Resolver fecha con regla aprobada preservando todos los analitos/raw/id. No sustituir por vista solo cu_pp perdiendo campos |
| [vw_drena_concentrados_oxido_parcela](vw_drena_concentrados_oxido_parcela.snapshot.sql), [sulfuro](vw_drena_concentrados_sulfuro_parcela.snapshot.sql) | Vistas | *_long + vw_pad_parcela_control | Hereda d.fecha | Registro/parcela × coincidencias dimensión | Duplicación o mapeo PAD ambiguo | Revisar claves; fecha indirecta | Validar unicidad de dimensión y PAD. OX admite por OR pads con parcelas <=32; no asumir filtro exclusivo |
| [vw_tablero_lixiviacion_final](vw_tablero_lixiviacion_final.snapshot.sql) | Vista | *_long + flujos + refino + control | d.fecha=f.fecha; límites de control en CASE | Módulo/campaña × fechas y registros coincidentes | Mezcla límites corregidos con química calendario; multiplicación al sumar por parcela | Sí, condicionado a intención operacional | Corregir origen de fecha química; validar unicidad diaria y contrato de grano antes de cambiar JOIN/agrupación |
| [vw_drena_quimica_ingest](vw_drena_quimica_ingest.snapshot.sql) | Vista | Raw con referencia de 3 partes | CAST(d.fecha_registro AS DATE) AS fecha | Registro/parcela implícito, sin id en salida | Desfase, conexión a base fija; `cu_gl` no prueba unidad real | Sí si contrato operacional | Alinear fecha conservando analitos y NULLIF existentes. Corroborar base referenciada; no ejecutar migración cross-db existente |
| [siir_curated.vw_siir_drena_concentrado_parcela_long](vw_siir_drena_concentrado_parcela_long.snapshot.sql) | Vista analítica | Tablas raw, múltiples UNION ALL | CAST(src.fecha_registro AS date) AS fecha_dia | Registro × parcela × analito | Mes/semana y conteos afectados por fecha | Sí si mart debe ser operacional | Centralizar fecha operacional preservando raw/id/analitos, flags y semántica de valores |
| [siir_mart.vw_siir_drena_resumen_pad_analito_diario](vw_siir_drena_resumen_pad_analito_diario.snapshot.sql) | Vista agregada | Curated | fecha_dia, mes/año derivados | Día/pad/analito | COUNT(*) llamado cantidad_parcelas incluye varias lecturas si existen | Indirecto + validar | Recalcular agrupación temporal desde fuente corregida; no sustituir COUNT/AVG sin decidir grano |
| [siir_mart.vw_siir_drena_resumen_parcela_analito_semanal](vw_siir_drena_resumen_parcela_analito_semanal.snapshot.sql) | Vista agregada | Curated | semana_inicio derivada de fecha_dia | Semana/parcela/analito | COUNT(*) llamado cantidad_dias puede contar registros | Indirecto + validar | Comparar bordes de semana/mes y multiplicidad sin alterar promedio arbitrariamente |
| [vw_estado_operacional_campana_parcela](vw_estado_operacional_campana_parcela.snapshot.sql) | Vista | campana_parcela_control | fecha_ini/fin_drenaje materializadas | Campaña/pad/parcela/módulo | Hereda actualización del control | No cambio SQL demostrado | Comparar fechas/estado por claves después del proceso autorizado |
| [sp_resumen_campana](sp_resumen_campana.snapshot.sql) | SP | Control + recuperaciones_pad | dias_drenaje; MIN/MAX de riego y última Fecha_drenaje | Base preagregada por campaña/pad/parcela, salida campaña | Duraciones cambian legítimamente; recuperación es otra fuente | No sustitución de fecha demostrada | Validar salida tras control corregido. Aparición fecha_ini/fin_drenaje en encabezado no equivale a uso ejecutable directo |
| [control_ley_ripio](control_ley_ripio.snapshot.sql), [diario](control_ley_ripio_diario.snapshot.sql) | Vistas | Recuperaciones_pad + apilado | R.Fecha_drenaje | Fecha/campaña/pad/parcela, sujeto a claves | Posible multiplicidad por joins de catálogo/apilado | No traslado de fecha justificado | Auditar unicidad; no aplicar regla de timestamp químico a fecha importada |
| [sp_calcular_balance_flujos_modelo6_v2](sp_calcular_balance_flujos_modelo6_v2.snapshot.sql) | SP | control_ley_ripio para ley; F44 usa riego_concentrados_oxido; F47 usa conc_cu | Fecha_drenaje en vista; CAST calendario en fuentes distintas | Etapas/flujo y módulos reclamados | Join de ley sin fecha puede multiplicar historia; no dependencia directa de drena_* encontrada | No cambio temporal automático | Revisar cardinalidad y selección temporal de ley por separado; no desplazar fechas de PLS/riego |
| Familia sp_calcular_balance_flujos / base_m6 / modelo6 / copy1 / v2 / contingencia_test; sp_calcular_datos_conciliados; sp_validar_balance_modelo6_v2 | SPs en snapshots adjuntos | Referencias de recuperación/balance, no consumidor directo de los 7 términos en sus cuerpos catalogados | Depende de etapa/fuente | Flujo/fecha y agregados | Alcance indirecto; variantes pueden diferir | Corroboración de grafo actual | No propagar sustituciones de texto a esta familia; revisar dependencias SQL actuales |
| [v_aporte_cu_diario](v_aporte_cu_diario.snapshot.sql), [v_recuperacion_real_vs_proyectada](v_recuperacion_real_vs_proyectada.snapshot.sql), [sp_curvas_recuperacion](sp_curvas_recuperacion.snapshot.sql) | Vistas/SP | Recuperaciones_pad, base/cinética | Fecha_drenaje y ventanas LAG/día ciclo | Campaña/parcela/fecha | Sensibilidad a fechas/duplicados de recuperación, ruta diferente | No cambio demostrado | Mantener fechas importadas; validar independencia antes de incluir en migración |
| [sp_compilar_parcela_campana_base](sp_compilar_parcela_campana_base.snapshot.sql), [sp_refrescar_produccion_diaria](sp_refrescar_produccion_diaria.snapshot.sql) | SPs | Recuperaciones_pad | MIN/MAX Fecha_drenaje / CAST(r.Fecha_drenaje AS DATE) | Campaña/parcela y producción diaria | CAST equivalente sintáctico, pero NO del timestamp drena raw | No corrección automática | No confundir este CAST con bug confirmado; corroborar contrato de entrada |
| tabs/oxido.py:184,238,286; tabs/sulfuro.py:187,241,289 | Dashboards Python | control_ley_ripio_diario | Fecha_drenaje BETWEEN y GROUP BY | Fecha y fecha/parcela | Impacto solo si cambia fuente de recuperación | No | Conservar consultas; revisar regresión de series si se modifica esa ruta |
| tabs/flujos_balance.py:534–575 | Backend UI balance | control_ley_ripio | Fecha_drenaje inicial/final | SUM fino producido por PAD/corte | Diferencia entre cortes; duplicados se propagan | No por esta corrección | No reescribir F23/F24 sin demostrar nueva dependencia |
| tabs/tab_importar_recuperaciones.py:115–170 | Importador | Excel → Recuperaciones_pad | pd.to_datetime de Fecha_drenaje | Fila Excel/parcela/campaña | Desplazar +1 alteraría fecha ya declarada por usuario | No | Mantener; documentar origen externo de la fecha |
| docs/ad_hoc/campana_parcela_control/definiciones_bd.sql; catálogos JSON; docs/migrations/fix_prod_cross_db_references.sql | Evidencia / script previo | Referencias históricas | Según snapshot | No ejecutados aquí | Confundir archivo con objeto instalado o ejecutar script PROD | Solo documentación | Versionar nuevas evidencias cuando se autorice; no ejecutar scripts existentes |

## Riesgos de cardinalidad concretos

1. **SP flujo histórico:** entradas de `#flujos` y `#drena` se unen a control por pad/parcela y intervalo, sin módulo. Varias filas de control reproducen una observación. El SELECT final vuelve a unir control por campaña/pad/parcela y cruza flujo con drenaje por fecha/pad/parcela. Aun corrigiendo los primeros JOINs con EXISTS, se debe revisar el último JOIN y la multiplicidad flujo × drenaje. No se afirma que test_v3 conserve el defecto: falta su cuerpo.
2. **Tablero:** parte de control a nivel módulo y une cada módulo al mismo flujo de parcela/día. La repetición puede ser intencional para mostrar módulos, pero una suma posterior por parcela puede inflarse. Varias lecturas de química o refino por día añaden multiplicidad. El filtro admite cualquier `pad_id NOT IN (1,65)` para ambos tipos; otros objetos usan SULF=2. Es una inconsistencia de mapeo a corroborar, no autorización para cambiar IDs.
3. **Razón de lixiviación:** obtiene métricas de control mediante agregación previa, pero une flujo y drenaje por parcela/día sin demostrar unicidad. Repeticiones afectan volumen y cobre acumulados. El UPDATE contra recuperaciones también exige una única coincidencia por fecha/parcela/campaña.
4. **Modelo6_v2:** joins `ModulosActivos → control_ley_ripio` (líneas 3409 y 3627) por campaña/parcela/PAD, sin fecha. Varias recuperaciones históricas pueden repetir el peso de cada módulo. Es un riesgo independiente del cambio de fecha química; no se resuelve agregando una fecha elegida arbitrariamente.
5. **Control:** asignar límites MIN/MAX de parcela a cada módulo no es por sí mismo un bug de SUM; el objeto tiene grano módulo. No reemplazar estos agregados ni eliminar el módulo sin justificación.

Los 102 registros/fechas informados no garantizan unicidad de todos los JOINs: deben verificarse claves por fuente, parcela, fecha, campaña y módulo, más los rangos superpuestos. Tampoco garantizan que los 102 días sobrevivan UNPIVOT cuando cu_pp es NULL.

## Recomendación mínima y validación previa a promoción

- Obtener cuerpos actuales de destino, test_v2, test_v3 y vistas operacionales con `02_backup_read_only.sql`; conservar fecha, servidor/base y hashes fuera de SQL Server.
- Comparar v2→v3: exclusivamente fuentes/fecha de drenaje; mantener EXISTS, firma, filtros, columnas y orden de resultados, tipos, agregaciones, NULL y tratamiento de riego.
- Corroborar el grafo con `01_dependencias_read_only.sql`, incluyendo objetos cross-db y SQL dinámico. Las dependencias guardadas y búsquedas textuales no acreditan exhaustividad de jobs, BI o aplicaciones fuera del repositorio.
- Verificar OX/SULF Jun1–Sep10, continuidad diaria y límites horarios (antes del umbral, 01/06 20:00 y 21:00, fechas posteriores 19:59 y 20:00), incluyendo NULL de fecha sin convertirlo a cero/fecha ficticia.
- Comparar PAD1 campaña4, PAD1 campaña11, PAD2 campaña10; casos con varios módulos; resultados día/semana/mes. Separar deltas explicables por reasignación de fecha de multiplicaciones de filas.
- Contar coincidencias de control por registro, registros drenaje por parcela/fecha, flujos por parcela/fecha y química de refino por fecha. Si hay varias mediciones, acordar significado de promedio/suma antes de introducir preagregaciones.
- Confirmar conservación de TMS/CuT de las fuentes y explicar cualquier cambio derivado de la fecha; no exigir igualdad ciega de Cu transferido cuando cambia emparejamiento temporal.

`03_migracion_pendiente.sql` y `04_rollback_pendiente.sql` son **plantillas deliberadamente bloqueadas**: faltan cuerpo real revisado, hashes, opciones SET y destino DEV. No constituyen una promoción lista ni inventan test_v3. Usan ALTER, transacción, comprobación de hash y lock cooperativo; por defecto ensayan con ROLLBACK. El lock solo coordina procesos que usen el mismo recurso: efectuar promoción en ventana controlada. Si hay firma de módulo se exige un plan de refirma. La restauración revierte el SP, no datos, ni deshace cambios posteriores de otros procesos. No se ejecutó ninguno de estos SQL.

## Inventario y comprobaciones locales

- `inventario_referencias.csv`: 2.090 coincidencias en 9 archivos de los siete términos solicitados y las dos nuevas vistas (sin coincidencias de las nuevas vistas); incluye comentarios, nombres prefijados y metadatos, no solo consumidores ejecutables.
- `inventario_objetos_catalogados.csv`: 28 objetos/versiones con referencias dentro de los dos catálogos SQL completos (14 por catálogo). Permite distinguir los JSON de una referencia de aplicación.
- `inventariar.py`: reproduce búsqueda local de archivos de texto, sin importar la aplicación ni conectarse a SQL. Excluye entornos, Git y este paquete de auditoría; no inspecciona contenido binario Excel/PDF ni servicios externos.
- Se revisaron adicionalmente referencias a drenaje/recuperación en Python y los cuerpos SQL extraídos; no se encontró invocación Python directa a los SPs de flujo/resumen/razón en esa búsqueda. La ausencia literal no excluye invocación dinámica o externa.
- No se ejecutan tests de aplicación que puedan abrir conexiones: no hay cambios funcionales que probar. Se verifica reproducción del inventario y whitespace de artefactos nuevos, además de `git diff --check` del repositorio.
- `05_cardinalidad_read_only.sql`: consultas propuestas de regla y multiplicidad, no ejecutadas. Los snapshots preservan el texto SQL salvo espacios finales y saltos/líneas vacías de la exportación; sus números de línea corresponden a estos archivos de evidencia. La comprobación local contrasta todas las líneas no vacías con el catálogo.

No se reemplazó MAX/AVG/SUM, no se introdujo conversión NULL→0, no se modificó SQL instalado ni código de negocio. Sin PROD, commit ni push.
