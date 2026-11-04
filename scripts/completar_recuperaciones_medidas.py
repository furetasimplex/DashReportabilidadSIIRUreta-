#!/usr/bin/env python3
"""Completa `Recuperaciones_pad` con recuperacion calculada de datos medidos.

Para los dias en que SIIR aun no trae lectura, parte de la ultima lectura de
cada pila y suma el Cu neto diario medido (riego, Cu de riego y Cu de drenaje;
Q de drenaje = 0,95 x Q de riego, la misma base de `report_metodo`). Solo
completa pilas con MAS de 30 dias desde el primer riego: las jovenes las
ajusta el metodo de Sulfuros y su drenaje real no es el 0,95.

Por defecto es una PRUEBA EN SECO: solo lee y escribe un plan en auditorias/.
Con --aplicar inserta filas nuevas (nunca actualiza ni borra) dentro de una
transaccion, solo en fechas posteriores a la ultima lectura de cada pila y
solo si no existe ya una fila para esa pila y fecha.

Uso (desde la raiz del repo):

    python scripts/completar_recuperaciones_medidas.py --caso 10013                    # prueba en seco
    python scripts/completar_recuperaciones_medidas.py --caso 10013 --aplicar          # escribe
    python scripts/completar_recuperaciones_medidas.py --hasta 2026-10-12 --pad OXIDOS

Despues de aplicar: refrescar el dash y ejecutar el calculo del Caso. Cuando
SIIR cargue las recuperaciones oficiales de esas fechas, reemplace estas filas
para no duplicar pila/fecha.
"""
import argparse
import csv
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ['RECON_SIN_CACHE'] = '1'
sys.path.insert(0, str(ROOT))

COLUMNS = ('Fecha_drenaje', 'PAD', 'pad_id', 'Parcela', 'parcela_id', 'Campana', 'campaña_id', 'Recuperacion_parcela')
FORBIDDEN = r'\b(update|delete|merge|truncate|alter|drop|create|exec|execute|call|grant|revoke)\b'


def statement_allowed(statement, schema, apply=False):
    """SELECT/WITH siempre; INSERT solo sobre Recuperaciones_pad, con VALUES y solo con --aplicar.

    Rechaza sentencias multiples y SELECT ... INTO (que crea tablas)."""
    sql = re.sub(r'/\*.*?\*/|--[^\n]*', '', statement, flags=re.S).strip().lower().rstrip(';').strip()
    if ';' in sql or re.search(FORBIDDEN, sql):
        return False
    if re.match(r'^(select|with)\b', sql):
        return not re.search(r'\b(insert|into)\b', sql)
    return bool(apply and re.match(rf'^insert\s+into\s+{re.escape(schema.lower())}\.recuperaciones_pad\s*\(', sql)
                and re.search(r'\bvalues\b', sql) and not re.search(r'\bselect\b', sql))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--caso', type=int, help='Caso oficial: define la ventana y la fecha final')
    parser.add_argument('--hasta', type=date.fromisoformat, help='ultima fecha a completar (YYYY-MM-DD)')
    parser.add_argument('--pad', choices=('SULFUROS', 'OXIDOS'), default='SULFUROS')
    parser.add_argument('--edad-minima', type=int, default=30, help='solo pilas con mas de estos dias desde el primer riego')
    parser.add_argument('--oficial-xlsx', type=Path, default=ROOT / 'Auditoria_Recuperaciones_SIIR_vs_Oficial_20261012.xlsx',
                        help='Excel con la hoja Oficial_02_12_oct: las curvas calculadas deben coincidir con el, salvo las pilas nuevas')
    parser.add_argument('--tolerancia-pp', type=float, default=0.05, help='diferencia maxima aceptada contra el oficial (pp)')
    parser.add_argument('--forzar', action='store_true', help='aplica aunque alguna pila difiera del oficial')
    parser.add_argument('--aplicar', action='store_true', help='inserta las filas (por defecto solo prueba en seco)')
    parser.add_argument('--salida', type=Path, help='carpeta para el plan (por defecto auditorias/completar_recuperaciones_<hasta>)')
    args = parser.parse_args(argv)
    if not args.caso and not args.hasta:
        parser.error('indique --caso o --hasta')
    return args


