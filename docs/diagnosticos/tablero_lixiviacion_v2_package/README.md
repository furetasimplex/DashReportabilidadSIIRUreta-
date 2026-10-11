# Tablero lixiviación V2 — evidencia LIVE incorporada parcialmente

04/10/2026. **Candidato completo para revisión manual; NO listo para despliegue.** Sin conexión a SQL, ejecución SQL, cambios en oficial/PROD, commit ni push.

## Estado actualizado: TEST V4 funcional VALIDADO LIVE

Ver [VALIDACION_LIVE_V4.md](VALIDACION_LIVE_V4.md): resultados reportados de unicidad, conservación de flujo/química, campaña y transferencia. Volúmenes fuente/V4: OX **2908120.161887**, SULF **9260436.238434**. Ceros químicos del 10-09 proceden del raw decimal(12,2), sin redondeo adicional de vistas.

El contrato LIVE informado tiene **33 columnas**, pero el mensaje no incluye sys.columns: quedó un marcador de posición. El candidato local tiene **25 columnas**. Falta recibir nombres, orden, tipos, precisión, escala y nullability para conciliarlos; no se inventan las ocho restantes. La validación reportada de tipos V4 no acredita el detalle del contrato local.

Siguen pendientes: despliegue V2, auditoría LIVE de consumidores y promoción/reemplazo oficial. La guarda permanece deshabilitada. Las instrucciones de ensayo siguientes corresponden al candidato local y no niegan las pruebas ya realizadas sobre TEST V4.

## Evidencia y alcance

[EVIDENCIA_LIVE_USUARIO.txt](EVIDENCIA_LIVE_USUARIO.txt) conserva el texto recibido. `VALIDADO LIVE` significa evidencia reportada por el usuario, no pruebas ejecutadas aquí. Los snapshots previos no se convierten en estado live.

| Componente | Alcance |
|---|---|
| Drenaje operacional | VALIDADO LIVE: CASE con fecha >=2026-06-01T21:00:00 y hora >=20; OX PAD1/SULF PAD2, dimensión por PAD+número |
| Multianalito | VALIDADO LIVE: siete analitos, timestamp raw, casts originales decimal(12,2), unicidad de fecha/parcela en pruebas aportadas |
| Refino operacional | VALIDADO LIVE: misma regla desde raw; sin nuevos casts; 4120 y 4270 fechas únicas OX/SULF |
| Campaña hidráulica | VALIDADO LIVE: preagregación MIN primer/MAX último riego y LEAD; extremos inclusivos, corte día anterior a próxima campaña; último riego NULL no asigna |
| Fuera de ventana | VALIDADO LIVE: conservar fila, campana_id/numero_campana NULL y estado_asignacion=FUERA_VENTANA_RIEGO; no descartar caudales pequeños |
| Cu y fórmulas | VALIDADO LIVE: g/L, kg/d=flujo×delta, t/d=kg/d/1000; 672×(2,03−0,28)=1176 kg/d=1,176 t/d |
| Hecho físico | Diseño aprobado PAD+parcela+fecha; contexto modular separado |
| Proyección funcional TEST V4 y conservación | **VALIDADO LIVE** según actualización del usuario |
| Tipos LIVE33 frente a candidato local25 | Validación LIVE reportada; pendiente incorporar sys.columns y conciliar contrato local |

Es normalización de fecha operacional, **no timezone**. No desplazar flujo ni normalizar dos veces una fecha operacional. El 01/06 a las 20:00 no cumple el umbral inicial 21:00; se conserva el CASE literal aprobado.

## Composición candidata

`01_create_v2_candidate.sql` crea únicamente el objeto NUEVO `inventar_SpcHidr.vw_tablero_lixiviacion_final_v2`; no modifica la oficial ni fuentes compartidas. Ya no hay SELECTs fuente NULL ni contratos `_test_v2`. La guarda de ensayo permanece deshabilitada y el lote revierte con ROLLBACK.

- UNION ALL de las vistas `vw_flujos_reales_*_long` conduce las filas, sin agregado ni filtro por campaña.
- Drenaje se normaliza inline desde `vw_drena_concentrados_*_long.fecha_registro` raw, conservando los siete valores y sus casts originales. No se usa su columna fecha ya transformada. Esta composición inline es candidata, no una vista final ejecutada LIVE.
- Dimensión: `p.numero=d.nro_parcela_pad AND p.id_pad=d.pad_id`. LEFT JOIN conserva en diagnóstico las correspondencias ausentes. Su unicidad y el JOIN final quedan pendientes de prueba.
- SULF P29–P32 permanece en fuente/CTE raw; no se elimina ni remapea. El flujo físico P1–P28 determina las filas finales.
- Refino se normaliza inline desde `vw_riego_*_refino_base.fecha_registro`, como el fragmento conceptual recibido; hereda sus tipos. No se supone que una vista operacional conceptual ya esté publicada.
- Ventana: se copia agrupación `(pad_id,campana_id,numero_campana,parcela_id)`, MIN/ MAX de riego y LEAD por PAD/parcela ordenado por primer riego/campaña. Se aplican ambos extremos inclusivos. No hay apertura a 2099.
- La preagregación hidráulica MIN/MAX **sí está autorizada explícitamente**; no fabrica un módulo ni agrega TMS, leyes, altura, secuencias o IDs CPC.
- No se deduplican campañas mediante DISTINCT/TOP 1 ni se oculta multiplicidad. Si una fecha produce varias coincidencias, falla la validación; no se inventa otro estado o regla.

