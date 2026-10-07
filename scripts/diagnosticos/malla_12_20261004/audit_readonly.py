"""Read-only DEV snapshot for 2026-10-04 Malla -1/2 tracing."""
import json, os, sys
from pathlib import Path
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from db_connection import get_engine
BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr':
    raise RuntimeError('Expected DEV inventar_SpcHidr')
names=['sp_actualizar_reporte_turno_cache_emision_test',
 'sp_reporte_turno_emision_test',
 'reporte_turno_cache_emision_test','v_reporte_turno_reales_test',
 'v_reporte_turno_fuentes_info_test','v_leyes_resueltas_data_tm_reporte_test',
 'v_leyes_resueltas_data_tm_reporte_test_v2','v_leyes_validadas_tm_turno',
 'v_validacion_leyes_tm1_v2','v_validacion_leyes_tm2_v2',
 'v_representatividad_diaria_calculada','v_peso_real_torre_turno_excel',
 'v_peso_teorico_turno_torre_excel','Informe_TM_lab',
 'representatividad_torres_resultado',
 'v_datos_apilado_tmh_v2','v_sal_ajustada',
 'v_ajuste_camiones_emision_test','v_reporte_diario_humedad_test',
 'v_apilado_tms_con_sal_srr_reporte_test']
out={}
with get_engine().connect() as con:
    ident=dict(con.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at')).mappings().one())
    if ident['database_name'].lower()!='inventar_spchidr': raise RuntimeError('wrong database')
    for name in names:
        obj='inventar_SpcHidr.'+name
        meta=con.execute(text('SELECT o.type_desc,o.modify_date,OBJECT_DEFINITION(o.object_id) definition FROM sys.objects o WHERE o.object_id=OBJECT_ID(:obj)'),{'obj':obj}).mappings().first()
        cols=[dict(x) for x in con.execute(text('SELECT c.name,c.column_id FROM sys.columns c WHERE c.object_id=OBJECT_ID(:obj) ORDER BY c.column_id'),{'obj':obj}).mappings()]
        item={'metadata':dict(meta) if meta else None,'columns':cols}
        date_col=next((c['name'] for c in cols if c['name'].lower()=='fecha'),None)
        if date_col and meta and name in {
            'reporte_turno_cache_emision_test',
            'v_representatividad_diaria_calculada',
            'v_peso_real_torre_turno_excel',
            'v_peso_teorico_turno_torre_excel',
            'Informe_TM_lab',
            'representatividad_torres_resultado',
            'v_datos_apilado_tmh_v2','v_sal_ajustada',
            'v_ajuste_camiones_emision_test','v_reporte_diario_humedad_test',
            'v_apilado_tms_con_sal_srr_reporte_test',
        }:
            sql=f'SELECT TOP (30) * FROM [{obj.split(".")[0]}].[{name}] WHERE [{date_col}] >= :start AND [{date_col}] < :end'
            try:
                item['rows']=[dict(x) for x in con.execute(text(sql),{'start':'2026-10-04','end':'2026-10-05'}).mappings()]
            except Exception as exc:
                item['select_error']=str(exc)
        out[name]=item
(BASE/'snapshot.json').write_text(json.dumps({'identity':ident,'objects':out},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(ident)
for k,v in out.items(): print(k, v['metadata']['type_desc'] if v['metadata'] else None, len(v['columns']),len(v.get('rows',[])),v.get('select_error','')[:120])
