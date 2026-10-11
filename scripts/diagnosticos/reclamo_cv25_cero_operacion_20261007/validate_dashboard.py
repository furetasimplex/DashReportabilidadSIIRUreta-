"""Validate the dashboard message logic with isolated, in-memory rows."""
import sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from reclamo import panel

base={'fecha_operacion':'2026-10-05','pad_id':2,'campana':11,
      'modulo_numero':16,'tms_rotopala_dia':0.0,'m3_rotopala_dia':0.0,
      'flag_calculo':'PRELIMINAR_CV25'}
def row(source,**extra): return {**base,'fuente_reclamo':source,**extra}
def text_of(node):
    if isinstance(node,(list,tuple)): return ' '.join(text_of(x) for x in node)
    if isinstance(node,str): return node
    return text_of(getattr(node,'children',[]))
def check(rows,required,forbidden=()):
    original=panel.db.avance_diario
    try:
        panel.db.avance_diario=lambda *_:pd.DataFrame(rows)
        _,message=panel.cb_avance(1,None,'2','2026-10-05','2026-10-05')
        rendered=text_of(message)
        for phrase in required: assert phrase in rendered,rendered
        for phrase in forbidden: assert phrase not in rendered,rendered
        return rendered
    finally: panel.db.avance_diario=original

results={
 'all_topography':check([row('TOPOGRAFIA')],['Todo el período tiene respaldo topográfico.']),
 'sin_dato':check([row('SIN_DATO')],['1 fila(s) sin respaldo topográfico ni proyección CV25.'],['Todo el período tiene respaldo topográfico.']),
 'both':check([row('PRELIMINAR_CV25'),row('SIN_DATO',modulo_numero=17)],
              ['1 combinaciones módulo/día con estimación CV25.','1 fila(s) sin respaldo topográfico ni proyección CV25.'],
              ['Todo el período tiene respaldo topográfico.']),
 'adjustment':check([row('AJUSTE_MANUAL')],['1 fila(s) con ajuste manual aprobado.'],['Todo el período tiene respaldo topográfico.']),
}
print('dashboard PASS', {k:len(v) for k,v in results.items()})
