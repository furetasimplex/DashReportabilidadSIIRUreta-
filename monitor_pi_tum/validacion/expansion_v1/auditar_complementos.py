"""Consultas complementarias de solo lectura para cierre."""
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev,_assert_dev_connection
from monitor_pi_tum.validacion.expansion_v1.auditar_balance import save, DATES, OUT

def main():
    with _engine_dev().connect() as c:
        _assert_dev_connection(c)
        names=['inventar_SpcHidr.v_peso_teorico_turno_torre_excel','inventar_SpcHidr.v_bd_ton_t12','reclamo.v_preliminar_cv25','reclamo.v_preliminar_cv25_con_acumulado','reclamo.v_reclamo_diario']
        names += [n+'_contingencia_test' for n in names[-3:]]
        for n in names:
            try:
                definition=c.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'),{'n':n}).scalar()
                if definition:
                    (OUT/(n+'.sql')).write_text(definition,encoding='utf-8')
                cols=c.execute(text('SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(:n)'),{'n':n}).scalars().all()
                dc=next((x for x in cols if x.lower() in ('dia','fecha','fecha_turno','fecha_operacional','fecha_operacion')),None)
                if not dc:
                    save('extra_'+n,{'columnas':cols}); continue
                dates=','.join("'"+x+"'" for x in DATES)
                rows=[dict(r) for r in c.execute(text(f'SELECT * FROM {n} WHERE [{dc}] IN ({dates})')).mappings()]
                save('extra_'+n,rows); print(n,len(rows),flush=True)
            except Exception as e:
                save('extra_'+n,{'error':str(e)})
        rows=[dict(r) for r in c.execute(text("SELECT batch_id,template_code,dataset_name,JSON_VALUE(business_key_json,'$.equipo_codigo') equipo,COUNT(*) filas FROM DEV_SIIR.hidro.import_row_history WHERE batch_id IN (10439,10463,20454,20455) GROUP BY batch_id,template_code,dataset_name,JSON_VALUE(business_key_json,'$.equipo_codigo')")).mappings()]
        save('historial_templates',rows)

if __name__=='__main__': main()