def main(argv=None):
    args = parse_args(argv)
    import contextlib, io
    from sqlalchemy import event, text
    with contextlib.redirect_stdout(io.StringIO()):
        from curvas_recon import db_pipeline as db
        from curvas_recon.recon_engine import (
            inicio_campana, load_cu_riego, load_drena_cu, load_riego, load_wip, resolve_window)
        from curvas_recon.recuperacion_medida import compare_with_official, plan_completion
        from curvas_recon.comparacion_oficial import load_official
        engine = db.get_engine()
    schema = db.SCHEMA
    assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', schema)

    @event.listens_for(engine, 'before_cursor_execute')
    def guard(conn, cursor, statement, parameters, context, executemany):
        if not statement_allowed(statement, schema, args.aplicar):
            raise RuntimeError('Sentencia no permitida bloqueada')

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ws = None
            if args.caso:
                caso = next((c for c in db.load_casos() if c['id'] == args.caso), None)
                if caso is None:
                    raise SystemExit(f'El Caso {args.caso} no existe entre los oficiales con run exitoso.')
                ws, we, _ = resolve_window(caso['fecha_inicio'], caso['fecha_fin'])
            until = args.hasta or we.date()
            ws_date = ws.date() if ws is not None else None
            label = args.pad
            with engine.connect() as conn:
                rows = conn.execute(text(f"""
                    SELECT Parcela, Fecha_drenaje, Recuperacion_parcela, pad_id, parcela_id, Campana, [campaña_id]
                    FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY Parcela ORDER BY Fecha_drenaje DESC, id_rec DESC) AS rn
                          FROM {schema}.Recuperaciones_pad WHERE PAD = :pad AND Recuperacion_parcela IS NOT NULL) x
                    WHERE rn = 1"""), {'pad': label}).fetchall()
            base = {}
            for parcela, fecha, pct, pad_id, parcela_id, campana, camp_id in rows:
                if str(parcela).strip().isdigit():
                    base[f'P{int(parcela):02d}'] = dict(fecha=fecha, pct=float(pct), ids=dict(
                        Parcela=parcela, pad_id=pad_id, parcela_id=parcela_id, Campana=campana, campaña_id=camp_id))
            if not base:
                raise SystemExit('Recuperaciones_pad no tiene lecturas para ese PAD.')
            ref = ws_date or (until - timedelta(days=45))
            ws_date = ref                                # base mas antigua que ref-31 d: no se extiende
            day_of = lambda v: v.date() if hasattr(v, 'date') else v
            start = min((day_of(b['fecha']) for b in base.values() if day_of(b['fecha']) >= ref - timedelta(days=31)),
                        default=ref)
            riego = load_riego(label, start, until)
            cu_r = load_cu_riego(label, start, until, fill=False)
            cu_d = load_drena_cu(label, start, until, fill=False)
            wip, first = load_wip(label), inicio_campana(label, until)
        to_dict = lambda s: {k.date(): float(v) for k, v in s.dropna().items()}
        q = {p: to_dict(riego[c]) for c in riego.columns for p in [f'P{int(str(c).lstrip("Pp")):02d}']} if len(riego) else {}
        cu_riego = to_dict(cu_r) if len(cu_r) else {}
        cu_drena = {f'P{int(str(c).lstrip("Pp")):02d}': to_dict(cu_d[c]) for c in cu_d.columns} if len(cu_d) else {}
        cu_tf = {p: m['CuTf'] for p, m in wip.items() if m.get('CuTf') == m.get('CuTf')}
        first = {f'P{int(str(p).lstrip("Pp")):02d}': v for p, v in first.items()}
        plan, report = plan_completion(base, cu_tf, first, q, cu_riego, cu_drena, until, window_start=ws_date,
                                       min_age_days=args.edad_minima)
    except SystemExit:
        raise
    except ImportError as exc:
        print(f'Falta un modulo de Python ({exc.name}). Instala requirements.txt y reintenta.')
        return 1
    except Exception as exc:                                     # nunca mostrar cadenas de conexion
        print(f'No se pudo leer la base ({type(exc).__name__}). Revisa el .env y la conectividad.')
        return 1

    folder = args.salida or ROOT / 'auditorias' / f'completar_recuperaciones_{until.isoformat()}'
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / 'plan_filas.csv', 'w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle); writer.writerow(('pila', 'fecha', 'recuperacion_pct'))
        writer.writerows((r['pila'], r['fecha'].isoformat(), f"{r['recuperacion_pct']:.9f}") for r in plan)
    with open(folder / 'plan_por_pila.csv', 'w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report[0])); writer.writeheader(); writer.writerows(report)

    print(f"{label} hasta {until} · {'APLICAR' if args.aplicar else 'prueba en seco'} · edad minima > {args.edad_minima} d")
    print(f'{"pila":5} {"estado":9} {"ultima":10} {"filas":>5} {"inicial %":>9} {"final %":>8}  motivo')
    for r in report:
        fin = '' if r['pct_final'] is None else f"{r['pct_final']:.3f}"
        print(f"{r['pila']:5} {r['estado']:9} {r['ultima_lectura']:10} {r['filas']:5d} {r['pct_inicial']:9.3f} {fin:>8}  {r['motivo'] or ''}")
    official = {}
    if args.oficial_xlsx and args.oficial_xlsx.exists():
        official = load_official(args.oficial_xlsx, None, pad=label)
    comparison, all_equal = compare_with_official(plan, report, official, args.tolerancia_pp)
    with open(folder / 'comparacion_con_oficial.csv', 'w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison[0])); writer.writeheader(); writer.writerows(comparison)
    print(f'\nComparacion con el reporte oficial (tolerancia {args.tolerancia_pp} pp; deben ser iguales salvo las pilas nuevas):')
    print(f'{"pila":5} {"dias":>4} {"max |dif| pp":>12} {"fecha":10} {"calculada %":>11} {"oficial %":>9}  estado')
    for r in comparison:
        f3 = lambda v: '' if v is None else f'{v:.3f}'
        print(f"{r['pila']:5} {r['dias_comparados']:4d} {f3(r['max_abs_pp']):>12} {r['fecha_max'] or '':10} "
              f"{f3(r['calculada_final_pct']):>11} {f3(r['oficial_final_pct']):>9}  {r['estado']}")
    if not official:
        print('(sin Excel oficial: no se pudo comparar)')
    print(f'Resultado: {"IGUALES salvo pilas nuevas" if all_equal and official else "HAY DIFERENCIAS o falta oficial"}')
    print(f'\nFilas a insertar: {len(plan)} · plan en {folder.relative_to(ROOT) if folder.is_relative_to(ROOT) else folder}')
    if not args.aplicar or not plan:
        if not args.aplicar:
            print('Prueba en seco: no se escribio nada. Repita con --aplicar para insertar.')
        return 0

    if not (all_equal and official) and not args.forzar:
        print('No se inserto nada: la comparacion con el oficial no coincide (use --forzar solo si lo revisó).')
        return 1
    try:
        with engine.begin() as conn:                              # transaccion unica
            before = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.Recuperaciones_pad WHERE PAD = :pad"), {'pad': label}).scalar()
            for r in plan:
                clash = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.Recuperaciones_pad WHERE PAD = :pad AND Parcela = :parcela "
                                          "AND CAST(Fecha_drenaje AS date) = :fecha"),
                                     {'pad': label, 'parcela': r['ids']['Parcela'], 'fecha': r['fecha']}).scalar()
                if clash:
                    raise RuntimeError(f"ya existe {r['pila']} {r['fecha']}; no se inserta nada")
            conn.execute(text(f"INSERT INTO {schema}.Recuperaciones_pad (Fecha_drenaje, PAD, pad_id, Parcela, parcela_id, Campana, [campaña_id], "
                              "Recuperacion_parcela) VALUES (:fecha, :pad, :pad_id, :parcela, :parcela_id, :campana, :camp_id, :pct)"),
                         [dict(fecha=r['fecha'], pad=label, pad_id=r['ids']['pad_id'], parcela=r['ids']['Parcela'],
                               parcela_id=r['ids']['parcela_id'], campana=r['ids']['Campana'],
                               camp_id=r['ids']['campaña_id'], pct=r['recuperacion_pct']) for r in plan])
            after = conn.execute(text(f"SELECT COUNT(*) FROM {schema}.Recuperaciones_pad WHERE PAD = :pad"), {'pad': label}).scalar()
            if after - before != len(plan):
                raise RuntimeError(f'verificacion fallida: se esperaban {len(plan)} filas nuevas y hay {after - before}; se revierte')
        print(f'Insertadas {len(plan)} filas en {schema}.Recuperaciones_pad (total del PAD: {before} -> {after}).')
    except Exception as exc:
        print(f'No se inserto nada ({type(exc).__name__}: {exc if isinstance(exc, RuntimeError) else "ver permisos y conectividad"}).')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
