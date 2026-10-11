# Auditoría integral de Reclamo

Fecha de extracción original: 2026-09-02. Base observada entonces: `inventar_SpcHidr` en `VPS-5347319-X`. La auditoría fue estrictamente read-only; no se ejecutó ningún procedimiento ni callback.

Las definiciones de vistas `reclamo.*` se refrescaron el 2026-10-07 desde PROD `inventar_SpcHidr_PROD` @ `VPS-6191873-X`. Catálogo y cadena actual: `analisis/vistas.md`.

## A. Arquitectura general

```text
FUENTES inventar_SpcHidr
  control_reclamo_diario ─────────────────────────┐
  control_medicion_topografia_diaria ─────────────┤
  control_reclamo_sulfuro_camiones_thm_diario ───┤
  disponible_rotopalas / modulo / modulos_turnos ┤
  vista_resumen_datos_filtrados / datos_filtrados┤
                                                  ▼
SINCRONIZACIÓN Y CONTROL reclamo
  sp_auto_mantener_secuencia
    ├─ sp_auto_congelar_modulos_nuevos
    │   ├─ sp_congelar_modulo
    │   ├─ sp_definir_secuencia
    │   └─ sp_establecer_linea_base
    └─ sp_auto_cerrar_y_avanzar_secuencia
  sp_sincronizar_desde_etl
  sp_cargar_cv25_horas
                                                  ▼
CAPA PERSISTENTE
  modulo_congelado / secuencia_rotopala
  topografia_avance / camiones_reclamo
  cv25_diario / rotopala_horas_turno / ajuste_manual
                                                  ▼
CÁLCULO
  v_modulo_base
  v_topografia_resuelta
  v_camiones_acumulado
  v_cv25_diario → v_preliminar_cv25 → v_preliminar_cv25_con_acumulado
  v_ajustes_aplicables
  v_reclamo_diario
  sp_calcular_reclamo_diario → calculo_diario
                                                  ▼
DASHBOARD
  reclamo/panel.py ← reclamo/db.py
                                                  ▼
PUBLICACIÓN
  v_reclamo_para_conciliados
  → sp_mantiene_datos_conciliados_emision_test
  → Datos_conciliados_of
```

## B. Objetos y roles

| Objeto | Tipo | Consume | Produce / rol |
|---|---|---|---|
| `sp_sincronizar_desde_etl` | SP | fuentes topográficas y THM | `topografia_avance`, `camiones_reclamo`, logs |
| `sp_cargar_cv25_horas` | SP | resumen CV025 y muestras de corriente | `cv25_diario`, `rotopala_horas_turno` |
| `sp_congelar_modulo` | SP | `disponible_rotopalas`, catálogo módulo | fotografía estable en `modulo_congelado` |
| `sp_establecer_linea_base` | SP | historia anterior al corte | previos de camiones y rotopala |
| `v_topografia_resuelta` | vista | acumulado topográfico | incremento diario no negativo |
| `v_camiones_acumulado` | vista | campos oficiales de camiones | diario y acumulado por campaña/módulo |
| `v_preliminar_cv25` | vista | CV025, horas y módulos abiertos | estimación diaria por módulo abierto |
| `v_preliminar_cv25_con_acumulado` | vista | preliminar + última topografía | acumulado que no retrocede; la usa `v_reclamo_diario` |
| `v_reclamo_diario` | vista | todos los anteriores | cálculo diario lógico |
| `sp_calcular_reclamo_diario` | SP | `v_reclamo_diario` | materializa `calculo_diario` |
| `v_cuadratura_modulo` | vista | base, historia, ajustes | saldo, porcentaje, excedente |
| `v_reclamo_para_conciliados` | vista | cálculo lógico actual | contrato del SP de publicación |

El inventario exhaustivo, fechas de creación/modificación, columnas, índices, FK, CHECK y dependencias se conserva en los CSV de la raíz de esta carpeta.

## C. Fórmulas centrales

