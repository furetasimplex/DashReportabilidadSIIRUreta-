# Curvas de Recuperaci?n ? campa?as activas del Caso

Aplicado el 21 de octubre de 2026 en DashReportabilidadSIIR/curvas_recon/pad_dashboard.py.

Se sustituy? la inclusi?n de todos los tramos medidos por selecci?n seg?n actividad en la ventana inclusiva del Caso. Se reutilizan fechas de riego positivo y Cu de drenaje del cache operativo existente. Se agrupan con la tolerancia vigente UNLISTED_GAP_DAYS (30 d?as), y por cada d?a activo del Caso se escoge el ciclo medido m?s reciente de ese grupo. As? se excluyen ciclos antiguos reemplazados e inicios posteriores. Si el Caso incluye un reinicio, pueden aparecer ambos ciclos. Se conserva completa cada traza seleccionada; no se recorta su historia anterior al Caso.

Una ?ltima lectura medida atrasada no cierra por s? sola la campa?a: se conserva si la operaci?n contin?a en el mismo grupo. Se oculta la reconstrucci?n hist?rica cuando no hay actividad ni arranque WIP en la ventana, salvo que exista raw validado del Caso. No cambian c?lculo, rampas, solver ni persistencia. El cache de figuras sigue separado por Caso, run y ventana.

Validaci?n focal: 8 pruebas. Suite integrada: 141 aprobadas, dos advertencias preexistentes por Dash DataTable. Verificaci?n de figuras automatizada; no se repiti? un c?lculo desde el navegador en esta tarea. Sin commit ni push.
