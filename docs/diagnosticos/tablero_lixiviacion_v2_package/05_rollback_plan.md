# Plan de retirada de V2 — no ejecutado

V2 será un objeto nuevo. El rollback inicial consiste en **retirar o revertir los consumidores de V2**, no restaurar ni alterar `vw_tablero_lixiviacion_final`.

1. Antes de desplegar: inventariar consumidores, propietario, versión, endpoint, dataset/exportador y procedimiento para revertir cada conexión. Guardar DDL, permisos, contrato y evidencias de validación fuera de SQL Server mediante un mecanismo autorizado.
2. Si falla V2: detener su adopción y actualización de reportes afectados. Identificar la causa (grano, ventana, fecha, unidad, precisión) sin modificar automáticamente ninguna fuente compartida.
3. Revertir cada consumidor a su versión anterior aprobada, incluida su interpretación de unidades. **No basta cambiar FROM:** un cliente V2 espera kg/d reales; el alias legacy del mismo nombre contiene t/d. Revertir consulta, etiquetas, conversiones y modelo de agregación como un conjunto.
4. Volver a validar el consumidor. El legacy conserva el problema conocido de multiplicidad; retornar a él no equivale a corregirlo ni autoriza usar sus sumas como referencia física.
5. Mantener V2 sin consumidores mientras se investiga. Retirada de permisos o eliminación del objeto, si luego se decide, requiere inventario actualizado y autorización separada. Este paquete no incluye DROP.
6. Conservar objetos TEST, backups, snapshots, logs y evidencia. No borrarlos. No ejecutar refresh/reproceso de tablas o reportes materializados como parte implícita de la retirada.

La creación de V2 no modifica datos. Si consumidores futuros materializan resultados, su reversión necesita un plan independiente; retirar la vista o reconectar el reporte no revierte esos datos. Si la promoción incluyera cambios a fuentes compartidas, sería otro despliegue con su propio rollback: este paquete no los implementa.
