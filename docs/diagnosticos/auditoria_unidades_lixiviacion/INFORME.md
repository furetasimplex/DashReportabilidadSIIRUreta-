# Auditoría estática de unidades y aliases químicos — SIIR

03/10/2026. Solo repositorio; sin conexión a SQL, ejecución de consultas, cambios funcionales, PROD, commit ni push.

## Resultado

Se confirma en los snapshots el problema del tablero legacy: los aliases `cu_drenaje_ppm`, `cu_refino_ppm` y `delta_cu_ppm` transportan Cu en **g/L**, según el contexto validado por el usuario, y `transferencia_cu_kg_d` calcula **t Cu/d** porque divide por 1000. Corregir el valor bajo el mismo nombre sería un cambio de contrato potencialmente crítico, no un ajuste cosmético.

También hay aliases coherentes (`cu_drenaje_gl`, concentraciones de drenaje `*_gl` del SP de flujo) y rutas cuyo significado dimensional no se puede cerrar con el código disponible. En particular, **no se extrapola** la validación de Cu drenaje/refino a todos los `*_cu_pp`, a plomo/azufre, a todos los analitos químicos ni a concentraciones SX/EW.

## Alcance y método

Se buscaron `cu_pp` y columnas terminadas en `_cu_pp`, los aliases solicitados y sufijos `_ppm`, `_gl`, `_kg_d`, `_t_d`, además de `cu_g_l`. Se examinaron las fórmulas de caudal/volumen por concentración; un inventario adicional recoge candidatos textuales de multiplicación alrededor de esos términos.

Se incluyen archivos textuales ocultos/ignorados, SQL, Python, catálogos JSON, CSV, Markdown y copias `release/`; se excluyen Git, entornos, dependencias y los entregables nuevos para evitar autorreferencias. No se interpretaron archivos binarios de reportes ni modelos publicados fuera del repositorio. El paquete V2 preparado en paralelo es una propuesta, no evidencia de implementación existente.

`OCURRENCIAS.csv` es la matriz detallada **por alias y línea**: archivo/objeto, fuente cuando demostrable, unidad sugerida, unidad acreditada, conversiones cercanas, consumidor, clasificación y riesgo. Repeticiones del mismo alias en una línea se consolidan. En catálogos con `definition`, la línea corresponde al cuerpo del objeto, no a la línea física del JSON; se identifica el catálogo y objeto. En archivos SQL/CSV/Markdown es la línea del archivo.

`FORMULAS_CANDIDATAS.csv` contiene candidatos por proximidad textual, incluidas expresiones multilínea. No prueba que cada coincidencia sea una multiplicación física: puede incluir comentarios o SELECT *. Las conversiones cercanas en el inventario tampoco demuestran linaje por sí solas. Las conclusiones confirmadas son las de la matriz razonada siguiente.

Los catálogos `report_export/exports/auditoria_ley_srr_202609/catalogo.json`, `objeto_firmas_final.json`, `columnas.json` y `report_export/exports/diagnostico_fase4/catalogo_dev.json`, y los archivos `auditoria_reclamo/`/`monitor_pi_tum/validacion/`, son evidencia guardada, no estado live. Copias de un mismo objeto no equivalen a consumidores adicionales. Las referencias de auditorías previas se identifican como documentación.

## Matriz razonada de unidades y riesgos

