# Alcance compartido (sin auditar analitos)

| Acción | Selector | Resolución de corte | Riesgo común |
|---|---|---|---|
| Torres / Editar comentarios | report-fecha-* | preparar_paquete_editor_representatividad → refrescar_representatividad_para_exportacion → fetch_fecha_corte_operacional_representatividad | Sí: fallo reproducido por horizonte tot_TM. |
| Torres / Publicar-materializar | Mes normalizado | _materializar_paquete_reporte_torre_oficial → mismo refresco/corte | Sí al crear snapshot nuevo. No ejecutado. |
| Torres / Descargar Excel oficial | Mismo selector | exportar_excel rama representatividad_torres (:7695) busca reporte oficial activo y usa fecha_corte_operacional del snapshot | NO vuelve a resolver este corte LIVE; puede descargar snapshot existente. Puede fallar por ausencia de oficial activo, error distinto. |
| Análisis TM / Excel | Mismo selector, tipo reporte_turno | preparar_paquete_reporte_turno_emision → refrescar_dependencias_reporte_turno_emision → fetch_fecha_corte_apilado_tmh_report | NO comparte SELECT tot_TM/bitácora. Comparte infraestructura RTO con otros flujos y puede fallar por otra cobertura. |
| Datos Conciliados / Excel | Mismo selector, tipo prod | preparar_paquete_datos_conciliados_emision → refrescar_dependencias_datos_conciliados_emision → coordinador RTO → corte apilado | NO misma condición; comparte ruta apilado con Análisis TM. Mantiene calendario completo para DC. |

El corte apilado (:2072) usa `v_contingencia_totalizador_diagnostico_turno`: cuatro claves CV008/CV108 × A/B, criterios PI/TUM desde septiembre, máximo global, no horizonte tot_TM. No se concluye que esos reportes funcionen hoy: sus refrescos no fueron ejecutados. Torres, después de pasar su propio corte, exige compatibilidad con el corte RTO. Eso es un bloqueo posterior potencial, no el actual.
