# Fix

No se aplicó código ni runtime: la causa del clic verde no quedó inequívocamente determinada y no se obtuvo acceso a la instancia DEV en ejecución. Fix mínimo pendiente de evidencia: comparar `callback_map`, `__file__`/hash del worker y `db.recalcular`/`db.mantener_secuencia` en el host del dashboard; corregir o reiniciar únicamente si esa comparación confirma runtime viejo o import incorrecto.

Diff de aplicación: ninguno.
