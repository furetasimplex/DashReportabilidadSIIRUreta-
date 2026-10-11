"""Ejecuta smokes existentes preservando sus artefactos históricos byte a byte."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from . import db, smoke_map_dev, smoke_modules_dev, smoke_diagnostic_dev
from .smoke_evidence import write_evidence, definition_hashes
from sqlalchemy import text


def run(name):
    module,category,target={
        'map':(smoke_map_dev,'CURRENT_SMOKE',Path('lixiviacion/SMOKE_MAP_DEV.json')),
        'modules':(smoke_modules_dev,'CURRENT_SMOKE',Path('lixiviacion/SMOKE_MODULES_DEV.json')),
        'diagnostic':(smoke_diagnostic_dev,'REGRESSION_TEST',Path('lixiviacion/diagnostico_fase1/smoke.json'))}[name]
    report={'passed':False}; hashes=None
    def capture(path,data,*args,**kwargs):
        if path.resolve()==target.resolve():
            report.update(json.loads(data)); return len(data)
        raise RuntimeError(f'Escritura inesperada del smoke: {path}')
    try:
        with db._connection() as conn:
            assert conn.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
            objects=[db.SOURCE,db.OP_SOURCE]
            if name=='modules': objects.append('inventar_SpcHidr.fn_estado_operacional_modulo_diario')
            hashes=definition_hashes(conn,objects)
        with patch.object(Path,'write_text',capture):
            module.run()
        assert report.get('passed'), 'Smoke no produjo resultado PASS'
    except Exception as exc:
        report.update(passed=False,failure=str(exc)); raise
    finally:
        write_evidence(category,name,report,period={'desde':'2026-06-01' if name=='diagnostic' else '2026-09-10','hasta':'2026-09-11' if name=='map' else '2026-09-10'},definitions=hashes)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('name',choices=['map','modules','diagnostic']); run(parser.parse_args().name)