## Proyección local de 25 columnas — pendiente conciliación con LIVE33

Orden exacto del candidato:

```text
pad_id, parcela_id, fecha,
campana_id, numero_campana, estado_asignacion,
flujo_m3_h, flujo_m3_d,
cu_drenaje_gl, h_drenaje, ph_drenaje, cl_drenaje, fet_drenaje, fe2_drenaje, eh_drenaje,
cu_refino_gl, h_refino, ph_refino, cl_refino, fet_refino, fe2_refino, eh_refino,
delta_cu_gl, transferencia_cu_kg_d, transferencia_cu_t_d
```

Sin campaña: IDs/número NULL y FUERA_VENTANA_RIEGO. Con campaña: CAMPANA_HIDRAULICA, nombre del diseño candidato aportado, sin afirmar validación de la proyección final.

Se retiran las propuestas anteriores `estado_asignacion_campana`, `EN_VENTANA_RIEGO`, el contador público y el estado de conflicto. Los conflictos se buscan en validaciones. No se incorpora `delta_h`, fórmula no requerida por la evidencia actual.

Los siete analitos por lado se conservan; únicamente Cu tiene g/L confirmado aquí. No atribuirlo a pH, Eh, acidez, hierro o cloruros. IDs raw/timestamps están en CTE para diagnóstico, no como nuevas columnas finales aprobadas.

No se agregan casts al flujo/refino. Drenaje hereda decimal(12,2) de fuente. Los tipos LIVE fueron reportados como validados; falta recibir su detalle para documentar precisión, escala y nullability y contrastarlos con este candidato local.

## Validación preparada, no ejecutada

`02_validate_v2_readonly.sql` comparte exactamente los CTE de 01 a través de `generar_candidato.py`. Incluye claves, conservación exacta bidireccional del flujo, cobertura, duplicados químicos, dimensión, cardinalidad tras JOIN, campaña, filas fuera, número/estado, Cu de fuentes y fórmulas/NULL/negativos. EXCEPT no sustituye conteos porque elimina duplicados.

Referencias reportadas para 01/06–10/09/2026, **no resultados ejecutados de V2**:

| PAD | Claves | 1 campaña | Sin campaña | Múltiples |
|---|---:|---:|---:|---:|
| OX / 1 | 3264 | 2219 | 1045 | 0 |
| SULF / 2 | 2856 | 1839 | 1017 | 0 |

OX fuera: 939 ceros y 106 positivos, total reportado 6,128278 m³; positivos con flujo_m3_h<0,01. SULF fuera: 1017 ceros. Se conservan todos. No convertir cifras reportadas redondeadas en tolerancias inventadas; comparar valores fuente/V2 en un corte estable.

La unicidad previa CPC+fecha con drenaje/refino coordinados **no demuestra todavía** unicidad física PAD+parcela+fecha. Repetir fuera del período validado; revisar ventanas degeneradas, fechas NULL, dimensión y numero_campana inconsistente sin cambiar la regla aprobada por iniciativa propia.

## Revisión manual futura y convivencia

1. Revisar evidencia y [MATRIZ_CONTRATO.md](MATRIZ_CONTRATO.md). La lista legacy procede de metadata histórica; las reglas nuevas proceden de la evidencia aportada.
2. Corroborar dependencias autorizadamente con 03; jobs/DMV siguen opcionales/separados. Nada se ejecutó aquí.
3. Revisar 01: deshabilitado y con ROLLBACK incluso al habilitarlo. Para probar 02/04 durante un ensayo, integrarlos antes del rollback en un lote revisado o preparar una transacción manual separada en la misma sesión. Ejecutar 01 completo y luego 02 no sirve: V2 ya se revirtió. No ejecutar fragmentos incompletos de TRY/CATCH.
4. Validar 02 y comparar contrato con 04: metadata legacy/V2 más lista exacta candidata. No exigir igual número de filas legacy/V2.
5. Preparar promoción separada únicamente después de validación explícita de proyección, tipos y conservación. Este paquete no contiene COMMIT de promoción.

Legacy y V2 conviven. `transferencia_cu_kg_d` cambia significado entre versiones: legacy entrega t/d, V2 kg/d. Migrar consulta, etiquetas y conversiones conjuntamente. Rollback sigue siendo retirar consumidores de V2, no restaurar legacy ni borrar TEST/backups; ver 05.

Verificaciones locales: generación reproducible, contrato, guardas, enlaces y git diff --check. No se compiló ni ejecutó T-SQL.
