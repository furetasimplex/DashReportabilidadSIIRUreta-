# Auditoría estática downstream — Tablero lixiviación V4

03/10/2026. Solo repositorio. Sin conexión a SQL Server, cambios funcionales, migraciones, commit ni push.

## 1. Dictamen

**No hay evidencia suficiente para autorizar el reemplazo directo de la vista oficial por V4.** No se encontró un consumidor ejecutable downstream de `vw_tablero_lixiviacion_final` en el código o en los dos catálogos SQL revisados. Esto NO acredita ausencia de consumidores en PROD, Power BI publicado, consultas ad hoc, jobs u otros repositorios.

El cambio tampoco es compatible semánticamente aunque se preserven los nombres: cambia el grano, la asignación de campaña, el universo de filas y potencialmente la unidad numérica de `transferencia_cu_kg_d`. Una consulta podría seguir compilando y entregar resultados distintos sin advertencia.

Recomendación: publicar, tras validación y autorización futura, un contrato físico versionado (por ejemplo `vw_tablero_lixiviacion_final_v2`, dejando explícito que implementa el diseño TEST V4). Mantener el oficial sin cambios durante la identificación/migración de consumidores. No crear una supuesta compatibilidad que vuelva a cruzar medidas físicas contra módulos.

## 2. Evidencia, alcance y límites

- Catálogos históricos: `report_export/exports/auditoria_ley_srr_202609/catalogo.json` y `report_export/exports/diagnostico_fase4/catalogo_dev.json`. Contienen las definiciones examinadas; no son evidencia del estado actual de PROD.
- `report_export/exports/auditoria_ley_srr_202609/objeto_firmas_final.json` contiene otra copia: se comprobó que los cinco cuerpos auditados son idénticos a `catalogo.json`. No aporta una versión funcional distinta.
- Los metadatos de `monitor_pi_tum/validacion/downstream/evidencia/dependencias.json` y `report_export/exports/diagnostico_fase4/dependencias.json` corroboran el sentido de las flechas del mapa: tablero como consumidor de las cuatro fuentes y vistas `*_parcela` como consumidoras de drenaje; no muestran un consumidor del tablero.
- Antecedente: `docs/ad_hoc/campana_parcela_control/README.md:46` enumera la vista como consumidora de CPC. Es una dependencia **upstream del tablero**, no prueba de que otro reporte consuma el tablero.
- La auditoría anterior `docs/diagnosticos/drenaje_operacional_20261002/` es evidencia derivada de esos mismos catálogos. Sus referencias no se cuentan como nuevos consumidores.
- `ARCHIVOS.md` lista todos los archivos y líneas con referencias literales a los cinco objetos auditados. `referencias_en_definiciones.csv` separa cada objeto dentro de los JSON; una coincidencia en CREATE VIEW no es un consumidor.
- `coincidencias_columnas.csv` registra nombres exactos, evitando confundir `flujo_m3_d` con `flujo_m3_dia`. Nombres comunes como `fecha`, `pad_id` o `modulo_id` **no demuestran linaje** por sí solos.
- La búsqueda cubre archivos textuales, incluidos ocultos/ignorados y `release/`, excluyendo Git y entornos/dependencias. No interpreta modelos binarios PBIX/XLSX ni verifica servicios desplegados. SQL dinámico construido por fragmentos podría eludir la búsqueda literal.
- No se dispone aquí del DDL TEST V4 completo. La descripción funcional del usuario se toma como diseño propuesto; no se verifican tipos, orden de columnas ni reglas exactas de ventanas/solapamientos del candidato.

## 3. Mapa de dependencias comprobadas

Flecha = productor → consumidor. Cuerpos históricos, no objetos instalados comprobados.

```text
flujos reales → vw_flujos_reales_oxido_long / sulfuro_long ─────┐
campana_parcela_control ─────────────────────────────────────┤
drena_concentrados_oxido → vw_drena_concentrados_oxido_long ───┤
drena_concentrados_sulfuro → vw_drena_concentrados_sulfuro_long┤
riego_concentrados_oxido → vw_riego_oxido_refino_base ──────────┤
riego_concentrados_sulfuro → vw_riego_sulfuro_refino_base ──────┤
                                                            ▼
                                      vw_tablero_lixiviacion_final
                                                │
                                  downstream no encontrado en repo

vw_drena_concentrados_oxido_long → vw_drena_concentrados_oxido_parcela
vw_drena_concentrados_sulfuro_long → vw_drena_concentrados_sulfuro_parcela
                                  ↑
                   vw_pad_parcela_control / vw_dim_parcela_pad
```

