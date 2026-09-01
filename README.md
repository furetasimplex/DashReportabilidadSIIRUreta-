# AppModeloRipios

## Operación PROD: sincronización de vistas y SP

El procedimiento recurrente para revisar, corregir y validar referencias SQL
entre `inventar_SpcHidr_PROD` y `PROD_SIIR` está documentado en
[docs/runbooks/sincronizacion_vistas_sps_prod.md](docs/runbooks/sincronizacion_vistas_sps_prod.md).

Comando habitual de revisión, sin modificaciones:

```powershell
python scripts\run_prod_reference_patch.py
```
