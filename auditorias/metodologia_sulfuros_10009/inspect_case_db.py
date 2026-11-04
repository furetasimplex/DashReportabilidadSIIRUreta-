"""Inspección SELECT-only acotada; nunca imprime la conexión ni sus errores."""
import contextlib, io, json, re, sys
from pathlib import Path
from sqlalchemy import event, text

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root.parent/'DashReportabilidadSIIR'))
try:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from curvas_recon import db_pipeline as db
        engine=db.get_engine()
    assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',db.SCHEMA)
    @event.listens_for(engine,'do_connect')
    def timeout(dialect,conn_rec,cargs,cparams):
        cparams['timeout']=10
    with engine.connect() as conn:
        conn.connection.driver_connection.timeout=20
        runs=[dict(r) for r in conn.execute(text(f'''SELECT TOP (12) id,caso_id,semana_lunes,semana_fin
            FROM {db.SCHEMA}.reconciliacion_run WHERE caso_id=:case ORDER BY id DESC'''),{'case':10009}).mappings()]
        cols=[r[0] for r in conn.execute(text('''SELECT c.name FROM sys.columns c
            JOIN sys.tables t ON t.object_id=c.object_id JOIN sys.schemas s ON s.schema_id=t.schema_id
            WHERE s.name=:schema AND t.name='reconciliacion_detalle_dia' ORDER BY c.column_id'''),{'schema':db.SCHEMA})]
    payload={'status':'read_only_ok','case':10009,'runs':runs,'daily_columns':cols}
    (Path(__file__).parent/'db_case_index.json').write_text(json.dumps(payload,default=str,indent=2),encoding='utf-8')
    print(json.dumps({'status':payload['status'],'runs':runs,'daily_columns':cols},default=str))
except Exception as exc:
    print(json.dumps({'status':'read_only_unavailable','error_type':type(exc).__name__}))