No se encontró consumidor posterior de las dos vistas `*_parcela` en los dos catálogos. No se encontró consulta de los cinco objetos desde Python/Dash, exportadores Excel, APIs o helpers textuales Power BI. No se inventa una relación con RTO, Datos Conciliados o el Generador Reporte por compartir nombres de columna.

## 4. Matriz consumidor × columnas e impacto

Clasificación referida a sustituir el tablero por V4 o promover fechas operacionales en sus cuatro fuentes, según se indica. Los elementos documentales no se presentan como consultas de negocio.

| Consumidor encontrado / evidencia | Productor | Columnas utilizadas | Operación / grano | Clasificación | Efecto esperado y recomendación |
|---|---|---|---|---|---|
| `vw_tablero_lixiviacion_final` en ambos catálogos; [snapshot](vw_tablero_lixiviacion_final.snapshot.sql) | `vw_drena_concentrados_oxido_long` y `...sulfuro_long` | `fecha,nro_parcela_pad,cu_pp,h_p,ph,cl,fet,fe2,eh` | UNION ALL, JOIN por parcela/fecha/PAD; proyecta química y calcula delta/transferencia | **IMPACTO DE GRANO/CARDINALIDAD** | Fechas operacionales cambian emparejamientos, NULL y valores de transferencia aun sin cambiar columnas. Si se renombran/eliminan columnas de origen, adicionalmente impacto de esquema |
| Mismo tablero / mismo snapshot | `vw_riego_oxido_refino_base` y `...sulfuro_refino_base` | `fecha,cu_pp,h_p,ph,cl,fet,fe2,eh` | UNION ALL, JOIN por fecha/PAD | **IMPACTO DE GRANO/CARDINALIDAD** | Cambian días de refino y deltas; varias muestras por fecha pueden multiplicar parcelas. Promover drenaje/refino coordinadamente, comprobando unicidad |
| [vw_drena_concentrados_oxido_parcela](vw_drena_concentrados_oxido_parcela.snapshot.sql) | `vw_drena_concentrados_oxido_long` | `id_registro,fecha,fecha_registro,nro_parcela_pad,cu_pp,h_p,ph,cl,fet,fe2,eh` | Proyección más JOIN a dimensión parcela/PAD | **IMPACTO DE GRANO/CARDINALIDAD** | La fecha publicada cambia y puede cambiar su unicidad lógica. Conservar firma permite compilar; si `fecha_registro` se elimina/renombra, **IMPACTO DE ESQUEMA** |
| [vw_drena_concentrados_sulfuro_parcela](vw_drena_concentrados_sulfuro_parcela.snapshot.sql) | `vw_drena_concentrados_sulfuro_long` | Mismas columnas | Igual patrón | **IMPACTO DE GRANO/CARDINALIDAD** | Mismo riesgo temporal y de esquema; el cambio de fecha por sí solo no implica cambiar cantidad de filas de esta proyección |
| Consumidor ejecutable posterior del tablero | Tablero oficial | Ninguno comprobado | No encontrado | No asignable a un consumidor inexistente | No se puede nombrar un reporte concreto que rompería o que sumaría duplicados |
| README CPC; informe previo; `01_dependencias_read_only.sql` previo; inventarios y snapshots anteriores | Metadatos / definiciones | Nombre del objeto; proyecciones de evidencia | Documentación o búsqueda en sys.objects | **SIN IMPACTO** funcional | Actualizar documentación tras promoción futura, no cuentan como downstream de datos |
| `reclamo/db.py:94`, `reclamo/panel.py:1508–1529`; copia `release/f6_candidate/reclamo/db.py` | Objetos de reclamo, no tablero | `campana_id,pad_id,modulo_id` | Consultas/detalle por módulo | **SIN IMPACTO** demostrado por V4 | Dependencia modular real, pero de otro contrato. No eliminar ni adaptar por coincidencia nominal |
| `tabs/tab_import_apilado.py:127–147` | Dimensión módulo y campañas importadas | Renombra `id_modulo` a `modulo_id` | Merge de importación | **SIN IMPACTO** demostrado | No consume el tablero |
| Familia SQL balance en `auditoria_reclamo/sql_definitions/`, `report_export/exports/` y `monitor_pi_tum/validacion/` | Otras fuentes de flujo | `flujo_m3_dia` y agregaciones | Balances por flujo | **SIN IMPACTO** demostrado por esta vista | El identificador no es `flujo_m3_d`; no atribuir estas SUM al tablero |

