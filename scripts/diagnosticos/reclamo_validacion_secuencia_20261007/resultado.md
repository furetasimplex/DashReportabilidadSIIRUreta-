# Resultado DEV

**VALIDACION_SECUENCIA_APLICABLE_PASS.**

El cálculo anterior del control 2 era `mc.estado = 'CONGELADO' AND NOT EXISTS
secuencia_rotopala`, sin filtro de elegibilidad. El panel presenta el resultado
de `db.semaforo`; no calcula este número por separado.

La definición vigente de los SP de secuencia usa dos caminos: movimiento
positivo de rotopala en `inventar_SpcHidr.control_reclamo_diario`, o módulo en
el rango `(frente_topografico, frente_topografico + @Siguientes]` de la misma
campaña y PAD, con `@Siguientes = 5` por defecto. El control 2 ahora refleja
esos mismos caminos y mantiene severidad `BLOQUEANTE`.

| Caso | Antes | Después | Motivo |
|---|---:|---:|---|
| PAD2/campaña_id 10, M22–M26 (ids 86–90) | 5 | 0 | Frente topográfico M16, cola elegible M17–M21, sin evidencia de rotopala propia |

El semáforo DEV devuelve `hallazgos=0` y `resultado=OK` para el control 2.
Se comprobó con casos de lectura que una fila sin secuencia con evidencia
real, o ubicada en M17–M21 con frente M16, sigue clasificada elegible y por
tanto bloqueante. No existía en DEV un módulo elegible sin secuencia para una
prueba positiva del semáforo con datos reales.

Comparación de invariantes antes/después: 85 filas en `secuencia_rotopala`,
85 módulos `CONGELADO`, 1100 filas en `calculo_diario`, TMS rotopala
`4002639.443107000000` y TMS camiones `1135757.803561000000`; todos
idénticos. No se insertaron filas ni se modificaron datos o SP.

**Alcance:** el semáforo es el control visual de publicación. El método
`db.publicar` existente no consulta `db.semaforo` antes de llamar al SP de
publicación; este cambio no altera ese flujo backend.

No hubo publicación, PROD, commit ni push.
