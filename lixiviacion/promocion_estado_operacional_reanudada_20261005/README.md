# Promoción de estado operacional — DEV, 05-10-2026

## Canónico y evidencia histórica

El usuario confirmó mediante las fuentes operacionales DEV que el 10-09-2026 existen riego y drenaje simultáneos en OX P1–P16/P30–P32 (19) y SULF P7–P8/P10–P25 (18). El canónico vigente es `RIEGO_DRENAJE`, no `RIEGO`. Se actualizó la expectativa documental y de smoke, sin cambiar CASE, ventanas ni reglas SQL.

La carpeta hermana `promocion_estado_operacional_20261005` conserva intacta la evidencia del intento anterior, detenido por un criterio documental desactualizado. El informe `DETALLE_MODULOS.md` también describe aquella ejecución histórica. Los JSON de smoke previos se respaldaron aquí antes de reejecutarlos; no constituyen validación de la promoción actual.

## Precheck y respaldo

Ambos oficiales estaban ausentes en DEV. Ambos TEST eran funciones inline (`IF`), con ANSI_NULLS y QUOTED_IDENTIFIER activos. `precheck.json` contiene columnas/tipos/nullability, dependencias SQL y referencias textuales visibles. No se encontraron dependencias enlazadas de oficiales inexistentes; esto no descarta consumidores externos.

Definiciones TEST exactas: `parcela_test_original.sql` y `modulo_test_original.sql`. Ausencia previa documentada en los archivos `*_official_original.sql`. Los candidatos sustituyen exclusivamente la cabecera por `CREATE FUNCTION` y el nombre oficial; parámetros, cuerpo y comentarios se conservan literalmente. No se normalizan cadenas SQL ni reglas.

## Validación transaccional

`python -m lixiviacion.promote_estado_dev deploy` crea ambos objetos dentro de la misma transacción. Antes del COMMIT verifica hashes SHA256 del sufijo literal posterior al nombre, contratos completos, las 24 columnas de parcela, 253 fechas × 60 parcelas, igualdad de todas las columnas con multiplicidad y casos canónicos. Compara módulos TEST/oficial para las 60 parcelas y sus conteos contra `modulos_total`.

Las reversas auditadas son DRENAJE_RESIDUAL → RIEGO/RIEGO_DRENAJE y REPOSO_PRE_RECLAMO → RIEGO/RIEGO_DRENAJE/DRENAJE_RESIDUAL, ordenadas por fecha dentro de PAD/parcela/campaña. También se rechazan SIN_CLASIFICAR y SIN_COBERTURA_HIDRAULICA en el período.

**COMMIT DEV realizado.** `deployment.json` acredita ambos CREATE confirmados; `post_commit.json` verifica persistencia y hashes desde una conexión nueva. Las funciones TEST permanecen instaladas.

| Verificación | Resultado |
|---|---|
| Histórico 01-01 a 10-09-2026 | 15.180 filas; 60 claves únicas cada fecha |
| Comparación completa TEST/oficial | SOLO_TEST=0, SOLO_OFICIAL=0, DIFERENCIAS=0 |
| Reversas terminales | 0 |
| SIN_CLASIFICAR / SIN_COBERTURA_HIDRAULICA | 0 / 0 |
| Canónico PAD1 | MIXTO=1, REPOSO_PRE_RECLAMO=12, RIEGO_DRENAJE=19 |
| Canónico PAD2 | APILADO=1, CONFORMADO_PRE_RIEGO=2, MIXTO=2, REPOSO_PRE_RECLAMO=5, RIEGO_DRENAJE=18 |
| Seis casos parcela requeridos | Exactos |
| Módulos TEST/oficial, todas las columnas | 60 parcelas sin diferencias |
| Conteo módulos vs modulos_total | 0 discrepancias |
| OX P29 / OX P17 / SULF P1 | Nombres y estados exactos |

SHA256 TEST = oficial en ambos casos (se ignora únicamente la cabecera hasta el nombre; el resto se conserva literal, incluso comentarios y espacios):

- Parcela: `eb4387b19c70568bc71f61885444020c8288283e8376a7e8cc55735ee4e40017`.
- Módulo: `66e3fc468d9a13d71cb2859451fde8e8a8937b06ba1bc1f874db3178d60afec2`.

Detalle completo en `validation_before_commit.json`. Estos hashes usan un método más estricto de preservación literal que el hash del precheck histórico; no deben compararse directamente con aquel hash normalizado con otro método.

## Dash y regresión

`map_db.diff` contiene exclusivamente las dos sustituciones de fuentes TEST por oficiales. Columnas, parámetros, ORDER BY, helpers y callbacks permanecen intactos. `map_db_before.py.txt` conserva la versión previa.

- `python -m pytest lixiviacion -q`: **43 PASS** (41 existentes y 2 nuevos de promoción).
- `python -m lixiviacion.smoke_map_dev`: **PASS**, 60 filas, seis casos y canónico actualizado; también contrato de 11/09.
- `python -m lixiviacion.smoke_modules_dev`: **PASS**, OX P29/P17 y SULF P1.
- `python -m lixiviacion.visual_review`: **PASS**, 13 comprobaciones, sin errores de página ni callbacks, sin overflow del documento. Navegación, mapa, drawer y módulos conservados. Captura SULF P1 inspeccionada: M1–M4 Reclamado, M5 Reclamo. Evidencias nuevas en `../visual_promocion/`, sin sobrescribir capturas anteriores. Servidor temporal detenido al terminar.
- `git diff --check`: **PASS**, solo advertencia LF/CRLF de `layout.py`, preexistente y ajena a esta promoción.

Archivos modificados en esta pasada: `map_db.py`, expectativas de fuente en `test_map.py`/`test_modules.py`, canónico en `smoke_map_dev.py`/`precheck_promocion_estado.py`, docstring de `smoke_modules_dev.py`, destino de evidencias en `visual_review.py`, `README.md`, `ESTADO_OPERACIONAL.md` y resultados JSON de los dos smokes. Nuevos: `promote_estado_dev.py`, `test_promocion.py`, esta carpeta de respaldo/validación/rollback y `visual_promocion/`.

## Rollback

Ver [ROLLBACK.md](ROLLBACK.md). Restituir consumidores TEST antes de retirar oficiales nuevos; revisar dependencias. No borrar funciones TEST ni backups. No se ejecuta el rollback preparado.

## Alcance

Solo DEV. Sin DML ni escrituras de datos, sin PROD, sin cambios en CPC, V2, Model6, Diagnóstico, Recomendador, callbacks, Store, drawer, fases, colores o geometría. Sin commit/push Git.
