# Dependencias del PAD global

`filtro-pad` se crea en la barra superior de `reclamo/panel.py:151`. En el código actual solo aparece como `State("filtro-pad", "value")` de `cb_opciones_modulo` (`:1830-1850`), que arma las opciones `aj-modulo` y `aj-destino` para Ajustes. No filtra Resumen, Matriz, Cuadratura, Avance, Vista previa, Rendimiento ni Datos base. Es engañoso como supuesto filtro global.

El propio `cb_opciones_modulo` incluye **PAD, campaña y módulo en cada etiqueta** y codifica los tres IDs en el valor. Si se elimina el PAD global, puede devolver todas las opciones de `db.modulos_disponibles()` conservando esas etiquetas: no se pierde la distinción de PAD. Para listas extensas, alternativa de UX: añadir `aj-filtro-pad` dentro de Ajustes y convertirlo en `Input` junto a `btn-actualizar`; entonces cambiar PAD actualizaría inmediatamente las opciones. La solución mínima es la primera, sin selector adicional.

`dr-filtro-pad` es un selector **local de Datos base**, pasado a `db.disponible_rotopalas` en `cb_tabla_disponible_rotopalas` (`:1982-1995`). `dr-ins-pad` es el PAD de inserción, no un filtro global (`:1964-1967,2154-2168`). Los análisis usan pestañas PAD locales (`matriz-pad-tabs`, `remanente-pad-tabs`, `preview-pad-tabs`, `cuadratura-pad-tabs`, `avance-pad-tabs`). Ninguna depende de `filtro-pad`.

Propuesta de cambio posterior, **no implementado**: quitar el bloque visual de `filtro-pad`; quitar ese `State` y el filtro `if pad` en `cb_opciones_modulo`; preservar la etiqueta y el valor con PAD para selección inequívoca; revisar que todos los módulos sigan disponibles. No eliminar `dr-filtro-pad` ni `dr-ins-pad`.
