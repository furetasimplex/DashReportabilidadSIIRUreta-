"""Read-only identification of stored flow profiles and recovery objects."""
import contextlib, io, json, re, sys
from pathlib import Path
from sqlalchemy import event, text

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'DashReportabilidadSIIR'))
with contextlib.redirect_stdout(io.StringIO()):
    from curvas_recon import db_pipeline as db
    engine=db.get_engine()
assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',db.SCHEMA)

@event.listens_for(engine, 'before_cursor_execute')
def guard(conn,cursor,statement,parameters,context,executemany):
    sql=re.sub(r'/\*.*?\*/|--[^\n]*','',statement,flags=re.S).strip()
    if not re.match(r'(?is)^(select|with)\b',sql) or re.search(r'(?i)\b(insert|update|delete|merge|truncate|alter|drop|create|exec|execute|call)\b',sql):
        raise ValueError('Non-SELECT blocked')
    cursor.connection.timeout=30

try:
    with engine.connect() as conn:
        q=text(f'''SELECT TOP (30) r.id, r.caso_id,r.semana_lunes,r.semana_fin,r.method,r.converged,
            COUNT(d.id) AS row_count, SUM(CASE WHEN d.q_pls IS NOT NULL THEN 1 ELSE 0 END) AS qd_rows
          FROM {db.SCHEMA}.reconciliacion_run r
          LEFT JOIN {db.SCHEMA}.reconciliacion_detalle_dia d ON d.run_id=r.id AND d.label='SULFUROS'
          WHERE r.caso_id IN (10009,10013)
          GROUP BY r.id,r.caso_id,r.semana_lunes,r.semana_fin,r.method,r.converged
          ORDER BY r.id DESC''')
        runs=[dict(r) for r in conn.execute(q).mappings()]
        q=text('''SELECT s.name AS schema_name,o.name AS object_name,o.type AS object_type
          FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
          WHERE s.name=:schema AND o.type IN ('U','V')
          AND (o.name LIKE '%recuper%' OR o.name LIKE '%recon%curva%') ORDER BY o.name''')
        objects=[dict(r) for r in conn.execute(q,{'schema':db.SCHEMA}).mappings()]
        q=text(f'''SELECT origen, MIN(fecha) AS primera,MAX(fecha) AS ultima,
            COUNT(*) AS filas, SUM(CASE WHEN fecha=:prev THEN 1 ELSE 0 END) AS filas_limite
            FROM {db.SCHEMA}.stg_recuperaciones_oficial WHERE pad_id=2 GROUP BY origen''')
        provenance=[dict(r) for r in conn.execute(q,{'prev':'2026-08-31'}).mappings()]
        q=text(f'''SELECT TOP(5) fecha,parcela,origen,recuperacion
            FROM {db.SCHEMA}.stg_recuperaciones_oficial
            WHERE pad_id=2 AND fecha=:prev ORDER BY parcela''')
        baseline=[dict(r) for r in conn.execute(q,{'prev':'2026-08-31'}).mappings()]
        q=text(f'''SELECT Parcela,Campana,Fecha_drenaje,Recuperacion_parcela
            FROM {db.SCHEMA}.Recuperaciones_pad WHERE PAD='SULFUROS'
            AND Parcela IN (24,25) AND Fecha_drenaje BETWEEN :start AND :end
            ORDER BY Parcela,Fecha_drenaje''')
        young=[dict(r) for r in conn.execute(q,{'start':'2026-08-30','end':'2026-09-02'}).mappings()]
        q=text(f'''SELECT s.parcela,s.parcela_id,s.origen,s.recuperacion,r.Campana,
             r.Recuperacion_parcela AS observada
            FROM {db.SCHEMA}.stg_recuperaciones_oficial s
            LEFT JOIN {db.SCHEMA}.Recuperaciones_pad r
              ON r.parcela_id=s.parcela_id AND r.Fecha_drenaje=s.fecha
            WHERE s.pad_id=2 AND s.fecha=:day AND s.origen='ago-2026'
            ORDER BY s.parcela''')
        august23=[dict(r) for r in conn.execute(q,{'day':'2026-08-23'}).mappings()]
    data={'runs':runs,'official_staging_sources':provenance,'baseline_sample':baseline,'young_campaign':young,'august23':august23}
    Path(__file__).with_name('profile_sources_metadata.json').write_text(json.dumps(data,ensure_ascii=False,default=str,indent=2),encoding='utf-8')
    print(json.dumps({'runs':runs,'official_23aug_rows':len(august23),
                      'matched_primary':sum(r['observada'] is not None and abs(float(r['observada'])-float(r['recuperacion']))<1e-8 for r in august23),
                      'young_campaign':young},ensure_ascii=False,default=str))
except Exception as exc:
    print(json.dumps({'error_type':type(exc).__name__}));raise SystemExit(1)
