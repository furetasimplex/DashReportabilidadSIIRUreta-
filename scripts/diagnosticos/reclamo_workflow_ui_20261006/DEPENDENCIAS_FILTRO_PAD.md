# Dependencias de `filtro-pad`

Antes: `filtro-pad` aparecía una vez en la barra superior y una vez como `State` de `cb_opciones_modulo` para filtrar `aj-modulo` y `aj-destino`. No intervenía en los demás análisis. La auditoría previa está en `../reclamo_runbook_20261006/DEPENDENCIAS_FILTRO_PAD.md`.

Después: se eliminaron el componente, el `State`, el argumento `pad` y el filtrado del DataFrame. Ambos desplegables reciben todos los módulos. Cada etiqueta incluye Módulo, Campaña y PAD; el valor conserva `campana_id|pad_id|modulo_id`.

Se preservaron `dr-filtro-pad` (filtro **local** de Datos base), `dr-ins-pad` (entrada de inserción) y las pestañas PAD locales. `validate.py` comprueba ausencia del ID global y de referencias huérfanas en `callback_map`, valores de ambos PAD y unicidad de IDs.