Topografía, para registros posteriores al primero:

`m3_incremento = max(m3_acumulado_actual - m3_acumulado_anterior, 0)`.

Primera medición:

`m3_incremento = max(m3_acumulado_actual - m3_rotopala_previo, 0)`.

Camiones:

`m3_camiones_acum = suma(m3_oficial)` y `tms_camiones_acum = suma(tms_oficial)`, particionados por campaña y módulo desde el corte.

Disponible para rotopala:

`m3_disponible_roto = max(m3_totales - m3_camiones_acum, 0)`.

`tms_disponible_roto = max(tms_conformado - tms_camiones_acum, 0)`.

Rotopala diaria:

`m3_rotopala_dia = COALESCE(incremento_topografia, m3_preliminar_cv25, 0) + ajuste_m3`.

`tms_rotopala_dia = (incremento_topografia × densidad si existe topografía; si no, tms_preliminar) + ajuste_tms`.

Avances:

`avance_camiones = m3_camiones_acum / m3_totales`.

`avance_total = (m3_camiones_acum + m3_topografia_acum) / m3_totales`.

`avance_roto = acumulado_topográfico o preliminar / (m3_totales - m3_camiones_acum)`.

CV025:

`TMS_R1 = TMS_CV025 × horas_R1 / (horas_R1 + horas_R2)`; análogo para R2. Si las horas totales son cero, ambos estimados quedan `NULL`.

Cuadratura:

`camiones_total = m3_camiones_previo + m3_camiones_sistema`.

`rotopala_total = COALESCE(m3_topografia_acumulada_sistema, m3_rotopala_previo, 0)`; la línea base de rotopala no se suma a un acumulado topográfico que ya la contiene.

`extraido_total = camiones_total + rotopala_total + ajustes`.

`porcentaje_extraido = 100 × extraido_total / m3_totales`.

`excedente = max(extraido_total - m3_totales, 0)`.

## D. Evidencia operativa

La fecha de corte activa es `2026-07-01`; la tolerancia de cuadratura es `0,5 %`. PAD 1 corresponde a óxidos/R1, módulos físicos 1–64. PAD 2 corresponde a sulfuros/R2, módulos 1–140.

El caso solicitado como “M187 → M192” mezcla identificador y número visible. En campaña 8 PAD 2, `modulo_id=187` es el módulo visible 123; `modulo_id=192` es el visible 128. La secuencia extraída confirma esta correspondencia. En julio, la actividad topográfica visible progresa 123, 124, 125, 126, 127 y siguientes; el detalle diario íntegro está en `data_samples/calculo_pad2_camp8_julio.csv`.

Ejemplo real del 2026-07-01, `modulo_id=187`/módulo visible 123: volumen 102.709,9 m³, TMS 197.765,528, densidad 1,925477; incremento topográfico 10.325,714 m³ y 19.881,925 TMS. El acumulado topográfico es 100.439,216 m³, pero el incremento no duplica los 90.113,502 m³ de línea base.

## E. Dashboard y publicación

La vista previa consulta directamente `v_reclamo_para_conciliados`; no reconstruye el cálculo desde `calculo_diario`. El SP de publicación también consume esa vista, por lo que comparten contrato lógico. Sin embargo, una vista previa actual puede diferir de `calculo_diario` ya materializado y de una publicación histórica si las vistas cambiaron o el rango no se reprocesó/republicó.

El semáforo es informativo. El callback de Publicar pide confirmación y llama directamente al SP; no consulta el resultado del semáforo ni impide la ejecución por controles bloqueantes.

El SP de publicación suma TMS de todos los módulos por fecha y PAD. Para campaña/módulo/avance construye un “ganador” diario: prioriza el módulo con mayor tonelaje reclamado diario, usando criterios de desempate definidos en el SP. Camiones se agregan por PAD independientemente de que exista movimiento de rotopala, gracias al filtro corregido de `v_reclamo_para_conciliados`.