| Archivo / objeto | Fuente y consumidor conocido | Nombre sugiere | Fórmula / unidad demostrada | Conversión | Clasificación | Riesgo de corregir |
|---|---|---|---|---|---|---|
| `vw_tablero_lixiviacion_final`, catálogos; copia `../tablero_lixiviacion_v4_impacto/vw_tablero_lixiviacion_final.snapshot.sql` | d.cu_pp de `vw_drena_concentrados_*_long`; salida de vista, sin downstream ejecutable encontrado | `cu_drenaje_ppm`: ppm | Proyección directa; g/L para Cu drenaje validado | Ninguna | **alias engañoso** | Renombrar rompe consultas/bindings; no aplicar ×1000 para cambiar solo el alias |
| Mismo objeto | r.cu_pp de `vw_riego_*_refino_base`; salida tablero | `cu_refino_ppm`: ppm | Proyección directa; g/L para Cu refino validado | Ninguna | **alias engañoso** | Mismo riesgo; la fecha operacional es un cambio separado |
| Mismo objeto | d.cu_pp − r.cu_pp | `delta_cu_ppm`: ppm | Resta de g/L = g/L; NULL si falta un operando | Ninguna | **alias engañoso** | No convertir NULL a 0 ni truncar negativos para limpiar el gráfico |
| Mismo objeto | f.flujo_m3_d × (d.cu_pp−r.cu_pp) | `transferencia_cu_kg_d`: kg/d | m³/d × g/L /1000 = t Cu/d | `/1000.0` | **inconsistencia dimensional** entre nombre y resultado | Quitar división cambia valor ×1000 para idéntica observación; requiere contrato versionado |
| `sp_razon_lixiviacion`, catálogo y `../drenaje_operacional_20261002/sp_razon_lixiviacion.snapshot.sql:226–238` | Unpivot drenaje; s.cu_pp; salida del SP | `cu_drenaje_gl`: g/L | ROUND(s.cu_pp,4), misma unidad validada | Redondeo, sin escala | **correcto** | No necesita conversión de unidad. Cambio de alias seguiría afectando clientes no identificados |
| Mismo SP, `cu_diario_ton`, `cu_acum_ton` | Caudal diario y s.cu_pp; sumas acumuladas en salida | t Cu/d y t Cu acumulado | caudal_m3_dia × cu_pp /1000; acumulado SUM del mismo producto | `/1000` | **correcto**, condicionado a que caudal_m3_dia sea m³/d como declara el SP | Validar factor de caudal del SP; el ISNULL(cu_pp,0) ya existente cambia ausencia a cero y NO se copia al nuevo contrato |
| `sp_flujo_riego_drenaje`, snapshot anterior:232–234 | #drena desde unpivot; salida SP | `cu_drenaje_prom_gl`, `cu_drenaje_max_gl`, `cu_drenaje_min_gl` | AVG/MAX/MIN de Cu g/L conservan g/L | ROUND(...,4) | **correcto** en dimensión | JOIN por módulos puede cambiar ponderación sin cambiar unidad; no confundir ambos defectos |
| `vw_drena_quimica_ingest`, catálogos / snapshot anterior | Tablas raw OX/SULF via CROSS APPLY → `cu_gl`; consumidor posterior no acreditado | g/L | NULLIF(CAST(v.cu_pp AS FLOAT),0), conserva g/L de Cu drenaje | Sin escala; cero→NULL existente | **correcto** para alias Cu | No extender esta conclusión a h_p/ph/cl/fet/fe2/eh. No tocar NULLIF como parte de renombre |
| `v_drena_oxido_unpivot`, `v_drena_sulfuro_unpivot`, `vw_drena_concentrados_*_long` / `*_parcela` | pN_cu_pp de raw; consumidores SP flujo/razón/control o tablero/parcela según ruta | `cu_pp` ambiguo, no declaración explícita ppm | Cu drenaje en g/L por validación aportada; CAST a decimal no cambia unidad | CAST/UNPIVOT, sin ×1000 | **no determinable con evidencia disponible** respecto al significado histórico de “pp”; unidad Cu de estas rutas sí acreditada | No renombrar globalmente `cu_pp`; requiere inventario de dependencias por objeto |
| `vw_riego_oxido_refino_base`, `vw_riego_sulfuro_refino_base` | refino_cu_pp de riego_concentrados_* → cu_pp; tablero | Nombre ambiguo | g/L para Cu refino confirmado; proyección directa | Ninguna | **no determinable con evidencia disponible** para nomenclatura histórica; no error de cálculo acreditado | La unidad validada de refino no acredita otros campos PLS/bleed de la misma tabla |
| `siir_curated.vw_siir_drena_concentrado_parcela_long` | pN_cu_pp y otros analitos → valor_raw/valor; resúmenes siir_mart | `analito_codigo=cu_pp`, valor sin sufijo unitario | Cu raw g/L en esta ruta; valores de otros analitos no acreditados por ese hecho | TRY_CONVERT decimal y reglas/flags de calidad, no escala universal demostrada | **no determinable con evidencia disponible** como contrato unitario multianalito | Añadir metadatos por analito antes de conversiones globales; no asumir unidad común |
| `sp_calcular_balance_flujos_modelo6_v2`, F37/F38 y otros; copias SQL balance/datos conciliados | `conc_cu.dump_dpls_cu`, `dump_feed_cu` → cu_g_l; #valores_m6.Ley_Cu | g/L de entrada, “Ley_Cu” de salida | SUM(flujo×cu_g_l)/SUM(flujo) conserva concentración; luego /10 | `/10.0`, no /1000 | **conversión dudosa** como ley másica si no se documenta densidad/convención | No corregir: puede ser convención de balance. Verificar unidad real de entrada, Tonelaje y consumidor |
| `modelo6_v2`, F44 (snapshot:5009–5042), F47 (5234–5247) | ingreso_piscina_pls_cu_pp y conc_cu.sulfuros_pls_a_sx_cu; #valores_m6, F25/F29 | Cu_g_L / Ley_Cu | F44 ponderación por flujo; F47 AVG; ambas /10 hacia Ley_Cu | `/10.0` | **conversión dudosa** si Ley_Cu se interpreta como % masa | El Cu de refino validado no confirma automáticamente el Cu PLS; preservar fórmula hasta contrato completo |
| `modelo6_v2` sección Riego_Con_Ley/Resumen:4722–4807 | Concentraciones y Riego_Base; #valores_m6 | Cu_g_L, pero SUM(Volumen) AS Tonelaje | SUM(Volumen×Cu_g_L)/SUM(Volumen)/10 | `/10.0`; volumen llamado Tonelaje | **conversión dudosa** / semántica volumen-masa pendiente | Si Volumen es m³ y Cu g/L, producto es kg Cu; su uso como % másico requiere explicación adicional |
| `Ley_i_gL`, `Ley_f_gL` en `auditoria_reclamo/raw/definiciones_externas_relevantes.csv:5131–5147` y otras líneas inventariadas | conc_cu (refino/ILS, según bloque), volúmenes inicial/final llamados TMS; balance | g/L | Diferencia (Vf×Cf−Vi×Ci)/(Vf−Vi), luego /10 | `/10`; COALESCE existentes | **conversión dudosa** | No atribuir TMS real solo por alias. Identificar fuente de V y convención de Ley_Cu antes de cambiar |
| `conc_er_t[a-d]_gl`, `er_ecc[1-3]_gl`, `ep_ecc[1-3]_gl` en SQL balance/datos conciliados | sx_ep_flujos_niveles / tags SX-EW según columna y objeto; snapshots de SP | g/L por sufijo | Promedios/NULLIF/conversiones en distintas rutas; unidad de medición no acreditada solo por nombre | Varía por ocurrencia; CSV conserva contexto | **no determinable con evidencia disponible** | No homologar con drenaje; revisar analito, solución, instrumento y contrato del SP |
| `ley_refino_oxido_gl`, `ley_feed_dump_gl`, `ley_dpls_gl`; `electrolito_rico_[a-d]_cu_gl` | `columnas.json`: tags_sx_ew y backups/rescate; ver inventario metadata | g/L | Metadatos de columna sin fórmula suficiente | No demostrada | **no determinable con evidencia disponible** | Algunas apariciones son solo backups; no declararlas consumidores vivos |
| `agua_lavado_t[a-d]_gl`, `organico_cd_t[a-d]_o[c-d]_gl` | `columnas.json`: sx_ep_flujos_niveles y backups | g/L por nombre | Analito/unidad efectiva no demostrados | No demostrada | **no determinable con evidencia disponible** | No asumir que sean Cu ni que compartan densidad/interpretación de solución acuosa |
| `pb_ppm`, `s_ppm` | `columnas.json:17274–17428`: data_calidad_catodica y backups | ppm | Sin fórmula/calibración encontrada en esta evidencia | Ninguna demostrada | **no determinable con evidencia disponible** | NO convertir a g/L ni clasificarlos como alias incorrectos por analogía con el tablero |
| `delta_gl` en informe previo | Documentación, no campo SQL localizado con ese nombre | g/L | Ejemplo de fórmula, no implementación | kg/1000 explicado | **correcto** como explicación dimensional | No contarlo como consumidor funcional |

