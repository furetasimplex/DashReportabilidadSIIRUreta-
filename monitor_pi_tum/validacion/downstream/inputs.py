"""Lectura de inputs y SP de cálculo puro del factor; no persiste datos."""
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev,_assert_dev_connection
from .inspeccionar import OUT,save
def main():
    with _engine_dev().connect() as c:
        _assert_dev_connection(c)
        names=['Historico_Apilado_Diario','v_datos_apilado_tmh_v2','v_srr_tms_origen_turno_emision_test','v_inventario_chancado_test','v_humedad_inventario_test','v_reporte_diario_humedad_test','v_ajuste_camiones_emision_test']
        for n in names:
            rows=[dict(r) for r in c.execute(text(f"SELECT * FROM inventar_SpcHidr.{n} WHERE Fecha='20260910'")).mappings()]
            save('input_'+n,rows);print(n,len(rows),flush=True)
        save('calculo_factor_actual',[dict(r) for r in c.execute(text("EXEC inventar_SpcHidr.sp_factor_ajuste_camiones_test @FechaInicio='20260910',@FechaFin='20260910'")).mappings()])
        modules=[dict(r) for r in c.execute(text("SELECT OBJECT_SCHEMA_NAME(object_id)+'.'+OBJECT_NAME(object_id) nombre,definition FROM sys.sql_modules WHERE definition LIKE '%Historico_Apilado_Diario%' OR definition LIKE '%Control_Apilado_TMH_v2_test%'")).mappings()]
        for m in modules:(OUT/(m['nombre']+'.sql')).write_text(m['definition'],encoding='utf-8')
        save('referencias_historico',[m['nombre'] for m in modules])
        save('triggers_y_columnas',[dict(r) for r in c.execute(text("SELECT OBJECT_SCHEMA_NAME(t.parent_id)+'.'+OBJECT_NAME(t.parent_id) tabla,t.name,t.is_disabled,OBJECT_DEFINITION(t.object_id) definicion FROM sys.triggers t WHERE t.parent_id IN (OBJECT_ID('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test'),OBJECT_ID('inventar_SpcHidr.reporte_turno_cache_emision_test'),OBJECT_ID('inventar_SpcHidr.trazabilidad_analitos_tm_emision_test'))")).mappings()])
        save('columnas_trazabilidad',[dict(r) for r in c.execute(text("SELECT name,is_identity,TYPE_NAME(user_type_id) tipo FROM sys.columns WHERE object_id=OBJECT_ID('inventar_SpcHidr.trazabilidad_analitos_tm_emision_test')")).mappings()])
if __name__=='__main__':main()
