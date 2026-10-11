# Runbook: sincronización de vistas y SP en PROD

Este procedimiento valida y corrige referencias cross-database de vistas y
procedimientos almacenados desplegados en `inventar_SpcHidr_PROD`.

## Bases canónicas

| Rol | Base |
|---|---|
| Aplicación e inventario | `inventar_SpcHidr_PROD` |
| Django, hidro y reconciliador | `PROD_SIIR` |
| Login | `PROD_SIIR.dbo.auth_user` |

No usar `SIIR_PROD`, `PR_SIIR`, `DEV_SIIR` ni `inventar_SpcHidr` como destinos
de módulos productivos. Un nombre de dos partes como
`inventar_SpcHidr.tabla` sí es válido: representa `schema.tabla` dentro de la
base actual.

## Configuración requerida

```env
ENVIRONMENT=production
SQLSERVER_DB=inventar_SpcHidr_PROD
LOGIN_DATABASE=PROD_SIIR.dbo.auth_user
BALANCE_RECON_DATABASE=PROD_SIIR
```

## Procedimiento habitual

### 1. Preflight de solo lectura

Ejecutar desde la raíz del repositorio:

```powershell
python scripts\run_prod_reference_patch.py
```

Este comando:

- carga el SQL versionado, nunca el contenido de una pestaña de SSMS;
- verifica que la conexión efectiva sea `inventar_SpcHidr_PROD`;
- comprueba que exista `PROD_SIIR`;
- muestra los módulos pendientes en orden de despliegue;
- no modifica objetos ni datos.

Resultado esperado si no hay drift:

```text
[PATCH-PROD] Modo: PREFLIGHT (SOLO LECTURA)
[PATCH-PROD] OK: preflight aprobado; no se modifico la base
```

El parche es idempotente: puede ejecutarse repetidamente si PROD ya está
sincronizado.

### 2. Aplicación

Solo si el preflight termina correctamente y muestra cambios pendientes:

```powershell
python scripts\run_prod_reference_patch.py --apply --confirm inventar_SpcHidr_PROD
```

La confirmación exacta evita aplicar por accidente en otro ambiente. Los
`ALTER VIEW` se ejecutan antes que los `ALTER PROCEDURE` consumidores. Todo se
ejecuta dentro de una transacción con `XACT_ABORT`; cualquier error causa
rollback integral.

Resultado esperado:

```text
[PATCH-PROD] OK: parche aplicado; ejecute el smoke test
```

### 3. Smoke test obligatorio

```powershell
python scripts\smoke_test_production_db.py
```

Resultado requerido:

```text
[SMOKE-PROD] RESULTADO: OK
  Base efectiva: inventar_SpcHidr_PROD
  Auth y dependencias cross-DB: PROD_SIIR
  Objetos y referencias SQL: OK
```

Para diagnóstico detallado:

```powershell
python scripts\smoke_test_production_db.py --verbose
```

### 4. Arranque

Solo después de aprobar el smoke:

```powershell
python main.py
```

Con `ENVIRONMENT=production`, el startup check es obligatorio y estricto. No
puede deshabilitarse con `DB_STARTUP_CHECK=0`.

## Códigos de salida

| Comando | Código | Significado |
|---|---:|---|
| `run_prod_reference_patch.py` | 0 | Preflight o aplicación correctos |
| `run_prod_reference_patch.py` | 1 | Conexión, preflight, compilación o transacción fallida |
| `run_prod_reference_patch.py` | 2 | Argumentos/confirmación inválidos |
| `smoke_test_production_db.py` | 0 | PROD completamente válida |
| `smoke_test_production_db.py` | 1 | Configuración, objetos o referencias incorrectas |
| `smoke_test_production_db.py` | 2 | `ENVIRONMENT` no es `production` |

## Promoción de drift real DEV → PROD

El parche anterior corrige una lista fija de referencias cross-DB. Para promover
cambios de lógica hechos en DEV (vistas, funciones y SP) se usa:

```powershell
python scripts\sync_modules_dev_to_prod.py                                  # preflight
python scripts\sync_modules_dev_to_prod.py --only reclamo.                  # filtra
python scripts\sync_modules_dev_to_prod.py --apply --confirm inventar_SpcHidr_PROD
```

Antes de comparar, cada definición de DEV se reescribe a los nombres canónicos
de producción (`DEV_SIIR`→`PROD_SIIR`, `test_DEV_SIIR`→`test_PROD_SIIR`, y los
tres-partes `inventar_SpcHidr.inventar_SpcHidr.x` a dos partes). Por eso los 12
módulos cross-DB conocidos **no** aparecen como drift: solo se lista divergencia
real. Un módulo que conserve un token sin mapeo canónico (`PR_SIIR`,
`SIIR_PROD`) se marca `[BLOQUEADO]` y no se promueve.

Al aplicar: respaldo de las definiciones actuales en `backups/`, un solo
`ALTER` transaccional con `XACT_ABORT`, validación con
`sp_refreshview`/`sp_refreshsqlmodule` antes del commit, y luego el smoke test.
Si el smoke falla, el script imprime el `--restore` exacto.

```powershell
python scripts\sync_modules_dev_to_prod.py --restore backups\prod_modules_antes_<sello>.sql
python scripts\sync_modules_dev_to_prod.py --self-test   # valida las reescrituras, sin BD
```

Objetos que existen solo en DEV se listan como `[SOLO DEV]` y no se crean: el
script solo hace `ALTER`. Crear objetos nuevos sigue siendo manual.

### Interfaz web

```powershell
python scripts\sync_web.py     # http://127.0.0.1:8070
```

Misma lógica, con pantalla: formulario de conexión DEV (PROD sale del `.env` y
se muestra solo para confirmar), checklist de módulos con diff por módulo, y los
botones **Dry-run**, **Transferir a PROD** (exige escribir
`inventar_SpcHidr_PROD`) y **Solo smoke test**. La salida del motor se muestra
tal cual. Los respaldos de `backups/` aparecen en un desplegable para restaurar.

Escucha solo en `127.0.0.1`: puede sobrescribir producción, no debe exponerse.

## Cómo incorporar nuevos módulos

El ejecutor actual corrige una lista controlada en
`docs/migrations/fix_prod_cross_db_references.sql`. Si el smoke detecta una
nueva vista o SP:

1. inspeccionar su definición en `sys.sql_modules`;
2. agregarlo a `@Objetivos` con un `deployment_order` explícito;
3. ubicar primero vistas fuente, luego vistas consumidoras y al final SP;
4. validar todos los `ALTER` en una transacción con rollback;
5. actualizar `PATCH_VERSION` tanto en el SQL como en el ejecutor;
6. ejecutar preflight, aplicación y smoke en ese orden.

No realizar un reemplazo masivo fuera de la lista controlada ni copiar SQL
desde una pestaña temporal de SSMS.

## Incidente conocido: `dbo.test_imp`

`dbo.v_imp_conciliacion_chancado` fue renombrada históricamente y conservaba
`CREATE VIEW dbo.test_imp` dentro de `sys.sql_modules`. El parche normaliza ese
encabezado antes del `ALTER`. Si reaparece `Invalid object name 'dbo.test_imp'`,
verificar que el ejecutor muestre la versión requerida del parche y no ejecutar
una copia antigua desde SSMS.
