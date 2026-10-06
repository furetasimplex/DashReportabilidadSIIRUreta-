# IDs y códigos visibles

Antes: `Campaña ID` en automatización; `campana_id` bajo el título Campaña en remanente; `ID 100` en editor; `ajuste_id` y `modulo_id` en ajustes; `ID` y `Campaña ID` en columnas ocultables de datos base. La opción de columnas mostraba el control nativo inglés «Toggle Columns» y el filtro nativo «filter data...». El historial de módulo y la tabla de avance exponían códigos de fuente y cálculo.

Después: `_tabla` elimina columnas técnicas de la tabla cliente, conserva los DataFrames originales, y usa formato local para columnas numéricas. La tabla principal de datos base contiene ocho columnas operativas; los valores técnicos siguen en `store-disponible-rotopalas` y en los callbacks. Se desactivó el filtro nativo inglés y se retiró el selector de columnas ocultas. El editor y los selectores usan nombres de módulo, campaña operacional y PAD. Estados, fuentes y códigos de cálculo se traducen solo al presentar. Los mensajes tras guardar datos base ya no exponen IDs o nombres de tabla.

La fuente de `Detalle` del log proviene del SP y no se reescribe automáticamente. El historial se identifica como eventos anteriores; se conserva el estado NO PUBLICAR que devuelve el semáforo, aunque su uso para un contador histórico merece revisión funcional separada.