## Lectura dimensional y distinción de errores

- `1 g/L = 1 kg/m³`; por ello `m³/d × g/L = kg/d`. Dividir esa masa por 1000 da t/d. Esta identidad **no afirma que ppm sea g/L**.
- Para un volumen acumulado m³, el producto entrega kg acumulados, no kg/d: el intervalo de la medida debe estar explícito. Un alias `_d` no demuestra que la fuente sea diaria.
- `g/L /10` equivale numéricamente a porcentaje masa/volumen (g por 100 mL). No demuestra porcentaje masa/masa sin densidad/convención. Si el modelo usa volumen como “Tonelaje”, la combinación posterior `/100` puede producir algebraicamente t Cu, pero eso no acredita la etiqueta “ley másica”. Se requiere trazabilidad completa antes de declarar un error numérico.
- AVG/MAX/MIN conservan la dimensión de una concentración. Un promedio mal ponderado, un JOIN multiplicado o un cero convertido a NULL pueden alterar el resultado sin ser conversiones de unidad.
- No se propaga a pH, potencial Eh, cloruros, hierro o acidez una unidad validada solo para Cu. No se asume unidad de `h_p` ni de `delta_h` por nombre.

## Consumidores y criticidad

La auditoría downstream previa no encontró un cliente ejecutable del tablero en Python/exportadores/API del repositorio. Sí encontró dependencias SQL de drenaje/refino al tablero y de drenaje a las vistas parcela. Eso no excluye consultas externas o modelos BI publicados.

