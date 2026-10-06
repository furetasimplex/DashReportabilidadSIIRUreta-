# Campaña operacional frente a campaña_id

Fuente canónica: `inventar_SpcHidr.disponible_rotopalas.[campaña_id]` ↔ `[campaña]`. La consulta SELECT en `mapping.json` devuelve seis pares, cero `campaña_id` ambiguos y cobertura completa de cuadratura, cálculo diario y logs de automatización.

| campaña_id interno | Campaña operacional |
|---:|---:|
| 4 | 17 |
| 3 | 16 |
| 2 | 15 |
| 10 | 11 |
| 8 | 10 |
| 7 | 9 |

No se codificaron estos pares en Python. Las lecturas de `reclamo/db.py` obtienen `campana` desde la tabla canónica mediante `OUTER APPLY`; el identificador permanece en cada DataFrame donde lo requieren callbacks y joins.

| Componente | Valor backend | Label anterior | Label actual | Fuente de número operacional |
|---|---|---|---|---|
| Remanente | `campana_id` | Campaña 4 | Campaña 17 | `db.cuadratura` + disponible_rotopalas |
| Cuadratura, gráfico/tabla/selector/detalle | `campana_id:modulo_id` | M33 / campaña 4 | C17 · M33 / Campaña 17 | `db.cuadratura` + disponible_rotopalas |
| Historial y resultado automatización | `campana_id`, `log_id` | Campaña ID | Campaña 17 | JOIN read-only para alertas; consulta de catálogo para respuesta del SP |
| Datos base y editor | `campana_id`, `id_disponible_rotopalas` | Campaña 17 (id 4), ID 100 | Campaña 17, Módulo 1 | `disponible_rotopalas` ya trae ambos |
| Agregar módulo | `campana_id` | Campaña 17 (id 4) | Campaña 17 | `campanas_disponible_rotopalas` |
| Ajustes documentados | `campana_id|pad_id|modulo_id` | M33 · campaña 4 | Módulo 33 · Campaña 17 · PAD Óxidos | `db.modulos_disponibles` + disponible_rotopalas |
| Ajustes registrados | `ajuste_id`, `modulo_id` | IDs técnicos | Campaña y Módulo operacionales | `db.ajustes` + disponible_rotopalas |
| Vista mensual | `campana_id+modulo_id` | Pivot solo por M33 | Campaña 17 / M33 | `db.avance_diario` + disponible_rotopalas |
| Vista previa | `campana_id`, `modulo_numero` | Módulo solo | Campaña 17 + módulo | `db.avance_diario` + disponible_rotopalas |

Los valores `value` de dropdown siguen siendo las claves originales. Una campaña sin correspondencia canónica se presenta como «Sin información», nunca como su ID interno.
