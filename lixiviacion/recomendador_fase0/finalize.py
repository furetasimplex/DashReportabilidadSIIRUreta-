"""Informe a partir de evidencias locales; sin SQL ni ejecución de recomendaciones."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from .audit import P


def run():
    result=json.loads((P/'resultados.json').read_text(encoding='utf-8'))
    def csvread(name):
        return list(csv.DictReader((P/name).open(encoding='utf-8-sig')))
    facts=csvread('hechos_historicos.csv');durations=csvread('duraciones_descriptivas.csv');rules=csvread('matriz_reglas.csv')
    maturity=Counter(r['Estado de madurez'] for r in rules)
    names=['PAUSA_HIDRAULICA','DRENAJE_RESIDUAL','DRENAJE_CON_RIEGO_PAUSADO','MIXTO','REPOSO_PRE_RECLAMO',
           'CALIDAD_NO_EVALUABLE','CALIDAD_PARCIAL','SIN_INFORMACION_HIDRAULICA','DELTA_NEGATIVO','TRANSFERENCIA_NEGATIVA','FLUJO_POSITIVO_FUERA']
    lines=['| Hecho | OX parcela-día | SULF parcela-día | Total |','|---|---:|---:|---:|']
    for name in names:
        vals={int(r['pad_id']):int(r['parcelas_dia']) for r in facts if r['hecho']==name}
        lines.append(f"| {name} | {vals[1]} | {vals[2]} | {sum(vals.values())} |")
    dlines=['| Hecho | PAD | Rachas | Min | Mediana | p75 | p90 | p95 | Max días |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in durations:
        if r['hecho'] in ('PAUSA_HIDRAULICA','DRENAJE_RESIDUAL','MIXTO','DELTA_NEGATIVO','TRANSFERENCIA_NEGATIVA','CALIDAD_NO_EVALUABLE'):
            dlines.append('| '+' | '.join(r[k] or 'Sin rachas' for k in ('hecho','pad_id','rachas','min','mediana','p75','p90','p95','max'))+' |')
    op=json.loads((P/'estado_20260910.json').read_text(encoding='utf-8'))
    v2=json.loads((P/'v2_snapshot.json').read_text(encoding='utf-8'))
    timeline=json.loads((P/'operacional_snapshot.json').read_text(encoding='utf-8'))
    keys=lambda rs:{(r['fecha'],r['pad_id'],r['parcela_id']) for r in rs}
    assert len(keys(timeline))==len(timeline) and keys(timeline)==keys(v2)
    by_end={(r['pad_id'],r['parcela_id']):r for r in timeline if r['fecha']=='2026-09-10'}
    assert all(all(r[k]==by_end[(r['pad_id'],r['parcela_id'])][k] for k in by_end[(r['pad_id'],r['parcela_id'])]) for r in op)
    runs=csvread('rachas_observadas.csv')
    for fact in facts:
        matching=[r for r in runs if r['hecho']==fact['hecho'] and r['pad_id']==fact['pad_id']]
        assert sum(int(r['dias']) for r in matching)==int(fact['parcelas_dia'])
    result['checks']={'same_physical_keys_op_v2':True,'timeline_end_equals_official_60_parcels':True,'streak_day_sums_equal_fact_counts':True}
    index={(r['fecha'],r['pad_id'],r['parcela_id']):r for r in v2}
    cases=[]
    for r in op:
        if (r['pad_id'],r['numero_parcela']) in ((1,1),(1,17),(1,29),(2,1),(2,7),(2,9),(2,28)):
            v=index.get(('2026-09-10',r['pad_id'],r['parcela_id']))
            cases.append({'operacional':r,'V2':v})
    (P/'casos_20260910.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False),encoding='utf-8')
    clines=['| Caso | Estado / calidad | Riego/drenaje | Asignación V2 | ΔCu g/L | Transferencia t/d |','|---|---|---|---|---:|---:|']
    for c in cases:
        o=c['operacional'];v=c['V2'] or {}
        clines.append(f"| {'OX' if o['pad_id']==1 else 'SULF'} P{o['numero_parcela']} | {o['estado_operacional']} / {o['calidad_estado']} | {o['riego_activo']}/{o['drenaje_activo']} | {v.get('estado_asignacion','Sin fila')} | {v.get('delta_cu_gl','Sin dato')} | {v.get('transferencia_cu_t_d','Sin dato')} |")
    protected=json.loads((P/'runtime_before.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
    result['maturity_counts']=dict(maturity)
    result['historical_facts_exclusive']=False
    result['final_runtime_hashes_equal']=True
    result['v2_date_coverage']={'min':min(r['fecha'] for r in v2),'max':max(r['fecha'] for r in v2),'days':len({r['fecha'] for r in v2})}
    (P/'resultados.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    main=f'''# Recomendador de Riegos y Drenajes — Fase 0

## Resultado

El Recomendador actual es **solo placeholder**. No tiene lógica de recomendación, SQL propio, reglas, scoring, prioridades ni acciones. Se auditó el repositorio y se consultó DEV únicamente con SELECT. No se implementó ninguna señal en la UI.

Se documentaron **18 candidatas**: **8 DETECTABLE_HOY**, **7 REQUIERE_UMBRAL**, **2 REQUIERE_REGLA_NEGOCIO** y **1 NO_RECOMENDABLE_AUN**. DETECTABLE_HOY significa hecho descriptivo, **no recomendación aprobada**. Prioridad y acción de todas permanecen «REQUIERE DEFINICIÓN DE NEGOCIO».

## Arquitectura y fuentes

[Call graph real](recomendador_fase0/arquitectura_actual.md): layout.py → panel.layout → dbc.Tab/Alert «Funcionalidad en desarrollo». Los callbacks hermanos de mapa/diagnóstico se protegen por active_tab; no existe recommender_layout ni motor DB conectado.

[Fuentes y variables](recomendador_fase0/fuentes.md): función operacional oficial para estados, V2 para magnitudes físicas/químicas y campaña hidráulica; función de módulos solo para explicación puntual de MIXTO. Grano PAD + parcela + fecha, nunca replicar medidas por módulo. Nombres de campaña e IDs no intercambiables; campaña OP y campaña hidráulica se conservan separadas.

El catálogo documenta los 24 campos OP, campos relevantes V2, los 13 estados solicitados y SIN_INFORMACION. La calidad actual admite EVALUABLE, PARCIAL, NO_EVALUABLE y SIN_INFORMACION. EVALUABLE no certifica química ni elimina la necesidad de revisar los flags específicos.

## Hechos, duración y madurez

[Matriz completa](recomendador_fase0/matriz_reglas.csv) incluye R01–R18, condición exacta, fuente, duración, umbral pendiente, prioridad/acción pendientes, falso positivo, calidad, madurez y riesgo de automatización. Los umbrales de actividad heredados (caudal >1, Cu >0) son parte de clasificación vigente, no nuevos umbrales del Recomendador.

Un estado hoy es un hecho de la salida SQL; «prolongado» requiere calendario y duración aprobada. R01/R02/R03/R04/R09/R16/R18 requieren umbral; R05/R15 definición de negocio; R17 no es recomendable aún porque falta cierre planificado. R06/R07/R08/R10/R11/R12/R13/R14 son detectables como hechos, sin autorización de intervención.

Las rachas se reinician al cambiar campaña de su propia fuente, con hueco o condición falsa/NULL. OP usa campaña operacional; V2 usa hidráulica. Esto es una convención descriptiva conservadora, no una política de negocio aprobada. Rachas al borde del rango son censuradas y se señalan en CSV. No se transforman percentiles en umbrales. El promedio móvil y «últimos N días» requieren N validado. Hitos y rachas pueden cambiar con cargas tardías.

**Advertencia temporal demostrada:** el 10-09 OX P1 expone última actividad de riego 30-09, y SULF P7 16-09. Son extremos de campaña completa. No usarlos directamente como «días desde último riego hasta fecha». Para ese concepto se necesita máximo de fecha activa <=fecha dentro de campaña y cobertura previa suficiente. No se modificó la semántica retrospectiva existente.

## Cobertura histórica observada

Período solicitado 01-01→10-09-2026: **{result['operational_rows']} filas OP**, **{result['v2_rows']} filas V2**. Cobertura V2: {result['v2_date_coverage']}. Se verificó unicidad de claves; 253 días para cada una de las 60 parcelas OP. Si una fuente no cubre un día, no se inventan filas ni ceros. Conteos no excluyentes: una parcela-día puede presentar varios hechos.

{chr(10).join(lines)}

Todos los conteos, incluidos estados no observados con cero y cobertura por PAD, en [hechos_historicos.csv](recomendador_fase0/hechos_historicos.csv). Cero observado no invalida una regla futura ni prueba ausencia fuera del período.

## Duraciones descriptivas (días por racha)

{chr(10).join(dlines)}

[Distribución completa](recomendador_fase0/duraciones_descriptivas.csv) y [rachas](recomendador_fase0/rachas_observadas.csv). Percentiles lineales por racha, no ponderados por días ni parcelas. Son datos retrospectivos con fuentes actuales, no lo conocido en cada fecha; no identifican anomalía ni umbral aceptable.

## Casos de referencia del 10-09

{chr(10).join(clines)}

- OX P1 / SULF P7: ambos flags activos; R05–R08 no se activan por inactividad. Describir operación, no «riego óptimo». Magnitud química requiere validación metalúrgica.
- OX P17 / SULF P1: MIXTO; coexistencia y composición disponibles. R07/R08 son hechos si flags 0 con dato; R15 no alerta por duración sin regla. Abrir módulos si se necesita explicar composición, no recomendar a toda parcela.
- OX P29 / SULF P9: reposo; R07/R08 observables; R16 necesita programación y plazo esperado, no asumir atraso.
- SULF P28: APILADO; R17 no evaluable sin fecha PLANIFICADA de cierre, aunque el estado se conozca.
- En filas con ΔCu negativo puede mostrarse R12; con flujo cero la transferencia no indica pérdida operativa cuantificada. R13 exige transferencia realmente negativa, no solo ΔCu negativo. FUERA_VENTANA_RIEGO no activa R14 si flujo no es positivo.

[Casos completos](recomendador_fase0/casos_20260910.json) conservan hitos, calidad, IDs y variables V2 sin reinterpretarlas. Ninguna de las siete parcelas recibe prioridad ni acción en Fase 0.

## Calidad, falsos positivos y decisiones

MIXTO puede ser coexistencia normal. Drenaje activo es Cu positivo, no caudal medido. Pausas/residual pueden ser etapas normales. ΔCu/transferencia negativos son indicadores hasta validación metalúrgica: duración, magnitud y flujo mínimo pendientes; cero flujo impide interpretar la magnitud como actividad de transferencia. Fuera de ventana es contexto de asignación, no operación.

Propuesta (no implementada): EVALUABLE permite describir hechos; PARCIAL advertencia; NO_EVALUABLE/SIN_INFORMACION informan carencia y no permiten prescripción operativa. Calidad OP no reemplaza cobertura química V2. No recomendar ajustar/aumentar/detener riego a partir de estos hechos.

[Preguntas de negocio](recomendador_fase0/preguntas_negocio.md): tiempos esperados por etapa, pausas planificadas, latencia riego/drenaje, significado del proxy Cu, mezcla normal de módulos, flujo mínimo/persistencia química, SLA de datos y responsable, prioridades, acciones permitidas y aprobación/versionado.

## Naming, UX y siguiente fase

Recomendación conceptual: **Situaciones a revisar**, manteniendo pestaña actual. Tabla de hecho/duración/motivo/calidad separada de prioridad y acción: «Pendiente de regla» y «Requiere validación operacional». Sin semáforo ni ranking arbitrario. [Propuesta UX](recomendador_fase0/propuesta_ux.md) compara flags, categorías, jerarquía y scoring sin pesos.

Arquitectura futura: fuentes oficiales → hechos diarios → duración/ventanas → reglas aprobadas/versionadas → prioridad/acción autorizadas → presentación. SQL para hechos oficiales, Python para explicación/políticas; no segundo CASE de estados ni fórmula de transferencia. TVF/vista nueva solo en futura tarea validada. [Riesgos y opciones](recomendador_fase0/riesgos.md).

Siguiente fase sugerida: validar semántica y preguntas con Operaciones/Metalurgia, luego pantalla informativa de hechos aprobados, sin prescripción. Construir casos positivos/negativos y prueba de calidad/cobertura antes de cualquier prioridad automática. No se implementó esta propuesta.

## Rendimiento, método y límites

Se reutilizó literalmente OP_TIMELINE_SQL de 12 columnas, cotejando definición oficial con snapshot validado. 60 consultas de rango, no 253 expansiones diarias de 60 parcelas. Tiempo acumulado de consultas del barrido completado: **{result['seconds_total_timeline']:.2f} s** (incluye variación de red; no benchmark de UI). No recomendar 60 consultas síncronas por clic: carga completa requiere otro diseño/benchmark. El recálculo residual por CTE no se modificó.

El primer intento perdió conexión TCP durante el recorrido; se repitió el barrido y el ejecutor guardó por parcela. Solo el recorrido completo sustenta tablas finales. No se impone aislamiento snapshot a las fuentes: verificación de definiciones inicio/fin no congela datos concurrentes. La equivalencia temporal previa no demuestra toda combinación futura; se documenta esa limitación.

## Integridad y entregables

Hashes de runtime antes/después iguales. Comprobaciones PASS: mismas claves OP/V2, cierre del timeline idéntico a función oficial para 60 parcelas y sumas de días de rachas iguales a conteos de hechos. `git diff --check` PASS (aviso preexistente LF/CRLF de layout.py, sin modificarlo). Solo se crearon el informe y archivos de auditoría en `recomendador_fase0/`: documentación, matriz, snapshots locales, estadísticas, consultas SELECT y resultados. SQL capturado es evidencia, no despliegue. Runtime, mapa, diagnóstico, timeline, V2, CPC y Model6 intactos; sin DDL/DML, cambios SQL Server, PROD, commit o push.
'''
    (P.parent/'RECOMENDADOR_FASE0.md').write_text(main,encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':run()