Los SPs de balance/datos conciliados son consumidores de otras fuentes químicas; compartir `cu_g_l` o `Ley_Cu` no los convierte en consumidores del tablero. Las rutas y líneas de sus expresiones están inventariadas, sin proponer reemplazos globales.

**Prioridad alta:** versionar el contrato de transferencia y explicitar g/L en el tablero nuevo; no corregir silenciosamente la oficial. **Prioridad de investigación:** convenciones volumen/Tonelaje/Ley_Cu y conversiones /10. **Sin evidencia de corrección necesaria:** pb_ppm/s_ppm y analitos cuya unidad no esté documentada.

## Entregables y límites de exhaustividad

- [OCURRENCIAS.csv](OCURRENCIAS.csv): cada alias/línea encontrado con clasificación conservadora; “no determinable” es un resultado explícito, no una unidad inferida.
- [FORMULAS_CANDIDATAS.csv](FORMULAS_CANDIDATAS.csv): expresiones candidatas con contexto y límites de interpretación. No es un parser de linaje SQL ni certificación de todas las fórmulas.
- [EVIDENCIA_FORMULAS.md](EVIDENCIA_FORMULAS.md): extractos numerados de cuerpos SQL históricos para los hallazgos principales.
- [ARCHIVOS.md](ARCHIVOS.md): rutas exactas encontradas. Los CSV aportan líneas y objetos cuando están disponibles.
- [METADATOS_COLUMNAS.csv](METADATOS_COLUMNAS.csv): 448 columnas con identificadores químicos en el snapshot de `columnas.json`, conservando tabla/esquema/tipo/ordinal; permite atribuir las coincidencias de metadata al objeto correcto sin inferir unidad.
- `auditar_local.py`: reproducción local, sin credenciales/conexiones/importación de aplicación.

No se acredita exhaustividad sobre SQL dinámico construido, archivos binarios o sistemas externos. No se corrigió ningún alias, fórmula, conversión, tratamiento NULL ni código funcional. Las validaciones fueron locales: inventario, documentación y `git diff --check`; no ejecución SQL ni pruebas contra bases.
