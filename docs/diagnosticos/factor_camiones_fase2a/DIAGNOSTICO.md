# Fase 2A — inspección previa, implementación detenida

Fecha: 28-09-2026. No se ejecutó DDL, DML ni procedimiento de cálculo o publicación.

## Ambiente y evidencia

Validación mediante `_engine_dev()` y `_assert_dev_connection()`: base efectiva `inventar_SpcHidr`, servidor efectivo `VPS-5347319-X`, coincidente con el host DEV configurado. No se consultó PROD.

En `20260928_091540/` se guardaron definiciones actuales de los cuatro procedimientos/vista inspeccionados, columnas y dependencias en `inspeccion.json`, y snapshots completos de las dos tablas de control. Son respaldos de inspección, no scripts de despliegue.

## Diferencia importante respecto de la solicitud

Hay dos cadenas distintas, no solo nombres equivalentes:

| Elemento | Cadena citada en la solicitud | Cadena consumida por el panel |
|---|---|---|
| Mantenedor | sp_mantiene_factor_ajuste_camiones_test | sp_mantiene_factor_ajuste_camiones_v2_test |
| Cálculo | Dentro del mantenedor | sp_factor_ajuste_camiones_test |
| Persistencia | Control_Factor_Ajuste_Camiones | Control_Factor_Ajuste_Camiones_v2_test |
| Límite KOM | Limite_Factor_Carga_KOM | Limite_KOM_TMH_Viaje |
| Límite CAT | Limite_Factor_Carga_CAT | Limite_CAT_TMH_Viaje |
| Histórico observado | 62 filas, 01-08-2025 a 31-01-2026 | 84 filas, 01-07-2026 a 22-09-2026 |

Todos los objetos están bajo el esquema `inventar_SpcHidr`.

La vista `v_ajuste_camiones_emision_test` lee exclusivamente `Control_Factor_Ajuste_Camiones_v2_test`. El mantenedor V2 llama a `sp_factor_ajuste_camiones_test`. Este último limita las cargas con 380/265 en las correcciones y clasifica estados usando esos mismos límites. El mantenedor V2 persiste actualmente 380/265 como constantes separadas.

Las constantes explícitas 357/236 y los campos `Constante_KOM_TMH_Viaje`, `Constante_CAT_TMH_Viaje`, `KOM_TMH_Mina`, `CAT_TMH_Mina`, `Dato_Mina_TMH` pertenecen a la cadena anterior. La cadena actual obtiene producción y viajes desde `mov_cam_powerbi`; no corresponde introducir esas constantes ni reconstruir allí el dato mina.

## Dependencias e impacto

- La tabla anterior tiene como consumidor `sp_mantiene_datos_conciliados_of_v2_ajustado_test`.
- El mantenedor V2 es llamado por `sp_mantiene_datos_conciliados_emision_test`.
- La vista actual es consumida por `sp_reporte_turno_emision_test`, `sp_mantiene_datos_conciliados_emision_test`, `fn_reconstitucion_srr_emision_test` y `fn_reconstitucion_srr_turno_emision_test`.
- El cálculo actual depende de `Historico_Apilado_Diario`, `mov_cam_powerbi`, `v_humedad_inventario_test`, `v_inventario_chancado_test` y `v_srr_tms_origen_turno_emision_test`.

Modificar solo el mantenedor anterior no parametrizaría el panel actual y afectaría otra cadena. Modificar solo las constantes persistidas por V2 produciría trazabilidad inconsistente si el cálculo continuara limitado por 380/265.

## Cambio mínimo recomendado para el alcance corregido

1. Aplicar la parametrización a la cadena actual V2, conservando intacta la cadena anterior.
2. Crear vigencias, auditoría y registro controlado según los requisitos originales.
3. Resolver límites por fecha en `sp_factor_ajuste_camiones_test`, tanto en correcciones como en condiciones de estados, sin cambiar fórmulas.
4. Hacer que `sp_mantiene_factor_ajuste_camiones_v2_test` persista exactamente los límites usados por ese cálculo bajo una lectura consistente. Revisar su captura `INSERT EXEC` antes de ampliar contratos de salida.
5. Exponer `Limite_KOM_TMH_Viaje` y `Limite_CAT_TMH_Viaje` persistidos en la vista de emisión.
6. Para esta cadena, usar como candidato de seed el **01-07-2026**, MIN(Fecha) real de la tabla V2, no el mínimo de la tabla anterior. No se sembró ningún registro.
7. Adaptar la validación 357/236: demostrar que la cadena anterior queda intacta y que producción/viajes de la cadena V2 no cambian. No exigir columnas inexistentes en V2 ni introducirlas artificialmente.

## Estado de entrega

Implementación detenida por la regla explícita del usuario ante diferencias importantes de arquitectura. No se crearon tablas SQL, procedimientos, migraciones ni rollback de despliegue. No hay parámetros provisionales persistidos ni reprocesos. El script local `scripts/inspect_factor_camiones_fase2a.py` contiene únicamente consultas SELECT y escritura de evidencia local.

Las pruebas de vigencias, concurrencia, recálculo y equivalencia antes/después quedan pendientes de la implementación con alcance corregido.