No se encontró un consumidor concreto clasificable únicamente como **IMPACTO SOLO DE NOMBRE/UNIDAD**. Esa categoría aplica al cambio de aliases si un cliente los utiliza, pero no hay cliente identificado para afirmarlo. El cambio de unidad bajo un alias existente sería **IMPACTO CRÍTICO** potencial, descrito a continuación, no una dependencia inventada.

## 5. Contrato actual: rupturas y cambios silenciosos

| Columnas / comportamiento actual | Cambio V4 evaluado | Riesgo si existe un consumidor externo | Recomendación de contrato |
|---|---|---|---|
| `pad_id,parcela_id,fecha,nombre_pad,nombre_parcela` | Clave física diaria | Menos duplicados; cambia universo respecto LEFT JOIN desde CPC | Preservar identidades/tipos y definir explícitamente dominio de fechas |
| `campana_id,numero_campana` | Campaña solo en ventana hidráulica válida | Nuevos NULL, pérdida de filas por filtros/INNER JOIN; conflicto si ventanas se solapan | Preservar como contexto nullable; no asignar campaña histórica por proximidad ni TOP 1 arbitrario |
| `id_campana_parcela_control,modulo_id,nombre_modulo` | No hay identidad singular al grano parcela/día | **IMPACTO DE ESQUEMA** si se eliminan; semántico si se inventa MIN/MAX o se devuelve NULL | Mantener solo como campos de compatibilidad nullable cuando corresponda, o pasar contexto a relación separada; nunca fabricar módulo representativo |
| `flujo_m3_h,flujo_m3_d` | Una señal física por parcela/día | SUM histórico cae al eliminar repetición; promedio ponderado también puede cambiar | Preservar unidad; no usar SUM(DISTINCT valor) como deduplicación |
| `cu_drenaje_ppm,cu_refino_ppm,delta_cu_ppm` | Nombres `*_gl` en V4 | Renombrar rompe SELECT explícitos; valores raw en g/L no necesitan ×1000 para el simple cambio de alias | Exponer aliases correctos; aliases antiguos solo en adaptador documentado como obsoletos, conservando valor |
| `transferencia_cu_kg_d` histórico | Hoy calcula `/1000`; V4 kg sin división y nuevo t/d | **IMPACTO CRÍTICO** potencial: mismo nombre pasa a valor ×1000 para idéntico flujo/delta | No cambiar silenciosamente unidad bajo contrato oficial; versionar y documentar migración |
| `h_drenaje,ph_drenaje,cl_drenaje,fet_drenaje,fe2_drenaje,eh_drenaje`, equivalentes refino y `delta_h` | Química sigue disponible | Eliminar por centrarse solo en Cu rompe contrato; no todas las unidades son g/L | Preservar si fuentes V4 contienen esos analitos; no renombrar unidades no validadas |
| `secuencia_carguio,secuencia_retiro`; fechas inicio/fin de carguío, reposo, operación, drenaje y retiro | Contexto de varios módulos | MIN/MAX puede construir ventanas ficticias; valores no únicos | Agregar solo mediante regla aprobada; de otro modo NULL/relación de contexto |
| `dia_relativo_campana,fase_operacional` | Nueva campaña hidráulica | Cambian etiquetas/cómputos y valores fuera de ventana | Definir referencia del día y fase; no heredar prioridad CASE sin validar ventanas |
| `tmh_cargado,tms_cargado,humedad_promedio,sal_promedio,cut_tm_total,cus_tm_total,cu_insoluble_total,altura_modulo_max` | Contexto agregado parcela/campaña | Agregación indebida de leyes o repetición diaria de TMS | Conservar solo tras definir semántica: leyes no se suman; ponderadores no se inventan; no sumar contexto diario como producción |

