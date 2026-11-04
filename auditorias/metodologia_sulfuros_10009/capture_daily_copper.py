"""Capture campaign-11 daily stacked Cu for baseline verification; SELECT only."""
import contextlib,io,json,re,sys
from pathlib import Path
from sqlalchemy import event,text
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'DashReportabilidadSIIR'))
with contextlib.redirect_stdout(io.StringIO()):
    from curvas_recon import db_pipeline as db
    engine=db.get_engine()
assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',db.SCHEMA)
@event.listens_for(engine,'before_cursor_execute')
def guard(conn,cursor,statement,parameters,context,executemany):
    sql=re.sub(r'/\*.*?\*/|--[^\n]*','',statement,flags=re.S).strip()
    if not re.match(r'(?is)^(select|with)\b',sql) or re.search(r'(?i)\b(insert|update|delete|merge|truncate|alter|drop|create|exec|execute|call)\b',sql):
        raise ValueError('Non-SELECT blocked')
    cursor.connection.timeout=30
try:
    with engine.connect() as conn:
        rows=[dict(r) for r in conn.execute(text(f'''SELECT TRY_CAST(Parcela AS int) pile,
            TRY_CAST(Campana AS int) campaign,CAST(Fecha AS date) date,
            SUM(CAST(Finos_cut AS float)) cu_t
            FROM {db.SCHEMA}.modulos_turnos WHERE pad_id=2 AND Campana=11
            AND Fecha<=:end AND Parcela BETWEEN 7 AND 25 GROUP BY Parcela,Campana,Fecha
            ORDER BY Parcela,Fecha'''),{'end':'2026-09-07'}).mappings()]
    p=Path(__file__).with_name('campaign11_daily_stacked_cu.json')
    p.write_text(json.dumps(rows,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'rows':len(rows),'pile_count':len({x['pile'] for x in rows})}))
except Exception as exc:
    print(json.dumps({'error_type':type(exc).__name__}));raise SystemExit(1)
