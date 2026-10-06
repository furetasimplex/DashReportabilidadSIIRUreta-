# Recomendaciones de interfaz — sin implementar

1. Mantener `Refrescar vista` como acción de consulta, con texto que indique que no sincroniza ni recalcula. Hacer que el cambio de período dispare consultas o avisar que hay que pulsarlo, porque numerosos callbacks usan fechas como `State`.
2. Mover `Actualizar secuencia de módulos` a **Módulos → Herramientas avanzadas**. Describirlo como mantención extraordinaria de secuencia y alertas, no como paso previo a Reprocesar. `db.recalcular` ya lo ejecuta en el orden seguro después del primer sync.
3. Tras Insertar/Actualizar base, mostrar CTA contextual **Reprocesar período** y advertir que guardar no rehace `calculo_diario`. Tras Reprocesar, mostrar rango efectivo y resumen por etapa, incluidos sync, secuencia, CV25/horas y cálculo; no insinuar que la fila del módulo quedó incluida si la ventana de automatización lo dejó fuera.
4. Diferenciar **bloqueos activos** de **eventos históricos**. El control de 30 días actualmente cuenta filas `ALERTA%` repetibles y se etiqueta `BLOQUEANTE`. Evaluar estado presente por módulo y dejar historial como evidencia. No modificar reglas hasta acordar definición de alerta activa.
5. Impedir publicación en backend cuando exista un bloqueo vigente aplicable al período; hoy el color rojo del semáforo es solo visual. Mostrar en confirmación el rango efectivo del `MERGE`, que puede iniciar en `fin - 7 días`, y recordar que Publicar no sincroniza ni calcula Reclamo.
6. Mostrar ruta y estado de aprobación de ajustes. Hoy Registrar crea `PROPUESTO`, pero este panel no ofrece aprobación. Evitar que se interprete como aplicado.
7. Quitar el PAD global. Las opciones de módulo de Ajustes ya incluyen PAD en la etiqueta; conservar filtros PAD locales en cada análisis y en Datos base. Ver `DEPENDENCIAS_FILTRO_PAD.md`.

Base: callbacks en `reclamo/panel.py`, helpers en `reclamo/db.py` y definiciones SQL DEV capturadas en `live_definitions.json` el 2026-10-06. No se cambió UI ni lógica.
