#!/usr/bin/env python3
"""Compara la metodologia de Sulfuros (ajuste de curvas de hasta 30 dias) con el
reporte oficial, fuera del dash.

Solo lectura: la conexion queda protegida para aceptar unicamente SELECT/WITH.
No ejecuta `Ejecutar cálculo`, no corre el metodo anterior ni guarda en SQL.
Lee la configuracion de conexion del `.env` del repo; no imprime credenciales.

Uso (desde la raiz del repo):

    python scripts/comparar_metodo_vs_oficial.py                 # Caso oficial mas reciente
    python scripts/comparar_metodo_vs_oficial.py --caso 10013
    python scripts/comparar_metodo_vs_oficial.py --caso 10013 \
        --oficial-xlsx Auditoria_Recuperaciones_SIIR_vs_Oficial_20261012.xlsx

Salida en auditorias/comparacion_oficial_<caso>/: RESULTADO.md, resumen_por_pila.csv
y detalle_diario.csv. Codigo de salida 1 si alguna verificacion falla.
"""
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ['RECON_SIN_CACHE'] = '1'          # lecturas directas, sin cache en disco
sys.path.insert(0, str(ROOT))

DEFAULT_XLSX = ROOT / 'Auditoria_Recuperaciones_SIIR_vs_Oficial_20261012.xlsx'
DEFAULT_HISTORY = ROOT / 'curvas_recon' / 'test_fixtures' / 'historico_oficial_validado_20260901_20261001.csv'


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--caso', type=int, help='id del Caso oficial (por defecto, el mas reciente)')
    parser.add_argument('--oficial-xlsx', type=Path, default=DEFAULT_XLSX,
                        help=f'Excel con la hoja Oficial_02_12_oct (por defecto {DEFAULT_XLSX.name})')
    parser.add_argument('--historico-csv', type=Path, default=DEFAULT_HISTORY,
                        help='historico oficial validado (CSV) para el dia previo a la ventana')
    parser.add_argument('--salida', type=Path, help='carpeta de salida (por defecto auditorias/comparacion_oficial_<caso>)')
    parser.add_argument('--tolerancia-pp', type=float, default=1e-4, help='tolerancia medido vs oficial en maduras')
    return parser.parse_args(argv)


def install_select_only_guard(engine):
    from sqlalchemy import event

    @event.listens_for(engine, 'before_cursor_execute')
    def guard(conn, cursor, statement, parameters, context, executemany):
        sql = re.sub(r'/\*.*?\*/|--[^\n]*', '', statement, flags=re.S).strip().lower()
        if not re.match(r'^(select|with)\b', sql) or re.search(
                r'\b(insert|update|delete|merge|truncate|alter|drop|create|exec|execute|call|grant|revoke)\b', sql):
            raise RuntimeError('Sentencia no SELECT bloqueada')


def load_inputs_from_sql(caso_id):
    """Misma preparacion que `Ejecutar cálculo`, pero solo con lecturas."""
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        from curvas_recon import db_pipeline as db, pad_data
        from curvas_recon.recon_engine import (
            inicio_campana, load_cu_riego, load_drena_cu, load_riego, load_wip, pilas_jovenes, resolve_window)
        from curvas_recon.sulfide_db_inputs import load_saved_profile, make_source_provider
        from curvas_recon.sulfide_inputs import load_sulfide_inputs
        install_select_only_guard(db.get_engine())
        casos = [c for c in db.load_casos() if c.get('run_id')]
    caso = next((c for c in casos if c['id'] == caso_id), None) if caso_id else (casos[0] if casos else None)
    if caso is None:
        raise SystemExit(f'El Caso {caso_id} no existe entre los oficiales con run exitoso.')
    with contextlib.redirect_stdout(io.StringIO()):
        ws, we, _ = resolve_window(caso['fecha_inicio'], caso['fecha_fin'])
        anchor = db.load_caso_anchor(caso['run_id'], caso['modelo_codigo'], caso['modelo_version'], caso['total_flujos'])
        problems = db.diagnose_caso_anchor(anchor)
        if problems:
            raise SystemExit('El run oficial no tiene ancla completa: ' + '; '.join(problems))
        young = pilas_jovenes('SULFUROS', ws, we)
        if not young:
            return caso, ws, we, anchor, None
        material = dict(riego=load_riego('SULFUROS', ws, we),
                        cu_riego=load_cu_riego('SULFUROS', ws, we, fill=False),
                        drena_cu=load_drena_cu('SULFUROS', ws, we, fill=False))
        provider = make_source_provider(
            material, pad_data.load_sulfuro(), load_wip('SULFUROS'), inicio_campana('SULFUROS', we), caso,
            saved_profile=load_saved_profile(caso['id'], ws, we))
        payload = load_sulfide_inputs(ws, we, caso['id'], anchor, source_provider=provider)
    return caso, ws, we, anchor, payload


def main(argv=None):
    args = parse_args(argv)
    from curvas_recon.comparacion_oficial import compare, load_official, write_outputs
    from curvas_recon.sulfide_inputs import SulfideInputError
    try:
        caso, ws, we, anchor, payload = load_inputs_from_sql(args.caso)
    except SulfideInputError as exc:
        print(f'ENTRADAS INCOMPLETAS: {exc}')
        return 1
    except SystemExit:
        raise
    except ImportError as exc:
        print(f'Falta un modulo de Python ({exc.name}). Instala requirements.txt y reintenta.')
        return 1
    except Exception as exc:                                   # nunca mostrar cadenas de conexion
        print(f'No se pudo leer la base ({type(exc).__name__}). Revisa el .env y la conectividad.')
        return 1
    print(f"Caso #{caso['id']} {caso['nombre']} · run {caso['run_id']} · {ws.date()}..{we.date()}")
    if payload is None:
        print('Sin curvas nuevas (<=30 dias): el dash usa la distribucion entre todas las curvas '
              '(metodo anterior, que guarda en SQL). No hay ajuste que comparar con este script.')
        return 0
    official = load_official(args.oficial_xlsx if args.oficial_xlsx.exists() else None,
                             args.historico_csv if args.historico_csv.exists() else None)
    result = compare(payload['rows'], payload['target_net_t'], ws, we, official, tol_pp=args.tolerancia_pp)
    folder = write_outputs(result, args.salida or ROOT / 'auditorias' / f"comparacion_oficial_{caso['id']}", f"Caso #{caso['id']}")
    print((folder / 'RESULTADO.md').read_text(encoding='utf-8'))
    print(f'Archivos en {folder.relative_to(ROOT) if folder.is_relative_to(ROOT) else folder}')
    return 0 if all(ok for _, ok, _ in result['checks']) else 1


if __name__ == '__main__':
    sys.exit(main())
