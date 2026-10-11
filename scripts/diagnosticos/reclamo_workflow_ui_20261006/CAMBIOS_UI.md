# Cambios de interfaz

| Zona | Antes | Después |
|---|---|---|
| Barra superior | Período, PAD global, Refrescar, Reprocesar | Período, Refrescar secundario, Reprocesar principal. Texto sobre rango histórico y guía de cinco pasos. |
| Módulos | Botón verde de secuencia al comienzo de la pestaña | `Herramientas avanzadas` colapsado; mismo `btn-automatizacion` y mismo callback. Texto aclara que no sincroniza rango ni recalcula. |
| Datos base | Guardar/Insertar sin siguiente paso claro | Aviso sobre Reprocesar en tarjeta y mensajes de éxito. Ningún guardado encadena un SP adicional. |
| Ajustes | Propuesta explicada | Añadida instrucción de reprocesar tras aprobación; la pantalla sigue sin aprobar/rechazar. |
| Publicación | Aviso genérico | Indica que Publicar no recalcula Reclamo, guía de tres comprobaciones y botón funcional con `disabled=False`. |
| Validaciones | Historial de 30 días aparecía como `NO PUBLICAR` | Historial en `INFORMACIÓN / TRAZABILIDAD`; los demás bloqueos y advertencias conservan su resultado SQL. Cada tarjeta muestra alcance y unidad. |

Las cuatro pestañas y los IDs funcionales existentes permanecen. No se modificaron llamadas a SP ni reglas de Reclamo.

Capturas: `before/barra_y_validaciones_1366x768.png` y `after/barra_y_validaciones_1366x768.png`; `after/modulos_1366x768.png`; `after/datos_base_1366x768.png`; `after/publicacion_1366x768.png`.