### Unidades

Con el significado g/L confirmado por el usuario: `m³/d × g/L = kg/d`. El snapshot calcula `flujo_m3_d*(cu_drenaje-cu_refino)/1000`, por tanto representa t/d bajo el alias `transferencia_cu_kg_d`.

La relación ×1000 aplica **manteniendo idéntica observación física y delta**. No se espera una relación global ×1000 en totales antes/después porque además cambian duplicados, fechas y asignación de campaña. Separar estos efectos en la comparación.

### SELECT *, agregaciones y suposiciones de módulo

- La vista histórica usa proyección explícita; los consumidores encontrados de las cuatro fuentes también enumeran columnas. **No se encontró un `SELECT *` del tablero ni de esas cuatro fuentes** en las definiciones/código inspeccionados.
- No se encontró `SUM(flujo_m3_d)` o `SUM(transferencia_cu_kg_d)` desde el tablero en un consumidor del repositorio. No es correcto afirmar que un exportador específico esté sumando esas señales.
- Sí hay evidencia de que la vista **produce** repetición: parte de CPC, proyecta `modulo_id` y une flujo de parcela usando intervalo carguío–retiro (retiro NULL → 2099), no una ventana hidráulica exclusiva. Química se une después por parcela/PAD/fecha. Varias campañas/módulos o muestras pueden generar multiplicidad.
- La vista no agrega ni deduplica esas filas; el daño de una SUM downstream es un riesgo fundado, pero no un consumidor encontrado. El usuario aporta además demostración SQL de multiplicidad; no fue repetida en esta auditoría.
- Existen aplicaciones que asumen filas por módulo (reclamo), pero sus consultas no apuntan al tablero. No confundirlas con consumidor afectado.

## 6. Compatibilidad sin replicación física: propuesta, no implementada

1. **Vista física versionada:** una fila `pad_id+parcela_id+fecha`; medidas kg/d y t/d con nombres correctos. Cero o una campaña válida; fechas sin campaña conservadas conforme al contrato que se apruebe. Ante ventanas solapadas, resolver con regla explícita o señalar conflicto: no duplicar señal ni elegir campaña arbitrariamente.
2. **Contexto separado:** relación campaña/parcela/módulo con IDs CPC, secuencias, estados y variables materiales. Puede mostrarse en detalle, pero no contiene copias de las medidas físicas que se puedan sumar. Una relación BI uno-a-muchos mal utilizada aún puede duplicar medidas: documentar dirección de filtros y pruebas.
3. **Adaptador opcional de columnas legacy sobre la vista física:** proyección de una sola fila por clave física, mismo orden/tipos compatibles; conserva aliases antiguos cuando sea necesario. IDs singulares de módulo/CPC se devuelven solo si el contexto es inequívocamente único; en otro caso NULL tipado, sin MIN/MAX arbitrario. Esto mantiene forma, **no garantiza compatibilidad semántica** con clientes que exigen esos IDs no NULL.
4. Para el adaptador legacy, conservar el número histórico de `transferencia_cu_kg_d` (t/d mal nombrado) únicamente como campo obsoleto documentado; el contrato nuevo publica kg y t correctamente. No mezclar ambas interpretaciones bajo el mismo endpoint/versión sin transición explícita.
5. Mantener el oficial temporalmente permite transición, pero conserva su defecto mientras exista: marcarlo como legacy y no conectarle nuevos análisis. No declarar resuelto el problema para todos los consumidores hasta migrarlos y retirar ese contrato.

**Es imposible conservar simultáneamente una fila por módulo con medidas completas, todas las identidades originales y una única señal física sumable por parcela/día.** Repartir el flujo por cantidad de módulos o mostrarlo solo en el primer módulo introduciría reglas nuevas y resultados engañosos; no se recomienda.

