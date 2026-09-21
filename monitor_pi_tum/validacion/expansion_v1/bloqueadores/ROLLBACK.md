# Rollback integral expansión V1

Ocho objetos de expansión V1: cinco creados y tres modificados. No desinstala fases anteriores del módulo PI/TUM.

No ejecutado. Orden: retirar consumidores Reclamo antes de su fuente; restaurar Balance y peso teórico antes de la vista de tonelajes que consume este último.

|Orden|Objeto|Estado previo|Definición previa / acción|
|---|---|---|---|
|1|reclamo.v_diferencia_cv25_contingencia_test|Ausente|No había definición; DROP VIEW|
|2|reclamo.v_reclamo_diario_contingencia_test|Ausente|No había definición; DROP VIEW|
|3|reclamo.v_preliminar_cv25_con_acumulado_contingencia_test|Ausente|No había definición; DROP VIEW|
|4|reclamo.v_preliminar_cv25_contingencia_test|Ausente|No había definición; DROP VIEW|
|5|reclamo.v_cv25_diario_contingencia_test|Ausente|No había definición; DROP VIEW|
|6|inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test|Existente|backup\inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test.sql|
|7|inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test|Existente|backup\inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test.sql|
|8|inventar_SpcHidr.v_bd_ton_t12_contingencia_test|Existente|backup\inventar_SpcHidr.v_bd_ton_t12_contingencia_test.sql|

[Script integral](rollback_integral_v1.sql) · [Manifiesto con hashes](manifiesto_rollback_v1.json)

Las definiciones previas a esta corrección de tipos se conservan además en los archivos *.antes.sql. El rollback integral vuelve al estado anterior a expansión V1, no al estado con el defecto float.

La vista v_representatividad_diaria_calculada_contingencia_test tiene un respaldo pero no fue modificada por los DDL de expansión V1; se conserva. Las tablas de acciones, los SP de gestión y el resolvedor operacional son preexistentes a esta expansión y permanecen. No existe evidencia suficiente para reconstruir un rollback de todas las fases anteriores; este manifiesto no lo pretende.

Se bloquean dependencias SQL nuevas externas a las cinco vistas retiradas. Los consumidores externos a SQL (aplicación/reportes) deben volver a apuntar a sus fuentes previas antes de ejecutar. No se ejecutó el script ni se probó su DDL con cambios reales por la restricción expresa del usuario.
