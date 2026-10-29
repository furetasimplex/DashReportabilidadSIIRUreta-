# Gráfico de Reconstitución — réplica del original

Actualizado el 27-10-2026 por solicitud del usuario. Fuente visual: `C:/Users/5330/Desktop/Reconstitucion/reconstitucion/panel.py::fig_gantt`, que monta `Reconstitucion/app.py`.

Reportabilidad recupera dos carriles por pad/campaña/módulo: naranja para días con volumen medido, como ventanas operacionales de 08:00 a 08:00; azul para el horario estimado. Se conservan barras horizontales, colores naranja/azul, eje de fechas, leyenda horizontal, identificación de módulo y detalle al pasar el cursor. No se agregan marcadores de cambio ajenos a la figura original. Los días sin volumen positivo no reciben barras naranjas.

El horario azul procede del `module_timeline` actual. No se restauraron las proyecciones antiguas por tasa de referencia o densidad. Las ventanas naranjas no acreditan horas efectivas; el horario azul sigue siendo una estimación. Los intervalos y huecos de las fuentes se conservan.

Cambio instalado: únicamente `fig_gantt` y su texto explicativo en `reconstitucion/panel.py`, más las expectativas visuales de las pruebas. Se mantienen callbacks, identidad Caso/run, selección, popups y exportación de informe. No se cambió el motor, la metodología, las consultas ni la base.

Verificación sin SQL: figuras de casos 10009/run10082 (7 barras por serie) y 10013/run10145 (16 por serie). Pasaron 15 pruebas en el repositorio destino. Navegador aislado con el panel activo y snapshot 10013: dos trazas bar, diez carriles, colores correctos, popups y bloqueo de descarga al cambiar Caso; sin errores JS/HTTP ni desbordamiento del documento móvil. No se reinició el servicio del usuario.

Evidencias y respaldo: `../curvas_recon/auditorias/replica_grafico_original_20261027/`. Si el proceso local no tiene recarga automática, reiniciar `main.py` para incorporar el gráfico.
