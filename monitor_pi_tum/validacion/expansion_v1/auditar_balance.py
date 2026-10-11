"""Ejecuta cálculos existentes DEV sin persistencia; captura resultados y errores."""
import json
from pathlib import Path
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection

OUT=Path(__file__).parent/'cierre'
DATES=['2026-08-31','2026-09-07','2026-09-08','2026-09-10','2026-09-13']
def save(name,data):
    (OUT/(name+'.json')).write_text(json.dumps(data,default=str,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    engine=_engine_dev()
    for day in DATES:
        for kind,name in [('oficial','sp_calcular_balance_flujos'),('TEST','sp_calcular_balance_flujos_contingencia_test')]:
            with engine.connect() as c:
                _assert_dev_connection(c)
                try:
                    rows=[dict(r) for r in c.execute(text(f'EXEC inventar_SpcHidr.{name} @fecha_inicio=:d,@fecha_fin=:d'),{'d':day}).mappings()]
                    save('balance_'+day+'_'+kind,rows)
                    print(day,kind,len(rows),flush=True)
                except Exception as e:
                    save('balance_'+day+'_'+kind,{'error':str(e)})
                    print(day,kind,'ERROR',flush=True)
                finally:
                    c.rollback()
    with engine.connect() as c:
        _assert_dev_connection(c)
        rows=[dict(r) for r in c.execute(text("SELECT CAST(fecha_turno AS date) fecha, MIN(COALESCE(TRY_CONVERT(float,cv025_tot),TRY_CONVERT(float,cv025tot))) minimo, MAX(COALESCE(TRY_CONVERT(float,cv025_tot),TRY_CONVERT(float,cv025tot))) maximo, COUNT(*) muestras FROM inventar_SpcHidr.datos_filtrados WHERE fecha_turno >= '20260907' AND fecha_turno < '20260915' GROUP BY CAST(fecha_turno AS date) ORDER BY fecha")).mappings()]
        save('cv025_diagnostico_pi',rows)

if __name__=='__main__':
    main()
