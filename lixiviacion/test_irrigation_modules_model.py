import copy
import hashlib
import pytest
from . import irrigation_modules_model as m

def roster():
    return m.roster_context([dict(fecha='2026-10-19',pad_id=2,parcela_id=59,campana_id=10,numero_campana='11',
        estado_roster='CONFIABLE',total_modulos=5,modulo_id=195+i,nombre_visible=f'M{131+i}',control_id_snapshot=500+i,
        secuencia_carguio=i+1,orden_incremental=i+1,fecha_ini_carguio=f'2026-08-{21+i}',
        fecha_fin_carguio=None,fecha_ini_retiro=None,fecha_fin_retiro='2026-09-01' if i==0 else None) for i in range(5)])

@pytest.mark.parametrize('n,state,count,ids',[(3,'VALIDA',3,[195,196,197]),(0,'VALIDA',0,[]),
    (None,'SIN_INFORMACION',None,None),(6,'INCONSISTENTE',6,None),(-1,'INCONSISTENTE',None,None),
    (True,'INCONSISTENTE',None,None),(3.5,'INCONSISTENTE',None,None),('3','VALIDA',3,[195,196,197])])
def test_reference_semantics(n,state,count,ids):
    r=roster();before=copy.deepcopy(r);out=m.reference_preview(r,n)
    assert out['estado']==state and out['cantidad']==count
    assert (None if out['sugeridos'] is None else [x['modulo_id'] for x in out['sugeridos']])==ids
    assert r==before

def test_manual_not_reference_and_retired_remains():
    r=roster();ref=m.reference_preview(r,3)
    assert m.selection(r,'SELECCION_CONOCIDA',[195,197,198])==([195,197,198],3)
    assert [x['modulo_id'] for x in ref['sugeridos']]==[195,196,197]
    assert len(r['miembros'])==5

def test_ambiguous_never_autosuggests_but_manual_is_possible():
    r=roster();r.update(orden_confiable=False,estado_roster='ORDEN_AMBIGUO')
    assert m.reference_preview(r,3)['sugeridos'] is None
    assert m.reference_preview(r,3)['estado']=='ORDEN_AMBIGUO'
    assert m.selection(r,'SELECCION_CONOCIDA',[195])[1]==1

@pytest.mark.parametrize('state,ids',[('SELECCION_CONOCIDA',[]),('NINGUN_MODULO',[195]),('SIN_INFORMACION',[195]),
    ('OTRO',[]),('SELECCION_CONOCIDA',[195,195]),('SELECCION_CONOCIDA',[999]),('SELECCION_CONOCIDA',[True])])
def test_bad_selection(state,ids):
    with pytest.raises(ValueError):m.selection(roster(),state,ids)

def test_zero_distinct_from_unknown():
    assert m.selection(roster(),'NINGUN_MODULO',[])[1]==0
    assert m.selection(roster(),'SIN_INFORMACION',[])[1] is None

def test_missing_roster_cannot_confirm():
    r=roster();r.update(campana_id=None,total=None)
    with pytest.raises(ValueError):m.selection(r,'NINGUN_MODULO',[])
    assert m.reference_preview(r,2)['estado']=='INCONSISTENTE'

def test_canonical_hash_and_stale():
    value={'ñ':None,'n':0,'array':[3,1]}
    assert m.digest(value)==hashlib.sha256(m.dump(value).encode('utf-16le')).digest()
    assert m.digest({'a':1,'b':2})==m.digest({'b':2,'a':1})
    assert m.digest({'n':None})!=m.digest({'n':0})
    with pytest.raises(m.StaleContextError,match='El contexto operacional cambió'):m.check_context('old','new')

def test_no_phase_model_dependency():
    import inspect
    assert 'import phase_model' not in inspect.getsource(m)


@pytest.mark.parametrize('bad',['missing','duplicate','name','date'])
def test_order_validation_does_not_trust_reliable_label(bad):
    r=roster();rows=[dict(x,fecha=r['fecha'],pad_id=2,parcela_id=59,campana_id=10,numero_campana='11',
                       estado_roster='CONFIABLE',total_modulos=5,orden_incremental=i+1) for i,x in enumerate(r['miembros'])]
    if bad=='missing':rows[1]['secuencia_carguio']=None
    if bad=='duplicate':rows[1]['secuencia_carguio']=1
    if bad=='name':rows[1]['nombre_visible']='No interpretable'
    if bad=='date':rows[1]['fecha_ini_carguio']='2026-08-01'
    result=m.roster_context(rows)
    assert result['estado_roster']=='ORDEN_AMBIGUO'
    assert m.reference_preview(result,3)['sugeridos'] is None
