"""Inventario estático y manifiesto histórico; nunca consulta LIVE."""
import ast
import csv
import hashlib
import json
from pathlib import Path

P=Path(__file__).parent


def run():
    original=Path('lixiviacion/SMOKE_DEV.json')
    manifest=dict(type='HISTORICAL_BASELINE',validated_at=None,
        validation_date_note='No registrada en SMOKE_DEV.json; no inferida del mtime ni de la fecha de inventario.',
        period={'desde':'2026-06-01','hasta':'2026-09-10'},environment='DEV',database='inventar_SpcHidr',
        source='inventar_SpcHidr.vw_tablero_lixiviacion_final_v2',definition_hash_at_validation=None,
        artifact=str(original),sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        expected=json.loads(original.read_text(encoding='utf-8')),represents_current_live=False,
        update_policy='Solo nueva versión con aprobación explícita del responsable funcional/usuario; nunca sobrescribir original.')
    (P/'baseline_fecha_no_registrada_20260601_20260910.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    items=[]
    for path in Path('lixiviacion').rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or any(x in path.parts for x in ('baselines','test_evidence')): continue
        if path.suffix not in ('.md','.json') and not (path.suffix=='.py' and ('test' in path.name or 'smoke' in path.name)): continue
        content=path.read_text(encoding='utf-8-sig')
        category='REGRESSION_TEST' if any(x in str(path) for x in ('timeline_runtime','performance_candidate','diagnostico_fase1','smoke_diagnostic','test_')) else 'STRUCTURAL_TEST'
        if path.name in ('smoke_dev.py','SMOKE_DEV.json'): category='HISTORICAL_BASELINE'
        elif path.name in ('smoke_map_dev.py','smoke_modules_dev.py','SMOKE_MAP_DEV.json','SMOKE_MODULES_DEV.json','smoke_current_dev.py'): category='CURRENT_SMOKE'
        elif path.name in ('test_promocion.py','test_smoke_strategy.py','smoke_evidence.py','run_versioned_smoke.py'): category='STRUCTURAL_TEST'
        tree=ast.parse(content) if path.suffix=='.py' else None
        constants=sorted({str(n.value) for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,(str,int,float)) and (isinstance(n.value,(int,float)) or any(t in n.value for t in ('2026','30136','RIEGO','MIXTO','APILADO','RECLAMO')))},key=str) if tree else []
        tests=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test')] if tree else []
        items.append({'archivo':str(path),'categoria':category,'tipo':'ejecutable' if tree else 'evidencia/documentación; no ejecutar',
          'proposito':' / '.join(tests) if tests else ('comparación histórica' if category=='HISTORICAL_BASELINE' else 'evidencia o validación '+category),
          'periodo':'2026-06-01..2026-09-10' if '2026-06-01' in content else ('2026-09-10' if '2026-09-10' in content else 'ver archivo; mocks o metadatos'),
          'hardcoded':json.dumps(constants,ensure_ascii=False),
          'dependencias':('Ninguna consulta; evidencia/documentación' if not tree else ('Sin LIVE: fixtures y archivos locales' if path.name.startswith('test_') else 'V2 / funciones operacionales según imports db/map_db; consultar matriz de estrategia')),
          'escribe_artefactos':bool(tree and any(s in content for s in ('write_text','write_evidence','json.dump'))),
          'puede_fallar_por_datos':'sí si consulta LIVE/canónicos; evidencia estática no se ejecuta' if 'smoke' in path.name else 'mocks/estático o comparación posterior; ver estrategia',
          'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    with (P/'INVENTARIO.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
    print('Inventario:',len(items))


if __name__=='__main__':run()
