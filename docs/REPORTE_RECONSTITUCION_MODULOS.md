# Informe de Reconstitución de Módulos — 27-10-2026

Restaurado en `reconstitucion/panel.py`, mediante `informe_modulos.py` y las dos plantillas del exportador original. El gráfico conserva una fila por pad/campaña/módulo y los turnos TA/TB en el eje temporal.

El botón **Descargar informe de módulos (XLSX)** permite elegir el pad. Se habilita después de cargar un resultado del modelo con identidad de Caso/run. Cambiar el Caso o su run invalida la descarga del resultado anterior. La exportación reutiliza la distribución de masa cargada; consulta calidad por fecha/turno con SELECT acotados únicamente al descargar, y la conserva en memoria por token/pad. No ejecuta SP ni escribe en la base.

La hoja `MODULOS` conserva los encabezados completos y formato original: A:DU para Óxidos y A:DP para Sulfuros. Incluye TMH/TMS, altura real, leyes, finos, consumo de ácido, solubilidad, composición de origen, granulometría y humedad disponible. Los campos de calidad se ponderan por la masa seca asignada a cada módulo/turno; la humedad de perfil se promedia por transportador con TMH y luego por módulo/turno con los pesos TMS. El Cu fino es TMS × CuT / 100. No representa una nueva reconciliación independiente de leyes o finos.

Los campos sin fuente canónica quedan vacíos. Se eliminan hojas auxiliares de la plantilla con #REF! o datos anteriores; no se presentan como informes calculados. `DETALLE` expone cobertura, alcance parcial/completo y fechas observadas; `CASO` incluye identidad y ventana. Un pad sin apilamiento conserva el encabezado y una explicación sin inventar módulos. Fecha de término solo se publica cuando el avance observado indica cierre; un módulo puede haber terminado dentro del caso y aun tener masa parcial porque comenzó antes.

Verificación: snapshots identificados Caso 10009/run 10082 (01–07 septiembre de 2026) y Caso 10013/run 10145 (01–12 octubre de 2026), más calidad SELECT capturada el 27-10-2026 (14 y 24 turnos SU respectivamente). Estos informes reproducen dichos snapshots; no certifican que el run oficial no haya cambiado después de su captura. OX no tiene apilamiento en ambos intervalos. Todos los módulos SU tienen cobertura de calidad de 100 % según solubilidad; cada campo conserva sus faltantes si los hubiera.

Las masas exportadas cierran con `shift_table`: 269.177,27418 t TMS para 10009 y 728.062,40730 t para 10013. La comparación con los archivos Óxido(5)/Sulfuro(5) utiliza la hoja `MODULOS`, campaña+módulo y fecha D de término de carguío; las fechas de reposo/humectación/riego no definen pertenencia al carguío.

Caso 10009: módulos C11/M134 y M135 parciales. Caso 10013: C12/M4 y M8 parciales; M5/M6/M7 completos. Sus diferencias TMS frente al Excel publicado son −13,8094 %, +2,9691 % y +6,2259 %. No se alteró el motor de reconstitución para forzar coincidencia. No se calcula error relativo de masas parciales contra módulos completos.

Pruebas: 63 en staging; 9 de exportación/integración repetidas en el destino instalado. Navegador contra la aplicación aislada con el panel activo y snapshot 10013: descarga XLSX válida, nombre Caso/run correcto, sin errores JS/HTTP y botón deshabilitado al cambiar Caso. La calidad se inyectó desde el SELECT congelado para esa prueba; los 547 ms medidos no representan una descarga con SQL en frío. La sesión local del usuario y la base no se modificaron.

Evidencias: `../curvas_recon/auditorias/reconstitucion_informe_comparacion_20261027/`; informes descargables: `../curvas_recon/outputs/reconstitucion_modulos_casos_20261027/`.

Si el proceso de Dash ya estaba iniciado sin recarga automática, reiniciar `main.py` para incorporar el botón.
