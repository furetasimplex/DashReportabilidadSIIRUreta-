#!/usr/bin/env python3
"""Extrae de la base los datos de un Caso a UN Excel, para probar el calculo en otro entorno.

Solo lectura: la conexion queda protegida para aceptar unicamente SELECT/WITH. No escribe en
SQL, no ejecuta SP y no calcula nada. El archivo no incluye credenciales ni cadenas de
conexion. Lee la configuracion del `.env` del repo.

Uso (desde la raiz del repo):

    python scripts/extraer_datos_caso.py --caso 10013
    python scripts/extraer_datos_caso.py --caso 10013 --salida C:/ruta/datos_caso_10013.xlsx

Hojas: caso, flujos_run (los 125 flujos del run oficial), riego, cu_riego, cu_drena (series
medidas SIN relleno, Oxidos y Sulfuros), recuperaciones_pad (curvas), campana (Cu apilado),
primer_riego, apilado, perfil_guardado (drenaje modelado guardado del Caso), historico_oficial
(flujos y concentraciones oficiales previas al Caso) y resumen.
"""
import argparse
import contextlib
import io
import os
import re
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ['RECON_SIN_CACHE'] = '1'          # lecturas directas, sin cache en disco
sys.path.insert(0, str(ROOT))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--caso', type=int, help='id del Caso oficial (por defecto, el mas reciente)')
    parser.add_argument('--salida', type=Path, help='archivo .xlsx de salida (por defecto auditorias/datos_caso_<id>.xlsx)')
    parser.add_argument('--dias-previos', type=int, default=45, help='dias de series medidas antes de la ventana')
    parser.add_argument('--dias-recuperaciones', type=int, default=420, help='dias de curvas de recuperacion antes de la ventana')
    parser.add_argument('--dias-historico', type=int, default=120, help='dias de historico oficial antes de la ventana')
    return parser.parse_args(argv)


def install_select_only_guard(engine):
    from sqlalchemy import event

    @event.listens_for(engine, 'before_cursor_execute')
    def guard(conn, cursor, statement, parameters, context, executemany):
        sql = re.sub(r'/\*.*?\*/|--[^\n]*', '', statement, flags=re.S).strip().lower().rstrip(';').strip()
        if (';' in sql or not re.match(r'^(select|with)\b', sql)
                or re.search(r'\b(insert|into|update|delete|merge|truncate|alter|drop|create|exec|execute|call|grant|revoke)\b', sql)):
            raise RuntimeError('Sentencia no SELECT bloqueada')


def main(argv=None):
    args = parse_args(argv)
    import pandas as pd
    from sqlalchemy import text
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            from curvas_recon import db_pipeline as db, recon_engine as E
            from curvas_recon.extraccion_caso import build_tables, write_workbook
            from curvas_recon.history_recovery import HistoryReader
            from curvas_recon.report_metodo import leer_apilado
            from curvas_recon.sulfide_db_inputs import load_saved_profile
            engine = db.get_engine()
            install_select_only_guard(engine)
            casos = [c for c in db.load_casos() if c.get('run_id')]
            caso = next((c for c in casos if c['id'] == args.caso), None) if args.caso else (casos[0] if casos else None)
            if caso is None:
                raise SystemExit(f'El Caso {args.caso} no existe entre los oficiales con run exitoso.')
            ws, we, _ = E.resolve_window(caso['fecha_inicio'], caso['fecha_fin'])
            start = ws - timedelta(days=args.dias_previos)
            series, wip, first = {}, {}, {}
            for label in ('OXIDOS', 'SULFUROS'):
                riego = E.load_riego(label, start, we)
                cu_r = E.load_cu_riego(label, start, we, fill=False)
                cu_d = E.load_drena_cu(label, start, we, fill=False)
                series[label] = dict(
                    riego=riego[riego.index >= start] if len(riego) else riego,
                    cu_riego=cu_r[cu_r.index >= start] if len(cu_r) else cu_r,
                    cu_drena=cu_d[cu_d.index >= start] if len(cu_d) else cu_d)
                wip[label] = E.load_wip(label)
                first[label] = E.inicio_campana(label, we)
            with engine.connect() as conn:
                flows = conn.execute(text(f"""
                    SELECT codigo_flujo, masa_medida, masa_reconciliada, fino_cu_medido, fino_cu_reconciliado
                    FROM {db.HIDRO_SCHEMA}.recon_resultado_flujo WHERE run_id = :run ORDER BY codigo_flujo"""),
                    {'run': int(caso['run_id'])}).fetchall()
                recoveries = conn.execute(text(f"""
                    SELECT PAD, TRY_CAST(Parcela AS INT) AS Parcela, Campana, CAST(Fecha_drenaje AS DATE) AS Fecha_drenaje,
                           Recuperacion_parcela
                    FROM {db.SCHEMA}.Recuperaciones_pad
                    WHERE Recuperacion_parcela IS NOT NULL AND PAD IN ('OXIDOS', 'SULFUROS')
                      AND Fecha_drenaje >= :desde ORDER BY PAD, Parcela, Fecha_drenaje"""),
                    {'desde': (ws - timedelta(days=args.dias_recuperaciones)).date()}).fetchall()
            stacking = leer_apilado(asof=we)
            saved = load_saved_profile(caso['id'], ws, we)
            history = [r for r in HistoryReader().load(engine, db.SCHEMA, db.HIDRO_SCHEMA, f'extraccion-{caso["id"]}', ws.date())
                       if pd.Timestamp(r['date']) >= ws - timedelta(days=args.dias_historico)]
    except SystemExit:
        raise
    except ImportError as exc:
        print(f'Falta un modulo de Python ({exc.name}). Instala requirements.txt y reintenta.')
        return 1
    except Exception as exc:                                           # nunca mostrar cadenas de conexion
        print(f'No se pudo leer la base ({type(exc).__name__}). Revisa el .env y la conectividad.')
        return 1

    last_rec = max((r[3] for r in recoveries), default=None)
    notes = [f'Extraido de la base en modo solo lectura. Caso {caso["id"]} run {caso["run_id"]} ({ws.date()}..{we.date()}).',
             f'Ultima lectura de Recuperaciones_pad: {last_rec}.',
             'Las series de riego, Cu riego y Cu drenaje van sin relleno (lecturas tal cual).']
    tables = build_tables(
        dict(id=caso['id'], nombre=caso['nombre'], run_id=caso['run_id'], fecha_inicio=caso['fecha_inicio'],
             fecha_fin=caso['fecha_fin'], modelo_codigo=caso['modelo_codigo'], modelo_version=caso['modelo_version'],
             total_flujos=caso['total_flujos']),
        (ws, we), flows, series, recoveries, wip, first, stacking, saved, history, notes)
    path = args.salida or ROOT / 'auditorias' / f'datos_caso_{caso["id"]}.xlsx'
    path.parent.mkdir(parents=True, exist_ok=True)
    write_workbook(tables, path)
    print(f'Caso #{caso["id"]} {caso["nombre"]} · run {caso["run_id"]} · {ws.date()}..{we.date()}')
    for name, frame in tables.items():
        print(f'  {name:20} {len(frame):7d} filas')
    print(f'Ultima lectura de recuperaciones: {last_rec}')
    print(f'\nArchivo: {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
