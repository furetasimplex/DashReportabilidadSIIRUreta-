# Ajuste de textos de Reclamo

Cambio de aplicación: únicamente reclamo/panel.py.

Diccionario ESTADO_CLIENTE y helper traducir_estado_cliente con fallback seguro. Traducción de estados/orígenes en tablas, notas y tooltips; mensajes operacionales bajo Avance; texto de falta de corriente en gráfico de horas; leyendas de Avance centralizadas.

Validación SELECT-only DEV para 01–07 de octubre de 2026: estados PAD1/PAD2 coinciden con lo solicitado. Gráficos, tablas y vista previa serializados sin los códigos prohibidos. DataFrames de origen intactos. AST confirma llamados db, clasificación de motivos, filtros y callbacks de escritura sin cambios. Ver validation.json.

Validación visual en navegador pendiente: cua informó que iab y chrome no están disponibles. La vista local reproducible se inicia con venv\Scripts\python.exe scripts\diagnosticos\reclamo_textos_cliente_20261007\validate_readonly.py --serve y se abre en http://127.0.0.1:8107/. La tabla inicial es un resumen de validación; los gráficos y mensajes usan los callbacks reales.

No se modificó SQL, base de datos, metodología, cálculo de horas, cálculo CV25, prioridad de fuentes, flags persistidos ni PROD. No se hizo commit ni push.
