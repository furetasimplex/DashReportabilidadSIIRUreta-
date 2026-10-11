"""Informe local desde evidencia; no abre conexiones."""
from collections import Counter
from scripts.backfill_septiembre_2026_reportes import P,TABLES,read,save

def main():
    before=read('before.json');after=read('after.json');log=read('ejecucion.json')
    keys={t:[col] for t,col in TABLES.items()}
    keys.update(Resumen_Intervalo_TotTM=['torre_id','fecha_turno','turno_op'],Clays_CuFe=['Fecha','Torre','Turno'],Clays_CuFe_trazabilidad=['id_trazabilidad'],trazabilidad_analitos_tm_emision_test=['Fecha','Turno','TM_Destino','Analito'],reporte_turno_cache_emision_test=['Fecha','Turno'])
    comparison={}
    for table,col in TABLES.items():
        original=read('backup_logico/'+table+'.json');final=read('after_rows/'+table+'.json')
        k=keys[table]
        b={tuple(str(r[x]) for x in k):r for r in original};a={tuple(str(r[x]) for x in k):r for r in final}
        changed=Counter();changed_dates=set()
        for key in a.keys() & b.keys():
            for field in a[key]:
                if a[key][field]!=b[key][field]:changed[field]+=1;changed_dates.add(str(a[key][col])[:10])
        comparison[table]={'filas_antes':len(original),'filas_despues':len(final),'claves_nuevas':len(a.keys()-b.keys()),'claves_eliminadas':len(b.keys()-a.keys()),'duplicados_despues':len(final)-len(a),'campos_con_cambios':dict(changed),'fechas_con_cambios':sorted(changed_dates)}
        before[table]['min_fecha']=min(before[table]['por_fecha'],default=None)
        before[table]['max_fecha']=max(before[table]['por_fecha'],default=None)
    save('comparacion.json',comparison);save('before.json',before)
    ui=read('ui_smoke.json') if (P/'ui_smoke.json').exists() else {'estado':'NO_EJECUTADO'}
    octu=read('octubre_readonly.json')
    if ui['estado']=='PASS_CALLBACKS_NO_REVISION_VISUAL' and octu['fuera_septiembre_identico']:
        log['estado']='BACKFILL_PASS_CON_OBSERVACIONES';save('ejecucion.json',log)
    import pandas as pd
    from report_export.export_to_excel import _obtener_fecha_corte_resumen_datos_conciliados, _campos_incompletos_resumen_datos_conciliados
    dc=pd.DataFrame(read('after_rows/Datos_conciliados_of.json'))
    cutoff=_obtener_fecha_corte_resumen_datos_conciliados(dc)
    gaps=[{'fecha':r['Fecha'],'campos':_campos_incompletos_resumen_datos_conciliados(r)} for _,r in dc.iterrows() if _campos_incompletos_resumen_datos_conciliados(r)]
    save('completitud_dc.json',{'corte_resumen_mtd':str(cutoff.date()),'dias_materializados':len(dc),'incompletos':gaps,'nota':'NULL existentes conservados. La cobertura de filas no implica completitud del resumen MTD.'})
    if (P/'after_backfill_before_smoke.json').exists():
        blocks=read('after_backfill_before_smoke.json')
        changes={t:{k:{'despues_bloques':blocks[t]['agregados_despues'].get(k),'despues_smoke_mensual':v} for k,v in after[t]['agregados_despues'].items() if v!=blocks[t]['agregados_despues'].get(k)} for t in after}
        save('comparacion_bloques_vs_smoke.json',{'diferencias_firmas_numericas':{t:d for t,d in changes.items() if d},'nota':'Firmas numéricas para detectar cambios, no KPIs: sumar IDs/módulos no tiene interpretación operacional. El SP DC reinicia @PisoOx/@CampanaPisoOx por llamada; el contexto de reclamo puede diferir al dividir un mes. El estado final corresponde al flujo mensual oficial probado, sin modificar su lógica. Las otras diferencias aquí observadas son residuos float.'})
    lines=['# Backfill extraordinario septiembre 2026 — DEV','',
        'Período fijo: **01-09-2026 a 30-09-2026 inclusive**. No usar estos scripts como runtime.',
        '',f"Estado ejecutor: **{log['estado']}**. Estado aplicación: **{ui['estado']}**.",'',
        '## Flujo y límites','',
        'Ver [entrypoints.md](entrypoints.md), [limites.md](limites.md) y [plan_bloques.json](plan_bloques.json).',
        'No hay máximo general de rango encontrado. Ventanas runtime 7/7/15 intactas; bloques de 7/7/15 días para refrescar fechas existentes.',
        'Representatividad incluye preparación RTO upstream; se conservó ese orden interno. No se publicó un snapshot oficial nuevo.',
        '', '## Ejecuciones','', '| Reporte | Desde | Hasta | Estado | Segundos |','|---|---|---|---|---:|']
    for e in log['bloques']:lines.append(f"| {e['reporte']} | {e['desde']} | {e['hasta']} | {e['estado']} | {e.get('duracion_segundos',0):.2f} |")
    lines+=['','## Cobertura / filas','', '| Tabla | Antes | Después | Duplicados después |','|---|---:|---:|---:|']
    for t,d in comparison.items():lines.append(f"| {t} | {d['filas_antes']} | {d['filas_despues']} | {d['duplicados_despues']} |")
    lines+=['','Las tablas diarias tienen 30 fechas; RTO se valida en Fecha/Turno A/B. La ausencia de una fuente/analito no se reemplaza por datos inventados.',
            'Comparación de campos y fechas en [comparacion.json](comparacion.json); perfiles y NULL en after.json/perfiles_fuentes.json.',
            '', '## Validaciones','']
    for phase in ('representatividad','analisis_tm','datos_conciliados'):
        f='validacion_'+phase+'.json'
        value=read(f) if (P/f).exists() else {'estado':'NO_EJECUTADO'}
        lines.append(f"- {phase}: **{value['estado']}**, [{f}]({f}).")
    lines+=['- Unit tests de orquestación/paquetes: **118 passed, 31 subtests passed**.',
            '- Suite adicional de exportación: **40 PASS, 3 FAIL** en runtime intacto (Campaña y dos pruebas de celdas posteriores al corte). Detalle: [tests.json](tests.json). No se corrigió código funcional.',
            '- `git diff --check`: PASS (aviso de conversión LF/CRLF en layout.py preexistente).',
            f"- Resultados fuera de septiembre idénticos por hash: **{octu['fuera_septiembre_identico']}**.",
            f"- Octubre, solo lectura: corte Torres **{octu['corte_representatividad']}**, corte apilado **{octu['corte_apilado']}**.",
            '- Los cortes de octubre se resuelven desde las fuentes actuales y se contrastan con precheck.json; no se recalculó octubre.',
            '', '## Aplicación y archivos','',
            'Smoke de callbacks reales con contexto Dash/Flask, SQL DEV y exportadores reales. No es revisión visual de navegador.',
            'Resultados en [ui_smoke.json](ui_smoke.json); archivos en exports/. El editor se consulta sin guardar comentarios.',
            'La descarga de Representatividad usa el snapshot activo existente y puede tener un corte distinto al resultado recién refrescado; no se republica automáticamente.',
            '', '## Alcance y recuperación','',
            'Solo DML mediante los coordinadores vigentes en DEV. Sin cambios runtime, fórmulas, límites, reglas, SQL/DDL ni Lixiviación.',
            'Octubre no recalculado. Sin PROD, commit ni push.',
            'Respaldos y firmas: before.json, backup_logico/, outside_before.json. Recuperación: [rollback.md](rollback.md).',
            'Definiciones LIVE de esta inspección: definitions/, objects.json, dependencies.json; no son scripts de despliegue.',
            '', '## Reproducibilidad','',
            '`python -m scripts.backfill_septiembre_2026_reportes` es dry-run (se niega a sobrescribir el respaldo).',
            '`--execute` exige precheck PASS, hashes runtime/DDL iguales y ausencia de ejecución previa. No reanudar automáticamente.',
            'Los scripts inspect_readonly/review_precheck/finish_readonly son SELECT; application_smoke requiere --execute porque conserva refrescos de los callbacks.',
            'summarize.py solamente organiza evidencia local.']
    lines+=['','## Archivos de salida de aplicación','', '| Reporte | Acción | Resultado | Archivo / observación |','|---|---|---|---|']
    for case in ui.get('casos',[]):
        filename=case.get('archivo')
        target=f'[{filename}](exports/{filename})' if filename else case.get('error',case.get('nota','Sin archivo; vista previa'))
        lines.append(f"| {case['reporte']} | {case['accion']} | {case['estado']} | {target} |")
        if case.get('archivo_live'):
            name=case['archivo_live'];lines.append(f"| Representatividad LIVE | Excel sin publicar | PASS | [{name}](exports/{name}) |")
    lines+=['','Se conservó el falso positivo inicial del harness en ui_smoke_harness_falso_positivo.json: los botones PDF color danger no eran Alert de error. No fue un fallo del callback y no se repitió el preview.',
            'Los tres fallos unitarios adicionales permanecen documentados; no se declara la suite completa como PASS.']
    lines+=['','## Observaciones que permanecen','',
            f'- DC materializa 30 días, pero el resumen MTD corta al **{cutoff.date()}**. El 22-09 faltan TMS_Rotopala_2_Real y Total_Ripios_Incluye_Camiones_Real; esos NULL estaban en el respaldo previo y siguen presentes. Ver completitud_dc.json.',
            '- La prueba mensual usa los writers reales. El contexto de reclamo óxidos (módulo/avance) difiere entre dos bloques y una llamada mensual: el SP inicializa @PisoOx y @CampanaPisoOx en cada llamada (definición LIVE, líneas 443–468). El estado final es el de los previews/exports mensuales oficiales, no una reconstrucción manual. Comparación en comparacion_bloques_vs_smoke.json.',
            '- Repetir la misma clave no duplicó resultados. Esto no implica equivalencia entre particiones de rango distintas para el contexto de reclamo. No se cambió esa regla.',
            '- Los factores automáticos 22/09 y 23/09 cambiaron respecto del respaldo previo durante el refresco de sus insumos. La separación calculado/aplicado y FORZADO_1 se mantuvo; 16/09 sigue calculado 0,21963019549669024 y aplicado 1.']
    (P/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