Preservación prioritaria: claves físicas, descriptores, fecha, flujo, química completa, campaña nullable, unidad explícita y trazabilidad de fuente. CPC/TMS/leyes/altura pueden preservarse como contexto agregado **solo con significado y método aprobados**, preferentemente separado del hecho diario. No fabricar valores para mantener columnas llenas.

## 7. Riesgos y checklist antes de PROD

- [ ] Obtener definición actual y contrato de columnas (nombre, ordinal, tipo, precisión, nullable), permisos y dependencias de oficial y fuentes. Los snapshots no sustituyen este paso.
- [ ] Buscar consumidores reales con dependencias SQL, SQL dinámico, jobs, Query Store/logs disponibles, modelos/datasets Power BI, Excel y aplicaciones externas. Documentar propietario de cada contrato.
- [ ] Comparar DDL TEST V4 completo contra oficial: cada columna eliminada/renombrada, unidad, política NULL y cambio de dominio de filas.
- [ ] Verificar una fila por PAD/parcela/fecha y unicidad por día de flujo, drenaje y refino antes de JOIN. Varias muestras requieren regla aprobada, no MAX/AVG de conveniencia.
- [ ] Validar mapeo PAD: snapshot tablero usa SULF=65 y admite pads fuera de (1,65); otras rutas usan 2. No asumir intercambiabilidad de IDs.
- [ ] Validar campaña cero/una por ventana hidráulica, bordes inclusivos/exclusivos, solapamientos y días sin campaña. No usar campaña histórica con retiro abierto como comodín.
- [ ] Confirmar idéntica normalización operacional en drenaje/refino, incluidos umbral inicial y horas límite; no desplazar flujo sin regla aprobada.
- [ ] Comparar por clave física primero, luego agregados día/mes/campaña: aislar eliminación de duplicados, reasignación temporal y conversión de unidad. Conservar NULL y negativos de delta salvo decisión funcional expresa.
- [ ] Probar numéricamente `kg = flujo × delta_gl`, `t = kg/1000`; validar tipos/precisión. No exigir igualdad de totales legacy multiplicados.
- [ ] Probar clientes explícitos y SELECT * externos: nuevos NULL de campaña/módulo, filtros, joins, bindings ordinales, exportadores y etiquetas de unidad.
- [ ] Probar que sumar TMS/leyes de contexto por fecha no se presente como balance físico; no agregar columnas de contexto con regla inventada.
- [ ] Ensayo y comparación documentados, backup/rollback, despliegue coordinado de fuentes y vista y aprobación antes de tocar PROD. Nada de esto se ejecutó en esta auditoría.

## 8. Archivos de evidencia y verificación local

- [ARCHIVOS.md](ARCHIVOS.md): rutas exactas y líneas de cada referencia literal a los cinco objetos.
- [referencias_objetos.csv](referencias_objetos.csv): inventario completo de esas coincidencias.
- [referencias_en_definiciones.csv](referencias_en_definiciones.csv): objeto SQL, catálogo y línea interna; distingue definición de consulta.
- [dependencias_encontradas.json](dependencias_encontradas.json): registros de los archivos de dependencias que nombran los objetos. Si está vacío significa sin registros encontrados, no ausencia de dependencias en SQL Server.
- [coincidencias_columnas.csv](coincidencias_columnas.csv): usos nominales; no es un grafo de linaje ni una lista automática de consumidores.
- [contrato_historico.json](contrato_historico.json): las 51 columnas del tablero según `report_export/exports/auditoria_ley_srr_202609/columnas.json`, con nombre, tipo base y ordinal. Este catálogo no contiene toda la precisión/nullabilidad necesaria para aprobar compatibilidad. La búsqueda de columnas incluye las 51, no solo las enumeradas en la solicitud.
- Los siete `*.snapshot.sql` del directorio se extraen del catálogo de septiembre con encabezado de procedencia. No se ejecutaron.
- `auditar_local.py` reproduce búsqueda estática; no importa módulos de la aplicación ni utiliza credenciales/conexiones.

Solo se agregaron documentos/evidencias de esta auditoría. No se modificaron objetos, datos o código funcional. No se ejecutaron tests de integración ni SQL. Validación local: inventario, enlaces y `git diff --check`.
