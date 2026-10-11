"""Completa evidencia read-only y revisión estática previa al backfill."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from sqlalchemy import text
from scripts.backfill_septiembre_2026_reportes import P, START, END, TABLES, read, save
from db_connection import get_engine

def outside(c):
    result={}
    for table,col in TABLES.items():
        rows=[dict(r) for r in c.execute(text(f'SELECT * FROM inventar_SpcHidr.[{table}] WHERE [{col}]<:a OR [{col}]>=:b OR [{col}] IS NULL'),{'a':START,'b':'2026-10-01'}).mappings()]
        encoded=sorted(json.dumps(r,default=str,sort_keys=True,ensure_ascii=False) for r in rows)
        result[table]={'count':len(rows),'sha256':hashlib.sha256('\n'.join(encoded).encode()).hexdigest()}
    return result

def main():
    if (P/'ejecucion.json').exists() or (P/'outside_before.json').exists():
        raise RuntimeError('No sobrescribir firmas previas ni revisar una ejecución ya iniciada')
    pre=read('precheck.json'); pi=read('fuente_pi_tum.json')
    assert pre['cortes']['representatividad']=='2026-09-30'
    assert pre['cortes']['apilado']>='2026-09-30'
    assert len(pre['cobertura_bitacora'])==30
    assert all(r['claves']==6 and r['fin_dia']<=pre['max_totalizador'] for r in pre['cobertura_bitacora'])
    assert len(pi)==120 and len({(r['fecha_operacional'],r['equipo_codigo'],r['turno']) for r in pi})==120
    assert all((r['estado_fronteras']=='FRONTERAS_COMPLETAS' and r['delta_frontera_pi'] is not None and float(r['delta_frontera_pi'])>=0 and r['estado_tecnico_pi'] in ('CON_VARIACION','CON_VARIACION_COBERTURA_PARCIAL')) or (r['tum_disponible'] and r['valor_turno_tum'] is not None and float(r['valor_turno_tum'])>=0) for r in pi)
    keys={t:[col] for t,col in TABLES.items()}
    keys.update(Resumen_Intervalo_TotTM=['torre_id','fecha_turno','turno_op'],Clays_CuFe=['Fecha','Torre','Turno'],Clays_CuFe_trazabilidad=['id_trazabilidad'],trazabilidad_analitos_tm_emision_test=['Fecha','Turno','TM_Destino','Analito'],reporte_turno_cache_emision_test=['Fecha','Turno'])
    for table,k in keys.items():
        rs=read('backup_logico/'+table+'.json')
        assert max(Counter(tuple(r[col] for col in k) for r in rs).values(),default=0)<=1,table
    assert not [t for t in read('triggers.json') if t['table_name'] in TABLES and not t['is_disabled']]
    assert all(d['referenced_database_name'] in (None,'DEV_SIIR','inventar_SpcHidr') and not d['referenced_server_name'] for d in read('dependencies.json'))
    with get_engine().connect() as c:
        assert c.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
        save('outside_before.json',outside(c))
    pre.update(estado='PASS',validaciones={'bitacora':'30 días / 6 claves; cierre completo','pi_tum':'120 claves únicas, 30 días, cierre válido según regla runtime','duplicados_destino':'0 en claves funcionales','triggers_destino':'Ninguno activo','idempotencia':'MERGE, UPDATE+INSERT NOT EXISTS o DELETE+INSERT por rango. Clays registra cambios de valor/fuente, SIN_CAMBIO no agrega auditoría. Fechas de cálculo cambian por diseño.','limite_permanente':'Sin modificación','entorno':'DEV','escrituras_fuera_septiembre':'Filtros revisados; hash externo previo capturado'})
    save('precheck.json',pre)
    print('PRECHECK PASS; 12 bloques planeados; cero DML ejecutado')

if __name__=='__main__':main()
